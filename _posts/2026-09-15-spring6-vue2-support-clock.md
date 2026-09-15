---
layout: post
title: "지원 시계로 읽는 스프링 6 + Vue 2 리스크 장부 (2/3)"
date: 2026-09-15 22:32:00 +0900
categories: [backend, frontend]
tags: [Spring, Vue2, EOL, 보안, 기술부채, 지원정책]
---

[1편]({% post_url 2026-09-15-spring6-vue2-stack-anatomy %})에서 스프링 6 + Vue 2 조합의 장점을 봤다. 이번엔 반대편 장부다. 이 조합의 리스크는 추상적인 "낡았다" 가 아니라 **날짜가 박힌 지원 종료의 누적**이고, 날짜는 전부 공식 문서에 있다.

## 지원 시계 — 2026년 9월 현재

| 부품 | 무료 지원 상태 | 근거 |
| --- | --- | --- |
| Vue 2 (core) | **2023-12-31 종료** — 보안 픽스 포함 전면 중단 | 공식 EOL 페이지[^vue-eol] |
| vue-router 3.x / vuex 3.x | 2023-12-31 부로 npm deprecated | 공식 EOL 예고 블로그[^vue-eol-blog] |
| Vuetify 2 | **2025-01-25 종료** | 공식 EOL 페이지[^vuetify-eol] |
| Spring Framework 6.2 | **OSS 지원 2026-06 종료** / 상용 지원은 2032년 중반까지 | 공식 버전 정책·지원정책 블로그[^sf-versions][^support-blog] |

읽는 법: **오늘 기준 이 스택의 두 축 모두 무료 지원이 끝나 있다.** 다만 성격이 다르다 — 스프링 6.2 는 석 달 전에 OSS 지원이 끝났지만 상용 우산이 2032년 중반까지 열려 있고, 7.0 으로 가는 완만한 길도 있다. Vue 2 는 2년 9개월 전에 **보안 픽스를 포함한 모든 공식 무료 지원이 끝났고**, 그 뒤로 나온 취약점은 공식 무료 채널로는 영원히 패치되지 않는다. 리스크의 무게중심은 명백히 프론트엔드 쪽에 있다.

## 리스크 1 — 패치되지 않는 취약점의 단방향 누적

Vue 2 공식 EOL 문서의 문장은 명확하다 — EOL 이후 Vue 2 는 *"보안과 브라우저 호환성 픽스를 포함한 어떤 업데이트도 받지 않는다."*[^vue-lts] 코드는 배포 채널(npm·CDN)에 계속 있지만, 고치는 사람이 공식적으로는 없다.

여기서 중요한 건 본체만이 아니라는 점이다. Vue 2 앱의 실제 표면적은 `vue` + `vue-router 3` + `vuex 3` + UI 프레임워크(Vuetify 2 등) + 무수한 Vue-2 전용 플러그인이고, **이 생태계 전체가 같은 방향으로 죽었다.** vue-router 3 과 vuex 3 은 본체와 같은 날 npm deprecated 됐고[^vue-eol-blog], Vuetify 2 도 2025년 1월 EOL 이다[^vuetify-eol]. 취약점이 어느 층에서 나오든 무료 픽스는 없다.

정직하게 한계도 적는다 — "EOL 후 Vue 2 에 몇 건의 미패치 취약점이 쌓였는가" 는 이 글에서 인용하지 않는다. 그 집계는 스캐너 벤더마다 다르고 중립 1차 출처로 검증하기 어렵다. 확실한 건 구조다: **새 취약점이 나올 때 그것을 무료로 고쳐 줄 주체가 없다.**

## 리스크 2 — 생태계 동결은 복리로 불어난다

지원 종료의 이차 효과는 시간이 갈수록 커진다.

- **신규 라이브러리는 Vue 3 전용으로 나온다.** 새 도구를 하나 들일 때마다 "Vue 2 지원 버전이 있는가" 라는 필터를 먼저 통과해야 하고, 통과하는 목록은 줄기만 한다.
- **브라우저는 계속 움직인다.** Vue 2 는 브라우저 호환성 픽스도 받지 않으므로[^vue-lts], 미래 브라우저 변경이 앱을 깨면 그건 내 패치로 막아야 한다.
- **빌드 체인도 같이 늙는다.** Vue 2 시대의 빌드 도구(webpack 4 대, vue-cli 등)에 묶여 있으면 Node 버전 업그레이드조차 연쇄 충돌이 된다. (이건 프로젝트마다 달라 일반화하지 않는다 — 우리 집 레거시에서 겪은 패턴이다.)

## 리스크 3 — 사람과 조직의 감가

정량 출처가 없어 짧게, 정성적으로만 적는다. 새로 합류하는 개발자는 Vue 3 를 배워서 온다. Vue 2 전용 지식(Options API 의 세부, `this` 기반 패턴, vuex 3)은 채용 시장에서 재생산되지 않는 지식이 돼 간다. 이건 취약점처럼 어느 날 터지는 리스크가 아니라, 유지보수 단가가 조용히 오르는 종류의 리스크다.

## 리스크 4 — 컴플라이언스의 관점

감사·보안 인증이 있는 산업에서는 "지원 종료된 소프트웨어의 사용" 자체가 지적 사항이 되는 경우가 있다. Vue 공식 문서조차 EOL 페이지에서 이 수요를 전제로 유료 연장 지원(HeroDevs NES — Vue 팀이 공식 파트너로 안내하는 상용 서비스)을 안내한다[^vue-lts]. 무료로 머무는 선택지가 공식적으로는 없다는 뜻이기도 하다.

## 장부의 결론

| | 스프링 6.2 에 머물기 | Vue 2 에 머물기 |
| --- | --- | --- |
| 무료 지원 | 끝남 (2026-06) | 끝남 (2023-12-31) |
| 유료 우산 | **있음, 2032 중반까지**[^support-blog] | 있음 (서드파티 NES, 벤더 상용)[^vue-lts] |
| 다음 버전으로의 경로 | 완만 (6.2→7.0, 점진) | 가파름 (Breaking changes 다수) |
| 생태계 | 살아 있음 | 동결 |

같은 "구버전에 머물기" 지만 두 축의 조건이 이렇게 다르다. 그래서 움직이는 순서에도 답이 있다 — **더 급한 쪽, 우산이 없는 쪽부터.** 구체적인 경로와 순서는 [3편 — 탈출 로드맵]({% post_url 2026-09-15-spring6-vue2-exit-roadmap %})에서.

---

## 근거의 한계

- Vue 2 EOL 후 누적 취약점 수, Vue 2 잔존 사용률 등의 정량 수치는 중립 1차 출처를 찾지 못해 인용하지 않았다.
- Vuetify 2 EOL 날짜는 공식 문서 간에 1월 23일(파트너십 블로그)과 1월 25일(EOL 페이지)로 이틀 차이가 있다. 본문 표는 EOL 전용 페이지의 날짜를 따랐다.
- HeroDevs NES 는 Vue 팀이 공식 안내하는 상용 서비스다. 그 서비스의 품질·범위에 대한 중립 제3자 평가는 확인하지 못했다.

## References

[^vue-eol]: Vue 2 공식 문서 — [Vue 2 Has Reached End of Life](https://v2.vuejs.org/eol/) (2023-12-31 EOL, 이후 기능·업데이트·픽스 없음)
[^vue-lts]: Vue 2 공식 문서 — [Vue 2 LTS, EOL & Extended Support](https://v2.vuejs.org/lts/) (보안·브라우저 호환성 픽스 중단 명시, HeroDevs NES 안내)
[^vue-eol-blog]: Vue 공식 블로그 — [Vue 2 is Approaching End Of Life](https://blog.vuejs.org/posts/vue-2-eol) (vue 2 core·vue-router 3.x·vuex 3.x npm deprecation)
[^vuetify-eol]: Vuetify 공식 문서 — [Vuetify 2 End of Life](https://v2.vuetifyjs.com/en/about/eol/) (2025-01-25 EOL)
[^sf-versions]: Spring 공식 위키 — [Spring Framework Versions](https://github.com/spring-projects/spring-framework/wiki/Spring-Framework-Versions) (6.2 OSS 지원 2026년 6월 종료)
[^support-blog]: spring.io 공식 블로그 — [Updates to Spring Support Policy](https://spring.io/blog/2025/02/13/support-policy-updates) (6.2 엔터프라이즈 지원 2032년 중반까지 연장)
