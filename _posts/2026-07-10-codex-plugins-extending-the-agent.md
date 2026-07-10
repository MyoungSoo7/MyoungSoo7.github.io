---
layout: post
title: "Codex 플러그인 — 에이전트 에게 *능력 을 끼우는* 법 (핸즈온 + 조합)"
date: 2026-07-10 12:35:00 +0900
categories: [ai, agent, codex]
tags: [codex, openai, plugin, ai-agent, skill, tool-use, mcp, composition, ax]
---

OpenAI 의 *AX 인재전쟁* 같은 자리 에서 반복 되는 화두 는 하나다 — **"AI 로 우리 회사 의 진짜 문제 를 풀 수 있는가."** 그 답 의 실체 중 하나 가 **Codex 플러그인** 이다. 범용 코딩 에이전트(Codex) 에 *우리 도메인 의 능력* 을 끼워 넣는 방법. 이 글 은 Codex 플러그인 이 무엇 이고, 어떻게 만들고 *조합* 하는지 를 핸즈온 으로 정리 한다.

![Codex 플러그인 개발 가이드 — 폴더 생성 → plugin.json → 스킬 → 등록 → 사용](/assets/images/codex/codex-plugin-handson.jpg)

---

## 0. 플러그인 이란 — 에이전트 의 *확장 슬롯*

Codex 자체 는 *범용* 이다. 코드 를 읽고 쓴다. 하지만 "한국은행 경제지표 를 조회해" 같은 *도메인 능력* 은 기본 으로 없다. **플러그인 은 그 능력 을 끼우는 확장 슬롯** 이다.

구조 를 보면 익숙 하다 — Claude Code 의 *스킬(SKILL.md)*, MCP 의 *도구(tool)* 와 같은 계열 이다. **에이전트 는 얇게, 능력 은 플러그인 으로.** 표준 인터페이스 에 도메인 을 꽂는다는 발상 은 [PSA(이식 가능한 추상화)]({% post_url 2026-07-08-jpa-through-the-lens-of-psa %}) 나 [헥사고날 어댑터]({% post_url 2026-07-07-object-oriented-design-from-a-diagram %}) 와 정확히 같다.

---

## 1. 최소 플러그인 — 4 개 로 끝난다

핸즈온 그림 이 보여주듯, 날씨 플러그인 하나 는 *네 조각* 이면 된다:

### ① 폴더
```bash
mkdir my-weather-plugin && cd my-weather-plugin
```
플러그인 은 *하나 의 폴더* 로 구성 된다. 그 안 에 `plugin.json` 과 스킬 파일.

### ② `plugin.json` — 플러그인 의 *정의서*
```json
{
  "name": "my-weather-plugin",
  "version": "0.1.0",
  "description": "현재 날씨를 제공하는 플러그인",
  "skills": ["weather/get_current_weather"],
  "permissions": [
    { "type": "network", "reason": "날씨 API 호출을 위해 외부 접근 필요" }
  ]
}
```
핵심 은 **`permissions`** 다 — *무엇 을 할 수 있는지* 를 선언 한다(여기 선 네트워크). 에이전트 확장 에서 *권한 을 명시* 하게 만든 건 좋은 설계다. 스킬 이 뭘 만질 수 있는지 가 *코드 밖 에* 드러난다.

### ③ 스킬(skill) — 실제 능력
```python
def get_current_weather(city: str) -> dict:
    api_key = os.getenv("WEATHER_API_KEY")
    if not api_key:
        raise ValueError("WEATHER_API_KEY 가 필요합니다")
    # weatherapi.com 호출 → 필요한 필드만 dict 로 반환
    ...
    return { "city": ..., "temp_c": ..., "condition": ... }
```
스킬 은 *함수 하나* 다. 입력(city) → 출력(dict). 비밀 은 환경변수(`WEATHER_API_KEY`) 로 — 코드 에 키 를 박지 않는다.

### ④ 등록 + 사용
```bash
codex plugin add ./my-weather-plugin
```
등록 하면, 이제 *자연어* 로 부른다 — "서울 현재 날씨 알려줘" → Codex 가 스스로 `get_current_weather("서울")` 을 호출 하고 결과 를 조합 해 답 한다. **사용자 는 함수 이름 을 몰라도 된다.** 자연어 → 도구 선택 → 실행 → 종합 이 에이전트 의 일이다.

> 이게 도구 사용(tool-use) 에이전트 의 핵심 루프 다 — [멀티 에이전트 글]({% post_url 2026-07-09-multi-agent-systems-in-practice %}) 의 그 ReAct.

---

## 2. 진짜 힘 — *플러그인 조합(composition)*

플러그인 하나 는 시작 일 뿐이다. **여러 플러그인 을 조합** 하면 실무 문제 를 푼다. 그림 의 예제 가 인상적 인데, *내가 오늘 배포한 서비스 들 과 정확히 겹친다*:

![Codex 플러그인 조합 — BizCheck + DartFS + KosisIndustry → AnalyzeComparison](/assets/images/codex/codex-plugin-composition.jpg)

문제: *"A사 의 사업 상태 를 확인 하고, 최신 재무제표 와 업종 평균 매출 을 비교해줘."* 이걸 플러그인 조합 으로:

```
BizCheck(사업자 진위)  → DartFS(재무제표)  → KosisIndustry(업종 통계)  → AnalyzeComparison(비교)
```

`plugin.json` 의 `skills` 에 여러 스킬 yaml 을 나열 하고, `analyze_comparison` 이 앞 결과 들 을 받아 종합 한다. 호출 전략 도 세 가지 — **순차**(이전 결과 가 다음 입력), **병렬**(독립 데이터 동시 조회), **조건부**(이전 결과 에 따라 분기).

> 재밌는 건 이 예제 의 DartFS(전자공시) · KosisIndustry(통계청) 가, [내가 오늘 settlement 에 배포한 economics(한국은행 ECOS) · financial(DART) · company(KOSIS/네이버)]({% post_url 2026-07-09-a-day-of-k8s-java-ops-senior-retrospective %}) 서비스 와 *같은 도메인* 이라는 것. MSA 로 짠 걸 플러그인 으로 감싸면 그대로 Codex 능력 이 된다.

**조합 = 오케스트레이션** 이다. 좁고 깊은 스킬 을 *순서·병렬·조건* 으로 엮는 것 — [하네스 엔지니어링]({% post_url 2026-07-10-harness-engineering-weekly-app-cycle %}) 의 그 파이프라인, 그리고 [설계 세 축]({% post_url 2026-07-07-backend-design-three-axes %}) 의 *결합도↔일관성* 판단 이 여기서도 나온다(돈·정합성 은 순차, 독립 조회 는 병렬).

---

## 3. 관측 은 여기서도 — stop-hook 로깅

에이전트 를 실무 에 쓰려면 *무슨 대화 를 했는지* 남겨야 한다. 그림 의 `save_log.py` 는 **stop-hook** — Codex(또는 Claude Code) 가 턴 을 끝낼 때 자동 실행 되어, 대화 를 `logs/<tool>/<session_id>.jsonl` 로 저장 한다.

- 표준 입력(JSON) 으로 세션 정보 를 받아
- `user_message`/`agent_message` 만 남기고 `tool_use`/`thinking`/`system` 은 *제거*(로그 용량·민감정보 축소)
- **항상 exit 0** — 로깅 실패 가 본 작업 을 막지 않게

이게 하네스 의 *관측* 기둥 이다. 그리고 "훅 으로 마크다운 밖 에서 강제" 한다는 점 에서, [superpowers 의 hooks/]({% post_url 2026-07-10-superpowers-6-pillars-of-skill-md %}) 와 같은 발상 — *문서 가 아니라 시스템 레벨 에서* 잠근다.

---

## 4. 좋은 플러그인 의 조건 (그림 의 Best Practices)

가이드 가 꼽는 원칙 은, 이 블로그 가 반복 해온 것 과 같다:

1. **명확한 입출력 스키마** — 각 스킬 의 파라미터·반환값 을 명확히 (에이전트 가 조합 하려면 계약 이 분명 해야)
2. **에러 처리 필수** — 각 단계 에서 실패 시 적절한 메시지. 삼키지 마라
3. **개성 활용(캐싱)** — 자주 조회 되는 데이터 는 캐시 로 속도 향상
4. **병렬 활용** — 독립 데이터 는 동시 조회
5. **로깅** — 각 플러그인 호출 결과 를 기록
6. **권한 명시** — permissions 로 *무엇 을 만지는지* 선언

`명확한 계약 · 실패 처리 · 관측 · 최소 권한` — 백엔드 에서 API 를 설계 할 때 와 토씨 하나 안 다르다.

---

## 맺으며 — AX 시대 의 실체

"AX 인재" 라는 말 이 추상 처럼 들리지만, 실체 는 이거 다 — **범용 에이전트 에 *우리 도메인 의 능력 을 플러그인 으로 끼우고, 조합 해서, 관측 하며* 실무 문제 를 푸는 사람.** Codex 플러그인 이든, Claude 스킬 이든, MCP 든 — 이름 은 달라도 구조 는 하나다: *얇은 에이전트 + 도메인 플러그인 + 조합 + 관측.*

그리고 그 플러그인 을 잘 만드는 능력 은, 결국 *백엔드 를 잘 짜는 능력* 과 같다 — 명확한 인터페이스, 실패 처리, 최소 권한, 관측 가능성. [문제 를 정의 하는 능력]({% post_url 2026-07-05-problem-definition-in-ax-era-backend %}) 이 있으면, 그걸 플러그인 으로 *조립* 하는 건 그 다음 이다.

*에이전트 는 얇게, 능력 은 플러그인 으로, 조합 으로 문제 를 푼다 — AX 는 그 조립 능력 의 다른 이름 이다.*

---

_참고: [Codex Plugins](https://developers.openai.com/codex/plugins) · [Plugin 만들기](https://developers.openai.com/codex/plugins/build) · [Skill 작성](https://developers.openai.com/codex/skills)_
_관련: [superpowers 6기둥]({% post_url 2026-07-10-superpowers-6-pillars-of-skill-md %}) · [하네스 엔지니어링]({% post_url 2026-07-10-harness-engineering-weekly-app-cycle %}) · [멀티 에이전트]({% post_url 2026-07-09-multi-agent-systems-in-practice %})_
