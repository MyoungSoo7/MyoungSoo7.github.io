---
layout: post
title: "서버 보안 점검표를 우리 노드 6대에 대 봤다 — 설정 파일이 아니라 실효값을 읽어야 한다"
date: 2026-09-24 20:22:58 +0900
categories: [security, devops]
tags: [linux, ssh, sshd, ufw, unattended-upgrades, hardening, kubernetes, k3s]
---

오늘 먼저 올라온 [리눅스 서버 보안 — 새 서버를 받으면 제일 먼저 잠그는 6 가지](/2026/09/24/linux-server-hardening-checklist/)는
그 글 스스로 "했다" 와 "적용됐다" 는 다르다는 말로 끝난다. 이 글은 그 말을 그대로 실험해 본 기록이다.
우리 홈랩 K3s 클러스터의 리눅스 노드 6대에 읽기 전용 명령만 써서, 점검표 항목이 **실제로 적용돼 있는지** 쟀다.

결론부터 적으면, 사람이 "해 뒀다" 고 믿는 상태와 커널·데몬이 지금 따르는 상태가 세 군데에서 어긋났다.
세 곳 모두 흔히 쓰는 확인 명령이 **틀린 답을 주거나, 반만 맞는 답을 준다**는 공통점이 있었다.

> 공개 글이라 노드 이름·포트 번호·OS 버전은 빼고 "6대 중 N대" 로만 적는다. 약점 지도를 공개하지 않기 위해서다.
> 측정 시각은 2026-09-24 저녁(KST)이고, 설정은 하나도 바꾸지 않았다.

## 측정 결과 한눈에

| 항목 | 점검표의 기대 | 실측 (6대 중) |
|---|---|---|
| SSH 비밀번호 로그인 | 꺼짐 | **6대 모두 켜짐** (`sshd -T` 실효값) |
| root 원격 로그인 | 금지 | 금지 1대, 키로만 허용 5대 |
| 호스트 방화벽(ufw) | 기본 차단 | **6대 모두 규칙 비활성** — 그중 3대는 서비스 상태가 `active` |
| 자동 보안 업데이트 | 켜짐 | 6대 모두 켜짐 |
| 새 커널로 부팅 | 업데이트 후 재부팅 | **4대가 재부팅 대기** — 오늘 아침 자동 설치된 커널 |
| 무차별 대입 차단(fail2ban, sshd jail) | 켜짐 | 5대 |
| 감사 로그(auditd) | 켜짐 | 1대 |
| 루프백 아닌 주소에서 대기 중인 TCP 포트 | 최소 | 노드당 8~28개 |

숫자만 보면 "절반은 안 했다" 로 읽힌다. 그런데 하나씩 따라가 보니 대부분은 안 한 게 아니라,
**했다고 생각한 방법이 실효값을 바꾸지 못했거나 잘못된 곳을 보고 확인한** 경우였다.

## 1. SSH — 설정 파일을 grep 하면 안 되는 이유

6대 모두 `PasswordAuthentication` 의 실효값이 `yes` 였다. 그런데 이 `yes` 가 어디서 왔는지는 노드마다 달랐다.

- **3대는 `yes` 가 명시돼 있었다.** 세 대 모두 본 설정 파일이 아니라 `sshd_config.d/50-cloud-init.conf` 였다. 설치 때 cloud-init 이 만든 파일이라, 사람이 이 줄을 직접 쓴 적은 없다.
- **3대는 아무 데도 적혀 있지 않았다.** 그런데 OpenSSH 의 기본값이 `yes` 다. 그중 1대에는 `99-hardening.conf` 라는
  하드닝 드롭인까지 있었다. `MaxAuthTries`·`X11Forwarding`·`AllowTcpForwarding` 등 여덟 줄이 있었지만 비밀번호 인증 줄은 없었다.
  하드닝은 했지만 가장 중요한 한 줄이 빠진 셈이다.

두 번째 함정은 우선순위다. [sshd_config(5)](https://man.openbsd.org/sshd_config) 에 따르면 따로 적힌 예외가 없는 한
**같은 키워드는 먼저 읽힌 값이 이긴다.** Ubuntu 는 본 설정 파일 앞부분에서 `Include /etc/ssh/sshd_config.d/*.conf` 를 읽는다.
그래서 드롭인이 파일 아래쪽의 설정보다 먼저 적용된다. 흔히 하듯 `/etc/ssh/sshd_config` 맨 아래에
`PasswordAuthentication no` 를 추가해도, 드롭인에 `yes` 가 있으면 그 줄은 **조용히 무시된다.**
에러도 경고도 없다.

그래서 확인은 파일이 아니라 데몬에게 묻는다.

```bash
sudo sshd -T | grep -Ei '^(passwordauthentication|permitrootlogin|kbdinteractiveauthentication) '
```

`sshd -T` 는 모든 파일과 기본값을 합쳐 **데몬이 실제로 쓸 값**을 출력한다. `grep` 은 사람이 쓴 줄을 보여 줄 뿐이다.
(`sshd -T` 도 디스크의 설정을 읽는 것이라, 설정을 바꾼 뒤 데몬을 다시 읽히지 않았다면 떠 있는 프로세스와 다를 수 있다.
이번 측정에서는 그 차이까지는 재지 않았다.)

root 로그인도 같은 방식으로 쟀다. 5대가 `prohibit-password` 였는데, 1대는 옛 별칭 `without-password` 로 표시됐다.
뜻은 같다. 키로는 root 로 들어올 수 있다는 뜻이고, 이것도 "root 금지" 는 아니다.

## 2. 방화벽 — `systemctl is-active ufw` 는 거짓말을 한다

6대 모두 `ufw status` 가 `Status: inactive` 였다. 이상한 건 그중 3대에서 `systemctl is-active ufw` 가 `active` 를 돌려줬다는 점이다.
모니터링이나 점검 스크립트가 systemd 상태만 본다면 이 3대는 "방화벽 켜짐" 으로 집계된다.

유닛 파일을 보면 이유가 나온다.

```ini
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/lib/ufw/ufw-init start quiet
```

`ufw.service` 는 부팅 때 한 번 규칙을 올리고 끝나는 oneshot 유닛이다. `RemainAfterExit=yes` 라서 실행이 끝난 뒤에도 `active` 로 남는다.
그리고 `/etc/ufw/ufw.conf` 의 `ENABLED=no` 이면 규칙을 하나도 올리지 않고 **정상 종료**한다.
그래서 "서비스는 active, 방화벽은 꺼짐" 이 모순 없이 동시에 성립한다.
`is-active` 가 알려 주는 건 "유닛이 실행에 성공했다" 뿐이다. "패킷을 막고 있다" 는 뜻이 아니다.

확인은 이렇게 한다.

```bash
sudo ufw status verbose        # 규칙이 올라가 있는가
sudo nft list ruleset | head   # 커널에 실제로 무엇이 있는가
```

### 그런데 방화벽을 꺼 둔 건 실수가 아니다

여기서 "켜면 된다" 로 끝내면 반만 맞다. [K3s 공식 요구사항 문서](https://docs.k3s.io/installation/requirements)는
Ubuntu 에서 **ufw 를 끄라고 권장**한다. 켜 둘 거라면 API 서버 포트와 파드·서비스 대역을 여는 규칙이 필요하다고 명시한다.
쿠버네티스 노드는 CNI·kube-proxy 가 iptables/nftables 를 직접 다루기 때문에 호스트 방화벽과 충돌하기 쉽다.
그래서 우리 노드의 방화벽이 꺼진 건 문서를 따른 선택이다.

다만 그 선택에는 대가가 따른다. 쿠버네티스 [NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)는
**파드** 사이의 트래픽 규칙이다. 노드에서 직접 도는 `sshd` 나 노드 익스포터 같은 호스트 프로세스는 그 대상이 아니다.
호스트 방화벽을 끄면 노드당 8~28개의 대기 포트가 같은 망 안의 누구에게나 열린다.
그리고 그 망 안에는 우리가 올린 파드들도 있다. 비밀번호 SSH 가 6대 모두 켜져 있다는 사실은 **여기서 비로소 의미를 갖는다.** 파드 하나가 뚫리면 공격자는 같은 망에서 노드들의 SSH 에
비밀번호를 대 볼 수 있다. fail2ban 의 sshd jail 은 5대에서 돌고 있어 반복 시도를 늦춰 주지만, 1대에는 그것마저 없다.
fail2ban 은 시도 속도를 낮출 뿐이다. 비밀번호 인증 자체를 끄는 것과는 다른 층이다.

외부 인터넷에 SSH 가 노출돼 있는지는 이번에 측정하지 못했다. 클러스터 안의 터널(cloudflared) 설정에는 SSH 경로가 없었지만,
공유기의 포트 포워딩은 노드 안에서 볼 수 없는 영역이다. 그래서 여기서는 위험을 **내부 횡이동**으로만 적는다.

## 3. 업데이트 — "All upgrades installed" 인데 옛 커널이 돈다

자동 보안 업데이트(`unattended-upgrades`)는 6대 모두 켜져 있었다. 그런데 4대에 `/var/run/reboot-required` 가 있었다.
확인해 보니 네 파일 모두 **오늘 날짜**였고, 원인도 같았다. 오늘 아침 자동 업데이트가 새 커널 이미지를 설치한 것이다.
이 4대에서는 떠 있는 커널(`uname -r`)이 디스크에 설치된 가장 새 커널보다 한 단계 뒤였다.

이건 고장이 아니라 기본 동작이다. [Ubuntu 서버 문서](https://documentation.ubuntu.com/server/how-to/software/automatic-updates/)가 설명하듯
`unattended-upgrades` 는 업데이트가 재부팅을 필요로 할 때 **재부팅까지 하도록 설정할 수 있는** 도구다.
하지만 설정 파일을 열어 본 노드에서 `Unattended-Upgrade::Automatic-Reboot` 줄은 주석 처리돼 있었다(기본값 그대로다).
패키지는 깔렸고 로그에는 `All upgrades installed` 가 찍혔다. 그런데 커널 취약점 패치는 재부팅 전까지 메모리에 올라오지 않는다.
**"설치됨" 과 "적용됨" 사이의 간격은 사람이 재부팅할 때까지 무한정 늘어날 수 있다.**

나머지 2대는 반대로 보안 업데이트가 설치 대기 상태였다(각각 10개, 8개 패키지). 목록은 대부분 커널 메타패키지와 관련 도구였다.
처음에는 phased update 때문에 보류된 것인지 의심했다. 하지만 Ubuntu 문서는
[보안 업데이트는 단계적 배포 대상이 아니라고](https://documentation.ubuntu.com/server/explanation/software/about-apt-upgrade-and-phased-updates/) 명시한다.
원인은 시점으로 보인다. 두 노드의 오늘 아침 실행 로그는 `All upgrades installed` 로 끝났고, 이 패키지들은 그 뒤 목록 갱신 때 올라온 것으로 보인다.
다음 실행은 내일 아침이다. 거기서 새 커널이 설치되면 이 2대도 앞의 4대와 같은 **재부팅 대기** 상태가 된다.

그래서 업데이트 점검은 한 줄로 끝나지 않는다.

```bash
cat /var/run/reboot-required 2>/dev/null        # 재부팅이 필요한가
uname -r; ls /boot/vmlinuz-* | sort -V | tail -1 # 떠 있는 커널 vs 설치된 커널
apt list --upgradable 2>/dev/null | grep -c security
```

우리 클러스터는 연구용이라 노드가 수시로 재부팅되고, 실제로 가동 일수가 2~13일이었다. 그래서 지금은 간격이 짧다.
하지만 가동 일수가 길어질수록 이 간격은 조용히 벌어진다. 어떤 대시보드도 이걸 빨간불로 띄우지 않는다.

## 4. 공통점 — 확인 명령이 무엇을 말하는지

세 가지 어긋남은 구조가 같다.

| 사람이 흔히 보는 것 | 실제로 말해 주는 것 | 봐야 하는 것 |
|---|---|---|
| `grep PasswordAuthentication /etc/ssh/sshd_config` | 사람이 그 파일에 쓴 줄 | `sshd -T` — 드롭인·기본값·우선순위를 합친 실효값 |
| `systemctl is-active ufw` | 부팅 스크립트가 성공했는지 | `ufw status`, `nft list ruleset` — 커널에 올라간 규칙 |
| 업데이트 로그 `All upgrades installed` | 디스크에 패키지가 깔렸는지 | `reboot-required`, `uname -r` vs 설치된 커널 |

점검표는 "무엇을 해야 하는가" 를 알려 준다. 하지만 **"됐는가" 는 그걸 집행하는 주체(데몬·커널)에게 직접 물어야** 안다.
설정 파일, 유닛 상태, 설치 로그는 모두 한 단계 떨어진 대리 지표다. 그리고 셋 다 틀린 채로 초록불을 켤 수 있다.

이번 측정에서 얻은 가장 큰 수확은 "절반이 비어 있다" 는 사실이 아니다. 그 절반이 **누구도 놓쳤다고 느끼지 못한 채로** 비어 있었다는 점이다.
하드닝 파일이 있는 노드는 SSH 가 잠겨 보이고, 서비스 상태만 보면 방화벽이 켜져 보인다. 점검표에 체크를 하기에는 충분한 신호다.

## 다음 단계와 한계

- 비밀번호 SSH 차단, 재부팅 대기 해소, 남은 1대의 fail2ban 은 노드 설정을 바꾸는 일이라 이번 글에서는 하지 않았다.
  무선으로 묶인 연구용 클러스터라 재부팅은 한 대씩 따로 해야 한다.
- 외부 노출(공유기 포트 포워딩)은 측정 범위 밖이다. 이 글의 위험 평가는 내부 횡이동 기준이다.
- 측정은 한 시점의 스냅샷이다. `sshd -T` 는 디스크 설정 기준이라 떠 있는 데몬과의 차이는 재지 않았다.
- 대기 포트 수는 루프백을 뺀 TCP 대기 소켓을 센 값이다. 서비스별로 인증이 있는지는 따지지 않았다.

## References

1. OpenBSD manual pages, [sshd_config(5)](https://man.openbsd.org/sshd_config) — "first obtained value" 규칙, `PasswordAuthentication` 기본값
2. K3s Documentation, [Requirements — UFW / Firewalld](https://docs.k3s.io/installation/requirements)
3. Kubernetes Documentation, [Network Policies](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
4. Ubuntu Server documentation, [Automatic updates](https://documentation.ubuntu.com/server/how-to/software/automatic-updates/)
5. Ubuntu Server documentation, [About apt upgrade and phased updates](https://documentation.ubuntu.com/server/explanation/software/about-apt-upgrade-and-phased-updates/)
6. systemd, [systemd.service(5) — `Type=oneshot`, `RemainAfterExit=`](https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html)
