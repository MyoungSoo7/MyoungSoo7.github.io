---
layout: post
title: "ArgoCD 자체를 GitOps 로 셀프 관리 — App-of-Apps 패턴 실전"
date: 2026-05-14 01:30:00 +0900
categories: [infra, kubernetes, gitops, devops]
tags: [argocd, app-of-apps, gitops, kubernetes, helm, self-heal]
---

ArgoCD 로 30 개 서비스를 GitOps 운영하다 보면 자연스러운 질문이 생깁니다. **"ArgoCD 자신의 Application CR 들은 누가 관리하지?"** 새 서비스 하나 추가할 때마다 `kubectl apply -f argocd-applications/foo.yaml` 을 손으로 치고 있다면, 그건 GitOps 가 아니라 그냥 git + kubectl 입니다.

이 글은 **App-of-Apps 패턴** 으로 ArgoCD 자신을 부트스트랩 1 회 후 완전 자율화시킨 실전 기록입니다. 5 노드 K3s 홈랩에서 30 개 Application CR 을 1 개의 root Application 으로 cascade 관리하는 구조를 1 시간만에 적용한 후 한 달 운영해본 결과입니다.

> 이 글에서 다루는 것
> - "ArgoCD Application 의 stale spec 문제" 가 왜 발생하는지
> - App-of-Apps 의 정확한 메커니즘 (recurse, prune, selfHeal 의 cascade)
> - 부트스트랩 1 회 = 그 다음부터 git push 만으로 앱 추가/삭제
> - selfHeal 적용 시 immutable 필드 충돌 함정 (실전 사례 포함)
> - root-app 자체의 self-reference 무한루프를 피하는 방법

---

## 1. 문제 — Application CR 도 결국 손으로 apply 해야 한다

ArgoCD 의 핵심은 `Application` CR 입니다. 각 서비스마다 하나씩 만들어서 "어떤 git repo 의 어떤 path 를 어떤 namespace 에 sync 할지" 를 선언합니다.

```yaml
# argocd-applications/sns-prod.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: sns-prod
  namespace: argocd
spec:
  source:
    repoURL: https://github.com/MyoungSoo7/helm-deploy
    path: charts/sns
    targetRevision: master
  destination:
    server: https://kubernetes.default.svc
    namespace: sns-prod
  syncPolicy:
    automated: { prune: false, selfHeal: true }
```

그런데 이 Application CR 자체는 git 으로 추적되어도, **클러스터에 적용시키는 행위는 수동** 입니다.

```bash
# 새 서비스 추가
git add argocd-applications/new-service.yaml
git commit -m "add new-service"
git push

# 그리고 이걸 안 하면 클러스터에는 아무 일도 안 일어남
kubectl apply -f argocd-applications/new-service.yaml
```

여기서 두 가지 문제가 생깁니다.

**문제 1 — 추가/삭제만이 아니라 수정도 stale 됩니다.**

git 의 `argocd-applications/sns-prod.yaml` 에서 `selfHeal: false → true` 로 바꾸고 push 만 했다고 가정합시다. ArgoCD 는 자기 자신의 Application CR 을 watch 하지 않으므로, 클러스터의 `sns-prod` Application 은 여전히 `selfHeal: false` 입니다. `kubectl apply -f` 를 안 친 만큼 git 과 실제가 어긋납니다.

저는 이걸 한 달간 모르고 `monitoring-prod` 에 `extraArgs` 를 git 에 추가했다가 Prometheus 가 안 받아먹는 이상한 디버깅을 30 분 했습니다. argocd-applications spec 이 stale 됐다는 걸 깨닫고 `kubectl apply -f argocd-applications/monitoring-prod.yaml` 한 번 치니 즉시 됐습니다.

**문제 2 — 30 개 앱을 관리하면 누가 어떤 걸 apply 했는지 추적 불가.**

30 개 Application CR + 빈번한 spec 변경 = 누가 무엇을 apply 했는지 추적 안 됨. git history 와 클러스터 실제 상태 간 신뢰 관계가 깨집니다.

---

## 2. 해법 — App-of-Apps 패턴

ArgoCD 가 자기 자신의 `argocd-applications/` 디렉토리를 watch 하게 만드는 패턴입니다. 모든 Application CR 을 관리하는 **상위 Application** 하나를 만들고, 그것만 한 번 수동 apply 합니다.

```yaml
# root-app.yaml — 1 회만 kubectl apply
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: root-app
  namespace: argocd
  finalizers: []   # root 삭제 시 자식 cascade 삭제는 안전 안정화 후
spec:
  project: default
  source:
    repoURL: https://github.com/MyoungSoo7/helm-deploy
    targetRevision: master
    path: argocd-applications
    directory:
      recurse: true   # 하위 디렉토리까지
  destination:
    server: https://kubernetes.default.svc
    namespace: argocd
  syncPolicy:
    automated:
      prune: true       # 파일 삭제 시 해당 Application 자동 삭제
      selfHeal: true    # 누가 직접 edit 하면 git 상태로 복원
    syncOptions:
      - CreateNamespace=false
      - ApplyOutOfSyncOnly=true
      - ServerSideApply=true   # CRD 의 큰 annotation 회피
```

부트스트랩:

```bash
kubectl apply -f root-app.yaml
```

이게 전부입니다. 이후 운영 흐름은 이렇게 됩니다.

| 작업 | 절차 |
|---|---|
| 새 서비스 추가 | `argocd-applications/new.yaml` git push → root-app 이 새 Application 자동 생성 |
| Application spec 수정 (selfHeal flip 등) | git push → root-app 이 자동 patch |
| 서비스 폐기 | 파일 삭제 + git push → `prune: true` 가 Application 삭제 |
| 누가 실수로 kubectl edit | `selfHeal: true` 가 git 상태로 즉시 복원 |

이제 클러스터 상태는 **git 의 `argocd-applications/` 디렉토리와 1:1** 입니다. `kubectl apply` 가 사라집니다.

---

## 3. recurse / prune / selfHeal 의 cascade

App-of-Apps 의 핵심은 root Application 의 syncPolicy 가 **자식 Application CR 의 lifecycle 만** 관리한다는 점입니다. 자식 Application 의 syncPolicy 는 **자식이 가리키는 실제 워크로드** 의 lifecycle 을 관리합니다. 2 단 cascade 입니다.

```
root-app (syncPolicy: prune=true, selfHeal=true)
    │
    ├─ sns-prod (syncPolicy: prune=false, selfHeal=true)
    │     │
    │     └─ Deployment sns, Service sns, Ingress sns, …
    │
    ├─ academy-prod (syncPolicy: prune=false, selfHeal=true)
    │     │
    │     └─ Deployment academy-admin, …
    │
    └─ infra-ssd (syncPolicy: prune=false, selfHeal=true)
          │
          └─ PV ssd-asat-postgres, PVC asat-postgres-data, …
```

이 분리가 중요합니다. 예를 들어:

- **root-app.prune: true** → `argocd-applications/sns-prod.yaml` 삭제 시 `sns-prod` Application CR 자체가 사라짐. 하지만 sns-prod 가 만든 워크로드 (Deployment 등) 는 sns-prod 의 prune 설정이 false 면 살아있음. 이게 안전장치.
- **sns-prod.prune: false** → git 에서 Deployment 정의를 지워도 클러스터에서 자동 삭제 안 됨. PV/PVC 같은 데이터 자원에 특히 중요.
- **selfHeal cascade** → 누가 `argocd-applications/sns-prod.yaml` 의 spec 을 kubectl edit 으로 바꾸면 root-app 이 git 으로 복원. 누가 sns Deployment replicas 를 직접 바꾸면 sns-prod 가 git 으로 복원.

`recurse: true` 는 `argocd-applications/sub-team/foo.yaml` 같은 중첩 디렉토리도 따라가게 합니다. 팀별로 디렉토리 분리할 때 유용.

---

## 4. 부트스트랩 시 주의 — annotation size error

처음 `kubectl apply -f root-app.yaml` 할 때 자식 Application CR 들이 일제히 생성됩니다. 각 Application CR 은 `kubectl.kubernetes.io/last-applied-configuration` annotation 에 자기 spec 전체를 기록하는데, syncPolicy / source / destination 등이 길어지면 **256KB annotation 한도** 에 걸려서 실패합니다.

해결: root-app.syncPolicy.syncOptions 에 `ServerSideApply=true` 를 켜둡니다. 이러면 client-side annotation 대신 server-side field manager 로 관리됩니다.

```yaml
syncOptions:
  - ServerSideApply=true
```

저는 이걸 모르고 처음 부트스트랩하다가 절반의 Application 만 생성된 채로 실패한 적이 있습니다. 에러 메시지에 `metadata.annotations: Too long` 이 나옵니다. 한 번 ServerSideApply 로 바꿔 적용하면 그 다음부턴 안 만남.

---

## 5. selfHeal 의 함정 — immutable 필드 충돌

selfHeal 을 켜면 git 과 클러스터의 drift 를 즉시 복원합니다. 일반적으로는 좋은 일인데, **immutable 필드** 가 drift 했을 때 sync 가 영구 실패 상태에 빠집니다.

실제로 겪은 사례 한 가지를 풀어봅니다.

```
settlement-staging-elasticsearch 라는 StatefulSet 이 있다.

라이브 클러스터 STS 의 volumeClaimTemplates[0].spec.storageClassName = "solomon-local"
   (어제 라이브 patch 로 바꾼 값)

차트 git 의 storageClassName = "local-path" (기본값)
```

selfHeal 이 켜진 순간 ArgoCD 는 git 의 `local-path` 를 적용하려고 STS 를 patch 합니다. 그런데 `volumeClaimTemplates[*].spec.storageClassName` 은 **StatefulSet 의 immutable 필드** 입니다.

```
StatefulSet.apps "settlement-staging-elasticsearch" is invalid:
spec: Forbidden: updates to statefulset spec for fields other than
'replicas', 'ordinals', 'template', 'updateStrategy',
'revisionHistoryLimit', 'persistentVolumeClaimRetentionPolicy' and
'minReadySeconds' are forbidden (retried 3 times).
```

ArgoCD 는 OutOfSync 상태에 영구히 잠깁니다. selfHeal 이 retry 를 무한 시도해도 같은 에러만 반환됩니다. 자식 Application 1 개만 멈추는 게 아니라, **root-app 자체도 sync 가 일부 실패하므로** "한 개라도 실패면 전체 OutOfSync" 가 되어 모니터링에 빨간불.

해결 패턴 3 가지:

**A. 라이브 검증값을 git 으로 거꾸로 영구화 (가장 안전)**

```yaml
# values-staging.yaml
elasticsearch:
  storageClass: solomon-local   # 라이브 STS 와 일치 → drift 0
```

이게 정답입니다. selfHeal 의 철학은 "git 이 single source of truth" 인데, 라이브 클러스터에서 손으로 만진 immutable 값이 git 보다 더 정확하다면 그건 git 을 업데이트해야 합니다.

**B. STS 를 cascade=orphan 으로 삭제 후 재생성**

```bash
kubectl delete sts <name> --cascade=orphan
# pods 는 살아있음, STS 만 사라짐
# ArgoCD 가 다음 sync 때 git 의 spec 으로 STS 재생성
# 새 STS 가 살아있는 pods 를 다시 인수
```

git 을 진실로 두고 싶을 때 쓰지만, orphan 인수 과정에서 pod label 매칭 안 맞으면 새 STS 가 다른 pod 를 만들어버려서 일시적으로 2 배로 뜹니다. 위험.

**C. ArgoCD Application 의 `Replace=true` syncOption**

```yaml
syncOptions:
  - Replace=true
```

이러면 patch 대신 delete + create 로 동기화합니다. STS 같은 stateful 리소스에는 절대 쓰면 안 됩니다. 데이터 손실.

저는 항상 A 입니다. drift 가 있다는 건 git 이 부족하다는 신호라고 보는 게 GitOps 의 정신.

---

## 6. root-app 자체의 self-reference 무한루프

App-of-Apps 패턴의 미묘한 함정 하나. `argocd-applications/` 디렉토리 안에 **`root-app.yaml`** 을 넣고 싶은 충동이 듭니다. "root-app 자신도 git 으로 관리하면 좋잖아." 이러면 안 됩니다.

```
root-app watches argocd-applications/
                    │
                    └─ argocd-applications/root-app.yaml  ← root-app 자신이 또 들어있음
                              │
                              └─ root-app 이 또 root-app 을 sync
                                        │
                                        └─ … 무한 reconcile
```

ArgoCD 는 이 패턴을 막진 않습니다. 그냥 동일 spec 이면 sync 가 no-op 으로 끝나서 무한루프가 표면적으로는 안 보이지만, 매 reconcile cycle 마다 root-app 이 자기 자신을 patch 시도해서 controller 에 부하만 줍니다.

해결: `root-app.yaml` 은 **레포 루트** 에 두고, `argocd-applications/` 디렉토리에 안 넣습니다. 부트스트랩 1 회만 수동 apply 후 영원히 안 건드림.

```
helm-deploy/
├── root-app.yaml                ← 레포 루트, 부트스트랩 전용
├── argocd-applications/
│   ├── sns-prod.yaml
│   ├── academy-prod.yaml
│   └── ...
└── charts/
    └── ...
```

root-app spec 을 바꾸고 싶으면 그땐 `kubectl apply -f root-app.yaml` 을 수동으로 칩니다. **1 회성 부트스트랩 + 1 회성 자기 수정.** 이 두 가지를 빼면 git push 만으로 다 됩니다.

---

## 7. 실전 운영 — 한 달 후 회고

App-of-Apps 적용 후 30 일간 추적해본 결과:

| 지표 | 도입 전 | 도입 후 |
|---|---|---|
| 새 서비스 1 개 추가 시간 | 차트 push + kubectl apply = 2 단계 | git push = 1 단계 |
| 클러스터-git drift 감지 평균 시간 | 수동 비교 (몇 시간/며칠) | ArgoCD UI 즉시 (분 단위) |
| Application spec stale 사고 | 월 2~3 회 | 0 회 |
| 환경별 syncPolicy 일관성 | 수동 관리 (drift 발생) | git diff 로 강제 일관 |

가장 큰 변화는 **클러스터 상태에 대한 신뢰** 입니다. 도입 전엔 "git 에 있는 게 진짜 적용됐는지?" 를 항상 의심해야 했습니다. 도입 후엔 `git pull && diff` 만 봐도 클러스터 상태를 확신합니다.

부작용은 한 가지 — **자식 Application 의 spec 을 절대 수동으로 못 만집니다**. 디버깅용 임시 변경 (예: `selfHeal: true → false` 잠깐 끄기) 도 selfHeal 이 즉시 원복합니다. 디버깅 중에는 root-app 의 selfHeal 만 잠깐 false 로 내려야 합니다.

```bash
# 임시 디버깅 — root-app 의 selfHeal 만 끈다
kubectl patch -n argocd app root-app --type merge \
  -p '{"spec":{"syncPolicy":{"automated":{"selfHeal":false}}}}'

# 자식 Application 의 syncPolicy 를 마음대로 수정 후 디버깅
kubectl patch -n argocd app sns-prod --type merge \
  -p '{"spec":{"syncPolicy":{"automated":{"selfHeal":false}}}}'

# 디버깅 끝나면 다시 켠다
kubectl apply -f root-app.yaml
```

이 운영 흐름이 익숙해지기 전엔 selfHeal 이 자꾸 원복해서 의문스러웠지만, 익숙해지면 "쥐도 새도 모르게 환경이 변경되는 일이 없는" 안정감을 줍니다.

---

## 8. 마무리

ArgoCD 자체를 GitOps 로 셀프 관리하는 건 **부트스트랩 비용 5 분 + 함정 3 가지 인지** 면 끝입니다.

- 부트스트랩: `root-app.yaml` 1 회 `kubectl apply`
- 함정 1: ServerSideApply 안 켜면 첫 부트스트랩에서 annotation 크기 에러
- 함정 2: selfHeal 켜기 전에 immutable 필드 drift 가 없는지 확인 (특히 StatefulSet)
- 함정 3: `root-app.yaml` 은 절대 `argocd-applications/` 안에 넣지 말 것

도입 비용 5 분, 운영 부담 -80%. 30 개 서비스 정도 되면 무조건 가성비가 맞는 패턴입니다.

저는 5 노드 K3s 홈랩에서 30 개 ArgoCD Application 을 이 패턴으로 관리하고 있고, 한 달간 0 회의 "kubectl apply 깜빡함" 사고를 경험했습니다. 이전에는 한 달 평균 2~3 회씩 있던 일입니다.

다음 글에서는 selfHeal 을 켠 상태에서 발생한 **Helm 차트의 라이브 patch 영구화 작업** 을 다룰 예정입니다. 운영 중 즉시 수정한 값들을 어떻게 git 으로 거꾸로 가져왔는지에 대한 이야기입니다.
