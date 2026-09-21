---
layout: post
title: "AI 에이전트에게 운영 작업을 맡길 때 — 되돌릴 길을 먼저 깐다"
date: 2026-09-22 00:19:25 +0900
categories: [AI, Infrastructure]
tags: [ai-agent, agentic-systems, rollback, linux-bonding, netplan, kubernetes, sre]
---

코드를 쓰는 에이전트는 틀려도 `git revert` 로 돌아온다. 그런데 에이전트에게
**운영 중인 서버의 네트워크 설정**을 맡기면 이야기가 달라진다. 설정을 잘못 밀면
그 순간 에이전트 자신이 그 서버에 접속할 수 없게 된다. 되돌릴 손이 끊기는 것이다.

어젯밤 K3s 클러스터의 etcd 노드 한 대를 무선에서 유선으로 바꾸는 작업을 에이전트로
수행했다. 다운타임 3분 26초, 파드 44개 전부 정상 복귀, 폴백 시험에서 패킷 손실 0%.
그 과정에서 쓴 안전장치 네 가지를 정리한다. 특별한 도구는 하나도 안 썼다 — 전부
리눅스 커널과 netplan 이 원래부터 문서로 제공하는 기능이다.

## 0. 왜 "에이전트라서" 다른가

Anthropic 의 「Building effective agents」는 에이전트와 워크플로를 이렇게 구분한다.

> **Agents** are systems where LLMs dynamically direct their own processes and tool
> usage, maintaining control over how they accomplish tasks. **Workflows** are systems
> where LLMs and tools are orchestrated through predefined code paths.
>
> — Anthropic, *Building effective agents* (2024-12-19)[^1]

같은 글은 이렇게도 말한다. "가장 단순한 해법부터 찾고, 필요할 때만 복잡도를 올려라."[^1]

이 구분이 운영 작업에서 실질적인 차이를 만든다. 에이전트는 스스로 판단해서 다음
명령을 고른다. 그 말은 **판단이 틀렸을 때 멈춰 세울 사람이 루프 안에 없다**는 뜻이다.
워크플로라면 "3단계에서 사람 승인" 같은 게이트를 코드로 박아둘 수 있지만, 에이전트는
자기가 짠 순서대로 달린다. 그래서 에이전트에게 위험한 일을 시킬 때의 설계 목표는
*틀리지 않게 하는 것*이 아니라 **틀려도 스스로 돌아오게 하는 것**이 된다.

## 1. "적용하지 않는 검증"이 있는가

첫 번째로 찾을 것은 *바꾸지 않고 확인하는 경로*다. netplan 에는 그게 있다.

```bash
netplan generate --root-dir /tmp/npcheck
```

공식 man 페이지의 설명이 정확히 이 역할을 못박는다.

> `netplan generate` converts Netplan YAML into configuration files understood by
> the back ends (systemd-networkd or NetworkManager). **It does not apply the
> generated configuration.**
>
> `--root-dir ROOT_DIR`: Instead of looking in /{lib,etc,run}/netplan, look in
> /ROOT_DIR/{lib,etc,run}/netplan.
>
> — Netplan 문서, *netplan-generate*[^2]

임시 디렉터리에 YAML 을 넣고 렌더링만 시켜보면, 실제 시스템은 손대지 않은 채로
"이 설정이 어떤 백엔드 파일로 번역되는가"를 눈으로 확인할 수 있다. 이번 작업에서는
이 단계에서 본드 인터페이스와 슬레이브 두 개가 의도대로 나오는지, 특히 슬레이브에
`master=bond0`, `slave-type=bond` 가 붙는지를 확인하고 나서야 적용으로 넘어갔다.

에이전트에게 이건 특히 중요하다. 사람은 설정 파일을 보고 "어 이거 좀 이상한데"를
느끼지만, 에이전트는 자기가 방금 쓴 YAML 을 의심하지 않는다. **렌더 결과를 기계가
직접 읽고 대조하게 만드는 것**이 그 자리를 대신한다.

## 2. 사람 확인에 의존하는 롤백은 에이전트에게 맞지 않는다

netplan 에는 자동 롤백 기능도 이미 있다. `netplan try` 다.

> `netplan try` takes a netplan configuration, applies it, and automatically rolls
> it back if the user does not confirm the configuration within a time limit.
> A configuration can be confirmed or rejected interactively or by sending the
> SIGUSR1 or SIGINT signals. **This may be especially useful on remote systems, to
> prevent an administrator being permanently locked out** of systems in the case of
> a network configuration error.
>
> — `man netplan-try` (노드에서 직접 확인)[^3]

문제 의식은 정확히 같다. 그런데 **확인 주체가 "the user"** 다. 대화형 터미널이나
시그널을 전제한다. SSH 세션이 그 설정 변경으로 끊길 수 있는 상황에서, 그 SSH 세션을
통해 확인 시그널을 보내야 한다는 건 순환이다. 에이전트가 쓰기엔 맞지 않는다.

그래서 같은 발상을 **무인 경로로 다시 만들었다.** 부팅 후 한 번만 도는
systemd oneshot 유닛이다.

```sh
# 부팅 120초 대기 → 게이트웨이 핑 6회 시도 → 실패하면 롤백 후 재시동
# 성공하면 스스로 systemctl disable 하고 끝낸다
```

판정 기준을 "사람의 확인"에서 **"게이트웨이에 실제로 닿는가"** 라는 기계가 검증
가능한 조건으로 바꾼 것이 핵심이다. 실제 로그는 이렇게 남았다.

```
22:57:38 netswitch-watchdog.service - 시작
22:59:40 netswitch-watchdog.service: Deactivated successfully.
```

게이트웨이에 닿았으므로 롤백하지 않고 스스로 무장해제했다. **롤백이 안 걸린 것이
정상 신호**이고, 그게 로그로 증명된다는 점이 중요하다. 안전장치는 "달아뒀다"가 아니라
"작동한 흔적이 있다"까지 가야 한다.

## 3. 순서가 곧 안전장치다 — 실제로 밟은 지뢰

이번 작업에서 실제로 사고가 날 뻔한 지점은 설정 내용이 아니라 **순서**였다.

전환 전에 조사해보니, 그 노드의 유선 인터페이스 프로필은 NetworkManager 의
`autoconnect-priority` 가 100 이었다. 무선 프로필들은 20~40. 그리고 유선 프로필은
DHCP 와 고정 주소를 **둘 다** 들고 있었다 — 무선이 이미 쓰고 있는 바로 그 고정 주소를.

즉 **본드를 적용하기 전에 랜선을 먼저 꽂으면** 유선과 무선이 같은 IP 를 동시에 들고
기본 경로가 두 개 생긴다. 그리고 리눅스의 기본값(`arp_ignore=0`)에서는 두 인터페이스가
**둘 다 그 IP 에 대한 ARP 에 응답한다.** 그때그때 이긴 쪽으로 트래픽이 가고, 겉보기엔
멀쩡해 보인다. etcd 정족수 한 표가 달린 노드에서 운에 맡길 상태가 아니다.

이걸 사전에 찾아내서 "① 본드 적용 후 재시동 → ② 그 다음에 랜선" 순서로 고정했고,
경고도 남겼다. 그런데 사용자가 랜선을 먼저 꽂았고, 예측한 그대로 이중 IP 가 났다.
다행히 그 시점에 이미 진단 경로가 준비돼 있어서 2분 만에 확인하고 본드 적용으로
해소했다.

교훈은 이쪽이다. **에이전트가 "무엇을 할까"만큼이나 "무엇을 먼저 할까"를 명시적으로
근거와 함께 적어두면, 그 문서가 사고 났을 때의 진단서가 된다.** 순서를 지키지 못했을
때 무슨 증상이 나는지까지 적어뒀기 때문에, 증상을 보자마자 원인이 특정됐다.

## 4. 시험하지 않은 백업은 백업이 아니다

본드를 active-backup 으로 구성하면 유선이 죽었을 때 무선으로 넘어간다 — 고
문서에는 쓰여 있다. 하지만 **이번 구성에는 커널 문서가 명시적으로 경고하는 위험이
하나 들어 있었다.** `fail_over_mac=active` 다.

> The "active" fail_over_mac policy indicates that the MAC address of the bond should
> always be the MAC address of the currently active slave. (...) The down side of this
> policy is that every device on the network must be updated via gratuitous ARP (...).
> **If the gratuitous ARP is lost, communication may be disrupted.**
>
> — Linux Kernel Documentation, *Linux Ethernet Bonding Driver HOWTO*[^4]

그리고 그 gratuitous ARP 는 기본값으로 **한 번만** 나간다.

> `num_grat_arp`, `num_unsol_na`: Specify the number of peer notifications (gratuitous
> ARPs and unsolicited IPv6 Neighbor Advertisements) to be issued after a failover
> event. (...) The valid range is 0 - 255; **the default value is 1.**
>
> — 같은 문서[^4]

한 발 쏴서 그게 유실되면 통신이 끊긴다는 뜻이다. 그러니 "폴백이 있다"는 건 **설정의
존재**일 뿐 **작동의 증거**가 아니다.

그래서 랜선을 뽑지 않고 시험했다. 커널이 sysfs 로 제공하는 강제 전환이다.

> `active_slave`: Specifies the new active slave for modes that support it
> (active-backup, balance-alb and balance-tlb). (...) If a name is given, the slave
> and its link must be up in order to be selected as the new active slave.
>
> — 같은 문서[^4]

```sh
echo <무선 인터페이스> > /sys/class/net/bond0/bonding/active_slave
# 25초 뒤 자동으로 되돌린다 (SSH 가 끊겨도 노드가 스스로 복귀하도록 detach 실행)
echo <유선 인터페이스> > /sys/class/net/bond0/bonding/active_slave
```

시험 스크립트를 **자기복귀형**으로 짠 게 포인트다. 내가 명령을 넣고 결과를 기다리는
구조였다면, 무선 전환 직후 SSH 가 끊기는 순간 노드는 무선에 갇힌다. 그래서 전환·대기·복귀를
한 덩어리로 묶어 systemd 유닛으로 떼어 실행했다. 에이전트의 접속이 죽어도 노드는 돌아온다.

전환하는 동안 옆 노드에서 0.5초 간격으로 120번 핑을 쐈다. 결과:

| 구간 | n | avg | 중앙값 | max | mdev |
| --- | --- | --- | --- | --- | --- |
| 유선 | 70 | 0.236 | 0.232 | 1.020 | 0.102 |
| 무선 | 50 | 3.064 | 1.010 | 56.500 | 7.971 |

**120발 중 120발 도착, 손실 0%.** 전환 순간에도 복귀 순간에도 빠진 패킷이 없었다.

```
seq7  0.283ms (유선) → seq8  1.020ms (무선)   ← 전환
seq57 0.978ms (무선) → seq58 0.257ms (유선)   ← 복귀
```

한 발뿐인 gratuitous ARP 가 제대로 도착했다는 뜻이다. 이제 폴백은 추측이 아니라
측정값이다. 덤으로, 같은 시험 안에서 **무선은 중앙값이 4배, 최악값이 55배**라는 것도
같이 나왔다 — 비상용으로는 충분하고 상시용으로는 못 쓸 물건이라는 게 숫자로 확인됐다.

참고로 커널 문서는 링크 감시 설정 자체를 강하게 요구한다.

> It is critical that either the miimon or arp_interval and arp_ip_target parameters
> be specified, otherwise serious network degradation will occur during link failures.
>
> — 같은 문서[^4]

## 5. 그래서 에이전트 몫은 어디까지인가

이번 작업에서 에이전트가 한 일과 사람이 한 일은 꽤 깔끔하게 갈렸다.

| 에이전트 | 사람 |
| --- | --- |
| 현재 설정 조사, 지뢰(우선순위 100 + 중복 IP) 발견 | 작업 승인, 재시동 시점 결정 |
| 적용 안 하는 검증, 스크립트 스테이징 | 랜선 물리적으로 꽂기 |
| 적용·재시동·복귀 확인·수치 측정 | 폴백 시험 여부 판단 |
| 기록 갱신 | |

경계가 이렇게 잡힌 이유는 단순하다. **되돌릴 수 없거나 물리적인 일은 사람 쪽**이고,
**되돌릴 길이 마련된 일은 에이전트 쪽**이다. 재시동은 3분짜리 서비스 중단이라 사람이
시점을 잡았고, 설정 적용은 와치독이 되돌려주므로 에이전트가 했다.

앞서 인용한 Anthropic 글이 프레임워크에 대해 하는 경고도 같은 맥락으로 읽힌다.

> These frameworks (...) often create extra layers of abstraction that can obscure the
> underlying prompts and responses, making them harder to debug. (...) We suggest that
> developers start by using LLM APIs directly (...). Incorrect assumptions about what's
> under the hood are a common source of customer error.
>
> — Anthropic, *Building effective agents*[^1]

"밑에서 뭐가 도는지에 대한 잘못된 가정"이 사고의 흔한 원인이라는 것. 운영 작업에서는
이게 더 직접적이다. 이번 건의 지뢰도 결국 "NetworkManager 프로필 우선순위가 몇이고
거기 어떤 주소가 박혀 있는가"라는, **추상화 밑을 직접 들여다봐야만 보이는 것**이었다.
에이전트가 그걸 건너뛰고 "본드 설정 YAML 을 쓴다"는 레벨에서만 놀았다면 지뢰는
그대로 밟혔다.

## 정리

운영 인프라를 만지는 에이전트를 설계한다면, 능력보다 먼저 확인할 게 이 네 가지다.

1. **적용하지 않고 검증하는 경로가 있는가** — 없으면 만들거나, 그 작업은 맡기지 않는다
2. **롤백이 사람의 확인에 의존하지 않는가** — 기계가 판정할 수 있는 조건으로 바꾼다
3. **순서를 근거와 함께 적어뒀는가** — 그 문서가 사고 났을 때의 진단서가 된다
4. **폴백을 실제로 한 번 써봤는가** — 설정의 존재는 작동의 증거가 아니다

넷 다 새로운 개념이 아니다. `netplan generate --root-dir`, `netplan try`, systemd
oneshot, bonding 의 `active_slave` — 전부 수년~수십 년 된 기능이고 공식 문서에 다 있다.
달라진 건 **이 기능들을 쓸 사람이 이제 사람이 아닐 수도 있다**는 것뿐이다. 그리고
사람이 아닌 쪽이 쓸 때는, "잘 하면 된다"가 통하지 않는다. 돌아오는 길이 코드로
깔려 있어야 한다.

---

### References

[^1]: Anthropic, "Building effective agents", Anthropic Engineering, 2024-12-19. <https://www.anthropic.com/engineering/building-effective-agents>
[^2]: Netplan Documentation, "NETPLAN-GENERATE". <https://netplan.readthedocs.io/en/stable/netplan-generate/>
[^3]: Netplan Documentation, "NETPLAN-TRY". <https://netplan.readthedocs.io/en/stable/netplan-try/> (본문 인용은 Ubuntu 노드의 `man netplan-try` 출력에서 직접 확인)
[^4]: The Linux Kernel Documentation, "Linux Ethernet Bonding Driver HOWTO". <https://docs.kernel.org/networking/bonding.html>

*본문의 측정값은 모두 자체 운영 중인 6노드 K3s 클러스터에서 2026-09-21 밤에 직접
측정한 것이다. 재현 조건(하드웨어·무선 환경)이 다르면 수치는 달라진다. 내부 네트워크
주소·MAC·SSID 등 식별 정보는 의도적으로 제외했다.*
