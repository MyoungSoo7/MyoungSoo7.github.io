---
layout: post
title: "Ouroboros 3부작 정리 — 매뉴얼 · Agentic Coding 5원칙 · 왜 프롬프트가 아니라 코드인가"
date: 2026-07-23 06:50:00 +0900
categories: [AI, Architecture]
tags: [Ouroboros, AgenticCoding, ClaudeCode, SpecFirst, EventSourcing, RewardHacking, FailClosed, CodeOverPrompts, HarnessEngineering]
---

# 세 편의 해부를 한자리에

Ouroboros를 제대로 이해하려면 세 개의 문서를 같이 읽어야 한다. 하나는 *어떻게 쓰는가*(매뉴얼), 하나는 *무엇을 가르치는가*(Agentic Coding 원칙), 하나는 *왜 이렇게 만들었는가*(코드 분석)다. 이 글은 그 세 편을 밀도 있게 하나로 엮은 종합 정리다. 원문 세 편을 먼저 첨부한다.

- 📖 [Ouroboros 매뉴얼 — 동작 원리와 활용법](https://codex.epril.com/wiki/ouroboros-manual-guide-usage)
- 📖 [Ouroboros에서 배우는 Claude Code 기반 Agentic Coding](https://codex.epril.com/wiki/agentic-coding-lessons-from-ouroboros-claude-code)
- 📖 [Ouroboros의 코드 분석 — 왜 프롬프트가 아니라 코드인가](https://codex.epril.com/wiki/ouroboros-code-analysis-why-code-over-prompts)

세 문서 모두 오픈소스 저장소 **Q00/ouroboros**(약 22만 줄 Python, 1,100여 파일)의 소스·문서를 실측 분석한 것이며, 분석 기준은 2026-07-19 main 브랜치(커밋 `7a064482`)다. 아래 인용한 상수·경로·수치는 전부 그 실측값이다.

---

# Part 1. 매뉴얼 — Ouroboros는 무엇이고 어떻게 쓰는가

## "프롬프트를 멈추고, 명세하라"

Ouroboros는 **명세 우선(specification-first) AI 워크플로 엔진**이다. 슬로건은 "Stop prompting. Start specifying." 핵심 진단은 이것이다 — **대부분의 AI 코딩 실패는 출력이 아니라 입력에서 발생한다. 병목은 AI의 능력이 아니라 인간의 명확성이다.**

Claude Code·Codex CLI·OpenCode·Gemini·Copilot 등 다양한 AI 코딩 CLI 위에서 *같은 워크플로*를 돌리는 로컬 우선 런타임 계층이며, 비결정적 에이전트 작업을 **재현 가능(replayable)·관측 가능(observable)·정책에 묶인(policy-bound)** 실행 계약으로 바꾼다. 3개 저장소로 된 "Agent OS" 스택에서 커널(OS 계층)에 해당한다.

## 전체 라이프사이클 — 반복이 아니라 진화

```
Interview → Seed → Execute → Evaluate
    ↑                              │
    └──────── Evolutionary Loop ───┘
```

| 단계 | 하는 일 |
|---|---|
| **Interview** | 소크라테스식 질문으로 숨은 가정 노출 |
| **Seed** | 답변을 *불변* 명세로 결정화(crystallize) |
| **Execute** | Double Diamond: Discover → Define → Design → Deliver |
| **Evaluate** | 3단계 게이트: Mechanical($0) → Semantic → 다중모델 Consensus |
| **Evolve** | Wonder("아직 뭘 모르나?") → Reflect → 다음 세대 |

평가의 출력이 다음 세대 Seed의 입력이 된다 — 그래서 각 사이클은 반복이 아니라 진화다.

## 두 개의 수학적 관문

Ouroboros 전체를 관통하는 두 상수:

- **입구 게이트 — 모호도(Ambiguity) ≤ 0.2.** `Ambiguity = 1 − Σ(clarity_i × weight_i)`. 각 명확도 차원(Goal/Constraint/Success/Context)을 LLM이 temperature 0.1로 채점해 가중합. 이 값 아래로 내려가야만 Seed 생성이 허용된다. "가중 명확도 80%면 남은 미지수는 코드 레벨 결정으로 흡수 가능"하기 때문.
- **출구 게이트 — 온톨로지 유사도(Similarity) ≥ 0.95.** `Similarity = 0.5×이름겹침 + 0.3×타입일치 + 0.2×완전일치`. 연속 세대의 스키마가 이만큼 안정되면 루프가 수렴·종료. 안전 밸브로 **30세대 하드 캡**.

> 명확해지기 전에는 만들지 말고(≤0.2), 안정되기 전에는 진화를 멈추지 말라(≥0.95).

## 설치와 첫 실행

```bash
# Claude Code 플러그인 (권장, Python 설치 불필요)
claude plugin marketplace add Q00/ouroboros
claude plugin install ouroboros@ouroboros
ooo setup           # MCP 서버 전역 등록(1회) + 프로젝트 설정

# 가장 빠른 길: 목표 하나로 인터뷰→A등급 Seed→실행 인계까지 자동
ooo auto "태스크 관리 CLI를 만들어줘"
```

주요 명령: `ooo interview`(질문), `ooo run`(Double Diamond 실행), `ooo evaluate`(3단계 검증), `ooo evolve`(수렴까지 진화), `ooo ralph`(세션 경계 넘어 수렴까지 지속 루프), `ooo unstuck`(막혔을 때 5개 수평사고 페르소나), `ooo brownfield`(기존 코드베이스 스캔). 에이전트 세션 안에서는 `ooo <cmd>` 스킬, 터미널에서는 `ouroboros` CLI.

## 아홉 개의 마음(The Nine Minds)

필요할 때만 로드되는 9개 사고 모드 에이전트: Socratic Interviewer(질문만·절대 안 만듦), Ontologist(본질 탐색), Seed Architect(명세 결정화), Evaluator(3단계 검증), Contrarian(모든 가정에 도전), Hacker(비관습 경로), Simplifier(복잡성 제거), Researcher(코딩 멈추고 조사), Architect(구조적 원인). 각각 단일 입장과 핵심 질문 하나를 갖는다.

---

# Part 2. Agentic Coding — 다섯 원칙

이 부분이 Ouroboros가 *도구를 넘어* 우리에게 가르치는 핵심이다. 모든 원칙은 관념이 아니라 **작동하는 코드와 상수**로 존재한다.

## 0장. 진짜 실패는 "능력 부족"이 아니라 "계약 표류"

가장 잡기 어려운 실패는 **Safe-but-Wrong** — "실행 결과가 안전하고, 파괴적이지 않고, 심지어 유용하면서도, 사용자가 말한 목표에 대해서는 틀린" 경우다. 파일도 안 지웠고 테스트도 통과하는데 산출물 계약이 표류했다. 명백한 차단보다 나쁜 이유는 **거짓 확신**을 만들기 때문. 전형적 사례: 도구를 원했는데 인수인계 문서가 옴, 결측 데이터를 `0`/`OK`로 위장. 방어는 **산출물 계약 6점 검사**(종류·실행 표면·보조 산출물 위장·결측 의미론·과거 교정 이력·검증 증거).

## 원칙 I — 명확해지기 전에는 만들지 마라

모호함을 *숫자*로 만든다(위 입구 게이트). 세부 설계가 배울 만하다:

- **차원별 하한선**: 전체 점수와 별개로 Goal≥0.75, Constraint≥0.65, Success≥0.70을 각각 요구 → "평균의 함정"(한 차원의 우수함이 다른 결핍을 가림) 차단.
- **의도적 유보는 감점 안 함**: "나중에 결정"은 의도적이므로 OK. *명확함이란 모든 걸 아는 게 아니라 모르는 걸 아는 것.*
- **명세는 결과의 목록, AC 3~7개**: "형제 AC의 하위 단계인 AC는 결함이다." 구현 분해는 실행 엔진의 몫 — 명세 단계에서 하면 토큰만 곱한다.
- **승격 정책**: 제품 레퍼런스·모델의 추측을 사용자 확인 없이 수용 기준으로 바꾸지 마라. **요구사항의 혈통(provenance)**을 지킨다.
- **Seed는 불변**: 목표·제약·수용 기준은 frozen. 실행 중 조용한 목표 재해석(=계약 표류)이 구조적으로 불가능해진다.

## 원칙 II — 완료는 승인이 아니다

"완료했습니다"에는 세 개의 다른 질문이 섞여 있다: ①끝났나(실행 상태) ②맞나(공식 평결) ③표류했나(드리프트). Ouroboros는 이를 *타입 수준*에서 분리한다("완료된 태스크는 실행이 끝났다는 증거일 뿐, AC 통과의 증명이 아니다").

**비용 사다리 $0 → $$ → $$$:**

| 단계 | 비용 | 내용 |
|---|---|---|
| Stage 1 Mechanical | $0 | 린트·빌드·테스트·커버리지. 실패하면 다음 단계 스킵 |
| Stage 2 Semantic | LLM 1회 | 구조화 JSON(score·ac_compliance·drift·reward_hacking_risk). 승인선 score≥0.8 + AC준수 |
| Stage 3 Consensus | 프런티어 다중모델 | 트리거 시에만. Advocate+Devil+Judge 법정 구조, 2/3 다수결 |

배울 점: **에이전트의 주장이 아니라 산출물(실제 코드)을 평가한다.** 그리고 **리워드 해킹 거부권** — 모든 승인 경로가 지나는 단 하나의 관문에서 `if reward_hacking_risk >= 0.7: final_approved = False`. 하드코딩·테스트 전용 분기·자리표시자를 탐지. **배심원 독립성**: 실행한 모델과 같은 벤더는 배심원에서 제외하되, 표가 2명 미만이 되면 필터링을 포기(순수성보다 표).

## 원칙 III — 기록되지 않은 것은 일어나지 않은 것이다

**이벤트 소싱**이 척추다. 모든 상태 변화는 불변 `BaseEvent`로 SQLite append-only 테이블에 기록되고(이름은 `execution.ac.completed` 같은 *과거형*), 모든 읽기 모델은 이벤트를 fold해 투영한다. 직접 저장되는 권위 상태는 없다. 그래서 "머신이 재시작돼도 뱀은 멈춘 자리에서 다시 시작"한다.

**드리프트 측정**은 놀랍도록 싸다 — LLM이 아니라 Jaccard 유사도: `combined = goal×0.5 + constraint×0.3 + ontology×0.2`, 허용선 ≤0.3. 상시 감시 지표는 싸고 결정론적이어야 하고, 정밀 판단(LLM)은 경보가 울린 뒤 투입한다. 3 이터레이션마다 **자동 회고**로 재측정.

## 원칙 IV — 반복하지 말고 진화하라

루프의 양 끝에 관문(≤0.2, ≥0.95). 2세대부터 인터뷰를 대체하는 두 엔진의 **온도 차이**가 의도적이다: Wonder(발산, 0.7) "아직 뭘 모르나?" → Reflect(수렴, 0.5) "스펙을 어떻게 고치나?" → 채점(측정, 0.1). *발산은 뜨겁게, 수렴은 미지근하게, 측정은 차갑게.*

**만족화(satisficing)**: "통과했고 도전받지 않은 AC는 그대로 유지" — LLM이 어겨도 결정론적 백스톱이 강제 keep. **정체의 네 얼굴**(전부 SHA-256 해시·뺄셈, LLM 없음): Spinning(같은 출력 3회)·Oscillation(A→B→A→B)·No-Drift(변화<0.01)·Diminishing Returns(개선폭<0.01). 처방은 "더 세게"가 아니라 **수평 사고** — 정체 패턴별로 5개 페르소나 매핑(Spinning→Hacker, No-Drift→Researcher, Diminishing→Simplifier, Oscillation→Architect, 만능→Contrarian). 개입 예산도 1회.

## 원칙 V — 자율성에는 경계를 세워라

핵심 관용구는 코드베이스에 106회 등장하는 **"불확실하면 닫힌 쪽으로 실패하라(fail-closed)."**

- **워치독**: idle 타임아웃(2h)과 no-progress 타임아웃(4h)을 구별 — *활동 ≠ 진전*. 로그만 쏟아내는 에이전트도 실질 진전 없으면 잡힌다.
- **비용 라우팅**: `frugal → standard → frontier` 사다리. 신뢰는 증명으로 벌어 강등, 실패는 재시도로 승급. **자동화는 사용자의 명시적 모델 선택을 이기지 않는다.**
- **fail-closed 기본값**: 신뢰·독립성·유효성은 *입증될 때만* 인정. 미상은 관대하게 받지 않고 거부.
- **모든 루프에 예산**: 세대 30·페르소나 개입 1·재시도 10·토큰은 "잘렸다는 증거"가 있을 때만 2배.

## Claude Code로 오늘 실천하기

세 문서가 공통으로 강조하는 실전 매핑:

| Ouroboros 장치 | 원칙 | Claude Code 대응물 |
|---|---|---|
| Socratic Interview + 모호도 게이트 | I. 명세 | 계획 모드, 착수 전 질문 지시, AskUserQuestion |
| 불변 Seed | I. 명세 | `SPEC-*.md` 파일, 승인된 계획 |
| 3단계 평가 | II. 검증 | lint/test 훅 → 자체 평가 → 리뷰 서브에이전트 |
| 배심원 독립성 | II. 검증 | 깨끗한 컨텍스트의 서브에이전트 리뷰(구현 대화 미공유) |
| 이벤트 소싱 | III. 기록 | git 커밋 이력, 작업 저널 파일 |
| 정체 감지 + 5 페르소나 | IV. 진화 | 정체 프로토콜, 페르소나 서브에이전트 병렬 소집 |
| 워치독 + fail-closed | V. 경계 | 권한 allow/ask/deny, PreToolUse 훅, 예산 명시 |

바로 복사해 쓰는 문장 하나: *"구현하지 말고, 먼저 모호함이 가장 큰 부분부터 하나씩 질문해줘. 충분히 명확해지면 수용 기준 3~7개짜리 명세를 만들어 승인받고 시작해."*

---

# Part 3. 코드 분석 — 왜 프롬프트가 아니라 코드인가

세 번째 문서는 가장 근본적인 질문에 답한다: *스킬 21개·에이전트 페르소나 ~15개는 얇은 인터페이스 껍질이고, 본체는 약 22만 줄 Python이다. 왜?*

## 코드 질량이 몰린 곳

| 패키지 | LOC | 역할 |
|---|---|---|
| orchestrator/ | 60,606 | 실행 엔진: AC 병렬 실행, 런타임 어댑터 13종, 제어 평면, 워치독 |
| mcp/ | 36,605 | MCP 서버 ~30개 도구, 백그라운드 잡, 보안 |
| auto/ | 21,762 | `ooo auto` 상태 기계 |
| cli/ | 19,314 | Typer 기반 CLI ~20종 |
| providers/ | 11,517 | LLM 어댑터 14종 |
| evaluation/ | 7,382 | 3단계 평가, 리워드 해킹 방어 |
| **resilience/** | **1,607** | 정체 4패턴 감지 |
| **observability/** | **1,812** | 드리프트 측정 |

**상위 4개(orchestrator·mcp·auto·cli)가 전체의 약 60%.** 이들은 "AI에게 뭘 시킬까"(프롬프트)가 아니라 **"AI를 어떻게 안전하게 구동·관리·검증·복구할까"(인프라)**를 다룬다. 반대로 철학적으로 가장 유명한 정체 감지(1,607)·드리프트(1,812)는 놀랍도록 작다. **좋은 원리는 코드가 적게 들고, 그 원리를 현실에서 굴리는 인프라가 코드를 많이 먹는다.**

## 코드여야만 하는 6가지 이유

1. **프롬프트는 지시, 코드는 강제.** "테스트 조작하지 마"라는 프롬프트와, 모든 승인 경로가 지나는 관문의 `if risk >= 0.7: approved = False`는 완전히 다른 보증 수준. *서명 패턴: "LLM은 제안하고, 결정론적 코드가 처분한다."*
2. **상태는 프롬프트에 살 수 없다.** 세션은 휘발성 → 6,000줄 넘는 영속성 코드(이벤트 스토어·UoW)가 "재시작해도 이어짐"을 지불.
3. **측정은 결정론적이어야 한다.** 관문 수치(0.2/0.3/0.95)가 실행마다 흔들리면 관문이 아님 → 모호도는 temperature 0.1 고정 + 순수 Python 가중합, 드리프트·정체·수렴은 LLM 없이 해시·Jaccard.
4. **프로세스 오케스트레이션은 시스템 프로그래밍.** 13종 외부 CLI를 자식 프로세스로 구동(스폰/취소/재생 수명주기, CLI별 스트림 파싱) — orchestrator가 6만 줄인 이유.
5. **프로토콜은 구현해야 한다.** 스킬이 엔진을 부르는 다리가 MCP 서버(36,605줄). `ooo ralph` 같은 장시간 루프는 "MCP 서버가 루프를 소유"하게 설계 — *루프의 신뢰성이 중요하면 루프를 프롬프트에서 코드로 옮긴다.*
6. **보안은 프롬프트를 불신하는 데서 시작.** sanitize/redact 246곳, DoS 상한, 원자적 설정 쓰기, 신뢰 불가 저장소 설정도 allowlist 안에서만.

## `ooo run` 한 번의 흐름

```
[Claude Code 세션] "ooo run seed.yaml"
  ① 스킬(프롬프트)  — SKILL.md가 MCP 도구 호출을 선언 (지능이 아니라 디스패치)
  ② MCP 서버(파이썬) — 요청 검증 → OrchestratorRunner (장시간이면 detached job)
  ③ 코어 엔진        — Seed 파싱(frozen) → AC 의존성 분석 → 병렬 실행 계획
  ④ 런타임 어댑터    — 백엔드 CLI를 자식 프로세스로 스폰 → 여기서 두 번째 LLM이 코드 작성
  ⑤ 이벤트 스토어    — 모든 단계가 불변 이벤트로 기록 (대시보드는 이 DB를 읽음)
  ⑥ 평가 파이프라인  — $0→$$→$$$, 단일 관문 리워드 해킹 거부권
```

읽어야 할 것: **프롬프트는 ①에만 있다.** LLM은 두 번 등장 — 첫 LLM(운전자)은 스킬을 읽고 MCP를 호출, 둘째 LLM(작업자)은 실제 코드를 작성. 그 사이 ②③은 전부 결정론적 Python이 **두 LLM 사이에 끼어 계약을 집행**한다. 관측이 사이드채널이 아니라 DB 읽기인 이유도 같다 — "기록이 곧 진실"이므로 화면은 기록의 투영일 뿐.

## 이 코드베이스가 가르치는 분업 원리

프롬프트와 코드의 경계선은 하나의 질문으로 판별된다:

> **"이것이 확률적으로 지켜져도 되는가, 결정론적으로 보장되어야 하는가?"**

전자(창의적 판단·페르소나·라우팅 선언)는 프롬프트로, 후자(규칙 강제·상태·측정·프로세스·프로토콜·보안·예산)는 코드로. Ouroboros의 22만 줄은 *후자의 목록이 생각보다 훨씬 길다*는 증거다.

그리고 이건 우리 자신의 Claude Code 활용에 그대로 적용된다: **CLAUDE.md의 지시(프롬프트)는 에이전트가 따르려 *노력*하는 것이고, hooks·권한·CI 게이트(코드)는 구조적으로 *강제*되는 것이다. 중요한 규칙일수록 왼쪽 열(프롬프트)에서 오른쪽 열(코드)로 옮겨야 한다.**

---

# 종합 — 위험한 루프를 안전하게 만드는 조건들

세 문서를 하나로 꿰면 Ouroboros라는 이름의 뜻이 드러난다. 자기 꼬리를 삼키는 뱀 — *출력이 입력이 되는 구조* — 는 위험하다. 피드백 루프는 오류도 증폭하기 때문이다. 22만 줄 전체가 그 위험을 안전하게 만들기 위한 조건의 목록이다:

1. 루프에 들어가기 전에 **명확함을 측정**하고 (원칙 I)
2. 각 바퀴에서 **완료와 승인을 분리**하고 (원칙 II)
3. 모든 바퀴를 **재생 가능하게 기록**하고 (원칙 III)
4. 바퀴가 진전인지 공회전인지 **구별**하고 (원칙 IV)
5. 루프 전체를 **예산과 울타리로 감싼다** (원칙 V)

우리가 AI 에이전트와 매일 만드는 것이 바로 이런 피드백 루프 — 우리의 지시가 출력이 되고, 그 출력이 다음 지시의 입력이 되는 — 다. 그 루프를 **증폭기로 만들지 소각로로 만들지는 모델 성능이 아니라 루프의 설계가 결정한다.** 뱀은 반복하지 않는다. 진화한다.

---

## 출처

이 글은 아래 세 편(모두 codex.epril.com 위키)을 참고·요약한 것이며, 세 문서는 공통으로 오픈소스 저장소 **Q00/ouroboros**(2026-07-19 main, 커밋 `7a064482`)의 소스·문서를 실측 분석한 1차 자료다. 인용한 상수·경로·LOC는 그 실측값이다.

- Ouroboros 매뉴얼 — 동작 원리와 활용법: <https://codex.epril.com/wiki/ouroboros-manual-guide-usage>
- Ouroboros에서 배우는 Claude Code 기반 Agentic Coding: <https://codex.epril.com/wiki/agentic-coding-lessons-from-ouroboros-claude-code>
- Ouroboros의 코드 분석 — 왜 프롬프트가 아니라 코드인가: <https://codex.epril.com/wiki/ouroboros-code-analysis-why-code-over-prompts>
- 원 저장소: Q00/ouroboros (README·docs/architecture.md·docs/guides/ 등 원문 인용의 출처)

> 참고: 본문의 수치·인용은 위 위키 문서가 명시한 분석 시점(2026-07)의 코드베이스 실측값에 근거한다. 코드는 이후 진화했을 수 있다.
