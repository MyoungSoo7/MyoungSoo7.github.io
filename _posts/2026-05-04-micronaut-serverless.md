---
layout: post
title: "Micronaut Serverless — 환율/주가 API를 Lambda로"
date: 2026-05-04 03:00:00 +0900
categories: [project, serverless]
tags: [micronaut, graalvm, lambda, serverless]
---

## 프로젝트 소개

Micronaut Framework 기반 서버리스 API입니다. USD/KRW 환율과 한국 주식 시세를 제공합니다.

**Live**: [serveless.lemuel.co.kr](https://serveless.lemuel.co.kr)

## 왜 Micronaut?

| | Spring Boot | Micronaut |
|---|---|---|
| 시작 시간 | ~2초 | ~0.5초 |
| 메모리 | ~200MB | ~80MB |
| GraalVM | 설정 복잡 | 네이티브 지원 |
| Lambda | 콜드 스타트 느림 | 콜드 스타트 빠름 |

서버리스 환경에서는 **콜드 스타트**가 핵심이므로 Micronaut이 유리합니다.

## API 엔드포인트

```
GET /api/exchange-rates     → USD 기준 환율 (KRW, JPY, EUR + 교차환율)
GET /api/stocks?symbol=005930  → 한국 주식 시세
GET /                       → API 문서
```

## 핵심 구현

```java
@Controller("/api/exchange-rates")
public class ExchangeRateController {
    
    @Get
    public ExchangeRateResponse getRates() {
        return service.getUsdBasedRates();  // Caffeine 5분 캐시
    }
}

@Client("https://open.er-api.com")
public interface ExchangeRateClient {
    @Get("/v6/latest/{base}")
    Map<String, Object> getLatest(@PathVariable String base);
}
```

## 기술 스택

Micronaut 4.7 / Java 25 / Caffeine Cache / AWS Lambda (SAM)
