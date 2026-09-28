---
layout: post
title: "MCP와 ACP 잘 쓰는 법 — 2026-07-28 스펙 기준 실전 규칙과 안티패턴"
date: 2026-09-28 22:56:18 +0900
categories: [AI]
tags: [MCP, ACP, AgentClientProtocol, A2A, Security, OAuth, Agent, Harness]
---

MCP와 ACP의 *개념*은 앞선 글([MCP vs REST·ACP](https://myoungsoo7.github.io/2026/08/09/mcp-vs-rest-api-acp-harness/), [ReAct·MCP·ACP](https://myoungsoo7.github.io/2026/09/17/react-mcp-acp-one-loop-three-boundaries/))에서 다뤘습니다. 이 글은 **"그래서 어떻게 써야 사고가 안 나는가"** 만 다룹니다. 근거는 MCP 공식 스펙 2026-07-28 개정판, MCP 공식 보안 가이드, Agent Client Protocol 공식 문서 같은 1차 출처로 한정했습니다. 출처가 없는 주장은 **(해석)** 이라고 표시했습니다.

---

## 0. 먼저 이름부터 — "ACP"는 두 개다

| 이름 | 누가 | 무엇과 무엇 사이 | 지금 상태 |
|---|---|---|---|
| **Agent Client Protocol** | Zed 주도 → `agentclientprotocol` 조직 | **에디터 ↔ 코딩 에이전트** | 프로토콜 v1 안정판, 활발히 쓰임 ([공식 소개](https://agentclientprotocol.com/overview/introduction)) |
| **Agent Communication Protocol** | IBM Research / BeeAI | 에이전트 ↔ 에이전트 | 2025-08-29 **A2A에 합류**(LF AI & Data) ([LF 공지](https://lfaidata.foundation/communityblog/2025/08/29/acp-joins-forces-with-a2a-under-the-linux-foundations-lf-ai-data/)) |

**규칙 1. 2026년에 "ACP를 쓴다"는 말은 거의 항상 Agent Client Protocol이다.** 에이전트 ↔ 에이전트 통신이 필요하면 IBM ACP 말고 [A2A](https://www.linuxfoundation.org/press/linux-foundation-launches-the-agent2agent-protocol-project-to-enable-secure-intelligent-communication-between-ai-agents)를 봅니다. IBM이 직접 합류를 발표했기 때문입니다. 문서나 회의에서 "ACP"라고만 쓰면 둘 중 어느 쪽인지 반드시 풀어 씁니다.

세 프로토콜은 경쟁하지 않고 **축이 다릅니다**.

```
 사람 ──(에디터 UI)── [ACP] ── 코딩 에이전트 ──[MCP]── 도구·데이터(DB, GitHub, 사내 API)
                                     │
                                   [A2A] ── 다른 조직/다른 벤더의 에이전트
```

- **MCP**: 에이전트가 *도구와 컨텍스트를* 얻는 통로 ([MCP 스펙](https://modelcontextprotocol.io/specification/2026-07-28))
- **ACP**: 사람이 쓰는 *에디터가 에이전트를* 부리는 통로 ([ACP 아키텍처](https://agentclientprotocol.com/overview/architecture))
- **A2A**: *에이전트끼리* 일을 주고받는 통로

어느 걸 써야 할지 헷갈리면 "지금 연결하려는 반대편이 무엇인가"만 물으면 됩니다. 도구면 MCP, 사람의 편집기면 ACP, 다른 에이전트면 A2A입니다.

---

## 1. MCP 잘 쓰는 법 — 2026-07-28 개정판을 전제로

2026-07-28 개정은 이전 판(2025-11-25)과 **호환이 깨지는 변경**이 많습니다. 예전 튜토리얼을 그대로 따라 하면 이미 폐기 예정인 방식으로 만들게 됩니다. 변경점은 [공식 changelog](https://modelcontextprotocol.io/specification/2026-07-28/changelog)와 [발표 블로그](https://blog.modelcontextprotocol.io/posts/2026-07-28/)에 정리돼 있습니다.

### 1-1. 서버는 무상태로 설계한다

개정판에서 `initialize` 핸드셰이크와 `Mcp-Session-Id` 헤더가 **제거**됐습니다. 프로토콜 버전과 capability는 이제 요청마다 `_meta`에 실려 오고, 서버 능력 조회는 새 RPC `server/discover`가 맡습니다 ([changelog](https://modelcontextprotocol.io/specification/2026-07-28/changelog)).

**규칙 2. 여러 요청에 걸친 상태가 필요하면 "명시적 핸들"을 도구 인자로 주고받는다.** 장바구니 ID나 워크플로 ID 같은 값입니다. 그리고 그 핸들은 **인증 수단이 아니다.** 공식 보안 가이드는 이것을 *State Handle Hijacking*이라고 부르며 다음을 요구합니다 ([Security Best Practices](https://modelcontextprotocol.io/specification/2026-07-28/basic/security_best_practices)).

- 핸들을 가졌다는 사실을 인증으로 취급하면 **안 된다**(MUST NOT).
- 핸들은 보안 난수로 만든다. 순차 ID는 금지다(SHOULD).
- 서버 쪽에서 `<user_id>:<handle>` 처럼 **검증된 토큰에서 뽑은 사용자 ID에 묶는다**(SHOULD). 클라이언트가 보낸 user_id를 믿지 않는다.

```python
# 안티패턴: 핸들만 맞으면 누구든 남의 장바구니를 조작할 수 있다
def add_item(cart_id: str, sku: str): carts[cart_id].append(sku)

# 권장: 토큰에서 온 주체로 키를 만든다
def add_item(ctx, cart_id: str, sku: str):
    key = f"{ctx.verified_user_id}:{cart_id}"   # 클라이언트 입력 아님
    if key not in carts: raise PermissionError
    carts[key].append(sku)
```

**(해석)** 무상태가 되면 서버를 로드밸런서 뒤에 여러 대 띄우기가 쉬워집니다. 대신 "세션이 알아서 막아 주던" 권한 경계를 이제 개발자가 직접 그어야 합니다.

### 1-2. 서버가 되묻는 흐름은 MRTR로

이전에는 서버가 클라이언트에게 먼저 요청(elicitation, sampling, roots)을 보냈습니다. 이제는 **Multi Round-Trip Requests**가 이 역할을 합니다. 서버는 `resultType: "input_required"`로 응답해 추가 입력이 필요하다고 알리고, 클라이언트는 `inputResponses`에 답을 담아 다시 요청합니다 ([changelog](https://modelcontextprotocol.io/specification/2026-07-28/changelog)). 요청 방향이 늘 클라이언트 → 서버 하나뿐이라서 무상태 설계와 맞물립니다.

**규칙 3. 새 서버에 Sampling·Roots·Logging을 쓰지 않는다.** 세 기능은 2026-07-28 기준 **deprecated**입니다. 옛 HTTP+SSE 전송도 마찬가지입니다. 스펙은 최소 12개월 유예를 약속하지만 새 코드를 여기에 얹을 이유는 없습니다 ([changelog](https://modelcontextprotocol.io/specification/2026-07-28/changelog)).

### 1-3. 게이트웨이·WAF와 협업하는 헤더를 활용한다

개정판에서 Streamable HTTP 요청은 `Mcp-Method`, `Mcp-Name` 헤더를 **반드시** 싣습니다. 본문 JSON을 열지 않아도 게이트웨이와 WAF가 "어떤 도구 호출인지"를 보고 라우팅하거나 차단할 수 있다는 뜻입니다 ([changelog](https://modelcontextprotocol.io/specification/2026-07-28/changelog)).

**규칙 4. 위험 도구(삭제·결제·배포)는 게이트웨이에서 `Mcp-Name` 기준으로 따로 정책을 건다.** 레이트 리밋이나 감사 로그 분리가 그 예입니다. **(해석)** 도구 이름을 `delete_*`, `deploy_*` 처럼 정책을 걸기 쉬운 규칙으로 짓는 것이 여기서 이득이 됩니다.

### 1-4. 목록은 캐시한다

`tools/list` 같은 목록 응답에 `ttlMs`와 `cacheScope`가 붙습니다. 변경 알림은 `subscriptions/listen`으로 옮겨졌습니다 ([changelog](https://modelcontextprotocol.io/specification/2026-07-28/changelog)).

**규칙 5. 클라이언트는 매 턴마다 도구 목록을 다시 받지 않는다.** 서버는 도구 목록이 자주 바뀌지 않는다면 TTL을 넉넉히 줍니다. **(해석)** 도구 설명은 결국 모델 컨텍스트에 들어가는 토큰입니다. 도구 수와 설명 길이는 성능 문제이기 전에 비용 문제입니다.

### 1-5. 인증: 토큰을 그대로 흘려보내지 않는다

보안 가이드에서 가장 자주 밟는 지뢰는 **Token Passthrough**입니다. MCP 서버가 클라이언트에게서 받은 토큰을 검증 없이 하위 API로 그대로 넘기는 안티패턴입니다. 스펙은 이를 명시적으로 금지합니다. *"MCP servers MUST NOT accept any tokens that were not explicitly issued for the MCP server."* ([Security Best Practices](https://modelcontextprotocol.io/specification/2026-07-28/basic/security_best_practices))

**규칙 6. 토큰의 audience가 내 서버인지 검증한다. 하위 API용 토큰은 서버가 따로 받는다.** 이 원칙을 어기면 레이트 리밋이나 감사 로그 같은 하위 API의 통제를 우회할 수 있습니다. 로그에 찍힌 주체도 흐려집니다.

2026-07-28 인가 스펙에서 달라진 점도 같이 챙깁니다 ([changelog](https://modelcontextprotocol.io/specification/2026-07-28/changelog)).

- RFC 9207 `iss` 파라미터 검증 (mix-up 공격 방지)
- Dynamic Client Registration은 deprecated → **Client ID Metadata Documents(CIMD)** 권장
- 클라이언트 자격증명은 발급한 issuer에 묶임
- `application_type`으로 CLI 앱의 localhost 리다이렉트 정리

MCP 서버가 서드파티 API 앞의 **프록시** 역할을 하면 *Confused Deputy* 문제도 챙겨야 합니다. 스펙이 요구하는 것은 네 가지입니다. 클라이언트별 동의(per-client consent), `redirect_uri` **정확 일치** 비교(와일드카드 금지), 일회용이고 짧게 만료되는 `state`, 그리고 동의 화면의 iframe 차단입니다 ([Security Best Practices](https://modelcontextprotocol.io/specification/2026-07-28/basic/security_best_practices)).

### 1-6. 클라이언트 쪽: 서버가 주는 URL을 믿지 않는다

MCP 서버가 악의적일 수 있다는 전제를 둡니다. OAuth 메타데이터 탐색 중에 클라이언트는 서버가 준 URL을 받아서 요청합니다. 이 URL이 `169.254.169.254` 같은 클라우드 메타데이터 주소나 사설 대역을 가리키면 **SSRF**가 됩니다. 스펙 권고는 다음과 같습니다 ([Security Best Practices](https://modelcontextprotocol.io/specification/2026-07-28/basic/security_best_practices)).

- OAuth 관련 URL은 HTTPS만 허용한다. http는 loopback 개발용일 때만 허용한다.
- 사설·링크로컬 대역을 차단한다. IP 검증은 **직접 구현하지 말라**고 명시한다(8진수·16진수·IPv4-mapped 우회 때문).
- 리다이렉트를 따라갈 때 매 홉을 다시 검증한다. 서버형 배포라면 egress 프록시를 둔다.
- 인가 URL은 `http(s)`만 허용하고 `javascript:`·`data:`·`file:`은 거부한다. URL을 열 때 **셸을 거치지 않는다**.

### 1-7. 로컬 stdio 서버 = 남의 코드를 내 권한으로 실행하는 것

**규칙 7. "원클릭 MCP 설치"는 곧 임의 코드 실행이다.** 스펙은 로컬 서버를 연결하기 전에 클라이언트가 **실행될 명령 전체를 잘림 없이 보여 주고** 명시적 동의를 받을 것을 요구합니다(MUST). 샌드박스와 최소 권한은 권고(SHOULD)입니다 ([Security Best Practices](https://modelcontextprotocol.io/specification/2026-07-28/basic/security_best_practices)). 서버를 만드는 쪽은 로컬 전용이면 `stdio`를 쓰고, HTTP로 열 거라면 인증 토큰이나 유닉스 소켓으로 접근을 막습니다.

실무 체크리스트로 줄이면 이렇습니다.

- [ ] `npx 무언가`를 설정 파일에 넣기 전에 패키지 출처와 버전을 고정했는가
- [ ] 서버에 넘기는 환경변수(API 키)는 그 서버에 꼭 필요한 것뿐인가
- [ ] localhost HTTP 서버가 인증 없이 떠 있지 않은가 (DNS rebinding 대상)

---

## 2. ACP 잘 쓰는 법 — 에디터와 에이전트를 떼어 놓기

ACP는 **LSP가 언어 서버에 한 일을 코딩 에이전트에 한다**는 목표를 내겁니다. 에이전트가 ACP를 구현하면 호환 에디터 어디서나 쓸 수 있습니다 ([소개](https://agentclientprotocol.com/overview/introduction)). 로컬 에이전트는 에디터의 **서브프로세스**로 뜨고 stdio 위의 JSON-RPC로 통신합니다. 원격 에이전트(HTTP/WebSocket) 지원은 공식 문서가 "진행 중"이라고 적고 있습니다.

지원 에이전트 목록에는 Gemini CLI, Codex CLI(Zed 어댑터), Claude Agent(Zed SDK 어댑터), GitHub Copilot(퍼블릭 프리뷰), Kiro CLI, Goose, OpenHands 등이 있습니다 ([Agents 목록](https://agentclientprotocol.com/overview/agents)). 실제로 이 글을 쓰는 맥의 `kiro-cli`에도 `acp` 서브커맨드가 들어 있습니다(`kiro-cli acp --help` → *"Start Agent Client Protocol (ACP) agent"*).

### 2-1. stdout은 프로토콜 전용이다

**규칙 8. ACP 에이전트는 stdout에 ACP 메시지 말고 아무것도 쓰지 않는다.** 로그와 진행 표시는 stderr로 보냅니다 ([Transports](https://agentclientprotocol.com/protocol/transports)). 디버그 `print` 한 줄이면 에디터가 JSON 파싱에 실패해 세션이 통째로 죽습니다. **(해석)** 직접 에이전트를 만들 때 가장 흔한 첫 버그입니다. MCP stdio 서버도 똑같은 함정을 가집니다.

### 2-2. MCP 서버 목록은 에디터가 넘긴다

`session/new`의 파라미터는 작업 디렉터리(`cwd`)와 **에이전트가 붙을 MCP 서버 목록**입니다 ([Session Setup](https://agentclientprotocol.com/protocol/session-setup)).

```json
{
  "jsonrpc": "2.0", "id": 1, "method": "session/new",
  "params": {
    "cwd": "/home/user/project",
    "mcpServers": [
      { "name": "filesystem", "command": "/path/to/mcp-server", "args": ["--stdio"], "env": [] }
    ]
  }
}
```

**규칙 9. MCP 설정을 에이전트마다 따로 두지 말고 에디터 한 곳에서 관리한다.** 에이전트를 바꿔 끼워도 같은 도구 세트가 따라옵니다. **(해석)** "에이전트 A에선 되는데 B에선 안 된다"의 원인 중 상당수는 모델이 아니라 설정 차이입니다. 설정을 한 곳에 모으면 비교 실험도 공정해집니다.

세션을 다시 이어 붙이는 방법은 두 가지이고, 둘 다 capability 협상이 먼저입니다. `session/load`는 대화 이력을 `session/update`로 **전부 재생**하고, `session/resume`은 재생 없이 이어 붙입니다. 클라이언트는 `initialize` 응답에서 `loadSession`이나 `sessionCapabilities.resume`을 확인한 **뒤에만** 호출해야 합니다(MUST) ([Session Setup](https://agentclientprotocol.com/protocol/session-setup)).

### 2-3. 권한 요청은 "사람이 보는 마지막 관문"으로 설계한다

에이전트는 도구 실행 전에 `session/request_permission`으로 사용자 허락을 받을 수 있습니다. 선택지는 `allow_once` / `allow_always` / `reject_once` / `reject_always`입니다. 도구 호출에는 `kind`(`read`·`edit`·`delete`·`execute`·`fetch` 등)가 붙습니다 ([Tool Calls](https://agentclientprotocol.com/protocol/tool-calls)).

**규칙 10. `kind`로 자동 승인 범위를 나눈다.** 예를 들면 `read`·`search`는 자동 승인하고, `edit`는 diff를 보여 준 뒤 승인하고, `delete`·`execute`는 매번 묻습니다. 스펙은 클라이언트가 사용자 설정에 따라 자동 허용하거나 거부해도 된다고(MAY) 열어 두었습니다. 그래서 **어디까지 자동으로 둘지는 도구를 쓰는 쪽의 책임**입니다. 턴이 취소되면 클라이언트는 대기 중인 권한 요청에 반드시 `cancelled`로 답해야 합니다(MUST). 이걸 빼먹으면 에이전트가 영원히 기다립니다.

**규칙 11. 파일 수정은 `diff` 콘텐츠로 보고하게 한다.** ACP 도구 호출 결과에는 `path`/`oldText`/`newText`를 담는 diff 타입과, 실시간 출력을 보여 주는 `terminal` 타입이 있습니다 ([Tool Calls](https://agentclientprotocol.com/protocol/tool-calls)). 사람이 검토할 수 있는 형태로 보고하는 에이전트를 고르거나 그렇게 만듭니다.

---

## 3. 흔한 안티패턴 요약

| 안티패턴 | 왜 문제인가 | 대신 |
|---|---|---|
| 클라이언트 토큰을 하위 API로 그대로 전달 | 스펙 명시 금지, 통제 우회·감사 불능 | audience 검증 + 서버 자체 토큰 |
| 순차 ID를 상태 핸들로 사용 | 추측 가능 → 남의 상태 조작 | 보안 난수 + 사용자 바인딩 |
| 새 서버에 Sampling·SSE 전송 사용 | 2026-07-28 deprecated | MRTR, Streamable HTTP |
| 서버가 준 OAuth URL을 셸로 열기 | RCE·XSS 경로 | 스킴 allowlist, 비셸 오프너 |
| stdio 에이전트/서버의 stdout 디버그 출력 | 프로토콜 스트림 오염 | stderr |
| 에이전트마다 MCP 설정 중복 | 설정 드리프트, 비교 불가 | ACP `session/new`로 에디터가 전달 |
| 모든 도구 호출 자동 승인 | 삭제·실행도 무검토 | `kind`별 승인 정책 |
| IBM ACP로 신규 설계 | A2A로 합류 완료 | A2A |

---

## 4. 아직 안 풀린 것

- **원격 ACP**: 공식 문서 스스로 "full support is a work in progress"라고 적고 있습니다. 클라우드에 띄운 에이전트를 에디터에 붙이는 표준 경로는 아직 확정되지 않았습니다.
- **MCP 마이그레이션 부담**: 세션 제거와 MRTR 전환은 기존 서버에 코드 변경을 요구합니다. deprecated 기능의 유예는 *최소* 12개월이라는 약속만 있고, 실제 제거 시점은 스펙이 정하지 않았습니다.
- **도구 설명 자체를 통한 공격**: 도구 설명이나 결과에 숨긴 지시로 모델을 조종하는 문제는 프로토콜 필드로 막을 수 없습니다. 위의 보안 가이드도 인가·전송·로컬 실행 위주입니다. **(해석)** 결국 최후 방어선은 2-3의 사람 승인과 최소 권한입니다.
- **중립적 비교 부재**: 어느 에이전트나 어느 MCP 서버가 "더 낫다"는 중립 제3자 헤드투헤드 벤치마크는 찾지 못했습니다. 이 글은 성능 우열을 주장하지 않습니다.

---

## 요약

1. **이름부터 확인**: ACP = Agent Client Protocol(에디터↔에이전트). 에이전트끼리는 A2A.
2. **MCP는 무상태**: 세션 대신 핸들을 쓰되 핸들은 인증이 아니다. 되묻기는 MRTR, 목록은 캐시한다.
3. **MCP 보안 3대 원칙**: 토큰 패스스루 금지, 서버가 준 URL 불신(SSRF·스킴), 로컬 서버 설치는 코드 실행과 같다.
4. **ACP는 경계 설계**: stdout은 프로토콜 전용, MCP 설정은 에디터 한 곳에서, 권한은 `kind`별로.

---

## References

**1차·공식 (사실로 인용)**

- Model Context Protocol, *Specification 2026-07-28*. <https://modelcontextprotocol.io/specification/2026-07-28>
- Model Context Protocol, *Changelog (2026-07-28)*. <https://modelcontextprotocol.io/specification/2026-07-28/changelog>
- Model Context Protocol, *Security Best Practices (2026-07-28)*. <https://modelcontextprotocol.io/specification/2026-07-28/basic/security_best_practices>
- D. Soria Parra, D. Delimarsky, *MCP 2026-07-28 release post*, MCP Blog. <https://blog.modelcontextprotocol.io/posts/2026-07-28/>
- modelcontextprotocol, *Release 2026-07-28*, GitHub. <https://github.com/modelcontextprotocol/modelcontextprotocol/releases/tag/2026-07-28>
- Agent Client Protocol, *Introduction*. <https://agentclientprotocol.com/overview/introduction>
- Agent Client Protocol, *Architecture*. <https://agentclientprotocol.com/overview/architecture>
- Agent Client Protocol, *Session Setup*. <https://agentclientprotocol.com/protocol/session-setup>
- Agent Client Protocol, *Transports*. <https://agentclientprotocol.com/protocol/transports>
- Agent Client Protocol, *Tool Calls*. <https://agentclientprotocol.com/protocol/tool-calls>
- Agent Client Protocol, *Agents*. <https://agentclientprotocol.com/overview/agents>
- agentclientprotocol/agent-client-protocol, GitHub. <https://github.com/agentclientprotocol/agent-client-protocol>
- LF AI & Data, *ACP Joins Forces with A2A under the Linux Foundation* (2025-08-29). <https://lfaidata.foundation/communityblog/2025/08/29/acp-joins-forces-with-a2a-under-the-linux-foundations-lf-ai-data/>
- IBM Research, *Agent Communication Protocol*. <https://research.ibm.com/projects/agent-communication-protocol>
- Linux Foundation, *Linux Foundation Launches the Agent2Agent Protocol Project* (2025-06-23). <https://www.linuxfoundation.org/press/linux-foundation-launches-the-agent2agent-protocol-project-to-enable-secure-intelligent-communication-between-ai-agents>
- IETF, *RFC 9207 — OAuth 2.0 Authorization Server Issuer Identification*. <https://www.rfc-editor.org/rfc/rfc9207>

**중립 제3자 비교**: 없음 (본문 4절 참조)
