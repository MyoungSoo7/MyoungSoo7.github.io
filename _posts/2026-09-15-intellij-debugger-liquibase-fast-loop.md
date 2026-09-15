---
layout: post
title: "인텔리제이 디버거와 Liquibase — 생산성은 '루프를 몇 번 도느냐'로 결정된다"
date: 2026-09-15 19:47:20 +0900
categories: [Engineering, Database]
tags: [IntelliJ, Liquibase, 디버깅, SpringBoot, 마이그레이션, 생산성]
---

[Liquibase 와 Flyway 비교]({% post_url 2026-09-14-liquibase-vs-flyway-change-identity %})에서는 도구를 고르는 축을, [깃랩과 인텔리제이]({% post_url 2026-09-14-gitlab-intellij-productive-workflow %})에서는 커밋·리뷰·CI 루프를 다뤘다. 이번엔 그 사이에 낀 자리다 — **로컬에서 디버거를 붙여 놓고 마이그레이션이 걸린 애플리케이션을 고치는 시간.**

이 조합이 유독 답답한 이유는 분명하다. 디버거는 "프로세스를 살려 둔 채 들여다보는" 도구인데, **Liquibase 는 프로세스가 뜨는 순간에만 일한다.** 한쪽은 재시작을 피하려 하고 다른 쪽은 재시작을 전제한다. 그래서 이 글의 주제는 디버거 단축키 목록이 아니라 **재시작 횟수를 어떻게 줄이는가**다.

한 번의 디버깅 루프 비용을 이렇게 쪼개 보면 어디를 건드려야 하는지가 보인다.

$$T_{loop} = T_{build} + T_{boot} + T_{migrate} + T_{repro}, \qquad T_{total} = n \times T_{loop}$$

Liquibase 설정으로 줄일 수 있는 건 $T_{migrate}$ 하나뿐이고, 대개 그건 제일 작은 항이다. **진짜 이득은 $n$ 을 줄이는 데서 나온다.** 아래 절들은 그 순서로 간다.

> 확인한 문서 버전: Liquibase 공식 문서는 5.1 기준, IntelliJ IDEA 는 현재 온라인 도움말, Spring Boot 는 현행 레퍼런스다. 버전이 다르면 동작이 다를 수 있다.

---

## 1. 먼저: changeset 의 정체성은 무엇인가

이걸 모르면 아래 모든 증상이 "갑자기 안 됨" 으로 보인다.

Liquibase 공식 문서의 정의는 이렇다 — **changeset 은 `author` 와 `id`, 그리고 changelog 파일 경로로 유일하게 식별된다.**[^changeset] `id` 는 식별자일 뿐이라 실행 순서를 정하지도, 정수일 필요도 없다.

여기서 나오는 첫 번째 함정 — **파일을 옮기면 다른 changeset 이 된다.** 리팩터링하다가 `db/changelog/v1/` 을 `db/changelog/2026/v1/` 로 정리하면, 이미 배포된 것과 같은 내용의 changeset 이 **미배포 상태로 다시 나타난다.** IDE 의 파일 이동은 자바 패키지는 잘 따라가지만 changelog 경로 문자열은 그런 보호를 받지 못한다.

두 번째로, 실행 여부를 판정하는 건 체크섬이다. 그런데 이 체크섬의 성질이 직관과 다르다.[^checksum]

- **파일의 체크섬이 아니다.** 그래서 포맷팅을 고쳐도 체크섬이 같을 수 있다.
- **changeset 이 안 변했는데도 저장된 체크섬이 바뀔 수 있다.** 알고리즘 개선 때문이며 맨 앞 한 자리에 한정된다(`8:9df0` → `9:0312`). 이 경우 검증은 실패하지 않고 **조용히 갱신된다.**
- Liquibase 4.22.0 의 체크섬 로직 변경은 **뷰·프로시저·저장 로직 객체의 공백 처리**를 개선한 것이다. 문서가 그 이유를 이렇게 적어 뒀다 — *"SQL 스크립트가 IDE 에 열려 있을 때 가끔 발생하는 것처럼"* 공백이 바뀌어 생기는 검증 오류를 막기 위해서다.[^checksum]

마지막 항목은 그냥 지나칠 문장이 아니다. **Liquibase 공식 문서가 "IDE 가 파일을 건드려서 체크섬이 깨지는 일"을 명시적으로 인정하고 있다.** 그리고 개선된 범위는 뷰·프로시저 등으로 한정돼 있다.

실무 대응은 하나다 — IntelliJ 의 **Settings | Editor | General 의 "On Save" 계열 설정(후행 공백 제거·저장 시 리포맷)이 changelog 디렉터리에 적용되지 않도록 범위를 좁힌다.** 저장만 했는데 마이그레이션이 깨지는 상황을 없애는 게, 아래의 어떤 디버깅 기법보다 루프 횟수를 크게 줄인다.

---

## 2. 디버거가 붙기도 전에 죽을 때

체크섬 불일치나 잘못된 SQL 은 **애플리케이션 부팅 중에** 터진다. 이 시점엔 내 컨트롤러에 찍어 둔 브레이크포인트는 아무 소용이 없다. 대부분 여기서 스택트레이스를 스크롤하며 "어느 changeset 이냐"를 눈으로 찾는다.

IntelliJ 의 **예외 브레이크포인트(Exception breakpoint)** 가 정확히 이 자리를 위한 물건이다. 공식 문서의 설명은 이렇다 — `Throwable` 또는 그 하위 클래스가 던져질 때 중단하며, **특정 소스 코드 위치를 지정할 필요가 없다.** 그리고 결정적으로: *"스택 트레이스와 달리, 예외에서 애플리케이션을 중단시키면 데이터가 아직 살아 있는 동안 주변 컨텍스트를 살펴볼 수 있다."*[^breakpoints]

즉 `liquibase.exception.*` 계열 예외에 예외 브레이크포인트를 걸어 두면, 텍스트로 요약된 메시지가 아니라 **그 순간의 changeset 객체와 계산된 체크섬을 변수 창에서 직접** 볼 수 있다. 라이브러리 소스를 안 받아도 된다 — 예외 브레이크포인트는 소스 참조가 필요 없다.

끊긴 뒤의 복구는 두 갈래이고, 둘은 하는 일이 다르다.

| 명령 | 하는 일 | 주의 |
| --- | --- | --- |
| `clear-checksums` | DATABASECHANGELOG 의 MD5SUM 을 전부 NULL 로 만든다. 다음 update 에서 재계산된다 | **이미 배포된 것의 체크섬만 재계산되는 게 아니다.** 공식 문서상 "대기 중인 changeset 은 배포된다"[^clearchecksums] |
| `changelog-sync` | 미배포 changeset 을 **실행된 것으로 표시**한다 (실제로 돌리지 않음) | 손으로 만든 객체 때문에 다음 update 가 실패하는 걸 막는 용도로 문서가 직접 예시를 든다[^changelogsync] |

로컬에서 스키마를 손으로 만졌다가 꼬였다면 순서는 이렇다 — **어긋난 것이 "내용" 이면 `clear-checksums`, "존재" 면 `changelog-sync`.** 그리고 둘 다 **로컬 전용 도구로 취급**한다. 운영 DB 에서 `clear-checksums` 는 복구가 아니라 *검증을 끄는 행위*다.

---

## 3. 부팅이 느릴 때 — `contexts` 가 정공법이다

로컬에서만 필요한 시드 데이터·대용량 더미가 부팅마다 도는 건 $T_{migrate}$ 를 직접 키운다. Spring Boot 레퍼런스가 이 경우의 권장 방법을 명시하고 있다 — **Liquibase 의 contexts 를 쓰라**는 것이고, 구체적으로 테스트 데이터 changeset 에 `context:@test` 를 달고 필요한 환경에서 `spring.liquibase.contexts=test` 를 주라고 적혀 있다.[^bootdata]

여기서 `@` 가 핵심이다. Liquibase 문서의 정의는 이렇다 — `context="@test"` 는 **컨텍스트를 주지 않고 Liquibase 를 실행하면 그 changeset 이 돌지 않게** 만든다.[^contexts]

`@` 가 없으면 어떻게 되느냐가 이 절에서 제일 중요한 함정이다.

> **컨텍스트 필터를 지정하지 않으면, changelog 의 모든 미배포 changeset 이 실행된다 — 컨텍스트가 붙어 있어도.**[^contexts]

"로컬용이라고 `context="dev"` 를 달아 놨는데 운영 배포에서 같이 나갔다" 의 정체가 이거다. 컨텍스트는 **필터를 줄 때만 필터**이고, 안 주면 태그일 뿐이다. 로컬 전용을 표시할 때는 `@` 를 붙인 형태를 쓴다.

참고로 컨텍스트 논리는 `AND` / `OR` / `!` / 괄호를 지원하고, 쉼표는 `OR` 의 별칭이다.[^contexts]

### `spring.liquibase.enabled=false` 로 꺼 버리는 건 다른 문제를 만든다

빠른 길처럼 보이지만, 스키마를 누가 만드느냐가 같이 바뀐다. Spring Boot 레퍼런스의 문장은 이렇다 — *"임베디드 데이터베이스로 식별되고 스키마 매니저(Flyway 또는 Liquibase)가 감지되지 않으면 `ddl-auto` 는 `create-drop` 이 기본값이 된다. 그 외 모든 경우엔 `none` 이 기본값이다."*[^bootdata]

**주의: `spring.liquibase.enabled=false` 일 때 "감지되지 않음" 으로 판정되는지 나는 실측하지 않았다.** 그래서 어느 쪽으로 떨어지는지 단언하지 않는다. 확실한 대응은 문서가 직접 권하는 것과 같다 — **`spring.jpa.hibernate.ddl-auto` 를 기본값에 맡기지 말고 명시로 박는다.** 그래야 Liquibase 를 껐을 때 "아무도 스키마를 안 만들어서" 혹은 반대로 "Hibernate 가 매번 드롭해서" 생기는 사고가 안 난다.

그 밖에 알아 둘 두 가지도 같은 문서에 있다.[^bootdata]

- `spring-boot-starter-liquibase` 가 클래스패스에 있으면 마이그레이션은 **애플리케이션 부팅과 테스트 실행 전 양쪽에서** 기본으로 돈다. `spring.liquibase.enabled` 를 main/test 설정에서 다르게 주는 식으로 조정한다.
- **두 가지 초기화 방식의 혼용은 불가능하다** — 예컨대 "부팅은 Liquibase, 테스트는 JPA" 는 지원되지 않는다.

---

## 4. 루프 횟수를 줄이는 IDE 쪽 — 그리고 여기서 제일 흔한 착각

### HotSwap 은 changelog 를 다시 읽어 주지 않는다

IntelliJ 의 HotSwap 은 디버깅 세션 중 변경된 **클래스**를 다시 로드한다. 공식 문서가 밝힌 VM 차원의 제약은 이렇다.[^flow]

- **메서드 본문이 수정된 경우에만** 동작한다. 시그니처 변경은 지원되지 않는다.
- **클래스 멤버의 추가·삭제는 지원되지 않는다.**
- 수정한 메서드가 **이미 콜스택에 올라가 있으면**, 그 메서드를 빠져나온 뒤에야 변경이 반영된다. 그때까지 해당 프레임은 *obsolete* 로 표시된다.

여기서 조합의 성질이 나온다 — **changelog 는 클래스가 아니라 리소스이고, Liquibase 는 부팅 시점에 한 번 읽는다. 즉 changelog 수정은 HotSwap 대상이 아니며 재부팅이 필요하다.** (이 문장은 위 제약과 Liquibase 의 실행 시점에서 따라 나오는 결론이지, 한 문서에 그대로 적힌 문장은 아니다.)

그래서 실전 순서가 정해진다 — **자바 코드 수정과 changelog 수정을 같은 루프에 섞지 않는다.** 자바만 고치는 동안은 HotSwap 으로 계속 밀고, changelog 는 고칠 것을 모아서 한 번에 반영한다. 섞으면 매번 재부팅이라 HotSwap 의 이득이 통째로 사라진다.

### Reset Frame 은 DB 를 되돌리지 않는다

이게 마이그레이션 디버깅에서 제일 위험한 착각이다. IntelliJ 문서는 한 줄로 못박아 뒀다 — **"Reset Frame 은 지역 변수만 초기화한다. 애플리케이션의 전역 상태 변경은 되돌리지 않는다."**[^flow]

`CREATE TABLE` 이 이미 실행된 뒤에 프레임을 되감으면, 코드는 처음으로 돌아가지만 **테이블은 그대로 남아 있다.** 그 상태로 다시 실행하면 "이미 존재함" 으로 죽는다. 원인을 코드에서 찾다가 시간을 버리는 전형적인 자리다. DDL 이 나간 뒤에는 프레임이 아니라 **DB 를 되돌려야 한다.**

### 재부팅을 부르지 않고 조건을 만드는 세 가지

- **조건부·임시 브레이크포인트** — 100번째 반복에서만 멈추려고 카운터 변수를 넣고 재부팅하는 대신 조건을 건다. 임시 브레이크포인트(`Ctrl+Alt+Shift+F8`)는 한 번 걸리면 스스로 사라진다.[^breakpoints]
- **비중단 브레이크포인트로 상태 바꾸기** — 브레이크포인트 속성에서 **Suspend 체크를 풀고** *Evaluate and log* 에 식을 넣으면, 멈추지 않으면서 변수를 수정한다. 공식 문서가 "디버깅할 때만 쓰고 싶은 로직을 넣는 용도" 로 예시까지 들어 둔 기능이다.[^flow]
- **Force return** — 메서드가 `return` 에 닿기 전에 임의의 값을 반환시킨다. 반환값을 만드는 과정이 아니라 **반환값을 받는 쪽**이 문제일 때, 그 조건을 재현하려고 데이터를 만들 필요가 없어진다.[^flow]
- **필드 워치포인트** — 특정 필드가 읽히거나 쓰일 때 중단한다. 다만 **리플렉션을 통한 필드 변경에는 동작하지 않는다.**[^breakpoints] 프레임워크가 값을 꽂는 지점을 쫓을 때 이 예외를 모르면 "안 걸리네" 로 끝난다.

---

## 5. 마이그레이션 코드 자체에 브레이크포인트를 거는 법

SQL·XML·YAML changeset 에는 브레이크포인트를 걸 수 없다. 그건 내 코드가 아니라 데이터다. 하지만 **`customChange` 는 다르다.**

Liquibase 의 `customChange` 는 `liquibase.change.custom.CustomTaskChange` 또는 `CustomSqlChange` 를 구현한 **내 자바 클래스**를 changeset 안에서 실행한다.[^customchange] 그러면 브레이크포인트를 걸 자리가 생긴다.

- `CustomTaskChange` → **`execute(Database database)`** 안에서 직접 실행된다. 여기에 브레이크포인트를 걸면 `Database` 객체째로 들여다볼 수 있다.
- `CustomSqlChange` → **`generateStatements(Database database)`** 는 실행하지 않고 statement 를 만들어 반환한다. **무엇이 나갈지**를 나가기 전에 확인하고 싶을 때 이쪽이 맞다.
- 그 밖에 `validate(Database)`, `setUp()`, `setFileOpener(ResourceAccessor)` 도 인터페이스가 정의한 훅이라 브레이크포인트를 걸 수 있다.

주의를 하나 붙인다 — **디버깅이 편하다고 일반 DDL 을 `customChange` 로 옮기라는 말이 아니다.** 선언적 changeset 을 자바 코드로 바꾸는 건 [앞 글]({% post_url 2026-09-14-liquibase-vs-flyway-change-identity %})에서 말한 Liquibase 의 장점(변경을 기술하면 도구가 SQL 을 만든다)을 스스로 버리는 일이다. 이 절은 **이미 `customChange` 가 있는 코드베이스**를 위한 것이다.

단순히 "무슨 SQL 이 나가는지" 만 알고 싶은 거라면 브레이크포인트가 아니라 `update-sql` 류의 미리보기가 정답이다. 실행하지 않고 SQL 만 뽑는 게 목적인데 디버거로 프로세스를 세우는 건 도구를 잘못 고른 것이다.

---

## 6. IntelliJ 의 Liquibase 지원 — 2024.1 이후로 기본 탑재다

의외로 덜 알려진 부분이다. JetBrains 공식 문서에 따르면, **IntelliJ IDEA 2024.1 이전에는 일부 Liquibase 기능이 JPA Buddy 플러그인에서만 제공됐고, 지금은 Liquibase 플러그인으로 제공된다.** 활성화 조건은 단순히 **프로젝트에 Liquibase 의존성이 있을 것**이다.[^ideaLiquibase]

쓸 만한 건 changelog 생성 쪽이다.

- **Persistence 툴 윈도우** → 퍼시스턴스 유닛이나 엔티티 우클릭 → **New | Liquibase Init Changelog**
- 생성 기준을 **Model(퍼시스턴스 유닛의 엔티티 매핑)** 과 **DB(연결된 데이터베이스의 스키마)** 중에 고른다
- **Changelog Preview** 창에서 저장 위치·파일명, 출력 형식(YAML/JSON/SQL/XML), 그리고 다른 changelog 에 넣을 **include / include folder / include context** 를 지정한다
- 미리보기 왼쪽에서 각 변경을 클릭해 결과를 보고, **드래그로 여러 변경을 한 changeset 으로 합치거나 무시**할 수 있다

마지막 항목이 실질적으로 중요하다. 자동 생성된 changelog 의 문제는 항상 **입자 크기**다 — 도구는 변경 하나당 changeset 하나를 뽑는데, 롤백 단위로는 그게 너무 잘다. 그걸 저장 전에 합칠 수 있게 해 뒀다는 게 이 UI 의 값어치다. 어느 쪽이든 **생성물은 초안이지 결과물이 아니다.** 사람이 읽고 손보는 단계는 빠지지 않는다.

---

## 7. 정리 — 루프를 줄이는 체크리스트

**설정으로 한 번만 해 두는 것**

1. changelog 디렉터리에 저장 시 자동 포맷·후행 공백 제거가 적용되지 않게 한다 (체크섬 깨짐의 최대 원인)
2. 로컬 전용 changeset 에는 `context="@..."` 를 쓴다. `@` 없이 쓰면 필터 미지정 시 **그냥 다 돈다**
3. `spring.jpa.hibernate.ddl-auto` 를 명시값으로 박는다
4. `liquibase.exception.*` 예외 브레이크포인트를 만들어 두고 평소엔 꺼 둔다

**루프를 돌 때**

5. 자바 수정과 changelog 수정을 **같은 루프에 섞지 않는다.** changelog 는 HotSwap 이 안 된다
6. DDL 이 나간 뒤에는 Reset Frame 으로 되돌리려 하지 않는다. **DB 를 되돌린다**
7. 조건 재현은 데이터가 아니라 조건부 브레이크포인트·비중단 브레이크포인트·Force return 으로 만든다
8. `customChange` 가 있으면 `execute()` / `generateStatements()` 가 브레이크포인트 자리다

**꼬였을 때**

9. 내용이 어긋났으면 `clear-checksums` (단, 대기 중 changeset 은 배포된다)
10. 존재가 어긋났으면 `changelog-sync`
11. 둘 다 로컬 전용이다

한 줄 요약 — **Liquibase 설정을 아무리 다듬어도 줄어드는 건 부팅 몇 초지만, changelog 를 건드리는 횟수를 줄이면 재부팅 자체가 사라진다.** 디버거의 값어치는 빠르게 보는 데 있는 게 아니라, **다시 띄우지 않아도 되게 만드는** 데 있다.

---

## 근거의 한계

- 위 기법들의 **정량적 효과(몇 초 절약, 몇 배 빠름)는 측정하지 않았고 인용하지 않았다.** 프로젝트 규모·changelog 개수·DB 종류에 따라 갈리며, 이 조합에 대한 중립적 벤치마크는 찾지 못했다.
- `spring.liquibase.enabled=false` 일 때 Hibernate 의 `ddl-auto` 기본값이 어느 쪽으로 결정되는지는 **실측하지 않았다.** 그래서 단언 대신 명시 설정을 권했다.
- "changelog 는 HotSwap 대상이 아니다" 는 HotSwap 의 문서화된 제약과 Liquibase 의 실행 시점에서 따라 나오는 추론이며, 한 문서에 그대로 적힌 문장이 아니다.
- IntelliJ 의 Liquibase 기능은 에디션·버전에 따라 제공 범위가 다를 수 있다. 위 내용은 JetBrains 온라인 도움말의 Liquibase 문서 기준이다.

---

## References

[^changeset]: Liquibase 공식 문서 — [What is a Changeset?](https://docs.liquibase.com/concepts/changelogs/changeset.html) (`author:id` + changelog 파일 경로로 유일 식별, `runAlways`/`runOnChange`, 기본 트랜잭션 동작)
[^checksum]: Liquibase 공식 문서 — [What is a Changeset checksum?](https://docs.liquibase.com/concepts/changelogs/changeset-checksums.html) (파일 체크섬이 아님, 접두 자리의 조용한 갱신, 4.22.0 의 공백 처리 변경)
[^clearchecksums]: Liquibase 공식 문서 — [clear-checksums](https://docs.liquibase.com/commands/utility/clear-checksums.html)
[^changelogsync]: Liquibase 공식 문서 — [changelog-sync](https://docs.liquibase.com/commands/utility/changelog-sync.html)
[^contexts]: Liquibase 공식 문서 — [What are contexts?](https://docs.liquibase.com/concepts/changelogs/attributes/contexts.html) (필터 미지정 시 컨텍스트가 붙은 changeset 도 실행됨, `@` 접두의 의미, 논리 연산자)
[^customchange]: Liquibase 공식 문서 — [customChange](https://docs.liquibase.com/change-types/custom-change.html) (`CustomTaskChange.execute()` vs `CustomSqlChange.generateStatements()`)
[^breakpoints]: JetBrains 공식 문서 — [Breakpoints | IntelliJ IDEA](https://www.jetbrains.com/help/idea/using-breakpoints.html) (예외 브레이크포인트, 필드 워치포인트의 리플렉션 제약, 임시 브레이크포인트)
[^flow]: JetBrains 공식 문서 — [Alter the program's execution flow | IntelliJ IDEA](https://www.jetbrains.com/help/idea/altering-the-program-s-execution-flow.html) (HotSwap 제약, Reset Frame 이 전역 상태를 되돌리지 않음, 비중단 브레이크포인트, Force return)
[^ideaLiquibase]: JetBrains 공식 문서 — [Liquibase | IntelliJ IDEA](https://www.jetbrains.com/help/idea/liquibase.html) (2024.1 이전 JPA Buddy, Init Changelog, Changelog Preview)
[^bootdata]: Spring Boot 공식 레퍼런스 — [Database Initialization](https://docs.spring.io/spring-boot/how-to/data-initialization.html) (`ddl-auto` 기본값 결정 규칙, `spring.liquibase.enabled`, `context:@test` + `spring.liquibase.contexts=test` 권장, 초기화 방식 혼용 불가)
