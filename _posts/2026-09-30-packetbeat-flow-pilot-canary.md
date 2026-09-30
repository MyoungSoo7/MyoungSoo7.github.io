---
layout: post
title: "Packetbeat 흐름 수집 3일 파일럿 — 초록불 말고 카나리로 판정하기"
date: 2026-09-30 22:57:00 +0900
categories: [kubernetes, security, observability]
tags: [packetbeat, elastic, eck, af_packet, falco, canary, k3s]
---

홈랩 K3s 클러스터의 워커 노드 1대에 Packetbeat 를 붙여 3일 동안 돌렸다. 목적은 하나다. **이 노드가 외부의 어느 주소·포트와 언제 얼마나 주고받았는지**를 연결 단위로 남기는 것이다. 사고가 났을 때 "정말 밖으로 나갔나"에 답할 증거를 만들려는 것이다.

3일째 되는 날 판정해야 했다. 그런데 자원 사용량과 문서 수만 보면 전부 초록불이었고, 그 초록불로는 판정할 수 없었다. 이 글은 그 이유와, 대신 넣은 **카나리(정답을 아는 가짜 트래픽)** 가 무엇을 증명했는지에 대한 기록이다.

## 1. 무엇을 수집하나 — flow, 내용이 아니라 "누가 누구와 얼마나"

Packetbeat 는 원래 HTTP·DNS·MySQL 같은 프로토콜을 해석하는 도구다. 이번 파일럿에서는 **프로토콜 해석을 전부 끄고 flow 만** 켰다.

Elastic 문서의 정의는 다음과 같다.

- flow 는 "같은 기간에 보내진, 출발지·목적지 주소와 프로토콜 같은 공통 속성을 가진 패킷의 묶음"이다.
- Packetbeat 는 흐름마다 패킷 수와 바이트 수를 보고한다.
- 해석은 **전송 계층(TCP/UDP)까지만** 한다.

([Elastic, Configure flows](https://www.elastic.co/guide/en/beats/packetbeat/current/configuration-flows.html))

따라서 페이로드는 저장되지 않는다. 남는 건 5-튜플과 시각, 양이다.

설정의 핵심은 세 가지다.

| 항목 | 값 | 근거 |
|---|---|---|
| 캡처 방식 | `af_packet` | 메모리 매핑 링버퍼. libpcap 보다 빠르고 커널 모듈이 필요 없다(리눅스 전용) — [Elastic, traffic capturing options](https://www.elastic.co/guide/en/beats/packetbeat/current/configuration-interfaces.html) |
| `flows.timeout` | 30s (기본값) | 이 시간 동안 패킷이 없으면 흐름을 끝내고 보고한다 |
| `flows.period` | 5m (기본 10s) | 주기 보고 간격. `-1` 로 끌 수도 있다 — 같은 문서 |

`period` 를 끄지 않고 5분으로 늘린 이유는 따로 있다. 끄면 흐름이 **끝나야만** 보고된다. 그러면 역연결 셸처럼 몇 시간씩 붙어 있는 연결이 끝날 때까지 안 보인다. 정작 제일 보고 싶은 연결이 제일 늦게 보이게 되는 것이다.

BPF 필터로 **사내 LAN 끼리의 트래픽, 멀티캐스트·브로드캐스트, IPv6 링크로컬은 뺐다.** 남는 건 "노드 ↔ 외부"뿐이다. (필터에 들어간 대역 값은 이 글에 적지 않는다.)

배포는 ECK(Elastic Cloud on Kubernetes)의 `Beat` 리소스로 했다. 별도 ArgoCD 앱으로 떼어 `prune: true` 를 주었다. 파일럿을 끌 때 CR 이 고아로 남지 않게 하려는 것이다. ([Elastic, ECK Beats](https://www.elastic.co/guide/en/cloud-on-k8s/current/k8s-beat.html))

### Falco 와 부딪히는 지점

`af_packet` 캡처는 곧 `socket(AF_PACKET, ...)` 이다. 리눅스 매뉴얼에 따르면 packet 소켓은 "장치 드라이버(OSI 2계층) 수준에서 원시 패킷을 주고받는" 소켓이다. 그래서 `CAP_NET_RAW` 가 필요하다. ([packet(7)](https://man7.org/linux/man-pages/man7/packet.7.html))

Falco 기본 룰 **`Packet socket created in container`** 가 정확히 이것을 잡는다. 이 룰은 maturity_stable 이고 기본으로 켜져 있다. ARP 스푸핑과 CVE-2020-14386(af_packet 권한 상승) 탐지가 목적이다. ([Falcosecurity Rules](https://falcosecurity.github.io/rules/), [falco PR #1402](https://github.com/falcosecurity/falco/pull/1402))

즉 Packetbeat 를 켜는 순간 보안 도구끼리 서로를 공격자로 본다.

예외는 **이미지 태그와 파드 이름 접두사를 AND 로 묶어 최대한 좁게** 걸었다. 그리고 이 규칙을 같이 적어 두었다: **파일럿을 끄면 이 예외도 반드시 같이 지운다.** Packetbeat 가 사라진 뒤 예외만 남으면 그 이름을 흉내 낸 무언가가 탐지를 통과하는 구멍이 된다.

## 2. 3일 수치 — 전부 초록불

| 지표 | 결과 |
|---|---|
| 파드 메모리 | 약 50Mi (최대 55Mi) |
| 파드 CPU | 약 5m |
| 노드 MemAvailable 최저(5분) | 55.7% (배포 전 기준선 55.2%) |
| 재시작 | 0 |
| 일 문서 수 | 16,630 / 17,160 / 16,845 |
| 일 저장 용량 | 10.5 / 10.0 / 9.3 MB |
| 기존 k8s 로그 대비 | 하루 약 600MB 대비 약 1.7% |
| 전송 실패 | 3일간 ES `_bulk` 타임아웃 1회(이벤트 7건) |

일 용량은 하루 1개씩 롤오버되는 백킹 인덱스의 `pri.store.size` 로 셌다(레플리카 0). 7일 보존이면 이 노드 하나에 약 70MB 가 쌓인다.

중단 기준 세 가지(MemAvailable 15% 미만 5분 지속, OOMKill, 일 문서 수가 기존 로그 일 합계 초과)에는 하나도 걸리지 않았다.

### 그런데 이 표로는 판정할 수 없다

이 표가 증명하는 건 **"Packetbeat 가 멀쩡히 돌면서 무언가를 적고 있다"** 까지다. **"보고 싶은 연결을 실제로 잡는다"** 는 증명하지 못한다.

BPF 필터가 잘못돼 외부 연결은 전부 빠지고 잡음만 하루 1.7만 건 쌓이고 있어도, 위 표는 한 칸도 바뀌지 않는다. 검사 대상이 0개여도 초록불이 켜지는 **공허한 통과(vacuous pass)** 와 같은 구조다.

측정 쪽에서도 함정이 하나 나왔다.

- 처음 만든 점검 스크립트는 ES 대신 **파드 로그의 `acked` 카운터**를 합산했다. 읽기 전용 계정에 `packetbeat-*` 권한이 없어서였다.
- 2일째 이 값이 958건으로 나왔다. 컨테이너 로그가 로테이션되어 **최근 2시간치만 남아 있었기** 때문이다(재시작 0).
- 실제 값은 약 1.7만 건이었다.
- 파드 로그를 세는 방식은 로그 첫 줄의 타임스탬프로 **커버 구간부터** 확인해야 한다.

## 3. 카나리 — 정답을 아는 입력을 하나 넣는다

그래서 판정 조건에 카나리를 넣었다. 탄광 카나리아처럼, **결과를 미리 아는 트래픽을 일부러 흘리고 그것이 끝까지 도착하는지** 보는 것이다.

### 방향 선택

처음 계획은 "외부 → 노드"였다. 그런데 공유기 뒤 홈랩 노드는 밖에서 바로 닿지 않는다. 그렇다고 같은 LAN 의 PC 에서 보내면, 필터가 일부러 빼는 트래픽이라 **안 잡히는 게 정상**이다. 그러면 시험이 되지 않는다.

그래서 방향을 뒤집었다. **노드에서 외부 주소로** UDP 1개를 내보낸다. 이것도 "노드 ↔ 외부"라서 똑같이 잡혀야 한다.

목적지는 RFC 5737 의 문서용 예약 대역 **TEST-NET-3(203.0.113.0/24)** 에서 골랐다. 이 대역은 "공용 인터넷에 나타나면 안 되고", 어느 누구에게도 할당되지 않는다. ([RFC 5737 §3·§4·§7](https://www.rfc-editor.org/rfc/rfc5737)) 기본 경로를 따라 NIC 를 떠나기는 하지만 **받는 쪽이 존재하지 않는다.** 제3자를 건드리지 않는 카나리다.

```bash
# 노드에서 1회. 페이로드 18바이트, 목적지 포트 47123
python3 -c 'import socket; s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.sendto(b"pb-canary-20260930", ("203.0.113.10", 47123))'
```

### 결과

약 2분 뒤 ES 관리자 계정으로 `destination.port: 47123` 을 조회했다.

```json
{"@timestamp":"2026-09-30T11:21:00.004Z","flow":{"final":false,"id":"EQIA…qbk"},
 "network":{"transport":"udp","packets":1,"bytes":60},"destination":{"port":47123}}
{"@timestamp":"2026-09-30T11:21:30.004Z","flow":{"final":true, "id":"EQIA…qbk"},
 "network":{"transport":"udp","packets":1,"bytes":60},"destination":{"port":47123}}
```

**60바이트**는 보낸 패킷과 정확히 맞는다.

| 층 | 바이트 |
|---|---|
| 이더넷 헤더 | 14 |
| IPv4 헤더 | 20 |
| UDP 헤더 | 8 |
| 페이로드 `pb-canary-20260930` | 18 |
| **합계** | **60** |

다른 트래픽이 우연히 같은 포트로 잡힌 게 아니다. **내가 넣은 바로 그 패킷**이다. 캡처 → BPF 필터 → flow 집계 → ES 전송 → 저장까지 전 구간이 한 번에 증명됐다.

## 4. 카나리가 덤으로 알려준 것 — 흐름 1개 = 문서 2개

문서가 **2건** 왔다. `flow.id` 는 같고 `flow.final` 만 다르다.

Elastic 필드 문서에 따르면 `final` 이 false 면 **"흐름의 중간 상태만 보고한 이벤트"**, true 면 **마지막 이벤트**다. ([Flow Event fields](https://www.elastic.co/guide/en/beats/packetbeat/current/exported-fields-flows_event.html))

- 첫 문서는 주기 보고 시점이 마침 흐름 수명 안에 걸려서 나간 중간 보고다.
- 둘째 문서는 30초 타임아웃 뒤의 최종 보고다.

로컬에서 미리 재 볼 때는 단발 UDP 가 약 1분 뒤 final 1건으로만 나왔다. 그래서 "1흐름 = 1문서"라고 생각하고 있었다. 주기 보고 시점과 겹치면 그 가정이 깨진다. 오래 사는 연결일수록 중간 보고는 더 많이 쌓인다.

운영상 결론은 이렇다.

- **"연결 몇 건"을 셀 때는 문서 수가 아니라 `flow.id` 기준 고유 개수**(`cardinality`)를 쓴다.
- 바이트 합계를 낼 때도 `final: true` 만 쓰거나 `flow.id` 별 최댓값을 쓴다. 기본 설정(`enable_delta_flow_reports: false`)에서는 중간 보고의 bytes 가 **누적값**이라, 그냥 더하면 이중 계상된다. ([Configure flows](https://www.elastic.co/guide/en/beats/packetbeat/current/configuration-flows.html))
- 반대로 **탐지 목적이면 `final: false` 를 버리면 안 된다.** 아직 끝나지 않은 연결은 중간 보고로만 보인다.

카나리가 없었다면 이 이중 계상은 확대 뒤 대시보드 숫자가 이상해질 때에야 알았을 것이다.

## 5. 판정과 아직 안 풀린 것

**판정: 계속. 확대 후보 조건 충족.**

- 중단 기준 해당 없음
- 카나리 성공
- 문서 수·CPU·메모리 안정
- 일 용량 확보

확대는 아직 결정하지 않았다. 남은 문제는 이렇다.

1. **노드별 트래픽 비율을 재지 않았다.** "10MB × 노드 수"는 틀린 계산이다. 외부 통신량은 노드마다 크게 다르다. 확대 추정은 노드별 pps 비율을 곱해서 해야 한다.
2. **무선 NIC 에서 캡처 중이다.** 이 노드는 무선으로 붙어 있다. 무선 링크가 흔들릴 때 캡처 누락이 생기는지는 이번 3일로 판단할 수 없다. 드롭·에러 카운터는 0이었지만, 누락은 카나리처럼 **정답을 아는 입력**을 반복해서 넣어야 잴 수 있다.
3. **조회 권한.** 자동 점검 계정은 여전히 `packetbeat-*` 를 읽지 못한다. 이번 카나리 확인은 사람이 승인해서 관리자 계정으로 1회 했다. 확대한다면 읽기 전용 역할에 read 를 추가하는 게 먼저다.
4. **흐름만으로는 "무엇을" 보냈는지 모른다.** 이상 통신의 성격까지 판단하려면 Suricata 같은 IDS 가 다음 단계다. 이번 파일럿의 실패 조건(카나리 미검출)은 곧바로 그쪽을 재검토하는 조건이기도 했다.

한 줄로 줄이면: **모니터링 도구의 헬스체크는 "돌고 있다"를 증명하고, 카나리는 "보고 있다"를 증명한다.** 둘은 다른 질문이다.

## References

1. Elastic. *Configure flows to monitor network traffic* — Packetbeat Reference. <https://www.elastic.co/guide/en/beats/packetbeat/current/configuration-flows.html>
2. Elastic. *Configure traffic capturing options* — Packetbeat Reference. <https://www.elastic.co/guide/en/beats/packetbeat/current/configuration-interfaces.html>
3. Elastic. *Flow Event fields* — Packetbeat Reference. <https://www.elastic.co/guide/en/beats/packetbeat/current/exported-fields-flows_event.html>
4. Elastic. *Beats* — Elastic Cloud on Kubernetes. <https://www.elastic.co/guide/en/cloud-on-k8s/current/k8s-beat.html>
5. Linux man-pages. *packet(7) — packet interface on device level*. <https://man7.org/linux/man-pages/man7/packet.7.html>
6. Falcosecurity. *Falco Rules overview* (Packet socket created in container). <https://falcosecurity.github.io/rules/>
7. H. Suezawa. *enable "Packet socket created in container" by default*, falcosecurity/falco PR #1402. <https://github.com/falcosecurity/falco/pull/1402>
8. J. Arkko, M. Cotton, L. Vegoda. *RFC 5737: IPv4 Address Blocks Reserved for Documentation*, IETF, 2010. <https://www.rfc-editor.org/rfc/rfc5737>

*수치는 모두 이 클러스터에서 2026-09-27 ~ 09-30 에 직접 측정한 값이다(Packetbeat 8.16.1, ECK 2.16.1). 다른 환경의 성능을 대표하지 않는다.*
