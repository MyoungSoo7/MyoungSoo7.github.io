---
layout: post
title: "Scene 2 가 모바일에서 까맣게 끊긴다 — LFS pointer · sceneType mismatch · mutated Flyway 3건 디버그"
date: 2026-05-21 21:50:00 +0900
categories: [debug, infra, xr]
tags: [git-lfs, docker, next-js, flyway, hibernate, argocd, gitops, mobile]
---

오늘 모바일 단말에서 *lemuel-xr* 의 요셉 미션 Scene 2 가 깨졌다는 신고가 들어왔다. Scene 1 은 잘 뜨는데 Scene 2 부터 **배경 이미지가 까만 사각형** + **저장 결정 버튼 3개가 아예 안 보임**. 한 시간 동안 풀어본 결과 *완전히 다른 레이어의* 버그 두 개가 같은 화면에 겹쳐 있었고, 같은 배포 사이클에 *세 번째 버그 (production 잠복형)* 도 같이 발견됐다.

> ⚠️ 보안 — 도메인 / 노드명 / 토큰은 redacted. 구조만 공유.

---

## TL;DR — 세 줄 + 표

| # | 버그 | 레이어 | 원인 | 사용자 영향 |
|---|---|---|---|---|
| 1 | Scene 2 배경 이미지 깨짐 | **CI / Docker** | `actions/checkout@v4` 에 `lfs: true` 누락 → 컨테이너 안에 LFS pointer (132 B) 만 들어감 | 모바일에서 즉시 보임 (까만 화면) |
| 2 | Scene 2 저장 버튼 누락 | **Frontend** | yml `type: interaction, interaction: pick_one` 인데 React 가 `type === "pick_one"` 만 매칭 | 모바일·데스크톱 양쪽 (Scene 2/4 진행 불가) |
| 3 | 새 backend pod CrashLoopBackOff | **DB / Flyway** | 마이그레이션 파일을 *적용된 뒤 수정* → Hibernate schema validation 실패 | **0** (기존 pod 가 살아있어 사용자 영향 없음. 잠복형) |

수정 커밋: `fix(frontend): Scene 2 백그라운드+버튼 — LFS checkout + interaction 매칭` — 빌드/배포 약 8분 → 모바일에서 1.5 MB 진짜 JPEG + 1/5·1/3·1/2 버튼 정상 노출 확인.

---

## 0. 배경 — 어디서 출발했나

오늘 디버그 직전의 상태:

- *lemuel-xr* = 성경 인물 의사결정 미션을 VR/AR/MR 3모드로 풀어주는 사이드 프로젝트. Next.js 16 + Spring Boot 4 + Python FastAPI AI 사이드카 + Coqui TTS 의 모노레포.
- Public demo URL: `https://xr.lemuel.co.kr` — Cloudflare Tunnel 통해 자가 K3s 클러스터로 라우팅.
- 직전에 *완전히 다른 버그* (Cloudflare 가 옛 HTML 을 캐싱해서 옛 chunk 파일명 참조 → 500) 를 `middleware.ts` 의 `Cache-Control: no-store` 로 해결한 직후였다. Scene 1 → 2 → 3 풀 사이클 `200 OK` 를 `curl` 로 검증해서 "끝났다" 판단.

그 직후 *모바일* 에서 Scene 1 은 잘 뜨는데 **Scene 2 부터 화면이 까만 사각형** 이라는 사진이 왔다.

```
JOSEPH — SCENE 2/5 · MODE: VR
풍년 — 저장 결정
[ 까만 사각형 ]
( 버튼 없음 )
```

`curl` 로 200 OK 검증이 끝났는데도 화면이 깨진다는 건, *백엔드 응답은 정상이지만 그 응답을 그리는 단계가 깨진다* 는 신호. 두 가지로 좁혔다 — 정적 자산 (`/images/scenes/2.jpg`) 누락, 그리고 응답의 *형태* 와 *프론트의 매칭* 간 mismatch.

---

## 1. 버그 #1 — Docker 이미지 안에 LFS pointer 가 들어가 있다

배경 이미지의 절대 경로는 `public/images/scenes/2.jpg`. Next.js 빌드는 이걸 그대로 `/app/public/` 에 복사해 standalone 런타임에서 서빙한다. 그래서 컨테이너 안을 직접 봤다.

```bash
$ POD=$(kubectl -n lemuel-xr-prod get pods -l app=lemuel-xr-frontend -o name | head -1)
$ kubectl -n lemuel-xr-prod exec "$POD" -- ls -la /app/public/images/scenes/
-rw-r--r-- 1 root root  132 May 21 06:58 1.jpg
-rw-r--r-- 1 root root  132 May 21 06:58 2.jpg
-rw-r--r-- 1 root root  132 May 21 06:58 3.jpg
-rw-r--r-- 1 root root  132 May 21 06:58 4.jpg
-rw-r--r-- 1 root root  132 May 21 06:58 5.jpg
```

**5개 다 132 byte.** Imagen 4.0 으로 생성해서 push 했을 때는 ~1.5 MB 짜리 JPEG 였는데 컨테이너 안에서는 132 byte. 그 모양은 너무 익숙하다.

```bash
$ kubectl -n lemuel-xr-prod exec "$POD" -- cat /app/public/images/scenes/2.jpg
version https://git-lfs.github.com/spec/v1
oid sha256:e381cfc189348af7baa7f6e6c98ff11a4225234be1c11c1c624c89584c04348f
size 1505924
```

**Git LFS pointer 그 자체.** 실제 binary blob 은 LFS 원격에만 있고, 작업 트리에는 132 byte 짜리 메타 파일만 있는 상태. `nginx` 든 Next.js standalone 이든 이걸 곧이곧대로 `image/jpeg` Content-Type 으로 서빙하면 브라우저는 "header 가 망가진 JPEG" 로 해석해서 까만 사각형을 그린다.

### 1.1. 왜 들어갔나

루트는 `.gitattributes` 였다.

```
*.jpg       filter=lfs diff=lfs merge=lfs -text
*.jpeg      filter=lfs diff=lfs merge=lfs -text
*.png       filter=lfs diff=lfs merge=lfs -text
```

원래는 Unity 의 텍스처 / FBX 같이 *진짜 큰* 바이너리를 LFS 로 넘기려고 적어둔 규칙이었다. 그런데 `*.jpg` 패턴이 *프론트 정적 자산* `public/images/scenes/*.jpg` 까지 같이 잡아챈다. 그 결과 — 로컬에서 `git add public/images/scenes/2.jpg` 하면 LFS 에 올라간다.

### 1.2. 왜 컨테이너 안에서 132 byte 인가

CI workflow 의 frontend job 이 이런 모양:

```yaml
frontend:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4         # ← lfs 옵션 없음
    - uses: docker/setup-buildx-action@v3
    - uses: docker/build-push-action@v6
      with:
        context: .
```

`actions/checkout@v4` 는 **기본값으로 LFS 파일을 받지 않는다**. LFS 파일은 132 byte pointer 만 받는다. 그 후 `docker buildx` 가 `COPY . .` 하면 — *그 132 byte* 가 컨테이너 안에 그대로 박힌다. CI 도, 빌드도, 푸시도 전부 성공으로 끝나지만 컨테이너 안의 정적 자산은 깨져있는 상태.

이게 정말로 "모든 자동화가 초록불인데 결과만 깨져있는" 종류의 버그다.

### 1.3. 픽스 — 한 줄

```yaml
frontend:
  steps:
    - uses: actions/checkout@v4
      with:
        lfs: true              # ← 추가
```

CI runner 가 LFS 원격에서 진짜 binary 를 받아오게 한 다음 `COPY . .` 가 그걸 컨테이너에 박는다.

---

## 2. 버그 #2 — sceneType mismatch (백엔드 yml ↔ 프론트 React)

이미지가 들어가도 *버튼 3개* (1/5·1/3·1/2 저장) 는 별개 문제. 응답 페이로드부터 확인했다.

백엔드 시나리오 정의 `joseph.yml`:

```yaml
- id: 2
  title: 풍년 — 저장 결정
  type: interaction          # ← top-level type
  interaction: pick_one      # ← 세부 interaction 형태
  options:
    - { id: save_20, label: "1/5 저장", weight: 20 }
    - { id: save_33, label: "1/3 저장", weight: 33 }
    - { id: save_50, label: "1/2 저장", weight: 50 }
```

이 yml 이 그대로 JSON 직렬화돼서 응답으로 나간다:

```json
{
  "currentScene": 2,
  "scenePayload": {
    "title": "풍년 — 저장 결정",
    "type": "interaction",
    "interaction": "pick_one",
    "options": [ ... ]
  }
}
```

프론트의 Joseph 페이지는 `payload.type` 한 필드만 보고 분기했다:

```tsx
const sceneType = (payload.type as string) ?? "";

{sceneType === "pick_one" && Array.isArray(payload.options) && (
  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
    {payload.options.map((o) => (
      <button onClick={() => decide.mutate(...)}>{o.label}</button>
    ))}
  </div>
)}
```

`payload.type === "interaction"` 이라 `sceneType === "pick_one"` 매칭이 false → 버튼이 *조건부 렌더링 자체에서 빠진다.* 빈 div 만 남는다.

### 2.1. 왜 이렇게 어긋났나

yml 의 `type` 은 **렌더링 카테고리** (cinematic / interaction / outro) 였고, `interaction` 은 *interaction 형태의 세부 종류* (pick_one / distribute) 였다. 즉 의도된 *2단계 분기* 였다. 그런데 프론트 코드가 1단계로 합쳐 그렸다. 의도와 코드가 처음부터 달랐던 거지, 이번에 깨진 게 아니다 — Scene 2 진입을 *지금까지 아무도 안 했기 때문에* 잠복해 있었다.

### 2.2. 픽스 — sceneType 도출 한 줄 추가

```tsx
const rawType = (payload.type as string) ?? "";
const sceneType =
  rawType === "interaction" ? ((payload.interaction as string) ?? "") : rawType;
```

이걸로 `payload.type === "interaction"` 이면 `payload.interaction` 값을 사용해서 `"pick_one"` / `"distribute"` 로 떨어진다. 기존 cinematic / outro 매칭도 그대로 동작.

기존 모든 매칭 블록 (`sceneType === "pick_one"`, `sceneType === "distribute"`, `sceneType === "cinematic"`, ...) 은 변경 없이 그대로 동작 — yml 스키마와 React 가 *드디어* 일치.

---

## 3. 푸시·배포 검증

두 줄짜리 PR 을 main 에 머지하고 ArgoCD Image Updater 가 새 이미지를 픽업하길 기다린다.

```bash
$ gh run view 26215066527 --json status,conclusion
{"status":"completed","conclusion":"success"}      # 5/5 job 성공

$ kubectl -n lemuel-xr-prod get pods -l app=lemuel-xr-frontend
NAME                                  READY   STATUS    RESTARTS   AGE
lemuel-xr-frontend-84dd6865d6-4m8zt   1/1     Running   0          5m27s

$ curl -sI https://xr.lemuel.co.kr/images/scenes/2.jpg | grep -E 'HTTP|content-length'
HTTP/2 200
content-length: 1505924                # ← 132 B → 1.5 MB. LFS pull 작동.
```

content-length 가 LFS pointer 안의 `size 1505924` 와 일치하는 게 깔끔하다. **버그 #1 검증 완료.**

버그 #2 (React 매칭) 는 같은 commit 의 같은 이미지에 들어있다. 모바일에서 새 탭으로 진입 → 1/5·1/3·1/2 버튼 3개 정상 노출, 클릭 → Scene 3 진행, monologue 응답 (`요셉이 실제로 따른 비율 (창 41:34)...`) 정상 표시.

---

## 4. 보너스 — 같은 배포에 잠복해 있던 *세 번째* 버그

위 두 fix 를 ArgoCD 가 픽업했는지 확인하다가 *backend* 의 새 pod 가 `CrashLoopBackOff` 인 걸 발견했다 (frontend 와 별 컴포넌트). 기존 pod (139 분 가동) 가 그대로 살아있어서 *사용자에게는 0초의 영향* 도 없었지만, 새 코드는 절대 못 뜨고 있는 상태.

### 4.1. 로그

```
ERROR o.s.o.j.LocalContainerEntityManagerFactoryBean
  Failed to initialize JPA EntityManagerFactory:
  Unable to build Hibernate SessionFactory [persistence unit: default];
  nested exception is org.hibernate.tool.schema.spi.SchemaManagementException:
  Schema validation: missing column [referenced_pmids] in table [theology_reviews]
```

Hibernate 의 `hibernate.hbm2ddl.auto=validate` 가 *entity 의 컬럼* 과 *실제 DB 의 컬럼* 사이의 mismatch 를 잡아낸 거다. Entity 쪽 (Java):

```java
@Column(name = "referenced_pmids", columnDefinition = "jsonb")
private java.util.List<String> referencedPmids;
```

DB 쪽 (`\d theology_reviews`):

```
id                  | bigint
content_version_id  | uuid
reviewer_id         | uuid
...
reviewer_profile_id | uuid               # ← 마이그레이션 V20260521135130 에서 추가
                                          # referenced_pmids 는 없음
```

### 4.2. 근본 원인 — *적용된 뒤 수정된* Flyway 마이그레이션

`V20260521135130__align_theology_reviews_with_profiles.sql` 파일을 열어보면 이런 형태:

```sql
-- ============================================================
-- theology_reviews 에 reviewer_profile_id 컬럼 추가
-- ============================================================

ALTER TABLE theology_reviews
    ADD COLUMN IF NOT EXISTS reviewer_profile_id UUID
        REFERENCES reviewer_profiles(id) ON DELETE SET NULL;

-- ...

-- ============================================================
-- 권장 — clinical_reviews 와 동일하게 referenced_pmids JSONB 도 추가
-- ============================================================

ALTER TABLE theology_reviews
    ADD COLUMN IF NOT EXISTS referenced_pmids JSONB NOT NULL DEFAULT '[]'::jsonb;
```

파일에는 `referenced_pmids` 컬럼 추가 SQL 이 *있다.* 그런데 DB 에는 그 컬럼이 *없다*. `flyway_schema_history` 를 보면:

```
version         | description                          | installed_on
20260521135130  | align theology reviews with profiles | 2026-05-21 06:29:46
```

이 마이그레이션은 *이미 적용됐다.* — 정확히는, *그날 6:29 에 적용된 시점의 파일에는* `reviewer_profile_id` 섹션만 있었다. 그 뒤 누군가 (자동 PR 봇이든 사람이든) 같은 파일을 열어서 `referenced_pmids` 섹션을 *덧붙였다.* Flyway 는 *같은 버전 번호* 에 대해 *이미 적용 기록이 있으니 재실행하지 않는다.* (checksum 검증을 끈 모드였다면 그대로 통과.)

결과 — 코드 (Entity) 는 새 컬럼을 기대하지만 DB 에는 그 컬럼이 없다. 새 backend pod 가 Hibernate 의 schema validation 에 걸려 Exit 1, 무한 재시작.

### 4.3. 왜 사용자에게는 안 보였나

ArgoCD 가 새 pod 를 `Pending → CrashLoop` 으로 띄우는 동안 *기존 pod* 는 그대로 `Running` 으로 들고 있다. K8s Deployment 의 RollingUpdate 전략이 새 pod 가 Ready 가 될 때까지 기존 pod 를 종료시키지 않는다. 결과적으로 *사용자 facing 트래픽은 100% 옛 pod 가 받고 있고*, 새 코드의 신기능 (`referenced_pmids` 관련 admin API) 만 깜깜한 상태. 모니터링이 "App: Degraded" 라고 알려주지 않았다면 *모르고 지나갈 수 있는 사고였다.*

### 4.4. 픽스 (다음 commit) — 새 timestamp 의 보조 마이그레이션 1건

원래 파일을 *되돌릴 수는 없다* — 이미 적용된 마이그레이션 파일을 수정하는 게 애초의 원죄. 대신 새 timestamp 의 별 파일을 추가:

```sql
-- V20260521214900__add_theology_reviews_referenced_pmids.sql
-- 이전 V20260521135130 가 적용된 뒤 referenced_pmids 섹션이 사후 추가됐는데
-- Flyway 가 같은 version 을 재실행하지 않아 production DB 에 누락.
-- 이 보조 마이그레이션으로 누락 컬럼만 채워 entity ↔ schema 정합 회복.

ALTER TABLE theology_reviews
    ADD COLUMN IF NOT EXISTS referenced_pmids JSONB NOT NULL DEFAULT '[]'::jsonb;

ALTER TABLE theology_reviews
    ADD CONSTRAINT ck_theology_reviews_referenced_pmids_array
    CHECK (jsonb_typeof(referenced_pmids) = 'array');

CREATE INDEX IF NOT EXISTS idx_theology_reviews_referenced_pmids_gin
    ON theology_reviews USING gin (referenced_pmids);

-- ROLLBACK NOTES (운영 사고 시 reference; 자동 적용 금지)
-- DROP INDEX IF EXISTS idx_theology_reviews_referenced_pmids_gin;
-- ALTER TABLE theology_reviews DROP CONSTRAINT IF EXISTS ck_theology_reviews_referenced_pmids_array;
-- ALTER TABLE theology_reviews DROP COLUMN IF EXISTS referenced_pmids;
```

`IF NOT EXISTS` 가 들어가있어서 *혹시 다른 환경* 에서는 이미 컬럼이 있어도 안전하게 통과한다.

---

## 5. 교훈 — 3가지

### 5.1. *모든 CI 가 초록불인 채로* 결과만 깨질 수 있다

LFS pointer 는 그 전형이다. Lint, test, build, push, deploy — 전부 성공으로 끝났는데 컨테이너 안의 정적 자산은 132 byte 메타 파일이다. 이걸 잡으려면 **빌드 결과물 안의 실제 파일** 을 한 번은 봐야 한다. CI 통과 = 코드 정확함 ≠ artifact 정확함.

CI 에서 *artifact 안에 들어간 정적 자산이 실제 binary 인지* 를 검증하는 step 을 추가하는 게 다음 작업:

```yaml
- name: Verify static assets are not LFS pointers
  run: |
    for f in public/images/scenes/*.jpg; do
      if [ "$(head -c 12 "$f")" = "version http" ]; then
        echo "::error::$f is an LFS pointer, not a real binary"
        exit 1
      fi
    done
```

### 5.2. 백엔드 *스키마* 와 프론트 *매칭 코드* 는 *같은 정의에서 생성* 돼야 한다

`type: interaction, interaction: pick_one` 와 React 의 `sceneType === "pick_one"` 의 mismatch 는 *yml 스키마를 TypeScript 타입으로 자동 생성* 하지 않은 결과다. 백엔드 yml 이 진실의 원천 (source of truth) 이면, 프론트가 그걸 *읽기만* 하면 되도록 — 예: zod schema generator, jsonschema-to-typescript, openapi-typescript 등 — 한 단계만 거치면 *컴파일 단계에서* 잡힌다.

다음 작업: `joseph.yml` → JSON Schema → TypeScript 타입 자동 생성 파이프라인.

### 5.3. *적용된 마이그레이션 파일은 절대 수정하지 않는다*

Flyway / Liquibase / Alembic 류 마이그레이션 도구의 *제1 계명* 이지만, 자동화 (자동 PR 봇, AI 코더) 가 잘 어기는 규칙이다. "기존 V20260521135130 파일에 한 섹션 더 추가" 가 자연스러워 보이지만, 그 파일이 이미 production 에 적용된 순간 *불가침* 이어야 한다. 추가 변경은 항상 *새 timestamp 의 새 파일*.

이걸 자동 봇이 어기지 않게 막는 방법:
- pre-commit / CI 에 *"이미 production 의 flyway_schema_history 에 있는 version 의 파일이 수정되면 reject"* hook
- 또는 마이그레이션 디렉토리에 `.versioned` 마커 + 적용된 파일은 read-only chmod

다음 작업으로 둠.

---

## 6. 마치며

세 버그가 한 줄로 정리되면:

1. **LFS pointer in Docker** — CI checkout 에 `lfs: true` 단 한 줄 누락이 컨테이너 안에 까만 사각형을 박았다.
2. **sceneType mismatch** — yml 의 *2단계 분기* 를 프론트가 1단계로 합쳐버려, 그 분기를 처음 타는 Scene 2 에서 버튼이 사라졌다.
3. **Mutated Flyway migration** — 이미 적용된 파일에 섹션을 사후 추가한 죄로, 새 backend pod 가 Hibernate schema validation 에 걸려 안 떴다. *기존 pod 가 살아있어 사용자에게는 안 보였다는 게 더 무서운 부분.*

세 가지가 *완전히 다른 레이어* — CI / 프론트 / DB — 인데 같은 배포 사이클에 같이 터졌다는 게 오늘의 가장 큰 데이터 포인트. 통합 시스템에서는 *하나의 사용자 신고* 가 *서로 무관한 여러 레이어의 잠복 버그* 를 동시에 폭로하는 경우가 자주 있다는 걸 다시 확인.

내일은 위 §5.1 / §5.2 의 두 가지 *재발 방지 가드* 를 PR 로 올릴 계획. — LFS pointer 검증 step, joseph.yml → TS 타입 자동 생성.

— *2026-05-21 (목), 르무엘에서.*
