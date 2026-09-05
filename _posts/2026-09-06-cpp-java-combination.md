---
layout: post
title: "C++과 Java 조합으로 할 만한 것들: 성능과 생산성을 함께 설계하기"
date: 2026-09-06 05:30:10 +0900
categories: [Architecture]
tags: [C++, Java, JNI, gRPC, Apache Arrow, Native, Performance, MSA]
---

# C++과 Java 조합으로 할 만한 것들

C++과 Java를 함께 사용한다고 해서 무조건 성능이 좋아지는 것은 아니다. 두 언어의 장점을 분명히 나누고, 경계 비용·메모리 소유권·배포 복잡성·장애 격리까지 설계해야 조합의 가치가 생긴다.

- **C++**: 낮은 지연시간, 세밀한 메모리 제어, 기존 native 라이브러리, CPU 집약 처리
- **Java**: 업무 로직, 네트워크 서버, 동시성 API, 생산성, 운영 도구와 생태계
- **공통 경계**: JNI, gRPC, Apache Arrow/Arrow Flight, 파일·메시지·HTTP API

가장 중요한 선택은 “어느 언어가 더 빠른가?”가 아니라 “어디를 프로세스 경계로 나누면 전체 시스템이 더 안전하고 운영 가능한가?”다.

## 1. 조합 패턴 한눈에 보기

| 패턴 | C++ 역할 | Java 역할 | 적합한 상황 |
| --- | --- | --- | --- |
| JNI | native 함수·라이브러리 | 애플리케이션·API | 프로세스 내부에서 직접 호출해야 할 때 |
| gRPC | native worker/service | 업무 API·orchestrator | 독립 배포와 장애 격리가 필요할 때 |
| Apache Arrow | 고속 데이터 처리 | 분석·서비스·데이터 파이프라인 | 대량 컬럼형 데이터를 복사 없이 교환할 때 |
| 파일/IPC | 엔진·배치 | 스케줄러·관리 API | 실시간 결합보다 안정적 비동기가 중요할 때 |
| 메시지 브로커 | 계산 worker | command·event 처리 | 재시도·확장·내구성이 필요할 때 |
| WebAssembly/별도 sandbox | 제한된 native 계산 | 실행 제어·보안 경계 | 사용자 코드나 위험한 계산을 격리할 때 |

이 글의 핵심 추천은 다음과 같다.

> 처음에는 Java와 C++을 별도 프로세스의 gRPC 서비스로 분리하고, 정말 필요한 좁은 경로에서만 JNI를 사용한다.

## 2. 가장 현실적인 조합: Java 서비스 + C++ worker

```text
Client
  │
  ▼
Java API / Spring
  │
  ├─ 인증·권한·업무 규칙
  ├─ 요청 검증·timeout
  ├─ DB·메시지·운영 API
  │
  ▼ gRPC / queue
C++ Worker
  ├─ 이미지·영상 처리
  ├─ 수치 계산·시뮬레이션
  ├─ 압축·암호화·native SDK
  └─ 결과 반환
```

Java는 요청 수명주기와 업무 흐름을 담당하고 C++은 계산 엔진이나 native 의존성이 필요한 작업을 담당한다. 두 프로세스가 분리되어 있으면 C++ segmentation fault가 Java API 프로세스까지 직접 죽이는 위험을 줄일 수 있다.

gRPC는 C++과 Java 양쪽에 공식 quick start와 생성 코드 흐름을 제공하며, 하나의 Protocol Buffers 계약으로 클라이언트와 서버 stub을 생성할 수 있다.[4][5]

### 실제로 만들 만한 프로젝트

- Java 주문 API + C++ 실시간 가격 계산기
- Java 영상 업로드 API + C++ 이미지·영상 변환 worker
- Java 문서 처리 서비스 + C++ OCR·형태 분석 엔진
- Java 검색 API + C++ 고속 ranking/reranking worker
- Java 시뮬레이션 관리 API + C++ 수치 계산 엔진
- Java ML serving gateway + C++ inference backend
- Java 로그·이벤트 파이프라인 + C++ 압축·필터링 worker

## 3. JNI: 가장 빠른 호출이지만 가장 조심해야 하는 경계

JNI(Java Native Interface)는 Java 코드가 native 코드와 상호 운용하도록 하는 표준 인터페이스다. Oracle JNI 사양은 native method의 컴파일·로딩·링킹, Java 객체·배열 접근, 예외 처리, VM invocation까지 정의한다.[1]

### JNI를 선택할 만한 경우

- 이미 검증된 C/C++ 라이브러리를 재사용해야 한다.
- 호출 빈도가 높고 IPC 비용이 문제가 된다.
- native 메모리와 Java heap 사이 복사가 병목이다.
- 하드웨어 SDK가 C/C++ API만 제공한다.
- 프로세스 분리가 오히려 기능상 불가능하다.

### JNI를 피하는 편이 좋은 경우

- 기능이 작고 gRPC/HTTP로 충분하다.
- C++ 코드가 자주 변경된다.
- 장애 격리가 중요하다.
- 팀이 native 메모리와 JVM 경계를 운영할 경험이 부족하다.
- 요청마다 큰 객체를 Java와 native 사이에서 변환한다.

### JNI의 운영 위험

- native memory leak은 Java GC가 해결하지 못한다.
- C++ crash가 JVM 프로세스를 종료시킬 수 있다.
- Java 예외와 C++ exception 경계를 명확히 해야 한다.
- thread attach/detach와 native thread 수명을 관리해야 한다.
- 플랫폼별 `.so`, `.dylib`, `.dll` 빌드와 배포가 필요하다.
- ABI와 compiler/runtime 호환성을 관리해야 한다.

JNI 경계를 설계할 때는 Java 객체를 그대로 넘기기보다 단순한 primitive·direct buffer·명시적인 handle API를 사용하는 것이 좋다.

```java
public final class NativeEngine implements AutoCloseable {
    private final long handle;

    public NativeEngine(Config config) {
        this.handle = nativeCreate(config.serialized());
    }

    public native Result execute(ByteBuffer input);

    @Override
    public void close() {
        nativeDestroy(handle);
    }

    private static native long nativeCreate(byte[] config);
    private static native void nativeDestroy(long handle);
}
```

핵심은 native handle의 소유권과 해제 시점을 명확히 하는 것이다. `finalize()`에 의존하지 말고 `AutoCloseable`, 명시적 release, try-with-resources를 사용해야 한다.

## 4. gRPC: 기본 선택으로 좋은 프로세스 경계

Java와 C++을 gRPC로 연결하면 언어별 구현은 분리하면서 통신 계약은 공유할 수 있다.

```protobuf
syntax = "proto3";

service ScoringService {
  rpc Score(ScoreRequest) returns (ScoreResponse);
}

message ScoreRequest {
  bytes payload = 1;
  string model_version = 2;
}

message ScoreResponse {
  double score = 1;
  string engine_version = 2;
}
```

C++ 서비스는 생성된 server interface를 구현하고, Java 서비스는 생성된 stub으로 호출한다. gRPC 공식 C++ quick start는 CMake와 Protocol Buffers를 이용해 client/server 코드를 생성·빌드하는 흐름을 보여주며, Java quick start는 Gradle 기반 client/server 예제를 제공한다.[4][5]

### gRPC를 운영 가능하게 만드는 항목

- deadline을 모든 요청에 전달한다.
- status code를 업무 오류와 시스템 오류로 구분한다.
- payload 크기 제한을 둔다.
- TLS와 인증을 적용한다.
- retry는 idempotent RPC에만 적용한다.
- correlation ID와 trace context를 전파한다.
- 서버의 graceful shutdown을 구현한다.
- 계약 변경은 backward-compatible하게 진행한다.
- C++ worker의 busy 상태와 queue depth를 메트릭으로 노출한다.

### 동기와 비동기 worker

Java API가 C++ 계산이 끝날 때까지 기다려야 한다면 gRPC unary RPC를 사용할 수 있다. 계산이 오래 걸리거나 재시도가 필요한 경우에는 다음처럼 비동기 모델이 더 적합하다.

```text
Java API → Job 생성 → 202 Accepted
             │
             ▼
       queue / job store
             │
             ▼
       C++ worker 처리
             │
             ▼
       result store + event
```

이 구조는 HTTP 요청과 계산 시간을 분리하고, worker 재시작·재처리·진행률 조회를 설계하기 쉽다.

## 5. Apache Arrow: 데이터 교환 비용 줄이기

대량 데이터를 Java와 C++ 사이에서 JSON으로 주고받으면 직렬화·역직렬화와 복사 비용이 커진다. Apache Arrow는 컬럼형 메모리 포맷과 언어별 구현을 제공한다. C++ 문서는 Arrow 배열·테이블, Parquet·CSV 입출력, compute kernel, partitioned dataset 처리를 안내한다.[2] Java 구현은 ValueVector, schema, IPC, Flight RPC, C Data Interface와 Java-to-C++ 연동 문서를 제공한다.[3]

### Arrow가 적합한 사례

- Java가 받은 대량 이벤트를 C++ 분석 엔진에 전달
- C++이 생성한 feature matrix를 Java serving 계층에 전달
- Java ETL과 C++ compute kernel 연결
- Parquet dataset을 C++로 필터링하고 Java API로 결과 제공
- Arrow Flight로 분석 데이터를 네트워크 전송

```text
Java ingestion
    │
    ▼ Arrow RecordBatch / IPC
C++ compute kernel
    │
    ▼ Arrow Table / Flight
Java API·query service
```

Arrow가 곧바로 “zero-copy”를 보장하는 것은 아니다. language binding, allocator, buffer ownership, IPC 경계, 네트워크 전송에 따라 복사가 발생할 수 있다. 실제 시스템에서는 batch 크기·메모리 사용량·GC pressure·native allocator를 측정해야 한다.

## 6. 파일·IPC·메시지 기반 조합

모든 C++ 계산을 실시간 RPC로 묶을 필요는 없다. 다음과 같은 경우에는 파일·object storage·메시지 브로커가 더 단순하고 안정적이다.

- 수초 이상 걸리는 배치 계산
- 재처리가 중요한 분석 작업
- 입력 데이터가 이미 파일로 존재한다.
- 요청과 결과가 강하게 동기화될 필요가 없다.
- native worker의 scale-out이 별도 큐로 관리되어야 한다.

```text
Java Scheduler
  → Job metadata + input URI
  → Queue
  → C++ worker
  → output URI + status event
  → Java API
```

이 모델에서는 idempotency key, 작업 상태, heartbeat, lease, retry count, dead-letter 상태를 명시해야 한다. “프로세스가 종료 코드 0으로 끝났다”만으로 데이터 처리가 성공했다고 보면 안 되고, 출력 파일 존재·행 수·checksum·결과 상태를 확인해야 한다.

## 7. 실제로 해볼 만한 프로젝트 6가지

### 프로젝트 1: Java 주문·가격 API + C++ pricing engine

Java는 주문 요청, 인증, DB, API를 담당하고 C++은 대량 가격 계산과 할인 규칙을 수행한다.

검증 포인트:

- 동일 입력에 대한 결정성
- gRPC deadline
- 가격 엔진 버전 기록
- 계산 결과 재현
- C++ crash 격리

### 프로젝트 2: Java 미디어 API + C++ transcoding worker

Java는 업로드·권한·metadata를 관리하고 C++/FFmpeg 기반 worker가 변환을 수행한다.

검증 포인트:

- 비동기 job 상태
- 진행률과 취소
- 파일 checksum
- worker 재시작 후 재처리
- 원본 보존 정책

### 프로젝트 3: Java 검색 API + C++ ranking engine

Java는 검색 API와 후보 집합을 만들고 C++은 낮은 latency의 scoring/reranking을 담당한다.

검증 포인트:

- p50/p95/p99 latency
- payload 크기
- model/engine version
- timeout fallback
- relevance 평가셋

### 프로젝트 4: Java AI gateway + C++ inference service

Java는 인증·quota·모델 라우팅·요청 추적을 맡고 C++은 native inference runtime이나 모델 실행을 맡는다.

검증 포인트:

- batch와 streaming
- GPU/CPU 자원 격리
- queue backpressure
- token/요청 비용 추적
- 모델 warm-up과 graceful shutdown

### 프로젝트 5: Java 데이터 파이프라인 + C++ Arrow compute

Java는 ingestion과 작업 제어를 맡고 C++은 Arrow 배열 기반 필터·집계·feature 계산을 수행한다.

검증 포인트:

- batch 크기별 처리량
- heap/native memory 사용량
- IPC copy 횟수
- schema compatibility
- 결과 checksum과 데이터 품질

### 프로젝트 6: Java 운영 플랫폼 + C++ 장치/센서 adapter

Java는 사용자·권한·설정·이력·알림을 관리하고 C++은 제조 장치나 OS native SDK와 연결한다.

검증 포인트:

- 장치 연결 끊김 복구
- native thread 관리
- 명령 중복 방지
- 안전한 timeout
- 장치 상태와 DB 상태의 reconciliation

## 8. 무엇을 선택할 것인가

### JNI를 선택

- 호출 빈도가 매우 높다.
- 프로세스 내부 공유가 필요하다.
- native library 재사용이 핵심이다.
- crash 위험과 플랫폼별 배포를 감당할 수 있다.

### gRPC를 선택

- 독립 배포가 필요하다.
- C++ 장애를 Java에서 격리해야 한다.
- 계약 기반 API가 필요하다.
- Java와 C++ 팀·릴리스 주기가 다르다.

### Arrow를 선택

- 데이터가 크고 표 형태다.
- JSON 직렬화 비용이 크다.
- batch/columnar compute가 중요하다.
- Java·C++ 양쪽에서 schema와 buffer lifecycle을 관리할 수 있다.

### 메시지·파일을 선택

- 작업이 오래 걸린다.
- 재처리와 내구성이 중요하다.
- 결과를 나중에 조회해도 된다.
- queue와 result store를 운영할 수 있다.

## 9. 실패하기 쉬운 설계

### “성능이 필요하니 JNI부터”

실제 병목이 네트워크, DB, 외부 API, 알고리즘, lock인지 측정하지 않고 JNI를 도입하면 복잡성만 늘어난다. 먼저 프로파일링하고, 큰 비용이 확인된 좁은 함수만 native로 옮긴다.

### 큰 Java 객체를 C++ 구조체로 매번 변환

객체 그래프 변환 비용과 메모리 소유권 문제가 커진다. batch, primitive array, direct buffer, Arrow schema, compact protobuf를 검토한다.

### C++ worker를 동기 API에 직접 묶기

긴 계산과 사용자 HTTP 요청을 하나의 deadline으로 묶으면 thread pool과 connection pool이 고갈될 수 있다. 작업 상태와 결과를 분리하는 비동기 job 모델이 더 적합할 수 있다.

### 버전과 계약을 기록하지 않기

C++ engine version, model version, schema version, Java API version을 결과에 남기지 않으면 장애 재현과 결과 설명이 어려워진다.

### native 메모리를 Java GC가 관리한다고 생각하기

Arrow allocator, direct buffer, native handle, C++ 객체의 수명은 JVM heap과 별개로 관리해야 한다. close·release·scope를 설계하고 native memory metric을 수집해야 한다.

## 결론

C++과 Java 조합은 다음처럼 역할을 나눌 때 가장 설득력이 있다.

- Java는 API·업무 흐름·권한·데이터·운영을 담당한다.
- C++은 계산 엔진·native SDK·낮은 지연시간 경로를 담당한다.
- gRPC는 기본 프로세스 경계로 사용한다.
- JNI는 측정으로 필요성이 확인된 좁은 경로에만 사용한다.
- Arrow는 대량 컬럼형 데이터 교환에 사용한다.
- 오래 걸리는 작업은 queue·job store·result event로 비동기화한다.

좋은 조합은 언어를 두 개 쓰는 것이 아니라, 각 언어의 책임과 실패 경계를 명확히 하는 것이다. Java의 운영성과 C++의 계산 성능을 결합하려면 호출 비용보다 더 중요한 **메모리 소유권, timeout, 버전 계약, 재처리, 관측 가능성**을 먼저 설계해야 한다.

## 참고 자료

[1] Oracle Java Native Interface Specification — JNI 설계와 native method 경계  
[2] Apache Arrow C++ Getting Started — 배열·테이블·파일·compute·dataset  
[3] Apache Arrow Java Documentation — Java API·IPC·Flight·C Data Interface  
[4] gRPC C++ Quick Start — CMake·Protocol Buffers·C++ client/server  
[5] gRPC Java Quick Start — Gradle·Java client/server·Protocol Buffers

## 출처

- JNI Specification: https://docs.oracle.com/en/java/javase/21/docs/specs/jni/index.html
- Apache Arrow C++: https://arrow.apache.org/docs/cpp/getting_started.html
- Apache Arrow Java: https://arrow.apache.org/java/current/
- gRPC C++ Quick Start: https://grpc.io/docs/languages/cpp/quickstart/
- gRPC Java Quick Start: https://grpc.io/docs/languages/java/quickstart/

## Sources

[1] https://docs.oracle.com/en/java/javase/21/docs/specs/jni/index.html — Java Native Interface Specification
[2] https://arrow.apache.org/docs/cpp/getting_started.html — Apache Arrow C++ Getting Started
[3] https://arrow.apache.org/java/current — Apache Arrow Java Documentation
[4] https://grpc.io/docs/languages/cpp/quickstart — gRPC C++ Quick Start
[5] https://grpc.io/docs/languages/java/quickstart — gRPC Java Quick Start
