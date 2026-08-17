---
layout: post
title: "그 노드가 죽으면, 죽었다는 걸 보여줄 대시보드도 같이 죽는다 — 홈랩 K3s 운영을 6개 축으로 채점했다"
date: 2026-08-18 01:50:00 +0900
categories: [kubernetes, sre]
tags:
  [
    kubernetes,
    k3s,
    sre,
    high-availability,
    local-persistent-volume,
    velero,
    backup,
    pod-disruption-budget,
    qos,
    gitops,
    homelab,
  ]
---

클러스터 상태를 노드별 그림으로 뽑아보는 습관이 있다. 도형 하나가 파드 하나, 무리 하나가 네임스페이스다. 오늘 새벽에도 6장을 뽑았고, 그림은 자기 일을 했다 — **무엇이 어디에 있는지**를 보여줬다.

그런데 그림은 그다음 질문에 답해주지 않는다. _이 배치는 운영으로서 몇 점인가._

이 글은 그 질문에 답해보려고 클러스터를 6개 축으로 채점한 기록이다. 결론부터 쓰면 이렇게 갈렸다. **선언적 배포와 백업 체계는 잘 잡혀 있고, 데이터 배치는 낙제다.** 그리고 낙제의 내용이 좀 고약하다 — 노드 한 대에 데이터베이스 7종과 관측 스택 전부가 같이 올라가 있다. 그 노드가 죽으면 죽었다는 걸 보여줄 그라파나도 같이 죽는다.

> **평가 규칙 세 가지.** ① 숫자는 전부 2026-08-18 01:42 KST 에 실제 클러스터에서 뽑은 것이다(`v1.35.4+k3s1`). ② 판정 기준은 내 취향이 아니라 공식 문서에서 가져온다. ③ 문서에 없는 판단은 "판단"이라고 표시한다. 사설 IP·스토리지 계정 식별자 같은 건 뺐다.
>
> 노드 6대의 역할·테인트 구성 자체는 [사흘 전 글](/2026/08/15/six-nodes-not-six-equal-nodes/)에서 이미 다뤘다. 여기서는 반복하지 않고 *그 위에 올라간 워크로드*만 본다.

---

## 채점표 먼저

| 축             | 무엇을 봤나                                              | 판정   |
| -------------- | -------------------------------------------------------- | ------ |
| 1. 겹수        | Deployment 88개 중 84개가 `replicas: 1`                  | **D**  |
| 2. 데이터 배치 | PersistentVolume 46개가 **전부** 노드 로컬               | **F**  |
| 3. 용량·QoS    | 메모리 요청 63~74%, 한도는 최대 200% 초과할당            | **C**  |
| 4. 백업        | 오프사이트 2중 스케줄 — 다만 정지점(consistency) 미보장  | **C+** |
| 5. 선언적 운영 | ArgoCD Application 59개, 58개 Synced                     | **A−** |
| 6. 명세 위생   | 컨테이너 154개 중 리퀘스트 누락 15개, liveness 없음 48개 | **B**  |

전체 규모는 Running 파드 146개, 네임스페이스 46개, Deployment 88개, StatefulSet 21개, DaemonSet 5개다.

---

## 축 1. 겹수 — 88개 중 84개가 한 겹

`replicas` 분포부터 보면 이렇다.

| replicas | Deployment 수                               |
| -------- | ------------------------------------------- |
| 1        | 84                                          |
| 2        | 2 (`coredns`, `lemuel-xr-frontend`)         |
| 3        | 2 (`settlement-app`, `settlement-frontend`) |

StatefulSet 21개는 **전부 1 레플리카**다. PostgreSQL 7개, MySQL, Elasticsearch 4개(로깅 hot/warm/cold + 검색용), Kafka, Prometheus, Alertmanager, MinIO — 하나도 빠짐없이 한 겹이다.

PodDisruptionBudget 은 6개 걸려 있는데, 실제로 무언가를 막는 건 그중 4개다. `kafka` 네임스페이스의 두 개는 `minAvailable: 0` 이라 사실상 아무것도 보호하지 않는다(Strimzi 기본값이다).

여기서 짚고 갈 오해가 하나 있다. PDB 를 걸어두면 노드 사고 전반이 막힌다고 생각하기 쉬운데, 쿠버네티스 공식 문서는 **kubelet 의 노드 압박 축출은 PDB 를 지키지 않는다**고 명시한다.

> The kubelet does not respect your configured PodDisruptionBudget or the pod's `terminationGracePeriodSeconds`.
> — [Node-pressure Eviction](https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/)

PDB 가 보장하는 건 [API 로 시작된 축출](https://kubernetes.io/docs/concepts/scheduling-eviction/api-eviction/), 즉 `kubectl drain` 같은 _자발적_ 중단이다. 메모리가 터져서 kubelet 이 파드를 걷어낼 때는 관여하지 않는다. 그러니 "PDB 6개"는 사고 대비 숫자가 아니라 계획된 유지보수 대비 숫자로 읽어야 맞다.

역방향 함정도 하나 실제로 걸려 있다. `logging/logs-es-default` PDB 는 지금 `disruptionsAllowed: 0` 이다(healthy 3 / desired 3). 이 상태에서 해당 노드에 `kubectl drain` 을 걸면 **드레인이 그 자리에서 멈춘다.** 계획된 재부팅을 하려다 처음 만나면 당황하기 딱 좋은 지점이다.

**판정 D.** 겹수를 안 준 것 자체는 홈랩에서 합리적 선택일 수 있다. 문제는 그게 선택이었는지 방치였는지가 클러스터에 안 적혀 있다는 점이다.

---

## 축 2. 데이터 배치 — 46개 볼륨이 전부 노드에 못 박혀 있다

이 클러스터의 PersistentVolume 46개를 StorageClass 로 갈라보면 이렇다.

| StorageClass                        | PV 수 |
| ----------------------------------- | ----- |
| `local-path`                        | 33    |
| `ssd-local`                         | 4     |
| `solomon-local`                     | 4     |
| `elk-hot` / `elk-warm` / `elk-cold` | 각 1  |
| `registry-local`                    | 1     |
| `nfs-server-local`                  | 1     |

**네트워크 스토리지가 0개다.** 46개 전부 `nodeAffinity` 가 특정 노드 하나에 박혀 있다. 노드별로 세면 ilwon 19, david 10, isagal 9, louise 7, solomon 1.

쿠버네티스 문서는 이 선택의 대가를 아주 직설적으로 적어놨다.

> However, `local` volumes are subject to the availability of the underlying node and are not suitable for all applications. If a node becomes unhealthy, then the `local` volume becomes inaccessible to the Pod. The Pod using this volume is unable to run. Applications using `local` volumes must be able to tolerate this reduced availability, as well as potential data loss, depending on the durability characteristics of the underlying disk.
> — [Volumes — local](https://kubernetes.io/docs/concepts/storage/volumes/#local)

Running 파드 146개 중 PVC 를 물고 있는 건 38개(26%)다. 이 38개는 **스케줄러가 다른 노드로 옮길 수 없다.** 나머지 108개는 원리상 옮길 수 있다.

그런데 진짜 문제는 개수가 아니라 *어느 38개인가*였다. ilwon 한 대에 붙은 19개를 그대로 옮겨 적는다.

```
asat-prod/asat-minio-0              logging/logs-es-hot-0
asat-prod/asat-postgres-0           logging/logs-es-warm-0
crypto-prod/crypto-postgres-0       logging/logs-ls-0
dart-prod/dart-postgres-0           monitoring/prometheus-kps-prometheus-0
database-prod/database-mysql-0      monitoring/alertmanager-kps-alertmanager-0
jen-prod/jen-postgres-0             monitoring/kps-grafana-...
kafka/lemuel-dual-role-0            nfs-server/nfs-server-...
settlement-prod/ai-postgres-0       registry-mirror/registry-mirror-...
settlement-prod/settlement-elasticsearch-0
sns-prod/sns-postgres-0
trading-prod/trading-postgres-0
```

한 노드에 PostgreSQL 6개, MySQL 1개, Kafka 브로커, 로그 파이프라인 전체(Elasticsearch hot·warm + Logstash), **Prometheus·Alertmanager·Grafana 전부**, 컨테이너 레지스트리 미러, NFS 서버가 같이 올라가 있다.

이 배치의 진짜 비용은 "DB 가 멈춘다"가 아니다. 그건 예상 가능한 손실이다. 비용은 **장애를 조사할 도구가 장애와 함께 사라진다**는 데 있다. ilwon 이 내려가면 메트릭도, 로그도, 대시보드도, 알림 라우터도 같이 내려간다. 복구하려고 이미지를 당기려 해도 레지스트리 미러가 거기 있다. 관측 스택을 관측 대상과 같은 실패 도메인에 두면, 정확히 필요한 순간에만 눈이 먼다.

부록으로 이름이 거짓말하는 사례도 하나 나왔다. `solomon-local` StorageClass 로 만들어진 PV 4개는 **전부 ilwon 에 있다.** 이름은 스케줄링에 아무 영향을 주지 않는다 — 배치를 결정하는 건 PV 의 `nodeAffinity` 이고, 이름은 사람만 속인다. (공식 문서도 [StorageClass 의 이름은 요청 식별자일 뿐](https://kubernetes.io/docs/concepts/storage/storage-classes/)이라고 정의한다.)

여기에 하나 더. 단일 레플리카 StatefulSet + 노드 다운 조합에는 별도의 문서화된 함정이 있다.

> When a node is shutdown but not detected by kubelet's Node Shutdown Manager, the pods that are part of a StatefulSet will be stuck in terminating status on the shutdown node and cannot move to a new running node. […] If the original shutdown node does not come up, these pods will be stuck in terminating status on the shutdown node forever.
> — [Node Shutdowns](https://kubernetes.io/docs/concepts/cluster-administration/node-shutdown/)

즉 노드가 곱게 죽지 않으면(정전, 커널 패닉) StatefulSet 파드는 자동으로 다른 데서 뜨는 게 아니라 `Terminating` 에 갇힌다. 로컬 볼륨이라 어차피 옮겨봐야 데이터가 없지만, "왜 새 파드가 안 뜨지"로 시간을 태우는 함정이 하나 더 있다는 뜻이다.

**판정 F.** 축 1의 낙제는 사실상 이 축의 결과다. 데이터가 노드에 묶여 있으면 레플리카를 늘려도 갈 곳이 없다.

---

## 축 3. 용량과 QoS — 요청은 70%, 한도는 200%

노드별 `Allocated resources` 실측이다.

| 노드    | CPU 요청 | CPU 한도 | MEM 요청 | MEM 한도 |
| ------- | -------- | -------- | -------- | -------- |
| ilwon   | 40%      | 178%     | **63%**  | 105%     |
| david   | 67%      | 292%     | **68%**  | 134%     |
| isagal  | 10%      | 70%      | **74%**  | 200%     |
| louise  | 38%      | 162%     | **70%**  | 155%     |
| solomon | 17%      | 55%      | 24%      | 44%      |
| lemuel  | 5%       | 30%      | 2%       | 8%       |

CPU 한도 초과할당은 별로 걱정할 게 아니다. CPU 는 압축 가능한 자원이라 넘치면 스로틀링으로 끝난다. **메모리는 다르다.** 한도 합이 isagal 200%, louise 155%, david 134% 라는 건, 그 노드의 파드들이 동시에 자기 한도까지 쓰면 물리 메모리가 안 남는다는 뜻이다.

그때 무슨 일이 일어나는지는 QoS 문서에 정의돼 있다. 리퀘스트와 리밋이 다르면 그 파드는 `Burstable` 이고,

> When a Node runs out of resources, Kubernetes will first evict `BestEffort` Pods running on that Node, followed by `Burstable` and finally `Guaranteed` Pods.
> — [Pod Quality of Service Classes](https://kubernetes.io/docs/concepts/workloads/pods/pod-qos/)

이 클러스터의 워크로드는 압도적으로 `Burstable` 이다. 즉 노드가 메모리 압박에 들어가면 축출 대상이 널려 있고, 축출은 (축 1에서 봤듯) PDB 를 지키지 않는다.

여유는 얼마나 남았을까. 워커 4대(ilwon 포함)의 allocatable 합과 요청 합은 이렇다.

$$\text{요청 합} = 52.0\ \text{GiB},\qquad \text{allocatable 합} = 76.2\ \text{GiB},\qquad \frac{52.0}{76.2} = 68.2\%$$

여기서 ilwon 한 대가 빠졌다고 가정해보자.

$$\text{남은 allocatable} = 45.6\ \text{GiB} \;<\; \text{총 요청} 52.0\ \text{GiB}$$

**산술적으로 안 들어간다.** (엄밀히는 상한값이다. 각 노드의 DaemonSet 파드 5개는 애초에 다른 노드로 이동하지 않으므로 실제 재배치 대상은 이보다 적다. 그래도 부호는 안 바뀐다.) 그리고 앞 절에서 봤듯이 그중 19개는 볼륨 때문에 애초에 이동 자체가 불가능하다. 즉 **용량 계산이 유의미해지기도 전에 스토리지에서 막힌다.**

**판정 C.** 리퀘스트를 성실히 달아둔 덕에 스케줄러가 판단할 근거는 있다. 다만 한 대를 잃어도 되는 헤드룸은 없다.

---

## 축 4. 백업 — 유일한 복구선인데, 정지점이 없다

데이터가 전부 노드 로컬이면 백업은 "있으면 좋은 것"이 아니라 **유일한 복구 수단**이다. 이 축은 꽤 잘 돼 있었다.

- 스케줄 2개: `daily-with-volumes`(매일 03:00, 전 네임스페이스, TTL 720h) + `hourly-critical`(4시간마다, 4개 핵심 네임스페이스, TTL 168h)
- 저장소: Cloudflare R2(S3 호환) — **클러스터 밖, 집 밖.** 노드 로컬 스토리지의 유일한 탈출구가 오프사이트에 있다는 건 이 클러스터에서 제일 잘한 결정이다.
- 이력 73건: Completed 57, PartiallyFailed 15, Failed 1
- 최근 daily 10회: 9회 Completed, 1회 PartiallyFailed

그런데 스케줄 정의를 열어보면 이렇게 돼 있다.

```yaml
defaultVolumesToFsBackup: true
hooks: {}
```

Velero 의 File System Backup 은 볼륨을 **살아있는 파일시스템에서 그대로 읽는다.** 공식 문서가 이 방식의 단점 첫 줄에 못을 박아뒀다.

> It backs up data from the live file system, in which way the data is not captured at the same point in time, so is less consistent than the snapshot approaches.
> — [Velero — File System Backup](https://velero.io/docs/main/file-system-backup/)

`hooks: {}` 라는 건 백업 전에 DB 를 잠그거나(`fsfreeze`), 덤프를 뜨거나, 체크포인트를 강제하는 훅이 **하나도 없다**는 뜻이다. 즉 PostgreSQL 7개와 MySQL 1개의 데이터 디렉터리를 쓰기가 진행되는 도중에 복사하고 있다. PostgreSQL 은 WAL 이 있어 크래시 복구로 대개 살아나지만, 그건 "대개"이지 보장이 아니다. 그리고 **아무도 복원을 안 해봤으면 그 보장은 검증된 적이 없다.**

정직하게 덧붙일 게 하나 더 있다. 최근 daily 백업은 Completed 로 끝나지만 매회 **경고가 257~271건**씩 달려 있다. 이 경고들이 무엇인지는 이번 조사에서 확인하지 못했다(`velero backup describe --details` 가 필요하다). "Completed 니까 괜찮다"고 넘어가기엔 숫자가 너무 일정하고 크다. 미해결 항목으로 남긴다.

**판정 C+.** 체계가 있다는 것만으로 상위권이다. 다만 백업의 품질은 "돌았는가"가 아니라 "복원되는가"로 재는 것이고, 그 시험은 아직 안 봤다.

---

## 축 5. 선언적 운영 — 여기는 잘 돼 있다

ArgoCD Application 59개 중 58개 Synced, 1개 OutOfSync(`elk-cluster`). 46개 네임스페이스 대부분이 Git 에 선언돼 있다는 뜻이고, 이건 홈랩 규모에서 흔치 않게 잘 지켜진 축이다. 노드가 통째로 날아가도 *워크로드 정의*는 안 잃는다. 축 2가 낙제인 클러스터에서 이건 생각보다 큰 안전망이다.

한 가지만 경계로 적어둔다. 59개 전부 `Healthy` 로 나오는데, **ArgoCD 의 Healthy 는 "의도한 대로 돌고 있다"보다 훨씬 약한 신호다.** 파드가 0개인 네임스페이스도 Synced/Healthy 로 표시될 수 있다 — 선언된 replicas 가 0이면 그 상태가 곧 원하는 상태이기 때문이다. 이건 공식 문서 인용이 아니라 이 클러스터를 보면서 얻은 내 판단이다. Application 의 존재 여부는 "사람이 의도했다"는 신호로 신뢰하되, health 는 별도 관측으로 확인하는 편이 안전하다.

**판정 A−.**

---

## 축 6. 명세 위생 — 나쁘지 않다

Running 컨테이너 154개 기준이다.

| 항목                 | 수  | 비율 |
| -------------------- | --- | ---- |
| 메모리 리퀘스트 없음 | 15  | 10%  |
| 메모리 리밋 없음     | 22  | 14%  |
| livenessProbe 없음   | 48  | 31%  |

리퀘스트가 90% 달려 있는 건 좋다. 스케줄러가 눈감고 배치하지 않는다는 뜻이다. liveness 없는 31% 는 애매한데, 프로브를 안 붙이는 게 맞는 워크로드(잡, 일부 사이드카)도 섞여 있어서 이 숫자만으로 나쁘다고 말할 수는 없다.

안정성 지표는 오히려 좋았다. **146개 중 131개(90%)가 재시작 0회.** 재시작이 몰린 곳은 애플리케이션이 아니라 오퍼레이터였다.

| 파드                       | 재시작 |
| -------------------------- | ------ |
| `sops-operator`            | 64     |
| `elastic-operator`         | 61     |
| `strimzi-cluster-operator` | 18     |
| `kps-grafana`              | 15     |
| `kps-kube-state-metrics`   | 14     |

오퍼레이터가 리더 선출 리스를 갱신하지 못해 스스로 종료하는 패턴은 이 클러스터에서 이전에도 관측된 적이 있다. 상위 3개가 전부 컨트롤러 런타임 기반 오퍼레이터라는 점에서 같은 계열의 문제일 가능성이 높지만, 이번 조사에서 각 파드의 종료 사유까지 확인하지는 않았으므로 추정으로 남긴다.

**판정 B.**

---

## 그래서 무엇을 먼저 고치나

세 개만 고른다. 기준은 "비용 대비 사고 시 손실 감소량"이다.

**1순위 — 백업에 훅을 붙인다.** 코드 몇 줄이고, 클러스터 구조를 하나도 안 건드리는데, 복구 가능성의 질이 바뀐다. Velero 는 [백업 훅](https://velero.io/docs/main/backup-hooks/)으로 pre/post 명령을 지원하니 PostgreSQL 은 `pg_dump` 또는 `CHECKPOINT`, MySQL 은 덤프를 pre 훅으로 걸면 된다. 그리고 **복원을 한 번 실제로 해본다.** 안 해본 백업은 백업이 아니라 희망이다.

**2순위 — 관측 스택을 데이터베이스와 다른 노드로 뗀다.** Prometheus·Grafana·Alertmanager 를 DB 7종과 같은 실패 도메인에 두는 건 순수한 손해다. 이것들도 PVC 를 물고 있어서 볼륨 이전이 필요하지만, 백업/복원으로 옮길 수 있는 규모다. 최소한 그라파나만이라도 다른 노드에 있으면, 사고 때 대시보드가 살아 있다.

**3순위 — 무상태 워크로드부터 두 겹으로 만든다.** PVC 없는 파드 108개는 지금 이 순간에도 다른 노드로 옮길 수 있다. 여기에 `replicas: 2` 와 [topologySpreadConstraints](https://kubernetes.io/docs/concepts/scheduling-eviction/topology-spread-constraints/) 를 얹는 건 스토리지 재설계 없이 가능한 유일한 가용성 개선이다. 참고로 현재 파드 중 안티어피니티를 쓰는 건 15개, 토폴로지 스프레드를 쓰는 건 5개뿐이다.

## 마지막으로 — 점수의 의미

홈랩에 프로덕션 SLO 를 들이대는 건 의미가 없다. 노드 6대로 3중화된 스토리지를 만들 이유도 없고, 만들 돈도 없다.

그래서 이 채점의 기준은 "이중화가 됐는가"가 아니라 **"무엇을 포기했는지 알고 포기했는가"**였다. 그 기준으로 보면 결과는 이렇다. 백업과 GitOps 는 *알고 한 선택*이 클러스터에 그대로 남아 있다 — 오프사이트 저장소, 두 개의 스케줄, 59개의 Application. 반면 데이터 배치는 _선택한 흔적이 없다._ 새 DB 가 필요할 때마다 기본 StorageClass 를 썼고, 기본값은 파드가 어디에 뜨든 거기 디스크를 잡았고, 그러다 보니 어쩌다 한 노드에 전부 모였다.

`kubectl get nodes` 는 여섯 줄을 출력한다. 그중 한 줄이 데이터의 100%를 들고 있는지는 그 출력 어디에도 안 적혀 있다. 그림을 그려도 안 나온다. 물어봐야만 나온다.

---

## References

- Kubernetes, [Volumes — `local`](https://kubernetes.io/docs/concepts/storage/volumes/#local) — 로컬 볼륨의 가용성·데이터 손실 특성
- Kubernetes, [Node Shutdowns](https://kubernetes.io/docs/concepts/cluster-administration/node-shutdown/) — 비정상 종료 시 StatefulSet 파드가 `Terminating` 에 갇히는 조건
- Kubernetes, [Node-pressure Eviction](https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/) — kubelet 축출이 PDB 를 지키지 않음
- Kubernetes, [Pod Quality of Service Classes](https://kubernetes.io/docs/concepts/workloads/pods/pod-qos/) — `BestEffort` → `Burstable` → `Guaranteed` 축출 순서
- Kubernetes, [Storage Classes](https://kubernetes.io/docs/concepts/storage/storage-classes/) — StorageClass 의 이름과 의미
- Kubernetes, [Topology Spread Constraints](https://kubernetes.io/docs/concepts/scheduling-eviction/topology-spread-constraints/)
- Velero, [File System Backup](https://velero.io/docs/main/file-system-backup/) — FSB 가 라이브 파일시스템을 읽는다는 명시적 한계
- Velero, [Backup Hooks](https://velero.io/docs/main/backup-hooks/)
- etcd, [FAQ — Why an odd number of cluster members?](https://etcd.io/docs/v3.5/faq/) · K3s, [High Availability Embedded etcd](https://docs.k3s.io/datastore/ha-embedded) — 쿼럼 $(n/2)+1$ 정의

_본문의 모든 수치는 2026-08-18 01:42 KST 에 `kubectl` 로 직접 수집했다. 확인하지 못한 항목(백업 경고 257~271건의 원인, 오퍼레이터 재시작의 개별 종료 사유)은 본문에 미해결로 표시했다._
