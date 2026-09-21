---
layout: post
title: "Claude 기초부터 고급까지 100 — 한국어 Claude Code 학습서 리포 소개"
date: 2026-09-22 00:12:42 +0900
categories: claude-code
tags: [claude, claude-code, learning, mcp, skills, hooks, subagents]
---

Claude Code 를 한국어로 처음부터 끝까지 훑는 학습서가 GitHub 에 통째로 올라와 있다.
**[lsszz2100/Claude_100 — "Claude 기초부터 고급까지 100"](https://github.com/lsszz2100/Claude_100)** 이다.
WikiDocs 출판용 Markdown 원고 전체를 MIT 라이선스로 공개해 둔 리포로, 이 글은 그 목차를
실측으로 훑고 어떤 독자에게 어느 파트가 맞는지 정리한 소개다.

## 리포 기본 정보 (2026-09-22 실측)

| 항목 | 값 |
|---|---|
| 리포 | [github.com/lsszz2100/Claude_100](https://github.com/lsszz2100/Claude_100) |
| 저자 | AI_Innovation_Studio (리포 [TOC.md](https://github.com/lsszz2100/Claude_100/blob/main/TOC.md) 명기) |
| 라이선스 | MIT |
| 생성 / 최종 push | 2026-05-03 / 2026-08-03 (GitHub API 실측) |
| 스타 | 59 (2026-09-22 기준) |
| 형태 | `TOC.md` + `pages/` 아래 페이지별 Markdown, WikiDocs 출판용 원고 |

제목은 "100" 이지만 실제 페이지 번호는 001~120 이고, 부록까지 합치면 본문 페이지가 120개다.
000 서문과 999 마무리, 이미지 생성 계획(900)까지 원고 전체가 그대로 들어 있다.

## 목차 구조 — 12개 파트

[TOC.md](https://github.com/lsszz2100/Claude_100/blob/main/TOC.md) 기준 구성은 다음과 같다.

- **Part 01 입문 (001–010)** — Claude 란 무엇인가, 챗봇과 에이전트의 차이, Web/Desktop/CLI/IDE 차이, 설치와 첫 세션
- **Part 02 프롬프트 기초 (011–020)** — 프롬프트 4요소(역할·목표·맥락·제약), 예시 기반 프롬프트, Plan Mode 기초
- **Part 03 기본 명령 (021–030)** — `/help` `/clear` `/compact` `/cost`, 작은 버그 고치기, 커밋 메시지, 초급자가 피해야 할 실수
- **Part 04 프로젝트 메모리 (031–037)** — CLAUDE.md 의 역할, 디렉터리별 CLAUDE.md, PRD.md, progress.md 로 장기 작업 관리
- **Part 05 실무 개발 워크플로 (038–055)** — 기능 개발·버그 조사·리팩터링·테스트·보안 리뷰·PR 생성·릴리스 노트까지 업무별 프롬프트 패턴 18개
- **Part 06 작업 환경 확장 (056–065)** — VS Code/JetBrains, 원격·모바일 흐름, 세션 resume, context window 관리, 비용과 모델 선택
- **Part 07 Skills (066–074)** — SKILL.md 구조, slash commands 와의 차이, progressive disclosure, 쓸모없는 Skill 제거 기준
- **Part 08 Hooks (075–082)** — PreToolUse/PostToolUse, 파일 수정 전 보안 차단, 커밋 전 테스트, Hooks 보안 설계
- **Part 09 MCP (083–091)** — stdio 와 HTTP MCP, GitHub/DB/브라우저 MCP, OAuth 인증 보안, MCP 서버 검증 체크리스트
- **Part 10 Subagents 와 Agent Teams (092–099)** — 역할별 에이전트(리뷰어·테스트·문서·보안·구현), 병렬 작업, worktree 기반 멀티 에이전트
- **Part 11 프로덕션 운영 (100)** — Claude Code 프로덕션 운영 전략
- **부록 (101–120)** — 명령어 치트시트, 추천 `.claude` 폴더 구조·CLAUDE.md·PRD·Skill·Hook 템플릿, MCP 보안 감사표, RAG 설계 체크리스트, Docker/CI-CD 예시, 비용 최적화, 팀 도입 가이드, 최종 프로젝트 10개

입문(개념) → 프롬프트 → 일상 명령 → 프로젝트 메모리 → 실무 패턴 → 확장 기능(Skills/Hooks/MCP/Subagents) → 운영·팀 도입으로
올라가는 전형적인 계단식 커리큘럼이고, 각 단계가 실제 Claude Code 의 기능 축과 1:1 로 맞아떨어진다.

## 누구에게 맞나

- **이제 시작하는 사람** — Part 01~03 만으로 "설치 → 첫 세션 → 기본 명령 → 피해야 할 실수" 까지 간다. 한국어로 이 구간을 순서대로 정리한 자료는 드물다.
- **쓰고는 있는데 CLAUDE.md·Skill 을 안 만들어 본 사람** — Part 04(프로젝트 메모리)와 Part 07~08(Skills/Hooks)이 핵심 구간이다. 특히 073 progressive disclosure, 074 "쓸모없는 Skill 제거 기준", 082 "Hooks 보안 설계" 같은 꼭지는 기능 나열이 아니라 운영 관점이다.
- **팀 도입을 검토하는 사람** — 부록의 110 MCP 보안 감사표, 117 비용 최적화, 118 팀 도입 가이드가 바로 그 용도다.

## 읽을 때 주의할 점

이 리포는 서드파티 원고다. Claude Code 는 릴리스 주기가 짧아 세부 명령·설정은 원고 시점과
달라질 수 있다 — 리포 최종 push 가 2026-08-03 이므로(GitHub API 실측) 그 이후 변경분은 반영되어
있지 않다. 기능별 최신 사양은 공식 문서를 기준으로 대조하는 것이 안전하다:

- Claude Code 전반: [공식 문서 Overview](https://code.claude.com/docs/en/overview)
- Skills: [공식 Skills 문서](https://code.claude.com/docs/en/skills)
- Hooks: [공식 Hooks 문서](https://code.claude.com/docs/en/hooks)
- MCP: [Model Context Protocol 공식 사이트](https://modelcontextprotocol.io)

거꾸로 말하면 이 리포의 가치는 "최신 사양서" 가 아니라 **한국어로 된 학습 경로와 실무 패턴 모음**에
있다. 무엇을 어떤 순서로 익힐지, 업무별 프롬프트를 어떻게 구조화할지는 버전이 바뀌어도 유효하다.
MIT 라이선스라 사내 온보딩 자료로 가공해 쓰기에도 부담이 없다.

## References

- [lsszz2100/Claude_100 — Claude 기초부터 고급까지 100](https://github.com/lsszz2100/Claude_100) (1차 출처: README·TOC.md, MIT License)
- [Claude Code 공식 문서 — Overview](https://code.claude.com/docs/en/overview)
- [Claude Code 공식 문서 — Skills](https://code.claude.com/docs/en/skills)
- [Claude Code 공식 문서 — Hooks](https://code.claude.com/docs/en/hooks)
- [Model Context Protocol](https://modelcontextprotocol.io)

리포 메타데이터(생성일·최종 push·스타 수·라이선스)는 2026-09-22 GitHub API (`gh api repos/lsszz2100/Claude_100`) 실측값이다.
