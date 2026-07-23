---
layout: post
title: "멀티에이전트 조율 패턴 5가지 — Anthropic의 패턴 선택 프레임워크 해설"
date: 2026-07-23 21:40:00 +0900
categories: [AI, Architecture]
tags: [MultiAgent, CoordinationPatterns, Orchestrator, GeneratorVerifier, AgentTeams, MessageBus, SharedState, Anthropic]
---

# "정교해 보여서" 패턴을 고르지 마라

Anthropic이 발표한 [Multi-Agent Coordination Patterns](https://claude.com/blog/multi-agent-coordination-patterns)의 핵심 진단은 뼈아프다 — **팀은 종종 "문제에 맞아서"가 아니라 "정교해 보여서" 조율 패턴을 고른다.** 처방은 단순하다: *가장 단순한 패턴으로 시작하고, 구체적 한계가 드러날 때 진화시켜라.* 패턴 선택은 취향이 아니라 **컨텍스트 경계와 정보 흐름**에 대한 구조적 질문의 답이어야 한다.

이 글은 그 5가지 패턴과 선택 프레임워크를 해설한다. ([어제 정리한 멀티에이전트 설계 원칙 13가지](/2026/07/23/multi-agent-system-design-principles/)가 "무엇을 설계하나"였다면, 이 글은 "어떻게 조율하나"다.)

---

## 패턴 1. Generator-Verifier — 만들고, 검증한다

**정의**: 한 에이전트가 초안을 만들고, verifier가 *명시적 기준*으로 평가해 수용하거나 피드백과 함께 되돌린다.

- **언제**: 품질이 중요하고 *평가 기준이 명확*한 출력
- **예시**: 고객 지원 이메일 생성, 테스트 검증이 딸린 코드 리뷰, 팩트체크, 컴플라이언스 검증
- **강점**: 단순하고, 경계가 분명한 품질 게이트에 효과적
- **약점**: 검증 기준이 명확히 정의돼야 함. verifier가 실질 평가 없이 *고무도장(rubber-stamp)* 찍을 위험. 생성자가 피드백을 못 받아내면 반복 루프가 정체
- **안티패턴**: "검증이 무엇인지 정의하지 않은 채 루프만 돌리면 실체 없는 *품질 통제의 환상*이 생긴다."

이건 [Explorer/Implementer/Verifier 글](/2026/07/23/agent-roles-explorer-implementer-verifier/)의 Verifier, 그리고 [Ouroboros의 3단계 평가 게이트](/2026/07/23/ouroboros-manual-agentic-coding-code-analysis/)와 같은 뿌리다 — verifier는 rubric·source of truth·max iteration·escalation을 가져야 진짜 검증이다.

## 패턴 2. Orchestrator-Subagent — 계획하고, 위임하고, 종합한다

**정의**: 리드 에이전트가 작업을 계획해 전문 서브에이전트에 위임하고, 결과를 종합한다.

- **언제**: 작업 분해가 명확하고 *하위작업의 경계가 뚜렷할* 때
- **예시**: 자동 코드 리뷰 — 보안 검사·테스트 커버리지·코드 스타일·아키텍처 평가를 각각 별도 에이전트에 분배
- **강점**: 계층 구조가 명확하고, 각 서브에이전트가 맥락 집중을 유지
- **약점**: 오케스트레이터가 **정보 병목**이 됨. 서브에이전트끼리 발견을 직접 공유하기 어려움. 명시적으로 병렬화하지 않으면 순차 실행이 처리량을 제한

## 패턴 3. Agent Teams — 지속하는 워커들이 큐에서 작업을 집는다

**정의**: 코디네이터가 여러 *지속적(persistent)* 워커 에이전트를 띄우고, 워커들이 공유 큐에서 작업을 claim해 여러 단계에 걸쳐 자율 수행하고 완료를 신호한다.

- **언제**: 병렬적이고 독립적이며 *오래 걸리는* 하위작업
- **예시**: 코드베이스 마이그레이션 — 각 팀원이 서로 다른 서비스를 독립적으로 담당
- **강점**: 워커가 여러 할당에 걸쳐 **지속 컨텍스트를 축적**. 도메인 특화로 성능 향상
- **약점**: *완전한 독립성*을 요구. 중간 발견 공유가 어려움. 작업 시간이 들쭉날쭉하면 완료 감지가 어려움. 공유 자원 동시 쓰기 시 충돌

## 패턴 4. Message Bus — 이벤트를 발행하고 구독한다

**정의**: 에이전트들이 라우터를 통해 이벤트를 발행(publish)·구독(subscribe)하고, 라우터가 매칭되는 구독자에게 메시지를 전달한다.

- **언제**: *이벤트 기반* 파이프라인이면서 에이전트 생태계가 계속 커질 때
- **예시**: 보안 운영 자동화 — triage 에이전트가 경보를 분류해 전문 조사 에이전트(네트워크·아이덴티티)로 라우팅, 컨텍스트 수집·대응 조정 에이전트가 협업
- **강점**: 유연한 이벤트 라우팅. 기존 연결을 다시 배선하지 않고 새 에이전트 추가 가능. 의미 기반(semantic) 라우팅 지원
- **약점**: 연쇄 이벤트를 가로지르는 **실행 추적이 어려움**. 라우터 오분류 시 조용한 실패. 순차 오케스트레이터 대비 디버깅 불투명

## 패턴 5. Shared-State — 공유 저장소에 직접 읽고 쓴다

**정의**: 에이전트들이 중앙 조율 없이 자율적으로, 영속 저장소(DB·파일시스템·문서)에 직접 읽고 쓴다.

- **언제**: 에이전트들이 *서로의 발견 위에 쌓아 올리는* 협업 리서치. 단일 실패점(SPOF)이 없어야 하는 시스템
- **예시**: 리서치 종합 — 문헌·산업 리포트·특허·뉴스를 조사하는 에이전트들이 각자 발견을 공유 저장소에 기여하고, 다른 에이전트가 즉시 보고 조사 방향을 조정
- **강점**: 탈중앙. 코디네이터라는 실패점 제거. 발견이 협업자 사이에 **실시간으로 흐름**
- **약점**: 명시적 조율 없으면 중복 작업. 모순된 접근. **반응 루프**(에이전트끼리 무한히 반응). 그래서 *종료 조건*(시간 예산·수렴 임계값·지정 결정 에이전트)이 일급(first-class)으로 필요

---

## 선택 프레임워크 — 짝지어 비교하기

Anthropic이 제시한 결정 규칙을 표로 정리하면:

| 갈림길 | 이걸 골라라 | 조건 |
|---|---|---|
| Orchestrator-Subagent ↔ Agent Teams | **Orchestrator** | 짧고 초점 있는 하위작업, 명확한 출력 |
| | **Agent Teams** | 여러 단계에 걸친 지속 컨텍스트 축적이 이득일 때 |
| Orchestrator-Subagent ↔ Message Bus | **Orchestrator** | 사전에 정해진 시퀀스 |
| | **Message Bus** | 워크플로가 이벤트에서 창발하고 발견에 따라 달라질 때 |
| Agent Teams ↔ Shared-State | **Agent Teams** | 상호작용 없는 분리된 파티션 |
| | **Shared-State** | 실시간 발견 흐름이 있는 협업 |
| Message Bus ↔ Shared-State | **Message Bus** | 이산적 이벤트 파이프라인 |
| | **Shared-State** | 에이전트가 반복 회귀하는 누적 지식 베이스 |

## 어디서 시작하나 — 오케스트레이터부터

Anthropic의 명확한 권고: **"대부분의 경우 orchestrator-subagent로 시작하라. 가장 적은 조율 오버헤드로 가장 넓은 범위의 문제를 다룬다."** 그리고 실패 지점을 관찰한 뒤, 구체적 필요가 분명해지면 다른 패턴으로 진화시킨다.

이 "가장 단순한 것부터, 필요할 때 진화"는 [Anthropic의 Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents)의 대원칙("find the simplest solution possible")과, [멀티에이전트 설계 원칙 1번](/2026/07/23/multi-agent-system-design-principles/)("single agent로 되는 일은 single agent로")과 정확히 같은 정신이다. 패턴은 사다리이지 뷔페가 아니다 — 아래에서 위로 올라가되, 올라갈 이유가 생겼을 때만.

---

## 한 줄 결론

조율 패턴 선택의 올바른 질문은 "무엇이 가장 정교한가"가 아니라 **"내 문제의 컨텍스트 경계와 정보 흐름은 어떤 모양인가"**다. Generator-Verifier로 품질을 게이팅하고, Orchestrator로 시작해 필요에 따라 Agent Teams·Message Bus·Shared-State로 진화하라. 그리고 어떤 패턴을 쓰든 — 특히 Shared-State라면 — **종료 조건을 일급으로** 설계하라. 무한 루프는 멀티에이전트의 고질병이다.

---

## 출처

- 원문(첨부): Anthropic/Claude, **Multi-Agent Coordination Patterns** (공식 블로그) — 5개 패턴 정의·트레이드오프·선택 프레임워크·시작 권고: <https://claude.com/blog/multi-agent-coordination-patterns>
- 관련(공식): Anthropic, **Building Effective Agents** — "가장 단순한 해법부터": <https://www.anthropic.com/engineering/building-effective-agents>
- 관련 본인 정리글: [멀티에이전트 설계 원칙 13가지](/2026/07/23/multi-agent-system-design-principles/) · [Explorer/Implementer/Verifier 역할 분리](/2026/07/23/agent-roles-explorer-implementer-verifier/) · [Ouroboros 3부작](/2026/07/23/ouroboros-manual-agentic-coding-code-analysis/)

> 참고: 본문의 패턴 정의·트레이드오프·선택 규칙은 Anthropic 공식 게시물의 내용을 충실히 옮긴 것이며, 각 패턴의 예시·명칭은 원문 기준이다.
