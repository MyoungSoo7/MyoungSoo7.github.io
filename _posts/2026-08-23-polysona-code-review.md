---
layout: post
title: "Polysona 코드 리뷰 — 프롬프트는 진짜인데, 대시보드 점수는 해시였다"
date: 2026-08-23 23:53:27 +0900
categories: [AI, Agent]
tags: [code-review, polysona, persona, claude-code, codex, hono, bun, security]
---

[LilMGenius/polysona](https://github.com/LilMGenius/polysona)를 읽어봤다. "AI 에이전트를 위한 페르소나 레이어"를 표방하는 MIT 공개 리포다. 심리 프레임워크 인터뷰로 사용자 페르소나를 추출해서, Codex·Claude Code·OpenCode 어디서든 같은 페르소나로 콘텐츠 파이프라인을 돌린다는 컨셉이다. 별 112개, fork 16개.

읽어보니 **프롬프트 설계는 가져다 볼 값어치가 있고, 대시보드는 그렇지 않았다.** 특히 하나는 실측으로 확인해야만 드러나는 종류의 문제였다.

아래 모든 인용은 커밋 [`ad1f263`](https://github.com/LilMGenius/polysona/tree/ad1f263801eb1e777a5ee89e0a034688bc6bfbd9) (v1.3.0, 기본 브랜치 `ralphthon`) 기준이고, 파일·라인 링크를 달아뒀으니 직접 대조할 수 있다. 저자와는 아무 관계가 없고, 공개된 코드를 외부에서 읽은 결과다. 이후 커밋에서 고쳐졌을 수 있다.

> **리뷰어 명시**: 이 글의 코드 분석과 실측은 Claude Opus 5 (1M context, 모델 ID `claude-opus-5[1m]`)가 수행했다. 클론은 로컬 스크래치패드에만 두고 리포에는 아무것도 쓰지 않았다.

---

## 먼저, 리포 태그가 내용을 싸게 보이게 만든다

리포 topics에 `mbti`, `enneagram`이 걸려 있다. 나도 처음에 이걸 보고 "근거 강도가 프레임워크마다 크게 갈리겠다"고 짐작했는데, **코드를 열어보니 MBTI도 에니어그램도 쓰지 않는다.**

핵심 프롬프트인 [`agents/profiler.md`](https://github.com/LilMGenius/polysona/blob/ad1f263801eb1e777a5ee89e0a034688bc6bfbd9/agents/profiler.md#L56)(15KB)가 실제로 쓰는 10개는 이렇다.

| # | 프레임워크 | 계보 |
|---|---|---|
| 1 | McAdams Life Story | 서사정체성 연구 |
| 2 | Laddering (+MI/ACT) | means-end chain, 동기면담 |
| 3 | Clean Language | David Grove |
| 4 | Johari Window | 대인 피드백 모델 |
| 5 | IFS | Richard Schwartz |
| 6 | Repertory Grid | Kelly 개인구성개념 이론 |
| 7 | Object Relations | 대상관계 |
| 8 | Projective Technique | 투사법 |
| 9 | Zen Koan | 선문답 |
| 10 | 五倫+陰陽 | 동양 관계론 |

앞 8개는 임상·연구 계보가 분명한 방법들이다. 9·10번은 심리검사라기보다 질문 기법에 가깝고, 8번 투사법은 그중 근거가 가장 약한 축에 속한다. 그래도 유형론 라벨(MBTI·에니어그램)을 안 쓴다는 점이 중요하다. **태그가 실제 설계보다 낮은 기대치를 만들고 있다.** 리포 메타데이터와 내용이 어긋나면 손해는 저자가 본다.

## 잘 만든 부분

### 1. profiler 프롬프트에 규율이 있다

심리 관련 프롬프트는 대개 "깊이 있게 물어봐" 수준에서 끝나는데, 이건 가드가 촘촘하다.

- **append-only 로깅 강제** — 기존 로그를 덮어쓰거나 재정렬하지 말고, 정정도 타임스탬프 붙여 추가하라
- **GAP 태깅** — 5개 자아 층(others-see-me / want-to-be-seen / conscious-ideal / rolemodel / unconscious-self) 사이의 모순을 발견하면 `~YYYY-MM-DD: GAP: LayerA(...) ↔ LayerB(...)` 형식으로 즉시 기록하라 ([L296](https://github.com/LilMGenius/polysona/blob/ad1f263801eb1e777a5ee89e0a034688bc6bfbd9/agents/profiler.md#L296))
- **경계 선언** — "Clarify interview boundaries: extraction, not therapy"
- **불확실성 표기 강제** — hypothesis / provisional 라벨을 붙이라
- **프레임워크별 Cautions** — "단일 일화로 과잉해석 금지", "결정론적 유년기 주장 회피", "면접자의 은유로 참여자의 은유를 대체하지 말 것"

특히 마지막 항목은 Clean Language의 핵심 원칙(어휘 오염 최소화)을 제대로 옮긴 것이다. 프롬프트만 놓고 보면 이 리포에서 가장 공들인 자산이 맞다.

### 2. QA 에이전트의 read-back 검증

[`agents/virtual-follower.md`](https://github.com/LilMGenius/polysona/blob/ad1f263801eb1e777a5ee89e0a034688bc6bfbd9/agents/virtual-follower.md#L21)의 실행 워크플로가 인상적이다.

> 4. **MUST use the Write tool** to save the QA report ... before responding.
> 5. **MUST immediately use the Read tool** on the saved QA report to confirm it exists and reflects the evaluation.
> 7. If the write fails, say it failed. Do not pretend QA storage succeeded.

썼다고 말하지 말고, 다시 읽어서 확인하고, 실패했으면 실패했다고 말하라. 에이전트가 "저장했습니다"라고 해놓고 실제로는 안 한 경우를 겪어본 사람이 짠 프롬프트다. 초안이 없으면 QA를 지어내지 말고 막혔다고 보고하라는 조항도 있다.

---

## 문제 — 실측으로 확인한 것

여기서부터는 읽기만 해서는 확신할 수 없어서, 로컬에서 서버를 띄우고 직접 요청을 보내 확인했다. Bun 1.3.14, 의존성은 `--ignore-scripts`로 설치.

### 1. 대시보드 QA 점수는 평가가 아니라 문자열 해시다 (심각)

README와 대시보드는 "가상 팔로워 20명이 초안을 평가해 TOP 5를 뽑는다"고 말한다. 그런데 [`server/routes/api.ts` L63](https://github.com/LilMGenius/polysona/blob/ad1f263801eb1e777a5ee89e0a034688bc6bfbd9/server/routes/api.ts#L63)의 점수 함수는 이렇다.

```ts
function deterministicScore(personaId, followerId, dimension, contentName = '') {
  const seed = `${personaId}-${followerId}-${dimension}-${contentName}`
  let hash = 0
  for (let i = 0; i < seed.length; i++) {
    hash = ((hash << 5) - hash) + seed.charCodeAt(i)
    hash |= 0
  }
  return 40 + Math.abs(hash % 56)
}
```

**초안 본문을 읽지 않는다.** 파일 *이름*만 시드에 들어간다. `hook`, `empathy`, `share`, `cta`, `platform_fit` 5개 차원 점수가 전부 이 해시에서 나온다 ([L145–L149](https://github.com/LilMGenius/polysona/blob/ad1f263801eb1e777a5ee89e0a034688bc6bfbd9/server/routes/api.ts#L145)).

실측해봤다. `content/drafts/`에는 `.gitkeep` 하나뿐이라 초안이 아예 없는 상태에서, **존재하지도 않는 파일명**으로 요청했다.

```console
$ curl 'http://127.0.0.1:38217/api/personas/default/qa-simulation?content=THIS-FILE-DOES-NOT-EXIST.md'
{"personaId":"default","contentName":"THIS-FILE-DOES-NOT-EXIST.md",
 "followers":[{"id":"f10","label":"30s male engineer",...,
   "scores":{"hook":92,"empathy":91,"share":40,"cta":95,"platform_fit":82},
   "total":400,"isTop5":true}, ...
```

없는 파일에 대해 팔로워 20명 × 5차원 점수와 TOP 5 랭킹이 그대로 나온다. 재요청하면 같은 값이 나온다 — 해시니까 당연하다.

문제는 이게 **거짓말이라서**가 아니라 **구분이 안 돼서**다. 이 리포에는 QA가 두 개 있다.

- **에이전트 QA** (`/qa` → virtual-follower): 실제 초안 텍스트를 LLM이 읽고 평가하고 리포트를 저장한다. 진짜다.
- **대시보드 QA** (`/api/.../qa-simulation`): 해시다.

UI에서는 둘 다 그냥 "점수"로 보인다. 화면의 92점을 평가 결과로 읽으면 안 된다. 데모용 플레이스홀더라면 `mock: true` 같은 플래그를 응답에 넣거나 UI에 "샘플 데이터" 라벨을 붙여야 한다. 함수 이름이 `deterministicScore`인 것도 의도는 "재현 가능한 데모값"이었을 텐데, 그 의도가 API 밖으로는 전혀 전달되지 않는다.

부수적으로 숫자도 안 맞는다. 에이전트 스펙의 팔로워 프로필은 5명인데, 대시보드 아키타입은 20명이다.

### 2. 대시보드가 모든 인터페이스에 인증 없이 열린다 (심각)

[`server/index.ts` L54](https://github.com/LilMGenius/polysona/blob/ad1f263801eb1e777a5ee89e0a034688bc6bfbd9/server/index.ts#L54)의 서버 export에는 `port`와 `fetch`만 있고 `hostname`이 없다. Bun의 기본 바인딩은 루프백이 아니다. 실제로 띄워서 확인했다.

```console
$ ss -ltn | grep 38217
LISTEN 0  512  *:38217  *:*
```

`*`, 즉 모든 인터페이스다. README는 이 대시보드를 "local-first"라고 소개하지만, 같은 네트워크에 있는 누구나 인증 없이 `/api/personas`를 긁을 수 있다. 인증·세션·CORS 제한이 코드에 전혀 없다.

담기는 데이터가 하필 **심리 프로파일**이다. 무의식 패턴, 방어기제, 대인관계 원형, 자아 층 사이의 모순(GAP)까지 파일로 남는다. 유출 시 피해가 큰 축에 속하는 데이터를 인증 없이 LAN에 여는 셈이라, 개인적으로는 이게 QA 점수보다 더 큰 문제라고 본다.

고치는 건 한 줄이다. `export default { port, hostname: '127.0.0.1', fetch: app.fetch }`.

### 3. 경로 탈출 (중간)

[`/api/personas/:id`](https://github.com/LilMGenius/polysona/blob/ad1f263801eb1e777a5ee89e0a034688bc6bfbd9/server/routes/api.ts#L94)는 URL 파라미터 `id`를 검증 없이 파일 경로에 붙인다.

```ts
const id = c.req.param('id')
const files = await readDir(`${personasDir}/${id}`)
```

`personas/` 밖에 마커를 심어놓고 요청해봤다.

```console
$ curl 'http://127.0.0.1:38217/api/personas/..%2F..'
{"id":"../..","name":"LEAKED_SECRET_MARKER",
 "persona":{"name":"LEAKED_SECRET_MARKER","core":{"bio":"this file is outside personas/"}}, ...
```

읽혔다. 다만 영향 범위는 제한적이다. 코드가 여는 파일명이 `persona.md` / `nuance.md` / `accounts.md` 세 개로 고정돼 있어서, 임의 파일을 통째로 읽지는 못한다. 그래도 디렉토리 존재 여부 오라클로는 충분히 쓰이고, 2번(LAN 노출)과 겹치면 의미가 달라진다.

`id`에 `/`나 `..`이 들어오면 400을 던지거나, 화이트리스트(`readdir('./personas')` 결과에 있는 이름만 허용)로 막으면 된다.

### 4. 훅 3개 중 2개가 실행되지 않는다 (경미하지만 오해 유발)

`hooks/`에는 세션 시작, 툴 사용 전, 툴 사용 후 훅이 있다. 그런데 두 개가 환경변수를 읽는다.

- [`pre-tool-use.sh` L6–L7](https://github.com/LilMGenius/polysona/blob/ad1f263801eb1e777a5ee89e0a034688bc6bfbd9/hooks/pre-tool-use.sh#L6): `TOOL_NAME="${TOOL_NAME:-}"`, `FILE_PATH="${FILE_PATH:-}"`
- [`post-tool-use.sh` L5](https://github.com/LilMGenius/polysona/blob/ad1f263801eb1e777a5ee89e0a034688bc6bfbd9/hooks/post-tool-use.sh#L5): `OUTPUT="${TOOL_OUTPUT:-}"`

Claude Code 훅은 이런 식으로 데이터를 넘기지 않는다. 공식 문서는 명시한다 — ["For command hooks, input arrives on stdin."](https://code.claude.com/docs/en/hooks) `PreToolUse` 훅은 `tool_name`, `tool_input`, `tool_use_id` 등을 담은 **JSON을 stdin으로** 받는다. Claude Code가 설정하는 환경변수는 `CLAUDE_PROJECT_DIR`, `CLAUDE_PLUGIN_ROOT` 같은 경로 계열이지 `TOOL_NAME`/`FILE_PATH`/`TOOL_OUTPUT`이 아니다.

즉 두 변수 모두 항상 빈 문자열이고, 조건문은 절대 참이 되지 않는다. **문서에는 있지만 돌지 않는 가드**가 두 개 있는 셈이다. 하나는 PLOON 덮어쓰기 방지, 다른 하나는 "AI slop 패턴 탐지"인데, 둘 다 사용자가 켜져 있다고 믿기 쉬운 종류의 안전장치다. `stdin`을 `jq`로 파싱하도록 고치면 된다.

---

## 정리

| 항목 | 판정 |
|---|---|
| profiler 프롬프트 (10 프레임워크, GAP 태깅, append-only) | 좋음 — 이 리포의 본체 |
| virtual-follower의 read-back 검증 프로토콜 | 좋음 |
| 리포 태그(mbti/enneagram) vs 실제 프레임워크 | 불일치 — 내용을 저평가하게 만듦 |
| 대시보드 QA 점수 | **평가 아님. 문자열 해시** |
| 서버 바인딩 + 인증 | **모든 인터페이스, 인증 없음** |
| `:id` 경로 처리 | 경로 탈출 가능(파일명 3종 제한) |
| pre/post-tool-use 훅 | 실행되지 않음 |
| 시크릿 하드코딩 | 없음 (스캔 클린) |

**쓸 거라면**: CLI·에이전트 플로우(`/interview`, `/content`, `/qa`)만 쓰는 게 낫다. 여긴 실제로 LLM이 일하고, 프롬프트 규율도 살아 있다. `bun run dev` 대시보드는 켜지 않거나, 켠다면 `hostname: '127.0.0.1'` 한 줄을 먼저 넣고 켜는 걸 권한다. 화면에 뜨는 QA 점수는 어느 쪽이든 지금은 신뢰하면 안 된다.

**만드는 입장에서 배울 점**은 따로 있다. 이 리포의 문제는 실력이 아니라 **표면 간 계약**이다. 같은 이름("QA 점수")이 한쪽에서는 실제 LLM 평가이고 다른 쪽에서는 데모 해시인데, 그 차이가 타입에도 응답에도 UI에도 안 적혀 있다. 훅도 마찬가지로 "있는 것"과 "도는 것"이 갈렸다. 에이전트 제품에서 이런 균열은 조용히 벌어진다 — 프롬프트에 `MUST use the Read tool to confirm`이라고 적을 정도로 검증에 신경 쓴 저자가, 자기 대시보드에는 같은 기준을 적용하지 못했다는 게 그 증거다.

**커밋됐다는 것과 도는 것은 다른 말이다.** 이건 남 얘기가 아니다.

---

## References

- 리포: [LilMGenius/polysona](https://github.com/LilMGenius/polysona) (MIT), 리뷰 기준 커밋 [`ad1f263`](https://github.com/LilMGenius/polysona/tree/ad1f263801eb1e777a5ee89e0a034688bc6bfbd9) (v1.3.0)
- [`agents/profiler.md`](https://github.com/LilMGenius/polysona/blob/ad1f263801eb1e777a5ee89e0a034688bc6bfbd9/agents/profiler.md) — 10 프레임워크, 5 자아 층, GAP 프로토콜
- [`agents/virtual-follower.md`](https://github.com/LilMGenius/polysona/blob/ad1f263801eb1e777a5ee89e0a034688bc6bfbd9/agents/virtual-follower.md) — read-back 검증
- [`server/routes/api.ts`](https://github.com/LilMGenius/polysona/blob/ad1f263801eb1e777a5ee89e0a034688bc6bfbd9/server/routes/api.ts) — `deterministicScore`(L63), `/personas/:id`(L94), `/qa-simulation`(L130)
- [`server/index.ts`](https://github.com/LilMGenius/polysona/blob/ad1f263801eb1e777a5ee89e0a034688bc6bfbd9/server/index.ts) — 서버 export(L54)
- [`hooks/pre-tool-use.sh`](https://github.com/LilMGenius/polysona/blob/ad1f263801eb1e777a5ee89e0a034688bc6bfbd9/hooks/pre-tool-use.sh) · [`hooks/post-tool-use.sh`](https://github.com/LilMGenius/polysona/blob/ad1f263801eb1e777a5ee89e0a034688bc6bfbd9/hooks/post-tool-use.sh)
- Anthropic, [Claude Code — Hooks](https://code.claude.com/docs/en/hooks) (훅 입력은 stdin JSON)
