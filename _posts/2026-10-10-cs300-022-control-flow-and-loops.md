---
layout: post
title: "[CS300 #022] 제어 흐름과 반복문 — 순차·선택·반복 세 가지로 충분하다"
date: 2026-10-10 18:22:00 +0900
categories: [cs]
tags: [cs300, programming, control-flow, loop, structured-programming]
---

컴퓨터공학 300 주제 시리즈의 022번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

프로그램의 실행 순서는 순차·선택·반복 세 가지 구조로 모두 표현할 수 있고, 반복문을 바르게 쓰는 핵심은 "언제 끝나는가"와 "매 바퀴마다 무엇이 참으로 유지되는가"를 아는 것이다.

## 왜 필요한가

CPU 는 기본적으로 다음 명령을 실행하고, 조건에 따라 다른 주소로 점프할 뿐이다. 고급 언어의 `if`, `for`, `while` 은 이 점프를 사람이 이해할 수 있는 모양으로 묶은 것이다. 묶는 방식이 엉성하면 코드는 어디로 튈지 모르는 덩어리가 된다.

반복문은 버그가 가장 많이 숨는 곳이기도 하다. 한 칸 어긋나는 off-by-one, 끝나지 않는 루프, 순회 중인 컬렉션을 수정하는 실수. 이 글은 제어 흐름을 구조적으로 보는 법과, 반복문을 증명하듯 쓰는 법을 정리한다.

## 핵심 개념

### 구조적 프로그래밍

1966년 뵘(Böhm)과 야코피니(Jacopini)는 임의의 흐름도가 순차, 선택, 반복 세 가지 구조의 조합으로 바뀔 수 있음을 보였다. 1968년 다익스트라는 CACM 에 보낸 짧은 글 "Go To Statement Considered Harmful"에서 무제한 `goto` 가 프로그램의 진행 상태를 텍스트로부터 읽어 내기 어렵게 만든다고 주장했다([EWD215 원문 PDF](https://www.cs.utexas.edu/~EWD/ewd02xx/EWD215.PDF)). 오늘날 대부분 언어가 `goto` 를 없애거나 제한한 배경이다.

```
 순차            선택                  반복
 [A]            <조건>                <조건> ──아니오──> 탈출
  |            예/    \아니오          |예
 [B]          [A]     [B]             [본문]
  |             \     /                 |
 [C]            [ 합류 ]            ────┘(조건으로 복귀)
```

세 구조 모두 **입구 하나, 출구 하나**다. 그래서 블록 단위로 떼어 생각할 수 있다. `break`, `continue`, 이른 `return` 은 출구를 늘리지만 범위가 한 블록으로 묶여 있어 실무에서는 허용되는 절충이다.

### 선택: if 와 패턴 매칭

`if/elif/else` 는 위에서부터 조건을 하나씩 검사한다. 조건이 겹치면 먼저 나온 쪽이 이긴다. 그래서 범위 조건은 좁은 것부터, 혹은 겹치지 않게 써야 한다.

Python 3.10 부터는 구조적 패턴 매칭 `match` 가 들어왔다([PEP 634](https://peps.python.org/pep-0634/)). 단순한 값 분기뿐 아니라 리스트·딕셔너리·클래스의 모양을 분해하면서 분기할 수 있다. C 의 `switch` 와 달리 다음 `case` 로 흘러내리는(fall-through) 동작이 없다.

### 반복: while 과 for

| 형태 | 언제 쓰나 | 종료 조건 |
|---|---|---|
| `while 조건` | 반복 횟수를 미리 모를 때 | 조건이 거짓이 될 때 |
| 카운터 `for (i=0; i<n; i++)` | 인덱스가 필요할 때(C·Java) | `i` 가 `n` 에 도달 |
| 순회 `for x in 컬렉션` | 원소를 하나씩 볼 때 | 반복자가 소진될 때 |

Python 의 `for` 는 카운터 루프가 아니라 반복자 프로토콜 위에서 동작하는 순회 루프다. `for x in obj` 는 `iter(obj)` 로 반복자를 얻고 `StopIteration` 이 날 때까지 `next()` 를 부른다([The for statement](https://docs.python.org/3/reference/compound_stmts.html#the-for-statement)).

### for-else

Python 의 `for`/`while` 에는 `else` 절이 붙을 수 있다. 루프가 `break` 없이 끝났을 때만 실행된다. "찾지 못했을 때"를 깃발 변수 없이 쓸 수 있다. 이름이 직관과 달라 헷갈리므로, 쓸 때는 주석을 다는 편이 낫다.

### 루프 불변식

반복문이 맞다는 것을 확신하는 도구가 **루프 불변식(loop invariant)** 이다. 매 바퀴 시작 시점에 항상 참인 명제다. 다음 세 가지를 보이면 루프가 옳다.

1. **초기화**: 첫 바퀴 전에 불변식이 참이다.
2. **유지**: 한 바퀴를 돌아도 불변식이 계속 참이다.
3. **종료**: 루프가 끝나면 불변식과 종료 조건을 합쳐 원하는 결과가 나온다.

여기에 **종료성**을 따로 보여야 한다. 매 바퀴 줄어드는 음이 아닌 정수(변량, variant)를 찾으면 된다. 이진 탐색이라면 `hi - lo` 가 그 역할을 한다.

### 흔한 실수

- **off-by-one**: `<` 와 `<=` 를 섞는다. 반열린 구간 `[lo, hi)` 를 일관되게 쓰면 많이 줄어든다.
- **무한 루프**: `while` 본문에서 조건에 쓰인 변수를 갱신하지 않는다.
- **순회 중 수정**: 리스트를 돌면서 원소를 지우면 인덱스가 밀려 일부를 건너뛴다.

## 직접 해 보기

```python
def find_first_negative(xs):
    for i, x in enumerate(xs):
        if x < 0:
            print("found at", i)
            break
    else:                       # break 없이 끝났을 때만
        print("no negative")

find_first_negative([3, 1, -2, 5])   # found at 2
find_first_negative([3, 1, 2])       # no negative

def http_class(status):
    match status:
        case 200 | 201 | 204:
            return "success"
        case 301 | 302:
            return "redirect"
        case int(s) if 400 <= s < 500:
            return "client error"
        case int(s) if 500 <= s < 600:
            return "server error"
        case _:
            return "unknown"

print([http_class(s) for s in (200, 302, 404, 503, 99)])
# ['success', 'redirect', 'client error', 'server error', 'unknown']

def lower_bound(a, target):
    # 불변식: a[:lo] < target <= a[hi:]  (구간 [lo, hi) 가 미정)
    lo, hi = 0, len(a)
    while lo < hi:              # 변량 hi - lo 가 매번 줄어든다
        mid = (lo + hi) // 2
        if a[mid] < target:
            lo = mid + 1
        else:
            hi = mid
    return lo                   # lo == hi: target 이 들어갈 첫 위치

print(lower_bound([1, 3, 5, 7, 9], 7), lower_bound([1, 3, 5, 7, 9], 4))  # 3 2
```

순회 중 수정이 어떻게 깨지는지도 직접 확인해 보자.

```python
xs = [2, 4, 6, 8]
for x in xs:
    if x % 2 == 0:
        xs.remove(x)
print(xs)                                   # [4, 8]  모두 짝수인데 둘이 남는다
print([x for x in [2, 4, 6, 8] if x % 2])   # []  새 리스트를 만드는 쪽이 안전
```

첫 바퀴에 2 를 지우면 4 가 인덱스 0 으로 당겨지고, 반복자는 인덱스 1 로 넘어가 6 을 본다. 4 는 검사조차 되지 않았다. 위 코드는 Python 3.12 에서 실행해 출력을 확인했다.

## 현업에서는

- **재시도 루프**: 외부 API 호출을 `while` 로 재시도할 때 최대 횟수와 백오프를 반드시 둔다. 종료 조건이 "성공할 때까지"뿐이면 장애가 무한 재시도 폭풍이 된다. 쿠버네티스도 실패한 컨테이너를 재시작할 때 지수 백오프를 쓰고 상한을 둔다([Pod Lifecycle](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/)).
- **조정 루프**: 쿠버네티스 컨트롤러는 "현재 상태를 관찰 → 원하는 상태와 비교 → 차이를 줄이는 행동"을 끝없이 반복한다. 끝나지 않는 것이 의도된 루프다. 이때도 한 바퀴의 작업은 짧고 멱등적이어야 한다.
- **페이지네이션**: 커서 기반 API 를 `while cursor:` 로 돌 때, 서버가 같은 커서를 돌려주는 버그가 있으면 무한 루프가 된다. 직전 커서와 같으면 멈추는 방어 코드를 넣는다.
- **이른 반환**: 깊게 중첩된 `if` 보다 조건이 안 맞으면 먼저 `return` 하는 가드 절이 읽기 쉽다. 코드 리뷰에서 자주 나오는 지적이다.

## 확인 문제

1. 구조적 프로그래밍의 세 가지 기본 구조는 무엇인가?
2. Python 에서 `for ... else` 의 `else` 는 언제 실행되는가?
3. 위 `lower_bound` 에서 `hi = mid - 1` 로 바꾸면 어떤 문제가 생기는가?
4. `while n != 1:` 형태의 콜라츠 반복이 모든 양의 정수에서 끝난다는 것이 증명되어 있는가?
5. 리스트를 순회하며 조건에 맞는 원소를 지우는 안전한 방법 두 가지를 들라.

### 풀이

1. 순차, 선택, 반복.
2. 루프가 `break` 없이 정상 종료했을 때. 반복 대상이 비어 있어도 실행된다.
3. 반열린 구간 불변식이 깨진다. `a[mid] >= target` 인 `mid` 자신이 답일 수 있는데 구간에서 빠져 버려 정답을 놓친다.
4. 아니다. 콜라츠 추측은 아직 미해결 문제다. 그래서 이 루프에는 증명된 변량이 없다.
5. 조건을 뒤집은 새 리스트를 만든다(리스트 내포·`filter`). 또는 복사본 `xs[:]` 을 순회하며 원본에서 지운다. 뒤에서부터 인덱스로 지우는 방법도 있다.

## 더 읽을거리 (References)

- Python Language Reference, [Compound statements](https://docs.python.org/3/reference/compound_stmts.html) — `if`, `while`, `for`, `match` 의 정확한 의미
- Python Tutorial, [More Control Flow Tools](https://docs.python.org/3/tutorial/controlflow.html)
- Edsger W. Dijkstra, [Go To Statement Considered Harmful (EWD215)](https://www.cs.utexas.edu/~EWD/ewd02xx/EWD215.PDF), CACM 11(3), 1968
- Corrado Böhm, Giuseppe Jacopini, "Flow diagrams, Turing machines and languages with only two formation rules", CACM 9(5), 1966
