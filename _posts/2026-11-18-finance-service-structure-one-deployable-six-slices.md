---
layout: post
title: "finance-service 구조 — 배포 단위는 하나, 서로를 모르는 도메인은 여섯"
date: 2026-11-18 23:27:58 +0900
categories: [Architecture, MSA]
tags: [settlement, finance-service, modular-monolith, archunit, hexagonal, kafka, outbox, msa]
---

[지난 글](/2026/10/28/finance-service-bank-atm-money-domain-essence/)에서는 정산 플랫폼 Lemuel 의 `finance-service` 안에 든 금융 도메인 여섯 개(계정계·대출·법인카드·보험·투자·평판)를 *무엇을 하는가* 의 관점에서 읽었다. 이번엔 *어떻게 들어 있는가* 를 본다.

한 줄로 요약하면 이렇다. **여섯 도메인은 한 JVM, 한 배포 단위 안에 있지만 서로의 코드를 단 한 줄도 import 하지 않는다.** 그리고 그 "안 한다"는 습관이 아니라 테스트가 강제한다.

아래 수치는 모두 settlement 리포 `develop` 브랜치 커밋 `7d5d660d`(2026-10-29) 기준으로 직접 센 것이다. main 자바 파일 960개, 테스트 373개다.

## 1. 원래는 서비스 여섯 개였다

처음부터 이렇게 생긴 건 아니다. 대출(loan)·카드(card)·보험(insurance)·예치(deposit)·투자(investment)·계정계(account)는 원래 **각각 독립된 마이크로서비스** 였다. 근거는 "커머스 플랫폼이 셀러에게 대출·카드·보험을 *겸영* 하는 그룹사"라는 사업 전제였고, 그 전제에서는 상품마다 인허가가 다르니 서비스를 쪼개는 게 맞았다.

2026-08-24 의 설계 결정 기록(ADR 0039, 리포 내부 문서)이 그 전제를 뒤집었다. 이 제품은 겸영 금융사가 아니라 **정산 SaaS** 이고, 고객 자금을 보유하지 않으며, 모든 금융 기능은 *취급* 이 아니라 *연계* 다. 인허가를 가진 주체가 우리가 아니면 "규제 때문에 쪼갠다"는 근거가 사라진다.

전제만 보고 합치지는 않았다. 실제 결합도를 쟀다. ADR 에 남은 조사표를 옮기면, 금융 서비스끼리 주고받는 이벤트 간선 수는 이랬다.

| 서비스 | 다른 금융 서비스로부터 받는 간선 | 실제 상류 |
|---|---:|---|
| insurance | 0 | 외부 보험사 전문 |
| loan | 0 | settlement, company |
| investment | 0 | settlement |
| deposit | 0 | settlement, payout |
| card | 0 | organization, company, 자기 토픽 |
| account | 7 | loan 6 + investment 1 (그 외 settlement·order·payout) |

다섯 개는 **서로 이벤트를 한 건도 주고받지 않았다.** ADR 의 표현을 빌리면 "현행 6분할은 결합도가 아니라 도메인 이름 유사성으로 그어져 있었다." 그래서 단계적으로 합쳤다. deposit 은 settlement 로 가고, 나머지가 `finance-service` 로 모였고, 이후 company-service 를 해체하면서 평판(reputation)이 합류했다(ADR 0044).

마틴 파울러가 [MonolithFirst](https://martinfowler.com/bliki/MonolithFirst.html)에서 말한, 경계를 모르는 채로 먼저 쪼개는 위험을 *반대 방향* 에서 수습한 셈이다. 다만 이건 단일체로 *되돌아간* 게 아니다. 합친 건 배포 단위이고, 도메인 경계는 그대로 남겼다. 그게 이 글의 나머지 내용이다.

## 2. 디렉터리 모양

`github.lms.lemuel` 아래 최상위 패키지가 일곱 개다.

| 패키지 | 자바 파일 | 내용 |
|---|---:|---|
| `loan` | 213 | 대출(선정산·담보·기업대출) |
| `card` | 176 | 법인카드·승인·영수증 매칭 |
| `insurance` | 176 | 보험 청약·보험사 연계 |
| `account` | 159 | 계정계(GL) + `banking/`(연금·적금·정기예금) |
| `investment` | 115 | 투자 주문·체결 |
| `reputation` | 90 | 기업 평판 판정 |
| `finance` | 30 | **중립 패키지** — 어느 도메인의 것도 아닌 공용 계약 |

여섯 도메인 패키지(코드 주석의 용어로 *슬라이스*)는 모두 같은 헥사고날 골격을 따른다.

```
card/
  domain/        ← 순수 도메인 (Card, AuthorizationHold, CardLimitPolicy …)
  application/
    port/in/     ← 유스케이스 인터페이스
    port/out/    ← 저장·발행 등 바깥으로 나가는 포트
    service/     ← 유스케이스 구현
  adapter/
    in/web, in/kafka     ← REST 컨트롤러, Kafka 컨슈머
    out/persistence, out/event
  config/
```

여기까지는 흔한 구조다. 흥미로운 건 슬라이스 *사이* 의 규칙이다.

## 3. 규칙 ① 슬라이스는 서로를 import 하지 않는다

슬라이스 간 import 를 전 조합으로 세 봤다.

```
account -> finance : 1 files
loan    -> finance : 4 files
card    -> finance : 1 files
investment -> finance : 3 files
reputation -> finance : 2 files
(슬라이스 → 다른 슬라이스 : 0)
```

**슬라이스끼리는 0건이다.** 바깥으로 나가는 의존은 전부 중립 패키지 `finance` 로만 향하고, 그 내용도 세 가지뿐이다.

- `finance.externaldata` — 외부 시세·기업정보 스냅샷과 "스냅샷이 너무 오래됐다"는 예외
- `finance.funding.SellerFundingProvider` — 셀러 재원 조회 계약
- `finance.projection` — 이벤트 순서 역전 방지용 체크포인트

이걸 지키는 게 `FinanceArchitectureTest` 다. [ArchUnit](https://www.archunit.org/userguide/html/000_Index.html)으로 네 가지를 검사한다.

1. 어느 슬라이스도 다른 슬라이스에 의존하지 않는다 (**전 조합**)
2. 중립 패키지 `finance..` 는 어느 슬라이스에도 의존하지 않는다
3. 계정계는 Outbox 발행 머시너리에 의존하지 않는다 (아래 규칙 ③)
4. finance 모듈 전체가 order·settlement 코드에 의존하지 않는다

1번을 쌍마다 따로 쓰지 않고 슬라이스 목록을 도는 데는 이유가 있다. 테스트 주석이 이렇게 설명한다. "슬라이스가 늘 때 규칙을 추가하는 것을 잊으면 새 슬라이스만 무방비가 된다. 목록 한 줄만 고치면 전 조합이 닫힌다."

왜 테스트로까지 막느냐는 질문의 답도 같은 주석에 있다. **같은 모듈 안에 있으면 컴파일러가 막지 않는다.** 서비스가 따로일 때는 다른 서비스의 클래스를 import 하려 해도 클래스패스에 없으니 컴파일 자체가 안 됐다. 합치는 순간 그 물리적 장벽이 사라지고, "편의상 한 줄 import 하는 순간 두 도메인이 엉키고 재분할 경로가 닫힌다." 합치면서 잃은 컴파일러의 보호를 테스트가 대신 맡는 구조다.

[Spring Modulith](https://docs.spring.io/spring-modulith/reference/fundamentals.html)가 "애플리케이션 모듈" 경계를 검증하는 것과 같은 발상이다. 다만 이 리포는 Modulith 를 쓰지 않고 ArchUnit 규칙을 직접 썼다.

### 가드가 공허하게 통과하지 않는다는 것부터 증명한다

이 테스트에서 가장 마음에 드는 부분은 규칙보다 앞에 있는 **자기검증** 이다.

```java
@Test
@DisplayName("[자기검증] 모든 슬라이스의 클래스를 실제로 임포트했다")
void importsEverySlice() {
    for (String slice : SLICES) {
        long n = financeClasses.stream()
                .filter(c -> c.getPackageName().startsWith("github.lms.lemuel." + slice)).count();
        assertThat(n).as("%s 슬라이스 클래스를 하나도 못 읽었다 — 가드가 무력화된 상태다", slice).isPositive();
    }
}
```

ArchUnit 은 검사 대상 클래스가 0개면 "위반 없음"으로 통과할 수 있다. 이 리포는 실제로 그 함정을 밟았다. ArchUnit 1.3.0 이 Java 25 바이트코드를 읽지 못해 클래스를 조용히 건너뛰었고, 아키텍처 테스트가 초록인 채로 아무것도 검사하지 않고 있었다. 지금 빌드는 1.4.1 이고, 그때의 교훈이 이 자기검증으로 남았다. **초록불이 "검사했는데 문제없다"인지 "아무것도 안 봤다"인지를 먼저 가린다.**

## 4. 규칙 ② 같은 JVM 인데도 Kafka 로 말한다

슬라이스끼리 import 를 못 하면 데이터는 어떻게 주고받을까. 대부분은 **Kafka 이벤트** 다.

법인카드가 좋은 예다. 카드 한도를 정하려면 기업 평판 등급이 필요한데, 평판은 같은 프로세스 안의 `reputation` 슬라이스가 판정한다. 그래도 카드는 `reputation` 을 부르지 않는다.

- `reputation` 이 등급이 바뀌면 `company-reputation-changed` 이벤트를 발행하고,
- `card` 의 `CompanyReputationChangedConsumer` 가 그걸 받아,
- 카드 자기 테이블(`ReputationProjectionJpaEntity`)에 **사본(projection)** 을 적재한다.
- 등급 enum 도 `card/domain/ReputationGrade` 로 카드가 자기 것을 따로 갖고 있다.

같은 JVM 안에서 메시지 브로커를 한 바퀴 도는 건 낭비처럼 보인다. 하지만 이 덕분에 `card` 는 `reputation` 이 *같은 프로세스에 있는지조차 모른다.* 나중에 둘을 다시 다른 서비스로 떼어 내도 카드 코드는 바뀔 게 없다.

### 예외: 재원 조회는 프로세스 내부 호출로 바꿨다

반대 방향의 결정도 있다. 카드가 결제를 승인하려면 셀러 재원을 계정계에 물어봐야 한다(폴백 없이 실패하면 거절하는 fail-closed 조회다). 계정계가 같은 프로세스로 들어온 뒤에도 이 호출은 한동안 **HTTP 루프백** — `localhost:8084`, 즉 같은 JVM 의 자기 자신 — 으로 남아 있었다.

ADR 0039 의 후속 기록(2026-08-26)은 이걸 이렇게 정리했다. 프로세스가 하나이니 그 왕복이 주는 장애 격리는 0이고, 남는 건 직렬화·타임아웃·재시도·공유키 검증 비용뿐이다. 그래서 중립 계약 `finance.funding.SellerFundingProvider` 를 두고, 카드는 그 인터페이스를, 계정계는 그 구현을 향하게 바꿨다.

이 기록의 핵심 문장이 이 구조 전체를 설명한다.

> 경계를 만드는 것은 전송 수단이 아니라 의존 방향이다.

HTTP 든 Kafka 든 메서드 호출이든, 카드와 계정계가 *서로가 아니라 계약을* 향하고 있으면 경계는 살아 있다. 그래서 재분리 경로도 닫히지 않았다. 계정계의 REST 표면(`GET /internal/account/sellers/{id}/funding`)은 그대로 남겨 뒀고, 다시 쪼개야 하면 같은 계약을 구현하는 HTTP 어댑터를 카드 쪽에 되돌려 끼우면 된다.

평판은 이벤트로, 재원은 직접 호출로 다르게 간 것은 성격이 다르기 때문으로 읽힌다. 평판은 *상태가 바뀌었다는 알림* 이라 늦게 반영돼도 되는 데이터이고, 재원은 *지금 결제를 승인해도 되느냐* 는 동기 질의라 응답을 기다려야 한다. (재원 쪽 근거는 ADR 에 명시돼 있고, 평판이 왜 이벤트로 남았는지를 따로 적은 문장은 찾지 못했다. 이 문단의 해석은 내 것이다.)

## 5. 규칙 ③ 계정계는 듣기만 한다

Kafka 컨슈머 파일 수를 슬라이스별로 세면 한쪽으로 크게 기운다.

| 슬라이스 | `@KafkaListener` 파일 |
|---|---:|
| account | 20 |
| card | 8 |
| loan | 4 |
| investment | 2 |
| reputation | 2 |
| insurance | 1 |

계정계(account)는 정산 확정·취소·조정, 대출 실행·상환, 투자 체결, 지급 완료, 포인트·상품권 이벤트까지 받아 **복식부기 분개** 로 옮긴다. 그런데 반대로 **발행은 금지돼 있다.** ArchUnit 규칙 3번이 계정계 패키지가 Outbox 발행 포트(`common.outbox.application`, `common.outbox.adapter.out`)에 의존하는 것을 막는다.

이유는 회계의 **직무분리** 다. 테스트 주석은 이렇게 쓴다. "장부에 *기록되는* 업무 시스템과 장부를 *기록하는* 원장이 같은 주체가 되면 직무분리가 깨진다." 대출을 실행한 쪽이 그 대출의 분개까지 스스로 쓰면 검증할 사람이 없어진다.

이 규칙은 합치면서 잃은 걸 메우려고 생겼다. 계정계가 독립 서비스였을 때는 컴포넌트 스캔에서 Outbox 패키지를 아예 빼 버려, 발행 포트가 *컨텍스트에 존재하지 않았다.* 주입하고 싶어도 할 수 없었다. finance-service 에서는 loan·investment 가 Outbox 로 발행해야 하니 스캔이 전역이고, 그 빈 수준의 방어가 사라졌다. 이제 계정계가 발행 포트를 주입하지 못하게 막는 건 이 ArchUnit 규칙과 별도 정적 검사 스크립트(`guard.mjs` 의 `ACCOUNT-CONSUME-ONLY`) 둘뿐이다. 테스트 주석의 한 줄이 정확하다. "배포 단위를 합친 것과 통제를 푼 것은 다른 일이다."

발행하는 쪽의 방식은 [Transactional Outbox](https://microservices.io/patterns/data/transactional-outbox.html) 패턴이다. 업무 데이터와 "보낼 이벤트"를 같은 DB 트랜잭션에 쓰고, 별도 폴러가 브로커로 내보낸다.

## 6. 규칙 ④ 공용 패키지도 슬라이스를 모른다

중립 패키지 `finance` 는 슬라이스들이 기대는 곳이므로, 반대로 이 패키지가 어느 슬라이스를 import 하면 순환이 생긴다. ArchUnit 규칙 2번이 그걸 막는다.

`finance.projection.JpaProjectionOrderSequencer` 에는 공용 코드를 *어디에* 두느냐에 대한 판단이 하나 더 있다. 이벤트 순서가 뒤집혀 들어올 때 옛 이벤트를 버리는 규칙은 서비스 공통 라이브러리 `shared-common` 이 갖고 있는데, 그 체크포인트를 *저장하는* JPA 엔티티는 일부러 finance-service 안에 뒀다. 엔티티를 공통 라이브러리에 넣으면 그 라이브러리를 엔티티 스캔하는 **모든** 서비스가 그 테이블을 가져야 하고(`ddl-auto=validate` 가 테이블이 없으면 기동을 끊는다), 이 기능을 쓰지 않는 서비스까지 마이그레이션을 강요받는다. 주석의 결론은 이렇다. **규칙은 한 벌, 저장은 쓰는 서비스에만.**

같은 클래스는 억제한 이벤트 수를 메트릭으로 남긴다. 순서 역전을 "조용히 잘 막고 있는 것"과 "상류가 계속 뒤집혀 오는 것"은 겉으로 똑같이 보여서, 세지 않으면 후자를 영영 못 본다는 이유다.

## 7. 합쳐서 새로 생긴 비용

구조가 깔끔하다고 공짜는 아니다. 서비스 여섯 개를 하나로 합치면서 생긴 비용도 같이 적는다.

- **경계를 컴파일러가 아니라 테스트가 지킨다.** 테스트가 안 돌거나 공허하게 통과하면 경계는 조용히 무너진다. 자기검증을 넣은 이유이고, 이 테스트가 CI 에서 실제로 도는지가 곧 경계의 생명줄이다.
- **빈 수준 방어가 사라졌다.** 규칙 ③처럼 예전엔 "아예 존재하지 않아서" 못 하던 것을 이제는 "규칙으로 금지해서" 못 한다. 같은 통제를 더 약한 수단으로 유지하는 셈이다.
- **장애 도메인이 하나가 됐다.** 보험 슬라이스의 메모리 누수가 같은 파드의 카드 승인까지 같이 죽일 수 있다. 서비스가 따로일 때는 없던 위험이다.
- **사본 테이블이 늘었다.** 이벤트로 주고받는 대가로 카드는 평판 사본을, 계정계는 각 도메인의 사건을 따로 들고 있다. 사본은 원본보다 늦고, 그 지연을 감수하는 설계여야 한다.
- **DB 하나에 마이그레이션 47개가 섞였다.** `V1__loan_core.sql` 같은 정수 번호부터 `V20260715…` 타임스탬프 번호까지, 여러 도메인의 스키마 변경이 한 Flyway 이력에 쌓여 있다. [Database per Service](https://microservices.io/patterns/data/database-per-service.html) 원칙에서 멀어진 것이고, 다시 쪼갤 때 가장 손이 많이 갈 부분이다.

## 정리

`finance-service` 는 마이크로서비스를 모놀리스로 되돌린 게 아니라, **배포 단위와 도메인 경계를 분리해서 생각한 결과** 다. 결합도를 재 보니 서로 얘기하지 않는 도메인들이었고, 그래서 한 프로세스에 넣었다. 대신 다음 네 가지를 테스트로 박아 뒀다.

1. 슬라이스는 서로를 import 하지 않는다.
2. 필요한 건 이벤트로 받거나, 중립 계약을 향한다.
3. 장부는 듣기만 하고 쓰지 않는다.
4. 공용 패키지는 누구의 것도 아니다.

이 규칙들이 지키는 건 지금의 깔끔함보다 **나중의 선택지** 다. ADR 0039 는 사업 전제가 다시 겸영으로 뒤집히면 재분할이 정답이 된다고 적어 두었고, 그때 비용을 결정하는 게 이 경계라고 했다. 합칠 때 쪼갤 길을 열어 두는 것, 그게 이 구조의 요점이다.

## References

1. Martin Fowler. *MonolithFirst* (2015). [martinfowler.com](https://martinfowler.com/bliki/MonolithFirst.html)
2. ArchUnit. *User Guide.* [archunit.org](https://www.archunit.org/userguide/html/000_Index.html)
3. Spring Modulith. *Reference — Fundamentals (Application Modules).* [docs.spring.io](https://docs.spring.io/spring-modulith/reference/fundamentals.html)
4. Chris Richardson. *Pattern: Transactional outbox.* [microservices.io](https://microservices.io/patterns/data/transactional-outbox.html)
5. Chris Richardson. *Pattern: Database per service.* [microservices.io](https://microservices.io/patterns/data/database-per-service.html)
6. settlement 리포 내부 문서 (비공개): ADR 0039 *금융 6서비스 코어/부가 2계층 재편* (2026-08-24, 후속 2026-08-26), ADR 0044 *company 3분할*, `FinanceArchitectureTest.java`, `JpaProjectionOrderSequencer.java` — `develop@7d5d660d` 기준.
7. 이전 글: [정산 SaaS 안의 금융 모델 여섯 개 — 은행·ATM·돈의 관점에서 다시 본 각 도메인의 본질](/2026/10/28/finance-service-bank-atm-money-domain-essence/) (2026-10-28)
