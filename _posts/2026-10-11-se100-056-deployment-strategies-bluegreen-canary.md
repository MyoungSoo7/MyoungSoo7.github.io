---
layout: post
title: "[SE100 #056] 배포 전략 — 롤링·블루그린·카나리"
date: 2026-10-11 17:03:39 +0900
categories: [software-engineering]
tags: [se100, delivery, deployment-strategies, blue-green, canary-release]
---

소프트웨어 공학 100 주제 시리즈의 56번째 글이다. (카테고리: 형상 관리와 전달)

## 한 줄 요약

배포 전략은 "새 버전이 잘못되었을 때 피해를 얼마나 작게, 얼마나 빨리 되돌릴 수 있는가" 를 설계하는 일이다. 롤링은 자원을 아끼며 점진 교체하고, 블루그린은 두 환경을 통째로 전환해 즉시 되돌리며, 카나리는 일부 트래픽에만 먼저 내보내 **비교 측정**으로 판정한다.

## 왜 필요한가

지속적 전달(SE100 #055 에서 다룬다)이 "언제든 배포할 수 있는 능력" 이라면, 배포 전략은 "배포해도 괜찮은 이유" 다. 테스트는 운영의 모든 것을 재현하지 못한다. 실제 트래픽 패턴, 실제 데이터 분포, 다른 서비스와의 상호작용에서만 드러나는 결함이 반드시 있다. 그렇다면 남는 질문은 결함이 운영에 닿았을 때 **몇 명의 사용자가, 몇 분 동안** 영향을 받느냐다.

모든 서버를 한꺼번에 내리고 새 버전을 올리는 방식은 다운타임이 생기고, 결함이 있으면 100% 사용자가 즉시 영향을 받으며, 되돌리는 데 배포와 같은 시간이 걸린다. 아래 세 전략은 이 세 문제를 서로 다른 비용으로 해결한다.

## 핵심 개념

### 재생성(Recreate)과 롤링 업데이트

Kubernetes [Deployment](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/)는 두 전략 타입을 제공한다.

- `Recreate`: 새 파드를 만들기 전에 기존 파드를 모두 죽인다. 다운타임이 생기지만 두 버전이 동시에 돌지 않는다. 구버전과 신버전이 공존하면 안 되는 경우(예: 호환되지 않는 스키마를 단독으로 쓰는 경우)에 쓴다.
- `RollingUpdate`(기본값): 파드를 점진적으로 교체한다. 두 파라미터가 속도와 안전을 조절한다.

| 파라미터 | 의미 | 기본값 |
|---|---|---|
| `maxUnavailable` | 교체 중 원하는 수보다 모자라도 되는 파드 수(또는 비율) | 25% |
| `maxSurge` | 교체 중 원하는 수보다 더 띄워도 되는 파드 수(또는 비율) | 25% |

문서의 설명대로 기본값이면 원하는 파드 수의 최소 75% 가 떠 있고, 최대 125% 까지 띄운다.

```
replicas=4, maxSurge=25%(1), maxUnavailable=25%(1)

시작   [v1][v1][v1][v1]
1단계  [v1][v1][v1][v1][v2]        surge 로 v2 하나 추가
2단계  [v1][v1][v1]   [v2]         v2 준비(readiness) 확인 후 v1 하나 제거
...
완료   [v2][v2][v2][v2]
```

롤링의 핵심은 **준비 상태 판정(readiness probe)** 이다. 새 파드가 실제로 요청을 처리할 준비가 되었을 때만 다음 단계로 간다. 프로브가 부실하면 롤링은 고장 난 파드로 차례차례 교체하는 장치가 된다. 진행이 멈추면 `progressDeadlineSeconds`(기본 600초) 이후 Deployment 가 진행 실패를 보고한다.

롤링의 한계는 둘이다. 교체 중에는 **두 버전이 동시에 트래픽을 받으므로** 버전 간 호환성이 필수이고, 되돌리기도 다시 롤링이라 시간이 걸린다.

### 블루그린 배포

Martin Fowler 의 [BlueGreenDeployment](https://martinfowler.com/bliki/BlueGreenDeployment.html)(2010)는 이렇게 설명한다. 운영 환경을 **가능한 한 동일하게** 두 벌 둔다. 한쪽(블루)이 운영 중일 때 다른 쪽(그린)에서 새 릴리스의 마지막 테스트를 하고, 문제가 없으면 라우터를 전환해 모든 요청을 그린으로 보낸다. 문제가 생기면 라우터를 다시 블루로 돌리면 된다.

```
           ┌──────────┐
 사용자 ──▶ │  라우터   │──┐
           └──────────┘  │ (전환 = 포인터 한 번)
                ┌────────┴────────┐
                ▼                 ▼
         [블루 v1: 운영]     [그린 v2: 대기·검증]
                └──── 공유 DB ────┘
```

Fowler 가 직접 지적하는 어려움은 **전환 중의 트랜잭션**이다. 그린이 운영되는 동안 들어온 트랜잭션을 블루로 되돌릴 때 놓칠 수 있다. 글은 두 환경에 트랜잭션을 함께 넣거나, 전환 전에 애플리케이션을 읽기 전용 모드로 잠시 운영하는 방법을 언급한다. 그리고 전환이 끝나면 이전 환경은 다음 릴리스의 스테이징이 되어, 두 환경이 운영·롤백 대기·다음 버전 준비 사이를 번갈아 순환한다.

| 장점 | 비용 |
|---|---|
| 전환과 롤백이 즉시 | 운영 용량 두 배 (전환 전후 일시적으로라도) |
| 전환 전에 운영 동등 환경에서 최종 검증 | DB 스키마가 두 버전 모두와 호환되어야 함 |
| 두 버전이 동시에 트래픽을 받지 않음 | 장기 연결·세션·캐시 워밍 처리 필요 |

### 카나리 릴리스

Danilo Sato 의 [CanaryRelease](https://martinfowler.com/bliki/CanaryRelease.html)(2014)는 카나리 릴리스를 "새 버전을 전체에 내보내기 전에 소수의 사용자에게 먼저 내보내 운영에 변경을 도입하는 위험을 줄이는 기법" 으로 정의한다. 이름은 유독 가스를 먼저 감지하도록 탄광에 데려가던 카나리아에서 왔다.

Google 의 [SRE Workbook 의 Canarying Releases 장](https://sre.google/workbook/canarying-releases/)은 더 엄밀한 정의를 준다.

> 카나리잉은 서비스 변경의 **부분적이고 시간 제한적인** 배포와 그 평가다.

변경을 받은 부분이 "카나리", 나머지가 "대조군(control)" 이다. 핵심은 카나리를 **과거 값이 아니라 같은 시간대의 대조군과 비교**한다는 점이다. 그래야 트래픽 변동이나 다른 원인으로 인한 지표 변화를 변경의 효과와 구분할 수 있다.

같은 장의 오류 예산 계산이 카나리의 가치를 정량적으로 보여 준다. 새 버전이 요청의 20% 를 실패시키는 결함을 가졌다고 하자. 카나리 모집단이 트래픽의 5% 라면 전체 오류율은 20% × 5% = 1% 에 그친다. 카나리 크기와 시간이 오류 예산 소모의 상한을 정한다.

카나리 설계에서 정할 것:

| 결정 | 고려 사항 |
|---|---|
| 모집단 크기 | 작을수록 안전하지만 신호가 약해 판정이 느리다 |
| 기간 | 배포 빈도와 맞아야 한다. 하루 여러 번 배포하면 카나리 기간도 짧아야 한다 |
| 평가 지표 | 오류율·지연 같은 빠른 지표, 큐 깊이 같은 느린 지표 |
| 판정 | 자동 분석(통계 비교) 후 진행·중단·롤백 |

### 점진적 전달 도구

이런 전략을 Kubernetes 위에서 선언적으로 표현하는 도구가 있다. [Argo Rollouts](https://argoproj.github.io/argo-rollouts/)는 블루그린, 카나리, 카나리 분석, 실험, 점진적 전달 기능을 제공하는 Kubernetes 컨트롤러와 CRD 묶음이다. [Flagger](https://docs.flagger.app/)도 비슷한 역할을 한다.

## 예제

### Argo Rollouts 카나리 단계 정의

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: order
spec:
  replicas: 10
  strategy:
    canary:
      steps:
        - setWeight: 5          # 트래픽 5% 를 카나리로
        - pause: {duration: 10m}
        - analysis:             # 대조군 대비 오류율·지연 자동 비교
            templates:
              - templateName: error-rate-vs-stable
        - setWeight: 25
        - pause: {duration: 10m}
        - setWeight: 50
        - pause: {duration: 10m}
        # 분석이 실패하면 자동으로 중단하고 안정 버전으로 되돌린다
  selector:
    matchLabels: {app: order}
  template:
    metadata:
      labels: {app: order}
    spec:
      containers:
        - name: order
          image: registry.example.com/order@sha256:<digest>
```

### 전략 선택 가이드

```
두 버전 공존이 불가능한가? ─ 예 ─▶ Recreate (또는 블루그린 + 유지보수 창)
        │ 아니오
        ▼
즉시 롤백이 반드시 필요하고 용량 2배를 감당할 수 있는가? ─ 예 ─▶ 블루그린
        │ 아니오
        ▼
의미 있는 지표와 자동 비교가 가능한가? ─ 예 ─▶ 카나리 (+ 자동 분석)
        │ 아니오
        ▼
롤링 업데이트 + 견고한 readiness probe + 빠른 수동 롤백 절차
```

## 흔한 오해와 함정

- **"블루그린이면 DB 도 두 벌."** 대부분 DB 는 공유한다. 그래서 스키마 변경은 두 버전 모두와 호환되게 expand-contract 로 나눠야 한다. DB 까지 두 벌이면 데이터 동기화라는 더 큰 문제가 생긴다.
- **"카나리 = 트래픽 일부 보내기."** 비교 판정 없이 일부만 보내는 것은 그냥 느린 배포다. 카나리의 본질은 **대조군 대비 평가**다.
- **카나리 지표 선택 실수.** 카나리 5% 의 오류가 전체 평균 지표에 묻혀 보이지 않을 수 있다. 카나리와 대조군을 **분리해서** 측정해야 한다.
- **readiness probe 없는 롤링.** 프로세스가 떴다는 것과 요청을 처리할 수 있다는 것은 다르다.
- **롤백 경로를 시험하지 않음.** 블루그린의 장점은 전환 스위치가 실제로 동작할 때만 있다. 정기적으로 되돌려 본다.
- **세션·연결 무시.** 장기 연결(WebSocket, gRPC 스트림)은 라우터 전환 후에도 이전 버전에 남는다. 연결 드레이닝 시간을 설계한다.

## 확인 문제

1. Kubernetes Deployment 의 `maxSurge` 와 `maxUnavailable` 기본값은 무엇이며, replicas=8 일 때 교체 중 파드 수의 범위는?
2. 블루그린 배포에서 Fowler 가 지적한 "전환 중 트랜잭션" 문제는 무엇이고, 어떤 대처가 언급되는가?
3. SRE Workbook 의 정의에서 카나리잉의 두 핵심 성질은 무엇인가?
4. 결함이 요청의 40% 를 실패시키고 카나리 모집단이 2% 라면, 카나리 기간 동안 전체 오류율은 얼마인가?
5. 카나리를 대조군이 아닌 "어제 같은 시간" 과 비교하면 어떤 문제가 생기는가?

### 풀이

1. 둘 다 25%. replicas=8 이면 최소 6개(75%)가 가용 상태이고, 최대 10개(125%)까지 존재할 수 있다.
2. 그린으로 전환한 뒤 블루로 되돌리면 그린이 운영하던 동안의 트랜잭션을 놓칠 수 있다. 두 환경에 트랜잭션을 함께 보내거나, 전환 전에 읽기 전용 모드로 잠시 운영하는 방법이 언급된다.
3. 부분적(서비스 일부에만)이고 시간 제한적인 배포, 그리고 그에 대한 평가.
4. 40% × 2% = 0.8%.
5. 트래픽 양·사용자 구성·다른 배포 등 시간에 따라 달라지는 요인이 섞여, 지표 변화가 변경 때문인지 구분할 수 없다. 같은 시간대의 대조군과 비교해야 다른 요인이 상쇄된다.

## 더 읽을거리 (References)

- Martin Fowler, [BlueGreenDeployment](https://martinfowler.com/bliki/BlueGreenDeployment.html), 2010
- Danilo Sato, [CanaryRelease](https://martinfowler.com/bliki/CanaryRelease.html), 2014
- Google, [The Site Reliability Workbook — Canarying Releases](https://sre.google/workbook/canarying-releases/)
- Kubernetes, [Deployments](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/)
- Kubernetes, [Configure Liveness, Readiness and Startup Probes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/)
- [Argo Rollouts](https://argoproj.github.io/argo-rollouts/)
- [Flagger](https://docs.flagger.app/)
- CS300: [파드, 디플로이먼트, 서비스]({% post_url 2026-10-10-cs300-227-pods-deployments-services %})
