---
layout: post
title: "쿠버네티스 운영 함정 4가지 — 하룻밤 디버깅 노트"
date: 2026-05-16 03:00:00 +0900
categories: [infra, kubernetes]
tags: [kubernetes, k3s, argocd, gitops, eck, flannel, troubleshooting, postmortem]
---

5/15 저녁 텔레그램 알림으로 시작된 한 통의 메시지 — *"⚠️ Pod 132개 중 4개 CrashLoopBackOff"*. 이 한 줄에서 출발해 자정 넘어까지 4가지 서로 다른 종류의 함정에 빠졌다 빠져나왔다. 각각의 함정이 K3s/K8s 운영하는 사람이라면 한 번쯤은 만나는 패턴이라 정리해둔다.

> 이 글에서 다루는 것
> - **함정 1**: GitOps selfHeal이 `kubectl patch`를 조용히 되돌린다 (가장 빈번)
> - **함정 2**: scheduler의 "Insufficient memory" 메시지는 거짓말일 수 있다 (가장 헷갈림)
> - **함정 3**: 옛 systemd 서비스 잔재가 CNI overlay를 죽인다 (가장 치명적)
> - **함정 4**: 이미지에 박힌 config는 멀티 환경에서 깨진다 (가장 반복적)
> - 각 함정의 증상·진단·해결 + 운영자가 들여야 할 습관

---

## TL;DR — 4가지 함정 한눈에

| # | 함정 | 증상 | 진단 키 | 처음 마주칠 확률 |
|---|---|---|---|---|
| 1 | **ArgoCD selfHeal 되돌림** | kubectl patch가 1초 후 원복 | `metadata.annotations.argocd.argoproj.io/tracking-id` | 매우 높음 |
| 2 | **scheduler 거짓말** | "Insufficient memory"인데 사실 nodeSelector 문제 | `kubectl describe pod \| grep Node-Selectors` | 높음 |
| 3 | **중복 systemd 서비스** | 같은 노드에서 `k3s.service` + `k3s-agent.service` 동시 가동 | `systemctl list-units 'k3s*'` | 중간 (전환 시) |
| 4 | **이미지 박힌 config** | prod OK, staging 죽음 | `kubectl logs ... \| grep "host not found"` | 매우 높음 |

---

## 함정 1 — GitOps selfHeal이 patch를 조용히 되돌린다

가장 헷갈리고 가장 빈번한 함정. **증상은 "고쳤는데 안 고쳐졌다"**.

### 시나리오

```bash
# Elasticsearch warm tier를 louise → ilwon으로 옮기려고 patch
kubectl -n logging patch elasticsearch logs --type=json \
  -p='[{"op":"replace","path":"/spec/nodeSets/1/podTemplate/spec/nodeSelector",
        "value":{"kubernetes.io/hostname":"ilwon"}}]'
# → elasticsearch.elasticsearch.k8s.elastic.co/logs patched ✓

# 1초 뒤 확인
kubectl -n logging get elasticsearch logs -o jsonpath='{.spec.nodeSets[1].podTemplate.spec.nodeSelector}'
# → {"kubernetes.io/hostname":"louise"}   ← ?!?!
```

이 리소스를 ArgoCD가 GitOps로 관리하고 있으면 `selfHeal: true` 가 *자동으로 git 상태로 되돌린다.* `kubectl edit` 도, helm `upgrade --install` 도, 모든 manual 변경이 사라진다. 로그도 안 남고, 에러도 안 뜬다.

### 진단

리소스 annotation을 본다:

```bash
kubectl -n logging get elasticsearch logs -o jsonpath='{.metadata.annotations}'
# → {"argocd.argoproj.io/tracking-id":"elk-cluster:elasticsearch.k8s.elastic.co/Elasticsearch:logging/logs", ...}
```

`argocd.argoproj.io/tracking-id` 가 박혀있으면 GitOps 관리 대상.

해당 ArgoCD app의 syncPolicy를 본다:

```bash
kubectl -n argocd get application elk-cluster -o jsonpath='{.spec.syncPolicy}'
# → {"automated":{"prune":false,"selfHeal":true}, ...}
```

`selfHeal: true` = 변경 즉시 원복. 이건 GitOps 도입한 클러스터의 **기본 가정**이다.

### 해결

선택지 3가지:

1. **(정도)** git 레포에서 고치고 push → ArgoCD가 sync. **이게 답이다.** GitOps의 존재 이유.
2. **(임시)** `selfHeal: false` 로 잠시 끄고 patch. 다시 켜기 전에 git 동기화 필수. 권장 안 함 — 사람이 까먹는다.
3. **(부분)** ArgoCD `ignoreDifferences` 로 특정 필드만 selfHeal 제외. 운영용 라벨/replica 같은 것에만 사용.

이번에는 1번. helm-deploy 레포의 `charts/elk-cluster/values.yaml` 에서 `warm.nodeHostname: louise → ilwon` 한 줄 바꿔 push. 30초 후 ArgoCD가 sync해서 STS가 갱신됐다.

### 운영 습관

> **kubectl로 변경할 때 관리 주체부터 확인하라.**
> annotation에 `argocd.argoproj.io/tracking-id` 또는 `app.kubernetes.io/managed-by: Helm` 이 있으면, 그 변경은 1초 후 사라진다.

---

## 함정 2 — Scheduler의 "Insufficient memory"는 거짓말일 수 있다

scheduler가 친절한 척 거짓말한다.

### 시나리오

ECK CRD를 git으로 patch해서 warm tier nodeSelector를 louise → ilwon 으로 바꿨다. 그런데 pod는 여전히 Pending:

```
FailedScheduling: 0/5 nodes are available:
  1 Insufficient memory,
  1 node(s) had untolerated taint(s),
  3 node(s) didn't match Pod's node affinity/selector.
```

ilwon은 메모리 11Gi 여유. pod는 4Gi 요청. **분명히 들어가는데** "Insufficient memory" 라고 한다.

### 진단

핵심 질문: *지금 scheduler가 어떤 node에 배치하려고 시도 중인가?*

```bash
kubectl -n logging describe pod logs-es-warm-0 | grep Node-Selectors
# → Node-Selectors:  kubernetes.io/hostname=louise   ← 여기!
```

CRD는 ilwon으로 바꿨지만 STS template 갱신이 누락됐고, pod는 여전히 louise로 nodeSelector를 들고 있었다. 그래서:

- "1 Insufficient memory" → louise (matches selector, 메모리 부족)
- "3 didn't match selector" → david/ilwon/solomon (selector mismatch)
- "1 untolerated taint" → lemuel (control-plane taint)

scheduler는 *"louise에 메모리 부족"* 이라고 정확히 말했지만, 사람은 *"내가 ilwon으로 옮겼는데?"* 라고 받아들인다. 메시지의 주어가 누락된 셈.

### 해결

STS rollout 강제:

```bash
kubectl -n logging delete pod logs-es-warm-0      # ECK가 새 template으로 재생성
```

확인:

```bash
kubectl -n logging get sts logs-es-warm -o jsonpath='{.status.currentRevision}{"\n"}{.status.updateRevision}{"\n"}'
# → 두 줄이 같으면 rollout 완료
```

### 운영 습관

> **"Insufficient memory" 봤을 때 진짜 메모리 보지 말고, 어느 노드 얘기인지부터 보라.**
> CRD/Deployment patch 후엔 `kubectl describe pod | grep Node-Selectors` 로 *지금 pod*의 selector를 확인. operator가 아직 STS template을 갱신 안 했으면 옛 선택자로 시도 중.

---

## 함정 3 — 옛 systemd 서비스 잔재가 CNI overlay를 죽인다

가장 무서운 함정 — 노드는 `Ready` 인데 cross-node 통신만 안 된다.

### 시나리오

solomon 노드에 4개 pod가 CrashLoopBackOff. 다 DNS 의존 (`kubernetes.default.svc`, `settlement-staging-postgres` 등). 표면적으론 DNS 문제 같은데 노드 상태는 멀쩡:

```
NAME      STATUS   ROLES                AGE
solomon   Ready    control-plane,etcd   5d3h
```

진단해보면:

| 테스트 | 결과 |
|---|---|
| ilwon pod → DNS | ✅ 정상 |
| solomon pod → 같은 solomon pod | ✅ 정상 |
| solomon pod → ilwon pod (cross-node) | ❌ ping 100% loss |
| solomon pod → ClusterIP | ❌ timeout |

→ solomon에서 cross-node 패킷이 안 나간다. **flannel VXLAN 터널 단절.**

### 진단 깊이

solomon SSH 들어가서:

```bash
ip -d link show flannel.1
# → Device "flannel.1" does not exist.
```

flannel 인터페이스 자체가 없다. 누가 죽이고 있나?

```bash
systemctl list-units --type=service --all 'k3s*' --no-pager
#   k3s-agent.service  loaded activating auto-restart       ← !!!
#   k3s.service        loaded activating start        start ← !!!

sudo journalctl -u k3s-agent -n 30
# → fatal msg="Error: flag provided but not defined: -cluster-dns"
```

진실: solomon이 옛날에 worker였을 때 `k3s-agent.service` 가 있었고, 나중에 control-plane으로 승격되면서 `k3s.service` 가 추가됐다. **두 서비스가 같은 kubelet/containerd 자원을 두고 충돌**. agent가 무한 재시작하면서 flannel.1 인터페이스를 깜빡깜빡 내려버렸다. 게다가 agent의 systemd unit엔 옛 K3s 버전이 쓰던 `-cluster-dns` 플래그가 박혀있어 새 K3s 바이너리가 못 인식.

### 해결

```bash
sudo systemctl disable --now k3s-agent.service
# → 8초 후
ip -d link show flannel.1
# → flannel.1: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1450 ...
#   vxlan id 1 local <internal-ip> dev wlp3s0b1 srcport 0 0 dstport 8472
```

cross-node ping 부활. 4개 CrashLoopBackOff pod 자동 복구.

### 운영 습관

> **노드 역할 변경(worker → control-plane, 또는 반대) 후엔 systemd 서비스 잔재를 반드시 정리하라.**
> K3s에서 control-plane node는 `k3s.service` 만 있어야 한다 (server가 agent 기능 포함). worker는 `k3s-agent.service` 만. 둘 다 활성화돼있으면 CNI가 깜빡깜빡 죽는다. 노드가 `Ready` 상태여도 마찬가지.

---

## 함정 4 — 이미지에 박힌 config는 멀티 환경에서 깨진다

전형적인 패턴. **prod에선 OK, staging에선 부팅 실패.**

### 시나리오

`settlement-staging-frontend`가 11번 재시작:

```
nginx: [emerg] host not found in upstream "settlement-app" in /etc/nginx/conf.d/nginx.conf:23
```

nginx 이미지의 nginx.conf에 upstream이 `settlement-app:8080` 으로 하드코드. prod에서는 release 이름이 `settlement` 라 service명이 `settlement-app` → 일치. 하지만 staging은 release명이 `settlement-staging` 이라 service명은 `settlement-staging-app` → host not found.

### 해결 — 이미지 재빌드 vs ConfigMap mount

| 방법 | 시간 | 위험 |
|---|---|---|
| 이미지 재빌드 | 5~10분 (CI) + ArgoCD pickup | 빌드 실패 가능, latest 태그면 imagePullPolicy 주의 |
| **ConfigMap mount** | 즉시 (helm sync 30초) | 없음 — chart 변경만 |

helm chart에서 release 이름 기반 ConfigMap 주입:

```yaml
{% raw %}{{- if .Values.frontend.enabled }}
apiVersion: v1
kind: ConfigMap
metadata: { name: {{ .Release.Name }}-frontend-nginx }
data:
  nginx.conf: |
    server {
        listen 80;
        location ~ ^/(api|admin|...)/  {
            proxy_pass http://{{ .Release.Name }}-app:8080;   # ← release-scoped
        }
        location / { try_files $uri $uri/ /index.html; }
    }
{{- end }}{% endraw %}
```

Deployment에서 mount:

```yaml
{% raw %}volumeMounts:
  - name: nginx-conf
    mountPath: /etc/nginx/conf.d/nginx.conf
    subPath: nginx.conf
volumes:
  - name: nginx-conf
    configMap:
      name: {{ .Release.Name }}-frontend-nginx
{% endraw %}```

Pod template annotation에 ConfigMap checksum 박아두면 ConfigMap 변경 시 자동 rollout:

```yaml
{% raw %}annotations:
  checksum/nginx-conf: {{ include (print $.Template.BasePath "/frontend-configmap.yaml") . | sha256sum }}
{% endraw %}```

prod 렌더 → `settlement-app:8080`, staging 렌더 → `settlement-staging-app:8080`. 한 이미지로 둘 다 동작.

### 운영 습관

> **환경 의존 값(service name, hostname, region 등)은 이미지에 박지 말고 차트의 ConfigMap/env로 주입하라.**
> 특히 `{% raw %}{{ .Release.Name }}{% endraw %}` 기반으로 만들면 멀티 환경 배포에서 자동으로 갈라진다. 한 번 만들어두면 환경 추가할 때 0줄 변경.

---

## 보너스 함정 — fail2ban이 운영자 본인을 차단한다

SSH 들어갈 때 사용자명을 모르면 root, ubuntu, pi, debian, admin... 이렇게 probe하기 쉬운데 — **fail2ban 기본 설정이 5번 실패 후 IP를 10분 차단한다.**

이번에 6번 시도 후 마지막 `solomon@` 한 번 성공했지만, 직후부터 SSH가 *"Connection refused"* 로 막혔다. 10분 기다려서 풀렸다.

> **운영 노드 SSH 사용자명은 README든 메모든 손 닿는 곳에 기록해두라.** "한 번 시도해보면 되겠지"는 fail2ban이 있는 환경에선 비싸다.

---

## 마무리 — 4가지 함정 종합 점검표

다음에 비슷한 incident 만나면 이 순서로 본다:

1. **변경했는데 반영 안 됨?** → annotation에 `argocd.argoproj.io/tracking-id` 있는지부터 확인
2. **scheduler 에러가 뭔가 이상?** → `kubectl describe pod | grep Node-Selectors` 로 *지금 pod*의 selector 확인 (CRD가 아니라)
3. **노드 Ready인데 통신 안 됨?** → `systemctl list-units 'k3s*'` 로 service 중복 확인, `ip link` 로 CNI 인터페이스 살아있는지 확인
4. **한 환경만 죽음?** → 이미지에 환경 의존 값 박혀있는지 logs로 확인 (`host not found`, `connection refused on hardcoded host` 등)

K3s 홈랩이든 회사 EKS든 — *문제는 보통 가장 평범한 곳에서 가장 평범한 이유로 터진다.* GitOps annotation, scheduler 메시지의 주어, systemd unit 잔재, 이미지에 박힌 hostname. 이 4가지만 머리에 두고 있으면 한밤중 incident에서 30분은 절약된다.

> **TL;DR** — 오늘 4시간 디버깅으로 배운 것: scheduler를 의심하기 전에 STS template을 의심하라, ArgoCD selfHeal을 의심하기 전에 annotation을 보라, CNI를 의심하기 전에 systemd를 보라, 이미지를 의심하기 전에 환경 차이를 보라.
