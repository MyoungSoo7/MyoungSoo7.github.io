---
layout: post
title: "피드백을 '검증된 학습'으로 — 에이전트 평가-피드백 파이프라인 해부"
date: 2026-07-24 09:33:00 +0900
categories: [AI, Architecture]
tags: [Ouroboros, FeedbackLoop, EvalHarness, EvidenceLedger, Independence, AgenticCoding, VerifiedLearning]
---

# 피드백은 어떻게 '검증된 학습'이 되는가

사람의 피드백("이거 이상해요", PR 리뷰, CI 실패)을 에이전트가 *안전하게* 받아 코드로 반영하고, 그 결과를 다시 다음 판단의 근거로 남기는 것 — 이것이 자기 개선 루프의 핵심이다. 아래 다이어그램은 그 **평가-피드백 운영 경로**(Ouroboros가 제안하는)를 한 장에 담았다.

![에이전트 평가-피드백 파이프라인 — Discord/GitHub 입력 → 증거 원장 → Eval Harness 4게이트(정확성·정직·정책·독립성) → Decision controller → Isolated/Verification/Independent 3레인 → resolution report + verified learning](/assets/images/ouroboros-feedback-eval-pipeline.jpg)

위에서 아래로 흐르는 이 파이프라인을 단계별로 해부한다. 이 글은 그동안의 시리즈 — [기록](/2026/07/23/ouroboros-manual-agentic-coding-code-analysis/)·[역할 분리](/2026/07/23/agent-roles-explorer-implementer-verifier/)·[운영 규칙](/2026/07/23/ai-work-operating-rules/) — 이 하나의 흐름으로 합쳐지는 지점이다.

---

## ① 입력 — 두 개의 피드백 원천

- **Discord feedback threads** (`#general` · `#general_ko`) — 사람의 자연어 피드백
- **GitHub evidence** (Issue · PR · review · CI) — 구조화된 기계 증거

핵심은 *성격이 다른 두 소스*를 함께 받는다는 것. 자연어 피드백은 "무엇이 불편한가"를, GitHub는 "무엇이 실제로 깨졌는가(CI·리뷰)"를 준다. 둘을 하나의 원장으로 합쳐야 판단이 온전해진다.

## ② 증거 수집 + 정본 원장(Canonical Feedback Ledger)

두 소스를 **단일 진실 원천**으로 모은다 — 피드백·증거·해결(resolution)을 append-only로 기록. 이건 [Ouroboros의 이벤트 소싱 원칙](/2026/07/23/ouroboros-manual-agentic-coding-code-analysis/) 그대로다: *"기록되지 않은 것은 일어나지 않은 것이다."* 원장이 있어야 "이 피드백이 어떤 PR/HEAD에서 나와 어떻게 처리됐나"를 재구성할 수 있고, 중복·모순을 잡을 수 있다.

## ③ Eval Harness — execute 전후 공통 게이트 (심장)

모든 변경이 실행 *전후*로 통과해야 하는 4개 게이트. 이 파이프라인의 심장이다.

| 게이트 | 요구 | 왜 |
|---|---|---|
| **정확성(Correctness)** | PR + HEAD 결속, 수용 피드백은 증거/유지보수자 표시 필요 | 피드백을 *구체적 커밋*에 묶어 추측 반영을 차단 |
| **정직(Honesty)** | AC · diff scope · lint/type/test/CI · **회귀 replay** | 진짜 검증만 인정 — 통과한 척(게이밍) 방지 |
| **정책(Policy)** | 메시지 가시성 · debounce/coalesce · **PARTIAL → Draft 금지** | 부분 완료를 완성처럼 내보내지 않음(safe-but-wrong 차단) |
| **독립성(Independence)** | 자기 작성 변경은 **별도 reviewer**, 권한/meta 변경은 승인 필수 | 작성자≠검증자 — 자기 코드를 자기가 통과시키지 못하게 |

네 게이트는 시리즈의 원칙을 그대로 코드 게이트로 만든 것이다:
- **정직**의 "회귀 replay"와 "PARTIAL → Draft 금지"는 [완료는 승인이 아니다](/2026/07/23/agent-roles-explorer-implementer-verifier/)의 증거 기반 검증.
- **독립성**의 "자기 변경은 별도 reviewer"는 [Explorer/Implementer/Verifier의 배심원 독립성](/2026/07/23/agent-roles-explorer-implementer-verifier/).
- **정확성**의 "증거/유지보수자 표시 필요"는 [Ouroboros의 요구사항 승격 정책](/2026/07/23/ouroboros-manual-agentic-coding-code-analysis/) — 확인된 것만 계약이 된다.

## ④ Decision controller — 소음을 다스린다

게이트를 통과한 피드백을 *어떻게 처리할지* 결정: **suppress**(무시) · **coalesce**(병합) · **community feedback window**(수렴 대기) · **revision** · **clarification** · **escalation**. 피드백은 중복되고, 서로 모순되고, 몰려 온다. 그대로 다 실행하면 [중복·충돌](/2026/07/24/when-multi-agent-is-a-loss/)이 터진다. debounce/coalesce로 *같은 피드백을 한 번만*, window로 *성급한 반영 대신 수렴을* 유도한다.

## ⑤ 세 실행 레인 — 권한을 쪼갠다

Decision이 실행으로 갈라진다. 세 레인의 권한이 다르다:

- **Isolated task** — *승인된 수정만*. 범위 밖은 못 건드림(최소 권한).
- **Verification** — AC · test · CI. 만들지 않고 검증만.
- **Independent** — review + reconcile. 독립 검토로 충돌을 조정.

이건 [Explorer/Implementer/Verifier 역할 분리](/2026/07/23/agent-roles-explorer-implementer-verifier/)의 실행 버전이다 — 구현·검증·조정을 다른 주체가 맡아, 자기 결정을 자기가 정당화하는 것을 구조적으로 막는다.

## ⑥ 출력 — Draft update + resolution report + verified learning

`feedback → patch → evidence → outcome 추적`. 단순히 코드를 고치고 끝이 아니라:
- **Draft update**: 실제 변경
- **Resolution report**: 무엇을 왜 어떻게 고쳤는지 (증거 포함)
- **Verified learning**: 이 결과가 **다음 triage/review의 근거**가 됨

마지막이 핵심 — 뱀이 꼬리를 무는 지점이다. 이번 해결의 outcome이 원장에 남아 *다음 피드백을 판단하는 입력*이 된다. [반복이 아니라 진화](/2026/07/23/ouroboros-manual-agentic-coding-code-analysis/)인 이유다.

---

## 왜 이 구조인가 — 위험한 루프를 안전하게

피드백 루프는 강력하지만 위험하다 — 잘못된 피드백을 반영하면 오류가 증폭되고, 검증 없이 돌면 소음이 쌓인다. 이 파이프라인은 그 위험을 **네 겹의 안전장치**로 감싼다:

1. **원장**(②) — 모든 것을 재구성 가능하게 기록
2. **게이트**(③) — 실행 전후로 정확성·정직·정책·독립성 강제
3. **컨트롤러**(④) — 소음(중복·성급함)을 다스림
4. **권한 분리**(⑤) — 자기 검증 금지, 최소 권한

그래서 이 흐름은 단순한 "피드백 받기"가 아니라, **피드백을 검증된 학습으로 바꾸는 규율**이다. 사람의 한마디가 안전하게 코드가 되고, 그 결과가 다시 더 나은 판단의 근거가 되는 — 자기 개선 시스템이 갖춰야 할 최소 골격이다.

---

## 출처 · 관련 글

- 첨부 이미지: 사용자 제공(Ouroboros 평가-피드백 운영 경로 다이어그램).
- 이벤트 소싱·평가 게이트·배심원 독립성·요구사항 승격의 근거: [Ouroboros 3부작 정리](/2026/07/23/ouroboros-manual-agentic-coding-code-analysis/) (원 저장소 Q00/ouroboros 실측 분석 기반).
- 관련 본인 정리글: [Explorer/Implementer/Verifier 역할 분리](/2026/07/23/agent-roles-explorer-implementer-verifier/) · [AI 작업 운영 규칙](/2026/07/23/ai-work-operating-rules/) · [멀티에이전트가 손해인 순간](/2026/07/24/when-multi-agent-is-a-loss/) · [하네스의 세 문서(SPEC/PLAN/DONE)](/2026/07/24/harness-spec-plan-done-criteria/)

> 참고: 파이프라인 구조·게이트 항목은 이미지(Ouroboros 평가-피드백 운영 경로) 기준이며, 본문은 각 단계를 시리즈에서 정리한 원칙과 연결해 해설했다.
