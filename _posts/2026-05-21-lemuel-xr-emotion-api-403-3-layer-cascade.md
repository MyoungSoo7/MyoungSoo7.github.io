---
layout: post
title: "lemuel-xr 감정 분석이 안 돌 때 — DB 비번부터 pgvector extension·SQL 문법까지 3중 캐스케이드"
date: 2026-05-21 22:00:00 +0900
categories: [infra, kubernetes, gitops]
tags: [lemuel-xr, k3s, argocd, postgres, pgvector, flyway, hibernate, frontend, debugging]
---

오후에 텔레그램으로 스크린샷 두 장이 왔다. 첫 장은 우리 프로젝트의 첫 페이지 — *"지금 마음에 떠오르는 한 줄을 적어 주세요"* 입력 박스. 두 장은 그 박스에 *"오늘 너무 외롭고 지쳐있어"* 를 적고 "감정 분석 + 본문 추천" 버튼을 눌렀더니 뜬 **`This page couldn't load`**.

DevTools Console 에는 한 줄:

```
Uncaught TypeError: Cannot read properties of undefined (reading 'emotion')
```

이거 디버깅하다가 *세 겹의 운영 사고* 가 한꺼번에 드러났다. 다 무관한 원인이고 다 같은 마이그레이션 한 commit 에 묶여있었다.

> ⚠️ 도메인·노드명·IP·토큰·비밀번호 redacted. 패턴만 공유.

---

## 0. 가설: 왜 *세 겹* 이 한꺼번에 터지나

각 한 줄로 요약하면:

1. **frontend** 가 *새 응답 shape* 를 기대한다 — `result.primary.emotion` 을 읽는다
2. **deployed backend** 는 *옛 응답 shape* 를 보낸다 — flat `{emotion, confidence}` 만
3. 그래서 `result.primary` 가 `undefined` → `.emotion` 접근에서 크래시

여기까지는 평범한 *프론트·백 응답 contract 불일치*. 진짜 재미는 **왜 옛 응답이 살아남았느냐** 다.

---

## 1. 첫 번째 layer — 옛 pod 가 안 죽는 이유

```bash
kubectl -n <ns> get pods -l app=backend
```
```
NAME                READY   STATUS             RESTARTS   AGE
backend-OLD-xxxxx   1/1     Running            0          11h
backend-NEW-yyyyy   0/1     CrashLoopBackOff   8 (45s ago)   18m
```

옛 pod 는 11시간 째 Running. 새 pod 는 CrashLoopBackOff. K8s 의 RollingUpdate 가 *새 pod readiness 통과* 못 하면 옛 pod 안 죽인다 — 안전장치다. 그래서 *Service 가 옛 pod 로만 라우팅 → 옛 응답이 계속 나옴*.

새 pod 크래시 로그:

```
Caused by: org.postgresql.util.PSQLException:
  FATAL: password authentication failed for user "xr"
```

DB 비번이 틀렸다.

```bash
# Postgres StatefulSet 의 init 환경변수
POSTGRES_USER     = xr
POSTGRES_PASSWORD = <literal-string>    ← 약한 literal (이후 ALTER USER 로 교체됨)

# Backend 의 ENV
SPRING_DATASOURCE_PASSWORD ← secretKeyRef → 회전된 24자 랜덤

# Secret 의 실제 값
<redacted-rotated>   ← rotation 됐음
```

DB 는 *literal `password`* 로 `xr` 사용자를 초기화했고, secret 은 그 후 어느 시점에 *24자 랜덤* 으로 회전됐다. 옛 pod 는 *secret rotation 이전* 시작돼서 Hikari connection pool 안의 idle connection 이 살아있어 *재인증 없이* 계속 동작하는 중이었다. 새 pod 는 *방금* 시작했으니 fresh 연결 시도 → fail.

> 운영의 무서운 면 — *연결 풀이 살아있는 동안* 은 비번 회전이 *조용히* 무력화된다. 다음 재시작에서 한꺼번에 터진다.

**Fix 1**: `xr` 사용자의 실제 password 를 secret 값으로 동기화.

```bash
kubectl exec postgres-0 -- psql -U xr -d <db> -c \
  "ALTER USER xr WITH PASSWORD '<secret 값>';"
```

옛 pod 가 안에서 *literal `password`* 로 여전히 연결 가능했기에 (다음 fresh 연결 전까지) 이 ALTER 자체는 옛 비번으로 인증되어 통과한다. 그 다음부터는 *secret 값* 으로 모두 통과.

---

## 2. 두 번째 layer — pgvector extension 이 image 에 없음

새 pod 를 한 번 죽이고 새로 띄웠더니 *다른 에러* 로 넘어갔다:

```
Caused by: org.flywaydb.core.internal.exception.FlywayMigrateException:
  Failed to execute script V6__scripture_embeddings.sql
  ERROR: extension "vector" is not available
  Detail: Could not open extension control file
    "/usr/share/postgresql/16/extension/vector.control": No such file or directory.
```

`CREATE EXTENSION IF NOT EXISTS vector` — pgvector 다. `postgres:16` *standard* image 에는 pgvector 가 *번들되어 있지 않다*. `pgvector/pgvector:pg16` 처럼 *번들된 image* 가 따로 있다.

여기서 두 갈래:

- **임시 패치**: 운영 pod 안에 `apt-get install -y postgresql-16-pgvector` — 즉시 회복. 단 *pod 재시작 시 사라지는 휘발성 fix*
- **영구 fix**: helm-deploy 차트의 image 를 `pgvector/pgvector:pg16` 으로 교체 → ArgoCD sync → postgres pod 재기동

두 개 다 했다. 임시로 백엔드 살리고, helm-deploy 의 `values.yaml` 에서 한 줄 교체:

```yaml
# charts/lemuel-xr/values.yaml
postgres:
-  image: postgres:16
+  image: pgvector/pgvector:pg16
```

commit + push → ArgoCD manual sync → postgres pod 가 새 image 로 재기동. PVC 가 유지돼서 데이터 보존. *비번 ALTER 도 PVC 에 남아 있어* 새 image 로도 그대로 인증 통과.

> 운영의 안락한 면 — *PVC 가 따로 있으면 image 만 바꾸는 사고는 데이터 손실 0*. 단 *재시작 동안 ~30초 다운타임* 은 받아들여야 한다.

---

## 3. 세 번째 layer — 마이그레이션 SQL 자체의 문법 버그

pgvector 가 박혔으니 V6 통과. 새 pod 가 또 다른 곳에서 죽었다:

```
Caused by: org.postgresql.util.PSQLException:
  ERROR: syntax error at or near "||"
  Position: 111
  Location: V20260521135130__align_theology_reviews_with_profiles.sql
  Line:     22
```

문제의 22~24줄:

```sql
COMMENT ON COLUMN theology_reviews.reviewer_profile_id IS
    '자문가의 등록 프로필 (role=theology). 신규 검토는 이 컬럼 채움. ' ||
    '레거시 row 는 reviewer_id (users) 만 있고 NULL.';
```

`||` 는 PostgreSQL 에서 *문자열 concat 연산자*. 그러나 **`COMMENT ON ... IS` 의 RHS 는 *단일 string literal* 만 받는다** — 표현식 (concat 포함) 불허다. 문법 책에는 *"comment_text: string literal"* 한 줄로만 나와서 잊기 쉽다.

같은 commit 의 *다른* `COMMENT ON` 들은 *짧아서 한 줄로 합쳐* 통과했었다. 이 한 줄만 길어서 *코드 가독성* 을 우선해 concat 으로 줄바꿈했더니 문법 위반.

**Fix 3a (운영)**: psql 로 *수정된 SQL 을 수동 실행* + `flyway_schema_history` 에 SUCCESS row 직접 INSERT.

```sql
COMMENT ON COLUMN theology_reviews.reviewer_profile_id IS
    '자문가의 등록 프로필 (role=theology). 신규 검토는 이 컬럼 채움. 레거시 row 는 reviewer_id (users) 만 있고 NULL.';

INSERT INTO flyway_schema_history
       (installed_rank, version, description, type, script, checksum,
        installed_by, execution_time, success)
SELECT 14, '20260521135130', 'align theology reviews with profiles', 'SQL',
       'V20260521135130__align_theology_reviews_with_profiles.sql',
       NULL, 'manual-hotfix', 0, true
WHERE NOT EXISTS (SELECT 1 FROM flyway_schema_history WHERE version = '20260521135130');
```

Flyway 가 다음 부팅 시 *이 row 가 success 로 기록돼 있음을 보고 skip* — 마이그레이션 통과.

**Fix 3b (영구)**: 마이그레이션 파일 자체에서 `||` 제거 + 한 string literal 로 합침. commit + push. 다음 배포 시 *원본 파일이 옳음*.

---

## 4. 부산물 — Hibernate schema validation

V20260521135130 의 hot-patch 가 *몇 줄을 빼먹은 채로* 적용됐다 (사용자가 읽었던 첫 ~39줄만 복붙). 그러나 같은 commit 의 JPA Entity 는 *V20260521135130 이 추가하기로 한 `referenced_pmids` JSONB 컬럼* 까지 매핑해두고 있었다:

```java
@JdbcTypeCode(SqlTypes.JSON)
@Column(name = "referenced_pmids", columnDefinition = "jsonb")
private List<String> referencedPmids;
```

새 backend 가 부팅 시 Hibernate `validate` 모드라서:

```
SchemaManagementException:
  Schema validation: missing column [referenced_pmids] in table [theology_reviews]
```

또 죽었다. psql 로 *빠진 41~53줄* 까지 마저 실행:

```sql
ALTER TABLE theology_reviews
    ADD COLUMN IF NOT EXISTS referenced_pmids JSONB NOT NULL DEFAULT '[]'::jsonb;
-- CHECK 제약 추가, GIN 인덱스 ...
```

이번엔 정말 통과. 새 backend 1/1 Running.

---

## 5. 네 번째 layer — AI sidecar 의 `ModuleNotFoundError`

backend 가 살아나니 *AI sidecar* 차례. CrashLoopBackOff:

```
File "/app/app.py", line 23, in <module>
    import providers
ModuleNotFoundError: No module named 'providers'
```

`ai/Dockerfile`:

```dockerfile
COPY app.py .
```

같은 commit 에서 `ai/providers.py` 가 *새로 추가됐는데* Dockerfile 의 `COPY` 가 업데이트 안 됐다. `app.py` 만 image 에 들어가고 `providers.py` 는 누락. python 부팅 즉시 ImportError.

**Fix 4**:

```dockerfile
 COPY app.py .
+COPY providers.py .
```

이 한 줄 + 위 마이그레이션 fix 를 같은 commit 으로 묶어 push. CI 빌드 후 ArgoCD sync → 새 AI image 가 1/1 Running.

---

## 6. 마지막 확인 — API 응답이 *옛 shape* 에서 *401/403* 으로 바뀌면 성공

```bash
curl -X POST https://<domain>/api/emotion/classify \
     -H "Content-Type: application/json" \
     -d '{"text":"오늘 외롭다"}'
```

- **사고 전**: `{"emotion":"CONFUSED","confidence":0.0}` — 옛 shape, AI 호출 실패하고 fallback
- **사고 후**: `HTTP 403` — JWT auth filter 가 정상 작동. *이제* 게스트 토큰 발급 + Authorization 헤더 흐름을 프론트가 추가하면 끝.

403 은 *나쁜 신호가 아니라* *새 코드가 떴다는 신호* 였다. 옛 shape 가 사라진 게 진척.

---

## 7. 정리 — 5겹의 fix 와 그 순서

| # | layer | fix | reversibility |
|---|---|---|---|
| 1 | DB 인증 (secret rotation 비대칭) | `ALTER USER ... WITH PASSWORD` | reversible — 비번 다시 회전 |
| 2 | pgvector extension 미번들 | `apt-get install` (임시) + helm-deploy image 교체 (영구) | reversible — image 되돌리기 |
| 3 | 마이그레이션 SQL 문법 (`COMMENT IS \|\|`) | psql 수동 실행 + schema_history 등록 + 코드 fix commit | reversible — DOWN SQL 별도 |
| 4 | Hibernate validation (`referenced_pmids` 누락) | 빠진 ALTER 마저 실행 | reversible — DROP COLUMN |
| 5 | AI Dockerfile (`providers.py` 미복사) | Dockerfile 수정 + commit + push | reversible — git revert |

순서가 *섞이면 안 됨* — 1 이 안 되면 2 의 에러 안 보인다. 2 가 안 되면 3 의 에러 안 보인다. *cascade* 라서 한 번에 한 layer 씩 까야 한다.

---

## 8. 운영에서 배운 두 가지

**(A) 비번 회전은 *connection pool 의 상태* 와 짝지어야 한다.**

비번을 회전하면 *기존 idle connection 은 계속 동작* 한다. 그래서 *비번 회전 직후의 모든 것이 OK 처럼 보인다*. 다음 *fresh* 연결이 필요한 순간 (롤링 업데이트·재기동·신규 pod) 한꺼번에 fail. 회전과 *명시적 pod 재기동* 또는 *connection drain* 을 짝지어 운영해야 한다. SQL 사용자의 password 를 *secret 으로만 관리하고 init 환경변수에선 literal 을 안 쓰는 게* 더 안전한 패턴이다.

**(B) Hibernate `validate` 와 Flyway 는 *같은 commit* 안에서 *합의된 schema* 를 봐야 한다.**

`@Column(name = "...")` 추가는 *반드시* 동일 commit 의 마이그레이션이 그 컬럼을 만들어야 한다. *그 마이그레이션이 실패해서 partially apply* 되면 Hibernate 가 부팅 시 *그 partial state* 를 보고 validation fail. *Migration 의 idempotency + Hibernate 의 strictness* 가 두 layer 라서, *migration 이 SUCCESS 인데 schema 가 partial* 인 상황은 *수동 hot-patch 가 만든 합법적 외상* 이다.

이 사고는 *3 layer cascade 라서 무서웠지만* 결과적으론 *각 layer 의 fix 가 짧고 reversible* 이라 *cascade 가 진실을 빠르게 드러내준* 케이스였다. 한 layer 가 너무 길거나 reversible 하지 않았다면 더 위험했다.

---

총 소요 약 1시간. commit 2개 (lemuel-xr `262d795`, helm-deploy `0d07e8f`) + DB hot-patch SQL 3건. 끝.
