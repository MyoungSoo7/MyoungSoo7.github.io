---
layout: post
title: "React와 Vue의 차이는 '변경을 어떻게 알아내는가' 하나에서 갈린다"
date: 2026-09-13 02:07:30 +0900
categories: [frontend, architecture]
tags: [React, Vue, JSX, SFC, reactivity, frontend]
---

React와 Vue 비교 글은 이미 많다. 대부분 "React는 자유롭고 Vue는 쉽다" 같은 인상 비평으로 끝난다. 그런데 두 기술의 문법·생태계·최적화 전략 차이는 사실 **하나의 설계 결정**에서 파생된 결과다. 바로 **상태가 바뀐 걸 프레임워크가 어떻게 알아내는가**다.

이 글은 그 한 갈래에서 나머지가 어떻게 따라 나오는지를 양쪽 공식 문서만 근거로 정리한다. 성능 우열은 단정하지 않는다 — 뒤에서 왜 단정할 수 없는지도 같이 적는다.

기준 시점은 2026년 9월 13일이고, 이 시점의 안정 버전은 **React 19.3.0**(2026-09-09 릴리스, View Transitions·Fragment Refs가 정식화된 버전)과 **Vue 3.5.42**(2026-08-27 릴리스)다.[^react193][^vuenpm]

---

## 1. 2026년에 달라진 전제 세 가지

오래된 비교 글을 그대로 믿으면 틀리는 지점부터 짚는다.

**① React는 더 이상 Meta 소유가 아니다.** 2026년 2월 24일, React·React Native·JSX의 소유권이 Linux Foundation 산하 **React Foundation** 으로 이관됐다. 공식 발표문 그대로다 — "React, React Native, and supporting projects like JSX are no longer owned by Meta — they are now owned by the React Foundation, an independent foundation hosted by the Linux Foundation."[^foundation] Linux Foundation 보도자료는 초기 플래티넘 멤버로 Amazon·Callstack·Expo·Huawei·Meta·Microsoft·Software Mansion·Vercel 을 명시한다.[^lf] 실제로 GitHub 저장소 경로도 `facebook/react` 에서 `react/react` 로 옮겨졌다(옛 주소는 리다이렉트된다). 다만 저장소의 `LICENSE` 파일 저작권 줄은 아직 "Copyright (c) Meta Platforms, Inc. and affiliates." 그대로다.[^reactlicense]

**② React Compiler는 이제 정식 버전이다.** 2025년 10월 7일 1.0 이 나왔다 — "We are releasing the compiler's first stable release today. … automatically optimizes components and hooks without requiring rewrites."[^compiler] 이건 뒤의 4절에서 중요한 의미를 갖는다.

**③ Vue의 Vapor Mode는 아직 정식 버전이 아니다.** 3.6 RC에서 "feature-complete" 상태이고, 3.6.0 정식 릴리스는 이 글을 쓰는 시점에 존재하지 않는다(GitHub 태그·npm 모두 404, 최신은 `3.6.0-rc.8`). RC 릴리스 노트의 표현은 "Vue 3.6 is now entering the RC phase as we have completed the intended feature set for Vapor Mode."[^vapor] 그리고 Vue 공식 릴리스 정책은 프리릴리스에 대해 이렇게 못박는다 — "Do not use pre-releases in production."[^vuereleases] **즉 2026년 9월 현재, "Vue는 이제 가상 DOM을 안 쓴다"는 서술은 정식 버전 기준으로는 사실이 아니다.**

---

## 2. 뿌리의 차이 — 변경 감지 모델

### React: 다시 호출해서 알아낸다

React는 상태가 바뀌면 **컴포넌트 함수를 다시 호출한다.** 공식 문서의 정의가 문자 그대로 그렇다 — "'Rendering' is React calling your components."[^rendercommit] 렌더가 일어나는 이유도 딱 두 가지로 못박혀 있다: 최초 렌더이거나, "The component's (or one of its ancestors') state has been updated."[^rendercommit]

여기서 괄호 안이 핵심이다. **조상의 상태가 바뀌어도 하위가 다시 호출된다.** React는 "무엇이 바뀌었는지"를 추적하지 않는다. 다시 실행해서 나온 결과를 이전 결과와 비교할 뿐이다. 그래서 React는 렌더 함수가 순수할 것을 요구한다 — "Same inputs, same output."[^rendercommit]

### Vue: 읽는 순간을 가로채서 알아낸다

Vue는 반대다. 값을 **읽을 때** 누가 읽었는지를 기록해두고, **쓸 때** 그 기록된 대상만 깨운다. 공식 심화 문서의 서술이다:

> "If a variable is read when there is a currently running effect, make that effect a subscriber to that variable."
> "Detect when a variable is mutated. E.g. when `A0` is assigned a new value, notify all its subscriber effects to re-run."[^reactivity]

이 가로채기는 Vue 3에서 **Proxy**(반응형 객체)와 **getter/setter**(ref)로 구현된다. Vue 2가 getter/setter만 쓴 건 당시 브라우저 지원 한계 때문이었다고 같은 문서가 밝힌다.[^reactivity]

Vue 공식 문서는 이 구조가 signals와 같은 계열임을 인정한다 — "Fundamentally, signals are the same kind of reactivity primitive as Vue refs." 다만 렌더링까지 세밀하게 쪼개는 건 아니라고 덧붙인다: "Due to the use of Virtual DOM, Vue currently relies on compilers to achieve similar optimizations."[^reactivity]

### 한 줄 요약

| | React | Vue |
|---|---|---|
| 변경을 아는 방법 | 다시 호출하고 결과를 비교 | 읽기를 가로채 의존성을 기록 |
| 추적 단위 | 컴포넌트 | 개별 값(ref/reactive 속성) |
| 대가 | 불필요한 재실행 | 반응형 객체라는 별도 개념 |

**뒤에 나오는 모든 차이는 이 표에서 파생된다.**

---

## 3. 그래서 코드 모양이 갈린다 — JSX vs SFC

React는 "다시 호출되는 함수"가 단위이므로, 마크업이 **JavaScript 표현식**이면 가장 자연스럽다. 공식 문서의 논거는 역사적이다:

> "But as the Web became more interactive, logic increasingly determined content. JavaScript was in charge of the HTML! This is why **in React, rendering logic and markup live together in the same place—components.**"[^jsx]

같은 문서는 JSX가 필수가 아니라는 점도 명시한다 — "JSX and React are two separate things."[^jsx]

Vue는 "정적으로 분석해서 컴파일러가 최적화한다"가 전제이므로, **템플릿**이 유리하다. 이유가 공식 문서에 그대로 적혀 있다:

> "Templates are easier to statically analyze due to their more deterministic syntax. This allows Vue's template compiler to apply many compile-time optimizations…"[^rendering]

그리고 Vue는 이 조합에 이름까지 붙였다 — **"Compiler-Informed Virtual DOM"**.[^rendering] 렌더 함수도 쓸 수 있지만 "Render functions are typically only used in reusable components that need to deal with highly dynamic rendering logic" 이라고 선을 긋는다.[^rendering]

SFC(`.vue` 한 파일에 template·script·style)에 대한 흔한 비판 — 관심사 분리 위반 — 에도 공식 답변이 있다:

> "separation of concerns is not equal to the separation of file types"
> "Inside a component, its template, logic, and styles are inherently coupled, and colocating them actually makes the component more cohesive and maintainable."[^sfc]

`<script setup>` 은 2021년 8월 Vue 3.2 에서 실험 딱지를 뗐고, 지금은 "the recommended syntax if you are using both SFCs and Composition API" 다.[^v32][^scriptsetup]

코드로 보면 차이가 분명하다.

React (JSX):

```jsx
function Counter() {
  const [count, setCount] = useState(0);
  const doubled = count * 2;            // 매 렌더마다 다시 계산된다
  return <button onClick={() => setCount(count + 1)}>{count} / {doubled}</button>;
}
```

Vue (SFC):

{% raw %}
```vue
<script setup>
import { ref, computed } from 'vue'
const count = ref(0)
const doubled = computed(() => count.value * 2)   // count 가 바뀔 때만 다시 계산된다
</script>

<template>
  <button @click="count++">{{ count }} / {{ doubled }}</button>
</template>
```
{% endraw %}

같은 화면인데, React 쪽은 "함수 전체가 다시 돈다"가 기본값이고 Vue 쪽은 "의존하는 값이 바뀐 것만 다시 돈다"가 기본값이다. `count.value` 의 `.value` 가 거슬린다면, 그건 **가로채기를 위해 값을 객체로 감싼 대가**다. 공짜로 얻는 게 아니다.

---

## 4. 그래서 최적화의 책임자가 갈린다

React의 기본값(전부 다시 호출)은 필연적으로 과잉 재실행을 만든다. 그래서 오랫동안 `memo`·`useMemo`·`useCallback` 을 **사람이** 손으로 붙이는 게 React 숙련도의 상당 부분이었다.

**React Compiler 1.0(2025-10-07 정식)은 이 책임을 도구로 옮긴 사건이다.** 공식 소개는 "a new build-time tool that automatically optimizes your React app" 이고, 릴리스 글은 "battle tested on major apps at Meta and is fully production-ready" 라고 적는다.[^compilerdocs][^compiler]

Vue는 같은 문제를 처음부터 다른 층에서 풀었다. 무엇이 바뀌었는지를 런타임이 이미 알고 있고(2절), 템플릿 컴파일러가 정적 부분을 미리 걷어낸다(3절). 그래서 Vue 사용자에게는 "메모이제이션을 어디에 붙이지"라는 고민 자체가 거의 없다.

여기서 흥미로운 수렴이 보인다. **React는 컴파일러를 붙여 Vue가 원래 하던 일(자동 최적화)에 다가갔고, Vue는 Vapor Mode로 가상 DOM을 걷어내 React가 못 하던 일(런타임 제거)로 가고 있다.** 다만 방향이 대칭이어도 성숙도는 대칭이 아니다 — React Compiler는 정식이고, Vapor Mode는 RC다(1절).

Vapor Mode의 성격은 릴리스 노트에 이렇게 규정돼 있다: "100% opt-in and supports a subset of existing Vue APIs… Features that depend on VNodes or the component public instance proxy are not available in Vapor components."[^vapor] 전면 교체가 아니라 **부분 도입용**이라는 뜻이다.

---

## 5. 가장 현실적인 차이 — 공식 권고가 정반대다

이게 실무 선택에 가장 크게 작용하는데도 비교 글에서 잘 안 다뤄진다.

**React 공식 문서는 프레임워크로 시작하라고 권한다.**

> "If you want to build a new app or website with React, we recommend starting with a framework."[^createreact]

이름까지 지목한다 — Next.js(App Router, Vercel 관리), React Router v7(Shopify 관리), 네이티브는 Expo. Create React App은 폐기됐다.[^createreact]

**Vue 공식 문서는 반대로 권한다.**

> "The general recommendation is to use a framework only if you need SSR."
> "If you don't need SSR, you can simply use Vite."[^quickstart]

기본 시작점은 `npm create vue@latest`(Vite + SFC)이고, Nuxt·Vike·Astro·Quasar는 SSR이 필요할 때의 선택지로 소개된다.[^quickstart]

**이 차이가 실무에서 뜻하는 것:** React를 고르면 사실상 메타프레임워크(대개 Next.js)를 같이 고르는 것이고, 그 프레임워크의 라우팅·빌드·배포 모델까지 따라온다. Vue를 고르면 기본값은 그냥 빌드 도구(Vite) 위의 SPA이고, 필요해질 때 Nuxt를 얹는다. **React 쪽이 초기 결정이 무겁고, Vue 쪽이 초기 결정이 가볍다.**

덧붙여 React 19의 서버 기능에는 안정성 단서가 붙어 있다. Server Components 자체는 stable 이지만, 그걸 구현하는 번들러/프레임워크용 하위 API는 semver를 따르지 않는다:

> "While React Server Components in React 19 are stable and will not break between minor versions, the underlying APIs used to implement a React Server Components bundler or framework do not follow semver and may break between minors in React 19.x."[^rsc]

앱 개발자에겐 영향이 없고, **프레임워크를 직접 만들거나 깊게 커스터마이즈하는 쪽엔 영향이 있다.**

한편 React 19에서 정식화된 Actions·`useActionState`·`useOptimistic` 은 폼과 비동기 상태 처리를 표준화했다 — "React 19 introduces `useOptimistic` to manage optimistic updates, and a new hook `React.useActionState` to handle common cases for Actions."[^react19] 이건 React 쪽의 분명한 강점이다.

---

## 6. 생태계 규모 — 숫자와 그 숫자의 한계

npm 주간 다운로드(2026-09-05 ~ 2026-09-11 구간, npm registry API 기준)는 다음과 같다.[^npm]

| 패키지 | 주간 다운로드 |
|---|---|
| `react` | 128,119,130 |
| `react-dom` | 120,650,097 |
| `vue` | 11,281,013 |
| `next` | 43,416,095 |
| `nuxt` | 1,436,097 |

**이 숫자를 점유율로 읽으면 안 된다.** 다운로드는 사용자 수가 아니라 패키지 내려받기 횟수이고, CI 실행·도커 재빌드·미러가 전부 포함된다. 게다가 동등 비교도 아니다 — React 웹 앱은 `react` 와 `react-dom` 을 둘 다 받지만 Vue는 `vue` 하나다. 그리고 Vue는 빌드 단계 없이 스크립트 태그로 쓰는 사용법을 공식적으로 지원하는데, 그 사용자는 npm 통계에 **구조적으로 안 잡힌다**.[^waysofusing] 규모의 **자릿수 차이**를 보여주는 신호 정도로만 쓰는 게 정직하다.

거버넌스도 대비된다. React는 중립 재단(Linux Foundation 산하) + 플래티넘 기업 회원 구조다(1절). Vue는 여전히 개인 주도 + 스폰서 재원이다 — "Vue is an independent, community-driven project. … Evan serves as the project lead." / "Vue's development is primarily funded through sponsorships and we have been financially sustainable since 2016."[^vuefaq] 라이선스는 **둘 다 MIT** 다.[^reactlicense][^vuelicense]

어느 쪽이 낫다고 말하긴 어렵다. 재단 구조는 특정 기업 이해에서 자유롭지만 의사결정이 느려질 수 있고, 개인 주도는 방향이 선명하지만 버스 팩터가 작다.

---

## 7. 성능 — 중립적인 정면 비교는 없다

여기는 조심해서 써야 한다.

Vue 공식 FAQ에는 React를 직접 언급한 성능 주장이 있다:

> "In stress-testing scenarios, Vue outperforms React and Angular by a decent margin in the js-framework-benchmark."[^vuefaq]

**이건 벤더 주장이다.** 그리고 같은 페이지가 스스로 단서를 단다 — "synthetic benchmarks like the above focus on raw rendering performance with dedicated optimizations and may not be fully representative of real-world performance results."[^vuefaq]

근거로 쓰인 js-framework-benchmark 자체는 정당한 물건이다. `krausest/js-framework-benchmark` 는 Apache-2.0 오픈소스이고, 현재 186개 구현이 들어 있으며, 로컬에서 재현할 수 있게 빌드·실행 절차가 문서화돼 있다.[^bench] 다만 저자가 명시한 교란 요인이 있다. **keyed / non-keyed 구분**이다 — README는 "this is what e.g. vue.js uses by default for lists… For React and Angular, using the item index as the key uses 'non-keyed' mode" 라고 적는다.[^bench] 즉 같은 표 안에서도 무엇을 비교 대상으로 놓느냐에 따라 결과가 달라진다. 저자는 스냅샷 결과가 "may not have the same quality (i.e. results might be for mixed browser versions…)" 라고도 경고한다.[^bench]

**그래서 이 글은 수치를 인용하지 않는다.** 공개 결과가 생성된 인터랙티브 표 형태라 텍스트로 검증되지 않았고, 검증 못 한 수치를 옮기는 건 이 블로그의 원칙에 어긋난다. 정직한 결론은 이렇다:

- 양쪽 다 현대적 웹 앱에서 렌더링 성능이 병목이 되는 경우는 드물다.
- 공개된 비교의 출처가 **한쪽 당사자**이고, 벤치마크 설정에 결과를 뒤집을 수 있는 선택지(keyed/non-keyed)가 있다.
- **중립 제3자가 동일 조건으로 수행한 최신 정면 비교는 확인되지 않았다.** 성능을 선택 기준으로 삼으려면 남의 표가 아니라 본인 앱의 프로파일을 재야 한다.

참고로 Vue 3.6 RC의 반응성 재작성(alien-signals 기반)도 "significantly improves the reactivity system's performance and memory usage" 라고 되어 있지만, 릴리스 노트에 근거 벤치마크가 첨부돼 있지 않다 — 역시 벤더 주장으로 읽어야 한다.[^vapor]

또 하나 덧붙이면, Vue 공식 사이트에 있던 "Comparison with Other Frameworks" 페이지는 Vue 3 문서에서 **삭제됐다**(현재 404, Vue 2 아카이브에만 남아 있다). 공식 FAQ 소스에는 `<!-- ## TODO How does Vue compare to React? -->` 라는 주석만 남아 있다. **양쪽 공식 문서 모두 정면 비교를 회피하고 있다**는 사실 자체가, 이런 비교가 얼마나 조건 의존적인지를 보여준다.

---

## 8. 장단점 정리

**React의 장점**
- 마크업이 JavaScript 그 자체라 추상화·조합에 제약이 적다(3절).
- 생태계 규모가 자릿수로 앞선다 — 라이브러리·채용·레퍼런스(6절).
- React Native로 네이티브까지 같은 모델이 이어진다.[^createreact]
- Server Components·Actions 등 서버 통합이 프레임워크 층에서 표준화돼 있다(5절).
- 재단 거버넌스로 단일 기업 의존이 줄었다(1절).

**React의 단점**
- 기본값이 과잉 재실행이라, Compiler를 안 쓰면 수동 메모이제이션 부담이 남는다(4절).
- 시작부터 메타프레임워크 선택이 강하게 권장돼 초기 결정이 무겁다(5절).
- "자유롭다"는 곧 "상태관리·라우팅·폼을 매번 고른다"는 뜻이라 팀 편차가 커진다.

**Vue의 장점**
- 세밀한 의존성 추적이 기본값이라 최적화를 덜 의식해도 된다(2·4절).
- SFC + 템플릿이라 HTML 경험을 그대로 쓰고 정적 분석·컴파일 최적화가 잘 먹는다(3절).
- 빌드 도구(Vite)만으로 시작할 수 있어 초기 진입이 가볍다(5절).
- 점진적 도입에 유리하다 — 기존 페이지 일부만 얹는 게 자연스럽다.

**Vue의 단점**
- 생태계·채용 시장 규모가 React보다 확연히 작다(6절).
- 반응형 래핑(`ref`/`.value`, Proxy)이라는 별도 개념을 배워야 하고, 반응성을 잃는 실수가 생긴다.
- 개인 주도 + 스폰서 재원이라 거버넌스 지속성 리스크가 상대적으로 크다(6절).
- Vapor Mode 같은 큰 개선이 아직 정식 버전이 아니다(1절).

---

## 9. 그래서 어떻게 고르나

기술적 우열보다 **맥락**이 결정한다.

- **채용·외주·레퍼런스가 중요하다** → React. 규모 차이가 자릿수다.
- **SSR·SEO·서버 통합이 요구사항의 중심이다** → React + Next.js. 공식 권고가 그 길이다.
- **기존 서버 렌더링 앱(JSP/Thymeleaf 등)에 화면을 점진적으로 얹는다** → Vue. 시작 비용이 가장 낮다.
- **팀 규모가 작고 프론트 전담이 없다** → Vue. 기본값이 안전한 쪽이 사고가 적다.
- **모바일 네이티브까지 한 모델로 간다** → React(+React Native).
- **성능 때문에 고민 중이다** → 둘 중 어느 쪽으로 바꿔도 답이 아닐 가능성이 높다. 먼저 프로파일을 재라(7절).

마지막으로, 이 글에서 가장 오래 유효할 문장은 이것이라고 본다. **React는 "다시 실행하고 비교한다", Vue는 "읽은 걸 기억했다가 깨운다".** 버전이 올라가고 컴파일러가 붙고 Vapor가 정식이 되어도, 이 뿌리는 당분간 바뀌지 않는다. 나머지 차이는 여기서 다시 유도해 내면 된다.

---

## References

[^react193]: React Blog, "React 19.3" (2026-09-09). <https://react.dev/blog/2026/09/09/react-19-3> · 버전·릴리스 일자는 npm registry(`registry.npmjs.org/react`)와 GitHub Releases API로 교차 확인.
[^vuenpm]: Vue npm registry (`registry.npmjs.org/vue`), `latest = 3.5.42`, 2026-08-27 발행 · GitHub `vuejs/core` latest non-prerelease `v3.5.42`.
[^foundation]: React Blog, "The React Foundation" (2026-02-24). <https://react.dev/blog/2026/02/24/the-react-foundation>
[^lf]: Linux Foundation, "Linux Foundation Announces the Formation of the React Foundation" (2026-02-24). <https://www.linuxfoundation.org/press/linux-foundation-announces-the-formation-of-the-react-foundation>
[^reactlicense]: React `LICENSE` (MIT). <https://github.com/react/react/blob/main/LICENSE>
[^compiler]: React Blog, "React Compiler 1.0" (2025-10-07). <https://react.dev/blog/2025/10/07/react-compiler-1>
[^compilerdocs]: React Docs, "React Compiler". <https://react.dev/learn/react-compiler>
[^vapor]: Vue GitHub Releases, `v3.6.0-rc.1` (2026-07-18, pre-release). <https://github.com/vuejs/core/releases/tag/v3.6.0-rc.1>
[^vuereleases]: Vue Docs, "Releases". <https://vuejs.org/about/releases.html>
[^rendercommit]: React Docs, "Render and Commit". <https://react.dev/learn/render-and-commit>
[^reactivity]: Vue Docs, "Reactivity in Depth". <https://vuejs.org/guide/extras/reactivity-in-depth.html>
[^jsx]: React Docs, "Writing Markup with JSX". <https://react.dev/learn/writing-markup-with-jsx>
[^rendering]: Vue Docs, "Rendering Mechanism". <https://vuejs.org/guide/extras/rendering-mechanism.html>
[^sfc]: Vue Docs, "Single-File Components". <https://vuejs.org/guide/scaling-up/sfc.html>
[^v32]: Vue Blog, "Vue 3.2 released" (2021-08-05). <https://blog.vuejs.org/posts/vue-3-2>
[^scriptsetup]: Vue API, "`<script setup>`". <https://vuejs.org/api/sfc-script-setup>
[^createreact]: React Docs, "Creating a React App". <https://react.dev/learn/creating-a-react-app>
[^quickstart]: Vue Docs, "Quick Start". <https://vuejs.org/guide/quick-start.html>
[^rsc]: React Reference, "Server Components". <https://react.dev/reference/rsc/server-components>
[^react19]: React Blog, "React 19" (2024-12-05). <https://react.dev/blog/2024/12/05/react-19>
[^npm]: npm registry downloads API, `https://api.npmjs.org/downloads/point/last-week/<pkg>` · 반환 구간 2026-09-05 ~ 2026-09-11 (조회 2026-09-13).
[^vuefaq]: Vue Docs, "FAQ". <https://vuejs.org/about/faq.html>
[^waysofusing]: Vue Docs, "Ways of Using Vue". <https://vuejs.org/guide/extras/ways-of-using-vue>
[^vuelicense]: Vue `LICENSE` (MIT). <https://github.com/vuejs/core/blob/main/LICENSE>
[^bench]: Stefan Krause, `js-framework-benchmark` (Apache-2.0, 제3자). <https://github.com/krausest/js-framework-benchmark> · 결과 표: <https://krausest.github.io/js-framework-benchmark/current.html> (본문에 수치를 인용하지 않은 이유는 7절 참조)

*출처 등급 표기: React·Vue 공식 문서와 릴리스 노트는 1차 자료로, Vue FAQ의 성능 서술과 3.6 RC의 성능 서술은 **벤더 주장**으로, js-framework-benchmark·npm 수치는 **제3자 데이터(방법론 한계 명시)** 로 구분해 인용했다. 중립 제3자의 최신 정면 성능 비교는 확인되지 않아 우열을 단정하지 않았다.*
