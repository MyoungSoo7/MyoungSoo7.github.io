---
layout: post
title: "DeepSeek Harness 를 OpenRouter 에 물리는 두 길 — ori dsh 와 커스텀 프로바이더, 그리고 소스에 적힌 함정들"
date: 2026-11-21 09:42:20 +0900
categories: [AI, Agent]
tags: [deepseek, harness, dsh, openrouter, ori, llm-gateway, agent]
---

DeepSeek Harness(`dsh`)는 이름에 DeepSeek 가 들어가 있지만 모델을 가리지 않는다. OpenRouter 는 모델 수백 개를 API 하나로 묶어 준다. 둘을 붙이면 하네스 하나로 여러 회사 모델을 바꿔 가며 돌릴 수 있다. 그래서 이 조합을 다룬 설정 가이드와 영상이 8월 이후 꽤 나왔다.

이 글은 붙이는 방법 두 가지를 정리하고, 붙인 뒤 무엇이 깨지는지를 짚는다. 근거는 두 회사의 공식 문서와 `deepseek-ai/deepseek-harness` 리포 소스다. 리포는 커밋 `2e39e70`(2026-11-18)을 클론해 읽었다. DSH 자체를 돌려 본 이야기는 [9월 체험기]({% post_url 2026-09-17-deepseek-harness-hands-on-postmortems-and-session-log-upload %})에, 비용 구조는 [9월 비용 글]({% post_url 2026-09-25-deepseek-harness-api-cost-kv-cache %})에 있다.

## 한 줄 요약

`ori dsh` 한 줄로 OAuth 로그인부터 모델 목록까지 OpenRouter 쪽이 다 채워 준다. 직접 붙일 때는 커스텀 프로바이더를 등록한다. 어느 쪽이든 **요청 형식 호환 설정**과 **DeepSeek 모델의 thinking 기본값**은 알고 있어야 한다.

## 두 물건이 각각 무엇인가

**DeepSeek Harness.** DeepSeek 이 2026-08-13 개발자 프리뷰(v0.1)로 공개한 MIT 라이선스 에이전트 하네스다. 설계 원칙은 "everything is a plugin" 이다. Cordis 프레임워크 위에서 모델 어댑터, 도구 레지스트리, 세션 로그, 에이전트 루프까지 전부 플러그인이라 설정으로 갈아 끼울 수 있다 ([아키텍처 문서](https://deepseek-harness.github.io/deepseek-harness/en/reference/)). 실행은 `npx @deepseek-ai/dsh web` 이고, 웹 UI 가 `127.0.0.1:3080` 에 뜬다. README 는 대문자로 호환성을 깨는 변경이 있을 거라고 경고한다 ([README](https://github.com/deepseek-ai/deepseek-harness)).

DeepSeek 은 같은 날 V4-Pro 정식판을 내면서, 코드 에이전트 벤치마크를 **DSH 의 최소(Minimal) 모드를 프레임워크로 써서** 쟀다고 각주에 적었다. 다른 프레임워크에서는 결과가 조금 다를 수 있다는 단서도 붙였다 ([DeepSeek API 공지, 중문](https://api-docs.deepseek.com/zh-cn/news/news260813.md)). 이 하네스는 DeepSeek 모델에 맞춰 다듬어졌다는 뜻이다. 다른 모델을 끼우면 행동이 달라질 수 있다.

**OpenRouter.** 여러 모델 회사의 API 를 하나의 OpenAI 호환 API 로 묶은 게이트웨이다. 추론 단가는 원 제공자 가격을 그대로 받고 마크업이 없다. 대신 크레딧을 충전할 때 5.5%(최소 $0.80) 수수료를 뗀다. 자기 제공자 키를 쓰는 BYOK 는 플랜별 무료 한도를 넘으면 5% 를 받는다 ([OpenRouter FAQ](https://openrouter.ai/docs/faq)). 무료 모델에 대해서는 [9월 글]({% post_url 2026-09-17-openrouter-free-models-what-you-get %})에서 따로 다뤘다.

## 길 1 — `ori dsh`

OpenRouter 의 Ori Harness 는 이미 쓰는 에이전트 CLI 를 OpenRouter 자격증명과 함께 띄워 주는 런처다. Claude Code, Codex 를 비롯한 여러 에이전트를 지원하고 DSH 도 그중 하나다 ([Ori Harness 문서](https://openrouter.ai/docs/guides/ori/harness)).

다만 DSH 는 이 목록에서 유일한 예외다. 다른 CLI 처럼 켜고 끄는 프로그램이 아니라 웹 서버라서, `ori dsh` 는 DSH 를 **실행하지 않고 설정만 한다.** 전역 DSH 설정이 OpenRouter 를 바라보게 바꿔 두고, 그다음은 평소처럼 `dsh` 를 돌리면 된다. `--model` 을 주면 기본 모델만 바꾸고 아무것도 띄우지 않는다.

로그인은 OAuth PKCE 다. 새 키를 만들어 붙여 넣을 필요가 없다. Ori 로 띄운 DSH 에서는 다음을 쓸 수 있다.

- `/model` 목록이 내 OpenRouter 카탈로그에서 오고, 조직 정책이 막은 모델은 빠진다.
- `/fast` 로 빠른 라우팅을 켠다.
- `/zdr` 로 데이터를 보관하지 않는 제공자에게만 요청을 보낸다.

조직 단위로 걸어 둔 허용 모델 목록과 예산 상한도 모든 요청에 적용된다.

**문서끼리 어긋나는 점 하나.** 같은 OpenRouter 의 DSH 소개 페이지 Q&A 는 `ori dsh` 가 설정 후 `dsh web` 을 **띄우고 URL 을 출력한다**고 쓴다. 이 경우 OpenRouter 자격증명은 그 서버에만 전달되므로, 손으로 띄운 `dsh web` 에는 별도 키가 필요하다고도 적는다 ([ori dsh 페이지](https://openrouter.ai/ori/harness/dsh)). 문서 가이드는 "설정만 한다"고 쓰고, 소개 페이지는 "띄운다"고 쓴다. 이 글에서는 어느 쪽이 현재 동작인지 직접 돌려 확인하지 않았다. 쓰기 전에 `ori --help` 와 실제 출력으로 확인하길 권한다.

## 길 2 — 커스텀 모델 API 로 직접 등록

Ori 없이 붙이는 방법은 DSH 공식 사용자 가이드에 있다 ([providers 가이드](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/user/guide/providers.md)). **Settings → Models → Add model provider** 에서 카드를 **Custom model API** 로 바꾸고 다음을 넣는다.

| 필드 | 값 |
| --- | --- |
| Provider ID | `openrouter` (소문자) |
| Base URL | `https://openrouter.ai/api/v1` |
| API protocol | OpenAI Chat Completions (`openai-completions`) |
| API key | OpenRouter 키 |
| 모델 | `deepseek/deepseek-v4-flash` 처럼 회사 접두어가 붙은 OpenRouter 슬러그 |

가이드가 강조하는 규칙들이 있다.

- **Provider ID 는 영구적이다.** 요청, 저장된 세션, 기본 모델, 자격증명 참조가 모두 이 ID 를 쓴다. 이름을 바꾸려면 새로 만들고 옛것을 지워야 한다.
- **프로토콜은 하나만.** 게이트웨이가 OpenAI 형식과 Anthropic 형식을 둘 다 받으면 프로바이더를 두 개 등록해야 한다.
- **Fetch available models 는 편의 기능이다.** 실패하거나 빈 목록이 오면 ID 를 손으로 넣으면 똑같이 동작한다. 내장 프로바이더는 base URL 을 게이트웨이로 바꿔도 설치된 카탈로그로 답한다. 게이트웨이가 실제로 무엇을 서빙하는지 보려면 커스텀 프로바이더로 조회해야 한다.
- **키는 쓰기 전용이다.** `$DSH_HOME/.credentials.yaml` 에 저장되고, 설정 파일에는 참조만 남는다. 저장한 뒤에는 UI 에서도 다시 꺼내 볼 수 없다.

설정 파일 위치는 2차 가이드마다 다르게 적혀 있다. 공식 가이드 기준으로는 `$DSH_HOME/profiles/<profile>/cordis.patch.yml` 이다. `dsh web` 으로 띄웠다면 `<profile>` 은 `web` 이다. 어댑터가 요청마다 이 파일을 다시 읽으므로 재시작은 필요 없다.

## 붙인 뒤 깨지는 것들 — 소스와 문서에 적힌 함정

### 1. 키도 주소도 맞는데 모든 요청이 거절된다

DSH 의 범용 어댑터(pi-ai)는 요청 형식을 **엔드포인트 URL 로 판단한다.** 모르는 주소는 OpenAI 본가로 간주하고 OpenAI 형식으로 보낸다. 그러면 OpenAI 와 조금이라도 다른 게이트웨이는 전부 거절한다. 공식 가이드가 꼽는 원인은 두 가지다 ([providers 가이드](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/user/guide/providers.md)).

- 추론 모델의 시스템 프롬프트를 `role: "developer"` 로 보내는데, 많은 게이트웨이가 이 역할을 받지 않는다.
- 출력 상한을 `max_completion_tokens` 로 보내는데, `max_tokens` 만 아는 서버가 있다.

웹 폼에는 이 둘을 고칠 칸이 없다. 설정 파일의 route 에 직접 적는다.

```yaml
- id: llm-pi-ai
  config:
    providers:
      openrouter:
        apiKeyEnv: OPENROUTER_API_KEY
        api: openai-completions
        baseURL: https://openrouter.ai/api/v1
        compat:
          supportsDeveloperRole: false
          maxTokensField: max_tokens
        models:
          - id: deepseek/deepseek-v4-flash
```

OpenRouter 가 실제로 이 둘 중 무엇을 거절하는지는 모델과 뒤편 제공자에 따라 다를 수 있다. 가이드의 문제 해결 순서는 "`curl` 로는 되는데 하네스에서 안 되면 이 두 줄부터"다. 가이드는 이 스위치가 엔드포인트를 검사하는 게 아니라 엔드포인트에 대한 **주장**이라는 점도 밝힌다. 값을 비워 두면 무시하지 않고 거부한다.

### 2. `off` 로 해도 DeepSeek 모델이 계속 생각한다

DeepSeek 직통 경로에서는 thinking 수준 `off / low / high / max` 가 그대로 동작한다. 하지만 **게이트웨이 뒤의 DeepSeek V4** 는 사정이 다르다. 공식 가이드는 이것을 "말하지 않으면 생각하는 모델"의 예로 든다. 비어 있는 `off` 는 아무 필드도 보내지 않으니 모델은 기본값대로 계속 생각한다. 생각에도 토큰 값이 든다. 모델에 `compat.thinkingFormat: deepseek` 를 달아 줘야 `off` 가 `thinking: {type: disabled}` 로 나간다.

손으로 추가한 모델은 추론 수준을 하나도 선언하지 않은 상태다. 그래서 Effort 메뉴가 아예 안 뜬다. 커스텀 프로바이더에서는 **Model options → Reasoning levels** 를 켜야 한다.

### 3. 한 번 골라 본 모델이 기본값이 된다

모델 선택기에서 모델을 고르면 그 모델이 **새 세션의 기본값**이 된다. 이미 요청을 보낸 세션은 자기 로그에 기록된 모델을 계속 쓴다. 비싼 모델을 한 번 시험해 보고 나면 그 뒤로 여는 세션이 전부 그 모델로 돈다. 청구서가 이상하면 선택기부터 볼 일이다.

### 4. OpenRouter 앱 순위에는 안 잡힌다 — 의도된 설계

OpenRouter 는 `HTTP-Referer`, `X-OpenRouter-Title` 같은 헤더로 어떤 앱이 요청을 보냈는지 집계해 앱 페이지와 순위를 만든다. DSH 는 이 헤더를 **일부러 보내지 않는다.** 리포의 설계 결정 노트(2026-06-21, implemented)는 모든 어댑터가 표준 `User-Agent` 만 보내도록 정했다. OpenRouter 전용 헤더는 제공자 고유의 제품 기능이라 공통 귀속 규칙에 넣지 않는다고 적었다 ([Agent Note: mandatory User-Agent attribution](https://github.com/deepseek-ai/deepseek-harness/blob/master/.agents/notes/archived/architecture/2026-06-21-mandatory-app-attribution-headers.md)).

같은 노트의 표에서 눈여겨볼 줄이 하나 더 있다. **DeepSeek 직통** 요청에는 `x-deepseek-harness-user-id` 와 조건부로 `x-deepseek-harness-session-id` 가 따로 붙는다. OpenRouter 로 가는 요청은 `User-Agent` 만 보낸다. 어떤 식별자가 어디로 가는지가 경로에 따라 달라진다는 뜻이다. 직통 경로에서 기본으로 켜진 세션 로그 업로드 문제는 [9월 체험기]({% post_url 2026-09-17-deepseek-harness-hands-on-postmortems-and-session-log-upload %})에서 다뤘다.

### 5. 다른 모델을 끼우면 하네스가 다르게 움직인다

앞서 말했듯 DeepSeek 은 자사 벤치마크를 DSH 로 쟀다. 반대 방향의 사례도 있다. InterSystems 커뮤니티의 한 개발자는 OpenRouter 를 통해 Claude Code 에 DeepSeek 모델을 물렸다가 잘 안 됐다고 썼다. 그 뒤 DSH 에 V4 Flash 를 물려 30분, $0.70 에 기능 하나를 끝냈다고 했다 ([Shutov, 2026-08-23](https://community.intersystems.com/post/agentic-coding-deepseek-flash)). 개인의 1회 경험담일 뿐 비교 실험은 아니다. 다만 **모델과 하네스는 짝으로 튜닝된다**는 일반론과는 맞는다.

## 그래서 어느 길로, 아니면 직통으로

| 상황 | 추천 | 이유 |
| --- | --- | --- |
| DeepSeek 모델만 쓴다 | **DeepSeek 직통** | 하네스가 이 경로에 맞춰져 있다. thinking 설정도 손볼 필요 없다. OpenRouter 충전 수수료 5.5% 도 없다 |
| 여러 회사 모델을 한 하네스에서 비교하고 싶다 | **OpenRouter** | 키 하나, 청구서 하나. 다른 모델을 하나 추가할 때마다 커스텀 프로바이더를 또 만들 필요가 없다 |
| 팀·조직 단위로 쓴다 | **`ori dsh`** | 허용 모델 목록·예산 상한을 조직 설정으로 강제한다. 키를 나눠 줄 필요가 없다 |
| 데이터 보관이 걱정된다 | `ori dsh` + `/zdr` | 무보관(ZDR) 제공자에게만 라우팅한다. 단 OpenRouter 라는 중간 홉이 하나 늘어난다는 사실은 그대로다 |

DeepSeek 는 8월 16일(UTC) 부터 시간대별 요금을 도입했고, 비혼잡 시간은 혼잡 시간의 50% 다 ([DeepSeek API 공지](https://api-docs.deepseek.com/news/news260813/)). OpenRouter 를 거친 DeepSeek 요청에 이 할인이 그대로 적용되는지는 이 글에서 확인하지 못했다. DeepSeek 만 쓴다면 직통이 유리할 가능성이 높지만, 단가는 자주 바뀌니 쓰는 날 두 가격표를 직접 비교해야 한다.

## 어느 길이든 공통 — SAFETY.md 를 먼저

DSH 리포의 `SAFETY.md` 는 이 프로젝트가 **보안 감사를 받지 않았고** 안전하거나 운영 준비된 것으로 취급하면 안 된다고 적는다. 모델이 만든 코드와 명령을 실행하고, 서드파티 플러그인을 불러오고, 주어진 네트워크·자격증명·파일에 접근하기 때문이다. 샌드박스, 승인 프롬프트, 권한 제어는 위험을 줄일 뿐 격리를 보장하지 않는다는 점도 명시했다 ([SAFETY.md](https://github.com/deepseek-ai/deepseek-harness/blob/master/SAFETY.md)).

샌드박스 모드는 `read-only`, `workspace-write`, `danger-full-access` 세 가지다. 이 모드들은 파일 쓰기만 다루고 네트워크는 범위 밖이다. 백엔드에 따라 집행이 `partial` 로 보고될 수도 있다 ([sandbox 문서](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/subsystems/sandbox.md)).

OpenRouter 를 붙이면 그 환경 안에 **결제 수단과 연결된 키**가 하나 더 생긴다. 일회용 VM 이나 컨테이너에서 돌리고, 키에 예산 상한을 걸어 두자.

## 2차 가이드와 공식 문서가 다른 곳

| 항목 | 일부 2차 가이드 | 공식 DSH 가이드 (`2e39e70`) |
| --- | --- | --- |
| 프로바이더 설정 파일 | `$DSH_HOME/settings.yaml` | `$DSH_HOME/profiles/<profile>/cordis.patch.yml` |
| `ori dsh` 가 DSH 를 띄우나 | 문서마다 다름 | (DSH 쪽 문서에는 언급 없음) OpenRouter 문서 가이드는 "설정만", 소개 페이지는 "띄운다" |

DSH 는 개발자 프리뷰라 몇 달 사이에 설정 구조가 바뀌었을 수 있다. 2차 가이드가 틀렸다기보다 시점이 달랐을 가능성이 크다. 그래서 설정은 쓰는 시점의 리포 문서로 확인하는 게 맞다.

## 근거의 한계

- 이 글은 문서와 소스를 읽고 썼다. `ori dsh` 와 커스텀 프로바이더 경로를 이 글을 위해 직접 실행해 보지는 않았다. 위의 "어긋나는 점"은 실행으로 판정하지 않은 상태다.
- V4-Pro 벤치마크는 DeepSeek 자체 측정이다. 이 글을 쓰며 중립 제3자의 독립 재현 결과는 찾지 못했다.
- InterSystems 커뮤니티 사례는 개인의 1회 경험이다.
- OpenRouter 수수료, 무료 한도, DeepSeek 시간대별 요금은 2026-11-21 에 각 공식 페이지에서 읽은 값이다. 바뀔 수 있다.
- DSH 가 이후 OpenRouter 전용 어댑터를 넣으면 귀속 헤더 결정(4번)은 바뀔 수 있다. 노트 자신이 그 가능성을 열어 두었다.

## References

1. DeepSeek-AI, *deepseek-ai/deepseek-harness* README (MIT). <https://github.com/deepseek-ai/deepseek-harness>
2. DeepSeek Harness, *Architecture*. <https://deepseek-harness.github.io/deepseek-harness/en/reference/>
3. DeepSeek Harness, *Providers user guide* (`docs/user/guide/providers.md`). <https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/user/guide/providers.md>
4. DeepSeek Harness, *Agent Note: Mandatory User-Agent attribution for provider requests* (2026-06-21). <https://github.com/deepseek-ai/deepseek-harness/blob/master/.agents/notes/archived/architecture/2026-06-21-mandatory-app-attribution-headers.md>
5. DeepSeek Harness, *SAFETY.md*. <https://github.com/deepseek-ai/deepseek-harness/blob/master/SAFETY.md>
6. DeepSeek Harness, *Process Sandbox* (`docs/subsystems/sandbox.md`). <https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/subsystems/sandbox.md>
7. DeepSeek API Docs, *DeepSeek-V4-Pro GA Release* (2026-08-13). <https://api-docs.deepseek.com/news/news260813/> · 중문판 <https://api-docs.deepseek.com/zh-cn/news/news260813.md>
8. OpenRouter, *Ori Harness*. <https://openrouter.ai/docs/guides/ori/harness>
9. OpenRouter, *DeepSeek Harness — Ori Harness on OpenRouter*. <https://openrouter.ai/ori/harness/dsh>
10. OpenRouter, *FAQ* (Pricing and fees). <https://openrouter.ai/docs/faq>
11. Olimpiu Pop, "The Open-Sourcing of DeepSeek Harness…", InfoQ, 2026-08-20. <https://www.infoq.com/news/2026/08/deep-seek-harness/>
12. Sergei Shutov, "Agentic Coding with DeepSeek Flash", InterSystems Developer Community, 2026-08-23 (개인 경험담). <https://community.intersystems.com/post/agentic-coding-deepseek-flash>
