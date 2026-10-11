---
layout: post
title: "[SE100 #053] 재현 가능한 빌드"
date: 2026-10-11 17:03:36 +0900
categories: [software-engineering]
tags: [se100, delivery, reproducible-builds, build, supply-chain]
---

소프트웨어 공학 100 주제 시리즈의 53번째 글이다. (카테고리: 형상 관리와 전달)

## 한 줄 요약

재현 가능한 빌드(reproducible build)란 같은 소스, 같은 빌드 환경, 같은 빌드 절차가 주어지면 **누구든** 비트 단위로 동일한 산출물을 다시 만들 수 있는 빌드다. 이것이 되면 "이 바이너리가 정말 이 소스에서 나왔는가" 를 신뢰가 아니라 해시 비교로 확인할 수 있다.

## 왜 필요한가

우리는 매일 남이 빌드한 바이너리를 실행한다. 배포판 패키지, 컨테이너 기반 이미지, Maven Central 의 JAR. 공개된 소스를 읽고 안전하다고 판단해도, 실제로 설치하는 것은 그 소스에서 **누군가 빌드했다고 주장하는** 바이너리다. 빌드 서버가 침해되었거나 빌드 중에 무언가가 끼어들었다면 소스 리뷰는 아무 의미가 없다.

Ken Thompson 은 튜링상 수상 강연 [Reflections on Trusting Trust](https://doi.org/10.1145/358198.358210)(CACM, 1984)에서 이 문제를 극단까지 밀어붙였다. 컴파일러 바이너리에 트로이 목마를 심으면, 컴파일러 소스를 아무리 깨끗하게 고쳐도 그 컴파일러로 다시 컴파일하는 한 목마가 계속 살아남는다. 결론은 "직접 만들지 않은 코드는 믿을 수 없다" 였다.

재현 가능한 빌드는 이 문제에 대한 실용적 답이다. 서로 독립적인 여러 주체가 같은 소스에서 빌드해 같은 해시를 얻는다면, 그들이 모두 같은 방식으로 침해되지 않은 한 산출물은 소스와 일치한다.

실무적 이점도 크다. 같은 커밋인데 어제와 오늘 빌드 결과가 다르다면, "어느 쪽이 운영에 나간 것인가" 를 확신할 수 없고, 빌드 캐시도 효과를 잃으며, 장애 분석 때 과거 산출물을 다시 만들어 볼 수도 없다.

## 핵심 개념

### 정의

[reproducible-builds.org 의 정의](https://reproducible-builds.org/docs/definition/)는 이렇다.

> 같은 소스 코드, 빌드 환경, 빌드 지침이 주어졌을 때, 어떤 당사자든 지정된 모든 산출물의 비트 단위로 동일한 사본을 재생성할 수 있다면 그 빌드는 재현 가능하다.

정의의 세부가 중요하다.

| 요소 | 정의가 말하는 것 |
|---|---|
| 빌드 환경 | 의존성과 그 버전, 빌드 설정 플래그, 빌드가 참조하는 환경 변수(예: 로케일). 이 집합은 **줄이는 것이 바람직**하다 |
| 산출물 | 실행 파일, 배포 패키지, 파일시스템 이미지. 빌드 로그 같은 부산물은 보통 제외 |
| 검증 | 비트 단위 비교. 보통 암호학적 해시로 한다 |
| 누가 정하나 | 무엇이 관련 환경이고 무엇이 산출물인지는 재현성을 주장하는 저자나 배포자가 정한다 |

"비슷하게 동작한다" 나 "기능적으로 같다" 는 재현성이 아니다. 해시가 같아야 한다.

### 무엇이 재현성을 깨는가

같은 소스인데 결과가 달라지는 원인은 놀랄 만큼 평범하다.

| 원인 | 예 | 처방 |
|---|---|---|
| 타임스탬프 | 바이너리에 박힌 빌드 시각, ZIP/JAR 항목의 수정 시각 | `SOURCE_DATE_EPOCH` 로 고정 |
| 파일 순서 | 디렉터리 순회 순서가 파일시스템마다 다름 | 정렬된 순서로 아카이브 |
| 빌드 경로 | 디버그 정보에 `/home/alice/src` 가 박힘 | 경로 접두사 재매핑 옵션 |
| 로케일·시간대 | 정렬 순서, 날짜 형식 | `LC_ALL=C`, `TZ=UTC` |
| 비결정적 자료구조 | 해시맵 순회 순서로 코드 생성 | 정렬 후 출력 |
| 의존성 해석 | 범위 지정 버전(`^1.2`)이 날마다 다른 버전으로 해석 | 잠금 파일, 해시 고정 |
| 네트워크 | 빌드 중 최신 파일 다운로드 | 사전 고정, 오프라인 빌드 |
| 권한·사용자 | 아카이브 안 파일의 uid, 권한 비트 | 고정 값으로 정규화 |

### SOURCE_DATE_EPOCH

타임스탬프 문제의 사실상 표준 해법은 [SOURCE_DATE_EPOCH 명세](https://reproducible-builds.org/specs/source-date-epoch/)다. 명세의 핵심 규칙은 다음과 같다.

- 값은 1970-01-01 00:00:00 UTC 이후 경과 초(윤초 제외)를 나타내는 **정수의 ASCII 표현**이어야 한다(MUST).
- 빌드 도구는 산출물에 현재 시각을 넣는 대신 이 값을 써야 한다(MUST).
- 값은 재현 가능해야 하며, 보통 마지막 커밋 시각이나 변경 기록의 최신 항목에서 가져온다.

```bash
export SOURCE_DATE_EPOCH=$(git log -1 --format=%ct)
```

### 생태계의 지원

| 도구 | 지원 방식 |
|---|---|
| Maven | `project.build.outputTimestamp` 속성을 pom.xml 에 지정하면 플러그인들이 재현 가능 모드로 동작 ([Maven 가이드](https://maven.apache.org/guides/mini/guide-reproducible-builds.html)) |
| Gradle | Gradle 9.0.0 부터 모든 아카이브 작업(Jar, Zip 등)이 기본적으로 재현 가능: 결정적 파일 순서, 고정 타임스탬프, 고정 권한 ([Gradle 문서](https://docs.gradle.org/current/userguide/working_with_files.html)) |
| Go | Go 1.21.0 이 "완벽하게 재현 가능한" 첫 Go 툴체인이라고 Go 팀이 발표 ([Russ Cox, 2023](https://go.dev/blog/rebuild)) |
| Debian | 배포판 차원의 재현성 작업과 지속적 검증 ([Debian Wiki](https://wiki.debian.org/ReproducibleBuilds), [테스트 결과](https://tests.reproducible-builds.org/debian/reproducible.html)) |

Go 팀의 글은 재현성 달성을 위해 툴체인에서 호스트 운영체제, 호스트 아키텍처, 호스트 C 툴체인 같은 환경 의존을 하나씩 제거한 과정을 자세히 설명한다. 재현성이 "설정 하나 켜기" 가 아니라 환경 의존을 깎아 내는 지속적 작업임을 보여 준다.

### 재현성과 신뢰의 사슬

```
         소스 (커밋 해시로 식별)
              │
   ┌──────────┼──────────┐
   ▼          ▼          ▼
 공식 빌더   독립 빌더 A   독립 빌더 B
   │          │          │
 sha256:9f.. sha256:9f.. sha256:9f..   ← 모두 같으면 산출물은 소스와 일치
```

Thompson 의 컴파일러 공격 자체에 대한 대응으로는 David A. Wheeler 의 [Diverse Double-Compiling(DDC)](https://dwheeler.com/trusting-trust/)이 있다. 서로 독립적인 컴파일러로 컴파일러 소스를 두 번 거쳐 빌드한 결과가 원래 컴파일러 바이너리와 비트 단위로 같은지 비교하는 방법으로, 2005년 ACSAC 논문과 2009년 박사 논문으로 발표되었다. 이 방법 역시 **재현 가능한 빌드가 전제**다. 결과가 매번 달라지면 비교 자체가 불가능하다.

## 실무 적용

### 재현성 점검: 두 번 빌드하고 비교

```bash
#!/usr/bin/env bash
# 같은 커밋을 서로 다른 디렉터리·시각에 두 번 빌드해 해시를 비교한다
set -euo pipefail
REV=$(git rev-parse HEAD)
export SOURCE_DATE_EPOCH=$(git log -1 --format=%ct)
export TZ=UTC LC_ALL=C

for i in 1 2; do
  dir=$(mktemp -d /tmp/rb-$i-XXXX)       # 경로를 일부러 다르게
  git worktree add -q "$dir" "$REV"
  (cd "$dir" && ./gradlew -q --no-build-cache clean jar)
  sha256sum "$dir"/build/libs/*.jar | awk '{print $1}' > /tmp/rb-$i.sha
  git worktree remove --force "$dir"
  sleep 2                                 # 시각도 다르게
done
diff /tmp/rb-1.sha /tmp/rb-2.sha && echo "재현 가능" || echo "차이 있음: diffoscope 로 분석"
```

차이가 나면 [diffoscope](https://diffoscope.org/) 같은 도구로 두 산출물을 재귀적으로 풀어 어디가 다른지 본다. 대부분 타임스탬프, 순서, 경로 중 하나다.

### 컨테이너 이미지에서

```dockerfile
# 기반 이미지는 태그가 아니라 다이제스트로 고정
FROM eclipse-temurin:21-jre@sha256:<digest>
# 패키지 설치는 버전을 명시하거나, 아예 빌드 단계에서 제외
COPY build/libs/app.jar /app/app.jar
```

`apt-get install` 을 버전 지정 없이 실행하는 Dockerfile 은 실행할 때마다 다른 이미지를 만든다. 재현성이 목표라면 OS 패키지 설치는 기반 이미지 쪽으로 밀어내고, 기반 이미지를 다이제스트로 고정한다.

## 흔한 오해와 함정

- **"Docker 를 쓰면 재현 가능하다."** 컨테이너는 실행 환경을 격리할 뿐이다. Dockerfile 안의 `apt-get update`, 고정되지 않은 태그, 빌드 시각이 박힌 레이어는 여전히 매번 다른 결과를 만든다. [Bazel FAQ](https://bazel.build/about/faq)는 Docker 가 시스템 환경의 재현성(어느 버전의 컴파일러인가)은 풀어 주지만, 불완전한 Makefile 을 컨테이너 안에서 돌리면 여전히 예측 불가능한 결과가 나올 수 있다고 설명한다.
- **"잠금 파일이 있으니 됐다."** 잠금 파일은 의존성 해석을 고정할 뿐, 타임스탬프·순서·경로 문제는 그대로다.
- **"재현성 = 결정성."** 결정성은 같은 기계에서 두 번 빌드해 같은 결과가 나오는 것이고, 재현성은 **다른 사람이 다른 기계에서** 같은 결과를 얻는 것이다. 후자가 훨씬 어렵다.
- **산출물 범위를 정하지 않음.** 로그나 테스트 리포트까지 같아야 한다고 고집하면 끝이 없다. 정의대로 "지정된 산출물" 을 명확히 하라.
- **한 번 달성하고 끝.** 의존성 업데이트나 플러그인 변경 하나로 재현성은 조용히 깨진다. CI 에서 이중 빌드 비교를 상시로 돌려야 유지된다.

## 확인 문제

1. reproducible-builds.org 의 정의에서 "비트 단위로 동일한" 이라는 조건이 왜 "기능적으로 동일한" 보다 중요한가?
2. Thompson 의 "Trusting Trust" 공격이 소스 리뷰만으로 막히지 않는 이유는?
3. 같은 커밋을 빌드한 JAR 두 개의 해시가 다르다. 가장 먼저 의심할 원인 세 가지와 처방을 들어라.
4. `SOURCE_DATE_EPOCH` 의 값은 보통 어디서 가져오며, 왜 현재 시각을 쓰면 안 되는가?
5. 결정적 빌드와 재현 가능한 빌드의 차이를 설명하라.

### 풀이

1. 해시가 같아야 제3자가 사람의 판단 없이 기계적으로 검증할 수 있다. "기능적으로 같다" 는 검증 방법이 없고, 악성 코드가 기능을 바꾸지 않은 채 끼어들 수도 있다.
2. 목마가 컴파일러 **바이너리**에 있어서, 컴파일러 소스를 깨끗하게 고쳐도 그 바이너리로 다시 컴파일하면 목마가 재삽입된다. 소스에는 흔적이 없다.
3. 아카이브 항목의 타임스탬프(고정 타임스탬프/`SOURCE_DATE_EPOCH`), 파일 순서(정렬된 아카이브), 빌드 경로가 디버그 정보에 포함(경로 재매핑). 그 밖에 로케일·시간대, 의존성 해석 차이.
4. 보통 마지막 커밋 시각이나 체인지로그의 최신 항목 시각. 현재 시각을 쓰면 빌드할 때마다 값이 달라져 산출물 해시가 달라진다.
5. 결정적 빌드는 같은 환경에서 반복 빌드해도 같은 결과가 나오는 성질이고, 재현 가능한 빌드는 문서화된 환경을 갖춘 다른 주체가 독립적으로 빌드해도 같은 결과가 나오는 성질이다. 재현성은 결정성에 더해 환경 의존을 통제·기술해야 한다.

## 더 읽을거리 (References)

- Reproducible Builds, [Definitions](https://reproducible-builds.org/docs/definition/)
- Reproducible Builds, [SOURCE_DATE_EPOCH specification](https://reproducible-builds.org/specs/source-date-epoch/)
- Ken Thompson, [Reflections on Trusting Trust](https://doi.org/10.1145/358198.358210), Communications of the ACM, 1984
- David A. Wheeler, [Fully Countering Trusting Trust through Diverse Double-Compiling](https://dwheeler.com/trusting-trust/)
- Russ Cox, [Perfectly Reproducible, Verified Go Toolchains](https://go.dev/blog/rebuild), The Go Blog, 2023
- Apache Maven, [Configuring for Reproducible Builds](https://maven.apache.org/guides/mini/guide-reproducible-builds.html)
- Gradle, [Working With Files — Reproducible archives](https://docs.gradle.org/current/userguide/working_with_files.html)
- Debian, [ReproducibleBuilds](https://wiki.debian.org/ReproducibleBuilds)
- Bazel, [Hermeticity](https://bazel.build/basics/hermeticity)
- CS300: [Dockerfile 모범 사례]({% post_url 2026-10-10-cs300-225-dockerfile-best-practices %})
