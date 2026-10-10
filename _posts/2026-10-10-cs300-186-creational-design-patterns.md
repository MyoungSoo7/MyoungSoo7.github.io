---
layout: post
title: "[CS300 #186] 디자인 패턴 1 — 생성 패턴: 객체를 누가, 어떻게 만들 것인가"
date: 2026-10-10 21:06:00 +0900
categories: [cs]
tags: [cs300, software-engineering, design-patterns, factory, builder]
---

컴퓨터공학 300 주제 시리즈의 186번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

생성 패턴(creational patterns)은 객체를 만드는 코드를 사용하는 코드에서 떼어 내는 설계 방법들이다. GoF 책의 다섯 가지 — 싱글턴, 팩토리 메서드, 추상 팩토리, 빌더, 프로토타입 — 는 모두 "`new` 를 어디에 둘 것인가" 에 대한 서로 다른 답이다.

## 왜 필요한가

`EmailNotifier()` 처럼 구체 클래스 이름을 직접 써서 객체를 만들면, 그 줄을 쓴 코드는 그 클래스에 묶인다. 알림 수단이 SMS 로 바뀌면 생성하는 모든 곳을 찾아 고쳐야 한다. 앞 글의 의존성 역전 원칙은 "추상에 의존하라" 고 했지만, 결국 누군가는 구체 객체를 만들어야 한다.

생성 패턴은 그 "누군가" 를 한곳에 모은다. 생성 책임을 분리하면 세 가지를 얻는다.

- 사용하는 쪽은 구체 타입을 몰라도 된다.
- 생성 규칙(검증, 기본값, 캐싱)을 한 곳에서 관리한다.
- 테스트에서 가짜 객체로 갈아 끼우기 쉬워진다.

## 핵심 개념

### GoF 와 패턴의 형식

1994년 Erich Gamma, Richard Helm, Ralph Johnson, John Vlissides 네 사람(Gang of Four, GoF)이 *Design Patterns: Elements of Reusable Object-Oriented Software* 에서 23개의 패턴을 정리했다. 생성 5개, 구조 7개, 행위 11개다. 이번 글부터 세 편에 걸쳐 차례로 다룬다.

각 패턴은 이름, 문제(언제 쓰는가), 해법(구조), 결과(장단점)로 기술된다. 패턴은 복사해 붙일 코드가 아니라 **이름 붙은 설계 아이디어**다. "여기는 빌더로 가죠" 한마디로 구조 전체를 전달하는 것이 패턴의 가장 큰 효용이다.

### 1. 싱글턴(Singleton)

클래스의 인스턴스가 하나만 있도록 보장하고, 그 인스턴스에 전역 접근점을 제공한다.

```
Config.instance() ──> 항상 같은 Config 객체
```

설정, 로거, 커넥션 풀처럼 "하나만 있어야 하는 것" 에 쓴다. 하지만 사실상 전역 변수라서 숨은 의존을 만들고, 테스트 사이에 상태가 새는 문제가 있다. 오늘날에는 싱글턴 클래스를 직접 만들기보다, 애플리케이션 시작 시 하나를 만들어 의존성 주입으로 나눠 주는 방식을 더 권한다.

파이썬에서는 **모듈 자체가 싱글턴**이다. 모듈은 한 번만 import 되어 `sys.modules` 에 캐시되기 때문이다. [파이썬 공식 FAQ](https://docs.python.org/3/faq/programming.html#how-do-i-share-global-variables-across-modules)도 모듈 간 전역 상태를 공유하는 표준 방법으로 설정용 모듈을 쓰라고 안내한다.

### 2. 팩토리 메서드(Factory Method)

객체를 만드는 인터페이스는 정의하되, 어떤 클래스의 인스턴스를 만들지는 하위 클래스(또는 등록된 생성 함수)가 결정한다.

```
           Creator
     create_product() ─────> Product (추상)
          ▲                       ▲
   ConcreteCreator ─────> ConcreteProduct
```

사용하는 쪽은 `create_exporter("csv")` 만 부르고, 반환된 객체가 `CsvExporter` 라는 사실을 모른다. 새 형식을 추가할 때 기존 코드를 고치지 않아도 되므로 개방-폐쇄 원칙과 잘 맞는다.

### 3. 추상 팩토리(Abstract Factory)

**서로 관련된 객체들의 묶음**을 일관되게 만들어 주는 인터페이스다.

| 팩토리 | 버튼 | 체크박스 | 스크롤바 |
|---|---|---|---|
| `LightThemeFactory` | 밝은 버튼 | 밝은 체크박스 | 밝은 스크롤바 |
| `DarkThemeFactory` | 어두운 버튼 | 어두운 체크박스 | 어두운 스크롤바 |

팩토리 하나를 고르면 그 계열의 부품만 나오므로 "밝은 버튼에 어두운 체크박스" 같은 섞임이 생기지 않는다. 클라우드 SDK 에서 "AWS 용 스토리지·큐·DB 클라이언트 묶음" 과 "GCP 용 묶음" 을 바꿔 끼우는 구조가 같은 아이디어다.

### 4. 빌더(Builder)

복잡한 객체의 **생성 과정**을 단계로 나누고, 같은 과정으로 다른 표현을 만들 수 있게 한다. 실무에서는 선택 항목이 많은 객체를 읽기 쉽게 조립하는 용도로 주로 쓴다.

```
# 생성자 인자가 10개라면 순서를 기억할 수 없다
HttpRequest("POST", url, None, None, 3, True, False, ...)

# 빌더는 이름 붙은 단계로 조립하고, 마지막 build() 에서 검증한다
RequestBuilder(url).method("POST").header(...).timeout(3).build()
```

`build()` 가 완성된 객체를 한 번에 돌려주므로, 반쯤 만들어진 불완전한 객체가 밖으로 새지 않는다. 결과 객체를 불변으로 만들기도 쉽다.

### 5. 프로토타입(Prototype)

미리 만들어 둔 원본을 **복제**해서 새 객체를 만든다. 생성 비용이 크거나, 설정 조합이 많아 클래스로 일일이 나누기 어려울 때 쓴다.
복제할 때는 얕은 복사와 깊은 복사의 차이를 반드시 이해해야 한다. 파이썬 [`copy` 모듈](https://docs.python.org/3/library/copy.html) 문서는 얕은 복사가 새 복합 객체를 만들되 안의 객체는 **참조를 그대로 넣고**, 깊은 복사는 안의 객체까지 재귀적으로 복사한다고 설명한다.

### 한눈에 비교

| 패턴 | 핵심 질문 | 쓰는 장면 |
|---|---|---|
| 싱글턴 | 하나만 있어야 하나? | 설정, 공유 자원 (가능하면 DI 로 대체) |
| 팩토리 메서드 | 어떤 구체 타입을 만들지 미뤄야 하나? | 플러그인, 형식별 처리기 |
| 추상 팩토리 | 관련 객체 묶음을 일관되게 바꿔야 하나? | 테마, 플랫폼별 클라이언트 묶음 |
| 빌더 | 생성 인자가 많고 검증이 필요한가? | HTTP 요청, 쿼리, 테스트 데이터 |
| 프로토타입 | 원본을 복제하는 편이 싼가? | 템플릿 문서, 게임 오브젝트 |

## 직접 해 보기

팩토리 메서드(등록형), 빌더, 프로토타입을 한 파일에서 돌려 본다.

```python
import copy
from dataclasses import dataclass, field

# 1) 팩토리 메서드(등록형): 새 종류는 등록만 하면 된다
EXPORTERS = {}
def exporter(fmt):
    def register(cls):
        EXPORTERS[fmt] = cls
        return cls
    return register

@exporter("csv")
class CsvExporter:
    def export(self, rows): return "\n".join(",".join(map(str, r)) for r in rows)

@exporter("md")
class MarkdownExporter:
    def export(self, rows): return "\n".join("| " + " | ".join(map(str, r)) + " |" for r in rows)

def create_exporter(fmt):
    try:
        return EXPORTERS[fmt]()
    except KeyError:
        raise ValueError(f"지원하지 않는 형식: {fmt}") from None

rows = [("id", "name"), (1, "kim")]
for fmt in ("csv", "md"):
    print(f"[{fmt}]\n{create_exporter(fmt).export(rows)}")

# 2) 빌더: 선택 항목이 많은 객체를 단계적으로 조립하고 마지막에 검증
@dataclass(frozen=True)
class HttpRequest:
    method: str
    url: str
    headers: tuple
    timeout: float

class RequestBuilder:
    def __init__(self, url):
        self._url, self._method, self._headers, self._timeout = url, "GET", [], 10.0
    def method(self, m):       self._method = m; return self
    def header(self, k, v):    self._headers.append((k, v)); return self
    def timeout(self, sec):    self._timeout = sec; return self
    def build(self):
        if self._method == "POST" and not any(k == "Content-Type" for k, _ in self._headers):
            raise ValueError("POST 에는 Content-Type 이 필요하다")
        return HttpRequest(self._method, self._url, tuple(self._headers), self._timeout)

req = (RequestBuilder("https://example.com/api")
       .method("POST").header("Content-Type", "application/json").timeout(3).build())
print(req)

# 3) 프로토타입: 만들어 둔 원본을 복제해서 조금만 바꾼다
@dataclass
class Doc:
    title: str
    tags: list = field(default_factory=list)

template = Doc("주간 보고", ["report"])
shallow = copy.copy(template)
deep = copy.deepcopy(template)
shallow.tags.append("week41")
deep.tags.append("week42")
print("원본:", template.tags, "| 얕은 복사본:", shallow.tags, "| 깊은 복사본:", deep.tags)
```

실행 결과:

```
[csv]
id,name
1,kim
[md]
| id | name |
| 1 | kim |
HttpRequest(method='POST', url='https://example.com/api', headers=(('Content-Type', 'application/json'),), timeout=3)
원본: ['report', 'week41'] | 얕은 복사본: ['report', 'week41'] | 깊은 복사본: ['report', 'week42']
```

마지막 줄을 주목하자. 얕은 복사본에 태그를 붙였더니 **원본까지 바뀌었다.** 얕은 복사본과 원본이 같은 리스트 객체를 가리키기 때문이다. 프로토타입 패턴을 쓰면서 이걸 모르면, 템플릿 하나를 고쳤는데 그 템플릿에서 나온 모든 문서가 같이 바뀌는 버그를 만든다.

`timeout=3` 이 `3.0` 이 아니라 `3` 으로 찍힌 점도 눈여겨볼 만하다. 데이터클래스의 타입 표기는 런타임에 강제되지 않는다. 엄격하게 하려면 `build()` 의 검증 단계에서 변환하거나 정적 타입 검사기를 함께 쓴다.

## 현업에서는

- **프레임워크가 생성을 대신한다.** Spring 의 빈 컨테이너나 파이썬 웹 프레임워크의 의존성 주입 기능은 거대한 팩토리다. 기본 스코프가 "애플리케이션 전체에서 하나" 인 경우가 많아, 싱글턴 패턴을 직접 구현할 일이 거의 없다.
- **빌더는 테스트 데이터 생성에서 빛난다.** `a_user().with_role("admin").build()` 같은 테스트 데이터 빌더를 두면, 테스트마다 수십 개 필드를 채우지 않고 그 테스트에 중요한 필드만 드러낼 수 있다.
- **쿠버네티스 매니페스트도 프로토타입이다.** 디플로이먼트의 `template` 은 파드의 원본이고, 레플리카셋은 그 원본을 복제해 파드를 찍어 낸다. 템플릿을 바꾸면 새 복제본으로 롤링 교체되는 것도 같은 구조다.
- **싱글턴은 테스트를 오염시킨다.** 전역 캐시 싱글턴에 앞 테스트가 넣은 값이 다음 테스트에 남아 순서에 따라 성공·실패가 바뀌는 "가끔 깨지는 테스트" 의 단골 원인이다.

## 확인 문제

1. GoF 가 정리한 생성 패턴 다섯 가지를 쓰라.
2. 팩토리 메서드와 추상 팩토리의 차이를 "하나" 와 "묶음" 이라는 말로 설명하라.
3. 빌더 패턴이 생성자 인자를 많이 받는 방식보다 나은 점 두 가지는?
4. 위 예제에서 얕은 복사본에 태그를 추가했을 때 원본이 바뀐 이유는?
5. 파이썬에서 싱글턴 클래스를 따로 만들지 않아도 되는 경우가 많은 이유는?

### 풀이

1. 싱글턴, 팩토리 메서드, 추상 팩토리, 빌더, 프로토타입.
2. 팩토리 메서드는 제품 하나의 구체 타입 결정을 미루고, 추상 팩토리는 서로 관련된 제품 묶음을 일관된 계열로 만들어 준다.
3. 단계마다 이름이 붙어 읽기 쉽고, `build()` 에서 한 번에 검증하므로 불완전한 객체가 밖으로 나가지 않는다. 결과 객체를 불변으로 만들기도 쉽다.
4. 얕은 복사는 안쪽 리스트를 새로 만들지 않고 같은 리스트의 참조를 복사하기 때문에, 두 객체가 같은 리스트를 공유한다.
5. 모듈은 한 번만 import 되어 캐시되므로, 모듈 수준 객체가 자연스럽게 프로세스 안에서 하나만 존재한다.

## 더 읽을거리 (References)

- Erich Gamma, Richard Helm, Ralph Johnson, John Vlissides, *Design Patterns: Elements of Reusable Object-Oriented Software*, Addison-Wesley, 1994 (서지 정보)
- Python 문서, [copy — Shallow and deep copy operations](https://docs.python.org/3/library/copy.html)
- Python 문서, [Programming FAQ — How do I share global variables across modules?](https://docs.python.org/3/faq/programming.html#how-do-i-share-global-variables-across-modules)
- Python 문서, [dataclasses](https://docs.python.org/3/library/dataclasses.html)
