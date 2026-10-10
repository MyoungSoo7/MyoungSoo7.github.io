---
layout: post
title: "[CS300 #203] CSS 레이아웃 — Flexbox 와 Grid, 남는 공간을 나누는 규칙"
date: 2026-10-10 21:23:00 +0900
categories: [cs]
tags: [cs300, web, css, flexbox, grid]
---

컴퓨터공학 300 주제 시리즈의 203번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

Flexbox 는 한 방향(행 또는 열)으로 늘어선 항목들 사이에 남는 공간을 나누는 1차원 레이아웃이고, Grid 는 행과 열을 동시에 정의해 항목을 칸에 배치하는 2차원 레이아웃이다.

## 왜 필요한가

예전 CSS 에는 "레이아웃" 전용 도구가 없었다. 표(`<table>`)로 화면을 짜거나, 원래 글 사이에 그림을 띄우려고 만든 `float` 를 억지로 써서 단을 나눴다. 세로 가운데 정렬 하나에도 요령이 필요했고, 같은 높이의 단을 만들려면 꼼수가 들었다.

Flexbox 와 Grid 는 레이아웃을 위해 처음부터 설계된 명세다. 이 둘을 이해하면 다음을 몇 줄로 해결한다.

- 가운데 정렬, 양 끝 정렬, 균등 간격
- 화면 너비에 따라 자동으로 줄 바꿈되는 카드 목록
- 머리말·사이드바·본문·꼬리말로 나뉜 페이지 골격

핵심은 "남는 공간을 누가, 얼마만큼 가져가는가"라는 규칙이다. 이 규칙을 계산할 수 있으면 화면이 왜 그렇게 나왔는지 설명할 수 있다.

## 핵심 개념

### 공통 용어

```
display: flex 또는 grid 를 준 요소 = 컨테이너
그 직속 자식                        = 항목(item)

Flexbox
  main axis (주축)  ───────────────▶   flex-direction: row 일 때 가로
  cross axis (교차축) │                 그와 수직
                    ▼
```

정렬 속성 이름에는 규칙이 있다. `justify-*` 는 주축(Grid 에서는 인라인 축, 보통 가로), `align-*` 는 교차축(Grid 에서는 블록 축, 보통 세로)이다. `*-content` 는 줄·트랙 묶음 전체를, `*-items` 는 각 항목을, `*-self` 는 항목 하나를 정렬한다.

### Flexbox: 기준 크기 + 남는 공간 분배

각 항목은 `flex: <grow> <shrink> <basis>` 세 값을 가진다.

| 속성 | 뜻 | 기본값 |
|---|---|---|
| `flex-basis` | 분배 전 기준 크기 | `auto` (내용·width 기반) |
| `flex-grow` | 남는 공간을 받을 비율 | 0 |
| `flex-shrink` | 모자란 공간을 양보할 비율 | 1 |

알고리즘을 아주 줄이면 이렇다.

1. 각 항목의 기준 크기(basis)를 정하고 합한다.
2. 컨테이너 크기에서 합을 빼 남는 공간을 구한다.
3. 남으면 `flex-grow` 비율로 나눠 준다.
4. 모자라면 `flex-shrink × basis` 비율로 줄인다. 큰 항목이 더 많이 줄어든다.
5. `min-width` 같은 제약에 걸린 항목은 고정하고 나머지로 다시 계산한다.

자주 쓰는 축약은 다음과 같다.

```css
.item { flex: 1; }        /* 1 1 0    : 기준 0 에서 출발해 균등 분배 */
.item { flex: auto; }     /* 1 1 auto: 내용 크기에서 출발해 남는 만큼 분배 */
.item { flex: none; }     /* 0 0 auto: 늘지도 줄지도 않음 */
```

`flex: 1` 은 기준이 0 이므로 내용과 상관없이 같은 너비가 되고, `flex: auto` 는 내용이 긴 항목이 더 넓어진다. 이 차이를 모르면 "왜 칸 너비가 다르지?"에서 오래 헤맨다.

자주 걸리는 함정이 하나 있다. Flex 항목의 `min-width` 기본값은 `auto` 라서, 긴 단어나 넓은 표가 있으면 그 내용보다 작게 줄어들지 않는다. 말줄임표(`text-overflow: ellipsis`)가 안 먹는다면 항목에 `min-width: 0` 을 준다.

### Grid: 트랙을 정의하고 칸에 놓는다

Grid 는 먼저 열과 행의 트랙 크기를 정한다.

```css
.page {
  display: grid;
  grid-template-columns: 200px 1fr 2fr;
  gap: 20px;
}
```

`fr` 은 "고정 크기와 간격을 뺀 나머지 공간의 몫"이다. 위 예에서 컨테이너가 1000px 이면 남는 공간은 1000 − 200 − 20×2 = 760px 이고, 1fr 은 760/3 ≈ 253.3px, 2fr 은 약 506.7px 이다.

이름 붙인 영역으로 골격을 그리듯 쓸 수도 있다.

```css
.page {
  display: grid;
  grid-template-columns: 240px 1fr;
  grid-template-rows: auto 1fr auto;
  grid-template-areas:
    "head head"
    "side main"
    "foot foot";
  min-height: 100vh;
}
header { grid-area: head; }
aside  { grid-area: side; }
main   { grid-area: main; }
footer { grid-area: foot; }
```

반응형 카드 목록은 한 줄이면 된다.

```css
.cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 16px;
}
```

칸은 최소 220px 을 지키고, 들어갈 수 있는 만큼 열을 만든 뒤 남는 공간은 `1fr` 로 나눠 가진다. 미디어 쿼리 없이 화면 너비에 따라 열 수가 바뀐다.

### 무엇을 고를까

| 상황 | 적합 |
|---|---|
| 버튼 묶음, 내비게이션 바, 아이콘+글자 정렬 | Flexbox |
| 내용 크기에 따라 자연스럽게 흐르는 한 줄 | Flexbox |
| 페이지 골격, 행·열을 함께 맞춰야 하는 표 형태 | Grid |
| 카드 목록에서 열 정렬을 맞추고 싶을 때 | Grid |

거칠게 말하면 Flexbox 는 "내용이 레이아웃을 정하고", Grid 는 "레이아웃이 내용을 받는다". 둘은 경쟁이 아니라 조합이다. Grid 로 골격을 짜고 각 칸 안은 Flexbox 로 정렬하는 식이 흔하다.

## 직접 해 보기

Flexbox 의 grow/shrink 분배와 Grid 의 `fr` 계산을 파이썬으로 재현한다. 최소 크기 제약은 생략한 단순판이다.

```python
def flex_line(container, items):
    """items: (이름, flex-basis, grow, shrink)"""
    free = container - sum(b for _, b, _, _ in items)
    out = []
    if free >= 0:
        total = sum(g for _, _, g, _ in items)
        for name, b, g, _ in items:
            out.append((name, b + (free * g / total if total else 0)))
    else:
        scaled = sum(b * s for _, b, _, s in items)
        for name, b, _, s in items:
            out.append((name, b + free * (b * s) / scaled))
    return free, out

def fr_tracks(container, tracks, gap=0):
    fixed = sum(float(t[:-2]) for t in tracks if t.endswith("px"))
    free = container - fixed - gap * (len(tracks) - 1)
    fr = sum(float(t[:-2]) for t in tracks if t.endswith("fr"))
    return [float(t[:-2]) if t.endswith("px") else free * float(t[:-2]) / fr
            for t in tracks]

for width in (600, 300):
    free, res = flex_line(width, [("A", 100, 1, 1), ("B", 200, 2, 1), ("C", 100, 0, 1)])
    print(f"flex 컨테이너 {width}px, 남는 공간 {free}px")
    for name, size in res:
        print(f"  {name}: {size:.1f}px")

print("grid 200px 1fr 2fr, gap 20, 1000px:",
      [round(x, 1) for x in fr_tracks(1000, ["200px", "1fr", "2fr"], gap=20)])
```

실행 결과:

```
flex 컨테이너 600px, 남는 공간 200px
  A: 166.7px
  B: 333.3px
  C: 100.0px
flex 컨테이너 300px, 남는 공간 -100px
  A: 75.0px
  B: 150.0px
  C: 75.0px
grid 200px 1fr 2fr, gap 20, 1000px: [200.0, 253.3, 506.7]
```

600px 일 때 C 는 `grow: 0` 이라 그대로고, 남는 200px 을 A 와 B 가 1:2 로 나눈다. 300px 일 때는 100px 이 모자라고, `shrink × basis` 가 100:200:100 이므로 B 가 가장 많이 줄어든다. 같은 값을 HTML 파일에 넣고 브라우저 개발자 도구의 Flexbox·Grid 오버레이로 보면 숫자가 그대로 맞는 것을 확인할 수 있다.

## 현업에서는

- **"왜 말줄임표가 안 되죠?"**: 흔한 원인은 Flex 항목의 `min-width: auto` 문제다. 항목에 `min-width: 0` 또는 `overflow: hidden` 을 준다.
- **관리 화면 레이아웃**: 사이드바 고정 너비 + 나머지 본문은 `grid-template-columns: 240px 1fr` 한 줄로 끝난다. 예전처럼 `calc(100% - 240px)` 를 계산할 필요가 없다.
- **대시보드 카드**: 홈랩 클러스터의 노드 상태 카드 같은 목록은 `repeat(auto-fill, minmax(...))` 로 짜 두면 휴대폰과 큰 모니터에서 모두 알맞은 열 수로 보인다.
- **순서 주의**: `order` 나 `grid-area` 로 시각적 순서를 바꿔도 DOM 순서, 즉 키보드 Tab 순서와 스크린 리더 낭독 순서는 바뀌지 않는다. 시각 순서와 논리 순서가 어긋나지 않게 마크업 순서를 먼저 맞춘다.

## 확인 문제

1. `flex: 1` 과 `flex: auto` 의 차이는 무엇인가.
2. 컨테이너 500px, 항목 A(basis 100, grow 1), B(basis 100, grow 3) 일 때 각 너비는?
3. 컨테이너 800px, `grid-template-columns: 100px 1fr 1fr`, `gap: 10px` 일 때 `1fr` 의 크기는?
4. Flex 항목 안의 긴 텍스트에 말줄임표가 적용되지 않는 흔한 원인은?
5. `order` 로 순서를 바꿀 때 접근성 측면에서 주의할 점은?

### 풀이

1. `flex: 1` 은 basis 가 0 이라 내용과 무관하게 비율대로 나누고, `flex: auto` 는 내용 크기를 기준으로 남는 공간만 나눈다.
2. 남는 공간 300px 을 1:3 으로 나눠 A = 175px, B = 325px.
3. (800 − 100 − 10×2) / 2 = 340px.
4. Flex 항목의 `min-width` 기본값이 `auto` 라 내용보다 작게 줄지 않기 때문이다. `min-width: 0` 을 준다.
5. 시각 순서만 바뀌고 Tab 순서와 낭독 순서는 DOM 순서를 따르므로 사용자가 혼란을 겪을 수 있다.

## 더 읽을거리 (References)

- W3C, *CSS Flexible Box Layout Module Level 1*: <https://www.w3.org/TR/css-flexbox-1/>
- W3C, *CSS Grid Layout Module Level 2*: <https://www.w3.org/TR/css-grid-2/>
- MDN, *Basic concepts of flexbox*: <https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_flexible_box_layout/Basic_concepts_of_flexbox>
- MDN, *Basic concepts of grid layout*: <https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_grid_layout/Basic_concepts_of_grid_layout>
