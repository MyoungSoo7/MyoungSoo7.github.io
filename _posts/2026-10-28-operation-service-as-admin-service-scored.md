---
layout: post
title: "operation-service 를 '관리자 서비스' 로 쓰면 몇 점인가 — 10점 만점 5점, 이름표와 실제 관리자 API 위치가 다르다"
date: 2026-10-28 02:14:00 +0900
categories: [Architecture, MSA]
tags: [Settlement, MSA, operation-service, Backoffice, Spring Security, ADR, Hexagonal]
---

정산 플랫폼의 자바 서비스는 지금 다섯 개다 — **order · settlement · finance · external-data · operation** (앞단에 gateway). [어제 글]({% post_url 2026-10-27-settlement-18-to-6-the-consumers-nobody-listed %})에서 18개를 6개로 접은 과정을 적었다. 이번 질문은 하나다.

> **operation-service 를 "관리자 서비스(백오피스)" 로 쓴다고 하면, 지금 상태로 몇 점인가?**

모든 수치는 2026-10-28 새벽 `master` 최신 커밋을 받아 직접 센 값이다. 저장소는 비공개라 링크 대신 파일 이름으로 적는다.

## 0. 결론 — 10점 만점에 5점

**모듈 자체는 잘 만들었는데, "관리자 서비스" 라는 역할에는 맞지 않는다.** 이유는 한 줄이다.

> 관리자 API 의 대부분이 operation 이 아니라 **order 와 settlement 에** 있다.

그리고 이건 실수가 아니라 **의도된 설계**다. 프로젝트 ADR 이 "관리자 화면에서 관리되니 묶는다" 는 근거를 이미 기각했다(아래 2절). 그러니 이 5점은 "코드가 나쁘다" 가 아니라 **"질문의 전제와 설계 의도가 다르다"** 는 점수다. 설계 의도대로 **"플랫폼 운영 서비스"** 로 평가하면 7점은 줄 수 있다.

## 1. 채점표

| 항목 | 점수 | 근거 |
|---|---|---|
| 관리자 기능 커버리지 | **2** | 관리자 API 가 있는 소스 파일 수: order 24 · settlement 26 · external-data 8 · finance 6 · **operation 5** |
| 권한·보안 | **7** | `/api/ops/**` 기본 ADMIN, 게시판·교육 관리 경로 ADMIN, webhook 은 Bearer 토큰. 단 필터 체인 4개가 경로별로 나뉘어 있어 복잡하다 |
| 모듈 경계(아키텍처) | **8** | 헥사고날, 슬라이스별 ArchUnit 테스트 3종, DB 스키마도 슬라이스별로 분리 |
| 테스트 | **5** | 슬라이스별 편차가 크다 — 게시판은 탄탄하고, 핵심인 인시던트는 얇다 |
| 운영 격리 | **5** | ADR 스스로 "게시판 트래픽이 관제 프로세스를 잠식할 수 있다" 고 적었다 |
| 문서 최신성 | **4** | `function.md` 가 흡수된 슬라이스 3개를 다루지 않고, 이미 있는 이상 탐지를 "예정" 으로 적고 있다 |
| **종합** | **5 / 10** | 가중치를 두지 않은 단순 평균(5.2)을 내림 |

이 점수는 **필자의 판단**이다. 정량 지표는 직접 센 파일 수뿐이고, 나머지는 코드와 ADR 을 읽고 매겼다.

## 2. 왜 관리자 API 가 operation 에 없나 — ADR 이 일부러 막았다

게이트웨이 라우팅을 보면 관리자 경로가 어디로 가는지 바로 보인다.

| 서비스 | 받는 관리자 경로 (일부) |
|---|---|
| **order** | `/admin/rbac` · `/admin/members` · `/admin/audit-logs` · `/admin/menus` · `/admin/common-codes` · `/admin/coupons` · `/admin/refunds` · `/admin/products` … |
| **settlement** | `/admin/settlements` · `/admin/payouts` · `/admin/reconciliation` · `/admin/monthly-closing` · `/admin/outbox` · `/admin/dlq` · `/admin/audit-trail` … |
| **finance** | `/admin/expense-receipts` · `/admin/finance/dlq` |
| **operation** | `/admin/boards` · `/admin/education` · `/admin/ops-dlq` · `/api/ops/**`(인시던트) |

**권한(RBAC)·회원·감사 로그·메뉴·공통코드** — 백오피스의 뼈대가 전부 order 에 있다. order 가 로그인과 사용자 마스터를 가진 서비스이기 때문이다.

이건 ADR 0043(board·education 을 operation 으로 흡수)에 정면으로 적혀 있다.

> 같은 날 ADR 0042 는 *"관리자 화면에서 관리되니 관리 기능으로 묶는다"* 는 병합 근거를 기각했다 (그 규칙엔 멈추는 지점이 없다).

같은 ADR 은 `backoffice-service` 를 새로 만드는 안도 "서비스를 줄이는 사이클에서 프로세스를 늘리는 모순" 이라며 기각했다. 그리고 operation 의 정의를 이렇게 바꿨다.

> 사업 도메인(거래·정산·금융)에도, 외부 데이터 위성에도 속하지 않는 **지원 기능들의 거처.**

즉 operation 은 **"관리자 서비스" 가 아니라 "갈 곳 없는 지원 기능의 집"** 이다. 관리자 기능은 **각 도메인 서비스가 자기 데이터에 대해 직접 가진다.** 정산 지급 승인을 operation 으로 옮기면 정산 원장에 쓰는 코드가 정산 서비스 밖으로 나가는데, 이건 [마이크로서비스의 기본 원칙인 분산 데이터 관리](https://martinfowler.com/articles/microservices.html)와 정면으로 부딪힌다.

## 3. 현재 상태의 장점

**① 슬라이스 경계가 코드로 강제된다.** operation 안에는 7개 패키지(incident·signal·anomaly·notification·board·education·config)가 있고, `OperationArchitectureTest`·`BoardArchitectureTest`·`EducationArchitectureTest` 가 슬라이스 사이 import 를 막는다. ADR 이 "관제가 커지면 다시 꺼낼 수 있다(가역적)" 고 말할 수 있는 근거가 이것이다.

**② 데이터 경계는 스키마로 남겼다.** board·education 을 흡수하면서 DB 는 하나(`lemuel_operation`)로 합쳤지만 테이블은 `board`·`education` 스키마로 나눠 뒀다. 프로세스는 합쳐도 데이터 소유권은 흐려지지 않는다.

**③ 관리 경로의 기본값이 "거부" 다.** `/api/ops/**` 는 webhook 하나만 열고 나머지를 전부 `hasRole("ADMIN")` 으로 막는다. 게시판·교육도 `/admin/**` 는 ADMIN 전용이다. 새 엔드포인트를 추가해도 깜빡하면 **열리는 쪽이 아니라 닫히는 쪽**이다.

**④ 관제 경로가 비즈니스를 절대 막지 않는다.** Alertmanager webhook 은 항상 200 을 돌려주고, 실패 신호 발행은 절대 예외를 던지지 않는다(`function.md` §1). 관리 기능이 잘못돼도 주문·정산 트랜잭션은 영향을 받지 않는다.

**⑤ 기능이 실제로 있다.** 인시던트 상태머신(OPEN→ACK→RESOLVED/FALSE_POSITIVE, 낙관적 락), 5분 단위 신호 집계, 기준선 기반 이상 탐지, 실시간 알림 스트림, 게시판(첨부·숨김·고정·복원), 교육 과정·레슨 관리까지 — 관리자 화면에 붙일 재료는 충분하다.

## 4. 현재 상태의 단점

**① 이름과 실제가 다르다.** "operation = 관리자" 로 읽히기 쉽지만 백오피스 핵심(RBAC·회원·감사 로그)은 order 에 있다. 새로 온 사람이 관리자 기능을 operation 에서 찾으면 헛걸음한다.

**② 관리자 화면이 최소 4개 서비스를 부른다.** 관리자 대시보드 한 장을 그리려면 order·settlement·finance·operation 을 모두 호출해야 한다. 지금은 게이트웨이가 경로만 나눠 줄 뿐, 화면용으로 묶어 주는 층이 없다.

**③ 같은 개념이 서비스마다 따로 있다.** DLQ 관리 API 는 `shared-common` 의 공용 컨트롤러 하나를 서비스마다 띄우는 구조라, 게이트웨이에서 `/admin/dlq`(settlement)·`/admin/finance/dlq`·`/admin/ops-dlq` 로 **경로를 바꿔 가며** 나눠 받는다. 감사 기록도 order 의 `/admin/audit-logs` 와 settlement 의 `/admin/audit-trail` 로 갈라져 있다. 운영자 입장에선 "DLQ 를 어디서 보지?" 가 세 군데다.

**④ 보안 필터 체인이 4개다.** operation 하나에 `SecurityFilterChain` 이 4개(관제 Order 1·알림 2·게시판 3·교육 4) + 공용 체인이 있다. Spring Security 는 [여러 체인 중 요청과 처음 맞는 하나만 적용한다](https://docs.spring.io/spring-security/reference/servlet/architecture.html). 그래서 `securityMatcher` 범위를 잘못 잡으면 어떤 경로가 엉뚱한 체인으로 떨어진다. 지금은 경로가 겹치지 않게 잘 나눠져 있지만, 관리자 기능을 더 얹을수록 **체인 수와 실수 가능성이 같이 늘어나는 구조**다.

**⑤ webhook 토큰이 없으면 인증 없이 열린다.** `OpsWebhookAuthFilter` 는 `app.ops.webhook.token` 이 비어 있으면 "개발 모드" 로 통과시키고 경고를 한 번만 남긴다. 로컬 편의를 위한 것이지만, 운영 배포에서 이 값이 빠지면 누구나 가짜 인시던트를 넣을 수 있다. **운영 프로파일에서는 기동을 실패시키는 쪽**이 안전하다.

**⑥ 핵심 슬라이스 테스트가 얇다.** 소스 대비 테스트 파일 수를 세면:

| 슬라이스 | main | test |
|---|---|---|
| incident | 37 | **4** |
| signal | 17 | 7 |
| anomaly | 13 | 4 |
| notification | 33 | 10 |
| board | 89 | 28 |
| education | 32 | 12 |

관제의 핵심인 **incident 가 가장 얇다.** 상태머신·재발화·자동 해제처럼 경계 조건이 많은 곳이라 아쉽다. (파일 수는 테스트 품질의 대리 지표일 뿐이다.)

**⑦ 운영 격리가 약해졌다 — ADR 이 스스로 인정한다.** ADR 0043 의 "정직한 대가" 절: 게시판 첨부 업로드(최대 20MB)와 교육 API 가 관제와 같은 프로세스의 CPU·커넥션 풀을 쓴다. DB 가 죽으면 관제·알림·게시판·교육이 같이 멈춘다. 여기에 관리자 기능까지 더 얹으면 **장애 범위가 더 넓어진다.**

**⑧ 기능 명세서가 따라오지 못했다.** `function.md` 는 여전히 "운영 관제 마이크로서비스" 로 시작하고, incident·signal 두 BC 만 설명한다. 흡수된 notification·board·education 은 없다. 이상 탐지(anomaly 슬라이스, 13파일)는 이미 들어와 있는데 로드맵엔 "Phase 3 예정" 으로 남아 있다.

## 5. 개선할 점 — 우선순위 순

| 순위 | 할 일 | 왜 |
|---|---|---|
| 1 | **"관리자 서비스" 라는 기대를 버리거나, 관리자 화면 전용 층을 따로 둔다** | 관리자 API 를 operation 으로 옮기는 건 ADR 0042·0043 과 데이터 소유 원칙을 거스른다. 화면 하나가 여러 서비스를 불러야 하는 문제는 [BFF(Backend for Frontend)](https://samnewman.io/patterns/architectural/bff/) 나 [게이트웨이 조합](https://microservices.io/patterns/apigateway.html)으로 푸는 게 맞다. 쓰기는 각 도메인에 두고, **읽기 조합만** 한 곳에서 한다 |
| 2 | **운영 프로파일에서 webhook 토큰 누락 시 기동 실패** | 경고 한 줄로는 운영에서 놓친다 |
| 3 | **incident 슬라이스 테스트 보강** | 상태 전이 위반(409), 재발화 시 심각도 상향만 반영, 해제 후 재발 시 새 인시던트, 낙관적 락 충돌 — 문서에 적힌 규칙마다 테스트 하나씩 |
| 4 | **`function.md` 를 "플랫폼 운영 서비스" 기준으로 다시 쓰기** | ADR 0043 이 정의를 바꿨으니 명세서도 따라가야 한다. 7개 슬라이스 표 + 이상 탐지 진행 상태 반영 |
| 5 | **DLQ·감사 로그의 운영자 진입점 하나로 모으기** | 저장소는 각자 두되, 관리자 화면에서 한 메뉴로 보이게. 1번의 조합 층이 있으면 자연히 해결된다 |
| 6 | **보안 체인 회귀 테스트** | 경로마다 "익명/일반 사용자/ADMIN" 으로 한 번씩 찔러 보는 표 기반 테스트. 체인이 늘어도 경로가 엉뚱한 체인으로 새는 걸 잡는다 |
| 7 | **관제 격리 기준을 숫자로 정하기** | ADR 이 "관제의 성역이 필요한 규모가 오면 다시 꺼낸다" 고 했다. 그 "규모" 를 첨부 업로드 동시 수, 커넥션 풀 사용률 같은 지표로 미리 정해 두면 결정이 쉬워진다 |

## 6. 그래서 어떻게 쓰면 되나

- **operation 은 지금처럼 "플랫폼 운영 서비스" 로 둔다.** 관제·알림·게시판·교육의 관리 기능은 이미 여기에 있고, 그 범위에선 7점짜리 모듈이다.
- **"관리자 서비스" 가 필요하면 쓰기를 옮기지 말고 화면을 묶는다.** 회원·권한은 order, 지급·정산은 settlement 에 그대로 두고, 관리자 프론트가 부르는 **읽기 전용 조합 층**만 하나 둔다.
- 그 조합 층을 operation 에 얹을지는 7번 기준과 같이 판단한다. 관제와 같은 프로세스에 관리자 대시보드 트래픽까지 실으면 ADR 이 이미 지적한 격리 문제가 커진다.

## References

- Martin Fowler & James Lewis, *Microservices* — Decentralized Data Management: <https://martinfowler.com/articles/microservices.html>
- Chris Richardson, *Pattern: API Gateway / Backends for Frontends*: <https://microservices.io/patterns/apigateway.html>
- Sam Newman, *Backends For Frontends*: <https://samnewman.io/patterns/architectural/bff/>
- Spring Security Reference — Servlet Architecture (`SecurityFilterChain`, 여러 체인 중 첫 매칭): <https://docs.spring.io/spring-security/reference/servlet/architecture.html>
- Spring Security Reference — Java Configuration, Multiple HttpSecurity Instances: <https://docs.spring.io/spring-security/reference/servlet/configuration/java.html>
- 저장소 내부 문서(비공개): `docs/adr/0041-notification-absorbed-into-operation.md`, `docs/adr/0043-board-education-absorbed-into-operation.md`, `operation-service/function.md`, `gateway-service` 라우트 설정
