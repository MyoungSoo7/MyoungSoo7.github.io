---
layout: post
title: "은행 EAI·MCI·FEP의 역할과 현대화: 4대 은행 공개자료의 한계, JEX와 Spring의 설계 비교"
date: 2026-08-09 01:10:00 +0900
categories: [Architecture, Finance, Java]
tags: [Banking, EAI, MCI, FEP, JEX, Spring, Legacy Modernization, 금융IT]
---

# 은행 EAI·MCI·FEP의 역할과 현대화

## 먼저 밝혀둘 범위

은행의 연계 아키텍처는 보안·경쟁·운영 이유로 전체 구성이 공개되지 않는다. 특히 KB국민은행·하나은행·우리은행·신한은행의 현재 내부 EAI·MCI·FEP 제품명, 버전, 배치 토폴로지, 계정계 연결 구성은 공식 자료만으로 완전히 확인하기 어렵다.

따라서 이 글은 다음을 구분해 작성한다.

```text
공개 근거
= 공식 제품 자료·공개 구축 사례·기술 문서

업계 일반 모델
= EAI·MCI·FEP의 일반적인 역할 분담

설계 제안
= 공개 구조를 바탕으로 한 현대화 방향

미확인
= 특정 은행의 현재 내부 제품·버전·실제 토폴로지
```

특정 은행이 특정 솔루션을 현재 사용한다고 공개 근거 없이 단정하지 않는다.

## 결론부터

EAI·MCI·FEP는 낡아서 한꺼번에 제거해야 할 부품이 아니라, **채널·내부 업무·대외기관 사이의 서로 다른 신뢰경계와 통신특성을 분리해 온 금융 연계 계층**이다. 현대화의 목표는 이름을 Kafka·API Gateway·MSA로 바꾸는 것이 아니라, 전문·라우팅·재처리·보안·관측성·대사를 더 명확한 계약으로 재구성하는 것이다.

```text
MCI
= 고객·내부 사용자 채널을 표준 업무 요청으로 정규화

EAI/ESB
= 기업 내부 애플리케이션과 업무 시스템 사이의 변환·라우팅·통합

FEP
= 외부 기관·전문·전용망·고속 거래의 접점과 안정성 관리

현대화
= 역할 제거가 아니라 계약·보안·관측성·배포 단위의 재설계
```

## 1. 은행의 큰 시스템 경계

전형적인 은행 업무 구조를 단순화하면 다음과 같다.

```text
고객 채널
  모바일·인터넷뱅킹·ATM·창구·콜센터·기업채널
          ↓
채널계 / MCI
          ↓
업무계
  수신·여신·외환·카드·자산관리·고객·인증
          ↓
계정계
  원장·잔액·거래·마감·정산
          ↓
정보계
  DW·리포팅·분석·위험·규제보고

외부 기관 경로:
업무/계정계 ↔ FEP ↔ 금융결제원·카드사·증권사·공공기관·해외망

내부 통합 경로:
업무 시스템 ↔ EAI/ESB ↔ 다른 내부 시스템
```

이 구조는 논리 모델이다. 실제 은행마다 채널 통합, 계정계·정보계 분리, 대외계, API Gateway, 이벤트 플랫폼, 클라우드 전환 방식이 다를 수 있다.

## 2. MCI: 채널을 업무 요청으로 통합하는 계층

MCI는 Multi Channel Integration 또는 Multi Channel Architecture로 불리며, 실무에서는 MCA와 혼용되기도 한다.

```text
모바일 전문
인터넷 전문
ATM 전문
창구 전문
콜센터 전문
기업뱅킹 전문
        ↓
MCI
        ↓
공통 업무 요청
```

### MCI가 해결하는 문제

채널마다 다음이 달라진다.

- 입력 필드와 전문 형식
- 인증 방식
- 세션·device 정보
- 오류 코드
- timeout과 재시도
- 동기·비동기 응답
- 화면별 aggregation

MCI는 채널별 차이를 업무 시스템에 그대로 전달하지 않고 공통 계약으로 정규화한다.

```text
channel request
→ authentication/context enrichment
→ validation
→ canonical request
→ route to business service
→ channel-specific response
```

### MCI가 하면 안 되는 일

MCI가 업무 규칙과 계정 원장까지 떠안으면 채널 통합 계층이 거대한 업무 허브가 된다.

```text
MCI에 두기 좋은 것:
  전문 변환·채널 인증 context·routing·aggregation·rate limit

MCI에 두면 위험한 것:
  잔액 원장 변경·이자 계산·대출 승인 판단·회계 분개
```

현대화 때 MCI를 API Gateway로 단순 치환하는 것도 충분하지 않다. API Gateway는 north-south 진입·인증·정책에 강하지만, 채널 전문 변환·업무 aggregation·레거시 adapter·금융 오류코드 호환까지 자동으로 해결하지 않는다.

## 3. EAI/ESB: 내부 애플리케이션 통합 계층

EAI는 Enterprise Application Integration이다. 내부 업무 시스템 사이의 메시지 전달, 데이터 변환, 라우팅, workflow 연계가 중심이다.

```text
고객관리
  ↕
EAI/ESB
  ↕
수신·여신·카드·회계·정보계
```

### EAI의 전형적 기능

```text
protocol adapter
message transformation
routing
orchestration
queueing
retry
transaction boundary
monitoring
```

예를 들어 계좌 개설이 다음 시스템을 건드린다고 하자.

```text
고객 원장 생성
→ KYC 결과 저장
→ 계좌번호 발급
→ 상품 가입 기록
→ 알림 발송
→ 정보계 적재
```

EAI가 모든 업무 규칙을 대신 갖는 것이 아니라, 각 시스템의 계약을 연결하고 성공·실패·재처리 흐름을 관리하는 구조가 바람직하다.

### EAI의 현대화 포인트

기존 EAI는 중앙 허브로 성장하면서 다음 문제가 생길 수 있다.

- 라우팅과 변환 규칙이 한 곳에 집중
- 중앙 장애가 전체 업무로 전파
- 배포 단위가 커짐
- 운영자가 화면에서만 흐름을 이해
- 메시지 스키마와 코드가 분리
- 재처리·중복 처리 정책이 인터페이스마다 다름

따라서 현대화에서는 다음을 분리한다.

```text
동기 API
  API Gateway + service contract

비동기 업무 이벤트
  Kafka/event platform + schema registry

파일·배치
  managed transfer + batch control + checksum

레거시 전문
  adapter/anti-corruption layer
```

EAI를 없애는 것이 아니라 중앙 변환을 도메인별 adapter와 명시적 이벤트 계약으로 분해한다.

## 4. FEP: 대외계와 전문 처리의 안정성 경계

FEP(Front End Processor)는 금융기관 외부 시스템과의 전용 접점으로 이해할 수 있다.

```text
은행 내부
  ↕
FEP
  ↕
외부 기관·금융결제망·카드·증권·공공기관
```

FEP에서 중요하게 보는 것은 일반적인 REST API 편의성보다 다음이다.

- 전문 format과 field length
- 고정 길이·전문 header
- 기관별 protocol
- TCP/전용망/보안 채널
- correlation ID
- 거래 timeout
- 전문 응답과 원거래 매칭
- 재전송·중복 방지
- 거래일·영업일·마감
- 장애 시 보류·대사·수동 처리

### FEP의 핵심은 “빠른 호출”이 아니다

외부기관 요청이 timeout됐을 때 가장 위험한 질문은 “다시 보내도 되는가?”다.

```text
요청 timeout
→ 외부기관 처리 여부 불명
→ 무조건 retry 금지
→ inquiry/status 조회
→ 원거래 ID로 대사
→ 승인된 보정 또는 재전송
```

FEP는 요청을 전달하는 네트워크 계층이면서 금융 거래의 결과를 추적하는 operational control plane이어야 한다.

## 5. EAI·MCI·FEP 비교

| 계층 | 주 대상 | 핵심 책임 | 대표 실패 | 현대 대응 |
|---|---|---|---|---|
| MCI | 고객·내부 채널 | 채널 정규화·인증 context·aggregation | 채널별 계약 불일치 | API Gateway·BFF·channel adapter |
| EAI/ESB | 내부 업무 시스템 | 변환·라우팅·통합 | 중앙 허브 장애·변환 규칙 폭발 | event platform·domain adapter |
| FEP | 외부 기관·금융망 | 전문·전용망·재전송·대사 | timeout 후 처리 여부 불명 | external integration gateway |

세 계층은 모두 “연결”을 하지만 연결의 경계가 다르다.

```text
MCI: 채널 경계
EAI: 기업 내부 애플리케이션 경계
FEP: 조직 외부·금융망 경계
```

## 6. 4대 은행의 솔루션을 어떻게 봐야 하는가

### 공개정보의 한계

KB국민은행·하나은행·우리은행·신한은행은 대규모 차세대·디지털·클라우드·오픈뱅킹·API·대외계 프로젝트를 지속해 왔지만, 현재 내부 EAI/MCI/FEP 제품명과 버전 전체를 공식 기술문서로 공개하지는 않는다.

따라서 다음 표현은 피해야 한다.

```text
“국민은행은 반드시 제품 X를 쓴다”
“4대 은행 모두 제품 Y로 통일됐다”
“신한은행의 현재 FEP 토폴로지는 Z다”
```

공개 구축 사례에서 확인되는 사실과 업계 일반 추론은 구분해야 한다.

### 공개적으로 확인 가능한 제품군 사례

국내 금융 IT 시장에는 다음과 같은 범주의 솔루션과 사업자가 공개되어 있다.

```text
상용 ESB/EAI/MCI/FEP 제품
인터페이스 관리(EIMS) 제품
API Management 제품
메시징·Kafka 플랫폼
전문 변환·대외 연계 adapter
```

예를 들어 INZENT는 EIMS를 전사 인터페이스 관리 시스템으로 소개하며 MCI·EAI·FEP 인터페이스의 통합 관리, 인터페이스 등록·배포·변경·배포 이력·거래통계와 온라인/배치·동기/비동기/bypass 유형을 제시한다. 제품 페이지의 구축 사례에 신한은행이 언급되지만, 이것만으로 신한은행 전체의 현재 EAI/MCI/FEP 제품 구성을 확정할 수는 없다.

전자신문의 2014년 기사도 금융권에서 EAI·MCI·FEP 기능을 통합 솔루션으로 대체하려는 흐름과 SC제일은행의 FEP 미들웨어 교체 사례를 소개한다. 이는 시장의 방향을 보여주는 공개 자료이지 2026년 4대 은행 내부 구성의 증거는 아니다.

### 4대 은행별 분석 프레임

공개 사실이 부족한 상황에서 은행별로는 “제품명 맞히기”보다 다음 관점이 유효하다.

| 은행 | 공개자료로 안전하게 말할 수 있는 범위 | 추가 확인이 필요한 것 |
|---|---|---|
| KB국민은행 | 대규모 채널·업무·대외 연계 현대화 대상 | 현재 MCI/FEP/EAI 제품·버전·운영 topology |
| 하나은행 | 디지털 채널·글로벌·내부 업무 연계가 중요한 대형 금융 플랫폼 | 국내/글로벌 연계 허브와 제품별 ownership |
| 우리은행 | 레거시·차세대·채널 통합을 함께 고려해야 하는 대형 금융 환경 | 대내 EAI·채널 통합·대외 FEP의 현재 분리/통합 상태 |
| 신한은행 | 공개 솔루션 구축 사례가 있으나 전체 현재 구성과 동일시 불가 | EIMS 사례와 실제 운영 제품·범위·버전의 관계 |

이 표의 목적은 모르는 것을 모른다고 표시하는 것이다. 금융권 포트폴리오에서 “어느 은행이 무슨 제품을 쓴다”보다 중요한 것은 **연계 문제를 어떤 책임 경계와 증거로 설계하는가**다.

## 7. 현대 아키텍처로 보완하는 방법

### 7.1 중앙 허브를 분해하되 계약은 중앙 관리

```text
기존:
모든 변환·라우팅·재처리가 중앙 EAI에 집중

현대:
도메인 adapter + event bus + schema registry
```

중앙에 남겨야 하는 것:

- 인터페이스 catalog
- schema/version
- security policy
- observability 표준
- routing ownership
- replay 권한
- 대사 기준

도메인으로 내려야 하는 것:

- 상품별 변환
- 업무별 상태 전이
- 외부 기관별 adapter
- retryable/non-retryable 판단
- domain event 생성

### 7.2 동기와 비동기를 분리

모든 연계를 Kafka로 바꾸거나 모든 연계를 REST로 바꾸는 것은 위험하다.

```text
즉시 응답이 필요한 조회·승인
  sync API

결과가 늦어도 되는 전파·분석·알림
  async event

기관 전문·파일·마감
  FEP/batch protocol
```

고객에게 즉시 결과를 보여줘야 하는 거래와, 후속 정보계 적재를 같은 timeout으로 처리하면 안 된다.

### 7.3 Outbox·Inbox·DLT·대사를 표준화

금융 거래에서 필요한 기본 계약은 다음이다.

```text
producer local transaction
  + outbox event

consumer
  + inbox/processed event
  + idempotency key

failure
  + retry policy
  + DLT/quarantine

recovery
  + replay
  + reconciliation
```

성공 응답만 표준화하면 부족하다. 실패·중복·timeout·부분 성공·수동 보정도 표준화해야 한다.

### 7.4 전문을 JSON으로 무조건 변환하지 않는다

고정 길이 전문은 비효율적으로 보일 수 있지만, 외부기관 계약과 운영 현실이 있다.

```text
외부 전문
  → strict parser/validator
  → canonical domain message
  → 내부 API/event
```

전문 원문·파싱 결과·canonical message를 모두 추적 가능하게 보존해야 장애 조사와 대사가 가능하다.

### 7.5 인터페이스를 코드와 metadata로 함께 관리

EIMS 형태의 인터페이스 catalog에 다음을 포함한다.

```yaml
interface_id: payment.capture.v2
owner: payment-platform
source: channel-mci
sink: core-payment
transport: sync-api
schema_version: 2
idempotency_key: payment_id
timeout_ms: 3000
retry: inquiry-before-retry
security_class: financial-sensitive
reconciliation_key: external_transaction_id
rollback: compensate-or-manual-review
```

문서만 존재하면 drift가 생긴다. schema registry·contract test·CI 검증과 연결해야 한다.

## 8. JEX Framework는 무엇인가

JEX는 공개된 일반 Spring 제품이 아니라 국내 금융·SI 현장에서 사용된 웹캐시 계열의 금융 업무 프레임워크로 소개되어 왔다. 공개 자료는 제한적이고, 조직·버전·프로젝트별 확장이 다를 수 있으므로 특정 JEX 구현 전체를 일반화하면 안 된다.

공개된 자료에서 설명되는 JEX 개념에는 다음이 있다.

```text
Jex Studio
  웹 기반 입출력·전문 정의 도구

JexData
  전문 데이터를 다루는 추상화

WSVC
  웹과 JSP 사이 웹서비스 전문

BCS
  JSP와 Java business component 사이 전문

IDO
  데이터베이스 접근 전문

IMO
  외부 AP 연계 전문

CMO
  공통 header 전문
```

전형적인 설명 흐름은 다음과 같다.

```text
Web 전문
  → JSP/action
  → BCS
  → Java business
  → IDO(DB) 또는 IMO(외부 AP)
```

이 구조는 일반적인 현대 Spring MVC의 REST/DTO/Repository 흐름과 이름은 다르지만, 금융 업무 개발에서 공통으로 필요한 것을 제공한다.

```text
입출력 계약
입력값 검증
공통 전문 header
업무 component 분리
DB 접근 추상화
외부기관 adapter
```

## 9. JEX가 Spring에서 차용하거나 공유하는 설계 원리

JEX가 Spring 코드를 그대로 사용한다고 단정할 공개 근거는 없다. 여기서 말하는 “차용”은 구현 코드 재사용이 아니라 **기업용 프레임워크가 Spring과 공유하는 설계 원리**라는 의미로 제한한다.

### 9.1 프레임워크가 흐름을 제어한다

Spring은 IoC/DI로 애플리케이션 객체 생성과 연결을 프레임워크가 관리한다.

JEX 계열 업무 프레임워크도 개발자가 모든 통신·전문·호출 순서를 바닥부터 작성하지 않고, 정의된 lifecycle과 metadata에 업무 코드를 끼워 넣는 방식으로 생산성을 높인다.

```text
직접 제어:
개발자가 socket·mapping·lifecycle을 모두 작성

Framework control:
프레임워크가 lifecycle·mapping·공통처리를 제공
개발자는 업무 규칙에 집중
```

### 9.2 계약 우선

Spring의 Controller DTO, validation, service interface, repository abstraction처럼 JEX도 전문 정의와 `JexData`를 중심으로 입력·출력 계약을 관리한다.

```text
HTTP JSON DTO
≈
JexData/전문 모델
```

다만 JexData가 JSON과 같다고 단순화하면 안 된다. 금융 전문은 반복부·고정 필드·공통 header·전문 코드·legacy mapping을 포함할 수 있다.

### 9.3 관심사 분리

Spring에서 Controller·Service·Repository·Adapter를 분리하는 것처럼 JEX의 action·business component·DB/AP interface 구분도 관심사 분리의 한 형태로 볼 수 있다.

```text
채널/action
  입력 검증·화면 흐름

business component
  업무 처리

IDO
  DB 접근

IMO
  외부 AP 연계
```

이것은 Hexagonal Architecture와도 연결할 수 있다. 단, 실제 코드가 완전히 hexagonal하다고 주장하려면 프로젝트별 소스 검증이 필요하다.

### 9.4 공통 인프라 집중

Spring Boot가 logging·configuration·transaction·security·web runtime을 공통화하듯, 금융 업무 프레임워크는 다음을 표준화하려고 한다.

- 공통 전문 header
- 오류코드
- transaction context
- 세션·인증
- DB/API connector
- 배포 단위
- 개발 도구
- 운영 모니터링

은행권에서 프레임워크의 핵심 가치는 “최신 언어 기능”보다 **많은 개발자가 같은 거래 규칙과 운영 conventions를 따르게 만드는 것**이다.

## 10. JEX와 Spring의 차이

| 구분 | JEX 계열 업무 프레임워크 | Spring/Spring Boot |
|---|---|---|
| 중심 추상화 | 금융 전문·업무 component·IDO/IMO | Bean·HTTP·Service·Repository·Message |
| 입력 모델 | 정의 파일·전문·JexData | DTO·JSON/XML·schema |
| 강점 | 금융 SI 표준화·전문 생산성·레거시 연계 | 범용성·생태계·테스트·클라우드·확장 |
| 런타임 관점 | 프레임워크 규약과 도구 중심 | IoC·auto-configuration·starter 중심 |
| 외부 연계 | IMO/전문 adapter | HTTP client·messaging·custom adapter |
| DB 연계 | IDO 등 정의 기반 접근 | JDBC·JPA·MyBatis·R2DBC |
| 운영 표준 | 조직·벤더·프로젝트 규약에 강하게 종속 | 애플리케이션과 인프라 선택 폭이 넓음 |
| 현대화 방향 | 전문·도구·레거시 adapter 보존 후 분리 | API/event/domain·cloud native로 확장 |

JEX를 Spring의 하위호환이나 구식 기술로만 평가하면 실제 금융 프로젝트의 생산성·전문·운영 규약을 놓친다. 반대로 Spring으로 교체하면 모든 문제가 사라진다고 보는 것도 위험하다.

## 11. Spring을 현대화에 어떻게 활용할 것인가

Spring/Spring Boot는 다음 계층에 적합하다.

```text
Spring Web / WebFlux
  채널 API·내부 API·BFF

Spring Security
  인증·인가·서비스 간 보안

Spring Integration / Apache Camel
  adapter·protocol·routing 필요 시

Spring Kafka
  event producer/consumer·DLT·retry

Spring Batch
  영업일·마감·대사·대량 배치

Spring Transactions
  로컬 DB transaction 경계

Actuator/Micrometer
  health·metrics·trace 연결
```

다만 Spring이 다음을 자동으로 해결하지는 않는다.

```text
PG/금융망 중복 거래
전문 계약 호환성
외부 timeout의 실제 처리 여부
원장 불변성
정산 대사
영업일 규칙
규제 감사
```

프레임워크는 도구이고, 금융 정확성은 도메인 불변식·이벤트 계약·대사·운영 절차의 문제다.

## 12. JEX에서 보존할 것과 Spring으로 개선할 것

### 보존할 것

```text
전문 metadata와 표준 header
공통 오류코드·거래 ID
금융기관별 adapter 경계
업무 component의 책임 분리
개발·배포·승인 표준
운영 추적과 대사 기준
```

### 개선할 것

```text
정의 파일과 실제 코드의 drift
중앙 허브에 집중된 routing
수동 전문 변경
세션에 종속된 상태
불명확한 retry
거래별 idempotency 부재
재처리·DLT·대사 표준 불일치
```

### Spring으로 옮길 때의 안전한 경로

```text
1. 기존 전문·오류·거래 ID catalog 생성
2. anti-corruption adapter 작성
3. canonical request/response 정의
4. contract test로 구·신 시스템 비교
5. shadow/read-only dual run
6. 업무 단위별 strangler 전환
7. 대사 결과가 일치할 때 traffic 전환
8. rollback 경로 유지
```

레거시를 먼저 삭제하지 않고, 구 시스템과 신 시스템의 결과를 비교하면서 전환해야 한다.

## 13. 현대 금융 연계 아키텍처 제안

```text
채널
  모바일·웹·ATM·창구
        ↓
API Gateway / MCI adapter / BFF
        ↓
Domain API·Command Gateway
        ↓
업무 서비스
  deposit·loan·card·payment·account
        ↓
Transactional Outbox
        ↓
Event Platform / Schema Registry
        ↓
정보계·대사·알림·분석

외부기관:
Domain service
  → External Integration Gateway
  → FEP adapter
  → 기관 전문/HTTPS/전용망
```

EAI가 담당하던 내부 변환을 무조건 event로 바꾸지 않고, 다음 기준을 사용한다.

```text
업무 결과를 즉시 알아야 함
  sync command/query

다른 시스템에 사실을 전파
  domain event

외부기관 전문·timeout·대사
  FEP adapter

대량 집계·영업일 처리
  batch + checkpoint
```

각 흐름에는 다음을 함께 둔다.

```text
trace_id
message_id
idempotency_key
schema_version
occurred_at
business_date
retry_count
reconciliation_key
```

## 14. 보안과 운영 보완

현대화된 EAI/MCI/FEP의 품질은 기능보다 실패 처리에서 드러난다.

### 보안

- 채널별 인증 강도와 step-up 인증
- 외부기관 mutual TLS·전용망
- 전문 원문 암호화·마스킹
- API와 event의 권한 분리
- Secret vault와 key rotation
- 운영자 maker-checker
- 데이터 분류와 최소 노출

### 관측성

```text
고객 요청
→ MCI request id
→ 내부 command id
→ FEP transaction id
→ 외부 기관 response id
→ 원장 posting id
→ reconciliation run id
```

이 연결이 있어야 “고객은 이체가 됐다고 하는데 계정에는 반영되지 않았다”는 사건을 조사할 수 있다.

### 대사

```text
내부 거래
vs 외부기관 명세
vs 계정계 원장
vs 정보계 집계
```

단일 로그보다 다중 원천의 대사 결과가 금융 시스템의 사실에 가깝다.

## 15. 최종 판단

| 질문 | 판단 |
|---|---|
| EAI·MCI·FEP는 폐기 대상인가? | 아님. 책임 경계를 현대 계약으로 재설계할 대상 |
| 4대 은행의 현재 제품을 공개자료만으로 확정할 수 있는가? | 불가. 공개 구축 사례와 현재 전체 topology를 구분해야 함 |
| JEX는 단순 JSP 도구인가? | 금융 전문·업무 component·DB/AP adapter를 표준화한 업무 프레임워크로 이해하는 편이 정확 |
| Spring이 대체할 수 있는가? | 일부 런타임·API·이벤트·배치 계층은 가능하지만 금융 전문·운영·대사 규칙은 별도 이전 필요 |
| 현대화의 핵심 | adapter·contract·event·idempotency·observability·reconciliation |

## 결론

은행 IT의 현대화는 EAI·MCI·FEP라는 이름을 제거하고 Spring·Kafka·API Gateway를 배치하는 작업이 아니다.

```text
기존 금융 연계가 가진 자산
= 전문·거래 ID·재처리·대사·운영 경험

현대화가 보완할 것
= 도메인 경계·schema version·자동 테스트·관측성·보안·배포 독립성
```

JEX 계열 프레임워크에서 배울 수 있는 핵심은 금융 업무 전문을 표준화하고 반복되는 입출력·업무 component·DB/AP 연계를 개발자 공통 규약으로 만든 점이다. Spring에서 중점적으로 차용할 수 있는 것은 IoC/DI, 관심사 분리, transaction 경계, adapter abstraction, 테스트 가능성, observability integration이다.

가장 현실적인 목표는 다음이다.

```text
JEX/레거시 전문
  → 안정적인 anti-corruption adapter

MCI
  → API Gateway/BFF + channel contract

EAI
  → domain integration + event platform + schema registry

FEP
  → 외부기관 integration gateway + inquiry/retry/reconciliation

Spring
  → API·업무 서비스·event·batch·security·observability runtime
```

**한 문장 요약:** 은행 현대화의 승부처는 기존 EAI·MCI·FEP·JEX를 무조건 없애는 데 있지 않고, 그 안에 축적된 금융 전문·대사·재처리 경험을 Spring·API·이벤트·계약 테스트·관측성으로 안전하게 재배치하는 데 있다.

## 참고 자료

- [전자신문: 금융권 통합 솔루션 도입으로 업무 효율 높인다](https://www.etnews.com/20140410000114)
- [INZENT EIMS: 전사 인터페이스 관리 시스템](https://www.inzent.com/solution_eims.php)
- [INZENT MCI/FEP](https://www.inzent.com/solution_mci_fep.php)
- [JEX Framework 공개 설명 자료](https://m.blog.naver.com/okskmk2/220807329434)
- [Spring Framework 공식 문서](https://docs.spring.io/spring-framework/reference/)
- [Spring Boot 공식 문서](https://docs.spring.io/spring-boot/index.html)
- [Spring Kafka 공식 문서](https://docs.spring.io/spring-kafka/reference/)
- [Apache Kafka 공식 문서](https://kafka.apache.org/documentation/)

> 특정 은행의 현재 내부 솔루션·버전·구성은 공개자료만으로 확인하지 못했다. 이 글의 4대 은행 관련 서술은 공개 범위의 한계와 분석 프레임을 설명하기 위한 것이며, 비공개 내부 구성을 사실처럼 주장하지 않는다.
