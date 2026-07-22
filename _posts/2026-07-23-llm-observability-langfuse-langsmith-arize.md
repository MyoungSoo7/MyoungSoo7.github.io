---
layout: post
title: "팀이 Claude Code·Codex를 잘 쓰고 있나? — LLM 관측 3대장 Langfuse·LangSmith·Arize"
date: 2026-07-23 08:15:00 +0900
categories: [AI, Observability]
tags: [Langfuse, LangSmith, ArizePhoenix, OpenTelemetry, ClaudeCode, Codex, LLMObservability, Monitoring]
---

# "느낌"으로는 팀을 관리할 수 없다

![팀장 대화 — 우리 팀원들 Claude Code 또는 Codex 잘 쓰고 있어? 그럼 모니터링 시스템(Langfuse, LangSmith, Arize AI) 대시보드를 만들어서 관리하자](/assets/images/llm-observability-langfuse-langsmith-arize.jpg)

팀이 Claude Code나 Codex를 도입하면 곧 이 질문이 온다: **"그래서, 잘 쓰고 있어?"** 토큰을 얼마나 태우는지, 비용이 어디로 새는지, 어떤 프롬프트가 반복 실패하는지 — 이걸 *느낌*이 아니라 *지표*로 봐야 관리가 된다. 그 지표를 만들어 주는 것이 **LLM 관측(observability) 플랫폼**이고, 대표 주자가 위 그림의 셋 — **Langfuse · LangSmith · Arize AI(Phoenix)** 다.

이 글은 세 시스템을 공식 자료 기준으로 정확히 소개하고, 그것들이 Claude Code·Codex와 실제로 어디서 맞물리는지를 정리한다.

---

## 1. Langfuse — 오픈소스 LLM 엔지니어링 플랫폼

Langfuse 공식 문서는 스스로를 이렇게 규정한다 — *"팀이 협업으로 LLM 애플리케이션을 디버그·분석·반복 개선하도록 돕는 **오픈소스** AI 엔지니어링 플랫폼."*

핵심 기능:
- **관측·트레이싱** — LLM 호출·멀티턴 대화·검색(retrieval)·임베딩·에이전트 워크플로를 네이티브 SDK(Python/JS), 100+ 프레임워크 통합, **OpenTelemetry**, LLM 게이트웨이로 추적
- **프롬프트 관리** — 버전 관리, 협업 편집, 라벨 기반 배포, 플레이그라운드 테스트
- **평가(Eval)** — LLM-as-a-judge, 코드 평가자, 사용자 피드백, 수동 주석, 데이터셋·실험
- **모니터링** — 사용자별 비용·지연 추적, 품질 지표 대시보드

결정적 강점 둘: **완전 오픈소스 + 셀프호스팅**("open, self-hostable, and extensible"), 그리고 **"OpenTelemetry 기반으로 호환성을 높이고 벤더 락인을 줄인다."** 데이터 주권과 자체 인프라를 중시하는 팀(예: 온프렘 홈랩)에 특히 잘 맞는다.

## 2. LangSmith — LangChain이 만든 관측·평가 플랫폼

LangSmith 공식 문서의 한 줄: *"개별 트레이스부터 프로덕션 전반의 성능 지표까지, LLM 애플리케이션에 대한 **완전한 가시성**."*

핵심 기능:
- **트레이싱·계측** — 개별 트레이스 캡처·분석
- **모니터링·대시보드** — *"대시보드를 만들고 알림을 설정해 품질을 추적하고 문제를 조기에 포착"*
- **성능 분석** — UI/API로 트레이스 필터·내보내기·비교
- **자동화** — 규칙·웹훅·온라인 평가
- **이슈 감지 엔진** — 트레이스에서 반복 문제를 자동 진단

오해 주의: 이름은 LangChain 계열이지만 **프레임워크 독립적**이다. 공식 문서가 명시하듯 OpenAI, **Anthropic**, CrewAI, Vercel AI SDK, Pydantic AI 등 "여러 프레임워크·프로바이더와 동작"하며 LangChain 없이도 쓸 수 있다. 배포는 **클라우드(smith.langchain.com)·하이브리드·셀프호스팅**을 지원한다. 평가·프롬프트 엔지니어링까지 한 제품에서 묶고 싶은 팀에 강점이 있다.

## 3. Arize AI Phoenix — OpenInference 기반 오픈소스 관측

Arize Phoenix는 *Arize AI와 커뮤니티가 만든 **오픈소스** AI 관측 플랫폼*이다. 네 축으로 구성된다:
- **트레이싱** — 모델 호출·검색·도구 사용·커스텀 로직을 캡처해 병목·동작 디버깅
- **평가** — LLM 기반 평가자·코드 검사·사람 라벨로 출력 품질 측정
- **프롬프트 엔지니어링** — 실제 예시로 프롬프트를 버전·테스트·재생
- **데이터셋·실험** — 같은 입력으로 변경을 체계적으로 비교

기술 토대가 특징적이다 — *"**OpenTelemetry** 위에 구축되고 **OpenInference** 계측으로 구동"* 되며 LangChain·LlamaIndex·DSPy를 지원하고 Python·TypeScript·Java를 커버한다. 배포는 클라우드와 셀프호스팅(Docker·Kubernetes·원하는 클라우드) 둘 다. Phoenix는 오픈소스 축이고, 상용 **Arize AX**는 엔터프라이즈 축이다(둘의 세부 차이는 공식 문서가 이 페이지에서 직접 대조하지 않아 여기선 단정하지 않는다).

---

## 세 시스템 비교

| 항목 | Langfuse | LangSmith | Arize Phoenix |
|---|---|---|---|
| 오픈소스 | ✅ 완전 OSS | 코어는 상용(셀프호스팅 옵션) | ✅ Phoenix는 OSS |
| 초점 | 관측+프롬프트+평가 균형 | 관측+평가+프롬프트 통합 | 관측+평가+실험(OpenInference) |
| OpenTelemetry | ✅ OTel 기반 | 프레임워크 독립(다중 프로바이더) | ✅ OTel + OpenInference |
| 셀프호스팅 | ✅ 강점 | ✅ 지원 | ✅ Docker/K8s |
| 잘 맞는 팀 | 데이터 주권·온프렘 | 평가까지 한 제품에서 | 오픈 계측 표준 선호 |

> 공통점: 셋 다 "LLM 호출의 트레이스 + 평가 + 비용/지연 대시보드"를 제공한다. 차이는 오픈소스 정도, 계측 표준(OTel/OpenInference), 그리고 평가·실험 기능의 무게중심이다.

---

## 그런데 Claude Code·Codex와는 어떻게 붙나 — OpenTelemetry라는 공용어

여기서 중요한 사실 하나. **Claude Code는 자체적으로 OpenTelemetry 텔레메트리를 내보낸다.** 공식 문서 기준으로 `CLAUDE_CODE_ENABLE_TELEMETRY=1` 하나로 켜지며, **메트릭·이벤트(로그)·트레이스(beta)** 를 OTLP·Prometheus로 export 한다. 대표 메트릭:

| 메트릭 | 뜻 |
|---|---|
| `claude_code.session.count` | 시작된 CLI 세션 수 |
| `claude_code.cost.usage` | 세션 비용(USD) |
| `claude_code.token.usage` | 사용 토큰 수 |
| `claude_code.lines_of_code.count` | 수정된 코드 라인 수 |
| `claude_code.commit.count` / `pull_request.count` | 생성된 커밋/PR 수 |
| `claude_code.active_time.total` | 총 활동 시간(s) |

이벤트로는 `user_prompt`·`assistant_response`·`api_request`/`api_error`·`tool_result`/`tool_decision`·`mcp_server_connection` 등이 나오고, 모든 텔레메트리에 `session.id`·`user.id`·`organization.id` 속성이 붙는다. (나는 이미 이 네이티브 OTel을 홈랩 OTLP 엔드포인트로 보내 팀/개인 사용량 대시보드를 굴리고 있다.)

**두 층을 구분하는 게 핵심이다:**

1. **하네스 사용량 층** — Claude Code의 네이티브 OTel 메트릭/이벤트. "누가·얼마나·얼마 비용으로 썼나"를 팀 단위로 본다. 팀장이 처음 궁금해한 바로 그 질문의 답이 여기 있다.
2. **LLM 호출 트레이스 층** — Langfuse·LangSmith·Phoenix가 빛나는 곳. 개별 프롬프트→응답의 트리, 평가 점수, 실패 패턴을 *호출 단위*로 파고든다.

두 층이 만나는 접점이 **OpenTelemetry**다. Langfuse와 Phoenix가 OTel/OpenInference 네이티브이므로, OTel로 흐르는 신호를 같은 백엔드 계보에서 다룰 수 있다. 다만 **정직한 단서**: Claude Code의 네이티브 export는 *사용량 메트릭·이벤트* 중심이고, 세 플랫폼의 진가인 *호출 단위 트레이스/평가*는 보통 LLM API 호출을 계측(instrument)하는 지점에서 나온다. "Claude Code를 Langfuse에 꽂으면 자동으로 풀 트레이스가 뜬다"는 식의 턴키 통합을 공식 문서로 확인하진 못했으니, 그렇게까지 단정하지 않는다. Codex 역시 이 글에서 네이티브 OTel 여부를 단정하지 않는다(그림의 맥락상 이름만 등장).

---

## 그래서 무엇을 골라야 하나

- **팀 사용량·비용 관리가 목적** → 먼저 **Claude Code 네이티브 OTel**을 켜서 Prometheus/Grafana 대시보드부터. 도구를 더 사기 전에 이미 공짜로 얻는 것이 많다.
- **데이터 주권·온프렘·오픈소스** → **Langfuse**(셀프호스팅 성숙, OTel 기반).
- **평가·프롬프트 엔지니어링까지 한 제품에서** → **LangSmith**(프레임워크 독립, Anthropic 포함 다중 프로바이더).
- **오픈 계측 표준(OpenInference)과 실험 워크플로 선호** → **Arize Phoenix**.

결국 팀장의 질문 — "잘 쓰고 있어?" — 에 답하는 순서는 이렇다: **네이티브 텔레메트리로 사용량을 먼저 계량하고, 품질·실패를 파고들 때 관측 플랫폼을 얹는다.** 느낌을 지표로 바꾸는 것, 그것이 관측의 전부다.

---

## 출처

- 첨부 이미지: 사용자 제공(팀 모니터링 시나리오).
- Langfuse (공식): <https://langfuse.com/docs> — "open-source AI engineering platform", OTel 기반·셀프호스팅.
- LangSmith (공식): <https://docs.langchain.com/langsmith> — "full visibility … traces to production-wide metrics", 프레임워크 독립.
- Arize Phoenix (공식): <https://arize.com/docs/phoenix> — OpenTelemetry + OpenInference 기반 오픈소스 관측.
- Claude Code 모니터링 (공식): <https://code.claude.com/docs/en/monitoring-usage> — 네이티브 OTel 메트릭·이벤트·트레이스(beta), `CLAUDE_CODE_ENABLE_TELEMETRY`.

> 참고: 각 제품의 세부 기능·가격·통합은 버전에 따라 바뀔 수 있다. Claude Code↔관측 플랫폼의 트레이스 수준 통합은 계측 방식에 따라 다르며, 본문은 공식 문서로 확인된 범위(네이티브 OTel export + 각 플랫폼의 OTel 수용)만 단정했다.
