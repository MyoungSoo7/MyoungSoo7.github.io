---
layout: post
title: "오퍼레이터 157회 재시작의 범인은 리소스가 아니라 라벨 하나였다"
date: 2026-09-14 22:45:02 +0900
categories: [Engineering, Kubernetes]
tags: [Kubernetes, nodeSelector, 라벨, Strimzi, ECK, 무선클러스터, 스케줄링]
---

아침 브리핑 봇이 이런 표를 보내왔다. 6노드 K3s 홈랩(전 노드 무선) 이야기다.

| 파드 | 재시작 증가분 | 누적 |
| --- | --- | --- |
| elastic-operator-0 | +70 | 157회 |
| lemuel-entity-operator | +50 | 79회 |
| strimzi-cluster-operator | +32 | 79회 |
| settlement-financial 외 2종 | +16/+15/+13 | 신규 |

권고 사항은 "해당 노드의 리소스 부족(Memory/Disk)이나 Operator 설정 오류를 점검하십시오"였다. 결론부터 — **리소스는 범인이 아니었다. 범인은 라벨 하나였고, 그 라벨의 알리바이는 주석 속에 있었다.**

## 1. 화살표부터 뒤집기 — 재시작의 타임스탬프를 본다

재시작 횟수는 누적 계수다. **언제** 죽었는지가 없으면 "지금 아픈 것"과 "어제 아팠던 흔적"을 구분할 수 없다. 그래서 표의 파드마다 마지막 종료 시각을 실측했다:

```
settlement-financial:  16회, 마지막 종료 09-13 19:13 KST
settlement-investment: 15회, 마지막 종료 09-13 19:14 KST
settlement-market:     13회, 마지막 종료 09-13 19:15 KST
```

세 개가 2분 안에 몰려 있고, 그 시각은 [어제 잇사갈 노드의 무선 동글이 뽑혔던 바로 그 창]({% post_url 2026-09-13-wireless-k8s-node-asymmetric-latency-spof %})이다. 이후 27시간 재시작 0회. 즉 "신규 관측"으로 보고된 세 줄은 현재 진행형 장애가 아니라 **어제 사건의 화석**이었다. 이 세 줄에 대한 조사는 여기서 끝난다.

반면 entity-operator 는 오늘도 죽고 있었다. 이전 컨테이너의 로그를 보면:

```
org.apache.kafka.common.errors.TimeoutException:
  Timed out waiting to send the call. Call: fetchMetadata
```

Kafka AdminClient 가 브로커 메타데이터를 못 가져와서 기동 자체가 실패한다. 이 파드는 잇사갈(무선이 가장 약한 노드)에 있었고, 브로커는 일원 노드의 SSD PV 에 고정돼 있다. 즉 **오퍼레이터가 관리 대상과 다른 노드에, 하필 가장 약한 링크 건너편에 앉아 있었다.** 메모리도 디스크도 설정도 아니다 — 위치의 문제다.

## 2. 진범 — 주석은 의도를 말하고, 라벨은 현실을 말한다

가장 재시작이 많았던 elastic-operator(ECK)의 GitOps 매니페스트에는 이렇게 적혀 있었다:

```yaml
# operator 는 르무엘(가벼운 control-plane) 에 두지 말고 데이비드(모니터링) 에 둔다
nodeSelector:
  monitoring: "true"
```

의도는 명확하다: david 노드에 두겠다. nodeSelector 는 라벨이 일치하는 노드에만 파드를 배치하는 가장 단순한 스케줄링 제약이다.[^assign] 그런데 노드 라벨을 실측하니:

```
david    monitoring=<없음>
ilwon    monitoring=true
louise   monitoring=true
```

**정작 david 에는 그 라벨이 없었다.** 라벨은 ilwon 과 louise 에 있었고, 스케줄러는 지시받은 대로 그중 하나 — 무선이 약한 louise — 에 파드를 놓았다. 누적 157회 재시작은 그 결과다.

여기서 무서운 건 실패의 형태다. 라벨이 어디에도 없었다면 파드는 Pending 으로 남고 즉시 눈에 띄었을 것이다. 하지만 라벨이 **엉뚱한 노드에 있으면 스케줄링은 성공한다.** 에러도, 경보도, Pending 도 없다. 주석(의도)과 라벨(현실)이 어긋난 채로 시스템은 "정상 동작"하고, 비용은 재시작 카운터에만 조용히 쌓인다. 주석은 코드가 아니므로 아무도 그것을 검증하지 않는다.

## 3. 처방 — 통신 지역성으로 배치한다

무선 클러스터에서 진짜 지연에 민감한 건 데이터플레인이 아니라 **컨트롤 루프**라는 게 이번 관찰의 요지다. 오퍼레이터는 apiserver 나 브로커와 상시 커넥션을 유지해야 하고, 그 커넥션이 약한 링크를 건너면 타임아웃 → 재시작 → 백오프를 반복한다. 그래서 "누구와 통신하는가"를 기준으로 세 개를 고정했다:

| 오퍼레이터 | 통신 상대 | 고정 노드 | 근거 |
| --- | --- | --- | --- |
| entity-operator | Kafka 브로커 | ilwon | 브로커가 있는 노드 — 무선 홉 자체가 사라진다. Strimzi 는 `entityOperator.template.pod.affinity` 로 배치를 지정할 수 있다[^strimzi] |
| strimzi-cluster-operator | apiserver | ilwon | control-plane 노드라 apiserver 가 로컬이다 |
| elastic-operator | apiserver·ES | david | 원래 주석의 의도대로. ECK Helm 차트는 `nodeSelector` 값을 노출한다[^eck] |

고정 방식은 라벨 재분배가 아니라 잘 알려진 노드 라벨 `kubernetes.io/hostname`[^labels] 핀을 택했다. david 에 monitoring=true 를 붙이는 게 "원래 설계"에 가깝지만, 그 라벨을 셀렉터로 쓰는 다른 워크로드가 있으면 라벨 하나가 여러 파드를 동시에 움직인다 — 사고를 고치려다 사고 범위를 넓히는 길이다. hostname 핀은 이 파드 하나만 움직인다. 대신 노드가 죽으면 파드가 Pending 으로 남는데, **이 오퍼레이터들은 잠깐 없어도 데이터플레인이 계속 도는 종류**라 (브로커·ES 는 오퍼레이터 없이도 동작한다) 가용성보다 위치 확실성을 택했다.

## 4. 적용 후 실측

GitOps 로 커밋 → ArgoCD 동기화 → 파드 위치 실측:

```
strimzi-cluster-operator → ilwon   (재시작 0 으로 재출발)
lemuel-entity-operator   → ilwon   (재시작 0 으로 재출발)
elastic-operator-0       → david   (재시작 0 으로 재출발)
```

재시작이 실제로 멎었는지는 하루짜리 계수로 판단할 문제라 오늘은 "위치가 의도와 일치한다"까지만 사실로 적는다. 참고로 잇사갈 무선은 오늘 USB 연장선을 달아 -74 → -65 dBm, tx 17 → 103 Mbit/s 로 개선됐다 — 하지만 링크가 좋아졌다고 오퍼레이터를 약한 노드에 되돌릴 이유는 없다. 좋은 링크는 보너스고, 배치는 구조다.

## 5. 남는 교훈

1. **재시작 카운터에는 시계가 없다.** 누적 횟수만 보고 원인을 추정하면 어제의 화석과 오늘의 출혈을 구분하지 못한다. `lastState.terminated.finishedAt` 부터 본다.
2. **의도를 주석에만 적으면 드리프트는 조용하다.** "david 에 둔다"는 문장은 6개월간 아무도 검증하지 않았다. 의도는 검증 가능한 형태(정확한 셀렉터, 또는 라벨 존재를 확인하는 게이트)로 적어야 한다.
3. **무선 클러스터의 최우선 배치 대상은 컨트롤 루프다.** 파드가 어느 노드에 뜨는지 신경 쓰지 않아도 되는 건 유선 데이터센터의 사치다. 링크 품질이 비대칭인 클러스터에서는 "누구와 통신하는가"가 곧 배치 기준이 된다.

---

## References

[^assign]: Kubernetes 공식 문서 — [Assigning Pods to Nodes](https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/) (nodeSelector·nodeAffinity)
[^labels]: Kubernetes 공식 문서 — [Well-Known Labels, Annotations and Taints](https://kubernetes.io/docs/reference/labels-annotations-taints/) (`kubernetes.io/hostname`)
[^strimzi]: Strimzi 공식 문서 — [Configuring Strimzi](https://strimzi.io/docs/operators/latest/configuring) (`EntityOperatorTemplate`, `template.pod.affinity`)
[^eck]: Elastic 공식 문서 — [Install ECK using the Helm chart](https://www.elastic.co/guide/en/cloud-on-k8s/current/k8s-install-helm.html)
