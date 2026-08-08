---
layout: post
title: "LLM 친화적 API로서의 MCP: 기존 서버 API와의 비교, 동작 원리, ACP와의 차이, 그리고 하네스 관점의 고찰"
date: 2026-08-09 02:40:00 +0900
categories: [AI, Architecture, Engineering]
tags:
  [
    MCP,
    Model Context Protocol,
    ACP,
    Agent Client Protocol,
    A2A,
    REST,
    OpenAPI,
    JSON-RPC,
    Harness,
    Agent,
  ]
---

# LLM 친화적 API로서의 MCP

"MCP는 LLM을 위한 API다"라는 문장은 절반만 맞다. 프로토콜의 스펙만 놓고 보면 MCP는 JSON-RPC 2.0 위에 얹힌 평범한 RPC다. 진짜 차이는 **스키마의 소비자가 컴파일러가 아니라 모델**이라는 데서 나오고, 그 한 가지 전제가 인증·상태·에러·버저닝·컨텍스트 예산까지 전부 다시 설계하게 만든다.

이 글은 세 가지를 정리한다.

1. 기존 서버 기반 API(REST/OpenAPI)와 MCP를 **무엇이 실제로 다른가** 기준으로 비교
2. MCP의 원리와 사용법 — 2026-07-28 스펙 개정으로 **상태를 버린** 최신 모습 기준
3. ACP(이름이 셋이다)와의 차이, 그리고 **하네스(harness) 관점에서 반드시 다뤄야 할 지점들**

> 출처 등급에 대해: 이 글의 프로토콜 서술은 전부 1차 스펙 문서를 근거로 한다. 성능·토큰 절감 수치는 대부분 **벤더(Anthropic) 자체 평가**이며, 그 부분은 본문에서 명시적으로 라벨링했다. 중립 제3자의 헤드투헤드 벤치마크는 현재 공개된 것이 없다.

---

## 1. 출발점: 기존 서버 기반 API는 누구를 위해 설계되었나

REST + OpenAPI 스택의 암묵적 전제는 이것이다.

- **통합 코드를 사람이 쓴다.** 개발자가 문서를 읽고, 클라이언트를 생성하고, 필드를 매핑하고, 에러 코드를 분기한다.
- **통합은 빌드 타임에 고정된다.** 어떤 엔드포인트를 부를지는 배포 시점에 이미 결정되어 있다.
- **스키마는 검증 도구다.** OpenAPI 스펙의 주 소비자는 코드 제너레이터와 밸리데이터지, 런타임에 "어떤 걸 부를까" 고민하는 주체가 아니다.
- **인증 주체 = 애플리케이션.** 서비스 계정이든 사용자 토큰이든, 누가 무엇을 할 수 있는지는 코드가 정해둔 경로 안에서만 움직인다.

이 전제가 전부 깨지는 순간이 에이전트다. 에이전트는 **런타임에** 도구 목록을 읽고, **자연어 설명을 근거로** 무엇을 부를지 스스로 고르고, 결과를 보고 다음 호출을 정한다. 즉 스키마의 소비자가 컴파일러에서 모델로 바뀐다. 그래서 필요한 것이 세 가지다.

- 도구를 **런타임에 발견**할 수 있는 표준 (`tools/list`)
- 모델이 읽고 판단할 수 있는 **자연어 설명 + JSON Schema**
- 임의 코드 실행에 준하는 위험을 다루는 **동의(consent)·권한 모델**

MCP는 정확히 이 세 가지를 표준화한다. Anthropic이 2024년 11월 공개했고, 2025년 12월 9일 Linux Foundation 산하 directed fund인 **Agentic AI Foundation(AAIF)** 에 기증되어 벤더 중립 거버넌스로 넘어갔다.[^aaif-anthropic][^aaif-lf]

---

## 2. MCP의 원리

### 2.1 참여자: Host / Client / Server

MCP는 클라이언트-서버 구조다. 다만 용어가 헷갈리기 쉬우니 스펙의 정의를 그대로 옮긴다.[^mcp-arch]

- **MCP Host**: AI 애플리케이션 본체. Claude Code, VS Code, Claude Desktop 같은 것들. 여러 개의 클라이언트를 관리한다.
- **MCP Client**: 호스트 안에서 **서버 하나당 하나씩** 생성되는 커넥터. 전용 연결을 유지한다.
- **MCP Server**: 컨텍스트와 기능을 제공하는 프로그램. 로컬이든 원격이든 상관없다.

```
┌─ MCP Host (AI 애플리케이션) ────────────┐
│  MCP Client 1 ──────────────┐          │
│  MCP Client 2 ──────────┐   │          │
│  MCP Client 3 ──────┐   │   │          │
└─────────────────────┼───┼───┼──────────┘
                      │   │   └──▶ Server A (로컬, stdio) 파일시스템
                      │   └──────▶ Server B (로컬, stdio) DB
                      └──────────▶ Server C (원격, HTTP) Sentry
```

MCP 스펙 자체가 Language Server Protocol에서 영감을 받았다고 명시한다.[^mcp-spec] LSP가 "에디터 N개 × 언어 M개"의 통합 비용을 무너뜨린 것과 같은 구조다.

$$N \times M \;\longrightarrow\; N + M$$

### 2.2 두 계층: 데이터 계층과 전송 계층

**데이터 계층**은 JSON-RPC 2.0 기반 메시지 규약이다. **전송 계층**은 그 메시지가 실제로 오가는 통로다. 전송은 두 가지다.[^mcp-arch]

- **stdio**: 로컬 프로세스 간 표준 입출력. 네트워크 오버헤드 없음. 보통 클라이언트 1개를 서빙.
- **Streamable HTTP**: 클라이언트→서버는 HTTP POST, 스트리밍이 필요하면 Server-Sent Events. 원격 서버용이며 bearer token, API key, 커스텀 헤더 같은 표준 HTTP 인증을 쓴다. 스펙은 OAuth를 권장한다.

### 2.3 세 가지 프리미티브

서버가 클라이언트에게 노출할 수 있는 것은 셋뿐이다.[^mcp-spec]

| 프리미티브    | 정체                          | 통제 주체        | 대략적 비유       |
| ------------- | ----------------------------- | ---------------- | ----------------- |
| **Tools**     | 모델이 실행할 수 있는 함수    | 모델이 고름      | `POST /orders`    |
| **Resources** | 읽을 수 있는 컨텍스트 데이터  | 앱/사용자가 붙임 | `GET /files/{id}` |
| **Prompts**   | 재사용 가능한 상호작용 템플릿 | 사용자가 고름    | 슬래시 커맨드     |

각 프리미티브는 발견용 `*/list`, 조회용 `*/get`, 실행용 `tools/call` 메서드를 갖는다.

이 셋의 구분이 실무에서 중요한 이유는 **누가 트리거하느냐**가 다르기 때문이다. Tool은 모델이 자율적으로 부르므로 부작용이 있는 동작은 전부 여기 들어가고, 그래서 권한 게이트도 전부 여기 걸린다. Resource는 모델이 "고르는" 게 아니라 앱이 컨텍스트에 붙이는 것이라 위험도가 다르다. 이 경계를 헷갈려서 파괴적 동작을 Resource로 노출하는 설계가 실제로 나온다.

### 2.4 2026-07-28 개정: MCP는 상태를 버렸다

여기가 최신 스펙에서 가장 크게 바뀐 지점이고, 2025년 자료만 읽고 온 사람이 가장 크게 틀리는 부분이다. 2026-07-28 개정판의 major change를 요약하면:[^mcp-changelog]

1. **`initialize` / `notifications/initialized` 핸드셰이크 제거.** MCP는 이제 stateless다. 모든 요청이 `_meta` 필드에 자신의 프로토콜 버전(`io.modelcontextprotocol/protocolVersion`)과 클라이언트 capability를 싣고 다닌다.
2. **`Mcp-Session-Id` 헤더와 프로토콜 레벨 세션 제거.** 호출 간 상태가 필요한 서버는 **서버가 발급한 핸들을 평범한 tool 인자로** 주고받아야 한다.
3. **`server/discover` 신설, 구현 필수.** 서버는 지원 버전·capability·신원을 이 RPC로 광고한다. 클라이언트는 첫 요청 전에 호출할 수도, STDIO에서 하위호환 프로브로 쓸 수도 있다.
4. **`subscriptions/listen` 도입.** HTTP GET 엔드포인트와 `resources/subscribe`를 대체하는 단일 long-lived POST 스트림. 클라이언트가 알림 종류를 opt-in한다.
5. **MRTR (Multi Round-Trip Requests) 패턴.** 서버가 클라이언트에게 요청을 거는 기존 방식(`roots/list`, `sampling/createMessage`, `elicitation/create`)을 대체한다. 서버는 `resultType: "input_required"` 결과를 돌려주고, 클라이언트는 **원래 요청을 재시도하면서** `inputResponses`를 실어 보낸다.
6. **모든 결과에 `resultType` 필수** (`"complete"` 또는 `"input_required"`).
7. **SSE 재개(resumability)와 메시지 재전송 제거.** 스트림이 끊기면 in-flight 요청은 잃고, 클라이언트는 **새 request ID로 재발행**해야 한다.
8. **`sampling` deprecated.** 서버가 클라이언트의 LLM을 역으로 호출하던 기능은 2026-07-28부터 폐기 상태다.[^mcp-arch]
9. **Tasks가 코어에서 공식 extension으로 이동** (`io.modelcontextprotocol/tasks`). 블로킹 `tasks/result` 대신 `tasks/get` 폴링 + `tasks/update` 입력.

minor change 중에도 **하네스 설계자가 반드시 봐야 할 것**이 섞여 있다.

- `tools/list`는 **결정적(deterministic) 순서**로 반환해야 한다(SHOULD). 이유가 명시적이다 — 클라이언트 캐시와 **LLM 프롬프트 캐시 히트율**.
- `tools/list`, `prompts/list`, `resources/list`, `resources/read` 결과에 `ttlMs`와 `cacheScope`(`public`/`private`)가 **필수**로 붙는다(`CacheableResult`).
- `_meta`에 OpenTelemetry trace context(`traceparent`, `tracestate`, `baggage`) 전파 규약이 문서화됐다.

즉 이번 개정의 방향성은 한 문장으로 요약된다. **"MCP를 평범한 무상태 HTTP 서비스처럼 배포·스케일·관측할 수 있게 만든다."** 세션 어피니티가 사라졌으니 로드밸런서 뒤에 그냥 여러 대 띄우면 되고, TTL이 붙었으니 중간 캐시를 둘 수 있고, OTel 규약이 있으니 기존 APM에 그대로 얹힌다. 반대급부로 **상태 관리 책임은 전부 서버 설계자에게 넘어왔다.**

### 2.5 최소 사용법

**서버 쪽(Python, 공식 SDK 계열의 전형적 형태):**

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("settlement-ops")

@mcp.tool()
def get_settlement_summary(merchant_id: str, date: str) -> str:
    """특정 가맹점의 일별 정산 요약을 조회한다.

    Args:
        merchant_id: 가맹점 ID (예: "M-10023")
        date: 조회 기준일, YYYY-MM-DD
    Returns:
        총 거래액/수수료/지급예정액이 담긴 JSON 문자열
    """
    ...

if __name__ == "__main__":
    mcp.run()   # 기본 stdio 전송
```

**클라이언트(호스트) 쪽 설정** — 로컬 stdio 서버는 실행 명령으로, 원격 서버는 URL로 등록한다.

```json
{
  "mcpServers": {
    "settlement-ops": {
      "command": "python",
      "args": ["-m", "settlement_mcp"],
      "env": { "SETTLEMENT_API_TOKEN": "..." }
    },
    "sentry": {
      "type": "http",
      "url": "https://mcp.sentry.dev/mcp"
    }
  }
}
```

여기서 실무적으로 중요한 디테일 하나. **로컬 stdio 서버의 인증은 환경변수로 들어간다.** 그래서 org-admin 토큰을 그대로 꽂는 순간, 그 토큰의 전 권한이 모델의 도구 표면이 된다. 최소 권한으로 좁게 발급한 토큰을 쓰는 것이 stdio MCP 서버 운영의 첫 번째 규칙이다.

**도구 설명(description)을 쓰는 법**도 REST 문서와 다르다. OpenAPI의 `description`은 사람이 읽고 넘어가는 주석이지만, MCP의 tool description은 **모델의 라우팅 근거**다. 즉 이것은 문서가 아니라 프롬프트다.

- 나쁜 예: `"정산 조회"`
- 좋은 예: `"특정 가맹점의 일별 정산 요약 조회. 월별 집계가 필요하면 get_monthly_settlement 를 대신 쓸 것. merchant_id 를 모르면 search_merchant 를 먼저 호출."`

인접 도구와의 **경계 조건과 선행 호출**을 설명에 박아두는 것이 도구 선택 정확도에 직접 영향을 준다.

---

## 3. 기존 서버 API vs MCP: 실제로 다른 지점

| 축              | REST / OpenAPI                   | MCP                                                   |
| --------------- | -------------------------------- | ----------------------------------------------------- |
| 스키마의 소비자 | 코드 제너레이터, 밸리데이터      | **모델**                                              |
| 통합 결정 시점  | 빌드 타임 (개발자가 코드로 고정) | **런타임** (모델이 목록 보고 선택)                    |
| 발견            | 문서·스펙 파일 (사람이 읽음)     | `server/discover` + `tools/list` (기계가 읽음)        |
| 와이어 포맷     | HTTP + JSON, 리소스 지향         | JSON-RPC 2.0, 메서드 지향                             |
| 전송            | HTTP(S)                          | stdio 또는 Streamable HTTP                            |
| 상태            | 보통 stateless (REST 원칙)       | **2026-07-28부터 stateless**, 필요하면 서버 발급 핸들 |
| 에러 처리       | HTTP 상태 코드 + 바디            | JSON-RPC error object (+ 코드 할당 정책)              |
| 버저닝          | URL 경로 `/v1`, 헤더             | 요청마다 `_meta` 안의 프로토콜 버전                   |
| 인가            | 앱 단위 토큰/스코프              | OAuth 권장 + **호출 시점 사용자 동의**                |
| 실패 모드       | 400/500 — 개발자가 대응          | **모델이 잘못된 도구를 그럴듯하게 고름**              |
| 비용 단위       | RPS, 대역폭                      | **컨텍스트 토큰**                                     |

마지막 두 줄이 핵심이다.

**첫째, 실패 모드가 다르다.** REST에서 잘못된 호출은 4xx로 즉시 튕긴다. MCP에서 가장 비싼 실패는 프로토콜 에러가 아니라 **모델이 그럴듯하지만 틀린 도구를 골라서 성공적으로 실행하는 것**이다. 200 OK가 떨어지고, 로그도 깨끗하고, 결과만 틀리다. 이 실패는 스키마 검증으로 못 잡는다. 도구 설명의 품질과 권한 게이트로만 잡힌다.

**둘째, 비용 단위가 다르다.** REST API는 안 부르면 공짜다. MCP 도구는 **부르지 않아도 정의만으로 컨텍스트를 먹는다.** Anthropic이 밝힌 자체 측정에 따르면, 5개 서버 58개 도구가 대화 시작 전에 이미 약 55K 토큰을 소모했고, Jira 서버 하나만 약 17K 토큰이었으며, 내부적으로는 최적화 전 도구 정의가 134K 토큰까지 갔다.[^advanced-tool-use] (벤더 자체 측정이며 서버 구현에 따라 크게 달라진다.)

그리고 이건 단순한 비용 문제가 아니라 **정확도 문제**로 이어진다. Claude Agent SDK 문서는 "도구가 30~50개를 넘으면 도구 선택 정확도가 저하된다"고 명시한다.[^tool-search-sdk] 사람이 쓰는 API 게이트웨이는 엔드포인트가 500개여도 아무 문제 없다. 모델은 다르다.

### MCP가 항상 정답은 아니다

REST/CLI 대비 MCP가 손해인 경우가 분명히 있다.

- **호출 경로가 이미 고정된 통합**: 배포 시점에 뭘 부를지 정해져 있다면 런타임 발견은 순수 오버헤드다. 그냥 SDK를 쓰는 게 맞다.
- **도구가 3~5개뿐인 좁은 에이전트**: 시스템 프롬프트에 직접 함수 정의를 박는 편이 단순하고 빠르다.
- **이미 훌륭한 CLI가 있는 경우**: 모델은 `kubectl`, `gh`, `psql`을 이미 잘 안다. 이걸 MCP 서버로 다시 감싸면 학습된 지식을 버리고 낯선 스키마를 새로 가르치는 셈이다. 실제로 얇은 MCP 래퍼가 원본 CLI보다 못 쓰이는 사례가 흔하다.

MCP가 이기는 지점은 **(a) 도구 세트가 사용자·환경마다 다르고 (b) 배포 시점에 알 수 없으며 (c) 여러 호스트에 재사용되어야 할 때**다.

---

## 4. ACP와의 차이 — 먼저 이름부터 정리하자

"ACP"라는 약어를 쓰는 프로토콜이 최소 셋이다. 이걸 구분하지 않으면 논의가 통째로 어긋난다.

### (A) Agent Client Protocol — Zed 발, 에디터 ↔ 에이전트

이 글에서 MCP와 비교할 대상이다. Zed가 만들었고 2025년 8월 27일 Gemini CLI를 초기 레퍼런스 구현으로 공개했다.[^zed-acp] 저장소는 `agentclientprotocol/agent-client-protocol`, Apache-2.0, 2025년 6월 23일 생성.[^acp-repo]

만들어진 계기가 재미있다. Zed는 이미 내장 터미널에서 Gemini CLI를 돌리고 있었는데, **ANSI 이스케이프 코드보다 구조적인 통신 수단이 필요**해서 최소한의 JSON-RPC 엔드포인트 집합을 정의한 것이 ACP다.[^zed-acp]

설계 원칙 셋을 스펙이 직접 밝힌다.[^acp-arch]

1. **MCP-friendly**: JSON-RPC 기반이며, 공통 데이터 타입에 대해 **MCP의 JSON 표현을 최대한 재사용**한다. "또 하나의 표현"을 만들지 않기 위해서다.
2. **UX-first**: 에이전트의 의도를 명확히 렌더링하는 데 필요한 만큼만 추상화한다. 필요 이상으로 추상적이지 않게.
3. **Trusted**: 신뢰하는 모델을 에디터로 부를 때를 전제한다. 툴 콜 통제권은 있지만, 에디터가 에이전트에게 로컬 파일과 MCP 서버 접근을 준다.

메서드 흐름은 이렇다.[^acp-overview]

```
Client(에디터) → Agent : initialize        (버전·capability 협상)
Client → Agent : auth/login                (에이전트가 요구할 때만)
Client → Agent : session/new | session/resume
Client → Agent : session/prompt            (사용자 메시지)
Agent  → Client: session/update  (알림)    ← 메시지 청크, 툴 콜, diff, plan,
                                              슬래시 커맨드 목록, 설정 변경...
Agent  → Client: session/request_permission (툴 콜 승인 요청)
Client → Agent : session/cancel  (알림)
```

주목할 규약 두 개: **모든 파일 경로는 절대경로여야 하고(MUST), 줄 번호는 1-based다.** 에디터 통합에서 이 두 가지가 어긋나면 조용히 엉뚱한 파일을 편집한다.

그리고 ACP와 MCP를 한 소켓에 올리지 않는 설계 결정이 명시되어 있다. 에디터가 자기 도구를 MCP로 노출하고 싶으면, ACP 소켓에 얹는 대신 **자기 자신으로 요청을 되돌리는 작은 stdio 프록시를 MCP 서버 설정으로 제공**하라고 스펙이 안내한다.[^acp-arch] 계층을 섞지 않겠다는 의지다.

> 버전 주의: 공식 문서는 `/protocol/v2/` 경로의 메서드 집합을 서술하지만, 저장소는 "현재 안정 ACP **프로토콜** 버전은 1"이라고 명시하고, 크레이트/스키마 아티팩트 버전과 와이어 프로토콜 버전을 **혼동하지 말라**고 경고한다. 와이어 호환성은 `initialize`에서 교환하는 `protocolVersion`으로만 판단해야 한다.[^acp-repo]

### (B) Agent Communication Protocol — IBM/BeeAI 발, 이미 A2A로 병합됨

이쪽 ACP는 RESTful API 기반의 에이전트 간 상호운용 프로토콜이었다. 지금 공식 사이트 최상단에 이렇게 붙어 있다: **"ACP is now part of A2A under the Linux Foundation!"** 마이그레이션 가이드까지 제공된다.[^ibm-acp] 새로 시작하는 프로젝트가 이 ACP를 채택할 이유는 없다.

### (C) A2A (Agent2Agent) — 에이전트 ↔ 에이전트

Google이 만들어 Linux Foundation으로 이관한 프로토콜. A2A 공식 문서가 MCP와의 관계를 직접 정리해 두었다.[^a2a-mcp]

- **MCP**: 에이전트가 **도구와 리소스**를 쓰는 방법. 잘 정의된 구조적 입출력, 대체로 무상태.
- **A2A**: 자율적이고 불투명한 **에이전트들이 서로 협업**하는 방법. 서로를 발견하고, 협상하고, 공유 태스크를 관리하고, 복잡한 데이터를 교환.

A2A 문서의 표현을 빌리면 **"A2A는 에이전트가 태스크를 파트너와 함께 수행하는 것에, MCP는 에이전트가 능력을 사용하는 것에 초점을 둔다."**

### 계층도

이 셋은 경쟁 관계가 아니라 **서로 다른 경계**를 표준화한다.

```
            ┌──────────────────────┐
   A2A ────▶│   다른 에이전트      │   에이전트 ↔ 에이전트 (위임/협업)
            └──────────────────────┘
                     ▲
                     │
┌──────────┐  ACP  ┌─┴──────────┐  MCP  ┌──────────────┐
│  에디터  │◀─────▶│  에이전트  │◀─────▶│ 도구 / 데이터 │
│  (IDE)   │       │            │       │ (MCP 서버)   │
└──────────┘       └────────────┘       └──────────────┘
   "이 에이전트가          "무엇을 할 수     "무엇에 손댈 수
    내 에디터 안           있는가"           있는가"
    어디에 사는가"
```

방향까지 보면 더 선명하다.

- **ACP에서는 에디터가 묻고 에이전트가 답한다.** 프롬프트가 들어가고, 진행 상황과 diff가 스트리밍되어 나온다. 에이전트는 **서버** 역할.
- **MCP에서는 에이전트가 묻고 서버가 답한다.** 도구를 호출하고 결과를 받는다. 에이전트는 **클라이언트** 역할.

**같은 에이전트가 동시에 두 모자를 쓴다.** 에디터에 대해서는 ACP 서버이고, 도구에 대해서는 MCP 클라이언트다.

| 축                 | ACP (Agent Client Protocol)                               | MCP                                      |
| ------------------ | --------------------------------------------------------- | ---------------------------------------- |
| 표준화하는 경계    | 에디터 ↔ 에이전트                                         | 에이전트 ↔ 도구/데이터                   |
| 답하는 질문        | "어떤 에이전트가 내 에디터에서 도나"                      | "그 에이전트가 뭘 만질 수 있나"          |
| 에이전트의 역할    | 서버                                                      | 클라이언트                               |
| 만든 곳 / 거버넌스 | Zed, Apache-2.0                                           | Anthropic → AAIF (Linux Foundation)      |
| 전송               | JSON-RPC over stdio (원격 HTTP/WS는 작업 중)              | JSON-RPC over stdio 또는 Streamable HTTP |
| 핵심 개념          | 세션, 프롬프트 턴, 스트리밍 업데이트, **diff**, 권한 요청 | tools, resources, prompts                |
| 상대를 참조하는가  | MCP의 JSON 표현을 재사용                                  | ACP를 모름 (도구 쪽만 봄)                |

터미널에서 도는 에이전트(Claude Code, Codex CLI)에게는 **ACP가 아예 스택에 없다.** MCP만 있다. 에디터 안으로 들어가는 순간 둘 다 관여한다.

---

## 5. 하네스 관점의 고찰

여기부터가 실제로 에이전트를 운영해 본 사람에게 남는 문제들이다. 프로토콜 스펙은 이 문제들을 **정의만 하고 해결은 하네스에 떠넘긴다.**

### 5.1 컨텍스트 예산이 1급 자원이다

앞서 봤듯 도구 정의는 부르지 않아도 토큰을 먹고, 30~50개를 넘으면 선택 정확도가 떨어진다.[^tool-search-sdk] 그래서 하네스 레벨의 완화 전략이 세 갈래로 나왔다.

**(a) 지연 로딩 / 도구 검색.** 전부 올리지 말고 필요할 때 찾아 올린다. Claude API에서는 도구에 `defer_loading: true`를 걸고 Tool Search Tool로 발견하는 방식이다. 프롬프트 캐시를 깨지 않는 것이 설계 포인트다 — 지연된 도구는 애초에 초기 프롬프트에 없기 때문이다.[^advanced-tool-use] Agent SDK에서는 기본 활성이고 `ENABLE_TOOL_SEARCH=auto:N`으로 "도구 정의가 컨텍스트 윈도우의 N%를 넘으면 켜기" 같은 임계 제어가 가능하다.[^tool-search-sdk]

> **벤더 자체 평가**: Anthropic은 Tool Search Tool 적용 시 토큰 사용 85% 감소, MCP 평가에서 Opus 4가 49%→74%, Opus 4.5가 79.5%→88.1%로 개선됐다고 밝혔다.[^advanced-tool-use] 중립 제3자 재현 결과는 공개된 것이 없다.

**(b) 코드 실행으로 도구 호출.** 모델이 도구를 하나씩 부르는 대신, 도구를 코드 API로 노출하고 모델이 스크립트를 쓰게 한다. 중간 결과가 모델 컨텍스트를 거치지 않는다는 것이 핵심이다.[^code-exec-mcp]

```typescript
// 직접 호출: 전사본 전체가 컨텍스트를 두 번 통과한다
// (읽을 때 한 번, 다시 쓸 때 한 번)

// 코드 실행: 전사본은 실행 환경 안에만 머문다
import * as gdrive from "./servers/google-drive";
import * as salesforce from "./servers/salesforce";

const transcript = (await gdrive.getDocument({ documentId: "abc123" })).content;
await salesforce.updateRecord({
  objectType: "SalesMeeting",
  recordId: "00Q5f000001abcXYZ",
  data: { Notes: transcript },
});
```

> **벤더 자체 평가**: 위 파일트리 방식 예시에서 Anthropic은 150,000 → 2,000 토큰(98.7% 절감)을 보고했다.[^code-exec-mcp] 이것은 특정 시나리오의 예시 수치이지 일반적 보장이 아니다.

**(c) Programmatic Tool Calling.** 위 아이디어를 API 기능으로 제품화한 것. 정직하게도 **손해 보는 구간까지 문서화되어 있다**는 점이 인용 가치가 있다.[^ptc-docs]

- 75개 도구 프로젝트 관리 벤치마크: 과금 입력 토큰 약 38% 감소, 정확도 변화 없음
- τ²-bench(턴당 순차 1~2회 호출): 점수 변화 없고 **비용은 약 8% 증가**. "순차 단일 호출 워크플로는 이득이 없다"고 명시
- 프로덕션 트래픽에서 도구 정의가 10~~49개인 요청: 통상 20~~40% 절감

교훈은 단순하다. **팬아웃/대용량 필터링에는 강하고, 순차 의존 워크플로에는 손해다.** 하네스는 워크로드 모양을 보고 껐다 켜야 한다.

### 5.2 캐시와 결정성 — 조용히 돈을 태우는 곳

2026-07-28 스펙이 `tools/list`에 **결정적 순서**를 SHOULD로 요구한 이유가 바로 프롬프트 캐시다.[^mcp-changelog] 도구 목록이 매번 다른 순서로 오면 시스템 프롬프트의 바이트가 달라지고, **프롬프트 캐시가 통째로 미스난다.**

이건 아주 실무적인 함정이다. 서버 구현에서 `dict` 순회나 병렬 수집 결과를 그대로 뱉으면 순서가 흔들리고, 그 결과는 에러가 아니라 **조용한 비용 증가**로만 나타난다. 로그에도 안 남고 알림도 안 뜬다. `ttlMs` / `cacheScope`가 스펙에 들어온 것도 같은 방향 — 중간 캐시를 둘 수 있게 하려는 것이다.

**하네스 체크리스트:** 도구 목록 정렬 고정 / TTL 존중 / 캐시 히트율 계측.

### 5.3 신뢰 경계 — 스펙이 강제할 수 없다고 스스로 인정한 부분

MCP 스펙의 보안 원칙 중 가장 무거운 한 줄은 이것이다.[^mcp-spec]

> **"도구 동작에 대한 설명(annotation 등)은 신뢰할 수 있는 서버에서 얻은 것이 아닌 한 신뢰할 수 없는 것으로 취급해야 한다."**

즉 **도구 설명 자체가 프롬프트 인젝션 벡터**다. 서드파티 MCP 서버를 붙이는 순간, 그 서버 운영자가 당신 모델의 시스템 프롬프트에 텍스트를 밀어 넣을 수 있는 것과 같다.

그리고 스펙은 **"MCP 자체는 이 보안 원칙들을 프로토콜 레벨에서 강제할 수 없다"** 고 명시한다. 구현자가 동의·인가 플로우를 직접 만들어야 한다는 뜻이다. 이 책임은 전부 하네스로 온다.

인가 쪽에서 스펙이 다루는 구체적 공격도 봐야 한다. 대표적으로 **Confused Deputy** — MCP 프록시 서버가 서드파티 인가 서버에 **정적 client ID**를 쓰면서, MCP 클라이언트에게는 **동적 등록**을 허용하고, 서드파티가 동의 쿠키를 심는 조합에서 성립한다. 공격자가 악성 redirect_uri로 동적 등록을 하면, 이미 심어진 동의 쿠키 때문에 **동의 화면이 스킵되고** 인가 코드가 공격자에게 전달된다.[^mcp-security] 완화책은 "프록시가 클라이언트별 동의를 직접 받는 것"이다.

2026-07-28 개정의 인가 관련 변경도 같은 맥락이다: 인가 응답에 RFC 9207의 `iss` 파라미터 포함(SHOULD)과 클라이언트의 `iss` 검증 의무(MUST), 그리고 **클라이언트 자격증명은 발급한 인가 서버에 바인딩**되므로 issuer로 키잉해서 저장해야 하고 다른 인가 서버에 재사용해서는 안 된다(MUST NOT).[^mcp-changelog]

**하네스 체크리스트:** 서버별 신뢰 등급 분리 / 파괴적 도구는 항상 사용자 승인 / 최소 권한 토큰 / 도구 설명을 신뢰 입력으로 취급하지 않기 / issuer별 자격증명 격리.

### 5.4 상태 관리 책임의 이동

프로토콜 세션이 사라졌으므로, 다단계 작업의 상태는 이제 **서버가 발급한 핸들을 tool 인자로 주고받아** 관리한다.[^mcp-changelog] 여기서 하네스가 답해야 할 질문이 생긴다.

- 그 핸들의 수명은? 만료되면 모델은 무엇을 보게 되나?
- 컨텍스트가 압축(compaction)될 때 핸들이 잘려나가면?
- 스트림이 끊겨 재발행할 때(스펙상 새 request ID로 새 요청) **부작용이 있는 도구가 두 번 실행되면?**

마지막 항목이 특히 중요하다. SSE 재개와 메시지 재전송이 제거되면서, **끊긴 요청의 재발행은 클라이언트 책임**이 됐다.[^mcp-changelog] 즉 부작용 있는 MCP 도구는 **멱등성 키를 자기 인자로 받는 설계**가 사실상 필수다. 이건 분산 메시징에서 at-least-once 배달 + 멱등 수신으로 푸는 것과 정확히 같은 문제이고, 같은 해법이 적용된다.

### 5.5 관측성

`_meta`의 OpenTelemetry trace context 전파 규약이 문서화된 것[^mcp-changelog]이 실무적으로 큰 이유는, 이게 있어야 **"모델이 왜 그 도구를 골랐나"와 "그 호출이 백엔드에서 뭘 했나"를 하나의 트레이스로 이을 수 있기** 때문이다. 이게 없으면 에이전트 장애 분석은 "모델 로그 따로, 서버 로그 따로"가 되어 사실상 불가능해진다.

계측해야 할 것들:

- 도구별 **선택 빈도 / 실패율 / 재시도율** — 안 쓰이는 도구는 순수 컨텍스트 낭비이므로 제거 후보다
- **도구 정의가 차지하는 토큰 비중** — 컨텍스트 윈도우의 몇 %인지
- **프롬프트 캐시 히트율** — 5.2의 정렬 문제를 잡는 유일한 신호
- 잘못된 도구 선택률 — 자동 계측이 어렵고 평가셋이 필요하다

### 5.6 하네스가 진짜로 다뤄야 하는 것: 도구 큐레이션

지금까지의 논의를 하나로 압축하면 이렇다.

**REST API 설계는 "이 동작을 어떻게 표현할까"의 문제였고, MCP 도구 설계는 "이 동작을 모델에게 보여줄 가치가 있는가"의 문제다.**

REST에서 엔드포인트를 하나 더 만드는 비용은 거의 0이다. MCP에서 도구를 하나 더 노출하는 비용은 0이 아니다 — 모든 요청의 컨텍스트를 먹고, 다른 도구들의 선택 정확도를 갉아먹는다. 그래서 좋은 하네스는 도구를 **더하는** 게 아니라 **고르는** 일을 한다.

- 도구 20개짜리 서버를 붙이기 전에, 그중 실제로 쓸 3개만 노출할 방법이 있는지 본다
- 이미 모델이 잘 아는 CLI가 있으면 MCP로 감싸지 않는다
- 겹치는 도구는 통합한다(모델은 비슷한 두 도구 앞에서 흔들린다)
- 도구 설명에 인접 도구와의 경계를 명시한다
- 사용률이 낮은 도구는 주기적으로 제거한다

---

## 6. 정리

- **MCP**는 에이전트 ↔ 도구/데이터 경계의 표준이다. JSON-RPC 2.0, stdio 또는 Streamable HTTP, tools/resources/prompts 세 프리미티브. 2025년 12월 Linux Foundation 산하 AAIF로 이관되어 벤더 중립이 됐다.
- **2026-07-28 개정으로 MCP는 무상태가 됐다.** `initialize` 핸드셰이크와 세션 헤더가 사라지고, `server/discover`가 생기고, 서버 주도 요청은 MRTR 패턴으로 뒤집혔으며, sampling은 폐기됐다. 2025년 자료로 MCP를 이해하고 있다면 지금 다시 읽어야 한다.
- **기존 서버 API와의 진짜 차이는 프로토콜이 아니라 소비자다.** 스키마를 모델이 읽는 순간 실패 모드가 "에러"에서 "그럴듯하게 틀린 성공"으로 바뀌고, 비용 단위가 RPS에서 토큰으로 바뀐다.
- **ACP(Agent Client Protocol)는 MCP의 경쟁자가 아니라 반대편 경계다.** 에디터 ↔ 에이전트를 표준화하고, MCP의 JSON 표현을 의도적으로 재사용한다. 같은 에이전트가 ACP 서버이면서 MCP 클라이언트다. 이름이 같은 IBM의 ACP는 이미 A2A로 병합됐고, A2A는 또 다른 층(에이전트 ↔ 에이전트)이다.
- **하네스가 해결해야 하는 것**은 컨텍스트 예산, 도구 큐레이션, 캐시 결정성, 신뢰 경계, 재시도 멱등성, 그리고 관측성이다. 프로토콜은 이 중 어느 것도 대신 해주지 않는다. 스펙 스스로 "프로토콜 레벨에서 강제할 수 없다"고 적어두었다.

---

## References

**MCP 1차 출처**

- Model Context Protocol, _Specification (latest)_ — <https://modelcontextprotocol.io/specification/latest>
- Model Context Protocol, _Architecture overview_ — <https://modelcontextprotocol.io/docs/learn/architecture>
- Model Context Protocol, _Key Changes (2026-07-28)_ — <https://modelcontextprotocol.io/specification/2026-07-28/changelog>
- Model Context Protocol, _Security Best Practices_ — <https://modelcontextprotocol.io/specification/2026-07-28/basic/security_best_practices>
- JSON-RPC 2.0 Specification — <https://www.jsonrpc.org/specification>

**거버넌스**

- Anthropic, _Donating the Model Context Protocol and establishing the Agentic AI Foundation_ (2025-12-09) — <https://www.anthropic.com/news/donating-the-model-context-protocol-and-establishing-of-the-agentic-ai-foundation>
- Linux Foundation, _Linux Foundation Announces the Formation of the Agentic AI Foundation (AAIF)_ (2025-12-09) — <https://www.linuxfoundation.org/press/linux-foundation-announces-the-formation-of-the-agentic-ai-foundation>

**ACP / A2A 1차 출처**

- Agent Client Protocol, _Introduction_ — <https://agentclientprotocol.com/overview/introduction>
- Agent Client Protocol, _Architecture_ — <https://agentclientprotocol.com/overview/architecture>
- Agent Client Protocol, _Protocol Overview_ — <https://agentclientprotocol.com/protocol/v2/overview>
- GitHub, _agentclientprotocol/agent-client-protocol_ (Apache-2.0) — <https://github.com/agentclientprotocol/agent-client-protocol>
- Zed, _Bring Your Own Agent to Zed — Featuring Gemini CLI_ (2025-08-27) — <https://zed.dev/blog/bring-your-own-agent-to-zed>
- A2A Protocol, _A2A and MCP: Detailed Comparison_ — <https://a2a-protocol.org/latest/topics/a2a-and-mcp/>
- Agent Communication Protocol (IBM/BeeAI), 공식 사이트의 A2A 병합 공지 — <https://agentcommunicationprotocol.dev/>

**벤더 자체 측정 (수치는 Anthropic 내부 평가이며 중립 제3자 재현 결과는 공개되어 있지 않음)**

- Anthropic Engineering, _Code execution with MCP: building more efficient AI agents_ (2025-11-04) — <https://www.anthropic.com/engineering/code-execution-with-mcp>
- Anthropic Engineering, _Introducing advanced tool use on the Claude Developer Platform_ (2025-11-24) — <https://www.anthropic.com/engineering/advanced-tool-use>
- Claude Platform Docs, _Programmatic tool calling_ — <https://platform.claude.com/docs/en/agents-and-tools/tool-use/programmatic-tool-calling>
- Claude Agent SDK Docs, _Scale to many tools with tool search_ — <https://code.claude.com/docs/en/agent-sdk/tool-search>

**면책**: 본문의 토큰 절감률·정확도 개선 수치는 전부 프로토콜/모델 벤더가 자사 워크로드에서 측정해 발표한 값이다. 워크로드 형태(팬아웃 vs 순차, 결과 크기, 도구 개수)에 따라 결과가 크게 달라지며, 실제로 Anthropic 자신도 순차 워크플로에서는 오히려 비용이 증가한 사례를 문서화했다. 도입 전 자신의 대표 트래픽에서 직접 측정할 것을 권한다.

[^mcp-spec]: Model Context Protocol, _Specification (latest)_. <https://modelcontextprotocol.io/specification/latest>

[^mcp-arch]: Model Context Protocol, _Architecture overview_. <https://modelcontextprotocol.io/docs/learn/architecture>

[^mcp-changelog]: Model Context Protocol, _Key Changes_ (spec revision 2026-07-28). <https://modelcontextprotocol.io/specification/2026-07-28/changelog>

[^mcp-security]: Model Context Protocol, _Security Best Practices_. <https://modelcontextprotocol.io/specification/2026-07-28/basic/security_best_practices>

[^aaif-anthropic]: Anthropic, _Donating the Model Context Protocol and establishing the Agentic AI Foundation_, 2025-12-09.

[^aaif-lf]: Linux Foundation, _Linux Foundation Announces the Formation of the Agentic AI Foundation (AAIF)_, 2025-12-09.

[^zed-acp]: Zed, _Bring Your Own Agent to Zed — Featuring Gemini CLI_, 2025-08-27.

[^acp-repo]: GitHub, _agentclientprotocol/agent-client-protocol_ README (Apache-2.0, created 2025-06-23).

[^acp-arch]: Agent Client Protocol, _Architecture_.

[^acp-overview]: Agent Client Protocol, _Protocol Overview_.

[^ibm-acp]: Agent Communication Protocol 공식 사이트 공지: "ACP is now part of A2A under the Linux Foundation."

[^a2a-mcp]: A2A Protocol, _A2A and MCP: Detailed Comparison_ (The Linux Foundation).

[^advanced-tool-use]: Anthropic Engineering, _Introducing advanced tool use on the Claude Developer Platform_, 2025-11-24. 벤더 자체 측정.

[^code-exec-mcp]: Anthropic Engineering, _Code execution with MCP: building more efficient AI agents_, 2025-11-04. 벤더 자체 측정.

[^ptc-docs]: Claude Platform Docs, _Programmatic tool calling_. 벤더 내부 평가 수치 포함.

[^tool-search-sdk]: Claude Agent SDK Docs, _Scale to many tools with tool search_.
