---
layout: post
title: "Cursor 마켓플레이스의 가짜 Claude Code 확장 — 지워도 남는 SSH 백도어, 그리고 내 맥 점검 기록"
date: 2026-11-04 01:31:45 +0900
categories: [security, supply-chain]
tags: [supply-chain, cursor, claude-code, vscode-extension, ssh, incident-response]
---

2026년 10월 29일, Cursor 마켓플레이스에 Claude Code 확장의 변조본이 약 11시간 동안 올라가 있었습니다. 이 확장을 설치하면 사용자 계정에 공격자의 SSH 키를 심고, 공격자 서버로 역방향 터널을 열려고 시도했습니다. 텔레그램으로 이 소식이 "VS Code 용 Claude Code 공식 익스텐션이 털렸다"는 문장으로 들어왔는데, 1차 출처를 확인해 보니 **범위가 그것보다 좁고, 대응은 그것보다 한 단계 더 필요했습니다.** 이 글은 확인된 사실과, 그 기준으로 제 맥을 점검한 결과를 정리합니다.

## 한 줄 요약

- **영향 범위:** Cursor 의 VS Code 확장 마켓플레이스에서 받은 `anthropic.claude-code` **2.1.312·2.1.313** (macOS·Windows)입니다. 노출 시간은 10/29 02:27~13:35 PT, 한국 시간으로 10/29 18:27 ~ 10/30 05:35 입니다. ([Cursor 공지](https://cursor.com/blog/claude-code-extension-security-notice))
- **영향 없음:** Microsoft VS Code 마켓플레이스, Open VSX, npm `@anthropic-ai/claude-code` CLI 입니다. ([Microsoft 보안블로그](https://www.microsoft.com/en-us/security/blog/2026/10/30/inside-malicious-claude-code-branded-cursor-extension-persistent-ssh-backdoor/))
- **핵심:** **확장을 지우는 것만으로는 부족합니다.** 페이로드가 확장과 별개로 실행되는 지속성 스크립트를 따로 심기 때문입니다. Cursor 공지가 직접 이렇게 적었습니다: *"Uninstalling the extension may not be sufficient."*

## "VS Code 공식 확장" 이 아니라 "Cursor 마켓플레이스" 다

처음 퍼진 정보에는 혼선이 있었습니다. 최초로 분석을 공개한 [OpenSourceMalware](https://opensourcemalware.com/blog/trojanized-claude-code-extension-plants-persistent-ssh-backdoor) 는 처음에 Open VSX 를 감염 경로로 지목했습니다. 그런데 Open VSX, npm, VS Code 마켓플레이스 모두 2.1.312 다음 버전이 2.1.314 로 건너뛰어 있었습니다. 그래서 "악성 버전이 레지스트리마다 내려졌다"는 추측이 붙었습니다. 이후 OpenSourceMalware 는 글을 고쳐, 출처가 Open VSX 가 아니라 **Cursor 가 운영하는 미러 겸 자체 마켓플레이스**였다고 정정했습니다.

버전이 건너뛴 이유는 Anthropic 쪽에서 직접 설명했습니다. Anthropic 의 Felix Rieseberg 는 X 에서 *"Anthropic 의 시스템이나 직원 노트북이 침해된 것이 아니다. 공격자가 Cursor 마켓플레이스 접근권으로 우리가 빌드·배포하지 않은 변조본을 올렸다"*고 밝혔습니다([WIRED 인용](https://www.wired.com/story/trojan-malware-targets-thousands-of-anthropic-claude-developer-systems/)). Anthropic 은 혼동을 피하려고 정상 확장을 곧바로 2.1.314 로 올렸습니다([SecurityWeek](https://www.securityweek.com/malicious-claude-code-extension-served-in-cursor-supply-chain-attack/)). 즉 **2.1.313 은 공식 채널에 존재한 적이 없는 번호**이고, 2.1.312 는 Open VSX 에 있는 것과 Cursor 에 있던 것이 서로 다른 파일입니다.

아직 풀리지 않은 질문도 있습니다. 보안업체 Phorion 의 CTO 는 변조본이 **Cursor 상의 Anthropic 공식 계정**으로 배포됐다고 말했습니다([Ars Technica](https://arstechnica.com/security/2026/10/anthropic-vs-code-extension-on-cursor-backdoored-for-nearly-12-hours/)). 하지만 공격자가 그 계정 권한을 어떻게 얻었는지는 글을 쓰는 시점(11/4)까지 Cursor 도 Anthropic 도 공개하지 않았습니다. Cursor 가 마켓플레이스 전체를 내리고, 키를 교체하고, 다시 빌드한 것으로 보아 단일 확장 문제가 아니었을 가능성을 지적하는 분석도 있지만(OpenSourceMalware), 이것은 **추정**입니다.

영향을 받은 사용자 수는 Cursor 가 X 에서 *"at most 5,000 users"* 라고 밝혔습니다([The Next Web 인용](https://thenextweb.com/news/tampered-claude-code-extension-cursor-ssh-backdoor)). 이 숫자를 독립적으로 검증한 제3자 자료는 찾지 못했습니다.

## 악성 코드는 무엇을 했나

Cursor 공지와 Microsoft 분석이 일치하는 부분만 적습니다.

1. **실행 시점.** `extension.js` 맨 앞에 66줄짜리 로더가 붙어 있었습니다. 확장 모듈이 **로드되기만 하면** 실행됩니다. 대화를 시작할 필요도 없고, npm 의 `postinstall` 같은 설치 훅도 쓰지 않습니다.
2. **정찰.** 호스트명·사용자명·OS·아키텍처·홈 경로·작업 디렉터리·`git config --global user.email`·공인 IP 를 모읍니다. 환경변수는 `KEY`·`TOKEN`·`SECRET`·`PASS`·`AWS`·`GCP` 가 들어간 **이름**을 최대 40개 모읍니다. 처음 보내는 비컨에는 값이 아니라 이름만 들어갑니다. 수집한 내용은 평문 HTTP 로 `134.209.82[.]225:8099/beacon` 에 POST 합니다.
3. **백도어 키.** `~/.ssh/authorized_keys` 에 `svc-telemetry` 라는 주석이 달린 Ed25519 공개키를 추가합니다.
4. **SSH 서비스 켜기 시도.** macOS 에서는 `sudo -n systemsetup -setremotelogin on` 을 실행합니다. Cursor 는 관리자 권한이 없는 일반적인 환경이라면 코드의 오류 때문에 **이 단계는 대개 실패했다**고 설명합니다.
5. **역방향 터널.** `tunnel@134.209.82[.]225` 로 `-R '*:0:localhost:22'` 터널을 열고, 60초마다 재시도합니다.
6. **지속성.** macOS 에서는 `~/Library/LaunchAgents/com.apple.sysmond.plist` 와 `~/.config/.smt`·`.smtk` 를 만듭니다. Windows 에서는 `SysMon` 예약 작업을 만들고, 실패하면 시작프로그램 폴더의 `sysmon.cmd` 로 대신합니다. 이름에 `com.apple` 이 들어가 있지만 **애플 구성요소가 아닙니다.**

Cursor 는 공격자 서버를 호스팅 업체와 협력해 내렸다고 밝혔습니다. 그래서 지금은 터널과 비컨이 동작하지 않습니다. 그렇다고 이미 심어진 키와 스크립트가 사라지는 것은 아닙니다.

## 처음 받은 대응 가이드와 다른 점

텔레그램으로 받은 대응 가이드는 "네트워크 차단 → 버전 확인 → 언인스톨" 이었습니다. 1차 출처 기준으로 고치면 이렇습니다.

| 받은 가이드 | 1차 출처 기준 |
| --- | --- |
| VS Code 공식 확장 | **Cursor 마켓플레이스**에서 받은 경우만 해당 |
| v2.1.313 | **2.1.312 와 2.1.313** 둘 다 (10/30 Cursor 공지 개정) |
| 언인스톨 | 언인스톨로는 **부족**. 키·LaunchAgent·스크립트·터널 프로세스를 따로 지우고, 그 호스트에서 접근 가능했던 자격증명을 **다른 신뢰할 수 있는 기기에서** 교체 |

Microsoft 는 지우기 **전에** 증거를 보존하라고 권고합니다. 확장 패키지, 변조된 `authorized_keys`, 생성된 키와 스크립트를 먼저 확보하라는 것입니다. 또 `svc-telemetry` 마커가 없다는 사실 하나로 안전하다고 판정하지 말라고도 적었습니다.

## 내 맥 점검 기록 (2026-11-04)

Cursor 공지의 확인 명령과 Microsoft 가 정리한 지속성 경로를 그대로 따라 실행했습니다.

```bash
# 1) 확장 설치 여부 — Cursor/VS Code 확장 폴더
find ~ -maxdepth 4 -type d -name 'anthropic.claude-code*'
ls -d /Applications/Cursor.app ~/.cursor

# 2) 공격자 키 (Cursor 공지의 확인 명령)
grep -qs svc-telemetry ~/.ssh/authorized_keys && echo "svc-telemetry key found" || echo "No key found"

# 3) 지속성 산출물
ls -la ~/Library/LaunchAgents/com.apple.sysmond.plist ~/.config/.smt ~/.config/.smtk

# 4) 터널 프로세스
pgrep -fl '134.209.82.225'
```

결과는 다음과 같습니다.

- Cursor 와 VS Code 가 설치돼 있지 않았고, `anthropic.claude-code` 확장 폴더도 없었습니다. 이 맥에서는 Claude Code 를 터미널 CLI 로만 씁니다. CLI(npm 배포본)는 이번 사건과 무관합니다.
- `svc-telemetry` 키가 없었습니다.
- `com.apple.sysmond.plist`, `.smt`, `.smtk` 파일이 없었습니다.
- 터널 프로세스가 없었습니다.

즉 **노출 경로 자체가 없었습니다.** 마커가 없다는 사실만으로 판정한 것이 아니라, 확장을 받을 수 있는 경로(Cursor)가 처음부터 없었다는 점이 근거입니다. 클러스터 노드들은 다른 커널 취약점 때문에 10/29 밤부터 꺼져 있어서 점검 대상에서 뺐습니다. 다시 켤 때 리눅스용 지속성 경로(`crontab -l` 의 `@reboot` 항목과 `~/.config/.smt`)도 같이 확인할 예정입니다.

## 남는 교훈

- **확장은 IDE 권한으로 돌아갑니다.** 확장은 별도로 격리되지 않아서, 로드되는 순간 사용자 계정으로 파일을 쓰고 명령을 실행합니다. 이번 로더는 "대화를 시작할 때" 가 아니라 "모듈이 로드될 때" 실행됐습니다.
- **자동 업데이트가 배포 속도를 결정합니다.** Phorion 의 설명대로 Cursor 는 확장 자동 업데이트가 기본으로 켜져 있었습니다. 5,000명이라는 숫자는 사용자가 클릭해서 생긴 것이 아니라 대부분 자동 업데이트에서 생겼을 가능성이 큽니다. Microsoft 는 승인된 게시자만 허용하는 설정과, 새로 게시된 버전의 설치를 늦추는 **설치 유예(cooldown)** 를 권고합니다.
- **게시자 이름은 증명이 아닙니다.** 매니페스트에 `"publisher": "Anthropic"` 이라고 적혀 있다고 해서 Anthropic 이 배포했다는 뜻은 아닙니다. 남의 이름으로 소프트웨어를 배포하는 마켓플레이스가 그 게시자를 인증할 책임을 진다는 OpenSourceMalware 의 지적은 이번 사건에서 가장 오래 남을 질문입니다.

## 침해 지표 (IOC)

Cursor 공지 10/30 개정판 기준입니다. 주소는 일부러 무력화해서 적었습니다.

- 공격자 엔드포인트: `134[.]209[.]82[.]225` (SSH 22, HTTP 8099 `/beacon`)
- SSH 키 주석: `svc-telemetry`, 지문 `SHA256:0Z6R+DF64Do2nwQic8a7kkfDLNNk4IiK+2U2Rci4htk` ([OpenSourceMalware](https://opensourcemalware.com/blog/trojanized-claude-code-extension-plants-persistent-ssh-backdoor))
- 변조된 `extension.js` SHA-256: `ecb58cb29078d9646ad1dcdbe51526f2d9cfea06be5fb2ab183e8ecc3ab6bf15`
- macOS 지속성: `~/Library/LaunchAgents/com.apple.sysmond.plist`, `~/.config/.smt`, `~/.config/.smtk`, 임시 키 `.stk_*`
- 버전별 VSIX 해시는 [Cursor 공지](https://cursor.com/blog/claude-code-extension-security-notice)에 나와 있습니다. 공지에 해시가 실린 빌드는 **darwin-arm64 와 win32-x64 두 가지뿐**입니다. Intel 맥과 리눅스 빌드는 해시 목록에 없습니다. 다만 Microsoft 분석과 Cursor 의 IOC 에는 리눅스용 지속성 경로(`@reboot` cron)가 들어 있으니, 리눅스라고 점검을 건너뛰지는 마세요.

감염 흔적이 있다면 Cursor 가 배포한 정리 스크립트(`remediate-macos.sh` / `remediate-windows.ps1`)를 쓰면 됩니다. 이 스크립트는 남은 것이 있으면 0이 아닌 종료코드를 돌려줍니다. 그다음 Cursor 공지의 5단계(자격증명·세션 교체)까지 진행해야 합니다.

## References

1. Cursor, "Security notice — malicious version of Anthropic.claude-code (2.1.312 and 2.1.313) identified in the Cursor VS Code Extension Marketplace", 2026-10-29 (10-30 개정). <https://cursor.com/blog/claude-code-extension-security-notice> — 1차·공식
2. Microsoft Threat Intelligence, "Inside a malicious Claude Code-branded extension and its persistent SSH backdoor", 2026-10-30. <https://www.microsoft.com/en-us/security/blog/2026/10/30/inside-malicious-claude-code-branded-cursor-extension-persistent-ssh-backdoor/> — 제3자 분석, 영향 범위 확인
3. OpenSourceMalware, "Trojanized Claude Code Extension Plants an SSH Backdoor", 2026-10-30. <https://opensourcemalware.com/blog/trojanized-claude-code-extension-plants-persistent-ssh-backdoor> — 최초 분석. 처음 Open VSX 로 지목한 부분은 본문에서 정정됨
4. StepSecurity, "Trojanized Claude Code Extension Delivered Persistent SSH Backdoor to Developer Machines", 2026-10-30. <https://www.stepsecurity.io/blog/claude-code-extension-trojanized>
5. Lily Hay Newman, "A Supply Chain Attack Put Malicious Anthropic Claude Extensions on Thousands of Devices", WIRED, 2026-10-30. <https://www.wired.com/story/trojan-malware-targets-thousands-of-anthropic-claude-developer-systems/> — Anthropic(Felix Rieseberg) 발언 인용
6. Dan Goodin, "Anthropic VS code extension on Cursor backdoored for nearly 12 hours", Ars Technica, 2026-10-30. <https://arstechnica.com/security/2026/10/anthropic-vs-code-extension-on-cursor-backdoored-for-nearly-12-hours/> — Phorion CTO 발언
7. Ionut Arghire, "Malicious Claude Code Extension Served in Cursor Supply Chain Attack", SecurityWeek, 2026-11-02. <https://www.securityweek.com/malicious-claude-code-extension-served-in-cursor-supply-chain-attack/>
8. Ana Maria Constantin, "Anthropic denies breach as tampered Claude Code extension hits Cursor users", The Next Web, 2026-10-31. <https://thenextweb.com/news/tampered-claude-code-extension-cursor-ssh-backdoor> — Cursor 의 "at most 5,000 users" 게시 인용
