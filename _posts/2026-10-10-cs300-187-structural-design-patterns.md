---
layout: post
title: "[CS300 #187] 디자인 패턴 2 — 구조 패턴: 객체를 감싸고 잇고 묶는 법"
date: 2026-10-10 21:07:00 +0900
categories: [cs]
tags: [cs300, software-engineering, design-patterns, adapter, decorator]
---

컴퓨터공학 300 주제 시리즈의 187번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

구조 패턴(structural patterns)은 클래스와 객체를 조합해 더 큰 구조를 만드는 방법이다. GoF 의 일곱 가지 — 어댑터, 브리지, 컴포지트, 데코레이터, 퍼사드, 플라이웨이트, 프록시 — 중 상당수는 "다른 객체를 **감싼다**" 는 같은 모양을 하고 있고, **감싸는 의도**로 구별된다.

## 왜 필요한가

현실의 코드는 혼자 있지 않다. 외부 결제 라이브러리, 오래된 사내 모듈, 클라우드 SDK 처럼 내가 고칠 수 없는 코드와 맞물려 돌아간다. 이들의 인터페이스는 내 코드가 원하는 모양과 다르고, 기능을 조금 덧붙이고 싶어도 원본을 수정할 수 없다.

구조 패턴은 원본을 건드리지 않고 그 위에 층을 하나 더 얹어서 문제를 푼다. 인터페이스를 맞추거나(어댑터), 기능을 덧붙이거나(데코레이터), 복잡함을 가리거나(퍼사드), 접근을 통제한다(프록시).

## 핵심 개념

### 1. 어댑터(Adapter)

호환되지 않는 인터페이스를 클라이언트가 기대하는 인터페이스로 **변환**한다. 해외여행용 전원 어댑터와 같다.

```
Client ──> Target 인터페이스
              ▲
           Adapter ──감싼다──> Adaptee (화씨를 돌려주는 레거시)
```

외부 라이브러리를 직접 부르지 않고 어댑터를 거치게 해 두면, 라이브러리를 교체할 때 어댑터 하나만 다시 쓰면 된다. 헥사고날 아키텍처(레이어드 아키텍처 글에서 다룬다)의 "어댑터" 가 바로 이 뜻이다.

### 2. 브리지(Bridge)

추상(무엇을 하는가)과 구현(어떻게 하는가)을 분리해 **둘을 독립적으로 확장**한다.
도형 종류(원, 사각형)와 렌더러(SVG, PNG)가 있을 때 상속으로만 풀면 `SvgCircle`, `PngCircle`, `SvgRect`, `PngRect` 처럼 곱셈으로 클래스가 늘어난다. 도형이 렌더러를 **필드로 가지게** 하면 도형 n 개 + 렌더러 m 개, 덧셈으로 끝난다.

### 3. 컴포지트(Composite)

개별 객체(잎)와 객체 묶음(가지)을 **같은 인터페이스**로 다룬다. 트리 구조에 쓴다.

```
Folder("root")
 ├─ File("a.txt", 120)
 ├─ Folder("img")
 │   ├─ File("x.png", 2048)
 │   └─ File("y.png", 1024)
 └─ Folder("empty")
```

`root.size()` 를 부르면 폴더는 자식들의 `size()` 를 더하고, 파일은 자기 크기를 돌려준다. 호출하는 쪽은 상대가 파일인지 폴더인지 신경 쓰지 않는다. UI 위젯 트리, 조직도, 수식 트리가 모두 이 모양이다.

### 4. 데코레이터(Decorator)

원본과 **같은 인터페이스**를 가진 래퍼로 감싸서 기능을 동적으로 덧붙인다. 래퍼를 여러 겹 쌓을 수 있다.

```
CachingSource(LoggingSource(RetryingSource(HttpSource())))
```

상속으로 `LoggingCachingRetryingHttpSource` 를 만드는 대신, 필요한 기능만 골라 겹친다. 자바의 `BufferedReader(new FileReader(...))` 가 교과서적인 예다.

파이썬의 `@decorator` 문법([PEP 318](https://peps.python.org/pep-0318/))은 이름이 같지만 정확히 같은 것은 아니다. 파이썬 데코레이터는 **함수나 클래스를 받아 다른 함수나 클래스를 돌려주는 문법적 장치**이고, GoF 데코레이터는 **객체 수준의 래핑 구조**다. 다만 "원래 것을 감싸 기능을 덧붙인다" 는 의도는 같아서, 로깅·재시도·캐싱 같은 용도로 둘 다 쓰인다. 함수 데코레이터를 만들 때는 [`functools.wraps`](https://docs.python.org/3/library/functools.html#functools.wraps)로 원래 함수의 이름과 문서 문자열을 보존하는 것이 관례다.

### 5. 퍼사드(Facade)

복잡한 하위 시스템 앞에 **단순한 창구** 하나를 둔다.

```
video.convert("in.mov", "out.mp4")
   └─> 내부: 코덱 선택, 디먹서, 비트레이트 계산, 오디오 믹서, 인코더 ...
```

하위 시스템을 숨기는 것이 아니라, 흔한 사용법을 위한 쉬운 길을 하나 더 내 주는 것이다. 세밀한 제어가 필요한 사용자는 여전히 하위 클래스를 직접 쓸 수 있다.

### 6. 플라이웨이트(Flyweight)

같은 값을 가진 객체가 대량으로 필요할 때, 변하지 않는 공통 상태(내재 상태)를 **공유**해 메모리를 아낀다. 문서 편집기에서 글자 하나하나가 글꼴 객체를 따로 갖지 않고 공유하는 식이다.
파이썬의 [`sys.intern`](https://docs.python.org/3/library/sys.html#sys.intern)은 같은 문자열을 하나의 객체로 공유하게 해 주는 함수로, 같은 발상이다.

### 7. 프록시(Proxy)

진짜 객체와 같은 인터페이스를 가진 **대리인**이 앞에 서서 접근을 제어한다. 목적에 따라 이름이 붙는다.

| 종류 | 하는 일 |
|---|---|
| 가상 프록시 | 진짜 객체 생성을 실제로 필요할 때까지 미룬다(지연 로딩) |
| 보호 프록시 | 권한을 검사한 뒤 넘긴다 |
| 원격 프록시 | 네트워크 너머의 객체를 로컬 객체처럼 보이게 한다(RPC 스텁) |
| 캐싱 프록시 | 결과를 저장해 두고 반복 호출을 막는다 |

### 감싸는 패턴들 구별하기

어댑터, 데코레이터, 프록시, 퍼사드는 코드 모양이 비슷해서 헷갈린다. **의도**로 구별한다.

| 패턴 | 인터페이스 | 의도 |
|---|---|---|
| 어댑터 | 바꾼다 | 안 맞는 것을 맞춘다 |
| 데코레이터 | 그대로 둔다 | 기능을 덧붙인다(여러 겹 가능) |
| 프록시 | 그대로 둔다 | 접근을 통제한다(생성·권한·원격·캐시) |
| 퍼사드 | 새로 만든다(더 단순하게) | 여러 객체를 한 창구로 묶는다 |

## 직접 해 보기

어댑터, 컴포지트, 데코레이터, 프록시와 파이썬 함수 데코레이터를 한 번에 돌려 본다.

```python
import functools, time

# 1) 어댑터: 외부 라이브러리의 다른 인터페이스를 우리 인터페이스에 맞춘다
class LegacyThermometer:              # 바꿀 수 없는 외부 코드
    def read_fahrenheit(self): return 98.6

class CelsiusAdapter:
    def __init__(self, legacy): self._legacy = legacy
    def celsius(self): return round((self._legacy.read_fahrenheit() - 32) * 5 / 9, 1)

print("어댑터:", CelsiusAdapter(LegacyThermometer()).celsius(), "C")

# 2) 컴포지트: 잎과 묶음을 같은 인터페이스로 다룬다
class File:
    def __init__(self, name, size): self.name, self.size_ = name, size
    def size(self): return self.size_

class Folder:
    def __init__(self, name, *children): self.name, self.children = name, list(children)
    def size(self): return sum(c.size() for c in self.children)   # 재귀

root = Folder("root", File("a.txt", 120),
              Folder("img", File("x.png", 2048), File("y.png", 1024)),
              Folder("empty"))
print("컴포지트: 전체 크기 =", root.size())

# 3) 데코레이터(GoF): 같은 인터페이스로 감싸 기능을 덧붙인다
class Source:
    def fetch(self, key): return f"value-of-{key}"

class LoggingSource:
    def __init__(self, inner): self.inner = inner
    def fetch(self, key):
        print(f"  [log] fetch({key})")
        return self.inner.fetch(key)

print("데코레이터:", LoggingSource(Source()).fetch("k1"))

# 4) 프록시: 진짜 객체 앞에서 접근을 제어한다(여기서는 캐시)
class SlowService:
    calls = 0
    def price(self, sku):
        SlowService.calls += 1
        time.sleep(0.05)
        return len(sku) * 1000

class CachingProxy:
    def __init__(self, real): self._real, self._cache = real, {}
    def price(self, sku):
        if sku not in self._cache:
            self._cache[sku] = self._real.price(sku)
        return self._cache[sku]

svc = CachingProxy(SlowService())
t0 = time.perf_counter()
for _ in range(10):
    svc.price("ABC")
print(f"프록시: 10번 호출, 실제 호출 {SlowService.calls}번, 걸린 시간 {time.perf_counter() - t0:.2f}초")

# 파이썬 데코레이터 문법 + functools.wraps
def timed(fn):
    @functools.wraps(fn)
    def wrapper(*a, **kw):
        t = time.perf_counter()
        try:
            return fn(*a, **kw)
        finally:
            print(f"  [timed] {fn.__name__} {time.perf_counter() - t:.3f}s")
    return wrapper

@timed
def work():
    """잠깐 일한다."""
    time.sleep(0.01)

work()
print("wraps 덕분에 이름·문서 유지:", work.__name__, "/", work.__doc__)
```

실행 결과(시간 값은 실행마다 조금씩 다르다):

```
어댑터: 37.0 C
컴포지트: 전체 크기 = 3192
  [log] fetch(k1)
데코레이터: value-of-k1
프록시: 10번 호출, 실제 호출 1번, 걸린 시간 0.05초
  [timed] work 0.010s
wraps 덕분에 이름·문서 유지: work / 잠깐 일한다.
```

프록시를 거친 10번의 호출 중 실제 서비스에 닿은 것은 첫 번째 한 번뿐이고, 걸린 시간도 느린 호출 한 번 분량이다. 호출하는 쪽 코드는 `svc.price(...)` 그대로다. `functools.wraps` 를 빼고 다시 돌려 보면 `work.__name__` 이 `wrapper` 로 바뀌는 것을 확인할 수 있다. 로그와 디버거에서 함수 이름이 사라지는 흔한 실수다.

## 현업에서는

- **안티부패 계층(Anti-Corruption Layer)은 어댑터다.** 외부 시스템의 이상한 필드명과 상태 코드가 내 도메인 코드로 번지지 않게, 경계에서 어댑터로 번역한다.
- **HTTP 미들웨어는 데코레이터 체인이다.** 인증 → 로깅 → 압축 → 실제 핸들러 순서로 겹겹이 감싸는 웹 프레임워크의 미들웨어 구조가 데코레이터 패턴 그대로다.
- **리버스 프록시와 서비스 메시.** 홈랩 클러스터의 Ingress 컨트롤러는 이름 그대로 프록시다. 실제 파드 앞에 서서 TLS 종료, 경로 라우팅, 접근 제어를 한다. 서비스 메시의 사이드카 프록시도 같은 역할을 파드마다 한다.
- **ORM 의 지연 로딩은 가상 프록시다.** `order.customer` 에 접근하는 순간 쿼리가 나가는 것은 프록시가 진짜 객체를 늦게 만들기 때문이다. 반복문 안에서 이걸 모르고 쓰면 N+1 쿼리 문제가 생긴다.

## 확인 문제

1. 어댑터와 데코레이터는 둘 다 객체를 감싼다. 인터페이스 관점에서 둘의 차이는?
2. 브리지 패턴이 "곱셈으로 늘어나는 클래스" 를 "덧셈" 으로 바꾸는 원리는?
3. 컴포지트 패턴에서 호출자가 파일과 폴더를 구별하지 않아도 되는 이유는?
4. 프록시의 종류를 세 가지 들라.
5. 함수 데코레이터에서 `functools.wraps` 를 빼면 어떤 문제가 생기는가?

### 풀이

1. 어댑터는 인터페이스를 다른 모양으로 바꾸고, 데코레이터는 같은 인터페이스를 유지한 채 기능을 덧붙인다.
2. 상속 계층 하나에 두 축(추상·구현)을 섞지 않고, 구현 축을 필드(합성)로 분리해 두 계층을 독립적으로 늘린다.
3. 둘 다 같은 인터페이스(`size()`)를 구현하므로, 호출자는 그 메서드만 부르면 된다.
4. 가상(지연 생성) 프록시, 보호(권한) 프록시, 원격 프록시, 캐싱 프록시 중 셋.
5. 감싼 함수의 `__name__`, `__doc__` 등 메타데이터가 내부 `wrapper` 의 것으로 바뀌어, 로그·디버깅·문서 도구에서 원래 함수 정보가 사라진다.

## 더 읽을거리 (References)

- Erich Gamma, Richard Helm, Ralph Johnson, John Vlissides, *Design Patterns: Elements of Reusable Object-Oriented Software*, Addison-Wesley, 1994 (서지 정보)
- Python 문서, [functools.wraps](https://docs.python.org/3/library/functools.html#functools.wraps)
- [PEP 318 — Decorators for Functions and Methods](https://peps.python.org/pep-0318/)
- Python 문서, [sys.intern](https://docs.python.org/3/library/sys.html#sys.intern)
