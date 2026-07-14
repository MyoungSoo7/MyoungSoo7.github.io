---
layout: post
title: "장애는 어디서 새는가 — 관측·추적·진단으로 보는 장애대응과 성능분석"
date: 2026-07-14 15:00:00 +0900
categories: [backend, devops, observability]
tags: [observability, apm, prometheus, grafana, elk, distributed-tracing, trace-id, slow-query, thread-dump, heap-dump, incident-response, msa, kubernetes]
---

새벽 4시, 알림이 울린다. "502가 6분째 뜬다"는 걸 사용자가 나보다 먼저 발견했다면, 그건 관측(observability)이 실패한 것이다. 장애대응의 승부는 **불이 난 뒤 얼마나 빨리 끄느냐가 아니라, 불씨를 얼마나 먼저 보느냐**에서 갈린다.

이 글은 MSA를 K3s 위에서 운영하며 실제로 겪은 장애들을 재료로, 장애대응과 성능분석에 쓰는 도구 9개를 **관측 → 탐지 → 추적 → 진단 → 심층분석** 흐름으로 정리한다. 도구 나열이 아니라 "장애가 났을 때 이 순서로 좁혀 들어간다"는 지도를 그리는 것이 목적이다.

> 핵심 관점: 장애는 한 지점에서 터지지만, 원인은 **여러 계층(로그·메트릭·트레이스·JVM·DB)** 에 흩어져 있다. 각 계층에 맞는 도구를 알아야 5분 안에 원인에 도달한다.

---

## 0. 관측성의 세 기둥 (Three Pillars)

본론 전에 지도부터. 관측성은 세 가지 신호로 구성된다.

| 신호 | 질문 | 도구 |
|---|---|---|
| **Metrics** | "지금 시스템이 건강한가?" (수치·추세) | Prometheus, Grafana |
| **Logs** | "무슨 일이 있었나?" (사건 기록) | ELK, 로그 추적 ID |
| **Traces** | "이 요청이 어디서 느렸나?" (요청 여정) | Distributed Tracing, APM |

메트릭으로 **탐지**하고, 트레이스로 **위치를 좁히고**, 로그로 **원인을 확정**한다. 이 셋이 서로를 가리키도록 엮는 것이 관측성 설계의 핵심이다.

---

## 1. 탐지 — Prometheus & Grafana

### Prometheus — 메트릭 수집

Prometheus는 각 서비스가 노출한 `/actuator/prometheus` 엔드포인트를 주기적으로 **pull(scrape)** 해 시계열로 저장한다. Spring Boot라면 Micrometer가 JVM·HTTP·커스텀 메트릭을 자동으로 노출한다.

```
# HELP http_server_requests_seconds
http_server_requests_seconds_count{uri="/orders",status="500"}  12
jvm_memory_used_bytes{area="heap"}  1.34e9
```

핵심은 **RED / USE 방법론**이다.

- **RED** (요청 관점): Rate(초당 요청), Errors(에러율), Duration(지연). 서비스 상태를 보는 3대 지표.
- **USE** (자원 관점): Utilization(사용률), Saturation(포화), Errors. CPU·메모리·커넥션풀 관점.

### Grafana — 시각화 + 경보

Grafana는 Prometheus 데이터를 대시보드로 그리고, **Alertmanager**와 엮어 임계치를 넘으면 알림을 보낸다. 여기서 장애대응의 첫 번째 원칙이 나온다.

> **사용자보다 먼저 알아야 한다.** 5xx 비율이 1분 이상 임계치를 넘으면, 6분 뒤 사용자가 문의하기 전에 봇이 30초 안에 알려야 한다.

내 홈랩에서는 Alertmanager의 경보를 모바일 푸시로 받도록 연동해, 새벽 장애도 폰이 먼저 울리게 만들어 두었다. 탐지가 늦으면 나머지 도구가 아무리 좋아도 소용없다.

---

## 2. 추적 — 로그 추적 ID & Distributed Tracing

### 로그 추적 ID (Correlation / Trace ID)

MSA에서 하나의 사용자 요청은 `gateway → order → inventory → points → payment` 여러 서비스를 거친다. 각 서비스가 따로 로그를 남기면, 장애 시 **어느 로그가 같은 요청인지** 알 수 없다.

해법은 **요청 진입점에서 Trace ID를 발급**해 모든 다운스트림 호출과 로그에 전파하는 것이다. Spring이라면 MDC(Mapped Diagnostic Context)에 넣어 로그 패턴에 박는다.

```
%d{HH:mm:ss} [%X{traceId}] [%thread] %-5level %logger - %msg%n
```

```
12:04:01 [a1b2c3d4] order-service   주문 생성 orderId=1024
12:04:01 [a1b2c3d4] inventory-service 재고 예약 productId=55
12:04:02 [a1b2c3d4] points-service  포인트 차감 실패 → 보상 트리거
```

`a1b2c3d4` 하나로 5개 서비스에 흩어진 로그를 한 줄로 꿰맨다. ELK에서 이 ID로 검색하면 요청의 전체 여정이 시간순으로 복원된다. **분산 로그의 첫 단추.**

### Distributed Tracing — 요청의 지도

Trace ID가 로그를 꿰맨다면, 분산 추적은 그 여정을 **시각적 타임라인(span 트리)** 으로 그린다. OpenTelemetry / Jaeger / Zipkin이 대표적이다.

```
[gateway]           ├────────────────────────────────┤ 820ms
  [order]             ├──────────────────────────────┤ 780ms
    [inventory]         ├──┤ 40ms
    [points]            ├──┤ 35ms
    [payment(외부)]        ├────────────────────────┤ 600ms  ← 병목!
```

각 span은 서비스·소요시간·부모관계를 담는다. 위 그림을 보면 전체 820ms 중 600ms가 외부 결제 API였음을 **즉시** 알 수 있다. 로그를 아무리 뒤져도 안 보이는 "어디서 느렸나"를 트레이스는 한눈에 보여준다.

### APM — 이 모두를 묶는 상위 개념

APM(Application Performance Monitoring)은 메트릭·트레이스·에러를 애플리케이션 관점에서 통합한 것이다(Datadog, Elastic APM, Pinpoint, Scouter 등). 트랜잭션별 응답시간 분포, 느린 트랜잭션 자동 캡처, 에러 발생 지점 추적을 한 화면에서 제공한다. 앞의 Prometheus/Trace를 **애플리케이션 단위로 재조립**한 뷰라고 보면 된다.

---

## 3. 로그 심층 — ELK, 그리고 실제 장애

### ELK 스택

- **Elasticsearch** — 로그를 색인해 검색 가능하게
- **Logstash / Fluent-bit** — 로그 수집·가공 파이프라인
- **Kibana** — 검색·시각화 UI

쿠버네티스에서는 각 파드가 stdout으로 로그를 뱉고, Fluent-bit가 노드마다 그것을 긁어 Elasticsearch로 보낸다. 그래서 애플리케이션은 **파일이 아니라 stdout**으로 로깅해야 한다(cloud-native 로깅).

### 실제 장애 — 로그가 스스로를 죽이다

한번은 새벽에 ELK가 폭주했다. 원인은 뜻밖이었다. 배치 폴링 쿼리 하나가 **파라미터 바인딩이 누락된 채** 배포되어, 2초 주기의 폴링마다 예외를 던졌다. 기능은 리트라이로 굴러갔지만, **2초마다 ERROR 스택트레이스가 쌓이며** Elasticsearch 색인 부하가 폭증하고 디스크가 차기 시작했다.

여기서 배운 교훈 둘:

1. **로그 폭증 자체가 장애다.** 애플리케이션은 멀쩡해 보여도 관측 인프라가 먼저 죽는다. ERROR 로그 rate에도 경보를 걸어야 한다.
2. **단위 테스트로는 못 막는다.** 컴파일·단위테스트는 통과했지만 런타임 쿼리 바인딩에서 터졌다. 이런 결함은 빌드 단계 정적 검증(쿼리 파라미터 매칭 체크)이나 통합 테스트에서 잡아야 한다.

로그는 진실을 담지만, 너무 많은 진실은 그 자체로 재앙이 된다.

---

## 4. DB 진단 — Slow Query

응답이 느리다면 열에 아홉은 DB다. **느린 쿼리 로그(slow query log)** 를 켜서 임계시간(예: 1초)을 넘는 쿼리를 잡는다.

MSA/JPA에서 가장 흔한 범인은 **N+1 문제**다. 주문 목록 10개를 조회하는데, 각 주문의 상품을 개별 쿼리로 가져오면 1 + 10번 쿼리가 나간다.

```java
// N+1 발생
List<Order> orders = orderRepository.findAll();       // 1번
orders.forEach(o -> o.getItems().size());             // N번 (지연로딩)

// 해결 — fetch join
@Query("SELECT o FROM Order o JOIN FETCH o.items")     // 1번으로
```

진단 순서: slow query 로그로 **어떤 쿼리가** 느린지 찾고 → `EXPLAIN`으로 **실행계획**(인덱스를 타는지, full scan인지)을 보고 → 인덱스 추가나 fetch 전략으로 고친다. 애플리케이션 코드가 아니라 쿼리 실행계획을 보는 것이 성능분석의 절반이다.

---

## 5. JVM 심층 — Thread Dump & Heap Dump

메트릭·로그·트레이스로도 안 잡히는 문제는 JVM 내부에 있다. 이때 **덤프**를 뜬다.

### Thread Dump — 멈춘 스레드를 잡는다

특정 순간 모든 스레드의 상태(스택 트레이스)를 찍는다. **응답 지연·행(hang)·데드락**을 진단한다.

```bash
jstack <pid> > thread.txt
# 또는 컨테이너: kubectl exec 후 actuator/threaddump
```

보는 법:
- `BLOCKED` 스레드가 많다 → 락 경합. 무엇을 기다리는지(`waiting to lock`) 추적.
- `Found one Java-level deadlock` → 데드락. 두 스레드가 서로의 락을 물고 있다.
- 같은 지점에서 멈춘 스레드가 수십 개 → 그 지점(외부 API, DB 커넥션 대기)이 병목.

> 운영 팁: 나는 Spring Boot 파드의 스레드/힙/GC 상태를 actuator 지표로 원격 진단하는 봇 명령을 만들어 두었다. 새벽에 "스레드가 비정상적으로 많은가?"를 폰에서 바로 물어볼 수 있다. 덤프를 뜨는 절차를 자동화해 두면 장애 시 손이 떨리지 않는다.

### Heap Dump — 메모리 누수를 잡는다

힙 전체의 객체 스냅샷을 찍는다. **OOM·메모리 누수·GC 과다**를 진단한다.

```bash
jmap -dump:live,format=b,file=heap.hprof <pid>
# MAT(Eclipse Memory Analyzer)로 분석
```

전형적 시나리오: 힙 사용량이 톱니파형으로 오르내리다가, **GC 후에도 바닥이 계속 높아진다** → 누수 신호. Heap dump를 MAT로 열어 "Dominator Tree"로 **누가 메모리를 붙잡고 안 놓는지**(예: 무한히 커지는 static 캐시, 닫히지 않는 커넥션)를 찾는다.

관련 GC 지표들도 함께 본다: Full GC 빈도가 잦아지고, Metaspace가 계속 차오르면(클래스로더 누수) 재기동 전에 원인을 찾아야 한다.

---

## 6. 장애대응 플레이북 — 순서가 곧 실력

도구를 아는 것과 **위기에서 순서대로 쓰는 것**은 다르다. 실제 대응은 이렇게 좁혀 들어간다.

```
1. 탐지    Grafana 대시보드 — 5xx? 지연? 어느 서비스?
              ↓ (Alertmanager가 이미 폰을 울렸어야 정상)
2. 범위    어느 서비스/엔드포인트인가 — RED 지표로 특정
              ↓
3. 추적    Trace ID로 그 요청의 여정 복원 — 어느 span이 느린가/터지나
              ↓
4. 원인    ELK에서 그 Trace ID·시간대 로그 — 예외 스택, 에러 메시지
              ↓
5. 심층    DB면 Slow Query / JVM이면 Thread·Heap Dump
              ↓
6. 조치    롤백 or 핫픽스 — 그리고 "왜 탐지가 늦었나"를 회고
```

가장 중요한 단계는 6번의 **회고**다. 같은 장애를 두 번 겪는 것은 도구의 실패가 아니라 프로세스의 실패다. 나는 5번의 연속 핫픽스를 겪고 나서야 "단위 테스트가 통과해도 배포 후 통합·설정 계층에서 터지는 결함"이라는 패턴을 발견했고, 그 뒤로 E2E 스모크 테스트와 배포 후 자동 검증을 방어선으로 추가했다.

---

## 7. 한눈 요약 — 증상별 도구

| 증상 | 첫 도구 | 심층 도구 |
|---|---|---|
| 5xx 급증 | Grafana(RED) | ELK(에러 로그 + Trace ID) |
| 특정 요청만 느림 | Distributed Tracing | Slow Query / 외부 API span |
| 전체적으로 느려짐 | Prometheus(포화 지표) | Thread Dump(경합) |
| 메모리 계속 증가 | Grafana(heap 추세) | Heap Dump(MAT) |
| 응답 없음(hang) | Thread Dump | 데드락/락 경합 분석 |
| 로그/디스크 폭증 | ELK(로그 rate) | 로그 레벨·쿼리 결함 |
| 어느 서비스인지 모름 | Trace ID | 서비스별 span 분해 |

관측성은 비용이다. 대시보드·트레이싱·로그 파이프라인을 만드는 데 시간이 든다. 하지만 그 비용은 **새벽 4시에 원인을 5분 만에 찾느냐, 2시간 헤매느냐**로 회수된다. 장애는 반드시 온다. 그때 흩어진 계층을 순서대로 좁혀 들어갈 지도가 있느냐 — 그것이 운영의 실력이다.
