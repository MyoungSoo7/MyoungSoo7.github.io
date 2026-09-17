---
layout: post
title: "DataGrip vs DbVisualizer 14 Pro — 데이터 마이그레이션 관점의 비교"
date: 2026-09-17 19:25:00 +0900
categories: [database, tooling]
tags: [DataGrip, DbVisualizer, 데이터마이그레이션, DB클라이언트, JetBrains, 라이선스]
---

DataGrip(JetBrains)과 DbVisualizer Pro 는 둘 다 "유료 범용 DB 클라이언트" 로 묶이지만, 데이터를 A 데이터베이스에서 B 데이터베이스로 옮기는 **마이그레이션 작업**을 기준으로 보면 설계 철학이 갈린다. DataGrip 은 **커넥션 간 직접 복사**를, DbVisualizer 는 **파일·스크립트 경유의 반복 가능한 이관**을 밀었다. 이 차이가 실무에서 어떤 선택으로 이어지는지, 공식 문서만으로 따져 본다.

먼저 버전 팩트 하나 — **DbVisualizer 14 는 2022-09-20 릴리스**이고 마지막 패치 14.0.4 는 2023-03-16 이다. 현재 최신은 26.x 대이며, 지금 Pro 구독을 사면 받는 건 14 가 아니라 최신 버전이다[^dbvis-versions]. 이 글은 요청대로 14 를 축으로 보되, 14 이후 달라진 지점은 그때마다 표시한다.

## 1. 라이선스 모델 — "구독 + 영구 사용권" 이라는 같은 뼈대, 다른 값

**DbVisualizer Pro** 는 구독형이지만 모든 구독에 **영구 사용권(perpetual usage license — buy once, use forever)** 이 포함된다. 공식 가격은 1인 기준 첫해 $199, 이듬해부터 갱신 $89 (VAT 별도), 프리미엄 지원 포함 티어는 $229/$119 다[^dbvis-pricing]. 갱신을 끊어도 구독 기간에 받은 버전은 계속 쓸 수 있다. 그리고 **Free 에디션이 별도로 존재**한다 — 다만 뒤에서 보듯 마이그레이션 핵심 기능은 전부 Pro 전용이다.

**DataGrip** 도 구독형이고, JetBrains 구독에는 **perpetual fallback license** 가 포함된다 — 활성 구독이 끝나도 특정 버전을 무기한 쓸 수 있고, 새 버전으로 올리려면 구독을 갱신해야 한다[^jb-fallback]. 뼈대는 DbVis 와 같다. 가격 숫자는 근거의 한계에 적은 이유로 이 글에 싣지 않는다.

## 2. DataGrip 의 마이그레이션 — 커넥션에서 커넥션으로 직접

DataGrip 마이그레이션의 간판은 **Copy Table to (F5)** 다. 테이블을 다른 스키마·다른 데이터 소스로 끌어다 놓으면 Import 대화상자가 열리고, 공식 문서가 드는 예시가 바로 이기종 이관이다 — *"예를 들어 `actor` 테이블을 MySQL 에서 PostgreSQL 로 복사할 수 있다"*[^dg-explorer]. 파일을 거치지 않고 **라이브 커넥션 간 직접 파이프**로 옮긴다.

이 Import 대화상자가 마이그레이션 콘솔 역할을 한다: 테이블-투-테이블 매핑 트리에서 대상 스키마를 **다른 데이터 소스**로 선택할 수 있고, 컬럼별 형변환 설정과 "변환 불가 값은 NULL 로 삽입" 옵션, DDL 미리보기까지 제공한다[^dg-import]. 보조 수단도 층층이 있다:

- **파일 경유**: CSV·TSV 등 구분자 파일 임포트, Export Data to File(SQL INSERT·TSV·JSON 등)[^dg-explorer]. 내보내기는 TXT·CSV·JSON·XML·Markdown·Excel 을 지원하고 **데이터 extractor 를 직접 만들 수도** 있다[^dg-export].
- **네이티브 덤프 통합**: PostgreSQL·MySQL 은 **mysqldump / pg_dump 를 IDE 안에서** 돌려 전체 구조+데이터 덤프를 뜬다[^dg-export]. 대용량에서 GUI 복사 대신 검증된 네이티브 경로를 쓰라는 설계다.
- **구조 비교**: 두 객체의 구조를 비교해 차이를 Diff 뷰어로 보여 주는 Migration 대화상자가 있어, 이관 전후 스키마 검증에 쓸 수 있다[^dg-explorer].

강점은 명확하다 — **일회성·대화형 이관이 압도적으로 빠르다.** 개발 DB 의 테이블 몇 개를 스테이징으로 옮기는 류의 작업은 드래그 한 번이다. 약점은 이 과정이 GUI 조작이라는 것: 같은 이관을 매주 반복하거나 기록으로 남기려면 IDE 밖(덤프 스크립트 등)으로 나가야 한다.

## 3. DbVisualizer Pro 의 마이그레이션 — 파일과 스크립트로, 반복 가능하게

DbVisualizer 의 문서화된 이관 경로는 **내보내기 → 들여오기** 다. 그리고 그 양 끝이 전부 **Pro 전용**이다[^dbvis-featlist]:

- **Export Schema / Export Table**: 스키마 전체 또는 선택 객체를 CSV·HTML·SQL·TXT·XML·XLS(X)·JSON 으로 내보낸다. SQL·XML 은 DDL+데이터를 함께 담을 수 있다[^dbvis-exp]. DbVis 14 에서 TXT 고정폭 형식이 Export Table/Schema/@export 로 확장됐다[^dbvis-14].
- **Import Table Data**: CSV·Excel 을 기존 테이블 또는 **새 테이블 생성**으로 들여오고, 컬럼 자동 매핑·데이터 타입 자동 감지를 지원한다[^dbvis-imp].
- **이기종 함정을 문서가 직접 다룬다**: Oracle 에서 SQL 로 내보내 PostgreSQL 에서 실행할 때 날짜·시간 리터럴 형식이 다른 문제를, **JDBC escape format** 으로 내보내 드라이버가 대상 DB 형식으로 변환하게 하라고 명시한다[^dbvis-exp]. 이기종 이관을 해 본 사람이 쓴 문서라는 티가 나는 대목이다.

그리고 DbVis 의 진짜 차별점은 **@export / @import 클라이언트 사이드 명령**이다. 임포트를 GUI 없이 `@import set ImportSource=... ; @import parse; @import target Table=...; @import execute;` 스크립트로 정의해 **명령줄 인터페이스(CLI)로 자동화**할 수 있고, dry run 으로 사전 검증하며, 실패한 행은 error record 파일로 떨어져 **고친 뒤 그 파일만 이어서 재실행**할 수 있다[^dbvis-import-cmd]. 매달 도는 정기 이관, 감사 추적이 필요한 이관이라면 — **반복 가능한 이관 스크립트는 DbVisualizer 쪽 손을 들어 준다.** 14 시절에도 이 축은 있었고(배치 임포트가 14 에서 기본값이 됐다[^dbvis-14]), MySQL 계열엔 서버 로컬 파일 고속 적재(LOAD DATA) 통합도 있다[^dbvis-imp].

약점도 대칭이다: DataGrip 의 Copy Table to 같은 **라이브 커넥션 간 직접 테이블 복사는 문서화된 경로가 아니다** — 이관은 원칙적으로 파일(또는 스크립트)을 거친다. 클릭 몇 번으로 끝날 일이 단계 몇 개가 된다.

## 4. 관점별 정리

| 관점 | DataGrip | DbVisualizer Pro (14 계열) |
| --- | --- | --- |
| 일회성 이기종 테이블 이관 | ◎ 커넥션 간 직접 복사 (MySQL→PostgreSQL 예시가 공식 문서에)[^dg-explorer] | △ Export → Import 단계 경유 |
| 반복·자동화 이관 | △ GUI 중심, 자동화는 네이티브 덤프로 우회 | ◎ @export/@import + CLI, dry run, 실패분 이어하기[^dbvis-import-cmd] |
| 대용량 | mysqldump/pg_dump IDE 통합[^dg-export] | MySQL 계열 LOAD DATA 통합[^dbvis-imp] |
| 이기종 타입 함정 대응 | 변환 불가 값 NULL 옵션·매핑별 형변환[^dg-import] | JDBC escape format 문서화[^dbvis-exp] |
| 스키마 구조 검증 | Migration 대화상자 + Diff 뷰어[^dg-explorer] | Export Schema 로 DDL 추출 비교[^dbvis-exp] |
| 무료 진입로 | 없음 (구독제) | Free 에디션 존재 — 단 이관 기능은 Pro 전용[^dbvis-featlist] |
| 구독 종료 후 | perpetual fallback license[^jb-fallback] | 영구 사용권 (buy once, use forever)[^dbvis-pricing] |

한 줄 요약 — **"지금 이 테이블을 저쪽 DB 로" 가 잦으면 DataGrip, "이 이관을 다음 달에도 똑같이, 기록 남기며" 가 잦으면 DbVisualizer Pro 다.** 그리고 DbVis 를 고른다면 14 가 아니라 현행 버전을 받게 된다는 것, 어느 쪽이든 마이그레이션 기능은 무료 티어 밖(Pro 전용/유료 제품)에 있다는 것이 구매 판단의 상수다.

---

## 근거의 한계

- **DataGrip 가격 숫자를 싣지 않았다.** JetBrains 구매 페이지는 스크립트 렌더링이라 텍스트로 금액을 검증할 수 없었다. 라이선스 구조(구독 + perpetual fallback)만 세일즈 FAQ 원문으로 확인했다.
- DbVisualizer 세부 기능 인용(Export Schema·Import 마법사·@import)은 현행 문서(24.x~26.x) 기준이다. 14 의 존재 여부는 14 what's new·릴리스 노트로 교차 확인했지만, 화면·옵션 세부는 14 와 다를 수 있다.
- 두 도구의 이관 속도·안정성 헤드투헤드 벤치마크는 중립 출처를 찾지 못해 싣지 않았다. 이 글의 비교 축은 성능이 아니라 **문서화된 기능의 유무와 설계**다.
- "DbVis 에 커넥션 간 직접 테이블 복사가 없다" 는 공식 문서에서 해당 기능을 확인하지 못했다는 뜻이다 — 부재의 증명은 아니다.

## References

[^dbvis-versions]: DbVisualizer 공식 — [Versions](https://www.dbvis.com/version-list/) (14.0 2022-09-20, 14.0.4 2023-03-16, 최신 26.2.2)
[^dbvis-pricing]: DbVisualizer 공식 — [Pricing](https://www.dbvis.com/pricing/) (Pro $199/첫해·$89/갱신 VAT 별도, perpetual usage license, Free 에디션)
[^jb-fallback]: JetBrains 세일즈 FAQ — [What is a perpetual fallback license](https://sales.jetbrains.com/hc/en-gb/articles/207240845-What-is-a-perpetual-fallback-license) (구독 종료 후에도 해당 버전 무기한 사용)
[^dg-explorer]: DataGrip 공식 문서 — [Database Explorer](https://www.jetbrains.com/help/datagrip/database-explorer.html) (Copy Table to F5, "MySQL 에서 PostgreSQL 로", Export Data to File, Migration 대화상자)
[^dg-import]: DataGrip 공식 문서 — [Import](https://www.jetbrains.com/help/datagrip/import-data.html) (Import 대화상자 매핑 트리, 다른 데이터 소스의 스키마 선택, inconvertible→NULL)
[^dg-export]: DataGrip 공식 문서 — [Export](https://www.jetbrains.com/help/datagrip/export-data.html) (data extractor, TXT/CSV/JSON/XML/Markdown/Excel, mysqldump·pg_dump 전체 덤프)
[^dbvis-exp]: DbVisualizer 공식 가이드 — [Exporting a Schema](https://www.dbvis.com/docs/26.1/working-with-schemas/exporting-a-schema/) (Pro 전용, 출력 형식, JDBC escape format 으로 이기종 날짜 리터럴 대응)
[^dbvis-imp]: DbVisualizer 공식 가이드 — [Importing Table Data](https://www.dbvis.com/docs/24.3/working-with-tables/importing-table-data/) (Pro 전용, CSV/Excel, 자동 매핑, 새 테이블 생성, LOAD DATA)
[^dbvis-import-cmd]: DbVisualizer 공식 가이드 — [@import — Importing data](https://www.dbvis.com/docs/25.3/working-with-sql/using-client-side-commands/import-importing-data/) (Pro 전용, CLI 자동화, dry run, errorRecords 이어하기)
[^dbvis-14]: DbVisualizer 공식 — [What's New in 14.0](https://www.dbvis.com/whatsnew/14.0/) (2022-09-20 릴리스, TXT 고정폭 확장, 배치 임포트 기본값, 신규 데이터 소스 4종)
[^dbvis-featlist]: DbVisualizer 공식 — [Feature list](https://www.dbvis.com/features/feature-list/) (Export Schema·Table Data Import 는 Pro 전용, Free 는 불가)
