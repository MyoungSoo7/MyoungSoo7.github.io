---
layout: post
title: "[CS300 #295] 접근성과 포용 — 누구나 쓸 수 있어야 완성이다"
date: 2026-10-10 22:55:00 +0900
categories: [cs]
tags: [cs300, hci, accessibility, wcag, a11y]
---

컴퓨터공학 300 주제 시리즈의 295번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

접근성(accessibility, a11y)은 장애가 있는 사람을 포함해 누구나 서비스를 인지하고 조작하고 이해할 수 있게 만드는 것이다. 웹에서는 W3C 의 WCAG 가 기준이고, 대부분은 올바른 HTML, 충분한 대비, 키보드 조작 같은 기본기로 해결된다.

## 왜 필요한가

WHO 는 세계 인구의 약 16%, 약 13억 명이 심각한 장애를 겪고 있다고 추정한다. 여기에 일시적 제약(팔 골절, 밝은 햇빛 아래의 휴대폰, 시끄러운 지하철)과 노화에 따른 시력·청력·운동 능력 저하까지 더하면 접근성의 혜택을 받는 사람은 훨씬 많다.

접근성은 법적 의무이기도 하다. 한국의 「장애인차별금지 및 권리구제 등에 관한 법률」은 정보 접근에서의 차별 금지를 규정한다. 다른 나라에도 비슷한 법이 있다.

그리고 접근성을 지키면 모두가 편해진다. 자막은 소리를 끈 사용자에게, 키보드 단축키는 숙련자에게, 명확한 레이블은 검색 엔진과 자동화 테스트에게 도움이 된다.

## 핵심 개념

### 다양한 사용 방식

| 사용자 | 쓰는 도구·방식 | 깨지는 지점 |
|---|---|---|
| 전맹 | 화면 낭독기(screen reader) | 대체 텍스트 없는 이미지, 레이블 없는 버튼 |
| 저시력 | 화면 확대, 고대비 모드 | 낮은 대비, 확대 시 깨지는 레이아웃 |
| 색각 이상 | 색 보정 없음 | 색으로만 구분한 상태 표시 |
| 운동 장애 | 키보드, 스위치, 음성 제어 | 마우스로만 되는 기능, 작은 터치 대상 |
| 청각 장애 | 자막, 수어 | 자막 없는 영상, 소리로만 주는 알림 |
| 인지 장애 | 단순한 화면, 충분한 시간 | 복잡한 흐름, 시간 제한, 모호한 문구 |

### WCAG 의 네 원칙(POUR)

WCAG(Web Content Accessibility Guidelines) 2.2 는 W3C 권고안(Recommendation)이다. 지침은 네 원칙 아래 묶인다.

| 원칙 | 뜻 | 예 |
|---|---|---|
| 인지 가능(Perceivable) | 정보를 감각으로 받아들일 수 있다 | 대체 텍스트, 자막, 충분한 대비 |
| 운용 가능(Operable) | 조작할 수 있다 | 키보드 접근, 충분한 시간, 발작 유발 깜빡임 금지 |
| 이해 가능(Understandable) | 이해할 수 있다 | 일관된 탐색, 입력 오류 안내 |
| 견고성(Robust) | 보조 기술이 해석할 수 있다 | 올바른 마크업, 이름·역할·값 제공 |

각 성공 기준은 A, AA, AAA 세 수준으로 나뉜다. 법이나 조달 기준은 보통 AA 를 요구한다.

### 명도 대비

WCAG 의 성공 기준 1.4.3(AA)은 일반 텍스트 4.5:1, 큰 텍스트 3:1 이상의 대비를 요구한다. 대비율은 앞서 색 공간 글에서 본 상대 휘도 L 로 계산한다.

```
대비율 = (L_밝은색 + 0.05) / (L_어두운색 + 0.05)      범위 1:1 ~ 21:1
```

버튼 테두리, 입력창 경계, 아이콘 같은 비텍스트 요소는 성공 기준 1.4.11 에서 3:1 을 요구한다.

### 시맨틱 HTML 이 먼저다

화면 낭독기는 화면의 픽셀이 아니라 접근성 트리(accessibility tree)를 읽는다. 브라우저는 HTML 요소에서 이 트리를 만든다. 그래서 올바른 요소를 쓰면 접근성의 대부분이 공짜로 따라온다.

```html
<!-- 나쁜 예: 보기엔 버튼이지만 키보드 포커스도, 역할도, Enter 동작도 없다 -->
<div class="btn" onclick="save()">저장</div>

<!-- 좋은 예: 포커스, Enter/Space 동작, "버튼" 역할이 기본 제공 -->
<button type="button" onclick="save()">저장</button>
```

WAI-ARIA 는 HTML 만으로 표현하기 어려운 위젯(탭, 트리, 실시간 영역)에 역할과 상태를 붙이는 명세다. W3C 의 [ARIA 작성 지침(APG)](https://www.w3.org/WAI/ARIA/apg/practices/read-me-first/)은 "No ARIA is better than Bad ARIA"라고 경고한다. 네이티브 HTML 요소로 되는 일이면 그것을 먼저 쓴다.

### 자주 깨지는 것

- 이미지 `alt`: 의미 있는 이미지는 내용을 설명하고, 장식 이미지는 `alt=""` 로 비워 화면 낭독기가 건너뛰게 한다. `alt` 속성 자체가 없으면 파일명을 읽어 버린다.
- 폼 레이블: `placeholder` 는 레이블이 아니다. 입력하면 사라지고 대비도 낮다. `<label for>` 를 쓴다.
- 키보드: Tab 으로 모든 기능에 도달하고, 포커스 위치가 보여야 한다. `outline: none` 으로 포커스 표시를 지우지 않는다.
- 색만으로 전달: "빨간 항목은 오류" 대신 아이콘이나 글자를 함께 쓴다.
- 동적 변화: 화면 일부가 바뀌면(토스트, 검증 오류) 화면 낭독기에도 알려야 한다. `aria-live` 영역을 쓴다.
- 언어 지정: `<html lang="ko">` 가 없으면 화면 낭독기가 한국어를 다른 언어 발음 규칙으로 읽을 수 있다.

## 직접 해 보기

대비율 계산기와 아주 작은 HTML 접근성 검사기를 만든다. 표준 라이브러리만 쓴다.

```python
from html.parser import HTMLParser

def lin(c8):
    c = c8 / 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

def lum(hexcolor):
    h = hexcolor.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)

def contrast(fg, bg):
    l1, l2 = sorted((lum(fg), lum(bg)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)

for fg, bg in [("#000000", "#ffffff"), ("#767676", "#ffffff"),
               ("#999999", "#ffffff"), ("#ffffff", "#4caf50")]:
    r = contrast(fg, bg)
    print(f"{fg} on {bg}: {r:5.2f}:1  본문 AA {'통과' if r >= 4.5 else '미달'}"
          f"  큰 글자 AA {'통과' if r >= 3 else '미달'}")

class A11yLint(HTMLParser):
    def __init__(self):
        super().__init__()
        self.problems, self.labels, self.inputs = [], set(), []
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "img" and "alt" not in a:
            self.problems.append(f"img 에 alt 없음: {a.get('src')}")
        if tag == "label" and "for" in a:
            self.labels.add(a["for"])
        if tag == "input" and a.get("type") not in ("hidden", "submit"):
            self.inputs.append(a)
        if tag == "div" and "onclick" in a and "role" not in a:
            self.problems.append("onclick 있는 div: 키보드로 접근 불가, button 을 쓸 것")
    def close(self):
        super().close()
        for a in self.inputs:
            if a.get("id") not in self.labels and "aria-label" not in a:
                self.problems.append(f"레이블 없는 input: name={a.get('name')}")

html = """
<img src="logo.png">
<img src="divider.png" alt="">
<label for="email">이메일</label><input id="email" name="email" type="email">
<input name="phone" type="tel" placeholder="전화번호">
<div onclick="save()">저장</div>
"""
lint = A11yLint()
lint.feed(html)
lint.close()
print("\n".join(lint.problems))
```

실행 결과다.

```
#000000 on #ffffff: 21.00:1  본문 AA 통과  큰 글자 AA 통과
#767676 on #ffffff:  4.54:1  본문 AA 통과  큰 글자 AA 통과
#999999 on #ffffff:  2.85:1  본문 AA 미달  큰 글자 AA 미달
#ffffff on #4caf50:  2.78:1  본문 AA 미달  큰 글자 AA 미달
img 에 alt 없음: logo.png
onclick 있는 div: 키보드로 접근 불가, button 을 쓸 것
레이블 없는 input: name=phone
```

`#767676` 은 흰 배경에서 본문 기준을 겨우 넘는 회색이다. 디자인에서 흔히 쓰는 `#999999` 는 미달이다. 초록 버튼에 흰 글자도 생각보다 대비가 낮다. 장식 이미지의 `alt=""` 는 올바르므로 검사에 걸리지 않았고, `placeholder` 만 있는 입력은 레이블 없음으로 잡혔다.

자동 검사는 일부만 잡는다. 대체 텍스트가 "있는지"는 알아도 "적절한지"는 모른다. 키보드만으로 실제 과업을 끝까지 해 보고, 화면 낭독기(macOS VoiceOver, Windows NVDA 등)로 한 번 들어 보는 수동 점검이 필요하다.

## 현업에서는

- CI 에 자동 접근성 검사(axe 계열 도구, Lighthouse 등)를 넣어 회귀를 막는다. 디자인 시스템의 컴포넌트를 접근성 있게 만들어 두면 그 위의 모든 화면이 혜택을 받는다.
- 운영 대시보드와 알림도 대상이다. 장애 상태를 빨강·초록 색만으로 표시하지 말고 글자나 아이콘을 함께 쓴다. 홈랩 k3s 모니터링 화면도 마찬가지다.
- CLI 와 문서도 접근성이 있다. 색이 들어간 터미널 출력은 `NO_COLOR` 같은 관례로 끌 수 있게 하고, 문서의 코드 스크린숏 대신 텍스트 코드 블록을 쓴다. 이미지 속 글자는 화면 낭독기와 검색이 읽지 못한다.
- 접근성은 출시 직전에 붙이는 것이 아니다. 설계 단계에서 포커스 순서와 대비를 정하는 것이 나중에 고치는 것보다 훨씬 싸다.
- 장애가 있는 사용자를 사용성 테스트에 직접 참여시킨다. 체크리스트를 통과해도 실제로 쓰기 어려운 경우가 있다.

## 확인 문제

1. WCAG 의 네 원칙(POUR)을 적어라.
2. 장식용 이미지에 `alt` 속성을 아예 빼면 안 되는 이유는?
3. `<div onclick>` 대신 `<button>` 을 써야 하는 이유 두 가지는?
4. 회색 글자 `#999999` 를 흰 배경 본문에 쓰면 WCAG AA 를 만족하는가?
5. 자동 접근성 검사만으로 충분하지 않은 이유는?

### 풀이

1. 인지 가능(Perceivable), 운용 가능(Operable), 이해 가능(Understandable), 견고성(Robust).
2. `alt` 가 없으면 화면 낭독기가 파일명 등을 읽을 수 있다. 장식 이미지는 `alt=""` 로 명시해 건너뛰게 한다.
3. 키보드 포커스와 Enter/Space 동작이 기본 제공되고, 보조 기술에 "버튼" 역할이 전달된다.
4. 대비율이 약 2.85:1 로 4.5:1 에 못 미쳐 만족하지 않는다.
5. 대체 텍스트의 적절성, 포커스 순서의 논리성, 과업 흐름의 이해 가능성 같은 것은 사람이 판단해야 한다.

## 더 읽을거리 (References)

- W3C, [Web Content Accessibility Guidelines (WCAG) 2.2](https://www.w3.org/TR/WCAG22/)
- W3C WAI, [ARIA Authoring Practices Guide](https://www.w3.org/WAI/ARIA/apg/)
- WHO, [Disability (fact sheet)](https://www.who.int/news-room/fact-sheets/detail/disability-and-health)
- 국가법령정보센터, [장애인차별금지 및 권리구제 등에 관한 법률](https://www.law.go.kr/%EB%B2%95%EB%A0%B9/%EC%9E%A5%EC%95%A0%EC%9D%B8%EC%B0%A8%EB%B3%84%EA%B8%88%EC%A7%80%EB%B0%8F%EA%B6%8C%EB%A6%AC%EA%B5%AC%EC%A0%9C%EB%93%B1%EC%97%90%EA%B4%80%ED%95%9C%EB%B2%95%EB%A5%A0)
