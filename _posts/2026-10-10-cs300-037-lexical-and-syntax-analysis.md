---
layout: post
title: "[CS300 #037] 어휘 분석과 구문 분석 — 글자를 나무로 바꾸기"
date: 2026-10-10 18:37:00 +0900
categories: [cs]
tags: [cs300, programming, lexer, parser, grammar]
---

컴퓨터공학 300 주제 시리즈의 037번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

어휘 분석(렉싱)은 글자의 흐름을 의미 있는 낱말(토큰)로 자르고, 구문 분석(파싱)은 토큰의 흐름을 문법 규칙에 따라 트리(AST)로 조립한다. 컴파일러, 인터프리터, 설정 파일 리더, 쿼리 엔진이 모두 이 두 단계로 시작한다.

## 왜 필요한가

컴퓨터에게 `2 + 3*4` 는 문자 7개일 뿐이다. 이것이 "3 과 4 를 곱한 뒤 2 를 더하라"는 뜻이 되려면 누군가 공백을 버리고, 숫자와 연산자를 구분하고, 곱셈이 먼저라는 규칙을 적용해 구조를 세워야 한다.

이 기술은 컴파일러 개발자만의 것이 아니다. 로그 형식 해석, 템플릿 엔진, 검색 쿼리 문법, DSL, JSON·YAML 파서, 코드 포매터와 린터가 모두 렉서와 파서다. 정규식으로 버티다가 괄호 중첩 앞에서 무너진 경험이 있다면 이 글이 그 다음 단계다.

## 핵심 개념

### 두 단계로 나누는 이유

```
 "x = 2 + 3*4"
      │  어휘 분석 (lexer / scanner / tokenizer)
      ▼
 NAME(x) OP(=) NUM(2) OP(+) NUM(3) OP(*) NUM(4)
      │  구문 분석 (parser)
      ▼
        Assign
        /    \
      x      (+)
            /   \
           2    (*)
               /   \
              3     4
```

렉서는 **정규 언어** 수준의 일을 한다. 숫자, 식별자, 키워드, 문자열 리터럴은 정규식이나 유한 오토마타로 인식할 수 있다. 파서는 **문맥 자유 언어** 수준의 일을 한다. 괄호 중첩, 연산자 우선순위, 블록 구조는 정규식으로 표현할 수 없고 스택(재귀)이 필요하다. 일을 나누면 각 단계가 단순해지고, 파서는 공백·주석 같은 잡음을 신경 쓰지 않아도 된다.

### 어휘 분석

렉서의 출력은 **토큰**의 나열이다. 토큰은 종류(NUMBER, NAME, OP)와 원문 문자열(렉심), 위치(줄·열)를 가진다. 위치 정보는 오류 메시지에 쓰인다.

렉서가 해결해야 하는 전형적인 문제:
- **최장 일치**: `>=` 를 `>` 와 `=` 가 아닌 한 토큰으로, `iffy` 를 키워드 `if` 가 아닌 식별자로.
- **키워드와 식별자 구분**: 식별자로 읽은 뒤 예약어 표에서 찾는다.
- **공백의 의미**: 대부분 버리지만 Python 은 들여쓰기를 INDENT/DEDENT 토큰으로 바꾼다. Python 언어 레퍼런스의 어휘 분석 장이 이 규칙을 정의한다([Lexical analysis](https://docs.python.org/3/reference/lexical_analysis.html)).

### 문법: BNF 로 쓰는 규칙

구문은 **문맥 자유 문법(CFG)** 으로 기술한다. 사칙연산의 문법을 우선순위가 드러나게 쓰면 이렇다.

```
expr   := term   (('+' | '-') term)*
term   := factor (('*' | '/') factor)*
factor := NUMBER | '(' expr ')' | '-' factor
```

규칙이 층을 이루는 방식이 곧 우선순위다. `expr` 은 `term` 들의 합이고, `term` 은 `factor` 들의 곱이다. 곱셈이 한 층 더 깊이 있으므로 먼저 묶인다. 반복 `(...)*` 을 왼쪽부터 쌓으면 **왼쪽 결합**이 된다. `10 - 4 - 3` 이 `(10 - 4) - 3` 으로 묶이는 이유다.

### 모호성

문법이 같은 문자열에 대해 두 개 이상의 트리를 허용하면 **모호하다**. `expr := expr '-' expr | NUMBER` 는 `10 - 4 - 3` 을 두 가지로 묶을 수 있어 결과가 3 또는 9 가 된다. 위처럼 층을 나누거나, 파서 생성기에 우선순위·결합 방향을 선언해 모호성을 없앤다. 유명한 예로 "매달린 else"가 있다. `if a if b s1 else s2` 의 `else` 가 어느 `if` 의 것인지 문법이 정해야 한다.

### 파싱 전략

| 전략 | 방향 | 특징 | 예 |
|---|---|---|---|
| 재귀 하강 (LL) | 하향식 | 규칙 하나 = 함수 하나. 손으로 쓰기 쉽고 오류 메시지가 좋다. 왼쪽 재귀 규칙은 반복으로 바꿔야 한다 | GCC·Clang 의 C/C++ 파서, 많은 손 파서 |
| LR / LALR | 상향식 | 토큰을 스택에 쌓고(shift) 규칙에 맞으면 줄인다(reduce). 표는 생성기가 만든다 | yacc, bison |
| PEG | 하향식 | 선택이 순서를 가진다(먼저 맞는 쪽). 모호성이 없다. 무한 되돌아가기를 메모이제이션으로 막는다(packrat) | CPython 3.9+ |

CPython 은 3.9 부터 LL(1) 파서를 PEG 기반 파서로 교체했다. PEP 617 은 LL(1) 제약 때문에 문법에 우회책이 쌓였고, PEG 가 더 자연스러운 문법 표현을 허용한다고 설명한다([PEP 617](https://peps.python.org/pep-0617/)). 현재 Python 전체 문법은 레퍼런스에 PEG 형식으로 실려 있다([Full Grammar specification](https://docs.python.org/3/reference/grammar.html)).

### 구체 구문 트리와 추상 구문 트리

파스 트리(구체 구문 트리)는 괄호, 쉼표 같은 모든 토큰을 담는다. **AST** 는 의미에 필요한 것만 남긴다. `(2 + 3)` 의 괄호는 트리 모양에 이미 반영되었으므로 AST 에는 노드로 남지 않는다. 이후 단계(타입 검사 #038, 코드 생성 #036)는 모두 AST 를 입력으로 받는다.

## 직접 해 보기

위 문법을 그대로 옮긴 재귀 하강 파서다. Python 3.12.3 에서 실행했다.

```python
import re
TOKEN = re.compile(r"\s*(?:(\d+)|(.))")

def tokenize(src):
    tokens = []
    for num, op in TOKEN.findall(src):
        if num: tokens.append(("NUM", int(num)))
        elif op in "+-*/()": tokens.append(("OP", op))
        elif op.strip(): raise SyntaxError(f"알 수 없는 문자 {op!r}")
    tokens.append(("EOF", None))
    return tokens

class Parser:
    def __init__(self, tokens):
        self.toks, self.i = tokens, 0
    def peek(self): return self.toks[self.i]
    def eat(self, kind, val=None):
        t = self.peek()
        if t[0] != kind or (val is not None and t[1] != val):
            raise SyntaxError(f"{kind} {val or ''} 기대, {t} 발견")
        self.i += 1
        return t
    def expr(self):                     # expr := term (('+'|'-') term)*
        node = self.term()
        while self.peek() in (("OP", "+"), ("OP", "-")):
            op = self.eat("OP")[1]
            node = (op, node, self.term())     # 왼쪽으로 쌓아 왼쪽 결합
        return node
    def term(self):                     # term := factor (('*'|'/') factor)*
        node = self.factor()
        while self.peek() in (("OP", "*"), ("OP", "/")):
            op = self.eat("OP")[1]
            node = (op, node, self.factor())
        return node
    def factor(self):                   # factor := NUM | '(' expr ')' | '-' factor
        t = self.peek()
        if t[0] == "NUM":
            return self.eat("NUM")[1]
        if t == ("OP", "-"):
            self.eat("OP"); return ("neg", self.factor())
        self.eat("OP", "(")
        node = self.expr()
        self.eat("OP", ")")
        return node

def parse(src):
    p = Parser(tokenize(src))
    tree = p.expr()
    p.eat("EOF")                        # 남은 토큰이 있으면 오류
    return tree
```

실행 결과(평가 함수 `ev` 는 트리를 재귀로 계산하는 10줄짜리 함수다):

```
2 + 3*4      -> ('+', 2, ('*', 3, 4)) = 14
(2 + 3)*4    -> ('*', ('+', 2, 3), 4) = 20
10 - 4 - 3   -> ('-', ('-', 10, 4), 3) = 3
-(1+2)*3     -> ('*', ('neg', ('+', 1, 2)), 3) = -9
2 +          -> SyntaxError: OP ( 기대, ('EOF', None) 발견
2 $ 3        -> SyntaxError: 알 수 없는 문자 '$'
(1 + 2       -> SyntaxError: OP ) 기대, ('EOF', None) 발견
```

Python 자신의 렉서와 파서 결과와 비교해 보자.

```python
import ast, tokenize, io
print(ast.dump(ast.parse("2 + 3*4", mode="eval").body))
# BinOp(left=Constant(value=2), op=Add(),
#       right=BinOp(left=Constant(value=3), op=Mult(), right=Constant(value=4)))
for tok in tokenize.generate_tokens(io.StringIO("x = 2 + 3*4\n").readline):
    print(tokenize.tok_name[tok.type], repr(tok.string))
# NAME 'x' / OP '=' / NUMBER '2' / OP '+' / NUMBER '3' / OP '*' / NUMBER '4' / NEWLINE '\n' / ENDMARKER ''
```

우리 파서의 `('+', 2, ('*', 3, 4))` 와 CPython AST 의 모양이 같다.

## 현업에서는

- **정규식의 한계를 알 때**: 중첩 괄호가 있는 쿼리 문법, 연산자 우선순위가 있는 필터 식을 정규식으로 처리하려다 실패한 코드는 작은 재귀 하강 파서로 바꾸면 짧고 정확해진다.
- **AST 기반 도구**: 린터, 포매터, 코드모드(대량 리팩터링) 도구는 소스를 AST 로 파싱해 규칙을 검사하거나 트리를 고쳐 다시 출력한다. Python 의 `ast` 모듈만으로도 "특정 함수 호출을 모두 찾기" 같은 정적 분석을 쉽게 만든다([ast](https://docs.python.org/3/library/ast.html)).
- **YAML 의 함정**: 쿠버네티스 매니페스트를 쓰는 YAML 은 들여쓰기와 암묵적 타입 해석을 렉싱 단계에서 처리한다. 따옴표 없는 `on`, `yes`, `08` 같은 값이 파서 버전에 따라 불리언이나 숫자로 읽히는 사고가 있다. 문자열은 따옴표로 감싸는 습관이 안전하다.
- **보안**: 직접 만든 파서에 깊게 중첩된 입력을 넣으면 재귀 깊이가 폭발한다(#024). 중첩 깊이와 입력 크기에 상한을 둔다.

## 확인 문제

1. 렉서와 파서가 각각 다루는 언어의 계층(정규, 문맥 자유)은?
2. 위 문법에서 `*` 가 `+` 보다 먼저 묶이는 이유는 문법의 어떤 구조 때문인가?
3. `expr := expr '-' NUMBER | NUMBER` 같은 왼쪽 재귀 규칙을 재귀 하강 파서로 그대로 구현하면 어떤 문제가 생기는가?
4. 파스 트리와 AST 의 차이는?
5. 위 파서에 거듭제곱 `^`(오른쪽 결합, `*` 보다 높은 우선순위)을 추가하려면 문법을 어떻게 바꾸는가?

### 풀이

1. 렉서는 정규 언어(정규식·유한 오토마타), 파서는 문맥 자유 언어(스택이 필요한 중첩 구조).
2. `term` 이 `factor` 의 곱으로 정의되고 `expr` 이 `term` 의 합으로 정의되어, 곱셈이 트리의 더 깊은 층에서 먼저 묶이기 때문이다.
3. `expr()` 이 토큰을 소비하기 전에 자기 자신을 다시 호출해 무한 재귀에 빠진다. 반복(`while`)으로 바꿔야 한다.
4. 파스 트리는 괄호·구분자를 포함한 모든 문법 기호를 담고, AST 는 의미에 필요한 구조만 남긴다.
5. `factor` 위에 층을 하나 추가한다. `power := unary ('^' power)?` 처럼 오른쪽을 자기 자신으로 재귀시켜 오른쪽 결합을 만들고, `term` 은 `power` 의 곱으로 바꾼다.

## 더 읽을거리 (References)

- Robert Nystrom, *Crafting Interpreters*, [Scanning](https://craftinginterpreters.com/scanning.html), [Parsing Expressions](https://craftinginterpreters.com/parsing-expressions.html)
- Python Language Reference, [Lexical analysis](https://docs.python.org/3/reference/lexical_analysis.html), [Full Grammar specification](https://docs.python.org/3/reference/grammar.html)
- [PEP 617 — New PEG parser for CPython](https://peps.python.org/pep-0617/)
- Aho, Lam, Sethi, Ullman, *Compilers: Principles, Techniques, and Tools*, 2nd ed., Addison-Wesley, 2006 — 3장 어휘 분석, 4장 구문 분석
