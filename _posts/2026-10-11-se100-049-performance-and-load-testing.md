---
layout: post
title: "[SE100 #049] 성능·부하 테스트"
date: 2026-10-11 17:01:49 +0900
categories: [software-engineering]
tags: [se100, software-testing, load-testing, latency, k6]
---

소프트웨어 공학 100 주제 시리즈의 49번째 글이다. (카테고리: 소프트웨어 테스팅)

## 한 줄 요약

성능 테스트는 "빠른가" 가 아니라 **"어떤 부하에서, 지연 분포의 어느 지점이, 얼마 동안, 어떤 목표를 만족하는가"** 를 묻는 실험이다. 평균 대신 백분위수를 보고, 부하 생성기가 서버와 **공모해 나쁜 순간을 덜 측정하는**(coordinated omission) 일을 막고, 목표(SLO)를 테스트의 합격 기준으로 코드화해야 결과를 믿을 수 있다.

## 왜 필요한가

기능 테스트는 "맞는 답을 내는가" 를 본다. 그러나 맞는 답을 8초 뒤에 내는 결제 화면은 고장과 다름없다. 성능 결함은 대개 다음 조건에서만 드러나서 기능 테스트로는 잡히지 않는다.

- 동시 요청이 많을 때(락 경합, 커넥션 풀 고갈)
- 오래 돌았을 때(메모리 누수, 디스크 증가, 캐시 오염)
- 갑자기 몰릴 때(오토스케일 지연, 콜드 스타트)
- 의존 서비스 하나가 느려졌을 때(재시도 폭주, 스레드 고갈)

그리고 성능 테스트는 **잘못 측정하기 쉬운** 테스트다. "평균 120ms, 합격" 이라는 보고서가 사용자 20명 중 1명이 2초를 기다리는 시스템을 가릴 수 있다.

## 핵심 개념

### 테스트 유형

Grafana k6 문서의 [Load test types](https://grafana.com/docs/k6/latest/testing-guides/test-types/) 는 목적별로 여섯 가지를 구분한다.

| 유형 | 부하 | 기간 | 목적 |
|---|---|---|---|
| 스모크(smoke) | 낮음 | 짧음(초~분) | 스크립트가 동작하고 최소 부하에서 시스템이 적절한지 |
| 평균 부하(average-load) | 운영 평균 | 중간(5~60분) | 예상되는 정상 조건에서의 성능 |
| 스트레스(stress) | 평균 초과 | 중간(5~60분) | 평균을 넘는 부하에서 한계 근처 동작 |
| 소크(soak) | 평균 | 김(수 시간) | 장시간 지속 사용에서의 신뢰성과 성능 |
| 스파이크(spike) | 매우 높음 | 짧음(수 분) | 갑작스럽고 짧고 거대한 증가에서의 동작과 생존 |
| 브레이크포인트(breakpoint) | 깨질 때까지 증가 | 필요한 만큼 | 시스템의 용량 한계 찾기 |

문서는 스모크 테스트부터 시작해 스크립트와 시스템이 최소 부하에서 정상임을 확인한 뒤 더 복잡한 패턴으로 가라고 권하고, 어떤 유형이 필요한지는 조직의 위험 프로필에 달렸다고 한다.

### 평균이 아니라 분포

Google SRE 책의 [Service Level Objectives](https://sre.google/sre-book/service-level-objectives/) 장은 대부분의 지표를 평균보다 **분포** 로 생각하는 편이 낫다고 말한다. 단순 평균은 꼬리 지연과 그 변화를 가릴 수 있다. 책의 그림 4-1 예에서는 전형적인 요청이 약 50ms 에 처리되는데 요청의 5% 는 20배 느리고, 평균만 보는 모니터링으로는 하루 동안 아무 변화도 보이지 않는다. 50번째 백분위수(중앙값)는 전형적인 경우를, 99번째나 99.9번째 같은 높은 백분위수는 그럴듯한 최악의 경우를 보여 준다.

```
 요청 수
  │█
  │██
  │███▇▅▃▂▁▁ ▁    ▁         ▁           ← 긴 꼬리
  └───────────────────────────────────▶ 지연
   p50          p95       p99      max
```

백분위수끼리는 **평균을 내면 안 된다.** 서버 10대의 p99 를 평균한 값은 전체 요청의 p99 가 아니다. 원시 지연값이나 히스토그램을 합친 뒤 백분위수를 다시 계산해야 한다. 넓은 범위의 지연값을 정밀도 손실 없이 기록하고 합치는 자료구조로 Gil Tene 의 [HdrHistogram](https://hdrhistogram.github.io/HdrHistogram/) 이 널리 쓰인다.

### Little 의 법칙

동시성, 처리량, 지연은 독립된 숫자가 아니다. Little 이 [A Proof for the Queuing Formula: L = λW](https://doi.org/10.1287/opre.9.3.383) (Operations Research, 1961) 로 증명한 관계가 있다.

$$L = \lambda W$$

시스템 안의 평균 요청 수 L 은 도착률 λ 와 평균 체류 시간 W 의 곱이다. 초당 200 요청이 평균 0.25초 머물면 시스템 안에는 평균 50개의 요청이 있다. 그래서 "가상 사용자 50명" 과 "초당 200 요청" 은 응답 시간이 0.25초일 때만 같은 부하다. 서버가 느려져 W 가 커지면 같은 50명이 만들어 내는 처리량은 떨어진다. 다음 절의 함정이 여기서 나온다.

### 닫힌 모델, 열린 모델, coordinated omission

k6 문서의 [Open and closed models](https://grafana.com/docs/k6/latest/using-k6/scenarios/concepts/open-vs-closed/) 에 따르면 **닫힌 모델** 에서는 이전 반복이 끝나야 다음 반복이 시작되므로, 새 반복의 도착률이 반복 시간(곧 응답 시간)에 묶인다. 시스템이 느려지면 부하 생성기도 덩달아 요청을 덜 보낸다. 문서는 이를 일부 문헌에서 **coordinated omission** 이라 부른다고 적는다. **열린 모델** 은 반복 시작을 반복 시간과 분리해, 대상 시스템의 응답 시간이 부하에 영향을 주지 않게 한다. k6 는 `constant-arrival-rate` 와 `ramping-arrival-rate` 실행기로 열린 모델을 구현한다.

Gil Tene 의 [wrk2 README](https://github.com/giltene/wrk2) 는 측정 쪽 문제를 설명한다. 각 연결이 응답을 받은 뒤에만 다음 요청을 보내는 방식은 개별 요청의 완료 시간은 정확히 재지만, 높은 지연 구간에서 부하 생성기가 서버와 "협조해" 측정을 피하게 되어 서버가 보인 높은 지연의 대부분을 무시하게 된다. wrk2 는 일정한 처리량으로 부하를 만들고, 지연을 **계획상 요청이 보내졌어야 할 시각** 부터 실제 응답 도착까지로 잰다.

아래는 이 글을 쓰며 돌린 작은 시뮬레이션이다. 서버는 평소 요청당 5ms 인데, 10초 중 1초 동안 멈춘다.

```python
# 닫힌 모델: 응답을 받아야 다음 요청. 열린 모델: 초당 100회 계획 시각에 요청,
# 지연은 '계획 시각'부터 측정. (전체 코드는 단일 서버 큐를 단순화한 것)
```

```
닫힌 모델: 표본 1801개  p50=   5.0ms  p99=   5.0ms  max=1000.0ms
열린 모델: 표본 1000개  p50=   5.0ms  p99= 960.0ms  max=1005.0ms
```

같은 서버, 같은 1초 정지인데 닫힌 모델의 p99 는 5ms 다. 정지 동안 닫힌 클라이언트는 요청을 딱 하나만 보내고 기다렸기 때문에 나쁜 1초가 표본 1개로 줄었다. 그 1초 동안 실제 사용자 100명이 겪었을 지연은 열린 모델에만 나타난다.

### 팬아웃과 꼬리

Dean 과 Barroso 의 [The Tail at Scale](https://doi.org/10.1145/2408776.2408794) (CACM, 2013) 은 대규모 서비스에서 지연 변동성을 견디는 기법을 다룬다. 핵심 직관은 산수로 확인할 수 있다. 서버 하나가 요청의 1% 에서 1초 이상 걸린다면, 사용자 요청 하나가 서버 100대에 동시에 퍼졌다가 모두 기다려야 할 때 그중 하나라도 느릴 확률은 1 − 0.99¹⁰⁰ ≈ 0.63 이다. 개별 서버의 p99 가 전체 시스템의 **중앙값** 근처를 결정하게 된다. 마이크로서비스 부하 테스트에서 하위 서비스의 p99 를 따로 보는 이유다.

## 실무 적용

### k6: 열린 모델 + SLO 를 임계값으로

[Thresholds](https://grafana.com/docs/k6/latest/using-k6/thresholds/) 는 테스트 지표의 합격/불합격 기준이고, 조건을 만족하지 못하면 테스트가 실패 상태로 끝난다. 문서는 흔히 임계값으로 SLO 를 코드화한다고 설명한다.

```javascript
import http from 'k6/http';

export const options = {
  scenarios: {
    checkout: {
      executor: 'constant-arrival-rate',   // 열린 모델: 응답이 느려져도 도착률 유지
      rate: 200, timeUnit: '1s',           // 초당 200 반복
      duration: '30m',
      preAllocatedVUs: 100, maxVUs: 400,   // Little: 200/s × 예상 지연 → 필요한 VU
    },
  },
  thresholds: {
    http_req_failed:   ['rate<0.01'],              // 오류율 1% 미만
    http_req_duration: ['p(95)<300', 'p(99)<800'], // SLO 를 백분위수로
  },
};

export default function () {
  http.post('https://staging.example.com/api/checkout', JSON.stringify({ cartId: 'c-1' }),
            { headers: { 'Content-Type': 'application/json' } });
}
```

계획한 반복을 시작하지 못하면 k6 는 그 수를 `dropped_iterations` 카운터로 기록한다. [문서](https://grafana.com/docs/k6/latest/using-k6/scenarios/concepts/dropped-iterations/) 는 원인으로 실행기 설정 부족(VU 가 모자람)과 SUT 가 설정된 도착률을 감당하지 못하는 경우 두 가지를 들고, 이 지표를 임계값에 넣을 수 있다고 설명한다. 이 값이 0 이 아니면 계획한 부하가 실제로 들어가지 않았다는 뜻이니 결과를 그대로 합격으로 읽으면 안 된다.

### 실험 설계 점검표

| 항목 | 확인할 것 |
|---|---|
| 목표 | SLO 형태로 미리 정했는가 (`p99 < 800ms @ 200 rps, 오류 < 1%`) |
| 부하 모델 | 열린 모델인가, 닫힌 모델이면 그 이유가 있는가 |
| 환경 | 운영과 같은 인스턴스 크기·설정·데이터 규모인가 |
| 데이터 | 캐시가 100% 맞는 동일 요청 반복이 아닌가 |
| 워밍업 | JIT·커넥션 풀·캐시 예열 구간을 측정에서 뺐는가 |
| 부하 생성기 | 생성기 자체의 CPU·네트워크가 병목이 아닌가 |
| 관측 | 서버 측 지표(CPU, GC, 풀 사용률, 큐 길이)를 같은 시간축에 기록했는가 |
| 결과 보관 | 히스토그램 원본과 실행 조건을 남겨 다음 실행과 비교할 수 있는가 |

## 흔한 오해와 함정

- **평균으로 합격 판정.** 꼬리를 가린다. SLO 는 백분위수로, 판정도 백분위수로.
- **백분위수의 평균.** 수학적으로 의미가 없다. 히스토그램을 합쳐서 다시 계산한다.
- **"동시 사용자 N명" 만으로 부하를 정의.** Little 의 법칙대로 처리량은 응답 시간에 따라 변한다. 도착률(rps)과 함께 정의한다.
- **닫힌 루프 도구의 결과를 그대로 신뢰.** 시스템이 멈춘 순간을 측정하지 않는다. 열린 모델로 바꾸거나 계획 시각 기준으로 보정한다.
- **스테이징의 작은 데이터로 측정.** 인덱스를 안 타는 쿼리는 데이터가 적을 때 빠르다. 성능 결함은 데이터 규모에 숨어 있다.
- **한 번 돌리고 끝.** 성능은 변경마다 회귀한다. 짧은 스모크·평균 부하 테스트를 파이프라인에 넣어 추세를 본다.

## 확인 문제

1. 스트레스 테스트와 브레이크포인트 테스트의 목적 차이는?
2. 평균 지연이 운영 지표로 부족한 이유를 SRE 책의 예로 설명하라.
3. 초당 300 요청, 평균 응답 0.2초인 서비스의 평균 동시 처리 요청 수는? 응답이 0.5초로 느려지면?
4. 위 시뮬레이션에서 닫힌 모델의 p99 가 5ms 로 나온 이유는?
5. 하위 서비스 50개에 동시 팬아웃하는 API 에서, 각 하위 서비스가 요청의 1% 에서 느리다면 사용자 요청이 느려질 확률은 대략 얼마인가?

### 풀이

1. 스트레스 테스트는 평균을 넘는 정해진 부하에서 시스템이 어떻게 동작하는지 본다. 브레이크포인트 테스트는 부하를 계속 올려 시스템이 깨지는 용량 한계를 찾는다.
2. 전형적인 요청이 약 50ms 인데 5% 가 20배 느린 경우, 평균은 꼬리의 변화를 가려 하루 종일 변화가 없어 보일 수 있다. 백분위수는 분포의 모양과 꼬리를 드러낸다.
3. L = λW = 300 × 0.2 = 60. 응답이 0.5초가 되면 같은 도착률에서 300 × 0.5 = 150 이 된다. 닫힌 모델로 VU 를 60에 고정했다면 처리량이 60 / 0.5 = 120 rps 로 떨어져 부하 자체가 줄어든다.
4. 서버가 멈춘 1초 동안 닫힌 클라이언트는 응답을 기다리느라 요청을 하나만 보냈다. 나쁜 구간이 표본 하나로만 기록되고, 나머지 수많은 빠른 표본이 백분위수를 지배했다.
5. 1 − 0.99⁵⁰ ≈ 0.39, 약 39%.

## 더 읽을거리 (References)

- Grafana k6 문서, [Load test types](https://grafana.com/docs/k6/latest/testing-guides/test-types/), [Open and closed models](https://grafana.com/docs/k6/latest/using-k6/scenarios/concepts/open-vs-closed/), [Thresholds](https://grafana.com/docs/k6/latest/using-k6/thresholds/), [Executors](https://grafana.com/docs/k6/latest/using-k6/scenarios/executors/)
- Google, *Site Reliability Engineering*, [Chapter 4 – Service Level Objectives](https://sre.google/sre-book/service-level-objectives/)
- J. D. C. Little, [A Proof for the Queuing Formula: L = λW](https://doi.org/10.1287/opre.9.3.383), Operations Research 9(3), 1961
- J. Dean, L. A. Barroso, [The Tail at Scale](https://doi.org/10.1145/2408776.2408794), Communications of the ACM 56(2), 2013
- Gil Tene, [wrk2 README](https://github.com/giltene/wrk2) / [HdrHistogram](https://hdrhistogram.github.io/HdrHistogram/)
- Apache, [JMeter](https://jmeter.apache.org/)
