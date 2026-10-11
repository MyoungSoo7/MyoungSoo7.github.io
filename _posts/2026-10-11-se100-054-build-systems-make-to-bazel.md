---
layout: post
title: "[SE100 #054] 빌드 시스템 — Make 에서 Bazel 까지"
date: 2026-10-11 17:03:37 +0900
categories: [software-engineering]
tags: [se100, delivery, build-systems, make, bazel]
---

소프트웨어 공학 100 주제 시리즈의 54번째 글이다. (카테고리: 형상 관리와 전달)

## 한 줄 요약

빌드 시스템은 "무엇이 바뀌었고, 그래서 무엇을 다시 만들어야 하는가" 를 결정하는 프로그램이다. Make 부터 Bazel 까지의 진화는 이 질문에 답하는 두 부품, 즉 **스케줄러(어떤 순서로)** 와 **재빌드 판정기(다시 할 필요가 있는가)** 를 더 정확하고 더 공유 가능하게 만드는 과정이었다.

## 왜 필요한가

작은 프로젝트에서는 "전부 다시 컴파일" 로 충분하다. 수천 개 모듈이 되면 이야기가 다르다. 전체 빌드가 30분이면 개발자는 하루에 몇 번밖에 피드백을 못 받고, 트렁크 기반 개발(SE100 #052 에서 다룬다)의 "하루 여러 번 통합" 은 불가능해진다.

반대로 너무 공격적으로 생략하면 틀린 결과가 나온다. 헤더 파일이 바뀌었는데 그것을 포함한 `.c` 파일을 다시 컴파일하지 않는 경우, "내 컴퓨터에서는 되는데" 문제, `make clean` 을 해야만 고쳐지는 버그가 여기서 나온다. 빌드 시스템의 목표는 **정확성(correctness)을 지키면서 최소한의 작업만 하는 것**이다.

## 핵심 개념

### Make: 의존성 그래프와 수정 시각

Stuart Feldman 이 1979년 발표한 [Make — a program for maintaining computer programs](https://doi.org/10.1002/spe.4380090402)(Software: Practice and Experience)가 출발점이다. [GNU make 매뉴얼](https://www.gnu.org/software/make/manual/make.html)의 첫 문장이 그 목적을 요약한다. make 는 큰 프로그램의 어느 부분을 다시 컴파일해야 하는지 자동으로 판단하고 그 명령을 실행한다.

```make
app: main.o util.o
	cc -o app main.o util.o

main.o: main.c util.h
	cc -c main.c

util.o: util.c util.h
	cc -c util.c
```

판단 기준은 단순하다. 매뉴얼의 설명대로 make 는 makefile 의 규칙과 **파일의 마지막 수정 시각**을 보고, 대상(target)보다 새로운 선행 파일(prerequisite)이 있으면 대상을 다시 만든다.

이 단순함이 강점이자 한계다.

| 한계 | 결과 |
|---|---|
| 수정 시각 기반 | 파일을 `touch` 만 해도 재빌드, 시계가 어긋난 네트워크 파일시스템에서 오판 |
| 의존성을 사람이 적음 | `util.h` 를 빠뜨리면 조용히 틀린 결과 |
| 명령의 입력이 불완전 | 컴파일러 플래그나 환경 변수가 바뀌어도 감지 못 함 |
| 로컬 상태 | 내 머신의 결과를 동료가 재사용할 수 없음 |

### 작업 기반에서 산출물 기반으로

Bazel 문서는 빌드 시스템을 [작업(task) 기반](https://bazel.build/basics/task-based-builds)과 [산출물(artifact) 기반](https://bazel.build/basics/artifact-based-builds)으로 구분해 설명한다.

- 작업 기반(문서는 Ant, Maven, Gradle, Grunt, Rake 를 예로 든다): 개발자가 "무엇을 하라" 는 명령형 작업을 정의한다. 작업이 임의의 일을 할 수 있어 시스템이 안전하게 생략하거나 병렬화하기 어렵다.
- 산출물 기반(Bazel 등): 개발자는 "무엇을 만들고 그 입력이 무엇인가" 를 선언하고, 어떻게 만들지는 시스템이 결정한다. 입력과 출력이 선언되어 있으므로 캐시와 병렬화가 안전해진다.

```python
# Bazel BUILD 파일 (Starlark): 선언적으로 입력과 출력을 밝힌다
java_library(
    name = "order-core",
    srcs = glob(["src/main/java/**/*.java"]),
    deps = ["//common:money", "@maven//:com_google_guava_guava"],
)

java_test(
    name = "order-core-test",
    srcs = glob(["src/test/java/**/*.java"]),
    deps = [":order-core", "@maven//:junit_junit"],
)
```

### 밀폐성(hermeticity)

Bazel 의 [Hermeticity](https://bazel.build/basics/hermeticity) 문서는 밀폐 빌드를 이렇게 정의한다. 같은 입력 소스와 제품 설정이 주어지면, 빌드를 호스트 시스템의 변화로부터 격리해 **항상 같은 출력**을 낸다. 두 측면이 있다.

- **격리(isolation)**: 도구를 소스 코드처럼 취급한다. 컴파일러와 도구를 내려받아 관리되는 파일 트리 안에서 쓰고, 호스트에 설치된 것을 쓰지 않는다.
- **소스 식별(source identity)**: 입력이 같은지를 해시로 판정한다.

문서는 이점으로 속도(입력이 같으면 캐시된 결과 재사용), 병렬 실행, 한 머신에서 서로 다른 도구 버전의 빌드 공존, 재현성을 든다. 재현 가능한 빌드(SE100 #053 에서 다룬다)의 엔지니어링 기반이 바로 이 밀폐성이다.

### 원격 캐시와 콘텐츠 주소 저장소

밀폐성이 확보되면 빌드 결과를 **팀 전체가 공유**할 수 있다. [Bazel 원격 캐싱 문서](https://bazel.build/remote/caching)는 원격 캐시가 두 부분으로 이루어진다고 설명한다.

```
액션 = (입력 파일 해시들, 명령줄, 환경 변수, 출력 이름)
            │ 해시
            ▼
  [액션 캐시]  action hash ──▶ 결과 메타데이터 (출력 파일들의 해시)
                                         │
                                         ▼
  [CAS]       content hash ──▶ 실제 출력 파일 바이트
```

동료가 이미 같은 입력으로 컴파일했다면 나는 컴파일하지 않고 결과를 내려받는다. Gradle 도 [빌드 캐시](https://docs.gradle.org/current/userguide/build_cache.html)에서 같은 발상을 쓴다. 태스크가 입력과 출력을 모두 기술하므로, 입력으로부터 출력을 유일하게 정의하는 캐시 키를 계산할 수 있다(Gradle 빌드 캐시는 기본으로 꺼져 있다).

### 빌드 시스템의 분류: 스케줄러 × 재빌드 판정기

Mokhov, Mitchell, Peyton Jones 의 [Build systems à la carte](https://doi.org/10.1145/3236774)(ICFP 2018)와 확장판 [Theory and practice](https://ndmitchell.com/downloads/paper-build_systems_a_la_carte_theory_and_practice-21_apr_2020.pdf)(JFP 2020)는 빌드 시스템을 두 부품의 조합으로 분해한다. 확장판의 Table 2 를 옮기면 다음과 같다.

| 재빌드 판정 \ 스케줄러 | 위상 정렬(Topological) | 재시작(Restarting) | 일시 중단(Suspending) |
|---|---|---|---|
| 더티 비트 | Make | Excel | — |
| 검증 트레이스 | Ninja | — | Shake |
| 구성 트레이스 | CloudBuild | Bazel | — |
| 깊은 구성 트레이스 | Buck | — | Nix |

- **위상 정렬 스케줄러**: 의존성 그래프를 미리 알고 순서를 정한다. 의존성이 정적이어야 한다.
- **재시작/일시 중단 스케줄러**: 빌드 도중에 새 의존성이 발견되는 **동적 의존성**을 처리한다.
- **검증 트레이스**: 지난번 입력의 해시를 기록해 두고, 바뀌었는지 확인해 재빌드를 판단한다.
- **구성 트레이스**: 입력 해시로부터 **결과 자체**를 찾아올 수 있게 기록한다. 이것이 클라우드 캐시를 가능하게 한다.

논문의 Table 1 은 Make 가 정적 의존성과 수정 시각을 쓰고 클라우드 빌드를 지원하지 않는 반면, Bazel 은 동적 의존성(단, 사용자 정의 규칙은 제외)과 클라우드 캐시를 지원한다고 정리한다. 논문은 이 표의 빈칸(일시 중단 스케줄러 + 구성 트레이스)을 "Cloud Shake" 라는 새 설계로 채워 보이기도 한다. 이 분류는 새 빌드 도구를 볼 때 "그래서 무엇이 다른가" 를 묻는 좋은 틀이다.

### Bazel 의 출처

[Bazel FAQ](https://bazel.build/about/faq)에 따르면 Bazel 은 Google 이 서버 소프트웨어를 빌드하는 내부 도구의 한 형태이고 코드 대부분을 그 내부 도구와 공유한다. 코드베이스의 "Blaze" 는 그 내부 이름이다. FAQ 는 Google 이 예전에 거대한 생성형 Makefile 로 빌드하다가 느리고 불안정한 빌드 문제를 겪었고 Bazel 이 그 해법이었다고 설명하며, 내부에서는 도구 자체를 소스 관리에 넣어 재현성을 확보한다고 밝힌다.

## 실무 적용

### 어떤 도구를 고를까

| 상황 | 현실적 선택 |
|---|---|
| 단일 언어, 중소 규모 JVM 서비스 | Gradle/Maven + 빌드 캐시, 잠금 파일 |
| 단일 언어, 대규모 모노레포 | 언어 생태계의 고급 기능(Gradle 구성 캐시, Nx/Turborepo 등) 검토 |
| 다언어 대규모 모노레포, 원격 실행 필요 | Bazel/Buck2/Pants 류 |
| C/C++ 작은 프로젝트 | Make 또는 CMake + Ninja |

Bazel 류로의 전환 비용은 크다. 모든 의존성을 선언해야 하고, 기존 생태계 플러그인을 그대로 쓸 수 없는 경우가 많다. 빌드 시간과 정확성 문제가 실제로 팀의 병목일 때 검토한다.

### 어느 도구든 적용할 원칙

```
[ ] 빌드 입력을 전부 선언한다 (숨은 입력: 환경 변수, 홈 디렉터리 설정, 네트워크)
[ ] 툴체인 버전을 저장소에 고정한다 (Gradle wrapper, .tool-versions, toolchains)
[ ] 빌드 중 네트워크 접근을 최소화한다 (의존성은 잠금 파일 + 미러)
[ ] 출력은 입력만의 함수가 되게 한다 (타임스탬프, 절대 경로 제거)
[ ] CI 에서 원격 캐시 쓰기, 개발자는 읽기 위주 (캐시 오염 방지)
[ ] "clean 빌드에서만 재현되는 버그" 를 빌드 정확성 결함으로 취급한다
```

## 흔한 오해와 함정

- **"Make 는 낡았다."** 정적 의존성, 로컬, 작은 규모라면 Make 는 여전히 단순하고 충분하다. 문제는 도구가 아니라 규모와 요구의 불일치다.
- **"캐시가 빠르게 해 준다."** 캐시는 입력 선언이 정확할 때만 안전하다. 숨은 입력이 있으면 캐시는 **틀린 결과를 빠르게** 돌려준다.
- **"Bazel 을 쓰면 자동으로 재현 가능하다."** 밀폐성을 깨는 규칙(호스트 도구 호출, 타임스탬프 삽입)을 쓰면 Bazel 도 재현 가능하지 않다.
- **`make clean` 을 습관처럼.** clean 빌드가 필요하다는 것은 의존성 선언이 틀렸다는 신호다. 덮지 말고 고친다.
- **빌드 스크립트를 형상 항목에서 제외.** 빌드 정의와 툴체인 버전도 소스와 똑같이 리뷰·버전 관리 대상이다.

## 확인 문제

1. Make 가 재빌드 여부를 판단하는 기준은 무엇이며, 그 방식의 약점 두 가지는?
2. 작업 기반 빌드 시스템과 산출물 기반 빌드 시스템의 차이를, 캐시 안전성 관점에서 설명하라.
3. Bazel 문서가 말하는 밀폐성의 두 측면은 무엇인가?
4. Mokhov 등의 분류에서 "검증 트레이스" 와 "구성 트레이스" 의 차이는 무엇이며, 원격 캐시에는 어느 쪽이 필요한가?
5. 원격 캐시를 도입했더니 가끔 오래된 코드가 포함된 산출물이 나온다. 가장 의심할 원인은?

### 풀이

1. 대상 파일보다 선행 파일의 수정 시각이 더 새로운지. 약점: 내용이 같아도 시각만 바뀌면 재빌드(혹은 시계 불일치로 오판), 사람이 의존성을 빠뜨리면 감지 못 함, 플래그·환경 변화 미감지.
2. 작업 기반은 임의 동작을 하는 명령형 작업이라 입력·출력을 시스템이 알 수 없어 생략과 캐시가 위험하다. 산출물 기반은 입력과 출력이 선언되어 있어 입력 해시로 결과를 안전하게 재사용할 수 있다.
3. 격리(도구를 소스처럼 관리해 호스트 환경과 분리)와 소스 식별(입력의 동일성을 해시로 판정).
4. 검증 트레이스는 이전 입력 해시를 기록해 "바뀌었는지" 만 확인한다. 구성 트레이스는 입력 해시로 **결과물 자체**를 찾아올 수 있게 저장한다. 다른 사람이 만든 결과를 가져오는 원격 캐시에는 구성 트레이스가 필요하다.
5. 선언되지 않은 숨은 입력. 그 입력이 바뀌어도 액션 해시가 같아 이전 결과가 캐시에서 반환된다.

## 더 읽을거리 (References)

- Stuart I. Feldman, [Make — a program for maintaining computer programs](https://doi.org/10.1002/spe.4380090402), Software: Practice and Experience, 1979
- GNU, [GNU make manual](https://www.gnu.org/software/make/manual/make.html)
- Andrey Mokhov, Neil Mitchell, Simon Peyton Jones, [Build systems à la carte](https://doi.org/10.1145/3236774), ICFP 2018
- Andrey Mokhov, Neil Mitchell, Simon Peyton Jones, [Build systems à la carte: Theory and practice](https://ndmitchell.com/downloads/paper-build_systems_a_la_carte_theory_and_practice-21_apr_2020.pdf), Journal of Functional Programming, 2020
- Bazel, [Task-Based Build Systems](https://bazel.build/basics/task-based-builds), [Artifact-Based Build Systems](https://bazel.build/basics/artifact-based-builds), [Hermeticity](https://bazel.build/basics/hermeticity), [Remote Caching](https://bazel.build/remote/caching), [FAQ](https://bazel.build/about/faq)
- Gradle, [Build Cache](https://docs.gradle.org/current/userguide/build_cache.html)
- CS300: [CI/CD]({% post_url 2026-10-10-cs300-196-ci-cd %})
