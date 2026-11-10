---
layout: post
title: "Spring Batch 아키텍처 — 메타데이터가 재시작을 만들고, 확장 모델 여섯 개는 '병목이 어디냐'로 고른다 (Spring Batch 6 기준)"
date: 2026-11-10 23:58:22 +0900
categories: [backend, batch]
tags: [spring-batch, batch-architecture, partitioning, remote-chunking, local-chunking, fault-tolerance, performance]
---

> **검증 범위.** 개념·동작·버전별 변화는 전부 Spring Batch 공식 레퍼런스(Domain Language, Scaling and Parallel Processing, What's new in Spring Batch 6)에서 확인했다. 성능 수치는 공식 문서가 직접 쓴 한 문장("수백 MB 파일 읽고 쓰기는 일반 하드웨어로 1분 안쪽")만 인용하고, 그 외 수치는 쓰지 않는다. "~일 것이다"로 표시한 부분은 문서에서 끌어낸 내 추론이다.

오늘 Spring Batch 글이 이미 두 편 나갔다. [김남윤 강의 정리]({% post_url 2026-11-10-spring-batch-performance-tuning-lecture-notes %})는 읽기 성능(Limit-Offset → No-Offset → Cursor)과 파티셔닝을, [cheese10yun/spring-batch5 리포 정리]({% post_url 2026-11-10-spring-batch5-fastcampus-repo-summary %})는 실습 코드를 다룬다. 이 글은 그 아래층 — **프레임워크가 어떻게 생겼고, 그 생김새가 성능·데이터 처리 선택을 어떻게 제약하는지**를 공식 레퍼런스로 정리한다.

## 1. 아키텍처 — 실행 로직보다 메타데이터가 본체다

공식 문서의 도메인 그림은 단순하다. `Job` 은 하나 이상의 `Step` 을 갖고, 각 Step 은 `ItemReader` 하나, 선택적 `ItemProcessor`, `ItemWriter` 하나를 갖는다. Job 은 `JobOperator` 로 실행·중지하고, 실행 중인 프로세스의 메타데이터는 `JobRepository` 에 저장·복원된다([Domain Language](https://docs.spring.io/spring-batch/reference/domain.html)).

핵심은 실행 단위를 세 겹으로 나눈 것이다.

| 개념 | 정의 | 역할 |
|---|---|---|
| `JobInstance` | **Job + 식별(identifying) JobParameters** | "1월 1일자 정산" 같은 논리적 실행. 재시작의 기준 |
| `JobExecution` | JobInstance 를 실행해 본 **한 번의 시도** | 상태·시작/종료 시각·ExitStatus·ExecutionContext 를 저장 |
| `StepExecution` | Step 을 실행해 본 한 번의 시도 | 커밋·롤백 횟수, 읽기/쓰기 건수 등 |

문서의 예가 이 구조의 의도를 잘 보여 준다. 1월 1일자 Job 이 21:00 에 시작해 21:30 에 실패하면 `BATCH_JOB_EXECUTION` 에 FAILED 행이 하나 남는다. 다음 날 같은 식별 파라미터(1월 1일)로 다시 돌리면 **JobInstance 는 그대로 하나이고 JobExecution 만 하나 늘어난다.** 같은 인스턴스를 쓰면 "멈춘 곳부터", 새 인스턴스면 "처음부터"다. 같은 JobInstance 가 이미 실행 중일 때 또 띄우면 `JobExecutionAlreadyRunningException` 이 난다. 반면 서로 다른 JobInstance(1월 1일분과 2일분)를 동시에 돌리는 건 막지 않는다 — 같은 데이터를 건드려 DB 락이 걸릴지는 스케줄러의 책임이다.

"멈춘 곳부터"를 가능하게 하는 게 `ExecutionContext` 라는 영속 property bag 이다. 리더가 "몇 번째 줄까지 읽었다"를 여기에 저장해 두면 재시작 때 그 지점부터 다시 읽는다. **Spring Batch 의 재시작 가능성은 실행 코드가 아니라 메타데이터 테이블에서 나온다.**

### Spring Batch 6 에서 바뀐 기본값 — "resourceless"

Spring Batch 6 은 `DefaultBatchConfiguration` 의 기본 인프라를 **resourceless**(5.2 에서 도입된 `ResourcelessJobRepository`)로 바꿨다. 메타데이터용 인메모리 DB(H2·HSQLDB)가 더 이상 필요 없고, DB 커넥션·트랜잭션을 쓰지 않아 메타데이터를 안 쓰는 경우의 기본 성능과 메모리 사용이 좋아진다고 문서는 설명한다. JDBC 저장소를 쓰려면 새 애너테이션 `@EnableJdbcJobRepository`(또는 `@EnableMongoJobRepository`)로 명시한다([What's new in 6](https://docs.spring.io/spring-batch/reference/whatsnew.html)).

여기서 끌어낼 수 있는 결론(내 추론): resourceless 는 실행 이력을 영속하지 않으므로, 위에서 말한 "같은 JobInstance 로 멈춘 곳부터 재시작"이 필요한 Job — 정산·대량 적재처럼 중간 실패가 비싼 Job — 에는 JDBC 저장소를 **명시적으로** 켜야 한다. 기본값이 바뀐 만큼, 업그레이드하면서 이걸 놓치면 재시작이 조용히 안 되는 상태가 될 수 있다.

6 버전은 설정도 줄였다. `JobRepository` 가 `JobExplorer` 를, `JobOperator` 가 `JobLauncher` 를 확장하게 되어 별도 빈이 필요 없고, 트랜잭션 매니저도 생략하면 `ResourcelessTransactionManager` 가 쓰인다.

## 2. 데이터 처리의 기본 단위 — 청크

청크 지향 처리는 "N 건 읽기 → 가공 → N 건 한 번에 쓰기"를 **한 트랜잭션**으로 묶는 반복이다. 6 버전에서는 5.1 부터 실험적으로 있던 새 구현 `ChunkOrientedStep` 이 정식이 되어 기존 `ChunkOrientedTasklet`/`TaskletStep` 을 대체한다. 내결함성도 정리됐다.

- **retry**: 별도 Spring Retry 라이브러리 대신 **Spring Framework 7 의 retry 기능** 기반(`RetryPolicy.builder().maxRetries(..).includes(..)`).
- **skip**: 전적으로 `SkipPolicy` 인터페이스 기반(예: `LimitCheckingExceptionHierarchySkipPolicy`).

```java
return new ChunkOrientedStepBuilder<Person, Person>("step", jobRepository, 100)
    .reader(itemReader)
    .writer(itemWriter)
    .faultTolerant()
    .retryPolicy(retryPolicy)   // 일시적 오류: 다시 시도
    .skipPolicy(skipPolicy)     // 불량 데이터: 건너뛰고 기록
    .build();
```

데이터 처리 관점의 구분은 이렇다 — **일시적 실패는 retry, 데이터 자체가 불량이면 skip, 둘 다 아니면 실패시키고 재시작.** 셋째 경로가 1절의 메타데이터에 기대는 부분이다.

6 버전은 운영 쪽도 보강했다. 비정상 종료된 실행을 SQL 로 직접 고치던 일을 `JobOperator#recover` 로 대신하고, graceful shutdown 시 실행 중인 Step 을 멈추고 재시작 가능한 상태로 저장하며, Micrometer 외에 **JFR 이벤트**(Job·Step 실행, 아이템 읽기·쓰기, 트랜잭션 경계)를 낸다.

## 3. 성능 — 확장 모델 여섯 개, 고르는 기준은 "병목이 어디냐"

공식 문서의 첫 조언이 가장 중요하다. **많은 배치 문제는 단일 스레드·단일 프로세스로 풀린다. 복잡한 구현을 고민하기 전에 현실적인 Job 의 성능부터 측정하라.** 문서는 일반 하드웨어로도 수백 MB 파일을 1분 안쪽에 읽고 쓸 수 있다고 쓴다([Scaling](https://docs.spring.io/spring-batch/reference/scalability.html)). 단일 스레드에서 쿼리 자체가 느리다면 확장 모델보다 [인덱스·청킹]({% post_url 2026-06-21-db-batch-performance-covering-index-and-chunking %})과 [읽기 방식]({% post_url 2026-11-10-spring-batch-performance-tuning-lecture-notes %})부터 고친다.

그래도 부족하면 아래 여섯 중에서 고른다. 표의 행은 모두 공식 문서의 서술을 옮긴 것이다.

| 모델 | 프로세스 | 병렬화되는 것 | 리더·라이터 스레드 안전 필요? | 트랜잭션·내결함성 | 맞는 상황 |
|---|---|---|---|---|---|
| Multi-threaded Step | 단일 | **Processor 만** | 아니오(메인 스레드가 직렬로 읽고 씀) | Processor 호출은 청크 트랜잭션에 **참여하지 않음** | 가공이 무겁고 읽기·쓰기는 가벼움 |
| Parallel Steps | 단일 | 서로 독립인 Step 들 | — | Step 별 | 책임이 다른 Step 들로 나뉨 |
| Local Chunking (6 신규) | 단일 | 청크 단위 처리·쓰기 | — | **위임한 ChunkProcessor 의 책임** | 멀티코어로 청크 자체를 병렬 처리 |
| Remote Chunking | 다중 | 가공·쓰기(워커) | — | 미들웨어가 내구성·전달 보장·단일 소비 필요 | 처리 비용 ≫ 읽기 비용, 매니저가 병목 아님 |
| Partitioning | 단일/다중 | 데이터 범위별 **Step 전체** | 각 워커가 자기 범위만 | 메시지는 내구성 불필요 — JobRepository 가 워커별 1회 실행 보장 | 데이터를 키 범위로 나눌 수 있음 |
| Remote Step (6 신규) | 다중 | Step 을 원격 노드에서 | — | Spring Integration 채널 경유 | Step 단위 분산 |

몇 가지는 표만으로는 놓치기 쉬워 따로 적는다.

**Multi-threaded Step 은 6 버전에서 모델이 바뀌었다.** 이전의 "병렬 반복" 방식은 상태 동기화가 많고 스로틀링·배압이 약해 트랜잭션 의미가 헷갈리고 성능도 나빴다는 게 문서의 자평이다. 6 버전은 **생산자-소비자** 모델로, 생산자 스레드와 소비자 스레드 사이에 크기가 제한된 내부 큐를 둔다. 청크가 쓰일 준비가 되면 생산자는 쓰기가 끝날 때까지 멈췄다가 다시 생산한다. 그래서 리더·라이터는 스레드 안전할 필요가 없지만 **처리량이 읽기·쓰기 속도에 묶일 수 있고**, 그 경우 문서는 local chunking 이나 local partitioning 을 권한다. Processor 는 여러 스레드에서 동시에 불리므로 스레드 안전해야 하고, 트랜잭션이 필요하면 `REQUIRED` 처럼 스스로 시작해야 한다(`MANDATORY` 는 실패한다).

**스레드를 늘리면 커넥션 풀이 따라와야 한다.** 문서는 Step 안의 풀링된 자원(예: `DataSource`)이 동시성을 제한할 수 있으니 풀을 원하는 스레드 수 이상으로 잡으라고 명시한다. 파티셔닝에서는 `gridSize` 가 단일 Step 이 task executor 를 요청으로 포화시키는 것을 막는다. 스레드 수·커넥션 수·대기 시간의 관계는 방금 쓴 [DB 커넥션 풀 × 스레드 풀]({% post_url 2026-11-10-db-connection-pool-vs-thread-pool-littles-law %}) 글의 리틀의 법칙이 그대로 적용된다.

**Remote Chunking 과 Partitioning 은 미들웨어 요구가 정반대다.** Remote chunking 은 아이템 자체를 메시지로 보내므로 미들웨어가 내구성·전달 보장·메시지당 단일 소비자를 갖춰야 한다. Partitioning 은 "어느 범위를 처리하라"는 StepExecution 요청만 보내고, 각 워커가 실행당 정확히 한 번 돌았는지는 JobRepository 메타데이터가 보장하므로 메시지는 내구성이 없어도 된다. **1절의 메타데이터가 여기서 분산 조정 장치로 다시 등장한다.**

**Local Chunking 은 내결함성을 넘겨준다.** `ChunkTaskExecutorItemWriter` 는 청크 트랜잭션도, retry·skip·chunk scanning 도 처리하지 않는다. 그건 위임받은 `ChunkProcessor` 의 일이고, task executor 의 수명 관리도 사용자 몫이다. 2절의 retry/skip 설정이 그대로 따라온다고 가정하면 안 된다.

## 4. 데이터 처리 — 단계를 끊어 흘리기(SEDA)

5.2 에서 `BlockingQueueItemReader`/`BlockingQueueItemWriter` 로 로컬 스레드 기반 SEDA(Staged Event-Driven Architecture) 처리가 들어왔고, 6 버전은 이를 **Spring Integration 메시지 채널**로 확장해 단계 사이를 비동기로 분리하고 변환·필터·라우팅을 채널에 맡길 수 있게 했다([What's new in 6](https://docs.spring.io/spring-batch/reference/whatsnew.html)). Job 하나 안에서 "추출 → 변환 → 적재"가 서로 다른 속도로 흐를 때 단계 사이에 큐를 두는 방식이다.

여기서 원칙(내 추론): 큐로 단계를 끊으면 각 단계의 처리량은 독립적으로 조절되지만, **청크 하나 = 트랜잭션 하나**라는 단순한 재시작 의미는 약해진다. 큐 안에 있던 아이템이 실패 시점에 어디까지 반영됐는지를 다시 따져야 하기 때문이다. 단순 청크로 시간 안에 끝나면 굳이 끊지 않는다 — 3절 첫 조언과 같은 결론이다.

## 5. 고르는 순서

1. **재시작이 필요한 Job 인가?** 필요하면 JDBC JobRepository 를 명시하고(6 버전 기본값은 resourceless), 식별 파라미터로 JobInstance 를 정의한다.
2. **단일 스레드로 측정한다.** 느리면 쿼리·인덱스·읽기 방식부터 고친다.
3. **병목이 어디인지 본다.** 가공이 병목이면 multi-threaded step → 더 크면 remote chunking. 읽기·쓰기까지 병목이면 local chunking 이나 partitioning. 서로 독립인 일이면 parallel steps.
4. **스레드를 늘린 만큼 커넥션 풀과 gridSize 를 맞춘다.**
5. **실패 경로를 정한다.** retry(일시적) / skip(불량 데이터) / 실패 후 재시작. local chunking 이면 이 설정을 ChunkProcessor 안에서 직접 한다.
6. **관측한다.** Micrometer 지표와 6 버전의 JFR 이벤트로 Step 별 읽기·쓰기·트랜잭션 경계를 본다.

## References

1. Spring Batch Reference, *The Domain Language of Batch*. <https://docs.spring.io/spring-batch/reference/domain.html>
2. Spring Batch Reference, *Scaling and Parallel Processing*. <https://docs.spring.io/spring-batch/reference/scalability.html>
3. Spring Batch Reference, *What's new in Spring Batch 6*. <https://docs.spring.io/spring-batch/reference/whatsnew.html>
4. (관련 글) 김남윤 Spring Batch 성능 튜닝 강의 정리 · cheese10yun/spring-batch5 리포 정리 · DB 커넥션 풀 × 스레드 풀 — 본문 링크 참조.
