---
layout: post
title: "*디자인 패턴* — *Java 와 Python* 의 *서로 다른 *결**"
date: 2026-06-13 19:10:00 +0900
categories: [backend, design-patterns, programming]
tags: [design-patterns, gof, java, python, comparison, oop, fundamentals]
---

> *디자인 패턴* 은 *경험 의 *결정체*. *25 년 *전 의 GoF 책 의 *23 패턴* 이 *지금도 *유효*.
> 그런데 *Java 에서 *짠 패턴* 과 *Python 에서 *짠 패턴* 은 *코드 모양 이 *완전히 다르다*.
> *언어 의 *결* 이 *패턴의 *얼굴* 을 *바꾼다*. *두 언어를 *동시에 보면 *패턴 의 *본질* 이 *드러난다*.

---

## TL;DR

| 패턴 분류 | Java 의 *모습* | Python 의 *모습* |
|----------|----------------|------------------|
| **Creational** | *명시적 클래스 + private constructor* | *모듈 변수 / 데코레이터 / metaclass* |
| **Structural** | *인터페이스 + composition* | *덕 타이핑 + mixin* |
| **Behavioral** | *interface + 콜백 객체* | *함수 자체 가 *일급 객체* |

핵심 한 줄 :

> *Java 패턴 은 *명시 적 *클래스 의존*, Python 패턴 은 *언어 자체 가 *패턴 의 *일부 가 *흡수* — *둘 다 *보면 *본질 이 *읽힌다*.

---

## 1. *디자인 패턴 이란*

### *기원 — Gang of Four (1994)*

- Erich Gamma, Richard Helm, Ralph Johnson, John Vlissides 의 *책*
- *제목* : *Design Patterns: Elements of Reusable Object-Oriented Software*
- 23 패턴 *카탈로그*
- *OO 언어 *대상* (당시는 C++, Smalltalk)
- *건축가 *Christopher Alexander 의 *패턴 언어 영향*

### *분류 *3 가지*

1. **Creational** (생성) : *객체 생성 의 *유연 화*
2. **Structural** (구조) : *클래스 / 객체 의 *구조적 *조합*
3. **Behavioral** (행위) : *알고리즘 / 책임 의 *분배*

### *현대 의 *위치*

- *옛 *교과서 의 *암기 대상* 같지만, *실 무 가 *그대로 활용*
- *프레임 워크 (Spring, Django, React) 의 *내부 가 *패턴 천지*
- *2020 년 대 *AI / 함수형 *시대* 에도 *유효*

---

## 2. **Singleton** — *오직 *하나 만 *존재*

### *목적*

> *클래스 의 *인스턴스 가 *시스템 에 *오직 *하나 만*.*

흔한 *적용* : *Logger, Config, ConnectionPool, Cache*.

### Java

```java
public class Logger {
  private static volatile Logger instance;
  private Logger() {}

  public static Logger getInstance() {
    if (instance == null) {
      synchronized (Logger.class) {
        if (instance == null) {
          instance = new Logger();
        }
      }
    }
    return instance;
  }
}
```

*Double-Checked Locking* 이 *멀티 스레드 안전*.

**더 좋은 방법** — *Enum 활용* :

```java
public enum Logger {
  INSTANCE;
  public void log(String msg) { ... }
}
```

### Python

```python
class Logger:
  _instance = None

  def __new__(cls):
    if cls._instance is None:
      cls._instance = super().__new__(cls)
    return cls._instance
```

또는 *모듈 *자체 가 *Singleton* :

```python
# logger.py
def log(msg):
    print(msg)

# 사용
import logger
logger.log("hello")
```

→ *Python 의 모듈 시스템* 이 *Singleton 의 *자연 형태*.

### *비교*

- Java — *명시 적 코드 + 동시성 고려*
- Python — *언어 가 *해결* (모듈 = Singleton)
- *둘 다 *주의* : *Singleton 은 *글로벌 상태* → *테스트 어려움*. *남용 금지*.

---

## 3. **Factory Method** — *객체 생성 의 *위임*

### *목적*

> *생성 의 *로직 을 *서브 클래스 / 별도 메서드* 로 *위임* — *호출 자가 *구체 클래스 *알 필요 없음*.*

### Java

```java
interface Shape { void draw(); }
class Circle implements Shape { ... }
class Square implements Shape { ... }

class ShapeFactory {
  public static Shape create(String type) {
    switch (type) {
      case "circle": return new Circle();
      case "square": return new Square();
    }
    throw new IllegalArgumentException();
  }
}
```

### Python

```python
class Circle: 
    def draw(self): print("circle")

class Square: 
    def draw(self): print("square")

def shape_factory(kind):
    return {"circle": Circle, "square": Square}[kind]()
```

또는 *dict 직접 등록* :

```python
SHAPES = {"circle": Circle, "square": Square}
shape = SHAPES["circle"]()
```

→ Python 은 *클래스 자체 가 *일급 객체* — *Factory 가 *함수 + dict 만 으로 충분*.

---

## 4. **Builder** — *복잡 객체 의 *단계 적 *구성*

### Java

```java
class User {
  private final String name;
  private final int age;
  private final String email;

  private User(Builder b) {
    name = b.name; age = b.age; email = b.email;
  }

  public static class Builder {
    private String name;
    private int age;
    private String email;

    public Builder name(String n) { name = n; return this; }
    public Builder age(int a) { age = a; return this; }
    public Builder email(String e) { email = e; return this; }
    public User build() { return new User(this); }
  }
}

// 사용
User u = new User.Builder()
            .name("Lee")
            .age(35)
            .email("l@l.com")
            .build();
```

### Python

```python
from dataclasses import dataclass

@dataclass
class User:
    name: str
    age: int
    email: str

u = User(name="Lee", age=35, email="l@l.com")  # 키워드 인자
```

→ Python 의 *키워드 인자 + dataclass* 가 *Builder 의 *대체*. *Builder 패턴 자체 가 *필요 없음*.

*Lombok 의 *@Builder* (Java) 가 *비슷한 *간결화*. 단 *언어 자체 가 *자연 지원* 하는 Python 이 더 *직접 적*.

---

## 5. **Adapter** — *호환 안 되는 *둘 을 *연결*

### Java

```java
interface OldChargingPort { void chargeWith2Pin(); }
class NewDevice { void chargeWithUSBC() { ... } }

class Adapter implements OldChargingPort {
  private final NewDevice device;
  Adapter(NewDevice d) { device = d; }

  @Override
  public void chargeWith2Pin() {
    device.chargeWithUSBC();  // 변환
  }
}
```

### Python

```python
class NewDevice:
    def charge_with_usb_c(self): print("USB-C")

class Adapter:
    def __init__(self, device): self.device = device

    def charge_with_2pin(self):
        self.device.charge_with_usb_c()
```

→ *형태 *거의 동일*. *Python 은 *interface 선언 없음* (덕 타이핑).

---

## 6. **Decorator** — *기능의 *동적 *추가*

### Java

```java
interface Coffee { double cost(); }
class Espresso implements Coffee { 
    public double cost() { return 3000; } 
}

class MilkDecorator implements Coffee {
  private final Coffee base;
  MilkDecorator(Coffee b) { base = b; }
  public double cost() { return base.cost() + 500; }
}

// 사용
Coffee latte = new MilkDecorator(new Espresso());
```

### Python

```python
# *언어 차원의 *@decorator* — 함수 자체에 적용
def with_milk(func):
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs) + 500
    return wrapper

@with_milk
def espresso(): return 3000

print(espresso())  # 3500
```

→ **Python 의 *데코레이터 가 *언어 의 *기능*** — *GoF Decorator 와 *이름 동일하지만 *언어 차원에 *흡수*.

객체 차원 의 Decorator 도 Java 와 *유사 하게 작성 가능*.

---

## 7. **Proxy** — *대리 객체*

### Java

```java
interface ImageService { void load(); }
class RealImage implements ImageService {
    public void load() { /* 디스크 IO */ }
}

class CachedProxy implements ImageService {
  private RealImage real;
  public void load() {
    if (real == null) real = new RealImage();
    real.load();  // 또는 캐시 활용
  }
}
```

### Python

```python
class RealImage:
    def load(self): print("로딩")

class CachedProxy:
    def __init__(self):
        self._real = None
    def load(self):
        if self._real is None:
            self._real = RealImage()
        self._real.load()
```

→ 동일 패턴. *Spring AOP / Hibernate Lazy Loading* 의 *내부 가 Proxy*.

---

## 8. **Strategy** — *알고리즘 의 *교체 가능*

### Java

```java
interface SortStrategy { void sort(int[] arr); }

class QuickSort implements SortStrategy { 
    public void sort(int[] arr) { ... } 
}
class MergeSort implements SortStrategy { ... }

class Sorter {
  private final SortStrategy strategy;
  Sorter(SortStrategy s) { strategy = s; }
  void doSort(int[] arr) { strategy.sort(arr); }
}

// 사용
new Sorter(new QuickSort()).doSort(arr);
```

### Python

```python
def quick_sort(arr): ...
def merge_sort(arr): ...

def sort(arr, strategy=quick_sort):
    return strategy(arr)

# 사용
sort([3,1,2], merge_sort)
```

→ *Python 은 *함수 자체 가 *Strategy*. *클래스 *불필요*.

→ ***함수형 언어 에선 *Strategy 가 *기본 — *패턴 자체 의 *별도 *이름 없음***.

---

## 9. **Observer** — *상태 변화 의 *알림*

### Java

```java
interface Listener { void onUpdate(String event); }

class EventBus {
  private final List<Listener> listeners = new ArrayList<>();

  public void subscribe(Listener l) { listeners.add(l); }
  public void publish(String e) {
    for (Listener l : listeners) l.onUpdate(e);
  }
}
```

### Python

```python
class EventBus:
    def __init__(self):
        self.listeners = []

    def subscribe(self, callback):
        self.listeners.append(callback)

    def publish(self, event):
        for cb in self.listeners:
            cb(event)

# 사용
bus = EventBus()
bus.subscribe(lambda e: print(f"got: {e}"))
bus.publish("user_login")
```

→ Python 의 *함수 *직접 등록*. *Java 는 *Listener 인터페이스 구현 클래스* 필요.

---

## 10. **Template Method** — *큰 흐름 *고정 + *세부 *위임*

### Java

```java
abstract class DataProcessor {
  public final void execute() {  // 큰 흐름
    open();
    process();
    close();
  }
  abstract void open();
  abstract void process();
  abstract void close();
}

class CsvProcessor extends DataProcessor {
  void open() { ... }
  void process() { ... }
  void close() { ... }
}
```

### Python

```python
class DataProcessor:
    def execute(self):  # 큰 흐름
        self.open()
        self.process()
        self.close()

    def open(self): raise NotImplementedError
    def process(self): raise NotImplementedError
    def close(self): raise NotImplementedError

class CsvProcessor(DataProcessor):
    def open(self): ...
    def process(self): ...
    def close(self): ...
```

→ *구조 동일*. Python 의 *abstract 강제 가 *덜 강함* — 호출 시 *런타임 *예외*.

`abc` 모듈 의 `@abstractmethod` 로 *강제 가능*.

---

## 11. **Command** — *요청 의 *객체 화*

### Java

```java
interface Command { void execute(); }

class LightOnCommand implements Command {
  private final Light light;
  LightOnCommand(Light l) { light = l; }
  public void execute() { light.on(); }
}

// 큐 / 실행
List<Command> queue = ...;
for (Command c : queue) c.execute();
```

### Python

```python
def light_on(light):
    return lambda: light.on()

# 큐
queue = [light_on(light1), light_on(light2)]
for cmd in queue:
    cmd()
```

→ *Python 은 *클로저 + 함수 *직접 활용*. *클래스 *불필요*.

---

## 12. *언어 의 *결* 이 *만든 *차이*

### Java 의 *패턴 의 *모습*

- *명시 적 *클래스 + 인터페이스*
- *명시 적 *제약 표현*
- *큰 코드 양*
- *대형 시스템 의 *명확성* 강점
- *툴 (IDE / 정적 분석) *친화*

### Python 의 *패턴 의 *모습*

- *함수 / 데코레이터 / 모듈 *자체* 가 *패턴 일 부 흡수*
- *간결 + 표현 력*
- *동적 *유연 함*
- *작은 프로젝트 / 스크립트 *친화*
- *Pythonic = 패턴 의 *간결화*

### *결국 *둘 다 *배우면 *얻는 것*

- *패턴 의 *본질 이 *언어 *무관 함* 을 *확인*
- *언어 *별 *최적 *표현 의 *직 관*
- ***Java 의 *명시 성 + Python 의 *간결성 의 *조합* 이 *시야*

---

## 13. *현장 의 *진짜 *사례*

### Spring Boot 의 *패턴 천국*

- *Singleton* — Bean (default scope)
- *Factory* — `BeanFactory`, `@Bean`
- *Proxy* — `@Transactional`, AOP
- *Strategy* — `PasswordEncoder`, `AuthenticationProvider`
- *Observer* — `ApplicationEventPublisher`
- *Template* — `JdbcTemplate`, `RestTemplate`
- *Decorator* — Filter chain
- *Adapter* — `HandlerAdapter`

→ *Spring 의 *내부 자체 가 *패턴 *교과서*. *Spring 잘 쓰면 *패턴 의 *직 관* 이 *자연 익혀짐*.

### Django 의 *Python 친화 *패턴*

- *Middleware* — Chain of Responsibility
- *Signal* — Observer
- *Model* — Active Record
- *Decorator* — `@login_required`, `@csrf_exempt`

→ *Python 의 *언어 친화 *접근*. *함수 / 데코레이터 가 *대부분*.

### *FastAPI 의 *현대 적 *접근*

- Dependency Injection (Python `Depends`)
- Type hints + Pydantic Validator
- *Async 우선*

→ *언어 + 패턴 + 도구* 의 *현대 적 조합*.

---

## 14. *흔한 *안티 패턴*

### 14.1. *패턴 *남용 (Patternitis)*

```java
// ❌ 단순 함수 하나 인데 5 클래스
interface Calculator { int calc(int a, int b); }
class CalculatorImpl implements Calculator { ... }
class CalculatorFactory { ... }
class CalculatorService { ... }
```

→ ***패턴 은 *문제 해결 도구*** 지 *교양 과시 가 *아니다*. *복잡 한 *상황 에 *적용*.

### 14.2. *Singleton 의 *남용*

```python
# ❌ 모든 게 Singleton
class UserService: _instance = None ...
class OrderService: _instance = None ...
class ProductService: _instance = None ...
```

→ *글로벌 상태 *증가* → *테스트 어려움 + 결합 도 ↑*.

### 14.3. *깊은 *상속 계층 의 Template Method*

```java
class A { ... }
class B extends A { ... }
class C extends B { ... }
class D extends C { ... }  // 5 단계 깊이
```

→ *Composition + Strategy 로 *대체* 권장. *상속 깊이 ↑ = *유지 보수 *난도 ↑*.

### 14.4. *Observer 의 *순서 의존*

```
이벤트 → A 처리 → B 처리 → C 처리
       (순서 *의존*)
```

→ *Observer 가 *순서 보장 안 함*. *순서 중요 면 *Chain of Responsibility* 또는 *Workflow Engine*.

---

## 15. *내 *경험* — *패턴 의 *적정 *사용*

### *3 년차* 시점 — *과한 적용*

*모든 기능에 *패턴 *적용 시도*. *코드 *비대화 + *읽기 어려움*. *기술 만 자랑*.

### *7 년차* 시점 — *필요 한 곳에만*

- *Strategy* — *알고리즘 *교체 가능 한* 경우 *반드시*
- *Observer* — *event-driven 시스템 의 *기본*
- *Template Method* — *큰 흐름 + 세부 위임 이 *명확 한* 경우
- *Builder* — *복잡 객체 (5 필드+) 생성*

*나머지 패턴 들 — *언어 / 프레임 워크 가 *흡수 함*. *Singleton, Factory, Adapter, Proxy* — *직접 *작성 가 *거의 없음*. *Spring 안 에서 *자연 활용*.

---

## 16. 마치며

> *디자인 패턴 은 *공통 *언어*. *개발자 간 *짧은 단어 로 *큰 의도 *전달* 가능. *모르면 *현장 *대화 가 *어렵다*.

3 줄 요약 :

1. ***패턴 의 *본질 은 *언어 *무관* — *Java 든 Python 이든 *적용 가능***. 단 *형태* 가 다를 뿐.
2. ***Java 는 *명시 성 + 강 한 *클래스*, Python 은 *언어 자체 가 *흡수*** — *둘 다 *보면 *본질 이 *드러난다*.
3. ***패턴 의 *적정 사용 = *현장 의 *시야* — *모든 곳 에 *적용 ≠ *좋은 코드***.

7년차 회고 :

> *"학부 시절 *패턴 을 *외우 려 *애 썼다*. *7 년 후 *Spring 의 *내부 가 *패턴 그 자체 *임을 *몸 으로 *느끼며 — *외우지 *말고 *사용 하며 *익히는* 게 *진짜 *길* 임을 *알게 됨*."*

다음 글 — *Spring Boot 안의 *디자인 패턴 의 *깊이* — `@Transactional`, `BeanFactory`, `Filter`, `ApplicationEventPublisher` 의 *패턴 적 *해석*. 같은 시리즈 로 이어 집니다.

---

> 본 글은 *7년차 백엔드 엔지니어 의 *경험 회고*. *GoF 23 패턴 의 *모든 *것* 은 *원전 (책) 직접 읽기* 추천. *Java / Python 의 *문법* 은 *시간에 따라 *변할 수 있음* — *본질 + 비유* 에 *무게 중심*.
