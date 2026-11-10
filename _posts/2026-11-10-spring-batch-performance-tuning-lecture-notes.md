---
layout: post
title: "Spring Batch 성능 튜닝부터 실전 전략까지 — 김남윤 강의 자료 정리"
date: 2026-11-10 23:55:08 +0900
categories: [backend, spring]
tags: [spring-batch, performance, mysql, no-offset, cursor, partitioning, idempotency, testing]
---

김남윤([cheese10yun](https://github.com/cheese10yun)) 님의 **「Spring Batch : 성능 튜닝부터 실전 전략까지」** 강의 자료(344쪽)를 읽고 정리한 글입니다. **강의 자료 원본 PDF는 [여기](/assets/pdf/spring-batch-lecture.pdf)에서 받을 수 있습니다** (16.6MB, 344쪽). 자료의 저작권은 저자 김남윤 님에게 있습니다. 저자의 글은 [블로그](https://cheese10yun.github.io/)에, 실습 코드는 [GitHub 저장소 spring-batch5](https://github.com/cheese10yun/spring-batch5)에 공개되어 있습니다.

강의는 세 파트로 나뉩니다. Part 1은 기본 개념, Part 2는 성능, Part 3은 실무 설계를 다룹니다. 기본 개념은 [Spring Batch 공식 레퍼런스](https://docs.spring.io/spring-batch/reference/)에도 잘 나와 있어서, 이 글은 **Part 2와 Part 3** 에 무게를 둡니다. 실습 환경은 Spring Batch 5, Spring Boot 3, Java 17, MySQL 8입니다.

> **수치에 대해.** 이 글의 ms 수치는 모두 **강사가 자기 실습 환경에서 잰 값**을 강의 자료에서 옮긴 것입니다. 하드웨어 사양이나 반복 횟수는 자료에 적혀 있지 않아서 재현 가능한 벤치마크로 보기는 어렵습니다. 절대값보다 **추세와 몇 배 차이가 나는지**를 보는 용도로 읽어 주세요.

## Part 1 요약 — 뼈대

- **Job → Step → Chunk(Reader / Processor / Writer)** 구조입니다. 청크 하나가 트랜잭션 하나이고, 청크 크기는 커밋 간격을 정합니다.
- 메타데이터 모델은 JobInstance(= Job + 식별 JobParameters), JobExecution, StepExecution, StepContribution입니다. 같은 파라미터로 이미 완료된 JobInstance는 다시 실행되지 않습니다.
- **장애 허용**: Skip(`LimitCheckingItemSkipPolicy`, `AlwaysSkipItemSkipPolicy`, `NeverSkipItemSkipPolicy`, 조합)과 Retry(`SimpleRetryPolicy`, `CompositeRetryPolicy`). 공식 문서: [Configuring Skip Logic](https://docs.spring.io/spring-batch/reference/step/chunk-oriented-processing/configuring-skip.html), [Retry Logic](https://docs.spring.io/spring-batch/reference/step/chunk-oriented-processing/retry-logic.html).

## Part 2 — 읽기 성능: Limit-Offset → No-Offset → Cursor

### 왜 Limit-Offset이 느려지나

`LIMIT n OFFSET m` 은 앞의 m행을 읽고 버린 다음 n행을 돌려줍니다. 그래서 뒤 페이지로 갈수록 한 페이지를 읽는 비용이 계속 늘어납니다. 강의는 하루치 100만 행과 나머지 1,166만 행으로 데이터를 만들고 EXPLAIN으로 이 현상을 보여 줍니다.

해결책은 두 가지입니다.

- **No-Offset(키셋)**: `WHERE id > :lastKey ORDER BY id LIMIT n`. 인덱스 seek라서 페이지마다 비용이 거의 같습니다. 대신 마지막 키는 애플리케이션이 상태로 들고 있어야 합니다.
- **Cursor**: DB에 커서를 열고 한 행씩 스트리밍합니다. 메모리는 적게 쓰지만 단일 스레드이고 커넥션을 오래 잡고 있습니다.

Spring Batch 쪽 대응물은 `JdbcPagingItemReader` / `JdbcCursorItemReader` 입니다([Database ItemReaders](https://docs.spring.io/spring-batch/reference/readers-and-writers/database.html)). 공식 `JdbcPagingItemReader` 는 `sortKey` 기반의 키셋 쿼리를 생성합니다. 그래서 "Spring Batch의 페이징 리더 = OFFSET" 이라는 통념은 리더 종류에 따라 맞기도 하고 틀리기도 합니다. JPA 계열 페이징 리더는 OFFSET을 씁니다.

**강사 측정값 (ms)**

| rows | Limit-Offset | No-Offset | Client Cursor | Server Cursor |
|---:|---:|---:|---:|---:|
| 10,000 | 503 | 471 | 472 | 476 |
| 100,000 | 4,701 | 5,893 | 2,108 | 2,111 |
| 500,000 | 85,000 | 13,779 | 9,840 | 9,016 |
| 1,000,000 | 573,000 | 21,953 | 23,104 | 18,814 |
| 5,000,000 | — | 97,587 | 86,381 | 78,288 |

읽는 법:

- 10만 건까지는 Limit-Offset도 버틸 만합니다. **50만 건부터 격차가 급격히 벌어집니다.** 100만 건에서는 약 26배입니다.
- Cursor는 No-Offset보다 조금 빠르지만 차이가 크지 않습니다. 결정적인 차이는 속도가 아니라 **메모리**입니다.

### 클라이언트 커서 vs 서버 커서 (MySQL)

MySQL Connector/J는 기본값으로 결과셋 **전체를 클라이언트 힙에 버퍼링**합니다. 수백만 행이면 OOM 위험이 있습니다. 스트리밍하려면 `fetchSize` 를 `Integer.MIN_VALUE` 로 주거나 `useCursorFetch=true` 와 함께 양수 fetchSize를 줘야 합니다. 출처는 [MySQL Connector/J 구현 노트 — ResultSet](https://dev.mysql.com/doc/connector-j/en/connector-j-reference-implementation-notes.html)입니다. 강의는 500만 행을 놓고 VisualVM으로 두 방식의 힙 사용량을 비교합니다.

| | 클라이언트 커서(버퍼링) | 서버 커서(스트리밍) |
|---|---|---|
| 데이터 위치 | 앱 힙에 전부 | 대부분 DB 서버 |
| 앱 메모리 | 결과셋 크기에 비례 | fetchSize에 비례, 일정 |
| 커넥션 | 전송 후 곧 반납 가능 | 순회 끝까지 점유 |
| 적합한 크기 | 수만 건 미만 | 수십만~수백만 건 |

## Part 2 — Processor·Writer: I/O 횟수를 줄여라

예제는 **회원 등급 배치**입니다. 아이템마다 외부 API를 호출해 등급을 계산하고, 아이템마다 UPDATE를 칩니다. 강의 자료의 처방은 두 가지입니다.

1. **Processor에서 아이템 단위 API 호출을 빼고 Writer로 옮깁니다.** Writer는 청크 단위로 받으니, 거기서 RxJava `Flowable` 로 호출을 병렬화합니다.
2. **Writer에서 아이템 단위 UPDATE를 그룹 UPDATE로 바꿉니다.** 등급(BASIC/PREMIUM/VIP)별로 묶어 `UPDATE ... WHERE id IN (...)` 를 한 번씩만 실행합니다.

```java
appliedGradeUsers.stream()
        .collect(Collectors.groupingBy(User::getGrade))
        .forEach((grade, targetUsers) -> {
            final var userIds = targetUsers.stream().map(User::getId).toList();
            userRepository.updateGrade(grade, userIds);
        });
```

**강사 측정값 (ms)**

API 호출 병렬화:

| rows | 기존 | parallel 10 | parallel 30 | parallel 100 |
|---:|---:|---:|---:|---:|
| 1,000 | 155,880 | 18,062 | 8,215 | 4,132 |
| 50,000 | 7,884,623 | 896,208 | 381,589 | 193,680 |

UPDATE 일괄화:

| rows | 단건 UPDATE | update in |
|---:|---:|---:|
| 10,000 | 11,310 | 229 |
| 1,000,000 | 1,188,477 | 38,688 |

API 병렬도를 높이면 시간이 거의 선형으로 줄어듭니다. 다만 그만큼 **상대 API 서버에 부하를 그대로 넘기는** 셈입니다. 병렬도는 내 쪽 성능이 아니라 **상대가 허용하는 처리량**에 맞춰 정해야 합니다. 이 부분은 강의 자료의 표에는 없는, 제 해석입니다.

## Part 2 — Partitioning: gridSize·스레드·커넥션의 삼각형

파티셔닝은 Step 하나를 기간별, 속성별(예: 등급), 파일 행 범위별 파티션으로 나눠 워커 스텝들이 병렬로 처리하게 하는 구조입니다([Scaling and Parallel Processing — Partitioning](https://docs.spring.io/spring-batch/reference/scalability.html)). 강의 자료에서 가장 실무적인 대목은 세 숫자의 관계를 정리한 표입니다.

| gridSize | taskExecutor 스레드 | 커넥션 풀 | 결과 |
|---:|---:|---:|---|
| 30 | 30 | 30 | 이상적. 워커 30개가 각자 커넥션 사용 |
| 30 | 10 | 30 | **스레드 병목.** 실제 동시성 10 |
| 30 | 30 | 10 | **커넥션 병목.** 11번째부터 대기 후 `Connection is not available` |

gridSize를 키운다고 빨라지지 않습니다. **min(스레드, 커넥션)** 이 실제 동시성입니다. 그리고 메타데이터 저장소(JobRepository)도 같은 풀을 쓴다면 그 몫까지 계산에 넣어야 합니다.

## Part 3 — 재처리 가능한 배치: 멱등성

예제는 **가맹점 일일 결제 집계**입니다. 핵심은 "배치를 언제 몇 번 다시 돌려도 최종 상태가 같아야 한다" 입니다.

- **고유 키**: `사업자 번호 + 결제 일자`. 이 조합이 "일일 집계"라는 작업의 본질적 식별자입니다. DB 유니크 제약으로도 걸어 둡니다.
- 재실행할 때 세 가지 경우를 나눕니다.
  - 키가 없으면 **INSERT**
  - 키는 있는데 재집계 금액이 다르면 **UPDATE**
  - 금액이 같으면 **아무것도 하지 않음**
- 집계 쿼리에서 `ONLY_FULL_GROUP_BY` 모드 때문에 걸리는 지점, Querydsl로 자동 재처리 대상을 고르는 방법도 다룹니다.

실패 전략을 **도메인에 따라 다르게** 가져가라는 정리도 좋았습니다. 쿠폰 발급처럼 정합성이 덜 치명적인 도메인은 *부분 실패 허용*(skip)이 낫고, 가맹점 정산처럼 돈이 걸린 도메인은 *전체 실패 후 수정·재처리*가 낫습니다. 그리고 장시간 배치는 처음부터가 아니라 **실패한 부분만** 재처리할 수 있게 설계해야 합니다.

## Part 3 — HTTP Page Item Reader: 남의 DB를 직접 읽지 마라

외부 팀 데이터(예제는 가입 쿠폰 발급 Job)를 읽을 때, 그 DB에 직접 붙지 말고 **페이지 단위 HTTP API**로 읽는 리더를 만들라는 내용입니다. 강의 자료가 드는 이유는 다음과 같습니다.

- **의존성**: 상대 DB의 증설·버전업·장애, 접속 정보 변경이 내 배치로 번지지 않습니다.
- **무결성·보안**: 직접 접근하면 JPA 더티 체킹 같은 경로로 의도치 않은 쓰기가 생길 수 있습니다. API는 계약된 데이터만 내줍니다.
- **변경 대응**: 상대 엔티티 구조가 바뀌어도 API 계약이 완충 지대가 됩니다.

## Part 3 — 배치 테스트 노하우

- **`JobLauncherTestUtils`**: `launchJob()` 으로 End-to-End 테스트를 하고(권장), `launchStep()` 으로 Step 하나만 격리해서 테스트합니다([Unit Testing](https://docs.spring.io/spring-batch/reference/testing.html)).
- **공통 지원 클래스**: `@SpringBatchTest` 와 자주 쓰는 메서드를 추상 클래스(강의에서는 `BatchTestSupport`)에 모으고 상속해서 씁니다.
- **given 셋업**: 복잡한 데이터는 `@Sql` 이나 JSON 파일로 준비합니다. 케이스를 늘리는 비용이 크게 줄어듭니다.
- **외부 의존 제거**: Mockito의 `when().thenReturn()` 을 쓰고, `RestTemplate` 이면 `MockRestServiceServer` 로 HTTP를 가로챕니다.
- 마지막 장은 "지속 가능한 테스트 코드"에 대한 고찰입니다.

## 근거의 한계

- **성능 수치는 전부 강사 1인의 측정값입니다(②등급, 벤더·저자 자체 측정에 준함).** 하드웨어, MySQL 설정, 반복 횟수, 분산이 공개되어 있지 않습니다. 같은 비교를 다룬 중립 제3자의 헤드투헤드 벤치마크는 찾지 못했습니다. 절대값을 다른 환경으로 옮겨 쓰면 안 됩니다.
- Limit-Offset 표에서 500만 건 값은 강의 자료에 없어서 "—" 로 비웠습니다.
- `JdbcPagingItemReader` 의 키셋 동작, MySQL 스트리밍 조건, 파티셔닝 구조는 **공식 문서(①등급)** 로 확인할 수 있는 사실입니다. API 병렬도와 상대 서버 부하, JobRepository의 커넥션 몫은 제 해석입니다.
- 이 글은 요약이라 생략된 맥락이 많습니다. 정확한 코드와 설명은 첨부한 원본 PDF와 저자의 공개 저장소에서 확인하세요. 원본 PDF의 저작권은 저자 김남윤 님에게 있습니다.

## References

1. 김남윤, 「Spring Batch : 성능 튜닝부터 실전 전략까지」 강의 자료(PDF, 344쪽) — [/assets/pdf/spring-batch-lecture.pdf](/assets/pdf/spring-batch-lecture.pdf). 저작권은 저자에게 있음.
2. 김남윤, 블로그 — <https://cheese10yun.github.io/>
3. 김남윤, GitHub `spring-batch5` — <https://github.com/cheese10yun/spring-batch5>
4. Spring Batch Reference Documentation — <https://docs.spring.io/spring-batch/reference/>
5. Spring Batch — Database ItemReaders — <https://docs.spring.io/spring-batch/reference/readers-and-writers/database.html>
6. Spring Batch — Configuring Skip Logic — <https://docs.spring.io/spring-batch/reference/step/chunk-oriented-processing/configuring-skip.html>
7. Spring Batch — Retry Logic — <https://docs.spring.io/spring-batch/reference/step/chunk-oriented-processing/retry-logic.html>
8. Spring Batch — Scaling and Parallel Processing — <https://docs.spring.io/spring-batch/reference/scalability.html>
9. Spring Batch — Unit Testing — <https://docs.spring.io/spring-batch/reference/testing.html>
10. MySQL Connector/J — JDBC API Implementation Notes (ResultSet streaming) — <https://dev.mysql.com/doc/connector-j/en/connector-j-reference-implementation-notes.html>
