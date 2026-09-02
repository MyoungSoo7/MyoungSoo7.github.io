---
layout: post
title: 리액트의 역사
date: 2026-09-03 06:16:40 +0900
categories: [Frontend]
tags: [React, History, JavaScript]
---

리액트(React)는 [Jordan Walke가 만든](https://react.dev/community/acknowledgements) 사용자 인터페이스 라이브러리다. 2013년 공개된 이후 13년 동안 프론트엔드의 기본 문법을 바꿔놓았고, 2026년 2월에는 Meta의 소유를 떠나 독립 재단으로 이관됐다.

이 글은 리액트 공식 블로그에 남아 있는 발표문을 따라 그 궤적을 정리한 것이다. 모든 날짜는 공식 릴리스 포스트 기준이다.

## 템플릿을 버리며 시작하다 (2013)

리액트 공식 블로그의 첫 글은 2013년 6월 5일 "[Why did we build React?](https://legacy.reactjs.org/blog/2013/06/05/why-react.html)"였다. 이 글이 내세운 주장은 지금 봐도 리액트의 정체성 그 자체다.

- **리액트는 MVC 프레임워크가 아니다.** 시간에 따라 변하는 데이터를 표현하는 재사용 가능한 컴포넌트를 만드는 라이브러리다.
- **리액트는 템플릿을 쓰지 않는다.** 당시 웹 UI는 템플릿이나 HTML 디렉티브로 만드는 게 상식이었는데, 리액트는 뷰를 렌더링하는 데 템플릿 언어 대신 자바스크립트라는 완전한 프로그래밍 언어를 그대로 쓴다.

같은 글은 마크업과 뷰 로직을 한데 묶으면 문자열을 손으로 이어붙일 일이 없어져 XSS 표면이 줄어든다는 점도 근거로 들었다. 당시엔 "HTML을 자바스크립트 안에 쓴다니" 하는 거부감이 컸지만, 결국 이 결정이 JSX와 컴포넌트 모델로 굳어졌다.

## 0.x 시대와 리액트 네이티브 (2015-2016)

2015년 3월 26일, [리액트 네이티브가 발표됐다](https://legacy.reactjs.org/blog/2015/03/26/introducing-react-native.html). 웹에서 검증된 컴포넌트 모델을 모바일 네이티브 UI로 가져간 것으로, "한 번 배워서 어디에나 쓴다(learn once, write anywhere)"는 표현이 여기서 나왔다.

2015년 10월 7일 [0.14](https://legacy.reactjs.org/blog/2015/10/07/react-v0.14.html)에서 패키지가 `react`와 `react-dom`으로 갈라졌다. 렌더링 대상이 DOM만이 아니게 되면서 코어와 렌더러를 분리한 것인데, 오늘날 리액트가 웹·모바일·서버를 동시에 겨냥하는 구조의 출발점이었다.

[15.0](https://legacy.reactjs.org/blog/2016/04/07/react-v15.html)은 2016년 4월에 나왔다.

## 라이선스 논란과 Fiber (2017)

리액트 초기의 BSD + 특허 라이선스 조합은 채택을 망설이게 하는 요인이었다. 2017년 9월 22일 Facebook(현 Meta)은 [React, Jest, Flow, Immutable.js를 MIT 라이선스로 재라이선스한다고 발표했다](https://engineering.fb.com/2017/09/22/web/relicensing-react-jest-flow-and-immutable-js/).

그로부터 나흘 뒤인 2017년 9월 26일 [React 16.0](https://legacy.reactjs.org/blog/2017/09/26/react-v16.0.html)이 나왔다. 내부 렌더러를 "Fiber"로 완전히 다시 쓴 릴리스로, 에러 바운더리·포털·프래그먼트 반환 같은 기능이 여기서 들어왔다. 이후 몇 년간의 동시성 작업은 전부 이 Fiber 위에서 이뤄진다.

## Hooks — 클래스 없는 리액트 (2018-2019)

2018년 [React Conf](https://legacy.reactjs.org/blog/2018/11/13/react-conf-recap.html)에서 Hooks가 제안됐고, 정식 릴리스는 2019년 2월 6일 [16.8.0](https://legacy.reactjs.org/blog/2019/02/06/react-v16.8.0.html)이었다.

클래스 컴포넌트 없이 함수 안에서 상태와 생명주기를 다룰 수 있게 되면서, 리액트 코드의 생김새가 실질적으로 한 번 더 바뀌었다. `this` 바인딩, HOC 중첩, render prop 지옥이 상당 부분 정리됐다.

## 17 — 아무 기능도 넣지 않은 메이저 버전 (2020)

2020년 10월의 [React 17](https://legacy.reactjs.org/blog/2020/10/20/react-v17.html)은 이상한 릴리스였다. 공식 발표문이 직접 이렇게 쓴다.

> The React 17 release is unusual because it doesn't add any new developer-facing features.

목적은 **점진적 업그레이드**였다. 그때까지는 앱 전체를 한 번에 올려야 했는데, 오래된 코드베이스에는 그게 부담이었다. 17은 서로 다른 버전의 리액트 트리를 한 페이지에 안전하게 얹을 수 있게 만들어, 다음 메이저(18)로 갈 때 앱을 조각 단위로 옮길 수 있는 길을 열었다. 이를 위해 이벤트 시스템을 손봤고, 그 변경이 깨질 수 있어 메이저 버전을 붙였다.

같은 해 12월 21일에는 [zero-bundle-size React Server Components](https://react.dev/blog/2020/12/21/data-fetching-with-react-server-components)가 공개됐다. 이후 5년간 리액트의 방향을 지배하는 아이디어다.

## 18 — 동시성 렌더러 (2022)

2022년 3월 29일 [React 18](https://react.dev/blog/2022/03/29/react-v18)이 나왔다. 새 동시성 렌더러 위에서 동작하는 기능들을 담았고, 기존 앱이 한꺼번에 갈아엎지 않고 점진적으로 채택할 수 있게 설계됐다 — 17이 깔아둔 길 위에서다.

이 시기의 특징은 리액트 팀이 작업 과정을 공개하기 시작했다는 점이다. [React Labs](https://react.dev/blog/2022/06/15/react-labs-what-we-have-been-working-on-june-2022) 연재가 시작됐고, 2023년 5월 3일에는 [Canary 릴리스 채널](https://react.dev/blog/2023/05/03/react-canaries)이 공식 채널로 추가됐다. 프레임워크가 리액트 릴리스 주기와 무관하게 개별 기능을 먼저 채택할 수 있게 한 조치로, 이전까지 Meta 내부에서 먼저 쓰이던 기능들을 커뮤니티가 같은 시점에 쓸 수 있게 됐다.

2023년 3월 16일에는 문서 사이트가 [react.dev](https://react.dev/blog/2023/03/16/introducing-react-dev)로 새로 열렸다.

## 19 — Actions와 서버 컴포넌트의 정식화 (2024)

2024년 12월 5일 [React 19](https://react.dev/blog/2024/12/05/react-19)가 안정 버전이 됐다. 공식 발표문이 나열한 주요 항목은 다음과 같다.

- **Actions** — 그리고 `useActionState`, `<form>` Actions, `useFormStatus`, `useOptimistic`
- **`use` API** — 렌더링 중 Promise와 컨텍스트를 읽는 새 API
- **React Server Components / Server Actions**
- 그 외: prop으로서의 `ref`, `<Context>`를 provider로 직접 사용, ref 정리 함수, 문서 메타데이터·스타일시트·async 스크립트 지원, 하이드레이션 오류 diff, 커스텀 엘리먼트 지원

## 도구의 세대교체 (2025)

2025년 2월 14일, 리액트 팀은 [Create React App을 종료했다](https://react.dev/blog/2025/02/14/sunsetting-create-react-app). 신규 앱에는 프레임워크를 쓰거나, 프레임워크가 맞지 않으면 Vite·Parcel·RSBuild 같은 빌드 도구로 옮기라는 권고였다. 오랫동안 "리액트 배우기 = CRA"였던 기본 진입로가 공식적으로 닫힌 것이다.

10월에는 굵직한 게 몰렸다.

- **[React 19.2](https://react.dev/blog/2025/10/01/react-19-2)** (10월 1일) — `Activity`, React Performance Tracks, `useEffectEvent` 등
- **[React Compiler v1.0](https://react.dev/blog/2025/10/07/react-compiler-1)** (10월 7일) — 2024년 10월 [베타](https://react.dev/blog/2024/10/21/react-compiler-beta-release)를 거쳐 첫 안정 릴리스. 손으로 `useMemo`/`useCallback`을 붙이던 최적화를 컴파일러가 대신한다
- **[React Foundation 설립 발표](https://react.dev/blog/2025/10/07/introducing-the-react-foundation)** (10월 7일)

12월은 반대로 어두웠다. 12월 3일 [React Server Components에서 인증 없이 원격 코드 실행이 가능한 치명적 취약점](https://react.dev/blog/2025/12/03/critical-security-vulnerability-in-react-server-components)이 공개됐고(19.0.1 / 19.1.2 / 19.2.1에서 수정), 12월 11일에는 그 패치를 우회하려던 연구자들이 [DoS와 소스 코드 노출 취약점 2건을 추가로 발견](https://react.dev/blog/2025/12/11/denial-of-service-and-source-code-exposure-in-react-server-components)했다. 서버로 넘어간 리액트가 서버의 위협 모델을 함께 짊어지게 됐다는 신호였다.

## Meta를 떠나다 (2026)

2026년 2월 24일, [React Foundation이 Linux Foundation 산하 독립 재단으로 공식 출범했다](https://react.dev/blog/2026/02/24/the-react-foundation).

> React, React Native, and supporting projects like JSX are no longer owned by Meta — they are now owned by the React Foundation.

플래티넘 창립 멤버는 8곳이고, 이사회는 각 멤버 대표로 구성된다. 다만 발표문은 **기술적 방향은 재단 이사회와 항상 독립**이라고 못박았다 — 기술 거버넌스는 리액트에 기여하고 유지보수하는 사람들이 계속 정하며, 그 구조를 정하기 위한 임시 리더십 협의회가 꾸려졌다.

저장소 이관도 함께 진행 중이다. 2026년 9월 3일 확인한 결과 `github.com/facebook/react`는 `github.com/react/react`로 301 리다이렉트된다.

## 정리

| 시기 | 사건 |
|------|------|
| 2013.06 | 첫 공식 블로그 글 — 템플릿 대신 컴포넌트 |
| 2015.03 | React Native 발표 |
| 2015.10 | 0.14, `react` / `react-dom` 분리 |
| 2017.09 | MIT 재라이선스, 16.0 (Fiber) |
| 2019.02 | 16.8, Hooks 정식 |
| 2020.10 | 17, 기능 없는 메이저 — 점진적 업그레이드 |
| 2020.12 | React Server Components 공개 |
| 2022.03 | 18, 동시성 렌더러 |
| 2023.03 | react.dev 오픈 |
| 2024.12 | 19, Actions / RSC 정식 |
| 2025.02 | Create React App 종료 |
| 2025.10 | 19.2, React Compiler v1.0, 재단 설립 발표 |
| 2025.12 | RSC 치명적 취약점 3건 |
| 2026.02 | React Foundation 정식 출범 |

2026년 9월 3일 기준 npm의 `react` 최신 버전은 **19.2.8**, 라이선스는 MIT다(npm 레지스트리 실측).

13년을 관통하는 흐름은 한 문장으로 요약된다. **템플릿을 버리고 컴포넌트로 시작해, 클래스를 버리고 함수로 가고, 클라이언트만이 아니라 서버까지 같은 모델로 덮은 뒤, 마지막에 회사의 소유에서 벗어났다.**

---

## References

- React, "[Why did we build React?](https://legacy.reactjs.org/blog/2013/06/05/why-react.html)" (2013-06-05) — 첫 공식 블로그 글
- React, "[Introducing React Native](https://legacy.reactjs.org/blog/2015/03/26/introducing-react-native.html)" (2015-03-26)
- React, "[React v0.14](https://legacy.reactjs.org/blog/2015/10/07/react-v0.14.html)" (2015-10-07) — 패키지 분리
- React, "[React v15.0](https://legacy.reactjs.org/blog/2016/04/07/react-v15.html)" (2016-04-07)
- Meta Engineering, "[Relicensing React, Jest, Flow, and Immutable.js](https://engineering.fb.com/2017/09/22/web/relicensing-react-jest-flow-and-immutable-js/)" (2017-09-22) — MIT 전환
- React, "[React v16.0](https://legacy.reactjs.org/blog/2017/09/26/react-v16.0.html)" (2017-09-26) — Fiber
- React, "[React Conf Recap: Hooks, Suspense, and Concurrent Rendering](https://legacy.reactjs.org/blog/2018/11/13/react-conf-recap.html)" (2018-11-13)
- React, "[React v16.8: The One With Hooks](https://legacy.reactjs.org/blog/2019/02/06/react-v16.8.0.html)" (2019-02-06)
- React, "[React v17.0](https://legacy.reactjs.org/blog/2020/10/20/react-v17.html)" (2020-10-20)
- React, "[Introducing Zero-Bundle-Size React Server Components](https://react.dev/blog/2020/12/21/data-fetching-with-react-server-components)" (2020-12-21)
- React, "[React v18.0](https://react.dev/blog/2022/03/29/react-v18)" (2022-03-29)
- React, "[Introducing react.dev](https://react.dev/blog/2023/03/16/introducing-react-dev)" (2023-03-16)
- React, "[React Canaries](https://react.dev/blog/2023/05/03/react-canaries)" (2023-05-03)
- React, "[React v19](https://react.dev/blog/2024/12/05/react-19)" (2024-12-05)
- React, "[Sunsetting Create React App](https://react.dev/blog/2025/02/14/sunsetting-create-react-app)" (2025-02-14)
- React, "[React 19.2](https://react.dev/blog/2025/10/01/react-19-2)" (2025-10-01)
- React, "[React Compiler v1.0](https://react.dev/blog/2025/10/07/react-compiler-1)" (2025-10-07)
- React, "[Introducing the React Foundation](https://react.dev/blog/2025/10/07/introducing-the-react-foundation)" (2025-10-07)
- React, "[Critical Security Vulnerability in React Server Components](https://react.dev/blog/2025/12/03/critical-security-vulnerability-in-react-server-components)" (2025-12-03)
- React, "[Denial of Service and Source Code Exposure in React Server Components](https://react.dev/blog/2025/12/11/denial-of-service-and-source-code-exposure-in-react-server-components)" (2025-12-11)
- React, "[The React Foundation: A New Home for React Hosted by the Linux Foundation](https://react.dev/blog/2026/02/24/the-react-foundation)" (2026-02-24)
- React, "[Acknowledgements](https://react.dev/community/acknowledgements)" — 최초 제작자 표기
- React, "[Versions](https://react.dev/versions)" — 버전별 릴리스 시기
