---
layout: post
title: "AI Agent 패턴 비교 — ReAct, Plan&Execute, Self-Reflection"
date: 2026-05-04 11:00:00 +0900
categories: [ai, architecture]
tags: [ai-agent, react, spring-ai, strategy-pattern]
---
{% raw %}

## AI Agent란?

단순 질의응답을 넘어 **목표를 달성하기 위해 자율적으로 도구를 사용하고, 판단하고, 행동하는 LLM 시스템**입니다.

이커머스 고객 지원 AI Agent를 Strategy 패턴으로 구현하여 4가지 전략을 상황에 맞게 선택합니다.

## 4가지 Agent 전략

### 1. ReAct (Reasoning + Acting)

```
Thought → Action → Observation 반복
```

```java
@Component
public class ReActStrategy implements AgentStrategy {
    
    private static final String SYSTEM_PROMPT = """
        당신은 자율적인 AI 에이전트입니다.
        사용자의 목표를 달성하기 위해 제공된 도구를 직접 호출하세요.
        도구 호출 결과를 바탕으로 최종 답변을 작성하세요.
        """;

    @Override
    public StrategyType type() { return StrategyType.REACT; }
    
    @Override
    public String execute(String goal) {
        return chatClient.prompt()
            .system(SYSTEM_PROMPT)
            .user(goal)
            .tools(functionTools)
            .call().content();
    }
}
```

### 2. Plan & Execute

```
전체 계획 수립 → 단계별 실행 → 결과 종합
```

복잡한 작업(주문 조회 → 환불 → 쿠폰 발급)을 먼저 계획한 후 순차 실행.

### 3. Self-Reflection

```
실행 → 결과 평가 → 부족하면 재시도
```

답변 품질을 스스로 평가하고 개선.

### 4. Limited Tools

도구 제한 모드 — 특정 상황에서 위험한 도구(환불, 삭제)를 제외.

## Strategy 패턴 적용

```java
@Component
public class AgentStrategyFactory {
    private final Map<StrategyType, AgentStrategy> strategies;
    
    public AgentStrategy getStrategy(StrategyType type) {
        return strategies.get(type);
    }
}
```

상황에 따라 전략을 동적으로 선택:
- 단순 질문 → **ReAct** (빠른 응답)
- 복잡한 요청 → **Plan & Execute** (정확한 실행)
- 중요한 작업 → **Self-Reflection** (품질 보장)
- 제한 환경 → **Limited Tools** (안전성)

## 고객 지원 AI의 추가 기능

- **감성 분석**: 고객 메시지에서 감정(긍정/부정/중립) 파악
- **우선순위 분류**: 긴급도에 따라 자동 분류
- **Content Safety**: 프롬프트 인젝션 방어 (`PromptSanitizer`)

## 기술 스택

- Spring AI + Google Gemini
- Strategy 패턴 (4가지 Agent 전략)
- Spring Boot 4.0 + PostgreSQL + pgvector

{% endraw %}
