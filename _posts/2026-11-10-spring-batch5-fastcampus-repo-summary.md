---
layout: post
title: "cheese10yun/spring-batch5 리포 정리 — Spring Batch 5 기초부터 No Offset·Cursor·Partition, 정산 통계 Job 까지"
date: 2026-11-10 23:23:48 +0900
categories: [spring, batch]
tags: [spring-batch, spring-boot, mysql, jpa, cursor, no-offset, partitioning, querydsl]
---

> **원본 리포:** [github.com/cheese10yun/spring-batch5](https://github.com/cheese10yun/spring-batch5)
> 패스트캠퍼스 강의 [「실무를 위한 Spring Batch의 모든 것 : 성능 개선부터 프로젝트까지」](https://fastcampus.co.kr/dev_online_springbatch)의 실습 코드다.

> **검증 범위.** 2026-11-10 기준 `main` HEAD `9992529`(커밋 29개)를 클론해서 **코드를 읽기만 했다.** 빌드하거나 실행하지 않았다. 이 글에 나오는 성능 수치는 **전부 리포 README 에 작성자가 적어 둔 측정값**이고, 내가 재현한 숫자는 하나도 없다. 프레임워크 동작에 대한 설명은 Spring Batch·Spring Boot·MySQL Connector/J 공식 문서로 확인했고, 출처는 맨 아래 References 에 모았다.

## 1. 한눈에 보기

| 항목 | 내용 |
|---|---|
| 스택 | Spring Boot 3.4.4, Java 17, `spring-boot-starter-batch`, Spring Data JPA, `spring-batch-test` |
| Part 3 추가 | Kotlin, QueryDSL 5.1.0(jpa jakarta·sql·sql-codegen), `starter-web` |
| DB | `compose.yaml` 의 `mysql:8.0.34`(DB `spring_batch`, utf8mb4, TZ Asia/Seoul) |
| 구성 | 독립 Gradle 모듈 26개. 단계마다 폴더를 새로 복사해서 "이전 단계 대비 무엇이 바뀌었나"를 `diff` 로 볼 수 있다 |
| 실행 | `spring.batch.job.name: ${job.name:NONE}` 이라서 `--job.name=xxxJob` 으로 실행할 Job 을 고른다 |

README 에는 MySQL 을 띄우는 방법, `general_log` 로 실제 SQL 을 보는 방법, 샘플 데이터(`payment_source`) 적재, Spring Batch 5 MySQL 메타 테이블 DDL(`BATCH_JOB_INSTANCE` 등, 5.x 에서 바뀐 `BATCH_JOB_EXECUTION_PARAMS.PARAMETER_TYPE` 포함), 메타 테이블 조인 조회 쿼리가 정리돼 있다.

모듈은 세 덩어리다.

- **Part 1 기초 (1-1 ~ 1-7):** 첫 Job → Job 구성 요소 → JobParameter·Tasklet·Chunk → JPA 리더/라이터 → skip → retry → 리스너
- **Part 2 성능 (2-1 ~ 2-7):** limit/offset 의 한계 → No Offset → Cursor → Processor/Writer 튜닝 → Partition
- **Part 3 프로젝트 (3-1-x, 3-2-x, 3-3-x):** 일일 결제 통계 Job, 회원가입 쿠폰 발급 Job(HTTP 리더), 배치 테스트

## 2. Part 1 — Spring Batch 5 문법

### 2.1 Builder 에 `JobRepository` 와 `TransactionManager` 를 직접 넘긴다

모든 모듈이 5.x 방식으로 작성돼 있다.

```java
return new JobBuilder("paymentReportJob", jobRepository)
        .incrementer(new RunIdIncrementer())
        .start(paymentReportStep)
        .build();

return new StepBuilder("paymentReportStep", jobRepository)
        .<PaymentSource, Payment>chunk(chunkSize, transactionManager)
        .reader(...).processor(...).writer(...)
        .build();
```

[Spring Batch 5.0 마이그레이션 가이드](https://github.com/spring-projects/spring-batch/wiki/Spring-Batch-5.0-Migration-Guide)의 내용과 그대로 맞는다. `JobBuilderFactory`·`StepBuilderFactory` 는 더 이상 빈으로 노출되지 않고 deprecated 됐다(5.2 에서 제거 예정). `@EnableBatchProcessing` 도 트랜잭션 매니저 빈을 만들어 주지 않는다. 그래서 tasklet/chunk 스텝에 `PlatformTransactionManager` 를 명시해야 한다.

이 리포에는 `@EnableBatchProcessing` 이 없다. Spring Boot 문서에 따르면 이 애너테이션을 붙이거나 `DefaultBatchConfiguration` 을 상속하면 Boot 의 배치 자동 구성이 **물러난다**. 메타 스키마 초기화도 함께 꺼진다([Spring Boot — Spring Batch](https://docs.spring.io/spring-boot/reference/io/spring-batch.html)). Boot 3 에서는 붙이지 않는 것이 기본 경로다. 리포가 그 경로를 따른다.

### 2.2 1-3: Tasklet 과 Chunk, JobParameter

- Tasklet 스텝: `.tasklet(sampleTasklet(), transactionManager)`
- Chunk 스텝: `.<BigDecimal, BigDecimal>chunk(5, transactionManager)`
- `@StepScope` 빈에서 `@Value("#{jobParameters['targetDate']}")` 로 파라미터를 받는다.

Part 2 부터는 `LocalDate` 타입으로 바로 받는다. 5.x 에서 JobParameter 가 임의 타입을 지원하게 되면서 메타 테이블에 `PARAMETER_TYPE` 컬럼이 생겼다. README 의 DDL 이 그 변경을 반영하고 있다.

Spring Boot 문서는 커맨드라인으로 Job 파라미터를 넘길 때 `--` 없이 `key=value` 형식으로 쓰라고 한다. `--` 가 붙은 인자는 `Environment` 프로퍼티가 되고, Job 파라미터로는 무시된다([Spring Boot how-to — Batch](https://docs.spring.io/spring-boot/how-to/batch.html)). 이 리포는 Job 이름만 `--job.name` 으로 넘기니 이 규칙과 맞는다.

### 2.3 1-4 ~ 1-7: 리더/라이터, 내결함성, 리스너

| 모듈 | 핵심 코드 |
|---|---|
| 1-4 | `JpaPagingItemReader` 로 `payment_source` 를 읽고, Processor 로 `Payment` 로 바꾼 뒤 `JpaItemWriter` 로 저장 |
| 1-5 | `.faultTolerant().skip(InvalidPaymentAmountException.class).skipLimit(2)` |
| 1-6 | `.retry(PartnerHttpException.class).retryLimit(10)` 에 `.noRollback(InvalidPaymentAmountException.class)` |
| 1-7 | Job/Step/Chunk 소요 시간 리스너와 ItemRead/Process/Write 리스너 |

skip 한도는 read·process·write 단계를 **합산**해서 적용된다. 한도를 넘는 다음 예외가 나면 스텝이 실패한다([Spring Batch — Configuring Skip Logic](https://docs.spring.io/spring-batch/reference/step/chunk-oriented-processing/configuring-skip.html)). 같은 문서는 "돈이 오가는 금융 데이터는 skip 하면 안 될 수 있다"고 경고한다. 강의 예제가 결제 데이터에 skip 을 거는 건 기능을 보여 주기 위한 것이다. 실무에서는 skip 된 건을 어디에 남길지(리스너, 별도 테이블)까지 함께 설계해야 한다.

1-7 의 `StepDurationTrackerListener`·`ChunkDurationTrackerListener` 는 Part 2·3 의 모든 모듈에 그대로 붙어 있다. 성능 비교에 쓰인 계측 도구가 바로 이 리스너들이다.

## 3. Part 2 — 성능 개선 (리포의 핵심)

### 3.1 2-1: limit/offset 은 뒤로 갈수록 느려진다

`JpaPagingItemReader` 는 페이지마다 `LIMIT n OFFSET m` 을 날린다. offset 이 커지면 DB 는 앞의 m 행을 읽고 버려야 하므로, 청크 하나를 처리하는 시간이 offset 에 비례해 늘어난다. README 의 작성자 측정값은 다음과 같다.

| 건수 | limit/offset 총 소요 |
|---|---|
| 1만 | 503 ms |
| 5만 | 1,964 ms |
| 10만 | 4,701 ms |
| 50만 | 85,000 ms |
| 100만 | 573,000 ms |

건수가 10배(10만 → 100만) 늘어날 때 시간은 약 122배 늘었다. 청크당 비용이 일정하지 않고 offset 에 비례해 커지니, 전체 비용은 대략 건수의 제곱에 가깝게 늘어난다.

$$
T_{\text{offset}}(N) \;\approx\; \sum_{k=0}^{N/c - 1} \alpha\,(k\,c) \;=\; O\!\left(\frac{N^2}{c}\right)
$$

여기서 $$c$$ 는 청크 크기, $$\alpha$$ 는 행당 스캔 비용이다.

### 3.2 2-2: No Offset 리더를 직접 만든다

`NoOffsetItemReader<T>` 는 `ItemStreamReader` 를 직접 구현한 클래스다.

1. `open()` 에서 쿼리를 `setMaxResults(1)` 로 한 번 실행해 **가장 큰 id + 1** 을 시작점(`firstId`)으로 잡는다. 이 동작은 쿼리에 `ORDER BY ps.id DESC` 가 있어야 성립한다. 예제 쿼리에는 실제로 이 정렬이 들어 있다.
2. 버퍼가 비면 `WHERE id < :firstId AND ...` 를 붙여 청크 크기만큼 가져오고, 마지막 행의 id 를 다음 `firstId` 로 쓴다.
3. `update()` 에서 `firstId` 를 `ExecutionContext` 에 저장한다. 그래서 재시작하면 끊긴 지점부터 다시 읽는다.

offset 없이 인덱스로 바로 위치를 찾으니, 청크당 시간이 데이터 위치와 상관없이 거의 일정하다.

### 3.3 2-3: Cursor 리더, 그리고 세 방식 비교

`JpaCursorItemReader` 로 같은 쿼리를 읽는다. README 의 작성자 측정값(단위 ms)은 다음과 같다.

| 건수 | Limit Offset | No Offset | Cursor |
|---|---|---|---|
| 1만 | 503 | 471 | 472 |
| 5만 | 1,964 | 2,102 | 1,239 |
| 10만 | 4,701 | 5,893 | 2,108 |
| 50만 | 85,000 | 13,779 | 9,840 |
| 100만 | 573,000 | 21,953 | 23,104 |
| 500만 | — | 97,587 | 86,381 |

작성자는 100만 건에서 No Offset 이 "약 26배" 빠르다고 적었다. 표의 숫자로 계산하면 실제로 그렇다.

$$
\frac{573{,}000}{21{,}953} \approx 26.1,\qquad \frac{573{,}000}{23{,}104} \approx 24.8
$$

No Offset 과 Cursor 는 둘 다 건수에 거의 선형으로 늘어나고, 500만 건에서도 두 방식의 차이는 약 13% 다. 어느 쪽을 고를지는 속도보다 운영 조건을 보고 정하는 게 맞다. 커넥션을 오래 잡아도 되는지, 재시작 지점을 어떻게 저장할지, 정렬 키가 단조 증가하는지 같은 것들이다.

> 단, 이 숫자들은 작성자의 단일 환경 측정값이다. 하드웨어와 반복 횟수는 내가 확인하지 못했고, 재현도 하지 않았다.

### 3.4 2-4 → 2-5 → 2-6-1: 외부 API 를 부르는 Processor/Writer 튜닝

시나리오는 회원 등급 갱신이다. `OrderClient.getGrade()` 는 호출 한 번에 `Thread.sleep(150)` 으로 외부 API 지연을 흉내 낸다.

| 단계 | 구조 | 효과 |
|---|---|---|
| 2-4 | Processor 에서 회원마다 동기 호출 | 청크 1,000건 × 150ms 가 그대로 직렬로 쌓인다 |
| 2-5 | Writer 에서 청크 전체를 RxJava `Flowable.parallel().runOn(Schedulers.io())` 로 병렬 호출한 뒤 `JpaItemWriter` 로 저장 | I/O 대기를 병렬로 겹친다 |
| 2-6-1 | 같은 병렬 호출 뒤에 **등급별로 묶어** `update User u set u.grade = :grade where u.id in :ids` 를 한 번씩 실행 | 행 단위 dirty-checking UPDATE 를 등급 수만큼의 벌크 UPDATE 로 줄인다 |

병렬 호출을 Processor 가 아니라 Writer 에서 하는 이유가 있다. Processor 는 아이템을 하나씩 받기 때문에, 청크 단위로 모아서 병렬화하려면 리스트 전체를 받는 Writer 에서 해야 한다. 이 모듈들에는 README 성능표가 없어서 개선 폭은 적지 않는다.

### 3.5 2-7: Partition Step

`PartitionJobConfig` 의 구성은 다음과 같다.

- JobParameter `startDate`·`endDate` 를 받는 `@StepScope LocalDatePartitioner` 가 날짜마다 `ExecutionContext{paymentDate}` 를 하나씩 만든다.
- `managerStep` 이 `.partitioner("workerStep", ...)`·`.gridSize(31)`·`ThreadPoolTaskExecutor(core 31, max 50)` 로 워커를 병렬로 돌린다.
- 각 워커의 `JpaCursorItemReader` 는 `#{stepExecutionContext['paymentDate']}` 로 자기 날짜만 읽는다.

Spring Batch 문서는 단일 프로세스·멀티스레드 병렬화 방법으로 Multi-threaded Step, Parallel Steps, Local Chunking, Partitioning 을 나열한다. 그러면서 "먼저 단일 스레드로 현실적인 Job 의 성능을 재고 나서 복잡한 구현을 고려하라"고 권한다([Spring Batch — Scaling and Parallel Processing](https://docs.spring.io/spring-batch/reference/scalability.html)). 이 리포의 순서도 같다. Part 2 앞부분에서 리더 자체를 먼저 고치고, 파티셔닝은 마지막에 다룬다.

## 4. Part 3 — 실전 Job 두 개와 테스트

### 4.1 일일 결제 통계 Job (3-1-1 → 3-1-4 → 3-3-1)

`payment_source` 를 사업자번호·날짜 기준으로 `SUM` 해서 `payment_daily_statistics` 에 적재하는 Job 이다. 단계별로 바뀌는 내용은 다음과 같다.

| 단계 | 바뀐 점 | 해결하는 문제 |
|---|---|---|
| 3-1-1 | `JdbcCursorItemReader` + `GROUP BY` SQL, `JpaItemWriter` | 기본 집계 |
| 3-1-2 | `ArgumentProperties`(`@EnableConfigurationProperties`) + `ClearExistingDataJobListener` 가 Job 시작 전에 그날 통계를 `DELETE` | **재실행해도 중복 적재되지 않게** (delete-then-insert) |
| 3-1-3 | `(businessRegistrationNumber, paymentDate)` 유니크 제약 + `PaymentDailyStatisticsRecoveryService` | 삭제하지 않고 **기존 행은 금액이 다를 때만 update, 없으면 insert** (upsert) |
| 3-1-4 | `PrepareTargetDatesJobListener` 가 "오늘 수정된 원천 데이터"의 결제일들을 찾아 대상 날짜 집합을 만든다. SQL 은 날짜 범위를 `OR` 로 이어 붙인다 | **늦게 들어온 정정 데이터**까지 과거 날짜 통계에 반영 |
| 3-3-1 | 재처리 대상이 없으면 JobParameter 의 `paymentDate` 로 대체 | 대상 날짜가 비어 Job 이 아무것도 안 하는 경우 방지 |

여기서 주목할 진화는 3-1-2 → 3-1-3 이다. delete-then-insert 는 간단하지만, 삭제와 재적재 사이에 통계가 잠깐 비어 보이고, 실패하면 그날 통계가 사라진 채로 남는다. 3-1-3 은 유니크 키로 기존 행을 찾아 갱신하는 쪽으로 바꿨다. 같은 날짜를 몇 번 다시 돌려도 결과가 같아지는(멱등) 방향이다.

리더 설정도 볼 만하다.

```java
.fetchSize(Integer.MIN_VALUE)   // MySQL 행 단위 스트리밍
.verifyCursorPosition(false)    // 스트리밍 ResultSet 에서 getRow() 검증을 끈다
```

MySQL Connector/J 는 **기본적으로 ResultSet 전체를 메모리로 가져온다.** 행 단위 스트리밍은 forward-only·read-only 문장에 fetch size `Integer.MIN_VALUE` 를 주는 것이 신호다. 대안은 `useCursorFetch=true` 와 양수 fetch size 를 함께 쓰는 커서 페치다. 스트리밍 중에는 결과를 다 읽거나 닫기 전까지 같은 커넥션으로 다른 쿼리를 보낼 수 없다([MySQL Connector/J — JDBC API Implementation Notes](https://dev.mysql.com/doc/connector-j/en/connector-j-reference-implementation-notes.html)).

### 4.2 회원가입 쿠폰 발급 Job (3-2-1 → 3-2-2 → 3-3-5)

`3-2-1-server` 는 회원 API 를 흉내 내는 별도 Spring 앱이다. 배치는 이 서버를 페이지 단위로 호출한다.

- **`HttpPageItemReader<T>`** 는 `AbstractItemCountingItemStreamItemReader` 를 상속한다. `RestTemplate` 으로 `?page=&size=` 를 호출하고, 응답의 `content` 를 버퍼에 담아 하나씩 반환하다가 `last=true` 를 받으면 끝낸다. 제네릭 응답 `PageResponse<T>` 를 역직렬화하려고 `ParameterizedTypeReference` 를 쓰는데, 코드 주석에 타입 소거 때문에 `LinkedHashMap` 이 돼서 `ClassCastException` 이 나는 이유가 길게 설명돼 있다.
- **3-2-2** 는 `ignoreErrors` 옵션을 추가한다. 페이지 호출이 실패하면 로그만 남기고 다음 페이지로 넘어간다(`if` → `while` 로 재시도 루프).
- **3-3-5** 는 테스트를 붙이면서 `ignoreErrors(false)` 로 되돌리고, DTO 를 불변(`final` 필드)으로 바꾼다.

### 4.3 배치 테스트 (3-3-1 ~ 3-3-5)

- `SpringBatchTestSupport`: `@SpringBatchTest` + `@SpringBootTest(properties = "spring.batch.job.enabled=false")` 기반 베이스 클래스. `launchJob`, `launchStep`, `thenBatchCompleted`, QueryDSL `deleteAll` 헬퍼를 둔다.
- 3-3-4 는 스텝 정의를 `PaymentStatisticsStepConfiguration` 으로 분리해 **스텝 단위로** 테스트한다(`jobLauncherTestUtils.launchStep`).
- 3-3-5 는 `@TestConfiguration` 에 `@Primary` 로 mock `RestTemplate` 을 등록하고, 페이지 0·1 응답을 `given(...)` 으로 정해 쿠폰 Job 을 외부 서버 없이 검증한다.

`spring.batch.job.enabled=false` 는 Boot 가 시작할 때 Job 을 자동 실행하지 않게 하는 공식 속성이다([Spring Boot — Spring Batch](https://docs.spring.io/spring-boot/reference/io/spring-batch.html)). 테스트에서 Job 이 두 번 도는 것을 막는다.

## 5. 읽으면서 걸린 점

강의 자료라서 일부러 단순하게 둔 부분이 많다. 그래도 그대로 복사해서 쓰면 문제가 될 수 있는 것들을 적어 둔다. 실행해서 확인한 게 아니라 **코드만 읽고 내린 판단**이다.

1. **2-3 Cursor 예제의 스트리밍 힌트가 주석 처리돼 있다.** 코드 주석은 "`HINT_FETCH_SIZE` 를 `Integer.MIN_VALUE` 로 줘서 스트리밍한다"고 설명하는데, 정작 그 줄(`.hintValues(...)`)이 `//` 로 막혀 있다. JDBC URL 에도 `useCursorFetch` 가 없다. 위 MySQL 문서대로라면 HEAD 그대로 실행할 때 결과 전체가 JVM 메모리로 올라온다. 이름은 Cursor 리더지만 메모리 측면에서는 스트리밍이 아닌 셈이다. 표의 Cursor 수치가 힌트를 켠 상태에서 잰 것인지는 리포만 봐서는 알 수 없다. 반면 Part 3 의 `JdbcCursorItemReader` 는 `fetchSize(Integer.MIN_VALUE)` 를 제대로 켜 두었다.
2. **`NoOffsetItemReader` 는 쿼리 문자열을 치환해서 조건을 넣는다.** `queryString.replace("WHERE", "WHERE id < :firstId AND")` 는 대소문자를 구분하고, `WHERE` 가 여러 번 나오면(서브쿼리 등) 모두 바꾸며, `WHERE` 가 없는 쿼리에서는 아무 일도 하지 않는다. 시작점 계산도 쿼리가 `ORDER BY id DESC` 라는 전제에 묵시적으로 기댄다. 일반화해서 쓰려면 조건과 정렬을 빌더가 직접 조립하게 해야 안전하다.
3. **2-2 README 의 비교표 헤더가 틀렸다.** 열 이름은 `Limit Offset | Cursor` 인데, 들어 있는 값은 2-3 표의 No Offset·Cursor 값과 같다.
4. **2-7 README 그림과 코드가 다르다.** README 의 Mermaid 다이어그램은 `gridSize=5` 인데 코드는 `gridSize(31)`, 코어 스레드 31개다. 워커 31개가 각각 커서를 열면 DB 커넥션도 그만큼 필요하다. 커넥션 풀 크기를 같이 맞춰야 한다.
5. **3-2-2 의 `ignoreErrors(true)` 는 페이지를 통째로 버린다.** 실패한 페이지의 회원들은 쿠폰을 못 받고 Job 은 성공으로 끝난다. 3-3-5 에서 `false` 로 되돌린 것이 맞는 방향이다. 실패를 무시하려면 최소한 실패한 페이지 번호를 남겨서 재처리할 수 있어야 한다.
6. **`ArgumentProperties` 는 리스너가 값을 바꾸는 싱글턴이다.** `PrepareTargetDatesJobListener` 가 대상 날짜를 이 빈에 써 넣고 리더가 읽는다. Job 하나만 실행하고 끝나는 CLI 프로세스에서는 문제가 없다. 같은 JVM 에서 Job 을 여러 번 돌리면(테스트, 스케줄러 상주) 이전 실행의 값이 남는다. JobExecutionContext 에 넣는 편이 Spring Batch 다운 방식이다. 날짜 조건을 `String.format` 으로 SQL 에 넣는 부분은 값이 `LocalDate` 라서 인젝션 경로는 아니다.

## 6. 정리

이 리포의 가치는 Part 2 에 있다. "Spring Batch 가 느리다"는 체감의 상당 부분이 **리더가 offset 페이징을 쓰기 때문**이라는 것을 같은 데이터·같은 리스너로 단계별로 보여 준다. 그다음 No Offset, Cursor, Writer 쪽 병렬 I/O, 벌크 UPDATE, 파티셔닝 순서로 하나씩 손댄다. Part 3 의 통계 Job 은 delete-then-insert 에서 유니크 키 기반 upsert 로, 다시 정정 데이터 재처리로 넘어가는 흐름이 실무 정산 배치의 고민을 그대로 담고 있다.

모듈마다 폴더가 따로 있으니, 읽을 때는 인접한 두 모듈을 `diff -r` 로 비교하는 게 가장 빠르다. 이 글의 Part 3 표도 그렇게 만들었다.

## References

- 원본 리포: [cheese10yun/spring-batch5](https://github.com/cheese10yun/spring-batch5) (HEAD `9992529`)
- 강의 페이지: [패스트캠퍼스 — 실무를 위한 Spring Batch의 모든 것](https://fastcampus.co.kr/dev_online_springbatch)
- Spring Batch 공식 위키: [Spring Batch 5.0 Migration Guide](https://github.com/spring-projects/spring-batch/wiki/Spring-Batch-5.0-Migration-Guide)
- Spring Batch 5.0 레퍼런스: [Configuring and Running a Job](https://docs.spring.io/spring-batch/docs/5.0.x/reference/html/job.html)
- Spring Batch 레퍼런스(최신판): [Scaling and Parallel Processing](https://docs.spring.io/spring-batch/reference/scalability.html) · [Configuring Skip Logic](https://docs.spring.io/spring-batch/reference/step/chunk-oriented-processing/configuring-skip.html) · [Database readers and writers](https://docs.spring.io/spring-batch/reference/readers-and-writers/database.html)
- Spring Boot 레퍼런스: [Spring Batch](https://docs.spring.io/spring-boot/reference/io/spring-batch.html) · [How-to: Batch Applications](https://docs.spring.io/spring-boot/how-to/batch.html)
- MySQL 공식: [Connector/J — JDBC API Implementation Notes (ResultSet streaming)](https://dev.mysql.com/doc/connector-j/en/connector-j-reference-implementation-notes.html)
