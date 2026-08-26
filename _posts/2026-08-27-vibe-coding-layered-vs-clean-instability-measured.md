---
layout: post
title: "바이브코딩에서 레이어드 vs 클린 — '안정도'를 숫자로 재고 레포 4개를 돌려봤다"
date: 2026-08-27 07:24:57 +0900
categories: [engineering]
tags: [architecture, clean-architecture, layered-architecture, vibe-coding, archunit, metrics, maintainability]
---

"레이어드보다 클린이 유지보수가 낫다"는 말은 너무 자주 들려서 이제 아무 정보도 없다. 낫다는 건 뭘 기준으로 낫다는 건가. 재본 사람은 별로 없다.

그래서 **재봤다.** 내 레포 4개의 프로덕션 소스 1,861개 파일에 마틴의 패키지 지표를 돌리고, 도메인이 프레임워크를 몇 번 import 하는지 셌다.

결론부터: **숫자는 나왔는데, 그 숫자가 내가 알고 싶었던 걸 재지 못한다.** 가장 완벽한 안정도 점수(I = 0.00)를 받은 레포가 도메인에서 프레임워크를 160번 import 하고 있었다. 지표가 틀린 게 아니라, 지표가 그쪽을 아예 안 본다.

---

## 1. "안정도"와 "유지보수성"을 먼저 정의한다

둘 다 아무 뜻이나 될 수 있는 단어라 정의부터 고정한다.

**안정도(stability)** 는 마틴이 1994년 논문에서 셀 수 있게 만들어놨다.[^1]

- **Ca (Afferent Couplings)** — 이 패키지 *바깥에서* 이 패키지 안의 클래스에 의존하는 클래스 수
- **Ce (Efferent Couplings)** — 이 패키지 *안에서* 바깥 클래스에 의존하는 클래스 수
- **I (Instability) = Ce ÷ (Ca + Ce)**, 범위 [0, 1]

원문 정의는 이렇다: "I=0 indicates a maximally stable category. I=1 indicates a maximally instable category."

직관은 단순하다. **남들이 나에게 의존하는데 나는 아무에게도 의존하지 않으면 나는 못 바뀐다 → 안정.** 반대로 내가 사방에 의존하고 나를 쓰는 사람은 없으면 나는 언제든 바뀐다 → 불안정. 여기서 "안정"은 좋다는 뜻이 아니라 **변경 압력을 덜 받는다**는 서술이다.

여기에 붙는 원칙이 **SDP(Stable Dependencies Principle)** 다. 논문 표현 그대로: "A package should only depend upon packages that are more stable than it is." 의존 화살표는 불안정한 쪽에서 안정한 쪽으로만 가야 한다.

**유지보수성(maintainability)** 은 ISO/IEC 25010:2023 이 §3.7 에서 5개 하위특성으로 쪼개놨다 — modularity(3.7.1), reusability(3.7.2), analysability(3.7.3), modifiability(3.7.4), testability(3.7.5).[^2] 이 글에서 I 로 재는 건 그중 **modularity 한 조각**이다. 표준 자체도 modifiability 항목에 "Modularity and analysability can influence modifiability" 라고 적어놨다 — **영향을 준다는 것이지 같다는 게 아니다.** 이 구분은 뒤에서 실제로 문제가 된다.

## 2. 두 구조의 실질적 차이는 화살표 방향 하나다

레이어드는 위에서 아래로 한 방향이다. Controller → Service → Repository → DB. 도메인 규칙이 사는 Service 층이 그 아래 Repository 층에 의존한다. 즉 **비즈니스 규칙이 영속화 기술에 의존한다.**

클린 아키텍처는 그 화살표 하나를 뒤집는다. 마틴의 Dependency Rule 은 "source code dependencies must point only inward" 한 줄이다.[^3] Repository 는 인터페이스로 안쪽(도메인)에 두고, 구현체를 바깥에 두고 DIP 로 뒤집는다.

나머지 차이는 대부분 명칭과 디렉터리 배치다. **진짜 다른 건 화살표 방향 하나뿐이고, I 지표는 정확히 그 방향을 재도록 만들어진 지표다.** 그래서 이 비교에 쓸 만하다 — 고 생각했다.

## 3. 바이브코딩이 이 차이를 왜 증폭시키나

바이브코딩이라는 말은 Andrej Karpathy 가 2025년 2월 2일에 만들었다. 그가 쓴 원문에는 사람들이 자주 빼먹는 문장이 두 개 있다.[^4]

> "I 'Accept All' always, I don't read the diffs anymore."

그리고 마지막 줄:

> "It's not too bad for throwaway weekend projects, but still quite amusing."

**만든 사람 본인이 적용 범위를 주말 프로젝트로 한정했다.** 그런데 지금 이 방식은 주말 프로젝트 밖에서도 쓰이고 있고, 여기서 아키텍처가 개입한다.

diff 를 안 읽으면 **경계 위반은 리뷰에서 안 걸린다.** 컴파일은 통과하고 테스트도 통과한다. 레이어드에서 Service 가 Repository 를 직접 부르는 건 애초에 정상이니 위반이랄 것도 없고, 클린에서 도메인이 JPA 를 import 해도 컴파일러는 아무 말 안 한다. 즉 **두 구조 모두 사람이 안 보면 무너지는데, 클린은 무너질 때 무너졌다는 걸 기계가 알아낼 수 있는 형태로 무너진다.** 이게 실질적인 차이다.

측정 근거도 있다. 두 개만 인용한다.

**METR RCT (2025).** 경력 개발자 16명, 실제 오픈소스 이슈 246건(평균 약 2시간), 평균 22,000+ 스타·100만+ 라인 레포에서 평균 5년 이상 일한 사람들. AI 허용 조건에서 작업 시간이 **19% 더 걸렸다.** 개발자 본인들은 사전에 24% 빨라질 거라 예측했고, 끝나고 나서도 20% 빨라졌다고 답했다. 경제학 전문가는 39%, ML 전문가는 38% 단축을 예측했다.[^5] 체감과 실측이 반대 방향이었다는 게 이 연구의 핵심이다.

**DORA 2025.** 응답자 약 5,000명. 90%가 업무에 AI 를 쓰고 80% 이상이 생산성이 올랐다고 믿는데, **30%는 AI 생성 코드를 거의 또는 전혀 신뢰하지 않는다.** 그리고 2024년과 달리 2025년에는 AI 도입과 처리량·제품 성과 사이에 양의 관계가 나타났지만, **AI 도입과 배포 안정성 사이에는 여전히 음의 관계가 남아 있다.** 이 글 주제에 정확히 걸리는 문장은 이거다:[^6]

> "Teams working in loosely coupled architectures with fast feedback loops see gains, while those constrained by tightly coupled systems and slow processes see little or no benefit."

**AI 는 증폭기지 정류기가 아니다.** 결합이 느슨한 코드베이스에서는 이득이 나고, 단단히 묶인 코드베이스에서는 거의 안 난다.

## 4. 그래서 내 레포 4개를 쟀다

파이썬 스크립트 두 개를 썼다. 방법은 이렇다.

- `.java` / `.kt` 파일에서 `package` 선언과 `import` 목록을 정규식으로 뽑는다
- `build` / `out` / `node_modules` / `.gradle` / `generated` 디렉터리와 경로에 `/test/` 가 들어간 파일은 제외 — **프로덕션 구조**를 재는 게 목적
- 패키지 이름을 역할(domain / application / adapter / config / common)로 접고, 역할 간 의존만 Ca·Ce 에 센다
- 별도로 `org.springframework` · `jakarta.persistence` · `org.hibernate` · `jakarta.servlet` · `org.apache.kafka` import 건수를 역할별로 센다

역할 분류기는 이렇게 생겼다. 순서가 중요하다 — 먼저 걸리는 쪽이 이긴다.

{% raw %}
```python
ROLES = [
    ('adapter',     re.compile(r'\.(adapter|controller|web|rest|api|infra|infrastructure|persistence|repository\b)')),
    ('application', re.compile(r'\.(application|service|usecase|facade)')),
    ('domain',      re.compile(r'\.domain(\.|$)|\.model(\.|$)|\.entity(\.|$)')),
    ('config',      re.compile(r'\.(config|configuration)(\.|$)')),
    ('common',      re.compile(r'\.(common|shared|util|global|support)(\.|$)')),
]

# I = Ce / (Ca + Ce)   — Martin 1994
ce, ca = len(efferent[role]), len(afferent[role])
i = ce / (ca + ce) if (ca + ce) else None
```
{% endraw %}

측정 대상 4개. `settlement` 은 작업 금지를 걸어둔 레포라 제외했다.

| 레포 | 프로덕션 파일 | 최초 커밋 | 표방 구조 |
|---|---|---|---|
| `lemuel-xr` | 158 | 2026-05-20 | 헥사고날 |
| `shop` | 859 | 2026-08-25 | 헥사고날 |
| `inter-asat` | 195 | 2026-03-26 | 레이어드 + 부분 포트 |
| `sparta-msa-project` | 649 | 2026-03-07 | 레이어드 |

결과.

**lemuel-xr** — 158 파일

| 역할 | 파일 | Ca | Ce | I | 프레임워크 import |
|---|---:|---:|---:|---:|---:|
| domain | 38 | 4 | 1 | 0.20 | **0** |
| application | 64 | 2 | 4 | 0.67 | 94 |
| adapter | 30 | 1 | 3 | 0.75 | 141 |
| config | 3 | 0 | 3 | 1.00 | 14 |
| common | 20 | 3 | 0 | 0.00 | 76 |

**shop** — 859 파일

| 역할 | 파일 | Ca | Ce | I | 프레임워크 import |
|---|---:|---:|---:|---:|---:|
| domain | 290 | 4 | 1 | 0.20 | **0** |
| application | 276 | 2 | 3 | 0.60 | 322 |
| adapter | 202 | 1 | 4 | 0.80 | 598 |
| config | 52 | 3 | 4 | 0.57 | 232 |
| common | 34 | 4 | 2 | 0.33 | 71 |

**inter-asat** — 195 파일

| 역할 | 파일 | Ca | Ce | I | 프레임워크 import |
|---|---:|---:|---:|---:|---:|
| domain | 61 | 2 | 0 | **0.00** | **160** |
| application | 100 | 1 | 2 | 0.67 | 73 |
| adapter | 32 | 1 | 2 | 0.67 | 222 |

**sparta-msa-project** — 649 파일

| 역할 | 파일 | Ca | Ce | I | 프레임워크 import |
|---|---:|---:|---:|---:|---:|
| domain | 365 | 2 | 4 | **0.67** | **464** |
| application | 85 | 2 | 3 | 0.60 | 246 |
| adapter | 159 | 2 | 3 | 0.60 | 659 |
| common | 22 | 4 | 0 | 0.00 | 24 |

역할 간 의존 방향도 같이 찍었다. sparta-msa 만 이렇게 나온다.

{% raw %}
```
domain       → adapter, application, common, (기타)
application  → adapter, common, domain
adapter      → application, common, domain
```
{% endraw %}

**도메인이 어댑터에 의존한다.** 의존 규칙이 역전된 정도가 아니라 세 역할이 서로를 다 부른다. I(domain) = 0.67 은 그걸 그대로 반영한 숫자다 — 도메인이 도메인답게 안정하지 않고 어댑터만큼 불안정하다.

## 5. 발견 ① — I 지표는 프레임워크 결합에 눈이 멀었다

표에서 제일 이상한 줄은 `inter-asat` 의 domain 이다.

**I = 0.00.** 마틴 기준으로 완벽하다. 남들이 의존하고 자기는 아무것도 의존하지 않는, 최대로 안정한 패키지. 그런데 같은 줄의 프레임워크 import 가 **160건**이다. `domain.model` 이 `jakarta.persistence.Entity` 를 물고 있고 `domain.port` 가 스프링 데이터의 `Page` · `Pageable` 을 물고 있다.

왜 이런 숫자가 나오나. **Ce 는 "리포 안의 다른 패키지"만 센다.** `jakarta.persistence` 는 리포 밖에 있으니 Ce 에 안 들어간다. 그래서 도메인이 JPA 에 아무리 깊이 묶여 있어도 I 값은 완벽하게 0.00 을 유지한다.

이건 내 스크립트의 버그가 아니라 **지표 정의 자체의 성질**이다. 1994년 논문은 C++ 시절, 한 시스템 내부 카테고리 간 의존을 재려고 만들어졌다. 프레임워크가 도메인 모델 자체에 애너테이션으로 파고드는 상황은 사정권 밖이다.

그래서 **"우리 도메인 I 값 낮아요"는 유지보수성의 증거가 아니다.** ISO 25010 으로 돌아가면, I 가 재는 건 modularity 의 일부고 modifiability 는 저 160건이 결정한다. JPA 를 걷어내려는 순간 도메인 모델 61개 파일을 다 건드려야 한다.

`lemuel-xr` 과 `shop` 은 도메인 프레임워크 import 가 **0건**이다. JPA 는 전부 `.adapter` 아래에만 산다. 두 레포의 I(domain)은 0.20 으로 inter-asat 의 0.00 보다 "나쁘다". **더 나쁜 점수를 받은 쪽이 실제로는 더 깨끗하다.**

## 6. 발견 ② — 규칙을 지키게 만든 건 원칙이 아니라 기계였다

레포별 도메인 위반 건수를 다시 보자.

| 레포 | 도메인 파일 | 프레임워크 import | 아키텍처 자동 게이트 |
|---|---:|---:|---|
| `lemuel-xr` | 38 | 0 | 없음 |
| `shop` | 290 | 0 | **ArchUnit 13개 파일** |
| `inter-asat` | 61 | 160 | 없음 |
| `sparta-msa-project` | 365 | 464 | 없음 |

패턴이 하나 보인다. **위반 없이 남은 건 (a) 작아서 아직 안 무너진 레포와 (b) 기계가 막고 있는 레포 둘뿐이다.**

`lemuel-xr` 은 도메인 38개다. 사람 머리에 들어온다. `shop` 은 290개인데 0건이고, 4개 중 유일하게 ArchUnit 이 깔려 있다. 규칙은 이렇게 생겼다.

{% raw %}
```java
@Test
void domainShouldNotDependOnSpringOrJpa() {
    ArchRule rule = noClasses()
            .that().resideInAPackage("..domain..")
            .and().resideOutsideOfPackage("..adapter..")
            .and().resideOutsideOfPackage("..application..")
            .should().dependOnClassesThat().resideInAnyPackage(
                    "org.springframework..",
                    "jakarta.persistence..",
                    "javax.persistence..")
            .because("도메인 레이어는 프레임워크에 의존하지 않는 순수 POJO 여야 한다");
    rule.check(mainClasses);
}
```
{% endraw %}

`sparta-msa-project` 는 게이트가 없고 도메인이 365개다. 464건 샜다. 패키지 단위로 다시 스캔하니 위반 패키지가 108개였고, 그중에는 이름이 `...domain.admin.controller` 인 것도 있었다. **도메인 패키지 안에 컨트롤러가 산다.** 이름이 규칙을 위반한다고 스스로 말하고 있는데 아무도 막지 않았다.

바이브코딩 맥락에서 이건 그냥 "테스트 쓰세요" 얘기가 아니다. diff 를 안 읽는 워크플로에서 **경계는 사람이 지킬 수 없다.** 지킬 수 있는 건 컴파일러거나 CI 다. 클린 아키텍처가 바이브코딩에서 갖는 실질적 이점은 "더 우아해서"가 아니라 **위반을 기계가 판정 가능한 명제로 바꿔놓기 때문**이다. 레이어드에는 애초에 판정할 명제가 없다 — Service 가 Repository 를 부르는 게 정상이니까.

## 7. 발견 ③ — 그런데 그 게이트도 초록불로 거짓말을 했다

여기서 끝났으면 깔끔한 결론인데, `shop` 의 ArchUnit 테스트를 열어보니 주석에 이런 게 적혀 있었다.

{% raw %}
```java
/**
 * 임포트가 0개면 규칙 전부가 <b>공허 통과</b>(검사 대상 없이 green)한다 — 실제로 order-service 는
 * ArchUnit 1.3.0 + Java 25(class major 69) 조합에서 0개를 임포트한 채 4개 규칙 전부 green 이었다.
 * green 과 blind 는 겉으로 구분되지 않으므로 임포트 건수를 먼저 검사한다.
 */
@Test
void importedClassesMustNotBeVacuous() {
    assertTrue(mainClasses.size() >= MIN_IMPORTED_CLASSES, ...);
}
```
{% endraw %}

ArchUnit 이 Java 25 바이트코드(class major 69)를 못 읽으면 클래스를 **0개** 임포트한다. 검사 대상이 0개면 `noClasses().should()...` 는 전부 참이다. **4개 규칙 전부 초록불인데 실제로 검사한 건 하나도 없었다.** 지금은 ArchUnit 1.4.1 로 올리고, 임포트 건수 하한을 먼저 검사하는 테스트를 앞에 세워서 막고 있다.

같은 파일에 하나 더 있다. `adaptersShouldNotDirectlyReferenceOtherDomainsPersistence` — 이름은 "**타** 도메인의 영속화를 참조하지 말라"인데, 처음 구현은 타깃 패키지만 보는 `DescribedPredicate` 라 소스 도메인과 비교를 안 했다. 그래서 같은 도메인 자기참조(QueryDSL `Q*` 클래스, 자기 리포지토리)까지 전부 위반으로 잡았다. **규칙 이름은 "타 도메인"인데 구현은 "모든 도메인"이었다.** 소스와 타깃을 같이 봐야 해서 `ArchCondition` 으로 다시 썼다.

이 두 개가 이 글에서 제일 중요한 부분이라고 생각한다. `shop` 은 커밋 47개를 이틀에 밀어넣은, 이 4개 중 가장 기계로 만들어진 레포다. 그 레포의 아키텍처 가드가 (1) 아무것도 검사하지 않으면서 초록불이었고, (2) 이름과 다른 걸 검사하고 있었다.

**"Accept All, diff 는 안 읽는다"의 대가는 프로덕션 코드에서만 발생하지 않는다. 그 코드를 지키라고 만든 가드에서도 똑같이 발생한다.** 그리고 가드의 실패는 프로덕션 코드의 실패보다 훨씬 조용하다 — 초록불이 뜨니까.

## 8. 정리 — 유리한 건 클린이 맞지만, 이유가 다르다

내가 재본 범위에서 말할 수 있는 건 이 정도다.

1. **I 지표만으로 두 구조를 비교하지 마라.** 프레임워크 결합을 안 본다. 완벽한 0.00 뒤에 160건이 숨어 있었다.
2. **바이브코딩에서 클린이 유리한 이유는 "의존성이 안쪽을 향해서"가 아니라 "위반이 기계 판정 가능한 명제가 돼서"다.** 화살표를 뒤집는 것 자체는 공짜가 아니고, 그 대가를 정당화하는 건 자동 게이트가 있을 때뿐이다.
3. **게이트를 붙였으면 게이트가 실제로 뭔가를 검사하는지부터 검사해라.** 공허 통과는 실패보다 위험하다.
4. **DORA 가 말한 건 아키텍처가 AI 의 증폭률을 결정한다는 거다.** 느슨하면 이득이 나고 단단히 묶여 있으면 안 난다. 아키텍처는 AI 도입 이후에 더 중요해졌지 덜 중요해지지 않았다.

## 9. 아직 안 풀린 것

이 글의 측정은 **관찰이지 실험이 아니다.** 정직하게 적어둔다.

- **n = 4.** 통계가 아니다. 내 레포다.
- **교란변수가 널려 있다.** 레포 나이(3월~8월), 목적(부트캠프 학습용 vs 실제 서비스), 규모(158~859), 게이트 유무가 전부 섞여 있다. `shop` 이 깨끗한 게 클린을 표방해서인지, ArchUnit 이 있어서인지, 이틀밖에 안 돼서인지 이 데이터로는 못 가른다.
- **역할 분류기가 이름 규칙에 의존한다.** 패키지 이름이 역할과 다르게 붙어 있으면 오분류된다. 실제로 sparta-msa 의 `domain.admin.controller` 는 첫 매치가 `adapter` 라 두 스캔의 도메인 파일 수가 달랐다(365 vs 508).
- **역할로 접으면 없던 순환이 보인다.** 역할 5개로 접으면 패키지 수십 개의 의존이 한 칸에 뭉쳐서 역할 간 양방향 화살표가 쉽게 생긴다. 이건 패키지 수준 순환의 증거가 아니다.
- **레이어드 vs 클린을 유지보수성 결과 변수로 비교한 중립 헤드투헤드 연구를 나는 못 찾았다.** METR 도 DORA 도 이 질문을 직접 묻지 않는다. 그러니 "클린이 유지보수에 낫다"는 여전히 실측이 아니라 **논증**이다. 이 글도 그 논증에 숫자를 조금 붙였을 뿐이다.

재현하려면 파일 두 개면 된다 — 패키지·import 를 정규식으로 뽑아 역할로 접고 `Ce/(Ca+Ce)` 를 계산하는 게 전부다. 자기 레포에 돌려보면 아마 나처럼 예상 밖의 줄을 하나쯤 만날 거다.

---

## References

[^1]: Robert C. Martin, "OO Design Quality Metrics: An Analysis of Dependencies", October 28, 1994. Ca·Ce·I·A·D 의 원 정의. [PDF](http://objectmentor.com/resources/articles/oodmetrc.pdf) ([아카이브](https://web.archive.org/web/2018/http://www.objectmentor.com/resources/articles/oodmetrc.pdf))
[^2]: ISO/IEC 25010:2023, *Systems and software engineering — SQuaRE — Product quality model.* Maintainability 하위특성 정의. <https://www.iso.org/standard/78176.html>
[^3]: Robert C. Martin, "The Clean Architecture", 2012-08-13. <https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html>
[^4]: Andrej Karpathy, X (Twitter) 게시물, 2025-02-02. "바이브코딩"이 처음 쓰인 글. [아카이브](https://archive.ph/yNSTA)
[^5]: Joel Becker, Nate Rush, Beth Barnes, David Rein, "Measuring the Impact of Early-2025 AI on Experienced Open-Source Developer Productivity", arXiv:2507.09089, 2025-07-10. <https://arxiv.org/abs/2507.09089>
[^6]: Google Cloud / DORA, *2025 State of AI-assisted Software Development Report*, 2025-09. <https://dora.dev/research/2025/dora-report/>

측정에 쓴 도구: [ArchUnit](https://www.archunit.org/) 1.4.1. 측정 대상은 본인 GitHub 레포 4개의 프로덕션 소스이며, 수치는 2026-08-27 시점 로컬 워킹트리 기준이다.
