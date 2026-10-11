---
layout: post
title: "[SE100 #088] 정형 기법 — TLA+ 와 모델 체킹"
date: 2026-10-11 17:08:57 +0900
categories: [software-engineering]
tags: [se100, quality-reliability, formal-methods, tla-plus, model-checking]
---

소프트웨어 공학 100 주제 시리즈의 88번째 글이다. (카테고리: 품질·신뢰성·보안)

## 한 줄 요약

TLA+ 는 시스템을 **상태와 상태 전이**로 기술하는 수학적 명세 언어이고, 모델 체커 TLC 는 그 명세가 허용하는 모든 실행을 기계적으로 탐색해 불변식이 깨지는 **반례 실행**을 찾아 준다. 테스트가 "몇 개의 실행" 을 확인한다면, 모델 체킹은 "작은 범위의 모든 실행" 을 확인한다.

## 왜 필요한가

동시성·분산 시스템의 버그는 대개 **드문 인터리빙**에서 나온다. 두 프로세스가 같은 값을 읽고 둘 다 덮어쓰는 갱신 손실, 리더 교체 도중 두 노드가 동시에 리더라고 믿는 상황, 재시도와 타임아웃이 엇갈리며 생기는 중복 처리. 이런 버그는 단위 테스트로 거의 재현되지 않고, 통합 테스트에서는 수천 번에 한 번 나타났다 사라진다.

AWS 엔지니어들은 [Use of Formal Methods at Amazon Web Services](https://lamport.azurewebsites.net/tla/formal-methods-amazon.pdf) (2014년 9월 보고서, 이후 [CACM 58(4), 2015](https://doi.org/10.1145/2699417) 에 게재)에서 이렇게 썼다. 깊은 설계 리뷰, 코드 리뷰, 정적 분석, 스트레스 테스트, 결함 주입 테스트를 모두 하지만 복잡한 동시성·장애 허용 시스템에는 여전히 미묘한 버그가 숨는다. 그리고 그 이유 중 하나로, 초당 수백만 요청 규모에서 "극히 드문" 사건 조합의 실제 확률을 사람의 직관이 잘 추정하지 못한다는 점을 든다.

## 핵심 개념

### 정형 기법의 스펙트럼

| 수준 | 하는 일 | 대표 도구 | 비용 |
|---|---|---|---|
| 정형 명세 | 설계를 수학으로 정확히 적는다 | TLA+, Alloy, Z | 낮음~중간 |
| 모델 체킹 | 유한한 모델의 모든 상태를 자동 탐색 | TLC, Apalache, SPIN, Alloy Analyzer | 중간 (상태 폭발이 한계) |
| 정리 증명 | 무한한 경우까지 성립함을 증명 | TLAPS, Coq/Rocq, Isabelle | 높음 |

현업에서 가장 많이 쓰이는 지점은 가운데, **명세 + 모델 체킹**이다. 증명만큼 강하지 않지만, 사람의 리뷰보다 훨씬 체계적이고 학습 비용이 감당할 만하다.

모델 체킹이라는 분야 자체는 1980년대 초 Clarke·Emerson 과 Queille·Sifakis 의 연구에서 시작되었고, Clarke, Emerson, Sifakis 는 이 공로로 [2007년 ACM 튜링상](https://amturing.acm.org/award_winners/clarke_1167964.cfm)을 받았다.

### TLA 와 TLA+

Leslie Lamport 는 [The Temporal Logic of Actions](https://lamport.azurewebsites.net/pubs/lamport-actions.pdf) (ACM TOPLAS 16(3):872–923, 1994; [DOI](https://doi.org/10.1145/177492.177726))에서 TLA 를 제시했다. 핵심 주장은 **알고리즘과 그 성질을 같은 논리의 식으로 쓰고, "알고리즘이 성질을 만족한다" 를 논리적 함의로 표현한다**는 것이다. TLA+ 는 여기에 집합론 기반 자료 구조와 모듈 체계를 더한 언어이며, Lamport 의 책 *Specifying Systems: The TLA+ Language and Tools for Hardware and Software Engineers* (Addison-Wesley, 2002)가 [무료로 공개](https://lamport.azurewebsites.net/tla/book.html)되어 있다. 언어와 도구는 현재 [TLA+ Foundation](https://foundation.tlapl.us/) 이 관리한다.

TLA+ 명세의 뼈대는 늘 같다.

```
Spec == Init /\ [][Next]_vars /\ Fairness
```

| 요소 | 의미 |
|---|---|
| `Init` | 가능한 초기 상태들을 기술하는 술어 |
| `Next` | 한 단계 전이(액션)들. 프라임(`x'`)은 다음 상태의 값 |
| `[][Next]_vars` | 모든 단계가 `Next` 이거나 `vars` 가 그대로인 단계(stuttering) |
| `Fairness` | "결국 일어나야 할 일" 을 위한 공정성 조건 (활성 성질 검사용) |

검사할 성질은 두 종류다. **안전성(safety)** 은 "나쁜 일이 절대 일어나지 않는다"(불변식: 리더는 최대 한 명), **활성(liveness)** 은 "좋은 일이 결국 일어난다"(요청은 결국 응답된다). 안전성 위반은 유한한 반례 경로로, 활성 위반은 끝없이 도는 루프 경로로 나타난다.

### 도구

[Lamport 의 도구 페이지](https://lamport.azurewebsites.net/tla/tools.html)가 정리한 주요 도구는 다음과 같다.

- **TLC**: 명시적 상태(explicit-state) 모델 체커. 상태를 하나씩 생성하며 너비 우선으로 탐색한다.
- **Apalache**: TLC 의 대안인 기호적(symbolic) 모델 체커.
- **PlusCal**: 의사코드에 가까운 알고리즘 언어. TLA+ 로 번역된다.
- **TLAPS**: TLA+ 증명 시스템.

## 예제

### 갱신 손실을 TLA+ 로

두 프로세스가 공유 변수 `x` 를 "읽고 → 1 더해 쓰는" 두 단계로 증가시킨다. 원자적이지 않다.

```
---------------------------- MODULE Counter ----------------------------
EXTENDS Naturals
VARIABLES x, pc, tmp
Procs == {"p", "q"}
vars  == <<x, pc, tmp>>

Init == /\ x = 0
        /\ pc  = [i \in Procs |-> "read"]
        /\ tmp = [i \in Procs |-> 0]

Read(i)  == /\ pc[i] = "read"
            /\ tmp' = [tmp EXCEPT ![i] = x]
            /\ pc'  = [pc  EXCEPT ![i] = "write"]
            /\ UNCHANGED x

Write(i) == /\ pc[i] = "write"
            /\ x'  = tmp[i] + 1
            /\ pc' = [pc EXCEPT ![i] = "done"]
            /\ UNCHANGED tmp

Finished == /\ \A i \in Procs : pc[i] = "done"
            /\ UNCHANGED vars                 \* 종료 상태를 교착으로 보지 않게

Next == (\E i \in Procs : Read(i) \/ Write(i)) \/ Finished
Spec == Init /\ [][Next]_vars

AllDoneImpliesTwo == (\A i \in Procs : pc[i] = "done") => x = 2
=========================================================================
```

설정 파일에 `INVARIANT AllDoneImpliesTwo` 를 주고 TLC 를 돌리면 불변식 위반과 함께 반례 경로를 내놓는다. p 가 읽고(0), q 가 읽고(0), p 가 쓰고(1), q 가 쓴다(1). 끝났는데 `x = 1` 이다.

### 모델 체커가 하는 일, 직접 흉내 내기

TLC 의 핵심 동작은 "도달 가능한 상태를 너비 우선으로 모두 생성하고, 각 상태에서 불변식을 확인하고, 위반 시 부모 포인터를 따라 경로를 복원" 하는 것이다. 위 명세를 파이썬으로 옮기면 다음과 같다.

```python
from collections import deque

# 상태: (x, (pc_p, tmp_p), (pc_q, tmp_q))   pc ∈ {"read", "write", "done"}
init = (0, ("read", 0), ("read", 0))

def next_states(s):
    x, *locals_ = s
    for i, (pc, tmp) in enumerate(locals_):
        new = list(locals_)
        if pc == "read":
            new[i] = ("write", x);  yield (x, *new)
        elif pc == "write":
            new[i] = ("done", tmp); yield (tmp + 1, *new)

def invariant(s):                       # 모두 끝났으면 x == 2 여야 한다
    x, *locals_ = s
    return not all(pc == "done" for pc, _ in locals_) or x == 2

def check():
    parent, frontier = {init: None}, deque([init])
    while frontier:
        s = frontier.popleft()
        if not invariant(s):
            trace = []
            while s is not None: trace.append(s); s = parent[s]
            return len(parent), trace[::-1]
        for t in next_states(s):
            if t not in parent:
                parent[t] = s; frontier.append(t)
    return len(parent), None

n, trace = check()
print(f"발견한 상태 수: {n}")
for step, st in enumerate(trace or []):
    print(step, st)
```

```
발견한 상태 수: 13
0 (0, ('read', 0), ('read', 0))
1 (0, ('write', 0), ('read', 0))
2 (0, ('write', 0), ('write', 0))
3 (1, ('done', 0), ('write', 0))
4 (1, ('done', 0), ('done', 0))
```

너비 우선이므로 찾은 반례가 **가장 짧은** 반례다. AWS 보고서에서 DynamoDB 복제 알고리즘의 데이터 손실 버그는 가장 짧은 반례조차 35단계였다. 사람이 리뷰로 따라가기 어려운 길이다.

### AWS 의 경험 (2014년 보고서 기준)

| 항목 | 보고 내용 |
|---|---|
| 시작 | 2011년부터 정형 명세와 모델 체킹 사용 |
| 적용 범위 | 대형 실제 시스템 10개, TLA+ 를 쓰는 팀 7개 |
| 학습 | 신입부터 수석 엔지니어까지 2~3주 만에 스스로 익혀 유용한 결과 |
| 예 | S3 하위 네트워크 알고리즘에서 버그 2건(최적화안에서 추가 버그), DynamoDB 복제·멤버십에서 버그 3건(일부는 35단계 반례), EBS 볼륨 관리에서 버그 3건 |
| 실패 사례 | 내부 잠금 관리자에서는 활성 성질을 검사하지 않아 활성 버그를 놓침 |

마지막 행이 중요하다. 모델 체커는 **물어본 것만** 확인한다.

## 실무 적용

- **대상 선택**: 코드 전체가 아니라 복제, 합의, 분산 잠금, 재시도·멱등성, 상태 기계처럼 "동시성 + 장애" 가 겹치는 핵심 프로토콜. 앞의 표처럼 수백 줄 규모의 명세가 보통이다.
- **작게 시작**: 프로세스 2~3개, 메시지 몇 개로 상수를 작게 잡는다. 대부분의 설계 버그는 작은 구성에서도 재현된다는 경험칙이 있고, 상태 폭발을 피하는 현실적 방법이기도 하다.
- **성질부터 적기**: 구현 상세보다 "절대 일어나면 안 되는 일" 목록(불변식)을 먼저 쓴다. 이 목록 자체가 설계 문서의 가장 정확한 부분이 된다.
- **장애를 액션으로**: 메시지 유실·중복·재정렬, 노드 크래시·재시작을 `Next` 의 액션으로 명시해야 모델 체커가 그 조합을 탐색한다.
- **설계 변경의 회귀 테스트**: 최적화를 제안할 때 명세를 먼저 바꾸고 TLC 를 돌린다. AWS 보고서도 공격적인 성능 최적화를 검증하는 데 썼다고 적는다.
- **참고 사례**: Azure Cosmos DB 는 다섯 가지 일관성 수준의 고수준 TLA+ 명세를 [공개 저장소](https://github.com/Azure/azure-cosmos-tla)에 두고 있다. [tlaplus/Examples](https://github.com/tlaplus/Examples) 에도 Paxos 등 다양한 명세가 있다.

## 흔한 오해와 함정

- **"정형 검증했으니 코드도 맞다"** — TLA+ 는 대개 **설계**를 검증한다. 구현이 명세와 다르면 보장은 없다. 명세와 코드의 대응을 리뷰하고, 가능하면 명세에서 나온 반례를 테스트로 옮긴다.
- **"모델 체킹 = 증명"** — TLC 는 주어진 유한 상수 범위 안에서 전수 검사한다. 노드 3개에서 통과했다고 노드 100개에서 성립한다는 증명은 아니다.
- **활성 성질 누락** — 안전성만 검사하면 "아무것도 안 하는 시스템" 도 통과한다. 공정성 조건과 함께 활성 성질을 확인한다.
- **너무 구체적인 모델** — 실제 바이트 형식, 타이머 값까지 넣으면 상태가 폭발한다. 추상화 수준을 올려 본질적인 상태만 남긴다.
- **명세를 한 번 쓰고 방치** — 설계가 바뀌었는데 명세가 그대로면 거짓 확신만 남는다. 설계 문서와 같은 저장소에서 함께 리뷰한다.

동시성의 기초는 CS300 [동시성과 병렬성]({% post_url 2026-10-10-cs300-124-concurrency-vs-parallelism %}), [Raft 합의]({% post_url 2026-10-10-cs300-134-raft-consensus %}) 에서 다뤘다.

## 확인 문제

1. TLA 에서 "시스템이 성질을 만족한다" 는 무엇으로 표현되는가?
2. 안전성과 활성의 차이를 예와 함께 설명하고, 각각의 반례는 어떤 모양인가?
3. 위 Counter 명세에서 `Finished` 액션이 없으면 TLC 는 무엇을 보고하는가?
4. 너비 우선 탐색으로 찾은 반례가 갖는 좋은 성질은?
5. AWS 내부 잠금 관리자 사례가 주는 교훈은?

### 풀이

1. 시스템 명세 식이 성질 식을 논리적으로 함의(implies)하는 것.
2. 안전성은 "나쁜 일이 절대 없다"(두 리더 동시 존재 금지)로, 반례는 위반 상태에 이르는 유한 경로다. 활성은 "좋은 일이 결국 일어난다"(요청은 결국 응답)로, 반례는 그 일이 영원히 일어나지 않는 무한(루프) 경로다.
3. 두 프로세스가 모두 `done` 이 되면 가능한 다음 단계가 없으므로 교착(deadlock)으로 보고한다. 종료를 정상으로 다루려면 정지 상태를 허용하는 액션을 넣거나 교착 검사를 끈다.
4. 가장 짧은 반례이므로 사람이 이해하고 디버깅하기 쉽다.
5. 모델 체커는 명세에 적은 성질만 검사한다. 활성 성질을 적지 않으면 활성 버그는 찾지 못한다.

## 더 읽을거리 (References)

- Leslie Lamport, [The Temporal Logic of Actions](https://lamport.azurewebsites.net/pubs/lamport-actions.pdf), ACM TOPLAS 16(3):872–923, 1994
- Leslie Lamport, [Specifying Systems](https://lamport.azurewebsites.net/tla/book.html), Addison-Wesley, 2002
- Leslie Lamport, [The TLA+ Home Page](https://lamport.azurewebsites.net/tla/tla.html), [TLA+ Tools](https://lamport.azurewebsites.net/tla/tools.html)
- C. Newcombe et al., [Use of Formal Methods at Amazon Web Services](https://lamport.azurewebsites.net/tla/formal-methods-amazon.pdf) (2014), 게재본 [How Amazon Web Services Uses Formal Methods](https://doi.org/10.1145/2699417), CACM 58(4):66–73, 2015
- [TLA+ Foundation](https://foundation.tlapl.us/), [tlaplus/tlaplus](https://github.com/tlaplus/tlaplus), [tlaplus/Examples](https://github.com/tlaplus/Examples)
- ACM, [A.M. Turing Award — Edmund M. Clarke](https://amturing.acm.org/award_winners/clarke_1167964.cfm)
- [Alloy](https://alloytools.org/)
