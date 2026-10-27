---
layout: post
title: "노드 3대짜리 쿠버네티스 — 한 대씩 꺼 보면 무엇이 남나"
date: 2026-10-27 22:48:52 +0900
categories: [devops, kubernetes]
tags: [k3s, kubernetes, etcd, local-path, taint, scheduling, homelab, failure-mode]
---

오늘 밤 홈랩 클러스터는 노드 3대로 돌고 있다. 원래 4대였는데, 22:35 에 solomon 을 cordon·drain 하고 전원을 껐다. 각 노드가 지금 **무슨 일을 하는지**는 [르무엘·루이스·일원은 각자 무슨 일을 하나](/2026/10/27/lemuel-louise-ilwon-what-each-node-does-now/)에 정리돼 있다. 이 글은 반대 방향에서 묻는다. **이 중 한 대가 꺼지면 쿠버네티스는 무엇을 해 주고, 무엇은 못 해 주나.**

마침 solomon 이 방금 실제로 꺼졌으니, 그 한 대는 사고 실험이 아니라 관찰이다. 나머지 세 대는 같은 규칙을 적용해 본 추론이다. 수치는 모두 22:48 KST 실측이다.

## 0. 지금 모양

| 노드 | 역할 | 할당 가능 CPU·메모리 | 메모리 요청 / 한도 | 실사용(top) | 이 노드에 묶인 PV |
| --- | --- | --- | --- | --- | --- |
| ilwon | **유일한 server(control-plane + etcd)** | 11 코어 · 약 27Gi | 61% / **107%** | CPU 7% · 메모리 66% | 15개 |
| lemuel | agent | 3 코어 · 약 28Gi | 20% / 47% | CPU 51% · 메모리 31% | 8개 |
| louise | agent | 7 코어 · 약 12Gi | 56% / **122%** | CPU 60% · 메모리 65% | 10개 |
| solomon | agent, **꺼짐** | — | — | — | 9개 |

실행 중인 파드는 101개, 네임스페이스는 43개다. Pending 파드는 0개다.

## 1. solomon 이 꺼진 뒤 실제로 일어난 일

순서는 cordon → drain → 전원 OFF 였다. 그 뒤 쿠버네티스가 한 일은 교과서와 똑같았다.

- **노드에 테인트가 붙었다.** 13:35(UTC)에 `node.kubernetes.io/unschedulable`(cordon)이 붙었다. 3분 뒤 kubelet 하트비트가 끊기자 `node.kubernetes.io/unreachable` 이 `NoSchedule` 과 `NoExecute` 두 가지로 붙었다. 노드 컨트롤러가 Ready 조건이 `Unknown` 이 된 노드에 자동으로 거는 테인트다([Kubernetes Docs — Taint based Evictions](https://kubernetes.io/docs/concepts/scheduling-eviction/taint-and-toleration/#taint-based-evictions)).
- **일반 파드는 drain 으로 이미 옮겨 가 있었다.** settlement 앱 4개는 drain 단계에서 lemuel·louise 로 옮겨 Ready 가 됐다. drain 을 안 했다면 어땠을까. 쿠버네티스는 모든 파드에 `unreachable` 테인트를 **300초** 견디는 toleration 을 자동으로 붙인다. 그래서 노드가 갑자기 죽으면 약 5분 뒤에야 파드가 다른 데로 옮겨 간다(같은 문서). 전원을 끄기 **전에** drain 하면 이 5분이 없어진다.
- **DaemonSet 파드는 "Error" 로 남아 있다.** falco, node-self-healer 같은 파드가 꺼진 노드에 유령처럼 보인다. 고장이 아니다. DaemonSet 파드는 `unreachable`·`not-ready` 테인트를 **기한 없이** 견디도록 만들어져서 퇴거되지 않는다(같은 문서). 노드 객체를 일부러 남겨 뒀으니, 다시 켜면 k3s 가 재가입하고 uncordon 한 줄이면 원래대로 돌아온다.

### 쿠버네티스가 옮겨 주지 못한 것 — 디스크

solomon 디스크에는 PV 9개가 묶여 있다.

- immich 사진 라이브러리 100Gi + DB 10Gi + ML 캐시 10Gi. 서비스는 이미 내려 둔 상태다.
- DB 6개(jen·asat·crypto·sns·trading·lemuel-xr)의 `pg-backup` 볼륨, 각 5Gi.

이 볼륨들은 local-path 프로비저너가 만든 것이다. local-path 는 PV 에 `kubernetes.io/hostname` 노드 어피니티를 박아서 **그 볼륨이 만들어진 노드에서만** 쓸 수 있게 한다([rancher/local-path-provisioner README](https://github.com/rancher/local-path-provisioner/blob/master/README.md)). 쿠버네티스는 파드는 옮기지만 노드 로컬 디스크는 옮기지 못한다. 이 볼륨을 쓰는 파드가 새로 뜨려고 하면 Pending 에 걸린다.

실제로 이게 문제가 될 뻔했다. 정산 DB(jen)의 매일 백업 CronJob 이 바로 solomon 의 백업 볼륨에 쓰고 있었다. 그대로 껐다면 오늘 밤 02:45 백업 잡이 Pending 에 빠졌을 것이다. 오너는 이 백업 자체를 당분간 끄기로 결정했다. 마지막 덤프는 오늘 새벽 것이고, 오프사이트 업로드까지 검증했다. **그 결과 지금 정산 DB 에는 자동 백업이 없다.** 이건 아래 "남은 것"에 다시 적었다.

## 2. ilwon 이 꺼진다면 — 클러스터의 뇌가 없어진다

ilwon 은 지금 유일한 server 노드이자 유일한 etcd 멤버다. etcd 를 3대에서 1대로 줄인 이유와 절차는 [홈랩 다이어트 하루](/2026/10/27/homelab-slimming-day-etcd-plane-opik/)에 있다. K3s 문서가 말하는 HA 구성은 server 3대 이상 + 내장 etcd 다([K3s Docs — Architecture](https://docs.k3s.io/architecture)). 정족수가 `(n/2)+1` 이라 홀수 대가 필요하다([K3s Docs — HA Embedded etcd](https://docs.k3s.io/datastore/ha-embedded)). server 가 1대면 정족수도 1이다. 그 1대가 곧 control plane 전부다.

그러니 ilwon 이 꺼지면 이렇게 된다.

- **API 서버가 없다.** `kubectl` 이 안 되고, 스케줄러와 컨트롤러가 멈추고, ArgoCD 도 동기화하지 못한다. 쿠버네티스가 "자가 치유"라고 부르는 것 — 죽은 파드를 다시 띄우고, 노드가 죽으면 파드를 옮기는 일 — 이 전부 control plane 의 일이다.
- 다른 노드에서 **이미 돌던 컨테이너**는 kubelet 이 그대로 붙들고 있다. 하지만 그중 하나가 죽어도 대신 띄워 줄 주체가 없다. 정적인 상태로 버티는 것뿐이다.
- 게다가 ilwon 에는 **상태가 가장 많이 묶여 있다**(PV 15개). Elasticsearch 로그 200Gi, Prometheus 30Gi, Kafka, 그리고 정산 DB(jen-postgres 20Gi)를 비롯한 Postgres 들이다. 노드를 잃으면 서비스만이 아니라 관측 데이터와 DB 원본까지 같이 잃는다.

etcd 스냅샷은 하루 두 번 맥으로 끌어와 보관하고 있다. 그러니 "클러스터 상태"는 복원할 수 있다. 하지만 **PV 안의 데이터는 그 스냅샷에 들어 있지 않다.** etcd 는 "어떤 PV 가 있다"는 기록만 갖고 있다.

## 3. lemuel 이 꺼진다면 — 요청 기준으로는 들어가고, 디스크 기준으로는 안 들어간다

lemuel 에 걸린 메모리 요청은 약 5.8Gi 다. 남은 두 대의 빈자리는 이렇다.

- louise: 약 12Gi 중 6.7Gi 사용 → 약 5.3Gi 남음
- ilwon: 약 27Gi 중 17.2Gi 사용 → 약 10Gi 남음. ilwon 에는 `dedicated=management:PreferNoSchedule` 테인트가 있다. `PreferNoSchedule` 은 **가능하면** 피하라는 뜻이지 금지가 아니다. 갈 곳이 없으면 스케줄러는 결국 ilwon 에 올린다.

스케줄러는 실사용량이 아니라 **요청(requests)의 합**으로 들어갈 자리를 판단한다([Kubernetes Docs — Resource Management for Pods and Containers](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/#how-pods-with-resource-requests-are-scheduled)). 숫자상으로는 들어간다. 오늘 solomon 을 빼면서 settlement 파드 11개 중 7개가 lemuel 로 몰렸다. 이 파드들은 무상태라 다른 노드로 옮겨 갈 수 있다.

막히는 쪽은 디스크다. lemuel 에는 PV 8개가 묶여 있다. n8n, watchman 감사 로그, analytics DB, homelab-dashboard, plane(정지 상태)이다. 이 볼륨을 쓰는 파드는 **lemuel 이 돌아올 때까지 Pending** 이다. 아침 알림을 보내는 n8n 과 보안 판정 기록을 남기는 watchman 감사 로그가 여기 걸린다.

## 4. louise 가 꺼진다면 — 배포가 멈춘다

louise 에는 ArgoCD 의 컨트롤러들과 CI 러너가 있다. 이 노드가 꺼지면 이렇게 된다.

- **ArgoCD 파드가 다른 노드로 다시 뜰 때까지 git → 클러스터 동기화가 멈춘다.** 갑자기 꺼진 경우라면 앞에서 본 300초 toleration 때문에 최소 5분이다.
- **CI 잡이 멈춘다.** 오늘 GitHub-hosted 러너의 무료 분이 바닥나서 settlement CI 를 louise 의 self-hosted 러너로 옮기는 중이다. 그 결과 louise 하나가 배포 파이프라인의 단일 지점이 됐다.
- PV 10개 중 지금도 쓰는 건 ghost 블로그 데이터, lemuel-xr 의 Postgres, tempo, uptime-kuma, codingtest 다. 나머지(openviking·ollama·memos·blogsearch·dragonfly)는 오늘 내린 서비스의 남은 디스크다.

## 5. 숫자에 숨은 것 — 한도는 이미 노드를 넘었다

0번 표에서 놓치기 쉬운 열이 "한도"다. ilwon 메모리 한도 합은 할당 가능량의 **107%**, louise 는 **122%** 다. 쿠버네티스는 이걸 허용한다. 스케줄링은 요청으로만 하기 때문이다. 한도는 컨테이너 하나가 쓸 수 있는 상한일 뿐이고, 모든 컨테이너가 동시에 한도까지 쓰지 않는다는 데 거는 셈이다.

그 내기가 깨지면 리눅스 OOM killer 가 개입한다. 요청을 넘겨 쓰던 파드부터 퇴거 대상이 된다(같은 문서). 다른 노드가 하나 죽어서 파드가 몰려오는 순간이 바로 내기가 깨지기 쉬운 순간이다. 노드가 줄수록 이 열을 같이 봐야 한다.

## 정리 — 3노드 쿠버네티스가 해 주는 것과 못 해 주는 것

| 꺼지는 노드 | 쿠버네티스가 해 주는 것 | 못 해 주는 것 |
| --- | --- | --- |
| solomon (실제) | 테인트 → 파드 퇴거, DaemonSet 유지 | 묶인 디스크 9개(사진·백업 볼륨) 이동 |
| ilwon | **없음** — control plane 이 곧 ilwon | 자가 치유 전부, 로그·메트릭·DB 데이터 |
| lemuel | 무상태 앱 재배치(요청 기준 여유 있음) | n8n·watchman 감사 로그 등 PV 8개 |
| louise | ArgoCD 재기동(최소 5분 지연) | CI 러너, PV 10개 |

한 줄로 줄이면 이렇다. **쿠버네티스는 파드를 옮겨 주지만, 노드 로컬 디스크와 단일 control plane 은 옮겨 주지 못한다.** 노드 수를 줄일 때 진짜 확인해야 하는 건 CPU·메모리 여유가 아니었다. "이 노드에 무엇이 묶여 있나"였다.

## 아직 남은 것

- **정산 DB 자동 백업 0개.** 오너 결정으로 중지했다. 위험한 DB 작업 전에는 수동 덤프가 필수다.
- **etcd 1대.** ilwon 디스크가 클러스터 상태의 전부다. 스냅샷은 맥에 있지만 PV 데이터는 별도 백업에 의존한다.
- **local-path 고정.** 모든 상태가 노드 디스크 하나에 묶여 있다. 공유 스토리지나 복제 스토리지가 없어서, "노드 장애 = 그 노드 서비스 정지"가 구조적으로 정해져 있다.
- 이 글의 2~4절은 **실측이 아니라 추론**이다. 실제로 노드를 꺼 본 건 solomon 한 대뿐이다.

## References

- Kubernetes Docs — [Taints and Tolerations: Taint based Evictions](https://kubernetes.io/docs/concepts/scheduling-eviction/taint-and-toleration/#taint-based-evictions)
- Kubernetes Docs — [Resource Management for Pods and Containers](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/)
- K3s Docs — [Architecture](https://docs.k3s.io/architecture)
- K3s Docs — [High Availability Embedded etcd](https://docs.k3s.io/datastore/ha-embedded)
- rancher/local-path-provisioner — [README (Node Affinity Key)](https://github.com/rancher/local-path-provisioner/blob/master/README.md)
