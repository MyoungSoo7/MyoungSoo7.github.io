---
layout: post
title: "IRP 비대면 가입 데모를 LION으로 분석하기: 금융 도메인 규칙과 프론트엔드 하네스"
date: 2026-08-09 14:00:00 +0900
categories: [Architecture, Finance, Frontend]
tags: [LION, IRP, React, TypeScript, Vite, Financial Domain, Portfolio, Computer Science Review]
---

# IRP 비대면 가입 데모를 LION으로 분석하기

## 먼저 밝히는 범위

이 글은 비공개 저장소 [`MyoungSoo7/irp-onboarding`](https://github.com/MyoungSoo7/irp-onboarding)의 기준 커밋을 읽고 LION(컴퓨터과학 종합평가) 관점으로 구조를 분석한 결과다.

```text
Repository: MyoungSoo7/irp-onboarding
Branch: main
Inspected commit: d1c9d9029ccce4c6f6d9e6405ae36180c22844af
Inspection mode: read-only source review + local test/build execution
```

저장소가 비공개이므로 이 글의 링크를 열려면 GitHub 권한이 필요하다. 글에는 실제 개인정보·금융계정·운영 API credential을 포함하지 않았다.

이 프로젝트는 실제 금융기관의 계좌개설 시스템이 아니다.

```text
실제 구현:
  React UI·상태·순수 도메인 함수·단위 테스트

데모:
  모의 본인인증·정적 상품·localStorage 이어하기·모의 전자서명

미구현/미확인:
  실명 인증기관·KYC/AML·금융기관 API·실제 계좌 개설·전자서명 법적 효력
```

## 한 문장 평가

`irp-onboarding`은 IRP 가입 여정을 React 위저드로 표현하고, 투자성향·상품 적합성·위험자산 70% 한도를 순수 TypeScript 도메인 함수와 테스트로 고정한 **금융 프론트엔드 포트폴리오 데모**다. 다만 현재는 금융기관 계정개설 시스템이 아니라 UI·도메인 규칙·상태관리의 프로토타입 단계다.

## 1. 프로젝트가 해결하려는 문제

README가 정의하는 사용자 여정은 5단계다.

```text
1. 본인확인
2. 투자성향 진단
3. 상품 선택
4. 운용비율 지정
5. 최종 확인·모의 계좌개설 완료
```

영업점 방문 없이 IRP 가입 과정을 설명하는 것이 제품의 중심이다. 따라서 이 프로젝트의 핵심 가치는 백엔드 API의 수보다:

```text
복잡한 금융 가입 절차
→ 사용자가 이해할 수 있는 단계
→ 도메인 규칙을 위반할 수 없는 UI
```

로 바꾸는 데 있다.

## 2. 전체 구조

현재 저장소의 구조는 작고 명확하다.

```text
src/
├── domain/
│   ├── allocation.ts
│   ├── riskProfile.ts
│   ├── types.ts
│   └── __tests__/
├── data/
│   ├── products.ts
│   └── questions.ts
├── state/
│   └── EnrollmentContext.tsx
├── steps/
│   ├── IdentityStep.tsx
│   ├── RiskQuizStep.tsx
│   ├── ProductSelectStep.tsx
│   ├── AllocationStep.tsx
│   └── ConfirmStep.tsx
├── pages/
│   ├── IntroPage.tsx
│   ├── WizardPage.tsx
│   └── CompletePage.tsx
└── components/
    ├── StepProgress.tsx
    └── ui.tsx
```

의존성 방향은 대체로 다음과 같다.

```text
data/types
   ↓
domain pure functions
   ↓
state/context
   ↓
steps/pages
   ↓
App/router
```

도메인 함수가 React에 의존하지 않는 구조는 좋은 선택이다. 브라우저 UI와 금융 규칙을 분리했기 때문에 향후 API·서버 검증·다른 UI로 재사용할 수 있다.

## 3. 화면 흐름과 상태 머신

`App.tsx`는 React Router와 `EnrollmentProvider`를 구성하고, `/`, `/apply`, `/complete` 경로를 제공한다.

```text
/          IntroPage
/app       WizardPage
/complete  CompletePage
```

`WizardPage`는 `state.step`에 따라 다섯 단계 컴포넌트 중 하나를 렌더링한다.

```text
step = 0 → IdentityStep
step = 1 → RiskQuizStep
step = 2 → ProductSelectStep
step = 3 → AllocationStep
step = 4 → ConfirmStep
```

`EnrollmentContext`는 `useReducer`로 다음 상태를 관리한다.

```text
step
maxStep
identity
answers
selectedIds
ratios
unsuitableAck
```

`GO` action은 현재 도달 가능한 단계보다 먼 단계로 이동하지 못하게 제한한다.

```text
step ≤ maxStep + 1
step < STEP_TITLES.length
```

이는 단순한 화면 전환이 아니라 가입 journey의 상태 전이 규칙이다.

## 4. IRP 도메인 규칙

### 4.1 투자성향 판정

`riskProfile.ts`는 7개 문항의 점수를 합산해 5단계 위험성향으로 변환한다.

```text
7~10점   STABLE
11~16점  CONSERVATIVE
17~22점  NEUTRAL
23~28점  ACTIVE
29~35점  AGGRESSIVE
```

`totalScore()`는 모든 문항이 응답되지 않으면 `null`을 반환한다.

```text
미응답 존재
→ risk grade 계산 불가
→ 다음 단계 진행 차단
```

이런 순수 함수는 UI 테스트보다 빠르고 결정론적으로 검증할 수 있다.

### 4.2 상품 적합성

상품 위험등급은 1이 매우 높은 위험이고 6이 매우 낮은 위험이다.

```text
1: 매우 높은 위험
2: 높은 위험
3: 다소 높은 위험
4: 보통 위험
5: 낮은 위험
6: 매우 낮은 위험
```

성향별 허용 기준은 `MIN_RISK_LEVEL_BY_GRADE`에 고정되어 있다. 위험한 상품을 선택하면 부적합 확인 절차가 필요하다.

```text
상품 위험등급이 성향 기준보다 위험
→ unsuitableAck 필요
```

이 구조는 “상품 선택 UI”와 “적합성 판단 규칙”을 분리한다는 점에서 포트폴리오 가치가 있다.

### 4.3 위험자산 70% 한도

`allocation.ts`는 세 가지를 검증한다.

```text
상품 선택이 비어 있지 않은가
각 비율이 1~100의 정수인가
전체 비율이 정확히 100%인가
위험자산 합계가 70% 이하인가
```

```text
riskAssetShare(entries)
→ isRiskAsset=true 상품의 ratio 합산

validateAllocation(entries)
→ EMPTY
→ INVALID_RATIO
→ SUM_NOT_100
→ RISK_LIMIT_EXCEEDED
```

중요한 점은 이 규칙이 React component 내부에 흩어지지 않고 순수 함수로 고정된다는 것이다. UI를 바꾸거나 서버 API를 추가해도 같은 정책을 재사용할 수 있다.

## 5. 데이터 흐름

### 본인확인 단계

```text
IdentityStep 입력
  → 이름·주민번호 형식·통신사·휴대폰 검증
  → 모의 인증번호 000000 확인
  → IdentityInfo 저장
```

README는 실제 개인정보를 입력하지 말라고 명시한다. 이 원칙은 중요하다.

현재 상태는 `localStorage`에 저장된다.

```text
EnrollmentState
  → localStorage: irp-onboarding-v1
  → 재방문 시 이어하기
```

다만 주민등록번호 앞자리·뒷자리 첫 숫자·휴대폰이 state에 들어가고 state 전체가 JSON으로 저장되므로, 실제 금융 시스템에서는 이 구조를 사용하면 안 된다.

```text
데모 localStorage
≠
실제 금융 개인정보 보관 설계
```

### 상품·배분 단계

```text
PRODUCTS static data
  → ProductSelectStep
  → selectedIds
  → ratios
  → validateAllocation
```

상품 데이터는 정적 fixture이며 실제 금융상품 추천 API나 상품설명서 원문과 연결되어 있지 않다.

### 최종 확인

`ConfirmStep`은 입력 정보를 요약하고 일부 값을 마스킹한 뒤 모의 전자서명과 완료 화면으로 연결한다.

이것은 UX demo로는 충분하지만 실제 시스템에서는 다음이 필요하다.

```text
서버 측 재검증
전자서명 provider
전자문서 원문 hash
동의 version
동의 시각·주체·IP/device audit
계좌개설 transaction ID
```

## 6. 테스트와 실제 실행 증거

초기 checkout에는 `node_modules`가 없어 테스트와 build가 실패했다.

```text
원인:
@vitejs/plugin-react·vitest/config·vite/client 미설치
```

의존성을 `npm ci --ignore-scripts`로 설치한 뒤 재실행했다.

```text
npm ci: 성공
npm run test:run: 성공
npm run build: 성공
```

실제 테스트 결과:

```text
Test Files: 2 passed
Tests: 14 passed
```

테스트 대상:

```text
allocation.test.ts: 7 tests
riskProfile.test.ts: 7 tests
```

빌드 결과:

```text
TypeScript noEmit: PASS
Vite production build: PASS
52 modules transformed
```

단, 설치 후 npm audit에서 다음이 보고됐다.

```text
4 vulnerabilities
3 moderate
1 high
```

이는 `npm audit fix --force`를 실행했다는 뜻이 아니며, 현재 의존성 변경은 하지 않았다. 실제 remediation은 dependency tree와 advisory를 확인한 뒤 별도 작업해야 한다.

## 7. LION 15개 컴퓨터과학 렌즈

| 영역 | 상태 | 근거와 한계 |
| --- | --- | --- |
| Programming | covered | TypeScript strict, React component, reducer, 순수 함수 |
| Data structures & algorithms | partial | 배열·filter·reduce 중심, 대규모 상품/복잡도 벤치마크는 없음 |
| Computer architecture | not evidenced | 브라우저 CPU·메모리·모바일 기기 성능 측정 없음 |
| Operating systems | partial | localStorage·브라우저 runtime은 있으나 프로세스/리소스 운영 없음 |
| Networks | not evidenced | 실제 API·TLS·timeout·retry·외부 연계 없음 |
| Databases | not applicable | DB 없음; localStorage만 사용 |
| Software engineering | covered | domain/UI 분리, reducer, 테스트, TypeScript strict |
| Web & mobile | partial | 반응형 위저드 의도는 있으나 실제 viewport·a11y 검증 미실행 |
| AI & data | not applicable | AI·추천 모델·RAG 없음, 정적 상품/설문 데이터 사용 |
| Theoretical CS | partial | 상태 전이·불변식·제약 조건이 있으나 formal model은 없음 |
| Programming languages | partial | TypeScript 타입·Vite build는 확인, compiler/runtime 심화 분석은 제한 |
| Security | partial | 민감정보 마스킹 의도와 demo 고지는 있으나 실제 auth/KMS/PII 보안 없음 |
| Graphics & multimedia | not applicable | 그래픽·미디어 pipeline 없음 |
| Distributed & cloud | not evidenced | backend·queue·cloud·multi-service 없음 |
| Mathematical foundations | partial | 점수 합산·비율 합계·70% 제약 사용, 금융 계산 검증은 제한 |

이 표에서 `covered`는 해당 영역의 모든 production 요구사항이 해결됐다는 뜻이 아니다. 저장소에서 충분한 구현 증거가 있다는 뜻이다.

## 8. 보안 분석

### 좋은 점

- README가 실제 개인정보 입력 금지를 명시한다.
- 최종 화면에서 일부 개인정보를 마스킹한다.
- 실제 인증 provider와 분리된 모의 인증이다.
- domain 규칙과 UI를 분리해 서버 재검증으로 확장하기 쉽다.
- API key·backend credential이 저장소에 보이지 않는다.

### 중요한 위험

현재 `EnrollmentState` 전체를 localStorage에 JSON 저장한다.

```text
localStorage:
  identity
  rrnFront
  rrnBackFirst
  phone
  answers
  selectedIds
  ratios
```

브라우저 localStorage는 금융 개인정보의 안전한 저장소가 아니다.

실제 전환 시:

```text
주민번호 원문 저장 금지
본인확인 provider의 opaque transaction ID만 저장
민감정보는 backend에서 제한된 lifecycle로 처리
localStorage에는 resume token·비민감 draft만 저장
XSS·CSP·session 관리 적용
```

또한 `ConfirmStep`에서 마스킹해 보여주는 것과 localStorage에 원문을 저장하지 않는 것은 별개의 문제다. 화면 마스킹은 저장 보안을 해결하지 않는다.

### 금융 도메인 검증의 한계

README는 위험자산 70% 한도를 실제 감독규정 취지와 연결한다. 포트폴리오 문장으로는 다음처럼 표현하는 것이 안전하다.

```text
IRP 데모 규칙으로 위험자산 70% 제한을 모델링했다.
실제 적용 전 상품 분류·법령·시행령·감독규정·금융기관 정책을 재검증해야 한다.
```

현재 코드는 상품이 `isRiskAsset`를 스스로 갖는 fixture 구조다. 실제 시스템에서는 상품 마스터와 규제 version이 authoritative source가 되어야 한다.

## 9. 운영·배포 평가

현재 저장소는 다음 성격이다.

```text
Vite static frontend
정적 상품·질문 data
browser local state
단위 테스트
```

장점:

- 배포 단순성
- 빠른 demo
- backend 없이 사용자 흐름 시연
- 도메인 규칙의 결정론적 테스트

부족한 운영 요소:

```text
CI workflow 증거 미확인
실제 배포 환경 미확인
error monitoring 미확인
audit log 미확인
KYC/AML adapter 미확인
backend API 미확인
rollback/release automation 미확인
```

현재 실행 가능한 운영 명령은 README 기준이다.

```bash
npm install
npm run dev
npm run test:run
npm run build
```

이번 검증에서는 `npm ci --ignore-scripts`를 사용했고 build/test는 통과했지만, npm audit 취약점 4건은 후속 검토가 필요하다.

## 10. 제품·포트폴리오 가치

이 프로젝트가 보여주는 것은 “실제 금융기관 계좌개설 경험”이 아니다. 대신 다음 역량을 보여준다.

```text
금융 업무 journey를 화면 단계로 분해
금융 규칙을 순수 함수로 분리
도메인 불변식을 단위 테스트로 고정
사용자에게 부적합 상품 확인 흐름 제공
민감정보를 화면에서 마스킹
frontend와 domain policy를 분리
```

삼성SDS·금융 IT 포트폴리오 관점에서는 다음 메시지가 적절하다.

> React 19·TypeScript 기반 IRP 비대면 가입 데모를 구현하고, 투자성향 판정·상품 적합성·위험자산 70% 한도를 UI가 아닌 순수 도메인 로직과 테스트로 분리했다.

다음 표현은 피해야 한다.

```text
실제 은행 IRP 계좌개설 시스템 구축
금융기관 KYC/AML 연동 완료
법적 효력이 있는 전자서명 구현
실제 금융상품 추천 엔진 운영
```

## 11. 개선 우선순위

### P0: 개인정보 저장 제거

```text
localStorage에 주민번호·휴대폰 원문 저장 금지
resume draft와 민감정보 분리
모의 인증은 demoTransactionId만 저장
```

### P1: 서버-클라이언트 정책 이중화

```text
client validation
  = 즉시 UX 피드백

server validation
  = 최종 신뢰 경계
```

상품 위험등급·70% 한도·동의 version은 서버가 authoritative source가 되어야 한다.

### P1: 실제 금융 상품 metadata 계약

```text
product_id
product_version
risk_level
is_risk_asset
principal_guarantee
fee
document_url
effective_from/effective_to
```

정적 fixture와 실제 상품 마스터를 명확히 분리한다.

### P1: 상태와 오류 모델 강화

```text
DRAFT
IDENTITY_PENDING
RISK_ASSESSED
PRODUCT_SELECTED
ALLOCATION_VALID
SIGNING_PENDING
SUBMITTED
COMPLETED
FAILED
```

현재 `step` 숫자만으로는 서버 작업·재시도·중복 제출·부분 실패를 표현하기 어렵다.

### P2: 접근성·브라우저 검증

```text
keyboard-only flow
screen reader name
320px width
200% zoom
focus-visible
input error announcement
```

### P2: CI와 dependency 보안

```text
npm ci
npm run test:run
npm run build
npm audit --audit-level=high
```

취약점 4건은 advisory별로 영향 범위를 확인한 뒤 fix·upgrade·accept risk를 결정한다.

## 최종 판정

```text
Verdict: conditional
```

조건:

```text
포트폴리오 데모로는 사용 가능
실제 금융 시스템으로 표현하면 안 됨
민감정보 localStorage 제거 필요
서버 authoritative validation 필요
금융상품·규제 source versioning 필요
CI·a11y·dependency 검증 보강 필요
```

## 결론

`irp-onboarding`은 작은 규모지만 금융 프론트엔드 포트폴리오에 필요한 좋은 출발점을 보여준다.

```text
UI
  → 5단계 가입 journey

Domain
  → risk profile·suitability·allocation rules

State
  → reducer·localStorage resume

Tests
  → 14개 순수 도메인 테스트

Build
  → TypeScript·Vite production build
```

가장 중요한 개선점은 기능을 더 많이 추가하는 것이 아니라 **데모와 실제 금융 시스템의 경계를 더 명확히 하고, 민감정보·서버 검증·상품 version·감사 추적을 설계에 반영하는 것**이다.

이 저장소는 다음과 같이 설명할 때 가장 정확하다.

> “React/TypeScript로 구현한 IRP 비대면 가입 journey 데모이며, 금융 도메인 제약을 순수 함수와 테스트로 모델링했다. 실제 KYC·계좌개설·전자서명 연동은 포함하지 않고, production 전환 시 개인정보 저장 제거와 서버 권위 검증이 필요하다.”

## 참고 자료

- [비공개 IRP Onboarding repository](https://github.com/MyoungSoo7/irp-onboarding)
- [LION 컴퓨터과학 종합평가 스킬](https://github.com/MyoungSoo7/leopard-github/tree/main/skills/lion)
- [React](https://react.dev/)
- [TypeScript](https://www.typescriptlang.org/)
- [Vite](https://vite.dev/)
- [Vitest](https://vitest.dev/)

> 본 분석은 비공개 저장소의 기준 커밋 `d1c9d9029ccce4c6f6d9e6405ae36180c22844af`에 대한 read-only 코드·문서·테스트/build 검토다. 운영 금융기관 연동이나 법률·규제 적합성을 인증하는 평가가 아니다.

<!-- LION verdict: conditional; source inspection only, no production mutation -->
