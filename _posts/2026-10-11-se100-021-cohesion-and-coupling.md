---
layout: post
title: "[SE100 #021] 응집도와 결합도 — 설계 품질의 두 축"
date: 2026-10-11 16:58:04 +0900
categories: [software-engineering]
tags: [se100, software-architecture, cohesion, coupling, modularity, information-hiding]
---

소프트웨어 공학 100 주제 시리즈의 21번째 글이다. (카테고리: 설계와 아키텍처)

## 한 줄 요약

응집도(cohesion)는 **한 모듈 안의 것들이 얼마나 같은 이유로 모여 있는가**, 결합도(coupling)는 **한 모듈을 바꿀 때 다른 모듈도 얼마나 바꿔야 하는가**를 묻는다. 좋은 분할은 응집도를 높이고 결합도를 줄이는 것인데, 무엇을 기준으로 나눌지는 Parnas 가 1972년에 답을 냈다. 바뀔 가능성이 큰 결정을 하나씩 모듈 안에 숨겨라.

## 왜 필요한가

"이 클래스는 너무 크다", "이 서비스들은 너무 얽혀 있다" 같은 리뷰 코멘트는 흔하다. 그런데 "왜 그게 나쁜가, 어떻게 나눠야 하는가" 를 물으면 대개 감으로 답한다. 감으로 나누면 두 가지 실패가 자주 나온다.

- **처리 단계로 나눈다.** 입력 모듈, 변환 모듈, 출력 모듈. 흐름도 그대로 자른 것이다. 그런데 데이터 형식 하나가 바뀌면 세 모듈을 다 고쳐야 한다.
- **기술 종류로 나눈다.** `utils`, `helpers`, `common`. 이름만 모듈이지 아무 관계 없는 함수가 모인다. 누구나 의존하므로 아무도 고치지 못한다.

둘 다 "모듈로 나눴다" 는 사실은 같지만 변경 비용은 크게 다르다. 응집도와 결합도는 이 차이를 말로 표현하는 도구다. SOLID 의 단일 책임 원칙도 같은 질문을 클래스 수준에서 다시 던진 것이다([SOLID 원칙]({% post_url 2026-10-10-cs300-185-solid-principles %})).

## 핵심 개념

### 출처: 구조적 설계

응집도와 결합도라는 용어는 W. P. Stevens, G. J. Myers, L. L. Constantine 의 논문 ["Structured design"](https://doi.org/10.1147/sj.132.0115) (IBM Systems Journal 13(2), 1974) 로 널리 퍼졌고, Yourdon 과 Constantine 의 책 *Structured Design* (Prentice-Hall, 1979) 에서 체계화됐다. Martin Fowler 는 IEEE Software 칼럼 [Reducing Coupling](https://martinfowler.com/ieeeSoftware/coupling.pdf) (2001) 에서 "가장 이른 설계 품질 지표가 결합도였고, 구조적 설계의 초기 작업에서 응집도와 함께 등장해 사라진 적이 없다" 고 썼다.

같은 칼럼에서 Fowler 가 내린 결합도의 정의가 실무에서 가장 쓸모 있다.

> 프로그램의 한 모듈을 바꿀 때 다른 모듈도 바꿔야 한다면, 결합이 존재한다.

이 정의에서 두 가지가 따라 나온다. 첫째, **중복은 언제나 결합이다.** 두 곳에 복사된 코드는 서로 호출하지 않아도 한쪽을 고치면 다른 쪽도 고쳐야 한다. 둘째, **결합은 0 이 될 수 없다.** 모듈은 서로 통신해야 하고, 결합을 금지하면 모든 것을 한 모듈에 넣게 되는데, 그러면 결합이 사라지는 게 아니라 "양탄자 밑에 숨겨질" 뿐이다(Fowler). 목표는 결합 제거가 아니라 **통제**다.

### 응집도의 서열

구조적 설계 계열 교재는 응집도를 약한 것부터 강한 것까지 대략 다음 순서로 정리한다. 이름과 개수는 교재마다 조금씩 다르므로 외울 대상이 아니라 "왜 같이 있는가" 를 묻는 체크리스트로 쓰는 편이 낫다.

| 수준 | 모인 이유 | 예 |
|---|---|---|
| 우연적(coincidental) | 이유 없음 | `CommonUtils` 에 날짜 포맷·암호화·엑셀 파싱 |
| 논리적(logical) | 같은 "종류" 의 일 | 모든 입력(파일·소켓·키보드)을 플래그로 분기하는 `readInput(type)` |
| 시간적(temporal) | 같은 시점에 실행 | `onStartup()` 에 캐시 예열·로그 설정·DB 마이그레이션 |
| 절차적(procedural) | 정해진 순서로 실행 | 검증 → 저장 → 메일 발송이 한 함수에 |
| 통신적(communicational) | 같은 데이터를 다룸 | 주문 하나로 영수증과 배송장을 모두 만드는 모듈 |
| 순차적(sequential) | 앞 단계 출력이 뒤 단계 입력 | 파싱 → 정규화 → 집계 파이프라인 |
| 기능적(functional) | 하나의 잘 정의된 일 | `calculateShippingFee(order)` |

위로 갈수록 "모듈 이름을 한 문장으로 말하기 어렵다". 이름에 "그리고", "또는", "관리자(Manager)" 가 들어가면 응집도를 의심해 볼 신호다.

### 결합도의 서열

결합도도 같은 계열 교재에서 강한 것부터 약한 것 순으로 정리된다.

| 수준 | 의존하는 것 | 냄새 |
|---|---|---|
| 내용(content) | 상대의 내부 구현 | 리플렉션으로 private 필드 수정 |
| 공통(common) | 공유 전역 데이터 | 전역 싱글턴 상태를 여러 모듈이 갱신 |
| 외부(external) | 외부 형식·프로토콜 | 여러 모듈이 같은 CSV 열 순서를 가정 |
| 제어(control) | 상대의 제어 흐름 | `process(data, mode=3)` 같은 플래그 인자 |
| 스탬프(stamp) | 필요 이상으로 큰 구조체 | 이메일만 필요한데 `User` 전체를 넘김 |
| 데이터(data) | 필요한 값만 | `sendMail(address, body)` |

실무에서는 서열 자체보다 **방향과 범위**가 더 중요하다. Fowler 는 같은 칼럼에서 "모든 곳의 결합을 걱정하면 압도된다" 며 **최상위 모듈 십여 개 사이의 의존 방향**부터 보라고 권한다. 결합된 모듈의 수보다 의존 관계의 패턴, 특히 순환을 본다.

### Parnas: 무엇을 기준으로 나누는가

D. L. Parnas 의 ["On the criteria to be used in decomposing systems into modules"](https://doi.org/10.1145/361598.361623) (CACM 15(12), 1972) 는 KWIC 색인 프로그램을 두 방식으로 나눠 비교한다.

- **첫 번째 분할**: 처리의 주요 단계마다 모듈 하나. Parnas 는 이를 "흐름도를 그리면 얻어지는 분할" 이라 부른다.
- **두 번째 분할**: "정보 은닉(information hiding)" 을 기준으로 삼은 분할. 줄 저장 방식, 순환 이동 방식, 정렬 방식 같은 설계 결정을 각각 한 모듈이 숨긴다. 모듈이 처리 단계와 대응하지 않는다.

입력 형식이나 저장 방식이 바뀌는 시나리오를 대 보면, 첫 번째 분할은 여러 모듈을 동시에 고쳐야 하고 두 번째 분할은 해당 결정을 숨긴 모듈 하나만 고치면 된다. 결론부에서 Parnas 는 이렇게 제안한다.

> 시스템을 흐름도에 근거해 모듈로 나누기 시작하는 것은 거의 언제나 틀렸다. 대신 **어려운 설계 결정이나 바뀔 가능성이 큰 설계 결정의 목록**에서 시작하고, 각 모듈이 그런 결정 하나를 다른 모듈로부터 숨기도록 설계하라.

이것이 응집도와 결합도를 실제로 개선하는 처방이다. 한 결정을 한 곳에 모으면 응집도가 올라가고, 그 결정을 밖에 드러내지 않으면 결합도가 내려간다. 두 축은 따로 노는 지표가 아니라 같은 행위의 두 결과다.

### 의존을 끊는 기본 수단: 인터페이스를 쓰는 쪽에 둔다

Fowler 의 칼럼은 도메인과 데이터베이스 사이 의존을 끊는 방법으로, **도메인 패키지 안에 저장 인터페이스를 정의하고 매퍼 패키지가 그것을 구현**하는 구조를 보여 준다. 구현은 인터페이스에 의존하지만 그 역은 아니므로, 도메인은 매퍼를 모른 채 동작한다. 콜백, 리스너, 이벤트도 같은 원리다. 이 아이디어는 SE100 #027(헥사고날·클린 아키텍처)에서 아키텍처 전체의 규칙으로 커진다.

```
 [Domain] ──정의── Store(interface)
                        ▲
                        │ 구현
 [Mapper] ── StoreImpl ─┘ ──▶ [Database]
```

## 실무 적용

### 리뷰에서 쓰는 질문 다섯 개

1. 이 모듈이 하는 일을 "그리고" 없이 한 문장으로 말할 수 있는가? (응집도)
2. 최근 변경 이력에서 **항상 같이 바뀌는 파일 쌍**이 서로 다른 모듈에 있지는 않은가? (숨어 있는 결합)
3. 이 모듈이 숨기는 설계 결정은 무엇인가? 그 결정이 바뀌면 몇 곳을 고쳐야 하는가? (Parnas)
4. 인자로 받은 플래그가 함수 내부 분기를 고르는가? (제어 결합)
5. 상위 패키지 사이 의존에 순환이 있는가? (Fowler)

2번은 도구로 측정할 수 있다. 같은 커밋에 함께 등장한 파일 쌍을 세면 "논리적 결합" 이 보인다.

```python
# git 이력에서 함께 바뀐 파일 쌍을 센다 (논리적 결합 탐지)
import itertools, subprocess, collections

log = subprocess.run(
    ["git", "log", "--name-only", "--pretty=format:@@", "-n", "500"],
    capture_output=True, text=True, check=True).stdout

pairs = collections.Counter()
for commit in log.split("@@"):
    files = sorted({f for f in commit.split("\n") if f.endswith((".java", ".kt", ".py"))})
    for a, b in itertools.combinations(files, 2):
        pairs[(a, b)] += 1

for (a, b), n in pairs.most_common(10):
    print(f"{n:3d}  {a}  <->  {b}")
```

상위에 뜬 쌍이 서로 다른 패키지라면, 둘 사이에 같은 설계 결정이 흩어져 있다는 뜻이다. 그 결정을 한 곳으로 모으는 것이 리팩터링 대상이다.

### 제어 결합을 데이터 결합으로

```kotlin
// 제어 결합: 호출자가 내부 분기를 고른다
fun export(report: Report, mode: Int): ByteArray = when (mode) {
    1 -> toCsv(report)
    2 -> toPdf(report)
    else -> error("unknown mode")
}

// 개선: 결정(형식)을 타입 하나 뒤에 숨긴다
interface ReportFormat { fun render(report: Report): ByteArray }
object CsvFormat : ReportFormat { override fun render(report: Report) = toCsv(report) }
object PdfFormat : ReportFormat { override fun render(report: Report) = toPdf(report) }

fun export(report: Report, format: ReportFormat) = format.render(report)
```

새 형식이 추가돼도 `export` 와 그 호출자는 바뀌지 않는다. "어떤 형식들이 있는가" 라는 바뀔 결정이 각 구현 안으로 숨었다.

## 흔한 오해와 함정

- **"결합도는 낮을수록 좋다."** 결합을 없애려고 모든 호출을 이벤트·메시지로 바꾸면, 결합은 줄지 않고 **보이지 않게** 된다. 컴파일러가 잡아 주던 의존이 런타임 계약으로 옮겨 갔을 뿐이다.
- **"작게 나눌수록 응집도가 높다."** 하나의 결정이 여러 작은 클래스에 흩어지면 오히려 응집도가 떨어진다. 크기가 아니라 "같은 이유로 바뀌는가" 가 기준이다.
- **"DRY 를 위해 공통 모듈로 뽑는다."** 우연히 모양만 같은 코드를 합치면 서로 다른 이유로 바뀌는 두 소비자가 한 모듈에 묶인다. 중복 제거가 새 결합을 만드는 경우다.
- **"인터페이스를 만들면 결합이 끊긴다."** 인터페이스가 구현 쪽 패키지에 있으면 의존 방향은 그대로다. 인터페이스는 **쓰는 쪽**에 있어야 한다(Fowler 의 Store 예).
- **"정보 은닉 = private 필드."** Parnas 가 말한 은닉 대상은 필드가 아니라 **설계 결정**이다. getter/setter 로 내부 구조를 그대로 노출하면 private 이어도 은닉은 없다.

## 확인 문제

1. Fowler 의 정의에 따르면 서로 호출하지 않는 두 모듈 사이에도 결합이 있을 수 있다. 어떤 경우인가?
2. Parnas 의 KWIC 예에서 첫 번째 분할과 두 번째 분할의 기준은 각각 무엇인가?
3. `save(entity, async=true)` 같은 시그니처는 어떤 결합에 해당하며, 어떻게 개선할 수 있는가?
4. 응집도를 올리고 결합도를 낮추는 일이 "같은 행위의 두 결과" 라는 말을 설명하라.
5. 저장소 인터페이스를 인프라 패키지에 두면 왜 의존이 끊기지 않는가?

### 풀이

1. 코드가 중복된 경우. 한쪽을 고치면 다른 쪽도 고쳐야 하므로 호출 관계가 없어도 결합이다. 같은 외부 형식(CSV 열 순서 등)을 각자 가정하는 경우도 마찬가지다.
2. 첫 번째는 처리의 주요 단계(흐름도), 두 번째는 정보 은닉 — 바뀔 가능성이 큰 설계 결정을 하나씩 숨기는 것.
3. 호출자가 내부 처리 방식을 고르는 제어 결합이다. 동기·비동기 저장을 별도 메서드나 별도 타입(전략)으로 나누면 호출자는 필요한 것만 선택하고 내부 분기에 의존하지 않는다.
4. 바뀔 결정 하나를 한 모듈 안에 모으면 그 모듈의 내용은 같은 이유로 묶이므로 응집도가 오르고, 그 결정을 밖으로 드러내지 않으면 다른 모듈이 거기 의존하지 않으므로 결합도가 내려간다.
5. 도메인이 인터페이스를 쓰려면 인프라 패키지를 import 해야 하므로, 도메인 → 인프라 의존이 그대로 남는다. 인터페이스를 도메인(쓰는 쪽)에 두고 인프라가 구현해야 의존이 역전된다.

## 더 읽을거리 (References)

- D. L. Parnas, ["On the criteria to be used in decomposing systems into modules"](https://doi.org/10.1145/361598.361623), Communications of the ACM 15(12), 1053–1058, 1972
- W. P. Stevens, G. J. Myers, L. L. Constantine, ["Structured design"](https://doi.org/10.1147/sj.132.0115), IBM Systems Journal 13(2), 115–139, 1974
- Martin Fowler, [Reducing Coupling](https://martinfowler.com/ieeeSoftware/coupling.pdf), IEEE Software, July/August 2001
- Edward Yourdon, Larry L. Constantine, *Structured Design: Fundamentals of a Discipline of Computer Program and Systems Design*, Prentice-Hall, 1979 (서지 정보)
- CS300: [SOLID 원칙]({% post_url 2026-10-10-cs300-185-solid-principles %})
