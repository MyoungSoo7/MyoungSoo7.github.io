---
layout: post
title: "서비스 18개를 6개로 접으며 센 것, 세지 못한 것 — 계약 목록에 없던 소비자 둘"
date: 2026-10-27 22:51:13 +0900
categories: [Architecture, Settlement]
tags: [settlement, microservices, adr, postgres-fdw, hyrums-law, consolidation]
---

정산 플랫폼(settlement)은 한때 **서비스 18개 + 게이트웨이**였습니다. 8월 18일부터 9월 말까지 ADR 열 개(0037~0046)를 쓰면서 이 숫자를 줄였고, 9월 24일 옛 서비스 여섯 개를 클러스터에서 지웠습니다. 그 뒤 한 달 동안은 조용했습니다.

그런데 오늘(10/27) 확인해 보니, 이 조용함은 **33일 동안 아무도 몰랐던 고장**이었습니다. 분석용 DB가 9월에 멈춘 옛 DB를 매일 새벽 "성공"이라고 기록하며 읽고 있었습니다.

이 글은 통합 캠페인이 **무엇을 셌는지**와 **무엇을 세지 못했는지**를 다룹니다. 한 달 회고(돈 버그·조용한 실패·CI)는 [앞 글]({% post_url 2026-10-26-settlement-one-month-0926-1026 %})에 있으니, 여기서는 "합치기"라는 결정 하나만 끝까지 따라가 보겠습니다.

## 1. 왜 18개였나 — 그리고 왜 그 질문에 답을 못 했나

18개라는 숫자에는 근거가 없었습니다. 처음에는 데이터 단위(재무·경제·시장·공통데이터…)마다 서비스 하나씩을 만들었습니다. 그러다 보니 "왜 18개인가?"라는 질문에 아무도 즉답을 하지 못했습니다.

ADR 0037(8/18)은 사후에 판정 규칙을 세운 문서입니다. 서비스를 나누는 사유를 **6축**으로 정리했습니다.

| 축 | 질문 |
| --- | --- |
| ① 정합성 | 트랜잭션 경계가 달라야 하는가 |
| ② 규제 | 감사·통제 경계인가 |
| ③ 장애 격리 | 같이 죽으면 안 되는가 |
| ④ 배포 주기 | 따로 배포해야 하는가 |
| ⑤ 팀 인지부하 | 한 팀이 감당 가능한가 |
| ⑥ 데이터 오너십 | 데이터의 단일 진실원이 어디인가 |

판정 규칙은 한 줄입니다.

> 최소 2축 이상 강하게 걸려야 별도 서비스로 정당화한다.

이 규칙은 Martin Fowler의 [MonolithFirst](https://martinfowler.com/bliki/MonolithFirst.html)가 경고한 지점과 정확히 겹칩니다. Fowler는 서비스 경계를 처음부터 맞히기 어렵고, 경계를 옮기는 리팩터링이 서비스 사이에서는 모놀리스 안에서보다 훨씬 힘들다고 말합니다. 그래서 이렇게 썼습니다.

> "even experienced architects working in familiar domains have great difficulty getting boundaries right at the beginning."
> — Martin Fowler, *MonolithFirst* (2015)

우리는 경계를 먼저 긋고 이유는 나중에 찾은 셈입니다. 그래서 0037 이후의 ADR은 모두 "이 경계는 2축을 넘는가?"를 실측으로 검사하는 문서가 됐습니다.

## 2. 접기의 기록 — ADR 0038~0046

| ADR | 결정 | 근거로 잰 것 |
| --- | --- | --- |
| 0038 | 재무·경제·시장·공통데이터 4개 → `external-data-service`(DB `lemuel_external`) | 넷 사이 Outbox·Kafka·계약 자산 **0건**, 같은 모양 클래스 **12계열 × 4벌 ≈ 48파일** |
| 0039 | finance 6개 → 코어/주변 | 5개 서비스 사이 이벤트 간선 **0개** |
| 0040 | ai → settlement 흡수 | 격리는 프로세스 분리가 아니라 트랜잭션 경계·가상 스레드·레이트리밋에서 나온다 |
| 0041 | notification(Kotlin) → operation | — |
| 0042 | organization → order | "관리 화면은 UI 표면이지 컨텍스트 경계가 아니다"(operation 안 기각) |
| 0043 | board·education → operation | operation 의 성격이 "플랫폼 운영 서비스"로 바뀜 |
| 0044 | company 3분할(원천 → external-data, 판정 → finance) | — |
| 0045 | finance 의 동기 GET 제거 → 로컬 스냅샷 | 폴백이 장애를 **판정으로 둔갑**시킴 |
| 0046 | external-data 는 **분리 유지** | 소비자가 finance 하나라는 전제가 틀림 |

두 가지가 눈에 띕니다.

**첫째, 0037은 C그룹 통합을 한 번 거절했습니다.** "개별 배치 SLA·쿼터 격리라는 실제 기술적 사유"가 이유였습니다. 엿새 뒤 0038이 이 판단을 뒤집었습니다. 배치 시간이 실제로 겹치는지 재 보니 겹치지 않았고, 소비자는 모두 공개 GET 동기 호출뿐이었습니다. 처음 판단은 "그럴 것 같다"에서 나왔고, 뒤집은 판단은 측정에서 나왔습니다.

**둘째, 0045는 합치기가 아니라 결합을 끊는 결정이었습니다.** 기준금리 조회가 실패하면 설정값 **3.5%**로 폴백했고, 재무자료 조회가 비면 사실상 **대출 거절**이 됐습니다. 상류 서비스가 죽으면 심사 결과가 바뀐 겁니다. 반환값만 봐서는 이게 진짜 결과인지 장애인지 구분할 수 없습니다. 0045는 이 동기 호출을 로컬 스냅샷으로 바꿔, 실패가 "3.5%로 진행" 대신 **503**이 되게 했습니다.

> 가용성을 잃는 대신 틀린 금리로 진행하지 않는다.

돈을 다루는 시스템이라면 이 거래는 언제나 할 만합니다.

## 3. 무엇을 셌나 — "계약 자산"

이 캠페인의 측정 단위는 일관되게 **계약 자산**이었습니다. Outbox 테이블, Kafka 토픽(SPEC 기준 서비스 간 토픽 57개), 이벤트 스키마, REST 클라이언트가 여기에 들어갑니다.

0038의 결론도 이 단위로 적혀 있습니다.

> 계약 자산 손실 0, 소비자 코드 변경 0.

경로 접두사(`/api/financial/**` 등)를 그대로 두었기 때문에, 소비자 쪽은 base-url만 바꾸면 됐습니다. 이 말은 사실이었습니다. **레포 안에서는요.**

## 4. 세지 못한 것 ① — 프론트엔드

ADR 0046(external-data 분리 유지)은 0045의 전제를 바로잡는 문서입니다. 0045까지는 external-data의 소비자를 finance 하나로 봤습니다. 실제로 세어 보니 결과는 이랬습니다.

| 소비자 | 경로 | 규모 |
| --- | --- | --- |
| 프론트엔드 API | `frontend/src/api/{company,economics,financial,market}.ts` | **33개 함수** |
| 프론트 화면 | CeoInsightPage · CeoInvestPage · CompanyLookupPage · LiveQuoteTicker 등 | **8개** |

브라우저가 직접 부르는 소비자는 백엔드 계약 목록(토픽·Outbox·Feign 클라이언트)에 잡히지 않습니다. 같은 레포 안에 있었는데도 "소비자 = 다른 백엔드 서비스"라는 틀 때문에 보이지 않았습니다.

## 5. 세지 못한 것 ② — DB 레벨 소비자, 33일

두 번째는 레포 밖에 있었습니다.

분석용 `analytics` DB는 [postgres_fdw](https://www.postgresql.org/docs/17/postgres-fdw.html)로 운영 DB를 원격 테이블처럼 읽습니다. FDW는 `CREATE SERVER ... OPTIONS (host, port, dbname)`으로 상대 DB를 **이름으로** 가리킵니다. n8n이 매일 새벽 `CALL _meta.run_etl();` 한 줄을 실행해 그 원격 테이블을 분석 스키마로 복사합니다.

통합 이후 이 FDW 서버 두 개는 여전히 옛 DB를 가리키고 있었습니다.

```sql
-- helm-deploy charts/analytics/sql/00_fdw_setup.sql (수정 전)
OPTIONS (host 'jen-postgres.jen-prod.svc.cluster.local', port '5432', dbname 'lemuel_financial');
OPTIONS (host 'jen-postgres.jen-prod.svc.cluster.local', port '5432', dbname 'lemuel_economics');
```

옛 서비스를 지울 때 **옛 DB는 지우지 않았습니다**. 롤백할 때 쓰려고 남겨 둔 것이고, 잘한 결정이었습니다. 그런데 바로 그 신중함 때문에 고장이 조용해졌습니다.

- DB가 살아 있으니 FDW 연결은 성공합니다.
- 테이블과 컬럼도 그대로이니 쿼리도 성공합니다.
- 새 행은 없지만 0행 복사도 에러는 아닙니다.
- 그래서 `etl_runs`에는 매일 **success**가 찍혔습니다.

멈춘 것은 워터마크뿐이었습니다. 재무는 9/19, 경제는 9/23에서 더 나아가지 않았습니다. 옛 서비스가 쓰기를 멈춘 날짜입니다. 9/24 철거부터 10/27 발견까지 **약 33일** 동안, 분석 대시보드는 한 달 전 세상을 보여 주면서 초록불을 켜고 있었습니다.

고친 것은 두 줄입니다(`dbname` → `lemuel_external`, helm-deploy `861db5a`). 바꾸기 전에 두 가지를 확인했습니다. 새 DB 컬럼이 옛 DB 컬럼의 상위집합인지, upsert 키가 겹치는 행이 0건인지입니다. ETL을 다시 돌린 결과는 다음과 같습니다.

| 소스 | 워터마크 | 적재 |
| --- | --- | --- |
| 재무 | 9/19 → **10/24** | 9,809행 |
| 경제 | 9/23 → **10/26** | 2,559행 (지표 4종 → 11종) |

## 6. 왜 안 보였나 — Hyrum's Law 의 DB 버전

Hyrum Wright가 정리한 [Hyrum's Law](https://www.hyrumslaw.com/)는 이렇습니다.

> With a sufficient number of users of an API, it does not matter what you promise in the contract: all observable behaviors of your system will be depended on by somebody.

우리가 약속한 계약은 REST 경로와 Kafka 토픽이었습니다. 하지만 **DB 이름**도 바깥에서 관찰할 수 있는 동작입니다. 누군가 그 이름에 의존하고 있었고, 그 누군가는 레포에도 계약 목록에도 없었습니다. 의존은 헬름 차트 안의 SQL 파일 한 줄로만 존재했습니다.

교훈을 세 가지로 정리합니다.

1. **소비자 목록은 레포 grep 으로 완성되지 않는다.** 서비스를 합치거나 지우기 전에 반대쪽에서도 찾아봐야 합니다. 그 DB와 호스트 이름을 참조하는 모든 것을 인프라 레포·FDW·크론·대시보드까지 뒤집니다. 이번에 `grep -r lemuel_financial helm-deploy/`를 한 번만 돌렸어도 걸렸을 겁니다.
2. **롤백용으로 남긴 옛 DB는 '살아 있는 거짓말'이다.** 남기는 건 맞습니다. 다만 쓰기를 막는 데서 그치지 말고, 접속 자체를 거절하거나 **읽기만 해도 눈에 띄게** 만들어야 합니다. 연결이 실패해야 소비자가 비명을 지릅니다.
3. **ETL 의 '성공'은 행 수가 아니라 워터마크로 판정한다.** "에러 없이 끝남"은 "새 데이터가 들어옴"이 아닙니다. 워터마크가 N일 이상 멈추면 실패로 보는 규칙 하나면, 33일이 하루로 줄었을 겁니다.

## 7. 지금의 모양

통합 뒤의 런타임을 오늘 실측했습니다(`kubectl top`, settlement-prod).

| 파드 | 노드 | 메모리 |
| --- | --- | --- |
| settlement-elasticsearch | ilwon | 1,363Mi |
| finance | lemuel | 722Mi |
| query | lemuel | 619Mi |
| operation | lemuel | 553Mi |
| external-data | lemuel | 534Mi |
| settlement-app | lemuel | 500Mi |
| receipt-ocr · circuit-breaker · redis · frontend · market-stream | louise/lemuel | 각 43Mi 이하 |

DB(`jen-postgres`, 199Mi)와 Kafka(Strimzi, 1,006Mi)는 ilwon에 있습니다.

덤이 하나 있습니다. 오늘 저녁 전기를 아끼려고 solomon 노드를 클러스터에서 잠시 빼면서(cordon·drain 후 전원 차단), settlement-prod 앱 파드 11개 중 7개가 lemuel에 모였습니다. 예전에 solomon에 몰려 있던 쏠림이 노드만 바뀌어 그대로 옮겨 온 셈입니다. 서비스 수를 줄여도 **배치(placement)의 쏠림은 따로 관리해야 할 문제**로 남습니다.

## 맺으며

18개를 6개로 줄이는 동안 우리는 정직하게 셌습니다. 토픽 57개, 복제 파일 48개, 이벤트 간선 0개를 셌습니다. 하지만 이 숫자들은 모두 **우리가 계약이라고 부르기로 한 것**의 개수였습니다.

시스템은 그보다 넓게 관찰되고 있었습니다. 브라우저는 33개 함수로 경로를 붙잡고 있었고, 분석 DB는 이름 한 줄로 옛 데이터베이스를 붙잡고 있었습니다. 다음에 무언가를 지울 때 먼저 던질 질문은 "누가 이걸 쓰나"가 아닙니다. **"이걸 지웠을 때 누가 비명을 지르나, 그리고 그 비명이 들리게 되어 있나"**입니다.

---

## References

- Martin Fowler, ["MonolithFirst"](https://martinfowler.com/bliki/MonolithFirst.html), martinfowler.com, 2015-06-03.
- Hyrum Wright, ["Hyrum's Law"](https://www.hyrumslaw.com/).
- PostgreSQL Global Development Group, ["F.36. postgres_fdw"](https://www.postgresql.org/docs/17/postgres-fdw.html), PostgreSQL 17 Documentation.
- settlement 레포 ADR 0037~0046 (`docs/adr/`, 비공개 레포 — 인용은 원문 그대로).
- helm-deploy 커밋 `861db5a` — `charts/analytics/sql/00_fdw_setup.sql` FDW 대상 교체(비공개 레포).
