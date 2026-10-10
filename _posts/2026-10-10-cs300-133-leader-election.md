---
layout: post
title: "[CS300 #133] 리더 선출 — 여럿 중 하나만 결정권을 갖게 하는 법"
date: 2026-10-10 20:13:00 +0900
categories: [cs]
tags: [cs300, distributed-systems, leader-election, lease, fencing-token]
---

컴퓨터공학 300 주제 시리즈의 133번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

리더 선출은 여러 노드 가운데 정확히 하나를 골라 "결정하는 역할" 을 맡기는 절차다. 실무에서는 합의 기반 저장소(etcd, ZooKeeper)의 임대(lease)로 리더를 정하고, 옛 리더가 깨어나 저지르는 사고는 펜싱 토큰으로 막는다.

## 왜 필요한가

여러 노드가 같은 일을 하면 문제가 되는 작업이 많다.

- 크론 작업(정산, 메일 발송)이 노드 수만큼 중복 실행된다.
- 컨트롤러 두 개가 같은 파드를 동시에 늘리고 줄이며 싸운다.
- 데이터베이스 복제본 둘이 서로 자기가 primary 라며 쓰기를 받는다(스플릿 브레인). 데이터가 갈라진다.

한 노드만 이 일을 하게 하면 단순해진다. 문제는 그 한 노드가 죽을 때다. 다른 노드가 이어받아야 한다. 그런데 앞 글들에서 봤듯이 "죽었다" 와 "느리다" 를 구별할 수 없다. 리더가 잠시 멈췄을 뿐인데 새 리더를 뽑으면, 리더가 둘이 된다. 리더 선출의 어려움은 뽑는 것이 아니라 **동시에 둘이 되지 않게** 하는 데 있다.

## 핵심 개념

### 요구 조건

- **안전성(safety)**: 어떤 순간에도 리더는 최대 하나다(적어도 같은 임기 안에서는).
- **활성(liveness)**: 리더가 사라지면 결국 새 리더가 뽑힌다.

FLP 불가능성 결과(Fischer, Lynch, Paterson, 1985)에 따르면, 메시지 지연에 상한이 없는 비동기 시스템에서 한 노드라도 멈출 수 있으면 합의를 항상 유한 시간 안에 끝내는 결정론적 알고리즘은 없다. 리더 선출도 합의 문제의 일종이다. 그래서 실제 알고리즘은 안전성은 언제나 지키고, 활성은 타임아웃과 무작위성으로 "현실적으로" 확보한다.

### 고전 알고리즘: 불리(Bully)와 링

교과서에 나오는 고전 방식들이다.

- **불리 알고리즘** (Garcia-Molina, 1982): 리더가 응답하지 않으면 자기보다 ID 가 큰 노드들에게 선거를 알린다. 아무도 대답하지 않으면 자기가 리더가 된다. 가장 큰 ID 의 살아 있는 노드가 이긴다.
- **링 알고리즘**: 논리적 링을 따라 후보 ID 를 돌리고, 한 바퀴 돈 뒤 가장 큰 ID 가 리더가 된다.

둘 다 "응답이 없으면 죽었다" 고 가정한다. 네트워크 분할에서는 양쪽이 각자 리더를 뽑아 스플릿 브레인이 될 수 있다. 그래서 오늘날 직접 구현하는 경우는 드물다.

### 과반수(쿼럼) 기반 선출

Raft 같은 합의 알고리즘은 **과반수의 표**를 얻어야 리더가 된다. 과반수 두 집합은 반드시 겹치므로, 같은 임기(term)에 리더가 둘 생길 수 없다. 분할되면 과반을 가진 쪽만 리더를 뽑는다. 이 내용은 다음 글에서 자세히 본다.

### 임대(Lease) 기반 선출: 실무의 표준

대부분의 애플리케이션은 합의를 직접 구현하지 않는다. 이미 합의로 동작하는 저장소에 "리더 자리" 를 하나 만들고 경쟁한다.

```
후보들 ──CAS(holder 비어 있거나 만료됐으면 나로)──► [ etcd / k8s Lease 객체 ]
리더   ──주기적 갱신(renew)─────────────────────►    holder=A, expires=t+15s
리더가 갱신 못 하면 → 만료 → 다른 후보가 CAS 로 차지
```

쿠버네티스는 이 목적으로 `coordination.k8s.io/v1` 의 Lease 객체를 쓴다. kube-controller-manager 와 kube-scheduler 가 여러 개 떠 있어도 실제로 일하는 것은 Lease 를 쥔 하나뿐이다. 관련 플래그 기본값은 임대 기간 15초, 갱신 기한 10초, 재시도 주기 2초다.

### 임대만으로는 부족하다: 펜싱 토큰

임대에는 시간이 개입한다. 리더 A 가 GC 나 VM 정지로 20초 멈췄다고 하자. 그동안 임대가 만료되고 B 가 리더가 된다. A 는 깨어나서 자기가 여전히 리더라고 믿고 쓰기를 보낸다. 리더가 둘인 순간이 생긴다.

해결책은 리더가 바뀔 때마다 증가하는 번호(펜싱 토큰)를 발급하고, 하류 저장소가 **본 적 있는 가장 큰 토큰보다 작은 토큰의 쓰기를 거부**하는 것이다. 리더 자신의 믿음이 아니라 저장소의 검사로 안전을 지킨다. etcd 에서는 키의 revision, ZooKeeper 에서는 zxid 같은 단조 증가 값이 이 역할을 할 수 있다.

## 직접 해 보기

임대 저장소와 펜싱 토큰을 검사하는 저장소를 만들고, 리더가 GC 로 멈췄다 깨어나는 장면을 재현한다.

```python
class LeaseStore:
    """etcd·쿠버네티스 Lease 를 흉내 낸 저장소. 시간은 정수 초로 직접 넘긴다."""
    def __init__(self): self.holder, self.expires, self.token = None, 0, 0
    def try_acquire(self, who, now, ttl=10):
        if self.holder is None or now >= self.expires or self.holder == who:
            if self.holder != who:
                self.token += 1                     # 리더가 바뀔 때마다 펜싱 토큰 증가
            self.holder, self.expires = who, now + ttl
            return self.token
        return None

class Storage:
    """펜싱 토큰을 검사하는 하류 저장소."""
    def __init__(self): self.max_token, self.value = 0, None
    def write(self, token, value):
        if token < self.max_token:
            return f"거부 (토큰 {token} < {self.max_token})"
        self.max_token, self.value = token, value
        return "ok"

lease, db = LeaseStore(), Storage()
t_a = lease.try_acquire("A", now=0);   print("t=0  A 획득 토큰", t_a)
print("t=1  A 쓰기:", db.write(t_a, "A-1"))
print("t=5  B 시도:", lease.try_acquire("B", now=5), "(아직 A 의 임대 중)")
# A 가 15초 동안 GC 로 멈춘다. 갱신을 못 해 t=10 에 임대 만료.
t_b = lease.try_acquire("B", now=12);  print("t=12 B 획득 토큰", t_b)
print("t=13 B 쓰기:", db.write(t_b, "B-1"))
print("t=15 A 깨어나 쓰기:", db.write(t_a, "A-2"), "<- 자기가 아직 리더라고 믿는다")
print("최종 값:", db.value)
```

```
t=0  A 획득 토큰 1
t=1  A 쓰기: ok
t=5  B 시도: None (아직 A 의 임대 중)
t=12 B 획득 토큰 2
t=13 B 쓰기: ok
t=15 A 깨어나 쓰기: 거부 (토큰 1 < 2) <- 자기가 아직 리더라고 믿는다
최종 값: B-1
```

A 는 t=15 에 자기가 리더라고 믿지만 저장소가 토큰을 보고 거부한다. `Storage.write` 의 토큰 검사를 지우면 A 의 옛 쓰기가 B 의 쓰기를 덮어 최종 값이 `A-2` 가 된다. 스플릿 브레인이 데이터에 남는 순간이다.

## 현업에서는

- **쿠버네티스 컨트롤러.** client-go 의 leaderelection 패키지가 Lease 기반 선출을 제공한다. 직접 만든 오퍼레이터를 여러 레플리카로 띄울 때 이 옵션을 켜야 중복 조정(reconcile)이 생기지 않는다. `kubectl get lease -n kube-system` 으로 현재 리더(holderIdentity)를 볼 수 있다.
- **k3s·etcd.** 내장 etcd 를 쓰는 k3s 고가용성 구성은 서버 노드를 홀수(보통 3)로 둔다. etcd 내부의 Raft 리더 선출이 과반에 의존하기 때문이다. 짝수 노드는 장애 허용 수를 늘리지 않고 분할 때 양쪽 모두 과반을 못 얻을 위험만 키운다.
- **데이터베이스 HA.** PostgreSQL 자동 장애 조치 도구들은 대개 etcd·Consul 같은 DCS 의 키를 리더 자리로 쓴다. 리더 키를 잃은 primary 는 스스로 쓰기를 멈추도록(자기 펜싱) 설계한다.
- **크론 중복 방지.** 여러 레플리카 중 하나만 배치 작업을 돌려야 한다면, 데이터베이스의 advisory lock 이나 Lease 로 리더를 정한다. 이때도 작업이 임대 기간보다 길어질 수 있음을 고려해야 한다.

## 확인 문제

1. 리더 선출의 진짜 어려움은 무엇인가?
2. 과반수 기반 선출에서 같은 임기에 리더가 둘 생기지 않는 이유는?
3. 임대 기반 리더가 GC 로 멈췄다 깨어났을 때 생길 수 있는 문제와 해결책은?
4. 3노드와 4노드 etcd 클러스터의 장애 허용 노드 수는 각각 몇인가?

### 풀이

1. 죽음과 느림을 구별할 수 없어서, 리더를 새로 뽑을 때 옛 리더가 살아 있으면 동시에 리더가 둘이 되는 것을 막기 어렵다.
2. 두 과반 집합은 반드시 한 노드 이상 겹치고, 각 노드는 한 임기에 한 표만 주기 때문이다.
3. 임대가 만료되어 새 리더가 생긴 뒤 옛 리더가 쓰기를 보내 데이터를 덮을 수 있다. 펜싱 토큰을 붙이고 저장소가 더 작은 토큰을 거부하게 한다.
4. 둘 다 1이다. 과반이 각각 2, 3 이므로 3노드는 1대, 4노드도 1대까지만 잃을 수 있다.

## 더 읽을거리 (References)

- [Leases — Kubernetes 공식 문서](https://kubernetes.io/docs/concepts/architecture/leases/)
- [etcd API Concurrency Reference (Election, Lock)](https://etcd.io/docs/v3.5/dev-guide/api_concurrency_reference_v3/)
- [Mike Burrows, "The Chubby lock service for loosely-coupled distributed systems", OSDI 2006](https://research.google/pubs/the-chubby-lock-service-for-loosely-coupled-distributed-systems/)
- [ZooKeeper Recipes and Solutions — Leader Election](https://zookeeper.apache.org/doc/current/recipes.html)
- Hector Garcia-Molina, "Elections in a Distributed Computing System", IEEE Transactions on Computers, 1982.
