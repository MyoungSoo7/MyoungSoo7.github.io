---
layout: post
title: "믿는 루프에서 검증하는 루프로 — Ouroboros 0.35 → 0.50 구조 진화 해부"
date: 2026-07-22 05:00:00 +0900
categories: [AI, Architecture]
tags: [Ouroboros, HarnessEngineering, TraceGuard, SpecFirst, Agent, ClaudeCode, ReleaseAnalysis, Architecture]
---

# 8일 만에 절반이 다시 지어진 코드베이스

[전편]({% post_url 2026-07-22-superpowers-omc-ouroboros-harness-stack %})에서 Ouroboros를 3축 하네스 스택의 WHAT 축 — 명세의 하네스 — 으로 소개했다. 그 글을 쓰며 로컬에 깔린 버전을 확인했더니 v0.35.0. 그런데 업스트림을 보니 최신이 **v0.50.5**였다. 내가 설치한 시점(7월 11일경)부터 최신 릴리스(7월 19일)까지 **8일**. 그 사이 마이너 버전이 15계단 뛰었다.

단순 버전 인플레가 아닌지 두 태그의 소스 트리를 통째로 비교해봤다. 결론: **구조가 실제로 절반쯤 다시 지어졌다.** 그리고 그 방향이 이 시리즈가 계속 이야기해온 주제와 정확히 일치한다 — *에이전트의 자가보고를 믿지 말고, 실행의 증거를 검증하라.*

## 수치로 보는 변화

| 지표 | v0.35.0 | v0.50.5 | 변화 |
|---|---:|---:|---|
| 파이썬 파일 수 | 302 | 466 | **+54%** |
| `orchestrator/` | 36 | 100 | **2.8×** |
| `mcp/` | 10 | 52 | **5.2×** |
| `plugin/` | 5 | 42 | **8.4×** |
| `auto/` | 12 | 40 | 3.3× |
| `cli/` | 7 | 38 | 5.4× |
| `tui/` | 7 | 25 | 3.6× |
| 신규 최상위 모듈 | — | **10개** | harness, interview_adapters, profiles, runtime, backends, dashboard_web, config_tui, dashboard, gjc_bridge, kiro |
| 소멸 최상위 모듈 | 3개 | — | execution, routing, secondary |

## 구조도 — Before / After

**v0.35.0 — 루프의 골격기.** 스펙 우선 루프(interview→seed→run→evaluate→evolve)의 뼈대는 완성돼 있고, 실행·라우팅·평가가 비슷한 크기의 모듈로 수평하게 늘어서 있다.

```
                    v0.35.0  (302 files)
┌─────────────────────────────────────────────────────┐
│                      cli / tui                      │  얇은 셸 (7+7)
├─────────────────────────────────────────────────────┤
│   interview → seed → run → evaluate → evolve        │
│                                                     │
│  ┌────────────┐ ┌───────────┐ ┌────────────────┐    │
│  │orchestrator│ │ execution │ │  evaluation    │    │
│  │    (36)    │ │routing(13)│ │     (14)       │    │
│  └────────────┘ └───────────┘ └────────────────┘    │
│  ┌──────┐ ┌────────┐ ┌────────┐ ┌─────────────┐     │
│  │agents│ │providers│ │ events │ │ evolution   │     │
│  │ (24) │ │  (16)  │ │  (12)  │ │   (10)      │     │
│  └──────┘ └────────┘ └────────┘ └─────────────┘     │
├─────────────────────────────────────────────────────┤
│          mcp (10)      ·      plugin (5)            │  부속품
└─────────────────────────────────────────────────────┘
     평가의 근거 = 에이전트가 쓴 transcript (자가보고)
```

**v0.50.5 — 검증 계약기.** 실행·라우팅이 orchestrator로 흡수돼 수직 통합되고, 그 옆에 완전히 새로운 축 — **harness/** — 가 선다. 평가의 근거가 자가보고에서 오케스트레이터 자신의 실행 기록으로 바뀐다.

```
                    v0.50.5  (466 files)
┌──────────────────────────────────────────────────────────┐
│        cli (38) · tui (25) · config_tui · dashboard_web  │  두꺼운 셸
├──────────────────────────────────────────────────────────┤
│  interview ──▶ seed ──▶ run ──▶ evaluate ──▶ evolve      │
│      │          │                   ▲                    │
│ interview_   AC = 기계 계약          │ 실행기록 기반 판정   │
│ adapters/    AcceptanceCriterion    │ + reward-hacking   │
│ (질문팩)      Spec{verify_command,   │   거부권(veto)      │
│              artifacts, assertion}  │                    │
│  ┌────────────────────────────┐  ┌──────────────────┐    │
│  │  orchestrator (100)        │  │   harness/ (신설) │    │
│  │  execution·routing 흡수     │  │  deliver_gate    │    │
│  │  verify-by-default         │◀─┤  traceguard_     │    │
│  │  실행기록 = 단일 진실        │  │    validator     │    │
│  └────────────────────────────┘  │  claim_term_guard│    │
│  ┌──────┐ ┌─────────┐ ┌───────┐  │  run_snapshot    │    │
│  │agents│ │providers│ │ events│  │  journal/        │    │
│  └──────┘ │+backends│ └───────┘  │   projection     │    │
│           │ +runtime│            └──────────────────┘    │
├──────────────────────────────────────────────────────────┤
│        mcp (52)          ·          plugin (42)          │  1급 표면
└──────────────────────────────────────────────────────────┘
     평가의 근거 = 오케스트레이터의 authoritative 실행 기록
```

## 소멸이 말해주는 것 — 수평 나열에서 수직 통합으로

`execution/`, `routing/`, `secondary/` 세 모듈이 사라졌다. 기능이 죽은 게 아니라 **orchestrator로 흡수**됐다(36→100 파일이 그 증거다). 0.35에서는 "실행"과 "라우팅"과 "오케스트레이션"이 대등한 이웃이었다. 0.50에서는 오케스트레이터가 실행을 직접 소유한다.

이 통합은 취향 문제가 아니다. v0.50.0 릴리스 노트의 표현을 빌리면, 이전까지 평가는 *"에이전트 자신이 쓴 transcript에서 성공을 재구성"*했다. 실행이 오케스트레이터 밖에 있으면 오케스트레이터는 전해 들은 이야기로 판정할 수밖에 없다. 실행을 안으로 끌어들여야 **"무엇이 실제로 실행됐는가"의 단일 진실(authoritative execution record)**을 쥘 수 있고, 그래야 그 기록에 대고 계약을 검증할 수 있다. 구조 변화가 철학 변화의 전제조건이었던 셈이다.

## 신설 축 1 — harness/: TraceGuard의 승격

새 모듈 중 가장 상징적인 것은 `harness/`다. 안을 열어보면:

```
harness/
├── deliver_gate.py          # 산출물 게이트
├── deliver_routing.py
├── traceguard_validator.py  # ← 주목
├── claim_term_guard.py      # 주장-용어 가드
├── run_snapshot.py          # 실행 스냅샷
├── journal.py / projection.py / projection_builder.py
```

`traceguard_validator.py` — 며칠 전 [실험 레포 rlm-forge를 라이브로 돌려보며]({% post_url 2026-07-22-superpowers-omc-ouroboros-harness-stack %}) 확인했던 그 **TraceGuard**(부모의 주장은 자식이 만든 증거 핸들로만 뒷받침된다, 위반 시 하드 거부)가 위성 실험체에서 **본체 코어 모듈로 승격**된 것이다. 파일명 옆의 `claim_term_guard`, `run_snapshot`, `journal/projection`까지 합쳐 보면 이 모듈의 정체는 명확하다: **"주장(claim)과 증거(evidence)를 분리하고, 증거 없는 주장을 기계적으로 거부하는 계층.**" 실험에서 증명된 패턴이 한 릴리스 사이클 만에 제품의 등뼈로 들어왔다.

## 신설 축 2 — 계약 스파인: 문자열 AC의 종말

v0.50.0의 자기 선언은 부제부터 노골적이다: **"The Verifiable Loop: contracts, not claims."**

핵심은 수용 기준(Acceptance Criteria)의 자료형 변화다. 0.35까지 AC는 **사람이 읽는 문자열**이었고, 판정자는 그것을 선의로 해석했다. 0.50에서 AC는 기계 계약이 된다:

```
AcceptanceCriterionSpec {
  verify_command:      # 이 명령이
  expected_artifacts:  # 이 산출물을 만들고
  output_assertion:    # 출력이 이 조건을 만족하면 성공
}
```

그리고 이 계약이 루프 전체를 관통한다 — 실행자는 프롬프트에 SUCCESS CONTRACT 블록을 받고, 증거 게이트는 선언된 명령·산출물이 **실행 기록에 실재하는지** 대조하고, 평가자는 같은 계약을 보고 판정한다. 가장 흥미로운 것은 **reward-hacking 거부권**: 다단계 합의 평가가 승인으로 기울어도, 높은 신뢰도의 "게이밍 신호"가 감지되면 승인 자체를 거부한다. 채점 기준을 역이용하는 에이전트를 상정하고 설계한 것이다. verify 게이트는 이제 opt-in이 아니라 **기본 경로**다.

부속 변화도 같은 방향이다: `run` 성공 시 3단 평가가 자동 체인되고(실패해도 run을 좌초시키지 않는 격리 포함), 모든 프로바이더(copilot/gemini/hermes/kiro/goose/...)가 같은 기계 판독 계약을 받도록 어휘가 통일됐다.

## 신설 축 3 — interview_adapters/: 질문도 모듈이 된다

인터뷰(소크라테스식 질문)는 0.35에도 있었지만, 0.50은 이를 **도메인 질문팩** 구조로 확장했다. `packs/ui_ux_basics.yaml` 같은 팩이 registry·trigger로 로드되는 구조 — 특정 도메인 작업이 감지되면 그 도메인의 "숨은 가정을 캐는 질문 세트"가 자동 투입되는 그림이다. 명세 하네스의 입력 단이 플러그인화된 것으로, WHAT 축의 확장성이 여기서 나온다.

그 외 — `mcp/`가 10→52로 커지며 에이전트 세션 안에서 쓰는 표면이 1급이 됐고, `plugin/` 5→42, 새 백엔드(Grok Build CLI, Antigravity CLI), `dashboard_web/`·`config_tui/` 같은 관측·설정 UI가 셸을 두껍게 만들었다.

## 해석 — WHAT 축이 자기 안에 HOW 게이트를 내장하기 시작했다

전편의 3축 좌표계로 읽으면 이번 진화의 의미가 선명해진다. 0.35의 Ouroboros는 순수한 WHAT 축이었다 — 스펙을 확정하고, 평가는 다른 축(절차 하네스의 리뷰 게이트)에 상당 부분 기대는 구조. 0.50은 **WHAT 축이 자기 완결적 검증 계층(harness/)을 내장**한 형태다. 스펙에 검증 명령을 심고, 실행 기록으로 대조하고, 게이밍을 거부한다.

이것은 이 시리즈 전체를 관통해온 명제의 업스트림 버전이다. [아키텍처 편]({% post_url 2026-07-22-hexagonal-msa-oop-coverage-harness %})에서 "위반이 스스로 드러나는 코드베이스"를 말했고, 실무에서도 유닛이 전부 초록인데 라이브에서만 버그가 드러나는 것을 봤다. Ouroboros 팀도 같은 결론에 도달한 것이다: **그럴듯한 보고가 아니라 실행된 사실만 신뢰한다.** 도구 생태계 전체가 같은 방향으로 수렴하고 있다는 것 — 이게 이번 비교분석의 가장 큰 수확이다.

## 그래서, 업그레이드할 것인가

내 환경 기준의 판단:

- **CLI/MCP(현재 0.35)** — 올릴 가치가 충분하다. 계약 기반 AC와 verify-by-default는 바로 체감되는 변화고, 특히 MCP 표면 5배 확장은 세션 안 사용성에 직결된다. 단, 8일에 15버전이 뛰는 속도의 프로젝트다 — 고정 버전으로 올리고, 자동 추적은 하지 않는다.
- **rlm-forge venv(0.30.1 git-ref 고정)** — 건드리지 않는다. 실험 레포는 특정 커밋에 논문·벤치마크가 묶여 있어 재현성이 우선이다. TraceGuard가 본체에 승격된 지금, 실험체의 역할은 이미 완수됐다.
- 한 가지 정직한 유보: `traceguard_validator.py`의 **존재와 위치**는 확인했지만, rlm-forge 버전과의 API 호환성까지 검증하진 않았다. 승격 과정에서 형태가 달라졌을 수 있다.

8일 치 diff에서 아키텍처 교훈 하나를 건졌다. **모듈 지도를 바꾸는 릴리스는 기능 릴리스가 아니라 철학 릴리스다.** execution이 orchestrator로 흡수된 것은 리팩터링이 아니라 "누가 진실을 소유하는가"에 대한 답변이었다.

---
*시리즈: [아키텍처 규율은 어떻게 에이전트의 하네스가 되는가]({% post_url 2026-07-22-hexagonal-msa-oop-coverage-harness %}) · [Superpowers × OMC × Ouroboros 3축 스택]({% post_url 2026-07-22-superpowers-omc-ouroboros-harness-stack %})*
