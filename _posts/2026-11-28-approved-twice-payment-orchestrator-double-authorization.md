---
layout: post
title: "승인이 두 번 났다 — 결제 오케스트레이터의 이중 승인과 매입 마감 (개연시 EP136 을 읽고)"
date: 2026-11-28 15:21:01 +0900
categories: [backend, payment]
tags: [결제, 멱등성, idempotency-key, 결제오케스트레이션, PG, 승인, 매입, 망취소, 개연시]
---

## 한 줄 요약

**결제 오케스트레이터가 응답을 못 받은 승인을 "실패"로 처리하고 다시 보내면, 같은 주문에 승인이 두 번 생긴다.** PG 의 멱등키는 그 PG 안에서만 유효하다. 그래서 여러 PG 를 묶는 오케스트레이터는 *주문 단위의 멱등성*을 스스로 가져야 한다. 이미 생긴 이중 승인은 **매입 전에** 취소해야 고객에게 즉시 풀린다.

---

## 0. 소재: 개연시 EP136 "APPROVED TWICE"

[개연시](https://gaeyeonsi.com/)는 실제 IT 장애 유형을 소재로, 불완전한 정보 속에서 연속으로 판단을 내리게 하는 도트 그래픽 시뮬레이션 게임이다. [EP136](https://gaeyeonsi.com/episodes/ep136) 소개문의 상황은 이렇다.

- 블프 주말 토요일 오후 5시, 쇼핑몰 "담다마켓".
- 같은 주문에 카드 승인 문자가 두 통 왔다는 문의가 들어온다.
- 재무는 결제대행사 A사의 승인 건수가 *우리 장부보다 3천 건 넘게 많다*고 한다.
- A사의 매입 마감은 6시다.
- 주인공은 두 대행사에 붙은 **결제 오케스트레이터** 담당 시니어다.
- 그런데 **결제 성공률은 평소보다 좋다.**

> 이 글은 게임의 정답을 풀지 않는다. 플레이하지 않았고, 소개문에 나온 증상만 놓고 *이런 증상이 일반적으로 어떤 메커니즘에서 나오는지*를 1차 문서로 정리했다. 게임 속 실제 원인은 다를 수 있다.

## 1. 먼저 용어: 승인과 매입은 다른 사건이다

카드 결제는 **인증 → 승인 → 매입**으로 진행된다([토스페이먼츠, 카드 결제 총정리](https://docs.tosspayments.com/resources/glossary/card-payment)).

| 단계 | 무슨 일 | 고객에게 보이는 것 |
| --- | --- | --- |
| 승인 | 카드사가 "이 결제 진행해도 된다"고 허락. 신용카드는 한도가 잡히고 체크카드는 출금된다 | 승인 문자, 결제 완료 화면 |
| 매입 | 상점(PG)이 카드사에 "이 건의 대금을 달라"고 청구 | 보이지 않음 |

고객이 받은 "승인 문자 두 통"은 매입이 아니라 **승인이 두 번** 났다는 뜻이다. 아직 돈이 최종적으로 오간 건 아니다. 그래서 마감 시각이 중요해진다.

같은 문서의 취소 정책을 보면 차이가 분명하다.

- **당일 전액취소:** 승인 취소(매입 전 취소)로 처리되고 즉시 끝난다.
- **익일 이후 취소, 부분취소:** 매입 후 취소로 처리되고 2~3 영업일이 걸린다.

[결제 취소 가이드](https://docs.tosspayments.com/guides/v2/cancel-payment)도 "매입되기 전에는 취소 직후 환불"된다고 적는다. 마감 전에 거두면 고객 입장에서는 *잠깐 잡혔다 풀린 한도*로 끝난다. 마감을 넘기면 *청구됐다가 며칠 뒤 돌아오는 환불*이 된다. 중복 청구 민원의 무게가 여기서 갈린다.

자동 매입을 쓰는 상점이라면, 승인 다음 날 PG 가 결제 건을 모아 카드사에 매입을 요청한다([토스페이먼츠, 수동 정산](https://docs.tosspayments.com/resources/glossary/manual-settlement)). 매입 마감 시각은 PG 와 계약마다 다르다. EP136 의 "6시"는 게임 속 설정이다.

## 2. 승인은 왜 두 번 나는가 — 세 가지 경로

### ① 타임아웃을 "실패"로 읽는다

가장 흔한 뿌리다. 승인 요청을 보냈는데 응답이 늦어 연결이 끊겼다. 이때 클라이언트가 아는 건 *응답을 못 받았다*는 것뿐이다. **승인이 났는지 안 났는지는 모른다.**

Stripe 문서는 이걸 정확히 짚는다. 연결이 끊기면 서버가 요청을 받았는지, 실행했는지 알 수 없다. 연결이 돌아와도 원래 요청의 성공 여부는 알려 주지 않는다([Stripe, Advanced error handling](https://docs.stripe.com/error-low-level)).

Visa Acceptance 지원 문서는 경고 상자로 못 박는다. 타임아웃이나 알 수 없는 응답은 *확정된 실패가 아니라 알 수 없는 결과*로 다뤄야 한다. 다음 행동을 하기 전에 원래 거래 ID 로 최신 상태를 조회하라고 한다([Visa Acceptance, Reversing or Deleting an Authorization](https://support.visaacceptance.com/knowledgebase/Knowledgearticle/?code=000002054)).

오케스트레이터가 이 "모름"을 "실패"로 접어 버리면, 장부에는 실패가 남고 A사에는 승인이 남는다. **"A사 승인이 우리 장부보다 많다"는 증상이 정확히 이 모양이다.**

### ② 재시도할 때 멱등키를 새로 만든다

재시도 자체는 문제가 아니다. 같은 멱등키로 재시도하면 PG 가 첫 요청의 결과를 돌려주고 두 번 처리하지 않는다.

- 토스페이먼츠는 모든 POST API 에 `Idempotency-Key` 헤더를 받는다. 키는 처음 쓴 날부터 15일간 유효하다([토스페이먼츠, 멱등키 헤더](https://docs.tosspayments.com/reference/using-api/authorization)).
- 첫 요청이 아직 처리 중이면 `409 IDEMPOTENT_REQUEST_PROCESSING` 을 돌려준다.

문제는 **시도마다 키를 새로 만들 때**다. 토스페이먼츠 문서는 에러가 났을 때 멱등키를 바꿔 같은 요청을 재시도하는 건 위험하다고 따로 적는다. Stripe 도 같은 말을 한다. `409` 가 오면 *같은 키로* 기다렸다 재시도하라고 하고, 새 키는 두 번째 작업을 시작할 수 있다고 경고한다([Stripe, Advanced error handling](https://docs.stripe.com/error-low-level)).

Stripe 문서에는 놓치기 쉬운 단서가 하나 더 있다. 재시도가 SDK 호출 한 번 안에서 끝나지 않고 *별도 호출이나 프로세스 재시작을 넘어가면*, 작업마다 키를 만들어 **저장해 두고** 모든 시도에 같은 키를 실어야 한다. 메모리에만 있던 키는 파드가 재시작되면 사라지고, 다음 시도는 새 키로 나간다.

### ③ PG 를 갈아타면 PG 의 멱등성은 따라오지 않는다

오케스트레이터 고유의 함정이다. 토스페이먼츠는 *멱등키 + API 키 + API 주소 + HTTP 메서드* 조합으로 중복을 판정한다([멱등키 헤더](https://docs.tosspayments.com/reference/using-api/authorization)). 다른 PG 들도 키의 유효 범위를 자기 계정 안으로 둔다. Stripe v2 는 "같은 계정 범위"를 조건으로 명시한다([Stripe, API v2 overview](https://docs.stripe.com/api-v2-overview)).

그러니 A사에 보낸 요청이 타임아웃 난 뒤 B사로 장애 조치(failover)하면, B사는 A사에서 무슨 일이 있었는지 알 길이 없다. 양쪽 다 정상적으로 승인한다. **두 PG 를 묶는 순간, "이 주문은 한 번만 승인한다"는 보장은 어느 PG 도 대신 해 주지 않는다.** 그 보장은 오케스트레이터 몫이다.

## 3. 성공률은 왜 오히려 좋아 보이나

EP136 소개문에서 가장 흥미로운 대목이다. 일반론으로 설명하면, 성공률을 **시도 단위**로 세는지 **주문 단위**로 세는지에 따라 같은 사고가 정반대 숫자로 보일 수 있다.

$$
\text{시도 성공률} = \frac{\text{성공 응답 수}}{\text{보낸 요청 수}}
\qquad
\text{주문 성공률} = \frac{\text{승인이 정확히 1건인 주문 수}}{\text{결제 시도 주문 수}}
$$

타임아웃 난 시도를 "실패"로 치지 않고 재시도·장애 조치로 다시 보낸다고 하자. 두 번째 시도가 성공하면 그 주문은 대시보드에서 *성공*으로 끝난다. 재시도가 공격적일수록 실패가 성공으로 "구제"되니 숫자는 좋아진다. 그런데 그 성공의 일부는 이미 A사에서 승인이 난 주문을 **한 번 더** 승인한 것이다.

성공률 지표는 *응답을 받은 쪽*만 센다. *응답을 못 받았지만 실제로는 일어난 승인*은 어떤 성공률에도 잡히지 않는다. 이런 사고는 대시보드가 아니라 **대사(reconciliation)**, 즉 PG 승인 내역과 우리 장부를 맞춰 볼 때만 드러난다. EP136 에서 이상을 처음 잡은 쪽이 모니터링이 아니라 *재무*라는 점이 그걸 보여 준다.

## 4. 이미 터졌다면: 마감 전에 거두는 순서

여기부터는 일반적인 대응 순서다(게임의 정답이 아니다).

**1) 새 이중 승인을 먼저 멈춘다.**
원인이 재시도·장애 조치 경로라면, 그 경로를 끄거나 타임아웃 뒤 재전송을 막는 게 먼저다. 거두는 사이에도 새 중복이 쌓이면 끝이 안 난다.

**2) 무엇을 취소할지 PG 쪽 기록으로 확정한다.**
- PG 승인 내역을 주문번호(`orderId`) 기준으로 묶어 *한 주문에 승인이 2건 이상*인 것을 뽑는다.
- 우리 장부가 "실패"라고 기록한 승인도 PG 에서 조회한다.
- 장부가 틀렸다는 게 이 사고의 전제이므로, **판단 근거는 PG 조회 결과**여야 한다.
- 토스페이먼츠는 같은 주문번호로 이미 승인된 결제에 다시 승인 요청이 오면 처리하지 않는다([보안과 신뢰](https://docs.tosspayments.com/reference/using-api/security-trust)). PG 가 이렇게 막아 줘도 *오케스트레이터가 시도마다 주문번호를 새로 만들거나 PG 를 바꿨다면* 막히지 않는다. 그 경우가 대사로 찾아야 할 대상이다.

**3) 남길 1건과 취소할 나머지를 정해 매입 전에 취소한다.**
- 주문당 한 건만 남긴다. 장부와 연결된 건, 배송·포인트 같은 후속 처리가 붙은 건을 남기는 게 자연스럽다.
- 취소 요청에도 **멱등키를 붙인다.** 토스페이먼츠 문서는 멱등키를 붙이면 "중복 취소 없이 안전하게" 처리된다고 적는다([코어 API, 결제 취소](https://docs.tosspayments.com/reference)).
- 급하게 수천 건을 취소하다 같은 결제를 두 번 취소하거나 남겨야 할 건을 취소하면, 사고가 하나 더 생긴다.

**4) 마감을 넘긴 건은 환불 경로로 따로 관리한다.**
매입 후 취소는 영업일 기준 며칠이 걸린다. 고객 안내 문구가 달라져야 하므로 마감 전·후 건을 나눠 둔다.

참고로 카드 네트워크 쪽에도 "응답을 못 받은 승인"을 위한 장치가 있다. Visa Acceptance 의 **타임아웃 승인 취소(timeout authorization reversal)** 는 승인 요청 뒤 응답을 못 받았을 때 그 승인을 되돌린다. 60초를 기다린 뒤 보내고, 원 요청에 실었던 거래 ID 로 묶는다([Visa Acceptance Developer, Time-Out Authorization Reversal](https://developer.visaacceptance.com/docs/vas/en-us/payments/developer/ctv/rest/payments/payments-processing-basic-intro/payments-timeout-auth-reversals-intro.html)). 국내 PG·VAN 의 "망취소"가 같은 문제를 푸는 장치인데, 구체 동작은 PG 마다 달라 각 PG 문서를 따라야 한다.

## 5. 다시 안 터지게: 오케스트레이터가 가져야 할 것

1. **결제 시도에 `UNKNOWN` 상태를 둔다.**
   `SUCCESS` / `FAILED` 두 갈래로는 타임아웃을 표현할 수 없다. `UNKNOWN` 은 *조회로 확정하기 전까지 다음 행동을 막는* 상태다. Stripe 문서도 결과를 모르면 새 키로든 옛 키로든 재시도하지 말고, 조회와 웹훅으로 먼저 대사하라고 한다([Stripe](https://docs.stripe.com/error-low-level)).
2. **멱등키는 시도가 아니라 작업(주문×PG) 단위로, 저장해서 쓴다.**
   재시작을 넘어도 같은 키가 나가야 한다. 키 설계는 IETF 초안 [The Idempotency-Key HTTP Header Field](https://datatracker.ietf.org/doc/draft-ietf-httpapi-idempotency-key-header/) 를 참고한다(아직 Internet-Draft 다). 같은 키를 다른 페이로드에 재사용하면 안 되고, 처리 중 중복 요청은 충돌(409)로 돌려준다.
3. **PG 장애 조치는 "앞 PG 의 결과가 확정된 뒤"에만 한다.**
   A사 결과가 `UNKNOWN` 이면 조회로 확정하거나 취소(망취소)가 끝난 뒤에 B사로 넘어간다. 응답이 늦다고 바로 갈아타는 건 이중 승인을 *설계로* 만드는 일이다.
4. **주문 단위 불변식을 DB 로 강제한다.**
   "한 주문에 살아 있는 승인은 최대 1건"을 유니크 제약이나 상태 전이 검사로 막는다. 애플리케이션 if 문만으로는 동시 요청을 못 막는다.
5. **매입 마감 전에 도는 대사 잡을 둔다.**
   PG 승인 내역과 장부를 주문 단위로 맞춰 보고, 차이를 *마감 전에* 사람에게 알린다. 성공률 대시보드는 이 사고를 못 본다(3장).

멱등키 자체의 설계는 이전 글 [멱등성과 멱등키]({% post_url 2026-11-10-idempotency-key-design %})와 [CS300 #138 멱등성과 재시도]({% post_url 2026-10-10-cs300-138-idempotency-and-retries %})에서 더 자세히 다뤘다.

## 근거의 한계

- **게임은 플레이하지 않았다.** EP136 의 상황 묘사는 공개된 에피소드 소개문만 참고했다. 2~3장의 메커니즘은 *이런 증상을 낳는 일반적 경로*이고, 게임 속 실제 원인이라는 주장이 아니다.
- **PG 별 차이.** 멱등키 유효 기간(토스페이먼츠 15일, Stripe v1 최소 24시간·v2 30일), 키 판정 범위, 망취소 방식, 매입 마감 시각은 PG·계약마다 다르다. 이 글의 수치는 각 문서에 적힌 값이고, 다른 PG 에 그대로 적용되지 않는다.
- **카드 네트워크 규정.** Visa 자료는 미국 지역 가맹점·Visa Acceptance 기준이다. 국내 카드사·VAN 의 망취소 규정을 1차 문서로 확인하지는 못했다.
- **성공률 해석(3장)** 은 시도·주문 단위 지표 차이에서 나온 설명이다. 실제 사고 데이터로 검증한 수치가 아니다.

## References

1. 개연시, *EP136 APPROVED TWICE* 에피소드 소개. <https://gaeyeonsi.com/episodes/ep136>
2. 토스페이먼츠 개발자센터, *카드 결제 총정리*. <https://docs.tosspayments.com/resources/glossary/card-payment>
3. 토스페이먼츠 개발자센터, *수동 정산*. <https://docs.tosspayments.com/resources/glossary/manual-settlement>
4. 토스페이먼츠 개발자센터, *결제 취소하기*. <https://docs.tosspayments.com/guides/v2/cancel-payment>
5. 토스페이먼츠 개발자센터, *인증 및 기타 헤더 설정 — 멱등키 헤더*. <https://docs.tosspayments.com/reference/using-api/authorization>
6. 토스페이먼츠 개발자센터, *보안과 신뢰*. <https://docs.tosspayments.com/reference/using-api/security-trust>
7. 토스페이먼츠 개발자센터, *코어 API*. <https://docs.tosspayments.com/reference>
8. Stripe, *Advanced error handling*. <https://docs.stripe.com/error-low-level>
9. Stripe, *Idempotent requests* (API Reference). <https://docs.stripe.com/api/idempotent_requests>
10. Stripe, *API v2 overview — Idempotency*. <https://docs.stripe.com/api-v2-overview>
11. J. Jena, S. Dalal, D. Tishkin, *The Idempotency-Key HTTP Header Field*, IETF httpapi WG Internet-Draft. <https://datatracker.ietf.org/doc/draft-ietf-httpapi-idempotency-key-header/>
12. Visa Acceptance, *Reversing or Deleting an Authorization*. <https://support.visaacceptance.com/knowledgebase/Knowledgearticle/?code=000002054>
13. Visa Acceptance Developer Center, *Time-Out Authorization Reversal*. <https://developer.visaacceptance.com/docs/vas/en-us/payments/developer/ctv/rest/payments/payments-processing-basic-intro/payments-timeout-auth-reversals-intro.html>
14. Visa, *Authorization and Reversal Processing Requirements for Merchants*. <https://usa.visa.com/content/dam/VCOM/regional/na/us/support-legal/documents/authorization-and-reversal-processing-best-practices-for-merchants.pdf>
