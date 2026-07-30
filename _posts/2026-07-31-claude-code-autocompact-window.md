---
layout: post
title: "Claude Code 의 autoCompactWindow 를 설치본에서 직접 확인했다 — 설정 경로 4개와 우선순위, 그리고 늘릴 수 없는 이유"
date: 2026-07-31 05:00:00 +0900
categories: [ai, engineering]
tags:
  [ClaudeCode, AutoCompact, ContextWindow, CLI, Settings, ReverseEngineering]
---

# 왜 이걸 파게 됐나

긴 세션을 돌리다 보면 Claude Code 가 대화를 알아서 요약하고 이어간다. 자동 컴팩션(auto-compact)이다. 그런데 이걸 조절하려고 검색하면 서로 다른 숫자가 나온다. 어떤 글은 트리거가 83% 라 하고, 어떤 글은 버퍼가 33k 라 하고, 또 어떤 글은 45k 라 한다. 창을 키울 수 있다고 쓴 글도 있다.

셋 중 어느 쪽이 맞는지 확인하는 가장 확실한 방법은 **설치된 실행 파일을 직접 읽는 것**이다. 이 글은 그 기록이다.

대상은 **Claude Code 2.1.212 (macOS, Homebrew Cask)** 다. 버전이 다르면 결과가 달라질 수 있으니, 아래 명령을 자기 설치본에 그대로 돌려 확인하길 권한다.

```sh
BIN="$(readlink -f "$(which claude)")"
strings -a "$BIN" | grep -o "autoCompactWindow[^,]\{0,120\}" | head
```

# 1. 설정 경로는 네 가지이고, 우선순위가 있다

가장 먼저 확인된 건 이 값을 정하는 경로가 하나가 아니라는 점이다. 위에서부터 이긴다.

**1순위 — 환경변수**

```sh
CLAUDE_CODE_AUTO_COMPACT_WINDOW=500000 claude
```

이게 설정돼 있으면 다른 경로는 전부 무시된다. CLI 도 이 사실을 알려준다. `/autocompact` 로 값을 바꾸려 하면 이런 메시지가 나온다.

> `CLAUDE_CODE_AUTO_COMPACT_WINDOW is set and takes precedence. Unset it to change this setting.`

**2순위 — 설정 파일**

`~/.claude/settings.json` 에 넣는다.

```json
{
  "autoCompactWindow": 500000
}
```

정수여야 하고 **최소 100,000 / 최대 1,000,000** 이다. 범위를 벗어나면 오류가 나는 게 아니라 **조용히 무시되고 기본값으로 폴백**한다. 오타를 내고도 반영된 줄 알기 쉬운 지점이다.

**3순위 — 서버가 내려주는 값**

계정·모델에 따라 서버가 창 크기를 지정하는 경로가 있다. `/autocompact` 출력에서 `auto (N tokens)` 형태로 표시된다.

**4순위 — auto (기본값)**

아무것도 설정하지 않았을 때. 모델에 맞춰 자동으로 고른다. 설치본에서 확인된 기본값은 이렇다.

- 최대 컨텍스트가 1M 미만인 모델: **200,000**
- Sonnet 5: **967,000** (원격·로컬 에이전트 표면에서는 500,000)

CLI 자체가 `auto` 를 "대부분의 경우 강력히 권장" 한다고 안내한다.

# 2. `/autocompact` 명령 문법

인자 없이 실행하면 현재 값과 출처를 보여주고, 10만 단위로 고르는 선택기를 띄운다.

```
/autocompact                # 현재 상태 + 선택기
/autocompact auto           # 자동으로 되돌림
/autocompact 500k           # 500,000
/autocompact 200000         # 절대값
/autocompact 200            # 200k 축약형
/autocompact reset          # unset / default 도 동일 — auto 로 복귀
```

파싱에 실패하면 이렇게 답한다.

> `Expected 'auto' or 100k–1M tokens (e.g. 500k, 200000, or 200 as shorthand)`

여기서 설정한 값은 `~/.claude/settings.json` 에 저장된다. 즉 2순위 경로에 쓰는 것이고, 1순위 환경변수가 있으면 저장해봐야 적용되지 않는다.

# 3. 늘릴 수는 없다 — 항상 min 이 걸린다

이 글에서 가장 중요한 부분이다.

실제 적용되는 창은 **`min(설정값, 모델의 최대 컨텍스트)`** 다. 이 설정은 창을 **줄이는 방향으로만 작동한다.**

200k 모델에 1,000,000 을 넣으면 200k 가 된다. `/autocompact` 출력도 이 경우를 명시적으로 표시한다.

> `capped to 200k by model`

같은 동작이 이슈 트래커에도 보고돼 있다. 커스텀 엔드포인트로 더 큰 창을 쓰는 모델을 붙였는데 200k 에서 잘린다는 내용이다([anthropics/claude-code#57964](https://github.com/anthropics/claude-code/issues/57964)). 이 이슈는 벤더의 공식 확인이 아니라 사용자 보고지만, 설치본에서 확인한 동작과 일치한다.

참고로 그 이슈의 회피책으로 언급된 모델명 뒤 `[1m]` 접미사도 설치본에서 확인된다. 다만 이건 커스텀 엔드포인트 용도이고, 정규 모델에서는 필요 없다.

# 4. 실제 컴팩션이 걸리는 지점

창 크기가 곧 트리거 지점은 아니다. 요약 자체를 생성할 공간을 남겨야 하기 때문이다.

설치본에서 확인된 계산은 이렇다.

```
유효 창 = min(설정값, 모델 최대 컨텍스트) − min(모델의 최대 출력 토큰, 20,000)
```

즉 **버퍼는 최대 20,000 토큰**이다. 200k 모델이고 설정을 건드리지 않았다면 유효 창은 180,000 근처가 된다.

여기서 검색으로 나오는 "버퍼 33k" "버퍼 45k" 같은 숫자와 어긋난다. 그 글들이 틀렸다기보다, **버전에 따라 값이 달라져 온 항목**으로 보는 게 맞다. 그래서 남의 숫자를 믿지 말고 자기 설치본에서 확인하라는 게 이 글의 결론 중 하나다.

트리거 시점을 앞당기는 비율 값도 존재하지만, 설치본 코드에서 이 값은 **테스트용 오버라이드**로 취급된다. 상시 운영에 의존할 만한 인터페이스로 보기는 어렵다.

# 5. 곁다리 환경변수

- `DISABLE_AUTO_COMPACT=1` — 자동 컴팩션만 끈다. 수동 `/compact` 는 살아 있다
- `DISABLE_COMPACT=1` — 컴팩션 자체를 끈다
- `CLAUDE_CODE_MAX_CONTEXT_TOKENS` — `DISABLE_COMPACT` 와 함께 쓸 때만 의미가 있는 경로가 있다. 커스텀 엔드포인트용

`/config` 에도 자동 컴팩션 토글이 있다.

# 6. 실무 권고

**대부분의 경우 건드리지 않는 게 맞다.** 이유는 앞의 3절이다. 이 설정은 창을 줄이기만 하므로, 잘못 고정하면 손해만 본다.

특히 **전역 설정 파일에 박는 건 권하지 않는다.** 계정·모델·크레딧 설정에 따라 같은 계정의 세션이라도 창이 200k 로 잡히기도 하고 1M 으로 잡히기도 한다. Opus 계열에서 1M 창을 쓰려면 사용량 크레딧이 활성화돼 있어야 하기 때문이다([Anthropic 지원 문서](https://support.claude.com/en/articles/8606394-how-large-is-the-context-window-on-paid-claude-plans)). 여기에 전역으로 200k 를 박으면 1M 세션의 창까지 함께 깎인다.

실제로 필자의 환경에서 세션별로 기록된 창 크기를 뽑아보니 200,000 과 1,000,000 이 섞여 있었다. 하나로 고정하면 그중 절반이 손해를 본다.

**조여야 할 이유가 있다면 세션 단위로만 건다.**

```sh
CLAUDE_CODE_AUTO_COMPACT_WINDOW=150000 claude
```

그리고 값을 너무 낮게 잡지 않는 게 좋다. MCP 서버와 스킬을 여럿 물린 환경은 시스템 프롬프트와 툴 정의만으로 수만 토큰을 쓴다. 창을 120k 아래로 조이면 실제 대화에 쓸 공간이 얼마 안 남아 컴팩션이 계속 돈다. 컴팩션은 공짜가 아니다 — 요약하는 동안 토큰을 쓰고, 요약 과정에서 원문 세부가 사라진다.

# 정리

- 설정 경로는 4개, 환경변수가 최우선이다
- 범위는 100,000–1,000,000, 벗어나면 조용히 무시된다
- **항상 `min(설정값, 모델 최대)` — 늘릴 수 없다**
- 버퍼는 최대 20,000 토큰 (2.1.212 기준)
- 기본값 `auto` 를 그대로 두는 게 대체로 낫다
- 조일 거면 전역이 아니라 세션 단위로

그리고 이 글의 숫자도 결국 특정 버전의 관찰이다. 자기 설치본에서 1절의 명령 한 줄로 확인하는 데 10초면 된다. 그게 어떤 블로그 글보다 정확하다.

---

# References

**1차 출처 (벤더 공식 문서)**

- [Context windows](https://platform.claude.com/docs/en/build-with-claude/context-windows) — Anthropic 플랫폼 문서. 모델별 컨텍스트 창 크기, context rot, 서버사이드 compaction
- [How large is the context window on paid Claude plans?](https://support.claude.com/en/articles/8606394-how-large-is-the-context-window-on-paid-claude-plans) — Anthropic 지원 문서. Claude Code 에서 Opus 계열 1M 창 사용 시 사용량 크레딧 요건

**1차 출처 (이슈 트래커)**

- [anthropics/claude-code#57964](https://github.com/anthropics/claude-code/issues/57964) — `CLAUDE_CODE_AUTO_COMPACT_WINDOW` 가 모델 컨텍스트 한도로 상한 처리된다는 사용자 보고. 벤더 확인이 아닌 사용자 보고

**본인 실측 (재현 명령 포함)**

- Claude Code 2.1.212 (macOS, Homebrew Cask) 설치본 문자열 분석. 설정 경로 4개와 우선순위, 값 범위(100,000–1,000,000), `min(설정값, 모델 최대)` 상한, 버퍼 `min(모델 최대 출력, 20,000)`, 모델 기본값(1M 미만 모델 200,000 / Sonnet 5 967,000), `/autocompact` 명령 문법. 재현: 본문 1절의 `strings` 명령
- 세션별 창 크기 혼재(200,000 / 1,000,000) 관찰 — 필자 로컬 환경의 세션 상태 파일 기록

_본문의 CLI 내부 동작에 관한 서술은 특정 버전(2.1.212)의 설치본을 관찰한 결과이며, Anthropic 이 공식 문서로 보증한 사양이 아니다. 버전 업데이트로 변경될 수 있다. 검색으로 확인되는 "버퍼 33k/45k", "트리거 83%" 등 다른 수치와 어긋나는 부분이 있으나, 2026년 7월 31일 기준 어느 쪽이 어느 버전에 해당하는지 확정할 수 있는 공식 자료는 확인하지 못했다._
