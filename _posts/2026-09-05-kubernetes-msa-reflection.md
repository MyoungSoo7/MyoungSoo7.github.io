---
layout: post
title: "쿠버네티스와 MSA에 대한 고찰: 분산 시스템의 자유와 운영 비용"
date: 2026-09-05 21:36:41 +0900
categories: [Architecture]
tags: [Kubernetes, MSA, Microservices, K3s, DevOps, SRE]
---

# 쿠버네티스와 MSA에 대한 고찰

쿠버네티스와 MSA는 함께 언급되는 경우가 많다. 컨테이너를 여러 서비스로 나누고 Kubernetes에 배포하면 현대적인 아키텍처가 완성되는 것처럼 보인다. 하지만 실제 운영에서 중요한 질문은 “몇 개의 파드로 나누었는가?”가 아니다.

- 서비스 경계가 업무 경계와 맞는가?
- 한 서비스의 장애가 다른 서비스로 전파되지 않는가?
- 데이터 일관성과 중복 처리를 감당할 수 있는가?
- 배포와 관측이 실제로 독립성을 뒷받침하는가?
- 팀이 늘어난 운영 복잡성을 감당할 수 있는가?

Kubernetes는 컨테이너화된 워크로드와 서비스를 선언적 설정과 자동화로 관리하는 플랫폼이다.[1] MSA는 하나의 애플리케이션을 독립적으로 배포 가능한 서비스들의 조합으로 설계하는 아키텍처 스타일이다.[3] 둘은 서로 보완적이지만, Kubernetes가 MSA를 자동으로 만들어 주는 것은 아니다.

## 1. Kubernetes와 MSA의 관계

```text
MSA
 ├─ 업무 capability 중심의 서비스 경계
 ├─ 독립 배포
 ├─ 서비스 간 계약과 통신
 ├─ 데이터 소유권
 └─ 장애 격리와 운영 책임

Kubernetes
 ├─ Pod 실행과 스케줄링
 ├─ Service discovery와 load balancing
 ├─ rollout/rollback
 ├─ self-healing
 ├─ resource 관리
 └─ secret/config 관리
```

MSA가 “무엇을 어떻게 나눌 것인가”에 대한 애플리케이션·조직·데이터 설계라면, Kubernetes는 나뉜 컴포넌트를 실행하고 원하는 상태로 수렴시키는 플랫폼이다. Kubernetes는 서비스 디스커버리, 롤아웃·롤백, self-healing, 수평 확장 같은 실행 기반을 제공하지만, 서비스의 업무 경계나 데이터 트랜잭션을 정의하지 않는다.[1]

Kubernetes 공식 문서가 강조하듯, Kubernetes는 데이터베이스·메시지 버스·로깅·모니터링을 모두 내장한 완성형 PaaS가 아니다. 애플리케이션 수준의 구성요소와 관측 시스템은 별도로 선택하고 운영해야 한다.[1]

## 2. MSA는 왜 필요한가

### 독립적인 변경과 배포

서비스가 사업 capability 단위로 나뉘면 한 기능의 변경이 전체 애플리케이션 배포로 이어지지 않을 수 있다. 팀이 서비스의 개발·테스트·배포·운영을 함께 책임질 수 있다면 변경의 범위와 책임이 선명해진다.[3]

### 독립적인 확장

검색, 결제, 이미지 처리, 알림은 부하 특성이 다르다. 하나의 모놀리스에서는 전체를 함께 확장해야 하지만, 서비스가 분리되면 병목이 있는 영역만 별도로 확장할 수 있다.

다만 독립 확장은 서비스 경계와 데이터 접근이 실제로 독립적일 때만 가능하다. 모든 서비스가 동일한 DB와 공통 테이블을 직접 조회한다면 배포 단위만 나뉘었을 뿐 결합도는 그대로 남는다.

### 장애 영향 범위 제한

한 서비스의 장애가 전체 사용자 요청을 중단시키지 않도록 timeout, retry, circuit breaker, bulkhead, fallback, 비동기 이벤트를 설계할 수 있다. 그러나 서비스가 네트워크 경계를 넘는 순간 실패 가능성이 늘어나므로 MSA는 장애를 없애는 구조가 아니라 장애를 다루는 책임을 분산시키는 구조에 가깝다.

## 3. Kubernetes가 MSA 운영에 주는 것

### 선언적 상태 관리

Kubernetes에서는 원하는 replica 수, 이미지, 환경변수, probe, resource를 선언하고 control plane이 실제 상태를 원하는 상태로 수렴시킨다. Deployment는 롤아웃과 롤백의 단위를 제공하고, Service는 파드 집합에 안정적인 네트워크 접근점을 제공한다.[1][2]

### self-healing과 readiness

컨테이너가 종료되면 재시작하거나, readiness probe에 실패한 파드를 트래픽 대상에서 제외할 수 있다. 이것은 장애를 자동으로 해결한다는 의미가 아니다. 프로세스를 다시 실행할 수 있을 뿐이며, 데이터 손상·잘못된 설정·외부 의존성 장애·비즈니스 오류까지 해결해 주지는 않는다.

운영자는 다음을 구분해야 한다.

- 파드가 Running인가
- 애플리케이션이 Ready인가
- 요청이 성공하는가
- 데이터 처리가 실제로 완료됐는가
- 재시작이 신규 장애인가, 누적 이력인가

### Service discovery와 네트워크 경계

서비스 간 호출은 Pod IP가 아니라 Kubernetes Service와 DNS를 통해 추상화하는 것이 일반적이다. 그러나 안정적인 DNS 이름이 있다고 해서 API 계약, timeout, 인증, 트래픽 정책이 자동으로 안전해지는 것은 아니다.

MSA에서 네트워크 호출은 다음을 명시해야 한다.

- 요청·응답 스키마
- timeout deadline
- retry 가능 여부
- idempotency key
- 인증과 권한
- backward compatibility
- 오류 코드와 fallback

## 4. 가장 어려운 문제는 데이터다

서비스가 자기 데이터를 소유하고 다른 서비스가 API로 접근하도록 하는 database-per-service 패턴은 결합도를 낮추고 독립적인 개발·배포·확장을 돕는다.[4] 여기서 database-per-service는 반드시 서비스마다 별도의 DB 서버를 만든다는 뜻은 아니다. private table, schema, database server처럼 여러 구현 수준이 가능하다.[4]

문제는 분산 트랜잭션이다.

```text
주문 생성
  1. Order Service: 주문 PENDING 저장
  2. Customer Service: 신용 한도 예약
  3. Payment Service: 결제 승인
  4. Inventory Service: 재고 예약
  5. 성공하면 주문 CONFIRMED
  6. 실패하면 보상 트랜잭션
```

각 서비스가 자신의 로컬 트랜잭션만 처리하면 모든 단계를 하나의 ACID 트랜잭션으로 묶기 어렵다. Saga는 여러 로컬 트랜잭션을 순서대로 실행하고, 실패하면 이전 단계의 보상 트랜잭션을 실행하는 방식이다.[5]

Saga에는 choreography와 orchestration이 있다.

- **Choreography**: 각 서비스가 도메인 이벤트를 발행하고 다음 서비스가 반응
- **Orchestration**: 별도의 coordinator가 각 서비스에 명령

Saga는 자동 rollback이 아니다. 개발자가 보상 동작을 직접 설계해야 하고, 격리 수준이 ACID와 같지 않기 때문에 중복 이벤트·경쟁 상태·부분 실패를 다뤄야 한다.[5]

## 5. Kubernetes 위 MSA의 운영 비용

### 배포 단위가 늘어난다

모놀리스 하나를 관리하던 시스템이 20개 서비스가 되면 Deployment, Service, ConfigMap, Secret, Ingress, HPA, PDB, ServiceMonitor, dashboard, alert, runbook도 늘어난다.

“서비스를 나누면 배포가 쉬워진다”는 말은 CI/CD, 이미지 관리, 환경 설정, 호환성 테스트, rollback 절차가 자동화되어 있을 때만 성립한다.

### 관측이 필수다

단일 프로세스에서는 stack trace 하나로 요청 흐름을 추적할 수 있지만, MSA에서는 요청이 여러 파드와 서비스로 이동한다. 최소한 다음 식별자를 전파해야 한다.

- `trace.id`
- `request.id`
- `tenant.id` 또는 안전한 업무 식별자
- service name
- version
- zone/node/pod 정보

메트릭은 서비스별 요청량·오류율·지연시간을 보여주고, 로그는 상세 사건을 보여주며, trace는 서비스 간 호출 경로를 보여준다. Kubernetes의 파드가 모두 Running이라는 사실만으로 사용자 요청의 성공을 증명할 수 없다.

### 장애가 연쇄될 수 있다

한 서비스의 latency 증가가 호출자 connection pool을 소진시키고, retry가 트래픽을 증폭시키며, 결국 다른 서비스까지 장애가 나는 구조가 가능하다.

따라서 다음 보호장치가 필요하다.

- 짧고 명시적인 timeout
- 지수 backoff와 retry 상한
- retry 가능한 오류와 불가능한 오류 구분
- circuit breaker
- bulkhead와 pool 분리
- queue 기반 비동기 처리
- load shedding
- 장애 격리와 graceful degradation

재시작 정책만으로 이런 연쇄 장애를 막을 수는 없다.

## 6. 실제 운영 관점에서의 Kubernetes·MSA 고찰

### “Running”은 서비스 정상의 충분조건이 아니다

운영 점검에서는 다음을 분리해야 한다.

1. 노드가 Ready인가
2. 파드가 Running인가
3. readiness probe가 통과하는가
4. 애플리케이션 요청이 성공하는가
5. downstream 호출이 정상인가
6. 메시지와 배치가 실제로 처리됐는가
7. DB와 외부 시스템의 결과가 일치하는가

특히 restartCount는 누적값이다. 현재 장애인지 과거의 재시작인지 확인하려면 Last State, 종료 사유, 종료 시각, uptime을 함께 봐야 한다.

### 성공 카운터 0은 업무 성공이 아니다

CronJob과 consumer를 운영할 때도 단순히 에러 카운터가 0인지만 보면 안 된다. 기대 실행 건수, source response, filtered/upsert 수, 마지막 non-zero 성공 시각을 확인해야 한다.

예를 들어 배치가 “실패 없이 종료”했지만 입력 데이터가 0건이어서 실제 처리도 0건일 수 있다. 업무 성공을 판단하려면 기술 상태와 처리 결과를 함께 검증해야 한다.

### MSA의 경계는 서비스 수가 아니라 책임이다

서비스를 많이 쪼개는 것이 좋은 설계는 아니다. 다음과 같은 신호가 있다면 경계를 다시 검토해야 한다.

- 항상 함께 배포되는 두 서비스
- 매 요청마다 서로 여러 번 호출하는 서비스
- 같은 DB 테이블을 직접 공유하는 서비스
- 하나의 장애가 전체 호출 경로를 막는 구조
- 팀이 운영할 수 없는 수의 배포·알림·대시보드

반대로 변경 주기, 데이터 소유권, 부하 특성, 장애 영향 범위, 팀 책임이 분명히 다르면 분리가 의미 있을 수 있다.

## 7. 모놀리스, 모듈러 모놀리스, MSA

MSA의 반대편에 무조건 큰 모놀리스만 있는 것은 아니다. 모듈러 모놀리스는 하나의 배포 단위를 유지하면서 내부의 업무 경계·의존성·데이터 소유권을 엄격히 나누는 중간 단계가 될 수 있다.

```text
모놀리스
  → 모듈러 모놀리스
  → 일부 서비스 분리
  → 필요한 영역만 MSA
```

이 접근은 네트워크 호출과 분산 트랜잭션을 바로 도입하지 않으면서 도메인 경계와 팀 책임을 먼저 검증할 수 있다. 실제로 서비스 경계가 아직 불확실하거나 운영팀이 작다면, 모듈러 모놀리스가 더 정직하고 경제적인 선택일 수 있다.

## 8. 도입·운영 판단 체크리스트

### MSA로 분리하기 전에

- 독립적으로 변경되는 업무 capability인가?
- 데이터 소유자가 명확한가?
- 독립 배포가 실제로 필요한가?
- 서비스 간 호출량과 latency를 감당할 수 있는가?
- 장애·재시도·중복 이벤트를 처리할 수 있는가?
- 계약 테스트와 호환성 정책이 있는가?
- 팀이 pager와 운영 책임을 감당할 수 있는가?

### Kubernetes에 올리기 전에

- 컨테이너 이미지가 재현 가능하게 빌드되는가?
- readiness/liveness/startup probe가 업무 특성에 맞는가?
- resource request/limit가 정의됐는가?
- 로그·메트릭·trace가 수집되는가?
- Secret과 설정이 이미지에서 분리됐는가?
- rollback이 검증됐는가?
- DB migration의 forward/backward compatibility가 있는가?
- 장애 시 runbook과 알림 수신자가 있는가?

## 결론

Kubernetes와 MSA는 현대적인 시스템을 만들기 위한 유용한 도구와 아키텍처지만, 복잡성을 제거하는 마법은 아니다.

Kubernetes는 분산 애플리케이션의 실행·배포·확장·복구 기반을 제공한다. MSA는 업무 경계와 팀·데이터·배포 책임을 분리하는 설계 방식이다. 두 가지를 결합하면 독립 배포와 확장, 장애 격리의 가능성이 커지지만, 그 대가로 네트워크 실패, 분산 데이터, 관측, 보안, 계약 관리, 운영 자동화의 책임이 늘어난다.

결국 좋은 질문은 “MSA인가?”가 아니다.

> 이 경계를 분리했을 때 변경·확장·장애 대응·팀 운영이 실제로 더 쉬워지는가?

그리고 Kubernetes에 대해서도 다음을 물어야 한다.

> 원하는 상태를 선언하는 것뿐 아니라, 실제 업무 결과와 장애 복구까지 검증할 수 있는가?

서비스 수와 파드 수보다 중요한 것은 책임의 명확성, 실패의 격리, 데이터의 일관성, 운영 증거다. MSA와 Kubernetes는 그 원칙을 실현할 때 가치가 있고, 유행을 복제하는 순간 운영 비용만 늘릴 수 있다.

## 참고 자료

[1] Kubernetes Overview — 선언적 관리, 서비스 디스커버리, 롤아웃, self-healing, 확장  
[2] Kubernetes Components — control plane, node components, addons  
[3] Martin Fowler, Microservices — 서비스 경계, 독립 배포, 장애 설계, 자동화  
[4] Microservices.io, Database per Service — 데이터 소유권과 결합도  
[5] Microservices.io, Saga — 분산 트랜잭션과 보상 처리

## 출처

- Kubernetes Overview: https://kubernetes.io/docs/concepts/overview/
- Kubernetes Components: https://kubernetes.io/docs/concepts/overview/components/
- Martin Fowler, Microservices: https://martinfowler.com/articles/microservices.html
- Database per Service: https://microservices.io/patterns/data/database-per-service.html
- Saga Pattern: https://microservices.io/patterns/data/saga.html

## Sources

[1] https://kubernetes.io/docs/concepts/overview — Kubernetes Overview
[2] https://kubernetes.io/docs/concepts/overview/components — Kubernetes Components
[3] https://martinfowler.com/articles/microservices.html — Microservices
[4] https://microservices.io/patterns/data/database-per-service.html — Database per Service
[5] https://microservices.io/patterns/data/saga.html — Saga Pattern
