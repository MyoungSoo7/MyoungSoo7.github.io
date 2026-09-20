---
layout: post
title: "에이전트의 영혼은 마크다운이다 — 샌드박스에서 까본 OpenClaw 워크스페이스 문서들의 역할"
date: 2026-09-20 18:42:24 +0900
categories: [ai, agents]
tags: [openclaw, agent, workspace, soul-md, heartbeat, memory, sandbox]
---

샌드박스에 OpenClaw 를 올려 놓고 워크스페이스 디렉터리를 직접 열어 봤다. 눈에 들어온 건 데이터베이스도 설정 패널도 아니고 마크다운 파일 몇 개다 — `SOUL.md`, `IDENTITY.md`, `USER.md`, `memory/`, `skills/`, `HEARTBEAT.md`.

![샌드박스 탐사 노트 — SOUL.md 는 페르소나·경계 핵심 문서, IDENTITY.md/USER.md 는 빈 템플릿, memory/skills 는 비어 있고 HEARTBEAT.md 는 30분마다 읽히는 틱 파일](/assets/images/openclaw-workspace/sandbox-exploration-note.png)

에이전트의 인격·기억·스케줄이 전부 사람이 읽고 고칠 수 있는 플레인 텍스트로 놓여 있다는 뜻이다. 이 글은 그 파일들이 각각 무슨 역할인지를 공식 문서 기준으로 정리하고, 마지막에 "워크스페이스 ≠ 샌드박스"라는 중요한 경계 하나를 짚는다.

## 워크스페이스란 무엇인가

OpenClaw 문서의 정의는 간명하다: **워크스페이스는 에이전트의 집(home)** 이다. 파일 도구들의 작업 디렉터리이자 세션 컨텍스트의 원천이고, "비공개로 유지하고 메모리처럼 다루라"고 안내한다. 기본 위치는 `~/.openclaw/workspace`.[^ws]

세션이 시작될 때 OpenClaw 는 이 안의 표준 파일들을 읽어 프롬프트에 주입(bootstrap)한다. 파일 하나당 기본 20,000자, 전체 60,000자 한도로 잘라 넣고, 필수 파일이 없으면 에러 대신 "missing file" 마커를 끼워 넣고 계속 진행한다.[^ws] 즉 이 파일들이 곧 에이전트의 시스템 프롬프트 재료다.

## 파일별 역할

| 파일 | 역할 | 언제 읽히나 |
|---|---|---|
| `AGENTS.md` | 운영 지침 — 규칙·우선순위·절차 | 매 세션 |
| `SOUL.md` | 페르소나·톤·경계 | 매 세션 |
| `IDENTITY.md` | 이름·바이브·이모지 | 부트스트랩 의식에서 생성·갱신 |
| `USER.md` | 사용자 모델 (선택) | 매 세션, 별도 4,000자 예산 |
| `memory/YYYY-MM-DD.md` | 일일 메모리 로그 | 메모리 도구가 필요할 때 검색 |
| `MEMORY.md` | 큐레이션된 장기 기억 (선택) | 메인 비공개 세션에서만 |
| `skills/` | 워크스페이스 스킬 (선택) | 스킬 시스템이 로드 |
| `HEARTBEAT.md` | 하트비트 체크리스트 | 기본 30분 틱마다 (버전 주의, 후술) |

몇 가지는 부연이 필요하다.

**`SOUL.md` — 인격의 자리.** 페르소나, 톤, 행동 경계를 담고 매 세션 로드된다.[^ws] 템플릿 자체가 "이 파일은 네 것이니, 네가 누구인지 알게 되는 대로 스스로 갱신하라"고 에이전트에게 말을 건다.[^soul] 절차·워크플로는 여기 넣지 않는 게 관례다 — 그건 `AGENTS.md` 소관이다.

**`IDENTITY.md` — 명함.** 이름·바이브·이모지·아바타. 첫 실행의 부트스트랩 의식(bootstrap ritual)에서 만들어지고, `- Label: value` 줄 단위로 파싱된다. 재미있는 디테일: `Theme`/`Creature`/`Vibe` 세 필드가 같은 "효과적 정체성" 값 하나로 합쳐지는데 우선순위는 Theme > Creature > Vibe 다.[^id]

**`USER.md` — 에이전트가 아는 나.** 안정적인 선호·소통 스타일·관계·진행 중 프로젝트를 담는 사용자 모델이다. 핵심 규율이 둘 있다: ① 관찰이 아니라 **지시문(directive)으로 쓴다** — 날짜 붙은 active/superseded 항목으로. ② 선호가 바뀌면 새 줄을 덧붙이지 말고 **기존 항목을 제자리에서 대체한다.** 일반 파일보다 일부러 작은 4,000자 예산이 따로 잡혀 있어 비대해지면 낡은 항목을 지우라는 압력이 구조에 박혀 있다.[^um]

**`memory/` 와 `MEMORY.md` — 이중 기억.** 상세 로그는 날짜별 `memory/YYYY-MM-DD.md` 에 쌓고, `MEMORY.md` 에는 오래 가는 사실·결정·요약만 큐레이션해 올린다. 전자는 매 프롬프트에 주입되지 않고 메모리 도구가 필요할 때 꺼내 오며, 후자는 **메인 비공개 세션에서만 로드**된다 — 그룹 채팅 세션에 개인 기억이 새지 않게 하는 설계다.[^ws]

**`HEARTBEAT.md` — 심장박동.** 에이전트를 30분마다(기본값; Anthropic OAuth/토큰 인증이면 1시간) 깨우는 하트비트 틱에서 읽히는 체크리스트다.[^hb] 안에 `tasks:` 블록을 두면 태스크별 주기(30m, 2h…)를 따로 걸 수 있고, 해당 틱에 만기(due)인 태스크가 하나도 없으면 모델 호출 자체를 건너뛴다 — 빈 하트비트로 토큰을 태우지 않는 장치다.[^hb]

## 빈 템플릿은 고장이 아니다

샌드박스에서 확인한 상태 — `IDENTITY.md`/`USER.md` 는 빈 템플릿, `memory/`/`skills/` 는 빈 디렉터리 — 는 신선한 워크스페이스의 정상 모습이다. `IDENTITY.md` 는 부트스트랩 의식이 에이전트와의 첫 대화에서 채우도록 설계돼 있고, `USER.md`/`MEMORY.md` 는 없으면 조용히 생략되는 선택 파일이다.[^ws] 인격은 설치 시점에 주어지는 게 아니라 첫 세션에서 "태어나는" 구조다.

한 가지 버전 함정: 최신 문서 기준으로 `HEARTBEAT.md` 는 **은퇴 수순**이다. 하트비트 지시는 상태 DB 의 모니터 스크래치로 옮겨 갔고, `openclaw doctor --fix` 가 기존 파일을 임포트·아카이브한 뒤 삭제하며, 그 이후 런타임은 이 파일을 읽지 않는다.[^hb-retired] 지금 샌드박스처럼 파일이 살아서 30분마다 읽히는 건 그 이전 동작이다 — 버전에 따라 이 파일의 지위가 다르다는 걸 알고 봐야 한다.

## 워크스페이스 ≠ 샌드박스

가장 오해하기 쉬운 지점. 공식 문서가 명시한다: **"워크스페이스는 기본 작업 디렉터리이지, 강한 샌드박스가 아니다."** 상대 경로는 워크스페이스 기준으로 풀리지만, 절대 경로는 샌드박싱을 켜지 않는 한 호스트의 다른 곳에 그대로 닿는다.[^ws]

격리가 필요하면 `agents.defaults.sandbox` 를 별도로 켜야 한다 — 그리고 이건 **기본값이 off** 다.[^sbx] 켜면 Docker 백엔드 기준으로 network `none`, capability 전체 드롭, 읽기 전용 루트라는 꽤 보수적인 기본값으로 도구 실행만 컨테이너로 들어간다(Gateway 프로세스는 호스트에 남는다). 이때 워크스페이스 파일들이 샌드박스에서 어떻게 보이는지는 `workspaceAccess` 가 정한다:[^sbx]

- `none`(기본) — 에이전트 워크스페이스는 아예 안 보이고, `~/.openclaw/sandboxes` 아래 격리된 별도 워크스페이스를 쓴다. 스킬은 읽을 수 있게 샌드박스 쪽으로 미러링된다.
- `ro` — 워크스페이스가 `/agent` 에 읽기 전용 마운트. 쓰기 도구는 거부된다.
- `rw` — `/workspace` 에 읽기/쓰기 마운트.

즉 "샌드박스에서 이 문서들을 읽었다"는 건 설정에 따라 의미가 달라진다 — 진짜 에이전트의 집을 본 것일 수도, 격리용 사본 워크스페이스를 본 것일 수도 있다.

## 정리 — 인격을 git 으로 관리한다는 것

이 설계의 요점은 에이전트의 정체성·기억·스케줄이 전부 **버전 관리 가능한 플레인 텍스트**라는 것이다. 실제로 공식 문서의 백업 안내가 `git init` 후 `AGENTS.md SOUL.md IDENTITY.md USER.md memory/` 를 커밋하라는 것이다.[^ws] 인격을 diff 로 리뷰하고, 기억을 커밋 히스토리로 되짚고, 워크스페이스를 통째로 복제해 에이전트를 이사시킬 수 있다. 반대급부도 같은 자리에서 나온다 — 전부 평문이므로 비밀은 절대 이 파일들에 넣으면 안 되고, `USER.md` 는 실제 개인 정보가 담기는 파일이라 워크스페이스 자체를 비공개로 유지하라는 게 공식 안내다.[^ws]

에이전트 프레임워크들이 인격과 기억을 어디에 두는가는 저마다 답이 다르다. OpenClaw 의 답은 가장 유닉스적이다: 전부 파일이다. 그리고 파일이라서, 샌드박스에 앉아 `cat` 몇 번으로 에이전트의 영혼을 열람할 수 있었던 것이다.

---

## References

[^ws]: OpenClaw 공식 문서, "Agent workspace" — 워크스페이스 정의·파일 맵·부트스트랩 예산·git 백업 안내·"not a hard sandbox" 명시. <https://docs.openclaw.ai/agent-workspace>
[^soul]: OpenClaw 공식 문서, "SOUL.md template". <https://docs.openclaw.ai/reference/templates/SOUL>
[^id]: OpenClaw 공식 문서, "IDENTITY template" — `- Label: value` 파싱, Theme/Creature/Vibe 우선순위. <https://docs.openclaw.ai/reference/templates/IDENTITY>
[^um]: OpenClaw 공식 문서, "User model" — directive 작성 규칙, supersede-in-place, 4,000자 예산. <https://docs.openclaw.ai/concepts/user-model>
[^hb]: OpenClaw 공식 문서(구버전 포함), "Heartbeat" — 기본 30m(Anthropic OAuth 시 1h), `tasks:` 블록, no-tasks-due 스킵. <https://docs.openclaw.ai/gateway/heartbeat>
[^hb-retired]: OpenClaw 공식 문서, "Retired HEARTBEAT.md workspace file" — 모니터 스크래치 이관, `openclaw doctor --fix` 마이그레이션. <https://docs2.openclaw.ai/reference/templates/HEARTBEAT>
[^sbx]: OpenClaw 공식 문서, "Sandboxing" — 기본 off, mode/scope/backend, workspaceAccess none/ro/rw, Docker 기본 network none. <https://docs.openclaw.ai/gateway/sandboxing>
