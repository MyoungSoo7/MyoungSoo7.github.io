---
layout: post
title: "*프록시* 와 *데코레이터* — *구조는 쌍둥이, 의도는 남남*: GoF 원전 정의부터 *인터페이스 기반(JDK)* vs *구체 클래스 기반(CGLIB)* 프록시의 갈림길까지"
date: 2026-07-28 00:26:00 +0900
categories: [java, spring, design-patterns]
tags: [Proxy, Decorator, GoF, DesignPatterns, SpringAOP, CGLIB, JDKDynamicProxy, Hibernate, Servlet]
---

# 같은 그림, 다른 의도

프록시 패턴과 데코레이터 패턴의 UML 을 나란히 그려보면 **거의 구분이 안 된다.** 둘 다

- 대상과 **같은 인터페이스**를 구현하고,
- 내부에 **대상 참조**를 하나 들고,
- 호출을 받으면 **뭔가 하고 대상에게 넘긴다.**

GoF 도 이 사실을 인정한다. 두 패턴 모두 "Decorator·Proxy 객체의 인터페이스가 장식/대리되는 객체의 인터페이스와 **동일할 것**을 요구한다"고 명시한다.

그런데도 GoF 는 이 둘을 **별개의 패턴으로 나눴다.** 이유는 하나다 — **의도(intent)가 다르기 때문**이다. 그리고 실무에서 이 둘을 헷갈리면 "왜 이 래퍼를 두 개 겹치면 안 되지?", "왜 이 프록시는 클라이언트가 못 만들지?" 같은 질문에서 코드가 꼬이기 시작한다.

이 글은 다음 순서로 간다.

1. **프록시의 정의** — 객체 프록시로 좁혀오기
2. **프록시 패턴** 소개 → 예제
3. **데코레이터 패턴** 소개 → 예제
4. **둘의 비교 정리**
5. **인터페이스 기반 프록시(JDK Dynamic Proxy)** 의 적용점
6. **구체 클래스 기반 프록시(CGLIB)** 의 적용점
7. **두 프록시 방식의 비교** — Spring 에서의 선택 기준

Spring AOP 의 self-invocation 함정 같은 *프레임워크 운용* 이슈는 예전 글([Reflection 과 Proxy]({% post_url 2026-07-14-spring-reflection-and-proxy-deep-dive %}), [Spring AOP 와 Pointcut]({% post_url 2026-06-06-spring-aop-aspect-pointcut-senior-explains-with-examples %}))에서 다뤘으니, 이 글은 **패턴 자체와 프록시 생성 방식의 선택**에 집중한다.

---

# 1. 프록시란 무엇인가

## 1.1 일반적 정의 — "대리(代理)"

프록시(proxy)는 원래 **"대리인"** 이라는 뜻이다. 소프트웨어에서는 계층을 가리지 않고 같은 개념이 반복된다.

| 층위 | 프록시의 실체 | 하는 일 |
|---|---|---|
| 네트워크 | forward/reverse proxy (nginx 등) | 클라이언트 대신 요청을 받아 뒤로 전달 |
| 원격 호출 | RPC/REST 클라이언트 스텁 | 로컬 객체처럼 보이지만 실제로는 원격 호출 |
| 객체 | Proxy 패턴 구현체 | 대상 객체 대신 호출을 받아 통제 후 위임 |

공통 구조는 **"클라이언트는 진짜에게 직접 말하지 않는다"** 이고, 공통 효과는 **간접층(indirection)** 이다. 이 글의 주제는 세 번째, **객체 수준의 프록시**다.

## 1.2 GoF 의 정의

> **Proxy**: Provide a surrogate or placeholder for another object to **control access to it**.
> — Gamma, Helm, Johnson, Vlissides, *Design Patterns: Elements of Reusable Object-Oriented Software* (Addison-Wesley, 1994), p.207

핵심 동사는 **control access** — "접근을 통제한다"이다. 무엇을 위해 통제하는가에 따라 GoF 는 프록시를 네 종류로 나눈다. (이 분류는 1993년 ECOOP 논문에서 이미 제시됐다.)

| 종류 | 목적 | 실무 예 |
|---|---|---|
| **Remote Proxy** | 다른 주소공간의 객체를 대신 표현 | RPC 스텁, Feign/HTTP Interface 클라이언트 |
| **Virtual Proxy** | 비싼 객체 생성을 **필요할 때까지 미룸** | Hibernate lazy loading, `EntityManager.getReference()` |
| **Protection Proxy** | 접근 권한 검사 | 권한 검사 래퍼, Spring Security 메서드 보안 |
| **Smart Reference** | 접근 시 부가 동작(참조 카운트·락·로딩 체크) | 트랜잭션 리소스 관리, 접근 감사 |

**Spring 을 쓴다는 것은 이 네 가지를 매일 쓴다는 뜻이다.** `@Transactional`, `@Async`, `@Cacheable`, Spring Data 리포지토리, JPA 지연 로딩 — 전부 프록시다.

---

# 2. 프록시 패턴

## 2.1 구조

```
   Client ──▶ ┌─────────────┐
              │  «interface» │
              │   Subject    │
              └─────────────┘
                 ▲        ▲
                 │        │
      ┌──────────┴──┐  ┌──┴────────────┐
      │ RealSubject │◀─│     Proxy     │   ── proxy 가 realSubject 참조를 들고
      └─────────────┘  └───────────────┘      "언제 / 누구에게 / 어떻게" 넘길지 결정
```

**클라이언트는 `Subject` 타입만 안다.** `RealSubject` 로 갈지, 갈 때 무엇을 검사할지는 프록시가 정한다.

## 2.2 예제 ① 보호 프록시 — 계좌 상세 조회

금융 시스템에서 계좌 상세 조회는 **"조회할 수 있는가"가 "조회한다"보다 먼저**다. 그런데 조회 로직 자체는 권한을 알 필요가 없다.

```java
// 공통 계약
public interface AccountQuery {
    AccountDetail findDetail(String accountNo);
}
```

```java
// RealSubject — 순수한 조회 책임만 갖는다
public class JdbcAccountQuery implements AccountQuery {

    private final AccountRepository repository;

    public JdbcAccountQuery(AccountRepository repository) {
        this.repository = repository;
    }

    @Override
    public AccountDetail findDetail(String accountNo) {
        return repository.findByAccountNo(accountNo)
                .orElseThrow(() -> new AccountNotFoundException(accountNo));
    }
}
```

```java
// Proxy — 접근을 "통제"한다. 조회 방법은 전혀 모른다.
public class ProtectedAccountQuery implements AccountQuery {

    private final AccountQuery target;
    private final AccessPolicy policy;
    private final AuditLogPort auditLog;

    public ProtectedAccountQuery(AccountQuery target, AccessPolicy policy, AuditLogPort auditLog) {
        this.target = target;
        this.policy = policy;
        this.auditLog = auditLog;
    }

    @Override
    public AccountDetail findDetail(String accountNo) {
        Principal principal = CurrentPrincipal.require();

        if (!policy.canRead(principal, accountNo)) {
            auditLog.denied(principal, accountNo);           // 거절도 감사 대상
            throw new AccessDeniedException("계좌 조회 권한 없음: " + accountNo);
        }
        auditLog.granted(principal, accountNo);
        return target.findDetail(accountNo);                  // 통과한 것만 위임
    }
}
```

**여기서 프록시가 하는 일의 성격을 보라.** 결과를 *꾸미지* 않는다. 반환값도 그대로다. **호출이 대상에 도달할지 말지를 결정**할 뿐이다. 이게 "control access" 다.

조립은 이렇게 된다.

```java
AccountQuery query = new ProtectedAccountQuery(
        new JdbcAccountQuery(repository), policy, auditLog);
```

## 2.3 예제 ② 가상 프록시 — 그리고 이건 이미 우리 코드에 있다

무거운 대상을 **실제로 필요해질 때까지 만들지 않는** 프록시다. 직접 만들면 이렇게 생겼다.

```java
public class LazyStatementImage implements StatementImage {

    private final String imageId;
    private final ImageStore store;
    private byte[] loaded;                     // 아직 안 읽음

    @Override
    public byte[] bytes() {
        if (loaded == null) {
            loaded = store.download(imageId);  // 첫 접근에 진짜 로딩
        }
        return loaded;
    }
}
```

그런데 **Hibernate 가 이미 정확히 이 일을 한다.** Hibernate 공식 javadoc 의 설명이 가상 프록시의 교과서적 서술이다.

> When bytecode enhancement is not used, an unfetched lazy association is represented by a **proxy object which holds the identifier (foreign key)** of the associated entity instance. … **A delegate entity instance is lazily fetched when any other method of the proxy is called.** Once fetched, the proxy delegates all method invocations to the delegate.
> — [Hibernate javadoc, `org.hibernate.Hibernate`](https://docs.hibernate.org/orm/current/javadocs/org/hibernate/Hibernate.html)

그래서 `em.getReference(Parent.class, id)` 는 **DB 쿼리 없이** 참조만 준다. Hibernate 사용자 가이드가 용도를 그대로 적어뒀다 — "In some cases, you don't really want to load the object state, but just having a reference to it (ie **a proxy**) … This is especially useful to link a child to its parent without having to load the parent."

**그리고 여기서 프록시의 대가가 드러난다.** 같은 javadoc 이 경고한다.

> The proxy **does not have the same concrete type** as the proxied delegate, and so `getClass(Object)` must be used in place of `Object.getClass()` … **`instanceof`** … `unproxy(Object, Class)` must be used to perform typecasts.

즉 **프록시는 "같은 인터페이스"이지 "같은 클래스"가 아니다.** 이 한 문장이 뒤(6·7장)의 CGLIB 논의와 그대로 연결된다.

---

# 3. 데코레이터 패턴

## 3.1 GoF 의 정의

> **Decorator**: **Attach additional responsibilities** to an object **dynamically**. Decorators provide a **flexible alternative to subclassing** for extending functionality.
> — GoF (1994), p.175

핵심 동사는 **attach additional responsibilities** — "책임을 덧붙인다"이다. 그리고 조건이 하나 더 붙는다: **동적으로**, 그리고 **상속의 대안으로**.

"상속의 대안"이 왜 중요한지는 조합 폭발을 그려보면 안다. 전문 전송에 압축·암호화·서명 3가지 옵션이 있고 상속으로 풀면 — `Compressing`, `Encrypting`, `Signing`, `CompressingEncrypting`, `CompressingSigning`, … **2ⁿ 개의 클래스**가 필요하다. 데코레이터는 **런타임에 n 개를 조립**해 같은 표현력을 얻는다.

## 3.2 구조 — 재귀적 중첩이 본질

```
   Client ──▶ ┌─────────────┐
              │ «interface» │
              │  Component  │
              └─────────────┘
                 ▲        ▲
      ┌──────────┴──┐  ┌──┴──────────────┐
      │ ConcreteComp│  │   Decorator     │──┐ component 참조
      └─────────────┘  └─────────────────┘  │
                          ▲   ▲   ▲         │
                     ┌────┘   │   └────┐    │  ← 데코레이터가 데코레이터를 감쌀 수 있다
                  Compress  Encrypt  Sign ──┘     (재귀적 중첩)
```

**데코레이터가 데코레이터를 감쌀 수 있다**는 점이 프록시와 갈리는 결정적 지점이다.

## 3.3 예제 — 대외 전문 전송 파이프라인

금융 대외계 전문은 대개 **압축 → 암호화 → 서명** 을 거쳐 나가고, 감사 요건상 **원문 해시를 남겨야** 한다. 그런데 이 조합은 **거래처마다 다르다.** A 기관은 압축 없이 암호화만, B 기관은 셋 다, 내부 테스트는 아무것도 안 함.

```java
public interface MessageSink {
    void write(byte[] payload);
}
```

```java
// ConcreteComponent — 진짜 전송
public class SocketMessageSink implements MessageSink {

    private final OutputStream out;

    @Override
    public void write(byte[] payload) {
        try {
            out.write(payload);
            out.flush();
        } catch (IOException e) {
            throw new MessageTransmitException(e);
        }
    }
}
```

```java
// 공통 데코레이터 — 기본 동작은 "그냥 위임"
public abstract class MessageSinkDecorator implements MessageSink {

    protected final MessageSink delegate;

    protected MessageSinkDecorator(MessageSink delegate) {
        this.delegate = Objects.requireNonNull(delegate);
    }

    @Override
    public void write(byte[] payload) {
        delegate.write(payload);
    }
}
```

```java
public class CompressingSink extends MessageSinkDecorator {

    public CompressingSink(MessageSink delegate) { super(delegate); }

    @Override
    public void write(byte[] payload) {
        super.write(Deflates.compress(payload));      // 변환 후 위임
    }
}

public class EncryptingSink extends MessageSinkDecorator {

    private final SecretKey key;

    public EncryptingSink(MessageSink delegate, SecretKey key) {
        super(delegate);
        this.key = key;
    }

    @Override
    public void write(byte[] payload) {
        super.write(Aes.encrypt(payload, key));
    }
}

public class SigningSink extends MessageSinkDecorator {

    private final PrivateKey signingKey;

    public SigningSink(MessageSink delegate, PrivateKey signingKey) {
        super(delegate);
        this.signingKey = signingKey;
    }

    @Override
    public void write(byte[] payload) {
        super.write(Signatures.attach(payload, signingKey));
    }
}

public class HashAuditingSink extends MessageSinkDecorator {

    private final AuditLogPort auditLog;

    public HashAuditingSink(MessageSink delegate, AuditLogPort auditLog) {
        super(delegate);
        this.auditLog = auditLog;
    }

    @Override
    public void write(byte[] payload) {
        auditLog.recordOutbound(Sha256.hex(payload));  // 원문 해시를 먼저 남기고
        super.write(payload);
    }
}
```

**조립은 클라이언트(설정)의 몫이다.**

```java
// B 기관 — 감사 → 압축 → 암호화 → 서명 → 전송
MessageSink toBankB =
    new HashAuditingSink(
        new CompressingSink(
            new EncryptingSink(
                new SigningSink(new SocketMessageSink(out), signingKey),
            aesKey)),
        auditLog);

// A 기관 — 암호화만
MessageSink toBankA = new EncryptingSink(new SocketMessageSink(out), aesKey);

// 내부 테스트 — 맨몸
MessageSink toStub = new SocketMessageSink(out);
```

**순서가 곧 의미**라는 점을 눈여겨보라. `HashAuditingSink` 를 가장 바깥에 두면 *원문* 해시가, 가장 안쪽에 두면 *서명까지 끝난 최종 바이트* 의 해시가 남는다. 이 유연함이 데코레이터의 값어치이자 동시에 **위험**이다. 조립 순서가 규제 요건을 좌우한다면, 조립 코드는 반드시 한 곳에 모으고 테스트로 고정해야 한다.

## 3.4 자바 표준 라이브러리는 데코레이터로 만들어져 있다

이 패턴을 **처음 배우는 곳은 사실 `java.io`** 다. `FilterInputStream` 의 javadoc 이 데코레이터의 정의 그 자체다.

> A `FilterInputStream` **wraps some other input stream**, which it uses as its basic source of data, **possibly transforming the data along the way or providing additional functionality**. The class `FilterInputStream` itself simply overrides select methods of `InputStream` with versions that **pass all requests to the wrapped input stream**.
> — [FilterInputStream (Java SE 26)](https://docs.oracle.com/en/java/javase/26/docs/api/java.base/java/io/FilterInputStream.html)

```java
InputStream in = new DigestInputStream(          // 해시 계산 추가
                    new BufferedInputStream(     // 버퍼링 추가
                        new CipherInputStream(   // 복호화 추가
                            new FileInputStream(path), cipher)), digest);
```

`BufferedInputStream`·`CipherInputStream`·`DigestInputStream`·`CheckedInputStream` — 전부 `FilterInputStream` 의 하위 클래스, 전부 데코레이터다.

**서블릿 스펙은 아예 문서에 패턴 이름을 박아뒀다.**

> `HttpServletRequestWrapper` — Provides a convenient implementation of the `HttpServletRequest` interface that can be subclassed by developers wishing to adapt the request to a Servlet. **This class implements the Wrapper or Decorator pattern.** Methods default to calling through to the wrapped request object.
> — [Jakarta Servlet 6.1 API](https://jakarta.ee/specifications/servlet/6.1/apidocs/jakarta.servlet/jakarta/servlet/http/httpservletrequestwrapper)

그래서 요청 본문을 여러 번 읽거나(캐싱), 로그에서 계좌번호·주민번호를 마스킹하는 필터는 **`HttpServletRequestWrapper` 를 상속해 데코레이터로** 만든다.

```java
public class MaskingRequestWrapper extends HttpServletRequestWrapper {

    public MaskingRequestWrapper(HttpServletRequest request) { super(request); }

    @Override
    public String getParameter(String name) {
        String raw = super.getParameter(name);       // 기본은 위임
        return SensitiveFields.contains(name) ? Masks.mask(raw) : raw;
    }
}
```

---

# 4. 프록시 vs 데코레이터 — 비교 정리

## 4.1 한 장의 표

| 기준 | **프록시 패턴** | **데코레이터 패턴** |
|---|---|---|
| **GoF 의도** | 대리자를 두어 **접근을 통제**한다 | **책임을 동적으로 추가**한다 |
| 핵심 질문 | "이 호출을 **통과시킬 것인가**?" | "이 호출에 **무엇을 더할 것인가**?" |
| 대상과의 관계 | 보통 **1:1**, 프록시가 대상을 **소유·관리**(생성 시점까지 결정) | **1:N 중첩**, 클라이언트가 조립 |
| 누가 조립하는가 | **프레임워크/인프라** (클라이언트는 모름) | **클라이언트/설정 코드** (명시적으로 감쌈) |
| 대상의 존재 | **아직 없을 수도** 있다 (가상 프록시) | **이미 존재**하는 객체를 감싼다 |
| 결과값 | 대개 **그대로** 통과 | 종종 **변형**됨 |
| 중첩 | 잘 하지 않음 | **재귀적 중첩이 본질** |
| 클라이언트 인지 | 대개 **모른다**(투명) | 대개 **안다**(직접 조립하므로) |
| 대표 예 | `@Transactional` 프록시, Hibernate lazy proxy, 권한 프록시 | `java.io` 스트림, `HttpServletRequestWrapper`, `Collections.unmodifiableList` |

## 4.2 구분이 헷갈릴 때 던질 질문 3개

**Q1. 이 래퍼를 두 겹, 세 겹 쌓는 게 자연스러운가?**
→ 자연스러우면 **데코레이터**. `BufferedInputStream(CipherInputStream(...))` 은 자연스럽고, `ProtectedAccountQuery(ProtectedAccountQuery(...))` 는 이상하다.

**Q2. 클라이언트가 진짜 객체에 직접 접근할 수 있나?**
→ 접근할 수 없고 **반드시 래퍼를 거쳐야** 하면 프록시 성격이 강하다. 데코레이터에서는 클라이언트가 원본을 손에 쥐고 있다가 감싸는 게 보통이다.

**Q3. 래퍼가 대상의 *생성·수명*까지 관여하나?**
→ 관여하면 **프록시**(특히 가상 프록시). 데코레이터는 **이미 만들어진 것**을 받는다.

## 4.3 실무의 정직한 결론 — "겹친다"

솔직히 말하면, 실무 코드의 상당수는 **두 성격을 동시에** 갖는다. 로깅 래퍼는 "책임 추가"(데코레이터)이면서 "모든 접근을 가로챈다"(프록시)이기도 하다. Spring AOP 의 CGLIB 프록시를 설명하는 Spring 공식 문서조차 **프록시를 만드는 방식을 데코레이터로 서술**한다.

> CGLIB proxying works by generating a subclass of the target class at runtime. Spring configures this generated subclass to delegate method calls to the original target. **The subclass is used to implement the Decorator pattern**, weaving in the advice.
> — [Spring Framework Reference — ProxyFactoryBean](https://docs.spring.io/spring-framework/reference/core/aop-api/pfb.html)

**그러니 목표는 "정확한 이름표 붙이기"가 아니다.** 진짜 목적은 이것이다.

> **의도를 코드로 드러내라.**
> 접근 통제가 목적이면 — 중첩을 허용하지 말고, 조립을 인프라 계층에 숨기고, 클라이언트가 원본을 못 잡게 하라.
> 책임 추가가 목적이면 — 공통 추상 데코레이터를 두고, 중첩 순서를 명시적으로 관리하고, 조립 코드를 한 곳에 모아라.

---

# 5. 인터페이스 기반 프록시 (JDK Dynamic Proxy)

여기서부터는 "패턴을 **어떻게 만들 것인가**"의 문제다. 프록시 클래스를 손으로 짜면 메서드가 30개인 인터페이스에서 곧 무너진다. 그래서 런타임 생성을 쓴다.

## 5.1 어떻게 동작하는가

JDK 표준 API 다. `java.lang.reflect.Proxy` javadoc 이 계약을 정확히 규정한다.

> A **proxy class** is a class created at runtime that implements a specified list of interfaces, known as **proxy interfaces**. … A method invocation on a proxy instance through one of its proxy interfaces will be **dispatched to the `invoke` method of the instance's invocation handler**, passing the proxy instance, a `java.lang.reflect.Method` object identifying the method that was invoked, and an array of type `Object` containing the arguments.
> — [Proxy (Java SE 26)](https://docs.oracle.com/en/java/javase/26/docs/api/java.base/java/lang/reflect/Proxy.html)

앞의 보호 프록시를 동적으로 만들면 이렇게 된다.

```java
public class AccessControlHandler implements InvocationHandler {

    private final Object target;
    private final AccessPolicy policy;

    public AccessControlHandler(Object target, AccessPolicy policy) {
        this.target = target;
        this.policy = policy;
    }

    @Override
    public Object invoke(Object proxy, Method method, Object[] args) throws Throwable {
        if (method.isAnnotationPresent(RequiresAccountAccess.class)) {
            String accountNo = (String) args[0];
            if (!policy.canRead(CurrentPrincipal.require(), accountNo)) {
                throw new AccessDeniedException("계좌 조회 권한 없음: " + accountNo);
            }
        }
        try {
            return method.invoke(target, args);
        } catch (InvocationTargetException e) {
            throw e.getTargetException();     // 원인 예외를 그대로 올린다 (중요)
        }
    }
}
```

```java
AccountQuery proxy = (AccountQuery) Proxy.newProxyInstance(
        AccountQuery.class.getClassLoader(),
        new Class<?>[] { AccountQuery.class },
        new AccessControlHandler(new JdbcAccountQuery(repository), policy));
```

`InvocationTargetException` 을 벗겨내는 처리를 빼먹으면 **모든 비즈니스 예외가 리플렉션 예외로 둔갑**한다. 손으로 쓸 때 가장 흔한 버그다.

## 5.2 적용점 — 언제 인터페이스 기반이 유리한가

**① 계약이 인터페이스로 명확히 정의돼 있을 때**
프록시가 잡는 범위 = 인터페이스에 선언된 메서드. **경계가 문서화된 계약과 정확히 일치**한다. "이 메서드는 왜 어드바이스가 안 걸리지?"라는 질문 자체가 줄어든다.

**② 구현체를 건드릴 수 없을 때 (`final` 이어도 무관)**
JDK 프록시는 상속이 아니라 **인터페이스 구현**이다. 구현 클래스가 `final` 이든, 생성자가 복잡하든 상관없다.

**③ 구현체가 아예 없을 때 — 가장 강력한 사례**
Spring Data JPA 리포지토리를 떠올려보라.

```java
public interface SettlementRepository extends JpaRepository<Settlement, Long> {
    List<Settlement> findByMerchantIdAndSettledAtBetween(String merchantId, Instant from, Instant to);
}
```

**구현 클래스를 아무도 안 짰다.** 그런데 동작한다. 인터페이스만으로 프록시를 만들고 메서드 이름을 파싱해 쿼리를 생성하기 때문이다. **구체 클래스 기반 프록시로는 원리적으로 불가능한 일**이다 — 상속할 클래스가 없으니까.

**④ 노출 인터페이스를 좁히고 싶을 때**
Spring Framework 7.0 부터는 `@Proxyable(interfaces=…)` 로 **대상이 구현한 모든 인터페이스가 아니라 선택한 인터페이스만** 프록시에 노출할 수 있다 — 공식 문서 표현으로 "limiting the exposure to selected interfaces". 내부용 인터페이스를 프록시 타입에서 감출 수 있다는 뜻이다.

## 5.3 한계

- **인터페이스에 없는 메서드는 못 잡는다.** `public` 이어도 인터페이스에 선언되지 않았으면 프록시 대상 밖이다.
- **구체 타입으로 캐스팅하면 터진다.** 프록시는 `JdbcAccountQuery` 가 **아니다**.

```java
@Autowired
private JdbcAccountQuery query;   // ❌ 구체 타입 주입 → JDK 프록시 환경에서 주입 실패
```

- `equals`/`hashCode`/`toString` 도 **핸들러로 디스패치된다**(javadoc 명시). 핸들러가 이를 고려하지 않으면 컬렉션 동작이 이상해진다.

---

# 6. 구체 클래스 기반 프록시 (CGLIB)

## 6.1 어떻게 동작하는가

**대상 클래스를 상속한 서브클래스를 런타임에 생성**하고, 각 메서드를 오버라이드해 가로챈 뒤 원본에 위임한다. Spring 공식 문서의 서술 그대로다 — "a CGLIB proxy is created which is a **runtime-generated subclass of the target type**". CGLIB 는 별도 의존성이 아니라 **`spring-core` 에 리패키징돼 포함**돼 있다.

```
 [클라이언트] ──▶ SettlementService$$SpringCGLIB$$0   ← 런타임 생성 서브클래스
                        │  extends
                        ▼
                  SettlementService                  ← 내 클래스 (인터페이스 없어도 됨)
```

## 6.2 적용점 — 언제 클래스 기반이 유리한가

**① 인터페이스가 없을 때 (그리고 만들 이유도 없을 때)**
구현체가 하나뿐인데 `XxxService` / `XxxServiceImpl` 를 기계적으로 만드는 관행에는 실익이 없다. 인터페이스 없이 클래스 하나로 두고 CGLIB 로 프록시하면 된다. Spring 문서도 "레거시 코드를 다룰 때 유용하다"고 인정한다.

**② 인터페이스에 선언되지 않은 public 메서드까지 어드바이스해야 할 때**
공식 문서가 이 목적을 명시한다 — "to proxy **every method defined for the target object**, not only those implemented by its interfaces".

**③ 구체 타입으로 주입·캐스팅이 필요할 때**
테스트나 레거시 코드가 구체 타입을 요구하면 클래스 기반이 답이다.

**④ 그리고 — Spring Boot 의 기본값이 이것이다**

> By default, Spring Boot's auto-configuration configures Spring AOP to use **CGLib proxies**. To use JDK proxies instead, set `spring.aop.proxy-target-class` to `false`.
> — [Spring Boot Reference — Aspect-Oriented Programming](https://docs.spring.io/spring-boot/reference/features/aop.html)

여기서 **자주 오해가 생긴다.** Spring Framework 코어의 서술과 Spring Boot 의 기본값이 다르다.

- **Spring Framework 코어**: "Spring AOP **defaults to using standard JDK dynamic proxies**" / 인터페이스가 하나라도 있으면 JDK, 없으면 CGLIB
- **Spring Boot**: 자동설정이 **CGLIB 를 기본으로 켠다**

공식 문서도 이 차이를 명시적으로 인정한다 — "The global default proxy type **may differ between setups.** While the core framework suggests interface-based proxies by default, **Spring Boot may — depending on configuration properties — enable class-based proxies by default.**"

**즉, 인터페이스를 만들어 놨어도 Spring Boot 앱에서는 대개 CGLIB 프록시가 만들어진다.** "인터페이스가 있으니 JDK 프록시겠지"라고 가정한 코드는 틀린다.

## 6.3 한계 — 상속의 제약을 그대로 물려받는다

공식 문서가 나열하는 제약이 곧 상속의 제약이다.

- **`final` 클래스는 프록시 불가** — 확장할 수 없으므로
- **`final` 메서드는 어드바이스 불가** — 오버라이드할 수 없으므로 (예외도 안 나고 **조용히 안 걸린다**)
- **`private` 메서드는 어드바이스 불가**
- **패키지-프라이빗 등 보이지 않는 메서드도 불가** — "effectively private"
- **생성자 우회**: "The constructor of your proxied object will not be called twice, since the CGLIB proxy instance is created through **Objenesis**." → 생성자가 실행되지 않으므로 **프록시 인스턴스 자신의 필드 상태에 의존하는 코드를 쓰면 안 된다.** (모든 호출은 타깃 인스턴스로 위임되므로 정상 동작하지만, 프록시 객체의 필드를 직접 읽는 코드는 예외다.)
- **모듈 시스템 제약**: 모듈 패스 배포 시 `java.lang` 패키지 클래스는 CGLIB 프록시 불가 — `--add-opens=java.base/java.lang=ALL-UNNAMED` 가 필요한데 모듈에는 쓸 수 없다

특히 **Kotlin 을 섞어 쓰면 ①②가 즉시 문제**가 된다. Kotlin 의 클래스·메서드는 기본이 `final` 이다. `kotlin-spring` 플러그인(`all-open`)이 필요한 이유가 정확히 이것이다.

---

# 7. 두 방식의 비교

## 7.1 표

| 기준 | **인터페이스 기반 (JDK Dynamic Proxy)** | **구체 클래스 기반 (CGLIB)** |
|---|---|---|
| 생성 원리 | 지정한 **인터페이스들을 구현**하는 클래스를 런타임 생성 | 대상 클래스를 **상속한 서브클래스**를 런타임 생성 |
| 의존성 | **JDK 내장** (`java.lang.reflect.Proxy`) | `spring-core` 에 리패키징 포함 |
| 필수 조건 | 인터페이스가 **하나 이상** 있어야 함 | 클래스가 `final` 이 아니어야 함 |
| 프록시 범위 | 인터페이스에 **선언된 메서드만** | `final`/`private`/불가시 를 제외한 **모든 메서드** |
| 구체 타입 캐스팅 | **불가** (`ClassCastException`) | 가능 (서브클래스이므로) |
| 구현체 없이 생성 | **가능** (Spring Data 리포지토리) | 불가능 |
| `final` 클래스/메서드 | **영향 없음** | 프록시 불가 / 조용히 미적용 |
| 생성자 | 대상 생성자와 무관 | **Objenesis 로 우회** |
| 모듈 시스템 | 제약 적음 | `java.lang` 등에서 제약 |
| Spring 코어 기본 | **인터페이스 있으면 이것** | 인터페이스 없으면 이것 |
| Spring Boot 기본 | `spring.aop.proxy-target-class=false` 로 전환 | **기본값(true)** |
| 성능 | 공식 문서: **"little performance difference"** — 결정 기준으로 삼지 말 것 | 동일 |

성능에 대해서는 Spring 문서가 단정적으로 말한다 — "There is **little performance difference** between CGLIB proxies and dynamic proxies. **Performance should not be a decisive consideration** in this case." (다만 이는 프레임워크 벤더의 1차 서술이며, 중립 제3자 벤치마크는 확인하지 못했다. 성능이 정말 쟁점이라면 각자 워크로드에서 측정해야 한다.)

## 7.2 둘 다에 해당하는 함정 — self-invocation

**프록시 방식과 무관하게** 같은 객체 내부 호출은 프록시를 거치지 않는다. Spring 문서의 서술이 명확하다.

> once the call has finally reached the target object …, any method calls that it may make on itself, such as `this.bar()` …, are going to be invoked **against the `this` reference, and not the proxy**. … **self invocation via an explicit or implicit `this` reference will bypass the advice.**
> — [Understanding AOP Proxies](https://docs.spring.io/spring-framework/reference/core/aop/proxying.html)

```java
@Service
public class SettlementService {

    public void closeDaily(LocalDate date) {
        for (Merchant m : merchants) {
            this.settleOne(m, date);       // ❌ @Transactional 이 안 걸린다
        }
    }

    @Transactional
    public void settleOne(Merchant m, LocalDate date) { ... }
}
```

**프록시 기반 AOP 의 근본 한계**이며, JDK 든 CGLIB 든 동일하다. 해법은 문서가 권하는 순서대로 — ① 자기 호출이 없도록 리팩터링(별 빈으로 분리), ② 자기 참조 주입, ③ 최후에 `AopContext.currentProxy()`.

## 7.3 그래서 무엇을 고를 것인가 — 결정 트리

```
 프록시 대상에 인터페이스가 있나?
   ├── 없다 ─────────────────────────────────▶ CGLIB (선택지가 없다)
   └── 있다
        ├── 그 인터페이스가 "진짜 계약"인가?
        │     (구현이 여러 개 / 테스트 대역 / 모듈 경계)
        │      ├── 예 ─────────────────────▶ JDK 프록시 권장
        │      │                              (경계가 계약과 일치, 노출 최소화)
        │      └── 아니오 (Impl 하나뿐, 관행상 만든 것)
        │             └────────────────────▶ 인터페이스 제거 + CGLIB 가 더 정직
        └── 인터페이스에 없는 메서드도 어드바이스해야 하나?
               └── 예 ────────────────────▶ CGLIB (proxyTargetClass=true)
```

**Spring 7.0 이후에는 빈 단위로 지정할 수도 있다.** 전역 기본값을 흔들지 않고 특정 빈만 방식을 고정한다.

```java
@Bean
@Proxyable(TARGET_CLASS)          // 이 빈만 클래스 기반으로
SettlementService settlementService() { ... }
```

---

# 8. 정리

**패턴 층위**

- **프록시**는 *접근을 통제*한다 — remote / virtual / protection / smart reference
- **데코레이터**는 *책임을 덧붙인다* — 상속 조합 폭발의 대안, 재귀적 중첩이 본질
- 구조는 같다. **GoF 가 둘을 나눈 근거는 오직 의도**이며, 실무에서는 겹치는 경우가 흔하다. 이름표보다 **의도가 코드에 드러나는지**가 중요하다

**구현 층위**

- **JDK 동적 프록시**는 *인터페이스를 구현* — 계약이 곧 경계, `final` 무관, 구현체 없이도 가능
- **CGLIB**는 *클래스를 상속* — 인터페이스 불필요, 전체 메서드 커버, 대신 상속의 제약을 그대로 상속
- **Spring Boot 의 기본값은 CGLIB** 이고, 이는 Spring 코어의 서술("인터페이스가 있으면 JDK")과 다르다. 이 차이를 모르면 프록시 타입에 대한 가정이 틀린다
- **self-invocation 은 두 방식 모두에 해당한다.** 이것만은 방식 선택으로 해결되지 않는다

가장 실용적인 한 줄로 줄이면 이렇다.

> **인터페이스는 "프록시를 위해" 만들지 마라.** 계약이 필요해서 만들었으면 JDK 프록시가 잘 맞고, 계약이 필요 없어서 안 만들었으면 CGLIB 가 잘 맞는다. 순서가 거꾸로 가면 — 프록시 때문에 의미 없는 `Impl` 클래스가 생기고, 그 인터페이스는 아무도 두 번째 구현체를 만들지 않은 채 영원히 남는다.

---

## References

- Gamma, E., Helm, R., Johnson, R., Vlissides, J. *Design Patterns: Elements of Reusable Object-Oriented Software.* Addison-Wesley, 1994 — **Decorator (p.175)**: "Attach additional responsibilities to an object dynamically. Decorators provide a flexible alternative to subclassing for extending functionality." / **Proxy (p.207)**: "Provide a surrogate or placeholder for another object to control access to it." 및 두 패턴의 인터페이스 동일성 요구 서술. (1차 권위 — 원전)
- Gamma, E., Helm, R., Johnson, R., Vlissides, J. *Design Patterns: Abstraction and Reuse of Object-Oriented Design.* ECOOP '93 — remote / virtual / protected proxy 분류의 초기 제시. [cseweb.ucsd.edu/~wgg/CSE210/ecoop93-patterns.pdf](https://cseweb.ucsd.edu/~wgg/CSE210/ecoop93-patterns.pdf)
- Oracle. *java.lang.reflect.Proxy (Java SE 26 API)* — 프록시 클래스/인스턴스 정의, `InvocationHandler` 디스패치 계약. [docs.oracle.com/en/java/javase/26/…/Proxy.html](https://docs.oracle.com/en/java/javase/26/docs/api/java.base/java/lang/reflect/Proxy.html)
- Oracle. *FilterInputStream (Java SE 26 API)* — "wraps some other input stream … pass all requests to the wrapped input stream" (JDK 내 데코레이터). [docs.oracle.com/en/java/javase/26/…/FilterInputStream.html](https://docs.oracle.com/en/java/javase/26/docs/api/java.base/java/io/FilterInputStream.html)
- Jakarta EE. *HttpServletRequestWrapper (Jakarta Servlet 6.1 API)* — "This class implements the **Wrapper or Decorator pattern**." [jakarta.ee/specifications/servlet/6.1/apidocs/…](https://jakarta.ee/specifications/servlet/6.1/apidocs/jakarta.servlet/jakarta/servlet/http/httpservletrequestwrapper)
- Spring. *Spring Framework Reference — Proxying Mechanisms / Understanding AOP Proxies* — JDK vs CGLIB 선택 규칙, `final`/`private`/가시성 제약, Objenesis 생성자 우회, 모듈 시스템 제약, self-invocation, 7.0 `@Proxyable`. [docs.spring.io/spring-framework/reference/core/aop/proxying.html](https://docs.spring.io/spring-framework/reference/core/aop/proxying.html)
- Spring. *Spring Framework Reference — AOP Proxies* — "Spring AOP defaults to using standard JDK dynamic proxies". [docs.spring.io/spring-framework/reference/core/aop/introduction-proxies.html](https://docs.spring.io/spring-framework/reference/core/aop/introduction-proxies.html)
- Spring. *Spring Framework Reference — Using the ProxyFactoryBean to Create AOP Proxies* — "The subclass is used to implement the Decorator pattern", "little performance difference between CGLIB proxies and dynamic proxies". [docs.spring.io/spring-framework/reference/core/aop-api/pfb.html](https://docs.spring.io/spring-framework/reference/core/aop-api/pfb.html)
- Spring Boot. *Reference — Aspect-Oriented Programming* — "By default, Spring Boot's auto-configuration configures Spring AOP to use CGLib proxies … set `spring.aop.proxy-target-class` to `false`." [docs.spring.io/spring-boot/reference/features/aop.html](https://docs.spring.io/spring-boot/reference/features/aop.html)
- Hibernate. *`org.hibernate.Hibernate` javadoc* 및 *User Guide* — 지연 로딩 프록시의 동작(식별자 보유, 첫 호출 시 초기화), `getReference()`, 프록시의 구체 타입 불일치와 `unproxy`/`getClass` 주의. [docs.hibernate.org/orm/current/javadocs/org/hibernate/Hibernate.html](https://docs.hibernate.org/orm/current/javadocs/org/hibernate/Hibernate.html)

*출처 등급: 패턴의 정의·분류는 GoF 원전(1994)과 ECOOP '93 논문(동료심사)을, 언어 차원의 동작은 Oracle javadoc 과 Jakarta 스펙 API 문서를, 프레임워크 동작은 Spring/Spring Boot/Hibernate 공식 문서를 인용했다. 본문 코드는 설명용 예제이며 특정 금융기관의 실제 코드가 아니다. JDK 프록시와 CGLIB 의 성능 동등성 주장은 Spring 공식 문서의 서술을 인용한 것으로, 이는 프레임워크 벤더의 1차 진술이며 중립 제3자 벤치마크는 확인하지 못했다 — 성능이 쟁점인 상황이라면 자체 측정이 필요하다.*
