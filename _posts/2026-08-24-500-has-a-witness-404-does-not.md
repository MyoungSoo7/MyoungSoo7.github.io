---
layout: post
title: "500 은 목격자가 있고 404 는 없다 — 바이브 코딩 에러를 Playwright 로 볼 것인가, 직접 볼 것인가"
date: 2026-08-24 17:28:04 +0900
categories: [engineering, AI]
tags: [vibe-coding, playwright, debugging, http, observability, delta-debugging, rfc9110]
---

에이전트에게 시켜서 만든 화면이 500 을 뱉는다. 혹은 404 를 뱉는다.
여기서 손이 갈라진다. 하나는 **Playwright 테스트를 하나 짜서 재현시키는 것**, 다른 하나는 **브라우저를 열고 직접 보는 것**.
어느 쪽이 나은가 — 이게 오늘 받은 질문이다.

먼저 결론부터 적는다. **둘은 경쟁 관계가 아니라 순서 관계다.** 직접 보기는 *가설을 만들고*, 자동 재현기는 그 가설을 *시험 가능하게* 만든다. 순서를 뒤집으면 둘 다 헛돈다.

그런데 이 답보다 먼저 정해야 할 게 하나 있다. **500 과 404 는 같은 종류의 사건이 아니다.** 계측을 고르기 전에 이걸 먼저 갈라야 하는데, 그 근거는 의견이 아니라 스펙에 적혀 있다.

---

## 1. 바이브 코딩에서 Kernighan 의 법칙이 깨지는 방식

1978년에 Kernighan 과 Plauger 가 쓴 문장이 있다.[^kp]

> Everyone knows that debugging is twice as hard as writing a program in the first place. So if you're as clever as you can be when you write it, how will you ever debug it?

디버깅은 작성보다 두 배 어렵다. 그러니 쓸 수 있는 만큼 영리하게 짜 놓으면, 그걸 어떻게 디버깅할 것인가 — 라는 자문이다. 여기엔 **내가 그걸 썼다** 는 전제가 깔려 있다. 두 배라는 비율이 성립하려면 분모가 있어야 한다.

바이브 코딩에는 그 분모가 없다. Karpathy 가 이 말을 처음 쓸 때 스스로 묘사한 작업 방식이 그렇다 — `"Accept All" always`, diff 를 읽지 않고, 코드가 자기 이해 범위를 넘어 자란다.[^karpathy] 그러면 디버깅 난이도는 작성 난이도의 두 배가 아니라 **정의되지 않는다**. 내가 그 코드에 대해 아는 것은, 디버깅 시점에 **바깥에서 재구성해 낸 만큼**이 전부다.

그래서 바이브 코딩에서는 이 명제가 성립한다.

> **관측 도구의 선택이 곧 이해의 상한이다.**

손으로 짠 코드라면 계측이 부족해도 "이 함수가 뭘 하는지는 내가 안다" 로 메울 수 있다. 여기서는 못 메운다. 계측 선택은 편의의 문제가 아니라 **인식 예산 전부**다. 질문이 사소해 보이지 않는 이유가 이것이다.

---

## 2. 500 과 404 는 목격자의 유무가 다르다 (RFC 9110)

HTTP 시맨틱스는 RFC 9110 에 있다. 두 클래스의 정의 문장을 그대로 놓고 보면 차이가 선명하다.[^rfc9110]

**5xx (§15.6):**

> The 5xx (Server Error) class of status code indicates that the server **is aware that it has erred** or is incapable of performing the requested method.

**500 (§15.6.1):**

> The 500 (Internal Server Error) status code indicates that the server encountered an **unexpected condition** that prevented it from fulfilling the request.

**4xx (§15.5):**

> The 4xx (Client Error) class of status code indicates that the client **seems to** have erred.

**404 (§15.5.5):**

> The 404 (Not Found) status code indicates that the origin server did not find a current representation for the target resource **or is not willing to disclose that one exists**.

여기서 갈린다.

5xx 는 **서버가 자기가 틀렸음을 안다(is aware that it has erred)** 는 뜻이다. 안다는 건 그 앎이 어딘가에 새겨졌다는 뜻이고, 실무에서 그건 스택트레이스다. **500 에는 목격자가 있다. 다만 그 목격자는 브라우저에 없다.**

404 는 정반대다. 404 는 오류가 아니라 **정상 동작**이다. 서버는 멀쩡하고, 스펙은 심지어 *"존재를 알려주지 않기로 한 경우"* 까지 404 로 인정한다. 즉 404 는 **설계상 진단 정보를 담지 않는다.** 4xx 클래스 정의가 `seems to have erred` 라고 hedge 를 건 것도 같은 맥락이다 — 스펙조차 책임 소재를 단정하지 않는다.

$$
\text{500} \;\Rightarrow\; \exists\,\text{목격자} \;\wedge\; \text{목격자} \notin \text{브라우저}
$$

$$
\text{404} \;\Rightarrow\; \text{목격자가 없을 수 있고, 없는 것이 정상이다}
$$

**여기서 나오는 실무 규칙이 하나 있다.**

- **500 을 브라우저에서 들여다보는 건 거의 항상 잘못된 계층이다.** 브라우저가 보여주는 건 *사건*이 아니라 *통보*다. 사건은 서버 쪽 스택에 있다.
- **404 는 정반대다.** 서버 쪽에 아무 증거가 없을 수 있으므로, 브라우저 Network 패널이 *증거 전부*인 경우가 흔하다 — 어떤 URL 이, 어떤 리다이렉트를 거쳐, 어떤 헤더로 실제로 나갔는가.

### 404 가 아무 흔적도 남기지 않은 실제 사례

이 블로그 자체에서 겪은 일이다. 글을 커밋하고 푸시했는데 퍼머링크가 404 였다. 원인은 front matter 의 `date:` 를 손으로 적으면서 몇 분 미래 시각을 넣은 것이었다. Jekyll 기본값 `future: false` 는 미래 날짜 글을 **조용히 제외한다.**

이 사고의 관측상 성질이 중요하다.

- GitHub Pages 빌드 상태: `built`
- 빌드 소요시간: 0 이 아님 (큐 거절이 아니라 실제로 돌았다는 뜻)
- 종료 코드: 정상
- 에러 로그: **세상 어디에도 없음**
- 사용자가 보는 것: 404

여기에 Playwright 테스트를 붙였다면 `404` 를 아주 성실하게 보고했을 것이고, 그 보고는 **아무것도 가르쳐 주지 않는다.** 증거는 서빙 계층이 아니라 *빌드 산출물 목록*에 있었다 — 정확히는 "있어야 할 파일이 없다" 는 **부재**가 증거였다. 부재는 어떤 요청으로도 관측되지 않는다.

### 그리고 상태 코드는 무고한 용의자를 지목한다

RFC 9110 §15.6.3 은 502 를 이렇게 정의한다.

> The 502 (Bad Gateway) status code indicates that the server, while acting as a gateway or proxy, received an **invalid response** from an inbound server it accessed.

2026-08-14 에 겪은 502 는 이 정의에 맞지 않았다. 업스트림 사이드카는 `POST /synthesize 200 OK` 를 찍고 있었다 — 유효한 응답이었다. 죽은 건 **호출자 자신의 디코더**였다. Spring `WebClient` 의 기본 인메모리 버퍼가 262,144 바이트이고, base64 로 인라인된 오디오가 그걸 넘기면서 `DataBufferLimitException` 이 **응답을 다 받은 뒤에** 터졌다.

에러 detail 문자열이 이 사고를 한 줄로 요약한다.

```text
200 OK from POST ... but response failed with cause
```

**같은 문장 안에서 상태 코드와 결과가 서로를 부정한다.** 이런 실패는 업스트림 관점에서 완벽한 성공이라 어느 로그에도 증상이 안 남는다. 이 건의 전말은 [커밋 316개를 다시 읽은 글](https://myoungsoo7.github.io/2026/08/24/lemuel-xr-316-commits-five-wrong-first-diagnoses/)의 오진 ① 에 적어 뒀다.

---

## 3. Playwright 는 디버거가 아니다 — 공식 문서가 그렇게 말한다

이제 도구 쪽. 반사적으로 짜게 되는 체크는 대개 이렇게 생겼다.

```js
await page.goto('/orders');
```

Playwright 공식 문서의 `page.goto()` 항목에 이렇게 적혀 있다.[^pw-goto]

> The method **will not throw an error when any valid HTTP status code is returned** by the remote server, including 404 "Not Found" and 500 "Internal Server Error".

즉 **지금 잡으려는 두 에러 모두에서 이 줄은 초록이다.** 문서는 이어서 `response.status()` 로 직접 확인하라고 안내한다. 그리고 `goto()` 가 돌려주는 것은 "the main resource response" — **메인 프레임 응답 하나**뿐이다.

SPA 라면 이 함정이 더 깊어진다. 셸은 200 으로 잘 뜨고 `/api/orders` 만 500 이면, 화면엔 빈 목록이 렌더되고 껍데기에 대한 모든 assertion 이 통과한다. `goto()` 는 XHR 을 건드리지도 않는다.

이건 [어제 쓴 완료기준 글](https://myoungsoo7.github.io/2026/08/24/vibe-coding-mvp-vs-harness-definition-of-done/)의 "0개 실행도 0 실패다" 와 **정확히 같은 실패 모드**다. 체크는 돌았고, 성공을 보고했고, 깨진 것에는 닿지도 않았다.

고치는 방향은 assertion 을 더 붙이는 게 아니라 **오라클을 네트워크 계층으로 내리는 것**이다. Playwright 문서가 `request`/`response` 이벤트 구독을 안내한다.[^pw-network]

```js
const bad = [];
page.on('response', r => {
  if (r.status() >= 400) bad.push(`${r.status()} ${r.url()}`);
});
page.on('pageerror', e => bad.push(`pageerror: ${e.message}`));

await page.goto('/orders');
await page.getByRole('button', { name: '조회' }).click();

expect(bad, bad.join('\n')).toEqual([]);
```

**여기서 정직하게 덧붙일 것.** 이 체크는 favicon 404, 애널리틱스 4xx 같은 무해한 것들도 같이 잡는다. 그래서 allowlist 가 붙게 되고, **allowlist 가 자라기 시작하는 순간 이 체크는 다시 거짓말을 시작한다.** 예외 목록에 패턴 하나가 너무 넓게 들어가면 진짜 500 이 조용히 그 안으로 들어간다. 오라클을 만들었다고 끝이 아니라, 오라클이 여전히 무언가를 거부하는지를 주기적으로 확인해야 한다.

---

## 4. 그럼 자동 재현기의 값은 어디에 있나 — Zeller 가 2002년에 답했다

Zeller 와 Hildebrandt 의 delta debugging 논문이 이 질문에 직접 답한다.[^dd]

케이스 스터디: Mozilla 가 **95번의 사용자 동작** 뒤에 크래시했다. `ddmin` 알고리즘이 이걸 **관련 동작 3개**로 줄였다. 896줄 HTML 은 크래시를 일으키는 **한 줄**로 줄었다. 비용은 **139회의 자동 테스트 실행, 500MHz PC 에서 35분**이었다.

논문에서 내가 이 글의 답이라고 보는 문장은 이거다.

> Several textbooks and guides about debugging are available that tell how to use binary search in order to isolate the problem — **based on the assumption that tests are carried out manually, too. With an automated test, however, we can automate this simplification of test cases.**

이분법을 다시 세우면 이렇게 된다.

**자동 재현기의 값은 버그를 "찾는" 데 있지 않다. 버그 판정을 함수로 만들어서 139번 호출할 수 있게 하는 데 있다.**

delta debugging 이 요구하는 것은 딱 하나, 판정 함수다.

$$
\text{test} : \text{환경} \longrightarrow \{\checkmark,\ \times,\ ?\}
$$

Playwright 의 진짜 역할은 웹 앱에 대해 **이 함수를 구현하는 것**이다. 직접 보기로는 이 함수를 구현할 수 없다 — 내 눈알은 139번 호출되지 않는다.

그래서 순서가 강제된다.

1. **재현되지 않는 것은 자동화할 수 없다.** → 먼저 직접 본다. 가설이 없으면 자동화할 대상 자체가 없다.
2. **자동화되지 않은 것은 최소화할 수 없다.** → 재현되면 즉시 자동화한다. 최소화는 여기서부터 가능해진다.
3. **오라클이 틀리면 최소화는 틀린 답으로 수렴한다.** → §3 의 `goto` 함정이 여기서 치명적이 된다. 500 을 초록으로 판정하는 오라클 위에서 139번을 돌리면, 알고리즘은 아주 자신 있게 쓰레기로 수렴한다.

### Trace 는 "직접 보기"를 박제한 것이다

Playwright 의 Trace Viewer 가 남기는 것은 액션별 DOM 스냅샷(Before / Action / After), 스크린캐스트 필름스트립, 콘솔 로그, 네트워크 로그, 소스 위치다. CI 권장 설정은 `trace: 'on-first-retry'` 다.[^pw-trace]

이건 직접 보기의 *대안*이 아니다. 직접 보기를 **사후에, 다른 사람이, 다른 기계에서** 할 수 있게 만든 것이다. 내가 보는 것과 같은 정보를, 내가 그 자리에 없을 때 꺼낼 수 있게 옮겨 담은 것 — 그게 trace 가 파는 물건이다.

---

## 5. 직접 보기가 유일한 정답인 경우 — 내 사례 셋

자동화가 이기지 못하는 국면이 분명히 있다. 셋 다 내가 겪은 것이고 날짜가 있다.

**(a) 재현 환경 자체가 다를 때.** Next.js standalone 빌드는 `HOSTNAME` 이 파드 이름으로 설정돼 파드 IP 에만 바인딩된다. 파드는 `Ready` 인데 `kubectl port-forward` 는 connection refused 가 났다. 로컬에서 도는 어떤 자동 체크도 여기선 거짓말을 한다 — 유일하게 맞는 계측은 실제 도메인을 직접 치는 것이었다.
→ **자동화가 재현하는 환경이 사고가 난 환경과 다르면, 그 자동화는 다른 질문에 답하고 있다.**

**(b) 증거가 브라우저 바깥에 있을 때.** §2 의 502 건. 브라우저는 502 를 본다. 서버 로그는 200 을 본다. 디코더를 기록하는 곳은 아무 데도 없다. 진실은 호출자의 *예외 타입*을 읽어야 나왔다. 그리고 수정이 먹었는지도 성공/실패로는 판정이 안 됐다 — 버퍼를 늘린 뒤에도 여전히 502 였고, 바뀐 건 **예외의 종류**였다(`DataBufferLimitException` → `TimeoutException 30000ms`).
→ **수정 여부는 성공/실패가 아니라 실패의 종류가 바뀌었는지로 판정하는 게 정확하다.**

**(c) 증거가 애초에 없을 때.** §2 의 Pages 404 건. 관측할 이벤트가 존재하지 않는다.
→ **부재를 잡으려면 요청이 아니라 산출물을 봐야 한다.**

셋을 관통하는 것은 하나다. **직접 보기가 이기는 건 "가설이 아직 없을 때"다.** 자동화는 이미 가진 가설만 시험할 수 있다. 첫 가설은 어딘가에서 와야 하고, 그건 대역폭 높은 비구조적 관찰에서 온다. 사람이 화면을 보는 행위의 값은 정확히 거기에 있지, 반복 실행에 있지 않다.

---

## 6. 결정 규칙

| 증상 | 첫 계측 | 그 다음 | 이 조합이 거짓말하는 방식 |
| --- | --- | --- | --- |
| 500, 재현됨 | **서버 로그·스택트레이스** (브라우저 아님) | 최소 재현 → Playwright 회귀 | 로그 레벨이 낮아 예외가 삼켜졌을 때 |
| 500, 간헐적 | 상관관계 ID + 로그 집계 | 재현 조건을 찾은 뒤 자동화 | 표본이 적으면 임계치의 오탐이 안 보인다 |
| 500 인데 업스트림은 200 | **호출자의 예외 타입** | 한도를 넘는 크기의 회귀 테스트 + 대조군 | 스텁 응답이 작으면 한도를 건드릴 일이 없다 |
| 404, 라우팅 | **브라우저 Network 패널** — 실제 나간 URL·리다이렉트 체인 | 라우트 계약 assert | 프록시·CDN 이 중간에서 다시 쓴 경우 |
| 404, 빌드 산출물 | **빌드 출력 목록** (서빙 계층 아님) | 산출물 존재 여부 assert | 빌드가 `exit 0` 으로 조용히 제외 |
| 404, 권한 위장 | 인증 컨텍스트를 바꿔 재요청 | 두 컨텍스트 비교 assert | 스펙상 합법이라 버그로 오진하기 쉽다 |
| XHR 500, 화면은 멀쩡 | `page.on('response')` | 동일 | allowlist 가 자라면서 다시 거짓말 |
| 브라우저에서만 재현 | `trace: 'on-first-retry'` | trace 를 **사람이** 연다 | trace 가 성공 실행에서만 남게 설정된 경우 |

표의 왼쪽 두 칸이 이 글의 답이다. **첫 계측은 증상이 정한다. 자동화는 그 다음 칸이지 첫 칸이 아니다.**

---

## 7. 바이브 코딩에만 있는 비대칭 하나

여기까지는 사람이 디버깅할 때의 얘기다. 에이전트에게 "고쳐봐" 를 반복시키는 루프에는 항이 하나 더 붙는다.

사람은 오라클이 부실해도 중간에 **"이거 좀 이상한데" 라고 멈춘다.** 루프는 안 멈춘다. 루프는 주어진 판정 함수가 초록을 내는 지점으로 수렴하고, **판정 함수가 틀렸으면 틀린 지점으로 정확하게 수렴한다.** §3 의 `goto` 체크만 쥐여 주면, 에이전트는 500 을 고치는 게 아니라 500 을 유지한 채 초록인 상태를 아주 성실하게 찾아낸다.

그래서 바이브 코딩에서는 **오라클을 먼저 만드는 게 선택이 아니다.** 순서가 뒤집히면 자동화는 디버깅을 돕는 게 아니라 디버깅을 *가린다*.

Lieberman 이 1997년 CACM 특집 서문에 쓴 문장이 아직도 유효하다.[^lieberman]

> Debugging is still, as it was thirty years ago, largely a matter of trial and error.

같은 글의 다음 문장이 더 아프다 — 많은 프로그래머가 선호하는 디버깅 기법으로 **print 문 삽입**을 꼽는 것이 기술 수준에 대한 서글픈 논평이라고 그는 썼다. 2026년의 등가물은 아마 **스크린샷을 찍어 에이전트에게 붙여넣는 것**일 것이다. 30년 뒤에도 trial and error 라는 것 자체는 문제가 아니다. 문제는 **그 trial 을 누가 채점하느냐**다.

---

## 한계

- Playwright 문서는 버전 태그를 고정하지 않고 현재 문서를 기준으로 인용했다. `goto()` 가 HTTP 에러 상태에서 throw 하지 않는다는 계약은 오래된 것이지만, 특정 버전에 고정해 확인한 것은 아니다.
- 내 사례들은 각각 특정 시점의 관측이며 현재 상태가 아니다. 날짜를 붙인 이유가 그것이다.
- **"Playwright 를 도입하면 디버깅 시간이 N% 줄어든다" 같은 정량 주장은 하지 않는다.** 단일 조직·사후 관찰·대조군 없음. Zeller 의 139회 / 35분 / 500MHz 도 2002년 Mozilla 한 사례의 실측치이지 일반 성능 주장이 아니다.
- 이 글은 웹 앱의 HTTP 에러에 한정된다. 데이터 정합성 오류처럼 상태 코드가 200 인 실패에는 표의 첫 칸이 통째로 다르다.

---

## 결론

질문은 "Playwright 냐 직접 보기냐" 였지만, 실제로 답해야 할 질문은 셋이었다.

1. **지금 것이 500 인가 404 인가.** 500 에는 목격자가 있고 그 목격자는 브라우저에 없다. 404 는 목격자가 없는 것이 정상이며, 그래서 브라우저 쪽 증거가 전부인 경우가 많다.
2. **가설이 있는가.** 없으면 직접 본다. 자동화는 없는 가설을 만들어 주지 않는다.
3. **판정 함수가 옳은가.** `page.goto()` 는 404 와 500 에서 던지지 않는다 — 공식 문서에 그렇게 적혀 있다. 오라클을 네트워크 계층으로 내리지 않으면, 자동화는 반복 가능한 거짓말이 된다.

직접 보기는 **가설의 원천**이고, 자동 재현기는 **가설의 시험 장치**다. 전자를 건너뛰면 시험할 게 없고, 후자를 건너뛰면 같은 걸 매번 처음부터 다시 본다.

---

## References

[^kp]: Brian W. Kernighan, P. J. Plauger, *The Elements of Programming Style*, 2nd ed., McGraw-Hill, 1978, ch. 2. ISBN 0-07-034207-5. (인용문은 2판 2장의 문장으로 널리 재인용된다.)

[^karpathy]: Andrej Karpathy, X 게시물, 2025-02-02. 원문 id `1886192184808149383`. "vibe coding" 이라는 표현이 처음 쓰인 글로, 본인이 `"Accept All" always` 와 `throwaway weekend projects` 라는 범위를 함께 적었다. <https://x.com/karpathy/status/1886192184808149383>

[^rfc9110]: R. Fielding, M. Nottingham, J. Reschke (eds.), *HTTP Semantics*, RFC 9110, IETF, June 2022. §15.5 (Client Error 4xx), §15.5.5 (404 Not Found), §15.6 (Server Error 5xx), §15.6.1 (500 Internal Server Error), §15.6.3 (502 Bad Gateway). <https://www.rfc-editor.org/rfc/rfc9110.html>

[^pw-goto]: Playwright 공식 문서, `page.goto()`. <https://playwright.dev/docs/api/class-page#page-goto>

[^pw-network]: Playwright 공식 문서, Network. <https://playwright.dev/docs/network>

[^pw-trace]: Playwright 공식 문서, Trace viewer. <https://playwright.dev/docs/trace-viewer>

[^dd]: Andreas Zeller, Ralf Hildebrandt, "Simplifying and Isolating Failure-Inducing Input", *IEEE Transactions on Software Engineering*, 28(2):183–200, February 2002. doi:[10.1109/32.988498](https://doi.org/10.1109/32.988498)

[^lieberman]: Henry Lieberman, "The Debugging Scandal and What to Do About It" (Introduction to the Special Section), *Communications of the ACM*, 40(4):26–29, April 1997. 저자 페이지에 서문 전문이 공개돼 있다. <https://web.media.mit.edu/~lieber/Lieberary/Softviz/CACM-Debugging/CACM-Debugging-Intro.html>
