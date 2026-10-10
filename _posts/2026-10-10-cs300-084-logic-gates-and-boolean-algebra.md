---
layout: post
title: "[CS300 #084] 논리 게이트와 불 대수 — 0 과 1 로 하는 계산의 문법"
date: 2026-10-10 19:24:00 +0900
categories: [cs]
tags: [cs300, computer-architecture, logic-gates, boolean-algebra, digital-logic]
---

컴퓨터공학 300 주제 시리즈의 084번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

불 대수는 참·거짓 두 값만 갖는 변수에 AND·OR·NOT 을 적용하는 대수이고, 논리 게이트는 그 연산을 트랜지스터로 만든 물리 부품이다. CPU 의 덧셈기도, 메모리 주소 해석기도 결국 이 게이트 몇 종류의 조합이다.

## 왜 필요한가

소프트웨어 개발자가 트랜지스터를 직접 배치할 일은 거의 없다. 그래도 이 층을 한 번은 알아야 하는 이유가 있다.

- `&`, `|`, `^`, `~` 비트 연산이 왜 그렇게 싼지 이해된다. 하드웨어 입장에선 게이트 한 층이다.
- 복잡한 조건문을 드모르간 법칙으로 정리해 읽기 쉬운 코드로 바꿀 수 있다.
- 다음 글(조합·순차 회로)과 데이터패스·파이프라인을 이해하는 기초가 된다.

클로드 섀넌은 MIT 석사 논문(학위 기록상 1940년)에서 릴레이 스위치 회로를 불 대수로 분석·설계할 수 있음을 보였다. 논리식과 회로가 같은 것이라는 이 관찰이 디지털 설계의 출발점이다.

## 핵심 개념

### 기본 연산과 진리표

| A | B | A AND B | A OR B | NOT A | A XOR B | A NAND B | A NOR B |
|---|---|---|---|---|---|---|---|
| 0 | 0 | 0 | 0 | 1 | 0 | 1 | 1 |
| 0 | 1 | 0 | 1 | 1 | 1 | 1 | 0 |
| 1 | 0 | 0 | 1 | 0 | 1 | 1 | 0 |
| 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 |

표기는 분야마다 다르다. 회로 쪽은 AND 를 곱(A·B), OR 를 합(A+B), NOT 을 윗줄이나 A' 로 적는다. 이 글은 A·B, A+B, A' 를 쓴다.

### 불 대수의 법칙

| 이름 | AND 형 | OR 형 |
|---|---|---|
| 항등 | A·1 = A | A+0 = A |
| 지배 | A·0 = 0 | A+1 = 1 |
| 멱등 | A·A = A | A+A = A |
| 보수 | A·A' = 0 | A+A' = 1 |
| 교환 | A·B = B·A | A+B = B+A |
| 결합 | (A·B)·C = A·(B·C) | (A+B)+C = A+(B+C) |
| 분배 | A·(B+C) = A·B + A·C | A+(B·C) = (A+B)·(A+C) |
| 흡수 | A·(A+B) = A | A + A·B = A |
| 드모르간 | (A·B)' = A' + B' | (A+B)' = A'·B' |

일반 대수와 다른 점은 OR 위에 AND 가 분배되는 것뿐 아니라 AND 위에 OR 도 분배된다는 것이다. 그리고 모든 법칙은 AND↔OR, 0↔1 을 맞바꾸면 짝이 되는 법칙이 나온다(쌍대성).

### 진리표에서 식으로: 곱의 합

어떤 진리표든 "출력이 1 인 줄마다 입력 조건을 AND 로 묶고, 그것들을 OR 로 잇는" 방식으로 식을 만들 수 있다. 이것을 곱의 합(SOP) 정규형이라 한다. XOR 의 출력이 1 인 줄은 (0,1), (1,0) 이므로 다음과 같다.

```
A XOR B = A'·B + A·B'
```

이 사실은 중요하다. **AND, OR, NOT 세 가지만 있으면 어떤 불 함수든 만들 수 있다.** 이런 집합을 함수적으로 완전하다고 한다.

### NAND 하나로 충분하다

NAND 는 단독으로 함수적으로 완전하다. NOT, AND, OR 를 NAND 로 만들 수 있기 때문이다.

```
NOT A    = A NAND A
A AND B  = NOT(A NAND B)
A OR B   = (NOT A) NAND (NOT B)     ← 드모르간
```

NOR 도 같은 성질이 있다. 실제 CMOS 공정에서 NAND·NOR 는 트랜지스터 4개로 만들 수 있지만 AND·OR 는 그 뒤에 인버터가 붙어 6개가 된다. 그래서 회로 합성 도구는 NAND·NOR 중심으로 회로를 짠다.

### 식 간소화

회로 비용은 게이트 수와 단계 수로 매긴다. 같은 함수를 더 적은 게이트로 만드는 것이 간소화다.

```
F = A·B + A·B'
  = A·(B + B')     분배
  = A·1            보수
  = A              항등
```

변수가 4~5개면 카르노 맵으로 손으로 정리하고, 그보다 크면 도구(Quine–McCluskey, 휴리스틱 최소화기)가 한다.

### 게이트 지연

게이트는 즉시 반응하지 않는다. 입력이 바뀌고 출력이 안정될 때까지 짧은 지연이 있다. 입력에서 출력까지 거치는 가장 긴 게이트 경로(임계 경로)의 지연이 회로가 버틸 수 있는 클록 주기를 정한다. 파이프라이닝(#090)은 이 임계 경로를 잘게 나누는 기술이다.

## 직접 해 보기

NAND 하나로 나머지 게이트를 만들고, 드모르간 법칙을 전수 검사한다. python3 로 실행해 확인했다.

```python
from itertools import product

def NAND(a, b): return 1 - (a & b)
def NOT(a):     return NAND(a, a)
def AND(a, b):  return NOT(NAND(a, b))
def OR(a, b):   return NAND(NOT(a), NOT(b))
def XOR(a, b):
    n = NAND(a, b)
    return NAND(NAND(a, n), NAND(b, n))

print("a b | AND OR XOR NAND")
for a, b in product((0, 1), repeat=2):
    print(a, b, "|", AND(a, b), " ", OR(a, b), " ", XOR(a, b), "  ", NAND(a, b))

ok = all(NOT(AND(a, b)) == OR(NOT(a), NOT(b)) and
         NOT(OR(a, b)) == AND(NOT(a), NOT(b))
         for a, b in product((0, 1), repeat=2))
print("De Morgan:", ok)

x, y = 0b1100, 0b1010
print(f"{x & y:04b} {x | y:04b} {x ^ y:04b} {~x & 0xF:04b}")
```

출력:

```
a b | AND OR XOR NAND
0 0 | 0   0   0    1
0 1 | 0   1   1    1
1 0 | 0   1   1    1
1 1 | 1   1   0    0
De Morgan: True
1000 1110 0110 0011
```

XOR 는 NAND 4개로 만들었다. 마지막 줄은 정수 비트 연산이 비트마다 같은 게이트를 나란히 적용한 것과 같다는 점을 보여 준다. 64비트 CPU 의 `AND` 명령 하나는 AND 게이트 64개가 동시에 동작하는 것이다.

## 현업에서는

- **조건문 정리**: `if not (a and b)` 는 `if not a or not b` 와 같다. 리뷰에서 부정이 겹친 조건을 드모르간으로 풀어 쓰면 읽기 쉬워진다.
- **비트마스크**: 권한·기능 플래그는 `flags & MASK` 로 검사하고 `flags | BIT` 로 켜고 `flags & ~BIT` 로 끈다. 리눅스 파일 권한 비트, 네트워크 서브넷 계산, 블룸 필터가 모두 이 방식이다.
- **XOR 활용**: XOR 는 같은 값을 두 번 적용하면 원래로 돌아온다(A ⊕ B ⊕ B = A). RAID 5 의 패리티, 체크섬, 스트림 암호의 키 스트림 결합이 이 성질을 쓴다.
- **FPGA**: 하드웨어 설계자는 Verilog·VHDL 로 불 함수를 기술하고 합성 도구가 이를 게이트(실제로는 룩업 테이블)로 바꾼다. 소프트웨어의 "컴파일" 에 해당하는 단계다.

## 확인 문제

1. A + A·B 를 간소화하라.
2. (A + B)' 를 드모르간 법칙으로 바꿔라.
3. AND, OR, NOT 이 함수적으로 완전한 이유를 한 문장으로 말하라.
4. NOR 만으로 NOT 을 만드는 방법은.

### 풀이

1. A·1 + A·B = A·(1 + B) = A·1 = A (흡수 법칙).
2. A'·B'.
3. 임의의 진리표를 출력이 1 인 줄들의 AND 항을 OR 로 묶는 곱의 합 형태로 적을 수 있기 때문이다.
4. A NOR A = (A + A)' = A'.

## 더 읽을거리 (References)

- Claude E. Shannon, [A Symbolic Analysis of Relay and Switching Circuits](https://dspace.mit.edu/handle/1721.1/11173), MIT 석사 논문, 1940 (MIT DSpace)
- [Nand to Tetris — 프로젝트 1: Boolean Logic](https://www.nand2tetris.org/)
- Python 공식 문서, [Expressions — Binary bitwise operations](https://docs.python.org/3/reference/expressions.html)
- David Money Harris, Sarah L. Harris, *Digital Design and Computer Architecture*, 2nd ed., Morgan Kaufmann. 1~2장.
