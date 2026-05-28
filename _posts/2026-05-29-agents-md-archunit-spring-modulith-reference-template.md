---
layout: post
title: "AGENTS.md + ArchUnit + Spring Modulith *통합 reference template* — *''복잡 도메인을 AI 시대에도 안전하게 확장''* 하기 위한 실전 셋업"
date: 2026-05-29 04:15:00 +0900
categories: [java, spring, architecture, ai, reference-template]
tags: [agents-md, archunit, spring-modulith, hexagonal, cursor-rules, claude-code, ddd, reference-app, ci-cd, github-actions]
---

> *''표준은 *artifact* 가 *있어야* 표준''* — 직전 글 ([Java/Spring + 헥사고날 — 복잡 도메인의 구조 표준]({% post_url 2026-05-29-java-spring-hexagonal-domain-standard-genai-future %})) 에서 *''왜 필요한가''* 를 풀었으니, 이번엔 *''어떻게 박는가''*. **신입이 *명령 한 줄* 로 시작해, *첫 commit 부터 표준 준수* 하고, *AI 가 짠 코드도 *경계를 못 어기며*, *PR 이 자동으로 1 차 리뷰된다*** — 이 *4 가지가 *동시에 작동* 하는 reference template* 의 *디렉토리 트리, 파일 본문, CI 워크플로* 까지 *복사해 쓸 수 있는 형태로* 정리한다.

목표는 *''*글이 *그대로 *코드베이스에 *심을 수 있는* 수준* 까지''*. 추상적 *''*해야 한다''* 는 *''*''다 들어본 말*''*''*. *''*어떤 파일에 *어떤 줄을 박는지''*''* 가 *''*표준 정립의 *진짜 *artifact*''*''*.

---

## 1. 결과물 미리보기 — *디렉토리 트리 + 명령 한 줄*

```
my-service/
├── AGENTS.md                            ← AI 도구 공통 (Claude Code, Cursor, Codex)
├── .cursor/rules/                       ← Cursor 전용 (AGENTS.md 의 subset 참조)
├── README.md                            ← 사람용
├── docs/
│   ├── adr/                             ← Architecture Decision Records
│   │   ├── 0001-why-hexagonal.md
│   │   ├── 0002-why-modulith.md
│   │   └── 0003-outbox-pattern.md
│   └── context-map.md                   ← DDD ubiquitous language
├── .github/
│   ├── pull_request_template.md
│   └── workflows/
│       ├── ci.yml                       ← ArchUnit + Modulith + tests
│       └── agent-review.yml             ← AI agent 1차 리뷰
├── build.gradle.kts
├── gradle/libs.versions.toml
└── src/
    ├── main/java/com/example/order/
    │   ├── package-info.java            ← @ApplicationModule (Modulith)
    │   ├── domain/                      ← 도메인 코어 (Spring/JPA 의존 0)
    │   │   ├── Order.java
    │   │   ├── OrderId.java
    │   │   ├── OrderStatus.java         ← sealed
    │   │   └── OrderPlacedEvent.java
    │   ├── application/                 ← 유스케이스 + port 정의
    │   │   ├── port/
    │   │   │   ├── in/
    │   │   │   │   └── PlaceOrderUseCase.java
    │   │   │   └── out/
    │   │   │       ├── LoadOrderPort.java
    │   │   │       └── SaveOrderPort.java
    │   │   └── service/
    │   │       └── PlaceOrderService.java
    │   └── adapter/
    │       ├── in/web/
    │       │   └── OrderController.java
    │       └── out/persistence/
    │           ├── OrderJpaEntity.java
    │           ├── OrderJpaRepository.java
    │           └── OrderPersistenceAdapter.java
    └── test/java/com/example/
        ├── architecture/
        │   └── HexagonalArchitectureTest.java   ← ArchUnit 룰
        └── order/
            └── domain/OrderTest.java             ← invariant 테스트
```

**신입의 *첫 1 주*** (의례화된 의식):

```bash
$ archetype new my-service           # cookiecutter / Spring Initializr extension
$ cd my-service && ./gradlew test    # ArchUnit + Modulith verify + unit
$ open AGENTS.md                     # 표준 학습 1 시간
$ git checkout -b feat/first-task
$ # Cursor / Claude Code 에서 작업
$ ./gradlew test                     # 자동으로 ArchUnit 통과해야 commit 가능
$ git commit && git push
$ # PR template 자동 채워짐, agent 1차 리뷰 자동 코멘트
```

*''*초기 셋업이 *어디에 무엇이 있는지* 가 *명확*''* 하면 *''*시니어가 *''*1 일 페어 코딩*''* 만 해도 *''*신입이 *2 주차부터 *팀 표준대로* 짠다*''*.

## 2. *AGENTS.md* — *AI 도구 공통 표준 진입점*

### 2.1. 왜 AGENTS.md 인가

2024 년 *Cursor 의 *.cursor/rules*, *Claude Code 의 *AGENTS.md / CLAUDE.md*, *Codex 의 *.codex/instructions*''* 가 *''각자 다른 형식''* 으로 *''*같은 정보를 *반복*''* 시키던 시기.

2025 년 *''*AGENTS.md 가 *de facto 표준''* 으로 수렴 (Anthropic, GitHub, 일부 OSS 들이 채택). *''*AGENTS.md 가 진실, 도구별 파일은 *AGENTS.md 를 *참조*''* 하는 패턴*.

### 2.2. *AGENTS.md 본문 — *복사용 템플릿**

````markdown
# AGENTS.md — my-service

> 이 파일은 *AI 도구 공통 표준 진입점* 입니다. Cursor, Claude Code, GitHub Copilot, Codex 등이 본 파일을 *''first read''* 합니다.

## 1. 코드베이스 *구조* (헥사고날 + Spring Modulith)

이 프로젝트는 **헥사고날 아키텍처** + **Spring Modulith** 를 따릅니다. *경계를 어기는 코드는 CI 에서 자동으로 *fail* 합니다*.

- `domain/` — **Spring·JPA·HTTP·외부 어떤 라이브러리도 import 금지**. `java.*`, 자기 패키지 안만.
- `application/port/in/` — 인바운드 유스케이스 인터페이스. *''*사용자가 *무엇을 *하고 싶은가*''* 표현.
- `application/port/out/` — 아웃바운드 인터페이스. *''*도메인이 *밖에 *필요한 것*''* 표현.
- `application/service/` — 유스케이스 구현. **JPA 직접 의존 금지** — `port/out` 만 호출.
- `adapter/in/web/` — Spring MVC controller. **도메인 객체를 *그대로 노출 금지* — DTO 변환 필수**.
- `adapter/out/persistence/` — JPA entity + repository. *''*도메인 객체 ↔ JPA entity *명시적 변환''*''*.

## 2. *의존 방향* 의 *유일한 규칙*

```
adapter → application → domain (가장 안쪽)
       ↘             ↗
         port (interface — application/port/ 안에 정의)
```

`adapter` 가 `domain` 을 import 해도 OK (외부가 안쪽을 본다). 그러나 *역방향 절대 금지*.

## 3. 도메인 *invariant*

- `OrderStatus` 는 `sealed` — `PENDING | PAID | CANCELLED | DELIVERED` 외 상태 추가 금지 (생성하려면 ADR 필수)
- `Money` 는 `BigDecimal` + currency code (USD/KRW). `double` 절대 금지
- `OrderId` 는 `UUID` v7 (시간 순서 보존)
- `cancel()` 은 `PAID` 이전에만 가능. `DELIVERED` 후 호출은 `IllegalStateException`

## 4. 이벤트 발행

- 도메인 이벤트는 *Spring Modulith Events* 사용
- *외부 시스템* 으로 가는 이벤트는 *Outbox pattern* 필수. `application/port/out/EventPublisher` 만 호출.
- *직접 KafkaTemplate.send() 절대 금지* (`@Transactional` 안 atomic 보장 안 됨)

## 5. *''*당신이 *AI 라면* 따라야 할 *5 가지 룰*''*

1. 새 파일 만들기 전에 *''*기존 구조의 *유사 파일* 을 *먼저 *참조*''*
2. *''*Spring annotation 을 `domain/` 에 *절대 추가하지 말 것*''*
3. *''*JPA `@Entity` 를 `application/` 에 *직접 import 하지 말 것*''*
4. *''*새 도메인 이벤트는 `OrderPlacedEvent` 같은 *기존 패턴* 따라 *record* 로 정의''*
5. *''*ArchUnit 룰 (`src/test/java/.../architecture/`) 을 *''*먼저 읽고''* 코드 짤 것''*

## 6. 검증 명령

```bash
./gradlew test                    # 모든 테스트 + ArchUnit
./gradlew :verify                 # Modulith boundary 검증
./gradlew spotlessApply           # 포맷
./gradlew dependencyAnalysis      # 의존 위반 분석
```

`git commit` 전에 위 4 개가 *모두 통과* 해야 합니다.

## 7. *추가 학습*

- `docs/adr/` — *''*왜 *이렇게 결정* 했는지''* 의 history
- `docs/context-map.md` — DDD ubiquitous language 사전
- `README.md` — 빌드·실행·로컬 환경
````

### 2.3. *왜 *Markdown* 인가*

- *AI 도구가 *''*가장 잘 읽는다''*''* (학습 데이터에 markdown 압도적)
- *사람도 *''*같은 파일을 본다''*''*
- *''*git diff 가 *의미 있는 단위*''*
- *''*GitHub 에서 *바로 렌더링*''*

## 3. *Spring Modulith 모듈 정의*

### 3.1. `package-info.java`

```java
@org.springframework.modulith.ApplicationModule(
    displayName = "Order Management",
    allowedDependencies = { "shared::Money", "payment::PaymentApi" }
)
package com.example.order;
```

*''*이 한 줄이 *''*''*다른 패키지가 *order 내부 *직접 import 금지*''*''*''* 를 *''*컴파일 타임에 강제* — 단 `shared::Money` 와 `payment::PaymentApi` 만 허용*. *''*Modulith 가 *''*다른 모듈은 *''*공개 인터페이스 (`PaymentApi` 같은)*''*''* 만 보게 *강제*''*''*.

### 3.2. *Verify 테스트*

```java
class ModularityTest {
    @Test
    void verify_modules() {
        var modules = ApplicationModules.of(MyServiceApplication.class);
        modules.verify();   // ← 위반 있으면 fail
    }

    @Test
    void document() {
        var modules = ApplicationModules.of(MyServiceApplication.class);
        new Documenter(modules)
            .writeModulesAsPlantUml()
            .writeIndividualModulesAsPlantUml();
    }
}
```

*''*document 메소드가 *''*PlantUML 다이어그램을 *자동 생성*''*''*. *''*''*아키텍처 문서가 *코드와 *자동 sync*''*''*''* — *''*''*가장 *오래된 *''*문서 drift* 문제* 해결''*''*''*.

## 4. *ArchUnit* 핵심 5 규칙

### 4.1. *`HexagonalArchitectureTest.java`*

```java
@AnalyzeClasses(
    packagesOf = MyServiceApplication.class,
    importOptions = ImportOption.DoNotIncludeTests.class
)
class HexagonalArchitectureTest {

    @ArchTest
    static final ArchRule domain_must_not_depend_on_spring =
        noClasses().that().resideInAPackage("..domain..")
            .should().dependOnClassesThat().resideInAnyPackage(
                "org.springframework..",
                "jakarta.persistence..",
                "jakarta.servlet..",
                "org.hibernate.."
            )
            .because("도메인은 *''*어떤 프레임워크도 모름*''*. AGENTS.md §1 참조.");

    @ArchTest
    static final ArchRule application_must_not_use_jpa_directly =
        noClasses().that().resideInAPackage("..application..")
            .should().dependOnClassesThat().resideInAnyPackage(
                "jakarta.persistence..",
                "org.springframework.data.jpa.."
            )
            .because("application 은 *port 만* 통과. AGENTS.md §1.");

    @ArchTest
    static final ArchRule adapter_in_must_not_depend_on_adapter_out =
        noClasses().that().resideInAPackage("..adapter.in..")
            .should().dependOnClassesThat().resideInAPackage("..adapter.out..")
            .because("어댑터끼리 직접 통신 금지 — 도메인 통과해야 함.");

    @ArchTest
    static final ArchRule controllers_must_return_dto_not_domain =
        classes().that().resideInAPackage("..adapter.in.web..")
            .and().areAnnotatedWith(RestController.class)
            .should().notHaveSimpleNameEndingWith("DomainController")
            .because("도메인 객체를 *그대로 *직렬화 금지* — DTO 변환 필수.");

    @ArchTest
    static final ArchRule no_direct_kafka_template =
        noClasses().that().resideInAPackage("..application..")
            .should().dependOnClassesThat().haveNameMatching(".*KafkaTemplate.*")
            .because("Outbox pattern 통해야 함. AGENTS.md §4.");
}
```

### 4.2. *''*규칙은 *5 개에서 시작* 하라*''*

*''*'30 개 ArchUnit 룰 처음부터 박으면 *팀이 *반발*''*''*. *''*'5 개로 시작 → *3 개월마다 *1 개 추가''*''*. *''*'각 룰이 *''*왜 있는지*''* 를 *because 메시지* 에 *''*반드시* 박을 것*''*.

### 4.3. *''*ArchUnit + AGENTS.md 양방향 *링크***

- `AGENTS.md §1` 에서 *''*규칙을 *natural language* 로 설명*''*
- `HexagonalArchitectureTest.java` 의 `.because("AGENTS.md §1 참조")` 가 *''*검증 메시지에 *링크* 박음*''*

→ *''*AI 가 *''*위반 시 *왜 위반인지*''*''* 를 *''*AGENTS.md 참조 메시지로 *자동 학습*''*''*.

## 5. *PR Template* — `.github/pull_request_template.md`

```markdown
## 변경 요약
<!-- 무엇을, 왜 -->

## 헥사고날 체크리스트
- [ ] 도메인 (`domain/`) 에 Spring/JPA 추가 없음
- [ ] 새 유스케이스 = `application/port/in` 인터페이스 + `service/` 구현 *둘 다* 추가
- [ ] 새 외부 의존 = `application/port/out` 인터페이스 + `adapter/out` 구현 *둘 다* 추가
- [ ] 도메인 이벤트 = `record` 로 정의 + Modulith Events 또는 Outbox 통해 발행
- [ ] *적용 안 됨* — 위 1-4 가 무관한 변경이면 체크

## 테스트
- [ ] 단위 테스트 (`domain/`)
- [ ] 어댑터 테스트 (`adapter/`)
- [ ] ArchUnit 통과 (`./gradlew test`)
- [ ] Modulith verify 통과 (`./gradlew :verify`)

## ADR
- [ ] 이 변경이 *''*아키텍처 결정''* 을 *''*포함하면''* `docs/adr/000X-*.md` 추가
- [ ] *적용 안 됨*

## AI 사용
- [ ] Claude Code / Cursor 사용
- [ ] *''*AGENTS.md 의 룰 *모두 *준수*''*
- [ ] *''*AI 가 생성한 코드를 *내가 *읽고 이해함*''* (ownership 확인)
```

*''*''*AI 사용 섹션이 *명시되어 있는 게 핵심* — *''*'AI 가 짠 거''* 가 *''*'그래서 *내가 이해 못 해도 OK''* 의 *알리바이가 되지 않게''* 막는 *제도적 장치*.

## 6. CI Workflow — `.github/workflows/ci.yml`

```yaml
name: ci

on:
  pull_request:
  push:
    branches: [master, main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-java@v4
        with:
          java-version: "21"
          distribution: temurin
          cache: gradle

      - name: ArchUnit + unit tests
        run: ./gradlew test

      - name: Modulith verify + 다이어그램 생성
        run: ./gradlew :verifyModularity

      - name: 의존 위반 분석
        run: ./gradlew dependencyAnalysis

      - name: AGENTS.md 존재·신선도 check
        run: |
          test -f AGENTS.md || (echo "::error::AGENTS.md missing" && exit 1)
          # 마지막 commit 이 90 일 이상 전이면 stale 경고
          last=$(git log -1 --format=%ct -- AGENTS.md)
          now=$(date +%s)
          age_days=$(( (now - last) / 86400 ))
          if [ $age_days -gt 90 ]; then
            echo "::warning::AGENTS.md last updated $age_days days ago — review needed"
          fi

      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: modulith-diagrams
          path: build/spring-modulith-docs/
```

### 6.1. *''*''AGENTS.md 가 *''*1 급 시민*''*''* — *''*CI 에서 *존재·신선도까지* 검증*''*

*''*''*문서가 *코드와 같은 라이프사이클''* — *''*예전엔 *''*'문서 작성 후 *방치*''*''*. 이제는 *''*'AGENTS.md 변경 안 한 게 *3 개월 넘으면 *경고*''*''*.

## 7. *Agent 1 차 PR 리뷰* — `.github/workflows/agent-review.yml`

```yaml
name: agent-review

on:
  pull_request:
    types: [opened, synchronize]

jobs:
  review:
    runs-on: ubuntu-latest
    permissions:
      pull-requests: write
      contents: read
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Claude Code review
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          npx -y @anthropic-ai/claude-code review \
            --files "$(git diff --name-only origin/${{ github.base_ref }}...HEAD | tr '\n' ' ')" \
            --context AGENTS.md \
            --context docs/adr/ \
            --output review.md

      - name: PR 코멘트 게시
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const body = fs.readFileSync('review.md', 'utf-8');
            await github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: `🤖 *Claude 1 차 리뷰*\n\n${body}\n\n*인간 리뷰가 *최종 결정*. 본 코멘트는 *조언*.*`
            });
```

### 7.1. *''*Agent 가 *''*AGENTS.md + ADR 을 context 로 받는 것* 이 *핵심*''*

*''*'AGENTS.md 가 없는 코드베이스 → Agent 리뷰가 *''*'general advice'''*. *''*'AGENTS.md 있는 코드베이스 → Agent 가 *''*'우리 룰''* 로 *''*'우리 도메인 용어*''* 로 리뷰*''*.

### 7.2. *''*''인간이 *마지막 결정* — *''*명시*''*''*

PR 코멘트 마지막 줄 `*인간 리뷰가 *최종 결정*. 본 코멘트는 *조언*.* ` 이 *''*'agent 가 *책임지지 않는다''* 를 *''*'명시적 약속*''* 으로 박는다*.

## 8. *Reference Application* — *''*Order 도메인 예시*''*

### 8.1. *Domain Core* — `Order.java`

```java
package com.example.order.domain;

import java.time.Instant;
import java.util.UUID;

public record Order(
    OrderId id,
    CustomerId customerId,
    Money amount,
    OrderStatus status,
    Instant placedAt
) {
    public Order {
        if (amount.isNegativeOrZero()) {
            throw new IllegalArgumentException("amount must be positive");
        }
    }

    public static Order place(CustomerId customer, Money amount) {
        return new Order(
            new OrderId(UUID.randomUUID()),
            customer,
            amount,
            OrderStatus.PENDING,
            Instant.now()
        );
    }

    public Order pay() {
        if (!(status instanceof OrderStatus.Pending)) {
            throw new IllegalStateException("only PENDING can be paid");
        }
        return new Order(id, customerId, amount, OrderStatus.PAID, placedAt);
    }

    public Order cancel() {
        return switch (status) {
            case OrderStatus.Pending p -> new Order(id, customerId, amount, OrderStatus.CANCELLED, placedAt);
            case OrderStatus.Paid pd   -> new Order(id, customerId, amount, OrderStatus.CANCELLED, placedAt);
            case OrderStatus.Cancelled c -> throw new IllegalStateException("already cancelled");
            case OrderStatus.Delivered d -> throw new IllegalStateException("delivered orders cannot be cancelled");
        };
    }
}
```

*''*record + sealed interface OrderStatus + pattern matching''* 가 *''*'invariant 를 *컴파일러로 *부분 강제*''*.

### 8.2. *sealed* `OrderStatus.java`

```java
package com.example.order.domain;

public sealed interface OrderStatus
    permits OrderStatus.Pending,
            OrderStatus.Paid,
            OrderStatus.Cancelled,
            OrderStatus.Delivered {

    record Pending() implements OrderStatus {}
    record Paid() implements OrderStatus {}
    record Cancelled() implements OrderStatus {}
    record Delivered() implements OrderStatus {}
}
```

*''*'새 상태 추가 → ADR 작성 강제*''* (sealed 가 *''*'다른 곳에서 implement 못 함*''*).

### 8.3. *Port In* — `PlaceOrderUseCase.java`

```java
package com.example.order.application.port.in;

import com.example.order.domain.*;

public interface PlaceOrderUseCase {
    PlaceOrderResult execute(PlaceOrderCommand cmd);

    record PlaceOrderCommand(
        CustomerId customerId,
        Money amount,
        IdempotencyKey idempotencyKey
    ) {}

    record PlaceOrderResult(OrderId orderId) {}
}
```

### 8.4. *Application Service*

```java
package com.example.order.application.service;

import com.example.order.application.port.in.PlaceOrderUseCase;
import com.example.order.application.port.out.*;
import com.example.order.domain.*;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class PlaceOrderService implements PlaceOrderUseCase {

    private final LoadOrderPort loadOrder;
    private final SaveOrderPort saveOrder;
    private final EventPublisher eventPublisher;

    public PlaceOrderService(
        LoadOrderPort loadOrder,
        SaveOrderPort saveOrder,
        EventPublisher eventPublisher
    ) {
        this.loadOrder = loadOrder;
        this.saveOrder = saveOrder;
        this.eventPublisher = eventPublisher;
    }

    @Override
    @Transactional
    public PlaceOrderResult execute(PlaceOrderCommand cmd) {
        var existing = loadOrder.findByIdempotencyKey(cmd.idempotencyKey());
        if (existing.isPresent()) {
            return new PlaceOrderResult(existing.get().id());
        }

        var order = Order.place(cmd.customerId(), cmd.amount());
        saveOrder.save(order, cmd.idempotencyKey());

        eventPublisher.publish(new OrderPlacedEvent(
            order.id(),
            order.customerId(),
            order.amount()
        ));

        return new PlaceOrderResult(order.id());
    }
}
```

*''*'`@Transactional + Idempotency-Key + Outbox EventPublisher''* — *''*'복잡 결제 도메인 정합성의 *3 박자*''*.

## 9. *측정* — DORA + agent-specific metric

### 9.1. *DORA 4* + 확장

| 지표 | 측정 |
|---|---|
| Deployment Frequency | GitHub Actions success rate / day |
| Lead Time for Change | PR open → merge |
| Change Failure Rate | rollback / incident |
| MTTR | incident open → close |

### 9.2. *Agent-specific metric* (2026 신규)

| 지표 | 측정 |
|---|---|
| **Agent 1 차 통과율** | 인간 리뷰어가 *agent 코멘트와 *반대 결정* 한 비율* — 낮을수록 *agent 가 *팀 표준 정확히 반영*''* |
| **ArchUnit fail/PR ratio** | *''*'PR 당 ArchUnit 위반 횟수''* — *''*'AGENTS.md 가 *AI 에 잘 전달되는지* 지표*''* |
| **AGENTS.md update frequency** | *''*'분기당 변경 수''* — *''*'표준이 *살아있는지* 척도*''* |
| **First-week onboarding velocity** | *''*'신입의 *첫 1 주 PR merge 수*''* — *''*'reference template 의 *진짜 가치'''*''* |

## 10. *흔한 함정* + 운영 노하우

### 10.1. *''*'ArchUnit 룰을 *처음부터 많이* 박지 마라''*

*''*'5 개 → 3 개월마다 1 개 추가''*. *''*'팀이 *룰에 익숙해진 뒤* 다음 룰''*. *''*'30 개로 시작하면 *''*'AI 가 못 통과해서 *AI 자체를 안 씀*''*''*.

### 10.2. *''*'AGENTS.md 길이 *2,000 자 이하* 유지''*

*''*'AI 가 *''*'1 차 read 로 *맥락 잡는다*''*''*. *''*'2,000 자 넘으면 *모델이 *''*'후반부를 *잘 안 본다*''*''*''*. *''*'세부 룰은 *링크로 *별도 문서*''*. AGENTS.md 는 *''*'index 역할*''*.

### 10.3. *''*'ADR 을 *''*'시니어가 다 쓰지 마라*''*''*

*''*'주니어가 *''*'ADR 초안 쓰고''* *시니어가 *리뷰*''*. *''*'결정의 *맥락 학습 = 가장 빠른 시니어 성장 경로''*. *''*'ADR review 가 *''*'팀 합의의 *공식 단계*''*''*.

### 10.4. *''*'Spring Modulith 의 *event publication registry 를 *꺼두지 말 것*''*

*Modulith 의 *''*'@ApplicationModuleListener''* 가 *''*'event 발행 *영속화 (publish/complete)''* 를 *자동 추적*''*. *''*'실패 시 *재시도*''* 가능*. *''*'설정 한 줄 (`spring.modulith.events.completion-mode=update`) 로 *''*'복원력 +1''*''*.

### 10.5. *''*'AI 가 *제시한 ADR 을 *그대로 *commit 하지 마라*''*

*''*'ADR 은 *''*'사람의 결정 기록''*''*. *''*'AI 가 *''*'후보 정리 + 비교 표 그리기*''* 까지는 OK*. *''*'결정은 *사람*''*. *''*'서명 (Author 필드) 도 *사람*''*.

## 11. 결론 — *''*'표준은 *문서가 아니라 *artifact*''*''*

처음에 말한 *''*'표준은 *artifact 가 *있어야* 표준*''*''* 으로 돌아가자. *''*'좋은 글, 좋은 PT, 좋은 talk''* — *''*'이 *3 가지로는 *팀이 *변하지 않는다*''*''*. *''*'코드베이스의 *''*'CI 가 fail* 하고''* *''*'PR template 의 체크박스가 *''*'비어있는 게 보이고''*''* *''*'archetype 한 줄이 *''*'표준 구조를 *물리적으로 박는*''*''*''* — *''*'이 *3 가지가 모이면 *팀이 변한다*''*''*.

**AGENTS.md** 는 *''*'AI 가 *우리 룰을 이해하게* 만드는 *진입점*''*. **ArchUnit** 은 *''*'룰을 *컴파일러 수준에서 *강제*''*. **Spring Modulith** 는 *''*'경계를 *물리적으로 박음*''*. **PR template + Agent review** 는 *''*'사람과 AI 의 *''*'협력 의례*''*''*. 다섯이 *''*'한 코드베이스에 *동시 작동*''* 하면 *''*'복잡 도메인이 *''*'AI 시대에도 안전하게 확장*''*''*.

> *''*'시니어의 일은 *''*'자기 머릿속의 결정 기준을 *''*'코드베이스의 artifact 로 *외화 (externalize) 하는 것''*''*. *''*'AI 시대엔 *''*'그 외화의 *수신자가 사람만이 *아니다*''*''*''*. *''*'그래서 *''*'2026 년 시니어의 출력물 = AGENTS.md + ArchUnit + ADR + Reference App''*''*''*.

*''*'복사해서 *오늘 *시작하세요*''*''*. 위 디렉토리 구조 그대로, AGENTS.md 본문 그대로, ArchUnit 5 규칙 그대로. *''*'완벽한 표준은 *없다''*. *''*'시작된 표준이 *완벽으로 진화한다''*. 시작 안 한 표준은 *''*'영원히 0*''*.

---

## 더 읽을 거리

- *Spring Modulith Reference* — *https://docs.spring.io/spring-modulith/reference/*
- *ArchUnit User Guide* — *https://www.archunit.org/userguide/*
- *AGENTS.md 표준 (community)* — *https://agents.md/* (2025 정착)
- *Anthropic Claude Code Documentation* — *https://docs.anthropic.com/claude-code/*
- *Cursor Rules Documentation* — *https://docs.cursor.com/rules*
- *Get Your Hands Dirty on Clean Architecture* — Tom Hombergs (Reactive Publishing) — 헥사고날 자바 실전서 *''*'표준''*''*
- *Building Evolutionary Architectures* — Ford, Parsons, Kua — Fitness Function 개념의 표준서
- *Domain Storytelling* — Stefan Hofer & Henning Schwentner — ubiquitous language 시각화 도구

*시리즈 마무리: 이 글로 *''*'백엔드 시니어의 *AI 시대 *방법론 정립 + 구조 표준''*''* 시리즈 (5/29 7 편) 완료. 다음은 *''*'AI 에이전트 *팀 도입 후 6 개월 후기*''* — 무엇이 변하고 무엇이 *''*'안 변했는지*''*''*.
