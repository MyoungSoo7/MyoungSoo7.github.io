---
layout: post
title: "[SE100 #048] 소비자 주도 계약 테스트"
date: 2026-10-11 17:01:47 +0900
categories: [software-engineering]
tags: [se100, software-testing, contract-testing, pact, microservices]
---

소프트웨어 공학 100 주제 시리즈의 48번째 글이다. (카테고리: 소프트웨어 테스팅)

## 한 줄 요약

**소비자 주도 계약(CDC)** 은 API 를 쓰는 쪽(소비자)이 "나는 이 요청을 보내고 응답에서 이 필드들만 쓴다" 를 실행 가능한 계약으로 적고, API 를 제공하는 쪽(제공자)이 자기 빌드에서 그 계약들을 검증하는 방식이다. 두 서비스를 함께 띄우지 않고도 "지금 이 버전을 배포해도 아무도 안 깨지는가" 에 답할 수 있다.

## 왜 필요한가

마이크로서비스 A 가 서비스 B 의 API 를 호출한다. A 의 테스트는 B 를 스텁으로 대체한다(SE100 #045). 이때 두 가지 위험이 생긴다.

1. **스텁이 거짓말을 한다.** B 가 `status` 필드 이름을 `state` 로 바꿨는데 A 의 스텁은 여전히 `status` 를 돌려준다. A 의 테스트는 초록불이고, 운영에서 깨진다.
2. **제공자가 누가 무엇을 쓰는지 모른다.** B 팀은 "`legacyCode` 필드를 지워도 되나?" 에 답할 수 없다. 그래서 아무것도 못 지우거나, 지웠다가 사고를 낸다.

가장 직관적인 해법은 A 와 B 를 함께 띄운 E2E 환경이다. 그러나 서비스가 늘수록 환경은 느리고 불안정해지고, 버전 조합은 기하급수로 늘어난다([통합 테스트와 E2E 테스트]({% post_url 2026-10-10-cs300-192-integration-and-e2e-testing %}), SE100 #044). 계약 테스트는 이 검증을 **서비스 쌍 단위로 쪼개** 각자의 빌드에서 돌린다.

## 핵심 개념

### 계약 테스트 일반

Martin Fowler 의 [ContractTest](https://martinfowler.com/bliki/ContractTest.html) (2011, 2018년 제목 변경) 는 외부 서비스를 테스트 더블로 대체하는 테스트와 별도로, **대역의 호출이 실제 서비스 호출과 같은 결과를 내는지** 확인하는 테스트를 주기적으로 돌리라고 한다. 몇 가지 운영 지침이 함께 있다.

- 계약 테스트는 내 코드의 변경 주기가 아니라 **외부 서비스의 변경 주기** 에 맞춰 돌린다. 하루 한 번이면 충분한 경우가 많다.
- 계약 테스트 실패는 일반 테스트 실패처럼 빌드를 깨기보다, 대역과 코드를 다시 맞추는 작업과 **공급 팀과의 대화** 를 촉발해야 한다.
- 계약 테스트는 정확한 데이터가 아니라 **형식** 을 확인한다.
- 예상 밖의 계약 파손을 줄이려면 **소비자 주도 계약** 으로 옮겨 가라. 공급 팀이 소비자의 계약 테스트 사본을 자기 빌드 파이프라인에서 돌리게 하는 것이다.

### Robinson 의 소비자 주도 계약 패턴

CDC 의 원전은 Ian Robinson 의 [Consumer-Driven Contracts: A Service Evolution Pattern](https://martinfowler.com/articles/consumerDrivenContracts.html) (2006) 이다. 이 글은 세 종류의 계약을 구분한다.

| 계약 | 누가 정의 | 성격 |
|---|---|---|
| 제공자 계약(provider contract) | 제공자 | 제공자가 내놓는 전체 기능 |
| 소비자 계약(consumer contract) | 개별 소비자 | 그 소비자가 실제로 기대하는 부분. **열려 있고 불완전** 하다 |
| 소비자 주도 계약(consumer-driven contract) | 모든 소비자 계약의 합 | 현재 소비자들이 요구하는 기능 전체에 대해 **닫혀 있고 완전** 하다. 제공자가 지켜야 할 의무 목록 |

글은 David Orchard 를 인용해 인터넷 프로토콜의 견고성 원칙("보낼 때는 보수적으로, 받을 때는 관대하게")을 언급하며, 소비자는 자기가 쓰는 부분만 검증하는 "딱 필요한 만큼의(just enough) 검증" 을 해야 한다고 말한다. 이렇게 하면 소비자는 제공자의 무관한 변경에 깨지지 않고, 제공자는 소비자 계약의 합을 보고 **무엇을 바꿔도 되는지** 알게 된다.

```
 소비자 A: {id, status}  ─┐
 소비자 B: {id, total}   ─┼─▶ 소비자 주도 계약 = {id, status, total}
 소비자 C: {id}          ─┘        └─ legacyCode 는 아무도 안 씀 → 제거 가능
```

### Pact 의 작동 방식

[Pact](https://docs.pact.io/) 는 HTTP 와 메시지 통합을 계약 테스트로 검증하는 코드 우선 도구다. [How Pact works](https://docs.pact.io/getting_started/how_pact_works) 의 정의로 **소비자** 는 HTTP 요청을 시작하는 쪽(데이터 흐름 방향과 무관), 큐에서는 메시지를 읽는 쪽이고, **제공자** 는 응답을 돌려주는 쪽이다.

```
[소비자 빌드]                                   [제공자 빌드]
 소비자 테스트 ─▶ Pact 목 제공자                   Pact 검증기
   (기대 요청/응답 등록)                             │ 계약의 요청을 실제 제공자에 재생
        │ 실제 HTTP 호출                             │ 실제 응답 vs 최소 기대 응답 비교
        ▼                                           ▼
   pact 파일(JSON) ──── 게시 ──▶ Pact Broker ◀── 검증 결과 게시
                                     │
                          can-i-deploy (버전 매트릭스 조회)
```

1. **소비자 테스트**: Pact DSL 로 기대 요청·응답을 목 제공자에 등록하고, 소비자 코드가 목 제공자에게 실제 요청을 보낸다. 목은 요청을 기대와 비교해 맞으면 기대 응답을 돌려준다. 모든 상호작용이 통과하면 **pact 파일** 이 생성된다.
2. **제공자 검증**: Pact 프레임워크가 pact 파일의 각 요청을 실제 제공자에 보내고, 실제 응답을 소비자 테스트에 적힌 **최소 기대 응답** 과 비교한다.
3. **제공자 상태(provider state)**: "사용자 123 생성 후 로그인" 처럼 한 테스트에 묶지 않고, "사용자 123 이 존재한다" 는 상태를 가진 별도 상호작용으로 쓴다. 제공자 쪽은 재생 전에 그 상태의 데이터를 준비한다.
4. **매트릭스와 can-i-deploy**: [Pact Broker 문서](https://docs.pact.io/pact_broker/can_i_deploy) 에 따르면 pact 를 게시하면 생성한 소비자 버전이, 검증 결과를 게시하면 검증한 제공자 버전이 기록된다. 서로 검증된 버전 조합의 표가 "Pact Matrix" 이고, `can-i-deploy` 는 이 표를 보고 특정 버전을 특정 환경에 배포해도 되는지 답한다.

## 실무 적용

### 소비자 테스트 (Pact JS, V3 API)

```javascript
import { PactV3, MatchersV3 } from '@pact-foundation/pact';
const { like } = MatchersV3;

const provider = new PactV3({ consumer: 'web-frontend', provider: 'order-service' });

it('주문 상태를 읽는다', () => {
  provider
    .given('order 42 exists')
    .uponReceiving('a request for order 42')
    .withRequest({ method: 'GET', path: '/orders/42' })
    .willRespondWith({
      status: 200,
      headers: { 'Content-Type': 'application/json' },
      body: like({ id: 42, status: 'PAID' }),   // 값이 아니라 타입·형태를 계약
    });

  return provider.executeTest(async (mockserver) => {
    const order = await new OrderClient(mockserver.url).get(42);
    expect(order.status).toBe('PAID');
  });
});
```

소비자가 쓰는 필드(`id`, `status`)만 적는다. 제공자 응답에 필드가 더 있어도 계약은 깨지지 않는다. Robinson 이 말한 "딱 필요한 만큼" 이다.

### 파이프라인

```bash
# 소비자 파이프라인 (브로커 주소·토큰은 PACT_BROKER_BASE_URL, PACT_BROKER_TOKEN 환경 변수)
npm test                                   # pact 파일 생성
pact-broker publish ./pacts --consumer-app-version "$GIT_SHA" --branch "$BRANCH"
pact-broker can-i-deploy --pacticipant web-frontend --version "$GIT_SHA" --to-environment production
# ... 배포 ...
pact-broker record-deployment --pacticipant web-frontend --version "$GIT_SHA" --environment production
```

제공자 파이프라인은 브로커에서 관련 pact 들을 받아 검증하고 결과를 게시한 뒤, 같은 `can-i-deploy` 를 통과해야 배포한다. 이렇게 하면 "제공자가 필드를 지웠는데 운영 중인 소비자 버전이 그 필드를 쓴다" 는 상황이 배포 **전에** 걸린다.

### 언제 맞고 언제 안 맞는가

Pact 문서 [What is it good for?](https://docs.pact.io/getting_started/what_is_pact_good_for) 는 조직 내부 마이크로서비스 개발·테스트에 특히 좋다고 하면서, 다음에는 맞지 않는다고 명시한다.

- 반대편 팀이 Pact 를 함께 쓰지 않는 API
- 소비자를 개별적으로 식별할 수 없는 API(예: 공개 API)
- 테스트 대상 API 를 쓰지 않고는 제공자에 데이터를 넣을 수 없는 경우
- 특정 소비자의 필요가 아니라 독자적으로 정해지는 안정된 제공자(예: OAuth 제공자)

공개 API 처럼 소비자를 모를 때는 제공자가 정의한 스키마(OpenAPI 등)를 기준으로 검증하는 제공자 주도 방식이 현실적이다. [Spring Cloud Contract](https://docs.spring.io/spring-cloud-contract/reference/) 처럼 소비자 주도와 생산자 주도 계약 테스트를 모두 지원하는 도구도 있다.

## 흔한 오해와 함정

- **계약 테스트로 비즈니스 로직까지 검증한다.** Pact 문서 [Contract Tests vs Functional Tests](https://docs.pact.io/consumer/contract_tests_not_functional_tests) 는 계약 테스트가 소비자와 제공자 사이를 오가는 **메시지** 에 집중하고, 올바른 부수효과(예: 주문이 실제로 저장됐는가)는 기능 테스트의 몫이라고 구분한다. 계약에 "잔액 부족이면 402" 같은 규칙을 수십 개 넣으면 제공자 팀은 사실상 소비자가 쓴 기능 테스트를 떠안는다.
- **정확한 값을 계약한다.** `body: { id: 42, status: 'PAID', createdAt: '2026-…' }` 를 그대로 계약하면 데이터가 바뀔 때마다 깨진다. 매처(`like`, `eachLike`)로 형태를 계약한다.
- **소비자가 쓰지도 않는 필드를 넣는다.** "혹시 몰라서" 넣은 필드는 제공자의 변경 자유를 빼앗는다.
- **브로커와 can-i-deploy 없이 파일만 주고받는다.** 어떤 소비자 버전이 운영에 있는지 모르면 "이 제공자 버전이 안전한가" 에 답할 수 없다.
- **E2E 를 모두 없앤다.** 계약 테스트는 형식 호환성을 본다. 배포 설정, 네트워크 정책, 인증 같은 것은 여전히 소수의 E2E·스모크 테스트가 필요하다.

## 확인 문제

1. 소비자 계약과 소비자 주도 계약의 차이를 Robinson 의 "열림/닫힘" 특성으로 설명하라.
2. Pact 에서 HTTP 응답 데이터가 제공자에서 소비자로 흐르는데도 요청을 보내는 쪽을 소비자라 부르는 이유는?
3. 제공자 상태(provider state)를 쓰는 이유는?
4. `can-i-deploy` 가 답하는 질문은 무엇이며, 그 답을 위해 브로커가 기록하는 정보는?
5. 공개 결제 API 를 운영하는 팀에 Pact 를 권하기 어려운 이유와 대안은?

### 풀이

1. 소비자 계약은 한 소비자가 기대하는 부분만 담아 제공자 기능 전체에 대해 열려 있고 불완전하다. 소비자 주도 계약은 현재 모든 소비자 계약을 합친 것으로, 소비자들이 요구하는 기능 전체에 대해 닫혀 있고 완전하며 제공자가 지켜야 할 의무가 된다.
2. Pact 의 정의는 데이터 흐름이 아니라 상호작용을 시작하는 쪽을 기준으로 한다. HTTP 에서는 요청을 시작하는 애플리케이션이 다른 애플리케이션의 기능이나 데이터를 이용하는 쪽이다.
3. 상호작용을 독립적으로 유지하기 위해서다. 앞선 요청의 부작용에 기대지 않고 "사용자 123 이 존재한다" 같은 전제 상태를 이름으로 선언하면, 제공자 검증 시 그 상태를 직접 준비한 뒤 요청을 재생할 수 있다.
4. "이 애플리케이션의 이 버전을 이 환경에 배포해도 그 환경의 다른 애플리케이션들과 호환되는가" 다. 브로커는 pact 를 만든 소비자 버전, 그 pact 를 검증한 제공자 버전과 결과, 그리고 각 환경에 배포된 버전을 기록한다.
5. 소비자를 개별적으로 식별할 수 없고 그들이 Pact 를 함께 쓰지도 않으며, API 가 특정 소비자의 필요로 바뀌지 않는다. 제공자가 정의한 스키마를 기준으로 하위 호환성을 검사하는 제공자 주도 계약 테스트가 맞다.

## 더 읽을거리 (References)

- Ian Robinson, [Consumer-Driven Contracts: A Service Evolution Pattern](https://martinfowler.com/articles/consumerDrivenContracts.html), martinfowler.com, 2006
- Martin Fowler, [ContractTest](https://martinfowler.com/bliki/ContractTest.html)
- Pact 문서, [Introduction](https://docs.pact.io/), [How Pact works](https://docs.pact.io/getting_started/how_pact_works), [Provider states](https://docs.pact.io/getting_started/provider_states), [Can I Deploy](https://docs.pact.io/pact_broker/can_i_deploy), [What is it good for?](https://docs.pact.io/getting_started/what_is_pact_good_for), [Contract Tests vs Functional Tests](https://docs.pact.io/consumer/contract_tests_not_functional_tests)
- Spring Cloud Contract, [Reference Documentation](https://docs.spring.io/spring-cloud-contract/reference/)
