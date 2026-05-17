---
layout: post
title: "정산 관리자 페이지가 빈 화면이 된 이유 — MSA 전환 중간 단계가 만든 4층 도미노"
date: 2026-05-17 22:00:00 +0900
categories: [backend, msa]
tags: [postmortem, msa, monolith-to-microservice, spring-boot, hibernate, gradle, flyway, postmortem, troubleshooting, ci-cd, deployment]
---

저녁 10시 반, 텔레그램에 한 줄짜리 신고가 들어왔다.

> **"정산에 왜 데이터가 없어?"** — `https://[운영-도메인]/admin/settlement`

페이지를 열어보면 깔끔하게 빈 테이블. 첫 번째 가설은 "권한 문제" 였지만, **DB 에는 정산 레코드가 1,310 건이 멀쩡히 들어 있었다**. 그때부터 한 시간 반 동안 4개 층을 거꾸로 파헤치는 디버깅이 시작됐고, 마지막엔 자정을 넘어서까지 hotfix 3회·PR 3건이 나왔다. 그 과정에 묻혀 있던 함정들이 너무 흥미로워서 글로 남긴다.

> 이 글에서 다루는 것
> - 빈 화면 1개에서 시작해 **컨트롤러 → SQL → JPA → 배포 파이프라인**까지 4개 층을 거꾸로 추적하는 절차
> - 모놀리스 → MSA 부분 분리 중 등장하는 *"의도한 분리가 배포 파이프라인을 통과하지 못한"* 함정
> - Gradle `bootJar` 비활성 + `jar` 활성으로 모듈을 "임시 library" 로 묶어 모놀리스가 흡수하는 패턴
> - `@EntityScan` 가 root-package auto-scan 을 막아주지 않는다는 미신
> - Squash merge 가 만들어내는 develop ↔ main commit divergence 와 hotfix 브랜치 전략
> - 도메인 enum 이 진화한 뒤 프론트엔드가 **수 년 묵은 레거시 상태값**을 그대로 들고 있을 때 벌어지는 일

---

## TL;DR

| 층 | 증상 | 진짜 원인 | 수정 |
|---|---|---|---|
| 1 | 프론트 admin 페이지 빈 테이블 | `/api/settlements/search` 가 404 — Spring `NoResourceFoundException` | 모놀리스 build 에 settlement 모듈 의존 추가 + scan packages 확장 |
| 2 | 같은 SQL을 직접 던지면 `relation "settlements" does not exist` | JDBC search_path = `"$user", public` 인데 실제 테이블은 `opslab` 스키마 | SQL FROM 절에 `opslab.` 스키마 prefix 명시 |
| 3 | 새 이미지가 `CrashLoopBackOff` — `Schema validation: missing table [ledger_entries]` | 같이 묶여온 신규 ledger 도메인 entity 가 prod 에 없는 테이블 검증 시도 | `@EntityScan` + `@EnableJpaRepositories` 명시로 ledger 패키지 제외 |
| 4 | develop → main PR 이 충돌 표시 | 이전 PR 의 squash merge 로 commit SHA 가 분기, develop 의 옛 커밋을 다시 replay 시도 | main 직접 hotfix 브랜치로 cherry-pick |

추가로 — **프론트 상태 필터 enum 이 백엔드와 완전 불일치**해서 필터를 켜면 빈 결과만 나오던 잔존 버그를 다음 라운드에 정리. 백엔드 도메인은 자동 전이 모델 (`REQUESTED → PROCESSING → DONE|FAILED|CANCELED`) 로 진화한지 오래인데 프론트는 옛 승인 워크플로우 enum (`CALCULATED/WAITING_APPROVAL/APPROVED/REJECTED`) 을 그대로 들고 있었다.

---

## 0. 사건 시작점 — DB 에는 1,310 건이 있는데 화면은 텅 비었다

가장 먼저 한 일은 가설을 둘로 갈라본 것이다.

1. **데이터가 없다** — DB 가 진짜 비었거나, 필터링/조인이 다 떨궈낸다
2. **데이터가 있는데 못 받는다** — 인증/네트워크/엔드포인트 문제

DB 접속해 직접 카운트 — `1,310건`. 가설 1 탈락. 그러면 가설 2. 프론트는 어떤 API 를 호출하는지부터 봤다.

```typescript
// SettlementAdmin.tsx
const response = await settlementApi.search(filters);
// → GET /api/settlements/search
```

직접 쳐봤다.

```bash
$ curl -s "/api/settlements/search?page=0&size=2" -w "%{http_code}\n"
401
```

401. 로그인 토큰을 발급받아 다시 요청.

```bash
$ TOKEN=$(curl -X POST .../auth/dev/auto-login?role=ADMIN | jq -r .token)
$ curl -s "/api/settlements/search?page=0&size=2" -H "Authorization: Bearer $TOKEN"
{"timestamp":"...","status":401,"error":"Unauthorized",...}
```

여전히 401. 토큰 발급은 200 인데 search 는 401. 이상하다.

여기서 직감했다 — **401 은 컨트롤러까지 도달하지 못한 응답**이거나, Spring Security 가 컨트롤러 부재로 인한 404 를 401 로 마스킹하고 있을 가능성. backend 로그를 봤다.

```json
{
  "level": "ERROR",
  "logger_name": "...GlobalExceptionHandler",
  "message": "[Exception] 처리되지 않은 예외 발생",
  "stack_trace": "NoResourceFoundException:
                  No static resource api/settlements/search
                  for request '/api/settlements/search'.
                  at ResourceHttpRequestHandler.handleRequest(...)
                  at DispatcherServlet.doDispatch(...)"
}
```

빙고. **컨트롤러가 등록되지 않아 DispatcherServlet 이 정적 리소스 핸들러로 fallback 한 것.** Spring Boot 의 표준 시그니처다.

## 1. 첫 번째 층 — 컨트롤러가 JAR 에 아예 없었다

소스 트리에서 `/api/settlements/search` 를 잡는 컨트롤러는 분명히 있었다.

```java
@RestController
@RequestMapping("/api/settlements")
public class SettlementSearchController {

    @GetMapping("/search")
    public ResponseEntity<SettlementPageResponse> search(...) { ... }
}
```

`@RestController` + `@RequestMapping` + `@GetMapping` 다 멀쩡. 배포된 git commit 에도 이 파일이 들어 있다. 그런데 왜 안 매칭되나?

배포 이미지의 JAR 안을 들여다봤다.

```bash
$ unzip -l /app/app.jar | grep -i "Settlement.*Controller"
(empty)

$ unzip -l /app/app.jar | grep "github/lms/lemuel/" | head -5
.../LemuelApplication.class
.../cart/...
.../order/...
.../payment/...
# settlement 패키지 자체가 없음
```

**JAR 안에 settlement 패키지가 통째로 없다.** 이게 1층의 진짜 원인이었다.

### 왜 이런 일이 생겼나

프로젝트는 모놀리스에서 MSA 로 전환하는 중이었다. 약 3주 전, 커밋 한 번에 도메인 코드를 모듈별로 재배치했다.

```
order-service/         # commerce 도메인 (user, order, payment, cart, ...)
settlement-service/    # 정산 도메인 (settlement, payout, chargeback, ...)
gateway-service/       # API gateway stub
```

각 모듈은 자기만의 `@SpringBootApplication` 진입점을 가졌다.
- `order-service/LemuelApplication` — 기존 모놀리스의 이름을 그대로 이어받음
- `settlement-service/SettlementServiceApplication` — 새로 생성

**의도**는 두 서비스를 분리 배포하는 것이었지만, **현실**의 CI / 헬름 차트는 아직 한 개의 배포만 빌드하고 있었다.

```yaml
# .github/workflows/ci.yml
build-args:
  MODULE=order-service   # ← settlement 는 빌드 자체에 빠져있었음
```

그리고 `LemuelApplication` 의 component scan 범위는 commerce 도메인만 포함하도록 좁혀져 있었다.

```java
@SpringBootApplication(scanBasePackages = {
    "github.lms.lemuel.user",
    "github.lms.lemuel.order",
    "github.lms.lemuel.cart",
    "github.lms.lemuel.payment",
    // ... settlement 없음
})
```

요약하자면 — **settlement-service 는 "곧 별도 배포될 예정"이라는 stub 만 만든 채로 어떤 컨테이너에도 실제로 적재되지 않고 떠 있었다.** MSA 의도는 절반만 완성된 상태였다. 그동안 *정산 페이지가 왜 작동했는지* 살펴보니 이전 모놀리스 시점의 잔여 캐시 + 운영자가 안 쓰던 페이지가 절묘하게 겹친 결과였다. 신고가 들어오기 전까지 아무도 몰랐다.

### 단기 수정 — Gradle 모듈을 임시 library 로 흡수

분리 배포까지 가는 길은 helm chart 신설, ArgoCD application 추가, post-deploy smoke 시나리오 보강 등 양이 많다. 운영 즉시 회복을 위해 **임시로 settlement-service 를 order-service 의 fat jar 에 번들하기로** 했다.

Spring Boot 모듈은 기본적으로 `bootJar` 플러그인이 활성화돼 있어 자체적으로 fat jar 를 만든다. 다른 Boot 모듈이 이걸 의존하면 *fat-in-fat* 이 되어 클래스 로딩이 깨진다. 그래서 dependency 로 쓰려면 일반 jar 모드로 바꿔야 한다.

```kotlin
// settlement-service/build.gradle.kts
// Library mode: settlement-service 는 order-service 의 fat jar 에 번들된다.
// MSA 분리 배포는 Phase B 에서 별도 helm chart + CI MODULE 로 재도입 예정.
tasks.named<org.springframework.boot.gradle.tasks.bundling.BootJar>("bootJar") {
    enabled = false
}
tasks.named<Jar>("jar") {
    enabled = true
    archiveClassifier.set("")
}
```

그리고 `SettlementServiceApplication.java` 는 그냥 삭제했다. `LemuelApplication` 이 유일한 entrypoint 가 돼야 두 개의 `@SpringBootApplication` 충돌을 피할 수 있다.

```kotlin
// order-service/build.gradle.kts
implementation(project(":settlement-service"))
```

```java
// order-service/LemuelApplication.java
@SpringBootApplication(scanBasePackages = {
    // ... 기존 commerce 도메인
    "github.lms.lemuel.settlement",
    "github.lms.lemuel.pgreconciliation",
    "github.lms.lemuel.payout",
    "github.lms.lemuel.chargeback",
    "github.lms.lemuel.ledger",  // ← 나중에 이 줄이 사고를 친다 (3층 참조)
})
```

로컬 `./gradlew :order-service:bootJar -x test` 통과. 새 JAR 안에 `SettlementSearchController.class` 가 정상 번들된 것 확인. 첫 번째 층 해결.

## 2. 두 번째 층 — SQL FROM 절이 스키마 prefix 를 빠뜨림

배포 전에 다른 함정도 있었다. 같은 폴더의 다른 JDBC adapter 들은 이렇게 쓰고 있었다.

```java
// DailyTotalsJdbcAdapter, SellerTierJdbcAdapter, ...
"FROM opslab.payments pay" +
"JOIN opslab.orders o ON o.id = pay.order_id" +
"JOIN opslab.products pr ON pr.id = o.product_id"
```

그런데 `SettlementSearchJdbcRepository` 만 unqualified.

```java
String fromClause =
    " FROM settlements s" +                       // ← 스키마 prefix 빠짐
    " JOIN orders o ON s.order_id = o.id" +
    " JOIN payments py ON s.payment_id = py.id" +
    " JOIN users u ON o.user_id = u.id" +
    " LEFT JOIN products pr ON o.product_id = pr.id" +
    where;
```

이게 왜 문제냐 — DB 가 다중 스키마 구조이고 애플리케이션 사용자의 `search_path` 가 `"$user", public` 으로 설정돼 있어서, `FROM settlements` 라고 쓰면 `public.settlements` 를 찾으러 간다. 실제 테이블은 `opslab.settlements` 에 있다.

```bash
$ psql -c "SHOW search_path;"
   search_path
-----------------
 "$user", public

$ psql -c "SELECT COUNT(*) FROM settlements s ...;"
ERROR:  relation "settlements" does not exist
```

JPA / Hibernate 가 만들어내는 쿼리는 `@Table(schema = "opslab", name = "settlements")` 어노테이션 기반으로 prefix 가 자동 붙는다. 그런데 **이 한 파일만 raw JdbcTemplate** 으로 짜여 있어서 누락된 것이다. 같은 폴더의 다른 형제 파일들과 비교만 했어도 30초 안에 잡혔을 일.

수정은 한 줄.

```java
String fromClause =
    " FROM opslab.settlements s" +
    " JOIN opslab.orders o ON s.order_id = o.id" +
    " JOIN opslab.payments py ON s.payment_id = py.id" +
    " JOIN opslab.users u ON o.user_id = u.id" +
    " LEFT JOIN opslab.products pr ON o.product_id = pr.id" +
    where;
```

이 두 가지 수정을 한 commit 으로 묶어 PR #1 (편의상 번호 가림). CI 3분 통과 → 머지. main 으로 가서 이미지 빌드 & 푸시. ArgoCD 동기화. 새 pod 가 떴다.

## 3. 세 번째 층 — `Schema validation: missing table [ledger_entries]`

새 pod 가 곧바로 `CrashLoopBackOff`. 4번 재시작. 로그를 봤다.

```json
{
  "level": "ERROR",
  "message": "Failed to initialize JPA EntityManagerFactory: ...
              org.hibernate.tool.schema.spi.SchemaManagementException:
              Schema validation: missing table [ledger_entries]"
}
```

문제는 두 가지가 겹쳐 있었다.

### (a) 같이 묶여온 신규 도메인 — ledger

내가 1층에서 `LemuelApplication` 의 scan 에 `github.lms.lemuel.ledger` 도 추가했었다. 그러면서 develop 에 미리 merge 돼 있던 *원장 도메인 Phase 1* 커밋이 함께 main 으로 흘러들어갔다. 이 도메인은 새로운 entity `LedgerEntryJpaEntity` 를 `opslab.ledger_entries` 테이블에 매핑한다.

### (b) Flyway 버전 충돌의 잔재

`order-service/src/main/resources/db/migration/V45__create_ledger_entries.sql` 이라는 migration 파일이 있긴 있었다. 그런데 prod DB 의 Flyway 히스토리는 이미 이렇게 돼 있었다.

| version | description | success |
|---|---|---|
| 45 | add settlement failure reason | t |
| 46 | add settlement failure reason | t |

V45 가 이미 다른 마이그레이션으로 적용돼 있었다. 옛 `V10`/`V12` 중복 정리 때 V45/V46 슬롯을 재사용한 흔적이 남은 것. **Flyway 는 같은 version 번호를 두 번 실행하지 않는다.** "Schema 'opslab' is up to date. No migration necessary." 한 줄과 함께 ledger_entries 마이그레이션은 영영 건너뛰어졌다.

결과: 테이블이 없는데 entity 가 있다 → Hibernate `ddl-auto: validate` 가 발견 → 빈 초기화 실패 → 컨텍스트 refresh 취소 → 앱 종료 → CrashLoopBackOff.

### 미신 — `@EntityScan` 만 빼면 되지 않나?

내 첫 시도였다. `@SpringBootApplication.scanBasePackages` 에서 `ledger` 만 빼면 될 줄 알았다. 안 됐다. 이유:

> **`@SpringBootApplication` 의 기본 entity scan 은 main 클래스가 위치한 패키지와 그 하위 전부.** scanBasePackages 와는 별개 메커니즘이다.

`LemuelApplication` 이 `github.lms.lemuel` 패키지에 있으니 자동 entity scan 은 그 아래 *모든* JPA `@Entity` 를 긁어모은다 — ledger 포함. component scan 에서 빼도 entity scan 은 못 막는다.

해결책은 `@EntityScan` 과 `@EnableJpaRepositories` 를 *명시*해서 자동 동작 자체를 덮어쓰는 것.

```java
@SpringBootApplication(scanBasePackages = {
    // ...
    "github.lms.lemuel.settlement",
    "github.lms.lemuel.pgreconciliation",
    "github.lms.lemuel.payout",
    "github.lms.lemuel.chargeback",
    // ledger 제거 — V47 migration 이 추가될 때까지 임시 비활성
})
@EntityScan(basePackages = {
    "github.lms.lemuel.cart",
    "github.lms.lemuel.category",
    "github.lms.lemuel.chargeback",
    "github.lms.lemuel.common",
    "github.lms.lemuel.coupon",
    "github.lms.lemuel.order",
    "github.lms.lemuel.payment",
    "github.lms.lemuel.payout",
    "github.lms.lemuel.pgreconciliation",
    "github.lms.lemuel.product",
    "github.lms.lemuel.review",
    "github.lms.lemuel.settlement",
    "github.lms.lemuel.shipping",
    "github.lms.lemuel.user",
})
@EnableJpaRepositories(basePackages = { /* 동일 */ })
public class LemuelApplication { ... }
```

여기에 한 가지 더 — settlement-service 안에 별도 `JpaConfig.java` 가 있었는데, 그 안에도 `@EntityScan` 이 ledger 를 포함하고 있었다. 두 개의 `@EntityScan` 이 동시에 활성화되면 충돌하거나 의도하지 않은 합집합이 만들어진다. **settlement-service 가 standalone 으로 뜨던 시절의 잔재**라 그냥 삭제했다.

### Spring Boot 4 사소한 함정

import 경로가 바뀌어 있었다.

```java
// Spring Boot 3 까지
import org.springframework.boot.autoconfigure.domain.EntityScan;

// Spring Boot 4 부터
import org.springframework.boot.persistence.autoconfigure.EntityScan;
```

처음에 옛 경로로 import 했다가 컴파일 실패. 같은 settlement-service 안의 다른 `JpaConfig.java` 가 신 경로를 쓰고 있는 걸 보고 알아챘다.

## 4. 네 번째 층 — Squash merge 가 만든 develop ↔ main commit divergence

3층 hotfix 를 develop 에 commit & push 했더니, 새 PR #2 (develop → main) 가 충돌(`DIRTY`) 표시.

```
mergeStateStatus: DIRTY
statusCheckRollup: []
```

local 에서 `git rebase origin/main` 해봤더니 한 줄 갈등은 30개 가까이 쏟아졌다.

```
Rebasing (3/29)
충돌 (내용): frontend/src/pages/Login.tsx
충돌 (추가/추가): order-service/.../DemoLoginService.java
...
```

원인은 squash merge 의 본질에 있다.

- develop 에 *작은* 커밋들이 쌓인다 (e.g. `commit A`, `commit B`)
- PR 을 squash merge 하면 main 에는 **새로운 SHA 의 단일 커밋 C** 만 생긴다
- develop 입장에서 `commit A`, `commit B` 는 여전히 자기 히스토리에 살아 있고, main 의 `C` 와 SHA 가 달라 *별개의 커밋* 으로 간주된다
- 새로 develop → main PR 을 만들면 GitHub 가 `A`, `B` 를 다시 main 위에 replay 시도 → 같은 변경을 두 번 적용하려다 충돌

이건 squash merge workflow 의 알려진 비용이다. 해결 패턴은 다음 중 하나.

1. develop 을 매번 main 에 force-reset (가능하지만 다른 작업자 있으면 위험)
2. develop 을 단순 "통합 브랜치" 로 안 쓰고 매번 feature 브랜치만 사용
3. **hotfix 시급 상황** — main 에서 직접 hotfix 브랜치를 따고 거기서 PR

세 번째로 갔다.

```bash
$ git rebase --abort
$ git checkout -b hotfix/ledger-exclude origin/main
$ git cherry-pick 4ecb93d
$ git push -u origin hotfix/ledger-exclude
$ gh pr create --base main --head hotfix/ledger-exclude ...
```

PR #3 깔끔하게 충돌 없이 머지. CI 통과 → main 으로 가서 새 이미지 빌드.

### 작은 보너스 — 노드 단위 `ImagePullBackOff`

새 이미지 빌드 직후 새 pod 가 또 다른 이유로 멈췄다. ImagePullBackOff. 이번엔 코드 잘못이 아니라 **특정 노드의 ghcr.io 외부 네트워크 일시 장애**.

```
Failed to pull image "...:main-eb2f78d":
  read tcp ...->...:443: read: connection reset by peer
Failed to resolve reference "...:main-eb2f78d":
  dial tcp: lookup ghcr.io: Try again
```

같은 시각 다른 노드에서 running 중인 기존 pod 의 DNS 는 멀쩡했다. **노드 단위 네트워크 플랩** 으로 결론. 가장 빠른 대응은 실패 pod 를 삭제해 deployment 가 다른 노드에 재스케줄하게 만드는 것.

```bash
$ kubectl -n <namespace> delete pod settlement-app-<hash>
pod "settlement-app-<hash>" deleted
```

새 pod 는 정상 노드에 스케줄돼 47초 안에 ready. 무재시작. 끝.

## 5. 뒤따라온 라운드 — 도메인 enum 진화 vs 프론트엔드 stale

여기까지가 *데이터를 화면에 띄우기* 까지의 1차전이었다. 사용자가 페이지를 들어가서 확인한 뒤 곧바로 두 번째 신고가 왔다.

> "필터 dropdown 의 상태값 (CALCULATED / WAITING_APPROVAL / APPROVED / REJECTED) 이 DB 실제 분포 (DONE 510 / CANCELED 200 / FAILED 200 / PROCESSING 200 / REQUESTED 200) 와 안 맞음. 전체 보기는 정상이지만 status 필터 사용 시 빈 결과."

백엔드 enum 을 봤다.

```java
public enum SettlementStatus {
    REQUESTED,    // 정산 요청됨 (초기 상태)
    PROCESSING,   // 정산 처리 중
    DONE,         // 정산 완료
    FAILED,       // 정산 실패
    CANCELED;     // 정산 취소

    // V26 에서 레거시 값(PENDING, CONFIRMED 등)은 DB에서 제거됐지만
    // 롤백 대비 방어 코드.
    public static SettlementStatus fromString(String status) { ... }
}
```

전이 모델은 자동. 외부 시스템이 결제를 캡쳐하면 정산 row 가 REQUESTED 로 생성되고, 스케줄러가 PROCESSING → DONE 으로 옮긴다. 환불로 net=0 이 되면 CANCELED 로 소멸. **사람이 승인/반려할 여지가 없다.**

그런데 프론트 코드는 옛 승인 워크플로우 시대의 enum 을 그대로 들고 있었다.

```typescript
// frontend/src/types/index.ts
status?: 'CALCULATED' | 'WAITING_APPROVAL'
       | 'APPROVED' | 'REJECTED'
       | 'PENDING' | 'CONFIRMED' | 'CANCELED';
```

```tsx
// SettlementAdmin.tsx
<option value="CALCULATED">계산완료</option>
<option value="WAITING_APPROVAL">승인대기</option>
<option value="APPROVED">승인됨</option>
<option value="REJECTED">반려됨</option>

// + 승인/반려 버튼 + 모달 + API 호출 전체가 살아있음
{settlement.status === 'WAITING_APPROVAL' && (
  <button onClick={() => approveSettlement(...)}>승인</button>
)}
```

심지어 백엔드에 `/api/settlements/{id}/approve` 엔드포인트는 **아예 없는데** 프론트는 그걸 호출하고 있었다. 백엔드 도메인 모델은 진화했고 그 변경이 프론트에 전파되지 않은 채 **수 개월** 흘러간 흔적이었다.

수정 범위:

| 파일 | 변경 |
|---|---|
| `types/index.ts` | `SettlementSearchRequest.status` 유니언 신규 enum 으로 교체. `SettlementDetail` 의 `amount → paymentAmount/commission/netAmount` 로 정렬 + `approved*/rejected*` 필드 제거 |
| `components/StatusBadge.tsx` | settlement 매핑에서 레거시 6개 항목 삭제 |
| `pages/SettlementAdmin.tsx` | 필터 dropdown 5개 옵션 갱신, status badge / text 매핑 정정, 승인/반려 버튼·모달·핸들러·로딩 상태 전부 제거 |
| `api/settlement.ts` | `approveSettlement`, `rejectSettlement` 함수 삭제. `getSettlement` 경로를 `/api/settlements/{id}` → `/settlements/{id}` 로 정정 (실제 `@RequestMapping("/settlements")` 와 매칭) |
| 테스트 | `mockDetail` 필드 + URL 갱신, 승인/반려 테스트 블록 제거 |

`-249/+42`. 코드는 줄었다.

배포 후 검증:

```bash
$ for ST in REQUESTED PROCESSING DONE FAILED CANCELED; do
    curl -s ".../api/settlements/search?status=$ST" -H "Bearer ..." \
      | jq -r '"\($status): \(.totalElements)"'
  done

REQUESTED: 200
PROCESSING: 200
DONE: 510
FAILED: 200
CANCELED: 200
# 합계 1310 = 전체와 일치 ✓
```

필터가 살아났다.

---

## 회고 — 같은 사고를 두 번 겪지 않기 위해

이 한 건이 드러낸 *제도 차원의* 결함 4개를 정리한다.

### 1. "분리 의도" 와 "분리 배포" 사이의 거리는 생각보다 멀다

코드를 모듈로 쪼개면서 "곧 분리 배포할 거니까" 라고 적어둔 commit message 가 그대로 3주 묵었다. 그 사이 새 도메인 코드가 settlement-service 에 계속 쌓였지만 **어디에도 배포되지 않았다.** 이게 신고 1건이 들어오기 전까지 보이지 않은 이유는 — 정산 페이지가 운영자가 자주 안 들어가는 화면이었기 때문.

> **규칙:** 모듈 분리 PR 의 acceptance criteria 에 *"새 모듈이 어떤 컨테이너로 배포되는지"* 를 적고, 분리 배포 helm chart + CI 까지 같은 PR 에서 끝내거나 — 분리 배포가 아직이면 *반드시 기존 모놀리스에 library 로 흡수* 한다. 두 상태 중 어느 것도 아닌 *limbo* 는 만들지 않는다.

### 2. 같은 폴더의 형제 파일과 다른 패턴은 *반드시* 의심

`SettlementSearchJdbcRepository` 가 `opslab.` 스키마 prefix 를 빠뜨린 건, 같은 폴더의 다른 JDBC adapter 들이 다 prefix 를 쓰고 있는데 이 파일만 안 쓰고 있던 *지역 일관성 위반* 이었다. 코드 리뷰 단계에서 형제 파일과의 diff 만 봤어도 잡혔을 일.

> **규칙:** 새 JDBC adapter / mapper 추가 시 *같은 디렉토리 내 다른 파일의 스키마 prefix 패턴* 을 따랐는지 체크하는 ArchUnit 룰 추가 고려.

### 3. `ddl-auto: validate` 는 마이그레이션 누락의 안전장치다 — 신뢰하고 활용한다

세 번째 층에서 hotfix 가 빠르게 나올 수 있었던 이유는 Hibernate validate 가 *fail-fast* 로 알려줬기 때문이다. ledger_entries 가 없다는 사실을 production 가서 처음 알게 된 게 아니라 *pod 가 뜨자마자* 알았다. `ddl-auto: none` 으로 했다면 ledger 관련 row 가 처음 들어오는 순간까지 잠복했을 거다.

> **규칙:** prod 에서 `ddl-auto: validate` 는 *기능* 이 아니라 *재해 차단 비용* 이다. 끄지 않는다.

### 4. Squash merge workflow 의 발 빠른 우회로를 미리 준비

운영 hotfix 가 필요할 때 develop → main PR 이 충돌로 막히면 그 자체가 추가 사고가 된다. 평소엔 별 문제 없지만 *시급할 때* 노출된다.

> **규칙:** 운영 hotfix 는 *항상* `hotfix/<short-desc>` 브랜치를 main 에서 따서 PR 한다. develop 을 거치지 않는다. 분류상 RCA 가 끝나 develop 에도 같은 변경이 들어가야 한다면 hotfix 머지 후 별도 cherry-pick.

### 5. 백엔드 도메인 진화에 프론트는 반드시 따라간다

`SettlementStatus` 도메인 enum 이 새 모델로 진화했을 때, 그 변경이 프론트 API 클라이언트 / 타입 / UI 컴포넌트 / 테스트까지 *원자적으로* 따라가지 않은 게 이번의 진짜 잠복 결함이다. 도메인 변경을 만든 사람이 곧장 프론트까지 PR 내는 게 가장 안전하다. PR 템플릿에 "프론트 영향 영역 체크리스트" 를 추가하면 자동화 가능.

---

## 마치며

빈 화면 1건이 4개 층의 도미노였다. 각 층마다 *왜 그게 그렇게 됐는지* 합리적 사유가 있었고, 어떤 것도 단독으로는 "심각한" 결함이 아니었다. 그런데 다 합쳐지자 운영자가 들어가는 첫 페이지가 그냥 비어버렸다.

이런 종류의 사고는 **사후에 보면 너무 명백한데 사전에는 안 보이는** 특성이 있다. 그래서 글로 남긴다. 다음에 비슷한 패턴이 보이면 (모듈 분리가 절반만 끝났다든지, JDBC raw SQL 이 스키마 prefix 를 빠뜨렸다든지, `ddl-auto: validate` 가 새 entity 에 트리거 됐다든지) — *4층 짜리 도미노가 잠복해 있는지* 의심부터 하면 좋겠다.

오늘의 변경 통계:

| 항목 | 값 |
|---|---|
| 진단 시작 → 1차 운영 회복 | 약 60분 |
| 추가 hotfix (ledger crash) | 약 25분 |
| 후속 정리 (enum 동기화) | 약 30분 |
| 총 commit / PR | 5 commit / 3 PR |
| 코드 변화 | `-336/+104` (정리 위주, frontend `-249/+42` 포함) |
| 운영 영향 | 기존 pod 가 계속 Running 이라 0초 — 신규 pod 만 실패 |

기존 pod 가 안 죽고 있었던 게 결과적으로 *가장 큰 안전망* 이었다. 다음 라운드에서는 — *helm chart 분리 + settlement-service standalone 배포 + V47 migration + ledger Phase 1 복귀* 로 가야 한다.
