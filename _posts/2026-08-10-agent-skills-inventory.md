---
layout: post
title: "이 Mac의 Agent Skill 생태계 지도: Hermes·Claude·Codex·Leopard"
date: 2026-08-10 14:35:00 +0900
categories: [ai-agent, engineering, automation]
tags: [Hermes, Claude, Codex, Leopard, skills, harness, agent-os]
---

Agent를 운영하다 보면 어느 순간 Script보다 더 큰 자산이 생긴다. 바로 **Skill**이다. Skill은 단순한 프롬프트가 아니라 특정 작업을 수행하는 방법, 권한 경계, 검증 절차, 실패 시 주의점을 재사용 가능한 문서로 고정한다.

이 글은 2026-08-10 KST 현재 이 Mac에 실제로 존재하는 Skill을 inventory하고, Hermes·Claude·Codex·Leopard 영역을 분리해 설명한다. 다만 Skill 파일만으로 “Claude가 만들었다”, “Codex가 만들었다”, “Hermes가 만들었다”를 모두 증명할 수는 없다. 따라서 아래에서 **보관 위치·실행 주체·확인 가능한 provenance**를 구분한다.

## 1. 전체 구조와 확인된 수량

| 영역 | 실제 경로 | 확인된 `SKILL.md` 수 | 성격 |
| --- | --- | ---: | --- |
| Hermes | `~/.hermes/skills/` | 104 | Hermes가 로드·관리하는 범용 Skill catalog |
| Claude | `~/.claude/skills/` | 21 | Claude Code와 Telegram 봇이 사용하는 로컬·프로젝트 Skill |
| Codex | `~/.codex/skills/` | 27 | Codex 기본 Skill과 Ouroboros 연동 Skill |
| Leopard | `~/leopard-github/skills/` | 4 | GitHub canonical source의 공유 Skill |

이 수량은 각 경로에서 `SKILL.md`를 실제 검색한 결과다. 외부 plugin cache, 프로젝트별 `.claude/skills`, 다른 worktree까지 합친 “전 세계의 모든 Skill” 수가 아니다.

## 2. Hermes Skill catalog — 104개

경로:

```text
/Users/lms/.hermes/skills/
```

Hermes 영역은 가장 넓다. Apple 자동화, 연구, 문서, GitHub, DevOps, 미디어, 생산성, ML/LLM, 개발, 창작 등 범용 작업을 포괄한다.

### 주요 분류

| 분류 | 대표 Skill | Agent가 어려워하는 부분 |
| --- | --- | --- |
| autonomous-ai-agents | `hermes-agent`, `claude-code`, `codex`, `computer-use`, `agent-self-improvement` | Agent 실행·권한·도구 선택·자기개선 |
| DevOps/K3s | `lemuel-k3s-readonly`, `lemuel-agent-os`, `evidence-grounded-ops-reporting` | 현재 상태와 과거 로그 구분, read-only 운영 |
| GitHub | `github-pr-workflow`, `github-code-review`, `github-issue-to-pr`, `github-repo-management` | PR·CI·branch·push의 실제 상태 검증 |
| Software development | TDD, systematic debugging, code review, spike, simplify code | 구현 전 조사와 검증 루프 |
| Research | arxiv, grounded-citations, blogwatcher, llm-wiki, market briefing | 출처·최신성·인용·RSS 관리 |
| Productivity | docx, pdf, xlsx, powerpoint, Google Workspace, Notion | 바이너리 문서 생성·검증·변환 |
| ML/MLOps | llama.cpp, vLLM, HuggingFace, W&B, lm-eval | 모델·패키지·서빙·평가 재현성 |
| Creative/media | image/video/audio/design 관련 Skill | 복합 산출물과 포맷 검증 |
| Apple/social/email | Notes, Reminders, iMessage, email, X | 외부 앱·권한·전송 부작용 |

### Hermes가 만든 것인가?

`~/.hermes/skills`에 있다는 사실은 **Hermes가 현재 로드·관리하는 Skill**이라는 뜻이지, 모든 파일을 Hermes가 최초 작성했다는 뜻은 아니다. 일부는 bundled skill, 일부는 외부 설치 skill, 일부는 사용자·Agent가 추가하거나 수정한 로컬 skill일 수 있다.

확정 가능한 표현:

```text
Hermes catalog에 등록됨
Hermes가 해당 작업 전에 로드할 수 있음
Hermes skill lifecycle 대상일 수 있음
```

확정할 수 없는 표현:

```text
모든 파일을 Hermes가 직접 작성함
각 파일을 특정 모델이 최초 작성함
```

## 3. Claude 로컬 Skill — 21개

경로:

```text
/Users/lms/.claude/skills/
```

Claude 영역은 사용자 프로젝트와 Telegram 봇 작업에 가까운 로컬 Skill이다.

확인된 주요 범주:

```text
academy-cve-policy
claudeclaw
lemuel-xr-flyway-migration
lemuel-xr-mental-health-safety
lemuel-xr-mermaid-sequence
lemuel-xr-theology-tone
quant-pipeline-stability
rlm
settlement-flyway-migration
settlement-hexagonal-conventions
sparta-flyway-migration
sparta-next-js-build-args
그림
레오파드
메타스페이스
새인물
스레드
지씨누수
풀지씨
하브루타
힙
```

### 역할별 의미

```text
Settlement:
  Flyway, Hexagonal convention, 정산 프로젝트 규칙

Lemuel-XR:
  Flyway, Mermaid sequence, 안전·신학 톤

K3s/운영:
  힙, 풀 GC, GC leak, 메타스페이스, 그림

Research/communication:
  하브루타, 새인물, 레오파드

Agent platform:
  claudeclaw, rlm, quant-pipeline-stability
```

### Claude 봇1~4의 관계

Claude 봇들은 같은 Skill catalog만 바라보는 것이 아니라, 각 Telegram project directory의 `CLAUDE.md`와 project memory도 함께 사용한다.

```text
봇1:
  범용·인프라·K3s

봇2:
  Settlement

봇3:
  MSA·P8

봇4:
  inter-asat·RAHAB
```

따라서 Claude Skill은 다음 세 층으로 나누어 보는 것이 정확하다.

```text
~/.claude/skills/       공통 로컬 Skill
project/CLAUDE.md       프로젝트 정책·규칙
project/memory/         프로젝트에서 검증된 지속 사실
```

## 4. Codex Skill — 27개

경로:

```text
/Users/lms/.codex/skills/
```

Codex 영역은 기본 Skill과 Ouroboros 연동 Skill이 중심이다.

### 기본 Skill

```text
.system/imagegen
.system/openai-docs
.system/plugin-creator
.system/skill-creator
.system/skill-installer
```

이 영역은 Codex가 이미지 생성, OpenAI 문서 확인, plugin/skill 작성·설치 같은 자기 확장 작업을 수행할 때 사용한다.

### Ouroboros Skill

```text
ouroboros-auto
ouroboros-brownfield
ouroboros-cancel
ouroboros-config
ouroboros-evaluate
ouroboros-evolve
ouroboros-help
ouroboros-interview
ouroboros-ooo
ouroboros-pm
ouroboros-publish
ouroboros-qa
ouroboros-ralph
ouroboros-resume-session
ouroboros-run
ouroboros-seed
ouroboros-setup
ouroboros-status
ouroboros-tutorial
ouroboros-unstuck
ouroboros-update
ouroboros-welcome
```

Codex의 Ouroboros Skill은 다음 실행 흐름을 문서화한다.

```text
요구사항 interview
→ seed 생성
→ run/auto
→ status
→ evaluate/QA
→ evolve/Ralph
→ resume/cancel
→ publish
```

### Codex가 만든 것인가?

`~/.codex/skills`는 Codex가 로드하는 위치이고, 특히 `ouroboros-*`는 Ouroboros setup으로 배포된 것으로 보인다. 하지만 정확한 최초 작성자와 각 파일의 생성 시점은 파일 경로만으로 확정할 수 없다.

따라서 이 글에서는 다음처럼 표시한다.

```text
Codex 실행 환경에 설치된 Skill
Ouroboros worker를 위해 동기화된 Skill
최초 작성자: provenance 없이는 미확정
```

## 5. Leopard canonical Skill — 4개

경로:

```text
/Users/lms/leopard-github/skills/
```

확인된 Skill:

```text
havruta/SKILL.md
leopard/SKILL.md
lion/SKILL.md
ouroboros-pr/SKILL.md
```

Leopard는 단순한 개인 로컬 Skill 폴더가 아니라, GitHub의 canonical source로 관리되는 공유 Skill family다.

### 역할

```text
leopard:
  공통 라우팅·작업 체계

lion:
  종합 컴퓨터과학·아키텍처 분석

havruta:
  주장·반론·근거 대조

ouroboros-pr:
  Ouroboros PR 검토·준비·전달
```

Claude 봇1~4가 이 Skill을 사용하더라도 수정은 설치된 복사본이 아니라 canonical Git source에서 먼저 해야 한다. 이것이 여러 Agent가 서로 다른 Skill 버전을 사용하는 것을 막는 핵심이다.

## 6. “누가 만들었나”를 어떻게 구분할까

현재 로컬 파일은 작성자 provenance가 완전하지 않다. 다음 정보가 있을 때만 attribution을 확정한다.

| 근거 | 확정 가능한 것 |
| --- | --- |
| Git commit author | 해당 commit의 기록 작성자 |
| 생성 metadata | Skill이 생성·설치된 시점과 도구 |
| canonical repository history | 원본 repository의 변경 주체 |
| install/update log | 설치·동기화 경로 |
| 단순 파일 존재 | 현재 보관·사용 위치만 확정 |

따라서 다음 표현을 피해야 한다.

```text
Claude가 만든 모든 Skill
Codex가 만든 모든 Skill
Hermes가 만든 모든 Skill
```

대신 다음 표현이 Trace에 맞다.

```text
Claude 환경에서 사용하는 Skill
Codex 환경에 설치된 Skill
Hermes catalog가 관리하는 Skill
Leopard canonical source의 Skill
```

## 7. Skill이 해결하는 Agent의 어려움

### 1) 반복 절차 기억

```text
Spring/Flyway migration
GitHub PR workflow
K3s read-only RCA
PDF/XLSX/DOCX 처리
```

### 2) 권한과 위험 통제

```text
운영 클러스터는 read-only
금융·건강·개인정보 작업은 safety gate
Git push·배포·외부 전송은 검증 후 실행
```

### 3) 작업 품질의 기준 고정

```text
TDD
diff check
CI 확인
실제 URL HTTP 200
원문 출처와 References
```

### 4) 역할별 관점 분리

```text
LION = 종합 분석
Havruta = 논증 대조
Ouroboros PR = 코드 변경 검토
Codex specialist = JPA/보안/멱등성/ArchUnit
```

### 5) 도구와 외부 서비스 연결

```text
RSS
GitHub CLI
HuggingFace
Kubernetes
Google Workspace
Apple 앱
```

## 8. Skill·Script·Memory·Tool의 차이

| 자산 | 주된 역할 | 예 |
| --- | --- | --- |
| Skill | 반복 가능한 작업 절차·정책 | `homelab-k3s-ops` |
| Script | 결정적 수집·변환·검증 | `k8s-rca-collect.sh` |
| Tool | 외부 시스템 호출 인터페이스 | MCP·GitHub·browser |
| Memory | 안정적인 사용자·환경 사실 | `MEMORY.md` |
| Wiki | 출처가 있는 지식과 분석 | `~/wiki/concepts` |
| Session | 일회성 진행 상태 | 현재 봇 작업 |
| Harness | 실행·중단·평가·receipt | Ouroboros |

좋은 Agent 운영은 Skill 하나에 모든 것을 넣지 않는다.

```text
Skill = 어떻게 할지
Script = 반복을 어떻게 결정적으로 할지
Tool = 어디에 연결할지
Memory = 무엇을 기억할지
Harness = 완료를 어떻게 증명할지
```

## 9. 현재 관리상 중요한 문제

### 중복과 provenance

Hermes 104개, Claude 21개, Codex 27개, Leopard 4개가 있어 총 156개의 `SKILL.md`가 확인된다. 하지만 다음은 아직 별도 registry로 통합되지 않았다.

```text
owner
source repository
version
last verified
required tools
side effects
supported platforms
```

### Skill과 외부 plugin의 혼재

`~/.claude/plugins/cache`에는 외부 plugin의 benchmark·bridge·skill script도 존재한다. 이들은 사용자 제작 Skill과 구분해야 한다.

```text
사용자/로컬 Skill
외부 marketplace Skill
bundled Skill
canonical Leopard Skill
Codex 동기화 Skill
```

### 실행 가능성 검증 부족

`SKILL.md`가 존재한다고 실제 기능이 사용 가능한 것은 아니다. 다음을 별도로 확인해야 한다.

```text
필수 command 존재
필수 credential 존재
연결 서비스 접근 가능
예제 command 실행 가능
산출물 검증 가능
```

독립 `SKILL.md`가 검증되지 않은 기능을 사용 가능하다고 주장해서는 안 된다.

## 10. 권장 Skill Registry

앞으로 각 Skill에 다음 metadata를 붙이는 것이 좋다.

```yaml
name: homelab-k3s-ops
owner: Hermes
source: local-or-bundled
canonical_source: leopard-or-repository-url
runtime: read-only
required_tools:
  - curl
  - ssh
side_effects: none
success_condition: current trace and timestamp present
failure_condition: endpoint unavailable or stale evidence
last_verified: 2026-08-10
```

특히 `owner`는 “최초 작성자”가 아니라 운영 책임 주체로 정의하는 것이 실용적이다.

```text
owner = 누가 유지·검증하는가
author = 누가 최초 작성했는가
source = 어디서 왔는가
runtime = 어느 Agent가 로드하는가
```

## 결론

이 Mac의 Skill 생태계는 단순한 프롬프트 모음이 아니다. 이는 여러 Agent가 역할을 나누어 일하기 위한 **운영 지식·권한·검증·도구 연결 계층**이다.

```text
Hermes:
  넓은 범용 catalog와 중앙 orchestration

Claude:
  프로젝트·Telegram·로컬 실행 Skill

Codex:
  전문 reviewer와 Ouroboros worker Skill

Leopard:
  Git canonical 공유 Skill
```

가장 중요한 원칙은 다음과 같다.

> **Skill의 가치는 지시문 길이가 아니라, 반복 실패를 줄이고 실제 완료 증거를 남기는 능력에서 나온다.**

그리고 누가 만들었는지 불명확한 파일에 임의로 저자를 붙이기보다, 실제 경로·Git provenance·설치 로그·실행 주체를 기준으로 기록하는 것이 Agent 생태계를 오래 유지하는 방법이다.

## References

- [Hermes Agent Documentation](https://hermes-agent.nousresearch.com/docs)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [Ouroboros Repository](https://github.com/Q00/ouroboros)
- [Codex Documentation](https://developers.openai.com/codex/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Leopard canonical skills](https://github.com/MyoungSoo7/leopard)

*이 inventory는 2026-08-10 KST에 로컬 경로에서 실제 검색한 `SKILL.md` 기준이다. 외부 plugin cache와 프로젝트별 worktree에 있는 파일을 모두 합친 완전한 전역 목록으로 과장하지 않는다.*

*공개 글에는 credential, token, private IP, 내부 endpoint를 포함하지 않았다.*
