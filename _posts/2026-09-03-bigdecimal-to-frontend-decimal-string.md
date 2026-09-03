---
layout: post
title: "백엔드 BigDecimal 을 프론트에 내릴 때 — 정규식 포맷터는 무엇을 지키고 무엇을 못 지키는가"
date: 2026-09-03 20:23:59 +0900
categories: [backend]
tags: [bigdecimal, javascript, jackson, json, intl-numberformat, precision]
---

정산 코드베이스의 규칙 하나는 이렇게 적혀 있다. "JSON 직렬화 시 금액은 십진 문자열로 다루고,
JS 쪽에서 `Number()` 변환을 제안하지 마라." 이 한 줄을 지키려고 프론트에 정규식 기반
포맷터를 두게 된다. 이 글은 그 정규식이 **정확히 무엇을 벌어주는지**를 실측으로 가른다.

결론부터: **정밀도는 이제 정규식이 아니라 플랫폼이 지켜준다.** 정규식이 실제로 버는 것은
정밀도가 아니라 **계약 좁히기** — 금액 계약이 허용하지 않는 입력을 표시 이전에 `null` 로
떨어뜨리는 일이다. 그 차이를 모르면 정규식을 잘못된 이유로 유지하게 된다.

## 1. 손실은 포맷터가 아니라 `JSON.parse` 에서 이미 일어난다

가장 흔한 오해는 "표시할 때 잘 포맷하면 된다"는 것이다. 아니다. 백엔드가 금액을 JSON
**수치**로 내리는 순간, 손실은 포맷터에 도달하기 전에 끝나 있다.

ECMA-262 는 Number 타입이 IEEE 754-2019 binary64 라고 규정하고
([§6.1.6.1](https://tc39.es/ecma262/multipage/ecmascript-data-types-and-values.html#sec-ecmascript-language-types-number-type)),
`Number.MAX_SAFE_INTEGER` 항목에서 **바로 이 예를 든다**:

> 예를 들어 9007199254740992 와 9007199254740993 은 둘 다 Number 값 9007199254740992 로 평가된다.
> — [ECMA-262, `Number.MAX_SAFE_INTEGER`](https://tc39.es/ecma262/multipage/numbers-and-dates.html#sec-number.max_safe_integer)

$$\texttt{Number.MAX\_SAFE\_INTEGER} = 2^{53} - 1 = 9{,}007{,}199{,}254{,}740{,}991$$

Node v24.14.0 에서 직접 확인한 값이다.

```
Number("9007199254740993")              → 9007199254740992
JSON.parse('{"a":9007199254740993}').a  → 9007199254740992
Number("0.1234567").toLocaleString("ko-KR") → "0.123"
```

두 번째 줄이 핵심이다. `JSON.parse` 는 표준 파서이고, 표준 파서는 JSON 수치를 Number 로
만든다. **응답 본문이 이미 도착했어도 파싱된 시점에 마지막 자리가 없다.** 포맷터를 아무리
잘 짜도 복구할 수 없다.

세 번째 줄은 다른 종류의 손실이다. 값은 멀쩡한데 **표시가 잘린다.** `toLocaleString` 의
기본 `maximumFractionDigits` 가 3 이라 소수 넷째 자리부터 조용히 사라진다. 예외도, 경고도
없다.

JSON 사양 자체가 이 문제를 예고해 뒀다.

> 이 사양은 구현이 수의 범위와 정밀도에 제한을 두는 것을 허용한다. (…) 정수이면서
> $$[-(2^{53})+1,\ (2^{53})-1]$$ 범위에 있는 수는 구현들이 그 수치에 정확히 합의한다는
> 의미에서 상호운용 가능하다.
> — [RFC 8259 §6 Numbers](https://www.rfc-editor.org/rfc/rfc8259#section-6)

즉 JSON 수치는 그 범위 밖에서 **상호운용을 보장하지 않는다.** 원화 정산에서 $$2^{53}$$
원(약 9,007조)을 넘길 일이 흔하냐고 물으면 드물다. 하지만 깨지는 건 큰 정수만이 아니다.
소수 자리가 유효한 요율·수수료·환산액이 훨씬 자주 걸린다. 그리고 **깨져도 아무 신호가
없다는 것**이 이 버그의 성질이다.

그래서 계약을 바꾼다. 금액은 JSON **문자열**로 내린다.

## 2. 백엔드 — 문자열화를 어디서 하느냐가 갈린다

`BigDecimal` 을 문자열로 내리는 방법은 세 가지고, 셋의 성질이 다르다.

| 방법 | JSON 상 타입 | 결과 |
|---|---|---|
| `WRITE_BIGDECIMAL_AS_PLAIN` | **수치** | 지수표기만 없앤다. 파싱 손실은 그대로 |
| `@JsonSerialize(using = ToStringSerializer.class)` | 문자열 | 직렬화기 구현에 의존 — 아래 함정 |
| 필드 타입을 `String` + `toPlainString()` | 문자열 | 런타임 직렬화기와 무관 |

첫 줄이 흔한 착각이다. Jackson 의 `WRITE_BIGDECIMAL_AS_PLAIN` 은 `JsonGenerator.Feature`
로, `SerializationFeature` 쪽 동명 항목은 [2.5 부터 deprecated 되어 이쪽으로 이관됐다](https://fasterxml.github.io/jackson-databind/javadoc/2.13/com/fasterxml/jackson/databind/SerializationFeature.html).
이 플래그가 하는 일은 지수표기를 평문으로 바꾸는 것뿐이고, **값은 여전히 JSON 수치**다.
1절의 손실은 하나도 막지 못한다.

`toString()` 이 아니라 `toPlainString()` 인 이유도 같은 결이다. `BigDecimal` 은
"임의 정밀도 부호 있는 십진수"로, 값이 $$\mathrm{unscaledValue} \times 10^{-\mathrm{scale}}$$ 이며 `toString()` 이
정준 표현을 제공한다([Javadoc](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/math/BigDecimal.html)).
정준 표현은 조건에 따라 지수표기를 쓴다. 지수표기가 섞이면 프론트 정규식이 거부하거나
파서마다 다르게 읽는다. `toPlainString()` 은 그 여지를 없앤다.

### 애너테이션에 맡겼다가 실기동에서 깨진 사례

세 번째 행을 고른 이유가 이 코드베이스에 주석으로 남아 있다.

> ★ 문자열화는 **필드 타입 자체를 String 으로 두고 `toPlainString()`** 으로 만든다.
> 직렬화기 애너테이션에 맡기지 않는 이유: Boot 4 런타임의 HTTP 메시지 변환은
> Jackson 3(`tools.jackson`)이라 Jackson 2 의 `@JsonSerialize/ToStringSerializer` 를
> 무시한다 — 실제로 애너테이션 방식은 단위 테스트(Jackson 2 컨버터 수동 배선)만 통과하고
> 실기동에서는 금액이 수치로 나갔다.
> — `WorkforceComparisonResponse.java` (2026-07-30 실적재 검증에서 발견)

읽어야 할 대목은 "무시한다"가 아니라 **"단위 테스트만 통과했다"** 다. 테스트가 자기 손으로
배선한 Jackson 2 매퍼를 쓰는 바람에, 애너테이션이 먹지 않는 실기동 경로는 아무도 검사하지
않았다. 초록불이 뜬 채로 금액이 수치로 나가고 있었다. 직렬화 계약은 **실제 서빙된 응답
본문**으로 검증해야 한다는 게 이 사례의 교훈이다.

같은 응답에서 **비율과 건수는 수치로 그대로 둔다.** 보존할 정밀도가 없는 값까지 문자열로
바꾸면 클라이언트가 산술할 때마다 되돌려야 한다. 문자열화는 금액에만 건다.

## 3. 프론트 — 정규식 포맷터를 한 줄씩

이제 프론트가 받는 것은 `"43750000.00"` 같은 십진 문자열이다. `Number()` 를 거치지 않고
표시 문자열을 만들어야 한다.

```ts
/** 부호 · 정수부 · (선택)소수부. 지수표기는 금액 계약에 없어 받지 않는다. */
const DECIMAL_RE = /^([+-]?)(\d+)(?:\.(\d+))?$/;

const isAllZero = (digits: string): boolean => /^0*$/.test(digits);

/** 정수부 문자열에 천단위 구분자를 넣는다 (Number 경유 없음). */
const groupThousands = (digits: string): string =>
  digits.replace(/^0+(?=\d)/, '').replace(/\B(?=(\d{3})+(?!\d))/g, ',');
```

각 조각이 하는 일:

- **`^...$` 앵커** — 부분 일치를 막는다. 앵커가 없으면 `"1,234원"` 안의 `1` 만 잡아
  `"1"` 을 표시한다. 금액 표시에서 부분 일치는 곧 오표시다.
- **`(\d+)` 정수부는 필수** — `".5"` 를 거부한다. `BigDecimal.toPlainString()` 은 항상
  정수부를 붙이므로, 정수부가 없다는 건 계약을 지나온 값이 아니라는 뜻이다.
- **지수표기 미수용** — RFC 8259 §6 의 JSON 수 문법은 `exp` 를 허용하지만, 이 정규식은
  받지 않는다. 백엔드가 `toPlainString()` 으로 내보내기로 했으니 `1e21` 이 도착하면
  **계약이 깨진 것**이고, 그때는 그럴듯하게 표시하는 것보다 표시를 포기하는 게 낫다.
- **`^0+(?=\d)`** — 선행 0 제거. 전방탐색이 없으면 `"0"` 이 빈 문자열이 된다.
  (참고로 선행 0 은 JSON 수 문법에서도 금지다: "Leading zeros are not allowed" — RFC 8259 §6.
  문자열 계약이라 도착할 수는 있어 방어한다.)
- **`\B(?=(\d{3})+(?!\d))`** — 천단위 구분자의 정석. `\B` 로 문자열 맨 앞을 제외하고,
  "뒤에 3의 배수 개 숫자가 남았고 그 뒤엔 숫자가 없는" 위치에만 쉼표를 넣는다.
  `(?!\d)` 가 빠지면 `(\d{3})+` 가 앞쪽에서도 매칭돼 자리가 밀린다.

본체는 부호·0·뒤쪽 0 을 처리한다.

```ts
const [, sign, integer, fraction = ''] = matched;
const trimmedFraction = fraction.replace(/0+$/, '');
const zero = isAllZero(integer) && trimmedFraction === '';
const negative = sign === '-' && !zero;
```

`trimmedFraction` 은 `"43750000.00"` 을 `"43,750,000"` 으로 만든다. 표시상 무의미한 뒤쪽
0 만 떼고 **남은 자리는 반올림 없이 전부 보존**한다. `negative` 의 `&& !zero` 는 `"-0.00"`
을 `"0"` 으로 만든다 — 계정 잔액이 `-0` 으로 보이는 건 표시 버그다.

`typeof value === 'number'` 분기가 따로 있는 것도 의도다. 이미 `number` 로 온 값(비율·백분위)은
**보존할 정밀도가 이미 없다.** 문자열 경로로 억지로 밀어넣어봤자 복구되지 않으므로 기존
로케일 포맷을 그대로 쓴다. 이 분기 덕에 마이그레이션이 표시 변화를 만들지 않는다.

## 4. 실측 — 정규식 vs `Intl.NumberFormat(문자열)`

여기서 뒤집힌다. `Intl.NumberFormat.prototype.format()` 은 **문자열 인자를 받고**, 그 경우
Number 변환을 거치지 않는다.

> Number, BigInt, 또는 **문자열**. 문자열은 수 변환과 같은 방식으로 파싱되지만,
> `format()` 은 문자열이 나타내는 **정확한 값을 사용**해 암묵적 Number 변환에서의 정밀도
> 손실을 피한다.
> — [MDN, `Intl.NumberFormat.prototype.format()`](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Intl/NumberFormat/format)

두 구현을 같은 입력에 통과시켰다. Node v24.14.0, 로케일 `ko-KR`,
`Intl` 쪽은 `{ maximumFractionDigits: 20 }`.

| 입력 | `formatDecimal` (정규식) | `Intl`(문자열) |
|---|---|---|
| `"9007199254740993"` | `"9,007,199,254,740,993"` | `"9,007,199,254,740,993"` |
| `"123456789012345678901"` | `"123,456,789,012,345,678,901"` | `"123,456,789,012,345,678,901"` |
| `"0.1234567"` | `"0.1234567"` | `"0.1234567"` |
| `"43750000.00"` | `"43,750,000"` | `"43,750,000"` |
| `"1000.500"` | `"1,000.5"` | `"1,000.5"` |
| `"+2500000"` | `"2,500,000"` | `"2,500,000"` |
| `"000123"` | `"123"` | `"123"` |
| `"-0.00"` | `"0"` | **`"-0"`** |
| `"1e21"` | **`null`** | `"1,000,000,000,000,000,000,000"` |
| `"abc"` | **`null`** | `"NaN"` |
| `""` | **`null`** | **`"0"`** |
| 소수 24자리 | 전부 보존 | 20자리에서 잘림 |

앞 일곱 줄, 즉 **정밀도 관련은 전부 동률이다.** 큰 정수도 유효 소수도 `Intl` 이 문자열
인자로 똑같이 지켜낸다. 정규식이 정밀도를 위해 존재한다는 설명은 이 표 앞에서 유지되지
않는다.

갈리는 건 뒤 다섯 줄이고, 성격이 셋으로 나뉜다.

1. **표시 규범** — `"-0.00"` 을 `"-0"` 으로 보여줄 것인가. 금액 화면에서는 아니다.
2. **계약 위반의 처리** — `"1e21"` 은 계약상 올 수 없는 형식인데 `Intl` 은 성실하게
   포맷해 준다. 깨진 계약이 화면에서 정상으로 보인다.
3. **오류 신호** — `"abc"` 는 `"NaN"` 이라는 **문자열**을 돌려준다. 예외가 아니라서 잡히지
   않고, 그대로 화면에 `NaN` 이 찍힌다.

그리고 셋 중 어디에도 안 들어가는 한 줄이 제일 위험하다.

```
new Intl.NumberFormat("ko-KR").format("")  →  "0"
```

**빈 문자열이 0 으로 표시된다.** 백엔드가 필드를 빠뜨렸든 널을 빈 문자열로 직렬화했든,
화면에는 "0원"이라는 **틀린 사실**이 뜬다. 값이 없다는 것과 값이 0 이라는 것은 정산에서
완전히 다른 진술이다.

소수 자리 상한도 실측했다. `maximumFractionDigits` 는 100 까지 받고 101 에서
`RangeError` 를 던진다. 100 으로 두면 24자리 케이스도 보존된다. 실무 금액 스케일에서는
넉넉하지만, **상한이 있고 넘으면 조용히 반올림된다**는 성질 자체는 남는다.

## 5. 그래서 정규식은 무엇을 버는가 — 계약 좁히기

정리하면 이렇다.

$$
\text{정규식이 버는 것} \;=\; \underbrace{\text{정밀도}}_{\text{플랫폼이 이미 준다}}
\;+\; \underbrace{\text{계약 위반 거부} \;+\; \text{표시 정규화}}_{\text{정규식만 한다}}
$$

`Intl` 은 **표시기**다. 무엇이든 최선을 다해 표시한다. 정규식은 **판별기**다. 계약을
지나온 값인지 먼저 묻는다. 금액 화면에 필요한 건 둘 다다.

그래서 실제로 권할 조합은 "정규식이냐 `Intl` 이냐"가 아니라 **정규식으로 검증하고 `Intl`
로 포맷**하는 쪽이다.

```ts
const nf = new Intl.NumberFormat('ko-KR', { maximumFractionDigits: 100 });

export const formatDecimal = (value: string | number | null | undefined): string | null => {
  if (value === null || value === undefined) return null;
  if (typeof value === 'number') return Number.isFinite(value) ? nf.format(value) : null;

  const matched = DECIMAL_RE.exec(value.trim());   // ← 정규식은 계약 검증만 담당
  if (!matched) return null;                       //    "", "abc", "1e21" 을 여기서 떨군다

  const [, sign, integer, fraction = ''] = matched;
  if (isAllZero(integer) && isAllZero(fraction)) return nf.format('0');   // -0.00 → 0
  return nf.format(`${sign === '-' ? '-' : ''}${integer}${fraction ? `.${fraction}` : ''}`);
};
```

같은 20개 입력으로 원본 구현과 대조했다. `maximumFractionDigits: 20` 에서 **20개 중 19개가
바이트 단위로 동일**했고, 유일한 불일치는 소수 24자리 케이스였다. 100 으로 올리면 그것도
일치한다.

무엇을 얻나. 천단위 구분·소수 표기·부호 위치가 **로케일 규칙**을 따른다. 손으로 짠
`replace(/\B(?=(\d{3})+(?!\d))/g, ',')` 는 세 자리 묶음에 쉼표라는 영어권 관습을 하드코딩한
것이다. 인도식 `1,23,456` 도, 구분자가 점인 로케일도 표현하지 못한다. 통화 기호·회계용
괄호 음수 표기가 필요해지는 순간 `Intl` 쪽은 옵션 한 줄이고 정규식 쪽은 재작성이다.

무엇을 잃나. `maximumFractionDigits` 상한(100)과, `Intl` 출력이 구현마다 달라질 수 있다는
점이다. MDN 은 "출력이 구현 간에 다를 수 있으며 이는 설계상 허용된 것"이라고 명시한다 —
**`format()` 결과를 하드코딩 상수와 비교하는 테스트는 쓰지 말라**는 경고가 붙어 있다.
표시 스냅샷 테스트를 정확 일치로 짜 두었다면 이 전환에서 깨진다.

## 6. 남은 함정 — 표시를 고쳐도 산술은 안 고쳐진다

이 포맷터가 고치는 건 **표시**뿐이다. 같은 값으로 정렬하거나 합계를 내는 코드가
`Number(a) - Number(b)` 라면 1절의 손실이 그대로 살아 있다. 표시 계층만 문자열로 바꾸고
비교·집계를 그대로 두면, **화면의 숫자는 맞는데 정렬 순서가 틀리는** 더 찾기 어려운 형태로
버그가 옮겨간다. 산술이 필요하면 `BigInt`(정수 최소단위) 나 십진 라이브러리로 가야 한다.

플랫폼 차원의 해법은 아직 오지 않았다. TC39 **Decimal** 제안(IEEE 754-2019 Decimal128 기반)은
[Stage 1](https://tc39.es/proposal-decimal/) 이다. 언어에 십진 타입이 들어오기 전까지 금액의
계약은 문자열이다.

채택률도 함께 봐야 한다. 이 코드베이스에서 `formatDecimal`/`decimalSign` 을 실제로 쓰는
파일은 12개다. 한편 `lib/decimal` 밖에서 `toLocaleString` 을 호출하는 줄은 117개고, 그중
금액 어휘(`amount`·`price`·`fee`·`salary`·`balance`·`total`·`commission`·`payout`)가 같은
줄에 있는 것이 45줄이다. **유틸을 만든 것과 전환이 끝난 것은 다르다.**

## 정리

- ❌ 금액을 JSON 수치로 내리고 프론트에서 잘 포맷한다 → **`JSON.parse` 에서 이미 끝났다**
- ❌ `WRITE_BIGDECIMAL_AS_PLAIN` 을 켠다 → 지수표기만 사라지고 값은 여전히 수치다
- ❌ 직렬화기 애너테이션에 맡긴다 → 런타임 매퍼가 바뀌면 조용히 무시된다
- ✅ 필드 타입을 `String` + `toPlainString()`, 비율·건수는 수치로 남김
- ✅ 프론트는 **정규식으로 계약을 검증**하고 **`Intl.NumberFormat` 에 문자열을 넘겨 포맷**
- ✅ 회귀 게이트는 `9007199254740993` 과 `""` 두 줄 — 전자는 정밀도, 후자는 계약

정규식을 "정밀도를 지키려고" 유지하고 있었다면, 그 이유는 2023년 이후로 유효하지 않다.
유지할 이유는 따로 있다. **표시기에게 판별을 시키지 않는 것.**

## References

**1차·공식 (사양·표준·벤더 문서)**

- [ECMA-262, §6.1.6.1 The Number Type](https://tc39.es/ecma262/multipage/ecmascript-data-types-and-values.html#sec-ecmascript-language-types-number-type) — Number 는 IEEE 754-2019 binary64
- [ECMA-262, `Number.MAX_SAFE_INTEGER`](https://tc39.es/ecma262/multipage/numbers-and-dates.html#sec-number.max_safe_integer) — 9007199254740992/993 예시
- [RFC 8259 §6 Numbers](https://www.rfc-editor.org/rfc/rfc8259#section-6) — JSON 수 문법, 상호운용 범위, 선행 0 금지
- [MDN, `Intl.NumberFormat.prototype.format()`](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Intl/NumberFormat/format) — 문자열 인자와 정밀도 보존
- [Java SE 21 `BigDecimal` Javadoc](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/math/BigDecimal.html) — `unscaledValue × 10^-scale`, `toString()` 정준 표현
- [Jackson `SerializationFeature` Javadoc](https://fasterxml.github.io/jackson-databind/javadoc/2.13/com/fasterxml/jackson/databind/SerializationFeature.html) — `WRITE_BIGDECIMAL_AS_PLAIN` 의 `JsonGenerator.Feature` 이관

**제안 (표준 아님)**

- [TC39 Decimal proposal](https://tc39.es/proposal-decimal/) — Stage 1 (2026-06-30 초안)

## 근거의 한계

- 4절과 5절의 실측 표는 **Node v24.14.0 / 로케일 `ko-KR` 단일 환경**에서 얻은 값이다.
  MDN 이 명시하듯 `Intl` 출력은 구현마다 다를 수 있으므로, 브라우저·ICU 버전이 다르면
  일부 칸이 달라질 수 있다. 다른 런타임에서의 교차 검증은 하지 않았다.
- 6절의 "45줄" 은 `toLocaleString` 이 있는 줄에 금액 어휘가 같이 있는지를 본 **어휘 필터**
  결과다. 각 줄이 실제로 금액을 표시하는지 하나씩 확인한 값이 아니므로, 미전환 규모의
  정확한 수치가 아니라 자릿수 감각으로만 읽어야 한다.
- 2절의 Jackson 2/3 사례는 이 코드베이스의 소스 주석에 기록된 자체 관찰이다. Jackson 3 의
  Jackson 2 애너테이션 처리 정책에 대한 벤더 공식 문서로 교차 확인하지는 않았다.
</content>
