---
layout: post
title: "Rust 는 C++ 의 무엇을 지웠고, GC 언어의 무엇을 지웠나"
date: 2026-08-21 16:25:00 +0900
categories: [engineering, language]
tags: [rust, memory-safety, ownership, borrow-checker, systems-programming]
---

Rust 를 "C++ 대체 언어" 라고만 이해하면 절반만 맞다. Rust 가 실제로 만든 자리는 그 이전에 아예 없던 자리 — **"GC 없이 메모리 안전한 시스템 언어"** 라는 좌표다. 그 좌표가 왜 이전엔 없었고, Rust 가 어떻게 만들었으며, 대신 무엇을 요구하게 됐는지가 이 글의 내용이다.

먼저 사실.

- Rust 는 **2006년** Mozilla 직원이던 **Graydon Hoare** 의 개인 프로젝트로 시작. Mozilla 공식 후원은 **2009년**.[^wiki-rust]
- **Rust 1.0** 은 **2015년 5월 15일** 첫 안정판.[^wiki-rust]
- **Rust Foundation** 은 **2021년 2월 8일** 설립. 창립 5개사: **AWS, Google, Huawei, Microsoft, Mozilla**.[^wiki-rust]
- **Linux 커널** 은 **2022년 말 6.1 버전** 부터 Rust 실험 지원을 도입, 2025년 실험 상태 종료.[^wiki-rust]

이 사실만 나열해도 Rust 의 궤적이 보인다 — 개인 프로젝트에서 시작해 브라우저 회사가 후원하다가, 세계 최대 클라우드 · OS · 하드웨어 회사들이 함께 재단을 세웠고, 결국 Linux 커널이 받아들였다. **20년이 안 걸렸다.**

---

## 1. Before Rust — 두 갈래 세계

2015년 이전 시스템 프로그래밍 언어의 지형은 대략 이렇게 갈라져 있었다.

| | 대표 언어 | 성능 | 메모리 안전성 | GC | 사용처 |
|---|---|---|---|---|---|
| **저수준 · 빠름** | C, C++ | 최상 | ❌ | 없음 | 커널, DB 엔진, 게임 엔진, 브라우저 |
| **고수준 · 안전** | Java, Go, Python, C# | 중상~중 | ✅ | 있음 | 서버, 앱, 도구 |

이 두 축은 **동시에 만족될 수 없다** 는 것이 30년의 상식이었다. GC 없이 성능을 얻으려면 안전을 포기하고, 안전을 얻으려면 GC 를 받아들여야 했다.

C/C++ 세계의 실제 대가는 통계로 남아 있다.

- Microsoft 보안 팀의 조사에 따르면 **자사 제품의 CVE 중 약 70%가 메모리 안전성 문제** (use-after-free, buffer overflow, double free 등).[^msrc-70]
- Chromium 프로젝트에서도 심각도 High/Critical CVE 의 **약 70%가 메모리 안전성 관련**.[^chromium-70]

이건 "C++ 프로그래머가 부족해서" 가 아니다. **언어 자체에 남은 위험** 이다. C++ 은 스마트 포인터, RAII, `unique_ptr` 등으로 대응해 왔지만, 안전을 강제하지 못한다 — 개발자가 규율을 지켜야 한다. 대규모 코드베이스에서 규율은 통계적으로 새다.

한편 Java · Go 진영은 **GC 라는 대가** 를 지불해 안전성을 얻었다. 이 대가는 다음과 같은 자리에서 실제 통증이 된다.

- **커널** — 인터럽트 컨텍스트에서 GC 가 멈추면 시스템이 멈춘다.
- **실시간 시스템** — GC pause 가 예측 불가능하다.
- **임베디드** — GC 런타임 자체가 메모리와 CPU 를 먹는다.
- **DB 엔진** — 마이크로초 단위 latency 에서 GC 는 감당 안 됨.
- **브라우저 렌더링 엔진** — 60fps 프레임을 위해 16ms 안에 끝내야 하는데 GC 가 그걸 뒤흔든다.

이 자리들에서는 어떤 안전성 대가를 치르더라도 C/C++ 을 써야 했다. Firefox 도 그중 하나였다.

---

## 2. Rust 가 나온 배경 — Firefox 는 안전한 브라우저 엔진이 필요했다

Mozilla 가 Rust 를 후원한 실용적 이유는 **Servo** — Firefox 를 다음 세대로 옮기기 위한 실험적 브라우저 엔진 — 이었다. 브라우저 엔진의 요구사항이 정확히 위 표의 "저수준 · 빠름 · 안전" 이 동시에 필요한 자리였다.

브라우저는 (1) 신뢰할 수 없는 웹의 코드를 실행하고, (2) 60fps 를 뽑아야 하며, (3) 수백 개의 CVE 가 매년 발견되는 소프트웨어 종류다. C++ 로 짜인 기존 엔진(Gecko) 은 세 요구를 다 만족했지만, (1) 과 (3) 의 관계에서 안전성 사고가 상수였다.

Hoare 는 개인 프로젝트를 이런 문장으로 요약했다 — **"technology from the past come to save the future from itself."**[^wiki-rust] 오래된 아이디어들(타입 시스템, 대수적 데이터 타입, 리전 기반 메모리 관리, ML 계열 언어의 함수형 접근) 을 조합해 미래의 시스템 언어를 만들자는 것.

이 조합에서 나온 세 개의 핵심 개념이 Rust 를 정의한다.

---

## 3. Rust 가 실제로 지운 것 — 세 개의 컴파일 타임 보장

### 3-1. Ownership — 메모리 소유권을 타입 시스템에

C++ 에서 `delete p` 후 다시 `p` 를 쓰는 use-after-free 는 언어가 잡아주지 않는다. Rust 는 **소유권(ownership)** 이라는 규칙으로 이걸 컴파일 시점에 막는다.

- 모든 값은 **정확히 하나의 소유자** 를 갖는다.
- 소유자가 스코프를 벗어나면 값은 **자동으로 해제** 된다(`Drop` trait, 결정적 시점).
- 값을 다른 변수에 대입하면 **소유권이 이동(move)** 되고, 원래 변수는 더 이상 사용할 수 없다.

```rust
let s1 = String::from("hello");
let s2 = s1;              // s1 의 소유권이 s2 로 이동
println!("{}", s1);       // 컴파일 에러: value used after move
```

C++ 코드의 use-after-free 를 Rust 는 **컴파일러가 잡는다.** 런타임에 발견되는 게 아니라, 애초에 실행 파일이 만들어지지 않는다.

### 3-2. Borrow checker — 참조의 규칙

읽기 참조(`&T`) 와 쓰기 참조(`&mut T`) 를 구분하고, 컴파일러가 다음을 강제한다.

- 특정 시점에 **여러 개의 읽기 참조는 허용**, 하지만
- **쓰기 참조는 오직 하나만 허용**, 그리고
- 쓰기 참조가 있을 때는 **읽기 참조가 있을 수 없다**.

이 규칙 하나로 **데이터 레이스(data race)가 컴파일 타임에 불가능** 하다. C++ 에서 흔한 "두 스레드가 같은 벡터를 동시에 수정" 같은 코드는 Rust 에서 컴파일이 안 된다.

```rust
let mut v = vec![1, 2, 3];
let first = &v[0];        // 읽기 참조
v.push(4);                // 쓰기 참조 시도
println!("{}", first);    // 컴파일 에러: cannot borrow as mutable
```

Rust 는 이걸 **"fearless concurrency"** 라 부른다 — 두려움 없이 병렬 코드를 짜라는 뜻. 두려움을 컴파일러에게 위탁했다.

### 3-3. GC 없는 자동 해제

Ownership 이 정한 시점에 값이 해제되므로 **런타임 GC 가 필요 없다.** 이건 다음 세 가지를 동시에 준다.

- **결정적 해제 시점** — `}` 를 만나면 그 스코프의 값들이 정확히 그 순간 해제. GC 처럼 "언제 해제될지 모름" 이 없다.
- **런타임 오버헤드 없음** — GC 스레드도, mark-and-sweep 도, generational heap 도 없다.
- **커널 · 임베디드에서 쓸 수 있음** — no_std 환경에서 `alloc` 크레이트만으로 동적 할당 가능하거나, 아예 힙 없이도 동작.

이 세 개(ownership, borrow checker, GC 없음) 가 조합되어 이전엔 없던 좌표를 만들었다 — **"C 만큼 빠르고, GC 없이, 메모리 안전한 언어."**

---

## 4. Before / After 코드 세 쌍

### 4-1. Use-after-free

**C++**
```cpp
std::string* leak() {
    std::string s = "hello";
    return &s;              // 스택 변수의 주소 반환
}                           // s 는 여기서 소멸

int main() {
    std::string* p = leak();
    std::cout << *p;        // undefined behavior: use-after-free
}
```

이 코드는 **컴파일된다.** 실행 시점에 crash 하거나, 운 나쁘면 조용히 잘못된 데이터를 읽는다. 프로덕션에서 몇 년 뒤에 발견되는 종류의 버그.

**Rust**
```rust
fn leak() -> &String {      // 컴파일 에러
    let s = String::from("hello");
    &s                      // s 의 lifetime 이 반환 값보다 짧다
}
```

`error[E0106]: missing lifetime specifier` 그리고 시도해 봐도 borrow checker 가 막는다. **컴파일러가 프로덕션 버그를 개발 시점에 잡는다.**

### 4-2. 데이터 레이스

**C++ (표준 라이브러리 사용)**
```cpp
std::vector<int> v = {1, 2, 3};

std::thread t1([&]() { v.push_back(4); });
std::thread t2([&]() { v.push_back(5); });

t1.join();
t2.join();
```

두 스레드가 같은 벡터를 동시에 수정한다. 결과는 undefined — 크래시, 데이터 손실, 힙 corruption 어느 것이든 가능. 컴파일은 통과한다.

**Rust**
```rust
let mut v = vec![1, 2, 3];

std::thread::spawn(|| { v.push(4); });   // 컴파일 에러
std::thread::spawn(|| { v.push(5); });   // 두 클로저가 v 를 동시에 캡처 시도
```

Send/Sync trait 와 borrow checker 가 조합되어 이 코드는 **컴파일이 안 된다.** 진짜 필요하면 `Arc<Mutex<Vec<i32>>>` 처럼 명시적으로 동기화 원시를 써야 한다.

### 4-3. Null 참조

**Java/C++**
```java
User u = repo.findById(id);
String name = u.getName();  // u 가 null 이면 NullPointerException
```

**Rust**
```rust
let u: Option<User> = repo.find_by_id(id);
let name = match u {
    Some(user) => user.name(),
    None       => String::from("(unknown)"),
};
```

Rust 에는 null 이 없다. **"값이 있을 수도 없을 수도 있다"** 는 `Option<T>` 라는 타입으로 표현되고, 컴파일러가 두 경우를 모두 다루도록 강제한다. Kotlin 의 nullable 타입과 같은 사상이지만, Rust 는 처음부터 이 방식으로 설계됐다.

---

## 5. Rust 가 남긴 것 — 무엇을 지우지 못했나, 무엇을 새로 만들었나

Rust 는 위 세 가지 안전성을 지웠지만, 대신 새로운 세 가지 통증을 만들었다.

### 5-1. 학습 곡선 — Borrow checker 와 싸우는 시간

Ownership 규칙은 처음 배우는 사람에게 매우 어렵다. "이 코드가 안전한데 왜 컴파일러가 막지?" 라는 상황이 흔하고, 그때마다 코드 구조를 바꿔야 한다.

Rust 커뮤니티에서 흔히 쓰는 표현이 **"fighting the borrow checker"** 다. 몇 달을 지나면 사고 방식이 바뀌어 이 싸움이 줄어들지만, **초기 진입 장벽이 상당** 하다는 사실은 변하지 않는다. Java 개발자가 첫 프로덕션 Rust 를 짜는 데는 대개 3~6개월의 학습이 필요하다.

### 5-2. 컴파일 시간

Rust 컴파일러는 (1) 타입 검사, (2) borrow checker, (3) monomorphization(제네릭 특수화), (4) LLVM 최적화 를 모두 수행한다. 특히 (3) 은 제네릭을 쓸 때마다 코드가 폭발적으로 늘어나 컴파일 시간에 큰 영향을 준다.

큰 Rust 프로젝트의 clean build 는 수십 분 걸리는 일이 흔하다. Cargo 의 incremental build 와 sccache 로 완화하지만, **"컴파일 시간" 은 Rust 프로젝트의 실질적 이슈** 다.

### 5-3. Async 의 복잡성

Rust 의 `async/await` 는 zero-cost abstraction 을 지향한 결과 **런타임을 언어에 포함하지 않았다.** Tokio, async-std, smol 등 여러 런타임 중 하나를 선택해야 하고, 각 라이브러리가 특정 런타임에 종속되는 파편화가 발생한다. `Send + Sync + 'static` bound 를 async 함수에서 다루는 게 어려운 것도 유명한 통증.

### 5-4. 생태계의 젊음

Java 30년, C++ 40년의 라이브러리 생태계에 비해 Rust 는 10년 남짓이다. 특정 도메인(예: 엔터프라이즈 워크플로, 특정 하드웨어 SDK, 오래된 프로토콜 라이브러리) 에서는 여전히 부족하다. **crates.io 는 빠르게 커지지만, "성숙" 은 시간이 필요한 개념** 이다.

---

## 6. Rust 가 실제로 들어간 자리 — 지금(2026) 어디까지 왔나

Rust 의 채택 궤적을 압축하면.

- **2015** — Rust 1.0
- **2019** — AWS Firecracker(microVM), Discord 의 Read States 서버 이전(Go → Rust)
- **2020** — Microsoft 가 Windows 커널의 일부를 Rust 로 재작성 시작 발표
- **2021** — Rust Foundation 설립 (AWS/Google/Huawei/Microsoft/Mozilla)
- **2022** — **Linux Kernel 6.1** Rust 실험 지원[^wiki-rust]
- **2023** — Meta, Rust 를 사내 지원 서버 언어로 승격
- **2024** — Android Platform 에서 Rust 로 작성된 코드에서 메모리 안전성 CVE 가 **0건** 이라고 발표
- **2025** — Linux 커널의 Rust 지원 "실험" 딱지 제거[^wiki-rust]

시스템 프로그래밍이 40년 동안 C 로만 이뤄져 왔다는 사실을 감안하면, **10년 만에 커널까지 들어간 것은 이례적** 이다. 그리고 이는 우연이 아니라 **"메모리 안전한 시스템 언어" 라는 좌표가 실제로 비어 있었고, 산업이 그 자리를 얼마나 원했는지** 를 보여준다.

---

## 7. 정리 — 이전엔 없던 좌표를 만든 언어

**Before Rust** : 시스템 프로그래밍은 안전과 성능 중 하나를 골라야 했다. 커널을 짜려면 안전을 포기하고, 안전을 얻으려면 GC 를 받아들이고, 그 GC 로는 커널을 못 짰다. 이 삼각 딜레마가 30년의 상수였다.

**After Rust** : 세 번째 좌표가 생겼다 — **GC 없이 컴파일 타임에 메모리 안전한 시스템 언어.** 이 좌표가 실재함이 증명되자, 그 자리에 있었어야 할 사용처(커널, 브라우저 엔진, 클라우드 인프라, 임베디드) 들이 하나씩 Rust 로 이동하기 시작했다. **완전한 대체는 앞으로 수십 년의 일** 이지만, "가능하다" 는 사실 자체가 지형을 바꿨다.

**대가로 새로 생긴 것**: borrow checker 와 싸우는 시간, 긴 컴파일, 파편화된 async 생태계, 아직 젊은 라이브러리 시장. Rust 는 이 대가들이 **위 세 가지 안전성 대가보다 다루기 쉽다** 는 판단을 내린 사람들이 쓰는 언어다.

**한 문장으로**: Rust 는 "안전하려면 GC 를, 빠르려면 C 를" 이라는 상식을 지웠다. 그 대신 "**컴파일러와 싸우면 런타임에서 죽지 않는다**" 는 새 상식을 세웠다. 시스템 프로그래밍이 그 계약을 받아들이기 시작한 게 지난 10년의 이야기다.

---

[^wiki-rust]: Wikipedia, _Rust (programming language)_ — <https://en.wikipedia.org/wiki/Rust_(programming_language)>. 2006년 Graydon Hoare 의 개인 프로젝트로 시작, 2009년 Mozilla 공식 후원; Rust 1.0 은 2015년 5월 15일; Rust Foundation 은 2021년 2월 8일 AWS/Google/Huawei/Microsoft/Mozilla 5개사 창립; Linux 커널 6.1(2022년 말) Rust 실험 지원 도입, 2025년 실험 상태 종료; Hoare 의 언어 요약 — "technology from the past come to save the future from itself."

[^msrc-70]: Microsoft Security Response Center(MSRC), _A proactive approach to more secure code_ (2019) — Microsoft 제품의 CVE 중 약 70%가 메모리 안전성 관련. <https://msrc.microsoft.com/blog/2019/07/a-proactive-approach-to-more-secure-code/>

[^chromium-70]: Chromium Project, _Memory safety_ — Chromium 의 High/Critical severity 보안 버그 중 약 70%가 메모리 안전성 문제. <https://www.chromium.org/Home/chromium-security/memory-safety/>
