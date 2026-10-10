---
layout: post
title: "[CS300 #201] 웹 브라우저 렌더링 과정 — 바이트가 픽셀이 되기까지"
date: 2026-10-10 21:21:00 +0900
categories: [cs]
tags: [cs300, web, browser, rendering, dom, cssom]
---

컴퓨터공학 300 주제 시리즈의 201번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

브라우저는 HTML 바이트를 DOM 으로, CSS 를 CSSOM 으로 만든 뒤 둘을 합쳐 렌더 트리를 만들고, 레이아웃(위치·크기 계산) → 페인트(그리기) → 합성(레이어 겹치기) 순서로 화면에 픽셀을 찍는다.

## 왜 필요한가

"페이지가 느리다"는 말은 여러 뜻이다. 서버 응답이 늦을 수도 있고, 자바스크립트가 HTML 파싱을 막고 있을 수도 있고, 스크롤할 때마다 레이아웃을 다시 계산하고 있을 수도 있다. 이 셋은 고치는 방법이 전혀 다르다.

렌더링 과정을 알면 다음 질문에 답할 수 있다.

- `<script>` 를 `<head>` 에 두면 왜 첫 화면이 늦게 뜨는가.
- `top` 을 바꾸는 애니메이션은 버벅이는데 `transform` 은 왜 부드러운가.
- 루프 안에서 `offsetHeight` 를 읽으면 왜 갑자기 느려지는가.

프론트엔드 성능 최적화(213번 주제)의 거의 모든 기법은 이 파이프라인의 어느 단계를 건너뛰거나 줄이는 일이다.

## 핵심 개념

### 전체 파이프라인

```
 네트워크                파싱                     렌더링
 ─────────   ┌──────────────────────┐   ┌─────────────────────────────┐
 HTML 바이트 ─▶ 토큰화 ─▶ 트리 구성 ─▶ DOM ─┐
                                         ├─▶ 렌더 트리 ─▶ 레이아웃 ─▶ 페인트 ─▶ 합성 ─▶ 화면
 CSS 바이트  ─▶ 파싱 ─────────────▶ CSSOM ─┘
 JS 바이트   ─▶ 파싱·실행 (DOM/CSSOM 을 읽고 고칠 수 있음)
```

단계마다 하는 일은 다음과 같다.

| 단계 | 입력 | 출력 | 하는 일 |
|---|---|---|---|
| HTML 파싱 | 바이트 | DOM 트리 | 문자 디코딩 → 토큰화 → 트리 구성 |
| CSS 파싱 | 스타일시트 | CSSOM | 규칙을 트리 구조로 정리 |
| 스타일 계산 | DOM + CSSOM | 노드별 계산된 스타일 | 캐스케이드·상속·명시도 적용 |
| 렌더 트리 구성 | 위 결과 | 렌더 트리 | 보이는 노드만 남김 (`display:none`, `<head>` 제외) |
| 레이아웃 | 렌더 트리 | 박스의 위치·크기 | 뷰포트 기준 기하 계산. 리플로우라고도 부른다 |
| 페인트 | 레이아웃 결과 | 그리기 명령 목록 | 글자·색·테두리·그림자를 픽셀로 칠할 준비 |
| 합성 | 여러 레이어 | 최종 프레임 | 레이어를 순서대로 겹쳐 GPU 로 출력 |

### HTML 파싱은 관대하고, 멈출 수 있다

HTML 표준은 파서를 토큰화 단계와 트리 구성 단계로 나눠 아주 자세히 정의한다. 닫는 태그가 빠지거나 태그가 잘못 중첩되어도 오류로 멈추지 않고, 표준이 정한 복구 규칙대로 트리를 만든다. 그래서 어느 브라우저에서나 같은 잘못된 HTML 이 같은 DOM 이 된다.

파서를 멈추는 것은 `<script>` 다. 스크립트는 `document.write()` 로 아직 파싱되지 않은 HTML 을 끼워 넣을 수 있기 때문에, 속성 없는 일반 스크립트를 만나면 파서는 스크립트를 내려받아 실행할 때까지 기다린다. 이것을 파서 차단(parser-blocking)이라고 한다.

| 형태 | 다운로드 | 실행 시점 | 파싱 차단 |
|---|---|---|---|
| `<script src>` | 즉시 | 받자마자, 파싱 멈춤 | 예 |
| `<script defer src>` | 병렬 | 파싱이 끝난 뒤, 문서 순서대로 | 아니오 |
| `<script async src>` | 병렬 | 받는 즉시, 순서 보장 없음 | 실행 순간만 |
| `<script type="module">` | 병렬 | 기본이 defer 처럼 동작 | 아니오 |

실제 브라우저는 파서가 멈춘 동안에도 뒤쪽 HTML 을 훑어 이미지·스크립트·스타일시트를 미리 요청하는 프리로드 스캐너를 둔다. 그래도 실행 자체가 늦어지는 것은 막지 못한다.

### CSS 는 렌더링을 막는다

CSSOM 이 완성되지 않으면 어떤 노드가 보이는지, 얼마나 큰지 알 수 없다. 그래서 브라우저는 스타일시트를 다 받을 때까지 첫 페인트를 미룬다. 스타일이 없는 화면이 번쩍 보였다가 바뀌는 일(FOUC)을 막기 위해서다. 또 스크립트가 `getComputedStyle()` 로 스타일을 물을 수 있으므로, 앞쪽 스타일시트가 끝나기 전에는 뒤쪽 스크립트 실행도 기다린다.

결론은 단순하다. CSS 는 작게, 빨리 보내고, 스크립트는 `defer` 나 `module` 로 미룬다.

### 레이아웃·페인트·합성, 그리고 다시 하기

DOM 이나 스타일이 바뀌면 파이프라인의 일부를 다시 돈다. 무엇을 바꾸느냐에 따라 다시 도는 범위가 다르다.

```
width, top, font-size 변경  → 스타일 → 레이아웃 → 페인트 → 합성   (가장 비쌈)
color, background 변경      → 스타일 →          페인트 → 합성
transform, opacity 변경     → 스타일 →                   합성   (가장 쌈)
```

`transform` 과 `opacity` 는 요소가 별도 합성 레이어에 올라가 있으면 메인 스레드의 레이아웃·페인트 없이 합성 단계만으로 처리할 수 있다. 애니메이션을 이 두 속성으로 만들라는 조언이 여기서 나온다. 다만 어떤 요소를 레이어로 올릴지는 브라우저 엔진이 정하며, 레이어가 너무 많으면 메모리를 더 쓴다.

### 강제 동기 레이아웃

브라우저는 보통 변경을 모아 두었다가 다음 프레임에 한 번에 레이아웃한다. 그런데 스크립트가 변경 직후 `offsetHeight`, `getBoundingClientRect()` 처럼 레이아웃 결과를 읽으면, 정확한 값을 주려고 그 자리에서 레이아웃을 강제로 수행한다. 이것을 쓰기와 읽기를 번갈아 반복하면 매 반복마다 레이아웃이 일어난다(레이아웃 스래싱).

```js
// 나쁜 예: 반복마다 쓰기 → 읽기 → 강제 레이아웃
for (const el of items) {
  el.style.width = box.offsetWidth + "px";
}

// 좋은 예: 읽기를 먼저 모으고 쓰기를 나중에 모은다
const w = box.offsetWidth;
for (const el of items) {
  el.style.width = w + "px";
}
```

### 프레임 예산

화면이 초당 60번 갱신된다면 한 프레임에 쓸 수 있는 시간은 약 16.7ms(1000/60)다. 이 안에 스크립트, 스타일, 레이아웃, 페인트, 합성이 다 끝나야 끊김 없이 보인다. 메인 스레드에서 긴 작업이 돌면 그동안 입력 처리도, 렌더링도 멈춘다. 이 내용은 다음 주제인 이벤트 루프(204번)와 바로 이어진다.

## 직접 해 보기

파이썬 표준 라이브러리의 `html.parser` 로 아주 단순한 트리 빌더를 만들어 DOM 이 어떤 모양인지 본다. `<head>` 와 `<script>` 하위는 렌더 트리에서 빠진다는 표시도 붙인다.

```python
from html.parser import HTMLParser

VOID = {"meta", "link", "img", "br", "hr", "input"}

class Node:
    def __init__(self, tag, parent=None):
        self.tag, self.parent, self.children, self.text = tag, parent, [], ""

class TreeBuilder(HTMLParser):
    def __init__(self):
        super().__init__()
        self.root = Node("#document")
        self.cur = self.root
    def handle_starttag(self, tag, attrs):
        node = Node(tag, self.cur)
        self.cur.children.append(node)
        if tag not in VOID:          # 빈 요소는 자식을 갖지 않는다
            self.cur = node
    def handle_endtag(self, tag):
        if self.cur.tag == tag:
            self.cur = self.cur.parent
    def handle_data(self, data):
        if data.strip():
            t = Node("#text", self.cur)
            t.text = data.strip()
            self.cur.children.append(t)

def dump(n, depth=0, hidden=False):
    label = n.tag if n.tag != "#text" else f'"{n.text}"'
    print("  " * depth + label + ("   <- 렌더 트리에서 제외" if hidden else ""))
    for c in n.children:
        dump(c, depth + 1, hidden or c.tag in {"head", "script"})

html = """<html><head><title>T</title><script>x()</script></head>
<body><h1>안녕</h1><p>렌더링 <b>과정</b></p></body></html>"""
b = TreeBuilder(); b.feed(html); dump(b.root)
```

실행 결과:

```
#document
  html
    head   <- 렌더 트리에서 제외
      title   <- 렌더 트리에서 제외
        "T"   <- 렌더 트리에서 제외
      script   <- 렌더 트리에서 제외
        "x()"   <- 렌더 트리에서 제외
    body
      h1
        "안녕"
      p
        "렌더링"
        b
          "과정"
```

진짜 브라우저 파서는 이보다 훨씬 복잡하다. 예를 들어 `<p>` 안에 `<div>` 가 오면 표준 규칙에 따라 `<p>` 를 자동으로 닫는다. 브라우저 개발자 도구의 Elements 패널에서 일부러 틀린 HTML 을 넣고, 소스와 DOM 이 어떻게 다른지 비교해 보면 좋다. Performance 패널로 기록하면 Parse HTML, Recalculate Style, Layout, Paint, Composite 같은 단계가 실제로 시간축 위에 찍히는 것도 볼 수 있다.

## 현업에서는

- **첫 화면이 늦다는 신고**: 가장 먼저 `<head>` 의 동기 스크립트와 큰 스타일시트를 본다. 분석 도구·광고 스크립트를 `async` 로 바꾸는 것만으로 첫 페인트가 당겨지는 경우가 많다.
- **스크롤이 끊긴다는 신고**: Performance 패널에서 프레임마다 보라색 Layout 막대가 반복되는지 본다. 스크롤 이벤트 핸들러가 레이아웃 값을 읽고 쓰는 패턴이 흔한 원인이다.
- **애니메이션**: 디자인 시스템에서 이동은 `transform: translate()`, 페이드는 `opacity` 로 통일해 두면 저사양 기기에서 차이가 크다.
- **홈랩의 대시보드**: k3s 클러스터에 Grafana 같은 무거운 웹 UI 를 띄워 두고 구형 노트북 브라우저로 열면, 서버는 한가한데 화면만 느린 경우가 있다. 이때 병목은 네트워크나 파드가 아니라 클라이언트 쪽 스크립트 실행과 레이아웃이다. 서버 메트릭만 보면 원인을 못 찾는다.

## 확인 문제

1. `<script src="a.js">` 와 `<script defer src="a.js">` 의 차이를 파싱 관점에서 설명하라.
2. CSS 가 "렌더 차단 리소스"인 이유는 무엇인가.
3. `display: none` 인 요소와 `visibility: hidden` 인 요소는 렌더 트리와 레이아웃에서 어떻게 다르게 취급되는가.
4. 왼쪽으로 미끄러지는 애니메이션을 `left` 로 만들 때와 `transform` 으로 만들 때, 다시 실행되는 파이프라인 단계를 비교하라.
5. 다음 코드가 느린 이유와 고치는 방법은? `for (el of list) { el.style.height = el.offsetWidth + "px"; }`

### 풀이

1. 일반 스크립트는 만나는 순간 파싱을 멈추고 내려받아 실행한 뒤 파싱을 재개한다. `defer` 는 병렬로 내려받고, 파싱이 끝난 뒤 문서 순서대로 실행하므로 파싱을 막지 않는다.
2. CSSOM 없이는 무엇이 보이고 얼마나 큰지 계산할 수 없어서, 브라우저가 스타일시트를 받을 때까지 첫 페인트를 미루기 때문이다.
3. `display: none` 은 렌더 트리에서 빠져 공간도 차지하지 않는다. `visibility: hidden` 은 렌더 트리에 남아 레이아웃 공간을 차지하되 그려지지만 않는다.
4. `left` 는 매 프레임 레이아웃·페인트·합성을 모두 다시 한다. `transform` 은 레이어가 분리되어 있으면 합성만 다시 한다.
5. 매 반복마다 스타일을 쓴 직후 `offsetWidth` 를 읽어 강제 동기 레이아웃이 반복된다. 먼저 모든 너비를 배열로 읽어 두고, 그 다음 반복에서 높이를 쓴다.

## 더 읽을거리 (References)

- WHATWG, *HTML Living Standard — Parsing HTML documents*: <https://html.spec.whatwg.org/multipage/parsing.html>
- MDN, *Populating the page: how browsers work*: <https://developer.mozilla.org/en-US/docs/Web/Performance/Guides/How_browsers_work>
- MDN, *Critical rendering path*: <https://developer.mozilla.org/en-US/docs/Web/Performance/Guides/Critical_rendering_path>
- web.dev, *Understand the critical path*: <https://web.dev/articles/critical-rendering-path>
