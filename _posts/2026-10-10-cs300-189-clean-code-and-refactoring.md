---
layout: post
title: "[CS300 #189] 클린 코드와 리팩터링 — 동작은 그대로, 구조만 바꾸는 기술"
date: 2026-10-10 21:09:00 +0900
categories: [cs]
tags: [cs300, software-engineering, refactoring, clean-code, code-smell]
---

컴퓨터공학 300 주제 시리즈의 189번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

클린 코드는 **다른 사람이 읽고 고치기 쉬운 코드**이고, 리팩터링은 겉으로 보이는 동작을 바꾸지 않으면서 내부 구조를 그런 방향으로 고치는 작업이다. 리팩터링의 전제 조건은 "동작이 바뀌지 않았다" 를 확인해 줄 테스트다.

## 왜 필요한가

코드는 쓰는 시간보다 읽히는 시간이 훨씬 길다. 파이썬 스타일 가이드 [PEP 8](https://peps.python.org/pep-0008/)도 첫머리에서 "코드는 쓰이는 것보다 훨씬 자주 읽힌다" 는 Guido van Rossum 의 통찰을 인용한다.

새 기능을 넣으려고 함수를 열었는데 이름이 `calc(d, t)` 이고, 안에 `0.9`, `0.95`, `50000` 같은 숫자가 맥락 없이 박혀 있다면, 고치기 전에 해독부터 해야 한다. 해독이 틀리면 버그가 된다. 리팩터링은 이 해독 비용을 다음 사람(대개 몇 달 뒤의 나)을 위해 미리 치르는 일이다.

## 핵심 개념

### 리팩터링의 정의

Martin Fowler 는 *Refactoring* 에서 리팩터링을 이렇게 정의한다.

> 겉으로 드러나는 동작을 바꾸지 않으면서, 이해하기 쉽고 수정 비용이 적게 들도록 소프트웨어의 내부 구조를 바꾸는 것.

두 가지가 중요하다.

1. **동작을 바꾸지 않는다.** 버그 수정이나 기능 추가는 리팩터링이 아니다. 둘을 한 커밋에 섞으면, 나중에 문제가 생겼을 때 어느 쪽 탓인지 가를 수 없다.
2. **작은 단계로 한다.** 한 번에 하나의 변환(함수 추출, 이름 바꾸기)을 하고, 매번 테스트를 돌린다. 테스트가 깨지면 바로 직전 단계만 되돌리면 된다.

Kent Beck 의 비유가 유명하다. 개발자는 "기능 추가" 모자와 "리팩터링" 모자를 번갈아 쓴다. 한 번에 한 모자만 쓴다.

### 코드 냄새

리팩터링이 필요한 곳을 알려 주는 징후를 [코드 냄새(code smell)](https://martinfowler.com/bliki/CodeSmell.html)라고 부른다. 냄새는 "반드시 문제" 가 아니라 "들여다볼 이유" 다.

| 냄새 | 증상 | 대표 처방 |
|---|---|---|
| 이해하기 어려운 이름 | `d`, `t`, `tmp2`, `doIt()` | 이름 바꾸기 |
| 긴 함수 | 스크롤해야 끝이 보인다 | 함수 추출 |
| 중복 코드 | 같은 계산이 여러 곳에 복사돼 있다 | 함수 추출, 공통 위치로 이동 |
| 매직 넘버 | 의미 없는 `0.95`, `86400` | 상수로 바꾸고 이름 붙이기 |
| 긴 매개변수 목록 | 인자가 6개 이상 | 매개변수 객체 도입 |
| 기본형 집착 | 금액·전화번호를 그냥 `int`·`str` 로 | 값 객체 도입 |
| 산탄총 수술 | 기능 하나 고치는데 파일 열 개를 고친다 | 함께 바뀌는 것을 한곳으로 모으기 |
| 기능 욕심 | 다른 객체의 데이터를 더 많이 쓴다 | 그 객체로 메서드 옮기기 |

처방 이름은 Fowler 의 [리팩터링 카탈로그](https://refactoring.com/catalog/)에 각각 절차와 함께 정리돼 있다.

### 클린 코드의 실천 항목

- **이름이 의도를 드러낸다.** `elapsed_days` 는 주석 없이 읽힌다. `d` 는 아니다.
- **함수는 한 가지 일을 하고, 한 추상 수준에 머문다.** "주문 합계 계산" 함수 안에서 HTTP 헤더를 파싱하고 있다면 추상 수준이 섞였다.
- **주석은 "왜" 를 쓴다.** "무엇을" 은 코드가 말해야 한다. `# 1을 더한다` 는 소음이고, `# 결제사 API 가 0-based 페이지를 쓰므로 보정` 은 정보다.
- **조건문을 단순하게.** 중첩 `if` 는 빠른 반환(guard clause)으로 펴고, 복잡한 조건식은 이름 있는 함수로 뺀다.
- **일관성.** 팀이 정한 포매터·린터를 쓴다. 스타일 논쟁을 도구에 맡기면 리뷰가 본질에 집중한다.

## 직접 해 보기

할인 계산 함수를 리팩터링하고, 무작위 입력 1만 개로 **전후 결과가 같은지** 확인한다. 기존 동작을 그대로 기록해 비교하는 이런 테스트를 특성화 테스트(characterization test)라고 부른다. 테스트가 없는 레거시 코드를 고치기 전에 먼저 만드는 안전망이다.

```python
import random

# ----- 리팩터링 전 -----
def calc(d, t):
    r = 0
    for i in d:
        if i[2] == 1:
            r += i[0] * i[1] * 0.9
        else:
            r += i[0] * i[1]
    if t == "VIP":
        r = r * 0.95
    if r > 50000:
        r = r - 3000
    return int(r)

# ----- 리팩터링 후 -----
MEMBER_ITEM_RATE = 0.9
VIP_RATE = 0.95
BIG_ORDER_THRESHOLD = 50_000
BIG_ORDER_DISCOUNT = 3_000

def line_amount(price, qty, member_sale):
    amount = price * qty
    return amount * MEMBER_ITEM_RATE if member_sale else amount

def apply_grade(subtotal, grade):
    return subtotal * VIP_RATE if grade == "VIP" else subtotal

def apply_big_order(total):
    return total - BIG_ORDER_DISCOUNT if total > BIG_ORDER_THRESHOLD else total

def order_total_v1(lines, grade):           # 첫 시도: sum() 으로 줄였다
    subtotal = sum(line_amount(p, q, flag == 1) for p, q, flag in lines)
    return int(apply_big_order(apply_grade(subtotal, grade)))

def order_total(lines, grade):              # 수정: 원래와 같은 순서로 누적
    subtotal = 0
    for price, qty, flag in lines:
        subtotal += line_amount(price, qty, flag == 1)
    return int(apply_big_order(apply_grade(subtotal, grade)))

# ----- 동작 보존 확인: 특성화 테스트(characterization test) -----
rng = random.Random(2026)
cases = []
for _ in range(10_000):
    lines = [(rng.randint(100, 30000), rng.randint(1, 5), rng.randint(0, 1))
             for _ in range(rng.randint(0, 6))]
    cases.append((lines, rng.choice(["VIP", "NORMAL"])))

for fn in (order_total_v1, order_total):
    diff = [(l, g) for l, g in cases if calc(l, g) != fn(l, g)]
    print(f"{fn.__name__:15s} 불일치 {len(diff)}건 / {len(cases)}건")
    if diff:
        l, g = diff[0]
        print(f"   예) 전 {calc(l, g)}  후 {fn(l, g)}")
```

실행 결과(Python 3.12):

```
order_total_v1  불일치 2건 / 10000건
   예) 전 164324  후 164325
order_total     불일치 0건 / 10000건
```

이 결과는 의도해서 만든 것이 아니라 예제를 쓰다가 실제로 걸린 것이다. 반복문을 `sum()` 한 줄로 줄인 "누가 봐도 안전한" 변환이 1만 건 중 2건에서 1원 차이를 냈다.
원인은 부동소수점이다. Python 3.12 부터 `sum()` 은 실수를 더할 때 Neumaier 보정 합산을 써서 정확도를 높인다([What's New in Python 3.12](https://docs.python.org/3/whatsnew/3.12.html)). 원래 코드의 `r +=` 누적은 `167324.99999999997` 을 만들고 `int()` 가 이를 `167324` 로 자른다. `sum()` 은 `167325.0` 을 만든다. 더 정확해진 것이지만, **동작은 바뀌었다.**

교훈은 세 가지다.

1. "명백히 같은" 변환도 테스트 없이 믿지 않는다.
2. 리팩터링 커밋에서는 원래 동작을 보존한다(`order_total`). 금액 계산을 정수나 `Decimal` 로 바꾸는 것은 **동작 변경**이므로 별도 커밋, 별도 리뷰로 한다.
3. 돈을 `float` 로 계산하는 원래 코드 자체가 다음 개선 대상이다. 특성화 테스트가 그 위험을 드러내 줬다.

## 현업에서는

- **보이스카우트 규칙.** "캠프장은 처음 왔을 때보다 깨끗하게 해 두고 떠난다." 기능 작업 중 지나가는 길의 이름 하나, 중복 하나를 정리하는 정도의 작은 리팩터링을 습관으로 한다. 단, 기능 변경과는 커밋을 나눈다.
- **포매터와 린터를 CI 에 건다.** 파이썬이면 PEP 8 을 따르는 포매터·린터를 커밋 전 훅과 CI 에 걸어 둔다. 사람이 리뷰에서 공백과 따옴표를 지적하는 시간이 사라진다.
- **IDE 의 자동 리팩터링을 쓴다.** 이름 바꾸기, 함수 추출, 시그니처 변경은 IDE 가 참조를 추적해 한 번에 바꿔 준다. 텍스트 치환보다 안전하다.
- **인프라 코드도 냄새가 난다.** 홈랩 클러스터의 매니페스트에서 같은 리소스 제한값과 레이블이 수십 개 파일에 복사돼 있다면 중복 코드 냄새다. Kustomize 의 공통 레이어나 Helm 값 파일로 추출하는 것이 같은 리팩터링이다.

## 확인 문제

1. 리팩터링과 기능 추가를 한 커밋에 섞으면 안 되는 이유는?
2. "매직 넘버" 냄새의 처방은 무엇이며, 무엇을 얻는가?
3. 특성화 테스트란 무엇이고 언제 쓰는가?
4. 위 예제에서 `sum()` 을 쓴 첫 시도가 결과를 바꾼 원인은?
5. 금액 계산을 `float` 에서 `Decimal` 로 바꾸는 작업은 리팩터링인가?

### 풀이

1. 동작 변경과 구조 변경이 섞여, 문제가 생겼을 때 원인을 가르기 어렵고 리뷰어도 무엇이 의도된 변화인지 판단할 수 없다.
2. 의미 있는 이름의 상수로 바꾼다. 숫자의 의도가 드러나고, 값을 바꿀 때 한 곳만 고치면 된다.
3. 현재 코드가 실제로 내는 결과를 그대로 기록해 두고, 변경 후 결과와 비교하는 테스트다. 테스트가 없는 레거시 코드를 리팩터링하기 전에 안전망으로 만든다.
4. Python 3.12 의 `sum()` 이 보정 합산을 써서 단순 누적과 다른 부동소수점 결과를 냈고, `int()` 절삭에서 1 차이가 났다.
5. 아니다. 결과값이 바뀔 수 있는 동작 변경이다. 리팩터링과 분리해 따로 커밋하고 리뷰한다.

## 더 읽을거리 (References)

- Martin Fowler, [Refactoring Catalog](https://refactoring.com/catalog/), 그리고 *Refactoring: Improving the Design of Existing Code*, 2nd ed., Addison-Wesley, 2018 (서지 정보)
- Martin Fowler, [CodeSmell](https://martinfowler.com/bliki/CodeSmell.html)
- [PEP 8 — Style Guide for Python Code](https://peps.python.org/pep-0008/)
- Python 문서, [What's New In Python 3.12](https://docs.python.org/3/whatsnew/3.12.html)
- Michael Feathers, *Working Effectively with Legacy Code*, Prentice Hall, 2004 (서지 정보)
