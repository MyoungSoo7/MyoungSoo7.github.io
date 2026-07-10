---
layout: post
title: "Claude Code 하네스 를 직접 만들기 — *SKILL.md + hook* 기획 부터 시운전 까지"
date: 2026-07-10 14:00:00 +0900
categories: [ai, engineering, agentic-coding]
tags: [claude-code, harness-engineering, skill-md, hook, superpowers, plugin, workflow]
---

앞의 두 글 — [하네스 해부]({% post_url 2026-07-10-harness-engineering-anatomy-from-a-diagram %}) 와 [Superpowers 구조]({% post_url 2026-07-10-superpowers-plugin-structure %}) — 는 *개념* 이었다. 이번 엔 **직접 하나 만든다.** "회의록 을 1페이지 로 요약" 하는 하네스 를, Superpowers 패턴 그대로 `.claude/` 폴더 에 SKILL.md 와 hook 으로 짓는 4단계 기획 이다.

핵심 아이디어 는 하나 — **반복 되는 작업 을 프롬프트 로 매번 설명 하지 말고, 하네스 로 굳혀서 매번 같은 품질 이 나오게** 한다.

---

## 1. 워크스페이스 — *무엇 을 어디에 두나*

![프로젝트 루트의 .claude 폴더 구조 — settings.json, hooks/, skills/ (메타 스킬 + 도메인 스킬)](/assets/images/harness-md-1-workspace-layout.jpg)

먼저 파일 배치. 하네스 는 프로젝트 루트 의 `.claude/` 안 에 산다:

```
<프로젝트-루트>/
└── .claude/
    ├── settings.json              # SessionStart + PostToolUse 훅 등록
    ├── hooks/
    │   ├── session-start.sh        # 세션 시작 시 핵심 규약 을 컨텍스트 상단 에 주입
    │   └── check-1page-output.sh   # Write/Edit 직후 산출물 가드 (검사 n종)
    └── skills/
        ├── using-<프로젝트>-harness/
        │   └── SKILL.md            # 메타 스킬: hook 협업 규약·재작성 행동 양식
        └── <도메인>-to-1page/
            └── SKILL.md            # 도메인 스킬: 보존 표현·7칸 스키마·처리 순서·예시
```

**두 스킬 의 분담 이 핵심** — Superpowers 패턴 그대로 다:

- **메타 스킬(`using-*`)** — 어떤 도메인 이든 공통 인 *협업 규약*. "훅 과 어떻게 협업 하나, 재작성 은 어떤 양식 으로 하나".
- **도메인 스킬(`<도메인>-to-1page`)** — 본 작업 에만 적용 되는 *구체 규칙*. 보존 할 표현, 7칸 스키마, 처리 순서, 예시.

메타 는 *변하지 않는 뼈대*, 도메인 은 *갈아 끼우는 살*. 새 도메인 이 생기면 도메인 스킬 만 하나 더 쓰면 된다.

---

## 2. 작성 절차 — *워크스페이스 를 채우는 6단계*

![작성 절차 6단계 — 폴더 정렬, 메타 스킬, 도메인 스킬, SessionStart hook, PostToolUse hook, settings+시운전](/assets/images/harness-md-2-build-steps.jpg)

빈 폴더 를 채우는 순서:

1. **폴더 정렬** — `using-<프로젝트>-harness/`, `<도메인>-to-1page/`, `hooks/` 를 먼저 만든다. 뼈대 부터.
2. **메타 스킬** — `using-*` SKILL.md 에 협업 규약·재작성 양식·도메인 호출 순서 를 쓴다.
3. **도메인 스킬** — `<도메인>-to-1page` SKILL.md 에 보존 표현·7칸 스키마·처리 순서·예시 를 쓴다.
4. **SessionStart hook** — `session-start.sh` 가 핵심 규약 을 *stdout 으로 출력*. 세션 시작 시 그 출력 이 컨텍스트 상단 에 박힌다. (모델 이 규약 을 *까먹기 전* 에 먼저 보게)
5. **PostToolUse hook** — `check-1page-output.sh` 가 Write/Edit *직후* 에 보존 표현 누락·확인 필요 항목·미확인 수치 단정 을 사후 검사. (산출물 이 나온 *뒤* 에 가드)
6. **settings + 시운전** — `settings.json` 에 두 훅 을 등록 하고, *회의록 1건* 으로 실제 돌려본다.

포인트 는 훅 의 *두 타이밍* 이다 — **SessionStart 는 사전 주입(잊지 않게), PostToolUse 는 사후 검사(빠뜨리지 않게).** 앞뒤 로 규율 을 못 박는다.

---

## 3. 입력 — *앞 산출물 이 어디로 가나*

![입력 매핑 표 — 설계 체크리스트·md 템플릿·한계 진단표·Superpowers 관찰·설계도가 SKILL.md의 각 섹션으로](/assets/images/harness-md-3-input-mapping.jpg)

이 기획 이 영리 한 지점. 하네스 를 *맨땅* 에서 쓰는 게 아니라, **앞 단계 에서 만든 산출물 을 SKILL.md 의 각 자리 로 옮겨 붓는다**:

| 출처(앞 산출물) | 워크스페이스 에서 의 역할 |
|---|---|
| 설계 체크리스트 | SKILL.md 의 *역할·금지·출력 형식* 섹션 |
| md 템플릿 v1 | SKILL.md 의 *골격* (역할/입력/처리/금지/출력/예시) |
| 한계 진단표 | SKILL.md 의 *적용 범위·범위 밖* 섹션 |
| Superpowers 관찰 + 작성 프랙티스 | SKILL.md *frontmatter*(name·description·triggers) + `.claude/` 구조 |
| 설계도 | SKILL.md *처리 순서·출력 맵핑* + hook 검사 항목 |

즉 **SKILL.md 는 창작 이 아니라 조립** 이다. 역할·금지·출력·범위·처리순서 라는 *칸* 이 정해져 있고, 앞 산출물 을 그 칸 에 배치 하면 된다. 좋은 하네스 문서 는 *잘 쓴 글* 이 아니라 *잘 채운 표* 다.

---

## 4. 자기 검수 — *여섯 파일 이 제대로 됐나*

![자기 검수 4체크 — 메타/도메인 스킬 분리, frontmatter triggers, 두 hook, 시운전 메모 + 최종 합격 기준](/assets/images/harness-md-4-self-review.jpg)

짓고 나서 통과 해야 할 체크리스트:

- **CHECK 1 — 메타·도메인 스킬 분리.** `using-*harness/` 와 `<도메인>-to-1page/` 가 *따로* 있나. 메타=협업 규약, 도메인=보존 표현·스키마.
- **CHECK 2 — frontmatter triggers.** 두 SKILL.md 의 `description` 에 도메인 *트리거 단어* 가 들어 있나. (있어야 필요할 때 자동 로드)
- **CHECK 3 — SessionStart + PostToolUse hook.** `session-start.sh` 가 규약 stdout 출력, `check-1page-output.sh` 가 사후 검사, `settings.json` 에 둘 다 등록.
- **CHECK 4 — 시운전 메모.** 세션 시작 시 SessionStart 안내 가 뜨는지 + Write/Edit 직후 PostToolUse 통과/실패 한 줄.

그리고 **최종 합격 기준 이 압권** 이다:

> **같은 형식 의 회의록 을 다시 넣었을 때, 출력 칸 구성 이 첫 번째 와 *같은가?*** 같지 않다면 → SKILL.md 시운전 메모 에 이유 를 추가 하고 v2 작업 항목 으로 표시.

이게 하네스 의 존재 이유 그 자체 다 — **재현성.** 같은 입력 에 같은 구조 의 출력. 프롬프트 로 매번 하면 매번 다르지만, 하네스 로 굳히면 *두 번째 도 첫 번째 와 같다.* 이 시운전 을 통과 해야 비로소 "하네스" 라 부를 수 있다.

---

## 마무리 — 기획 이 곧 하네스 다

네 장 의 그림 을 관통 하는 흐름:

**어디에 두나(구조) → 어떻게 채우나(절차) → 무엇 을 붓나(입력) → 제대로 됐나(검수)**

이건 사실 *소프트웨어 기획* 과 똑같다. 폴더 구조 = 아키텍처, 6단계 = 구현 순서, 입력 매핑 = 요구사항 추적, 자기 검수 = 인수 테스트. 다른 점 은 산출물 이 앱 이 아니라 **"AI 가 매번 같은 품질 로 일 하게 만드는 껍데기"** 라는 것.

> 하네스 엔지니어링 의 실체 는 거창 하지 않다 — **`.claude/` 폴더 에 SKILL.md 두 장 과 훅 두 개 를 잘 배치 하고, 두 번째 시운전 이 첫 번째 와 같은지 확인 하는 것.** 규율 을 파일 로 굳히면, 잔소리 하는 시니어 가 폴더 안 에 상주 한다.

나 도 이 패턴 으로 프로젝트 마다 `.claude/` 를 채워 왔다. 회의록·정산 리포트·블로그 초안 — 반복 되는 것 은 전부 하네스 로 굳힐 후보 다. 다음 에 같은 작업 을 세 번째 하고 있다면, 그건 SKILL.md 로 만들 신호 다.
