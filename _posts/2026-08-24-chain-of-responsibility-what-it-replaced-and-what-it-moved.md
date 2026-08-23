---
layout: post
title: "Chain of Responsibility — 무엇을 없앴고, 무엇을 옮겼나"
date: 2026-08-24 06:05:30 +0900
categories: [design-patterns, engineering]
tags: [chain-of-responsibility, gof, servlet-filter, netty, dom-events, kotlin]
---

디자인 패턴 글은 대개 "이렇게 쓰면 됩니다" 로 시작한다.
그러면 **왜 이게 생겼는지**가 빠진다. 패턴은 하늘에서 떨어진 게 아니라
누군가 같은 고통을 반복해서 겪다가 이름을 붙인 것이다.

그래서 이 글은 순서를 뒤집는다. **없던 시절 → 무엇이 아팠나 → 등장 → 그 뒤로 뭐가 달라졌나.**
마지막에는 내 저장소에서 이 전환이 실제로 일어난 커밋 하나를 열어본다.

---

## 1. before — 보내는 쪽이 받는 쪽을 알아야 했다

GUI 도움말을 생각해 보자. 버튼을 클릭하고 F1 을 누르면 도움말이 뜬다.
그런데 그 버튼에 특정 도움말이 없으면 그 버튼이 놓인 대화상자의 일반적인 도움말이,
그것도 없으면 애플리케이션 전체 도움말이 떠야 한다.

문제는 **버튼이 "누가 도움말을 줄지" 를 모른다**는 것이다.
버튼이 화면 어디에 놓이느냐에 따라 답이 달라지고, 그건 버튼을 만들 때 알 수 없다.
GoF 가 이 패턴의 동기(Motivation)로 든 예가 정확히 이것이다.[^gof]

패턴 이름이 붙기 전에 이 상황을 어떻게 풀었나. 두 가지 중 하나였다.

**(1) 보내는 쪽이 받는 쪽을 직접 참조한다.**

```java
// 버튼이 자기를 감싼 것들을 다 알아야 한다
if (parentDialog.hasHelp())      parentDialog.showHelp();
else if (parentWindow.hasHelp()) parentWindow.showHelp();
else                             app.showGenericHelp();
```

버튼 코드가 대화상자·윈도우·앱을 전부 안다. 새 계층이 하나 끼면 버튼을 고쳐야 한다.

**(2) 가운데에 거대한 분기 디스패처를 둔다.**

```java
switch (request.getType()) {
    case AUTH:    return authHandler.handle(request);
    case LOGGING: return logHandler.handle(request);
    case ...      // 핸들러가 늘 때마다 이 파일이 열린다
}
```

이쪽은 더 흔했다. 그리고 이 디스패처는 **모든 핸들러를 아는 유일한 지점**이 되어,
기능을 추가할 때마다 반드시 편집되는 파일이 된다. 병합 충돌이 몰리는 자리이기도 하다.

웹 서버 쪽에도 같은 before 가 있었고, 이건 기록이 남아 있다.
서블릿 스펙에 필터가 들어가기 전 상황을 오라클 문서는 이렇게 적는다 —
**여러 서블릿/JSP 컨테이너가 독자적인 필터 메커니즘을 도입했고, 그 컨테이너에 배포하는
개발자에게는 이득이었지만 그런 코드의 재사용성은 떨어졌다**는 것이다.[^filters]
인증·로깅·압축 같은 "요청을 가로채는" 일이 필요하긴 한데, 표준이 없으니
컨테이너마다 다른 방식으로 붙였고 옮기면 다시 짜야 했다.

---

## 2. 문제의 정확한 형태

위 사례들의 공통점을 GoF 는 세 문장으로 정리했다 —
**둘 이상의 객체가 요청을 처리할 수 있는데 누가 처리할지 미리 알 수 없을 때,
수신자를 명시하지 않고 요청을 던지고 싶을 때, 처리할 수 있는 객체 집합이 동적으로 정해져야 할 때.**[^gof]

핵심은 마지막이다. **집합이 동적**이라는 것. 컴파일 타임에 목록이 고정된다면
`switch` 로도 충분하다. 목록이 배포 시점에, 혹은 요청마다 달라질 수 있어야 하는 순간
분기문은 표현력을 잃는다.

---

## 3. 등장 — 1994년, 그리고 "암묵적 수신자"

Chain of Responsibility 는 1994년 GoF 카탈로그의 23개 패턴 중 하나로 이름을 얻었다.
의도는 한 문장이다 — 요청을 보내는 쪽과 받는 쪽의 결합을 피하기 위해,
**둘 이상의 객체에게 처리할 기회를 주고**, 수신 객체들을 사슬로 이어 누군가 처리할 때까지
요청을 흘려보낸다.[^gof]

구현은 놀랍도록 단순하다. 각 핸들러가 `successor` 하나를 들고, 처리하거나 넘긴다.

```java
abstract class HelpHandler {
    private HelpHandler successor;
    public void handleHelp() {
        if (successor != null) successor.handleHelp();   // 못 하면 다음으로
    }
}
```

GoF 가 만든 진짜 개념은 코드가 아니라 용어 쪽이다 — **암묵적 수신자(implicit receiver)**.
요청을 만든 객체는 누가 그걸 처리할지 **모르는 채로** 요청을 놓는다.
이게 전부다. 그리고 이 한 줄이 30년 뒤 웹 프레임워크 절반의 뼈대가 됐다.

---

## 4. after — 무엇이 사라졌나

### 4-1. 서블릿 필터 (2001)

`javax.servlet.Filter` 는 **Servlet 2.3 의 신규 기능**으로 들어왔다.
JSR 53 최종 릴리스는 2001년 9월 25일, 스펙 문서 날짜는 2001년 9월 17일이다.[^servlet23][^jsr53]
필터의 `doFilter` 는 다음 대상을 직접 부르지 않고 **체인 객체에게 부탁한다.**

```java
public void doFilter(ServletRequest req, ServletResponse res, FilterChain chain) {
    // ... 전처리
    chain.doFilter(req, res);   // 다음이 누구인지 나는 모른다
    // ... 후처리
}
```

여기서 **사라진 것**이 결정적이다. 필터는 자기 다음이 다른 필터인지 최종 서블릿인지 모른다.
그리고 체인의 구성과 순서는 코드가 아니라 **배포 서술자(`web.xml`)의 매핑 순서**로 정해진다.[^servlet23]
인증 필터를 하나 추가하는 일이 **자바 파일을 안 고치고** 끝난다.
스펙 문서가 예로 든 필터 목록 — 인증, 로깅/감사, 이미지 변환, 압축, 암호화 —
이 전부가 예전에는 서블릿 안에 섞여 있던 것들이다.[^servlet23]

`chain.doFilter` 를 **부르지 않으면** 요청이 거기서 끊긴다. 인증 실패 시 401 을 쓰고 멈추는
그 흔한 코드가 CoR 의 "내가 처리하고 끝낸다" 다.

### 4-2. DOM 이벤트 버블링 (2000)

브라우저 쪽에서도 같은 해법이 표준이 됐다. DOM Level 2 Events 는
2000년 11월 13일 W3C 권고안이 됐고(2020년 11월 3일자로 대체됨),
**버블링을 "이벤트가 대상에서 처리된 뒤 조상들을 따라 위로 전파되는 과정"** 으로 정의한다.[^dom2]

`Event.BUBBLING_PHASE = 3`, 그리고 `stopPropagation()` 이 체인을 끊는다.
오늘 우리가 아무 생각 없이 쓰는 **이벤트 위임(event delegation)** —
`<ul>` 하나에 리스너를 달아 수백 개 `<li>` 의 클릭을 받는 그 기법 — 이
버블링 체인 위에서만 성립한다. 리스트 항목마다 리스너를 붙이던 시절이 before 다.

### 4-3. Netty ChannelPipeline

Netty 의 `ChannelPipeline` 은 자바독에서 자기 정체를 직접 밝힌다 —
**Intercepting Filter 패턴의 발전된 형태**라고.[^netty]
핸들러는 `ctx.fireChannelRead(msg)` 로 "다음 핸들러" 에게 넘기는데, 누군지는 모른다.

Netty 가 보여주는 건 **CoR 이 정적일 이유가 없다**는 것이다.
`ChannelPipeline` 은 스레드 안전해서 **언제든 핸들러를 넣고 뺄 수 있다.**[^netty]
프로토콜 협상이 끝난 뒤 압축 핸들러를 끼워 넣는 식의 일이 가능해진다.
GoF 가 말한 "동적으로 정해지는 집합" 의 가장 문자 그대로의 구현이다.

### 4-4. 그리고 나머지 전부

- **Express / Koa 미들웨어의 `next()`** — 서블릿 필터와 구조가 같다.
- **OkHttp `Interceptor.Chain`**, **Spring Security `FilterChainProxy`** — 이름부터 체인이다.
- **자바 예외 처리** — `throw` 한 쪽은 어느 `catch` 가 잡을지 모른다. 스택을 거슬러 올라가며
  처리자를 찾고, 아무도 안 잡으면 최상단으로 떨어진다. **언어 차원에 박힌 CoR** 이다.

패턴이 성공했다는 가장 확실한 증거는 이거다 — **이제 아무도 이걸 "패턴" 이라고 부르지 않는다.**
미들웨어라고 부르고, 필터라고 부르고, 파이프라인이라고 부른다.

---

## 5. after — 무엇이 새로 생겼나

여기를 안 쓰면 홍보글이 된다. CoR 은 문제를 **없앤 게 아니라 옮겼다.**

**(1) 수신이 보장되지 않는다.** GoF 자신이 결과(Consequences)에 명시한 약점이다 —
요청에 명시적 수신자가 없으므로 처리된다는 보장이 없고, 체인이 잘못 구성돼도 마찬가지다.[^gof]
Netty 문서는 이걸 아주 구체적으로 적는다: 인바운드 이벤트가 최상단 핸들러를 넘어가면
**조용히 버려지거나, 주의가 필요하면 로깅된다**고.[^netty]
`switch` 의 `default:` 는 컴파일러가 챙겨주지만, 체인의 끝은 아무도 안 챙긴다.

**(2) 순서가 코드에서 설정으로 옮겨간다.** 서블릿에서 필터 순서는 배포 서술자의
매핑 순서다.[^servlet23] 좋은 소식이자 나쁜 소식이다 — 재배포 없이 바꿀 수 있지만,
**컴파일러가 검증하지 않는 곳에 정확성이 걸린다.** 압축 필터를 암호화 필터 앞뒤 어디에 두느냐로
결과가 달라지는데, 그 지식은 XML 한 줄에 있다.

**(3) "누가 처리했는지" 를 런타임에만 알 수 있다.** 이게 암묵적 수신자의 대가다.
분기문이던 시절엔 코드를 읽으면 답이 나왔다. 지금은 로그를 켜야 안다.
스택 트레이스가 `doFilter` 로 열 겹 쌓이는 그 경험이 여기서 온다.
(Netty 가 인바운드/아웃바운드 핸들러를 건너뛰어 **스택 깊이를 줄이는 최적화**를 명시해 둔 것도
이 비용이 실재한다는 방증이다.[^netty])

**(4) 흐름을 끊는 실수가 조용하다.** `chain.doFilter()` 나 `next()` 를 안 부르면
요청은 그냥 멈춘다. 에러도 없고 예외도 없다. 응답이 안 올 뿐이다.

---

## 6. 내 코드에서도 같은 일이 일어났다

추상적으로 끝내면 아깝다. 내 저장소 [inter-asat](https://github.com/MyoungSoo7/inter-asat) 에
**이 전환이 통째로 담긴 커밋이 하나 있다.** `ecb5638` (2026-03-31, "논문 분석 및 적용").
청각 측정 세션의 신뢰도 등급(A/B/C/F)을 매기는 코드다.

**before** — 이른 반환(early return) if 더미:

```java
// ReliabilityGradeCalculator.java @ ecb5638^
if (reversalCount == 0)               return new GradeResult(F, "No reversals recorded");
if (reversalCount < MIN_REVERSALS_B)  return new GradeResult(C, "Insufficient reversals: " + reversalCount);
if (accuracyRate.compareTo(ACCURACY_B_LOW) < 0 || ...) return new GradeResult(C, "Accuracy out of range: " + accuracyRate);
if (anticipatoryRatio > MAX_ANTICIPATORY_C)            return new GradeResult(C, "Excessive anticipatory responses: ...");
if (floorCeilingReached)              return new GradeResult(C, "Floor/ceiling reached");
...
if (reversalCount >= MIN_REVERSALS_A && accuracyInA && lowAnticipatory && headphoneVerified)
                                      return new GradeResult(A, "All criteria met");
return new GradeResult(B, "Partial criteria met");
```

**after** — 규칙이 값이 됐다 (지금은 코틀린 `fun interface`):

```kotlin
fun interface GradeRule {
    fun evaluate(input: GradeInput): GradeResult?   // 못 정하면 null → 다음 규칙
}

private val CHAIN: List<GradeRule> = listOf(
    GradeRule { if (it.reversalCount == 0) GradeResult(F, "No reversals recorded") else null },
    GradeRule { if (it.reversalCount < MIN_REVERSALS_B) GradeResult(C, "...") else null },
    // ...
)

for (rule in CHAIN) { rule.evaluate(input)?.let { return it } }
return FALLBACK      // 체인 종단 = B등급
```

여기서 정직하게 세 가지를 짚는다.

**(1) 두 버전은 동작이 완전히 같다.** 사실 before 도 이미 체인이었다 —
이른 반환 `if` 하나하나가 "처리하거나 다음으로 넘긴다" 는 CoR 그 자체다.
바뀐 건 **체인이 제어 흐름(control flow)에서 데이터(list)로 이동한 것**뿐이다.

**(2) 그래서 얻은 건 확장성이 아니라 가시성이다.** 규칙이 값이 되면
개별로 테스트할 수 있고, 순서가 `listOf(...)` 한 곳에 한눈에 보인다.
이건 진짜 이득이다.

**(3) 그런데 코드 주석이 약속한 것의 절반은 아직 못 지켰다.**
주석은 "새 등급/기준 추가 시 Rule만 추가" 라고 적혀 있는데,
`CHAIN` 은 `companion object` 안의 `private val` 이다 — **하드코딩된 리스트다.**
규칙을 추가하려면 여전히 이 파일을 연다.
GoF 가 말한 "동적으로 정해지는 집합" 도, 서블릿의 배포 서술자도, Netty 의 런타임 조립도 아니다.
**CoR 의 모양은 갖췄지만 CoR 의 탈결합은 아직 없다.**

같은 저장소가 다른 곳(전략 레지스트리)에서는 스프링의 `List<T>` 주입으로
구현체를 런타임에 모은다. 그 배선을 여기 그대로 가져오면 주석의 나머지 절반이 채워진다.
`@Component` 로 각 규칙을 등록하고 `List<GradeRule>` 을 주입받으면,
규칙 추가가 **파일 추가**가 된다 — 그게 원래 이 패턴이 팔려는 물건이다.

**하나는 잘 했다.** 마지막 `FALLBACK = B등급` 이 명시적 종단이다.
GoF 가 경고한 "요청이 체인 끝으로 떨어질 수 있다" 에 대한 정확한 대응이다.
많은 CoR 구현이 이걸 빼먹고 `null` 을 반환한다.

---

## 7. 본질 한 줄

CoR 은 **분기를 없애는 패턴이 아니다. 분기의 소유권을 옮기는 패턴이다.**

- 없앤 것: "보내는 쪽이 받는 쪽 목록을 아는 것"
- 옮긴 곳: 체인을 **조립하는 쪽** — 배포 서술자, DI 컨테이너, 런타임 파이프라인
- 새로 생긴 비용: 수신 무보장, 순서가 설정으로, 처리자를 런타임에만 앎

그러니 판단 기준도 하나로 줄어든다.
**옮길 곳이 있는가?** 체인을 조립하는 주체가 사용하는 쪽과 분리돼 있다면 CoR 은 값을 한다.
조립도 사용도 같은 파일에서 한다면 — 내 `ReliabilityGradeCalculator` 처럼 —
얻는 건 가독성뿐이고, `if` 더미보다 확실히 낫지만 패턴이 약속한 것의 절반이다.

패턴을 쓸지 말지는 "이게 CoR 인가" 로 정해지지 않는다.
**"이 체인을 누가 조립하는가" 로 정해진다.**

---

## References

[^gof]: Gamma, E., Helm, R., Johnson, R., & Vlissides, J. (1994). *Design Patterns: Elements of Reusable Object-Oriented Software*, "Chain of Responsibility" (p. 223). Addison-Wesley. 의도·동기(문맥 도움말)·적용 조건·결과("수신이 보장되지 않는다")는 저자 4인 명의로 공개된 발췌본에서 확인: [InformIT — Design Patterns: Chain of Responsibility](https://www.informit.com/articles/article.aspx?p=1398601)

[^servlet23]: Sun Microsystems (2001). *Java Servlet Specification, Version 2.3, Final Release* (2001-09-17), SRV.6 "Filtering". 필터가 2.3 신규 기능이라는 서술, `doFilter` 위임/차단 동작, 배포 서술자 매핑 순서로 체인 순서가 정해진다는 규정, 필터 예시 목록. [스펙 PDF](https://courses.cs.duke.edu/fall06/cps116/docs/servlet-2_3-fcs-spec.pdf) · [JCP PFD 사본](https://jcp.org/aboutJava/communityprocess/first/jsr053/servlet23_PFD.pdf)

[^jsr53]: Java Community Process. *JSR 53: Java Servlet 2.3 and JavaServer Pages 1.2 Specifications* — Final Release 2001-09-25. [jcp.org/en/jsr/detail?id=53](https://jcp.org/en/jsr/detail?id=53)

[^filters]: Oracle. *The Essentials of Filters.* 서블릿 2.3 이전에 컨테이너별 독자 필터 메커니즘이 난립해 재사용성이 떨어졌다는 서술. [oracle.com/java/technologies/filters.html](https://www.oracle.com/java/technologies/filters.html)

[^dom2]: W3C (2000). *Document Object Model (DOM) Level 2 Events Specification*, W3C Recommendation 13 November 2000 (2020년 11월 3일 대체됨). §1.2.3 Event bubbling, `stopPropagation()`, `BUBBLING_PHASE`. [w3.org/TR/DOM-Level-2-Events/](https://www.w3.org/TR/DOM-Level-2-Events/)

[^netty]: Netty Project. *`ChannelPipeline` API Reference (4.1).* "Intercepting Filter 패턴의 발전된 형태" 자기 규정, 최상단을 넘어간 인바운드 이벤트의 조용한 폐기, 스택 깊이 단축을 위한 핸들러 평가 건너뛰기, 스레드 안전한 런타임 add/remove. [netty.io/4.1/api/io/netty/channel/ChannelPipeline.html](https://netty.io/4.1/api/io/netty/channel/ChannelPipeline.html)

**코드 출처:** [MyoungSoo7/inter-asat](https://github.com/MyoungSoo7/inter-asat) — before 는 `ecb5638^`, CoR 도입은 `ecb5638` (2026-03-31), 현재 코틀린 판은 `main` @ `e40f057`.
GoF 원문 인용은 저자 공개 발췌 범위 안에서 최소한으로 옮겼고, 본문 설명은 모두 필자의 요약이다.
