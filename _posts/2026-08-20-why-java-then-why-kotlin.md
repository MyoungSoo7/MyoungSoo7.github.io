---
layout: post
title: "Java 는 C++ 의 무엇을 지웠고, Kotlin 은 Java 의 무엇을 지웠나"
date: 2026-08-20 14:15:00 +0900
categories: [engineering, language]
tags: [java, kotlin, jvm, history, null-safety, gc]
---

두 언어를 한 줄에 놓고 "Java 다음에 Kotlin" 이라고 말하는 순간, 놓치는 게 있다. **Java 와 Kotlin 은 서로 다른 문제를 풀러 왔다.** Java 는 C++ 을 대체하려 왔고, Kotlin 은 Java 를 대체하려 오지 않았다 — Java 위에 얹혀 살려 왔다.

먼저 사실부터 나열한다. Sun Microsystems 의 Java 1.0 은 **1996년 1월 23일**에 공개됐다.[^wiki-java] JetBrains 가 Project Kotlin 을 발표한 건 **2011년 7월**, 1.0 은 **2016년 2월 15일**이다.[^wiki-kotlin] 이 15년의 간격에 두 언어가 각자 무엇을 지웠는지가 들어 있다.

---

## 1. Java 이전 — C/C++ 이 가진 여섯 개의 통증

Gosling 이 Java 를 설계할 때 내건 목표는 다섯이었다 — "simple, object-oriented, and familiar", "robust and secure", "architecture-neutral and portable", "high performance", "interpreted, threaded, and dynamic".[^wiki-java] 목표는 언제나 문제의 반대편에 있다. 목표를 뒤집으면 그 시절의 통증이 나온다.

| 통증 (C/C++, 1990년대 초) | 실제로 무엇이었나 |
|---|---|
| **메모리 누수와 이중 해제** | `malloc/free`, `new/delete` 를 개발자가 손으로 짝 맞춤. 큰 코드베이스에서 누락은 상수. |
| **널/야생 포인터, 세그폴트** | 해제된 메모리를 가리키는 포인터, 배열 범위 밖 접근 → 프로세스 크래시. 런타임에서만 잡힘. |
| **이식성** | 같은 소스가 x86 / SPARC / PowerPC 에서 다르게 빌드됨. 워드 크기, 엔디안, `long` 의 비트수까지 플랫폼 종속. |
| **헤더/링커 지옥** | `.h` 중복 포함, 매크로 충돌, 링크 순서에 따른 심볼 미해결. |
| **다중 상속의 다이아몬드** | C++ 의 virtual inheritance 로 방어했지만 코드 규약과 리뷰 비용이 컸음. |
| **네트워크 안전** | 웹 초창기에 신뢰할 수 없는 코드를 다운로드해 실행하려면, 언어 수준에서 포인터 산술과 임의 메모리 접근을 봉해야 했음. |

여기서 Java 가 실제로 지운 것과 대체한 것을 하나씩 짚는다.

### 1-1. 가비지 컬렉터 — `malloc/free` 를 언어에서 삭제

C 의 `free(p)` 와 그 다음 `p` 를 다시 쓰는 실수(use-after-free)는 언어 문법에 존재하는 한 없앨 수 없다. Java 는 **문법에서 뺐다.** `delete` 키워드가 없다. `finalize()` 는 있지만 GC 가 해제 시점을 정한다. 대가는 두 가지 — (1) GC 일시 정지, (2) 메모리 사용량의 상한을 개발자가 직접 관리하지 못함. 이 대가는 30년째 튜닝 대상이지만, "누가 해제해야 하나" 라는 질문 자체는 사라졌다.

### 1-2. 바이트코드와 JVM — "Write Once, Run Anywhere"

같은 `.java` 를 컴파일한 `.class` 는 x86 이든 ARM 이든 SPARC 이든 같은 파일이다. 플랫폼별 JVM 이 그 바이트코드를 자기 CPU 명령으로 번역한다. C 에서 `#ifdef _WIN32` 를 뿌리며 관리하던 이식성 코드가 **JVM 벤더의 문제로 옮겨졌다.** 이건 문제를 없앤 게 아니라 **책임을 이동시킨** 사례다. 잘 지운 사례로 착각하기 쉬우니 구분해 둔다.

### 1-3. 포인터 산술 봉인 — 언어 수준의 안전

`&p + 3` 이 안 된다. 배열은 항상 자기 길이를 알고, 범위를 넘으면 `ArrayIndexOutOfBoundsException` 이 던져진다. 신뢰할 수 없는 코드(당시엔 applet, 지금은 서버에 올라가는 서드파티 JAR) 를 실행할 때 언어가 최소한의 격리를 보장한다.

### 1-4. 다중 상속 제거, 인터페이스 도입

C++ 의 다중 상속을 지우고 **단일 상속 + 다중 인터페이스** 로 재편했다. 다이아몬드 문제 자체가 소멸했다. 대신 "믹스인" 이 필요할 때 코드 재사용이 어색해지는 대가가 생겼다 — 이 자리를 Java 8 의 default method 와 Kotlin 이 뒤에 채운다.

---

## 2. Java 가 남긴 것들 — 20년 뒤에도 살아있던 문제

Java 는 위 여섯 개 통증 중 다섯을 지웠다. 하지만 20년이 지난 2010년대에도 남아 있던 문제가 있었다. 이게 Kotlin 이 등장한 자리다.

### 2-1. NullPointerException

Java 의 참조 타입은 전부 nullable 이다. `String s` 는 문자열일 수도, `null` 일 수도 있다. 컴파일러는 그 둘을 구분하지 않는다. Tony Hoare 는 자신이 1965년에 도입한 null 참조를 **"the billion-dollar mistake"** 라고 부른다.[^hoare-npe]

Java 8 은 `Optional<T>` 을 표준 라이브러리에 넣었지만 (1) 필드에는 못 쓰고 (2) 기존 API 의 반환값에만 붙일 수 있고 (3) `null` 자체를 없애지는 못한다. 즉 **관습으로 회피할 수 있게 됐을 뿐 언어에서 지운 건 아니다.**

### 2-2. 값 객체(POJO)의 보일러플레이트

DTO 하나에 필드가 5개면 — `equals`, `hashCode`, `toString`, getter 5개, setter 5개, 생성자 1~2개 — 코드가 100줄이 넘는다. Lombok 은 이걸 어노테이션으로 접었지만, **런타임 어노테이션 프로세서에 의존한다.** 언어가 아니라 도구가 짊어졌다.

### 2-3. 가변성이 기본값

`final` 을 붙이지 않으면 재할당 가능, `List` 를 명시하지 않으면 mutable 컬렉션. 스레드 안전성을 얻으려면 `final` 을 사방에 도배해야 한다.

### 2-4. Checked exception 의 확산

체크 예외가 IO/네트워크 코드마다 `throws` 절을 오염시킨다. 스트림/람다와도 잘 안 어울린다. Java 8 이후 표준 라이브러리조차 새 API 는 대개 unchecked 로 간다.

---

## 3. Kotlin 이 등장한 배경 — "왜 Scala 로 안 갔나"

JetBrains 는 IntelliJ IDEA · ReSharper 등의 IDE 제품을 **자체적으로 대량의 Java 코드로** 유지하는 회사다. 사내 자바 코드베이스가 커지면서 대안을 찾았고, 검토 결과 **Scala 만이 원하는 기능을 갖췄지만 컴파일 속도가 문제였다** 고 밝혔다.[^wiki-kotlin] 실제 Kotlin 의 명시된 목표 중 하나는 **"Java 만큼 빠르게 컴파일한다"** 이다.[^wiki-kotlin]

이 배경을 정확히 이해하지 않으면 Kotlin 을 오해한다 — Kotlin 은 "더 나은 언어 이론" 을 지향한 학술적 프로젝트가 아니라, **자기 회사의 자바 코드에 바로 얹혀야 하는 실용적 프로젝트** 였다. 그래서 다음 두 가지가 처음부터 요구사항이었다.

- **Java 와의 100% 상호운용성** — 기존 Java 코드에서 Kotlin 을 호출할 수 있고, 그 반대도 가능해야 한다. `.kt` 와 `.java` 가 같은 프로젝트에 섞여 있을 수 있어야 한다.
- **JVM 을 그대로 쓴다** — 새 런타임이 아니라 기존 JVM 바이트코드로 컴파일된다. Spring, Hibernate, Netty 등 모든 Java 라이브러리를 그대로 쓴다.

Google 이 2019년 5월 7일 Kotlin 을 Android 의 **"preferred language"** 로 지정한 것[^wiki-kotlin] 은 이 상호운용성 덕이다. 안드로이드는 하루아침에 Java 를 버리지 못한다 — 표준 라이브러리, SDK 시그니처, 기존 앱 수백만 개가 Java 다. Kotlin 은 그 위에 얹혀서 동작한다.

---

## 4. Kotlin 이 실제로 지운 것들

### 4-1. Nullable 을 타입 시스템에 넣었다

```kotlin
val s: String  = "hello"   // null 불가 - 컴파일러가 강제
val n: String? = null      // nullable - 물음표가 명시
val len = s.length         // OK
val len = n.length         // 컴파일 에러
val len = n?.length ?: 0   // 안전 호출 + 엘비스 연산자
```

핵심은 `String` 과 `String?` 이 **서로 다른 타입** 이라는 점이다. Java 는 이 둘을 문법으로 구분할 수 없다. Kotlin 은 구분한다 — 그래서 NPE 를 "런타임 사고" 가 아니라 "컴파일 에러" 로 옮겼다. 완벽하지는 않다(플랫폼 타입, `!!` 강제 언박싱, 자바 상호호출 지점에서는 여전히 새어 나온다). 그러나 **문법에 존재한다** 는 사실 자체가 다르다.

### 4-2. `data class` — 값 객체를 4줄로

```kotlin
data class User(val id: Long, val name: String, val email: String)
```

이 한 줄이 `equals`, `hashCode`, `toString`, `copy`, componentN 을 전부 생성한다. Java 16 의 `record` 가 뒤늦게 비슷한 자리를 채웠지만, Kotlin 은 2016년부터 이걸 갖고 있었다.

### 4-3. `val` — 불변이 기본

`val` 은 재할당 불가, `var` 는 재할당 가능. 이름이 한 글자 다르니 코드 리뷰에서 `var` 이 나오면 눈에 띈다. **불변을 얻기 위해 `final` 을 여기저기 붙일 필요가 없다.**

### 4-4. Coroutines — 콜백 지옥과 스레드 풀 사이

`suspend` 함수와 `launch { }` 로 비동기 코드가 동기 코드처럼 읽힌다. Java 는 21에서야 Virtual Thread 로 비슷한 자리에 도달했다. Kotlin 은 2018년 1.3 부터 안정판.

### 4-5. Extension function — 남의 클래스에 메서드를 추가

```kotlin
fun String.isValidEmail(): Boolean = this.contains("@")
```

Java 의 `StringUtils.isValidEmail(str)` 유틸리티 클래스 패턴을 지운다.

---

## 5. Before / After — 실제 코드 비교 셋

### 5-1. 값 객체

**Java (Java 15 이전, Lombok 없음)**
```java
public final class User {
    private final long id;
    private final String name;
    private final String email;

    public User(long id, String name, String email) {
        this.id = id;
        this.name = name;
        this.email = email;
    }

    public long getId() { return id; }
    public String getName() { return name; }
    public String getEmail() { return email; }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (!(o instanceof User)) return false;
        User u = (User) o;
        return id == u.id
            && Objects.equals(name, u.name)
            && Objects.equals(email, u.email);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, name, email);
    }

    @Override
    public String toString() {
        return "User{id=" + id + ", name=" + name + ", email=" + email + "}";
    }
}
```

**Kotlin**
```kotlin
data class User(val id: Long, val name: String, val email: String)
```

38줄이 1줄이 됐다. `copy(name = "새이름")` 까지 공짜로 붙는다.

### 5-2. null 처리

**Java**
```java
public String findUpperName(Long id) {
    User u = repo.findById(id);
    if (u == null) return null;
    String name = u.getName();
    if (name == null) return null;
    return name.toUpperCase();
}
```

**Kotlin**
```kotlin
fun findUpperName(id: Long): String? =
    repo.findById(id)?.name?.uppercase()
```

`?.` 체인 한 줄이 6줄의 방어 코드를 대체한다. **더 중요한 건**: Kotlin 판에서 `?` 를 하나라도 빼먹으면 컴파일이 안 된다. Java 판은 방어 코드를 빼먹어도 그냥 컴파일된다 — 그리고 프로덕션에서 NPE 로 로그가 쌓인다.

### 5-3. 리스트 변환

**Java 8+**
```java
List<String> names = users.stream()
    .filter(u -> u.getAge() >= 18)
    .map(User::getName)
    .collect(Collectors.toList());
```

**Kotlin**
```kotlin
val names = users
    .filter { it.age >= 18 }
    .map { it.name }
```

`Collectors.toList()` 가 사라지고, `.stream()` 이 필요 없다. 컬렉션이 처음부터 지연 연산 · 즉시 연산을 선택할 수 있게 설계됐다.

---

## 6. 정리 — 두 언어의 관계

**Java 는 C++ 을 지웠다.** 언어를 바꿔서 지웠다. C 개발자에게 Java 는 새 언어였고, 기존 코드는 재작성해야 했다.[^java-cpp-migration] 통증은 컸지만 얻은 것도 컸다 — 세그폴트가 사라지고, 같은 JAR 이 리눅스와 윈도우에서 돌았다.

**Kotlin 은 Java 를 지우지 않았다.** Java 를 지우려 하지도 않았다. Kotlin 코드와 Java 코드가 같은 프로젝트에 섞여 있고, 같은 JVM 에서 같은 바이트코드로 돌고, 같은 라이브러리를 쓴다. Kotlin 은 Java 의 **문법적 통증** (NPE, 보일러플레이트, 가변 기본값)만 뽑아냈다. 런타임과 생태계는 그대로 뒀다.

이 차이가 실제로 뭘 뜻하냐면 — Java → Kotlin 마이그레이션은 파일 단위로 가능하다. `User.java` 를 `User.kt` 로 바꿔도 나머지는 손대지 않아도 된다. C++ → Java 마이그레이션은 그렇게 안 됐다. **한 언어는 대체제로 왔고, 다른 한 언어는 부가재로 왔다.**

그리고 지금 우리가 답할 수 없는 질문이 하나 있다 — Kotlin 이 지운 문제를 언젠가 Java 스스로 지웠을 때(record, pattern matching, virtual thread 는 이미 그 조짐), Kotlin 이 남는 이유가 무엇일지. 이건 이 글의 범위가 아니지만, 두 언어의 관계를 이해하려면 답이 필요해질 것이다.

---

[^wiki-java]: Wikipedia, _Java (programming language)_ — <https://en.wikipedia.org/wiki/Java_(programming_language)>. Sun Microsystems 의 Java 1.0 은 1996년 1월 23일 공개; Gosling 의 다섯 목표(simple/object-oriented/familiar, robust/secure, architecture-neutral/portable, high performance, interpreted/threaded/dynamic).

[^wiki-kotlin]: Wikipedia, _Kotlin (programming language)_ — <https://en.wikipedia.org/wiki/Kotlin_(programming_language)>. Project Kotlin 은 2011년 7월 JetBrains 발표; Kotlin 1.0 은 2016년 2월 15일; Scala 만이 원하는 기능을 갖췄으나 컴파일 속도가 문제였다는 배경; "Java 만큼 빠르게 컴파일한다" 는 명시 목표; 2019년 5월 7일 Google 의 Android preferred language 선언.

[^hoare-npe]: Tony Hoare, _Null References: The Billion Dollar Mistake_, QCon London 2009 발표. "I call it my billion-dollar mistake. It was the invention of the null reference in 1965." — <https://www.infoq.com/presentations/Null-References-The-Billion-Dollar-Mistake-Tony-Hoare/>

[^java-cpp-migration]: C++ → Java 마이그레이션에는 GC 도입, 헤더/링커 모델 소멸, 다중 상속 제거 때문에 소스 코드의 상당 부분 재작성이 필요했다. 컴파일러 옵션 몇 개로 되는 일이 아니었다.
