---
layout: post
title: "[CS300 #039] JVM 과 바이트코드 — 한 번 컴파일해 어디서나 실행하는 구조"
date: 2026-10-10 18:39:00 +0900
categories: [cs]
tags: [cs300, programming, jvm, bytecode, java]
---

컴퓨터공학 300 주제 시리즈의 039번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

JVM 은 클래스 파일에 담긴 스택 기반 바이트코드를 읽어 검증하고, 처음엔 인터프리트하다가 자주 쓰이는 코드를 JIT 로 기계어로 바꿔 실행하는 가상 머신이며, Java 뿐 아니라 Kotlin·Scala 같은 언어의 공통 실행 기반이다.

## 왜 필요한가

Java 서버를 운영하다 보면 결국 JVM 을 만난다. `-Xmx` 를 얼마로 잡을지, 배포 직후 왜 느린지, `NoSuchMethodError` 가 왜 컴파일은 됐는데 실행 중에 나는지, `UnsupportedClassVersionError` 는 무엇인지. 모두 JVM 의 구조, 즉 클래스 로딩·바이트코드·JIT·메모리 영역을 알면 바로 풀린다.

#036 에서 본 "바이트코드 + 가상 머신 + JIT" 구조의 가장 성숙한 실물이 JVM 이다. 이 글은 실제 바이트코드를 열어 보며 그 구조를 따라간다.

## 핵심 개념

### 전체 흐름

```
 Calc.java ──javac──> Calc.class (바이트코드, 플랫폼 중립)
                          │
                ┌─────────▼──────────┐
                │ JVM                │
                │ 1. 클래스 로더      │  필요할 때 클래스 파일을 읽는다
                │ 2. 링크(검증·준비·해석) │  바이트코드가 안전한지 검사
                │ 3. 초기화           │  static 초기화 블록 실행
                │ 4. 실행 엔진        │  인터프리터 → JIT(C1, C2)
                │ 5. GC               │  힙 관리 (#028)
                └────────────────────┘
                          │
                  OS / CPU 기계어
```

"한 번 쓰고 어디서나 실행(Write once, run anywhere)"의 실체는 이것이다. `javac` 는 특정 CPU 가 아니라 **JVM 이라는 가상 기계**를 위한 코드를 만들고, 각 플랫폼의 JVM 구현이 그것을 실행한다. JVM 명세는 Java 언어와 독립적으로, 클래스 파일 형식과 명령어 집합만으로 가상 머신을 정의한다([JVMS SE 21](https://docs.oracle.com/javase/specs/jvms/se21/html/index.html)).

### 클래스 파일

클래스 파일은 정해진 이진 형식이다. 첫 4바이트는 매직 넘버 `0xCAFEBABE`, 그 다음은 부 버전과 주 버전이다. 주 버전은 이 파일을 만든 Java 버전을 나타낸다(Java 21 은 65, Java 25 는 69). 낮은 버전의 JVM 이 높은 주 버전 파일을 만나면 `UnsupportedClassVersionError` 를 던진다. 그 뒤에 **상수 풀**(문자열, 클래스·메서드 이름, 숫자 상수 표), 필드, 메서드, 속성이 이어진다([JVMS Chapter 4 — The class File Format](https://docs.oracle.com/javase/specs/jvms/se21/html/jvms-4.html)).

메서드 호출은 이름이 아니라 상수 풀 인덱스(`#15`)로 기록되고, 실제 메모리 주소로 바꾸는 일(해석, resolution)은 실행 중에 일어난다. 그래서 컴파일 때 있던 메서드가 실행 때 다른 버전의 라이브러리에 없으면 `NoSuchMethodError` 가 난다.

### 스택 기반 명령어

JVM 바이트코드는 **피연산자 스택** 위에서 동작한다. 각 메서드 호출은 프레임을 만들고, 프레임에는 지역 변수 배열과 피연산자 스택이 있다([JVMS §2.6 Frames](https://docs.oracle.com/javase/specs/jvms/se21/html/jvms-2.html)).

| 명령어 | 동작 |
|---|---|
| `iload_0` | 지역 변수 0번(int)을 스택에 올림 |
| `imul` / `iadd` | 스택 위 int 두 개를 꺼내 곱/합을 올림 |
| `iconst_1`, `bipush 6` | 상수를 올림 |
| `ireturn` | 스택 꼭대기 int 를 반환 |
| `invokestatic` / `invokevirtual` | 정적 / 가상 메서드 호출 |
| `getstatic`, `ldc` | 정적 필드, 상수 풀 값 로드 |

명령어 이름의 첫 글자가 타입을 나타낸다(`i` int, `l` long, `d` double, `a` 참조). 타입별로 명령이 따로 있기 때문에, 검증기가 바이트코드만 보고 타입 안전성을 확인할 수 있다([JVMS Chapter 6 — Instruction Set](https://docs.oracle.com/javase/specs/jvms/se21/html/jvms-6.html)).

스택 기반을 택한 이유는 **이식성과 간결함**이다. 레지스터 개수가 CPU 마다 다르므로 레지스터를 가정하지 않는 편이 어디서나 옮기기 쉽고, 피연산자를 명시하지 않아 명령이 짧다. 레지스터 할당은 JIT 가 대상 CPU 에 맞게 한다.

### 검증

JVM 은 신뢰할 수 없는 바이트코드를 실행할 수 있도록 설계되었다. 로딩 후 **검증기**가 스택 넘침·모자람이 없는지, 타입이 맞는지, 점프가 명령어 경계를 벗어나지 않는지, 초기화 안 된 객체를 쓰지 않는지 확인한다. 검증을 통과한 코드는 메모리를 임의로 건드릴 수 없다.

### 실행 엔진: 인터프리터와 계층형 JIT

HotSpot JVM 은 처음엔 바이트코드를 인터프리트하고, 호출 횟수와 루프 반복 수를 센다. 일정 기준을 넘으면 컴파일한다.

- **C1 (클라이언트 컴파일러)**: 빨리 컴파일하고, 프로파일 정보를 모으는 코드를 심는다.
- **C2 (서버 컴파일러)**: 모인 프로파일로 공격적으로 최적화한다(인라이닝, 탈출 분석, 루프 최적화).
- **OSR(On-Stack Replacement)**: 오래 도는 루프는 메서드가 끝나길 기다리지 않고 실행 도중 컴파일된 코드로 갈아탄다.
- **역최적화**: 최적화의 가정(예: 이 호출은 항상 같은 클래스)이 깨지면 컴파일된 코드를 버리고 인터프리터로 돌아간다.

Oracle 의 JVM 기술 개요는 HotSpot 이 성능에 중요한 부분만 컴파일하고 드물게 쓰이는 대부분의 코드는 컴파일하지 않는다고 설명한다([Java Virtual Machine Technology Overview](https://docs.oracle.com/en/java/javase/21/vm/java-virtual-machine-technology-overview.html)).

### 메모리 영역

JVM 명세의 런타임 데이터 영역은 스레드마다 있는 것(PC 레지스터, JVM 스택, 네이티브 메서드 스택)과 공유되는 것(힙, 메서드 영역)으로 나뉜다(#027). HotSpot 은 메서드 영역을 메타스페이스라는 네이티브 메모리에 구현한다. 그래서 `-Xmx` 로 힙만 제한해도 프로세스 전체 메모리는 그보다 크다.

### JVM 은 Java 만의 것이 아니다

JVM 이 받는 것은 Java 소스가 아니라 클래스 파일이다. Kotlin, Scala, Clojure, Groovy 가 모두 클래스 파일을 만든다. 그래서 서로의 라이브러리를 그대로 쓰고, 같은 GC·JIT·프로파일러를 공유한다.

## 직접 해 보기

OpenJDK 25 에서 실행했다.

```java
public class Calc {
    static int f(int a, int b) { return a * b + 1; }
    public static void main(String[] args) {
        String s = "hi";
        System.out.println(f(6, 7) + s.length());   // 45
    }
}
```

`javac Calc.java && javap -c Calc` ([javap 매뉴얼](https://docs.oracle.com/en/java/javase/21/docs/specs/man/javap.html)):

```
  static int f(int, int);
    Code:
       0: iload_0
       1: iload_1
       2: imul
       3: iconst_1
       4: iadd
       5: ireturn

  public static void main(java.lang.String[]);
    Code:
       0: ldc           #7                  // String hi
       2: astore_1
       3: getstatic     #9                  // Field java/lang/System.out:Ljava/io/PrintStream;
       6: bipush        6
       8: bipush        7
      10: invokestatic  #15                 // Method f:(II)I
      13: aload_1
      14: invokevirtual #21                 // Method java/lang/String.length:()I
      17: iadd
      18: invokevirtual #27                 // Method java/io/PrintStream.println:(I)V
      21: return
```

#036 에서 본 CPython 바이트코드(`LOAD_FAST`, `BINARY_OP`)와 구조가 같다. 차이는 JVM 명령에 타입(`i`)이 박혀 있다는 점이다. `(II)I` 는 "int 두 개를 받아 int 를 반환"하는 메서드 디스크립터다.

파일 앞부분과 버전도 보자.

```
$ xxd Calc.class | head -1
00000000: cafe babe 0000 0045 ...
$ javap -v Calc | grep major
  major version: 69
```

`0x45` 는 69, 즉 Java 25 로 컴파일된 파일이다.

JIT 가 언제 개입하는지는 `-XX:+PrintCompilation` 으로 볼 수 있다. `f` 를 5천만 번 부르는 루프를 돌리면 이런 줄이 나온다(일부).

```
48    8       3       Hot::f (6 bytes)
48    9       4       Hot::f (6 bytes)
49    8       3       Hot::f (6 bytes)   made not entrant: not used
51   10 %     3       Hot::main @ 4 (33 bytes)
52   12 %     4       Hot::main @ 4 (33 bytes)
```

대략 시작 후 밀리초, 컴파일 ID, 계층(3 은 C1 프로파일링, 4 는 C2) 순이다. `f` 가 먼저 C1 으로, 곧이어 C2 로 컴파일되고, C1 버전은 폐기된다. `%` 표시는 루프 도중 갈아타는 OSR 컴파일이다. 출력 형식은 JVM 버전마다 달라질 수 있는 진단 출력이다.

## 현업에서는

- **버전 불일치**: CI 는 Java 21 로 빌드했는데 운영 컨테이너 베이스 이미지가 Java 17 이면 `UnsupportedClassVersionError` 로 기동조차 못 한다. 빌드 `--release` 옵션과 런타임 이미지 버전을 맞춘다.
- **의존성 충돌**: 컴파일 때와 다른 버전의 라이브러리가 클래스패스에 올라가면 `NoSuchMethodError`, `NoClassDefFoundError` 가 실행 중에 난다. 바이트코드가 이름과 디스크립터로 메서드를 찾기 때문이다. `mvn dependency:tree` 같은 도구로 실제 선택된 버전을 확인한다.
- **컨테이너 메모리**: 쿠버네티스 파드의 메모리 한도는 힙 + 메타스페이스 + 스레드 스택 + 코드 캐시 + 다이렉트 버퍼를 모두 담아야 한다. 힙을 한도의 일부로만 잡는 이유다.
- **워밍업**: 롤링 배포 직후의 지연 상승은 인터프리터와 C1 단계 때문이다. 트래픽을 천천히 늘리거나 워밍업 요청을 먼저 보낸다. 시작 시간이 중요하면 CDS(클래스 데이터 공유)나 AOT 컴파일을 검토한다.

## 확인 문제

1. 클래스 파일의 첫 4바이트는 무엇이며, 주 버전 번호는 무엇을 알려 주는가?
2. JVM 바이트코드가 레지스터 기반이 아니라 스택 기반인 이유 하나를 들라.
3. 소스는 문제없이 컴파일됐는데 실행 중 `NoSuchMethodError` 가 나는 전형적인 원인은?
4. 위 `f` 의 바이트코드 `iload_0, iload_1, imul, iconst_1, iadd` 실행 중 피연산자 스택의 변화를 a=6, b=7 로 적어 보라.
5. OSR 컴파일은 어떤 상황을 위해 존재하는가?

### 풀이

1. 매직 넘버 `0xCAFEBABE`. 주 버전은 클래스 파일 형식의 버전, 즉 어느 Java 버전으로 컴파일됐는지를 알려 주며 JVM 이 지원하는지 판단하는 데 쓰인다.
2. CPU 마다 레지스터 수가 달라도 가정할 것이 없어 이식성이 좋고, 피연산자를 명시하지 않아 명령이 짧다. 레지스터 할당은 JIT 가 대상 CPU 에 맞춰 한다.
3. 컴파일 때 쓴 라이브러리 버전과 실행 때 클래스패스의 버전이 달라, 바이트코드가 가리키는 메서드 시그니처가 실행 시점 클래스에 없는 경우.
4. `[6]` → `[6, 7]` → `[42]` → `[42, 1]` → `[43]`, 그리고 `ireturn` 이 43 을 반환한다.
5. 메서드 호출 한 번 안에서 아주 오래 도는 루프처럼, 메서드가 끝나길 기다리면 컴파일된 코드를 쓸 기회가 없는 경우. 실행 중인 프레임을 컴파일된 코드로 교체한다.

## 더 읽을거리 (References)

- The Java Virtual Machine Specification, Java SE 21, [Chapter 4 — The class File Format](https://docs.oracle.com/javase/specs/jvms/se21/html/jvms-4.html), [Chapter 6 — The Java Virtual Machine Instruction Set](https://docs.oracle.com/javase/specs/jvms/se21/html/jvms-6.html)
- The Java Virtual Machine Specification, Java SE 21, [Chapter 2 — The Structure of the Java Virtual Machine](https://docs.oracle.com/javase/specs/jvms/se21/html/jvms-2.html)
- Oracle, [The javap Command](https://docs.oracle.com/en/java/javase/21/docs/specs/man/javap.html)
- Oracle, [Java Virtual Machine Technology Overview](https://docs.oracle.com/en/java/javase/21/vm/java-virtual-machine-technology-overview.html)
