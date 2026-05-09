---
layout: post
title: "온체인 개발 입문 1일차 — Solidity + Hardhat 첫 컨트랙트"
date: 2026-05-09 15:00:00 +0900
categories: [blockchain, ethereum]
tags: [solidity, hardhat, ethereum, smart-contract, erc20, web3]
---

> 이 시리즈는 르무엘이 `$LMUL` ERC-20 + Academy NFT 수료증 + USDC 결제 컨트랙트를 만들면서 정리한 7일 노트입니다.

오늘은 환경 셋업 + 첫 컨트랙트 한 통.

> 이 글에서 다루는 것
> - 왜 Hardhat (vs Foundry, Truffle)
> - Solidity 5분 부트스트랩
> - 첫 컨트랙트: Counter (가장 작은 예)
> - 테스트 + 가스 측정

---

## 1. 도구 선택 — Hardhat 이유

| | Hardhat | Foundry | Truffle |
|---|---|---|---|
| 언어 | TS / JS | Solidity (forge) | JS |
| 테스트 속도 | 빠름 | **매우 빠름** | 느림 |
| 학습 곡선 | 쉬움 | 보통 | 쉬움 |
| 생태계 | **풍부** (플러그인) | 빠르게 성장 | 정체 |
| 권장 | **입문 + 풀스택** | 고성능 / 본격 운영 | 비추천 |

이번 시리즈는 Hardhat 으로 갑니다 — TS 와 잘 어울리고 OpenZeppelin 통합이 매끄럽습니다.

---

## 2. 5분 부트스트랩

```bash
mkdir lemuel-onchain-day1 && cd $_
npm init -y
npm install --save-dev hardhat @nomicfoundation/hardhat-toolbox @openzeppelin/contracts dotenv

npx hardhat init
# Create a TypeScript project (npm)
```

기본 디렉토리:

```
contracts/      ← Solidity 파일
scripts/        ← 배포 스크립트
test/           ← Mocha + Chai 테스트
hardhat.config.ts
```

---

## 3. 첫 컨트랙트 — Counter

```solidity
// contracts/Counter.sol
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract Counter {
    uint256 public count;

    event Incremented(address indexed by, uint256 newCount);

    function increment() external {
        count += 1;
        emit Incremented(msg.sender, count);
    }

    function reset() external {
        count = 0;
    }
}
```

핵심 단어 4개:

- **`pragma solidity ^0.8.24`** — 컴파일러 버전 고정
- **`uint256 public`** — 자동 getter 생성 (`counter.count()`)
- **`external`** — 외부에서만 호출 가능 (가스 절약)
- **`event`** — 블록체인 로그. 백엔드가 listen 가능

---

## 4. 컴파일 + 테스트

```typescript
// test/Counter.test.ts
import { expect } from "chai";
import { ethers } from "hardhat";

describe("Counter", () => {
  it("increments and emits event", async () => {
    const [me] = await ethers.getSigners();
    const counter = await (await ethers.getContractFactory("Counter")).deploy();
    expect(await counter.count()).to.equal(0);

    await expect(counter.increment())
      .to.emit(counter, "Incremented")
      .withArgs(me.address, 1);

    expect(await counter.count()).to.equal(1);
  });

  it("resets to zero", async () => {
    const counter = await (await ethers.getContractFactory("Counter")).deploy();
    await counter.increment();
    await counter.reset();
    expect(await counter.count()).to.equal(0);
  });
});
```

```bash
npx hardhat compile
npx hardhat test
# Counter
#   ✓ increments and emits event
#   ✓ resets to zero
# 2 passing
```

### 가스 측정

```bash
REPORT_GAS=true npx hardhat test

#  Solc version: 0.8.24
#  ·-------------|-----------|
#  | Method      | Avg Gas   |
#  ·-------------|-----------|
#  | increment   | 27,234    |
#  | reset       | 23,612    |
#  ·-------------|-----------|
```

가스를 항상 보세요. **Gwei × 가스 = 사용자가 내는 돈** 입니다.

---

## 5. 함정 모음 (입문자가 자주)

1. **Solidity 버전 미스매치** — `^0.8.24` 컨트랙트를 0.8.20 컴파일러로 빌드 시 에러
2. **`pure` vs `view` vs `payable`** — pure 는 state 안 읽음, view 는 읽기만, payable 은 ETH 받음
3. **`uint256` underflow** — 0 에서 `-1` 시 0.8 부터는 자동 revert (이전엔 underflow)
4. **`require` vs `assert` vs `revert`** — 입력 검증은 require, 내부 invariant 는 assert, 커스텀 에러는 revert
5. **이벤트 indexed 3개 한정** — 4번째부터는 indexed 안 됨 (검색 불가)

---

## 다음 학습 (7일 코스)

| Day | 주제 |
|---|---|
| 1 | Solidity 셋업 + Counter (오늘) |
| 2 | ERC-20 토큰 발행 + OpenZeppelin |
| 3 | ERC-721 NFT + 메타데이터 + Soulbound |
| 4 | 결제/Escrow 컨트랙트 + 보안 패턴 |
| 5 | testnet 배포 (Sepolia) + 검증 (Etherscan) |
| 6 | Frontend 연동 (ethers.js + MetaMask) |
| 7 | 실 운영 — 자체 노드 + 인덱서 + 백엔드 통합 |

---

> 코드 표본은 [`lemuel-token`](https://github.com/MyoungSoo7/lemuel-token) 레포에 있습니다 — 7일 끝까지의 결과물.
