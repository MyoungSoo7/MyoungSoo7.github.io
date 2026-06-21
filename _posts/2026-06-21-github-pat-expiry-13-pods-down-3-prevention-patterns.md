---
layout: post
title: "*GitHub PAT 만료* 로 *13 pod* 가 *동시에 죽었다* — *GHCR 인증 사고* 와 *재발 방지 3 패턴*"
date: 2026-06-21 23:30:00 +0900
categories: [devops, security, kubernetes, incident-postmortem]
tags: [github, ghcr, pat, image-pull-secret, kubernetes, argocd, sops, kyverno, incident, postmortem]
---

> *"2 일 전 부터 *13 pod* 가 *ImagePullBackOff* 였습니다"* — 우리 클러스터 의 *모니터링 알림* 이 *조용히 누적* 되다가 오늘 *눈에 띄게 보였다*.
>
> 원인 은 *Kubernetes 도, Docker 도, ArgoCD 도 아니었다*. *GitHub Personal Access Token (PAT)* 이 *만료* 된 것. *클러스터 의 *모든 namespace* 에 *동일한 ghcr-pull secret* 이 *수동 kubectl create* 로 *분산* 되어 있어서, *그 토큰 만료 가 *체감 적으로 *13 pod 동시 죽음* 으로 *드러났다*.
>
> 더 *고통스러운 발견* : *다른 정상 동작 처럼 보이는 pod 들* 도 *같은 만료된 토큰* 을 가지고 있었다. *그들은 *image 가 노드 에 *이미 cached* 되어 있어 *imagePullPolicy: IfNotPresent* 덕분에 *조용히 살아 있는 것*. *다음 *rolling update / 노드 재시작* 의 *시점* 에 *전부 동시* 죽을 *시한 폭탄*.
>
> 이 글은 *그 사고 의 *진단 과정*, *해결 의 즉시 조치*, *그리고 *재발 방지 의 3 패턴* — *SOPS+ArgoCD 분배*, *default ServiceAccount 자동 패치*, *Kyverno 자동화 (미래)* — 를 *현장 의 깊이* 로 정리한다.

내 *11 편 인프라 연작* 의 *후속 — *현장 사고 회고* 첫 편*:
- [*보안 의 7 기둥*](/2026/06/20/security-7-pillars-auth-encryption-firewall-audit.html) — *시크릿 관리* 의 *원칙*
- [*K8s 컨테이너 오케스트레이션 전쟁사*](/2026/06/20/kubernetes-container-orchestration-what-we-actually-use.html)
- [*K8s 로드밸런서*](/2026/06/21/kubernetes-loadbalancer-network-layers-l4-l7.html)

---

## TL;DR — *한 줄 결론*

> *GitHub PAT* 가 *조용히 만료* 됐고, *13 pod 가 *ImagePullBackOff* 로 *2 일 잠재*. *클러스터 의 *수동 분배 된 ghcr-pull secret 40+ 카피* 가 *모두 동시 죽음*. *해결*: 새 PAT 발급 + *SOPS+ArgoCD 로 분배 자동화* + *default ServiceAccount 패치* + *Kyverno 미래 자동화*. *교훈*: *PAT 만료 는 *알람 사각지대* — *cached image* 가 *진실을 가린다*. *git 추적 가능한 secret 분배* + *expiry 모니터링* 이 *2026 년 production 의 기본*.

---

## 1. *시작 — *증상*

### 1.1 *알림 도착*

```
⚠️ Pod 316개 (Running 303 / Pending 0 / 문제 13)
   • data-prod/data-app-569487d9bd-d4f7n ImagePullBackOff ×0 @ 데이비드
   • jabis-prod/jabis-app-6889cc6757-9q2tc ImagePullBackOff ×0 @ 데이비드
   • jabis-prod/jabis-frontend-599f8c887b-znkxl ImagePullBackOff ×0 @ 데이비드
   • livecommerce-prod/livecommerce-app-7b7b86d544-rmn2w ImagePullBackOff ×0 @ 데이비드
   • livecommerce-prod/livecommerce-frontend-79d4cb4cb7-r9nmq ImagePullBackOff ×0 @ 데이비드
   • logistic-prod/console-app-9d68bff74-hdz9s ImagePullBackOff ×0 @ 이사갈
   ... 외 7개
```

총 *13 pod 가 *ImagePullBackOff*. *5 namespace* (data / jabis / livecommerce / logistic / pilgrim / report) 에 *흩어져* 있다.

### 1.2 *첫 의심* — *이미지 사라짐?*

```bash
$ kubectl -n data-prod describe pod data-app-569487d9bd-d4f7n
...
  Warning  Failed   (x684 over 2d10h)  kubelet
    Failed to pull image "ghcr.io/myoungsoo7/public-data:latest":
    failed to pull and unpack image:
    failed to resolve reference:
    unexpected status from HEAD request to
      https://ghcr.io/v2/myoungsoo7/public-data/manifests/latest:
    403 Forbidden
```

`403 Forbidden` — *권한 부족*. 이미지 *존재* 한다. *받을 권한* 이 없다.

### 1.3 *두 번째 의심* — *credential 만료*

```bash
$ kubectl -n data-prod get secret ghcr-pull -o yaml | grep dockerconfigjson | base64 -d
{"auths":{"ghcr.io":{"auth":"bXlvdW5nc29vNzpnaG9fUHJX...ZzLa"}}}
                                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                  myoungsoo7:gho_PrW...ZzLa
```

`gho_` prefix — *OAuth token*. 어디서 받았는지 *기억 안 남*. *언제 만료* 되는지 *모름*.

다른 namespace 의 토큰 도 확인 :

| Namespace | 토큰 prefix | 형식 |
|---|---|---|
| jabis-prod | `gho_PrW...ZzLa` | OAuth |
| settlement-prod | `gho_PrW...ZzLa` | OAuth (동일) |
| sparta-prod | `ghp_4Fw...sexR` | Classic PAT (다름!) |
| data-prod | `gho_PrW...ZzLa` | OAuth (동일) |

→ *40 namespace 중 *대부분* 이 *동일 OAuth 토큰*. *몇 개 만 *다른 PAT*. *언제 어떻게 *분산* 됐는지 *알 수 없음*.

---

## 2. *진단 — *왜 *지금 시점에 *13 pod 만* 죽는가*

### 2.1 *cached image 의 함정*

> *대부분 pod 는 *정상* 처럼 보였다. 왜 *13 pod 만 *죽었나?*

K8s 의 *기본 `imagePullPolicy`* :
- 태그 가 `latest` 이면 → `Always` (매 시작 시 pull)
- 태그 가 명시적 (예: `v1.2.3`) 이면 → `IfNotPresent` (캐시 우선)

대부분 의 우리 pod 는 *해당 노드 에 *이미 image cached*. *재시작 안 한 한* *새로 pull 안 함* → *만료된 토큰 도 영향 없음*.

**13 pod 의 공통점**:
- 모두 `imagePullPolicy: Always` (latest tag 사용)
- *2 일 전* (2026-06-19) *rolling update* 시점 에 *새 pull 시도*
- 그 시점 에 *PAT 가 이미 만료* → *401 Unauthorized*

→ 즉 *PAT 는 이미 만료된 지 오래* — *우리가 *cached image 덕분에 *조용히 살고 있었던 것*.

### 2.2 *시한폭탄 의 진실*

다른 *310 정상 pod* 도 *같은 만료 토큰* 보유. *그들의 운명*:
- **rolling update** 시 → 새 image pull 시도 → *동시* 실패
- **노드 재시작** 시 → 노드 의 image cache *날아감* → *모든 pod 새로 pull* → *동시* 실패
- **HPA scale up** 시 → 새 pod 가 *새 노드* 에 스케줄 → *image 없음* → pull 시도 → *실패*
- **Cluster Autoscaler / 새 노드 합류** 시 → *동일*

→ **시한폭탄**. *언제 터질지 *예측 불가*. *현재 평화* 는 *cache 의 우연*.

### 2.3 *진단 명령 — *새 PAT 으로 *진짜 작동 검증***

새 PAT (`ghp_Nl8V...DcOkK`) 발급 받고 검증:

```bash
# Basic auth 로 manifest HEAD
AUTH=$(echo -n "myoungsoo7:$NEW_PAT" | base64)
curl -s -o /dev/null -w 'HTTP %{http_code}\n' \
  -H "Authorization: Basic $AUTH" \
  https://ghcr.io/v2/myoungsoo7/jabis-backend/manifests/latest
# → HTTP 401   ← 어? 새 PAT 도 안 됨?
```

여기 서 *처음 *멈췄다*. 새 PAT 도 *401*?

**원인** : ghcr.io 는 *Bearer auth flow* — PAT 으로 *Basic auth 직접* 하면 *안 됨*. *OAuth token exchange* 후 *Bearer* 로 *manifest 호출*.

```bash
# 1) PAT 으로 OAuth token 받기
TOKEN=$(curl -s -u "myoungsoo7:$NEW_PAT" \
  'https://ghcr.io/token?scope=repository:myoungsoo7/jabis-backend:pull' \
  | jq -r .token)

# 2) Bearer token 으로 manifest
curl -s -o /dev/null -w 'HTTP %{http_code}\n' \
  -H "Authorization: Bearer $TOKEN" \
  https://ghcr.io/v2/myoungsoo7/jabis-backend/manifests/latest
# → HTTP 404 / 200   ← 정상
```

또는 *진짜 진실* : `docker login` + `docker pull`:
```bash
echo "$NEW_PAT" | docker login ghcr.io -u myoungsoo7 --password-stdin
# Login Succeeded
docker pull ghcr.io/myoungsoo7/jabis-backend:latest
# Status: Downloaded newer image
```

→ **PAT 는 작동**. *Basic auth 직접* 이 *틀린 검증 방법* 이었던 것.

> 함정 : `curl` 검증 만 으로 *PAT 가 *깨졌다* 라고 판단 하면 안 됨. *docker / kubelet 의 *실제 flow* 와 *다른 layer*. *진짜 검증 은 `docker pull`*.

---

## 3. *해결 — *즉시 조치*

### 3.1 *40 namespace 일괄 갱신*

```bash
NEW_PAT="ghp_Nl8V...DcOkK"
GH_USER="myoungsoo7"

for ns in $(kubectl get ns -o name | cut -d/ -f2 | grep -E '\-prod$|\-staging$'); do
  kubectl -n "$ns" create secret docker-registry ghcr-pull \
    --docker-server=ghcr.io \
    --docker-username=$GH_USER \
    --docker-password=$NEW_PAT \
    --dry-run=client -o yaml | kubectl apply -f -
done
```

→ *40 namespace 의 *ghcr-pull secret 일괄 교체*. `dry-run + apply` 로 *기존 있으면 갱신, 없으면 생성*.

### 3.2 *ImagePullBackOff pod 강제 재시작*

새 secret 이 *동일 이름* (`ghcr-pull`) 이라 *Deployment spec 변경 없음* → *자동 rolling update 안 일어남*. *수동 으로 *pod 삭제* 필요:

```python
# Python 으로 ImagePullBackOff pod 만 골라서 삭제
kubectl get pods -A -o json | python3 -c '
import sys, json, subprocess
data = json.load(sys.stdin)
for p in data["items"]:
    for cs in p["status"].get("containerStatuses", []):
        w = cs.get("state", {}).get("waiting", {})
        if w.get("reason") in ("ImagePullBackOff", "ErrImagePull"):
            ns = p["metadata"]["namespace"]
            name = p["metadata"]["name"]
            subprocess.run(["kubectl", "-n", ns, "delete", "pod", name, "--wait=false"])
            print(f"deleted {ns}/{name}")
            break
'
```

→ 13 pod 삭제 → ReplicaSet 가 *새 pod 생성* → *새 secret 으로 pull* → 정상 회복.

### 3.3 *예상치 못한 *2 차 문제 — logistic-prod***

10 pod 회복 됐는데 *logistic-prod 의 3 pod 는 여전히 ImagePullBackOff*:

```
console-app-9d68bff74-wlxvz       0/1   ImagePullBackOff
monitoring-service-56468c96c4-... 0/1   ImagePullBackOff
task-service-b57586756-fn6m9      0/1   ImagePullBackOff
```

에러 메시지 가 *다름*:
```
401 Unauthorized   <- *anonymous token* 시도
```

→ *anonymous*? 새 secret 적용 안 됐나? 확인:
```bash
kubectl -n logistic-prod get pod console-app-9d68bff74-wlxvz \
  -o jsonpath='{.spec.imagePullSecrets}'
# → (empty)
```

**원인 발견** : logistic-prod 의 *Deployment spec 자체 에 *imagePullSecrets 필드 없음*. *secret 은 namespace 에 있지만 *pod 가 *그것 을 *참조 하지 않음*. *anonymous pull 시도* → 401.

### 3.4 *ServiceAccount 패치 해결*

K8s 의 *기본 동작* : pod 의 imagePullSecrets 는 *자기 의 spec* 또는 *ServiceAccount 의 imagePullSecrets* 중 하나 라도 있으면 사용.

→ *default ServiceAccount* 에 *imagePullSecrets 추가* 하면 *그 namespace 의 *모든 pod* 가 *자동 적용*:

```bash
kubectl -n logistic-prod patch serviceaccount default \
  -p '{"imagePullSecrets":[{"name":"ghcr-pull"}]}'

# 모든 pod 재시작 (새 SA 정책 받기 위해)
kubectl -n logistic-prod delete pods --all
```

→ 즉시 회복. **logistic-prod 가 다른 namespace 와 *다른 점* 은 *처음부터 *default SA 패치 누락* 이었던 것**.

---

## 4. *Root cause — *왜 *이런 사고 가 *가능 했나*

### 4.1 *3 가지 누적 실패*

| 실패 | 결과 |
|---|---|
| **PAT 만료 모니터링 부재** | 토큰 만료 *알람 없음* — 사용자 가 *2 일 동안 모름* |
| **수동 분배 (git 추적 0)** | 40 namespace 의 secret 이 *언제 어떤 토큰 으로 *분산* 됐는지 *기록 없음* |
| **default SA 패치 누락 (logistic-prod)** | *체크리스트* 가 *문서화 안 됨* → *반복 가능 한 실수* |

→ **각자 *작은 누락* — 모이면 *2 일 outage*.

### 4.2 *cached image 의 *위장 효과*

> *클러스터 가 *건강 해 보이는 진짜 이유* 는 *우연 의 *image cache* 뿐*.

이건 *Observability 의 *진실*: *health check 가 *완벽 해도* *그 health 의 *전제 조건* 이 *우연* 이면 *안전 하지 않다*. 우리 의 311 pod 의 *대부분* 이 *그 우연 의 cache* 위에 *서 있었다*.

---

## 5. *재발 방지 — *3 패턴*

### 5.1 *패턴 1 — *SOPS + ArgoCD 자동 분배***

수동 `kubectl create` 의 *모든 문제 해결*:

```yaml
# helm-deploy/secrets/ghcr-pull.sops.yaml — *36 SopsSecret docs* 멀티 도큐먼트
apiVersion: isindir.github.com/v1alpha3
kind: SopsSecret
metadata:
  name: ghcr-pull
  namespace: academy-prod
spec:
  enforceOwnership: true
  secretTemplates:
    - name: ghcr-pull
      type: kubernetes.io/dockerconfigjson
      stringData:
        .dockerconfigjson: ENC[AES256_GCM, ...]   ← SOPS 암호화
---
apiVersion: isindir.github.com/v1alpha3
kind: SopsSecret
metadata:
  name: ghcr-pull
  namespace: jabis-prod
...
# (36 docs)
```

```yaml
# helm-deploy/argocd-applications/ghcr-pull-secrets.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: ghcr-pull-secrets
spec:
  source:
    path: secrets
    directory:
      include: 'ghcr-pull.sops.yaml'
  destination:
    server: https://kubernetes.default.svc
    namespace: argocd       # 형식적 (각 SopsSecret 이 자기 namespace 명시)
  syncPolicy:
    automated: { prune: false, selfHeal: true }
```

→ **PAT 갱신 시**:
```bash
sops secrets/ghcr-pull.sops.yaml   # 에디터 가 평문 으로 열림, 저장 시 자동 재암호화
git add -A && git commit -m "rotate ghcr PAT 2026-Q3" && git push
# ArgoCD 가 *36 namespace 동시* 갱신. 사람 손 0.
```

**얻은 것**:
- *git audit log* — 언제 누가 어떤 PAT 으로 갱신 했는지 *전부 기록*
- *Single source of truth* — *36 곳 의 *동일성* 자동 보장
- *Recovery 빠름* — 사고 시 *git revert* 한 줄 로 옛 secret 복원

### 5.2 *패턴 2 — *default ServiceAccount 자동 패치***

새 namespace 만들 때 *반드시* :
```bash
kubectl -n <new-ns> patch serviceaccount default \
  -p '{"imagePullSecrets":[{"name":"ghcr-pull"}]}'
```

**자동화 (미래 — Kyverno)** :
```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: add-imagepullsecret-to-default-sa
spec:
  rules:
    - name: add-pull-secret
      match:
        any:
          - resources:
              kinds: [ServiceAccount]
              names: [default]
              namespaces: ["*-prod", "*-staging"]
      mutate:
        patchStrategicMerge:
          imagePullSecrets:
            - name: ghcr-pull
```

→ 새 namespace 가 *만들어 지자 마자 *default SA 가 자동 패치*. *사람 가 잊을 일 없음*.

### 5.3 *패턴 3 — *Expiry 모니터링***

**Prometheus blackbox exporter** :
```yaml
# 매 분 마다 canonical image manifest 호출 — 401 = 알람
modules:
  http_ghcr_auth:
    prober: http
    http:
      method: HEAD
      headers:
        Authorization: "Basic <base64 of user:PAT>"
      valid_status_codes: [200, 404]   # 401 = fail
      preferred_ip_protocol: ip4

# Alert rule
- alert: GHCRAuthFailing
  expr: probe_http_status_code{job="ghcr-auth"} == 401
  for: 5m
  labels: { severity: critical }
  annotations:
    summary: "GHCR PAT 만료 가능성 — kubectl create secret docker-registry 검토"
```

→ *2 일 잠재* 대신 *5 분 안* 알람. *cached image 의 위장* 을 *우회*.

**또는 GitHub API 직접** :
```bash
# PAT 의 expiration 직접 조회
curl -H "Authorization: token $PAT" -I https://api.github.com/user
# → response header 의 `github-authentication-token-expiration` 확인
```

PrometheusRule + cron job 으로 *expiration 7 일 전 알람*. **PAT 만료 자체 가 *예방 가능 한 사건***.

---

## 6. *교훈 — *5 가지*

### 6.1 *Cache 는 *진실을 가린다*

> *Observability 의 health check 는 *health 의 *증거* 가 *아니다*. *그 health 의 *전제 조건* 도 *증명* 되어야 한다.

우리 의 311 정상 pod 는 *PAT 작동 의 증거 가 아니라* *image cache 의 증거*. *PAT 작동 검증* 은 *별도 probe* 가 필요.

### 6.2 *"수동 kubectl create" 는 *부채 다*

git 추적 없는 *kubectl 직접 명령* 은 *audit 0 + 동기화 0 + recovery 어려움*. *GitOps 라면 *git 안에 *암호화 라도 *기록* 해야*.

### 6.3 *Multi-step credential flow 의 *각 단계 검증*

GHCR 의 *Basic → Bearer → manifest* 의 *3 단계* 중 *어디서 깨졌는지* 모르면 *틀린 결론*. *docker login + docker pull* 이 *진짜 검증* (모든 단계 포함).

### 6.4 *Default ServiceAccount 는 *공기 같은 존재*

*명시 안 해도 작동 하는 듯 보이지만* *imagePullSecrets / automountServiceAccountToken / 등* 의 *기본값* 이 *프로덕션 의 보안 / 안정성 의 핵심*. *체크리스트* 화 의무.

### 6.5 *PAT 보다 *Fine-grained PAT 또는 *GitHub App***

GitHub PAT classic 은 *모든 repo 권한 한 번 에*. *Fine-grained PAT* 는 *특정 repo + 특정 scope*. *GitHub App* 은 *expiry 없음 + organization 단위 관리*. 클러스터 production credential 은 *App-installed* 가 *장기 적 답*.

---

## 7. *체크리스트 — *PAT / GHCR 관련*

내가 *production K8s + GHCR private image* 운영 시 *반드시 확인* 하는 *7 가지*:

1. *모든 -prod / -staging namespace 의 `default` ServiceAccount 에 `imagePullSecrets: [ghcr-pull]`* 패치 되어 있는가
2. *ghcr-pull secret 이 *git 안에 *SOPS 암호화* 되어 분배 되는가 (수동 kubectl create 아님)
3. *PAT 의 *expiration date* 가 *7 일 전 알람* 으로 모니터링 되는가
4. *PAT 가 *fine-grained* 또는 *GitHub App* 인가 (classic PAT 아님)
5. *blackbox exporter* 가 *ghcr.io manifest 401* 을 *5 분 안* 잡아내는가
6. *Kyverno (또는 webhook)* 로 *새 namespace 의 default SA 자동 패치*
7. *PAT 분실 / 누출 시 *즉시 revoke + 새 토큰 발급* 절차 가 *런북* 으로 *문서화* 되어 있는가

---

## 8. *결론 — *작은 누락 들 이 *대형 사고 의 *재료*

> *PAT 만료 자체 는 *5 분 fix*. 사고 의 진짜 무게 는 *2 일 잠재 의 시한폭탄 의 *발견 의 우연*.

오늘 정리한 *3 누적 실패* :
- *수동 분배* + *문서화 0* → *어디 가 무엇 으로 *분산* 됐는지 모름
- *모니터링 부재* → *2 일 동안 알람 0*
- *체크리스트 누락* → *logistic-prod 처럼 *처음부터 default SA 패치 빠짐*

*재발 방지 3 패턴* :
1. *SOPS + ArgoCD 분배* — git 추적 + audit log + recovery
2. *default ServiceAccount 패치* — pod spec 의 imagePullSecrets 빠져도 자동 적용
3. *Expiry 모니터링* — cached image 의 위장 우회

> *production K8s 에서 *"평화로워 보이는 클러스터"* 는 *대부분 의 경우* *기본기 의 *우연 한 성공* 이지 *설계 의 *증명* 이 아니다*. *그 우연 을 *체계적 으로 *증명* 하는 것 — *그게 *SRE 의 *진짜 일*.

*PAT 한 토큰* 의 *조용한 만료* 가 *2 일 후 13 pod* 를 죽일 수 있다. *그 만료 가 *3 일 전 알람* 으로 *예방 가능* 하다는 것 — *그 사실 을 *오늘 *체계화* 하는 게 *내일 의 평화*.

---

## *참고*

- *Kubernetes 공식 — Pull an Image from a Private Registry* : [kubernetes.io/docs/tasks/configure-pod-container/pull-image-private-registry](https://kubernetes.io/docs/tasks/configure-pod-container/pull-image-private-registry).
- *GitHub 공식 — Working with the Container registry* : [docs.github.com/en/packages/working-with-a-github-packages-registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry).
- *SOPS 공식* : [getsops.io](https://getsops.io).
- *sops-secrets-operator* (isindir) : [github.com/isindir/sops-secrets-operator](https://github.com/isindir/sops-secrets-operator).
- *Kyverno* — Kubernetes-native policy : [kyverno.io](https://kyverno.io).
- 자매편 :
  - [*보안 의 7 기둥*](/2026/06/20/security-7-pillars-auth-encryption-firewall-audit.html) — *시크릿 관리* 의 *원칙*
  - [*K8s 컨테이너 오케스트레이션*](/2026/06/20/kubernetes-container-orchestration-what-we-actually-use.html)
  - [*Prometheus + Grafana*](/2026/06/19/prometheus-grafana-metrics-visualization.html) — *블랙박스 모니터링*
