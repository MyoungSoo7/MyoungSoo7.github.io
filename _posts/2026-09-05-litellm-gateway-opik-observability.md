---
layout: post
title: "intelligence.lemuel.co.kr과 Opik으로 보는 LLM Gateway·Agent 관측성"
date: 2026-09-05 05:50:00 +0900
categories: [AI, LLMOps, Infrastructure]
tags: [LiteLLM, Opik, LLM Gateway, 관측성, 비용관리, Agent]
---

AI 서비스를 운영할 때는 모델을 호출하는 것만으로 충분하지 않다. 어떤 애플리케이션이 어떤 모델과 Provider를 사용했는지, 비용과 토큰은 얼마인지, 요청이 실패했는지, 대화가 얼마나 오래 이어졌는지, 최종 품질은 어떠했는지를 함께 관측해야 한다.

이 글에서는 `intelligence.lemuel.co.kr`에 연결된 LiteLLM Gateway와 Opik 대시보드를 함께 살펴본다. LiteLLM은 LLM 호출의 진입점과 비용·접근 제어를 담당하고, Opik은 Agent 실행 과정과 대화 품질을 관측하는 계층으로 볼 수 있다.

## 1. `intelligence.lemuel.co.kr`은 무엇인가

`intelligence.lemuel.co.kr`은 LiteLLM Proxy Server를 외부에서 접근하는 Gateway 주소다. 현재 공개 접속은 Cloudflare Access 이메일 OTP 인증 뒤에 제공된다.[1] 즉 이 주소는 특정 모델 하나의 홈페이지가 아니라, 여러 LLM Provider를 하나의 API 형식과 운영 정책으로 묶는 관문이다.

```text
Claude·OpenAI·Gemini·기타 모델 클라이언트
                  ↓
       intelligence.lemuel.co.kr
              LiteLLM Gateway
        ├─ 인증·가상 키
        ├─ 모델 라우팅
        ├─ 재시도·fallback
        ├─ 비용·토큰 집계
        └─ 로그·사용량 관리
                  ↓
       Provider별 실제 LLM API
```

LiteLLM 공식 문서는 Proxy Server가 중앙 API Gateway로서 인증·인가, 프로젝트·사용자별 비용 추적, 가상 키, 모델 접근 제어, 로깅과 관리 UI를 제공한다고 설명한다.[2] 또한 여러 Provider의 API를 OpenAI 호환 입력·출력 형식으로 통합할 수 있다.[2]

## 2. LiteLLM의 핵심 기능

### 통합 API 형식

애플리케이션은 Provider마다 다른 SDK와 응답 형식을 직접 처리하는 대신 LiteLLM Gateway를 공통 endpoint로 사용할 수 있다.

```text
애플리케이션
  → OpenAI 호환 요청
  → LiteLLM
  → 실제 Provider API
  → 정규화된 응답
```

이 구조는 모델을 OpenAI에서 Gemini나 다른 Provider로 바꿀 때 애플리케이션 코드를 덜 수정하게 해 준다. 다만 모델별 기능·토큰 계산·추론 옵션이 완전히 동일해지는 것은 아니므로, 모델 교체 후에는 품질·비용·지연을 다시 검증해야 한다.

### 라우팅·재시도·Fallback

LiteLLM Router는 여러 deployment 사이에서 재시도와 fallback을 구성할 수 있다.[2] 특정 Provider의 일시 오류나 rate limit에 대응할 수 있지만, 재시도는 비용과 지연을 늘릴 수 있다. 따라서 `retry_count`, fallback 발생 여부, 최종 성공 여부를 함께 관측해야 한다.

### Virtual Key와 권한 분리

Virtual Key는 사용자·팀·애플리케이션별로 모델 접근과 사용량을 분리하는 논리적 키다. LiteLLM 문서는 키별·사용자별·팀별 spend 조회와 모델 목록·예산·rate limit 설정을 지원한다고 설명한다.[3]

```text
Hermes key
  → Hermes 작업 비용

bot key
  → Telegram 봇 비용

실험 key
  → 모델 비교·평가 비용
```

키를 분리하면 비용을 누가 발생시켰는지와 어떤 모델을 사용했는지 추적하기 쉽다. 키 자체는 비밀번호처럼 취급해야 하며, 화면 캡처·Git·로그·블로그에 노출해서는 안 된다.

### 비용·토큰·성공·실패 집계

LiteLLM은 모델별 가격 정보와 응답 토큰을 이용해 spend를 계산하고, 키·사용자·팀 단위로 사용량을 추적한다.[4] 공식 문서는 응답 헤더의 계산 비용, spend log, 입력·출력·전체 토큰, 요청 성공·실패를 확인하는 방법을 제시한다.[4]

비용은 Provider 청구서와 항상 동일하다고 가정하면 안 된다. 가격표 버전, 캐시 토큰, 모델 alias, 시간 범위, 실패 요청과 재시도 집계가 차이를 만들 수 있으므로 운영 비용은 Gateway 집계와 Provider 청구 데이터를 대조해야 한다.

## 3. 첫 번째 그림: LiteLLM 사용량·비용 대시보드

![LiteLLM Gateway 사용량 분석 대시보드](/assets/images/litellm-usage-dashboard.jpg)

첫 번째 그림은 LiteLLM의 API 사용량과 지출을 보여주는 화면이다. 화면의 주요 영역은 다음과 같다.

### Top Virtual Keys

화면에는 `hermes`, `hermes-imported`, `test-first-key` 등의 Key Alias가 표시되고, 키별 Spend가 비교된다. 판독된 화면 기준으로 `hermes`가 약 `$0.12`, `hermes-imported`가 약 `$0.02`를 사용한 것으로 보인다.

이 패널은 “어떤 모델이 비싼가”보다 먼저 “어떤 호출 주체가 비용을 만들었는가”를 답한다. 다만 화면에 보이는 키 ID는 일부가 마스킹되어 있고, 이 글에서는 원문 키를 기록하지 않는다.

### Top Public Model Names

모델별 지출 막대에는 다음 모델들이 보인다.

```text
gpt-4o
gpt-4.1
gemini-2.5-flash
gemini-3-flash-preview
gpt-4.1-mini
```

화면상 `gpt-4o`의 비용 막대가 가장 크고, 이어 `gpt-4.1`, `gemini-2.5-flash`, `gemini-3-flash-preview` 순으로 보인다. 이 차트는 호출 횟수 자체가 아니라 화면에 집계된 spend 규모를 비교하는 영역이다.

### Spend by Provider

하단에는 Provider별 지출을 합산한 도넛 차트와 표가 있다. 화면 판독 기준 총 지출은 `$0.14`이며, Provider는 `gemini`, `nous`, `openai`로 나뉜다. 표시된 표에는 성공 요청 합계 44건, 실패 0건, 총 토큰 약 228,603개가 보인다.

화면에 표시된 세부 값은 다음처럼 읽힌다.

```text
gemini:
  성공 19건
  토큰 약 144,800

a Nous:
  성공 2건
  토큰 약 2,600

openai:
  성공 23건
  토큰 약 81,203

실패:
  각 Provider 0건으로 표시
```

여기서 `failed = 0`은 요청 계층에서 기록된 실패가 없다는 뜻이지, 업무 결과가 모두 정확하거나 품질 문제가 없다는 뜻은 아니다. 성공한 API 응답도 잘못된 답변, 부적절한 도구 호출, 검증 누락을 포함할 수 있다.

## 4. 두 번째 그림: Opik Quality & conversations

![Opik Quality & conversations 대시보드](/assets/images/opik-quality-conversations.jpg)

두 번째 그림은 Opik의 `Quality & conversations` 대시보드다. Opik은 LLM 애플리케이션의 LLM 호출·도구 호출·Agent 단계를 Trace로 기록하고, 품질·지연·비용·오류를 평가하는 플랫폼이다.[6]

화면은 네 패널로 구성된다.

### Thread volume

`08/07`부터 `09/04`까지의 대화 스레드 수를 막대그래프로 표시한다. 대부분의 기간에는 활동이 거의 없고, `09/02`에 소량의 스레드가 나타나며 `09/04`에 20건을 넘는 급증이 관측된다.

이는 해당 날짜에 요청이 집중되었음을 보여주는 관측값이다. 그러나 이것만으로 실제 사용자 트래픽 급증, 장애, 또는 특정 봇의 작업이라고 단정할 수는 없다. 프로젝트·Trace·source metadata를 함께 확인해야 한다.

### Thread duration

`thread_duration.p50`, `p90`, `p99` 세 백분위수의 지속시간을 보여준다. 화면에서는 `09/04`에 세 지표가 함께 크게 상승하며, p99는 약 1시간 6분 40초에 가까운 눈금까지 올라간다.

해석 가능한 가설은 다음과 같다.

```text
긴 Agent 세션
장시간 백그라운드 작업
여러 요청이 한 스레드에 누적
도구 호출 또는 재시도 지연
테스트·데모 데이터의 집중 유입
```

다만 p99가 높다고 해서 모든 대화가 한 시간 이상 걸렸다는 의미는 아니다. p99는 상위 1%의 긴 실행을 나타내므로 p50·p90과 함께 분포를 읽어야 한다.

### Trace feedback scores와 Thread feedback scores

두 피드백 패널은 현재 빈 상태다. Opik 화면은 SDK·UI·온라인 scoring rule을 통해 Trace 또는 Thread에 점수를 추가해야 품질 추세를 볼 수 있다고 안내한다.[6]

따라서 현재 화면에서 확인되는 상태는 다음과 같다.

```text
볼륨:
  관측됨

지속시간:
  관측됨

Trace 품질 점수:
  미수집

Thread 품질 점수:
  미수집
```

이것은 LiteLLM이 API 사용량을 기록하는 것과 대조된다. LiteLLM은 “누가 어떤 모델을 얼마나 호출했는가”에 강하고, Opik은 “그 호출과 Agent 실행이 어떤 흐름으로 결과를 만들었고 품질이 어땠는가”에 강하다.

## 5. LiteLLM과 Opik의 관계

두 시스템은 경쟁하는 도구라기보다 서로 다른 관측 계층이다.

```text
사용자
  ↓
Hermes·Claude·RAG·Agent
  ↓ OpenAI 호환 API
LiteLLM Gateway
  ├─ 키·권한
  ├─ 모델 라우팅
  ├─ Provider 호출
  ├─ 비용·토큰
  └─ 성공·실패
          ↓
        Opik 계측
  ├─ Trace·Span
  ├─ Thread volume
  ├─ Thread duration
  ├─ feedback score
  └─ 품질 평가
```

이상적인 연동에서는 LiteLLM의 `request_id`, key alias, model, provider, cost를 Opik Trace의 metadata와 연결한다. 그러면 한 번의 작업에 대해 다음 질문에 함께 답할 수 있다.

```text
어떤 Agent가 요청했는가?
어떤 Virtual Key를 사용했는가?
어떤 모델과 Provider가 실제로 응답했는가?
Fallback이 발생했는가?
비용과 토큰은 얼마인가?
도구 호출과 대화는 얼마나 오래 걸렸는가?
최종 답변 품질은 기준을 통과했는가?
```

단순히 LiteLLM과 Opik URL을 모두 알고 있는 것만으로는 연동이 완료되지 않는다. 공통 correlation ID와 실제 Trace 수집을 검증해야 한다.

## 6. 관측 항목별 역할 분담

| 관측 질문 | LiteLLM | Opik |
| --- | --- | --- |
| 어떤 모델을 호출했는가 | 강함 | Trace metadata로 보완 |
| 어느 Provider 비용인가 | 강함 | 보완 가능 |
| Virtual Key별 사용량 | 강함 | 보완 가능 |
| 재시도·Fallback | Gateway 로그 중심 | Span metadata로 보완 |
| Agent 단계 흐름 | 제한적 | 강함 |
| Tool 호출 순서 | 애플리케이션 의존 | 강함 |
| 대화 지속시간 | 제한적 | Thread duration |
| 사용자·자동 품질 점수 | 별도 구성 | 강함 |
| Provider 청구 대조 | 원천 집계 | 직접 기능 아님 |

LiteLLM은 **경제·접근·라우팅 관측**의 중심이고, Opik은 **실행·품질·대화 관측**의 중심이다.

## 7. 운영에서 주의할 해석

### 성공 요청 0건 실패 ≠ 품질 성공

LiteLLM 화면에서 Failed가 0이어도 다음은 여전히 가능하다.

```text
잘못된 답변
근거 없는 답변
도구 결과 누락
검증 단계 생략
너무 긴 지연
불필요한 토큰 사용
```

### 비용이 낮음 ≠ 효율이 좋음

저렴한 모델이 항상 좋은 선택은 아니다. 재시도·후처리·사용자 재질문까지 포함한 전체 작업 비용과 성공률을 봐야 한다.

### 긴 Thread duration ≠ 서버 장애

긴 스레드는 실제 장애일 수도 있지만, 장시간 정상 작업·백그라운드 대기·사용자 대화 누적일 수도 있다. Trace 상세와 프로세스·Gateway 로그를 함께 대조해야 한다.

### Opik 프로젝트가 있음 ≠ 모든 Agent가 연결됨

프로젝트와 기존 Trace가 보이는 것은 일부 데이터가 수집되었다는 증거다. Hermes·Telegram 봇·원격 worker 전체가 포함됐다는 증거는 아니다.

## 8. 권장 연동 검증 절차

```text
1. 테스트용 LiteLLM Virtual Key 준비
2. 짧은 테스트 요청 1건 생성
3. LiteLLM에서 model·provider·cost·tokens 확인
4. 같은 request/correlation ID로 Opik Trace 확인
5. LLM Span과 Tool Span 순서 대조
6. 실패·재시도·fallback을 의도적으로 테스트
7. 실제 Provider 청구·Gateway spend와 대조
8. 개인정보·Secret 원문이 수집되지 않았는지 확인
9. 운영 Project로 제한적 확대
```

첫 도입 단계에서는 원문 프롬프트와 도구 결과 전체를 보내기보다 다음 metadata부터 수집하는 편이 안전하다.

```text
run_id
agent_id
session_id
model
provider
virtual_key_alias
request_id
latency_ms
input/output/total tokens
spend
error_type
verification_status
```

## 결론

`intelligence.lemuel.co.kr`의 LiteLLM Gateway는 여러 LLM Provider를 통합하고, Virtual Key·라우팅·Fallback·비용·토큰·성공·실패를 관리하는 **LLM 진입점**이다. Opik은 그 뒤에서 LLM 호출과 Agent 실행 단계를 Trace·Thread로 관측하고 품질 피드백을 축적하는 **LLMOps 관측 계층**이다.

두 그림은 이 구분을 보여준다.

```text
LiteLLM 화면:
  누가 어떤 모델·Provider를 얼마나 사용했고 얼마를 썼는가

Opik 화면:
  대화가 얼마나 많고 오래 지속됐으며 품질 점수가 있는가
```

현재 화면 기준으로 비용·토큰·사용량과 Thread volume·duration은 일부 관측되고 있지만, Trace/Thread feedback score는 아직 비어 있다. 따라서 다음 단계는 단순히 대시보드를 더 만드는 것이 아니라, LiteLLM의 request metadata와 Opik의 Trace를 동일한 작업 ID로 연결하고, 실제 업무 성공·품질 점수를 추가하는 것이다.

## References

[1] [intelligence.lemuel.co.kr — LiteLLM Gateway](https://intelligence.lemuel.co.kr/)

[2] [LiteLLM 공식 문서 — Getting Started](https://docs.litellm.ai/)

[3] [LiteLLM 공식 문서 — Virtual Keys](https://docs.litellm.ai/docs/proxy/virtual_keys)

[4] [LiteLLM 공식 문서 — Spend Tracking](https://docs.litellm.ai/docs/proxy/cost_tracking)

[5] [Opik — Lemuel instance](https://opik.lemuel.co.kr/)

[6] [Opik 공식 문서 — LLM Observability & Optimization](https://www.comet.com/docs/opik/)

*LiteLLM과 Opik 화면의 수치는 제공된 스크린샷을 판독해 기록한 예시 관측값이다. 화면에 표시된 집계가 전체 운영 시스템과 Provider 청구액을 대표한다고 단정하지 않으며, 첫 번째 LiteLLM 화면의 세부 값은 이미지 해상도·표시 범위에 따른 근사값이다. 실제 운영 판단에는 원천 로그·request ID·Provider 청구 데이터·개별 Trace를 함께 대조해야 한다.*
