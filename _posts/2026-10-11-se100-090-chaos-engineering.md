---
layout: post
title: "[SE100 #090] 카오스 엔지니어링"
date: 2026-10-11 17:08:59 +0900
categories: [software-engineering]
tags: [se100, quality-reliability, chaos-engineering, resilience, fault-injection]
---

소프트웨어 공학 100 주제 시리즈의 90번째 글이다. (카테고리: 품질·신뢰성·보안)

## 한 줄 요약

카오스 엔지니어링은 "서버를 무작위로 죽이는 것" 이 아니라, **정상 상태(steady state)에 대한 가설을 세우고 현실적인 장애를 주입해 그 가설을 반증하려는 통제된 실험**이다. 실험이 가설을 깨지 못할수록 시스템에 대한 확신이 커지고, 깨면 장애가 고객에게 닿기 전에 고칠 약점을 얻는다.

## 왜 필요한가

분산 시스템의 약점은 개별 구성요소가 아니라 **구성요소 사이의 상호작용**에 숨어 있다. [Principles of Chaos Engineering](https://principlesofchaos.org/) 은 그런 체계적 약점의 예로 서비스 불가 시의 부적절한 폴백 설정, 잘못 조정된 타임아웃으로 인한 재시도 폭풍, 하류 의존성에 몰린 과도한 트래픽으로 인한 장애, 단일 장애점 붕괴로 인한 연쇄 장애를 든다.

이런 약점은 단위 테스트로는 드러나지 않는다. 각 서비스는 자기 명세를 지키고 있기 때문이다. 통합 테스트 환경은 운영의 트래픽 패턴, 설정, 규모를 재현하지 못한다. 그리고 장애 대응 절차는 문서로만 있고 아무도 실행해 본 적이 없다. 결국 많은 조직이 이 약점들을 **실제 장애 날**에 처음 발견한다. 카오스 엔지니어링은 그 발견 시점을 우리가 고른 시간, 고른 범위로 앞당기는 방법이다.

## 핵심 개념

### 정의와 기원

Principles of Chaos Engineering 은 카오스 엔지니어링을 "운영 환경의 격동적인 조건을 견디는 시스템 능력에 대한 확신을 쌓기 위해 시스템에 실험하는 분야" 로 정의한다.

이 이름은 Netflix 에서 나왔다. Basiri 등의 [Chaos Engineering](https://doi.org/10.1109/MS.2016.60) (IEEE Software 33(3):35–41, 2016; [arXiv 판](https://arxiv.org/abs/1702.05843))에 따르면 Netflix 는 수년간 운영 서비스를 호스팅하는 가상 머신 인스턴스를 무작위로 골라 종료하는 내부 서비스 Chaos Monkey 를 운영했다. 목적은 엔지니어들이 개별 인스턴스 장애를 견디도록 서비스를 설계하게 만드는 것이었고, 엔지니어가 빨리 대응할 수 있도록 **평일 업무 시간에만** 동작했다. 이 성공이 확장되어, AWS 리전 전체 장애를 모사하는 Chaos Kong, 서비스 간 요청을 실패시켜 우아한 성능 저하를 확인하는 FIT(Failure Injection Testing)로 이어졌다. 논문은 이런 활동의 공통 원리를 정리해 "Chaos Engineering" 이라는 분야로 명명했다. Chaos Monkey 는 [오픈소스](https://github.com/Netflix/chaosmonkey)로 공개되어 있다.

### 테스트와 무엇이 다른가

같은 논문은 관점의 차이를 강조한다. 전통적 접근은 명세가 입력을 출력으로 어떻게 대응시키는지 정의하고 구현이 명세와 맞는지 묻는다. 그러나 분산 시스템에서 명세는 불완전하다. 카오스 엔지니어링은 **시스템 관점**을 택해, 운영 중인 서비스 집합을 하나의 시스템으로 보고 경계에서 측정한 지표의 정상 상태가 유지되는지를 묻는다. 원칙 문서의 표현으로는 "시스템이 **어떻게** 동작하는지 검증하기보다 시스템이 **동작한다**는 것을 확인한다."

| 구분 | 테스트 | 카오스 실험 |
|---|---|---|
| 질문 | 구현이 명세와 맞는가 | 장애 조건에서도 정상 상태가 유지되는가 |
| 결과 | 통과/실패 | 가설 반증 여부 + 새로운 지식 |
| 환경 | 주로 운영 이전 | 운영을 강하게 선호 (안전장치와 함께) |
| 대상 | 알려진 동작 | 알려지지 않은 상호작용 |

### 실험의 네 단계

```
 ① 정상 상태 정의  ──▶ ② 가설: 대조군과 실험군 모두 정상 상태 유지
        ▲                          │
        │                          ▼
 ⑤ 약점 개선 ◀── ④ 두 군의 차이로 가설 반증 시도 ◀── ③ 현실의 사건을 변수로 주입
```

1. **정상 상태 정의**: 정상 동작을 나타내는 측정 가능한 출력. Netflix 는 초당 스트림 시작 수(SPS)를 시스템 건강의 주 지표로 쓴다고 논문은 밝힌다.
2. **가설**: 대조군과 실험군 모두에서 정상 상태가 유지될 것이다.
3. **변수 주입**: 서버 크래시, 디스크 고장, 네트워크 단절 같은 현실 사건.
4. **반증 시도**: 두 군의 정상 상태 차이를 찾는다.

### 고급 원칙 다섯 가지

원칙 문서는 다음을 이상적인 적용으로 든다.

| 원칙 | 요지 | 실무 해석 |
|---|---|---|
| 정상 상태 행동에 가설을 세운다 | 내부 속성이 아니라 측정 가능한 출력(처리량, 오류율, 지연 백분위)에 집중 | CPU 가 아니라 SLI 를 본다 (SE100 #084) |
| 현실 사건을 다양화한다 | 영향이나 빈도로 우선순위. 하드웨어·소프트웨어 고장뿐 아니라 트래픽 급증 같은 비고장 사건도 | 과거 사후 분석 목록이 최고의 출발점 |
| 운영에서 실험한다 | 실제 트래픽 표본만이 요청 경로를 믿을 만하게 포착 | 운영 이전에서 시작해 점진적으로 |
| 자동화해 지속 실행한다 | 수동 실험은 지속 불가능 | 배포 파이프라인·정기 스케줄 |
| 폭발 반경을 최소화한다 | 고객 영향을 최소화·격리하는 것은 실험자의 책임 | 소수 트래픽, 자동 중단 조건 |

### 도구

| 도구 | 성격 |
|---|---|
| [Chaos Monkey](https://netflix.github.io/chaosmonkey/) | 운영 인스턴스 무작위 종료 (Spinnaker 연동) |
| [Chaos Mesh](https://chaos-mesh.org/) | 쿠버네티스용 카오스 플랫폼. [CNCF](https://www.cncf.io/projects/chaosmesh/) 에 2020-07-14 합류, 2022-02-16 인큐베이팅 |
| [LitmusChaos](https://litmuschaos.io/) | 오픈소스 카오스 엔지니어링 플랫폼. [CNCF](https://www.cncf.io/projects/litmus/) 에 2020-06-25 합류, 인큐베이팅 |
| [AWS FIS](https://docs.aws.amazon.com/fis/latest/userguide/what-is.html) | AWS 관리형 결함 주입 서비스. CloudWatch 알람 기반 **중단 조건(stop condition)** 제공 |

## 실무 적용

### 실험 설계서

```markdown
# 실험 CE-007: 추천 서비스 지연 시 홈 화면
- 정상 상태(SLI): 홈 API 성공률 ≥ 99.9%, p99 지연 ≤ 800ms (5분 창)
- 가설: 추천 서비스에 500ms 지연이 생겨도 홈 API 는 타임아웃(300ms) 후
        기본 추천으로 폴백하므로 정상 상태가 유지된다.
- 변수: recommendation 파드 1개에 네트워크 지연 500ms (5분)
- 폭발 반경: 카나리 셀 1개 (전체 트래픽의 약 1%), 업무 시간, 담당자 대기
- 중단 조건: 홈 API 성공률 < 99.5% 가 1분 지속 또는 에러 버짓 2% 소모 시 즉시 중단
- 롤백: 실험 리소스 삭제 (kubectl delete), 확인 담당 @oncall
- 결과 기록: 가설 유지/반증, 발견한 약점, 후속 티켓
```

중단 조건을 SLO 와 에러 버짓에 묶어 두면 "실험이 얼마나 위험해도 되는가" 가 별도 협상 없이 정해진다.

### Chaos Mesh 로 지연 주입

[Chaos Mesh 문서의 NetworkChaos 예](https://chaos-mesh.org/docs/simulate-network-chaos-on-kubernetes/)를 실험 설계에 맞게 고친 것이다.

```yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: NetworkChaos
metadata:
  name: ce-007-reco-delay
  namespace: shop
spec:
  action: delay
  mode: one                 # 대상 중 파드 하나만
  selector:
    namespaces: [shop]
    labelSelectors:
      app: recommendation
  delay:
    latency: '500ms'
    correlation: '100'
    jitter: '0ms'
  duration: '5m'
```

### 중단 조건이 있는 실험 루프

```python
import random

def home_success_rate(group, injected):          # 실제로는 메트릭 조회
    base = 0.9995
    if group == "experiment" and injected:
        base -= random.uniform(0.002, 0.008)     # 폴백이 불완전하면 떨어진다
    return base

def run(minutes=5, abort_below=0.995, seed=7):
    random.seed(seed)
    for m in range(1, minutes + 1):
        ctl = home_success_rate("control", True)
        exp = home_success_rate("experiment", True)
        print(f"{m}분: 대조군 {ctl:.4f}  실험군 {exp:.4f}")
        if exp < abort_below:
            return f"중단: 실험군 성공률 {exp:.4f} < {abort_below} → 가설 반증, 폴백 점검"
    return "가설 유지: 차이가 허용 범위 안"

print(run())
```

실행하면 몇 분 안에 실험군 성공률이 중단 기준 아래로 내려가 실험이 멈춘다. 이것은 실패가 아니라 **성공한 실험**이다. 고객 1% 에게 몇 분 동안 생긴 영향으로, 폴백이 기대대로 작동하지 않는다는 사실을 알아냈기 때문이다.

### 게임 데이와 함께

AWS Well-Architected 의 [REL12-BP05](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_testing_resiliency_game_days_resiliency.html) 는 실제 상황을 처리할 같은 팀이 참여하는 게임 데이를 정기적으로 열어 대응 절차를 연습하라고 권하고, 절차를 문서화만 하고 연습하지 않는 것을 안티패턴으로 든다. 카오스 실험이 **시스템**의 약점을 찾는다면 게임 데이는 **사람과 절차**의 약점을 찾는다. 경보가 올바른 사람에게 갔는가, 런북대로 했을 때 복구되는가(SE100 #083 의 MTTR 분해).

### 시작 순서

1. 관측 가능성부터: 정상 상태를 측정할 수 없으면 실험도 없다(SE100 #085).
2. 운영 이전 환경에서, 이미 결과를 안다고 생각하는 실험부터. 대개 그 "안다" 가 틀린다.
3. 과거 장애 사후 분석의 원인을 재현하는 실험으로 개선 조치를 검증한다.
4. 운영에서는 카나리 범위, 업무 시간, 자동 중단 조건과 함께.
5. 통과한 실험을 자동화해 회귀 방지 장치로 만든다.

## 흔한 오해와 함정

- **"무작위로 부수는 것"** — 가설·측정·중단 조건 없는 장애 주입은 실험이 아니라 사고 유발이다.
- **"운영에서 바로 해야 진짜"** — 원칙은 운영을 선호하지만 폭발 반경 최소화와 함께다. 관측·롤백 준비가 안 된 조직이 운영부터 시작하면 신뢰만 잃는다.
- **약점을 찾고 고치지 않음** — 실험 결과가 백로그에 묻히면 같은 장애를 운영에서 다시 만난다. 후속 조치를 실험 종료 조건에 넣는다.
- **인프라 장애만 주입** — 원칙은 잘못된 응답 같은 소프트웨어 고장, 트래픽 급증 같은 비고장 사건도 변수로 든다. 설정 값 오류, 의존 API 의 느린 응답이 실제로 더 흔한 원인이다.
- **실험군만 관찰** — 대조군 없이 보면 같은 시간대의 다른 변화(배포, 트래픽 변동)를 실험 효과로 착각한다.

## 확인 문제

1. Principles of Chaos Engineering 의 정의에서 카오스 엔지니어링의 목적은 무엇인가?
2. 실험의 정상 상태로 CPU 사용률보다 SPS 나 성공률 같은 지표가 나은 이유는?
3. Chaos Monkey 가 평일 업무 시간에만 동작한 이유는?
4. 위 실험 루프가 중단으로 끝났을 때 이를 "성공한 실험" 이라 부르는 이유는?
5. 카오스 실험과 게임 데이가 각각 주로 찾는 약점은?

### 풀이

1. 운영 환경의 격동적인 조건을 견디는 시스템 능력에 대한 확신을 쌓는 것.
2. 원칙은 내부 속성이 아니라 시스템의 측정 가능한 출력에 가설을 세우라고 한다. 사용자 경험을 직접 반영하는 출력 지표여야 "시스템이 동작한다" 를 확인할 수 있다. CPU 는 원인 후보일 뿐 사용자 영향과 일대일이 아니다.
3. 인스턴스 종료로 서비스가 실패하면 엔지니어가 빠르게 대응할 수 있게 하기 위해서다.
4. 실험의 목적은 가설을 반증할 수 있는지 보는 것이다. 통제된 작은 범위에서 폴백 결함이라는 약점을 발견했으므로, 실제 장애 전에 고칠 대상을 얻었다.
5. 카오스 실험은 시스템 설계·구성의 약점(폴백, 타임아웃, 의존성), 게임 데이는 사람과 절차의 약점(경보 전달, 런북, 의사결정)을 주로 찾는다.

## 더 읽을거리 (References)

- [Principles of Chaos Engineering](https://principlesofchaos.org/) (2019년 3월 갱신판)
- A. Basiri et al., [Chaos Engineering](https://doi.org/10.1109/MS.2016.60), IEEE Software 33(3):35–41, 2016 ([arXiv:1702.05843](https://arxiv.org/abs/1702.05843))
- Netflix, [Chaos Monkey (GitHub)](https://github.com/Netflix/chaosmonkey), [문서](https://netflix.github.io/chaosmonkey/)
- [Chaos Mesh 문서 — Simulate Network Faults](https://chaos-mesh.org/docs/simulate-network-chaos-on-kubernetes/), [CNCF 프로젝트 페이지](https://www.cncf.io/projects/chaosmesh/)
- [LitmusChaos](https://litmuschaos.io/), [CNCF 프로젝트 페이지](https://www.cncf.io/projects/litmus/)
- AWS, [What is AWS Fault Injection Service?](https://docs.aws.amazon.com/fis/latest/userguide/what-is.html)
- AWS, [REL12-BP05 Conduct game days regularly](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_testing_resiliency_game_days_resiliency.html)
