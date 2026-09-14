---
layout: post
title: "JBoss · WildFly · Tomcat — 셋을 나란히 놓고 비교할 수 없는 이유"
date: 2026-09-15 07:19:05 +0900
categories: [backend]
tags: [jboss, wildfly, tomcat, jakarta-ee, java, was, undertow, redhat]
---

"JBoss 랑 Tomcat 중에 뭐 쓰지?"는 실무에서 가장 자주 나오는 질문이면서, **질문의 형태가 이미 틀린** 대표 사례다. 세 이름이 같은 층위에 있지 않기 때문이다.

- **Tomcat** 은 제품이다. 서블릿 컨테이너.
- **WildFly** 는 제품이다. 완전한 Jakarta EE 애플리케이션 서버.
- **JBoss** 는 제품이 아니다. **브랜드**다. 그 브랜드 아래에 애플리케이션 서버도 있고, **Tomcat 배포판도 있다.**

즉 "JBoss vs Tomcat"은 "현대 vs 세단" 같은 문장이다. 이 글은 셋의 성능을 비교하는 글이 아니라, **무엇과 무엇을 비교해야 비교가 성립하는지**를 정리한다. 벤치마크 숫자는 한 줄도 없다 — 중립적으로 재현 가능한 헤드투헤드 자료를 찾지 못했고, 찾지 못한 숫자는 쓰지 않는다.

---

## 1. 층위부터 정리

| 이름 | 정체 | 만든 곳 | 라이선스 | 지원 |
| --- | --- | --- | --- | --- |
| **Apache Tomcat** | 서블릿 컨테이너 (Jakarta EE 기술의 **부분집합** 구현) | Apache Software Foundation | Apache 2.0 | 커뮤니티 |
| **WildFly** | Jakarta EE **Full Platform** 구현 애플리케이션 서버 | Red Hat (JBoss 커뮤니티) | Apache 2.0 (2023년 LGPL→ASL 전환) | 커뮤니티 |
| **JBoss EAP** | WildFly 기반 **상용 제품** | Red Hat | 소스 공개, 프로덕션은 구독 | Red Hat |
| **JBoss Web Server (JWS)** | **Apache Tomcat 배포판** + 부가 컴포넌트 | Red Hat | 구독 | Red Hat |
| ~~JBoss AS~~ | WildFly 의 옛 이름 (2013년 개명) | — | — | — |
| ~~JBoss Web~~ | JBoss AS ≤7 / EAP 6 에 내장됐던 웹 컨테이너 (Undertow 로 대체됨) | — | — | — |

Tomcat 공식 문서는 자신을 이렇게 정의한다 — "Apache Tomcat 은 **Jakarta EE 기술의 부분집합(a subset)** 에 대한 오픈소스 구현이다."[^whichversion] 이 한 문장이 Tomcat 과 WildFly 의 관계를 전부 설명한다. 경쟁 제품이 아니라 **포함 관계**다.

## 2. 무엇을 구현하나 — 스펙 범위가 전부다

### Tomcat 이 구현하는 것

Tomcat 은 서블릿 계열 5~6개 스펙만 구현한다.[^whichversion]

| Tomcat | Servlet | Pages(JSP) | EL | WebSocket | Authentication | 대응 플랫폼 | 필요 Java |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 11.0.x | 6.1 | 4.0 | 6.0 | 2.2 | 3.1 | **Jakarta EE 11** | 17+ |
| 10.1.x | 6.0 | 3.1 | 5.0 | 2.1 | 3.0 | **Jakarta EE 10** | 11+ |
| 9.0.x | 4.0 | 2.3 | 3.0 | 1.1 | 1.1 (JASPIC) | **Java EE 8** | 8+ |

여기 **없는 것**이 중요하다. EJB, JTA(분산 트랜잭션), CDI, JMS, JPA, Batch, Concurrency — 전부 없다. Tomcat 위에서 이것들을 쓰려면 애플리케이션이 직접 라이브러리를 들고 들어가야 한다. Spring 이 그 자리를 채운 역사적 이유가 여기 있다.

### WildFly 가 구현하는 것

WildFly 37 은 **Jakarta EE 10 Full Platform / Web Profile / Core Profile** 세 프로파일 모두의 호환 구현이고, Java SE 17 과 21 에서 인증됐다.[^wf37] TCK 결과는 `wildfly/certifications` 저장소에 공개돼 있다.[^cert]

Full Platform 이라는 건 위에서 "Tomcat 에 없다"고 나열한 것이 **전부 서버 쪽에 있다**는 뜻이다. 트랜잭션 매니저(Narayana), JMS 브로커(ActiveMQ Artemis), CDI(Weld), JPA(Hibernate), 커넥션 풀·JCA(IronJacamar), 클러스터링(Infinispan/JGroups)이 서버 구성요소로 들어 있고 관리 콘솔에서 설정한다.

## 3. 역설 — 좁은 쪽이 더 빨리 간다

여기가 이 비교에서 가장 흥미로운 지점이다.

- **Tomcat 11.0.x** 는 이미 **Jakarta EE 11 이 요구하는 버전**의 서블릿 계열 스펙(Servlet 6.1, JSP 4.0, EL 6.0, WebSocket 2.2, Authentication 3.1)을 구현한다.[^whichversion]
- **표준 WildFly** 는 37 시점에도 **EE 10** 이다. WildFly 문서는 "EE 11 은 GA 됐지만 WildFly Preview 는 38 릴리스 전에는 완전 지원하지 않고, **표준 WildFly 는 빨라야 39** 에 가서야 EE 11 을 지원한다"고 적고 있다.[^wfpreview]

구현 범위가 넓을수록 전체 플랫폼 TCK 를 통과시키는 데 시간이 더 든다. **"풀 스펙"은 공짜가 아니라 지연 비용을 동반한다.** 최신 서블릿 API 가 급한 팀에게는 이게 실질적인 판단 근거가 된다.

반대 방향도 사실이다 — EE 11 서블릿을 Tomcat 으로 먼저 받아봐야, EJB·JTA 가 필요해지는 순간 Tomcat 에는 답이 없다.

## 4. 웹 계층의 계보 — Tomcat 은 한때 JBoss 안에 있었다

이 부분이 "JBoss 와 Tomcat 은 다른 거냐"를 헷갈리게 만드는 진짜 원인이다.

**JBoss AS 7 / EAP 6 까지**, JBoss 애플리케이션 서버 내부의 웹 컨테이너는 **JBoss Web** 이었다. 설정은 `jboss-web.xml` 로 했고, 요청 처리 확장은 **Valve** 로 했다.[^eap64] Valve 는 Tomcat 의 아키텍처 개념이다.

**WildFly 8 (2014-02) 부터 이게 통째로 교체됐다.** WildFly 8 문서는 한 줄로 못박는다 — "Web subsystem was replaced in WildFly 8 with Undertow."[^wfly8] Red Hat 제품 문서도 같다 — Undertow 는 "JBoss EAP 7 에서 JBoss Web 을 대체한다."[^eapundertow]

마이그레이션 문서를 보면 교체의 폭이 보인다.[^migrate]

- 확장 모듈: `org.jboss.as.web` → `org.wildfly.extension.undertow`
- 설정 네임스페이스: `urn:jboss:domain:web:*` → `urn:jboss:domain:undertow:*`
- **Undertow 는 JBoss Web Valve 를 지원하지 않는다.** 일부 밸브는 Undertow Handler 로 자동 변환되지만, 자동 변환이 불가능한 항목은 마이그레이션 경고로 나열된다.
- CLI 에 `subsystem=web:migrate` 와 `:describe-migration` 오퍼레이션이 준비돼 있다 — 변환 불가 항목을 미리 뽑아볼 수 있다.

> 한 가지는 정직하게 남긴다. "JBoss Web 은 Tomcat 의 포크였다"는 서술이 널리 통용되지만, 나는 이 글을 쓰면서 그 계보를 1차 문서로 확인하지 못했다. 확인한 것은 **JBoss Web 이 Valve·`jboss-web.xml` 같은 Tomcat 계열 확장 개념을 그대로 갖고 있었고, Undertow 로 대체되면서 그 개념이 폐기됐다**는 사실까지다.

## 5. Red Hat 제품 지도 — 그리고 벤더 자신의 분기 기준

"JBoss"라는 이름표가 붙은 Red Hat 제품은 최소 둘이고, **계보가 다르다.**

| 제품 | 실체 | 핵심 구성 |
| --- | --- | --- |
| **JBoss EAP** | WildFly 기반 Jakarta EE 서버 | Undertow, Narayana, Artemis, Infinispan … |
| **JBoss Web Server (JWS)** | **Apache Tomcat 배포판** | Tomcat 10.1, Tomcat Native, Tomcat Vault, mod_cluster, APR, OpenSSL |

JWS 6.x 는 "Apache Tomcat 10.1 의 배포판"이라고 문서에 그대로 쓰여 있다.[^jws] 즉 **"JBoss 쓴다"는 말이 실제로는 "Tomcat 쓴다"인 경우가 있다.** 이름만 듣고 스택을 추정하면 안 된다.

그리고 Red Hat 자신이 두 제품의 분기 기준을 한 문장으로 제시한다:

> "Java 애플리케이션에 **클러스터링이나 세션 복제**가 필요하면 Red Hat JBoss Enterprise Application Platform (JBoss EAP) 를 사용하라."[^jws]

벤더가 직접 그은 선이라 인용 가치가 있다. 웹 계층만 필요하면 Tomcat 계열, 상태 복제·분산 트랜잭션이 필요하면 EAP/WildFly 계열이다.

EAP ↔ WildFly 버전 매핑도 공식 KB 에 있다 — EAP 8.1↔WildFly 35, 8.0↔28, 7.4↔23, 7.3↔18, 7.2↔14, 7.1↔11, 7.0↔10. EAP 는 별도 브랜치로 관리되므로 **정확히 1:1 대응하는 버전은 없다**는 단서가 같은 문서에 달려 있다.[^kb21906]

## 6. 선택 기준

결정에 실제로 영향을 주는 축은 넷이다.

**축 1 — 애플리케이션이 EE 스펙을 요구하는가**
EJB·JTA(2PC)·JMS·CDI·Batch 를 컨테이너에서 받아야 하면 Tomcat 은 후보에서 빠진다. Spring Boot + 라이브러리로 대체 가능한 범위라면 Tomcat 으로 충분하다.

**축 2 — 상태를 복제해야 하는가**
세션 클러스터링·분산 캐시가 요건이면 WildFly/EAP 쪽이다. Red Hat 이 위에서 그은 선과 같다.

**축 3 — 벤더 지원이 계약 요건인가**
필요하면 EAP(앱서버) 또는 JWS(Tomcat). 필요 없으면 WildFly 또는 Apache Tomcat. **오픈소스라서 못 쓰는 게 아니라, 지원 계약이 필요해서 제품을 사는 것**이다.

**축 4 — 최신 스펙 속도**
서블릿 계열 최신 스펙이 급하면 Tomcat 이 앞선다(§3).

## 7. 실무 함정 다섯

**① `javax.*` → `jakarta.*` 경계는 Tomcat 9/10 사이에 있다.**
Tomcat 9 는 Java EE 8(= `javax.*`), Tomcat 10.0 부터는 Jakarta EE 9 이후(= `jakarta.*`) 스펙을 구현한다.[^whichversion] 이 경계를 넘는 건 버전 업그레이드가 아니라 **소스 변경**이다. 서버를 바꾸는 작업과 네임스페이스를 바꾸는 작업을 같은 릴리스에 묶으면 원인 분리가 불가능해진다.

**② Java 버전 요구가 함께 올라간다.**
Tomcat 9→10.1 은 Java 8→11, 10.1→11.0 은 Java 11→17 이 최소선이다.[^whichversion] "톰캣만 올리면 된다"가 성립하지 않는다.

**③ "JBoss"라는 이름만으로 스택을 추정하지 마라.**
§5 대로 JWS 는 Tomcat 이다. 운영 인수인계 문서에 "JBoss"만 적혀 있으면 실제 바이너리를 확인해야 한다.

**④ JBoss Web → Undertow 이관은 설정 변환이 아니라 개념 변환이다.**
Valve 가 Handler 로 1:1 대응하지 않는다. `:describe-migration` 으로 **변환 불가 목록을 먼저 뽑는** 것이 순서다.[^migrate]

**⑤ Spring Boot 의 "내장 톰캣"은 배포 모델이 다른 물건이다.**
실행 가능한 jar 안의 Tomcat 과, WAR 을 올리는 독립 실행 Tomcat 은 운영 모델(배포 단위, 프로세스 수명, 설정 위치)이 다르다. "우리는 Tomcat 쓴다"는 말만으로는 어느 쪽인지 알 수 없다.

## 8. 이 글이 말하지 않은 것

- **성능 비교를 하지 않았다.** 세 제품의 재현 가능한 중립 헤드투헤드 벤치마크를 찾지 못했다. 벤더·커뮤니티 자체 측정은 있지만 조건이 공개·재현되지 않아 인용하지 않는다.
- **메모리 사용량·기동 시간 수치를 쓰지 않았다.** 같은 이유다. 구성(프로파일, Galleon 레이어, 배포 앱)에 따라 크게 달라지는 값을 단일 숫자로 적으면 오해를 만든다.
- **병행 운영 시의 주의점**(같은 호스트에 Tomcat 과 JBoss 를 함께 둘 때의 포트·JVM·로깅 충돌 등)은 이 글의 범위가 아니다.
- **JBoss Web 의 Tomcat 포크 여부**는 §4 에 적은 대로 미확인이다.

---

## 마무리

세 이름을 한 줄에 놓으면 이렇게 된다.

- **Tomcat** = 서블릿 컨테이너. Jakarta EE 의 **부분집합**. 좁고 빠르다.
- **WildFly** = Jakarta EE **Full Platform** 구현. 넓고, 넓은 만큼 새 스펙 채택이 늦다.
- **JBoss** = 브랜드. 그 아래 WildFly 기반 **EAP** 와 Tomcat 기반 **JWS** 가 **따로** 있다.

그래서 올바른 질문은 "JBoss 냐 Tomcat 이냐"가 아니라 **"컨테이너가 스펙을 얼마나 책임져야 하는가"** 다. 그 답이 정해지면 제품은 거의 자동으로 결정된다. 나머지는 지원 계약을 살 것인가의 문제다.

---

### References

- Apache Tomcat. *Which Version Do I Want?* <https://tomcat.apache.org/whichversion.html>
- Apache Software Foundation Wiki. *Tomcat Versions*. <https://cwiki.apache.org/confluence/display/TOMCAT/Tomcat+Versions>
- WildFly. *WildFly 37 is released!* (2025-08-04). <https://www.wildfly.org/news/2025/08/04/WildFly-37-is-released/>
- WildFly Documentation. *WildFly and WildFly Preview* (37). <https://docs.wildfly.org/37/WildFly_and_WildFly_Preview.html>
- wildfly/certifications. *WildFly 37.0.0.Final — Jakarta EE 10 Full Platform TCK 결과*. <https://github.com/wildfly/certifications/blob/EE10/WildFly_37.0.0.Final/jakarta-full-platform-jdk17.adoc>
- WildFly 8 Documentation. *Undertow subsystem configuration*. <https://docs.jboss.org/author/display/WFLY8/Undertow%20subsystem%20configuration.html>
- WildFly 10 Documentation. *How do I migrate my application from AS7 to WildFly*. <https://docs.jboss.org/author/display/WFLY10/How%20do%20I%20migrate%20my%20application%20from%20AS7%20to%20WildFly.html>
- WildFly. *WildFly 8 Final is released!* (2014-02-12). <https://www.wildfly.org/news/2014/02/12/WildFly-8-Final-is-released/>
- Red Hat. *JBoss EAP — Development Guide, Chapter 10. Undertow*. <https://docs.redhat.com/en/documentation/jboss_enterprise_application_platform_continuous_delivery/12/html/development_guide/undertow>
- Red Hat. *JBoss EAP 6.4 — jboss-web.xml Configuration Reference*. <https://docs.redhat.com/en/documentation/red_hat_jboss_enterprise_application_platform/6.4/html/security_guide/jboss-webxml_configuration_reference>
- Red Hat. *JBoss Web Server 6.1 Installation Guide*. <https://docs.redhat.com/en/documentation/red_hat_jboss_web_server/6.1/html-single/installation_guide/index>
- Red Hat Customer Portal. *Which version of JBoss EAP corresponds to which WildFly version?* (Solution 21906). <https://access.redhat.com/solutions/21906>
- wildfly/wildfly PR #17214 — *[WFLY-18534] Change the WildFly license to ASL 2.0*. <https://github.com/wildfly/wildfly/pull/17214>

[^whichversion]: Apache Tomcat 공식 "Which Version Do I Want?" 페이지. Tomcat 이 "Jakarta EE 기술의 부분집합 구현"이라는 자기 정의, 버전별 스펙 매핑표(Servlet/JSP/EL/WebSocket/Authentication), 필요 Java 버전, 그리고 각 계열이 대응하는 플랫폼(11.0.x=EE 11, 10.1.x=EE 10, 10.0.x=EE 9, 9.0.x=Java EE 8).
[^wf37]: WildFly 37 릴리스 공지. "Standard WildFly 37 is a compatible implementation of the EE 10 Platform as well as the Web Profile and the Core Profile… when running on Java SE 17 and Java SE 21."
[^cert]: wildfly/certifications 저장소의 WildFly 37.0.0.Final Full Platform TCK 결과 요약(2025-08-04, JDK 17).
[^wfpreview]: WildFly 37 문서 "WildFly and WildFly Preview". "EE 11 is now GA, but WildFly Preview won't fully support it before the 38 release, and standard WildFly won't support EE 11 before the WildFly 39 release, at earliest."
[^wfly8]: WildFly 8 문서 Undertow subsystem configuration. "Web subsystem was replaced in WildFly 8 with Undertow."
[^eapundertow]: Red Hat JBoss EAP Development Guide, Undertow 장. "It replaces JBoss Web in JBoss EAP 7."
[^migrate]: WildFly 10 문서 "How do I migrate my application from AS7 to WildFly". 모듈·네임스페이스 변경, Valve 미지원과 Handler 대응, `subsystem=web:migrate` 및 `:describe-migration` 오퍼레이션, 자동 변환 불가 항목의 경고 목록.
[^eap64]: Red Hat JBoss EAP 6.4 문서. `jboss-web.xml` 이 "JBoss Web 의 부가 기능에 대한 설정 옵션"을 담는 EAP 전용 배포 서술자라는 설명.
[^jws]: Red Hat JBoss Web Server 6.1 Installation Guide. JWS 가 "Apache Tomcat 서블릿 컨테이너의 완전 지원 구현"이며 JWS 6.x 가 Apache Tomcat 10.1 을 포함한다는 서술, 구성요소 목록(Tomcat Native, Tomcat Vault, mod_cluster, APR, OpenSSL), 그리고 "클러스터링·세션 복제가 필요하면 JBoss EAP 를 쓰라"는 분기 지침.
[^kb21906]: Red Hat KB Solution 21906. EAP ↔ WildFly/JBoss AS 버전 매핑표와 "정확히 대응하는 버전은 없다(별도 브랜치로 관리)"는 단서.
