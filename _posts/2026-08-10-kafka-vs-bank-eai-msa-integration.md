---
layout: post
title: "Apache Kafka 기반 MSA와 은행 EAI 솔루션 비교: 이벤트 스트리밍과 거래 연계의 경계"
date: 2026-08-10 16:45:00 +0900
categories: [architecture, kafka, msa, finance]
tags: [Apache Kafka, EAI, MCI, FEP, ESB, banking, Spring Boot, MSA]
---

Apache Kafka로 MSA를 구성하다 보면 은행의 EAI·ESB·MCI·FEP 같은 연계 솔루션과 비교하게 된다. 둘 다 시스템 사이의 메시지와 데이터를 전달하지만, **같은 문제를 같은 방식으로 푸는 제품은 아니다.**

이 글은 Kafka를 금융권 EAI의 단순한 대체재로 보지 않고, 이벤트 스트리밍 backbone과 거래 연계 미들웨어의 책임을 나눠 비교한다.

## 한 줄 결론

```text
Kafka:
  대규모 이벤트를 기록·재생·다중 소비하는 스트리밍 backbone

은행 EAI:
  이기종 시스템 간 거래·변환·라우팅·감사·운영 통제를 제공하는 연계 플랫폼
```

따라서 정답은 “Kafka로 EAI를 전부 교체”가 아니라 다음에 가깝다.

```text
Kafka = 내부 이벤트 스트리밍·비동기 backbone
EAI/ESB = 복잡한 거래 연계·변환·라우팅·운영 통제
MCI = 채널·대외 접점 통합
FEP = 금융기관·외부 전문망 연계
```

실제 금융기관의 특정 제품·구성은 공개자료만으로 확정할 수 없으므로, 아래의 은행 EAI 설명은 공개된 EAI/ESB 패턴과 금융 IT의 일반적인 역할 모델을 기준으로 한다.

## 1. 두 기술이 해결하는 문제의 출발점

### Kafka의 출발점

Kafka는 여러 Producer와 Consumer가 직접 연결되며 복잡해지는 문제를 중앙 로그와 Consumer Group으로 완화한다.

```text
Producer
  ↓
Topic / Partition / Offset
  ↓
Consumer Group A
Consumer Group B
Consumer Group C
```

핵심 가치는 다음이다.

```text
여러 Consumer Group의 독립 소비
Partition 기반 병렬성
메시지 보존과 재생
높은 처리량
이벤트 기반 서비스 분리
```

### 은행 EAI의 출발점

EAI는 서로 다른 애플리케이션·데이터·프로토콜·전문 포맷을 연결한다. IBM은 EAI를 애플리케이션 간 메시지 기반·트랜잭션 지향 통합 패턴으로 설명하며, ESB는 중앙 구성요소가 애플리케이션 통합을 수행하는 아키텍처 패턴으로 설명한다.

은행 환경에서는 다음 문제가 중심이 된다.

```text
코어뱅킹 ↔ 계정계 주변 시스템
채널계 ↔ 업무계
대외기관 ↔ 은행 내부
신·구 시스템 간 전문 변환
동기 거래와 비동기 처리
전문 재처리·추적·감사
```

즉 EAI의 질문은 “이벤트를 얼마나 많이 흘릴까?”만이 아니다.

```text
어떤 전문을
어떤 경로로
어떤 형식으로 변환해
어떤 거래 규칙과 감사 흔적을 남기며
재처리할 것인가?
```

## 2. 개념·역할 비교

| 구분 | Apache Kafka | 은행 EAI/ESB | 금융권에서의 의미 |
| --- | --- | --- | --- |
| 기본 모델 | 분산 이벤트 로그·스트림 | 중앙 연계·브로커·거래 통합 | 이벤트 backbone vs 연계 허브 |
| 메시지 단위 | Record·event | 전문·메시지·거래 요청/응답 | 도메인 이벤트 vs 업무 전문 |
| 소비 방식 | Consumer Group·offset | 라우팅·채널·어댑터·거래 플로우 | 독립 소비 vs 명시적 연계 경로 |
| 순서 | Partition 내부 | 거래 플로우·전문 규칙·시스템 계약 | key 순서 vs 거래 순서 |
| 변환 | Serializer·Streams·Connect 등 | 매핑·전문 변환·어댑터 | schema 변환 성숙도와 범위 차이 |
| 재처리 | offset reset·재생·새 group | 거래 추적·재전송·보상·운영 콘솔 | 기술 재생 vs 업무 재처리 |
| 트랜잭션 | Kafka 내부 transaction 지원 | 외부 거래·전문·원장 중심 통제 | Kafka exactly-once ≠ 금융 거래 exactly-once |
| 관찰 | lag·ISR·broker metrics | 전문 추적·거래 ID·운영 화면·감사 | 운영 지표의 관점이 다름 |
| 강점 | 처리량·확장·다중 소비 | 이기종 통합·변환·라우팅·거래 운영 | 서로 대체보다 상호 보완 |
| 주요 비용 | broker·partition·replica·lag 운영 | 라이선스·벤더 종속·전문 개발·허브 복잡도 | 운영 조직의 역량과 계약 비용 |

## 3. 금융 거래에서 가장 중요한 차이: 이벤트와 전문

Kafka의 메시지는 보통 발생한 사실을 표현한다.

```text
payment_captured
settlement_requested
payout_completed
```

은행 EAI의 전문은 다음과 같은 거래 요청·응답일 수 있다.

```text
계좌이체 요청 전문
잔액 조회 요청/응답
대외기관 승인 전문
전문 오류·응답코드
```

이 둘은 연결될 수 있지만 동일하지 않다.

```text
도메인 이벤트:
  이미 일어난 사실

거래 전문:
  특정 시스템에 처리·응답을 요청하는 계약
```

Kafka Topic에 거래 전문을 그대로 넣는다고 금융 거래의 정합성·감사·재처리가 자동으로 확보되는 것은 아니다. 전문의 원문, 거래 ID, 요청·응답 시각, 응답 코드, 재처리 상태, 보상 거래를 별도로 설계해야 한다.

## 4. Kafka 기반 MSA의 강점

### 4.1 여러 서비스가 같은 이벤트를 독립 소비

예를 들어 결제 완료 이벤트를 다음 서비스가 각각 읽을 수 있다.

```text
settlement-service
risk-service
notification-service
analytics-service
audit-service
```

Consumer Group이 다르면 각자의 offset과 처리 속도를 갖는다. 이것은 단일 목적의 point-to-point 연계보다 MSA 확장에 유리하다.

### 4.2 이벤트 재생

새로운 Consumer Group이 과거 이벤트를 읽어 projection이나 분석 모델을 다시 만들 수 있다. 단, 보존 기간과 개인정보·금융 데이터 보존 정책을 함께 결정해야 한다.

### 4.3 처리량과 수평 확장

Partition을 늘리고 Consumer를 분산해 처리량을 확대할 수 있다. 그러나 순서는 Partition 안에서만 보장되므로 Aggregate key를 먼저 설계해야 한다.

```text
order_id를 key로 사용
→ 같은 주문 이벤트를 같은 Partition에 배치
→ 주문 단위 순서 유지
```

전체 거래의 전역 순서를 보장하려고 Partition 하나를 선택하면 Kafka의 병렬성 장점을 잃는다.

## 5. 은행 EAI의 강점

### 5.1 이기종 시스템과 레거시 연결

은행에는 REST/JSON만 있는 것이 아니다.

```text
HTTP·REST
SOAP
JMS/MQ
TCP 전문
파일·배치
Mainframe 연계
고정 길이 전문
암호화·전자서명 전문
```

EAI는 이런 프로토콜과 데이터 형식 사이에서 어댑터·변환·라우팅을 제공하는 데 강점을 가진다.

### 5.2 거래 단위 추적

금융 운영에서는 “메시지가 Kafka에 들어갔다”보다 다음 질문이 중요할 수 있다.

```text
이체 요청은 어디까지 처리됐는가?
대외기관 응답은 무엇이었는가?
재전송했는가?
중복 거래는 막았는가?
누가 언제 어떤 전문을 재처리했는가?
```

EAI 운영 플랫폼은 전문 ID·거래 ID·응답코드·재처리 이력·운영 화면을 중심으로 설계되는 경우가 많다.

### 5.3 동기 요청/응답과 대외 연계

고객 요청이 즉시 응답을 요구하는 경우 Kafka 비동기 이벤트만으로 UX와 거래 계약을 설명하기 어렵다.

```text
채널 요청
→ MCI/FEP/EAI 라우팅
→ 코어·대외기관 처리
→ 응답 매핑
→ 채널 반환
```

이런 동기 흐름과 타임아웃·재시도·전문 오류코드·회로차단은 별도 연계 플랫폼의 역할이 될 수 있다.

## 6. MCI·FEP·EAI의 역할을 Kafka와 함께 보기

### MCI

MCI는 채널 통합 관점에서 설명되는 경우가 많다.

```text
모바일
인터넷뱅킹
ATM
상담·창구
제휴 채널
```

각 채널의 요청을 내부 공통 서비스 계약으로 변환하고 채널별 차이를 흡수한다. Kafka는 MCI를 자동으로 대체하지 않는다. Kafka를 MCI 뒤의 비동기 이벤트 backbone으로 사용할 수는 있다.

### FEP

FEP는 외부 금융기관·결제망·카드사·공공기관 등과의 전문 연계 관점이 강하다.

```text
외부 전문망
보안·암호화
전문 송수신
응답코드
재전송·대사
```

외부 전문의 동기 응답과 보안·감사 계약은 Kafka Topic만으로 해결되지 않는다. FEP/EAI와 Kafka 사이에는 명확한 경계와 중계 adapter가 필요하다.

### EAI/ESB

EAI/ESB는 내부 시스템 사이의 라우팅·변환·통합 흐름을 담당한다. Kafka는 이 흐름 중 이벤트 스트리밍이 적합한 부분을 맡을 수 있지만, 모든 거래 흐름을 Kafka Topic으로 바꾸는 것은 다른 종류의 중앙 복잡성을 만들 수 있다.

## 7. Kafka를 EAI의 대체재로 사용할 때 생기는 문제

### 7.1 동기 거래를 억지로 비동기로 만들기

잔액 조회·이체 승인·대외기관 응답처럼 즉시 결과가 필요한 업무를 Kafka request/reply로만 처리하면 timeout·상관관계·재시도·중복 응답이 복잡해진다.

### 7.2 전문 변환을 Consumer마다 중복 구현

EAI가 중앙에서 전문 변환을 담당하던 것을 Kafka Consumer 각각에 흩어 놓으면:

```text
변환 로직 중복
버전 불일치
오류 코드 해석 차이
감사 추적 분산
```

이 생길 수 있다.

### 7.3 Kafka exactly-once를 금융 exactly-once로 오해

Kafka 내부 transaction은 Kafka Streams와 transactional producer/consumer 경로에서 의미가 있다. 외부 원장·대외기관·DB까지 자동으로 원자성을 보장하지 않는다.

금융 거래에는 다음이 여전히 필요하다.

```text
idempotency key
business unique constraint
ledger invariant
outbox/inbox
reconciliation
compensation
audit trail
```

### 7.4 운영 책임의 이동

EAI가 사라지는 것이 아니라 다음 운영 책임이 MSA 팀으로 이동할 수 있다.

```text
Topic·Partition 설계
Schema Registry
Consumer lag
DLQ·retry
재처리 통제
PII 보호
ACL·TLS
Broker·disk·replica
```

벤더 솔루션 비용을 줄이는 대신 플랫폼 운영 비용과 조직 역량이 필요하다.

## 8. 현실적인 하이브리드 아키텍처

은행형 MSA라면 다음처럼 역할을 나누는 편이 현실적이다.

```text
[채널]
  ↓
MCI / API Gateway
  ↓
[동기 거래 API]
  ↓
Core Banking / FEP / EAI
  │
  └─ 거래 결과·업무 이벤트
          ↓
      Kafka Backbone
       ├─ 정산
       ├─ 알림
       ├─ 위험 탐지
       ├─ 분석
       └─ 감사 projection
```

### 동기 경로

```text
인증
잔액 조회
이체 승인
결제 승인
대외기관 즉시 응답
```

### 비동기 경로

```text
거래 완료 이벤트
정산 요청
알림
분석·리포팅
검색 projection
감사 이벤트
```

### 핵심 경계

```text
EAI/FEP:
  거래 요청·응답·전문 변환·대외 연계

Kafka:
  거래 결과의 이벤트 확산·재생·다중 소비
```

이 구조는 기존 계정계와 레거시를 보존하면서 MSA의 독립 소비와 점진적 현대화를 가능하게 한다.

## 9. 데이터 계약과 정합성 설계

Kafka와 EAI를 함께 쓸 때는 메시지 envelope와 거래 추적 ID를 공통으로 둬야 한다.

```json
{
  "eventId": "uuid",
  "eventType": "payment_captured",
  "schemaVersion": 1,
  "aggregateType": "payment",
  "aggregateId": "payment-123",
  "traceId": "trace-456",
  "occurredAt": "2026-08-10T07:00:00Z",
  "source": "payment-service",
  "payload": {}
}
```

전문 연계에는 추가로 다음이 필요할 수 있다.

```text
transactionId
messageId
correlationId
request/response type
external institution code
response code
retry count
reconciliation status
```

이벤트 계약은 Schema Registry·호환성 정책과 함께 관리해야 한다. EAI 전문과 Kafka 이벤트를 변환할 때는 단순 필드 매핑이 아니라 **업무 의미·상태 전이·재처리 의미**까지 매핑해야 한다.

## 10. 비교 판단 프레임워크

| 질문 | Kafka 우선 | EAI/ESB 우선 |
| --- | --- | --- |
| 여러 서비스가 같은 사건을 읽는가? | 적합 | 가능하지만 과할 수 있음 |
| 과거 이벤트 재생이 필요한가? | 강점 | 구현 방식에 따라 다름 |
| 즉시 요청/응답인가? | 신중 | 적합 |
| 레거시·전문·이기종 프로토콜인가? | Adapter 필요 | 강점 |
| 높은 이벤트 처리량인가? | 강점 | 제품·구성 의존 |
| 대외기관 거래 추적·재전송인가? | 별도 구현 필요 | 강점 |
| 기존 금융 운영 콘솔·감사 계약이 있는가? | 통합 필요 | 기존 체계 활용 |
| 플랫폼 팀이 Broker 운영 가능한가? | 전제 조건 | 벤더 운영 모델 검토 |
| 비동기 확산·분석·정산인가? | 적합 | 보조 가능 |

## 11. 도입 전 체크리스트

### 비즈니스

```text
이것은 사실 이벤트인가, 처리 요청인가?
즉시 응답이 필요한가?
실패하면 보상·대사가 필요한가?
거래 중복이 금전 손실로 이어지는가?
```

### Kafka

```text
Partition key는 무엇인가?
순서 범위는 어디까지인가?
replication·acks·min.insync.replicas는?
lag·ISR·rebalance를 어떻게 모니터링하는가?
재처리 권한은 누구에게 있는가?
```

### EAI/FEP

```text
전문 변환 책임자는 누구인가?
응답코드와 오류 의미는 어디에 정의하는가?
대외기관 timeout·재전송 정책은?
거래 trace와 감사 이력은?
신·구 시스템 coexistence 기간은?
```

### 공통

```text
event/message schema version
idempotency key
correlation/trace ID
PII·금융정보 보호
DLQ·retry·보상
reconciliation
운영자 승인·감사
```

## 결론

Apache Kafka와 은행 EAI는 경쟁 제품으로 단순 비교하기 어렵다.

```text
Kafka:
  이벤트가 일어난 뒤 여러 시스템에 확산하고 재생하는 데 강함

EAI/ESB:
  이기종 시스템 사이의 거래·전문·변환·라우팅을 통제하는 데 강함

MCI:
  채널 접점을 통합

FEP:
  외부 금융기관·전문망을 연결
```

은행의 MSA 현대화에서는 다음 하이브리드가 현실적인 출발점이다.

```text
동기 거래·대외 전문:
  MCI / FEP / EAI / Core

거래 결과·비동기 확산:
  Kafka

정합성·감사:
  원장·Outbox·Inbox·대사·불변 audit
```

Kafka를 도입했다고 금융권 EAI의 역할이 사라지는 것은 아니다. 반대로 EAI를 유지한다고 Kafka 기반 MSA가 불가능한 것도 아니다.

> 좋은 금융 MSA는 기술 이름을 통일하는 것이 아니라, 거래의 경계·이벤트의 경계·책임의 경계를 분명히 한다.

## References

- [IBM — What Is an Enterprise Service Bus?](https://www.ibm.com/think/topics/esb)
- [IBM Redbooks — Integration Throughout and Beyond the Enterprise](https://www.redbooks.ibm.com/redbooks/pdfs/sg248188.pdf)
- [IBM Redbooks — Connecting Enterprise Applications](https://www.redbooks.ibm.com/redbooks/pdfs/sg247406.pdf)
- [Apache Kafka Documentation](https://kafka.apache.org/documentation/)
- [Apache Kafka Design](https://kafka.apache.org/documentation/#design)
- [Confluent — Message Delivery Guarantees](https://docs.confluent.io/kafka/design/delivery-semantics.html)
- [Debezium Documentation](https://debezium.io/documentation/)
- [Greg Lee’s Lab — Apache Kafka core concepts](https://medium.com/greglee-lab/the-8-core-concepts-that-make-up-apache-kafka-adfe5c57fc0f)
- [Greg Lee’s Lab — Kafka adoption checklist](https://medium.com/greglee-lab/apache-kafka-isnt-a-silver-bullet-4-things-to-check-before-you-ship-28128627a32f)

*금융기관의 특정 EAI·MCI·FEP 제품과 내부 구성은 공개자료만으로 확정하지 않았다. 이 글의 은행 EAI 비교는 공개 EAI/ESB 문서와 금융 연계의 일반적인 역할 모델을 기반으로 한다.*

*공개 글에는 credential, token, private IP, 내부 endpoint를 포함하지 않았다.*

## Related posts

- [Apache Kafka 정리: 핵심 개념부터 운영 전 체크리스트까지](https://myoungsoo7.github.io/2026/08/10/apache-kafka-core-concepts-and-production-checklist/)
- [Java/Spring 확장성: 변하는 축·추상화·이름](https://myoungsoo7.github.io/2026/08/10/scalability-abstraction-interview/)
- [Settlement Order·Payment·Settlement 흐름](https://myoungsoo7.github.io/2026/08/09/settlement-order-payment-flow/)
- [은행 EAI·MCI·FEP·JEX·Spring 현대화 비교](https://myoungsoo7.github.io/2026/08/09/bank-eai-mci-fep-jex-spring-architecture/)
