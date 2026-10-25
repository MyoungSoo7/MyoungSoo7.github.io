---
layout: post
title: "settlement 한 달 결산 (9/26~10/26) — 돈 버그 2건, 조용한 실패 4건, 그리고 코드 밖에서 난 빨간불"
date: 2026-10-26 05:34:11 +0900
categories: [Settlement, Retrospective]
tags: [settlement, idempotency, n-plus-one, observability, spring-security, caffeine, github-actions, trivy, gemini]
---

지난 한 달(2026-09-26 ~ 10-26) 동안 settlement 의 `develop` 브랜치에는 머지 커밋을 뺀 커밋이 28개 들어갔다. 커밋 메시지를 종류별로 세면 이렇다.

| 분류 | 건수 | 대표 |
| --- | --- | --- |
| 돈 계산 정확성 | 2 | 부분환불 멱등키 충돌, 기프트카드 재차감 |
| 기능 (평판·셀러 연결) | 5 | 사업자번호 기반 셀러 자동연결, 500개 상한 가시화 |
| 운영 관측·보안 위생 | 4 | ERROR 노이즈, 캐시 적중률 미터, Boot 생성 비밀번호 |
| 성능 | 1 | 주문 목록 N+1 |
| 의존성·CVE | 5 | Spring 7.0.9, jackson, pgjdbc, npm audit |
| CI·빌드 | 6 | 캐시 할당량, 레지스트리 스로틀 재시도, 러너 이전 |
| 릴리스·기타 | 5 | develop→main 릴리스, 회사 수집 실패 격리 |

숫자 자체보다 **어떤 종류의 문제가 어떻게 발견됐는지**를 보면 더 많은 게 보인다. 한 달 동안 고친 것들은 거의 다 다음 두 가지 중 하나였다.

1. 테스트는 초록인데 **돈이 틀리는** 경로
2. 에러가 안 나는데 **아무도 모르게 실패하는** 경로

여기에 코드와 무관하게 CI 를 빨갛게 만든 사건들이 겹쳤다. 아래에서 차례로 정리한다.

> 이 리포는 private 이다. 그래서 이 글에는 내부 주소·키·고객 데이터를 싣지 않았다. 클래스 이름과 동작 원리만 다룬다.

---

## 1. 돈 버그 2건 — 멱등키가 "같은 요청" 을 잘못 정의했다

### 1-1. 같은 금액 부분환불 두 번이 한 번으로 합쳐진다 (#371)

환불 실행기의 멱등키는 원래 `tender-{tenderId}-{금액}` 이었다.

얼핏 그럴듯하다. 그런데 **같은 결제수단에서 같은 금액을 정당하게 두 번 부분환불**하면, 두 요청이 같은 키를 받는다. 회귀 테스트로 이 상황을 재현하자 키 두 개가 `[tender-102-5000, tender-102-5000]` 으로 똑같이 나왔다. 그러면 시스템이 이렇게 갈라진다.

- **PG 쪽:** 두 번째 환불을 "재시도" 로 보고 무시한다.
- **포인트·기프트카드 원장:** 자연키가 두 번째 복원을 삼킨다.
- **결제 엔티티:** `addRefund` 와 `addRefundedAmount` 는 **조건 없이** 실행된다.

결과적으로 결제 쪽 환불 누계가 실제로 돌려준 돈보다 앞서 나간다. 장부와 현금이 어긋난다.

멱등키의 원칙은 Stripe API 문서에 잘 정리돼 있다. 키는 **"같은 연산의 재시도"** 를 식별해야 하고, 서로 다른 연산에는 서로 다른 키를 써야 한다[^stripe]. 금액만으로는 "다른 연산" 을 구분할 수 없었던 것이다.

새 키에는 **환불 직전 누계**를 넣었다.

$$
\text{key} = \texttt{tender-}\{id\}\texttt{-}\{\text{refunded}_{\text{before}}\}\texttt{-}\{\text{amount}\}
$$

이 설계에서 핵심은 두 가지다.

- **누계는 잠근 행(`SELECT … FOR UPDATE`)에서 읽는다.** 그래서 커밋된 환불이 하나 늘 때마다 누계가 단조 증가하고, 키도 서로 달라진다.
- **PG 호출 뒤 DB 커밋 전에 죽은 시도는 같은 누계에서 다시 출발한다.** 그래서 재시도는 같은 키를 받고, 이중 환불 방어는 그대로 유지된다.

### 1-2. 다 쓴 기프트카드의 재시도가 다른 카드에서 또 차감된다 (#373)

"이미 차감했나?" 를 판정하는 로직은 `loadSpendable`(쓸 수 있는 카드 목록)에서만 사용 기록을 찾았다.

문제는 첫 시도가 카드를 전부 써서 `USED_UP` 이 된 경우다. 그 카드는 쓸 수 있는 목록에서 빠지므로, 재시도가 그 카드의 기존 차감 기록을 보지 못한다. 그러면 다른 카드에서 **한 번 더 차감**하거나, 다른 카드가 없으면 잔액부족으로 실패한다.

고친 방법은 판정 기준을 바꾸는 것이었다. 이제 원장을 **참조(tender id) 기준으로 카드를 가로질러** 조회한다.

교훈은 이렇다. 멱등 판정을 **필터링된 부분집합**에 걸면, 상태가 바뀌어 그 부분집합에서 빠진 레코드가 판정에서 사라진다.

### 공통 규칙: 빨간불을 먼저 본다

두 PR 모두 **수정 전 코드에서 회귀 테스트가 빨간 것**을 먼저 확인했고, 그다음에 고쳤다. 돈 계산 로직은 이 순서를 지키지 않으면, 테스트가 실제로 버그를 잡는지 알 수 없다.

---

## 2. 조용한 실패 4건 — 에러가 안 나서 몰랐다

### 2-1. 평판 배치가 매일 81% 를 버리고 있었다 (#352, #353)

평판 재산정 배치는 기업 목록을 `100건 × 최대 5페이지 = 500개` 까지만 받아 왔다.

상장사는 2,661개였으니, **2,161개(81%)가 매일 조용히 빠지고 있었다.** 그런데 요약 로그에는 `companies=500` 만 찍혀서, 목록이 잘렸다는 사실이 보이지 않았다.

1단계에서는 **동작을 바꾸지 않고 잘림을 드러내기만** 했다.

- 응답에 `truncated` 필드를 추가했다.
- 상한에 걸리면 `WARN` 을 남긴다.
- 상한값을 설정으로 뺐다. 기본값은 500 그대로다.

상한을 올리는 것은 별도 결정으로 남겼다. 올리면 감성 분석 LLM 호출 수와 배치 시간이 약 5배가 되기 때문이다.

같은 시기에 회사별 기사 수집도 손봤다. **한 회사가 실패하면 전체 수집이 멈추던 구조**를 회사 단위로 격리했다(#365).

### 2-2. 감성 분석이 100% 키워드 폴백이었다 (#374)

`gemini-2.5-flash` 를 호출하자 404 가 돌아왔다. 메시지는 "no longer available to new users" 였다. 그 결과 24시간 경고 200건이 **전량 키워드 폴백**이었고, 실패한 호출이 일일 상한까지 다 써 버렸다.

기본 모델을 `gemini-3.5-flash` 로 바꾸자 이번엔 다른 함정이 나왔다. 3 계열 모델은 thinking 토큰이 출력 예산을 먼저 쓴다. 실측해 보니 256 토큰 중 245 토큰을 thinking 이 가져갔다. Gemini 문서는 `thinkingLevel` 로 사고 깊이를 조절하라고 안내한다[^gemini]. 그래서 짧은 분류 작업에는 `minimal` 을 줬다.

반면 OCR 은 1024 토큰 예산 안에서 추출이 정확했기 때문에 thinking 을 그대로 뒀다. **같은 모델이라도 작업마다 실측한 뒤에 정했다.**

### 2-3. ERROR 로그의 100% 가 장애가 아니었다 (#379)

settlement-app 의 24시간치 ERROR 로그를 하나씩 확인해 보니, **장애는 한 건도 없었다.**

- **33건:** 새벽 스모크 테스트(Playwright)가 응답 도중 연결을 끊으면서 생긴 `Broken pipe`
- **나머지:** 게스트 토큰으로 `getMe` 를 호출해 생긴 404 를 AOP 가 ERROR 로 한 번 더 기록한 것

ERROR 레벨을 장애 신호로 쓸 수 없는 상태였다. 그래서 두 가지로 나눴다.

- **클라이언트가 끊은 경우:** 원인 사슬에서 판별해 `debug` 로 낮춘다.
- **4xx 비즈니스 예외:** `WARN` 으로 낮춘다.

5xx 와 무관한 `IOException("disk full")` 은 그대로 ERROR 로 둔다. 이게 바뀌지 않았는지는 대조군 테스트로 확인했다. 대시보드용 타이머의 `outcome` 태그도 바꾸지 않았다.

### 2-4. 캐시 적중률 미터가 아예 없었다 (#380)

기동 로그에 이런 줄이 있었다.

```
The cache 'products' is not recording statistics. No meters except 'cache.size' will be registered.
```

Caffeine 은 `recordStats()` 를 켜야 통계를 수집한다[^caffeine]. 꺼져 있으면 Micrometer 는 적중률 미터를 만들 재료가 없다. 빌더에 한 줄을 추가했다. 비용은 접근할 때마다 카운터를 하나 올리는 정도다.

---

## 3. 보안 위생 — 아무도 안 쓰는 계정의 비밀번호가 로그에 남았다 (#381)

서비스 다섯 개 모두 기동할 때 `Using generated security password: <uuid>` 를 찍고 있었다.

Spring Boot 는 개발자가 `UserDetailsService` 같은 인증 빈을 따로 정의하지 않으면, `user` 라는 인메모리 사용자를 만들고 비밀번호를 로그에 출력한다[^boot]. 그런데 이 서비스들은 JWT 필터로만 인증하고 formLogin·httpBasic 을 꺼 둔다. 그러니 이 계정은 쓰일 곳이 없는데 **비밀번호만 매번 로그 수집기에 평문으로 쌓이고 있었다.**

서비스마다 `exclude` 를 다는 대신, 공통 모듈에 자동 구성을 하나 뒀다. Boot 의 `UserDetailsServiceAutoConfiguration` **보다 먼저** 등록돼서 Boot 가 물러나게 만드는 방식이다. 이렇게 하면 새로 추가되는 서비스도 이 설정을 빠뜨리지 않는다.

---

## 4. 성능 — 주문 156건에 쿼리 313번 (#382)

관리자 주문 목록 API 의 운영 평균 응답 시간은 1.13초였다(22회 기준). 원인은 전형적인 N+1 이었다. 주문마다 라인을 조회하고, 라인마다 옵션을 또 조회했다.

$$
Q_{\text{before}} = 1 + N + \sum_{i=1}^{N} L_i \qquad\longrightarrow\qquad Q_{\text{after}} = 3
$$

여기서 $N$ 은 주문 수, $L_i$ 는 $i$ 번째 주문의 라인 수다. 수정 후에는 주문 1번, 라인 `IN` 1번, 옵션 `IN` 1번으로 끝난다. `IN` 절은 1000개 단위로 잘라 보내고, 결과는 입력 순서대로 유지한다.

Hibernate 에도 배치 페칭 기능이 있다[^hibernate]. 하지만 이 코드는 헥사고날 구조의 영속성 어댑터에서 도메인으로 조립하는 경로라서, 명시적으로 일괄 로드하는 쪽을 택했다. 목록이 비어 있으면 자식 조회를 0번 하도록 해서 빈 `IN ()` 도 막았다.

배포 후 응답 시간 재측정은 아직 하지 못했다. 이유는 아래 5절에 있다.

---

## 5. 코드 밖에서 난 빨간불

이번 달 CI 빨간불의 상당수는 **코드와 무관했다.**

### 5-1. Actions 저장소 할당량 (#383)

10/20 에 #382 의 CI 가 커버리지 업로드 단계에서 `Artifact storage quota has been hit` 로 실패했다.

조사해 보니 실제 아티팩트는 75MB 뿐이었다. 범인은 Actions **캐시** 11.8GB 였고, 그중 6.9GB 가 이미 머지된 PR 4개의 buildkit 캐시였다. PR 하나당 약 1.7GB 다.

GitHub 문서에 따르면 PR 에서 만든 캐시는 그 PR 의 merge ref(`refs/pull/.../merge`) 범위에 묶인다. 그래서 같은 PR 의 재실행만 그 캐시를 쓸 수 있다[^ghcache]. 머지가 끝나면 그 캐시는 **아무도 못 쓰는 용량**이 된다.

조치는 두 가지였다.

- Docker 의 `gha` 캐시 백엔드[^dockergha]에서 `cache-to`(내보내기)는 push 이벤트에서만 하도록 바꿨다. PR 은 `cache-from` 으로 develop·main 캐시를 읽기만 한다.
- 이 규칙을 하네스 게이트 테스트로 고정했다.

그래도 할당량은 다시 찼다. 10/25 에 머지한 릴리스 PR #388 의 main CI 도 같은 `Artifact storage quota has been hit` 로 프론트엔드 잡이 실패했다. 이미지 집계 잡은 "프론트엔드 변경이 있는데 이미지가 안 만들어졌다" 는 이유로 초록 통과를 거부했다. 덕분에 **빨간 릴리스가 운영에 나가지는 않았다.**

다만 그 결과 #379~#384 는 **아직 운영에 배포되지 않은 상태다.** 실패 로그의 에러 메시지에도 "Usage is recalculated every 6-12 hours" 라고 나온다. 캐시를 지워도 할당량은 바로 풀리지 않는다. 그리고 아티팩트와 캐시는 같은 저장 용량을 함께 쓴다[^ghbilling].

### 5-2. 레지스트리 스로틀 (#384)

Maven Central 이 가끔 403·429 를 돌려준다. 테스트 잡에는 재시도가 있었지만, Dockerfile 안의 gradle 은 재시도 범위 밖이었다.

그래서 POSIX sh 래퍼를 하나 만들었다. **스로틀 신호일 때만** 지수적으로 물러서 최대 3회 재시도하고, 컴파일 에러 같은 다른 실패는 종료코드를 그대로 돌려준다.

### 5-3. 새로 공개된 CVE (#366, #354, #358, #369)

10/12 에는 테스트가 전부 통과했는데도 Trivy SBOM 스캔[^trivy] 게이트가 main 을 막았다. 직전 초록 이후에 공개된 의존성 CVE 6건(CRITICAL 4, HIGH 2) 때문이었다.

Spring Framework 7.0.9, jsoup, lz4 를 올리고, `.trivyignore` 에는 손대지 않았다. 한 달 동안 이런 의존성 갱신 PR 이 네 번 들어갔다. 코드를 한 줄도 안 바꿔도, **달력이 지나가면 빌드가 빨개진다.**

### 5-4. 러너 이전

10/15 에 CI 노드 하나가 퇴역하면서, 백엔드 공용·테스트 잡을 다른 셀프호스티드 러너로 옮겼다.

---

## 6. 기능 — 셀러 자동연결은 "꺼진 채로" 릴리스

9/27 에 사업자등록번호로 셀러를 기업에 자동연결하는 기능을 넣었다(`7a7bd0b7`). 그런데 10/4 릴리스 리뷰에서 P1 세 건이 나왔다. 그래서 기능을 빼는 대신 **스위치를 만들어 기본값 OFF 로 릴리스**했다(#360).

- **스위치가 꺼져 있을 때:** 번호 적재는 계속하고, 매칭만 건너뛴다.
- **나중에 켤 때:** 그동안 쌓인 번호로 다음 재매칭이 연결한다.

P1 세 건은 같은 날 #361 과 #364 로 고쳤다. 같은 릴리스에서 호출자가 없는 레거시 지급 메서드도 제거했다(`23b26c66`).

---

## 정리

한 달을 한 줄로 요약하면 이렇다. **"테스트가 초록이고 에러가 안 났는데 틀린 것" 을 찾는 데 대부분의 시간을 썼다.**

| 유형 | 사례 | 발견 경로 |
| --- | --- | --- |
| 초록인데 돈이 틀림 | 멱등키 충돌, 재차감 | 경계 케이스 회귀 테스트 (수정 전 빨강 확인) |
| 에러 없이 누락 | 81% 기업 누락, 100% 폴백 | 운영 로그 수치를 기대치와 대조 |
| 에러인데 장애 아님 | ERROR 100% 노이즈 | 24시간 ERROR 전수 분류 |
| 코드 무관 빨간불 | 할당량, 스로틀, CVE | 실패 로그 원문 확인 (재실행부터 하지 않기) |

다음 한 달에 할 일은 세 가지다.

1. 할당량이 풀리면 #388 의 main CI 를 재실행하고 배포한다.
2. 배포 후 주문 목록 응답 시간과 "generated security password" 로그 0건을 실측한다.
3. 평판 배치 상한을 올릴지(LLM 비용 대 누락률) 결정한다.

### 한계

- 이 글의 수치는 모두 PR 본문에 기록된 **운영 실측 1회분**이다. 반복 측정해 통계를 낸 값이 아니다.
- N+1 개선의 운영 효과는 아직 배포 전이라 **측정되지 않았다.**

---

## References

[^stripe]: Stripe API Reference, "Idempotent requests". <https://docs.stripe.com/api/idempotent_requests>
[^gemini]: Google AI for Developers, "Gemini thinking" (`thinkingLevel`). <https://ai.google.dev/gemini-api/docs/thinking>
[^caffeine]: Ben Manes, Caffeine Wiki, "Statistics" (`Caffeine.recordStats()`). <https://github.com/ben-manes/caffeine/wiki/Statistics>
[^boot]: Spring Boot Reference, "Spring Security" — default `UserDetailsService` and generated password, `UserDetailsServiceAutoConfiguration`. <https://docs.spring.io/spring-boot/reference/web/spring-security.html>
[^hibernate]: Hibernate ORM 6.6 User Guide, "Batch fetching". <https://docs.jboss.org/hibernate/orm/6.6/userguide/html_single/Hibernate_User_Guide.html>
[^ghcache]: GitHub Docs, "Dependency caching reference" — restrictions for accessing a cache (merge ref scope). <https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching>
[^dockergha]: Docker Docs, "GitHub Actions cache" (`type=gha`, `cache-to`/`cache-from`). <https://docs.docker.com/build/cache/backends/gha/>
[^ghbilling]: GitHub Docs, "GitHub Actions billing" (artifact and cache storage). <https://docs.github.com/en/billing/concepts/product-billing/github-actions>
[^trivy]: Aqua Security, Trivy documentation. <https://trivy.dev/latest/docs/>
