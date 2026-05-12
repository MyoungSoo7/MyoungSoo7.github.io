---
layout: post
title: "WiFi 3-NIC + bash watchdog 로 K3s 노드 floating VIP failover — 2014 Mac Mini 살리기"
date: 2026-05-12 22:35:00 +0900
categories: [infra, kubernetes, networking, devops]
tags: [k3s, wifi, networkmanager, vip, failover, keepalived, watchdog]
---

2014년산 Mac Mini (솔로몬) 의 내장 WiFi 가 무작위로 끊겨서 K3s 노드가 NotReady 되는 일이 반복됐습니다. WiFi 동글 2 개 추가 (AX900 / A3000UA) + 자체 bash watchdog 로 **[내부VIP] floating VIP** 페일오버 구현. keepalived 가 단일 호스트 다중 NIC 시나리오에 맞지 않아서 직접 만든 기록입니다.

> 이 글에서 다루는 것
> - 왜 keepalived 가 안 맞는가
> - bash watchdog + systemd 30 줄로 충분한 이유
> - 실제 페일오버 동작 검증 (disconnect/reconnect)
> - K3s 의 한계 — node-IP 는 여전히 single point
> - 진짜로 막은 것 vs 못 막은 것

---

## 1. 문제 — WiFi 무작위 단절

```
$ kubectl get nodes
solomon   NotReady   <none>   2d
```

조사:
- 솔로몬: 2014 Mac Mini, 내장 WiFi 만 (유선 포트 없음)
- 평균 RTT: 110ms (정상), 가끔 끊김
- 단절 시 etcd VXLAN endpoint 잃음 → flannel 페일

## 2. 하드웨어 보강 — WiFi 동글 2 종

| 인터페이스 | 드라이버 | 칩셋 | 제품 |
|---|---|---|---|
| wlp3s0b1 | 내장 | Broadcom | 2014 Mac Mini |
| wlxb0386cf8d710 | rtw89_8851bu | RTL8851BU | **ipTime AX900 Mini** (WiFi 6) |
| wlxb0386cf4af80 | rtw88_8822bu | RTL8822BU | **ipTime A3000UA** (WiFi 5) |

USB 동글 2 개 다 꽂아도 둘 다 `state DOWN` — NetworkManager 연결 안 함. 직접 연결:

```bash
sudo nmcli device wifi connect "lms" password "xxx" \
  ifname wlxb0386cf8d710 name lms-ax900
sudo nmcli device wifi connect "sky" password "xxx" \
  ifname wlxb0386cf4af80 name sky-a3000ua
```

다른 SSID 로 분산 (`lms` 2.4G, `sky` 5G) → 한 AP 장애 시 다른 쪽 살아남음.

NetworkManager 강성 설정:
```bash
sudo nmcli connection modify lms \
  connection.autoconnect yes \
  connection.autoconnect-retries 0 \
  802-11-wireless.powersave 2     # disable
```

## 3. K3s 의 진짜 문제 — 3-NIC 이 도움 안 됨

3 IP 가 있어도:

| 트래픽 종류 | 영향 |
|---|---|
| 아웃바운드 (솔로몬 → 외부) | ✅ 페일오버 |
| **인바운드 control-plane** | ❌ K3s 는 한 노드 IP 만 알아봄 |
| **flannel VXLAN endpoint** | ❌ 다른 노드 cache 에 .108 만 등록 |

즉 **`[내부VIP]` 이라는 IP 가 죽으면 NIC 가 살아도 K3s 는 죽음.**

해결: floating VIP. .108 이 어떤 NIC 에 있든 무관하게 살아있어야 함.

## 4. 왜 keepalived 안 쓰나

VRRP 의 일반적 시나리오:
```
host1 (master, .108)  ←→  host2 (backup)
   eth0                       eth0
```

내 시나리오:
```
host1 (solomon)
├─ wlp3s0b1   .108?
├─ wlxb...    .108?  ← 이게 되어야 함
└─ wlxb...    .108?
```

단일 호스트의 다중 NIC 사이 IP 페일오버는 VRRP 가 의도한 게 아님. `track_interface` + `notify_script` 로 우회 가능하지만 의외로 복잡. **bash 30 줄이 깔끔.**

## 5. 자체 watchdog — 30 줄

```bash
#!/bin/bash
# /usr/local/sbin/vip-failover.sh
set -u
VIP="[내부VIP]"
NETMASK="24"
PRIORITY_NICS=("wlp3s0b1" "wlxb0386cf8d710" "wlxb0386cf4af80")

pick_active() {
  for nic in "${PRIORITY_NICS[@]}"; do
    [ -d "/sys/class/net/$nic" ] || continue
    [ "$(cat /sys/class/net/$nic/operstate)" = "up" ] || continue
    [ "$(cat /sys/class/net/$nic/carrier)" = "1" ] || continue
    echo "$nic"; return 0
  done
  return 1
}

has_vip() { ip -4 addr show "$1" 2>/dev/null | grep -q "inet ${VIP}/"; }

while true; do
  active=$(pick_active) || { sleep 2; continue; }

  if has_vip "$active"; then
    # 중복 제거
    for nic in "${PRIORITY_NICS[@]}"; do
      [ "$nic" != "$active" ] && has_vip "$nic" && \
        ip addr del "${VIP}/${NETMASK}" dev "$nic" 2>/dev/null
    done
  else
    # 모든 NIC 에서 떼고 active 에 붙임
    for nic in "${PRIORITY_NICS[@]}"; do
      ip addr del "${VIP}/${NETMASK}" dev "$nic" 2>/dev/null || true
    done
    ip addr add "${VIP}/${NETMASK}" dev "$active"
    arping -c 3 -I "$active" -U "${VIP}"   # gratuitous ARP
  fi
  sleep 2
done
```

systemd:
```ini
[Service]
Type=simple
ExecStart=/usr/local/sbin/vip-failover.sh
Restart=always
RestartSec=5s
```

## 6. 실제 페일오버 테스트

```bash
# 정상 상태
$ ip -4 -br addr | grep wl
wlp3s0b1        UP    [내부VIP]/24    ← VIP
wlxb0386cf8d710 UP    [LAN노드]/24
wlxb0386cf4af80 UP    [LAN노드]/24

# 의도적 단절
$ sudo nmcli device disconnect wlp3s0b1
Device 'wlp3s0b1' successfully disconnected.

# 5 초 후 (watchdog 자동 동작)
$ ip -4 -br addr | grep wl
wlxb0386cf8d710 UP    [LAN노드]/24 [내부VIP]/24   ★ VIP 이동
wlxb0386cf4af80 UP    [LAN노드]/24

$ kubectl get node solomon
solomon   Ready   <none>   2d    ← NotReady 안 됨

# 재연결
$ sudo nmcli connection up lms
# 5 초 후
$ ip -4 -br addr | grep wl
wlp3s0b1        UP    [내부VIP]/24 [LAN노드]/24  ★ 복귀
wlxb0386cf8d710 UP    [LAN노드]/24
wlxb0386cf4af80 UP    [LAN노드]/24
```

복귀 시 DHCP 가 새 IP (.114) 도 줘서 듀얼 IP 가 되는데 기능엔 무관. K3s 는 .108 만 보면 되고, .108 이 살아있음.

## 7. 진짜로 막은 것

- ✅ WiFi 카드 1 개 죽어도 노드는 Ready
- ✅ 페일오버 동안 K3s control-plane 통신 끊김 없음 (gratuitous ARP 로 스위치 ARP table 즉시 갱신)
- ✅ etcd 멤버 (이 노드가 마스터일 때) 도 무중단
- ✅ 외부 도메인 200 OK 유지

## 8. 못 막은 것 (한계)

- ❌ 라우터(공유기) 가 죽으면 셋 다 끊김 (당연)
- ❌ 솔로몬 OS 자체가 죽으면 (kernel panic, 디스크 fail) 어떤 NIC 도 무의미
- ❌ 솔로몬 host 의 SSD 가 죽으면 PVC 다 손실 (백업 별건)

이건 결국 **노드 단일점**. control-plane 3-master HA + PVC 다른 노드 분산이 진짜 답.

## 9. 부가 효과 — 솔로몬을 etcd 멤버로 승격 가능

floating VIP 가 있으니 솔로몬도 안정적인 IP 를 가짐 → K3s 3-master 의 멤버로 합류 가능.

```
$ kubectl get nodes
solomon   Ready   control-plane,etcd   2d3h   ★ 마스터 승격
```

다음 글 [K3s 3-Master HA 마이그레이션](/2026/05/12/k3s-3master-ha-sqlite-etcd-migration/) 에서 이어집니다.

---

## 10. 정리 — over-engineering 안 한 것의 가치

| 시도한 것 | 결과 |
|---|---|
| keepalived 단일 호스트 다중 NIC 시도 | 30 분 헛소동, 적합하지 않음 |
| bash watchdog 30 줄 | 검증 통과, 1 시간 |
| systemd autoConnect + powersave off | 보조 안정성 |

**툴이 시나리오에 맞는지 먼저 확인.** 표준 솔루션이 항상 답은 아닙니다.
