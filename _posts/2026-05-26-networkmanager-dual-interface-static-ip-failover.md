---
layout: post
title: "노드 IP 가 DHCP 로 매번 바뀐다 — NetworkManager 로 *유선/무선 둘 다 같은 정적 IP* 박기 + k3s --node-ip 명시 + autoconnect-priority 페일오버"
date: 2026-05-26 02:30:00 +0900
categories: [infra, networking, kubernetes]
tags: [k3s, networkmanager, nmcli, static-ip, dhcp, autoconnect, homelab, node-ip]
---

홈랩 노드 한 대(*david*)가 매일 다른 IP 로 깨어났다. 어제 .107, 오늘 .113, 다음에 보니 .116. DHCP 가 풀에서 잘못 골라주는 게 아니라 *유선·무선 두 인터페이스가 동시에 DHCP 로 받아서* 그 중 하나가 올라온다. 사용자가 *''두 개 다 .113 으로 고정해''* 라고 했을 때, 단순히 "yes / no" 가 아니라 *''두 개의 인터페이스에 같은 정적 IP, 어떻게 안전하게''* 를 풀어야 하는 문제가 됐다.

이 글은 그 *3-line nmcli 명령* 의 *배경* 을 같이 정리한다. *왜* 그 명령이어야 하고, *어디서* 다른 선택지가 있고, *k3s* 가 그 결과를 어떻게 reflect 하는지.

---

## TL;DR

| 단계 | 명령 | 효과 |
|---|---|---|
| 1. 유선·무선 둘 다 static .113 | `nmcli con mod <con> ipv4.method manual ipv4.addresses 10.0.0.113/24 ipv4.gateway 10.0.0.1 ipv4.dns "10.0.0.1 1.1.1.1"` | DHCP 의존성 제거 |
| 2. 유선 우선 (priority 높게) | `nmcli con mod netplan-enp2s0 connection.autoconnect-priority 100` | 둘 다 후보일 때 wired 가 이긴다 |
| 3. WiFi 는 *자동 안 올림* (충돌 방지) | `nmcli con mod sky connection.autoconnect false` | 둘 다 동시에 .113 잡으면 ARP conflict → WiFi 는 명시적으로 올릴 때만 |
| 4. k3s 가 IP 변경 인지 | `K3S_AGENT_ARGS="--node-ip=10.0.0.113 --node-external-ip=10.0.0.113"` + `systemctl restart k3s-agent` | Node object 의 InternalIP 가 .113 으로 갱신 |
| 5. cordon 풀기 | `kubectl uncordon david` | SchedulingDisabled 해제 |

---

## 1. 왜 *두 인터페이스 같은 IP* 가 까다로운가

같은 서브넷에서 *두 NIC* 에 *같은 IP* 를 주면 ARP 가 답을 *둘 중 하나로* 보낸다. 어느 쪽이 이길지 *비결정적*. 패킷의 절반이 한쪽 NIC, 절반이 다른 쪽 NIC 로 가면 TCP connection 이 꼬인다.

그래서 *''두 인터페이스 같은 IP''* 의 *실제 의미* 는 *''한 번에 하나만 active''*. 옵션:

1. **Linux bonding (active-backup)** — `bond0` 가 wired + wireless 를 묶고 한쪽만 active. 가장 견고하지만 설정 복잡.
2. **NetworkManager autoconnect 우선순위** — 한쪽이 link-up 이면 다른 쪽은 자동 비활성. 설정 간단.
3. **systemd-networkd `RequiredForOnline`** — netplan + systemd-networkd 조합. Ubuntu 의 기본이지만 NetworkManager 와 충돌 가능.

이번에 채택한 건 *옵션 2* — 가장 적은 변경으로 *유선 우선, 무선은 수동 폴백* 을 구현.

---

## 2. 현재 상태 확인부터

```bash
$ ssh admin@<current-ip> "ip -br addr; nmcli -t -f NAME,DEVICE,STATE,AUTOCONNECT-PRIORITY connection show --active"
enp2s0           UP   10.0.0.116/24 fe80::2d8:61ff:fe2d:51ef/64
wlxb0386cf8d624  UP   10.0.0.113/24 fe80::2cae:8073:961e:2d46/64

netplan-enp2s0:enp2s0:activated:0
sky:wlxb0386cf8d624:802-11-wireless:activated:0
```

확인:
- 두 인터페이스 *모두 active* — 둘 다 IP 받음
- enp2s0(유선) = .116 (오늘 DHCP 가 새로 줌)
- WiFi(`sky` 라는 connection profile 명, 안방 AP 이름인 듯) = .113 (오늘 DHCP)
- 둘 다 `AUTOCONNECT-PRIORITY=0` (기본값)

목표 상태:
- enp2s0 = static .113, priority 100 (wired 우선)
- sky = static .113, autoconnect=false (수동 폴백)

---

## 3. 위험 — SSH 가 *어느 인터페이스로* 들어와 있는지

설정 중에 NetworkManager 가 *현재 SSH 세션이 쓰는 인터페이스* 의 IP 를 바꾸면 *SSH 가 끊긴다*. 끊기면 *명령 중간에서 멈춰서 노드가 어정쩡한 상태* 가 된다 (한쪽 인터페이스는 새 설정, 다른 쪽은 옛 설정).

확인:

```bash
$ ssh admin@10.0.0.116 "ss -tn | grep ':22'"
ESTAB  0  0  10.0.0.116:22  10.0.0.108:54932
```

`10.0.0.116` — 즉 *유선* 으로 들어와 있다. 그러면 *유선 IP 를 바꾸는 명령* 은 *현재 SSH 를 끊는다*. 두 가지 방법:

**방법 A**: WiFi 로 SSH 다시 잡고, 유선 IP 변경. (WiFi 가 살아있는 동안)

**방법 B**: 변경 명령을 *background + disown* 으로 노드에서 자체 실행. SSH 가 끊겨도 노드 안에서 계속 실행 후 재접속.

방법 B 가 안전하다. SSH 끊긴 *원인* 이 명령의 *목적* 이면 정상 동작.

---

## 4. 실제 명령 — *3-line nmcli*

```bash
# 4-1. NM profile 수정 (활성 연결엔 즉시 영향 X)
sudo nmcli con mod 'netplan-enp2s0' \
  ipv4.method manual \
  ipv4.addresses 10.0.0.113/24 \
  ipv4.gateway 10.0.0.1 \
  ipv4.dns "10.0.0.1 1.1.1.1" \
  connection.autoconnect-priority 100

sudo nmcli con mod 'sky' \
  ipv4.method manual \
  ipv4.addresses 10.0.0.113/24 \
  ipv4.gateway 10.0.0.1 \
  ipv4.dns "10.0.0.1 1.1.1.1" \
  connection.autoconnect false \
  connection.autoconnect-priority 10
```

이 시점에서는 *running 연결* 은 그대로. *NM profile 파일* (`/etc/NetworkManager/system-connections/*.nmconnection`) 만 수정됨. *다음에 connection 이 올라올 때* 이 설정이 적용됨.

```bash
# 4-2. swap 을 background 로 (SSH 끊김 예상)
nohup sudo bash -c '
  sleep 2
  nmcli con down sky                # WiFi 다운 — .113 IP 해제
  sleep 2
  nmcli con down netplan-enp2s0     # 유선 다운 (현재 .116 해제)
  sleep 1
  nmcli con up netplan-enp2s0       # 유선 다시 올림 → 새 설정 적용 → .113
  sleep 2
  systemctl restart k3s-agent       # k3s 가 새 IP 로 다시 register
' >/tmp/ipfix.log 2>&1 & disown
echo 'swap kicked off'
```

`disown` 이 핵심. SSH 세션이 hang-up 신호를 보내도 background process 가 *parent 와 분리* 되어 끝까지 실행됨.

`nmcli con up netplan-enp2s0` 가 끝나면 enp2s0 가 *새* 정적 IP `.113` 으로 올라온다. 내 SSH 세션 (원래 .116 에 묶임) 은 끊긴다 — *정상*.

---

## 5. 결과 확인

15 초 뒤 다시 SSH (이번엔 .113):

```bash
$ ssh admin@10.0.0.113 "ip -br addr | head -3"
lo               UNKNOWN   127.0.0.1/8 ::1/128
enp2s0           UP        10.0.0.113/24 10.0.0.116/24 ...
wlxb0386cf8d624  UP        (IPv6 only)
```

흠 — `10.0.0.116` 이 *아직 enp2s0 에 붙어있다*. NetworkManager 가 *새 IP 추가* 만 하고 *이전 DHCP lease 의 IP* 는 해제 안 함. 잔여 IP 라 통신엔 문제 없지만 *깔끔하지 않음*. 정리:

```bash
$ ssh admin@10.0.0.113 "sudo ip addr del 10.0.0.116/24 dev enp2s0"
$ ssh admin@10.0.0.113 "ip -br addr show enp2s0"
enp2s0   UP   10.0.0.113/24 fe80::...
```

이제 깔끔.

---

## 6. k3s 가 새 IP 를 *어떻게* 알게 하나

`nmcli` 가 OS 레벨의 IP 를 바꿨지만 *k3s 의 Node object* 는 따로 등록 시점의 IP 를 들고 있다.

```bash
$ kubectl get node david -o wide
NAME    STATUS  INTERNAL-IP       ...
david   Ready   10.0.0.116   # ← 아직 옛 IP
```

해법은 두 단계:

### 6.1 `K3S_AGENT_ARGS` 에 `--node-ip` 명시

```bash
$ ssh admin@10.0.0.113 "cat /etc/systemd/system/k3s-agent.service.env"
K3S_URL=https://<control-plane-ip>:6443
K3S_TOKEN=<redacted>
K3S_AGENT_ARGS="--node-ip=10.0.0.113 --node-external-ip=10.0.0.113"
```

(swap 스크립트의 마지막 `systemctl restart k3s-agent` 가 이 env 를 다시 로드하면서 `--node-ip` 가 적용됨)

`--node-ip` 명시는 *DHCP 가 IP 를 자주 바꾸는 환경* 에서 필수. 명시 안 하면 k3s 가 *''default route 가 가는 인터페이스의 첫 번째 IPv4''* 를 자동으로 픽 — 인터페이스 두 개면 어느 쪽일지 비결정적.

### 6.2 Kubelet 이 Node 재등록

```bash
$ sleep 12 && kubectl get node david -o wide
NAME    STATUS  INTERNAL-IP        ...
david   Ready   10.0.0.113   # ← 갱신 완료
```

`systemctl restart k3s-agent` 만으로 *대부분의 경우* Node IP 갱신. 안 되면 강제 재등록:

```bash
$ kubectl delete node david
# (k3s-agent 가 다시 register — 새 IP 로)
```

⚠️ delete node 는 *pod 들이 잠시 evict* 되므로 운영 중에는 신중히. 이번엔 *swap 도중* 이라 어차피 pod 영향 있어서 무리없음.

---

## 7. 페일오버 — *유선 빠지면 WiFi 가 살리나*

설정상 `sky` 의 `autoconnect=false`. *자동* 으로는 안 살아남 (충돌 방지). 명시적으로:

```bash
# 유선 케이블 빠진 상황을 가정
$ sudo nmcli con down netplan-enp2s0
$ sudo nmcli con up sky      # WiFi 가 .113 으로 올라옴
```

*자동 페일오버* 가 필요하면 다음 옵션 중 하나:

**옵션 1 — `connection.autoconnect-priority` 만 다르게**:
- enp2s0: priority 100, autoconnect=true
- sky: priority 10, autoconnect=true
- 둘 다 active 가능 (충돌 ARP 위험) — *권장 X*

**옵션 2 — udev/systemd 로 link-down 시 sky up**:
```bash
# /etc/systemd/system/wifi-failover.service
[Service]
ExecStart=/usr/local/bin/wifi-failover.sh
```
*복잡하고 깨지기 쉬움*.

**옵션 3 — Linux bonding active-backup**:
```yaml
# /etc/netplan/01-bond.yaml
network:
  bonds:
    bond0:
      interfaces: [enp2s0, wlxb0386cf8d624]
      addresses: [10.0.0.113/24]
      parameters: { mode: active-backup, primary: enp2s0 }
```
*가장 견고*. 다만 WiFi 가 bond slave 가 되면 SSID 설정이 까다로움.

홈랩이라면 옵션 3 이 *correct answer*. 이번엔 `autoconnect=false` 의 *manual fallback* 로 충분.

---

## 8. 서버체크봇 같은 *외부 monitor* 의 config 갱신

server-monitor 의 `config.yml` 도 david 의 *지난 IP* 를 들고 있었다:

```yaml
- name: 데이비드
  host: 10.0.0.107   # ← 옛 IP (수 시간 전)
  port: 22
  user: david
```

수정:

```yaml
- name: 데이비드
  host: 10.0.0.113   # ← 고정 후 영구
  port: 22
  user: david
```

그리고 *봇 프로세스 재시작* 이 필요했다 — config 는 파일에서 *시작 시* 한 번만 읽는다. 메모리에 들고 있다가 다음 `/서버` 명령에 *옛 IP* 로 SSH 시도 → 실패.

```bash
$ kill 86129          # 옛 봇 PID (config 캐시 들고 있음)
$ cd /Users/lms/server-monitor && nohup ./server-monitor -mode bot -config config.yml > /tmp/bot.log 2>&1 &
$ pgrep -lf 'server-monitor.*bot'
99236 ./server-monitor -mode bot ...
```

> *교훈*: 외부 도구 (모니터링·alerting·CI runner) 의 *노드 IP* 도 *함께* 갱신해야 한다. *클러스터 안* 의 갱신만으로는 부족.

---

## 9. *''static IP''* 가 *DHCP* 보다 항상 좋은가

홈랩에서는 거의 *그렇다*. 하지만 *production cloud* 에서는 *아니다*. EC2/GKE 에서는 *DHCP 가 항상* 같은 IP 를 준다 (인스턴스 lifecycle 동안). cloud-init / metadata API 가 *node-ip* 을 제공하니 k3s 도 자동 인식. 그쪽에선 static 박을 이유가 없다.

홈랩의 *문제* 는 *DHCP 풀이 작고 + 기기가 자주 들락날락하고 + 라우터의 DHCP 정책이 갤럭시탭이나 노트북에 우선권을 주는* 식의 *조용한 비결정성*. 그래서 *''내 노드만 static''* 으로 격리하는 게 운영의 단순함을 산다.

---

## 10. 다음 단계

이 글의 후속:
1. `K3S_AGENT_ARGS` 를 *cloud-init / Ansible* 로 자동화 — 노드 추가 시 *수동 편집* 막기
2. `static IP table` 을 *git* 으로 관리 (DHCP 예약 + nmcli profile 두 곳) — *single source of truth*
3. Linux bonding 으로 옵션 3 적용 — 자동 페일오버

작은 명령이지만 *그 뒤의 모델* 을 정리해두는 게 *동일 사고 재발 방지* 의 9 할.

---

> 작성: 2026-05-26. 환경: Ubuntu 26.04, NetworkManager 1.50, K3s v1.35.4. 노드: david (worker, 6 코어 / 16GB / Intel NUC).
