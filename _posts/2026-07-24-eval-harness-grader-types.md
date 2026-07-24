---
layout: post
title: "Eval Harness와 Grader 6종 — 무엇으로 채점할 것인가"
date: 2026-07-24 09:58:00 +0900
categories: [AI, Architecture]
tags: [EvalHarness, Grader, LLMasJudge, Evaluation, CostLadder, Ouroboros, AgenticCoding]
---

# 하네스의 심장은 '채점기(grader)'다

Eval harness는 단순하다 — *에이전트를 태스크에 돌리고, 출력을 채점한다.* 그런데 이 "채점"을 무엇으로 하느냐가 하네스의 신뢰도를 통째로 결정한다. 정규식으로 될 걸 LLM에게 묻거나, 테스트로 될 걸 사람에게 맡기면 — 비용은 폭증하고 일관성은 무너진다. **태스크마다 맞는 채점기를 고르는 것**, 그게 핵심 기술이다.

아래 표가 Grader 6종과 각각의 용도다.

![Grader type 6종과 용도 — Exact/regex/JSON schema, Unit/integration test, Static analysis, Reference comparison, LLM-as-judge, Human grader](/assets/images/eval-harness-grader-types.jpg)

| Grader type | 언제 쓰나 |
|---|---|
| **Exact / regex / JSON schema** | 구조화 출력, 금지어, citation, tool args |
| **Unit test / integration test** | coding agent, data transform, API workflow |
| **Static analysis** | code quality, security rule |
| **Reference comparison** | 요약, 분류, 추출 |
| **LLM-as-judge** | subjective quality, instruction following, reasoning quality |
| **Human grader** | 고위험, 애매한 품질, judge calibration |

---

## 채점기는 하나의 스펙트럼이다 — 싸고 결정론적 → 비싸고 주관적

6종은 무작위가 아니라 **비용·결정성·주관성의 축** 위에 정렬된다:

```
결정론적·저비용 ───────────────────────────▶ 주관적·고비용
Exact/regex → Test → Static → Reference → LLM-judge → Human
   $0          $0      $       $ ~ $$        $$         $$$
```

### 1. Exact / regex / JSON schema — 가장 싸고 확실
- **강점**: $0, 완전 결정론적, 재현 100%
- **쓸 곳**: 구조화 출력(JSON 스키마 준수), 금지어 검출, citation 형식, tool args 유효성
- 정답이 *정확히 정의되는* 것엔 이걸 써라. LLM에게 "JSON 맞아?"를 묻는 건 낭비다.

### 2. Unit / integration test — 동작을 채점
- **강점**: 결정론적, *행동*을 검증(존재가 아니라 동작)
- **쓸 곳**: coding agent, 데이터 변환, API 워크플로
- "빌드 성공"과 "요청한 기능이 동작"은 다른 명제다. 테스트는 후자를 잡는다.

### 3. Static analysis — 규칙 기반 품질
- **강점**: 싸고 결정론적, 코드를 실행 안 하고 검사
- **쓸 곳**: code quality, security rule (린트·SAST)

### 4. Reference comparison — 정답과 대조
- **강점**: 골든 레퍼런스와 비교(정확도·recall 등 지표화)
- **쓸 곳**: 요약, 분류, 추출 — 기대 출력이 있는 작업
- 정답 집합이 있으면 지표로 잴 수 있다. 다만 "정답이 여럿"인 생성 작업엔 한계.

### 5. LLM-as-judge — 주관을 채점
- **강점**: 규칙으로 못 잡는 *주관적 품질*을 평가
- **쓸 곳**: subjective quality, instruction following, reasoning quality
- **함정**: [rubric 없이 돌리면 고무도장(rubber-stamp)](/2026/07/23/multi-agent-coordination-patterns/) — 실체 없이 통과시킨다. 반드시 rubric·source of truth·최대 반복 수를 줘야 한다. ([Ouroboros가 평가자에게 "근거(evidence) 없으면 검증 실패"로 강제하는 이유](/2026/07/23/ouroboros-manual-agentic-coding-code-analysis/).)

### 6. Human grader — 최후이자 기준점
- **강점**: 골드 스탠다드
- **쓸 곳**: 고위험, 애매한 품질, 그리고 **judge calibration**
- Anthropic도 못 박는다 — *"사람이 에이전트를 테스트하면 eval이 놓친 엣지 케이스를 찾는다."* 특히 마지막 용도가 중요: 사람 라벨로 **LLM-judge를 보정(calibration)** 한다. 사람은 모든 걸 채점할 순 없지만, *채점기를 채점*할 수 있다.

---

## 메타 원칙 — 채점기 고르는 법

### 원칙 1. 태스크 유형에 맞춰라
정답이 정확 → Exact/schema. 동작 → Test. 코드 규칙 → Static. 기대 출력 존재 → Reference. 주관 품질 → LLM-judge. 고위험/보정 → Human. **표의 오른쪽 열이 곧 선택 기준이다.**

### 원칙 2. 비용 사다리 — 싼 게 비싼 걸 게이팅
이건 [Ouroboros의 3단계 평가](/2026/07/23/ouroboros-manual-agentic-coding-code-analysis/)($0 Mechanical → $$ Semantic → $$$ Consensus)와 같은 구조다. **컴파일도 안 되는 코드의 의미론을 LLM-judge에게 묻지 마라.** exact/test/static이 먼저 걸러야, 비싼 LLM-judge·human을 *걸러진 것에만* 쓴다. 싼 검사가 실패하면 비싼 검사는 아예 건너뛴다.

### 원칙 3. 채점기도 게이밍당한다
[하드코딩·테스트 전용 분기](/2026/07/23/agent-roles-explorer-implementer-verifier/)로 테스트를 통과시키거나, LLM-judge가 근거 없이 점수만 내는 것 — 채점기 자체를 속이는 것도 막아야 한다. 그래서 test는 negative test를 포함하고, LLM-judge는 evidence를 요구하고, 최종엔 human calibration으로 검증한다.

### 원칙 4. 한 태스크에 여러 채점기
현실은 조합이다. coding agent 하나를 채점해도: schema(출력 형식) + test(동작) + static(보안) + LLM-judge(코드 가독성) + 가끔 human(고위험 변경). [어제 본 Eval Harness의 4게이트](/2026/07/24/agentic-feedback-eval-pipeline/)가 바로 이 조합을 층으로 쌓은 것이다.

---

## 한 줄 결론

Eval harness의 품질은 채점기 선택에서 갈린다. **정답이 정의되면 결정론적으로(exact/test/static), 주관적이면 LLM-judge로, 고위험이면 human으로** — 그리고 항상 *싼 채점기가 비싼 채점기를 게이팅*하게 하라. 사람의 자리는 "모든 걸 채점"이 아니라 "채점기를 보정하고, 정말 위험한 것만 본다"이다.

---

## 출처 · 관련 글

- 첨부 이미지: 사용자 제공(Grader type 6종과 용도).
- 비용 사다리·평가자 evidence 강제·리워드 해킹 방어: [Ouroboros 3부작 정리](/2026/07/23/ouroboros-manual-agentic-coding-code-analysis/) (원 저장소 Q00/ouroboros 실측 분석).
- LLM-judge 고무도장 경고(공식): Anthropic, [Multi-Agent Coordination Patterns](https://claude.com/blog/multi-agent-coordination-patterns).
- human eval의 가치(공식): Anthropic, [Multi-Agent Research System](https://www.anthropic.com/engineering/multi-agent-research-system) — "사람이 eval이 놓친 엣지 케이스를 찾는다".
- 관련 본인 정리글: [평가-피드백 파이프라인](/2026/07/24/agentic-feedback-eval-pipeline/) · [Explorer/Implementer/Verifier](/2026/07/23/agent-roles-explorer-implementer-verifier/) · [하네스의 세 문서](/2026/07/24/harness-spec-plan-done-criteria/)

> 참고: 6종 분류·용도는 이미지 기준이며, 본문의 비용 사다리·게이밍 방어·calibration 논의는 Ouroboros·Anthropic 공식 자료로 근거를 댔다.
