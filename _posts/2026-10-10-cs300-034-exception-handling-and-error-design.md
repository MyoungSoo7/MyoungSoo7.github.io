---
layout: post
title: "[CS300 #034] 예외 처리와 오류 설계 — 실패도 인터페이스다"
date: 2026-10-10 18:34:00 +0900
categories: [cs]
tags: [cs300, programming, exception, error-handling, result-type]
---

컴퓨터공학 300 주제 시리즈의 034번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

오류 처리는 "실패를 어떻게 알리고, 누가 받아서, 무엇을 할 것인가"를 정하는 설계이며, 언어는 이를 예외(던지고 잡기) 또는 값(Result·error 반환) 두 방식으로 지원한다.

## 왜 필요한가

정상 경로만 있는 프로그램은 없다. 파일이 없고, 네트워크가 끊기고, 사용자가 숫자 칸에 글자를 넣는다. 이때 프로그램이 할 수 있는 선택은 많지 않다. 다시 시도하거나, 대체값을 쓰거나, 호출자에게 알리거나, 멈추는 것이다.

문제는 오류 처리가 엉성할 때 생기는 비용이 크다는 점이다. 예외를 조용히 삼키면 장애가 몇 시간 뒤 엉뚱한 곳에서 드러난다. 모든 오류를 `Exception` 으로 뭉뚱그리면 호출자가 재시도할지 포기할지 판단할 수 없다. 실패 방식은 함수 시그니처만큼 중요한 인터페이스다.

## 핵심 개념

### 두 가지 전달 방식

| 방식 | 실패 알림 | 대표 언어 | 장점 | 단점 |
|---|---|---|---|---|
| 예외 | 호출 스택을 거슬러 올라가며 잡힐 때까지 전파 | Python, Java, C#, JavaScript | 정상 경로 코드가 깔끔, 중간 계층은 신경 안 써도 됨 | 함수 시그니처에 드러나지 않음(Java 검사 예외 제외), 제어 흐름이 숨는다 |
| 값 반환 | 반환값에 성공/실패를 담음 | Go(`error`), Rust(`Result`), C(반환 코드) | 실패 가능성이 타입·시그니처에 보임, 흐름이 명시적 | 전파 코드가 장황해질 수 있음 |

Go 는 `error` 를 일반 값으로 다루는 관례를 택했다. 공식 블로그는 오류를 반환값으로 검사하는 것이 Go 의 관용구라고 설명한다([Error handling and Go](https://go.dev/blog/error-handling-and-go)). Rust 는 복구 가능한 오류에 `Result<T, E>`, 복구 불가능한 버그에 `panic!` 을 쓰도록 구분하고, `?` 연산자로 전파를 한 글자로 줄였다([Error Handling](https://doc.rust-lang.org/book/ch09-00-error-handling.html)).

### Python 의 try 문 구조

```
try:       실패할 수 있는 코드 (최소한으로)
except E:  E 타입 예외가 났을 때
else:      예외가 나지 않았을 때만
finally:   무슨 일이 있어도 마지막에 (정리)
```

`else` 는 "try 블록을 작게 유지하라"는 원칙을 위해 있다. 예외를 기대하지 않는 후속 코드를 `try` 밖으로 빼서, 엉뚱한 줄의 예외를 실수로 잡지 않게 한다. `finally` 는 `return` 이 있어도 실행된다([Errors and Exceptions](https://docs.python.org/3/tutorial/errors.html)). 파일·락·연결처럼 반드시 돌려줘야 하는 자원은 `with` 문(컨텍스트 매니저)으로 다루는 것이 더 안전하다.

### 예외 계층과 잡는 범위

예외는 클래스 계층을 이룬다. Python 에서 `ZeroDivisionError` 는 `ArithmeticError` 의 하위, 그 위는 `Exception`, 맨 위는 `BaseException` 이다. `KeyboardInterrupt`, `SystemExit` 는 `Exception` 이 아니라 `BaseException` 바로 아래에 있다. 그래서 `except Exception` 은 Ctrl+C 를 막지 않지만, 맨 `except:` 는 그것까지 삼킨다([Built-in Exceptions](https://docs.python.org/3/library/exceptions.html)).

원칙: **처리할 수 있는 예외만, 가장 구체적인 타입으로 잡는다.**

### 예외 연쇄: 원인을 보존하라

저수준 예외(`KeyError`)를 그대로 위로 올리면 호출자가 구현 세부에 묶인다. 반대로 새 예외로 바꾸면서 원래 예외를 버리면 디버깅 단서가 사라진다. Python 의 `raise 새예외 from 원래예외` 는 둘 다 해결한다. 새 예외의 `__cause__` 에 원인이 남고, 트레이스백에 두 단계가 모두 찍힌다. Java 의 `new MyException("msg", cause)` 도 같은 역할이다.

### 검사 예외 논쟁

Java 는 예외를 둘로 나눈다. `IOException` 같은 **검사 예외(checked)** 는 메서드가 잡거나 `throws` 로 선언해야 컴파일된다. `RuntimeException` 계열은 **비검사 예외**다. Java 튜토리얼은 이를 "Catch or Specify Requirement"로 설명하고, 클라이언트가 복구할 수 있다고 합리적으로 기대되면 검사 예외를, 그렇지 않으면 비검사 예외를 쓰라고 권한다([Lesson: Exceptions](https://docs.oracle.com/javase/tutorial/essential/exceptions/index.html)). 실무에서는 검사 예외가 람다·스트림과 잘 맞지 않아, 많은 프레임워크가 비검사 예외로 감싸는 쪽을 택했다.

### 여러 오류를 한꺼번에

검증이나 병렬 작업에서는 오류가 여러 개 동시에 생긴다. Python 3.11 의 PEP 654 는 `ExceptionGroup` 과 `except*` 를 도입해 여러 예외를 한 번에 던지고 타입별로 나눠 잡게 했다([PEP 654](https://peps.python.org/pep-0654/)). `asyncio.TaskGroup` 이 하위 작업들의 실패를 이 방식으로 모은다.

### 오류 설계 체크리스트

1. **복구 가능한가로 나눈다.** 재시도할 수 있는 일시 오류(타임아웃), 호출자 잘못(잘못된 입력), 프로그램 버그(불변식 위반)는 서로 다른 타입이어야 한다.
2. **추상화 수준에 맞춘다.** 저장소 계층의 `SQLException` 을 도메인 계층에 그대로 흘리지 않는다. 원인은 연쇄로 보존한다.
3. **삼키지 않는다.** 처리할 수 없으면 잡지 말고, 잡았으면 로그든 변환이든 흔적을 남긴다.
4. **빨리 실패한다.** 잘못된 설정은 시작할 때 터뜨린다. 요청 처리 중에 발견하면 피해가 크다.
5. **메시지에 맥락을 담는다.** "실패했다"가 아니라 어떤 값이, 무엇을 기대했는데, 무엇이었는지.

## 직접 해 보기

Python 3.12.3 에서 실행:

```python
def demo(x):
    try:
        print(" try")
        r = 10 / x
    except ZeroDivisionError as e:
        print(" except:", e)
        return "err"
    else:
        print(" else:", r)
        return "ok"
    finally:
        print(" finally")       # return 이 있어도 실행된다

print(demo(2))   #  try /  else: 5.0 /  finally / ok
print(demo(0))   #  try /  except: division by zero /  finally / err

class ConfigError(Exception):
    pass

def load_port(env):
    try:
        return int(env["PORT"])
    except KeyError as e:
        raise ConfigError("PORT 환경 변수가 없다") from e
    except ValueError as e:
        raise ConfigError(f"PORT 값이 정수가 아니다: {env['PORT']!r}") from e

for env in ({"PORT": "8080"}, {}, {"PORT": "eighty"}):
    try:
        print(load_port(env))
    except ConfigError as e:
        print(type(e).__name__, e, "| cause:", type(e.__cause__).__name__)
# 8080
# ConfigError PORT 환경 변수가 없다 | cause: KeyError
# ConfigError PORT 값이 정수가 아니다: 'eighty' | cause: ValueError

def validate(user):
    errors = []
    if not user.get("name"):
        errors.append(ValueError("name 비어 있음"))
    if user.get("age", 0) < 0:
        errors.append(ValueError("age 음수"))
    if errors:
        raise ExceptionGroup("검증 실패", errors)

try:
    validate({"name": "", "age": -1})
except* ValueError as eg:
    for e in eg.exceptions:
        print("-", e)
# - name 비어 있음
# - age 음수
```

같은 `load_port` 를 Rust 식으로 쓰면 실패가 시그니처에 드러난다(개념 코드).

```rust
fn load_port(env: &HashMap<String, String>) -> Result<u16, ConfigError> {
    let raw = env.get("PORT").ok_or(ConfigError::Missing)?;
    raw.parse::<u16>().map_err(|_| ConfigError::NotANumber(raw.clone()))
}
```

## 현업에서는

- **재시도 가능 여부**: HTTP 클라이언트 라이브러리는 연결 실패·5xx 와 4xx 를 다른 예외로 나눈다. 재시도 미들웨어는 전자만 재시도한다. 이 구분이 없으면 잘못된 요청을 끝없이 다시 보낸다.
- **경계에서 변환**: 웹 API 는 도메인 예외를 HTTP 상태 코드와 오류 본문으로 바꾸는 계층을 한 곳에 둔다. 컨트롤러마다 `try/except` 를 흩뿌리지 않는다.
- **크래시를 두려워하지 않기**: 쿠버네티스에서 복구 불가능한 상태(필수 설정 누락, DB 스키마 불일치)를 만난 프로세스는 오류를 남기고 종료하는 편이 낫다. 컨테이너가 재시작되고, `CrashLoopBackOff` 상태가 문제를 드러낸다. 이상한 상태로 계속 살아 있는 파드가 더 위험하다.
- **로그와 예외 한 번씩**: 같은 예외를 잡을 때마다 로그를 찍고 다시 던지면 한 장애에 같은 스택 트레이스가 수십 번 찍힌다. 최종 처리 지점에서 한 번만 기록한다.

## 확인 문제

1. Python `try` 문에서 `else` 절은 언제 실행되며, 왜 쓰는가?
2. 맨 `except:` 와 `except Exception:` 의 차이는?
3. `raise ConfigError(...) from e` 가 `raise ConfigError(...)` 보다 나은 점은?
4. Java 의 검사 예외와 비검사 예외를 구분하는 기준은?
5. 예외 방식과 값 반환 방식(Result) 각각의 장점을 하나씩 들라.

### 풀이

1. `try` 블록에서 예외가 나지 않았을 때 실행된다. 예외를 기대하지 않는 코드를 `try` 밖으로 빼서 엉뚱한 예외를 잡지 않기 위해 쓴다.
2. 맨 `except:` 는 `BaseException` 전부, 즉 `KeyboardInterrupt`, `SystemExit` 까지 잡는다. `except Exception:` 은 그 둘을 잡지 않는다.
3. 원래 예외가 `__cause__` 로 보존되어 트레이스백에 근본 원인이 함께 나온다.
4. 검사 예외는 컴파일러가 처리나 `throws` 선언을 강제한다. `RuntimeException` 과 `Error` 계열은 비검사다. 설계 지침상 호출자가 복구할 수 있으면 검사, 아니면 비검사.
5. 예외는 정상 경로 코드가 깔끔하고 중간 계층이 전파를 신경 쓰지 않아도 된다. Result 는 실패 가능성이 타입에 드러나 처리 누락을 컴파일러가 잡는다.

## 더 읽을거리 (References)

- Python Tutorial, [Errors and Exceptions](https://docs.python.org/3/tutorial/errors.html)
- Python Docs, [Built-in Exceptions — Exception hierarchy](https://docs.python.org/3/library/exceptions.html)
- [PEP 654 — Exception Groups and except*](https://peps.python.org/pep-0654/)
- The Rust Programming Language, [Error Handling](https://doc.rust-lang.org/book/ch09-00-error-handling.html)
- The Go Blog, [Error handling and Go](https://go.dev/blog/error-handling-and-go)
