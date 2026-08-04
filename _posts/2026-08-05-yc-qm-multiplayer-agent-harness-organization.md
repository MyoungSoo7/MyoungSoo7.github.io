---
layout: post
title: "YC의 QM 멀티에이전트 하네스 — 개인 비서를 넘어 조직 운영 플랫폼으로"
date: 2026-08-05 00:35:52 +0900
categories: [ai, agent, platform, organization]
tags: [QM, Y-Combinator, multi-agent, agent-harness, Slack, Codex, Claude-Code, Hermes, governance]
---

> **QM의 핵심은 에이전트를 여러 개 띄우는 것이 아니라, 개인·방·조직 단위의 기억·권한·파일·샌드박스·스케줄을 하나의 운영 플랫폼으로 묶는 것이다.**

## 한눈에 보기

[Y Combinator의 QM 저장소](https://github.com/yc-software/qm)

YC는 2026년 7월 말 내부에서 사용하던 `QM`을 공개했다. 저장소의 공식 설명은 QM을 *work를 위한 multiplayer agent harness*로 소개하며, Slack과 웹에서 동작하는 조직용 에이전트 하네스를 목표로 한다.[^1]

YC의 공개 설명에 따르면 QM은 회계·법무·이벤트·엔지니어링 등 여러 업무에 사용되며 QM 자체를 만드는 데에도 활용된다.[^2] 다만 공개 저장소는 초기·실험적 소프트웨어이며, 조직의 보안 검토나 운영 인증을 대신하지 않는다고 명시한다.[^3]

## 1. QM이 기존 Agent와 다른 점

많은 Agent 제품은 한 명의 사용자를 위한 개인 비서 모델에서 출발한다.

```text
사용자 → 개인 Agent → 개인 대화·파일·도구
```

QM은 조직에서 재사용 가능한 경계를 추가한다.

```text
조직
├── 사람별 scope
├── 방/채널별 scope
├── 프로젝트 scope
├── 공유 skill·web app
├── 개인·공유 memory
└── scope별 sandbox·권한·credentials
```

QM README 기준으로 사람과 방마다 메모리, 파일, keychain view, 권한, cron, web app, durable sandbox가 분리된다. 개인 업무는 서로 영향을 주지 않으면서도 Slack 채널·그룹 메시지·프로젝트에서 협업할 수 있다는 것이 핵심이다.[^1]

## 2. 주요 구성

| 구성 | 조직에서의 의미 |
|---|---|
| Personal scope | 개인의 기억·파일·도구·권한을 독립적으로 관리 |
| Room/project scope | 팀·채널·프로젝트 단위의 공유 작업공간 |
| Slack + Web | 같은 정체성과 설정을 여러 인터페이스에서 사용 |
| Shared skills | 개인 skill을 공유하고 관리자 승인 후 조직 skill로 승격 |
| Cron/watch | 사람이 지켜보지 않아도 예약·이벤트 기반 작업 실행 |
| Web apps | Agent가 내부용 업무 앱을 만들고 대상 사용자에게 게시 |
| Durable sandbox | 작업 도구와 파일이 유지되는 격리 실행환경 |
| Harness abstraction | Pi, OpenCode, Codex, Claude Code 등을 같은 코어에서 선택 |

이 구조는 단순 멀티에이전트 오케스트레이션보다 **조직의 Agent 운영체계**에 가깝다. 핵심 추상화는 Agent의 개수가 아니라 scope와 권한이다.

## 3. 아키텍처

공식 README는 TypeScript/Node 기반의 headless core, Fastify HTTP, Postgres persistence, scope별 sandbox 구조를 제시한다.[^1]

```text
Slack / Web / Admin / Portal
             ↓ plugins
        Headless Core
  identity · policy · scheduler
             ↓
        Agent Loop
 Pi · OpenCode · Codex · Claude Code
             ↓
   Per-scope Durable Sandbox
 files · tools · logged-in services
             ↕
          PostgreSQL
sessions · memory · queue · identity
```

QM의 중요한 설계는 코어와 조직별 커스터마이징을 분리하는 것이다.

```text
QM core
  + 조직 deployment repository
      ├── config
      ├── skills/tools
      ├── sandbox image
      ├── provider coordinates
      └── infrastructure
```

조직은 `qm init`으로 자체 deployment 디렉터리를 만들고, 전체 소스 코드를 직접 복제하지 않고도 조직 설정과 샌드박스 계층을 운영할 수 있다. 반대로 코어까지 함께 관리해야 하면 공개 저장소를 GitHub Fork가 아닌 일반 clone 기반의 private downstream repository로 유지하는 방식을 문서화하고 있다.[^1][^4]

## 4. 조직에서의 유용성

### 4.1 개인 Agent의 조직 확장

개인 Agent를 조직에 그대로 복제하면 다음 문제가 발생한다.

- 사용자마다 다른 기억과 권한
- 중복되는 도구·skill
- 같은 업무의 중복 실행
- 작업 결과의 개인 채팅 종속
- 누가 무엇을 실행했는지 추적 어려움

QM은 개인 scope와 공유 scope를 분리해 이 문제를 다룬다.

```text
개인 기억·권한·파일
        ≠
팀 채널·프로젝트의 공유 작업
        ≠
조직 전체에 승인된 skill·도구
```

이 분리는 조직 지식의 공유와 개인정보·업무 권한의 격리를 동시에 노리는 설계다.

### 4.2 부서 간 공통 기반

YC가 회계·법무·이벤트·엔지니어링에서 QM을 사용한다고 설명한 이유는 업무별로 별도 Agent 제품을 만들지 않고 공통 하네스 위에 도메인별 skill과 connector를 올릴 수 있기 때문이다.[^2]

```text
공통 Core
  ├── 회계: 비용·영수증·보고
  ├── 법무: 문서·검토·일정
  ├── 이벤트: 참가자·후속조치·운영
  └── 엔지니어링: 코드·CI·로그·PR
```

다만 공통화는 곧 권한 통합을 의미하지 않는다. 회계와 법무의 데이터 경계, 엔지니어링의 저장소 권한, 이벤트 운영 데이터의 개인정보 범위는 각각 별도 scope와 connector 정책으로 분리해야 한다.

### 4.3 조직 지식의 실행화

QM의 shared skill과 company brain 연결은 단순 문서 검색보다 한 단계 더 나아간다.

```text
조직 규칙·문서·데이터
        ↓
공유 skill·connector·memory
        ↓
업무 실행·보고서·내부 앱
        ↓
감사 로그·재사용 가능한 결과
```

문서가 Agent의 답변에만 머무르지 않고 실제 일정·업무 앱·데이터 조회·PR·보고서로 연결될 때 조직 생산성으로 전환될 가능성이 있다.

## 5. 보안 설계: 유용성보다 먼저 봐야 할 부분

QM은 `strict`, `auto`, `dangerous` 세 가지 보안 posture를 제시한다.[^1]

| posture | 동작 | 적용 관점 |
|---|---|---|
| Strict | 거의 모든 harness tool call에 사람 승인 | 법무·금융·운영 변경 |
| Auto | 외부 데이터·tool 결과를 classifier로 선별 | 일반 내부 업무, 단 운영 검증 필요 |
| Dangerous | 콘텐츠 screening·도구 간 pause 없음 | 격리된 실험 전용 |

모든 posture에 재귀 삭제나 파괴적 SQL 같은 사전 선언된 거부 정책을 적용한다고 설명하지만, `SECURITY.md`는 이것이 완전한 샌드박스 경계가 아니며 우회 가능성이 있다고 명시한다.[^3]

### 공개 보안 문서에서 확인되는 한계

- 명령 정책은 난독화·인코딩·스크립트 작성 후 실행으로 우회될 수 있음
- 브라우저 동작은 일부 core gate와 별도 경계에 있음
- 샌드박스 안에서 사용 중인 credentials는 프로세스가 읽을 수 있음
- credential purpose 문구는 완전한 권한 통제가 아님
- content screening은 휴리스틱이며 prompt injection을 보장해서 막지 않음
- 파일 artifact에 만료·완전한 byte reclamation이 없음
- 관리자에게 scope-authorized 민감 콘텐츠 열람 권한이 있음
- 조직 kill switch와 일부 governance versioning/revertibility가 미완성

따라서 QM을 운영에 도입할 때 “AI가 안전한가?”보다 다음 질문이 정확하다.

```text
누가 어떤 scope에서
어떤 credential과 tool을
어떤 승인 상태로 사용했고
어떤 외부 시스템에
어떤 효과를 남겼는가?
```

QM의 audit은 사고 조사에 유용하지만, 공개 보안 문서가 말하듯 audit 기록 자체가 실행을 예방하는 것은 아니다.[^3]

## 6. 조직 도입 평가 프레임워크

QM 또는 유사 하네스를 도입할 때는 기능 목록보다 업무 단위로 평가해야 한다.

### 단계 1: 업무 후보 선정

```text
반복적이고
입력·출력이 명확하며
실패 비용이 통제 가능하고
사람이 검토할 수 있는 업무
```

추천 시작 영역:

- 내부 문서 검색·요약
- 회의·이벤트 후속조치
- CI 실패 분류
- 로그·장애 브리핑
- 주간 리포트 초안
- PR 변경 요약

처음부터 지급·법률 확정·운영 배포를 완전 자동화하는 것은 부적합하다.

### 단계 2: 결과 단위 정의

| 측정축 | 질문 |
|---|---|
| 성공률 | 사람이 승인할 수 있는 결과가 몇 %인가? |
| 시간 | 사람의 대기·탐색·작성 시간을 얼마나 줄였는가? |
| 재작업 | Agent 결과를 다시 고치는 비용은 얼마인가? |
| 정확도 | 근거 없는 주장·도구 오작동·누락은 얼마나 되는가? |
| 비용 | 모델·샌드박스·스토리지·브라우저 비용은? |
| 보안 | scope 탈출·권한 오남용·민감정보 노출은? |
| 채택 | 팀이 실제로 계속 사용하는가? |

### 단계 3: 권한 단계화

```text
읽기·요약
→ 초안 작성
→ 사람 승인 후 외부 전달
→ 제한된 내부 변경
→ 고위험 자동화는 별도 승인
```

조직 단위 하네스의 가치는 자동화 수준이 아니라, **자동화 수준을 업무별로 다르게 설정할 수 있는 능력**에 있다.

## 7. 현재 운영 시스템과의 비교

당신이 운영하는 Hermes·Claude 봇 구조와 QM은 방향이 겹치지만 추상화의 중심이 다르다.

| 항목 | 현재 Hermes·Claude 봇 | QM |
|---|---|---|
| 중심 단위 | 봇1~봇4·tmux 세션 | 사람·방·프로젝트 scope |
| 인터페이스 | Telegram·CLI | Slack·Web |
| 세션 운영 | tmux/PTY·launchd | core·DB·durable sandbox |
| 명령 체계 | 작업체크·목록·보고·clear | 조직 UI·채널·프로젝트 |
| 지식 공유 | memory·skill·Wiki | scoped memory·shared skill·company brain |
| 권한 | Hermes/K3s RBAC·도구 정책 | posture·grant·audience·scope |
| 강점 | 개인 운영 자동화·K3s 통합 | 조직 사용자·공유 업무·배포 표준화 |
| 다음 보강 | 중앙 상태·큐·권한·감사 | 도메인별 connector·현장 검증 |

QM은 당신의 구조를 대체한다기보다, 현재의 **중앙 Hermes + 봇1~4 + 작업상태 계약**을 조직용 scope·Slack·Web·durable sandbox 모델로 확장할 때 비교할 기준이 된다.

특히 현재 명령어 체계는 QM의 조직 운영 개념으로 다음처럼 확장할 수 있다.

```text
작업체크  → scope/agent readiness
작업목록  → shared task/project board
작업보고  → channel/project progress report
봇클리어  → session context reset, workspace 유지
봇상태    → process·connector·scope·recent activity
봇재시작  → isolated agent runtime restart
```

## 8. QM의 한계와 도입 전 체크리스트

QM 저장소는 최신 상태가 빠르게 변하고, 2026년 8월 1일 기준 약 45개 커밋과 v0.1.4 릴리스가 공개되어 있다.[^1] 따라서 버전·배포 문서·보안 한계를 현재 revision 기준으로 다시 확인해야 한다.

도입 전 확인:

- [ ] 조직 데이터가 어느 provider로 전송되는가
- [ ] Postgres·object storage·sandbox 백업과 삭제 정책
- [ ] 개인·방·프로젝트 scope의 실제 접근 테스트
- [ ] Admin의 민감 데이터 열람 범위
- [ ] Slack 외부 참여자가 포함된 room 정책
- [ ] browser provider의 egress·보존·로그 정책
- [ ] credential materialization과 만료·폐기 경로
- [ ] org floor·kill switch·governance versioning 상태
- [ ] sandbox escape·prompt injection·command policy 우회 테스트
- [ ] 모델·sandbox·browser 비용 예산과 rate limit
- [ ] upstream 업데이트·private fork·deployment layer 운영 책임

## 결론

QM의 가장 중요한 메시지는 “멀티에이전트를 여러 개 띄우자”가 아니다.

> **조직에서 Agent를 쓰려면 모델보다 먼저 사람·방·프로젝트별 기억, 권한, 파일, 실행환경, 승인, 감사, 재사용 경계를 설계해야 한다.**

QM은 개인 Agent를 조직 플랫폼으로 확장하는 유용한 참조 구현이다. 특히 Slack·Web이라는 업무 표면, scope별 durable sandbox, shared skill, cron/watch, harness 독립성은 팀 단위 Agent 운영을 시작할 때 좋은 설계 재료가 된다.

반면 QM은 공개 보안 문서 스스로 초기·실험적 소프트웨어라고 밝히며, 명령 정책·브라우저·credential·screening·artifact·kill switch의 한계를 공개한다. 따라서 바로 전사 도입하기보다 저위험 내부 업무로 시작해 다음을 검증하는 것이 합리적이다.

```text
업무 가치
× 결과 품질
× 권한 통제
× 감사 가능성
× 운영 복구성
```

현재 당신의 Hermes·Claude 봇 운영 경험과 결합하면, QM은 **Telegram 중심 개인/운영 Agent 구조를 조직 scope·공유 프로젝트·권한·감사 플랫폼으로 확장할 때의 비교 기준**으로 가장 큰 가치가 있다.

## References

[^1]: [yc-software/qm — 공식 GitHub 저장소와 README](https://github.com/yc-software/qm)
[^2]: [Y Combinator — QM 공개 발표](https://x.com/ycombinator/status/2083243960684908768)
[^3]: [QM SECURITY.md — 공식 위협 모델과 한계](https://github.com/yc-software/qm/blob/main/SECURITY.md)
[^4]: [QM deployment/getting started 문서](https://github.com/yc-software/qm/blob/main/docs/getting-started.md)
[^5]: [QM LICENSE — MIT License](https://github.com/yc-software/qm/blob/main/LICENSE)

*이 글은 QM 공식 저장소·공식 보안 문서·YC 공개 발표를 우선 근거로 작성했다. 스타트업 내부 도입 전에는 대상 revision, provider 보존정책, sandbox·네트워크·권한 구현을 직접 검증해야 한다.*
\n<style>\n.post-content table { width: 100%; border-collapse: collapse; margin: 1.5rem 0; }\n.post-content th, .post-content td { border: 1px solid #ddd; padding: .6rem; vertical-align: top; }\n.post-content th { background: #f6f8fa; }\n</style>