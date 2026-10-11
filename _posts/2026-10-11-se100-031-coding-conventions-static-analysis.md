---
layout: post
title: "[SE100 #031] 코딩 컨벤션과 정적 분석"
date: 2026-10-11 16:59:55 +0900
categories: [software-engineering]
tags: [se100, code-quality, coding-conventions, static-analysis, linter, formatter]
---

소프트웨어 공학 100 주제 시리즈의 31번째 글이다. (카테고리: 구현과 코드 품질)

## 한 줄 요약

컨벤션은 "사람이 합의할 것" 과 "기계에 맡길 것" 을 나누는 작업이고, 정적 분석은 그 중 기계 몫을 실행 전에 검사하는 일이다. 정적 분석은 원리적으로 완전할 수 없으므로, 좋은 도입은 "얼마나 많이 잡느냐" 보다 "개발자가 믿고 고치느냐" 로 판가름 난다.

## 왜 필요한가

리뷰 댓글 대부분이 들여쓰기와 import 순서라면 그 팀은 가장 비싼 자원(사람의 주의력)을 가장 싼 문제에 쓰고 있다. 그동안 동시성 버그와 경계 처리 실수는 지나간다. 리뷰 일반론은 [코드 리뷰]({% post_url 2026-10-10-cs300-190-code-review %}) 글에서 다뤘다.

반대 방향의 실패도 흔하다. 규칙 수백 개를 한꺼번에 켜면 기존 코드에서 경고가 수천 개 쏟아지고, 곧 `# noqa` 가 코드 전체에 뿌려진다. 경고를 무시하는 습관이 생기면 중요한 경고도 함께 묻힌다.

## 핵심 개념

### 컨벤션의 세 층

| 층 | 다루는 것 | 누가 판정하나 | 대표 도구 |
|---|---|---|---|
| 포매팅 | 들여쓰기, 줄바꿈, 공백, 따옴표 | 포매터가 자동으로 고친다 | gofmt, google-java-format, Black, Ruff formatter, Prettier |
| 스타일·관용 | 명명 규칙, import 정리, 사용하지 않는 변수 | 린터가 지적, 일부 자동 수정 | Checkstyle, Ruff, ESLint |
| 의미·버그 패턴 | null 역참조, 잘못된 equals, 자원 누수 | 정적 분석기가 경고 | Error Prone, SpotBugs, NullAway, Infer, mypy |

아래 층으로 갈수록 판정이 어렵고 오탐(false positive)도 늘어난다. 그래서 운영 정책도 달라야 한다. 포매팅은 **토론 없이 자동 적용**, 스타일은 **팀 합의 후 CI 차단**, 의미 규칙은 **신뢰도가 높은 것만 차단하고 나머지는 리뷰 시점 제안**으로 두는 것이 일반적인 배치다.

### 원전이 말하는 컨벤션의 목적

Python 의 [PEP 8](https://peps.python.org/pep-0008/)은 "코드는 쓰이는 것보다 훨씬 자주 읽힌다(code is read much more often than it is written)" 는 Guido 의 통찰을 근거로 든다. 같은 문서의 절 제목 "A Foolish Consistency is the Hobgoblin of Little Minds" 는 일관성보다 가독성이 우선하는 경우가 있다고 분명히 말한다. 컨벤션은 법이 아니라 읽는 비용을 낮추는 도구라는 뜻이다.

공식 가이드는 숫자를 고정한다. PEP 8 은 한 줄 79자, [Google Java Style Guide](https://google.github.io/styleguide/javaguide.html)는 열 제한 100자와 블록 들여쓰기 +2 칸이다. [Kotlin 코딩 컨벤션](https://kotlinlang.org/docs/coding-conventions.html)은 언어 차원에서 제공된다. 숫자가 옳아서가 아니라 **정해져 있다는 사실**이 가치다.

### 포매터: 논쟁을 끝내는 장치

Go 는 처음부터 `gofmt` 를 표준 도구로 내놓았다. Andrew Gerrand 의 [go fmt your code](https://go.dev/blog/gofmt)(2013)는 기계가 정한 형식의 이점을 쓰기 쉬움, 읽기 쉬움, 유지보수 쉬움(기계적 변경이 무관한 diff 를 만들지 않음)으로 정리한다.

Prettier 는 이 철학을 더 직접적으로 적었다. [Option Philosophy](https://prettier.io/docs/en/option-philosophy.html) 문서에 따르면 Prettier 를 쓰는 가장 큰 이유는 "스타일에 대한 끝없는 논쟁을 멈추는 것" 이고, 옵션이 늘수록 논쟁은 "어떤 옵션을 쓸까" 로 옮겨갈 뿐이라서 옵션 추가 요청을 더는 받지 않기로 했다.

포매터 옵션을 놓고 다시 회의를 열면 원래 목적을 잃는다. 기본값을 쓰고 넘어가는 편이 낫다.

### 정적 분석의 이론적 한계

정적 분석은 프로그램을 실행하지 않고 그 성질을 판정하려 한다. 그런데 H. G. Rice 의 1953년 논문 [Classes of recursively enumerable sets and their decision problems](https://doi.org/10.1090/S0002-9947-1953-0053041-6)에서 나온 Rice 정리는, 프로그램이 계산하는 함수에 관한 **자명하지 않은 의미적 성질은 일반적으로 결정 불가능**하다는 것을 보였다. "이 함수가 null 을 역참조하는가" 같은 질문에 모든 프로그램에 대해 항상 정답을 내는 도구는 존재할 수 없다.

그래서 모든 실용 도구는 둘 중 하나(또는 둘 다)를 포기한다.

```
            실제로 버그 있음      실제로 버그 없음
경고함      진양성(잘 잡음)        위양성(오탐) ← 신뢰를 갉아먹음
경고안함    위음성(놓침)           진음성
```

- **건전(sound)** 쪽으로 기울면 놓치는 것은 줄지만 오탐이 늘어난다.
- **실용(unsound)** 쪽으로 기울면 오탐은 적지만 일부 버그를 놓친다.

개발자용 린터와 버그 패턴 검사기는 대개 후자를 택한다. 경고 0 은 "버그 0" 이 아니다.

### 산업 경험: 신뢰가 전부다

Google 의 경험을 정리한 Sadowski 등의 [Lessons from Building Static Analysis Tools at Google](https://research.google/pubs/lessons-from-building-static-analysis-tools-at-google/)(CACM 2018, [DOI](https://doi.org/10.1145/3188720))은 첫 문장부터 결론을 말한다. 정적 분석 프로젝트가 성공하려면 개발자가 그것이 **이득이 되고 쓰기 즐겁다고 느껴야** 한다. 논문은 FindBugs 경험과 학계 문헌의 교훈을 바탕으로 만든 인프라가 Google 엔지니어 다수에게 매일 쓰이며, 엔지니어가 **스스로 선택해** 코드가 체크인되기 전에 고치는 이슈가 하루 수천 건이라고 보고한다. 그 기반이 된 플랫폼이 [Tricorder](https://research.google/pubs/tricorder-building-a-program-analysis-ecosystem/)(ICSE 2015, [DOI](https://doi.org/10.1109/ICSE.2015.76))다.

상용 도구 쪽 경험 보고로는 Coverity 의 [A Few Billion Lines of Code Later](https://doi.org/10.1145/1646353.1646374)(CACM 2010)가 있다.

여기서 나오는 실무 원칙은 셋이다. 경고는 **개발 흐름 안에서**(에디터, 리뷰, 컴파일) 보여 주고, **고치는 방법**까지 함께 주며, 오탐이 많은 검사는 차단 규칙에서 내린다. 신뢰는 한 번 잃으면 모든 규칙에 번진다.

도구가 여럿이면 결과 형식을 OASIS 표준 [SARIF 2.1.0](https://docs.oasis-open.org/sarif/sarif/v2.1.0/sarif-v2.1.0.html)으로 모으면 된다. GitHub 코드 스캐닝도 [SARIF 업로드](https://docs.github.com/en/code-security/code-scanning/integrating-with-code-scanning/sarif-support-for-code-scanning)를 받는다.

## 실무 적용

### 검사를 어디에 두는가

```
[에디터]         [커밋 전]          [CI]                  [리뷰]
EditorConfig  →  pre-commit 훅  →  포매터 검사·린터·    →  사람은 설계·의도·
포매터 on-save    (빠른 것만)        정적 분석·타입 검사       테스트에 집중
                                    (실패 시 머지 차단)
```

[EditorConfig](https://editorconfig.org/)는 에디터와 무관하게 줄끝·들여쓰기를 맞추고, [pre-commit](https://pre-commit.com/) 훅에는 몇 초 안에 끝나는 검사만 둔다(느리면 사람들은 `--no-verify` 를 배운다). 로컬 훅은 우회될 수 있으므로 같은 검사를 CI 에서 다시 돌린다.

### Python 예: Ruff 하나로 포매터 + 린터

```toml
# pyproject.toml
[tool.ruff]
line-length = 100

[tool.ruff.lint]
# E/F: pycodestyle·pyflakes 기본, B: 버그 경향 패턴, I: import 정렬, C90: 복잡도
select = ["E", "F", "B", "I", "C90"]

[tool.ruff.lint.mccabe]
max-complexity = 10
```

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.17.0          # 팀이 쓰는 버전으로 고정
    hooks:
      - id: ruff-check
        args: [--fix]
      - id: ruff-format
```

훅 이름은 [ruff-pre-commit](https://github.com/astral-sh/ruff-pre-commit) README 기준이다. 타입 검사는 [mypy](https://mypy.readthedocs.io/en/stable/)를 CI 에 둔다.

### Java 예: 컴파일 단계에 버그 패턴 검사 붙이기

[Error Prone](https://errorprone.info/)은 javac 플러그인으로 동작해 컴파일러의 타입 검사를 보강한다. [버그 패턴 목록](https://errorprone.info/bugpatterns)은 각 검사가 무엇을 왜 잡는지 설명한다. Uber 의 [NullAway](https://github.com/uber/NullAway)는 Error Prone 위에서 `@Nullable` 주석을 근거로 null 역참조 가능성을 검사한다. 바이트코드 수준 분석은 [SpotBugs](https://spotbugs.github.io/), 형식 검사는 [Checkstyle](https://checkstyle.org/)과 [google-java-format](https://github.com/google/google-java-format)이 맡는다.

### 레거시에 도입할 때: 래칫(ratchet)

기존 코드에 경고가 수천 개라면 한 번에 0 으로 만들려 하지 않는다.

1. 포매터를 한 번에 전체 적용하는 커밋을 **단독으로** 만든다(기능 변경과 섞지 않는다). 그 커밋 해시를 `.git-blame-ignore-revs` 파일에 적어 두면 [`git blame --ignore-revs-file`](https://git-scm.com/docs/git-blame)(또는 `blame.ignoreRevsFile` 설정)과 [GitHub 의 blame 화면](https://docs.github.com/en/repositories/working-with-files/using-files/viewing-and-understanding-files)이 그 커밋을 건너뛴다.
2. 린터는 현재 경고 수를 기준선(baseline)으로 저장하고, **새로 생기는 경고만** CI 에서 막는다.
3. 기준선 숫자는 내려갈 수만 있고 올라갈 수 없게 한다. 손대는 파일부터 자연스럽게 줄어든다.

### 체크리스트

- [ ] 포매터 설정 파일이 저장소에 있고 CI 가 "포맷 안 된 코드" 를 거부한다
- [ ] 억제 주석(`noqa`, `@SuppressWarnings`)에는 이유를 함께 쓰는 규칙이 있다
- [ ] 정적 분석 경고가 리뷰 화면(PR 코멘트, SARIF)에 뜬다

## 흔한 오해와 함정

- **"정적 분석을 통과했으니 안전하다."** Rice 정리 때문에 어떤 도구도 모든 의미적 버그를 잡을 수 없다. 테스트와 리뷰를 대체하지 않는다.
- **"규칙은 많을수록 좋다."** 오탐이 많은 규칙 하나가 나머지 규칙 전체의 신뢰를 떨어뜨린다. 규칙은 소수 정예로 시작해 늘린다.
- **"스타일은 리뷰에서 지적하면 된다."** 기계가 판정할 일을 사람이 지적하면 중요한 지적이 묻힌다.
- **"우리 팀만의 스타일을 만들자."** 커뮤니티 표준과 포매터 기본값을 따르면 신규 입사자와 외부 코드가 같은 모양이 된다. 고유 규칙은 비용이다.
- **포매터 적용과 로직 변경을 한 커밋에 섞기.** diff 가 커져 리뷰가 불가능해진다.

## 확인 문제

1. 컨벤션의 세 층(포매팅, 스타일, 의미 규칙)마다 운영 정책이 달라야 하는 이유는?
2. Rice 정리가 정적 분석 도구 설계에 주는 함의를 "오탐" 과 "놓침" 이라는 말로 설명하라.
3. Google 의 정적 분석 경험 보고에서 성공 조건으로 꼽은 것은 무엇이며, 그것이 규칙 선택에 어떤 영향을 주는가?
4. 경고가 5,000개 있는 레거시 저장소에 린터를 도입하는 절차를 세 단계로 제시하라.

### 풀이

1. 아래 층일수록 판정이 어렵고 오탐이 많다. 포매팅은 판정이 기계적이라 자동 수정이 맞고, 스타일은 합의 후 차단할 수 있지만, 의미 규칙은 오탐 가능성이 있어 신뢰도 높은 것만 차단하고 나머지는 제안으로 둔다.
2. 자명하지 않은 의미적 성질은 결정 불가능하므로, 도구는 모든 버그를 잡으려 하면 오탐이 늘고, 오탐을 줄이려 하면 일부를 놓친다. 실용 도구는 대개 오탐을 줄이는 쪽을 택한다.
3. 개발자가 도구가 이득이고 쓰기 즐겁다고 느끼는 것. 따라서 오탐이 많거나 고치는 방법이 불명확한 규칙은 차단 규칙에서 빼고, 경고를 개발 흐름 안에서 실행 가능한 형태로 제공해야 한다.
4. (1) 포매터 전체 적용을 단독 커밋으로 만들고 blame 무시 목록에 등록한다. (2) 현재 경고를 기준선으로 저장해 새 경고만 CI 에서 막는다. (3) 기준선은 내려가기만 하게 하고, 수정하는 파일부터 점진적으로 경고를 해소한다.

## 더 읽을거리 (References)

- [PEP 8 – Style Guide for Python Code](https://peps.python.org/pep-0008/)
- [Google Java Style Guide](https://google.github.io/styleguide/javaguide.html)
- [Kotlin Coding conventions](https://kotlinlang.org/docs/coding-conventions.html)
- Andrew Gerrand, [go fmt your code](https://go.dev/blog/gofmt), The Go Blog, 2013
- Prettier, [Option Philosophy](https://prettier.io/docs/en/option-philosophy.html)
- H. G. Rice, "Classes of recursively enumerable sets and their decision problems", *Trans. AMS* 74(2), 1953, [DOI](https://doi.org/10.1090/S0002-9947-1953-0053041-6)
- C. Sadowski et al., "Lessons from Building Static Analysis Tools at Google", *CACM* 61(4), 2018, [DOI](https://doi.org/10.1145/3188720)
- C. Sadowski et al., "Tricorder: Building a Program Analysis Ecosystem", ICSE 2015, [DOI](https://doi.org/10.1109/ICSE.2015.76)
- A. Bessey et al., "A Few Billion Lines of Code Later", *CACM* 53(2), 2010, [DOI](https://doi.org/10.1145/1646353.1646374)
- OASIS, [SARIF Version 2.1.0](https://docs.oasis-open.org/sarif/sarif/v2.1.0/sarif-v2.1.0.html)
- [Error Prone](https://errorprone.info/), [NullAway](https://github.com/uber/NullAway), [SpotBugs](https://spotbugs.github.io/), [Ruff](https://docs.astral.sh/ruff/)
