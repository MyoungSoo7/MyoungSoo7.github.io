---
layout: post
title: "oh-my-claudecode(OMC): Claude Code 위에 얹는 멀티에이전트 오케스트레이션 레이어"
date: 2026-07-22 03:00:00 +0900
categories: [AI, Architecture]
tags: [ClaudeCode, OMC, MultiAgent, Orchestration, AgentTeams, Harness]
---

# 에이전트 하나로 부족할 때: 오케스트레이션이라는 레이어

이전 글에서 [Superpowers의 프롬프트 하네스](/2026/07/22/Superpowers-프롬프트를-넘어-에이전트의-작업-방식을-설계하는-하네스/)를 다뤘습니다 — 에이전트 **하나**가 올바른 절차를 밟게 만드는 규율의 층이었죠. 이번 글은 그 다음 층입니다. **oh-my-claudecode(OMC)** 는 Claude Code 위에 "여러 에이전트를 어떻게 편성하고, 위임하고, 검증시킬 것인가"라는 **오케스트레이션 레이어**를 얹는 플러그인입니다.

슬로건부터 노선이 분명합니다: *"Teams-first Multi-agent orchestration for Claude Code. Zero learning curve."* — 그리고 다소 도발적인 *"Don't learn Claude Code. Just use OMC."*

## 왜 '레이어'인가: 모드 전환이 아니라 층 쌓기

전통적인 접근은 컨텍스트를 끊고 모드를 갈아탑니다 — "계획 모드로 전환 → 실행 모드로 전환". OMC가 근본적으로 다른 지점은 **모드 스위칭이 아니라 레이어 컴포지션**이라는 것입니다. Claude Code의 스킬 시스템을 이용해 행동 양식을 **위에 쌓아** 올리기 때문에, 하나의 세션 흐름 안에서 오케스트레이션 능력이 활성화됩니다.

구조를 단순화하면 이렇게 됩니다.

```
사용자 (자연어 한 줄)
   │
   ▼
오케스트레이션 레이어 (OMC)
   ├─ 라우팅: 작업 복잡도 → 적절한 에이전트/모드 선택
   ├─ 편성: 스무 종 남짓의 전문 에이전트 (버전에 따라 19~27종)
   ├─ 모델 배정: Haiku/Sonnet/Opus 티어 매칭
   ├─ 상태/메모리: .omc/ 아래 세션·아티팩트·스킬
   └─ 검증 루프: 될 때까지 verify → fix
   │
   ▼
Claude Code (실행 기반: 도구, 서브에이전트, 스킬)
```

## 에이전트 편성: 전문화 + 모델 티어 매칭

OMC는 아키텍처 리뷰, 리서치, 설계, 테스트, 데이터 분석 등 역할별로 전문화된 에이전트 로스터를 둡니다. 대표적인 원형(archetype)만 봐도 편성 철학이 읽힙니다.

- **Executor** — 구현 담당
- **Reviewer / Critic / Security-review** — 서로 다른 렌즈의 검토자들
- **Plan / PRD / Verify / Fix** — 팀 파이프라인의 단계 담당자
- **Advisor / Synthesizer** — 교차 모델 합의(consensus) 담당

흥미로운 건 **Model × Agent 호환성 매트릭스**입니다. 모든 에이전트에 가장 비싼 모델을 쓰는 게 아니라, 단순 작업은 Haiku, 복잡한 추론은 Opus로 라우팅해 30~50% 토큰을 아끼는 **premium / balanced / budget** 프리셋을 제공합니다. 멀티에이전트의 최대 약점인 비용 폭발을 편성 단계에서 제어하는 설계입니다.

## 실행 모드: 상황에 맞는 편성 패턴

OMC의 오케스트레이션 모드는 "몇 명을, 어떤 대형으로 뛰게 할 것인가"의 패턴 목록입니다.

| 모드 | 편성 | 쓰임새 |
|------|------|--------|
| **Team** (권장 표준) | `plan → prd → exec → verify → fix` 단계형 파이프라인 | 제대로 된 기능 개발. Claude Code 네이티브 팀 기능 위에서 동작 |
| **Autopilot** | 리드 에이전트 1 + 자율 위임 | 요구 한 줄 → 끝까지 자율 완주 |
| **Ralph** | 집요한 verify/fix 루프 | "조용한 부분 성공" 방지 — 검증이 통과할 때까지 안 놓아줌 |
| **Ultrawork** | 최대 병렬 | 대량 수정·리팩토링 버스트 |
| **UltraQA** | 품질 게이트 사이클 | tests/build/lint/typecheck 가 다 녹색이 될 때까지 |
| **Pipeline** | 순차 강제 | 엄격한 순서가 필요한 작업 |
| **omc team** (CLI) | tmux 분할 페인에 실제 CLI 프로세스 편성 | Codex·Gemini·Cursor 등 **타사 에이전트 CLI**까지 팀원으로 |

호출 방식이 이 도구의 성격을 잘 보여줍니다. 복잡한 명령 문법 대신 **자연어 매직 키워드**입니다 — 프롬프트에 `autopilot`, `ralph`, `ulw`, `ultrathink` 같은 단어를 섞으면 해당 모드가 활성화되고, `stopomc`로 멈춥니다. "Zero learning curve"가 마케팅 문구가 아니라 인터페이스 설계 원칙인 셈입니다.

## 컨텍스트 손실과 싸우는 메모리 계층

멀티에이전트의 고질병은 **단계 사이의 컨텍스트 증발**입니다. 앞 단계 에이전트가 내린 결정을 뒷 단계가 모르는 문제죠. OMC는 이를 계층화된 메모리로 받습니다.

- **Priority Memory** — CLAUDE.md와 비슷한 역할이지만 OMC가 자동 관리하며 에이전트 간 공유
- **Working Memory** — Team 모드의 단계마다 자동 갱신되어, 후반 단계 에이전트가 전반의 결정을 승계
- **커스텀 스킬 추출** — 디버깅 과정에서 얻은 패턴을 `/skillify`로 재사용 가능한 스킬 파일(`.omc/skills/`)로 굳혀, 프로젝트에 커밋 가능

세 번째가 특히 눈에 띕니다. "값비싼 삽질의 결과를 선언적 파일로 굳혀 반복을 없앤다"는 점에서, 제가 운영 중인 메모리 파일 체계나 Superpowers의 스킬 철학과 정확히 같은 결에 있습니다. 이 패턴은 이제 에이전트 생태계의 공통 문법이 되어가는 듯합니다.

## 관측가능성: 오케스트라에는 지휘봉이 보여야 한다

여러 에이전트가 병렬로 뛰기 시작하면 "지금 무슨 일이 벌어지고 있는가"가 블랙박스가 되기 쉽습니다. OMC는 **HUD(Heads-Up Display)** 상태줄로 이를 노출합니다 — 에이전트별 실행 상태, 토큰 사용량, 모델 라우팅 결정, 병렬화 진행률이 실시간으로 보입니다. 사후에는 `omc session friction report`로 컨텍스트 비대화나 마찰 신호를 분석할 수 있고요.

멀티에이전트 도구를 평가할 때 저는 이 부분을 중요하게 봅니다. **위임의 전제는 감시 가능성**입니다. 보이지 않는 자율성은 신뢰가 아니라 방치가 되기 때문입니다.

## 교차 모델 자문: 한 모델의 맹점을 다른 모델로

`omc ask`(세션 안에서는 `/ask`)는 Codex, Gemini, Grok, Cursor 같은 **타사 모델에게 자문을 구하고 그 결과를 아티팩트로 저장**하는 서브시스템입니다. `/ccg` 스킬은 아예 Codex + Antigravity의 답을 Claude가 종합하는 3-모델 합의를 만듭니다.

```bash
omc ask codex "이 아키텍처의 리스크를 짚어줘"
omc ask grok "이 코드 리뷰를 교차 검증해줘"
```

단일 모델의 확신에 찬 오답을 다른 모델의 시선으로 걸러내는 것 — 검증 레이어를 모델 다양성으로 구현한 접근입니다.

## Superpowers와 OMC: 경쟁이 아니라 다른 층

두 플러그인을 같은 카테고리로 묶기 쉽지만, 실제로는 **다른 층위**를 담당합니다.

| | Superpowers | OMC |
|---|---|---|
| 질문 | 에이전트가 **어떤 절차**로 일하는가 | 에이전트들을 **어떻게 편성**하는가 |
| 단위 | 스킬(절차 규율) | 모드(편성 패턴) + 에이전트 로스터 |
| 강제 방식 | 행동 전 스킬 호출 규율 | 라우팅 + 검증 루프 + 메모리 승계 |
| 비유 | 개인의 업무 규율 | 팀의 조직도와 업무 프로세스 |

프롬프트 하네스가 개인기라면, 오케스트레이션 레이어는 팀 전술입니다. 결국 방향은 하나로 수렴합니다 — **LLM의 원시 능력을 조직적 규율로 감싸, 결과의 분산을 줄이는 것.**

## 남은 생각

OMC의 철학 중 가장 급진적인 건 "Claude Code를 배우지 말고 OMC를 쓰라"는 선언입니다. 저는 절반만 동의합니다. 추상화가 잘 작동할 때 이 말은 옳지만, 오케스트레이션이 꼬였을 때 결국 열어봐야 하는 건 그 아래층이기 때문입니다. 다만 방향성 자체는 분명해 보입니다 — 에이전트 도구의 경쟁은 이제 모델 성능이 아니라, **그 위에 어떤 편성·검증·메모리 레이어를 쌓았는가**의 싸움으로 옮겨가고 있습니다.

---

**참고 자료**
- [oh-my-claudecode GitHub (Yeachan-Heo)](https://github.com/Yeachan-Heo/oh-my-claudecode)
- [OMC REFERENCE 문서](https://github.com/Yeachan-Heo/oh-my-claudecode/blob/main/docs/REFERENCE.md)
- [oh-my-claudecode — Teams-First Multi-Agent Orchestration 리뷰](https://ice-ice-bear.github.io/posts/2026-03-20-oh-my-claudecode/)
- [Oh My Claude (omc): A Multi-Agent Orchestration Tool for Claude Code](https://cmaven.github.io/en/claude/oh-my-claude-omc/)
