---
layout: post
title: "에이전트를 진화시킨다는 말의 실제 구현 — oh-my-darwin 코드 해부"
date: 2026-08-24 00:15:00 +0900
categories: [ai, tooling]
tags: [coding-agent, meta-harness, evolutionary-algorithm, map-elites, codex, cli, code-reading]
---

"코딩 에이전트를 진화 루프로 돌린다"는 문장은 요즘 흔하다. 흔한 만큼 대부분 슬라이드에서 끝난다. 제안하고, 실행하고, 채점하고, 좋은 것만 남긴다 — 말은 네 단어면 되는데, 그걸 실제로 돌리려면 **"실행이 언제 끝났는지 어떻게 아느냐"** 같은 지저분한 질문에 전부 답해야 한다.

[oh-my-darwin](https://github.com/clarence-lee-sheng/oh-my-darwin) 은 그 답들을 코드로 적어 놓은 리포다. 규모는 작다 — TypeScript 8,502줄, 커밋 31개, 작성자 2명, 2026년 5월 17일부터 19일까지 **사흘**. 루트에 `HACKATHON_DEMO_PLAN.md` 가 있으니 정체는 분명하다. 해커톤 프로젝트다.

그런데 사흘짜리 프로토타입치고 답이 구체적이다. 이 글은 그 구체적인 지점들만 골라 읽는다. **쓰라고 권하는 글이 아니라, 이 문제를 직접 풀 사람이 남의 답안지를 보는 글이다.**

---

## 1. 무엇을 하는 물건인가

Darwin 자체는 LLM 을 부르지 않는다. **다른 에이전트 CLI 를 띄우는 껍데기**다.

기본 엔진은 [OMX(oh-my-codex)](https://github.com/Yeachan-Heo/oh-my-codex) 이고, 실패하면 [Codex CLI](https://github.com/openai/codex) 로 폴백한다. `package.json` 의 `dependencies` 는 **빈 객체**다 — 런타임 의존성이 하나도 없다. Node 20 이상과 TypeScript 컴파일러만 있으면 된다.

사용자가 치는 명령은 네 개다.

| 명령 | 하는 일 | 남기는 것 |
|---|---|---|
| `darwin init` | 소크라테스식 인터뷰로 태스크를 스펙화 | `.darwin/meta-spec.md` |
| `darwin baseline` | 첫 실행 + 첫 점수 | `.darwin/frontier.json` |
| `darwin meta` | 제안 → 실행 → 채점 → frontier 갱신 반복 | `.darwin/evolution.jsonl`, `runs/`, `proposals/` |
| `darwin status` | 현재 frontier·이력·capability 조회 | — |

상태는 전부 평문이다. Markdown, JSON, JSONL. DB 도 서버도 없다. **"에이전트 루프의 상태를 어디에 두느냐"** 에 대한 이 답 — 프로젝트 디렉터리 안의 append-only 텍스트 — 은 규모가 작을 때 압도적으로 옳다. `git diff` 로 읽히고, `grep` 으로 검색되고, 망가지면 손으로 고칠 수 있다.

`meta-spec.md` 가 담는 항목이 특히 눈에 띈다. 태스크, **스코어러**, 제약, **HITL 패턴**, 최적화 표면, **중단 조건**. 마지막 세 개를 인터뷰에서 강제로 물어보는 게 이 도구의 관점이다 — 사람이 어디서 개입하고 언제 멈추는지를 태스크 정의의 일부로 본다.

---

## 2. 가장 잘 만든 부분 — 전략을 계약으로 분리했다

Darwin 의 루프는 그냥 "제일 좋은 걸 골라 또 시킨다"(greedy)로 굳어 있지 않다. `src/strategy/contract.ts` 에 **훅 인터페이스**가 있고, 사용자가 `.mjs` 파일로 갈아끼운다.

```ts
export interface StrategyHooks {
  selectParents?(ctx): ParentAttempt[];        // 무엇을 변이의 부모로 삼을까
  mutationDirective?(ctx): string;             // 제안자에게 어떤 방향을 지시할까
  acceptCandidate?(candidate, ctx): boolean;   // 이 후보를 실행할 가치가 있나
  updatePopulation?(attempt, population, ctx); // 개체군을 어떻게 갱신할까
}
```

이건 유전 알고리즘의 표준 분해를 그대로 옮긴 것이다 — 선택, 변이, 수용, 대체. 그리고 리포는 이 계약을 구현한 전략 **네 개**를 `templates/strategies/` 에 넣어 놨다.

- **greedy** — 항상 현재 frontier 를 부모로. 기본 동작을 명시적으로 적은 것.
- **tournament** — 과거 시도 중 K개(코드상 `TOURNAMENT_SIZE = 3`)를 무작위로 뽑아 그중 최고를 부모로. frontier 가 가려버린 "오래됐지만 강한" 줄기로 되돌아갈 수 있다. 유전 알고리즘의 토너먼트 선택 그 자체다.
- **novelty** — 부모를 점수가 아니라 **frontier 와 텍스트적으로 먼 정도**로 고른다. 임베딩 없이 토큰 자카드 거리를 쓴다. 목적 함수를 버리고 새로움만 좇는 탐색이 오히려 목적을 더 잘 달성한다는 [Lehman & Stanley 의 novelty search](https://doi.org/10.1162/EVCO_a_00025) 계보다.
- **map-elites** — `(sandbox, model)` 노브 조합을 니치로 삼아 **셀마다 최고 개체를 따로 보관**한다. 매 이터레이션 무작위 니치의 엘리트를 부모로 뽑아 그 셀을 채우거나 빈 셀을 노린다. [Mouret & Clune 의 MAP-Elites](https://arxiv.org/abs/1504.04909) 를 에이전트 설정 공간에 그대로 적용한 것이다.

**이게 이 리포에서 제일 배울 만한 지점이다.** "에이전트 루프"를 자작하는 사람 대부분은 greedy 하나만 짜고 끝낸다. 그러다 점수가 평평해지면 손 쓸 방법이 없다. 여기서는 그 상황이 파일 하나 바꾸는 문제가 된다. 각 전략 파일 맨 위에 `Use when` / `Avoid when` 주석이 달려 있는 것도 좋다 — novelty 는 "텍스트 거리가 행동 다양성의 나쁜 대리 지표일 때는 피하라"고 자기 한계를 먼저 적어 놨다.

방어 코드도 인상적이다. 전략 훅은 사용자가 쓴 JS 다. `safeHook()` 은 훅이 없거나, 던지거나, **모양이 틀린 값을 돌려주면** 한 줄 경고를 찍고 기본 구현으로 되돌아간다.

```ts
// 전략 훅은 사용자가 작성한 JS다. 절대 루프를 죽여서는 안 된다.
```

사용자 확장점을 여는 순간 이 문장이 설계 원칙이 되어야 한다는 걸 아는 코드다. `isPopulation`, `isParentAttempt` 같은 타입 가드가 런타임 검증까지 붙어 있다.

---

## 3. 가장 약한 부분 — 적합도 함수가 사람이다

진화 알고리즘의 성패는 전략이 아니라 **적합도 함수**에서 갈린다. 그래서 `src/scorer/` 를 봤다. 스코어러 종류는 네 가지다.

- `command` — 명령을 실행해 숫자를 파싱 (구현됨)
- `test-suite` — 테스트 스위트 결과를 점수로 (구현됨)
- `human` — 사람에게 물어본다 (구현됨)
- `llm-judge` — **구현 안 됨**

`llm-judge` 분기의 코드는 이렇다.

```ts
writeTerminalError(
  "darwin: scorer 'llm-judge' is not yet implemented; not falling back to human verification.",
);
return { score: null, note: "llm-judge scorer is not implemented yet" };
```

그리고 `human` 스코어러의 실체는 이것이다.

```ts
const raw = (await rl.question("realized score? (number, blank to skip) > ")).trim();
```

**터미널이 숫자를 묻고 사람이 친다.** `meta-spec.md` 에 `## Scorer` 섹션이 없으면 이게 기본값이다.

이건 버그가 아니라 정직한 설계 결정이다. 명령이나 테스트로 점수가 나오는 태스크 — 해커톤 데모가 고른 `tiny-js-repair` 픽스처처럼 `npm test` 가 `score: 0` 또는 `score: 1` 을 찍는 태스크 — 라면 루프는 완전 자동으로 돈다. 문제는 **그런 태스크가 이미 자동화하기 제일 쉬운 태스크라는 것**이다.

리서치나 설계처럼 진짜 이 루프가 필요한 태스크에서는 매 이터레이션 사람이 숫자를 친다. 30분짜리 시도를 20번 돌리면 사람이 20번 앉아 있어야 한다. 그리고 `--attempt-max` 기본값은 정확히 30분(`30 * 60 * 1000`)이다.

여기서 이 도구가 알려주는 진짜 교훈이 나온다. **에이전트 진화 루프에서 어려운 부분은 진화가 아니다. 채점이다.** 선택·변이·대체는 위에서 봤듯 30줄짜리 `.mjs` 로 끝난다. 반면 "이 시도가 저 시도보다 나은가"를 사람 없이 판정하는 문제는, 이 리포가 유일하게 손대지 않고 남겨둔 칸이다.

덧붙이면, 자동 스코어러를 붙였을 때 따라오는 문제도 같이 온다. 측정 지표가 목표가 되는 순간 그 지표는 좋은 지표이길 그만둔다는 오래된 경고 — 에이전트가 20번 시도하며 최적화하는 대상은 당신의 의도가 아니라 **당신이 적은 스코어러 명령**이다.

---

## 4. 제일 영리하고 제일 위태로운 부분 — TUI 꼭두각시 조종

`darwin meta` 는 매 이터레이션 엔진을 새로 띄운다. 그런데 OMX/Codex 는 **대화형 TUI** 다. 배치 실행기가 아니다. 여기서 두 가지 질문이 생긴다.

1. 목표를 어떻게 집어넣나?
2. 끝났다는 걸 어떻게 아나?

`src/runtime/goal-attempt.ts` 의 답은 이렇다.

```ts
const DEFAULTS = {
  runner: "initial",
  maxDurationMs: 30 * 60 * 1000,  // 절대 상한 30분
  quietMs: 60_000,                // 정적 판정 60초
  gracefulMs: 5_000,              // /quit 후 SIGTERM 까지 유예 5초
  tuiWarmupMs: 1_500,             // TUI 초기화 대기 1.5초
};
```

> 완료 판정 휴리스틱: `stop` 이벤트를 본 뒤 정적 타이머를 시작한다. 이후 들어오는 `pre_tool_use` / `user_prompt_submit` 이 타이머를 리셋한다. 타이머가 만료되면 목표가 "끝났다"고 보고 `/quit` 를 보낸다.

풀어 쓰면 — **TUI 를 띄우고 1.5초 기다렸다가 `/goal <텍스트>` 를 주입한다. 그리고 `.darwin/events.jsonl` 을 지켜본다.** `stop` 이벤트가 뜨면 60초 카운트다운을 건다. 그 사이에 도구 호출이나 프롬프트 제출이 새로 들어오면 카운트다운을 취소한다. 60초 동안 아무 일도 안 일어나면 끝난 걸로 치고 `/quit` 를 보내고, 5초 뒤에도 안 죽으면 SIGTERM 을 보낸다. 그래도 30분을 넘기면 잘라낸다.

이벤트가 파일에 흐르는 건 Darwin 이 `.codex/hooks.json` 에 자기 자신(`darwin-hook`)을 등록해 두기 때문이다. `SessionStart`, `PreToolUse`, `PermissionRequest`, `PostToolUse`, `UserPromptSubmit`, `Stop` 이 잡힌다. 프로세스 정리도 `terminateProcessTree()` 로 **프로세스 트리 전체**에 SIGTERM → 유예 → SIGKILL 순으로 간다. 자식이 손자를 남기는 상황까지 봤다는 뜻이다.

**이 설계에 대한 평가는 갈린다.**

잘한 쪽: 다른 사람의 대화형 TUI 를 자동화하는 문제에 대한 실용적이고 완결된 답이다. `quiet-child.ts`, `process-tree.ts`, `file-wait.ts`, `bridge.ts` 로 계층이 나뉘어 있고 각각 테스트가 있다. 테스트 파일이 31개인데 `goal-attempt`, `quiet-child`, `process-tree`, `file-wait` 가 전부 커버돼 있다. 사흘짜리 프로젝트에서 가장 손이 많이 간 자리가 여기다.

위태로운 쪽: **이건 계약이 아니라 관찰이다.** 60초 침묵이 "완료"라는 보장은 어디에도 없다. 에이전트가 60초 넘게 생각하면 살아 있는데 죽인다. 반대로 잘못된 상태로 멈춰 있으면 성공으로 채점된다. `/goal` 슬래시 명령의 이름이나 `stop` 이벤트 이름이 상류에서 바뀌면 조용히 깨진다 — 에러가 아니라 **매번 정적 타임아웃**이라는 형태로.

`--goal-runner exec` 라는 비슬래시 자동화 경로를 따로 둔 건 이 취약함을 만든 사람들도 알고 있다는 뜻이다.

---

## 5. 의외로 제대로 된 부분 — capability 승격의 안전장치

Darwin 의 야심적인 기능 중 하나는 **이터레이션이 만들어낸 스킬이나 훅을 프로젝트에 승격시키는 것**이다. 시도 N 이 유용한 `SKILL.md` 를 발견하면 시도 N+1 이 그걸 쓴다. 자기 능력을 자기가 늘리는 루프다.

이건 위험한 기능이다. LLM 이 제안한 파일을 사용자 프로젝트에 쓰고, LLM 이 제안한 훅을 실행 경로에 등록한다는 뜻이니까. `src/capabilities/manifest.ts` 가 그 위험을 어떻게 막는지가 흥미롭다.

**경로 탈출 차단:**

```ts
function resolveUnder(base: string, rel: string, label: string): string {
  if (!rel || isAbsolute(rel)) throw new Error(`${label} must be a relative path`);
  const normalized = normalize(rel);
  if (normalized.startsWith("..")) throw new Error(`${label} cannot escape proposal dir`);
  const full = resolve(base, normalized);
  const root = resolve(base);
  if (full !== root && !full.startsWith(root + "/")) {
    throw new Error(`${label} cannot escape proposal dir`);
  }
  return full;
}
```

절대 경로 거부, `..` 거부, 그리고 **정규화 후 접두사 재확인**까지. 마지막 검사가 있는 게 중요하다 — 앞의 두 검사만으로는 심볼릭 링크나 우회 표기를 다 못 막는다.

**훅 명령 화이트리스트:**

```ts
`hook capability ${name} is not auto-safe: command must be exactly "darwin-hook ${eventInfo.event}"`
```

제안된 훅이 임의의 셸 명령을 실행할 수 없다. **문자열이 정확히 일치**해야 한다. "안전한 명령인지 검사"가 아니라 "이 명령만 허용"이다. 전자는 언제나 뚫리고 후자는 안 뚫린다.

**해시 추적:** 승격된 capability 는 sha256 을 기록해 두고, 파일이 사라지거나 내용이 바뀌면 `stale` 로 표시한다. `darwin capabilities` 로 조회된다.

사흘짜리 해커톤 코드에서 이 세 가지가 다 들어 있는 건 예상 밖이다. **자기 코드를 고치는 에이전트 시스템을 만들 사람이라면 이 파일은 읽을 값어치가 있다.**

---

## 6. 그래서 쓸 물건인가 — 아니다. 다만.

솔직한 결론부터.

**쓰지 말아야 할 이유:**

- **라이선스가 없다.** `LICENSE` 파일도 `package.json` 의 `license` 필드도 없다. 라이선스 없는 공개 리포는 "자유롭게 쓰라"는 뜻이 아니라 기본 저작권이 그대로 살아 있다는 뜻이다. 회사 코드에 넣을 수 없다.
- **npm 에 없다.** `registry.npmjs.org/oh-my-darwin` 은 404다. `npm link` 로 직접 걸어야 한다. 버전은 `0.0.1`.
- **기본 실행 모드가 가드레일 해제다.** 기본값 `omx --madmax --xhigh` 에서 `--madmax` 는 [OMX 문서 표현 그대로](https://github.com/Yeachan-Heo/oh-my-codex) Codex 의 `--dangerously-bypass-approvals-and-sandbox` 단축이다. "정상적인 승인·샌드박스 가드레일을 제거하므로 신뢰할 수 있는 리포와 환경에서만 쓰라"고 상류 문서가 직접 경고한다. Codex 폴백도 같은 플래그를 쓴다. 즉 **Darwin 은 승인 없이 도구를 쓰는 에이전트를 무인으로 최대 30분씩 반복 실행하는 도구다.**
- **3개월 넘게 멈춰 있다.** 마지막 커밋이 5월 19일이다.

**그런데도 읽을 값어치가 있는 이유:**

이 리포는 "에이전트 자기개선 루프"라는 말을 **실행 가능한 명세로 번역해 놓은 참조 구현**이다. 슬라이드에서는 안 보이는 칸들 — 완료 판정, 프로세스 트리 정리, 사용자 훅 샌드박싱, 전략 교체 지점, 상태 파일 레이아웃 — 이 전부 채워져 있고, 어디가 정직하게 비어 있는지(`llm-judge`)도 표시돼 있다.

같은 걸 직접 만들 사람이라면 순서는 이렇다.

1. `src/strategy/contract.ts` — 루프의 교체 가능한 지점을 어디로 자를 것인가
2. `templates/strategies/*.mjs` — 네 가지 탐색 전략이 각각 30줄로 어떻게 표현되는가
3. `src/runtime/goal-attempt.ts` — 대화형 에이전트의 "끝"을 어떻게 판정할 것인가
4. `src/capabilities/manifest.ts` — 에이전트가 제안한 코드를 어떻게 안전하게 받을 것인가

그리고 `src/scorer/` 는 **당신이 직접 풀어야 할 문제가 남아 있는 자리**로 보면 된다. 이 리포가 가장 적게 답한 칸이자, 실제로는 가장 중요한 칸이다.

---

## References

- oh-my-darwin 소스 — <https://github.com/clarence-lee-sheng/oh-my-darwin> (본문의 코드 인용·기본값·파일 구조는 2026-05-19 커밋 `ce991f8` 기준 실측)
- OMX(oh-my-codex) — <https://github.com/Yeachan-Heo/oh-my-codex> (`--madmax` 및 `--xhigh` 정의, `.codex/hooks.json` 훅 표면)
- OpenAI Codex CLI — <https://github.com/openai/codex>
- Mouret, J.-B., & Clune, J. (2015). *Illuminating search spaces by mapping elites.* arXiv:1504.04909 — <https://arxiv.org/abs/1504.04909>
- Lehman, J., & Stanley, K. O. (2011). *Abandoning Objectives: Evolution Through the Search for Novelty Alone.* Evolutionary Computation, 19(2), 189–223 — <https://doi.org/10.1162/EVCO_a_00025>
- Node.js Test runner (`node --test`) — <https://nodejs.org/api/test.html>
