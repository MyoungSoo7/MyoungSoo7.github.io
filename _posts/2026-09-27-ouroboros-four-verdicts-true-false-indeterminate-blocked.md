---
layout: post
title: "우로보로스 잘 쓰는 법 — 검증 결과는 왜 참/거짓 둘이 아니라 넷이어야 하는가?"
date: 2026-09-27 01:57:19 +0900
categories: [AI, Agent]
tags: [Ouroboros, Agent Harness, Evaluation, Verification, Evolve, LLM Agent]
---

[우로보로스(Ouroboros)](https://github.com/Q00/ouroboros)로 에이전트 하네스를 실험하면서 가장 크게 바뀐 생각은 이것이다. **에이전트의 성패는 실행이 아니라 검증 단계에서 결정되고, 검증 결과를 몇 갈래로 나누느냐가 다음 세대(evolve)의 품질을 결정한다.**

결론부터 적으면, 검증 결과는 **참/거짓 둘이 아니라 넷**으로 나눠야 한다.

| 판정 | 의미 | 다음 행동 | 에이전트 호출 |
|---|---|---|---|
| **True** | 합격 | 끝. 재시도 없음 | ✕ |
| **False** | 불합격, 이유가 확인됨 | **반례를 들고** 재시도 / evolve | ○ |
| **Indeterminate** | 판정 불가 (시간 초과, 검사 실행 실패) | **검사만** 다시 돌린다 | ✕ |
| **Blocked** | 실행 환경 문제 (도구 없음, 권한, 네트워크) | 환경을 고친다. 사람에게 알린다 | ✕ (소용없음) |

에이전트를 다시 부르는 건 **False 하나뿐**이다. 나머지 셋에서 에이전트를 부르면 돈과 시간만 쓰고, 더 나쁘게는 **틀린 신호로 다음 세대를 진화시킨다.**

## 1. 우로보로스의 흐름과 검증의 위치

우로보로스의 흐름을 사용자 관점에서 다섯 단계로 적으면 이렇다.

```
① 인터뷰 (ooo interview)   모호한 점을 사용자에게 묻는다
      ↓
② Seed (요구사항 계약)       Seed 를 실행 가능한 check 로 바꿔 미리 동결
      ↓
③ 실행 (ooo run)           worker 가 코드를 수정
      ↓
④ 검증                      합격인지 판정
      ↓
⑤ 실패하면 복구              재시도, evolve
```

README 도 같은 구조를 *Interview → Seed → Execute → Evaluate* 와 그 뒤의 진화 루프로 설명하며, 핵심을 이렇게 요약한다.[^readme]

> *"This is where the Ouroboros eats its tail: the output of evaluation becomes the input for the next generation's seed specification."*

**검증의 출력이 다음 세대의 입력이 된다.** 그러니 검증이 "왜 실패했는지" 를 잘못 말하면, 다음 세대는 잘못된 방향으로 정확하게 진화한다.

## 2. 참/거짓 두 갈래로 나누면 생기는 세 가지 사고

### 2.1 Blocked 를 False 로 칠 때 — 코드로 환경을 고치려는 에이전트

테스트 러너가 설치돼 있지 않아서 검사가 실패했다고 하자. 이걸 "불합격" 으로 에이전트에게 돌려주면, 에이전트는 **코드가 틀렸다고 믿고** 코드를 고친다. 코드를 아무리 고쳐도 환경은 그대로이니 세대만 소모된다. 더 나쁘면 에이전트가 검사를 우회하는 코드를 만든다.

Blocked 는 에이전트의 문제가 아니다. **에이전트를 부르지 말고 환경을 고쳐야** 한다.

### 2.2 Indeterminate 를 False 로 칠 때 — 노이즈로 진화하기

시간 초과나 간헐적 실패는 코드의 결함이 아니라 **측정의 결함**일 수 있다. 같은 코드에서 결과가 바뀌는 테스트는 오래전부터 알려진 문제다. Luo 등은 FSE 2014 에서 이런 "flaky test" 가 회귀 테스트의 전제를 무너뜨린다고 정리했다.[^flaky]

> *"An important assumption of regression testing is that test outcomes are deterministic ... Unfortunately, in practice, some tests often called flaky tests—have non-deterministic outcomes."*

판정 불가를 불합격으로 에이전트에게 넘기면, 에이전트는 **존재하지 않는 결함**을 고치느라 코드를 흔든다. Indeterminate 는 **검사만 다시 돌려서** 판정을 확정하는 게 먼저다.

### 2.3 "건너뜀" 을 True 로 칠 때 — 조용히 열리는 게이트

세 번째가 가장 위험하다. **아무것도 검사하지 않았는데 합격**으로 처리되는 경우다.

우로보로스 평가 가이드는 이 함정을 직접 적어 두었다.[^eval] Stage 1(기계 검사: lint·build·test·static·coverage)에서 명령이 설정되지 않은 검사는 이렇게 처리된다.

> *"If a check has no command configured (`None`), it is silently skipped and treated as **passed**."*

그리고 곧바로 경고한다.

> *"If Stage 1 always passes, this is usually why."*

즉 `.ouroboros/mechanical.toml` 이 없거나 자동 탐지가 실패하면, Stage 1 은 **아무것도 막지 않는 게이트**가 된다. "증거 없음" 을 True 로 접는 순간 생기는 일이다. 4분기로 보면 이건 True 가 아니라 **Blocked**(검사할 수단이 없음)다.

## 3. 우로보로스는 이미 어디까지 와 있나

반가운 점은, 우로보로스 본가도 같은 방향으로 가고 있다는 것이다.

### Verdict Envelope v1

설계 문서(RFC) *Verdict Envelope v1* 은 흩어진 판정 결과를 하나의 타입으로 묶으면서 상태를 넷으로 정의한다.[^rfc]

```json
"status": "PASS | FAIL | BLOCKED | DEFERRED"
```

문서가 밝힌 문제의식도 같다. 호출자가 판정의 의미를 *"prose or subsystem-specific fields"* 에서 추론해야 하는 상황을 없애고, 하나의 타입이 있는 봉투로 노출하자는 것이다.

### Failure 와 Error 의 구분

평가 가이드는 이미 **failure**(산출물이 기준을 못 맞춤)와 **error**(파이프라인 자체가 끝나지 못함)를 구분한다.[^eval]

> *"**Errors** leave the AC in an indeterminate state. The orchestrator runner handles them via tier escalation (retry with a stronger model) or stagnation detection if retries are exhausted."*

### 4분기와 비교했을 때 남는 틈

| 상황 | 현재 문서상 처리 | 4분기 관점 |
|---|---|---|
| 검사 명령 미설정 | 건너뛰고 **통과** | Blocked (증거 없음) |
| Stage 1 명령을 찾을 수 없음 (*"Command not found"*) | 검사 **실패** → 거부 | Blocked |
| Stage 1 명령 시간 초과 | 검사 **실패** → 거부 | Indeterminate |
| LLM API 오류, 투표 부족 등 error | indeterminate → **더 강한 모델로 재시도** | 원인이 환경이면 Blocked. 모델을 바꿔도 소용없음 |
| RFC 의 상태 집합 | PASS / FAIL / BLOCKED / DEFERRED | **Indeterminate 가 따로 없음** |

(위 표의 "현재 처리" 는 모두 인용한 두 문서 기준이다. 코드의 최신 동작은 버전에 따라 다를 수 있다.)

RFC 의 DEFERRED 는 *"user-owned decisions"* 를 위한 상태로, 판정불가(Indeterminate)와는 다른 개념이다. 시간 초과처럼 **"다시 재면 답이 나올 수도 있는" 상태**를 담을 자리가 하나 더 있으면, evolve 루프가 노이즈에 반응하는 일을 구조적으로 줄일 수 있다.

## 4. 성숙한 검증 도구는 이미 "모름" 을 말한다

이 분류가 새로운 발상은 아니다. SMT 솔버의 표준 인터페이스인 SMT-LIB 는 `check-sat` 의 응답을 셋으로 정의한다.[^smt]

```
check_sat_response ::= sat | unsat | unknown
reason-unknown     ::= memout | incomplete | ...
```

"모른다" 를 정식 답으로 두고, **왜 모르는지**(메모리 초과인지, 방법이 불완전한지)까지 말하게 한다. 에이전트 검증도 같아야 한다. 판정기가 "모름" 을 말할 수 없으면, 그 "모름" 은 참이나 거짓 어딘가에 **조용히 섞여 들어간다.**

## 5. 실전 — 우로보로스를 쓸 때 이렇게 한다

### 5.1 Stage 1 을 반드시 내 손으로 확인한다

- 프로젝트 루트의 `.ouroboros/mechanical.toml` 이 **실제로 존재하고**, 명령이 비어 있지 않은지 본다. 없으면 `ouroboros detect` 로 만들고 내용을 검토한다.[^eval]
- 명령이 허용 목록 밖이면 조용히 건너뛴다는 점도 기억한다(같은 문서의 *"Blocked executable"* 항목).
- "Stage 1 이 한 번도 실패한 적이 없다" 는 좋은 신호가 아니라 **점검 신호**다.

### 5.2 판정 분류 규칙을 명시한다

검사 결과를 넷으로 나누는 규칙을 하네스에 명시적으로 둔다. 예를 들면 다음과 같다.

```python
def classify(exit_code, timed_out, stderr, ran_any_check):
    if not ran_any_check:
        return "BLOCKED"            # 검사할 수단이 없음 — 합격 아님
    if exit_code == 127 or "Command not found" in stderr:
        return "BLOCKED"            # 도구 없음 — 에이전트 호출 금지
    if timed_out:
        return "INDETERMINATE"      # 검사만 재실행
    if exit_code == 0:
        return "TRUE"
    return "FALSE"                  # 반례를 붙여 에이전트에게
```

(POSIX 셸 명세는 *"If the command is not found, the exit status shall be 127"* 이라고 정한다.[^posix] 실제 규칙은 환경에 맞게 정한다.)

### 5.3 False 에는 반드시 반례를 붙인다

"테스트 실패" 한 줄로는 다음 세대가 배울 게 없다. **어떤 입력에서, 무엇을 기대했고, 무엇이 나왔는지**를 붙인다. 실패한 테스트 이름, 입력, 기대값과 실제값, 관련 로그 일부가 반례다. 우로보로스가 인터뷰에서 모호함을 걷어냈듯, 재시도 단계에서는 **반례가 모호함을 걷어낸다.**

### 5.4 Indeterminate 는 검사만 N 번

에이전트를 부르지 않고 검사만 2~3 회 다시 돌린다. 결과가 갈리면 **flaky** 로 기록하고 그 검사를 고친다. 계속 시간 초과면 Blocked 로 올린다(자원 부족일 가능성).

### 5.5 Blocked 는 에이전트가 아니라 사람에게

Blocked 에서 에이전트를 부르는 건 소용이 없다. 알림을 보내고 루프를 멈춘다. **evolve 예산은 False 에만 쓴다.**

## 맺으며 — "모름" 을 말할 수 있는 하네스

에이전트 하네스를 만들다 보면 에이전트를 더 똑똑하게 만드는 데 관심이 쏠린다. 그런데 실험해 보면 더 큰 차이는 **판정기가 얼마나 정직한가**에서 나온다. 모르는 걸 모른다고, 막힌 걸 막혔다고 말하는 판정기 위에서만 evolve 가 진짜 학습이 된다.

우로보로스는 인터뷰로 **입력의 모호함**을 걷어내는 도구다. 같은 태도를 **출력의 판정**에도 적용하는 것. 그게 우로보로스를 잘 쓰는 가장 확실한 방법이라고 생각한다. 비용도 있다. 분기가 늘면 하네스 코드가 늘고, 분류 규칙이 틀리면 True 가 Blocked 로 새는 반대 방향의 사고도 생긴다. 그래서 분류 규칙 자체도 테스트 대상이다.

---

## References

[^readme]: Q00/ouroboros, *README*. <https://github.com/Q00/ouroboros>
[^eval]: Q00/ouroboros, *docs/guides/evaluation-pipeline.md* (commit bd89995). <https://github.com/Q00/ouroboros/blob/bd89995/docs/guides/evaluation-pipeline.md>
[^rfc]: Q00/ouroboros, *docs/rfc/verdict-envelope-v1.md* (commit 3dd8917). <https://github.com/Q00/ouroboros/blob/3dd8917/docs/rfc/verdict-envelope-v1.md>
[^flaky]: Qingzhou Luo, Farah Hariri, Lamyaa Eloussi, Darko Marinov, *An empirical analysis of flaky tests*, FSE 2014. <https://doi.org/10.1145/2635868.2635920>
[^smt]: Clark Barrett, Pascal Fontaine, Cesare Tinelli, *The SMT-LIB Standard: Version 2.6*. <https://smt-lib.org/papers/smt-lib-reference-v2.6-r2021-05-12.pdf>
[^posix]: The Open Group, *POSIX.1-2024, Shell Command Language — 2.8.2 Exit Status for Commands*. <https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html>
