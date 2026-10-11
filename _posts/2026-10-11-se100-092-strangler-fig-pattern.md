---
layout: post
title: "[SE100 #092] 스트랭글러 피그 — 점진적 교체"
date: 2026-10-11 17:10:41 +0900
categories: [software-engineering]
tags: [se100, evolution-and-people, strangler-fig, legacy-displacement, incremental-migration]
---

소프트웨어 공학 100 주제 시리즈의 92번째 글이다. (카테고리: 유지보수·진화·사람)

## 한 줄 요약

레거시를 한 번에 갈아엎지 말고, 앞단에서 요청을 가로채 기능 단위로 새 시스템에 넘기다가 옛 시스템이 아무 일도 안 하게 되면 끈다. 투자와 회수가 **조금씩, 눈에 보이게** 일어나는 것이 이 패턴의 본질이다.

## 왜 필요한가

전면 재작성(big-bang rewrite)은 매력적이다. 새 언어, 새 아키텍처, 깨끗한 코드. 그러나 대가가 크다.

- **가치가 마지막 날에야 나온다.** 몇 년짜리 재작성은 끝나기 전까지 사용자에게 아무것도 주지 못한다. 그 사이 사업 요구는 바뀐다.
- **숨은 요구를 잃는다.** Martin Fowler 는 2004년 원래 글([Original Strangler Fig Application](https://martinfowler.com/bliki/OriginalStranglerFigApplication.html))에서 재작성 때는 "옛것이 남아 있어야 하고, 심지어 옛 버그도 새 시스템에 넣어야 하는 경우가 많다" 고 지적했다. 운영 중인 시스템에 녹은 예외 처리와 관행은 문서에 없다.
- **중단 지점이 없다.** 재작성은 중간에 멈추면 투자 전부가 사라진다.

Joel Spolsky 는 [Things You Should Never Do, Part I](https://www.joelonsoftware.com/2000/04/06/things-you-should-never-do-part-i/) (2000)에서 처음부터 다시 짜는 결정을 "소프트웨어 회사가 저지를 수 있는 단 하나의 최악의 전략적 실수" 라고 불렀다. 옛 코드는 쓰였고, 테스트됐고, 그 과정에서 찾은 버그 수정이 쌓여 있기 때문이다.

## 핵심 개념

### 이름의 유래

Fowler 는 2001년 호주 퀸즐랜드 열대우림에서 본 교살무화과(strangler fig)에서 이름을 따왔다. 씨앗이 숙주 나무 위에서 싹터 뿌리를 땅으로 내리고, 수년에 걸쳐 숙주를 감싸며 결국 숙주는 사라지고 무화과가 남는다. 원래 제목은 "Strangler Application" 이었으나, 2024년 개정판 [Strangler Fig Application](https://martinfowler.com/bliki/StranglerFigApplication.html) 에서 폭력적 어감을 피하고 식물 비유를 분명히 하려고 "Fig" 를 붙였다고 밝힌다.

개정판의 핵심 문장은 다음과 같다.

> 무화과처럼, 이 방식은 작은 추가 — 흔히 새 기능 — 로 시작한다. 레거시 코드베이스 위에 만들지만 그것과는 분리되어 있다.

> 이 방식이 하는 일은 투자와 회수가 모두 점진적이고 눈에 보이게 일어나도록 만드는 것이다.

### 네 단계 (Azure 아키텍처 센터의 정리)

Microsoft 의 [Strangler Fig 패턴 문서](https://learn.microsoft.com/en-us/azure/architecture/patterns/strangler-fig)는 과정을 네 단계로 그린다.

```
1) 파사드 도입          2) 점진 분해            3) 레거시 폐기        4) 파사드 제거
 client                  client                  client                client
   │                       │                       │                     │
 [facade]                [facade]                [facade]                │
  │    ╲                  │    ╲                       ╲                 │
 legacy  new            legacy  NEW                      NEW            NEW
 (대부분)  (일부)          (일부)   (대부분)                 (전부)
```

1. 클라이언트와 시스템 사이에 **파사드(프록시)** 를 둔다. 처음엔 거의 모든 요청이 레거시로 간다.
2. 기능을 하나씩 새 시스템에 구현하고, 파사드가 해당 경로를 새 시스템으로 돌린다.
3. 레거시에 의존하는 것이 없어지면 레거시를 폐기한다.
4. 파사드를 걷어내고 클라이언트가 새 시스템과 직접 통신한다. 또는 파사드를 옛 클라이언트용 어댑터로 남겨 둘 수도 있다.

같은 문서는 이 패턴이 **맞지 않는** 경우도 명시한다. 백엔드로 가는 요청을 가로챌 수 없을 때, 레거시 소스를 수정할 수 없을 때(이관된 기능을 끄고 내부 호출을 돌려야 하므로), 시스템이 작아 통째 교체가 간단할 때, 원 시스템을 빨리 완전히 없애야 할 때다.

### 전환기 아키텍처는 낭비가 아니다

파사드, 이벤트 복제, 어댑터처럼 **나중에 버릴 것을 알고 만드는 코드** 가 생긴다. Fowler 의 동료들은 [Patterns of Legacy Displacement](https://martinfowler.com/articles/patterns-legacy-displacement/) (Ian Cartwright, Rob Horn, James Lewis)에서 이를 [Transitional Architecture](https://martinfowler.com/articles/patterns-legacy-displacement/transitional-architecture.html) 라는 패턴으로 이름 붙였다. Fowler 의 개정판 글도 "낭비처럼 보일 수 있지만 점진적 접근의 위험 감소와 이른 가치가 그 비용보다 크다" 고 쓴다.

### 가로채기의 수단

| 수단 | 설명 | 예 |
|---|---|---|
| HTTP 라우팅 | 경로·헤더 기준으로 프록시가 분기 | API 게이트웨이, 인그레스 규칙 |
| [Event Interception](https://martinfowler.com/articles/patterns-legacy-displacement/event-interception.html) | 상태 변경 이벤트를 가로채 새 컴포넌트로 흘림 | 메시지 큐 앞에 라우터 |
| [Legacy Mimic](https://martinfowler.com/articles/patterns-legacy-displacement/legacy-mimic.html) | 새 시스템이 레거시가 기대하는 인터페이스를 흉내 냄 | 레거시가 읽는 파일·테이블 형식으로 출력 |
| 코드 내부 추상화 | 같은 프로세스 안에서 구현 교체 | Branch by Abstraction |
| DB 측 신호 | 앱을 못 고칠 때 트리거·CDC 로 변경을 내보냄 | 변경 데이터 캡처 |

### 코드 안에서의 스트랭글러: Branch by Abstraction

경계가 네트워크가 아니라 모듈일 때는 [Branch by Abstraction](https://martinfowler.com/bliki/BranchByAbstraction.html) (Fowler, 2014; 이름은 Paul Hammant)을 쓴다. 단계는 다음과 같다.

1. 클라이언트 코드와 기존 공급자 사이에 추상화 계층을 만든다.
2. 모든 클라이언트가 추상화만 쓰도록 옮긴다.
3. 같은 추상화 뒤에 새 구현을 만든다.
4. 클라이언트를 새 구현으로 점진 전환한다.
5. 옛 구현을 지운다(필요하면 추상화도).

트렁크 기반 개발에서 장기 브랜치 없이 대규모 교체를 하는 방법이다. 브랜치 전략은 [Git 브랜치 전략]({% post_url 2026-10-10-cs300-195-git-branching-strategies %}) 글에서 다뤘다.

## 예제

### 1) 프록시 라우팅 (Nginx)

```nginx
# 이관이 끝난 경로만 새 서비스로. 나머지는 전부 레거시.
upstream legacy  { server legacy-app:8080; }
upstream orders  { server orders-svc:8080; }

server {
  listen 80;
  location /api/orders/ { proxy_pass http://orders; }   # 2단계: 주문 이관 완료
  location /            { proxy_pass http://legacy; }   # 기본값은 레거시
}
```

### 2) 비율 전환과 비교 (Kotlin)

새 경로를 바로 믿지 않고, 일부 트래픽만 보내면서 결과를 비교한다.

```kotlin
class OrderQueryRouter(
    private val legacy: OrderQuery,
    private val modern: OrderQuery,
    private val rolloutPercent: () -> Int,          // 설정에서 읽음 (0 → 100)
    private val metrics: Metrics,
) : OrderQuery {
    override fun find(id: String): Order {
        val useModern = (id.hashCode().mod(100)) < rolloutPercent()
        if (!useModern) {
            val result = legacy.find(id)
            // 그림자 호출: 결과는 버리고 차이만 기록 (dark launching)
            runCatching { modern.find(id) }
                .onSuccess { if (it != result) metrics.inc("order.mismatch") }
                .onFailure { metrics.inc("order.modern_error") }
            return result
        }
        return modern.find(id)
    }
}
```

- 그림자 호출은 [Dark Launching](https://martinfowler.com/articles/patterns-legacy-displacement/dark-launching.html) 이다. 쓰기 작업에는 부작용 때문에 그대로 쓰면 안 된다.
- 해시 기반 분기라 같은 주문은 항상 같은 쪽으로 간다. 사용자 단위 일관성이 필요하면 사용자 ID 로 해시한다.
- 불일치율이 0 에 수렴하고 오류율이 안정되면 비율을 올린다. 단계적 노출은 [Canary Release](https://martinfowler.com/bliki/CanaryRelease.html) 와 같다.

### 3) 이관 순서 정하기 체크리스트

- [ ] 가로채기 지점이 있는가 (게이트웨이, 큐, 모듈 경계)
- [ ] 이 기능을 옮겼을 때 **사용자가 체감하는 가치** 가 있는가 (가치가 큰 것부터)
- [ ] 데이터 소유권이 분리 가능한가, 아니면 공유 DB 를 한동안 같이 써야 하는가
- [ ] 되돌리기(라우팅 원복)가 설정 변경 한 번으로 되는가
- [ ] 레거시 쪽 해당 코드 경로를 끌 수 있는가
- [ ] 이관 완료의 정의(레거시 호출 0, 데이터 동기화 중단)가 정해졌는가

## 흔한 오해와 함정

- **"스트랭글러는 결국 기능 동등성(feature parity)을 맞추는 일이다."** Patterns of Legacy Displacement 는 [Feature Parity](https://martinfowler.com/articles/patterns-legacy-displacement/feature-parity.html) 를 별도 패턴으로 다루며, 사람들이 그 노력을 크게 과소평가하고, 실제로는 쓰이지 않는 기능까지 다시 만드는 낭비가 생긴다고 경고한다. 옮길 때마다 "이 기능이 여전히 필요한가" 를 묻는다.
- **파사드가 병목·단일 장애점이 된다.** Azure 문서가 명시한 고려사항이다. 파사드도 다중화하고 지연을 측정한다.
- **양쪽이 서로를 부른다.** 이관 중에는 새 시스템이 레거시를 부르고, 레거시가 새 기능을 부르는 일이 생긴다. 이때 레거시의 개념이 새 모델에 스며들지 않도록 [Anti-corruption Layer](https://learn.microsoft.com/en-us/azure/architecture/patterns/anti-corruption-layer) 를 둔다.
- **끝내지 않는다.** 80% 를 옮기고 나머지 20% 때문에 레거시와 파사드를 몇 년씩 같이 운영하면 두 시스템의 비용을 모두 낸다. 폐기 날짜를 계획에 넣는다.
- **새 시스템을 다음 교살이 불가능하게 만든다.** Fowler 의 원래 글은 "우리가 하는 일은 오늘 내일의 레거시를 쓰는 것" 이라며, 새 시스템도 나중에 쉽게 교체되도록 설계하라고 한다.

## 확인 문제

1. 스트랭글러 피그가 전면 재작성보다 위험이 작은 이유를 "투자와 회수" 관점에서 설명하라.
2. Azure 문서가 이 패턴이 적합하지 않다고 든 조건 두 가지를 쓰라.
3. Transitional Architecture 를 "버릴 코드" 라고 반대하는 동료를 어떻게 설득하겠는가?
4. 위 Kotlin 예제의 그림자 호출을 주문 생성(쓰기) API 에 그대로 쓰면 어떤 문제가 생기는가?
5. Branch by Abstraction 이 장기 기능 브랜치보다 나은 점은?

### 풀이

1. 기능 단위로 새 시스템에 넘기므로 각 단계에서 가치가 출시되고, 문제가 생기면 그 단계만 되돌린다. 중간에 멈춰도 이미 옮긴 부분의 가치는 남는다. 재작성은 마지막에 가서야 가치가 나오고 중간 중단 시 투자 전체를 잃는다.
2. 요청을 가로챌 수 없을 때, 레거시 소스를 수정할 수 없을 때, 시스템이 작아 통째 교체가 간단할 때, 원 시스템을 빨리 완전히 폐기해야 할 때 (중 둘).
3. 전환기 코드는 위험을 줄이고 가치를 일찍 내기 위한 비용이며, 그 비용이 위험 감소와 이른 가치보다 작다는 것이 Fowler 와 Patterns of Legacy Displacement 의 논지다. 수명과 제거 시점을 미리 정해 두면 "영구 임시 코드" 가 되지 않는다.
4. 레거시와 새 시스템 양쪽에서 주문이 두 번 생성된다(이중 결제·이중 재고 차감). 쓰기는 새 시스템을 별도 저장소에 기록만 하거나, 멱등 키와 격리된 환경에서 비교해야 한다.
5. 트렁크에서 계속 통합·배포하면서 교체가 진행되므로, 오래 갈라진 브랜치의 병합 충돌과 통합 지연이 없다. 신구 구현이 공존해 단계별로 전환·되돌림이 가능하다.

## 더 읽을거리 (References)

- Martin Fowler, [Strangler Fig Application](https://martinfowler.com/bliki/StranglerFigApplication.html) (2024 개정) / [Original Strangler Fig Application](https://martinfowler.com/bliki/OriginalStranglerFigApplication.html) (2004)
- Ian Cartwright, Rob Horn, James Lewis, [Patterns of Legacy Displacement](https://martinfowler.com/articles/patterns-legacy-displacement/)
- Microsoft, [Strangler Fig pattern — Azure Architecture Center](https://learn.microsoft.com/en-us/azure/architecture/patterns/strangler-fig)
- AWS, [Strangler fig pattern — Prescriptive Guidance](https://docs.aws.amazon.com/prescriptive-guidance/latest/modernization-decomposing-monoliths/strangler-fig.html)
- Martin Fowler, [Branch By Abstraction](https://martinfowler.com/bliki/BranchByAbstraction.html)
- Joel Spolsky, [Things You Should Never Do, Part I](https://www.joelonsoftware.com/2000/04/06/things-you-should-never-do-part-i/)
- [마이크로서비스 vs 모놀리스]({% post_url 2026-10-10-cs300-199-microservices-vs-monolith %}) (CS300 #199)
