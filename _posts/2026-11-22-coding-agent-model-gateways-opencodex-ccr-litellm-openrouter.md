---
layout: post
title: "코딩 에이전트 앞에 끼우는 모델 게이트웨이 4종 — opencodex · claude-code-router · LiteLLM · OpenRouter"
date: 2026-11-22 18:02:57 +0900
categories: [ai, devtools]
tags: [opencodex, claude-code-router, LiteLLM, OpenRouter, LLM-gateway, Claude-Code, Codex]
---

## 한 줄 요약

네 개 다 하는 일은 하나다. **코딩 에이전트와 모델 사이에 끼어서 요청을 다른 곳으로 보낸다.** 다른 건 *어디서 도느냐*다.

| 이름 | 어디서 도나 | 기본 주소 |
| --- | --- | --- |
| [opencodex](https://github.com/lidge-jun/opencodex) | 내 PC (데스크톱 게이트웨이) | `localhost:10100` |
| [claude-code-router](https://github.com/musistudio/claude-code-router) (CCR) | 내 PC (데스크톱 게이트웨이) | `127.0.0.1:3456` |
| [LiteLLM](https://github.com/BerriAI/litellm) | 내 서버 (조직용 셀프호스트) | 예시 `:4000` |
| [OpenRouter](https://openrouter.ai) | 남의 서버 (관리형 SaaS) | `https://openrouter.ai/api` |

어디서 도느냐에 따라 **키가 어디에 모이고 로그가 어디에 쌓이는지**가 정해진다. 결국 그게 고르는 기준이 된다.

---

## 1. 왜 이런 계층이 생겼나

코딩 에이전트는 저마다 특정 API 형식에 묶여 있다. Claude Code 는 Anthropic Messages, Codex 는 OpenAI Responses 형식으로 말한다. 그런데 대부분의 에이전트는 **base URL 을 바꿀 수 있게** 열어 둔다. Claude Code 라면 `ANTHROPIC_BASE_URL` 하나다.

이 한 줄을 다른 주소로 돌리면 그 사이에 무엇이든 끼울 수 있다. 끼운 쪽이 요청 형식을 번역하면 *에이전트 화면은 그대로 두고 뒤의 모델만 바꾸는* 일이 가능해진다.

Anthropic 공식 문서는 게이트웨이가 주는 이점을 다섯 가지로 정리한다([Claude Code docs, Other LLM gateways](https://code.claude.com/docs/en/llm-gateway)).

- 자격증명 중앙화
- 사용량 귀속
- 비용 통제
- 감사 로그
- 프로바이더 전환

같은 문서에 단서도 붙어 있다. 게이트웨이는 *조직이 운영해야 하는 인프라*가 된다. 그리고 Claude Code 가 새 기능을 낼 때마다 게이트웨이가 그걸 전달하지 못하면 그 기능이 깨진다.

## 2. 데스크톱 게이트웨이: opencodex 와 CCR

둘 다 *개인 PC 에 띄우는 로컬 프록시 + 대시보드*다. 성격도 비슷하다.

### opencodex

README 의 정의는 "코딩 도구와 모델 프로바이더 사이의 가벼운 로컬 게이트웨이"다([README](https://github.com/lidge-jun/opencodex)).

- **번역하는 프로토콜:** OpenAI Responses, Chat Completions, Anthropic Messages 세 가지를 받아 각 프로바이더 형식으로 바꾼다. 스트리밍, 도구 호출, 추론, 이미지도 *클라이언트·모델·프로바이더가 지원하는 범위에서* 넘긴다.
- **설치와 연결:** `npm install -g @bitkyc08/opencodex` 후 `ocx start` 를 하면 `localhost:10100` 에 프록시와 대시보드가 뜬다. Claude Code 는 `ocx claude` 로 붙인다.
- **라우팅:** `provider/model` 문법으로 고른다(예: `codex -m "ollama/llama3"`). **Combos** 는 가상 모델 ID 하나 뒤에 여러 프로바이더를 두고 장애 조치나 가중 라운드로빈을 건다.
- **보안 기본값:** 기본은 `127.0.0.1` 에만 바인딩한다. 루프백 밖으로 열면 `OPENCODEX_API_AUTH_TOKEN` 이 없을 때 아예 시작을 거부한다.
- **정리:** `ocx stop` 은 Codex 설정을 원래대로 되돌린다고 README 에 적혀 있다.
- **텔레메트리:** 익명 일일 사용 요약을 보낸다. 공지를 보고 거부하지 않은 경우에만 보내고, `ocx telemetry disable` 이나 `DO_NOT_TRACK=1` 로 끈다.

README 의 "40개 이상 프로바이더"는 **프로젝트 자체 주장**이고, 이 글에서 전부 확인하지는 않았다.

### claude-code-router (CCR)

이름은 Claude Code 용 같지만 지금은 범위가 훨씬 넓다. README 는 스스로를 "코딩 에이전트를 위한 로컬 모델 게이트웨이이자 컨트롤 플레인"이라고 소개한다([README](https://github.com/musistudio/claude-code-router)).

- **붙는 에이전트:** Claude Code, Codex, Grok CLI, Kimi CLI, Kilo Code, OpenCode 등 10종에 프로필을 적용한다.
- **포트:** 모델 게이트웨이는 `127.0.0.1:3456`, 관리 UI 는 `:3458` 이다. 데스크톱 앱(Electron)과 npm CLI(Node 22 이상) 두 가지로 제공한다.
- **라우팅:** 헤더·본문 조건 라우팅, 접두사, 요청 재작성, 재시도, 순서 있는 폴백 모델을 지원한다. 자격증명 풀과 키 로테이션도 있다.
- **기능 덧붙이기:** "Fusion" 으로 비전이나 웹 검색이 없는 모델에 그 기능을 붙인다. MCP 도구 허브와 브라우저 자동화도 들어 있다.
- **관측:** 요청마다 실제로 해석된 프로바이더·모델·자격증명, 지연, 토큰, 추정 비용을 로그로 남긴다.

### 둘의 차이

방향은 거의 같고 출발점이 다르다. opencodex 는 이름처럼 **Codex 쪽에서** 출발했다. ChatGPT 계정 풀, Codex 서브에이전트 피커 같은 Codex 특화 기능이 두껍다. CCR 은 **Claude Code 쪽에서** 출발해 *에이전트 전체의 컨트롤 플레인*으로 넓어졌다.

2026-11-22 GitHub API 기준 스타는 CCR 약 3.8만, opencodex 약 1.9만이다. opencodex 리포는 2026년 6월에 만들어져 반년이 채 안 됐다. 둘 다 MIT 라이선스다.

## 3. 조직용 셀프호스트: LiteLLM

LiteLLM 은 앞의 둘보다 한 층 위에 있다. *개인 PC 의 편의 도구*보다는 **팀이나 조직이 서버에 띄우는 AI 게이트웨이**에 가깝다.

리포 설명은 "100개 이상 LLM API 를 OpenAI(또는 네이티브) 형식으로 호출하고 비용 추적·가드레일·부하분산·로깅을 제공한다"이다([GitHub](https://github.com/BerriAI/litellm)).

Claude Code 연결은 공식 튜토리얼이 있다([LiteLLM docs, Claude Code Quickstart](https://docs.litellm.ai/docs/tutorials/claude_responses_api)).

```bash
uv tool install 'litellm[proxy]'
litellm --config config.yaml          # 예시: http://0.0.0.0:4000
export ANTHROPIC_BASE_URL="http://0.0.0.0:4000"
export ANTHROPIC_AUTH_TOKEN="$LITELLM_KEY"   # 마스터 키 또는 가상 키
```

데스크톱 게이트웨이와 갈리는 지점은 **가상 키**다. 개발자마다 접근할 모델이 제한된 키를 따로 발급하고, 사용량을 그 키 단위로 귀속시킨다. 앞서 본 Anthropic 공식 문서의 롤아웃 절차와 같은 모양이다. 공식 문서도 "개발자마다 게이트웨이 자격증명을 발급해서, 퇴사 처리가 키 하나 회수로 끝나게 하라"고 권한다([Claude Code docs](https://code.claude.com/docs/en/llm-gateway)).

이 블로그에서도 LiteLLM 을 직접 운영한 기록이 있다.

- [모델 추가 함정 네 가지]({% post_url 2026-09-04-litellm-add-model-four-traps %})
- [Opik 과 묶은 관측성]({% post_url 2026-09-05-litellm-gateway-opik-observability %})
- [공급망 사고 뒤 걷어낸 이유]({% post_url 2026-10-26-litellm-supply-chain-decommission %})

## 4. 관리형 SaaS: OpenRouter

OpenRouter 는 서버를 아예 띄우지 않는다. 남이 운영하는 게이트웨이에 키 하나로 붙는 방식이다.

Claude Code 연동은 OpenRouter 공식 문서에 나와 있다([OpenRouter docs, Claude Code Integration](https://openrouter.ai/docs/guides/guides/claude-code-integration)).

```bash
export ANTHROPIC_BASE_URL="https://openrouter.ai/api"
export ANTHROPIC_AUTH_TOKEN="$OPENROUTER_API_KEY"
export ANTHROPIC_API_KEY=""   # 반드시 빈 값
```

문서가 짚는 함정은 세 가지다.

- **`ANTHROPIC_API_KEY` 는 비워야 한다.** 이 값은 `x-api-key` 로 나가고 Anthropic 직결 자격증명으로 취급된다. 비워 두지 않으면 Anthropic 으로 직접 인증하려는 폴백이 생긴다.
- **예전 Anthropic 로그인이 남아 있으면 `/logout` 을 한 번 해야 한다.** 남아 있으면 모델을 못 찾는다는 식의 엉뚱한 에러가 난다.
- **동작 보장은 Anthropic 1st-party 프로바이더뿐이다.** Claude Code + OpenRouter 조합은 그 경우만 보장된다고 명시돼 있다.

OpenRouter 가 내세우는 이점은 여러 Anthropic 프로바이더 사이의 장애 조치, 조직 예산 한도, 사용량 대시보드다. 모두 **벤더 설명**이다.

관련 글: [OpenRouter 무료 모델 비교]({% post_url 2026-09-17-openrouter-free-models-what-you-get %}), [DeepSeek Harness 를 OpenRouter 에 물리는 두 길]({% post_url 2026-11-21-deepseek-harness-on-openrouter-two-paths %}).

## 5. 한눈에 비교

| | opencodex | CCR | LiteLLM | OpenRouter |
| --- | --- | --- | --- | --- |
| 형태 | 로컬 프록시+대시보드 | 로컬 프록시+데스크톱 앱 | 셀프호스트 서버 | 관리형 SaaS |
| 주 사용자 | 개인 | 개인 | 팀·조직 | 개인~조직 |
| 출발점 | Codex | Claude Code | 범용 SDK·프록시 | 범용 API 마켓 |
| 프로바이더 키 위치 | 내 PC | 내 PC | 내 서버 DB | 내 키 불필요(OpenRouter 키 하나) |
| 요청 로그 위치 | 내 PC | 내 PC | 내 서버 | OpenRouter |
| 사용자별 키 | 없음(루프백 기본) | CCR 클라이언트 키 | 가상 키 | OpenRouter 키 |
| 운영 부담 | 낮음 | 낮음 | 높음 | 없음 |

## 6. 끼우기 전에 알아야 할 것

### ① Anthropic 은 "Claude 가 아닌 모델로 라우팅"을 지원하지 않는다

공식 문서는 Anthropic 이 서드파티 게이트웨이를 보증·유지·감사하지 않는다고 적는다. 그리고 *어떤 게이트웨이를 거치든 Claude Code 를 Claude 가 아닌 모델로 보내는 것*은 지원하지 않는다고 명시한다([Claude Code docs](https://code.claude.com/docs/en/llm-gateway)).

opencodex 와 CCR 의 핵심 기능이 바로 이 일이다. 돌아가더라도 그건 *지원 범위 밖에서 돌아가는* 것이다.

### ② 구독 로그인과 게이트웨이 키는 과금이 다르다

게이트웨이 자격증명(`ANTHROPIC_AUTH_TOKEN` 등)이 활성화돼 있으면 요청에 claude.ai 구독 로그인 대신 그 키가 실린다. 사용량은 **그 키 주인에게 토큰 단위로 과금**된다.

반대로 `ANTHROPIC_BASE_URL` 만 바꾸고 자격증명을 안 넣으면, 요청은 게이트웨이를 거치지만 구독 로그인이 그대로 쓰인다([Claude Code docs](https://code.claude.com/docs/en/llm-gateway)). "게이트웨이를 끼웠으니 구독 한도와 무관하다"는 생각은 설정에 따라 틀린다.

### ③ 1st-party 가 아닌 주소면 꺼지는 기능이 있다

LiteLLM 문서에 따르면, Claude Code 는 `ANTHROPIC_BASE_URL` 이 Anthropic 1st-party 호스트가 아니면 **도구 검색(tool search)을 끈다.** 그러면 MCP 도구 스키마가 전부 컨텍스트에 인라인으로 들어간다. `ENABLE_TOOL_SEARCH=true` 로 다시 켤 수 있다고 한다([LiteLLM docs](https://docs.litellm.ai/docs/tutorials/claude_responses_api)).

게이트웨이가 새 헤더나 새 기능을 전달하지 못해 조용히 깨지는 경우도 있다. Anthropic 문서가 말한 *게이트웨이를 계속 업데이트해야 한다*는 단서가 이 얘기다.

### ④ 프로바이더 약관

opencodex README 의 면책 문구는 일부 프로바이더, 특히 Anthropic 이 서드파티 프록시로 API 트래픽을 보내는 계정을 정지하거나 제한할 수 있다고 경고한다. 연결 전에 각 약관을 확인하라고 적는다([README, Disclaimer](https://github.com/lidge-jun/opencodex)).

ChatGPT 계정 풀 기능에도 별도 경고가 붙어 있다. 추가 계정으로 한도를 우회하는 걸 보증하지 않는다는 내용이다.

### ⑤ 게이트웨이는 키 금고다 — 그래서 표적이 된다

가장 무거운 얘기다. 게이트웨이는 구조적으로 **모든 프로바이더 키와 모든 요청·응답 로그가 모이는 자리**다.

LiteLLM 은 2026년에 공급망 사고를 두 번 겪었다.

- **3월:** CI 의 보안 스캐너 의존성을 통해 악성 `1.82.7`/`1.82.8` 이 PyPI 에 올라갔다([LiteLLM 공지, 2026-03](https://docs.litellm.ai/blog/security-update-march-2026)).
- **10월 21일:** 릴리스 파이프라인이 뚫려 자격증명을 훔치는 `1.107.0` 이 PyPI 와 Docker 이미지로 배포됐다([LiteLLM 공지, 2026-10-21](https://docs.litellm.ai/blog/security-incident-oct-21-2026); [GitHub Advisory GHSA-92x9-889m-jgmw](https://github.com/advisories/GHSA-92x9-889m-jgmw)).

Microsoft 분석에 따르면 10월의 악성 패키지는 import 하지 않아도 *Python 을 시작하기만 하면* 실행됐다. 그리고 LiteLLM 프록시 DB 에서 자격증명과 모델 설정 레코드를 읽으려 했다([Microsoft Security Blog, 2026-10-23](https://www.microsoft.com/en-us/security/blog/2026/10/23/inside-the-litellm-1-107-0-supply-chain-compromise-credential-theft-through-python-startup-hooks/)).

LiteLLM 공지의 진입 경로 설명은 더 직접적이다(공지 스스로 조사 중 작성돼 일부 부정확할 수 있다고 밝혔다).

1. 공개 인터넷에 노출된 내부 LiteLLM 배포에 공격자가 접근했다고 본다.
2. 그 **로그**에서 개발자들의 GitHub CLI OAuth 토큰을 얻었다.
3. 그 토큰으로 릴리스 워크플로를 장악했다.

공지는 Claude Code 가 특정 상황에서 사용자의 GitHub CLI OAuth 토큰을 응답 본문에 넣는 경우를 관찰했다고도 적었다.

게이트웨이를 끼운다는 건 결국 **키와 대화 로그를 한 곳에 모은다**는 뜻이다. 그 한 곳의 보안이 곧 전체의 보안이 된다. 이렇게 정리할 수 있다.

- **로컬 게이트웨이**(opencodex, CCR): 피해 범위가 내 PC 로 좁다. 대신 PC 가 털리면 전부 털린다.
- **셀프호스트**(LiteLLM): 버전 고정, 이미지 digest 고정, 로그 보존 정책이 필수다.
- **SaaS**(OpenRouter): 이 책임을 벤더에 맡기는 대신, 내 요청이 남의 서버를 지나간다.

## 7. 고르는 법

- **혼자, 여러 모델을 써 보고 싶다** → opencodex 나 CCR. Codex 를 주로 쓰면 opencodex, 여러 에이전트를 한 화면에서 관리하고 싶으면 CCR 쪽이 문서상 맞는다.
- **서버를 띄우기 싫고 키 하나로 끝내고 싶다** → OpenRouter. 단, Claude Code 와 쓸 거면 Anthropic 1st-party 를 최우선 프로바이더로 둔다.
- **팀에 배포하고 사용량·비용·감사를 쥐어야 한다** → LiteLLM 같은 셀프호스트. 운영할 사람과 업데이트 책임이 있어야 한다.
- **Claude 만 쓴다** → 게이트웨이가 꼭 필요한지부터 따진다. Anthropic 은 자체 게이트웨이(Claude apps gateway)도 문서화해 두었다([Claude Code docs](https://code.claude.com/docs/en/llm-gateway)).

## 근거의 한계

- **직접 실행하지 않았다.** 네 도구의 기능 설명은 각 README·공식 문서 기준이다. 이 글을 쓰며 설치해 돌려 보지 않았다. "40+ 프로바이더", 장애 조치 품질 같은 주장은 **프로젝트·벤더 주장**이다.
- **중립 비교가 없다.** 네 게이트웨이의 지연·안정성·호환성을 같은 조건에서 잰 중립 제3자 헤드투헤드는 찾지 못했다.
- **스타 수는 스냅샷이다.** 2026-11-22 GitHub API 조회값이고, 인기를 보여 줄 뿐 품질 지표는 아니다.
- **사고 경위는 진행 중 기록이다.** LiteLLM 10월 사고의 진입 경로 설명은 LiteLLM 공지 기준이고, 공지 스스로 일부 내용이 나중에 부정확하거나 불완전한 것으로 밝혀졌다고 적었다.
- **문서는 빨리 바뀐다.** 넷 다 업데이트가 매우 잦다(opencodex·CCR·LiteLLM 모두 조회 시점 하루 이내 push). 포트, 명령어, 지원 목록은 쓰기 전에 각 문서에서 다시 확인해야 한다.

## References

1. Anthropic, *Other LLM gateways*, Claude Code Docs. <https://code.claude.com/docs/en/llm-gateway>
2. lidge-jun, *opencodex* README (MIT). <https://github.com/lidge-jun/opencodex> · 문서 <https://opencodex.me/>
3. musistudio, *claude-code-router* README (MIT). <https://github.com/musistudio/claude-code-router> · 문서 <https://ccrdesk.top/>
4. BerriAI, *LiteLLM*. <https://github.com/BerriAI/litellm>
5. LiteLLM, *Claude Code Quickstart*. <https://docs.litellm.ai/docs/tutorials/claude_responses_api>
6. OpenRouter, *Claude Code Integration*. <https://openrouter.ai/docs/guides/guides/claude-code-integration>
7. LiteLLM, *Security Update: Suspected Supply Chain Incident*, 2026-03-24. <https://docs.litellm.ai/blog/security-update-march-2026>
8. LiteLLM, *Contained: Oct 21, 2026 LiteLLM release v1.107.0 Compromised*. <https://docs.litellm.ai/blog/security-incident-oct-21-2026>
9. GitHub Advisory Database, *GHSA-92x9-889m-jgmw: Malicious code in litellm (PyPI)*. <https://github.com/advisories/GHSA-92x9-889m-jgmw>
10. Microsoft Security Blog, *Inside the LiteLLM 1.107.0 supply chain compromise*, 2026-10-23. <https://www.microsoft.com/en-us/security/blog/2026/10/23/inside-the-litellm-1-107-0-supply-chain-compromise-credential-theft-through-python-startup-hooks/>
