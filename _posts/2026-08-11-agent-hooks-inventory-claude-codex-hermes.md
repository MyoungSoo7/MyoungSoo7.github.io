---
layout: post
title: "에이전트 하네스에 훅을 심는다는 것: Claude Code·Codex·Hermes 세 하네스 훅 전수 조사"
date: 2026-08-11 01:20:00 +0900
categories: [ai-agent, devops, tooling]
tags:
  [
    Claude Code,
    Codex,
    Hermes,
    hooks,
    PreToolUse,
    UserPromptSubmit,
    멀티에이전트,
    상호배제,
  ]
---

에이전트를 오래 쓰다 보면 같은 결론에 도달한다. **문서에 적어둔 규율은 지켜지지 않는다.**

CLAUDE.md 에 "프로덕션 클러스터를 만지기 전에 다른 세션과 겹치는지 확인하라"고 적어두면, 모델은 대체로 지킨다. 그런데 '대체로'가 문제다. 컨텍스트가 길어지면 잊고, 급하면 건너뛰고, 세션을 새로 열면 아예 모른다. LLM 의 규율은 **확률적**이다.

훅(hook)은 그 확률을 1 또는 0으로 만드는 장치다. 모델의 선의가 아니라 하네스의 프로세스 실행으로 강제되기 때문이다.

이 글은 개인 맥 한 대에서 Claude Code · Codex CLI · Hermes 세 하네스가 실제로 물고 있는 훅을 **전수 조사한 기록**이다. 설정 파일을 읽어 하나씩 확인했고, 파일 경로와 등록 개수를 그대로 적었다.

---

## 1. 먼저, 훅의 계약을 정확히 알아야 한다

훅을 잘못 만들면 에이전트가 아예 멈춘다. 그래서 공식 문서의 계약부터 정확히 짚는다.

Claude Code 훅은 "세션 수명주기의 특정 지점에서 자동 실행되는 사용자 정의 셸 명령·HTTP 엔드포인트·LLM 프롬프트"다. 이벤트는 세 가지 케이던스로 나뉜다 ([Claude Code Hooks reference][docs-hooks]).

| 케이던스    | 이벤트                                    |
| ----------- | ----------------------------------------- |
| 세션당 1회  | `SessionStart`, `SessionEnd`              |
| 턴당 1회    | `UserPromptSubmit`, `Stop`, `StopFailure` |
| 툴 호출마다 | `PreToolUse`, `PostToolUse`               |

핵심은 **종료 코드 규약**이다. 공식 문서를 그대로 인용하면:

> **Exit 0 (Success)** — Claude Code parses stdout for JSON output fields. (…) For most events, stdout is written to the debug log but not shown in the transcript. The exceptions are `UserPromptSubmit`, `UserPromptExpansion`, and `SessionStart`, where **stdout is added as context that Claude can see and act on**.
>
> **Exit 2 (Blocking Error)** — Claude Code ignores stdout and any JSON in it. Instead, **stderr text is fed back to Claude as an error message**. The effect depends on the event: `PreToolUse` blocks the tool call, `UserPromptSubmit` rejects the prompt, and so on.
>
> **Any other exit code** is a non-blocking error for most hook events. The action proceeds (…)
>
> — [Claude Code Hooks reference, Exit Codes and Output Handling][docs-hooks]

여기서 훅 설계의 두 가지 축이 나온다.

- **주입(inject)**: `UserPromptSubmit` / `SessionStart` 에서 exit 0 + stdout → 그대로 컨텍스트가 된다. 모델이 뭔가를 _기억할 필요가 없어진다._
- **차단(block)**: `PreToolUse` 에서 exit 2 + stderr → 툴 호출이 막히고, 이유가 모델에게 전달된다.

그리고 `async: true` 필드가 있다. 문서 표현으로는 "If `true`, runs in the background without blocking." 느린 훅(텔레그램 알림, 상태 파일 갱신)은 반드시 여기에 둬야 턴 지연이 없다.

---

## 2. 계층 1 — 글로벌 Claude Code (`~/.claude/settings.json`)

가장 많은 훅이 여기 있다. 이벤트 등록 **10건**, 서로 다른 스크립트 **9개**(`claude-ctx-watch.sh` 는 `Stop` 과 `PreCompact` 양쪽에 등록돼 있어 2번 세어진다).

### 2-1. `PreToolUse` (matcher: `Bash`) — 3건

| 스크립트                               | 하는 일                             | 차단 여부           |
| -------------------------------------- | ----------------------------------- | ------------------- |
| `hooks/bash-danger-check.sh`           | 위험 명령 패턴 검사                 | **exit 2 로 차단**  |
| `hooks/cluster-coordinator.sh` → `.py` | 세션 간 클러스터 작업 상호배제      | **exit 2 로 차단**  |
| `rtk hook claude`                      | 명령 출력 토큰 절감 프록시로 재작성 | 재작성만, 차단 없음 |

`bash-danger-check.sh` 는 jq 가 있으면 jq 로, 없으면 grep 폴백으로 `.tool_input.command` 를 뽑아 두 종류의 패턴을 본다.

```bash
# 하드 블록 (exit 2)
block_patterns=(
  'rm[[:space:]]+-rf?[[:space:]]+/($|[[:space:]])'
  'rm[[:space:]]+-rf?[[:space:]]+~($|[[:space:]/])'
  ':\(\)\{[[:space:]]*:\|:&[[:space:]]*\};:'   # fork bomb
  'mkfs\.'
  'dd[[:space:]]+if=.*of=/dev/(sd|nvme|disk)'
  'shutdown[[:space:]]' 'reboot[[:space:]]*$'
)

# 경고만 하고 통과 (exit 0, stderr)
warn_patterns=(
  'git[[:space:]]+push[[:space:]]+.*--force'
  'git[[:space:]]+reset[[:space:]]+--hard'
  'curl[[:space:]]+.*\|[[:space:]]*(bash|sh)'
)
```

여기서 배울 점은 **차단과 경고를 분리했다는 것**이다. `git push --force` 를 하드 블록으로 두면 정당한 작업까지 막혀 훅을 통째로 꺼버리게 된다. 꺼진 훅은 없는 훅이다.

### 2-2. `UserPromptSubmit` — 2건 (둘 다 컨텍스트 주입형)

```bash
# hooks/inject-datetime.sh — stdout 이 그대로 컨텍스트가 된다
cat <<EOF
<current-datetime>
ISO: $(date '+%Y-%m-%d %H:%M:%S %z')
Human: $(date '+%A, %B %d, %Y at %I:%M %p')
Timezone: $(date '+%Z')
</current-datetime>
EOF
```

LLM 은 "지금 몇 시인지"를 모른다. 학습 시점 이후를 알 수 없고, 세션 중 시간이 흐르는 것도 모른다. 이 다섯 줄이 그 문제를 영구히 없앤다. **훅으로 해결할 수 있는 문제를 프롬프트로 해결하려 하지 않는 것**이 원칙 하나다.

두 번째는 `bot-status-inject.py` — 같은 맥에서 도는 여러 에이전트 세션이 서로 뭘 하는지 보게 한다.

```python
me = session_id()
others = read_others(me)      # 남의 상태를 먼저 읽고
write_status(me, "working", prompt)   # 내 상태를 쓴다
block = render(others)
if block:
    print(block)              # stdout → 컨텍스트
```

주석에 설계 의도가 남아 있다. _"재시작 직후 첫 메시지부터 다른 봇이 뭘 하는지 보인다. 모델이 뭔가를 기억할 필요가 없다."_ 그리고 결정적으로 — **실패해도 절대 프롬프트를 막지 않는다.** 전체가 `try/except` 로 감싸여 있고 무슨 일이 있어도 `sys.exit(0)` 이다. `UserPromptSubmit` 에서 exit 2 는 프롬프트를 지워버리기 때문이다.

### 2-3. `Stop` — 3건 / `PreCompact` — 1건

| 스크립트                              | 하는 일                                         | 모드          |
| ------------------------------------- | ----------------------------------------------- | ------------- |
| `inter-asat/scripts/update-status.sh` | 14개 프로젝트 STATUS.md 자동 갱신               | `async: true` |
| `bin/claude-ctx-watch.sh`             | 컨텍스트 사용량 70/80/90% 진입 시 텔레그램 알림 | `async: true` |
| `hooks/bot-status-idle.py`            | 이 세션을 idle 로 표시                          | 동기 (5s)     |

`claude-ctx-watch.sh` 는 transcript 의 마지막 assistant 메시지 usage 에서 컨텍스트 크기를 계산한다.

```
컨텍스트 크기 = input_tokens + cache_creation_input_tokens + cache_read_input_tokens
```

output 토큰을 더하지 않는 이유가 스크립트 주석에 있다. _"output 은 다음 턴 입력으로 들어가므로 다음 usage 에 이미 반영됨."_ 중복 계산을 피한 것이다. 그리고 버킷(70/80/90%)마다 **1회만** 알린다 — 매 턴 알리면 알림이 노이즈가 되어 무시된다.

### 2-4. `PostToolUse` (matcher: `Edit|Write`) — 1건

`hooks/prettier-format.sh` 는 편집된 파일의 디렉터리에서 위로 올라가며 `node_modules/.bin/prettier` 를 찾고, 없으면 PATH 의 전역 prettier 로 폴백하고, 그것도 없으면 **조용히 exit 0** 한다. prettier 가 없는 리포에서 매 편집마다 에러를 뱉지 않기 위해서다.

---

## 3. 계층 2 — Codex CLI (`~/.codex/hooks.json`)

Codex 쪽은 훨씬 얇다. 등록 **2건**뿐이다.

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "bash '/Users/lms/.codex/hooks/bash-danger-check.sh'",
            "timeout": 5
          }
        ]
      }
    ],
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "bash '/Users/lms/.codex/hooks/inject-datetime.sh'",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```

`~/.codex/hooks/` 에는 스크립트가 3개(`bash-danger-check.sh`, `inject-datetime.sh`, `prettier-format.sh`) 있는데 **prettier 는 배선되지 않았다.** 파일이 있다고 도는 게 아니다 — 훅 감사에서 가장 흔한 착각이 이것이다. 디렉터리를 보고 "3개 돌고 있네"라고 결론 내리면 틀린다. 반드시 설정 파일에서 등록 여부를 확인해야 한다.

Codex 의 훅 스크립트 3개는 Claude 쪽 `~/.claude/hooks/` 의 동명 파일과 크기·타임스탬프가 같다(모두 2054 / 406 / 1458 바이트, 4월 7일). **복사본**이다. 여기서 이 구성의 첫 번째 약점이 드러난다 — 한쪽을 고치면 다른 쪽은 낡는다. 이 문제를 제대로 푼 사례가 바로 다음 계층이다.

---

## 4. 계층 3 — Hermes, 그리고 세 하네스가 공유하는 하나의 락

Hermes(개인 에이전트 게이트웨이)는 `~/.hermes/config.yaml` 에 훅을 **딱 하나** 물고 있다.

```yaml
hooks:
  pre_tool_call:
    - matcher: terminal
      command: /usr/bin/python3 /Users/lms/.hermes/agent-hooks/cluster-coordinator.py
      timeout: 10
hooks_auto_accept: true
```

Hermes 는 훅 스크립트를 승인 목록으로 관리한다. `~/.hermes/shell-hooks-allowlist.json` 에 **승인 시점의 스크립트 mtime** 이 함께 기록된다.

```json
{
  "approvals": [
    {
      "approved_at": "2026-08-03T21:19:41Z",
      "command": "/usr/bin/python3 /Users/lms/.hermes/agent-hooks/cluster-coordinator.py",
      "event": "pre_tool_call",
      "script_mtime_at_approval": "2026-08-03T21:17:27Z"
    }
  ]
}
```

승인 후 스크립트가 바뀌면 재승인을 요구하겠다는 설계다. 훅은 임의 코드 실행이므로 이 정도 방어는 정당하다.

### 4-1. 어댑터/코어 분리 — 이 구성에서 가장 잘 된 부분

같은 이름의 `cluster-coordinator.py` 가 Claude(`~/.claude/hooks/`)와 Hermes(`~/.hermes/agent-hooks/`) 양쪽에 있다. 그런데 Codex 훅처럼 복사본이 아니다. 둘 다 **같은 코어 모듈 하나**를 import 한다.

```python
"""
cluster_lock_core.py — Claude Code 세션들과 Hermes 가 *공유* 하는
클러스터 작업 상호배제 코어.

두 하네스의 훅 어댑터가 이 모듈만 쓴다:
  - ~/.claude/hooks/cluster-coordinator.py       (Claude Code PreToolUse, block = exit 2)
  - ~/.hermes/agent-hooks/cluster-coordinator.py (Hermes pre_tool_call,   block = stdout JSON)

같은 레지스트리(~/.claude/locks/active-tasks.jsonl) 와 같은 (action,target) 키를 쓰므로
Claude ↔ Hermes 사이에서도 양방향으로 경합이 막힌다.
"""
```

구조가 명확하다.

```
              ┌─────────────────────────────┐
Claude Code ──┤ cluster-coordinator.py      │──┐
(PreToolUse)  │  exit 2 + stderr            │  │
              └─────────────────────────────┘  │   ┌──────────────────────┐
                                               ├──►│ cluster_lock_core.py │
              ┌─────────────────────────────┐  │   │  parse_command()     │
Hermes ───────┤ cluster-coordinator.py      │──┘   │  claim(TTL)          │
(pre_tool_call)│ stdout JSON                │      └──────────┬───────────┘
              └─────────────────────────────┘                 │
                                                              ▼
                                        ~/.claude/locks/active-tasks.jsonl
                                        (fcntl 파일 락, TTL 60s)
```

**훅 어댑터는 하네스의 입출력 규약만 담당하고, 판단 로직은 하네스 중립 코어에 둔다.** 하네스마다 차단 방식이 다르다 — Claude 는 exit 2 + stderr, Hermes 는 stdout JSON. 그 차이를 어댑터가 흡수하니 정책은 한 곳에서만 고치면 된다. Codex 의 복사본 방식과 정확히 대비된다.

### 4-2. 무엇을 잡아채는가

```python
매칭: ssh(노드 IP/alias)
    · kubectl write(delete/drain/cordon/uncordon/apply/patch/replace/scale/edit/rollout restart)
    · helm write
차단: exit 2 + stderr        우회: CLAUDE_COORDINATOR_SKIP=1
세션 식별: CLAUDE_PROJECT_DIR 또는 cwd 의 basename
```

차단 메시지는 이렇게 나간다.

```
[cluster-coordinator] 🔒 BLOCKED
다른 세션 'telegram-bot3' 가 12s 전에 동일 작업(kubectl-write:settlement-prod) 을 시작했습니다.
중복 가능성. 60s 후 자동 해제. 정말 필요하면 사용자 확인 후 CLAUDE_COORDINATOR_SKIP=1 prefix.
```

세 가지 설계 판단이 들어 있다.

1. **TTL 60초 자동 해제.** 세션이 죽어도 락이 영구히 남지 않는다. 크래시하는 에이전트에게 영구 락은 재앙이다.
2. **명시적 우회 경로.** 훅이 틀렸을 때 빠져나갈 문이 없으면 사람은 훅을 삭제한다. `CLAUDE_COORDINATOR_SKIP=1` 이 그 문이다.
3. **세션 정체성 = 디렉터리 이름.** PID 나 세션 UUID 가 아니다. 그래서 세션을 재시작해도 정체성이 유지된다. 재시작에 견디는 식별자를 고르는 것이 멀티에이전트 조율의 기본기다.

---

## 5. 계층 4 — 프로젝트 로컬 훅

`~/*/.claude/settings.json` 을 훑어 훅이 있는 파일 **15개**를 찾았다. 성격이 뚜렷하게 갈린다.

### 5-1. settlement — "문서 규율의 기계화"

```json
{
  "PreToolUse": [
    {
      "matcher": "Write|Edit|MultiEdit",
      "hooks": [
        {
          "command": "node \"$CLAUDE_PROJECT_DIR/scripts/harness/guard.mjs\" --hook"
        }
      ]
    },
    {
      "matcher": "Write|Edit|MultiEdit|Skill",
      "hooks": [
        {
          "command": "node \"$CLAUDE_PROJECT_DIR/scripts/harness/skill-router.mjs\" --hook"
        }
      ]
    }
  ],
  "SessionStart": [
    {
      "hooks": [
        {
          "command": "node \"$CLAUDE_PROJECT_DIR/scripts/harness/telemetry-report.mjs\" --hook"
        }
      ]
    }
  ]
}
```

`skill-router.mjs` 의 헤더 주석이 이 계층의 존재 이유를 가장 잘 설명한다.

> CLAUDE.md / HARNESS.md 라우팅 표("X-service 를 만지면 해당 `*-rules` 스킬 로드")는 지금까지 **LLM 이 기억해서 지키는 문서 규율**이었다. 이 훅은 그 권장을 기계화한다: 편집 대상 경로를 보고 해당 규칙 스킬 로드를 `additionalContext` 리마인더로 주입한다(세션당 스킬별 1회 — 스팸 방지).

"세션당 스킬별 1회"라는 디테일이 중요하다. 리마인더를 매번 주입하면 컨텍스트를 먹고, 반복되면 모델이 무시한다.

`guard.mjs` 는 왜 리포에 직접 두었는지를 주석에 남겼다.

> Why this exists: the settlement-copilot / invest-copilot **plugin guards live outside the build graph** (…) and are not wired into CI on a fresh clone.

플러그인에 의존한 가드는 클론한 사람 환경에서 사라진다. 그래서 리포에 추적되는 파일로 옮겼다. 같은 설정이 settlement 본체 + 워크트리 7개에 동일하게 들어 있다.

### 5-2. eln-convenient — 리마인더 4종 (`PostToolUse: Write|Edit`)

| 훅                             | 트리거                    | 목적                         |
| ------------------------------ | ------------------------- | ---------------------------- |
| `check-i18n-sync.sh`           | i18n 로케일 파일 편집     | ko/en 키 동기화 확인         |
| `rebuild-reminder.sh`          | `services/*/src/` 편집    | docker rebuild 리마인더      |
| `prisma-migration-reminder.sh` | `schema.prisma` 편집      | 마이그레이션 리마인더        |
| `check-compose-env.sh`         | `docker-compose.yml` 편집 | 필수 환경변수·포트 충돌 검증 |

전부 **"편집했으면 반드시 뒤따라야 하는 후속 작업"** 을 잡는다. 사람도 에이전트도 똑같이 잊는 종류의 것들이다.

### 5-3. 나머지

| 리포                                      | 이벤트                             | 훅                                                            |
| ----------------------------------------- | ---------------------------------- | ------------------------------------------------------------- |
| ouroboros / ouroboros-pr / ouroboros-main | `UserPromptSubmit` / `PostToolUse` | `keyword-detector.py` (매직 키워드 감지) / `drift-monitor.py` |
| inter-asat                                | `PostToolUse`                      | CLAUDE.md·STATUS.md·agents 편집 시 하네스 drift 검사          |
| sparta-msa-project                        | `SessionStart`                     | STATUS.md 자동 갱신(브랜치·최근 커밋 5개)                     |
| oh-my-openagent                           | `SessionStart` / `SessionEnd`      | 개발환경 bootstrap / cleanup                                  |

`inter-asat` 의 것은 인라인 bash 로 짧게 끝냈다.

```bash
f="$CLAUDE_FILE_PATHS"
case "$f" in
  *CLAUDE.md*|*STATUS.md*|*.claude/agents/*|*HARNESS.md*)
    bash scripts/harness-check.sh --quiet 2>&1 || echo "⚠ 하네스 drift 감지" ;;
esac
```

`oh-my-openagent` 의 `setup.sh` 는 한 스크립트를 Codex App(`.codex/setup.sh`) · Cursor(`.cursor/environment.json`) · Claude Code(`.claude/settings.json`) 세 하네스가 공유한다. 4-1 의 어댑터/코어 분리와 같은 사고방식이다.

---

## 6. 전체 요약

| 계층               | 위치                           | 등록 수                          | 성격                      |
| ------------------ | ------------------------------ | -------------------------------- | ------------------------- |
| 글로벌 Claude Code | `~/.claude/settings.json`      | 10건 / 스크립트 9개              | 안전·주입·관측            |
| Codex CLI          | `~/.codex/hooks.json`          | 2건 (스크립트 3개 중 1개 미배선) | 안전·주입 (Claude 복사본) |
| Hermes             | `~/.hermes/config.yaml`        | 1건 + allowlist 승인             | 상호배제                  |
| 프로젝트 로컬      | `*/.claude/settings.json` 15개 | 리포당 1~4건                     | 규율 기계화               |

이벤트별로 다시 보면 목적이 선명하게 갈린다.

| 이벤트                        | 이 맥에서의 용도                                     |
| ----------------------------- | ---------------------------------------------------- |
| `UserPromptSubmit`            | 컨텍스트 주입 — 현재 시각, 다른 봇 상태, 매직 키워드 |
| `PreToolUse`                  | 차단 — 위험 명령, 세션 간 클러스터 경합, 리포 불변식 |
| `PostToolUse`                 | 후속 리마인더 — 포맷팅, i18n, 마이그레이션, drift    |
| `Stop` / `PreCompact`         | 관측 — 컨텍스트 사용량 알림, STATUS 갱신, idle 표시  |
| `SessionStart` / `SessionEnd` | 준비·정리 — 환경 bootstrap, 텔레메트리 리포트        |

---

## 7. 반복해서 나타난 설계 원칙 6가지

1. **주입은 `UserPromptSubmit`, 차단은 `PreToolUse`.** 모델이 기억해야 하는 것은 주입으로, 하면 안 되는 것은 차단으로. 프롬프트에 적어 부탁하는 것은 마지막 수단이다.
2. **주입형 훅은 절대 실패하지 않는다.** `bot-status-inject.py` 는 전체가 try/except 이고 무조건 exit 0 이다. `UserPromptSubmit` 에서 exit 2 는 사용자의 프롬프트를 지운다.
3. **차단과 경고를 분리한다.** 정당한 작업까지 막는 훅은 결국 꺼진다. 꺼진 훅은 없는 훅이다.
4. **모든 락에는 TTL 과 명시적 우회 경로.** 크래시하는 에이전트에게 영구 락은 재앙이고, 탈출구 없는 훅은 삭제된다.
5. **어댑터와 코어를 분리한다.** 하네스별 입출력 규약(exit 2 vs stdout JSON)은 얇은 어댑터가 흡수하고, 판단 로직은 하네스 중립 코어 하나에. Codex 의 복사본과 `cluster_lock_core.py` 의 차이가 정확히 이 지점이다.
6. **정체성은 재시작에 견디는 값으로.** PID·세션 UUID 가 아니라 디렉터리 이름.

---

## 8. 이 구성의 약점 — 정직하게

전수 조사를 하니 문제도 같이 보였다.

- **Codex 훅은 Claude 훅의 복사본이다.** 한쪽을 고치면 다른 쪽이 낡는다. `cluster_lock_core.py` 처럼 코어를 공유하도록 바꾸는 것이 맞다.
- **`~/.codex/hooks/prettier-format.sh` 는 배선되어 있지 않다.** 존재하지만 돌지 않는다. 디렉터리만 보고 판단하면 틀린다.
- **`cluster-coordinator.py.bak.20260804_061653` 같은 백업 파일이 훅 디렉터리에 남아 있다.** 지금은 무해하지만(설정에서 참조하지 않음), 훅 디렉터리에 실행 권한 있는 옛 버전을 남기는 건 좋은 습관이 아니다.
- **훅 실행 실패의 관측 수단이 약하다.** exit 0 훅의 stderr 는 디버그 로그로만 가고 모델도 사용자도 보지 못한다([문서][docs-hooks]). 조용히 죽은 주입형 훅은 발견하기 어렵다.

마지막 항목이 가장 위험하다. **차단형 훅은 고장 나면 티가 나지만(작업이 막힌다), 주입형 훅은 고장 나도 티가 안 난다.** 그냥 컨텍스트가 조금 부족해질 뿐이고, 그 결과는 모델이 조금 더 자주 틀리는 것으로만 나타난다. 주입형 훅을 늘릴수록 "이 훅이 지금도 도는가"를 확인하는 수단이 필요해진다.

---

## References

- Anthropic, _Claude Code Hooks reference_ — 이벤트 목록, 종료 코드 규약, `async`/`asyncRewake` 필드. [https://code.claude.com/docs/en/hooks][docs-hooks]
- Anthropic, _Automate actions with hooks_ (quickstart). <https://code.claude.com/docs/en/hooks-guide>
- 본문의 훅 목록·개수·인용된 주석은 2026-08-11 기준 로컬 머신의 `~/.claude/settings.json`, `~/.codex/hooks.json`, `~/.hermes/config.yaml`, 각 리포의 `.claude/settings.json` 을 직접 읽어 확인한 것이다. 공개 배포된 구성이 아니므로 제3자가 재현·검증할 수 없다는 점을 밝혀 둔다. 재현 가능한 부분은 위 공식 문서의 훅 계약뿐이다.

[docs-hooks]: https://code.claude.com/docs/en/hooks
