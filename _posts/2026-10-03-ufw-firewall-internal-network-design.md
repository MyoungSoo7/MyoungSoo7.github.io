---
layout: post
title: "UFW 방화벽과 내부망 — '내부 대역만 허용'이 지켜주는 것과 못 지켜주는 것"
date: 2026-10-03 17:00:00 +0900
categories: [Security, Infra]
tags: [ufw, firewall, iptables, docker, k3s, kubernetes, networkpolicy, homelab, 내부망]
---

홈랩이나 사내 서버에서 방화벽을 처음 세팅할 때 가장 흔한 방침은 이렇다. **"외부는 막고, 내부망은 믿는다."** Ubuntu 라면 그 도구는 거의 항상 UFW 다.

이 글은 UFW 로 그 방침을 제대로 구현하는 법을 정리한다. 그리고 더 중요한 이야기, **그 방침이 생각보다 많은 경로를 놓친다**는 점을 다룬다. Docker, Kubernetes, 터널이 끼면 "내부망만 허용" 규칙은 생각만큼 일하지 않는다.

> 이 글의 IP 주소는 모두 예시다. 내부망 예시는 `10.0.10.0/24`([RFC 1918](https://www.rfc-editor.org/rfc/rfc1918) 사설 대역 중 임의로 고른 값), 외부 주소 예시는 [RFC 5737](https://www.rfc-editor.org/rfc/rfc5737) 문서용 대역(`203.0.113.0/24`)을 썼다.

이 블로그의 관련 실전기:
- [K3s flannel cross-node 가 안 될 때 — ufw 8472/UDP 함정](/2026/05/11/k3s-flannel-ufw-8472-cross-node-함정/)
- [K3s + ufw — 재부팅 후 overlay 가 죽는 함정](/2026/05/26/k3s-ufw-overlay-block-reboot-trap/)
- [유령 iptables LOG 규칙 추적기](/2026/07/21/lemuel-disk-ufw-iptables-log-flood/)
- [파드 하나가 뚫리면 어디까지 닿나](/2026/09/24/flat-cluster-network-networkpolicy/)

이 글은 그 조각들을 하나의 그림으로 묶는 개론이다.

---

## 1. UFW 가 무엇이고 기본값이 무엇인가

[Ubuntu Server 문서](https://ubuntu.com/server/docs/how-to/security/firewalls/)는 UFW 를 "`iptables` 방화벽 설정을 쉽게 하려고 개발된" 도구라고 소개한다. 즉 UFW 는 방화벽 그 자체가 아니라 **커널 패킷 필터 규칙을 대신 써 주는 프런트엔드**다. 같은 문서에 따르면 UFW 는 처음에 **꺼져 있다**.

[ufw(8) 매뉴얼](https://manpages.ubuntu.com/manpages/noble/en/man8/ufw.8.html)에 적힌 설치 직후 기본 정책은 다음과 같다.

| 방향 | 기본 정책 |
|---|---|
| incoming (들어오는 연결) | deny |
| outgoing (나가는 연결) | allow |
| routed / forward (거쳐 가는 패킷) | deny |

IPv6 규칙도 기본으로 함께 적용된다. 끄려면 `/etc/default/ufw` 에서 `IPV6` 를 `no` 로 바꾼다. **IPv4 만 막고 IPv6 를 잊는 실수**를 UFW 기본값이 막아 준다.

---

## 2. "내부망만 허용"을 UFW 로 쓰는 법

### 기본 골격

```bash
# 1) 기본 정책: 들어오는 건 막고, 나가는 건 허용
sudo ufw default deny incoming
sudo ufw default allow outgoing

# 2) 켜기 전에 SSH 부터 열어 둔다 (원격 접속 중이라면 필수)
sudo ufw allow from 10.0.10.0/24 to any port 22 proto tcp

# 3) 켜기
sudo ufw enable
sudo ufw status numbered
```

**순서가 중요하다.** 원격으로 SSH 접속한 상태에서 SSH 허용 규칙 없이 `enable` 하면 그대로 끊긴다.

### 서비스별로 "내부에서만"

```bash
# DB 는 내부망에서만
sudo ufw allow from 10.0.10.0/24 to any port 5432 proto tcp

# 웹은 전체 공개
sudo ufw allow 443/tcp
```

`from <대역> to any port <포트> proto <프로토콜>` 형식은 매뉴얼의 규칙 문법(`[proto PROTOCOL] [from ADDRESS [port PORT]] [to ADDRESS [port PORT]]`)을 그대로 쓴 것이다.

### SSH 무차별 대입 완화: `limit`

```bash
sudo ufw limit ssh/tcp
```

매뉴얼에 따르면 `limit` 은 "한 IP 가 30 초 안에 6 회 이상 연결을 시도하면" 연결을 거부한다. 공개 SSH 를 꼭 열어야 한다면 `allow` 대신 `limit` 을 쓴다. 다만 이건 속도 제한일 뿐이다. 키 인증과 비밀번호 로그인 끄기를 대신하지 못한다.

### 규칙은 위에서부터, 처음 맞는 것이 이긴다

매뉴얼 NOTES 절: **"Rule ordering is important and the first match wins."**

```bash
sudo ufw status numbered            # 번호 확인
sudo ufw insert 1 deny from 203.0.113.50   # 특정 IP 차단을 맨 위에
sudo ufw delete 3                   # 번호로 삭제
```

넓은 `allow` 아래에 특정 IP `deny` 를 추가하면 **그 deny 는 영원히 매치되지 않는다.** 차단 규칙은 `insert` 로 위에 넣는다.

### 거쳐 가는 트래픽은 `route`

라우터나 게이트웨이 역할을 하는 서버라면, 자신을 목적지로 하는 패킷과 **자신을 거쳐 가는 패킷**은 다른 체인을 탄다. 후자는 `ufw route` 로 쓴다(매뉴얼 예: `ufw route allow in on eth0 out on eth1 to … port 80 proto tcp`). 이때 IP 포워딩 자체도 켜야 한다(`/etc/ufw/sysctl.conf`). "규칙을 넣었는데 안 된다"의 상당수가 `allow` 와 `route allow` 를 혼동한 경우다.

---

## 3. 첫 번째 구멍: Docker 는 UFW 를 지나가지 않는다

Docker 공식 문서의 [Packet filtering and firewalls](https://docs.docker.com/engine/network/packet-filtering-firewalls/)는 이렇게 경고한다.

> "Docker and ufw use firewall rules in ways that make them incompatible with each other."

이유는 패킷 경로다. 컨테이너 포트를 publish(`-p 8080:80`)하면 Docker 가 NAT 규칙을 직접 넣는다. 그러면 그 트래픽은 "ufw 방화벽 설정을 거치기 전에 우회"되고, 문서 표현대로 **"사실상 방화벽 설정을 무시"**하게 된다. `ufw status` 에는 8080 이 없는데 외부에서 8080 이 열려 있는 상황이 이렇게 생긴다.

대응은 공식 문서 기준으로 두 가지다.

1. **외부에 열 필요가 없으면 localhost 에만 publish 한다.** [Port publishing](https://docs.docker.com/engine/network/port-publishing/) 문서는 "컨테이너 포트 publish 는 기본적으로 안전하지 않다"고 적는다. `-p 127.0.0.1:8080:80` 처럼 주소를 붙이면 호스트만 접근할 수 있다. 단, 같은 문서에 따르면 28.0.0 이전 버전에서는 같은 L2 세그먼트의 다른 호스트가 localhost 로 publish 한 포트에 닿을 수 있었다. 버전도 확인하자.
2. **필터링이 필요하면 `DOCKER-USER` 체인에 넣는다.** [Docker 문서](https://docs.docker.com/engine/network/firewall-iptables/)에 따르면 `FORWARD` 체인에 추가한 규칙은 Docker 규칙 *뒤에* 처리되므로 효과가 없다. 컨테이너행 트래픽을 걸러야 한다면 `DOCKER-USER` 체인을 써야 한다.

**교훈: Docker 가 도는 호스트에서는 `ufw status` 가 실제 노출 상태를 말해 주지 않는다.** 노출 여부는 바깥에서 직접 포트를 찔러 봐야 안다.

---

## 4. 두 번째 구멍: Kubernetes(K3s) 는 UFW 와 사이가 나쁘다

[K3s 설치 요구사항 문서](https://docs.k3s.io/installation/requirements)는 아예 이렇게 권한다.

> "It is recommended to turn off ufw (uncomplicated firewall)"

그래도 UFW 를 켜 둘 거라면 최소한 다음 규칙이 필요하다고 명시한다(K3s 기본 파드·서비스 대역 기준).

```bash
ufw allow 6443/tcp                 # apiserver
ufw allow from 10.42.0.0/16 to any # pods
ufw allow from 10.43.0.0/16 to any # services
```

노드끼리는 역할에 따라 추가 포트가 필요하다(같은 문서의 인바운드 규칙 표).

| 포트 | 용도 |
|---|---|
| TCP 6443 | K3s supervisor·Kubernetes API |
| TCP 2379–2380 | 내장 etcd HA(서버 간) |
| UDP 8472 | Flannel VXLAN |
| TCP 10250 | kubelet |
| UDP 51820 / 51821 | Flannel WireGuard(IPv4 / IPv6) |

같은 문서는 **"VXLAN 포트는 외부에 노출하면 안 된다"**고도 적는다. 그래서 위 포트들은 `from 10.0.10.0/24` 처럼 **노드가 있는 내부 대역에만** 연다.

이 블로그의 [8472 함정](/2026/05/11/k3s-flannel-ufw-8472-cross-node-함정/)과 [재부팅 함정](/2026/05/26/k3s-ufw-overlay-block-reboot-trap/)이 정확히 이 표에서 한 줄을 빠뜨려서 생긴 장애였다. 파드는 뜨는데 노드 간 통신만 조용히 죽는 식으로 나타난다.

---

## 5. 세 번째 구멍: "내부망"은 생각보다 넓다

여기까지 하면 "외부는 막고 내부는 연다"가 완성된 것 같다. 하지만 **내부망 허용 규칙이 믿는 대상**을 다시 보자.

### (1) 내부망 = 그 대역의 모든 기기

`allow from 10.0.10.0/24` 는 그 대역의 **모든 기기**를 믿는다는 뜻이다. 서버 6 대뿐 아니라 같은 공유기에 붙은 노트북, 휴대폰, 스마트 TV, IoT 기기까지 포함된다. 그중 하나가 감염되면 그 기기는 "내부"다. 무선 비밀번호를 아는 손님도, 남는 랜 포트에 꽂은 누군가도 마찬가지다([유선 포트 보안 글](/2026/09/24/wired-network-security-from-the-switch-port/) 참고).

→ 가능하면 **서버만 있는 별도 대역**(VLAN 또는 별도 공유기)을 두고, 그 대역만 허용한다. 그게 어렵다면 최소한 DB·etcd·kubelet 같은 포트는 **서버 IP 하나하나**로 좁힌다.

### (2) 클러스터 안은 UFW 가 보지 않는 또 하나의 내부망

Kubernetes 파드끼리의 통신은 노드 방화벽이 아니라 오버레이 네트워크 위에서 일어난다. K3s 문서대로 `10.42.0.0/16`(파드 대역)을 통째로 허용하면, **어떤 파드든 다른 모든 파드에 닿는다.** 웹 파드 하나가 뚫리면 같은 클러스터의 DB 파드까지 닿는다는 뜻이다.

이 층은 UFW 가 아니라 **Kubernetes NetworkPolicy** 의 몫이다. [공식 문서](https://kubernetes.io/docs/concepts/services-networking/network-policies/)에 따르면 NetworkPolicy 는 파드 트래픽을 IP·포트 수준(L3/L4)에서 제어한다. 단 이를 구현하는 네트워크 플러그인이 있어야 하고, 없으면 정책 리소스를 만들어도 효과가 없다. 실제로 세어 보니 네임스페이스 대부분에 정책이 없었다는 이야기가 [이 글](/2026/09/24/flat-cluster-network-networkpolicy/)이다.

### (3) 터널은 인바운드 방화벽을 아예 지나지 않는다

Cloudflare Tunnel 같은 터널은 서버 안의 에이전트(`cloudflared`)가 **바깥으로 연결을 먼저 맺는** 구조다([Cloudflare Tunnel 문서](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/)). 인터넷 사용자의 요청은 그 아웃바운드 연결을 타고 들어온다. 그래서 **UFW 의 `deny incoming` 은 터널로 공개한 서비스를 전혀 막지 못한다.** UFW 기본 정책이 outgoing 을 허용하기 때문이다.

터널로 내부 서비스를 공개하는 순간 그 서비스는 "내부망 전용"이 아니라 **인터넷 공개 서비스**가 된다. 그러니 앱 자체의 인증이나 터널 앞단의 접근 제어(예: Cloudflare Access)가 있어야 한다. "방화벽이 있으니 관리 화면은 인증 없이 둬도 된다"는 판단이 가장 위험한 지점이 여기다.

---

## 6. 정리: 층마다 다른 도구

| 층 | 막는 대상 | 도구 |
|---|---|---|
| 호스트 인바운드 | 인터넷 → 서버 포트 | UFW `default deny incoming` + 필요한 포트만 |
| 내부망 세분화 | 같은 대역의 다른 기기 → 서버 | 서버 전용 대역(VLAN), IP 단위 허용 |
| 컨테이너 publish | 외부 → Docker 컨테이너 | `127.0.0.1:` 바인드, `DOCKER-USER` 체인 |
| 클러스터 내부 | 파드 → 파드 | Kubernetes NetworkPolicy |
| 터널·리버스 프록시 | 인터넷 → 터널로 공개한 앱 | 앱 인증, 앞단 접근 제어(Access 등) |

UFW 는 **첫 번째 줄을 아주 잘 한다.** 나머지 네 줄은 UFW 가 보지 못하는 경로다.

---

## 체크리스트

- [ ] `ufw default deny incoming`, SSH 허용 규칙을 넣은 **뒤에** `enable`
- [ ] 공개 SSH 라면 `limit` + 키 인증 + 비밀번호 로그인 끔
- [ ] 차단 규칙은 `insert` 로 위에 넣고, `status numbered` 로 순서 확인
- [ ] IPv6 규칙도 적용되는지 확인(`/etc/default/ufw`)
- [ ] Docker 호스트는 `ufw status` 를 믿지 말고 **외부에서 포트 스캔**으로 확인
- [ ] K3s 라면 문서의 포트 표대로, 노드 대역에만 열기(8472 를 외부에 열지 않기)
- [ ] "내부망 전체 허용" 대신 서버 IP 단위로 좁히기
- [ ] 파드 대역 통째 허용을 쓴다면 NetworkPolicy 로 네임스페이스마다 문 달기
- [ ] 터널로 공개한 서비스는 **방화벽과 무관하게** 인증 필수

---

## References

1. Ubuntu, *ufw(8) manual page* (noble). <https://manpages.ubuntu.com/manpages/noble/en/man8/ufw.8.html>
2. Ubuntu Server documentation, *Firewalls*. <https://ubuntu.com/server/docs/how-to/security/firewalls/>
3. Docker Docs, *Packet filtering and firewalls*. <https://docs.docker.com/engine/network/packet-filtering-firewalls/>
4. Docker Docs, *Docker with iptables* (DOCKER-USER). <https://docs.docker.com/engine/network/firewall-iptables/>
5. Docker Docs, *Port publishing and mapping*. <https://docs.docker.com/engine/network/port-publishing/>
6. K3s Docs, *Requirements* (Inbound Rules, ufw). <https://docs.k3s.io/installation/requirements>
7. Kubernetes Docs, *Network Policies*. <https://kubernetes.io/docs/concepts/services-networking/network-policies/>
8. Cloudflare Docs, *Cloudflare Tunnel*. <https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/>
9. IETF, *RFC 1918 — Address Allocation for Private Internets*. <https://www.rfc-editor.org/rfc/rfc1918>
10. IETF, *RFC 5737 — IPv4 Address Blocks Reserved for Documentation*. <https://www.rfc-editor.org/rfc/rfc5737>
