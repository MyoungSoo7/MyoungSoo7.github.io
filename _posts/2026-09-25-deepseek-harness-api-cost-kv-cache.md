---
layout: post
title: "DeepSeek Harness 와 API 비용 (+ Nemotron) — 청구서를 정하는 건 모델 단가가 아니라 캐시 적중률이다"
date: 2026-09-25 02:15:00 +0900
categories: [engineering]
tags: [deepseek, nemotron, nvidia, harness, api-cost, kv-cache, prompt-caching, claude-code, finops]
---

DeepSeek Harness 는 이 블로그에서 세 번 다뤘다. [결정 원장](/2026/08/27/deepseek-harness-decision-ledger/), [인포그래픽 팩트체크](/2026/09/03/deepseek-harness-infographic-fact-check/), [직접 실행과 세션 로그 업로드](/2026/09/17/deepseek-harness-hands-on-postmortems-and-session-log-upload/). 세 글 모두 **돈 이야기는 하지 않았다.** 이번에는 비용을 다룬다.

결론부터 쓴다. DeepSeek API 에서는 **캐시 적중 입력이 캐시 미스 입력보다 30~50 배 싸다.** 그래서 에이전트 하네스의 비용은 "어떤 모델을 쓰느냐"보다 **"요청 앞부분(prefix)을 얼마나 안 깨느냐"**로 더 크게 갈린다. DeepSeek Harness 는 이 사실을 설계 규약으로 박아 둔 리포다. 패키지 README 에 **"KV Cache effect" 절이 403 번** 나온다.

> **가격 기준일: 2026-09-25.** 이 글의 모든 API 토큰 가격(DeepSeek·Anthropic·NVIDIA Nemotron/Amazon Bedrock·OpenRouter)은 이 날짜에 각 공식 페이지에서 조회한 값이다. 리포는 [`deepseek-ai/deepseek-harness`](https://github.com/deepseek-ai/deepseek-harness) 커밋 `477b4f4`(2026-09-24)를 클론해 셌다. 가격은 자주 바뀐다. 8월에는 DeepSeek 가격 페이지에 "큰 폭의 인상 예정" 공지가 붙어 있었다([8/12 글](/2026/08/12/ai-coding-token-cost-fact-check/)).

---

## 1. 가격표: 세 칸 중 어디를 봐야 하나

[DeepSeek 공식 가격 페이지](https://api-docs.deepseek.com/quick_start/pricing)의 현행 모델은 두 개다. 단위는 USD / 1M 토큰이다.

| (2026-09-25 기준) | `deepseek-flash` 피크 | `deepseek-flash` 오프피크 | `deepseek-v4-pro` 피크 | `deepseek-v4-pro` 오프피크 |
|---|---|---|---|---|
| 입력 (캐시 적중) | $0.006 | $0.003 | $0.044 | $0.022 |
| 입력 (캐시 미스) | $0.30 | $0.15 | $1.32 | $0.66 |
| 출력 | $1.20 | $0.60 | $3.96 | $1.98 |

- 두 모델 모두 컨텍스트는 1M, 최대 출력은 384K 이고 thinking 모드가 기본값이다. `deepseek-flash` 는 이미지를 받고 `deepseek-v4-pro` 는 받지 않는다.
- 적중과 미스의 가격 차이는 **flash 가 50 배, v4-pro 가 30 배**다. 출력 단가가 아니라 이 비율이 이 글의 주제다.

### 한국 업무 시간은 거의 피크다

같은 페이지 기준으로 **"오프피크 요금은 피크의 절반"**이다. 피크는 **월~금 01:00–04:00, 06:00–10:00 UTC** 이고 중국 공휴일은 제외된다. KST 로 바꾸면 **평일 10:00–13:00, 15:00–19:00** 이다. 한국에서 낮에 돌리는 에이전트는 대부분 피크 단가를 낸다. 반대로 야간 배치나 주말 작업은 같은 일을 반값에 한다.

---

## 2. DeepSeek 캐시는 '자동'이고 '접두사 완전 일치'다

[DeepSeek KV 캐시 가이드](https://api-docs.deepseek.com/guides/kv_cache)의 요점은 다음과 같다.

- **모든 사용자에게 기본으로 켜져 있다.** 코드 수정이 필요 없다. 디스크 기반 캐시다.
- 다음 요청은 **캐시 접두사 단위(cache prefix unit)와 완전히 일치할 때만** 적중한다.
- 접두사 단위는 요청마다 사용자 입력 끝과 모델 출력 끝에서, 그리고 긴 입출력에서는 일정 토큰 간격으로 만들어진다.
- 적중 여부는 응답 `usage` 의 `prompt_cache_hit_tokens` / `prompt_cache_miss_tokens` 로 확인한다.
- **최선 노력(best-effort)** 방식이라 적중률은 보장되지 않는다. 안 쓰는 캐시는 "보통 몇 시간에서 며칠 안에" 지워진다.

Anthropic 과 비교하면 모델이 다르다. [Anthropic 프롬프트 캐싱](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)은 `cache_control` 로 **중단점을 명시**하고, 캐시 **쓰기에 추가 요금**(5 분 TTL 기준 기본 입력의 1.25 배)을 받는다. TTL 은 기본 5 분이고 1 시간 옵션이 있다. DeepSeek 는 쓰기 요금 없이 자동으로 캐시한다. 대신 개발자가 제어할 손잡이도 없다. **접두사를 안 깨는 것만이 유일한 레버**다.

---

## 3. DeepSeek Harness 는 이 레버를 규약으로 만들었다

클론한 리포에서 `packages/**/README.md` 369 개를 셌다. 그중 305 개 파일에 **`#### KV Cache effect`** 제목이 모두 403 번 나온다. 기능 하나를 추가할 때마다 **"이 기능이 요청 접두사를 깨는가"**를 README 에 선언하도록 한 것이다. 문장 패턴은 대략 세 가지다.

- **무영향**: "the package never touches a request prefix, so it cannot invalidate provider cache reuse."(`workspace`)
- **뒤에 붙이기만 함**: "Append-only; newly visible content follows the reusable request prefix and does not invalidate existing KV-cache entries."(`tool-web`, `tool-todo` 등)
- **깨지는 조건 명시**: 웹 검색 패키지는 "each changed query or model route prevents reuse from its first difference" 라고 적는다.

LLM 어댑터([`llm-deepseek` README](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/llm/llm-deepseek/README.md))에는 캐시를 지키는 장치가 구체적으로 들어 있다.

- **`systemPromptUpdate: in-history`**: 시스템 프롬프트가 바뀌어도 맨 앞의 system 메시지를 다시 쓰지 않는다. 바뀐 프롬프트를 **캐시된 히스토리 뒤에 덧붙인다.** 기본 `deepseek-flash` 항목이 이 모드를 선언한다. README 표현으로는 "the prefix through that history stays reusable" 이다.
- **`toolUpdate: addition-only`**: 도구 목록이 바뀌어도 앞쪽 도구 스키마를 고치지 않는다. `tool_addition` / `tool_removal` 블록으로 뒤에 붙인다.
- **그래도 깨지는 경우를 적어 둔다**: 모델·라우트·프롬프트·스키마·히스토리가 바뀌거나, 이미지 경로 설명이 바뀌거나, Files ID 가 갱신되거나, base64 폴백이 일어나면 "첫 번째 영향받은 토큰부터" 재사용이 끊긴다. 모델을 바꾸면 캐시 도메인 자체가 달라진다.

[`token-meter`](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/llm/token-meter/README.md) 패키지는 세션 로그를 재생해 `uncachedInputTokens`·`cacheReadTokens`·`cacheWriteTokens`·`outputTokens` 를 따로 집계한다. 다만 README 스스로 이 값이 **"청구 기록이 아닌 참고 수치"**라고 적는다. 또 휴리스틱(4 글자 ≈ 1 토큰)이 **"CJK 텍스트와 JSON 스키마를 크게 과소평가한다"**고 경고한다. **한국어 사용자는 하네스 화면의 숫자보다 콘솔 청구 내역을 믿어야 한다**는 뜻이다.

---

## 4. 숫자로 보면: 같은 세션, 캐시 유무 차이

**가상의** 코딩 에이전트 세션 하나를 공식 단가로 계산해 봤다. 가정은 다음과 같다.

- 30 턴 진행한다.
- 첫 요청 컨텍스트는 20K 토큰이다(시스템 프롬프트 + 도구 스키마).
- 매 턴 도구 결과와 대화가 3K 토큰씩 붙는다.
- 턴당 출력은 1K 토큰이다.
- 접두사가 안 깨지면 직전까지의 컨텍스트는 적중, 새로 붙은 부분만 미스로 본다.

그러면 누적 입력은 1,905,000 토큰이고, 그중 적중이 1,798,000(**94.4%**), 미스가 107,000 이다. 출력은 30,000 토큰이다.

| 모델 / 시간대 | 접두사 유지 | 매 턴 접두사 깨짐 | 배수 |
|---|---|---|---|
| `deepseek-flash` 피크 | **$0.079** | $0.608 | 7.7× |
| `deepseek-flash` 오프피크 | $0.039 | $0.304 | 7.7× |
| `deepseek-v4-pro` 피크 | **$0.339** | $2.633 | 7.8× |
| `deepseek-v4-pro` 오프피크 | $0.170 | $1.317 | 7.8× |

같은 가정으로 [Anthropic 공식 가격](https://platform.claude.com/docs/en/about-claude/pricing)(2026-09-25 기준)을 대면 다음과 같다. 새로 붙는 부분은 5 분 캐시 쓰기, 나머지는 캐시 읽기로 계산했다.

| 모델 | 캐시 활용 | 캐시 없음 |
|---|---|---|
| Claude Haiku 4.5 | $0.464 | $2.055 |
| Claude Sonnet 5 | $0.927 | $4.110 |
| Claude Opus 5.5 | $1.495 | $8.220 |

이 표에서 읽을 것은 두 가지다.

Nemotron 을 같은 가정으로 계산한 표는 아래 5절에 있다.

1. **같은 벤더 안에서 캐시가 깨지면 비용이 약 8 배가 된다.** 이 차이는 모델을 바꿔서 생기는 차이와 맞먹는다. flash 로 캐시를 매 턴 깨면($0.608), v4-pro 로 캐시를 지킨 것($0.339)보다 비싸다.
2. **벤더 간 단가 차이는 크다. 하지만 이 표는 품질을 비교하지 않는다.** 같은 일을 몇 턴에 끝내는지, 재시도가 얼마나 나는지는 모델마다 다르다. 턴 수가 두 배가 되면 비용도 거의 두 배가 된다.

**이 계산의 한계**
- 토크나이저가 달라서 같은 텍스트도 벤더마다 토큰 수가 다르다.
- thinking 토큰은 출력으로 과금된다. 이 계산의 "턴당 출력 1K"에는 추론 토큰이 거의 없다고 가정했으므로, 실제 thinking 모드에서는 출력 비용이 훨씬 커질 수 있다.
- DeepSeek 캐시는 최선 노력이라 94% 적중은 **상한에 가까운 가정**이다.
- 실측이 아니라 공식 단가표로 한 산술이다.

---

## 5. Nemotron 은 어떤가 — NVIDIA 는 토큰을 팔지 않는다

DeepSeek 의 대안으로 자주 거론되는 오픈 모델이 NVIDIA **Nemotron** 이다. [free-claude-code](/2026/09/11/free-claude-code-what-it-actually-reroutes/)의 기본 모델도 `nvidia_nim/nvidia/nemotron-3-super-120b-a12b` 였다. 그런데 비용 구조가 DeepSeek 와 근본적으로 다르다.

### NVIDIA 자체 API 에는 토큰 가격표가 없다 (2026-09-25 기준)

- build.nvidia.com 의 호스팅 API 는 **무료 체험**이다. [NIM 페이지](https://developer.nvidia.com/nim)는 "DGX Cloud 기반 NIM API 엔드포인트를 **프로토타이핑용으로 무료**로 제공한다"고 적는다. [NIM FAQ](https://forums.developer.nvidia.com/t/nvidia-nim-faq/300317)는 이 카탈로그가 **"평가와 프로토타이핑 용도로만"** 설계됐다고 밝히고, 레이트 리밋은 모델과 동시 사용자 수에 따라 달라진다고만 한다. 수치는 공개하지 않는다.
- [모델 페이지](https://build.nvidia.com/nvidia/nemotron-3-super-120b-a12b)의 체험 서비스는 **NVIDIA API Trial Terms of Service** 를 따른다.
- **프로덕션**은 두 갈래다.
  1. NIM 컨테이너를 직접 띄운다. 이 경우 **NVIDIA AI Enterprise 라이선스**가 필요하고 과금 단위는 **GPU** 다. 가격은 공개돼 있지 않고 "Contact Us" 와 90 일 체험판만 있다([AI Enterprise](https://www.nvidia.com/en-us/data-center/products/ai-enterprise/)).
  2. 파트너의 종량제 엔드포인트를 쓴다.
- 가중치 자체는 다르다. [Nemotron 페이지](https://www.nvidia.com/en-us/ai-data-science/foundation-models/nemotron/) FAQ 는 Hugging Face 에서 내려받은 모델을 **"프로덕션에서도 무료로"** 돌릴 수 있다고 적는다. 라이선스는 MIT 가 아니라 **NVIDIA Nemotron Open Model License** 다([모델 카드](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-FP8), "ready for commercial use").

정리하면 **무료 엔드포인트로 에이전트를 상시 돌리는 건 약관상 프로토타이핑의 범위를 넘는다.** 토큰당 비용을 내고 쓰려면 NVIDIA 가 아니라 클라우드 사업자의 가격표를 봐야 한다.

### 1 차 가격표: Amazon Bedrock (2026-09-25 기준)

클라우드 사업자 공식 가격표 가운데 Nemotron 을 올려 둔 곳은 [Amazon Bedrock](https://aws.amazon.com/bedrock/pricing/)(NVIDIA 탭, 온디맨드)이다. 단위는 USD / 1M 토큰이다.

| 모델 | 입력 | 출력 | 비고 |
|---|---|---|---|
| Nemotron 3 Super 120B A12B | $0.15 | $0.65 | US East/West |
| Nemotron 3 Nano 30B A3B | $0.06 | $0.24 | US East/West |
| Nemotron Nano 2 | $0.06 | $0.23 | US East/West |
| Nemotron Nano 2 VL | $0.20 | $0.60 | US East/West |

GovCloud 는 Super 기준 $0.18 / $0.78 이다. 리전마다 가격이 다르므로 서울 리전 제공 여부와 가격은 콘솔에서 직접 확인해야 한다. 그리고 가격표에 **Nemotron 용 프롬프트 캐싱 단가가 없다.** 4 절과 같은 30 턴 세션을 캐시 할인 없이 계산하면 다음과 같다.

| 모델 (Bedrock US, 2026-09-25) | 30 턴 세션 |
|---|---|
| Nemotron 3 Nano 30B A3B | $0.121 |
| Nemotron 3 Super 120B A12B | $0.305 |
| (비교) `deepseek-flash` 피크, 접두사 유지 | $0.079 |
| (비교) `deepseek-flash` 피크, 매 턴 깨짐 | $0.608 |

재미있는 대비가 나온다. Nemotron Super 의 캐시 없는 입력 단가($0.15)는 DeepSeek flash **오프피크의 캐시 미스** 단가와 같다. 하지만 DeepSeek 는 캐시가 적중하면 $0.003~0.006 까지 내려간다. **캐시를 잘 지키는 하네스라면 DeepSeek 가, 접두사가 자주 깨지는 워크로드라면 캐시 할인이 없는 Nemotron 이 상대적으로 유리해지는** 구조다. 이번에도 품질·턴 수는 비교에 넣지 않았다.

### 애그리게이터 가격 (참고, 2026-09-25 기준)

1 차 출처는 아니지만 시장 가격을 가늠하는 참고로 적는다. [OpenRouter 의 Nemotron 3 Super 엔드포인트 목록](https://openrouter.ai/api/v1/models/nvidia/nemotron-3-super-120b-a12b/endpoints)에는 다음이 올라 있다.

- DeepInfra(bf16): $0.085 / $0.40
- DekaLLM(fp8): $0.08 / $0.45
- 무료 변형 `:free`: 제공자 "Nvidia", $0 / $0

세 곳 모두 컨텍스트 262,144 이고 캐싱은 없다. 모델 카드상 최대 컨텍스트는 1M 이지만 Hugging Face 기본 설정은 256K 이고, 호스팅 제공자는 대개 이쪽을 따른다. 무료 변형도 결국 위의 NVIDIA 체험 약관 범위 안이라고 보는 게 안전하다.

---

## 6. Claude Code 에 DeepSeek 를 붙이면 캐시는 어떻게 되나

DeepSeek 는 Anthropic 형식 엔드포인트 `https://api.deepseek.com/anthropic` 을 제공하고, [Claude Code 연동 가이드](https://api-docs.deepseek.com/quick_start/agent_integrations/claude_code)도 공식으로 낸다. 비용 관점에서 봐야 할 부분은 다음과 같다([Anthropic API 호환 문서](https://api-docs.deepseek.com/guides/anthropic_api)).

- **`cache_control` 은 무시된다.** Claude Code 가 공들여 찍는 캐시 중단점은 의미가 없어지고, DeepSeek 의 자동 접두사 캐시만 동작한다. 적중률은 결국 Claude Code 가 요청 앞부분을 얼마나 안정적으로 유지하느냐에 달린다.
- **모델 이름 매핑**: `claude-opus` 로 시작하는 이름은 `deepseek-v4-pro` 로, `claude-sonnet`·`claude-haiku` 와 그 밖의 이름은 `deepseek-flash` 로 간다. 과금은 매핑된 모델 단가를 따른다. Opus 를 고르면 v4-pro 요금이 나온다.
- **지원하지 않는 블록**: `document`, `search_result`, `redacted_thinking`, `code_execution_tool_result`, `mcp_tool_use`, `mcp_tool_result`, `container_upload`. `thinking.budget_tokens` 도 무시된다. thinking 길이를 예산으로 묶어 비용을 통제하는 방법은 통하지 않는다는 뜻이다.
- **웹 검색은 된다.** 다만 추가 토큰이 든다고 명시돼 있다.

그리고 Anthropic 쪽 [LLM gateway 문서](https://code.claude.com/docs/en/llm-gateway)는 선을 분명히 긋는다. "Anthropic 은 서드파티 게이트웨이 제품을 보증·유지·감사하지 않으며, **어떤 게이트웨이로든 Claude Code 를 Claude 가 아닌 모델로 라우팅하는 것을 지원하지 않는다.**" 동작은 하지만 지원 범위 밖이다. 이 구조의 자세한 내용은 [free-claude-code 글](/2026/09/11/free-claude-code-what-it-actually-reroutes/)에 정리했다.

반면 DeepSeek Harness 는 어댑터가 DeepSeek 캐시를 전제로 설계됐다(`in-history`, `addition-only`). **같은 DeepSeek 모델이라도 어느 하네스에 태우느냐에 따라 적중률, 곧 청구액이 달라질 수 있다.** 두 하네스의 적중률을 실측으로 비교하지는 않았다. 비교하려면 같은 작업을 돌려 `prompt_cache_hit_tokens` 를 합산해 보면 된다.

---

## 7. 비용표에 안 나오는 비용

- **동시성 한도**: DeepSeek 의 [레이트 리밋](https://api-docs.deepseek.com/quick_start/rate_limit)은 RPM 이 아니라 **동시 요청 수**로 걸린다. flash 는 2,500, v4-pro 는 500 이고, 키가 여러 개여도 **계정 단위**로 계산된다. 넘으면 429 가 난다. 서브에이전트를 많이 띄우는 하네스라면 이 한도가 병목이 된다. 확장 요청은 추가 비용이 없다고 한다.
- **데이터 위치**: [DeepSeek 개인정보처리방침](https://cdn.deepseek.com/policies/en-US/deepseek-privacy-policy.html)(2026-05-06 개정)은 서버가 **중화인민공화국에 있다**고 적는다. 사내 코드를 보내는 에이전트라면 단가보다 먼저 이 조항이 도입 여부를 가른다.
- **텔레메트리 헤더**: DeepSeek Harness 는 공식 DeepSeek 요청마다 설치 단위 익명 ID 헤더를 붙인다. [9/17 글](/2026/09/17/deepseek-harness-hands-on-postmortems-and-session-log-upload/)에서 실행해 확인한 내용이다.
- **오픈 웨이트라는 출구**: [DeepSeek-V4-Pro-0813](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-0813)과 [DeepSeek-V4.1-Flash](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash)는 모델 카드 기준 **MIT 라이선스**다. 데이터 위치가 문제라면 자체 호스팅이라는 선택지가 있다. 다만 V4-Pro 는 파라미터가 1.7T 라서, 이때 비용표는 토큰 단가가 아니라 GPU 시간표가 된다.

---

## 가져갈 것

1. **DeepSeek 에서는 캐시 적중 입력이 미스보다 30~50 배 싸다.** 청구서를 줄이는 첫 번째 레버는 모델 교체가 아니라 **접두사를 안 깨는 것**이다.
2. 시스템 프롬프트나 도구 목록을 세션 중간에 **앞에서 고치면** 그 뒤 전부가 미스가 된다. 바뀐 내용은 **뒤에 덧붙인다.** DeepSeek Harness 가 `in-history` 와 `addition-only` 로 하는 일이 이것이다.
3. 한국 낮 시간(평일 10–13 시, 15–19 시 KST)은 DeepSeek **피크**다. 배치 작업은 밤이나 주말로 옮기면 절반 가격이다.
4. 하네스가 보여 주는 토큰 수는 참고치다. 특히 한국어는 과소평가된다. **판단은 `usage` 필드와 콘솔 청구 내역으로** 한다.
5. **Nemotron 은 NVIDIA 가 토큰을 팔지 않는다.** 무료 API 는 프로토타이핑용이다. 종량제는 Bedrock 같은 클라우드 가격표(Super $0.15 / $0.65, 캐시 할인 없음)를 보고, 아니면 가중치를 내려받아 GPU 비용으로 계산한다.
6. 단가표 비교는 품질을 빼고 한 계산이다. 실제 비용은 "턴당 단가 × 끝내는 데 걸린 턴 수"이고, 뒤쪽 항은 직접 돌려 봐야 안다.

---

## References

1. DeepSeek, *Models & Pricing* (2026-09-25 조회). <https://api-docs.deepseek.com/quick_start/pricing>
2. DeepSeek, *Context Caching (KV Cache)*. <https://api-docs.deepseek.com/guides/kv_cache>
3. DeepSeek, *Anthropic API compatibility*. <https://api-docs.deepseek.com/guides/anthropic_api>
4. DeepSeek, *Claude Code integration*. <https://api-docs.deepseek.com/quick_start/agent_integrations/claude_code>
5. DeepSeek, *Rate Limit*. <https://api-docs.deepseek.com/quick_start/rate_limit>
6. DeepSeek, *Privacy Policy* (2026-05-06). <https://cdn.deepseek.com/policies/en-US/deepseek-privacy-policy.html>
7. deepseek-ai, *deepseek-harness* (commit `477b4f4`). <https://github.com/deepseek-ai/deepseek-harness>
8. deepseek-harness, *llm-deepseek README*. <https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/llm/llm-deepseek/README.md>
9. deepseek-harness, *token-meter README*. <https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/llm/token-meter/README.md>
10. Anthropic, *Pricing*. <https://platform.claude.com/docs/en/about-claude/pricing>
11. Anthropic, *Prompt caching*. <https://platform.claude.com/docs/en/build-with-claude/prompt-caching>
12. Anthropic, *Claude Code — LLM gateway configuration*. <https://code.claude.com/docs/en/llm-gateway>
13. Hugging Face, *deepseek-ai/DeepSeek-V4-Pro-0813*. <https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-0813>
14. Hugging Face, *deepseek-ai/DeepSeek-V4.1-Flash*. <https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash>
15. NVIDIA, *NIM for Developers*. <https://developer.nvidia.com/nim>
16. NVIDIA Developer Forums, *NVIDIA NIM FAQ*. <https://forums.developer.nvidia.com/t/nvidia-nim-faq/300317>
17. NVIDIA, *nemotron-3-super-120b-a12b* (API Catalog). <https://build.nvidia.com/nvidia/nemotron-3-super-120b-a12b>
18. NVIDIA, *Nemotron foundation models*. <https://www.nvidia.com/en-us/ai-data-science/foundation-models/nemotron/>
19. NVIDIA, *AI Enterprise*. <https://www.nvidia.com/en-us/data-center/products/ai-enterprise/>
20. Hugging Face, *nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-FP8*. <https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-FP8>
21. AWS, *Amazon Bedrock Pricing* (NVIDIA 탭, 2026-09-25 조회). <https://aws.amazon.com/bedrock/pricing/>
22. OpenRouter, *nvidia/nemotron-3-super-120b-a12b endpoints* (애그리게이터, 참고용). <https://openrouter.ai/api/v1/models/nvidia/nemotron-3-super-120b-a12b/endpoints>
