---
layout: post
title: "[CS300 #202] HTML 시맨틱 — 태그는 모양이 아니라 의미다"
date: 2026-10-10 21:22:00 +0900
categories: [cs]
tags: [cs300, web, html, semantics, accessibility]
---

컴퓨터공학 300 주제 시리즈의 202번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

시맨틱 HTML 은 "어떻게 보이는가"가 아니라 "이것이 무엇인가"를 태그로 표현하는 일이고, 그 의미를 브라우저·스크린 리더·검색 엔진이 그대로 읽어 간다.

## 왜 필요한가

`<div>` 와 CSS 만 있으면 어떤 화면이든 만들 수 있다. 그래서 "보이기만 하면 되지"라는 유혹이 크다. 그런데 화면을 보지 않고 페이지를 읽는 사용자와 프로그램이 생각보다 많다.

- 스크린 리더는 제목 목록, 랜드마크(머리말·본문·내비게이션) 목록으로 페이지를 건너다닌다.
- 키보드 사용자는 Tab 키로 버튼과 링크 사이를 이동한다. `<div onclick>` 은 기본적으로 Tab 으로 닿지 않는다.
- 검색 엔진과 미리보기 봇은 본문과 내비게이션을 구분해야 내용을 제대로 요약한다.
- 브라우저의 읽기 모드, 번역 기능, 자동 완성도 태그의 의미를 단서로 쓴다.

같은 화면이라도 태그를 잘 고르면 이 기능들이 공짜로 따라오고, 잘못 고르면 하나하나 손으로 흉내 내야 한다.

## 핵심 개념

### 의미는 "접근성 트리"로 전달된다

브라우저는 DOM 과 별도로 접근성 트리를 만들어 운영체제의 접근성 API 에 넘긴다. 각 노드는 역할(role), 이름(name), 상태(state)를 가진다. 시맨틱 요소는 이 정보를 기본으로 갖고 있다.

| 요소 | 암묵적 역할 | 기본 제공 |
|---|---|---|
| `<button>` | button | 포커스, Enter·Space 로 클릭, 폼 제출 |
| `<a href>` | link | 포커스, Enter 로 이동, 새 탭 열기 |
| `<nav>` | navigation | 랜드마크로 건너뛰기 |
| `<main>` | main | 본문 바로 가기 |
| `<header>` (body 직속) | banner | 랜드마크 |
| `<footer>` (body 직속) | contentinfo | 랜드마크 |
| `<h1>`~`<h6>` | heading (level 1~6) | 제목 목록 탐색 |
| `<ul>`, `<ol>` | list | "항목 5개" 같은 개수 안내 |
| `<label for>` | — | 입력칸 이름 제공, 클릭 시 입력칸 포커스 |

역할과 요소의 대응은 W3C 의 *ARIA in HTML* 문서가 표로 정해 둔다.

### 구획 요소

HTML 표준은 문서 구조를 나타내는 구획(sectioning) 요소를 정의한다.

```
<body>
  <header> 사이트 로고, 검색 </header>
  <nav> 주요 메뉴 </nav>
  <main>
    <article>               ← 단독으로 배포해도 뜻이 통하는 글
      <h1>글 제목</h1>
      <section>             ← 제목을 가진 주제 묶음
        <h2>소제목</h2>
      </section>
    </article>
    <aside> 관련 글 </aside> ← 본문과 간접적으로 관련된 내용
  </main>
  <footer> 저작권, 연락처 </footer>
</body>
```

`<main>` 은 문서에서 숨겨지지 않은 것이 하나만 있어야 한다. `<section>` 은 스타일링용 상자가 아니다. 단지 감싸기만 할 목적이면 `<div>` 가 맞다. HTML 표준도 그렇게 권한다.

### 제목 수준은 건너뛰지 않는다

스크린 리더 사용자는 제목 목록을 목차처럼 쓴다. `<h1>` 다음에 바로 `<h4>` 가 오면 중간 단계가 빠진 목차가 된다. 글자 크기를 바꾸고 싶으면 태그 수준을 바꾸지 말고 CSS 를 바꾼다.

### 상호작용은 네이티브 요소로

가장 흔한 실수는 클릭 가능한 `<div>` 다.

```html
<!-- 나쁜 예 -->
<div class="btn" onclick="save()">저장</div>

<!-- 좋은 예 -->
<button type="button" onclick="save()">저장</button>
```

`<div>` 로 버튼을 제대로 흉내 내려면 `role="button"`, `tabindex="0"`, Enter·Space 키 처리, 비활성 상태 표현을 다 직접 구현해야 한다. W3C 의 ARIA 사용 지침 첫 규칙도 "네이티브 HTML 요소로 되는 일이면 ARIA 대신 그 요소를 쓰라"는 것이다.

링크와 버튼의 구분도 의미로 한다. 다른 주소로 **이동**하면 `<a href>`, 현재 페이지에서 **동작**하면 `<button>` 이다.

### 텍스트 수준 의미

| 요소 | 의미 | 흔한 오해 |
|---|---|---|
| `<strong>` | 중요함 | `<b>` 는 의미 없이 굵게 |
| `<em>` | 강세(말할 때 힘줌) | `<i>` 는 다른 목소리·용어 |
| `<time datetime>` | 기계가 읽는 날짜 | 그냥 텍스트로 쓰면 해석 불가 |
| `<code>`, `<kbd>` | 코드, 키 입력 | 고정폭 글꼴은 결과일 뿐 |
| `<figure>` + `<figcaption>` | 그림과 설명의 묶음 | — |

### 폼은 라벨과 짝을 짓는다

```html
<label for="email">이메일</label>
<input id="email" type="email" autocomplete="email" required>
```

`type="email"` 은 모바일에서 @ 가 있는 키보드를 띄우고, `autocomplete` 는 브라우저 자동 완성에 힌트를 주며, `required` 는 별도 스크립트 없이 제출 전 검사를 한다. 의미를 정확히 적을수록 기능이 따라온다.

## 직접 해 보기

파이썬으로 간단한 시맨틱 점검기를 만든다. 제목 수준 건너뛰기, `onclick` 이 붙은 `<div>`, 라벨 없는 입력칸, `<main>` 개수를 검사한다.

```python
from html.parser import HTMLParser

class Lint(HTMLParser):
    def __init__(self):
        super().__init__()
        self.last_h, self.mains, self.labels, self.inputs = 0, 0, set(), []
        self.warn = []
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if len(tag) == 2 and tag[0] == "h" and tag[1].isdigit():
            lv = int(tag[1])
            if self.last_h and lv > self.last_h + 1:
                self.warn.append(f"제목 수준 건너뜀: h{self.last_h} -> h{lv}")
            self.last_h = lv
        if tag == "main":
            self.mains += 1
        if tag == "div" and "onclick" in a:
            self.warn.append("onclick 이 붙은 div: <button> 을 쓰라")
        if tag == "label" and "for" in a:
            self.labels.add(a["for"])
        if tag == "input" and a.get("type") not in ("hidden", "submit"):
            self.inputs.append(a.get("id"))
    def report(self):
        for i in self.inputs:
            if i not in self.labels:
                self.warn.append(f"라벨 없는 입력칸: id={i}")
        if self.mains != 1:
            self.warn.append(f"<main> 이 {self.mains}개")
        return self.warn or ["문제 없음"]

page = """<body><h1>주문</h1><h3>배송지</h3>
<div onclick="go()">다음</div>
<label for="name">이름</label><input id="name">
<input id="phone" type="tel"></body>"""
l = Lint(); l.feed(page)
print("\n".join(l.report()))
```

실행 결과:

```
제목 수준 건너뜀: h1 -> h3
onclick 이 붙은 div: <button> 을 쓰라
라벨 없는 입력칸: id=phone
<main> 이 0개
```

이 정도 규칙만으로도 실제 페이지에서 꽤 많은 문제가 걸린다. 브라우저 개발자 도구의 Accessibility 패널을 열면 각 요소가 접근성 트리에서 어떤 역할과 이름을 받았는지 직접 확인할 수 있다.

## 현업에서는

- **디자인 시스템의 컴포넌트**: 버튼 컴포넌트가 내부에서 `<div>` 를 렌더링하면, 그 회사의 모든 화면이 한꺼번에 키보드 접근성을 잃는다. 반대로 기반 컴포넌트를 네이티브 요소로 만들어 두면 한 번에 해결된다.
- **법·조달 요건**: 공공·금융 서비스는 접근성 지침 준수가 요구되는 경우가 많다. 시맨틱 마크업은 그 출발점이다(214번 주제에서 다룬다).
- **테스트 코드**: Testing Library 같은 도구는 `getByRole("button", { name: "저장" })` 처럼 역할과 이름으로 요소를 찾도록 권한다. 마크업이 시맨틱하면 테스트도 사용자 관점으로 쓰기 쉬워진다.
- **사내 도구**: 홈랩이나 사내 관리 화면처럼 "나만 쓰는" 페이지도, 표를 `<table>` 로 만들어 두면 복사·붙여넣기만으로 스프레드시트에 그대로 들어간다. 작은 이득이지만 매일 쌓인다.

## 확인 문제

1. `<section>` 과 `<div>` 는 언제 각각 쓰는가.
2. 다른 페이지로 이동하는 UI 와 모달을 여는 UI 는 각각 어떤 요소로 만들어야 하는가.
3. `<b>` 와 `<strong>` 은 화면에서 똑같이 굵게 보일 수 있다. 차이는 무엇인가.
4. `<div role="button">` 으로 버튼을 만들 때 추가로 구현해야 하는 것을 세 가지 들라.
5. 접근성 트리의 노드가 갖는 세 가지 정보는 무엇인가.

### 풀이

1. `<section>` 은 보통 제목을 가진 주제 묶음일 때, `<div>` 는 의미 없이 스타일·스크립트용으로 감쌀 때 쓴다.
2. 이동은 `<a href>`, 현재 페이지 안의 동작(모달 열기)은 `<button type="button">`.
3. `<strong>` 은 "중요함"이라는 의미를 갖고, `<b>` 는 의미 없이 주의를 끄는 표기다.
4. `tabindex="0"` 으로 포커스 가능하게 하기, Enter·Space 키 처리, 비활성·눌림 같은 상태를 `aria-*` 로 표현하기.
5. 역할(role), 이름(name), 상태(state·값).

## 더 읽을거리 (References)

- WHATWG, *HTML Living Standard — Sections*: <https://html.spec.whatwg.org/multipage/sections.html>
- W3C, *ARIA in HTML*: <https://www.w3.org/TR/html-aria/>
- W3C, *Accessible Rich Internet Applications (WAI-ARIA) 1.2*: <https://www.w3.org/TR/wai-aria-1.2/>
- MDN, *Semantics*: <https://developer.mozilla.org/en-US/docs/Glossary/Semantics>
