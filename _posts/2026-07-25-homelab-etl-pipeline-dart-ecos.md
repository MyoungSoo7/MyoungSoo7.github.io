---
layout: post
title: "21개 사일로 DB를 하나로 — Postgres만으로 만든 홈랩 ETL 파이프라인 (dart·ECOS 정규화)"
date: 2026-07-25 13:00:00 +0900
categories: [Data, Architecture]
tags: [ETL, DataWarehouse, Medallion, StarSchema, PostgreSQL, postgres_fdw, n8n, Grafana, GitOps, ArgoCD, Kimball]
---

# 홈랩에 데이터가 20개 넘게 흩어져 있었다

K3s 홈랩을 오래 굴리다 보니 서비스마다 자기 DB를 갖는 전형적인 MSA 사일로가 됐다. 클러스터를 실측해보니 **서비스별 PostgreSQL이 21개**, 거기에 MySQL·MinIO(오브젝트)·Kafka·Elasticsearch까지. 데이터는 다 있는데, 이걸 **가로질러 보는 통합 분석 계층이 없었다.** 기업 재무(전자공시 dart)와 거시 경제지표(한국은행 ECOS)가 각각 다른 DB에 살고 있으니, "연도별 기업 실적과 그때의 금리·환율을 같이 보고 싶다" 같은 단순한 질문에도 답할 데가 없었다.

그래서 분산된 소스를 연결·정규화하는 **ETL 파이프라인**을 만들었다. 클라우드 데이터 웨어하우스 없이, **가진 것(K3s + PostgreSQL + n8n + Grafana + ArgoCD)만으로.** 이 글은 그 설계와 실제 구축 기록이다.

## 설계 원칙 두 가지: Medallion + 별 모양

두 개의 잘 알려진 패턴을 뼈대로 삼았다.

**① Medallion 아키텍처** — 원천→정제→비즈니스의 3계층(Bronze/Silver/Gold)으로 데이터 품질을 점진적으로 끌어올리는 설계다. Databricks가 정식화한 용어로, "각 계층이 데이터 품질 단계를 나타낸다"고 규정한다(벤더 1차 정의).[^medallion]

**② Kimball 차원 모델(star schema)** — Silver/Gold에서 사실(fact) 테이블을 여러 차원(dimension) 테이블이 감싸는 별 모양. 여러 fact가 공유하는 **컨폼드 디멘전(conformed dimension)** 이 서로 다른 소스를 하나로 꿰는 표준 커넥터가 된다. Ralph Kimball이 1996년 『The Data Warehouse Toolkit』에서 제시한 방법론이다(1차 권위).[^kimball]

전체 그림은 이렇다:

```
 [소스: jen-postgres]            [analytics-postgres = 웨어하우스]
 lemuel_financial(dart) ─┐        ┌────────────────────────────────┐
   companies             │        │ Bronze  raw_dart / raw_ecos     │
   financial_statements  ├─FDW──▶ │   (원천 랜딩)                    │
 lemuel_economics(ECOS) ─┤        │      │                          │
   indicators            │        │ Silver norm.dim_company         │
   indicator_values      ┘        │        norm.dim_indicator       │
                                  │        norm.fact_financial_*    │
                                  │        norm.fact_economic_*     │
                                  │      │  (+ 파생지표)             │
                                  │ Gold  mart.company_financials   │
                                  │       mart.economic_timeseries  │
                                  │       mart.financial_vs_macro   │
                                  └───────────────┬────────────────┘
   n8n(매시 스케줄) ── CALL _meta.run_etl() ──────┘   Grafana 대시보드
```

핵심은 **이 전부를 평범한 PostgreSQL 하나(analytics-postgres) 위에 스키마로 구현**했다는 것이다. Bronze=`raw_*` 스키마, Silver=`norm` 스키마, Gold=`mart` 스키마.

## Phase 1 — 웨어하우스를 GitOps로 세운다

먼저 타깃 DB. 신규 `analytics-postgres`(StatefulSet)를 Helm 차트로 만들고 ArgoCD로 배포했다. 컨테이너 최초 기동 시 medallion 스키마와 운영 메타 테이블(`_meta.etl_runs` 실행로그, `_meta.watermarks` 증분커서)이 자동 생성되도록 init 스크립트를 넣었다. 비밀번호는 Kubernetes Secret으로 분리하고 **git에는 넣지 않았다** — 이 원칙은 끝까지 지켰다.

## Phase 2 — 정규화: 두 소스가 별 모양으로 합쳐진다

소스는 두 개로 좁혔다. 전자공시 재무(`lemuel_financial`: `companies`, `financial_statements`)와 한국은행 경제지표(`lemuel_economics`: `indicators`, `indicator_values`).

Silver 계층에서 컨폼드 디멘전과 fact로 정규화했다:

- `norm.dim_company` — 기업 마스터(corp_code 자연키 → 서로게이트키)
- `norm.dim_indicator` — 경제지표 마스터
- `norm.fact_financial_statement` — 기업 × 회계연도 × 재무구분. 여기서 **파생지표를 계산해 얹었다**: 영업이익률·순이익률·부채비율·ROE.
- `norm.fact_economic_indicator` — 지표 × 관측일

raw→norm 변환은 전부 `INSERT ... ON CONFLICT DO UPDATE`(멱등 upsert)로 짰다. 같은 데이터를 몇 번을 흘려도 결과가 같도록 — 재실행 안전성은 배치 파이프라인의 기본이다.

실제로 돌렸더니 파일럿 데이터가 이렇게 정규화됐다(실측):

| 계층 | 결과 |
|---|---|
| Bronze | companies 834 · financial_statements 3,229 · indicators 4 · indicator_values 2,202 |
| Silver | dim_company 834 · fact_financial_statement 3,229 · fact_economic_indicator 2,202 |
| Gold(예) | 삼성전자 2025 매출 333.6조 · 순이익 45.2조 · 영업이익률 13.1% · ROE 10.4% |
| Gold(지표) | 기준금리·CPI·국고채3년·원달러환율 시계열 |

> 위 수치는 이 홈랩의 실제 파일럿 DB에서 나온 값(본인 데이터, 재현 가능)이며, 특정 종목에 대한 투자 판단 근거가 아니다.

`mart.financial_vs_macro`는 두 소스를 잇는 크로스소스 뷰다 — 연도별 기업 총계(매출·순이익)와 그 해의 거시지표 평균을 같이 본다. 컨폼드 시간축이 미시(기업)와 거시(경제)를 하나의 마트에서 만나게 한다.

## Phase 3 — 자동화: "오케스트레이터가 데이터를 나르지 않게" 한다

여기가 이번 설계에서 제일 마음에 드는 부분이다.

처음엔 n8n의 Postgres 노드로 소스에서 행을 읽어 타깃에 넣는 그림을 생각했다. 그런데 그러면 **수천 행이 오케스트레이터를 통과**한다. 대신 PostgreSQL의 **postgres_fdw**(외래 데이터 래퍼)를 썼다. postgres_fdw는 원격 PostgreSQL의 테이블을 로컬처럼 `SELECT`할 수 있게 해주는 공식 확장으로, 설정은 `CREATE EXTENSION` → `CREATE SERVER` → `CREATE USER MAPPING` 순서다(공식 문서).[^fdw]

`analytics-postgres`에서 `jen-postgres`의 두 DB를 외래 서버로 걸고 외래 테이블로 임포트했다. 그러면 데이터 이동이 **DB 내부에서** 일어난다. ETL 전체를 단일 프로시저 `_meta.run_etl()`로 감쌌다:

```sql
CALL _meta.run_etl();
-- FDW로 원천 pull → Bronze 적재 → Silver 멱등 upsert(+파생지표)
--   → watermark 갱신 → _meta.etl_runs 로그. 예외 시 status='failed' 기록.
```

이제 **n8n이 할 일은 매시 정각에 이 프로시저를 호출하는 것 하나뿐**이다. 워크플로는 노드 두 개(Schedule Trigger → Postgres "CALL")로 끝난다. 오케스트레이터는 얇게, 데이터 중력은 DB 안에. 자격증명 한 개, 실패 지점 최소화.

검증도 대충 넘기지 않았다. 스케줄을 임시로 1분 주기로 바꿔 재시작하고, `_meta.etl_runs`에 자동 실행 레코드가 실제로 쌓이는지 확인한 뒤 다시 매시로 되돌렸다. "돌 것이다"가 아니라 "도는 걸 봤다".

## Phase 4 — 관측: 안 보이면 못 고친다

마지막은 Grafana. kube-prometheus-stack의 사이드카가 라벨(`grafana_dashboard=1` / `grafana_datasource=1`)이 붙은 리소스를 자동 로드하는 구조라, 대시보드는 라벨 ConfigMap(GitOps)로, 데이터소스는 비밀번호가 있으니 Secret으로 넣었다. 6개 패널 — 마지막 성공 시각, 최근 적재 행수, 정규화 행수, ETL 실행 이력, 매출 상위 기업, 경제지표 시계열. 데이터소스 헬스체크는 `Database Connection OK`.

`_meta.etl_runs`가 곧 관측의 심장이다. 매 실행이 시작/종료/행수/상태/에러로 남으니, 신선도(마지막 성공 이후 경과)와 실패를 대시보드가 바로 보여준다.

## 설계에서 지킨 것들

- **오케스트레이터는 얇게**: 데이터 이동은 postgres_fdw로 DB가, n8n은 트리거만.
- **멱등성**: 모든 적재가 upsert. 재실행·중복에 안전.
- **비밀은 코드에 없다**: DB·FDW·데이터소스 비번 전부 Secret. git엔 자리표시자만.
- **GitOps 단일 소스**: 스키마 SQL·n8n 워크플로·대시보드까지 전부 helm-deploy 레포에 버전관리, ArgoCD가 배포.
- **측정 가능한 완료 기준**: "정규화됨"이 아니라 "삼성전자 재무가 마트에 뜬다", "스케줄이 실제로 fire된다", "데이터소스가 연결된다"로 검증.

## 정직한 한계

파일럿이다. 과장하지 않기 위해 경계도 적는다.

- **소스 2개**(21개 중). 척추를 증명한 것이지 전면 통합이 아니다. 나머지는 같은 템플릿으로 확장하는 일이 남았다.
- **현재는 full-refresh**. watermark 컬럼(`synced_at`)과 `_meta.watermarks`는 넣어뒀지만, 실제 증분 append는 아직 아니다. 파일럿 데이터가 작아(수천 행) full-refresh가 더 단순·안전했다. 데이터가 커지면 증분으로 전환해야 한다.
- **스키마 드리프트**: 소스 서비스가 독립 배포돼 컬럼이 예고 없이 바뀔 수 있다. 감지 로직은 아직 없다 — 프로덕션이라면 1일차부터 넣어야 할 항목.
- **PII**: 여러 도메인을 통합하면 개인정보가 섞일 수 있다. 이번 소스(공개 재무·거시지표)는 해당이 적지만, 소스를 넓히면 마스킹·접근분리 설계가 선행돼야 한다.

## 닫으며

거창한 도구 없이도, 잘 알려진 패턴 두 개(Medallion·Kimball)와 PostgreSQL의 기본기(FDW·멱등 upsert·스토어드 프로시저)만으로 분산 데이터를 연결·정규화하는 파이프라인이 선다. 요령은 하나다 — **오케스트레이터를 얇게 두고, 데이터가 있는 곳(DB) 가까이에서 일을 시키는 것.** 그리고 각 단계를 "될 것"이 아니라 "되는 것을 본" 상태로 남기는 것.

---

## References

- Databricks. *What is the medallion lakehouse architecture?* (공식 문서 — Bronze/Silver/Gold 정의). [docs.databricks.com/aws/en/lakehouse/medallion](https://docs.databricks.com/aws/en/lakehouse/medallion)
- Kimball Group. *Dimensional Modeling Techniques — Star Schema / Conformed Dimensions* (1차 권위, Ralph Kimball). [kimballgroup.com/.../dimensional-modeling-techniques](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/) · Kimball & Ross, *The Data Warehouse Toolkit* (3rd ed.)
- PostgreSQL Global Development Group. *postgres_fdw — access data stored in external PostgreSQL servers* (공식 문서). [postgresql.org/docs/current/postgres-fdw.html](https://www.postgresql.org/docs/current/postgres-fdw.html)
- n8n Docs — Schedule Trigger / Postgres node (공식 문서). [docs.n8n.io](https://docs.n8n.io/)

*출처 등급: Medallion은 Databricks 1차 정의, 차원 모델링은 Kimball 1차 권위, postgres_fdw/n8n은 공식 문서를 인용했다. 본문의 행수·재무 수치는 이 홈랩 파일럿 DB의 실측값(본인 데이터)이며 투자 조언이 아니다. 성능·규모에 대한 일반화 주장은 하지 않았다(파일럿 범위 명시).*
