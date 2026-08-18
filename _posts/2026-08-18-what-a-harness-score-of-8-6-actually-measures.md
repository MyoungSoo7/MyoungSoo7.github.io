---
layout: post
title: "평균 8.6점짜리 하네스는 무엇으로 만들어지는가 — 검증 9.5, 상태 8.0 의 편차를 읽는다"
date: 2026-08-18 21:15:00 +0900
categories: [engineering, ai]
tags:
  [
    ai-harness,
    claude-code,
    guardrails,
    ci,
    static-analysis,
    kafka,
    spring,
    msa,
    settlement,
  ]
---

정산 리포(`settlement`, 18 마이크로서비스)의 **개발 하네스**를 4개 축으로 채점한 표를 받았다.

![정산 리포 하네스 4축 채점 — 검증 9.5 / 권한 8.5 / 상태 8.0 / 재현 8.5](/assets/images/settlement-harness-score-4axes.jpg)

$$\text{평균} = \frac{9.5 + 8.5 + 8.0 + 8.5}{4} = 8.625$$

이 글은 점수 자랑이 아니다. **왜 축마다 점수가 다른지**를 리포 안에서 근거를 찾아 설명하는 글이다. 결론부터 쓰면 — 이 편차는 하네스의 품질 차이가 아니라 **하네스가 만들어진 방식**의 흔적이다.

> **표의 출처에 대해**: 이 4축 루브릭과 점수는 내가 매긴 것이 아니라 외부에서 받은 채점 결과다. 채점자·기준의 상세는 표에 없다. 그래서 이 글에서 검증 가능한 것은 점수 자체가 아니라 **"저 한 줄 평이 리포의 어떤 사실을 가리키는가"** 뿐이다. 아래 모든 수치는 `settlement` 리포 `origin/develop` `bfa0738c` 기준이며, 세는 명령을 함께 적는다.

---

## 하네스가 뭔지부터

여기서 "하네스"는 LLM 에이전트가 이 저장소에서 일할 때 딛는 바닥 전체를 말한다. 프롬프트가 아니라 **배선**이다. 리포의 `HARNESS.md`(345줄)는 그 구성을 5계층으로 정의한다 — 판단을 위임하는 서브에이전트, 온디맨드 규칙 스킬, 워크플로 커맨드, 기계 차단 게이트, 관측 텔레메트리. 원칙은 한 문장이다.

> 결정적인 것은 훅·게이트로 강제, 판단이 필요한 것은 에이전트로 위임, 작성과 검증은 분리.
> — `HARNESS.md`

중요한 건 두 축의 분리다. `.claude/`(모델에게 주는 지식)와 `scripts/harness/`(기계가 강제하는 실행 코어)가 나뉘어 있고, 후자는 저장소에 추적되어 **플러그인·MCP 없이도 CI·새 클론·다른 CLI 에서 그대로 돈다.** 이 분리가 네 축 점수 전부에 영향을 준다.

```bash
# 규모 (직접 세는 명령)
git ls-files 'scripts/harness/test/*.test.mjs' | wc -l          # 18
git ls-files '.claude' | wc -l                                  # 84
grep -oE "id: '[A-Z][A-Z0-9-]+'" scripts/harness/guard.mjs | sort -u | wc -l   # 18
```

---

## 검증 9.5 — "사고 기반 게이트 14종 + 가짜 GREEN 방어 내장"

가장 높은 축이다. 이유는 게이트의 **출처**에 있다. 이 리포의 게이트는 베스트 프랙티스 목록에서 온 것이 아니라, 대부분 **실제로 한 번 터진 사건**에서 왔다. `HARNESS.md` 의 게이트 설명은 예외 없이 "무엇이 조용히 깨지는가"로 시작한다.

몇 개만 원문 근거와 함께 본다.

**트랜잭션 롤백 게이트** — `@Transactional` 메서드에서 체크 예외가 나가면 스프링은 **커밋한다.** 이건 버그가 아니라 문서화된 기본값이다. Spring 공식 문서: "기본 설정에서 트랜잭션 인프라는 런타임·언체크 예외에 대해서만 롤백을 표시한다… 체크 예외는 기본 설정에서 롤백을 유발하지 않는다"[^spring-rollback]. 일반 웹앱에선 감수할 만하지만 원장·정산에서는 **반쪽 커밋**이 된다. 그래서 게이트가 `@Transactional` + 체크 예외 조합에 `rollbackFor` 를 강제한다.

**AOP 프록시 게이트** — 같은 빈 안에서 `this.method()` 로 부가기능 메서드를 부르면 프록시를 안 거친다. 역시 문서화된 동작이다: "self invocation 은 해당 메서드 호출에 걸린 어드바이스가 실행될 기회를 주지 않는다"[^spring-proxy]. 결과는 `@Retry`·`@CircuitBreaker`·`@Cacheable`·`@PreAuthorize` 가 **조용히 무력화**되는 것 — 컴파일도 테스트도 통과하고 운영에서만 안 걸린다. ArchUnit 1.3 이 Java 25 바이트코드를 못 읽어서 이 게이트는 소스 스캔 계층에 있다.

**KAFKA-GROUP-OWNER** — 두 서비스가 같은 컨슈머 `group-id` 를 쓰면 카프카는 한 그룹으로 보고 파티션을 나눠 준다. 공식 문서 그대로다: "파티션들이 그룹의 모든 멤버 사이에 균형 배분되어 **각 파티션은 그룹 내 정확히 한 컨슈머에게 할당된다**"[^kafka-consumer]. 즉 한쪽이 가져간 메시지는 다른 쪽에 오지 않고 오프셋까지 공유된다. 예외도 로그도 없이 유실이다. 2026-08-14 실사건 — `order-service` 가 모놀리스 분리 잔재로 `lemuel-settlement` 그룹을 들고 있었다.

**KAFKA-DLQ** — `@KafkaListener` 가 있는 모듈에 DLT 배선이 안 닿으면 스프링 카프카 기본값으로 떨어진다. `DefaultErrorHandler` 의 기본은 `FixedBackOff(0L, 9)` 이고, 10회 실패 후 기본 recoverer 는 **레코드를 ERROR 로그만 찍고 넘어간다**[^spring-kafka]. 조용한 유실이다.

**Kafka 토픽 카탈로그 게이트** — 막는 건 "파티션 수가 코드 밖에서 정해지는 상태"다. 메시지 키가 outbox `aggregateId` 라서 파티션 수를 바꾸면 키 재해시가 일어난다. 카프카는 "파티션 내부에서만 전체 순서를 보장"하고 파티션 배정은 키 해시로 결정되므로[^kafka-order][^kafka-protocol], 파티션 수 변경은 **이미 쌓인 메시지의 순서 보장까지 소급해서 붕괴**시킨다. 되돌릴 수 없다.

**메뉴↔라우트 / 백엔드 표면↔화면 게이트** — 이 두 개가 특히 이 리포답다. 메뉴만 있고 라우트가 없으면 죽은 링크, 라우트만 있고 메뉴가 없으면 유령 화면인데 **컴파일러도 런타임도 알려주지 않는다.** 반대편도 잡는다 — 실제로 card Phase 2·insurance·deposit·organization 이 REST 와 게이트웨이 라우팅을 전부 갖춘 채 화면 0 으로 방치돼 있었다.

**프론트 렌더 경합 게이트** — `waitFor(API 가 불렸는지)` 로 기다린 뒤 곧바로 `getBy*` 로 데이터 의존 엘리먼트를 집는 형태를 막는다. 호출 시점과 렌더 반영 시점 사이에 상태 갱신 한 틱이 있어서 **로컬은 늘 통과하고 CI 러너에서만 랜덤하게 실패**한다. 2026-08-13 하루에 두 파일이 같은 이유로 필수 체크를 깼다. 린트로는 안 잡힌다 — `testing-library/prefer-find-by` 는 `waitFor(() => getBy...)` 형태만 보고 이 사각지대는 대상이 아니다.

### 0.5 를 깎은 것 — "잔여는 운용 지식 의존"

이 축에서 인상적인 건 게이트 목록이 아니라 **가짜 GREEN 방어가 내장돼 있다는 점**이다. 게이트가 늘면 다음 실패 모드는 "게이트가 초록인데 사실이 아닌 상태"로 옮겨간다. 리포는 이걸 세 군데서 막는다.

- `report-freshness.mjs` — 테스트/JaCoCo XML 이 그 모듈 `src/` 최신 mtime 보다 오래되면 `STALE`(exit 1). 직전 빌드 산출물을 이번 변경의 증거로 인용하는 것을 **종료 코드로** 차단한다. 리포트가 아예 없으면 `MISSING`.
- `api-screen-gate` 의 `PENDING_BUDGET` 래칫 — 인정된 화면 부채는 **내려가기만** 한다. 줄었는데 예산을 안 내려도 FAIL 이라 목록이 늘 정확하다. 추출 정규식이 깨져 전부 통과하는 가짜 GREEN 은 스캔 하한선으로 막는다.
- 부팅 IT — 실 PostgreSQL 에 Flyway 체인을 적용하고 `ddl-auto: validate` 로 띄우는 것 자체가 어서션이다. 없으면 마이그레이션과 엔티티가 어긋나도 단위 테스트는 전부 초록이다.

그런데도 만점이 아닌 이유는 리포 자신이 적어 뒀다. `report-freshness` 의 개선 로그에는 `verified_at: 미검증`, 한계로 "mtime 근사, Docker 다운 skip 축은 별개 문제로 남는다"가 명시돼 있다. **통합테스트가 Docker 부재로 조용히 스킵되는 축은 아직 기계화되지 않았다.** 그건 여전히 사람이 `ignored=0` 을 눈으로 확인해야 하는 운용 지식이다. 표의 "잔여는 운용 지식 의존"이 정확히 이걸 가리킨다.

### 덤 — 문서가 이미 하나 뒤처져 있다

"게이트 14종"을 검증하려고 세어 봤다. `HARNESS.md` 의 차단성 기계 게이트는 정확히 14개다(ArchUnit · JaCoCo · 이벤트 계약 · 돈 경로 가드 · OO 구조 · AOP 프록시 · TX 롤백 · Kafka 토픽 · Kafka 발행부 · SSE nginx · 스케줄러 락 · 메뉴↔라우트 · API↔화면 · 렌더 경합). 표의 숫자와 맞는다.

그런데 코드에는 **15번째가 있다.**

```bash
git ls-files 'scripts/harness/test/node-version-gate.test.mjs'   # 존재
git show origin/develop:HARNESS.md | grep -ci 'node-version\|nvmrc'   # 0
```

`node-version-gate.test.mjs` 는 `.nvmrc` 를 단일 출처로 삼아 워크플로와 `frontend/Dockerfile` 의 Node 메이저 일치를 강제한다. 도입 배경도 적혀 있다 — Dependabot 이 `frontend/Dockerfile` 의 `FROM node` 를 20→26 으로 올렸는데 워크플로의 `node-version` 리터럴은 어느 생태계도 추적하지 않아 20 에 남았고, **6 메이저가 벌어진 채로 머지됐는데 아무 게이트도 빨개지지 않았다.** 실재하고 CI 에서 도는 게이트인데 `HARNESS.md` 에는 한 글자도 없다.

이건 이 하네스를 깎아내리는 발견이 아니라 이 하네스의 논지를 증명하는 발견이다. **기계화되지 않은 문서는 반드시 드리프트한다.** 실제로 이 리포는 그래서 문서 사실 게이트 5종(이벤트 토픽 수·구현 상태 역전·소비처 배선·Spring Boot 버전·서비스 수)을 `harness-audit.mjs` 에 넣어 뒀다 — 자신이 3주간 "14 마이크로서비스"로 남아 같은 문서 안의 "자바 16서비스"와 모순됐던 사고 이후에. 게이트 목록 자체는 아직 그 5종에 안 들어가 있을 뿐이다.

---

## 권한 8.5 — "3중 강제·예외 규율 우수, Bash 경유 편집의 실시간 공백"

권한 축은 "에이전트가 무엇을 못 하게 막는가"다.

### 왜 높은가 — 같은 규칙을 세 시점에서

`guard.mjs` 하나가 세 시점에 붙어 있다.

| 시점           | 트리거                              | 실패 시                            |
| -------------- | ----------------------------------- | ---------------------------------- |
| 파일 편집 직전 | PreToolUse `Write\|Edit\|MultiEdit` | **exit 2 = 편집 차단**             |
| `git commit`   | `core.hooksPath` pre-commit         | **커밋 거부** (`--no-verify` 금지) |
| PR·push        | `harness-guard.yml`                 | **CI 실패**                        |

핵심은 이게 **중복이 아니라 서로의 우회를 막는 구성**이라는 점이다. 로컬 훅을 안 깔면 커밋 가드만 비고 실시간 훅과 CI 는 산다. `--no-verify` 로 커밋 훅을 건너뛰면 CI 가 같은 규칙을 다시 돌린다. 게다가 삭제 축은 따로 다룬다 — 스테이징·CI 파일 목록이 `--diff-filter=ACMR` 로 삭제(D)를 빼고 오기 때문에 내용 스캔으로는 "지워버리기"를 못 잡는다. 그래서 `--deleted-list` 가 삭제 목록을 별도로 받아 `.claude/`·`scripts/harness/` 경로를 지킨다. **하네스가 자기 자신의 삭제를 막는다.**

예외 규율도 느슨하지 않다. 규칙 면제 주석은 `reason`·`issue`·`owner`·**미래 `expires`** 네 필드가 다 유효해야 하고, 아니면 `INVALID-ALLOWANCE` 위반이 된다. 무기한 면제가 문법적으로 불가능하다.

```javascript
violations.push({
  file: f,
  line: i + 1,
  id: "INVALID-ALLOWANCE",
  msg: "harness-guard 예외는 유효한 reason, issue, owner, 미래 expires가 필요함",
});
```

### 왜 1.5 를 깎았나 — 운반 수단은 fail-open 이다

파일 편집은 Write/Edit 도구를 거치지만, `sed -i`·`perl -i`·리다이렉트·`tee` 로도 소스를 고칠 수 있다. 그래서 Bash 계층(`--hook-bash`)에 `CMD-EDIT-BYPASS`·`CMD-NO-VERIFY`·`CMD-PROD-DB-WRITE`·`CMD-EVENT-PRODUCE` 4종이 있다. 그런데 이 계층은 **의도적으로 fail-open** 이다. 주석에 이유가 적혀 있다.

```javascript
// 파일 훅(--hook)과 달리 fail-open 이다: 여기는 내용 불변식이 아니라 운반 수단 차단이라,
// 입력 파싱 실패에 fail-closed 하면 하네스 결함 하나가 모든 Bash 실행을 멈춘다(블래스트 반경).
// 우회 시도는 커밋(--staged)·CI(--list) 계층이 내용 기준으로 재차단한다.
```

이건 잘 내린 트레이드오프지만 **트레이드오프인 건 맞다.** 명령 문자열 정규식으로 막는 계층이라 실시간 창에는 구멍이 남고(커밋 전까지는 통과), 반대로 정상 명령을 오차단하면 마찰이 된다. 표의 "실시간 공백·오차단 마찰"이 이 둘을 한 줄로 압축한 것이다. 이 축이 9점대로 못 가는 건 도구를 덜 만들어서가 아니라 **`fail-open`·`fail-closed` 를 동시에 만족시킬 수 없는 구조** 때문이다.

---

## 상태 8.0 — 가장 낮은 축, 그리고 가장 정직한 축

"닫힌 피드백 루프·단일 진실 원칙, 세션 상태 GC·머신 간 관측 단절."

### 잘한 두 가지

**닫힌 피드백 루프.** 대부분의 하네스는 관측을 적재하고 끝난다 — 사람이 리포트를 돌려야 보이고, 아무도 안 돌린다. 여기는 `SessionStart` 훅이 `telemetry-report.mjs --hook` 으로 최근 차단·라우터 순응률·가드 카나리아 생존을 **세션마다 자동 주입**한다. 알릴 게 없으면 침묵한다. 관측이 사람을 거치지 않고 에이전트에게 도달한다.

**단일 진실 원칙.** 휘발성 수치를 모아 둔 정본 문서를 아예 폐지했다(2026-08-07 `STATUS.md`). 이유가 실전적이다 — 병행 세션이 동시에 갱신하면서 값이 늘 어긋났다. 대신 문서에는 값과 **재현 git 명령을 병기**한다. 그러면 수치가 falsifiable 해져 조용한 드리프트가 불가능해진다. 집계는 반드시 `git ls-files` 기준이다. `find` 는 `build/` 사본과 `.claude/worktrees/` 에이전트 사본을 이중 집계해서 과거 "마이그레이션 224" 유령 수치를 만들었다.

### 왜 8.0 인가

두 구멍 다 **상태의 수명 주기** 문제다.

첫째, 세션 상태 GC 가 기회적이다. 라우터는 세션당 스킬별 1회 주입을 위해 `.claude/harness/state/skill-router-*.json` 을 남긴다. 정리 로직은 있다.

```javascript
export const STATE_RETENTION_DAYS = 14;
```

하지만 이건 **라우터가 호출될 때만** 돈다(`pruneStaleState`). 라우터 불변식이 "어떤 실패도 exit 0"이라 정리 실패도 조용히 넘어간다. 즉 편집이 없는 기간에는 아무도 치우지 않는다. 도입 동기 자체가 "세션당 상태 파일 1개가 영구 누적(실측 ~70개)"이었다는 점에서, 이건 해결이 아니라 **완화**다.

둘째, 머신 경계. 텔레메트리는 로컬 `.claude/harness/logs/*.jsonl` 에 쌓이고 gitignore 라 커밋되지 않는다. CI 러너의 이력은 아티팩트(30일)로만 남아 로컬 리포트와 단절돼 있었다. 2026-08-15 에 `telemetry-ci-pull.mjs` + `--merge` 로 합산 경로가 생겼지만, 수집은 best-effort 이고 **누가 언제 당기느냐에 의존한다.** 관측 도구가 게이트를 막지 않는다는 설계 원칙의 당연한 대가다.

정리하면 이 축의 감점은 **기능 부재가 아니라 "상태는 누가 치우고 어디서 합쳐지는가"가 아직 기계에 완전히 넘어가지 않았다**는 것이다. 게이트는 이벤트에 반응해서 만들기 쉽지만, 상태 관리는 반응할 이벤트가 없다. 그게 이 축이 제일 낮은 구조적 이유다.

---

## 재현 8.5 — "0 의존 코어·manifest·falsifiable 문서"

재현 축은 "새 클론에서도 같은 판정이 나오는가"다.

**0 의존 코어.** `scripts/harness/` 12개 파일은 순수 Node 다. npm 설치도, MCP 서버도, 플러그인도 필요 없다. 이게 왜 중요하냐면 — 이 하네스는 이전에 한 번 이걸로 데였다. Bash 명령 검사를 담당하던 `check-command` 는 `settlement-copilot` **플러그인 소유**였고, 플러그인이 없는 환경에는 그 검사가 아예 존재하지 않았다. "플러그인 독립" 전제의 구멍이었고, 2026-08-15 에 저장소 네이티브 `COMMAND_RULES` 로 다시 만들었다.

같은 사고를 다시 안 내려고 MCP 능력마다 **폴백을 명시**한다. `integrity_check` → `/admin/integrity` API, `trial_balance` → `/api/account/trial-balance`, 하네스 정합 → `harness-audit.mjs`(정적, 0 의존). 폴백이 불가능한 것(`projection_status`·`outbox_status` 같은 라이브 컨슈머 lag)은 **"런타임 전용 — 폴백 없음"이라고 표에 적어 둔다.** 조용한 "MCP 단독"을 금지하는 규약이다.

**manifest + 추적 검증.** `manifest.json` 이 필수 산출물을 정의하고 CI 가 `git ls-files` 로 실존·추적 여부를 확인한다. 목표 1번이 "fresh clone 에 필수 하네스 산출물이 모두 포함된다"이고, Claude/Codex 양쪽 정본 쌍은 `criticalContractPairs` 가 드리프트를 차단한다. CI 마지막 단계는 `git diff --exit-code` — **워킹트리가 깨끗해야 통과**한다. 게이트가 자기 실행으로 파일을 바꾸면 그것도 실패다.

**falsifiable 문서.** 위에서 본 "수치에 재현 명령 병기" 규약이 재현성 축에도 그대로 기여한다.

### 왜 1.5 를 깎았나

두 가지다. 하나는 **Windows 환경차** — DoD 체크리스트에 "PowerShell 은 `git commit -F <file>`"처럼 플랫폼 분기가 산문으로 남아 있다. 기계가 아니라 사람이 기억해야 하는 조건이다.

다른 하나가 더 근본적이다. **런타임 산출물이 gitignore 라서 정보가 클론을 못 넘는다.** `.claude/harness/logs/`(텔레메트리)와 `state/`(라우터 세션)는 저장소에 없다. 그래서 "게이트 규칙 A 는 지난 3개월간 0회 발화했다 = 죽은 규칙 후보"라는 판정은 **그 머신에서만** 가능하다. 새 클론은 규칙 자체는 100% 재현하지만 규칙의 **효과 이력**은 0에서 시작한다. 커밋하면 병행 세션 충돌과 노이즈가 생기니 이것도 트레이드오프지만, 재현성 축에서는 감점 요인이 맞다.

---

## 그래서 이 편차가 말하는 것

네 축을 나란히 놓으면 패턴이 하나 보인다.

| 축   | 점수 | 감점의 성격                                     |
| ---- | ---- | ----------------------------------------------- |
| 검증 | 9.5  | 아직 기계화 못 한 잔여(Docker skip)             |
| 권한 | 8.5  | 구조적 트레이드오프(fail-open vs 블래스트 반경) |
| 재현 | 8.5  | 구조적 트레이드오프(gitignore vs 노이즈)        |
| 상태 | 8.0  | 반응할 이벤트가 없어서 안 만들어진 부분         |

**검증 축이 가장 높은 건 사고가 그 축의 백로그를 대신 써 주기 때문이다.** 카프카 그룹 충돌, 워크플로 한 줄 주석, Dependabot 의 Node 26, CI 에서만 깨지는 렌더 경합 — 전부 한 번 터졌고, 터진 다음 날 게이트가 생겼다. `HARNESS-IMPROVEMENT-LOG.md` 에 `status`·`predicted_effect`·`verified_at` 을 남기는 규약까지 있다. 예측이 빗나가면 `reverted` 로 남기고 되돌린다.

**상태 축이 가장 낮은 건 상태 문제가 시체를 남기지 않기 때문이다.** 상태 파일 70개가 쌓여도 아무것도 빨개지지 않는다. 텔레메트리가 머신 사이에서 끊겨 있어도 빌드는 초록이다. 사고가 안 나면 백로그가 안 생기고, 백로그가 없으면 게이트도 안 생긴다. 이 축을 올리려면 **사건 없이 스스로 만들어야** 하고, 그건 훨씬 어렵다.

그러니 읽어야 할 숫자는 평균 8.625 가 아니다. **1.5 점의 편차**다.

## 이 점수가 말하지 않는 것

마지막으로 한계를 분명히 해 둔다.

- **루브릭 출처가 표에 없다.** 4축의 정의·가중치·만점 기준을 확인할 수 없으므로, 다른 리포와 이 점수를 비교하는 건 의미가 없다. 축별 한 줄 평이 리포의 실재하는 사실을 가리키는지만 검증 가능하고, 이 글이 한 게 그것이다.
- **게이트 수는 안전의 척도가 아니다.** 14 든 15 든, 각 게이트가 실제로 발화했는지는 텔레메트리가 답할 문제다. 그리고 그 텔레메트리는 위에서 봤듯 머신 로컬이다.
- **여기서 다룬 건 하네스지 프로덕션이 아니다.** 게이트가 잡는 건 "코드가 이런 모양이 되는 것"이고, 그게 곧 "정산이 맞다"는 뜻은 아니다. 그건 JaCoCo·통합테스트·대사 쪽 이야기다.

---

## References

**리포 1차 자료** — `MyoungSoo7/settlement`, `origin/develop` `bfa0738c` (2026-08-18 확인). 인용한 파일: `HARNESS.md`, `scripts/harness/guard.mjs`, `scripts/harness/skill-router.mjs`, `scripts/harness/test/node-version-gate.test.mjs`, `scripts/harness/test/api-screen-gate.test.mjs`, `.github/workflows/harness-guard.yml`, `docs/plan/HARNESS-IMPROVEMENT-LOG.md`, `docs/plan/superpowers/specs/2026-07-13-reproducible-harness-p0-design.md`. 저장소는 공개다 — <https://github.com/MyoungSoo7/settlement> 에서 인용한 파일을 직접 열어 확인할 수 있다.

[^spring-rollback]: Spring Framework Reference, _Rolling Back a Declarative Transaction_. "In its default configuration, the Spring Framework's transaction infrastructure code marks a transaction for rollback only in the case of runtime, unchecked exceptions… Checked exceptions that are thrown from a transactional method do not result in a rollback in the default configuration." <https://docs.spring.io/spring-framework/reference/data-access/transaction/declarative/rolling-back.html>

[^spring-proxy]: Spring Framework Reference, _Proxying Mechanisms_. "self invocation is not going to result in the advice associated with a method invocation getting a chance to run. In other words, self invocation via an explicit or implicit `this` reference will bypass the advice." <https://docs.spring.io/spring-framework/reference/core/aop/proxying.html>

[^kafka-consumer]: Apache Kafka, `KafkaConsumer` javadoc. "balancing the partitions between all members in the consumer group so that each partition is assigned to exactly one consumer in the group." <https://kafka.apache.org/43/javadoc/org/apache/kafka/clients/consumer/KafkaConsumer.html>

[^spring-kafka]: Spring for Apache Kafka Reference, _Handling Exceptions_ / `DefaultErrorHandler` javadoc. "By default, after ten failures, the failed record is logged (at the ERROR level)" · "the default configuration (`FixedBackOff(0L, 9)`)". <https://docs.spring.io/spring-kafka/reference/kafka/annotation-error-handling.html>

[^kafka-order]: Apache Kafka, _Introduction_ (버전별 아카이브 문서 페이지 — 현행 문서는 같은 내용을 JS 로 로드해 인용 가능한 정적 URL 이 없다). "Kafka only provides a total order over messages within a partition, not between different partitions in a topic." <https://kafka.apache.org/081/getting-started/introduction/>

[^kafka-protocol]: Apache Kafka, _Protocol / Design_. "Semantic partitioning means using some key in the message to assign messages to partitions… the client can take a key associated with the message and use some hash of this key to choose the partition." <https://kafka.apache.org/43/design/protocol/>
