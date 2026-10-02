---
layout: post
title: "Spicycrab — Python 을 Rust 로 바꿔 주는 트랜스파일러, 직접 돌려 봤다 (30배 빨랐고, 세 줄짜리 코드에서 깨졌다)"
date: 2026-10-02 20:25:00 +0900
categories: [Programming]
tags: [python, rust, transpiler, spicycrab, performance, benchmark]
---

Python 쓰는 사람들 사이에서 **Spicycrab** 이라는 이름이 돌았다. "Rust 를 배우지 않고도 Rust 의 성능을 얻는다"는 Python→Rust 트랜스파일러다.
발표 내용만 옮기면 소개 글이 되니, 이 글은 **lemuel 노드에 직접 설치해서 돌려 본 결과**까지 적는다.

## 어디서 나온 물건인가

[Python 공식 블로그의 Language Summit 2026 보고](https://blog.python.org/2026/09/language-summit-2026-spicycrab/)에 따르면,
Kushal Das 가 서밋에서 발표했다. 이름은 그가 매운 음식을 좋아해서 붙였다고 한다.

겨냥하는 사람은 분명하다.

- 서버 한 대로 더는 버티지 못하는 **성능 벽**에 부딪혔다. 수평 확장으로도 안 풀린다.
- 그렇다고 **새 언어를 배우고 싶지는 않다.**

Kushal 은 2008년 Django 를 쓰던 시절을 예로 들었다. 그때 유일한 선택지는 "뜨거운 경로"를 C 확장으로 다시 쓰는 것이었고,
그러면 Python 을 쓰는 게 아니게 되는 데다 크래시와 보안 문제를 떠안아야 했다. Rust 는 그 문제를 풀었지만
"Rust 문법이 머리를 깨뜨린다"는 게 그의 표현이다. 작은 조직들이 결국 Python 을 버리고 Go 로 옮기는 걸 보면서,
**Python 을 떠나지 않고 성능을 얻는 길**을 만들고 싶었다고 한다.

## 구성 — 도구 두 개

[GitHub README](https://github.com/kushaldas/spicycrab)의 설명은 이렇다.

- **`crabpy`** — 타입 주석이 붙은 Python 코드를 Rust 소스로 바꾼다. 결과물은 `cargo` 로 빌드하는 평범한 Rust 프로젝트다.
- **`cookcrab`** — Rust crate 의 API 를 Python 스텁으로 만들어 준다. 그래서 Python 문법으로 `clap` 이나 `actix-web` 같은 Rust 라이브러리를 쓰는 코드를 쓸 수 있다.

서밋 데모에서는 `actix-web` 패턴으로 쓴 Python 비동기 웹 서버를 Rust 로 바꿔 빌드했고, 그 바이너리가 "Hello World!"를 HTTP 로 응답했다.
발표장에서 `actix-web` 설치에 의존성 180개가 내려받아지자 웃음이 나왔다는 대목도 있다.

조건도 README 에 분명히 적혀 있다.

- **모든 Python 코드에 타입 주석이 있어야 한다.**
- Python 3.10+ 라고 적혀 있지만, [PyPI](https://pypi.org/project/spicycrab/)에 올라간 현재 버전(0.1.1)은 `requires_python >=3.14` 다.
- *"spicycrab and cookcrab are under active development. APIs, CLI options, and generated code may change frequently."*

## 직접 돌려 봤다

**환경:** lemuel(4코어, k3s 컨트롤 플레인과 여러 파드가 함께 도는 홈랩 노드), CPython 3.14 / 3.12, Rust 1.99(cargo), spicycrab 0.1.1.
노드에 영향이 없게 uv·Python·Rust 툴체인은 전부 임시 폴더에 설치했고, 실행은 메모리 상한을 건 개별 스코프에서 했다.

### 1) 잘 되는 경우 — 정수 루프

3,000,000 미만의 소수를 세는 코드다. 타입 주석을 붙였고 `while` 루프만 쓴다.

```python
def is_prime(n: int) -> bool:
    if n < 2:
        return False
    i: int = 2
    while i * i <= n:
        if n % i == 0:
            return False
        i = i + 1
    return True
```

`crabpy transpile primes.py -o primes_rs -n primes` 가 만든 Rust 는 이렇다.

```rust
pub fn is_prime(n: i64) -> bool {
    if n < 2 {
        return false;
    }
    let mut i: i64 = 2;
    while (i * i) <= n {
        if (n % i) == 0 {
            return false;
        }
        i += 1;
    }
    true
}
```

사람이 쓴 것처럼 깔끔하다. `cargo build --release` 는 9초 만에 끝났다. 같은 일을 세 번씩 돌린 결과다(초, 3회 중앙값).

| 실행 | 결과 | 시간 (중앙값) | 최대 메모리 |
|---|---|---|---|
| Rust (spicycrab 변환 후 빌드) | 216816 | **2.00초** | 1.9MB |
| CPython 3.14 | 216816 | 59.78초 | 12MB |
| CPython 3.12 | 216816 | 82.58초 | 10.6MB |

같은 답을 **약 30배(3.14 대비) 빠르게** 냈다. 다만 조건을 분명히 해 둔다.

- 순수 정수 루프는 트랜스파일러에게 **가장 유리한 경우**다. 실제 서비스 코드는 I/O, 문자열, 라이브러리 호출 비중이 크다.
- lemuel 은 다른 일을 하는 노드라 절대 시간에는 소음이 있다(같은 Rust 바이너리가 1.75~2.24초로 흔들렸다). 배수만 보는 게 맞다.

### 2) 깨지는 경우 — 세 줄짜리 코드

타입 주석이 없으면 시작부터 거절한다. 이건 문서에 적힌 그대로다.

```text
Error: t1.py:line 1: Missing type annotation for parameter
```

더 신경 쓰이는 건 **변환은 "성공"했는데 빌드가 안 되는** 경우였다.

```python
def main() -> None:
    squares: list[int] = [x * x for x in range(5)]
    d: dict[str, int] = {"a": 1}
    print(squares, d)
```

```rust
let squares: Vec<i64> = 0..5.into_iter().map(|x| x * x).collect::<Vec<_>>();
let d: HashMap<String, i64> = HashMap::from([("a".to_string(), 1)]);
println!("{}", squares);
```

`crabpy` 는 ✓ 를 찍었지만 `cargo build` 는 오류 3개로 실패했다. 범위에 괄호가 빠졌고(`(0..5)` 여야 한다), `Vec` 는 `{}` 로 출력할 수 없고,
`print` 의 두 번째 인자 `d` 는 아예 사라졌다.

정수 크기에서도 차이가 난다. Python 의 `int` 는 크기 제한이 없지만, 변환된 코드는 `i64` 다.

```python
big: int = 2 ** 70
```
```rust
let big: i64 = (2 as f64).powf(70 as f64);
```

이건 타입 불일치로 빌드가 안 된다. 설령 빌드되더라도 `2**70` 은 `i64` 범위를 넘는다. **Python 에서 맞던 숫자가 Rust 에선 다른 의미가 될 수 있다**는 점은 이 방식 전체가 안고 가는 숙제다.

## 그럼 언제 쓸 만한가

서밋에서도 같은 질문이 나왔다. Ken Jin 이 **mypyc, Cython, SPy** 대신 왜 이 방식이냐고 물었고, Kushal 은 SPy 는 Python 의 일부만 지원한다고 답하면서도
*"mypyc 도 좋고, 많은 경우 mypyc 를 바로 써도 된다"*고 인정했다. 그의 진짜 목표는 하나 더 있었다. Python 사용자가
**"문법에 겁먹지 않고" Rust 를 쓰게 하는 것**이다. 결과물이 읽을 수 있는 Rust 소스라는 점이 여기서 의미를 가진다.

직접 써 본 입장에서 정리하면 이렇다.

- **지금 쓸 만한 곳:** 타입이 분명한 계산 위주의 작은 모듈. 그리고 "이 Python 코드가 Rust 로는 어떻게 생기나"를 배우는 교재.
- **아직 이른 곳:** 운영 서비스 전체. 변환 성공 메시지를 믿으면 안 되고, 반드시 빌드와 테스트로 확인해야 한다. 0.1.x 이고 작성자 스스로 "자주 바뀐다"고 경고한다.
- **꼭 지킬 것:** 변환 전후 결과를 같은 입력으로 비교하는 테스트. 위의 `print(squares, d)` 처럼 조용히 사라지는 코드가 있다.

## LLM 이 다시 써 주는 시대에 트랜스파일러는?

서밋에서 가장 매운 질문은 Gregory P. Smith 에게서 나왔다. 최신 LLM 이 코드를 다른 언어로 통째로 다시 쓰는 일이 흔해질 텐데,
그건 Python 에게 **존재론적인** 문제라는 것이다. Kushal 의 답은 현실적이었다. LLM 재작성은 문제를 "한 번" 풀 뿐이고,
그 코드를 오래 유지보수하는 비용은 많은 조직에 감당하기 어렵다는 것이다(블로그 보고에 따르면 그는 Bun 의 Zig→Rust 재작성 비용 165,000달러를 예로 들었다).

트랜스파일러의 답은 **원본을 계속 Python 으로 유지한다**는 데 있다. 다만 오늘 확인한 대로, 그 약속이 지켜지려면 변환이 "성공했다"는 말과
"같은 동작을 한다"는 말 사이의 간극이 먼저 좁혀져야 한다.

## References

- Python Insider (PSF), *Spicycrab (Python Language Summit 2026)* — <https://blog.python.org/2026/09/language-summit-2026-spicycrab/>
- spicycrab GitHub 리포 (README) — <https://github.com/kushaldas/spicycrab>
- spicycrab on PyPI (0.1.1, requires_python >=3.14) — <https://pypi.org/project/spicycrab/>
- spicycrab 문서 (actix-web 예제) — <https://spicycrab.readthedocs.io/en/latest/actix_web.html>
- SPy — <https://github.com/spylang/spy>
