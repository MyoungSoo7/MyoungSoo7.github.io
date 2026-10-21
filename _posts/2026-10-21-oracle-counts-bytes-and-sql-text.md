---
layout: post
title: "오라클은 글자를 세지 않는다 — VARCHAR2 의 바이트 길이와, SQL 을 글자 그대로 기억하는 공유 풀"
date: 2026-10-21 22:51:56 +0900
categories: [Engineering, Database]
tags: [Oracle, VARCHAR2, NLS_LENGTH_SEMANTICS, Bind Variable, Hard Parse, CURSOR_SHARING, MyBatis]
---

다른 DB 에서 오라클로 넘어오면 먼저 데는 건 대개 두 가지다. 빈 문자열이 NULL 이 된다는 것, `ROWNUM` 이 정렬보다 먼저 매겨진다는 것. 둘 다 [이전 글]({% post_url 2026-08-12-oracle-mysql-mariadb-tibero-comparison %})에서 다뤘다.

이 글은 그다음에 데는 두 가지를 다룬다. 겉으로는 서로 관계없어 보이지만 뿌리는 같다. **오라클은 사람이 생각하는 단위로 세지 않는다.**

- 컬럼 길이는 **글자가 아니라 바이트**로 센다. 그래서 `VARCHAR2(10)` 에 한글 10자가 들어가지 않는다.
- SQL 문은 **의미가 아니라 글자 그대로** 비교한다. 그래서 값만 바뀐 SQL 천 개는 오라클에게 서로 다른 SQL 천 개다.

둘 다 문법 에러가 나지 않는다. 개발 환경에선 멀쩡하다가 운영 데이터나 운영 트래픽이 들어와야 드러난다.

## 1. `VARCHAR2(10)` 은 "10글자" 가 아니다

### 기본값이 BYTE 다

`VARCHAR2(10)` 의 10 이 무엇을 세는지는 `NLS_LENGTH_SEMANTICS` 파라미터가 정한다. 오라클 레퍼런스에 적힌 기본값은 이렇다.[^nlslen]

> Default value: `BYTE`

`BYTE` 면 길이를 바이트로 재고, `CHAR` 면 글자 수로 잰다. 이 설정은 `VARCHAR2`·`CHAR` 컬럼과 PL/SQL 변수에 적용된다. 아무것도 안 건드리고 `VARCHAR2(10)` 을 만들면 **10바이트짜리 컬럼**이 생긴다.

### 한글 한 글자는 UTF-8 에서 3바이트다

요즘 오라클은 대개 데이터베이스 문자셋을 `AL32UTF8`(오라클의 UTF-8)로 만든다. UTF-8 에서 몇 바이트를 쓰는지는 코드 포인트 구간으로 정해져 있다. RFC 3629 의 표에서 `U+0800`~`U+FFFF` 구간은 3바이트다.[^rfc3629]

> `0000 0800-0000 FFFF | 1110xxxx 10xxxxxx 10xxxxxx`

한글 음절(가~힣)은 `U+AC00`~`U+D7A3` 이므로[^unicodehangul] 전부 이 구간에 들어간다. **한글 한 글자 = 3바이트**다.

그러면 계산은 단순하다.

| 넣는 값 | 바이트 | `VARCHAR2(10)` (BYTE) |
|---|---|---|
| `abcdefghij` (영문 10자) | 10 | 들어간다 |
| `홍길동` (한글 3자) | 9 | 들어간다 |
| `홍길동전` (한글 4자) | 12 | **실패** |

영문 테스트 데이터로는 절대 안 터진다. 운영에서 한글 이름이 들어오는 순간 터진다.

### 터질 때 나오는 에러

이때 나오는 게 `ORA-12899` 다.[^ora12899]

> value too large for column string (actual: string, maximum: string)

에러 문서에 중요한 단서가 하나 더 있다.

> Note that widths are reported in characters if character length semantics are in effect for the column, otherwise widths are reported in bytes.

즉 `(actual: 12, maximum: 10)` 이 찍혔다면 그 12 와 10 은 **바이트**다. "4글자 넣었는데 왜 12냐" 고 헷갈리면 이 줄을 보면 된다.

### 고치는 법 — 컬럼에 단위를 적는다

컬럼을 만들 때 단위를 명시하면 세션 설정과 무관하게 의도가 고정된다.

```sql
CREATE TABLE member (
  name  VARCHAR2(10 CHAR),   -- 10글자
  code  VARCHAR2(10 BYTE)    -- 10바이트 (ASCII 코드값 등)
);
```

"그럼 인스턴스 기본값을 `CHAR` 로 바꾸면 되지 않나" 싶은데, 오라클 문서가 이걸 명시적으로 말린다.[^nlslen]

> Oracle strongly recommends that you do NOT set the `NLS_LENGTH_SEMANTICS` parameter to `CHAR` in the instance or server parameter file.

이유도 적혀 있다. 기존 설치 스크립트들이 예상치 못하게 글자 단위 컬럼을 만들어 런타임 에러나 버퍼 오버플로가 날 수 있다는 것이다. 단위는 **전역 설정이 아니라 DDL 에 적는 것**이 맞다.

참고로 `NCHAR`, `NVARCHAR2`, `CLOB`, `NCLOB` 은 이 설정과 상관없이 항상 글자 단위다.[^nlslen]

## 2. 오라클은 SQL 을 글자 그대로 기억한다

### 하드 파싱과 소프트 파싱

오라클은 SQL 을 실행하기 전에 공유 풀(shared pool)에 같은 SQL 이 이미 있는지 찾는다. 있으면 재사용하고, 없으면 새로 만든다. SQL 튜닝 가이드의 정의는 이렇다.[^sqlproc]

> If Oracle Database cannot reuse existing code, then it must build a new executable version of the application code. This operation is known as a **hard parse**, or a **library cache miss**.

> A **soft parse** is any parse that is not a hard parse.

하드 파싱이 왜 비싼지도 같은 문서에 있다. 하드 파싱 동안 라이브러리 캐시와 데이터 딕셔너리 캐시를 여러 번 들여다보고, 그때마다 **래치(latch)** 라는 직렬화 장치를 잡는다.

> Latch contention increases statement execution time and decreases concurrency.

한 건만 보면 티가 안 난다. 동시에 수백 개가 하드 파싱하면 래치를 서로 기다리느라 CPU 는 놀고 응답은 느려진다.

### "같은 SQL" 의 기준은 글자 하나하나다

문제는 오라클이 무엇을 "같다" 고 보느냐다. 커서 공유 문서의 기준은 엄격하다.[^cursor]

> For a textual match to occur, the text of the SQL statements or PL/SQL blocks must be character-for-character identical, including spaces, case, and comments.

공백, 대소문자, 주석까지 같아야 한다. 그러니 값만 다른 두 SQL 은 당연히 다른 SQL 이다. 문서가 직접 든 예다.

```sql
SELECT count(1) FROM employees WHERE manager_id = 121;
SELECT count(1) FROM employees WHERE manager_id = 247;
```

> Usually, SQL statements that differ only in literals cannot use the same shared SQL area.

회원 번호로 조회하는 화면이 있고, 그 번호를 SQL 문자열에 이어 붙인다면 **회원 수만큼 서로 다른 SQL** 이 공유 풀에 쌓이고, 매번 하드 파싱한다. 오라클 Real-World Performance 그룹의 평가는 짧다.[^cursor]

> applications that use literals are a frequent cause of performance, scalability, and security problems.

성능만이 아니라 **보안(security)** 이 같은 문장에 들어 있다는 게 핵심이다. 값을 문자열로 이어 붙이는 코드는 곧 SQL 인젝션 코드이기 때문이다.

### 바인드 변수 — 값은 SQL 바깥으로

해법은 값을 SQL 텍스트에서 빼내는 것이다.

```sql
SELECT count(1) FROM employees WHERE manager_id = :mgr_id;
```

이러면 SQL 텍스트는 하나로 고정되고, 값만 실행할 때마다 바뀐다. 문서 표현으로는:[^cursor]

> When identical statements use bind variables, Oracle Database can take advantage of cursor sharing, and share the plan and other information when different values are bound to the same statement.

문서의 예제에서는 서로 다른 값 세 개(101, 120, 165)로 실행해도 공유 풀에는 SQL 하나만 남고 `VERSION_COUNT` 는 1이었다.

### 자바에서는 어디가 갈림길인가

애플리케이션 코드에서 이 차이는 한 글자로 갈린다.

- JDBC: `Statement` 에 문자열을 이어 붙이면 리터럴, `PreparedStatement` 의 `?` 는 바인드다.
- MyBatis: `#{}` 와 `${}` 다. 공식 문서에 따르면 `#{}` 는 `PreparedStatement` 파라미터(`?`)로 값을 넣고, `${}` 는 "MyBatis won't modify or escape the string" — 문자열을 그대로 SQL 에 박는다.[^mybatis]

MyBatis 문서도 `${}` 에 사용자 입력을 넣는 건 SQL 인젝션으로 이어진다고 경고한다. 즉 `${}` 는 정렬 컬럼명처럼 **바인드할 수 없는 자리**에, 화이트리스트로 검증한 값만 쓰는 도구다. 조회 조건 값에 `${}` 가 보이면 오라클에선 하드 파싱 문제이고, 어느 DB 에서든 보안 문제다.

### 공유 풀에서 직접 확인하기

리터럴 SQL 이 쌓이고 있는지는 `V$SQL` 에서 보인다. 앞부분이 같은 SQL 이 여러 줄이고 각각 실행 횟수가 1 근처라면 리터럴로 찍어내고 있다는 뜻이다.

```sql
SELECT sql_text, executions, parse_calls
  FROM v$sql
 WHERE sql_text LIKE 'SELECT count(1) FROM employees WHERE manager_id%'
 ORDER BY last_active_time DESC
 FETCH FIRST 20 ROWS ONLY;
```

### `CURSOR_SHARING=FORCE` 는 반창고다

코드를 당장 못 고칠 때 쓰는 스위치가 있다. `CURSOR_SHARING` 을 `FORCE` 로 두면 오라클이 리터럴을 시스템이 만든 바인드 변수로 바꿔 친다.[^cursor] 그런데 문서는 이걸 쓰라고 하지 않고, 쓰지 말아야 할 이유를 길게 적는다.

- 파싱 횟수 자체는 줄지 않는다. 하드 파싱을 소프트 파싱으로 바꿔 줄 뿐이다.
- SQL 인젝션은 **막지 못한다.** 값이 바인드로 바뀌는 건 인젝션이 이미 일어난 뒤이기 때문이다.
- 비슷한 문장을 찾느라 소프트 파싱에 일이 더 붙는다.
- 모든 리터럴을 지우니 옵티마이저가 쓸 수 있던 정보까지 사라져 실행 계획이 나빠질 수 있다.

권장 사항은 분명하다.

> The best practice is to write sharable SQL and use the default of `EXACT` for `CURSOR_SHARING`.

`FORCE` 를 써야 한다면 조건도 붙어 있다. 공유 풀의 문장들이 리터럴만 다르고, 라이브러리 캐시 미스로 응답 시간이 실제로 나쁘고, 소스를 고칠 때까지 임시로 쓰는 것이며, **인스턴스가 아니라 세션 단위로** 설정할 것.[^cursor] `NLS_LENGTH_SEMANTICS` 와 똑같은 결론이다 — 전역 스위치로 덮지 말고 원인을 고쳐라.

## 정리

| | 오라클이 세는 단위 | 증상 | 고치는 곳 |
|---|---|---|---|
| 컬럼 길이 | 바이트 (기본 `BYTE`) | 한글 데이터에서 `ORA-12899` | DDL 에 `CHAR`/`BYTE` 명시 |
| SQL 동일성 | 글자 그대로 (공백·대소문자·주석 포함) | 트래픽이 늘면 하드 파싱·래치 경합 | 바인드 변수 (`PreparedStatement`, `#{}`) |

둘 다 **전역 설정으로 덮지 말라**는 게 오라클 문서 자신의 권고다. `NLS_LENGTH_SEMANTICS=CHAR` 를 인스턴스에 걸지 말 것, `CURSOR_SHARING=FORCE` 를 인스턴스에 걸지 말 것. 단위는 DDL 에, 값은 바인드에 — 원인이 있는 자리에서 고친다.

## References

[^nlslen]: Oracle, _Oracle Database Reference 23ai_, "NLS_LENGTH_SEMANTICS". <https://docs.oracle.com/en/database/oracle/oracle-database/23/refrn/NLS_LENGTH_SEMANTICS.html>
[^rfc3629]: F. Yergeau, _RFC 3629: UTF-8, a transformation format of ISO 10646_, Section 3. <https://www.rfc-editor.org/rfc/rfc3629#section-3>
[^unicodehangul]: The Unicode Consortium, "Hangul Syllables" code chart (U+AC00–U+D7AF). <https://www.unicode.org/charts/PDF/UAC00.pdf>
[^ora12899]: Oracle, _Database Error Messages_, "ORA-12899". <https://docs.oracle.com/en/error-help/db/ora-12899/>
[^sqlproc]: Oracle, _SQL Tuning Guide 23ai_, "SQL Processing". <https://docs.oracle.com/en/database/oracle/oracle-database/23/tgsql/sql-processing.html>
[^cursor]: Oracle, _SQL Tuning Guide 23ai_, "Improving Real-World Performance Through Cursor Sharing". <https://docs.oracle.com/en/database/oracle/oracle-database/23/tgsql/improving-rwp-cursor-sharing.html>
[^mybatis]: MyBatis, "Mapper XML Files — String Substitution". <https://mybatis.org/mybatis-3/sqlmap-xml.html>
