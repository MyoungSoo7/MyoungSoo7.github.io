---
layout: post
title: "성능을 주장하지 않는 릴리스를 어떻게 평가할 것인가 — Ouroboros 0.50.8 → 0.51.0 해부"
date: 2026-08-10 01:20:00 +0900
categories: [AI, Engineering]
tags:
  [
    Ouroboros,
    Release Analysis,
    Adaptive Concurrency,
    AIMD,
    Verification,
    Coding Agent,
  ]
---

7월에 [0.35 → 0.50 구조 진화]({% post_url 2026-07-22-ouroboros-035-050-structure-evolution %})를 썼고, 어제 [5개 축 채점표]({% post_url 2026-08-09-ouroboros-vs-gajae-code-scorecard %})를 썼습니다. 그 채점표에서 Ouroboros의 **성능(수렴 효율)에 10점 만점에 5점**을 줬습니다. 근거가 없어서였습니다.

그 다음 날 0.51.0이 나왔습니다. 이 글은 **0.50.8 → 0.51.0**을 유용성과 성능 두 축으로 분해합니다.

그런데 분해하는 과정에서 예상하지 못한 결론이 먼저 나왔습니다. **이 릴리스는 성능이 좋아졌다고 주장하지 않습니다.** 그러면 성능 축은 어떻게 써야 할까요. 그게 이 글의 진짜 주제입니다.

## 이 글의 증거 등급

이 글의 모든 수치에는 셋 중 하나의 라벨이 붙습니다. 섞지 않겠습니다.

| 라벨            | 뜻                                                    | 검증 가능성                                |
| --------------- | ----------------------------------------------------- | ------------------------------------------ |
| 🔬 **실측**     | 내 로컬 두 설치본을 직접 비교해 얻은 값               | 아래 재현 명령으로 누구나 재현 가능        |
| 📄 **1차 공식** | 업스트림 릴리스 노트·PR 본문·패키지 메타데이터의 문언 | 링크로 확인 가능, 다만 **작성자 자기보고** |
| ❌ **없음**     | 찾아봤지만 존재하지 않음                              | 부재 자체가 발견                           |

특히 세 번째가 중요합니다. 이 글에서 가장 많이 등장하는 라벨입니다.

재현 환경: 업그레이드 직전 0.50.8 venv 전체를 백업해 둔 상태였습니다. 그래서 릴리스 노트가 아니라 **설치된 두 코드 트리를 직접 diff** 할 수 있었습니다.

```bash
OLD=~/ouroboros-mcp-venv.backup-v0.50.8-20260809/lib/python3.14/site-packages/ouroboros
NEW=~/ouroboros-mcp-venv/lib/python3.14/site-packages/ouroboros

diff -rq "$OLD" "$NEW" | grep -c '^Only in'          # 신규/삭제 항목 수
diff -rq "$OLD" "$NEW" | grep '^Only in '"$OLD"       # 삭제된 파일
find "$OLD" -name '*.py' | wc -l ; find "$NEW" -name '*.py' | wc -l
```

---

## 1. 🔬 실측 — 이 릴리스의 무게중심은 어디인가

| 항목             | 0.50.8    | 0.51.0    | 변화                 |
| ---------------- | --------- | --------- | -------------------- |
| `.py` 파일 수    | 511       | 556       | +45                  |
| 총 파이썬 라인   | 281,642   | 296,951   | **+15,309 (+5.4%)**  |
| 패키지 크기      | 24,524 KB | 25,988 KB | +6.0%                |
| **삭제된 파일**  | —         | —         | **0개**              |
| 마이그레이션 SQL | 2개       | 2개       | **바이트 단위 동일** |
| 동봉 스킬        | 22개      | 22개      | 이름 동일            |

두 가지가 즉시 눈에 띕니다.

**첫째, 순수 가산 릴리스입니다.** `diff -rq` 의 "Only in OLD" 결과가 **0건**입니다. 45개 모듈이 늘었고 하나도 사라지지 않았습니다. 이동은 있었습니다 — 예를 들어 `SubmitFanoutResultsHandler` 가 `mcp/tools/evaluation_handlers.py` 에서 `mcp/tools/fanout_handler.py` 로 옮겨갔습니다 — 하지만 기능이 제거된 곳은 없습니다.

**둘째, 스키마가 안 바뀌었습니다.** `001_initial.sql` 과 `002_brownfield.sql` 두 개가 전부이고, 둘 다 0.50.8과 바이트 단위로 동일합니다. 즉 이 업그레이드는 **DB 마이그레이션을 요구하지 않습니다.** (다만 이건 "롤백해도 안전하다"와는 다릅니다 — §5의 resume 계약 문제를 보세요.)

무게중심은 하위 패키지별 증가율에서 드러납니다.

| 하위 패키지     | 0.50.8 | 0.51.0 |       증가 |     증가율 |
| --------------- | -----: | -----: | ---------: | ---------: |
| `verification`  |    781 |  1,449 |       +668 | **+85.5%** |
| `persistence`   |  5,595 |  9,983 |     +4,388 | **+78.4%** |
| `harness`       |  5,035 |  5,977 |       +942 |     +18.7% |
| `dashboard_web` |  1,146 |  1,332 |       +186 |     +16.2% |
| `evolution`     | 10,824 | 11,737 |       +913 |      +8.4% |
| `core`          | 12,258 | 13,059 |       +801 |      +6.5% |
| `mcp`           | 41,205 | 43,561 |     +2,356 |      +5.7% |
| `cli`           | 22,219 | 23,485 |     +1,266 |      +5.7% |
| `orchestrator`  | 88,656 | 91,982 | **+3,326** |      +3.8% |
| `bigbang`       | 10,072 | 10,066 |         −6 |     −0.06% |

상대 증가율 1·2위가 **`verification`(+85.5%)과 `persistence`(+78.4%)** 입니다. 절대 증가량 1위는 `orchestrator`(+3,326줄)지만 이미 8.8만 줄짜리 덩어리라 비율로는 +3.8%에 불과합니다.

숫자가 말하는 것: **이번 릴리스는 실행 엔진을 손대지 않았습니다. 검증하는 부분과 저장하는 부분을 거의 두 배로 늘렸습니다.**

---

## 2. 유용성 축 — 늘어난 건 기능이 아니라 "손댈 수 있는 지점"

### 2.1 🔬 MCP 툴 표면: 31 → 32개, 제거 0개

두 venv의 인터프리터에서 `get_ouroboros_tools()` 를 실제로 호출해 파라미터 스키마를 덤프 비교한 결과입니다.

**추가된 툴 1개**

| 툴                         | 파라미터                         | 설명(원문)                                                                                                                                                                                  |
| -------------------------- | -------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ouroboros_fetch_artifact` | `contract_id` (string, required) | "Fetch and integrity-check a disposable Ouroboros artifact by the contract_id returned in an artifact envelope. … This is an explicit read and **never re-executes the originating work**." |

**파라미터가 추가된 툴 3개**

| 툴                             | 추가 파라미터                     |
| ------------------------------ | --------------------------------- |
| `ouroboros_execute_seed`       | `auto_evolve` (boolean, optional) |
| `ouroboros_start_execute_seed` | `auto_evolve` (boolean, optional) |
| `ouroboros_start_evaluate`     | `auto_evolve`, `seed_handoff_id`  |

기존 파라미터의 타입·필수여부·기본값·enum 변경은 **0건**입니다. 제거된 툴도 **0개**입니다. MCP 클라이언트 입장에서 이 업그레이드는 하위호환입니다.

`auto_evolve` 의 설명이 이 릴리스의 방향을 요약합니다 — "Override execution.auto_evolve for the chained evaluation. **When true, an explicitly rejected evaluation starts a bounded Ralph continuation loop.**" 거절이 종료가 아니라 다음 라운드의 입력이 됩니다.

### 2.2 🔬 새 CLI 명령군 3개

| 명령                                   | 파일                           | 크기      |
| -------------------------------------- | ------------------------------ | --------- |
| `ooo artifacts prune\|fetch\|replay`   | `cli/commands/artifacts.py`    | 140줄     |
| `ooo update`                           | `cli/commands/update.py`       | **886줄** |
| `ouroboros setup --runtime claude-cli` | `cli/commands/claude_setup.py` | 75줄      |

886줄짜리 `update` 명령이 유독 큽니다. 도입 동기가 PR #1859 본문에 그대로 적혀 있는데, 이게 이번 릴리스에서 제일 정직한 문장입니다 (📄 1차 공식, 기여자 clroot):

> "The update flow existed only as the conversational Claude Code skill, while the CLI shipped `uninstall` but no `update`. **#158 showed the consequence**: a user stuck on an old version … the only resolution was 'type `ooo update` in your claude session'. CLI-first users, CI scripts, and non-Claude runtimes had no supported path."

업데이트 방법이 대화형 스킬 안에만 있었고, 구버전에 갇힌 사용자에게 해줄 수 있는 말이 "클로드 세션을 열어서 치세요" 뿐이었다는 겁니다. 🔬 이 변화는 동봉된 스킬 파일에서도 확인됩니다 — `skills/update/SKILL.md` 가 **175줄짜리 인라인 파이썬 절차에서 `ouroboros update --check` 한 줄 호출로 축약**되었습니다.

구현도 방어적입니다. 🔬 실행 중인 CLI와 **동일한 매니저·환경**(uv → pipx → pip 순으로 receipt 기반 탐지)으로만 업그레이드하고, 프로젝트 `.env` 가 `UV_*`/`PIP_*`/`PIPX_*` 를 설정하는 것을 금지합니다.

세 번째 `claude_setup.py` 는 75줄로 제일 작지만 존재 이유가 제일 무겁습니다. 상류 의존성 충돌을 피해 가려고 만든 우회로이고, 그 사정은 §5-②에서 다룹니다.

### 2.3 Disposable Memory — RFC가 드디어 코드가 됨

📄 PR #1855 본문의 첫 문장: "The accepted Disposable Memory RFC was still **documentation-only on main**." 승인된 설계가 문서로만 존재하던 상태였다는 자기 진술입니다.

🔬 실제로 들어온 것은 13개 파일, `persistence` 서브패키지 +78% 증가의 대부분입니다. 핵심은 `persistence/artifact_store.py` (1,999줄) 하나로, docstring이 구조를 요약합니다:

> "Content-addressed storage and conservative GC for Disposable Memory."

본문을 `.ouroboros/artifacts/<prefix>/<sha256>.json` 에 EventStore **바깥**으로 저장하고, 이벤트 원장에는 계약별 manifest만 남깁니다. 그리고 봉투 타입(`core/disposable_memory.py`)의 주석이 의도를 못 박습니다 — "The caller-facing envelope **deliberately has no artifact-body or transcript field**."

🔬 강제되는 상한:

| 상수                            | 값        | 위치                               |
| ------------------------------- | --------- | ---------------------------------- |
| `MAX_DISPOSABLE_ARTIFACT_BYTES` | **1 MiB** | `core/disposable_memory.py:18`     |
| `MAX_DISPOSABLE_ENVELOPE_BYTES` | **4 KiB** | `core/disposable_memory.py:19`     |
| `DEFAULT_ARTIFACT_TTL`          | 90일      | `persistence/artifact_store.py:94` |
| `DEFAULT_REPLAY_RETENTION`      | 90일      | `persistence/artifact_store.py:95` |

여기서 유용성의 실체가 나옵니다. **부모 세션 컨텍스트로 4 KiB 이상 돌아오지 않습니다.** 자식 에이전트가 1 MiB 짜리 결과를 만들어도 부모는 참조만 받고, 필요할 때 `ouroboros_fetch_artifact` 로 명시적으로 꺼냅니다. 컨텍스트 오염을 설계로 막은 겁니다.

### 2.4 Hidden checklist — 채점 답안지를 워커에게 안 보여준다

이게 이번 릴리스의 헤드라인 기능입니다. 🔬 코드에서 실제로 확인했습니다.

`orchestrator/atomic_prompt_builder.py` 의 `_build_success_contract_block()` 에서 **다음 두 블록이 삭제**되었습니다:

```python
# 0.50.8 에만 존재
if spec.verify_command:
    lines.append(f"- Run locally before completion: {spec.verify_command}. "
                 "The verify gate re-runs it and records authoritative evidence.")
...
if spec.output_assertion:
    lines.append(f"- Expected output: {spec.output_assertion}")
```

0.51.0은 대신 고정 문구만 붙입니다:

```python
lines.append("- The harness independently verifies this contract; complete the work "
             "from the AC requirements and provide truthful evidence.")
```

같은 파일 docstring이 이유를 밝힙니다:

> "Artifact names are part of the work contract, but the harness-owned `verify_command` and `output_assertion` are **deliberately hidden**. The worker must satisfy the requested outcome **without receiving the grader's answer key**."

숨기는 건 프롬프트만이 아닙니다. 🔬 세 겹입니다.

1. **Seed 투영에서 제거** — `mcp/tools/seed_handoff.py:15` 의 `_HIDDEN_WORKER_KEYS = frozenset({"verify_command", "output_assertion"})`. 해당 키를 드롭할 뿐 아니라, 그 **값 문자열이 다른 필드에 우연히 새어 있으면 그것까지 치환**합니다. 잘못된 YAML은 fail-closed — "Malformed input fails closed: the raw text is never forwarded to a worker."
2. **재시도 힌트에서 제거** — `orchestrator/retry_hints.py:30` 이 `redact_hidden_contract_values(text, (spec.verify_command, spec.output_assertion))` 를 통과시킵니다.
3. **인코딩 우회 차단** — `orchestrator/contract_redaction.py` 가 원본 외에 `repr()`, `shlex.quote()`, `json.dumps()`, JSON 내부 문자열까지 5가지 변형을 만들어 **긴 것부터** 치환합니다.

**그리고 끄는 방법이 없습니다.** 🔬 `_build_success_contract_block` 에 조건 분기가 추가되지 않았고, `config/models.py` 에 새로 생긴 필드는 `auto_evolve` 와 `auto_evolve_max_generations` 둘뿐이며, `reveal|disclose|expose_contract|(enable|disable).*hidden|redact.*(enable|disable)` 정규식 전수 스캔에서 스위치가 **0건** 나왔습니다.

> ⚠️ **범위 주의.** 릴리스 노트는 "acceptance-criteria details are unconditionally hidden" 이라고 광범위하게 씁니다. 하지만 PR #1916 본문과 실제 코드는 더 좁습니다 — **`verify_command` 와 `output_assertion` 만** 숨깁니다. `expected_artifacts` 는 여전히 워커에게 노출됩니다. 이 글은 코드 쪽을 따릅니다.

---

## 3. 성능 축 — 무엇이 바뀌었나

### 3.1 🔬 가장 중요한 실측: 튜닝된 상수가 하나도 없다

두 트리 전체의 모듈·클래스 레벨 숫자 상수(710개 vs 747개)와 함수의 숫자형 기본 인자를 AST로 전수 추출해 비교했습니다.

| 항목                                       | 결과    |
| ------------------------------------------ | ------- |
| 동일 파일·동일 이름에서 **값이 바뀐 상수** | **0건** |
| 숫자형 **함수 기본 인자** 변경             | **0건** |
| 제거된 숫자 상수                           | **0건** |

폴링 간격, SQLite PRAGMA, 커넥션 풀 크기도 전부 그대로입니다.

```
mcp/detached_jobs.py      _POLL_INTERVAL_SECONDS = 0.05   (동일)
dashboard_web/server.py   _POLL_INTERVAL_SEC     = 0.7    (동일)
dashboard_web/page.py     WAIT_POLL_MS           = 3000   (동일)
PRAGMA / pool_size / max_overflow                        (동일)
```

즉 **0.51.0의 성능 변화는 상수 튜닝이 아니라 알고리즘 교체입니다.** 이건 좋은 신호이기도 하고, 동시에 "숫자를 조금 올려서 빨라졌다"는 종류의 손쉬운 검증이 불가능하다는 뜻이기도 합니다.

### 3.2 정적 semaphore → AIMD 윈도우

📄 PR #1851의 핵심 문장:

> "Replace the static AC delivery semaphore with an **AIMD window** that starts conservatively, halves on backend pressure, and grows after sustained success."

🔬 구현은 `orchestrator/adaptive_concurrency.py` (470줄)에 있고, 알고리즘 식별자는 `"aimd/v2"`, 승인 스코프는 `"provider_call"` 입니다.

동시 실행 한도를 $L$, 최대치를 $L_{\max}$ 라 할 때 정책은 이렇습니다.

$$
L \leftarrow \max\!\left(1,\ \left\lfloor \frac{L}{2} \right\rfloor\right) \quad \text{(백엔드 압력 관측 시)}
$$

$$
L \leftarrow \min\!\left(L_{\max},\ L + 1\right) \quad \text{(연속 성공 3회마다)}
$$

🔬 구체 값:

| 파라미터        | 값                                                                       | 근거                                                 |
| --------------- | ------------------------------------------------------------------------ | ---------------------------------------------------- |
| 감소 비율       | **÷2**                                                                   | `ADAPTIVE_CONCURRENCY_DECREASE_RATIO = "1/2"`        |
| 증가 스텝       | **+1**                                                                   | `adaptive_concurrency.py:385`                        |
| 증가 임계       | **연속 성공 3회**                                                        | `ADAPTIVE_CONCURRENCY_SUCCESSES_BEFORE_INCREASE = 3` |
| 하한 $L_{\min}$ | **1**                                                                    | `max(1, floor(L/2))`                                 |
| 초기값          | `effective_workers` (CLI 백엔드는 `DEFAULT_UNKNOWN_MAX_CONCURRENCY = 1`) | `backend_limits.py:52`                               |
| 상한 $L_{\max}$ | `max_parallel_workers`                                                   | `runner.py:10368`                                    |
| 쿨다운 상한     | **86,400초** (24시간)                                                    | `MAX_ADAPTIVE_CONCURRENCY_COOLDOWN_SECONDS`          |

압력 신호는 두 경로로 읽습니다. HTTP 429를 12가지 필드명(`http_status`, `httpStatus`, `status_code`, `api_error_status` …)에서 찾고, 그게 없으면 텍스트 패턴(`too many (concurrent) requests`, `concurrency limit|cap|maximum|exceeded`, `rate limit(ed|exceeded|reached)` …)으로 잡습니다. 프로바이더마다 제각각인 에러 포맷을 정규화하는 부분이 이 파일에서 가장 긴 축에 듭니다.

설계에서 인상적인 부분 두 가지:

**(a) 동시성 거절과 쿼터 소진을 구분합니다.** 📄 PR 본문 — "Distinguish concurrency rejection from explicit quota exhaustion so 429 pressure tunes dispatch while quota keeps the existing durable pause/resume authority." 🔬 코드에서 `QUOTA_EXHAUSTION` 은 창을 **줄이지 않고** epoch/streak만 리셋합니다. 쿼터가 떨어진 건 동시성 문제가 아니니 창을 줄여봐야 소용이 없고, 그건 durable pause가 처리할 일이라는 판단입니다.

**(b) epoch 가드.** 🔬 `adaptive_concurrency.py:380` — 거절이 도착하기 _전에_ 발급된 permit의 성공은 카운트하지 않습니다. 주석: "Completions already in flight when a rejection arrived must not immediately undo the multiplicative decrease." 이게 없으면 감소 직후 in-flight 완료들이 바로 창을 다시 부풀려서 AIMD가 진동합니다.

🔬 로그 문구도 바뀌었습니다:

|             | 0.50.8                                                                          | 0.51.0                                                                                                      |
| ----------- | ------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| 로그 이벤트 | `fan_out_capped`                                                                | `fan_out_initialized`                                                                                       |
| 문구        | "Fan-out **capped** to N worker(s) … Override with `OUROBOROS_MAX_CONCURRENCY`" | "Fan-out **initialized** … adaptive ceiling M"                                                              |
| docstring   | "**serialized by default** … raised only by explicit operator override"         | "**start serialized** … then **probes** toward the configured worker budget from live success/429 feedback" |

"cap"이 "initial"이 되고 "override"가 "probe"가 됐습니다. 같은 숫자(`DEFAULT_UNKNOWN_MAX_CONCURRENCY = 1`)인데 **의미가 상한에서 출발점으로 바뀐 것**이 이 릴리스의 성능 변화를 가장 정확하게 요약합니다.

### 3.3 ❌ 그런데 측정이 없습니다

여기서부터가 이 글을 쓴 이유입니다.

**첫째, 릴리스 노트에 성능 수치가 0건입니다.** 📄 v0.51.0 본문 전체를 훑었습니다. 처리량·지연·완료시간 숫자가 하나도 없습니다. 전부 정성 서술입니다.

**둘째, 성능 변경 PR 자체에 before/after가 없습니다.** 📄 #1851에 있는 숫자는 테스트 통과 수(1,251 passed, 1 skipped)와 제어 동작 검증(`Retry-After: 2` → 2초 지연, 쿼터 → 4시간 durable PAUSED)뿐입니다. **"정적 semaphore 대비 처리량이 얼마나 늘었는가"에 대한 답이 없습니다.**

**셋째, 벤치마크 하네스는 있는데 안 돌렸습니다.** 이게 결정적입니다. 📄 헤드라인 PR #1916에는 `src/ouroboros/auto/` 변경 시 **필수**라고 명시된 "R-run comparison" 표가 있습니다. 슬롯 구성이 진지합니다:

| 항목                           | Baseline | This PR | Ratio |
| ------------------------------ | -------- | ------- | ----- |
| Rounds completed in 600 s      | `N/A`    | `N/A`   | `N/A` |
| Per-round wall-clock (s/round) | `N/A`    | `N/A`   | `N/A` |
| Terminal reason                | `N/A`    | `N/A`   | `N/A` |
| EventStore event count         | `N/A`    | `N/A`   | `N/A` |

전부 `N/A` 입니다. Budget compliance 항목도 `[x] N/A (substrate-only successor ownership guard)` 로 면제 처리됐습니다. **측정할 틀은 갖춰져 있고, 이번엔 채우지 않았습니다.**

**넷째, 배포물 안에도 성능 산출물이 없습니다.** 🔬 두 휠 모두 `tests/` 디렉터리가 없어 타이밍 assertion 자체가 포함되지 않습니다. 이름에 bench/perf/latency/throughput이 들어간 파일은 양쪽 통틀어 `orchestrator/traceguard_benchmark_capture.py` 하나뿐인데, 이 파일은 **두 버전이 바이트 단위로 동일**하고 자체 docstring이 "It is deliberately **fixture-only: no live model calls**" 라고 밝힙니다.

인용 가능한 실측 시간은 CI 시간뿐입니다 — #1837의 16,457개 테스트 9분 19초, v0.50.2의 "CI time cut by more than half". 📄 **둘 다 CI 시간이지 제품 런타임이 아닙니다.**

### 3.4 🔬 그리고 느려질 수 있는 곳도 있습니다

성능 축을 정직하게 쓰려면 반대 방향도 세야 합니다.

**(a) 재시도 힌트 예산이 8배 늘었습니다.**

|                      | 0.50.8                                                        | 0.51.0                                              |
| -------------------- | ------------------------------------------------------------- | --------------------------------------------------- |
| 재시도 프롬프트 힌트 | `redact_and_truncate_text(...)` 후 `[-500:]` — **최대 500자** | `_MAX_HINT_CHARS = 4_000` + `_MAX_TRACE_FACTS = 12` |

재시도마다 프롬프트에 실려 나가는 토큰이 늘어납니다. 진단 품질과 맞바꾼 **의도된 비용 증가**입니다.

**(b) 대시보드 run picker가 N+1 쿼리가 됐습니다.**

|                           | 0.50.8                                                                                 | 0.51.0                                                                         |
| ------------------------- | -------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| `dashboard_web/reader.py` | 단일 집계 SQL (`UNION ALL` + `GROUP BY` + `ORDER BY last_row DESC LIMIT ?`) — 쿼리 1회 | 시작 이벤트만 뽑은 뒤 **run마다 별도 이벤트 클러스터 쿼리 + `reduce_board()`** |

리스트에 담기는 정보량(status/phase/provider/토큰/컬럼별 카운트)은 크게 늘었지만 DB 왕복 횟수도 늘었습니다. 로컬 SQLite라 체감은 작겠지만, **방향은 느려지는 쪽**입니다.

**(c) 검증이 늘면 LLM 호출이 늘어납니다.** 📄 #1915(캐시 버그 수정)의 정량 표가 유일하게 명확한 동작 델타입니다:

| 세대      | 수정 전                      | 수정 후                      |
| --------- | ---------------------------- | ---------------------------- |
| gen 1     | 0 assertions, 1 LLM call     | 동일                         |
| **gen 2** | **0 assertions, 1 LLM call** | **1 assertion, 2 LLM calls** |
| gen 3     | —                            | 진짜 캐시 히트               |

**이건 속도 개선이 아니라 의도된 비용 증가입니다.** 못 읽은 추출을 "답이 없다"로 영구 기억하던 버그를 고쳤더니, 2세대부터 검증이 실제로 돌기 시작해서 호출이 하나 늘었습니다. 거꾸로 읽으면 안 됩니다.

### 3.5 그래서 성능 축의 결론

메커니즘은 확실히 개선됐습니다. 고정 상한을 손으로 맞추던 것에서, 프로바이더 피드백으로 창을 탐색하는 제어기로 바뀌었습니다. AIMD는 TCP 혼잡 제어에서 수십 년 검증된 형태이고, epoch 가드나 쿼터/동시성 분리 같은 디테일도 실제로 겪어본 사람이 쓴 코드입니다.

**하지만 개선폭은 알 수 없습니다.** 그리고 이건 제가 게을러서 못 찾은 게 아니라 **존재하지 않습니다.** 릴리스 노트에도, PR에도, 패키지 안에도 없습니다. 심지어 프로젝트가 스스로 "필수"라고 정한 R-run 표를 비워 둔 채 머지했습니다.

> **0.51.0은 빨라졌다고 주장하지 않습니다. 그러니 빨라졌다고 읽어 주면 안 됩니다.**

정적 semaphore가 병목이었던 워크로드라면 AIMD가 도움이 될 겁니다. 하지만 그건 제 추론이지 이 릴리스가 제시한 증거가 아닙니다. 판단하려면 각자 재야 합니다.

---

## 4. 🔬 패키지 메타데이터 델타

| 항목                               | 변화                                                                                                                         |
| ---------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| `Requires-Dist` (기본 의존성 12개) | **변경 0건** — 버전 범위까지 전부 동일                                                                                       |
| `Requires-Python`                  | `>=3.12` 동일                                                                                                                |
| 제거된 extra                       | 없음                                                                                                                         |
| 신규 extra                         | `claude-cli` (**의존성 없는 빈 extra** — 이유는 §5-② 참조), `claude-sdk` (`anthropic==0.117.0`, `claude-agent-sdk==0.2.123`) |
| 신규 Classifier                    | **12줄** (0.50.8에는 Classifier가 한 줄도 없었음)                                                                            |
| 신규 Keywords                      | `agent-os, ai-agent, claude-code, llm-orchestration, mcp, spec-driven-development` 등 11개                                   |
| 신규 Project-URL                   | Homepage / Repository / Bug Tracker / Sponsor                                                                                |

기본 의존성이 하나도 안 바뀐 릴리스에 +15,309줄이 들어왔습니다. 외부 라이브러리를 끌어오지 않고 자체 구현으로 채웠다는 뜻입니다.

Summary 문구 변화도 기록해 둘 만합니다:

- 0.50.8: "… Works with **Claude Code and Codex CLI**."
- 0.51.0: "… works across **Claude Code, Codex CLI, OpenCode, Hermes, Gemini, Kiro, Copilot, Pi, Zcode, Goose, GJC, Antigravity, and Grok**."

2개에서 13개가 됐습니다. Classifier·Keywords·Project-URL이 이번에 처음 붙은 것과 합치면, **PyPI 상품 페이지를 이번에 처음 제대로 만들었다**는 신호로 읽힙니다.

---

## 5. 물릴 수 있는 것들 — 파괴적 변경 6건

유용성 축의 실전 부분입니다. 업그레이드 전에 확인하세요.

### ① 슬래시 커맨드 개명 (📄 #1919)

`status` / `help` / `config` 스킬 정체성이 `ouroboros-*` 로 바뀌었습니다. 직접 호출형이 `/ouroboros:ouroboros-status`, `/ouroboros:ouroboros-help`, `/ouroboros:ouroboros-config` 가 됩니다. PR 본문이 명시합니다 — "**reserved bare aliases are deliberately not retained** because they would recreate the collision." 자연어 `ooo status` 와 `drift` 별칭은 유지됩니다.

### ② `[mcp,claude]` 동시 설치 거부 (📄 #1928) — 그리고 이건 Ouroboros 탓이 아닙니다

MCP 2와 Claude Agent SDK가 요구하는 MCP 1.x가 한 인터프리터에 공존할 수 없습니다. `[all,mcp]`, `[mcp,claude-sdk]` 도 거부됩니다. 🔬 새 모듈 `package_profiles.py` 에 에러 문구가 그대로 박혀 있습니다:

```python
UNSUPPORTED_CLAUDE_SDK_MCP_MESSAGE = (
    "Unsupported package profiles: ouroboros-ai[mcp] requires MCP 2, while "
    "ouroboros-ai[claude] and ouroboros-ai[claude-sdk] require MCP 1.x. "
    "Use [claude] alone for the Claude SDK runtime, or use [claude-cli] with "
    "[mcp]; run the MCP 2 server in a separate environment/process."
)
```

**본인이 물리는지 확인하는 법:**

```bash
ls $(python -c "import site;print(site.getsitepackages()[0])") \
  | grep -iE 'dist-info' | grep -iE 'mcp|claude|anthropic'
```

🔬 제 환경에서는 `mcp-2.0.0.dist-info` 와 `mcp_types-2.0.0.dist-info` 만 나오고 `claude_agent_sdk`·`anthropic` 이 없습니다. 즉 순수 `[mcp]` 프로파일이라 이 변경에 물리지 않습니다. 둘 다 나오는 분은 환경을 둘로 쪼개야 합니다.

#### 그런데 왜 이런 선택지 없는 상황이 됐나

이 항목을 처음 쓸 때 저는 이걸 "Ouroboros가 만든 파괴적 변경"으로 분류했습니다. **인과가 반대였습니다.**

📄 PyPI 릴리스 이력을 보면 사정이 분명합니다.

| 패키지                 | 버전                             | 날짜 (UTC)     |
| ---------------------- | -------------------------------- | -------------- |
| `mcp` (MCP Python SDK) | `2.0.0a1`                        | 2026-06-11     |
|                        | `2.0.0rc1`                       | 2026-07-27     |
|                        | **`2.0.0` 정식**                 | **2026-07-28** |
| `claude-agent-sdk`     | `0.2.134` (이 글 작성 시점 최신) | 2026-08-08     |

그리고 그 최신 `claude-agent-sdk 0.2.134` 의 의존성이 이렇습니다:

```
mcp<2.0.0,>=1.23.0
```

**MCP SDK v2가 정식 출시된 지 열흘이 넘도록 상한이 `<2.0.0` 에 그대로 있습니다.** 그리고 이건 손이 안 간 게 아닙니다 — 같은 기간에 `0.2.129`(08-04)부터 `0.2.134`(08-08)까지 **닷새 동안 여섯 번 릴리스**했습니다. 다른 건 다 나갔고 이 핀만 안 움직였습니다.

핀 자체는 실수가 아니라 의도된 것이었습니다. 이슈 [#1028 "deps: pin mcp below 2.0.0"](https://github.com/anthropics/claude-agent-sdk-python/issues/1028)(2026-06-10, closed)이 v2가 아직 알파일 때 방어적으로 넣은 것입니다. 합리적인 조치였습니다. 문제는 **v2가 정식이 된 뒤에도 풀리지 않았다**는 것입니다.

v2 출시 **다음 날** 이슈가 올라왔습니다 — [#1150 "Support MCP Python SDK v2 for in-process SDK MCP servers"](https://github.com/anthropics/claude-agent-sdk-python/issues/1150) (2026-07-29). 📄 이 글을 쓰는 시점 상태:

- **open**, 라벨 **없음**, assignee **없음**
- 댓글 1개인데 메인테이너가 아니라 다른 사용자(`author_association: NONE`)의 +1:

> "+1 hit this today upgrading our MCP server to `mcp==2.0.0` (the SDK v2 line implementing the 2026-07-28 MCP spec). With v2 now stable, **the mcp<2.0.0 pin blocks co-installing claude-agent-sdk with any standards-current MCP v2 codebase.** … we cannot move to the new MCP spec until anthropic's agent sdk supports the new spec."

그래서 이 항목의 성격이 달라집니다. Ouroboros는 `[mcp,claude]` 를 **거부하기로 결정한 게 아니라**, 애초에 성립할 수 없게 된 조합을 **런타임에 터지게 두는 대신 설치 시점에 정직하게 막은 것**입니다. 이전에는 pip이 `mcp` 를 한쪽으로 해결해 주고 나면 어느 쪽 코드 경로가 먼저 닿느냐에 따라 깨졌습니다.

§4에서 신규 extra `claude-cli` 가 **의존성이 하나도 없는 빈 extra** 라고 적었는데, 이제 이유가 설명됩니다. **Claude Agent SDK를 아예 끌어오지 않는 것이 목적**입니다. `mcp<2.0.0` 을 상속받지 않으려면 그 패키지를 의존성에서 빼는 수밖에 없고, 대신 subprocess로 Claude CLI에 붙습니다. 🔬 그래서 `setup --runtime claude-cli` 가 런타임 백엔드 `claude_mcp` 로 매핑되고(`config/models.py:470,651` 에 리터럴 추가), 이걸 위해 `cli/commands/claude_setup.py` 75줄이 새로 들어왔습니다.

> **정리하면 이렇습니다.** 상류(MCP SDK)가 메이저 버전을 올렸고, 중간(Claude Agent SDK)이 따라오지 않았고, 하류(Ouroboros)가 그 간극을 자기 패키징으로 흡수했습니다. 사용자에게 보이는 건 "Ouroboros가 설치를 거부한다"지만, 실제로 고쳐져야 할 곳은 거기가 아닙니다. **이 파괴적 변경은 `claude-agent-sdk` 의 핀이 풀리는 날 사라질 성질의 것입니다.**

### ③ EventStore SQLite 전용 강제 (📄 #1897 / 🔬 `persistence/backend_contract.py`)

형식이 멀쩡한 non-SQLite URL도 이제 **생성 시점에** 거부됩니다(PostgreSQL URL 포함). 이전에는 받아 놓고 첫 커서에서 죽었습니다. 경로 없는 `sqlite+aiosqlite://` 와 `:memory:` 는 이제 정직하게 `supports_cross_process_workers=False` 를 보고합니다.

### ④ hidden checklist는 끌 수 없음 (§2.4)

🔬 스위치가 없습니다. 커스텀 워커나 패시브 플러그인 경로를 쓰고 있고 워커가 `verify_command` 를 읽는 걸 전제로 짜여 있다면 동작이 바뀝니다. 📄 그리고 알려진 제약이 있습니다 — "The opaque Seed vault is intentionally **process-local** … a parent restart invalidates the handle and **fails closed** to a manual evaluation retry."

### ⑤ 동시성 설정의 의미가 격하됐고, resume이 깨질 수 있음 (📄 #1851)

`OUROBOROS_MAX_CONCURRENCY` 와 백엔드 `max_concurrency` 가 하드 리밋에서 "compatible **pre-flight estimates**" 로 내려갔습니다. 이제 하드 실링은 `max_parallel_workers` 하나입니다.

그리고 이게 더 중요합니다. 🔬 정책 스냅샷(`aimd/v2` + `admission_scope: provider_call`)이 실행 semantics에 durable 기록되고, resume 시 정책이 맞지 않으면 `resume_blocked: adaptive_concurrency_policy_unavailable` 로 **fail-closed** 합니다. **0.50.x에서 시작해 진행 중인 run이 있다면, 업그레이드 후 그 run의 resume이 막힐 수 있습니다.** 진행 중인 작업을 끝내고 올리세요.

### ⑥ `logging.level` 이 이제 진짜 먹습니다 (📄 #1956 / 🔬 `cli/logging_setup.py`)

이전에는 `ouroboros config set logging.level warning` 이 성공을 보고하고도 실제 로거에 도달하지 않았습니다. 0.51.0에서 배선이 연결됐습니다. **과거에 warning을 걸어 두고 잊은 분은 출력이 갑자기 줄어듭니다.** 버그가 고쳐진 건데 체감은 "로그가 사라졌다" 입니다.

> 하나 더: v0.50.7의 #1803이 worktree 정리 기본값을 `prune-merged` 로 바꿨습니다. 0.50.7 **이전** 버전에서 건너뛰는 분에게는 이것도 함께 옵니다.

---

## 6. 이 릴리스에 들어간 제 PR 4건 — 전부 같은 병

이번 릴리스에 제 PR 4건이 머지됐습니다. 넣고 보니 네 개가 **완전히 다른 코드 경로에서 같은 병**을 앓고 있었습니다. **실패가 성공으로 보이는 배관.**

### #1837 — 아무 입력에나 매칭되는 정규식이 검증 증거로 쓰이던 문제

`SpecVerifier._safe_compile` 이 모델이 준 패턴에 대해 **컴파일되는지만** 물었습니다. 빈 문자열에 매칭되는 패턴은 모든 문자열에 매칭되므로, 컴파일도 잘 되고 첫 후보 파일에 매칭되어 `verified=True, detail="Found file: main.py"` 를 돌려줍니다. 프로젝트가 만족하지 못한 인수 기준에 대해서요.

재현: `.*`, `x?`, `\s*`, `(?:)`, `|`, `^`, `\A\Z` **7개 패턴 전부**가, `CameraProvider` 가 존재하지 않는 프로젝트에서 `verified_pass=True` 를 냈습니다. 결과는 `ACResult(passed=True, score=1.0, final_verdict="pass", verification_method="spec_verifier")`.

핵심은 이 문장입니다:

> "The spec verifier exists to catch agent self-report lies; **here it overturned an honest failure into a pass**."

**에이전트는 정직하게 FAIL을 보고했습니다.** 검증기가 그걸 뒤집었습니다. 거짓말을 잡으라고 놓은 장치가 진실을 지웠습니다.

수정은 추출 단계가 아니라 **검증기 단계**에서 거부합니다. 추출에서 버리면 어댑터가 "보고 없음"을 "검사할 게 없음"으로 읽어서 — 원문 표현으로 — "a refusal that silently _removes_ the check" 가 되기 때문입니다. 매칭 폭 기준도 검토했다 버렸습니다. `(?=class CameraProvider)` 같은 lookahead-only 패턴까지 같이 죽기 때문입니다.

**그리고 이 PR에서 제일 값어치 있는 부분은 폐기된 실험 기록입니다.** negative-control 코퍼스 방식을 프로토타입까지 만들었다가 접었고, 이유 세 가지를 남겼습니다:

1. **"Five successive hardening rounds** each closed the family the previous round had probed and left the next one open — `class`, then `interface`, then `trait` — and **26 of 26** modifier-prefixed forms survived every version." 다섯 라운드를 돌았는데 매번 직전 라운드가 뚫은 계열만 막고 다음 계열은 열려 있었고, modifier 접두 형태는 26개 전부가 모든 버전을 통과했습니다.
2. **차단 장치 자체가 공격면이 됩니다.** 컨트롤 하나가 후보 파일이 **하나도 없는** 프로젝트에서 `(.*)*#` 를 **비종료**로 만들었습니다. 검증기를 지키려고 넣은 코드가 검증기를 멈춰 세웠습니다.
3. "The direction is easy to get backwards." 방향을 거꾸로 잡기 쉽습니다.

그래서 범위를 좁혔습니다. **"모든 입력에 매칭" 계열만 닫고, "무관한 입력에 매칭" 계열(`.`, `.+`, `[\s\S]`, `class\s+\w+` 등)은 열어 둔 채 문서화했습니다.** 다 막으려다 아무것도 못 막느니, 닫은 범위를 정확히 적는 쪽을 골랐습니다.

### #1893 — 비어 있는 error 프레임이 종료로 안 잡히던 문제

`_extract_error_from_events` 가 payload가 null이거나 비어 있는 최상위 `error` 프레임에 대해 "종료 에러 없음"이라고 답했고, 게다가 자기 루프 **안에서** 답했습니다. 결과는 두 가지였습니다. CLI가 실패를 선언했는데 `Result.ok` 에 부분 텍스트가 담겨 돌아왔고, 앞쪽의 얇은 프레임이 뒤에 오는 완전한 에러를 버렸습니다.

가장 이상한 건 자기모순이었습니다:

> "`error: {}` took the dict branch and correctly reported `"Unknown error"`, while `error: null` reported nothing — **the same declared failure, opposite verdicts.** That contradicts the invariant stated three lines above it, `# Top-level error events are always terminal`."

주석은 "최상위 error는 항상 종료"라고 세 줄 위에 적혀 있었습니다.

### #1895 — 망가진 턴을 멀쩡한 턴으로 보고하던 문제

ourocode 어댑터의 plain 경로에 독립적인 결함이 둘 있었습니다.

**빈 턴이 `Result.ok` 를 반환했습니다.** `stopReason: "refusal"` 인 경우까지 포함해서요. 형제 어댑터는 전부 여기서 fail-closed 합니다 — `gjc_llm_adapter.py:447`, `codex_cli_adapter.py:1023`, `gemini_cli_adapter.py:469`, `claude_code_adapter.py:1252`. 하나만 빠져 있었습니다.

**잘림이 `length` 로 드러나지 않았습니다.** `_finish_reason` 이 `end_turn` 과 `cancelled` 만 번역해서 ACP의 `max_tokens` 가 그대로 호출자에게 갔습니다. 그런데 이 코드베이스가 검사하는 마커는 `finish_reason == "length"` 입니다 — `bigbang/ambiguity.py:527` 과 `:921` 이 둘 다 그걸 키로 씁니다. 그래서 **ourocode에서는 그 가드가 한 번도 도달되지 않았고, 잘린 답변이 완전한 답변으로 소비됐습니다.**

### #1915 — 못 읽은 추출을 답으로 기억하던 문제

`_parse_response` 가 서로 전혀 다른 두 상황에 같은 빈 튜플을 돌려줬습니다. **아예 읽을 수 없었던 응답**과 **읽었는데 검증할 게 없던 응답**입니다. `extract` 는 둘 중 뭐든 seed id로 캐시합니다(`extractor.py:139`).

> "So **one unreadable reply becomes that seed's extraction result forever.**"

그 seed의 **모든 이후 세대**에서 spec 검증이 꺼진 채로 남고, 디버그 로그는 그걸 캐시 히트라고 보고합니다. 조용합니다.

게다가 세 줄 위 transport 실패 경로는 이미 다음 세대에 재시도하고 있었습니다. **파싱 실패 경로만 영구적이었습니다.** 수정 효과가 §3.4의 그 표입니다 — gen2에서 assertion 0→1개, LLM 호출 1→2회.

---

### 네 개를 겹쳐 보면

| PR    | 어디서            | 무엇이 성공으로 보였나                                      |
| ----- | ----------------- | ----------------------------------------------------------- |
| #1837 | 검증기            | 아무 데나 매칭되는 정규식이 **정직한 FAIL을 pass로** 뒤집음 |
| #1893 | 프로바이더 어댑터 | CLI가 선언한 실패가 **`ok` + 부분 텍스트로** 반환됨         |
| #1895 | 프로바이더 어댑터 | 빈 턴·거부·잘린 답변이 **정상 턴으로** 보고됨               |
| #1915 | 추출 캐시         | 읽지 못한 응답이 **"검증할 것 없음"으로 영구 기억됨**       |

네 곳 다 크래시가 없습니다. 로그도 정상입니다. 그냥 **초록불이 켜집니다.**

Ouroboros가 0.50.0에서 내건 슬로건이 "The Verifiable Loop: **contracts, not claims**" 였습니다. 검증 계층을 아무리 두껍게 쌓아도, 그 계층 내부의 배관 하나가 실패를 삼키면 전체가 무의미해집니다. §1의 실측에서 `verification` 서브패키지가 **+85.5%** 로 상대 증가율 1위였던 게 우연이 아니라고 생각합니다.

---

## 7. 채점표 재조정

어제 매긴 점수를 이 릴리스 기준으로 다시 봅니다.

| 축              | 어제 |     오늘 | 근거                                                                                                                                             |
| --------------- | ---: | -------: | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| 유용성          | 7/10 | **8/10** | MCP 툴 하위호환 유지하며 +1, CLI 명령군 3개 추가·제거 0, 봉투 4 KiB 상한으로 컨텍스트 오염을 설계로 차단, `ooo update` 로 업그레이드 경로 정상화 |
| 성능(수렴 효율) | 5/10 | **5/10** | **메커니즘은 바뀌었고 증거는 안 바뀌었습니다.**                                                                                                  |

성능 점수를 올리지 않는 이유는 단순합니다. AIMD가 정적 semaphore보다 나은 설계라는 건 제 판단이고, 점수는 판단이 아니라 증거에 붙여야 합니다. 프로젝트가 스스로 "필수"라고 규정한 R-run 표를 비워 둔 채 머지한 릴리스에, 제가 대신 숫자를 만들어 줄 수는 없습니다.

거꾸로 이렇게도 말할 수 있습니다. **0.51.0은 성능 릴리스가 아닙니다. 검증·저장 릴리스입니다.** `verification` +85.5%, `persistence` +78.4%, 실행 엔진 +3.8%, 튜닝된 상수 0개. 숫자가 그렇게 말하고 있고, 릴리스 노트가 성능을 주장하지 않는 것도 그래서 일관됩니다. 이 릴리스를 성능으로 평가하는 건 애초에 잘못된 자입니다.

### 업그레이드할 것인가

**하세요. 단, 진행 중인 run을 끝내고 하세요.**

- ✅ 스키마 변경 없음, 삭제 모듈 0개, 기본 의존성 변경 0건, MCP 툴 제거 0개
- ⚠️ 진행 중인 0.50.x run이 있으면 resume이 fail-closed 될 수 있음 (§5-⑤)
- ⚠️ `[mcp,claude]` 를 같이 설치했다면 먼저 쪼개기 (§5-② 확인 명령 참조). 원인은 Ouroboros가 아니라 `claude-agent-sdk` 의 `mcp<2.0.0` 핀이고, 그게 풀리면 없어질 제약입니다
- ⚠️ 슬래시 커맨드를 스크립트에 박아 뒀다면 `ouroboros-*` 로 (§5-①)
- ⚠️ 로그가 갑자기 조용해지면 버그가 아니라 `logging.level` 이 이제 먹는 것 (§5-⑥)

---

## 마무리 — 부재를 기록하는 것도 분석이다

이 글을 쓰면서 제일 오래 망설인 부분은 §3.3이었습니다. "성능 개선 없음"이라고 쓰면 릴리스를 깎아내리는 것처럼 읽히니까요.

그런데 실제로 일어난 일은 다릅니다. 이 프로젝트는 R-run 비교표라는 **틀을 이미 만들어 뒀습니다.** `600초 라운드 수`, `라운드당 wall-clock`, `EventStore 이벤트 수` — 슬롯이 진지합니다. 그리고 `src/ouroboros/auto/` 를 건드리면 필수라고 규정까지 해 뒀습니다. 이번에 안 채웠을 뿐입니다.

틀이 없어서 못 잰 것과, 틀이 있는데 안 잰 것은 다릅니다. 전자는 설계 부재고 후자는 릴리스 규율의 문제입니다. 그리고 후자는 다음 릴리스에서 표 하나 채우면 해결됩니다.

그때까지, 저는 이 릴리스의 성능에 대해 아무 말도 하지 않겠습니다. **모르는 것을 모른다고 쓰는 것도 결과를 보장하는 일의 일부입니다.**

---

## References

### 1차 공식 — 업스트림 릴리스 (github.com/Q00/ouroboros)

- [v0.51.0](https://github.com/Q00/ouroboros/releases/tag/v0.51.0) — "Ouroboros is Loop Engineering"
- [v0.50.0](https://github.com/Q00/ouroboros/releases/tag/v0.50.0) — "The Verifiable Loop: contracts, not claims" (2026-07-08)
- [v0.50.2](https://github.com/Q00/ouroboros/releases/tag/v0.50.2) · [v0.50.3](https://github.com/Q00/ouroboros/releases/tag/v0.50.3) · [v0.50.6](https://github.com/Q00/ouroboros/releases/tag/v0.50.6) · [v0.50.7](https://github.com/Q00/ouroboros/releases/tag/v0.50.7) · [v0.50.8](https://github.com/Q00/ouroboros/releases/tag/v0.50.8)

### 1차 공식 — PR 본문 (작성자 자기보고, 제3자 재현 미확인)

- [#1851 — adapt concurrency from provider feedback](https://github.com/Q00/ouroboros/pull/1851) (AIMD 윈도우)
- [#1916 — hidden-checklist convergence loop](https://github.com/Q00/ouroboros/pull/1916) (R-run 표 `N/A`)
- [#1855 — disposable artifact lifecycle](https://github.com/Q00/ouroboros/pull/1855)
- [#1859 — native `ooo update`](https://github.com/Q00/ouroboros/pull/1859) (기여자 clroot)
- [#1891 — durable generation lease](https://github.com/Q00/ouroboros/pull/1891) (기여자 sumin220)
- [#1897 — EventStore SQLite-only](https://github.com/Q00/ouroboros/pull/1897) · [#1919 — 슬래시 커맨드 개명](https://github.com/Q00/ouroboros/pull/1919) · [#1928 — 패키징 extras](https://github.com/Q00/ouroboros/pull/1928) · [#1931 — Bash artifact provenance](https://github.com/Q00/ouroboros/pull/1931) · [#1936 — zero-time job snapshots](https://github.com/Q00/ouroboros/pull/1936) · [#1956 — `logging.level` 배선](https://github.com/Q00/ouroboros/pull/1956)

### 1차 공식 — 본인 PR

- [#1837 — refuse regexes that match any input as verification evidence](https://github.com/Q00/ouroboros/pull/1837)
- [#1893 — keep an empty OpenCode error frame terminal](https://github.com/Q00/ouroboros/pull/1893)
- [#1895 — stop reporting a degraded ourocode turn as a clean one](https://github.com/Q00/ouroboros/pull/1895)
- [#1915 — stop remembering an unreadable extraction as an answer](https://github.com/Q00/ouroboros/pull/1915)

### 1차 공식 — 상류 의존성 (§5-② 근거)

- [`mcp` on PyPI](https://pypi.org/project/mcp/) — `2.0.0` 정식 출시 **2026-07-28** (`2.0.0rc1` 07-27, `2.0.0a1` 06-11)
- [`claude-agent-sdk` on PyPI](https://pypi.org/project/claude-agent-sdk/) — 최신 `0.2.134`(2026-08-08)의 `Requires-Dist` 가 여전히 **`mcp<2.0.0,>=1.23.0`**
- [anthropics/claude-agent-sdk-python#1150 — Support MCP Python SDK v2 for in-process SDK MCP servers](https://github.com/anthropics/claude-agent-sdk-python/issues/1150) — 2026-07-29 개설, 이 글 작성 시점 open·라벨 없음·assignee 없음·메인테이너 응답 없음
- [anthropics/claude-agent-sdk-python#1028 — deps: pin mcp below 2.0.0](https://github.com/anthropics/claude-agent-sdk-python/issues/1028) — 2026-06-10, closed. 핀이 들어간 경위

### 패키지

- [ouroboros-ai on PyPI](https://pypi.org/project/ouroboros-ai/) — 0.50.8 / 0.51.0 `METADATA` 비교 출처
- 업스트림: [Q00/ouroboros](https://github.com/Q00/ouroboros) (MIT)

### 이 블로그의 관련 글

- [믿는 루프에서 검증하는 루프로 — Ouroboros 0.35 → 0.50 구조 진화 해부]({% post_url 2026-07-22-ouroboros-035-050-structure-evolution %})
- [우로보로스 vs 가재코드 — 5개 축 10점 채점]({% post_url 2026-08-09-ouroboros-vs-gajae-code-scorecard %})
- [두 하네스, 두 무게중심]({% post_url 2026-07-24-gajae-code-vs-ouroboros-harness %})

### 확인하지 못한 것 (정직하게 남깁니다)

- **PR 번호와 코드의 대응**: 설치된 트리 전체에서 `#1851`, `#1916` 문자열이 검색되지 않습니다. 소스에 존재하는 이슈 태그는 `#1823, #1825, #1826, #1829, #1830, #1832, #1838, #1839, #1888, #1889, #1901, #1955` 입니다. §2.4와 §3.2의 구현 서술은 **기능 설명으로 매칭한 것**이지 소스의 이슈 태그로 확인한 것이 아닙니다.
- **성능 수치**: §3.3 참조. 존재하지 않습니다.
- **PR 수치의 제3자 검증**: 모든 테스트 통과 수·타이밍은 PR 작성자 자기보고이며, 중립 제3자 재현 결과는 부재합니다.
- **hidden checklist의 실제 범위**: 릴리스 노트("acceptance-criteria details are unconditionally hidden")와 PR 본문·코드("harness-owned verifier commands and output assertions")가 어긋납니다. 이 글은 코드를 따랐습니다.
