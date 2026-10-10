---
layout: post
title: "[CS300 #040] Rust 의 소유권과 빌림 — GC 없이 메모리 안전을 얻는 법"
date: 2026-10-10 18:40:00 +0900
categories: [cs]
tags: [cs300, programming, rust, ownership, borrow-checker]
---

컴퓨터공학 300 주제 시리즈의 040번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

Rust 는 모든 값에 주인을 하나씩 정하고(소유권), 주인이 범위를 벗어나면 즉시 해제하며, 남이 값을 쓸 때는 "여럿이 읽기 또는 하나만 쓰기" 규칙의 참조(빌림)만 허용한다. 이 규칙을 컴파일러가 검사해 GC 없이 해제 후 사용·이중 해제·데이터 경쟁을 막는다.

## 왜 필요한가

#027 과 #028 에서 메모리 관리의 두 길을 봤다. C 처럼 사람이 직접 해제하면 빠르지만 해제 후 사용과 이중 해제가 생긴다. GC 를 쓰면 안전하지만 런타임 비용과 멈춤이 생긴다.

Rust 는 세 번째 길을 택했다. 해제 시점을 **컴파일러가 코드의 구조로부터 정한다.** 실행 중에 추적할 것이 없으니 GC 가 필요 없고, 규칙을 어기는 코드는 컴파일되지 않으니 안전하다. 그 대가로 프로그래머는 "누가 이 값의 주인인가"를 늘 생각해야 한다. 처음 Rust 를 배우는 사람이 가장 많이 부딪히는 벽이 이 빌림 검사기다. 규칙의 이유를 알면 벽이 지도로 바뀐다.

## 핵심 개념

### 소유권 규칙 세 줄

Rust 공식 책은 소유권 규칙을 이렇게 정리한다([What Is Ownership?](https://doc.rust-lang.org/book/ch04-01-what-is-ownership.html)).

1. Rust 의 모든 값에는 **소유자**가 있다.
2. 한 번에 소유자는 **하나**뿐이다.
3. 소유자가 범위를 벗어나면 값은 **버려진다(drop)**.

3번이 핵심이다. `{ let s = String::from("hi"); }` 의 닫는 중괄호에서 컴파일러가 `drop(s)` 를 넣는다. 힙 메모리는 이때 해제된다. C++ 의 RAII 와 같은 아이디어이며, 파일 핸들·락·소켓 같은 자원에도 똑같이 적용된다.

### 이동

2번 규칙 때문에 대입이나 함수 인자 전달은 기본적으로 **이동(move)** 이다.

```
let a = String::from("hello");
let b = a;

 스택                      힙
 a: [ptr|len|cap] ──┐
                    ├──> "hello"     a 는 무효가 되고 b 만 주인이다
 b: [ptr|len|cap] ──┘
```

`String` 은 스택에 포인터·길이·용량을 두고 내용은 힙에 둔다. `let b = a;` 는 스택의 세 값만 복사한다. 이때 `a` 와 `b` 가 같은 힙을 가리키는 채로 둘 다 유효하면, 범위를 벗어날 때 두 번 해제된다. 그래서 Rust 는 `a` 를 **무효로 만든다.** 이후 `a` 를 쓰면 컴파일 오류 E0382 다([E0382](https://doc.rust-lang.org/error_codes/E0382.html)).

깊은 복사가 필요하면 `.clone()` 을 명시적으로 부른다. 비용이 드는 일이 코드에 드러난다.

정수, 불리언, 부동소수점처럼 스택에만 있고 복사가 싼 타입은 `Copy` 트레이트를 구현한다. 이런 타입은 대입해도 원본이 유효하다.

### 빌림: 참조

값을 넘길 때마다 소유권을 주고받으면 불편하다. 그래서 **참조**로 잠시 빌려준다.

| 참조 | 문법 | 할 수 있는 일 | 동시에 몇 개 |
|---|---|---|---|
| 공유 참조 | `&T` | 읽기 | 여러 개 |
| 가변 참조 | `&mut T` | 읽기·쓰기 | 하나만, 그동안 공유 참조도 없어야 함 |

공식 책의 빌림 규칙은 두 줄이다([References and Borrowing](https://doc.rust-lang.org/book/ch04-02-references-and-borrowing.html)).

- 어느 시점에든 **가변 참조 하나** 또는 **불변 참조 여러 개** 중 하나만 가질 수 있다.
- 참조는 **항상 유효**해야 한다.

이것은 읽기-쓰기 락(readers-writer lock)의 규칙과 같다. 다만 실행 중 락이 아니라 **컴파일 시점의 증명**이다. 그래서 두 가지 큰 버그 부류가 사라진다.

- **반복자 무효화**: 벡터의 원소를 참조하는 동안 `push` 하면, 재할당으로 원소가 다른 곳으로 옮겨져 참조가 허공을 가리킨다. Rust 에서는 공유 참조가 살아 있는 동안 가변 빌림이 필요한 `push` 를 막는다(E0502).
- **데이터 경쟁**: 두 스레드가 같은 데이터에 동시에 쓰거나, 하나는 쓰고 하나는 읽는 상황. 가변 참조가 하나뿐이므로 구조적으로 생길 수 없다.

### 수명

"참조는 항상 유효해야 한다"를 검사하려면 컴파일러가 참조가 **얼마나 오래 쓰이는지**와 원본이 **얼마나 오래 사는지**를 비교해야 한다. 이 범위를 **수명(lifetime)** 이라 한다.

대부분은 컴파일러가 알아서 추론한다(수명 생략 규칙). 함수가 여러 참조를 받아 참조를 돌려줄 때처럼 관계가 모호하면 `'a` 같은 수명 매개변수로 관계를 적어 준다. `fn longest<'a>(x: &'a str, y: &'a str) -> &'a str` 은 "반환 참조는 두 인자 중 더 짧게 사는 것만큼만 유효하다"는 뜻이다([Validating References with Lifetimes](https://doc.rust-lang.org/book/ch10-03-lifetime-syntax.html)). 수명 표기는 수명을 **바꾸지 않는다.** 관계를 설명할 뿐이다.

### NLL: 참조는 마지막 사용까지만 산다

초기 Rust 는 참조가 선언된 블록 끝까지 살아 있다고 보았다. 그래서 이미 다 쓴 참조 때문에 거부되는 코드가 많았다. RFC 2094 의 **비어휘적 수명(Non-Lexical Lifetimes)** 은 참조의 수명을 마지막으로 쓰인 지점까지로 줄였다([RFC 2094](https://rust-lang.github.io/rfcs/2094-nll.html)). 아래 예에서 `&mut e` 를 쓴 뒤 `e` 를 다시 읽을 수 있는 이유다.

### 규칙이 너무 엄격할 때

모든 데이터 구조가 "주인 하나" 모양은 아니다. 그래프, 양방향 연결 리스트, 여러 곳에서 공유하는 캐시가 그렇다. 표준 라이브러리는 이런 경우를 위한 도구를 제공한다.

- `Rc<T>` / `Arc<T>`: 참조 계수로 공유 소유(#028). `Arc` 는 스레드 간 공유용.
- `RefCell<T>` / `Mutex<T>`: 빌림 규칙 검사를 실행 시점으로 미룬다. 어기면 패닉하거나(`RefCell`) 기다린다(`Mutex`).
- `unsafe`: 컴파일러가 증명하지 못하는 것을 프로그래머가 책임지는 구역. 표준 라이브러리 내부 구현에 쓰이고, 안전한 API 로 감싸서 내놓는다.

## 직접 해 보기

아래 코드는 Rust Playground(stable, rustc 1.99.0, 2021 edition)에서 컴파일·실행했다.

```rust
fn take(s: String) -> usize { s.len() }          // 소유권을 받는다
fn borrow(s: &String) -> usize { s.len() }       // 빌린다
fn push_bang(s: &mut String) { s.push('!'); }    // 가변으로 빌린다

fn main() {
    let a = String::from("hello");
    let b = a;                         // 이동: a 는 이제 무효
    let c = b.clone();                 // 명시적 깊은 복사
    println!("{} {}", b, c);           // hello hello

    let n = borrow(&c);
    println!("{} {}", c, n);           // hello 5   빌려줬을 뿐, c 는 그대로

    let mut d = String::from("hi");
    push_bang(&mut d);
    println!("{}", d);                 // hi!

    let x = 5; let y = x;              // i32 는 Copy
    println!("{} {}", x, y);           // 5 5

    println!("{}", take(d));           // 3   d 는 take 로 이동, 이후 사용 불가

    let mut e = String::from("e");
    let m = &mut e;
    m.push('x');
    println!("{}", e);                 // ex   NLL: m 의 수명은 위 줄에서 끝났다
}
```

규칙을 어기면 컴파일러가 이유를 정확히 짚는다. 같은 환경의 실제 메시지다.

```rust
let a = String::from("hello");
let b = a;
println!("{} {}", a, b);
```

```
error[E0382]: borrow of moved value: `a`
2 |     let a = String::from("hello");
  |         - move occurs because `a` has type `String`, which does not implement the `Copy` trait
3 |     let b = a;
  |             - value moved here
4 |     println!("{} {}", a, b);
  |                       ^ value borrowed here after move
```

```rust
let mut v = vec![1, 2, 3];
let first = &v[0];
v.push(4);
println!("{}", first);
```

```
error[E0502]: cannot borrow `v` as mutable because it is also borrowed as immutable
3 |     let first = &v[0];
  |                  - immutable borrow occurs here
4 |     v.push(4);
  |     ^^^^^^^^^ mutable borrow occurs here
5 |     println!("{}", first);
  |                    ----- immutable borrow later used here
```

C++ 에서 같은 코드는 컴파일되고, `push` 가 재할당을 일으키면 `first` 는 해제된 메모리를 가리키게 된다. Rust 는 이 상황을 빌드 단계에서 거부한다.

해제 시점은 `Drop` 트레이트로 직접 볼 수 있다.

```rust
struct Guard(&'static str);
impl Drop for Guard {
    fn drop(&mut self) { println!("drop {}", self.0); }
}
fn consume(g: Guard) { println!("consume {}", g.0); }

fn main() {
    let _a = Guard("a");
    {
        let _b = Guard("b");
        println!("inner scope end");
    }                                  // drop b
    let c = Guard("c");
    consume(c);                        // c 는 consume 안에서 끝난다
    println!("main end");
}                                      // drop a
```

출력:

```
inner scope end
drop b
consume c
drop c
main end
drop a
```

`c` 는 소유권이 `consume` 으로 넘어갔으므로 `main` 이 아니라 `consume` 이 끝날 때 해제된다.

## 현업에서는

- **메모리 안전 언어로의 이동**: 시스템 소프트웨어에서 메모리 안전성 취약점을 줄이려는 흐름 속에 Rust 가 채택되고 있다. 리눅스 커널에도 Rust 로 커널 코드를 작성할 수 있는 지원이 들어갔다([Rust — The Linux Kernel documentation](https://docs.kernel.org/rust/index.html)).
- **컨테이너 생태계의 Rust 도구**: 컨테이너 런타임, 프록시, CLI 도구 중 Rust 로 작성된 것이 늘고 있다. GC 멈춤이 없고 정적 바이너리 하나로 배포되어 작은 컨테이너 이미지에 넣기 좋다.
- **API 설계에서의 소유권**: Rust 함수 시그니처는 `String`(소유권을 가져간다), `&str`(읽기만 빌린다), `&mut String`(수정하려 빌린다)로 의도가 드러난다. 다른 언어로 API 를 설계할 때도 "이 함수는 인자를 보관하는가, 잠깐 읽는가, 바꾸는가"를 명시하는 습관으로 옮겨 쓸 수 있다(#025).
- **빌림 검사기와 싸우지 않기**: 컴파일 오류를 `clone()` 과 `Rc<RefCell<...>>` 로 덮으면 컴파일은 되지만 설계가 흐려진다. 오류가 가리키는 "누가 주인인가"를 다시 정하는 쪽이 대개 더 좋은 구조로 이어진다.

## 확인 문제

1. Rust 소유권 규칙 세 가지를 말하라.
2. `let b = a;` 후 `a` 를 쓸 수 없는 이유를 이중 해제와 연결해 설명하라.
3. `i32` 변수는 대입 후에도 원본을 쓸 수 있는데 `String` 은 안 되는 이유는?
4. 벡터 원소에 대한 참조를 쥔 채 `push` 를 막는 규칙은 어떤 실제 버그를 예방하는가?
5. 수명 매개변수 `'a` 를 적으면 참조의 수명이 늘어나는가?

### 풀이

1. 모든 값에는 소유자가 있다. 소유자는 한 번에 하나다. 소유자가 범위를 벗어나면 값은 버려진다.
2. 대입은 스택의 포인터만 복사하므로 둘 다 유효하면 같은 힙 메모리를 두 주인이 범위 끝에서 각각 해제하게 된다. 그래서 `a` 를 무효로 해 주인을 하나로 유지한다.
3. `i32` 는 `Copy` 트레이트를 구현해 대입이 비트 복사이고 해제할 힙 자원이 없다. `String` 은 힙 버퍼를 소유하므로 `Copy` 가 아니고 대입이 이동이다.
4. 재할당으로 원소가 옮겨지면서 기존 참조가 해제된 메모리를 가리키는 반복자 무효화(해제 후 사용) 버그.
5. 아니다. 수명 표기는 여러 참조 사이의 관계를 컴파일러에게 설명할 뿐, 실제로 값이 사는 기간을 바꾸지 않는다.

## 더 읽을거리 (References)

- The Rust Programming Language, [What Is Ownership?](https://doc.rust-lang.org/book/ch04-01-what-is-ownership.html)
- The Rust Programming Language, [References and Borrowing](https://doc.rust-lang.org/book/ch04-02-references-and-borrowing.html)
- The Rust Programming Language, [Validating References with Lifetimes](https://doc.rust-lang.org/book/ch10-03-lifetime-syntax.html)
- [RFC 2094 — Non-lexical lifetimes](https://rust-lang.github.io/rfcs/2094-nll.html)
- Rust Error Codes Index, [E0382](https://doc.rust-lang.org/error_codes/E0382.html), [E0502](https://doc.rust-lang.org/error_codes/E0502.html)
