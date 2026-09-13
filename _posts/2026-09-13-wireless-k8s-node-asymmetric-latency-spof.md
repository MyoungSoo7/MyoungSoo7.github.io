---
layout: post
title: "핑 손실 0% 인데 응답이 2.7초 — 무선 K3s 노드 하나가 앓는 날의 해부"
date: 2026-09-13 18:27:23 +0900
categories: [infra, network]
tags: [wifi, 802.11, kubernetes, k3s, usb, eproto, local-path, kubelet-lease, homelab]
---

집의 K3s 클러스터는 6노드 전부 무선이다. 연구용 클러스터라 이 제약은 의도된 것이고, 그래서 "무선 링크가 약해지면 쿠버네티스에서 실제로 무엇이 어떤 순서로 무너지는가"를 관찰할 기회가 종종 온다. 오늘 워커 노드 한 대가 하루 종일 그 표본이 되어 주었다. 겉보기 증상은 이랬다 — **노드는 Ready, 파드는 Running, 내부에서 치는 NodePort 는 200. 그런데 바깥에서 보는 서비스만 간헐적으로 502.** 이 글은 그 하루를 시간 순서가 아니라 **층위 순서**로 해부한 기록이다: 무선 링크 → USB 버스 → kubelet → 스토리지 → 진단 방법론.

> 같은 날 같은 클러스터에서 나온 앞선 두 글 — [dBm 은 링크 품질이 아니다]({% post_url 2026-09-13-wifi-dbm-is-not-link-quality-beacon-loss %}), [신호가 가장 센 노드가 가장 느렸다]({% post_url 2026-09-13-wifi-strongest-signal-worst-link-retry-measurement %}) — 이 *신호와 측정*을 다뤘다면, 이 글은 약해진 링크가 **쿠버네티스 계층에서 무엇으로 번역되는가**를 다룬다.

## 1. 손실 0% 와 지연 2.7초는 공존한다

문제 노드를 향해 다른 노드에서 핑을 쳐 보면 이렇다 (본문의 수치는 전부 오늘 이 클러스터에서 직접 잰 값이다):

```
--- 문제 노드로, 이웃 노드에서 ---
20 packets transmitted, 20 received, 0% packet loss
rtt min/avg/max = 3.9/399.3/2701.8 ms
```

손실은 0 인데 평균 0.4초, 최악 2.7초. 유선 감각으로는 모순이지만 802.11 에서는 자연스러운 조합이다. 무선 MAC 계층은 프레임이 깨지면 **스스로 재전송**하고, 스테이션이 낮은 전송 레이트로 떨어지면 프레임들이 큐에서 **대기**한다. IP 계층 위에서 보면 패킷은 결국 도착하므로 손실이 아니라 **지연**으로 나타난다. 재전송과 버퍼링이 손실을 지연으로 바꿔치기하는 것이다.

더 중요한 관찰은 **방향 비대칭**이다. 같은 시각, 문제 노드에서 게이트웨이로 나가는 핑은 평균 16–28 ms 로 멀쩡했다. 즉 그 노드에 SSH 로 들어가 "밖으로" 핑을 쳐 보는 통상의 점검으로는 **아무 이상도 안 보인다.** `iw dev <if> link` 를 떠 보면 이유가 드러난다 — 송신(tx)과 수신(rx)의 비트레이트가 따로 논다. 오늘 이 노드는 신호가 -61 dBm 에서 -76 dBm 까지 미끄러지는 동안 수신 쪽이 HE-MCS 1–2 (17–26 Mbit/s) 바닥까지 떨어졌고, 절전 모드는 꺼져 있음을 확인했으니(`iw dev <if> get power_save` → off) 절전 탓도 아니다. 802.11 링크의 레이트 적응은 방향별로 독립이라, **한 방향만 앓는 링크**가 성립한다.

교훈: 무선 노드의 링크 품질은 **반드시 양방향에서** 재야 한다. 노드 안에서 밖으로 재는 것만으로는 인바운드 열화가 구조적으로 안 보인다.

## 2. 그 위층: 터널은 왜 502 를 냈나

외부 트래픽은 Cloudflare Tunnel([cloudflared](https://github.com/cloudflare/cloudflared)) 커넥터가 클러스터 안에서 origin 서비스로 프록시한다. 커넥터 로그에는 이렇게 남았다:

```
ERR Unable to reach the origin service ... dial tcp <ClusterIP>:<port>: connection refused / i/o timeout
```

커넥터는 다른 노드에서 돌고 있었고, origin 파드는 문제 노드에 있었다. 커넥터 → 문제 노드 방향이 정확히 위에서 잰 "앓는 방향"이다. 파드 자체는 멀쩡해서, 이웃 노드에서 NodePort 로 직접 치면 200 이 나왔다. 그래서 증상이 "간헐 502" — 인바운드 지연이 튈 때만 dial timeout 이 나는 것이다. **노드 Ready ≠ 서비스 정상**이라는 당연한 명제가, 무선에서는 "한 방향만 느린 링크"라는 형태로 구현된다.

## 3. 동글 교체 시도와 USB 에러 -71

신호가 계속 미끄러지길래 더 좋다는 USB 무선 동글(RTL8822BU 계열, 커널 [rtw88](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/net/wireless/realtek/rtw88) 드라이버)을 하나 더 꽂아 봤다. 결과는 커널 로그의 반복 패턴으로 남았다:

```
usb 1-1.4: new high-speed USB device
rtw_8822bu 1-1.4:1.0: Firmware version 30.20.0, H2C version 13
rtw_8822bu 1-1.4:1.0: write register 0xc4 failed with -71
usb 1-1.4: USB disconnect, device number 12
(재열거 → 펌웨어 로드 → -71 → 분리, 무한 반복)
```

여기서 -71 은 커널 USB 스택의 `-EPROTO` 다. 커널 공식 문서 [USB Error codes](https://www.kernel.org/doc/html/latest/driver-api/usb/error-codes.html)는 이를 비트스터프 오류, 응답 패킷 미수신 등 **버스 수준 프로토콜 오류**로 규정한다. 드라이버나 설정의 문제가 아니라 접점·전원·기기 결함처럼 물리층에 가까운 실패라는 뜻이다. 실제로 이 동글은 "인식을 못 하는" 게 아니라 **인식 → 펌웨어 로드까지 가서 초기화 도중 죽는** 것이었고, 이 구분이 중요하다. `lsusb` 에 보인다는 것과 동작한다는 것 사이에는 펌웨어 로드와 레지스터 초기화라는 긴 계단이 있다.

## 4. 좋은 동글을 뽑는 순간: lease 가 시계다

교체를 시도하며 잘 동작하던 동글을 뽑자 노드는 통째로 사라졌다. 이때 사고의 타임라인을 가장 정확히 알려준 건 핑도 SSH 도 아니고 **kubelet 의 노드 lease** 였다. 쿠버네티스는 노드마다 `kube-node-lease` 네임스페이스에 Lease 객체를 두고 kubelet 이 주기적으로 갱신하게 한다([Leases 공식 문서](https://kubernetes.io/docs/concepts/architecture/leases/)). 갱신이 멈춘 시각이 곧 링크가 죽은 시각이다:

```
kubectl -n kube-node-lease get lease <node> -o jsonpath='{.spec.renewTime}'
```

오늘 이 값은 동글을 뽑은 시각(17:57:44 KST)에 얼어붙었고, 잠시 뒤 노드 컨디션이 NotReady 로 넘어갔다([Node status 문서](https://kubernetes.io/docs/reference/node/node-status/)). 복구도 같은 방법으로 확인했다 — 동글을 다시 꽂고 lease 가 다시 흐르기 시작한 시각(18:04:19 KST)이 복구 시각이다. 무선 노드를 굴린다면 lease 의 `renewTime` 이 가장 값싸고 정직한 블랙박스다.

## 5. 파드는 왜 대피하지 못했나: local-path PV 의 못박기

노드가 NotReady 가 되면 쿠버네티스는 파드를 다른 노드로 옮기려 한다. 그런데 이 노드의 서비스들(사진 서버, 메모 서버)은 옮겨지지 못하고 그대로 하드 다운됐다. 이유는 스토리지다. 이 클러스터는 [local-path-provisioner](https://github.com/rancher/local-path-provisioner) 를 쓰는데, 이 방식의 PV 는 특정 노드의 로컬 디스크 경로 위에 만들어지고 PV 에 그 노드로의 nodeAffinity 가 박힌다 — 쿠버네티스의 [local 볼륨](https://kubernetes.io/docs/concepts/storage/storage-classes/#local) 일반의 성질이다. 확인해 보면:

```
kubectl get pv -o jsonpath='...nodeAffinity...'
→ 사진 DB·라이브러리·메모 데이터 전부 이 노드에 고정
```

즉 **약한 무선 링크의 노드 + local-path PV = 그 서비스의 단일 장애점(SPOF)** 이다. 파드는 스케줄러가 옮길 수 있어도 데이터는 못 옮긴다. "노드가 죽으면 파드가 대피하니까 괜찮다"는 가정은 스토리지 계층에서 조용히 무효가 된다. 이건 무선이라 생긴 문제가 아니라 무선이 **드러낸** 문제다 — 유선 노드도 죽을 수 있고, 그때도 똑같이 못 옮긴다. 무선은 그 리허설을 자주 시켜줄 뿐이다.

## 6. 진단 방법론에서 얻은 것 두 가지

**핑이 안 간다고 죽은 게 아니다.** 이 클러스터의 다른 노드 하나는 `net.ipv4.icmp_echo_ignore_all=1` 로 ICMP 응답을 정책적으로 끄고 있다([ip-sysctl 문서](https://www.kernel.org/doc/html/latest/networking/ip-sysctl.html)). 장애 대응 중에 이 노드로 핑을 쳤다면 "여기도 죽었다"고 오진했을 것이다. 핑 무응답의 반례 확인(SSH 포트, kubelet 상태)을 습관으로 둬야 한다.

**측정 대상의 정체를 MAC 으로 검증하라.** 초기 측정에서 나는 SSH 별칭이 가리키는 IP 를 그대로 믿고 엉뚱한 기기(같은 대역의 다른 장치)를 문제 노드로 오인해 잰 적이 있다. `ip neigh` 로 IP–MAC 대응을 확인하고, 쿠버네티스가 아는 노드 IP(`kubectl get nodes -o wide`)와 대조한 뒤에야 측정이 유효해졌다. DHCP 가 도는 무선 환경에서는 "이 IP = 그 노드"라는 가정이 자주 낡는다.

## 7. 무선 전제 안에서의 처방

이 클러스터에서 유선 전환은 선택지가 아니다(연구 목적의 의도된 제약). 그 전제 안에서 오늘 내린 처방은:

- **하드웨어**: -71 을 내는 동글은 소프트웨어로 살릴 수 없다 — 폐기. 남은 동글은 USB 연장 케이블이 도착하면 금속 섀시와 포트 밀집부에서 떨어뜨려 안테나 위치를 확보한다(도착 전까지는 열화 상태로 운용하되, 아래 감시로 커버).
- **감시**: lease `renewTime` 워처 + 외부 도메인 200 워처. 노드 Ready 만 보는 감시는 이 장애 모드를 통과시킨다.
- **배치**: local-path PV 를 쓰는 서비스는 그 노드의 링크 품질이 곧 서비스 SLO 라는 사실을 받아들이고, 다음 개선으로 해당 PV 의 노드 재배치(링크가 안정적인 노드로 데이터 이사)를 검토한다.

한 줄 요약 — 무선 K3s 노드의 장애는 "끊김"보다 **"한 방향만 느려짐"** 으로 먼저 오고, 그 신호는 노드 밖에서 안으로 재야만 보이며, 시계는 kubelet lease 가 갖고 있고, 피해 반경은 local-path PV 가 정한다.

## References

- Linux 커널 공식 문서, [USB Error codes](https://www.kernel.org/doc/html/latest/driver-api/usb/error-codes.html) — `-EPROTO(-71)` 의 정의
- Linux 커널 공식 문서, [IP Sysctl](https://www.kernel.org/doc/html/latest/networking/ip-sysctl.html) — `icmp_echo_ignore_all`
- Linux 커널 소스, [drivers/net/wireless/realtek/rtw88](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/net/wireless/realtek/rtw88) / [rtw89](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/net/wireless/realtek/rtw89)
- Kubernetes 공식 문서, [Leases](https://kubernetes.io/docs/concepts/architecture/leases/) · [Node status](https://kubernetes.io/docs/reference/node/node-status/) · [Storage Classes — local](https://kubernetes.io/docs/concepts/storage/storage-classes/#local)
- Rancher, [local-path-provisioner](https://github.com/rancher/local-path-provisioner)
- Cloudflare, [cloudflared](https://github.com/cloudflare/cloudflared)

*본문의 RTT·신호 세기·비트레이트·커널 로그·lease 타임스탬프는 2026-09-13 필자의 홈랩 K3s 클러스터에서 직접 채취·실측한 것이다.*
