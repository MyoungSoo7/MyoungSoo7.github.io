---
layout: post
title: "*Multi-Agent 의 *깊이* — *마스터 ↔ 워커 / 조정 패턴 / 충돌 처리*"
date: 2026-06-15 16:05:00 +0900
categories: [backend, ai, agent]
tags: [multi-agent, agent, llm, orchestration, distributed, ai-architecture, ai]
---

> *Single Agent 가 *모든 걸 *처리 하려 하면* — *답 의 *깊이 ↓ + 비용 ↑ + 컨텍스트 부족*.
> *2026 년 의 *AI 시스템 의 *주류 = *Multi-Agent*. *여러 *전문 *Agent 가 *협업* 해서 *복잡 한 *작업* 을 *분담*.
> 그러나 *Agent 도 *분산 시스템* — *조정, *통신, *충돌, *비용* 의 *4 차원 *고민* 이 *필수*.
> 이 글은 *Multi-Agent 의 *진짜 *깊이*.

---

## TL;DR

| 영역 | 핵심 |
|------|------|
| **왜** | Single Agent 의 *컨텍스트 / 깊이 / 전문성* 한계 |
| **토폴로지** | Master-Worker / Pipeline / Peer (수평) |
| **조정** | Orchestrator-Worker / Hierarchical / Decentralized |
| **통신** | Message / Shared State / Event Bus |
| **충돌** | Voting / 합의 / Tie-breaker / Re-planning |
| **비용** | *토큰 N 배 + Latency 조심* |
| **2026** | LangGraph / CrewAI / AutoGen / Claude Computer Use 등 *표준화 중* |

핵심 한 줄 :

> *Multi-Agent 는 *마이크로 서비스 의 *AI 버전*. *서비스 분리 의 *모든 *원칙 이 *적용*. *분산 시스템 의 *학습 이 *그대로 *재 활용*.*

---

## 1. **Single Agent 의 *한계*

### *컨텍스트 *부담*

- 함수 50 개 + 시스템 프롬프트 + 사용자 컨텍스트
- *모두 1 회 호출 의 *입력* 으로 들어감
- *비용 ↑ + LLM 의 *판단 정확도 ↓*

### *전문성 *부족*

- *코드 분석 + 보안 검토 + 디자인 + 테스트* — *한 모델 의 *모든 *영역 *전문화 불가*
- *별 도 *프롬프트 / 모델 / 도구* 가 *효율 적*

### *깊이 *제한*

- *복잡 한 작업 의 *단일 LLM 의 *추론 깊이 부족*
- *Plan-and-Execute 의 *Plan 자체 가 *오차*

### *비용 / 시간*

- *복잡 한 단일 호출 → *수십 초 + 수만 토큰*
- *분리 하면 *병렬화 가능*

→ *이 4 한계 가 *Multi-Agent 의 *진짜 *동기*.

---

## 2. **Multi-Agent 의 *3 토폴로지*

### *2.1. Master-Worker*

```
        Master Agent
       (전체 조정)
            │
    ┌───────┼───────┐
   워커 A  워커 B  워커 C
  (검색)  (분석)  (생성)
```

- *마스터* 가 *작업 분할 + 통합*
- *워커* 가 *특화 작업 *수행*
- *대표 패턴* : LangGraph, CrewAI 의 *기본 구조*

### *2.2. Pipeline*

```
Agent A → Agent B → Agent C → 결과
(요약)   (번역)    (검증)
```

- *순차 적 *변환*
- *각 Agent 가 *이전 결과 받아 *처리*
- *대표 패턴* : 데이터 파이프라인 + LLM

### *2.3. Peer*

```
Agent A ↔ Agent B
   ↕         ↕
Agent C ↔ Agent D
```

- *대등 한 Agent 들 의 *서로 *통신*
- *합의 + 토론 + 검증*
- *대표 패턴* : Debate, Voting, Constitutional AI

---

## 3. **조정 패턴*

### *3.1. Orchestrator-Worker*

```java
@Service
public class OrchestratorAgent {
    @Autowired ChatClient orchestrator;
    @Autowired List<WorkerAgent> workers;
    
    public Response process(Request req) {
        // 1. 작업 분할
        TaskPlan plan = orchestrator.plan(req);
        
        // 2. 워커 별 *위임*
        List<TaskResult> results = plan.tasks().stream()
            .map(task -> selectWorker(task).execute(task))
            .toList();
        
        // 3. 통합
        return orchestrator.synthesize(results);
    }
}
```

장점 :
- *명확 한 *책임 분리*
- *추적 + 디버깅 쉬움*
- *워커 *독립 적 *교체 가능*

단점 :
- *마스터 가 *병목*
- *복잡 한 *plan 의 *오차*

### *3.2. Hierarchical*

```
Master
  ├─ Manager 1
  │   ├─ Worker 1.1
  │   └─ Worker 1.2
  └─ Manager 2
      ├─ Worker 2.1
      └─ Worker 2.2
```

- *대규모 *작업* 의 *조직 화*
- *각 매니저 가 *부분 책임*
- *대규모 기업 운영* 의 *직접 *비유*

### *3.3. Decentralized*

```
Agent 들 이 *서로 *직접 통신*
중앙 *조정 없음*
*Consensus / Voting* 으로 *결정*
```

- *Single Point of Failure 없음*
- *복잡한 *합의 알고리즘 필요*
- *분산 시스템 의 *진짜 *학습 적용*

### *3.4. 패턴 *선택*

```
단순 작업           → Orchestrator-Worker
복잡 + 대규모       → Hierarchical
검증 / 합의 중요    → Decentralized + Voting
```

---

## 4. **통신 패턴*

### *4.1. Direct Message*

```java
agentA.sendTo(agentB, message);
```

- *간단*
- *순서 보장*
- *N x N 통신 시 *복잡*

### *4.2. Shared State*

```java
SharedContext context = new SharedContext();
agentA.write(context, "step1", result1);
agentB.read(context, "step1");
```

- *상태 의 *명시 적 공유*
- *동시성 + 락 *문제* 발생
- *Redis / DB 활용 가능*

### *4.3. Event Bus*

```java
@EventListener
public void onTaskCompleted(TaskCompletedEvent e) {
    // *비동기 처리*
}
```

- *느슨한 결합*
- *Pub/Sub 패턴*
- *확장 성 + 모니터링 쉬움*

### *4.4. Spring AI 의 *통합*

```java
@Bean
ApplicationEventPublisher agentEventBus() { ... }

// Agent 간 *통신 = ApplicationEvent*
@Component
public class AgentA {
    @Autowired ApplicationEventPublisher publisher;
    
    public void process() {
        Result r = doWork();
        publisher.publishEvent(new AgentMessage("A", "B", r));
    }
}

@Component
public class AgentB {
    @EventListener
    public void onMessage(AgentMessage msg) {
        if ("B".equals(msg.target())) {
            handle(msg);
        }
    }
}
```

→ *Spring 의 *Event 시스템 활용* = *Agent 통신 의 *교과서*.

---

## 5. **충돌 처리** — *Multi-Agent 의 *진짜 어려움*

### *5.1. 의견 *불일치*

```
Agent A : 답 X 가 *맞다*
Agent B : 답 Y 가 *맞다*
→ *Tie-breaker* 필요
```

해결 :

1. ***Voting*** — *N 개 Agent 가 *투표*, *과반수 결정*
2. ***신뢰 도 가중*** — *각 Agent 의 *과거 정확도 *반영*
3. ***Master 의 *최종 결정***
4. ***재 분석*** — *결과 *다르면 *추가 컨텍스트 제공* + 재 호출

### *5.2. *중복 작업*

```
Agent A : *DB 갱신 중*
Agent B : *동시에 *같은 DB 갱신 시도*
→ 데이터 부정합 위험
```

해결 — *분산 락 / 멱등성 / 트랜잭션*.

### *5.3. *Race Condition*

```
Agent A : 데이터 *읽기 → 처리 → 쓰기*
Agent B : *그 사이 *다른 값 쓰기*
→ Agent A 의 *쓰기 가 *덮어 씀*
```

해결 — *Optimistic Lock / 버전 관리 / Event Sourcing*.

### *5.4. *Deadlock*

```
Agent A : Lock X → 대기 Lock Y
Agent B : Lock Y → 대기 Lock X
→ 영원히 대기
```

해결 — *Lock 순서 통일 / Timeout / Try-lock*.

---

## 6. **비용** — *N 배 증가*

### *토큰 *폭발*

```
Single Agent 의 호출 1 회 = 토큰 X
Multi-Agent 의 작업 1 회 = 토큰 X × N (Agent 수)
                          + 통신 토큰
                          + 컨텍스트 공유 토큰
→ *수 배 ~ 수십 배 증가 가능*
```

### *Latency*

```
순차 = 합산
병렬 = 최대치
→ *병렬화 + 조정* 의 *균형*
```

### *비용 *최적화 *전략*

1. ***Cheap Model 활용*** — *Worker 에 *작은 모델*, *Master 에 *큰 모델*
2. ***Caching*** — *반복 답 *재 사용*
3. ***Tool selection*** — *불필요 한 함수 제거*
4. ***Early Exit*** — *조건 만족 시 *조기 종료*

---

## 7. **2026 의 *Multi-Agent *프레임 워크*

### *7.1. LangGraph (LangChain)*

```python
from langgraph.graph import StateGraph

graph = StateGraph(State)
graph.add_node("researcher", researcher_agent)
graph.add_node("writer", writer_agent)
graph.add_node("editor", editor_agent)

graph.add_edge("researcher", "writer")
graph.add_edge("writer", "editor")

app = graph.compile()
```

- *그래프 기반 *조정*
- *상태 공유 표준*
- *Python 기반*

### *7.2. CrewAI*

```python
from crewai import Agent, Task, Crew

researcher = Agent(role="Researcher", goal="...", tools=[...])
writer = Agent(role="Writer", goal="...", tools=[...])

task1 = Task(description="...", agent=researcher)
task2 = Task(description="...", agent=writer)

crew = Crew(agents=[researcher, writer], tasks=[task1, task2])
result = crew.kickoff()
```

- *역할 기반 *명시*
- *직관 적*

### *7.3. AutoGen (Microsoft)*

- Multi-Agent Conversation Framework
- *대화 기반 협업*
- *Code Execution 강함*

### *7.4. Spring AI 의 *방향*

- *2026 시점 — *공식 Multi-Agent 의 *명시 적 *지원 *진행 중*
- *현재 — Function Calling + Custom Orchestration*
- *Spring Integration / Spring Cloud 와 *통합 예상*

### *7.5. Claude Computer Use / Claude Code SDK*

- *Anthropic 의 *Multi-Agent 의 *현대 적 접근*
- *프로젝트 수준 의 *Sub-agent 호출*
- *Skills + Agent Orchestration*

---

## 8. **실 무 사례*

### *8.1. 코드 리뷰 시스템*

```
Master : 코드 PR 분석 요청
  ├─ Worker 보안 : OWASP 검토
  ├─ Worker 성능 : Big-O 분석
  ├─ Worker 스타일 : 코딩 표준 검토
  └─ Worker 테스트 : 테스트 커버리지

Master : 통합 리뷰
```

### *8.2. 데이터 분석 Pipeline*

```
Crawler → Cleaner → Analyzer → Visualizer → Reporter
  ↓          ↓          ↓           ↓            ↓
  RAG     중복 제거   통계 / ML   차트 생성    PDF 작성
```

### *8.3. 마케팅 캠페인 자동화*

```
Strategist : 캠페인 *기획*
  ├─ Copywriter : 텍스트 *생성*
  ├─ Designer   : 이미지 *생성*
  └─ Analyst    : *타깃 *분석*

Strategist : 통합 + A/B 테스트 *설계*
```

### *8.4. DevOps 자동화*

```
Monitor : 알람 감지
  ↓
Triage  : 우선 순위 + 근본 원인 *추정*
  ├─ LogAnalyzer : 로그 *분석*
  ├─ MetricsAnalyzer : 지표 *분석*
  └─ RecentChanges : 최근 변경 *추적*

Resolver : 해결 *제안* 또는 *자동 패치*
```

---

## 9. **흔한 함정**

### *9.1. 너무 *많은 *Agent*

> 7 Agent + 14 단계 → 비용 폭발 + 디버깅 지옥.

→ ***적정 *3~5 Agent* 가 *대부분 시스템에 *충분*.

### *9.2. 무한 루프*

```
A → B → C → A → B → C → ...
```

해결 — *최대 단계 수 제한 + Termination 조건*.

### *9.3. 무 의미한 *통신*

```
Agent A : *결과 *전송*
Agent B : *받기 만 *함* — 사용 안 함*
```

→ *각 Agent 의 *입출력 *필요성 *검증*.

### *9.4. *Shared State 의 *동시성*

```
2 Agent 가 *동시에 *같은 변수 *수정* → 부정합
```

→ *Lock / 트랜잭션 / Event Sourcing*.

### *9.5. *Master 의 *과부하*

> *모든 결정 이 *Master* 통과 → *Single Point of Failure + 병목*.

해결 — *Hierarchical 로 분할 + Worker 의 *자율 결정 확대*.

### *9.6. *통신 비용 *무시*

> Agent 간 *메시지 *크기 = *토큰 비용*. *서로 *모든 컨텍스트 *전송 = *비용 폭발*.

해결 — *Compression / Summarization / Reference 만 전달*.

### *9.7. *Observability 부재*

> *어느 Agent 가 *어느 결정* 했는지 *모름*. *디버깅 불가*.

해결 — *모든 Agent 호출 의 *Distributed Tracing*.

---

## 10. **권장 *Multi-Agent *설계 *6 단계*

### Step 1 — *Single Agent 부터*

```
*먼저 *Single Agent 로 *시도*. *한계 *확인 후 *분리* 결정*.
```

### Step 2 — *역할 *분리 *기준*

```
*도메인* / *전문성* / *책임* / *모델 크기* 별 *분리*
```

### Step 3 — *토폴로지 *선택*

```
*Master-Worker* (대부분), *Pipeline* (변환), *Peer* (합의)
```

### Step 4 — *통신 *패턴 결정*

```
*Spring Event* (이벤트), *Redis* (공유 상태), *직접 호출* (간단)
```

### Step 5 — *충돌 처리 + 종료 조건*

```
*Voting / Tie-breaker / Re-planning / Termination*
```

### Step 6 — *Observability + 비용 *모니터링*

```
*Distributed Tracing + Cost Tracking + Audit Log*
```

---

## 11. *내 *경험* — *Multi-Agent *적용 시작*

### *처음 시도 (2025 초)*

- *3 Agent + Master*
- *함수 *각자 분리*
- *통신 = Direct Method Call*
- *비용 : 단일 Agent 의 *5 배*

### *현재 (2026)*

- *5 Agent + Hierarchical*
- *통신 = ApplicationEvent + Redis*
- *Voting + Tie-breaker*
- *Distributed Tracing*
- *비용 : 단일 의 *2 배* (Cheap Model 활용)

### *얻은 *교훈*

1. ***시작 은 *간단 하게*** — Master-Worker 3 명.
2. ***통신 비용 무시 *치명적*** — 컨텍스트 압축.
3. ***Observability 가 *필수*** — *Jaeger / Tracing*.
4. ***Single Agent 로 *해결 가능 하면 *그렇게*** — *분리 의 *비용 *고려*.

---

## 12. *마치며*

> *Multi-Agent 는 *마이크로 서비스 의 *AI 버전*. *분산 시스템 의 *모든 원칙 의 *AI 적용*. *시작 은 *간단*, *성장 시 *Hierarchical*, *합의 필요 면 *Decentralized*.

3 줄 요약 :

1. ***토폴로지 3 종* — Master-Worker / Pipeline / Peer*** — *상황 별 *선택*.
2. ***통신 + 충돌 + 비용 의 *3 차원 *균형*** — *분산 시스템 의 *재 발견*.
3. ***Observability 없 으면 *Multi-Agent = *블랙 박스*** — *비용 폭발 + 디버깅 불가*.

7년차 회고 :

> *"Single Agent 만 으로 *모든 걸 *처리 하려 한 *시기 가 *비싸 고 *부정확 했다*. *Multi-Agent 로 *분리 한 *현재 — *각 Agent 의 *책임 명확 + 비용 ↓ + 정확도 ↑*. *분산 시스템 학습 의 *AI 적용 의 *진짜 가치*."*

다음 글 — *Multi-Agent 의 *Observability* — *Jaeger / OpenTelemetry / Cost Tracking 의 *실 무 적용*. 같은 시리즈 로 이어 집니다.

---

> 본 글은 *7년차 백엔드 / Multi-Agent 운영 회고*. *프레임 워크 의 *변화 속도 가 *매우 빠르므로* — *6 개월 후 *세부 가 *변할 수 있음*. *원리 + 설계 원칙* 에 *무게 중심* 을 두는 게 *오래 가는 지식*.
