---
layout: post
title: "K3s 홈랩에서 노드 1대 OFF 로 ECK·Tempo·TTS 가 3시간 멈췄다 — local-path PV node-affinity 와 nodeSelector 트랩"
date: 2026-05-24 19:50:00 +0900
categories: [infra, kubernetes, postmortem]
tags: [k3s, local-path, persistent-volume, node-affinity, eck-operator, argocd, homelab, lemuel-xr]
---

WiFi 가 불안해서 노드 1대(*david*)를 꺼둔 사이, 그와 *전혀 무관해 보이는* 세 서비스가 동시에 멈춰 있었다. **ECK operator pod 가 100분째 Pending, Tempo pod 가 다시 켜도 또 Pending, TTS pod 두 개가 31시간·45시간째 ContainerCreating.** 노드 한 대가 한 시간이면 *그 노드의 워크로드* 만 영향을 받아야 정상인데, 다른 노드에 있어야 마땅한 것들까지 같이 멈춘 이유는 무엇인가.

이 글은 그 디버깅 기록이다. 결론을 먼저 말하면 — *local-path provisioner 의 PV 가 죽은 노드에 묶여 있었고*, *ECK 의 nodeSelector 가 우연히 그 죽은 노드만 매치했고*, *ArgoCD self-heal 이 직접 패치를 매번 원복했다*. 3분짜리 정답이 3시간이 된 건 *세 개의 트랩이 동시에 작동* 했기 때문이다.

---

## TL;DR

| 서비스 | 증상 | 원인 | 영구 수정 |
|---|---|---|---|
| Tempo | 새 pod Pending — *''didn't match PersistentVolume's node affinity''* | local-path PV 가 david 에 고정 | PVC + PV 폐기 → 새 PV 가 살아있는 노드에 생성 |
| ECK operator | pod Pending 100m — *''3 node(s) didn't match Pod's node affinity/selector''* | STS `nodeSelector: monitoring=true` 가 david(off) 만 매치 | solomon 에 `monitoring=true` 라벨 부여 |
| TTS sidecar | ContainerCreating 31h·45h — *''Insufficient memory''* | PVC 가 solomon 에 묶였는데 solomon 이 cordoned | `kubectl uncordon solomon` |
| ECK STS 직접 패치 | 5분 후 원복 | ArgoCD `selfHeal: true` + `ApplyOutOfSyncOnly` 가 STS 전체를 desired 로 되돌림 | helm values 수정 또는 *라벨* 로 우회 |

---

## 1. 첫 증상 — 노드 하나가 빠졌을 뿐인데

홈랩 5 노드 중 david 는 WiFi 가 불안해서 **의도적으로 꺼뒀다**. solomon 은 이전에 NotReady 였다가 회복 후 *cordon* 상태 (보호 차원). 두 노드 모두 *완전히 죽은 건 아니고 스케줄링에서 빠진 상태*.

이 상황에서 `kubectl get pods -A | grep -v Running` 의 결과:

```
elastic-system   elastic-operator-0           0/1   Pending             0    100m
monitoring       tempo-0                      0/1   Pending             0    56s
lemuel-xr-prod   lemuel-xr-tts-...-dbhw4      0/1   ContainerCreating   0    31h
lemuel-xr-prod   lemuel-xr-tts-...-f6qh8      0/1   ContainerCreating   0    45h
```

ContainerCreating 이 31시간이라는 건 *말이 안 된다*. ContainerCreating 은 보통 *image pull + mount* 가 끝나면 Running 으로 가는, *수 분짜리* 단계다. 이 숫자는 *Age* (pod 생성 시점부터의 시간) 일 뿐이고 실제로는 *Pending → 스케줄 실패가 31시간 누적된 것*. 진짜 시계는 `describe` 의 `Events` 에 있다.

---

## 2. Tempo — local-path PV 의 node-affinity 트랩

```
Warning  FailedScheduling   75s   default-scheduler
  0/5 nodes are available: 1 node(s) had untolerated taint(s),
  1 node(s) were unschedulable,
  3 node(s) didn't match PersistentVolume's node affinity.
```

핵심은 *''3 node(s) didn't match PersistentVolume's node affinity''*. **PV 가 노드 1개에만 묶여 있다.** 어느 노드인지 확인:

```bash
$ kubectl -n monitoring get pvc storage-tempo-0 -o jsonpath='{.spec.volumeName}'
pvc-abd09e30-2dff-42cb-9a75-ac4f28cba821

$ kubectl get pv pvc-abd09e30-... -o jsonpath='{.spec.nodeAffinity}'
{"required":{"nodeSelectorTerms":[{"matchExpressions":[
  {"key":"kubernetes.io/hostname","operator":"In","values":["david"]}
]}]}}
```

**david.** 그래서 다른 노드로 *옮길 수가 없다*. local-path provisioner 는 *생성 시점의 노드* 에 PV 를 1:1 로 묶는다 (그게 정의상 local-path 다). 노드가 죽으면 PV 도 같이 죽는 것과 같다.

이 PV 안에 *남기고 싶은 데이터* 가 있다면 david 를 복구해야 한다. 그런데 Tempo 는 *Pending 인 채 한 번도 데이터를 쓴 적이 없다*. 따라서 PVC + PV 를 폐기하고 *재생성* 하면 새 PV 가 *살아있는 노드 중 하나에* 만들어진다.

```bash
$ kubectl -n monitoring delete pvc storage-tempo-0 --wait=false
$ kubectl -n monitoring delete pod tempo-0 --force --grace-period=0
```

StatefulSet 컨트롤러가 즉시 PVC 와 pod 를 다시 만들고, local-path 가 새 PV 를 *louise* 위에 생성. 30초 후 **tempo-0 1/1 Running**.

---

## 3. ECK — nodeSelector 가 죽은 노드만 매치

```
Warning  FailedScheduling   62m
  0/5 nodes are available: 1 node(s) had untolerated taint(s),
  1 node(s) were unschedulable,
  3 node(s) didn't match Pod's node affinity/selector.
```

이번엔 *''node affinity/**selector**''*. PV 가 아니라 *pod 의 nodeSelector*. 확인:

```bash
$ kubectl -n elastic-system get sts elastic-operator -o jsonpath='{.spec.template.spec.nodeSelector}'
{"monitoring":"true"}
```

그리고 클러스터에서 `monitoring=true` 라벨이 붙은 노드는 *오직 david 뿐이었다*. ECK chart values 에 *''operator 는 데이비드(모니터링)에 둔다''* 라고 친절하게 주석까지 달려 있다. david 가 살아있던 동안에는 완벽히 동작했다. david 가 꺼지자 *어디서도 스케줄될 수 없는 pod* 가 됐다.

### 첫 시도 — STS 직접 패치 (실패)

```bash
$ kubectl -n elastic-system patch sts elastic-operator \
    --type=json -p='[{"op":"remove","path":"/spec/template/spec/nodeSelector"}]'
statefulset.apps/elastic-operator patched
```

5분 후 다시 확인:

```bash
$ kubectl -n elastic-system get sts elastic-operator -o jsonpath='{.spec.template.spec.nodeSelector}'
{"monitoring":"true"}
```

**원복됐다.** ArgoCD `syncPolicy: { automated: { selfHeal: true } }` + `ApplyOutOfSyncOnly` 는 *현재 spec 이 desired 와 다르면 desired 를 다시 적용* 한다. ignoreDifferences 에는 `containers/0/args` 만 들어가 있어서 *nodeSelector 변경* 은 자유롭게 원복 대상.

### 두 번째 시도 — 라벨로 우회 (성공)

helm values 를 수정해서 PR + 배포 사이클을 돌리는 대신, **노드 라벨 한 줄로** desired 와 현실을 일치시킬 수 있다:

```bash
$ kubectl label node solomon monitoring=true --overwrite
node/solomon labeled

# STS 는 그대로 (nodeSelector: monitoring=true) — 이제 solomon 이 매치된다
$ kubectl -n elastic-system delete pod elastic-operator-0 --force --grace-period=0
```

10분 후: **elastic-operator-0 1/1 Running on solomon.**

> *교훈*: "desired spec 을 바꾸기 어렵다면, *현실* 을 desired 에 맞춰라." 라벨은 *cluster-scoped 사실* 일 뿐 GitOps 의 desired 가 아니므로 ArgoCD 가 원복하지 않는다.

이 트릭은 *영구 해결* 인가 *우회* 인가? 답은 *둘 다*. david 가 복귀해도 solomon 의 라벨이 같이 살아있을 뿐이라 ECK 가 *둘 중 어느 쪽에든* 스케줄될 수 있게 된다 — 가용성이 더 좋아진 셈이다.

---

## 4. TTS — solomon cordon 의 후폭풍

```
Warning  FailedScheduling
  0/5 nodes are available:
  1 node(s) didn't match PersistentVolume's node affinity,  # ← PVC 가 solomon 에
  1 node(s) had untolerated taint(s),                       # ← lemuel (control-plane)
  1 node(s) were unschedulable,                             # ← solomon (cordoned)
  2 Insufficient memory.                                    # ← louise, ilwon
```

5개 노드 *전부* 못 받는 슬픈 상태. 분석:

| 노드 | 이유 | 해법 |
|---|---|---|
| solomon | unschedulable (cordon) | **uncordon** |
| solomon | (실은 여기로 가야 함 — PVC 가 묶임) | uncordon 으로 동시 해결 |
| david | NotReady (off) | 무관 |
| lemuel | control-plane taint | 무관 (TTS 는 거기 두지 않는다) |
| louise, ilwon | Insufficient memory | TTS 가 GPU/큰 메모리 워크로드 |

**`kubectl uncordon solomon`** 한 줄. 1분 후 *두 pod 모두 ContainerCreating → Running*. XTTS-v2 모델 1.87GB 다운로드가 시작됐고, 약 12분 후 모델 로딩 완료, Ready=1/1.

---

## 5. 세 트랩이 동시에 작동한 이유

각 서비스의 *단일 문제* 는 별것 아니다. 그러나 **셋이 동시에 같은 노드(david)에 의존하고 있었다**:

```
              [david: NotReady (WiFi off)]
                ┃
                ┣━ Tempo PV (local-path) — 데이터 묶임
                ┣━ ECK nodeSelector(monitoring=true) — 유일한 매치
                ┗━ (TTS 는 solomon 의존이지만 solomon 이 cordoned)
```

이 *교집합* 이 명시적인 곳은 어디에도 없었다. local-path PV 의 nodeAffinity 는 *생성 시 자동* 으로 박힌다. ECK 의 nodeSelector 는 *Helm values* 에 있다. TTS 의 PVC 묶임은 *런타임 결정*. *세 가지 다른 메커니즘* 으로 david 에 의존했기 때문에 grep 하나로 찾을 수 없었다.

### 일반화

홈랩이나 GitOps 환경에서 **노드 한 대를 빼기 전에 다음을 확인하라**:

```bash
# 1) 이 노드에 묶인 local-path PV
kubectl get pv -o json | jq -r '
  .items[] | select(.spec.nodeAffinity.required.nodeSelectorTerms[]?.matchExpressions[]?.values[]? == "<NODE>")
  | "\(.metadata.name)  \(.spec.claimRef.namespace)/\(.spec.claimRef.name)"'

# 2) 이 노드를 *유일하게* 매치하는 nodeSelector / nodeAffinity
kubectl get nodes -l <매치-키>=<값>   # 결과가 한 노드뿐이면 위험

# 3) 이 노드에 묶인 PVC (writeable PV 가 있는 워크로드)
kubectl get pvc -A -o json | jq -r '
  .items[] | "\(.metadata.namespace)/\(.metadata.name)  \(.spec.volumeName)"' \
  | xargs -n1 -I{} sh -c '...'
```

원자적 *''이 노드 1대 안전하게 빼도 됨''* 체크리스트가 표준화되어 있지 않은 게 K8s 가 풀어야 할 큰 숙제 중 하나다. *PodDisruptionBudget* 은 *replica 가 부족할 때* 만 막아주지, *PVC node-affinity 때문에 다른 곳으로 못 가는 상황* 은 잡지 못한다.

---

## 6. 다음에 다시 안 당하기

### 6.1 single-node nodeSelector 는 *라벨을 둘 이상* 에 부여

ECK 가 *''monitoring 전용 노드 1대''* 에 묶이면 그 노드가 사라질 때 ECK 도 사라진다. *어차피 ECK 는 가벼우니* monitoring=true 를 **control-plane 노드 (solomon, lemuel) 에도 부여** 해서 *fallback target* 을 만든다. helm chart 의 *''david 에 둔다''* 주석은 *desired location* 이지 *유일한 자리* 가 아니어야 한다.

### 6.2 local-path 대신 *replicated* storage

Tempo·ECK·TTS 모두 *데이터가 한 노드에 묶이면 그 노드 없이 못 산다*. 홈랩이라면 [longhorn](https://longhorn.io/) 또는 [rook-ceph](https://rook.io/) 로 *replicated PV* 를 쓰면 노드 한 대가 죽어도 PV 가 다른 곳에서 살아남는다. 진입장벽이 있어서 local-path 로 시작했지만, *이제 cluster 가 5 노드까지 컸으니* 옮길 시점.

### 6.3 ArgoCD 직접 패치는 *임시 진단용* 으로만

`kubectl patch` 로 ECK 의 nodeSelector 를 제거한 시도는 *5분짜리 헛수고* 였다. ArgoCD `selfHeal` 이 켜져 있는 한 *git 이 desired 의 유일한 출처*. 영구 수정은 (a) helm values 수정 + PR, 또는 (b) ignoreDifferences 추가, 또는 (c) *라벨로 desired 를 만족시키기* — 셋 중 하나여야 한다.

### 6.4 *''Age 가 30시간''* 은 *진행 30시간* 이 아니다

`STATUS=ContainerCreating, AGE=31h` 를 본 순간 *''뭔가가 31시간 동안 일하고 있다''* 라고 잘못 읽었다. 실제로는 *pod 가 처음 만들어진 게 31시간 전, 그 후로 한 발자국도 못 갔음*. 진짜 시계는 `kubectl describe pod ... | grep -A20 Events:` 의 *Age* 컬럼. *Pending 인 채로 시간이 누적된 것* 인지, *방금 ContainerCreating 으로 막 들어와서 image pull 중* 인지를 거기서 구분해야 한다.

---

## 7. 회복 후 잔여 작업

세 서비스가 모두 회복된 직후 ArgoCD 화면:

| App | Sync | Health | 비고 |
|---|---|---|---|
| eck-operator | Synced | Progressing → Healthy | solomon 라벨로 즉시 회복 |
| tempo | OutOfSync | Healthy | `nodeSelector: {}` 직접 패치 잔재 |
| elk-cluster | OutOfSync | Progressing → Healthy | ES/Kibana 가 ECK 회복 후 자기 회복 |
| lemuel-xr-prod | OutOfSync | Degraded → Healthy | TTS 모델 로드 후 readiness 통과 |
| cluster-ops | Synced | Degraded | eck-leader-elect-patch Job (rancher/kubectl distroless 잔재) |

OutOfSync 들은 *복구 과정에서 만든 직접 패치 자국*. 이걸 정리하는 게 *진짜 영구화*. 다음 PR 에서:

1. tempo chart values 의 `nodeSelector` 를 *기본값* 으로 되돌리기 (workaround 였음)
2. eck-operator chart values 의 `nodeSelector: { monitoring: "true" }` 는 그대로 두되, *solomon 도 monitoring=true 라벨* 을 *node-labels* 자동화 (manifest 로)
3. cluster-ops 의 leader-elect Job 은 *이미 수동 적용된 args 와 동치* — 삭제하거나 Helm `lookup` 으로 idempotent 화

---

## 8. 마무리

홈랩이라는 *작은 클러스터* 의 장점은 *모든 트랩이 명백히 보인다* 는 것이다. production 5 노드면 *복원력이 약점* 이지만 *디버깅이 빠르다*. 같은 문제가 100 노드 클러스터에서 발생했다면 *node-affinity 그래프* 자체를 그려보기 전엔 원인을 찾을 수 없었을 것이다.

**오늘의 한 줄 교훈**:

> *''노드를 빼기 전에, 그 노드의 *hostname* 으로 묶인 모든 것을 한 번 grep 해본다''*. *PV nodeAffinity, pod nodeSelector, label-only-on-this-node nodeAffinity, taints/tolerations*. 네 곳 모두.

라벨 한 줄이 STS 패치보다 강력했다는 사실은, *desired state 를 바꿀 수 없을 때 현실을 desired 에 맞추라* 는 GitOps 의 작은 역설을 다시 떠올리게 한다.

---

> 작성: 2026-05-24. 환경: K3s v1.35.4, ArgoCD, ECK 2.16.1, Grafana Tempo, lemuel-xr (Spring Boot 4 + Python TTS sidecar). 홈랩 5 노드 (lemuel, ilwon, louise, david, solomon).
