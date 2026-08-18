---
layout: post
title: "표에 적은 네 문장을 리포지토리에 대조했다 — settlement 실측"
date: 2026-08-18 21:30:00 +0900
categories: [Architecture, Kubernetes]
tags: [settlement, Kafka, Outbox, ArchUnit, ArgoCD, Velero, MSA]
---

정리해 둔 역량 표가 있다. 네 줄짜리다.

![정합성 중심 백엔드 / 이벤트 기반 설계 / 운영까지 책임 / AI 활용과 통제 — 네 항목의 역량 표](/assets/images/settlement-four-claims.jpg)

표는 그 자체로는 주장이다. 주장은 대조 대상이 있을 때만 값이 매겨진다. 그래서 이 글은 표를 해설하지 않고, **네 문장을 `settlement` 리포지토리와 실제 클러스터에 하나씩 대 봤다.**

대조 시점은 develop 브랜치 `93fe6368`, 클러스터는 K3s 6노드(`settlement-prod` 네임스페이스)다. 아래 수치는 전부 그 시점에 직접 센 것이고, 맞지 않은 항목은 맞지 않았다고 적었다.

---

## 0. 먼저 크기

문장을 재기 전에 대상의 크기를 알아야 한다.

| 항목                                | 수           |
| ----------------------------------- | ------------ |
| Java 소스 파일                      | 3,737        |
| Kotlin / Python / Go                | 57 / 53 / 22 |
| Gradle 모듈 (`settings.gradle.kts`) | 17           |
| Flyway 마이그레이션                 | 555          |
| 테스트 파일                         | 1,036        |
| develop 커밋 (2026-02-10 이후)      | 1,614        |

개인 프로젝트치고는 큰 편이고, 큰 만큼 "말로만 그렇게 돼 있는" 부분이 생기기 쉽다. 그게 이 대조의 이유다.

---

## 1. "정합성 중심 백엔드" — 확인됨

> 트랜잭션·동시성·멱등성·원장·대사 관점으로 주문/결제/정산 문제 해결

네 단어를 각각 찾았다.

**트랜잭션.** `@Transactional` 515개. 숫자 자체는 의미가 크지 않지만, 원장 계열 마이그레이션(`account_entries` 계열)이 append-only 방향으로 굳어져 온 흔적이 남아 있다. 회계 원장에서 UPDATE 를 막는 건 정합성 설계의 기본 자세다.

**동시성.** `@Version`(낙관적 락)이 45개 파일, `PESSIMISTIC_WRITE`(비관적 락)가 22곳. 둘을 섞어 쓴다는 건 "일단 락 걸고 본다"가 아니라 **경합 빈도에 따라 전략을 나눴다**는 뜻이다. 잔액 차감처럼 충돌이 잦은 지점과, 충돌이 드문 조회·갱신 지점을 같은 도구로 다루면 둘 중 하나는 반드시 손해를 본다.

**멱등성.** 이게 가장 명확했다. 세 겹이 실제로 존재한다.

1. 발행 측 — `CREATE UNIQUE INDEX IF NOT EXISTS uq_{investment,organization,card}_outbox_event_id` 같은 유니크 인덱스로 **같은 event_id 의 중복 발행**을 DB가 거부한다.
2. 수신 측 — 서비스마다 `processed_events` 테이블이 있다. 이미 처리한 event_id 는 두 번째 도착에서 걸러진다.
3. 최종 방어 — 비즈니스 유니크 제약.

Kafka 는 기본적으로 at-least-once, 즉 **중복 전달을 정상 동작으로 규정한다**.[^kafka] 그러니 컨슈머가 멱등하지 않으면 그건 Kafka 의 문제가 아니라 설계의 구멍이다. 세 겹은 과하지 않다.

**원장·대사.** 차변/대변(DEBIT) 표기가 21곳에 흩어져 있고, 대사(reconciliation) 서비스는 이 리포에서 유일하게 **Kotlin 전용 모듈**이다. Java 파일이 0개다. 언어를 바꿔 가며 한 모듈을 통째로 쓴 이유까지는 코드가 말해 주지 않지만, 최소한 "이름만 있는 모듈"은 아니다.

**판정: 확인됨.** 네 단어 전부 대응하는 코드가 있다.

---

## 2. "이벤트 기반 설계" — 세 개는 확인, 하나는 절반

> Kafka·Transactional Outbox·프로젝션·DB-per-service를 개인 프로젝트로 검증

**Kafka.** `KafkaTemplate` + `@KafkaListener` 사용처가 143곳, 그중 `@KafkaListener` 만 61개. 컨슈머가 61개면 서비스 간 결합이 HTTP 호출이 아니라 이벤트로 상당 부분 넘어갔다는 뜻이다.

**Transactional Outbox.** outbox 테이블을 가진 서비스가 13개. `V20260728010000__outbox_envelope_n4.sql` 처럼 봉투(envelope) 규격을 나중에 통일한 마이그레이션까지 있다. 이 패턴의 요점은 **비즈니스 데이터 변경과 메시지 발행을 하나의 로컬 트랜잭션에 묶는 것**이고,[^outbox] 그래야 "DB 는 커밋됐는데 이벤트는 안 나갔다"가 사라진다. 13개 서비스에 같은 구조가 반복돼 있다.

**프로젝션.** 존재하되 넓지는 않다. 읽기 모델 SQL 이 확인된 건 `card-service` 쪽이 대표적이고, 별도 조회 전용 배포가 클러스터에 떠 있다. "전 서비스 CQRS"는 아니다.

**DB-per-service — 여기서 갈린다.**

리포지토리는 확실히 그렇게 쓰여 있다. 서비스마다 독립 jdbc URL 이 박혀 있고(`account-postgres:5432/lemuel_account` 형태), 하네스 문서는 cross-DB 조인 0건을 주장한다. **논리적 분리는 진짜다.**

그런데 클러스터를 보면 Postgres 인스턴스는 **하나**다.

```
jen-prod / jen-postgres-0   (pgvector/pgvector:pg17)
└─ lemuel_account, lemuel_ai, lemuel_commondata, lemuel_company,
   lemuel_economics, lemuel_financial, lemuel_investment, lemuel_loan,
   lemuel_market, lemuel_operation, lemuel_organization, lemuel_settlement
```

12개 데이터베이스가 한 StatefulSet 파드 안에 있다. Database per service 패턴이 노리는 것 중 **스키마 결합 제거는 달성**했지만, **장애 격리는 달성하지 못했다**.[^dbps] 이 파드가 죽으면 12개 도메인이 같이 죽는다. 개인 프로젝트에서 인스턴스 12개를 띄우지 않은 건 합리적인 선택이지만, 그건 "비용 때문에 물리 분리를 미뤘다"이지 "DB-per-service 를 검증했다"와 같은 문장이 아니다.

덤으로 하나 더 나왔다. 코드에는 있는 `lemuel_card`, `lemuel_insurance`, `lemuel_deposit` 이 **프로덕션에 없다.** 만들어 두고 배포하지 않은 도메인이 있다는 뜻이다.

**판정: Kafka·Outbox 확인됨, 프로젝션 부분 확인, DB-per-service 는 논리만 참.**

---

## 3. "운영까지 책임" — 확인됨, 단 백업 성공률은 79%

> k3s·Argo CD·Helm·Prometheus/Grafana·ELK·Velero 기반 운영 자동화

이건 클러스터에 직접 물어봤다.

| 축              | 실측                                                              |
| --------------- | ----------------------------------------------------------------- |
| settlement-prod | Deployment 22, 실행 중 Pod 28, CronJob 2                          |
| Argo CD         | Application **59개** — Synced+Healthy 57, OutOfSync(단 Healthy) 2 |
| 모니터링        | `monitoring` 네임스페이스 Pod 13                                  |
| 로깅            | `logging` Pod 11 (+ `elastic-system`)                             |
| 백업            | Velero Pod 7, 스케줄 2개 모두 Enabled                             |

Velero 스케줄은 `hourly-critical`(`0 */4 * * *`, 97일째)과 `daily-with-volumes`(`0 3 * * *`, 99일째)다. 마지막 백업이 각각 19분 전, 9시간 전이었다. **자동화가 실제로 돌고 있다**는 건 이 두 줄로 확인된다.

다만 백업 73건의 상태를 다 세 보면 이렇다.

```
Completed        58
PartiallyFailed  14
Failed            1
```

완전 성공은 79%다. `PartiallyFailed` 는 백업 프로세스 자체는 끝났지만 개별 항목에서 오류가 있었던 상태로 남는다.[^velero] 원인별로 파고들지는 않았으므로 여기서는 "돌긴 도는데 5건 중 1건은 깨끗하지 않다"까지만 말하겠다. **백업은 복원해 보기 전까지 백업이 아니다**, 라는 오래된 말이 정확히 이 지점을 겨냥한다. 스케줄이 Enabled 인 것과 복구가 되는 것은 다른 명제다.

Argo CD 쪽 OutOfSync 2건은 Healthy 상태이므로 서비스 영향은 없지만, 선언한 상태와 실제 상태가 갈라져 있다는 신호[^argocd]인 건 맞다.

**판정: 확인됨. 단 "자동화가 있다"와 "자동화가 건강하다"는 다르고, 이 표는 앞쪽만 주장하고 있다.**

---

## 4. "AI 활용과 통제" — 통제는 확인, "Loop·Graph"는 근거를 못 찾았다

> Subagent·Loop·Graph 기반 작업 분해와 테스트·정적 분석·아키텍처 기준 검증

뒷문장부터 보자. **검증 장치는 실재하고, 실행된다.**

- ArchUnit: **17개 모듈 전부**에 아키텍처 테스트가 있다(파일 35개). 도메인의 Spring 의존 금지, application 레이어의 JPA 직접 사용 금지, adapter 간 cross-domain 의존 금지 — 이런 규칙은 리뷰어의 기억이 아니라 컴파일 단계에서 강제돼야 의미가 있다.[^archunit]
- CI 워크플로 8개. 그중 `semgrep.yml` 은 `--config p/default --config p/secrets` 로 정적 분석과 비밀값 스캔을 함께 건다.
- 하네스 자체의 셀프 테스트를 직접 돌려 봤다.

```
$ node --test scripts/harness/test/*.test.mjs
# tests 235
# pass  235
# fail  0
# duration_ms 267xxx
```

235개 전부 통과, 4분 27초. **에이전트를 검사하는 코드가 스스로 테스트를 갖고 있다**는 게 이 항목에서 가장 단단한 부분이다. 도구를 만들어 쓰는 사람은 많지만 그 도구에 테스트를 붙이는 경우는 드물다.

앞문장은 상황이 다르다. Subagent 는 확실하다 — 서브에이전트 9종, 스킬 37개, 커맨드 29개가 정의돼 있다. 그런데 **"Loop"와 "Graph"에 해당하는 구조는 리포지토리에서 직접적인 근거를 찾지 못했다.** grep 으로 잡힌 `subgraph` 는 README 의 mermaid 다이어그램 문법이었다. 요구사항 인터뷰 루프처럼 반복 구조로 볼 만한 문서 서술은 있지만, "Loop·Graph 기반 작업 분해"라고 나란히 쓸 만큼 코드로 구현된 실체는 확인되지 않았다.

**판정: "Subagent 기반 작업 분해와 테스트·정적 분석·아키텍처 기준 검증"까지는 전부 참. "Loop·Graph"는 표현이 근거보다 앞서 있다.**

---

## 대조 결과

| 표의 주장                         | 판정      | 근거                                                             |
| --------------------------------- | --------- | ---------------------------------------------------------------- |
| 정합성 중심 백엔드                | ✅ 확인됨 | 3겹 멱등성, 낙관/비관 락 병용, 원장 append-only, 대사 전용 모듈  |
| Kafka·Outbox                      | ✅ 확인됨 | 컨슈머 61, outbox 보유 서비스 13, envelope 규격 통일             |
| 프로젝션                          | 🟡 부분   | 읽기 모델은 있으나 전면 적용 아님                                |
| DB-per-service                    | 🟡 논리만 | 12 DB, **인스턴스 1개** — 스키마 결합은 끊었고 장애 격리는 못 함 |
| 운영까지 책임                     | ✅ 확인됨 | Argo CD 59앱, Velero 2스케줄 상시 가동, 모니터링·로깅 스택       |
| — 백업 건강도                     | 🟡 79%    | PartiallyFailed 14 / Failed 1                                    |
| AI 통제(테스트·정적분석·ArchUnit) | ✅ 확인됨 | ArchUnit 17/17, semgrep 2룰셋, 하네스 셀프테스트 235/235         |
| AI 활용(Loop·Graph)               | ❌ 미확인 | 리포 내 대응 구현 없음                                           |

여덟 줄 중 다섯이 참, 둘이 절반, 하나가 미확인이다.

## 그래서 표를 어떻게 고칠 것인가

대조의 목적은 점수가 아니라 문장 수정이다. 세 군데를 고치겠다.

1. **"DB-per-service"** → **"서비스별 DB 분리(논리) — 단일 인스턴스 12 DB"**. 물리 분리는 아직 안 했으니 안 했다고 쓰는 게 낫다. 면접에서 "인스턴스는 몇 개죠?" 한 마디에 무너지는 문장을 이력서에 둘 이유가 없다.
2. **"Loop·Graph"** → 뺀다. 근거가 생기면 그때 다시 넣는다.
3. **"운영 자동화"** → 여기에 **백업 복원 리허설**을 붙인다. 79%는 지금 상태의 정직한 숫자이고, 이걸 올리는 게 다음 작업이다.

반대로, 고칠 필요가 없다고 확인된 문장도 있다. 3겹 멱등성과 ArchUnit 17/17, 하네스 셀프테스트 235건은 숫자로 그대로 말할 수 있다. **검증을 거친 문장만 남기면 표는 짧아지지만 반박이 어려워진다.**

---

## 남은 한계

이 글은 정적 분석과 클러스터 조회로만 만들어졌다. 부하 테스트를 돌리지 않았으므로 성능에 대해서는 아무 주장도 하지 않는다. Velero 백업으로 실제 복원을 시도해 보지 않았으므로 "복구 가능"이라고도 쓰지 않았다. `PartiallyFailed` 14건의 개별 원인, 프로젝션의 적용 범위, OutOfSync 2건의 정체는 이 대조에서 열지 않은 상자다.

측정하지 않은 것을 측정한 것처럼 쓰지 않는 것 — 그게 정합성을 다루는 사람이 자기 이력서에 먼저 적용해야 할 규칙이라고 생각한다.

---

## References

[^kafka]: Apache Kafka, _Kafka Documentation — Message Delivery Semantics_. 프로듀서/컨슈머 기본 보장이 at-least-once 이며 중복 전달이 발생할 수 있음을 규정한다. <https://kafka.apache.org/documentation/#semantics>

[^outbox]: Chris Richardson, _Pattern: Transactional outbox_, microservices.io. 패턴 명명자 본인의 카탈로그. 데이터 변경과 메시지 발행을 하나의 로컬 트랜잭션으로 묶는 구조를 정의한다. <https://microservices.io/patterns/data/transactional-outbox.html>

[^dbps]: Chris Richardson, _Pattern: Database per service_, microservices.io. 서비스별 데이터 소유와 그로 인한 결합 제거를 다룬다. <https://microservices.io/patterns/data/database-per-service.html>

[^velero]: Velero, _Backup API Type_ (`status.phase` 필드). 백업 상태값의 정의 위치. <https://velero.io/docs/main/api-types/backup/>

[^argocd]: Argo CD, _Resource Health_ / Application sync status 문서. OutOfSync 와 Healthy 가 독립적인 축임을 설명한다. <https://argo-cd.readthedocs.io/en/stable/operator-manual/health/>

[^archunit]: ArchUnit, _User Guide_. 아키텍처 규칙을 단위 테스트로 강제하는 방식. <https://www.archunit.org/userguide/html/000_Index.html>
