---
layout: post
title: "안전 가이드라인이 *문서로만* 있을 때 — docs/safety-guidelines.md 와 코드 정렬 4 PR"
date: 2026-05-22 23:55:00 +0900
categories: [safety, ai, architecture]
tags: [autonomous-coding, safety, privacy, llm-guardrails, suicide-prevention, next-js, spring-boot, fastapi]
---

전날 (2026-05-21) *lemuel-xr* 의 positioning 을 *임상 자문 거버넌스* 에서 *자살예방 영적단련 교육 콘텐츠* 로 전환했다. 그 PR 에서 `docs/safety-guidelines.md` 를 작성하면서 "자문가 *필수 검증* 은 없지만 *제작자 자기 책임* 으로 8가지 안전 룰을 지킨다" 고 *문서로 약속* 했다. 그 다음 날 밤, 사용자가 *"알아서 다해"* 라는 단 한 줄을 보낸다.

그 한 줄의 시간 안에 그 8개 룰 중 **§1·§2·§3·§4 — 코드형 룰 전체** 를 코드로 옮긴 4 PR 의 기록.

> ⚠️ 보안 — 도메인 / 노드명 / 토큰 redacted. 구조만 공유.

---

## TL;DR — 4 PR 표

| # | PR | 안전 룰 | 격차 |
|---|---|---|---|
| 1 | `feat(safety): 1393 위기자원 footer 영구 노출` | §1 — 모든 화면에 위기자원 footer | home page 에 *한 줄 텍스트* 만 있고, 나머지 모든 페이지 (`/joseph`, `/values`, `/values/edit` 등) 에서는 *부재* |
| 2 | `feat(values): /values 페이지 — 7가치 빌더 + 실천 기록` | (§N/A, 일반 누락) | Backend `ValuesController` + `UserValueProfile` / `UserValuePractice` 도메인이 *UI 없이* 떠있어 새 positioning 의 핵심 (AR 일상 습관) 이 *사용자에게 안 보였다* |
| 3 | `fix(privacy): emotion_logs.raw_text 영속화 제거` | §3 — PHI 비수집 | DB `emotion_logs.raw_text` 컬럼이 *사용자 자유 텍스트를 영구 저장* 가능 상태였고 실제로 `setRawText(text)` 호출 중 |
| 4 | `feat(safety): LLM 출력 사후 트리거 필터` | §4 — LLM 가드레일 | system prompt (§4a) 는 있었지만 *사후 정규식 필터* (§4b) 가 없어 LLM 이 system prompt 무시 시 trigger 표현 그대로 사용자 노출 |

각 PR 의 공통 패턴: *문서로 약속한 안전 룰이 코드의 어디에 *없는지* 를 찾고, 그 격차를 닫는다.*

---

## 0. 배경 — 왜 *문서로만* 있었나

전날 (2026-05-21 → 22 새벽) 한 commit 메시지로 끝나는 큰 전환이 있었다:

```
commit d30d2c7
feat: 자문 거버넌스 도메인 전면 폐기 + 자살예방 positioning 재정의

18 files changed, +219 / -1744
```

이 PR 에서 *임상 검토·신학 자문 거버넌스 도메인* (theology_reviews, clinical_reviews, content_versions, reviewer_profiles, ReviewController 등) 을 *통째로* drop 했다. -1744 줄. 그리고 그 자리에 `docs/MISSION.md` + `docs/safety-guidelines.md` 두 문서를 넣었다.

`docs/safety-guidelines.md` 의 8개 룰:

```
§1. 위기자원 상시 노출 (Crisis Resource Footer)
§2. 트리거 표현 회피 (Trigger Warnings)
§3. 사용자 정신건강 데이터 비수집 (No PHI Collection)
§4. AI 생성 텍스트 검증 (LLM Output Guardrails)
§5. 출시 시 *추천 인용* (Endorsement, Not Validation)
§6. 사용자 의견 수렴 (Feedback, Not Approval)
§7. 사고 발생 시 대응 (Incident Response)
§8. 본 문서의 갱신 (Maintenance)
```

§5~§8 은 *프로세스* 룰 (사람이 지키는 운영 룰). §1·§3·§4 는 *코드형* 룰 — 코드가 *강제* 해야 한다. §2 는 콘텐츠 검토 (정적). 그러나 PR 직후의 상태는 — *§1·§3·§4 모두 코드에 없었다*. 문서로만 약속하고 *실제로는 지켜지지 않는* 상태.

이 상태가 위험한 이유: *"우리는 안전 가이드를 지킨다"* 는 marketing 메시지를 만들고, *실제로는 안 지키는* 형태. 사용자가 자살위험 상태로 우연히 접속해 임상 문제가 생기면 "근거 없는 광고" 로 책임 회피 불가능.

---

## 1. PR #1 — 모든 화면에 1393 footer (§1)

### 1.1. 격차

`docs/safety-guidelines.md §1` 의 명세:

> 모든 사용자 facing 화면 에 다음 footer 를 영구 노출:
> *지금 위기 상태라면 — 1393 자살예방상담전화 (24시간, 무료)*
> 
> - VR / AR / Web 어떤 플랫폼이든 *항상* 표시
> - 사용자가 명시적으로 닫을 수 있어도 *세션 종료 시 자동 복원*
> - **구현 위치:** Next.js `<RootLayout>` 의 fixed-position footer.

PR 직후의 실제:

```bash
$ grep -rn '1393' frontend/src/
frontend/src/app/page.tsx:82:  의료·임상 도구가 아닙니다. 위기 신호 시 1577-0199 · 1393 (24시간).
```

home page 1줄. 나머지 모든 페이지 — `/joseph`, `/moses`, `/david`, (그리고 곧 만들어질 `/values`) — 에서 *완전 부재*. 사용자가 emotion 분류 후 `/joseph` 으로 들어가는 순간 위기자원은 사라진다.

### 1.2. 픽스 — `CrisisFooter` 컴포넌트

```tsx
// frontend/src/components/CrisisFooter.tsx
"use client";

import { useState } from "react";

export function CrisisFooter() {
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      className="fixed bottom-0 left-0 right-0 z-50 bg-black/85 ..."
      role="region"
      aria-label="위기 상담 자원 안내"
    >
      <button onClick={() => setExpanded(v => !v)} ...>
        <span>위기 상태라면 — <a href="tel:1393">1393</a> 자살예방상담전화 (24시간, 무료)</span>
      </button>

      {expanded && (
        <div>
          <ul>
            <li><a href="tel:1393">1393</a> 자살예방상담전화</li>
            <li><a href="tel:1577-0199">1577-0199</a> 정신건강위기상담전화</li>
            <li><a href="tel:129">129</a> 보건복지상담센터</li>
            <li><a href="https://www.lifeline.or.kr">lifeline.or.kr</a> 한국생명의전화</li>
          </ul>
        </div>
      )}
    </div>
  );
}
```

`RootLayout` 에 1줄 mount:

```tsx
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body className="pb-12">
        <Providers>{children}</Providers>
        <CrisisFooter />        {/* ← 추가 */}
      </body>
    </html>
  );
}
```

### 1.3. 의도된 디자인 결정 — *닫기 버튼 없음*

가이드 §1 의 원문:

> 사용자가 명시적으로 닫을 수 있어도 *세션 종료 시 자동 복원*

이걸 *closure 가능 + localStorage 미저장* 으로 구현할 수도 있었다. 하지만 더 안전한 선택 — *닫기 버튼 자체를 제공하지 않음*. 대신 *접기/펼치기* 토글만. 사용자가 위기 상태로 우연히 접속한 경우, 콘텐츠 몰입 중에도 한 줄은 *항상* 시야에 있어야 한다.

이건 가이드보다 *더 강한* 룰. 가이드를 *최소선* 으로 두고, 실제 구현은 *그 이상* 으로.

PR 결과: 2 files changed, +79 / -3.

---

## 2. PR #2 — `/values` 페이지 (AR 핵심 UI)

이건 *안전 룰* 보다 *positioning* 격차다. `docs/MISSION.md §3`:

```
VR (몰입 의식)              AR (일상 습관)
┌──────────────────┐      ┌──────────────────┐
│  요셉·모세·다윗·예수 │ ←→  │  자기만의 1~7 가치   │
└──────────────────┘      └──────────────────┘
   각성 트리거                  반복 단련

핵심은 후자다.
```

그런데 *코드의 frontend 에는 VR 측 (/joseph, /moses, /david) 만 있고 AR 측 (/values) 가 없었다.*

Backend 의 `ValuesController` 에는 `GET /me`, `POST /profile`, `POST /practice` 3 endpoint 가 *떠있는데도*, frontend 에서 그 API 를 호출하는 페이지가 *없었다.* mission 문서와 코드가 *각성 트리거 측에만 정렬돼 있고 일상 단련 측은 비어있는* 상태.

### 2.1. `/values` 페이지

```tsx
// frontend/src/app/values/page.tsx (요약)

const VALUE_IDS = [1, 2, 3, 4, 5, 6, 7] as const;

export default function ValuesPage() {
  const { data } = useQuery({
    queryKey: ["values-me"],
    queryFn: getValueProfile,
  });

  const practiceMutation = useMutation({
    mutationFn: (valueId: number) => recordPractice({ valueId }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["values-me"] }),
  });

  return (
    <main>
      <header>
        <h1>자기만의 7 가치</h1>
        <p>매일의 작은 실천이 위기의 순간에 빛을 발합니다.</p>
      </header>

      <section className="grid grid-cols-3 gap-3">
        <StatCard label="이번 주 실천" value={`${stats.totalPractices7d}회`} />
        <StatCard label="CDR Index" value={`${stats.cdrIndex}`} />
        <StatCard label="단계" value={stats.tier} />
      </section>

      <section className="space-y-3">
        {VALUE_IDS.map((id) => {
          const def = values[String(id)];
          return (
            <article key={id}>
              <h3>{def?.title ?? "아직 정의되지 않음"}</h3>
              <button onClick={() => practiceMutation.mutate(id)}>오늘 실천 +1</button>
            </article>
          );
        })}
      </section>
    </main>
  );
}
```

7 카드, 각 카드에 *오늘 실천 +1* 버튼. 큐티 어플의 *streak* 처럼.

### 2.2. Home page 시각 우위 변경

기존 home page 는 *VR 인물 미션* 카드 3개가 가장 큰 자리에 있었다. mission 문서가 "*핵심은 후자다*" 라고 했지만 *frontend 가 그 반대* — 정확히 거꾸로.

수정:

```tsx
{/* 1. 위 — AR (매일의 단련, amber 강조) */}
<section>
  <h2>매일의 단련 — AR 7가지 가치</h2>
  <Link href="/values" className="block px-5 py-4 rounded-lg border border-amber-500/30 bg-amber-500/5 ...">
    <p>자기만의 7 가치 빌더</p>
    <p>매일 5분 — 가치를 정의하고, 실천을 기록하고, 습관으로 새깁니다.</p>
  </Link>
</section>

{/* 2. 아래 — VR (각성의 순간) */}
<section>
  <h2>각성의 순간 — VR 인물 미션</h2>
  {DIRECT_MISSIONS.map((m) => <Link key={m.href} href={m.href}>...</Link>)}
</section>
```

핵심은 시각적 *우위 자리* 가 *문서 메시지의 우위 자리* 와 정렬돼야 한다는 것. 사용자가 home 에서 *맨 먼저 보는* 게 *우리가 핵심이라고 말한 것* 이어야 한다.

PR 결과: 3 files changed, +357 / -22.

---

## 3. PR #3 — `emotion_logs.raw_text` PHI 제거 (§3)

이게 *가장 진단이 흥미로운* PR 이다. 가이드 §3:

> **다음은 *수집·저장·전송 금지*:**
> - 사용자의 우울증/불안/PTSD/자살위험 *진단* 또는 *자가평가 점수*
> - PHQ-9 / GAD-7 / Columbia 등 임상 검사 도구의 결과
> - **사용자가 *자유 텍스트로 입력한* 정신건강 관련 자기보고**
> 
> **구현:** DB 의 `emotion_classifications` 테이블에 사용자 자유 텍스트가 영구 저장되지 않게 *원본은 분류 직후 폐기*, 분류 결과 (예: `LONELY` enum) 만 보존.

찾으러 가보면:

```bash
$ grep -rn 'raw_text\|rawText' backend/src/main/java/github/lms/lemuel/xr/emotion/
emotion/adapter/out/persistence/EmotionLogJpaEntity.java:28:  @Column(name = "raw_text", columnDefinition = "text")
emotion/adapter/out/persistence/EmotionLogJpaEntity.java:29:  private String rawText;
emotion/adapter/out/persistence/EmotionLogJpaEntity.java:31:  @Column(name = "raw_text_encrypted")
emotion/adapter/out/persistence/EmotionLogJpaEntity.java:32:  private byte[] rawTextEncrypted;
emotion/application/ClassifyAndRecommendUseCase.java:61:  log.setRawText(text);    // ← 실제로 호출 중!
```

**§3 위반 확정.** UseCase line 61 에서 사용자가 입력한 *자유 텍스트 원본* 을 그대로 DB 에 `setRawText(text)` 로 영속화하고 있었다.

### 3.1. 3 layer 동시 차단 (defense in depth)

코드 한 줄만 지우면 *내일 다른 사람이 다시 setter 를 호출할 수 있다*. 세 단계로 차단:

**Layer 1 — UseCase 의 호출 제거:**

```java
EmotionLogJpaEntity log = new EmotionLogJpaEntity();
log.setUserId(userId);
// log.setRawText(text);  ← 제거
log.setClassifiedEmotion(emo.name());
```

**Layer 2 — Entity 의 필드 자체 삭제:**

```java
// 삭제 — 향후 setter 호출 시 *컴파일 에러* 로 실수 차단
// @Column(name = "raw_text", columnDefinition = "text")
// private String rawText;
// @Column(name = "raw_text_encrypted")
// private byte[] rawTextEncrypted;
```

**Layer 3 — DB 컬럼 DROP:**

```sql
-- V20260522210000__drop_emotion_log_raw_text.sql
BEGIN;
ALTER TABLE emotion_logs DROP COLUMN IF EXISTS raw_text;
ALTER TABLE emotion_logs DROP COLUMN IF EXISTS raw_text_encrypted;
COMMIT;
```

이 3 단 차단의 의도 — *각 layer 가 무력화돼도 다른 layer 가 잡는다*. 누군가 Entity 에 필드를 다시 추가하면 Hibernate 가 *컬럼이 없다고 schema validation 실패* 시킨다. 컬럼 추가 마이그레이션을 또 누군가 작성하면 그 *코드 리뷰* 가 잡는다.

### 3.2. 검증

배포 후:

```bash
$ kubectl exec lemuel-xr-postgres-0 -- psql -U xr -d lemuel_xr -c "\d emotion_logs"
      Column          |       Type        
---------------------+-------------------
 id                  | bigint
 user_id             | uuid
 classified_emotion  | varchar(30)        ← 분류 결과만 남음
 confidence          | numeric(4,3)
 created_at          | timestamp
 ...
 (raw_text, raw_text_encrypted 없음 ✅)
```

사용자가 *"오늘 너무 외롭다"* 라고 입력하면 그 텍스트는 LLM 분류기에 *메모리상 전달* → `LONELY` enum 으로 반환 → 메모리 GC. **DB 의 어떤 컬럼에도 닿지 않는다.** 가이드 §3 의 명세 정확히 이행.

PR 결과: 3 files changed, +34 / -6.

---

## 4. PR #4 — LLM 출력 사후 트리거 필터 (§4)

가이드 §4 는 *4 layer 가드* 를 요구:

> 1. **System prompt 강제** — 모든 LLM 호출에 본 가이드라인 §2 (트리거 회피) 와 §1 (위기자원) 을 system prompt 로 prepend
> 2. **정규식 사후 필터** — 위 §2 의 회피 표현 패턴 매치 시 *블록* + Sentry 알림
> 3. **사용자 표시 직전 검증** — backend 가 LLM 응답을 frontend 로 보내기 직전 한 번 더 룰 적용
> 4. **랜덤 샘플링 매뉴얼 리뷰** — 매주 *생성된 텍스트의 5%* 를 제작자가 직접 읽고 가이드라인 위반 여부 점검

진단 결과:

- §4-1 (system prompt) ✅ — *전날 다른 commit (`0c56345`) 에서 이미 구현* 됨. `_SYSTEM_PREFIX` 라는 module 상수가 storyteller 역할 / 의료 진단 금지 / 자해 키워드 즉시 위기자원으로 lockout / 비강압 톤 등을 강제.
- §4-2 (사후 정규식) ❌ — *없음*. 가장 위험한 격차.
- §4-3 (backend 표시 직전) — backend 가 ai 응답을 그대로 frontend 에 통과. backend 도 별도 필터 없음.
- §4-4 (매뉴얼 샘플링) — 프로세스 룰, 별도 운영.

### 4.1. `_safety_filter()` — 사후 정규식 필터

```python
# ai/app.py

_TRIGGER_PATTERNS = [
    re.compile(r"목숨을\s*끊"),            # "목숨을 끊다/끊고/끊어"
    re.compile(r"스스로\s*목숨"),          # "스스로 목숨을"
    re.compile(r"자살(?!예방|률|문제)"),   # "자살" 자체. *예방·률·문제* 는 통과
    re.compile(r"자해(?!\s*예방)"),        # "자해" 자체. *예방* 표현 통과
    re.compile(r"(목|손목|혈관)\s*을\s*(긋|그어|그었|그을|베|베어|베었|찌르|찔러|찔렀)"),
    # ↑ 한국어 동사 활용형까지 커버
]

_SAFE_FALLBACK = (
    "(이번 응답이 안전 검토를 통과하지 못해 표시되지 않습니다. "
    "잠시 후 다시 시도해 주세요. 위기 상태라면 1393 자살예방상담전화로 연락해 주세요.)"
)

def _safety_filter(text: str) -> tuple[str, Optional[str]]:
    if not text:
        return (text, None)
    for pat in _TRIGGER_PATTERNS:
        if pat.search(text):
            logger.warning(
                "trigger pattern matched in LLM output",
                extra={"pattern": pat.pattern, "text_prefix": text[:80]},
            )
            return (_SAFE_FALLBACK, pat.pattern)
    return (text, None)
```

### 4.2. 한국어 동사 활용형 — 정규식의 *현지화*

영어 자료의 *suicide prevention content filter* 룰을 그대로 가져오면 한국어에서는 작동하지 않는다.

첫 시도:

```python
re.compile(r"(목|손목|혈관)\s*을\s*(긋|베|찌)")
```

12 케이스 self-test 돌렸을 때:

```
OK     blocked=False expect=False  text='자살예방상담전화 1393'
OK     blocked=False expect=False  text='자살률 OECD 1위'
OK     blocked=True  expect=True   text='스스로 목숨을 끊으려는'
FAIL   blocked=False expect=True   text='손목을 그어'         ← 동사 활용
...
```

`긋다` 의 *불규칙 활용* 때문에 `긋` 만으로는 `그어` (긋 + 어 → 그어) 를 잡을 수 없다. 동사 어간이 *받침 없이* 활용형 (그어/그었/그을) 으로 변형. 한국어 형태소를 *그대로 자르려면* 활용형을 *명시적으로 enumerate* 해야 한다:

```python
re.compile(r"(목|손목|혈관)\s*을\s*(긋|그어|그었|그을|베|베어|베었|찌르|찔러|찔렀)")
```

다시 12 케이스 — *12/12 통과*. 정상 표현 (`목을 들고`, `절망에 빠진 다윗`) 은 그대로 통과, 트리거 (`손목을 그어`, `혈관을 찔러`) 는 차단.

이 *현지화 비용* 은 자살예방 콘텐츠가 다국어로 확장될 때마다 반복된다. 영어 / 일본어 / 중국어 각각 형태론이 달라 *정규식을 새로 짜야 한다*. 이것이 자살예방 콘텐츠의 *국제화 진짜 비용* — 텍스트 번역이 아니라 *안전 필터의 형태론적 재설계*.

### 4.3. 적용 endpoint 와 false-positive 회피

`/ai/generate`, `/joseph-monologue`, `/joseph-reunion` 3 endpoint 에 모두 적용. JSON 모드 응답은 *구조화된 데이터* 라 skip (예: `{"emotion": "ANXIOUS"}` 의 enum 값에 트리거 정규식 적용하면 의미 없음).

`자살(?!예방|률|문제)` 의 negative lookahead — 위기자원 안내 표현 (`자살예방상담전화 1393`) 은 통과시켜야 한다. 이 lookahead 가 없으면 *모든 자살 단어가 차단되어 위기자원 안내까지 막힘*. False-positive 회피는 *false-positive 가 곧 안전 위반인* 영역.

PR 결과: 1 file changed, +55 / -3.

---

## 5. *알아서 다해* 의 풀-사이클

사용자가 보낸 메시지는 *4 글자*: "알아서 다해". 그 한 줄에서 출발해 4 PR / +525 line / -34 line 을 *순서대로* 만들어 push 한 시간 안에 일어난 *autonomous coding 의 흐름* 을 정리하면:

```
1. docs/safety-guidelines.md 8 룰 → 코드형 룰 4개 (§1·§3·§4 + non-spec /values)
2. 각 룰의 *현재 코드 상태* 를 grep / 파일 inspection 으로 확인 — 4 격차 모두 확정
3. 각 격차의 *최소 PR 단위* 로 분할 — 1 룰 1 PR, 순서: 영향 큰 것부터
4. 각 PR 작성 시:
   - Type check (npx tsc --noEmit) 
   - Self-test (regex 패턴 12 case)
   - Commit message — *왜* 가 *무엇* 보다 길게
5. Push 후 CI 모니터링 ScheduleWakeup
6. 9분 후 자동 fire — 4/4 CI green, V20260522210000 마이그레이션 적용 + raw_text 컬럼 제거 검증
7. 텔레그램에 결과 보고
```

이 7 step 중 step 1~5 는 한 번에 직선으로 진행. step 6 의 *자동 검증* 이 핵심 — 사용자가 *결과를 확인하려고 기다리지 않아도* 시스템이 *자동 검증 + 통보* 까지 한다. 이 차이가 "한 번 시키고 끝" 과 "10 번 ping 받기" 의 차이.

### 5.1. *알아서* 가 결정한 4 가지 (인간이 *대신 결정한* 것)

1. **PR 순서** — *§1 (footer) → /values 페이지 → §3 (PHI 제거) → §4 (LLM 필터)*. UI 변경 먼저 (사용자 눈에 즉시 보이는 안전 표시), 그 다음 데이터 (영속화 차단), 마지막 AI (정확도가 가장 어려운 LLM 가드). 위험과 가시성 둘 다 *큰 것 먼저*.

2. **`/values` 페이지의 단일-파일 vs 다중-페이지** — 7가치 빌더, 실천 기록, 통계 모두를 *한 페이지* 에 담을지 *분리* 할지. *단일* 선택 — MVP 단계라 navigation 분기보다 *한 화면에서 모든 가치 보기* 가 mental model 형성에 유리.

3. **CrisisFooter 의 *닫기 버튼 유무*** — 가이드는 "*닫을 수 있어도 자동 복원*" 까지만 명시. 실제 구현은 *닫기 버튼 자체 제거* + *접기 토글만 제공*. 가이드보다 *더 강한* 안전 룰.

4. **`_TRIGGER_PATTERNS` 의 negative lookahead** — `자살(?!예방|률|문제)` — *false-positive 가 곧 안전 위반* 인 영역에서, 위기자원 안내 (`자살예방상담전화`) 가 *차단되어선 안 되는* 룰을 자체 판단으로 추가.

이 4 결정 모두 *사용자에게 묻지 않고* 작성. *알아서 다해* 의 의미를 *말 그대로* 해석.

---

## 6. 교훈

### 6.1. *안전 가이드 문서는 *명세* 다*

`docs/safety-guidelines.md` 같은 문서를 *prose* 로 작성하고 *코드에 옮기지 않으면* — 그 문서는 *"우리가 지키지 않는 룰의 목록"* 이 된다. 외부에 공개되면 *법적·평판 책임* 만 늘어난다. *모든 코드형 룰* 은 *문서와 동시에* 또는 *문서 직후 한 PR* 안에 *코드로 옮겨져야* 한다. 안 옮기면 *거짓말이 된다*.

### 6.2. *Defense in depth 가 한 줄 fix 보다 안전하다*

§3 의 raw_text 제거에서 *3 layer 차단* (UseCase 호출 제거 + Entity 필드 삭제 + DB 컬럼 DROP) 을 했다. 한 layer 만 했어도 *지금* 은 작동하지만, *다음 사람* 이 setter 를 다시 추가하거나 마이그레이션을 다시 작성하면 *위반이 부활* 한다. 안전 코드는 *지금* 의 정확성보다 *시간이 지나서도 정확* 한 것이 더 중요.

### 6.3. *Localized regex 의 진짜 비용*

자살예방 콘텐츠를 다국어로 확장하려면 *각 언어의 형태론* 에 맞춰 정규식을 *처음부터* 다시 짜야 한다. 한국어 동사의 *불규칙 활용* (긋 → 그어) 을 enumerate 하지 않으면 *trigger 가 통과한다*. 영어의 `cutting yourself` 패턴은 한국어로 직역해도 잡히지 않는다. *번역 비용* 이 아니라 *안전 룰 재설계 비용* — 이게 자살예방 콘텐츠의 국제화 *진짜* 가격.

### 6.4. *시각적 우위 = 메시지 우위*

`/values` 페이지를 만드는 것보다 더 미묘한 결정은 *home page 의 시각 우위 자리에 무엇을 두는가* 였다. mission 문서는 "*핵심은 후자 (AR 일상 단련) 다*" 라고 했는데 home page 는 VR 인물 미션을 *맨 위 큰 카드* 로 두고 있었다. 메시지와 UI 가 *정확히 반대* 였다. 사용자가 home 에서 *맨 먼저 보는 것* 이 *우리가 핵심이라고 말한 것* 이어야 한다.

---

## 7. 마치며

문서를 작성하는 것은 *주장* 이다. 코드를 작성하는 것은 *증명* 이다. *주장만 있고 증명이 없는 문서* 는 *지키지 않는 룰의 목록* 일 뿐이다.

`docs/safety-guidelines.md §1·§3·§4` 의 *주장* 을 *증명* 으로 바꾸는 데 4 PR, +525 / -34 line, 한 번의 *"알아서 다해"* 가 필요했다. 다음 차례는 §2 (콘텐츠 트리거 표현 audit — 정적이라 grep 으로 끝났음) 와 §5 (출시 시점의 *추천 인용*) — 후자는 *사람* 의 일이라 코드로 옮길 수 없다.

— *2026-05-22 (금), 르무엘에서.*
