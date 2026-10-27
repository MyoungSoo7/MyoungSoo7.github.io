---
layout: post
title: "감시자는 누가 감시하나 — 파수꾼의 카나리 세 겹과, 오늘 밤 꺼진 노드 하나"
date: 2026-10-27 22:52:51 +0900
categories: [Security, AI]
tags: [watchman, secops-agent, dead-mans-switch, falco, alertmanager, kubernetes, canary]
---

> *Quis custodiet ipsos custodes?* — 감시자는 누가 감시하는가. (유베날리스, 『풍자시』 6권)

**파수꾼(Watchman)**은 홈랩 K3s 클러스터의 Alertmanager·Falco 경보를 받는 SecOps 에이전트입니다. 경보가 오면 읽기 전용 도구로 원인을 조사하고, 판정과 조치 **제안**을 텔레그램 카드로 보냅니다. 한 달 회고는 [앞 글]({% post_url 2026-10-26-watchman-one-month-after-submission %})에 정리했습니다. 이 글은 그 회고에서 빠진 질문 하나만 다룹니다.

**파수꾼이 조용할 때, 그건 클러스터가 평화로운 걸까, 아니면 파수꾼이 눈이 먼 걸까?**

마침 오늘 밤 전기를 아끼려고 노드 하나(solomon)를 껐습니다. 그래서 이 질문을 실험실이 아니라 실제 운영에서 시험해 볼 수 있었습니다. 글에 나오는 수치는 모두 오늘(10/27) 파수꾼의 `/state`와 감사로그에서 직접 읽은 값입니다.

## 1. 문제: 침묵은 두 가지 뜻을 가진다

경보 시스템이 고장 나면 어떻게 될까요? 대개 **아무 일도 일어나지 않습니다.** Prometheus가 죽어도, Alertmanager 설정이 깨져도, 웹훅 인증서가 만료돼도 경보는 오지 않습니다. 그리고 경보가 오지 않는 상태는 평화로운 상태와 겉보기에 똑같습니다.

이 문제의 고전적인 답은 **데드맨 스위치**입니다. 손을 떼면, 즉 신호가 끊기면 울리는 장치입니다. kube-prometheus는 이를 `Watchdog`이라는 경보로 기본 제공합니다. [공식 런북](https://runbooks.prometheus-operator.dev/runbooks/general/watchdog/)의 설명은 이렇습니다.

> This is an alert meant to ensure that the entire alerting pipeline is functional. This alert is always firing ... If not firing then it should alert external systems that this alerting system is no longer working.

규칙의 표현식은 `vector(1)`입니다. 항상 참이므로 항상 울립니다. 이 경보가 **도착하지 않는 것**이 바로 경보입니다.

파수꾼은 이 원리를 세 겹으로 쌓았습니다. 겹마다 증명하는 구간이 다릅니다.

```
 [Falco on 노드 N] ──► falcosidekick ──► Alertmanager ──► watchman ──► 텔레그램
 └──────── ③ 노드별 카나리 ────────┘
 └──────────────── ② Falco 카나리 (탐지 경로 전체) ────────────────┘
                                   └── ① Watchdog 하트비트 ──┘
```

## 2. 첫째 겹 — Watchdog 하트비트 (10/7)

가장 쉬운 겹입니다. Alertmanager가 `Watchdog`을 파수꾼에게 계속 보내고, 파수꾼은 마지막 수신 시각만 기록합니다. `HEARTBEAT_STALE_S`(운영값 1,200초, 즉 20분) 동안 소식이 없으면 끊김 카드를 한 장 보내고, 신호가 돌아오면 복구 카드를 한 장 보냅니다.

설계에서 중요했던 결정은 하나입니다. **Watchdog 은 조사 파이프라인에 들어가지 않습니다.** HTTP 핸들러가 받는 즉시 걸러내므로, 조사 슬롯·LLM·실행 기록을 전혀 타지 않습니다. 이유는 간단합니다. 경보 폭주로 조사 슬롯이 가득 차서 503을 돌려주는 순간이 하트비트가 가장 필요한 순간이기 때문입니다. 이때 하트비트까지 503에 막히면, 바쁜 상태가 고장으로 오진됩니다.

오늘 값은 이렇습니다.

```json
"heartbeat": {"enabled": true, "stale_s": 1200, "last_age_s": 357, "count": 458, "lost": false}
```

**한계:** Watchdog은 Prometheus 안에서 태어납니다. 그래서 Prometheus → Alertmanager → 파수꾼 구간만 증명합니다. 정작 보안 경보의 출발점인 **Falco**가 살아 있는지는 전혀 알려 주지 않습니다.

## 3. 둘째 겹 — Falco 카나리 (10/8)

이 겹은 실제 사건에서 나왔습니다. 10월 7일에 Falco 오탐 예외를 튜닝하자 Falco 경보가 **0건**이 됐습니다. 튜닝이 성공한 걸까요, 아니면 Falco가 죽은 걸까요? 근거가 없었습니다. 손으로 카나리를 한 번 쏘아 보고 15초 만에 도착하는 걸 확인한 뒤에야 판정할 수 있었습니다.

그래서 이 확인을 자동화했습니다. 카나리 워크로드는 **자기 컨테이너 안의 `/etc/shadow`를 읽습니다.** Falco 기본 룰이 확실히 울리는 동작입니다. 경보는 진짜 탐지 경로(Falco → sidekick → Alertmanager → 파수꾼)를 그대로 거쳐 도착합니다. 파수꾼은 이 경보를 조사 슬롯에 넣기 전에 떼어 내고, 수신 시각과 지연(`lag_s`)만 기록합니다.

여기서 조심할 점이 하나 있습니다. **"카나리처럼 보이는 경보"를 무조건 무시하면, 그 자체가 탐지를 피하는 구멍이 됩니다.** 그래서 카나리 판정은 룰·네임스페이스·파드 이름 접두사·컨테이너·명령·파일 등 **일곱 조건이 모두 맞을 때만** 내립니다. 하나라도 다르면 일반 경보로 정식 조사합니다. `resolved` 재전송은 걸러 내되 생존 증거로 세지 않습니다. 무수신 허용 시간 `FALCO_CANARY_STALE_S`는 3시간(10,800초)입니다.

## 4. 셋째 겹 — 노드별 카나리, 그리고 "1/6 만 증명하던" 구멍

둘째 겹을 붙인 날 바로 구멍이 보였습니다. 카나리는 처음에 CronJob이었는데, **20번 실행이 전부 lemuel 노드에 떴습니다.** 결국 Falco 여섯 개 중 하나만 증명하고 있었던 겁니다. 나머지 다섯 노드의 Falco는 죽어도 알 수 없었습니다.

지금 카나리는 DaemonSet(`watchman-falco-canary`)입니다. 노드마다 시각을 엇갈려 한 시간에 한 번씩 울립니다. 파수꾼은 `FALCO_CANARY_HOSTS`에 적힌 노드별로 마지막 수신을 따로 추적합니다. 한 노드가 STALE 시간 동안 조용하면 **그 노드만** 카드 한 장, 돌아오면 복구 한 장입니다. 경로 전체가 끊긴 동안에는 노드별 카드를 내지 않고 전체 카드 한 장으로 묶습니다. 노드 다섯 장이 쏟아지면 진짜 원인(공통 경로)이 묻히기 때문입니다.

이 단계에서 두 가지를 더 고쳤습니다.

- **재기동이 시계를 0 으로 돌려놓는 문제(10/8).** 그날만 세 번 배포했습니다. 감시 창이 3시간인데 3시간 안에 재배포가 이어지면, 죽은 노드를 **영원히** 잡지 못합니다. 그래서 해시 체인 감사로그의 `falco_canary*` 행에서 마지막 수신과 노드별 상태를 되살리게 했습니다. 끊긴 상태로 재기동되면 끊김 카드는 다시 내지 않고, 노드가 돌아오면 복구 카드만 냅니다.
- **카드가 원인 후보만 나열하던 문제(10/18).** david·isagal이 클러스터에서 빠졌을 때, 카드는 "falco 파드? 카나리 파드? 노드?"를 나란히 늘어놓기만 했습니다. 지금은 Node 객체 상태를 먼저 조회해서 "클러스터에서 빠진 노드(404)"나 "NotReady"를 첫 줄에 씁니다.

## 5. 실전: 오늘 밤 solomon 을 껐다

오늘 저녁 전기를 아끼려고 solomon을 cordon·drain한 뒤 전원을 내렸습니다. 클러스터 쪽 이야기는 [정산 글]({% post_url 2026-10-27-settlement-18-to-6-the-consumers-nobody-listed %})에 있습니다. 파수꾼이 본 것은 다음과 같습니다(KST, 감사로그 기준).

| 시각 | 사건 |
| --- | --- |
| 22:03:25 | solomon 카나리 마지막 수신 (`lag_s` 263) |
| (그 뒤) | solomon 전원 차단 |
| 22:43:51 | `SentinelTargetDown`(node=solomon) 경보 수신 |
| 22:46:26 | 카드 발송 — **"판정: 🔧 운영 장애 (보안 사고 아님)"** · 근거 `up{job="sentinel"} == 0`, 노드 NotReady/Unreachable · 신뢰도 높음 |
| 내일 01:03 무렵 (예정) | 카나리 3시간 무수신 → solomon 노드 끊김 카드 |

판정은 맞았습니다. 공격이 아니라 노드가 사라진 것입니다. 다만 파수꾼은 **그게 의도된 일이라는 것까지는 모릅니다.** 운영자의 의도는 클러스터 상태 어디에도 기록되지 않기 때문입니다. "운영 장애"라는 판정 자체가 정직한 표현입니다.

### 쿠버네티스는 아직 "Running"이라고 말한다

이 장면에서 가장 흥미로웠던 건 아래 출력입니다. 전원이 꺼진 지 한참 지났는데도 API는 이렇게 보여 줍니다.

```
watchman-falco-canary-5szrr   1/1   Running   0   19d   10.42.3.125   solomon
```

이건 버그가 아니라 문서에 적힌 동작입니다. 노드가 unreachable이 되면 노드 컨트롤러가 `NoExecute` taint를 붙이고, 일반 파드는 기본 300초 뒤 퇴거됩니다. 그런데 [DaemonSet 파드는 `node.kubernetes.io/unreachable`·`not-ready` 를 `tolerationSeconds` 없이 견디도록 생성](https://kubernetes.io/docs/concepts/workloads/controllers/daemonset/#taints-and-tolerations)되기 때문에 **절대 퇴거되지 않습니다.** 그리고 파드 상태를 고쳐 쓸 kubelet은 꺼진 기계 안에 있습니다. 그래서 API에 남은 "Running"은 마지막으로 전해진 소식일 뿐입니다.

카나리가 **파드 상태를 묻지 않고 경보가 실제로 도착했는지만 세는** 이유가 바로 이것입니다. 상태는 보고받는 값이고, 도착은 직접 관측한 값입니다. 감시자의 감시는 언제나 후자 위에 세워야 합니다.

### 263초

부수적인 관측도 하나 있습니다. 평소 카나리 탐지→수신 지연은 다른 노드에서 30초 안팎이었는데, solomon만 꾸준히 **262~263초**였습니다. solomon은 예전부터 CPU 병목으로 apiserver 응답이 느리던 노드입니다. 카나리는 생존뿐 아니라 **노드마다의 탐지 지연**까지 공짜로 재 주고 있었던 셈입니다. (전원을 내린 직후 ilwon·lemuel 카나리 지연도 150~180초로 올라갔습니다. 원인은 아직 확인하지 못했고, 내일 아침 값을 다시 볼 예정입니다.)

## 6. 그리고 발견한 것 — 기대 목록도 계약이다

`/state`를 읽다가 이 줄에서 멈췄습니다.

```json
"falco_canary": {"enabled": true, "stale_s": 10800, "count": 1201, "lost": false,
                 "hosts_expected": 5, "hosts_lost": 1}
```

solomon은 아직 3시간이 지나지 않았습니다. 그런데 이미 **1개 노드가 끊긴 상태**입니다. 감사로그를 보니 이렇게 남아 있었습니다.

```
2026-10-15  falco_canary_host_lost  {"isagal": 10849}
2026-10-17  falco_canary_host_lost  {"david": 10853}
```

isagal은 퇴역한 뒤 기대 목록에서 빠졌습니다. david도 클러스터에서 빠졌고 지금은 전기를 아끼려고 전원까지 내려 둔 상태인데, 기대 목록에는 아직 남아 있습니다. 운영 설정은 지금도 `FALCO_CANARY_HOSTS = lemuel,ilwon,solomon,david,louise`입니다. 그래서 10월 17일부터 열흘 동안 `hosts_lost`는 **영구히 1**이었습니다.

이 상태가 무서운 이유는 다음과 같습니다. 끊김 카드는 한 번만 나갑니다(같은 사실을 반복해서 알리지 않는 설계입니다). 그 뒤로 "1"은 평소 값이 됩니다. 그러면 **진짜로 두 번째 노드가 죽어서 2가 되기 전까지, 지표만 봐서는 아무 변화도 보이지 않습니다.** 정상 상태의 기준선에 이미 고장이 하나 섞여 있는 겁니다.

같은 날 쓴 [정산 글]({% post_url 2026-10-27-settlement-18-to-6-the-consumers-nobody-listed %})의 결론과 정확히 같은 모양입니다. 거기서는 지워진 DB를 FDW 설정 한 줄이 계속 붙잡고 있었고, 여기서는 지워진 노드를 환경변수 한 줄이 계속 붙잡고 있습니다. **"무엇이 있어야 하는가"를 적은 목록도 계약입니다.** 클러스터가 줄어들 때 이 목록을 갱신하지 않으면, 감시 장치가 거짓말을 하는 게 아니라 **영원히 같은 진실만 반복합니다.**

고칠 방향은 두 가지입니다.

1. **기대 목록을 손으로 적지 않는다.** Node 객체에서 도출합니다. 단, "존재하는 노드 = 기대 노드"로 두면 노드가 통째로 사라졌을 때 기대 목록에서도 같이 빠져서 탐지가 안 됩니다. 그래서 *퇴역은 사람이 명시적으로 선언하고, 그 외의 소멸은 끊김으로 취급*하는 비대칭이 필요합니다.
2. **"오래 끊긴 노드"를 별도 상태로 노출한다.** N일 이상 끊긴 노드는 "퇴역 선언 대기"로 따로 세어, 기준선이 오염되지 않게 합니다.

오늘 밤 solomon 카드가 나간 뒤에는 `hosts_lost`가 2가 될 겁니다. 하나는 열흘 묵은 david, 하나는 방금 꺼진 solomon입니다. 둘 다 고장이 아니라 사람이 일부러 끈 노드입니다. 설정을 어떻게 정리할지는 클러스터 주인(사람)이 결정할 일이므로, 이 글을 쓴 시점에는 손대지 않았습니다.

## 맺으며

세 겹을 다시 정리합니다.

| 겹 | 증명하는 구간 | 허용 침묵 | 오늘 |
| --- | --- | --- | --- |
| ① Watchdog | Prometheus → Alertmanager → 파수꾼 | 20분 | 정상, 수신 458 |
| ② Falco 카나리 | Falco → sidekick → … → 파수꾼 | 3시간 | 정상, 수신 1,201 |
| ③ 노드별 | 노드 N 의 Falco 하나하나 | 3시간 | 5개 중 1개 끊김 (david, 클러스터 제외·전원 내림) → 곧 2개 |

감시자를 감시하는 일은 결국 이 질문 하나로 모입니다. **"조용하다"를 "괜찮다"로 읽어도 되는 근거가 있는가.** 파수꾼은 그 근거를 매시간 스스로 만들어 냅니다. 그리고 오늘 배운 것은, 그 근거를 판정하는 **기준선 자체도 낡는다**는 사실입니다.

---

## References

- Prometheus Operator, ["Watchdog" runbook](https://runbooks.prometheus-operator.dev/runbooks/general/watchdog/), kube-prometheus runbooks.
- Prometheus Operator, [`kubePrometheus-prometheusRule.yaml`](https://github.com/prometheus-operator/kube-prometheus/blob/main/manifests/kubePrometheus-prometheusRule.yaml) — `Watchdog` 규칙(`expr: vector(1)`).
- Kubernetes Documentation, ["DaemonSet — Taints and tolerations"](https://kubernetes.io/docs/concepts/workloads/controllers/daemonset/#taints-and-tolerations).
- Kubernetes Documentation, ["Taints and Tolerations — taint based evictions"](https://kubernetes.io/docs/concepts/scheduling-eviction/taint-and-toleration/) — 일반 파드의 기본 `tolerationSeconds=300`.
- watchman-agent 커밋 `f36f767`(하트비트), `d1222bf`(Falco 카나리), `bc8f0e2`(노드별), `40a52e3`(재기동 복원), `04fbc9f`(Node 상태 힌트, #228).
