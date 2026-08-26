---
layout: post
title: "StatefulSet 에 PVC 를 미리 만들어 붙이면 어디서 발목이 잡히는가"
date: 2026-08-27 05:10:00 +0900
categories: [kubernetes, storage]
tags: [statefulset, persistentvolumeclaim, local-persistent-volume, k3s, strimzi, homelab]
---

홈랩 k3s 클러스터에서 상태 저장 워크로드 네 개(Postgres 2대·Kafka 브로커·Elasticsearch)를
**PVC 를 손으로 먼저 만들어 붙이는 방식**으로 굴리고 있다. 멘토링 요청을 준비하면서
"이게 정석이 아닌 건 아는데, 나중에 어떤 식으로 발목을 잡느냐"를 스스로 정리해야 했고,
그 과정에서 **문서로 알던 것과 클러스터에 실제로 떠 있는 것이 다르다**는 걸 발견했다.

이 글은 그 실측 기록이다. 결론부터 말하면, 발목을 잡는 건 "우회를 썼다"는 사실 자체가 아니라
**이름 규약 하나에 전부를 걸고 있는데 그 규약이 어긋나도 아무 신호가 없다**는 점이다.

---

## 1. 먼저, 이게 정확히 무슨 방식인가

흔히 "`volumeClaimTemplates` 대신 PVC 를 미리 만든다"고 말하지만, 정확하지 않다.
템플릿은 그대로 있다. 다만 **그 템플릿이 만들었을 이름과 똑같은 이름의 PVC 를 미리 만들어 둔다.**
StatefulSet 컨트롤러는 그 이름의 PVC 가 이미 있으면 새로 만들지 않고 **그것을 그냥 쓴다.**

이름 규칙은 쿠버네티스 소스에 박혀 있다.

```go
// pkg/controller/statefulset/stateful_set_utils.go
func getPersistentVolumeClaimName(set *apps.StatefulSet, claim *v1.PersistentVolumeClaim, ordinal int) string {
	return fmt.Sprintf("%s-%s-%d", claim.Name, set.Name, ordinal)
}
```

`<템플릿 이름>-<StatefulSet 이름>-<ordinal>` 이다.
같은 파일의 `storageMatches()` 는 파드의 볼륨이 참조하는 `claimName` 이 이 함수의 결과와
**문자열로 같은지**를 비교한다.[^src] 계약의 전부가 이 문자열 비교다.

그리고 이건 편법이 아니다. 공식 문서의 StatefulSet Limitations 첫 줄이 이렇게 되어 있다.

> The storage for a given Pod must either be provisioned by a PersistentVolume Provisioner
> based on the requested storage class, **or pre-provisioned by an admin**.[^sts]

`Volume Claim Templates` 절도 두 가지 조건 중 하나만 만족하면 stable storage 가 된다고 적는다 —
동적 프로비저닝이 되거나, 아니면 **"클러스터에 이미 올바른 StorageClass 와 충분한 용량의
PersistentVolume 이 있거나".**[^sts] 지금 방식은 두 번째다.

Strimzi 의 재해복구 문서는 아예 이 패턴을 *복구 절차로* 안내한다 — PV 를 `Retain` 으로 남긴 뒤
같은 이름의 PVC 를 `volumeName` 으로 그 PV 에 직접 묶어 다시 만들라고.[^strimzi-dr]

그러니 "정석이 아니다"는 말은 절반만 맞다. **정석이 아닌 건 방식이 아니라, 이 방식이 요구하는
불변조건을 아무도 검사하지 않고 있다는 상태 쪽이다.**

## 2. 실측 — 템플릿이 거짓말을 하고 있었다

클러스터에서 `ssd-local` StorageClass 를 쓰는 PVC 를 전부 뽑고, 그것을 쓰는 StatefulSet 의
`volumeClaimTemplates` 와 대조했다.

| StatefulSet | 템플릿의 `storageClassName` | **살아 있는 PVC 의 `storageClassName`** | 바인딩된 PV |
|---|---|---|---|
| `jen-prod/jen-postgres` | `solomon-local` | **`ssd-local`** | `ssd-jen-postgres` |
| `settlement-prod/settlement-elasticsearch` | `local-path` | **`ssd-local`** | `ssd-settlement-es` |

둘 다 어긋나 있다. StatefulSet 은 5월 10일·12일에 만들어졌고 PVC 는 5월 13일에 만들어졌다 —
SSD 로 옮기면서 PVC 만 바꿔 끼웠고, **템플릿은 그대로 남았다.**

중요한 건 이게 *에러가 아니라는 것*이다. PVC 가 이미 존재하므로 컨트롤러는 템플릿의 `spec` 을
읽지 않는다. 파드는 Running, PVC 는 Bound, ArgoCD 는 Synced, 대시보드는 전부 초록이다.
git 에 적힌 `storageClassName: solomon-local` 은 **아무 데도 적용되지 않는 죽은 글자**인데,
다음에 이 파일을 읽는 사람(3개월 뒤의 나 포함)에게는 여전히 사실처럼 보인다.

## 3. 그래서 어디서 발목이 잡히는가

### (a) PVC 를 한 번 지우면, 완전히 다른 스토리지가 뜬다

템플릿은 죽어 있는 게 아니라 **자고 있다.** PVC 가 사라지는 순간 컨트롤러는 템플릿대로
PVC 를 다시 만든다. 그런데 그 템플릿에 적힌 클래스는 실제와 다르다.

`settlement-elasticsearch` 가 특히 나쁘다. 템플릿의 `local-path` 는 정적 클래스가 아니라
**rancher.io/local-path 동적 프로비저너**이고, 그 클래스의 `reclaimPolicy` 는 `Delete` 다.

```
$ kubectl get sc
NAME            PROV                           BINDMODE               RECLAIM
local-path      rancher.io/local-path          WaitForFirstConsumer   Delete
solomon-local   rancher.io/local-path          WaitForFirstConsumer   Retain
ssd-local       kubernetes.io/no-provisioner    WaitForFirstConsumer   Retain
```

즉 PVC 가 한 번 지워지면 ES 는 **빈 볼륨을 새로 받아서, 아무 데서나, 정상 기동한다.**
CrashLoop 도 아니고 Pending 도 아니다. 그냥 인덱스가 없는 채로 Green 이 된다.
원래 SSD 위의 데이터는 `ssd-settlement-es` PV 에 `Retain` 으로 남아 있지만 아무도 그걸 안 쓴다.
**가장 늦게 발견되는 종류의 사고다.**

### (b) 노드가 고정된다 — 그리고 네 개가 전부 한 대에 몰려 있다

`ssd-local` 은 `local` 볼륨이고, 공식 문서는 이렇게 못박는다.

> Local volumes can only be used as a statically created PersistentVolume.
> **Dynamic provisioning is not supported.**
>
> **You must set a PersistentVolume `nodeAffinity` when using `local` volumes.**[^vol]

`nodeAffinity` 는 선택이 아니라 필수다. 그리고 그게 곧 파드를 그 노드에 묶는다. 실측하면:

```
ssd-asat-postgres    node=ilwon  reclaim=Retain  Bound  asat-prod/asat-postgres-data
ssd-jen-postgres     node=ilwon  reclaim=Retain  Bound  jen-prod/data-jen-postgres-0
ssd-kafka-broker     node=ilwon  reclaim=Retain  Bound  kafka/data-lemuel-dual-role-0
ssd-settlement-es    node=ilwon  reclaim=Retain  Bound  settlement-prod/data-settlement-elasticsearch-0
```

**네 개 전부 `ilwon` 이다.** 파드도 넷 다 거기 떠 있다. 6노드 클러스터인데 상태 저장
워크로드는 단일 장애점 위에 있고, 그중 하나는 서비스의 **유일한 데이터베이스**다.
같은 문서가 그 대가를 그대로 적어 둔다 — 노드가 불건강해지면 볼륨에 접근할 수 없고
파드는 뜨지 못한다.[^vol]

이건 PVC 선생성의 부작용이 아니라 **local PV 를 고른 것의 대가**다. 다만 PVC 를 손으로 만들면
그 대가가 어디에 얼마나 쌓였는지가 매니페스트 어디에도 안 보인다는 점이 문제다.
위 표는 `kubectl` 로 캐야 나왔다.

### (c) 스케일아웃이 에러 없이 멈춘다

`ssd-local` 의 프로비저너는 `kubernetes.io/no-provisioner` 다.
replicas 를 1 → 2 로 올리면 컨트롤러는 `data-<sts>-1` PVC 를 만들고,
그 이름의 PV 를 미리 만들어 두지 않았으므로 **영원히 Pending 이다.**
StatefulSet 은 `OrderedReady` 정책상 그 파드를 기다리며 멈춰 선다.
스케일아웃이 실패하는 게 아니라 *진행되지 않는다.*

### (d) `volumeClaimTemplates` 는 아예 수정할 수 없다

위 (a) 의 불일치를 "git 에서 고치면 되지"라고 생각했다면, 안 된다.

```go
// pkg/apis/apps/validation/validation.go
allErrs = append(allErrs, apivalidation.ValidateImmutableField(
    statefulSet.Spec.VolumeClaimTemplates, oldStatefulSet.Spec.VolumeClaimTemplates,
    specPath.Child("volumeClaimTemplates")).WithOrigin("immutable")...)
```

`volumeClaimTemplates` 는 통째로 immutable 이다.[^valid] 클래스든 용량이든 못 바꾼다.
바꾸려면 StatefulSet 을 지웠다 다시 만들어야 하고, 그때 파드까지 죽이지 않으려면
`--cascade=orphan` 으로 오브젝트만 지워야 한다.[^del]

GitOps 를 쓰고 있으면 이게 한 겹 더 나쁘다. ArgoCD 는 이 필드를 apply 하려다 계속 거부당하고,
**영구 OutOfSync** 로 남는다. 고장 신호와 구조적 잡음이 섞이기 시작한다.

### (e) PVC 회수 정책은 지금은 무해하지만, 켜는 날 조용히 어긋난다

네 StatefulSet 모두 `persistentVolumeClaimRetentionPolicy` 가 `Retain/Retain` —
즉 기본값이다.[^sts] 그리고 손으로 만든 PVC 네 개는 `ownerReferences` 가 전부 비어 있다.

```
asat-prod/asat-postgres-data                     owners=NONE
jen-prod/data-jen-postgres-0                     owners=NONE
kafka/data-lemuel-dual-role-0                    owners=NONE
settlement-prod/data-settlement-elasticsearch-0  owners=NONE
```

지금은 아무 문제가 없다. 문서상 owner reference 는 정책을 `Delete` 로 **바꿀 때** 컨트롤러가
붙이는 것이기 때문이다.[^sts] 다만 이 필드를 나중에 켜는 사람은 "정리되겠지"라고 기대할 텐데,
손으로 만든 PVC 와 정적 PV(`Retain`)가 섞인 상태에서 실제로 무엇이 지워지고 무엇이 남는지는
**켜 보기 전에는 모른다.** 지금 문서화해 두지 않으면 그때 알아내야 한다.

## 4. 덤 — 같은 클러스터에 서로 다른 패턴 세 개가 섞여 있었다

조사하다 보니 네 워크로드가 각기 다른 방식이었다.

- **`jen-postgres` · `settlement-elasticsearch`** — StatefulSet + `volumeClaimTemplates` + 이름 규약으로 PVC 선점 (위에서 본 그것)
- **`lemuel-dual-role`** — StatefulSet 이 아예 없다. Strimzi 의 `KafkaNodePool` 이 관리하고, PVC 이름은 오퍼레이터의 규약 `data-<클러스터>-<풀>-<pod_id>` 를 따른다[^strimzi]
- **`asat-postgres`** — StatefulSet 인데 `volumeClaimTemplates` 가 **비어 있다.** 파드 스펙에서 `asat-postgres-data` PVC 를 그냥 마운트한다

세 번째가 특히 함정이다. 이름에 ordinal 이 없으니 규약 밖이고, replicas 를 늘리면
**모든 파드가 같은 RWO 볼륨을 물려고 든다.** 지금은 replicas=1 이라 아무 일도 안 일어난다.

## 5. 정리 — 무엇을 고칠 것인가

방식을 갈아엎을 생각은 없다. 공식 문서가 허용하는 방식이고, 홈랩에서 SSD 를 특정 노드에
붙여 쓰는 이상 local PV 는 사실상 유일한 선택지다. 대신 순서는 이렇게 잡았다.

1. **템플릿과 실물의 불일치부터 없앤다.** (a) 가 유일하게 데이터 손실로 이어지는 항목이다.
   `volumeClaimTemplates` 가 immutable 이라 `--cascade=orphan` 재생성이 필요하고, 그동안
   파드는 살아 있어야 한다.
2. **불변조건을 검사로 만든다.** "PVC 의 `storageClassName` 이 그 StatefulSet 템플릿의
   값과 같은가"는 `kubectl` 한 번이면 나온다. 사람이 기억할 게 아니라 주기적으로 도는
   검사가 될 일이다. 이 글의 표는 전부 그렇게 뽑았다.
3. **ilwon 집중을 문서에 명시한다.** 옮기는 건 별개 작업이고 비용이 크다. 최소한
   "이 노드가 죽으면 무엇이 같이 죽는가"가 어딘가에 적혀 있어야 한다.

발목을 잡는 건 우회 그 자체가 아니었다. 이름 규약에 전부를 걸어 두고 **그 규약이 지켜지는지
아무도 안 보고 있었다**는 것이 진짜 문제였고, 초록불 대시보드가 그걸 3개월 동안 가려 줬다.

> 같은 클러스터를 두고 정리한 다른 질문들은
> [GitOps 로 홈랩을 굴리며 멘토에게 묻고 싶은 여섯 가지]({% post_url 2026-08-27-six-gitops-questions-i-want-a-mentor-to-answer %})
> 에 모아 두었다. 이 글은 그중 스토리지 항목을 끝까지 파고든 기록이다.

---

## References

[^sts]: Kubernetes Documentation, *StatefulSets* — "Limitations", "Volume Claim Templates", "Stable Storage", "PersistentVolumeClaim retention". <https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/>
[^src]: kubernetes/kubernetes, `pkg/controller/statefulset/stateful_set_utils.go` — `getPersistentVolumeClaimName()`, `storageMatches()`. <https://github.com/kubernetes/kubernetes/blob/master/pkg/controller/statefulset/stateful_set_utils.go>
[^valid]: kubernetes/kubernetes, `pkg/apis/apps/validation/validation.go` — `ValidateStatefulSetUpdate()`. <https://github.com/kubernetes/kubernetes/blob/master/pkg/apis/apps/validation/validation.go>
[^vol]: Kubernetes Documentation, *Volumes* — "local". <https://kubernetes.io/docs/concepts/storage/volumes/#local>
[^del]: Kubernetes Documentation, *Delete a StatefulSet* — `--cascade=orphan`, "Persistent Volumes". <https://kubernetes.io/docs/tasks/run-application/delete-stateful-set/>
[^strimzi]: Strimzi Documentation, *Deploying and Managing Strimzi* — Kafka 파드의 PVC 명명 규약 `data-<kafka_cluster_name>-<pool_name>-<pod_id>`. <https://strimzi.io/docs/operators/latest/deploying>
[^strimzi-dr]: Strimzi Documentation, *Deploying and Managing Strimzi* — 네임스페이스 삭제로부터의 클러스터 복구 절차(PV 를 `Retain` 으로 남기고 같은 이름의 PVC 를 `volumeName` 으로 재생성). <https://strimzi.io/docs/operators/latest/deploying>

클러스터 수치(PV·PVC·StorageClass·노드 배치·`ownerReferences`)는 2026-08-27 자
운영 중인 k3s 클러스터에서 `kubectl` 로 직접 조회한 값이다.
