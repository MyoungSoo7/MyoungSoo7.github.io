---
layout: post
title: "노트북 노드를 UPS 로 — k3s 클러스터에 정전 감지기 붙이기"
date: 2026-09-26 14:28:05 +0900
categories: [Homelab, Kubernetes]
tags: [홈랩, k3s, 정전감지, sysfs, power_supply, systemd, cordon, Telegram, IoT]
---

홈랩 k3s 클러스터의 노드 중 하나는 노트북이다. 서버로 쓰기엔 애매한 기계라고 생각했는데, 뒤집어 보면 **배터리가 달린 유일한 노드**다. 정전이 나면 데스크톱 노드들은 즉시 꺼지지만, 이 노트북은 배터리로 몇 시간을 버틴다.

그래서 이 노드를 **UPS 겸 정전 감지기**로 쓰기로 했다. 목표는 세 가지였다.

1. 어댑터 전원이 끊기면 폰으로 바로 알림
2. 배터리로 버티는 동안 잔량을 구간마다 알림, 복구되면 정전 시간을 알림
3. 배터리가 바닥나기 전에, 쿠버네티스가 이 노드에 새 파드를 보내지 않게 막기

## 1. 재료 — 리눅스는 이미 전원 상태를 파일로 준다

별도 센서는 필요 없다. 리눅스 커널은 전원 장치 상태를 `/sys/class/power_supply/` 아래 파일로 노출한다. 이 노트북에서는 이렇게 보인다.

```
/sys/class/power_supply/
├── ADP1/online        # 어댑터 연결: 1, 분리: 0
└── BAT1/
    ├── capacity       # 잔량 0–100 (%)
    ├── status         # Charging / Discharging / Not charging ...
    ├── charge_now     # 현재 충전량 (µAh)
    └── current_now    # 순간 전류 (µA)
```

각 파일의 의미는 커널 문서 [sysfs-class-power ABI](https://www.kernel.org/doc/Documentation/ABI/testing/sysfs-class-power)에 정의돼 있다. `capacity` 는 *"Fine grain representation of battery capacity"*, 값 범위는 0–100 이다.

남은 시간은 `charge_now / current_now` 로 대략 추정할 수 있다(µAh ÷ µA = 시간).

### 함정: 방전 전류의 부호

처음에는 `current_now > 0` 일 때만 남은 시간을 계산했다. 그런데 커널 문서를 다시 읽으니 이렇게 적혀 있었다.

> *"Negative values are used for discharging batteries, positive values for charging batteries"*

규약상 **방전 중에는 음수**다. 반면 이 노트북(ACPI 배터리 드라이버)은 방전 중에도 양수를 주는 경우가 있다. 드라이버마다 다르다는 뜻이다. 그대로 두면 규약을 따르는 기기에서는 남은 시간이 영원히 "계산 중" 으로 나온다. **절댓값**을 쓰는 것으로 고쳤다. 테스트를 이 기기에서만 돌렸다면 못 잡았을 버그다.

## 2. 감지 로직 — 단순하지만 세 가지는 챙긴다

5초마다 `ADP1/online` 을 읽는 루프다. Python 표준 라이브러리만 쓴다. 단순한 루프지만 실전에서 필요한 것이 세 가지 있었다.

**① 디바운스.** 케이블이 헐거우면 0/1 이 순간적으로 튄다. 상태가 **10초 이상 유지돼야** 전이로 인정한다.

**② 구간 알림의 중복 방지.** 잔량 50·30·15·10% 에서 알리는데, 절전에서 깨어나거나 폴링 사이에 **29% → 9% 처럼 여러 구간을 한 번에 건너뛰는** 경우가 있다. 첫 구현은 여기서 알림을 두 번 보냈다. 건너뛴 구간을 한꺼번에 처리하고, 알림은 한 번만 보내도록 고쳤다.

**③ 알림 큐.** 이게 핵심이다. **정전이면 공유기도 꺼진다.** 노트북은 살아 있어도 인터넷이 없으니 알림을 보낼 수 없다. 그래서 전송에 실패한 알림은 로컬 파일(JSON Lines)에 쌓아 두고, 네트워크가 돌아오면 원래 시각을 붙여 순서대로 보낸다.

```
(지연 전송 · 원래 03:12:40) ⚠️ 어댑터 전원이 끊겼습니다 ...
(지연 전송 · 원래 04:05:11) 🔋 배터리로 버티는 중 — 잔량 50% ...
✅ 어댑터 전원이 복구됐습니다. 정전 시간 1시간 27분.
```

실시간 알림은 아니지만 "언제 끊겼고 얼마나 버텼는지" 는 정확히 남는다. **실시간으로 받으려면 공유기와 모뎀에 따로 UPS 가 있어야 한다.** 이건 소프트웨어로 풀 수 없는 문제다.

## 3. 알림 — 텔레그램 봇으로 sendMessage 만

알림은 이 노드에 이미 있는 텔레그램 봇으로 보낸다. [Bot API](https://core.telegram.org/bots/api) 의 `sendMessage` 한 번이면 된다.

같은 봇이 대화도 받고 있어서(`getUpdates` 폴링) 충돌을 걱정했는데, 충돌하는 건 **업데이트를 받는 쪽끼리**다. 문서도 getUpdates 는 웹훅이 설정돼 있으면 동작하지 않는다고 적을 뿐이다. 보내기만 하는 `sendMessage` 는 수신 쪽과 무관하다.

토큰은 스크립트나 환경변수에 넣지 않았다. **전송하는 순간에 봇의 설정 파일에서 읽는다.** 그리고 전송 실패 로그에는 예외 **종류만** 남긴다. 예외 메시지에는 요청 URL, 즉 토큰이 섞일 수 있기 때문이다.

## 4. 쿠버네티스와 연동 — cordon 만, drain 은 하지 않는다

배터리가 10% 아래로 내려가면 이 노드를 **cordon** 한다. [쿠버네티스 문서](https://kubernetes.io/docs/concepts/architecture/nodes/)의 표현으로는 노드를 *"mark it unschedulable"* 하는 것이다. 새 파드는 이 노드에 배치되지 않고, 이미 떠 있는 파드는 그대로 둔다. ([`kubectl cordon`](https://kubernetes.io/docs/reference/kubectl/generated/kubectl_cordon/))

**drain(파드 축출)은 일부러 넣지 않았다.** 배터리 10% 에서 파드를 쫓아내면 다른 노드로 옮겨 가는데, 정전이라면 그 다른 노드들도 이미 꺼져 있다. 괜히 재스케줄링 폭풍만 만든다. 대신 두 가지 안전장치를 넣었다.

- **내가 건 cordon 만 푼다.** 정전 전에 누군가 이미 cordon 해 둔 노드라면 손대지 않는다. 전원이 복구돼도 풀지 않는다. 사람이 점검 중이던 노드를 자동화가 풀어 버리는 사고를 막기 위해서다.
- **최소 권한.** 클러스터 관리자 자격증명이 아니라 이 노드의 **kubelet 자격증명**을 쓴다. [Node Authorization 문서](https://kubernetes.io/docs/reference/access-authn-authz/node/)에 따르면 NodeRestriction 어드미션 플러그인이 켜져 있을 때 kubelet 은 **자기 노드 객체만** 수정할 수 있다. 관리자 자격증명보다 사고 반경이 훨씬 작다. 실제 cordon 전에 `--dry-run=server` 로 권한이 통과하는지 먼저 확인했다.

### 솔직한 한계

k3s 의 컨트롤플레인은 다른 노드들에 있다. **집 전체가 정전이면 API 서버도 같이 꺼져서 cordon 요청이 닿지 않는다.** 이 경우에는 "cordon 실패" 알림만 큐에 쌓였다가 복구 후에 도착한다.

그러니 cordon 이 실제로 의미 있는 경우는 **이 노드만 전원이 빠진 상황**이다. 멀티탭이 꺼졌거나, 콘센트가 불량이거나, 누가 어댑터를 뽑은 경우다. 기능을 붙이기 전에 이 한계부터 적어 두는 게 맞다고 생각했다.

## 5. 상시 실행 — systemd user 서비스

```ini
[Service]
ExecStart=/usr/bin/python3 %h/.local/bin/power-watch/power-watch.py
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
```

- `Restart=always` 로 스크립트가 죽어도 다시 뜬다.
- 사용자 세션이 없어도 돌도록 linger 를 켜 두었다.
- 상태(현재 AC 여부, 정전 시작 시각, 이미 보낸 구간, 내가 건 cordon 여부)를 파일에 저장한다. 그래서 **정전 도중 서비스가 재시작돼도** 정전 시간과 구간 알림이 이어진다.

## 6. 어떻게 테스트했나 — 가짜 sysfs

어댑터를 수십 번 뽑았다 꽂을 수는 없다. 그래서 sysfs 경로를 환경변수로 바꿀 수 있게 만들었다. 임시 디렉토리에 `ADP1/online`, `BAT1/capacity` 같은 **가짜 파일**을 만들고, 값을 바꿔 가며 시나리오를 재현했다.

| 시나리오 | 확인한 것 |
|---|---|
| 1 → 0, 0.3초 뒤 1, 다시 0 | 순간 튐은 무시되고 알림은 1번만 |
| 잔량 45 → 29 → 9 | 구간을 건너뛰어도 알림 중복 없음 |
| 9% 도달 | cordon 호출, 알림 |
| 0 → 1 | 복구 알림 + 정전 시간 + uncordon |
| 토큰 없음(전송 실패) | 큐에 쌓임 → 이후 원래 시각을 붙여 순서대로 전송 |

여기에 전송 대신 로그만 남기는 dry-run 모드를 더해서, 실제 텔레그램과 쿠버네티스를 건드리지 않고 로직만 검증했다. 실제 경로는 마지막에 한 번씩만 확인했다. 테스트 메시지 1건, 그리고 cordon/uncordon 의 server-side dry-run 이다.

실제로 어댑터를 뽑는 최종 테스트는 아직 남아 있다.

## 정리

- **"쓸모없는 노드" 가 "유일하게 정전을 목격하는 노드" 가 됐다.** 하드웨어 특성(배터리)이 곧 역할이다.
- 코드보다 설계에서 더 많이 배웠다.
  - 정전이면 네트워크도 없다 → 큐
  - 자동화가 사람의 작업을 되돌리면 안 된다 → 내가 건 cordon 만 푼다
  - 자동 조치는 상황 전체에서 효과가 있어야 한다 → drain 제외, 한계 명시
- 이 노트북에는 가속도계, 지자기 센서, 힌지 각도 센서, 카메라도 있다. 충격 감지나 자석 문열림 센서도 같은 방식(sysfs 읽기 → 상태 전이 → 알림 큐)으로 만들 수 있다.

## References

- Linux kernel — [ABI: sysfs-class-power](https://www.kernel.org/doc/Documentation/ABI/testing/sysfs-class-power)
- Kubernetes — [Node Authorization](https://kubernetes.io/docs/reference/access-authn-authz/node/) · [Nodes](https://kubernetes.io/docs/concepts/architecture/nodes/) · [kubectl cordon](https://kubernetes.io/docs/reference/kubectl/generated/kubectl_cordon/)
- Telegram — [Bot API](https://core.telegram.org/bots/api)
- K3s — [Documentation](https://docs.k3s.io/)
