---
layout: post
title: "*Opus 5.5* 가 *Fable 5.1* 을 전 항목에서 앞섰다 — 그리고 벤더는 \"격차는 그보다 좁다\" 고 썼다 (2026년 9월 22일 발표 기준)"
date: 2026-09-23 16:05:00 +0900
categories: [ai, llm, engineering]
tags: [Claude, Anthropic, ClaudeOpus55, ClaudeFable51, LLM, Benchmark, ModelSelection, Safeguards, Pricing, ClaudeCode]
---

# 봇이 틀렸고, 스크린샷이 맞았다

오늘 오후에 이런 대화가 있었다. 클러스터 노드에 상주하는 Claude 봇에게 "Fable 5.1 이 Opus 5.5 보다 성능이 낮아?" 라고 물었더니 봇은 "아니요, Fable 이 위 등급입니다" 라고 답했다. 근거는 벤더의 모델 **계열 분류** — Fable 은 Mythos 급 파생이고 Opus 는 그 아래 라인이라는 것. 몇 분 뒤 벤치마크 표 스크린샷이 도착했고, 표는 9개 항목 전부에서 Opus 5.5 가 Fable 5.1 보다 높았다.

봇은 정정했다. 등급과 성능을 섞어 말한 것이다. 그런데 그다음 질문이 더 중요했다 — **"저 자료 확실한지 어떻게 알아?"** 이 글은 그 질문에 답하려고 1차 출처를 직접 대조한 기록이고, 대조 끝에 우리 노드들의 모델을 실제로 바꾼 이유까지 적는다.

이전 글 [Opus 5 vs Fable 5]({% post_url 2026-07-30-claude-opus-5-vs-claude-fable-5-model-selection %}) 에서 "절반 가격의 동급 지능" 구도를 다뤘다. 두 달 만에 같은 구도가 한 단계 더 밀렸다.

---

# 1차 출처 대조 — 스크린샷은 진짜였다

Anthropic 은 2026년 9월 22일 [Claude Opus 5.5 를 발표했다](https://www.anthropic.com/claude-opus-5-5). 같은 날짜의 [시스템 카드 PDF](https://www-cdn.anthropic.com/fc1b44717c85dc068bc6ba5024219938094694bd/Claude%20Opus%205.5%20System%20Card.pdf) 도 올라와 있다. 돌아다니는 스크린샷의 9개 행 × 5개 모델 수치를 발표 페이지의 표와 한 칸씩 대조했고 **전부 일치했다.** 각주 문구까지 같았다.

아래 표는 발표 페이지 그대로다. **벤더 자체 측정**이며, 각주 조건이 결과 해석을 바꾸므로 표 아래를 반드시 같이 읽어야 한다.

| 벤치마크 (분류) | **Opus 5.5** | **Fable 5.1** | Opus 5 | GPT-6 Astra | GPT-5.6 Sol |
|---|---|---|---|---|---|
| Terminal-Bench 4.0 (에이전틱 코딩)¹ | **66.4%** | 55.8% | 52.3% | 57.9% | 37.3% |
| FrontierCode v1.1 Main (에이전틱 코딩) | **54.4%** | 50.3% | 48.0% | 53.3% | 47.5% |
| CursorBench 4.0 (에이전틱 코딩) | **57.8%** | 51.8% | 46.6% | — | 41.7% |
| GDPval-AA v2.1 (지식 노동, Elo) | **1846** | 1735 | 1708 | 1542 | 1588 |
| AutomationBench (업무 워크플로)² | 40.0% | 31.4% | 26.9% | **41.4%** | 28.8% |
| Humanity's Last Exam (도구 사용) | **67.7%** | 65.6% | 63.6% | 57.2% | — |
| Terminal-Bench-Science 0.1 (과학 연구)³ | 58.7% | 52.6% | 29.0% | **64.6%** | 22.4% |
| OSWorld 2.0 (컴퓨터 사용, partial) | **81.8%** | 80.7% | 74.0% | — | — |
| Chartography (차트 인식, 도구 사용) | **89.0%** | 88.4% | 83.4% | — | — |

발표 페이지 각주에서 해석에 영향을 주는 조건만 옮긴다.

- 모든 Opus 5.5 결과는 별도 표기가 없으면 adaptive thinking **max effort** 다. Terminal-Bench 4.0 은 Opus 5.5 가 xhigh effort, GPT-6 Astra 는 OpenAI 가 보고한 high effort 값이다 — 각 모델의 최고점끼리 비교한 것이다.
- Opus 5.5 는 **프로덕션 세이프가드를 켠 채** 측정됐다. 세이프가드가 개입한 사이버보안 과제는 Opus 4.8 이, 생물학·프런티어 LLM 개발 과제는 Opus 5 가 대신 풀었다. 벤더 스스로 "이것이 Opus 5.5 점수를 낮췄을 가능성이 높다" 고 적었다.
- ¹ Terminal-Bench 4.0 표준오차는 Opus 5.5 ±2.6pt, 나머지 Claude 모델 ±1.6–2pt.
- ² AutomationBench 는 Zapier 가 측정했고 **폴백 모델 없이** 돌려서 세이프가드 개입을 실패로 셌다. GPT-6 Astra 가 이 항목에서 앞선 데는 이 조건이 작용한다.
- ³ Terminal-Bench-Science 표준오차는 모델당 ±3.5–5pt. 이 항목의 GPT-6 Astra 우위(64.6 vs 58.7)는 오차 범위를 넘는다.

## 벤더의 자기 반박

같은 페이지에 이 문장이 있다.

> "at these levels of capability we've found that benchmark margins have become a less reliable guide to real-world differences. In our own use, the gap between Opus 5.5 and Claude Fable 5.1 is narrower than these scores suggest."

표를 내놓은 당사자가 표의 격차를 할인하라고 말하는 것이다. 발표 첫 문단의 포지셔닝도 "Fable 5.1 을 이긴다" 가 아니라 이것이다.

> "It performs at the level of Claude Fable 5.1 on most work and costs 40% less to run than Opus 5."

즉 벤더의 공식 주장은 **"Fable 5.1 급 성능을 Opus 5 보다 40% 싸게"** 다. 표는 그 주장을 뒷받침하는 자료이지, 표 자체가 "Fable 을 대체한다" 는 선언은 아니다. 7월의 Opus 5 발표문이 "Fable 5 에 근접" 이었다면, 9월의 Opus 5.5 는 "Fable 5.1 수준" 으로 한 단어가 올라갔다.

---

# 가격 — 이번엔 절반이 아니라 40%

두 발표 페이지의 가격을 나란히 놓는다. 단위는 100만 토큰당 달러.

| | **Opus 5.5** | Opus 5 | **Fable 5.1** |
|---|---|---|---|
| 입력 | **$4** | $5 | $10 |
| 출력 | **$20** | $25 | $50 |
| 캐시 읽기 | **$0.20** | $0.50 | $0.25 |
| 캐시 쓰기 | $5 | $6.25 | (페이지에 미기재) |
| API ID | `claude-opus-5-5` | `claude-opus-5` | `claude-fable-5-1` |

Opus 5.5 는 Opus 5 대비 토큰 단가 20% 인하에 캐시 읽기 60% 인하다. 벤더가 말하는 "40% 절감" 은 단가 인하에 **작업당 토큰 사용량 감소**를 더한 수치다 — "It costs less per token than Opus 5 and uses fewer tokens per task, which nets out to a 40% drop in costs." 단가만 보고 40% 를 기대하면 안 된다.

Fable 5.1 과 비교하면 입력·출력 단가는 정확히 2.5배 차이다. 두 페이지 어디에도 이 비교는 직접 쓰여 있지 않지만 숫자는 그렇다. 캐시 읽기는 $0.20 vs $0.25 로 거의 같다.

발표 페이지에는 Fable 5.1 과의 직접 비용 사례가 하나 있다. HAProxy 를 C 에서 Rust 로 옮기는 내부 테스트에서 두 모델 모두 회귀 테스트를 거의 통과했고, Opus 5.5 는 9.5시간, Fable 5.1 은 12시간이 걸렸으며 비용은 51% 적었다. 벤더 내부 사례 한 건이므로 일반화는 못 하지만, 방향은 가격표와 일치한다.

fast mode 는 입력 $8 · 출력 $40 에 최대 2.5배 속도로 Claude Code 와 Claude Platform 에서 제공된다.

---

# 벤치마크에 안 나오는 것 — 세이프가드가 Fable 급으로 올라왔다

7월 글에서 Opus 5 를 고를 이유 중 하나로 "세이프가드 리라우팅이 Fable 보다 훨씬 덜하다" 를 꼽았다. 이번엔 그 차이가 **없어졌다.** 발표 페이지 기준:

- "Because Opus 5.5 is comparable to Claude Mythos 5.1 in biology and cybersecurity, we're deploying it with safeguards similar to those on Claude Fable 5.1."
- Opus 라인 최초로 사이버보안·생물학·증류(distillation) 세 영역에서 Fable 5.1 과 같은 급의 세이프가드를 달고 나왔다. 개입 시 다른 모델로 **투명하게 폴백**한다.
- 사이버보안: 대부분의 사이버보안 과제는 Opus 4.8 로 재라우팅된다. 자기 코드의 버그를 찾고 고치는 건 여전히 된다. Cyber Verification Program 이 Opus 5.5 로 확장되며 3단계 티어로 Mythos 모델 접근까지 이어진다.
- 생물학: Fable 5.1 과 동일한 세이프가드. 검증된 조직은 Life Sciences Verification Program 으로 신청.
- 증류 방지: Fable 5.1 에서 도입한 preserved thinking 이 적용된다. 2026년 8월 31일 이후 생성된 API 계정 대상.
- thinking 모드는 더 이상 끌 수 없다.

Fable 5.1 과 Mythos 5.1 의 관계도 [Fable 5.1 발표 페이지](https://www.anthropic.com/claude-fable-and-mythos-5-1)에 명시돼 있다 — "Claude Fable 5.1 and Claude Mythos 5.1 are the same model, but with different levels of safeguards." Mythos 5.1 은 미국 내 검증된 조직에만 열려 있다.

정리하면 **"Opus 는 세이프가드가 느슨해서 편하다"** 는 7월의 선택 근거는 이제 성립하지 않는다. Opus 5.5 는 Fable 5.1 과 같은 급의 안전장치를 달고 있다. 보안 연구나 생물학 쪽 작업이라면 Opus 5.5 를 골라도 Fable 과 같은 리라우팅을 겪는다.

발표 페이지에 **없는** 것도 적어 둔다. 컨텍스트 윈도우, 최대 출력, 지식 컷오프, 레이턴시 등급은 발표 페이지에 나오지 않는다. 플랫폼 문서의 모델 비교표에서 확인해야 하고, 이 글에서는 확인하지 않았으므로 쓰지 않는다.

---

# 우리 클러스터에서는 어떻게 했나

k3s 6노드에 노드마다 Claude Code 상주 봇이 하나씩 돈다 ([이전 글]({% post_url 2026-09-19-resident-claude-agent-on-each-k3s-node %})). 오늘 기준 배치는 이렇게 바뀌었다.

| | 어제까지 | 오늘 |
|---|---|---|
| 노드 5개 | `claude-opus-4-8[1m]` | `claude-opus-5-5[1m]` |
| 커맨드 노드 1개 | `fable[1m]` (Fable 5.1) | 유지, 전환 검토 중 |

바꾼 근거는 벤치마크 표가 아니라 **가격표와 세이프가드 문단**이다. 벤더가 "격차는 좁다" 고 한 표를 근거로 상위 모델을 내리는 건 약하다. 하지만 같은 급의 세이프가드에 입력·출력 단가가 2.5배 차이라면, 노드 봇처럼 짧은 대화형 작업을 온종일 하는 자리는 Opus 5.5 가 맞다. 남은 Fable 자리는 7월 글의 결론과 같다 — 며칠씩 사람 없이 돌아가는 장기 자율 작업. 그 자리에 정말 Fable 이 필요한지는 이번 주에 실제 작업으로 재 볼 생각이다.

실측 한 가지: `~/.claude/settings.json` 의 `model` 을 `claude-opus-5-5[1m]` 로 바꾸고 봇을 재시작하면 Claude Code 배너에 "Opus 5.5 (1M context)" 가 뜬다. 1M 컨텍스트 접미사 `[1m]` 은 5.5 에서도 그대로 동작했다.

---

# 정리

- 돌아다니는 벤치마크 표는 진짜다. Anthropic 발표 페이지(2026-09-22)와 9행 × 5열 전부 일치한다.
- 그 표에서 Opus 5.5 는 Fable 5.1 을 9개 항목 전부에서 앞선다. 단 벤더 자체 측정이고, 벤더 스스로 "실사용 격차는 이보다 좁다" 고 썼다.
- 공식 포지셔닝은 "Fable 5.1 급 성능을 Opus 5 대비 40% 싸게" 다. Fable 5.1 과는 단가 2.5배 차이.
- 7월에 Opus 를 고를 이유였던 "느슨한 세이프가드" 는 사라졌다. Opus 5.5 는 Fable 5.1 급 세이프가드를 단다.
- 봇이 "등급" 을 근거로 답한 건 틀렸다. 계열 분류는 성능 근거가 아니다. 1차 출처를 열어 대조하는 데 3분이 걸렸고, 그게 답이었다.

---

# References

**1차 출처 (Anthropic 공식)**

- [Introducing Claude Opus 5.5](https://www.anthropic.com/claude-opus-5-5) — Anthropic, 2026-09-22. 벤치마크 표와 각주, 가격, 세이프가드, HAProxy 사례, "gap is narrower" 서술
- [Claude Opus 5.5 System Card](https://www-cdn.anthropic.com/fc1b44717c85dc068bc6ba5024219938094694bd/Claude%20Opus%205.5%20System%20Card.pdf) — Anthropic, 2026-09-22
- [Introducing Claude Fable 5.1 and Claude Mythos 5.1](https://www.anthropic.com/claude-fable-and-mythos-5-1) — Anthropic, 2026-09. Fable 5.1 가격, Fable/Mythos 관계, preserved thinking
- [Claude Fable](https://www.anthropic.com/claude/fable) — Anthropic. Fable 라인 포지셔닝

*본문의 성능 수치는 전부 벤더 자체 측정이다. 중립 제3자의 Opus 5.5 vs Fable 5.1 헤드투헤드 평가는 2026년 9월 23일 기준 확인하지 않았다.*
