---
layout: post
title: "이미 Claude Code를 쓴다면 — Gajae-Code보다 Ouroboros가 나은 이유"
date: 2026-07-24 11:00:00 +0900
categories: [AI, Architecture]
tags: [ouroboros, gajae-code, claude-code, harness-engineering, mcp, measure-drift, spec-first, tracguard, lock-in]
---

# 질문을 바꾸면 답이 정해진다

"Gajae-Code와 Ouroboros 중 뭐가 낫냐"는 그 자체론 답이 갈립니다. 앞선 [두 하네스 비교글]({% post_url 2026-07-24-gajae-code-vs-ouroboros-harness %})에서 정리했듯 둘은 무게중심이 달라서, 상황에 따라 답이 달라지니까요.

그런데 질문에 전제를 하나 붙이면 답이 거의 정해집니다. **"나는 이미 Claude Code를 쓴다"** 는 전제입니다. 이 한 줄이 답의 8할을 결정합니다.

이유는 단순합니다. **Claude Code 유저에게 이 둘은 층위가 다릅니다.**

- **Ouroboros = Claude Code 위에 '얹는' 계층.** MCP 서버라서 `mcp__ouroboros__*` 도구로 Claude Code 안에 그대로 마운트됩니다. 쓰던 Claude Code를 그대로 두고 능력만 더합니다.
- **Gajae-Code = Claude Code와 같은 급의 '완결형 하네스'.** 자체 `gjc` CLI · `ModelRegistry` · `ToolSession` · TUI를 가진 독립 하네스입니다. 쓰려면 갈아타거나 병행해야 합니다.

즉 Claude Code 유저에게 **Gajae-Code는 이미 가진 런타임(모델·툴·조종석)을 한 벌 더 갖는 '중복'** 이 되기 쉽고, **Ouroboros는 없던 능력을 더하는 '보완'** 이 됩니다. 여기서부터 나머지가 파생됩니다.

---

## Claude Code를 쓸 때 Ouroboros가 나은 점 4가지

### 1) 대체가 아니라 추가 — 런타임 중복이 없다

Ouroboros는 MCP 도구 세트로 붙으므로, Claude Code의 **모델 접근·도구·권한·hooks·TUI를 전부 그대로** 둔 채 스펙 루프만 얹습니다. 반면 Gajae-Code를 도입하면 이미 Claude Code가 주는 스택(모델 레지스트리·툴 경계·조종석)을 **통째로 다시** 들고 옵니다. 같은 일을 하는 런타임을 두 벌 굴리는 셈이죠.

앞 글에서 정리한 프레임으로 말하면 — Gajae-Code는 조종석·엔진을 한 몸으로 묶은 **통합형**, Ouroboros는 조종석(우로코드)과 엔진(호스트 독립 MCP)을 떼어 놓은 **분리형**입니다. 그리고 **분리형이라서** Claude Code 유저는 프론트로 Claude Code를 그대로 쓰고 Ouroboros의 엔진만 얹을 수 있습니다. 통합형은 이 "엔진만 떼어 얹기"가 안 됩니다.

### 2) measure_drift — '얼마나 벗어났나'를 수치로 잰다

긴 작업일수록 무서운 건 목표에서 조용히 이탈(drift)하는 것입니다. Ouroboros는 목표를 **불변 seed로 굳혀** 놓고, 결과가 그 seed에서 얼마나 벗어났는지를 `measure_drift`로 **수치화**합니다.

Gajae-Code의 검증은 **출력 레벨**입니다 — tool result · artifact · completion delivery. "무엇이 나왔나"는 보지만 "원래 의도에서 얼마나 멀어졌나"라는 **거리**는 나오지 않습니다. Claude Code 위에서 몇십 턴짜리 작업을 돌릴 때, 이 거리 지표의 유무는 큰 차이입니다.

### 3) TraceGuard — 근거 없는 주장을 결정론적으로 막는다

멀티에이전트를 쓰면 "그럴듯한데 근거 없는" 결과가 부모로 새어 올라오는 게 고질병입니다. Ouroboros(그리고 그 위의 rlm-forge)는 **TraceGuard / evidence-gate**로, 부모의 종합이 자식이 만든 증거 없이는 주장하지 못하도록 **규칙으로** 강제합니다. LLM 판단에 기대는 게 아니라 증거 인용 여부를 결정론적으로 검사하죠. Gajae-Code의 `team` 게이트에는 이런 증거 강제 장치가 (적어도 표 기준) 드러나 있지 않습니다.

### 4) 락인 없음 + Claude Code를 백엔드로 부린다

가장 잘 맞물리는 지점입니다. Ouroboros의 `OrchestratorRunner`는 **claude 자식 에이전트를 spawn**합니다. 즉 Ouroboros가 **Claude Code를 자기 '실행 백엔드'로 부립니다.** "나는 Claude Code를 쓴다"는 전제와 정확히 포개지죠 — 측정·오케스트레이션은 Ouroboros가, 실제 코딩 실행은 Claude Code가 맡습니다.

덤으로 **락인이 없습니다.** seed는 호스트 독립이라, 나중에 Codex나 OpenCode로 옮겨도 같은 스펙·같은 루프가 따라옵니다. Gajae-Code로 갈아타면 그 하네스 안에 자산이 묶입니다.

---

## 솔직한 반대편 — Ouroboros가 굳이 필요 없는 경우

균형을 위해 반대 방향도 적어 둡니다. 과장하면 나중에 내가 손해니까요.

- **짧은 단발 코딩엔 그냥 Claude Code로 충분합니다.** Ouroboros도 MCP 도구 목록 컨텍스트 비용 + 자식 spawn 비용이 있어 **공짜가 아닙니다.** 스펙에 오래 묶이는 작업이 아니면 오버헤드만 늘 수 있습니다.
- **Gajae-Code의 강점(통합 코딩 TUI 한 벌)은 Claude Code 유저에겐 이미 있는 것**이라 이득이 상쇄됩니다. 반대로 말하면, Claude Code를 **안** 쓰는 사람에겐 Gajae-Code의 완결성이 오히려 매력일 수 있습니다. 이 글의 결론은 어디까지나 "이미 Claude Code를 쓴다"는 전제 위에서만 성립합니다.
- **Ouroboros의 in-run 벤치마크는 아직 미해결입니다.** 오프라인 replay/truncation 검증은 통과 상태지만, live run 한 번 한 번의 품질·토큰 트레이드오프를 실시간으로 재는 문제는 여전히 열려 있습니다. 만능이 아닙니다.

---

## 한 줄 요약

**이미 Claude Code가 조종석이라면, 같은 조종석을 하나 더 들이는(Gajae-Code) 것보다 그 위에 스펙·측정·오케스트레이션을 얹는(Ouroboros) 쪽이 결이 맞는다.** Ouroboros는 Claude Code를 대체하지 않고 백엔드로 부리며, measure_drift로 이탈을 재고, TraceGuard로 근거를 강제하고, 락인을 남기지 않는다. 예전에 정리한 **"주축 하나(측정하는 Ouroboros) + 부품 몇 개(실행하는 Claude Code)"** 구도 그대로다. 물론 — 짧은 작업엔 그냥 Claude Code로 충분하다는 단서를 잊지 않은 채로.

> 관련 글: [두 하네스, 두 무게중심 — Gajae-Code vs Ouroboros 비교분석]({% post_url 2026-07-24-gajae-code-vs-ouroboros-harness %}) · [하네스의 주축을 고르다 — 왜 Ouroboros인가]({% post_url 2026-07-22-ouroboros-harness-main-axis %})
