---
layout: post
title: "Flyway 를 쓰는 서비스는 이미지 롤백이 스키마 롤백이 아니다"
date: 2026-09-24 15:50:00 +0900
categories: [devops]
tags: [flyway, database-migration, rollback, kubernetes, argocd, spring-boot]
---

오늘 여러 서비스를 한꺼번에 이전 이미지로 되돌리다가 얻은 교훈을 한 줄로 적으면 이렇다.

> **Flyway 를 쓰는 서비스는 이미지 롤백이 스키마 롤백이 아니다.
> 되돌릴 때는 새 마이그레이션이 붙은 서비스를 빼고 되돌려야 한다.**

당연한 말 같지만, 쿠버네티스에서 롤백은 너무 쉽다. `kubectl rollout undo` 한 줄,
혹은 ArgoCD 에서 이전 리비전 클릭 한 번이면 된다. 그래서 "전부 어제 버전으로"가 반사적으로 나온다.
이 글은 그 반사를 멈춰야 하는 이유와, 그 대신 무엇을 해야 하는지를 정리한다.

Flyway 기본 개념은 전에 따로 정리했다 —
[Liquibase vs Flyway, 변경의 정체성]({% post_url 2026-09-14-liquibase-vs-flyway-change-identity %}).

## 무엇이 되돌아가고 무엇이 안 되돌아가나

Spring Boot 앱에 Flyway 가 붙어 있으면, 앱이 뜰 때 Flyway 가 먼저 돌면서 아직 적용되지 않은
마이그레이션(`V7__...sql` 같은)을 DB 에 적용한다
([Spring Boot 문서](https://docs.spring.io/spring-boot/how-to/data-initialization.html)).

그러니 새 버전을 배포하는 순간 일어나는 일은 두 가지다.

| | 배포할 때 | 이미지를 롤백할 때 |
|---|---|---|
| 애플리케이션 코드 | v2 로 바뀜 | v1 로 돌아감 ✅ |
| DB 스키마 | V7 이 적용됨 | **V7 그대로 남음** ❌ |
| `flyway_schema_history` | V7 기록 추가 | **V7 기록 그대로** ❌ |

이미지는 컨테이너 안의 코드만 바꾼다. DB 는 컨테이너 밖에 있다.
롤백 후의 상태는 "어제"가 아니라 **"어제의 코드 + 오늘의 스키마"**라는, 한 번도 테스트한 적 없는 조합이다.

## 더 나쁜 점: 옛 이미지는 대개 조용히 뜬다

"옛 코드가 새 스키마를 보면 Flyway 가 에러를 내 주겠지"라고 기대하기 쉽다. 기본 설정에서는 그렇지 않다.

- Flyway 는 `migrate` 전에 자동으로 `validate` 를 돈다 — [`validateOnMigrate` 기본값 `true`](https://documentation.red-gate.com/flyway/reference/configuration/flyway-namespace/flyway-validate-on-migrate-setting).
- 그런데 validate 가 무시하는 패턴의 기본값이 [`ignoreMigrationPatterns = "*:future"`](https://documentation.red-gate.com/flyway/reference/configuration/flyway-namespace/flyway-ignore-migration-patterns-setting) 다.
  "future" 는 DB 에는 적용돼 있지만 지금 코드에는 없는 마이그레이션이다. 롤백한 옛 이미지 입장에서 V7 이 정확히 이 상태다.

즉 **기본 설정의 옛 이미지는 V7 을 모른 척하고 정상 기동한다.** 헬스체크도 초록이다.
문제는 그다음에 터진다. V7 이 컬럼 이름을 바꿨거나, NOT NULL 컬럼을 추가했거나, 테이블을 쪼갰다면
옛 코드의 쿼리가 **요청을 받는 시점에** 실패한다. 기동 실패는 바로 보이지만, 런타임 실패는 트래픽이 와야 보인다.

반대로 누군가 `*:future` 를 무시 목록에서 뺐다면, 옛 이미지는 validate 에서 실패해 기동 자체를 못 한다.
CrashLoopBackOff 가 된다. 어느 쪽이든 롤백으로 "어제의 정상"을 되찾지는 못한다.

## 그럼 스키마도 되돌리면 되지 않나?

Flyway 에는 [undo 마이그레이션](https://documentation.red-gate.com/flyway/flyway-concepts/migrations/undo-migrations)(`U7__...sql`)이 있다.
하지만 두 가지를 알고 써야 한다.

1. **Teams 에디션 기능이다.** 문서 상단에 `EDITION: TEAMS` 로 표시돼 있다. 커뮤니티 에디션에는 없다.
2. 문서 스스로 한계를 적어 둔다. undo 는 **해당 마이그레이션 전체가 성공했다고 가정**한다.
   DDL 트랜잭션이 없는 DB 에서 중간에 실패한 마이그레이션에는 도움이 안 된다.
   drop·delete·truncate 같은 파괴적 변경이 있으면 특히 조심하라고 한다. 지운 데이터는 undo 스크립트로 돌아오지 않는다.

그리고 같은 문서가 **대안**을 제시한다. 요지는 이렇다.

> DB 와 현재 프로덕션에 배포된 **모든 버전의 코드** 사이에 하위 호환성을 유지하라.
> 그러면 옛 버전의 앱도 DB 와 호환되므로, 애플리케이션 코드만 롤백하고 조사한 뒤 바로잡으면 된다.
> 이것은 잘 검증된 백업·복구 전략으로 보완해야 한다.

## 실전 규칙

### 1. 롤백 대상을 고르기 전에, 마이그레이션이 붙었는지부터 본다

되돌리려는 두 이미지 사이에 `db/migration/V*.sql` 이 추가됐는지 확인한다.

```bash
git diff --name-only <롤백할_커밋>..<현재_커밋> -- '*db/migration/*'
```

결과가 비어 있지 않은 서비스는 **일괄 롤백 목록에서 뺀다.** 그 서비스는 따로, 사람이 판단한다.

### 2. 마이그레이션 서비스는 "뒤로"가 아니라 "앞으로" 고친다 (roll forward)

문제가 새 코드에 있다면, 스키마는 그대로 두고 코드만 고친 v2.1 을 내보낸다.
문제가 새 스키마에 있다면, 그걸 고치는 **새 마이그레이션 V8** 을 추가한다.
`flyway_schema_history` 를 손으로 지우는 건 최후의 수단이다. 기록과 실제 스키마가 갈라진다.

### 3. 애초에 롤백 가능한 마이그레이션만 만든다 (expand → contract)

컬럼 이름 변경을 한 번에 하지 않고 여러 배포로 나눈다.

1. **expand** — 새 컬럼을 추가하고, 코드는 양쪽에 쓴다. 옛 코드도 여전히 동작한다.
2. 데이터를 이관하고, 코드는 새 컬럼을 읽는다.
3. **contract** — 옛 코드가 더 이상 배포되지 않는 게 확실해진 뒤, 옛 컬럼을 지운다.

이렇게 하면 1·2 단계에서는 이미지 롤백이 다시 안전해진다. 위 Flyway 문서가 말하는
"배포된 모든 버전의 코드와 호환"이 바로 이 상태다.

### 4. 롤백 계획에는 백업 시점이 적혀 있어야 한다

파괴적 마이그레이션이 포함된 배포라면, 배포 직전 백업(또는 스토리지 스냅샷)이 있는지 확인한 뒤에 배포한다.
Flyway 문서도 undo 보다 **검증된 백업·복구 전략**을 우선하라고 권한다.

## 체크리스트

- [ ] 되돌릴 이미지 구간에 새 `V*.sql` 이 있는가? → 있으면 일괄 롤백에서 제외
- [ ] 우리 설정의 `ignoreMigrationPatterns` 는 기본값(`*:future`)인가? → 그렇다면 "기동 성공 = 정상"이 아니다
- [ ] 최근 마이그레이션이 옛 코드와 호환되는가(expand 단계인가)?
- [ ] 파괴적 변경이라면 직전 백업이 있는가?
- [ ] 고치는 방향이 roll forward(코드 수정 또는 V다음번호) 인가?

이미지 태그는 시간을 되돌려 주지만, 데이터베이스는 시간이 한 방향으로만 흐른다.

## References

- Flyway 문서, *Validate On Migrate Setting* (기본값 `true`) — <https://documentation.red-gate.com/flyway/reference/configuration/flyway-namespace/flyway-validate-on-migrate-setting>
- Flyway 문서, *Ignore Migration Patterns Setting* (기본값 `*:future`) — <https://documentation.red-gate.com/flyway/reference/configuration/flyway-namespace/flyway-ignore-migration-patterns-setting>
- Flyway 문서, *Undo Migrations* (Teams 에디션, 한계와 하위 호환 대안) — <https://documentation.red-gate.com/flyway/flyway-concepts/migrations/undo-migrations>
- Spring Boot 문서, *Database Initialization* (기동 시 Flyway 실행) — <https://docs.spring.io/spring-boot/how-to/data-initialization.html>
