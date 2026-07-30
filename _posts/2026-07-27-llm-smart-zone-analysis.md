---
layout: post
title: "'스마트존 123k' 는 없었다 — 컨텍스트 임계점 주장을 직접 검증한 기록"
date: 2026-07-27 23:50:00 +0900
categories: [ai, llm, engineering]
tags:
  [
    LLM,
    ContextWindow,
    ContextRot,
    Claude,
    ClaudeCode,
    LostInTheMiddle,
    NoLiMa,
    Benchmark,
  ]
---

> **2026-07-31 전면 개정.** 이 글의 초판은 "LLM 의 스마트존은 123k 토큰이며 그 지점에서 추론 정밀도가 15% 이상 하락한다" 고 주장했다. 그 수치에는 출처가 없었고, 검증 결과 근거를 찾지 못했다. 초판의 핵심 주장을 철회하고, 같은 주제를 검증 가능한 자료로 다시 쓴다. 초판을 읽고 인용하신 분들께 사과드린다.

# 틀린 숫자 하나에서 시작한다

초판에는 이렇게 적혀 있었다.

> "고성능 모델들이 정교한 추론 능력을 유지하는 최적의 구간, 즉 '스마트존' 은 약 123k ~ 125k 토큰 부근에서 급격한 변화를 맞이한다. Claude Opus 는 200k 를 지원하지만 **123k 를 기점으로 추론의 정밀도가 15% 이상 하락**하는 현상이 관찰되었다."

이 문장에는 세 가지 문제가 있다.

첫째, **측정 방법이 없다.** 무슨 과제로, 몇 번, 어떤 기준으로 "정밀도" 를 쟀는지 적혀 있지 않다. 재현할 수 없는 수치는 수치가 아니다.

둘째, **출처가 없다.** 15% 라는 숫자를 뒷받침하는 논문도, 벤더 문서도, 공개된 벤치마크도 인용되어 있지 않다.

셋째, **결론의 형태가 틀렸다.** 뒤에서 보겠지만 컨텍스트 성능 저하는 "임계점을 넘으면 떨어진다" 는 계단 함수가 아니다. 훨씬 이르게, 훨씬 완만하게, 그리고 **과제에 따라 다르게** 시작된다.

이 글은 그 세 가지를 순서대로 고친다.

# 1. 성능 저하는 실재한다 — 다만 위치의 문제다

컨텍스트가 길어지면 모델이 흔들린다는 관찰 자체는 사실이고, 잘 알려진 1차 연구가 있다.

Liu 등의 「Lost in the Middle」(TACL 2024) 은 다문서 QA 와 키-값 검색 두 과제에서, **정답이 담긴 문서의 위치만 바꿔가며** 성능을 측정했다. 결과는 뚜렷한 U 자 곡선이었다. 정답이 컨텍스트의 맨 앞이나 맨 뒤에 있을 때 성능이 가장 높고, 중간에 있을 때 가장 낮다.

논문이 보고한 구체적 수치는 이렇다. GPT-3.5-Turbo 의 다문서 QA 성능은 정답 위치에 따라 **20% 이상** 차이가 났고, 최악의 경우 **문서를 하나도 주지 않았을 때(56.1%)보다 낮았다.** 문서를 20개에서 50개로 늘려도 성능은 1.5% 남짓 오르는 데 그쳤다. 검색기가 더 많이 찾아와도 읽는 쪽이 못 쓴 것이다.

여기서 중요한 건 이 저하가 **총 토큰 수의 임계점이 아니라 정보의 위치**에서 왔다는 점이다. "123k 를 넘으면" 이 아니라 "중간에 묻히면" 이다.

# 2. 저하는 123k 보다 훨씬 일찍 시작된다

더 결정적인 반증은 Modarressi 등의 「NoLiMa」(ICML 2025) 다.

기존 needle-in-a-haystack 평가는 질문과 정답 문장이 같은 단어를 공유해서, 모델이 문자열 매칭만으로도 풀 수 있었다. NoLiMa 는 질문과 정답의 **어휘 중복을 최소화**해 연상 추론을 강제한다. 128k 이상을 지원한다고 주장하는 13개 모델을 평가한 결과가 논문 Table 3 에 있다.

| 모델              | 주장 길이 | 실효 길이 | 기준점수 | 32K 에서 |
| ----------------- | --------- | --------- | -------- | -------- |
| GPT-4o            | 128K      | 8K        | 99.3     | 69.7     |
| Llama 3.3 70B     | 128K      | 2K        | 97.3     | 42.7     |
| Gemini 1.5 Pro    | 2M        | 2K        | 92.6     | 48.2     |
| Claude 3.5 Sonnet | 200K      | 4K        | 87.5     | 29.8     |
| Command R+        | 128K      | <1K       | 90.9     | 7.4      |

(실효 길이 = 기준점수의 85% 를 유지하는 최대 길이)

읽어야 할 지점은 두 가지다.

**하나.** 13개 중 11개가 **32K 에서 이미 기준점수의 절반 이하**로 떨어진다. 123k 는커녕 32k 도 못 간다. 논문은 "2K–8K 에서도 상당한 하락" 을 보고한다.

**둘.** 실효 길이가 주장 길이보다 한두 자릿수 짧다. Gemini 1.5 Pro 는 2M 을 주장하지만 이 과제에서의 실효 길이는 2K 다. 초판이 "Gemini 는 128k 이상에서 중간을 놓친다" 고 쓴 건 방향은 맞았지만 자릿수가 틀렸다.

즉 **"123k 전까지는 안전하다" 는 명제가 가장 위험한 부분이다.** 안전 구간을 실제보다 훨씬 넓게 잡게 만들기 때문이다.

한 가지 단서는 달아야 한다. NoLiMa 는 연상 추론 검색이라는 특정 과제의 결과이고, 코드 편집이나 요약 같은 다른 과제에 그대로 옮길 수는 없다. 요점은 "32k 가 새로운 임계점" 이 아니라 **임계점이 과제마다 다르므로 상수로 못 박으면 안 된다** 는 것이다.

# 3. 벤더도 같은 말을 한다

Anthropic 의 공식 문서는 이 현상에 이름을 붙여 명시하고 있다.

> "컨텍스트 창이 크다고 자동으로 더 나은 것은 아니다. 토큰 수가 늘어나면 정확도와 재현율이 떨어지며, 이를 **context rot** 라 부른다. 그래서 공간이 얼마나 남았는지만큼이나 무엇을 컨텍스트에 담을지 선별하는 일이 중요하다."
> — Anthropic, [Context windows](https://platform.claude.com/docs/en/build-with-claude/context-windows)

벤더가 자기 제품의 한계를 문서 본문에 적어둔 셈이다. 다만 **여기에도 "몇 토큰부터" 라는 숫자는 없다.** 있었다면 초판이 그걸 인용했을 것이다.

같은 문서에서 확인되는 사실관계도 초판과 다르다. Claude Opus 5·Opus 4.8·Opus 4.7·Opus 4.6·Sonnet 5·Sonnet 4.6 은 **1M 토큰** 창을 갖는다. 초판이 쓴 "Claude 3.5/5 Opus 는 200k" 는 존재하지 않는 모델명이며 수치도 틀렸다.

# 4. Claude Code 는 실제로 어디서 자르는가

여기서부터는 문헌이 아니라 **설치본을 직접 뜯어 확인한 결과**다. 대상은 Claude Code 2.1.212, macOS. 아래 명령으로 누구나 재현할 수 있다.

```sh
strings -a "$(readlink -f "$(which claude)")" | grep -o "autoCompactWindow[^,]\{0,120\}"
```

확인된 동작은 이렇다.

**설정 경로는 네 가지이고 우선순위가 있다.**

1. 환경변수 `CLAUDE_CODE_AUTO_COMPACT_WINDOW` — 최우선. 이게 설정돼 있으면 `/autocompact` 명령으로 바꿀 수 없다
2. `settings.json` 의 `autoCompactWindow` — 정수, 최소 100,000 / 최대 1,000,000. 범위 밖 값은 조용히 무시되고 auto 로 폴백한다
3. 서버가 내려주는 실험값
4. `auto` — 기본값. 모델별로 조정된 창을 고른다

**실제 임계값은 항상 `min(설정값, 모델 최대 컨텍스트)` 다.** 즉 이 설정은 창을 **줄일 수만 있고 늘릴 수 없다.** 200k 모델에 1,000,000 을 넣어도 200k 로 잘린다. 이 동작은 이슈 트래커에도 보고돼 있다([anthropics/claude-code#57964](https://github.com/anthropics/claude-code/issues/57964)).

여기서 초판의 마지막 오류가 드러난다. 초판은 "컨텍스트가 123k 에 도달하면 하네스가 즉시 `/clear` 를 내리는 **The 123k Wipe 를 공식 적용했다**" 고 썼다. 그러나 해당 시스템의 스크립트 디렉터리와 설정 파일 어디에도 123k 관련 코드는 없었다. 적용된 적이 없는 규칙을 적용했다고 쓴 것이다.

이 설정의 전체 동작 — 네 개의 설정 경로와 우선순위, 컴팩션이 실제로 걸리는 지점 계산, 곁다리 환경변수 — 은 별도의 글에 정리했다. → [Claude Code 의 autoCompactWindow 를 설치본에서 직접 확인했다](/2026/07/31/claude-code-autocompact-window/)

한 가지 덧붙일 실무 함정이 있다. 같은 계정의 세션이라도 컨텍스트 창이 200k 로 잡히기도 하고 1M 으로 잡히기도 한다. Opus 계열에서 1M 창을 쓰려면 사용량 크레딧이 활성화돼 있어야 하기 때문이다([Anthropic 지원 문서](https://support.claude.com/en/articles/8606394-how-large-is-the-context-window-on-paid-claude-plans)). 그래서 `autoCompactWindow` 를 전역에 고정하면 1M 세션의 창까지 함께 깎인다.

# 5. 그래서 무엇을 해야 하나

숫자 하나를 다른 숫자 하나로 바꾸는 건 같은 실수의 반복이다. 검증된 자료에서 나오는 실무 지침은 임계점이 아니라 **구조**에 관한 것이다.

**위치를 관리한다.** Lost in the Middle 이 보인 U 자 곡선은 지금도 유효하다. 결정적인 정보는 프롬프트의 앞이나 뒤에 둔다. 중간에 묻지 않는다.

**총량보다 밀도를 본다.** 문서를 20개에서 50개로 늘려도 1.5% 밖에 안 올랐다는 결과는, 검색기를 키우는 것보다 재순위화나 절단이 낫다는 뜻이다. 에이전트에서는 MCP 서버와 툴 정의가 그대로 컨텍스트를 먹는다는 점도 같은 이야기다.

**자기 과제로 직접 잰다.** 남의 임계점을 빌려오지 않는다. 실제 과제를 짧은 컨텍스트에서 한 번, 길게 채운 상태에서 한 번 돌려 정답률을 비교하면 자기 시스템의 실효 길이가 나온다. NoLiMa 가 한 일이 정확히 그것이고, 방법은 공개돼 있다.

**창을 줄이는 설정은 세션 단위로만 쓴다.** 앞서 본 대로 전역 고정은 손해가 크다. 필요하면 `CLAUDE_CODE_AUTO_COMPACT_WINDOW=150000 claude` 처럼 그 세션에만 건다.

# 정리

초판이 제시한 123k 라는 숫자는 근거가 없었다. 없는 임계점을 믿으면 그 아래는 안전하다고 착각하게 되는데, 실제 측정치는 훨씬 이른 구간에서 이미 성능이 흔들린다고 말한다.

컨텍스트 저하는 실재하는 현상이고, 잘 측정된 1차 연구가 있고, 벤더도 인정한다. 다만 그 어느 쪽도 "몇 토큰" 이라는 단일한 답을 주지 않는다. 답이 없다는 사실을 그대로 적는 것이, 있어 보이는 숫자를 지어내는 것보다 언제나 낫다.

이 글의 초판은 그 반대로 했다. 그래서 다시 썼다.

---

# References

**1차 출처 (동료심사 논문)**

- Liu, N. F., Lin, K., Hewitt, J., Paranjape, A., Bevilacqua, M., Petroni, F., Liang, P. (2024). [Lost in the Middle: How Language Models Use Long Contexts](https://aclanthology.org/2024.tacl-1.9/). _Transactions of the ACL_, 12:157–173. DOI: 10.1162/tacl_a_00638. (프리프린트: [arXiv:2307.03172](https://arxiv.org/abs/2307.03172)) — U 자 성능 곡선, 위치별 20% 이상 차이, closed-book 56.1% 대조, 문서 20→50 증가 시 ~1.5% 개선
- Modarressi, A., Deilamsalehy, H., Dernoncourt, F., Bui, T., Rossi, R. A., Yoon, S., Schütze, H. (2025). [NoLiMa: Long-Context Evaluation Beyond Literal Matching](https://proceedings.mlr.press/v267/modarressi25a.html). _ICML 2025_, PMLR 267:44554–44570. (프리프린트: [arXiv:2502.05167](https://arxiv.org/abs/2502.05167)) — 본문 표는 논문 Table 3 발췌. 13개 모델 중 11개가 32K 에서 기준점수 절반 이하, 실효 길이 정의(기준점수의 85%)

**1차 출처 (벤더 공식 문서)**

- [Context windows](https://platform.claude.com/docs/en/build-with-claude/context-windows) — Anthropic 플랫폼 문서. context rot 정의, 모델별 컨텍스트 창 크기, compaction·context editing
- [How large is the context window on paid Claude plans?](https://support.claude.com/en/articles/8606394-how-large-is-the-context-window-on-paid-claude-plans) — Anthropic 지원 문서. 플랜·모델별 창 크기, Claude Code 에서 Opus 1M 사용 시 크레딧 요건
- [Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) — Anthropic 엔지니어링 블로그. 위 문서가 context rot 대응 방법으로 연결하는 글

**1차 출처 (이슈 트래커)**

- [anthropics/claude-code#57964](https://github.com/anthropics/claude-code/issues/57964) — `CLAUDE_CODE_AUTO_COMPACT_WINDOW` 가 모델 컨텍스트 한도로 상한 처리된다는 사용자 보고. 벤더 확인이 아닌 사용자 보고이며, 본문의 실측 결과와 일치한다

**본인 실측 (재현 명령 포함)**

- Claude Code 2.1.212 (macOS) 설치본 문자열 분석. `autoCompactWindow` 의 우선순위·범위(100,000–1,000,000)·`min(설정값, 모델 최대)` 상한. 재현: 본문 4절의 `strings` 명령

_본문의 성능 저하 관련 주장은 위 동료심사 논문 두 편에 근거한다. 두 논문 모두 특정 과제(다문서 QA·키-값 검색·연상 추론 검색)의 측정 결과이며, 코드 편집이나 장문 요약 등 다른 과제에 그대로 일반화되지 않는다. 2026년 7월 31일 기준, "특정 토큰 수를 넘으면 성능이 떨어진다" 는 형태의 단일 임계점을 제시한 권위 있는 출처는 확인하지 못했다._
