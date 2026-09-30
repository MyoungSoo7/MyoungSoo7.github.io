---
layout: post
title: "Jev 는 Claude Code·Codex 의 모델이 될 수 없다 — 그래서 하네스의 어디에 꽂히는가"
date: 2026-09-30 22:18:00 +0900
categories: [ai]
tags: [jev, typesafe, harness, claude-code, codex, mcp, hooks, agent]
---

"Codex·Claude Code 에 Jev 를 붙인다" 는 말을 들으면 흔히 *모델을 Jev 로 바꾼다*를 떠올린다.
하지만 그건 구조적으로 안 된다. Jev 는 글을 쓰지 않기 때문이다. 이 글은 **Jev 가 코딩 에이전트
하네스의 어느 자리에 들어갈 수 있는지**, 그리고 커뮤니티 구현들이 그 자리를 어떻게 설계했는지를
1차 문서와 README 기준으로 정리한다.

> 공개: 이 글은 Anthropic 의 Claude(Claude Code)로 작성했다. Claude Code 는 이 글이 다루는 대상
> 중 하나다. 제품 간 우열은 주장하지 않는다.

이전 글과 겹치지 않게, Jev 자체의 개념(System One, 보정된 확률)은
[System One 과 LLM 의 차이]({% post_url 2026-09-19-jev-system-one-vs-llm-era %}),
신뢰도 게이트는 [신뢰도 게이트 가이드]({% post_url 2026-09-20-jev-confidence-gate-korean-guide %}),
라우터 이득 측정은 [라우터 모델은 원장 없이 평가할 수 없다]({% post_url 2026-09-23-router-model-needs-a-usage-ledger %})
를 보면 된다. 여기서는 **배선도**만 다룬다.

## 1. 왜 "모델 교체" 가 불가능한가

TypeSafe 공식 문서는 System One 모델을 이렇게 정의한다. Jev 는 상태를 평가해 **타입이 정해진
답과 확률**을 돌려주고, *답장·코드·추론 설명을 생성하지 않는다*
([docs.typesafe.ai — System One](https://docs.typesafe.ai/concepts/system-one)).
질문 형식도 세 가지로 고정돼 있다.

| 프리미티브 | 돌려주는 것 |
| --- | --- |
| Choice | 미리 정한 선택지 중 하나 + 분포 |
| Score | 정의한 척도 위의 값 |
| Noul | 참/거짓 확률 하나 |

호출 경로도 `POST /v1/systemone` 전용이다. Claude Code 는 `ANTHROPIC_BASE_URL` 로 게이트웨이를
바꿀 수 있지만, Anthropic 문서는 **게이트웨이를 통해 Claude Code 를 Claude 가 아닌 모델로
라우팅하는 것을 지원하지 않는다**고 적는다
([Claude Code — LLM gateways](https://code.claude.com/docs/en/llm-gateway)).
Codex 도 커스텀 provider 를 정의할 수 있지만 그건 채팅/응답 API 를 말하는 모델을 전제로 한다
([Codex — Advanced configuration](https://developers.openai.com/codex/config-advanced)).
텍스트를 못 내는 모델은 에이전트 루프의 "생각하는 자리" 에 앉을 수 없다.

그래서 Jev 가 들어갈 자리는 **루프 옆**이다. LLM 이 제안하고, Jev 가 좁은 질문에 답하고,
코드가 결정한다.

## 2. 네 개의 꽂는 자리

| 자리 | 대표 구현 | 출처 성격 | Jev 가 하는 일 |
| --- | --- | --- | --- |
| ① 스킬 | `typesafe-ai/skills` | **TypeSafe 공식** | 에이전트가 필요할 때 Jev API 를 부르는 법을 배운다 |
| ② 모델 라우터(프록시) | `gargpratyush/jev-router` | 커뮤니티 | 매 턴 "어느 등급 모델에 보낼지" 판정 |
| ③ MCP 도구 | `jkudish/jev-mcp` | 커뮤니티 | 검증·분류·리랭크 등 판정을 도구로 노출 |
| ④ 훅·제안 심사 | `TypeSafeAI/jev-harness` | 커뮤니티(공식 아님) | LLM 의 제안 하나를 네 질문으로 심사 |

### ① 공식 스킬 — 가장 얇은 연결

TypeSafe 가 직접 내는 건 에이전트 스킬이다
([github.com/typesafe-ai/skills](https://github.com/typesafe-ai/skills), MIT).
Claude Code 에서는 플러그인 마켓플레이스로 설치한다.

```bash
claude plugin marketplace add typesafe-ai/skills
claude plugin install typesafe@typesafe-ai
```

Codex 등 다른 에이전트는 `npx skills add typesafe-ai/skills --skill typesafe-ai` 를 쓴다.
스킬은 "Jev 를 이렇게 부르면 된다" 는 지식을 컨텍스트에 넣는 것일 뿐, 하네스의 제어 흐름은
바꾸지 않는다. **부를지 말지는 여전히 LLM 이 정한다.** 가장 안전하지만 가장 약한 연결이다.
참고로 TypeSafe 는 공식 MCP 서버를 내지 않았다 — MCP 는 전부 커뮤니티 구현이다.

### ② 라우터 프록시 — 모델 *선택*만 맡긴다

`jev-router` 는 모델을 Jev 로 바꾸는 대신 **어느 Claude/GPT 모델을 쓸지를 Jev 에게 묻는다**
([README](https://github.com/gargpratyush/jev-router)). `jev-claude`·`jev-codex` 가 루프백
프록시를 띄우고 진짜 CLI 를 실행하며, README 는 "Jev 는 새 사용자 턴의 모델만 고른다" 고
적는다. 기존 `claude login`·`codex login` 인증을 그대로 쓰고, Codex 쪽은 임시 provider 를
끼워 넣는다.

README 에 적힌 정책에서 배울 점이 많다. 판정은 확률이지만, **정책은 코드에 박혀 있다.**

- 사용자가 `/model` 로 명시하면 라우팅을 멈춘다 — 사람의 지시가 이긴다.
- Jev 호출이 실패하면 현재 모델을 유지한다(fail-open).
- 신뢰도가 낮으면 **다운그레이드는 안 하고**, 업그레이드는 중간 등급까지만 한다.
- 대화가 크면 다운그레이드를 거부한다 — 모델을 바꾸면 프롬프트 캐시를 버리게 되기 때문이다.
- 결정 근거(요청·응답 원문)를 세션별 임시 파일(권한 600)에 남기고 `/jev-explain` 으로 보여준다.

네 번째 항목이 특히 좋은 예다. "싼 모델로 보내면 싸다" 는 직관이, 긴 대화에선 캐시 재작성
비용 때문에 틀릴 수 있다. 판정 모델이 모르는 비용을 **정책 코드가 안다.**

단, 이 라우터가 실제로 비용을 얼마나 줄이는지에 대한 중립 측정은 찾지 못했다. README 에도
절감률 수치는 없다. 내 사용 패턴에서 라우팅 이득이 얼마나 작았는지는
[이전 글]({% post_url 2026-09-23-router-model-needs-a-usage-ledger %})에 적었다.

### ③ MCP 도구 — 판정을 LLM 의 손에 쥐여 준다

`jev-mcp` 는 Jev 판정을 11개 MCP 도구로 노출한다(`jev_verify`, `jev_screen`, `jev_review`,
`jev_gate` 등, [README](https://github.com/jkudish/jev-mcp)). 등록은 양쪽 다 한 줄이다.

```bash
claude mcp add jev -- npx -y @jkudish/jev-mcp
```

```toml
# ~/.codex/config.toml
[mcp_servers.jev]
command = "npx"
args = ["-y", "@jkudish/jev-mcp"]
```

README 는 응답 시간을 "대략 150~500ms, 1센트 미만" 으로 적는데, 이건 **구현자 주장**이고 내가
재현하지 않았다. 구조적 한계는 ① 과 같다. 도구를 *부를지*는 LLM 이 정하므로, 가장 필요한 순간에
안 부를 수 있다. README 가 "등록만 되고 안 쓰이는 도구" 문제를 풀려고 별도 스킬을 동봉한 것도
이 때문이다.

### ④ 제안 심사 하네스 — LLM 이 아니라 코드가 Jev 를 부른다

가장 흥미로운 건 `TypeSafeAI/jev-harness` 다
([README](https://github.com/TypeSafeAI/jev-harness)). 먼저 출처부터 분명히 하자. README 는
스스로 **"TypeSafeAI 커뮤니티 조직이며 공식 TypeSafe AI 팀과 독립적이고, 공식 SDK 나 보증된
프로덕션 런타임이 아니다"** 라고 밝힌다. 연구 단계다.

계약은 한 문장이다. *LLM 이 행동 하나를 제안하고, Jev 가 좁은 질문 네 개에 답하고, 코드가
증거를 만든다.* 그리고 굵게 적혀 있다 — 이 저장소는 **패치를 적용하지도, 제안된 코드를
실행하지도, 권한을 주지도 않는다.**

```text
호스트가 작업과 제안 1건을 받는다
  -> 호스트가 스키마·범위·경로·diff 를 검증한다
  -> (검증 통과 시에만) Jev 심사를 받는다
  -> decide(validation, review, threshold)
  -> 호스트가 증거를 기록하고, 할 일은 따로 결정한다
```

질문 세트(v4)는 네 개, 모델은 `jev-1.13.0` 에 고정, 임계값은 0.8 로 고정이다.

| 질문 ID | 바람직한 답 |
| --- | --- |
| `addresses_task` — 작업을 해결하는가 | yes |
| `evidence_supports` — 인용한 증거가 뒷받침하는가 | yes |
| `unrelated_changes` — 무관한 변경이 섞였는가 | no |
| `needs_clarification` — 사람에게 되물어야 하는가 | no |

이 설계에서 읽어낼 원칙은 세 가지다.

1. **싼 검사가 먼저, 비싼 판정은 나중.** 검증에 실패한 제안에는 Jev 를 부르지 않는다. 파일
   경로가 범위 밖이면 확률을 물을 이유가 없다.
2. **판정은 권한이 아니다.** `decide()` 는 결과를 받을 뿐, 호의적 결과가 나와도 행동을 허가하지
   않는다. 실행 권한은 호스트(여기선 Claude Code·Codex 의 권한 시스템)가 끝까지 쥔다.
3. **신뢰도의 뜻을 과장하지 않는다.** Noul 답을 `p ≥ 0.5 ? yes : no`, 신뢰도를 `max(p, 1−p)`
   로 계산하는데, 이건 *분포의 통계량*이지 "이 제안이 맞을 확률" 이 아니다. TypeSafe 문서도
   보정(calibration)은 예측 집단에 대해 측정되며 개별 답의 정답을 보장하지 않는다고 적는다
   ([docs.typesafe.ai — System One](https://docs.typesafe.ai/concepts/system-one)).

⚠️ README 의 `pnpm bench:review` 결과(기본 7/25 → +Jev 25/25)는 README 스스로 **스크립트된 mock
값이며 Jev 의 측정이 아니라고** 밝힌다. 성능 근거로 인용하면 안 된다.

## 3. Claude Code·Codex 쪽 소켓: 훅

④ 를 실제 에이전트에 붙이는 소켓은 양쪽 모두 **PreToolUse 훅**이다. Claude Code 훅은 도구
호출 직전에 JSON 입력을 받아 `permissionDecision: "deny"` 로 막을 수 있다
([Claude Code — Hooks reference](https://code.claude.com/docs/en/hooks)). Codex 도 `hooks.json`
이나 `config.toml` 의 `[[hooks.PreToolUse]]` 로 같은 구조의 훅을 받고, 프로젝트 로컬 훅은
신뢰된 프로젝트에서만 로드한다
([Codex — Advanced configuration](https://developers.openai.com/codex/config-advanced)).

그러면 배선은 이렇게 된다.

```text
LLM(Claude/GPT)이 Edit/Bash 호출을 제안
  → PreToolUse 훅 (코드)
      ├ 경로·범위·diff 결정론 검사  ── 실패 → deny (Jev 호출 없음)
      ├ Jev: 네 질문 Noul 병렬 질의
      └ 임계값 미달·호출 실패 → "ask"(사람에게) — 자동 허가로 기울지 않기
  → 통과해도 CLI 의 원래 권한 프롬프트·샌드박스는 그대로
```

주의할 점: ② 라우터는 Jev 실패 시 fail-open(현재 모델 유지)이 맞지만, **심사 게이트에서의
fail-open 은 "검사 없이 통과"** 가 된다. 같은 "실패하면 그냥 진행" 이라도 자리에 따라 뜻이
정반대다. 라우팅은 품질 문제, 게이트는 안전 문제이기 때문이다. 게이트는 실패 시 사람에게
넘기는 쪽(fail-to-human)이 맞다고 본다 — 이건 내 설계 의견이다.

## 4. 정리 — 무엇을 고를까

- **그냥 써 보고 싶다** → ① 공식 스킬. 공식 출처이고 제어 흐름을 안 건드린다.
- **토큰 비용이 문제** → ② 라우터. 단, 먼저 내 사용량에서 라우팅이 몇 번 일어나는지 재 볼 것.
- **사실 확인·분류를 에이전트가 싸게 하게** → ③ MCP. 호출 여부는 LLM 재량이라는 점을 감안.
- **LLM 행동을 코드가 심사** → ④ 의 계약을 참고해 훅으로 직접 구현. 저장소는 연구용 참고
  구현이지 가져다 쓰는 런타임이 아니다.

공통 교훈은 하나다. **Jev 는 결정을 내리지 않는다. 결정의 재료를 싸게 만든다.** 결정은
fail-open/fail-closed 를 아는 코드와, 끝까지 권한을 쥐는 하네스가 내린다. 모델이 좋아질수록
이 경계를 코드로 적어 두는 쪽이 더 중요해진다.

### 근거의 한계

- ② ③ ④ 는 모두 커뮤니티 구현이다. 나온 지 2주 안팎(2026-09-16~22 생성)이라 인터페이스가
  바뀔 수 있다.
- Jev 판정을 붙였을 때 코딩 에이전트의 결과 품질이나 비용이 좋아진다는 **중립 제3자
  헤드투헤드 측정은 찾지 못했다.** "N배 빠르다" 류의 수치는 인용하지 않았다.

## References

1. TypeSafe, *System One* — <https://docs.typesafe.ai/concepts/system-one>
2. TypeSafe, *Introducing System One models and Jev* — <https://typesafe.ai/blog/introducing-system-one-models-and-jev>
3. TypeSafe, 공식 에이전트 스킬 `typesafe-ai/skills` — <https://github.com/typesafe-ai/skills>
4. Anthropic, *Claude Code — Hooks reference* — <https://code.claude.com/docs/en/hooks>
5. Anthropic, *Claude Code — Other LLM gateways* — <https://code.claude.com/docs/en/llm-gateway>
6. OpenAI, *Codex — Advanced configuration* (profiles, providers, hooks) — <https://developers.openai.com/codex/config-advanced>
7. gargpratyush, `jev-router` (커뮤니티) — <https://github.com/gargpratyush/jev-router>
8. jkudish, `jev-mcp` (커뮤니티) — <https://github.com/jkudish/jev-mcp>
9. TypeSafeAI 커뮤니티 조직, `jev-harness` (비공식·연구 단계) — <https://github.com/TypeSafeAI/jev-harness>
