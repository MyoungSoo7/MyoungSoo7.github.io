---
layout: post
title: "토큰 80% 아끼는 설정 5개 — 공식 문서로 하나씩 검증했다"
date: 2026-08-23 04:56:48 +0900
categories: [AI, LLM]
tags: [prompt-caching, token, mcp, tool-search, openai, anthropic, cost]
---

이런 이미지를 받았다.

![ChatGPT 토큰 80% 아끼는 설정 5개](/assets/images/token-saving-5-settings.jpg)

다섯 항목 자체는 방향이 맞다. 다만 이런 카드뉴스가 늘 그렇듯 **왜 그런지, 어디까지가 사실인지, 어떤 조건에서 안 통하는지**가 빠져 있다. 그래서 OpenAI와 Anthropic 공식 문서만 놓고 한 항목씩 확인했다.

먼저 제목의 "80%"부터. 이 숫자는 **두 벤더 공식 문서 어디에도 없다.** 실제로 문서에 적힌 수치는 이렇다.

- OpenAI: GPT-5.6 이상에서 캐시된 입력 토큰은 **비캐시 입력 요금의 0.1배**로 과금된다 ([Prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching)).
- Anthropic: 캐시 읽기 **0.1배**, 캐시 쓰기는 5분 TTL **1.25배** / 1시간 TTL **2배** ([Prompt caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)).

즉 할인은 "요청 전체"가 아니라 **캐시에 적중한 접두부(prefix)에 한해** 90%다. 그리고 Anthropic 쪽은 쓰기 프리미엄이 있어서, 5분 TTL은 최소 2회, 1시간 TTL은 최소 3회는 재사용해야 본전이다. 한 번 쓰고 마는 프롬프트에 캐시를 켜면 오히려 손해다.

이 전제를 깔고 5개 항목을 본다.

---

## 1. 캐시 적중률 높이기 — 맞다. 단, 최소 길이와 렌더 순서가 있다

카드의 "고정 규칙은 앞에, 바뀌는 요구사항은 뒤에"는 정확하다. 두 벤더 모두 **접두부 완전 일치(exact prefix match)** 방식이기 때문이다. OpenAI 문서는 "Cache hits are only possible for exact prefix matches within a prompt"라고 못박고, 지침·툴·스키마·공유 컨텍스트를 고정하고 요청별 내용을 그 뒤에 두라고 안내한다.

Anthropic은 렌더 순서를 명시한다: **`tools` → `system` → `messages`**. 프롬프트 맨 앞이 `tools`라는 사실이 4번 항목의 근거가 되므로 기억해 둘 것.

카드가 빠뜨린 조건 세 가지.

**(a) 최소 캐시 길이가 있다.** 그보다 짧으면 에러 없이 조용히 캐시가 안 잡힌다. Anthropic 기준:

| 모델 | 최소 캐시 토큰 |
|---|---|
| Claude Opus 5 / Fable 5 / Mythos 5 | 512 |
| Opus 4.8, Sonnet 5, Sonnet 4.6/4.5, Opus 4.1/4, Sonnet 4 | 1,024 |
| Opus 4.7, Haiku 3.5 | 2,048 |
| Opus 4.6, Opus 4.5, Haiku 4.5 | 4,096 |

**세대가 올라간다고 단조 감소하지 않는다.** 3K 토큰짜리 프롬프트는 Opus 5에서는 캐시되고 Opus 4.6·Haiku 4.5에서는 안 된다. 모델을 바꿨는데 갑자기 캐시 히트가 0이 되면 이걸 의심해야 한다. OpenAI는 기본 1,024 토큰 이상에서 자동 활성화된다.

**(b) breakpoint는 4개까지.** Anthropic은 요청당 `cache_control` 최대 4개다.

**(c) 20블록 lookback.** Anthropic은 breakpoint 하나당 **최대 20개 위치**까지만 뒤로 훑어 캐시 항목을 찾는다. 대화가 길어져 breakpoint가 마지막 캐시 쓰기 지점에서 20블록 이상 밀리면 그 창을 벗어나 조용히 미스가 난다. 툴 호출이 많은 에이전트 루프에서 한 턴에 블록이 20개 넘게 쌓이면 실제로 겪는다. 중간에 breakpoint를 하나 더 박는 게 해법이다.

그리고 **적중을 실측할 것.** Anthropic은 응답 `usage.cache_read_input_tokens` / `cache_creation_input_tokens`로 확인된다. 같은 접두부로 반복 호출하는데 read가 계속 0이면 어딘가에서 조용히 깨지고 있다는 뜻이다. 대표적인 범인은 시스템 프롬프트 안의 `datetime.now()`, UUID, `sort_keys` 없는 `json.dumps()`, 사용자별로 달라지는 툴 목록이다.

## 2. 컨텍스트는 쌓지 말고 깎기 — 맞다. 단, 깎는 방향이 중요하다

목표·결정·제약·다음 행동만 남기라는 조언 자체는 옳다. 문제는 **손으로 깎으면 1번과 정면충돌한다**는 점이다. 오래된 로그를 앞에서 지우면 접두부 바이트가 바뀌고, 그 뒤 전부가 캐시 무효화된다. 절약하려다 매 요청 풀값을 내는 전형적인 패턴이다.

Anthropic은 이걸 API 기능으로 제공한다 ([Context editing](https://platform.claude.com/docs/en/build-with-claude/context-editing), [Compaction](https://platform.claude.com/docs/en/build-with-claude/compaction)).

- `clear_tool_uses_20250919` — 오래된 툴 결과 제거
- `clear_thinking_20251015` — thinking 블록 제거
- `compact_20260112` — 서버 측에서 이전 맥락을 요약 블록으로 압축

전자는 **잘라내기**, 후자는 **요약**이다. 성격이 다르니 섞어 쓰면 안 된다. 그리고 세션 중간에 지시를 추가해야 할 때 top-level `system`을 고치면 대화 전체 접두부가 깨진다. Opus 5 / Opus 4.8 / Fable 5 / Mythos 5는 `messages` 배열에 `{"role": "system", ...}`을 덧붙이는 방식을 지원해서, 캐시된 접두부를 건드리지 않고 지시를 추가할 수 있다.

## 3. 필요한 MCP만 켜기 — 다섯 중 근거가 가장 단단하다

"도구가 많을수록 정의 토큰 증가"는 사실이고, Anthropic 문서에 실제 수치가 있다 ([Tool search tool](https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool)).

> GitHub, Slack, Sentry, Grafana, Splunk를 붙인 전형적인 멀티서버 구성은 **작업을 시작하기도 전에 정의만으로 약 55k 토큰**을 소비한다.

여기에 더 중요한 게 붙는다. **비용만의 문제가 아니다.**

> 사용 가능한 도구가 **30~50개를 넘어가면** Claude의 도구 선택 정확도가 떨어진다.

즉 MCP를 다 켜두면 돈만 더 내는 게 아니라 **답이 나빠진다.** 카드가 "정의 토큰 증가"까지만 말하고 멈춘 부분이 여기다.

해법도 문서에 있다. 도구 정의에 `defer_loading: true`를 걸고 tool search tool을 쓰면, 컨텍스트에는 검색 도구와 비지연 도구만 올라가고 필요할 때만 3~5개가 로드된다. 문서는 이 방식이 **정의 토큰을 85% 이상 줄인다**고 적고 있다. 기준선도 명시돼 있다 — 도구가 10개 이상이거나 정의가 10k 토큰을 넘으면 tool search 검토, 10개 미만이고 매 요청 다 쓰면 그냥 표준 방식.

캐시와의 궁합도 좋다. 지연 로딩된 도구는 시스템 프롬프트 접두부에서 아예 빠지고, 발견되면 대화 중간에 `tool_reference` 블록으로 인라인 추가된다. **접두부가 그대로라 캐시가 유지된다.** 다만 `defer_loading: true`인 도구에 `cache_control`을 같이 걸면 400이 난다. breakpoint는 비지연 도구에 걸어야 한다.

주의: 자주 쓰는 3~5개는 비지연으로 남겨두라는 것, 그리고 **모든 도구를 지연시키면 400 에러**(`At least one tool must have defer_loading=false`)라는 것.

## 4. 프로젝트 설정 고정 — 맞다. 단, "다 깨진다"는 아니다

"구조가 안정적일수록 캐시 재사용 ↑"은 맞지만, 실무에서 필요한 건 **무엇이 무엇을 깨는지**다. Anthropic은 캐시를 3계층(tools / system / messages)으로 두고 표를 공개한다.

| 바뀐 것 | tools 캐시 | system 캐시 | messages 캐시 |
|---|---|---|---|
| 툴 정의(추가·삭제·순서 변경) | ✘ | ✘ | ✘ |
| 모델 교체 | ✘ | ✘ | ✘ |
| web search / citations / speed 토글 | ✓ | ✘ | ✘ |
| 시스템 프롬프트 내용 | ✓ | ✘ | ✘ |
| tool_choice, 이미지 | ✓ | ✓ | ✘ |
| thinking 파라미터 | 모델별 | 모델별 | ✘ |
| effort 설정 | 모델별 | 모델별 | ✘ |
| 메시지 내용 | ✓ | ✓ | ✘ |

(✘ = 무효화, ✓ = 유지)

읽는 법은 간단하다. **툴 정의와 모델 교체만이 전부를 날린다.** `tool_choice`를 요청마다 바꾸거나 이미지를 끼워 넣는 건 tools+system 캐시를 유지한다 — 여기 겁먹을 필요 없다. 반대로 "모드"를 만들겠다고 툴 셋을 갈아끼우는 건 매번 전체 재구축이다. 모드는 툴 교체가 아니라 메시지 내용으로 전달하는 게 맞다.

툴을 정말 바꿔야 한다면 Opus 5부터는 베타로 mid-conversation tool changes(`mid-conversation-tool-changes-2026-07-01`)가 있다. `messages`에 `tool_addition` / `tool_removal` 블록을 넣어 캐시 접두부를 유지한 채 툴 셋을 바꾼다.

## 5. Reasoning 레벨 잠그기 — 절반만 맞다

카드는 "Medium ↔ High 전환 시 캐시 무효화"라고 단정한다. Anthropic 표 기준으로는 **틀리진 않았지만 과장이다.**

`effort` 변경과 `thinking` 파라미터 변경은 **messages 캐시를 무효화**한다. 하지만 tools·system 캐시는 "모델별(model-specific)"이다. 즉 대개 가장 크고 비싼 접두부인 툴 정의 + 시스템 프롬프트는 살아남을 수 있다. "레벨 바꾸면 캐시가 날아간다"가 아니라 "**대화 이력 캐시가 날아간다**"가 정확한 표현이다.

그래서 실무 조언은 카드와 조금 달라진다. 세션 내내 레벨을 못 박는 것보다, **라우트별로 레벨을 정해두고 그 라우트 안에서 일관되게 쓰는 것**이 낫다. 짧은 조회는 낮은 effort, 어려운 에이전트 작업은 높은 effort로 나누는 편이, 전부를 하나로 고정해 쉬운 작업에 과지출하는 것보다 낫다.

---

## 카드에 없지만 알아야 하는 것

**동시 요청은 캐시를 공유하지 못한다.** Anthropic 문서 기준, 캐시 항목은 첫 응답이 **스트리밍을 시작한 뒤에야** 읽을 수 있다. 같은 접두부로 N개를 병렬 발사하면 전부 풀값이다. 팬아웃 패턴이라면 1개를 보내고 첫 토큰이 나온 뒤 나머지를 쏘는 게 맞다.

**프리워밍이 가능하다.** `max_tokens: 0`으로 요청하면 prefill만 돌아 캐시가 쓰이고 즉시 반환된다(출력 토큰 과금 없음). 앱 부팅·배포 직후처럼 트래픽 직전 시점이 있고 첫 요청 지연이 사용자에게 보이는 경우에만 의미가 있다. 트래픽이 TTL보다 촘촘하면 실제 요청이 알아서 데워주므로 불필요한 쓰기 비용만 는다.

**TTL을 확인할 것.** OpenAI GPT-5.6 이상은 지원값이 `30m` 하나이고 그게 기본이다. 이전 모델은 5~10분(최대 1시간) 또는 확장 보존 최대 24시간. Anthropic은 기본 5분, 옵션 1시간이다.

---

## 정리

카드의 다섯 항목은 방향이 맞다. 다만 실제로 적용하려면 이렇게 바뀐다.

1. **캐시 적중** — 고정→변동 순서는 맞다. 여기에 모델별 최소 토큰(512~4096, 단조 감소 아님), breakpoint 4개, 20블록 lookback, 그리고 `cache_read_input_tokens` 실측이 붙는다.
2. **컨텍스트 깎기** — 맞다. 단 앞에서 깎으면 캐시가 깨지므로 context editing / compaction API로 처리한다.
3. **MCP 최소화** — 가장 확실하다. 5개 서버 = 약 55k 토큰, 30~50개 넘으면 선택 정확도 하락, tool search + `defer_loading`으로 정의 토큰 85%+ 절감.
4. **설정 고정** — 전부가 아니라 계층이다. 툴 정의와 모델 교체만이 전체를 날린다.
5. **reasoning 레벨** — messages 캐시만 깨진다. 하나로 잠그기보다 라우트별로 정하는 게 낫다.

그리고 "80%"는 출처가 없다. 실제로는 **캐시 적중한 접두부에 한해 90%**이고, 쓰기 프리미엄 때문에 2~3회는 재사용해야 본전이다. 이 조건을 빼고 절약률만 인용하면, 재사용이 없는 워크로드에서는 오히려 비용이 오른다.

---

## References

- OpenAI, [Prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching)
- Anthropic, [Prompt caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)
- Anthropic, [Tool search tool](https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool)
- Anthropic, [Tool use with prompt caching](https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-use-with-prompt-caching)
- Anthropic, [Context editing](https://platform.claude.com/docs/en/build-with-claude/context-editing)
- Anthropic, [Compaction](https://platform.claude.com/docs/en/build-with-claude/compaction)
