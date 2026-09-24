---
layout: post
title: "리눅스 서버 보안 — 새 서버를 받으면 제일 먼저 잠그는 6 가지"
date: 2026-09-24 19:45:00 +0900
categories: [security, devops]
tags: [linux, ssh, sshd, hardening, firewall, unattended-upgrades, systemd, sysctl, auditd, fail2ban]
---

서버 보안 이야기는 금방 거창해진다. 제로 트러스트, SIEM, EDR 같은 것들이다.
그런데 실제 사고는 대부분 훨씬 시시한 곳에서 난다. **비밀번호로 열려 있는 SSH, 몇 달째
안 올린 패키지, 쓰지도 않는데 열려 있는 포트, root 로 도는 서비스** 같은 것들이다.

이 글은 [원칙을 다룬 7 기둥 글](/2026/06/20/security-7-pillars-auth-encryption-firewall-audit/)의
실전편이다. 리눅스 서버 한 대를 새로 받았을 때 **순서대로 무엇을 잠그고, 잠갔는지 어떻게
확인하는지**를 적는다. 명령은 Debian/Ubuntu 기준이다.

> 이 글의 기본 틀은 NIST 의 [SP 800-123 *Guide to General Server Security*](https://csrc.nist.gov/pubs/sp/800/123/final)
> 와 같다. OS 를 먼저 잠그고, 필요 없는 건 빼고, 남은 걸 최소 권한으로 돌리고, 기록을 남긴다.

---

## TL;DR

| # | 할 일 | 확인 명령 |
|---|---|---|
| 1 | SSH 는 키로만, root 직접 로그인 금지 | `sudo sshd -T \| grep -E 'passwordauth\|permitroot'` |
| 2 | 보안 업데이트 자동 적용 | `systemctl status unattended-upgrades` |
| 3 | 방화벽은 기본 차단, 필요한 포트만 허용 | `sudo ufw status verbose`, `ss -tlnp` |
| 4 | 서비스는 root 가 아닌 계정 + systemd 샌드박스로 | `systemd-analyze security` |
| 5 | 커널 정보 노출 줄이기 (sysctl) | `sysctl kernel.dmesg_restrict kernel.kptr_restrict` |
| 6 | 무차별 대입 차단과 감사 로그 | `fail2ban-client status`, `ausearch` |

순서가 중요하다. **1 번을 하기 전에는 다른 걸 하지 않는다.** 인터넷에 붙은 서버는 켜지는
순간부터 SSH 무차별 대입을 맞는다. MITRE ATT&CK 은 이를
[T1110 Brute Force](https://attack.mitre.org/techniques/T1110/) 로 따로 분류해 둘 만큼
흔한 초기 침투 기법으로 본다.

---

## 1. SSH — 키로만 들어오게 한다

### 1.1 기본값을 먼저 알아야 한다

[OpenSSH `sshd_config` 매뉴얼](https://man.openbsd.org/sshd_config)에 적힌 업스트림 기본값은 이렇다.

| 옵션 | 기본값 | 의미 |
|---|---|---|
| `PasswordAuthentication` | `yes` | 비밀번호 로그인 **허용** |
| `PermitRootLogin` | `prohibit-password` | root 는 키로만 허용 (비밀번호는 거부) |
| `MaxAuthTries` | `6` | 연결당 인증 시도 횟수. 절반을 넘으면 실패가 로그에 남는다 |
| `AllowUsers` | (없음) | 지정하지 않으면 **모든 사용자** 로그인 허용 |

즉 아무것도 안 건드리면 **일반 계정은 비밀번호로 들어올 수 있고, 모든 계정이 대상이다.**
배포판이 기본값을 바꿔 두기도 하니, 문서보다 실제 적용값을 봐야 한다(1.3).

### 1.2 설정

먼저 **키 로그인이 되는지부터 확인**한다. 순서를 뒤집으면 스스로를 잠가 버린다.

```bash
# 로컬에서 키 생성 (Ed25519) 후 서버에 등록
ssh-keygen -t ed25519 -C "me@laptop"
ssh-copy-id -i ~/.ssh/id_ed25519.pub deploy@server

# 새 터미널에서 키로 들어가지는지 확인 — 기존 세션은 닫지 않는다
ssh -i ~/.ssh/id_ed25519 deploy@server
```

그다음 드롭인 파일을 하나 만든다.

```bash
sudo tee /etc/ssh/sshd_config.d/00-hardening.conf >/dev/null <<'EOF'
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin no
MaxAuthTries 3
AllowUsers deploy
X11Forwarding no
EOF

sudo sshd -t && sudo systemctl reload ssh
```

파일 이름을 `00-` 으로 시작하게 한 데에는 이유가 있다. 매뉴얼에 따르면 `sshd_config` 는
*"각 키워드에 대해 처음 얻은 값을 쓴다"*. 그래서 **나중에 적은 값이 이기는 게 아니라 먼저 읽힌
값이 이긴다.** `Include /etc/ssh/sshd_config.d/*.conf` 가 본 파일 앞부분에 있으면 드롭인이 먼저
읽히고, 드롭인끼리는 이름순이다. 클라우드 이미지가 넣어 둔 `50-cloud-init.conf` 에
`PasswordAuthentication yes` 가 있다면 `00-` 파일이 그보다 먼저 읽혀야 한다.

### 1.3 확인은 파일이 아니라 적용값으로

설정 파일을 `cat` 하는 건 확인이 아니다. 위에 쓴 대로 어느 줄이 이길지는 읽는 순서가 정한다.
[`sshd -T`](https://man.openbsd.org/sshd) 는 *"실제로 적용될 설정을 출력"* 한다.

```bash
sudo sshd -T | grep -Ei '^(passwordauthentication|kbdinteractiveauthentication|permitrootlogin|maxauthtries|allowusers)'
```

여기서 `passwordauthentication no` 가 나와야 끝난 것이다.

---

## 2. 업데이트 — 사람이 기억하게 두지 않는다

패치가 나온 취약점도 적용하지 않으면 계속 열려 있다. 미국 CISA 는 **실제 공격에 쓰인 것이
확인된 취약점**만 모아
[Known Exploited Vulnerabilities 카탈로그](https://www.cisa.gov/known-exploited-vulnerabilities-catalog)로
공개한다. 이 목록에 오른 항목은 이론상 위험이 아니라 이미 누군가 쓰고 있는 공격이다.

Debian/Ubuntu 에서는 [`unattended-upgrades`](https://wiki.debian.org/UnattendedUpgrades) 가
보안 업데이트를 자동으로 적용한다.

```bash
sudo apt install unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades

# 실제로 도는지, 무엇을 설치했는지
systemctl status unattended-upgrades
sudo unattended-upgrade --dry-run --debug | tail
ls /var/log/unattended-upgrades/
```

주의할 점이 하나 있다. 커널이나 glibc 를 업데이트해도 **재부팅하거나 서비스를 재시작하기
전에는 옛 코드가 메모리에서 계속 돈다.** `/var/run/reboot-required` 파일이 생겼는지 보고,
재부팅할 시간을 따로 잡는다.

---

## 3. 방화벽 — 기본은 차단

먼저 지금 무엇이 열려 있는지 본다.

```bash
sudo ss -tlnp     # 듣고 있는 TCP 포트와 프로세스
sudo ss -ulnp     # UDP
```

`0.0.0.0` 이나 `[::]` 에 붙어 있는데 외부에서 쓸 일이 없는 서비스라면 `127.0.0.1` 에만 붙게
설정을 바꾸거나, 아예 끈다. **방화벽은 두 번째 방어선이다.** 방화벽을 켜기 전에 안 쓰는 서비스부터
끈다.

그다음 기본 차단 정책을 건다.

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow OpenSSH          # SSH 를 먼저 열어야 잠기지 않는다
sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw status verbose
```

> ⚠️ **Docker 를 쓰는 서버라면**, 컨테이너 포트 공개(`-p`)는 Docker 가 iptables 에 직접 규칙을
> 넣어서 ufw 규칙을 우회할 수 있다. Docker 공식 문서
> [Packet filtering and firewalls](https://docs.docker.com/engine/network/packet-filtering-firewalls/#docker-and-ufw)
> 를 따로 확인한다. 컨테이너 포트는 `-p 127.0.0.1:8080:8080` 처럼 바인딩 주소를 명시하는 게 제일 간단하다.

---

## 4. 서비스는 최소 권한으로 — systemd 가 절반을 해 준다

직접 올린 서비스가 root 로 돈다면, 그 서비스에 취약점이 하나만 있어도 서버 전체가 넘어간다.
systemd 유닛 파일 몇 줄로 공격 범위를 크게 줄일 수 있다. 각 옵션의 정확한 의미는
[`systemd.exec(5)`](https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html) 에 있다.

```ini
[Service]
User=myapp
Group=myapp
NoNewPrivileges=yes          # setuid 바이너리 등으로 권한 상승 금지
ProtectSystem=strict         # / 전체를 읽기 전용으로
ReadWritePaths=/var/lib/myapp
ProtectHome=yes              # /home, /root 안 보이게
PrivateTmp=yes               # 서비스 전용 /tmp
PrivateDevices=yes
ProtectKernelTunables=yes
ProtectKernelModules=yes
ProtectControlGroups=yes
RestrictSUIDSGID=yes
CapabilityBoundingSet=       # capability 전부 제거 (1024 미만 포트가 필요하면 CAP_NET_BIND_SERVICE 만)
```

적용 결과는 [`systemd-analyze security`](https://www.freedesktop.org/software/systemd/man/latest/systemd-analyze.html)
로 잰다. 매뉴얼 설명대로 이 명령은 서비스별 보안 설정을 보고 **0.0~10.0 사이의 "exposure level"**
을 매긴다. 높을수록 샌드박스가 거의 없다는 뜻이다.

```bash
systemd-analyze security              # 전체 서비스 한눈에
systemd-analyze security myapp.service  # 항목별로 무엇이 빠졌는지
```

단, 매뉴얼에도 적혀 있듯 이 점수는 **systemd 가 구현한 기능만** 본다. 앱이 자체적으로 하는
보안은 반영되지 않는다. 절대적인 안전 등급이 아니라 체크리스트로 쓴다.

---

## 5. 커널 — 공격자에게 줄 정보를 줄인다

권한 상승 공격은 대개 커널 주소나 커널 로그를 읽는 데서 시작한다. 커널 공식 문서
[`/proc/sys/kernel/`](https://www.kernel.org/doc/html/latest/admin-guide/sysctl/kernel.html)
에 각 값이 설명돼 있다.

```bash
sudo tee /etc/sysctl.d/90-hardening.conf >/dev/null <<'EOF'
kernel.dmesg_restrict = 1            # 일반 사용자의 dmesg 열람 금지
kernel.kptr_restrict = 2             # /proc 에 커널 포인터 주소 노출 금지
kernel.unprivileged_bpf_disabled = 1 # 비특권 사용자의 bpf() 호출 금지
EOF
sudo sysctl --system
sysctl kernel.dmesg_restrict kernel.kptr_restrict kernel.unprivileged_bpf_disabled
```

배포판마다 이미 켜 둔 값이 있으니 먼저 `sysctl` 로 현재값을 보고, 없는 것만 추가한다.
AppArmor·SELinux 같은 LSM 도 이 층위에 속한다. 켜져 있는지 확인하는 것부터 시작한다
([커널 LSM 문서](https://docs.kernel.org/admin-guide/LSM/index.html)).

```bash
sudo aa-status | head      # Ubuntu: AppArmor
getenforce                 # RHEL 계열: SELinux
```

---

## 6. 막고, 남긴다 — fail2ban 과 auditd

**막는 쪽.** 1 번에서 비밀번호 로그인을 껐다면 무차별 대입은 이미 성공할 수 없다. 그래도 로그가
시끄럽고 다른 서비스(웹 로그인 등)도 있으니, [fail2ban](https://github.com/fail2ban/fail2ban)
으로 반복 실패한 IP 를 일정 시간 차단한다.

```bash
sudo apt install fail2ban
sudo tee /etc/fail2ban/jail.local >/dev/null <<'EOF'
[sshd]
enabled = true
EOF
sudo systemctl restart fail2ban
sudo fail2ban-client status sshd
```

**남기는 쪽.** 사고가 나면 **누가 언제 무엇을 바꿨는가**가 제일 먼저 필요하다.
[`auditd`](https://man7.org/linux/man-pages/man8/auditd.8.html) 로 민감한 파일에 감시를 건다.

```bash
sudo apt install auditd
sudo auditctl -w /etc/ssh/sshd_config -p wa -k sshd_config
sudo auditctl -w /etc/sudoers -p wa -k sudoers
sudo ausearch -k sshd_config      # 누가 건드렸는지
```

`auditctl` 로 넣은 규칙은 재부팅하면 사라진다. 영구 적용하려면 `/etc/audit/rules.d/` 아래
파일에 적는다. 그리고 로그가 그 서버 안에만 있으면, 서버를 장악한 공격자가 지울 수 있다.
가능하면 **다른 곳으로 보낸다.**

---

## 마무리 — "했다" 와 "적용됐다" 는 다르다

이 체크리스트에서 제일 자주 틀리는 건 설정을 몰라서가 아니다. **설정 파일을 고치고 적용됐다고
믿는 것**이다.

- `sshd_config` 를 고쳤는데 드롭인이 먼저 읽혀 비밀번호 로그인이 그대로 열려 있다.
- 패키지는 업데이트했는데 재부팅을 안 해서 옛 커널이 돈다.
- ufw 를 켰는데 Docker 가 연 포트는 그대로 열려 있다.

그래서 표의 오른쪽 열(확인 명령)이 왼쪽 열만큼 중요하다. 설정 파일이 아니라 **실행 중인 상태**를
확인해야 한다. 마지막으로, 밖에서 스캔해 보는 게 가장 정직한 확인이다. 서버 안에서 본
`ss -tlnp` 결과와 **외부 네트워크에서** 본 열린 포트 목록이 같아야 한다.

---

## References

- NIST, [SP 800-123: Guide to General Server Security](https://csrc.nist.gov/pubs/sp/800/123/final)
- OpenBSD, [sshd_config(5)](https://man.openbsd.org/sshd_config) · [sshd(8)](https://man.openbsd.org/sshd) · [ssh-keygen(1)](https://man.openbsd.org/ssh-keygen)
- MITRE ATT&CK, [T1110 Brute Force](https://attack.mitre.org/techniques/T1110/)
- CISA, [Known Exploited Vulnerabilities Catalog](https://www.cisa.gov/known-exploited-vulnerabilities-catalog)
- Debian Wiki, [UnattendedUpgrades](https://wiki.debian.org/UnattendedUpgrades)
- Docker Docs, [Packet filtering and firewalls](https://docs.docker.com/engine/network/packet-filtering-firewalls/#docker-and-ufw)
- systemd, [systemd.exec(5)](https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html) · [systemd-analyze(1)](https://www.freedesktop.org/software/systemd/man/latest/systemd-analyze.html)
- Linux Kernel, [Documentation for /proc/sys/kernel/](https://www.kernel.org/doc/html/latest/admin-guide/sysctl/kernel.html) · [Linux Security Module Usage](https://docs.kernel.org/admin-guide/LSM/index.html)
- fail2ban, [GitHub repository](https://github.com/fail2ban/fail2ban)
- man7.org, [auditd(8)](https://man7.org/linux/man-pages/man8/auditd.8.html)
