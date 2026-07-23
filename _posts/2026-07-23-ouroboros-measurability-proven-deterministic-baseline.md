---
layout: post
title: "측정가능성은 이미 증명됐다 — 라이브 수치를 쫓다 멈추고 결정론적 baseline을 채택한 이유"
date: 2026-07-23 09:30:00 +0900
categories: [AI, Architecture]
tags: [Ouroboros, HarnessEngineering, Measurability, TraceGuard, Benchmark, MeasureDrift, Determinism, EventSourcing]
---

# "숫자 한 줄"을 쫓다 배운 것

지난 글에서 나는 [하네스 엔지니어링의 주축을 Ouroboros로 두겠다](/2026/07/22/ouroboros-harness-main-axis/)고 선언하며, 남은 숙제로 *"실제 run에서 벤치마크를 어떻게 붙일 것인가(in-run 벤치마크)"*를 걸어뒀다. 이번엔 그걸 실제로 파봤다. 그리고 예상과 다른 자리에 도착했다.

결론부터: **깨끗한 라이브 비교수치 한 줄을 쫓는 걸 멈추고, 이미 확보한 결정론적(deterministic) baseline을 공식 baseline으로 채택하기로 했다.** 이게 포기가 아니라 오히려 더 단단한 선택인 이유를 적는다. 핵심 메시지는 하나다 — **Ouroboros의 "측정가능성" 자체는 이미 실증됐다.**

## 무엇을 하려 했나

목표는 소박했다. Ouroboros로 작은 run을 하나 완주시켜, **재귀 RLM 경로 vs 바닐라 단일호출**의 품질·토큰을 나란히 찍은 *fresh 라이브 수치*를 뽑는 것. 그러면 "하네스가 측정 가능하다"를 살아있는 숫자로 보여줄 수 있으니까.

현실은 이랬다.

1. **1차 라이브 run** — 재귀 하위호출 8개가 전부 성공했는데, 마지막 부모 synthesis에서 게이트가 걸렸다: `TraceGuard rejected: parent synthesis completion is not a JSON object`.
2. **모델을 바꿔봄** — 기본 모델 `gemini-3-flash-preview`가 JSON을 마크다운 펜스로 감싸는 게 원인 같아, `gemini-2.5-pro`로 교체(백업+자동복원)했더니 이번엔 atomic 실행 자체가 실패했다. 그 엔드포인트에서 안 서빙되는 모델이었다.
3. **근본 원인** — 파서가 모델 출력을 fence 제거 없이 엄격하게 `json.loads` 했다. 즉 *"실행되는 모델은 JSON을 안 지키고, JSON을 지킬 모델은 이 엔드포인트에서 안 돈다."*

파서를 fence-tolerant하게 고치니 다음 라이브 run은 깔끔하게 완주했다(게이트가 reject 대신 통과). 하지만 그 지점에서 나는 멈췄다. **왜냐하면 이 삽질 자체가 답을 말해주고 있었기 때문이다.**

## 라이브 수치의 함정: 측정가능성이 모델 룰렛에 인질로 잡힌다

생각해보라. 오늘의 "깨끗한 비교수치"는 오늘 어떤 모델이 어떤 엔드포인트에서 JSON을 얼마나 얌전히 뱉었느냐에 달려 있다. gemini-flash가 펜스를 씌우면 게이트가 막히고, 2.5-pro는 아예 안 돌고, 내일 모델이 또 바뀌면 숫자도 흔들린다.

**측정가능성(measurability)이 그날그날의 모델 컨디션에 인질로 잡히면, 그건 측정가능성이 아니다.** 재현 안 되는 숫자는 측정이 아니라 목격담이다.

그래서 방향을 튼다. 측정의 근거를 *모델에 의존하는 라이브 수치*가 아니라, *모델과 무관하게 재현되는 결정론적 baseline*에 둔다. 이게 (C)의 정체다 — 라이브 수치 사냥을 멈추고, API 한 푼 안 쓰고도 언제든 똑같이 재생되는 결정론적 지표를 공식 baseline으로 삼는 것.

## (C)가 근거로 삼는 세 개의 다리

"측정가능하다"는 주장은 세 가지가 동시에 성립해야 한다: ① 모든 스텝이 기록되고(관측), ② 품질이 숫자로 계산되고(지표), ③ 게이트가 실제로 판정한다(강제). 세 다리 전부 이번에 실측으로 확인됐다.

### ① 관측 — 이벤트 소싱 텔레메트리 (Ouroboros)

Ouroboros는 모든 것을 `~/.ouroboros/ouroboros.db`(event-sourced SQLite)에 이벤트로 남긴다. 이번 라이브 run들로 `rlm_run` 이벤트가 **34 → 52건**으로 늘었고, 각 이벤트 payload에는 `schema_version: rlm.trace.v1` + `trace_id` · `subcall_id` · **`parent_trace_id`** 가 박혀 있다. 즉 재귀 하위호출(chunk_001~006 → 부모 synthesis)이 **부모/자식 evidence 핸들의 그래프로** 저널된다. 무슨 일이 있었는지 사후에 정확히 재구성할 수 있다.

### ② 지표 — 결정론적 품질 비교 (API 0원, 재현)

이미 확보된 완주 아티팩트(`rlm-shared-truncation-comparison-v1`)의 수치:

| 지표 | 재귀 RLM | 바닐라 단일호출 |
| --- | ---: | ---: |
| completion_quality_score | **1.00** | **1.00** |
| required_field / retained_fact_citation | 1.00 / 1.00 | 1.00 / 1.00 |
| truncation_boundary / omitted_fact_safety | 1.00 / 1.00 | 1.00 / 1.00 |
| confidence | 0.97 | 0.93 |

`comparison_method: deterministic_score_delta_v1`, **score_delta = 0.0**, `rlm_outperforms_vanilla: false`. 이 표의 핵심은 "RLM이 이겼다"가 아니다. **재귀의 가치는 점수를 올리는 게 아니라, 부모/자식 evidence 핸들이라는 *구조*를 만들어 검증할 자리를 제공하는 것**이다. 그리고 그 구조의 값어치는 아래 실험이 못 박는다.

### ③ 강제 — evidence-gate가 실제로 판정한다

`unsupported-claim-rate` 결정론적 ablation(72 fixtures × 6 policies = **432 evaluations**, Hermes 호출 없음):

| 정책 | Unsupported claim rate | Mean score |
| --- | ---: | ---: |
| single_call_loose | **1.00** | 0.80 |
| single_call_guarded | **0.00** | 1.00 |
| hermes_rlm_evidence_gated | **0.00** | 1.00 |
| hermes_rlm_without_gate | **1.00** | 0.80 |

읽는 법: **evidence-gate가 있으면 환각(근거 없는 주장) 비율이 0.0, 없으면 1.0.** 재귀 구조만으로는 부족하다(`without_gate`도 1.0). 게이트가 붙어야 0이 된다. 그리고 이 게이트는 이론이 아니다 — 이번 라이브 run에서 **비정형 synthesis를 실제로 거부**하는 걸 눈으로 봤다(그래서 파서를 고쳐야 했다). 게이트가 "그럴듯한데 근거 없는" 출력을 성공으로 위장시키지 않고 붙잡는다는 게, 문서 문구가 아니라 관측된 사실로 확인됐다.

## (C)가 뜻하는 것

세 다리를 합치면 이렇게 정리된다.

> **Ouroboros 위에서는 "하네스가 목표에서 얼마나 벗어났나"를 숫자로 물을 수 있다.** 모든 스텝이 이벤트로 남고(①), 품질이 결정론적으로 계산되며(②), 게이트가 근거 없는 주장을 0으로 눌러버린다(③). 이 세 가지는 API를 태우지 않고도 언제든 똑같이 재현된다.

이게 측정가능성의 실증이다. 라이브 비교수치 한 줄은 여기에 *더 예쁜 데코레이션*일 뿐, 증명의 필수 조건이 아니었다. 오히려 그 한 줄에 매달리면 측정의 근거를 모델 룰렛에 넘겨주게 된다. 그래서 (C) — **결정론적 baseline을 공식 baseline으로 채택하고, 여기서 선을 긋는다.**

대비를 다시 새겨두자. Superpowers·OMC 같은 하네스에는 애초에 이벤트 스토어도, 품질 지표 벡터도, 판정 게이트도 없다. **잴 대상 자체가 없다.** 측정가능성이 Ouroboros를 주축으로 삼는 이유인 건 그래서다.

## 남겨둔 정직한 조각

두 가지는 솔직히 열어둔다.

- **Fresh 라이브 vanilla-vs-recursive 비교수치**는 이제 파서 문제가 아니라, `--truncation-benchmark`의 입력 fixture가 이 작업 환경에 없어서 막혀 있다. 출력 아티팩트로 입력을 충실히 복원할 수 없고, 지어내면 그건 가짜 수치다. 그래서 안 만들었다.
- 이 결정론적 실험들이 기록된 실험용 리포(rlm-forge)는 사실상 접는 방향이다. 앞으로 **측정의 무게중심은 Ouroboros 자신의 계측기** — 이벤트 스토어, `measure_drift`/`evaluate`의 지표 벡터(`{score, ac_compliance, goal_alignment, drift_score, uncertainty}`, 통과 게이트 score≥0.8·drift≤0.3), evidence-gate — 로 옮겨간다.

## 한 줄 요약

**측정가능성은 "오늘 라이브로 뽑은 예쁜 숫자"가 아니라 "언제든 재현되는 결정론적 근거"로 증명된다.** 이벤트가 그래프로 쌓이고(관측), 품질이 결정론적으로 계산되며(지표), 게이트가 환각을 0으로 누른다(강제) — 세 다리가 모두 섰다. 그래서 라이브 수치 사냥을 멈추고 결정론적 baseline을 공식 채택한다. Ouroboros의 측정가능성은, 이미 증명됐다.
