---
layout: post
title: "K3s logs-es-cold 가 4 시간 Pending 이던 이유 — nodeSelector 만 있고 toleration 이 빠진 함정"
date: 2026-05-26 04:00:00 +0900
categories: [infra, kubernetes, elasticsearch]
tags: [k3s, elastic, eck, taint, toleration, helm, gitops, debugging, homelab]
---

K3s 홈랩의 *logs-es-cold-0* (Elasticsearch cold tier) 가 **4 시간 32 분 Pending** 으로 떠있었다. PVC 도 bound 되어 있고, target node (solomon) 는 Ready 였다. 그런데도 scheduler 가 거부.

원인은 *taint vs toleration 의 비대칭*. nodeSelector 만 있고 toleration 이 없었던 것.

---

## 1. 증상

```text
$ kubectl get pod -n logging logs-es-cold-0
NAME             READY   STATUS    RESTARTS   AGE
logs-es-cold-0   0/1     Pending   0          23h
```

스케쥴러 로그:

```text
$ kubectl describe pod -n logging logs-es-cold-0
Node-Selectors:  kubernetes.io/hostname=solomon
Tolerations:     node.kubernetes.io/not-ready:NoExecute op=Exists for 300s
                 node.kubernetes.io/unreachable:NoExecute op=Exists for 300s
Events:
  Warning  FailedScheduling  default-scheduler
    0/5 nodes are available:
    1 node(s) had untolerated taint(s),
    1 node(s) were unschedulable,
    3 node(s) didn't match Pod's node affinity/selector.
```

번역:
- `3 node(s) didn't match Pod's node affinity/selector` → lemuel·louise·david (hostname ≠ solomon)
- `1 node(s) were unschedulable` → 사용자가 cordon 해둔 노드
- `1 node(s) had untolerated taint(s)` → **solomon. 여기가 진짜 핵심.**

---

## 2. PVC 는 정상

```text
$ kubectl get pvc -n logging
NAME                                STATUS   VOLUME                CAPACITY   STORAGECLASS
elasticsearch-data-logs-es-cold-0   Bound    elk-cold-solomon-1    500Gi      elk-cold
```

`elk-cold-solomon-1` 이라는 PV 가 solomon 의 로컬 SSD 에 미리 만들어져있다. PVC 는 Bound. *데이터를 어디 쓸지* 는 문제 없다.

---

## 3. taint 확인

```text
$ kubectl describe node solomon | grep Taints
Taints:  dedicated=storage:NoSchedule
```

홈랩에서 *solomon (2014 Mac Mini)* 는 **저장 전용 노드** 로 분리해뒀다. 일반 워크로드가 자기 메모리 빨아먹지 않게 `dedicated=storage:NoSchedule` taint 로 격리.

→ 이 taint 를 *통과* 하려면 pod 가 명시적으로 toleration 을 가져야 한다.

```yaml
tolerations:
  - key: dedicated
    operator: Equal
    value: storage
    effect: NoSchedule
```

logs-es-cold STS 에는 이게 *없었다*. 그래서 nodeSelector 로 solomon 만 지정해놓고도, *문 앞에서 막힌* 상태였다.

---

## 4. taint 와 nodeSelector 는 *서로 보완* 관계가 아니다

흔히 헷갈리는 부분:

| 메커니즘 | 방향 | 의미 |
|---|---|---|
| **nodeSelector** | pod → node | "이 node 만 가고 싶다" |
| **node affinity** | pod → node | nodeSelector 의 강력판 (soft/hard, in/notIn 등) |
| **taint** | node → pod | "내 위에 아무거나 못 올린다" |
| **toleration** | pod → node | "그 taint 견딜 수 있다" |

→ nodeSelector + node taint 가 *동시에* 있는 노드에 가려면 *둘 다* 통과해야 한다. nodeSelector 만으로는 taint 가 *그냥 안 보이는 게 아니라 reject 한다*.

이게 헷갈리는 이유: 일반적으로 nodeSelector 가 *지정하면* 거기로 가는데, *taint 막혀서 안 갔다* 는 게 직관에 안 맞아서.

---

## 5. fix — 두 단계

### A. 임시 (즉시 띄우기)

```bash
kubectl patch sts -n logging logs-es-cold --type=merge -p '
{"spec":{"template":{"spec":{"tolerations":[
  {"key":"dedicated","operator":"Equal","value":"storage","effect":"NoSchedule"}
]}}}}'
```

60 초 후:

```text
$ kubectl get pod -n logging logs-es-cold-0 -o wide
NAME             READY   STATUS     RESTARTS   IP            NODE
logs-es-cold-0   0/1     Init:2/4   0          10.42.6.171   solomon
```

→ solomon 으로 정상 스케쥴. Init container 작업 (sysctl `vm.max_map_count=262144` 등) 진행.

### B. 영구화 (Helm chart)

`charts/elk-cluster/templates/elasticsearch.yaml` 의 cold tier podTemplate.spec 에 tolerations 추가:

```yaml
podTemplate:
  spec:
    nodeSelector:
      kubernetes.io/hostname: {{ .Values.elasticsearch.cold.nodeHostname }}
    tolerations:
      - key: dedicated
        operator: Equal
        value: storage
        effect: NoSchedule
    initContainers:
      ...
```

ArgoCD sync 이후 *재배포 시* 자동 적용. 임시 patch 가 *덮어써져도* 같은 toleration 이 들어가니 OK.

---

## 6. 왜 이게 어제까지 안 보였나

logs-es-cold 가 사실 *처음부터* taint 못 통과하던 것 같지만, **이전에는 노드에 taint 가 없었다**. 며칠 전 solomon 을 "storage 전용" 으로 격리하면서 `dedicated=storage:NoSchedule` 을 추가했고, 그때 *기존 pod (logs-es-cold-0) 는 이미 running 상태라서 그대로 살아있었다.*

(taint 는 *기존 pod 를 쫓아내지 않는다* — `NoSchedule` 은 *신규* 스케쥴만 막는다. `NoExecute` 면 쫓아낸다.)

새벽에 ilwon 작업 + louise 재부팅 cascade 가 일어나면서 *logs-es-cold-0 가 evict* 되었고, *재생성* 하려는데 taint 막혀서 4 시간 Pending.

---

## 7. cluster 격리 패턴 — taint + toleration 의 *철학*

`dedicated=storage:NoSchedule` 를 쓴 이유:
- solomon = 2014 Mac Mini, 메모리 작음
- *일반 워크로드가 잘못 들어오면* OOMKilled 또는 다른 ES tier 와 메모리 경합
- *명시적으로 storage 라벨 받은 pod 만* 허용하고 싶음

이 패턴은 *클러스터에서 노드의 역할* 을 코드로 표현하는 방법이다. 별도 "이 노드는 X 용입니다" 문서를 보지 않아도 *taint 가 곧 문서* 다.

대신 *모든 storage workload* 에 toleration 을 *반드시* 박아야 한다. 빠뜨리면 오늘처럼 *Pending 4 시간*.

---

## 8. checklist

새 노드에 taint 를 추가할 때:

- [ ] 해당 노드를 *써야 하는* 모든 워크로드 (deployment, sts, ds, job) 찾기 (label selector / nodeSelector / nodeName 기준)
- [ ] 각각의 podTemplate 에 toleration 추가
- [ ] Helm chart / Kustomize / GitOps 에 반영 (live patch 만 하면 *다음 sync* 에 사라짐)
- [ ] *기존 running pod* 가 evict 되면 재스케쥴 가능한지 *시뮬레이션* (`kubectl drain --dry-run` 비슷한 효과)
- [ ] CD pipeline 이 *toleration drift* 를 잡는지 확인 (없으면 자동 alarm 미스)

오늘 같은 사고 = checklist 의 2 번을 빠뜨린 결과.
