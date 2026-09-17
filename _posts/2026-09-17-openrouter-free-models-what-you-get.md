---
layout: post
title: "OpenRouter 무료 모델 비교: 가격이 0 이라는 것 말고 무엇이 다른가"
date: 2026-09-17 21:10:14 +0900
categories: [AI, LLM, API]
tags: [OpenRouter, LLM, Free Tier, API, Rate Limit]
---

무료 모델 비교 글은 대개 "어느 모델이 똑똑한가" 로 간다. 그런데 OpenRouter 의 무료 모델을 실제로
붙여 보면 성능보다 먼저 걸리는 것들이 있다. 컨텍스트가 유료판과 다르고, 공급자가 하나뿐이고,
하루 요청 수에 천장이 있고, 프롬프트가 로깅된다.

이 글은 **OpenRouter 공개 API 를 직접 긁어서** 그 차이를 숫자로 확인한 기록이다.
벤치마크 점수는 다루지 않는다 — 검증할 수 없는 수치를 옮겨 적는 것보다, 누구나 `curl` 한 번으로
재현할 수 있는 사실을 정리하는 쪽이 쓸모 있다고 봤다.

**측정 시각: 2026-09-17 21:07 KST (12:07 UTC).** 아래 수치는 전부 이 시점의 스냅샷이고,
목록은 자주 바뀐다. 재현 방법은 글 끝에 적어 두었다.

```bash
curl -s https://openrouter.ai/api/v1/models | jq '.data | length'
# 444
```

## 1. "무료" 가 한 종류가 아니다

전체 444개 중 프롬프트·컴플리션 단가가 모두 `"0"` 인 모델은 **24개**다.
그런데 ID 가 `:free` 로 끝나는 것은 **20개**뿐이다. 나머지 4개는 이렇다.

| ID | 정체 |
| --- | --- |
| `openrouter/free` | 무료 모델 중에서 임의로 하나를 골라 주는 **라우터** |
| `stealth/union-alpha` | 스텔스(비공개 코드명) 모델 — 테스트 기간 무료 |
| `google/lyria-3-pro-preview` | 음악 생성 모델 |
| `google/lyria-3-clip-preview` | 음악 생성 모델 |

이 구분은 장식이 아니다. OpenRouter 의 무료 요청 한도는 **"ID 가 `:free` 로 끝나는 무료 모델
변형을 쓰는 경우"** 에 걸린다.[^limits] 즉 위 4개는 가격이 0 이면서도 `:free` 변형의 일일 한도
계산과는 다른 경로에 있다.

### 함정: `pricing.prompt == 0` 으로 무료를 거르면 틀린다

`google/lyria-3-pro-preview` 의 API 응답을 그대로 보면 이렇다.

```json
{
  "id": "google/lyria-3-pro-preview",
  "pricing": { "prompt": "0", "completion": "0" }
}
```

가격 키가 전부 0 이다. 그런데 같은 응답의 `description` 첫 문장은 이렇게 시작한다.

> Full-length songs are priced at $0.08 per song.

**곡당 $0.08 이라는 가격이 구조화된 `pricing` 객체가 아니라 산문 설명에만 있다.**
토큰 단가가 0 인 것은 이 모델이 토큰으로 과금되지 않기 때문이지 공짜라서가 아니다.
스크립트로 "무료 모델 목록" 을 뽑을 때 `pricing.prompt == "0"` 만 보면 **돈이 나가는 모델이
목록에 섞여 들어온다.** 무료를 거르려면 ID 의 `:free` 접미사를 보는 편이 안전하다.

## 2. 결정적 차이 — 무료 모델은 공급자가 하나뿐이다

여기가 이 글에서 제일 중요한 부분이다. 무료 모델 20개 전부에 대해
`/api/v1/models/<id>/endpoints` 를 조회했다.

```
endpoint 1개인 free 모델: 20 / 20
```

**예외 없이 전부 엔드포인트가 하나다.** 유료판과 나란히 놓으면 차이가 드러난다.

| 모델 | 유료 엔드포인트 수 | 무료 엔드포인트 수 |
| --- | ---: | ---: |
| `z-ai/glm-5.2` | 32 | 1 |
| `google/gemma-4-31b-it` | 14 | 1 |
| `google/gemma-4-26b-a4b-it` | 11 | 1 |
| `nvidia/nemotron-3-ultra-550b-a55b` | 4 | 1 |
| `thinkingmachines/inkling` | 4 | 1 |
| `nvidia/nemotron-3.5-lightning` | 4 | 1 |
| `thinkingmachines/inkling-small` | 3 | 1 |
| `nvidia/nemotron-3-super-120b-a12b` | 2 | 1 |

이게 실무에서 뜻하는 바는 명확하다.

- **폴백이 없다.** OpenRouter 의 강점 중 하나가 한 공급자가 429/장애일 때 같은 모델의 다른
  공급자로 자동 재시도하는 것인데,[^limits] 엔드포인트가 하나면 재시도할 곳이 없다. 429 가
  그대로 내 코드까지 온다.
- **스펙을 내가 고를 수 없다.** 컨텍스트 길이·양자화·최대 출력이 그 하나의 공급자 설정으로 고정된다.
- **가용성이 그 공급자의 컨디션과 같다.** 무료 모델로 만든 서비스의 SLA 는 그 한 곳의 SLA 다.

그리고 그 하나의 공급자가 누구인지 보면 무료 티어의 성격이 보인다.

| 무료 모델 | 유일한 공급자 | 양자화 |
| --- | --- | --- |
| `nvidia/nemotron-3.5-lightning:free` | Nvidia | nvfp4 |
| `thinkingmachines/inkling:free` | Thinking Machines | nvfp4 |
| `poolside/laguna-s-2.1:free` | Poolside | fp4 |
| `cohere/north-mini-code:free` | Cohere | unknown |
| `google/gemma-4-31b-it:free` | Google AI Studio | unknown |
| `liquid/lfm-2.5-2.6b:free` | Liquid | fp8 |
| `nex-agi/nex-n2.5-pro:free` | Nex AGI | fp8 |
| `z-ai/glm-5.2:free` | **Decart** | fp4 |
| `inclusionai/ling-3.0-flash-vl:free` | **Novita** | bf16 |
| `dots-studio/dots-3-note-preview:free` | **AtlasCloud** | fp8 |

20개 중 **15개가 모델을 만든 회사 자신이 서빙한다.** 나머지 5개(inclusionai 3개, z-ai, dots-studio)만
제3의 호스팅 업체다. 여기서부터는 해석이지만 — 무료 티어는 OpenRouter 가 베푸는 할인이 아니라
**모델 벤더가 자기 모델을 쓰게 하려고 용량을 내놓은 자리**로 보는 편이 동작을 잘 설명한다.
엔드포인트가 하나인 것도, 양자화와 컨텍스트가 벤더 마음대로인 것도, 로그를 벤더가 가져가는 것도
그 전제에서 자연스럽다.

## 3. 그래서 무료판 스펙은 유료판과 같지 않다

`:free` 가 "같은 모델에서 값만 뺀 것" 이라고 생각하면 어긋난다.
20개 중 **13개만 유료 대응판이 있고, 7개는 무료로만 존재한다.** 스펙을 대조하면 이렇다.

| 모델 | 무료 ctx | 유료 ctx | 무료 max_out | 유료 max_out |
| --- | ---: | ---: | ---: | ---: |
| `z-ai/glm-5.2` | **32,768** | 1,048,576 | 29,491 | 131,072 |
| `poolside/laguna-s-2.1` | **262,144** | 1,048,576 | 32,768 | 131,072 |
| `nvidia/nemotron-3.5-content-safety` | 128,000 | 131,072 | **8,192** | 117,964 |
| `google/gemma-4-26b-a4b-it` | 262,144 | 262,144 | **32,768** | 235,929 |
| `inclusionai/ling-3.0-flash-fin` | 262,144 | 262,144 | **32,768** | 235,929 |
| `thinkingmachines/inkling` | 1,048,576 | 1,048,576 | **262,144** | 471,859 |
| `nvidia/nemotron-3-ultra-550b-a55b` | 1,000,000 | 262,144 | 65,536 | 32,768 |
| `nvidia/nemotron-3.5-lightning` | 1,000,000 | 262,144 | 65,536 | 131,072 |
| `nvidia/nemotron-3-super-120b-a12b` | 262,144 | 262,144 | 235,929 | 235,929 |
| `thinkingmachines/inkling-small` | 1,048,576 | 1,048,576 | 262,144 | 262,144 |
| `poolside/laguna-xs-2.1` | 262,144 | 262,144 | 32,768 | 32,768 |
| `google/gemma-4-31b-it` | 262,144 | 262,144 | 32,768 | 16,384 |
| `inclusionai/ling-3.0-flash-vl` | 262,144 | 131,072 | 32,768 | 32,768 |

가장 큰 낙차는 `z-ai/glm-5.2` 다. 유료판은 32개 공급자 중 다수가 1,048,576 토큰을 서빙하는데,
무료판은 Decart 한 곳의 **32,768** 이다. 대략 **32배 차이**다.
"GLM 5.2 는 1M 컨텍스트" 라는 문장을 믿고 `:free` 를 붙이면 긴 문서에서 그대로 깨진다.

다만 **방향이 일정하지는 않다.** `nemotron-3-ultra` 와 `nemotron-3.5-lightning` 은 오히려 무료판
쪽 컨텍스트가 크게 잡혀 있고, `gemma-4-31b-it` 은 최대 출력이 무료판 쪽이 크다.
유료 항목의 `context_length` 는 그 모델의 이론적 최대가 아니라 **대표 공급자 기준**이기 때문이다.

그래서 실용적인 결론은 "무료는 깎여 있다" 가 아니라 이것이다 —
**내가 호출할 정확한 변형 ID 로 API 를 직접 조회해서 숫자를 읽어라.** 모델 카드에 적힌 스펙과
내 요청이 실제로 가는 엔드포인트의 스펙은 다른 값이다.

## 4. 무료 모델 20종 (2026-09-17 스냅샷)

| 모델 ID (`:free` 생략) | ctx | max_out | 입력 | tools |
| --- | ---: | ---: | --- | --- |
| `thinkingmachines/inkling-small` | 1,048,576 | 262,144 | text, image, audio | ✅ |
| `thinkingmachines/inkling` | 1,048,576 | 262,144 | text, image, audio | ✅ |
| `nvidia/nemotron-3.5-lightning` | 1,000,000 | 65,536 | text | ✅ |
| `nvidia/nemotron-3-ultra-550b-a55b` | 1,000,000 | 65,536 | text | ✅ |
| `dots-studio/dots-3-note-preview` | 512,000 | 460,800 | text, image | ✅ |
| `inclusionai/ling-3.0-flash-vl` | 262,144 | 32,768 | text, image, video | ✅ |
| `nex-agi/nex-n2.5-mini` | 262,144 | 235,929 | text, image | ✅ |
| `nex-agi/nex-n2.5-pro` | 262,144 | 235,929 | text, image | ✅ |
| `inclusionai/ling-3.0-flash-sante` | 262,144 | 32,768 | text | ✅ |
| `inclusionai/ling-3.0-flash-fin` | 262,144 | 32,768 | text | ✅ |
| `poolside/laguna-s-2.1` | 262,144 | 32,768 | text | ✅ |
| `poolside/laguna-xs-2.1` | 262,144 | 32,768 | text | ✅ |
| `google/gemma-4-26b-a4b-it` | 262,144 | 32,768 | text, image, video | ✅ |
| `google/gemma-4-31b-it` | 262,144 | 32,768 | text, image, video | ✅ |
| `nvidia/nemotron-3-super-120b-a12b` | 262,144 | 235,929 | text | ✅ |
| `cohere/north-mini-code` | 256,000 | 64,000 | text | ✅ |
| `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning` | 256,000 | 65,536 | text, audio, image, video | ✅ |
| `nvidia/nemotron-3.5-content-safety` | 128,000 | 8,192 | text, image | ❌ |
| `liquid/lfm-2.5-2.6b` | 65,536 | 8,192 | text | ❌ |
| `z-ai/glm-5.2` | 32,768 | 29,491 | text | ❌ |

읽는 법 몇 가지.

- **멀티모달이 필요하면** `inkling` 계열(text+image+audio)이나 `nemotron-3-nano-omni`(+video)가
  후보다. `ling-3.0-flash-vl` 과 `gemma-4` 계열은 비디오 입력을 받는다.
- **툴 콜링이 필요하면** `supported_parameters` 에 `tools` 가 있는지부터 본다. 위 20개 중
  3개는 없다. 에이전트를 붙일 거면 이 열이 컨텍스트 길이보다 먼저다.
- **`nemotron-3.5-content-safety` 는 범용 채팅 모델이 아니다.** 이름 그대로 안전성 분류용이고,
  출력 8,192 에 tools 도 없다. "무료 목록에 있으니 써 보자" 로 고를 물건이 아니다.
- **도메인 특화판이 섞여 있다.** `ling-3.0-flash-fin`(금융), `ling-3.0-flash-sante`(의료),
  `north-mini-code`(코드)는 범용 비교표에 나란히 놓으면 오해를 부른다.

## 5. 하루에 몇 번 부를 수 있나

무료 모델에는 플랫폼 차원의 요청 수 한도가 있다. OpenRouter 자체 헬프센터 기준이다.[^zendesk]

| 누적 크레딧 구매액 | 분당 요청 | 일일 요청 |
| --- | ---: | ---: |
| $10 미만 (무결제 포함) | 20 | 50 |
| $10 이상 | 20 | 1,000 |

몇 가지 중요한 성질이 있다.

- **계정을 더 만들어도 소용없다.** 문서가 명시한다 — "Making additional accounts or API keys
  will not affect your rate limits, as we govern capacity globally."[^limits]
- **한 번이라도 $10 을 넣었으면 잔액이 그 아래로 떨어져도 상향된 한도가 유지된다.**[^zendesk]
- **카운터는 UTC 자정에 리셋된다.** 한국 시간 오전 9시다.[^sdk] 한국에서 밤에 돌리는 배치가
  자정에 초기화될 거라 기대하면 어긋난다.
- **남은 횟수는 조회할 수 있다.** `GET /api/v1/key` 로 `limit`/`remaining`/`used` 를 읽는다.[^sdk]

그리고 429 의 출처가 둘이라는 점을 구분해야 한다.[^limits]

1. **OpenRouter 쪽** — 위의 분당/일일 한도를 넘음.
2. **공급자 쪽** — 그 공급자가 혼잡하거나 자체 제한. 이때 `error.metadata.provider_code` 에
   공급자 원래 에러 코드가 담긴다.

유료 모델이라면 2번은 폴백 라우팅이 자동으로 다른 공급자를 시도해 준다. 그런데 앞서 본 대로
**무료 모델은 엔드포인트가 하나라 시도할 다른 곳이 없다.** 무료 티어에서 429 를 자주 보는
이유가 여기 있고, `Retry-After` 를 존중하는 지수 백오프가 선택이 아니라 필수인 이유도 이것이다.

## 6. 프롬프트는 어디로 가나

무료 모델 페이지에 반복해서 붙는 문구가 있다.

> Note: All prompts and completions for this model are logged by the provider and may be used to
> improve the model.

스텔스 모델 쪽은 더 직설적이다.

> Please do not upload any personal, confidential, or otherwise sensitive information.
> This is a trial use only. Do not use for production or business-critical systems.[^free-router]

정리하면 이렇다.

- **OpenRouter 자신은** 옵트인하지 않는 한 프롬프트·응답을 저장하지 않는다.[^data]
- **공급자는 다르다.** 각 공급자의 학습·보존 정책은 엔드포인트마다 구조화되어 노출되고,
  계정 설정에서 "학습할 수 있는 공급자로 라우팅할지" 를 끌 수 있다. 중요한 건
  **유료 모델과 무료 모델의 설정이 따로 있다**는 점이다.[^provider-logging]
- 학습 옵트아웃을 켜면 학습하는 공급자로는 라우팅되지 않는다. 그런데 무료 모델은 공급자가
  하나뿐이므로, 그 하나가 학습한다면 **그 모델은 그냥 못 쓰게 된다.** 무료 목록이 갑자기
  줄어 보인다면 이 설정을 의심해 볼 만하다.
- 더 강하게는 `zdr` 파라미터나 계정 설정으로 Zero Data Retention 엔드포인트만 쓰도록 강제할 수
  있다. 요청 단위 `zdr` 은 계정 설정과 OR 로 동작해서 켜는 것만 되고 끄지는 못한다.[^zdr]

사내 코드나 고객 데이터를 무료 모델에 넣기 전에 볼 것은 성능표가 아니라 이 항목이다.

## 7. 그래서 어떻게 고르나

무료 모델을 고를 때 순서는 이렇게 두는 게 실전에 맞다.

1. **데이터 정책** — 이 프롬프트가 학습에 쓰여도 되는가. 안 되면 여기서 끝이다.
2. **tools 지원 여부** — 에이전트/함수호출을 쓸 거면 필수 조건이다.
3. **실제 엔드포인트 스펙** — 모델 카드가 아니라 `/endpoints` 응답의 ctx·max_out·quantization.
4. **요청 수 예산** — 하루 50회로 되는 일인가, 1,000회가 필요한가.
5. **그 다음에** 품질.

그리고 무료 모델을 프로덕션 경로에 넣는다면 최소한 이 셋은 있어야 한다.

- 지수 백오프 + `Retry-After` 존중
- **유료 모델 폴백** — 무료 변형은 폴백 상대가 구조적으로 없다
- 일일 카운터 모니터링 (`GET /api/v1/key`)

개인적으로는, 무료 티어는 **프로토타이핑과 평가**에 쓰고 프로덕션 경로에서는 같은 모델의 유료
변형으로 바꾸는 게 맞다고 본다. 유료 변형에는 플랫폼 요청 한도가 없고, 무엇보다 공급자가 여러
곳이라 한 곳이 죽어도 자동으로 다음 곳을 시도한다. 무료판과 유료판의 진짜 차이는 가격이 아니라
**그 이중화**다.

## 재현 방법

이 글의 모든 숫자는 아래 두 줄로 다시 뽑을 수 있다. 인증 없이 열려 있는 엔드포인트다.

```bash
# 무료 모델 목록 + 스펙
curl -s https://openrouter.ai/api/v1/models \
| jq -r '.data[] | select(.id|endswith(":free"))
        | [.id, .context_length, .top_provider.max_completion_tokens,
           (.supported_parameters|index("tools")!=null)] | @tsv'

# 특정 모델의 공급자·양자화·컨텍스트
curl -s https://openrouter.ai/api/v1/models/z-ai/glm-5.2:free/endpoints \
| jq -r '.data.endpoints[] | [.provider_name, .quantization, .context_length] | @tsv'
```

목록은 계속 바뀐다. 이 글의 표를 그대로 믿지 말고, 쓰기 직전에 한 번 돌려 보는 편이 낫다.
이 글이 진짜 말하려는 것은 표의 내용이 아니라 **표를 만드는 방법**이다.

---

## References

[^limits]: OpenRouter, "API Credit & Rate Limits — Handle 402 and 429 Errors" — 무료 변형(`:free`) 대상 요청 한도, 계정·키를 늘려도 한도가 공유된다는 설명, 429 의 두 출처와 `error.metadata.provider_code`, 폴백 라우팅. <https://openrouter.ai/docs/api_reference/limits>
[^zendesk]: OpenRouter Help Center, "OpenRouter Rate Limits – What You Need to Know" (2025-10-10) — 무료 50 req/day · 20 req/min, 크레딧 $10 이상 구매 시 1,000 req/day, 잔액이 내려가도 상향 한도 유지. <https://openrouter.zendesk.com/hc/en-us/articles/39501163636379>
[^sdk]: OpenRouter, `FreeModelDailyRequests` 스키마 — `limit`/`remaining`/`used` 필드, "the counter resets at UTC midnight". <https://openrouter.ai/docs/client-sdks/typescript/models/freemodeldailyrequests>
[^models-api]: OpenRouter, "Models API" — `/api/v1/models` 응답 스키마, `pricing` 의 각 키, "A value of `"0"` indicates the feature is free", 변형 접미사(`:free`) 규칙. <https://openrouter.ai/docs/guides/overview/models>
[^data]: OpenRouter, "Data Collection — OpenRouter Privacy" — 옵트인하지 않으면 프롬프트·응답을 저장하지 않는다는 기본 정책. <https://openrouter.ai/docs/guides/privacy/data-collection>
[^provider-logging]: OpenRouter, "Provider Logging — Provider Data Retention Policies" — 공급자별 학습·보존 정책의 구조화 노출, 유료/무료 모델에 대해 별도 설정이 존재한다는 서술. <https://openrouter.ai/docs/guides/privacy/provider-logging>
[^zdr]: OpenRouter, "Zero Data Retention" — 계정·가드레일·요청 단위 ZDR 강제, 요청 단위 `zdr` 은 OR 로 동작. <https://openrouter.ai/docs/guides/features/zdr>
[^free-router]: OpenRouter, `openrouter/free` (Free Models Router) 모델 페이지 — 라우터 설명과 각 무료 엔드포인트에 붙는 로깅 고지 문구. <https://openrouter.ai/openrouter/free>

본문의 모델 수·컨텍스트·엔드포인트 수·공급자·양자화 수치는 2026-09-17 12:07 UTC 에
`https://openrouter.ai/api/v1/models` 와 `https://openrouter.ai/api/v1/models/{id}/endpoints`
를 직접 조회해 얻은 값이다. 제3자 벤치마크 점수는 검증 가능한 1차 자료를 확보하지 못해
의도적으로 다루지 않았다.
