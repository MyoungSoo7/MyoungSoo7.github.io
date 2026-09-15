---
layout: post
title: "스프링 6 + Vue 2, 어디로 어떤 순서로 — 탈출 로드맵 (3/3)"
date: 2026-09-15 22:34:00 +0900
categories: [backend, frontend]
tags: [Spring, Vue2, Vue3, 마이그레이션, 로드맵, vue-compat]
---

[1편]({% post_url 2026-09-15-spring6-vue2-stack-anatomy %})에서 장점을, [2편]({% post_url 2026-09-15-spring6-vue2-support-clock %})에서 지원 시계를 봤다. 결론은 이랬다 — 두 축 모두 무료 지원이 끝났지만 스프링 쪽엔 2032년까지의 상용 우산과 완만한 업그레이드 길이 있고, Vue 2 쪽엔 그게 없다. 이제 마지막 질문: **그래서 어디로, 어떤 순서로 가는가.**

## 선택지는 셋이고, 셋 다 합법적이다

**A. 버틴다 (돈으로 시간 구매).** Vue 2 는 Vue 팀이 공식 안내하는 유료 연장 지원(HeroDevs NES — SLA 포함)으로[^vue-lts], Spring 6.2 는 상용 지원으로[^support-blog] 각각 우산을 산다. 합리적인 경우: **앱의 수명이 정해져 있을 때.** 2년 뒤 폐기될 시스템을 마이그레이션하는 건 낭비다. 비합리적인 경우: 수명이 무기한인데 "당장 급하지 않아서" 버틸 때 — 2편에서 본 대로 생태계 동결 비용은 복리다.

**B. 프론트만 움직인다 (Vue 2 → 3).** 스프링 6 은 상용 우산 아래 그대로 두고, 우산이 없는 쪽부터 옮긴다.

**C. 둘 다 움직인다.** 프론트는 Vue 3, 백엔드는 Spring 7 (2025년 11월 출시, 현행 프로덕션 라인이고 7.1 은 2026년 11월 예정[^sf-versions]). 부트를 쓴다면 백엔드 경로는 [스프링부트 4 마이그레이션 지도]({% post_url 2026-09-15-spring-framework-6-to-boot-4-migration-map %})에 이미 정리해 뒀다.

## 순서에 답이 있다 — 우산 없는 쪽부터

1편에서 말한 REST 경계의 배당이 여기서 나온다 — **두 마이그레이션은 서로 독립이다.** Vue 3 는 스프링 버전을 모르고, Spring 7 은 프론트 프레임워크를 모른다. 그러니 순서는 기술 의존성이 아니라 리스크로 정하면 되고, 리스크 순위는 2편의 장부가 이미 매겨 놨다:

1. **먼저 API 계약을 고정한다.** OpenAPI 스펙이든 계약 테스트든, 프론트와 백엔드가 서로를 검증할 기준을 마이그레이션 전에 박아 둔다. 계약이 고정돼 있으면 한쪽을 갈아엎는 동안 다른 쪽이 인질이 되지 않는다.
2. **Vue 2 → 3 를 먼저 간다.** 무료 지원이 끝난 지 3년 가까이 된 쪽이 급하다.
3. **Spring 6.2 → 7 은 그 다음이다.** 상용 우산이 필요 없는 팀이라도 6.2 는 이미 산을 넘은 세대라 경로가 완만하고, 서두를 이유가 프론트보다 약하다.

## Vue 2 → 3: 공식 경로는 빅뱅이 아니다

전면 재작성의 유혹을 먼저 꺾는다 — Vue 팀은 **마이그레이션 빌드(`@vue/compat`)** 라는 점진 경로를 공식 제공한다. 공식 정의: *"Vue 2 호환 동작을 설정 가능하게 제공하는 Vue 3 의 빌드"* 로, **기본은 Vue 2 모드로 돌고**, 변경·폐지된 기능을 쓰면 런타임 경고를 내며, 호환성은 **컴포넌트 단위로** 켜고 끌 수 있다[^mig-build].

공식 워크플로우의 뼈대:[^mig-build]

1. `vue` 를 3.x 로, 같은 버전의 `@vue/compat` 설치, `vue-template-compiler` → `@vue/compiler-sfc` 교체
2. 빌드 설정에서 `vue` 를 `@vue/compat` 으로 alias, compat 모드 활성화
3. 컴파일 에러(필터 등)부터 잡고 → 런타임 경고를 하나씩 걷어낸다. 충돌하는 동작은 `compatConfig` 로 컴포넌트별 opt-in
4. 경고가 0 이 되면 마이그레이션 빌드를 제거하고 표준 Vue 3 로 전환

공식 문서가 명시한 한계 세 개가 사실상 사전 점검표다:[^mig-build]

- **Vue 2 내부 API 에 의존하는 라이브러리는 못 넘어간다.** 문서가 Vuetify·Quasar·ElementUI 를 직접 거명한다 — UI 프레임워크는 compat 으로 끌고 가는 게 아니라 **Vue 3 대응 메이저 버전으로 교체**하는 항목이다 (Vuetify 2 자체도 EOL 이다[^vuetify-eol]). 실무에서는 이 UI 프레임워크 교체가 마이그레이션 공수의 대부분을 차지하는 경우가 많다 — 여기가 견적의 중심이다.
- **IE11 을 버려야 한다.** Vue 3 는 IE11 지원을 공식적으로 접었다. IE11 요구가 남아 있는 환경이면 선택지는 A(버티기)뿐이다.
- **SSR 커스텀 셋업은 별도 공사다.** `vue-server-renderer` → `@vue/server-renderer` 교체가 필요하다.

브레이킹 체인지 자체는 공식 목록이 있고[^breaking] — `new Vue()` → `createApp`, `v-model` 재설계, `$set`/`$delete` 제거(프록시 반응성으로 불필요), 필터 제거, 라이프사이클 이름 변경 등 — 하나씩 보면 기계적이다. 핵심 조언은 두 가지다. 첫째, **아직 2.7 로 안 올라갔다면 그것부터.** 2.7 은 Composition API 를 백포트한 공식 디딤돌이라[^naruto], 2.7 에서 새 문법으로 쓴 코드는 3 에서 거의 그대로 산다. 둘째, 마이그레이션 빌드는 문서 스스로 "언젠가 발행을 중단할 예정" 이라고 밝힌 **임시 다리**다[^mig-build] — 다리 위에서 사는 게 아니라 건너는 용도다.

## 백엔드: 스프링의 로드맵은 예측 가능성이 자산이다

스프링 쪽 미래는 공식 문서에 날짜까지 박혀 있다 — 7.0 이 현행 프로덕션 라인(2025-11), 7.1 이 2026-11 예정, 6.2 상용 지원은 2032 중반까지[^sf-versions][^support-blog]. 매년 11월 마이너, 세대 전환 시 마지막 마이너에 긴 우산 — 이 리듬이 공표돼 있어서 **업그레이드를 몇 년 뒤로 계획하는 것 자체가 가능**하다. Vue 2 가 주는 교훈을 뒤집으면 그대로 스프링 쪽 행동 지침이 된다: 우산이 있을 때 움직이는 게 가장 싸다. 2032 는 멀어 보이지만, 그때까지 6.2 에 머물수록 7-세대와의 거리는 벌어진다.

## 정리 — 한 장짜리 로드맵

| 시점 | 프론트 | 백엔드 |
| --- | --- | --- |
| 지금 | API 계약 고정 (OpenAPI/계약 테스트) | 같이 계약 고정 |
| 1단계 | Vue 2.7 로 (아직이면) + Composition API 로 신규 코드 | 6.2 최신 패치 유지 |
| 2단계 | `@vue/compat` 으로 점진 전환, UI 프레임워크 메이저 교체 | — |
| 3단계 | 표준 Vue 3 전환, compat 제거 | Spring 7 준비 (deprecation 청소) |
| 4단계 | — | 6.2 → 7.0 ([부트면 이 지도]({% post_url 2026-09-15-spring-framework-6-to-boot-4-migration-map %})) |
| 예외 | 앱 수명 확정 시: NES 로 버티기 | 상용 지원으로 2032 까지 가능 |

한 줄 요약 — **이 조합의 미래는 "스프링 6 + Vue 2 를 지키는 것" 이 아니라, 잘 갈라 둔 경계를 그대로 쓰며 한쪽씩 갈아끼우는 것이다.** 경계가 깨끗하면 스택은 늙어도 아키텍처는 늙지 않는다.

---

## 근거의 한계

- 마이그레이션 공수(인월)나 "UI 프레임워크 교체가 공수의 대부분" 이라는 비중 판단은 내 경험칙이며 정량 출처가 없다. 프로젝트 규모·컴포넌트 수·커스텀 정도에 따라 크게 다르다.
- 마이그레이션 빌드 문서의 워크플로우는 Vue 3.1~3.2 시점 기준으로 쓰인 것이다. 절차의 뼈대는 유효하나 버전 숫자는 현재와 다를 수 있다.
- Spring 7.1 의 2026년 11월 출시는 공식 위키의 예정이며, 예정은 바뀔 수 있다.

## References

[^vue-lts]: Vue 2 공식 문서 — [Vue 2 LTS, EOL & Extended Support](https://v2.vuejs.org/lts/) (HeroDevs NES 공식 안내, SLA)
[^support-blog]: spring.io 공식 블로그 — [Updates to Spring Support Policy](https://spring.io/blog/2025/02/13/support-policy-updates) (6.2 상용 지원 2032 중반까지)
[^sf-versions]: Spring 공식 위키 — [Spring Framework Versions](https://github.com/spring-projects/spring-framework/wiki/Spring-Framework-Versions) (7.0 현행 프로덕션 라인, 7.1 은 2026-11 예정, 6.2 OSS 종료)
[^mig-build]: Vue 공식 마이그레이션 가이드 — [Migration Build](https://v3-migration.vuejs.org/migration-build.html) (`@vue/compat` 정의·워크플로우·한계: 내부 API 의존 라이브러리, IE11, SSR)
[^breaking]: Vue 공식 마이그레이션 가이드 — [Breaking Changes](https://v3-migration.vuejs.org/breaking-changes/) (전체 브레이킹 체인지 목록)
[^naruto]: Vue 공식 블로그 — [Vue 2.7 "Naruto" Released](https://blog.vuejs.org/posts/vue-2-7-naruto) (Composition API·`<script setup>` 백포트)
[^vuetify-eol]: Vuetify 공식 문서 — [Vuetify 2 End of Life](https://v2.vuetifyjs.com/en/about/eol/) (2025-01-25 EOL)
