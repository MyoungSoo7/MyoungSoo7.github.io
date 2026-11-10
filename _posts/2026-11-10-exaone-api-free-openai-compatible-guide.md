---
layout: post
title: "EXAONE API 무료로 쓰기 — OpenAI 호환 엔드포인트에 붙일 때 실제로 걸리는 것들"
date: 2026-11-10 10:33:27 +0900
categories: [AI, LLM]
tags: [EXAONE, K-EXAONE, LG AI연구원, OpenAI호환, API, LLM]
---

> **검증 범위.** 이 글은 스레드에 올라온 한 장짜리 사용법([달의 이성 @darlsam37](https://www.threads.com/@darlsam37/post/DfinwP5Gf33))을 출발점으로 삼고, 모든 사실을 LG AI연구원의 공식 문서([docs.exaone.ai](https://docs.exaone.ai/ko/docs/k-exaone-2.5))와 보도자료로 대조했다.
> **직접 실행한 것:** 키 없이 `POST https://api.exaone.ai/v1/chat/completions` 와 `GET /v1/models` 를 호출했다. 둘 다 **HTTP 401** 과 OpenAI 형식의 에러 본문 `{"error":{"message":"invalid api key format","type":"authentication_error",...,"code":"invalid_api_key"}}` 을 돌려줬다(2026-11-10 KST 실측).
> **실행하지 않은 것:** 키를 발급받아 실제로 응답을 받아 보지는 않았다. 아래 코드 예시 가운데 공식 문서에 없는 것(OpenAI SDK 예시)은 *공식 스펙으로 유추한 것*이라고 표시해 두었다.

## 1. 무엇이 공개됐나

LG AI연구원은 2026년 11월 9일 "엔비디아 AI 데이 서울 2026"에서 K-EXAONE 2.5 API를 무료로 연다고 발표했다. 보도자료에는 다음과 같이 적혀 있다. "개발자와 스타트업, 기업, 연구 기관 등 누구나 API 키만 발급받으면 별도 비용 없이 'K-엑사원 2.5'를 서비스 개발과 연구에 활용할 수 있다"([LG 보도자료](https://www.lg.co.kr/media/release/30760), [LG AI Research News](https://www.lgresearch.ai/news/view?seq=754)). 플랫폼 변경 이력에도 같은 날짜로 *"This service is currently available free of charge."* 라고 남아 있다([Changelog](https://docs.exaone.ai/en/docs/changelog)).

공식 모델 페이지에 적힌 사양은 다음과 같다([Models](https://docs.exaone.ai/en/docs/models)).

| 항목 | 값 |
| --- | --- |
| 모델 ID | `k-exaone_v2.5` |
| 파라미터 | 750B (Active 31B) |
| 컨텍스트 / 최대 출력 | 512K / 512K |
| 지식 컷오프 | 2026-01 |
| 모달리티 / 언어 | 텍스트 전용 / 한국어·영어 |
| 기능 | Chat, Tool calling, Structured outputs, Code generation, Streaming |

## 2. 스레드 카드의 3단계를 공식 문서와 대조하기

스레드 카드는 사용법을 세 단계로 요약했다. 각 단계를 공식 문서와 비교한 결과다.

| 카드 내용 | 공식 문서 | 판정 |
| --- | --- | --- |
| ① docs.exaone.ai 가입 → My Profile → API Key → 'API Key 생성하기' | 키는 플랫폼에서 발급한다([Authentication](https://docs.exaone.ai/en/docs/authentication)) | 일치 |
| ① "계정당 1개, 30일 만료" | 공개 문서에서 해당 문구를 **찾지 못함** | **미확인 — 작성자 주장** |
| ② 주소 `https://api.exaone.ai/v1` | base URL `https://api.exaone.ai`, 엔드포인트 `/v1/chat/completions`([Quick Start](https://docs.exaone.ai/en/docs/quick-start)) | 일치 |
| ② 모델 `k-exaone_v2.5` | 같음([K-EXAONE 2.5](https://docs.exaone.ai/ko/docs/k-exaone-2.5)) | 일치 |
| ② 헤더 `Authorization: Bearer <키>` | 같음 | 일치 |
| ③ `POST /v1/chat/completions` | 같음. 문서에 "EXAONE API는 OpenAI Compatible API를 지원합니다"라고 적혀 있음 | 일치 |

"30일 만료"는 가입 후 화면에서만 보이는 정보일 수도 있다. 그러나 공개 문서로는 확인할 수 없었다. 키가 정말 30일마다 만료된다면, 운영 환경에 붙일 때 **키 갱신을 운영 절차에 넣어야 한다**. 만료되면 401(`invalid_api_key` 류)이 나오므로 그 응답으로 감지할 수 있다.

## 3. 호출하기

### curl (공식 예시 그대로)

```bash
export EXAONE_API_KEY="발급받은_키"   # 키는 코드·리포에 넣지 말 것

curl 'https://api.exaone.ai/v1/chat/completions' \
  -H "Authorization: Bearer $EXAONE_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "k-exaone_v2.5",
    "max_tokens": 512,
    "messages": [{"role": "user", "content": "Hello"}],
    "stream": false
  }'
```

### OpenAI Python SDK (공식 스펙에서 유추 — 직접 실행 안 함)

공식 문서는 `requests` 예시만 싣고 있다. 다만 "OpenAI 호환"이라고 명시했으므로 SDK의 `base_url` 만 바꾸면 되는 구조다. 이 예시는 직접 돌려 보지 않았다.

```python
import os
from openai import OpenAI

client = OpenAI(
    base_url="https://api.exaone.ai/v1",
    api_key=os.environ["EXAONE_API_KEY"],
)

resp = client.chat.completions.create(
    model="k-exaone_v2.5",
    messages=[{"role": "user", "content": "피보나치 수열을 파이썬으로 짜 줘"}],
    max_tokens=4096,                          # 추론 토큰 포함 — 아래 4절 참고
    extra_body={"reasoning_effort": "low"},   # 기본값은 max
)

msg = resp.choices[0].message
print(msg.content.strip())                         # 앞에 "\n\n" 이 붙을 수 있다
print(getattr(msg, "reasoning_content", None))     # OpenAI 표준에 없는 확장 필드
print(resp.usage)
```

`reasoning_effort` 를 `extra_body` 로 넘긴 이유가 있다. SDK에 있는 같은 이름의 인자는 OpenAI 쪽 값 집합을 전제로 타입이 정해져 있다. 반면 EXAONE은 `max` 같은 자기만의 값을 쓴다. `extra_body` 로 넘기면 SDK 버전이 달라도 요청 본문에 그대로 실린다.

### 도구에 붙이기

공식 문서의 [Starting with Agents](https://docs.exaone.ai/en/docs/agent-start)에 Hermes와 OpenCode 설정이 나와 있다. Hermes에서는 `~/.hermes/config.yaml` 에 provider를 아래처럼 등록한다.

```yaml
providers:
  exaone:
    api: https://api.exaone.ai/v1
    key_env: EXAONE_API_KEY
    transport: chat_completions
    default_model: k-exaone_v2.5
    extra_body:
      temperature: 1.0
      top_p: 0.95
agent:
  reasoning_effort: medium
```

그 밖에 base URL과 모델명을 바꿀 수 있는 OpenAI 호환 클라이언트라면 같은 세 값(주소·모델·키)으로 붙는 구조다. 스레드 카드의 "주소와 모델 이름만 바꾸면"이 바로 이 말이다. 다만 4절에서 다루듯 **응답 형태가 OpenAI와 완전히 같지는 않다.**

## 4. "OpenAI 호환"인데 실제로 걸리는 것들

공식 문서에 적힌 동작 가운데 OpenAI 모델을 쓰던 코드에서 문제가 되기 쉬운 것들이다.

**① 추론을 끌 수 없다.** 문서에 따르면 "K-EXAONE 2.5는 항상 추론 과정을 거친 뒤 답변을 하기 때문에 `enable_thinking` 옵션이 `true` 로 자동 설정"된다. 조절할 수 있는 것은 `reasoning_effort` 하나뿐이다. 그런데 이 값의 **기본값이 `max`** 다. 아무 설정 없이 기존 코드를 붙이면 가장 느리고 토큰을 가장 많이 쓰는 모드로 돈다. 공식 예시 응답을 보면 "Hello"에 답하는 데 `completion_tokens` 218개 중 `reasoning_tokens` 가 209개였다. 빠른 응답이 필요하면 `low` 로 명시하자.

**② `max_tokens` 에 추론 토큰이 포함된다.** 그래서 `max_tokens` 를 작게 잡으면 추론하는 동안 한도가 다 차서 `content` 가 비거나 잘릴 수 있다. 이 부분은 문서를 보고 유추한 것이다. 입력에 대한 제약은 다음과 같다.

$$ n_{\text{input}} + \texttt{max\_tokens} \le 524{,}288 $$

이 한도를 넘으면 400이 돌아온다.

**③ 응답에 OpenAI 표준이 아닌 필드가 있다.** 추론 내용은 `message.reasoning_content` 에, 추론 토큰 수는 `usage.reasoning_tokens` 에 담긴다. 스트리밍에서는 `delta.reasoning_content` 청크가 먼저 오고 그다음에 `delta.content` 가 온다. `delta.content` 만 이어 붙이는 클라이언트라면 추론이 진행되는 동안 **아무것도 오지 않는 것처럼** 보인다.

**④ `content` 앞에 `"\n\n"` 이 붙을 수 있다.** 문서가 직접 경고하는 부분이다. 응답 문자열을 정확히 비교하는 테스트나 파서가 있다면 `strip()` 부터 하자.

**⑤ `reasoning_effort` 값 집합이 문서마다 다르다.** API 레퍼런스에는 `low / high / max` 세 가지가 있다. 반면 에이전트 가이드는 `low / medium / high / max` 네 가지라고 하고, 예시에서도 `medium` 을 쓴다. 키가 없어 `medium` 을 API에 직접 보내 확인하지는 못했다. 400이 난다면 이 차이부터 의심하자.

**⑥ 권장 샘플링 값은 `temperature=1.0`, `top_p=0.95` 다.** 에이전트처럼 이전 추론을 유지해야 하는 멀티턴에서는 `chat_template_kwargs.preserve_thinking=true` 를 함께 권장한다.

## 5. 성능 주장은 어떻게 읽어야 하나

LG가 공개한 에이전틱 벤치마크 수치는 아래와 같다. 모두 **벤더가 직접 측정한 값**이다. 보도자료에도 "오픈 데이터셋을 기반으로 자체 측정한 결과"라고 적혀 있다([LG 보도자료](https://www.lg.co.kr/media/release/30760), [Models](https://docs.exaone.ai/en/docs/models)).

| 벤치마크 | K-EXAONE 2.5 | DeepSeek-V4.1-Flash | GLM-5.3 |
| --- | --- | --- | --- |
| SWE-Bench Pro | 59.2 | 58.4 | 64.0 |
| BrowseComp | 78.0 | 75.8 | 79.0 |
| AutomationBench (Open-set) | 74.6 | 74.9 | 71.6 |
| Claw-Eval | 77.3 | 75.8 | 77.6 |

이 비교를 독립적으로 재현한 중립 제3자의 헤드투헤드 결과는 찾지 못했다(2026-11-10 기준). "8주 만에 24개 지표 종합 70% 이상 향상"도 같은 보도자료에 실린 내부 분석 결과다. 그러니 우열은 자기 작업으로 직접 재 보는 수밖에 없다. 비용이 0인 지금이 그러기에 가장 좋은 시점이다.

## 6. 쓰기 전에 알아 둘 제약

- **무료 기간은 정해져 있지 않다.** AI타임스 보도에서 LG 관계자는 개방 기한을 "(현재로서는) 명시적으로 정하지 않았다"고 했다. 시스템 부담 때문에 "적절한 가이드라인을 마련"하겠다는 말도 덧붙였다([AI타임스](https://www.aitimes.com/news/articleView.html?idxno=217175)). 따라서 "무료"는 *지금의 조건*이지 확정된 가격이 아니다. 서비스에 붙인다면 다른 OpenAI 호환 공급자로 갈아탈 수 있는 구조로 두는 편이 안전하다.
- **레이트 리밋 수치는 공개돼 있지 않다.** 에러 코드 표에 `429 — You have exceeded your rate limit` 만 있고 구체적인 한도는 없다([Error Codes](https://docs.exaone.ai/en/docs/error-codes)). 재시도와 백오프는 클라이언트가 직접 구현해야 한다.
- **키 관리.** 공식 문서는 키를 브라우저나 모바일 앱 같은 클라이언트 코드에 넣지 말라고 하며, 백엔드를 거쳐 호출하라고 권한다([Authentication](https://docs.exaone.ai/en/docs/authentication)). 무료라고 해서 키가 노출돼도 괜찮은 것은 아니다. 할당량이 계정 단위라면 남이 그 할당량을 다 써 버릴 수 있다.
- **웨이트를 직접 돌리는 방법은 별개다.** 7월 말 허깅페이스에 공개된 K-EXAONE 2.0(아파치 2.0)과 공식 리포의 vLLM·llama.cpp 서빙 경로는 셀프호스팅용이다([K-EXAONE GitHub](https://github.com/LG-AI-EXAONE/K-EXAONE), [AI타임스](https://www.aitimes.com/news/articleView.html?idxno=217175)). 반면 이번 무료 API는 LG 서버에서 2.5를 돌려 주는 방식이다.

## 7. 정리

| 질문 | 답 |
| --- | --- |
| 정말 무료인가 | 공식 changelog·보도자료 기준 **현재** 무료. 기한은 미정 |
| 기존 OpenAI 코드에 붙나 | 붙는다. base URL `https://api.exaone.ai/v1` + 모델 `k-exaone_v2.5` + Bearer 키 |
| 그대로 쓰면 되나 | 아니다. `reasoning_effort` 기본값 `max`, `max_tokens` 에 추론 포함, `reasoning_content` 확장 필드, 앞 줄바꿈 — 이 네 가지는 손봐야 한다 |
| 30일 만료 | 공식 문서로는 확인 불가. 실제로 그렇다면 키 갱신을 운영 절차에 넣을 것 |
| 성능 | 벤더 자체 측정만 있음. 중립 재현 부재 |

## References

1. LG AI연구원, 「'K-엑사원 2.5' API 무료 개방」, LG 보도자료, 2026-11-09. <https://www.lg.co.kr/media/release/30760>
2. LG AI Research, "K-EXAONE 2.5 API 무료 공개", LG AI Research News, 2026-11-09. <https://www.lgresearch.ai/news/view?seq=754>
3. EXAONE API Platform, "K-EXAONE 2.5" (API 레퍼런스). <https://docs.exaone.ai/ko/docs/k-exaone-2.5>
4. EXAONE API Platform, "Quick Start". <https://docs.exaone.ai/en/docs/quick-start>
5. EXAONE API Platform, "Authentication". <https://docs.exaone.ai/en/docs/authentication>
6. EXAONE API Platform, "Error Codes". <https://docs.exaone.ai/en/docs/error-codes>
7. EXAONE API Platform, "Models". <https://docs.exaone.ai/en/docs/models>
8. EXAONE API Platform, "Starting with Agents". <https://docs.exaone.ai/en/docs/agent-start>
9. EXAONE API Platform, "Changelog" (2026-11-09 항목). <https://docs.exaone.ai/en/docs/changelog>
10. LG-AI-EXAONE, K-EXAONE 공식 GitHub 리포지터리. <https://github.com/LG-AI-EXAONE/K-EXAONE>
11. 이정환, 「LG, 'K-엑사원 2.5' API 전면 무료 개방…개발자 진입 장벽 낮춘다」, AI타임스, 2026-11-09. <https://www.aitimes.com/news/articleView.html?idxno=217175>
12. 달의 이성(@darlsam37), EXAONE API 사용법 카드, Threads (이 글의 출발점·작성자 주장 출처). <https://www.threads.com/@darlsam37/post/DfinwP5Gf33>
