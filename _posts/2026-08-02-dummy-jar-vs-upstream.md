---
layout: post
title: "더미 JAR를 만들 뻔했다 — 없는 의존성 앞에서 upstream을 먼저 본 이유"
date: 2026-08-02 06:10:00 +0900
categories: [Engineering, Java, Build]
tags: [Maven, Java Agent, Lombok, Git, Debugging]
---

빌드를 부탁받았다. 요청은 이랬다.

> pom.xml에 윈도우 경로(`C:/...`)가 있어서 에러가 나니까, 이걸 리눅스 환경에 맞게 수정한 뒤 mvn으로 빌드해 줘.

한 줄 고치면 될 줄 알았다. 실제로는 껍질이 네 겹이었고, **그중 세 겹은 진짜 문제가 아니었다.** 그리고 마지막 한 겹 앞에서, 하마터면 가장 나쁜 방법을 쓸 뻔했다.

대상은 [MyoungSoo7/babeagent](https://github.com/MyoungSoo7/babeagent) — [gromit25/AppAgent](https://github.com/gromit25/AppAgent) 의 포크다. JDBC·서블릿·소켓 호출을 가로채 로그를 남기는 **Java 에이전트**다.

---

## 껍질 벗기기

**1겹. 윈도우 경로.** 진짜였다. 하지만 고치는 방향이 중요했다.

```xml
<deploy.target.dir>C:/apps/AppAgent</deploy.target.dir>
```

이걸 `/opt/appagent` 같은 프로젝트 **밖** 경로로 바꾸고 싶은 유혹이 있는데, 하면 안 된다. 같은 pom 안에서 [maven-clean-plugin](https://maven.apache.org/plugins/maven-clean-plugin/) 이 이 경로를 이렇게 지운다.

```xml
<fileset>
  <directory>${deploy.target.dir}</directory>
  <includes><include>**/*</include></includes>
</fileset>
```

`mvn clean` 한 번에 그 디렉터리가 통째로 날아간다는 뜻이다. 윈도우에서 `C:/apps/AppAgent` 는 이 프로젝트 전용 배포 폴더였겠지만, 유닉스에서 아무 경로나 넣으면 그건 **빌드 도구에게 rm -rf 를 쥐여 주는 것**이다. 그래서 프로젝트 안으로 넣었다.

```xml
<deploy.target.dir>${project.basedir}/target/deploy</deploy.target.dir>
```

**2겹. `mvn: command not found`.** Maven 설치. 문제가 아니었다.

**3겹. 컴파일 에러 391개.** `cannot find symbol: method getValue()`, `method builder()` … 소스가 통째로 망가진 것처럼 보인다. 아니었다. Lombok 1.18.28 이 **JDK 25에서 조용히 아무 일도 안 한 것**이다. 애노테이션 프로세싱이 실패해도 에러를 내지 않고 그냥 코드를 생성하지 않는다. 그러면 생성됐어야 할 getter/builder 가 전부 "없는 심볼"이 된다. JDK 25 지원은 Lombok 1.18.40 부터다([Lombok Changelog](https://projectlombok.org/changelog)). JDK 21에서는 오히려 `NoSuchFieldError` 로 요란하게 죽고, **JDK 17에서는 정상 동작한다.** (이 함정은 [앞 글](/2026/08/02/silent-failures-six-of-them/)에서 자세히 다뤘다.)

**4겹. 이미 손상된 pom.xml.** 내가 손대기 전에, 누군가 이 문제를 풀려다 `com.redeye:TextGen` 의존성 블록을 지우면서 **인접한 블록과 합쳐 놨다.** 결과는 `com.redeye:jakarta.servlet-api:6.1.0` — 세상에 존재하지 않는 좌표다.

그리고 여기서 **진짜 블로커**가 드러났다.

```java
import com.redeye.textgen.TextGen;   // ← 어디에도 없는 비공개 라이브러리
```

`TextGen-0.1.jar`. Maven Central 에 없고, 레포에도 없고, 로컬 `.m2` 에도 없다. 로그 템플릿을 컴파일하는 데만 쓰인다.

---

## 세 가지 선택지, 그리고 함정

1. 업스트림에 TextGen 없는 구현이 있는지 본다
2. 진짜 jar 를 구해 온다
3. **더미 jar 를 만든다** — 같은 패키지·같은 시그니처의 빈 클래스를 넣고 컴파일만 통과시킨다

작업 디렉터리에는 이미 3번을 향한 흔적이 있었다. 커밋되지 않은 `Dockerfile.build` 파일이었다.

```dockerfile
# 더미 JAR를 동일한 경로로 주입
COPY ./dummy_lib_target/TextGen-0.1.jar /tmp/dummy_lib/TextGen-0.1.jar
RUN mvn clean package -DskipTests
```

이게 왜 최악인지는 명확하다. **더미 jar 를 넣으면 빌드는 초록불이 된다.** `BUILD SUCCESS`, jar 생성 완료, 보고 끝. 그런데 실제로 에이전트를 붙이는 순간 `TextGen.compile()` 이 빈 껍데기를 반환하고, **로그 템플릿 기능만 조용히 죽는다.** 에이전트는 뜨고, 앱도 돌고, 아무도 에러를 안 본다. 로그가 이상해질 뿐이다.

이건 어제 글에서 정리한 침묵 장애의 교과서적 형태다. **초록불이 "동작한다"는 뜻이 아니라 "컴파일러가 불평하지 않았다"는 뜻일 때가 있다.**

---

## 실제로 한 것: `git merge-base` 한 줄

3번을 밀어내려면 1번을 확인해야 했다. 포크 프로젝트에서 이건 명령 두 개면 끝난다.

```console
$ git merge-base --is-ancestor HEAD upstream/main && echo "fast-forward 가능"
fast-forward 가능
$ git rev-list --count HEAD..upstream/main
90
```

[`git merge-base --is-ancestor`](https://git-scm.com/docs/git-merge-base) 는 "HEAD 가 upstream 의 조상인가"를 답한다. **YES 라는 건 로컬 고유 커밋이 하나도 없다는 뜻이다.** 이 포크는 갈라진 게 아니라 그냥 **90커밋 뒤처져 있었다.**

그리고 업스트림은 이미 TextGen 을 버린 뒤였다. 대체품은 2025년 11월에 새로 들어온 50여 줄짜리 `Logfmt` 클래스 — 외부 의존성 없이 `key=value` 로그 포맷([logfmt](https://brandur.org/logfmt), Brandur Leach 의 정리가 사실상 표준 설명이다)을 만든다.

```java
// 사라진 것
logTemplate = TextGen.compile(Config.LOG_TEMPLATE.getValue());
log = logTemplate.gen(valueMap);

// 대체된 것
log.append(Logfmt.toString(valueMap));
```

키 이름도 짧아졌다 (`curTime`→`ts`, `elapsedTime`→`elapsed`, `txId`→`tx`). 로그 라인 끝의 ASCII RS(Record Separator) 문자도 빠졌다. 즉 **비공개 라이브러리 의존을 없애면서 로그 포맷을 표준 logfmt 로 정리한 리팩터링**이었고, 그건 이미 8개월 전에 끝나 있었다.

그래서 체리픽도, 더미도 필요 없었다.

```console
$ git merge --ff-only upstream/main
$ grep -rn "TextGen" --include='*.java' --include='*.xml' .
(없음)
```

내가 손상된 pom.xml 을 고치느라 들인 시간도 필요 없었다. 업스트림 pom 에는 애초에 그 의존성도, `<Class-Path>lib/TextGen-0.1.jar</Class-Path>` 도 없었다. **fast-forward 한 번이 내 수정 전부를 대체했다.**

업스트림 대비 남은 로컬 수정은 결국 **한 줄**이다 — 그 윈도우 경로.

```console
$ git diff --stat
 pom.xml | 7 ++++++-
```

---

## 초록불 확인: JDK 17로 빌드

```console
$ export JAVA_HOME=$(/usr/libexec/java_home -v 17.0.2)
$ mvn clean package && mvn install -DskipTests
BUILD SUCCESS
```

산출물과 매니페스트:

```
target/deploy/babeagent.jar        96,133 bytes
target/deploy/lib/                 asm, oshi-core, jna, jna-platform, slf4j-api
```

```
Premain-Class: com.redeye.appagent.AppAgent
Can-Redefine-Classes: true
Can-Retransform-Classes: true
Class-Path: lib/asm-9.7.1.jar lib/oshi-core-6.8.2.jar lib/jna-5.17.0.jar ...
```

`TextGen-0.1.jar` 가 Class-Path 에서 사라졌다. Build-Jdk 는 17.0.2.

---

## 그런데 초록불은 여기서도 거짓말을 할 뻔했다

여기서 끝냈다면 "빌드 성공, 여기 jar 입니다"로 보고했을 것이다. 그런데 이 산출물은 **Java 에이전트**다. 에이전트가 정말 붙는지는 붙여 봐야 안다.

```console
$ java -javaagent:target/deploy/babeagent.jar Hello
Caused by: java.lang.NoClassDefFoundError: jakarta/servlet/Servlet
	at com.redeye.appagent.appwriter.MethodPair.load(MethodPair.java:57)
	at com.redeye.appagent.AppAgent.premain(AppAgent.java:38)
*** java.lang.instrument ASSERTION FAILED ***: "result" ... agent load/premain call failed
FATAL ERROR in native method: processing of -javaagent failed
```

JVM 이 아예 죽었다. 이게 [`java.lang.instrument` 규약](https://docs.oracle.com/en/java/javase/17/docs/api/java.instrument/java/lang/instrument/package-summary.html)이다 — `premain` 이 예외를 던지면 JVM 은 **애플리케이션을 시작하지 않고 abort 한다.** 에이전트 버그는 조용히 넘어가지 않는다.

그런데 이건 버그가 아니라 **설계였다.** 에이전트는 서블릿·JDBC 호출을 감싸므로 `jakarta.servlet.Servlet` 을 참조할 수밖에 없고, 그 의존성은 `provided` 스코프다 — [Maven 의 `provided` 는 "컴파일엔 필요하지만 런타임엔 호스트가 제공한다"](https://maven.apache.org/guides/introduction/introduction-to-dependency-mechanism.html)는 뜻이다. 즉 이 에이전트의 정당한 부착 대상은 **서블릿 컨테이너 위에서 도는 앱**이지, Hello World 가 아니다.

호스트 조건을 맞춰 주자 통과했다.

```console
$ java -cp ".:$(find ~/.m2 -name 'jakarta.servlet-api-*.jar' | head -1)" \
       -javaagent:target/deploy/babeagent.jar Hello
APP RAN OK
```

`premain` 이 끝까지 돌고 애플리케이션이 실행됐다. 이제 "빌드됐다"가 아니라 **"붙는다"**고 말할 수 있다.

---

## 남은 것 세 가지

- **포크에서 의존성이 막히면 upstream 을 먼저 봐라.** `git merge-base --is-ancestor` 한 줄이면 "갈라진 것"과 "뒤처진 것"을 구분할 수 있다. 뒤처진 거였다면, 당신이 풀려는 문제는 이미 남이 풀었을 가능성이 높다. 나는 이걸 **껍질 세 개를 벗긴 뒤에야** 확인했다. 순서를 바꿨어야 했다.
- **더미 스텁은 "빌드를 통과시키는 방법"이지 "빌드를 고치는 방법"이 아니다.** 정말 써야 한다면 최소한 그게 죽인 기능을 문서에 적고, 런타임에 큰 소리로 실패하게 만들어야 한다. 조용한 no-op 이 가장 나쁘다.
- **산출물의 종류에 맞는 스모크 테스트가 있어야 한다.** 라이브러리는 import 해 보고, CLI 는 `--help` 를 때려 보고, **Java 에이전트는 실제로 `-javaagent` 로 붙여 봐야 한다.** `BUILD SUCCESS` 는 컴파일러의 의견일 뿐이다.

그리고 빌드 요청을 받았을 때 원래 들은 문제("윈도우 경로")가 진짜 문제였던 비율은, 이번 경우 **네 겹 중 한 겹**이었다.

---

## References

- Apache Maven — [Introduction to the Dependency Mechanism (dependency scopes)](https://maven.apache.org/guides/introduction/introduction-to-dependency-mechanism.html)
- Apache Maven — [Maven Clean Plugin](https://maven.apache.org/plugins/maven-clean-plugin/)
- Oracle — [`java.lang.instrument` package summary (JDK 17)](https://docs.oracle.com/en/java/javase/17/docs/api/java.instrument/java/lang/instrument/package-summary.html) — `premain` 실패 시 JVM abort 규약
- Git — [`git merge-base`](https://git-scm.com/docs/git-merge-base)
- Project Lombok — [Changelog](https://projectlombok.org/changelog) — JDK 25 지원 도입 버전
- Brandur Leach — [logfmt](https://brandur.org/logfmt) — logfmt 포맷의 사실상 표준 정리 (개인 저술이며 공식 사양은 아님)
- 대상 저장소: [MyoungSoo7/babeagent](https://github.com/MyoungSoo7/babeagent) · 업스트림 [gromit25/AppAgent](https://github.com/gromit25/AppAgent) (둘 다 public)

> **검증 범위:** 위 명령 출력과 스택 트레이스는 이번 작업에서 실제로 재현한 것이다. 다만 스모크 테스트는 "에이전트가 `premain` 을 통과하고 앱이 실행된다"까지만 확인했다. 실제 서블릿/JDBC 호출이 올바르게 계측되는지는 **검증하지 않았다** — 그건 서블릿 컨테이너와 DB 가 붙은 환경이 필요하다. 로그 포맷이 `TextGen` 시절과 달라졌다는 점(키 이름 축약, RS 종료문자 제거)도, 이 로그를 파싱하는 소비자가 있다면 확인이 필요하다.
