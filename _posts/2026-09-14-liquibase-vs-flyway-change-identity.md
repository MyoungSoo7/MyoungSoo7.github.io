---
layout: post
title: "Liquibase와 Flyway — 장단점은 '변경의 정체성'을 무엇으로 잡느냐에서 갈린다"
date: 2026-09-14 19:18:32 +0900
categories: [Engineering, Database]
tags: [Liquibase, Flyway, 마이그레이션, 스키마관리, SpringBoot, 라이선스]
---

DB 마이그레이션 도구를 고를 때 흔히 비교표를 먼저 본다. XML 이냐 SQL 이냐, 롤백이 되냐 안 되냐, 멀티 DB 를 지원하냐. 그런데 그 표의 항목들은 대부분 **하나의 설계 선택에서 파생된 결과**다. 그 선택은 이것이다 — *하나의 변경을 무엇으로 식별할 것인가.*

- **Flyway**: 버전. 파일명에 박혀 있다. `V001.002__NewTwitterColumn.sql` 의 `001.002`.
- **Liquibase**: 세 값의 조합. 체인지셋의 `id`, `author`, 그리고 changelog **파일 경로**.

기호로 쓰면 Flyway 의 식별자는 $\text{version}$ 하나이고, Liquibase 는 $(\text{id},\ \text{author},\ \text{filename})$ 튜플이다. 이 차이가 순서·중복·롤백·충돌 양상을 전부 바꾼다. 아래 장단점은 그 축 위에서 정리한 것이다.

먼저 출처 원칙을 밝힌다. 기능·동작에 대한 사실 주장은 **양쪽 벤더의 공식 문서와 실제 저장소 파일**로 확인한 것만 적는다. 성능 우열은 **중립 제3자의 헤드투헤드 벤치마크를 찾지 못했으므로 아예 다루지 않는다.** 그리고 한 가지는 내 손으로 실측한 것이다 — 내 정산 서비스 저장소의 마이그레이션 305개와, 거기서 실제로 났던 사고.

## 1. Flyway: 파일명이 곧 순서이자 정체성

Flyway 의 모델은 단순하다. 버전 마이그레이션은 **버전 순서대로 정확히 한 번** 적용되고, `flyway_schema_history` 테이블이 무엇이 언제 누구에 의해 적용됐는지와 **체크섬**을 기록한다.[^fw-versioned] 파일명 구조는 `prefixVERSIONseparatorDESCRIPTIONsuffix` 이고 기본 prefix 는 `V` 다.[^fw-prefix]

체크섬은 "이미 적용된 스크립트가 나중에 수정되지 않았는가"를 잡기 위해 있다. `migrate` 를 돌릴 때 자동으로 검증되며, 어긋나면 배포가 아니라 **부팅이 실패**한다. Redgate 자신의 해설에 따르면 SQL 마이그레이션의 체크섬은 CRC32 이고, `validate` 는 (1) 적용된 파일이 사라졌는지, (2) 현재 버전보다 **낮은** 버전의 파일이 나중에 끼어들었는지, (3) 내용이 바뀌었는지를 본다.[^fw-validate] 의도적인 변경이라면 `repair` 로 이력 테이블을 갱신해야 한다.[^fw-history]

**장점.** 배울 것이 거의 없다. SQL 파일에 이름만 규칙대로 붙이면 끝이고, 실행되는 것이 내가 쓴 SQL 그대로다. DB 벤더 고유 문법(파티셔닝, `BRIN` 인덱스, 트리거)을 쓰는 데 제약이 없다. 리뷰어가 보는 diff 가 곧 DB 에 나갈 문장이다.

**단점.** 순서가 파일명에만 존재한다. 이게 다음 절의 사고로 이어진다.

## 2. 실측 — 305개의 마이그레이션, 그리고 git 이 못 잡은 충돌

내 정산 서비스는 Flyway 를 쓴다. 서비스별 `db/migration` 아래 버전 마이그레이션이 **305개**다(`order-service` 156, `settlement-service` 52, `finance-service` 42, `external-data-service` 33, `operation-service` 19). 버전은 `V20260716200200__payout_bank_account_encryption.sql` 처럼 **초 단위 타임스탬프**를 쓴다.

이건 우연이 아니라 Flyway 문서가 권하는 회피책이다. 문서는 "단순 증가 정수로 충분하지만, Flyway Desktop 은 기본적으로 타임스탬프를 버전에 넣는데 **두 명이 동시에 마이그레이션을 추가할 때의 충돌을 피하는 데 도움이 되기 때문**"이라고 적는다.[^fw-versioned] 즉 벤더도 이 지점이 약하다는 걸 안다.

그런데 타임스탬프도 완전하지 않다. 2026-08-27, 같은 저장소에 동시에 쓰는 두 봇 세션이 **같은 버전**을 만들었다.

```
봇1: V20260827110000__menu_return_requests.sql
봇4: V20260827110000__menu_education_enrollments.sql
```

**핵심은 이게 git 에서 충돌이 아니라는 점이다.** 파일명이 다르니 서로 다른 파일 추가일 뿐이다. 각자 브랜치에서 CI 초록불, `git rebase` 조용히 통과, 테스트도 통과한다(각자 자기 트리만 도니까). Flyway 는 버전 중복을 **스키마를 보기도 전에** 거부하므로, 합쳐진 main 이 배포되는 순간 애플리케이션 부팅 자체가 죽는다. 런타임까지 가서야 드러나는 종류의 결함이다.

Liquibase 였다면 어땠을까. 두 갈래로 갈린다.

- 루트 changelog 에서 `include` 로 하위 changelog 를 나열하는 구조라면, 두 세션이 **같은 파일의 같은 목록**을 고쳐야 한다. git 이 충돌로 잡는다. 문서상 `include` 는 "발견된 순서대로" 실행되므로 순서가 그 목록에 명시적으로 적혀 있다.[^lb-include]
- `includeAll` 로 디렉터리를 통째로 거는 구조라면 공유 파일 편집이 없으니 Flyway 와 같은 사각지대가 생긴다. 다만 실행 순서는 **알파벳 순**이고, 문서 자신이 "`includeAll` 을 쓴다면 충돌과 파일명 재정렬을 막기 위해 네이밍 전략을 강제하라"고 경고한다.[^lb-includeall] 그리고 이 경우에도 **부팅이 죽지는 않는다** — 체인지셋 식별자에 파일명이 포함되므로 `id` 가 같아도 파일이 다르면 서로 다른 변경이다.[^lb-dbcl]

정리하면 이건 "Liquibase 가 우월하다"가 아니라 **실패가 어디서 드러나느냐의 차이**다. Flyway 는 늦게, 크게, 확실하게 터진다. Liquibase 는 이르게 잡히거나(`include`), 조용히 둘 다 실행된다(`includeAll`). 어느 쪽이 나은지는 팀이 "조용한 통과"와 "요란한 실패" 중 무엇을 더 무서워하느냐에 달렸다.

## 3. Liquibase: 변경을 기술(記述)하고, 도구가 SQL 을 만든다

Liquibase 의 changelog 는 SQL·XML·YAML·JSON 으로 쓸 수 있고, 두 가지 모델이 있다.[^lb-changelog]

- **SQL 모델**(`.sql`): 주석으로 체인지셋을 구분하고 SQL 을 직접 쓴다.
- **플랫폼 독립 모델**(`.xml`/`.yaml`/`.json`): `createTable` 같은 **Change Type** 을 쓰면 Liquibase 가 DB 별 SQL 을 생성한다.[^lb-changetype]

추적 테이블은 둘이다. `DATABASECHANGELOG` 는 체인지셋별로 한 행을 남기며 `ID`/`AUTHOR`/`FILENAME` 조합이 유일하다. **기본키는 일부러 없다** — DB 마다 키 길이 제약이 달라서다.[^lb-dbcl] `DATABASECHANGELOGLOCK` 은 동시에 두 인스턴스가 돌지 못하게 막는 명시적 락 테이블로, "클러스터의 여러 서버가 기동 시 자동으로 Liquibase 를 돌리는" 상황을 문서가 대놓고 상정한다. 비정상 종료로 락이 남으면 `liquibase release-locks` 로 푼다.[^lb-lock]

또 하나 큰 차이는 **조건부 실행**이다. `contexts`, `labels`, `preconditions` 로 "어느 환경에서 어떤 체인지셋이 도는지"를 changelog 안에서 선언한다.[^lb-changelog]

**장점.** 변경이 데이터로 기술되므로 도구가 개입할 여지가 크다 — 자동 롤백 생성, DB 이식, 전제조건 검사. 여러 DB 벤더를 동시에 지원해야 하는 제품이라면 이 값은 크다.

**단점.** 추상화의 대가가 있다. XML 은 문서 자신도 "구체적이지만 장황하다(specific but verbose)"고 인정한다.[^lb-changelog] 그리고 벤더 고유 기능은 결국 `sql`/`sqlFile` Change Type 으로 원시 SQL 을 넣게 되는데, 그러면 추상화의 이득은 사라지고 래퍼만 남는다. 실제로 내 정산 저장소의 마이그레이션 상당수(파티셔닝, BRIN 인덱스, 트리거, 부분 유니크 인덱스)가 그 부류다.

## 4. 롤백 — 가장 오해가 많은 항목

"Liquibase 는 롤백이 되고 Flyway 는 안 된다"는 요약은 양쪽 다 틀렸다.

**Flyway 에는 undo 마이그레이션이 있다.** `V001__addCarTable.sql` 에 대응하는 `U001__undoAddCarTable.sql` 을 쓰고 `undo` 명령으로 실행한다. 단, 공식 문서 페이지 상단에 **`EDITION: TEAMS`** 가 박혀 있다 — 오픈소스 판의 기능이 아니다.[^fw-undo]

**그리고 Flyway 문서 스스로 undo 의 한계를 길게 적는다.** ① 스키마 변경엔 쓸 만하지만 데이터 변경엔 잘 안 맞는다(`DROP`/`DELETE`/`TRUNCATE` 를 되돌리려면 데이터를 복원해야 하는데 정적 데이터가 아니면 어렵다). ② undo 는 "마이그레이션 전체가 성공했고 이제 되돌린다"를 가정한다. DDL 트랜잭션이 없는 DB 에서 **10개 문장 중 7번째가 실패**한 경우엔 아무 도움이 안 된다. 문서가 대안으로 제시하는 것은 **DB 와 배포된 모든 코드 버전 사이의 하위 호환을 유지하고, 검증된 백업·복구 전략(가능하면 스토리지 스냅샷)을 갖추는 것**이다.[^fw-undo]

**Liquibase 의 롤백은 OSS 에서 쓸 수 있다** — 단 "명령행, Ant, Maven 에서 사용 가능"이라는 단서가 붙는다. `rollback`(태그 기준), `rollback-to-date`, `rollback-count` 세 가지가 기본이다. 다만 **`rollback-one-changeset`·`rollback-one-update` 처럼 '특정 하나만 되돌리기'는 Liquibase Secure 전용**이고, `--rollback-on-error` 도 Secure 4.18.0+ 기능이다.[^lb-rollback]

Liquibase 가 실질적으로 더 나은 지점은 **롤백을 검증할 수단**이 딸려온다는 것이다. `update-testing-rollback` 은 체인지셋을 배포하고 → 역순으로 롤백하고 → 다시 배포해 본다. `future-rollback-sql` 은 아직 배포되지 않은 변경을 되돌리는 SQL 을 미리 뽑아 준다(문서는 "감사자가 모든 변경에 롤백이 있는지 확인해야 할 때" 쓴다고 적는다).[^lb-rollback] 그리고 Liquibase 문서도 정직하다 — "롤백 스크립트는 애플리케이션 개발에서 가장 만들고 유지하기 어려운 것 중 하나이며, 특히 데이터가 바뀔 때 그렇다."[^lb-rollback]

**결론은 양쪽 문서가 같은 말을 한다.** 되돌리기의 실무적 정답은 도구의 롤백 명령이 아니라 **하위 호환 유지 + 앞으로 굴리기(roll forward) + 검증된 백업**이다. Flyway 문서의 권고가 정확히 그것이고, 그래서 Flyway 는 "이미 적용된 마이그레이션은 고치지 말고 새 버전을 만들어 앞으로 굴려라"를 베스트 프랙티스로 명시한다.[^fw-versioned]

## 5. 라이선스 — 2026년에 이 비교의 무게중심이 옮겨간 지점

이 항목은 최근에 **실제로 바뀌었고**, 검증이 쉬우니 정확히 적는다.

**Flyway 오픈소스는 Apache-2.0 이다.** `flyway/flyway` 저장소의 `LICENSE.md` 가 Apache License 2.0 이고 저작권 표기는 Red Gate Software Ltd 2010–2026 이다. Redgate 는 그 위에 Community/Teams/Enterprise 에디션을 별도로 판매하며, README 는 그 에디션들이 **"오픈소스 프로젝트의 일부가 아니다"** 라고 명시한다.[^fw-repo]

**Liquibase 는 2025년에 Apache-2.0 을 떠났다.** 2010-07-11 에 `nvoxland` 가 "changed license to APL" 로 아파치 라이선스를 채택했던 그 저장소에서, **2025-09-30 커밋 `c574abc`("chore: update LICENSE to Functional Source License, Version 1.1", PR #7317)** 로 **FSL-1.1-ALv2** 로 바뀌었다. 현재 README 도 "Liquibase Community 는 Functional Source License 로 라이선스된다"고 적는다.[^lb-license]

경계는 Maven Central 의 POM 으로 정확히 확인된다.

| 아티팩트 | POM 의 `<license><name>` |
| --- | --- |
| `liquibase-core:4.33.0` | Apache License, Version 2.0 |
| `liquibase-core:5.0.0` | Apache License, Version 2.0 |
| `liquibase-core:5.0.1` | **FSL-1.1-ALv2** |

즉 **5.0.0 까지는 Apache-2.0, 5.0.1 부터 FSL** 이다(2026-09-14 기준 최신은 `liquibase-core` 5.0.4, `flyway-core` 13.6.0).[^mvn]

FSL-1.1-ALv2 가 실제로 무엇을 제한하는지도 라이선스 전문에서 그대로 옮긴다. 허용 목적은 "Competing Use 가 아닌 모든 목적"이고, Competing Use 란 이 소프트웨어를 **대체하거나 실질적으로 동일한 기능을 제공하는 상업적 제품·서비스로 타인에게 제공하는 것**을 말한다. 명시적으로 허용되는 것에는 **내부 사용**, 비상업적 교육·연구, 그리고 정당한 라이선시에게 제공하는 전문 서비스가 포함된다. 그리고 **각 버전은 공개 후 2년째 되는 날 Apache-2.0 으로 전환**된다(ALv2 Future License).[^fsl]

**실무적으로 무슨 뜻인가.** 사내 애플리케이션에서 스키마를 관리하는 통상적인 사용은 "내부 사용"에 해당해 영향이 거의 없다. 무게가 실리는 쪽은 **Liquibase 를 안에 넣어 남에게 파는 경우** — 관리형 DB 서비스, 배포 플랫폼, 마이그레이션을 기능으로 내세운 SaaS 다. OSI 승인 오픈소스만 허용하는 사내 정책이 있는 조직이라면 승인 절차부터 다시 밟아야 한다. (법적 판단이 아니라 라이선스 원문의 조항을 옮긴 것이다. 실제 적용은 법무 검토 사항이다.)

이 한 항목 때문에 "둘 다 오픈소스니 취향대로"라는 2024년식 요약은 더 이상 정확하지 않다.

## 6. Spring Boot 에서는 어느 쪽이든 "하나만" 써라

Spring Boot 문서는 스키마 생성에 **단일 메커니즘을 쓰라**고 권한다. 그리고 Flyway·Liquibase 같은 상위 도구를 쓴다면 **그것만으로 스키마를 만들라**고 명시한다. `schema.sql`/`data.sql` 을 Flyway·Liquibase 와 **함께** 쓰는 것은 권장되지 않으며 **향후 릴리스에서 지원이 제거될 예정**이다.[^boot]

덧붙여 Boot 의 `spring.jpa.hibernate.ddl-auto` 기본값 결정에는 마이그레이션 도구의 존재가 끼어든다 — 임베디드 DB 가 감지되고 **스키마 매니저(Flyway 또는 Liquibase)가 감지되지 않았을 때만** `create-drop` 이 되고, 그 밖에는 `none` 이다.[^boot] 즉 마이그레이션 도구를 넣는 순간 Hibernate 의 자동 DDL 은 조용히 물러난다. 두 개를 같이 켜 두고 "왜 스키마가 두 번 생기지"로 고생하는 사고는 여기서 나온다.

## 7. 요약 — 어느 쪽을 고를까

| 축 | Flyway | Liquibase |
| --- | --- | --- |
| 변경의 식별자 | 버전(파일명) | `id` + `author` + 파일 경로 |
| 실행 순서의 근거 | 버전의 수치 정렬 | `include` 나열 순 / `includeAll` 알파벳 순 |
| 추적 테이블 | `flyway_schema_history` | `DATABASECHANGELOG` + `DATABASECHANGELOGLOCK` |
| 동시 실행 방지 | 이 글에서 공식 문서로 확인하지 못함 | 전용 락 테이블 `DATABASECHANGELOGLOCK` + `release-locks` |
| 작성 형식 | SQL(+ Java·스크립트) | SQL / XML / YAML / JSON |
| DB 추상화 | 없음(내가 쓴 SQL 그대로) | Change Type 이 DB별 SQL 생성 |
| 조건부 실행 | 고급 규칙 설정 가능 | `contexts`·`labels`·`preconditions` |
| 롤백 | undo 마이그레이션, **Teams 에디션** | `rollback`/`-to-date`/`-count` 는 OSS, 단건 롤백은 Secure |
| 롤백 검증 | — | `update-testing-rollback`, `future-rollback-sql` |
| 오픈소스 라이선스 | Apache-2.0 | 5.0.0까지 Apache-2.0, **5.0.1부터 FSL-1.1-ALv2** |

**Flyway 가 맞는 경우**: DB 벤더가 하나로 고정돼 있고, SQL 을 직접 쓰는 게 자연스럽고, 팀이 작아 마이그레이션 추가가 직렬에 가깝고, 라이선스를 단순하게 유지하고 싶을 때. 내 정산 저장소가 정확히 이 조건이고, 그래서 Flyway 다.

**Liquibase 가 맞는 경우**: 지원해야 할 DB 벤더가 여럿이거나, 환경별로 도는 변경이 갈리거나(`contexts`/`labels`), 롤백을 **검증까지** 자동화해야 하는 규제 환경이거나, 여러 팀이 같은 저장소에 동시에 마이그레이션을 밀어 넣는 구조일 때. 다만 5.0.1 이후 버전을 쓴다면 라이선스 검토를 먼저 끝내야 한다.

**근거의 한계.** 이 글은 기능과 라이선스만 비교했다. 마이그레이션 속도·메모리 같은 성능 비교는 **중립적인 제3자 헤드투헤드 벤치마크를 찾지 못해 다루지 않았다.** 양쪽 벤더가 각자 내는 수치는 재현 조건이 공개돼 있지 않아 인용하지 않았다. 5절의 305개 마이그레이션과 2026-08-27 버전 충돌은 내 저장소에서 직접 센 것이고, 일반적인 통계가 아니다.

마지막으로 이름 이야기. 질문을 받은 김에 찾아봤는데, **"Liquibase = liquid + base" 라는 어원을 밝힌 1차 출처는 찾지 못했다.** 확인되는 사실은 2006년 Sundog 의 엔지니어였던 Nathan Voxland 가 여러 고객사의 서로 다른 DB 를 감당하려고 만들었고, Scott Ambler·Pramod Sadalage 의 *Refactoring Databases: Evolutionary Database Design* 을 읽고 **DB 변경을 리팩터링의 연속으로 보는 발상**에서 출발했다는 것이다. `addLookupTable` 같은 고수준 Change Type 이 거기서 나왔다.[^lb-origin] 이름의 유래는 추측하지 않고 비워 둔다.

---

## References

[^fw-versioned]: Redgate, "Versioned migrations", Flyway Product Documentation. <https://documentation.red-gate.com/flyway/flyway-concepts/migrations/versioned-migrations>
[^fw-prefix]: Redgate, "Flyway SQL Migration Prefix Setting", Flyway Product Documentation. <https://documentation.red-gate.com/flyway/reference/configuration/flyway-namespace/flyway-sql-migration-prefix-setting>
[^fw-history]: Redgate, "Flyway schema history table", Flyway Product Documentation. <https://documentation.red-gate.com/flyway/flyway-concepts/migrations/flyway-schema-history-table>
[^fw-validate]: Redgate, "Flyway's Validate Command Explained Simply". 벤더 1차 해설 문서(CRC32 언급 포함). <https://www.red-gate.com/hub/product-learning/flyway/flyways-validate-command-explained-simply/>
[^fw-undo]: Redgate, "Undo migrations", Flyway Product Documentation. 페이지 상단에 `EDITION: TEAMS` 표기. <https://documentation.red-gate.com/flyway/flyway-concepts/migrations/undo-migrations>
[^fw-repo]: flyway/flyway 저장소 `LICENSE.md` 및 README (Apache-2.0, Copyright © Red Gate Software Ltd 2010-2026). <https://github.com/flyway/flyway>
[^lb-changelog]: Liquibase, "What is a Changelog?". <https://docs.liquibase.com/concepts/changelogs/home.html>
[^lb-changetype]: Liquibase, "What is a Change type?". <https://docs.liquibase.com/change-types/home.html>
[^lb-dbcl]: Liquibase, "DATABASECHANGELOG table". <https://docs.liquibase.com/concepts/tracking-tables/databasechangelog-table.html>
[^lb-lock]: Liquibase, "What is the DATABASECHANGELOGLOCK table?". <https://docs.liquibase.com/concepts/tracking-tables/databasechangeloglock-table.html>
[^lb-include]: Liquibase, "include". <https://docs.liquibase.com/change-types/include.html>
[^lb-includeall]: Liquibase, "includeAll". <https://docs.liquibase.com/change-types/includeall.html>
[^lb-rollback]: Liquibase, "What is a rollback?". <https://docs.liquibase.com/workflows/liquibase-community/using-rollback.html>
[^lb-license]: liquibase/liquibase 저장소 `LICENSE.txt`·`pom.xml`·README, 및 커밋 `c574abc` ("chore: update LICENSE to Functional Source License, Version 1.1 (#7317)", 2025-09-30). <https://github.com/liquibase/liquibase/commit/c574abc00bafd6bc55ed8e4ae7bbde25d0af4ed3>
[^mvn]: Maven Central 의 각 버전 POM `<licenses>` 블록 (`liquibase-core` 4.33.0 / 5.0.0 / 5.0.1) 및 `maven-metadata.xml` (2026-09-14 조회). <https://repo1.maven.org/maven2/org/liquibase/liquibase-core/>
[^fsl]: Functional Source License, Version 1.1, ALv2 Future License 전문 (Permitted Purpose / Competing Use / Grant of Future License 조항). <https://fsl.software/FSL-1.1-ALv2.template.md>
[^boot]: Spring Boot Reference, "Database Initialization". <https://docs.spring.io/spring-boot/how-to/data-initialization.html>
[^lb-origin]: Liquibase, "Liquibase Celebrates 15 Years of Improving Database Release Quality & Speed" (2021-06-16 보도자료, Nathan Voxland 직접 인용). <https://finance.yahoo.com/news/liquibase-celebrates-15-years-improving-130000340.html>
