---
layout: post
title: "*절반 가격의 동급 지능* — Claude *Opus 5* vs *Fable 5*, 벤치마크 너머의 선택 기준 (2026년 7월 30일 기준)"
date: 2026-07-30 02:20:00 +0900
categories: [ai, llm, engineering]
tags: [Claude, Anthropic, ClaudeOpus5, ClaudeFable5, LLM, Benchmark, ModelSelection, AgenticCoding, ArtificialAnalysis, ClaudeCode]
---

# 6주 만에 뒤집힌 구도

2026년 6월 9일, Anthropic 은 `claude-fable-5` 를 내놓으면서 "5세대 지능" 이라고 불렀다. Mythos 급 모델을 일반 공개한 첫 사례였고, 가격은 입력 100만 토큰당 $10 · 출력 $50 — Opus 계열의 정확히 두 배였다.

그리고 7월 24일, `claude-opus-5` 가 나왔다. Anthropic 자신의 발표문 첫 문장이 이렇다.

> "Fable 5 의 프런티어 지능에 **근접**하면서 가격은 **절반**."

6주 만에 상위 티어의 존재 이유를 묻게 만드는 문장이다. 실제로 Anthropic 공식 문서의 모델 선택 가이드는 지금 이렇게 시작한다 — **"어떤 모델을 쓸지 모르겠다면 Claude Opus 5 로 시작하라. 가용한 최고 성능이 필요한 워크로드에는 Claude Fable 5 를 쓰라."** 벤더 스스로 상위 모델을 기본값에서 내린 것이다.

이 글은 그 "가용한 최고 성능이 필요한 워크로드" 가 구체적으로 무엇인지를 따진다. 벤치마크 표를 나열하는 대신, **어떤 상황에서 어느 쪽이 나은가**에 집중한다. 그리고 벤치마크에 아예 나오지 않는 네 가지 차이 — 지식 컷오프, 레이턴시, 세이프가드 리라우팅, 데이터 보존 의무 — 가 실무에서는 점수 차보다 크게 작용한다는 걸 보인다.

---

# 스펙 대조 — 공식 문서 기준

Anthropic 플랫폼 문서의 모델 비교표에서 두 모델만 발췌했다. 1차 출처다.

| | **Claude Fable 5** | **Claude Opus 5** |
|---|---|---|
| API ID | `claude-fable-5` | `claude-opus-5` |
| 포지셔닝 | 장기 실행 에이전트를 위한 차세대 지능 | 복잡한 에이전틱 코딩과 엔터프라이즈 작업 |
| 가격 (입력/출력, 100만 토큰) | **$10 / $50** | **$5 / $25** |
| 컨텍스트 윈도우 | 1M | 1M |
| 최대 출력 | 128k | 128k |
| Adaptive thinking | 예 (**항상 켜짐**) | 예 |
| Extended thinking (`budget_tokens`) | 아니오 | 아니오 |
| 상대적 레이턴시 | **Slower** | Moderate |
| 신뢰 가능 지식 컷오프 | **2026년 1월** | **2026년 5월** |
| 학습 데이터 컷오프 | 2026년 1월 | 2026년 5월 |

컨텍스트 윈도우와 최대 출력은 동일하다. 즉 "Fable 이 더 긴 작업을 할 수 있다" 는 통념은 **스펙상 근거가 없다.** 차이는 같은 창 안에서 어떻게 행동하느냐에 있다.

눈여겨볼 두 행이 있다. **지식 컷오프가 4개월 차이**나고, **레이턴시 등급이 다르다.** 뒤에서 다시 다룬다.

---

# 벤치마크 — 무엇이 실제로 갈리는가

## Anthropic 자체 측정 (벤더 주장)

발표문에서 검증 가능한 형태로 명시된 것만 옮긴다. 모두 **벤더가 자사 모델을 비교한 수치**이므로 그렇게 읽어야 한다.

- **Frontier-Bench v0.1** (에이전틱 코딩): Opus 5 가 모든 모델을 앞서며, Opus 4.8 성능의 두 배 이상을 **더 낮은 태스크당 비용**으로 달성
- **CursorBench 3.2**: max effort 에서 Fable 5 최고점의 **0.5% 이내**를, **절반 비용**으로
- **OSWorld 2.0** (컴퓨터 사용): Fable 5 의 최고 성적을 **1/3 남짓 비용**으로 추월
- **ARC-AGI 3** (신규 문제 해결): 차순위 모델의 **3배** 점수
- **Zapier AutomationBench** (업무 자동화 완주율): 동일 비용 기준 차순위의 약 **1.5배**. 최저 effort 설정에서도 다른 어떤 모델보다 많은 태스크를 통과
- 단, **사이버보안 과제에서는 여전히 Mythos 5 에 뒤진다**고 명시

## Artificial Analysis 측정 (제3자, 단 협력 관계 공시)

| 지표 | Opus 5 (max) | Fable 5 (max) |
|---|---|---|
| Intelligence Index | **61** | 60 (사실상 동률) |
| GDPval-AA v2 (Elo) | **1861** | 1747 (+114) |
| AA-Briefcase (Elo) | **1720** | 1574 (+146) |
| Humanity's Last Exam | 53% | 동급 |
| Terminal-Bench v2.1 | 89% (선두권) | — |
| 태스크당 평균 비용 | **$2.03** | $2.75 (26% ↓) |

Artificial Analysis 는 **"Anthropic 의 출시 전 Opus 5 평가를 지원했다"** 고 스스로 밝혔다. 완전히 독립적인 측정으로 취급하면 안 되고, 이 글에서도 그 전제로 인용한다.

## Fable 5 가 여전히 앞서는 지점

같은 Artificial Analysis 보고에서, Fable 5 의 우위가 남은 항목이 명확히 지목된다.

> **AA-Omniscience (사실 지식)** — Opus 5 는 체급 차이대로 Fable 5 보다 사실 지식이 낮다. Opus 4.8 대비 정확도는 +7%p 올랐지만, **불확실할 때 더 자주 답하면서 환각률이 +14%p 상승해 50% 에 도달**했다.

이건 순위표 한 줄이 아니라 **아키텍처 선택의 결과**다. 사용자 대면 서비스, 법률·의료·금융처럼 틀린 답의 비용이 큰 도메인에서는 Frontier-Bench 9.6 점 차이보다 이 한 줄이 결정적일 수 있다.

또한 Anthropic 이 6월 Fable 5 출시 당시 내세웠던 파트너 평가들(Cognition, Cursor, GitHub, 법률 리드라인 블라인드 리뷰 등)은 **Opus 5 기준으로 재실행되지 않았다.** 6월의 주장이 반박된 게 아니라 **검증되지 않은 채 남아 있는** 상태다. 본인 워크로드가 그 평가들과 닮았다면 순위표를 믿지 말고 직접 돌려봐야 한다.

---

# 벤치마크에 안 나오는 네 가지 차이

실무 선택은 대개 여기서 갈린다.

## 1. 지식 컷오프 4개월

Fable 5 는 2026년 1월, Opus 5 는 2026년 5월이다. 빠르게 움직이는 생태계 — 프레임워크 메이저 버전, 쿠버네티스 릴리스, 클라우드 API 변경 — 를 다루는 작업이라면 **Opus 5 가 알고 있는 것을 Fable 5 는 모른다.** 검색 도구로 메울 수 있지만, 도구 없이 던지는 질문에서는 상위 티어가 오답을 낸다.

## 2. 레이턴시

공식 표에서 Fable 5 는 `Slower`, Opus 5 는 `Moderate` 다. 벤더 자신의 분류다. 두 모델 다 대화형 챗 응답 속도를 노린 물건이 아니라 **배치·백그라운드 성격**에 가깝지만, 둘 중에서는 Fable 이 느린 쪽이다. 사람이 앞에서 기다리는 UX 라면 이 등급 차이가 점수 차보다 먼저 체감된다.

## 3. 세이프가드 리라우팅

Fable 5 는 사이버보안·생물학 관련 질의에 강한 세이프가드를 걸어두고, **플래그되면 자동으로 더 낮은 성능의 모델로 라우팅**한다. Anthropic 은 이 경우 Fable 가격으로 과금하지 않는다고 명시한다.

문제는 **오탐**이다. 보안 코드 감사, 취약점 분석, 생명과학 데이터 처리처럼 정당한 업무가 걸리면, 비싼 상위 티어를 고르고도 실제로는 하위 모델의 답을 받게 된다. 이런 도메인이라면 상위 티어 선택 자체가 역효과다.

## 4. 데이터 보존 30일 의무

Fable 5 사용은 **안전 모니터링을 위한 30일 데이터 보존을 요구한다.** 제로 데이터 보존(ZDR) 계약 하에 운영하는 조직은 Fable 5 를 쓸 수 없고, API 요청이 `400 invalid_request_error` 로 거부된다. 요청 본문에 문제가 없는데 400 이 계속 뜬다면 조직의 보존 설정부터 확인해야 한다.

규제 환경·ZDR 조직에서는 **이 한 줄이 벤치마크 차트를 열기도 전에 비교를 끝낸다.**

참고로 미국 내 인퍼런스가 필요한 워크로드용으로 Fable 5 는 1.1배 가격의 US-only 옵션을 제공한다.

---

# 구독 관점 — 2026년 7월 20일 변경

API 가 아니라 Claude 구독으로 쓰는 경우, 7월 20일부로 플랜에 따라 구조가 갈렸다.

| 플랜 | Fable 5 선택 | 플랜 한도 포함 | 초과 시 |
|---|---|---|---|
| **Max**, Team Premium, 레거시 Enterprise Premium 좌석 | 가능 | **포함** — 주간 한도의 최대 50% | usage credits 또는 다른 모델로 전환 |
| **Pro**, Team Standard | 가능 | **미포함** | **첫 요청부터** usage credits (= API 요율) |
| Usage-based Enterprise / API | 가능 | 해당 없음 | 표준 API 요율 |

여기서 중요한 건 **모델 접근이 막힌 게 아니라 사용료 부담 주체가 바뀌었다**는 점이다. Pro 에서도 Fable 5 는 선택 가능하지만 구독료와 별개로 종량 크레딧이 빠진다.

그리고 Opus 5 발표문이 이 구도에 못을 박았다 — **"Claude Max 의 새 기본 모델이자 Pro 에서 가장 강력한 모델."**

즉 Max 사용자에게 실질적 결론은 이렇다. Fable 5 는 주간 풀 안에서 최대 절반까지만 쓸 수 있고 소모 속도도 빠른 반면, **Opus 5 는 상한 없이 플랜 안에서 쓰는 기본 모델이다.** 상위 티어를 고르는 대가가 점수 차가 아니라 주간 한도 압박으로 돌아온다.

---

# 상황별 선택 가이드

지금까지의 근거를 실제 판단으로 압축하면 이렇다.

| 상황 | 선택 | 근거 |
|---|---|---|
| 일상적 에이전틱 코딩, 리팩터링, 코드 리뷰 | **Opus 5** (high 또는 xhigh) | Frontier-Bench 우위 + 절반 가격, Max 기본 모델 |
| 컴퓨터 사용 / GUI 자동화 | **Opus 5** | OSWorld 2.0 에서 Fable 최고점을 1/3 비용으로 추월 |
| 업무 자동화 · 지식 노동 산출물 | **Opus 5** | GDPval-AA v2 +114, AA-Briefcase +146 Elo |
| 최신 프레임워크 · 인프라 버전 대응 | **Opus 5** | 지식 컷오프 4개월 최신 |
| 보안 감사 · 취약점 분석 · 생명과학 | **Opus 5** | Fable 의 세이프가드 오탐 리라우팅 회피 |
| ZDR / 규제 환경 | **Opus 5** | Fable 은 30일 보존 의무로 사용 불가 |
| 사람이 기다리는 인터랙티브 UX | **Opus 5** 또는 Sonnet 5 | Fable 은 공식 분류상 `Slower` |
| Pro 플랜 사용자 전반 | **Opus 5** | 플랜 포함. Fable 은 첫 요청부터 종량 과금 |
| **며칠에 걸친 완전 자율 실행** | **Fable 5** | 장기 실행 에이전트가 설계 목표. 단계 계획·서브에이전트 위임·자체 검증 |
| **사실 정확도가 결정적인 작업** | **Fable 5** | Opus 5 의 환각률 50%(+14%p) 는 실측된 리스크 |
| 6월 Fable 파트너 평가와 닮은 워크로드 | **양쪽 다 측정** | Opus 5 기준 재실행이 없어 비교 근거 부재 |
| 공격적 사이버·자율 생물학의 최상단 | 둘 다 아님 | 해당 역량은 Project Glasswing 의 Mythos 5 |

한 줄로 줄이면: **기본값을 Opus 5 로 두고, Fable 5 는 "며칠짜리 자율 실행" 과 "사실 정확도" 라는 두 개의 명확한 이유가 있을 때만 꺼낸다.**

---

# API 로 옮길 때 걸리는 것들

두 모델 다 Opus 4.7 이후의 요청 형태를 따르지만, Fable 5 에는 추가 제약이 있다.

```python
# Fable 5 — thinking 파라미터를 아예 빼야 한다
response = client.beta.messages.create(
    model="claude-fable-5",
    max_tokens=16000,
    output_config={"effort": "high"},          # low | medium | high | xhigh | max
    betas=["server-side-fallback-2026-06-01"], # 거부 시 폴백, 기본 탑재 권장
    fallbacks=[{"model": "claude-opus-5"}],
    messages=[...],
)
```

- **`thinking` 은 항상 켜져 있다.** `{"type": "disabled"}` 를 보내면 400. `budget_tokens` 도 400 (Opus 5 도 동일).
- **어시스턴트 프리필 불가.** 출력 형태를 강제하려면 `output_config.format` (structured outputs) 을 쓴다.
- **`stop_reason: "refusal"`** 을 `response.content` 를 읽기 **전에** 분기해야 한다. 세이프가드가 걸리면 HTTP 200 에 빈 `content` 가 온다. 위 예시처럼 서버사이드 폴백을 기본으로 켜두는 걸 권한다.
- **ZDR 조직은 모든 요청이 400.** 페이로드를 디버깅하기 전에 조직 보존 설정을 본다.
- `effort` 는 단순 옵션이 아니다. Artificial Analysis 측정에서 effort 단계별로 GDPval-AA v2 점수가 **407 Elo 폭**으로 벌어졌고 출력 토큰 사용량은 low→max 사이 **약 8배** 차이가 났다. **effort 를 max 로 고정해두고 잊는 건 성능이 아니라 청구서를 올리는 선택**이 되기 쉽다.

---

# 근거의 한계

정직하게 적어둔다.

1. **완전히 독립적인 제3자 헤드투헤드가 없다.** 이 글의 수치는 ① Anthropic 자체 발표와 ② Artificial Analysis 측정에서 왔고, 후자는 출시 전 평가 협력을 스스로 공시했다. 시중의 비교 글 상당수는 이 두 출처의 표를 재인용한 것이라 별도 증거로 치지 않았다.
2. **Fable 5 가 앞서는 개별 코딩 벤치마크 수치는 이 글에 싣지 않았다.** 여러 곳에서 Anthropic 시스템 카드를 인용해 소수점대 우위를 보고하지만, 1차 출처 원문으로 직접 확인하지 못한 수치는 쓰지 않는다는 원칙을 따랐다. 해당 항목이 본인 워크로드의 핵심이라면 시스템 카드를 직접 확인하길 권한다.
3. **effort 설정에 따라 두 모델은 사실상 여러 개의 다른 모델이다.** 동일 effort 를 맞추지 않은 비교는 신뢰하기 어렵다.
4. 결국 **본인 태스크로 A/B 를 돌리는 것을 대체할 근거는 없다.** 위 표는 그 실험의 출발점이지 결론이 아니다.

---

# 정리

6주 전이라면 "가장 좋은 모델" 질문에 Fable 5 라고 답했을 것이다. 지금은 다르다.

Anthropic 자신이 문서 첫 줄에서 Opus 5 를 기본값으로 지정했고, Max 플랜의 기본 모델을 바꿨다. 가격은 절반이고, 지식은 4개월 더 최신이고, 레이턴시 등급은 한 칸 위고, 데이터 보존 의무가 없고, 세이프가드 오탐도 훨씬 덜하다. 지능 지표는 사실상 동률이다.

Fable 5 에 남은 자리는 좁지만 분명하다 — **며칠씩 사람 없이 돌아가는 장기 자율 작업**, 그리고 **사실 지식의 정확도가 결정적인 작업**. 이 둘에 해당하지 않는다면, 두 배 가격을 낼 이유를 찾기 어렵다.

---

# References

**1차 출처 (Anthropic 공식)**

- [Introducing Claude Opus 5](https://www.anthropic.com/news/claude-opus-5) — Anthropic, 2026-07-24. Frontier-Bench, CursorBench 3.2, OSWorld 2.0, ARC-AGI 3, AutomationBench 관련 서술 및 "Max 기본 모델" 명시
- [Models overview](https://platform.claude.com/docs/en/about-claude/models/overview) — Anthropic 플랫폼 문서. 스펙 대조표, 가격, 지식 컷오프, 레이턴시 등급, 모델 선택 권고
- [Claude Fable](https://www.anthropic.com/claude/fable) — Anthropic. Fable 5 포지셔닝, 가격, 세이프가드 리라우팅, 30일 데이터 보존 요구
- [Introducing Claude Fable 5 and Claude Mythos 5](https://platform.claude.com/docs/en/about-claude/models/introducing-claude-fable-5-and-claude-mythos-5) — Anthropic 플랫폼 문서. 출시 상세 및 API 변경사항
- [Claude Fable 5 on your plan](https://support.claude.com/en/articles/15424964-claude-fable-5-on-your-plan) — Anthropic 지원 문서. 플랜별 한도 구조 (2026-07-20 변경)

**제3자 측정 (협력 관계 공시됨)**

- [Opus 5: Fable 5 level intelligence at a lower cost per task](https://artificialanalysis.ai/articles/opus-5) — Artificial Analysis, 2026-07-24. Intelligence Index, GDPval-AA v2, AA-Briefcase, AA-Omniscience 환각률, 태스크당 비용, effort 단계별 편차. 해당 문서에 "Anthropic 의 출시 전 평가를 지원했다" 는 공시가 포함되어 있음

*본문의 성능 비교 주장은 위 두 범주의 출처에 근거하며, 중립적 제3자 헤드투헤드 평가는 2026년 7월 30일 기준 확인되지 않았다.*
