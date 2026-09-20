---
layout: post
title: "지시 파일은 설득이고, 통제는 강제다 — 하네스 5종 비교와 자유도의 6개 축"
date: 2026-09-20 19:20:26 +0900
categories: [ai, security]
tags: [agent, harness, claude-code, codex, cursor, openclaw, openshell, nemoclaw, sandbox, landlock]
---

[4a 실습 글](/2026/09/20/sandbox-policy-lab-two-open-failure-modes/)은 한 샌드박스 안에서 잠금 장치들을 실측하는 데서 끝났다. 이번 정리는 시야를 넓힌다 — 지금 쓰이는 **하네스 5종이 각자 어떤 파일로 지시받고 어떤 층으로 통제되는지**, 그리고 통제를 **6개 축**으로 쪼갰을 때 "자유도 = 공격 표면"이라는 등식이 어떻게 성립하는지다.

![하네스 5종의 지시 파일·기본 통제 비교표와, NemoClaw 참조 구성의 6개 축(Filesystem/Network/Process identity/Binary identity/Persistence/Inference routing)을 4a 실측과 대조한 표](/assets/images/openclaw-workspace/harness-controls-six-axes.jpg)

## 표 1 — 하네스마다 "듣는 파일"과 "막는 층"이 따로 있다

| 하네스 | 지시 파일 | 기본 통제 |
|---|---|---|
| Claude Code | `CLAUDE.md` | tool rules · permission mode · sandbox 설정이 실행/승인 결정 |
| Codex CLI | `AGENTS.md` | sandbox 설정 + approval policy, 한도 내에서 자동 실행 |
| Cursor | `.cursor/rules/*.mdc` | 편집은 무승인, 터미널은 기본 승인 |
| Hermes | skills · memory · cron · messaging | approval mode + terminal backend |
| OpenClaw | `SOUL.md`/`AGENTS.md` · 게이트웨이 세션 · 스케줄 | 이 코스에선 OpenShell 안 |

이 표에서 정말 중요한 건 열이 **둘로 갈라져 있다**는 사실 자체다. 지시 파일과 통제는 다른 성질의 물건이다.

**지시 파일은 설득 층이다.** Claude Code 공식 문서가 이걸 이례적으로 명시한다: 메모리 파일은 "컨텍스트이지, 강제되는 설정이 아니다(context, not enforced configuration)"이며, "권한 규칙은 Claude Code 가 강제하는 것이지 모델이 강제하는 게 아니다 — `CLAUDE.md` 의 지시는 Claude 가 *무엇을 시도할지*를 바꿀 뿐, Claude Code 가 *무엇을 허용할지*는 바꾸지 않는다."[^cc-mem][^cc-perm] Codex 도 같은 구조다: `AGENTS.md` 는 매 실행마다 루트→작업 디렉터리 순으로 병합돼 프롬프트에 들어가는 지침이고,[^cx-agents] 실제 한도는 sandbox mode(read-only/workspace-write)와 approval policy 의 조합이 정한다 — workspace-write 에서 네트워크는 기본 차단이다.[^cx-sbx] Cursor 의 `.mdc` 룰도 프롬프트에 섞이는 가이드이고, 편집은 자동·터미널 명령은 샌드박스/승인 경로로 가는 건 Run Mode 설정의 소관이다.[^cur-rules][^cur-run]

**통제는 강제 층이다.** 다섯 하네스 모두 이 층을 갖고 있지만 구현 위치가 다르다 — Claude Code 는 permission mode + 자체 샌드박스(macOS Seatbelt 류), Codex 는 Seatbelt/Landlock+seccomp,[^cx-sbx] Cursor 는 샌드박스+분류기, Hermes(본인 로컬 오케스트레이터)는 approval mode 와 터미널 백엔드 구성, 그리고 OpenClaw 는 — 이 코스 구성에서는 — 하네스 밖의 **OpenShell 래퍼**가 담당한다.

그래서 그림의 요약 문장이 정확하다: **"CLI 선택 = 시작 기본값 선택, OpenShell 래퍼 = 그 기본값이 어디까지 닿을지 결정."** 어느 CLI 를 고르느냐는 설득 층의 문법과 통제 층의 기본값을 고르는 일이고, OpenShell 같은 외부 래퍼는 그 기본값이 실제 OS 에서 닿는 반경을 정한다. NVIDIA 는 같은 OpenShell 통합을 Codex·Cursor·OpenCode 에도 문서화해 두었다[^dli] — 래퍼가 하네스에 독립적인 층이라는 뜻이다.

## 표 2 — 자유도의 6개 축, 그리고 4a 에서 본 것과의 대조

NemoClaw 참조 구성은 "에이전트의 자유도"를 6개 축으로 분해한다. 각 축이 손잡이(무엇을 조절하나)와 참조 구성(어떻게 잠갔나)을 갖고, 우리가 4a 샌드박스에서 실측한 것과 정확히 맞물린다:

| 축 | 손잡이 | 참조 구성 → 4a 실측 |
|---|---|---|
| Filesystem | 읽기/쓰기 경로 | 쓰기는 `/tmp`·`/sandbox/.openclaw`·`/sandbox/.nemoclaw`·workdir 만, 시스템 경로는 읽기 전용(Landlock best_effort) → 우리의 `/opt` 쓰기 거부 |
| Network | host+port+method/path, **바이너리별** | 기본 거부 + 짧은 allowlist, 각 항목이 HTTP 형태·바이너리에 바인딩 → 우리의 git OK / curl 거부 |
| Process identity | 실행 유저 | non-root, ptrace/mount/setuid 는 seccomp 차단 → uid 998 |
| Binary identity | 어떤 실행 파일이 grant 를 쓰나 | exe 경로 + 조상 프로세스 walk + TOFU 해시. `argv[0]` 은 스푸핑 가능해 불신 |
| Persistence | cron · skills · `SOUL.md` | workspace 권한 + 호스트 관리 파일 보호 → 우리 `SOUL.md` 는 쓰기 가능(열림) |
| Inference routing | 모델 호출이 어디로 나가나 | `inference.local` 게이트웨이 경유, Privacy Router 가 오퍼레이터 정책으로 내보낼 것을 결정 → 샌드박스 curl 로 NVIDIA API 가 403 |

세 축은 4a 에서 이미 봤던 수수께끼의 답을 준다.

**Network 축의 "per binary" 가 git OK/curl 거부를 설명한다.** 4a 에서 같은 호스트라도 git 은 되고 curl 은 안 되는 걸 봤다. 호스트 allowlist 만으로는 설명이 안 되는 현상인데, 참조 구성은 허용 항목을 호스트+포트+메서드/경로에 더해 **요청을 보내는 바이너리**에까지 바인딩한다. "github.com 은 git 바이너리에게만 열려 있다"는 식이다 — 같은 목적지라도 도구가 다르면 다른 권한이다.

**Binary identity 축은 그 바인딩의 아킬레스건을 정직하게 적었다.** 바이너리별 grant 를 하려면 "지금 이 요청을 보낸 게 진짜 git 인가"를 판정해야 한다. 참조 구성의 답은 exe 경로 + 조상 프로세스 walk + 최초 신뢰(TOFU) 해시의 조합이고, `argv[0]` 은 스푸핑이 가능하므로 **믿지 않는다**. 프로세스 이름이 아니라 실행 파일의 정체를 본다는 것 — 이게 allowlist 를 "이름 검사"에서 "신원 검사"로 끌어올리는 부분이다.

**Inference routing 은 다른 다섯 축이 못 다루는 유출로를 막는다.** 에이전트의 가장 큰 상시 트래픽은 모델 호출 자체다. 참조 구성은 이걸 로컬 게이트웨이(`inference.local`)로 강제 경유시키고, Privacy Router 가 오퍼레이터 정책에 따라 무엇이 밖으로 나갈지 정한다. 4a 에서 샌드박스 curl 로 NVIDIA API 를 직접 치면 403 이 났던 이유가 이것이다 — 모델 호출조차 에이전트가 임의 경로로 하게 두지 않는다.

그리고 Persistence 축은 [앞 글의 실패 모드 ①](/2026/09/20/sandbox-policy-lab-two-open-failure-modes/)과 그대로 만난다. 참조 구성도 cron·skills·`SOUL.md` 를 지속성 통로로 명시하고 호스트 관리 파일은 보호하지만, 우리 실습 구성에서 `SOUL.md` 는 쓰기 가능이었다 — 6축 프레임 안에서도 이 축이 **열린 채**라는 걸 표가 스스로 표시하고 있다.

## "자유도 = 공격 표면"이라는 등식

6축 표의 제목이 이 프레임의 요지다. 축 하나하나가 에이전트에게 주는 자유도이면서 동시에 공격자가 쓸 수 있는 표면이다: 쓰기 경로는 지속성 통로가 되고, 네트워크 허용은 유출로가 되고, 실행 유저의 권한은 상승의 발판이 되고, 바이너리 신원 판정의 틈은 allowlist 우회가 되고, 모델 호출 경로는 데이터가 새는 마지막 문이 된다. 통제 설계란 자유도를 0 으로 만드는 게 아니라 — 그러면 에이전트가 일을 못 한다 — **축별로 필요한 만큼만 열고, 열린 곳을 정확히 아는 것**이다. 표 1 의 하네스들이 전부 설득 층과 강제 층을 분리해 둔 이유이기도 하다: 설득 층은 넓게 열어 두되(지시는 자유롭게), 강제 층에서 축별로 잠근다.

남은 실습은 셋이다 — ① 하네스 무게 비교 채팅(추상화·가정·내장 기능), ② 브라우저를 셸로 쓰는 CLI 에이전트(화면 조작 대신 데이터를 반환하게), ③ 런처를 호스트 셸로(우린 이미 VM 터미널로 진행해 연결 불가라 스킵). 다음 글감은 아마 ①이나 ②가 될 것이다.

---

## References

[^cc-mem]: Claude Code 공식 문서, "How Claude remembers your project" — "Claude treats them as context, not enforced configuration." <https://code.claude.com/docs/en/memory>
[^cc-perm]: Claude Code 공식 문서, "Configure permissions" — "Permission rules are enforced by Claude Code, not by the model. Instructions in your prompt or CLAUDE.md shape what Claude tries to do, but they don't change what Claude Code allows." <https://code.claude.com/docs/en/permissions>
[^cx-agents]: OpenAI Codex 공식 문서, "Custom instructions with AGENTS.md" — 전역→프로젝트 병합 순서, 32KiB 한도. <https://developers.openai.com/codex/guides/agents-md>
[^cx-sbx]: OpenAI Codex 공식 문서, "Sandbox & approvals" — sandbox mode × approval policy 조합, workspace-write 의 네트워크 기본 차단, macOS Seatbelt/Linux Landlock+seccomp. <https://github.com/openai/codex/blob/main/docs/sandbox.md>
[^cur-rules]: Cursor 공식 문서, "Rules" — `.cursor/rules/*.mdc`, frontmatter 로 적용 조건 결정. <https://cursor.com/docs/rules>
[^cur-run]: Cursor 공식 문서, "Run Modes" — 편집·터미널의 승인 경로 분리, 샌드박스와 분류기. <https://cursor.com/docs/agent/security/run-modes>
[^dli]: NVIDIA DLI 코스 "Securing Agents with NemoClaw and OpenShell" (`DLI+S-FX-43+V1`) — NemoClaw 참조 구성과 OpenShell 통합. <https://learn.nvidia.com/courses/course-detail?course_id=course-v1:DLI+S-FX-43+V1>

관련 시리즈: [OpenClaw 워크스페이스 문서들의 역할](/2026/09/20/openclaw-workspace-file-roles/) · [검증 실험 로그 6줄 읽기](/2026/09/20/openclaw-trust-but-verify-lab-log/) · [정책 격리 실습(4a)의 두 실패 모드](/2026/09/20/sandbox-policy-lab-two-open-failure-modes/)

*표의 실측 항목(/opt 거부, git OK/curl 거부, uid 998, SOUL.md 쓰기 가능, NVIDIA API 403)은 본인 샌드박스 실습에서의 관찰이다. Hermes 는 본인 로컬 오케스트레이터 구성으로 공개 문서가 없다.*
