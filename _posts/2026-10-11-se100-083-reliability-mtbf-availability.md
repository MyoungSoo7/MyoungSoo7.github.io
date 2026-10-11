---
layout: post
title: "[SE100 #083] 신뢰성 공학 — MTBF·MTTR·가용성"
date: 2026-10-11 17:08:51 +0900
categories: [software-engineering]
tags: [se100, quality-reliability, reliability, mtbf, mttr, availability]
---

소프트웨어 공학 100 주제 시리즈의 83번째 글이다. (카테고리: 품질·신뢰성·보안)

## 한 줄 요약

신뢰성은 "정해진 시간 동안 고장 없이 동작할 확률" 이고, 가용성은 "필요할 때 쓸 수 있는 비율" 이다. 정상 상태 가용성은 MTBF/(MTBF+MTTR) 로 근사되며, 이 식은 **고장을 줄이는 것만큼 복구를 빠르게 하는 것**이 중요하다는 사실을 숫자로 보여 준다.

## 왜 필요한가

"서비스가 안정적이어야 한다" 는 요구사항은 측정할 수 없다. 측정할 수 없으면 다음 질문에 답할 수 없다.

- 이중화에 돈을 쓸 것인가, 장애 탐지 자동화에 쓸 것인가?
- 외부 결제 API 의 가용성이 우리 서비스 가용성의 상한을 얼마로 묶는가?
- 지난달 장애 세 번은 "많은" 것인가?

신뢰성 공학은 하드웨어·항공·통신 분야에서 오래 다듬어진 정량 어휘를 준다. 소프트웨어에 그대로 맞지 않는 부분도 있지만, 어휘와 계산 습관만으로도 위 질문들이 "느낌" 에서 "트레이드오프" 로 바뀐다.

## 핵심 개념

### 신뢰도 함수와 고장률

시점 0 에 정상인 시스템이 시간 t 까지 고장 나지 않을 확률을 **신뢰도 함수** R(t) 라 한다. 순간 고장률(hazard rate)을 h(t) 라 할 때 가장 단순한 모델은 고장률이 상수 λ 인 **지수 분포**다. [NIST/SEMATECH e-Handbook](https://www.itl.nist.gov/div898/handbook/apr/section1/apr161.htm) 이 정리한 식은 다음과 같다.

$$R(t) = e^{-\lambda t}, \qquad h(t) = \lambda, \qquad \mathrm{MTTF} = \frac{1}{\lambda}$$

지수 분포는 고장률이 상수인 **유일한** 분포이고, 그래서 "지금까지 얼마나 오래 돌았는지" 가 다음 고장 확률에 영향을 주지 않는다(무기억성). 같은 NIST 핸드북은 많은 제품의 고장률이 시간에 따라 [욕조 곡선(bathtub curve)](https://www.itl.nist.gov/div898/handbook/apr/section1/apr124.htm) 을 그린다고 설명한다. 초기 고장기(감소), 고장률이 거의 일정한 내재 고장기, 마모 고장기(증가)다. 지수 모델은 그중 평평한 구간의 모델이다.

```
 고장률 h(t)
   │╲                                    ╱
   │ ╲                                 ╱
   │  ╲______________________________╱
   │  초기 고장기     내재(안정) 고장기     마모 고장기
   └──────────────────────────────────────────▶ 시간
```

소프트웨어는 물리적으로 마모되지 않지만, 배포 직후 결함이 집중적으로 드러나는 모습은 초기 고장기와 닮았고, 변경이 쌓이며 구조가 망가지는 모습은 일종의 마모처럼 보인다. 비유는 쓸모 있지만 소프트웨어 고장률이 이 곡선을 따른다는 정량적 근거로 쓰지는 않는다.

### MTTF, MTBF, MTTR

| 용어 | 의미 | 쓰는 대상 |
|---|---|---|
| MTTF (Mean Time To Failure) | 고장까지의 평균 시간 | 수리하지 않는(교체하는) 대상 |
| MTBF (Mean Time Between Failures) | 수리 후 다음 고장까지의 평균 정상 가동 시간 | 수리 가능한 시스템 |
| MTTR (Mean Time To Repair/Recover) | 고장 후 정상 복귀까지의 평균 시간 | 수리 가능한 시스템 |

MTTR 의 R 은 조직마다 Repair, Recover, Restore, Resolve 등으로 다르게 쓴다. "근본 수정 배포까지" 와 "사용자 영향 해소까지" 는 몇 배씩 차이가 나므로, 지표를 비교하기 전에 **시계가 언제 시작하고 언제 멈추는지**부터 맞춰야 한다. 실무에서는 MTTR 을 탐지(MTTD), 진단, 완화로 쪼개 보는 편이 개선 지점을 찾기 쉽다.

```
 정상 ──────────────▶ 고장 ─(탐지)─▶ 알림 ─(진단)─▶ 원인 파악 ─(완화)─▶ 정상 복귀
      ◀── MTBF ──▶        ◀──────────────────── MTTR ───────────────────▶
```

### 가용성

수리 가능한 시스템이 "올라와 있는" 시간의 비율이 가용성이다. 정상 상태에서

$$A = \frac{\mathrm{MTBF}}{\mathrm{MTBF} + \mathrm{MTTR}}$$

[AWS Well-Architected 신뢰성 기둥](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/availability.html)은 이 식의 예로 MTBF 150일, MTTR 1시간이면 가용성 추정치가 99.97% 라고 든다. 이 식에서 바로 보이는 것이 있다. MTBF 를 두 배로 늘리는 것과 MTTR 을 절반으로 줄이는 것은 가용성에 **같은 효과**를 낸다. 대부분의 소프트웨어 조직에서 고장을 절반으로 줄이는 것보다 롤백 자동화로 복구 시간을 절반으로 줄이는 것이 훨씬 싸다.

### "9 의 개수" 와 두 가지 측정법

[Google SRE 책의 Embracing Risk 장](https://sre.google/sre-book/embracing-risk/)은 가용성을 두 방식으로 정의한다.

- **시간 기반**: 가동 시간 / (가동 시간 + 중단 시간). 이 기준으로 99.99% 는 1년에 최대 52.56분 중단이다.
- **요청 기반(aggregate availability)**: 성공한 요청 / 전체 요청. 하루 250만 요청에 일일 목표 99.99% 라면 그날 오류 250건까지 허용된다.

전 세계에 분산된 서비스는 어딘가에서는 늘 일부 트래픽을 처리하고 있어 "다운" 을 정의하기 어렵기 때문에, 같은 장은 요청 기반 측정이 더 의미 있다고 설명한다. 이 관점은 SLI·SLO 설계로 이어진다(SE100 #084).

### 직렬과 병렬

AWS 문서는 의존성 구성에 따른 계산도 제시한다.

- **경성 의존(hard dependency, 직렬)**: 의존 대상이 하나라도 멈추면 같이 멈춘다. 가용성은 곱이다. 99.99% 시스템이 99.99% 독립 의존 두 개에 경성 의존하면 99.99%×99.99%×99.99% ≈ 99.97%.
- **독립 중복(병렬)**: 하나만 살아 있으면 된다. 가용성은 1 − Π(1 − Aᵢ). 99.9% 독립 구성요소 두 개면 99.9999%.

$$A_{\text{serial}} = \prod_i A_i, \qquad A_{\text{parallel}} = 1 - \prod_i (1 - A_i)$$

두 식 모두 **고장이 서로 독립**이라는 가정에 기대고 있다. 같은 설정 실수, 같은 버전의 버그, 같은 리전 장애는 이중화된 구성요소를 동시에 쓰러뜨린다. 이것이 병렬 계산이 현실보다 낙관적인 가장 흔한 이유다.

### 소프트웨어 고장의 성격

Jim Gray 는 Tandem 기술 보고서 *Why Do Computers Stop and What Can Be Done About It?* (TR 85.7, 1985)에서 재현이 잘 되는 결함과, 타이밍·상태에 따라 나타났다 사라지는 일시적 결함을 구분했다. 후자는 프로세스를 재시작하거나 다른 복제본으로 넘기면 대개 사라진다. 재시작·재시도·페일오버 같은 **복구 메커니즘**이 소프트웨어 가용성에 크게 기여하는 이유가 이것이다. 동시에, 결정적 버그는 이중화해도 모든 복제본에서 똑같이 터진다.

## 실무 적용

### 가용성 예산 계산기

```python
from math import prod

def serial(*a):   return prod(a)
def parallel(*a): return 1 - prod(1 - x for x in a)
def from_mtbf(mtbf_h, mttr_h): return mtbf_h / (mtbf_h + mttr_h)
def downtime_min_per_year(a): return (1 - a) * 365 * 24 * 60

api      = 0.9995
db       = parallel(0.999, 0.999)        # 독립 복제본 2개라고 가정
payment  = 0.999                         # 외부 결제 API (경성 의존)
service  = serial(api, db, payment)
print(f"전체 {service:.5f} → 연간 중단 약 {downtime_min_per_year(service):.0f}분")

# 결제를 비동기 큐로 바꿔 경성 의존을 끊으면
service2 = serial(api, db)
print(f"결제 연성화 {service2:.5f} → 연간 중단 약 {downtime_min_per_year(service2):.0f}분")

# MTBF 두 배 vs MTTR 절반: 같은 효과
print(f"{from_mtbf(720, 2):.5f} {from_mtbf(1440, 2):.5f} {from_mtbf(720, 1):.5f}")
```

실행하면 전체 가용성이 약 0.9985(연간 약 790분 중단)로, 결제 API 하나가 상한을 묶고 있음이 보인다. 결제 호출을 비동기로 돌려 **경성 의존을 연성 의존으로** 바꾸면 약 0.9995(연간 약 260분)로 오른다. 이중화보다 의존성 구조 변경이 더 큰 레버인 경우가 많다. 마지막 줄은 MTBF 를 두 배로 하는 것과 MTTR 을 절반으로 하는 것이 같은 값을 낸다는 것을 확인한다.

### MTTR 을 줄이는 체크리스트

- 탐지: 사용자 관점 지표(오류율, 지연)에 경보가 걸려 있는가, 아니면 CPU 같은 원인 지표에만 걸려 있는가
- 진단: 배포·설정 변경 이력이 대시보드에 겹쳐 보이는가
- 완화: 롤백이 한 명령으로 되는가, 기능 플래그로 끌 수 있는가, 트래픽을 다른 곳으로 뺄 수 있는가
- 연습: 위 절차를 실제로 해 본 적이 있는가(SE100 #090)

관련 기초는 CS300 [백업과 재해 복구]({% post_url 2026-10-10-cs300-237-backup-and-disaster-recovery %}), [분산 컴퓨팅의 오류들]({% post_url 2026-10-10-cs300-129-fallacies-of-distributed-computing %}) 에서 다뤘다.

## 흔한 오해와 함정

- **"MTBF 가 10만 시간이면 10만 시간 동안 안 고장 난다"** — MTBF 는 평균이다. 지수 모델에서 t = MTTF 시점의 생존 확률은 e⁻¹, 즉 약 37% 뿐이다.
- **평균 하나로 판단** — MTTR 평균 30분이라도 대부분 5분이고 한 번이 6시간일 수 있다. 분포(최댓값, 상위 백분위)를 같이 본다.
- **독립 가정의 남용** — 같은 이미지, 같은 설정, 같은 컨트롤 플레인을 공유하면 "이중화" 는 계산만큼 효과가 없다.
- **부분 장애 무시** — 시간 기반 가용성은 "10% 사용자만 실패" 를 놓친다. 요청 기반 측정이 이를 잡는다.
- **가용성 = 신뢰성** — 하루에 1초씩 1000번 멈추는 시스템은 가용성은 높지만 신뢰성(연속 무고장 시간)은 낮다. 긴 배치 작업에는 후자가 중요하다.

## 확인 문제

1. MTBF 300시간, MTTR 3시간인 시스템의 정상 상태 가용성은? MTTR 을 30분으로 줄이면?
2. 각각 99.9% 인 서비스 세 개에 직렬로 경성 의존하는 시스템의 가용성 상한은 대략 얼마인가?
3. 시간 기반 가용성이 분산 서비스에서 덜 의미 있는 이유는?
4. 병렬 이중화 계산이 현실보다 낙관적이 되는 대표적 이유 두 가지는?

### 풀이

1. 300/303 ≈ 0.9901(약 99.01%). MTTR 0.5시간이면 300/300.5 ≈ 0.99834(약 99.83%).
2. 0.999³ ≈ 0.997, 약 99.7%.
3. 일부 지역·일부 사용자만 실패하는 부분 장애가 흔해 "올라와 있다/내려가 있다" 의 이분법이 맞지 않는다. 성공 요청 비율이 사용자 경험을 더 잘 반영한다.
4. 공통 원인 고장(같은 버그·설정·리전)으로 독립 가정이 깨지는 것, 그리고 페일오버 메커니즘 자체의 실패나 전환 시간이 계산에 빠지는 것.

## 더 읽을거리 (References)

- NIST/SEMATECH, [e-Handbook of Statistical Methods — Assessing Product Reliability](https://www.itl.nist.gov/div898/handbook/apr/apr.htm) ([Exponential](https://www.itl.nist.gov/div898/handbook/apr/section1/apr161.htm), [Bathtub curve](https://www.itl.nist.gov/div898/handbook/apr/section1/apr124.htm))
- AWS, [Reliability Pillar — Availability](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/availability.html)
- AWS, [Availability and Beyond: Understanding and Improving the Resilience of Distributed Systems on AWS](https://docs.aws.amazon.com/whitepapers/latest/availability-and-beyond-improving-resilience/availability-and-beyond-improving-resilience.html)
- Google, [Site Reliability Engineering, Chapter 3 — Embracing Risk](https://sre.google/sre-book/embracing-risk/)
- Jim Gray, *Why Do Computers Stop and What Can Be Done About It?*, Tandem Technical Report 85.7, 1985 (서지 정보)
