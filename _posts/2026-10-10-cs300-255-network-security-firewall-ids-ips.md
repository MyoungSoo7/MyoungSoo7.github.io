---
layout: post
title: "[CS300 #255] 네트워크 보안 — 방화벽·IDS·IPS 가 각자 맡는 일"
date: 2026-10-10 22:15:00 +0900
categories: [cs]
tags: [cs300, security, firewall, ids, network-security]
---

컴퓨터공학 300 주제 시리즈의 255번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

방화벽은 정책에 따라 트래픽을 **허용하거나 막고**, IDS 는 트래픽을 지켜보다 수상한 것을 **알리고**, IPS 는 경로 한가운데서 수상한 것을 **즉시 끊는다**. 셋 다 "기본 거부" 와 "구역 나누기" 라는 설계 위에서만 제 역할을 한다.

## 왜 필요한가

애플리케이션 코드를 아무리 잘 짜도 열려 있지 말아야 할 포트가 열려 있으면 소용없다. 인터넷에 노출된 관리용 DB, 테스트용으로 띄운 대시보드, 기본 비밀번호의 원격 접속 서비스. 이런 노출은 자동 스캐너가 인터넷 전체를 꾸준히 훑기 때문에 금방 발견된다.

또 침입은 언젠가 일어난다고 가정해야 한다. 그때 공격자가 한 서버에서 다른 서버로 옆으로 이동(lateral movement)하지 못하게 막고, 이상한 흐름을 일찍 알아채는 것이 네트워크 보안의 역할이다. 앱 보안이 "문을 튼튼하게" 라면 네트워크 보안은 "문의 수를 줄이고 복도에 칸막이와 감시를 두는 것" 이다.

## 핵심 개념

### 방화벽의 종류

NIST SP 800-41 Rev.1 의 분류를 실무 말로 옮기면 다음과 같다.

| 종류 | 판단 근거 | 특징 |
|---|---|---|
| 패킷 필터 | 주소, 포트, 프로토콜 | 빠르지만 응답 패킷을 위해 넓게 열어야 한다 |
| 상태 기반(stateful) | 위 + 연결 상태 추적 | 나간 요청의 응답만 자동 허용. 현재의 기본 |
| 애플리케이션 계층(프록시, WAF) | HTTP 메서드, URL, 본문 | 내용을 이해한다. 비용이 크다 |
| 호스트 기반 | 각 서버의 커널 필터(nftables 등) | 네트워크 방화벽을 지나 내부에서 오는 트래픽도 통제 |

상태 기반 방화벽의 핵심은 **연결 추적(conntrack)** 이다. 안쪽에서 시작한 연결의 응답은 따로 규칙을 쓰지 않아도 통과하고, 바깥에서 먼저 시작한 연결은 규칙에 있어야만 들어온다.

### 규칙 설계 원칙

1. **기본 거부**: 마지막 규칙은 "나머지 전부 drop". 필요한 것만 연다.
2. **나가는 방향(egress)도 통제**: 웹 서버가 인터넷 아무 곳에나 접속할 이유는 없다. 침입한 악성코드는 밖으로 연결을 맺어 명령을 받고 데이터를 내보낸다. 나가는 쪽을 막으면 이 단계가 끊긴다.
3. **구역 나누기(segmentation)**: 인터넷 ↔ DMZ(공개 서버) ↔ 내부 업무망 ↔ 데이터 구역. 구역 사이 흐름만 허용 목록으로 연다.
4. **관리 경로 분리**: SSH·관리 콘솔은 관리 전용 대역이나 VPN·배스천을 거쳐서만.

nftables 로 쓴 서버용 최소 규칙의 모양이다(예시 대역은 문서용 RFC 5737 주소).

```
table inet filter {
  chain input {
    type filter hook input priority 0; policy drop;
    ct state established,related accept
    iif "lo" accept
    tcp dport 443 accept
    ip saddr 198.51.100.0/24 tcp dport 22 accept
  }
}
```

### IDS 와 IPS

NIST SP 800-94 는 둘을 묶어 IDPS 라 부른다.

| 구분 | IDS | IPS |
|---|---|---|
| 위치 | 미러링 포트·탭에서 사본을 본다 | 트래픽 경로 한가운데(inline) |
| 동작 | 경보 | 차단·연결 리셋·정상화 |
| 오탐의 대가 | 담당자의 피로 | **정상 서비스 차단** |
| 장애 시 | 탐지만 멈춤 | 통과시킬지(fail-open) 막을지(fail-closed) 결정 필요 |

탐지 방식은 세 가지다.

- **시그니처 기반**: 알려진 공격 패턴과 대조. 정확하지만 새 공격은 못 잡는다.
- **이상 기반**: 평소 기준선과 다른 행동(갑작스런 트래픽, 새로운 포트)을 잡는다. 새 공격도 잡지만 오탐이 많다.
- **상태 기반 프로토콜 분석**: 프로토콜 정의와 다른 동작을 잡는다.

위치에 따라 네트워크 기반(NIDS)과 호스트 기반(HIDS)으로도 나눈다. 오픈소스 Suricata 는 NIDS·IPS 로 모두 쓸 수 있다.

### 암호화 트래픽의 한계

요즘 트래픽 대부분은 TLS 로 암호화되어 네트워크 IDS 가 내용을 볼 수 없다. 그래서 탐지 지점이 메타데이터(누가 누구와, 얼마나, 언제), TLS 종단 지점(로드 밸런서·인그레스), 호스트(EDR, 감사 로그)로 옮겨 가고 있다. 다음 글들의 SIEM 과 제로 트러스트가 이 변화와 이어진다.

## 직접 해 보기

상태 추적 방화벽과 아주 단순한 이상 탐지를 파이썬으로 흉내 낸다. 주소는 모두 문서용 대역(RFC 5737)이다.

```python
import ipaddress
from collections import defaultdict

# 예시 주소는 문서용 대역(RFC 5737)만 쓴다
WEB = ipaddress.ip_address("192.0.2.10")
RULES = [  # (방향, 출발지 대역, 목적지, 포트, 동작) — 위에서부터 첫 일치
    ("in",  "0.0.0.0/0",        WEB, 443, "accept"),
    ("in",  "198.51.100.0/24",  WEB, 22,  "accept"),   # 관리망에서만 SSH
    ("out", "192.0.2.0/24",     None, 53, "accept"),   # DNS 만 밖으로
]
conntrack = set()          # 상태 추적: 허용된 연결의 반대 방향 응답은 통과

def decide(direction, src, dst, sport, dport):
    if (dst, src, dport, sport) in conntrack:           # 기존 연결의 응답 패킷
        return "accept(established)"
    for d, net, target, port, action in RULES:
        if d == direction and ipaddress.ip_address(src) in ipaddress.ip_network(net) \
           and (target is None or ipaddress.ip_address(dst) == target) and dport == port:
            conntrack.add((src, dst, sport, dport))
            return action
    return "drop(default)"                              # 기본 거부

pkts = [
    ("in",  "203.0.113.7",  "192.0.2.10", 51000, 443),  # 인터넷 -> HTTPS
    ("out", "192.0.2.10",  "203.0.113.7", 443, 51000),  # 그 응답
    ("in",  "203.0.113.7",  "192.0.2.10", 51001, 22),   # 인터넷 -> SSH
    ("out", "192.0.2.10",  "203.0.113.99", 40000, 4444),# 서버가 밖으로 임의 포트(역연결 의심)
]
for p in pkts:
    print(f"{p[0]:<3} {p[1]:>13}:{p[3]:<5} -> {p[2]:>13}:{p[4]:<5} {decide(*p)}")

# 아주 단순한 이상 탐지(IDS 흉내): 짧은 시간에 여러 포트를 두드리면 경보
events = [("203.0.113.50", port) for port in range(20, 40)] + [("203.0.113.7", 443)] * 5
ports_by_src = defaultdict(set)
for src, port in events:
    ports_by_src[src].add(port)
for src, ports in ports_by_src.items():
    if len(ports) >= 10:
        print(f"ALERT 포트 스캔 의심: {src} 가 {len(ports)}개 포트 접근")
```

실행 결과(Python 3.12):

```
in    203.0.113.7:51000 ->    192.0.2.10:443   accept
out    192.0.2.10:443   ->   203.0.113.7:51000 accept(established)
in    203.0.113.7:51001 ->    192.0.2.10:22    drop(default)
out    192.0.2.10:40000 ->  203.0.113.99:4444  drop(default)
ALERT 포트 스캔 의심: 203.0.113.50 가 20개 포트 접근
```

두 번째 줄의 응답 패킷은 나가는 방향 규칙이 없는데도 통과했다. 연결 추적 덕분이다. 네 번째 줄은 서버가 먼저 바깥 임의 포트로 나가려는 시도로, egress 기본 거부에 걸렸다. 침해된 서버가 공격자에게 역연결하는 전형적인 모양이다. 마지막 경보는 "10개 이상 포트" 라는 임계값 하나로 만든 규칙이라 정상 모니터링 도구도 걸릴 수 있다. 이상 기반 탐지의 오탐이 어디서 오는지 보여 준다.

## 현업에서는

- **클라우드 보안 그룹과 쿠버네티스 NetworkPolicy**: 둘 다 상태 기반 방화벽 규칙을 선언형으로 쓴 것이다. 쿠버네티스 공식 문서대로 NetworkPolicy 는 **네트워크 플러그인(CNI)이 지원해야** 실제로 적용된다. 지원하지 않는 CNI 에 정책을 써도 오류 없이 무시되므로, 적용 후 실제로 막히는지 시험해야 한다. 네임스페이스마다 "기본 전부 거부" 정책을 먼저 두고 필요한 흐름만 여는 방식이 흔히 쓰인다(공식 문서에 기본 거부 정책 예시가 있다).
- **egress 가 빠진 정책**: ingress 만 쓰고 egress 를 비워 두는 경우가 많다. 파드가 털렸을 때 클러스터 밖으로 무엇이든 보낼 수 있다. DNS 와 필요한 외부 API 만 허용하는 egress 정책을 함께 둔다.
- **IPS 는 탐지 모드로 시작**: 새 시그니처 세트는 먼저 IDS(경보만) 모드로 몇 주 돌려 오탐을 정리한 뒤 차단으로 바꾼다.
- **노출 점검**: 홈랩이든 회사든 공유기나 방화벽의 포트 포워딩 목록을 정기적으로 확인한다. "잠깐 테스트용" 으로 연 포트가 가장 오래 남는다.

## 확인 문제

1. 상태 기반 방화벽이 단순 패킷 필터보다 나은 점은?
2. 나가는 방향(egress) 필터링이 침해 이후 단계에서 어떤 역할을 하는가?
3. IDS 와 IPS 의 오탐 비용이 다른 이유는?
4. 시그니처 기반과 이상 기반 탐지의 장단점을 비교하라.
5. 쿠버네티스에 NetworkPolicy 를 적용했는데 아무것도 막히지 않는다. 가장 먼저 의심할 것은?

### 풀이

1. 연결 상태를 추적해 내부에서 시작한 연결의 응답만 자동 허용한다. 응답용으로 넓은 포트 범위를 열 필요가 없다.
2. 악성코드의 명령 서버 접속과 데이터 반출을 막거나 드러나게 한다.
3. IDS 오탐은 경보 하나로 끝나지만 IPS 는 경로 위에서 실제로 정상 트래픽을 끊어 장애를 만든다.
4. 시그니처: 정확도가 높고 설명이 쉬우나 새 공격을 못 잡는다. 이상 기반: 미지의 공격도 잡을 수 있으나 기준선 설정이 어렵고 오탐이 많다.
5. 사용 중인 CNI 가 NetworkPolicy 를 지원하는지.

## 더 읽을거리 (References)

- NIST, [SP 800-41 Rev. 1: Guidelines on Firewalls and Firewall Policy](https://csrc.nist.gov/pubs/sp/800/41/r1/final)
- NIST, [SP 800-94: Guide to Intrusion Detection and Prevention Systems (IDPS)](https://csrc.nist.gov/pubs/sp/800/94/final)
- Kubernetes, [Network Policies](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- Suricata, [Suricata User Guide](https://docs.suricata.io/en/latest/)
