---
layout: post
title: "Claude Code 의 SKILL.md — *하네스의 *5 축* 으로 본 *본질 — *반복*, *역할*, *원칙*, *금지*, *고정*"
date: 2026-05-29 01:55:00 +0900
categories: [llm, prompt-engineering, claude-code, agent]
tags: [claude-code, skill-md, prompt-engineering, harness, agent-design, system-prompt, llm-behavior]
---

> SKILL.md 는 *마크다운 파일* 이다. *그게 끝* 이다. *48 줄짜리* 텍스트가 *어떻게 LLM 의 *행동을 *재현 가능하게* 고정* 하는가? *''그냥 *프롬프트* 잖아''* 라고 단순화하는 순간, *왜 같은 LLM 이 *어떤 프롬프트는 *지키고* *어떤 프롬프트는 *3 턴 뒤 잊는가*''* 라는 질문에 *답을 못 한다*.
>
> Claude Code 의 *하네스 (harness)* 는 *''system prompt + tool 정의 + 컨텍스트 관리 + 메모리 시스템 + 슬래시 커맨드 + 훅''* 의 *결합 무대* 다. *SKILL.md 는 그 무대 위에서 *재사용 가능한 행동 패턴* 을 *외부 파일* 로 *분리한 것*. *''*Skill 을 *호출하면* *그 순간 그 텍스트가 *system prompt 처럼 *주입*''* 되는 *런타임 메커니즘*.

이 글은 SKILL.md 의 *본질* 을 *5 가지 축* — **반복 / 역할 / 원칙 / 금지사항 / 하네스 고정** — 으로 분해하고, *각 축이 *왜 LLM 의 *재현성* 을 만드는가*, 그리고 *왜 *그 축 하나만 빠져도 무너지는가* 를 풀어본다.

---

## 1. 출발점 — *''왜 같은 LLM 이 *다르게 행동* 하는가''*

LLM 은 *상태 없는 함수* 다. *입력 → 출력*. *같은 입력 → 같은 출력 *분포** (temperature 0 이라면 *결정론적*).

그렇다면 *''Claude 가 자꾸 *지시를 잊는다*''* 는 *어디서 오는가*?

답: ***''매 턴마다 *입력이 *다르다*''***.

- 턴 1: `[system] + [user_1]`
- 턴 2: `[system] + [user_1] + [assistant_1] + [user_2]`
- 턴 10: `[system] + [user_1] + ... + [user_10]` — *수만 토큰의 컨텍스트*

같은 system prompt 가 *맨 앞* 에 있어도, *컨텍스트가 길어지면* 그 영향력이 *현저히* 약해진다. *''*Lost in the middle*''* 현상 — *중간에 있는 정보는 *attention 이 *덜 간다***.

SKILL.md 가 풀려는 *진짜 문제* 가 이거다. *''*system prompt 가 *어떻게 *길어진 컨텍스트* 에서도 *지켜지는가*''*.

---

## 2. *축 1 — *반복* (Repetition)*

### 2.1 *왜 LLM 은 *지시를 잊는가**

Transformer 의 *attention* 은 *''*최근* 토큰''* 과 *''*반복된* 토큰''* 에 *더 강하게* 가중치를 둔다. 이건 *학습 데이터의 통계적 진실* 이다 — *사람의 글에서 *반복된 단어가 *중요*** 하기 때문.

이걸 *역으로 활용* 하는 게 SKILL.md 의 *반복 전략*.

### 2.2 *3 가지 반복 위치*

좋은 SKILL.md 는 *같은 핵심 명령* 을 *3 곳* 에 *반복* 한다.

```markdown
---
name: brainstorming
description: You MUST use this before any creative work — *반복 위치 1: front matter*
---

You MUST use this before any creative work — *반복 위치 2: 첫 줄*

## The Rule

Invoke this skill BEFORE writing any code — *반복 위치 3: 핵심 절*
```

- *Front matter* 의 description — *Skill *로딩 결정* 시 *읽힘*
- *첫 줄* — *LLM 이 *가장 먼저* 만나는 행동 지침*
- *핵심 절* — *구체적 *실행 시점* 명시*

### 2.3 *MUST / NEVER / ABSOLUTELY 의 *대문자 반복**

SKILL.md 의 *눈에 띄는 패턴*:

```
You ABSOLUTELY MUST invoke the skill.
This is not negotiable. This is not optional.
You cannot rationalize your way out of this.
```

*같은 의미를 *3 번* 다른 표현으로*. *과해 보이지만* 이건 *LLM 의 행동을 *실제로 바꾼다*. *공식 superpowers 의 *using-superpowers* 스킬이 이 패턴의 *교과서*.

### 2.4 *흔한 함정 #1 — *''한 번만* 말해도 알아듣겠지''*

```markdown
# 안티 패턴
Use TDD for all new features.
```

*1 줄짜리 지시* 는 *컨텍스트 8K 이후* 거의 *영향력 없음*. *3 곳에 분산 + 강조 형용사* 가 *진짜 효과*.

---

## 3. *축 2 — *역할* (Role)*

### 3.1 *''You are an expert X''* 의 *인지적 닻*

```markdown
You are a senior Spring Boot architect with 10 years of production experience.
```

이 한 줄이 *왜 효과적인가*? *통계적* 이유:

- *학습 데이터에서 *''senior architect''* 가 등장하는 문맥* 은 *''*검증된 패턴* / *trade-off 분석* / *production 경험''*
- LLM 은 *''*역할이 명시* 되면 *그 역할의 *통계적 분포* 안에서 *답을 *샘플링***

### 3.2 *역할의 *3 단계 깊이**

**Level 1 — *''너는 X 다''***
```
You are a JPA optimization expert.
```
*기본형*. 효과 있지만 *약함*.

**Level 2 — *''너는 X 인데, *왜 그런 *권한* 을 가졌는가*''***
```
You are a JPA optimization expert who has spent 5 years
hunting N+1 queries in high-traffic production systems.
You've seen the pattern where a single missing fetch join
caused 10,000 queries per request.
```
*경험* 까지 부여하면 *답이 *더 구체적* 으로 나옴*.

**Level 3 — *''너는 X 이고, *이 작업에서 *이런 결정* 을 할 권한이 있다*''***
```
You are a JPA optimization expert.

You have authority to:
- Refuse to add caching when proper fetch strategy would solve it
- Flag entity design that prevents efficient queries
- Insist on adding indexes when query plans show full scans
```
*권한* 까지 부여하면 *''*완곡한 *권고*'' 가 아니라 *''*명확한 *결정*''* 으로 응답*.

### 3.3 *역할의 *재현성* 효과*

같은 *system prompt* 의 *맨 앞* 에 역할이 *고정* 되면, *컨텍스트가 길어져도* LLM 의 *행동 분포가 *그 역할에 *anchored***. *''*초기 분포가 *결과 분포를 끌어당김***.

### 3.4 *흔한 함정 #2 — *역할이 *너무 일반적**

```
You are a helpful assistant.
```
*거의 의미 없음*. *''helpful''* 은 *기본 분포의 *중앙* — *어떤 분포로도 끌리지 않음*.

*''helpful Spring Boot security auditor''* 처럼 *영역 특정* 이 *진짜 효과*.

---

## 4. *축 3 — *원칙* (Principle)*

### 4.1 *''규칙''* 과 *''원칙''* 의 *차이*

**규칙 (Rule)** — *''*A 일 때 B 하라*''*. *조건-행동 매핑*.
**원칙 (Principle)** — *''*판단의 *기준*'' — *새로운 상황에서도 *유추 가능**.

```markdown
# 규칙 (Rule)
When user mentions Kafka, suggest Outbox pattern.

# 원칙 (Principle)
When data crosses a transaction boundary, atomicity must be preserved
by either co-transactional storage (outbox) or idempotent consumption.
The principle: *atomicity is *non-negotiable*; *the *mechanism* is.
```

원칙은 *''*나중에 *처음 보는 상황* 에서도 *지킬 수 있게''* 한다. 규칙만 있는 SKILL.md 는 *''*명시 안 된 경우 = 실패''*.

### 4.2 *원칙의 *3 가지 조건**

**조건 1 — *Why 가 *명시* 됨***
```markdown
Why: 과거 *원자성 깨진 outbox 가 *유령 이벤트* 를 *3 개 시스템* 으로 전파.
재발 방지 차원의 원칙.
```
*Why* 가 있으면 *''*이 원칙이 *이 상황에 *적용 되는가*''* 를 *LLM 이 *판단 가능**.

**조건 2 — *경계 조건이 *명시 됨***
```markdown
Exception: 단발성 작업이고 *재시도 가능 한 *조회* 만 일 때는 *원칙 완화 허용*.
```
경계가 *명시* 되면 *''*경계 안에서는 *철저히*, 경계 밖에서는 *유연하게*''* 가 *가능*.

**조건 3 — *반대편 *반례가 *명시* 됨***
```markdown
Counter-example: *''*속도가 중요* 하니까 *outbox 생략*''* 같은 주장은 *틀림*.
*outbox 는 *비동기 polling* 이라 *속도에 영향 없음*.
```
*''*잘못된 주장* 을 *반박할 *근거*''* 가 *함께 있으면 *LLM 이 *그 주장에 *흔들리지 않음***.

### 4.3 *흔한 함정 #3 — *원칙 없이 규칙만**

```markdown
# 안티 패턴
Always use @Transactional on service methods.
```
*''*왜 그런가*''* 가 *없으니* LLM 이 *새 상황에서 *적용 못 함*. *''*static 메서드는*?*, *''*read-only 는*?*, *''*Kafka listener 는*?*''*'' 같은 *모든 경우를 *별도 규칙 으로 *나열* 해야 함.

원칙 한 줄이 *규칙 10 줄* 보다 *효과적*.

---

## 5. *축 4 — *금지사항* (Prohibitions)*

### 5.1 *''*하지 마라*''* 가 *''*해라*''* 보다 *왜 강한가*

LLM 의 *학습 데이터* 에서 *''*Do not*''* / *''*NEVER*''* / *''*Don't*''* 의 *맥락 분포* 는 *''*경고 / 위험 / 중요 결정''*. 그래서:

- *''*Do X*''* 는 *''*기본 분포에 *X 를 추가*''*
- *''*NEVER X*''* 는 *''*분포에서 *X 를 *적극적으로 *배제*''*

*''*적극적 배제''* 가 *''*수동적 추가''* 보다 *강한 효과*.

### 5.2 *3 가지 금지 패턴*

**패턴 1 — *Red flag (붉은 깃발) 나열***
```markdown
## Red Flags — These thoughts mean STOP

| Thought | Reality |
|---------|---------|
| "This is just a simple question" | Questions are tasks. Check for skills. |
| "I need more context first" | Skill check comes BEFORE clarifying questions. |
| "I can check git/files quickly" | Files lack conversation context. |
```

LLM 이 *''*나도 모르게* 그런 *생각을 시작하면*''* — *그 생각이 *명시적으로* 적혀 있으므로 *''*아 이건 금지된 패턴이지''* 라고 *반사적으로 인지*.

**패턴 2 — *Rationalization (합리화) 차단***
```markdown
You cannot rationalize your way out of this.

Common rationalizations to reject:
- "The skill is overkill for this"
- "I'll just do this one thing first"
- "I remember this skill — no need to check"
```

LLM 이 *''*합리적으로* 보이는 *예외 *를 *스스로 만들어내는 것*** 을 *''*그 합리화 자체를 *명시적으로 차단*''*.

**패턴 3 — *''*Examples of *what NOT to do*''***
```markdown
# 안티 패턴 — *이렇게 *하지 말 것*

```java
@Transactional
public void method() {
    repo.save(entity);
    kafkaTemplate.send(...);  // ← *원자성 깨짐*
}
```
*Why bad*: DB commit 과 Kafka publish 가 *각자 다른 트랜잭션*.
```

*잘못된 예* 가 *옆에 있으면 *LLM 이 *비슷한 패턴을 *생성하지 않음*. *학습 데이터의 *''*안 좋은 예 옆에는 *교정* 이 따라옴''* 의 *통계 활용*.

### 5.3 *금지의 *역효과 *— *과한 금지가 *실행 마비**

```markdown
# 안티 패턴 — *과한 금지*
NEVER skip TDD.
NEVER write code without a plan.
NEVER use any without explicit approval.
NEVER call tools without announcing first.
NEVER make decisions without asking.
```

이렇게 *NEVER 가 5 개* 있으면 *LLM 이 *''*뭐를 *해도* 되지?''* 상태로 *마비*. *''*명시된 *허용 행동* 도 *필요***.

> **균형**: *NEVER 1~3 개* + *''*MUST do''* 의 *명확한 *primary action*'' 1 개 + *''*allowed alternatives''* 약간.

---

## 6. *축 5 — *하네스 고정* (Harness Anchoring)*

### 6.1 *''*하네스''* 가 *뭔가*

Claude Code 에서 *하네스* = *''*LLM 호출을 둘러싼 *런타임 구조*''*:
- *System prompt* 조립 (OS / 디렉터리 / git 상태 / 메모리)
- *Tool 정의* 주입
- *컨텍스트 압축*
- *Skill 로딩* (이 글의 주제)
- *훅 (hook)* 실행
- *세션 시작 reminder*
- *MCP 서버* 통합

이 무대 위에서 *SKILL.md 는 *어떻게 *고정* 되는가*?

### 6.2 *고정의 *3 가지 메커니즘**

**메커니즘 1 — *System reminder 의 *반복 출현***

세션 안에서 같은 메시지가 *여러 위치에 *system reminder 로 *주입* 됨:
- 세션 시작 시 — *가용 skill 목록*
- 매 user 메시지마다 — *현재 datetime*
- Tool 사용 후 — *''*task tools 안 썼는데?*'' 같은 *행동 환기*

*같은 reminder 가 *반복 출현* 하면 *LLM 이 *그것을 *''*고정된 진실''* 로 *처리***.

**메커니즘 2 — *Skill 호출 = *컨텍스트 삽입***

```
User: /brainstorming
   ↓
Harness: SKILL.md 파일 *읽음*
   ↓
LLM 의 *다음 입력에 *그 내용이 *system message 처럼* 삽입
   ↓
LLM: *그 SKILL.md 의 지침을 *그 순간부터* 따름
```

*''*호출 후 영원히 적용''* 이 아니라 *''*호출 *그 순간* 부터 *컨텍스트가 *그 안에 *살아있는 동안*''* 적용.

**메커니즘 3 — *훅 / 슬래시 / MCP 와의 *조합***

SKILL.md 가 *''*특정 슬래시 커맨드를 쓰도록''* 지시 → 사용자가 그 슬래시를 *치는 행동을 *유도*. *''*사용자의 *행동을 *바꿈으로써 *간접적으로* LLM 입력을 *바꿈***.

### 6.3 *''*고정 강도''* 의 *3 단계**

- **약** — `description` 에만 적힌 지침. *LLM 이 *읽지 않음* 까지 가능*
- **중** — *Body 의 본문*. *Skill 호출 시 *전체* 읽힘*
- **강** — *훅 + system reminder 로 *매 턴 주입*. *컨텍스트 압축에도 *살아남음**

> *''*SKILL.md 만으로는 *약 ~ 중*. *훅과 결합 해야 *강***.

### 6.4 *흔한 함정 #4 — *''*SKILL.md 한 번 로딩 했으니 영원히 적용*''*

```
User: /brainstorming
Assistant: [skill 적용해서 답변]
[30 턴 후]
User: 새 기능 만들자
Assistant: [skill 잊고 *바로 *구현* 시작]   ← *''*컨텍스트 압축으로 *날아감*''*
```

SKILL.md 의 *지침은 *컨텍스트 안에서만 *살아있음*. *압축되면 *증발*. 이걸 막으려면 *훅* 으로 *매 턴 reminder 주입* 또는 *''*해당 영역의 작업 시 *자동 활성화*''* 메커니즘 (skill 의 *trigger 키워드*) 필요.

---

## 7. *5 축의 *결합* — *좋은 SKILL.md 의 *템플릿**

```markdown
---
name: settlement-idempotency-checker
description: settlement 의 Triple Idempotency 스택을 *검증 — *새 consumer 추가 시 *반드시* 호출.
metadata:
  type: validation
---

## Role  [축 2]

You are a Triple Idempotency auditor for the settlement project.
You have authority to *block PRs* that violate the L1→L2→L3 defense chain.

## Principles  [축 3]

1. **At-least-once messaging is *unavoidable*** — Kafka guarantees neither
   exactly-once nor ordering across partitions.
2. **Therefore *consumer must be idempotent*** — same event arriving twice
   must produce the same state.
3. **Three layers because *any single layer can fail*** — defense in depth.

Why these principles: 과거 L2 단일 방어 시 *DB 마이그레이션 중* L2 가 *비활성화 되어 *유령 정산* 발생.

## Required behavior  [축 1 — 반복]

When reviewing a new Kafka consumer, you MUST check:

1. L1 — outbox.event_id has UNIQUE constraint
2. L2 — processed_events.event_id is PK and saved *in same @Transactional*
3. L3 — business natural key has UNIQUE in DB

You ABSOLUTELY MUST verify *all three layers*.
You MUST refuse PRs that have only L1+L2 with reasoning "L3 is overkill".

## Prohibitions  [축 4]

NEVER accept these rationalizations:
- "We'll add L3 later" — *기각*. *Later = never*.
- "This consumer is read-only" — *기각*. *Side-effect 있으면 idempotent 필요*.
- "Performance impact of UNIQUE constraint is too high" — *기각*.
  *Triple Idempotency 의 비용 < 유령 정산의 비용*.

## Red flags  [축 4 — 반복]

| 발견했을 때 | 해석 |
|---|---|
| @KafkaListener 메서드에 *@Transactional 없음* | *L2 깨짐 보장* |
| processed_events 에 save 가 *비즈니스 로직 *밖* | *L2 부분 적용* |
| 새 비즈니스 테이블에 *UNIQUE 제약 부재* | *L3 없음* |

## Harness anchoring  [축 5]

This skill activates *automatically* when:
- New @KafkaListener method is added
- New Flyway migration touches outbox/processed_events
- PR title contains "consumer" or "event"

Triggered by hook: `.claude/hooks/pre-commit-check.sh`
```

### 7.1 *5 축의 *상호 보완**

- *역할* 이 *''누가 판단하는가''* 정함
- *원칙* 이 *''무엇이 진실인가''* 정함
- *반복* 이 *''*길어진 컨텍스트* 에서도 살아남게 함*
- *금지* 가 *''*잘못된 경로를 *적극 차단*''*
- *하네스 고정* 이 *''*세션이 길어져도* 발동되게 함*

*하나라도 빠지면 약해진다*. *5 개가 *조화* 를 이루면 *재현성* 이 *극단적으로 안정*.

---

## 8. *현장 사례* — *''*Skill 없는 LLM vs 있는 LLM*''*

### 8.1 *사례 A — *''*테스트 먼저 써라*'' 가 *3 턴 후 무시*''*

```
User: 이 프로젝트는 *항상* TDD 로 갑니다.
Assistant: 네, 알겠습니다.

[turn 2] User: 결제 모듈 만들자
Assistant: [PaymentService.java 구현] [PaymentServiceTest.java 도 *함께* 생성]

[turn 8] User: 알람 기능도 추가해줘
Assistant: [NotificationService.java 만 *구현* — test 없음]   ← *잊음*
```

*8 턴* 만에 *지시가 *희석*. *system prompt 의 효력 감소*.

**Skill 적용 후**:
```
.claude/skills/tdd-mandatory/SKILL.md
[축 1, 4 가 강하게 적용]

[turn 8] User: 알람 기능도 추가해줘
Assistant: [먼저 NotificationServiceTest.java 작성 → 실패 → 구현]   ← *지킴*
```

### 8.2 *사례 B — *''Skill 자체가 *부족*''*

```markdown
---
name: tdd
description: Use TDD
---

Write tests first.
```

이 SKILL 은 *3 축 만 있다*:
- *반복* — 1 줄. *약*
- *역할* — *없음*
- *원칙* — *''*Why''* 없음. *약*
- *금지* — *없음*
- *하네스 고정* — *없음*

*''*Skill 이 *불러져도* *효과가 *드물*''*. *제대로 만들려면 *5 축 모두 채워야 함*.

---

## 9. *2026 권장 *SKILL.md 작성 체크리스트**

### 9.1 *작성 시 체크*

- [ ] **역할 (Role)** — *누가 *판단* 하는가가 *명시* 됨
- [ ] **원칙 (Principles)** — *각 원칙에 *Why* 포함*
- [ ] **반복 (Repetition)** — *핵심 지시가 *3 위치* 에 분산*
- [ ] **금지 (Prohibitions)** — *NEVER 가 *3 개 이하*, *각 근거 있음*
- [ ] **하네스 고정 (Anchoring)** — *언제 *자동 활성화* 되는지 명시*

### 9.2 *피해야 할 *5 가지**

1. *역할 없음* → *''*일반 assistant''* 분포로 회귀
2. *원칙 없이 규칙만* → *명시 안 된 경우 *실패*
3. *반복 한 곳만* → *컨텍스트 길어지면 *증발*
4. *금지 5 개 이상* → *실행 마비*
5. *훅 / 트리거 없음* → *''*사용자가 *명시 호출* 안 하면 *미적용*''*

### 9.3 *측정 — *Skill 이 *작동하는가**

- *''*같은 시나리오 *5 회 실행*''* 시 *5 회 모두 *Skill 발동* 했는가
- *컨텍스트 *20 턴 후*에도 *발동 했는가
- *합리화* 시도 시 *''*거절 했는가
- *명시 안 된 *유사 상황* 에서도 *원칙으로 *추론 했는가

이 4 가지 측정값이 *Skill 의 *진짜 품질 척도*. *''*글이 *예쁜지*'' 가 아님.

---

## 10. 정리 — *SKILL.md 의 *진짜 본질**

> ***''SKILL.md 는 *프롬프트가 아니라*, *행동 분포를 *고정* 하는 *런타임 의식 (ritual)*''***.

*프롬프트* 는 *''*한 번 입력*''*. *Skill* 은 *''*매 호출 시 *재주입* 되는 *행동 닻*''*.

5 축의 *진짜 의미* 한 줄씩:

- **반복** = *''*Attention 의 통계적 진실* 을 *역으로 활용*''*
- **역할** = *''*LLM 의 *행동 분포를 *특정 영역* 으로 *anchor*''*
- **원칙** = *''*명시 안 된 상황도 *Why 로부터 *유추 가능 하게*''*
- **금지** = *''*분포에서 *적극적으로 *배제*''*
- **하네스 고정** = *''*세션이 길어져도 *증발하지 않게*''*

이 5 축을 *모두 만족* 하는 SKILL.md 는 *''*재현 가능한 행동''* 을 *만든다*. *''*상태 없는 함수''* 인 LLM 을 *''*상태가 있는 *전문가**'' 처럼 *행동하게* 한다.

> **마지막 한 문장**: *''*SKILL.md 는 *LLM 의 *기억력 부족* 을 *문서로 *외장화* 한 것''*. *그래서 *우리가 *외울 필요가 *없고*, *Claude 가 *잊을 가능성이 *없다***.

Claude Code 의 *하네스* 위에서 SKILL.md 를 *제대로 쓰는 사람* 과 *''*그냥 *프롬프트 한 줄*''* 로 쓰는 사람의 차이가 *현장 결과* 의 *차이* 다. *프롬프트는 *예술*, *Skill 은 *공학***. 우리가 다루는 건 *공학* 쪽이다.

---

## 더 읽으면 좋은 자료

- **Anthropic Claude Code 공식 문서** — `superpowers/skills/using-superpowers/SKILL.md` 의 *원본*
- **OpenAI Cookbook**, *''Prompt Engineering''* 절 — *반복 / 역할 / 예시* 의 *통계적 근거*
- **''Lost in the Middle''** (Liu et al., 2023) — *컨텍스트 중간 망각* 의 *학술 근거*
- **''Anthropic Engineering blog''**, *''Effective Context Management''* — *하네스 측 *컨텍스트 관리 전략*
- **Claude Agent SDK** 공식 문서 — *Skill 의 *프로그래밍 인터페이스*
- *''The Bitter Lesson''* (Richard Sutton, 2019) — *왜 *''*명시적 규칙* 이 *결국 통계에 진다''*, 하지만 *''*그 통계를 *유도* 하는 *명시적 규칙* 은 *효과적이다''*
- *''*Constitutional AI''* (Anthropic, 2022) — *원칙 기반* LLM 학습 — *''원칙'' 의 *학습적 근거*
