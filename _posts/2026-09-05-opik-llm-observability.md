---
layout: post
title: "Opik으로 보는 LLM·Agent 관측성: 두 화면으로 이해하는 Trace와 품질 운영"
date: 2026-09-05 05:46:00 +0900
categories: [AI, LLMOps, Observability]
tags: [Opik, LLM, Agent, Trace, LLMOps, 관측성]
---

AI Agent가 답변을 생성했다는 사실만으로는 운영 품질을 판단하기 어렵다. 어떤 모델을 호출했는지, 도구를 몇 번 사용했는지, 얼마나 오래 걸렸는지, 토큰과 비용이 얼마나 들었는지, 오류가 어느 단계에서 발생했는지를 함께 봐야 한다. `https://opik.lemuel.co.kr/`은 이런 실행 흐름을 기록하고 분석하기 위한 **Opik 기반 LLM 관측성 플랫폼**이다.

이 글은 두 개의 Opik Projects 화면을 중심으로 Opik의 용도와 작동 구조를 설명한다. 첫 번째 그림은 사용자가 이번에 제공한 화면이고, 두 번째 그림은 Projects 대시보드에서 프로젝트별 지표와 오류를 보여주는 화면이다.

## 1. 첫 번째 그림: Opik은 무엇을 관측하는가

![Opik 관측성 화면 — 첫 번째 제공 이미지](/assets/images/opik-observability-overview.jpg)

첫 번째 화면의 세부 텍스트는 이미지 판독 제약으로 모두 확정하지 못했다. 따라서 이 그림에 특정 수치나 메뉴명을 근거 없이 붙이지 않는다. 다만 두 그림이 공통으로 보여주는 Opik의 핵심은 **AI 애플리케이션 실행을 프로젝트 단위로 묶고, Trace와 품질·비용 지표를 함께 보는 것**이다.

Opik 공식 문서는 챗봇, RAG 파이프라인, 다단계 Agent의 동작을 이해하고 개선하기 위한 오픈소스 플랫폼으로 Opik을 설명한다. LLM 호출, 도구 호출, Agent 단계를 기록하고, 운영 환경에서 피드백 점수·지연시간·비용·오류율을 모니터링할 수 있다.[1]

## 2. 두 번째 그림: Projects 대시보드 읽기

![Opik Projects 대시보드 — 프로젝트별 Trace·비용·오류](/assets/images/opik-projects-errors.jpg)

두 번째 화면은 `Personal / Projects` 영역의 프로젝트 목록이다. 화면에는 `memory-qa`, `Opik Demo Agent Obs...`, `Default Project` 세 프로젝트가 표시되어 있다. 테이블의 주요 열은 프로젝트 이름, 최근 갱신일, Trace count, Avg duration, Total cost, Errors, Avg total tokens, Avg feedback scores다.

화면에서 확인되는 예시는 다음과 같다.

```text
memory-qa:
  14 traces
  평균 1.8초
  비용 < $0.01
  평균 총 토큰 1379.89

Opik Demo Agent Obs...:
  116 traces
  평균 4.3초
  비용 $0.01
  2 errors
  평균 총 토큰 667.51

Default Project:
  Trace 데이터 없음
```

이 숫자는 해당 화면에 표시된 프로젝트 예시의 관측값이지, 현재 운영 중인 Hermes·Claude 봇 전체의 상태를 의미하지 않는다. 특히 `Opik Demo Agent Obs...`의 `2 errors`는 그 프로젝트에 기록된 오류가 두 건 있다는 뜻이며, 오류의 원인과 심각도는 개별 Trace를 열어야 판단할 수 있다.

## 3. Trace는 Agent 작업의 영수증이다

사용자 질문 하나가 여러 모델·도구 호출로 이어질 때 전체 실행을 하나의 Trace로 묶을 수 있다.

```text
Trace: "Kubernetes 장애 분석"
  ├─ Span: 요청 분류
  ├─ Span: 클러스터 상태 조회
  ├─ Span: 로그 수집
  ├─ Span: LLM 분석
  ├─ Span: 출처·근거 검증
  └─ Span: 최종 응답 생성
```

Opik 공식 문서는 모든 LLM 호출, 도구 호출, Agent 단계를 기록해 최종 출력으로 이어진 전체 경로를 검사할 수 있다고 설명한다.[1]

Trace와 Span을 분리하면 “답이 틀렸다”를 더 구체적인 질문으로 바꿀 수 있다.

```text
모델이 잘못 판단했는가?
검색 결과가 부족했는가?
도구가 오류를 반환했는가?
재시도가 비용을 키웠는가?
Context가 잘못 주입됐는가?
최종 합성 단계에서 근거가 누락됐는가?
```

이것이 일반 애플리케이션 로그와 Agent 관측성의 차이다. 단순히 예외 문자열을 남기는 것이 아니라, **한 응답이 만들어진 의사결정 경로와 비용 구조**를 함께 남긴다.

## 4. Projects는 관측 범위를 나누는 경계다

Projects는 서로 다른 애플리케이션이나 실험을 분리하는 논리적 경계다. 예를 들어 다음처럼 나눌 수 있다.

```text
hermes-command-center
telegram-bots
openviking-memory
k8s-operations
blog-publishing
rag-evaluation
```

프로젝트를 분리하면 다음을 비교하기 쉬워진다.

- Agent별 평균 응답 시간
- 모델별 토큰·비용
- 도구 오류율
- 사용자 피드백 점수
- 프롬프트·검색 설정 변경 전후 품질

반대로 모든 실행을 `Default Project` 하나에 넣으면 서비스별 병목과 오류가 섞여 원인 분석이 어려워진다. 프로젝트 이름만 잘 나누는 것으로 관측이 완성되는 것은 아니지만, 운영 책임과 비용 범위를 나누는 첫 단계가 된다.

## 5. Opik 지표의 의미

### Trace count

기록된 실행 흐름 수다. 요청량과 같을 수 있지만, SDK 설정·샘플링·전송 실패가 있으면 실제 사용자 요청 수와 달라질 수 있다.

### Avg duration

Trace의 평균 처리 시간이다. 평균만 보면 긴 꼬리 지연을 놓칠 수 있으므로 p95·p99 또는 최대 지연도 함께 보는 것이 좋다.

### Total cost

기록된 모델 호출 비용의 합이다. 모델 가격표, 토큰 집계, 누락된 호출, 무료·내부 모델 여부에 따라 실제 청구액과 다를 수 있다. 따라서 비용 숫자는 청구 시스템과 대조해야 한다.

### Avg total tokens

Trace당 평균 입력·출력 등 집계 토큰이다. 토큰이 많다고 반드시 품질이 좋은 것은 아니며, 불필요한 Context·반복 호출·긴 도구 결과가 비용과 지연을 키울 수 있다.

### Errors

실행 중 오류로 기록된 Trace 또는 단계의 수다. 오류 수가 0이어도 비즈니스 성공을 보장하지 않는다. 올바른 답변인지, 필수 검증을 했는지, 게시·전달이 완료됐는지를 별도 확인해야 한다.

### Feedback scores

사용자 평가나 자동 평가 결과다. 평가 기준·샘플·판정 모델을 함께 기록하지 않으면 숫자만으로 품질을 비교할 수 없다.

## 6. Opik의 작동 구조

일반적인 연결은 다음과 같다.

```text
사용자 요청
  ↓
Agent 애플리케이션
  ├─ LLM 호출
  ├─ Tool 호출
  ├─ 검색/RAG
  └─ 외부 API
          ↓
     Opik SDK 또는 OTEL 계측
          ↓
     Trace·Span·Metric 수집
          ↓
     Opik Project 저장
          ↓
     Projects / Dashboards / 평가 화면
```

Opik은 SDK·통합 계층을 통해 다양한 모델·프레임워크에서 Trace를 기록할 수 있고, MCP 서버를 사용하면 Claude Code·Cursor·VS Code Copilot·Codex·opencode 같은 개발 도구에서 Trace를 읽고 평가·실험할 수 있다고 공식 문서가 설명한다.[1]

이 구조에서 반드시 구분해야 할 것은 **계측 설정이 존재하는 것**과 **실제 Trace가 도착하는 것**이다. 환경변수나 OTEL endpoint가 설정되어 있어도 Collector가 꺼져 있거나 프로젝트 인증이 틀리면 화면에는 새로운 실행이 나타나지 않을 수 있다.

## 7. 우리 Agent 구조에 적용하는 방법

현재 Hermes가 중앙 지휘자이고 여러 봇·원격 worker가 실행을 맡는 구조라면 다음과 같이 설계할 수 있다.

```text
Hermes Command Center:
  계획·권한·최종 검증 Trace

Telegram bots:
  bot별 또는 기능별 프로젝트

OpenViking:
  Context 검색 Span
  사용한 memory/resource 식별자

Kubernetes worker:
  조회 명령·응답 시간·판정 결과

GitHub/Ghost 게시:
  초안·검증·commit·Pages·URL 확인 단계
```

권장 공통 필드는 다음과 같다.

```text
run_id
agent_id
session_id
model
provider
tool_name
input_tokens
output_tokens
latency_ms
error_type
verification_status
artifact_id
```

단, 사용자 프롬프트 원문·도구 결과 전체·사진·Secret을 무조건 기록하면 개인정보와 인증정보가 관측 시스템에 복제될 수 있다. 처음에는 원문 대신 해시·길이·분류·결과 상태를 기록하고, 디버깅이 필요한 제한된 Trace에만 마스킹된 콘텐츠를 허용하는 편이 안전하다.

## 8. Opik을 도입할 때의 검증 순서

```text
1. 테스트용 Project 생성
2. 샘플 LLM Trace 1건 발생
3. Trace와 Span이 실제 표시되는지 확인
4. 모델·토큰·지연·오류 필드 확인
5. Tool 호출 Trace 확인
6. 비용 집계와 원장/청구 데이터 대조
7. 평가 점수와 판정 기준 확인
8. 운영 Project로 제한적 확대
```

화면에 프로젝트가 보이는 것만으로는 연결 완료가 아니다. 다음 세 가지를 모두 확인해야 한다.

```text
수집:
  실제 Trace가 들어오는가

정확성:
  모델·토큰·비용·오류 값이 원천 로그와 맞는가

활용:
  Trace를 이용해 품질·속도·비용을 개선했는가
```

## 9. 현재 화면에 대한 사실·해석·미확인

### 확인된 사실

- `opik.lemuel.co.kr`은 Cloudflare Access 로그인 뒤 Opik 화면으로 접근하는 서비스다.
- Projects 화면에는 세 프로젝트와 Trace·duration·cost·tokens·errors 관련 열이 표시된다.
- `Opik Demo Agent Obs...` 프로젝트에는 화면상 `2 errors`가 표시된다.
- Opik 공식 문서는 LLM 호출·도구 호출·Agent 단계 Trace, 평가, 비용·지연·오류 모니터링을 주요 기능으로 설명한다.[1]

### 해석

- Opik은 Hermes·Claude·RAG·Tool 실행을 품질과 비용 관점에서 분석하는 LLMOps 계층으로 사용할 수 있다.
- Projects는 Agent나 실험의 관측 범위와 책임을 분리하는 경계로 쓰는 것이 적합하다.

### 미확인

- 현재 Hermes와 Telegram 봇의 신규 Trace가 이 Opik 인스턴스로 실제 유입되는지
- 화면의 두 오류가 어떤 Span과 원인에 해당하는지
- 모든 모델 호출의 비용 집계가 실제 제공자 청구액과 일치하는지
- 첫 번째 제공 이미지의 세부 지표와 프로젝트가 무엇인지

## 결론

Opik은 단순한 에러 로그 뷰어가 아니다. Agent 실행을 Trace와 Span으로 쪼개어 모델 호출, 도구 사용, 지연, 토큰, 비용, 오류, 피드백을 하나의 실행 기록으로 연결하는 **LLM·Agent 관측성 플랫폼**이다.

```text
무엇을 호출했는가?
왜 그렇게 답했는가?
어디서 느려졌는가?
무엇이 실패했는가?
얼마나 비용이 들었는가?
품질이 실제로 좋아졌는가?
```

이 질문에 답하려면 프로젝트 목록만 보는 것으로 부족하다. 실제 Trace를 발생시키고, 원천 로그와 값을 대조하고, 평가 기준을 고정하며, 개인정보·Secret을 마스킹해야 한다. 우리 구조에서는 Hermes가 지휘·검증을 담당하고 Opik이 실행 증거를 축적하는 형태가 가장 자연스럽다.

## References

[1] [Opik 공식 문서 — Open-Source LLM Observability & Optimization](https://www.comet.com/docs/opik/)

[2] [Opik Architecture and self-hosting information](https://www.comet.com/docs/opik/self-host/overview)

*이 글의 프로젝트 수치와 오류 표시는 제공된 Opik Projects 화면을 읽어 정리한 것이다. 화면에 표시된 프로젝트가 현재 운영 Agent 전체를 대표한다고 해석하지 않으며, 실제 Trace 유입·비용 정확성·첫 번째 이미지의 세부 내용은 별도 검증이 필요하다.*
