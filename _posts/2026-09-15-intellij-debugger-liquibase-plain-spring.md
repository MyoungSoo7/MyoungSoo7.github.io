---
layout: post
title: "인텔리제이 디버거와 Liquibase, 부트 없이 — 순수 스프링에서는 루프의 축이 바뀐다"
date: 2026-09-15 22:17:27 +0900
categories: [Engineering, Database]
tags: [IntelliJ, Liquibase, Spring, 디버깅, HotSwap, 생산성]
---

[앞 글]({% post_url 2026-09-15-intellij-debugger-liquibase-fast-loop %})에서 인텔리제이 디버거와 Liquibase 조합의 루프 비용을 다뤘는데, 그 글은 스프링부트를 전제했다 — `spring.liquibase.*` 프로퍼티, 스타터가 붙여 주는 자동 실행. 이번 글은 같은 주제를 **부트가 없는 순수 스프링 프레임워크**에서 다시 푼다.

결론부터: 순수 스프링이라고 루프가 더 느린 게 아니다. **축이 다를 뿐이다.** 부트에서는 자동구성이 정해 놓은 실행 시점을 프로퍼티로 조절했다면, 순수 스프링에서는 **실행 시점 자체가 내 코드다.** 그 차이가 디버깅 루프에서 어디에 유리하고 어디에 불리한지가 이 글의 내용이다.

앞 글과 같은 식을 다시 쓴다.

$$T_{loop} = T_{build} + T_{boot} + T_{migrate} + T_{repro}, \qquad T_{total} = n \times T_{loop}$$

부트 없는 환경의 특이점 두 개가 이 식을 바꾼다 — ① $T_{migrate}$ 를 **0 으로 만들 수 있다** (마이그레이션을 부팅에서 떼어낼 수 있으므로), ② 외장 서블릿 컨테이너에 war 를 얹는 구조라면 $T_{boot}$ 에 **재배포 비용이 추가된다.** 하나는 유리하고 하나는 불리하다. 순서대로 간다.

> 확인한 문서 버전: SpringLiquibase 는 Liquibase 공식 javadoc 5.0.3, Maven 플러그인은 공식 문서 Community 5.0.4, IntelliJ IDEA 는 현재 온라인 도움말, Spring Framework 는 현행 레퍼런스다.

---

## 1. 부트가 없으면 자동구성 대신 빈이 있다

Liquibase 는 부트 없이도 스프링 통합을 자체 제공한다 — `liquibase.integration.spring.SpringLiquibase`. 공식 javadoc 의 정의는 이렇다: *"A Spring-ified wrapper for Liquibase"* 이고, 빈으로 등록하면 **스프링 컨텍스트가 초기화될 때 자동으로 실행된다.**[^springliquibase] javadoc 이 직접 싣고 있는 예시:

```xml
<bean id="myLiquibase" class="liquibase.integration.spring.SpringLiquibase">
    <property name="dataSource" ref="myDataSource" />
    <property name="changeLog" value="classpath:db-changelog.xml" />
</bean>
```

실행 메커니즘도 javadoc 에 그대로 적혀 있다 — 이 클래스는 `InitializingBean` 을 구현하고, `afterPropertiesSet()` 이 *"Executed automatically when the bean is initialized"* 다.[^springliquibase] 즉 **마이그레이션의 실행 시점 = 이 빈의 초기화 시점**이고, 그 시점은 빈 정의 순서·의존 관계로 내가 정한다. 부트에서는 자동구성이 "DataSource 다음, JPA 이전" 을 알아서 보장해 줬지만, 순수 스프링에서는 **`depends-on` 을 내가 걸어야** JPA 의 스키마 검증보다 마이그레이션이 먼저 돈다. 이걸 빼먹으면 "가끔 기동 순서에 따라 검증이 실패하는" 재현 안 되는 버그가 된다.

빈 프로퍼티 목록이 곧 조절판이다. javadoc 의 필드 목록에서 디버깅 루프와 직결되는 것만 뽑으면:[^springliquibase]

| 프로퍼티 | 역할 |
| --- | --- |
| `shouldRun` | false 면 이 빈은 아무것도 안 한다 — 부팅과 마이그레이션의 분리 스위치 (2절) |
| `contexts` | 부트의 `spring.liquibase.contexts` 에 해당 (3절) |
| `dropFirst` | **업데이트 전에 DB 를 드롭한다** |
| `clearCheckSums` | **부팅할 때마다 체크섬을 지운다** |
| `testRollbackOnUpdate` | update 때 롤백을 같이 테스트 |
| `parameters` | changelog 파라미터 주입 |

경고 하나를 진하게 적는다 — `dropFirst` 와 `clearCheckSums` 가 **부팅 경로의 빈 프로퍼티로 존재한다.** 로컬 편의로 켜 둔 설정이 환경 분기 실수로 운영 컨텍스트에 딸려 가면, 전자는 데이터를 지우고 후자는 [앞 글]({% post_url 2026-09-15-intellij-debugger-liquibase-fast-loop %})에서 말한 "검증을 끄는 행위" 를 매 부팅마다 한다. 순수 스프링의 통제권은 이런 자유까지 포함한다. 프로파일별 빈 정의를 나눌 때 이 두 개는 반드시 로컬 쪽에만 있어야 한다.

---

## 2. 제일 큰 이득 — $T_{migrate}$ 를 부팅에서 떼어낸다

부트의 스타터는 "부팅하면 마이그레이션이 돈다" 를 기본값으로 준다. 순수 스프링은 그 결합 자체를 선택할 수 있다 — **`shouldRun=false` 로 부팅에서 빼고, 마이그레이션은 Maven 플러그인으로 밖에서 돌린다.**

```bash
mvn liquibase:update
```

Maven `update` goal 의 공식 문서가 이 워크플로우의 근거다: changelog 의 미배포 changeset 을 `id`·`author`·파일 경로로 판정해 배포하며,[^maven-update] 디버깅 루프에 쓸 만한 조절 속성이 붙어 있다 — `liquibase.contexts`(컨텍스트 필터), `liquibase.changesToApply`(앞에서부터 N 개만 적용), `liquibase.toTag`(태그까지만 적용).[^maven-update] 특히 `changesToApply` 와 `toTag` 는 **"문제의 changeset 직전까지만 올린 DB"** 를 만들 때 유용하다 — 부트의 부팅 결합 방식에는 없는 종류의 정밀 조작이다.

이렇게 떼어내면 디버깅 루프가 이렇게 바뀐다:

- 앱 재시작은 이제 마이그레이션을 다시 타지 않는다. $T_{migrate}$ 가 루프에서 사라진다.
- changelog 를 고치는 루프는 **앱을 아예 안 띄우고** `mvn liquibase:update` ↔ 수정만 반복한다. 앞 글의 "자바 루프와 changelog 루프를 섞지 말라" 가, 여기서는 프로세스 차원에서 강제된다.
- 실패도 앱 부팅 로그가 아니라 Maven 출력에서 바로 본다.

정직한 대가도 적는다 — 부팅 결합의 원래 목적은 **"코드와 스키마가 항상 같이 간다"** 는 보장이다. 떼어내는 순간 그 보장은 배포 파이프라인이 대신 책임져야 한다. 그래서 이 분리는 **로컬 디버깅 루프의 최적화**이지, 운영 배포 구조를 바꾸라는 말이 아니다. 로컬은 `shouldRun=false`+플러그인, 운영은 파이프라인의 명시적 update 단계 — 이렇게 환경별로 갈라 두는 게 안전하다.

---

## 3. contexts — 개념은 같고, 꽂는 자리가 다르다

로컬 전용 시드 데이터를 컨텍스트로 거르는 전략은 [앞 글]({% post_url 2026-09-15-intellij-debugger-liquibase-fast-loop %}) 3절과 동일하고, `@` 접두의 의미와 "필터를 안 주면 컨텍스트 붙은 changeset 도 전부 돈다" 는 함정도 그대로다.[^contexts] 다른 건 값을 꽂는 자리뿐이다.

| 어디서 | 부트 | 순수 스프링 |
| --- | --- | --- |
| 부팅 결합 실행 | `spring.liquibase.contexts` 프로퍼티 | `SpringLiquibase` 빈의 `contexts` 프로퍼티[^springliquibase] |
| 빌드 도구 실행 | (해당 없음) | `mvn liquibase:update -Dliquibase.contexts=...`[^maven-update] |

Maven 문서도 같은 함정을 같은 문장으로 반복한다 — *"If a context is not specified, then all contexts will be executed."*[^maven-update] 빈 프로퍼티와 Maven 속성 **양쪽 다** 필터를 주는 걸 잊으면, 한쪽 경로로 돌 때만 시드가 다 들어가는 "가끔 다른 DB" 가 만들어진다. 2절처럼 실행 경로를 둘로 나눴다면 contexts 도 두 자리에 다 있어야 한다.

---

## 4. 외장 톰캣이라면 — 루프 비용의 왕은 재배포다

순수 스프링 프로젝트의 상당수는 내장 서버가 아니라 **외장 서블릿 컨테이너에 war** 를 얹는다. 이 구조에서 "고치고 다시 본다" 의 기본값은 재배포이고, 재배포는 컨텍스트 재초기화라서 1절의 `SpringLiquibase` 빈이 있다면 **마이그레이션까지 다시 탄다.** $T_{boot}$ 와 $T_{migrate}$ 가 한 덩어리로 루프에 들어오는 최악 조합이다.

IntelliJ 가 정확히 이 문제를 위한 조절판을 공식 문서로 제공한다 — **Update 액션의 정책**이다.[^update-policies] 서버 위에서 도는 앱을 수정할 때 "서버 재시작은 실용적이지 않다" 며 갱신 범위를 고르게 해 뒀고, 정책은 아티팩트 형태에 따라 갈린다:

| 정책 | 하는 일 | 아티팩트 |
| --- | --- | --- |
| Update resources | HTML·JSP·CSS 등 리소스만 아티팩트 디렉터리에 갱신 | exploded |
| **Update classes and resources** | 모듈 재컴파일 + 클래스·리소스 갱신. **디버그 모드면 클래스는 HotSwap 으로 JVM 안에서 교체된다** | exploded |
| Hot Swap classes | 재컴파일 + HotSwap. **디버그 모드 전용** | packaged |
| Redeploy | 아티팩트 재빌드 + 재배포 | 둘 다 |
| Restart server | 서버 재시작 + 재배포 | 둘 다 |

톰캣 런 구성 문서에 따르면 이 액션은 Run/Debug 툴 윈도우에서 `Ctrl+F10` 으로 호출하고, run 모드에서는 클래스를 출력 폴더에 복사만 할 뿐 실제 리로드 여부는 런타임 능력에 달려 있다고 명시돼 있다.[^tomcat-config] 즉 **최속 루프의 공식은 "exploded 아티팩트 + 디버그 모드 + Update classes and resources"** 다. 이 조합에서만 HotSwap 이 JVM 안의 클래스를 직접 갈아끼운다.

HotSwap 자체의 제약 — 메서드 본문만, 시그니처·멤버 변경 불가, 콜스택에 있는 메서드는 빠져나온 뒤 반영 — 은 [앞 글]({% post_url 2026-09-15-intellij-debugger-liquibase-fast-loop %}) 4절 그대로다.[^flow] 그리고 changelog 에 대한 결론도 같다: "Update resources" 가 changelog 파일을 아티팩트 디렉터리에 복사해 줘도, **Liquibase 는 컨텍스트 초기화 때 한 번 읽고 끝**이므로 살아 있는 앱에는 반영되지 않는다. changelog 반영은 재배포(=재초기화)거나, 2절처럼 아예 밖에서 `mvn liquibase:update` 로 돌리거나 둘 중 하나다. 후자 쪽이 루프가 짧다는 게 이 글의 요지다.

(참고 — 외장 서버 런 구성은 IntelliJ IDEA Ultimate 기능이다. Community 라면 4절의 조절판 없이 2절의 분리 전략이 사실상 유일한 루프 단축이다.)

---

## 5. 테스트 루프 — 컨텍스트 캐시는 부트 전유물이 아니다

"통합 테스트가 느린 건 부트가 없어서" 라는 말을 가끔 듣는데, 사실이 아니다. 컨텍스트 캐싱은 **Spring Framework 의 TestContext 프레임워크** 소관이라 순수 스프링에서 똑같이 작동한다. 공식 레퍼런스의 규칙:[^ctx-caching]

- 한 번 로드된 `ApplicationContext` 는 **static 캐시**에 저장되고, **같은 설정 조합**을 선언한 이후 테스트 전부가 재사용한다.
- 캐시 키는 설정 파라미터의 조합이다 — locations/classes, 프로파일, 프로퍼티 소스, 컨텍스트 초기화자 등. **하나라도 다르면 다른 컨텍스트가 새로 뜬다.**
- 캐시 크기 기본 32, LRU 축출. `spring.test.context.cache.maxSize` 로 조절.
- `@DirtiesContext` 는 캐시에서 컨텍스트를 제거하고 다음 테스트에서 재구축시킨다.

이게 Liquibase 와 만나는 지점이 핵심이다 — 테스트 컨텍스트에 1절의 `SpringLiquibase` 빈이 들어 있다면, **마이그레이션 실행 횟수 = 컨텍스트 로드 횟수**다. 캐시가 잘 맞으면 테스트 스위트 전체에서 마이그레이션은 한 번 돌고, 설정 조합이 테스트 클래스마다 미묘하게 다르면(프로파일 하나, 프로퍼티 하나 차이) 그 수만큼 컨텍스트가 뜨면서 **마이그레이션도 그 수만큼 돈다.** 통합 테스트가 느린 프로젝트에서 범인은 대개 테스트 코드가 아니라 캐시 미스다.

캐시를 조용히 죽이는 함정도 공식 문서에 명시돼 있다 — **캐시는 static 이라 프로세스가 갈리면 무효**다. Maven Surefire 의 forkMode 가 `always`/`pertest` 면 *"TestContext framework 는 테스트 클래스 간에 컨텍스트를 캐시할 수 없고, 빌드는 그만큼 크게 느려진다"* 고 레퍼런스가 직접 경고한다.[^ctx-caching] IDE 에서는 빠른데 빌드에서만 느리다면 fork 설정부터 본다.

---

## 6. 정리 — 순수 스프링 버전 체크리스트

**구조를 정할 때 (한 번)**

1. `SpringLiquibase` 빈에 `depends-on` 으로 JPA 보다 먼저 돌 순서를 명시한다
2. `dropFirst`·`clearCheckSums` 는 로컬 프로파일의 빈 정의에만 존재하게 한다
3. 로컬은 `shouldRun=false` + `mvn liquibase:update` 로 부팅과 마이그레이션을 분리한다
4. contexts 필터는 빈 프로퍼티와 Maven 속성 **두 자리 모두**에 준다

**루프를 돌 때**

5. changelog 루프는 앱 없이 Maven 플러그인만으로 돈다 — `changesToApply`·`toTag` 로 "문제 직전까지의 DB" 를 만든다
6. 외장 서버는 exploded + 디버그 + "Update classes and resources"(`Ctrl+F10`) 가 최속이다. Redeploy 는 마이그레이션까지 다시 태운다
7. HotSwap 제약과 Reset Frame 의 한계는 [부트 편]({% post_url 2026-09-15-intellij-debugger-liquibase-fast-loop %})과 동일하다

**테스트가 느릴 때**

8. 테스트 클래스 간 설정 조합을 통일해 컨텍스트 캐시를 맞춘다 — 캐시 미스 수 = 마이그레이션 실행 수
9. 빌드에서만 느리면 Surefire fork 설정을 본다

한 줄 요약 — **부트는 루프를 프로퍼티로 조절하고, 순수 스프링은 루프를 구조로 조절한다.** 자동구성이 없다는 건 불편이 아니라, 마이그레이션을 부팅에서 떼어낼 권한이 처음부터 내 손에 있다는 뜻이다.

---

## 근거의 한계

- 각 기법의 정량 효과(초 단위 절약)는 측정하지 않았고 인용하지 않았다. war 크기·컨테이너 기동 시간·changelog 규모에 따라 갈린다.
- "changelog 는 Update resources 로 복사돼도 살아 있는 앱에 반영되지 않는다" 는 SpringLiquibase 의 실행 시점(`afterPropertiesSet`)에서 따라 나오는 추론이며, 한 문서에 그대로 적힌 문장은 아니다.
- `SpringLiquibase` 의 빈 프로퍼티 목록은 javadoc 5.0.3 기준이다. 구버전(4.x)에는 일부 프로퍼티가 없거나 이름이 다를 수 있다.
- 외장 서버 Update 정책은 IntelliJ IDEA Ultimate 의 런 구성 기준이며, 에디션·버전에 따라 제공 범위가 다를 수 있다.

---

## References

[^springliquibase]: Liquibase 공식 javadoc — [SpringLiquibase (liquibase-core 5.0.3)](https://javadocs.liquibase.com/liquibase-core/liquibase/integration/spring/SpringLiquibase.html) (빈 등록 예시, `afterPropertiesSet` 자동 실행, `shouldRun`·`contexts`·`dropFirst`·`clearCheckSums`·`testRollbackOnUpdate` 프로퍼티)
[^maven-update]: Liquibase 공식 문서 — [Maven update (Community 5.0.4)](https://docs.liquibase.com/community/integration-guide-5-0-4/maven-update) (`mvn liquibase:update`, `liquibase.contexts`·`changesToApply`·`toTag` 속성, 컨텍스트 미지정 시 전부 실행)
[^contexts]: Liquibase 공식 문서 — [What are contexts?](https://docs.liquibase.com/concepts/changelogs/attributes/contexts.html) (`@` 접두의 의미, 필터 미지정 시 동작)
[^update-policies]: JetBrains 공식 문서 — [Updating applications on application servers | IntelliJ IDEA](https://www.jetbrains.com/help/idea/updating-applications-on-application-servers.html) (Update 정책 표, exploded/packaged 별 차이, 디버그 모드의 HotSwap 사용)
[^tomcat-config]: JetBrains 공식 문서 — [Run/Debug Configuration: Tomcat Server | IntelliJ IDEA](https://www.jetbrains.com/help/idea/run-debug-configuration-tomcat-server.html) (On 'Update' action, `Ctrl+F10`, run 모드에서는 런타임 능력에 의존)
[^flow]: JetBrains 공식 문서 — [Alter the program's execution flow | IntelliJ IDEA](https://www.jetbrains.com/help/idea/altering-the-program-s-execution-flow.html) (HotSwap 의 VM 차원 제약)
[^ctx-caching]: Spring Framework 공식 레퍼런스 — [Context Caching](https://docs.spring.io/spring-framework/reference/testing/testcontext-framework/ctx-management/caching.html) (static 캐시, 캐시 키 구성 요소, maxSize 32 LRU, fork 시 캐시 무효, `@DirtiesContext`)
