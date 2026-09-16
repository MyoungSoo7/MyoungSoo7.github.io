---
layout: post
title: "메이븐 프로필 — 켜지는 규칙을 모르면 조용히 안 켜진다"
date: 2026-09-16 20:48:00 +0900
categories: [Engineering, Build]
tags: [Maven, pom.xml, 프로필, settings.xml, 빌드, 이식성]
---

메이븐 프로필에서 사람들이 실제로 잃는 시간은 "무엇을 쓸 수 있나" 가 아니라 **"왜 안 켜졌나"** 에 있다. `-P prod` 를 쳤는데 기본 프로필이 사라지고, 부모 POM 에 정의한 프로필이 자식에서 안 뜨고, `${appserver.home}` 이 경로가 아니라 글자 그대로 박혀 나간다.

이 세 가지는 전부 **버그가 아니라 문서에 적힌 동작**이다. 이 글은 메이븐 공식 프로필 가이드를 기준으로 **활성화 규칙과 그 규칙이 만드는 함정**을 정리한다.[^mvnprofile]

> 어제 쓴 [프로파일은 늘리고 산출물은 늘리지 않는다]({% post_url 2026-09-15-spring-profiles-vs-build-artifacts %}) 는 **"메이븐 프로필로 환경 설정을 굽지 마라"** 쪽을 다뤘다. 이 글은 반대쪽이다 — **그럼 정당한 용도는 무엇이고, 그때 규칙은 어떻게 도는가.** 두 글은 겹치지 않는다.

---

## 0. 먼저 정의 — 프로필은 POM 을 바꾼다

가이드의 정의 문장이 이 글 전체의 전제다.[^mvnprofile]

> 프로필은 POM 에서 쓸 수 있는 요소의 부분집합(과 추가 섹션 하나)으로 지정되며 여러 방식으로 트리거된다. **프로필은 빌드 시점에 POM 을 수정하고**, 대상 환경 집합에 대해 동등하지만 다른 파라미터를 주기 위해 **상보적인 집합으로 쓰도록** 만들어졌다. 그래서 프로필은 **팀 구성원마다 빌드 결과가 달라지는 상황을 쉽게 만들 수 있다.**

마지막 문장을 공식 문서가 스스로 적어 뒀다는 게 중요하다. 프로필은 편의 기능이 아니라 **이식성을 담보로 잡는 기능**이다. 그래서 메이븐은 "어디에 정의했느냐" 로 권한을 다르게 준다. 이게 §4 다.

---

## 1. 프로필은 세 곳에 산다

정의 위치는 셋뿐이다.[^mvnprofile]

| 범위 | 위치 |
| --- | --- |
| 프로젝트별 | `pom.xml` |
| 사용자별 | `${user.home}/.m2/settings.xml` |
| 전역 | `${maven.home}/conf/settings.xml` |

두 `settings.xml` 이 다 있으면 **병합되고, 사용자 쪽이 우선**한다.[^mvnsettings] 그리고 `settings.xml` 안에서 쓸 수 있는 보간은 시스템 프로퍼티와 `${env.HOME}` 류뿐이다 — **`settings.xml` 의 프로필 안에 정의한 프로퍼티는 보간에 쓸 수 없다.**[^mvnsettings]

---

## 2. 가장 많이 당하는 것 — 프로필은 상속되지 않는다

멀티모듈에서 부모 POM 에 프로필을 정의해 두고 자식 모듈에서 켜지길 기대하는 건 아주 흔한 오해다. 가이드는 정반대로 적는다.[^mvnprofile]

> **프로필은 자식 POM 에 상속되지 않는다.** 대신 Maven Model Builder 가 아주 이른 시점에 프로필을 해석하고, **활성화된 프로필의 *효과* 만**(예: 프로필 안에 정의된 플러그인) 상속된다. 암묵적 프로필 활성화는 **그 프로필을 감싼 컨테이너에만** 영향을 주며, **같은 id 를 가졌더라도 다른 프로필에는 전혀 영향을 주지 않는다.**

두 가지가 갈린다.

- **프로필 자체**는 내려가지 않는다. 자식 POM 은 부모의 프로필 목록을 물려받지 않는다.
- **활성화된 프로필이 만들어 낸 결과**(플러그인·의존성·프로퍼티)는 일반 POM 상속 규칙대로 내려간다.

그래서 "부모에서 `env=prod` 로 켜지는 프로필을 만들어 두면 모듈마다 알아서 켜지겠지" 는 성립하지 않는다. 부모 POM 컨텍스트에서 평가돼서 그 **효과**만 내려갈 뿐이다. 자식에서 조건을 따로 평가받고 싶으면 그 프로필을 자식에 다시 써야 한다.

---

## 3. 활성화 — 조건은 AND 로만 묶인다

### 3.1 명시적 활성화

```bash
mvn -P profile-1,profile-2 package
```

`-P` 로 켠 프로필은 **활성화 설정이나 `settings.xml` 의 `<activeProfiles>` 로 켜진 것에 *더해서*** 활성화된다.[^mvnprofile]

**메이븐 4 에서 동작이 하나 바뀌었다.** 해석할 수 없는 프로필을 켜거나 끄려고 하면 **거부한다.** 선택적으로 만들려면 id 앞에 `?` 를 붙인다.[^mvnprofile]

```bash
mvn -P profile-1,profile-2,?profile-3 package
```

### 3.2 `activeByDefault` — 이게 1번 함정이다

```xml
<profile>
  <id>dev</id>
  <activation><activeByDefault>true</activeByDefault></activation>
</profile>
```

"기본값" 이라는 이름 때문에 "아무것도 안 하면 켜진다" 로 읽히는데, 문서의 조건은 훨씬 좁다.[^mvnprofile]

> 이 플래그는 **다른 프로필이 명령줄·`settings.xml`·다른 활성화 조건으로 활성화되지 않은 경우에만** 평가된다. 그렇지 않으면 아무 효과가 없다.
>
> 기본 활성 프로필들은 **같은 POM 의 다른 프로필이 명령줄이나 활성화 설정으로 켜지는 순간 전부 자동으로 비활성화된다.**

즉 이렇게 된다.

```bash
mvn package              # dev 켜짐
mvn -P release package   # release 켜짐 + dev 는 조용히 꺼짐
```

`-P release` 는 `release` 를 **추가**하는 게 아니라 `dev` 를 **밀어낸다.** 기본 프로필에 공통 설정(인코딩·리소스 경로 등)을 넣어 뒀다면 릴리스 빌드에서만 그게 통째로 빠진다. 에러는 안 난다.

**대책은 `activeByDefault` 를 공통 설정 그릇으로 쓰지 않는 것**이다. 항상 필요한 건 프로필 밖 `<build>` 에 두고, `activeByDefault` 는 "다른 걸 고르지 않았을 때의 *선택지*" 로만 쓴다.

### 3.3 JDK — 접두사 매칭이지 숫자 비교가 아니다

```xml
<activation><jdk>1.4</jdk></activation>
```

이건 **문자열 접두사** 매칭이다. `1.4.0_08`·`1.4.2_07` 에는 걸리지만 **`1.8` 이나 `11` 에는 안 걸린다.**[^mvnprofile] 범위를 쓰려면 `[` 나 `(` 로 시작해야 한다.

```xml
<activation><jdk>[1.3,1.6)</jdk></activation>
```

여기 문서가 달아 둔 경고가 실무에서 진짜로 문다.[^mvnprofile]

> `,1.5]` 같은 상한은 **대부분의 1.5 릴리스를 포함하지 않는다.** 그 릴리스들은 위 범위가 고려하지 않는 `_05` 같은 추가 "패치" 릴리스를 갖기 때문이다.

그리고 `[`·`(` 로 시작하지 않으면 **벤더 접두사**로 해석된다. `zulu64` 로 쓰면 Zulu JDK 에서 켜지고, `!` 를 앞에 붙이면 부정이다.[^mvnprofile]

### 3.4 OS·프로퍼티·파일

**OS** 는 `name`·`family`·`arch`·`version` 을 `os.name` 등 자바 시스템 프로퍼티와 대조한다(대소문자 무시). 각 값에 `!` 로 부정할 수 있고, **주어진 OS 조건은 전부 맞아야** 한다. **메이븐 3.9.7 부터** `version` 에 `regex:` 접두사를 붙여 정규식 매칭을 쓸 수 있다. 실제 값은 `mvn --version` 이 찍어 준다.[^mvnprofile]

**프로퍼티**는 네 가지 꼴이 있고 헷갈리기 쉬우니 표로 본다.[^mvnprofile]

| 설정 | 켜지는 조건 |
| --- | --- |
| `<name>debug</name>` | `debug` 가 **아무 값으로든** 정의됨 |
| `<name>!debug</name>` | `debug` 가 **아예 정의되지 않음** |
| `<name>debug</name><value>true</value>` | 값 없이 정의됐거나 값이 `true` |
| `<name>debug</name><value>!true</value>` | 정의 안 됐거나 값이 `true` 가 아님 |

환경변수는 `env.FOO` 꼴로 접근하고, **윈도우에서는 이름이 전부 대문자로 정규화**된다.[^mvnprofile] 그리고 **메이븐 3.9.0 부터** `packaging` 이라는 이름으로 POM 의 packaging 값을 조건에 쓸 수 있다 — 여러 프로젝트가 공유하는 부모 POM 에서만 쓸모가 있다.[^mvnprofile]

**파일**은 `<exists>` / `<missing>` 인데, 여기 제약이 따로 있다.[^mvnprofile]

> 이 요소의 보간은 **`${project.basedir}`, 시스템 프로퍼티, 요청 프로퍼티로 제한된다.** (…) POM 자체에 정의된 프로퍼티와 값은 보간에 쓸 수 없다. 예를 들어 위 활성자는 `${project.build.directory}` 를 쓸 수 없고 경로 `target` 을 하드코딩해야 한다.

`${project.build.directory}` 를 썼는데 조건이 영영 안 맞는다면 이것이다.

### 3.5 조건은 AND 뿐이고, OR 은 아예 없다

여러 조건을 한 프로필에 넣으면 **전부 맞아야** 켜진다. 그리고 결정적으로 — **같은 타입을 한 프로필에 두 번 쓰는 건 지원되지 않는다.**[^mvnprofile]

$$\text{active} \;\iff\; \bigwedge_{k=1}^{n} c_k \qquad\text{단,}\quad \forall i \neq j:\; \mathrm{type}(c_i) \neq \mathrm{type}(c_j)$$

`property` 조건 두 개를 넣어 "`env=stage` 또는 `env=prod`" 를 만들 수 없다는 뜻이다(MNG-5909, MNG-3328). OR 이 필요하면 **프로필을 두 개로 쪼개고 같은 내용을 양쪽에 두는 것**밖에 방법이 없다. 프로필 개수가 늘어나는 구조적 이유가 여기 있다.

### 3.6 끄기 — 문법에 함정이 있다

```bash
mvn -P '!profile-1,!profile-2' package   # ! 는 셸에서 이스케이프/따옴표 필요
mvn -P=-profile-1,-profile-2 package     # CLI-309 때문에 이 꼴이 권장됨
```

`!` 는 bash·zsh 에서 특수문자라 따옴표가 필요하고, `-` 로 시작하는 옵션 값에는 알려진 버그(CLI-309)가 있어 **문서가 `-P=-이름` 꼴을 권장**한다.[^mvnprofile] 이걸로 `activeByDefault` 프로필이나 활성화 조건에 걸린 프로필을 강제로 끌 수 있다.

---

## 4. 어디에 썼느냐가 무엇을 고칠 수 있는지를 정한다

이게 메이븐 프로필 설계의 핵심이고, 대부분의 "왜 안 먹지" 가 여기서 나온다.

**`settings.xml`·`profiles.xml` 의 프로필** 은 딱 세 가지만 건드릴 수 있다.[^mvnprofile]

- `<repositories>`
- `<pluginRepositories>`
- `<properties>`

이유도 명시돼 있다 — 외부 파일 프로필은 엄밀한 의미에서 이식 가능하지 않기 때문에, **빌드 결과를 바꿀 가능성이 높아 보이는 것은 전부 POM 안의 인라인 프로필로 제한**한다.[^mvnprofile]

**POM 안의 프로필** 은 훨씬 넓다 — `dependencies`, `dependencyManagement`, `modules`, `repositories`, `pluginRepositories`, `properties`, `reporting`, `dependencyManagement`, `distributionManagement` 등과 **`<build>` 의 일부 하위 요소**(`defaultGoal`, `resources`, `testResources`, `finalName`, `plugins`, `pluginManagement` 등)다. 그리고 경계가 딱딱하다.[^mvnprofile]

> `<build>` 의 **다른 요소를 수정하려는 프로필은 유효하지 않고 "malformed POM" 에러로 빌드를 실패시킨다.**

왜 이렇게 막았는지도 문서가 설명한다. **effective POM 이 원격 저장소에 배포되면 누구든 그걸 가져다 빌드하는데, 런타임 수정분은 배포되지 않는다.** 그래서 `settings.xml` 에서 의존성을 바꿀 수 있게 하면 남이 그 POM 으로 빌드할 수 없게 된다.[^mvnprofile]

---

## 5. 여러 개가 켜졌을 때 — 뒤가 이긴다

활성 프로필의 요소는 같은 이름의 전역 요소를 **덮어쓰고**, 컬렉션이면 **확장**한다. 그리고 순서 규칙이 명확하다.[^mvnprofile]

> 같은 POM 이나 외부 파일에서 여러 프로필이 활성이면, **나중에 정의된 것이 먼저 정의된 것보다 우선한다** — **프로필 id 나 활성화 순서와 무관하게.**

`profile-1`·`profile-2` 가 각각 저장소를 하나씩 추가하면 결과는 이렇게 된다.[^mvnprofile]

```
profile-2-repo, profile-1-repo, global-repo
```

**`-P profile-2,profile-1` 로 순서를 바꿔 쳐도 결과는 같다.** 우선순위를 정하는 건 명령줄 순서가 아니라 **POM 안에 적힌 순서**다. 여기서 헛다리를 짚기 쉽다.

---

## 6. 문서가 직접 이름 붙인 두 함정

가이드에는 "Profile Pitfalls" 라는 절이 따로 있고, 함정을 둘로 나눠 이름까지 붙여 뒀다.[^mvnprofile]

### 6.1 External Properties — 이식성이 깨진다

`pom.xml` 의 플러그인이 `${appserver.home}` 을 쓰고, 그 값은 **내 `settings.xml` 프로필에만** 있는 경우다.

```xml
<!-- pom.xml -->
<configuration><appserverHome>${appserver.home}</appserverHome></configuration>
```

```xml
<!-- ~/.m2/settings.xml — 나한테만 있음 -->
<profile>
  <id>appserverConfig</id>
  <properties><appserver.home>/path/to/appserver</appserver.home></properties>
</profile>
```

내 통합테스트는 통과한다. 그리고 문서가 동료의 빌드를 이렇게 묘사한다.[^mvnprofile]

> 동료가 integration-test 까지 빌드하려 하면 그의 빌드는 **화려하게 실패한다.** 플러그인 설정 파라미터를 해석할 수 없다고 하거나, **더 나쁘게는 그 파라미터 값이 문자 그대로 `${appserver.home}` 인 채로** — 경고라도 해 준다면 — 유효하지 않다고 한다.
>
> 축하한다, 당신의 프로젝트는 이제 이식 불가능하다.

"더 나쁘게는" 쪽이 진짜다. **에러가 아니라 문자열이 그대로 흘러간다.** 빌드는 성공하고 배포된 아티팩트만 틀린다.

### 6.2 Incomplete Specification of a Natural Profile Set — 집합에 구멍이 난다

`env=dev` 와 `env=dev-2` 프로필만 만들어 두고 `env=production` 은 안 만든 경우다. `mvn -Denv=production integration-test` 를 치면 어떤 프로필도 안 걸리고, 그래서 `${appserver.home}` 이 **보간되지 않은 채로** 남는다.[^mvnprofile]

> 우리는 프로필을 쓸 때 프로덕션 환경의 경우를 고려하지 않았다. `production`·`test`·어쩌면 `local` 까지가 (…) **자연스러운 대상 환경 집합**을 이룬다. 이 자연 집합을 불완전하게 명세했다는 건 **유효한 대상 환경을 개발 환경 하나로 사실상 제한해 버렸다**는 뜻이다. 동료들 — 그리고 아마 상사 — 은 여기서 유머를 느끼지 못할 것이다.

규칙으로 적으면 이렇다. 대상 환경 집합 $E$ 에 대해 프로필 집합 $P$ 는 이걸 만족해야 한다.

$$\bigcup_{p \in P} \mathrm{trigger}(p) \;\supseteq\; E$$

**포함 관계가 깨지는 순간 실패는 "프로필 없음" 이 아니라 "보간 안 된 문자열" 로 나타난다.** 이게 이 함정이 오래 숨는 이유다. 빈 문자열이 아니라 `${...}` 라는 그럴듯한 값이 들어가서, 로그를 봐도 눈에 안 띈다.

---

## 7. 그래서 뭘로 확인하나

추측하지 말고 물어보면 된다. maven-help-plugin 에 goal 이 준비돼 있다.[^mvnhelp]

```bash
mvn help:active-profiles     # 지금 활성인 프로필
mvn help:all-profiles        # 이 프로젝트에서 쓸 수 있는 프로필 전부
mvn help:effective-pom       # 활성 프로필이 반영된 최종 POM
mvn help:effective-settings  # 전역+사용자 settings 병합 결과
mvn help:evaluate            # 표현식 값을 직접 물어보기
```

문서가 적는 각 goal 의 역할은 이렇다.[^mvnhelp]

> `help:active-profiles` 는 현재 빌드에서 활성인 프로필을 나열한다. (…) `help:effective-pom` 은 **활성 프로필이 반영된** 현재 빌드의 effective POM 을 XML 로 표시한다. **`verbose` 면 각 XML 요소에 그 줄의 출처를 설명하는 주석이 붙는다.**

마지막 문장이 디버깅에서 제일 쓸모 있다. `mvn help:effective-pom -Dverbose=true` 를 치면 **어떤 값이 어느 파일에서 왔는지**가 주석으로 찍힌다. "이 설정 누가 넣었지" 를 추적하는 가장 빠른 길이다.

§6.1 의 증상(`${appserver.home}` 이 문자 그대로 남음)은 `help:evaluate` 로 즉시 잡힌다.

---

## 8. 이름 짓기 — 문서의 권고가 실용적이다

가이드가 제안하는 규칙은 단순하지만 효과가 있다.[^mvnprofile]

> 프로필 id 가 의도를 암시하게 하라. 한 가지 좋은 방법은 **공통 시스템 프로퍼티 트리거를 프로필 이름의 일부로 쓰는 것**이다. `env` 프로퍼티로 트리거되는 프로필이라면 `env-dev`·`env-test`·`env-prod` 같은 이름이 된다. (…) **프로필 id 의 "-" 를 "=" 로 바꾸면 그대로 올바른 명령줄 옵션이 된다.**

즉 `env-test` 라는 이름을 보면 활성화 방법이 바로 나온다.

```bash
mvn -Denv=test package
```

이름이 곧 사용법이 된다. §6.2 의 "자연 집합에 구멍" 도 이 규칙을 쓰면 눈에 보인다 — `env-dev`·`env-test` 만 있고 `env-prod` 가 없으면 목록에서 바로 티가 난다.

---

## 9. 정리 — 정당한 용도와 아닌 용도

프로필이 **맞는** 쓰임은 빌드 자체가 정말 달라져야 하는 경우다.

- JDK·OS별로 다른 의존성이나 플러그인이 필요할 때 (`<jdk>`, `<os>` 활성화)
- 통합테스트처럼 평소엔 끄고 CI 에서만 켜는 실행 (`-Prun-its`)
- 릴리스 전용 플러그인(서명·소스/자바독 첨부) 묶기
- 사내 저장소 주소처럼 **빌드 결과를 바꾸지 않는** 것 → `settings.xml` 쪽 프로필이 딱 이 용도로 허용 범위가 좁혀져 있다

**아닌** 쓰임은 어제 글에서 다룬 그것이다 — **환경별 설정값을 프로필로 산출물에 굽는 것.** 그러면 환경 수만큼 아티팩트가 생기고, 테스트한 것과 배포한 것이 달라진다.

규칙만 다시 압축하면 이렇다.

1. 프로필은 **상속되지 않는다.** 효과만 내려간다.
2. `activeByDefault` 는 **다른 프로필이 켜지면 꺼진다.**
3. 조건은 **AND 뿐**이고 같은 타입은 두 번 못 쓴다. OR 은 없다.
4. `<jdk>1.4</jdk>` 는 **접두사** 매칭이다. `1.8` 에 안 걸린다.
5. 우선순위는 **POM 에 적힌 순서**지 `-P` 순서가 아니다.
6. `settings.xml` 프로필은 **repositories·pluginRepositories·properties 만** 건드린다.
7. 자연 집합에 구멍이 나면 **에러가 아니라 `${...}` 문자열**이 나간다.
8. 확신이 안 서면 **`mvn help:effective-pom -Dverbose=true`.**

---

## 10. 근거의 한계

- **전부 메이븐 공식 문서 기준이다.** 인용은 Apache Maven 프로필 가이드·설정 레퍼런스·maven-help-plugin 문서에서 왔고, 버전 번호를 단정한 곳은 **문서에 그 번호가 적혀 있는 경우뿐**이다(3.9.0 packaging, 3.9.7 `regex:`, 메이븐 4 의 `?` 접두사).
- **메이븐 4 는 `?` 접두사와 미해결 프로필 거부만 다뤘다.** 메이븐 4 가 프로필 모델 전반에서 또 무엇을 바꿨는지는 확인하지 않았다. 4 로 올릴 계획이라면 별도로 릴리스 노트를 봐야 한다.
- **`profiles.xml` 은 언급만 했다.** 가이드가 외부 파일 프로필을 설명하며 함께 들지만 오래된 메커니즘이고, 실제 동작을 확인하지 않았다.
- **성능·빌드 시간 얘기는 없다.** 프로필이 빌드를 느리게/빠르게 한다는 주장은 하지 않았고, 재현 가능한 측정치도 찾지 않았다.
- **§9 의 "맞는 쓰임 / 아닌 쓰임" 구분은 내 판단이다.** 문서는 이식성 경고와 함정 두 개를 명시하지만, 그걸 용도 목록으로 정리한 건 내 해석이다. 특히 "통합테스트 토글" 같은 항목은 가이드의 `run-its` 예시에서 가져왔지만 "권장 용도" 라고 문서가 적은 건 아니다.
- **실측하지 않았다.** 이 글은 문서 정리이고, 각 활성화 규칙을 내 환경에서 하나씩 재현해 본 결과가 아니다. 특히 JDK 범위 상한(`,1.5]`)의 동작은 문서의 경고를 옮긴 것이다.

---

## References

[^mvnprofile]: Apache Maven 공식 문서 — [Introduction to Build Profiles](https://maven.apache.org/guides/introduction/introduction-to-profiles.html)
[^mvnsettings]: Apache Maven 공식 문서 — [Settings Reference](https://maven.apache.org/settings.html)
[^mvnhelp]: Apache Maven 공식 문서 — [Apache Maven Help Plugin](https://maven.apache.org/plugins/maven-help-plugin/)
