---
layout: post
title: "React가 Angular 대비 갖는 구조적 장점"
date: 2026-09-03 06:34:00 +0900
categories: [frontend, architecture]
tags: [React, Angular, JSX, frontend]
---

React와 Angular를 “더 나은 프레임워크”로 줄 세우는 것은 정확한 비교가 아니다. 둘은 애초에 같은 층위의 물건이 아니다. 이 글은 어느 쪽이 우월하다는 주장 대신, 공식 문서에 근거해 두 기술의 구조 차이가 실제로 어떤 상황에서 React 쪽에 유리하게 작동하는지를 정리한다.

## 1. 라이브러리 vs 프레임워크: 출발점이 다르다

React 저장소의 공식 설명은 다음과 같다.

> "React is a JavaScript library for building user interfaces."

반면 Angular 공식 문서는 스스로를 이렇게 소개한다.

> "Angular is a web framework that empowers developers to build fast, reliable applications that users love."

React는 UI를 그리는 라이브러리 하나이고, 라우팅·폼·HTTP 클라이언트·의존성 주입(DI) 같은 나머지는 프로젝트가 선택한다. Angular는 라우터·Forms·HTTP Client·DI를 프레임워크 안에 기본 포함한다. 이 차이가 이후의 모든 장단점의 원인이다.

| 구분 | React | Angular |
| --- | --- | --- |
| 자기 정의 | JavaScript library | Web framework |
| 라우팅 | 별도 라이브러리 선택 | 내장 |
| 폼 | 별도 선택 | 내장 |
| HTTP 클라이언트 | 별도 선택(fetch 등) | 내장(HttpClient) |
| DI | 없음 | 내장 |

## 2. 장점 1 — 기존 기술 스택에 가정을 두지 않는다

React README는 이렇게 명시한다.

> "We don't make assumptions about the rest of your technology stack, so you can develop new features in React without rewriting existing code."

> "React has been designed for gradual adoption from the start, and you can use as little or as much React as you need."

즉 React는 “전체를 React로 새로 짤 것”을 전제하지 않는다. 기존 서버 렌더링 화면, 레거시 jQuery 화면, 또는 다른 프레임워크가 이미 돌고 있는 페이지의 위젯 하나에만 React를 붙이는 것이 설계상 가정된 사용법이다. Angular는 프레임워크 전체가 하나의 애플리케이션 컨텍스트(모듈/DI 트리)를 구성하므로, 화면 한 조각만 떼어 붙이는 부분 도입이 React만큼 가볍지 않다.

레거시 화면을 한 번에 재작성할 여력이 없는 조직이라면, 이 차이는 실질적인 마이그레이션 리스크 차이로 이어진다.

## 3. 장점 2 — 템플릿 문법이 아니라 JavaScript 자체를 쓴다

React 공식 문서는 JSX를 이렇게 설명한다.

> "The markup syntax you've seen above is called JSX. It is optional, but most React projects use JSX for its convenience."

JSX는 별도의 템플릿 언어가 아니라 JavaScript 표현식 위에 얹힌 마크업 문법이다. 조건 분기나 반복은 프레임워크 전용 디렉티브(`*ngIf`, `*ngFor` 류) 대신 JavaScript의 삼항 연산자·`map`·`&&`를 그대로 쓴다. 배워야 할 문법 표면이 하나 줄어든다는 뜻이다. 반대급부로 JSX는 HTML보다 엄격해서(예: 모든 태그를 닫아야 하고, 컴포넌트는 다중 JSX 태그를 바로 반환할 수 없다) 별도 규칙을 익혀야 하는 것도 사실이다.

## 4. 장점 3 — 상태는 트리 안의 “위치”로 결정된다

React의 상태 보존 규칙은 문서에 명시적으로 정의돼 있다.

> "React keeps track of which state belongs to which component based on their place in the UI tree."

> "React preserves a component's state for as long as it's being rendered at its position in the UI tree. If it gets removed, or a different component gets rendered at the same position, React discards its state."

이 모델은 단순하지만 예측 가능하다는 장점이 있다. 같은 위치에 다른 컴포넌트가 렌더링되면 상태가 자동으로 초기화되고, `key`를 지정하면 명시적으로 상태 경계를 제어할 수 있다. 복잡한 조건부 UI에서 “왜 상태가 유지되거나 초기화되는가”를 추적할 때, 이 규칙 하나로 대부분 설명된다.

## 5. 장점 4 — 프레임워크 전체 업그레이드 주기에서 자유롭다

Angular는 릴리즈 주기를 문서로 공표한다.

> "A major release every 12 months"

> "All major releases are typically supported for 24 months."

즉 Angular를 채택하면 프레임워크가 정한 12개월 주기의 메이저 업그레이드 사이클에 팀 일정이 함께 묶인다. React는 라이브러리 하나이므로, 애플리케이션이 React 자체를 언제 올릴지와 라우터·상태관리 등 나머지 조각을 언제 올릴지를 각각 독립적으로 결정할 수 있다. 다만 이는 “강제 업그레이드가 없다”는 장점이자, 뒤집으면 “버전 조합을 프로젝트가 직접 관리해야 한다”는 부담이기도 하다.

## 6. 이건 장점이면서 동시에 대가다

공정하게 짚어야 할 부분이 있다. React가 라우팅·폼·DI·HTTP 클라이언트를 내장하지 않는다는 사실은 유연성이자 곧 선택 비용이다. Angular 팀이 문서에서 소개하는 Router·Forms·HttpClient·DI는 신규 프로젝트에서 “무엇을 쓸지 고르는 시간” 자체를 없애준다. 대규모 조직이 표준화된 도구 조합을 강제하고 싶다면, 오히려 Angular의 이런 내장 구조가 장점으로 작동한다.

## 7. 정리

```text
React가 유리한 상황:
  기존 화면에 부분적으로 UI를 얹어야 한다
  팀마다 라우팅·상태관리 조합을 다르게 가져가도 된다
  프레임워크 강제 업그레이드 주기에 묶이고 싶지 않다

Angular가 유리한 상황:
  라우팅·폼·HTTP·DI까지 하나의 표준으로 강제하고 싶다
  대규모 조직에서 도구 선택 자체를 줄이고 싶다
  12개월 주기의 예측 가능한 릴리즈·LTS 정책을 원한다
```

두 기술을 “좋다/나쁘다”로 비교하는 것보다, React는 라이브러리로서 최소 가정을, Angular는 프레임워크로서 최대 표준화를 목표로 설계됐다는 사실을 먼저 이해하는 편이 실제 선택에 더 도움이 된다.

## References

- [React 공식 저장소 README](https://github.com/facebook/react)
- [React 공식 문서 — Quick Start / JSX](https://react.dev/learn)
- [React 공식 문서 — Preserving and Resetting State](https://react.dev/learn/preserving-and-resetting-state)
- [Angular 공식 문서 — Overview](https://angular.dev/overview)
- [Angular 공식 문서 — Versioning and releases](https://angular.dev/reference/releases)

*이 글에 인용된 문구는 작성 시점 기준 공식 문서/저장소의 내용이며, 두 프로젝트 모두 버전에 따라 문서 내용이 달라질 수 있다.*
