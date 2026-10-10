---
layout: post
title: "[CS300 #027] 메모리 모델 — 스택과 힙"
date: 2026-10-10 18:27:00 +0900
categories: [cs]
tags: [cs300, programming, memory, stack, heap]
---

컴퓨터공학 300 주제 시리즈의 027번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

스택은 함수 호출마다 자동으로 쌓이고 사라지는 빠르고 작은 메모리이고, 힙은 크기와 수명을 실행 중에 정하는 크고 유연한 메모리다. 값이 어디에 사는지가 수명과 성능과 버그 종류를 결정한다.

## 왜 필요한가

`StackOverflowError`, 세그멘테이션 폴트, 메모리 누수, 쿠버네티스 파드의 `OOMKilled`. 서로 다른 증상 같지만 뿌리는 하나다. 프로그램이 메모리를 어디에서 얼마나 오래 쓰는지 몰랐다는 것이다.

가비지 컬렉션(#028), Rust 의 소유권(#040), JVM 튜닝(#039)을 이해하려면 먼저 스택과 힙이라는 두 영역의 성격을 알아야 한다.

## 핵심 개념

### 프로세스의 메모리 배치

운영체제는 프로세스마다 가상 주소 공간을 준다. 리눅스 x86-64 의 전형적인 배치는 대략 이렇다(세부는 운영체제 파트에서 다룬다).

```
높은 주소
 ┌──────────────────┐
 │ 스택  ↓ 아래로 자람 │  함수 프레임: 지역 변수, 반환 주소
 │        ...        │
 │ (공유 라이브러리, mmap 영역) │
 │        ...        │
 │ 힙    ↑ 위로 자람  │  malloc / new 로 얻은 메모리
 ├──────────────────┤
 │ BSS / 데이터       │  전역·정적 변수
 │ 텍스트(코드)       │  기계어
 └──────────────────┘
낮은 주소
```

### 스택

함수를 호출하면 **스택 프레임(활성 레코드)** 이 하나 쌓인다. 프레임에는 매개변수, 지역 변수, 돌아갈 주소, 저장해 둔 레지스터가 들어간다. 함수가 반환하면 스택 포인터를 되돌리는 것만으로 프레임 전체가 해제된다.

- **할당·해제가 극히 싸다.** 포인터 하나를 더하고 빼면 끝이다.
- **크기를 컴파일 시점에 알아야 한다**(대부분 언어). 프레임 크기가 고정되어야 하기 때문이다.
- **수명이 호출과 묶인다.** 함수가 끝나면 그 지역 변수는 더 이상 유효하지 않다.
- **작다.** 스레드마다 하나씩 있고, 리눅스 메인 스레드 기본값은 수 MB 수준이다(`ulimit -s` 로 확인). 넘치면 스택 오버플로다.

Rust 공식 책은 스택을 "후입선출", 힙을 "덜 조직된" 공간으로 대비하며, 스택에 넣는 데이터는 크기가 알려지고 고정되어야 한다고 설명한다([The Rust Book 4.1](https://doc.rust-lang.org/book/ch04-01-what-is-ownership.html)).

### 힙

크기를 실행 중에야 알거나, 함수가 끝난 뒤에도 살아야 하는 데이터는 힙에 둔다. C 는 `malloc`/`free`, C++ 은 `new`/`delete`, Java·Python·Go 는 객체 생성 시 런타임이 힙에서 할당한다.

- **유연하다.** 아무 크기나, 아무 때나 할당하고 원하는 만큼 살린다.
- **비싸다.** 할당기가 빈 블록을 찾고, 관리 정보를 갱신한다. 멀티스레드에서는 경쟁도 생긴다.
- **해제 책임이 있다.** 수동(C), 소유권(Rust, C++ RAII), 자동(GC) 중 하나로 누군가 돌려줘야 한다.
- **단편화.** 크기가 다른 블록을 할당·해제하다 보면 빈 공간이 잘게 흩어진다.

### 무엇이 어디에 사는가

| 언어 | 스택 | 힙 |
|---|---|---|
| C | 지역 변수, 고정 크기 배열 | `malloc` 결과 |
| Java | 지역 기본형(`int` 등), 객체 **참조** | 모든 객체와 배열 |
| Python (CPython) | 인터프리터의 C 프레임 | 사실상 모든 객체 (전용 힙) |
| Rust | 기본적으로 모든 값 | `Box`, `Vec`, `String` 의 내용물 |

Java 가상 머신 명세는 스레드마다 **JVM 스택**이 있고 프레임을 담으며, 모든 스레드가 공유하는 **힙**에 객체와 배열이 할당된다고 정의한다. 스택이 허용 크기를 넘으면 `StackOverflowError` 를 던진다고도 명시한다([JVMS §2.5](https://docs.oracle.com/javase/specs/jvms/se21/html/jvms-2.html)). CPython 문서는 모든 Python 객체와 자료구조가 인터프리터가 관리하는 **사설 힙**에 있다고 설명한다([Memory Management](https://docs.python.org/3/c-api/memory.html)).

주의할 점: "Java 에서 `int` 는 스택에 산다"는 지역 변수일 때만 맞다. 객체의 필드인 `int` 는 객체와 함께 힙에 있다. 또 JIT 컴파일러는 탈출 분석으로 일부 객체를 힙에 두지 않기도 한다. 위치는 언어 의미가 아니라 구현의 선택이다.

### 대표적인 버그

| 버그 | 원인 | 결과 |
|---|---|---|
| 스택 오버플로 | 너무 깊은 재귀, 거대한 지역 배열 | 크래시, `StackOverflowError` |
| 댕글링 포인터 | 끝난 함수의 지역 변수 주소를 반환 | 정의되지 않은 동작 |
| 해제 후 사용 | `free` 뒤 포인터 사용 | 데이터 오염, 보안 취약점 |
| 이중 해제 | 같은 블록 `free` 두 번 | 할당기 상태 파괴 |
| 메모리 누수 | 해제 안 함 / 참조를 계속 쥠 | 점진적 메모리 증가, OOM |

해제 후 사용과 버퍼 오버플로는 메모리 안전성 취약점의 큰 몫을 차지한다. GC 언어와 Rust 는 이 부류를 언어 차원에서 막으려 한다.

## 직접 해 보기

C 로 각 영역의 주소를 찍어 본다(`gcc -O0`, 리눅스 x86-64).

```c
#include <stdio.h>
#include <stdlib.h>
static int global_counter = 0;

void frame(int depth, char *prev) {
    char local;
    if (prev) printf("depth %d: local at %p (diff %ld bytes)\n",
                     depth, (void*)&local, (long)(prev - &local));
    if (depth < 3) frame(depth + 1, &local);
}

int main(void) {
    int *heap = malloc(sizeof(int) * 4);
    int on_stack = 0;
    printf("global : %p\nheap   : %p\nstack  : %p\n",
           (void*)&global_counter, (void*)heap, (void*)&on_stack);
    frame(0, NULL);
    free(heap);
    return 0;
}
```

한 번 실행한 출력:

```
global : 0x56754db2a014
heap   : 0x5675736342a0
stack  : 0x7fff245f231c
depth 1: local at 0x7fff245f22c7 (diff 48 bytes)
depth 2: local at 0x7fff245f2297 (diff 48 bytes)
depth 3: local at 0x7fff245f2267 (diff 48 bytes)
```

주소 공간 배치 무작위화(ASLR) 때문에 절댓값은 실행할 때마다 바뀐다. 그래도 관계는 같다. 전역과 힙은 낮은 쪽, 스택은 높은 쪽에 있고, 재귀가 깊어질수록 지역 변수 주소가 **작아진다**. 스택이 아래로 자란다는 뜻이다. 이 환경에서 `frame` 한 번의 프레임은 48바이트였다.

Java 에서 스레드 스택 크기를 바꿔 보면 오버플로 깊이가 달라진다.

```java
public class Deep {
    static int depth = 0;
    static void down() { depth++; down(); }
    public static void main(String[] a) {
        try { down(); } catch (StackOverflowError e) {
            System.out.println("StackOverflowError at depth ~" + (depth / 1000) * 1000);
        }
    }
}
```

OpenJDK 25 에서 `java -Xss256k Deep` 은 약 2,000, `java -Xss2m Deep` 은 약 49,000 깊이에서 멈췄다. 수치는 JVM 버전·JIT 상태·플랫폼마다 다르므로 비율만 참고한다.

## 현업에서는

- **컨테이너 메모리 한도**: 쿠버네티스에서 컨테이너가 `limits.memory` 를 넘기면 커널 OOM 킬러에 의해 종료될 수 있다([Resource Management for Pods and Containers](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/)). JVM 은 힙 외에도 스레드 스택, 메타스페이스, 다이렉트 버퍼를 쓰므로 힙 최대치를 한도와 같게 잡으면 위험하다.
- **스레드 수와 스택**: 스레드 1,000개면 스택도 1,000개다. 스레드 풀을 크게 잡은 서비스가 힙은 여유 있는데 메모리가 모자라는 이유다. Java 의 가상 스레드는 스택을 힙에 저장해 이 비용을 줄인다([JEP 444](https://openjdk.org/jeps/444)).
- **할당 줄이기**: 지연 시간이 중요한 경로에서는 힙 할당 자체를 줄인다. 객체 재사용, 미리 크기를 잡은 버퍼, 스택에 놓을 수 있는 값 타입이 그 수단이다.
- **누수 추적**: Python 은 `tracemalloc` 으로 할당 위치별 메모리를 스냅숏으로 비교할 수 있다([tracemalloc](https://docs.python.org/3/library/tracemalloc.html)). 홈랩 클러스터에서 파드 메모리가 며칠에 걸쳐 오르면 먼저 이런 도구로 증가하는 할당 지점을 찾는다.

## 확인 문제

1. 스택 할당이 힙 할당보다 빠른 근본 이유는?
2. C 함수에서 지역 배열의 주소를 반환하면 왜 위험한가?
3. Java 에서 `Point p = new Point(1, 2);` 를 지역 변수로 선언했다. `p` 와 `Point` 객체는 각각 어디에 있는가(일반적인 경우)?
4. 위 C 실험에서 재귀가 깊어질수록 주소가 작아지는 것은 무엇을 뜻하는가?
5. 파드의 JVM 힙을 `limits.memory` 와 똑같이 설정하면 생길 수 있는 문제는?

### 풀이

1. 스택은 스택 포인터를 움직이는 것만으로 할당·해제가 끝난다. 빈 블록 탐색이나 관리 정보 갱신이 없다.
2. 함수가 반환하면 그 프레임은 해제되어 다음 호출이 덮어쓴다. 반환된 포인터는 댕글링 포인터이고, 사용하면 정의되지 않은 동작이다.
3. 참조 변수 `p` 는 그 메서드의 스택 프레임에, `Point` 객체는 힙에 있다. 단 JIT 의 탈출 분석이 객체 할당을 없앨 수도 있다.
4. 이 플랫폼에서 스택이 높은 주소에서 낮은 주소 방향으로 자란다는 뜻이다.
5. 힙 밖의 메모리(스레드 스택, 메타스페이스, 네이티브 버퍼, JIT 코드 캐시)까지 합치면 한도를 넘어 OOMKilled 로 종료될 수 있다.

## 더 읽을거리 (References)

- The Java Virtual Machine Specification, Java SE 21, [Chapter 2 — 2.5 Run-Time Data Areas](https://docs.oracle.com/javase/specs/jvms/se21/html/jvms-2.html)
- The Rust Programming Language, [What Is Ownership? — The Stack and the Heap](https://doc.rust-lang.org/book/ch04-01-what-is-ownership.html)
- Python/C API, [Memory Management](https://docs.python.org/3/c-api/memory.html)
- Kubernetes Docs, [Resource Management for Pods and Containers](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/)
