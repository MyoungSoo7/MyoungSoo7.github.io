---
layout: post
title: "Vue 프론트 유효성 체크 — 직접 구현부터 VeeValidate·Zod 까지, 그리고 서버가 다시 봐야 하는 이유"
date: 2026-10-16 00:23:25 +0900
categories: [frontend]
tags: [vue, validation, vee-validate, zod, vuelidate, accessibility, wcag, spring]
---

Vue 에서 폼 유효성 체크를 어떻게 하느냐는 질문의 답은 **폼 크기**에 따라 갈린다. 필드 몇 개면 `computed` 로 직접 짜는 게 낫고, 폼이 커지면 스키마 라이브러리를 쓰는 게 낫다. 어느 쪽이든 변하지 않는 전제가 하나 있다. **프론트 검증은 UX 이고, 보안은 서버가 한다.**

이 글은 Vue 3 기준으로 세 가지 방법을 비교하고, 실무에서 자주 밟는 함정 네 가지(한글 IME, 에러 표시 시점, 접근성, 라이브러리 버전 궁합)를 공식 문서 기준으로 정리한다. 백엔드 쪽 시나리오는 어제 쓴 [유효성 검사 실전 시나리오 30가지]({{ site.baseurl }}/2026/10/15/input-validation-30-scenarios/)에 있다. 이 글은 그 앞단이다.

---

## 0. 먼저 — 프론트 검증은 우회된다

MDN 은 HTML 제약 검증(constraint validation)을 설명하면서 **서버 측 검증이 여전히 필요하다**고 못박는다. 이유도 구체적으로 든다. 개발자 도구로 HTML 을 고치거나, 폼을 거치지 않고 HTTP 요청을 직접 만들거나, 스크립트로 값을 넣으면 일부 검사는 아예 돌지 않는다 ([MDN — Constraint validation][mdn-cv]).

OWASP 도 같은 입장이다. 유효성 검사는 형식(syntax)과 의미(semantics)를 둘 다 보는 것이고, SQL 인젝션·XSS 방어와 **인가(authorization)는 별개 통제**다 ([OWASP Input Validation Cheat Sheet][owasp-iv]).

그래서 프론트 검증의 역할은 정확히 이것이다.

- 사용자가 **제출 전에** 틀린 걸 알게 한다 (왕복 한 번 절약)
- 무엇이 왜 틀렸는지 **글로** 알려 준다
- 서버로 가는 명백한 쓰레기 요청을 줄인다

막아 주는 것은 없다. 이 전제를 깔고 방법을 고른다.

---

## 1. 방법 ① — 직접 구현 (필드 3~4개짜리 폼)

로그인·검색·간단한 문의 폼이라면 라이브러리 없이 `reactive` + `computed` 로 충분하다.

{% raw %}
```vue
<script setup>
import { reactive, computed } from 'vue'

const form = reactive({ email: '', password: '' })
const touched = reactive({ email: false, password: false })

const errors = computed(() => ({
  email: /^\S+@\S+\.\S+$/.test(form.email) ? '' : '이메일 형식이 아닙니다 (예: name@domain.com)',
  password: form.password.length >= 8 ? '' : '비밀번호는 8자 이상이어야 합니다',
}))
const valid = computed(() => Object.values(errors.value).every(e => !e))

function onSubmit() {
  touched.email = touched.password = true   // 제출 시엔 전부 보여 준다
  if (!valid.value) return
  // api.post('/login', form) ...
}
</script>

<template>
  <form @submit.prevent="onSubmit" novalidate>
    <label for="email">이메일</label>
    <input id="email" v-model.trim="form.email" @blur="touched.email = true"
           :aria-invalid="touched.email && !!errors.email"
           aria-describedby="email-err" />
    <p id="email-err" v-if="touched.email && errors.email">{{ errors.email }}</p>

    <label for="pw">비밀번호</label>
    <input id="pw" type="password" v-model="form.password" @blur="touched.password = true"
           :aria-invalid="touched.password && !!errors.password"
           aria-describedby="pw-err" />
    <p id="pw-err" v-if="touched.password && errors.password">{{ errors.password }}</p>

    <button type="submit">로그인</button>
  </form>
</template>
```
{% endraw %}

포인트 세 가지.

1. **`touched` 를 따로 둔다.** 에러는 계산은 항상 하되, 사용자가 그 칸을 한 번 떠난 뒤(blur)나 제출을 누른 뒤에만 *보여 준다*. 안 그러면 페이지를 열자마자 빨간 글씨가 깔린다.
2. **`v-model.trim`** 으로 앞뒤 공백을 걸러 낸다. Vue 는 `.trim`·`.number`·`.lazy` 수식어를 공식 지원한다 ([Vue — Form Input Bindings][vue-forms]). 단, 서버가 같은 정규화를 다시 해야 한다 — 프론트 정규화도 우회된다.
3. **`novalidate`** 를 붙이면 브라우저 기본 말풍선 대신 내 에러 문구를 쓴다. 기본 검증(`type="email"`, `required`)을 그대로 쓰고 싶으면 빼면 된다 ([MDN][mdn-cv]).

이메일 정규식은 일부러 느슨하게 썼다. 이메일 형식을 프론트에서 정밀하게 맞추려는 시도는 정상 주소를 거절하는 쪽으로 실패하기 쉽다. "@ 가 있고 점이 있다" 정도만 보고, 진짜 확인은 서버의 인증 메일로 한다.

**한계:** 필드가 10개를 넘거나, 비밀번호 확인처럼 **필드 간 규칙**이 생기거나, 서버 중복 확인 같은 **비동기 검사**가 끼면 `touched`·`pending`·제출 상태를 손으로 관리하는 코드가 폼 본체보다 커진다. 그때가 라이브러리로 넘어갈 시점이다.

---

## 2. 방법 ② — VeeValidate + Zod (실무 기본값)

VeeValidate 는 Composition API 기반으로 만들어진 Vue 폼 라이브러리다. `useForm`·`useField` 가 핵심이고, Yup·Zod·Valibot 스키마를 공식 연동 패키지로 지원한다 ([VeeValidate — Getting started][vv-start]).

{% raw %}
```vue
<script setup>
import { useForm } from 'vee-validate'
import { toTypedSchema } from '@vee-validate/zod'
import { z } from 'zod'

const schema = toTypedSchema(
  z.object({
    email: z.string().min(1, '이메일을 입력하세요').email('이메일 형식이 아닙니다'),
    password: z.string().min(8, '비밀번호는 8자 이상이어야 합니다'),
    passwordConfirm: z.string(),
  }).refine(v => v.password === v.passwordConfirm, {
    message: '비밀번호가 일치하지 않습니다',
    path: ['passwordConfirm'],          // 에러를 붙일 필드
  })
)

const { handleSubmit, errors, defineField, setErrors, isSubmitting } =
  useForm({ validationSchema: schema })

const [email, emailAttrs] = defineField('email')
const [password, passwordAttrs] = defineField('password')
const [passwordConfirm, confirmAttrs] = defineField('passwordConfirm')

const onSubmit = handleSubmit(async values => {
  // 전 필드가 통과했을 때만 여기 들어온다
  await api.post('/signup', values)
})
</script>

<template>
  <form @submit="onSubmit">
    <input v-model="email" v-bind="emailAttrs" />
    <span>{{ errors.email }}</span>

    <input type="password" v-model="password" v-bind="passwordAttrs" />
    <span>{{ errors.password }}</span>

    <input type="password" v-model="passwordConfirm" v-bind="confirmAttrs" />
    <span>{{ errors.passwordConfirm }}</span>

    <button :disabled="isSubmitting">가입</button>
  </form>
</template>
```
{% endraw %}

직접 구현 대비 얻는 것:

- **`handleSubmit`** 은 모든 필드를 검사하고 전부 통과해야 콜백을 부른다. 폼 이벤트 핸들러로 쓰면 기본 제출도 알아서 막는다(`.prevent` 불필요). 실패 시 두 번째 인자 콜백으로 첫 오류 필드에 포커스를 줄 수 있다 ([VeeValidate — Handling Forms][vv-forms]).
- **`meta`** 에 `valid`·`dirty`·`touched`·`pending` 이 폼 단위로 모인다. 제출 버튼 비활성화 같은 조건을 손으로 집계할 필요가 없다 ([VeeValidate — Handling Forms][vv-forms]).
- **스키마 하나가 타입·규칙·메시지를 같이 들고 있다.** `toTypedSchema` 는 Zod 스키마에서 입력값과 제출값의 타입을 끌어낸다 ([VeeValidate — Zod][vv-zod]).
- **필드 간 규칙**은 Zod 의 `refine` + `path` 로 특정 필드에 에러를 붙인다.

### ⚠️ 버전 궁합 — 지금 `npm i zod` 하면 깨진다

여기서 실제로 많이 막힌다. 2026-10-16 npm 레지스트리 기준:

| 패키지 | latest | 비고 |
| --- | --- | --- |
| `vee-validate` | 4.15.1 | v5 는 `5.0.0-beta.1` (beta 태그) |
| `@vee-validate/zod` | 4.15.1 | **peerDependency `zod@^3.24.0`** |
| `zod` | 4.6.7 | latest 가 이미 v4 |

즉 아무 버전 지정 없이 세 개를 설치하면 Zod 4 가 깔리고 `@vee-validate/zod` 의 peer 조건(`^3.24.0`)과 충돌한다. 실제로 이 오류를 보고한 사용자 논의가 VeeValidate 리포에 남아 있다 ([vee-validate Discussion #5086][vv-5086]). (표의 수치는 `registry.npmjs.org` 를 직접 조회한 값이다.)

선택지는 둘이다.

1. **안정판 조합:** `vee-validate@4` + `@vee-validate/zod@4` + `zod@3` 으로 고정한다. 위 예제 코드가 그대로 돈다.
2. **Zod 4 를 써야 한다면:** VeeValidate v5 로 간다. v5 는 Standard Schema 를 직접 지원해서 `@vee-validate/zod` 같은 연동 패키지가 필요 없어지고, `toTypedSchema` 호출만 지우면 된다 ([VeeValidate v5 Migration Guide][vv-v5]). 다만 **아직 beta** 라는 점을 감안해야 한다.

Zod 4 로 가면 에러 메시지 파라미터도 `message` 에서 `error` 로 바뀌었다(구 파라미터는 deprecated 지만 동작은 한다) ([Zod 4 Migration guide][zod-v4]). 예제를 복사할 때 어느 버전 문서인지 확인할 것.

---

## 3. 방법 ③ — Vuelidate (기존 프로젝트라면)

Vuelidate 는 규칙을 데이터 모델 옆에 같은 구조로 선언하는 "모델 기반" 방식이다. Vue 3 과 Vue 2 를 둘 다 지원하기 때문에 **Vue 2 레거시**에서 많이 쓰였다 ([Vuelidate — Getting started][vuelidate]).

```js
import { useVuelidate } from '@vuelidate/core'
import { required, email } from '@vuelidate/validators'

const state = reactive({ email: '' })
const rules = { email: { required, email } }
const v$ = useVuelidate(rules, state)
// v$.value.email.$error, v$.value.$validate()
```

다만 Vuelidate 공식 문서 스스로 **현재 LTS 모드**라고 밝히고, 활발히 유지보수되는 대안으로 Regle·VeeValidate 를 소개한다 ([Vuelidate][vuelidate]). 새 프로젝트라면 굳이 고를 이유가 없고, 이미 쓰고 있다면 무리해서 옮길 이유도 없다.

### UI 라이브러리 내장 검증

Element Plus(`el-form :rules`), Vuetify(`v-text-field :rules`), Quasar(`q-input :rules`)는 각자 검증 규칙을 받는다. 이미 그 UI 키트로 화면을 짜고 있다면 내장 기능을 쓰는 게 에러 표시 스타일까지 맞아서 편하다. 스키마를 백엔드와 공유하고 싶어지는 시점에 VeeValidate 로 감싸는 걸 고려하면 된다.

---

## 4. 실무 함정 네 가지

### ① 한글 입력 중엔 `v-model` 이 갱신되지 않는다

Vue 공식 문서 주석: 중국어·일본어·한국어처럼 **IME 를 쓰는 언어는 조합(composition) 중에 `v-model` 이 갱신되지 않는다.** 조합 중에도 반응하려면 `v-model` 대신 직접 `input` 이벤트와 `value` 바인딩을 쓰라고 한다 ([Vue — Form Input Bindings][vue-forms]).

증상은 이렇다. "이름 2자 이상" 규칙인데 "홍길" 까지 쳐도 마지막 글자가 조합 중이라 모델엔 "홍" 만 들어가 있다. 실시간 글자 수 카운터나 "입력하면 즉시 에러가 사라지는" UX 에서 한 박자 늦게 보인다.

{% raw %}
```vue
<input :value="name" @input="e => name = e.target.value" />
```
{% endraw %}

이렇게 쓰면 조합 중 값도 들어온다. 단, 조합이 안 끝난 값으로 검증하면 "홍ㄱ" 같은 중간 상태가 잠깐 에러로 보일 수 있다. **blur 시점 검증**이면 이 문제는 거의 안 생긴다 — 그래서 한글 서비스는 "타이핑 중 즉시 검증"보다 "떠날 때 검증 + 제출 시 전체 검증"이 기본값으로 무난하다.

### ② 에러를 언제 보여 줄 것인가

규칙은 하나로 정해 두고 폼 전체에 일관되게 쓴다. 권장 기본값:

- **처음 진입:** 아무 에러도 안 보여 준다
- **필드를 떠날 때(blur):** 그 필드만 검사·표시
- **이미 에러가 떠 있는 필드:** 입력할 때마다 재검사 — 고치는 즉시 사라지게
- **제출:** 전부 touched 로 만들고 전부 표시, 첫 에러 필드로 포커스

VeeValidate 의 `handleSubmit` 이 제출 시 모든 필드의 `touched` 를 `true` 로 바꾸는 것도 이 흐름이다 ([VeeValidate — Handling Forms][vv-forms]).

### ③ 빨간 테두리만으로는 에러가 아니다 — 접근성

WCAG 2.2 성공기준 3.3.1(Error Identification)은 입력 오류를 자동으로 감지했다면 **어느 항목이 틀렸는지 식별하고 오류를 텍스트로 설명**하라고 요구한다. 색이나 아이콘은 *추가로* 써도 되지만 텍스트를 대신할 수 없다 ([W3C — Understanding SC 3.3.1][wcag-331]).

구현 기법은 W3C 의 ARIA21 이 정리해 뒀다.

- 실패한 필드에 `aria-invalid="true"`
- 에러 문구 요소에 `id` 를 주고 입력에 `aria-describedby` 로 연결
- **검증을 수행하기 전에는 `aria-invalid="true"` 를 걸지 않는다**

([W3C — ARIA21][aria21]) 1장 예제의 `:aria-invalid="touched.email && !!errors.email"` 가 정확히 이 세 번째 조건이다.

### ④ 비동기 검증(중복 확인)은 마지막 응답만 믿는다

아이디 중복 확인처럼 서버를 부르는 검증은 응답 순서가 뒤집힐 수 있다. "abc" 요청이 "abcd" 요청보다 늦게 오면 화면에 엉뚱한 결과가 남는다. 입력 디바운스(300ms 안팎)를 걸고, 응답이 왔을 때 **현재 입력값과 요청 당시 값이 같은지** 확인한 뒤에만 반영한다. 그리고 이 결과는 어디까지나 안내다 — 중복 확인을 통과해도 가입 시점에 다른 사람이 먼저 가져갈 수 있으므로, 최종 판정은 서버의 DB UNIQUE 제약이 한다.

---

## 5. 서버로 이어 붙이기 — 400 을 폼에 다시 뿌린다

프론트를 통과해도 서버가 거절할 수 있다(이미 쓰는 이메일, 서버에만 있는 규칙). 그 결과를 토스트 한 줄로 끝내지 말고 **해당 필드 아래에** 다시 꽂아 주면 두 계층이 한 화면으로 이어진다.

Spring MVC 는 `@RequestBody` 파라미터에 `@Valid` 를 붙이면 Bean Validation 을 실행하고, 실패 시 `MethodArgumentNotValidException` 을 던진다. 파라미터에 직접 `@NotBlank` 같은 제약을 붙이는 경우엔 `HandlerMethodValidationException` 이 나므로, 공식 문서는 **두 예외를 모두 처리하라**고 권한다 ([Spring — Validation][spring-val], [Spring — Java Bean Validation][spring-bv]).

```kotlin
data class SignupRequest(
    @field:NotBlank @field:Email val email: String,
    @field:Size(min = 8) val password: String,
)

@PostMapping("/signup")
fun signup(@Valid @RequestBody req: SignupRequest) = service.signup(req)
```

`@ControllerAdvice` 에서 필드 에러를 `{ "errors": { "email": "이미 사용 중인 이메일입니다" } }` 모양으로 내려 주면, 프론트에서는 VeeValidate 의 `setErrors` 한 줄로 받는다 ([VeeValidate — useForm][vv-useform]).

```js
const onSubmit = handleSubmit(async values => {
  try {
    await api.post('/signup', values)
  } catch (e) {
    if (e.response?.status === 400) setErrors(e.response.data.errors)
    else throw e
  }
})
```

이 구조의 장점은 **규칙이 둘로 갈라져도 화면은 하나**라는 것이다. 프론트 스키마와 서버 제약이 조금 어긋나 있어도(어긋나는 게 정상이다) 사용자는 같은 자리에서 같은 모양의 에러를 본다.

---

## 고르는 기준 한 장

| 상황 | 추천 |
| --- | --- |
| 필드 3~4개, 필드 간 규칙 없음 | 직접 구현 (`computed` + `touched`) |
| 회원가입·결제·다단계 폼, 비동기 검사 | VeeValidate + Zod (버전 고정 주의) |
| 이미 Element Plus·Vuetify·Quasar 로 화면을 짬 | 내장 `rules` |
| Vue 2 레거시 유지보수 | 쓰던 것(Vuelidate 등) 유지 |
| 어떤 경우든 | **서버에서 다시 검증** + 400 을 필드에 다시 표시 |

체크리스트:

- [ ] 서버가 같은 규칙을 다시 검사하는가 (프론트 검증은 보안이 아니다)
- [ ] 처음 진입 시 에러가 안 보이는가 (`touched` 이후에만)
- [ ] 한글 입력 필드에서 조합 중 값 처리를 정했는가
- [ ] 에러가 색이 아니라 **텍스트**로, 필드에 `aria-describedby` 로 연결돼 있는가
- [ ] 제출 실패 시 첫 에러 필드로 포커스가 가는가
- [ ] 비동기 검증이 늦게 온 응답을 버리는가
- [ ] `vee-validate` / `@vee-validate/zod` / `zod` 버전을 고정했는가
- [ ] 서버 400 응답을 해당 필드 아래에 다시 보여 주는가

---

## References

1. MDN Web Docs, ["Using HTML form validation and the Constraint Validation API"][mdn-cv] — 서버 측 검증이 여전히 필요한 이유
2. OWASP Cheat Sheet Series, ["Input Validation Cheat Sheet"][owasp-iv] — syntax/semantics, allowlist, 인가와의 분리
3. Vue.js, ["Form Input Bindings"][vue-forms] — `v-model` 수식어, IME 조합 중 미갱신 주석
4. VeeValidate v4, ["Getting started (Composition API)"][vv-start]
5. VeeValidate v4, ["Handling Forms"][vv-forms] — `handleSubmit`, `meta`, 제출 동작
6. VeeValidate v4, ["Zod Schema Validation"][vv-zod] — `toTypedSchema`
7. VeeValidate v4, ["useForm API"][vv-useform] — `errors`, `setErrors`
8. VeeValidate v5, ["Migration Guide"][vv-v5] — Standard Schema 지원, 연동 패키지 deprecated
9. logaretm/vee-validate, ["How is the support for Zod 4? (Discussion #5086)"][vv-5086] — `@vee-validate/zod` 의 zod peer 충돌 보고
10. Zod, ["Migration guide (Zod 4)"][zod-v4] — `message` → `error` 파라미터
11. Vuelidate, ["Getting started"][vuelidate] — LTS 모드 공지 및 대안
12. W3C WAI, ["Understanding Success Criterion 3.3.1: Error Identification" (WCAG 2.2)][wcag-331]
13. W3C WAI, ["ARIA21: Using aria-invalid to Indicate An Error Field"][aria21]
14. Spring Framework Reference, ["Validation (Web MVC)"][spring-val] — `MethodArgumentNotValidException` / `HandlerMethodValidationException`
15. Spring Framework Reference, ["Java Bean Validation"][spring-bv]
16. npm registry (`registry.npmjs.org`) — `vee-validate`, `@vee-validate/zod`, `zod` 의 latest·peerDependencies (2026-10-16 직접 조회)

[mdn-cv]: https://developer.mozilla.org/en-US/docs/Web/HTML/Constraint_validation
[owasp-iv]: https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html
[vue-forms]: https://vuejs.org/guide/essentials/forms.html
[vv-start]: https://vee-validate.logaretm.com/v4/guide/composition-api/getting-started/
[vv-forms]: https://vee-validate.logaretm.com/v4/guide/composition-api/handling-forms/
[vv-zod]: https://vee-validate.logaretm.com/v4/integrations/zod-schema-validation/
[vv-useform]: https://vee-validate.logaretm.com/v4/api/use-form/
[vv-v5]: https://vee-validate.logaretm.com/v5/guide/migration/
[vv-5086]: https://github.com/logaretm/vee-validate/discussions/5086
[zod-v4]: https://zod.dev/v4/changelog
[vuelidate]: https://vuelidate-next.netlify.app/
[wcag-331]: https://www.w3.org/WAI/WCAG22/Understanding/error-identification.html
[aria21]: https://www.w3.org/WAI/WCAG22/Techniques/aria/ARIA21
[spring-val]: https://docs.spring.io/spring-framework/reference/web/webmvc/mvc-controller/ann-validation.html
[spring-bv]: https://docs.spring.io/spring-framework/reference/core/validation/beanvalidation.html
