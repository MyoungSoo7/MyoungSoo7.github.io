---
layout: post
title: "[CS300 #031] 함수형 프로그래밍 — 불변성과 순수 함수"
date: 2026-10-10 18:31:00 +0900
categories: [cs]
tags: [cs300, programming, functional-programming, immutability, pure-function]
---

컴퓨터공학 300 주제 시리즈의 031번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

순수 함수는 같은 입력에 언제나 같은 출력을 내고 바깥 세계를 바꾸지 않는 함수이며, 불변 데이터는 만든 뒤 바뀌지 않는 값이다. 이 둘을 기본으로 삼으면 코드를 조각조각 따로 이해하고 테스트하고 병렬로 돌릴 수 있다.

## 왜 필요한가

"어제는 됐는데 오늘은 안 된다", "테스트를 혼자 돌리면 통과하는데 같이 돌리면 실패한다", "멀티스레드에서만 가끔 값이 틀린다". 이런 버그의 상당수는 **공유된 가변 상태**에서 나온다. 어떤 함수가 전역 변수나 인자로 받은 객체를 몰래 바꾸면, 그 함수의 결과는 호출 순서와 타이밍에 따라 달라진다.

함수형 프로그래밍은 Haskell 이나 Scala 를 써야만 하는 것이 아니다. Python, Java, JavaScript 에서도 "되도록 순수하게, 되도록 불변으로"라는 원칙만 지켜도 이런 버그가 크게 준다. 이어지는 #032 고차 함수, #035 비동기, 파트 뒤쪽의 동시성 주제가 모두 이 원칙에 기대고 있다.

## 핵심 개념

### 순수 함수

함수가 다음 두 조건을 만족하면 **순수(pure)** 하다.

1. **결정적**: 같은 인자에 대해 언제나 같은 값을 돌려준다. 현재 시각, 난수, 전역 변수, 파일 내용 같은 숨은 입력에 기대지 않는다.
2. **부수 효과 없음**: 반환값 말고는 아무것도 바꾸지 않는다. 전역 변수 수정, 인자 객체 수정, 파일·네트워크·DB 쓰기, 화면 출력이 모두 부수 효과다.

| 함수 | 순수한가 | 이유 |
|---|---|---|
| `len(xs)` | 예 | 입력만 보고, 아무것도 안 바꾼다 |
| `sorted(xs)` | 예 | 새 리스트를 만든다 |
| `xs.sort()` | 아니오 | 인자 `xs` 를 제자리에서 바꾼다 |
| `random.random()` | 아니오 | 숨은 상태(난수 생성기)에 의존하고 바꾼다 |
| `datetime.now()` | 아니오 | 호출 시각이 숨은 입력이다 |
| `print(x)` | 아니오 | 출력이라는 부수 효과 |

### 참조 투명성

순수 함수 호출은 **그 결과값으로 바꿔 써도 프로그램의 의미가 변하지 않는다.** 이를 참조 투명성이라 한다. `add(2, 3)` 을 어디서든 `5` 로 바꿀 수 있다. 덕분에 세 가지가 쉬워진다.

- **추론**: 함수 하나만 보고 동작을 확정할 수 있다.
- **테스트**: 목(mock)이나 준비 상태 없이 입력과 기대 출력만 있으면 된다.
- **최적화**: 결과를 캐시해도(메모이제이션, #024) 안전하고, 호출 순서를 바꾸거나 병렬로 돌려도 안전하다.

Python 공식 함수형 프로그래밍 HOWTO 는 함수형 스타일의 이점으로 형식적 증명 가능성, 모듈성, 조합 가능성, 디버깅·테스트 용이성을 든다([Functional Programming HOWTO](https://docs.python.org/3/howto/functional.html)).

### 불변성

불변 객체는 만든 뒤 상태를 바꿀 수 없다. 값을 "바꾸고" 싶으면 **새 값을 만든다.**

- 공유해도 안전하다. 누구도 못 바꾸니 방어적 복사가 필요 없다(#025).
- 스레드 간 동기화가 필요 없다. 읽기만 하는 데이터에는 경쟁 상태가 없다.
- 해시 키로 쓸 수 있다. 바뀌지 않으니 해시값도 바뀌지 않는다.
- 이전 버전이 남는다. 실행 취소, 시간 여행 디버깅, 이벤트 소싱이 자연스럽다.

Python 은 `tuple`, `frozenset`, `str`, `int` 가 불변이고, 직접 만든 클래스는 `@dataclass(frozen=True)` 로 불변으로 만들 수 있다. 속성에 대입하면 `FrozenInstanceError` 가 나며, `dataclasses.replace` 로 일부 필드만 바꾼 새 객체를 만든다([dataclasses](https://docs.python.org/3/library/dataclasses.html)).

주의: 불변 컨테이너 안에 가변 객체가 있으면 그 부분은 바뀐다. `(1, [2, 3])` 은 튜플이지만 안의 리스트는 수정 가능하고, 그래서 해시도 안 된다. 진짜 불변은 **깊은** 불변이다.

### 새로 만들면 느리지 않은가

매번 전체를 복사하면 느리다. 함수형 언어는 **영속 자료구조(persistent data structure)** 로 이를 해결한다. 새 버전이 바뀌지 않은 부분을 이전 버전과 **공유**한다(구조적 공유). 예를 들어 불변 연결 리스트 앞에 원소를 붙이면 새 노드 하나만 만들고 꼬리는 그대로 공유한다. 오카사키(Okasaki)의 『Purely Functional Data Structures』가 이 분야의 표준 교재다.

```
v1:        [2] -> [3] -> nil
v2: [1] ---^              (v2 = 1 :: v1, 노드 하나만 새로)
```

### 함수형 코어, 명령형 껍데기

현실의 프로그램은 DB 에 쓰고, 화면에 출력하고, 네트워크로 보내야 한다. 부수 효과를 없앨 수는 없다. 대신 **가두는** 것이 실용적인 전략이다.

```
 ┌───── 명령형 껍데기 (I/O, DB, 시간, 난수) ─────┐
 │   입력 읽기 → [ 순수 코어: 계산·판단·변환 ] → 결과 쓰기 │
 └──────────────────────────────────────────────┘
```

비즈니스 규칙(할인 계산, 상태 전이, 검증)은 순수 함수로 쓰고, I/O 는 가장자리에 모은다. 핵심 로직은 빠른 단위 테스트로, 껍데기는 소수의 통합 테스트로 검증한다.

### 역사적 배경

1977년 튜링상 수상 강연을 바탕으로 한 배커스(Backus)의 1978년 논문 "Can Programming Be Liberated from the von Neumann Style?"은 변수 대입 중심의 명령형 스타일을 비판하고 함수 조합 중심의 프로그래밍을 제안했다. 이후 ML, Haskell 같은 언어가 이 흐름을 이었고, 지금은 주류 언어들이 람다, 불변 컬렉션, 스트림 API 형태로 그 아이디어를 흡수했다.

## 직접 해 보기

Python 3.12.3 에서 실행:

```python
from dataclasses import dataclass, replace, FrozenInstanceError

@dataclass(frozen=True)
class Point:
    x: int
    y: int

p = Point(1, 2)
p.x = 10            # FrozenInstanceError: cannot assign to field 'x'
q = replace(p, x=10)
print(p, q, p == Point(1, 2), hash(p) == hash(Point(1, 2)))
# Point(x=1, y=2) Point(x=10, y=2) True True

total = 0
def add_impure(x):
    global total
    total += x
    return total
print(add_impure(5), add_impure(5))   # 5 10   같은 입력, 다른 출력

def add_pure(acc, x):
    return acc + x
print(add_pure(0, 5), add_pure(0, 5)) # 5 5

def append_bad(xs, x):
    xs.append(x); return xs           # 인자를 바꾼다
def append_good(xs, x):
    return xs + [x]                   # 새 리스트

a = [1]
b = append_good(a, 2); print(a, b)    # [1] [1, 2]
c = append_bad(a, 3);  print(a, c, a is c)   # [1, 3] [1, 3] True

t = (1, [2, 3])
t[1].append(4); print(t)              # (1, [2, 3, 4])  얕은 불변
hash(t)                               # TypeError: unhashable type: 'list'
```

## 현업에서는

- **리덕스·리액트 상태 관리**: 상태를 제자리에서 바꾸지 않고 새 객체를 만들어야 변경 감지(참조 비교)가 동작한다. 불변성이 라이브러리 계약의 일부다.
- **데이터 파이프라인**: Spark 같은 분산 처리 엔진은 불변 데이터셋에 변환을 쌓는 모델을 쓴다. 변환이 순수하면 실패한 파티션을 다시 계산해 복구할 수 있다.
- **설정과 인프라**: 쿠버네티스에서 ConfigMap 을 `immutable: true` 로 표시하면 실수로 인한 변경을 막고([ConfigMaps](https://kubernetes.io/docs/concepts/configuration/configmap/)), 바꿀 때는 새 이름으로 만들어 롤아웃한다. 컨테이너 이미지도 태그를 덮어쓰지 않고 새 태그(또는 다이제스트)로 배포하는 것이 같은 원칙이다.
- **테스트 속도**: 할인·세금·정산 규칙을 순수 함수로 뽑아내면 DB 없이 수천 개 경우를 몇 초에 검증할 수 있다.

## 확인 문제

1. 순수 함수의 두 조건은?
2. `def greet(): return f"Hello at {time.time()}"` 은 순수한가?
3. 참조 투명성이 메모이제이션을 안전하게 만드는 이유는?
4. `frozen=True` 데이터클래스에 리스트 필드가 있으면 완전히 불변인가?
5. "함수형 코어, 명령형 껍데기" 구조가 테스트에 유리한 이유는?

### 풀이

1. 같은 입력에 같은 출력(결정성), 반환값 외의 부수 효과 없음.
2. 아니다. 현재 시각이라는 숨은 입력에 의존해 호출마다 결과가 다르다.
3. 같은 인자에 결과가 항상 같고 호출이 아무것도 바꾸지 않으므로, 저장된 결과로 호출을 대체해도 프로그램 의미가 같다.
4. 아니다. 필드에 다른 리스트를 대입하는 것은 막지만 그 리스트의 내용은 바꿀 수 있다. `tuple` 등 불변 타입을 써야 깊은 불변이 된다.
5. 핵심 로직이 입력과 출력만으로 검증되므로 목·DB 준비 없이 빠르고 많은 단위 테스트를 쓸 수 있고, I/O 부분만 소수의 통합 테스트로 확인하면 된다.

## 더 읽을거리 (References)

- Python Docs, [Functional Programming HOWTO](https://docs.python.org/3/howto/functional.html)
- Python Docs, [dataclasses — frozen instances](https://docs.python.org/3/library/dataclasses.html)
- John Backus, "Can Programming Be Liberated from the von Neumann Style? A Functional Style and Its Algebra of Programs", CACM 21(8), 1978
- Chris Okasaki, *Purely Functional Data Structures*, Cambridge University Press, 1998
