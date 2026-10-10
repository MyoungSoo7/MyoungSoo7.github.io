---
layout: post
title: "[CS300 #139] 장애 감지와 하트비트 — 죽었는지 느린지 모를 때 판단하는 법"
date: 2026-10-10 20:19:00 +0900
categories: [cs]
tags: [cs300, distributed-systems, failure-detection, heartbeat, kubernetes]
---

컴퓨터공학 300 주제 시리즈의 139번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

장애 감지기는 하트비트 같은 주기 신호가 끊기면 그 노드를 "의심" 한다. 비동기 네트워크에서는 느린 노드와 죽은 노드를 완벽히 구별할 수 없으므로, 모든 장애 감지는 빨리 알아채기(완전성)와 잘못 의심하지 않기(정확성) 사이의 절충이다.

## 왜 필요한가

리더 선출, Raft, 복제, 샤드 재배치. 앞 글들의 메커니즘은 모두 "누가 죽었는지 안다" 는 전제에서 움직인다. 리더가 죽었다고 판단해야 새 리더를 뽑고, 노드가 죽었다고 판단해야 그 노드의 파드를 다른 곳에 띄운다.

이 판단이 틀리면 두 방향으로 사고가 난다.

- **너무 늦게 판단**: 죽은 노드로 요청이 계속 가고, 장애 시간이 길어진다.
- **너무 빨리 판단**: 잠깐 느렸을 뿐인 노드를 죽었다고 보고 리더를 바꾸거나 데이터를 옮긴다. 옮기는 작업이 부하를 만들어 다른 노드도 느려지고, 그 노드도 죽었다고 판단되는 연쇄가 생긴다.

장애 감지는 단순해 보이지만 시스템 안정성을 좌우하는 설정이다.

## 핵심 개념

### 근본적 한계

메시지 지연에 상한이 없는 비동기 시스템에서는, 응답이 없는 노드가 죽었는지 아주 느린지 유한 시간 안에 확실히 알 방법이 없다. 그래서 감지기는 "죽었다" 가 아니라 "의심한다" 고 말한다.

찬드라(Tushar Chandra)와 토우그(Sam Toueg)는 1996년 논문 "Unreliable Failure Detectors for Reliable Distributed Systems" 에서 장애 감지기를 두 성질로 분류했다.

| 성질 | 의미 |
|---|---|
| 완전성(completeness) | 실제로 죽은 노드는 결국 의심받는다 |
| 정확성(accuracy) | 살아 있는 노드를 잘못 의심하지 않는다 |

완전성은 쉽다(타임아웃을 두면 언젠가 의심한다). 정확성이 어렵다. 그리고 이 논문은 정확성이 "결국에는" 성립하는 약한 감지기만 있어도, 과반이 살아 있으면 합의를 풀 수 있음을 보였다. Raft 의 선거 타임아웃이 바로 그런 불완전한 감지기다.

### 하트비트 방식

| 방식 | 동작 | 예 |
|---|---|---|
| 푸시(push) | 감시 대상이 주기적으로 "살아 있다" 를 보낸다 | 쿠버네티스 kubelet 의 Lease 갱신, Raft 리더 하트비트 |
| 풀(pull) | 감시자가 주기적으로 물어본다 | 로드밸런서 헬스체크, 쿠버네티스 프로브 |

### 타임아웃 고르기

고정 타임아웃의 절충은 명확하다.

```
타임아웃 짧게  →  빠른 감지,  잦은 오탐(GC 멈춤, 네트워크 출렁임을 장애로 착각)
타임아웃 길게  →  느린 감지,  드문 오탐
```

흔한 규칙은 "하트비트 주기의 여러 배", 그리고 "관측된 왕복 시간 분포의 꼬리보다 넉넉하게" 다. etcd 가 선거 타임아웃을 왕복 시간의 10배 이상으로 권하는 것이 한 예다.

### 적응형 감지: φ 누적 감지기

하야시바라(Naohiro Hayashibara) 등이 2004년 제안한 φ(phi) 누적 장애 감지기는 이진 판단 대신 **의심 수준**을 연속 값으로 낸다. 최근 하트비트 간격의 분포를 학습하고, "지금까지 하트비트가 안 온 것이 그 분포에서 얼마나 드문 일인가" 를 φ = -log10(P) 로 계산한다. φ=1 이면 틀릴 확률 약 10%, φ=3 이면 약 0.1% 정도로 해석된다. 네트워크가 원래 출렁이는 환경이면 자동으로 너그러워진다. Cassandra 와 Akka 가 이 방식을 쓴다.

### 대규모 클러스터: 가십과 SWIM

노드 수천 개가 서로 하트비트를 보내면 메시지가 N² 으로 늘어난다. SWIM(2002, Das 등)은 각 노드가 주기마다 무작위 노드 하나만 ping 하고, 응답이 없으면 다른 노드 k 개에게 대신 ping 해 달라고 부탁한다(간접 ping). 자기 네트워크 문제로 인한 오탐을 줄인다. 의심 결과는 가십으로 퍼진다. HashiCorp 의 memberlist(Consul, Serf 의 기반)가 SWIM 을 확장해 쓴다.

### 무엇을 감시하는가

"프로세스가 살아 있다" 와 "일을 할 수 있다" 는 다르다. 프로세스는 살아 있지만 데드락에 걸렸을 수 있고, 데이터베이스 연결이 끊겼을 수 있다. 감시 신호가 무엇을 증명하는지 분명히 해야 한다.

## 직접 해 보기

1초마다 하트비트를 보내는 노드가 있다. 네트워크 지연이 조금 출렁이고, 1% 확률로 1~5초 멈춘다(GC 등). 5~8분 살다가 죽는 실행을 200번 반복하며, 타임아웃마다 "살아 있는데 의심한 횟수" 와 "죽은 뒤 알아채기까지 걸린 시간" 을 잰다.

```python
import random
random.seed(11)

INTERVAL = 1.0                                   # 하트비트 주기 1초

def heartbeat_times(duration, crash_at):
    """살아 있는 동안 하트비트 도착 시각. 지연 변동 + 가끔 긴 멈춤(GC 등)."""
    t, out = 0.0, []
    while t < crash_at:
        out.append(t + max(0, random.gauss(0.05, 0.02)))           # 네트워크 지연 변동
        t += INTERVAL
        if random.random() < 0.01: t += random.uniform(1, 5)      # 1%: 1~5초 멈춤(GC 등)
    return out

def evaluate(timeout, runs=200, duration=600):
    false_alarms, detect = 0, []
    for _ in range(runs):
        crash_at = random.uniform(300, 500)
        beats = heartbeat_times(duration, crash_at)
        for prev, nxt in zip(beats, beats[1:]):       # 살아 있는데 간격이 timeout 초과
            if nxt - prev > timeout: false_alarms += 1
        detect.append(beats[-1] + timeout - crash_at)  # 마지막 하트비트 + timeout 에 탐지
    return false_alarms / runs, sum(detect) / runs

print("timeout  실행당 오탐  평균 탐지 지연")
for timeout in (1.5, 3, 5, 8):
    fa, d = evaluate(timeout)
    print(f"{timeout:5.1f}s   {fa:7.2f}회     {d:6.2f}s")
```

```
timeout  실행당 오탐  평균 탐지 지연
  1.5s      3.75회       0.97s
  3.0s      2.87회       2.39s
  5.0s      0.92회       4.43s
  8.0s      0.00회       7.50s
```

타임아웃을 줄이면 빨리 알아채지만 멀쩡한 노드를 자주 의심한다. 1.5초면 한 번 실행에 4번 가까이 헛경보가 울린다. 8초면 헛경보는 사라지지만 장애를 알아채는 데 7초 넘게 걸린다. 공짜 점심은 없다. 멈춤 분포를 알면 그보다 약간 긴 타임아웃을 고를 수 있고, 그 분포를 자동으로 학습하는 것이 φ 누적 감지기의 발상이다.

## 현업에서는

- **쿠버네티스 노드.** kubelet 은 기본 10초마다 자기 Lease 객체를 갱신한다. 컨트롤 플레인의 노드 수명주기 컨트롤러는 `node-monitor-grace-period`(현재 문서 기준 기본 50초) 동안 소식이 없으면 노드의 Ready 상태를 Unknown 으로 바꾸고 `node.kubernetes.io/unreachable` 테인트를 붙인다. 파드에는 이 테인트를 기본 300초 견디는 톨러레이션이 붙어 있어서, 노드가 죽어도 파드가 다른 노드로 옮겨지기까지 몇 분이 걸린다. 일시적인 네트워크 문제로 파드를 대량 이동시키지 않으려는 보수적 기본값이다.
- **컨테이너 프로브.** liveness 프로브는 "재시작해야 하나", readiness 프로브는 "트래픽을 보내도 되나" 를 묻는다. liveness 에 데이터베이스 연결 확인을 넣으면 DB 장애 하나에 모든 파드가 재시작을 반복한다. liveness 는 프로세스 자체의 건강만, 의존성은 readiness 로 보는 것이 일반적 권장이다.
- **홈랩 클러스터.** 무선으로 연결된 노드나 CPU 가 약한 노드는 순간적으로 하트비트가 늦어 NotReady 로 깜빡이기 쉽다. 이럴 때 타임아웃을 무작정 줄이면 오탐이 늘고, 늘리면 실제 장애 대응이 느려진다. 먼저 하트비트가 늦는 원인(전파 세기, 디스크 지연, CPU 경합)을 지표로 확인하는 것이 순서다.
- **알림 설계.** 모니터링 경보도 장애 감지기다. "1번 실패하면 경보" 는 오탐이 많다. "5분 중 3번 실패" 처럼 창을 두는 것이 같은 절충이다.

## 확인 문제

1. 비동기 시스템에서 완벽한 장애 감지가 불가능한 이유는?
2. 장애 감지기의 완전성과 정확성을 각각 설명하라.
3. 타임아웃을 너무 짧게 잡았을 때 생길 수 있는 연쇄 효과는?
4. SWIM 의 간접 ping 은 어떤 오탐을 줄이는가?
5. liveness 프로브에 외부 DB 연결 확인을 넣으면 왜 위험한가?

### 풀이

1. 메시지 지연에 상한이 없어서, 응답이 없는 노드가 죽은 것인지 아주 느린 것인지 유한 시간 안에 구별할 수 없다.
2. 완전성은 실제로 죽은 노드를 결국 의심하는 것, 정확성은 살아 있는 노드를 잘못 의심하지 않는 것이다.
3. 멀쩡한 노드를 죽었다고 보고 리더 교체·데이터 이동을 일으키고, 그 부하로 다른 노드도 느려져 또 오탐되는 연쇄가 생긴다.
4. 감시하는 쪽 노드나 그 경로의 네트워크 문제 때문에 대상이 죽은 것처럼 보이는 오탐을 줄인다. 다른 노드들이 대신 확인해 주기 때문이다.
5. DB 장애 하나로 모든 파드가 동시에 재시작을 반복해 장애가 커진다. 재시작은 DB 문제를 고치지 못한다.

## 더 읽을거리 (References)

- [Tushar D. Chandra, Sam Toueg, "Unreliable Failure Detectors for Reliable Distributed Systems", Journal of the ACM, 1996 (PDF)](https://www.cs.utexas.edu/~lorenzo/corsi/cs380d/papers/p225-chandra.pdf)
- [Das, Gupta, Motivala, "SWIM: Scalable Weakly-consistent Infection-style Process Group Membership Protocol", DSN 2002 (PDF)](https://research.cs.cornell.edu/projects/Quicksilver/public_pdfs/SWIM.pdf)
- [Node Status (Heartbeats) — Kubernetes 공식 문서](https://kubernetes.io/docs/reference/node/node-status/)
- [Configure Liveness, Readiness and Startup Probes — Kubernetes 공식 문서](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/)
- Naohiro Hayashibara et al., "The φ Accrual Failure Detector", IEEE SRDS 2004.
