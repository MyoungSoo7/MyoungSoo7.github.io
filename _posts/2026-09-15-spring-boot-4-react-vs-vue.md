---
layout: post
title: "스프링부트 4 백엔드에서 React vs Vue — 프레임워크 비교가 아니라 '경계 설계' 비교다"
date: 2026-09-15 22:40:00 +0900
categories: [Engineering, Web]
tags: [Spring Boot 4, React, Vue, SPA, CORS, Vite, frontend-maven-plugin]
---

React 와 Vue 자체의 비교(변경 감지 모델, JSX vs SFC, 생태계)는 [이틀 전 글](/2026/09/13/react-vs-vue-2026-differences-and-tradeoffs/)에서 다뤘다. 오늘의 질문은 다르다 — **백엔드가 스프링부트 4 로 정해져 있을 때**, 그 옆자리에 React 를 앉히느냐 Vue 를 앉히느냐는 무엇으로 갈리는가.

먼저 김을 빼자. 스프링부트 입장에서 React 와 Vue 는 **기술적으로 동일한 존재**다. 둘 다 빌드하면 정적 파일 묶음(HTML/JS/CSS)이 되고, 둘 다 REST/JSON 으로 대화하며, 둘 다 [Vite](https://vite.dev/config/server-options.html) 로 개발 서버를 돌린다. 부트 4 가 React 만 지원하거나 Vue 와 더 잘 붙는 API 를 갖고 있는 것이 아니다. 그래서 이 선택은 프레임워크 기능 비교가 아니라 **세 가지 경계 설계 + 한 가지 조직 문제**로 정리된다.

## 1. 배포 경계 — 한 JAR 로 묶을 것인가, 둘로 나눌 것인가

### 방식 A: 부트 JAR 에 프론트를 내장

빌드 시 프론트를 컴파일해 부트의 정적 리소스 위치(`classpath:/static` 등 — [부트 공식 문서의 정적 콘텐츠 규약](https://docs.spring.io/spring-boot/reference/web/servlet.html))에 밀어 넣으면 JAR 하나로 배포가 끝난다. Maven 이라면 [frontend-maven-plugin](https://github.com/eirslett/frontend-maven-plugin) 이 Node 설치부터 `npm run build` 까지 빌드 라이프사이클에 편입시켜 준다. CORS 문제도 원천적으로 없다 — 같은 origin 이니까.

- **React 든 Vue 든 차이 없음.** 둘 다 `dist/` 를 복사하는 것뿐이다.
- 소규모 팀·admin 툴·사내 서비스에서 강력하다. 배포 파이프라인이 하나다.
- 대가: 프론트 한 줄 고쳐도 백엔드 재배포, 프론트/백 릴리스 주기가 묶인다.

### 방식 B: 분리 배포 (SPA 는 CDN/정적 호스팅, 부트는 API 만)

릴리스 주기가 분리되고 프론트 배포가 초 단위가 된다. 대가로 **CORS 가 정면에 온다** — 부트 쪽에서 [스프링 공식 CORS 설정](https://docs.spring.io/spring-framework/reference/web/webmvc-cors.html)(`@CrossOrigin` 또는 전역 `CorsConfiguration`)을 명시해야 하고, 쿠키 세션을 쓸 거면 `allowCredentials` 와 origin 화이트리스트를 정확히 맞춰야 한다.

여기도 **React/Vue 차이는 없다.** 갈리는 건 팀의 운영 역량이다 — 배포 대상이 둘이 되는 비용을 감당할 규모인가.

## 2. 개발 루프 경계 — 어차피 둘 다 Vite 프록시다

개발 중에는 프론트 개발 서버(HMR)와 부트(8080)가 따로 뜬다. 이때 [Vite 의 `server.proxy`](https://vite.dev/config/server-options.html) 로 `/api` 를 부트로 넘기는 구성이 표준이고, 이 설정 파일은 React 프로젝트든 Vue 프로젝트든 **글자 하나까지 같다**:

```js
// vite.config.js — React/Vue 공통
export default {
  server: { proxy: { '/api': 'http://localhost:8080' } }
}
```

한때 React(CRA)와 Vue(vue-cli)의 개발 서버가 달라 설정법이 갈렸지만, [React 공식 문서](https://react.dev/learn/creating-a-react-app)와 [Vue 공식 문서](https://vuejs.org/guide/introduction.html) 모두 Vite 기반 툴체인으로 수렴한 지금은 이 경계에서 차이가 소멸했다.

## 3. 보안 경계 — Spring Security 와의 궁합도 무승부, 단 숙제는 공통

SPA + 부트 조합이면 인증은 대개 "쿠키 세션 + CSRF 토큰" 또는 "토큰(JWT) + Authorization 헤더" 다. 전자를 고르면 [Spring Security 공식 문서의 SPA 용 CSRF 설정](https://docs.spring.io/spring-security/reference/servlet/exploits/csrf.html)(쿠키로 토큰을 노출하고 JS 가 헤더로 되돌려주는 패턴)을 따라야 하는데 — 이 문서가 요구하는 것은 프론트가 쿠키를 읽어 헤더에 싣는 것뿐이라 **React 와 Vue 어느 쪽도 유불리가 없다.** axios/fetch 레벨의 일이지 프레임워크 레벨의 일이 아니기 때문이다.

## 4. 그래서 진짜 갈림길 — 조직과 코드베이스의 모양

기술 경계 세 곳이 전부 무승부라면, 선택은 [일반 비교 글](/2026/09/13/react-vs-vue-2026-differences-and-tradeoffs/)에서 본 프레임워크 자체의 성격과 **스프링 백엔드 팀이라는 맥락**의 교차점에서 난다.

| 관점 | React 쪽으로 기우는 경우 | Vue 쪽으로 기우는 경우 |
| --- | --- | --- |
| 팀 구성 | 프론트 전담 인력이 있고 채용 풀을 넓게 유지해야 함 | 자바 개발자가 프론트까지 겸업 (풀스택 강제) |
| 학습 곡선 | JS 생태계에 이미 익숙 | 템플릿 문법(SFC)이 JSP/Thymeleaf 경험자에게 진입이 완만 |
| 코드베이스 성격 | 거대한 서드파티 생태계·디자인시스템 의존 | 공식 라우터·상태관리로 "정답이 하나인" 구조 선호 |
| 스프링과의 유사성 | — | 관례 기반·공식 스택 일체형이라는 철학이 스프링과 닮음 |

특히 "자바 백엔드 개발자가 프론트를 겸업하는" 국내 SI·사내 시스템 맥락에서는 Vue 의 SFC(템플릿/스크립트/스타일 분리)가 JSP·Thymeleaf 에서 넘어오는 인지 비용이 낮다는 점이 실무에서 자주 결정타가 된다. 반대로 프론트를 독립 직군으로 운영하는 조직이라면 채용 시장과 생태계 크기에서 React 가 안전한 기본값이다.

## 결론

1. **부트 4 와의 기술 궁합은 무승부다.** 배포·개발 루프·보안 세 경계 모두 React/Vue 가 완전히 동일한 방식으로 붙는다. "스프링에는 X 가 더 잘 맞는다" 는 주장을 만나면 근거를 요구하라 — 대부분 조직 경험담이지 기술 제약이 아니다.
2. 따라서 결정 변수는 둘로 준다: **누가 프론트를 짜는가**(전담 vs 겸업), **릴리스 주기를 묶을 것인가**(내장 vs 분리).
3. 겸업+내장이면 Vue, 전담+분리면 React 가 통계적으로 무난한 조합이고, 그 반대 조합도 틀린 게 아니라 비용을 아는 선택이면 된다.

## References

- Spring Boot — [Servlet Web Applications: Static Content](https://docs.spring.io/spring-boot/reference/web/servlet.html) · [프로젝트 홈](https://spring.io/projects/spring-boot)
- Spring Framework — [CORS](https://docs.spring.io/spring-framework/reference/web/webmvc-cors.html)
- Spring Security — [Cross Site Request Forgery (SPA 패턴 포함)](https://docs.spring.io/spring-security/reference/servlet/exploits/csrf.html)
- Vite — [Server Options (proxy)](https://vite.dev/config/server-options.html)
- React — [Creating a React App](https://react.dev/learn/creating-a-react-app) / Vue — [Introduction](https://vuejs.org/guide/introduction.html)
- eirslett — [frontend-maven-plugin](https://github.com/eirslett/frontend-maven-plugin)
