---
layout: post
title: "Hermes 무료 버전과 월 20달러 Plus의 차이 — 모델·도구·크레딧·운영비를 분리해서 보기"
date: 2026-10-26 02:04:04 +0900
categories: [AI, Hermes, Agent, Automation]
tags: [Hermes Agent, Nous Portal, Free, Plus, Tool Gateway, Pricing]
---

> 기준 시각: 2026-10-26 02:04 KST. 가격과 제공 범위는 Nous Portal 공개 페이지와 Hermes 공식 문서를 확인해 정리했다. 실제 한도·모델 목록·도구 가격은 계정·시점·정책에 따라 달라질 수 있다.

## 결론

Hermes 프로그램 자체는 무료로 설치·실행할 수 있지만, **무료 Nous Portal 요금제와 월 20달러 Plus는 inference 모델 접근·월간 크레딧·호스팅 도구·요청 한도에서 차이가 난다**. 무료 버전은 무료 모델과 표준 한도로 시작하는 선택이고, Plus는 월 20달러로 22달러의 월간 크레딧과 200개 이상의 모델·호스팅 도구·높은 한도를 제공하는 선택이다.[1][2]

## 1. 먼저 구분해야 할 세 가지

### Hermes Agent 프로그램

Hermes Agent는 로컬에 설치해 사용할 수 있는 에이전트 런타임이다. 공식 Quickstart는 macOS·Linux·WSL2에서 설치하고, provider와 모델을 선택한 뒤 일반 채팅이 동작하는지 검증하도록 안내한다.[7] 따라서 **Hermes 설치 비용**과 **어떤 inference/provider를 선택할지**는 별개의 문제다.

### Nous Portal 요금제

Nous Portal은 Hermes에서 모델과 관리형 도구를 사용할 수 있게 하는 계정·과금 계층이다. 공개 요금표에는 Free, Plus, Super, Ultra가 별도로 표시된다.[1][2]

### Hermes Cloud

Hermes Cloud는 상시 실행되는 호스팅 인스턴스다. 클라우드 인스턴스의 컴퓨트·스토리지 비용과 inference·도구 사용료는 구독 요금과 별도로 확인해야 한다.[2] 따라서 Plus에 가입했다고 곧바로 클라우드 호스팅 비용까지 모두 포함된다고 해석하면 안 된다.

## 2. Free와 Plus 비교

| 항목 | Free | Plus |
| --- | --- | --- |
| 월 구독료 | $0 | $20/월 |
| 월간 Nous 크레딧 | $0 | $22 — 10% 보너스 포함 |
| 크레딧 이월 | 공개 요금표상 별도 Plus 이월 한도 없음 | $10 rollover cap |
| 모델 | 무료 모델만 | 200개 이상 모델 |
| 호스팅 도구 | 유료 구독 기반 도구 게이트웨이 대신 계정에 표시되는 무료 범위·표준 한도 확인 필요 | Hosted tool usage, 높은 한도 |
| 요청·사용 한도 | Standard rate limits | High rate limits |
| 도구 과금 | 자체 키 또는 무료 범위·제공 조건에 따름 | 사용한 모델·도구가 같은 Nous 크레딧에서 차감될 수 있음 |
| Hermes 로컬 실행 | 가능 — provider·키·로컬 환경에 따라 별도 | 가능 |

위 표에서 “무료”는 “모든 도구와 모든 모델을 무제한으로 무료 사용”이라는 뜻이 아니다. 공개 Portal 페이지는 Free를 **무료 모델만, 표준 한도, 월간 크레딧 $0**으로 표시하고, Plus를 **월 $20, 월간 크레딧 $22, 200개 이상 모델, 호스팅 도구, 높은 한도**로 표시한다.[1][2]

## 3. Plus에서 실제로 달라지는 부분

### 3.1 모델 선택 폭

Plus는 공개 요금표상 200개 이상의 모델을 제공한다.[1][2] Hermes 공식 Portal 문서는 여러 연구소의 모델을 하나의 Portal 계정과 청구 체계로 전환할 수 있다고 설명한다.[4] 모델마다 가격과 성능·도구 호출 특성이 다르므로, Plus가 특정 모델의 품질을 보장한다거나 모든 모델이 동일하게 동작한다고 해석해서는 안 된다.

### 3.2 월간 크레딧

Plus의 공개 표시는 월 20달러 결제에 22달러 월간 크레딧을 더하는 구조다.[1] 이 크레딧은 모델 inference와 관리형 도구 사용에 쓰일 수 있으며, 실제 사용량은 선택한 모델·입출력 토큰·도구 호출에 따라 달라진다.[2][3]

따라서 “월 20달러를 냈으니 모델을 무제한 사용한다”가 아니라 **월 22달러 상당의 사용 크레딧과 높은 요청 한도를 받는다**고 이해하는 것이 정확하다. Plus의 월 크레딧을 모두 사용하면 추가 top-up·다음 결제 주기·다른 provider가 필요할 수 있다.

### 3.3 Tool Gateway

Hermes 공식 문서에 따르면 유료 Nous Portal 구독은 Web Search·Extract, 이미지 생성, TTS, 클라우드 브라우저 자동화를 Nous가 관리하는 Tool Gateway로 사용할 수 있게 한다.[4][5] 이 방식은 검색 업체·이미지 생성 업체·브라우저 업체·음성 API를 각각 가입하고 키를 관리하는 대신 하나의 Portal 인증과 과금 경로로 묶는 장점이 있다.[4]

도구 호출도 공짜 무제한이 아니다. Tool Gateway 문서는 네 가지 관리형 도구가 사용량 기반으로 청구된다고 설명한다.[5] Plus 이용자는 `hermes tools`에서 모든 도구를 자동으로 켜기보다 필요한 도구만 선택하고, Portal 잔액과 도구별 사용량을 확인해야 한다.

## 4. Free에서도 가능한 선택지

Free 또는 Nous 구독 없이도 Hermes를 사용할 수 있는 경로가 모두 사라지는 것은 아니다.

- 자체 API 키를 가진 provider 연결
- 무료 모델을 제공하는 provider 사용
- 로컬 Ollama·LM Studio·OpenAI-compatible endpoint 사용
- 자체 웹 검색·TTS·브라우저 provider 연결
- 무료 범위가 있는 관리형 도구 사용

공식 문서는 Hermes가 여러 provider와 custom endpoint를 지원하며, 로컬 모델은 최소 64K context가 필요하다고 설명한다.[7] 웹 검색 문서도 API 키가 없을 때 여러 공개 무료 tier를 순환하는 경로와, 자체 Firecrawl·SearXNG·Brave 등의 연결 경로를 설명한다.[6]

다만 자체 provider를 연결하면 API 키 발급·한도·청구·장애·보안을 사용자가 직접 관리해야 한다. Free는 비용을 0으로 만드는 마법이라기보다 **Nous Portal 구독을 선택하지 않고 다른 provider·무료 모델·로컬 실행을 조합하는 방식**에 가깝다.

## 5. Plus가 유리한 경우와 Free가 충분한 경우

### Plus가 유리한 경우

- Claude·GPT·Gemini·Qwen 등 여러 모델을 한 계정에서 번갈아 사용해야 하는 경우
- 웹 검색·페이지 추출·브라우저 자동화·이미지 생성·TTS를 API 키 여러 개 없이 사용해야 하는 경우
- Hermes를 Telegram·cron·블로그 자동화처럼 반복 운영하는 경우
- 표준 한도에 자주 걸리거나 긴 에이전트 작업을 안정적으로 이어가야 하는 경우
- 모델과 도구 사용량을 하나의 Portal 잔액에서 관리하려는 경우

### Free가 충분한 경우

- 가벼운 대화와 무료 모델 위주로 사용하는 경우
- 로컬 모델 또는 자체 API 키를 이미 보유한 경우
- 브라우저·이미지·TTS·웹 검색을 매일 쓰지 않는 경우
- 요청량이 적고 표준 한도로 충분한 경우
- 월 비용보다 직접 구성·운영하는 통제권을 우선하는 경우

## 6. 이 사용자 환경에 적용할 때의 판단 기준

현재 이 블로그의 Hermes 사용은 Nous 모델, Telegram, cron, 웹 조사, 브라우저·파일 작업, GitHub Pages 게시 검증을 결합한다. 이 유형은 단순 채팅보다 모델 호출과 도구 호출이 반복되므로 Free의 표준 한도만으로는 중단·지연·무료 모델 전환이 발생할 가능성을 운영 전에 확인해야 한다. 이 문장은 계정별 실제 사용량을 측정한 비용 예측이 아니라, 공식 요금 구조와 현재 워크플로우를 결합한 운영 판단이다.

권장 운영 순서는 다음과 같다.

1. 모델별 사용량과 도구 사용량을 Portal에서 분리해 확인한다.
2. Plus의 월 22달러 크레딧을 모델 inference와 Tool Gateway에 어떻게 배분할지 정한다.
3. 매일 브리핑·블로그 게시 같은 작업은 성공 여부를 commit·Pages workflow·공개 URL로 검증한다.
4. 잔액 부족에 대비해 자체 API provider 또는 로컬 모델을 fallback으로 준비한다.
5. 비용을 줄이려면 브리핑 수집은 저비용 모델·스크립트로, 최종 편집·검증은 더 강한 모델로 분리한다.

## 확인된 사실과 미확인 범위

- **확인된 사실:** 공개 Portal 요금표의 Free·Plus 가격·월간 크레딧·모델 수·한도 표기.[1][2]
- **확인된 사실:** 유료 구독의 Tool Gateway 범위와 사용량 기반 도구 과금 안내.[4][5]
- **확인된 사실:** Hermes가 여러 provider·custom endpoint·무료 웹 검색 경로를 지원한다는 공식 문서.[6][7]
- **미확인:** 계정별 실제 잔액, 특정 모델의 실제 토큰 단가, 도구별 예상 월 비용, Free 계정에 표시되는 무료 tool pool의 정확한 크기. 이 값은 계정·시점·사용량을 Portal에서 확인해야 한다.

## 참고 자료

[1] [Nous Portal — Choose a Plan](https://portal.nousresearch.com/manage-subscription)

[2] [Nous Portal](https://portal.nousresearch.com/)

[3] [Nous Portal API Docs](https://portal.nousresearch.com/api-docs)

[4] [Hermes Agent — Nous Portal](https://hermes-agent.nousresearch.com/docs/integrations/nous-portal)

[5] [Hermes Agent — Nous Tool Gateway](https://hermes-agent.nousresearch.com/docs/user-guide/features/tool-gateway)

[6] [Hermes Agent — Web Search & Extract](https://hermes-agent.nousresearch.com/docs/user-guide/features/web-search)

[7] [Hermes Agent — Quickstart](https://hermes-agent.nousresearch.com/docs/getting-started/quickstart)

> ※ 가격·모델 카탈로그·무료 범위·도구 단가는 변경될 수 있으므로 결제 전 Nous Portal의 현재 화면과 계정별 표시를 재확인해야 한다.

## Sources

[1] https://portal.nousresearch.com/manage-subscription
[2] https://portal.nousresearch.com
[3] https://portal.nousresearch.com/api-docs
[4] https://hermes-agent.nousresearch.com/docs/integrations/nous-portal
[5] https://hermes-agent.nousresearch.com/docs/user-guide/features/tool-gateway
[6] https://hermes-agent.nousresearch.com/docs/user-guide/features/web-search
[7] https://hermes-agent.nousresearch.com/docs/getting-started/quickstart
