---
layout: post
title: "*아키텍처 *vs *SOLID *vs *의존성 역전 (DIP) *vs *의존성 주입 (DI)* — *4 개 가 *왜 *자꾸 *섞이는가*"
date: 2026-06-21 23:10:00 +0900
categories: [software-engineering, object-oriented, architecture]
tags: [oop, solid, dip, di, architecture, hexagonal, clean-architecture, spring, dependency-injection, java]
---

> *"아키텍처 가 *중요하다"* 와 *"SOLID 를 *지켜야 한다"* 와 *"DIP 를 *적용 했다"* 와 *"Spring 의 *DI 를 *쓴다"* 를 *같은 *뜻* 으로 *말하는 사람과 *이 4 개 가 *서로 다른 *층* 의 *서로 다른 *개념* 이라고 *말하는 사람은 *PR 리뷰* 를 *완전히 다르게 *한다*.
>
> *4 개 는 *서로 *포함* / *실현* / *근거* 의 *관계* 다. **아키텍처** 는 *시스템 전체* 의 *경계와 흐름*, **SOLID** 는 *클래스/모듈 수준* 의 *5 가지 *설계 원칙*, **DIP** 는 *SOLID 의 *D* — *추상화 의 *방향* 에 *대한 원칙*, **DI** 는 *DIP 를 *실현* 하는 *구현 기법 중 하나*. *위 → 아래* 로 *추상도 가 *낮아지고 *구체성 이 *높아진다*.
>
> 이 글은 *4 개 의 *경계* 를 *그려* *흔한 *오해* (예: *"DI = DIP"*, *"SOLID = 아키텍처"*, *"Spring 쓰면 *아키텍처 좋아짐"*) 를 *분해* 한다. *Java + Spring* 기준 예제 로 *같은 *코드* 가 *4 개 *층* 에서 *각자 *무엇을 *해결 했는지* 를 *보인다*.

---

## TL;DR

> 4 개 는 *추상도* 가 *다른 *동심원*.
>
> 1. **아키텍처 (Architecture)** — *시스템 전체 의 *경계 와 *흐름*. 예: *Layered, Hexagonal (Ports & Adapters), Clean Architecture, MSA, Modular Monolith*. *"무엇이 *무엇 안 에 *있고 *어디로 *말할 수 있는가"* 의 *최상위 *지도*.
> 2. **SOLID** — *클래스 / 모듈 수준* 의 *5 가지 *설계 원칙*. SRP (단일 책임), OCP (개방-폐쇄), LSP (리스코프 치환), ISP (인터페이스 분리), **DIP** (의존성 역전).
> 3. **DIP (Dependency Inversion Principle)** — *SOLID 의 *D*. *"고수준 모듈 이 *저수준 모듈 에 *의존하지 *말고* *둘 다 *추상* 에 *의존* 하라"*. *원칙* (Principle). *기법 이 아니라 *방향 의 *원칙*.
> 4. **DI (Dependency Injection)** — *DIP 를 *실현* 하는 *구현 기법 중 하나*. *"객체 가 *자신의 *의존성* 을 *직접 *생성하지 않고 *외부에서 *주입 받는다"*. *기법* (Technique). Spring/Guice 의 *IoC 컨테이너* 가 *대표적*.
>
> **포함 관계**: *아키텍처 ⊃ SOLID ⊃ DIP ⊃ DI*. *아키텍처 결정 안에서* *클래스 수준 의 *SOLID* 가 *지켜지고*, *그중 *D 원칙 (DIP)* 이 *방향* 을 *정 하고*, *그 방향 을 *실제 코드 에 *적용* 하는 *기법 중 하나* 가 *DI*.
>
> **흔한 오해**: ① *"Spring 쓰니까 *DI = DIP* 도 자동" — 아니다, *@Autowired* 는 *DIP 위반* 도 *얼마든지 *할 수 있다. ② *"SOLID 지키면 아키텍처 좋다"* — 아니다, *클래스 5 개 가 *깔끔* 해도 *시스템 전체 의 *경계 가 *없으면 *모놀리식 *스파게티*. ③ *"DIP 의 *구현 = DI* 뿐" — 아니다, *Service Locator, Strategy, Factory, Plugin* 도 *DIP 의 *실현 기법*.

---

## 0. *왜 *4 개 가 *자꾸 *섞이는가*

### 0.1 *3 개 의 *유사한 *어휘*

| 어휘 | 정체 | 종류 |
|---|---|---|
| Dependency **Inversion** Principle (DIP) | *SOLID 의 *원칙* | 원칙 (Principle) |
| Inversion **of Control** (IoC) | *제어 흐름 의 *역전* | 패턴 (Pattern) |
| Dependency **Injection** (DI) | *의존성 의 *주입* | 기법 (Technique) |

*"Inversion"* 이라는 단어 가 *DIP 와 *IoC* 에 *동시에* 나오고, *"Dependency"* 가 *DIP 와 *DI* 에 *동시에 *나오기 때문 에 — *4 글자 약어 만 보면 *같은 것 처럼 *느껴진다*. *Spring 공식 문서 마저 *예전에는 *"IoC = DI"* 처럼 *읽힐 수 있게 쓰여 *혼란 을 *키웠다*.

### 0.2 *4 개 의 *추상도 *지도*

```
┌─────────────────────────────────────────────┐
│           아키텍처                            │  ← 시스템 / 모듈 경계
│  ┌─────────────────────────────────────┐    │
│  │           SOLID 5 원칙                │    │  ← 클래스 / 모듈 설계
│  │  ┌───────────────────────────┐      │    │
│  │  │   DIP (의존성 역전 원칙)    │      │    │  ← 추상화 의 *방향*
│  │  │  ┌─────────────────┐      │      │    │
│  │  │  │ DI / IoC 컨테이너 │      │      │    │  ← 구현 *기법*
│  │  │  │ Service Locator  │      │      │    │
│  │  │  │ Strategy / Factory│     │      │    │
│  │  │  │ Plugin           │      │      │    │
│  │  │  └─────────────────┘      │      │    │
│  │  └───────────────────────────┘      │    │
│  │  SRP / OCP / LSP / ISP            │      │
│  └─────────────────────────────────────┘    │
└─────────────────────────────────────────────┘
```

*위 → 아래* 로 *추상도 가 *낮아지고 *구체성 이 *높아진다*. *각 층* 은 *위 층 의 *결정* 을 *전제 로 *동작* 한다.

### 0.3 *4 개 를 *동시에 *틀려 *흔한 *증상*

- **"Spring 쓰니 아키텍처 좋다"** — *Spring 의 *@Service / @Repository / @Autowired* 는 *DI 기법*. *아키텍처 가 *Layered 인지 *Hexagonal 인지* 와 *무관*. *@Service 만 있는 *공룡 클래스* 가 *Spring 모놀리스 의 *전형*.
- **"인터페이스 만 만들면 DIP"** — *인터페이스 가 *"누구를 위해 *존재* 하는지* 가 *DIP 의 *진짜 *지점*. *Repository* 인터페이스 가 *Application 패키지 에 있으면 DIP, *Adapter 패키지 에 있으면 *DIP 위반*.
- **"@Autowired = SOLID"** — *주입 받는 대상 이 *구체 클래스* 면 *SOLID 의 *D 위반*. *주입 *기법 (DI)* 은 *맞지만 *D 원칙* 은 *깨졌다*.

---

## 1. *아키텍처 — *시스템 전체* 의 *경계 와 *흐름*

### 1.1 *정의

> *아키텍처* 는 *시스템 의 *최상위 *구조 결정* — *어떤 컴포넌트 가 *존재하는가, *서로 어떻게 *말 하는가, *변경 의 *비용 이 *어디에서 *발생하는가*. *코드 수준 이 *아닌 *모듈 / 서브시스템 수준 의 *지도*.

### 1.2 *대표적 *아키텍처 *스타일*

| 스타일 | 핵심 결정 | 의존성 흐름 |
|---|---|---|
| **Layered** (전통적 N-tier) | Presentation → Service → Repository → DB | 위 → 아래 (단방향) |
| **Hexagonal (Ports & Adapters)** | Domain ← Application ← Adapter | *바깥 → 안* (도메인 이 *중심*) |
| **Clean Architecture** | Entity ← Use Case ← Interface Adapter ← Framework | *바깥 → 안* (4 동심원) |
| **Onion Architecture** | Domain Model ← Domain Services ← Application ← Infrastructure | *바깥 → 안* |
| **MSA** | 각 서비스 가 *독립 배포 + 독립 DB* | 서비스 간 *네트워크 호출* |
| **Modular Monolith** | 단일 배포 + 모듈 *경계 강제* | 모듈 간 *명시 적 *공개 API* |

### 1.3 *Hexagonal 의 *결정 예시 — *코드 가 *말 *못 하는 것*

```
┌─────────────────────────────────────────────────────────┐
│  Adapter (Web)         Adapter (Persistence)            │
│  - UserController      - UserJpaRepository (implements) │
│                                                          │
│        ↓ uses                  ↑ implements             │
│  ┌─────────────────────────────────────────────────┐    │
│  │           Application                            │    │
│  │  - UserService (uses port)                       │    │
│  │  - UserRepository (port = interface)             │    │
│  └─────────────────────────────────────────────────┘    │
│        ↓ uses                                            │
│  ┌─────────────────────────────────────────────────┐    │
│  │           Domain                                 │    │
│  │  - User (entity, 순수 비즈니스 모델)              │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

이 *그림* 이 *아키텍처 결정*:
- **무엇이 무엇 안 에 있는가**: Domain 은 *Application 을 *모른다*. Application 은 *Adapter 를 *모른다*.
- **어디로 말 할 수 있는가**: *바깥 (Adapter) 은 *안 (Application/Domain) 을 *알아도 되고*, *안 은 *바깥 을 *알면 *안 된다*.
- **인터페이스 (Port) 가 *어디 에 있는가*: *Application 패키지*. *Adapter 가 *구현* 한다.

이 *결정* 은 *코드 한 줄 안* 에 *드러나지 않는다*. *전체 디렉터리 구조 / 패키지 의존 방향 / ArchUnit 룰* 로 *강제* 한다.

### 1.4 *아키텍처 가 *해결 하는 *것*

- *변경 의 *국소 화*: DB 를 PostgreSQL → MongoDB 로 바꿔도 *Adapter 한 모듈* 만 *교체*. Domain / Application 은 *불변*.
- *테스트 가능성*: Domain 을 *프레임워크 없이 *순수 단위테스트*. Application 을 *fake adapter* 로 *통합 테스트*.
- *팀 경계*: MSA 라면 *팀 = 서비스*. Modular Monolith 라면 *팀 = 모듈*. *코드 오너십 의 *물리적 *기반*.

> *아키텍처 는 *코드 의 *기하학 (geometry)*. *클래스 가 *깔끔* 해도 *기하학 이 *깨져 있으면* *유지보수 비용 이 *기하급수적*. *반대로 *기하학 이 *맞으면 *클래스 내부 가 *좀 지저분 해도 *고치기 쉽다*.

---

## 2. *SOLID — *클래스 / 모듈 수준* 의 *5 가지 *원칙*

Robert C. Martin 이 *2000 년대 초* 에 *정리* 한 *객체지향 *설계 의 *5 원칙*. *클래스 / 모듈 의 *수준 에서 *변경 비용 을 *줄이는 *처방*.

### 2.1 *5 원칙 *요약*

| 약어 | 풀네임 | 한 줄 요약 |
|---|---|---|
| **S** | Single Responsibility Principle | *클래스 는 *하나 의 *변경 이유* 만 가진다 |
| **O** | Open-Closed Principle | *확장에는 열려 있고, *수정 에는 *닫혀 있다* |
| **L** | Liskov Substitution Principle | *서브타입 은 *부모 타입 의 *계약 을 *깨지 않아야 한다* |
| **I** | Interface Segregation Principle | *클라이언트 는 *사용하지 않는 *메서드 에 *의존 하지 않아야 한다* |
| **D** | Dependency Inversion Principle | *고수준 모듈 이 *저수준 모듈 에 *직접 의존 하지 않고 *추상 에 *의존* |

### 2.2 *S (단일 책임) — *변경 이유 의 *수* 가 *책임 의 *수*

```java
// 위반: 3 가지 변경 이유 (계산식 / DB / 이메일)
class Order {
    BigDecimal calculateTotal() { ... }     // ① 가격 정책 변경
    void saveToDatabase() { ... }           // ② 영속화 방식 변경
    void sendConfirmationEmail() { ... }    // ③ 알림 방식 변경
}

// 준수: 책임 분리
class Order {
    BigDecimal calculateTotal() { ... }
}
class OrderRepository { void save(Order o) { ... } }
class OrderNotifier { void notify(Order o) { ... } }
```

### 2.3 *O (개방-폐쇄) — *기존 코드 수정 없이 *기능 추가*

```java
// 위반: 결제 수단 추가 마다 if 문 추가
class PaymentService {
    void pay(String type, BigDecimal amount) {
        if ("CARD".equals(type)) { /* ... */ }
        else if ("BANK".equals(type)) { /* ... */ }
        else if ("KAKAO".equals(type)) { /* ... */ }  // ← 매번 수정
    }
}

// 준수: 다형성 으로 *수정 없이 확장*
interface PaymentMethod { void pay(BigDecimal amount); }
class CardPayment implements PaymentMethod { ... }
class BankPayment implements PaymentMethod { ... }
class KakaoPayment implements PaymentMethod { ... }  // ← 새 클래스 추가만, PaymentService 미수정
```

### 2.4 *L (리스코프 치환) — *계약 의 *유지*

```java
// 위반: 정사각형 is-a 직사각형 인데 setWidth 가 height 도 바꿔 부모 계약 깨짐
class Rectangle {
    void setWidth(int w) { this.width = w; }
    void setHeight(int h) { this.height = h; }
}
class Square extends Rectangle {
    @Override void setWidth(int w) { this.width = w; this.height = w; }  // ← 부모 계약 위반
    @Override void setHeight(int h) { this.width = h; this.height = h; }
}
// → Rectangle 을 가정한 코드 가 Square 에서 깨진다
```

### 2.5 *I (인터페이스 분리) — *큰 인터페이스 를 *작게 *쪼개*

```java
// 위반: Worker 인터페이스 가 너무 크다
interface Worker {
    void work();
    void eat();
    void sleep();
}
class Robot implements Worker {
    void work() { ... }
    void eat() { throw new UnsupportedOperationException(); }  // ← 안 쓰는 메서드 의존
    void sleep() { throw new UnsupportedOperationException(); }
}

// 준수: 역할별 인터페이스 분리
interface Workable { void work(); }
interface Eatable { void eat(); }
interface Sleepable { void sleep(); }
class Robot implements Workable { void work() { ... } }
```

### 2.6 *D — *DIP — *별도 섹션* 에서 *깊게* (다음 챕터)

> *SOLID 5 개 가 *전부 *클래스 / 모듈 수준 의 *원칙*. *아키텍처 (시스템 수준)* 와는 *층 이 다르다*. *SOLID 만 *지킨다고 *아키텍처 가 *좋아지지 *않는다*. 반대로 *아키텍처 가 *좋아도 *SOLID 위반 클래스 가 *섞일 수 있다*. *두 층 이 *독립적*.

---

## 3. *DIP — *추상화 의 *방향* 에 *대한 *원칙*

### 3.1 *원문 *정의*

> **Dependency Inversion Principle** (Martin, 1996)
> 1. *High-level modules should not depend on low-level modules. Both should depend on **abstractions**.*
> 2. *Abstractions should not depend on details. Details should depend on **abstractions**.*

번역:
1. *고수준 모듈* 은 *저수준 모듈* 에 *의존 하지 *말 것*. *둘 다 *추상* 에 *의존 할 것*.
2. *추상* 은 *세부* 에 *의존 하지 *말 것*. *세부* 가 *추상* 에 *의존* 할 것.

### 3.2 *"역전 (Inversion)" 은 *무엇* 의 *역전 인가*

전통적 (절차적) 흐름:

```
UserService → MySQLUserRepository → MySQL Driver  (위 → 아래, 의존도 위 → 아래)
```

*고수준 (UserService)* 이 *저수준 (MySQLUserRepository)* 을 *직접 import* 한다. *MySQL 을 *PostgreSQL 로 바꾸려면 *UserService 가 *함께 *변경* 되어야 한다 — *고수준 이 *저수준 의 *변경 비용 을 *흡수 한다*.

DIP 적용:

```
UserService → UserRepository (interface)
                  ↑
              MySQLUserRepository implements
```

*UserService 가 *인터페이스 만 *알고*, *구현* 이 *그 인터페이스* 를 *구현* 한다 — *의존 방향 이 *역전* 되었다. *MySQL → PostgreSQL 교체 시 *UserService 무변경*.

**핵심**: *"방향 이 뒤집힌 것"* 이 *DIP 의 *진짜 의미*. *DI (주입) 의 *방향* 이 *아니라* *컴파일 타임 의 *import 방향*.

### 3.3 *DIP 의 *핵심 질문 — *인터페이스 가 *어느 패키지 에 있는가*

DIP 가 *정말 *지켜졌는지* 의 *시금석*:

```
[패턴 A — DIP 준수]
application/
  ├── UserService.java
  └── UserRepository.java   ← 인터페이스가 application 패키지 (고수준 곁)
adapter/
  └── UserJpaRepository.java  ← application.UserRepository 를 implements

[패턴 B — DIP 위반]
application/
  └── UserService.java
adapter/
  ├── UserRepository.java    ← 인터페이스가 adapter 패키지 (저수준 곁)
  └── UserJpaRepository.java ← UserRepository 를 implements
```

*패턴 B 도 *"인터페이스를 만든다"* 는 *외형 은 같다*. 하지만:
- *application* 패키지 가 *adapter* 패키지 의 *UserRepository 를 *import* 한다 → *고수준 → 저수준 의존 방향 그대로*.
- *DIP 의 *역전 이 *일어나지 *않았다*. *형식적 인터페이스 만 *추가* 된 *위장 DIP*.

> *"인터페이스 를 만들었으니 DIP" 라는 *오해* 는 *흔하지만 *틀리다*. *인터페이스 가 *어느 모듈 의 *소유* 인지* 가 *진짜 *DIP*. *Hexagonal 아키텍처 에서 *Port 가 *Application 패키지에 있어야* 한다는 *룰 의 *직접적 *근거*.

### 3.4 *DIP 가 *해결 하는 *것*

- **컴파일 타임 의존 그래프 의 *역전***: *고수준 모듈 이 *저수준 의 *변경 에 *불변*.
- **추상화 의 *소유권***: *고수준 이 *원하는 인터페이스* 를 *정의*, *저수준 이 *맞추 도록* 한다 — *저수준 의 *기존 API 에 *맞추기 위해 *고수준 을 *왜곡 하지 *않는다*.
- **테스트 더블 의 *자연스러운 *주입점***: *인터페이스 가 *있으니 *Mock / Fake* 로 *대체 가능*.

---

## 4. *DI — *DIP 를 *실현 하는 *구현 기법 중 *하나*

### 4.1 *정의

> **Dependency Injection** (DI) — *객체 가 *자신이 *사용 할 *의존성* 을 *직접 *생성 하지 않고 *외부 (생성자/세터/필드) 에서 *전달 받는 *기법*.

### 4.2 *3 가지 *DI 형태*

```java
// 1. 생성자 주입 (권장)
class UserService {
    private final UserRepository repo;
    UserService(UserRepository repo) {
        this.repo = repo;
    }
}

// 2. 세터 주입
class UserService {
    private UserRepository repo;
    void setUserRepository(UserRepository repo) { this.repo = repo; }
}

// 3. 필드 주입 (Spring 의 @Autowired 필드)
class UserService {
    @Autowired
    private UserRepository repo;
}
```

### 4.3 *DI 와 *IoC 컨테이너 의 *관계*

*IoC (Inversion of Control)* 는 *"제어 흐름 을 *프레임워크 에 *맡긴다"* 라는 *더 넓은 *패턴*. *Spring Framework, Guice, Dagger, Micronaut, Quarkus* 등 의 *IoC 컨테이너* 가 *DI 를 *자동화* 한다.

```java
@Component
class UserService {
    private final UserRepository repo;

    UserService(UserRepository repo) {   // ← Spring 이 이 자리 에 UserJpaRepository 를 자동 주입
        this.repo = repo;
    }
}
```

> *IoC 컨테이너 ≠ DI*. *DI 는 *기법*, *IoC 컨테이너 는 *DI 를 *자동화 하는 *도구*. *손으로 *new UserJpaRepository() 를 *생성자 인자 로 전달* 하는 것도 *DI* 다.

### 4.4 *DIP 없는 *DI = 위장*

```java
// DI 는 했지만 DIP 위반
class UserService {
    private final MySQLUserRepository repo;  // ← 구체 클래스 주입

    UserService(MySQLUserRepository repo) {  // ← 구체 클래스 의존
        this.repo = repo;
    }
}
```

*MySQLUserRepository 라는 *구체 클래스* 를 *생성자 로 *주입 받는다*. *주입 (DI) 는 *맞지만 *의존성 의 *방향 이 *고수준 → 저수준 그대로*. *DIP 위반*.

```java
// DIP + DI 둘 다 준수
interface UserRepository { ... }              // ← 고수준 (application) 패키지 에 위치
class MySQLUserRepository implements UserRepository { ... }  // ← 저수준 (adapter) 패키지

class UserService {
    private final UserRepository repo;        // ← 추상 에 의존

    UserService(UserRepository repo) {        // ← 추상 을 주입 받음
        this.repo = repo;
    }
}
```

> **DI 는 *DIP 의 *충분조건 이 *아니다*. *DI 의 *대상 이 *추상 인가 *구체 인가* 가 *DIP 의 *분기점*.

### 4.5 *DIP 의 *대체 실현 기법*

DI 만 *DIP 를 *실현 하는 것 이 *아니다*.

| 기법 | 설명 |
|---|---|
| **Dependency Injection** | 외부에서 의존성 주입 (생성자/세터/필드) |
| **Service Locator** | `Locator.get(UserRepository.class)` 로 *동적 lookup* (안티패턴 시각도 있음) |
| **Strategy Pattern** | 알고리즘 인터페이스 + 런타임 선택 |
| **Factory Pattern** | *추상 팩토리* 가 *구현체* 를 *생성* |
| **Plugin / SPI** | Java ServiceLoader, OSGi, Eclipse 확장점 |
| **Template Method** | 부모 가 *후크 메서드* 정의, 자식 이 채움 |

이 *전부 가 *"고수준 이 *추상* 에 *의존* 하고 *저수준 이 *그 추상 을 *구현"* 의 *DIP 의 *형태*. *DI 는 *현대 *Java 프레임워크 가 *가장 *흔히 *선택* 하는 *기법* 일 뿐*.

---

## 5. *4 개 의 *교차 — *같은 코드 가 *4 개 *층 에서 *각자 무엇을 *해결 했는가*

### 5.1 *예제 *시나리오*

> "주문 생성 시 사용자에게 이메일 알림을 보낸다."

### 5.2 *Level 0 — *아무 것 도 *안 한 *코드*

```java
class OrderController {
    @PostMapping("/orders")
    void create(@RequestBody OrderRequest req) {
        Connection conn = DriverManager.getConnection("jdbc:mysql://...");
        // ... INSERT INTO orders ...

        Properties props = new Properties();
        props.put("mail.smtp.host", "smtp.gmail.com");
        Session session = Session.getInstance(props);
        // ... MimeMessage 작성 + Transport.send ...
    }
}
```

*아키텍처 X, SOLID X, DIP X, DI X*. *모든 것 이 *컨트롤러 안에 *섞임*. *변경 비용 = 전체 재작성*.

### 5.3 *Level 1 — *클래스 분리 (SRP)*

```java
class OrderController {
    OrderService orderService = new OrderService();

    void create(OrderRequest req) {
        orderService.create(req);
    }
}

class OrderService {
    OrderRepository repo = new OrderRepository();
    EmailSender email = new EmailSender();

    void create(OrderRequest req) {
        Order o = new Order(req);
        repo.save(o);
        email.send(o);
    }
}
```

*SOLID 의 *S 일부 *준수* (책임 분리). *그러나 *D 위반*: *OrderService 가 *구체 클래스 OrderRepository, EmailSender 를 *직접 new*. *변경 시 *OrderService 도 *수정 필요*.

### 5.4 *Level 2 — *인터페이스 도입 (DIP 시도)*

```java
interface OrderRepository { void save(Order o); }
interface NotificationSender { void send(Order o); }

class JpaOrderRepository implements OrderRepository { ... }
class SmtpNotificationSender implements NotificationSender { ... }

class OrderService {
    private final OrderRepository repo;
    private final NotificationSender notifier;

    OrderService() {
        this.repo = new JpaOrderRepository();          // ← 여기 가 문제
        this.notifier = new SmtpNotificationSender();  // ← 여기 도
    }
}
```

*인터페이스 는 *있다 (DIP 시도)*. 그러나 *OrderService 가 *여전히 *구체 클래스 를 *new* 한다 → *컴파일 타임 의 *고수준 → 저수준 의존 그대로*. *형식적 DIP, 실질 위반*.

### 5.5 *Level 3 — *DI 적용 (수동)*

```java
class OrderService {
    private final OrderRepository repo;
    private final NotificationSender notifier;

    OrderService(OrderRepository repo, NotificationSender notifier) {  // ← 주입
        this.repo = repo;
        this.notifier = notifier;
    }
}

// main 또는 Configuration 에서
OrderService service = new OrderService(
    new JpaOrderRepository(),
    new SmtpNotificationSender()
);
```

*DI 적용 (생성자 주입)*. *DIP 도 *준수* (인터페이스 에 의존). *손으로 *조립* 하는 형태*. *Spring 없는 *순수 자바*.

### 5.6 *Level 4 — *Spring IoC 컨테이너 자동화*

```java
@Service
class OrderService {
    private final OrderRepository repo;
    private final NotificationSender notifier;

    OrderService(OrderRepository repo, NotificationSender notifier) {
        this.repo = repo;
        this.notifier = notifier;
    }
}

@Repository
class JpaOrderRepository implements OrderRepository { ... }

@Component
class SmtpNotificationSender implements NotificationSender { ... }
```

*Spring 컨테이너 가 *주입 을 *자동화*. *Level 3 과 *원리 는 *동일* — *Spring 이 *조립 *코드* 를 *대신 *써 줄 뿐*.

### 5.7 *Level 5 — *Hexagonal 아키텍처 까지*

```
domain/
  └── Order.java                       (순수 비즈니스 모델, Spring 어노테이션 X)

application/
  ├── OrderService.java                (Use case)
  ├── port/
  │   ├── OrderRepository.java         (인터페이스 — DIP 의 핵심)
  │   └── NotificationSender.java
  └── ...

adapter/
  ├── persistence/
  │   └── JpaOrderRepository.java      (implements application.port.OrderRepository)
  ├── notification/
  │   └── SmtpNotificationSender.java
  └── web/
      └── OrderController.java
```

*ArchUnit 룰* 로 *강제*:
```java
@Test
void domainShouldNotDependOnApplication() {
    noClasses().that().resideInAPackage("..domain..")
        .should().dependOnClassesThat().resideInAPackage("..application..")
        .check(allClasses);
}

@Test
void applicationShouldNotDependOnAdapter() {
    noClasses().that().resideInAPackage("..application..")
        .should().dependOnClassesThat().resideInAPackage("..adapter..")
        .check(allClasses);
}
```

*아키텍처 + SOLID + DIP + DI 가 *모두 동시 작동*:
- **아키텍처**: 패키지 의존 방향 강제 (도메인 ← 애플리케이션 ← 어댑터)
- **SOLID**: 각 클래스 가 *단일 책임 + 인터페이스 분리 + 추상 의존*
- **DIP**: 인터페이스 가 *application/port* 에 위치 (고수준 의 소유)
- **DI**: Spring 의 자동 주입

### 5.8 *4 개 가 *각자 무엇을 *해결 했는가*

| 층 | 해결 한 *문제* | 깨지면 *증상* |
|---|---|---|
| 아키텍처 | "DB 를 바꾸려면 *얼마나 *수정* 해야 하나" | 도메인 코드 안 에 JPA 어노테이션 / SQL 이 박힘 |
| SOLID (D 제외) | "이 클래스 *수정 마다 *얼마 *터지나" | 1 클래스 *변경 → 10 군데 *컴파일 에러* |
| DIP | "고수준 모듈 이 *저수준 변경* 에 *흔들리는가" | DB 교체 시 *Service 시그니처* 도 *바뀜* |
| DI | "테스트 시 *의존성* 을 *Mock 으로 *교체 가능 한가" | 단위 테스트 가 *불가능*, *통합 테스트* 만 가능 |

---

## 6. *흔한 *오해* 와 *답*

### 6.1 *"Spring 쓰니 *DIP 자동" — *아니다*

```java
@Service
class OrderService {
    @Autowired
    private JpaOrderRepository repo;  // ← 구체 클래스 주입
}
```

*Spring 의 *@Autowired* 는 *DI 기법*. *주입 대상 이 *구체 클래스* 면 *DIP 위반*. *@Autowired 가 *DIP 를 *자동 보장 하지 *않는다*.

### 6.2 *"인터페이스 만들면 *DIP" — *아니다*

```
adapter/
  ├── UserRepository.java            (인터페이스 — 그러나 adapter 소유)
  └── UserJpaRepository.java
application/
  └── UserService.java (imports adapter.UserRepository)
```

*application 이 *adapter 의 *인터페이스 를 *import* 한다 → *컴파일 의존 방향 은 *application → adapter* 그대로*. *형식적 DIP, 실질 위반*. *인터페이스 의 *소유권* 이 *DIP 의 *진짜 *지점*.

### 6.3 *"SOLID 지키면 *아키텍처 자동 좋음" — *아니다*

SOLID 5 개 가 *전부 *클래스 / 모듈 수준 의 *원칙*. *클래스 5 개 가 *깔끔* 해도 *시스템 전체 의 *경계 가 *없으면 *모놀리식 *스파게티*. *수백 개 클래스 가 *각자 *깔끔 하지만 *서로 *임의 의존* 한다면 *프로젝트 변경 비용 은 *여전히 *지수적*.

> SOLID 는 *현미경*, *아키텍처 는 *위성 사진*. *둘 다 *필요* 하다.

### 6.4 *"DI 안 쓰면 *DIP 안 된 거" — *아니다*

DIP 의 *대체 실현 기법* 이 *Section 4.5 에 *나열* 됨. *Service Locator, Strategy, Factory, Plugin, Template Method* 모두 *DIP 를 *실현* 한다. *DI 는 *Spring 시대 에 *가장 *흔할 뿐*. *순수 함수형 언어 (Haskell)* 는 *DI 없이 *DIP* 를 *타입 클래스 + 모나드 트랜스포머* 로 *달성* 한다.

### 6.5 *"IoC = DI" — *아니다*

IoC 는 *더 넓은 패턴* — *프레임워크 가 *내 코드 를 *호출 한다 (Hollywood Principle)*. *Spring Web 의 *@Controller* 가 *HTTP 요청 시 *내 메서드 를 *호출* 하는 것 도 *IoC*. DI 는 *IoC 의 *부분 집합*.

### 6.6 *"DIP 적용 = 인터페이스 무조건 추가" — *아니다*

*변경 가능성 이 *낮은* *유틸리티 (StringUtils, MathUtils)* 까지 *인터페이스 화* 하면 *불필요한 *추상화 비용*. *DIP 는 *변경 비용 이 *큰 *경계 에서 *적용*. *YAGNI*.

---

## 7. *정리

### 7.1 *4 개 의 *한 줄 *정의*

| 개념 | 한 줄 |
|---|---|
| **아키텍처** | *시스템 전체* 의 *경계 와 *흐름 의 *결정* |
| **SOLID** | *클래스 / 모듈 수준 의 *5 가지 *설계 원칙* |
| **DIP** | *고수준 이 *저수준 에 *의존 하지 않고 *둘 다 *추상* 에 의존 하라 — *원칙* |
| **DI** | *의존성 을 *직접 *생성 하지 *않고 *주입 받는다 — *기법* |

### 7.2 *4 개 의 *포함 관계*

```
아키텍처 (시스템)
   └── SOLID (클래스)
          └── DIP (의존 방향 의 원칙)
                 └── DI (실현 기법 중 하나)
```

### 7.3 *PR 리뷰 시 *4 개 *질문*

1. **아키텍처**: *이 변경 이 *모듈 경계* 를 *넘는가*? Domain 이 Adapter 를 import 하는가? Application 이 Adapter 의 인터페이스 를 import 하는가?
2. **SOLID**: *클래스 의 *변경 이유 가 *2 개 이상 인가*? 인터페이스 가 *클라이언트 가 안 쓰는 메서드* 를 *포함 하는가*?
3. **DIP**: *주입 받는 타입* 이 *인터페이스 인가 구체 클래스 인가*? *인터페이스 가 *어느 패키지 의 *소유 인가*?
4. **DI**: *생성자 주입 인가 필드 주입 인가*? *테스트 시 *Mock 으로 *교체 가능* 한가?

### 7.4 *마지막 한 마디

> *4 개 가 *섞이는 *이유 는 *Spring 의 *마법 같은 *@Autowired 가 *4 개 를 *동시에 *덮어버려 *각자 의 *경계 를 *흐리게 *만들기 때문*. Spring 을 *벗긴 *순수 자바* 로 *4 개 를 *각각 *분리해 *적용해 보면 *각 층 이 *무엇을 *해결 하고 *무엇을 *해결 못 하는지* 가 *드러난다*.
>
> *아키텍처 가 *없으면 *클래스 5 개 가 *깔끔 해도 *프로젝트 가 *터지고*, *SOLID 가 *없으면 *Hexagonal 디렉터리 안 의 *공룡 클래스 가 *변경 비용 을 *무한대로 *밀어 올리고*, *DIP 가 *없으면 *인터페이스 가 *형식뿐 인 *위장 추상화* 가 되고*, *DI 가 *없으면 *테스트 가 *통합 테스트* 만 *가능* 해진다. *4 개 가 *각자 *맡은 *문제 의 *범위 가 *다르고*, *4 개 가 *같이 *맞물려야 *유지보수 가능한 *객체지향 시스템* 이 *완성* 된다.
