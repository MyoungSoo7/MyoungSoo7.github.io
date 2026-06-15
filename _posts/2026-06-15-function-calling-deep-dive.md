---
layout: post
title: "*Function Calling 의 *깊이* — *Agent 패턴 / Tool 설계 / 보안 / 추적*"
date: 2026-06-15 15:35:00 +0900
categories: [backend, ai, agent]
tags: [function-calling, agent, llm, tool-use, react, security, observability, spring-ai]
---

> *LLM 이 *"날씨 모름"* 이라고 답하던 시대 는 끝났다.
> *Function Calling* — *LLM 이 *Java 함수 *직접 호출* 가능* — 이 *AI 시대 의 *Agent 의 *기본 *벽돌*.
> 그러나 *벽돌 한 장 만으로 *집* 이 되진 않는다. *Tool 설계 + 보안 + 추적* 의 *3 축* 이 함께 가야 *진짜 시스템*.
> 이 글은 *그 3 축 의 *실 무 깊이*.

---

## TL;DR

| 영역 | 핵심 |
|------|------|
| **동작 원리** | LLM 이 *질문 분석 → 적합 함수 *결정* → 함수 호출 → 결과 → 응답 *합성* |
| **Tool 설계** | *명확 한 *이름 + 설명*, *작은 책임*, *멱등성*, *실패 처리* |
| **Agent 패턴** | ReAct (Reason + Act) / Plan-and-Execute / Multi-Agent |
| **보안** | *입력 검증 + 권한 제한 + sandbox + audit* |
| **추적** | *함수 호출 *수 / 비용 / 오류 율* 의 *모니터링* |
| **2026 의 *상태*** | 안정화 진입 / 표준화 진행 |

핵심 한 줄 :

> *Function Calling 은 *AI 의 *손 *과 *발*. *손과 발 의 *권한 을 *잘못 주면 *시스템 의 *손실 *불가피*. *설계 의 *중요도 가 *코드 작성 보다 *높다*.*

---

## 1. **Function Calling 의 *기본 원리*

### *2023 년 *전 의 *문제*

> 사용자 : "*서울 의 *현재 *날씨 는?*"
> LLM    : "*지금 날씨 는 *알 수 없어요. *학습 시점 의 데이터 만 가지고 있습니다.*"

LLM 은 *외부 정보* 에 *접근 *불가*. *답 의 *시점 *고정*.

### *Function Calling 의 *발상*

> *"LLM 이 *답 모를 때 — *함수 호출 로 *답을 *얻게 *하자.*"*

```
1. 사용자 질문
2. LLM 이 *"이 질문 은 weatherFunction 호출 *필요*" 판단
3. LLM 이 *호출 *요청* + 인자 (city = "서울") 출력
4. Spring 이 *Java 의 *weatherFunction *실행*
5. 결과 (현재 25°C, 맑음) 를 LLM 에 *재 입력*
6. LLM 이 *자연어 응답* 작성
```

→ ***LLM 의 *지식 의 *한계 를 *외부 도구 로 *확장**.

---

## 2. **Spring AI 의 *Function Calling 구현*

### *함수 정의*

```java
@Configuration
public class FunctionConfig {
    
    @Bean
    @Description("Get current weather for a city")
    public Function<WeatherRequest, WeatherResponse> weatherFunction() {
        return req -> {
            // 외부 API 호출
            return weatherApi.fetchCurrent(req.city());
        };
    }
}

public record WeatherRequest(String city) {}
public record WeatherResponse(double tempCelsius, String condition) {}
```

### *호출*

```java
ChatResponse res = chatModel.call(new Prompt(
    "서울 현재 날씨 는?",
    OpenAiChatOptions.builder()
        .withFunction("weatherFunction")  // *등록 만*
        .build()
));
```

LLM 이 *자동 *결정* — *함수 *호출 → 결과 + 자연어 응답*.

### *복수 함수 — Agent 패턴*

```java
@Bean
ChatClient agentClient(ChatClient.Builder builder) {
    return builder
        .defaultFunctions(
            "weatherFunction",
            "stockPriceFunction",
            "calendarFunction",
            "dbQueryFunction"
        )
        .build();
}
```

→ *LLM 이 *질문 분석 → *적합 한 *복수 함수 *순차 호출 → 통합 응답*.

---

## 3. **Tool 설계** — *진짜 어려움*

### *함수 설계 의 *5 원칙*

#### 1. ***명확 한 이름 + 설명***

```java
// ❌ 모호
@Description("Process the data")
Function<X, Y> handle() { ... }

// ✅ 명확
@Description("Calculate monthly settlement for a vendor given vendor_id and month")
Function<SettlementRequest, SettlementResponse> calculateMonthlySettlement() { ... }
```

LLM 이 *함수 선택* 의 *근거 = 설명*. *설명이 *불명확* 하면 *호출 안 함* 또는 *잘못 호출*.

#### 2. ***작은 책임***

```java
// ❌ 너무 많은 일
@Description("Get user, update points, send notification")
Function<X, Y> doEverything() { ... }

// ✅ 분리
@Description("Get user by id")
@Description("Update user points")
@Description("Send notification to user")
```

LLM 이 *복수 함수 *순차 *호출 가능*. *단일 책임* 이 *조합 의 *유연성*.

#### 3. ***멱등성***

```java
// ❌ 재시도 시 *2 번 처리
@Description("Charge user")
Function<ChargeRequest, ...> charge() { ... }

// ✅ idempotency key 포함
@Description("Charge user (idempotency_key required)")
Function<ChargeRequest, ...> chargeIdempotent() { ... }
```

LLM 이 *함수 *재시도 *가능*. *멱등성 없으면 *중복 처리 위험*.

#### 4. ***실패 처리*** — *명시 적 *오류*

```java
@Description("Get product by id. Returns null if not found.")
Function<ProductId, Optional<Product>> getProduct() { ... }
```

*실패 의 *형태* 를 *명시* — LLM 이 *다음 행동 *결정 가능*.

#### 5. ***Output 의 *구조 화***

```java
// ❌ 자유 형식
Function<X, String> get() { ... }

// ✅ 구조 화
record StockPriceResult(double current, double change, double volume) {}
Function<StockRequest, StockPriceResult> getStockPrice() { ... }
```

*JSON / record 형태 의 *Output 이 *LLM 의 *재 사용 *쉬움*.

---

## 4. **Agent 패턴** — *복수 함수 의 *조합*

### *4.1. ReAct (Reason + Act)*

```
1. Reason  : 사용자 의 *질문 *분석*
2. Act     : 적합 한 *함수 호출*
3. Observe : 결과 관찰
4. Reason  : 결과 가 *답 인가? *아니면 *추가 호출 필요?*
5. Act     : (필요 시) 다음 함수 호출
6. ...
7. Answer  : *최종 응답*
```

대표 예 :

```
사용자 : "오늘 *서울 날씨 + 코스피 + 일정 *3 개 추천 해 줘.*"
LLM    :
  → weatherFunction("서울")    → 맑음, 25°C
  → stockPriceFunction("KOSPI") → 3200, +1.2%
  → calendarFunction(...)       → 회의 / 운동 / 식사
  → 통합 응답
```

### *4.2. Plan-and-Execute*

```
1. Plan : LLM 이 *전체 단계 *계획*
2. Execute : 단계 별 *함수 호출*
3. Synthesize : *최종 응답*
```

*복잡 한 작업* 에 *유리*. 단 *Plan 의 *오차 가 *큼*.

### *4.3. Multi-Agent*

```
사용자 → 마스터 Agent
              ↓ 작업 *분배*
          ┌───┴───┬───────┬───────┐
         검색 A   분석 B   생성 C   검증 D
              ↓
          마스터 가 *통합*
```

*전문화 된 *복수 Agent 의 *조합*. 2026 의 *최신 패턴*.

### *4.4. Tool 선택 의 *전략*

```
함수 N 개 → LLM 의 context 부담 ↑
→ *Tool selection layer* 추가 (사전 *필터링*)

예 :
  사용자 질문 → embedding → 유사 함수 5 개 만 추출
              → LLM 에 *그 5 개 만 *제시*
              → 호출 결정
```

*함수 100 개 이상* 의 *대규모 Agent* 에 *필수*.

---

## 5. **보안** — *함수 의 *권한 모델*

### *5.1. 입력 검증*

```java
@Bean
@Description("Query database with SQL")
Function<DbQueryRequest, ...> dbQuery() {
    return req -> {
        // ❌ 직접 실행
        return jdbc.query(req.sql());  // SQL injection
    };
}
```

해결 — *파라미터 화 쿼리 + 화이트 리스트* :

```java
@Bean
@Description("Query products by category")
Function<ProductQueryRequest, List<Product>> productByCategory() {
    return req -> {
        // ✅ 미리 정의 된 쿼리
        return jdbc.queryForList(
            "SELECT * FROM products WHERE category = ?",
            req.category()
        );
    };
}
```

***함수 의 *행동 을 *좁게 제한*. SQL / 명령 의 *임의 실행 *절대 *불가*.

### *5.2. 권한 모델*

```java
@Bean
@Description("Get user data (admin only)")
@PreAuthorize("hasRole('ADMIN')")
Function<UserQueryRequest, User> getUserAsAdmin() { ... }

@Bean
@Description("Get my profile")
Function<Void, MyProfile> getMyProfile() {
    return ignore -> {
        Long userId = SecurityContextHolder
            .getContext().getAuthentication()
            .getName();
        return userRepo.findById(userId);
    };
}
```

LLM 호출 의 *사용자 권한* 을 *함수 별 *적용*. *Excessive Agency (OWASP LLM08) 방지*.

### *5.3. Sandbox*

```java
@Bean
@Description("Execute Python code")
Function<CodeRequest, CodeResult> executeCode() {
    return req -> {
        // ✅ Docker / nsjail / seccomp 등 *격리 환경*
        return sandboxRunner.execute(req.code(), timeout = 5s, memLimit = 256MB);
    };
}
```

*코드 / shell 실행 함수* 는 *반드시 *격리*. *호스트 의 *직접 영향 불가*.

### *5.4. Audit Log*

```java
@Bean
ChatClient chatClient(ChatClient.Builder builder) {
    return builder
        .defaultAdvisors(new FunctionCallAuditAdvisor())
        .build();
}

class FunctionCallAuditAdvisor implements ... {
    public void onFunctionCall(String name, Object input, Object output) {
        auditLog.record(name, input, output, userId, timestamp);
    }
}
```

***모든 함수 호출 의 *기록*. *사후 *문제 추적 가능 + 보안 *증거*.

### *5.5. Rate Limit*

```java
@Bean
@Description("Send email")
@RateLimiter(name = "email", limitForPeriod = 5, periodInSeconds = 60)
Function<EmailRequest, ...> sendEmail() { ... }
```

LLM 이 *반복 호출* 의 *비용 / 영향 제한*.

---

## 6. **추적** — *Observability*

### *핵심 지표*

```
- 함수 별 *호출 수*
- 함수 별 *성공 / 실패 율*
- 함수 별 *latency (P50, P99)*
- 함수 별 *비용*
- *Chain 의 *깊이* (한 요청에 *몇 번 호출 *됐는지)
```

### *Spring AI 의 *내장 Observability*

```yaml
management:
  tracing:
    sampling:
      probability: 1.0
  metrics:
    distribution:
      percentiles-histogram:
        spring.ai.chat.client: true
```

자동 *수집*. Grafana 대시보드 *바로 연결*.

### *함수 호출 의 *흐름 시각화*

```
요청 → 함수 A → 함수 B → 함수 C → 최종 응답
        ↓        ↓         ↓
       300ms   500ms     200ms       *총 1초*
```

*Jaeger / OpenTelemetry* 와 통합 — *분산 추적 의 *진수*.

---

## 7. **실 무 적용 *사례*

### *7.1. 고객 지원 Agent*

```
함수 :
  - searchKnowledgeBase
  - getUserOrder
  - getUserSubscription
  - createSupportTicket
  - sendNotification

사용자 : "내 주문 취소 가능해?"
Agent :
  1. getUserOrder → 주문 정보
  2. searchKnowledgeBase → 취소 정책
  3. → "이 주문 은 *24시간 *전이라 *취소 가능. *진행 할까요?"
```

### *7.2. 데이터 분석 Agent*

```
함수 :
  - queryDatabase
  - generateChart
  - exportReport
  - sendEmail

사용자 : "지난 달 매출 차트 메일 보내 줘"
Agent :
  1. queryDatabase(month = -1)
  2. generateChart(data)
  3. exportReport(chart)
  4. sendEmail(report)
```

### *7.3. DevOps Agent*

```
함수 :
  - getPodStatus
  - tailLog
  - rollbackDeployment
  - createAlert

사용자 : "왜 productservice 가 *느려?"
Agent :
  1. getPodStatus(productservice)
  2. tailLog(productservice, lastMinutes=5)
  3. → "DB 연결 풀 *고갈. *주말 *알람 받으셨 어요?"
```

### *7.4. 정량 트레이딩 Agent (조심 — 실 거래 위험)*

```
*거래 함수 는 *반드시 *수동 확인 단계 필요*
- LLM 가 *자동 거래 *바로 불가*
- 알람 + 검토 → 사용자 승인 → 거래
```

---

## 8. **흔한 함정**

### 8.1. *Tool 너무 많음*

*함수 50 개 + LLM 의 *context 크기* — *비용 ↑ + 정확도 ↓*. *Tool selection 추가* 또는 *Multi-Agent 분리*.

### 8.2. *함수 설명 *모호*

```
@Description("Process X")  // ❌
@Description("Calculate tax for an invoice given amount and country code (KR / US / JP)")  // ✅
```

LLM 의 *선택 *근거 = 설명*. *명확성이 *결정 적*.

### 8.3. *입력 검증 *부재*

LLM 의 *입력 을 *직접 SQL / shell 등에 *넘기는 것* — *SQL injection / command injection*. *반드시 *검증*.

### 8.4. *비용 *폭발*

```
함수 호출 1 회 = 토큰 비용
복수 호출 + Chain 의 깊이 = 곱 셈 으로 증가
→ 한 요청 의 *비용 이 *수십 ~ 수백 배 증가 가능*
```

*Rate limit + 비용 알람* 필수.

### 8.5. *Excessive Agency*

```
함수 :
  - deleteAllUsers ❌
  - dropTable ❌
  - shutdownServer ❌
```

*위험 한 작업 의 *함수 노출 *절대 *금지*. *읽기 전 용 / 수동 확인 *우선*.

### 8.6. *멱등성 *부재*

LLM 의 *재시도* 가 *2 번 결제 / 2 번 메일 발송* 으로 *이어 짐*. *Idempotency key + DB UNIQUE 제약*.

### 8.7. *Audit 없음*

```
*문제 발생 후 — *왜 *그 함수 가 *호출 됐는지 *추적 불가*
→ *디버깅 *지옥*
```

*모든 호출 의 *기록 의무*.

---

## 9. **권장 *Agent 의 *6 단계 *설계*

### Step 1 — *함수 *명세 작성*

```
함수 명, 설명, 입력 스키마, 출력 스키마, 권한 요구, 예외 처리
```

### Step 2 — *보안 *분석*

```
- 어떤 권한 *필요*?
- 입력 *검증 *어떻게*?
- 영향 *최대 *얼마*?
- *Sandbox 필요 *한가?
- Rate limit *필요?
```

### Step 3 — *멱등성 *적용*

```
- 변경 함수 의 *Idempotency key
- DB UNIQUE 제약
```

### Step 4 — *Observability 통합*

```
- Micrometer Metrics
- Distributed Tracing
- Audit Log
```

### Step 5 — *Agent 패턴 *선택*

```
- 단순 : Tool list + ReAct
- 복잡 : Plan-and-Execute
- 대규모 : Multi-Agent
```

### Step 6 — *테스트 + 모니터링*

```
- 단위 테스트 (mock LLM)
- E2E 테스트 (실 LLM)
- 카오스 테스트 (함수 실패 시 *Agent 동작*)
- 비용 + 정확도 *지속 모니터링*
```

---

## 10. *내 *경험* — *Function Calling *적용*

### *2024 도입*

- *단일 함수 *시범*
- *보안 검증 *부재*
- *추적 *없음*

### *2025 확장*

- *5 개 함수 + ReAct 패턴*
- *Audit Log + Rate Limit*
- *Sandbox 미적용 (위험)*

### *2026 현재*

- *20+ 함수 + Multi-Agent*
- *모든 함수 의 *권한 모델*
- *Sandbox (Docker + nsjail) 적용*
- *비용 의 *예측 + 알람*
- *오류 시 *graceful fallback*

### *얻은 *교훈*

1. ***Tool 설계 의 *깊이 = Agent 의 *성능***
2. ***보안 = 함수 설계 의 *첫 *순간 부터***
3. ***추적 *없으면 *디버깅 *불가능***
4. ***Multi-Agent 는 *모놀리식 *부담 의 *분산***

---

## 11. *마치며*

> *Function Calling 의 *깊이 = *Tool 설계 + 보안 + 추적* 의 *3 축 의 *완성*. *한 축 부족 시 *시스템 의 *손실*.

3 줄 요약 :

1. ***Tool 설계 의 *5 원칙* — *명확 한 이름 / 작은 책임 / 멱등성 / 명시 적 오류 / 구조 화 *output***
2. ***보안 = 함수 의 *권한 + 입력 검증 + Sandbox + Audit + Rate Limit*** — *5 가지 의 *조합*.
3. ***Observability *없는 *Agent = *위험 *부담***. *모니터링 + 비용 알람 + 분산 추적*.

7년차 회고 :

> *"함수 *2 개 + ReAct 로 *시작* 했다. *지금 의 *시스템 은 *수십 함수 + Multi-Agent. *그 사이 의 *학습 = *함수 설계 의 *디자인 패턴 깊이* 의 *재 발견*."*

다음 글 — *Multi-Agent 의 *깊이* — *마스터 ↔ 워커 / *조정 패턴 / 충돌 처리*. 같은 시리즈 로 이어 집니다.

---

> 본 글은 *7년차 백엔드 / Spring AI 운영 회고*. *Function Calling 의 *생태계 가 *빠르게 *변화 — *6 개월 후 *세부 가 *변할 수 있음*. *원리 + 설계 원칙* 에 *무게 중심* 을 두는 게 *오래 가는 지식*.
