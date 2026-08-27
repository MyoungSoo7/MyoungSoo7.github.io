---
layout: post
title: "마이그레이션의 정답지는 어디서 오는가 — Spring Boot → NestJS 사례를 읽고"
date: 2026-08-27 16:22:44 +0900
categories: [engineering]
tags: [migration, testing, jdbc, timezone, hibernate, nestjs, spring-boot]
---

Toby's Codex 에 [Spring Boot 백엔드를 NestJS 로 옮긴 기록](https://codex.epril.com/migrating-spring-boot-to-nestjs/)이 올라왔다. 개인 블로그의 백엔드를 통째로 갈아엎은 1인 마이그레이션 회고인데, 읽고 나서 계속 남은 건 이 문장이었다.

> "정답지는 원본이 살아 있을 때만 뽑을 수 있다"
> — Toby's Codex, 「9시간이 사라질 뻔했다」

테스트 이야기가 아니다. **오라클(oracle) 문제**다.

## 테스트는 정답지가 아니다

소프트웨어 테스팅에서 "무엇이 옳은 출력인가" 를 판정해 주는 근거를 오라클이라고 부른다. 우리가 평소에 쓰는 단위 테스트는 오라클을 *내가 손으로 적어 넣은* 것이다. `assertEquals(expected, actual)` 의 `expected` 는 결국 내 머릿속에서 나왔다.

여기에 마이그레이션의 함정이 있다. 새 시스템을 짜면서 테스트도 같이 짜면, 나는 **내가 이해한 명세**와 **내가 구현한 코드**를 비교하는 것이지, **원래 돌던 시스템의 실제 동작**과 비교하는 게 아니다. 원문에서 테스트 234개가 전부 초록불인데도 응답 날짜가 9시간 어긋나 있었던 이유가 정확히 이것이다. 새 시스템은 자기 기준으로 완벽하게 일관적이었다.

반면 아직 살아 있는 구 시스템은 오라클을 *생성*한다. 명세에 안 적힌 것, 문서가 틀리게 적어놓은 것, 아무도 의도하지 않았지만 사용자가 이미 그렇게 알고 있는 것까지 전부 포함해서.

원문의 두 장치는 정확히 이 성질을 쓴다.

- **골든 파일** — 순수 함수의 입출력 쌍을 구 시스템에서 뽑아 고정한다. 정적 오라클.
- **섀도우 diff** — 두 백엔드를 나란히 세우고 같은 요청을 쏴서 비교한다. 동적 오라클.

두 번째는 GitHub 이 2014년에 [Scientist](https://github.com/github/scientist) 라는 라이브러리로 만들어 둔 패턴과 같은 발상이다. 기존 경로를 `use`(control), 새 경로를 `try`(candidate) 로 감싸 둘 다 실행하고 결과를 비교하되, 반환값은 언제나 control 것을 쓴다. 다만 Scientist 는 **반환값 비교**가 기본이다 — README 도 "Scientist compares control and candidate values using `==`" 라고 못박는다. 원문이 부작용(DB 상태)까지 비교하려고 DB 를 두 벌로 갈라놓은 건 그 한계를 알고 한 설계다.

왜 그게 필요했는지는 JPA 를 써 본 사람이면 안다. 원문에 나오는 `save()` 없이 상태만 바꾸는 코드 23곳은 Hibernate 의 dirty checking 에 기대고 있다. Jakarta Persistence 는 영속성 컨텍스트가 관리하는 엔티티의 변경을 flush 시점에 DB 로 동기화하도록 규정하고, Hibernate 는 트랜잭션 커밋 시 자동 flush 를 건다([Hibernate ORM User Guide — Flushing](https://docs.jboss.org/hibernate/orm/6.6/userguide/html_single/Hibernate_User_Guide.html#flushing)). 이걸 명시적 `save()` 를 요구하는 ORM 으로 옮기면서 한 곳 빠뜨리면 — **에러가 안 난다. 200 이 나가고 본문도 정상이고 DB 만 안 바뀐다.** 응답 비교로는 절대 안 잡힌다.

## 9시간은 어디서 왔나 — 1차 문서로 뜯어보기

원문에서 제일 아찔한 발견은 타임존이었다. JDBC URL 에 `serverTimezone=Asia/Seoul` 이 붙어 있는데 컨테이너에 타임존 설정이 없어 JVM 은 UTC 로 돌고 있었다는 것. 원문은 원인만 짚고 넘어가는데, MySQL 공식 문서를 보면 왜 하필 **읽을 때만** 어긋나는지까지 설명이 된다.

Connector/J 의 [Datetime types processing](https://dev.mysql.com/doc/connector-j/en/connector-j-connp-props-datetime-types-processing.html) 문서에 세 개의 옵션이 맞물려 있다.

- `connectionTimeZone` — 커넥션 타임존. 기본값 `LOCAL`(= JVM 기본 타임존). 문서에 **"Former connection option `serverTimezone` is still valid as an alias of this one"** 이라고 적혀 있다. 즉 `serverTimezone=Asia/Seoul` 은 이 값을 서울로 바꾼 것이다.
- `preserveInstants` — 기본값 `true`. 켜져 있으면 드라이버가 시점(instant)을 보존하려고 변환을 한다. 문서: *"On retrieval, Connector/J converts the received value from the session time zone to the JVM default one."*
- `forceConnectionTimeZoneToSession` — 기본값 `false`. **`connectionTimeZone` 을 설정해도 서버 세션의 `time_zone` 변수는 바뀌지 않는다.**

조합하면 이렇다. 드라이버는 "세션은 서울" 이라고 믿고, JVM 기본은 UTC 다. 조회할 때 서울 → UTC 변환이 걸린다. **-9시간.** DB 에 `2026-08-09 08:59:25` 로 들어있는 값이 애플리케이션에서는 `2026-08-08 23:59:25` 로 보인다. 원문이 관측한 숫자와 정확히 일치한다.

그리고 세 번째 옵션이 기본 `false` 라는 점이 원문의 "읽을 때는 변환하는데 쓸 때는 변환하지 않는 비대칭" 을 설명한다. 세션 타임존은 손대지 않은 채 드라이버 쪽 변환만 걸리니, 값이 어느 경로로 들어가고 나오느냐에 따라 변환이 붙기도 하고 안 붙기도 한다. 같은 글의 작성 시각이 목록과 검색 결과에서 9시간 다르게 보였다는 대목도 같은 뿌리다.

여기서 배울 건 "타임존 조심해라" 가 아니다. **기본값 세 개가 조용히 맞물려서 만들어 낸 동작이 몇 년간 운영 서비스의 사실상 명세가 되어 있었다**는 것. 새 시스템이 DB 값을 정직하게 그대로 보여주는 순간 그게 회귀(regression)가 된다. 정직한 쪽이 틀린 게 되는 상황은 오라클을 구 시스템에서 뽑지 않으면 존재조차 알 수 없다.

## 버그까지 그대로 옮긴다는 결정

원문에서 가장 성숙하다고 느낀 판단은 따로 있다. 검색 API 만 타임존 변환을 안 타는 문제를 발견하고도 **고치지 않고 그대로 재현했다**는 것. 컷오버가 끝난 뒤에 고치기로 미리 정해뒀기 때문에.

이건 취향이 아니라 원칙에 가깝다. 마이그레이션 배포에서 "이식" 과 "개선" 을 섞으면, 사고가 났을 때 원인이 이식 실패인지 개선의 부작용인지 분리가 안 된다. 롤백 판단도 흐려진다. 동작 보존을 먼저 증명하고, 개선은 다음 배포로 미루는 것 — 리팩터링에서 "한 번에 하나만 바꾼다" 와 같은 규율이다.

## 나에겐 정답지가 없었다

이 글을 읽은 날, 나는 정확히 반대편 사례를 손에 들고 있었다. 다른 프로젝트에서 `.gitignore` 에 앵커 없는 `out/` 한 줄이 들어 있었고, 헥사고날 구조라 소스 디렉터리 이름이 하필 `out` 이었다. `git add` 가 아웃바운드 어댑터를 **전부** 조용히 무시하고 있었다. 에러도 경고도 없이. 클론해서 빌드를 걸어보고 나서야 알았다.

차이는 여기다. 원문의 저자에게는 구 시스템이 아직 살아 있었다. 나에게는 원본이 이미 없다. 정답지를 뽑을 창(窓)이 닫힌 뒤에 문제를 발견한 것이다.

원문의 교훈을 뒤집으면 이렇게 된다. **원본을 지우는 순간 오라클도 같이 지워진다.** 지우기 전에 뽑아 두는 비용은 몇 시간이고, 안 뽑았을 때의 비용은 "원래 뭐였는지 아무도 모르는 상태에서 다시 만들기" 다. 조용한 실패에 대해서는 [전에도](/2026/08/02/silent-failures-six-of-them/) 쓴 적이 있는데, 그때 정리하지 못한 조각이 이거였다 — 신호가 없는 실패를 잡는 유일한 방법은 감시를 늘리는 게 아니라 **비교 대상을 확보하는 것**이다.

---

**출처 등급에 대해.** 원문에 나오는 수치(코드 9,000줄, 컨테이너 메모리 595MB → 220MB, 컷오버 18초 등)는 저자 본인의 1인 프로젝트 자기 보고이며 제3자 재현이나 중립 벤치마크가 아니다. 이 글은 그 숫자를 성능 우열의 근거로 쓰지 않았고, 검증 *방법론* 과 그 안에서 관측된 동작만 다뤘다. Spring Boot 와 NestJS 의 메모리 특성을 일반화하려면 별도의 통제된 측정이 필요하다. 반면 JDBC 드라이버 동작과 JPA flush 규정은 벤더 공식 문서를 1차 출처로 확인했다.

## References

- Toby's Codex, 「9시간이 사라질 뻔했다 — Spring Boot 백엔드를 NestJS로 옮긴 이야기」 (2026-08-27) — <https://codex.epril.com/migrating-spring-boot-to-nestjs/>
- MySQL, *Connector/J Developer Guide* §6.3.11 Datetime types processing (`connectionTimeZone` / `preserveInstants` / `forceConnectionTimeZoneToSession`) — <https://dev.mysql.com/doc/connector-j/en/connector-j-connp-props-datetime-types-processing.html>
- Hibernate ORM 6.6, *User Guide* — Flushing — <https://docs.jboss.org/hibernate/orm/6.6/userguide/html_single/Hibernate_User_Guide.html#flushing>
- Jakarta Persistence 3.2 Specification — <https://jakarta.ee/specifications/persistence/3.2/>
- GitHub, *Scientist* — A library for carefully refactoring critical paths — <https://github.com/github/scientist>
