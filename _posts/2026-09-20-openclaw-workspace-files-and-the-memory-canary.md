---
layout: post
title: "에이전트가 자기 파일 일곱 개를 설명했다 — 그중 둘은 이미 은퇴한 파일이었다"
date: 2026-09-20 18:43:30 +0900
categories: [AI, Agent]
tags: [OpenClaw, Agent, Memory, Sandbox, Workspace, LLM]
---

오늘 세 편을 썼다. [능력과 정책은 다른 층이라는 이야기](https://myoungsoo7.github.io/2026/09/20/where-agent-policy-belongs-nemoclaw-openshell/), [GPU 를 빌린다는 것의 값](https://myoungsoo7.github.io/2026/09/20/nvidia-brev-gpu-stop-is-a-capacity-bet/), 그리고 [실제로 떠 있는 기계 한 장](https://myoungsoo7.github.io/2026/09/20/brev-gpu-environments-but-a-cpu-is-running/). 남은 층이 하나 있었다. **에이전트가 세션을 넘어서 자기를 기억하는 층.**

그래서 [OpenClaw](https://openclaw.ai) 로 돌아가는 에이전트에 두 가지를 시켰다. 하나는 *"네 워크스페이스 파일들을 나열하고 각각 한 문장으로 설명해라"*, 다른 하나는 *"장기 기억 파일에 이 한 줄을 정확히 추가하고, 네가 쓴 경로를 말해라"*.

두 번째 답은 맞았다. 그런데 **첫 번째 답을 문서와 대조해보니 일곱 개 중 둘이 이미 폐기된 파일이었다.**

![OpenClaw Control UI — 워크스페이스 파일 목록과 MEMORY.md 쓰기](/assets/images/openclaw/openclaw-workspace-memory-test.jpg)

*(위 화면은 가리지 않고 그대로 올렸다. 앞 글의 Brev 콘솔과 달리 여기엔 계정 ID·인스턴스 ID·토큰 같은 식별자가 화면에 없다. 보이는 경로는 컨테이너 내부 경로다.)*

> 참고: 이름이 비슷하지만 이 글의 OpenClaw 와 앞 글에서 다룬 NVIDIA 의 NemoClaw/OpenShell 사이의 관계는 **확인하지 않았다.** 이 글의 근거는 전부 `docs.openclaw.ai` 1차 문서다.

## 1. 화면이 말한 것

`Activity: 5 tools` 가 답 앞에 붙어 있다. 외워서 읊은 게 아니라 **실제로 디렉터리를 읽고** 답했다는 뜻이다. 그 답이 이랬다.

> **AGENTS.md**: Your workspace guide covering memory, heartbeats, and how to treat this folder as home.
> **HEARTBEAT.md**: Template for periodic checks; leave empty to skip heartbeat API calls.
> **IDENTITY.md**: Define your agent's name, creature, vibe, emoji, and avatar.
> **POLICY.md**: Shows the sandbox's network policy presets (verified/blocked hosts) and remediation steps.
> **SOUL.md**: Your core truths, boundaries, vibe, and continuity—evolving persona file.
> **TOOLS.md**: Local notes for your setup (cameras, SSH, TTS voices, etc.).
> **USER.md**: About the human you're helping: name, pronouns, timezone, notes, and context.

읽기 좋다. 일곱 줄 다 그럴듯하고, 문법도 어색한 데가 없고, 각 파일이 무슨 일을 하는지 딱 떨어진다. **이게 함정이다.**

## 2. 문서와 대조 — 둘은 은퇴했다

OpenClaw 문서의 워크스페이스 파일 목록은 이렇게 되어 있다: `AGENTS.md`, `SOUL.md`, `USER.md`, `IDENTITY.md`, **AGENTS.md 의 `## Tools` 섹션**, `BOOT.md`, `BOOTSTRAP.md`, `memory/YYYY-MM-DD.md`, `MEMORY.md`, `skills/`.

`TOOLS.md` 가 없다. `HEARTBEAT.md` 도 없다. 찾아보니 둘 다 **따로 은퇴 안내 페이지가 있었다.**

> **TOOLS.md is retired**
> Local tool and environment notes now live in the `## Tools` section of `AGENTS.md`.
> — [TOOLS.md retired](https://docs.openclaw.ai/reference/templates/TOOLS)

> **HEARTBEAT.md is retired**
> OpenClaw no longer creates `HEARTBEAT.md` in new workspaces **or reads it at runtime.** Heartbeat instructions now live in the system-owned monitor scratch in the shared state database.
> — [Retired HEARTBEAT.md workspace file](https://docs.openclaw.ai/reference/templates/HEARTBEAT)

게이트웨이 문서는 한 번 더 못을 박는다.

> Runtime heartbeat instructions come from database scratch only. **The runtime never reads `HEARTBEAT.md`.**
> — [Heartbeat](https://docs.openclaw.ai/gateway/heartbeat)

그러니까 화면의 저 문장 — *"leave empty to skip heartbeat API calls"* — 은 **더 이상 참이 아닌 동작을 설명하고 있다.** 파일을 비워도 스킵을 결정하는 건 그 파일이 아니다. 문서 기준으로 스킵 판정은 DB 의 monitor scratch 가 비었는지로 내려진다(`reason=empty-heartbeat-file`).

### 이게 에이전트의 잘못인가

아니다. 그리고 이 구분이 중요하다.

- **파일이 거기 있는 건 사실이다.** 오래된 워크스페이스에 남아 있을 수 있고, 문서도 그 경우를 상정해 `openclaw doctor --fix` 로 아카이브·병합하라고 안내한다. 이 배포본에서 그 마이그레이션이 돌았는지 나는 모른다.
- **에이전트는 디렉터리를 정직하게 읽었다.** 있는 파일을 나열했다.
- **틀린 건 "설명"이다.** 파일명을 보고 *그럴듯한 역할*을 채워 넣었고, 그 역할이 현재 런타임에는 없다.

교훈은 이거다. **에이전트가 자기 파일을 설명할 수 있다는 것은 그 파일이 작동한다는 증거가 아니다.** 파일 존재는 `ls` 로 확인되지만, 파일이 *무엇을 하는가*는 런타임 문서로만 확인된다. 일곱 줄 중 둘이 그 경계를 넘었고, 둘 다 읽기엔 완벽했다.

## 3. POLICY.md — 문서에 없고, 동사가 "Shows" 다

남은 하나가 더 흥미롭다. `POLICY.md` 는 은퇴 안내조차 없다. 워크스페이스 문서·메모리 문서·샌드박스 문서·템플릿 목록, 그리고 `docs.openclaw.ai/llms.txt` 전체(1,348줄)를 훑었는데 **이 파일명이 한 번도 안 나온다.** 이 배포본에만 있는 파일인지, 스킬이 만든 것인지, 문서가 아직 안 따라온 것인지 — 모른다. 모른다고 적어둔다.

그런데 에이전트가 고른 동사를 보자.

> POLICY.md: **Shows** the sandbox's network policy presets (verified/blocked hosts) and remediation steps.

**Shows.** 강제한다(enforces)가 아니라 보여준다다. 우연이든 아니든, 이 동사가 정확하다. OpenClaw 에서 실제 집행은 워크스페이스 파일이 아니라 게이트웨이 설정에 있고, 문서가 그걸 셋으로 쪼개서 적어놨다.

> 1. **Sandbox** (`agents.defaults.sandbox.*` …) decides **where tools run** (sandbox backend vs host).
> 2. **Tool policy** (`tools.*`, `tools.sandbox.tools.*` …) decides **which tools are available/allowed**.
> 3. **Elevated** (`tools.elevated.*` …) is an **exec-only escape hatch** from ordinary sandboxing. **It cannot bypass a creator role's required sandbox.**
> — [Sandbox vs tool policy vs elevated](https://docs.openclaw.ai/gateway/sandbox-vs-tool-policy-vs-elevated)

셋 다 **에이전트가 쓸 수 없는 곳**에 있다. 그리고 같은 문서는 필수 샌드박스가 프로비저닝에 실패하면 *fails closed* 라고 적는다 — 통제가 안 서면 열리는 게 아니라 닫힌다.

같은 이야기가 워크스페이스 문서에도 두 번 나온다.

> The workspace is the **default cwd, not a hard sandbox.** Tools resolve relative paths against the workspace, but absolute paths can still reach elsewhere on the host unless sandboxing is enabled.

> The `## Tools` section holds local environment notes and conventions. **It does not control tool availability; it is only guidance.**
> — [Agent workspace](https://docs.openclaw.ai/concepts/agent-workspace)

아침 글의 결론이 *"가드레일이 클라이언트에 있으면 그건 가드레일이 아니라 기본값이다"* 였다. 여기서는 이렇게 바꿔 쓸 수 있다.

**에이전트가 편집할 수 있는 파일에 적힌 정책은 정책이 아니라 메모다.** 워크스페이스는 작업 공간이지 경계가 아니다. 경계는 `agents.defaults.sandbox` 쪽에 있다.

## 4. 기억을 믿지 말고 검증하는 법 — 카나리아 한 줄

두 번째 지시는 이렇게 줬다.

> Append exactly this one line to your curated long-term memory file MEMORY.md (create it if missing): `"PREF-7Q2K: The user prefers replies in Korean, keeping technical terms in English."` Do not write it to any other file. Then tell me the exact path you wrote to.

세 조각이 다 일부러 들어간 것이다.

| 장치 | 왜 |
| --- | --- |
| `PREF-7Q2K` 라는 무의미한 토큰 | 세상 어디에도 없는 문자열이라 나중에 `grep` 한 번이면 진위가 끝난다 |
| "다른 파일엔 쓰지 마라" | 쓰기 범위를 좁혀 놓아야 "어딘가엔 썼다"로 빠져나갈 수 없다 |
| "네가 쓴 정확한 경로를 말해라" | 자연어 확언 대신 **검증 가능한 출력**을 요구한다 |

결과는 화면에 그대로 남았다. 툴 실행 줄이 `Write to /sandbox/.openclaw/workspace/MEMORY.md (82 chars)` 였고, 답도 같은 경로였다. 경로·바이트 수·파일 하나. **"기억했습니다"는 검증할 수 없지만, 이 세 개는 검증된다.**

문서가 이 방식을 정당화해준다.

> OpenClaw remembers things by writing plain Markdown files in your agent's workspace (default `~/.openclaw/workspace`). **The model only remembers what gets saved to disk; there is no hidden state.**
> — [Memory overview](https://docs.openclaw.ai/concepts/memory)

숨은 상태가 없다는 건, 뒤집으면 **디스크에 안 남았으면 기억이 아니라는 뜻이다.** 그래서 "기억해둘게요"라는 답은 그 자체로는 아무 정보가 아니고, 파일 경로는 정보다.

덧붙여 알아둘 제약 셋 (전부 문서 기준이고, 내가 이 배포본에서 실측한 게 아니다):

- **버짓이 따로 있다.** 부트스트랩 주입은 파일당 `bootstrapMaxChars` 기본 `20000`, 전체 `bootstrapTotalMaxChars` 기본 `60000` 이고 `USER.md` 는 별도로 4,000자다. `MEMORY.md` 가 버짓을 넘으면 **디스크 파일은 온전한 채로 주입본만 잘린다.** 파일이 커졌는데 에이전트가 앞부분만 아는 상황이 조용히 만들어진다.
- **`MEMORY.md` 는 메인 세션 전용이다.** 문서는 *"Only load `MEMORY.md` in the main, private session (not shared/group contexts)"* 라고 적는다. 개인 채팅에서 기억시킨 게 그룹 채팅에서 안 나오는 건 고장이 아니라 설계다.
- **날짜 로그는 자동 주입되지 않는다.** `memory/YYYY-MM-DD.md` 는 `memory_search`/`memory_get` 으로 검색되는 층이고, 매 턴 프롬프트에 실리지 않는다.

한 가지 추정도 적어둔다. 쓰기 경로가 `/sandbox/.openclaw/workspace/` 로 시작한다. 문서의 기본 워크스페이스는 `~/.openclaw/workspace` 이고 샌드박스 루트 기본값은 `~/.openclaw/sandboxes` 다. 이 앞에 붙은 `/sandbox` 는 **샌드박스 컨테이너 안에서 돌고 있다는 정황**으로 읽히지만, 설정을 직접 보지 않았으니 여기까지는 추정이다. 확실히 보려면 `openclaw sandbox explain` 이 있다 — 문서가 유효 모드·호스트 워크스페이스·마운트·툴 정책을 한 번에 찍어준다고 안내한다.

## 5. 남는 것 셋

**① 에이전트의 자기 설명은 소스가 아니다.** 일곱 줄 중 둘이 폐기된 파일을 살아 있는 것처럼 설명했다. 틀린 티가 하나도 안 났다는 게 핵심이다. 에이전트한테 자기 구성을 물어보는 건 *출발점*으로는 훌륭하고 *근거*로는 못 쓴다. 파일 목록은 믿고, 역할 설명은 문서로 다시 짚는다.

**② 정책은 에이전트가 못 만지는 곳에 둔다.** `POLICY.md` 는 보여주는 파일이고, 집행은 샌드박스 모드·툴 allow/deny·elevated 게이트에 있다. 셋 다 게이트웨이 설정이다. 이건 아침 글에서 브라우저 자바스크립트에 가드레일이 있던 그 리포와 정확히 같은 구조의 문제다 — **쓰는 주체와 지키는 주체가 같으면 그건 규칙이 아니다.**

**③ 기억은 토큰으로 검증한다.** 고유 문자열 + 쓰기 범위 제한 + 경로 회신. 세 줄이면 "정말 저장됐나"가 확언이 아니라 관측이 된다. 에이전트를 오래 쓸 생각이면 이 체크를 가끔 돌리는 게 낫다 — 특히 버짓 잘림처럼 **조용히** 생기는 고장이 있기 때문에.

---

## References

- [OpenClaw](https://openclaw.ai) — 제품 홈
- [Agent workspace — OpenClaw Docs](https://docs.openclaw.ai/concepts/agent-workspace) — 워크스페이스 파일 목록, "default cwd, not a hard sandbox", `## Tools` 섹션의 성격, 부트스트랩 문자 버짓
- [Memory overview — OpenClaw Docs](https://docs.openclaw.ai/concepts/memory) — 메모리 파일 계층, "no hidden state", 주입본 잘림
- [Sandbox vs tool policy vs elevated — OpenClaw Docs](https://docs.openclaw.ai/gateway/sandbox-vs-tool-policy-vs-elevated) — 세 가지 통제의 분리, fails closed, `openclaw sandbox explain`
- [Sandboxing — OpenClaw Docs](https://docs.openclaw.ai/gateway/sandboxing) — 샌드박스 모드·백엔드·workspaceAccess
- [TOOLS.md retired — OpenClaw Docs](https://docs.openclaw.ai/reference/templates/TOOLS) · [Retired HEARTBEAT.md workspace file](https://docs.openclaw.ai/reference/templates/HEARTBEAT) — 두 파일의 폐기 안내
- [Heartbeat — OpenClaw Docs](https://docs.openclaw.ai/gateway/heartbeat) — "The runtime never reads HEARTBEAT.md", `doctor --fix` 마이그레이션
- 같은 날 앞선 글: [에이전트 정책은 어디에 두나](https://myoungsoo7.github.io/2026/09/20/where-agent-policy-belongs-nemoclaw-openshell/) · [GPU '정지'가 안전하지 않은 이유](https://myoungsoo7.github.io/2026/09/20/nvidia-brev-gpu-stop-is-a-capacity-bet/) · [GPU Environments 인데 CPU 가 떠 있다](https://myoungsoo7.github.io/2026/09/20/brev-gpu-environments-but-a-cpu-is-running/)

*(문서 인용은 모두 2026-09-20 확인 시점 기준이다. OpenClaw 문서는 페이지 URL 뒤에 `.md` 를 붙이면 렌더 전 원문 마크다운을 그대로 내려주므로, 자바스크립트로 그려지는 표·아코디언도 텍스트로 검증할 수 있다.)*
