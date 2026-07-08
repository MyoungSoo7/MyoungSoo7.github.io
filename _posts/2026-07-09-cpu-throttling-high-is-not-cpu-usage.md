---
layout: post
title: "CPUThrottlingHigh 57.5% — CPU 사용률 이 아니다"
date: 2026-07-09 02:40:00 +0900
categories: [kubernetes, observability, sre]
tags: [kubernetes, cpu-throttling, cfs-quota, prometheus, alerting, velero, k3s, limits]
---

밤 에 홈랩 클러스터 에서 알림 이 하나 왔다.

```
[resolved] CPUThrottlingHigh
severity: info
namespace: velero
57.5% throttling of CPU in namespace velero
for container velero in pod velero-8f9577d5d-xxxxx.
```

이걸 보고 처음 든 질문 은 이랬다 — *"CPU 사용률 이 높은 건가?"* 그리고 두 번째 질문 — *"제동 이 57% 에서 걸리나? 100% 가 아니고? 누가 57.5 로 제약 을 뒀지?"*

**둘 다 아니다.** 이 알림 은 쿠버네티스 알림 중 가장 많이 오해 되는 것 중 하나 라서, 정리 해 둔다.

---

## 1. 결론 부터 — 57.5% 는 *제약값* 이 아니라 *측정 결과* 다

- **사용률 이 아니다.** 실제 확인 해 보니 그 순간 velero pod 의 CPU 사용 은 `1m` — 거의 0 이었다.
- **임계값 도 아니다.** 아무 도 "57.5 에서 제동" 이라고 설정 한 적 없다.
- 57.5% 의 정체 는 — **측정 구간 동안 지나간 CPU 스케줄링 주기 들 중, 제동(throttle) 이 걸린 주기 의 비율** 이다.

그러니까 이 알림 은 *"CPU 를 많이 쓰고 있다"* 가 아니라 **"쓰려고 할 때마다 limit 벽 에 부딪히고 있다"** 는 뜻 이다. 사용률 과 throttling 은 아예 다른 축 이다.

## 2. 동작 원리 — CFS quota 는 100ms 단위 로 집행 된다

쿠버네티스 의 `limits.cpu` 는 리눅스 **CFS(Completely Fair Scheduler) quota** 로 구현 된다. 핵심 은 *시간 을 잘게 쪼개서 집행* 한다는 것:

1. 시간 이 **100ms 주기(period)** 로 나뉜다.
2. 컨테이너 는 주기 마다 **quota** 를 받는다. `limits.cpu: 2` 면 *매 100ms 마다 최대 200ms 어치* CPU 시간 (코어 2개 몫).
3. 어떤 주기 에서 quota 를 다 써버리면 — **그 주기 의 남은 시간 동안 프로세스 가 강제 로 얼어붙는다(frozen).** 다음 주기 가 시작 되면 다시 실행.

이 "얼어붙은 주기" 가 *throttled period* 다. 커널 은 `nr_periods`(지나간 주기 수) 와 `nr_throttled`(제동 걸린 주기 수) 를 센다. 그리고:

```
throttling 비율 = nr_throttled / nr_periods
```

**5분 간 주기 3,000개 중 1,725개 에서 quota 소진 → 1725 / 3000 = 57.5%.** 이게 알림 의 57.5% 다.

즉 제동 은 *항상 limit 의 100% 를 친 순간* 에 걸린다. 57.5% 는 **그 제동 이 얼마나 자주 걸렸는가** 라는 빈도 통계 다.

## 3. 그럼 사람 이 정한 숫자 는 뭔가

이 알림 뒤 에 사람 이 설정 한 숫자 는 딱 두 개 다:

| 숫자 | 누가 정했나 | 의미 |
|------|-----------|------|
| `limits.cpu: 2` | 내 가 (helm values) | 제동 이 걸리는 **벽** |
| `25%` | kube-prometheus-stack 기본 룰 | 알림 이 뜨는 **임계값** |

알림 룰 (요지) 은 이렇게 생겼다:

```promql
sum(increase(container_cpu_cfs_throttled_periods_total[5m]))
/
sum(increase(container_cpu_cfs_periods_total[5m]))
> 0.25
```

*"최근 5분 간 주기 의 25% 이상 에서 제동 이 걸리면 info 알림."* 우리 케이스 는 57.5% > 25% 라서 발화 한 것 뿐 이다.

## 4. 왜 velero 였나 — 버스트형 워크로드 의 숙명

velero 는 전형적 인 **버스트형** 워크로드 다. 평소 엔 거의 놀다가(1m), 백업 스케줄 이 돌 때 몇 분 간 CPU 를 확 끌어쓴다.

실제 로 타임라인 을 맞춰 보니 — 알림 시각 은 4시간 마다 도는 `hourly-critical` 백업 job 직후 였다. 백업 하는 몇 분 동안 velero 가 2 core 벽 을 계속 치받았고 → throttled 주기 비율 이 치솟았고 → 백업 이 끝나자 알림 도 `[resolved]` 로 저절로 꺼졌다.

이 패턴 (평소 0 → 순간 burst → limit 충돌) 은 백업 · 배치 · 컴파일 · GC 같은 워크로드 에서 아주 흔하다. 그래서 **CPUThrottlingHigh 는 대표적 인 노이즈성 알림** 으로 불린다. 오죽하면 kube-prometheus-stack 에서 severity 가 `info` 다.

## 5. 그래서 언제 조치 해야 하나

판단 기준 은 하나 다 — **throttling 이 *지연(latency)* 으로 이어지는가.**

**조치 불필요 (우리 케이스):**
- 배치성 작업 이고, 몇 분 늦게 끝나도 무방
- 알림 이 주기 작업 시각 과 겹치고 스스로 resolved
- 서비스 응답 시간 에 영향 없음

**조치 필요:**
- 사용자 요청 을 받는 서비스 (API, 웹) 에서 지속 발생 — throttling 은 곧 **tail latency** (p99 폭발) 로 나타난다
- 백업/배치 가 throttling 때문 에 시간 창(window) 을 넘김

**조치 방법 (택 1):**
1. `limits.cpu` 상향 — 벽 을 뒤로 민다 (2 → 3~4)
2. **limit 제거** — CPU 는 압축 가능한(compressible) 자원 이라, requests 만 두고 limit 을 없애는 운영 철학 도 널리 쓰인다 (노드 여유 가 있을 때 마음껏 쓰게)
3. 알림 튜닝 — 특정 네임스페이스 제외 or 임계값 상향

나 는 그냥 둔다 — 백업 은 정상 완료 됐고, info 알림 이 4시간 에 한 번 스쳐 가는 건 비용 이 아니다. **모든 알림 에 반응 하는 것 보다, 알림 의 의미 를 정확히 아는 게 먼저 다.**

## 6. 요약

1. **CPUThrottlingHigh ≠ CPU 사용률 높음.** 사용률 1m 짜리 pod 에서도 뜬다.
2. 제동 은 **항상 limit 100% 에서** 걸린다. 57.5% 는 *제동 이 걸린 주기 의 비율* 이라는 빈도 통계 다.
3. 사람 이 정한 건 `limits.cpu`(벽) 와 알림 임계값 25%(기본값) 둘 뿐.
4. 버스트형 워크로드 (백업·배치) 에선 정상 현상 에 가깝다. **latency 에 영향 줄 때만 조치.**

> 같은 원리 로 — 그라파나 에서 CPU 그래프 가 낮은데 서비스 가 느리다면, `container_cpu_cfs_throttled_periods_total` 을 꼭 봐라. *사용률 은 낮은데 목 이 졸리고 있는* 경우 가 진짜 있다.
