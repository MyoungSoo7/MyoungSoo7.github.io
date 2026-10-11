---
layout: post
title: "[SE100 #037] 레거시 코드 다루기 — 심(seam)과 특성 테스트"
date: 2026-10-11 17:00:01 +0900
categories: [software-engineering]
tags: [se100, code-quality, legacy-code, seams, characterization-tests, refactoring]
---

소프트웨어 공학 100 주제 시리즈의 37번째 글이다. (카테고리: 구현과 코드 품질)

## 한 줄 요약

레거시 코드는 오래된 코드가 아니라 **테스트가 없는 코드**다. 고치기 전에 먼저 지금 동작을 그대로 기록하는 특성 테스트로 안전망을 치고, 테스트를 넣을 틈인 심(seam)을 찾아 의존성을 끊은 뒤, 작게 바꾼다.

## 왜 필요한가

테스트가 없는 코드를 고칠 때 개발자는 두 가지 중 하나를 고른다. **편집하고 기도하기**(고치고, 수동으로 몇 번 눌러 보고, 배포)와 **아예 건드리지 않기**(같은 로직을 복사해 새 곳에 붙임)다. 앞의 것은 장애를, 뒤의 것은 중복과 부채를 만든다.

진짜 어려움은 순환에 있다. 리팩터링하려면 테스트가 필요한데, 테스트를 넣으려면 의존성을 끊는 리팩터링이 필요하다. 이 글의 기법들은 이 닭과 달걀 문제를 **최소한의 안전한 변경**으로 깨는 방법이다. 단위 테스트 일반은 [단위 테스트]({% post_url 2026-10-10-cs300-191-unit-testing %}) 글을, 대규모 교체 전략은 [기술 부채]({% post_url 2026-10-10-cs300-200-technical-debt %}) 글을 참고한다.

## 핵심 개념

### 레거시 코드의 정의

Michael Feathers 는 2002년 Object Mentor 논문 [Working Effectively With Legacy Code](https://objectmentor.com/resources/articles/WorkingEffectivelyWithLegacyCode.pdf)에서 이렇게 썼다.

> 레거시 코드와 그렇지 않은 코드를 가르는 주된 것은 테스트, 정확히는 테스트의 부재다. … 테스트가 있으면 코드를 거리낌 없이 개선할 수 있다. 테스트가 없으면 나아지는지 나빠지는지조차 알 수 없다.

같은 글은 "코드의 나이는 아무 상관이 없다. 사람들은 지금 이 순간에도 레거시 코드를 쓰고 있다" 고 덧붙인다. 이 생각은 2004년 책 *Working Effectively with Legacy Code*(Prentice Hall)로 확장되었다.

### 기준은 "어제의 동작"

같은 논문은 레거시 코드에 넣는 테스트가 보통의 테스트와 다르다고 말한다. 그 테스트에서 **올바른 동작이란 외부 명세가 아니라 그 클래스들이 어제 하던 일**이다. 목적은 정답 검증이 아니라 불변식을 세워서, 변경이 동작을 바꿨는지 **감지**하는 것이다. 논문은 이를 test covering 이라 불렀고, 책에서는 **특성 테스트(characterization test)** 라는 이름으로 정착했다. 지금 동작에 버그가 있어 보여도 일단 그대로 기록한다. 버그 수정은 안전망을 친 **다음**, 별도 변경으로 한다.

```
일반 테스트:   명세 ──▶ 기대값 ──▶ 코드가 맞는가?
특성 테스트:   코드 실행 ──▶ 관찰값을 기대값으로 고정 ──▶ 변경 후에도 같은가?
```

### 변경 전략 다섯 단계

2002년 논문의 전략은 다음과 같다.

1. 변경 지점을 찾는다.
2. **변곡점(inflection point)** 을 찾는다. 클래스 묶음에 대한 좁은 인터페이스로, 그 뒤의 어떤 변경이든 이 지점에서 감지되거나 애플리케이션에 영향이 없는 곳이다.
3. 변곡점을 테스트로 덮는다. (a) 외부 의존성 끊기, (b) 내부 의존성 끊기, (c) 테스트 작성.
4. 변경한다.
5. 덮인 코드를 리팩터링한다.

핵심은 2번이다. 변경할 메서드 하나를 직접 테스트하려 들면 의존성이 너무 많다. 변경의 영향이 모두 지나가는 **좁은 목**을 찾아 거기에 테스트를 건다.

### 심(seam)

책의 심 모델 장(InformIT 에 [발췌 공개](https://www.informit.com/articles/article.aspx?p=359417&seqNum=2))은 심을 이렇게 정의한다.

> 심은 그 자리를 편집하지 않고도 프로그램의 동작을 바꿀 수 있는 곳이다.

그리고 **모든 심에는 활성화 지점(enabling point)이 있다**. 어느 동작을 쓸지 결정하는 곳이다. Fowler 의 [LegacySeam](https://martinfowler.com/bliki/LegacySeam.html)도 이 정의를 인용하며, 심을 찾으면 의존성을 끊어 테스트를 넣을 수 있다고 설명한다.

| 심 종류 | 동작을 바꾸는 방법 | 활성화 지점 | 쓰이는 곳 |
|---|---|---|---|
| 전처리 심 | 매크로·헤더 치환 | 전처리기 정의 | C/C++ |
| 링크 심 | 다른 구현을 링크·클래스패스에 둠 | 빌드 설정 | C, Java 클래스패스 |
| 객체 심 | 호출 대상 객체를 다른 구현으로 교체 | 객체를 만드는 곳(생성자 인자 등) | 객체지향 언어 전반 |

책은 객체 심을 객체지향 언어에서 가장 유용한 심이라고 부른다. 의존성 주입(SE100 #036 에서 다룬다)은 객체 심의 활성화 지점을 생성자로 끌어올리는 일이다.

### 안전하게 의존성을 끊는 작은 기법들

테스트가 없는 상태에서 하는 리팩터링이므로 **IDE 자동 리팩터링이나 기계적 단계만** 쓴다.

| 기법 | 하는 일 |
|---|---|
| 매개변수로 빼내기 | 메서드 안에서 만들던 객체를 인자로 받고, 기존 호출부에는 기존 객체를 기본값으로 |
| 메서드 추출 후 오버라이드 | 문제 호출을 protected 메서드로 빼고, 테스트용 하위 클래스에서 오버라이드 |
| 싹 틔우기(sprout) | 새 기능은 테스트된 새 메서드·클래스로 작성하고 레거시에서는 호출 한 줄만 추가 |
| 감싸기(wrap) | 기존 메서드 이름을 바꾸고 같은 이름의 새 메서드가 이전 것 + 새 동작을 호출 |

### 큰 단위로 가면

모듈 하나를 넘어 시스템을 바꿀 때는 [Strangler Fig](https://martinfowler.com/bliki/StranglerFigApplication.html)(새 시스템이 옛 시스템을 점진적으로 대체)와 [Branch by Abstraction](https://martinfowler.com/bliki/BranchByAbstraction.html)(추상화 층을 세우고 그 뒤에서 구현을 교체)이 같은 원칙을 아키텍처 수준에서 적용한다. 변경 목표가 의존성 그물에 얽혀 있다면 Ola Ellnor·Daniel Brolund 의 *The Mikado Method*(Manning, 2014)처럼 시도와 되돌리기를 반복하며 선행 작업 그래프를 그리는 방법도 있다.

## 예제

### 레거시 함수

```python
# billing.py (레거시) — DB 와 현재 시각에 직접 묶여 있다
import datetime, db

def monthly_invoice(customer_id):
    c = db.fetch_customer(customer_id)
    usage = db.fetch_usage(customer_id)
    total = 0
    for u in usage:
        if u.kind == "call":
            total += u.minutes * (90 if c.plan == "basic" else 60)
        elif u.kind == "sms":
            total += 20 if c.plan == "basic" else 0
    if datetime.date.today().month == 12 and c.years >= 3:
        total = int(total * 0.9)            # 연말 장기 고객 할인
    return max(total, 1000 if c.plan == "basic" else 0)
```

### 1단계: 심 만들기 (매개변수로 빼내기, 기본값 유지)

```python
def monthly_invoice(customer_id, *, fetch_customer=db.fetch_customer,
                    fetch_usage=db.fetch_usage, today=datetime.date.today):
    c = fetch_customer(customer_id)
    usage = fetch_usage(customer_id)
    ...
    if today().month == 12 and c.years >= 3:
        ...
```

기존 호출부는 한 글자도 바뀌지 않는다. 활성화 지점은 키워드 인자다.

### 2단계: 특성 테스트로 현재 동작 고정

```python
import itertools, json, pathlib, datetime
from types import SimpleNamespace as NS
from billing import monthly_invoice

def run_grid():
    results = {}
    for plan, years, month, calls, sms in itertools.product(
            ["basic", "pro"], [0, 3], [6, 12], [0, 7, 40], [0, 5]):
        c = NS(plan=plan, years=years)
        usage = [NS(kind="call", minutes=calls), *[NS(kind="sms")] * sms]
        total = monthly_invoice("X",
                                fetch_customer=lambda _: c,
                                fetch_usage=lambda _: usage,
                                today=lambda: datetime.date(2026, month, 1))
        results[f"{plan}/{years}y/m{month}/call{calls}/sms{sms}"] = total
    return results

def test_characterization():
    golden = pathlib.Path("tests/golden/monthly_invoice.json")
    actual = run_grid()
    if not golden.exists():                 # 첫 실행: 현재 동작을 기록
        golden.write_text(json.dumps(actual, indent=1, sort_keys=True))
    assert actual == json.loads(golden.read_text())
```

입력 조합 48개의 출력이 골든 파일로 고정된다. 이 방식은 승인 테스트(approval test) 또는 골든 마스터라고도 불리며, [ApprovalTests](https://approvaltests.com/) 같은 라이브러리가 기록·비교·승인 흐름을 제공한다.

### 3단계: 안전망을 검증하고 리팩터링

안전망이 실제로 변경을 잡는지 확인하려면 일부러 코드를 망가뜨려 본다(예: `0.9` 를 `0.8` 로). 테스트가 실패해야 정상이다. 이 작업을 자동화한 것이 변이 테스트이며, Java 에는 [PIT](https://pitest.org/)가 있다. 그다음에야 요금표를 데이터로 빼고, 할인 규칙을 순수 함수로 추출한다. 연습용으로는 Emily Bache 의 [Gilded Rose Refactoring Kata](https://github.com/emilybache/GildedRose-Refactoring-Kata)가 널리 쓰인다.

## 흔한 오해와 함정

- **"특성 테스트에서 버그를 발견하면 바로 고친다."** 안전망을 치는 중에는 동작을 바꾸지 않는다. 버그는 기록해 두고, 안전망 완성 후 별도 커밋으로 테스트 기대값과 함께 고친다.
- **"골든 파일이 있으니 끝."** 입력 공간을 충분히 덮지 않으면 거짓 안심이다. 분기 경계값을 조합에 넣고, 커버리지와 변이 테스트로 확인한다.
- **"전부 새로 짜는 게 빠르다."** 레거시 코드 안의 예외 처리와 이상한 분기 상당수는 과거 장애의 흔적이다. 재작성은 그 지식을 버린다.
- **안전망 없이 수동 리팩터링.** 의존성을 끊는 첫 단계는 IDE 자동 리팩터링이나 기본값 있는 매개변수 추가처럼 동작 보존이 명백한 변경만 쓴다.
- **골든 파일에 비결정적 값.** 시각, 난수, 해시 순서가 들어가면 테스트가 흔들린다. 심으로 고정하거나 정렬·마스킹한다.

## 확인 문제

1. Feathers 가 정의한 레거시 코드는 무엇이며, "나이" 가 기준이 아닌 이유는?
2. 특성 테스트에서 "올바른 동작" 의 기준은 무엇인가? 일반 단위 테스트와 어떻게 다른가?
3. 심과 활성화 지점의 정의를 쓰고, 위 Python 예제에서 각각이 무엇인지 지적하라.
4. 변곡점에 테스트를 거는 이유는?

### 풀이

1. 테스트가 없는 코드. 변경이 동작을 바꿨는지 알려 줄 수단이 없다는 것이 문제의 본질이고, 이는 방금 쓴 코드에도 해당한다.
2. 코드가 지금(어제) 하는 동작 자체가 기준이다. 일반 테스트는 명세로부터 기대값을 정하지만, 특성 테스트는 관찰한 출력을 기대값으로 고정해 변경 감지에 쓴다.
3. 심: 그 자리를 편집하지 않고 동작을 바꿀 수 있는 곳(여기서는 `fetch_customer(...)`, `today()` 호출부). 활성화 지점: 어느 동작을 쓸지 결정하는 곳(함수의 키워드 인자).
4. 변경 대상 뒤의 어떤 변경도 변곡점에서 감지되거나 무해하므로, 의존성이 얽힌 내부 메서드 하나하나를 테스트하지 않고도 좁은 인터페이스 한 곳에서 안전망을 칠 수 있다.

## 더 읽을거리 (References)

- Michael Feathers, [Working Effectively With Legacy Code](https://objectmentor.com/resources/articles/WorkingEffectivelyWithLegacyCode.pdf), Object Mentor, 2002
- Michael Feathers, *Working Effectively with Legacy Code*, Prentice Hall, 2004 (서지 정보) / 발췌 [Testing Effectively With Legacy Code](https://www.informit.com/articles/article.aspx?p=359417), InformIT, 2005
- Martin Fowler, [LegacySeam](https://martinfowler.com/bliki/LegacySeam.html), [StranglerFigApplication](https://martinfowler.com/bliki/StranglerFigApplication.html), [BranchByAbstraction](https://martinfowler.com/bliki/BranchByAbstraction.html)
- Ola Ellnor, Daniel Brolund, *The Mikado Method*, Manning, 2014 (서지 정보)
- [ApprovalTests](https://approvaltests.com/), [PIT Mutation Testing](https://pitest.org/), [Gilded Rose Refactoring Kata](https://github.com/emilybache/GildedRose-Refactoring-Kata)
