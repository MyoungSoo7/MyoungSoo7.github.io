---
layout: post
title: "Vue 기본 문법 비교: jQuery와 JSP를 기준으로 이해하기"
date: 2026-09-19 03:32:55 +0900
categories: [Frontend, JavaScript, Web]
tags: [Vue, jQuery, JSP, Jakarta Server Pages, Frontend Migration]
---

# Vue 기본 문법 비교: jQuery와 JSP를 기준으로 이해하기

Vue를 처음 배우는 개발자는 기존에 익숙한 jQuery와 JSP 문법을 기준으로 비교하면 빠르게 이해할 수 있다. 다만 세 기술은 같은 계층의 도구가 아니다.

- **JSP**: 서버에서 동적 HTML을 생성하는 서버 페이지 기술
- **jQuery**: 브라우저 DOM 조작·이벤트·Ajax를 단순화하는 JavaScript 라이브러리
- **Vue**: 상태와 화면을 연결하는 반응형 UI 프레임워크

Jakarta Server Pages는 동적 web content를 생성하는 Jakarta EE 기술이며, JSP page·Expression Language·tag library·container 처리를 정의한다.[6] jQuery는 DOM traversal/manipulation, event handling, animation과 Ajax를 단순화하는 JavaScript 라이브러리다.[4]

Vue는 HTML 기반 template과 reactivity를 이용해 component 상태와 렌더링된 DOM을 선언적으로 연결한다.[1][2]

## 1. 같은 화면을 세 방식으로 보기

다음 요구사항을 가정한다.

```text
이름을 입력하면
"안녕하세요, 이름님"을 화면에 표시한다.
```

### JSP

```jsp
<input name="name" value="${name}">
<p>안녕하세요, ${name}님</p>
```

JSP의 `${name}`은 서버가 JSP를 처리할 때 전달한 값을 HTML에 반영하는 방식이다. 사용자가 입력한 뒤 브라우저 화면을 즉시 바꾸려면 form submit이나 별도의 JavaScript가 필요하다.

### jQuery

```html
<input id="name">
<p id="greeting"></p>

<script>
  $("#name").on("input", function () {
    $("#greeting").text("안녕하세요, " + $(this).val() + "님");
  });
</script>
```

jQuery는 DOM을 선택하고 이벤트가 발생하면 DOM을 직접 변경한다. `.on()`은 선택된 요소에 이벤트 handler를 붙이며, selector를 함께 주면 delegated event도 구성할 수 있다.[5]

### Vue

```vue
<script setup>
import { ref } from 'vue'

const name = ref('')
</script>

<template>
  <input v-model="name" />
  <p>안녕하세요, {{ name }}님</p>
</template>
```

Vue에서는 `name` 상태가 바뀌면 template의 `{{ name }}`가 자동으로 갱신된다. 개발자가 매번 `textContent`를 찾아 직접 바꾸지 않아도 된다. Vue의 template은 component data와 렌더링 DOM을 선언적으로 연결하며, reactivity system이 상태 변경에 따라 필요한 DOM 업데이트를 수행한다.[1][2]

## 2. 값 출력: JSP EL·jQuery text·Vue interpolation

### JSP EL

```jsp
<p>${user.name}</p>
<p>${empty user ? '로그인 필요' : user.name}</p>
```

JSP Expression Language는 서버가 가지고 있는 model·request·session 등의 값을 화면에 표현하는 데 사용한다.

### jQuery

```javascript
$("#user-name").text(user.name);
```

jQuery의 `.text()`는 선택한 DOM 요소의 text content를 읽거나 설정한다. 문자열을 HTML로 해석하지 않는 출력이 필요한 경우 `.html()`보다 안전한 기본 선택이 될 수 있다.

### Vue

```vue
<template>
  <p>{{ user.name }}</p>
  <p>{{ user ? user.name : '로그인 필요' }}</p>
</template>
```

Vue의 mustache interpolation은 기본적으로 값을 plain text로 처리한다. 임의 HTML을 출력하는 `v-html`은 XSS 위험이 있으므로 신뢰된 HTML에만 사용해야 한다.[1]

## 3. 속성 바인딩: JSP 출력·jQuery attr·Vue v-bind

### JSP

```jsp
<a href="${pageUrl}" class="${active ? 'active' : ''}">
  상세보기
</a>
```

서버가 HTML attribute 문자열을 만들어 응답한다.

### jQuery

```javascript
$("#detail-link")
  .attr("href", pageUrl)
  .toggleClass("active", active);
```

jQuery는 이미 생성된 DOM의 attribute와 class를 명령형으로 변경한다.

### Vue

```vue
<template>
  <a :href="pageUrl" :class="{ active: active }">
    상세보기
  </a>
</template>
```

`v-bind`는 `:`로 줄여 쓸 수 있다. Vue는 해당 attribute를 reactive state와 동기화한다.[1]

자주 쓰는 비교:

```text
JSP       → href="${pageUrl}"
jQuery    → .attr("href", pageUrl)
Vue       → :href="pageUrl"
```

## 4. 조건부 렌더링

### JSP: JSTL

```jsp
<c:choose>
  <c:when test="${loggedIn}">
    <span>로그아웃</span>
  </c:when>
  <c:otherwise>
    <span>로그인</span>
  </c:otherwise>
</c:choose>
```

JSP에서는 JSTL과 EL을 이용해 서버 렌더링 시 조건을 선택한다.

### jQuery

```javascript
if (loggedIn) {
  $("#logout").show();
  $("#login").hide();
} else {
  $("#logout").hide();
  $("#login").show();
}
```

jQuery에서는 DOM이 이미 존재하고, script가 표시·숨김 상태를 직접 조정한다.

### Vue

```vue
<template>
  <span v-if="loggedIn">로그아웃</span>
  <span v-else>로그인</span>
</template>
```

Vue의 `v-if`와 `v-else`는 상태에 따라 template 구조를 반응적으로 관리한다.

```text
JSP       → 서버 응답을 만들 때 조건 선택
jQuery    → 브라우저 DOM을 직접 show/hide
Vue       → 상태에 따라 template을 선언
```

## 5. 반복 렌더링

### JSP: JSTL `c:forEach`

```jsp
<ul>
  <c:forEach var="item" items="${items}">
    <li>${item.name}</li>
  </c:forEach>
</ul>
```

### jQuery: each와 직접 append

```javascript
const $list = $("#list").empty();

items.forEach(function (item) {
  $list.append(
    $("<li>").text(item.name)
  );
});
```

문자열 HTML을 직접 이어 붙이기보다 `.text()` 등을 사용해 사용자 입력이 HTML로 해석되지 않게 하는 편이 안전하다.

### Vue: `v-for`

```vue
<template>
  <ul>
    <li v-for="item in items" :key="item.id">
      {{ item.name }}
    </li>
  </ul>
</template>
```

`v-for`에서는 반복 항목을 안정적으로 식별할 `:key`를 함께 제공하는 것이 좋다.

## 6. 이벤트 처리

### JSP

JSP 자체는 브라우저 event system을 관리하는 기술이 아니다. 보통 HTML event attribute나 jQuery·일반 JavaScript를 함께 사용한다.

```jsp
<button onclick="submitForm()">저장</button>
```

### jQuery

```javascript
$("#save").on("click", function (event) {
  event.preventDefault();
  save();
});
```

동적으로 생성되는 요소에는 event delegation을 사용할 수 있다.

```javascript
$("#list").on("click", ".delete", function () {
  deleteItem($(this).data("id"));
});
```

### Vue

```vue
<template>
  <form @submit.prevent="save">
    <button type="submit">저장</button>
  </form>
</template>
```

Vue의 `v-on`은 `@`로 줄여 쓸 수 있고 `.prevent`, `.stop`, `.once` 같은 event modifier를 제공한다.[3]

```text
jQuery: event.preventDefault()를 handler에서 직접 호출
Vue:    @submit.prevent로 의도를 template에 표현
```

## 7. 양방향 입력: JSP form·jQuery val·Vue v-model

### JSP

```jsp
<form method="post" action="/users">
  <input name="email" value="${user.email}">
  <button type="submit">저장</button>
</form>
```

브라우저가 form을 제출하고 서버가 다시 페이지를 생성한다.

### jQuery

```javascript
$("#email").on("input", function () {
  form.email = $(this).val();
});
```

DOM 값과 JavaScript 객체를 동기화하는 코드를 직접 작성해야 한다.

### Vue

```vue
<script setup>
import { ref } from 'vue'

const email = ref('')
</script>

<template>
  <input v-model="email" type="email" />
  <p>{{ email }}</p>
</template>
```

`v-model`은 form input과 reactive state를 연결한다. Vue template에서 ref는 편의상 자동 unwrap되며, JavaScript 코드에서는 `email.value`로 접근한다.[2]

## 8. Ajax와 API 호출

### JSP

JSP는 API client 자체가 아니다. 일반적인 구조는 JSP가 초기 HTML을 만들고, 이후 JavaScript가 Ajax API를 호출하는 방식이다.

```jsp
<script>
  const initialUser = ${userJson};
</script>
```

### jQuery Ajax

```javascript
$.ajax({
  url: "/api/users",
  method: "GET",
  dataType: "json"
})
.done(function (users) {
  renderUsers(users);
})
.fail(function () {
  showError();
});
```

jQuery는 Ajax API와 success·error·complete event를 제공한다.[4]

### Vue + fetch

```vue
<script setup>
import { onMounted, ref } from 'vue'

const users = ref([])
const loading = ref(false)
const error = ref('')

async function loadUsers() {
  loading.value = true
  error.value = ''

  try {
    const response = await fetch('/api/users')
    if (!response.ok) throw new Error('HTTP error')
    users.value = await response.json()
  } catch (e) {
    error.value = '사용자 조회에 실패했습니다.'
  } finally {
    loading.value = false
  }
}

onMounted(loadUsers)
</script>

<template>
  <p v-if="loading">조회 중...</p>
  <p v-else-if="error">{{ error }}</p>
  <ul v-else>
    <li v-for="user in users" :key="user.id">
      {{ user.name }}
    </li>
  </ul>
</template>
```

Vue는 fetch를 강제하지 않는다. fetch, Axios, TanStack Query 같은 API layer를 선택하고, Vue의 reactive state와 연결하면 된다.

## 9. 화면 갱신 방식의 근본 차이

### JSP: 서버 중심

```text
요청
  ↓
Controller
  ↓
Model
  ↓
JSP 렌더링
  ↓
완성된 HTML 응답
```

화면 상태 변경이 서버 요청과 새 HTML 응답으로 이어지는 경우가 많다.

### jQuery: DOM 명령 중심

```text
초기 HTML
  ↓
selector로 DOM 검색
  ↓
이벤트·Ajax callback
  ↓
DOM 직접 수정
```

작은 화면에는 빠르고 직관적이지만, 상태가 많아지면 어느 코드가 DOM을 바꿨는지 추적하기 어려워질 수 있다.

### Vue: 상태 중심

```text
reactive state
  ↓
component template
  ↓
렌더링
  ↓
state 변경 감지
  ↓
필요한 DOM 업데이트
```

Vue는 상태와 template을 연결하고, 반응성 시스템을 통해 상태 변경에 따른 DOM 갱신을 관리한다.[1][2]

## 10. 컴포넌트와 JSP include 비교

### JSP include

```jsp
<%@ include file="/WEB-INF/jsp/common/header.jsp" %>

<main>
  페이지 내용
</main>

<%@ include file="/WEB-INF/jsp/common/footer.jsp" %>
```

JSP include는 서버 측 페이지 조합에 가깝다. 공통 HTML 조각과 서버 model을 결합하는 데 유용하다.

### jQuery partial HTML

```javascript
$("#header").load("/fragments/header.html");
```

브라우저가 HTML 조각을 가져와 특정 DOM 위치에 삽입한다.

### Vue component

```vue
<script setup>
import UserCard from './UserCard.vue'
</script>

<template>
  <UserCard
    v-for="user in users"
    :key="user.id"
    :user="user"
    @remove="removeUser"
  />
</template>
```

Vue component는 template, state, event와 재사용 경계를 함께 갖는다. 부모가 props를 전달하고 자식이 event를 발생시키는 구조로 화면 관계를 명시할 수 있다.

## 11. 문법 대응표

| 목적 | JSP | jQuery | Vue |
|---|---|---|---|
| 값 출력 | `${name}` | `.text(name)` | `{{ name }}` |
| HTML 출력 | JSP 출력·escape 정책 | `.html(html)` | `v-html="html"` |
| 속성 설정 | `href="${url}"` | `.attr("href", url)` | `:href="url"` |
| class 설정 | `${condition}` 조합 | `.toggleClass()` | `:class` |
| 조건 | JSTL `c:if`·`c:choose` | `if` + `.show()`/`.hide()` | `v-if`·`v-else` |
| 반복 | `c:forEach` | `each` + `append` | `v-for` |
| 이벤트 | HTML/JS 필요 | `.on()` | `@click`·`v-on` |
| 입력 연결 | form submit | `.val()` + handler | `v-model` |
| API | JavaScript와 조합 | `$.ajax()` | `fetch`·Axios 등과 reactive state 조합 |
| 화면 조합 | include/taglib | partial HTML | component |
| 상태 갱신 | 서버 재요청 중심 | 직접 DOM 수정 | reactive state 변경 |

## 12. 같은 기능을 Vue로 바꾸는 사고방식

### jQuery 사고방식

```javascript
$("#loading").show();
$.getJSON("/api/items", function (items) {
  $("#loading").hide();
  $("#list").empty();
  items.forEach(function (item) {
    $("#list").append(
      $("<li>").text(item.name)
    );
  });
});
```

### Vue 사고방식

```vue
<script setup>
import { ref } from 'vue'

const loading = ref(false)
const items = ref([])

async function loadItems() {
  loading.value = true
  try {
    items.value = await fetch('/api/items').then((r) => r.json())
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <p v-if="loading">조회 중...</p>
  <ul>
    <li v-for="item in items" :key="item.id">
      {{ item.name }}
    </li>
  </ul>
</template>
```

jQuery에서는 “어떤 DOM을 어떻게 바꿀지”를 작성한다. Vue에서는 “상태가 무엇이고 상태에 따라 어떤 UI를 보여줄지”를 작성한다.

## 13. JSP 개발자가 Vue를 배울 때의 대응

### JSP model → Vue state

```text
JSP: request/model attribute
Vue: ref(), reactive(), props, store
```

JSP에서 서버가 전달하던 값을 Vue에서는 API response, 초기 JSON, props 또는 state store로 공급한다.

### JSTL 조건문 → Vue directive

```text
<c:if>       → v-if
<c:forEach>  → v-for
EL ${value}  → {{ value }} / :attribute
```

### JSP form submit → API + reactive state

JSP form은 서버 endpoint에 submit하고 새 페이지를 받는 전통적 흐름이 강하다. Vue는 `@submit.prevent`로 기본 submit을 막고 API 호출 후 state를 갱신하는 SPA 흐름을 구성할 수 있다.[3]

### JSP include → component

JSP include는 공통 출력 조각을 합치는 방식이고, Vue component는 props·events·local state를 포함하는 UI 단위다. 단순한 파일 include를 그대로 component로 옮기기보다 책임과 데이터 흐름을 함께 분리해야 한다.

## 14. jQuery에서 Vue로 이동할 때 주의할 점

### DOM을 직접 잡지 않기

```javascript
// jQuery 방식
$("#status").text(status);
```

Vue에서는 다음처럼 state를 바꾸는 편이 기본이다.

```javascript
status.value = '완료'
```

```vue
<span>{{ status }}</span>
```

### 같은 상태를 여러 곳에서 중복 관리하지 않기

jQuery에서는 DOM이 사실상의 상태 저장소가 되기 쉽다. Vue에서는 reactive state를 source of truth로 정하고 화면은 state에서 계산되도록 구성한다.

### computed와 method 구분하기

반복 계산 결과는 computed로 분리한다. Vue 공식 문서도 template에 복잡한 logic을 직접 넣기보다 computed property를 사용하라고 안내한다.[1]

### `v-html` 주의

사용자 입력이나 외부 API HTML을 검증 없이 `v-html`로 출력하면 XSS 위험이 있다. 기본 interpolation인 `{{ }}`를 우선 사용하고, HTML이 필요하면 허용 목록 기반 sanitization을 먼저 적용한다.[1]

## 15. 어떤 기술을 선택할까?

### JSP가 적합한 경우

- 서버 렌더링이 중심이다.
- 기존 Spring MVC·Servlet 시스템을 유지한다.
- SEO·초기 HTML·단순 form 처리가 중요하다.
- 화면 상호작용이 복잡하지 않다.

### jQuery가 적합한 경우

- 기존 서버 렌더링 페이지에 작은 동작을 추가한다.
- 전체 frontend framework 도입이 과하다.
- 레거시 plugin과 기존 DOM 구조를 유지해야 한다.
- 작은 Ajax·validation·modal 기능이 필요하다.

### Vue가 적합한 경우

- 화면 상태와 상호작용이 많다.
- component 재사용이 필요하다.
- SPA 또는 부분적으로 reactive한 화면을 만든다.
- DOM 직접 조작을 줄이고 data flow를 명확히 하고 싶다.
- TypeScript·테스트·빌드 기반 frontend를 운영한다.

## 결론

세 기술의 핵심 차이는 다음과 같다.

```text
JSP:
  서버가 HTML을 생성한다.

jQuery:
  JavaScript가 DOM을 직접 조작한다.

Vue:
  reactive state가 template을 갱신한다.
```

기존 기술을 Vue 문법으로 단순 치환하면 충분하지 않다. 구현 사고방식 자체가 바뀐다.

```text
JSP 개발자:
  Model → EL/JSTL → 서버 HTML

jQuery 개발자:
  Selector → Event → DOM 조작

Vue 개발자:
  State → Template/Directive → Reactive UI
```

마이그레이션에서는 다음 순서가 현실적이다.

1. JSP 화면의 server model·form·include 경계를 파악한다.
2. jQuery의 selector·event·Ajax·DOM mutation을 목록화한다.
3. 화면의 source of truth가 어디에 있는지 정한다.
4. 작은 widget부터 Vue component로 분리한다.
5. API response·loading·error·empty 상태를 reactive state로 모델링한다.
6. DOM 직접 조작과 Vue template 조작이 같은 영역에서 충돌하지 않게 한다.
7. XSS·CSRF·권한·API error handling을 별도로 검증한다.

Vue는 jQuery의 상위 호환 버전도 아니고 JSP의 frontend 문법 버전도 아니다. **JSP의 서버 렌더링, jQuery의 DOM 명령, Vue의 상태 기반 UI**를 구분해야 세 기술을 정확히 선택하고 안전하게 전환할 수 있다.

## 참고 자료

[1] Vue Template Syntax — interpolation, directives, attribute binding, `v-html`  
[2] Vue Reactivity Fundamentals — `ref`, `reactive`, `script setup`  
[3] Vue Event Handling — `v-on`, `@`, handlers와 modifiers  
[4] jQuery API Documentation — DOM, event, Ajax API  
[5] jQuery `.on()` — direct/delegated event handling  
[6] Jakarta Server Pages Specification 3.0 — JSP, EL, tag library와 server-side dynamic content

## 출처

- Vue Template Syntax: https://vuejs.org/guide/essentials/template-syntax.html
- Vue Reactivity Fundamentals: https://vuejs.org/guide/essentials/reactivity-fundamentals.html
- Vue Event Handling: https://vuejs.org/guide/essentials/event-handling.html
- jQuery API: https://api.jquery.com/
- jQuery `.on()`: https://api.jquery.com/on/
- Jakarta Server Pages Specification: https://jakarta.ee/specifications/pages/3.0/jakarta-server-pages-spec-3.0

## Sources

[1] https://vuejs.org/guide/essentials/template-syntax.html — Vue Template Syntax
[2] https://vuejs.org/guide/essentials/reactivity-fundamentals.html — Vue Reactivity Fundamentals
[3] https://vuejs.org/guide/essentials/event-handling.html — Vue Event Handling
[4] https://api.jquery.com — jQuery API Documentation
[5] https://api.jquery.com/on — jQuery on
[6] https://jakarta.ee/specifications/pages/3.0/jakarta-server-pages-spec-3.0 — Jakarta Server Pages Specification
