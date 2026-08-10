---
layout: post
title: "떠도는 Claude Code '울트라코드' 3단계 팁, 한 줄이 틀렸다"
date: 2026-08-11 05:10:00 +0900
categories: [AI, Claude Code]
tags: [claude-code, ultracode, workflow, subagent, orchestration, fact-check]
---

이런 팁이 돌아다닌다.

![Claude Code ultracode 3단계 팁](/assets/images/claude-code-ultracode-tip.jpg)

요약하면 ① `/model` 을 opus 4.8 로, ② `/effort` 를 ultracode 로, ③ 프롬프트에 `workflow` 입력. 그러면 Claude 가 오케스트레이션을 설계하고 서브 에이전트를 대량으로 띄워 검증·리포트까지 한다는 것이다.

**결론부터: 큰 그림은 맞다. 그런데 세 줄 중 ③은 단어가 틀렸고, ①은 필요 이상으로 좁고, ②를 했으면 ③은 아예 불필요하다.** 그리고 이 팁이 한 줄도 언급하지 않는, 실제로는 제일 중요한 스위치가 하나 있다.

---

## 어떻게 확인했나 (출처 등급 먼저)

내 로컬에 설치된 Claude Code **2.1.212** 정품 바이너리에서 사용자 대면 메시지 문자열과 설정 스키마 설명을 직접 뽑아 대조했다.

```bash
claude --version
# 2.1.212 (Claude Code)

strings /usr/local/Caskroom/claude-code/2.1.212/claude | grep -i ultracode
```

출처 등급을 섞지 않기 위해 미리 밝힌다.

- 아래 인용한 **큰따옴표 문자열은 전부 그 빌드에 실제로 들어 있는 원문**이다. 내가 요약하거나 추측한 게 아니다.
- 다만 이건 **특정 버전 스냅샷**이지 Anthropic 공식 문서가 아니다. 문서화되지 않은 내부 동작은 예고 없이 바뀔 수 있다.
- 설정 키 이름과 기본값은 사용자가 `/config` 로 직접 확인할 수 있는 것들이라, 검증 가능성을 위해 그대로 적었다.

---

## 먼저, ultracode 가 대체 뭔가

`/effort ultracode` 를 실행하면 나오는 메시지가 정의 그 자체다.

> "Set effort level to ultracode (this session only): **xhigh + dynamic workflow orchestration**"

그리고 설정 스키마의 `ultracode` 키 설명은 이렇다.

> "Enable ultracode for the session: xhigh effort plus standing dynamic-workflow orchestration. **Session-scoped**"

즉 ultracode 는 두 개를 한 번에 켜는 스위치다.

1. **추론 강도(effort)를 xhigh 로** — 실제로 내부에서 `ultracode → xhigh` 로 매핑된다.
2. **워크플로 오케스트레이션을 상시 켬** — 매 턴 "이 작업은 Workflow 툴로 처리하라"는 지시가 서 있는 상태가 된다.

세션이 켜져 있는 동안 모델에게 다시 주입되는 문구도 확인된다.

> "Use the Workflow tool on every substantive task; **token cost is not a constraint.** … Solo only on conversational/trivial turns."

이 한 줄이 ultracode 의 성격을 다 설명한다. **"토큰 비용은 제약이 아니다"** 를 모델에게 명시적으로 알려주는 모드다. 팁 이미지가 "이것만으로"라고 가볍게 적은 것과 온도차가 크다.

---

## 3단계 정정

### ① "opus 4.8 로 설정" → 틀리진 않았지만 지나치게 좁다

모델이 xhigh 를 지원해야 하는 건 맞다. 지원하지 않으면 이 메시지로 거절된다.

> "Ultracode runs at xhigh effort, which \<모델\> doesn't support — switch to an **xhigh-capable model**"

그런데 그 xhigh 지원 모델 목록이 빌드 안에 문자열로 박혀 있다.

> `"Fable 5, Opus 4.7+, Sonnet 5"`

**Opus 4.8 만 되는 게 아니다.** Opus 4.7 이상, Sonnet 5, Fable 5 도 된다. Sonnet 5 로도 ultracode 가 켜진다는 건 비용 측면에서 꽤 중요한 정보인데, 팁은 이걸 빼먹었다.

### ② "`/effort` 를 ultracode 로" → 맞다. 단 전제조건 두 개

`/effort` 의 사용법 문자열은 이렇게 조립된다.

```
Usage: /effort <low|medium|high|xhigh|max|ultracode|auto>
```

여기서 `ultracode` 항목은 **모델이 xhigh 를 지원할 때만 목록에 나타난다.** 그래서 안 보인다고 버그가 아니라, 모델부터 바꾸라는 신호다. 실패 경로는 둘이다.

- 모델이 xhigh 미지원 → 위의 "switch to an xhigh-capable model"
- 워크플로 기능이 꺼져 있음 → **"Ultracode needs dynamic workflows enabled (see `/config`)."**

두 번째가 함정이다. 모델을 아무리 올려도 `/config` 에서 dynamic workflows 가 꺼져 있으면 ultracode 는 안 켜진다.

그리고 **세션 한정**이다. 영구 저장되는 effort 설정 값의 enum 은 `["low","medium","high","xhigh"]` 로 정의돼 있어서 ultracode 는 애초에 "기본값으로 저장" 대상이 아니다. 켤 때마다 켜야 한다. (`--settings` 로 세션에 주입하는 경로는 따로 있다.)

### ③ "프롬프트에 `workflow` 를 입력" → **단어가 틀렸다**

키워드 트리거를 켜고 끄는 설정의 설명 원문은 이렇다.

> `workflowKeywordTriggerEnabled`: 'Enable the **"ultracode" keyword trigger**: including the keyword in a prompt opts that turn into the Workflow tool. Set to false to disable the trigger. Default: true.'

키워드는 `workflow` 가 아니라 **`ultracode`** 다. 관련 UI 라벨도 "Ultracode keyword trigger", 무시했을 때 뜨는 토스트도 "Ultracode keyword ignored for this prompt" 이다.

물론 "이건 워크플로로 돌려줘"처럼 **말로 요청하면 그것도 옵트인으로 인정된다.** 그러니 팁의 ③이 완전히 헛발질은 아니다. 하지만 "`workflow` 라는 단어를 넣으면 켜지는 마법의 토큰"이라는 인상은 사실이 아니다. 그 마법의 토큰은 `ultracode` 다.

**더 중요한 건, ②를 했으면 ③은 필요 없다는 점이다.** `/effort ultracode` 로 세션을 켜 두면 옵트인이 상시 유지되므로 매 프롬프트에 뭔가를 덧붙일 이유가 없다. 두 줄은 같은 문 하나를 여는 서로 다른 열쇠이지, 순서대로 밟아야 하는 계단이 아니다.

- **세션 전체를 그 모드로**: `/effort ultracode` (②)
- **이번 턴만**: 프롬프트에 `ultracode` (③, 단어 교정본)

참고로 키워드가 잡혔는데 이번엔 원치 않을 때는 `alt+w` 로 그 프롬프트에 한해 무시할 수 있다.

---

## 팁이 말하지 않는 것: 안전장치가 같이 꺼진다

이게 이 글에서 제일 중요한 부분이다.

Claude Code 에는 동적 워크플로가 너무 커질 때 경고하는 장치가 있고, `/config` 의 **"Dynamic workflow size"** 항목으로 조절한다. 선택지와 내부 임계값은 이렇다.

| 설정           | 에이전트 기준치        |
| :------------- | :--------------------- |
| `small`        | 5                      |
| `medium`       | 15                     |
| `large`        | 50                     |
| `unrestricted` | 제한 없음 (**기본값**) |

그런데 경고를 낼지 판단하는 함수는 인자로 `ultracodeActive` 를 받고, **그게 참이면 아무것도 하지 않고 즉시 반환한다.** 즉 —

> **ultracode 를 켜면 워크플로 규모 경고가 통째로 꺼진다.**

설계상 일관적이긴 하다. "토큰 비용은 제약이 아니다"라고 모델에게 말해 놓고 "에이전트가 너무 많습니다"라고 경고하면 앞뒤가 안 맞으니까. 하지만 **사용자 입장에서는 가속 페달과 함께 계기판 경고등이 같이 꺼지는 것**이고, 기본값이 `unrestricted` 라는 점까지 겹치면 실수하기 좋은 조합이다.

실제로 이 CLI 는 높은 effort 자체에 대해서도 이렇게 경고한다.

> "May use excessive tokens resulting in long response times or overthinking. **Use sparingly for the hardest tasks.**"

"과잉 사고(overthinking)"를 공급자가 직접 실패 모드로 명시하고 있다. 3단계 팁의 낙관적인 톤과는 확실히 결이 다르다.

---

## 그래서 언제 켜나

팁이 나열한 능력 — 오케스트레이션 설계, 실행 스크립트 생성, 서브 에이전트 대량 기동, 태스크 분담, 결과 검증, 리포트 — 은 **실재한다.** 과장이 아니다. 문제는 그게 공짜가 아니라는 것뿐이다.

내 기준은 이렇다.

**켤 만한 것** — 넓게 훑어야 답이 나오는 일. 리포 전반 감사, 대규모 마이그레이션 대상 발굴, 여러 관점으로 교차 검증해야 하는 리뷰, 독립적인 설계안 여러 개를 뽑아 비교하는 일. 공통점은 **한 컨텍스트에 안 들어가거나, 한 관점으로는 놓치는 일**이다.

**켜면 안 되는 것** — 파일 하나 고치기, 값 하나 확인하기, 대화. 이런 데서 ultracode 는 답을 낫게 만들지 못하고 지연과 비용만 늘린다. 공급자 스스로 "conversational/trivial turns 는 혼자 하라"고 지시문에 박아 둔 이유다.

그리고 켤 거라면 **`unrestricted` 기본값을 그대로 두지 말고 `/config` 에서 크기 가이드라인을 먼저 정해 두길 권한다.** ultracode 상태에서는 경고가 안 뜨지만, ultracode 를 끄고 워크플로만 쓰는 평상시에는 이 값이 실제로 브레이크 역할을 한다.

---

## 정리

| 팁의 주장                | 판정        | 실제                                                              |
| :----------------------- | :---------- | :---------------------------------------------------------------- |
| ① `/model` 을 opus 4.8   | ▲ 좁음      | xhigh 지원 모델이면 됨: "Fable 5, Opus 4.7+, Sonnet 5"            |
| ② `/effort` 를 ultracode | ○ 맞음      | 단 dynamic workflows 활성 필요, 세션 한정                         |
| ③ 프롬프트에 `workflow`  | ✕ 단어 오류 | 키워드는 `ultracode`. 게다가 ②를 했으면 불필요                    |
| "이것만으로" 다 된다     | △           | 기능은 실재. 다만 규모 경고가 함께 꺼지고 기본값은 `unrestricted` |

한 줄로 줄이면 — **`/effort ultracode` 한 줄이면 되고, 그게 켜는 건 성능이 아니라 "비용 제약 해제"다.**

---

## References

**1차 (설치본 검증)**

- Claude Code CLI **2.1.212** — 사용자 대면 메시지 문자열 및 설정 스키마 설명 원문. 본문의 모든 큰따옴표 인용은 이 빌드에서 직접 추출.
- 확인 가능한 설정 항목(사용자가 `/config` 에서 직접 열람 가능): `Dynamic workflow size`(`small`/`medium`/`large`/`unrestricted`), `Ultracode keyword trigger`(`workflowKeywordTriggerEnabled`, 기본 `true`), dynamic workflows 활성 여부
- 확인 가능한 명령: `/effort <low|medium|high|xhigh|max|ultracode|auto>`, `/model`, `alt+w`(키워드 이번 턴 무시)

**공식 문서**

- Claude Code 문서: <https://code.claude.com/docs/en/overview>

**한계 명시**

- 위 문자열은 **2.1.212 라는 특정 버전의 스냅샷**이다. 임계값(5/15/50), 모델 목록, 키워드 동작은 이후 버전에서 바뀔 수 있으므로, 중요한 판단 전에는 본인 설치본에서 `/config` 와 `/effort` 로 직접 확인하는 것을 권한다.
- ultracode 사용 시의 **품질 향상 폭에 대한 중립 제3자 벤치마크는 확인하지 못했다.** 본문은 "무엇이 켜지는가"를 다룬 것이지 "얼마나 좋아지는가"를 주장하지 않는다.
- "그래서 언제 켜나" 절의 기준은 내 사용 경험에 근거한 판단이며, 공급자 권고가 아니다.
