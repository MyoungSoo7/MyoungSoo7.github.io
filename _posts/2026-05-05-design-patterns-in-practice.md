---
layout: post
title: "실전 디자인 패턴 적용기 — 7개 프로젝트에서 배운 것"
date: 2026-05-05 10:00:00 +0900
categories: [architecture, design-pattern]
tags: [design-pattern, spring-boot, observer, strategy, facade, decorator, template-method]
---
{% raw %}

운영 중인 프로젝트에 디자인 패턴을 적용하며 배운 실전 경험을 정리합니다.

## 1. Observer 패턴 — 주식 자동매매

**문제**: `TradingService`가 매매 실행 후 `NotificationService.sendTradeAlert()`를 직접 호출. 알림 채널 추가 시 서비스 코드 수정 필요.

**해결**: Spring `ApplicationEvent`로 매매 이벤트를 발행하고, 리스너가 비동기로 처리.

```java
// 이벤트 정의
public record TradeEvent(Trade trade, String message) {
    public static TradeEvent of(Trade trade) {
        String emoji = trade.getType() == Trade.TradeType.BUY ? "🟢 매수" : "🔴 매도";
        return new TradeEvent(trade, String.format("%s %s %d주 @%,d원",
                emoji, trade.getStockName(), trade.getQuantity(), trade.getPrice()));
    }
}

// 발행자
@Component
public class TradeEventPublisher {
    private final ApplicationEventPublisher publisher;
    public void publish(Trade trade) {
        publisher.publishEvent(TradeEvent.of(trade));
    }
}

// 리스너 — 텔레그램 알림 (비동기)
@Async @EventListener
public void onTradeEvent(TradeEvent event) {
    notificationService.sendTradeAlert(event.trade());
}
```

**효과**: 서비스 코드 수정 없이 Slack, Email 등 새 리스너 추가 가능.

---

## 2. Strategy 패턴 — 매매 전략 + 재무 지표

### 주식/코인 매매 전략

```java
public interface TradingStrategy {
    String name();
    Signal evaluate(String stockCode, List<Double> prices);
    enum Signal { BUY, SELL, HOLD }
}

@Component
public class MaCrossStrategy implements TradingStrategy {
    // 5일선/20일선 골든크로스 → 매수
}

@Component  
public class RsiStrategy implements TradingStrategy {
    // RSI 30 이하 → 매수, 70 이상 → 매도
}
```

Spring이 `List<TradingStrategy>`로 자동 주입 → 새 전략 추가 시 클래스만 생성.

### DART 재무 지표 추출

```java
public interface MetricExtractor {
    String metricName();
    String extract(List<Map<String, Object>> financialItems);
}

@Component
public class RevenueExtractor implements MetricExtractor {
    @Override public String metricName() { return "매출액"; }
    @Override public String extract(List<Map<String, Object>> items) {
        return items.stream()
            .filter(i -> i.get("account_nm").toString().contains("매출"))
            .map(i -> i.get("thstrm_amount").toString())
            .findFirst().orElse("");
    }
}
```

기존: AnalysisService에 하드코딩된 if-else 체인 → 신규 지표 추가 시 서비스 수정 필요.
개선: 새 `MetricExtractor` 구현체만 추가 → OCP(개방-폐쇄 원칙) 준수.

---

## 3. Template Method 패턴 — 코인 매매 전략

**문제**: `RsiCryptoStrategy`와 `BollingerBandStrategy`가 동일한 평가 흐름(데이터 검증 → 지표 계산 → 임계값 비교)을 반복.

```java
public abstract class AbstractCryptoStrategy implements CryptoStrategy {
    
    @Override
    public final Signal evaluate(String coin, List<Double> prices) {
        if (prices.size() < requiredDataPoints()) return Signal.HOLD;
        double indicator = calculateIndicator(prices);
        if (indicator <= buyThreshold()) return Signal.BUY;
        if (indicator >= sellThreshold()) return Signal.SELL;
        return Signal.HOLD;
    }

    protected abstract int requiredDataPoints();
    protected abstract double calculateIndicator(List<Double> prices);
    protected abstract double buyThreshold();
    protected abstract double sellThreshold();
}
```

하위 클래스는 4개 메서드만 구현. 평가 흐름은 변경 불가(`final`).

---

## 4. Decorator 패턴 — 리스크 관리

**문제**: 급락장에서 전략이 "매수" 시그널을 보내지만, 리스크 관리 없이 그대로 실행되면 위험.

```java
public class RiskManagedStrategy implements CryptoStrategy {
    private final CryptoStrategy delegate;   // 원본 전략
    private final double maxLossPercent;

    @Override
    public Signal evaluate(String coin, List<Double> prices) {
        Signal signal = delegate.evaluate(coin, prices);
        
        if (signal == Signal.BUY) {
            double change = (prices.get(0) - prices.get(10)) / prices.get(10) * 100;
            if (change < -maxLossPercent) return Signal.HOLD; // 급락 시 매수 차단
        }
        return signal;
    }
}
```

원본 전략 코드를 수정하지 않고 리스크 체크를 감쌈. 여러 Decorator 중첩 가능.

---

## 5. Facade 패턴 — 대시보드

**문제**: `DashboardController`가 `KisApiClient`, `TradeRepository`, `TradingService`를 각각 호출.

```java
@Component
public class TradingFacade {
    private final KisApiClient kisApi;
    private final TradeRepository tradeRepo;
    private final TradingService tradingService;

    public Map<String, Object> getPortfolioSummary() {
        Map<String, Object> summary = new LinkedHashMap<>();
        summary.put("trades", tradeRepo.findTop50());
        summary.put("priceHistory", tradingService.getPriceHistory());
        summary.put("balance", kisApi.getBalance());
        return summary;
    }
}
```

컨트롤러는 `facade.getPortfolioSummary()` 한 줄로 모든 데이터 획득.

---

## 6. Adapter 패턴 — 미디어 검색

```java
public interface MediaSource {
    String name();
    SearchResult searchPhotos(String query, int page, int perPage);
    SearchResult searchVideos(String query, int page, int perPage);
}
```

현재 Pexels만 구현. 향후 Unsplash, Pixabay 추가 시 `MediaSource` 구현체만 작성.

---

## 7. Chain of Responsibility — 매매 검증

```java
public interface TradeValidator {
    boolean validate(String stockCode, int qty, int price);
    String reason();
}

@Component
public class MarketHoursValidator implements TradeValidator {
    // 장 시간이 아니면 false
}
```

검증 로직을 체인으로 연결 — 새 검증 규칙 추가 시 Validator 구현체만 생성.

---

## 적용 결과 요약

| 패턴 | 프로젝트 | Before | After |
|------|---------|--------|-------|
| Observer | auto-trading | 직접 알림 호출 | 이벤트 기반 비동기 |
| Strategy | auto/crypto/dart | if-else 체인 | 인터페이스 + 자동 주입 |
| Template Method | crypto-trading | 코드 중복 | 공통 흐름 + 커스텀 계산 |
| Decorator | crypto-trading | 리스크 관리 없음 | 전략 래핑 |
| Facade | auto-trading | 컨트롤러 복잡 | 단일 진입점 |
| Adapter | media-search | Pexels 하드코딩 | 멀티 소스 확장 |
| CoR | auto-trading | 검증 로직 산재 | 검증 체인 |

**핵심 교훈**: 디자인 패턴은 "코드를 바꾸지 않고 기능을 확장"하기 위한 것. OCP(개방-폐쇄 원칙)를 지키면 새 전략, 새 알림 채널, 새 데이터 소스 추가가 기존 코드 수정 없이 가능해진다.

{% endraw %}
