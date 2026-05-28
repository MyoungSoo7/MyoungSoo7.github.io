---
layout: post
title: "Harness Engineering ④ Deployment Harness — CI/CD + GitOps, 그리고 *외부 검증* 까지 가야 끝나는 이유"
date: 2026-05-29 01:40:00 +0900
categories: [devops, deployment]
tags: [harness, deployment, cicd, gitops, argocd, image-updater, helm, canary, blue-green, sre]
---

> "Harness Engineering 의 4 가지 얼굴" 시리즈의 마지막 4 편. [① AI Agent]({% post_url 2026-05-29-harness-engineering-1-ai-agent-claude-code %}) / [② Test]({% post_url 2026-05-29-harness-engineering-2-test-spring-boot %}) / [③ Software Engineering]({% post_url 2026-05-29-harness-engineering-3-developer-toolchain %})

배포는 *개발자가 가장 자주 깨먹는* 부분이다. 코드 push 까진 *내가 한 일* 인데, 그 다음부터 *컨테이너 빌드 → 레지스트리 push → 클러스터 sync → pod rollout → 사용자 트래픽 흡수* 는 *여러 시스템의 합주* 다.

이 합주를 *반복 가능하게, 추적 가능하게, 안전하게* 만드는 인프라가 *Deployment Harness*. 단순히 "쿠버네티스 깔았다" 가 아니라, *push → 사용자에게 도달* 까지의 *전체 라이프사이클* 을 게이트 + 관찰 + 롤백 가능하게 묶는 것.

이 글은 GitOps 시대의 deployment harness 표준 패턴과, *5월 17일 sparta-msa 배포 사고* 같은 *내부 신호 vs 외부 검증* 의 차이를 정리한다.

---

## TL;DR — Deployment Harness 의 8 단계

| # | 단계 | 도구 / 패턴 |
|---|---|---|
| 1 | 코드 push | GitHub / GitLab |
| 2 | CI 빌드 | GitHub Actions, Tag-immutable 이미지 |
| 3 | 이미지 push | GitHub Container Registry, ECR, GCR |
| 4 | 이미지 업데이터 감지 | ArgoCD Image Updater, Flux Image Automation |
| 5 | Git 매니페스트 commit | helm-deploy repo 자동 PR/push |
| 6 | GitOps sync | ArgoCD, Flux |
| 7 | Pod rollout | Rolling / Canary / Blue-Green |
| 8 | **외부 검증** | curl on public domain, smoke test |

---

## 0. *내부 신호* 만 믿으면 안 되는 이유

5월 17일 sparta-msa 의 *newest-build 경합* 사고. 줄거리:

1. 개발자 A 가 `fix/bug-x` 커밋 push
2. 개발자 B 가 *같은 시점* 에 `feat/y` 커밋 push
3. CI 두 빌드 동시 시작 → 둘 다 `:latest` 이미지로 push (잘못된 태그 전략)
4. Image Updater 가 *마지막 push 된 이미지* 만 받아서 sync
5. *A 의 fix 가 묻힘* — 그러나 *ArgoCD 는 Healthy*, *Pod 는 Running*, *모든 내부 신호 OK*
6. 사용자 도메인 `chat.lemuel.co.kr` 에 *fix 적용 안 된 상태* 가 *3 시간 노출*

교훈: **내부 신호 (Argo Healthy, Pod Running) 만으로는 *fix 가 사용자에게 도달* 했는지 모른다.** *외부 도메인의 served bytes* 까지 검증해야 *진짜 끝*.

이게 *deployment harness 의 8 단계 중 8 번째 — 외부 검증* 이 *왜 필수* 인지의 이유.

---

## 1. 코드 push → CI 빌드

```yaml
# .github/workflows/build.yml
name: Build
on:
  push:
    branches: [main]

jobs:
  build-and-push:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v4

      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - uses: docker/metadata-action@v5
        id: meta
        with:
          images: ghcr.io/myorg/sparta-chat
          tags: |
            type=sha,prefix=sha-,format=short
            type=raw,value=${{ github.sha }}-${{ github.run_number }}
            type=ref,event=branch

      - uses: docker/build-push-action@v5
        with:
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

핵심 결정:
- **`:latest` 태그 *쓰지 말 것*** — 5월 17일 사고의 직접 원인
- **`commit SHA + run_number` 조합** — *immutable* 이미지 태그. 같은 SHA 도 *재빌드 시 새 태그*
- **`cache-from / cache-to`** — 빌드 속도 ↑

---

## 2. 이미지 push → 이미지 업데이터 감지

### ArgoCD Image Updater 설정

```yaml
# argocd Application
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: sparta-chat
  annotations:
    argocd-image-updater.argoproj.io/image-list: chat=ghcr.io/myorg/sparta-chat
    argocd-image-updater.argoproj.io/chat.update-strategy: newest-build
    argocd-image-updater.argoproj.io/chat.allow-tags: regexp:^[a-f0-9]{40}-\d+$
    argocd-image-updater.argoproj.io/chat.helm.image-name: image.repository
    argocd-image-updater.argoproj.io/chat.helm.image-tag: image.tag
    argocd-image-updater.argoproj.io/write-back-method: git
    argocd-image-updater.argoproj.io/git-branch: main
```

**중요 옵션:**
- `update-strategy: newest-build` → 가장 최근 *빌드* 이미지 (semver 기반 아님)
- `allow-tags: regexp:^[a-f0-9]{40}-\d+$` → SHA + run_number 형식만 허용. `:latest` 같은 다른 태그 *무시*
- `write-back-method: git` → 감지 시 *helm-deploy repo 에 자동 PR*

### Write-back 결과

```yaml
# helm-deploy/applications/sparta-chat/values.yaml (자동 변경)
image:
  repository: ghcr.io/myorg/sparta-chat
  tag: 7a3f9c2-142   # ← 이미지 업데이터가 commit
```

---

## 3. GitOps Sync — *Git 이 source of truth*

ArgoCD 가 *Git 의 상태와 클러스터의 상태를 비교* → diff 있으면 sync.

```bash
$ argocd app get sparta-chat
Name:               sparta-chat
Sync Status:        Synced
Health Status:      Healthy
Revision:           7a3f9c2  # Git commit
Images:             ghcr.io/myorg/sparta-chat:7a3f9c2-142
```

이 단계가 *Argo Healthy* 의 의미. **단 *진짜 사용자가 새 버전을 받았다* 는 의미가 *아님*.**

---

## 4. Rollout 전략 — *얼마나 안전하게* 새 버전 노출할까

### Rolling Update (기본)

```yaml
# Deployment
spec:
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 25%       # 동시에 추가 생성 가능 pod 수
      maxUnavailable: 0   # 동시 종료 허용 pod 수 (0 = 항상 capacity 유지)
```

- 새 pod 1개 띄움 → ready → 옛 pod 1개 종료 → 반복
- 다운타임 0
- 단점: *새 버전에 버그* 면 *점진적으로 모든 사용자* 가 영향

### Canary — 일부 트래픽만

```yaml
# Argo Rollouts
apiVersion: argoproj.io/v1alpha1
kind: Rollout
spec:
  strategy:
    canary:
      steps:
        - setWeight: 10    # 트래픽 10% 새 버전으로
        - pause: { duration: 5m }
        - setWeight: 25
        - pause: { duration: 10m }
        - setWeight: 50
        - pause: { duration: 30m }
        - setWeight: 100
      trafficRouting:
        nginx:
          stableIngress: sparta-chat-stable
```

- 새 버전을 *10% → 25% → 50% → 100%* 단계적 노출
- 각 단계 사이 *대기 + 메트릭 검증*
- 메트릭 (에러율, latency) 악화 시 자동 *rollback*

### Blue-Green — *완전 분리* 후 swap

```yaml
strategy:
  blueGreen:
    activeService: sparta-chat-active
    previewService: sparta-chat-preview
    autoPromotionEnabled: false   # 수동 승인
```

- 새 버전 (green) 을 *별도 서비스* 로 띄움
- *Preview URL* 로 *내부 테스트*
- 승인 시 *active 트래픽을 green 으로 swap*
- 옛 (blue) 은 *N분 유지* 후 종료

선택 기준:

| 전략 | 적합 워크로드 |
|---|---|
| Rolling | 일반 stateless 서비스 (대부분) |
| Canary | 큰 트래픽 + risk 큼 (결제, 인증) |
| Blue-Green | DB 마이그레이션 동반, *완전 롤백 필요* |

---

## 5. 외부 검증 — *진짜* 배포 확인

위 모든 단계가 통과해도 *사용자 도메인에서* 새 버전을 안 받을 수 있다 (CDN 캐시, 잘못된 ingress, DNS 캐시 등).

### 표준 외부 검증 스크립트

```bash
#!/bin/bash
# scripts/verify-deployment.sh
DOMAIN="https://chat.lemuel.co.kr"
EXPECTED_COMMIT="${1:?Need commit SHA}"

# 1. /version 엔드포인트가 새 commit 노출
ACTUAL=$(curl -sf "$DOMAIN/version" | jq -r .commit)
if [ "$ACTUAL" != "$EXPECTED_COMMIT" ]; then
    echo "❌ Expected $EXPECTED_COMMIT, got $ACTUAL"
    exit 1
fi

# 2. 핵심 API 200 응답
HEALTH=$(curl -sf -w "%{http_code}" "$DOMAIN/api/health" -o /dev/null)
if [ "$HEALTH" != "200" ]; then
    echo "❌ Health check failed: $HEALTH"
    exit 1
fi

# 3. CDN 캐시 무력화 확인 (Cache-Control 헤더)
CACHE=$(curl -sIf "$DOMAIN/" | grep -i "cache-control")
echo "Cache header: $CACHE"

# 4. 새 버전의 *기능* 동작
RESPONSE=$(curl -sf "$DOMAIN/api/v2/new-feature")
if ! echo "$RESPONSE" | jq -e .ok > /dev/null; then
    echo "❌ New feature endpoint failed"
    exit 1
fi

echo "✅ External verification passed"
```

CI 의 *마지막 step* 또는 *별도 verification job* 으로 실행. *이게 통과해야 진짜 배포 성공*.

내 환경에선 `sparta-deploy-pipeline-verifier` agent 가 이 역할을 자동화. 5월 17일 사고 이후 *직접 도입*.

---

## 6. Observability — *배포의 영향* 을 즉시 보기

좋은 deployment harness 는 *배포 직후의 메트릭 변화* 를 자동으로 보여준다.

### Grafana 대시보드 annotation

```yaml
# Helm release 시 annotation 추가
helm:
  hooks:
    - kind: Job
      annotations:
        helm.sh/hook: post-install,post-upgrade
spec:
  template:
    spec:
      containers:
        - image: curlimages/curl
          command: ["sh", "-c"]
          args:
            - |
              curl -X POST http://grafana/api/annotations \
                -H "Authorization: Bearer $TOKEN" \
                -d '{
                  "tags": ["deploy"],
                  "text": "Deployed {{ .Values.image.tag }}",
                  "time": '$(date +%s%3N)'
                }'
```

Grafana 대시보드의 *그래프 위에 수직선* 으로 *배포 시점* 표시. 메트릭 변화와 배포의 인과 *즉시 인식*.

### Prometheus Alert — *배포 후 SLO 위반* 자동 감지

```yaml
- alert: PostDeployErrorSpike
  expr: |
    (
      sum(rate(http_requests_total{status=~"5.."}[5m]))
      /
      sum(rate(http_requests_total[5m]))
    ) > 0.01
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "Error rate > 1% after recent deploy"
```

배포 직후 *에러 폭증* 시 자동 알림. *rollback 결정* 의 트리거.

---

## 7. Rollback — *실수했을 때 빨리 되돌리기*

### Git 기반 rollback (GitOps 의 강점)

```bash
# helm-deploy repo
$ git log applications/sparta-chat/values.yaml
abc123 - chore: bump sparta-chat to 7a3f9c2  (HEAD)
def456 - chore: bump sparta-chat to 9b24dec  ← rollback target
xyz789 - chore: bump sparta-chat to 0531376

$ git revert abc123
$ git push
# ArgoCD 가 자동 sync → 옛 버전으로 rollback
```

*매뉴얼 명령* 으로 K8s 만지지 않음. *Git 만 되돌리면* ArgoCD 가 알아서.

### Argo Rollouts 의 자동 rollback

```yaml
spec:
  strategy:
    canary:
      analysis:
        templates:
          - templateName: error-rate-check
        startingStep: 1
      steps:
        - setWeight: 10
        - pause: { duration: 5m }
        - analysis: { templateName: error-rate-check }   # 메트릭 검증
        - setWeight: 50
```

`error-rate-check` 실패 시 *자동으로 이전 버전 복원*.

---

## 8. 내 환경의 deployment harness

```
[Code push] (GitHub: settlement/lemuel-xr/sparta-msa)
       ↓
[GitHub Actions] → Tag: {SHA}-{run_number}
       ↓
[ghcr.io] (immutable tags)
       ↓
[ArgoCD Image Updater] (newest-build, regex allow-tags)
       ↓
[helm-deploy repo] (자동 commit by image-updater)
       ↓
[ArgoCD sync] (auto)
       ↓
[K3s rollout] (Rolling, maxUnavailable=0)
       ↓
[External verification] (sparta-deploy-pipeline-verifier agent)
       ↓
[Grafana annotation] (배포 시점 표시)
       ↓
[Prometheus alert 활성] (PostDeployErrorSpike)
```

5월 17일 사고 이후 *외부 검증 단계* 가 *반드시* 들어감. *Argo Healthy* 만 보지 않고 *chat.lemuel.co.kr/version* 의 SHA 까지 확인.

---

## 9. 흔한 함정 5가지

### ❌ 함정 1: `:latest` 태그

위에서 자세히. *immutable tag* 가 절대 원칙.

### ❌ 함정 2: 트래픽 차단 없이 DB 마이그레이션

```
1. Deploy v2 (마이그레이션 포함)
2. 옛 pod (v1) 이 *마이그레이션된 스키마에서* 실행 → 에러
```

해결: *backward compatible 마이그레이션* (column 추가는 OK, 삭제는 *2 단계*). 또는 *Blue-Green* 으로 옛 버전 완전 종료 후.

### ❌ 함정 3: PreStop / Readiness 없이 rollout

```yaml
# ❌ 트래픽 받자마자 죽음
spec:
  containers:
    - name: app
      ports: [{ containerPort: 8080 }]
```

```yaml
# ✅ readiness + preStop 으로 무중단
spec:
  containers:
    - name: app
      readinessProbe:
        httpGet: { path: /health, port: 8080 }
        initialDelaySeconds: 10
      lifecycle:
        preStop:
          exec:
            command: ["sleep", "15"]  # in-flight 요청 처리 시간
```

### ❌ 함정 4: 환경 차이 (dev / staging / prod)

각 환경의 *값* 만 다르고 *구조* 는 동일해야. Helm `values-dev.yaml` / `values-prod.yaml` 분리.

### ❌ 함정 5: 사람이 *수동 sync*

ArgoCD UI 에서 *수동 sync* 누르는 순간 *GitOps 가 깨짐*. *자동 sync* 가 원칙, 수동은 *비상시만*.

---

## 결론 — Deployment Harness 는 *조용한 안전망*

배포가 *반복 가능하고, 추적 가능하고, 안전하게* 되면:
- 개발자가 *하루에 여러 번* 배포해도 *두렵지 않음*
- 사고 시 *5분 내 rollback*
- *누가 언제 무엇을 배포했는지* 명확
- *외부 사용자에게 도달했는가* 까지 검증

이게 *DevOps / SRE 가 제공하는 진짜 가치*. 개발자가 *자기 일에 집중* 하도록 *배포 과정을 안 보이게* 만드는 인프라.

5월 17일 사고처럼 *내부 신호만 보고 안심* 하다 *외부 사용자가 옛 버전* 받는 사고는 *deployment harness 의 missing layer* 의 증거. *그 layer 를 추가하는 게 SRE 의 일*.

---

## 시리즈 정리 — Harness Engineering 4 가지의 공통 패턴

| 영역 | Harness 의 역할 |
|---|---|
| ① AI Agent | LLM 의 능력을 *증폭* (tool, 권한, 컨텍스트) |
| ② Test | 테스트의 *신뢰와 속도* 를 결정 |
| ③ Software Engineering | 개발자의 *생산성* 을 결정 |
| ④ Deployment | 배포의 *안전성* 을 결정 |

공통 패턴:
1. **자동화** — 사람의 반복 작업을 시스템에 위임
2. **게이트** — 안전 기준 미달 시 *자동 차단*
3. **Observability** — 모든 단계의 *기록 + 메트릭*
4. **회복** — 실수해도 *되돌릴 수단*
5. **표준화** — *팀 / 환경 / 시점이 달라도* 같은 인터페이스

이게 *harness engineering* 의 본질. **시스템의 *반복 가능한 안전* 을 만드는 일**.

내 진로가 백엔드든, SRE 든, AI 엔지니어든 *이 패턴은 동일* 하다. *어느 layer 의 harness 를 짤 것인가* 만 다르다.

---

## 참고

- *Continuous Delivery* — Humble & Farley (2010)
- *Accelerate* — Forsgren, Humble, Kim (2018)
- *Site Reliability Engineering* — Google (2016)
- [ArgoCD 공식 문서](https://argo-cd.readthedocs.io/)
- [Argo Rollouts](https://argoproj.github.io/argo-rollouts/)
- 시리즈 다른 편:
  - [① AI Agent Harness]({% post_url 2026-05-29-harness-engineering-1-ai-agent-claude-code %})
  - [② Test Harness]({% post_url 2026-05-29-harness-engineering-2-test-spring-boot %})
  - [③ Software Engineering Harness]({% post_url 2026-05-29-harness-engineering-3-developer-toolchain %})
