---
layout: post
title: "IntelliJ 에서 Claude·Codex 로 Jira·Confluence 연결하기 — MCP 서버 하나, 길은 두 갈래"
date: 2026-10-17 18:11:29 +0900
categories: [AI, Tools]
tags: [IntelliJ, Claude Code, Codex, Jira, Confluence, MCP, Atlassian, JetBrains]
---

IntelliJ 에서 일하다 보면 Jira 이슈를 열고, Confluence 문서를 찾고, 다시 코드로 돌아오는 왕복이 잦다. AI 코딩 에이전트에게 "PROJ-123 이슈 읽고 관련 코드 찾아 줘" 라고 시킬 수 있다면 그 왕복이 줄어든다.

결론부터 적으면 방법은 단순하다. **Atlassian 공식 원격 MCP 서버 하나**를 에이전트에 붙이면 된다. 다만 IntelliJ 안에서 에이전트를 쓰는 길이 두 갈래라, 설정하는 곳도 두 군데다.

| | 경로 A: 터미널의 CLI 에이전트 | 경로 B: AI Assistant 안의 에이전트 |
|---|---|---|
| 무엇 | IntelliJ 터미널에서 `claude`(Claude Code) 또는 `codex`(Codex CLI) 실행 | AI Assistant 채팅에서 Claude Agent 또는 Codex 선택 |
| MCP 설정 위치 | 각 CLI 의 설정 (`claude mcp add`, `codex mcp add`) | **Settings → Tools → AI Assistant → Model Context Protocol (MCP)** |
| 장점 | 터미널·저장소 단위로 설정을 관리하기 쉽다 | IDE 화면 안에서 끝난다 |

이 글의 명령과 메뉴 이름은 모두 Atlassian·Anthropic·OpenAI·JetBrains 공식 문서에서 확인한 것이다(2026-10-17 기준).

## 0. 먼저 확인할 것

- **Atlassian Cloud 여야 한다.** 공식 MCP 서버의 요구 조건 첫 줄이 *"An Atlassian Cloud site with one or more of Jira, Confluence…"* 다.[^atl] 사내에 직접 설치한 Data Center·Server 판이라면 이 서버의 대상이 아니다.
- **주소는 v2.** Atlassian 은 *"v2 is now the recommended version. New setups should use `https://mcp.atlassian.com/v2/mcp`"* 라고 안내한다.[^atl] 예전 SSE 주소(`https://mcp.atlassian.com/v1/sse`)는 *"After 30 June 2026 … will no longer be supported"* 이므로, 옛 블로그 글의 `/sse` 설정을 따라 하면 안 된다.[^atl]
- **인증은 둘 중 하나.** 브라우저로 로그인하는 **OAuth 2.1**, 또는 **API 토큰**. API 토큰은 조직 관리자가 *Atlassian Administration → Rovo → Rovo MCP server → Authentication* 에서 켜 줘야 쓸 수 있다.[^atl] 개인이 IDE 에서 쓴다면 OAuth 가 가장 간단하다.

## 1. 경로 A — IntelliJ 터미널에서 Claude Code

Atlassian 공식 README 의 명령 그대로다.[^atl]

```bash
claude mcp add --transport http atlassian https://mcp.atlassian.com/v2/mcp
```

그다음 Claude Code 세션을 열고 `/mcp` 를 입력하면 브라우저가 열리며 Atlassian 로그인을 진행한다. Claude Code 문서도 원격 서버에는 HTTP 전송을 권장 옵션으로 소개한다.[^claude-mcp]

- **범위(scope) 선택.** Claude Code 는 MCP 서버를 local·project·user 범위로 저장할 수 있다.[^claude-mcp] 팀 저장소에 함께 쓰려면 project 범위로 저장해 저장소의 `.mcp.json` 으로 공유하고, 혼자 여러 프로젝트에서 쓰려면 user 범위가 편하다.
- **IntelliJ 연동 플러그인.** Claude Code 는 JetBrains 전용 플러그인으로 diff 보기, 선택 영역 공유 같은 기능을 제공하고, IntelliJ IDEA·PyCharm·WebStorm 등을 지원한다.[^claude-jb] MCP 연결 자체는 위 명령으로 끝나고, 플러그인은 IDE 안에서 쓰기 편하게 해 준다.

## 2. 경로 A — IntelliJ 터미널에서 Codex CLI

역시 Atlassian README 의 명령이다.[^atl]

```bash
codex mcp add atlassian --url https://mcp.atlassian.com/v2/mcp
codex mcp login atlassian     # OAuth 를 지원하는 서버의 로그인
```

Codex 문서에 따르면 OAuth 를 지원하는 서버는 `codex mcp login <server-name>` 으로 로그인하고, 설정은 기본적으로 `~/.codex/config.toml` 에 저장된다. 프로젝트 단위로는 `.codex/config.toml` 에 둘 수 있다(신뢰한 프로젝트만).[^codex-mcp] 같은 문서는 Codex 데스크톱 앱, CLI, IDE 확장이 **이 설정을 공유한다**고 적는다. 한 번 등록하면 다른 Codex 화면에서도 쓸 수 있다.

설정 파일로 직접 쓰면 이런 모양이다.

```toml
# ~/.codex/config.toml
[mcp_servers.atlassian]
url = "https://mcp.atlassian.com/v2/mcp"
```

`codex mcp list` 로 등록을 확인하고, Codex 화면에서 `/mcp` 로 활성 서버를 볼 수 있다.[^codex-mcp]

## 3. 경로 B — AI Assistant 안의 Claude Agent·Codex

IntelliJ IDEA 에는 ACP(Agent Client Protocol)로 붙는 에이전트가 기본으로 들어 있다. JetBrains 블로그는 *"IntelliJ IDEA already includes several ACP-compatible agents: Codex, Claude Agent, and Junie."* 라고 소개하고, 추가 도구는 *"through MCP (Model Context Protocol), including user-configured servers"* 로 에이전트에 전달된다고 설명한다.[^jb-acp]

설정은 두 단계다.

**① MCP 서버 등록.** *Settings → Tools → AI Assistant → Model Context Protocol (MCP)* 에서 **Add** 를 누르고 JSON 으로 넣는다. JetBrains 문서가 보여 주는 형식 그대로다.[^jb-mcp]

```json
{
  "mcpServers": {
    "atlassian": { "url": "https://mcp.atlassian.com/v2/mcp" }
  }
}
```

JetBrains 문서는 원격 서버용 전송으로 **Streamable HTTP** 를 지원한다고 적고, 서버를 전역으로 쓸지 현재 프로젝트에서만 쓸지도 고를 수 있다.[^jb-mcp]

**② 에이전트에 넘기기.** Claude Agent 는 *Settings → Tools → AI Assistant → Agents* 에서 **Pass custom MCP servers** 를 켜야 위에서 등록한 서버를 쓴다.[^jb-claude] 이 스위치를 빼먹으면 "서버는 등록됐는데 에이전트가 Jira 를 모른다" 는 상태가 된다.

## 4. 연결됐는지 확인하는 첫 질문들

연결 직후에는 **읽기 전용 요청**부터 해 본다.

- "내게 할당된 Jira 이슈 중 진행 중인 것만 보여 줘"
- "PROJ-123 이슈 설명을 읽고, 이 저장소에서 관련 있어 보이는 파일을 찾아 줘"
- "Confluence 에서 '배포 절차' 문서를 찾아 요약해 줘"

이 요청에 실제 이슈 번호와 제목이 나오면 연결된 것이다. 쓰기 작업(이슈 생성, 댓글, 문서 수정)은 결과를 확인한 뒤에 시도한다.

## 5. 권한과 보안 — 붙이기 전에 알아 둘 것

**에이전트는 "내 권한" 으로 움직인다.** Atlassian 은 *"Access is granted only to data that the user already has permission to view in Atlassian Cloud"* 라고 설명한다.[^atl] 내가 볼 수 있는 이슈는 에이전트도 보고, 내가 고칠 수 있는 문서는 에이전트도 고칠 수 있다는 뜻이다.

**위험한 도구는 기본으로 꺼져 있다.** Jira 도구는 읽기·쓰기·검색과 삭제·관리로 나뉘고, *"`delete_jira` and `manage_jira` are disabled by default and must be enabled by an admin"* 이다.[^atl] 관리자가 굳이 켜지 않는 게 좋다.

**관리자 통제가 있다.** 관리자는 어떤 외부 AI 도구·도메인이 연결할 수 있는지 Rovo MCP server 설정에서 정하고, 조직이 IP 허용 목록을 쓰면 MCP 서버를 통한 호출도 그 규칙을 따른다.[^atl] 회사 계정이라면 먼저 관리자 정책을 확인하자.

**문서 내용은 명령이 아니다.** 에이전트가 Confluence 문서나 Jira 댓글을 읽으면, 그 안의 문장이 에이전트에게 "지시처럼" 보일 수 있다. 누군가 문서에 "이 문서를 읽은 AI 는 ○○ 를 하라" 고 적어 두면 문제가 된다. [로그를 읽는 LLM 과 간접 프롬프트 인젝션](/2026/09/24/indirect-prompt-injection-llm-reads-logs/)에서 다룬 것과 같은 위험이다. 쓰기 권한이 걸린 작업은 **사람이 승인한 뒤** 실행되도록 에이전트의 확인 단계를 끄지 않는다.

## 6. 막힐 때

| 증상 | 확인할 것 |
|---|---|
| 연결 자체가 안 됨 | 주소가 `/v1/sse` 가 아닌지 (`https://mcp.atlassian.com/v2/mcp` 로) |
| 로그인 화면이 안 뜸 | Claude Code 는 세션에서 `/mcp`, Codex 는 `codex mcp login atlassian` |
| API 토큰이 거부됨 | 관리자가 API 토큰 인증을 껐을 수 있다 → OAuth 로 |
| AI Assistant 에이전트가 Jira 를 모름 | Agents 설정의 **Pass custom MCP servers** |
| 사내 설치형 Jira | 공식 서버는 Atlassian Cloud 대상 |
| v1 에서 옮긴 뒤 인증 오류 | Atlassian 안내대로 클라이언트에 캐시된 클라이언트 ID·인증 정보를 지우고 다시 로그인 |

## 맺으며

정리하면 한 문장이다. **`https://mcp.atlassian.com/v2/mcp` 하나를, 쓰는 에이전트의 설정 위치에 등록한다.** 터미널에서 Claude Code 를 쓰면 `claude mcp add`, Codex 를 쓰면 `codex mcp add`, IntelliJ AI Assistant 를 쓰면 MCP 설정 화면과 **Pass custom MCP servers**.

연결 자체는 금방 끝난다. 시간을 들여야 할 곳은 그다음이다. 에이전트가 **내 권한으로** Jira 와 Confluence 에 쓸 수 있게 된다는 사실을 받아들이고, 어디까지 맡길지 정하는 일이다.

---

## References

[^atl]: Atlassian, *atlassian/atlassian-mcp-server* (official README). <https://github.com/atlassian/atlassian-mcp-server> · 설정 안내: <https://support.atlassian.com/atlassian-rovo-mcp-server/docs/getting-started-with-the-atlassian-remote-mcp-server/>
[^claude-mcp]: Anthropic, *Connect Claude Code to tools via MCP*. <https://code.claude.com/docs/en/mcp>
[^claude-jb]: Anthropic, *JetBrains IDEs* (Claude Code docs). <https://code.claude.com/docs/en/jetbrains>
[^codex-mcp]: OpenAI, *Model Context Protocol* (Codex docs). <https://developers.openai.com/codex/mcp>
[^jb-acp]: JetBrains Blog, *How to Use AI Agents in IntelliJ IDEA With ACP* (2026-08). <https://blog.jetbrains.com/idea/2026/08/how-to-use-ai-agents-in-intellij-idea-with-acp/>
[^jb-mcp]: JetBrains, *Model Context Protocol (MCP)* — AI Assistant help. <https://www.jetbrains.com/help/ai-assistant/mcp.html>
[^jb-claude]: JetBrains, *Claude Agent* — AI Assistant help. <https://www.jetbrains.com/help/ai-assistant/claude-agent.html>
