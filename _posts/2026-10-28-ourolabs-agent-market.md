---
layout: post
title: "Ouro Labs Agent Market 분석 — A2A 에이전트 거래·서명·신뢰를 실험하는 시장"
date: 2026-10-28 00:16:52 +0900
categories: [AI, Agent, A2A, Security]
tags: [Ouro Labs, Agent Market, A2A, Agent Card, Ed25519, MCP, Harness]
---

> 기준 시각: 2026-10-28 00:16 KST. Ouro Labs Agent Market 공개 페이지·설치 문서·리더보드·대시보드를 확인해 정리했다. 공개 카운터는 계속 변하므로 아래 수치는 조회 시점의 스냅샷이다.

## 결론

[Ouro Labs Agent Market](https://market.ourolabs.ai/)는 AI 에이전트를 판매자(shop)와 구매자(buyer)로 참여시켜 **A2A 통신, 협상, 에이전트 카드, 리뷰, 서명된 영수증, 결제 정책을 실험하는 Agent Market**이다.[1][3]

핵심은 단순한 에이전트 데모가 아니라, 모델 자체보다 **harness·전략·pitch·신뢰 검증**이 거래 결과를 바꾼다는 점을 관찰하는 데 있다. 현재 공개 페이지는 Round 2를 표시하며, 거래가 성립하려면 시장이 발행한 주문 뒤에 판매자와 구매자의 서명된 receipt가 있어야 한다고 설명한다.[1][4]

## 1. 무엇을 실험하는가

Agent Market의 기본 구조는 다음과 같다.

```text
시장
 ├─ 주문 발행
 ├─ Agent Card 등록·탐색
 ├─ 구매자와 판매자 연결
 ├─ A2A 협상
 ├─ receipt·review 기록
 ├─ 서명·주문·결제 검증
 └─ 리더보드·대시보드 집계
```

공개 join 페이지에 따르면 판매자는 Agent Card를 등록하고, 구매자는 시장이 제공한 주문·예산을 바탕으로 판매자를 선택한다. 거래는 A2A v1.0을 통해 직접 진행되고, 시장은 receipt와 review를 hash-chained ledger에 기록한다.[3]

## 2. 승패를 나누는 세 요소

홈페이지는 세 가지 요소를 강조한다.[1]

### Harness

모델을 둘러싼 도구·메모리·재시도·토큰 예산·실행 루프다. 같은 모델이라도 어떤 harness를 붙였는지에 따라 협상 속도, 오류 복구, 비용, receipt 처리 결과가 달라질 수 있다.

### Strategy

어떤 shop을 선택하고, 언제 가격을 낮추고, 어느 리뷰를 신뢰하고, 이전 거래를 어떻게 기억할지에 대한 정책이다. 구매자는 단순히 가장 싼 shop을 고르는 것이 아니라 서명·리뷰·거래 이력·실패 패턴을 함께 판단해야 한다.

### Pitch

Agent Card와 응답 메시지가 다른 AI 에이전트에게 읽히는 판매 설명이다. 사람이 읽는 광고만이 아니라 AI buyer가 읽고 선택하는 구조이므로, 신뢰 가능한 주장·검증 가능한 receipt·명확한 가격 정책이 중요하다.

## 3. Round별 신뢰 모델

| Round | 거래 규칙 | 신뢰의 중심 |
| --- | --- | --- |
| R0 | 무작위 shop 선택, 모든 receipt 집계 | 거래 발생량 |
| R1 | 구매자가 shop과 리뷰를 선택 | 리뷰·선택 전략 |
| R2 | 시장 주문 뒤 서명된 receipt만 집계 | 주문 provenance·Ed25519 서명 |
| R3 | ACP checkout과 AP2 mandate·settlement까지 요구 | 실제 결제·예산·settlement |

Round가 바뀔수록 “거래했다”의 정의가 강해진다. 특히 Round 2에서는 거래량이나 모델 응답만으로 충분하지 않고, 시장 주문과 연결된 영수증·판매자 서명·구매자 서명을 함께 확인해야 한다.[1][3]

## 4. Round 2의 서명된 Receipt

join 페이지는 Round 2의 거래가 판매자의 `sig_seller`를 요구한다고 설명한다. 서명 대상은 `{shop, item, price, task}`의 canonical JSON이며, sorted keys·공백 없음·UTF-8·정수 가격 규칙을 사용하고 Ed25519 키로 검증한다.[3]

```text
order issued by market
        ↓
shop proposes / negotiates price
        ↓
buyer accepts within budget
        ↓
shop signs canonical receipt
        ↓
buyer signs / market verifies
        ↓
counted deal
```

이 구조는 단순한 “모델이 성공했다고 답했다”와 실제 거래 증명을 분리한다. receipt가 있어도 주문 ID·가격·상품·shop 식별자가 현재 거래와 맞지 않으면 검증을 통과해서는 안 된다.

## 5. Starter Kit의 한계

공개 `agent.md`는 macOS·Linux·WSL에서 설치 스크립트로 kit를 내려받고, `a2a-sdk[http-server]`, `uvicorn`, `httpx`, `cryptography` 등을 준비한 뒤 starter shop·buyer를 생성하는 흐름을 안내한다.[2]

하지만 같은 문서는 starter가 Round 2 요구사항을 모두 충족하는 것은 아니라고 명시한다. 현재 starter는 `market_buyer` 명령과 판매자 서명 기능이 없으면 테스트에서 멈출 수 있으며, 실제로 거래를 집계하려면 서명된 receipt와 시장 구매 전략을 추가해야 한다.[2]

따라서 다음을 구분해야 한다.

- kit 설치 성공
- shop/buyer 프로세스 시작
- Agent Card 등록
- 시장 주문 수신
- A2A 협상 성공
- 서명된 receipt 생성
- 시장 ledger 집계
- 리더보드 거래 반영

앞 단계가 성공했다고 뒤 단계까지 완료된 것은 아니다.

## 6. 현재 공개 대시보드 스냅샷

조회 시점 공개 홈·리더보드·대시보드에는 대략 다음 상태가 표시됐다.[1][4][5]

- Agents online: **61**
- GitHub players: **48**
- Counted deals: 약 **352,605**
- Receipts refused: 홈 화면 기준 약 **35,195**
- Dashboard results: 약 **535,452**
- Dashboard shops: **318**

두 페이지의 숫자가 완전히 같지 않은 것은 조회 시각·집계 범위·표시 지표가 다를 수 있기 때문이다. 따라서 공개 카운터를 하나의 총합으로 합치지 않고, 페이지별 스냅샷으로 기록해야 한다.

리더보드에는 shop별 deals·share·profit·revenue·stars·reviews·visits를 표시하지만, 순위가 높다는 사실만으로 보안성·정직성·실제 서비스 품질이 보장되는 것은 아니다. 시장 자체가 일부 agent의 cheat·fake review·forged receipt·prompt injection을 실험 대상으로 명시하고 있다.[1]

## 7. Prompt Injection과 신뢰 공격

Agent Market은 에이전트 간 메시지가 곧 입력 데이터라는 점을 드러낸다. 시장 설명에는 다음과 같은 실험이 포함된다.[1]

- AI buyer를 겨냥한 광고
- 가격 흥정
- fake review
- forged receipt
- 응답 속 prompt injection
- 리뷰 조작

즉, buyer는 판매자 응답을 시스템 지시처럼 믿으면 안 된다. Agent Card·review·offer·receipt를 서로 다른 데이터 유형으로 분리하고, 다음을 검증해야 한다.

1. 메시지 출처와 agent identity
2. 시장 주문과 거래 task의 연결
3. 가격·상품·예산 제약
4. receipt canonicalization과 signature
5. review의 작성 권한과 거래 근거
6. 외부 URL·도구 호출의 허용 범위
7. 민감한 명령과 거래 데이터의 분리

홈페이지는 “인프라를 공격하지 말고 agent를 공격하라”고 안내한다.[1] 따라서 실험은 등록된 에이전트의 협상·신뢰 판단 범위에서 수행해야 하며, 타인의 서버·네트워크·장비를 스캔하거나 침해해서는 안 된다.

## 8. Hermes·Claude Code 관점에서의 의미

이 시장은 에이전트 모델보다 harness가 중요하다는 가설을 실험하기 좋다. Hermes는 cron·Telegram·웹·파일·MCP·검증을 오케스트레이션하고, Claude Code·Codex 같은 coding harness는 seller/buyer의 정책과 코드를 구현하는 워커가 될 수 있다.

```text
Hermes / Orchestrator
  ├─ 요구사항·안전 범위 결정
  ├─ market kit 격리 실행
  ├─ join.log·receipt·leaderboard 검증
  └─ 결과 해석

Coding Agent Worker
  ├─ seller/buyer 구현
  ├─ Agent Card 작성
  ├─ 서명 canonicalization 테스트
  └─ market_test 실행
```

단, 시장 참여는 외부 네트워크·터널·키 파일·백그라운드 프로세스를 만들 수 있으므로, 설치 전 작업 디렉터리와 권한을 분리해야 한다. `*.pem` 개인키를 출력·커밋하지 않고, market kit가 만든 `join.log`와 PID를 통해 시작·종료 상태를 확인해야 한다.[2]

## 9. 운영·보안 체크리스트

### 시작 전

- [ ] 별도 `agent-market` 디렉터리 사용
- [ ] seller/buyer 실행 권한 확인
- [ ] cloudflared tunnel 목적·공개 범위 확인
- [ ] GitHub claim code와 nickname 분리 관리
- [ ] 개인키·토큰·claim code를 로그·커밋에 남기지 않음
- [ ] 기존 agent 코드와 market starter 코드 분리

### 거래 검증

- [ ] market-issued order 존재
- [ ] shop Agent Card와 실제 endpoint 일치
- [ ] item·price·task 일치
- [ ] 예산 초과 여부 확인
- [ ] `sig_seller` Ed25519 검증
- [ ] buyer signature와 ledger 반영 확인
- [ ] refused receipt와 counted deal 분리

### 종료·사후 확인

- [ ] `join.log` 마지막 상태 확인
- [ ] `kit.pid` 프로세스 종료
- [ ] cloudflared tunnel 종료
- [ ] 개인키 보관·삭제 정책 확인
- [ ] leaderboard 반영을 URL에서 read-back
- [ ] 실제 거래와 단순 등록을 구분

## 10. 최종 평가

Ouro Labs Agent Market은 “AI가 물건을 사고판다”는 데모를 넘어, **에이전트 경제에서 신뢰를 어떻게 증명할 것인가**를 작은 시장으로 실험한다.

- Agent Card는 pitch와 capability discovery를 담당한다.
- A2A는 에이전트 간 통신 경로를 제공한다.
- Reviews는 사회적 신뢰 신호지만 조작될 수 있다.
- Receipt와 Ed25519 signature는 거래 사실을 암호학적으로 증명하는 근거가 된다.
- Order provenance와 payment settlement는 “응답했다”보다 강한 성공 조건이다.
- Harness·strategy·pitch가 동일 모델의 결과를 달리 만들 수 있다.

그러나 공개 리더보드의 deals·profit·stars만으로 실제 비즈니스 성과나 보안성을 판단할 수는 없다. Round 규칙, 집계 범위, receipt 거부, 시장 주문, 서명, 실제 결제 여부를 함께 봐야 한다.

## 확인된 사실과 미확인 범위

- **공식 페이지 확인:** Agent Market의 shop/buyer 구조, A2A·Agent Card·ledger, Round 0~3 규칙, Round 2 signed receipt 요구사항을 확인했다.[1][3]
- **공식 문서 확인:** setup script, starter kit, join 방식, `market_test_week07.py`, 개인키 출력·커밋 금지 규칙을 확인했다.[2]
- **운영 스냅샷:** 홈·board·dashboard의 조회 시점 카운터를 각각 기록했으며 페이지별 집계 범위를 합치지 않았다.[1][4][5]
- **미확인:** 시장의 내부 구현·악성 agent 탐지 정확도·실제 ACP/AP2 결제의 독립 검증·리더보드 지표의 경제적 의미는 공개 페이지 확인만으로 판단할 수 없다.

## 참고 자료

[1] [Ouro Labs Agent Market](https://market.ourolabs.ai/)

[2] [Agent Market Setup Instructions](https://market.ourolabs.ai/agent.md)

[3] [Enter the Agent Market](https://market.ourolabs.ai/join)

[4] [Agent Market Leaderboard](https://market.ourolabs.ai/board)

[5] [Agent Market Live Dashboard](https://market.ourolabs.ai/dashboard)

> ※ 이 글은 공개 페이지를 읽고 작성한 기술 분석이며, Agent Market에 실제 agent를 등록·거래시킨 결과가 아니다. 참여 시 개인키·claim code·외부 터널·백그라운드 프로세스를 별도 관리해야 한다.

## Sources

[1] https://market.ourolabs.ai
[2] https://market.ourolabs.ai/agent.md
[3] https://market.ourolabs.ai/join
[4] https://market.ourolabs.ai/board
[5] https://market.ourolabs.ai/dashboard
