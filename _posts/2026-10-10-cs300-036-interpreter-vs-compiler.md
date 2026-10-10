---
layout: post
title: "[CS300 #036] 인터프리터와 컴파일러의 차이 — 번역은 언제 일어나는가"
date: 2026-10-10 18:36:00 +0900
categories: [cs]
tags: [cs300, programming, compiler, interpreter, jit]
---

컴퓨터공학 300 주제 시리즈의 036번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

컴파일러는 프로그램을 실행 전에 다른 언어(대개 기계어나 바이트코드)로 번역하고, 인터프리터는 프로그램을 읽으면서 바로 실행한다. 현대 언어 구현은 대부분 둘을 섞으며, "컴파일 언어/인터프리터 언어"는 언어가 아니라 구현의 성질이다.

## 왜 필요한가

"파이썬은 인터프리터 언어라 느리다", "자바는 컴파일 언어인데 왜 JVM 이 필요한가" 같은 말은 반쯤 맞다. 실제 CPython 은 소스를 먼저 바이트코드로 컴파일하고, Java 는 바이트코드를 인터프리트하다가 뜨거운 부분만 기계어로 다시 컴파일한다.

이 구분을 정확히 알면 성능 특성을 예측할 수 있다. 첫 요청이 왜 느린지(JIT 워밍업), 컨테이너 이미지에 무엇을 넣어야 하는지(바이너리 하나인지, 런타임이 필요한지), 오류가 언제 드러나는지(빌드 시점인지 실행 시점인지)가 모두 여기서 갈린다.

## 핵심 개념

### 번역의 큰 그림

모든 언어 구현은 대략 같은 단계를 거친다. 나이스트롬의 『Crafting Interpreters』는 이를 산을 오르내리는 그림으로 설명한다. 소스를 분석하며 올라가 의미를 파악하고, 목표 형태로 내려온다([A Map of the Territory](https://craftinginterpreters.com/a-map-of-the-territory.html)).

```
 소스 코드
   │ 어휘 분석 (토큰)          ← #037
   │ 구문 분석 (AST)           ← #037
   │ 의미 분석 (이름·타입 확인)  ← #038
   ▼
 중간 표현(IR) ── 최적화
   │
   ├─▶ 기계어 생성 ─▶ 실행 파일        (AOT 컴파일러: gcc, rustc, go)
   ├─▶ 바이트코드 ─▶ 가상 머신이 실행   (javac+JVM, CPython)
   └─▶ AST 를 직접 순회하며 실행        (트리 순회 인터프리터)
```

### 컴파일러 (AOT)

AOT(ahead-of-time) 컴파일러는 실행 전에 전체 프로그램을 목표 기계의 명령어로 번역한다.

- 실행 시 번역 비용이 없다. 시작이 빠르고 예측 가능하다.
- 프로그램 전체를 보고 오래 최적화할 수 있다(인라이닝, 루프 최적화, 레지스터 할당).
- 결과물은 특정 CPU·OS 용이다. 다른 플랫폼에는 다시 컴파일해야 한다.
- 타입 오류 같은 많은 오류가 빌드 시점에 드러난다.

### 인터프리터

인터프리터는 프로그램을 번역해 저장하지 않고 **실행하면서** 의미를 수행한다.

- **트리 순회 인터프리터**: AST 노드를 재귀적으로 방문하며 계산한다. 구현이 가장 쉽고 느리다.
- **바이트코드 인터프리터**: 먼저 간단한 가상 명령어(바이트코드)로 컴파일한 뒤, 가상 머신이 명령어를 하나씩 읽어 실행한다. 명령어가 조밀한 배열이라 캐시 효율이 좋고 트리 순회보다 빠르다.

인터프리터가 느린 이유는 명령어마다 "무슨 명령인가?"를 판별하는 디스패치 비용과, 동적 언어라면 값의 타입을 매번 확인하는 비용이 붙기 때문이다.

### CPython 은 실제로 무엇을 하나

CPython 은 소스를 **바이트코드로 컴파일**한 뒤 그것을 **인터프리트**한다. 컴파일 결과는 `__pycache__/모듈.cpython-312.pyc` 같은 파일로 캐시된다. Python 용어집은 바이트코드를 "인터프리터 내부 표현"이며 가상 머신에서 실행된다고 정의하고, `dis` 모듈로 볼 수 있다고 안내한다([Glossary — bytecode](https://docs.python.org/3/glossary.html#term-bytecode), [dis](https://docs.python.org/3/library/dis.html)). 바이트코드는 CPython 버전마다 바뀌는 구현 세부이며 언어 명세의 일부가 아니다.

Python 3.13 에는 실험적인 JIT 컴파일러가 추가되었다([PEP 744](https://peps.python.org/pep-0744/)). 기본 빌드에서는 꺼져 있다.

### JIT: 실행 중에 컴파일하기

JIT(just-in-time) 컴파일러는 실행 중에 자주 쓰이는 코드를 기계어로 컴파일한다. Java HotSpot VM 이 대표적이다. Oracle 문서는 HotSpot 이 표준 인터프리터로 애플리케이션을 시작하고, 실행 중 코드를 분석해 성능에 중요한 "핫스팟"만 컴파일하며, 드물게 쓰이는 대부분의 코드는 컴파일하지 않는다고 설명한다([Java Virtual Machine Technology Overview](https://docs.oracle.com/en/java/javase/21/vm/java-virtual-machine-technology-overview.html)).

JIT 는 AOT 가 못 하는 일을 할 수 있다. **실제 실행 프로파일**을 보고 최적화한다. 예를 들어 어떤 가상 메서드 호출 지점이 실제로는 늘 한 구현만 부른다면 그것을 인라인한다. 가정이 깨지면 최적화된 코드를 버리고 인터프리터로 돌아간다(역최적화).

대가는 **워밍업**이다. 시작 직후에는 인터프리터로 돌기 때문에 느리고, 컴파일 자체도 CPU 를 쓴다.

### 비교

| | AOT 컴파일 | 바이트코드 인터프리터 | JIT |
|---|---|---|---|
| 번역 시점 | 실행 전 | 실행 전(바이트코드) + 실행 중(해석) | 실행 중 |
| 시작 속도 | 빠름 | 빠름 | 느림(워밍업) |
| 최고 성능 | 높음 | 낮음 | 높음, 프로파일 기반 |
| 이식성 | 플랫폼별 빌드 | VM 이 있으면 어디서나 | VM 이 있으면 어디서나 |
| 예 | C, Rust, Go | CPython, Lua | HotSpot JVM, V8 |

### 언어 vs 구현

같은 언어도 구현에 따라 다르게 실행된다. Python 은 CPython(바이트코드 인터프리터) 외에 PyPy(JIT) 구현이 있다. Java 도 GraalVM 네이티브 이미지로 AOT 컴파일할 수 있다. 그래서 "Python 은 인터프리터 언어다"보다 "CPython 은 바이트코드 인터프리터다"가 정확한 말이다.

## 직접 해 보기

CPython 3.12.3 이 함수를 어떤 바이트코드로 바꾸는지 본다.

```python
import dis
def f(a, b):
    return a * b + 1
dis.dis(f)
```

```
  2           0 RESUME                   0

  3           2 LOAD_FAST                0 (a)
              4 LOAD_FAST                1 (b)
              6 BINARY_OP                5 (*)
             10 LOAD_CONST               1 (1)
             12 BINARY_OP                0 (+)
             16 RETURN_VALUE
```

값을 스택에 올리고(LOAD), 연산이 스택 위 두 값을 꺼내 결과를 다시 올리는 **스택 머신**이다. 같은 함수를 C 로 쓰고 `gcc -O2 -S` (GCC 13.3, x86-64)로 보면 레지스터 명령 두 개가 된다.

```
f:
	endbr64
	imull	%esi, %edi
	leal	1(%rdi), %eax
	ret
```

이제 같은 식 `a * b + 1` 을 두 방식으로 직접 실행해 보자.

```python
tree = ("+", ("*", ("var", "a"), ("var", "b")), ("num", 1))

def interp(node, env):                 # 트리 순회 인터프리터
    op = node[0]
    if op == "num": return node[1]
    if op == "var": return env[node[1]]
    l, r = interp(node[1], env), interp(node[2], env)
    return l + r if op == "+" else l * r

def compile_(node, code):              # 스택 바이트코드 컴파일러
    op = node[0]
    if op == "num": code.append(("PUSH", node[1]))
    elif op == "var": code.append(("LOAD", node[1]))
    else:
        compile_(node[1], code); compile_(node[2], code)
        code.append(("ADD",) if op == "+" else ("MUL",))
    return code

def run(code, env):                    # 가상 머신
    stack = []
    for ins in code:
        if ins[0] == "PUSH": stack.append(ins[1])
        elif ins[0] == "LOAD": stack.append(env[ins[1]])
        else:
            r, l = stack.pop(), stack.pop()
            stack.append(l + r if ins[0] == "ADD" else l * r)
    return stack.pop()

env = {"a": 6, "b": 7}
print(interp(tree, env))               # 43
code = compile_(tree, [])
print(code)   # [('LOAD', 'a'), ('LOAD', 'b'), ('MUL',), ('PUSH', 1), ('ADD',)]
print(run(code, env))                  # 43
```

컴파일러가 만든 명령 목록이 CPython 의 `dis` 출력과 같은 모양이라는 점에 주목하자. 컴파일은 한 번, 실행은 여러 번 할 수 있다.

## 현업에서는

- **컨테이너 이미지 크기**: Go·Rust 서비스는 정적 바이너리 하나를 거의 빈 베이스 이미지에 넣을 수 있다. Python·Node.js 서비스는 런타임과 의존성이 함께 들어가 이미지가 커진다.
- **JVM 워밍업과 롤링 배포**: 쿠버네티스에서 JVM 파드를 새로 띄우면 처음 몇 분은 JIT 전이라 지연 시간이 높다. readiness 프로브를 통과하자마자 전체 트래픽을 받으면 p99 지연이 튄다. 워밍업 요청을 보내거나 트래픽을 점진적으로 늘린다.
- **서버리스 콜드 스타트**: 시작 시간이 과금과 지연에 직결되는 환경에서는 AOT 컴파일(GraalVM 네이티브 이미지 등)을 검토한다. 대신 최고 처리량은 JIT 보다 낮을 수 있다.
- **.pyc 와 배포**: 읽기 전용 파일 시스템 컨테이너에서는 `__pycache__` 를 쓰지 못해 매번 컴파일한다. 이미지 빌드 때 `python -m compileall` 로 미리 만들어 두면 시작이 빨라진다.

## 확인 문제

1. "Python 은 인터프리터 언어다"라는 문장을 더 정확하게 고쳐 보라.
2. 트리 순회 인터프리터보다 바이트코드 인터프리터가 대체로 빠른 이유는?
3. JIT 가 AOT 보다 유리할 수 있는 최적화의 예를 하나 들라.
4. JVM 서비스에서 배포 직후 지연 시간이 높은 이유는?
5. 위 `compile_` 함수에 뺄셈을 추가하면 `run` 에서 피연산자 꺼내는 순서가 왜 중요한가?

### 풀이

1. "Python 의 표준 구현 CPython 은 소스를 바이트코드로 컴파일한 뒤 가상 머신에서 인터프리트한다." 언어가 아니라 구현의 성질이다.
2. 바이트코드는 조밀한 선형 배열이라 포인터를 따라 트리를 오갈 필요가 없고 캐시 효율이 좋으며, 이름 해석 같은 작업을 컴파일 시점에 미리 해 둘 수 있다.
3. 실제 실행 프로파일을 보고, 늘 한 구현만 호출되는 가상 메서드 호출을 인라인하는 것.
4. 시작 직후에는 인터프리터로 실행되고, 핫스팟이 JIT 로 컴파일되기 전까지 느리기 때문이다(워밍업).
5. 스택에서 먼저 꺼낸 값이 오른쪽 피연산자다. 순서를 바꾸면 `a - b` 가 `b - a` 로 계산된다.

## 더 읽을거리 (References)

- Robert Nystrom, *Crafting Interpreters*, [A Map of the Territory](https://craftinginterpreters.com/a-map-of-the-territory.html)
- Python Docs, [dis — Disassembler for Python bytecode](https://docs.python.org/3/library/dis.html)
- Oracle, [Java Virtual Machine Technology Overview](https://docs.oracle.com/en/java/javase/21/vm/java-virtual-machine-technology-overview.html)
- [PEP 744 — JIT Compilation](https://peps.python.org/pep-0744/)
- Aho, Lam, Sethi, Ullman, *Compilers: Principles, Techniques, and Tools*, 2nd ed., Addison-Wesley, 2006
