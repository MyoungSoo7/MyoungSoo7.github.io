---
layout: post
title: "Load 12인데 CPU 60% Idle? — Linux loadavg가 거짓말하는 순간"
date: 2026-05-16 04:00:00 +0900
categories: [infra, linux]
tags: [linux, loadavg, monitoring, performance, netdata, kernel, troubleshooting]
---

K3s 마스터 노드 르무엘에서 부하 스파이크를 추적하던 중, 새벽 2시 51분에 *Load Average 12.28 / 4 cores* 알람이 떴다. 4코어 머신에서 Load 12면 **300%** — 본능적으로 "이건 죽기 직전이다"라고 생각하게 된다. 그런데 같은 시각에 잡은 `vmstat` 출력은 정반대였다:

```
%Cpu(s): 13.3 us, 23.3 sy, 0.0 ni, 60.0 id, 3.3 wa, 0.0 hi, 0.0 si
```

**CPU의 60%가 idle.** 운영자라면 한 번쯤 마주치는, 그러나 잘 정리된 글이 적은 "loadavg가 진짜 부하를 반영하지 않는 순간"이다. 이번에 그 메커니즘을 라이브 캡처로 분해해봤다.

> 이 글에서 다루는 것
> - Load Average가 실제로 *무엇을* 세고 있는지 (단순 CPU 사용률이 아님)
> - 60% idle인데 Load 12가 나오는 구체적 시나리오
> - fork-heavy 모니터링 에이전트(netdata apps.plugin 등)가 loadavg를 부풀리는 매커니즘
> - 좀비 프로세스가 가속기 역할을 하는 이유
> - 임계치 알람을 1분 vs 5분 평균으로 봐야 하는 이유

---

## TL;DR

| 항목 | 값 |
|---|---|
| 외형 알람 | Load avg 12.28 / 4 cores (307%) |
| 실제 CPU | us 13% + sy 23% = **36% busy, 60% idle** |
| `vmstat` runqueue (r) | 2–3 (정상) |
| `vmstat` blocked (b) | **0** (디스크/네트워크 대기 없음) |
| D-state 프로세스 | **0개** |
| 좀비 프로세스 | **18개** (만성적) |
| 진짜 원인 | netdata apps.plugin · suricata 등 fork-heavy 에이전트가 짧은 R-state 태스크를 폭발적으로 만들어 loadavg sampling에 잡힘 |
| 권고 | 알람은 *5분 평균* + *시간 지속성* 기준으로 보고, 1분 평균 단발 스파이크는 무시 |

---

## 1. 잘못된 직관 — "Load = CPU 사용률"

가장 흔한 오해. **Load Average는 CPU 사용률이 아니다.** 정확한 정의는:

> 5초마다 측정되는 **"실행 가능 상태(R) + 비가로채기 대기 상태(D)" 프로세스 수**의 지수가중 이동평균.

핵심 두 가지:

1. **CPU를 실제로 *쓰고 있는* 프로세스만 세는 게 아니다.** CPU를 *기다리는* 프로세스도 카운트한다.
2. **D-state(uninterruptible sleep)도 포함한다.** 즉 디스크 I/O 대기로 막힌 프로세스도 loadavg를 올린다.

여기까지는 알려진 사실. 그런데 한 가지가 덜 알려져 있다 — **R-state로 *순간 들렀다 나가는* 프로세스도 셈에 잡힐 수 있다**. 5초 sampling 주기에 운 나쁘게 걸리면 카운트. 어떤 워크로드는 이 "운"을 시스템적으로 키운다.

---

## 2. 라이브 캡처 — 무엇이 진짜 일하고 있나

스파이크 도중에 동시에 잡은 데이터:

### 2.1 `top` (정렬: %CPU)

```text
top - 02:51:41 up 31 days, 8:36
load average: 11.60, 7.55, 4.00
Tasks: 296 total, 1 running, 277 sleeping, 0 stopped, 18 zombie
%Cpu(s): 13.3 us, 23.3 sy, 0.0 ni, 60.0 id, 3.3 wa, 0.0 hi, 0.0 si

    PID USER      %CPU   COMMAND
 959537 netdata   20.0   netdata
1492335 iamipro   20.0   top              ← 측정 도구 자기 자신
 960215 netdata   13.3   apps.plugin
 338889 root       6.7   Suricata-Main
3777642 root       6.7   k3s-server
```

- 1초 단위 CPU 점유는 netdata가 최상위지만 20% 정도 — 4코어 시스템에서 사실상 0.8 core 미만
- `dockerd`는 보이지도 않음 (`coredns` 핫픽스 이후 0%로 진정 상태)
- 가장 눈에 띄는 건 **18 zombie** 와 **1 running, 277 sleeping**

### 2.2 `vmstat 1`

```
procs -----------memory---------- ---swap-- -----io---- -system-- -------cpu-------
 r  b   swpd   free   buff  cache   si   so    bi    bo   in   cs us sy id wa st
 0  0 611840 538104 2998224 24109584  0   1   175   392 6496   24 18 12 69  0  0
 1  0 611840 538104 2998224 24109608  0   0     0   360 8247 13470 15 13 69  3  0
 1  0 611840 432712 2998224 24212260  0   0     0   976 6725 8961  15 14 70  2  0
```

- `r` (runqueue): 0–1 정도. 정상.
- `b` (uninterruptible block): **0**. 디스크/네트워크 대기 없음.
- `wa` (iowait): 0–3%. 정상.
- `cs` (context switches): 8k–13k/s. 약간 높지만 평소대로.

### 2.3 D-state 프로세스 직접 카운트

```bash
$ ps -eo state,pid,cmd | awk '$1 == "D"'
(empty)
```

**0개.** I/O로 막힌 프로세스가 단 한 개도 없다.

---

## 3. 모순 정리 — 데이터가 가리키는 결론

| 지표 | 값 | 의미 |
|---|---|---|
| Load avg 1분 | 11.60 | "엄청 바쁘다"는 *전통적 해석* |
| CPU idle | 60% | 실제로는 한가하다 |
| Runqueue (r) | 0–1 | 대기열에 사실상 없다 |
| Block (b) | 0 | I/O 대기 없다 |
| D-state | 0 | uninterruptible 없다 |

**Load 12를 만들 만한 R+D 프로세스가 어디에도 없다.** 그러면 loadavg는 *무엇을* 세고 있는 걸까?

답은 **5초 sampling의 timing**과 **fork-heavy 워크로드의 결합**이다.

---

## 4. fork-heavy 모니터링 에이전트가 loadavg를 부풀리는 매커니즘

netdata의 `apps.plugin`을 보자. 이놈은 `/proc/<pid>/*` 트리를 *모든 프로세스에 대해* 주기적으로 스캔한다. 스캔 단계에서:

1. 부모 프로세스(`apps.plugin`)가 자식을 fork
2. 자식이 짧은 작업(예: 한 디렉터리 stat) 수행 → 거의 즉시 종료
3. 부모가 `wait()` 으로 거둠

이 과정에서 자식은 **수십 밀리초 동안 R-state** 였다가 사라진다. 만약 loadavg sampler가 그 짧은 순간에 우연히 걸리면 카운트된다. 한 번 fork당 확률은 매우 낮지만, *몇 백 번씩* 반복되면 통계적으로 확실히 잡힌다.

여기에 **suricata** (보안 IDS) 같은 멀티스레드 처리기까지 가세하면 R-state 진입 빈도가 더 높아진다.

> 핵심 비유: loadavg는 "복도에 사람이 몇 명 있나"를 매 5초마다 세는 거다. 진짜 *오래 머무는* 사람이 없어도 *지나가는 사람*이 많으면 평균이 올라간다. 그리고 그 사람들은 "60% idle"이라는 결론에는 영향을 안 준다 — 너무 짧게 들렀다 가니까.

---

## 5. 좀비 18개 — 가속기 역할

`top`에서 `18 zombie`가 만성적으로 떠있는 게 보였다. 좀비는 *이미 죽었지만 부모가 `wait()`을 안 해서 PID가 살아있는* 프로세스다. CPU도 메모리도 안 먹지만, **프로세스 테이블 슬롯을 차지하고 있다**.

이게 왜 가속기인가:

- 좀비가 누적된다 = 부모(보통 docker/k3s/모니터 에이전트)의 wait() 호출이 빠진다는 신호
- wait()이 늦으면 자식 종료 직후의 R→Z 전환이 sampling에 더 잘 잡힌다
- 또한 새 fork와 좀비 정리가 동시에 일어나면 짧은 동기화 비용도 발생

본 사례에서 좀비 부모를 추적해보니 대부분 `dockerd` (르무엘만 docker 런타임이라 이 패턴이 두드러짐) + 몇 개의 K3s 관련 프로세스였다.

> 운영 직감: **`top`에서 zombie 카운트가 두 자릿수면 — 그 환경의 fork/wait 패턴이 깨끗하지 않다는 뜻**. 직접적인 장애는 아니지만 다른 메트릭(loadavg 포함)을 흐리는 잡음을 만든다.

---

## 6. 알람 설계 — 1분 vs 5분 vs 15분 평균

`/proc/loadavg`에서 나오는 세 숫자:

```
11.60 (1분)   7.55 (5분)   4.00 (15분)
```

1분 평균은 *순간 노이즈*에 민감하다. 5분 평균은 *지속성*을 본다. 15분 평균은 *추세*를 본다.

본 사례에서 의미 있는 신호는 5분 평균이 4 → 8로 *상승 추세에 있는지* 정도였다. 1분 평균이 12를 찍은 건 거의 부수 효과.

**알람 임계치를 1분 기준으로 잡으면 fork-heavy 워크로드가 있는 환경에서는 끊임없이 false positive가 난다.** 대부분의 모니터링 도구가 기본값으로 1분 평균을 쓰는 게 함정. 권장 패턴:

| 알람 유형 | 평균 창 | 임계치 (n cores 기준) |
|---|---|---|
| 즉시 알람 (page) | 5분 | 1.5 × n |
| 경고 (notify) | 5분 | 1.0 × n |
| 추세 감시 (dashboard) | 15분 | 0.8 × n |
| 1분 평균 | (참고용으로만 표시, 단발 알람 X) | — |

> 본 환경에서 `server-monitor`도 1분 평균으로 ⚠️를 띄우고 있었다. 이번 incident로 5분 기준으로 옮기거나 임계치를 1.0 → 1.2/core로 완화하는 게 합리적이라 결론 냈다.

---

## 7. 그러면 진짜 부하는 어떻게 보나

Load Average만 보면 안 된다는 결론이 났으니, 대체 무엇을 보는가:

### 7.1 즉시 진단 3개 (라이브)

```bash
# 1. CPU 사용률 (top + 5초 정도 관찰)
top -bn3 -d1 | grep -E "Cpu\(s\)|load avg"

# 2. Runqueue + blocked
vmstat 1 5

# 3. D-state 직접 카운트
ps -eo state,pid,cmd | awk '$1 ~ /[DR]/ {print}'
```

### 7.2 정량 메트릭 (대시보드용)

- `node_cpu_seconds_total{mode=~"user|system|iowait"}` (Prometheus)
- `node_load5` *와 함께* `node_cpu_utilization` 을 같이 보기
- `node_procs_running`, `node_procs_blocked`

### 7.3 한 가지 룰

> **Load avg가 임계 넘었는데 CPU idle이 충분히 남아있고 iowait도 낮으면 — 90%는 측정 아티팩트다.** 진짜 자원 부족이면 CPU나 iowait이 *반드시* 올라간다.

---

## 8. 운영 습관 — 이 incident에서 굳힌 것들

> **A. 알람은 5분 평균 + 지속성으로 본다.**  
> 1분 평균의 단발 스파이크는 fork-heavy 환경에서 매우 흔하다. on-call을 깨우는 알람의 신호 대 잡음비를 위해서는 5분 평균이 기본.

> **B. Loadavg가 높을 때 *idle/iowait*을 함께 본다.**  
> 한 줄 룰: `load_5min/n_cores > 0.8` 이면서 `cpu_idle > 30%` *이고* `iowait < 10%` 이면 측정 아티팩트로 의심.

> **C. 좀비 카운트는 fork/wait 위생의 지표다.**  
> 0–1개는 정상. 두 자릿수가 만성적으로 떠있으면 — *직접 장애는 아니어도* 다른 메트릭을 흐리는 잡음 발생. docker/k3s/agent 중 어디서 wait()을 빠뜨리는지 추적해두면 다음에 비슷한 incident에서 빨라진다.

> **D. 모니터링 에이전트의 자체 부하를 가시화한다.**  
> netdata, suricata, prometheus node-exporter 같은 에이전트들이 *자기 자신을* 메트릭에 노출하는지 확인. apps.plugin은 폴링 주기를 늘리거나(`update every 5` 등) 비활성화할 수 있다.

> **E. "근본 원인을 안다고 부르려면 — 그 원인을 *재현* 또는 *역으로 해소*할 수 있어야 한다."**  
> 이번에는 fork-heavy 가설을 직접 재현(에이전트 잠시 멈추고 loadavg 변화 관찰)하지 않았다. 같은 패턴이 다시 나오면 그때 확정하자. 가설로만 남겨두는 것도 솔직한 진단이다.

---

## 마무리

Load Average는 1985년 BSD에서 도입된 메트릭이다. 당시에는 단일 CPU에서 *오래 실행되는* 프로세스가 일반적이었고, "복도에 사람이 몇 명"이 곧 시스템 부담을 잘 반영했다. 2026년의 시스템 — 멀티코어, fork-heavy 모니터링, 컨테이너 런타임, 좀비를 만드는 docker daemon이 섞인 환경 — 에서는 그 직관이 빗나간다.

가끔 "Load 12"라는 숫자에 흔들려서 멀쩡한 시스템을 재시작하거나 OS 재설치를 결심하기 직전에, **`vmstat`과 `ps -eo state`을 5초만 잡아보면** 90%는 false alarm이다. 본 사례도 *Load 12에 OS 재설치를 검토하다가*, 라이브 캡처 덕에 *60% idle*이라는 사실을 확인하고 작업을 중단했다.

> **TL;DR** — Load Average는 *CPU 사용률이 아니라 R+D 프로세스의 짧은 카운트*다. fork-heavy 모니터링 에이전트와 좀비 누적이 결합하면 60% idle 상태에서도 Load 12가 찍힌다. 알람은 *5분 평균 + 지속성*으로, 판정은 *idle/iowait 동시 확인*으로. 1분 평균에 흔들리지 마라.
