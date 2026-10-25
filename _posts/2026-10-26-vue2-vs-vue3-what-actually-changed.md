---
layout: post
title: "Vue 2 vs Vue 3 — 문법보다 엔진이 바뀌었다"
date: 2026-10-26 01:35:57 +0900
categories: [Frontend, Vue]
tags: [Vue2, Vue3, Composition API, 반응성, Proxy, 마이그레이션]
---

Vue 2 와 Vue 3 의 차이를 물으면 흔히 "Composition API 가 생겼다" 로 끝난다. 그런데 Composition API 는 **Vue 2.7 에도 백포트돼 있다** ([Vue FAQ](https://vuejs.org/about/faq.html)). 그러니 그건 두 버전을 가르는 선이 아니다. 진짜 차이는 눈에 덜 띄는 곳에 있다 — **반응성을 감지하는 방식, 템플릿을 렌더 함수로 바꾸는 컴파일러, 그리고 전역 상태를 들고 있던 `Vue` 생성자**. 이 글은 그 셋을 축으로 차이를 정리한다.

> 앞서 쓴 [스프링 6 + Vue 2 3부작](/2026/09/15/spring6-vue2-exit-roadmap/) 이 "언제·어떤 순서로 옮길까" 를 다뤘다면, 이 글은 "옮기면 코드에서 무엇이 달라지나" 를 다룬다.

## 한눈에 보는 연표

| 시점 | 사건 | 출처 |
| --- | --- | --- |
| 2020-09-18 | Vue 3.0 "One Piece" 정식 출시 | [Vue 공식 블로그](https://blog.vuejs.org/posts/vue-3-one-piece) |
| 2021-04 | Vue 3 의 IE11 지원 계획 철회 RFC 확정, 대신 Vue 2.7 백포트에 집중 | [vuejs/rfcs #296](https://github.com/vuejs/rfcs/discussions/296) |
| 2022-02-07 | `npm install vue` 기본값이 Vue 3 로 전환 | [Vue 공식 블로그](https://blog.vuejs.org/posts/vue-3-as-the-new-default) |
| 2022-07-01 | Vue 2.7 (마지막 마이너) 출시 | [Vue 2 LTS](https://v2.vuejs.org/lts/) |
| 2023-12-31 | Vue 2 EOL — 보안·브라우저 호환 패치 종료 | [Vue 2 LTS](https://v2.vuejs.org/lts/) |

## 1. 반응성: `Object.defineProperty` → `Proxy`

가장 근본적인 차이다. Vue 공식 문서가 직접 이렇게 쓴다: *"Vue 2 used getter / setters exclusively due to browser support limitations. In Vue 3, Proxies are used for reactive objects and getter / setters are used for refs."* ([Reactivity in Depth](https://vuejs.org/guide/extras/reactivity-in-depth.html))

Vue 2 는 인스턴스를 만들 때 `data` 의 **이미 있는 속성** 을 하나씩 돌며 getter/setter 로 바꿔 끼운다. 그래서 *나중에 생긴 속성은 감지하지 못한다*. Vue 2 문서가 직접 밝히는 한계는 이렇다 ([v2 Reactivity](https://v2.vuejs.org/v2/guide/reactivity.html)):

- 객체에 속성을 **추가·삭제** 하는 건 감지되지 않는다.
- 배열을 `items[i] = x` 처럼 **인덱스로 대입** 하거나 `items.length = n` 으로 길이를 바꾸는 것도 감지되지 않는다.

그래서 Vue 2 코드에는 이런 우회가 흔하다.

```js
// Vue 2
this.$set(this.user, 'nickname', 'lemuel')   // 새 속성 추가
this.items.splice(1, 1, 'x')                 // 인덱스 대입 대신
```

Vue 3 의 `Proxy` 는 속성 단위가 아니라 **객체 전체의 읽기·쓰기를 가로챈다**. 그래서 새 속성 추가도, 인덱스 대입도 그냥 감지된다. 마이그레이션 가이드는 그 결과로 `Vue.set` / `Vue.delete` / `$set` / `$delete` 를 아예 지웠다 — *"They are no longer required with proxy-based change detection."* ([Breaking Changes](https://v3-migration.vuejs.org/breaking-changes/))

```js
// Vue 3
user.nickname = 'lemuel'   // 감지됨
items[1] = 'x'             // 감지됨
```

**대가도 있다.** `Proxy` 는 폴리필로 흉내 낼 수 없는 언어 기능이다. 그래서 Vue 3 는 IE11 을 지원하지 않는다 ([Vue FAQ](https://vuejs.org/about/faq.html): *"Vue 3 leverages modern JavaScript features and does not support IE11."*). 그리고 `reactive()` 가 돌려주는 프록시는 원본과 `===` 비교에서 **다른 객체** 다 ([Reactivity in Depth](https://vuejs.org/guide/extras/reactivity-in-depth.html)). 원본 객체를 `Map` 의 키로 쓰던 코드라면 여기서 미묘하게 깨진다.

## 2. 렌더링: 런타임 diff → "컴파일러가 힌트를 주는" 가상 DOM

두 버전 모두 템플릿을 렌더 함수로 컴파일하고 가상 DOM 을 diff 한다. 차이는 **컴파일러가 런타임에 얼마나 많은 정보를 넘기느냐** 다. Vue 공식 문서는 Vue 3 의 방식을 *Compiler-Informed Virtual DOM* 이라고 부른다 ([Rendering Mechanism](https://vuejs.org/guide/extras/rendering-mechanism.html)).

- **정적 노드 캐싱** — 바인딩이 하나도 없는 노드는 최초 렌더 때 한 번만 만들고 이후 diff 에서 건너뛴다. 정적 노드가 연달아 충분히 많으면 HTML 문자열 하나로 합쳐 `innerHTML` 로 꽂는다.
- **패치 플래그** — 컴파일러가 "이 노드는 `class` 만 바뀐다" 같은 표시를 붙인다. 그러면 런타임은 그 부분만 비교한다.
- **블록 트리** — 동적인 자손 노드만 평평한 배열로 모아 둔다. 그래서 재렌더 때 트리 전체를 걷지 않아도 된다.

같은 문서는 순수 런타임 diff 의 약점을 이렇게 짚는다: 바뀌지 않는 부분까지 매번 vnode 를 새로 만들고 전부 비교해야 한다는 것. Vue 3 의 위 최적화들이 겨냥하는 게 바로 이 비용이다.

**성능 수치에 대해.** Vue 팀은 3.0 출시 공지에서 "번들 최대 41% 감소, 초기 렌더 최대 55% 빠름, 업데이트 최대 133% 빠름, 메모리 최대 54% 감소" 를 내걸었다 ([Vue 3.0 공지](https://blog.vuejs.org/posts/vue-3-one-piece)). 이건 **벤더 자체 측정치** 다. 측정 조건이 공지에 상세히 공개되지 않았고, 두 버전을 같은 조건에서 비교한 중립적인 제3자 벤치마크는 찾지 못했다. 그러니 "최대" 라는 단어를 그대로 읽어야 한다 — 우리 앱이 그만큼 빨라진다는 보장은 아니다.

## 3. 전역 API: `new Vue()` → `createApp()`

Vue 2 에서는 `Vue.use()` · `Vue.component()` · `Vue.mixin()` 이 **하나뿐인 전역 `Vue` 생성자** 를 고친다. 그래서 같은 페이지에 앱을 두 개 띄우거나 테스트끼리 격리하려 하면 플러그인 설정이 서로 새어 나간다. Vue 3 는 이 전역 상태를 **앱 인스턴스** 로 옮겼다 ([Breaking Changes — Global API](https://v3-migration.vuejs.org/breaking-changes/)).

```js
// Vue 2
Vue.use(router)
new Vue({ render: h => h(App) }).$mount('#app')

// Vue 3
createApp(App).use(router).mount('#app')
```

같은 개편으로 내부 API 들이 **트리 셰이킹 가능한 named export** 가 됐다. 쓰지 않는 기능(예: `Transition`)은 번들에서 빠진다.

## 4. 코드 레벨에서 자주 부딪히는 변경

공식 [Breaking Changes](https://v3-migration.vuejs.org/breaking-changes/) 목록 가운데 실무에서 가장 자주 걸리는 것만 추렸다.

| 영역 | Vue 2 | Vue 3 |
| --- | --- | --- |
| 컴포넌트 `v-model` | `value` prop + `input` 이벤트, 이름을 바꾸려면 `model` 옵션 | `modelValue` + `update:modelValue`, `v-model:title` 처럼 **여러 개** 가능. `.sync` 는 제거 ([v-model](https://v3-migration.vuejs.org/breaking-changes/v-model.html)) |
| `v-if` + `v-for` 를 한 엘리먼트에 | `v-for` 가 먼저 | **`v-if` 가 먼저** ([v-if vs v-for](https://v3-migration.vuejs.org/breaking-changes/v-if-v-for.html)) — 같은 템플릿이 다르게 동작 |
| 이벤트 버스 | `$on` / `$off` / `$once` | 제거 — mitt 같은 외부 라이브러리나 provide/inject 로 대체 |
| 필터 | 템플릿 파이프 필터 (예: `currency`) | 제거 — 메서드나 computed 로 |
| 루트 노드 | 템플릿당 하나 | 여러 개 가능(Fragment) |
| 생명주기 이름 | `beforeDestroy` / `destroyed` | `beforeUnmount` / `unmounted` |
| 이벤트 선언 | 선택 | `emits` 옵션으로 선언 |
| 비동기 컴포넌트 | `() => import(...)` | `defineAsyncComponent(...)` |
| `$listeners` | 별도 | `$attrs` 에 통합(`class`·`style` 도 포함) |
| 배열 `watch` | 원소가 바뀌어도 발화 | **배열이 통째로 교체될 때만** 발화 — 원소 변경까지 보려면 `deep` 필요 |

이 중 가장 위험한 건 `v-if`/`v-for` 우선순위와 배열 `watch` 두 가지다. **컴파일 에러가 나지 않는다.** 화면이나 부수효과만 조용히 달라진다. Vue 공식 마이그레이션 빌드(`@vue/compat`)가 이런 지점마다 경고 플래그를 띄우는 이유가 그것이다 (예: `COMPILER_V_IF_V_FOR_PRECEDENCE`).

## 5. 새로 생긴 것

Vue FAQ 가 Vue 3 전용 기능으로 꼽는 건 셋이다: **Teleport**(DOM 트리의 다른 위치로 렌더링 — 모달 등), **Suspense**(비동기 의존성을 기다리는 동안 대체 UI 보여주기), **다중 루트 엘리먼트** ([Vue FAQ](https://vuejs.org/about/faq.html)). 그 밖의 생태계도 함께 바뀌었다. Vue 3 가 기본값이 되면서 공식 권장 도구가 이렇게 정리됐다 ([Vue 3 as the New Default](https://blog.vuejs.org/posts/vue-3-as-the-new-default)):

- Vue CLI(webpack) → **Vite**
- Vuex → **Pinia**
- Vetur → **Volar**
- 명령줄 타입 검사 **vue-tsc**

## 6. Composition API 는 "차이" 가 아니라 "다리" 다

처음 질문으로 돌아가 보자. Composition API(`setup`, `ref`, `computed`, `<script setup>`)는 Vue 3 와 함께 나왔지만 Vue 2.7 에 공식 백포트됐다. Vue 2 LTS 페이지는 *"Due to 2.7, the DX gap between the two major versions are no longer that prominent"* 라고 쓴다 ([Vue 2 LTS](https://v2.vuejs.org/lts/)). 그리고 업그레이드로 얻는 것을 세 가지로 좁힌다: 더 정교한 TypeScript 지원, 더 나은 성능, Vue 3 생태계와 앞으로의 기능.

그래서 실무 순서는 대개 이렇다.

1. Vue 2.7 로 올린다.
2. 새 코드는 Composition API 로 쓴다 — 이 코드는 Vue 3 에서도 그대로 돈다.
3. `$set` · 필터 · 이벤트 버스 · `.sync` 같은 Vue 2 전용 패턴을 걷어낸다.
4. 마지막에 `@vue/compat` 로 Vue 3 로 갈아끼우고 경고를 0 으로 만든다.

옵션 API(`data` / `methods` / `computed`)는 Vue 3 에서도 **폐기되지 않았다**. 공식 문서는 두 스타일을 토글로 나란히 보여준다. "Vue 3 = Composition API 강제" 는 흔한 오해다.

## 정리

| 축 | Vue 2 | Vue 3 |
| --- | --- | --- |
| 반응성 | `Object.defineProperty` — 속성 추가·인덱스 대입 감지 못함 | `Proxy` — 감지됨, 대신 IE11 불가 |
| 렌더링 | 런타임 diff 중심 | 정적 캐싱·패치 플래그·블록 트리 |
| 앱 생성 | 전역 `Vue` 를 직접 수정 | `createApp()` 인스턴스 단위, 트리 셰이킹 |
| 코드 구성 | 옵션 API (2.7 부터 Composition API 도) | 옵션 API + Composition API, `<script setup>` |
| 지원 | 2023-12-31 EOL | 현행 |

문법 표만 보면 바뀐 게 많아 보인다. 하지만 그 대부분은 **`Proxy` 로 바꾼 반응성과 `createApp` 으로 바꾼 전역 상태의 후속 정리** 다. `$set` 이 사라진 것도, `Vue.use` 가 `app.use` 가 된 것도 이 두 결정에서 나왔다. 마이그레이션 비용이 실제로 나오는 곳은 문법이 아니라 **에러 없이 동작만 달라지는 지점** (`v-if`/`v-for` 우선순위, 배열 `watch`, `$attrs` 에 합쳐진 `class`)이다.

## 근거의 한계

- 성능 수치는 전부 Vue 팀의 자체 발표다. 중립적인 제3자의 동일 조건 헤드투헤드 벤치마크는 찾지 못했다.
- 위 표는 공식 Breaking Changes 목록의 *발췌* 다. 커스텀 디렉티브 API, 렌더 함수 `h` 시그니처, 트랜지션 클래스 이름 변경 등은 빠져 있다. 실제 마이그레이션 전에는 원문 목록 전체를 대조해야 한다.

## References

- Vue.js, *Breaking Changes — Vue 3 Migration Guide*. <https://v3-migration.vuejs.org/breaking-changes/>
- Vue.js, *v-model — Vue 3 Migration Guide*. <https://v3-migration.vuejs.org/breaking-changes/v-model.html>
- Vue.js, *v-if vs. v-for Precedence — Vue 3 Migration Guide*. <https://v3-migration.vuejs.org/breaking-changes/v-if-v-for.html>
- Vue.js, *Reactivity in Depth* (Vue 3). <https://vuejs.org/guide/extras/reactivity-in-depth.html>
- Vue.js, *Reactivity in Depth* (Vue 2). <https://v2.vuejs.org/v2/guide/reactivity.html>
- Vue.js, *Rendering Mechanism*. <https://vuejs.org/guide/extras/rendering-mechanism.html>
- Vue.js, *Frequently Asked Questions*. <https://vuejs.org/about/faq.html>
- Vue.js, *Vue 2 LTS, EOL & Extended Support*. <https://v2.vuejs.org/lts/>
- Evan You, *Announcing Vue 3.0 "One Piece"*, The Vue Point, 2020-09-18. <https://blog.vuejs.org/posts/vue-3-one-piece>
- Evan You, *Vue 3 as the New Default*, The Vue Point, 2022-01-20. <https://blog.vuejs.org/posts/vue-3-as-the-new-default>
- Evan You, *Proposal for dropping ie11 support in Vue 3*, vuejs/rfcs Discussion #296, 2021-04-02. <https://github.com/vuejs/rfcs/discussions/296>
