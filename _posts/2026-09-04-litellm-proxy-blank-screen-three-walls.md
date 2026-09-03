---
layout: post
title: "LiteLLM 프록시에 로그인했는데 아무것도 안 뜬다 — 게이트웨이의 루트는 대시보드가 아니다"
date: 2026-09-04 06:06:33 +0900
categories: [infra]
tags: [litellm, llm-gateway, cloudflare-access, kubernetes, k3s, openai-api, swagger]
---

사내(라기보다 집안) LLM 게이트웨이로 LiteLLM 프록시를 K3s 위에 올려 두고 한 달을 썼다.
그러다 브라우저로 들어가 본 사람이 이렇게 말했다. **"로그인하면 아무것도 안 떠."**

파드는 멀쩡했다. `Running`, 재시작 0회, DB 연결됨. 그런데도 화면에는 쓸 게 없었다.
결론부터 말하면 고장이 아니라 **벽이 세 겹**이었고, 세 벽이 전부 "빈 화면"이라는 같은
증상으로 보였다. 이 글은 그 세 겹을 하나씩 갈라 본 기록이다.

## 1. LiteLLM 프록시는 대시보드 앱이 아니다

먼저 이게 뭔지부터. LiteLLM 프록시는 공식 문서 표현으로 "LLM Gateway" 이고, 하는 일은
세 가지다 — 100개 넘는 모델을 OpenAI `ChatCompletions` 형식 하나로 통일해서 부르게 해
주고, 가상 키(virtual key)로 인증·예산·사용량을 추적하고, 같은 모델의 여러 배포 사이를
로드밸런싱한다.([LiteLLM 공식 문서](https://docs.litellm.ai/docs/proxy/quick_start))

즉 **사람이 보는 화면이 주인공이 아니다.** 주인공은 `/v1/chat/completions` 이고,
사람용 화면은 곁다리로 붙어 있다. 이 전제가 안 잡히면 "홈페이지에 뭐가 떠야 정상"인지에
대한 기대부터 틀린다.

내 구성은 이렇게 생겼다. 컨피그맵 하나에 모델 목록과 일반 설정이 들어간다.

```yaml
model_list:
  - model_name: gpt-4o
    litellm_params:
      model: openai/gpt-4o
      api_key: os.environ/OPENAI_API_KEY
  # ... gpt-4o-mini / gpt-4.1 / gpt-4.1-mini / gemini-2.5-flash / gemini-2.5-flash-lite

general_settings:
  master_key: os.environ/LITELLM_MASTER_KEY
  database_url: os.environ/DATABASE_URL

litellm_settings:
  drop_params: true
  request_timeout: 600
```

`drop_params: true` 는 프로바이더가 모르는 파라미터를 예외 대신 **버리게** 하는 설정이다.
기본 동작은 그 반대 — 지원 안 하는 파라미터를 보내면 예외를 던진다. 켜 두면 같은 코드로
여러 프로바이더를 호출할 때 파라미터를 프로바이더별로 손보지 않아도 된다.([공식 문서](https://docs.litellm.ai/docs/completion/drop_params))

## 2. 첫째 벽 — 루트는 원래 Swagger 다

파드 안에서 직접 두들겨 봤다. 클러스터 밖 요소를 다 걷어내고 앱만 보는 게 순서다.

| 경로 | 상태 | 응답 |
| --- | --- | --- |
| `/` | 200 | `text/html` 3,052 B, `<title>LiteLLM API - Swagger UI</title>` |
| `/ui` | 200 | `text/html` 26,433 B, `<title>LiteLLM Dashboard</title>` |
| `/docs` | 404 | — |
| `/openapi.json` | 200 | 1,195,293 B |
| `/health/readiness` | 200 | `{"status":"healthy","db":"connected"}` |

여기서 두 줄이 답을 다 하고 있다. **루트(`/`)는 Swagger API 문서고, 관리 콘솔은 `/ui` 다.**
그리고 `/docs` 가 404 인 건 고장이 아니라 그 반대의 증거다 — LiteLLM 은 `DOCS_URL` 기본값이
`"/"` 라서 문서가 루트로 올라와 있고, 그래서 `/docs` 에는 아무것도 없다. 공식 문서도
"Your Proxy Swagger is available on the root of the Proxy" 라고 못 박는다.([공식 문서](https://docs.litellm.ai/docs/proxy/ui))

그러니 루트에서 본 화면은 "아무것도 안 뜬" 게 아니라 **기대한 것과 다른 게 뜬 것**이었다.
API 레퍼런스 페이지를 대시보드로 알고 보면, 특히 휴대폰에서는, 빈 화면과 구별이 잘 안 된다.

고치는 방법도 문서에 있다. 루트를 콘솔로 보내고 싶으면 문서 경로를 옮기고 리다이렉트를 건다.

```shell
DOCS_URL="/docs"          # 문서를 루트에서 치운다
ROOT_REDIRECT_URL="/ui"   # 루트로 오면 콘솔로 보낸다
```

`ROOT_REDIRECT_URL` 은 `DOCS_URL` 이 `"/"` 가 아닐 때만 의미가 있다.([공식 문서](https://docs.litellm.ai/docs/proxy/ui))
한 줄짜리 설정이지만, 이걸 안 걸어 두면 앞으로도 들어오는 사람마다 같은 자리에서 넘어진다.

## 3. 둘째 벽 — 콘솔에 로그인할 계정이 아예 없었다

`/ui` 로 갔다 치자. 그다음이 또 막힌다. 로그인 엔드포인트를 직접 때려 보면 이유가 그대로 나온다.

```
GET  /login  -> 405 {"detail":"Method Not Allowed"}
POST /login  -> 401 {"error":{"message":"Invalid credentials used to access UI.
                     Check 'UI_USERNAME', 'UI_PASSWORD' in .env file", ...}}
```

에러 메시지가 친절해서 다행이었다. **UI 로그인 계정이 설정된 적이 없었다.** 시크릿에는
`DATABASE_URL`, `GEMINI_API_KEY`, `LITELLM_MASTER_KEY`, `OPENAI_API_KEY` 네 개뿐이었고
`UI_USERNAME`/`UI_PASSWORD` 가 없었다. 공식 문서가 요구하는 건 이 두 개다.([공식 문서](https://docs.litellm.ai/docs/proxy/ui))

```shell
LITELLM_MASTER_KEY="sk-..."   # 프록시 마스터 키
UI_USERNAME=...               # 콘솔 로그인 아이디
UI_PASSWORD=...               # 콘솔 로그인 비밀번호
```

문서는 콘솔의 전제 조건도 같이 적어 둔다 — **마스터 키가 설정돼 있어야 하고, DB 가 붙어
있어야 한다.**([공식 문서](https://docs.litellm.ai/docs/proxy/ui)) 가상 키를 발급·삭제하고 사용량을 추적하는 화면이니 저장소가
없으면 성립하지 않는다. 마스터 키는 반드시 `sk-` 로 시작해야 하고, DB 는 postgres 를
`DATABASE_URL` 로 물린다.([공식 문서](https://docs.litellm.ai/docs/proxy/virtual_keys)) 우리 쪽은 둘 다 이미 충족돼 있었다
(`/health/readiness` 의 `"db":"connected"`). 없던 건 계정뿐이었다.

시크릿에 두 값을 넣고 파드를 다시 띄운 뒤 같은 요청을 다시 보냈다.

```
POST /login -> 200, 리다이렉트 .../ui/?login=success
```

여기서 한 가지 습관을 적어 둔다. **`200` 을 "됐다" 의 증거로 쓰지 않는다.** 위 결과에서
내가 근거로 삼은 건 상태코드가 아니라 `?login=success` 로 넘어간 최종 URL 이다. 상태코드만
보면 로그인 폼을 다시 그려 주는 200 과 구별이 안 된다.

## 4. 셋째 벽 — Cloudflare Access 는 API 도 막는다

이 프록시는 OpenAI·Gemini 실키를 쥐고 있다. 그래서 도메인 앞에 Cloudflare Access(이메일
OTP)를 세워 뒀다. 그런데 이 벽에는 사람이 예상 못 하는 성질이 하나 있다.

바깥에서 세 경로를 그냥 때려 보면 이렇다.

| 경로 | 엣지 응답 |
| --- | --- |
| `/` | 302 (143 B, `<center>cloudflare</center>`) |
| `/ui` | 302 (동일) |
| `/health/liveliness` | 302 (동일) |

**헬스체크까지 302 다.** Access 는 애플리케이션 단위로 걸리기 때문에 경로를 가리지 않는다.
브라우저는 이 302 를 따라가 OTP 화면을 보여 주고 사람이 통과하면 그만이지만, `curl` 이나
SDK 는 로그인 HTML 을 받아 들고 "이상한 응답"으로 죽는다. 즉 **브라우저 세션이 없는
프로그램은 이 도메인으로 API 를 부를 수 없다.**

해법은 두 가지다.

1. **내부에서 부른다.** 클러스터 안이나 같은 사설망에서 NodePort(`<노드IP>:30400`)로 직접
   호출한다. Access 를 지나지 않으니 프록시의 마스터 키/가상 키만 있으면 된다.
2. **Access 서비스 토큰을 쓴다.** Cloudflare 가 Client ID/Secret 한 쌍을 발급해 주고,
   요청 헤더에 `CF-Access-Client-Id` 와 `CF-Access-Client-Secret` 을 실으면 자동화된
   시스템도 Access 정책을 통과한다. 이때 **해당 정책의 action 을 `Service Auth` 로 두어야**
   한다. 아니면 Access 가 여전히 IdP 로그인을 요구한다. 그리고 Client Secret 은 발급 시점에
   **한 번만** 표시된다 — 잃어버리면 새로 만드는 수밖에 없다.([Cloudflare 공식 문서](https://developers.cloudflare.com/cloudflare-one/identity/service-tokens/))

여기서 두 겹의 인증이 생긴다는 점을 분명히 해 두는 게 좋다. Access 를 통과하는 것과
LiteLLM 이 요청을 받아 주는 것은 **다른 문제**다. Access 를 지나도 키 없이 부르면 프록시가
자기 몫의 401 을 돌려준다.

```
GET /v1/models              -> 401 {"error":{"message":"Authentication Error, No api key passed in.", ...}}
GET /v1/models  + 마스터키  -> 200 ["gpt-4o","gpt-4o-mini","gpt-4.1","gpt-4.1-mini",
                                   "gemini-2.5-flash","gemini-2.5-flash-lite"]
```

마지막으로 실제 추론을 한 번 돌려 끝을 확인했다. 가장 싼 모델로 토큰 몇 개만.

```bash
curl http://<노드IP>:30400/v1/chat/completions \
  -H "Authorization: Bearer <키>" -H "Content-Type: application/json" \
  -d '{"model":"gemini-2.5-flash-lite",
       "messages":[{"role":"user","content":"대한민국 수도를 한 단어로만"}],
       "max_tokens":16}'
```

```
200  content="서울"  usage={prompt_tokens: 9, completion_tokens: 1, total_tokens: 10}
```

## 5. "빈 화면" 은 증상 이름이 아니다

이번 건에서 진짜로 배운 건 LiteLLM 지식이 아니라 **진단 순서**다. 사용자가 본 하나의 증상
뒤에는 성격이 완전히 다른 세 층이 있었다.

| 층 | 무엇이 막았나 | 이번 사례의 실제 상태 |
| --- | --- | --- |
| 엣지 인증 | Cloudflare Access | 정상 동작 (모든 경로 302) |
| 앱 라우팅 | 루트는 Swagger, 콘솔은 `/ui` | 설계대로. 기대가 틀렸음 |
| 앱 인증 | `UI_USERNAME`/`UI_PASSWORD` | **없었음. 이게 진짜 결함** |

세 층을 가르는 방법은 단순하다. **안에서 밖으로 좁혀 나간다.** 파드 안에서
`127.0.0.1:4000` 을 때려 앱 자체의 응답을 확보하고(여기서 라우팅과 앱 인증이 갈린다),
그다음 도메인으로 같은 경로를 때려 엣지가 무엇을 바꾸는지 본다. 두 결과가 다르면 그 차이가
곧 엣지의 몫이다. 이번엔 안에서는 200, 밖에서는 302 였고 그래서 Access 는 "정상"으로
분류됐다.

반대로 했다면 — 브라우저에서만 붙들고 씨름했다면 — 세 층이 전부 흰 화면으로 겹쳐 보여서
어디를 고쳐야 할지 끝내 못 골랐을 것이다.

## 6. 정리해서 남긴 것

- 루트가 문서 페이지인 건 **사양**이다. 사람을 콘솔로 보내고 싶으면 `DOCS_URL` +
  `ROOT_REDIRECT_URL` 을 건다. 안 걸면 새로 오는 사람마다 같은 데서 넘어진다.
- 콘솔을 쓸 거면 `UI_USERNAME`/`UI_PASSWORD` 를 **처음 배포할 때** 넣는다. 마스터 키와 DB 는
  콘솔의 전제 조건이다.
- Access 는 헬스체크까지 막는다. 자동화가 그 도메인을 부를 계획이라면 서비스 토큰을 같이
  설계한다. "나중에 뚫자" 로 미루면 결국 Access 를 끄자는 이야기가 나오는데, 이 프록시는
  실제 결제되는 API 키를 쥐고 있으므로 그건 선택지가 아니다.

## References

- [LiteLLM — Admin UI Quick Start](https://docs.litellm.ai/docs/proxy/ui) — 루트 = Swagger,
  콘솔 = `/ui`, `UI_USERNAME`/`UI_PASSWORD`, `DOCS_URL`/`ROOT_REDIRECT_URL`, 콘솔 전제 조건
- [LiteLLM — Virtual Keys](https://docs.litellm.ai/docs/proxy/virtual_keys) — 마스터 키 `sk-` 접두사, `DATABASE_URL` 요구사항
- [LiteLLM — CLI Quick Start](https://docs.litellm.ai/docs/proxy/quick_start) — LLM Gateway 가 맡는 역할 정의
- [LiteLLM — Drop Unsupported Params](https://docs.litellm.ai/docs/completion/drop_params) — `drop_params` 기본 동작과 효과
- [Cloudflare One — Service tokens](https://developers.cloudflare.com/cloudflare-one/identity/service-tokens/) — `CF-Access-Client-Id`/`Secret` 헤더, 정책 action `Service Auth`, Secret 1회 노출

## 근거의 한계

- 본문의 상태코드·바이트수·응답 본문은 **2026-09-04 새벽, 단일 클러스터의 단일 파드**에서
  얻은 값이다. LiteLLM 이미지는 `main-latest` 태그를 쓰고 있어 버전이 고정돼 있지 않으므로,
  다른 시점에 같은 태그를 받으면 페이지 크기나 일부 경로 동작이 달라질 수 있다.
- 3절의 "계정이 설정된 적이 없다" 는 배포 매니페스트와 시크릿 키 목록으로 판단한 것이고,
  과거 이력 전체를 추적해 확인한 것은 아니다.
- 4절의 서비스 토큰 절차는 Cloudflare 공식 문서를 인용한 것이고, 이 도메인에 실제로
  적용해 통과시켜 본 것은 아니다. 검증한 것은 "토큰 없이는 302 로 막힌다" 까지다.
- 성능·비용 비교는 하지 않았다. 다른 LLM 게이트웨이와의 중립적 head-to-head 벤치마크는
  이 글의 범위 밖이고, 그런 비교 없이 우열을 말하지 않는다.
