---
layout: post
title: "[CS300 #011] 정수론 기초 — 나머지 연산과 최대공약수"
date: 2026-10-10 18:11:00 +0900
categories: [cs]
tags: [cs300, math, number-theory, modular-arithmetic, gcd]
---

컴퓨터공학 300 주제 시리즈의 011번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

나머지 연산은 정수를 n 개의 동치류로 접어서 "시계 위의 산술" 을 하게 해 주고, 유클리드 호제법은 두 수의 최대공약수를 로그 시간에 구한다. 이 둘이 해싱, 난수, 암호, 체크섬의 기본 도구다.

## 왜 필요한가

컴퓨터의 정수는 고정 폭이다. 32 비트 부호 없는 정수의 덧셈은 사실 mod 2³² 덧셈이다. 해시 테이블은 `hash(key) % 버킷수` 로 위치를 정하고, 원형 버퍼는 `(i + 1) % size` 로 돌고, 라운드 로빈 부하 분산은 `요청번호 % 서버수` 로 서버를 고른다.

최대공약수는 분수 약분 같은 산수 문제에만 쓰이는 게 아니다. 다음 글에서 다룰 모듈러 역원, 그리고 RSA 키 생성이 모두 확장 유클리드 호제법에 기대고 있다. 정수론은 지금 인터넷 보안의 바닥에 깔려 있다.

## 핵심 개념

### 나눗셈 정리

정수 a 와 양의 정수 n 에 대해 다음을 만족하는 정수 q(몫)와 r(나머지)이 **유일하게** 존재한다.

```
a = q·n + r,   0 ≤ r < n
```

이 r 을 a mod n 이라 쓴다. 수학의 정의에서 나머지는 항상 0 이상 n 미만이다.

**주의: 언어마다 % 의 정의가 다르다.** 파이썬은 나눗셈을 내림(floor)으로 정의해서 결과가 제수 n 과 같은 부호를 갖는다. C, C++, 자바, Go 는 0 쪽으로 버림(truncate)하므로 나머지가 피제수 a 와 같은 부호다.

| 식 | 파이썬 | C·자바·Go |
|---|---|---|
| 7 % 3 | 1 | 1 |
| −7 % 3 | 2 | −1 |
| 7 % −3 | −2 | 1 |

파이썬의 동작은 공식 문서의 이항 산술 연산 항목에 정의되어 있다([Python Language Reference, Binary arithmetic operations](https://docs.python.org/3/reference/expressions.html#binary-arithmetic-operations)). 음수 해시 값에 `%` 를 쓰는 C 계열 코드에서 배열 인덱스가 음수가 되는 버그가 여기서 나온다.

### 합동과 모듈러 산술

n 이 a − b 를 나누면 a 와 b 가 **법 n 에 대해 합동**이라 하고 a ≡ b (mod n) 으로 쓴다. 006번 글에서 본 대로 이는 동치 관계이고, 정수를 n 개의 동치류 [0], [1], …, [n−1] 로 나눈다.

합동은 덧셈·뺄셈·곱셈과 잘 맞물린다. a ≡ b, c ≡ d (mod n) 이면

```
a + c ≡ b + d    a − c ≡ b − d    a·c ≡ b·d    (mod n)
```

그래서 큰 수의 계산 중간중간에 나머지를 취해도 최종 나머지는 같다. (a·b) mod n = ((a mod n)·(b mod n)) mod n 이다. 이 성질 덕분에 수백 자리 수의 거듭제곱도 작은 수의 곱셈만으로 계산할 수 있다.

**나눗셈은 그대로 되지 않는다.** 2·3 ≡ 2·8 (mod 10) 이지만 3 ≢ 8 (mod 10) 이다. 양변을 2 로 "나눌" 수 없다. 언제 나눌 수 있는지는 다음 글의 주제다.

### 빠른 거듭제곱

aᵏ mod n 을 k 번 곱하면 k 에 비례해 느리다. 지수를 이진수로 보고 제곱을 반복하면 곱셈 횟수가 약 2·log₂k 번으로 준다.

```
3^13 = 3^(1101₂) = 3^8 · 3^4 · 3^1
3 → 3² → 3⁴ → 3⁸ 을 차례로 제곱해 만들고, 비트가 1 인 것만 곱한다.
```

파이썬 내장 `pow(a, k, n)` 이 이 방식으로 동작한다.

### 최대공약수와 유클리드 호제법

gcd(a, b) 는 a 와 b 를 모두 나누는 가장 큰 양의 정수다. gcd(a, b) = 1 이면 a 와 b 는 **서로소**다.

**핵심 보조정리.** gcd(a, b) = gcd(b, a mod b).

> **증명.** a = qb + r 이라 하자. d 가 a 와 b 를 나누면 r = a − qb 도 나눈다. 반대로 d 가 b 와 r 을 나누면 a = qb + r 도 나눈다. 따라서 (a, b) 의 공약수 집합과 (b, r) 의 공약수 집합이 같고, 최댓값도 같다. ∎

이것을 b 가 0 이 될 때까지 반복하는 것이 **유클리드 호제법**이다. gcd(a, 0) = a.

```
gcd(252, 105)
= gcd(105, 42)     252 = 2·105 + 42
= gcd(42, 21)      105 = 2·42  + 21
= gcd(21, 0)       42  = 2·21  + 0
= 21
```

**얼마나 빠른가.** 두 단계마다 큰 쪽 수가 적어도 절반 아래로 준다(0 < b ≤ a 이면 a mod b < a/2 가 항상 성립한다). 그래서 단계 수는 O(log min(a, b)) 다. 최악의 입력은 연속한 피보나치 수다(라메의 정리). 수백 자리 수에도 수백 단계면 끝난다.

### 확장 유클리드와 베주 항등식

**베주 항등식.** 모든 정수 a, b 에 대해 ax + by = gcd(a, b) 를 만족하는 정수 x, y 가 존재한다.

확장 유클리드 호제법은 gcd 를 구하는 과정을 거꾸로 따라가며 x, y 를 함께 구한다. 252·x + 105·y = 21 의 한 해는 x = −2, y = 5 다. 이 x, y 가 다음 글에서 모듈러 역원이 된다.

**따름정리.** ax + by 꼴로 쓸 수 있는 정수는 정확히 gcd(a, b) 의 배수들이다. 예를 들어 6 원과 10 원짜리 동전(거스름 허용)으로는 2 원 단위 금액만 만들 수 있다.

### 소수와 산술의 기본 정리

1 보다 크고 1 과 자기 자신 말고는 약수가 없는 수가 소수다. 2 이상의 모든 정수는 소수의 곱으로 **유일하게**(순서를 무시하면) 분해된다. 존재는 004번 글에서 강한 귀납법으로 보였고, 유일성은 "소수 p 가 ab 를 나누면 p 는 a 나 b 를 나눈다" 는 유클리드 보조정리로 보인다. 이 보조정리는 베주 항등식으로 증명된다.

## 직접 해 보기

유클리드 호제법과 확장 유클리드를 직접 구현하고 표준 라이브러리와 비교한다. `math.gcd` 와 3 인자 `pow` 는 공식 문서에 정의된 내장 기능이다.

```python
import math

def gcd(a, b):
    steps = 0
    while b:
        a, b = b, a % b
        steps += 1
    return a, steps

def ext_gcd(a, b):
    """ax + by = g 인 (g, x, y)"""
    if b == 0:
        return a, 1, 0
    g, x1, y1 = ext_gcd(b, a % b)
    return g, y1, x1 - (a // b) * y1

print(gcd(252, 105), math.gcd(252, 105))
g, x, y = ext_gcd(252, 105)
print(g, x, y, 252 * x + 105 * y)

# 최악의 경우: 연속 피보나치 수
F = [0, 1]
while len(F) < 80:
    F.append(F[-1] + F[-2])
print(F[79], F[78], gcd(F[79], F[78]))

# 언어별 나머지 차이: 파이썬 % 와 C 방식(math.fmod) 비교
print(-7 % 3, math.fmod(-7, 3))

# 빠른 거듭제곱
def power_mod(a, k, n):
    result, base = 1, a % n
    while k:
        if k & 1:
            result = result * base % n
        base = base * base % n
        k >>= 1
    return result
print(power_mod(3, 13, 1000), pow(3, 13, 1000), 3**13 % 1000)
print(pow(7, 10**18, 10**9 + 7))
```

실행 결과다.

```
(21, 3) 21
21 -2 5 21
14472334024676221 8944394323791464 (1, 77)
2 -1.0
323 323 323
259616729
```

마지막 줄은 7 의 10¹⁸ 제곱을 10⁹ + 7 로 나눈 나머지다. 10¹⁸ 은 이진수로 60 자리이므로 제곱 60 번과 곱셈 60 번 이하면 끝난다. `math.fmod` 는 C 의 `fmod` 와 같은 규칙(피제수의 부호)을 따른다고 공식 문서에 적혀 있다.

## 현업에서는

- **해시 테이블과 샤딩.** `hash(key) % N` 으로 버킷이나 샤드를 고르면 N 이 바뀔 때 거의 모든 키의 위치가 바뀐다. 키 k 가 같은 자리에 남으려면 k mod N 과 k mod (N+1) 이 같아야 하는데, 그런 키는 대략 1/(N+1) 정도뿐이다. 노드를 늘렸다 줄였다 하는 캐시 클러스터가 일관된 해싱(consistent hashing)을 쓰는 이유다.
- **음수 나머지 버그.** 자바에서 `Math.abs(key.hashCode()) % n` 은 `hashCode()` 가 `Integer.MIN_VALUE` 일 때 `abs` 결과가 여전히 음수라서 음수 인덱스를 만든다. 자바는 이 문제를 위해 결과가 항상 0 이상인 `Math.floorMod` 를 제공한다.
- **정수 오버플로.** 고정 폭 정수의 덧셈은 mod 2ᵏ 산술이다. 큰 수를 다루는 해시·체크섬 코드는 이 성질을 일부러 이용하고, 잔액 계산 같은 코드는 이 성질 때문에 사고가 난다.
- **암호.** RSA 는 수백 자리 수의 모듈러 거듭제곱을 쓰고, 키 생성에서 확장 유클리드로 비밀 지수를 구한다([RFC 8017, PKCS #1: RSA Cryptography Specifications](https://www.rfc-editor.org/rfc/rfc8017)). 다음 글에서 자세히 본다.

## 확인 문제

1. 파이썬에서 `-13 % 5` 의 값은? C 에서 `-13 % 5` 는?
2. gcd(1071, 462) 를 유클리드 호제법으로 구하라.
3. 2¹⁰⁰ mod 7 을 손으로 구하라.
4. 6x + 9y = 4 를 만족하는 정수 x, y 가 존재하는가?

### 풀이

1. 파이썬은 2, C 는 −3.
2. 1071 = 2·462 + 147, 462 = 3·147 + 21, 147 = 7·21 + 0. 답은 21.
3. 2³ = 8 ≡ 1 (mod 7) 이므로 2¹⁰⁰ = (2³)³³·2 ≡ 2 (mod 7).
4. 없다. gcd(6, 9) = 3 이고 4 는 3 의 배수가 아니다.

## 더 읽을거리 (References)

- Eric Lehman, F. Thomson Leighton, Albert R. Meyer, *Mathematics for Computer Science*, 9장 Number Theory — [MIT 공개 PDF](https://courses.csail.mit.edu/6.042/spring18/mcs.pdf)
- [Python Documentation, math — gcd(), fmod()](https://docs.python.org/3/library/math.html)
- [Python Language Reference, Binary arithmetic operations](https://docs.python.org/3/reference/expressions.html#binary-arithmetic-operations)
- Donald E. Knuth, *The Art of Computer Programming, Vol. 2: Seminumerical Algorithms*, 3판, Addison-Wesley, 4.5.2절(유클리드 알고리즘)
