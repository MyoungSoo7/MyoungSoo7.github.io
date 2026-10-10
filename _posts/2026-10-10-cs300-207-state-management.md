---
layout: post
title: "[CS300 #207] 상태 관리 — 무엇을, 어디에, 누가 바꾸는가"
date: 2026-10-10 21:27:00 +0900
categories: [cs]
tags: [cs300, web, state-management, redux, react]
---

컴퓨터공학 300 주제 시리즈의 207번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

상태 관리는 화면을 만드는 데이터를 종류별로 나누고(지역·공유·서버·URL 상태), 각각을 가장 가까운 곳에 두되, 바꾸는 경로를 하나로 정해 예측 가능하게 만드는 일이다.

## 왜 필요한가

작은 앱에서는 상태가 문제 되지 않는다. 컴포넌트 하나가 자기 값을 들고 있으면 끝이다. 앱이 커지면 다음 증상이 나타난다.

- 같은 데이터(로그인 사용자, 장바구니)가 여러 곳에 복사되어 서로 다른 값을 보여 준다.
- 값 하나를 전달하려고 중간 컴포넌트 다섯 개에 props 를 계속 넘긴다(prop drilling).
- 누가 언제 이 값을 바꿨는지 추적할 수 없어 버그를 재현하지 못한다.
- 서버에서 받은 목록이 오래된 값인지, 지금 다시 받아야 하는지 판단하는 코드가 여기저기 흩어진다.

전역 저장소 라이브러리 하나를 도입한다고 해결되지 않는다. 먼저 상태의 **종류**를 구분해야 한다.

## 핵심 개념

### 상태의 네 종류

| 종류 | 예 | 주인 | 알맞은 위치 |
|---|---|---|---|
| 지역 UI 상태 | 드롭다운 열림, 입력 중인 글자 | 컴포넌트 하나 | 컴포넌트 내부 (`useState`, `ref`) |
| 공유 클라이언트 상태 | 로그인 사용자, 테마, 장바구니 초안 | 앱의 여러 곳 | 공통 조상, Context, 전역 스토어 |
| 서버 상태 | 상품 목록, 주문 내역 | 서버 | 서버 캐시 라이브러리 |
| URL 상태 | 검색어, 페이지 번호, 필터 | 주소창 | 쿼리 문자열, 경로 |

이 구분이 중요한 이유는 성격이 다르기 때문이다. 서버 상태는 내가 주인이 아니다. 다른 사용자가 바꿀 수 있고, 받아 온 순간부터 낡기 시작하며, 받아 오는 동안 로딩·오류 상태가 있다. TanStack Query 문서는 서버 상태의 특징으로 원격에 있고, 비동기로 가져와야 하며, 소유권이 공유되고, 모르는 사이에 낡을 수 있다는 점을 든다. 이런 데이터를 일반 전역 변수처럼 다루면 캐시 무효화, 중복 요청 제거, 재시도를 손으로 다 짜야 한다.

URL 상태를 따로 두는 이유는 공유와 새로 고침이다. 검색 필터를 메모리에만 두면 새로 고침하거나 링크를 동료에게 보냈을 때 사라진다.

### 원칙 1: 가능한 한 가까이 둔다

React 문서는 두 컴포넌트가 같은 데이터를 써야 하면 그 상태를 **가장 가까운 공통 부모로 끌어올리라**(lifting state up)고 설명한다. 반대로 한 곳에서만 쓰면 그 컴포넌트 안에 둔다. 모든 것을 전역에 두면 어떤 변경이 어디에 영향을 주는지 알기 어려워지고, 관계없는 화면까지 다시 렌더링된다.

### 원칙 2: 원본은 하나, 나머지는 계산

장바구니 항목과 "총 개수"를 둘 다 상태로 저장하면, 항목을 바꾸고 개수를 갱신하지 않는 순간 둘이 어긋난다. 계산할 수 있는 값은 저장하지 말고 원본에서 파생한다.

```
원본 상태:  items = { apple: 2, pear: 1 }
파생 값:    totalCount = 3   ← 저장하지 않고 매번 계산 (필요하면 메모이제이션)
```

### 원칙 3: 바꾸는 경로를 하나로

Redux 문서는 세 가지 원칙을 내세운다.

1. **단일 진실 공급원**: 앱의 전역 상태는 하나의 스토어 객체 트리에 있다.
2. **상태는 읽기 전용**: 상태를 바꾸는 유일한 방법은 "무슨 일이 일어났는지"를 담은 액션을 보내는 것이다.
3. **변경은 순수 함수로**: 리듀서 `(이전 상태, 액션) → 새 상태` 가 변경을 기술한다.

```
 UI ──dispatch(action)──▶ reducer(state, action) ──▶ 새 state ──▶ UI 다시 그림
 ▲                                                               │
 └───────────────────────────── subscribe ────────────────────────┘
```

리듀서가 이전 객체를 고치지 않고 새 객체를 돌려주면(불변성) 두 가지 이득이 있다. 참조 비교 한 번으로 "바뀌었나"를 알 수 있고, 이전 상태들이 그대로 남아 있어 시간 여행 디버깅과 되돌리기가 쉬워진다.

### 도구 고르기

| 필요 | 선택지 예 |
|---|---|
| 지역 상태 | 프레임워크 기본 기능 (`useState`, `useReducer`, Vue `ref`) |
| 깊은 트리에 값 전달 | React Context, Vue `provide/inject` |
| 큰 공유 상태, 변경 이력 추적 | Redux Toolkit, Pinia, Zustand 등 |
| 서버 상태 | TanStack Query, SWR 등 |
| URL 상태 | 라우터의 쿼리 파라미터 |

Context 는 "전달" 도구이지 최적화된 저장소가 아니다. Context 값이 바뀌면 그 값을 쓰는 하위 컴포넌트가 다시 렌더링되므로, 자주 바뀌는 큰 객체를 통째로 넣으면 불필요한 렌더링이 늘어난다.

## 직접 해 보기

Redux 의 핵심을 30줄로 만든다. 스토어, 순수 리듀서, 구독, 파생 값이 다 들어 있다. `node store.js` 로 실행한다.

```js
function createStore(reducer, initial) {
  let state = initial;
  const listeners = new Set();
  return {
    getState: () => state,
    dispatch(action) {
      const prev = state;
      state = reducer(state, action);
      if (state !== prev) listeners.forEach((l) => l(state, action));
    },
    subscribe(l) { listeners.add(l); return () => listeners.delete(l); },
  };
}

function cart(state, action) {
  switch (action.type) {
    case "add": {
      const qty = (state.items[action.id] ?? 0) + 1;
      return { ...state, items: { ...state.items, [action.id]: qty } };
    }
    case "remove": {
      const { [action.id]: _, ...rest } = state.items;
      return { ...state, items: rest };
    }
    default:
      return state;               // 모르는 액션이면 같은 참조를 돌려준다
  }
}

const totalCount = (s) => Object.values(s.items).reduce((a, b) => a + b, 0);

const store = createStore(cart, { items: {} });
const history = [];
store.subscribe((s, a) => {
  history.push(s);
  console.log(`${a.type.padEnd(6)} ${JSON.stringify(s.items)}  배지=${totalCount(s)}`);
});
store.dispatch({ type: "add", id: "apple" });
store.dispatch({ type: "add", id: "apple" });
store.dispatch({ type: "add", id: "pear" });
store.dispatch({ type: "remove", id: "apple" });
store.dispatch({ type: "noop" });
console.log("기록된 상태 수:", history.length, "/ 첫 상태 보존:", JSON.stringify(history[0].items));
```

Node.js 22 실행 결과:

```
add    {"apple":1}  배지=1
add    {"apple":2}  배지=2
add    {"apple":2,"pear":1}  배지=3
remove {"pear":1}  배지=1
기록된 상태 수: 4 / 첫 상태 보존: {"apple":1}
```

`noop` 액션은 같은 참조를 돌려받으므로 구독자가 호출되지 않는다. 그리고 리듀서가 매번 새 객체를 만들었기 때문에 `history[0]` 이 나중 변경에 오염되지 않고 처음 값을 그대로 갖고 있다. 리듀서 안에서 `state.items[action.id]++` 처럼 원본을 고쳤다면 기록이 전부 같은 객체를 가리키게 되고, 참조 비교로는 변경을 감지하지 못한다. 직접 바꿔서 확인해 보면 차이가 바로 보인다.

## 현업에서는

- **"전역 스토어에 다 넣자"의 결말**: 서버 응답, 폼 입력, 모달 열림까지 전역에 넣은 프로젝트는 액션 이름이 수백 개가 되고, 화면 하나 고치는 데 파일 네 개를 건드린다. 서버 상태를 캐시 라이브러리로 옮기기만 해도 전역 스토어가 크게 줄어드는 경우가 많다.
- **낡은 데이터 문제**: "저장했는데 목록에 안 보여요"는 대개 쓰기 후 관련 목록 캐시를 무효화하지 않아서다. 서버 상태 라이브러리는 이것을 쿼리 키 단위 무효화로 다룬다.
- **URL 이 진실 공급원**: 관리 화면의 필터·정렬·페이지는 URL 에 두면 북마크, 공유, 뒤로 가기가 다 자연스럽게 동작한다. 홈랩의 로그 검색 화면처럼 "그 검색 결과 링크 좀 보내 줘"가 잦은 도구에서 특히 유용하다.
- **디버깅**: 상태 변경이 액션으로만 일어나면 버그 신고에 "액션 기록"을 첨부받아 그대로 재생할 수 있다.

## 확인 문제

1. 상태를 네 종류로 나누고 각각의 예를 하나씩 들라.
2. 장바구니 "총 개수"를 별도 상태로 저장하면 어떤 위험이 있는가.
3. 리듀서가 이전 상태를 직접 수정하면 어떤 문제가 생기는가.
4. 서버 상태를 일반 전역 상태처럼 다루기 어려운 이유 두 가지는?
5. 검색 필터를 URL 쿼리에 두는 장점은?

### 풀이

1. 지역 UI(드롭다운 열림), 공유 클라이언트(로그인 사용자), 서버(상품 목록), URL(검색어·페이지).
2. 항목과 개수를 따로 갱신해야 해서 하나를 빠뜨리면 둘이 어긋난다. 파생 값으로 계산해야 한다.
3. 참조가 그대로라 변경 감지(참조 비교)가 실패하고, 이전 상태 기록이 함께 오염되어 되돌리기·시간 여행 디버깅이 불가능해진다.
4. 주인이 서버라 모르는 사이 낡을 수 있고, 비동기라 로딩·오류·재시도·중복 요청 제거·캐시 무효화가 필요하다.
5. 새로 고침해도 유지되고, 링크로 공유·북마크할 수 있으며, 뒤로 가기가 자연스럽게 동작한다.

## 더 읽을거리 (References)

- React, *Managing State*: <https://react.dev/learn/managing-state>
- React, *Sharing State Between Components*: <https://react.dev/learn/sharing-state-between-components>
- Redux, *Three Principles*: <https://redux.js.org/understanding/thinking-in-redux/three-principles>
- TanStack Query, *Overview*: <https://tanstack.com/query/latest/docs/framework/react/overview>
