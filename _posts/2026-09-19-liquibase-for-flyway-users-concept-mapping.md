---
layout: post
title: "Flyway 를 아는 사람을 위한 Liquibase — 개념 하나씩 대응표로 옮겨봤다"
date: 2026-09-19 03:35:53 +0900
categories: [Engineering, Database]
tags: [Flyway, Liquibase, 마이그레이션, 스키마관리, 대응표, 에디션]
---

[지난 글](/2026/09/14/liquibase-vs-flyway-change-identity/)에서 두 도구의 차이가 "변경의 정체성을 무엇으로 잡느냐" 에서 갈린다고 썼다. 그건 *왜* 다른지에 대한 글이었다. 이번 글은 *그래서 내가 아는 Flyway 개념이 Liquibase 에서는 무엇인가* 에 대한 글이다. Flyway 를 쓰던 사람이 Liquibase 를 처음 열었을 때 "이건 `R__` 인가, `baseline` 은 어디 있나, `repair` 는?" 하고 묻게 되는 순서대로, Flyway 쪽 용어를 기준 삼아 하나씩 옮긴다.

원칙은 지난 글과 같다. 사실 주장은 **양쪽 공식 문서**로 확인한 것만 적고, 어느 에디션에서 되는지를 문서에 적힌 대로 표기한다. 성능 비교는 중립 측정이 없어 다루지 않는다. 확인 시점은 2026-09-19 이고, 대상 버전은 GitHub 최신 릴리스 기준 Flyway `13.7.0`(2026-09-15), Liquibase Community `5.0.4`(2026-08-20) 이다.[^gh]

## 0. 먼저 에디션 지도를 그려야 한다

대응표를 읽으려면 양쪽의 유료 경계를 먼저 알아야 한다. 같은 이름의 기능이 한쪽은 무료, 다른 쪽은 유료인 경우가 여러 개다.

- **Flyway**: Redgate 의 명령어 목록 페이지가 명령마다 `Community` / `Teams` / `Enterprise` 티어를 표기한다.[^fw-cmd] 오픈소스 코드는 Apache-2.0 이다.
- **Liquibase**: 문서가 명령마다 `All editions` / `Liquibase Secure` 를 표기한다.[^lb-rb] 5.0 부터 Community 와 Secure 가 배포 채널부터 분리됐고, Community 는 FSL-1.1-ALv2 로 바뀌었다.[^lb-500] 라이선스 자체의 의미는 지난 글 5절에 있으니 여기선 반복하지 않는다.

이 글의 표에서 **(C)** 는 무료 배포판에서 되는 것, **(T)** 는 Flyway Teams, **(E)** 는 Flyway Enterprise, **(S)** 는 Liquibase Secure 다.

## 1. 마이그레이션 종류

| Flyway | Liquibase | 비고 |
|---|---|---|
| 버전 마이그레이션 `V1__x.sql` — 버전 순서로 정확히 한 번 실행[^fw-v] | 체인지셋 (`id`+`author`+파일경로) — 한 번 실행되면 재실행 안 함[^lb-cs] | Liquibase 의 `id` 는 **순서를 지시하지 않는다.** 문서가 "just an identifier" 라고 명시. 순서는 changelog 안에 적힌 순서다 |
| 반복 마이그레이션 `R__x.sql` — 체크섬이 바뀔 때마다 재실행, 버전 마이그레이션 뒤에 알파벳 순[^fw-r] | `runOnChange="true"` 체인지셋 — 체크섬이 바뀌면 재실행[^lb-cs] | 가장 정확한 1:1 대응. 단 Liquibase 는 "항상 마지막에" 라는 규칙이 없다. changelog 에 적힌 자리에서 돈다 |
| 반복 마이그레이션을 매번 강제 실행 — `${flyway:timestamp}` 플레이스홀더를 넣어 체크섬을 매번 바꾸는 트릭[^fw-r] | `runAlways="true"`[^lb-cs] | Flyway 는 트릭, Liquibase 는 속성. 이건 Liquibase 쪽이 정직하다 |
| Undo 마이그레이션 `U1__x.sql` **(T)**[^fw-u] | `rollback` 블록 (모델형 changelog 에선 자동 생성 가능, SQL 형식에선 `--rollback` 주석으로 직접 작성)[^lb-rb] | 4절에서 따로 |
| Java 마이그레이션 — `JavaMigration` 인터페이스 구현[^fw-java] | `customChange` Change Type — Java 클래스를 체인지셋 안에서 호출[^lb-custom] | 용도 설명이 양쪽 다 "SQL 로 표현 어려운 BLOB·대량 데이터 변환" |
| 스크립트 마이그레이션 `.sh` `.ps1` `.py` 등[^fw-script] | 공식 문서에서 동급 대응을 확인하지 못했다 | 이 항목은 Flyway 고유로 두는 게 정확하다 |

핵심은 첫 줄이다. Flyway 사용자는 "버전 = 순서" 에 익숙하다. Liquibase 로 오면 그 등식이 깨진다. `id` 에 `001`, `002` 를 적어도 Liquibase 는 그걸 정렬 키로 쓰지 않는다. changelog 파일에 위에서 아래로 적힌 순서가 실행 순서다. 지난 글에서 다룬 `include`/`includeAll` 문제가 여기서 나온다.

## 2. 명령어

| Flyway | Liquibase | 비고 |
|---|---|---|
| `migrate` (C)[^fw-cmd] | `update` (C)[^lb-upd] | |
| `info` (C) — 적용/대기 상태 표시 | `status` — 미배포 체인지셋 목록[^lb-status] + `history` — 배포된 체인지셋과 deploymentId[^lb-hist] | Flyway 는 한 명령, Liquibase 는 둘로 나눠져 있다 |
| `validate` (C) — 이름·타입·체크섬 차이, 로컬에 없는 적용분, 미적용분을 검사[^fw-val] | `validate` — changelog 문법·참조 파일·XSD·id/author/file 중복·체크섬·추적 테이블 존재 검사[^lb-val] | 이름은 같지만 Liquibase 쪽은 **changelog 문법 검사** 비중이 크다. 양쪽 다 "SQL 자체의 정확성은 안 본다" 고 명시 |
| `repair` (C) — 실패 항목 제거, 체크섬·설명·타입 재정렬, 사라진 마이그레이션을 deleted 로 표시[^fw-rep] | `clear-checksums` — MD5SUM 컬럼을 전부 비우고 다음 `update` 에서 재계산[^lb-cc] | 부분 대응. Flyway `repair` 의 "실패 행 제거" 에 해당하는 것은 Liquibase 에선 해당 행을 직접 다루거나 `changelog-sync` 로 처리해야 한다 |
| `baseline` (C) — 기존 DB 를 특정 버전까지 적용된 것으로 표시[^fw-bl] / `baselineOnMigrate` 설정[^fw-bom] | `changelog-sync` — 미배포 체인지셋 전부를 실행된 것으로 표시[^lb-sync] | 용도가 같다. Liquibase 문서도 첫 문장에 "baseline a new database environment" 라고 쓴다 |
| `undo` **(T)**[^fw-cmd] | `rollback` / `rollback-count` / `rollback-to-date` (C), `rollback-one-changeset` / `rollback-one-update` **(S)**[^lb-rb] | 4절 |
| `check dryrun` **(T)**[^fw-cmd] | `update-sql` — 실행할 SQL 을 출력만 한다[^lb-usql] | **에디션이 뒤집힌 항목.** Flyway 는 드라이런이 Teams, Liquibase 는 Community |
| `diff` / `generate` **(E)** — 스키마 비교 후 마이그레이션 생성[^fw-cmd] | `diff` / `diff-changelog` — 두 DB 비교, 차이를 changelog 로 생성[^lb-diff][^lb-dcl] | **또 하나 뒤집힌 항목.** Liquibase 는 기본 비교·생성이 Community 에 있다. 단 Drift Report 같은 보고서는 Secure |
| `clean` (C) — 스키마의 모든 객체 삭제, 문서가 "never use on production" 명시[^fw-cmd] | `drop-all` | 양쪽 다 개발용 |
| `check drift` **(E)**[^fw-cmd] | `diff` 로 드리프트 탐지 (C), Drift Report 는 **(S)**[^lb-diff] | |
| `mcp` **(E)** — AI 코딩 에이전트용 MCP 서버[^fw-cmd] | 공식 문서에서 확인하지 못했다 | 2026년 9월 시점 |

표를 보면 패턴이 보인다. **Flyway 는 "실행" 은 무료로 열고 "미리 보기·비교·생성" 을 유료로 뒀다.** Liquibase 는 반대로 미리 보기(`update-sql`)와 비교(`diff`)를 무료에 두고, **"한 건만 되돌리기" 와 "보고서" 를 유료로 뒀다.** 두 회사가 돈을 받는 자리가 다르다. 팀이 뭘 자주 쓰는지에 따라 무료 판의 체감 범위가 달라진다.

## 3. 설정과 실행 제어

| Flyway | Liquibase | 비고 |
|---|---|---|
| `outOfOrder=true` — 1.0, 3.0 적용 후 2.0 이 발견되면 무시하지 않고 적용. 기본값 `false`[^fw-ooo] | **기본 동작이 이것이다.** `update` 는 changelog 를 순서대로 읽으며 `DATABASECHANGELOG` 에 없는 체인지셋을 전부 적용한다[^lb-upd] | Flyway 사용자가 가장 놀라는 지점. Liquibase 에는 "순서에 어긋난 변경을 거부" 하는 기본 안전장치가 없다 |
| `target` — 이 버전까지만 적용. `current`/`latest`/`next` 특수값[^fw-tgt] | `update-to-tag` — 태그까지만 적용[^lb-utt] / `update-count` — N 개까지만 적용[^lb-uc] | Liquibase 는 태그를 changelog 안에 `tagDatabase` 체인지셋으로 심거나 `tag` 명령으로 찍는다[^lb-tag] |
| `cherryPick` **(T)** — 지정한 마이그레이션만, 지정한 순서로[^fw-cp] | `contexts` / `labels` — 체인지셋에 태그를 붙이고 실행 시 필터[^lb-ctx] | 대응이 느슨하다. Flyway 는 실행 시점에 골라내고, Liquibase 는 작성 시점에 태그를 붙여둔다 |
| `ignoreMigrationPatterns` — `type:status` 패턴으로 validate/repair 에서 무시[^fw-ign] | `contexts`/`labels` 필터, 또는 `preconditions` 의 `onFail` | 부분 대응 |
| `placeholders` — `${key}` 를 SQL 에서 치환[^fw-ph] | property substitution — `${property-name}` 치환[^lb-prop] | 문법까지 같다 |
| `locations` — 스캔할 경로 배열, classpath/filesystem 접두사[^fw-loc] | 루트 changelog 의 `include` / `includeAll` | Flyway 는 설정, Liquibase 는 changelog 안의 선언 |
| 콜백 `beforeMigrate.sql` `afterMigrate.sql` 등 — 생명주기 훅[^fw-cb] | 공식 문서에서 대응 개념을 확인하지 못했다 | `runAlways` 체인지셋을 changelog 앞뒤에 두면 비슷하게 흉내낼 수 있지만, 문서가 그렇게 권하지 않으므로 대응이라 적지 않는다 |
| — | `preconditions` — DB 상태를 검사해 실행 여부 결정. changelog 레벨은 검증 단계에서 평가[^lb-pre] | Flyway 에 직접 대응 없음. Liquibase 고유 |

`outOfOrder` 줄을 다시 보자. Flyway 에서 이 값을 `true` 로 켜는 건 팀이 의식적으로 하는 결정이다. Liquibase 는 그게 기본이다. 그래서 두 사람이 서로 다른 브랜치에서 체인지셋을 추가하고 나중에 합쳐도, Liquibase 는 "이미 뒤 버전이 적용됐으니 앞 버전을 거부" 하지 않고 둘 다 조용히 적용한다. 지난 글에서 "Flyway 는 늦게 크게 확실하게 터지고, Liquibase 는 조용히 통과한다" 고 쓴 게 이 동작이다.

## 4. 되돌리기 — 에디션 표기를 정확히

지난 글에서 "Liquibase 는 롤백이 되고 Flyway 는 안 된다는 요약은 양쪽 다 틀렸다" 고 썼다. 이번엔 문서의 에디션 표기를 그대로 옮긴다.

**Flyway.** `undo` 명령과 `U__` 마이그레이션은 문서 상단에 `EDITION: TEAMS` 가 박혀 있다.[^fw-u] 무료 판에 되돌리기 명령은 없다. 그리고 문서 스스로 한계를 길게 적는다 — undo 는 마이그레이션 전체가 성공했음을 가정하므로, DDL 트랜잭션이 없는 DB 에서 10문장 중 5번째가 실패한 경우엔 도움이 안 된다. 그런 상황의 대안으로 문서가 권하는 건 **DB 와 배포된 모든 코드 버전의 하위 호환을 유지하고 애플리케이션을 롤백하는 것**이다.[^fw-u]

**Liquibase.** 롤백 명령 표의 에디션 컬럼은 이렇다.[^lb-rb]

| 명령 | 에디션 |
|---|---|
| `rollback` (태그 기준) | All editions |
| `rollback-count` | All editions |
| `rollback-to-date` | All editions |
| `update-testing-rollback` — 배포 → 롤백 → 재배포로 롤백을 검증 | All editions |
| `future-rollback-sql` — 미배포 변경의 롤백 SQL 을 미리 출력 | All editions |
| `rollback-one-changeset` | **Liquibase Secure** |
| `rollback-one-update` | **Liquibase Secure** |

그리고 주의 하나. 모델형 changelog(XML/YAML/JSON) 에서는 `createTable` 같은 Change Type 의 롤백을 Liquibase 가 만들어 주지만, **SQL 형식 changelog 에서는 그렇지 않다.** 문서 원문은 "Custom rollback definitions are not supported in formatted SQL changelogs. You must write rollback SQL manually in the changelog file" 이다.[^lb-rb] Flyway 사용자가 SQL 을 그대로 쓰고 싶어서 Liquibase 의 SQL 형식을 택하면, 롤백에서는 Flyway 의 `U__` 와 똑같이 손으로 써야 한다. 자동 롤백은 추상화를 받아들인 대가로 얻는 것이다.

## 5. 추적 테이블과 체크섬

| Flyway | Liquibase | 비고 |
|---|---|---|
| `flyway_schema_history` 한 테이블. 상태값: Pending / Success / Ignored / Deleted / Available / Undone / Above Target / Baseline …[^fw-hist] | `DATABASECHANGELOG` — 체인지셋마다 한 행, `id`+`author`+`filename` 이 유일, **기본키 없음**(DB 별 키 길이 제약 회피)[^lb-dbcl] + `DATABASECHANGELOGLOCK` | Flyway 는 상태 머신을 한 테이블에 담고, Liquibase 는 "실행됐다" 만 남긴다. 되돌리면 행을 **삭제**한다[^lb-rb] |
| 체크섬: SQL 마이그레이션은 **CRC32**, `migrate` 시 자동 검증, 어긋나면 실패[^fw-val] | 체크섬: `MD5SUM` 컬럼. **파일의 체크섬이 아니라 체인지셋의 체크섬** — 포맷만 고치면 값이 안 바뀜. 알고리즘 버전 접두사(`8:`→`9:`)가 바뀌면 조용히 갱신[^lb-sum] | Flyway 는 파일 내용에 민감하고, Liquibase 는 의미에 민감하다. 공백 정리 커밋이 Flyway 에선 validate 실패, Liquibase 에선 무해 |
| 트랜잭션: 마이그레이션 하나가 한 트랜잭션. 실패 시 (가능하면) 롤백하고 중단. `group=true` 면 대기 중 전부를 한 트랜잭션으로[^fw-tx] | 체인지셋 하나가 한 트랜잭션(기본). `runInTransaction` 으로 조정[^lb-cs] | 단위가 같다 |

체크섬 줄이 실무에서 자주 걸린다. Flyway 팀은 "이미 적용된 파일은 절대 건드리지 않는다" 를 몸에 익힌다. Liquibase 로 오면 그 규율을 조금 풀어도 된다 — 주석·공백·들여쓰기는 고쳐도 체크섬이 같다. 대신 반대 방향의 함정이 있다. 체크섬이 안 바뀌니 "고쳤는데 왜 안 도나" 가 되고, 그래서 `runOnChange` 가 필요해진다.

## 6. 배포 형태 — 2026년에 새로 생긴 차이

Liquibase Community 5.0 은 **드라이버·확장·상당수 의존성을 빼고** 배포된다. 릴리스 노트가 "much lighter, modular … both allows and requires users to manage their Liquibase dependencies" 라고 쓰고, 그 자리에 `liquibase lpm` 패키지 매니저 명령을 넣었다.[^lb-500] Java 최소 버전도 17 로 올라갔다.

Flyway 는 명령줄 배포판 문서에 DB 별 드라이버 레퍼런스 페이지가 있고[^fw-drv], 릴리스 주기가 빠르다 — 2026년 8월 13일 `13.3.0` 부터 9월 15일 `13.7.0` 까지 5주 동안 다섯 번이다.[^gh]

Flyway 사용자가 Liquibase 5.x 를 처음 깔면 "왜 PostgreSQL 드라이버가 없나" 를 먼저 만난다. 버그가 아니라 설계다. `lpm` 으로 받거나 클래스패스에 직접 넣어야 한다.

## 7. 옮겨갈 때 실제로 바뀌는 습관 다섯 개

대응표를 다 놓고 보면, Flyway 사용자가 Liquibase 에서 **고쳐야 하는 습관**은 다섯 개로 모인다.

1. **파일명이 아니라 changelog 순서를 관리한다.** `id` 에 번호를 붙여도 정렬되지 않는다. 루트 changelog 의 `include` 목록이 곧 순서다.
2. **순서 어긋남을 도구가 막아주지 않는다.** Flyway 의 `outOfOrder=false` 기본 안전장치가 없다. 원하면 `preconditions` 나 리뷰 규칙으로 직접 만든다.
3. **`R__` 대신 속성을 쓴다.** `runOnChange` 가 반복 마이그레이션, `runAlways` 가 매번 실행이다. `${flyway:timestamp}` 트릭은 잊는다.
4. **되돌리기의 무료 범위가 넓어지지만, SQL 형식이면 손으로 쓴다.** 태그·개수·날짜 기준 롤백은 Community 다. 단건 롤백은 Secure 고, SQL changelog 의 롤백 블록은 `U__` 처럼 직접 작성이다.
5. **드라이런과 비교는 무료로 얻는다.** `update-sql` 과 `diff` 는 Community 다. Flyway 에서 Teams/Enterprise 였던 두 가지가 여기서는 기본 도구다.

반대로 **Flyway 로 돌아갈 때** 잃는 것도 같은 목록이다 — 순서 안전장치를 얻고, `runOnChange` 의 자리 자유를 잃고, 드라이런과 비교를 유료로 넘긴다.

---

**검증 범위.** 표의 모든 기능·에디션 주장은 2026-09-19 기준 Redgate Flyway 문서와 Liquibase 문서(5.1 표기 페이지)에서 확인했다. Liquibase 문서는 5.1 버전 페이지를 기준으로 했으나 GitHub 최신 Community 릴리스는 5.0.4 라 세부 동작이 다를 수 있다. "공식 문서에서 확인하지 못했다" 고 적은 항목은 기능이 없다는 뜻이 아니라 **문서에서 대응 개념을 찾지 못했다**는 뜻이다. 두 도구를 같은 스키마에 실제로 번갈아 적용해 본 실측은 이 글에 없다. 성능 비교는 중립 측정이 없어 다루지 않았다.

## References

[^gh]: GitHub REST API `GET /repos/flyway/flyway/releases`, `GET /repos/liquibase/liquibase/releases` — 2026-09-19 조회. <https://github.com/flyway/flyway/releases> · <https://github.com/liquibase/liquibase/releases>
[^fw-cmd]: Redgate, "Commands" (명령별 Community/Teams/Enterprise 티어 표). <https://documentation.red-gate.com/flyway/reference/commands>
[^fw-v]: Redgate, "Versioned migrations". <https://documentation.red-gate.com/flyway/flyway-concepts/migrations/versioned-migrations>
[^fw-r]: Redgate, "Repeatable migrations" (`${flyway:timestamp}` 트릭 포함). <https://documentation.red-gate.com/flyway/flyway-concepts/migrations/repeatable-migrations>
[^fw-u]: Redgate, "Undo migrations" (`EDITION: TEAMS`). <https://documentation.red-gate.com/flyway/flyway-concepts/migrations/undo-migrations>
[^fw-java]: Redgate, "Java-based migrations". <https://documentation.red-gate.com/flyway/flyway-concepts/migrations/java-based-migrations>
[^fw-script]: Redgate, "Script migrations". <https://documentation.red-gate.com/flyway/flyway-concepts/migrations/script-migrations>
[^fw-val]: Redgate, "Validate" (CRC32 명시). <https://documentation.red-gate.com/flyway/reference/commands/validate>
[^fw-rep]: Redgate, "Repair". <https://documentation.red-gate.com/flyway/reference/commands/repair>
[^fw-bl]: Redgate, "Baseline" 및 "Baselines" 개념. <https://documentation.red-gate.com/flyway/reference/commands/baseline> · <https://documentation.red-gate.com/flyway/flyway-concepts/baselines>
[^fw-bom]: Redgate, "Flyway Baseline On Migrate Setting". <https://documentation.red-gate.com/flyway/reference/configuration/flyway-namespace/flyway-baseline-on-migrate-setting>
[^fw-ooo]: Redgate, "Flyway Out Of Order Setting". <https://documentation.red-gate.com/flyway/reference/configuration/flyway-namespace/flyway-out-of-order-setting>
[^fw-tgt]: Redgate, "Flyway Target Setting". <https://documentation.red-gate.com/flyway/reference/configuration/flyway-namespace/flyway-target-setting>
[^fw-cp]: Redgate, "Flyway Cherry Pick Setting" (Flyway Teams). <https://documentation.red-gate.com/flyway/reference/configuration/flyway-namespace/flyway-cherry-pick-setting>
[^fw-ign]: Redgate, "Flyway Ignore Migration Patterns Setting". <https://documentation.red-gate.com/flyway/reference/configuration/flyway-namespace/flyway-ignore-migration-patterns-setting>
[^fw-ph]: Redgate, "Flyway Placeholders Namespace". <https://documentation.red-gate.com/flyway/reference/configuration/flyway-namespace/flyway-placeholders-namespace>
[^fw-loc]: Redgate, "Flyway Locations Setting". <https://documentation.red-gate.com/flyway/reference/configuration/flyway-namespace/flyway-locations-setting>
[^fw-cb]: Redgate, "Callbacks". <https://documentation.red-gate.com/flyway/flyway-concepts/callbacks>
[^fw-hist]: Redgate, "Flyway schema history table" (마이그레이션 상태 목록). <https://documentation.red-gate.com/flyway/flyway-concepts/migrations/flyway-schema-history-table>
[^fw-tx]: Redgate, "Migration transaction handling". <https://documentation.red-gate.com/flyway/flyway-concepts/migrations/migration-transaction-handling>
[^fw-drv]: Redgate, "Database Driver Reference". <https://documentation.red-gate.com/flyway/reference/database-driver-reference>
[^lb-500]: liquibase/liquibase Release `v5.0.0` (2025-09-30) — Community/Secure 분리, FSL, LPM, Java 17. <https://github.com/liquibase/liquibase/releases/tag/v5.0.0>
[^lb-cs]: Liquibase, "What is a Changeset?" (`id` 는 순서를 지시하지 않음, `runAlways`/`runOnChange`/`runInTransaction`). <https://docs.liquibase.com/concepts/changelogs/changeset.html>
[^lb-upd]: Liquibase, "update" (순서대로 읽고 DBCL 에 없는 것을 적용). <https://docs.liquibase.com/commands/update/update.html>
[^lb-status]: Liquibase, "status". <https://docs.liquibase.com/commands/change-tracking/status.html>
[^lb-hist]: Liquibase, "history". <https://docs.liquibase.com/commands/change-tracking/history.html>
[^lb-val]: Liquibase, "validate". <https://docs.liquibase.com/commands/utility/validate.html>
[^lb-cc]: Liquibase, "clear-checksums". <https://docs.liquibase.com/commands/utility/clear-checksums.html>
[^lb-sync]: Liquibase, "changelog-sync". <https://docs.liquibase.com/commands/utility/changelog-sync.html>
[^lb-rb]: Liquibase, "What is a rollback?" (명령별 에디션 표, SQL 형식 롤백 수동 작성). <https://docs.liquibase.com/commands/rollback/home.html>
[^lb-usql]: Liquibase, "update-sql". <https://docs.liquibase.com/commands/update/update-sql.html>
[^lb-diff]: Liquibase, "diff". <https://docs.liquibase.com/commands/inspection/diff.html>
[^lb-dcl]: Liquibase, "diff-changelog". <https://docs.liquibase.com/commands/inspection/diff-changelog.html>
[^lb-utt]: Liquibase, "update-to-tag". <https://docs.liquibase.com/commands/update/update-to-tag.html>
[^lb-uc]: Liquibase, "update-count". <https://docs.liquibase.com/commands/update/update-count.html>
[^lb-tag]: Liquibase, "tag". <https://docs.liquibase.com/commands/utility/tag.html>
[^lb-ctx]: Liquibase, "What are contexts?". <https://docs.liquibase.com/concepts/changelogs/attributes/contexts.html>
[^lb-pre]: Liquibase, "What are preconditions?". <https://docs.liquibase.com/concepts/changelogs/preconditions.html>
[^lb-prop]: Liquibase, "What is property substitution?". <https://docs.liquibase.com/concepts/changelogs/property-substitution.html>
[^lb-custom]: Liquibase, "customChange". <https://docs.liquibase.com/change-types/custom-change.html>
[^lb-dbcl]: Liquibase, "What is the DATABASECHANGELOG table?". <https://docs.liquibase.com/concepts/tracking-tables/databasechangelog-table.html>
[^lb-sum]: Liquibase, "What is a Changeset checksum?". <https://docs.liquibase.com/concepts/changelogs/changeset-checksums.html>

관련 글: [Liquibase 와 Flyway — 장단점은 '변경의 정체성' 에서 갈린다 (9/14)](/2026/09/14/liquibase-vs-flyway-change-identity/)
