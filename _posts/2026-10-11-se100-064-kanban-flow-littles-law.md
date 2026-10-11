---
layout: post
title: "[SE100 #064] 칸반과 흐름 — 리틀의 법칙과 WIP 제한"
date: 2026-10-11 17:05:18 +0900
categories: [software-engineering]
tags: [se100, process, kanban, littles-law, wip-limit, flow-metrics]
---

소프트웨어 공학 100 주제 시리즈의 64번째 글이다. (카테고리: 프로세스와 방법론)

## 한 줄 요약

리틀의 법칙 $$L = \lambda W$$ 를 팀에 옮기면 **평균 진행 중 작업(WIP) = 처리량 × 평균 사이클 타임** 이다. 처리량이 그대로라면 일을 빨리 끝내는 방법은 하나뿐이다. 동시에 붙든 일을 줄이는 것. 칸반의 WIP 제한은 이 산수를 팀 규칙으로 만든 것이다.

## 왜 필요한가

바쁜 팀일수록 이런 보드를 갖고 있다.

```
 할 일(43)   │ 진행 중(17)          │ 리뷰 대기(9) │ 완료
 ...         │ 결제 리팩터링(23일째)  │ ...         │
             │ 알림 개선(19일째)     │             │
             │ ...                  │             │
```

다섯 명이 열일곱 개를 진행 중이다. 모두 바쁘다. 그런데 이해관계자는 "왜 아무것도 안 끝나느냐" 고 묻는다. 사람의 바쁨(활용률)과 일의 흐름은 다른 것이다. 진행 중인 항목이 많으면 각 항목은 대부분의 시간을 **기다리면서** 보낸다. 리뷰를 기다리고, 전환된 사람의 주의를 기다리고, 다른 항목에 밀려서 기다린다.

## 핵심 개념

### 리틀의 법칙: 원전과 조건

John D. C. Little 은 [A Proof for the Queuing Formula: L = λW](https://doi.org/10.1287/opre.9.3.383)(Operations Research 9(3), 1961)에서 이 관계를 증명했다. 50년 뒤에 쓴 [Little's Law as Viewed on Its 50th Anniversary](https://doi.org/10.1287/opre.1110.0940)(Operations Research 59(3), 2011)는 실무자에게 특히 유용하다.

- **정의.** 대기 시스템 안의 평균 항목 수 L 은 평균 도착률 λ 와 항목이 시스템 안에서 보내는 평균 시간 W 의 곱이다.
- **유한 구간에서도 성립.** 관찰 구간 [0, T] 에서 L, λ, W 를 그 구간의 표본 경로로 정의하면, 구간 시작·끝에 시스템이 비어 있지 않아도 L = λW 가 정확히 성립한다(정리 LL.2).
- **분포·순서와 무관.** 도착 과정이 정상(stationary)일 필요가 없고, FIFO 든 우선순위든 처리 순서와도 무관하다.
- **측정이지 예측이 아니다.** Little 은 이 관계가 사후에 정확하다는 점을 들어 "우리는 예측이 아니라 측정을 하고 있다" 고 쓴다. 미래 예측에 쓰려면 과거 데이터가 미래를 대표한다는 별도의 가정이 필요하다.

그리고 실무 해석을 명확히 준다. 세 양은 서로 묶여 있어서, **λ 가 정해져 있다면 L 을 줄이는 유일한 길은 항목당 평균 대기 W 를 줄이는 것**이다. 반대로 읽으면 L 을 줄이면 W 가 준다.

### 소프트웨어 팀의 언어로

| 큐잉 이론 | 칸반 흐름 지표 | 정의 (Kanban Guide) |
|---|---|---|
| L | WIP | 시작했지만 끝나지 않은 작업 항목 수 |
| λ (안정 상태에서 이탈률) | 처리량(Throughput) | 단위 시간당 끝난 항목 수 |
| W | 사이클 타임(Cycle Time) | 항목이 시작된 때부터 끝난 때까지 경과 시간 |
| — | 작업 항목 나이(Work Item Age) | 시작된 때부터 현재까지 경과 시간 |

정의는 [The Kanban Guide](https://kanbanguides.org/english/)(John Coleman, Daniel Vacanti, 2025년 5월판)에서 그대로 옮겼다. 이 가이드는 위 네 가지를 반드시 추적할 흐름 지표로 둔다.

$$\text{평균 사이클 타임} = \frac{\text{평균 WIP}}{\text{평균 처리량}}$$

앞의 보드에 대입해 보자. 팀이 주당 평균 5건을 끝내고 진행 중(리뷰 대기 포함)이 26건이라면 평균 사이클 타임은 약 5.2주다. 처리량을 두 배로 올리는 것은 어렵다. WIP 를 10건으로 줄이는 것은 **결정**으로 가능하고, 같은 처리량이면 평균 사이클 타임은 2주로 준다.

### 칸반의 뿌리와 두 갈래

칸반이라는 말은 토요타 생산 방식에서 왔다. Lean Enterprise Institute 의 [용어집](https://www.lean.org/lexicon-terms/kanban/)은 칸반을 "풀(pull) 시스템에서 품목의 생산 또는 인출(운반)을 허가하고 지시하는 신호 장치" 로 정의하고, "칸반 없이는 어떤 부품도 생산·이동하지 않는 한" 진정한 풀 시스템이 유지된다고 쓴다. [토요타](https://global.toyota/en/company/vision-and-philosophy/production-system/)는 그 두 기둥 중 하나인 저스트 인 타임을 "필요한 것을, 필요할 때, 필요한 만큼만 만드는 것" 으로 설명한다. 소프트웨어의 WIP 제한은 이 "허가 신호" 의 직접 후예다. 빈칸이 생겨야 다음 일을 당긴다.

지식 노동의 칸반에는 현재 두 가이드가 있다.

| | Kanban Method ([Kanban University](https://kanban.university/kanban-guide/)) | The Kanban Guide ([ProKanban.org](https://prokanban.org/the-kanban-guide/)) |
|---|---|---|
| 뿌리 | David J. Anderson, *Kanban*(Blue Hole Press, 2010) | John Coleman, Daniel Vacanti |
| 정의 | 전문 서비스(지식 노동)를 관리하는 방법 | 프로세스를 통한 가치 흐름을 최적화하는 전략 |
| 실천 | 시각화, WIP 제한, 흐름 관리, 정책 명시, 피드백 고리, 협업적 개선·실험적 진화 (6) | 워크플로 정의·시각화, 항목 능동 관리, 워크플로 개선 (3) |
| 특징 | 변화 관리 원칙: "지금 하는 것에서 시작한다" | 네 가지 필수 흐름 지표 |

둘 다 핵심은 같다. 일을 보이게 하고, 동시에 붙드는 양을 제한하고, 흐름을 재서 개선한다.

### 왜 WIP 를 줄이면 처리량이 떨어지지 않는가

직관은 "동시에 많이 하면 많이 끝난다" 고 말한다. 처리량의 상한은 팀의 처리 능력이다. 능력이 이미 다 쓰이고 있다면 WIP 를 늘려도 처리량은 늘지 않고, 늘어난 WIP 는 리틀의 법칙에 따라 고스란히 사이클 타임으로 간다. 게다가 전환 비용이 붙으면 처리량은 오히려 떨어진다.

## 예제

간단한 모형으로 확인한다. 숫자는 모두 설명용 가정이다.

```python
# 한 팀의 흐름 모형 (숫자는 모두 설명용 가정)
# - 백로그는 항상 충분하다. 진행 중 항목이 WIP 한도보다 적으면 새 항목을 당겨온다.
# - 팀의 하루 처리 능력은 작업량 2.0. 진행 중 항목들에 고르게 나뉜다.
# - 항목 하나의 작업량은 평균 5 (3~7 사이 무작위).
# - 동시에 붙든 항목이 많을수록 전환 비용으로 능력이 깎인다 (항목당 2%, 최대 50%).
import random

def run(wip_limit, days=600, seed=1):
    rng = random.Random(seed)
    active, done = [], []
    for day in range(days):
        while len(active) < wip_limit:                       # pull
            active.append({"start": day, "left": rng.uniform(3, 7)})
        share = 2.0 * (1 - min(0.02 * len(active), 0.5)) / len(active)
        for it in active:
            it["left"] -= share
        for it in [a for a in active if a["left"] <= 0]:
            done.append((it["start"], day + 1))
            active.remove(it)
    window = [(s, e) for s, e in done if 300 <= e < 600]     # 후반 300일 측정
    throughput = len(window) / 300
    cycle = sum(e - s for s, e in window) / len(window)
    return throughput, cycle

print("WIP 한도  처리량(건/일)  평균 사이클 타임(일)  처리량 x 사이클 타임")
for w in (1, 2, 4, 8, 16):
    th, ct = run(w)
    print(f"{w:7d}  {th:12.2f}  {ct:19.1f}  {th * ct:18.1f}")
```

실행 결과:

```
WIP 한도  처리량(건/일)  평균 사이클 타임(일)  처리량 x 사이클 타임
      1          0.34                  2.9                 1.0
      2          0.36                  5.6                 2.0
      4          0.36                 11.1                 4.0
      8          0.34                 23.7                 8.2
     16          0.28                 57.9                16.0
```

- 마지막 열이 WIP 한도와 거의 같다. 리틀의 법칙이 모형 안에서 그대로 확인된다.
- WIP 를 1에서 8로 늘려도 처리량은 거의 그대로이고 사이클 타임만 여덟 배가 된다.
- WIP 16 에서는 전환 비용 때문에 처리량까지 떨어진다. 바쁜데 덜 끝나는 상태다.

## 실무 적용

### WIP 제한을 처음 거는 법

1. **현재를 잰다.** 지난 4~8주의 열별 평균 WIP, 주당 완료 수, 사이클 타임 분포를 뽑는다.
2. **현재보다 약간 낮게 건다.** 처음부터 이론적 최적값을 노리지 않는다. 지금의 평균보다 조금 낮춰 막히는 곳을 드러낸다.
3. **막힘을 질문으로 다룬다.** 한도에 걸려 일을 못 당기면, 그 사람은 새 일 대신 막힌 항목(대개 리뷰·테스트)을 돕는다. [ProKanban.org](https://prokanban.org/the-kanban-guide/)의 가이드 요약 표현대로 "모든 병목은 질문" 이다.
4. **오래된 항목부터 본다.** 데일리 회의를 사람 순서가 아니라 보드 오른쪽부터, **작업 항목 나이**가 많은 순서로 진행한다.
5. **정책을 적는다.** "리뷰 대기 열 한도 3", "긴급 항목은 동시에 1건" 처럼 보드에 명시한다.

### 지표 쿼리 예

```sql
-- 이슈 트래커 이력에서 주별 처리량과 사이클 타임(일) 백분위
SELECT date_trunc('week', done_at)                          AS week,
       count(*)                                             AS throughput,
       percentile_cont(0.5)  WITHIN GROUP (ORDER BY done_at::date - started_at::date) AS ct_p50,
       percentile_cont(0.85) WITHIN GROUP (ORDER BY done_at::date - started_at::date) AS ct_p85
FROM work_items
WHERE started_at IS NOT NULL AND done_at IS NOT NULL
GROUP BY 1 ORDER BY 1;
```

평균만 보지 말고 85번째 백분위처럼 꼬리를 본다. 사이클 타임 분포는 대개 오른쪽으로 긴 꼬리를 가진다. 처리량 데이터를 이용한 확률적 일정 예측은 SE100 #077 에서 다룬다.

## 흔한 오해와 함정

- **리틀의 법칙으로 개별 항목의 완료일을 예측한다.** 이 법칙은 **평균** 사이의 관계다. 개별 항목의 사이클 타임은 분포로 봐야 한다.
- **시작·완료 정의가 열마다 다르다.** "시작" 을 백로그 등록으로, "완료" 를 배포로 잡을지 정하지 않으면 지표가 의미를 잃는다. 경계를 먼저 정의한다.
- **WIP 를 사람 단위로만 제한한다.** "1인당 2건" 은 리뷰 대기 열이 쌓이는 것을 못 막는다. 열(상태) 단위 한도가 필요하다.
- **처리량을 목표로 삼는다.** 항목을 잘게 쪼개면 처리량 숫자는 쉽게 오른다. 지표는 개선을 위한 질문 도구다.
- **"칸반 = 보드".** 보드는 시각화일 뿐이다. WIP 제한과 흐름 관리가 없으면 칸반 보드가 아니라 할 일 목록이다.

## 확인 문제

1. 리틀의 법칙을 소프트웨어 팀의 세 흐름 지표로 쓰라.
2. 처리량이 주당 4건, 평균 WIP 가 12건이다. 평균 사이클 타임은? WIP 를 6건으로 줄이고 처리량이 유지된다면?
3. Little 이 2011년 논문에서 강조한, 이 법칙이 성립하는 데 필요 **없는** 조건 두 가지를 쓰라.
4. 위 모형에서 WIP 16 일 때 처리량이 떨어진 이유는?
5. 데일리 회의를 "작업 항목 나이" 순으로 진행하는 이유는?

### 풀이

1. 평균 WIP = 평균 처리량 × 평균 사이클 타임.
2. 12 / 4 = 3주. WIP 6건이면 6 / 4 = 1.5주.
3. 도착 과정의 정상성(stationarity), 특정 처리 순서(큐 규율). 유한 관찰 구간에서도, 구간 양 끝에 항목이 남아 있어도 성립한다.
4. 동시에 붙든 항목이 많아 전환 비용이 처리 능력을 깎았기 때문이다. WIP 증가가 사이클 타임뿐 아니라 처리량까지 해친 것이다.
5. 나이가 많은 항목이 사이클 타임 분포의 꼬리를 만든다. 오래된 것부터 끝내야 예측 가능성이 올라가고 막힌 원인이 드러난다.

## 더 읽을거리 (References)

- John D. C. Little, [A Proof for the Queuing Formula: L = λW](https://doi.org/10.1287/opre.9.3.383), Operations Research 9(3), 1961
- John D. C. Little, [Little's Law as Viewed on Its 50th Anniversary](https://doi.org/10.1287/opre.1110.0940), Operations Research 59(3), 2011
- John Coleman, Daniel Vacanti, [The Kanban Guide](https://kanbanguides.org/english/), May 2025
- Kanban University, [The Official Kanban Guide](https://kanban.university/kanban-guide/)
- Lean Enterprise Institute, [Kanban — Lean Lexicon](https://www.lean.org/lexicon-terms/kanban/)
- Toyota, [Toyota Production System](https://global.toyota/en/company/vision-and-philosophy/production-system/)
- David J. Anderson, *Kanban: Successful Evolutionary Change for Your Technology Business*, Blue Hole Press, 2010 (서지 정보)
