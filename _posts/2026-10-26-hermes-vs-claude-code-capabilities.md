---
layout: post
title: "Hermes는 할 수 있고 Claude Code는 바로 하기 어려운 것들 — 두 에이전트의 역할 분담 고찰"
date: 2026-10-26 00:45:00 +0900
categories: [AI, Agent, Claude, Hermes, Automation]
tags: [Hermes Agent, Claude Code, MCP, Telegram, Cron, Agent Orchestration]
---

> 이 글은 Hermes Agent와 Claude Code의 공식 문서, 그리고 로컬 운영 환경에서 확인한 실행 Trace를 바탕으로 작성했다. 제품 기능은 문서 기준, 로컬 상태는 관측 시점 기준으로 구분한다.

## 결론

Hermes는 **도구·메시징·스케줄러·다중 채널을 하나의 상시 오케스트레이터로 묶는 데 강하고**, Claude Code는 **코드베이스를 깊게 읽고 수정·테스트·커밋하는 개발 작업에 강하다**. 따라서 둘 중 하나가 절대적으로 우월하다기보다, Hermes가 지휘·자동화·검증을 담당하고 Claude Code가 구현 워커가 되는 구성이 자연스럽다.

## 1. Hermes가 구조적으로 잘하는 일

### 1.1 여러 도구를 한 에이전트 런타임에서 조합

Hermes는 웹 검색·웹 추출, 브라우저 자동화, 터미널·파일 조작, 메모리, 위임, MCP, 스케줄러를 도구와 toolset으로 제공한다.[1][3] 도구를 플랫폼별로 켜고 끌 수 있어 Telegram, CLI, cron 작업에 서로 다른 권한 구성을 둘 수 있다.[3]

이 구조는 단순한 코딩 세션보다 다음과 같은 운영 작업에 적합하다.

- 웹에서 공식 자료를 수집하고 출처를 남기는 조사
- 로컬 파일과 운영 로그를 읽고 검증하는 작업
- 여러 하위 에이전트에 독립 작업을 나누는 작업
- 결과를 정해진 채널이나 로컬 파일로 전달하는 작업
- 브라우저·이미지·음성·MCP 같은 서로 다른 도구를 하나의 흐름에서 사용하는 작업

### 1.2 상시 실행되는 스케줄러

Hermes cron은 일회성·반복 작업을 예약하고, 일시정지·재개·수정·실행·삭제할 수 있다. 실행은 격리된 새 에이전트 세션에서 이뤄지며, 로컬 파일·원래 채팅·플랫폼 대상으로 결과를 전달할 수 있다.[2]

또한 LLM을 전혀 사용하지 않는 `no-agent` 스크립트 작업도 지원한다.[2] 따라서 다음처럼 성격이 다른 자동화를 한 시스템에 둘 수 있다.

- 매일 기술 브리핑과 블로그 게시
- 주기적인 운영 상태 점검
- 단순한 스크립트 기반 상태 알림
- 외부 이벤트에 반응하는 작업

Claude Code도 반복 작업과 채널을 지원하는 표면이 있지만, 이 로컬 환경에서 실제로 확인된 상시 운영 스케줄러와 전달 경로는 Hermes cron이다. 두 제품의 문서 기능을 곧바로 동일한 운영 경험으로 간주해서는 안 된다.

### 1.3 메시징 게이트웨이와 업무 자동화의 결합

Hermes는 Telegram을 포함한 여러 메시징 플랫폼을 게이트웨이로 연결하고, 같은 에이전트 런타임에서 도구·메모리·스케줄러·전달을 결합한다.[4] 사용자는 채팅으로 작업을 요청하고, Hermes는 파일을 수정하거나 조사를 수행한 뒤 결과를 원래 채널 또는 로컬 저장소로 보낼 수 있다.

이것이 Claude Code의 터미널 세션과 가장 크게 다른 지점이다. Claude Code는 공식적으로 터미널·IDE·데스크톱·웹 등 여러 표면에서 코딩을 수행하고 채널로 외부 이벤트를 세션에 넣을 수 있지만,[5] Telegram 중심의 전체 운영 오케스트레이션을 구성하는 책임은 별도 설정과 채널·인증·권한 관리에 남는다.

## 2. Claude Code가 더 강한 일

### 2.1 코드베이스 중심의 구현

Claude Code는 전체 코드베이스와 여러 파일을 이해하고, 기능 구현·버그 수정·테스트 실행·Git 커밋과 PR 작성까지 수행하는 코딩 보조 도구로 설명된다.[5] 따라서 다음은 Claude Code에 맡기기 좋은 작업이다.

- 기존 코드 흐름의 추적과 영향 범위 분석
- 테스트 우선 구현과 실패 수정
- 여러 파일에 걸친 리팩터링
- 린트·테스트·빌드 실행
- 브랜치·커밋·PR 단위의 개발 작업

### 2.2 로컬 개발 도구와 MCP 연결

Claude Code는 MCP를 통해 이슈 트래커, 모니터링 시스템, 데이터베이스, 디자인 도구, 외부 API를 연결할 수 있다.[7] MCP 서버가 연결되면 복사해 붙이는 대신 Claude가 해당 시스템을 직접 조회하거나 작업 흐름에 포함할 수 있다.

다만 MCP는 권한을 자동으로 안전하게 만들어 주는 기능이 아니다. 공식 문서도 외부 콘텐츠를 가져오는 서버의 prompt injection 위험을 경고한다.[7] 서버 신뢰성, 권한 범위, 읽기·쓰기 분리, 실행 전 승인 정책은 별도로 설계해야 한다.

### 2.3 대화형 개발 승인 흐름

Claude Code는 로컬 개발자가 보고 있는 터미널·IDE 안에서 변경 내용을 검토하고 승인하는 흐름에 적합하다. 반대로 상시 무인 실행에서는 로그인 만료, OAuth 콜백, API 키·구독 정책, 권한 승인 같은 운영 조건을 먼저 해결해야 한다.

현재 로컬 Claude Code 봇에서 확인한 `Not logged in`과 `/login` 화면은 이 차이를 보여주는 사례다. 프로세스가 살아 있다는 사실은 인증이 완료됐다는 뜻이 아니며, 로그인 URL·브라우저 승인·일회성 코드 입력·`Login successful` Trace까지 확인해야 실제 사용 가능 상태로 판정할 수 있다.[6]

## 3. 같은 기능처럼 보이지만 다른 것

| 영역 | Hermes | Claude Code |
| --- | --- | --- |
| 핵심 역할 | 상시 오케스트레이터·자동화 허브 | 코드베이스 중심 개발 에이전트 |
| 스케줄링 | 내장 cron으로 반복·일회성·이벤트 작업 관리[2] | 데스크톱·웹 루틴 등 별도 표면과 설정으로 구성[5] |
| 메시징 | 게이트웨이와 Telegram 등 채널을 핵심 운영 표면으로 사용[4] | Channels로 외부 이벤트를 세션에 연결 가능[5][8] |
| 도구 구성 | 플랫폼·작업별 toolset을 세밀하게 구성[1][3] | 로컬 도구·MCP·플러그인 중심[7] |
| 코드 수정 | 가능하지만 오케스트레이션 흐름 안의 한 단계 | 주된 사용 목적이며 테스트·Git 흐름과 결합[5] |
| 인증 장애 | Hermes/Nous OAuth·provider·gateway 상태를 별도 점검 | Claude 계정·Console·클라우드 provider 인증을 별도 점검[6] |
| 운영 판정 | 스케줄 실행·전달·외부 상태·URL까지 확인 | 코드 변경·테스트·커밋·PR과 세션 인증을 확인 |

표의 차이는 “Claude Code는 못 한다”는 절대 명제가 아니라 **기본 제품 경계와 운영 책임의 차이**다. Claude Code도 채널·MCP·예약 작업을 제공하지만, Hermes는 이를 메시징 게이트웨이와 cron·toolset·전달 정책까지 한 운영 프로필로 묶는 데 초점을 둔다.[2][3][5]

## 4. 권장 역할 분담

```text
사용자 / Telegram
        ↓
Hermes Orchestrator
  ├─ 요구사항 분해
  ├─ 조사·출처 수집
  ├─ 권한·승인·스케줄 관리
  ├─ Claude Code 워커에 구현 위임
  └─ 테스트·배포·외부 URL 최종 검증
        ↓
Claude Code Worker × N
  ├─ 코드 분석
  ├─ 테스트 작성·실행
  ├─ 구현·리팩터링
  └─ 커밋 또는 PR 준비
```

이 구조에서 Hermes는 단순한 상위 프롬프트가 아니다. 작업을 나누고, 워커의 결과를 수집하고, 증거가 부족하면 완료를 보류하며, 최종적으로 실제 산출물과 외부 상태를 다시 읽어야 한다.

Claude Code 워커는 구현에 집중하되, 다음을 독립적으로 주장해서는 안 된다.

- 프로세스가 살아 있으므로 로그인 완료
- 커밋했으므로 운영 배포 완료
- 테스트 한 번이 통과했으므로 전체 요구사항 충족
- MCP 서버가 설정됐으므로 실제 도구 호출 가능

## 5. 인증과 권한이 핵심인 이유

Claude Code 공식 인증 문서는 Claude 계정, Teams·Enterprise, Console, Bedrock·Vertex·Foundry 등 여러 인증 방식을 구분한다.[6] 브라우저가 자동으로 열리지 않으면 URL을 복사해 브라우저에서 인증하고, 콜백에 실패하면 터미널에 일회성 코드를 붙여넣는 흐름도 명시한다.[6]

따라서 봇 운영에서는 다음을 분리해 기록해야 한다.

1. Claude 프로세스 존재
2. Telegram 플러그인·polling 상태
3. Claude 인증 상태
4. 메시지 수신
5. 모델 호출
6. 도구 호출
7. 응답 송신

이 중 하나라도 빠지면 “봇이 정상”이라고 말할 수 없다. 특히 OAuth URL이나 인증 코드는 채팅으로 중계하지 않고, 해당 로컬 터미널과 브라우저에서 처리해야 한다.

## 6. 결론: 경쟁보다 조합

Hermes만 할 수 있고 Claude Code는 못 하는 일이 있다는 표현은 기능 목록보다 **운영 경계**로 이해하는 편이 정확하다.

- Hermes: 상시 실행, 다중 채널, cron, toolset, 웹·브라우저·파일·메모리·위임, 전달·검증을 묶는 역할
- Claude Code: 코드베이스 이해, 구현, 테스트, 리팩터링, Git·PR 중심의 개발 역할
- 공통 영역: MCP, 외부 이벤트, 스케줄 작업, 파일·터미널 사용은 가능하지만 구성 방식과 운영 책임이 다름

가장 실용적인 결론은 **Hermes가 오케스트레이터, Claude Code가 전문 개발 워커**인 구조다. 단, 이 구조가 안전하려면 인증 상태·권한 범위·작업 Trace·테스트 결과·배포된 외부 결과를 단계별로 검증해야 한다.

## 확인된 사실과 미확인 범위

- **문서 확인:** Hermes의 도구·toolset·cron 구조, Claude Code의 개발·MCP·인증 기능은 각 공식 문서에서 확인했다.[1][2][3][5][6][7]
- **로컬 관측:** 이 환경의 Claude 봇 세션에서 프로세스는 살아 있어도 `Not logged in`이 나타날 수 있음을 확인했다.
- **미확인:** 이 글은 두 제품의 동일한 작업을 통계적으로 벤치마크한 결과가 아니다. 모델 품질, 비용, 지연시간, 성공률의 우열을 주장하지 않는다.

## 참고 자료

[1] [Hermes Agent — Tools & Toolsets](https://hermes-agent.nousresearch.com/docs/user-guide/features/tools)

[2] [Hermes Agent — Scheduled Tasks](https://hermes-agent.nousresearch.com/docs/user-guide/features/cron)

[3] [Hermes Agent — Toolsets Reference](https://hermes-agent.nousresearch.com/docs/reference/toolsets-reference)

[4] [Hermes Agent — Quickstart](https://hermes-agent.nousresearch.com/docs/getting-started/quickstart)

[5] [Claude Code — Overview](https://code.claude.com/docs/en/overview)

[6] [Claude Code — Authentication](https://code.claude.com/docs/en/iam)

[7] [Claude Code — MCP](https://code.claude.com/docs/en/mcp)

[8] [Claude Code — Channels](https://code.claude.com/docs/en/channels)

> ※ 제품 기능과 인증 흐름은 문서 업데이트에 따라 달라질 수 있다. 실제 운영에서는 실행 시점의 로그·설정·인증 상태·외부 결과를 우선한다.

## Sources

[1] https://hermes-agent.nousresearch.com/docs/user-guide/features/tools
[2] https://hermes-agent.nousresearch.com/docs/user-guide/features/cron
[3] https://hermes-agent.nousresearch.com/docs/reference/toolsets-reference
[4] https://hermes-agent.nousresearch.com/docs/getting-started/quickstart
[5] https://code.claude.com/docs/en/overview
[6] https://code.claude.com/docs/en/iam
[7] https://code.claude.com/docs/en/mcp
[8] https://code.claude.com/docs/en/channels
