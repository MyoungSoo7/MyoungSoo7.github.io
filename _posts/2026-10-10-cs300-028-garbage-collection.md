---
layout: post
title: "[CS300 #028] 가비지 컬렉션의 원리 — 더 이상 닿을 수 없는 것을 치운다"
date: 2026-10-10 18:28:00 +0900
categories: [cs]
tags: [cs300, programming, garbage-collection, memory, jvm]
---

컴퓨터공학 300 주제 시리즈의 028번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

가비지 컬렉션은 프로그램이 더 이상 도달할 수 없는 힙 객체를 런타임이 찾아 자동으로 회수하는 일이며, 핵심 기법은 참조 계수와 추적(마크) 두 계열이다.

## 왜 필요한가

#027 에서 본 것처럼 힙 메모리는 누군가 돌려줘야 한다. C 처럼 사람이 직접 `free` 하면 해제 후 사용, 이중 해제, 누수가 생긴다. 가비지 컬렉터(GC)는 이 책임을 런타임으로 옮긴다. Java, Python, Go, JavaScript, C# 이 모두 GC 를 쓴다.

그런데 GC 가 있다고 메모리 문제가 사라지지는 않는다. 참조를 계속 쥐고 있으면 누수는 그대로 생기고, GC 가 도는 동안 애플리케이션이 멈추는 지연(pause)이 응답 시간을 흔든다. 원리를 알아야 튜닝도 장애 분석도 할 수 있다.

## 핵심 개념

### 쓰레기의 정의: 도달 가능성

GC 는 "앞으로 쓰이지 않을 객체"를 알 수 없다. 대신 더 쉬운 근사를 쓴다. **루트(root)에서 참조를 따라가 닿을 수 없는 객체는 앞으로도 쓸 수 없다.** 루트는 스택의 지역 변수, 전역 변수, CPU 레지스터 같은 프로그램이 직접 쥔 참조다.

```
 루트(스택·전역)
   │
   ▼
  [A] ──> [B] ──> [C]        A, B, C: 도달 가능 → 살아 있다
                               
  [D] ──> [E]                D, E: 어떤 루트에서도 닿지 않음 → 쓰레기
   ▲       │
   └───────┘                 (서로 참조해도 쓰레기다)
```

이 아이디어는 1960년 매카시(McCarthy)가 Lisp 를 설명한 논문에서 처음 체계적으로 나왔다. 그가 묘사한 방식이 오늘날 마크-스윕의 원형이다.

### 계열 1: 참조 계수

모든 객체가 "나를 가리키는 참조 수"를 들고 있다. 참조가 생기면 +1, 사라지면 -1, 0 이 되는 순간 즉시 해제한다.

- 장점: 해제가 즉각적이고 예측 가능하다. 긴 멈춤이 없다.
- 단점: 모든 대입마다 계수 갱신 비용이 든다. 그리고 **순환 참조를 회수하지 못한다.** 위 그림의 D 와 E 는 서로를 가리켜 계수가 1 에서 내려가지 않는다.

CPython 이 참조 계수를 기본으로 쓴다. 순환은 보조 GC 가 따로 처리한다.

### 계열 2: 추적 GC

루트에서 출발해 닿는 객체를 모두 표시하고, 표시되지 않은 것을 치운다.

| 알고리즘 | 동작 | 특징 |
|---|---|---|
| 마크-스윕 | 표시 후 힙 전체를 훑어 미표시 블록 해제 | 객체를 옮기지 않음, 단편화 발생 |
| 마크-컴팩트 | 표시 후 살아 있는 객체를 한쪽으로 모음 | 단편화 제거, 이동 비용 |
| 복사(semi-space) | 살아 있는 객체만 다른 공간으로 복사 | 할당이 포인터 증가로 빨라짐, 공간 2배 |

### 세대별 가설

대부분의 객체는 금방 죽는다. 요청 처리 중 만든 임시 문자열, 반복자, DTO 가 그렇다. 이를 **약한 세대 가설**이라 한다. 그래서 힙을 젊은 세대와 늙은 세대로 나누고, 젊은 세대만 자주 수집한다. 젊은 세대는 대부분 쓰레기라 살아남은 소수만 복사하면 되므로 싸다. 여러 번 살아남은 객체는 늙은 세대로 승격된다.

CPython 내부 문서도 이 가설("Most objects die young")을 근거로 세대를 나눈다고 설명한다. 새 객체는 0세대에서 시작하고, 수집에서 살아남으면 다음 세대로 옮겨진다([CPython GC internals](https://github.com/python/cpython/blob/main/InternalDocs/garbage_collector.md)).

### CPython 의 순환 탐지

CPython 의 순환 수집기는 컨테이너 객체(리스트, 딕셔너리, 인스턴스 등)만 추적한다. 방법이 영리하다.

1. 수집 대상 집합의 각 객체에 대해 `gc_ref` 를 참조 계수로 초기화한다.
2. 집합 **안의** 객체가 서로를 가리키는 참조만큼 `gc_ref` 를 뺀다.
3. 남은 `gc_ref > 0` 인 객체는 집합 **밖**에서 참조되는 것이니 살아 있다. 거기서 닿는 객체도 살린다.
4. 나머지는 순환 쓰레기다.

루트를 따로 알 필요 없이 참조 계수만으로 외부 참조를 찾아내는 것이다.

### 멈춤과 동시 수집

단순한 추적 GC 는 수집하는 동안 애플리케이션 스레드를 모두 멈춘다(stop-the-world). 힙이 크면 멈춤도 길다. 현대 GC 는 표시 작업 대부분을 애플리케이션과 **동시에** 수행해 멈춤을 줄인다. 대가는 CPU 사용량 증가와 쓰기 장벽(write barrier) 같은 추가 비용이다.

- **Java**: Java 21 GC 튜닝 가이드에 따르면 대부분의 하드웨어·OS 구성에서 기본은 G1 이다. G1 은 대부분의 작업을 동시에 하는 세대별 수집기다([HotSpot GC Tuning Guide](https://docs.oracle.com/en/java/javase/21/gctuning/available-collectors.html)). 짧은 멈춤이 중요한 경우 ZGC 를 고를 수 있고, 세대별 ZGC 가 JEP 439 로 들어왔다([JEP 439](https://openjdk.org/jeps/439)).
- **Go**: 공식 GC 가이드는 Go 의 GC 가 마크-스윕 방식이며 객체를 옮기지 않고(non-moving), 대부분 애플리케이션과 동시에 동작한다고 설명한다. 조절 손잡이는 `GOGC` 다([A Guide to the Go Garbage Collector](https://tip.golang.org/doc/gc-guide)).

### GC 언어의 누수

GC 는 **도달 불가능한** 것만 치운다. 도달 가능하지만 다시는 안 쓰는 객체는 영원히 남는다. 크기 제한 없는 캐시, 해제 안 한 이벤트 리스너, 전역 리스트에 계속 쌓이는 로그 객체가 전형적인 GC 언어의 누수다. 약한 참조(weak reference)는 "이 참조만으로는 객체를 살려 두지 말라"는 표시로, 캐시 구현에 쓰인다([weakref](https://docs.python.org/3/library/weakref.html)).

## 직접 해 보기

Python 3.12.3 에서 실행:

```python
import gc, sys, weakref

class Node:
    def __init__(self, name):
        self.name = name
        self.other = None
    def __del__(self):
        print("free", self.name)

a = Node("a")
print(sys.getrefcount(a))   # 2  (a + getrefcount 인자로 잡힌 임시 참조)
b = a
print(sys.getrefcount(a))   # 3
del b
del a                       # free a   계수가 0 이 되자마자 즉시 해제

gc.disable()                # 순환 수집기 끄기
x = Node("x"); y = Node("y")
x.other = y; y.other = x    # 순환
del x, y                    # 아무것도 출력되지 않는다: 계수가 0 이 안 됨
print("gc.collect() ->", gc.collect())
# free x
# free y
# gc.collect() -> 25        (회수한 객체 수, 실행 환경마다 다르다)
gc.enable()
print(gc.get_threshold())   # (700, 10, 10)

class Big: pass
obj = Big()
r = weakref.ref(obj)
print(r() is obj)           # True
del obj
print(r())                  # None   약한 참조는 객체를 살려 두지 않는다
```

`gc.collect()` 의 반환값은 두 `Node` 뿐 아니라 각 인스턴스의 속성 딕셔너리 등 함께 회수된 객체 수를 센 값이다.

## 현업에서는

- **JVM 파드 튜닝**: 컨테이너 안 JVM 은 컨테이너 메모리 한도를 인식해 기본 힙 크기를 정한다. 실무에서는 `-XX:MaxRAMPercentage` 로 한도 대비 힙 비율을 정하고, 나머지를 스택·메타스페이스·네이티브 메모리에 남긴다.
- **GC 로그부터 본다**: 응답 시간이 주기적으로 튀면 GC 멈춤을 먼저 의심한다. Java 는 `-Xlog:gc*` 로 수집 종류, 멈춤 시간, 수집 전후 힙 크기를 남길 수 있다.
- **Go 의 메모리 한도**: 컨테이너에서 Go 서비스를 돌릴 때 `GOMEMLIMIT` 로 런타임에 메모리 상한을 알려 주면 한도에 가까워질수록 GC 를 더 자주 돌린다. Go GC 가이드가 이 설정을 다룬다.
- **누수 진단**: 힙 덤프에서 "누가 이 객체를 붙잡고 있나(GC 루트까지의 경로)"를 찾는 것이 GC 언어 누수 분석의 핵심이다.

## 확인 문제

1. GC 가 "쓰레기"를 판단하는 기준은 무엇이며, 왜 "앞으로 안 쓸 객체"를 직접 판단하지 않는가?
2. 참조 계수 방식이 회수하지 못하는 경우는?
3. 세대별 GC 가 젊은 세대를 자주, 늙은 세대를 드물게 수집하는 근거는?
4. CPython 순환 수집기에서 `gc_ref` 가 0 보다 크게 남은 객체는 무엇을 뜻하는가?
5. GC 언어에서도 메모리 누수가 생기는 대표적인 경우를 두 가지 들라.

### 풀이

1. 루트에서 참조를 따라 도달할 수 있는지가 기준이다. 앞으로의 사용 여부는 일반적으로 결정 불가능하므로, 도달 불가능이라는 안전한 근사를 쓴다.
2. 객체들이 서로를 가리키는 순환 참조. 외부 참조가 없어도 계수가 0 이 되지 않는다.
3. 약한 세대 가설. 대부분의 객체가 금방 죽으므로 젊은 세대 수집이 적은 비용으로 많은 메모리를 회수한다.
4. 수집 대상 집합 밖에서 그 객체를 참조하는 것이 있다는 뜻이다. 따라서 살아 있고, 그 객체에서 닿는 것도 살아 있다.
5. 크기 제한 없는 캐시나 전역 컬렉션에 객체가 계속 쌓이는 경우, 등록한 리스너·콜백을 해제하지 않는 경우.

## 더 읽을거리 (References)

- CPython, [Garbage collector design (InternalDocs)](https://github.com/python/cpython/blob/main/InternalDocs/garbage_collector.md)
- Python Docs, [gc — Garbage Collector interface](https://docs.python.org/3/library/gc.html)
- Oracle, [HotSpot Virtual Machine Garbage Collection Tuning Guide, Java SE 21](https://docs.oracle.com/en/java/javase/21/gctuning/)
- Go, [A Guide to the Go Garbage Collector](https://tip.golang.org/doc/gc-guide)
- John McCarthy, "Recursive Functions of Symbolic Expressions and Their Computation by Machine, Part I", CACM 3(4), 1960
