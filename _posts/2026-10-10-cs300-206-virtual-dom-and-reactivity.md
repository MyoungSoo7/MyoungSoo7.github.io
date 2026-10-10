---
layout: post
title: "[CS300 #206] 프론트엔드 프레임워크의 원리 — 가상 DOM 과 반응성"
date: 2026-10-10 21:26:00 +0900
categories: [cs]
tags: [cs300, web, react, vue, virtual-dom, reactivity]
---

컴퓨터공학 300 주제 시리즈의 206번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

프론트엔드 프레임워크는 "상태가 바뀌면 화면을 다시 그린다"는 선언적 모델을 제공하고, 실제 DOM 변경을 최소화하기 위해 가상 DOM 비교(React 방식)나 의존성 추적 반응성(Vue·Svelte·Solid 방식)을 쓴다.

## 왜 필요한가

DOM API 만으로 화면을 만들면 "무엇을 어떻게 바꿀지"를 개발자가 직접 적어야 한다. 장바구니 수량이 바뀌면 수량 칸, 합계, 배지 숫자, 결제 버튼 상태를 하나하나 찾아 고친다. 상태가 열 개, 화면 조각이 스무 개가 되면 어딘가 하나를 빠뜨리게 된다. 화면과 데이터가 어긋나는 버그다.

프레임워크는 질문을 바꾼다. "어떻게 바꿀까" 대신 "이 상태일 때 화면은 이렇게 생겼다"만 적는다.

```
UI = f(state)
```

상태가 바뀌면 프레임워크가 f 를 다시 계산하고, 이전 결과와 다른 부분만 실제 DOM 에 반영한다. 이 "다른 부분만 찾는" 방법이 프레임워크마다 다르고, 그 차이가 성능 특성과 사용법의 차이를 만든다.

## 핵심 개념

### 왜 DOM 을 그냥 통째로 다시 만들지 않나

`innerHTML` 로 매번 전부 갈아엎으면 코드는 간단하다. 하지만 입력 중이던 텍스트, 커서 위치, 포커스, 스크롤 위치, 재생 중인 동영상 상태가 다 날아간다. 그리고 노드 생성과 레이아웃 비용이 크다(201번 주제). 그래서 바뀐 곳만 고치는 것이 필요하다.

### 방식 1: 가상 DOM 과 재조정(reconciliation)

React 는 컴포넌트 함수가 돌려준 결과를 평범한 자바스크립트 객체 트리(가상 DOM)로 만든다. 상태가 바뀌면 다시 렌더링해 새 트리를 만들고, 이전 트리와 비교해서 차이만 실제 DOM 에 적용한다.

```
상태 변경 → 컴포넌트 재실행(render) → 새 가상 트리
                                      │ 비교(diff)
                         이전 가상 트리 ┘
                                      ▼
                           변경 목록 → 실제 DOM 반영(commit)
```

두 트리를 최적으로 비교하는 일반 알고리즘은 비용이 크다. React 문서는 일반 해법이 O(n³) 수준이라고 설명하고, 대신 두 가지 가정으로 O(n) 휴리스틱을 쓴다.

1. 타입이 다른 요소(`<div>` → `<span>`, 컴포넌트 A → B)는 하위 트리 전체가 다르다고 보고 새로 만든다.
2. 목록의 자식들은 개발자가 준 `key` 로 같은 항목인지 판별한다.

`key` 를 배열 인덱스로 주면 맨 앞에 항목을 끼워 넣을 때 모든 항목의 키가 한 칸씩 밀린다. React 는 내용이 전부 바뀐 것으로 보고, 각 항목이 들고 있던 입력값이나 내부 상태가 엉뚱한 항목으로 옮겨 간다. 키는 데이터의 고유 ID 로 준다.

React 공식 문서는 이 과정을 렌더(render) 단계와 커밋(commit) 단계로 나눠 설명한다. 렌더는 컴포넌트를 호출해 무엇을 그릴지 계산하는 단계이고, 커밋은 실제 DOM 을 고치는 단계다. 렌더가 일어나도 결과가 같으면 DOM 은 건드리지 않는다.

### 방식 2: 의존성 추적 반응성

Vue, Svelte, Solid 같은 프레임워크는 "어떤 상태를 어떤 화면 조각이 읽었는가"를 기록해 두었다가, 그 상태가 바뀌면 그 조각만 다시 실행한다.

```
effect 실행 중 price.get() 호출 → "이 effect 는 price 에 의존" 기록
price.set(1200)                → price 에 의존하는 effect 만 재실행
```

Vue 3 는 자바스크립트 `Proxy` 로 객체의 읽기(get)와 쓰기(set)를 가로채 이 기록을 자동으로 한다. 공식 문서는 이를 track(읽을 때 구독 등록)과 trigger(쓸 때 구독자 실행)로 설명한다. Vue 는 이렇게 컴포넌트 단위로 다시 렌더링할 대상을 정한 뒤, 컴포넌트 안에서는 가상 DOM 비교도 함께 쓴다. 컴파일러가 템플릿의 정적인 부분을 미리 표시해 비교할 양을 줄인다.

Svelte 는 컴파일러가 상태와 DOM 갱신 코드를 빌드 시점에 연결한다. Svelte 5 는 `$state` 같은 룬(rune)으로 반응형 상태를 선언한다.

### 두 방식 비교

| 항목 | 가상 DOM 비교 | 세밀한 반응성 |
|---|---|---|
| 변경 감지 | 다시 렌더링해서 비교 | 읽기 시점에 구독, 쓰기 시점에 통지 |
| 다시 실행되는 범위 | 상태를 가진 컴포넌트와 그 하위 | 그 상태를 읽은 곳만 |
| 개발자가 신경 쓸 것 | 불필요한 재렌더링(메모이제이션) | 반응성이 끊기는 패턴(구조 분해 등) |
| 상태 표현 | 불변 값 + setState | 반응형 객체·시그널 |

어느 쪽이 무조건 빠르지는 않다. 화면 대부분이 자주 바뀌면 비교 비용이 비슷해지고, 일부만 자주 바뀌면 세밀한 반응성이 유리한 경향이 있다. 실제 성능은 앱 구조에 따라 다르므로 측정해야 한다.

### 공통 원칙: 상태는 한 방향으로 흐른다

두 방식 모두 "상태 → 화면" 한 방향 흐름을 기본으로 한다. 화면에서 일어난 이벤트는 상태를 바꾸는 함수를 호출하고, 바뀐 상태가 다시 화면을 만든다. DOM 을 직접 고쳐서 화면과 상태를 따로 놀게 하면 프레임워크가 다음 렌더링 때 덮어쓴다.

## 직접 해 보기

두 방식의 핵심을 각각 20줄 안팎의 자바스크립트로 만든다. `node vdom.js` 로 실행한다.

```js
// 1) 가상 DOM: 키 기반 목록 비교
function diffList(oldList, newList) {
  const ops = [];
  const oldByKey = new Map(oldList.map((n) => [n.key, n]));
  const newKeys = new Set(newList.map((n) => n.key));
  for (const n of oldList) if (!newKeys.has(n.key)) ops.push(`REMOVE ${n.key}`);
  newList.forEach((n, i) => {
    const prev = oldByKey.get(n.key);
    if (!prev) ops.push(`INSERT ${n.key} at ${i}`);
    else if (prev.text !== n.text) ops.push(`UPDATE ${n.key} text="${n.text}"`);
  });
  return ops;
}
const before = [ { key: "a", text: "사과" }, { key: "b", text: "배" }, { key: "c", text: "감" } ];
const after  = [ { key: "b", text: "배" }, { key: "c", text: "단감" }, { key: "d", text: "귤" } ];
console.log("가상 DOM 비교 결과:", diffList(before, after));

// 2) 반응성: 읽을 때 의존성 기록, 쓸 때 다시 실행
let activeEffect = null;
function signal(value) {
  const subs = new Set();
  return {
    get() { if (activeEffect) subs.add(activeEffect); return value; },
    set(v) { value = v; for (const fn of [...subs]) fn(); },
  };
}
function effect(fn) {
  const run = () => { activeEffect = run; fn(); activeEffect = null; };
  run();
}
const price = signal(1000), qty = signal(2);
effect(() => console.log(`합계 표시 갱신: ${price.get() * qty.get()}원`));
qty.set(3);
price.set(1200);
```

Node.js 22 에서 실행한 결과:

```
가상 DOM 비교 결과: [ 'REMOVE a', 'UPDATE c text="단감"', 'INSERT d at 2' ]
합계 표시 갱신: 2000원
합계 표시 갱신: 3000원
합계 표시 갱신: 3600원
```

첫 번째는 키 덕분에 "b 는 그대로, c 는 글자만 변경, a 삭제, d 추가"라는 최소 변경을 찾는다. 키 없이 인덱스로 비교했다면 세 칸 모두 글자가 바뀐 것으로 나온다. 두 번째는 `effect` 가 처음 실행될 때 `price` 와 `qty` 를 읽었으므로 둘 중 무엇이 바뀌어도 합계가 다시 계산된다. 실제 프레임워크는 여기에 일괄 처리(같은 틱의 여러 변경을 한 번에 반영), 의존성 정리, 중첩 effect 처리를 더한 것이다.

## 현업에서는

- **"왜 이 컴포넌트가 계속 다시 그려지지?"**: React 개발자 도구의 Profiler 로 렌더링 원인을 본다. 부모가 매 렌더마다 새 객체·새 함수를 props 로 넘기는 것이 흔한 원인이다. `memo`, `useMemo`, `useCallback` 은 측정한 뒤에 필요한 곳에만 쓴다.
- **목록 key 버그**: 체크박스 목록에서 항목을 삭제했더니 다른 항목의 체크 상태가 바뀌었다면 인덱스 key 를 의심한다.
- **반응성 끊김**: Vue 에서 반응형 객체를 구조 분해하면 일반 값이 되어 더 이상 추적되지 않는다. 공식 문서가 `toRefs` 등을 안내하는 이유다.
- **프레임워크 선택**: 홈랩 대시보드처럼 작은 관리 화면이면 어느 프레임워크든 충분하다. 선택 기준은 성능 미세 차이보다 팀이 익숙한가, 생태계와 문서가 탄탄한가가 더 크다.

## 확인 문제

1. `UI = f(state)` 모델이 직접 DOM 을 조작하는 방식보다 버그를 줄이는 이유는?
2. React 의 재조정이 O(n) 이 될 수 있게 해 주는 두 가지 가정은?
3. 목록 key 로 배열 인덱스를 쓰면 어떤 문제가 생기는가.
4. 의존성 추적 반응성에서 "구독"은 언제 일어나고 "통지"는 언제 일어나는가.
5. 렌더 단계와 커밋 단계의 차이는?

### 풀이

1. 화면을 상태로부터 매번 계산하므로, 상태와 화면이 어긋나는 "갱신 누락"이 구조적으로 줄어든다.
2. 타입이 다른 요소는 하위 트리가 다르다고 본다. 목록 자식은 `key` 로 동일성을 판별한다.
3. 중간 삽입·삭제 시 키가 밀려 다른 항목으로 인식된다. 불필요한 DOM 변경이 생기고, 항목별 내부 상태(입력값 등)가 엉뚱한 항목에 붙는다.
4. effect·렌더 함수가 실행되며 상태를 **읽을 때** 구독하고, 상태를 **쓸 때** 구독자에게 통지해 다시 실행한다.
5. 렌더는 컴포넌트를 호출해 무엇을 그릴지 계산하는 단계, 커밋은 그 결과의 차이를 실제 DOM 에 반영하는 단계다.

## 더 읽을거리 (References)

- React, *Render and Commit*: <https://react.dev/learn/render-and-commit>
- React (legacy docs), *Reconciliation*: <https://legacy.reactjs.org/docs/reconciliation.html>
- Vue.js, *Reactivity in Depth*: <https://vuejs.org/guide/extras/reactivity-in-depth.html>
- Vue.js, *Rendering Mechanism*: <https://vuejs.org/guide/extras/rendering-mechanism.html>
