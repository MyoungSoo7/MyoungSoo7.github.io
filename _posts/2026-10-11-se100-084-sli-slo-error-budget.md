---
layout: post
title: "[SE100 #084] SLI·SLO·에러 버짓"
date: 2026-10-11 17:08:52 +0900
categories: [software-engineering]
tags: [se100, quality-reliability, sli, slo, error-budget, burn-rate]
---

소프트웨어 공학 100 주제 시리즈의 84번째 글이다. (카테고리: 품질·신뢰성·보안)

## 한 줄 요약

SLO 는 숫자 하나가 아니라 **명세(무엇을 좋은 사건으로 셀지) + 구현(어디서 어떻게 셀지) + 창(window) + 목표 + 버짓 정책 + 경보 규칙**의 묶음이다. 이 묶음을 제품·개발·운영이 합의했을 때에만 에러 버짓이 "출시 속도와 안정성 사이의 계약" 으로 작동한다.

## 왜 필요한가

용어와 기본 계산은 CS300 [SLI·SLO·에러 버짓]({% post_url 2026-10-10-cs300-235-sli-slo-error-budget %}) 에서 다뤘다. 이 글은 그다음 단계, 즉 SLO 를 실제로 **설계하고 운영할 때** 부딪히는 결정을 다룬다. 현장에서 SLO 가 실패하는 모습은 대개 이렇다.

- 대시보드에 "가용성 99.95%" 가 있지만 무엇을 분자·분모로 셌는지 아무도 모른다.
- 목표를 넘겨도 아무 일도 일어나지 않는다. 버짓 정책이 없거나, 있어도 제품 쪽이 동의한 적이 없다.
- 경보가 SLO 와 무관하게 CPU·메모리 임계값에 걸려 있어, SLO 는 월말 보고서용 숫자로만 남는다.

세 가지 모두 숫자는 있는데 **결정과 연결되지 않은** 상태다.

## 핵심 개념

### SLI 는 비율로: 좋은 사건 / 유효한 사건

[The Site Reliability Workbook 의 Implementing SLOs 장](https://sre.google/workbook/implementing-slos/)은 SLI 를 **좋은 사건 수를 전체 사건 수로 나눈 비율**로 정의하길 권한다. 0% 는 아무것도 안 되는 상태, 100% 는 아무것도 깨지지 않은 상태가 되어 직관적이고, 에러 버짓이 자연스럽게 "100% − SLO" 가 된다. 같은 장의 예시로, 99.9% 성공률 SLO 에서 4주 동안 300만 요청을 받았다면 버짓은 오류 3,000건이고, 한 번의 장애로 1,500건이 났다면 버짓의 50% 를 쓴 것이다.

```
           좋은 사건 수                 예: 상태코드 5xx 가 아니고 300ms 안에 끝난 요청
  SLI = ──────────────────
           유효한 사건 수                예: 헬스체크·봇·4xx 를 제외한 사용자 요청
```

분모의 "유효한" 이 설계의 절반이다. 클라이언트 잘못(4xx)을 분모에 넣으면 남의 실수가 우리 버짓을 갉아먹고, 헬스체크를 넣으면 실제 사용자 경험이 희석된다.

### SLI 명세와 SLI 구현

같은 장은 **SLI 명세**(specification: 사용자에게 중요한 결과가 무엇인가)와 **SLI 구현**(implementation: 그것을 어떻게 측정하는가)을 분리한다. 하나의 명세에 여러 구현이 있을 수 있고, 각 구현은 품질(사용자 경험을 얼마나 정확히 반영하는가), 커버리지(얼마나 많은 사용자를 포착하는가), 비용에서 장단점이 있다.

| 측정 지점 | 품질 | 커버리지 | 비용·난이도 |
|---|---|---|---|
| 애플리케이션 서버 로그/메트릭 | 중 (네트워크·LB 문제를 못 봄) | 높음 | 낮음 |
| 로드밸런서 메트릭 | 중상 | 높음 | 낮음 |
| 합성 프로버(synthetic probe) | 중 (실제 사용자 아님) | 낮음 | 중 |
| 클라이언트 계측 (RUM) | 높음 | 높음 | 높음, 잡음 많음 |

처음에는 이미 있는 로드밸런서 메트릭으로 시작하고, SLO 가 실제 사용자 불만과 어긋날 때 측정 지점을 사용자 쪽으로 옮기는 것이 일반적인 경로다.

### 창(window)의 선택

같은 장은 롤링 창과 달력 창을 비교한다. 롤링 창은 사용자 경험에 가깝다. 월말의 큰 장애를 사용자가 다음 달 1일에 잊지는 않기 때문이다. 창 길이는 **주 단위 정수배**로 잡아 주말 수가 일정하게 하라고 권하며(30일 창은 주말이 4번일 때도 5번일 때도 있다), 범용으로 **4주 롤링 창**을 좋은 출발점으로 제시한다. 달력 창(예: 분기)은 사업 계획과 맞추기 좋지만, 분기 중간에는 남은 기간의 트래픽을 모르므로 버짓 판단이 추측이 된다.

### 에러 버짓 정책

[예시 에러 버짓 정책](https://sre.google/workbook/error-budget-policy/)의 골격은 다음과 같다.

- **목표**: 반복되는 SLO 미달로부터 고객을 보호하고, 신뢰성과 기능 개발 사이의 균형에 유인을 준다.
- **비목표**: SLO 미달에 대한 처벌이 아니다.
- **미달 시**: 직전 4주 창에서 버짓을 초과하면 P0 이슈와 보안 수정을 제외한 변경·릴리스를 멈추고, SLO 안으로 돌아올 때까지 신뢰성 작업에 집중한다.
- **반드시 신뢰성 작업을 하는 경우**: 서비스 자체의 코드 버그나 절차 오류로 버짓을 초과했을 때, 사후 분석에서 경성 의존을 완화할 기회가 드러났을 때 등.
- **기능 작업을 계속해도 되는 경우**: 회사 전체 네트워크 장애처럼 서비스 밖의 원인일 때 등.

Implementing SLOs 장은 제품 관리자·개발팀·SRE 세 당사자가 이 정책에 **모두 동의하는 것**을 SLO 가 목적에 맞는지 보는 시험으로 삼는다. 동의가 안 되면 SLI·SLO 를 다시 고친다. 동의 없는 정책은 버짓이 바닥난 날 무력화된다.

### SLO 는 상한이기도 하다

[SRE 책의 SLO 장](https://sre.google/sre-book/service-level-objectives/)은 Chubby 사례를 든다. 전역 Chubby 가 목표를 크게 넘는 가용성을 계속 보이자 사용자 서비스들이 Chubby 가 절대 안 멈춘다고 가정하고 부적절한 의존을 만들었다. 그래서 분기 중 실제 장애로 목표 아래로 떨어지지 않았다면 **의도적으로 계획된 중단**을 만들어 그런 의존을 드러냈다. 목표를 지나치게 초과 달성하는 것도 위험 신호다.

### 다중 창·다중 번 레이트 경보

[Alerting on SLOs 장](https://sre.google/workbook/alerting-on-slos/)은 단순 임계값에서 시작해 여섯 단계로 경보를 개선한다. 최종 권고는 긴 창과 짧은 창을 **둘 다** 넘을 때 울리는 다중 번 레이트 경보다. 99.9% SLO 기준 권장 출발값은 다음과 같다.

| 심각도 | 긴 창 | 짧은 창 | 번 레이트 | 소모 버짓 |
|---|---|---|---|---|
| 페이지 | 1시간 | 5분 | 14.4 | 2% |
| 페이지 | 6시간 | 30분 | 6 | 5% |
| 티켓 | 3일 | 6시간 | 1 | 10% |

번 레이트 1 은 창이 끝날 때 버짓을 정확히 다 쓰는 속도다. 긴 창은 "의미 있는 양의 버짓이 실제로 소모됐는가" 를, 짧은 창은 "지금도 계속 타고 있는가" 를 본다. 짧은 창 덕분에 문제가 멎으면 경보가 빨리 꺼진다(reset time 개선).

## 실무 적용

### Prometheus 규칙

위 표의 첫 두 줄을 그대로 옮긴 규칙이다. `slo:error_ratio:rateXX` 는 오류 요청 비율을 창별로 미리 계산한 recording rule 이라고 가정한다.

```yaml
groups:
- name: checkout-slo
  rules:
  - alert: CheckoutErrorBudgetFastBurn
    expr: |
      (slo:error_ratio:rate1h{service="checkout"}  > (14.4 * 0.001)
       and
       slo:error_ratio:rate5m{service="checkout"}  > (14.4 * 0.001))
      or
      (slo:error_ratio:rate6h{service="checkout"}  > (6 * 0.001)
       and
       slo:error_ratio:rate30m{service="checkout"} > (6 * 0.001))
    labels:
      severity: page
    annotations:
      summary: "checkout 에러 버짓 빠른 소진 (SLO 99.9%, 30일 창 기준)"
  - alert: CheckoutErrorBudgetSlowBurn
    expr: |
      slo:error_ratio:rate3d{service="checkout"} > 0.001
      and
      slo:error_ratio:rate6h{service="checkout"} > 0.001
    labels:
      severity: ticket
```

`0.001` 은 1 − 0.999 다. 워크북의 번 레이트 값은 30일 창 기준이라, 4주(672시간) 창을 쓰면 같은 "1시간에 2%" 가 번 레이트 13.44 가 된다. 목표나 창을 바꾸면 이 상수와 번 레이트를 함께 다시 계산해야 하므로, 실무에서는 생성 스크립트나 SLO 도구로 규칙을 만들어 사람이 직접 숫자를 고치지 않게 한다. 도구 간 이식을 위한 벤더 중립 명세로 [OpenSLO](https://github.com/OpenSLO/OpenSLO) 가 있다.

### 번 레이트 → 경보까지 걸리는 시간

```python
# 창 T 동안 버짓의 비율 f 를 소모했을 때의 번 레이트 = f * (SLO 기간 / T)
SLO_PERIOD_H = 30 * 24
for frac, window_h in [(0.02, 1), (0.05, 6), (0.10, 72)]:
    print(f"{frac:.0%} in {window_h}h → burn rate {frac * SLO_PERIOD_H / window_h:.1f}")
# 2% in 1h → 14.4, 5% in 6h → 6.0, 10% in 72h → 1.0

def hours_to_exhaust(burn): return SLO_PERIOD_H / burn
print(hours_to_exhaust(14.4), hours_to_exhaust(6))   # 50.0h, 120.0h
```

번 레이트 14.4 가 계속되면 30일 버짓이 50시간 만에 바닥난다. 이 숫자가 "왜 이건 새벽에 깨워야 하는가" 에 대한 답이다.

### SLO 문서 한 장

```markdown
# SLO: checkout API
- 담당: 결제팀 / 승인: PM 김○○, 개발 리드 이○○, SRE 박○○ (2026-10-01)
- SLI 명세: 결제 확정 요청 중 성공하고 800ms 안에 응답한 비율
- SLI 구현: L7 로드밸런서 로그. 분모는 POST /checkout/confirm, 4xx 제외
- 목표: 99.9% / 4주 롤링   → 버짓: 유효 요청의 0.1%
- 경보: 다중 창·다중 번 레이트 (번 레이트는 4주 창으로 재계산: 13.44 / 5.6 / 0.93)
- 버짓 정책: 초과 시 P0·보안 외 릴리스 동결, 사후 분석 액션 우선
- 재검토: 분기 1회 (실제 고객 불만·VOC 와 SLI 의 일치 여부 확인)
```

## 흔한 오해와 함정

- **SLO = SLA** — SLA 는 미달 시 결과(환불 등)가 붙은 계약이다. SLO 는 내부 목표이고, SLA 보다 엄격하게 잡아 여유를 두는 것이 보통이다.
- **100% 목표** — 버짓이 0 이면 모든 변경이 위험이 되고, 결국 아무도 정책을 지키지 않는다. 사용자가 체감 못 하는 차이에 드는 비용도 크다.
- **지표 아무거나 SLI** — CPU 사용률은 사용자 경험의 원인 후보일 뿐 결과가 아니다. SLI 는 사용자가 겪는 결과를 센다.
- **평균 지연** — 평균은 꼬리 지연을 숨긴다. 지연 SLI 도 "임계값 안에 끝난 요청의 비율" 로 정의하면 비율형 SLI 로 통일된다.
- **SLO 를 한 번 정하고 끝** — 사용자 불만이 있는데 SLO 는 초록색이면 SLI 구현이 틀린 것이고, SLO 를 어겨도 아무도 불평하지 않으면 목표가 과한 것이다.

## 확인 문제

1. SLI 를 "좋은 사건 / 유효한 사건" 비율로 정의하는 장점 두 가지는?
2. 30일 창 대신 4주(28일) 롤링 창을 권하는 이유는?
3. 99.9% SLO, 30일 기준에서 1시간 동안 버짓 5% 를 소모했다. 번 레이트는? 이 속도가 계속되면 버짓은 몇 시간 뒤 바닥나는가?
4. 다중 창 경보에서 짧은 창이 하는 역할은?
5. 에러 버짓 정책에 "처벌이 아니다" 라는 비목표를 명시하는 이유는?

### 풀이

1. 0~100% 의 직관적 척도가 되고, 에러 버짓을 "100% − SLO" 로 바로 정의할 수 있다. 지연·가용성 등 서로 다른 SLI 를 같은 형식으로 다룰 수 있다.
2. 주 단위 정수배라 매 창에 포함된 주말 수가 같아, 주중·주말 트래픽 차이 때문에 SLI 가 의미 없이 흔들리는 것을 막는다.
3. 0.05 × 720 / 1 = 36. 720/36 = 20시간 뒤 바닥난다.
4. 문제가 여전히 진행 중인지 확인해, 이미 멎은 문제로 긴 창이 계속 경보를 울리는 것(긴 reset time)을 막는다.
5. 처벌로 인식되면 팀은 오류를 덜 세도록 SLI 를 조작하거나 정책 발동을 피하려 한다. 정책의 목적은 신뢰성 작업에 집중할 "허가" 를 주는 것이다.

## 더 읽을거리 (References)

- Google, [Site Reliability Engineering, Chapter 4 — Service Level Objectives](https://sre.google/sre-book/service-level-objectives/)
- Google, [The Site Reliability Workbook, Chapter 2 — Implementing SLOs](https://sre.google/workbook/implementing-slos/)
- Google, [The Site Reliability Workbook, Chapter 5 — Alerting on SLOs](https://sre.google/workbook/alerting-on-slos/)
- Google, [The Site Reliability Workbook, Appendix B — Example Error Budget Policy](https://sre.google/workbook/error-budget-policy/)
- [OpenSLO specification](https://github.com/OpenSLO/OpenSLO)
