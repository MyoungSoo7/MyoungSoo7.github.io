---
layout: post
title: "GitOps 전문가의 시야 — 36개 Application 운영에서 드러나는 7가지 심화 주제"
date: 2026-05-19 23:30:00 +0900
categories: [infra, kubernetes, gitops, devops]
tags: [gitops, argocd, kubernetes, image-updater, sops, app-of-apps, sync-wave, reconciliation]
---
{% raw %}

GitOps 입문 글 두 편([App-of-Apps]({% post_url 2026-05-14-argocd-self-management-app-of-apps %}) · [docker-compose vs ArgoCD]({% post_url 2026-05-14-docker-compose-vs-k8s-argocd-gitops-comparison %}))을 쓴 뒤로 한 달 동안 5 노드 K3s 홈랩에서 **36개 ArgoCD Application** 을 운영했다. *"GitOps 가 좋아요"* 는 표면 결론. 그 아래로 내려가면 *"왜 이렇게 설계해야만 하는가"* 가 보이는 자리가 있다.

이 글은 그 자리들의 정리다. **GitOps 가 무엇인가** 가 아니라, *36개 앱을 reconciliation loop 에 맡기고 한 달 살아본 뒤 알게 된 7가지 함정과 패턴*. 입문 톤이 아니라 **운영자 톤**으로 간다.

> **이 글이 가정하는 독자**
> - ArgoCD 또는 Flux 로 최소 5~10개 앱 운영 경험
> - "git push 하면 클러스터에 반영된다" 정도는 이미 익숙
> - immutable field, sync hook, helm template 등 용어가 어색하지 않음

---

## TL;DR — 7가지 한눈에

| # | 주제 | 핵심 |
|---|---|---|
| 1 | Reconciliation 은 *트리거*가 아니라 *합의 상태(convergence)* 다 | git push → 즉시 반영은 환상. pull-based 의 본질을 이해해야 사고 모드를 잡는다 |
| 2 | `selfHeal` 과 `prune` 의 **비대칭(asymmetric)** 안전 | 28/36 앱이 `selfHeal:true, prune:false`. 의도된 비대칭이다 |
| 3 | image-updater **write-back 모드** — `git` vs `argocd` | 두 방식의 트레이드오프. 내가 `argocd` 를 고른 이유와 그 비용 |
| 4 | **Immutable field 충돌** — GitOps 가 막히는 9가지 자리 | StatefulSet selector, Service clusterIP, PVC storageClass… 손으로 풀어야 하는 자리들 |
| 5 | **Sync wave** — 의존성 있는 배포의 순서 보장 | root-app + Application CR + CRD + workload 의 cascade 순서 |
| 6 | **Secret in GitOps** — 3가지 접근법 비교 | sealed-secrets vs SOPS vs external-secrets. 내가 SOPS-operator 를 고른 이유 |
| 7 | **AppProject + RBAC** — 36개 앱을 한 project 에 두는 위험 | 멀티-테넌시가 없으면 한 PR 이 모든 앱을 destination 변경할 수 있다 |

---

## 1. Reconciliation 은 *트리거* 가 아니라 *합의 상태(convergence)*

가장 자주 오해되는 부분. *"git push 했는데 왜 아직 반영 안 됐어요?"* 라는 질문은 GitOps 의 본질을 잘못 짚는다.

ArgoCD 의 동작:

```
loop forever:
  for each Application:
    desired = git@<repoURL>:<path>@<targetRevision> 의 매니페스트 렌더링
    actual  = cluster 의 현재 상태
    diff    = compare(desired, actual)
    if diff != empty and syncPolicy.automated != null:
      apply(diff)
```

이 loop 은 기본 **3분 주기**(`timeout.reconciliation`) 로 돈다. webhook 을 안 걸어두면 git push 후 *최대 3분* 이 합법적인 지연 시간이다.

**중요한 사고 전환**: GitOps 는 *"git push → 클러스터 변경"* 이라는 인과 사슬이 아니라, *"git 의 상태 = 클러스터의 상태"* 라는 **합의(convergence)** 다. 시간차는 본질이지 결함이 아니다.

이걸 잘못 이해하면 다음 사고가 난다:

> 새벽에 hotfix 를 git push. 5분 뒤 *"왜 아직?"* 싶어서 `kubectl apply -f` 를 손으로 침. ArgoCD 가 그걸 *drift* 로 감지해서 다음 reconciliation 에 **롤백**. hotfix 가 사라짐.

**해결**:
- webhook 설정 (`POST /api/webhook` → git provider 가 push 시 알림)
- `argocd app sync <name>` 로 즉시 강제 (`--force`, `--prune` 신중히)
- 위 두 가지를 모두 안 쓸 거라면 *기다리는 게* 정답

---

## 2. `selfHeal` 과 `prune` 의 비대칭 안전

내 36개 Application 의 `syncPolicy.automated` 분포:

| selfHeal | prune | 앱 수 | 의도 |
|---|---|---:|---|
| **true** | **false** | 28 | 일반 앱: 손으로 만든 drift 는 즉시 되돌리지만, git 에서 사라진 리소스는 *남겨둠* |
| false | false | 6 | 위험한 앱(cost, dart, data, pilgrim, report 등): 모든 변경 수동 승인 |
| true | true | 1 | `cluster-ops`, `root-app`: 메타 관리 레이어 — 누락 = 의도된 삭제 |
| false | true | 1 | 거의 안 씀 |

**왜 28/36 이 비대칭(`selfHeal:true, prune:false`) 인가?**

- **`selfHeal:true`** = "누가 손으로 만든 변경(`kubectl edit`) 은 자동 롤백" — drift 방지
- **`prune:false`** = "git 에서 매니페스트 삭제해도 클러스터에서는 안 지움" — *사고 방지*

비대칭의 이유: **잘못된 추가는 사람이 만들고, 잘못된 삭제는 git diff 가 만든다.** 누가 PR 에서 ConfigMap 한 줄 지웠다고 PVC 까지 같이 삭제되면 데이터 유실. `prune:false` 가 그 안전벨트.

`prune:true` 가 합당한 자리:
- **App-of-Apps root**: Application CR 자체 라이프사이클은 git 이 진실. 거기 없으면 cluster 에서 진짜로 지워야 일관성.
- **cluster-ops**: NetworkPolicy/Quota 같은 가드. git 에서 제거 = "이 가드 해제 의도" 라고 명시.

> **함정**: `selfHeal:true, prune:true` 를 *모든* 앱에 적용하면, git 한 줄 실수가 production PVC 를 지운다. 절대 default 로 두지 말 것.

---

## 3. image-updater write-back: `git` vs `argocd`

내 36개 중 22개가 `argocd-image-updater` 로 새 컨테이너 이미지 자동 감지. ghcr.io 에 새 SHA 가 올라오면 Application 의 helm parameter `<image>.tag` 를 자동 갱신한다.

**write-back 방식 두 가지**:

### (a) `write-back-method: git`

```yaml
annotations:
  argocd-image-updater.argoproj.io/write-back-method: git
  argocd-image-updater.argoproj.io/git-branch: master
```

- 동작: 새 이미지 감지 → helm-deploy 레포에 `.argocd-source-<app>.yaml` 자동 커밋 → ArgoCD reconcile
- 장점: **git history 가 진실의 원천**. 누가 언제 어떤 이미지로 갔는지 git log 로 추적 가능. 진정한 GitOps.
- 단점: PR 폭증. 22개 앱이 매번 새 이미지 → 매번 커밋. 하루 50~100 commit. CI/PR 알림에 묻힘.

### (b) `write-back-method: argocd` (내 선택)

```yaml
annotations:
  argocd-image-updater.argoproj.io/write-back-method: argocd
```

- 동작: 새 이미지 감지 → Application CR `.spec.source.helm.parameters` **in-place 수정** → ArgoCD reconcile
- 장점: git history 깨끗. helm-deploy 레포는 *차트 변경* 만, 이미지 태그는 ArgoCD 내부 상태로.
- 단점: **Application spec 이 git 과 다른 상태가 됨**. App-of-Apps root 가 reconcile 할 때 그 in-place 수정을 *drift* 로 보고 되돌릴 위험.

### 함정 — App-of-Apps + write-back: argocd 충돌

root-app 이 `argocd-applications/asat-prod.yaml` 을 진실로 보고 `selfHeal:true` 로 돌면, image-updater 가 in-place 로 수정한 Application 의 `helm.parameters` 가 root-app 에 의해 매 분 *되돌려진다*.

**해결**: root-app 의 Application CR 정의에서 `helm.parameters` 를 *명시하지 않는다*. image-updater 가 추가하는 키가 root-app 의 차이로 잡히지 않게.

```yaml
# argocd-applications/asat-prod.yaml — root-app 이 보는 spec
spec:
  source:
    repoURL: https://github.com/MyoungSoo7/helm-deploy
    path: charts/asat
    helm:
      valueFiles: [values.yaml]
      # ⚠️ parameters: 절대 적지 말 것. image-updater 가 채울 자리.
```

내 22개 앱 모두 `write-back: argocd` 다. 이유: git history 클린이 하루 100 commit 노이즈보다 운영상 더 가치 있었음. 동일 결정을 다른 운영자가 할 필요는 없다 — 팀이 크고 audit 요구가 강하면 `git` 이 더 정통.

---

## 4. Immutable field 충돌 — GitOps 가 막히는 9가지 자리

`kubectl apply` 가 거부하는 필드들. GitOps 는 이 자리에서 멈춘다.

| # | 리소스 | 필드 | 변경 시 어떻게 풀까 |
|---|---|---|---|
| 1 | `Deployment` | `spec.selector.matchLabels` | delete + recreate. 다운타임 발생 |
| 2 | `StatefulSet` | `spec.selector` / `volumeClaimTemplates` | StatefulSet 만 삭제 (PVC 보존), 재생성 |
| 3 | `Service` | `spec.clusterIP` | NodePort/LB 도 신중. service 삭제+생성 |
| 4 | `Service` | `spec.type` (ClusterIP↔NodePort) | 일부 K8s 버전은 가능, 일부 거부 |
| 5 | `PVC` | `spec.storageClassName` | PV 만들고 PVC 만들기는 1회. expand 만 일부 가능 |
| 6 | `Job` | `spec.selector` / `spec.template` | Job 삭제 + 재생성. status 유실 |
| 7 | `CronJob` | `spec.jobTemplate.spec.template` (일부 필드) | CronJob 자체 재생성 |
| 8 | `Ingress` | `spec.ingressClassName` (구버전) | 1.18+ 에선 변경 가능 |
| 9 | `NetworkPolicy` | `spec.podSelector` | drop & recreate, 짧은 노출 윈도우 |

ArgoCD 의 대응 카드:

- **`Replace=true`** sync option: `kubectl replace --force` 로 동작. 다운타임 발생 가능.
- **`argocd.argoproj.io/sync-options: Replace=true`** annotation: 리소스별로 지정.
- **`PreSync` hook**: 변경 전 백업/마이그레이션.
- **`PostSync` hook**: 변경 후 검증/스모크 테스트.

내 운영 사례: `asat-postgres` StatefulSet 의 `volumeClaimTemplates` 변경이 필요했을 때 — git 에서 차트만 바꾸면 *sync failed* 가 나고 끝. 결국 **수동 절차**:

```bash
# 1. PVC 데이터 백업
kubectl -n asat-prod exec asat-postgres-0 -- pg_dump ... > backup.sql

# 2. StatefulSet 만 삭제 (PVC 는 cascade orphan 으로 보존)
kubectl -n asat-prod delete sts asat-postgres --cascade=orphan

# 3. git push (차트 변경)
git push  # ArgoCD 가 새 StatefulSet 만듦

# 4. PVC 재바인딩 확인 / 복구
```

**GitOps 의 정직한 한계**: 모든 변경이 git push 만으로 풀리지는 않는다. *"손으로 풀어야 하는 자리"* 의 목록을 미리 알아두는 게 운영 성숙도.

---

## 5. Sync wave — 의존성 있는 배포 순서 보장

순서가 중요한 경우:

- CRD 먼저 → 그 CRD 를 쓰는 리소스
- DB Job 먼저 → app Deployment
- NetworkPolicy 먼저 → 보호받을 pod
- root Application 먼저 → child Application

ArgoCD 의 도구: `argocd.argoproj.io/sync-wave` annotation. 정수, 낮을수록 먼저.

```yaml
# CRD 먼저
metadata:
  annotations:
    argocd.argoproj.io/sync-wave: "-10"
---
# Application CR (CRD 가 있어야 valid)
metadata:
  annotations:
    argocd.argoproj.io/sync-wave: "0"
---
# Workload
metadata:
  annotations:
    argocd.argoproj.io/sync-wave: "10"
```

내 root-app 의 `argocd-applications/*.yaml` 에서 실제 사용:
- `-10`: AppProject, ConfigMap 같은 메타
- `0`: 일반 Application
- `1~2`: 의존하는 후속 (e.g., monitoring 이 namespace 생성 후 sync 되어야 하는 elastic 같은 친구)

**함정**: sync-wave 는 *Sync 호출 단위* 안에서만 순서를 보장한다. 다른 Application 끼리의 순서를 보장하지 않는다 (Application 간엔 ArgoCD 가 병렬 처리). 정말 강한 순서 보장이 필요하면 **Application Health gate** + 후속 Application 의 `dependsOn` (ArgoCD 2.10+ ApplicationSet) 또는 sync hooks 로.

---

## 6. Secret in GitOps — 3가지 접근법

git 은 평문 저장소. *"git 에 secret 넣지 마라"* 가 기본 진리. 하지만 GitOps 는 *"모든 게 git 에"* 가 원칙. 충돌.

해결책 3가지:

### (a) sealed-secrets (Bitnami)
- 클러스터 안의 controller 가 가진 private key 로 복호화
- git 에는 암호화된 `SealedSecret` CR 저장
- 장점: 단순, K8s native. 클러스터 키만 안전하면 됨.
- 단점: **클러스터 이전 시 키 같이 옮겨야 함**. multi-cluster 분산 키 관리 까다로움.

### (b) SOPS (Mozilla)
- AWS KMS / GCP KMS / age / PGP 로 부분 암호화. yaml/json 의 *값만* 암호화 (키는 평문).
- git diff 가 *어떤 키가 바뀌었는지*는 보임. 값은 안 보임.
- 장점: 키 관리가 외부 KMS 로 위임. multi-cluster 친화적.
- 단점: 운영에 SOPS-operator 같은 도구가 필요. 학습 곡선.

### (c) external-secrets (External Secrets Operator)
- secret 본문은 **외부 vault** (HashiCorp Vault, AWS Secrets Manager) 에. git 엔 *참조* 만.
- 장점: secret rotation 자동. audit 강함.
- 단점: 외부 vault 의존성. 홈랩 단독 운영엔 과함.

### 내 선택과 이유 — SOPS-operator

3일 전(2026-05-15) `sops-operator` 를 도입했다. 이유 3가지:

1. **K3s 홈랩 = 외부 KMS 없음, age 키만으로 운영 가능**. sealed-secrets 처럼 클러스터 키에 묶이지 않음.
2. **multi-cluster 백업 시나리오**: lemuel 노드 망가져도 age 키만 안전하면 어디서나 복호화.
3. **git diff 가 의미 있음**: SealedSecret 은 매번 전체 ciphertext 가 바뀌어서 *어떤 키가 바뀌었는지* 가 안 보임. SOPS 는 키별 부분 암호화라 *어떤 키가 회전됐는지* 가 diff 에 명시.

helm-deploy 레포에 `charts/<app>/secrets.sops.yaml` 형태로 커밋, sops-operator 가 `SopsSecret` CRD 감지 → 클러스터에 `Secret` 자원 생성. 평문 secret 은 클러스터 안에만, git 엔 ciphertext 만.

```yaml
# charts/asat/templates/sops-secret.yaml — 예
apiVersion: isindir.github.com/v1alpha3
kind: SopsSecret
metadata:
  name: asat-app-sopssecret
spec:
  secretTemplates:
    - name: asat-app-secret
      stringData:
        JWT_SECRET: ENC[AES256_GCM,data:...]
        ASAT_INTERNAL_SERVICE_TOKEN: ENC[AES256_GCM,data:...]
```

> ⚠️ **운영 메모**: 2026-05-18 점검에서 sops-operator pod 가 34회 재시작 흔적. logs 는 reconcile 정상. OOM 가능성 — describe pod 로 lastState 확인 권장. *"secret 도구 자체"* 의 안정성은 별도 monitoring 항목으로 잡아야 한다.

---

## 7. AppProject + RBAC — 36개 앱을 한 project 에 두는 위험

ArgoCD 의 `AppProject` 는 멀티-테넌시 경계. 그러나 — 부끄럽게도 — 내 클러스터는 36개 앱이 모두 `project: default` 다.

`default` project 의 기본값:

```yaml
spec:
  sourceRepos: ['*']
  destinations:
    - namespace: '*'
      server: '*'
```

**무엇이 문제인가**:

- 어떤 Application 도 *어떤 git repo* 든 source 로 지정 가능
- 어떤 Application 도 *어떤 namespace* 든 destination 으로 지정 가능

= 누가 PR 로 `argocd-applications/asat-prod.yaml` 의 destination namespace 를 `kube-system` 으로 바꾸면, root-app 이 자동 sync 해서 ASAT 컨테이너가 kube-system 에 뜬다. 그리고 그게 dangerous workload 라면 클러스터 컨트롤 플레인을 침해할 수 있다.

**제대로 된 multi-tenant 설계**:

```yaml
# argocd-projects/asat.yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: asat
  namespace: argocd
spec:
  sourceRepos:
    - https://github.com/MyoungSoo7/helm-deploy  # asat 가 갈 수 있는 repo
  destinations:
    - namespace: asat-prod                        # asat 가 갈 수 있는 ns
      server: https://kubernetes.default.svc
    - namespace: asat-staging
      server: https://kubernetes.default.svc
  clusterResourceWhitelist:  # cluster-scoped 자원 제한
    - group: ''
      kind: Namespace
  namespaceResourceBlacklist:  # 위험 자원 차단
    - group: 'rbac.authorization.k8s.io'
      kind: 'ClusterRoleBinding'
  roles:
    - name: dev
      policies:
        - p, proj:asat:dev, applications, sync, asat/*, allow
        - p, proj:asat:dev, applications, get, asat/*, allow
      groups:
        - asat-developers
```

이러면:
- asat AppProject 의 Application 은 `helm-deploy` 외 다른 repo source 불가
- destination 은 asat-prod / asat-staging 두 ns 만
- ClusterRoleBinding 같은 위험 자원 sync 차단
- `asat-developers` 그룹은 asat 앱만 sync 가능

내 36개를 이렇게 갈라야 한다는 걸 알면서도 아직 안 했다. 이유는 *"홈랩 운영자 = 나 혼자"* 라서 RBAC 의 가치가 적음. 하지만 *블라스트 반경(blast radius)* 측면에선 default project 는 위험. 이 글 쓰면서 *"이번 주 안에는 갈라야겠다"* 결심.

---

## 마무리 — GitOps 의 성숙도 곡선

GitOps 입문 시 만난 *"git push 하면 자동 반영, 멋지다"* 의 단계가 있다. 그 다음에 *"근데 왜 안 반영되지?"* 가 오고, 그 다음에 *"selfHeal 이 작년에 만든 PVC 를 지웠다"* 같은 사고로 한 번 부딪힌다.

이 글의 7가지는 그 부딪힘에서 추출한 정수다. 정리하면:

1. **Reconciliation 은 합의 상태다** — 즉시 반영 환상 버리기
2. **selfHeal/prune 비대칭** — 잘못된 추가는 사람이, 잘못된 삭제는 git diff 가
3. **image-updater write-back** — git history 클린 vs PR 폭증의 트레이드오프
4. **Immutable field** — 모든 변경이 git push 로 풀리지 않는다
5. **Sync wave** — 순서가 필요한 곳에 명시적 의존성
6. **Secret 처리** — sealed-secrets / SOPS / external-secrets 중 운영 환경에 맞게
7. **AppProject** — 36개를 한 default 에 두지 마라

GitOps 는 *"매니페스트를 git 에 두자"* 가 아니라 **"클러스터 상태를 합의 가능한 데이터로 표현하자"** 다. 입문 단계의 *"빠르다, 편하다"* 가 운영 단계의 *"정직하다, 추적 가능하다"* 로 진화한다. 그리고 그 진화의 마디마다 위 7개가 있다.

다음 글에서는 *"ArgoCD ApplicationSet 으로 root-app 을 다음 단계로"* 와 *"GitOps + Progressive Delivery (Argo Rollouts)"* 를 다뤄볼 예정.

---

## 참고

- [ArgoCD 자체를 GitOps 로 셀프 관리 — App-of-Apps 패턴]({% post_url 2026-05-14-argocd-self-management-app-of-apps %}) — 본 글의 #5, #7 의 기반
- [Docker Compose vs ArgoCD GitOps]({% post_url 2026-05-14-docker-compose-vs-k8s-argocd-gitops-comparison %}) — 본 글의 #4 immutable field 사례가 거기 settlement V22 와 동일 카테고리
- [K3s 홈랩 하루치 운영기]({% post_url 2026-05-17-elk-modernization-etcd-stability-eck-crashloop-deepdive %}) — sync-wave 와 sops-operator 실전 도입 기록
- [ArgoCD Best Practices (공식)](https://argo-cd.readthedocs.io/en/stable/operator-manual/best_practices/)
- [SOPS](https://github.com/getsops/sops) / [sops-secrets-operator](https://github.com/isindir/sops-secrets-operator)

{% endraw %}
