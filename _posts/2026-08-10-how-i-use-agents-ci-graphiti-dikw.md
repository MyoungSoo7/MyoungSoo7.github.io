---
layout: post
title: "나는 Agent를 어떻게 쓰는가: Strict CI·Graphiti·DIKW로 연결한 Agent 운영"
date: 2026-08-10 18:50:00 +0900
categories: [ai-agent, software-engineering, knowledge-management]
tags: [Agent, Claude, Codex, Hermes, CI, Regression, Graphiti, DIKW, Memory]
---

첨부된 그림은 “요즘 나는 Agent를 어떻게 쓰는가?”라는 질문에 대해 세 가지 축으로 답한다.

```text
Strict CI:
  회귀 테스트·문서화

Graphiti:
  관계형 지식 그래프

DIKW:
  Data → Information → Knowledge → Wisdom
```

![Agent 활용: Strict CI·Graphiti·DIKW](/assets/images/agent-usage-ci-graphiti-dikw.jpg)

이 글에서는 그림의 세 축을 현재 봇1~4와 Hermes·Claude·Codex·Ouroboros를 운영한 경험에 연결해 정리한다.

## 1. Agent를 “코드 생성기”가 아니라 CI의 검증자로 사용하기

가장 먼저 Agent를 적용하기 좋은 영역은 **Strict CI**다.

```text
코드 변경
→ 컴파일
→ 테스트
→ 정적 분석
→ 회귀 검증
→ 문서·diff 확인
→ 완료 판정
```

Agent에게 모든 판단을 맡기는 대신, CI가 결정적인 사실을 판정하고 Agent가 실패를 해석하도록 나누는 구조다.

### Regression

봇1~4 작업에서도 다음과 같은 회귀 검증이 핵심이었다.

```text
기존 테스트가 깨졌는가?
새 변경이 기존 계약을 훼손했는가?
운영 DB migration이 rollback 가능한가?
기존 API·이벤트·상태 전이가 유지되는가?
```

예를 들어 봇2의 KRX/market-service 작업에서는 migration을 실제 운영 스키마에 적용해 영향 범위를 확인한 뒤 rollback했고, 테스트 결과와 변경 범위를 분리해 보고했다. 운영 변경을 곧바로 확정하지 않고 검증 단계에서 멈춘 것이 중요한 지점이다.

### Documentation

Agent가 만든 코드보다 문서화가 더 중요한 경우도 있다.

```text
왜 이 구조를 선택했는가?
누가 이 데이터를 소유하는가?
실패하면 어떻게 재처리하는가?
어떤 권한이 필요한가?
검증은 어떤 명령으로 재현하는가?
```

봇1의 K-ICS 분석, 봇2의 KRX 결손 조사, 봇3·4의 P8/RAHAB 작업처럼 복잡한 작업은 코드만 남기면 다음 Agent가 같은 탐색을 반복한다. 결과·근거·미확인 범위·다음 조치를 문서화해야 작업 경험이 재사용된다.

## 2. 봇1~4를 CI의 역할별 실행자로 보기

현재 봇1~4는 모두 같은 일을 하는 복제 Agent가 아니다.

```text
봇1:
  금융·보험 규제·K-ICS 분석

봇2:
  Settlement·KRX·market-service·데이터 정합성

봇3:
  P8·RAHAB·Agent harness·MCP 조사

봇4:
  RAHAB·AC table·mutation·designer gate
```

역할을 나누면 다음과 같은 CI형 파이프라인을 만들 수 있다.

```text
봇1:
  규제·도메인 사실 검증

봇2:
  데이터·마이그레이션·통합 검증

봇3:
  구현·harness 개선

봇4:
  acceptance criteria·문서·gate 검증

Hermes:
  조정·정책·최종 보고
```

단, Agent가 실제로 어떤 commit을 만들었는지는 Git trace로 확인해야 한다. “봇3이 만들었다”와 “봇3 환경에서 사용된 파일”은 다른 주장이다.

## 3. Graphiti: Agent의 기억을 관계로 연결하기

그림의 가운데는 Graphiti와 지식 그래프다.

단순한 문서 목록은 다음 질문에 약하다.

```text
이 결정은 어떤 장애에서 나왔는가?
이 Skill은 어떤 실패를 예방하는가?
이 서비스는 어떤 API·DB·팀과 연결되는가?
이 규칙은 어떤 commit·테스트·Trace에 근거하는가?
```

그래프 구조는 다음 관계를 표현할 수 있다.

```text
[실패 Trace]
      ↓ 근거
[개선 Rule]
      ↓ 적용
[Skill/Tool]
      ↓ 검증
[Test/CI]
      ↓ 결과
[Commit/Artifact]
```

현재 운영에서 이미 유사한 관계를 다음과 같이 관리하고 있다.

```text
Agent Artifact Registry:
  owner·runtime·source·permission·verification

Wiki:
  원문·RCA·설계·결정

Memory:
  안정적인 사실·사용자 선호

Git:
  diff·commit·branch

Trace:
  실제 실행 결과
```

Graphiti 같은 그래프 도구를 추가하면 이 관계를 시간·주체·프로젝트·근거별로 탐색하는 방향으로 확장할 수 있다. 다만 그래프에 들어간 내용이 자동으로 사실이 되는 것은 아니다.

```text
Graph node 생성
≠ 사실 검증

관계 연결
≠ 인과관계 확정

Agent memory 저장
≠ 신뢰할 수 있는 지식
```

## 4. DIKW: Agent 경험을 지식으로 승격하는 단계

그림 오른쪽의 DIKW는 Agent 운영 데이터를 어떻게 지식으로 바꾸는지 설명하는 모델로 활용할 수 있다.

### Data

가공되지 않은 실행 기록이다.

```text
명령어
로그
테스트 출력
Git diff
commit SHA
API 응답
Pod 상태
사용자 정정
```

### Information

Data에 시간·대상·맥락을 붙인 상태다.

```text
8월 7일 거래일에 KRX 수집 건수 0
봇2가 migration dry-run 후 rollback
봇3의 P10·P11 commit 확인
봇4의 RAHAB AC table 검토
```

### Knowledge

반복해서 활용할 수 있는 규칙으로 정리된 상태다.

```text
실패 카운터 0만으로 업무 성공 판정 금지
현재 로그와 만성 로그를 구분
운영 DB migration은 승인 전 rollback 검증
작업자와 artifact 최초 작성자를 구분
```

### Wisdom

상황에 맞는 판단과 우선순위 선택이다.

```text
KRX 결손은 API 실패 카운터보다 거래일 기대건수 우선
zeude는 장애가 아니라 미사용 stale reference 정리 후보
API endpoint rc=7은 클러스터 장애가 아니라 관측 지점 문제일 수 있음
봇 재시작보다 작업 문맥 보존이 중요하면 clear와 restart를 분리
```

DIKW의 핵심은 위로 올라갈수록 자동 요약이 아니라 **검증·맥락·판단**이 필요하다는 점이다.

## 5. Hermes·Claude·Codex·Ouroboros의 연결

현재 Agent 운영 구조를 그림의 세 축에 배치하면 다음과 같다.

```text
Strict CI:
  테스트·lint·ArchUnit·migration dry-run·Pages 검증

Graphiti/Wiki:
  Agent artifact·RCA·결정·문서 관계

DIKW:
  Trace → 맥락 → 규칙 → 운영 판단
```

각 도구의 역할도 분리한다.

```text
Hermes:
  cron·조정·메모리·보고

Claude bots:
  프로젝트별 탐색·구현·검토

Codex:
  전문 리뷰·hook·평가·workflow

Ouroboros:
  run·evaluate·evolve·checkpoint·receipt
```

이 구조에서 중요한 것은 Agent가 많다는 사실이 아니라, **결과가 다음 계층으로 어떻게 승격되는가**다.

```text
실행 결과
→ 검증된 artifact
→ 문서·관계
→ 재사용 규칙
→ 다음 작업의 guardrail
```

## 6. Agent 활용의 안전한 승격 규칙

모든 관찰을 바로 Memory·Wiki·Skill에 넣으면 오염된다.

```text
Trace:
  사실의 원본

Candidate:
  아직 검증되지 않은 관찰

Validated:
  테스트·원문·반복 관찰로 확인

Promoted:
  Rule·Skill·Tool·문서로 승격

Retired:
  오래되거나 반증된 지식
```

예를 들어 다음은 바로 영구 규칙이 되면 안 된다.

```text
한 번의 API 실패
→ “항상 endpoint가 죽었다”

한 번의 Agent 실수
→ “모델은 이 구조를 이해하지 못한다”

한 번의 테스트 통과
→ “운영도 안전하다”
```

검증과 시간창이 필요하다.

## 7. “Agent를 어떻게 쓰는가?”에 대한 현재 답

현재의 답은 다음과 같다.

```text
Agent에게 코드를 대신 쓰게 한다:
  일부만 해당

Agent에게 반복 검증을 맡긴다:
  Strict CI

Agent의 실패와 결정을 연결한다:
  Graphiti/Wiki/Artifact Registry

실행 기록을 운영 판단으로 승격한다:
  DIKW
```

가장 가치 있는 Agent는 가장 많은 코드를 생성하는 Agent가 아니다.

```text
실패를 재현하고
근거를 남기고
다음 작업의 비용을 줄이고
위험한 변경을 멈추는 Agent
```

## 결론

첨부된 그림의 세 단어는 Agent 운영의 방향을 간단하게 요약한다.

```text
Strict CI:
  결과를 검증한다

Graphiti:
  결과와 지식을 연결한다

DIKW:
  데이터를 판단 가능한 지식으로 승격한다
```

봇1~4를 활용한 현재 운영에서도 핵심은 Agent의 숫자나 모델명이 아니다.

```text
봇1~4:
  역할별 실행자

Hermes:
  중앙 조정자

Claude·Codex:
  구현·리뷰·오케스트레이션

Ouroboros:
  실행·평가·진화

CI·Trace·Wiki·Memory:
  검증과 지식 승격 계층
```

> **Agent를 잘 쓰는 방법은 Agent에게 일을 많이 시키는 것이 아니라, Agent의 실행이 검증된 정보·재사용 가능한 지식·더 나은 다음 작업으로 이어지게 만드는 것이다.**

## Sources

- [Graphiti — GitHub](https://github.com/getzep/graphiti)
- [Graphiti — Documentation](https://help.getzep.com/graphiti)
- [DIKW pyramid — Wikipedia](https://en.wikipedia.org/wiki/DIKW_pyramid)
- [Claude Code — Subagents](https://docs.anthropic.com/en/docs/claude-code/sub-agents)
- [Claude Code — Hooks](https://docs.anthropic.com/en/docs/claude-code/hooks-guide)
- [Model Context Protocol](https://modelcontextprotocol.io/docs/2026-07-28/getting-started/intro)

*첨부 이미지는 사용자가 제공한 그림이며, 이미지의 구조를 현재 Hermes·Claude 봇1~4·Codex·Ouroboros 운영 경험에 연결해 재구성했다.*

*봇별 역할·작업 결과는 확인된 세션·파일·Git·실행 Trace 범위에서만 서술했으며, 최초 작성자 provenance가 없는 artifact의 저자를 임의로 단정하지 않았다.*

*공개 글에는 credential·token·private IP·내부 endpoint를 포함하지 않았다.*

## Related posts

- [Agentic Coding의 Self-Improving Loop](https://myoungsoo7.github.io/2026/08/10/self-improving-loop-agentic-coding/)
- [Claude의 Dynamic Workflow](https://myoungsoo7.github.io/2026/08/10/claude-dynamic-workflows/)
- [Agent Skill 생태계 지도](https://myoungsoo7.github.io/2026/08/10/agent-skills-inventory/)
- [Agent Script·Tool 지도](https://myoungsoo7.github.io/2026/08/10/agent-tools-built-on-mac/)
- [Hidden Checklist와 자기개선 루프](https://myoungsoo7.github.io/2026/08/10/hidden-checklist-agent-loop/)

---

*2026-08-10 작성*

---

## Appendix: Agent knowledge promotion checklist

```text
[ ] 실행 Trace가 있는가?
[ ] 시간·대상·실행 주체가 기록됐는가?
[ ] 사실과 추론이 분리됐는가?
[ ] 회귀 테스트나 결정적 검증이 있는가?
[ ] 기존 Knowledge와 충돌하지 않는가?
[ ] owner·source·last_verified가 있는가?
[ ] 오래되면 폐기할 조건이 있는가?
```

