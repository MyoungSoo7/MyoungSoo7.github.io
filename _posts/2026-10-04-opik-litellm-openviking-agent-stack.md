---
layout: post
title: "에이전트 스택의 세 층 — OpenViking(기억)·LiteLLM(관문)·Opik(관측)을 한 줄로 엮기"
date: 2026-10-04 20:46:25 +0900
categories: [AI, Infra]
tags: [OpenViking, LiteLLM, Opik, AI에이전트, LLM게이트웨이, 컨텍스트DB, LLM관측]
---

AI 에이전트를 직접 운영하다 보면, 모델 하나 붙이는 것보다 **모델 주변**이 더 일이 된다. 크게 세 가지가 필요하다.

1. **기억** — 에이전트가 무엇을 알고, 무엇을 기억하는가
2. **관문** — LLM 호출이 어디로 가고, 얼마를 쓰고, 막히면 어디로 돌아가는가
3. **관측** — 에이전트가 실제로 무엇을 했고, 잘했는가

이 홈랩에서는 이 세 층을 각각 **OpenViking**, **LiteLLM**, **Opik** 이 맡고 있다. LiteLLM 과 Opik 대시보드는 [이전 글](/2026/09/05/litellm-gateway-opik-observability/)에서 다뤘다. 이 글은 세 도구를 **하나의 흐름으로 엮는 방법**과, 왜 그렇게 엮어야 하는지에 집중한다. 이유는 이 블로그의 [제미나이 청구서 사건](/2026/09/14/gemini-api-bill-root-cause-openviking/)에서 비싸게 배웠다.

## 1. OpenViking — 에이전트의 기억을 파일시스템으로

### 무엇인가

[OpenViking](https://github.com/volcengine/OpenViking) 은 Volcengine 조직이 공개한 오픈소스(AGPLv3) 프로젝트다. README 는 스스로를 *"The Context Database for AI Agents"* 라고 소개한다. 저장소 설명은 *"Unify Agent Memory, Knowledge RAG and Skills"* 다. 에이전트가 아는 모든 것, 즉 지식·기억·기술을 **하나의 파일시스템**으로 다루겠다는 발상이다.

```
viking://resources/...                  # 문서·코드
viking://user/{user_id}/memories/...    # 사용자 선호, 경험
viking://user/{user_id}/skills/...      # 작업 수행 방법
```

에이전트는 이 공간을 `ls`, `tree`, `read`, `grep` 처럼 탐색한다.

### 핵심 아이디어: 3단계 컨텍스트(L0/L1/L2)

README 에 따르면 디렉터리마다 세 층의 요약이 있다.

| 층 | 내용 | 쓰임 |
|---|---|---|
| **L0 (Abstract)** | 한 문장 요약 | 관련 있는지 빠르게 판단 |
| **L1 (Overview)** | 핵심 정보와 사용 시나리오 | 계획 세우기 |
| **L2 (Details)** | 원본 전체 | 필요할 때만 읽기 |

에이전트는 L0 → L1 → L2 순으로 **필요한 만큼만** 깊이 들어간다. 검색도 전체 인덱스가 아니라 디렉터리 단위로 한다(*"Search a directory, not the whole index."*). 컨텍스트 창을 아끼는 설계다.

### 사용법

```bash
uv tool install openviking --upgrade
openviking-server init      # ~/.openviking/ov.conf 생성 (임베딩 모델 + VLM 지정)
openviking-server doctor    # 설정 점검
```

```python
# pip install openviking-sdk
from openviking_sdk import SyncHTTPClient

client = SyncHTTPClient(url="http://127.0.0.1:1933", api_key="your-user-key")
client.initialize()
client.add_resource(path="./notes.md", to="viking://resources/demo-notes")
client.find(query="배포 절차", limit=5)
```

세션을 커밋하면 대화가 보관되고, 거기서 **기억이 Markdown 으로 추출**된다. 사람이 읽고 고칠 수 있는 형태다. Claude Code, Codex, OpenClaw, Hermes 등과의 연동(Hooks·MCP·플러그인)도 README 에 정리돼 있다.

### 숨은 비용 — 기억은 공짜가 아니다

L0/L1 요약은 저절로 생기지 않는다. **문서가 바뀔 때마다 LLM 이 요약을 다시 쓴다.** [설정 가이드](https://docs.openviking.ai/en/guides/01-configuration)가 임베딩 모델과 VLM 을 필수로 요구하는 이유다.

이 홈랩에서는 이게 실제 사고가 됐다. 메모리 서버에 1분마다 쓰기가 일어나는 동기화 작업이 붙어 있었다. 쓰기 한 번이 디렉터리 재요약을 부르고, 그 재요약이 LLM 을 여러 번 불렀다. 그렇게 한 달 청구서가 전월 대비 **+2,217%** 가 됐다([사건 기록](/2026/09/14/gemini-api-bill-root-cause-openviking/)).

교훈은 하나다. **기억 계층은 사용자가 직접 호출하지 않는 '숨은 LLM 소비자' 다.** 그래서 두 번째 층이 필요하다.

## 2. LiteLLM — 모든 LLM 호출이 지나가는 관문

### 무엇인가

[LiteLLM](https://docs.litellm.ai/) 은 *"Call 100+ LLMs using the OpenAI Input/Output Format"*, 즉 100개가 넘는 LLM 을 OpenAI 형식 하나로 부르게 해 주는 도구다. 프록시 서버(LLM 게이트웨이, 기본 포트 4000)로 띄우면 이런 기능이 생긴다.

- **가상 키(Virtual keys):** 앱·사람마다 다른 키를 주고 권한을 나눈다
- **예산·지출 추적:** *"Track spend & set budgets per project"*
- **속도 제한(Rate limiting)**
- **재시도·대체(Fallback):** 한 공급자가 막히면 다른 배포로 넘어간다

### 사용법 — 프록시 설정 한 장

```yaml
# config.yaml
model_list:
  - model_name: summarizer            # 앱이 부르는 이름
    litellm_params:
      model: gemini/gemini-3.1-flash-lite
      api_key: os.environ/GEMINI_API_KEY

litellm_settings:
  callbacks: ["opik"]                  # 모든 호출을 Opik 으로 기록 (3절)
```

```bash
litellm --config config.yaml           # → http://0.0.0.0:4000
```

앱 쪽에서는 OpenAI SDK 의 `base_url` 만 프록시로 바꾸면 된다.

### OpenViking 을 관문 뒤로 보내기

이 글의 핵심 연결이 여기다. OpenViking 설정 가이드에 따르면 **임베딩과 VLM 공급자로 `litellm` 을 지정할 수 있다.** 그러면 OpenViking 의 요약·임베딩 호출이 전부 LiteLLM 프록시를 지난다.

그러면 이렇게 된다.

- OpenViking 전용 **가상 키**를 주고, 그 키에 **월 예산과 분당 호출 상한**을 건다.
- 재요약 폭주가 생기면 청구서가 오기 전에 **예산 상한에서 멈춘다.**
- 지출이 LiteLLM 대시보드에 **"OpenViking 몫"** 으로 따로 보인다.

9월 사고 때 이 연결이 있었다면 원인을 훨씬 빨리 좁혔을 거라고 본다. "어느 앱이 썼나" 를 키별 지출이 바로 말해 주기 때문이다.

## 3. Opik — 호출의 '질' 을 보는 층

LiteLLM 이 **얼마나** 썼는지를 보여 준다면, [Opik](https://github.com/comet-ml/opik) 은 **무엇을, 어떻게** 했는지를 보여 준다. 입력·출력·지연·토큰을 트레이스로 남기고, 데이터셋으로 평가하고, 대화를 스레드로 묶는다.

### 연결 방법 세 가지

**① LiteLLM 콜백** — 위 설정의 `callbacks: ["opik"]` 한 줄이면 관문을 지나는 모든 호출이 Opik 에 남는다([LiteLLM 문서](https://docs.litellm.ai/docs/observability/opik_integration)). 요청마다 `opik` 메타데이터로 `project_name`, `tags`, `thread_id` 를 붙일 수 있다. 프록시에서는 `opik_` 접두어 헤더로 넘긴다.

> 주의: 같은 기능인데 문서마다 키 이름이 다르다. LiteLLM 문서는 `callbacks: ["opik"]`, [Opik 쪽 문서](https://www.comet.com/docs/opik/integrations/litellm)는 `success_callback: ["opik"]` 로 적는다. 버전에 맞는 쪽을 확인하자.

**② OpenTelemetry** — Opik 은 OTel 을 HTTP 로 받는다([OTel 문서](https://www.comet.com/docs/opik/tracing/opentelemetry/overview)). 셀프호스팅 엔드포인트는 `http://<opik>:5173/api/v1/private/otel` 이다. OTel 을 내보내는 에이전트라면 SDK 없이 바로 붙는다.

**③ 스레드로 대화 묶기** — 트레이스에 같은 `thread_id` 를 주면 Opik 이 한 대화로 묶는다([스레드 문서](https://www.comet.com/docs/opik/tracing/advanced/log_chat_conversations)). 에이전트 세션 단위로 품질을 채점할 수 있다.

### 이 홈랩에서의 실제 사용

이 글을 쓰는 시점에 Opik 의 가장 활발한 프로젝트는 텔레그램 Claude Code 봇의 대화 기록이다. 9월 초부터 2,600건 넘게 쌓였고 하루 약 150건씩 들어온다. 대화마다 토큰(입력·출력·캐시)과 걸린 시간이 남는다. 나머지 실험·데모 프로젝트는 대부분 멈춰 있다. **관측 도구도 실제로 보는 프로젝트만 남기는 게** 관리 비용을 줄인다.

## 4. 세 층을 한 그림으로

```
          ┌──────────────────────────┐
 사용자 ─▶│  에이전트 (Hermes·Claude…)  │
          └────┬──────────────┬──────┘
               │ 기억 읽기·쓰기 │ LLM 호출
               ▼              │
        ┌────────────┐        │
        │ OpenViking │────────┤  요약·임베딩도 LLM 호출
        │  (기억)     │        │
        └────────────┘        ▼
                       ┌────────────┐   가상 키·예산·상한·대체
                       │  LiteLLM   │──────────────▶ Gemini / OpenAI / …
                       │  (관문)     │
                       └─────┬──────┘
                             │ 콜백 (모든 호출)
                             ▼
                       ┌────────────┐
                       │   Opik     │  트레이스·스레드·평가
                       │  (관측)     │
                       └────────────┘
```

핵심 원칙은 이렇다.

1. **모든 LLM 호출은 관문을 지난다.** 에이전트가 직접 하는 호출뿐 아니라 **기억 계층의 숨은 호출까지.** 관문을 우회하는 호출이 있으면 그곳이 다음 청구서 사고의 진원지다.
2. **관문은 '얼마', 관측은 '무엇'.** LiteLLM 의 지출 대시보드와 Opik 의 트레이스는 서로를 대신하지 못한다. 지출이 튀면 LiteLLM 에서 **누가** 썼는지 보고, Opik 에서 **무엇을** 했는지 본다.
3. **기억은 비용이다.** OpenViking 같은 컨텍스트 DB 는 강력하다. 그만큼 쓰기 빈도가 곧 LLM 호출 빈도가 된다. 동기화 주기, 재요약 조건, 캐시 적중률을 운영 지표로 봐야 한다.

## 5. 셀프호스팅 체크리스트

- [ ] OpenViking 의 임베딩·VLM 공급자를 `litellm` 으로 두고, 전용 가상 키에 예산 상한을 건다
- [ ] LiteLLM 마스터 키는 사람만 쓰고, 앱마다 가상 키를 나눈다
- [ ] LiteLLM → Opik 콜백을 켜고, 요청 메타데이터에 `thread_id` 를 넣는다
- [ ] Opik·OpenViking 의 내부 저장소(DB·캐시) 포트는 외부에 열지 않는다. Opik 의 저장소 구성은 [Opik·Redis·ClickHouse 글](/2026/10/03/opik-redis-clickhouse-usage-and-use-cases/) 참고
- [ ] OpenViking 은 AGPLv3 다. 고쳐서 네트워크 서비스로 제공할 계획이면 라이선스 의무를 확인한다

## References

- OpenViking — [GitHub (volcengine/OpenViking)](https://github.com/volcengine/OpenViking) · [Python SDK](https://github.com/volcengine/OpenViking/blob/main/sdk/python/README.md) · [Configuration guide](https://docs.openviking.ai/en/guides/01-configuration)
- LiteLLM — [Docs](https://docs.litellm.ai/) · [Opik integration](https://docs.litellm.ai/docs/observability/opik_integration)
- Opik — [GitHub (comet-ml/opik)](https://github.com/comet-ml/opik) · [LiteLLM integration](https://www.comet.com/docs/opik/integrations/litellm) · [OpenTelemetry](https://www.comet.com/docs/opik/tracing/opentelemetry/overview) · [Threads](https://www.comet.com/docs/opik/tracing/advanced/log_chat_conversations)
