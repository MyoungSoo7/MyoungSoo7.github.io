---
layout: post
title: "PAM·계정통제 — 관리자 권한과 프로그램 설치를 막는다는 건 실제로 무엇을 막는가"
date: 2026-09-24 20:28:33 +0900
categories: [security, devops]
tags: [linux, pam, sudo, sudoers, least-privilege, docker, fapolicyd, apparmor, application-allowlisting]
---

"PAM/계정통제" 라는 이름의 통제는 보통 두 문장으로 설명된다. **관리자 권한 사용을 제한한다**, 그리고 **허가받지 않은 프로그램 설치를 제한한다**.
두 문장 다 맞는 말이지만, 리눅스에서 그 문장이 실제로 어떤 설정에 대응하는지 따져 보면 생각보다 빈 곳이 많다.
이 글은 그 통제가 무엇으로 이루어지는지 1차 문서로 정리하고, 우리 홈랩 K3s 클러스터의 리눅스 노드 6대에 **읽기 전용 명령만** 써서 실제 상태를 잰 기록이다.

앞서 올린 [서버 보안 점검표를 우리 노드 6대에 대 봤다](/2026/09/24/server-hardening-audit-effective-state-6-nodes/) 와 같은 방식이다.
노드 이름·계정명·주소·OS 버전은 싣지 않고 "6대 중 N대" 로만 적는다. 이 글을 쓰는 동안 설정은 하나도 바꾸지 않았다.

## 결론 먼저

- 관리자 권한 통제는 세 층이다. **누가 올라갈 수 있나**(sudoers·PAM), **올라갈 때 증명을 요구하나**(비밀번호 재확인), **sudo 를 안 거치는 옆문이 있나**(특권 그룹·소켓).
  우리 노드는 첫째 층은 있었고, 둘째 층은 6대 모두 꺼져 있었고, 셋째 층에서 "비특권" 으로 만든 계정 하나가 사실상 root 였다.
- 리눅스에서 "설치 제한" 은 `apt` 를 막는 것으로 끝나지 않는다. 사용자가 쓸 수 있는 디렉터리에서 바이너리를 **실행**할 수 있으면 설치는 필요 없다.
  그래서 진짜 통제 대상은 설치가 아니라 **실행**이고, 그건 PAM 이 아니라 애플리케이션 허용목록(allowlisting)의 영역이다.

## 1. 층 하나 — 누가 관리자 권한에 올라갈 수 있나

리눅스에서 관리자 권한을 얻는 정문은 둘이다. `sudo` 와 `su`.

`sudo` 의 권한은 sudoers 정책이 정한다. 공식 매뉴얼은 sudoers 를 "default sudo security policy plugin" 이라 부르고,
누가 어떤 명령을 누구 권한으로 실행할 수 있는지를 이 파일(또는 `/etc/sudoers.d/`)이 정한다고 설명한다 ([sudoers(5)](https://www.sudo.ws/docs/man/sudoers.man/)).

`su` 는 PAM 스택(`/etc/pam.d/su`)을 탄다. 여기서 쓰는 전통적 통제가 `pam_wheel` 이다.
매뉴얼 요약 그대로 "Only permit root access to members of group wheel" — 지정한 그룹에 속한 사람만 root 로 `su` 할 수 있게 한다 ([pam_wheel(8)](https://man7.org/linux/man-pages/man8/pam_wheel.8.html)).

**실측**

| 항목 | 결과 |
| --- | --- |
| sudoers 에 사람 관리자 계정 1개가 등록 | 6대 중 6대 |
| 위와 별개로, 설치 시 기본 계정용 sudo 규칙이 남아 있음 | 6대 중 1대 |
| root 계정 비밀번호 잠김(`passwd -S` 상태 L) | 6대 중 5대 (1대는 비밀번호가 설정된 상태) |
| `su` 에 `pam_wheel` 적용 | 6대 중 0대 |

`pam_wheel` 은 한 대에서 확인해 보니 배포판 기본 `/etc/pam.d/su` 에 **주석 처리된 예시 줄로만** 들어 있었다.
root 비밀번호가 잠겨 있으면 `su` 로 root 가 될 길이 원래 막혀 있으므로 5대에선 실해가 작다.
문제는 root 비밀번호가 살아 있는 1대다. 거기선 root 비밀번호를 아는 누구든, 어떤 그룹이든 `su` 할 수 있다.

## 2. 층 둘 — 올라갈 때 증명을 요구하나

sudoers 매뉴얼의 기본 동작은 "most users authenticate themselves before they can use `sudo`" 다.
단 예외가 명시돼 있다 — 호출자가 root 이거나, 대상이 자기 자신이거나, **정책이 그 사용자나 명령에 대해 인증을 끈 경우** ([sudoers(5), User Authentication](https://www.sudo.ws/docs/man/sudoers.man/)).
세 번째가 `NOPASSWD` 태그다.

MITRE ATT&CK 는 이 설정을 권한 상승 기법의 한 갈래로 올려 두었다. `user1 ALL=(ALL) NOPASSWD: ALL` 같은 줄을 예로 들며,
공격자가 이런 느슨한 설정을 악용해 사용자 비밀번호 없이 권한을 올릴 수 있다고 적는다 ([T1548.003 Sudo and Sudo Caching](https://attack.mitre.org/techniques/T1548/003/)).

**실측**

| 항목 | 결과 |
| --- | --- |
| 사람 관리자 계정의 sudo 규칙이 `NOPASSWD: ALL` | 6대 중 6대 |
| 기본 계정용으로 남은 규칙도 `NOPASSWD: ALL` | 해당 1대 |
| 로그인 실패 잠금(`pam_faillock`) 적용 | 6대 중 0대 |
| 비밀번호 품질 검사(`pam_pwquality`) 적용 | 6대 중 4대 |

이 표에서 읽어야 할 건 개별 줄이 아니라 줄 사이의 관계다.
`NOPASSWD: ALL` 이면 sudo 는 비밀번호를 묻지 않는다. 그러면 비밀번호 품질 검사(4대)도, 실패 잠금([pam_faillock(8)](https://man7.org/linux/man-pages/man8/pam_faillock.8.html), 0대)도 **sudo 경로에서는 작동할 기회가 없다.**
결국 우리 노드에서 "관리자 세션" 과 "root" 사이에는 두 번째 요소가 없다. SSH 키 하나가 곧 root 다.

이게 곧바로 잘못이라는 뜻은 아니다. SSH 가 키 전용이고 자동화 도구가 sudo 를 쓰는 환경이라면 `NOPASSWD` 는 흔한 절충이다.
다만 그 절충을 했다면 "관리자 권한 사용 제한" 이라는 통제는 **SSH 키 관리로 이동한 것**이고, 점검표에 PAM 항목으로 초록불을 켜선 안 된다.
([앞 글](/2026/09/24/server-hardening-audit-effective-state-6-nodes/)에서 쟀듯 우리 노드는 그 SSH 쪽도 비밀번호 인증이 실효값 기준 켜져 있었다. 두 약점이 겹친다.)

**기록은 남는가.** sudoers 는 기본으로 성공·실패 시도를 모두 syslog 로 남긴다 ([sudoers(5), Logging](https://www.sudo.ws/docs/man/sudoers.man/)).
실측에서도 6대 모두 journal 에 sudo 기록이 쌓이고 있었다. 하지만 이건 "무슨 명령을 실행했나" 까지다.
`sudo -i` 로 root 셸을 연 뒤 그 안에서 무엇을 했는지는 명령 한 줄로만 남는다. 세션 내용을 남기는 sudo I/O 로깅(`log_output`)은 **6대 중 0대**였다.

## 3. 층 셋 — sudo 를 안 거치는 옆문

sudoers 를 아무리 잘 써도, sudo 를 거치지 않고 root 와 같은 일을 할 수 있는 경로가 있으면 소용없다. 가장 흔한 게 `docker` 그룹이다.

Docker 공식 설치 후속 문서는 경고 상자로 이렇게 못 박는다 — "The `docker` group grants root-level privileges to the user"
([Docker, Linux post-installation steps](https://docs.docker.com/engine/install/linux-postinstall/)).
Docker 데몬은 root 로 돌고, 그 소켓에 쓸 수 있는 사용자는 호스트 파일시스템을 마운트한 컨테이너를 띄울 수 있기 때문이다.

**실측**

| 항목 | 결과 |
| --- | --- |
| `docker.sock` 소유 `root:docker`, 모드 660 | 6대 중 6대 |
| 사람 관리자 계정이 `docker` 그룹 소속 | 6대 중 6대 |
| **sudo 권한이 없는(`sudo -l` 에 허용 명령 0개) CI 러너 계정이 `docker` 그룹 소속** | **6대 중 1대** |

마지막 줄이 이번 점검에서 가장 중요한 발견이다. 그 계정은 일부러 "비특권" 으로 만들었고, 실제로 sudo 권한은 하나도 없다.
sudoers 만 보는 점검에선 모범 사례로 통과한다. 그런데 `docker` 그룹 소속이라는 한 줄 때문에 Docker 문서 기준으로 root 급 권한을 갖는다.
해당 노드에선 지금 러너 서비스가 돌고 있지 않았지만, 계정과 그룹 소속은 그대로 남아 있었다.
CI 러너는 남이 올린 코드를 실행하는 프로세스다. 권한 경계가 가장 단단해야 할 계정이 가장 조용하게 경계를 넘어 있던 셈이다.

반대로 K3s 의 containerd 소켓은 6대 모두 `root:root` 660 이었다. 같은 "컨테이너 런타임 소켓" 이라도 그룹을 열어 두었느냐에 따라 결과가 갈린다.

교훈은 한 줄이다. **권한 점검은 sudoers 를 읽는 게 아니라 "이 계정이 root 와 같은 일을 할 수 있는 모든 경로" 를 세는 것이다.**
`docker`, `lxd`, `disk` 같은 그룹 소속과 root 소유 소켓의 그룹 권한은 sudoers 에 한 글자도 나타나지 않는다.

## 4. "프로그램 설치 제한" 은 실행 제한이다

"허가되지 않은 프로그램 설치를 막는다" 를 리눅스로 옮기면 흔히 "일반 사용자는 `apt` 를 못 쓴다" 가 된다. 그건 sudo 가 이미 해 준다.
하지만 설치 없이도 프로그램은 돈다. 홈 디렉터리나 `/tmp` 에 바이너리나 스크립트를 내려받아 실행 권한만 주면 된다. 패키지 관리자는 이 경로를 모른다.

그래서 이 통제의 실체는 **무엇이 실행될 수 있는가** 다. NIST 는 이것을 애플리케이션 허용목록(application whitelisting)으로 정의한다 —
허가된 애플리케이션과 구성요소의 목록을 두고 그 목록에 있는 것만 실행되게 해 악성코드·무허가 소프트웨어 실행을 막는다
([NIST SP 800-167, Guide to Application Whitelisting](https://csrc.nist.gov/pubs/sp/800/167/final)).

리눅스에서 이걸 하는 수단은 대략 세 층이다.

1. **마운트 옵션.** 사용자가 쓸 수 있는 파일시스템(`/tmp`, `/home`, `/dev/shm`)을 `noexec` 로 마운트한다. 가장 싸지만 인터프리터(`python3 script.py`, `bash script.sh`)를 통한 실행은 막지 못한다.
2. **MAC(강제 접근 통제).** AppArmor·SELinux 는 프로그램별로 무엇에 접근할 수 있는지를 제한한다. 이미 있는 프로그램을 가두는 도구지, "목록에 없는 새 프로그램은 실행 불가" 를 기본으로 하는 도구는 아니다.
3. **실행 허용목록 데몬.** `fapolicyd` 는 스스로를 "a simple application whitelisting daemon for Linux" 라 소개한다.
   기본 정책의 목표로 "Anything requesting execution must be trusted" 를 들고, `ld.so` 로 바이너리를 직접 불러 우회하는 경로까지 막도록 설계됐다
   ([fapolicyd README](https://github.com/linux-application-whitelisting/fapolicyd)).

**실측**

| 항목 | 결과 |
| --- | --- |
| `/tmp`·`/home`·`/dev/shm` 중 `noexec` 가 붙은 마운트 | 6대 중 0대 |
| (참고) `/tmp` 가 별도 tmpfs 로 분리돼 있음 | 6대 중 4대 — 단 옵션은 `nosuid,nodev` 뿐 |
| AppArmor 활성, enforce 프로파일 존재 | 6대 중 6대 |
| `fapolicyd` 등 실행 허용목록 데몬 가동 | 6대 중 0대 |

여기서 하나 걸려 넘어질 뻔했다. `findmnt -O noexec` 로 거르면 `/tmp`·`/dev/shm` 이 목록에 나온다. 그런데 각 마운트의 옵션을 직접 찍어 보면 `noexec` 는 어디에도 없다.
findmnt 매뉴얼을 보면 `-O` 는 앞의 `no` 를 부정으로 해석하고, 그 해석을 끄려면 `+` 를 붙이라고 한다. 즉 `-O noexec` 는 "`exec` 옵션이 명시되지 않은 마운트" 를 고른 것이고, 문자 그대로 찾으려면 `-O +noexec` 여야 했다.
걸러 주는 명령의 결과를 믿지 말고 **옵션 문자열 자체를 읽어야** 한다 — [앞 글](/2026/09/24/server-hardening-audit-effective-state-6-nodes/)의 "실효값을 읽어라" 와 같은 교훈이다.
그리고 `/tmp` 를 분리해 `nosuid,nodev` 를 붙여 둔 4대도, 실행 차단에 해당하는 `noexec` 는 빠져 있었다.

즉 우리 노드는 "기존 프로그램을 가두는" 층(AppArmor)은 있지만, "목록에 없는 프로그램이 도는 것" 자체를 막는 층은 없다.
관리자 계정이 아닌 사용자도 자기 홈에 받은 바이너리를 실행할 수 있다. 설치 제한은 **패키지 관리자 수준에서만** 존재한다.

솔직히 말하면 쿠버네티스 노드에 `fapolicyd` 를 까는 건 공짜가 아니다. 컨테이너 런타임이 수시로 새 이미지 레이어의 바이너리를 실행하므로 정책을 잘못 짜면 노드가 멈춘다.
fapolicyd README 도 새 정책은 permissive 모드로 먼저 돌려 보라고 권하고, 잘못하면 시스템이 교착될 수 있다고 경고한다.
그래서 여기서의 요점은 "당장 깔아라" 가 아니라, **"설치 제한" 항목에 초록불을 켜려면 무엇으로 실행을 막고 있는지 한 줄로 댈 수 있어야 한다** 는 것이다.

## 5. 점검표를 다시 쓴다면

"PAM/계정통제" 를 한 줄짜리 체크 항목으로 두지 말고, 아래 질문으로 쪼개면 우리 같은 빈 곳이 바로 드러난다.

| 질문 | 확인하는 것 | 근거 |
| --- | --- | --- |
| 누가 root 가 될 수 있나? | sudoers + `/etc/sudoers.d/*` 전체, `su` 의 `pam_wheel`, root 비밀번호 상태 | [sudoers(5)](https://www.sudo.ws/docs/man/sudoers.man/), [pam_wheel(8)](https://man7.org/linux/man-pages/man8/pam_wheel.8.html) |
| 올라갈 때 증명을 요구하나? | `NOPASSWD` 유무, 있다면 그 대가를 어디서 치르나(SSH 키 전용·MFA) | [MITRE T1548.003](https://attack.mitre.org/techniques/T1548/003/) |
| 무엇을 했는지 남나? | sudo 명령 기록 + 세션 I/O 로깅 여부 | [sudoers(5)](https://www.sudo.ws/docs/man/sudoers.man/) |
| sudo 를 안 거치는 길은? | `docker` 등 특권 그룹 소속, root 소유 소켓의 그룹 권한 | [Docker docs](https://docs.docker.com/engine/install/linux-postinstall/) |
| 목록에 없는 프로그램이 도나? | `noexec` 마운트, 실행 허용목록(fapolicyd 등) | [NIST SP 800-167](https://csrc.nist.gov/pubs/sp/800/167/final), [fapolicyd](https://github.com/linux-application-whitelisting/fapolicyd) |

이 중 셋째 층(옆문)은 도구가 알아서 잡아 주지 않는다. sudoers 린터도, PAM 설정 검사기도 `docker` 그룹을 보지 않는다.
우리 점검에서 가장 무거운 발견이 바로 거기서 나왔다는 게 이 글의 요지다.

## 한계

- 표본은 홈랩 노드 6대이고 모두 같은 계열 배포판이다. 다른 배포판(예: `wheel` 그룹이 기본 활성인 계열)에선 기본값이 다르다.
- 실측은 2026-09-24 한 시점의 읽기 전용 스냅숏이다. LDAP·SSSD 같은 중앙 계정 관리는 이 노드들에 없어 다루지 않았다.
- `pam_wheel` 이 주석으로만 있다는 건 1대에서 파일을 직접 보고 확인했다. 나머지는 "적용된 줄이 없다" 까지만 확인했다.
- 이 글은 발견을 공개할 뿐 고치지 않았다. 설정 변경(sudoers·그룹 소속 정리)은 별도로 결정할 일이다.

## References

- sudo project, [sudoers(5) manual](https://www.sudo.ws/docs/man/sudoers.man/) — User Authentication, Logging
- Linux-PAM, [pam_wheel(8)](https://man7.org/linux/man-pages/man8/pam_wheel.8.html)
- Linux-PAM, [pam_faillock(8)](https://man7.org/linux/man-pages/man8/pam_faillock.8.html)
- MITRE ATT&CK, [T1548.003 Abuse Elevation Control Mechanism: Sudo and Sudo Caching](https://attack.mitre.org/techniques/T1548/003/)
- Docker Docs, [Linux post-installation steps for Docker Engine](https://docs.docker.com/engine/install/linux-postinstall/) — "The docker group grants root-level privileges"
- Sedgewick, Souppaya, Scarfone, [NIST SP 800-167: Guide to Application Whitelisting](https://csrc.nist.gov/pubs/sp/800/167/final) (2015)
- [fapolicyd — File Access Policy Daemon](https://github.com/linux-application-whitelisting/fapolicyd)
