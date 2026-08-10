---
layout: post
title: "바이브 코딩의 다음 경계: Claude·Codex·MCP가 코드를 0으로 만들 때 누가 아키텍처를 결정하는가"
date: 2026-08-10 18:20:00 +0900
categories: [ai-agent, software-engineering, architecture]
tags: [바이브코딩, Claude Code, Codex, MCP, 인프런, 아키텍처, 경계설정, 엣지케이스]
---

바이브 코딩은 “자연어로 원하는 기능을 설명하면 Agent가 코드를 작성한다”는 경험에서 출발했다. 하지만 실제 시스템을 운영해보면 어려운 지점은 코드의 양이 아니다.

```text
어디까지가 책임 범위인가?
무엇을 허용하지 않아야 하는가?
실패·재시도·중복·부분 성공은 어떻게 처리하는가?
이 선택이 다른 시스템과 어떤 계약을 만드는가?
```

초기 바이브 코딩은 구현 속도를 높였지만, 복잡한 도메인에서는 경계와 엣지케이스를 놓치기 쉬웠다. Claude Code와 Codex는 이 문제를 단순 코드 생성에서 Agent Loop·검증·Harness·Skills·Evals의 문제로 확장했고, MCP는 Agent가 외부 지식과 도구를 직접 사용할 수 있는 연결 계층을 만들었다.[1][2][3]

최근에는 인프런이 강의 콘텐츠를 MCP Connector로 검색하고 코드 리뷰·설계 검토에 활용하는 방향까지 제시하고 있다.[4] 이제 질문은 “코드를 얼마나 빨리 생성하는가?”를 넘어선다.

> **코드가 0에 가까워지는 시대에, 아키텍처의 판단은 누구의 것이 되는가?**

## 1. 바이브 코딩의 첫 단계: 코드 작성 비용을 낮추다

초기 바이브 코딩의 생산성은 반복적인 코드 작성 비용을 낮추는 데서 나왔다.

```text
요구사항 설명
→ CRUD·DTO·Controller·Repository 생성
→ 실행
→ 오류 메시지 전달
→ 수정
```

이 방식은 다음 작업에서 특히 효과적이다.

```text
보일러플레이트
단순 API
화면 골격
테스트 fixture
반복 변환 코드
문서 초안
```

하지만 코드가 생성된다는 사실과 시스템이 올바르게 설계됐다는 사실은 다르다.

```text
코드 생성:
  빠르게 가능

경계 결정:
  도메인·조직·운영 맥락 필요

엣지케이스 결정:
  실패 비용과 업무 규칙 필요
```

컴파일 성공은 품질의 일부일 뿐이다. 특히 주문·결제·정산·권한·개인정보·분산시스템에서는 “정상 경로가 동작한다”는 사실만으로 충분하지 않다.

## 2. 한계의 핵심은 코드가 아니라 경계다

바이브 코딩에서 가장 자주 발생하는 문제는 Agent가 기능을 못 만드는 것이 아니라, 기능의 경계를 임의로 정하는 것이다.

### 경계가 필요한 질문

```text
누가 이 데이터의 소유자인가?
어떤 서비스가 상태를 변경하는가?
트랜잭션의 범위는 어디까지인가?
외부 API 실패를 누가 재시도하는가?
이벤트는 사실인가 명령인가?
동기 응답과 비동기 처리는 어디서 나누는가?
```

예를 들어 정산 시스템에서 “정산 완료 API를 만들어줘”라는 요청은 다음을 포함하지 않는다.

```text
중복 요청
부분 실패
환불 이후 재정산
지급 실패
대사 불일치
금액 반올림
동시 상태 변경
```

Agent가 이 질문에 답하지 않고 코드를 먼저 만들면, 시스템 경계가 코드 안에 암묵적으로 굳어진다.

## 3. 엣지케이스는 예외 목록이 아니라 계약이다

엣지케이스를 단순한 예외 목록으로 취급하면 계속 누락된다. 더 좋은 방법은 시스템 계약으로 표현하는 것이다.

```text
정상 상태:
  REQUESTED → PROCESSING → DONE

실패 상태:
  PROCESSING → FAILED

재시도:
  같은 event_id는 한 번만 반영

취소:
  DONE 이후 임의 취소 금지

대사:
  내부 금액과 외부 지급 결과가 다르면 자동 완료 금지
```

이를 코드·테스트·데이터베이스 제약으로 옮기면 Agent가 자연어를 잊어도 시스템이 위반을 드러낼 수 있다.

```text
자연어 원칙
→ 상태 전이 테스트
→ UNIQUE constraint
→ ArchUnit rule
→ schema validation
→ integration test
```

좋은 Agent 환경은 모든 규칙을 프롬프트에 넣는 환경이 아니라, 중요한 규칙을 실행 가능한 검증으로 바꾼 환경이다.

## 4. Claude 중심의 진화: 대화형 생성에서 작업 시스템으로

Claude Code 계열의 변화는 단순한 코드 생성보다 Agent가 저장소를 읽고, 명령을 실행하고, 테스트 결과를 보고, 다시 수정하는 작업 루프를 강화한 데 있다. Claude Code는 공식 문서에서 Subagent·Skills·Hooks·MCP 같은 확장 지점을 제공한다.[1]

개념적으로 흐름은 다음과 같다.

```text
사용자 목표
→ 저장소 탐색
→ 변경 계획
→ 코드 수정
→ 테스트·도구 실행
→ 실패 분석
→ 추가 수정
→ 결과 보고
```

이 방식의 장점은 사람이 매번 “테스트해”, “로그를 봐”, “실패 원인을 확인해”라고 지시하지 않아도 된다는 점이다.

하지만 Inner Loop만으로는 Self-Improving Loop가 아니다.

```text
Inner Loop:
  현재 작업을 통과시킴

Outer Loop:
  다음 작업의 문서·규칙·테스트·Skill·Tool을 개선
```

현재 코드만 고치고 다음 작업에서도 같은 실수를 반복한다면, Agent가 개선된 것이 아니라 한 번의 결과만 수정된 것이다.

## 5. Codex 중심의 진화: 지침과 Evals를 Harness로 묶다

Codex 계열의 Agentic Coding은 저장소 지침, Skills, 실행 trace, 평가를 결합하는 방향으로 발전했다. `AGENTS.md`는 Agent가 프로젝트의 구조와 작업 규칙을 찾는 예측 가능한 진입점으로 사용된다.[5]

OpenAI는 Agent Skill의 개선 여부를 평가하기 위해 출력뿐 아니라 Agent가 어떤 단계를 거쳤는지와 실행 결과를 함께 보는 Evals를 설명한다.[6]

이 관점에서 Skill은 단순 프롬프트 파일이 아니다.

```text
Skill
+ 입력·출력 계약
+ 사용 도구
+ 검증 명령
+ 실패 조건
+ 평가 사례
```

가 되어야 한다.

예를 들어 “Spring 기능을 구현하라”는 Skill보다 다음이 강하다.

```text
1. 기존 패키지 경계를 확인한다
2. Controller가 Repository를 직접 의존하지 않는지 검사한다
3. 상태 전이 테스트를 추가한다
4. ./scripts/verify.sh를 실행한다
5. 실패가 있으면 원인과 미확인 범위를 보고한다
```

다만 이 절차도 강제 규칙은 아니다. 가능하면 ArchUnit·테스트·정적 분석·CI로 승격해야 한다.

## 6. MCP: Agent를 지식과 실행의 네트워크에 연결하다

MCP(Model Context Protocol)는 AI 애플리케이션이 외부 시스템의 데이터·도구·workflow에 연결되도록 하는 공개 표준이다.[2][3]

MCP의 역할을 단순화하면 다음과 같다.

```text
Agent
  ↓
MCP Client
  ↓
MCP Server
  ├─ 문서·강의·코드 검색
  ├─ 파일·DB 조회
  ├─ 외부 API 호출
  ├─ 전문 도구 실행
  └─ workflow 제공
```

MCP는 “모델이 더 많이 안다”를 보장하지 않는다. 대신 모델이 필요한 순간 외부 지식과 작업 도구에 접근할 수 있게 한다.

이 차이는 중요하다.

```text
지식 내장:
  모델의 사전학습·프롬프트에 의존

MCP 연결:
  실행 시점의 외부 자료·도구에 의존
```

그러나 MCP 도구의 설명이 잘못됐거나, 권한이 과하거나, 반환 자료가 오래됐거나, 출처가 불명확하면 Agent의 오류도 더 빠르게 실행될 수 있다.

## 7. 인프런 MCP가 만드는 다음 단계

인프런은 MCP Connector를 등록하면 강의 내용을 검색하고, 실무에서 코드 리뷰·설계 검토를 강의 지식 위에서 받을 수 있는 방향을 소개한다.[4]

이 구조는 학습과 구현 사이의 거리를 줄인다.

```text
강의 개념
→ Agent가 검색
→ 현재 코드에 적용 제안
→ 코드 리뷰·설계 검토
→ 수정안 생성
```

이전에는 개발자가 강의를 보고 다음을 직접 수행해야 했다.

```text
개념 이해
→ 프로젝트 구조에 매핑
→ 코드 작성
→ 오류 수정
→ 설계 검토
```

이제 Agent가 강의 내용과 소스코드를 동시에 볼 수 있다. 특히 다음 영역에서 유용할 수 있다.

```text
Spring·JPA 패턴
테스트 전략
객체지향 설계
동시성·트랜잭션
Kafka·메시징
클린 아키텍처
```

하지만 “유명 강사의 강의를 참조했다”는 사실은 “현재 시스템에 올바른 설계를 선택했다”는 증거가 아니다.

## 8. 코드가 0에 수렴하는 현상

MCP와 Agent의 결합이 발전하면 사람의 직접 작성 코드는 줄어든다.

```text
사람:
  목표·제약·승인·판단

Agent:
  검색·설계 후보·코드·테스트·문서

MCP:
  외부 지식·도구·실행 연결

Evaluator:
  기준·검증·회귀 테스트
```

이론적으로는 애플리케이션 코드가 0에 가까워질 수 있다. 하지만 정확히는 **사람이 손으로 작성하는 코드의 양**이 줄어드는 것이다.

대신 다른 코드와 계약이 늘어난다.

```text
도구 호출 schema
권한 정책
MCP adapter
검증 script
architecture rule
schema·event contract
CI·eval harness
observability
```

코드가 사라지는 것이 아니라 코드의 위치가 이동한다.

```text
직접 작성하는 business code ↓
Agent와 연결하는 harness code ↑
검증·정책·관측 코드 ↑
```

따라서 “코드 0”은 개발자의 소멸이 아니라 **추상화 책임의 이동**으로 보는 편이 정확하다.

## 9. 아키텍처가 유명 강의에 의존할 때의 위험

강의는 좋은 출발점이 될 수 있지만, 특정 강사의 관점이 곧 프로젝트의 아키텍처 계약이 되어서는 안 된다.

### 위험 1. 맥락의 손실

강의의 예제는 특정 규모·팀·도메인·운영 가정을 가진다.

```text
강의 예제:
  단일 애플리케이션
  명확한 도메인
  통제된 데이터
  제한된 실패 시나리오

현실 시스템:
  레거시·외부 연동·조직 경계
  부분 실패·권한·규제
  데이터 마이그레이션
```

예제의 패턴을 그대로 복사하면 도메인과 운영 조건이 빠진다.

### 위험 2. 권위 편향

“유명 강사가 그렇게 말했다”는 설계 근거가 아니다. 설계는 다음 질문에 답해야 한다.

```text
우리 도메인의 변하는 축은 무엇인가?
우리의 트랜잭션 경계는 어디인가?
실패 시 복구 방식은 무엇인가?
운영자가 어떤 Trace를 볼 수 있는가?
이 구조의 비용은 무엇인가?
```

### 위험 3. 정답 패턴의 과잉 적용

모든 시스템에 다음을 적용하면 오히려 복잡도가 커질 수 있다.

```text
무조건 MSA
무조건 DDD
무조건 이벤트 기반
무조건 Hexagonal
무조건 CQRS
무조건 Kafka
```

패턴은 문제의 답이지, 아키텍처 정체성이 아니다.

### 위험 4. 기술부채의 출처 은폐

Agent가 강의의 설계를 적용했는데 장애가 발생하면 책임 경계가 흐려진다.

```text
누가 선택했는가?
어떤 대안을 검토했는가?
어떤 가정을 했는가?
어떤 검증을 통과했는가?
```

이 기록이 없으면 팀은 강사의 권위와 Agent의 출력 사이에서 원인을 추적하기 어렵다.

## 10. 강의 MCP를 안전하게 사용하는 법

인프런 MCP 같은 교육 지식 MCP는 다음 계층으로 사용해야 한다.

```text
1. Retrieval:
   관련 강의·개념 검색

2. Interpretation:
   현재 도메인과 차이점 분석

3. Proposal:
   여러 설계 후보 제시

4. Verification:
   테스트·정적 분석·운영 조건 확인

5. Decision:
   팀·사용자가 최종 선택
```

Agent가 강의 내용을 곧바로 소스에 적용하게 하기보다 다음 출력 형식을 요구하는 편이 낫다.

```text
강의 주장:
  원문·강의 단위·출처

적용 가정:
  현재 프로젝트에서 성립하는 조건

차이점:
  강의 예제와 현재 시스템의 차이

후보 A/B:
  장점·단점·운영비용

검증 계획:
  테스트·Trace·성능·보안

결정:
  승인 전 제안 상태
```

이렇게 해야 교육 콘텐츠가 설계 결정의 **근거 자료**가 되지, 설계 자체가 되지 않는다.

## 11. Claude·Codex·MCP 조합의 역할 분리

현재 Agentic Coding의 성숙한 형태는 하나의 Agent에게 모든 판단을 맡기는 것이 아니다.

```text
Claude:
  저장소 탐색·대화형 구현·문맥 연결

Codex:
  계획·코드 수정·전문 리뷰·Evals

MCP:
  외부 지식·문서·도구 연결

Deterministic tools:
  compile·test·lint·schema·security 검사

Human:
  경계·위험·비즈니스 책임·최종 승인
```

실제 도입에서 중요한 것은 “어떤 모델이 더 똑똑한가”보다 **역할과 권한의 분리**다.

```text
Read-only knowledge MCP
≠
Write-capable production MCP

교육 콘텐츠 검색
≠
자동 아키텍처 승인

코드 생성 성공
≠
업무 성공
```

## 12. 코드 0 시대에 개발자가 해야 하는 일

개발자의 역할은 사라지기보다 상위 경계로 이동한다.

### 문제 경계 설정

```text
무엇을 만들지
무엇을 만들지 않을지
누가 책임질지
```

### 계약 설계

```text
API
Event
Schema
State transition
Permission
Error semantics
```

### 엣지케이스 선택

```text
중복
재시도
부분 실패
동시성
타임아웃
취소
재처리
대사
```

### 평가 설계

```text
무엇을 통과로 볼지
어떤 Evidence가 필요한지
어떤 실패를 차단할지
```

### 아키텍처 책임

```text
강의의 패턴을 선택적으로 적용
대안과 비용을 비교
운영·조직·데이터 현실 반영
결정과 가정을 기록
```

즉 개발자는 타이핑을 덜 할 수 있지만, 판단을 덜 할 수는 없다.

## 13. 고찰: 아키텍처의 외주화인가, 판단의 민주화인가

MCP를 통한 교육 콘텐츠와 Agent의 결합은 두 가지 방향으로 갈 수 있다.

### 긍정적 방향: 지식 접근의 민주화

```text
경험이 적은 개발자도 좋은 설명에 접근
필요한 순간에 관련 개념 검색
코드와 설계의 피드백 루프 단축
학습과 실무 적용의 간극 축소
```

이는 강사의 지식이 더 많은 개발자에게 전달되는 좋은 변화다.

### 위험한 방향: 판단의 외주화

```text
강사가 말한 구조니까 채택
Agent가 생성했으니까 신뢰
MCP가 연결됐으니까 검증 완료
테스트가 통과했으니까 아키텍처도 정답
```

이 흐름은 개발자의 판단 능력을 강화하지 않고, 권위와 도구에 판단을 위임한다.

### 진짜 문제

“코드가 0에 수렴한다”는 표현은 편리하지만, 다음 책임을 가린다.

```text
누가 경계를 정의했는가?
누가 실패 비용을 부담하는가?
누가 데이터 정합성을 보장하는가?
누가 운영 장애를 설명하는가?
누가 최종 결정을 승인했는가?
```

코드가 줄어들수록 이 질문은 더 중요해진다.

## 14. 권장 개발 루프

MCP와 강의 지식을 연결할 때는 다음 루프를 권장한다.

```text
Goal
 ↓
Domain boundary
 ↓
Relevant knowledge retrieval
 ↓
Candidate architecture A/B
 ↓
Failure·edge-case review
 ↓
Small implementation
 ↓
Deterministic verification
 ↓
Operational trace
 ↓
Human decision
 ↓
Promote to project rule
```

강의 콘텐츠는 `Relevant knowledge retrieval` 단계에 둔다. 최종 결정 직전에 반드시 현재 프로젝트의 데이터·운영·조직 조건을 통과시켜야 한다.

## 결론

바이브 코딩은 단순한 자연어 코드 생성에서 Claude·Codex 기반 Agent Loop, Skills·Hooks·Evals 중심의 Harness Engineering, MCP 기반 외부 지식·도구 연결로 진화하고 있다.

인프런 MCP처럼 강의 지식을 검색하고 코드 리뷰·설계 검토에 연결하는 흐름은 개발자의 학습과 구현을 빠르게 만들 수 있다. 그러나 여기서 아키텍처가 유명 강사의 강의와 Agent 출력에 자동으로 종속되면, 개발은 빨라져도 판단의 주체는 흐려진다.

```text
코드 감소
≠ 책임 감소

지식 연결
≠ 설계 검증

강의 인용
≠ 도메인 적합성

MCP 사용
≠ 승인된 변경
```

가장 바람직한 방향은 다음이다.

> **강의는 설계 후보를 제공하고, MCP는 지식과 도구를 연결하며, Claude와 Codex는 구현·검증을 반복하고, 개발자는 경계·엣지케이스·책임·최종 결정을 소유한다.**

코드가 0에 가까워질수록 개발자의 핵심 능력은 코드 타이핑이 아니라 **무엇을 코드로 만들지 결정하는 능력**이 된다.

## Sources

1. [Claude Code 공식 문서 — Subagents](https://code.claude.com/docs/en/sub-agents)
2. [Anthropic — Introducing the Model Context Protocol](https://www.anthropic.com/news/model-context-protocol)
3. [Model Context Protocol — Introduction](https://modelcontextprotocol.io/docs/2026-07-28/getting-started/intro)
4. [인프런 — MCP Connector와 강의 기반 코드 리뷰·설계 검토](https://www.inflearn.com/pages/mcp)
5. [AGENTS.md — Agent 프로젝트 지침](https://agents.md/)
6. [OpenAI Developers — Testing Agent Skills Systematically with Evals](https://developers.openai.com/blog/eval-skills)
7. [인프런 — 모두를 위한 MCP를 이용한 업무자동화](https://www.inflearn.com/course/%EB%AA%A8%EB%91%90%EB%A5%BC-%EC%9C%84%ED%95%9C-mcp%EB%A5%BC-%EC%9D%B4%EC%9A%A9%ED%95%9C-%EC%97%85%EB%AC%B4%EC%9E%90%EB%8F%99)

*인프런 MCP의 내부 구현·실제 정확도·사용자별 결과 품질은 공개된 소개만으로 확정하지 않았다. 이 글에서 확인된 사실과 아키텍처에 대한 해석·제안은 구분해서 서술했다.*

*공개 글에는 credential, token, private IP, 내부 endpoint를 포함하지 않았다.*

## Related posts

- [Agentic Coding의 Self-Improving Loop](https://myoungsoo7.github.io/2026/08/10/self-improving-loop-agentic-coding/)
- [Hidden Checklist와 자기개선 루프](https://myoungsoo7.github.io/2026/08/10/hidden-checklist-agent-loop/)
- [Agent Skill 생태계 지도](https://myoungsoo7.github.io/2026/08/10/agent-skills-inventory/)
- [Agent Script·Tool 지도](https://myoungsoo7.github.io/2026/08/10/agent-tools-built-on-mac/)
- [React·Vue·JSP와 AX 시대의 프론트엔드 선택](https://myoungsoo7.github.io/2026/08/09/react-vue-jsp-ax-comparison/)

*이 글은 외부 자료를 요약·재구성한 분석 글이며, 특정 강사·플랫폼·Agent 제품의 품질을 보증하거나 비판하는 평가가 아니다.*

---
