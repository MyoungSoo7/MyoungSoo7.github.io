---
layout: post
title: "자문가가 없을 때, 시스템이 거버넌스를 대신 가동한다 — Lemuel XR 검토 자동화 4편"
date: 2026-05-21 21:50:00 +0900
categories: [backend, governance, devops]
tags: [spring-boot, hexagonal, flyway, postgres, jsonb, playwright, e2e, next-js, jpa, idempotency]
---

성경 기반 감정 회복 + 서사 게임 플랫폼 **Lemuel XR** 의 Phase 2 마지막 단계. 신학·임상 자문가 영입은 진행 중인데, 자문가가 회의실에 들어오기 전까지 **시스템 측 거버넌스를 완전히 가동** 시켜놓아야 했다. 이 글은 하루에 4개의 PR(A·B·C·E) 로 끝낸 그 작업의 정리다.

> **TL;DR** — 검토 *행위* 가 아니라 검토 *체계* 를 먼저 코드로 박았다. 자문가가 verdict 만 넣으면 status 전환·격리(quarantine)·이력 표출까지 자동으로 흐르게.

---

## 왜 이 순서였나

자문 검토 워크플로 는 책 한 권 두께의 정책으로 끝낼 수도 있고, 4개의 use case 로 끝낼 수도 있다. 후자를 골랐다. 자문가가 들어오기 전에 *최소한의 동작하는 거버넌스* 를 확보해 두는 게, 자문가의 첫 verdict 가 허공에 떠 있지 않게 만드는 길이다.

```
[A] verdict 종합  →  자동 status 전환
[B] rejected 시  →  content_quarantine 자동 적재
[C] 결정 이력    →  /reviews 페이지 timeline
[E] 사용자 흐름  →  Playwright 5-Scene E2E
```

D (MVP-JESUS.md, Theme 11 영적 구원 시나리오 설계) 는 내가 단독으로 글로 써야 하는 영역이라 이번 묶음에서 빠졌다.

---

## A — verdict 종합 use case `EvaluateContentStatusUseCase`

신학(theology) + 임상(clinical) 자문가 각각이 `approve / request_changes / reject` 중 하나를 verdict 로 등록한다. 이 두 verdict 의 *조합* 으로 콘텐츠 status 가 결정된다.

```java
private String decideNext(Optional<TheologyReviewJpaEntity> t,
                          Optional<ClinicalReviewJpaEntity> c) {
    // 1. clinical Veto → 즉시 rejected (신학 verdict 무관)
    if (c.isPresent() && Boolean.TRUE.equals(c.get().getVetoUsed())) {
        return "rejected";
    }
    // 2. 한쪽이라도 reject
    if (t.isPresent() && "reject".equals(t.get().getVerdict())) return "rejected";
    if (c.isPresent() && "reject".equals(c.get().getVerdict())) return "rejected";

    // 3. 양쪽 모두 approve → published
    if (t.isPresent() && "approve".equals(t.get().getVerdict())
            && c.isPresent() && "approve".equals(c.get().getVerdict())) {
        return "published";
    }
    // 4. 한쪽이라도 request_changes
    if ((t.isPresent() && "request_changes".equals(t.get().getVerdict()))
            || (c.isPresent() && "request_changes".equals(c.get().getVerdict()))) {
        return "changes_requested";
    }
    return null; // 5. 한쪽 verdict 만 있음 → 다른 쪽 대기
}
```

### 임상 자문가의 단독 거부권(Veto)

핵심은 **임상 자문가만의 단독 거부권(Veto)** 이다. 트라우마·moral injury 안전성에서 임상 측이 "이건 절대 안 됨" 을 선언하면, 신학 측 의견과 무관하게 즉시 rejected. 정신건강 안전이 신학적 정합성보다 *항상* 우선이라는 정책을, if 문 한 줄로 박았다.

```java
if ("rejected".equals(next) && !"rejected".equals(previous)) {
    v.setStatus("rejected");
    quarantineRejected(contentVersionId, theology, clinical); // → B 로 이어짐
}
```

`published` 와 `archived` 는 terminal state — 본 use case 의 입력으로 들어와도 status 변경하지 않는다. immutability 보장.

---

## B — 격리(Quarantine) 자동 적재

rejected 가 된 콘텐츠는 단순히 status 만 바뀌어선 안 된다. **왜 거부됐는지, 누가 거부했는지, 어떤 키워드 때문이었는지** 를 별도 테이블에 박아둬야 admin 이 후속 처리(승급/escalate/closed)를 할 수 있다.

### content_quarantine 스키마

```sql
CREATE TABLE content_quarantine (
    id BIGSERIAL PRIMARY KEY,
    content_version_id UUID NOT NULL REFERENCES content_versions(id) ON DELETE CASCADE,

    veto_by TEXT NOT NULL CHECK (veto_by IN (
        'clinical_veto',          -- 임상 단독 거부권
        'theology_reject',        -- 신학만 reject
        'clinical_reject',        -- 임상만 reject (Veto 미사용)
        'both_reject',            -- 양쪽 reject
        'auto_keyword_filter',    -- 키워드 필터 자동 차단
        'manual'                  -- admin 수동
    )),
    reason TEXT,
    blocked_keywords JSONB DEFAULT '[]'::jsonb,

    triggered_by_theology_review_id BIGINT REFERENCES theology_reviews(id) ON DELETE SET NULL,
    triggered_by_clinical_review_id BIGINT REFERENCES clinical_reviews(id) ON DELETE SET NULL,

    reviewed_by_admin UUID,
    admin_action TEXT CHECK (admin_action IN ('closed', 'escalated')),
    admin_notes TEXT,

    quarantined_at TIMESTAMP NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMP
);

CREATE INDEX content_quarantine_pending_idx
    ON content_quarantine(quarantined_at DESC) WHERE resolved_at IS NULL;
CREATE INDEX content_quarantine_version_idx ON content_quarantine(content_version_id);
CREATE INDEX content_quarantine_veto_by_idx ON content_quarantine(veto_by);
```

설계 포인트:

- **FK ON DELETE SET NULL** — review row 가 지워져도 격리 이력은 보존돼야 한다. 컴플라이언스 측면에서 *누가 왜 차단했는지* 의 root cause 는 사라지더라도, *콘텐츠가 차단됐었다* 는 사실은 사라지면 안 된다.
- **blocked_keywords JSONB GIN** — 지금은 비어있지만 자동 키워드 필터 도입 시 채워질 자리. 미리 인덱스 박아놓음.
- **pending 부분 인덱스** — admin 대시보드에서 *해결 안 된 것만* 조회하는 게 99% — 부분 인덱스로 효율 확보.

### Idempotent 적재

같은 콘텐츠에 대해 같은 사유(`veto_by`)로 두 번 격리되면 안 된다. 자문가가 verdict 를 한 번 수정·재등록할 수 있는 워크플로라서, EvaluateContentStatusUseCase 가 두 번 호출돼도 멱등해야 한다.

```java
if (quarantines.existsByContentVersionIdAndVetoBy(contentVersionId, vetoBy)) {
    log.info("content_quarantine 이미 적재됨 — skip. version={} veto_by={}",
            contentVersionId, vetoBy);
    return;
}
```

settlement 시스템에서 익힌 **Triple Idempotency** 패턴(outbox event_id / processed_events PK / DB UNIQUE) 의 가벼운 버전. 여기는 (content_version_id, veto_by) 페어가 사실상 unique 키 역할.

---

## C — /reviews 페이지의 검토 이력 timeline

자문가가 verdict 만 등록하면 사라지는 건 의미가 없다. **결정의 흐름** 이 보여야 다음 자문가가 *왜 이 콘텐츠가 이 상태인지* 를 즉시 이해할 수 있다.

### Endpoint

```java
@GetMapping("/api/reviews/history")
public ResponseEntity<List<HistoryItem>> history(
        @RequestParam(value = "limit", defaultValue = "30") int limit) {
    List<ContentVersionJpaEntity> all = versions.findAll();
    List<HistoryItem> items = all.stream()
            .filter(v -> v.getStatus() != null
                    && !"in_review".equals(v.getStatus())
                    && !"draft".equals(v.getStatus()))
            .sorted((a, b) -> b.getCreatedAt().compareTo(a.getCreatedAt()))
            .limit(limit)
            .map(v -> new HistoryItem(
                    v.getId(), v.getContentKind(), v.getContentRef(), v.getVersion(),
                    v.getStatus(), v.getCreatedAt(), v.getPublishedAt(),
                    theologyReviews.findByContentVersionIdOrderByReviewedAtDesc(v.getId())
                            .stream().limit(3).map(this::toTimelineEntry).toList(),
                    clinicalReviews.findByContentVersionId(v.getId())
                            .stream().limit(3).map(this::toClinicalTimelineEntry).toList()))
            .toList();
    return ResponseEntity.ok(items);
}
```

`in_review` 와 `draft` 는 *아직 결정 안 난* 상태. history 에선 제외 — 그건 큐(/queue) 의 영역.

### Frontend: theology + clinical 시간 정렬

각 콘텐츠 카드 안에서 신학·임상 검토 row 를 **시간순으로 merge** 해서 한 줄짜리 timeline 으로 표시.

```tsx
const merged: TimelineEntry[] = [...item.theology, ...item.clinical].sort(
  (a, b) => new Date(a.reviewedAt).getTime() - new Date(b.reviewedAt).getTime(),
);
```

```
[14:23] 신학  approve     | 창세기 41:34 인용 정확. 풍년 비율 33% 일치.
[14:27] 임상  ⚠VETO       | moral injury 표현 — 고난 정당화 footer 없음. 수정 후 재제출.
```

status 색상은 published=초록 / rejected=빨강 / changes_requested=노랑. **Veto 사용 시 ⚠VETO 마커** — 다음 자문가가 즉시 인지하도록.

---

## E — Playwright Joseph 5-Scene E2E

여기까지 코드 레벨에서는 다 됐다. 하지만 *진짜로* 사용자가 Joseph 미션을 1번 Scene 부터 5번 outro 까지 완주할 수 있는가는 다른 문제다. 손가락 클릭 흐름이 깨지는 건 unit test 가 못 잡는다.

```ts
test("immigrant_first 결말 흐름이 완주된다", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("link", { name: /Joseph/ }).first().click();

    // Scene 1 cinematic → 계속
    await page.getByRole("button", { name: /계속/ }).click();

    // Scene 2 pick_one — "1/3 저장" (요셉이 실제로 따른 비율, 창 41:34)
    await page.getByRole("button", { name: /1\/3|33|저장/ }).first().click();

    // Scene 3 distribute — 이주민 가족 우선
    await page.getByRole("button", { name: /이주민|immigrant/i }).first().click();

    // Scene 4 pick_one — 정체를 즉시 밝힌다
    await page.getByRole("button", { name: /밝히|reveal|용서/i }).first().click();

    // Scene 5 outro
    await page.getByRole("button", { name: /미션 완료/ }).click();
    await page.waitForURL(/\/$/);
});
```

**immigrant_first** 결말을 골라 검증한 이유 — Scene 3 에서 이주민(외국인) 줄에 곡식을 먼저 주는 결정이 Scene 5 에서 **moral injury / 섭리는 가해자의 정당화가 아니다** 결말 톤으로 분기되는 가장 어려운 경로다. 이게 깨지면 나머지 farmer_first / merchant_first 도 의심해야 한다.

> Jones 2022 (PMID 35609469) 의 moral injury 매핑. 자문가 검토 항목 중 `moral_injury_risk` (1-5, 낮을수록 위험) 척도와 직접 연결된다.

### config 결정

```ts
export default defineConfig({
  fullyParallel: false,
  workers: 1,  // 세션 순서 의존 — 병렬 X
  webServer: process.env.BASE_URL
    ? undefined
    : { command: "npm run dev", url: "http://localhost:3000", ... },
});
```

`BASE_URL` 환경변수로 임의 origin 지정 가능. CI 에선 `BASE_URL=https://xr.lemuel.co.kr npx playwright test` 로 *실제 배포된 환경* 을 두드릴 수 있게.

---

## 배포 검증

`main` 한 번 푸시하면 끝난다는 게 GitOps 의 약속이다. 그 약속이 지켜졌는지 확인:

```
✅ A 1f663e9  feat(theology): EvaluateContentStatusUseCase
✅ B 331afdc  feat(theology): content_quarantine 자동 적재
✅ C 9f07f97  feat(reviews): /reviews 검토 이력 timeline
✅ E b860539  test(e2e): Playwright Joseph 5-Scene
✅ doc 3342046 CLAUDE.md Theme 11 단독

CI 5 run / 25 job 전부 success
ArgoCD Image Updater 자동 sync → newest-build 태그 반영
xr.lemuel.co.kr/reviews → "검토 이력" 탭 렌더링 OK
xr.lemuel.co.kr/api/reviews/history → 200 OK
```

내부에서 본 신호(CI green, ArgoCD Healthy) 와 외부에서 본 신호(`curl https://xr.lemuel.co.kr/api/reviews/history` 가 200) 가 일치해야 "끝" 이다. 이 원칙은 [어제 글](/2026/05/20/production-agent-goal-completed-external-verification.html) 에서 다뤘다.

---

## 다음 단계

남은 건 한 가지:

- **D — MVP-JESUS.md** (Theme 11, 영적 구원 시나리오 설계서). 이건 자동화할 수 없는 글이다. 내가 단독으로 써야 한다.

자문가 영입 outreach 는 별도 트랙. 시스템 측 산출물은 영입 전에 다 깔아놨다 — 자문가의 첫 verdict 가 들어오는 순간 status 전환·격리·이력 표출까지 자동으로 흐른다.

> *코드로 박을 수 있는 거버넌스는 코드로 박는다. 사람이 해야 하는 결정만 사람에게 남긴다.*

---

## 인용·참고

- 창세기 41:34 — 요셉의 1/3 저장 비율
- Jones 2022, PMID 35609469 — moral injury 척도 매핑
- Phase 2 설계: `docs/governance/CLINICAL-REVIEW.md`
- 이전 글: [Production agent 가 '끝났다' 고 말하기까지](/2026/05/20/production-agent-goal-completed-external-verification.html)
