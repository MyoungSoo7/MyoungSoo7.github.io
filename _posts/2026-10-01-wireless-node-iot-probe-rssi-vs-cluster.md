---
layout: post
title: "신호 세기와 클러스터 반응을 같은 시계로 — 무선 노드 3대에 붙인 측정기, 첫 1시간"
date: 2026-10-01 00:07:07 +0900
categories: [infra, wireless]
tags: [wifi, rssi, iot, k3s, prometheus, grafana, daemonset, tcp, rto, homelab]
---

홈랩 K3s 클러스터 6대 중 3대(louise·isagal·solomon)는 일부러 무선으로 둔다. 무선 IoT 조건에서 쿠버네티스 노드가 어떻게 버티는지 보려는 연구용 설정이다. 그런데 지금까지 쓴 무선 글([dBm 은 링크 품질이 아니다](/2026/09/13/wifi-dbm-is-not-link-quality-beacon-loss/), [RSSI 4점 실측과 변동성](/2026/09/20/wireless-cluster-rssi-variability-optimization/))은 전부 **그 순간 한 번 잰 값**이었다. 신호가 흔들릴 때 클러스터가 실제로 어떻게 반응하는지는 같은 시계 위에 올려 본 적이 없다.

그래서 측정기를 만들어 운영 클러스터에 붙였다. 친구에게 IoT 과제로 줄 만한 걸 찾다가 시작한 일인데, 과제의 핵심은 "신호가 약하다"가 아니라 **"신호가 이만큼 약해지면 시스템이 이렇게 된다"는 인과를 데이터로 잇는 것**이라고 봤다. 아래 그래프가 첫 1시간 결과다.

![무선 노드 3대의 RSSI와 apiserver TCP 연결 RTT, 2026-09-30 23:04~10-01 00:06, 30초 간격](/assets/images/wifi-probe/wifi-probe-first-hour.png)

*그림: 위는 신호 세기(RSSI, dBm), 아래는 각 노드에서 컨트롤 플레인 apiserver 까지의 TCP 연결 시간 중앙값. 빨간 선 -67·-75 dBm 은 아래 "기준선" 절 참조. 본인 실측.*

## 무엇을 재는가 — 신호와 결과를 한 번에

측정기는 무선 노드 3대에만 뜨는 파드 하나다. 30초마다 다음을 잰다.

| 무엇 | 어디서 | 왜 |
| --- | --- | --- |
| 신호 세기·링크 품질 | 커널의 `/proc/net/wireless` | 원인 쪽 변수 |
| 인터페이스 up/down | `/sys/class/net/<if>/operstate` | 끊김 자체 |
| **기본 경로가 어느 NIC 인가** | `/proc/net/route` (metric 최솟값) | 아래에서 설명 — 이게 제일 중요했다 |
| apiserver 3대(:6443)까지 **TCP 연결 시간** 5회 | 직접 connect | 결과 쪽 변수 |
| 게이트웨이 ping 5회 | ICMP | 무선 구간만 따로 |

ping 만 재지 않은 이유가 있다. 쿠버네티스 노드가 살아 있다고 인정받는 건 kubelet 이 apiserver 에 TCP 로 붙어서 상태를 보고할 때다([Kubernetes: Leases — Node heartbeats](https://kubernetes.io/docs/concepts/architecture/leases/#node-heartbeats)). 그러니 "클러스터 입장에서 이 노드가 괜찮은가"에 가장 가까운 값은 게이트웨이 ping 이 아니라 **apiserver 까지의 TCP 연결 시간**이다. 노드의 Ready 상태는 kube-state-metrics 가 이미 내보내고 있어서, 신호·RTT·Ready 가 모두 같은 Prometheus 시계에 모인다.

`/proc/net/wireless` 는 오래된 Wireless Extensions 인터페이스다. 커널 무선 문서는 새 개발을 cfg80211/nl80211 로 하라고 하고, WE 는 기본 기능만 호환으로 남아 있다고 적는다([Linux Wireless: About Wireless-Extensions](https://wireless.docs.kernel.org/en/latest/en/developers/documentation/wireless-extensions.html)). 그래도 파일 하나 읽으면 되니 권한이 가장 적게 드는 경로라 이걸 골랐다. 이 선택의 대가는 바로 아래에서 나온다.

## 첫 1시간에 나온 것

**1) isagal 은 무선 노드인데 트래픽은 유선으로 나가고 있었다.** 기본 경로를 찍어 보니 isagal 은 무선 동글(`wlx…`)이 아니라 유선 `eno4` 로 나간다. 그래프 아래 주황 선의 RTT 0.47 ms 는 **무선을 잰 값이 아니다.** 신호 세기(대체로 -55~-58 dBm, 순간 최저 -63 dBm, 2.4 GHz)는 무선 NIC 에서 읽지만, 연결 시간은 유선 경로 값이라 둘 사이에 인과가 없다. 기본 경로를 같이 기록하지 않았다면 "-57 dBm 인데 0.5 ms 라니 무선도 꽤 좋다"는 틀린 결론을 그대로 글에 썼을 것이다. 무선 실험에 이 노드를 쓰려면 경로부터 바꿔야 한다(연구 설계의 몫이라 아직 손대지 않았다).

**2) 드라이버가 거짓 값을 준다.** solomon 에는 NIC 이 두 개 있다. 쓰는 쪽은 5 GHz USB 동글(-29~-36 dBm)이고, 안 쓰는 내장 칩은 한때 **-6 dBm** 을 보고했다. 1 m 안에 AP 가 없는 한 불가능한 값이다. `/proc/net/wireless` 의 숫자는 드라이버가 채우는 것이라 물리량이라고 믿으면 안 된다. 대시보드는 이 인터페이스를 빼고 그렸다.

**3) 중앙값은 평온한데 최댓값에 1초짜리가 숨어 있다.** 1시간 동안 isagal 의 TCP 연결 시간 중앙값은 0.5 ms 안팎으로 평평했다. 그런데 회차별 **최댓값**을 보면 360회(3 대상 × 120회) 중 **8회가 1.03~1.06초**였다. 0.5 ms 와 1초 사이에는 아무 값도 없다. 이 모양은 TCP 의 첫 SYN 이 한 번 유실돼서 재전송된 것으로 보는 게 자연스럽다. RFC 6298 은 초기 재전송 타이머(RTO)를 **1초**로 두라고 권고한다([RFC 6298 §2.1](https://www.rfc-editor.org/rfc/rfc6298#section-2), "SHOULD set RTO <- 1 second"). 게이트웨이 ping 도 같은 1시간 동안 2회 유실이 있었다. 다만 이건 "SYN 재전송과 모양이 일치한다"는 추정이다. 패킷 캡처로 확인하지는 않았다. louise(1.3~1.6 ms, 최대 6.8 ms)와 solomon(약 2.2 ms, 최대 35 ms)에는 이런 1초 계단이 없었다.

그래서 교훈은 **중앙값 그래프만 보면 이게 안 보인다**는 것이다. 중앙값 그래프와 별도로 최댓값·유실률 패널을 두었다. kubelet 입장에서 1초 지연 한 번은 치명적이지 않다. 하지만 이것이 몰려 오는 순간이 이전 글에서 본 [노드 flap](/2026/09/13/wireless-k8s-node-asymmetric-latency-spof/)의 전조인지는 이 측정기로 앞으로 봐야 할 질문이다.

## 기준선: 빨간 선은 어디서 왔나

그래프의 -67 dBm 선은 Cisco 메시 AP 설계 가이드의 권고다. 이 가이드는 모든 데이터 레이트에서 **RSSI -67 dBm, SNR 25 dB 를 목표로 하라**고 적는다([Cisco Mesh Design Guide 8.7](https://www.cisco.com/c/en/us/td/docs/wireless/controller/technotes/8-7/b_mesh_87/b_mesh_87_chapter_0101.html)). 음성 트래픽 설계 문서도 최소 커버리지를 -65 dBm 으로 잡고, 유실 1% 미만·지연 100 ms 미만을 요구한다([Cisco: Voice over WLAN best practices](https://www.cisco.com/c/en/us/products/collateral/wireless/voice-deploy-optimi-infra-og.html)). -75 dBm 선은 공식 기준이 아니라 내가 임의로 그은 "위험" 표시다. Cisco RRM 의 커버리지 홀 기본값은 -80 dBm 이다([Cisco RRM 설정](https://www.cisco.com/c/en/us/td/docs/wireless/controller/ewc/17-3/olh/Content/topics/t_config_rf_rrm.html)).

주의할 점이 있다. 이 기준들은 **사무실 AP 커버리지 설계용**이다. "RSSI 가 -67 을 넘으면 쿠버네티스 노드가 NotReady 가 된다"는 문턱이 아니다. 무선 k8s 노드용 문턱을 제시한 중립 제3자 자료는 찾지 못했다. 그 문턱을 **이 데이터로 직접 찾는 것**이 과제의 본론이다. 지금 세 노드는 1시간 최저값이 가장 약한 isagal 도 -63 dBm 이라 문턱 근처의 데이터가 아직 없다.

## 측정기는 최소 권한으로

운영 클러스터에 올리는 것이라 권한을 좁게 잡았다.

- 노드 선택은 `nodeAffinity` 로 무선 3대만 한다. hostNetwork 는 노드의 실제 NIC 과 경로를 봐야 해서 켰다.
- `capabilities: drop ALL` 에 `NET_RAW` 하나만 추가했다(ping 용). `privileged` 는 끄고 `readOnlyRootFilesystem` 은 켰다. **호스트 경로 마운트는 없다** — `/proc/net`·`/sys/class/net` 은 hostNetwork 네임스페이스에서 그대로 보인다.
- 서비스 어카운트 토큰은 마운트하지 않는다. 쿠버네티스 API 를 부를 일이 없다.
- 노출은 `:9102/metrics` 하나이고, ServiceMonitor 로 Prometheus 가 긁어 간다([Prometheus Operator: ServiceMonitor](https://prometheus-operator.dev/docs/developer/getting-started/#using-servicemonitors)).

hostNetwork 는 Pod Security Standards 의 Baseline 에서도 금지되는 항목이다([Kubernetes: Pod Security Standards](https://kubernetes.io/docs/concepts/security/pod-security-standards/)). 그러니 이건 "안전한 파드"가 아니라 "필요한 예외 하나만 열고 나머지를 닫은 파드"다. 전체가 YAML 파일 하나라서 지우면 GitOps 가 깨끗이 걷어 간다.

## 과제로 줄 때의 형태

친구에게 넘길 문장은 이렇게 정리했다.

> 무선 노드 3대의 RSSI·연결 시간·Ready 상태가 30초 간격으로 쌓이고 있다. 거리나 장애물을 바꿔 가며 **RSSI 가 몇 dBm 아래로 내려갈 때 apiserver 연결 최댓값과 유실률이 꺾이고, 그게 NotReady 로 이어지는지** 찾아라. 단, 기본 경로가 무선이 아닌 노드는 제외하고, 드라이버가 주는 값이 물리적으로 말이 되는지부터 확인하라.

첫 1시간이 이미 뒤쪽 두 조건을 가르쳐 줬다.

## 한계

- 데이터가 **1시간**뿐이다. 낮·밤, 전자레인지, 이웃 AP 같은 변동은 아직 안 들어 있다.
- 세 노드 모두 신호가 강한 구간(-29~-63 dBm)에만 있다. 문턱은 **아직 관측되지 않았다.**
- 1초 스파이크를 SYN 재전송으로 본 것은 RFC 값과 모양이 맞는다는 추정이다. 패킷 캡처 검증은 안 했다.
- isagal 은 기본 경로가 유선이라 이 노드의 연결 시간은 무선 실험 데이터로 쓸 수 없다.

---

*이 글과 측정기(exporter·DaemonSet·대시보드)는 Anthropic 의 Claude 와 함께 작성·구축했다. 수치는 모두 본인 클러스터 실측이다.*

## References

1. Kubernetes Documentation, "Leases — Node heartbeats". <https://kubernetes.io/docs/concepts/architecture/leases/#node-heartbeats>
2. Kubernetes Documentation, "Pod Security Standards". <https://kubernetes.io/docs/concepts/security/pod-security-standards/>
3. Linux Wireless (kernel.org), "About Wireless-Extensions". <https://wireless.docs.kernel.org/en/latest/en/developers/documentation/wireless-extensions.html>
4. V. Paxson, M. Allman, J. Chu, M. Sargent, "Computing TCP's Retransmission Timer", RFC 6298, IETF, 2011. <https://www.rfc-editor.org/rfc/rfc6298>
5. Cisco, "Wireless Mesh Access Points, Design and Deployment Guide, Release 8.7" (RSSI -67 dBm·SNR 25 dB 목표). <https://www.cisco.com/c/en/us/td/docs/wireless/controller/technotes/8-7/b_mesh_87/b_mesh_87_chapter_0101.html>
6. Cisco, "Voice over Wireless LAN: Deployment and Optimization Best Practices" (-65 dBm, 유실 <1%, 지연 <100 ms). <https://www.cisco.com/c/en/us/products/collateral/wireless/voice-deploy-optimi-infra-og.html>
7. Cisco, "Radio Resource Management" 설정 (커버리지 홀 기본 -80 dBm). <https://www.cisco.com/c/en/us/td/docs/wireless/controller/ewc/17-3/olh/Content/topics/t_config_rf_rrm.html>
8. Prometheus Operator, "Getting started — Using ServiceMonitors". <https://prometheus-operator.dev/docs/developer/getting-started/#using-servicemonitors>
