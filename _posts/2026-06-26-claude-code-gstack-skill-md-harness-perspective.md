---
layout: post
title: "Claude Code 의 gstack 과 SKILL.md — harness 관점 에서 보는 4 축 프레임워크 활용법"
date: 2026-06-26 02:30:00 +0900
categories: [claude-code, ai, skills, harness]
tags: [claude-code, skill-md, gstack, harness, garry-tan, agent-skills, superpowers]
---

![Garry Tan의 gstack /office-hours SKILL.md 4대 축 분석](/assets/images/claude-code-gstack-skill-md-framework.jpg)
*Garry Tan 의 gstack /office-hours SKILL.md 의 4 핵심 축 — Role / Principles / Prohibitions / Output Format. Claude Code 를 *전체 스타트업 팀* 으로 만드는 *스킬 기반 분해* 의 한 예시.*

Claude Code 의 `Skill` 시스템 을 1년+ 사용 했다. 처음 엔 *문서 한 장* 으로 보였던 SKILL.md 가, 시간 이 지나면서 *진짜 의 agent 행동 의 모듈* 임 을 알게 됐다. 그 SKILL.md 의 *구조* 를 *Garry Tan 의 office-hours 평가 프레임워크* 로 풀어 둔 위 다이어그램 — *4 축 (Role / Principles / Prohibitions / Output Format)* 이 *어떤 SKILL.md 에든 적용 가능 한 골격* 이다.

이 글 은 *harness (Claude Code 의 runtime) 가 SKILL.md 를 *어떻게 *읽고 invoke 하는지* + *4 축 프레임워크 를 *내 skill 에 어떻게 적용* 하는지* — 1년+ 운영 경험 으로 정리.

---

## 1. SKILL.md — *Claude Code 의 *behavior 단위***

Claude Code 의 `skills/` 디렉토리 의 각 폴더 가 *하나의 skill*. 그 안 의 `SKILL.md` 가 *skill 의 *진짜 본체*. 내 클러스터 의 실 예 :

```
~/.claude/skills/
├── settlement-flyway-migration/SKILL.md
├── lemuel-xr-mental-health-safety/SKILL.md
├── quant-pipeline-stability/SKILL.md
├── academy-cve-policy/SKILL.md
└── (다른 30+ 스킬)
```

각 SKILL.md 의 *기본 형태*:

```markdown
---
name: settlement-flyway-migration
description: settlement 의 Flyway 마이그레이션 작성 시 활성화...
---

# settlement — Flyway 마이그레이션 작성 가이드

## 언제 활성화되나
- ...

## 현재 컨벤션 — 정수 번호 단조 증가
- ...

## 핵심 패턴
- ...
```

frontmatter 의 `description` 은 *harness 가 *invoke 결정 시 *읽는 한 줄*. body 는 *invoke 후 model 이 *따르는 instructions*.

---

## 2. Harness 관점 — *SKILL.md 의 *생명 주기***

내가 실제로 관찰한 *harness 의 *skill 처리 순서*:

### Step 1 — *session start 시 *registry 로딩***
세션 시작 시 *harness 가 *모든 SKILL.md 의 *frontmatter 만 읽음*. *name + description* 만 *system prompt 의 *available-skills 섹션 으로 주입*. body 는 *아직 안 읽음*.

내 *현재 세션* 의 *<system-reminder>* 안 :
```
- lemuel-xr-mental-health-safety: lemuel-xr 에서 사용자 에게 노출될 모든 텍스트...
- settlement-flyway-migration: settlement 의 Flyway 마이그레이션 작성 시 활성화...
- claudeclaw: Claude Code Channels 텔레그램 연동 설치 가이드...
(약 30+ 스킬 의 *frontmatter 만*)
```

→ harness 의 *최적화 전략* — *수십 ~ 수백 skill 의 *full body* 를 *모두 prompt 에 넣지 않음*. *얇은 description 만*. *body 는 *필요할 때만 lazy load*.

### Step 2 — *task 매칭*
사용자 의 *요청* 또는 *현재 작업* 이 *어느 skill 의 description 과 매칭* 되면 *model 이 *Skill tool 호출* — 그 시점 에 *full body* 를 *읽고 *system prompt 에 주입*.

예: 사용자 가 "settlement Flyway V38 작성" 요청 → model 이 `Skill("settlement-flyway-migration")` 호출 → SKILL.md body 가 *현재 컨텍스트 에 *완전 주입* → model 이 *그 내용 을 *따라* 작성.

### Step 3 — *body 의 *지속성*
한 번 invoke 된 SKILL.md 의 body 는 *해당 세션 의 *system prompt 의 일부* 로 남음. *반복 작업 시* 마다 *재 invoke 안 함*.

### Harness 의 *3 가지 제약*

1. **description 길이**: 너무 길면 *모든 skill 의 *registry 가 *prompt token 소모*. *200~400 자* 가 *합리적 상한*.
2. **body 길이**: invoke 후 *prompt 의 일부* 가 됨. *너무 길면 *context window 부담* + *해당 세션 의 다른 task 압박*. *수백 줄 이상 의 SKILL.md 는 *split (sub-files)* 권장.
3. **description 의 매칭 정밀도**: *너무 일반 적이면 *오 invoke* (관계 없는 task 에 활성화), *너무 구체 적이면 *under invoke* (정작 필요한 task 에 활성화 안 됨).

---

## 3. 4 축 프레임워크 — *다이어그램 의 *진짜 가치***

다이어그램 의 *Role / Principles / Prohibitions / Output Format* 은 *어떤 SKILL.md 든 적용 가능* 한 *체크리스트*. 

### 축 1 — Role (역할)

*"이 skill 이 *model 에게 *어떤 역할 을 *요구* 하는지"*. 다이어그램 의 *gstack 예시*:
- "창업가 관점 판단기"
- "시니어 PM/CEO 처럼 사고"
- "Garry Tan 의 판단력 압축"

→ *model 의 *의식 모드* 를 *전환*. *일반 적인 coding assistant* 가 *VC partner* 의 *시야* 로 *전환*. *prompt engineering 의 *persona 기법* 의 정형화.

내 *settlement-flyway-migration* 의 *Role*:
- *settlement 의 DB schema 책임자*
- *Triple Idempotency 패턴 의 *진짜 의도 알고 있는 사람*

### 축 2 — Principles (원칙)

*"task 수행 시 *어떤 기준 으로 *판단 / 선택* 하는지"*. gstack 의 *6 Force Questions* (수요현실, 고통, 특정성, 진입점, 놀라움, 적합성) 가 그 예. *각 질문 이 *판단 의 *축*.

내 *settlement-flyway-migration* 의 *Principles*:
- *정수 번호 단조 증가* (V1 → V37)
- *Triple Idempotency 의 L3 (자연키 UNIQUE) 강제*
- *outbox_events / processed_events 의 *고정 스키마* 유지

### 축 3 — Prohibitions (금지사항)

*"이 task 에서 *절대 *하지 말아야* 할 것"*. *negative space 의 정의* — *positive instructions 만 으론 *애매한 영역* 의 *명시 적 차단*.

gstack 의 *금지사항*:
- *Boil the lake philosophy* (모든 사용자 한 번에 해결 시도)
- *품질 타협*
- *근거 없는 변경*
- *직접 적인 추측*

내 *settlement-flyway-migration* 의 *Prohibitions*:
- *타임스탬프 컨벤션 사용 금지* (settlement 은 정수만)
- *ADD CONSTRAINT 의 idempotent wrap 누락 금지* (06-23 V50 사고 의 교훈)
- *Outbox 스키마 의 *event_id UNIQUE 제거 금지*

### 축 4 — Output Format (출력 형식)

*"task 결과 의 *구체 적 *형식*"*. gstack 의 *BUILD / No-BUILD 결정 신호*, *Design Doc 저장*, *구조화 된 가이드라인*.

내 *settlement-flyway-migration* 의 *Output Format*:
- *V{N+1}__{snake_case_summary}.sql* 파일 명 형식
- *주석 의 *컨텍스트 한 줄*
- *마이그레이션 별 *Rollback note*

---

## 4. *4 축 적용 — *내가 새 SKILL.md 작성 시 *체크리스트***

다이어그램 의 *4 축* 을 *나의 SKILL.md 작성 절차* 로 변환:

```markdown
---
name: <skill-id>
description: <언제 활성화되는지 + 어떤 task 에 도움 되는지, 200~400 자>
---

# <Skill 의 의도 의 한 줄>

## 언제 활성화되나 (When)
- 경로 / 파일 패턴
- 어휘 / 키워드 트리거

## 역할 (Role)
- 이 skill 활성화 시 model 의 *의식 모드*
- 어떤 *전문가 시야* 로 task 보는지

## 원칙 (Principles)
- 판단 의 *축* 5~7 개
- *Why* 명시 (각 원칙 의 *근거*)

## 금지사항 (Prohibitions)
- 절대 하지 말 것
- *과거 사고 의 사례* 인용 (구체 적)

## 출력 형식 (Output Format)
- 결과물 의 *형식 / 구조*
- *예시 코드 / 템플릿*

## 예시 (Examples) — *선택*
- *Before / After* 또는 *정상 / 안티 패턴*
- *과거 의 실제 PR 또는 commit 인용*

## 회복 절차 — *선택*
- 잘못 된 경우 *어떻게 되돌리나*
```

→ *4 축 + 활성화 조건 + 예시 + 회복 절차* 의 *7 섹션*. *gstack 의 4 축 의 *확장*.

---

## 5. *anti-pattern — *약한 SKILL.md 의 *흔한 5 가지 함정***

1년+ 운영 에서 *내가 *직접 망친 SKILL.md* + 다른 사람 의 *공통 약점*:

### Anti-pattern 1 — *너무 추상 적인 description*
```yaml
# 안 좋은
description: 좋은 코드 작성 시 활성화

# 좋은
description: settlement 의 order-service/src/main/resources/db/migration/ 안에서 Flyway V{N}__*.sql 파일 작성 시 활성화. 정수 번호 단조 증가, Triple Idempotency 패턴, settlement_immutability_trigger 자동 반영.
```
*추상 적 description* = *harness 가 *언제 invoke 할지 모름*. *under-invoke* 발생.

### Anti-pattern 2 — *Role 없는 *원칙 만***
원칙 만 나열 하면 *model 이 *왜 그 원칙* 인지 *맥락 부족*. *Role 이 *동기 부여* — *"settlement 의 DB 책임자 로서"* 같은 한 줄 이 *깊은 차이*.

### Anti-pattern 3 — *Prohibition 의 *근거 부재***
```markdown
# 약함
- ADD CONSTRAINT 의 idempotent wrap 의무

# 강함
- ADD CONSTRAINT 의 idempotent wrap 의무
  (2026-06-23 settlement V50 사고 의 직접 교훈 — partial 적용 후
   ADD CONSTRAINT 재실행 시 duplicate_object 에러 → CrashLoop 160 회.
   DO $$ EXCEPTION WHEN duplicate_object THEN NULL $$ wrap 의무.)
```
*근거 가 *명시* 되면 *model 이 *edge case 에서 *근거 따라 판단 가능*. *근거 없으면 *맹목 적 적용*.

### Anti-pattern 4 — *Output Format 의 *부재***
*"DB 변경 하라"* 만 명시 → model 이 *각자 다른 형식* 으로 생성. *output 의 *예시 한 줄* — *"V38__add_user_status_history.sql 같은 형식"* — 이 *결과 의 일관성*.

### Anti-pattern 5 — *너무 긴 body*
*500 줄 SKILL.md* — invoke 후 *context window 의 큰 부분*. *짧고 정밀* + *깊이 가 필요 한 sub-topic 은 *별도 reference 파일*. Anthropic 공식 의 *SKILL.md 의 reference 패턴* 이 그 처방.

---

## 6. *gstack 의 *진짜 의도 — *판단력 의 *압축***

다이어그램 의 *gstack* 이 *진짜 의도* 는 *"Garry Tan 의 판단력 을 *압축 해서 *Claude 가 *대신 사용 하게"*. 

이게 *SKILL.md 의 *진짜 가치*. *지식 전달 (RAG, fine-tuning)* 보다 *판단 의 압축 (prompt engineering)* 이 *현재 LLM 의 *진짜 강점*. *Garry Tan 의 판단 100 페이지 * 가 *4 축 200 줄 SKILL.md 로 *압축 가능*. *그 압축 된 판단 이 *Claude 의 model weight 의 *지능 위에서 *재구성*.

내 *settlement-flyway-migration* 도 동일 패턴 — *내 14개월 의 DB schema 사고 (V50, V44, V35 등)* 의 *경험* 을 *SKILL.md 의 *200 줄* 로 압축. *새 세션 의 Claude* 가 *그 경험* 위에서 *나처럼 판단*.

→ *SKILL.md 의 *진짜 자산 가치* — *"my judgment 의 *transferable 형태"*. *내가 잊더라도, 다른 사람 이 인계 받더라도, *새 세션 의 LLM 이 *처음 부터 시작 해도* — *같은 판단 의 *재현 가능성*.

---

## 7. *Harness 관점 의 *최적 SKILL.md 작성 패턴***

내 운영 경험 의 *권장 5 가지*:

### 1. description 은 *trigger + 가치 의 *2 문장***
```yaml
description: <언제 활성화 — 경로/키워드/상황>. <어떤 가치 제공 — 무엇을 자동 적용 하는지>.
```
*첫 문장* 이 *trigger*, *두 번째* 가 *가치*. harness 의 *invoke 결정 의 *2 단계 매칭* 에 *적합*.

### 2. body 는 *200~400 줄 의 *집중***
*1000 줄 SKILL.md* 는 *invoke 후 context 폭증*. *200~400 줄 의 *핵심 + reference 파일 분리* 가 *합리적*.

### 3. *과거 사고 의 사례 인용*
*"06-23 V50 사고 의 교훈"* 같은 *구체 적 timestamp + 사고 ID*. *모호 한 원칙* 보다 *훨씬 강력*. *model 이 *비슷한 상황 인식 시 *바로 적용*.

### 4. *Negative space 명시*
*positive instruction 만 으론 *모호*. *Prohibitions 의 *명시 적 차단* 이 *진짜 안전 망*. *Anti-pattern 의 *Before / After* 예시.

### 5. *output format 의 *템플릿***
*결과물 의 *예시 형식* 을 *SKILL.md 안 에 *직접 포함*. *model 이 *0 부터 추측 안 하고 *템플릿 의 *빈칸 채움*.

---

## 8. *내가 자주 작성 하는 SKILL.md 의 *변종 5 가지***

내 클러스터 의 *실 사용 변종*:

| SKILL 종류 | 패턴 |
|---|---|
| *마이그레이션 (settlement-flyway, lemuel-xr-flyway, sparta-flyway)* | *컨벤션 + 사고 회고 + 템플릿* |
| *보안 (security-scan, lemuel-xr-mental-health-safety)* | *체크리스트 + 금지사항 + 회복 절차* |
| *코드 (lemuel-xr-mermaid-sequence, lemuel-xr-theology-tone)* | *Role + Examples + Anti-patterns* |
| *운영 (claudeclaw, k8s-lemuel-cluster-toolbox)* | *상황 별 분기 + 결정 매트릭스* |
| *글쓰기 (writing-skills, brainstorming)* | *워크플로우 단계 + 산출물 형식* |

각 변종 이 *공통 의 *4 축* 위에서 *맥락 별 강조 다름*. *gstack 의 *판단 압축* + 내 의 *경험 압축* 이 *같은 의도*.

---

## 9. *Claude Code 의 *Skill 시스템 의 진화*

2024 년 의 Claude Code → 2026 년 까지 *Skill 시스템 의 변화*:

- *2024 — *system prompt 의 manual 주입* (skill 의무 활성)
- *2025 — *SKILL.md 의 *frontmatter 매칭* + *Skill tool 의 명시 적 invoke*
- *2025 H2 — *Skill tool 의 *자동 invoke* + *registry 의 lazy load*
- *2026 — *MCP server 의 *skill 노출* (skills 가 *MCP resource 로 통합*)

*MCP + Skill 의 융합* 이 *현재 의 진화 방향*. *외부 server 가 *skill 제공*, *Claude 가 *그 skill 자동 활용*. *Anthropic 공식 의 *skills MCP server* 가 *2026 의 표준*.

---

## 10. 마치며 — *SKILL.md 는 *자산***

다이어그램 의 *4 축* 은 *Garry Tan 의 office-hours 의 *분석 도구*. 그러나 *진짜 가치* 는 *그 분석 의 *적용 방향*:

> *내 14 개월 의 클러스터 운영, 33 도메인 의 사고 회고, settlement V50 의 idempotent 패턴, sparta 의 gateway 충돌 회복* — *이 모든 *경험 의 압축* 이 *내 SKILL.md 의 *물리 적 자산*.

블로그 글 이 *지식 의 *전파* 라면, SKILL.md 는 *판단 의 *실행 형태*. 글 은 *읽는 사람 의 *해석* 에 따라 *효과 다름*. SKILL.md 는 *Claude 가 *항상 동일 한 판단 으로 *재현*.

내가 *오늘 밤 *완전히 잊는 일* 이 생겨도, 또는 *다른 시니어 가 *클러스터 인계 받아도* — *SKILL.md 안 의 *판단 의 압축* 이 *Claude 의 *어떤 새 세션* 에서도 *동일 한 정밀도 로 작동*. *진짜 의 *transferable 자산*.

*Claude Code 의 *Skill 시스템* 을 *깊이 활용 하는 시점* — *내 판단 의 *어느 부분 을 *어떤 SKILL.md 로 *압축 할지* — 그 의식 적 결정 이 *2026 년 의 시니어 엔지니어 의 *agentic productivity 의 *진짜 자산화 의 시작*.

---

## 참고

- Garry Tan 의 *Y Combinator office hours* — 원본 평가 프레임워크
- *Anthropic Skills 공식 문서* — [docs.claude.com/skills](https://docs.claude.com/en/docs/agents-and-tools/agent-skills)
- *Model Context Protocol (MCP)* — [modelcontextprotocol.io](https://modelcontextprotocol.io)
- 자매편:
  - [AI Agent Architecture 분해](/2026/06/26/ai-agent-architecture-decomposition.html)
  - [AI 코드 PR 머지 7 질문](/2026/06/21/ai-code-pr-merge-7-questions-checklist.html)
  - [바이브 코딩 과 시니어 개발자 7 가지 기준](/2026/06/18/vibe-coding-and-senior-developer-7-criteria.html)
  - [Function Calling Deep Dive](/2026/06/15/function-calling-deep-dive.html)
