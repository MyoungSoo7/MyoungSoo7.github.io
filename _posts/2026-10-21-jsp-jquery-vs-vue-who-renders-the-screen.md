---
layout: post
title: "JSP + jQuery vs Vue + JavaScript — 기술 비교가 아니라 '화면을 누가 만드나' 의 비교다"
date: 2026-10-21 23:09:46 +0900
categories: [Frontend, Architecture]
tags: [JSP, jQuery, Vue, JavaScript, Spring Boot, Thymeleaf, Legacy, Migration]
---

국내 SI·공공·사내 시스템에서 지금도 자주 만나는 화면 조합이 **JSP + jQuery** 다. 새로 시작하는 프로젝트는 **Vue(또는 React) + JavaScript** 를 고른다. 둘을 비교하는 글은 많지만, 대부분 "옛날 것 vs 요즘 것" 으로 끝난다.

이 글의 주장은 이렇다. **두 조합의 진짜 차이는 기술의 신구가 아니라, 화면을 서버가 만드느냐 브라우저가 만드느냐다.** 그 차이를 알면 언제 무엇을 고를지, 기존 JSP 를 어떻게 옮길지가 정리된다.

## 1. 지금 각 기술의 공식 상태 (2026-10 기준)

| 기술 | 공식 상태 | 근거 |
|---|---|---|
| **JSP** (Spring Boot 에서) | 지원은 하지만 *"If possible, JSPs should be avoided"* | Spring Boot 레퍼런스[^boot] |
| **jQuery** | **4.0.0** 이 2026-01-17 정식 출시. 3.x 는 *"will only receive critical security patches and bug fixes"* | jQuery 블로그·지원 정책[^jq4][^jqsup] |
| **Vue 3** | 현재 버전 (npm 최신 3.5.x) | Vue 공식 문서[^vue] |
| **Vue 2** | *"Vue 2 will reach End of Life (EOL) on December 31st, 2023"* | Vue 2 LTS 안내[^vue2] |

몇 가지는 의외일 수 있다.

- **jQuery 는 죽지 않았다.** 20년 만에 4.0 이 나왔다. 다만 성격이 바뀌었다. 4.0 은 `jQuery.isArray`, `jQuery.parseJSON`, `jQuery.trim` 같은 함수들을 제거하면서 *"Use native equivalents like `Array.isArray()`, `JSON.parse()`, `String.prototype.trim()`…"* 이라고 안내한다.[^jq4] **브라우저가 jQuery 를 따라잡았다**는 공식 인정이다.
- **Spring Boot 는 JSP 를 피하라고 한다.** 실행 가능한 jar 로 패키징하면 *"JSPs are not supported when using an executable jar"* 이고, war 로 패키징해야 동작한다.[^boot] Spring Boot 가 자동 설정을 제공하는 템플릿 엔진은 FreeMarker, Groovy, Thymeleaf, Mustache 다.[^boot]
- **Vue 2 로 만든 화면은 이미 레거시다.** EOL 이후에는 *"no longer receive updates, including security and browser compatibility fixes"* 이다.[^vue2] "JSP 를 Vue 로 옮겼는데 Vue 2 였다" 면 레거시를 레거시로 옮긴 셈이다.

## 2. 핵심 차이 — 화면을 누가 만드나

| | JSP + jQuery | Vue + JavaScript |
|---|---|---|
| **HTML 을 만드는 곳** | 서버 (요청마다 JSP 가 HTML 을 그려 보냄) | 브라우저 (서버는 데이터만, 화면은 Vue 가 그림) |
| **화면 상태가 사는 곳** | DOM 자체 (`$('#qty').val()`) | 자바스크립트 상태 (`data`, `ref`) → DOM 은 결과물 |
| **변경 방식** | "이 버튼 누르면 저 칸을 바꿔라" — **명령형** | "상태가 이러면 화면은 이렇다" — **선언형** |
| **서버와 주고받는 것** | 페이지 전체, 또는 `$.ajax` 로 받은 조각 | JSON API |
| **빌드 도구** | 필요 없음 | 보통 필요 (Vite 등). 단, 없이도 쓸 수 있음 |
| **팀 구조** | 백엔드 개발자가 화면까지 | 프론트·백엔드가 API 로 나뉘기 쉬움 |

jQuery 시절 코드가 커지면 무너지는 이유가 여기 있다. **화면의 "진짜 상태" 가 DOM 곳곳에 흩어져 있기 때문**이다. 체크박스 하나, 숨김 필드 하나, `data-` 속성 하나가 각각 상태를 들고 있고, 이벤트 핸들러가 늘수록 "지금 화면이 왜 이 모양인가" 를 아무도 설명하지 못하게 된다.

Vue 는 이 문제를 **상태를 한곳에 두고, 화면은 그 결과로만 그리는** 방식으로 푼다. 대신 그 대가로 API 설계, 상태 관리, 빌드 도구를 받아들여야 한다.

## 3. 보안 — 기본값이 다르다

화면에 사용자 입력을 찍을 때의 기본값이 다르다.

- **Vue**: 공식 보안 문서는 *"Whether using templates or render functions, content is automatically escaped."* 라고 적는다.[^vuesec] 위험한 건 HTML 을 그대로 넣는 `v-html` 이고, 문서는 사용자 제공 HTML 을 신뢰하지 말라고 경고한다.
- **JSP + jQuery**: 출력할 때마다 이스케이프를 **개발자가 챙겨야** 한다. JSP 쪽에서는 JSTL `<c:out>` 같은 이스케이프 출력을, jQuery 쪽에서는 `.html()` 대신 `.text()` 를 쓰는 식이다. 하나라도 빠지면 XSS 가 된다. jQuery 4.0 이 Trusted Types 와 CSP 지원을 추가한 것도 이 문제를 줄이기 위한 방향이다.[^jq4]

**기본값이 안전한 쪽**과 **매번 기억해야 안전한 쪽**의 차이는, 화면이 수백 개가 되면 결과의 차이가 된다.

## 4. 그래서 언제 무엇을

**JSP(또는 서버 템플릿) + 약간의 JS 가 맞는 경우**

- 관리자 화면, 조회·입력 위주의 업무 화면
- 페이지마다 상호작용이 단순하고, 화면 수는 많은 시스템
- 백엔드 개발자가 화면까지 맡는 작은 팀

다만 **새로 만든다면 JSP 보다 Thymeleaf 같은 템플릿 엔진**이 낫다. Spring Boot 가 자동 설정을 제공하고, 실행 가능한 jar 의 제약도 없다.[^boot]

**Vue 가 맞는 경우**

- 한 화면 안에서 상태가 복잡하게 얽히는 경우 (편집기, 대시보드, 여러 단계 입력 마법사)
- 같은 API 를 웹·모바일이 함께 쓰는 경우
- 프론트엔드를 전담하는 사람이 있는 팀

## 5. 중간 길 — 전부 바꾸지 않아도 된다

Vue 공식 문서는 Vue 를 쓰는 방법의 첫 번째로 *"Enhancing static HTML without a build step"* 을 든다.[^vue] 또 빌드 도구를 쓰지 않거나 *"progressive enhancement"* 같은 단순한 용도라면 Options API 를 권한다.[^vue]

즉 기존 JSP·Thymeleaf 페이지를 그대로 두고, **복잡한 한 영역만 Vue 로** 바꿀 수 있다. 실무에서 가장 현실적인 이전 순서는 이렇다.

1. **jQuery 유틸 함수부터 걷어 낸다.** jQuery 4.0 이 제거한 함수 목록이 그대로 "네이티브로 바꿀 목록" 이다.[^jq4] `$.trim` → `String.prototype.trim()`, `$.parseJSON` → `JSON.parse()`.
2. **상태가 복잡한 화면 하나를 고른다.** 그 화면의 데이터를 JSON API 로 분리하고, 그 영역만 Vue 로 그린다.
3. **새 화면은 처음부터 새 방식으로.** 남은 JSP 는 기능이 바뀔 때 함께 옮긴다. 한 번에 다 바꾸는 "빅뱅 전환" 보다 안전하다.
4. **Vue 2 는 고르지 않는다.** 이미 EOL 이다.[^vue2]

## 맺으며

JSP + jQuery 와 Vue + JavaScript 를 고르는 건 유행의 문제가 아니라 **"화면의 상태를 어디에 두고, 누가 책임지게 할 것인가"** 의 문제다. 단순한 화면이 많다면 서버가 그리는 쪽이 여전히 효율적이고, 복잡한 화면이 많다면 상태를 한곳에 모으는 쪽이 유지보수 비용을 줄인다.

공식 문서들이 보내는 신호도 분명하다. Spring Boot 는 JSP 를 피하라고 하고, jQuery 는 브라우저 기본 기능을 쓰라고 하고, Vue 는 2 를 끝냈다. 레거시를 한 번에 버릴 필요는 없지만, **새로 쓰는 코드가 어느 방향을 향하는지**는 지금 정해야 한다.

---

## References

[^boot]: Spring Boot Reference, *Servlet Web Applications — Template Engines, JSP Limitations*. <https://docs.spring.io/spring-boot/reference/web/servlet.html>
[^jq4]: jQuery Blog, *jQuery 4.0.0* (2026-01-17). <https://blog.jquery.com/>
[^jqsup]: jQuery, *Version Support*. <https://jquery.com/support/>
[^vue]: Vue.js, *Introduction* (Vue 3 guide). <https://vuejs.org/guide/introduction.html>
[^vue2]: Vue.js, *Vue 2 LTS, EOL & Extended Support*. <https://v2.vuejs.org/lts/>
[^vuesec]: Vue.js, *Security* (best practices). <https://vuejs.org/guide/best-practices/security.html>
