---
layout: post
title: "72시간에 수백 개 PR을 만든 사건을 어떻게 이해할 것인가: 100개 터미널과 하네스 엔지니어링"
date: 2026-08-08 23:25:00 +0900
categories: [AI, Engineering, DevOps]
tags: [Harness Engineering, Claude Code, Ouroboros, tmux, cmux, GitHub, Agent]
---

# 72시간에 수백 개 PR을 만든 사건을 어떻게 이해할 것인가

## 먼저 확인된 사실과 미확인 사실을 나눈다

나정환의 LinkedIn 게시물과 AI 팟캐스트 소개는 다음 사건을 언급한다.

> 72시간 만에 GitHub에 엄청난 커밋과 PR을 올렸고, 그 결과 GitHub 계정이 정지된 사건.

그가 Ouroboros 메인테이너라는 점과 하네스 엔지니어링을 설명했다는 점은 공개 검색 결과에서 확인된다. 그러나 다음 세부사항은 이번 글을 작성하는 시점에 1차 원문으로 확인하지 못했다.

- 실제로 터미널을 100개 띄웠는가
- 100개가 모두 동시에 LLM Agent를 실행했는가
- 150KB가 터미널 프로그램의 실행 파일 크기인지, 메모리 RSS인지
- tmux, cmux, 자체 터미널 중 무엇을 사용했는가
- 수백 개 PR의 자동 생성·검증·제출 비율이 얼마였는가

따라서 아래 내용은 사건의 사실을 재구성한 것이 아니라, 공개적으로 언급된 현상을 설명하기 위한 **가능한 시스템 구조와 운영적 고찰**이다.

## 핵심은 터미널 개수가 아니라 작업 슬롯이다

“터미널 100개”라는 표현은 실제로는 다음 중 하나일 수 있다.

```text
터미널 창 100개
tmux pane/session 100개
PTY subprocess 100개
worktree 100개
Agent 작업 슬롯 100개
```

이들은 서로 다르다. 터미널 100개를 만들어도 대부분이 대기 shell이면 LLM 작업량은 0이다. 반대로 하나의 supervisor가 100개의 subprocess를 관리하면 화면에 터미널이 100개 보이지 않아도 100개의 작업 슬롯을 운영할 수 있다.

실제 생산성은 다음 식에 가깝다.

```text
작업 처리량
= 작업 슬롯 수 × 작업당 성공률 × 검증 통과율
  ÷ 재작업·충돌·rate limit 비용
```

PR 개수가 많다는 것만으로 품질이나 기여 가치를 판단할 수 없는 이유다.

## 노트북 한 대에서 가능한 구조

가장 현실적인 구조는 다음과 같다.

```text
작업 큐
  ↓
scheduler / supervisor
  ↓
┌──────────────┬──────────────┬──────────────┐
│ worktree-001 │ worktree-002 │ worktree-003 │ ...
│ agent-001    │ agent-002    │ agent-003    │ ...
└──────────────┴──────────────┴──────────────┘
  ↓
각 작업의 test → diff → branch → PR
```

각 Agent는 반드시 독립된 작업 디렉터리 또는 Git worktree를 가져야 한다.

```bash
git worktree add /tmp/agent-001 -b agent/001 main
git worktree add /tmp/agent-002 -b agent/002 main
```

공유 작업 디렉터리를 100개 Agent가 동시에 수정하면 파일 충돌과 Git index 충돌이 발생한다. 따라서 병렬화의 핵심은 터미널이 아니라 **작업공간 격리**다.

## tmux를 사용했을 가능성

tmux는 다음 역할에 적합하다.

```text
tmux server
 ├─ session agent-001
 ├─ session agent-002
 ├─ session agent-003
 └─ session agent-100
```

장점은 SSH가 끊겨도 세션이 살아 있고, Linux·macOS 서버에서 동일하게 동작하며, CLI로 생성·조회·입력할 수 있다는 점이다. Agent 운영 서버, 원격 노드, 재부팅 복구에는 tmux가 현실적인 선택이다.

하지만 tmux는 Agent를 이해하지 않는다. 어떤 pane이 작업 완료인지, 어떤 pane이 승인을 기다리는지, 어느 branch가 어떤 PR과 연결됐는지를 직접 구성해야 한다.

## cmux를 사용했을 가능성

cmux는 tmux의 상위 버전이 아니라 목적이 다른 도구다. 공개 저장소 설명 기준으로 cmux는 Ghostty 기반의 macOS 네이티브 터미널이며, vertical tab, pane, Agent 알림 ring, Git branch·PR·port 표시, 브라우저 pane과 CLI/socket API를 제공한다.

따라서 cmux는 다음 상황에 유리하다.

```text
Mac 한 대에서 여러 Agent를 눈으로 관리
Agent가 입력을 기다릴 때 알림
workspace·branch·PR 상태 확인
브라우저와 터미널을 한 화면에서 검증
```

반면 cmux만으로 100개의 장기 원격 Agent를 운영한다고 단정할 수는 없다. 현재 공개 문서 기준으로 cmux는 macOS 로컬 작업공간에 강하고, SSH 단절과 원격 서버 세션 보존은 tmux가 더 적합하다.

현실적인 조합은 다음과 같다.

```text
cmux
 ├─ tmux attach agent-001
 ├─ tmux attach agent-002
 ├─ tmux attach agent-003
 └─ supervisor dashboard
```

cmux는 관찰·알림 UI, tmux는 세션 지속성, supervisor는 작업 재시작·큐·제한을 담당한다.

## 150KB 터미널이라는 말의 해석

“150KB 터미널”도 검증 없이 실제 메모리 절감 수치로 쓰면 안 된다. 가능한 의미는 서로 다르다.

```text
실행 파일 크기 150KB
프로세스 RSS 150KB
PTY wrapper의 private memory 150KB
터미널 UI의 추가 메모리 150KB
컨테이너 레이어 일부 150KB
```

특히 Agent 100개의 전체 메모리 사용량은 터미널만으로 결정되지 않는다.

```text
터미널/PTY
+ shell
+ Agent CLI
+ Node/Python runtime
+ Git worktree·파일 cache
+ 로그·buffer
+ LLM API 응답 대기
```

LLM을 원격 API로 호출하면 모델 가중치는 노트북에 없지만, 100개의 Agent 프로세스와 컨텍스트·로그·네트워크 연결은 여전히 자원을 사용한다. 따라서 150KB라는 수치가 사실이어도 그것은 **전체 Agent 시스템 메모리**를 의미하지 않을 가능성이 높다.

## 대량 PR이 GitHub 계정 정지로 이어질 수 있는 이유

GitHub는 PR 개수만 보는 것이 아니다. 다음 신호가 함께 나타나면 자동화·스팸·남용으로 판단될 수 있다.

- 짧은 시간에 비정상적으로 많은 PR 생성
- 유사한 제목·본문·변경 패턴 반복
- 여러 저장소에 대한 빠른 대량 활동
- 낮은 테스트 품질 또는 빈 내용의 PR
- 동일 계정·토큰·IP에서의 burst 요청
- 타 저장소에 대한 무차별 자동 제출
- maintainer 요청이나 프로젝트 규칙을 무시한 반복 작업

여기서 핵심 교훈은 Agent를 많이 실행하지 말라는 것이 아니다. **작업 생성과 외부 제출 사이에 품질·정책·속도 게이트가 필요하다**는 것이다.

```text
Agent 생성
→ local test
→ diff/secret/license 검사
→ 중복·유사 PR 검사
→ rate limit
→ maintainer 정책 확인
→ 사람이 승인한 것만 push/PR
```

## Ouroboros와 하네스 엔지니어링의 관점

이 사건을 하네스 엔지니어링 관점에서 보면 Agent 수보다 다음 제어면이 중요하다.

```text
Planner
  ↓
Task queue
  ↓
Isolated worktree
  ↓
Agent execution
  ↓
Test/security/license gates
  ↓
Evidence bundle
  ↓
Human approval
  ↓
GitHub delivery
```

Ouroboros 같은 검토 계층은 Agent의 말이 아니라 실제 diff, 테스트, 보안 결과, 실행 Trace를 기준으로 다음 단계 통과 여부를 판단해야 한다. “PR을 생성했다”와 “검토 가능한 변경을 전달했다”는 같은 말이 아니다.

## 우리 환경에 적용한다면

현재 우리 환경은 다음과 같다.

```text
봇1~4:
  tmux tgbot1~tgbot4
  Claude Code
  Telegram MCP

노드봇:
  systemd → tmux → Claude/bridge

Mac 실험:
  cmux + tgbot-experimental
```

이 구조를 100개 슬롯으로 확장하려면 한 번에 100개의 Claude를 무작정 띄우는 것이 아니라:

1. 큐에 작업을 등록한다.
2. 작은 batch만 동시에 실행한다.
3. 각 작업에 worktree와 branch를 할당한다.
4. RTK로 터미널 출력을 줄인다.
5. 테스트·보안·diff gate를 통과시킨다.
6. 중복·유사 PR을 차단한다.
7. GitHub API rate limit과 프로젝트 정책을 확인한다.
8. 사람이 승인한 결과만 push·PR한다.

## 결론

나정환 사례에서 배울 점은 “터미널 100개를 만드는 비법”보다 **한 대의 컴퓨터를 Agent 작업장으로 바꾸는 운영 모델**이다.

```text
cmux = Mac의 관찰·알림·workspace UI
 tmux = 세션 지속성과 원격 운영
worktree = 코드 격리
scheduler = 작업량 제어
RAG/LLM = 작업 수행
Ouroboros = 검토·증거 게이트
GitHub = 승인된 결과의 전달 계층
```

100개의 터미널이 실제로 존재했는지, 150KB가 무엇을 의미하는지, 어떤 도구 조합을 사용했는지는 원문 Trace 없이는 확정할 수 없다. 그러나 위 구조라면 노트북 한 대에서 많은 Agent 작업 슬롯을 운영하는 것은 기술적으로 설명 가능하다.

다만 **수백 개 PR을 빠르게 올리는 능력과 좋은 오픈소스 기여는 다르다.** 좋은 하네스는 속도를 높이는 동시에 작업 중복·품질 저하·보안 유출·GitHub 남용을 막아야 한다.

## 참고 자료

https://kr.linkedin.com/posts/junghwan-na-ba7228302_72%EC%8B%9C%EA%B0%84%EB%A7%8C%EC%97%90-%EA%B9%83%ED%97%99%EC%97%90-%EC%97%84%EC%B2%AD%EB%82%9C-%EC%BB%A4%EB%B0%8B%EA%B3%BC-pr%EC%9D%84-activity-7459252852352266240-jH69
- [Ouroboros](https://github.com/Q00/ouroboros)
- [cmux](https://github.com/manaflow-ai/cmux)
- [cmux 공식 사이트](https://cmux.com/)
- [tmux 공식 사이트](https://github.com/tmux/tmux)
- [기존 블로그의 Ouroboros AgentOS 검증 글](/2026/07/30/ouroboros-agentos-roadmap-verification/)

> 이 글은 공개적으로 확인된 링크와 우리 환경의 실행 구조를 바탕으로 작성한 분석이다. 100개 터미널, 150KB, 실제 사용 도구와 처리량은 원문 Trace가 확인되기 전까지 가설로 표시한다.
