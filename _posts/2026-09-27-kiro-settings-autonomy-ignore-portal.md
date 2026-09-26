---
layout: post
title: "Kiro 설정 화면 한 장 뜯어보기 — Autopilot, 무시 파일, 코드 레퍼런스, 그리고 포털 호스트"
date: 2026-09-27 02:20:00 +0900
categories: [AI, engineering]
tags: [kiro, aws, agentic-ide, harness, settings, permissions, kiroignore, security]
---

![Kiro 설정 화면 — Agent Focus Portal: Public Hosts, Startup Mode, Agent Autonomy(Autopilot), Agent Ignore Files, Code References: Reference Tracker](/assets/images/kiro-settings-screen.jpg)

AWS 의 에이전트형 IDE **Kiro** 에서 `Settings → User → Kiro` 를 열면 위 화면이 나온다. 공식 소개는 "AI 에이전트의 도움으로 실제 엔지니어링 작업을 쉽게 내보내게 하는 **에이전트형 개발 환경**"이고, "AWS 안의 작고 확고한 팀이 만들고 운영한다"([About](https://kiro.dev/about/)).

화면에 보이는 설정은 다섯 개다. 겉보기엔 UI 취향 설정 같지만, 하나씩 보면 **에이전트가 무엇을 읽고, 언제 묻고, 누가 조종할 수 있는지**를 정하는 하네스 설정이다. 위에서부터 차례로 보되, 실무에서 중요한 순서로 재배열했다.

> 기준: Kiro 공식 문서, 2026-09-27 조회. 화면 속 두 항목(Startup Mode, Agent Focus Portal: Public Hosts)은 공식 문서에서 설명을 찾지 못했다. 그래서 **화면에 적힌 설명문**을 1 차 자료로 삼았고, 해당 부분에 따로 표시했다.

---

## 1. Agent Autonomy — `Autopilot` 은 기본값이다

화면의 드롭다운은 `Autopilot` 이다. [공식 문서](https://kiro.dev/docs/ide/chat/autopilot/)에 따르면 이것이 **기본값**이다. 설정 키는 `kiroAgent.agentAutonomy` 다.

| 모드 | 동작 |
|---|---|
| **Autopilot** (기본) | 단계마다 승인 없이 파일 생성, 여러 위치의 코드 수정, **명령 실행**, 구조적 결정까지 한다 |
| **Supervised** | 파일 수정이 포함된 턴마다 멈추고 승인을 기다린다. 변경은 hunk 단위로 Accept / Reject 하거나 파일 단위, Accept All / Reject All 로 처리한다 |

되돌리는 방법도 두 층이다.

- **Revert**: **마지막 턴**의 파일 변경만 되돌린다.
- **체크포인트 복원**: 프롬프트를 보낼 때마다 [체크포인트](https://kiro.dev/docs/checkpoints/)가 생긴다. 복원하면 코드와 **Kiro 의 컨텍스트**를 함께 그 시점으로 돌린다.

여기서 문서가 직접 박아 둔 경고 두 개가 이 설정의 핵심이다.

1. **"Supervised 모드는 코드 리뷰 워크플로이지 보안 통제가 아니다."**([Privacy and security](https://kiro.dev/docs/privacy-and-security/)) Supervised 에서 Reject 하면 파일은 돌아간다. 하지만 그 턴에 이미 실행된 명령까지 돌아가지는 않는다.
2. **"Kiro 는 자신이 실행한 MCP 도구나 bash 명령이 만든 파일 변경을 추적하지 않는다."**([Checkpoints](https://kiro.dev/docs/checkpoints/)) 체크포인트로 되돌려도 스크립트가 지운 파일, 명령이 바꾼 DB 는 그대로다.

그래서 실제 안전장치는 이 드롭다운이 아니라 IDE 1.0 에서 들어온 **권한 계층**이다. 문서 표현으로는 "권한 계층은 자율성 모드가 진행 여부를 정한 **뒤에** 적용된다"([Permissions](https://kiro.dev/docs/permissions/)).

- IDE 1.0 은 예전의 **Trusted Commands / Command Denylist** 를 `permissions.yaml` 셸 규칙으로 대체했다([What's new in 1.0](https://kiro.dev/docs/ide/whats-new-v1/)).
- 규칙의 우선순위는 **deny > ask > allow** 다.
- 기본값은 이렇다. 워크스페이스 읽기, 읽기 전용 git, 시스템 정보 명령은 허용하고 **나머지는 전부 승인을 묻는다.**
- `.git/`, `.vscode/`, `mcp.json`, `.kiroignore` 같은 **보호 경로**는 쓰기 전에 항상 묻는다.
- 파일 위치는 사용자 규칙이 `~/.kiro/settings/permissions.yaml` 이고, 워크스페이스 규칙은 **리포 밖** `~/.kiro/workspace-roots/<hash>/permissions.yaml` 에 저장된다. 에이전트가 리포 안 파일을 고쳐 자기 권한을 넓히는 경로가 막혀 있다는 뜻이다.

**권장**: Autopilot 을 쓰려면 먼저 `permissions.yaml` 에서 위험한 명령(`rm -rf`, `git push`, `kubectl delete`, 배포 스크립트)을 `deny` 나 `ask` 로 명시한다. "자율성은 높게, 권한은 좁게"가 에이전트 하네스의 기본 조합이다.

---

## 2. Agent Ignore Files — 에이전트가 읽지 말아야 할 것

화면 설명: "Kiro Agent 가 워크스페이스 파일을 읽을 때 존중할 무시 패턴 파일. 예: `.gitignore`". 설정 키는 `kiroAgent.agentIgnoreFiles` 이고, 기본 제공되는 전용 파일이 [`.kiroignore`](https://kiro.dev/docs/kiroignore/)다.

- `.kiroignore` 는 gitignore 문법으로 **Kiro 가 특정 파일을 읽지 못하게** 한다.
- 여러 파일을 함께 쓸 수 있다: `[".gitignore", ".kiroignore"]`. `[]` 로 두면 워크스페이스 수준 무시 파일을 끈다.
- 전역 무시 파일 `~/.kiro/settings/kiroignore` 와 git 의 `core.excludesfile` 은 자동으로 적용된다.
- 무시된 파일의 경로와 내용은 **검색 결과에도 나오지 않는다.**
- 지원 범위는 IDE 가 완전 지원이다. CLI v3 는 검색 결과 필터링만 되고, Web 은 지원하지 않는다.

**`.gitignore` 와 `.kiroignore` 는 목적이 다르다.** `.gitignore` 는 "커밋하지 않을 것"이고 `.kiroignore` 는 "**모델에 보내지 않을 것**"이다. `.env`, `*.pem`, `kubeconfig`, 고객 데이터 덤프, 내부 네트워크 구성 문서는 git 에서 이미 빠져 있더라도 로컬 디스크에는 있다. 에이전트는 로컬 디스크를 읽는다. 둘 다 등록해 두는 게 맞다.

```gitignore
# .kiroignore
.env*
*.pem
*.key
**/secrets/**
kubeconfig*
dumps/
```

`.kiroignore` 자체도 보호 경로라서, 에이전트가 이 파일을 고쳐 무시 목록을 푸는 건 항상 승인을 거친다.

---

## 3. Code References: Reference Tracker — 기본은 꺼져 있다

화면의 체크박스 "Allow Kiro to generate code with code references" 는 비어 있다. [공식 문서](https://kiro.dev/docs/privacy-and-security/code-references/)에 따르면 **기본값이 비활성화**다.

- 켜면 Kiro 가 생성한 코드가 공개 코드와 비슷할 때 **출처 정보**를 함께 제공한다. 기록은 Output 탭의 `code-references` 로그에 남는다.
- 화면 설명문에 따르면 끈 상태에서는 **공개 코드와 유사한 생성 자체를 억제**한다. 이 부분은 공식 문서 본문에서는 확인하지 못했고 화면 문구 기준이다.
- 엔터프라이즈 관리자가 조직 전체를 옵트아웃하면 사용자가 되돌릴 수 없다.

라이선스를 신경 쓰는 조직이라면 **꺼 둔 기본값이 보수적인 선택**이다. 오픈소스 코드 조각을 알고 쓰려는 팀이라면 켜 두고 로그를 리뷰 절차에 넣는다.

---

## 4. Startup Mode — `code` vs 에이전트 우선

화면 설명: "Kiro 가 **code-first** 로 시작할지 **agent-first** 로 시작할지 정한다." 값은 `code` 다.

이 설정 자체의 문서는 찾지 못했다. 다만 배경은 확인된다. [IDE 1.0 변경 기록](https://kiro.dev/changelog/ide/1-0/)(2026-06-25)이 **실험 기능 Agent Focus Mode** 를 도입했다. [Focus Mode 문서](https://kiro.dev/docs/ide/experimental/focus-mode/)의 설명은 "전통적 레이아웃을 뒤집어 **대화가 메인 패널**을 차지하고 세션들이 왼쪽에 늘어선다"이다. 병렬 에이전트 세션을 지휘하는 화면이다. 발표 블로그는 "IDE 가 여전히 기본값"이라고 적었다. 이 설정은 앱을 열 때 어느 레이아웃으로 시작할지를 고르는 것으로 보인다.

**선택 기준**: 코드를 직접 읽고 고치는 시간이 길면 `code`, 여러 에이전트 세션을 돌려 놓고 결과를 검토하는 흐름이면 agent-first 가 맞다. 실험 기능이라는 점은 감안한다.

---

## 5. Agent Focus Portal: Public Hosts — 보안 설정이다

이 항목은 공식 문서와 변경 기록에서 찾지 못했다. **화면 설명문만으로** 정리한다. 설명이 상당히 구체적이다.

> 로컬 웹 포털이 응답할 추가 호스트 이름. 앞단에 터널이나 리버스 프록시를 둘 때 쓴다(예: `my-portal.example.com`). 포털은 **인식하지 못한 호스트 이름을 전부 거부**하며, 이것이 **악성 웹페이지가 포털을 조종하는 것을 막는** 장치다. 그래서 터널의 호스트 이름은 여기 등록해야 한다. 포트와 전체 URL 은 받아서 호스트 이름으로 줄이고, **와일드카드는 허용하지 않는다.** 포털이 다음에 시작될 때 적용된다. 이름을 등록한다고 포털이 노출되지는 않으며, **페어링은 여전히 필요하다.**

읽어 보면 로컬에서 도는 **에이전트 조종용 웹 포털**이 있고, 그 포털이 `Host` 헤더 허용 목록으로 자신을 지키고 있다. 이것은 **DNS 리바인딩** 류 공격에 대한 표준적인 방어다. 사용자가 방문한 악성 페이지가 자기 도메인을 `127.0.0.1` 로 다시 해석시켜 브라우저 안에서 로컬 서비스에 요청을 보내는 공격인데, 이때 요청의 Host 는 공격자 도메인이 되므로 허용 목록에서 막힌다.

이 설계에서 배울 점이 세 가지 있다.

- **와일드카드 금지.** `*.example.com` 을 허용하면 그 도메인 아래 누군가 만든 서브도메인이 모두 통과한다. 정확한 이름만 받는다.
- **"목록에 넣어도 노출되지 않는다."** 허용 목록은 문을 여는 게 아니라, 이미 열린 터널을 **알아보게** 하는 것이다. 노출 여부는 터널 쪽이 결정한다.
- **페어링은 별도다.** 호스트 이름 검사는 브라우저 기반 공격을 막고, 페어링은 사람 인증을 한다. 두 층을 섞지 않았다.

**권장**: 휴대폰 같은 외부에서 에이전트를 조종할 게 아니라면 **비워 둔다.** 터널을 쓴다면 인증이 붙은 터널(예: 접근 제어가 있는 Zero Trust 터널)을 쓰고, 그 정확한 호스트 이름 하나만 등록한다. 참고로 공식 문서에 있는 원격 조종 경로는 iOS TestFlight 앱으로 **클라우드 세션**을 조종하는 방식이다([Mobile](https://kiro.dev/docs/mobile/)).

---

## 6. 화면 밖이지만 같이 봐야 할 설정

- **텔레메트리와 콘텐츠 수집**: 무료 티어와 개인 구독자는 기본적으로 사용 데이터·오류·지표와 **"서비스 개선을 위한 콘텐츠"**가 수집된다. `Settings → User → Application → Telemetry and Content` 에서 두 체크박스로 끌 수 있고, 엔터프라이즈 사용자는 자동으로 옵트아웃된다([Data protection](https://kiro.dev/docs/privacy-and-security/data-protection/)). 회사 코드를 개인 계정으로 여는 경우라면 **가장 먼저 확인할 항목**이다.
- **Steering**: `.kiro/steering/*.md`(워크스페이스)와 `~/.kiro/steering/`(전역)에 규칙을 둔다. 포함 방식은 front matter 로 `always`(기본) / `fileMatch` / `manual` / `auto` 중 고른다. `AGENTS.md` 도 지원한다([Steering](https://kiro.dev/docs/steering/)).
- **MCP**: `.kiro/settings/mcp.json`(워크스페이스)과 `~/.kiro/settings/mcp.json`(사용자)이 병합되고 워크스페이스가 우선한다. MCP 서버에 넘길 환경 변수는 **Mcp Approved Env Vars** 에 승인해야 한다([MCP configuration](https://kiro.dev/docs/mcp/configuration/)).
- **Hooks**: `.kiro/hooks/<id>.json` 에 `PreToolUse`, `PostToolUse`, `Stop` 같은 이벤트 훅을 건다. 파일 트리거는 **에이전트가 만든 변경에만** 반응한다([Hooks](https://kiro.dev/docs/hooks/)).

---

## 시작 세팅 체크리스트

- [ ] `Telemetry and Content` 에서 콘텐츠 수집 여부를 결정했다
- [ ] `.kiroignore` 를 만들고 `Agent Ignore Files` 에 `.gitignore` 와 함께 등록했다
- [ ] Autopilot 을 쓴다면 `permissions.yaml` 에 파괴적 명령을 `deny` 또는 `ask` 로 넣었다
- [ ] Supervised 는 리뷰 도구지 보안 장치가 아님을 알고 선택했다
- [ ] 명령과 MCP 가 만든 변경은 체크포인트로 안 돌아간다는 걸 알고, git 커밋을 자주 한다
- [ ] Code References 를 조직의 라이선스 정책에 맞게 두었다
- [ ] Agent Focus Portal: Public Hosts 는 쓸 일이 없으면 비워 두었다

---

## References

1. Kiro, *About*. <https://kiro.dev/about/>
2. Kiro Docs, *Autopilot / Supervised*. <https://kiro.dev/docs/ide/chat/autopilot/>
3. Kiro Docs, *Checkpoints*. <https://kiro.dev/docs/checkpoints/>
4. Kiro Docs, *Privacy and security*. <https://kiro.dev/docs/privacy-and-security/>
5. Kiro Docs, *Permissions*. <https://kiro.dev/docs/permissions/>
6. Kiro Docs, *What's new in IDE 1.0*. <https://kiro.dev/docs/ide/whats-new-v1/>
7. Kiro Docs, *.kiroignore*. <https://kiro.dev/docs/kiroignore/>
8. Kiro Docs, *Code references*. <https://kiro.dev/docs/privacy-and-security/code-references/>
9. Kiro Changelog, *IDE 1.0.0 — Agent Focus, Permissions, Custom Agents, and More* (2026-06-25). <https://kiro.dev/changelog/ide/1-0/>
10. Kiro Docs, *Agent Focus Mode (experimental)*. <https://kiro.dev/docs/ide/experimental/focus-mode/>
11. Kiro Docs, *Mobile*. <https://kiro.dev/docs/mobile/>
12. Kiro Docs, *Data protection*. <https://kiro.dev/docs/privacy-and-security/data-protection/>
13. Kiro Docs, *Steering*. <https://kiro.dev/docs/steering/>
14. Kiro Docs, *MCP configuration*. <https://kiro.dev/docs/mcp/configuration/>
15. Kiro Docs, *Hooks*. <https://kiro.dev/docs/hooks/>
