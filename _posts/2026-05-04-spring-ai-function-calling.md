---
layout: post
title: "Spring AI Function Calling — LLM에게 도구를 쥐여주기"
date: 2026-05-04 12:00:00 +0900
categories: [ai, spring]
tags: [spring-ai, function-calling, gemini, tools]
---
{% raw %}

## Function Calling이란?

LLM이 **외부 함수를 직접 호출**하여 실시간 정보를 가져오는 패턴입니다. 날씨, 계산, 현재 시간 등 LLM이 자체적으로 알 수 없는 정보를 도구를 통해 해결합니다.

## 구현

### 1. 도구 정의

```java
@Component
public class FunctionTools {

    @Tool("현재 날씨를 조회합니다")
    public WeatherResponse getWeather(WeatherRequest request) {
        // 외부 API 호출
        return weatherClient.fetch(request.getCity());
    }

    @Tool("수학 계산을 수행합니다")
    public CalculatorResponse calculate(CalculatorRequest request) {
        return switch (request.getOperation()) {
            case ADD -> new CalculatorResponse(request.getA() + request.getB());
            case MULTIPLY -> new CalculatorResponse(request.getA() * request.getB());
            // ...
        };
    }

    @Tool("현재 시간을 반환합니다")
    public CurrentTimeResponse getCurrentTime() {
        return new CurrentTimeResponse(LocalDateTime.now());
    }
}
```

### 2. LLM에 도구 연결

```java
public String chat(String userMessage) {
    return chatClient.prompt()
        .user(userMessage)
        .tools(functionTools)  // 도구 등록
        .call()
        .content();
}
```

### 3. 동작 흐름

```
사용자: "서울 날씨 어때?"
    ↓
LLM 판단: getWeather 호출 필요
    ↓
LLM → getWeather({city: "서울"}) 호출
    ↓
함수 실행 → {temp: 22, condition: "맑음"} 반환
    ↓
LLM: "서울은 현재 22도이고 맑은 날씨입니다."
```

LLM이 **언제 어떤 도구를 쓸지 자율적으로 판단**합니다. 개발자는 도구만 정의하면 됩니다.

## 면접에서 이렇게 말하면 됩니다

> "Function Calling은 LLM의 한계(실시간 데이터, 계산)를 외부 함수로 보완하는 패턴입니다. Spring AI의 `@Tool` 어노테이션으로 함수를 정의하면, LLM이 자율적으로 필요한 도구를 선택하여 호출합니다."

{% endraw %}
