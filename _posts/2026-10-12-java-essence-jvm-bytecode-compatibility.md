---
layout: post
title: "자바의 본질 — JVM·바이트코드·하위 호환성, 그리고 정적 타입 OOP 의 설계 철학"
date: 2026-10-12 00:11:42 +0900
categories: [java]
tags: [java, jvm, bytecode, class-file, backward-compatibility, preview-features, lts, oop]
---

자바·코틀린 20편 시리즈의 **자바 1편(J1)** 이다. 문법을 하나씩 보기 전에, "자바라는 언어는 무엇을 지키려고 설계됐는가" 를 먼저 정리한다. 이후 아홉 편에서 나오는 거의 모든 문법적 선택 — 타입 소거, default 메서드, record, 람다의 컴파일 방식, 프리뷰 기능 — 은 이 글의 세 가지 축으로 설명된다.

1. **JVM 과 클래스 파일** — 자바 언어와 실행 환경을 분리한 구조
2. **하위 호환성** — 25년 넘게 깨지 않으려는 약속과 그 대가
3. **정적 타입 OOP** — 컴파일 시점에 최대한 잡겠다는 태도

짝이 되는 코틀린 글은 [K1 코틀린의 본질: 실용주의와 자바 상호운용](https://myoungsoo7.github.io/2026/10/12/kotlin-essence-pragmatism-java-interop/) 이다. JVM 내부(JIT·GC·메모리 모델)는 이 블로그의 [JVM 내부 구조 글](/2026/06/22/jvm-internals-jit-gc-memory-model-escape-analysis/)과 [JVM 구조와 자바 버전 진화 글](/2026/05/29/jvm-structure-java-version-evolution-production-impact/)에서 따로 다뤘으므로 여기서는 "언어 설계" 관점에 집중한다.

---

## 1. 설계 목표 — 원래 무엇을 약속했나

### 1.1 The Java Language Environment 백서의 다섯 가지 목표

오라클이 지금도 공개하고 있는 백서 [The Java Language Environment](https://www.oracle.com/java/technologies/introduction-to-java.html) 는 자바 기술의 성격을 다음 제목들로 정리한다.

| 백서의 표제 | 실무 언어로 옮기면 |
|---|---|
| Simple, Object Oriented, and Familiar | C/C++ 개발자가 큰 재교육 없이 쓸 수 있는 객체지향 언어 |
| Robust and Secure | 컴파일·런타임 양쪽에서 오류를 일찍 잡고, 메모리를 직접 만지지 않는다 |
| Architecture Neutral and Portable | 하드웨어 독립적인 중간 형식(바이트코드)으로 배포한다 |
| High Performance | 해석 실행이 기본이지만 성능을 포기하지 않는다 |
| Interpreted, Threaded, and Dynamic | 바이트코드를 실행하는 런타임, 언어 수준 스레드, 동적 로딩 |

백서는 "architecture neutral intermediate format designed to transport code efficiently to multiple hardware and software platforms" 라고 바이트코드를 설명하고, 그 중립적이고 이식 가능한 플랫폼이 곧 **Java virtual machine** 이라고 말한다.

### 1.2 이 목표가 오늘 코드에 남긴 흔적

- **포인터 산술이 없다** → 배열 경계 검사, `NullPointerException`, GC. "Robust" 의 대가로 약간의 런타임 비용을 낸다.
- **바이트코드라는 중간층** → 같은 `.jar` 가 리눅스·맥·윈도에서 돈다. 동시에 코틀린·스칼라·그루비가 같은 JVM 위에 올라갈 수 있는 이유가 된다.
- **언어 수준 스레드** → `synchronized`, `Thread` 가 언어/표준 라이브러리에 1급으로 들어 있다. 이것이 가상 스레드까지 이어진다([J7](https://myoungsoo7.github.io/2026/10/12/java-concurrency-thread-to-virtual-threads/)).

---

## 2. JVM 과 클래스 파일 — 언어와 실행 환경의 분리

### 2.1 무엇인가: JVM 은 "자바" 를 모른다

JVM 명세 1.2 절은 이렇게 못 박는다.

> "The Java Virtual Machine knows nothing of the Java programming language, only of a particular binary format, the `class` file format."
> — [JVMS §1.2](https://docs.oracle.com/javase/specs/jvms/se21/html/jvms-1.html)

그리고 바로 이어서 "any language with functionality that can be expressed in terms of a valid `class` file can be hosted by the Java Virtual Machine" 라고 적는다. 코틀린이 자바와 섞여 돌 수 있는 근본 이유가 이 한 문장이다.

즉 자바 플랫폼은 **두 개의 명세**로 이루어져 있다.

| 명세 | 다루는 것 | 예 |
|---|---|---|
| JLS (Java Language Specification) | 소스 코드의 문법·의미 | 제네릭, 람다, record, sealed |
| JVMS (Java Virtual Machine Specification) | 클래스 파일 형식·바이트코드·링크·검증 | `invokevirtual`, `invokedynamic`, 상수 풀 |

언어 기능이 추가될 때 **JVMS 는 건드리지 않고 JLS 와 컴파일러(javac)만으로 해결**하려는 경향이 강하다. 제네릭의 타입 소거가 대표적이다([J2](https://myoungsoo7.github.io/2026/10/12/java-type-system-generics-erasure-pecs/)).

### 2.2 클래스 파일의 구조와 버전 번호

모든 클래스 파일은 매직 넘버 `0xCAFEBABE` 로 시작하고, 그 뒤에 `minor_version`, `major_version` 이 온다([JVMS §4.1](https://docs.oracle.com/javase/specs/jvms/se21/html/jvms-4.html)). 메이저 버전은 Java SE 릴리스마다 1씩 올라간다.

| Java SE | major_version |
|---|---|
| 5.0 | 49 |
| 8 | 52 |
| 11 | 55 |
| 17 | 61 |
| 21 | 65 |
| 25 | 69 |

(출처: [JVMS SE 21 표 4.1-A](https://docs.oracle.com/javase/specs/jvms/se21/html/jvms-4.html), [JVMS SE 25 §4.1](https://docs.oracle.com/javase/specs/jvms/se25/html/jvms-4.html))

직접 확인하는 방법:

```bash
javac Hello.java
javap -v Hello.class | grep -E "major|minor"
#   minor version: 0
#   major version: 65     ← JDK 21 로 컴파일
```

### 2.3 실무 사용사례: `UnsupportedClassVersionError` 읽는 법

운영에서 가장 흔한 버전 사고는 "빌드한 JDK 가 실행하는 JRE 보다 높다" 이다.

```text
java.lang.UnsupportedClassVersionError: com/example/App has been compiled by a more recent
version of the Java Runtime (class file version 65.0), this version of the Java Runtime
only recognizes class file versions up to 61.0
```

위 표만 있으면 바로 해석된다. 65 = Java 21 로 빌드했는데 61 = Java 17 런타임에서 띄웠다. 해결은 둘 중 하나다.

1. 런타임(컨테이너 베이스 이미지)을 21 로 올린다.
2. 빌드를 17 대상으로 내린다 — 이때 **`--release 17`** 을 쓴다(아래 2.4).

JVM 은 반대 방향, 즉 **옛 클래스 파일은 그대로 로드**한다. JVMS 는 Java SE 25 구현이 메이저 버전 "45 through 69, inclusive" 를 지원한다고 적는다([JVMS SE 25 §4.1](https://docs.oracle.com/javase/specs/jvms/se25/html/jvms-4.html)). 1990년대에 컴파일된 클래스도 원칙적으로 오늘의 JVM 에서 로드된다는 뜻이다.

### 2.4 `-source/-target` 대신 `--release`

JDK 9 의 [JEP 247](https://openjdk.org/jeps/247) 은 `--release N` 을 도입했다. `-source`/`-target` 만으로는 **언어 수준과 클래스 파일 버전만** 맞춰질 뿐, 새 JDK 에만 있는 API 를 실수로 호출하는 것을 막지 못한다. `--release N` 은 "N 버전에 문서화된 API" 를 기준으로 컴파일하므로 그 실수까지 컴파일 에러로 잡는다.

```bash
# 나쁜 예: JDK 21 로 17 대상 빌드. 21 에만 있는 API 를 써도 컴파일이 통과할 수 있다.
javac -source 17 -target 17 App.java

# 좋은 예
javac --release 17 App.java
```

```kotlin
// Gradle (Kotlin DSL) — toolchain 을 쓰거나, 최소한 release 를 지정
java {
    toolchain { languageVersion = JavaLanguageVersion.of(21) }
}
tasks.withType<JavaCompile> { options.release = 17 }
```

```xml
<!-- Maven -->
<properties>
  <maven.compiler.release>17</maven.compiler.release>
</properties>
```

**함정**: `List.reversed()` 는 Java 21 에 추가된 메서드다([List Javadoc](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/List.html)). `-target 17` 만 걸고 JDK 21 로 빌드하면 컴파일은 되지만 17 런타임에서 `NoSuchMethodError` 가 난다. `--release 17` 이면 컴파일 단계에서 막힌다.

### 2.5 멀티 릴리스 JAR

라이브러리 작성자는 한 JAR 에 버전별 구현을 같이 넣을 수 있다(JDK 9, [JEP 238](https://openjdk.org/jeps/238)). 매니페스트에 `Multi-Release: true` 를 넣고 `META-INF/versions/N/` 아래에 해당 버전용 클래스를 둔다. 오래된 런타임은 `versions` 디렉터리를 무시하고 루트 클래스를 쓴다.

```text
my-lib.jar
├── com/example/Util.class               ← 기본(가장 낮은 지원 버전)
└── META-INF
    ├── MANIFEST.MF                      ← Multi-Release: true
    └── versions
        └── 21
            └── com/example/Util.class   ← 21 이상에서 이 구현 사용
```

실무에서 직접 만들 일은 드물지만, 의존성 JAR 을 풀어보다 `META-INF/versions` 를 만나면 "버그가 특정 JDK 에서만 재현되는" 이유가 될 수 있다는 것만 기억하자.

---

## 3. 바이트코드 위의 언어 기능 — 무엇이 컴파일러 몫이고 무엇이 JVM 몫인가

### 3.1 컴파일러만으로 구현된 기능 (JVM 은 모름)

| 기능 | 바이트코드에 남는 모습 |
|---|---|
| 제네릭 | 타입 인자 소거 + 캐스트 삽입. 선언 정보는 `Signature` 속성에만 남음 |
| 오토박싱 | `Integer.valueOf(int)` / `intValue()` 호출 |
| 향상된 for | `Iterator` 호출 또는 인덱스 루프 |
| 내부 클래스 | `Outer$Inner.class` 별도 파일 |
| `var` | 아무것도 안 남음 — 추론된 정적 타입으로 기록 |

제네릭의 `Signature` 속성은 JVMS 가 "declaration in the Java programming language uses type variables or parameterized types" 인 클래스·메서드·필드·레코드 컴포넌트에 붙인다고 정의한다([JVMS §4.7.9](https://docs.oracle.com/javase/specs/jvms/se21/html/jvms-4.html)). 실행에는 쓰이지 않지만 리플렉션은 이것을 읽는다 — 스프링이 `List<String>` 같은 제네릭 정보를 알아내는 경로다.

### 3.2 JVM 의 도움을 받은 기능: `invokedynamic`

Java SE 7 의 JVMS 에 `invokedynamic` 명령어가 추가됐고([JVMS SE 7 6장](https://docs.oracle.com/javase/specs/jvms/se7/html/jvms-6.html)), Java 8 의 람다는 이것을 이용해 컴파일된다. `LambdaMetafactory` Javadoc 은 자신이 "typically used as bootstrap methods for `invokedynamic` call sites, to support the lambda expression and method reference expression features" 라고 설명한다([LambdaMetafactory](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/invoke/LambdaMetafactory.html)).

```java
Runnable r = () -> System.out.println("hi");
```

```text
// javap -c 결과 (요지)
invokedynamic #7, 0  // InvokeDynamic #0:run:()Ljava/lang/Runnable;
```

람다마다 익명 클래스 파일(`Foo$1.class`)이 생기지 않고, 실제 구현 객체는 **런타임에 처음 호출될 때** 연결된다. 이 덕분에 JDK 가 나중에 람다 구현 전략을 바꿔도 이미 컴파일된 바이트코드는 그대로 둘 수 있다. 문자열 연결(`+`)도 JDK 9 의 [JEP 280](https://openjdk.org/jeps/280) 이후 같은 방식(`invokedynamic`)으로 컴파일된다.

### 3.3 실무 함의

- **람다 스택트레이스에 `lambda$main$0` 같은 이름이 보이는 이유** — 람다 몸체는 원래 클래스의 private 합성 메서드로 컴파일된다.
- **바이트코드 조작 라이브러리(ByteBuddy, ASM, CGLIB)** 가 새 JDK 의 클래스 파일 버전을 지원해야 스프링·하이버네이트·Mockito 가 새 JDK 에서 돈다. "JDK 를 올렸더니 Mockito 가 터진다" 는 대부분 이 층위의 문제다.
- 프록시 기반 기능(AOP, `@Transactional`)이 바이트코드 생성에 의존한다는 점은 [J9](https://myoungsoo7.github.io/2026/10/12/java-how-spring-uses-java-reflection-proxy-di/) 에서 자세히 다룬다.

---

## 4. 하위 호환성 — 자바가 가장 비싸게 지키는 약속

### 4.1 무엇인가: 세 종류의 호환성

| 종류 | 질문 | 깨지면 |
|---|---|---|
| 소스 호환 | 옛 소스가 새 javac 로 컴파일되는가 | 컴파일 에러 |
| 바이너리 호환 | 옛 `.class` 가 새 라이브러리와 링크되는가 | `NoSuchMethodError`, `IncompatibleClassChangeError` |
| 동작 호환 | 같은 입력에 같은 결과인가 | 조용한 버그 |

JLS 13장은 바이너리 호환성을 이렇게 정의한다.

> "A change to a type is *binary compatible with* … pre-existing binaries if pre-existing binaries that previously linked without error will continue to link without error."
> — [JLS §13.2](https://docs.oracle.com/javase/specs/jls/se21/html/jls-13.html)

### 4.2 호환성 규칙이 언어 설계를 지배한 사례

**사례 1 — 제네릭의 타입 소거 (Java 5)**
J2SE 5.0 은 제네릭을 도입하며 "compile-time type safety to the Collections Framework" 를 내세웠다([J2SE 5.0 새 기능](https://docs.oracle.com/javase/1.5.0/docs/relnotes/features.html)). 그러나 이미 배포된 수많은 컬렉션 코드(raw `List`)와 섞여 돌아야 했기에, 타입 인자를 런타임에 남기지 않는 소거 방식을 택했다. 그 결과가 `new T[]` 불가, `instanceof List<String>` 제약, 힙 오염 경고다([J2](https://myoungsoo7.github.io/2026/10/12/java-type-system-generics-erasure-pecs/)).

**사례 2 — default 메서드 (Java 8)**
`Collection` 에 `stream()` 을 추가하고 싶은데, 인터페이스에 추상 메서드를 추가하면 세상의 모든 구현체가 컴파일 에러가 난다. 람다 JEP([JEP 126](https://openjdk.org/jeps/126))는 "virtual extension methods will allow interfaces to be evolved in a source and binary compatible fashion" 이라고 이유를 밝힌다. JLS 도 "Adding a `default` method … does not break compatibility with pre-existing binaries" 라고 적되, 다이아몬드 상속 충돌 시 `IncompatibleClassChangeError` 가능성을 단서로 단다([JLS §13.5.7](https://docs.oracle.com/javase/specs/jls/se21/html/jls-13.html)). 자세한 건 [J3](https://myoungsoo7.github.io/2026/10/12/java-class-model-default-record-sealed/).

**사례 3 — `var` 는 키워드가 아니다 (Java 10)**
[JEP 286](https://openjdk.org/jeps/286) 은 "`var` is not a keyword; instead it is a reserved type name" 이라고 명시한다. 변수명·메서드명으로 `var` 를 쓴 기존 코드를 깨지 않기 위해서다.

```java
var var = "ok";        // 컴파일된다 — 변수 이름 var
int var() { return 1; } // 메서드 이름 var 도 가능
// class var {}        // 이건 불가 — 타입 이름으로는 예약됨
```

**사례 4 — `_` 식별자의 단계적 회수**
Java 8 에서 `_` 를 식별자로 쓰면 경고, Java 9 에서 에러가 됐고([JEP 213](https://openjdk.org/jeps/213)), Java 22 에 와서야 "쓰지 않는 변수" 라는 새 의미로 재도입됐다([JEP 456](https://openjdk.org/jeps/456)). 문법 하나를 바꾸는 데 여러 릴리스에 걸쳐 경고 → 에러 → 재정의 순서를 밟는다.

### 4.3 실무 사용사례: 라이브러리 API 를 바꿀 때 지켜야 할 것

JLS 13.5.4 는 "Adding an `abstract`, `private`, or `static` method to an interface does not break compatibility with pre-existing binaries", 반면 "Deleting a member from an interface may cause linkage errors" 라고 한다([JLS §13.5.4](https://docs.oracle.com/javase/specs/jls/se21/html/jls-13.html)). 주의할 점은 **바이너리 호환과 소스 호환은 다르다**는 것이다. 추상 메서드 추가는 이미 컴파일된 구현 클래스는 링크되지만, 그 구현 클래스를 **다시 컴파일**하면 에러가 난다.

사내 공통 모듈을 운영한다면 다음 원칙이 실용적이다.

```java
public interface PaymentGateway {
    PaymentResult pay(PaymentRequest req);

    // 새 기능은 default 로 추가 → 기존 구현체 재컴파일도 깨지지 않는다
    default PaymentResult payIdempotent(PaymentRequest req, String key) {
        return pay(req);
    }
}
```

- 메서드 **삭제**는 deprecate → 한 릴리스 이상 유예 → 삭제.
- 시그니처 변경(파라미터 타입 변경)은 사실상 "삭제 + 추가" 다. 오버로드를 새로 만들고 옛 것을 deprecate 한다.
- `public` 필드 대신 메서드를 노출한다(필드는 진화시킬 방법이 없다).

### 4.4 호환성의 예외: 내부 API 와 보안 관리자

자바는 **공개 API** 의 호환성을 지키지, JDK 내부 구현까지 지키지 않는다. 최근 릴리스들은 그 경계를 실제로 강제하기 시작했다.

| 변화 | JEP | 릴리스 |
|---|---|---|
| JDK 내부 강한 캡슐화가 기본값 | [JEP 396](https://openjdk.org/jeps/396) | 16 |
| `--illegal-access` 제거, 강한 캡슐화 고정 | [JEP 403](https://openjdk.org/jeps/403) | 17 |
| Security Manager 제거 예정(deprecated for removal) | [JEP 411](https://openjdk.org/jeps/411) | 17 |
| Security Manager 영구 비활성화 | [JEP 486](https://openjdk.org/jeps/486) | 24 |

JEP 403 이후 JDK 내부 클래스에 리플렉션으로 접근하면 `InaccessibleObjectException` 등이 난다. 예외로 `sun.misc`, `sun.reflect` 패키지는 `jdk.unsupported` 모듈이 계속 열어둔다고 JEP 403 은 적는다. JEP 486 이후에는 `-Djava.security.manager` 로 Security Manager 를 켜려 하면 기동이 실패하고 `System.setSecurityManager()` 는 `UnsupportedOperationException` 을 던진다.

**실무 함정**: 오래된 라이브러리가 `setAccessible(true)` 로 JDK 내부를 건드리면 JDK 17 업그레이드 시 터진다. 임시방편으로 `--add-opens java.base/java.lang=ALL-UNNAMED` 를 붙일 수 있지만, 이는 "내부 API 의존" 이라는 부채를 기록해 두는 것이지 해결이 아니다. 라이브러리 버전을 올리는 것이 답이다.

---

## 5. 릴리스 모델 — 6개월 주기, LTS, 프리뷰

### 5.1 6개월 주기와 버전 번호

JDK 10 의 [JEP 322](https://openjdk.org/jeps/322) 가 시간 기반 릴리스를 정의했다. 버전 문자열은 `$FEATURE.$INTERIM.$UPDATE.$PATCH` 이고, `$FEATURE` 가 6개월마다 올라간다. JEP 은 "The March 2018 release is JDK 10, the September 2018 release is JDK 11" 이라고 예시를 든다. 즉 **3월·9월** 에 피처 릴리스가 나온다.

### 5.2 LTS 는 OpenJDK 가 아니라 벤더가 정한다

JEP 322 는 LTS 를 언어 차원에서 정의하지 않는다. 구현자가 빌드 정보에 "LTS" 를 넣을 수 있다고만 한다(`11 2018-09-20 LTS` 예시). OpenJDK 의 JDK 25 프로젝트 페이지도 JDK 25 를 "a long-term support (LTS) release from most vendors" 라고 표현한다([JDK 25](https://openjdk.org/projects/jdk/25/)).

오라클의 [Java SE 지원 로드맵](https://www.oracle.com/java/technologies/java-se-support-roadmap.html)은 "Java SE 8, 11, 17, 21, and 25 are LTS releases" 이고 앞으로 2년마다 LTS 를 내며 다음 LTS 는 2027년 9월의 Java 29 라고 밝힌다. JDK 25 GA 는 2025년 9월 16일이다([JDK 25](https://openjdk.org/projects/jdk/25/)).

| 구분 | 버전 |
|---|---|
| LTS (오라클 기준) | 8, 11, 17, 21, 25 |
| 비 LTS 예 | 9, 10, 12–16, 18–20, 22–24 |
| 다음 예정 LTS (오라클) | 29 (2027-09) |

**실무 원칙**: 운영 서비스는 LTS 를 기준선으로 삼고, 비 LTS 는 CI 에서 "다음 LTS 대비 호환성 테스트" 용으로 돌린다. 스프링부트가 요구하는 최소 자바 버전도 LTS 축을 따라 움직인다([J10](https://myoungsoo7.github.io/2026/10/12/spring-boot-java-version-compatibility/)).

### 5.3 프리뷰 기능 — 호환성 약속 밖에 둔 실험

[JEP 12](https://openjdk.org/jeps/12) 는 프리뷰 기능을 "fully specified, fully implemented, and yet impermanent" 라고 정의한다. 완성됐지만 바뀔 수 있다는 뜻이다.

```bash
javac --release 25 --enable-preview Main.java
java --enable-preview Main
```

- javac 는 `--enable-preview` 를 `--release N`(또는 `-source N`)과 **같이** 써야만 받는다.
- 프리뷰 기능을 쓴 클래스 파일은 `minor_version` 이 `65535` 로 찍힌다. JVMS 는 이런 파일을 해당 Java SE 버전에서 프리뷰가 켜진 경우에만 로드하고, **다른 버전에서는 절대 로드하지 않는다**고 규정한다([JVMS §4.1](https://docs.oracle.com/javase/specs/jvms/se21/html/jvms-4.html)).
- JEP 12: "Java SE $N+1 does not claim backwards compatibility with the preview features of Java SE $N."

**함정**: 프리뷰 기능을 운영 코드에 쓰면 JDK 업그레이드가 곧 코드 수정이 된다. 예를 들어 구조적 동시성은 JDK 25 에서도 "Fifth Preview" 상태다([JDK 25 JEP 505](https://openjdk.org/projects/jdk/25/)). 라이브러리는 프리뷰를 쓰면 안 되고, 애플리케이션도 "다음 업그레이드 때 고칠 각오" 가 있을 때만 쓴다.

---

## 6. 정적 타입 OOP — 컴파일러를 첫 번째 리뷰어로

### 6.1 무엇인가

자바는 **명목적(nominal) 정적 타입** 언어다. 타입의 호환은 구조가 아니라 선언된 이름과 상속 관계로 결정되고, 대부분의 타입 오류는 컴파일 시점에 잡힌다.

```java
interface Shape { double area(); }
record Circle(double r) implements Shape {
    public double area() { return Math.PI * r * r; }
}
// 구조가 같아도 Shape 를 implements 하지 않으면 Shape 가 아니다
record Square(double side) { double area() { return side * side; } }

Shape s = new Circle(1);      // OK
// Shape t = new Square(1);   // 컴파일 에러: 명목적 타입
```

### 6.2 "컴파일 타임에 잡는다" 의 범위와 한계

| 컴파일러가 잡는 것 | 런타임까지 미뤄지는 것 |
|---|---|
| 없는 메서드 호출, 타입 불일치 | `null` 역참조 (`NullPointerException`) |
| checked 예외 미처리 | `ClassCastException` (raw 타입·힙 오염) |
| sealed 계층의 switch 누락 케이스 | 배열 공변성 (`ArrayStoreException`) |
| `final` 재할당 | 리플렉션 기반 호출 실패 |

JLS 는 checked 예외를 강제하는 이유와 함께, `RuntimeException` 을 강제하지 않는 이유도 밝힌다. 런타임 예외를 선언하게 하면 "would not aid significantly in establishing the correctness of programs" 라는 것이다([JLS §11.2](https://docs.oracle.com/javase/specs/jls/se21/html/jls-11.html)). 이 부분은 [J5](https://myoungsoo7.github.io/2026/10/12/java-null-optional-exceptions/) 에서 다룬다.

가장 큰 구멍은 **null** 이다. 자바의 참조 타입은 모두 null 을 허용하고, 타입 시스템은 이를 구분하지 않는다. 코틀린이 가장 먼저 고친 것이 바로 이 부분이다([K2](https://myoungsoo7.github.io/2026/10/12/kotlin-null-safety-platform-types/)).

### 6.3 배열 공변성 — 초기 설계의 흔적

```java
Object[] objs = new String[1];   // 컴파일 OK (배열은 공변)
objs[0] = 42;                    // 런타임 ArrayStoreException
```

배열은 공변이라 컴파일러가 못 잡는다. 반면 제네릭은 불변(invariant)으로 설계되어 `List<Object> l = new ArrayList<String>();` 은 컴파일 에러다([JLS §4.10.2](https://docs.oracle.com/javase/specs/jls/se21/html/jls-4.html)). 한 언어 안에 두 가지 철학이 공존하는 이유는 배열이 제네릭보다 10년 먼저 설계됐기 때문이다. 실무 원칙은 단순하다: **공개 API 에는 배열보다 `List` 를 쓴다.**

### 6.4 진화 방향: "OOP 단일 패러다임" 에서 "데이터 지향" 으로

Java 16~21 사이에 들어온 기능들은 상속 중심 OOP 를 보완하는 방향이다.

| 기능 | JEP | 릴리스 | 역할 |
|---|---|---|---|
| `instanceof` 패턴 매칭 | [394](https://openjdk.org/jeps/394) | 16 | 타입 검사 + 캐스트 결합 |
| record | [395](https://openjdk.org/jeps/395) | 16 | 투명한 데이터 운반자 |
| sealed 클래스 | [409](https://openjdk.org/jeps/409) | 17 | 닫힌 계층(합 타입) |
| record 패턴 | [440](https://openjdk.org/jeps/440) | 21 | 구조 분해 |
| switch 패턴 매칭 | [441](https://openjdk.org/jeps/441) | 21 | 망라성 검사 |

```java
sealed interface Payment permits Card, Transfer {}
record Card(String number, long amount) implements Payment {}
record Transfer(String account, long amount) implements Payment {}

long fee(Payment p) {
    return switch (p) {                       // 모든 경우를 다뤘는지 컴파일러가 검사
        case Card c     -> c.amount() * 3 / 100;
        case Transfer t -> 500;
    };
}
```

이 흐름은 "정적 타입으로 최대한 잡는다" 는 원래 철학을 **데이터 모델링** 까지 확장한 것이다. 새 결제 수단을 `permits` 에 추가하면 `default` 없는 switch 는 전부 컴파일 에러가 나서, 빠뜨린 곳을 컴파일러가 알려준다. 상세는 [J3](https://myoungsoo7.github.io/2026/10/12/java-class-model-default-record-sealed/)·[J6](https://myoungsoo7.github.io/2026/10/12/java-pattern-matching-switch-record-patterns/).

---

## 7. 정리 — 자바 문법을 읽는 세 개의 질문

새 자바 기능을 만나면 다음 세 질문으로 읽으면 설계 의도가 거의 다 보인다.

1. **이건 javac 만의 일인가, JVM 도 바뀌었나?** — 소거·박싱·`var` 는 javac, 람다·문자열 연결은 `invokedynamic`.
2. **옛 코드와 옛 바이너리를 깨지 않으려고 무엇을 양보했나?** — 소거, default 메서드, 예약 타입명 `var`.
3. **어떤 오류를 컴파일 타임으로 끌어왔나?** — 제네릭(캐스트 오류), sealed+switch(누락 케이스), record(equals/hashCode 실수).

| 축 | 얻은 것 | 낸 대가 |
|---|---|---|
| JVM·바이트코드 | 이식성, 다언어 생태계(코틀린) | 시작 시간·메모리, 바이트코드 도구 의존 |
| 하위 호환성 | 오래된 코드·라이브러리 재사용 | 소거 같은 타협, 느린 문법 진화 |
| 정적 타입 OOP | 대규모 팀·리팩터링 안정성 | 장황함, null 구멍 |

코틀린은 이 셋 중 **JVM 과 호환성은 그대로 이어받고**, 장황함과 null 구멍을 언어 차원에서 고치려 한 언어다. 그 이야기는 [K1](https://myoungsoo7.github.io/2026/10/12/kotlin-essence-pragmatism-java-interop/) 에서 이어진다.

---

## References

- Oracle, *The Java Language Environment* — https://www.oracle.com/java/technologies/introduction-to-java.html
- JVMS SE 21, §1.2 The Java Virtual Machine — https://docs.oracle.com/javase/specs/jvms/se21/html/jvms-1.html
- JVMS SE 21, Chapter 4 The class File Format (§4.1, §4.7.9) — https://docs.oracle.com/javase/specs/jvms/se21/html/jvms-4.html
- JVMS SE 25, Chapter 4 — https://docs.oracle.com/javase/specs/jvms/se25/html/jvms-4.html
- JVMS SE 7, Chapter 6 (invokedynamic) — https://docs.oracle.com/javase/specs/jvms/se7/html/jvms-6.html
- JLS SE 21, Chapter 4 (§4.10.2) — https://docs.oracle.com/javase/specs/jls/se21/html/jls-4.html
- JLS SE 21, Chapter 11 Exceptions — https://docs.oracle.com/javase/specs/jls/se21/html/jls-11.html
- JLS SE 21, Chapter 13 Binary Compatibility — https://docs.oracle.com/javase/specs/jls/se21/html/jls-13.html
- J2SE 5.0 New Features and Enhancements — https://docs.oracle.com/javase/1.5.0/docs/relnotes/features.html
- `LambdaMetafactory` Javadoc (SE 21) — https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/invoke/LambdaMetafactory.html
- `List` Javadoc (SE 21) — https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/List.html
- JEP 12: Preview Features — https://openjdk.org/jeps/12
- JEP 126: Lambda Expressions & Virtual Extension Methods — https://openjdk.org/jeps/126
- JEP 213: Milling Project Coin — https://openjdk.org/jeps/213
- JEP 238: Multi-Release JAR Files — https://openjdk.org/jeps/238
- JEP 247: Compile for Older Platform Versions — https://openjdk.org/jeps/247
- JEP 280: Indify String Concatenation — https://openjdk.org/jeps/280
- JEP 286: Local-Variable Type Inference — https://openjdk.org/jeps/286
- JEP 322: Time-Based Release Versioning — https://openjdk.org/jeps/322
- JEP 394 / 395 / 409 / 440 / 441 — https://openjdk.org/jeps/394 , https://openjdk.org/jeps/395 , https://openjdk.org/jeps/409 , https://openjdk.org/jeps/440 , https://openjdk.org/jeps/441
- JEP 396 / 403: Strongly Encapsulate JDK Internals — https://openjdk.org/jeps/396 , https://openjdk.org/jeps/403
- JEP 411 / 486: Security Manager — https://openjdk.org/jeps/411 , https://openjdk.org/jeps/486
- JEP 456: Unnamed Variables & Patterns — https://openjdk.org/jeps/456
- OpenJDK, JDK 25 — https://openjdk.org/projects/jdk/25/
- Oracle Java SE Support Roadmap — https://www.oracle.com/java/technologies/java-se-support-roadmap.html

---

## 자바 · 코틀린 시리즈 (20편)

**자바**

- J1. [자바의 본질 — JVM·바이트코드·하위 호환성](/2026/10/12/java-essence-jvm-bytecode-compatibility/) ← 지금 글
- J2. [타입 시스템 — 제네릭, 타입 소거, PECS](/2026/10/12/java-type-system-generics-erasure-pecs/)
- J3. [클래스 모델의 진화 — default 메서드, record, sealed](/2026/10/12/java-class-model-default-record-sealed/)
- J4. [람다·함수형 인터페이스·Stream](/2026/10/12/java-lambda-functional-interface-stream/)
- J5. [null 과 예외 — Optional, checked/unchecked](/2026/10/12/java-null-optional-exceptions/)
- J6. [패턴 매칭 — instanceof, switch 식, record 패턴](/2026/10/12/java-pattern-matching-switch-record-patterns/)
- J7. [동시성 — Thread 에서 가상 스레드까지](/2026/10/12/java-concurrency-thread-to-virtual-threads/)
- J8. [현대 자바 문법 총정리 — LTS 버전별](/2026/10/12/java-modern-syntax-by-version/)
- J9. [스프링이 자바를 쓰는 방식 — 리플렉션·프록시·DI](/2026/10/12/java-how-spring-uses-java-reflection-proxy-di/)
- J10. [스프링부트 × 자바 버전 호환](/2026/10/12/spring-boot-java-version-compatibility/)

**코틀린**

- K1. [코틀린의 본질 — 실용주의와 자바 상호운용](/2026/10/12/kotlin-essence-pragmatism-java-interop/)
- K2. [널 안전 — ?, ?:, !!, 플랫폼 타입](/2026/10/12/kotlin-null-safety-platform-types/)
- K3. [클래스 — data/sealed/object/value class](/2026/10/12/kotlin-classes-data-sealed-object-value/)
- K4. [함수 — 확장 함수, 고차 함수, inline/reified](/2026/10/12/kotlin-functions-extension-inline-reified/)
- K5. [스코프 함수 let/run/with/apply/also](/2026/10/12/kotlin-scope-functions-use-cases/)
- K6. [컬렉션과 시퀀스](/2026/10/12/kotlin-collections-and-sequences/)
- K7. [코루틴과 Flow](/2026/10/12/kotlin-coroutines-and-flow/)
- K8. [제네릭 변성 in/out](/2026/10/12/kotlin-generics-variance-in-out/)
- K9. [코틀린 × 스프링 — 플러그인, Jackson, JPA](/2026/10/12/kotlin-with-spring-plugins-jackson-jpa/)
- K10. [코틀린 × 스프링부트 — 코루틴, DSL, 버전 호환](/2026/10/12/kotlin-spring-boot-coroutines-dsl-compatibility/)
