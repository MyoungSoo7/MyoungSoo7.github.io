---
layout: post
title: "에이전트를 역할로 쪼개라 — 탐색(Explorer)·구현(Implementer)·검증(Verifier)"
date: 2026-07-23 12:20:00 +0900
categories: [AI, Architecture]
tags: [SubAgents, ClaudeCode, LeastPrivilege, SeparationOfConcerns, Explorer, Implementer, Verifier, RewardHacking]
---

# 가장 안전한 에이전트 세팅은 '똑똑한 하나'가 아니라 '역할이 나뉜 셋'

에이전트 하나에게 탐색·구현·검증을 다 시키면 세 가지가 무너진다 — 탐색 소음이 컨텍스트를 오염시키고, 구현이 범위를 넘고, 자기가 짠 코드를 자기가 통과시킨다. 해법은 더 똑똑한 모델이 아니라 **역할 분리 + 최소 권한**이다. 아래 표가 그 설계다.

![에이전트 3역할 매트릭스 — Explorer/Implementer/Verifier 각각의 책임·도구 권한·산출물·금지 행동](/assets/images/agent-roles-explorer-implementer-verifier.jpg)

| 역할 | 책임 | 도구 권한 | 산출물 | 금지 행동 |
|---|---|---|---|---|
| **Explorer** | 읽기·조사·위험 발견 | 읽기·검색 전용 | 파일 목록, 발견사항, 수정 후보, 위험 | 코드 수정, raw 로그 덤프 |
| **Implementer** | 계획 범위 안에서만 구현 | 읽기 + 편집 | 변경 파일, 구현 요약, 테스트 명령 | 범위 확장, 임의 리팩터링, *테스트만 고치기* |
| **Verifier** | 테스트·리뷰·완료 기준 확인 | 읽기·검색·실행 | pass/fail, 근거, 누락 조건 | 새 기능 구현 |

이 표의 힘은 오른쪽 두 열 — **도구 권한**과 **금지 행동** — 에 있다. "무엇을 하라"보다 "무엇을 *할 수 없게* 하라"가 안전을 만든다.

---

## Explorer — 읽되, 절대 건드리지 않는다

**책임**은 읽기·조사·위험 발견. **도구는 읽기·검색 전용.** 산출물은 파일 목록·발견사항·수정 후보·위험이다.

핵심은 **컨텍스트 격리**다. web search, 파일 읽기, 코드베이스 탐색은 중간 결과가 폭발하는데, 이 소음이 메인 대화로 쏟아지면 판단이 흐려진다. Claude Code 공식 문서도 서브에이전트의 첫 이점으로 *"탐색과 구현을 메인 대화 밖으로 분리해 컨텍스트를 보존"* 함을 든다 — 서브에이전트는 자기 컨텍스트 창에서 일하고 **요약만** 돌려준다.

**금지 행동이 날카롭다: 코드 수정 금지, raw 로그 덤프 금지.** 탐색자가 코드를 만지기 시작하면 격리가 깨지고, 로그를 통째로 붙이면 [요약 대신 소음](/2026/07/23/ai-fix-5-question-patterns/)이 된다. Explorer의 산출물은 *정제된 발견*이지 원자재가 아니다. (Ouroboros의 Socratic Interviewer가 *"절대 만들지 않는다"* 로 못 박은 것과 같은 원리다.)

## Implementer — 계획 범위 '안에서만' 만든다

**책임**은 계획 범위 안에서만 구현. **도구는 읽기+편집.** 산출물은 변경 파일·구현 요약·테스트 명령이다.

세 가지 **금지 행동**이 이 역할의 정수다:
1. **범위 확장 금지** — 시키지 않은 걸 "이왕 하는 김에" 하지 않는다.
2. **임의 리팩터링 금지** — 통과·승인된 코드를 지나가며 고치는 건 [회귀 위험 + 리뷰 부담 + 예산 낭비의 삼중 손실](/2026/07/23/ouroboros-manual-agentic-coding-code-analysis/)이다.
3. **테스트만 고치기 금지** — 가장 교활한 실패. 기능을 고치는 대신 *테스트를 통과하게 만들려고 테스트를 수정*하는 것. 이건 [Ouroboros가 거부권(veto)으로 차단하는 리워드 해킹](/2026/07/23/ouroboros-manual-agentic-coding-code-analysis/) 그 자체다.

Implementer에게 편집 권한을 주되 **범위라는 울타리**를 함께 준다. 자율성은 경계 안에서만 신뢰할 수 있다.

## Verifier — 검증만 하고, 만들지 않는다

**책임**은 테스트·리뷰·완료 기준 확인. **도구는 읽기·검색·실행.** 산출물은 pass/fail·근거·누락 조건이다.

**금지 행동: 새 기능 구현 금지.** 이게 왜 중요한가? 검증자가 구현을 겸하면 **자기 결정을 정당화**하게 되기 때문이다. Anthropic의 멀티에이전트 시스템이 서브에이전트마다 *"distinct tools, prompts, and exploration trajectories"* 로 관심사를 분리하고, 별도의 CitationAgent를 두는 이유가 이것 — **작성자와 검증자를 분리**해야 검증이 독립적이다. (Ouroboros도 "실행한 자가 승인하지 않는다"는 배심원 독립성을 코드로 강제한다.)

Verifier의 산출물이 `pass/fail` + **근거** + **누락 조건**인 것도 중요하다. "좋아 보임"이 아니라 *증거와 함께* 판정해야 하고, 무엇을 확인 못 했는지(누락)까지 정직하게 남겨야 한다.

---

## 이 표를 Claude Code로 구현하기

세 역할은 그대로 **Claude Code 서브에이전트 3개**가 된다. 공식 문서가 말하는 서브에이전트의 이점이 정확히 이 표의 열들이다 — *"각 서브에이전트는 자체 컨텍스트 창 + 특정 도구 접근 + 독립 권한"*, 그리고 *"사용 도구를 제한해 제약을 강제(Enforce constraints by limiting which tools a subagent can use)."*

`tools` frontmatter로 **도구 권한 열**을 그대로 코드화한다:

```markdown
# .claude/agents/explorer.md
---
name: explorer
description: 코드베이스 탐색·조사·위험 발견. 읽기 전용.
tools: Read, Grep, Glob        # 읽기·검색 전용 (편집·실행 없음)
---
너는 Explorer다. 읽고 조사해 발견사항·수정후보·위험을 요약한다.
코드를 수정하지 않는다. raw 로그를 덤프하지 않는다 — 정제된 요약만 반환한다.
```

```markdown
# .claude/agents/implementer.md
---
name: implementer
description: 승인된 계획 범위 안에서만 구현.
tools: Read, Edit, Write, Bash  # 읽기+편집
---
너는 Implementer다. 주어진 SPEC 범위 안에서만 구현한다.
범위를 확장하지 않고, 임의 리팩터링을 하지 않으며,
테스트를 통과시키려고 테스트를 수정하지 않는다(고쳐야 하면 사유를 먼저 보고).
산출물: 변경 파일, 구현 요약, 검증 명령.
```

```markdown
# .claude/agents/verifier.md
---
name: verifier
description: 테스트·리뷰·완료 기준 확인. 구현하지 않음.
tools: Read, Grep, Bash         # 읽기·검색·실행 (편집 없음 → 새 기능 구현 불가)
---
너는 Verifier다. diff와 SPEC만 받아 수용 기준 충족을 검증한다.
새 기능을 구현하지 않는다. 출력: pass/fail + 근거 + 누락 조건.
```

**주목할 설계**: Verifier에 `Edit`/`Write`를 아예 주지 않으면, "새 기능 구현 금지"가 프롬프트의 부탁이 아니라 **구조적 강제**가 된다. [중요한 규칙일수록 프롬프트에서 코드로 옮긴다](/2026/07/23/ai-work-operating-rules/) — 도구 권한 제한이 바로 그 "코드로 옮기기"다.

---

## 한 줄 결론

Explorer·Implementer·Verifier는 세 가지 원칙의 결합이다 — **최소 권한**(각자 필요한 도구만), **관심사 분리**(탐색≠구현≠검증), **증거 인계**(각자 정해진 산출물로). 에이전트를 더 똑똑하게 만들기 전에, 역할을 나누고 권한을 좁혀라. 금지 행동 하나하나가 당신이 겪어봤을 실패 하나하나를 막는다.

---

## 출처

- 첨부 이미지: 사용자 제공(에이전트 3역할 매트릭스).
- Claude Code, **Create custom subagents** (공식) — 자체 컨텍스트 창·도구 접근 제한·독립 권한, "탐색/구현 분리로 컨텍스트 보존", "도구 제한으로 제약 강제": <https://code.claude.com/docs/en/sub-agents>
- Anthropic, **How we built our multi-agent research system** (공식) — 서브에이전트별 distinct tools/prompts, 별도 CitationAgent(작성/검증 분리): <https://www.anthropic.com/engineering/multi-agent-research-system>
- 관련 본인 정리글: [Ouroboros 3부작](/2026/07/23/ouroboros-manual-agentic-coding-code-analysis/)(리워드 해킹 거부권·배심원 독립성·최소권한 역할) · [AI 작업 운영 규칙](/2026/07/23/ai-work-operating-rules/) · [멀티에이전트 설계 원칙 13가지](/2026/07/23/multi-agent-system-design-principles/)

> 참고: 위 서브에이전트 예시의 `tools` 값은 예시이며, 실제 도구명·권한은 Claude Code 버전과 프로젝트 설정에 맞춰 조정하라. 핵심은 "역할별로 도구를 좁힌다"는 원리다.
