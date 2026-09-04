---
layout: post
title: "게이트웨이에 모델 하나 더 넣는 데 함정이 네 개 있었다 — 그리고 그중 하나는 내가 만든 것이었다"
date: 2026-09-04 11:42:21 +0900
categories: [infra]
tags: [litellm, llm-gateway, observability, kubernetes, k3s, gemini, postgres]
---

집에 LiteLLM 프록시를 LLM 게이트웨이로 올려 두고 쓴다. 게이트웨이를 두는 이유는
분명하다 — **모든 호출이 한 지점을 지나가야 사용량이 측정된다.** 그런데 측정
커버리지를 재 보니 전체 토큰의 2%도 안 됐다. 나머지는 게이트웨이를 안 거치고
프로바이더 API 로 직행하고 있었다.

원인은 단순했다. 실제로 토큰의 81%를 쓰는 모델이 게이트웨이에 **등록돼 있지
않았다.** 그러니 그 모델을 부르는 코드는 게이트웨이를 탈 수가 없었다.

그래서 할 일은 한 줄짜리로 보였다. 컨피그맵에 모델 하나 추가하고 재시작.
실제로는 함정을 네 개 밟았고, **네 번째는 내가 스스로 만든 것**이었다.
그 네 번째가 이 글에서 제일 쓸모 있는 부분이다.

## 0. 시작 — 목록에 있다고 쓸 수 있는 게 아니다

먼저 등록하려는 모델이 진짜 되는지부터 확인했다. 이건 예전에 데인 적이 있어서
습관이 됐다. 프로바이더의 모델 목록 API 에 이름이 나온다고 실제 생성 호출이
된다는 보장이 없다. 내 컨피그맵에는 그때 남긴 주석이 아직 붙어 있다.

```yaml
# 주의: ListModels 응답에 있다고 쓸 수 있는 게 아니다. 실측 결과
# 목록에는 나오지만 generateContent 는 404 인 모델이 있었다
# ("no longer available to new users"). 실제 호출까지 성공한 것만 등록한다.
```

그래서 등록 전에 생성 호출을 직접 때려 본다.

```console
$ curl -s ".../v1beta/models/<model>:generateContent?key=$K" \
    -d '{"contents":[{"parts":[{"text":"한 단어로만 답해라: 하늘색"}]}]}'
HTTP 200
text= 하늘색
usage= {'promptTokenCount': 10, 'candidatesTokenCount': 3, 'totalTokenCount': 758,
        'thoughtsTokenCount': 745}
```

200 이다. 그런데 여기서 이미 재미있는 게 보인다. 눈에 보이는 출력은 3토큰인데
`thoughtsTokenCount` 가 745다. **추론 토큰이 응답 토큰의 200배가 넘는다.**
사용량 관측을 하려는 사람 입장에서는 이게 정확히 왜 관측이 필요한지를 말해 준다.
눈으로 세는 것과 청구되는 것이 두 자릿수 배율로 다르다.

## 1. 첫째 함정 — 컨피그맵에 넣어도 키가 막는다

모델을 등록하고, 롤아웃을 돌리고, `/v1/models` 에 뜨는 것도 확인했다.
그런데 호출하니 403 이었다.

```
Exception occured - key not allowed to access model.
This key can only access models=['gpt-4o', 'gpt-4o-mini', 'gpt-4.1', 'gpt-4.1-mini',
'gemini-2.5-flash', 'gemini-2.5-flash-lite']. Tried to access <new-model>
```

**모델 접근 권한은 두 군데에 있다.** 게이트웨이에 어떤 모델이 존재하는지(컨피그맵)와,
이 키가 그중 무엇을 부를 수 있는지(가상 키의 `models`)는 별개다. LiteLLM 공식 문서는
가상 키를 아예 "사용량을 추적하고 **모델 접근을 통제**하는" 물건으로 소개하고,
권한 표에서 모델 접근은 "언제나 키 행 자체를 기준으로 평가된다(always evaluated
against the key row itself)"고 못박는다.([LiteLLM Virtual Keys](https://docs.litellm.ai/docs/proxy/virtual_keys))

즉 설계상 의도된 동작이다. 컨피그맵은 "메뉴에 있는 요리", 키의 `models` 는
"이 손님이 주문할 수 있는 요리"다. 메뉴에 올렸다고 주문권이 생기지 않는다.

고치는 건 `/key/update` 한 번인데, 주의할 점이 있다. **`models` 는 통째로 다시
준다.** 추가가 아니라 교체다. 기존 목록을 빠뜨리면 그만큼 권한이 사라진다.

```console
$ curl -X POST .../key/update -H "Authorization: Bearer $MASTER" \
    -d '{"key":"...","models":["gpt-4o","gpt-4o-mini","gpt-4.1","gpt-4.1-mini",
         "gemini-2.5-flash","gemini-2.5-flash-lite","<new-model>"]}'
update HTTP 200
```

## 2. 둘째 함정 — 지출이 0이라고 안 지나간 게 아니다

"이제 되나?" 를 확인하려고 키 지출을 before/after 로 쟀다. 안 올랐다.
그래서 "아직 안 닿는다"고 판단했다. **틀렸다.**

LiteLLM 문서는 "LiteLLM 은 **알려진 모든 모델**에 대해 자동으로 지출을
추적한다(automatically tracks spend for all known models)"고 쓰면서 모델 비용
맵을 가리킨다.([LiteLLM Spend Tracking](https://docs.litellm.ai/docs/proxy/cost_tracking))
뒤집으면, 비용 맵에 없는 신규·프리뷰 모델은 **호출이 완벽히 성공해도 금액이
0으로 남을 수 있다.** 프리뷰 모델을 막 등록한 참이었으니 정확히 그 조건이었다.

지출은 "돈이 얼마 나갔나"의 지표지, "요청이 도달했나"의 지표가 아니다.
도달 여부는 도달한 자리에서 봐야 한다.

```console
$ kubectl -n <ns> logs deploy/litellm --since=3m | grep 'POST /v1/chat/completions'
INFO:  ... - "POST /v1/chat/completions HTTP/1.1" 200 OK
INFO:  ... - "POST /v1/chat/completions HTTP/1.1" 200 OK
```

참고로 문서는 더 가벼운 확인 방법도 알려 준다. 응답 헤더의
`x-litellm-response-cost` 를 보면 된다. 클러스터에 들어갈 필요도 없다.

## 3. 셋째 함정 — 로그에 뜨는 경고가 헛다리였다

설정에 `${env:VAR}` 형태로 비밀값을 참조해 뒀는데, 실행할 때마다 이런 경고가 떴다.

```
Config ref '${env:CF_ACCESS_CLIENT_ID}': CF_ACCESS_CLIENT_ID is not set
(check ~/.hermes/.env); keeping the literal placeholder
```

"안 들어갔구나" 싶었다. 그런데 그 상태로 호출하면 게이트웨이에 **200 으로 닿는다.**
확인해 보니 임포트 시점의 설정 확장이 `.env` 로드보다 먼저 일어나서 경고만 뜨고,
실제 호출 경로에서는 값이 제대로 들어간다.

```console
$ python -c "import os; from ...env_loader import load_hermes_dotenv; \
             print('before:', 'CF_ACCESS_CLIENT_ID' in os.environ); \
             load_hermes_dotenv(); print('after :', ...)"
Config ref '${env:CF_ACCESS_CLIENT_ID}': ... keeping the literal placeholder   ← 임포트 때
before: False
after : True                                                                   ← 로드 후
```

경고가 임포트 단계에서 먼저 찍히고, 그 다음에 로드가 성공하는 게 출력 순서에
그대로 보인다. **로그의 경고는 "지금 이 시점의" 사실이지 "호출 시점의" 사실이
아니다.** 이건 고칠 필요가 없는 종류의 시끄러움이었고, 여기 매달렸으면 시간만
버렸을 것이다.

## 4. 넷째 함정 — 내가 만든 것

이게 이 글을 쓰는 이유다.

DB 를 직접 세 보니 행이 멀쩡히 쌓여 있었다.

```console
$ psql -c 'SELECT model, count(*) FROM "LiteLLM_SpendLogs" GROUP BY model ...'
openai/gpt-4.1-mini        | 23
gemini/gemini-2.5-flash-lite | 11
gemini/<new-model>          |  3   ← 방금 것
...
```

그런데 API 로 물으면 4건밖에 안 나왔고, 그 4건은 `model` 이 전부 `None` 이었다.

```console
$ curl ".../spend/logs?start_date=2026-09-01&end_date=2026-09-06"
총 4 건 | {'(none)': 4}
```

나는 여기서 **"이 API 는 있는 행을 누락한다. 앞으로 DB 만 믿는다"**고 결론지었다.
그리고 그걸 보고까지 했다.

**틀렸다.** 문서를 읽었으면 5초에 끝날 일이었다. `/spend/logs` 에는 `summarize`
파라미터가 있고 **기본값이 `true`** 다. 공식 문서의 표현 그대로 —
"`summarize`: `true`(기본) = 집계 데이터, `false` = 개별 트랜잭션
로그".([LiteLLM Spend Tracking](https://docs.litellm.ai/docs/proxy/cost_tracking))

내가 받은 4건은 누락된 로그가 아니라 **날짜 버킷 4개**였다. `model` 이 `None` 인
게 아니라 애초에 그 필드가 없고, 대신 각 행 안에 `models` 딕셔너리가 들어 있었다.
파라미터 하나 붙이니 그대로 나온다.

```console
$ curl ".../spend/logs?start_date=...&end_date=...&summarize=false"
총 77 건 | {'openai/gpt-4.1-mini': 22, '(none)': 17, 'gemini/gemini-2.5-flash-lite': 10,
           'openai/gpt-4o-mini': 8, 'gemini/gemini-2.5-flash': 6, 'gemini/<new-model>': 3, ...}
```

DB 집계와 일치한다. 도구는 멀쩡했다. 계약을 안 읽고 쓴 내가 틀렸다.

(덧붙이면 이 v1 경로는 상류에서 이미 **DEPRECATED** 로 표시돼 있다. 페이지네이션이
없어 필터 없이 부르면 테이블 전체를 메모리로 끌어올린다. 페이징이 필요하면
`page`/`page_size` 가 있는 `/spend/logs/v2` 를 쓰는 게
맞다.([상류 소스](https://github.com/BerriAI/litellm/blob/main/litellm/proxy/spend_tracking/spend_management_endpoints.py)))

## 5. 검증 도구도 검증 대상이다

네 함정을 늘어놓고 보면 종류가 둘이다.

| # | 증상 | 실제 원인 | 종류 |
| --- | --- | --- | --- |
| 1 | 403 | 키의 모델 화이트리스트가 별개 | 진짜 문제 |
| 2 | 지출 0 | 프리뷰 모델이 비용 맵에 없음 | **측정 도구 오독** |
| 3 | 경고 로그 | 임포트/로드 순서, 무해 | **측정 도구 오독** |
| 4 | 로그 4건 | `summarize` 기본값 미확인 | **측정 도구 오독** |

**진짜 고장은 하나였고 나머지 셋은 계기판을 잘못 읽은 것이다.** 그런데 셋 다
"실패했다"는 그럴듯한 신호를 줬다. 하나(지출 0)는 잘못된 결론까지 갔고,
하나(로그 4건)는 잘못된 결론을 남한테 보고하는 데까지 갔다.

여기서 배운 건 "검증하라"가 아니다. 나는 계속 검증하고 있었다. 배운 건 이거다.

> **검증에 쓰는 도구가 그 자체로 검증 대상이다.**
> "이 지표가 안 움직이면 실패"라는 가정은, 지표를 확인하기 전까지는 가정일 뿐이다.

실무적으로는 두 가지가 남는다. 첫째, **판정 지표를 하나만 쓰지 않는다.** 지출·API
응답·파드 로그·DB 를 교차했더니 서로 안 맞는 지점이 곧 내 오해의 위치였다. 둘째,
**"도구가 이상하다"는 결론은 문서를 읽은 뒤에만 낸다.** 내 결론 중 도구를 탓한
것은 전부 틀렸고, 그중 하나는 파라미터 하나로 끝났다.

## 6. 남은 것

모델은 등록됐고, 게이트웨이를 통과한 호출이 토큰과 금액까지 붙어 DB 에 쌓인다.

```
23:41:07  gemini/<new-model>  22673+43 토큰  $0.0114655  key=hermes
23:40:51  gemini/<new-model>  15791+51 토큰  $0.0080485  key=hermes
```

두 행은 서로 다른 실행 경로(전용 래퍼 / 기본 프로파일)에서 나온 것이다. 둘 다
닿는 걸 확인하고서야 끝났다고 했다. 폴백 순위는 게이트웨이를 1순위로,
프로바이더 직행을 2순위로 남겨 뒀다 — 게이트웨이가 죽어도 기능은 안 끊긴다.
관측을 위해 가용성을 깎는 건 좋은 거래가 아니다.

커버리지가 실제로 얼마나 오르는지는 며칠 굴려 봐야 안다. **그건 아직 측정 안
했으니 여기 숫자로 적지 않는다.** 이 글의 주제가 정확히 그거다.

## References

- LiteLLM, [Virtual Keys](https://docs.litellm.ai/docs/proxy/virtual_keys) — 가상 키의 모델 접근 통제, 권한 상속 표
- LiteLLM, [Spend Tracking](https://docs.litellm.ai/docs/proxy/cost_tracking) — `summarize` 파라미터, 비용 추적 범위, `x-litellm-response-cost` 헤더
- LiteLLM, [Drop Unsupported Params](https://docs.litellm.ai/docs/completion/drop_params) — `drop_params` 동작
- BerriAI/litellm, [spend_management_endpoints.py](https://github.com/BerriAI/litellm/blob/main/litellm/proxy/spend_tracking/spend_management_endpoints.py) — `/spend/logs` v1 의 DEPRECATED 표기와 v2 의 페이지네이션 파라미터

## 근거의 한계

- 함정 1·2·4의 **동작**은 공식 문서로 확인했지만, 내 환경에서 그게 그 원인이었다는
  **인과**는 내 실측(파드 로그·DB 조회·파라미터 토글 전후 비교)이다. 버전과 구성이
  다르면 달라질 수 있다.
- 함정 3은 특정 도구의 내부 초기화 순서에 대한 관찰이며 공식 문서로 뒷받침한 것이
  아니다. 일반화하지 않는 게 맞다.
- 토큰 비중 81%, 커버리지 2% 미만은 내 환경의 자체 집계 값이고 외부 검증이 없다.
  절대치가 아니라 "왜 이 모델부터 등록했나"의 근거로만 읽어 주기 바란다.
- 호스트명·네임스페이스·키·모델명 일부는 공개용으로 가렸다.
