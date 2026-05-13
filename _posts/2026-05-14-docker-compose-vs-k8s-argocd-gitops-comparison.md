---
layout: post
title: "Docker Compose vs Kubernetes + ArgoCD GitOps — 30 개 서비스 운영 비교"
date: 2026-05-14 04:30:00 +0900
categories: [infra, kubernetes, gitops, devops, comparison]
tags: [docker-compose, kubernetes, argocd, gitops, image-updater, helm, comparison]
---

작년까지 docker-compose 로 30 개 서비스를 운영하다가, 두 달 전 K3s + ArgoCD GitOps 로 전환했습니다. 오늘 새벽 한 시간 동안 settlement 앱의 Flyway 마이그레이션 버그를 디버깅하면서, "docker-compose 시절이었다면 어떻게 했을까" 와 "지금은 어떻게 했는가" 가 너무 선명하게 대조돼서 글로 남깁니다.

이 글은 **이론적 비교** 가 아닙니다. 어제 발생한 실제 사고를 두 방식으로 풀어보면서 차이를 정리합니다. 운영 입문자/주니어 분들께 "GitOps 가 왜 좋아?" 라는 질문에 구체적인 답을 드릴 수 있길 바랍니다.

> 이 글에서 다루는 것
> - 같은 사고 (settlement V22 Flyway 중복) 를 두 방식으로 해결하는 시나리오
> - 작업 분류별 어디에 git push 하는지 (4 가지 유형)
> - GitOps 가 더 빠르지 않다는 사실 — 5~10 분이 걸린다
> - 옛 방식에서 더 빨랐던 7 가지 케이스
> - 여전히 수동인 작업 5 가지 (immutable 필드, DB 스키마 충돌 등)
> - 30 개 서비스 운영에서 어느 시점부터 GitOps 가 가치 있는가

---

## 1. 같은 사고를 두 방식으로 풀기 — settlement V22 Flyway 중복

새벽 1 시. settlement-prod 의 모든 pod 가 CrashLoopBackOff. 로그:

```
Caused by: org.flywaydb.core.api.FlywayException:
  Found more than one migration with version 22
Offenders:
-> V22__add_settlement_query_indexes.sql
-> V22__performance_indexes.sql
```

소스 코드에 동일 버전 마이그레이션 두 개가 들어가 있어서 Flyway 가 거부.

### 1.1 docker-compose 였다면

```bash
# 1. SSH 로 운영 서버 접속
ssh ops@prod-server-1

# 2. 코드 직접 수정
cd /opt/settlement
git pull origin main
git checkout -b hotfix/v22-duplicate
git mv V22__add_settlement_query_indexes.sql V45__add_settlement_query_indexes.sql

# 3. 이미지 직접 빌드
docker-compose build settlement-app

# 4. 적용
docker-compose up -d settlement-app

# 5. 다른 서버에도 동일하게 (만약 3 노드 분산이라면)
ssh ops@prod-server-2 ...
ssh ops@prod-server-3 ...

# 6. git 에 fix 커밋, 푸시 (나중에)
git commit -am "hotfix"
git push
```

문제점:

- **서버마다 수동** — 노드 3 개면 3 번 반복
- **추적 안 됨** — "누가 언제 prod-server-2 의 settlement-app 만 1.5.2 로 박았지?" 가 안 보임
- **GA 안 됨** — git 푸시 안 하고 까먹으면 (운영 중엔 흔함) 다음 재배포 시 원복
- **다른 서버 누락** — 6 번을 잊으면 노드마다 다른 코드가 돌아감

### 1.2 GitOps 였다면 (= 어제 새벽 한 일)

```bash
# 1. 로컬에서 git worktree (운영 서버 SSH 한 번도 안 들어감)
git worktree add /tmp/settlement-fix origin/main -b fix/duplicate-flyway-migrations
cd /tmp/settlement-fix
git mv .../V22__... .../V45__...

# 2. PR 오픈
git push -u origin fix/duplicate-flyway-migrations
gh pr create --base main ...

# 3. PR 머지
gh pr merge --squash --admin
```

이후는 자동:

```
PR 머지
   ↓
GitHub Actions CI 실행 (build, test, jacoco, sonarcloud)
   ↓
docker build + push 'ghcr.io/myoungsoo7/settlement:main-<sha>'
   ↓
ArgoCD image-updater (2 분 polling) 가 새 이미지 감지
   ↓
ArgoCD Application 의 helm.parameters 자동 업데이트 (write-back-method: argocd)
   ↓
ArgoCD selfHeal 이 Deployment spec 변경 감지
   ↓
Kubernetes rolling update (maxSurge: 1, maxUnavailable: 0)
   ↓
새 pod startup → readiness probe 통과 → 옛 pod terminate
   ↓
끝.
```

수동 작업: **1 회** (PR 머지 클릭).
전체 시간: **머지 후 10 분**.

특이점:

- SSH 0 회
- kubectl apply 0 회
- 노드 마다 수동 작업 0 회 (rolling update 가 알아서)
- git 추적: 100% — PR/commit/이미지 태그/Application sync 가 다 git 에 묶임

### 1.3 비교

| 항목 | docker-compose | GitOps |
|---|---|---|
| 작업 단계 | 6 단계, 노드마다 반복 | 3 단계, 1 회 |
| SSH | 노드 수만큼 | 0 회 |
| 적용 시간 | 즉시 (수 분) | 5-10 분 |
| 추적성 | 수동 (잘 안 됨) | 100% git |
| 노드 동기 | 수동 | 자동 |
| 휴먼 에러 위험 | 높음 | 낮음 |

GitOps 가 더 **느립니다** (5-10 분 대 즉시). 대신 **추적/롤백/자동화** 가 압도적입니다.

---

## 2. 작업 종류별 어디에 push 하는가

GitOps 에서 "git push 하면 자동 배포된다" 는 말은 단순화입니다. 실제론 4 종류의 변경이 있고 각각 다른 repo / 다른 path 에 push 합니다.

### 2.1 앱 코드 변경

비즈로직, API 추가, 버그 수정 등.

```
push to: app repo (예: github.com/MyoungSoo7/settlement)
파이프라인: app repo → ghcr.io → image-updater → ArgoCD → pod
관여하는 자동화: GitHub Actions, image-updater, ArgoCD selfHeal
```

옛 방식: `docker-compose build && docker-compose up -d` 매 서버마다.

### 2.2 인프라 / 배포 설정

리소스 limits, env 변수, probe 경로, replica 수 등.

```
push to: helm-deploy repo, charts/<app>/values*.yaml
파이프라인: helm-deploy → ArgoCD chart diff 감지 → 자동 sync
```

옛 방식: docker-compose.yml 직접 수정 후 `docker-compose up -d`.

### 2.3 새 서비스 추가

서비스 전체 도입.

```
push to: helm-deploy repo, argocd-applications/new-app.yaml + charts/new-app/
파이프라인: root-app (App-of-Apps) 이 새 Application CR 자동 생성 → 자식 Application 이 차트 watch 시작
```

옛 방식: docker-compose.yml 에 service 블록 추가 후 `docker-compose up -d`. **수동 작업 단계 동일.**

### 2.4 ArgoCD Application 자체의 스펙 변경

selfHeal flip, valueFiles 추가, image-updater annotation 등.

```
push to: helm-deploy repo, argocd-applications/<app>.yaml
파이프라인: root-app 이 자동 patch (App-of-Apps 의 selfHeal=true)
```

옛 방식: 이 개념 자체가 없음 — docker-compose 엔 "메타 배포 설정" 이라는 레이어가 없음.

### 2.5 어떻게 외우는가

| 변경의 성격 | repo |
|---|---|
| "이 앱의 동작이 바뀜" | app repo |
| "이 앱의 배포 방식이 바뀜" | helm-deploy / charts/ |
| "새 앱 추가/제거" | helm-deploy / argocd-applications/ |
| "ArgoCD 가 이 앱을 어떻게 관리하는지" | helm-deploy / argocd-applications/<app>.yaml |

이게 익숙해지면 docker-compose 시절의 "한 파일에 다 박혀있는 단순함" 이 그리워지지만 — 동시에 "분리되어서 좋다" 도 느낍니다.

---

## 3. GitOps 가 옛 방식보다 느린 7 가지 케이스

균형 잡힌 비교를 위해 GitOps 가 손해 보는 케이스도 정리합니다.

### 3.1 즉시 디버깅 patch 가 필요할 때

```
# 옛: 즉시 (10 초)
ssh prod && docker-compose run --rm -e DEBUG=true settlement-app sh

# GitOps: 5~10 분
git checkout -b debug-temp
# 수정
git commit && git push
# PR 생성, CI 통과, 머지, image-updater, ArgoCD reconcile
# 5-10 분 후에야 디버깅 시작
```

긴 CI 가 디버깅 속도를 죽입니다. 우회법: 임시로 `kubectl exec` + 로컬 도구. 하지만 GitOps 정신에 반함.

### 3.2 한 노드에서만 빠르게 테스트하고 싶을 때

```
# 옛: docker-compose --profile experiment up -d
# GitOps: 전 클러스터에 영향 — staging/canary 분리 필요
```

K8s 에선 canary deployment (Argo Rollouts, Flagger) 가 별도 도구. docker-compose 의 단순한 "프로필" 같은 게 없음.

### 3.3 단일 노드 / 학습 환경

K3s 만 해도 etcd, kube-proxy, coredns 등 베이스 RSS 1GB+. 라즈베리파이 같은 작은 노드에서 1 앱만 돌릴 거면 docker-compose 가 훨씬 가볍.

### 3.4 외부 노출 안 되는 1 회성 서비스

ad-hoc 데이터 마이그레이션 job 같은 거. 옛엔 `docker-compose run --rm migrate` 한 줄. K8s 에선 Job CR + 차트 + ArgoCD = 과한 인프라.

K8s 에선 `kubectl create job` 으로 인라인 한 줄 가능하지만 — 그건 GitOps 가 아닌 라이브 patch.

### 3.5 환경변수 즉시 변경

```
# 옛: docker-compose 의 .env 수정 + restart
# GitOps: values 수정 + PR (또는 라이브 kubectl set env, 단 selfHeal 이 원복 위험)
```

settlement-staging 에서 어제 이 함정을 그대로 겪었습니다. selfHeal=true 가 켜진 채 라이브로 env 12 개를 patch 했더니, sync 트리거 시 모두 사라짐. 영구화 commit 필요.

### 3.6 빠른 롤백 시나리오

```
# 옛: docker-compose pull <old-tag> && docker-compose up -d
#     30 초

# GitOps: git revert + push + CI + image-updater + ArgoCD
#         10 분
```

긴급 롤백이 필요할 때 GitOps 의 자동화 사슬이 오히려 발목을 잡습니다. ArgoCD UI 에서 직접 rollback 버튼을 누르면 즉시 가능하지만 — 그건 git 우회.

### 3.7 비용 (학습 + 인프라)

- docker-compose: 학습 1 주, 인프라 0 원 (단일 VM)
- K8s + ArgoCD: 학습 1~3 개월, 인프라 노드 비용 + 마스터 노드 RAM 2GB

10 개 미만 서비스로 단일 팀이 운영한다면, docker-compose 가 절대 손해 아닙니다.

---

## 4. 여전히 수동인 작업 5 가지

GitOps 도 만능이 아닙니다. "git push 만 하면 다 됨" 은 거짓말입니다. 어제 settlement 디버깅에서 만난 5 종류의 예외:

### 4.1 DB 스키마 충돌 해소

```
ERROR: relation "orders" already exists
```

이미 만든 테이블 vs Flyway 마이그레이션 충돌. 해결: 직접 DB 접속 후 `DROP TABLE flyway_schema_history` + BASELINE_VERSION 조정.

git push 로는 못 함. **라이브 SQL 1 회 필수.**

### 4.2 1 회성 Secret 생성

기밀값 (API key, JWT secret 등) 을 git 에 못 박을 때. Sealed Secrets / SOPS / External Secrets Operator 같은 도구로 GitOps 화 가능하지만, 초기 셋업 비용 큼.

해결: `kubectl create secret generic ...` 1 회. 그 다음부턴 ArgoCD 가 secretRef 만 git 으로 관리.

### 4.3 PV/PVC 의 immutable 필드

StatefulSet 의 volumeClaimTemplates 의 storageClassName, accessModes 같은 필드는 immutable. ArgoCD 가 변경 시도 → API server 가 거부 → sync 영구 실패.

해결: 라이브 STS 와 차트가 일치하도록 git 을 라이브로 맞추거나, STS 를 cascade=orphan 으로 삭제 후 재생성.

### 4.4 인증서 / DNS

Cloudflare Tunnel 경로, DNS 레코드, TLS 인증서. cert-manager + DNS01 challenge 로 GitOps 화 가능하지만, 어제 lemuel.co.kr 같은 케이스는 Cloudflare 대시보드에서 수동.

### 4.5 노드 레벨 (디스크 마운트, 노드 라벨, ufw)

K3s 자체의 OS-level 설정. 노드 추가/제거, mkfs, mount, fstab, ufw allow 등. 이건 본질적으로 노드 SSH 작업.

자동화하려면 Ansible/Terraform + cloud-init 까지 가야 함.

---

## 5. 언제 GitOps 가 가치 있는가

저는 30 개 서비스 운영하면서 GitOps 의 손익분기점을 이렇게 봅니다.

| 서비스 수 | 추천 |
|---|---|
| 1-5 | docker-compose — GitOps 의 학습/인프라 비용 회수 불가 |
| 5-15 | 분기점. 팀 규모와 변경 빈도에 따라 |
| 15-30 | GitOps 가 명확히 우위 |
| 30+ | GitOps 없이는 운영 불가능 — 추적/롤백/일관성이 사람으로 안 됨 |

또 다른 기준:

- **혼자 운영**: 30 개도 docker-compose 가능 (단, 좋은 기억력 필요)
- **2-3 명 팀**: 10 개부터 GitOps 가 협업 마찰을 줄임
- **5명+**: 무조건 GitOps. "누가 prod 의 뭘 바꿨지?" 가 일상 질문이 됨

저는 30 개 서비스 + 1 명 (저) 운영입니다. docker-compose 로도 했었고, 1 년 운영해 본 결과 **GitOps 가 더 편함** 결론. 손해 보는 부분 (느린 디버깅, 학습 곡선) 보다 이득 (추적, 자동 일관성, 롤백, 휴먼 에러 0) 이 더 큰 것 같습니다.

특히 어제 새벽 한 시간 짜리 사고를 SSH 한 번도 안 들어가고 PR 두 개로 푼 경험은 — docker-compose 시절에는 불가능했을 일입니다. 노드 3 개를 새벽에 SSH 들어가서 똑같은 git pull + docker-compose build 를 3 번 했을 거고, 그 와중에 한 노드에서만 빌드 에러 났을 거고, 그 노드만 옛 상태 남아있어서 다음 날 일관성 깨진 채로 운영됐을 겁니다.

---

## 6. 정리 — 한 페이지 요약

```
GitOps 의 본질:
  "클러스터 상태 = git 의 상태" 라는 단일 진실의 원천.

비용:
  - 학습 1-3 개월
  - 인프라 마스터 노드 RAM 2GB+
  - 적용 속도 5-10 분 (docker-compose 즉시 대비)

이득:
  - 추적: 모든 변경이 git log
  - 롤백: git revert 1 줄
  - 자동 일관성: 노드별 차이 0
  - 휴먼 에러: SSH 안 들어가니까 0
  - 협업: PR review 로 변경 검토

손익분기점:
  - 서비스 15 개 이상
  - 팀 2 명 이상
  - 변경 주 1 회 이상

여전히 수동:
  - DB 스키마 충돌
  - 1 회성 Secret
  - immutable 필드 drift
  - DNS / 인증서 (cert-manager 도입 전)
  - 노드 OS-level 작업
```

---

## 7. 마무리 — 그래도 git push 가 답인 이유

어제 새벽 settlement 사고 1 시간 동안 제가 한 일:

1. PR #65 (CI MODULE build-arg) 머지 — 1 분
2. CI 실행 대기 — 4 분
3. 새 이미지에서 V10 중복 발견 — 2 분 로그 분석
4. PR #66 (V10/V12 영구화) 자동 작성 + 머지 — 3 분
5. CI 재실행 + 이미지 푸시 — 5 분
6. image-updater pickup + 새 pod rollout — 5 분
7. staging 의 BASELINE_VERSION + flyway_schema_history DROP — 5 분

**총 25 분, SSH 1 회 (DB SQL 1 회), kubectl 0 회.**

docker-compose 시절이었다면:

1. SSH 노드 3 개 각각 접속 — 10 분
2. 코드 수정 후 노드별 빌드 — 노드당 5 분 × 3 = 15 분
3. 한 노드에서 빌드 에러 (메모리 부족, OS 패키지 차이 등) — 디버깅 30 분
4. 빌드 완료 후 docker-compose up — 5 분
5. 한 노드 누락 발견 — 추가 15 분
6. V10 중복 또 발견 — 위 단계 반복

**총 2~3 시간, SSH 6 회+, 새벽 절망 N 회.**

GitOps 의 첫 5 분 (PR 만들고 머지하기) 가 docker-compose 의 마지막 1 시간 (모든 노드 동기화) 보다 길게 느껴질 수 있습니다. 하지만 총 시간은 5 배 빠릅니다. 그리고 잠을 잘 수 있습니다.

새벽 4 시에 클러스터 상태를 git log 로 확인하면서 자고, 깨어나서 "어, 정상이네" 하고 시작하는 하루는 — docker-compose 시대엔 없던 평화입니다.

다음 글에서는 이번 사고의 핵심이었던 **image-updater + write-back-method=argocd 패턴** 을 더 깊이 다룰 예정입니다. ArgoCD Application 의 helm.parameters 를 image-updater 가 자동 갱신하는 메커니즘과, 그게 깨졌을 때의 복구법에 대한 이야기입니다.
