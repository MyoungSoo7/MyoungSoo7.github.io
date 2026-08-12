---
layout: post
title: "Self-Improving Loop에 대한 고찰 — 토비의 글을 1차 자료와 대조하며"
date: 2026-08-12 16:30:00 +0900
categories: [AI, 에이전트]
tags:
  [
    AI Agent,
    Agentic Coding,
    Self-Improving Loop,
    Harness Engineering,
    Claude Code,
    Codex,
    Evaluation,
    고찰,
  ]
---

토비(이일민)의 [AI Agentic Coding의 Self-Improving Loop란 무엇인가](https://codex.epril.com/what-is-self-improving-loop-in-ai-agentic-coding)(2026-08-08)를 읽었다. 최근 읽은 에이전트 관련 글 중 가장 정리가 잘 된 축에 든다. 그래서 요약만 하고 넘기는 대신, **그 글이 세운 주장을 논문과 벤더 1차 자료에 하나씩 대조**해봤다.

결론부터 적는다. 글의 주장은 1차 자료로 **대체로 뒷받침된다.** 다만 대조 과정에서 글에서 가장 약한 고리 하나가 드러났다. 그것은 Memory도 Harness도 아니고 **평가자(Evaluator)를 신뢰할 수 있다는 전제**다. 그리고 공교롭게도 그 전제를 가장 강하게 흔드는 자료가, 이 주제를 밀고 있는 Anthropic과 OpenAI 자신의 문서다.

---

## 1. 원문의 핵심 주장

먼저 논평 대상을 정확히 옮긴다. 아래는 [원문](https://codex.epril.com/what-is-self-improving-loop-in-ai-agentic-coding)의 논지다.

| 주장                       | 요지                                                                                                                       |
| -------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| Self-Improving Model 아님  | 실시간으로 좋아지는 건 모델 가중치가 아니라 **모델이 일하는 시스템**. 그래서 "Self-Improving Harness"가 더 정확한 말       |
| Agent Loop ≠ 개선          | Read→Test→Fix 는 루프지만 "어제의 시행착오가 오늘의 Claude에게 아무런 영향을 주지 못한다"                                  |
| Ralph Loop ≠ 개선          | "반복과 개선은 다른 개념이다." 101번째 실행이 1번째보다 나은 상태에서 시작하지 않는다                                      |
| Instruction → Verification | "자연어 지시보다 실행 가능한 제약이 강하다." 가능하면 지시를 검증으로 승격시킬 것                                          |
| Evaluation > Memory        | `Execution → Evaluation → Evidence → Diagnosis → Lesson → Memory`. 평가 없이 Memory부터 만들면 잘못된 판단까지 잘 기억한다 |
| Context Pollution          | 수백 줄 AGENTS.md는 "모든 규칙이 중요해진다. 결국 아무 규칙도 중요하지 않게 된다"                                          |
| Outer Loop가 핵심          | 현재 작업을 끝내는 Inner Loop가 아니라 Task→Failure→Retrospective→Harness 개선 의 Outer Loop                               |
| Self-Drift 경고            | harness 변경에 회귀 테스트가 없으면 개선이 아니라 표류                                                                     |

그리고 전체를 관통하는 한 문장 —

> Every expensive failure should leave the system better than it found it.

이 문장에는 동의한다. 아래는 그 다음 이야기다.

---

## 2. 1차 자료가 지지하는 부분

### 2-1. "Instruction보다 Verification" — 가장 강한 실증 근거가 있다

원문에서 가장 실무적으로 중요한 주장인데, 정작 원문은 이걸 논증이 아니라 경험칙으로 제시한다. 그런데 이 주장을 **정량적으로 뒷받침하는 논문**이 있다.

Fudan/Peking 연구진의 [Agentic Harness Engineering(AHE)](https://arxiv.org/abs/2604.25850)(arXiv:2604.25850, 2026-04-28, **preprint·동료심사 전**)은 harness 구성요소를 자동으로 진화시키는 폐루프를 만들고, 10회 반복으로 Terminal-Bench 2 pass@1을 **69.7% → 77.0%** 로 올렸다고 보고한다. 같은 표에서 사람이 설계한 Codex harness는 71.9%다.

여기까지는 "harness가 중요하다"는 이야기지만, 진짜 흥미로운 건 ablation이다. 논문 초록의 표현을 그대로 옮기면:

> Ablations further localize the gain to tools, middleware, and long-term memory rather than the system prompt.

**개선의 출처가 system prompt가 아니라 도구·미들웨어·장기기억이었다는 것.** 이건 "자연어 지시보다 실행 가능한 제약이 강하다"는 원문의 주장과 정확히 같은 방향이고, 원문이 제시하지 않은 실증을 제공한다. 프롬프트를 다듬는 데 쓰는 시간을 도구와 검증에 옮기라는 조언에 근거가 생긴 셈이다.

다만 라벨은 정확히 붙여야 한다. preprint이고, 벤치마크 2종이며, 저자 일부가 상업 조직 소속이다. 독립 재현은 아직 확인하지 못했다.

### 2-2. "AGENTS.md는 백과사전이 아니라 지도" — OpenAI가 독립적으로 같은 결론

원문의 Context Pollution 절은 OpenAI 팀의 실패 경험과 거의 문장 단위로 겹친다. [Harness engineering](https://openai.com/index/harness-engineering/)(2026-02-11)에서 Ryan Lopopolo는 "one big AGENTS.md" 시도가 실패했다며 네 가지 이유를 든다.

> Context is a scarce resource. … Too much guidance becomes non-guidance. When everything is "important," nothing is. … It rots instantly. … It's hard to verify.

그래서 그들은 AGENTS.md를 백과사전이 아니라 **목차(table of contents)** 로 취급하고 약 100줄로 유지하며, 실제 지식은 `docs/` 를 system of record로 두고 관리한다. 원문의 "지도" 비유와 같다. 서로 다른 두 출처가 독립적으로 같은 결론에 도달했다면, 이 조언은 신뢰해도 좋다고 본다.

한 가지 덧붙이면, OpenAI 쪽에는 원문에 없는 디테일이 하나 있다. **린트 에러 메시지 자체에 수정 지시를 넣는다**는 것.

> Because the lints are custom, we write the error messages to inject remediation instructions into agent context.

규칙을 문서에 적는 대신 **위반한 바로 그 순간에 컨텍스트로 배달**하는 방식이다. 원문의 "Instruction을 Verification으로 승격"을 한 단계 더 밀어붙인 형태이고, 개인적으로는 이 글에서 가장 바로 훔쳐 쓸 만한 아이디어였다.

### 2-3. Generator/Evaluator 분리 — Anthropic 실험과 일치

원문은 생성자와 평가자를 분리하라고 권한다. Anthropic Labs의 [Harness design for long-running application development](https://www.anthropic.com/engineering/harness-design-long-running-apps)(2026-03-24)는 GAN에서 착안해 planner·generator·evaluator 3-에이전트 구조를 만들었고, 분리의 이유를 이렇게 적는다.

> When asked to evaluate work they've produced, agents tend to respond by confidently praising the work—even when, to a human observer, the quality is obviously mediocre.

여기까지는 원문과 같다. 그런데 바로 다음 문장이 원문에는 없다. 그리고 그 문장이 이 고찰의 본론이다.

---

## 3. 원문에서 가장 약한 고리 — 평가자는 누가 평가하는가

### 3-1. 분리해도 평가자는 여전히 관대하다

Anthropic 글의 같은 문단을 이어서 인용한다.

> The separation doesn't immediately eliminate that leniency on its own; the evaluator is still an LLM that is inclined to be generous towards LLM-generated outputs. But tuning a standalone evaluator to be skeptical turns out to be far more tractable than making a generator critical of its own work.

즉 **분리는 문제를 해결하는 게 아니라 다루기 쉬운 형태로 바꿀 뿐**이다. 분리된 평가자도 여전히 후하고, 회의적으로 만드는 별도의 튜닝이 필요하다. 원문은 `Execution → Evaluation → Evidence → Diagnosis → Lesson → Memory` 파이프라인에서 Evaluation을 신뢰 가능한 기준점으로 두는데, 1차 자료는 그 기준점 자체가 보정 대상이라고 말한다.

여기서 무한후퇴가 시작된다. 평가자도 harness의 일부다. 그렇다면 평가자를 개선하는 루프의 평가는 누가 하는가? 원문은 "결정론적 평가를 선호하라"는 좋은 답을 갖고 있다. 문제는 그 답을 끝까지 적용할 수 없다는 데 있다.

### 3-2. 도구들 자체가 비결정론적 평가로 기울어 있다

가장 좋은 예가 Claude Code의 `/goal` 이다. 원문도 Inner Loop 사례로 언급하는 기능인데, [공식 문서](https://code.claude.com/docs/en/goal)의 설명은 이렇다.

> After each turn, a small fast model checks whether the condition holds.

그리고 결정적으로:

> The evaluator judges your condition against what Claude has surfaced in the conversation. **It doesn't run commands or read files independently**, so write the condition as something Claude's own output can demonstrate.

평가자는 명령을 실행하지 않는다. **transcript를 읽을 뿐이다.** 그러니까 작업하는 에이전트가 "테스트가 통과했습니다"라고 써두면, 평가자가 검증할 수 있는 것은 그 문장이 대화에 등장했다는 사실까지다. 원문이 "LLM에게 '테스트가 통과했는지 판단해줘'라고 할 이유는 없다"고 했던 바로 그 구조가, 표준 도구의 기본 동작으로 들어와 있다.

이건 `/goal` 을 쓰지 말라는 뜻이 아니다(문서가 스스로 한계를 밝히고 있고, 조건을 "Claude의 출력으로 증명 가능하게" 쓰라는 안내도 명확하다). 요점은 **"결정론적으로 평가하라"는 원칙이 도구 기본값과 충돌하며, 그 충돌을 메우는 건 각자의 몫**이라는 것이다. 원문의 통합 `verify.sh` 제안이 좋은 이유가 여기 있다. 종료 코드는 거짓말을 하지 않는다. 다만 그 종료 코드를 **루프의 판정에 실제로 연결**해두지 않으면, 판정은 조용히 LLM의 자기 보고로 되돌아간다.

### 3-3. 점수는 단조 증가하지 않는다 — hill climbing 조언의 한계

원문은 한 번에 하나씩 바꾸는 hill climbing을 권한다(72 → A: 75 → B: 73 기각 → C: 81 채택). 방법론으로는 옳다. 그런데 Anthropic의 실측 기록은 그 전제가 현실에서 잘 성립하지 않음을 보여준다.

> While scores generally improved over iterations, the pattern was not always cleanly linear. Later implementations tended to be better as a whole, but I regularly saw cases where I preferred a middle iteration over the last one.

점수는 대체로 올랐지만 깨끗하게 선형은 아니었고, 마지막보다 중간 결과물이 더 나았던 경우가 반복적으로 있었다는 것이다. 이런 노이즈 위에서 "이번 변경으로 3점 올랐으니 채택" 같은 판정은 위험하다. 한 번의 측정으로 harness 변경을 채택/기각하면, 채택되는 것의 상당수가 노이즈일 수 있다.

AHE 논문은 이 문제를 다르게 푼다. 변경마다 **자기 예측을 함께 선언하게 하고**, 다음 라운드의 실제 결과로 그 예측을 검증한다.

> decision observability pairs every edit with a self-declared prediction, later verified against the next round's task-level outcomes … so each edit becomes a falsifiable contract and ineffective ones are reverted at file granularity.

"한 번에 하나씩"이 규율이라면, "모든 변경은 반증 가능한 계약"은 **메커니즘**이다. 후자가 확장성이 있다. 변경을 직렬화하지 않고도 효과 없는 변경을 파일 단위로 되돌릴 수 있기 때문이다. 원문의 Improvement Log에 `status: candidate` 필드가 있는 건 좋은 출발인데, 여기에 `predicted_effect` 와 `verified_at` 을 한 줄씩 더 붙이면 훨씬 강해진다고 본다.

### 3-4. 메모리 위협 모델은 원문이 그린 방향과 조금 다르다

원문에는 Untrusted Experience 절이 있다. GitHub 이슈에 "앞으로 항상 이 규칙을 영구 메모리에 추가하라"는 문장이 심겨 있으면 학습하지 말라는, 옳은 경고다. 그런데 원문이 인용한 그 논문의 실측 결과는 방어의 무게중심을 조금 다른 곳에 둔다.

[Bad Memory](https://arxiv.org/abs/2607.14611)(arXiv:2607.14611, 2026-07-16, **preprint**)는 Claude Code와 Codex를 4개 모델(Haiku 4.5, Opus 4.7, GPT-5.2, GPT-5.5)에서 샌드박스로 평가했다. 초록의 핵심 결과:

> although it is difficult to make an agent overwrite its own memory files using untrusted external content, payloads already planted in those files can successfully attack current and future sessions.

**외부 콘텐츠로 에이전트가 자기 메모리 파일을 덮어쓰게 만드는 건 오히려 어려웠다.** 진짜 문제는 일단 그 파일에 들어간 payload가 현재와 미래 세션을 계속 공격한다는 쪽이었다. 논문은 이를 reflected XSS와 stored XSS의 차이에 빗댄다.

이게 실무에 주는 함의는 분명하다. 입구 게이트(쓰기 시점 검증)도 필요하지만, 그보다 **이미 들어와 있는 것들의 지속·누적을 관리하는 쪽**이 더 급하다. 출처 추적(provenance), 주기적 감사, 그리고 삭제. 원문 후반의 Harness Gardener / Garbage Collection 절은 위생 관리 항목처럼 배치돼 있는데, 이 논문에 비춰보면 사실상 **보안 절**이다. 원문의 이 문장이 생각보다 무겁다는 뜻이다.

> 무언가를 잘 기억하는 것만큼 잘 잊는 능력도 중요하다.

참고로 OWASP는 2025년 12월 Agentic Applications Top 10에서 persistent memory poisoning을 ASI06으로 별도 분류했다(위 논문에서 재인용).

---

## 4. 한 가지 더 — harness 부채

원문은 L5부터 시작하지 말라고 조언한다. 동의하는데, 여기서 한 걸음 더 나가고 싶다. **harness는 공짜가 아니고, 그 자체가 유지보수 대상이 된다.**

OpenAI 사례의 비용 구조를 보면 분명하다. 5개월, 엔지니어 3명에서 7명으로, 사람이 코드를 한 줄도 쓰지 않는 대신 **환경·규칙·검증을 만드는 데 전담**했다. 그들이 만든 것 중에는 지식베이스가 최신인지 검사하는 전용 린터와 CI 잡, 그리고 낡은 문서를 찾아 수정 PR을 여는 doc-gardening 에이전트까지 있다. **harness를 관리하는 harness가 필요해졌다는 뜻이다.**

원문은 AGENTS.md가 "쓰레기장"이 되는 걸 경고하는데, 같은 일이 스킬·훅·린트 규칙·평가 스위트 전체에서 일어난다. 규칙 40개짜리 린트 설정과 아무도 실패 원인을 모르는 평가 스위트는 200줄짜리 CLAUDE.md와 같은 종류의 부채다. 오히려 더 나쁘다. 문서는 무시되지만 **깨진 검증은 능동적으로 방해**하고, 결국 누군가 규칙을 끄는 것으로 끝난다. 원문이 인용한 Goodhart 사례(`Lint Errors = 0` → 린트 규칙을 꺼버림)가 정확히 그 경로다.

그래서 우선순위가 필요한데, 앞의 AHE ablation이 마침 힌트를 준다. **도구·미들웨어·장기기억에 먼저 투자하고 system prompt 손질은 나중.** 그리고 harness 항목마다 "이게 없으면 무엇이 깨지는가"를 답할 수 없다면, 그건 추가할 때가 아니라 지울 때다.

---

## 5. 내 경험에 대입하면

측정 데이터가 아니라 일화라는 점을 먼저 밝힌다. 아래는 개인 프로젝트에서 관찰한 것이고, 정량화하지 않았다.

**자연어 규칙과 실행 가능한 제약의 차이는 실제로 크다.** 헥사고날 구조를 쓰는 정산 프로젝트에서 "도메인 레이어는 Spring에 의존하지 않는다", "application에서 JPA를 직접 쓰지 않는다" 같은 경계 규칙을 한동안 문서로만 갖고 있었다. 문서에 적혀 있고, 에이전트도 그 문서를 읽었다. 그럼에도 위반은 반복됐다. 같은 규칙을 ArchUnit 테스트로 옮기고 CI에 물린 뒤에야 멈췄다. 규칙이 명확해져서가 아니라, **위반이 실패로 관측되기 시작해서**다. 원문의 "Instruction을 Verification으로 승격"은 수사가 아니라 실제로 작동하는 조작이다.

**반대로, 통합 verify 명령은 만드는 것보다 유지하는 게 어렵다.** 하나로 묶은 검증이 느려지면 우회 압력이 생긴다. 사람도 우회하고 에이전트도 우회한다. 원문의 조언은 옳지만, `verify.sh` 를 만드는 순간 그 실행 시간이 새로운 관리 지표가 된다는 점은 같이 적혀야 공정하다고 본다.

**가장 실행 비용이 낮은 조언은 Improvement Log였다.** 실패를 기록하되 `status: candidate` 로 두고, 재현 테스트가 생겼을 때만 규칙으로 승격시키는 것. 도구도 인프라도 필요 없고 파일 하나면 된다. 그런데 이게 원문이 말한 "비싼 실패를 그냥 버리지 말자"를 실제로 구현하는 최소 단위다.

---

## 6. 그래서 내가 바꾸기로 한 세 가지

1. **규칙 하나를 승격시킨다.** 자연어로만 적혀 있는 규칙 중 최근 반복 위반된 것 하나를 골라 테스트나 린트로 옮긴다. 하나씩. 전부 옮기려다 아무것도 안 옮기는 걸 피하려고.
2. **Improvement Log를 시작하되 예측 필드를 넣는다.** 원문의 스키마에 `predicted_effect` 와 `verified_at` 을 추가한다. AHE의 "반증 가능한 계약"을 가난한 버전으로 흉내내는 것. 예측이 빗나간 변경은 되돌린다.
3. **평가자를 먼저 감사한다.** 에이전트가 "통과했다"고 보고한 건과 실제 종료 코드를 표본으로 대조한다. 평가를 신뢰하기 전에 평가를 평가한다. 3-2에서 본 이유 때문에, 이게 세 가지 중 가장 중요하다고 생각한다.

---

## 7. 원문에 대한 최종 평가

**추천한다.** 특히 "반복과 개선은 다른 개념이다"라는 구분과, Inner Loop/Outer Loop의 분리는 이 주제를 다룬 글 중에서 가장 명료하다. 성숙도 모델(L0~L5)도 자기 위치를 가늠하는 도구로 유용하다.

내가 덧붙이고 싶은 건 하나다. 원문의 파이프라인은 Evaluation을 든든한 바닥으로 놓고 그 위에 Memory와 Harness를 쌓는다. 그런데 1차 자료들을 읽어보면 **그 바닥이 생각보다 무르다.** 평가자는 관대하고, 점수는 단조롭게 오르지 않으며, 표준 도구의 완료 판정조차 transcript 읽기에 기대고 있다.

그러니 원문의 마지막 문장을 이렇게 이어 적고 싶다. 모든 비싼 실패가 시스템을 더 낫게 만들어야 한다면, **먼저 "더 낫다"를 측정하는 물건이 거짓말하지 않는지 확인해야 한다.**

---

## 이 글의 한계

- 논평 대상은 토비의 글 1편이고, 대조한 1차 자료는 5건이다. 이 주제 전반의 문헌 조사가 아니다.
- 인용한 논문 2건(AHE, Bad Memory)은 모두 **arXiv preprint로 동료심사를 거치지 않았다.** AHE는 벤치마크 2종에 한정된 결과이고, 독립 재현 보고는 확인하지 못했다.
- OpenAI·Anthropic 글의 수치와 성과 서술은 **자사 자체 보고**다(예: OpenAI의 "약 1/10 시간", 엔지니어당 하루 3.5 PR, 약 100만 줄). 외부에서 재현하거나 검증할 수 있는 형태로 공개되어 있지 않으므로 사실이 아니라 벤더 주장으로 읽어야 한다. 이 글은 그 수치들을 논증의 근거로 쓰지 않았고, 비용 구조와 방법론 서술만 인용했다.
- harness 설계를 놓고 **중립 제3자가 수행한 head-to-head 비교는 찾지 못했다.** 이 영역의 공개 자료는 현재 대부분 벤더 또는 당사자 자기 보고다.
- 5절의 개인 경험은 정량화하지 않은 일화다. 위반 건수도 소요 시간도 측정하지 않았다.
- L4/L5 수준의 harness를 장기간 운영한 경험은 없다. 4절의 harness 부채 논의는 소규모 운영 관찰과 인용 자료에 기반한 추론이다.

---

## References

**논평 대상**

- 토비(이일민), [AI Agentic Coding의 Self-Improving Loop란 무엇인가](https://codex.epril.com/what-is-self-improving-loop-in-ai-agentic-coding), Toby's Codex, 2026-08-08

**1차 자료 — 공식 문서**

- Anthropic, [Keep Claude working toward a goal (`/goal`)](https://code.claude.com/docs/en/goal), Claude Code Docs

**1차 자료 — 논문 (preprint, 동료심사 전)**

- Jiahang Lin et al., [Agentic Harness Engineering: Observability-Driven Automatic Evolution of Coding-Agent Harnesses](https://arxiv.org/abs/2604.25850), arXiv:2604.25850, 2026-04-28
- Soham Gadgil, David Alexander, Sai Sunku, Franziska Roesner, [Bad Memory: Evaluating Prompt Injection Risks from Memory in Agentic Systems](https://arxiv.org/abs/2607.14611), arXiv:2607.14611, 2026-07-16

**벤더 1차 자료 (자체 보고 — 수치는 벤더 주장으로 읽을 것)**

- Prithvi Rajasekaran (Anthropic Labs), [Harness design for long-running application development](https://www.anthropic.com/engineering/harness-design-long-running-apps), 2026-03-24
- Ryan Lopopolo (OpenAI), [Harness engineering: leveraging Codex in an agent-first world](https://openai.com/index/harness-engineering/), 2026-02-11

**독자가 직접 확인할 것**

- AHE의 Terminal-Bench 2 결과는 preprint 단계이며 독립 재현 보고를 확인하지 못했다. 수치를 인용할 계획이라면 논문 본문의 실험 설정과 이후 개정판을 직접 확인하기 바란다.
- 메모리 기반 프롬프트 인젝션의 공격 성공률은 논문에 따르면 시스템·모델·공격 목표·세션 시퀀스에 따라 크게 달랐다. 단일 수치로 요약하지 않은 이유다.
