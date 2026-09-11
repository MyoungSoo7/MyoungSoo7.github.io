---
layout: post
title: "이름은 같고 계약은 다르다 — Claude Code와 Codex 훅 공식문서 비교"
date: 2026-09-11 23:57:40 +0900
categories: [dev]
tags: [claude-code, codex, hooks, agent, cli]
---

작년 여름에 같은 주제로 한 번 썼다. 그때 결론은 "Claude Code는 이음새가 서른 개고, Codex는
의도적으로 성기다" 였다. 2026년 9월 지금 다시 재보니 그 문장은 절반이 틀렸다.
Codex에도 훅이 정식으로 들어왔고, **이벤트 이름이 Claude Code와 거의 똑같다.**

그런데 이름이 같다고 같은 물건이 아니다. 공식문서를 나란히 놓고 보면, 실제로 사람들이 주로 쓰는
대여섯 개 훅에서 **차단 방식·출력 JSON 모양·타임아웃·신뢰 승인 절차가 전부 조금씩 다르다.**
이 글은 두 제품의 공식 레퍼런스만 근거로 그 차이를 정리한 것이다.

기준 문서는 두 개다.

- Claude Code: [Hooks reference](https://code.claude.com/docs/en/hooks) (code.claude.com)
- Codex: [Hooks](https://developers.openai.com/codex/hooks) (developers.openai.com/codex,
  현재 learn.chatgpt.com/docs/hooks 로 리다이렉트)

---

## 1. 이벤트 목록 — Codex 12개는 Claude의 부분집합에 가깝다

Codex 공식문서는 훅이 도는 시점을 이렇게 나눈다.

> | When | Hooks |
> | --- | --- |
> | During a turn | `PreToolUse`, `PermissionRequest`, `PostToolUse`, `PreCompact`, `PostCompact`, `UserPromptSubmit`, `SubagentStop`, `Stop` |
> | When a session or subagent starts | `SessionStart`, `SubagentStart` |
> | When the main thread ends | `SessionEnd` (doesn't run for subagents) |

여기에 타임아웃 항목에서만 언급되는 `Interrupt` 를 더하면 12개다.

이 12개 중 `Interrupt` 를 뺀 11개는 **전부 Claude Code에도 같은 이름으로 있다.** 반대로
Claude Code 레퍼런스에는 그 11개 말고도 `Setup`, `StopFailure`, `PermissionDenied`,
`PostToolUseFailure`, `PostToolBatch`, `TaskCreated`, `TaskCompleted`, `WorktreeCreate`,
`WorktreeRemove`, `Notification`, `ConfigChange`, `InstructionsLoaded`, `CwdChanged`,
`FileChanged`, `DirectoryAdded`, `TeammateIdle`, `PreModelSwitch`, `PostModelSwitch`,
`MessageDisplay`, `Elicitation`, `ElicitationResult`, `UserPromptExpansion` 이 더 있다.

즉 **표면적이 3배쯤 차이 나되, 겹치는 쪽은 이름까지 같다.** 이건 우연이 아니다. Codex 문서는
플러그인 훅의 환경변수로 `PLUGIN_ROOT` / `PLUGIN_DATA` 를 주면서
`CLAUDE_PLUGIN_ROOT` / `CLAUDE_PLUGIN_DATA` 를 "legacy compatibility" 로 같이 넣어 준다고
적는다. Claude 플러그인 포맷을 그대로 먹겠다는 뜻이다.

<small>(실측 보조 — 내 맥의 Codex 0.152.1은 Claude 플러그인 포맷으로 배포된 훅을
`superpowers@claude-plugins-official:hooks/hooks.json:session_start` 같은 키로 실제로 로드해 두고 있다.
아래 6절 참고.)</small>

---

## 2. 주로 쓰는 훅 6종 — 같은 이름, 다른 계약

실무에서 실제로 손이 가는 훅은 몇 개 안 된다. 위험한 명령 차단(`PreToolUse`),
프롬프트에 컨텍스트 주입(`UserPromptSubmit`), 편집 후 포맷·린트(`PostToolUse`),
세션 부팅(`SessionStart`), 턴 종료 검증(`Stop`), 압축 전후(`PreCompact`/`PostCompact`).
이 여섯 자리에서 두 문서가 어떻게 갈리는지가 이 글의 본론이다.

### 차단 가능 여부와 방법

각 제품 문서가 **자기 표에 스스로 적어 둔 대로** 옮기면 이렇다.

| 이벤트 | Claude Code 공식 | Codex 공식 |
| --- | --- | --- |
| `PreToolUse` | 차단 O — exit 2 로 도구 호출 차단 | 차단 O — `permissionDecision: "deny"` 또는 exit 2 |
| `UserPromptSubmit` | 차단 O — exit 2 로 프롬프트 처리 차단 | 차단 O — `decision: "block"` 또는 exit 2 |
| `PostToolUse` | **차단 X — 도구가 이미 실행됨** | **차단 O(실행 후) — `decision: "block"` 이 도구 결과를 대체** |
| `SessionStart` | 차단 X | **차단 O — `continue: false`** |
| `Stop` / `SubagentStop` | 차단 O — exit 2 로 종료를 막음 | 차단 X(계속 진행만) — `decision: "block"` 이면 멈추는 대신 이어감 |
| `PreCompact` / `PostCompact` | 차단 X | 차단 O — `continue: false` |
| `PermissionRequest` | 차단 X — **exit 2 무시**, JSON `decision` 객체를 쓸 것 | 차단 O — `decision.behavior: "deny"` |

표현이 다른 자리(`Stop`)와, 실제 능력이 다른 자리(`SessionStart`, `PreCompact`)가 섞여 있다.
`Stop` 은 양쪽 다 "턴을 끝내지 말고 계속 시켜라"를 표현하는데 Claude는 그걸 '차단'으로,
Codex는 '계속'으로 이름 붙였을 뿐 하는 일은 같은 계열이다. 반면 `SessionStart` 에서
세션 자체를 끊을 수 있느냐는 진짜로 갈린다.

### 가장 많이 헛디딜 자리 — `PermissionRequest`

이름이 완전히 같은데 출력 JSON 모양이 다르다.

```jsonc
// Claude Code
{
  "hookSpecificOutput": {
    "hookEventName": "PermissionRequest",
    "decision": "allow",          // allow | deny | pending
    "reason": "..."
  }
}

// Codex
{
  "decision": { "behavior": "deny" }
}
```

Claude는 `decision` 이 **문자열**이고 `hookSpecificOutput` 안에 들어간다. Codex는 `decision` 이
**객체**고 최상위에 있으며 안쪽 키가 `behavior` 다. 게다가 Claude 문서는 이 이벤트에서
**exit 2가 무시된다**고 명시한다. 한쪽에서 돌던 스크립트를 그대로 옮기면 아무 에러 없이
"결정을 안 한 훅"이 되어 조용히 통과된다. Claude 문서의 표현을 그대로 빌리면 —

> "The hook can deny the call, but staying silent doesn't approve it."

침묵은 승인이 아니지만, **침묵은 차단도 아니다.** 포팅 사고는 대개 여기서 난다.

### 그나마 그대로 옮겨지는 자리

`UserPromptSubmit` 의 컨텍스트 주입은 양쪽이 같은 모양이다.

```json
{
  "hookSpecificOutput": {
    "hookEventName": "UserPromptSubmit",
    "additionalContext": "Ask for a clearer reproduction before editing files."
  }
}
```

`PreToolUse` 의 `permissionDecision` / `permissionDecisionReason` 도 필드명이 같다.
현실적으로 **두 하네스에 같은 스크립트를 걸고 싶다면 `PreToolUse` 와 `UserPromptSubmit` 둘로
범위를 좁히는 게 제일 안전하다.**

---

## 3. 핸들러 타입 — 5종 대 2종

훅 하나가 "무엇을 실행하는가"에서 격차가 가장 크다.

| | Claude Code | Codex |
| --- | --- | --- |
| 핸들러 타입 | `command`, `http`, `mcp_tool`, `prompt`, `agent`(실험적) | `command`, `mcp_tool` |

Claude의 `http` 는 훅을 외부 엔드포인트로 POST하고, `prompt` 는 훅 안에서 모델에게 직접 묻고,
`agent` 는 서브에이전트를 띄운다. Codex에는 이 셋이 없다. 대신 Codex도 `mcp_tool` 핸들러에
`${tool_input.file_path}` 같은 플레이스홀더 치환을 지원해서, MCP 서버를 경유하면 비슷한 일을
할 수는 있다.

`http` 가 있다는 건 통제해야 할 면도 같이 생긴다는 뜻이라, Claude 쪽에는 그 대가로
`allowedHttpHookUrls`(URL 허용목록)와 `httpHookAllowedEnvVars`(헤더에 끼울 수 있는 환경변수
허용목록)라는 설정이 따로 있다. Codex에는 이런 설정이 없다 — 막을 면 자체가 없기 때문이다.

---

## 4. exit code 규약 — 여기는 거의 같다

| exit | Claude Code | Codex |
| --- | --- | --- |
| `0` | 성공. stdout이 `{...}` 로 파싱되면 JSON으로 읽음 | 성공, 정상 진행 |
| `2` | **차단.** 사유는 JSON decision 또는 stderr | **차단/거부.** 사유를 stderr에 쓴다 |
| 그 외 | 대부분 비차단 오류 (단 `WorktreeCreate`/`WorktreeRemove` 는 **0이 아니면 전부 차단**) | 훅 실패. 동작은 계속 진행 |

Claude 쪽에 하나 더 중요한 규칙이 있다.

> Exit code 2 **cannot be overridden** by `permissionDecision: "allow"`.

JSON으로 allow를 써 놓고 스크립트가 exit 2로 죽으면 **차단이 이긴다.** 안전한 방향으로 지는
설계라 옳지만, `set -e` 를 걸어 둔 훅이 뜻밖의 곳에서 2를 뱉으면 도구가 통째로 막힌다.

---

## 5. 타임아웃 — 기본은 같고 꼬리가 다르다

| | Claude Code | Codex |
| --- | --- | --- |
| 기본 | `command`/`http`/`mcp_tool` 600초, `prompt` 30초, `agent` 60초 | 600초 |
| 프롬프트 계열 | `UserPromptSubmit` 30초 | (별도 축소 규정 없음) |
| 모델 전환 | `PreModelSwitch`/`PostModelSwitch` 30초 | 해당 이벤트 없음 |
| 표시 계열 | `MessageDisplay` 10초 | 해당 이벤트 없음 |
| 종료 계열 | `SessionEnd` 공유 1.5초 예산(개별 타임아웃이 더 길면 최대 60초까지) | `SessionEnd`/`Interrupt` **기본 1초, 최대 3초** |
| 비동기 | `async: true`(타임아웃 미적용), `asyncRewake: true` | `async: true` (다음 안전 지점에 출력 전달) |

둘 다 **종료 훅에 쓸 수 있는 시간이 1초 남짓**이라는 점이 같다. 세션이 끝날 때 로그를 원격으로
쏘는 훅을 달아 놓고 "가끔 안 올라온다"고 느꼈다면 대개 이 예산 때문이다. 그런 건
`Stop`/`SessionEnd` 가 아니라 비동기로 돌리는 게 맞다.

---

## 6. 신뢰 모델 — Codex가 Claude에 없는 걸 하나 갖고 있다

표면적은 Claude가 넓지만, **훅을 "승인"하는 절차는 Codex 쪽이 더 빡빡하다.**

Codex 문서:

> Before a non-managed command hook can run, Codex requires you to review and trust the exact
> hook definition. Codex records trust against the hook's current hash, so new or changed hooks
> are marked for review and skipped until trusted.

**훅 정의의 해시를 기록**해 두고, 내용이 한 글자라도 바뀌면 다시 검토 대상으로 돌려 **승인 전까지
건너뛴다.** CLI에서 `/hooks` 로 검토·신뢰·개별 비활성화를 한다.

실제로 내 맥의 `~/.codex/config.toml` 에는 이런 항목이 세 개 들어 있다(해시값은 생략).

```toml
[hooks.state."/Users/lms/.codex/hooks.json:pre_tool_use:0:0"]
trusted_hash = "sha256:..."

[hooks.state."/Users/lms/.codex/hooks.json:user_prompt_submit:0:0"]
trusted_hash = "sha256:..."

[hooks.state."superpowers@claude-plugins-official:hooks/hooks.json:session_start:0:0"]
trusted_hash = "sha256:..."
```

여기서 두 가지가 동시에 보인다. ① 훅 하나하나가 해시로 못 박혀 있다. ② 세 번째 줄은
**Claude 플러그인 포맷으로 배포된 훅을 Codex가 로드한 것**이다. 1절에서 말한 호환성이 설정
파일에 그대로 남아 있다. 참고로 파일(`hooks.json`)에 적는 이벤트 이름은 PascalCase
(`PreToolUse`)인데 신뢰 원장의 키는 snake_case(`pre_tool_use`)다 — 같은 이벤트를 두 표기로
쓰는 셈이라 처음 보면 헷갈린다.

Claude Code 쪽에는 내용 해시 승인에 해당하는 게 없다. 대신 다른 층위로 막는다.

- **워크스페이스 신뢰**: 프로젝트의 `.claude/settings.json` 훅은 신뢰 대화상자를 수락해야 돈다.
  사용자 설정(`~/.claude/settings.json`)은 로컬이라 항상 신뢰된다.
- **`/hooks` 메뉴**: 설정된 훅을 출처 라벨(User/Project/Local/Plugin/Session)과 함께 보여주는
  **읽기 전용 브라우저**다. 수정은 JSON을 직접 고쳐야 한다.
- **`disableAllHooks`** 로 전부 끄기, **`allowManagedHooksOnly`**(관리 정책 전용)로 사용자·프로젝트·
  로컬·플러그인 훅을 무시하고 관리 훅만 허용.
- 서브프로세스에서 `OTEL_*` 익스포터 환경변수를 스크럽하고,
  `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB=1` 로 추가 스크럽.

정리하면 **Claude는 "어디서 온 훅이냐"로 막고, Codex는 "그 훅이 그대로냐"로 막는다.**
관점이 다르고, 둘 다 필요한 종류다. 훅 스크립트를 자동화가 덮어쓰는 환경이라면 Codex의 해시
승인이 확실히 유리하다 — 스크립트가 바뀌면 조용히 실행되는 대신 멈추기 때문이다.

---

## 7. 관리자 통제 — 설정 파일이 다르다

| | Claude Code | Codex |
| --- | --- | --- |
| 전면 비활성화 | `disableAllHooks` | `requirements.toml` 의 `[features] hooks = false` |
| 관리 훅만 허용 | `allowManagedHooksOnly` (관리 정책 계층) | `allow_managed_hooks_only = true` |
| 어디에 쓰나 | settings.json 계층(User < Project < Local < Managed) | **`requirements.toml` 에만** |

Codex 문서가 굳이 한 문장을 따로 박아 둔 함정이 있다.

> This setting is only supported in `requirements.toml`; putting it in `config.toml` does not
> enable managed-hooks-only mode.

`config.toml` 에 넣으면 **에러도 안 나고 그냥 안 먹는다.** 조직 정책으로 훅을 잠갔다고 믿고
있는데 실제로는 안 잠긴 상태가 될 수 있는 자리라, 넣었으면 반드시 확인해야 한다.

한편 우선순위 규칙도 정반대에 가깝다. Claude는 계층이 높을수록 이긴다(Managed가 최종).
Codex는 **"Higher-precedence config layers don't replace lower-precedence hooks"** — 즉
여러 소스에 걸린 훅이 **전부 다 돈다.** 게다가 같은 이벤트에 걸린 command 훅들은 동시에
실행되어 서로를 막지 못한다.

> Multiple matching command hooks for the same event are launched concurrently, so one hook
> can't prevent another matching hook from starting.

"상위 설정으로 덮어썼으니 하위 훅은 안 돌겠지"가 Codex에서는 틀린 가정이다.

---

## 8. matcher — 규칙이 은근히 다르다

Codex는 단순하다. `matcher` 는 정규식이고, 생략하거나 `"*"` 또는 `""` 이면 전부 매칭한다.
`^Bash$`, `Edit|Write`, `mcp__filesystem__.*` 같은 식이다.

Claude는 **문자 구성에 따라 해석이 바뀐다.**

| matcher 값 | 해석 |
| --- | --- |
| `"*"`, `""`, 생략 | 전부 매칭 |
| 영숫자·`_`·`-`·공백·`,`·`\|` 만 있음 | 정확 일치 또는 목록 (`Edit\|Write`) |
| 그 외 문자가 하나라도 있음 | **앵커 없는 정규식** |

그래서 Claude에서 `^Edit$` 는 정규식으로, `Edit` 는 정확 일치로 처리된다. 정규식은 앵커가 없어서
`Edit` 를 정규식으로 넣으면 `MultiEdit` 도 걸린다. 또 Claude에는 matcher 위에 한 겹 더 있는
`if` 필드가 있어 권한 규칙 문법으로 좁힐 수 있다 — `"Bash(git *)"`, `"Edit(src/**)"` 같은 것.
**Codex에는 `if` 에 해당하는 게 없다.** 명령 문자열 수준의 필터는 훅 스크립트 안에서 직접 해야 한다.

---

## 9. 옮길 때 실제로 걸리는 것 5가지

두 문서를 나란히 놓고 뽑은 체크리스트다.

1. **`PermissionRequest` 를 그대로 옮기지 말 것.** 출력 JSON 구조가 다르고, Claude에서는
   exit 2가 무시된다.
2. **`PostToolUse`/`SessionStart`/`PreCompact` 의 차단 능력이 다르다.** Codex에서 `continue: false`
   로 막던 걸 Claude로 옮기면 안 막힌다(그 반대도).
3. **핸들러 타입 확인.** `http`·`prompt`·`agent` 를 쓰는 Claude 훅은 Codex에 옮길 자리가 없다.
4. **`if` 필터는 Codex에 없다.** 스크립트 안쪽 조건문으로 내려야 한다.
5. **Codex는 훅을 바꾸면 승인이 풀린다.** CI나 스크립트로 훅 파일을 갱신하는 파이프라인이라면
   갱신 후 `/hooks` 승인이 필요하다는 걸 절차에 넣어야 한다.

---

## 10. 이 글의 한계

- 여기 적힌 **동작 규정은 전부 두 제품의 공식 레퍼런스 서술이고, 내가 두 하네스에서 훅을 돌려
  대조 실험한 결과가 아니다.** 문서와 구현이 어긋나는 자리는 있을 수 있다.
- 버전이 빠르게 움직인다. 확인 시점은 2026-09-11이고, 내 맥 기준 설치본은
  **Codex 0.152.1 / Claude Code 2.1.251** 이다. `codex features list` 에서 `hooks` 는
  `stable true`, 한때 별도 플래그였던 `plugin_hooks` 는 `removed` 로 바뀌어 있다.
- 6절의 `trusted_hash` 블록과 로컬 훅 구성은 **내 기계의 실측값**이지 문서 인용이 아니다.
  (참고로 그 맥에서 실제로 걸어 쓰는 Claude 훅은 `PreToolUse`·`PostToolUse`·`UserPromptSubmit`·
  `Stop`·`PreCompact` 다섯 이벤트, 핸들러 11개이며 전부 `command` 타입이다. Codex 쪽은
  `PreToolUse`·`UserPromptSubmit` 둘뿐이다. "30개 중 실제로 쓰는 건 대여섯 개"라는 말은
  적어도 내 환경에서는 사실이다.)
- 성능·안정성 우열은 다루지 않았다. 두 제품을 같은 조건에서 비교한 중립 제3자 벤치마크는
  찾지 못했다.

---

## 한 줄 결론

**Codex는 Claude Code의 훅 어휘를 거의 그대로 가져왔지만, 계약서는 다시 썼다.**
이벤트 이름이 같다는 이유로 스크립트를 복사하면 조용히 안 도는 자리가 생긴다.
반대로 Codex의 해시 기반 신뢰 승인은 Claude Code에 없는 안전장치라, 훅을 자동으로 갱신하는
환경이라면 그쪽이 한 수 위다.

---

## References

- Anthropic, *Claude Code — Hooks reference*. <https://code.claude.com/docs/en/hooks>
- Anthropic, *Claude Code — Get started with hooks*. <https://code.claude.com/docs/en/hooks-guide>
- OpenAI, *Codex — Hooks*. <https://developers.openai.com/codex/hooks>
- OpenAI, *Codex — Configuration*. <https://developers.openai.com/codex/config-reference>
- openai/codex, `docs/config.md` (`allow_managed_hooks_only` 관련 서술).
  <https://github.com/openai/codex/blob/main/docs/config.md>
- 로컬 실측: Codex 0.152.1 / Claude Code 2.1.251, macOS, 2026-09-11.
