---
layout: post
title: "정산 대사와 LLM 비용 대사는 같은 문제다 — PG 파일과 SpendLogs, 두 원장을 맞추는 법"
date: 2026-09-28 05:41:40 +0900
categories: [AI, backend]
tags: [정산, 대사, reconciliation, LiteLLM, Opik, LLMOps, 비용관리, 정합성, ClaudeCode]
---

정산 시스템을 만들면서 가장 오래 붙잡고 있던 질문은 이것이었다.
**"내 장부와 바깥의 청구서가 어긋나면, 어느 쪽을 믿고 어떻게 분류하는가."**

LLM 게이트웨이를 운영하면서 같은 질문을 다시 만났다. PG사 정산 파일 자리에
OpenAI·Google 청구서가 있고, 내부 결제 원장 자리에 LiteLLM 의 사용량 로그가 있을 뿐이다.
이 글은 두 시스템을 나란히 놓고, 정산 쪽에서 이미 풀어둔 답을 LLM 비용 쪽으로 옮겨 본 기록이다.

결론부터 적으면 이렇다.

> - LLM 비용도 **"내부 원장 vs 외부 청구서"** 대사 문제다. LiteLLM 공식 문서도 청구서와 안 맞을 때의 대조 절차를 따로 둔다.
> - 가장 위험한 불일치는 금액 차이가 아니라 **"바깥에는 있는데 안에는 없는 거래"** 다. 정산에서는 매출 누락, LLM 에서는 게이트웨이를 우회한 호출이다. 실제로 한 번 터졌다.
> - Opik 트레이스는 **원장이 아니다.** 과정을 보는 기록이고, 돈을 맞추는 데는 쓰지 않는다.

## 1. 정산: 내부 원장과 PG 파일

정산 서비스의 PG 대사 모듈은 PG 정산 파일과 내부 결제 원장을 거래 ID 로 맞대고, 어긋난 건을
6가지로 분류한다. 코드의 분류 주석을 그대로 옮기면 이렇다.

| 분류 | 뜻 | 처리 |
| --- | --- | --- |
| `MISSING_INTERNAL` | PG 파일에만 있음 — 내부 거래 누락 | **가장 위험.** 매출 누락 의심 |
| `MISSING_PG` | 내부 원장에만 있음 | PG 파일 누락 또는 정산 지연 |
| `AMOUNT_MISMATCH` | 양쪽 다 있는데 1원 이상 차이 | 운영자 검토 후 역정산 결정 |
| `DUPLICATE` | PG 파일 안에 같은 거래키 2회 이상 | 이중 청구 의심 |
| `ROUNDING_DIFF` | 1원 미만 차이 | **유일하게 자동 보정** |
| `FEE_MISMATCH` | 매출은 맞는데 실입금이 (매출 − 환불 − 공제)와 다름 | 수수료 구조 오인 또는 PG 파일 오류 |

`FEE_MISMATCH` 주석에는 이렇게 적혀 있다. *"매출 대사만으로는 절대 잡히지 않는 자금 누수 지점이다."*
그래서 파서는 금액만 읽지 않고 수수료·VAT·에스크로 수수료·이체 수수료와 `net_deposit`(실입금)까지 따로 읽는다.

대사를 둘러싼 장치도 같이 있다.

- **같은 파일을 두 번 올려도 결과가 두 번 생기지 않는다.** 업로드 파일의 SHA-256 을 저장하고, `COMPLETED` 상태에만 거는 부분 UNIQUE 인덱스로 멱등 키를 만들었다.
- **같은 결제로 정산이 두 번 생기지 않는다.** `payment_id` 에 UNIQUE 제약이 있고, 테스트가 "애플리케이션 가드를 전부 우회해도 DB 제약이 최종 방어선"임을 직접 검증한다.
- **동시 환불이 같은 정산을 이중 차감하지 못한다.** 차감 대상 정산은 `SELECT ... FOR UPDATE` 로 잠근다.
- **늦게 도착한 이벤트가 최신 상태를 덮지 못한다.** 프로젝션은 순서가 뒤바뀐 이벤트를 걸러내고 `settlement.projection.out_of_order` 메트릭을 올린다.

이 규칙들은 대부분 Claude Code 와 함께 코드와 테스트로 옮겼다. 리포의 커밋 2,187개 중 1,648개(약 75%)에
Claude 공동 작성 표시가 있고, 정산 서비스에만 테스트 메서드가 2,022개 있다. AI 가 짠 코드도 이 테스트를
통과해야 들어간다. **AI 가 쓴 코드를 믿는 근거가 테스트라면, AI 가 쓴 돈을 믿는 근거는 무엇인가** — 여기서
두 번째 질문이 시작된다.

## 2. LLM: SpendLogs 와 프로바이더 청구서

홈랩의 LiteLLM 게이트웨이는 OpenAI 4개, Gemini 4개(임베딩 포함) 모델을 하나의 OpenAI 호환 엔드포인트로
묶는다. 설정에서 대사 관점으로 중요한 줄은 두 가지다.

```yaml
general_settings:
  database_url: os.environ/DATABASE_URL   # 사용량이 여기에 쌓인다

litellm_settings:
  fallbacks:
    - gemini-2.5-flash: [gpt-4.1-mini]
    - gemini-2.5-flash-lite: [gpt-4.1-mini]
    - gemini-3-flash-preview: [gpt-4.1-mini]
```

첫째, DB 를 붙이면 LiteLLM 은 요청마다 `LiteLLM_SpendLogs` 테이블에 한 줄씩 남긴다. 키 해시, 모델 그룹,
실제 호출한 API base, 토큰 수, 비용($)이 들어간다([LiteLLM Spend Tracking][litellm-spend]).
**이게 LLM 쪽의 내부 원장이다.**

둘째, 폴백이 있다. Gemini 로 요청했는데 실패하면 `gpt-4.1-mini` 가 대신 답한다. 그러면 "요청한 모델"과
"돈이 나간 프로바이더"가 달라진다. SpendLogs 는 이걸 `attempted_fallbacks` 로 기록한다. 정산으로 치면
"주문은 A 가맹점, 결제는 B PG" 같은 상황이라, 청구서를 프로바이더별로 맞출 때 반드시 이 칸을 봐야 한다.

LiteLLM 문서는 아예 *"비용이 프로바이더 청구서와 안 맞나요?"* 라는 항목을 두고, 시간 범위를 맞추고
토큰 종류(캐시 포함)를 비교한 뒤 차이가 **수집 누락인지, 계산식 문제인지, 단가표 문제인지** 가르라고
안내한다([Debugging a cost discrepancy][litellm-discrepancy]). 정산의 분류표와 거의 같은 구조다.
단가가 비어 있어서 `$0` 으로 기록된 요청은 경고 로그와 `litellm_zero_cost_requests_total` 카운터로
따로 드러내 준다([같은 문서][litellm-spend]). 정산의 `ROUNDING_DIFF` 처럼 "조용히 넘어가기 쉬운 차이"를
시끄럽게 만드는 장치다.

## 3. 실제로 터진 불일치: 바깥에만 있던 호출

이 비유가 말장난이 아니라는 걸 보여준 사건이 있었다.
9월에 Gemini 청구서가 전월 대비 **+2,217%** 로 나왔다
([제미나이 API 청구서 ₩183,711][gemini-bill]).

원인을 찾을 때 제일 먼저 LiteLLM 게이트웨이를 의심했지만, 라우팅 로그상 Gemini 로 나간 트래픽은 미미해서
후보에서 뺐다. 범인은 게이트웨이를 **거치지 않고** Gemini 를 직접 부르던 메모리 서버였다. 1분마다 도는
동기화 크론 7대가, 쓰기 한 번마다 뒤에서 LLM 호출 8회를 일으키고 있었다.

정산 분류로 옮기면 정확히 `MISSING_INTERNAL` 이다. **외부 청구서에는 있는데 내부 원장에는 없는 거래.**
정산에서 이 분류를 "가장 위험"이라고 적어둔 이유가 그대로 드러났다. 내부 원장만 보고 있으면 아무 이상이 없어
보이고, 돈은 바깥에서 새고 있다.

여기서 얻은 규칙은 하나다. **게이트웨이가 원장이 되려면, 모든 호출이 게이트웨이를 지나야 한다.**
우회 경로가 하나라도 있으면 SpendLogs 는 "부분 원장"이고, 부분 원장으로는 대사를 할 수 없다.

## 4. Opik 트레이스는 원장이 아니다

Opik 은 에이전트가 어떤 순서로 무엇을 호출했고, 한 대화가 얼마나 길었고, 품질 점수가 어땠는지를 본다.
돈을 맞추는 도구가 아니라 **과정을 보는 도구**다.

두 기록이 자동으로 이어져 있다고 가정하면 안 된다는 것도 직접 확인했다.

- 이 게이트웨이 설정에는 LiteLLM → Opik 로 보내는 콜백이 없다. 즉 SpendLogs 와 Opik 트레이스는 지금 **따로 쌓인다.**
- Claude Code 의 트레이스를 Opik 에 넣을 때는, OTLP 익스포터가 로컬 머신 주소로만 내보낸다는 문서에 없는 동작 때문에 한참 막혔다([Claude Code 를 Opik 으로 실측하다][opik-claude]).

그래서 역할을 이렇게 나눴다.

| 질문 | 볼 곳 |
| --- | --- |
| 이번 달 얼마 나갔나, 청구서와 맞나 | LiteLLM SpendLogs ↔ 프로바이더 청구서 |
| 어떤 앱·키가 많이 썼나 | SpendLogs 의 키·태그 집계 |
| 왜 이 에이전트는 호출을 12번이나 했나 | Opik 트레이스 |
| 답변 품질이 떨어졌나 | Opik 피드백 점수 |

정산으로 치면 SpendLogs 는 **원장**, Opik 은 **거래 처리 로그**다. 원장이 틀렸을 때 원인을 찾으러 로그를
보지만, 로그로 원장을 대신하지는 않는다.

## 5. 두 시스템 대응표

| 정산 | LLM 비용 |
| --- | --- |
| 내부 결제 원장 | LiteLLM `LiteLLM_SpendLogs` |
| PG 정산 파일 | OpenAI·Google 청구서 |
| 거래 ID | 요청 ID·키 해시·시간 범위 |
| `MISSING_INTERNAL` (매출 누락) | 게이트웨이 우회 호출 |
| `FEE_MISMATCH` (수수료 구조 오인) | 캐시 토큰·단가표 불일치 |
| `ROUNDING_DIFF` 자동 보정 | `$0` 요청 경고·카운터 |
| 파일 SHA-256 멱등 키 | (아직 없음) |
| 운영자 승인 후 역정산 | (아직 없음) |

## 6. 아직 안 한 것

표의 마지막 두 줄이 비어 있는 게 이 글의 솔직한 결론이다.

- **정기 대사 잡이 없다.** 정산은 PG 파일을 올리면 자동으로 분류되지만, LLM 쪽은 청구서가 이상해 보일 때 사람이 SpendLogs 를 뒤진다. 사건이 난 뒤에야 대사를 한 셈이다.
- **예산 상한이 없다.** 설정에 키별 `max_budget` 이 없다. 정산으로 치면 한도 없는 법인카드다. Gemini 사건 때는 호출 쪽 코드에 레이트 리밋 상수를 박아서 막았는데, 이건 게이트웨이가 아니라 호출하는 쪽을 믿는 방식이다.
- **우회 경로를 기계로 막지 않았다.** "모든 호출은 게이트웨이를 지난다"는 지금 규칙일 뿐이고, 네트워크에서 프로바이더 직접 호출을 차단하지는 않았다.

다음 단계는 정산에서 이미 만든 것을 그대로 가져오는 것이다. 청구서 파일을 올리면 SpendLogs 와 맞대어
분류하는 잡, 그리고 분류 결과가 `MISSING_INTERNAL` 이면 알림. 새로 발명할 건 거의 없다. 이미 한 번 풀어 둔
문제이기 때문이다.

## 한계

- LLM 쪽 대사는 설계와 사건 1건에 기반한 글이다. 정산처럼 자동 대사를 돌려 누적 수치를 낸 건 아니다.
- SpendLogs 의 비용은 LiteLLM 단가표로 **계산한 값**이고, 실제 청구 금액은 프로바이더가 정한다. 둘이 다를 수 있다는 게 이 글의 전제다.
- 정산 쪽 수치(커밋 비율, 테스트 수)는 2026-09-28 기준 리포에서 센 값이다.

## References

- [LiteLLM — Spend Tracking][litellm-spend] (공식 문서: `LiteLLM_SpendLogs` 필드, `$0` 요청 경고)
- [LiteLLM — Debugging a cost discrepancy][litellm-discrepancy] (공식 문서: 청구서와 안 맞을 때의 대조 절차)
- [제미나이 API 청구서 ₩183,711 — 근본원인을 찾아 막기까지][gemini-bill] (이 블로그)
- [Claude Code 를 Opik 으로 실측하다 — 익스포터는 로컬 머신 밖으로 나가지 않았다][opik-claude] (이 블로그)
- [intelligence.lemuel.co.kr과 Opik으로 보는 LLM Gateway·Agent 관측성][gateway-opik] (이 블로그)

[litellm-spend]: https://docs.litellm.ai/docs/proxy/cost_tracking
[litellm-discrepancy]: https://docs.litellm.ai/docs/troubleshoot/cost_discrepancy
[gemini-bill]: /2026/09/14/gemini-api-bill-root-cause-openviking/
[opik-claude]: /2026/09/04/claude-code-traces-into-opik-exporter-is-local-only/
[gateway-opik]: /2026/09/05/litellm-gateway-opik-observability/
