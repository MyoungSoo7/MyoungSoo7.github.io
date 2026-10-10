---
layout: post
title: "[CS300 #235] SLI·SLO·에러 버짓 — 얼마나 안정적이면 충분한가"
date: 2026-10-10 21:55:00 +0900
categories: [cs]
tags: [cs300, devops, sre, slo, reliability]
---

컴퓨터공학 300 주제 시리즈의 235번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

SLI 는 사용자가 느끼는 서비스 품질을 재는 지표, SLO 는 그 지표의 목표치, 에러 버짓은 "1 − SLO" 만큼 허용된 실패의 양이다. 버짓이 남아 있으면 변경을 밀고, 바닥나면 안정화에 집중한다.

## 왜 필요한가

"장애는 없어야 한다"는 목표는 듣기에는 좋지만 쓸모가 없다. 100% 가용성은 달성할 수 없고, 다가갈수록 비용이 기하급수적으로 늘며, 배포를 멈추게 만든다. 반대로 목표가 없으면 개발팀은 기능을, 운영팀은 안정성을 각자 주장하며 끝없이 다툰다.

SLO 는 이 다툼을 숫자로 바꾼다. "한 달에 0.1% 까지는 실패해도 된다"고 합의하면, 남은 실패 허용량(에러 버짓)이 배포 속도와 안정화 작업 사이의 판단 기준이 된다. Google 의 SRE 방법론이 이 개념을 널리 퍼뜨렸다.

## 핵심 개념

### 용어

| 용어 | 정의 | 예 |
|---|---|---|
| SLI (Service Level Indicator) | 서비스 수준을 정량적으로 잰 값. 보통 "좋은 이벤트 / 전체 이벤트" | 성공 응답 비율, 300ms 안에 끝난 요청 비율 |
| SLO (Service Level Objective) | SLI 의 목표 값과 측정 기간 | 30일 동안 99.9% 의 요청이 성공 |
| SLA (Service Level Agreement) | 고객과의 계약. 어기면 환불 등의 결과가 따른다 | 월 가용성 99.5% 미만이면 요금 10% 환불 |
| 에러 버짓 | 1 − SLO. 기간 동안 허용된 나쁜 이벤트의 양 | 99.9% 면 0.1% |

SLA 는 SLO 보다 느슨하게 잡는다. 내부 목표(SLO)를 어겼을 때 계약 위반(SLA)까지는 여유가 있어야 대응할 시간이 생긴다.

### 좋은 SLI 고르기

SLI 는 **사용자 관점**이어야 한다. CPU 사용률은 SLI 가 아니다. 사용자는 CPU 를 보지 않는다.

| 서비스 종류 | 대표 SLI |
|---|---|
| 요청-응답 (API, 웹) | 가용성(성공 비율), 지연(임계값 안 비율) |
| 데이터 파이프라인 | 신선도(데이터가 얼마나 최근인가), 정확성, 처리 완료 비율 |
| 저장소 | 내구성, 읽기·쓰기 성공 비율 |

어디서 재는지도 중요하다. 서버 로그로 재면 로드밸런서 앞에서 버려진 요청은 안 보인다. 로드밸런서 지표가 사용자에 더 가깝다. 클라이언트 측정이 가장 가깝지만 잡음이 많다.

지연 SLI 는 평균이 아니라 "임계값 안에 끝난 비율"로 정의한다. 평균은 소수의 아주 느린 요청을 숨긴다.

### 9 의 개수와 허용 시간

| SLO | 30일 기준 허용 실패 시간 |
|---|---|
| 99% | 7시간 12분 |
| 99.5% | 3시간 36분 |
| 99.9% | 43분 12초 |
| 99.95% | 21분 36초 |
| 99.99% | 4분 19초 |

(30일 = 43,200분에 1 − SLO 를 곱한 값이다.)

9 가 하나 늘 때마다 허용 시간은 10분의 1 이 된다. 99.99% 라면 사람이 경보를 받고 노트북을 열기도 전에 한 달 버짓이 끝날 수 있다. 그만큼 자동 복구가 필요하다. 의존하는 서비스보다 높은 SLO 는 원칙적으로 달성할 수 없다는 점도 기억한다.

### 에러 버짓 정책

에러 버짓은 정책과 함께여야 의미가 있다. SRE Workbook 이 제시하는 정책의 골자는 이렇다.

- 버짓이 남아 있으면: 정상적으로 기능을 배포한다.
- 버짓을 소진하면: 버그 수정과 안정성 개선 외의 배포를 멈춘다. 버짓이 회복될 때까지.
- 단일 사건이 버짓의 큰 부분을 소모했다면 포스트모템을 쓰고 개선 작업을 우선순위에 올린다(236번).

중요한 것은 이 정책을 **사건이 터지기 전에** 개발·운영·제품 책임자가 함께 합의하는 것이다.

### 번 레이트(burn rate) 경보

"SLI 가 99.9% 아래로 떨어지면 경보"는 좋지 않은 경보다. 1분짜리 잡음에도 울리고, 천천히 새는 문제는 늦게 잡는다. 대신 **버짓을 얼마나 빨리 태우고 있는가**에 경보를 건다.

번 레이트 = 현재 에러 비율 / 허용 에러 비율. 번 레이트 1 은 기간이 끝날 때 버짓을 정확히 다 쓰는 속도다.

30일 SLO 에서 "1시간 동안 한 달 버짓의 2% 를 썼다"를 번 레이트로 바꾸면 `0.02 × 720시간 / 1시간 = 14.4` 다. SRE Workbook 은 이런 식으로 긴 창(1시간)과 짧은 창(5분)을 함께 보는 다중 창(multiwindow) 번 레이트 경보를 권한다. 긴 창은 중요도를, 짧은 창은 "아직 진행 중인가"를 확인해 문제가 끝난 뒤에도 경보가 계속 울리는 것을 막는다.

## 직접 해 보기

에러 버짓 잔량과 번 레이트를 계산해 보자.

```python
SLO = 0.999
WINDOW_H = 30 * 24

def allowed_minutes(slo, days=30):
    return days * 24 * 60 * (1 - slo)

for s in (0.99, 0.995, 0.999, 0.9995, 0.9999):
    m = allowed_minutes(s)
    print(f"SLO {s * 100:g}% -> {int(m // 60)}h {m % 60:.1f}m per 30d")

# 한 달 동안의 요청·실패 집계(일 단위 단순화)
total_requests = 90_000_000
failed_so_far = 54_000          # 지난 20일 누적
budget = total_requests * (1 - SLO)
print(f"\nbudget={budget:,.0f} failures, used={failed_so_far:,} "
      f"({failed_so_far / budget:.0%}), remaining={budget - failed_so_far:,.0f}")

def burn_rate(error_ratio, slo=SLO):
    return error_ratio / (1 - slo)

print("\nburn-rate threshold for '2% of budget in 1h':", 0.02 * WINDOW_H / 1)
for label, long_err, short_err in [
    ("big outage, ongoing", 0.02, 0.03),
    ("big outage, recovered", 0.02, 0.0002),
    ("slow leak", 0.002, 0.002),
]:
    bl, bs = burn_rate(long_err), burn_rate(short_err)
    page = bl >= 14.4 and bs >= 14.4
    print(f"{label:22} burn(1h)={bl:5.1f} burn(5m)={bs:5.1f} page={page}")
```

결과는 다음과 같다.

```
SLO 99% -> 7h 12.0m per 30d
SLO 99.5% -> 3h 36.0m per 30d
SLO 99.9% -> 0h 43.2m per 30d
SLO 99.95% -> 0h 21.6m per 30d
SLO 99.99% -> 0h 4.3m per 30d

budget=90,000 failures, used=54,000 (60%), remaining=36,000

burn-rate threshold for '2% of budget in 1h': 14.4
big outage, ongoing    burn(1h)= 20.0 burn(5m)= 30.0 page=True
big outage, recovered  burn(1h)= 20.0 burn(5m)=  0.2 page=False
slow leak              burn(1h)=  2.0 burn(5m)=  2.0 page=False
```

세 번째 경우인 "느린 누수"는 사람을 깨울 일은 아니지만, 번 레이트 2 가 계속되면 15일 만에 한 달 버짓이 바닥난다. 그래서 더 긴 창(예: 6시간, 3일)과 낮은 번 레이트 임계값으로 티켓 수준 경보를 따로 둔다.

## 현업에서는

- **SLO 는 적게, 사용자 여정 단위로.** 엔드포인트마다 SLO 를 만들면 아무도 관리하지 않는다. "로그인", "결제", "검색"처럼 사용자에게 중요한 여정 몇 개를 고른다.
- **처음 목표는 과거 실적에서.** 지난 몇 주의 SLI 를 보고 그보다 약간 낮게 시작한 뒤 조정한다. 근거 없이 99.99% 를 선언하면 첫 달에 정책이 무력해진다.
- **배포 게이트.** 에러 버짓 잔량을 배포 파이프라인이 확인하게 하면 정책이 말로 끝나지 않는다. 버짓이 바닥났으면 기능 배포를 막고 수정 배포만 허용한다.
- **계획된 작업도 버짓에서.** 점검·마이그레이션으로 인한 다운타임도 사용자에게는 장애다. 버짓을 미리 떼어 두고 계획한다.
- **작은 클러스터에도 쓸모가 있다.** 홈랩 서비스라도 "블로그 응답 성공률 99.5%/30일" 정도의 목표를 두고 Prometheus 기록 규칙으로 번 레이트를 계산하면, 잡다한 CPU 경보 대신 실제로 손봐야 할 때만 알림을 받을 수 있다.

## 확인 문제

1. SLI, SLO, SLA 를 한 문장씩 구분하라.
2. 30일 기준 99.95% SLO 의 허용 실패 시간은?
3. 지연 SLI 를 평균 응답 시간으로 정의하면 안 되는 이유는?
4. 번 레이트 1 과 14.4 는 각각 무엇을 뜻하는가?
5. 장기·단기 두 창을 함께 쓰는 번 레이트 경보의 장점은?

### 풀이

1. SLI 는 품질을 잰 값, SLO 는 그 값의 내부 목표, SLA 는 어기면 계약상 결과가 따르는 외부 약속이다.
2. 43,200분 × 0.0005 = 21.6분(21분 36초).
3. 평균은 소수의 매우 느린 요청을 가린다. 임계값 안 비율이나 분위수로 정의해야 사용자 경험을 반영한다.
4. 1 은 기간 끝에 버짓을 정확히 다 쓰는 속도. 14.4 는 30일 버짓의 2% 를 1시간에 쓰는 속도(그대로면 약 50시간에 소진).
5. 긴 창으로 의미 있는 소모만 잡고, 짧은 창으로 문제가 지금도 진행 중일 때만 울리게 해 오경보와 늦은 해제를 줄인다.

## 더 읽을거리 (References)

- Google SRE Book, [Service Level Objectives](https://sre.google/sre-book/service-level-objectives/)
- Google SRE Workbook, [Implementing SLOs](https://sre.google/workbook/implementing-slos/)
- Google SRE Workbook, [Example Error Budget Policy](https://sre.google/workbook/error-budget-policy/)
- Google SRE Workbook, [Alerting on SLOs](https://sre.google/workbook/alerting-on-slos/)
