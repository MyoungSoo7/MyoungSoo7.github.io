---
layout: post
title: "JBoss 와 톰캣을 환경에 따라 같이 쓸 때 신경 쓸 것 — 클래스로더 방향이 반대다"
date: 2026-09-15 07:21:25 +0900
categories: [java, infra]
tags: [jboss, wildfly, tomcat, jakarta-ee, classloader, jndi, spring-boot, servlet]
---

흔한 배치다. **개발은 스프링 부트 임베디드 톰캣, 스테이징은 독립 톰캣, 운영은 JBoss EAP 나 WildFly.** 혹은 레거시가 JBoss 이고 신규 서비스만 톰캣으로 나가는 경우. 어느 쪽이든 전제는 같다 — *둘 다 서블릿 컨테이너니까 같은 WAR 가 양쪽에서 똑같이 돌겠지.*

그 전제가 깨지는 지점들을 정리한다. 두 서버가 공유하는 계약은 `jakarta.servlet` API 하나뿐이고, **그 바깥은 전부 서버마다 다르다.** 순서는 취향이 아니라 "개발 톰캣에서 초록불인 WAR 를 JBoss 에 올렸을 때 먼저 터지는 순서"다.

출처 원칙: 동작 규칙·기본값 같은 사실 주장은 Apache Tomcat·WildFly·Red Hat·Spring 공식 문서로 확인한 것만 적는다. 문서로 확인되지 않은 것은 추론이라고 라벨을 붙이고, 성능 우열 같은 논쟁적 주장은 애초에 하지 않는다 — 두 서버의 중립적인 헤드투헤드 벤치마크를 찾지 못했다.

---

## 0. 이름부터 — JBoss 는 하나가 아니다

- **JBoss** 는 브랜드다. 지금 제품 이름으로는 **WildFly**(커뮤니티 애플리케이션 서버)와 **Red Hat JBoss EAP**(상용 구독 제품)로 갈린다.
- **웹 계층은 더 이상 톰캣 계열이 아니다.** 옛날 JBoss AS 의 웹 서브시스템(JBoss Web)은 톰캣 포크였지만, WildFly 는 이를 **Undertow** 로 교체했다. 그래서 AS 7 → WildFly 마이그레이션 문서는 `web` 서브시스템 설정을 `undertow` 로 옮기는 작업을 따로 다룬다.[^wf-undertow]

이게 첫 번째 실무적 함의다. **톰캣의 `Valve` 는 JBoss 쪽에 그대로 옮겨지지 않는다.** Undertow 에는 밸브 개념이 없고 핸들러로 다시 써야 한다. Red Hat 마이그레이션 가이드는 `migrate` 오퍼레이션이 커스텀 밸브 등 일부 설정을 옮기지 못하며 그런 항목은 수동으로 이관해야 한다고 명시한다.[^eap-valve] 자동 변환 도구가 조용히 빠뜨리는 쪽이라 특히 위험하다.

(세 서버의 정체성·스펙 범위 비교 자체는 이 글의 주제가 아니다. 여기서는 **한 조직이 둘을 동시에 쓸 때 무엇이 깨지는가**만 본다.)

---

## 1. 클래스로더 우선순위가 정반대다 — 이 글의 중심축

나머지 대부분이 여기서 파생된다.

**톰캣**의 웹앱 클래스로더는 자바 표준 위임 모델을 **의도적으로 뒤집는다**(parent-last). 공식 문서가 밝히는 탐색 순서는:

```
Bootstrap (JVM) → WEB-INF/classes → WEB-INF/lib → System → Common
```

다만 예외가 있다. JRE 기본 클래스와 **톰캣이 구현한 스펙 API(Servlet/JSP/EL/WebSocket)** 는 웹앱이 덮어쓸 수 없다.[^tomcat-cl] 결과적으로 톰캣에서는 **WAR 안에 넣은 라이브러리가 대체로 이긴다.**

**WildFly / JBoss EAP** 는 모듈형 클래스로딩이다. 배포물도 모듈이고, 명시적으로 선언하지 않은 서버 모듈에는 접근할 수 없다. 그리고 우선순위가 이렇게 잡힌다:

```
암묵적(implicit) 의존성  →  명시적(explicit) 의존성
   →  로컬 리소스(WEB-INF/classes, WEB-INF/lib)  →  배포 간(inter-deployment) 의존성
```

즉 **서버가 자동으로 붙여준 모듈이 가장 높고, WAR 안의 JAR 이 그 아래다.**[^eap-cl][^wf-cl]

두 규칙을 겹치면 결론이 나온다. **같은 WAR 가, 경합하는 라이브러리를 두 서버에서 서로 반대쪽으로 해석한다.** 톰캣에서는 내가 번들한 버전, JBoss 에서는 서버가 제공하는 버전.

증상은 보통 이렇게 나온다:

- `NoSuchMethodError` — 컴파일할 땐 있던 메서드가 런타임 JAR 에는 없다
- `AbstractMethodError` / `LinkageError` — 인터페이스와 구현이 서로 다른 버전에서 왔다
- `ClassCastException: X cannot be cast to X` — 이름이 같은 클래스가 다른 클래스로더에서 두 번 로드됐다

**대응.** WildFly/EAP 쪽의 제어면은 `WEB-INF/jboss-deployment-structure.xml` 이다. 이 파일로 서버가 자동으로 붙인 의존성을 **배제**하거나(`<exclusions>`), 모듈을 명시적으로 추가하거나, 로컬 리소스를 뒤로 미룰 수 있다.[^eap-jds] 예:

```xml
<jboss-deployment-structure>
  <deployment>
    <exclusions>
      <!-- 서버가 붙여주는 모듈 대신 WAR 안의 것을 쓰겠다 -->
      <module name="org.apache.log4j"/>
    </exclusions>
  </deployment>
</jboss-deployment-structure>
```

이 파일은 JBoss 계열만 해석한다. **톰캣은 이 파일을 모르고 무시하므로, WAR 에 그냥 넣어둬도 톰캣 배포는 영향을 받지 않는다.** 한 산출물로 양쪽을 커버해야만 하는 상황에서 쓸 수 있는 몇 안 되는 카드다.

---

## 2. 서버가 주는 API 범위가 달라서, WAR 내용물이 달라야 한다

톰캣은 서블릿 컨테이너다. JPA 구현체도, CDI 도, JTA 트랜잭션 매니저도 없다 — 필요하면 앱이 번들해야 한다. WildFly/EAP 는 Jakarta EE 서버라 그걸 서버가 준다.

여기서 §1 과 맞물려 **모순**이 생긴다:

- 톰캣: 번들해야 **돈다**
- JBoss: 같은 걸 번들하면 서버 모듈과 경합하고, 우선순위가 서버 쪽이라 **내가 넣은 게 진다** (또는 둘 다 로드돼 `ClassCastException`)

"하나의 WAR 로 어디든" 을 목표로 잡으면 이 모순을 `jboss-deployment-structure.xml` 의 배제 규칙으로 한 줄씩 메우는 싸움이 된다. **더 나은 기본값은 산출물을 환경별로 나누는 것이다** — 메이븐/그레이들 프로파일로 같은 소스에서 `provided` 범위를 달리한 두 WAR 를 만든다. 의존성 그래프의 차이가 **빌드 시점에** 드러나기 때문이다. 배제 규칙은 그 차이를 런타임까지 미룬다.

---

## 3. `javax` → `jakarta` — 환경별 지뢰 1순위

버전 조합을 잘못 맞추면 위의 모든 논의가 무의미해진다. 앱이 아예 안 뜬다.

| 서버 | 네임스페이스 |
| --- | --- |
| Tomcat 9.x 이하 | `javax.*` |
| Tomcat 10.0 이상 | `jakarta.*` (Jakarta EE 9+) |
| JBoss EAP 7.x | `javax.*` (Jakarta EE 8) |
| JBoss EAP 8.0 | `jakarta.*` (Jakarta EE 10) |

톰캣 10 마이그레이션 가이드는 "Tomcat 10 onwards implements the specifications of Jakarta EE 9" 라고 밝히고, **Tomcat 9 이하용 웹앱은 그대로 배포되지 않으므로 변환이 필요하다**고 명시한다.[^tomcat10] Red Hat EAP 8.0 마이그레이션 가이드도 EAP 8.0 이 Jakarta EE 10 이며 애플리케이션의 `javax.` 네임스페이스를 `jakarta.` 로 바꿔야 한다고 적는다.[^eap8-jakarta]

**함정은 바꿔야 할 대상이 import 문만이 아니라는 것이다.** 세 종류가 있다:

1. **소스의 import** — IDE 가 잡아준다. 제일 쉽다.
2. **`javax.` 로 시작하는 프로퍼티/설정 *이름*** — 문자열이라 컴파일러가 안 잡는다. (예: 퍼시스턴스 설정 키)
3. **`META-INF/services/javax.*` 리소스 *파일명*** — `ServiceLoader` 는 파일을 못 찾으면 예외를 던지지 않고 **아무것도 없다고 판단한다.** 그래서 이 경우는 조용히 기능만 사라진다. 세 가지 중 가장 늦게 발견된다.

변환 도구는 있다. 톰캣 10 은 `legacyAppBase`(기본 `webapps-javaee`)에 둔 `javax` 웹앱을 자동 변환해주고,[^tomcat10] Eclipse Transformer 같은 바이트코드 변환기도 쓸 수 있으며, Red Hat 은 EAP 8 이행용 Migration Toolkit 을 제공한다.[^eap8-mta] 다만 **이건 대응책이지 설계가 아니다.** 환경마다 네임스페이스가 다른 상태를 영구히 유지하겠다는 뜻이라면, 그때부터는 소스 자체가 두 벌이 된다.

---

## 4. JNDI 이름은 포터블하지 않다

데이터소스를 서버에서 받아 쓰는 구조라면 이름 규칙부터 다르다.

- **톰캣**: `context.xml` 또는 `server.xml` 의 `<Resource>` 로 정의하고 앱은 `java:comp/env/jdbc/이름` 으로 조회한다.[^tomcat-jndi]
- **JBoss EAP**: 데이터소스의 JNDI 이름이 **`java:/` 또는 `java:jboss/` 로 시작해야 한다**고 문서가 못 박는다.[^eap-ds]

그래서 코드에 `java:/jdbc/MyDS` 를 하드코딩하면 톰캣에서 안 뜨고, `java:comp/env/jdbc/MyDS` 를 EAP 데이터소스 이름으로 쓰면 등록이 거부된다.

**포터블한 자리는 하나뿐이다** — 애플리케이션은 `java:comp/env/...` 만 바라보게 하고, `resource-ref` 를 환경별 디스크립터가 실제 서버 이름으로 매핑한다. 코드에서 서버 고유 이름이 사라지는 게 핵심이다. (스프링 부트라면 애초에 JNDI 를 걷어내고 `spring.datasource.*` 를 외부 설정으로 주입하는 쪽이 환경 차를 더 줄인다.)

---

## 5. 세션 복제 — 스펙은 한 줄, 나머지는 전부 서버 고유

양쪽 다 `web.xml` 의 `<distributable/>` 로 "이 앱은 분산 가능" 을 선언한다. **공통은 거기까지다.**

- **톰캣**: `<Cluster>` 설정(DeltaManager/BackupManager)과 로드밸런서 어피니티를 위한 엔진 속성 `jvmRoute` 를 쓴다.[^tomcat-cluster]
- **WildFly**: `distributable-web` 서브시스템이 세션 관리 정책을 정의하고, 백엔드는 Infinispan(내장) 또는 원격 Infinispan(HotRod)이다. 라우팅은 세션 ID 뒤에 라우트를 덧붙이는 방식이고, 복제 단위를 **SESSION / ATTRIBUTE** granularity 로 고를 수 있다.[^wf-dweb]

실무적으로 신경 쓸 것:

- **ATTRIBUTE granularity 에 대응하는 톰캣 설정이 없다.** WildFly 에서 속성 단위 복제를 전제로 튜닝한 세션 크기 가정이 톰캣에서는 성립하지 않는다.
- **로드밸런서 설정이 서버마다 다르다.** 어피니티를 세션 ID 라우트로 거는 WildFly 와 `jvmRoute` 를 쓰는 톰캣은 LB 쪽 구성이 다르다. 한쪽 LB 설정을 그대로 복사하면 스티키가 안 걸리고, 그 증상은 "가끔 로그아웃됨" 으로만 보인다 — 로그에는 아무것도 안 남는다.
- **한 도메인에서 톰캣 앱과 JBoss 앱을 같이 서비스한다면 세션 쿠키 스코프를 확인해야 한다.** 둘 다 기본 쿠키 이름이 `JSESSIONID` 이므로, 쿠키 path 를 `/` 로 넓히면 서로의 세션 쿠키를 덮어쓸 수 있다. *(이 문단은 특정 문서의 인용이 아니라 쿠키 규칙과 두 서버의 기본 쿠키 이름에서 나오는 추론이다. 실제로 겹치는지는 브라우저 개발자도구에서 `Set-Cookie` 의 path 를 직접 확인하는 게 맞다.)*

---

## 6. 로깅 — WildFly 는 WAR 안을 들여다본다

톰캣은 웹앱 안의 로깅 설정 파일에 대해 특별히 하는 일이 없다. 앱이 자기 로깅 라이브러리를 초기화할 뿐이다.

WildFly 는 다르다. 로깅 서브시스템에 **기본값이 `true` 인 속성이 둘** 있다:

- `add-logging-api-dependencies` — 배포물에 로깅 API 의존성을 자동으로 추가한다(기본 `true`)
- `use-deployment-logging-config` — **배포물 안의 로깅 설정 파일을 사용한다**(기본 `true`)[^wf-logging]

그래서 WAR 안에 `logback.xml` / `log4j2.xml` 같은 파일을 넣어두면, 톰캣에서는 그냥 앱 설정이지만 **WildFly 에서는 그 배포물에 대한 로그 매니저 설정으로 채택된다.** "운영에서만 로그가 안 나온다" 또는 "운영에서만 로그 레벨이 다르다" 의 흔한 원인이 여기다.

**권고.** 배포물 안에는 로깅 설정 파일을 넣지 않고, WildFly 쪽은 서버에 정의한 **로깅 프로파일**을 `MANIFEST.MF` 의 `Logging-Profile` 엔트리로 지정한다. 서버 설정이라 재배포 없이 런타임에 레벨을 바꿀 수 있다는 게 실질적인 이득이다.[^wf-logging]

---

## 7. 한 호스트에 둘 다 올릴 때 — 포트

둘 다 기본 HTTP 포트가 8080 이다. 한 머신에 같이 올리면 당연히 충돌한다.

- **톰캣**: `server.xml` 의 `<Connector port="...">` 를 커넥터마다 고친다.
- **WildFly/EAP**: 포트는 **소켓 바인딩 그룹**에 정의돼 있고, `jboss.socket.binding.port-offset` 하나로 **그룹 전체를 옮긴다**:[^eap-ports]

$$
port_{actual} = port_{binding} + offset
$$

```bash
# HTTP 8080→8180, 관리 9990→10090 ... 그룹 전체가 100씩 밀린다
./standalone.sh -Djboss.socket.binding.port-offset=100
```

이게 장점이자 함정이다. **오프셋은 HTTP 만 미는 게 아니라 관리 포트(9990)와 트랜잭션 포트까지 전부 민다.** 그래서 오프셋을 준 뒤에 관리 CLI 가 기본 포트로 안 붙고, 모니터링·헬스체크가 조용히 옛 포트를 긁는다. 포트를 옮겼으면 **관리·모니터링 쪽 주소를 같이 옮겼는지** 반드시 확인한다.

**AJP 도 같이 본다.** 옛날 톰캣은 AJP 커넥터를 모든 인터페이스에 열어둔 채로 배포됐고, 이것이 CVE-2020-1938(Ghostcat)로 이어졌다. NVD 는 9.0.0.M1–9.0.30, 8.5.0–8.5.50, 7.0.0–7.0.99 가 영향 범위이며 기본 활성 상태였다고 기록한다.[^ghostcat] 이후 버전은 AJP 의 기본 구성이 달라졌으므로, **레거시 JBoss/톰캣 시절의 AJP 설정을 새 서버에 그대로 복사하지 않는다.** 복사가 되면 그게 더 나쁜 신호다.

---

## 8. 스프링 부트를 양쪽에 올린다면

부트 앱을 JBoss 에 WAR 로 올리는 절차는 공식 문서에 3단계로 정리돼 있다:[^boot-war]

1. `SpringBootServletInitializer` 를 상속하고 `configure` 를 오버라이드한다
2. 패키징을 `war` 로 바꾼다
3. 내장 서블릿 컨테이너 의존성을 `provided` 로 표시한다

여기서 자주 오해되는 사실 하나 — **WAR 로 바꿔도 `java -jar` 로 계속 실행된다.** 부트 플러그인이 `provided` 의존성을 `WEB-INF/lib-provided` 에 넣어 실행 가능한 WAR 을 만들기 때문이다.[^boot-war] "WAR 로 바꾸면 로컬 실행이 깨진다" 는 걱정 때문에 임베디드 톰캣용 JAR 과 JBoss 용 WAR 을 완전히 다른 빌드로 갈라놓는 경우가 있는데, 그럴 필요는 없다.

다만 **WAR 로 가는 순간 §1·§2 가 전부 적용된다.** 부트가 끌고 오는 의존성 중 서버가 이미 제공하는 것들(Jakarta API, 로깅, 검증 등)이 JBoss 쪽 모듈과 만난다. 그 지점부터는 `jboss-deployment-structure.xml` 또는 빌드 프로파일의 영역이다.

---

## 마무리 — 규칙 네 개

**① "같은 WAR 하나로 어디서나" 를 목표로 두지 않는다.** 목표는 같은 *소스*다. 산출물은 환경별로 다른 게 정상이고, 그걸 빌드가 만들게 한다.

**② 환경 차이는 코드가 아니라 빌드와 디스크립터에 둔다.** 코드에 `if (서버가 JBoss면)` 이 들어가는 순간, 그 분기는 두 환경 중 한쪽에서만 실행되므로 영원히 절반만 테스트된다.

**③ 로컬 톰캣 초록불은 JBoss 초록불의 증거가 아니다.** 우선순위가 구조적으로 반대라서 다른 결과가 나오는 게 정상이다. 운영이 JBoss 라면 **JBoss 위에서 도는 검증 단계가 파이프라인에 있어야 한다.** 이건 "있으면 좋은 것" 이 아니라, §1 때문에 **없으면 검증이 성립하지 않는 것**이다.

**④ 서버가 제공하는 것 목록을 적어두고 빌드에서 강제한다.** JPA 구현체, 로깅, 검증, JSON 바인딩 — 이 목록이 문서가 아니라 `provided` 선언으로 존재하면, 새 의존성이 들어올 때 사람이 기억하지 않아도 빌드가 알려준다.

이 서버들을 계속 쓸 것인가, 비용은 어떻게 되는가는 [지난 글]({% post_url 2026-09-13-oracle-weblogic-jboss-necessity-and-cost %})에서 따로 다뤘다. 이 글은 **이미 둘을 같이 쓰기로 한 상태**에서의 이야기다.

---

## References

[^tomcat-cl]: Apache Tomcat 공식 문서 — [Class Loader How-To](https://tomcat.apache.org/tomcat-10.1-doc/class-loader-howto.html)
[^tomcat10]: Apache Tomcat 공식 문서 — [Tomcat Migration Guide: Tomcat 10.0.x](https://tomcat.apache.org/migration-10.html)
[^tomcat-jndi]: Apache Tomcat 공식 문서 — [JNDI Resources How-To](https://tomcat.apache.org/tomcat-10.1-doc/jndi-resources-howto.html)
[^tomcat-cluster]: Apache Tomcat 공식 문서 — [Clustering/Session Replication How-To](https://tomcat.apache.org/tomcat-10.1-doc/cluster-howto.html)
[^wf-cl]: WildFly 공식 문서 — [Developer Guide: Class Loading in WildFly](https://docs.wildfly.org/36/Developer_Guide.html#Class_Loading_in_WildFly)
[^wf-undertow]: WildFly 공식 문서 — [How do I migrate my application from AS7 to WildFly](https://docs.wildfly.org/36/How_do_I_migrate_my_application_from_AS7_to_WildFly.html) (JBoss Web → Undertow)
[^wf-logging]: WildFly 공식 문서 — [Admin Guide: Logging Configuration](https://docs.wildfly.org/36/Admin_Guide.html#Logging) (`add-logging-api-dependencies`, `use-deployment-logging-config`, `Logging-Profile`)
[^wf-dweb]: WildFly 공식 문서 — [High Availability Guide: Distributable Web Applications](https://docs.wildfly.org/36/High_Availability_Guide.html)
[^eap-cl]: Red Hat 공식 문서 — [JBoss EAP Development Guide: Class Loading and Modules](https://docs.redhat.com/en/documentation/red_hat_jboss_enterprise_application_platform/8.0/html/development_guide/class_loading_and_modules)
[^eap-jds]: Red Hat 공식 문서 — [JBoss EAP Development Guide: `jboss-deployment-structure.xml`](https://docs.redhat.com/en/documentation/red_hat_jboss_enterprise_application_platform/8.0/html/development_guide/class_loading_and_modules)
[^eap-ds]: Red Hat 공식 문서 — [JBoss EAP Configuration Guide: Datasource Management](https://docs.redhat.com/en/documentation/red_hat_jboss_enterprise_application_platform/8.0/html/configuration_guide/datasource_management) (JNDI 이름은 `java:/` 또는 `java:jboss/` 로 시작)
[^eap-ports]: Red Hat 공식 문서 — [JBoss EAP Configuration Guide: Network and Port Configuration](https://docs.redhat.com/en/documentation/red_hat_jboss_enterprise_application_platform/8.0/html/configuration_guide/network_and_port_configuration) (socket binding group, port offset)
[^eap-valve]: Red Hat 공식 문서 — [JBoss EAP 7 Migration Guide: Migrate Web Subsystem Configuration](https://docs.redhat.com/en/documentation/red_hat_jboss_enterprise_application_platform/7.4/html/migration_guide/) (`migrate` 오퍼레이션이 옮기지 못하는 설정)
[^eap8-jakarta]: Red Hat 공식 문서 — [JBoss EAP 8.0 Migration Guide: Application Migration Changes](https://docs.redhat.com/en/documentation/red_hat_jboss_enterprise_application_platform/8.0/html/migration_guide/) (Jakarta EE 10, `javax.` → `jakarta.`)
[^eap8-mta]: Red Hat 공식 문서 — [Migration Toolkit for Applications](https://docs.redhat.com/en/documentation/migration_toolkit_for_applications)
[^boot-war]: Spring 공식 문서 — [Spring Boot Reference: Traditional Deployment](https://docs.spring.io/spring-boot/how-to/deployment/traditional-deployment.html)
[^ghostcat]: NVD — [CVE-2020-1938](https://nvd.nist.gov/vuln/detail/CVE-2020-1938) (Apache Tomcat AJP, "Ghostcat")
