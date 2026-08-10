---
layout: post
title: "React·Vue·JSP 비교: AX 시대에 어떤 UI 기술이 우위에 있는가"
date: 2026-08-10 17:00:00 +0900
categories: [frontend, architecture, ax]
tags: [React, Vue, JSP, AX, AI, Spring, frontend]
---

React·Vue·JSP는 모두 웹 화면을 만들 수 있지만, 같은 종류의 기술은 아니다. React와 Vue는 브라우저 중심의 컴포넌트 UI 생태계이고, JSP는 서버에서 HTML을 생성하는 Jakarta EE 계열의 서버 템플릿 기술이다.

따라서 “무조건 어떤 것이 최고인가?”보다 다음 질문이 먼저다.

```text
어디에서 렌더링할 것인가?
상태와 상호작용이 얼마나 복잡한가?
AI 기능을 어디에 붙일 것인가?
기존 Java/Spring 조직과 시스템을 얼마나 활용할 것인가?
운영·보안·배포 복잡성을 감당할 수 있는가?
```

이 글에서 말하는 AX는 AI Transformation 또는 AI Experience를 포함한다. 즉 AI를 호출하는 기능만이 아니라, 사용자의 의도를 이해하고 결과를 검증·수정·승인하는 제품 경험까지 포함한다.

## 1. 세 기술의 정체

| 기술 | 본질 | 주된 렌더링 | 강점 |
| --- | --- | --- | --- |
| React | UI 라이브러리·컴포넌트 생태계 | Client/Server 혼합 가능 | 복잡한 인터랙션·AI UI·생태계 |
| Vue | 점진적 프론트엔드 프레임워크 | SPA·SSR·SSG | 학습성·생산성·점진적 도입 |
| JSP | Jakarta EE 서버 페이지 템플릿 | Server-side HTML | 레거시 Java 통합·단순 서버 렌더링 |

React 공식 문서는 React를 컴포넌트와 Hook 중심으로 설명한다. Vue 공식 문서는 Vue를 반응성 기반의 “progressive framework”로 소개하며 SPA·SSR·SSG를 지원한다고 설명한다. Jakarta Server Pages는 동적 웹 콘텐츠를 생성하는 서버 페이지 기술이다.

## 2. React

### 장점

```text
컴포넌트 재사용
복잡한 상태 관리
대규모 프론트엔드 생태계
TypeScript와의 결합
SSR/RSC/SSG 선택지
AI SDK·스트리밍 UI 생태계
```

React는 화면을 작은 컴포넌트로 분해하고 상태 변화에 따라 UI를 갱신하는 모델에 적합하다. 실시간 스트리밍, 채팅, 파일 업로드, 도구 실행 결과, 승인·수정 화면처럼 상호작용이 많은 제품에서 강하다.

### 단점

```text
React 자체는 전체 애플리케이션 프레임워크가 아님
라우팅·데이터 fetching·상태관리 선택지가 많음
생태계가 빠르게 변함
Server/Client 경계 이해 필요
번들·hydration·캐시 최적화 필요
```

React를 선택하면 React만 선택하는 것이 아니다.

```text
React + Next.js 또는 다른 meta-framework
상태관리
서버 데이터 캐시
폼·검증
테스트
빌드·배포
```

를 함께 선택하게 된다.

### React가 우위인 분야

```text
AI chat/copilot
실시간 스트리밍 UI
복잡한 SaaS 대시보드
대규모 디자인 시스템
다양한 프론트엔드 인력 채용
B2C 제품의 고도화된 인터랙션
```

Vercel AI SDK 공식 문서는 React뿐 아니라 Vue·Svelte·Angular 등도 지원하지만, React 기반 문서·컴포넌트·제품 생태계가 특히 크다. AI Agent의 메시지·tool call·streaming result를 화면에 표현해야 한다면 React는 가장 안전한 기본 선택 중 하나다.

## 3. Vue

### 장점

```text
낮은 진입장벽
명확한 템플릿 문법
반응성 모델
점진적 도입
Composition API
SPA·SSR·SSG 선택지
```

Vue는 기존 HTML 화면에 점진적으로 추가할 수 있고, 규모가 커지면 SPA나 SSR 구조로 확장할 수 있다. React보다 팀 내 학습 비용과 선택지 피로가 낮다고 느끼는 조직도 많다.

### 단점

```text
React보다 좁은 글로벌 채용·생태계 풀
대규모 팀별 관례 차이
Nuxt 등 추가 프레임워크 선택 필요
복잡한 상태·실시간 UI에서 아키텍처 규율 필요
```

Vue가 단순하다는 것은 설계가 자동으로 좋아진다는 뜻은 아니다. 컴포넌트 경계, 상태 소유권, API contract, 테스트 전략을 별도로 정해야 한다.

### Vue가 우위인 분야

```text
기존 서버 페이지의 점진적 현대화
관리자 화면
중간 규모 SaaS
팀 생산성과 유지보수성 중시 조직
Nuxt 기반 SSR/콘텐츠 서비스
```

특히 JSP나 서버 렌더링 화면 전체를 한 번에 React로 바꾸기 어렵다면 다음 방식이 현실적이다.

```text
JSP 유지
→ 특정 화면·컴포넌트만 Vue 도입
→ 공통 API와 디자인 토큰 정리
→ 화면 단위 점진 전환
```

## 4. JSP

### 장점

```text
Spring MVC·Jakarta EE와 직접 통합
서버 렌더링 단순성
초기 Java 조직의 낮은 전환 비용
브라우저에 전달되는 HTML이 직관적
SEO·초기 렌더링이 단순
```

JSP는 서버에서 동적 HTML을 생성한다. 복잡한 브라우저 상태가 필요하지 않은 업무 화면, 기존 Java 웹 애플리케이션, 장기간 운영 중인 내부 시스템에서는 여전히 실용적일 수 있다.

### 단점

```text
복잡한 상호작용에 불리
프론트·백엔드 배포 결합
서버 왕복 증가
컴포넌트 생태계와 현대적 상태관리 부족
AI 스트리밍·실시간 UX 구현 난이도
```

JSP를 무조건 “낡아서 폐기”라고 말하는 것도 정확하지 않다. 문제는 기술의 나이가 아니라 요구사항과 운영 비용이다.

```text
단순 CRUD
내부 업무 화면
기존 Spring MVC 유지보수
낮은 변경 빈도
```

라면 JSP를 유지하는 편이 합리적일 수 있다. 반면 화면이 AI 대화·실시간 협업·복합 상태·풍부한 시각화로 확장되면 프론트엔드 현대화 필요성이 커진다.

## 5. 핵심 비교

| 평가 기준 | React | Vue | JSP |
| --- | --- | --- | --- |
| 복잡한 상호작용 | 매우 강함 | 강함 | 약함 |
| 학습 시작 난이도 | 중간 | 낮음~중간 | 낮음(기존 Java 팀 기준) |
| 대규모 생태계 | 매우 강함 | 강함 | 제한적 |
| 점진적 도입 | 가능하지만 설계 필요 | 매우 강함 | 기존 시스템에 자연스러움 |
| SSR/SSG | meta-framework 필요 | Nuxt 등 활용 | 기본 서버 렌더링 |
| AI streaming UI | 매우 강함 | 강함 | 구현 비용 큼 |
| 기존 Spring MVC 통합 | API 중심 | API 중심 | 직접 통합 |
| 화면과 백엔드 독립 배포 | 강함 | 강함 | 약함 |
| 단순 내부 CRUD | 과할 수 있음 | 적합 | 매우 적합 |
| 인력·생태계 | 가장 넓음 | 넓음 | 레거시 중심 |
| 장기 AX 제품 | 우위 | 충분히 경쟁력 있음 | 제한적 |

## 6. AX 시대의 프론트엔드 요구사항

AX 제품은 단순히 “LLM 답변을 보여주는 화면”이 아니다.

```text
사용자 의도 입력
→ Agent 처리 상태 표시
→ streaming 응답
→ tool call 표시
→ 근거·출처 표시
→ 사용자의 승인·수정
→ 실패·재시도
→ 결과 저장·감사
```

이 흐름에는 다음 UI 상태가 필요하다.

```text
idle
planning
streaming
tool-running
awaiting-approval
partial-result
failed
completed
```

또한 AI 결과에는 전통적인 CRUD보다 더 많은 불확실성이 있다.

```text
모델이 틀릴 수 있음
도구가 실패할 수 있음
권한이 다를 수 있음
응답이 늦을 수 있음
결과를 검토해야 함
```

따라서 AX 프론트엔드는 **상태·스트리밍·근거·승인·복구**를 1급 UI 개념으로 다뤄야 한다.

## 7. AX 시대의 기술별 우위

### 7.1 React: AI 제품 경험·생태계 우위

React는 다음 영역에서 가장 강한 선택이다.

```text
AI Copilot
Agent workspace
멀티패널 인터페이스
실시간 tool result
스트리밍 markdown
파일·이미지·코드 결과 미리보기
복합 승인 workflow
```

AI SDK와 UI 컴포넌트 생태계가 빠르게 확장되고, TypeScript 기반의 타입 계약을 적용하기 쉽다.

단, React를 선택했다는 이유로 AI 품질이 좋아지는 것은 아니다. Backend의 tool contract, trace, evaluation, permission policy가 더 중요하다.

### 7.2 Vue: 업무 AX·점진적 현대화 우위

Vue는 다음 경우에 강하다.

```text
기존 서버 페이지를 점진적으로 현대화
중간 규모 업무 시스템
AI 추천을 기존 화면에 단계적으로 삽입
작은 팀의 빠른 제품화
Nuxt 기반 SSR/콘텐츠와 AI 결합
```

예를 들어 Spring MVC/JSP 기반 상담 화면에서:

```text
기존 화면 유지
→ Vue 검색·추천 위젯 추가
→ Vue 대화 패널 추가
→ API/권한/감사 계약 정리
```

처럼 위험을 낮출 수 있다.

### 7.3 JSP: 안정적 운영·레거시 AX 접점에서의 우위

JSP가 AX 시대에 완전히 사라지는 것은 아니다. 다음 분야에서는 여전히 가치가 있다.

```text
은행·공공·기업 내부 업무
기존 Spring MVC 계정계 주변 화면
규정 변경이 잦지만 UI 상호작용은 단순한 시스템
장기간 유지되는 레거시 시스템
점진 현대화 전 안정적인 기준선
```

JSP 화면에 AI를 붙인다면 전체 UI를 한 번에 바꾸기보다:

```text
JSP:
  권한·업무 화면·기존 transaction 유지

React/Vue widget:
  검색 보조·요약·추천·대화·검토 UI

Spring API:
  AI orchestration·audit·policy
```

의 점진적 구조가 현실적이다.

## 8. Spring Backend와의 조합

### React + Spring

```text
React/Next.js:
  복합 UI·streaming·AI interaction

Spring Boot:
  domain·security·transaction·audit

MCP/AI service:
  tool orchestration·model routing
```

장점은 팀과 배포를 독립시킬 수 있다는 것이다. 단점은 인증·CORS·API contract·observability를 분명히 해야 한다.

### Vue + Spring

```text
Vue/Nuxt:
  업무 UI·SSR·점진 현대화

Spring Boot:
  domain·security·transaction
```

생산성과 전환 비용의 균형이 좋다.

### JSP + Spring

```text
Spring MVC:
  controller·service·transaction

JSP:
  서버 렌더링 화면
```

운영 단순성이 장점이지만, AI streaming·복합 client state·독립 배포가 필요해질수록 별도 API/Widget 구조가 필요하다.

## 9. 선택 기준

| 상황 | 추천 |
| --- | --- |
| 신규 AI Copilot·Agent 제품 | React 우선 검토 |
| 대규모 디자인 시스템·복합 대시보드 | React |
| 중간 규모 업무 시스템·빠른 개발 | Vue |
| 기존 JSP의 단계적 현대화 | Vue 또는 React widget |
| 단순 Java 내부 CRUD | JSP 유지 가능 |
| 금융·공공 레거시와 안정성 우선 | JSP 유지 + 선택적 Vue/React |
| 콘텐츠·SSR·SEO와 AI 결합 | React meta-framework 또는 Nuxt |
| 여러 프론트엔드 팀과 채용 시장 고려 | React |

## 10. 최종 판단

```text
React:
  AX 제품 경험·복잡한 상호작용·AI streaming에 가장 강한 기본 선택

Vue:
  생산성·점진적 현대화·중간 규모 업무 AX에 강한 균형 선택

JSP:
  기존 Java 시스템의 안정적 운영과 저위험 유지보수에 강한 선택
```

따라서 AX 시대의 우위는 다음처럼 정리할 수 있다.

```text
새로운 AI 제품을 만든다:
  React 우위

기존 업무 시스템에 AI를 단계적으로 넣는다:
  Vue 우위 또는 React widget

기존 금융·공공 Java 시스템을 안정적으로 유지한다:
  JSP도 여전히 유효
```

가장 현실적인 엔터프라이즈 전략은 하나를 전부 선택하는 것이 아니다.

```text
JSP:
  레거시 transaction·권한·업무 화면 유지

Vue:
  점진적 업무 UI 현대화

React:
  새로운 AI workspace·Copilot·복합 상호작용

Spring:
  domain·security·transaction·audit의 중심
```

## References

- [React 공식 문서](https://react.dev/reference/react)
- [Vue 공식 문서](https://vuejs.org/guide/introduction.html)
- [Jakarta Server Pages 공식 사양](https://jakarta.ee/specifications/pages/)
- [Vercel AI SDK 공식 문서](https://ai-sdk.dev/docs/introduction)
- [React·Vue·JSP 비교에 참고한 공식 기술 문서](https://react.dev/)

*React·Vue·JSP의 기능과 생태계는 버전에 따라 달라질 수 있다. “AX 시대의 우위”는 기술 자체의 절대 우열이 아니라 AI 상호작용·팀 역량·기존 시스템·운영 비용을 함께 고려한 아키텍처 판단이다.*

*공개 글에는 credential, token, private IP, 내부 endpoint를 포함하지 않았다.*
