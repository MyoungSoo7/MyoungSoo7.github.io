---
layout: post
title: "Antigravity 설정 화면 한 장 해설 — 에이전트에게 어디까지 맡길 것인가"
date: 2026-09-27 02:29:35 +0900
categories: [AI, Tools]
tags: [Antigravity, Google, AI에이전트, 코딩에이전트, 권한, 샌드박스, 보안설정]
---

![Antigravity Settings → General 화면. Execution(Queued Messages: Queue / Send Immediately), Global Permissions(Security Preset: Default, Tool Permissions), Agent Behavior(Plan Review Policy: Always Ask), Network Permissions(Network Access Rules)](/assets/images/antigravity-settings-general.jpg)

구글의 에이전트형 개발 도구 **Antigravity** 의 `Settings → General` 화면이다. 한 화면에 설정이 다섯 개뿐이지만, 모두 같은 질문에 대한 답이다.

> **에이전트가 사람에게 묻지 않고 어디까지 해도 되는가?**

이 글은 공식 문서([antigravity.google/docs](https://antigravity.google/docs/getting-started))와 [변경 이력](https://antigravity.google/changelog)을 근거로 각 설정을 해설한다. 2026-09-27 에 확인했다. Antigravity 는 업데이트가 잦아서, **화면의 이름과 문서의 이름이 아직 다른 곳이 몇 군데 있다.** 그런 곳은 따로 표시했다.

## 1. Global Permissions → Security Preset — 가장 중요한 한 칸

에이전트가 **터미널 명령을 실행하고 파일을 읽고 쓰는 범위**를 한 번에 정하는 프리셋이다. 변경 이력 2.14.0(2026-09-15)에서 이 영역의 이름이 **"Global Permissions"** 로 바뀌었고, 프로젝트별 설정에서는 "Inherit Global" 로 전역값을 물려받는다.

프리셋의 내용은 **OS 에 따라 다르다.**

### macOS·Linux — 샌드박스 기반

[Permissions 문서](https://antigravity.google/docs/permissions)의 표를 옮기면 이렇다.

| 프리셋 | 샌드박스 | 터미널 명령 | 파일 접근 | MCP·웹 |
|---|---|---|---|---|
| **Default** | 켜짐 | 샌드박스 안에서는 허용, 밖은 물어봄 | 워크스페이스 + 임시 디렉토리 | 물어봄 |
| **Request Review** | 꺼짐 | 항상 물어봄 | 워크스페이스만 | 물어봄 |
| **Turbo** | 꺼짐 | 무제한 허용 | 파일시스템 전체 | 허용 |

[Agent Settings 문서](https://antigravity.google/docs/agent-settings)의 설명은 이렇다.

- Default: *"Commands run without prompting inside the Terminal Sandbox; running outside the sandbox requires approval."*
- Turbo: *"All commands run without prompting with no isolation or restrictions, and the agent has full read and write access to your filesystem."*

### Windows — 샌드박스가 기본이 아님

["Security preset" 이라는 이름](https://antigravity.google/docs/sandbox)이 문서에 그대로 나오는 곳은 Windows 쪽이다.

| 프리셋 | 터미널 | 작업 폴더 밖 파일 접근 |
|---|---|---|
| **Default** | 매번 검토 요청 | 항상 물어봄 |
| **Full machine** | 매번 검토 요청 | 허용 |
| **Turbo mode** | 묻지 않고 진행 | 허용 |

문서에는 *"None of the presets turn the sandbox on."* 이라고 적혀 있다. Windows 에서는 **프리셋만으로 샌드박스가 켜지지 않는다**는 뜻이다. 샌드박스를 켜면 프리셋이 **Custom** 으로 바뀐다.

**권장:** 화면처럼 **Default** 가 무난하다. Turbo 는 이름 그대로 편하지만, 에이전트가 파일시스템 전체에 쓸 수 있게 된다. 프롬프트 인젝션이 섞인 문서나 웹 페이지를 읽은 에이전트가 `rm` 을 물어보지 않고 실행해도 막을 장치가 없다. 쓰더라도 **버려도 되는 VM·컨테이너 안에서만** 쓰는 게 맞다.

## 2. Tool Permissions — 프리셋 위에 얹는 세부 규칙

화면 설명은 *"Modify permissions for file, terminal, and MCP tools."* 다. 옆의 숫자 배지(2)는 현재 등록된 규칙 수로 보인다.

화면의 이 이름은 문서에서 찾지 못했다. 다만 [Permissions 문서](https://antigravity.google/docs/permissions)의 **allow / ask / deny 규칙**이 바로 이 내용이다.

- 모든 행동은 `행동(대상)` 형태로 표현된다. `read_file`, `write_file`, `read_url`, `execute_url`, `command`, `mcp` 가 있다.
- 우선순위는 **Deny > Ask > Allow** 다.
- 그리고 중요한 한 줄이 있다. *"Your configured allow/deny/ask rules are layered on top of the preset and always take precedence."* 규칙이 프리셋보다 **항상 우선**한다.

그래서 실전 조합은 이렇게 된다. **프리셋은 Default 로 두고, 자주 쓰는 안전한 명령만 allow 에 올린다.** 예를 들면 테스트 실행이나 린트 같은 것이다. 위험한 것(`git push --force` 같은 것)은 deny 에 올린다. 웹과 MCP 는 기본이 Ask 라서, 처음 보는 도구 호출은 사람이 한 번씩 보게 된다.

## 3. Network Permissions → Network Access Rules

화면 설명은 *"Configure allowed and denied URLs for reading."* 이다. 이 이름도 문서에서 그대로 찾지는 못했다. 대응하는 것은 `read_url(도메인)` 규칙이다.

- `read_url` 은 호스트와 서브도메인까지 맞춘다. 문서의 예로 `google.com` 은 `mail.google.com` 도 포함한다.
- [Sandbox 문서](https://antigravity.google/docs/sandbox): *"Sandboxed commands run without network access by default. Domains allowed under read_url are added to the sandbox's outbound allowlist."* 샌드박스 안의 명령은 **기본적으로 네트워크가 없고**, 여기서 허용한 도메인만 나갈 수 있다.

에이전트 보안에서 네트워크가 중요한 이유는 **유출 경로**이기 때문이다. 에이전트가 코드나 비밀값을 읽는 것 자체보다, 그것을 **외부로 보낼 수 있느냐**가 사고의 크기를 정한다. 패키지 레지스트리나 공식 문서 도메인처럼 **필요한 곳만 허용**하는 게 기본 방향이다.

## 4. Agent Behavior → Plan Review Policy

화면 설명은 *"Whether the agent asks you to review its documents."* 이고, 값은 **Always Ask** 다.

[변경 이력](https://antigravity.google/changelog) 2.17.0(2026-09-22)에 따르면 예전 이름(Artifact Review Policy)이 **Plan Review Policy** 로 바뀌었다. 선택지는 세 가지다. *"review every plan, review only when the agent judges it worthwhile, or skip review entirely."*

| 선택 | 동작 | 설정 파일 값([Settings 문서](https://antigravity.google/docs/settings)) |
|---|---|---|
| 매번 검토 | 계획을 만들면 항상 멈추고 승인을 기다림 | `asks-for-review` (기본값) |
| 에이전트 판단 | 검토할 가치가 있다고 볼 때만 멈춤 | `agent-decides` |
| 검토 생략 | 멈추지 않고 진행 | `always-proceed` |

화면의 "Always Ask" 는 문맥상 첫 번째(매번 검토)로 보인다. 다만 이 라벨이 문서에는 없어서 추정이다.

화면 아래 안내처럼 입력창에 `/` 를 치고 **plan** 을 고르면, 에이전트가 먼저 **Implementation Plan** 문서를 만든다. 사람이 **Proceed** 를 눌러야 구현을 시작한다([Plan 문서](https://antigravity.google/docs/plan)).

**권장:** 큰 작업일수록 **Always Ask**. 코드를 수백 줄 고친 뒤 되돌리는 것보다, 계획 한 페이지를 읽고 방향을 고치는 게 훨씬 싸다. 이 설정은 보안보다 **비용** 문제에 가깝다.

## 5. Execution → Queued Messages

선택지는 **Queue / Send Immediately** 다. 설명은 *"Configure when follow-up messages are sent."*

에이전트가 일하는 도중에 사람이 추가 지시를 입력하면 어떻게 할지를 정한다.

- **Queue**: 지금 작업이 끝날 때까지 줄을 세워 뒀다가 보낸다. 작업 흐름을 끊지 않는다.
- **Send Immediately**: 바로 끼어든다. 방향이 틀렸다는 걸 알았을 때 빨리 고칠 수 있다.

변경 이력에는 대기 중인 메시지에 *"Send now, Edit, and Delete"* 버튼이 있다는 내용이 있다(2.14.0). 그래서 Queue 로 두어도 급하면 개별 메시지를 바로 보낼 수 있다. 다만 이 두 선택지의 정확한 동작을 설명한 문서 페이지는 찾지 못했다. 위 설명은 화면 문구에서 읽은 해석이다.

## 정리 — 화면 속 설정이 합리적인 이유

| 설정 | 화면 값 | 판단 |
|---|---|---|
| Security Preset | Default | ✅ 권장. Turbo 는 격리된 환경에서만 |
| Tool Permissions | 규칙 2개 | ✅ 프리셋 위에 필요한 것만 allow, 위험한 것은 deny |
| Network Access Rules | — | 필요한 도메인만 허용하는 게 기본 방향 |
| Plan Review Policy | Always Ask | ✅ 큰 작업일수록 이득 |
| Queued Messages | Queue | 취향. 흐름을 안 끊으려면 Queue |

에이전트 도구의 설정 화면은 결국 **자율성과 통제 사이의 다이얼**이다. 이 화면의 선택(Default + Always Ask)은 "빨리 하되, 방향과 위험한 행동은 사람이 본다" 쪽이다. 처음 쓰는 도구라면 이렇게 시작하고, 믿을 만한 명령부터 하나씩 allow 로 옮기는 게 안전하다.

## References

모두 2026-09-27 에 확인했다.

- Google Antigravity Docs — [Permissions](https://antigravity.google/docs/permissions) · [Agent Settings](https://antigravity.google/docs/agent-settings) · [Sandbox](https://antigravity.google/docs/sandbox) · [Settings](https://antigravity.google/docs/settings) · [Plan](https://antigravity.google/docs/plan) · [Artifact Review](https://antigravity.google/docs/artifact-review) · [Browser Allowlist/Denylist](https://antigravity.google/docs/ide/allowlist-denylist)
- Google Antigravity — [Changelog](https://antigravity.google/changelog) (2.14.0 Global Permissions 명칭 변경, 2.17.0 Plan Review Policy)
