---
layout: post
title: "[SE100 #055] 지속적 전달과 지속적 배포"
date: 2026-10-11 17:03:38 +0900
categories: [software-engineering]
tags: [se100, delivery, continuous-delivery, continuous-deployment, deployment-pipeline]
---

소프트웨어 공학 100 주제 시리즈의 55번째 글이다. (카테고리: 형상 관리와 전달)

## 한 줄 요약

지속적 전달(Continuous Delivery)은 소프트웨어를 **언제든 운영에 내보낼 수 있는 상태**로 유지하는 규율이고, 지속적 배포(Continuous Deployment)는 거기서 한 걸음 더 나가 파이프라인을 통과한 **모든 변경을 자동으로 운영에 내보내는** 실천이다. 앞의 것은 능력이고 뒤의 것은 그 능력을 매번 행사하는 선택이다.

## 왜 필요한가

CI/CD 파이프라인의 구성과 DORA 지표의 기초는 [CI/CD]({% post_url 2026-10-10-cs300-196-ci-cd %})에서 다뤘다. 이 글은 두 개념의 원전 정의, 그 경계에서 실무 판단이 갈리는 지점, 그리고 지속적 배포를 실제로 가능하게 했던 조건을 본다.

두 용어를 혼동하면 잘못된 목표가 생긴다. "우리는 규제 산업이라 지속적 배포를 못 한다" 는 말은 맞을 수 있다. 하지만 그것이 "그러니 배포 가능한 상태를 유지할 필요도 없다" 로 이어지면, 분기마다 몇 주짜리 통합·안정화 단계를 치르는 예전 방식으로 돌아간다. 지속적 전달은 배포 빈도와 무관하게 가져야 할 능력이다.

## 핵심 개념

### 원전의 정의

Jez Humble 과 David Farley 의 책 *Continuous Delivery: Reliable Software Releases through Build, Test, and Deployment Automation*(Addison-Wesley, 2010)이 개념을 정리했다. Humble 이 운영하는 [continuousdelivery.com](https://continuousdelivery.com/)의 정의는 이렇다.

> 지속적 전달은 새 기능, 설정 변경, 버그 수정, 실험을 포함한 모든 종류의 변경을 안전하고 빠르며 지속 가능한 방식으로 운영 환경 또는 사용자 손에 전달하는 능력이다.

같은 페이지는 목표를 "배포를 예측 가능하고 일상적인 일로, 필요할 때 언제든 수행할 수 있게" 만드는 것이라 하고, 코드를 항상 배포 가능한 상태로 유지함으로써 "개발 완료" 뒤에 오던 통합·테스트·하드닝 단계와 코드 프리즈를 없앤다고 쓴다.

Martin Fowler 의 [ContinuousDelivery](https://martinfowler.com/bliki/ContinuousDelivery.html)(2013)는 판단 기준을 더 구체적으로 준다. Thoughtworks 의 CD 워킹 그룹이 만든 지표로, 다음을 만족하면 지속적 전달을 하고 있다.

| 지표 | 의미 |
|---|---|
| 생명주기 내내 배포 가능 | "배포 가능하게 만드는 단계" 가 따로 없다 |
| 새 기능보다 배포 가능 상태 유지를 우선 | 깨진 파이프라인이 기능 개발보다 먼저 |
| 누구든 변경 직후 운영 준비 상태에 대한 빠른 자동 피드백을 받음 | 파이프라인 결과가 공개되고 빠르다 |
| 어떤 버전이든 어떤 환경에든 버튼 하나로 배포 | 배포가 수작업 절차가 아니다 |

Fowler 가 제시하는 핵심 시험은 이것이다. 사업 책임자가 지금 개발 중인 버전을 당장 운영에 배포해 달라고 요청했을 때, **아무도 눈 하나 깜짝하지 않아야** 한다.

### 둘의 차이

같은 글에서 Fowler 는 경계를 분명히 긋는다. 지속적 배포는 모든 변경이 파이프라인을 거쳐 **자동으로 운영에 들어가** 하루에도 여러 번 운영 배포가 일어나는 것이고, 지속적 전달은 잦은 배포가 **가능하지만** 사업상 이유로 더 느린 속도를 선택할 수 있는 것이다. 그리고 지속적 배포를 하려면 지속적 전달을 하고 있어야 한다.

```
커밋 ─▶ 빌드 ─▶ 단위 테스트 ─▶ 통합/인수 테스트 ─▶ 스테이징 ─▶ [운영 배포]
 └──────────── 지속적 통합 ────────────┘
 └──────────────────── 지속적 전달 ─────────────────┘      ↑ 사람이 버튼
 └──────────────────── 지속적 배포 ───────────────────────────┘ 자동
```

| | 지속적 전달 | 지속적 배포 |
|---|---|---|
| 운영 반영 결정 | 사람(사업 판단) | 파이프라인 |
| 전제 | 항상 배포 가능 | 지속적 전달 + 충분한 자동 검증과 자동 복구 |
| 적합한 곳 | 규제·계약상 승인 필요, 모바일 앱 심사, 펌웨어 | 웹 서비스, 내부 API |
| 실패 비용 통제 | 배포 전 수동 확인 | 점진 배포, 자동 롤백, 피처 플래그 |

Agile 선언문의 [12원칙](https://agilemanifesto.org/principles.html) 첫 번째가 "가치 있는 소프트웨어를 일찍 그리고 지속적으로 전달(continuous delivery)해 고객을 만족시키는 것" 이라는 점도 기억할 만하다. 용어의 뿌리가 애자일에 있다.

### 배포 파이프라인

지속적 전달의 핵심 장치는 Fowler 가 [DeploymentPipeline](https://martinfowler.com/bliki/DeploymentPipeline.html)(2013)이라 부르는 것이다. 빌드를 여러 단계로 나누어, 각 단계가 대개 시간을 더 들이는 대가로 확신을 높인다. 앞 단계는 대부분의 문제를 빠르게 찾고, 뒤 단계는 느리지만 더 철저히 검사한다. 단계는 자동일 수도, 사람의 승인을 요구할 수도 있으며, 운영 배포는 보통 마지막 단계다. Fowler 는 보통 첫 단계가 컴파일을 하고 **이후 단계에 바이너리를 제공**한다고 설명한다. 여기서 실무 원칙 두 가지가 나온다.

1. **한 번 빌드한 산출물을 승격(promote)한다.** 스테이징에서 검증한 바이너리와 운영에 나가는 바이너리가 같아야 한다. 환경마다 다시 빌드하면 검증이 무의미해진다.
2. **환경 차이는 설정으로만.** 산출물은 같고 주입되는 설정만 다르다.

### 사례: IMVU 의 지속적 배포 (2009)

지속적 배포라는 말을 널리 알린 글 중 하나가 Timothy Fitz 의 [Continuous Deployment at IMVU: Doing the impossible fifty times a day](https://timothyfitz.com/2009/02/10/continuous-deployment-at-imvu-doing-the-impossible-fifty-times-a-day/)(2009)다. 글에 적힌 당시 구조는 이렇다.

- 커밋하면 모든 테스트를 자동 실행하고, 통과하면 클러스터에 배포한다.
- 테스트 스위트는 30~40대 머신에 분산되어 9분, 배포는 6분이 걸렸다. 평균적으로 하루 50번 배포했다.
- 약 15,000개의 테스트 케이스가 하루 약 70번 돌기 때문에, 테스트는 "백만 번에 한 번" 이하로만 실패해야 했다. 간헐적 실패 테스트를 고치는 일을 체계적으로 했다.
- 배포 스크립트는 기준 지표(부하, CPU, PHP 오류 등)를 샘플링한 뒤 일부 머신에만 새 코드를 올리고, 1분 뒤 통계적으로 유의한 악화가 있으면 **자동 롤백**했다. 문제가 없으면 전체로 확대하고 5분 더 감시했다.

이 사례에서 지속적 배포의 실제 조건이 보인다. 빠르고 **믿을 수 있는** 테스트, 그리고 배포 직후의 자동 감시와 자동 롤백. 마지막 부분은 카나리 배포(SE100 #056 에서 다룬다)의 초기 형태다.

### 무엇을 재는가

[DORA 의 소프트웨어 전달 성과 지표](https://dora.dev/guides/dora-metrics-four-keys/)는 원래의 네 가지에서 현재 다섯 가지로 바뀌었다. 처리량(throughput) 측에 변경 리드 타임, 배포 빈도, 실패한 배포의 복구 시간을, 불안정성(instability) 측에 변경 실패율과 **배포 재작업률(deployment rework rate, 운영 사고 때문에 생긴 계획에 없던 배포의 비율)** 을 둔다. 같은 문서는 DORA 연구가 속도와 안정성이 상충 관계가 아님을 반복해서 보였다고 쓰며, 지표를 목표로 삼으면 굿하트의 법칙에 따라 조작이 생긴다고 경고한다.

## 실무 적용

### 지속적 전달 자가 진단

```
[ ] main 의 최신 커밋을 지금 운영에 배포하라는 요청을 받아도 걱정이 없는가
[ ] 배포 절차가 문서가 아니라 스크립트/파이프라인인가
[ ] 스테이징과 운영에 같은 산출물(같은 다이제스트)이 나가는가
[ ] 이전 버전으로 되돌리는 절차가 버튼 하나인가, 연습해 본 적이 있는가
[ ] 실패한 파이프라인을 고치는 것이 새 기능 작업보다 우선인가
[ ] 간헐적으로 실패하는 테스트를 추적·격리·수정하는 규칙이 있는가
[ ] DB 스키마 변경이 애플리케이션 배포와 독립적으로 안전한가 (expand-contract)
```

### 승인 단계를 둔 지속적 전달 예 (GitHub Actions)

{% raw %}
```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    outputs:
      digest: ${{ steps.push.outputs.digest }}
    steps:
      - uses: actions/checkout@v4
      - run: ./gradlew test bootJar
      - id: push
        run: ./scripts/build-and-push.sh   # 이미지 다이제스트를 출력
  deploy-staging:
    needs: build
    environment: staging
    steps:
      - run: ./scripts/deploy.sh staging ${{ needs.build.outputs.digest }}
  deploy-prod:
    needs: [build, deploy-staging]
    environment: production    # 환경 보호 규칙으로 승인자 지정 → 지속적 전달
    steps:                     # 승인 규칙을 빼면 → 지속적 배포
      - run: ./scripts/deploy.sh prod ${{ needs.build.outputs.digest }}
```
{% endraw %}

지속적 전달과 지속적 배포의 차이가 파이프라인에서는 승인 규칙 한 줄이라는 점이 핵심이다. 그 한 줄을 지울 수 있느냐는 자동 검증과 자동 복구를 얼마나 믿을 수 있느냐에 달려 있다.

## 흔한 오해와 함정

- **"CD 는 배포 자동화 도구다."** 도구는 수단이다. 정의의 핵심은 코드가 **항상** 배포 가능한 상태라는 것이다.
- **"지속적 전달 = 매일 운영 배포."** 그것은 지속적 배포다. 지속적 전달은 배포 빈도가 아니라 배포 **능력**을 말한다.
- **환경별 재빌드.** 스테이징용과 운영용 빌드를 따로 하면 스테이징 검증이 운영 산출물을 보증하지 않는다.
- **승인 단계를 "안전장치" 로 착각.** 사람이 수백 줄의 변경을 몇 초 보고 승인하는 것은 실질적 검증이 아니다. 승인이 필요하다면 무엇을 보고 승인하는지 정의해야 한다.
- **불안정한 테스트 방치.** 간헐적 실패가 잦으면 사람들은 빨간 빌드를 무시하기 시작하고, 파이프라인의 신호가 사라진다. IMVU 사례가 테스트 신뢰성을 그토록 강조한 이유다.

## 확인 문제

1. Fowler 가 제시한 지속적 전달의 "핵심 시험" 은 무엇인가?
2. 지속적 전달과 지속적 배포의 차이를 "누가 운영 반영을 결정하는가" 의 관점에서 설명하라.
3. 모바일 앱처럼 스토어 심사가 필요한 제품에서도 지속적 전달이 의미 있는 이유는?
4. 파이프라인에서 "한 번 빌드해 승격한다" 는 원칙을 어기면 어떤 문제가 생기는가?
5. IMVU 사례에서 하루 50번 배포를 가능하게 한 조건 두 가지를 들어라.

### 풀이

1. 사업 책임자가 현재 개발 버전을 당장 운영에 배포해 달라고 해도 아무도 당황하지 않는 상태.
2. 지속적 전달에서는 파이프라인이 배포 가능한 산출물을 만들고 운영 반영은 사람이 사업 판단으로 결정한다. 지속적 배포에서는 파이프라인을 통과한 모든 변경이 자동으로 운영에 반영된다.
3. 지속적 전달은 배포 빈도가 아니라 언제든 내보낼 수 있는 능력이다. 심사 제출 시점을 자유롭게 고를 수 있고, 통합·안정화 단계가 없어지며, 긴급 수정도 즉시 준비된다.
4. 스테이징에서 검증한 산출물과 운영 산출물이 다를 수 있다. 빌드 환경·의존성 해석 차이로 운영에서만 나는 결함이 생겨도 검증이 막지 못한다.
5. 빠르고 매우 신뢰성 높은 자동 테스트(9분, 간헐 실패를 극도로 억제), 그리고 일부 머신 선배포 후 지표를 비교해 악화 시 자동 롤백하는 배포 스크립트.

## 더 읽을거리 (References)

- Jez Humble, David Farley, *Continuous Delivery: Reliable Software Releases through Build, Test, and Deployment Automation*, Addison-Wesley, 2010 (서지 정보)
- Jez Humble, [What is Continuous Delivery?](https://continuousdelivery.com/)
- Martin Fowler, [ContinuousDelivery](https://martinfowler.com/bliki/ContinuousDelivery.html), 2013
- Martin Fowler, [DeploymentPipeline](https://martinfowler.com/bliki/DeploymentPipeline.html)
- Timothy Fitz, [Continuous Deployment at IMVU: Doing the impossible fifty times a day](https://timothyfitz.com/2009/02/10/continuous-deployment-at-imvu-doing-the-impossible-fifty-times-a-day/), 2009
- DORA, [DORA's software delivery performance metrics](https://dora.dev/guides/dora-metrics-four-keys/)
- DORA, [Capabilities: Continuous delivery](https://dora.dev/capabilities/continuous-delivery/)
- [Principles behind the Agile Manifesto](https://agilemanifesto.org/principles.html)
- CS300: [CI/CD]({% post_url 2026-10-10-cs300-196-ci-cd %})
