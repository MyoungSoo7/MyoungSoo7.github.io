---
layout: post
title: "OpenClaw·OpenShell·NemoClaw 비교: 에이전트 판단·보안 런타임·운영 스택"
date: 2026-09-20 19:02:37 +0900
categories: [AI, Security, Infrastructure]
tags: [OpenClaw, OpenShell, NemoClaw, AI Agent, Sandbox, Policy, Runtime]
---

# OpenClaw·OpenShell·NemoClaw 비교

OpenClaw, OpenShell, NemoClaw는 모두 AI 에이전트 보안과 관련해 언급되지만 같은 계층의 제품이 아니다.

핵심을 한 문장으로 요약하면 다음과 같다.

> **OpenClaw는 어떤 도구로 무엇을 시도할지 결정하는 에이전트 프레임워크이고, OpenShell은 그 행동이 닿을 수 있는 파일·네트워크·OS 연산을 제한하는 보안 런타임이며, NemoClaw는 둘을 정책 프리셋·추론 연결·수명주기 운영과 함께 묶은 스택이다.**

NVIDIA의 공식 문서도 NemoClaw를 지원·검증 후보 AI 에이전트를 NVIDIA OpenShell sandbox 안에서 더 안전하게 실행하는 오픈소스 reference stack으로 설명한다.[1][3]

## 1. 세 계층을 먼저 분리하기

```text
사용자 목표
   ↓
OpenClaw
  계획·도구 선택·메모리·에이전트 실행
   ↓
NemoClaw
  온보딩·정책 blueprint·추론 라우팅·수명주기
   ↓
OpenShell
  sandbox·파일·네트워크·credential·OS 실행 경계
   ↓
Host / VM / Container / Network / Model Endpoint
```

이를 다른 방식으로 표현하면:

```text
OpenClaw  = decision plane
OpenShell = enforcement plane
NemoClaw  = productized integration / lifecycle plane
```

다만 이 구조는 이해를 위한 분석 모델이다. 실제 구성요소와 지원 agent, 플랫폼, provider는 버전·blueprint에 따라 달라질 수 있으므로 설치 전 현재 공식 문서와 repository의 release를 확인해야 한다.[1][3]

## 2. OpenClaw: 무엇을 할지 결정하는 계층

OpenClaw는 사용자의 요청을 해석하고, 어떤 tool·skill·workflow를 사용할지 결정하는 agent 쪽에 해당한다.

```text
요청
  ↓
의도 해석
  ↓
계획
  ↓
도구 선택
  ├─ 파일 읽기
  ├─ shell 실행
  ├─ 웹 조회
  ├─ API 호출
  └─ 외부 시스템 조작
```

### OpenClaw가 담당하는 것

- 자연어 목표 해석
- 작업 계획
- tool call 선택
- 결과를 다음 판단에 반영
- memory·context 활용
- 여러 단계 workflow 수행
- 사용자에게 결과와 다음 행동 보고

### OpenClaw가 혼자 보장하지 않는 것

에이전트가 어떤 행동을 선택하는 것과 실제 OS가 그 행동을 허용하는 것은 별개다.

```text
OpenClaw가 “파일을 읽자”고 결정
  ≠ 해당 파일을 실제로 읽을 권한이 있음

OpenClaw가 “curl을 실행하자”고 결정
  ≠ 외부 네트워크 연결이 허용됨

OpenClaw가 “설정 파일을 수정하자”고 결정
  ≠ sandbox 밖 경로까지 수정 가능함
```

따라서 OpenClaw의 tool policy를 문서나 prompt만으로 제한하면 충분하지 않다. 실제 경계는 runtime·OS·container·network·credential 계층에서 강제해야 한다.

## 3. OpenShell: 행동이 닿는 범위를 제한하는 런타임

NVIDIA OpenShell repository는 OpenShell을 autonomous AI agent를 위한 safe, private runtime으로 설명한다.[2]

OpenShell의 핵심은 모델의 판단을 바꾸는 것보다 **그 판단이 실제로 미칠 수 있는 영향 범위를 제한하는 것**이다.

```text
에이전트가 실행하려는 행동
  ↓
OpenShell policy / sandbox
  ├─ 허용 파일
  ├─ 차단 파일
  ├─ writable path
  ├─ network egress
  ├─ credential 접근
  ├─ process / syscall 경계
  └─ resource / lifecycle
       ↓
실제 OS 연산
```

### OpenShell 관점의 보안 경계

- filesystem read/write 범위
- 네트워크 destination과 egress
- credential custody와 전달 범위
- sandbox process
- host·container·VM 경계
- agent의 지속 실행과 종료
- 정책 위반 시 차단·감사

OpenShell은 agent 종류에 종속된 단순 기능이 아니라, agent가 실행되는 runtime 경계로 보는 것이 핵심이다.

### OpenShell이 해결하는 문제

```text
모델이 악의적이거나 실수로
  ~/.ssh 읽기
  .env 수집
  임의 사이트로 전송
  production API 호출
  host 경로 수정
```

같은 행동을 하더라도 sandbox와 policy가 제대로 구성돼 있으면 실제 영향 범위를 제한할 수 있다.

### OpenShell의 한계

- 잘못된 policy를 작성하면 안전하지 않은 경로가 허용될 수 있다.
- sandbox가 있다고 해서 prompt injection 자체가 사라지지는 않는다.
- 허용된 네트워크와 credential이 과도하면 데이터 유출 반경이 커진다.
- host integration, Docker socket, privileged 권한이 있으면 경계가 약해질 수 있다.
- runtime의 버전·플랫폼·아키텍처별 동작을 실제 검증해야 한다.

즉, OpenShell은 “안전함”이라는 자동 보증서가 아니라 **정책을 실행하는 enforcement layer**다.

## 4. NemoClaw: 정책과 수명주기를 묶은 스택

NVIDIA는 NemoClaw를 OpenShell 설치, agent integration, versioned blueprint, managed inference, network policy, managed integrations와 함께 제공하는 reference stack으로 설명한다.[1][3]

```text
NemoClaw
  ├─ onboarding
  ├─ agent 선택
  ├─ OpenShell 설치·연결
  ├─ 정책 blueprint
  ├─ managed inference / model routing
  ├─ credential custody
  ├─ integrations
  ├─ sandbox lifecycle
  └─ doctor·rebuild·recovery 경로
```

### NemoClaw가 추가하는 가치

OpenShell을 직접 구성하면 runtime과 policy를 직접 설계해야 한다. NemoClaw는 특정 agent를 sandbox에 넣고 실행하기 위한 onboarding과 lifecycle, 정책 preset, inference 경로를 묶어 도입 난도를 낮추는 방향이다.[1][3]

### NemoClaw의 장점

- agent와 runtime을 함께 설치·구성하기 쉬움
- versioned blueprint로 정책 구성을 표준화할 수 있음
- managed inference와 credential custody를 통합할 수 있음
- sandbox lifecycle을 운영 명령으로 묶기 쉬움
- OpenClaw 외에도 Hermes와 LangChain Deep Agents 등 여러 agent 가이드를 제공한다.[3][4]

### NemoClaw의 주의점

- reference stack은 모든 운영 환경의 완제품을 의미하지 않는다.
- blueprint의 기본 정책을 그대로 production에 적용하기 전에 검토해야 한다.
- managed inference·credential·network integration은 새로운 trust boundary다.
- agent·OpenShell·NemoClaw 버전 호환성을 함께 관리해야 한다.
- 설치 script와 자동 lifecycle이 host·Docker·VM·network 상태를 변경할 수 있다.
- GitHub issue에 나타나는 현상처럼 빠르게 변화하는 preview 생태계에서는 현재 commit·release 기준 검증이 필요하다.[1]

## 5. 비교표

| 관점 | OpenClaw | OpenShell | NemoClaw |
|---|---|---|---|
| 계층 | Agent / decision | Runtime / enforcement | Integration stack / lifecycle |
| 핵심 질문 | 무엇을 할 것인가? | 어디까지 허용할 것인가? | 어떻게 설치·정책·운영할 것인가? |
| 주요 기능 | 계획·tool 선택·memory·workflow | sandbox·filesystem·network·OS 경계 | onboarding·blueprint·inference·integration |
| 주요 출력 | tool call과 agent response | allow·deny·sandbox execution | 실행 가능한 stack·정책·상태 |
| 보안 책임 | 과도한 자율성·잘못된 tool 선택 | 실제 접근·연산 범위 제한 | 기본 정책·credential·lifecycle 관리 |
| 독립 사용 | agent로 사용 가능 | 다양한 agent runtime에 사용 가능 | OpenShell 위 지원 agent 통합 |
| 실패 예시 | 위험한 tool을 선택 | 위험한 path/network가 허용됨 | 잘못된 preset·버전·lifecycle |
| 검증 단위 | task·tool trace | policy·sandbox·egress | 설치·blueprint·runtime·recovery |

## 6. 실제 실행 흐름

### 정상적인 요청

사용자가 “저장소 테스트를 실행하고 실패 원인을 정리해줘”라고 요청했다고 하자.

```text
1. OpenClaw가 목표를 해석한다.
2. 저장소를 읽고 test command를 선택한다.
3. NemoClaw가 선택된 agent와 sandbox lifecycle을 제공한다.
4. OpenShell이 repository workspace 안에서 명령을 실행한다.
5. 네트워크 접근은 policy에 의해 제한된다.
6. 결과·로그·exit code가 agent에 반환된다.
7. OpenClaw가 실패 원인과 다음 조치를 정리한다.
```

### 위험한 요청

에이전트가 `.env`를 읽고 외부 paste 서비스로 업로드하려 한다면:

```text
OpenClaw: tool 선택 또는 계획
OpenShell: .env read / external egress 차단
NemoClaw: 정책·credential·lifecycle 상태 기록
결과: 실행 실패와 차단 Trace 보존
```

여기서 OpenShell이 막았다고 해서 OpenClaw의 판단이 옳았다는 의미는 아니다. 오히려 이 분리를 통해 **판단 실패**와 **실행 경계 차단**을 따로 분석할 수 있다.

## 7. 보안 설계 원칙

### 7.1 결정 계층과 실행 계층을 분리

```text
Decision plane:
  모델·agent·OpenClaw

Enforcement plane:
  OpenShell·OS sandbox·container·network policy

Operations plane:
  NemoClaw·blueprint·lifecycle·observability
```

prompt나 system instruction은 결정 계층의 행동을 유도한다. 하지만 production 보호는 enforcement 계층의 deny·allow와 OS 권한으로 해야 한다.

### 7.2 기본 deny

- workspace 밖 write deny
- `.env`, SSH key, private key read deny
- production API egress deny
- wildcard shell deny
- Docker socket deny
- privileged container deny
- 무제한 retry·recursion deny

### 7.3 credential 분리

```text
개발 sandbox credential
  ≠
CI credential
  ≠
production credential
```

managed inference를 사용할 때도 어떤 credential이 어느 계층에 보관되고, agent가 직접 보거나 단지 proxy를 통해 사용하는지 확인해야 한다. NemoClaw 문서는 OpenShell이 managed inference와 host-configured integration credential의 custody를 제공한다고 설명한다.[3]

### 7.4 네트워크 allowlist

```text
agent sandbox
  ├─ package registry: 필요 시 허용
  ├─ source control: 제한된 endpoint
  ├─ model endpoint: 명시적 허용
  ├─ internal DB: 기본 차단
  └─ arbitrary internet: 기본 차단
```

네트워크를 열어 놓고 sandbox라고 부르면 안 된다. 실제 egress와 DNS·proxy·credential 경로까지 관찰해야 한다.

## 8. 운영과 수명주기

NemoClaw 같은 stack을 도입할 때 lifecycle은 설치보다 중요하다.

```text
preflight
  ↓
onboard
  ↓
policy render
  ↓
sandbox create
  ↓
agent start
  ↓
health / logs / metrics
  ↓
rebuild / upgrade
  ↓
stop / delete / rollback
```

### 운영 체크리스트

- [ ] host OS·architecture·GPU·memory 확인
- [ ] Docker/Container runtime 상태 확인
- [ ] OpenShell version pin
- [ ] NemoClaw blueprint commit pin
- [ ] agent version과 호환성 확인
- [ ] sandbox 이름·identity 분리
- [ ] credential custody 확인
- [ ] network policy render/read-back
- [ ] writable path 확인
- [ ] policy deny test
- [ ] restart·rebuild·recovery 테스트
- [ ] uninstall·rollback 절차 확보
- [ ] audit log와 resource usage 보존

### Mac과 Linux를 구분

NVIDIA 공식 문서의 readiness·platform 지원 범위를 그대로 모든 macOS·Linux 환경에 일반화하면 안 된다. 사용 중인 CPU architecture, Docker backend, GPU/driver, VM 경계를 먼저 확인하고, 지원되지 않거나 qualification이 필요한 환경은 실험·canary로 분리해야 한다.[3]

## 9. 장애 분석 프레임

### Agent가 잘못 판단했나?

증거:

- prompt
- plan
- tool selection
- model output
- retry chain

담당 계층:

```text
OpenClaw / agent decision
```

### 명령은 맞았지만 실행 범위를 넘었나?

증거:

- sandbox decision
- filesystem deny
- network deny
- process·syscall log
- credential policy

담당 계층:

```text
OpenShell / OS runtime
```

### 설치·정책·재시작·복구가 실패했나?

증거:

- NemoClaw onboarding output
- blueprint version
- lifecycle event
- runtime health
- rebuild·upgrade trace

담당 계층:

```text
NemoClaw / lifecycle integration
```

이렇게 분리하면 다음과 같은 잘못된 결론을 줄일 수 있다.

```text
sandbox가 실행됨 → agent가 정상
agent가 tool을 선택함 → 실제 작업 성공
설치 명령 exit 0 → 서비스 사용 가능
HTTP 200 → inference와 policy 정상
```

## 10. 세 기술을 함께 쓸 때의 장단점

### 장점

- 판단·실행·운영 책임이 계층별로 분리된다.
- agent를 바꿔도 runtime 보안 경계를 재사용할 수 있다.
- policy와 lifecycle을 blueprint로 반복 적용할 수 있다.
- 모델 routing과 credential custody를 표준화할 수 있다.
- 장기 실행 agent를 sandbox와 관측 계층 안에 둘 수 있다.

### 단점

- 계층이 늘어 troubleshooting path가 길어진다.
- agent·runtime·stack·model provider 버전 조합이 복잡하다.
- 정책이 너무 엄격하면 agent 기능이 깨진다.
- 정책이 너무 넓으면 sandbox가 실질적인 보호를 제공하지 못한다.
- managed inference와 외부 integration에 대한 trust가 추가된다.
- preview/reference stack은 production SLA로 오해하면 안 된다.

## 11. 도입 순서

### 개발자 실험

```text
OpenClaw만 로컬 실행
→ 위험하지 않은 test repository
→ OpenShell read-only sandbox
→ 정책 deny/allow 확인
```

### 팀 개발

```text
OpenShell version pin
→ NemoClaw blueprint 검토
→ 개발 credential만 연결
→ network allowlist
→ audit log
→ ephemeral sandbox
```

### 운영·장기 agent

```text
전용 host 또는 VM
→ sandbox per agent
→ short-lived credential
→ managed policy
→ canary
→ failure injection
→ rollback·recovery 검증
→ 운영 승인
```

### 절대 먼저 하지 않을 것

- host의 broad filesystem mount
- Docker socket mount
- production SSH key 상시 주입
- `latest` version 사용
- arbitrary outbound internet 허용
- 설치 script의 무검토 실행
- preview 기능을 production으로 표현
- sandbox 성공만으로 보안 검증 완료 선언

## 결론

세 기술은 경쟁 제품이라기보다 서로 다른 책임 계층이다.

```text
OpenClaw:
  어떤 tool을 사용할지, 어떤 순서로 행동할지 결정

OpenShell:
  그 행동이 닿을 수 있는 파일·네트워크·OS 범위를 강제 제한

NemoClaw:
  agent와 OpenShell을 정책 preset·inference·credential·lifecycle과 묶어 운영
```

가장 중요한 원칙은 **결정과 enforcement를 분리하는 것**이다.

```text
Agent가 하지 말라고 지시받음
  ≠ 실제로 못 함

Runtime이 deny함
  = 실제 실행 경계에서 차단
```

따라서 OpenClaw만으로 보안 runtime이 된다고 생각해서는 안 되고, OpenShell만으로 agent의 위험한 판단이 사라진다고 생각해서도 안 된다. NemoClaw 역시 설치 편의성과 lifecycle을 제공하는 reference stack이지, 모든 환경에서 자동으로 안전한 production 플랫폼이 되는 것은 아니다.

실무에서는 다음 순서가 가장 안전하다.

```text
OpenClaw로 판단 흐름 확인
→ OpenShell로 deny/allow 경계 검증
→ NemoClaw로 blueprint·credential·lifecycle 표준화
→ canary·audit·read-back
→ 운영 승인
```

결국 세 계층의 성공 기준은 다음처럼 분리해야 한다.

```text
판단 성공
+ 실행 경계 준수
+ 정책 적용 성공
+ 수명주기 복구 가능
+ 실제 결과 read-back
```

이 네 가지가 모두 확인될 때에만 “안전하게 동작했다”고 말할 수 있다.

## 참고 자료

[1] NVIDIA NemoClaw GitHub — OpenShell sandbox 안에서 지원 agent를 실행하는 reference stack  
[2] NVIDIA OpenShell GitHub — autonomous AI agent를 위한 safe·private runtime  
[3] NVIDIA NemoClaw Documentation — onboarding, managed inference, network policy, credentials, lifecycle  
[4] NVIDIA NemoClaw Overview — OpenClaw·Hermes·LangChain agent와 OpenShell policy controls

## 출처

- NVIDIA NemoClaw: https://github.com/NVIDIA/NemoClaw
- NVIDIA OpenShell: https://github.com/NVIDIA/OpenShell
- NemoClaw Documentation: https://docs.nvidia.com/nemoclaw/user-guide/openclaw/home
- NVIDIA NemoClaw Overview: https://www.nvidia.com/en-us/ai/nemoclaw/

## Sources

[1] https://github.com/NVIDIA/NemoClaw — NVIDIA NemoClaw
[2] https://github.com/NVIDIA/OpenShell — NVIDIA OpenShell
[3] https://docs.nvidia.com/nemoclaw/user-guide/openclaw/home — NemoClaw Documentation
[4] https://www.nvidia.com/en-us/ai/nemoclaw — NVIDIA NemoClaw Overview
