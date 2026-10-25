---
layout: post
title: "Vue 2 핵심 문법과 자주 쓰는 문법 — 옵션 객체 하나로 읽기"
date: 2026-10-26 02:10:19 +0900
categories: [Frontend, Vue]
tags: [Vue2, 문법, Options API, 디렉티브, 컴포넌트, 레거시]
---
{% raw %}
Vue 2 컴포넌트는 결국 **옵션 객체 하나** 다. `data` · `computed` · `watch` · `methods` · `props` 같은 칸에 코드를 나눠 담으면, Vue 가 그것을 반응형 인스턴스로 엮어 준다 ([The Vue Instance](https://v2.vuejs.org/v2/guide/instance.html)). 이 글은 그 칸들과 템플릿 디렉티브를 **실무에서 쓰는 빈도 순** 으로 정리한다. 기준은 전부 Vue 2 공식 가이드(v2.vuejs.org)다.

> Vue 2 는 2023-12-31 에 EOL 을 맞았다 ([Vue 2 LTS](https://v2.vuejs.org/lts/)). 그래도 운영 중인 레거시 코드는 여전히 많다. 이 글은 그 코드를 읽고 고치는 사람을 위한 문법 정리다. Vue 3 와 무엇이 다른지는 [Vue 2 vs Vue 3 — 문법보다 엔진이 바뀌었다](/2026/10/26/vue2-vs-vue3-what-actually-changed/) 에, jQuery·JSP 에서 넘어오는 관점은 [Vue 기본 문법 비교: jQuery와 JSP](/2026/09/19/vue-jquery-jsp-syntax-comparison/) 에 따로 정리했다.

## 0. 전체 그림 — 한 파일 짜리 컴포넌트(SFC)

```vue
<template>
  <div class="todo">
    <input v-model.trim="draft" @keyup.enter="add" placeholder="할 일">
    <p v-if="!items.length">비어 있음</p>
    <ul v-else>
      <li v-for="item in visible" :key="item.id" :class="{ done: item.done }">
        <input type="checkbox" v-model="item.done">
        {{ item.text }}
      </li>
    </ul>
    <span>{{ remaining }}개 남음</span>
  </div>
</template>

<script>
export default {
  name: 'TodoList',
  props: { initial: { type: Array, default: () => [] } },
  data() {
    return { draft: '', items: this.initial.slice(), hideDone: false }
  },
  computed: {
    visible() { return this.hideDone ? this.items.filter(i => !i.done) : this.items },
    remaining() { return this.items.filter(i => !i.done).length }
  },
  watch: {
    items: { handler(v) { localStorage.todos = JSON.stringify(v) }, deep: true }
  },
  methods: {
    add() {
      if (!this.draft) return
      this.items.push({ id: Date.now(), text: this.draft, done: false })
      this.draft = ''
    }
  },
  mounted() { /* DOM 이 붙은 뒤 */ }
}
</script>
```

이 예제 하나에 아래에서 설명할 문법의 대부분이 들어 있다.

## 1. 템플릿 — 값 출력과 바인딩

| 문법 | 뜻 | 축약 |
| --- | --- | --- |
| `{{ expr }}` | 텍스트 보간 (HTML 이스케이프됨) | — |
| `v-bind:href="url"` | 속성에 표현식 바인딩 | `:href="url"` |
| `v-on:click="fn"` | 이벤트 리스너 | `@click="fn"` |
| `v-html="raw"` | HTML 그대로 삽입 | — |

보간에는 **표현식 하나** 만 들어간다. `if` 나 `var` 같은 문장은 들어가지 않는다 ([Template Syntax](https://v2.vuejs.org/v2/guide/syntax.html)). `v-html` 은 XSS 위험이 있어 공식 문서가 *신뢰할 수 있는 콘텐츠에만* 쓰라고 경고한다 — 사용자 입력에는 절대 쓰지 않는다.

**class · style 바인딩** 은 객체나 배열을 받는다. 정적 `class` 와 함께 써도 합쳐진다 ([Class and Style Bindings](https://v2.vuejs.org/v2/guide/class-and-style.html)).

```html
<div class="card" :class="{ active: isActive, 'is-error': hasError }"></div>
<div :class="[base, isActive ? 'on' : '']"></div>
<div :style="{ color: textColor, fontSize: size + 'px' }"></div>
```

## 2. 조건 렌더링 — `v-if` 와 `v-show`

```html
<p v-if="type === 'A'">A</p>
<p v-else-if="type === 'B'">B</p>
<p v-else>그 밖</p>

<p v-show="open">토글 패널</p>
```

둘 다 "보이거나 안 보이게" 하지만 동작이 다르다 ([Conditional Rendering](https://v2.vuejs.org/v2/guide/conditional.html)).

- `v-if` 는 **진짜로 만들고 부순다.** 조건이 거짓이면 DOM 에 아예 없고, 안쪽 자식 컴포넌트도 파괴된다.
- `v-show` 는 **항상 렌더링** 해 두고 CSS `display` 만 바꾼다. `<template>` 에는 쓸 수 없고 `v-else` 와도 함께 쓸 수 없다.

공식 가이드의 기준: 자주 토글하면 `v-show`, 실행 중에 조건이 잘 바뀌지 않으면 `v-if`. 여러 요소를 한꺼번에 묶을 때는 `<template v-if>` 를 쓴다 — 감싸는 태그가 최종 DOM 에 남지 않는다.

**함정:** Vue 는 같은 자리의 요소를 재사용한다. 그래서 로그인 방식을 바꾸는 폼에서 `v-if` / `v-else` 로 `<input>` 을 갈아끼워도 **입력값이 남는다**. 서로 다른 요소로 취급하게 하려면 각각 다른 `key` 를 준다.

## 3. 리스트 렌더링 — `v-for` 와 `key`

```html
<li v-for="(item, index) in items" :key="item.id">{{ index }}. {{ item.name }}</li>
<li v-for="(value, name) in obj" :key="name">{{ name }}: {{ value }}</li>
<span v-for="n in 5" :key="n">{{ n }}</span>
```

`key` 는 선택이 아니라고 생각하는 게 안전하다. Vue 2 의 기본 동작은 **"제자리 패치"** 다. 순서가 바뀌어도 DOM 을 옮기지 않고 같은 위치의 요소 내용만 덮어쓴다. 그래서 입력값이나 자식 컴포넌트 상태가 **엉뚱한 줄에 남는다** ([List Rendering](https://v2.vuejs.org/v2/guide/list.html)). `key` 에는 **고유한 원시값** (id 등)을 쓴다. 객체·배열은 키로 쓰지 말라고 공식 문서가 명시한다. 배열 인덱스는 순서가 바뀌는 목록에서 키 구실을 못 한다.

**함정 — `v-if` 와 `v-for` 를 한 요소에.** Vue 2 에서는 `v-for` 가 먼저 평가된다. 그래서 모든 항목을 돌면서 매번 `v-if` 를 검사한다. 공식 스타일 가이드는 이 조합을 **필수(A등급) 규칙으로 금지** 하고, 대신 걸러낸 computed 를 돌리라고 한다 ([Style Guide](https://v2.vuejs.org/v2/style-guide/#Avoid-v-if-with-v-for-essential)). Vue 3 는 이 우선순위가 뒤집히므로 더더욱 피해야 한다.

## 4. 이벤트 — `v-on` 과 수식어

```html
<button @click="count++">+1</button>
<button @click="say('hi', $event)">인자와 이벤트 같이</button>
<form @submit.prevent="onSubmit">...</form>
<a @click.stop.prevent="go">전파 중단 + 기본동작 막기</a>
<input @keyup.enter="search">
<div @click.self="close">배경 클릭만</div>
<button @click.once="init">한 번만</button>
```

이벤트 수식어로 `.stop` `.prevent` `.capture` `.self` `.once` `.passive` 가 있다. 공식 문서는 수식어의 목적을 *메서드가 DOM 세부사항이 아니라 데이터 로직에만 집중하게 하는 것* 이라고 설명한다 ([Event Handling](https://v2.vuejs.org/v2/guide/events.html)). 수식어를 **이어 쓰는 순서도 의미가 있다.** `@click.prevent.self` 는 모든 클릭의 기본동작을 막지만, `@click.self.prevent` 는 그 요소 자신을 클릭했을 때만 막는다. 원래 DOM 이벤트 객체가 필요하면 `$event` 로 넘긴다.

## 5. 폼 — `v-model`

```html
<input v-model="name">
<input v-model.trim="email">       <!-- 앞뒤 공백 제거 -->
<input v-model.number="age">       <!-- 숫자로 변환 -->
<input v-model.lazy="memo">        <!-- input 대신 change 시점에 반영 -->
<input type="checkbox" v-model="agree">
<input type="checkbox" value="a" v-model="picked">   <!-- picked: [] 배열 -->
<select v-model="city"><option value="seoul">서울</option></select>
```

`v-model` 은 **요소에 따라 다른 속성과 이벤트로 풀리는 문법 설탕** 이다. 텍스트 입력은 `value` + `input`, 체크박스·라디오는 `checked` + `change`, select 는 `value` + `change` 다. 그리고 HTML 의 초기 `value` · `checked` · `selected` 속성은 **무시하고 `data` 를 진실로 삼는다** ([Form Input Bindings](https://v2.vuejs.org/v2/guide/forms.html)). 초기값은 반드시 `data` 에 둔다.

## 6. `data` — 반드시 함수

```js
data() {
  return { items: [], loading: false, error: null }
}
```

컴포넌트의 `data` 는 **객체를 돌려주는 함수** 여야 한다. 객체를 그냥 쓰면 그 컴포넌트의 모든 인스턴스가 같은 객체를 공유한다 ([Components Basics](https://v2.vuejs.org/v2/guide/components.html#data-Must-Be-a-Function)). 그리고 **나중에 쓸 속성도 처음부터 선언해 둔다.** 인스턴스가 만들어질 때 `data` 에 없던 속성은 반응형이 아니기 때문이다 ([The Vue Instance](https://v2.vuejs.org/v2/guide/instance.html)). 빈 값이라도 `null` · `''` · `[]` 로 자리를 잡아 둔다.

## 7. `computed` vs `methods` vs `watch`

| | 언제 다시 실행되나 | 용도 |
| --- | --- | --- |
| `computed` | **의존하는 반응형 값이 바뀔 때만** (캐시) | 다른 상태에서 파생된 값 |
| `methods` | 다시 렌더링할 때마다, 호출할 때마다 | 이벤트 처리, 인자를 받는 계산 |
| `watch` | 지정한 값이 바뀔 때 | 부수효과 (API 호출·저장·비동기) |

computed 는 반응형 의존성을 기준으로 **캐시** 된다. 그래서 `Date.now()` 처럼 반응형이 아닌 값만 쓰는 computed 는 **영영 갱신되지 않는다.** 공식 문서가 직접 드는 예다 ([Computed and Watchers](https://v2.vuejs.org/v2/guide/computed.html)). 같은 문서는 `watch` 를 남용하지 말라고도 한다. 파생 값은 computed 로, 비동기이거나 비용이 큰 작업만 watch 로 한다.

```js
watch: {
  keyword(newVal, oldVal) { this.fetch(newVal) },          // 기본
  filters: { handler: 'reload', deep: true },              // 객체 내부까지
  userId: { handler: 'load', immediate: true }             // 생성 직후 1회 실행
}
```

## 8. 컴포넌트 통신 — props 는 내려가고 이벤트는 올라간다

```js
// 자식
export default {
  props: {
    title: { type: String, required: true },
    count: { type: Number, default: 0 },
    options: { type: Array, default: () => [] }   // 객체·배열 기본값은 팩토리 함수
  },
  methods: {
    inc() { this.$emit('update', this.count + 1) }
  }
}
```

```html
<!-- 부모 -->
<Counter :title="label" :count="n" @update="n = $event" />
```

props 는 **단방향 데이터 흐름** 이다. 부모가 바뀌면 자식에게 내려가지만, 그 반대는 아니다. 자식이 prop 을 직접 바꾸면 Vue 가 콘솔에 경고를 낸다. 로컬에서 바꿔야 하면 `data` 나 `computed` 로 복사해서 쓴다 ([Props](https://v2.vuejs.org/v2/guide/components-props.html#One-Way-Data-Flow)). 객체·배열 prop 의 `default` 는 팩토리 함수로 준다. 위로 알릴 때는 `$emit` 을 쓴다.

**Vue 2 에서 자주 보이는 두 축약:**

- 컴포넌트 `v-model` = `value` prop + `input` 이벤트. 이름을 바꾸려면 `model: { prop, event }` 옵션을 쓴다.
- `.sync` — `:title.sync="t"` 는 `:title="t" @update:title="t = $event"` 의 줄임이다.

둘 다 Vue 3 에서 바뀐다. Vue 3 의 `v-model` 은 `modelValue` 를 쓰고, `.sync` 는 제거된다.

## 9. 슬롯 — `v-slot` (2.6+)

```html
<!-- 자식: BaseLayout -->
<header><slot name="header"></slot></header>
<main><slot>기본 내용</slot></main>
<ul><li v-for="it in items" :key="it.id"><slot name="row" :item="it"></slot></li></ul>
```

```html
<!-- 부모 -->
<BaseLayout>
  <template #header><h1>제목</h1></template>
  <p>본문</p>
  <template #row="{ item }">{{ item.name }}</template>
</BaseLayout>
```

2.6.0 부터 named slot 과 scoped slot 이 **`v-slot` 하나로 통일** 됐다. 축약은 `#` 이다. 예전의 `slot` · `slot-scope` 속성은 deprecated 다 — 다만 제거되지는 않아 오래된 코드에서 여전히 보인다 ([Slots](https://v2.vuejs.org/v2/guide/components-slots.html)). 규칙 하나만 기억하면 된다: *부모 템플릿의 모든 것은 부모 스코프에서, 자식 템플릿의 모든 것은 자식 스코프에서 컴파일된다.* 자식의 데이터를 부모 슬롯에서 쓰고 싶으면 scoped slot 으로 명시적으로 넘겨야 한다.

## 10. 생명주기 훅

```
beforeCreate → created → beforeMount → mounted
             → beforeUpdate → updated
             → beforeDestroy → destroyed
```

실무에서 쓰는 건 대부분 셋이다 ([Lifecycle Diagram](https://v2.vuejs.org/v2/guide/instance.html#Lifecycle-Diagram)).

- `created` — 반응형 데이터는 준비됐지만 DOM 은 아직 없다. **API 호출** 을 시작하기 좋은 곳.
- `mounted` — DOM 이 붙었다. 차트 라이브러리처럼 DOM 이 필요한 초기화를 한다.
- `beforeDestroy` — 타이머, `window` 리스너, 외부 라이브러리 인스턴스를 **정리** 한다. 빠뜨리면 메모리 누수가 난다.

훅 안에서 **화살표 함수를 쓰지 않는다.** `this` 가 인스턴스를 가리키지 않게 되기 때문이다 — 공식 문서의 경고다.

## 11. 자주 부딪히는 Vue 2 전용 함정 세 가지

**① 새 속성과 배열 인덱스 대입은 감지되지 않는다.** Vue 2 는 `Object.defineProperty` 로 반응성을 만든다. 그래서 객체에 속성을 *추가* 하거나 `arr[i] = x` 로 대입하면 화면이 갱신되지 않는다 ([Reactivity in Depth](https://v2.vuejs.org/v2/guide/reactivity.html)).

```js
this.$set(this.user, 'nickname', 'lemuel')
this.items.splice(i, 1, newItem)
this.form = Object.assign({}, this.form, { a: 1, b: 2 })   // 여러 개는 새 객체로
```

**② DOM 갱신은 비동기다.** 데이터를 바꾼 직후 DOM 을 읽으면 아직 옛 값이 있다. Vue 는 변경을 모았다가 다음 틱에 한 번에 반영한다. 갱신된 DOM 을 봐야 하면 `$nextTick` 을 쓴다 ([Async Update Queue](https://v2.vuejs.org/v2/guide/reactivity.html#Async-Update-Queue)).

```js
this.show = true
this.$nextTick(() => this.$refs.input.focus())
```

**③ `ref` 는 렌더링이 끝난 뒤에야 채워진다.** `this.$refs.x` 는 `mounted` 이후에만 유효하다. 반응형도 아니므로 템플릿이나 computed 에서 쓰지 않는다.

## 12. 레거시에서 자주 보이지만 Vue 3 에서 사라지는 것

| 문법 | 예 | Vue 3 에서 |
| --- | --- | --- |
| 필터 | 보간 안에서 파이프로 `currency` 같은 필터 적용 | 제거 → 메서드나 computed |
| 이벤트 버스 | `new Vue()` 를 만들어 `$on` / `$emit` | `$on` 제거 → 외부 라이브러리 |
| 믹스인 | `mixins: [formMixin]` | 남아 있으나 Composition API(composable)를 권장 |
| `.native` | `@click.native` | 제거 |
| `$listeners` | `v-on="$listeners"` | `$attrs` 에 통합 |

이 표는 Vue 3 공식 [Breaking Changes](https://v3-migration.vuejs.org/breaking-changes/) 목록에서 Vue 2 코드에 흔히 보이는 항목만 뽑은 것이다. 레거시 코드를 고칠 때 이 패턴을 새로 늘리지 않는 것이 나중의 마이그레이션 비용을 줄인다.

## 13. 2.7 이라면 — `<script setup>` 도 된다

Vue 2.7 은 Composition API 와 `<script setup>` 을 코어에 백포트했다 ([Vue 2 LTS](https://v2.vuejs.org/lts/)). 그래서 2.7 프로젝트에서는 새 컴포넌트를 아래처럼 써도 된다 — 그리고 이 코드는 Vue 3 에서도 그대로 동작한다.

```vue
<script setup>
import { ref, computed } from 'vue'
const count = ref(0)
const double = computed(() => count.value * 2)
</script>

<template>
  <button @click="count++">{{ count }} / {{ double }}</button>
</template>
```

## 한 장 요약

| 하고 싶은 것 | Vue 2 문법 |
| --- | --- |
| 값 출력 | `{{ x }}` |
| 속성 바인딩 | `:href="url"` · `:class="{ on: a }"` |
| 이벤트 | `@click="fn"` · `@submit.prevent` · `@keyup.enter` |
| 조건 | `v-if` / `v-else-if` / `v-else` · 잦은 토글은 `v-show` |
| 반복 | `v-for="it in list" :key="it.id"` |
| 입력 | `v-model` · `.trim` `.number` `.lazy` |
| 파생 값 | `computed` |
| 부수효과 | `watch` (`deep` · `immediate`) |
| 부모 → 자식 | `props` (객체 기본값은 팩토리) |
| 자식 → 부모 | `$emit('evt', payload)` |
| 끼워 넣기 | `<slot>` · `<template #name="{ item }">` |
| DOM 접근 | `ref="x"` → `this.$refs.x` (mounted 이후) |
| 반영 후 작업 | `this.$nextTick(cb)` |
| 새 속성 추가 | `this.$set(obj, key, val)` |

## 근거의 한계

- 이 글은 Vue 2 **공식 가이드** 만 근거로 삼았다. "자주 쓰는" 의 순서는 필자의 실무 경험에 따른 것이다. 사용 빈도를 집계한 중립적인 통계는 찾지 못했다.
- Vuex · Vue Router · 커스텀 디렉티브 · 렌더 함수 · 트랜지션은 다루지 않았다.

## References

- Vue.js, *The Vue Instance* (v2). <https://v2.vuejs.org/v2/guide/instance.html>
- Vue.js, *Template Syntax* (v2). <https://v2.vuejs.org/v2/guide/syntax.html>
- Vue.js, *Computed Properties and Watchers* (v2). <https://v2.vuejs.org/v2/guide/computed.html>
- Vue.js, *Class and Style Bindings* (v2). <https://v2.vuejs.org/v2/guide/class-and-style.html>
- Vue.js, *Conditional Rendering* (v2). <https://v2.vuejs.org/v2/guide/conditional.html>
- Vue.js, *List Rendering* (v2). <https://v2.vuejs.org/v2/guide/list.html>
- Vue.js, *Event Handling* (v2). <https://v2.vuejs.org/v2/guide/events.html>
- Vue.js, *Form Input Bindings* (v2). <https://v2.vuejs.org/v2/guide/forms.html>
- Vue.js, *Components Basics* (v2). <https://v2.vuejs.org/v2/guide/components.html>
- Vue.js, *Props* (v2). <https://v2.vuejs.org/v2/guide/components-props.html>
- Vue.js, *Slots* (v2). <https://v2.vuejs.org/v2/guide/components-slots.html>
- Vue.js, *Reactivity in Depth* (v2). <https://v2.vuejs.org/v2/guide/reactivity.html>
- Vue.js, *Style Guide* (v2). <https://v2.vuejs.org/v2/style-guide/>
- Vue.js, *Vue 2 LTS, EOL & Extended Support*. <https://v2.vuejs.org/lts/>
- Vue.js, *Breaking Changes — Vue 3 Migration Guide*. <https://v3-migration.vuejs.org/breaking-changes/>
{% endraw %}
