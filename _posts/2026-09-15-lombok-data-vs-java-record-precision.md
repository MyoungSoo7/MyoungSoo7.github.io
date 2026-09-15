---
layout: post
title: "Lombok @Data 와 record 정밀분석 — 둘은 같은 문제를 푸는 두 해법이 아니다"
date: 2026-09-15 22:48:43 +0900
categories: [Engineering, Java]
tags: [Java, Lombok, record, JEP395, JPA, Jackson, 불변성]
---

"record 가 나왔으니 Lombok 은 끝났다" 는 말을 자주 듣는다. 이 문장의 문제는 결론이 아니라 **전제**다. 두 기능이 같은 문제를 푼다고 가정하는데, record 를 설계한 문서가 그 가정을 직접 부정한다. JEP 395 의 Non-Goals 절이다.[^jep395]

> While records do offer improved concision when declaring data carrier classes, it is not a goal to declare a "war on boilerplate". **In particular, it is not a goal to address the problems of mutable classes which use the JavaBeans naming conventions.**
>
> It is not a goal to add features such as properties or **annotation-driven code generation**, which are often proposed to streamline the declaration of classes for "Plain Old Java Objects".

record 의 목표에서 "JavaBeans 규약을 쓰는 가변 클래스의 문제" 와 "애너테이션 기반 코드 생성" 이 **명시적으로 제외**돼 있다. 그런데 그 둘이 정확히 `@Data` 가 하는 일이다. 즉 record 는 `@Data` 의 상위호환이 아니라, 애초에 다른 것을 만들려고 한 물건이다.

이 글은 "어느 쪽이 좋은가" 를 묻지 않는다. **각각이 정확히 무엇을 생성하고, 어디서 구조적으로 불가능해지고, 어디서 조용히 틀리는가** 를 1차 문서만으로 대조한다. [이전 글]({% post_url 2026-09-13-java17-sealed-record-real-use-vs-kotlin %})에서 sealed + record 를 ADT 관점으로 봤다면, 이번엔 record 를 Lombok 과 정면으로 놓는다.

> **버전과 범위.** record 는 JDK 14·15 프리뷰를 거쳐 **JDK 16 에서 정식화**됐다(JEP 395, Release 16).[^jep395] 자바 17 은 record 를 담은 첫 LTS 일 뿐 record 가 도입된 버전은 아니다 — 이 글에서 "자바 17 의 record" 라는 표현은 쓰지 않는다. Lombok 쪽 사실은 전부 projectlombok.org 공식 기능 문서 기준이다.

---

## 1. 무엇이 생성되는가 — 정확히

먼저 추측을 걷어내고 각 문서가 말하는 생성물을 그대로 적는다.

**`@Data`** 는 다섯 애너테이션의 묶음이다.[^lombokdata]

> `@Data` is a convenient shortcut annotation that bundles the features of `@ToString`, `@EqualsAndHashCode`, `@Getter` / `@Setter` and `@RequiredArgsConstructor` together

구체적으로는 모든 필드의 getter, **non-final 필드의 setter**, `toString`, `equals`, `hashCode`, 그리고 final 필드와 `@NonNull` 필드를 채우는 생성자다. `transient` 필드는 `equals`/`hashCode` 에서 빠지고, `static` 필드는 아예 전부에서 빠진다.

**record** 는 헤더에 적힌 컴포넌트마다 **두 개의 멤버**를 얻는다.[^jep395]

> For each component in the header, two members: a `public` accessor method with the same name and return type as the component, and a `private` `final` field with the same type as the component

여기에 canonical constructor, 컴포넌트 전부를 쓰는 `equals`/`hashCode`, 컴포넌트 이름까지 찍는 `toString` 이 붙는다.

정리하면 이렇다.

| | `@Data` | `record` |
|---|---|---|
| 접근자 이름 | `getName()` (JavaBeans) | `name()` (컴포넌트 이름 그대로) |
| setter | non-final 필드에 생성 | **없음** (필드가 final) |
| 클래스 final 여부 | 아님 | **암묵적 final**, `abstract` 불가 |
| 상위 클래스 | 자유 | **항상 `java.lang.Record`**, `extends` 절 자체가 없음 |
| 인터페이스 구현 | 가능 | 가능 |
| 추가 인스턴스 필드 | 가능 | **불가** (인스턴스 초기화 블록도 불가) |
| `native` 메서드 | 가능 | **불가** |
| 생성 주체 | 애너테이션 프로세서 | **javac (언어 기능)** |

record 쪽 제약은 전부 JEP 395 "Rules for record classes" 에 열거된 것이다.[^jep395] 이 제약들이 왜 있는지가 다음 절의 주제다.

---

## 2. 진짜 차이는 보일러플레이트가 아니라 "표현과 API 의 결합"

JEP 395 는 record 가 무엇을 **포기**하는지 한 문장으로 못박는다.

> This means that record classes **give up a freedom that classes usually enjoy — the ability to decouple a class's API from its internal representation** — but, in return, record class declarations become significantly more concise.

이게 이 글에서 가장 중요한 한 문장이다. 보통의 클래스는 필드 이름을 바꿔도 getter 이름을 유지해 API 를 지킬 수 있다. `@Data` 도 그 자유 위에 있다 — 필드에 `@Getter(AccessLevel.NONE)` 을 걸어 특정 필드를 API 에서 숨기거나, 손으로 쓴 getter 로 표현과 노출을 분리할 수 있다.

record 는 그 자유가 **없다**. 헤더가 곧 상태이고 상태가 곧 API 다. 컴포넌트 이름 하나를 바꾸면 접근자 이름이 바뀌고, 그건 호출자를 깨는 변경이다. 컴포넌트를 추가하면 canonical constructor 시그니처가 바뀐다.

이건 단점이 아니라 **계약**이다. JEP 의 표현대로 record 는 "transparent carrier" 임을 의미론적으로 주장하는 타입이고, 투명성은 숨길 수 없다는 뜻이다. 그래서 판단 기준은 이렇게 갈린다.

- 이 타입의 내부 표현이 앞으로 바뀔 수 있고 API 는 지켜야 한다 → record 가 **구조적으로 부적합**
- 이 타입은 그냥 이 값들이다, 영원히 → record 가 정확히 그 선언

`@Data` 는 이 질문에 답을 강요하지 않는다. 그게 편한 점이자, 아무도 그 질문을 안 하게 되는 지점이다.

---

## 3. equals 계약 — 여기가 가장 정밀하게 갈린다

### record 에는 명세된 불변식이 있다

`java.lang.Record` 자바독은 모든 record 가 지켜야 할 불변식을 못박는다.[^recordjavadoc]

> For all record classes, the following invariant must hold: if a record R's components are `c1, c2, ... cn`, then if a record instance is copied as follows: `R copy = new R(r.c1(), r.c2(), ..., r.cn());` then it must be the case that `r.equals(copy)`.

$$\forall r \neq \mathrm{null}:\quad r.\mathrm{equals}\bigl(\,\mathrm{new}\ R(r.c_1(),\ \ldots,\ r.c_n())\,\bigr) \;=\; \mathrm{true}$$

**분해했다가 그대로 다시 조립하면 같은 값이어야 한다.** 이것이 "transparent carrier" 라는 말의 형식적 정의다. `@Data` 에는 이에 대응하는 명세된 계약이 없다. 있는 것은 "필드로부터 equals 를 만들어 준다" 는 구현 설명뿐이다.

다만 정확히 하자. JEP 395 는 컴파일러가 이걸 **검사하지 못한다**고 스스로 밝힌다.

> However, it is not generally possible for a compiler to check that explicitly declared methods respect this invariant.

그래서 JEP 는 접근자를 손으로 덮어써서 값을 슬쩍 보정하는 코드를 "bad style" 예시로 직접 든다(`x` 가 100 을 넘으면 100 을 돌려주는 `SmallPoint`). 즉 record 의 보장은 **아무것도 안 덮어썼을 때만** 명세 수준의 보장이고, 손대는 순간 사람의 규율 문제로 돌아온다.

### `@Data` 는 `callSuper` 를 설정할 수 없다

Lombok 문서의 이 문장이 실무에서 가장 자주 발에 걸린다.[^lombokdata]

> However, **the parameters of these annotations (such as `callSuper`, `includeFieldNames` and `exclude`) cannot be set with `@Data`.**

그리고 `@EqualsAndHashCode` 문서는 상속이 끼면 무슨 일이 생기는지 설명한다.[^lombokeq]

> Normally, auto-generating an `equals` and `hashCode` method for such classes is a bad idea, as the superclass also defines fields, which also need equals/hashCode code but this code will not be generated. ... **Not setting `callSuper` to true when you extend another class generates a warning**

두 문장을 합치면 결론이 나온다. **상속 계층에 `@Data` 를 붙이면 상위 클래스 필드가 동등성에서 빠진 채로, 경고 하나만 남기고 컴파일된다.** 고치려면 `@Data` 를 풀고 `@EqualsAndHashCode(callSuper = true)` 를 따로 붙여야 한다(문서 말대로 Lombok 은 명시 애너테이션에 양보한다).

record 에서는 이 버그가 **발생할 수 없다**. `extends` 절 자체가 없기 때문이다. 문제를 잘 푸는 게 아니라 문제가 성립하지 않는다 — 이게 언어 기능과 코드 생성기의 차이다.

### 둘 다 걸리는 함정: 컴포넌트 타입의 equals

Lombok 문서는 이걸 명시적으로 경고한다.[^lombokeq]

> Note that lombok just defers to the `.equals()` implementation for all objects except primitives and arrays. Some well known types have possibly surprising equals implementations. For example, `java.math.BigDecimal` considers scale, i.e. **`1E2` is not equal to `100`** according to `BigDecimal`'s own `equals` implementation.

record 도 컴포넌트의 `equals` 에 위임하므로 `BigDecimal` 문제는 **똑같이** 생긴다. 차이는 탈출구다.

- Lombok: `@EqualsAndHashCode.Include(replaces = "fieldName")` 로 매핑된 값을 쓰게 한다 — 문서에 정확한 레시피가 있다.[^lombokeq]
- record: 명시 `equals` 를 직접 쓴다 → 그 순간 §3 첫머리의 **명세 보장을 스스로 포기**한다.

정산 금액을 `BigDecimal` 로 다루는 코드에서 이건 가설이 아니라 실제로 터지는 자리다. record 를 쓴다면 canonical constructor 에서 `stripTrailingZeros()` 로 **정규화**하는 쪽이 낫다 — 그러면 `equals` 를 안 건드리고도 스케일이 통일된다. JEP 가 compact constructor 의 용도로 든 예가 정확히 이 "normalize" 다.[^jep395]

---

## 4. `@Data` 의 가장 위험한 한 문장 — 조용한 미생성

Lombok 문서에 이 문장이 있다.[^lombokdata]

> If the class already contains a method with the same name and parameter count as any method that would normally be generated, that method is not generated, and **no warning or error is emitted**. For example, if you already have a method with signature `equals(AnyType param)`, **no `equals` method will be generated, even though technically it might be an entirely different method due to having different parameter types.**

이 문장이 말하는 실패는 이렇게 생긴다.

```java
@Data
public class Money {
    private final BigDecimal amount;
    private final String currency;

    // 오버라이드한 줄 알았지만 파라미터가 Object 가 아니다
    public boolean equals(Money other) { ... }
}
```

`equals(Object)` 는 **생성되지 않는다.** 경고도 에러도 없다. `Object.equals` 가 그대로 상속되니 동일성 비교는 참조 비교가 되고, `HashMap` 과 `Set` 과 `List.contains` 가 전부 조용히 틀린 답을 낸다. 컴파일은 통과하고 테스트도 `assertEquals(a, b)` 를 정적 타입 `Money` 로 호출하면 통과할 수 있다.

record 의 같은 자리 규칙은 정반대다.[^jep395]

> **Any explicit declarations of a member that would otherwise be automatically derived must match the type of the automatically derived member exactly**, disregarding any annotations on the explicit declaration.

파생 멤버를 명시 선언하려면 타입이 정확히 맞아야 하고, 안 맞으면 **컴파일 에러**다. 같은 실수가 한쪽에서는 런타임 미스터리가 되고 다른 쪽에서는 빌드 실패가 된다.

이 대비가 이 글 전체에서 가장 날카로운 지점이다. 코드 생성기는 "생성하지 않음" 이라는 결과를 가질 수 있고, 언어 규칙은 그럴 수 없다.

---

## 5. 불변성 — 공정한 비교 대상은 `@Value` 다

`@Data` 는 non-final 필드에 setter 를 만든다. 즉 **가변 빈**이다. record 는 컴포넌트 필드가 final 이다. 여기까지만 보고 "record 가 불변이라 낫다" 고 말하면 두 군데가 부정확하다.

**첫째, record 의 불변성은 얕다.** 자바독의 표현이 정확히 그렇다.[^recordjavadoc]

> A record class is a **shallowly immutable**, transparent carrier for a fixed set of values

```java
record Order(String id, List<String> items) {}

var list = new ArrayList<>(List.of("a"));
var o = new Order("o-1", list);
list.add("b");          // o 의 내용이 바뀐다
```

자바독은 명시 canonical constructor 를 쓰는 이유 중 하나로 **"perform defensive copies on mutable components"** 를 직접 든다.[^recordjavadoc] 즉 방어적 복사는 record 가 해 주는 게 아니라 **사람이 써야 하는 것**이다.

```java
record Order(String id, List<String> items) {
    Order {
        items = List.copyOf(items);   // compact constructor 에서 정규화
    }
}
```

**둘째, `@Data` 는 Lombok 의 불변 버전이 아니다.** 불변 쪽 대응물은 `@Value` 이고, 문서는 이렇게 정의한다.[^lombokvalue]

> `@Value` is the immutable variant of `@Data`; all fields are made `private` and `final` by default, and setters are not generated. **The class itself is also made `final` by default, because immutability is not something that can be forced onto a subclass.**

`@Value` 는 실질적으로 `final @ToString @EqualsAndHashCode @AllArgsConstructor @FieldDefaults(makeFinal=true, level=PRIVATE) @Getter` 의 축약이다. 그러니 "불변 데이터 캐리어" 라는 같은 자리를 놓고 겨루는 건 **record 대 `@Value`** 이고, `@Data` 는 처음부터 다른 자리에 있다. `@Data` 와 record 를 맞붙이는 흔한 비교가 자꾸 이상해지는 이유가 여기 있다.

그래도 `@Value` 와 record 사이엔 차이가 남는다. `@Value` 는 접근자가 `getX()` 라 JavaBeans 규약을 지키고, 클래스가 final 이지만 상위 클래스를 가질 수는 있으며, 추가 인스턴스 필드를 둘 수 있다. record 는 셋 다 안 된다.

---

## 6. JPA — 여기서는 둘 다 답이 아니다

### record 는 엔티티가 될 수 없다 (설정 문제가 아니다)

Hibernate 사용자 가이드가 JPA 명세 §2.1 의 요구사항을 옮겨 놓은 대목이다.[^hibernate]

> The entity class must have a public or protected **no-argument constructor**. ...
> The entity class **must not be final**. No methods or persistent instance variables of the entity class may be final.

record 는 암묵적 final 이고, 컴포넌트가 하나라도 있으면 no-arg 생성자가 없다. 두 요구를 **동시에** 어긴다. Hibernate 는 자기 요구는 더 느슨하다고 밝히면서도 final 에 대해선 이렇게 덧붙인다.

> Technically Hibernate can persist final classes ... However, it is generally not a good idea as doing so will stop Hibernate from being able to **generate proxies for lazy-loading** the entity.

즉 어노테이션을 더 붙이거나 설정을 바꿔서 우회할 성질이 아니다. **record 는 엔티티 자리에 오지 않는다.**

### `@Data` 를 엔티티에 붙이는 것도 답이 아니다

여기서는 공정하게 갈라 적는다.

**Lombok 이 이미 고려한 것** — 프록시 문제는 문서에 답이 있다.[^lombokeq]

> Unless your class is `final` and extends `java.lang.Object`, lombok generates a `canEqual` method which means **JPA proxies can still be equal to their base class**, but subclasses that add new state don't break the equals contract.

또 `equals`/`hashCode` 는 기본적으로 필드가 아니라 **getter 를 통해** 접근하며(`lombok.equalsAndHashCode.doNotUseGetters` 로 바꿀 수 있다), 이건 프록시에서 오히려 필요한 동작이다.[^lombokeq]

**그래도 남는 것** — `@Data` 는 non-final 필드에 setter 를 전부 열고, `toString` 에 모든 필드를 넣고, 앞서 본 대로 `callSuper` 를 설정할 수 없다. 생성 전략으로 채워지는 `id` 를 동등성에 포함하면 영속화 전후로 `hashCode` 가 달라진다 — Hibernate 가 이 주제에 **절 하나를 통째로 할애**하고 있다는 사실 자체가 난이도의 방증이다("Implementing `equals()` and `hashCode()`", §3.4.7).[^hibernate] 이 절의 결론을 여기서 요약하지는 않겠다. 맥락(관리 상태·세션·detach) 의존이 커서, 한 줄로 옮기면 틀린 말이 되기 쉽다.

**실무 결론.** 엔티티에는 둘 다 붙이지 않고 필요한 것만 손으로 쓴다. record 는 그 옆, **DTO·조회 프로젝션·이벤트 페이로드** 자리에서 제값을 한다. 엔티티와 record 는 경쟁 관계가 아니라 계층이 다르다.

---

## 7. 프레임워크 상호운용 — 사실만

**직렬화.** record 는 커스터마이즈가 막혀 있다.[^jep395]

> Instances of record classes can be serialized and deserialized. However, the process **cannot be customized** by providing `writeObject`, `readObject`, `readObjectNoData`, `writeExternal`, or `readExternal` methods. The components of a record class govern serialization, while **the canonical constructor of a record class governs deserialization**.

이건 양날이다. 좋은 쪽 — 역직렬화가 canonical constructor 를 타므로 compact constructor 의 검증이 **역직렬화에도 그대로 걸린다**. 자바 직렬화의 고전적 구멍(생성자를 우회해 불변식이 깨진 객체가 생기는 것)이 record 에서는 닫힌다. 나쁜 쪽 — `readObject` 로 옛 포맷을 흡수하는 식의 호환 트릭을 쓸 수 없다.

**Jackson.** record 지원은 2.12 에 들어갔다(`#2709: Support for JDK 14 record types`).[^jackson] 여기에 조용한 동작 변경이 하나 있다.

> if you have a `Record` type with 1 property ... it would be assumed to use "Delegating" style of parameter passing, and would (only) accept JSON String to bind. **With 2.12 all `Records` default to "Properties" style binding so a single-property JSON Object is expected instead.**

**컴포넌트가 하나뿐인 record** 를 JSON 으로 주고받는다면 이 한 줄을 확인하고 가야 한다. `@JsonCreator(mode = DELEGATING)` 으로 옛 동작을 되살릴 수 있다고 같은 문서가 안내한다.

**Spring Boot 설정 바인딩.** 공식 문서가 record 를 직접 언급한다.[^bootcfg]

> **Constructor binding can be used with records.** Unless your record has multiple constructors, there is no need to use `@ConstructorBinding`.

단, 같은 절의 제약도 같이 읽어야 한다 — 생성자 바인딩은 `@EnableConfigurationProperties` 나 설정 프로퍼티 스캐닝으로 등록된 클래스에만 적용되고, **`@Component`·`@Bean`·`@Import` 로 만들어진 빈에는 쓸 수 없다.**[^bootcfg] 설정 클래스는 record 가 잘 맞는 대표적인 자리다.

**JavaBeans 규약.** record 접근자는 `getX()` 가 아니라 `x()` 다. getter 이름 규약에 의존하는 도구(일부 표현식 언어, 옛 태그 라이브러리, 리플렉션으로 `get*` 을 훑는 코드)는 record 컴포넌트를 **속성으로 보지 못한다**. 이건 버그가 아니라 §1 의 설계 결과이고, JEP 가 Non-Goals 에 "JavaBeans 규약을 쓰는 가변 클래스의 문제는 다루지 않는다" 고 적어 둔 것과 같은 이야기다.[^jep395]

---

## 8. 빌드·툴체인 리스크의 비대칭

record 는 **언어 기능**이다. javac 가 만든다. 빌드 도구가 허락할 일이 없다.

`@Data` 는 **애너테이션 프로세싱 위에** 있다. 그리고 그 바닥이 최근에 움직였다. Oracle 의 JDK 23 릴리스 노트, JDK-8321314 다.[^jdk23]

> **Annotation processing in `javac` disabled by default (JDK-8321314)**
>
> As of JDK 23, annotation processing is only run with some explicit configuration of annotation processing or with an explicit request to run annotation processing on the `javac` command line. ...
>
> Invocations of `javac` that rely on annotation processing without any explicit annotation processing configuration will need to be updated to keep running annotation processors. **In JDK 21 and 22, `javac` prints a note identifying such invocations.** To preserve the old behavior, `-proc:full` can be passed to `javac`.

같은 노트가 Maven Compiler Plugin 의 `maven.compiler.proc` 프로퍼티까지 안내한다. 최신 빌드 플러그인들은 이미 대응했으므로 대부분의 프로젝트는 아무 일 없이 넘어갔다. 요점은 "Lombok 이 곧 깨진다" 가 아니다.

요점은 **의존의 방향**이다. 언어 기능은 툴체인의 기본값이 바뀌어도 영향을 받지 않고, 코드 생성기는 받는다. 10년짜리 코드베이스에서 이 비대칭은 한 번은 청구된다.

(애너테이션 프로세싱이 꺼진 빌드에서 Lombok 이 어떤 증상으로 나타나는지 — 생성되지 않은 getter 호출부에서 컴파일 에러가 나는 형태일 것 — 는 문서에서 인용한 게 아니라 위 동작으로부터의 **추론**이다. 자기 빌드에서 확인하는 게 맞다.)

---

## 9. 결정표

| 상황 | 선택 | 근거 |
|---|---|---|
| 불변 값, 모든 컴포넌트를 그대로 노출 | **record** | 설계 의도 그대로 |
| 표현을 바꿔도 API 는 지켜야 함 | **record 불가** | API ↔ 표현 분리를 포기하는 게 계약 |
| 상속 계층이 필요 | **record 불가** | `extends` 절 없음, 암묵적 final |
| JavaBeans `getX()` 규약을 요구하는 경계 | `@Value` 또는 손으로 | record 접근자는 `x()` |
| JPA 엔티티 | **둘 다 아님** | record 는 구조적 불가, `@Data` 는 setter·toString·callSuper |
| DTO / 조회 프로젝션 / 이벤트 페이로드 | **record** | 얕은 불변 + 명세된 equals 계약 |
| Spring `@ConfigurationProperties` | **record** | 생성자 바인딩 공식 지원 |
| 가변 빈이 정말 필요 (폼 바인딩 등) | `@Data` | record 가 다루지 않기로 한 영역 |
| 빌더가 필요한 불변 타입 | record + `@Builder` | `@Builder` 는 **생성자에도** 붙는다[^lombokbuilder] |
| 컴포넌트 10개 넘는 값 타입 | 재검토 | 그건 타입이 하나 더 필요하다는 신호다 |

마지막 줄의 `@Builder` 는 문서의 다음 규칙에서 따라 나온다 — "`@Builder` can be placed on a class, or on a constructor, or on a method."[^lombokbuilder] record 의 canonical constructor 는 생성자이므로 여기에 해당한다. 둘은 배타적이지 않다. **record 를 쓰면서 Lombok 을 쓰는 조합이 실무에서 가장 흔한 정답**인 경우가 많다.

한 줄 요약 — **`@Data` 는 "이 클래스의 보일러플레이트를 대신 써 달라" 는 요청이고, record 는 "이 타입은 이 값들이다" 라는 선언이다.** 앞의 것은 구현 편의이고 뒤의 것은 의미론이다. 그래서 둘은 대체 관계가 아니며, 대체하려 들 때 §4 와 §6 같은 자리에서 대가를 치른다.

---

## 근거의 한계

- **성능 비교를 하지 않았다.** 두 방식의 런타임 성능을 비교한 중립적인 벤치마크를 찾지 못했다. 생성되는 바이트코드가 사실상 같은 모양이라 유의미한 차이가 없을 것이라 **추정**하지만, 측정하지 않은 것을 사실로 적지 않는다.
- **"Lombok 은 코드 품질을 해친다" 류의 주장은 다루지 않았다.** 조직의 취향과 규율 문제여서 문서로 판정할 수 없다. 이 글은 문서로 판정 가능한 것만 다뤘다.
- **JPA 의 `equals`/`hashCode` 는 요약하지 않았다.** Hibernate 가 한 절을 할애할 만큼 맥락 의존적이라, 한 줄로 옮기면 틀린 말이 되기 쉽다. §6 은 **구조적 제약**(final·no-arg 생성자)만 단정했고 나머지는 원문으로 넘겼다.
- **§8 의 증상 서술은 추론이다.** JDK 23 의 기본값 변경은 릴리스 노트 원문이지만, 그것이 각자의 빌드에서 어떤 에러로 나타나는지는 빌드 도구와 플러그인 버전에 달려 있다. 실측을 권한다.
- **버전 기준**: record 는 JEP 395(JDK 16 정식). Lombok 은 현재 공식 기능 문서. Jackson 은 2.12 릴리스 노트. Hibernate 인용은 사용자 가이드 5.2 의 Entity types 장이며, 같은 절 제목(3.4.2 Prefer non-final classes / 3.4.3 Implement a no-argument constructor / 3.4.7 Implementing equals() and hashCode())이 7.3·8.0 가이드 목차에도 그대로 있음을 확인했다. 그래도 자신의 Hibernate 버전 문서로 재확인하는 편이 안전하다.

---

## References

[^jep395]: OpenJDK 공식 — [JEP 395: Records](https://openjdk.org/jeps/395) (Status: Closed / Delivered, Release 16). Non-Goals, Description, Rules for record classes 절.
[^recordjavadoc]: Oracle 공식 API 문서 — [`java.lang.Record` (Java SE 21)](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/Record.html)
[^lombokdata]: Project Lombok 공식 기능 문서 — [`@Data`](https://projectlombok.org/features/Data)
[^lombokeq]: Project Lombok 공식 기능 문서 — [`@EqualsAndHashCode`](https://projectlombok.org/features/EqualsAndHashCode)
[^lombokvalue]: Project Lombok 공식 기능 문서 — [`@Value`](https://projectlombok.org/features/Value)
[^lombokbuilder]: Project Lombok 공식 기능 문서 — [`@Builder`](https://projectlombok.org/features/Builder)
[^hibernate]: Hibernate ORM 공식 사용자 가이드 — [Entity types](https://docs.hibernate.org/orm/5.2/userguide/html_single/chapters/domain/entity.html) (JPA 명세 §2.1 The Entity Class 의 요구사항을 인용하고 있다). 최신 목차는 [Hibernate ORM 7.3 User Guide](https://docs.hibernate.org/orm/7.3/userguide/html_single/) 참조.
[^jackson]: FasterXML 공식 위키 — [Jackson Release 2.12](https://github.com/FasterXML/jackson/wiki/Jackson-Release-2.12) 및 [jackson-databind#2709](https://github.com/FasterXML/jackson-databind/issues/2709)
[^bootcfg]: Spring 공식 문서 — [Externalized Configuration — Constructor Binding](https://docs.spring.io/spring-boot/reference/features/external-config.html)
[^jdk23]: Oracle 공식 — [Consolidated JDK 23 Release Notes](https://www.oracle.com/java/technologies/javase/23all-relnotes.html), tools/javac: "Annotation processing in `javac` disabled by default (JDK-8321314)"
