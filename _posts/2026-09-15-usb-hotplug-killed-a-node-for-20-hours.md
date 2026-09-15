---
layout: post
title: "USB 동글 하나 더 꽂았을 뿐인데 — 노드가 20시간 죽었다"
date: 2026-09-15 22:03:23 +0900
categories: [devops]
tags: [K3s, etcd, WiFi, NetworkManager, USB, 장애회고, 무선클러스터]
---

오늘 아침 6시 59분 48초, 우리 집 K3s 클러스터의 컨트롤플레인 노드 하나가 네트워크에서 완전히 사라졌다. 원인은 해킹도 정전도 아니었다. **가동 중인 노드에 USB 무선 동글을 하나 더 꽂은 것.** 그 순간 기존 동글의 드라이버가 행에 걸렸고, 노드는 저녁 7시 44분 재부팅될 때까지 20시간 45분 동안 불통이었다.

이 글은 그 하루의 회고다. 핫플러그가 왜 위험했는지, 그 전날 밤 찾아낸 또 하나의 범인(강제로 켜지는 WiFi 절전)은 무엇이었는지, 그리고 진단 과정에서 밟은 함정 네 개를 적는다. 모든 수치는 이 클러스터에서 직접 측정한 값이다.

## 타임라인

| 시각 | 사건 |
| --- | --- |
| 전날 밤 | etcd 쿼럼 지연 조사 → WiFi 절전이 원인으로 확정, 런타임으로 끔 |
| 06:59:48 | 노드에 두 번째 USB 동글 핫플러그 → 기존 동글 드라이버 행, 노드 불통 |
| 07:10 | 새 동글 제거 — 효과 없음 |
| 07:36 | 기존 동글 뽑았다 재삽입 — 효과 없음 |
| 19:44 | 재부팅 — 즉시 복구 |
| 19:46:37 | 노드 Ready 복귀, 이후 Kafka 브로커·ES·OCR 순차 복구 |

USB 재삽입으로도 안 풀렸다는 게 핵심이다. 행은 동글이 아니라 **커널 쪽 드라이버 상태**에 걸려 있었고, 그건 버스를 다시 꽂는다고 리셋되지 않는다. 교훈은 짧다: **동글 교체는 끄고 한다.** 살아 있는 노드의 USB 버스는 생각보다 공유된 자원이라, 새 장치의 삽입(버스 리셋·전력 변동)이 옆 장치의 펌웨어를 데려갈 수 있다.

## 배경: 전날 밤 잡은 진짜 범인 — 강제로 켜지는 WiFi 절전

이 노드가 왜 그날 밤 수술대에 있었냐면, etcd 쿼럼 지연 때문이었다. 우리 클러스터는 [노드 여섯 대가 전부 무선]({% post_url 2026-09-13-wireless-k8s-node-asymmetric-latency-spof %})인데, etcd 멤버 3대 중 2대의 USB 동글에서 **WiFi 절전(power save)이 켜져** 있었다.

절전이 켜진 링크의 서명은 뚜렷하다. 같은 구간 핑이 최소 14ms, 최대 **1031ms** — 패킷마다 라디오를 깨우는 비용이 붙는다. etcd 기본 하트비트가 100ms, 선거 타임아웃이 1000ms 인 시스템([etcd tuning][etcd-tuning])에서 왕복 1초는 사실상 멤버가 깜빡이는 것과 같다.

`iw dev <if> set power_save off` 로 끄면 되는데, 함정이 있다. 우분투는 `/etc/NetworkManager/conf.d/default-wifi-powersave-on.conf` 라는 파일을 기본으로 싣고 오고, 내용은 이거다:

```ini
[connection]
wifi.powersave = 3
```

`3` 은 enable — NetworkManager 는 재연결·재부팅 때마다 절전을 **도로 켠다**. 런타임 `iw` 만으로는 이길 수 없다. 값의 의미는 공식 설정 문서([802-11-wireless 설정][nm-settings])에 있다: 0=default, 1=ignore, 2=**disable**, 3=enable.

영구 해법은 사전순으로 나중에 읽히는 오버라이드 파일이다 ([NetworkManager.conf][nm-conf] 는 conf.d 를 파일명 순으로 읽고 나중 값이 이긴다):

```bash
# /etc/NetworkManager/conf.d/zz-wifi-powersave-off.conf
[connection]
wifi.powersave = 2

sudo nmcli general reload conf
```

오늘 재부팅이 뜻하지 않게 이 픽스의 검증 기회가 됐다. 부팅 직후 확인하니 절전이 다시 켜져 있었고(오버라이드 설치 전이었다), 파일을 심고 나서는 꺼진 상태가 유지된다. 실측으로 닫은 셈이다.

## 진단에서 밟은 함정 네 개

**① Ready 는 거짓말을 한다.** 노드가 죽고도 `kubectl get nodes` 는 한동안 Ready 를 보여준다. k3s 노드는 컨트롤플레인 쪽으로 자기가 터널을 걸기 때문에 상태 갱신이 끊긴 시점과 NotReady 판정 사이에 갭이 있다. 죽은 *정확한 시각*이 필요하면 `kube-node-lease` 네임스페이스의 Lease 객체 `renewTime` 을 본다 — 쿠버네티스의 공식 하트비트 메커니즘이다([Nodes — Heartbeats][k8s-nodes]). 이번에 06:59:48 이라는 초 단위 시각을 준 것도 lease 였고, 그 시각이 사용자의 "아침에 동글 하나 더 꽂았는데" 와 분 단위로 일치하면서 원인이 확정됐다.

**② 같은 벤더의 MAC 은 남일 수 있다.** 서브넷을 스캔하니 낯선 IP 에 우리 동글들과 같은 벤더 대역(b0:38:6c)의 MAC 이 떠 있었다. "다른 IP 로 붙었나?" — 아니었다. SSH 호스트키를 비교하니 다른 키. 같은 제품군 어댑터를 쓰는 **다른 집 기기**였다. 장치의 신원은 MAC 이 아니라 호스트키로 확정한다. ([어제 쓴 부재 증명 글]({% post_url 2026-09-14-proving-a-usb-device-is-absent %})과 같은 원리다 — 존재/부재/신원은 전부 실측으로만.)

**③ 복구 직후의 잡은 DNS 로 죽는다.** 노드 Ready 복귀 3분 뒤 아침에 실패했던 배치 잡을 재실행했더니 `Could not resolve host` 로 또 죽었다. 노드는 Ready 인데 그 노드의 CoreDNS·파드망은 아직 덜 서 있던 것. 몇 분 두고 재시도하니 성공했다(대상 20건 전부 처리, 에러 0). 복구 직후의 실패는 새 장애가 아니라 여진일 수 있다.

**④ 순간 스톨은 경보가 아니다.** 낮 동안 남은 2/3 쿼럼을 감시하는데 etcd healthz 가 한 번 `context deadline exceeded` 를 뱉었다. 달려가 보니 3연속 재검사는 전부 ok — 무선 특유의 순간 스톨이었다. 무선 클러스터의 감시는 **단발 실패로 울리면 안 되고**, N연속 실패로만 울려야 한다. 이번엔 10초 간격 3연속으로 잡았다.

## 그래도 버틴 것: outbox 의 20시간

노드에는 단일 Kafka 브로커가 있었다. 즉 20시간 동안 클러스터의 이벤트 발행이 전부 멈췄다. 그런데 복구 후 확인한 지표는:

```
outbox_pending_count 0
outbox_dlq_published_total 0
발행 에러 폴링 3,543회 → 복구 후 증가 정지
```

Transactional Outbox 패턴이라 이벤트는 브로커가 아니라 **DB 에 먼저** 쌓인다. 브로커가 죽어 있던 20시간 동안 발행기는 3,543번 실패했지만 데이터는 한 건도 안 잃었고, 브로커가 돌아오자 밀린 걸 전부 배출하고 pending 0 으로 수렴했다. 장애는 막지 못해도 장애를 **버티는** 설계는 만들 수 있다.

## 정리

- 살아 있는 노드에 USB 동글 핫플러그는 도박이다. 기존 동글 드라이버가 행에 걸리면 재삽입으로 안 풀리고 재부팅만이 답이다. **교체는 끄고.**
- 우분투의 WiFi 절전은 기본 conf 가 재부팅마다 강제로 켠다. `iw` 런타임 명령이 아니라 NetworkManager 오버라이드 파일(`wifi.powersave = 2`)로 꺼야 하고, 재부팅으로 검증해야 끝이다.
- 죽은 시각은 Ready 가 아니라 node lease 로, 장치 신원은 MAC 이 아니라 호스트키로, 복구 직후 실패는 여진인지부터, 무선 감시는 N연속 실패로만.
- etcd 멤버 3대 중 1대가 하루 종일 빠져 있어도 클러스터는 돌았다 — 대신 그 하루는 여유가 0이었다. HA 의 여유분은 이런 날 쓰라고 있는 것이다([k3s HA embedded etcd][k3s-ha]).

무선 클러스터 시리즈의 앞 글들: [신호 세기는 링크 품질이 아니다]({% post_url 2026-09-13-wifi-dbm-is-not-link-quality-beacon-loss %}), [USB 연장선 하나로 11dB]({% post_url 2026-09-14-usb-extension-cable-wifi-dongle-11db %}).

---

## References

- NetworkManager 공식 문서 — [NetworkManager.conf(5)][nm-conf] (conf.d 읽기 순서와 오버라이드)
- NetworkManager 공식 문서 — [802-11-wireless settings][nm-settings] (`powersave` 값 0–3 의 의미)
- etcd 공식 문서 — [Tuning][etcd-tuning] (하트비트 100ms·선거 타임아웃 1000ms 기본값과 네트워크 지연)
- Kubernetes 공식 문서 — [Nodes: Heartbeats][k8s-nodes] (kube-node-lease 의 renewTime)
- K3s 공식 문서 — [High Availability Embedded etcd][k3s-ha]

[nm-conf]: https://networkmanager.dev/docs/api/latest/NetworkManager.conf.html
[nm-settings]: https://networkmanager.dev/docs/api/latest/settings-802-11-wireless.html
[etcd-tuning]: https://etcd.io/docs/v3.5/tuning/
[k8s-nodes]: https://kubernetes.io/docs/concepts/architecture/nodes/
[k3s-ha]: https://docs.k3s.io/datastore/ha-embedded
