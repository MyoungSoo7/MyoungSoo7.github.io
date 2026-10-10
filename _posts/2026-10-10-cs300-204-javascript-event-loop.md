---
layout: post
title: "[CS300 #204] 자바스크립트 이벤트 루프 — 스레드 하나로 동시에 일하는 법"
date: 2026-10-10 21:24:00 +0900
categories: [cs]
tags: [cs300, web, javascript, event-loop, async]
---

컴퓨터공학 300 주제 시리즈의 204번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

자바스크립트는 콜 스택이 하나인 단일 스레드 언어이고, 이벤트 루프가 "태스크 하나 실행 → 마이크로태스크 전부 비우기 → (필요하면) 화면 갱신"을 반복하면서 비동기 작업의 결과를 차례로 실행한다.

## 왜 필요한가

다음 코드의 출력 순서를 바로 말할 수 있는가.

```js
setTimeout(() => console.log("A"), 0);
Promise.resolve().then(() => console.log("B"));
console.log("C");
```

답은 C, B, A 다. 0ms 타이머가 Promise 보다 늦게 실행된다. 이 순서를 설명하지 못하면 다음과 같은 일을 겪는다.

- 상태를 바꾼 직후 값을 읽었는데 아직 반영되지 않아 버그가 난다.
- 큰 배열을 정렬하는 동안 버튼이 눌리지 않고 화면이 멈춘다.
- Node.js 서버에서 무거운 JSON 처리 하나가 모든 요청의 응답을 늦춘다.

이벤트 루프는 브라우저와 Node.js 양쪽에서 "왜 멈췄는가", "왜 이 순서인가"를 설명하는 공통 언어다.

## 핵심 개념

### 구성 요소

```
 ┌───────────── 콜 스택 ─────────────┐
 │  지금 실행 중인 함수들 (하나뿐)      │
 └──────────────────────────────────┘
          ▲  비면 다음 일을 꺼낸다
          │
 ┌────────┴────────┐   ┌──────────────────────┐
 │ 마이크로태스크 큐 │   │ 태스크 큐(들)           │
 │ Promise then     │   │ setTimeout, 이벤트,    │
 │ queueMicrotask   │   │ 네트워크 응답, MessageChannel │
 └──────────────────┘   └──────────────────────┘
          ▲                     ▲
          └──── Web API / libuv 가 완료되면 넣는다 ────┘
```

타이머를 세거나, 네트워크를 기다리거나, 파일을 읽는 일은 자바스크립트 스레드가 하지 않는다. 브라우저(Web API)나 Node.js 의 libuv 가 대신 기다렸다가, 끝나면 콜백을 큐에 넣는다. 자바스크립트 스레드는 큐에서 꺼내 실행만 한다.

### 한 바퀴의 순서

HTML 표준이 정의한 이벤트 루프의 처리 모델을 단순화하면 다음과 같다.

1. 태스크 큐에서 가장 오래된 태스크 **하나**를 꺼내 실행한다.
2. 마이크로태스크 체크포인트: 마이크로태스크 큐가 **빌 때까지** 전부 실행한다. 실행 중에 새로 들어온 마이크로태스크도 이번에 처리한다.
3. 렌더링할 때가 되었으면 화면을 갱신한다. 이때 `requestAnimationFrame` 콜백, 스타일 계산, 레이아웃, 페인트가 일어난다.
4. 1로 돌아간다.

스크립트 전체(`<script>` 실행)도 하나의 태스크다. 그래서 앞의 예에서는 동기 코드 C 가 먼저 끝나고, 마이크로태스크 B 가 비워진 뒤, 다음 태스크인 타이머 A 가 실행된다.

| 종류 | 예 | 처리 방식 |
|---|---|---|
| 태스크(매크로태스크) | `setTimeout`, `setInterval`, 클릭 이벤트, `MessageChannel` | 한 바퀴에 하나 |
| 마이크로태스크 | `Promise.then/catch/finally`, `await` 이후, `queueMicrotask`, `MutationObserver` | 한 번에 전부 |
| 렌더링 단계 | `requestAnimationFrame` | 화면 갱신 직전 |

"매크로태스크"는 표준 용어가 아니고 표준은 그냥 태스크(task)라고 부른다. 개발자들이 마이크로태스크와 구분하려고 쓰는 말이다.

### `await` 는 어디서 멈추나

```js
async function f() {
  console.log("1");
  await null;          // 여기서 함수가 양보한다
  console.log("3");    // 나머지는 마이크로태스크로 이어진다
}
f();
console.log("2");
```

`await` 앞까지는 호출한 쪽과 같이 동기로 실행된다. `await` 를 만나면 함수는 일단 반환하고, 나머지 부분은 기다리던 Promise 가 처리된 뒤 마이크로태스크로 재개된다. 그래서 1, 2, 3 순서가 된다.

### 메인 스레드를 막으면 모든 것이 멈춘다

콜 스택이 하나이므로 오래 걸리는 동기 코드는 그 시간 동안 다른 모든 것을 막는다. 클릭 처리, 타이머, 화면 갱신이 다 밀린다. `setTimeout(fn, 10)` 의 10ms 는 "10ms 뒤에 반드시 실행"이 아니라 "10ms 이후 언젠가 큐에 넣음"이다.

마이크로태스크도 조심해야 한다. 마이크로태스크 안에서 계속 새 마이크로태스크를 넣으면 큐가 영원히 비지 않아, 태스크도 렌더링도 영영 돌아오지 않는다.

```js
function forever() { queueMicrotask(forever); }  // 화면이 얼어붙는다
```

긴 작업을 처리하는 방법은 세 가지다.

- **쪼개기**: 작업을 조각내고 조각 사이에 `setTimeout` 등으로 태스크를 양보해 렌더링과 입력 처리가 끼어들게 한다.
- **다른 스레드로**: 브라우저는 Web Worker, Node.js 는 `worker_threads` 로 계산을 옮긴다. 메시지로만 주고받는다.
- **알고리즘 개선**: 애초에 O(n²) 를 O(n log n) 으로 바꾸는 것이 가장 확실하다.

### Node.js 의 이벤트 루프

Node.js 도 같은 원리지만 libuv 가 정한 단계(phase)가 있다.

```
 ┌─▶ timers          setTimeout, setInterval 만료 콜백
 │   pending callbacks  일부 시스템 오류 콜백
 │   poll            I/O 이벤트 대기·처리
 │   check           setImmediate
 └── close callbacks  socket.on('close')
```

각 콜백 사이에는 `process.nextTick` 큐와 Promise 마이크로태스크 큐가 비워진다. `process.nextTick` 은 Promise 보다도 먼저 실행된다. 이름과 달리 "다음 틱"이 아니라 "지금 작업 바로 다음"이다. Node.js 공식 문서도 대부분의 경우 `setImmediate` 를 권한다.

## 직접 해 보기

Node.js 로 다음 파일을 실행한다(`node loop.js`).

```js
console.log("1 동기 시작");
setTimeout(() => console.log("5 태스크: setTimeout 0"), 0);
Promise.resolve()
  .then(() => console.log("3 마이크로태스크: then #1"))
  .then(() => console.log("4 마이크로태스크: then #2"));
queueMicrotask(() => console.log("3' 마이크로태스크: queueMicrotask"));
console.log("2 동기 끝");

// 메인 스레드를 막으면 타이머도 늦는다
const t0 = Date.now();
setTimeout(() => console.log(`6 10ms 타이머가 실제로 ${Date.now() - t0}ms 뒤 실행`), 10);
const end = Date.now() + 200;
while (Date.now() < end) {}   // 200ms 동안 바쁜 대기
```

Node.js 22 에서 실행한 결과:

```
1 동기 시작
2 동기 끝
3 마이크로태스크: then #1
3' 마이크로태스크: queueMicrotask
4 마이크로태스크: then #2
5 태스크: setTimeout 0
6 10ms 타이머가 실제로 201ms 뒤 실행
```

볼 점이 세 가지다.

1. 동기 코드(1, 2)가 모두 끝나야 비동기 콜백이 시작된다.
2. `then #2` 는 `then #1` 이 끝나야 큐에 들어가므로, 그 사이에 먼저 들어와 있던 `queueMicrotask` 가 끼어든다. 마이크로태스크 큐는 들어온 순서(FIFO)다.
3. 10ms 타이머는 바쁜 대기 200ms 가 끝난 뒤에야 실행됐다. 마지막 숫자는 기기마다 조금씩 다르지만 200ms 보다 작아지지는 않는다.

같은 코드를 브라우저 콘솔에 붙여 넣어도 1~5 의 순서는 같다.

## 현업에서는

- **UI 가 얼어붙는 신고**: 개발자 도구 Performance 패널에서 50ms 를 넘는 긴 작업(Long Task)을 찾는다. 대개 큰 목록 렌더링, 동기 JSON 파싱, 정규식 폭주가 원인이다. 이것은 웹 성능 지표 INP 와 직결된다(213번 주제).
- **Node.js API 서버의 꼬리 지연**: 평균 응답은 빠른데 가끔 수백 ms 가 튀면, 이벤트 루프 지연(event loop lag)을 메트릭으로 수집해 본다. 동기 암호화, 큰 파일 동기 읽기(`readFileSync`), 큰 배열 정렬이 루프를 막고 있는 경우가 많다.
- **쿠버네티스에서의 함정**: 홈랩 k3s 클러스터에 Node.js 서비스를 올리고 CPU limit 을 낮게 잡으면, 이벤트 루프가 스로틀링에 걸려 헬스 체크 응답까지 늦어질 수 있다. 그러면 liveness probe 실패로 재시작이 반복된다. 무거운 계산은 워커로 빼고, probe 타임아웃은 실제 지연 분포를 보고 정한다.
- **테스트의 비동기 대기**: "상태를 바꿨는데 DOM 이 아직 안 바뀌었다"는 테스트 실패는 대개 마이크로태스크나 다음 프레임을 기다리지 않아서다. 테스트 도구의 `await` 기반 대기 함수를 쓴다.

## 확인 문제

1. `setTimeout(f, 0)` 과 `Promise.resolve().then(f)` 중 무엇이 먼저 실행되는가. 이유는?
2. 마이크로태스크 안에서 마이크로태스크를 계속 등록하면 어떤 일이 생기는가.
3. `async` 함수에서 `await` 이전 코드와 이후 코드는 각각 언제 실행되는가.
4. 계산이 오래 걸리는 함수 때문에 버튼이 눌리지 않는다. 해결 방법 두 가지를 들라.
5. Node.js 에서 `process.nextTick` 과 `Promise.then` 콜백 중 먼저 실행되는 것은?

### 풀이

1. Promise 쪽이 먼저다. 현재 태스크가 끝나면 마이크로태스크 큐를 모두 비운 뒤에야 다음 태스크(타이머)를 꺼내기 때문이다.
2. 마이크로태스크 큐가 비지 않아 다음 태스크와 렌더링이 영원히 실행되지 않는다. 화면이 멈춘다.
3. `await` 이전은 호출 시점에 동기로, 이후는 기다린 Promise 가 처리된 뒤 마이크로태스크로 실행된다.
4. 작업을 조각내 태스크 사이에 양보하기, Web Worker 로 옮기기. 알고리즘 자체를 개선하는 것도 답이다.
5. `process.nextTick` 이 먼저다.

## 더 읽을거리 (References)

- WHATWG, *HTML Living Standard — Event loops*: <https://html.spec.whatwg.org/multipage/webappapis.html#event-loops>
- MDN, *JavaScript execution model*: <https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Execution_model>
- MDN, *Using microtasks in JavaScript with queueMicrotask()*: <https://developer.mozilla.org/en-US/docs/Web/API/HTML_DOM_API/Microtask_guide>
- Node.js, *The Node.js Event Loop*: <https://nodejs.org/en/learn/asynchronous-work/event-loop-timers-and-nexttick>
