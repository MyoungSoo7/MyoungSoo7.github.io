---
layout: post
title: "Jenkins vs GitHub Actions — Docker 빌드부터 Kubernetes 배포까지 자동화 실전 비교"
date: 2026-05-15 15:30:00 +0900
categories: [devops, ci-cd, kubernetes]
tags: [jenkins, github-actions, docker, kubernetes, argocd, gitops, ghcr, helm]
---

CI/CD 도구를 처음 고르는 분, 또는 Jenkins 만 알다가 GitHub Actions 로 넘어가려는 분, 반대로 Actions 만 써본 분이 사내 Jenkins 와 마주쳤을 때 — 결국 같은 질문에 부딪힙니다. **"내 코드 push 가 어떻게 컨테이너가 되고, 어떻게 Pod 으로 돌아가나?"**

이 글은 그 한 줄을 끝까지 따라가는 글입니다. 30 개 서비스를 GitHub Actions + GHCR + ArgoCD 로 운영하면서 정리한 실전 파이프라인, 그리고 같은 일을 Jenkins Declarative Pipeline 으로 짰을 때의 비교까지 다룹니다.

> 이 글에서 다루는 것
> - CI/CD 파이프라인의 4 단계 (Build → Test → Push → Deploy) 를 도구 무관하게 이해하기
> - GitHub Actions 실전 워크플로우 (실제로 30 개 서비스에 쓰는 패턴)
> - Jenkins Declarative Pipeline 으로 같은 일을 짜는 법
> - 두 도구의 차이를 8 가지 관점에서 비교 (러너, 시크릿, 캐싱, 비용, …)
> - Docker 이미지 빌드 모범 사례 (multi-stage, buildx, cache mount, immutable tags)
> - CD 의 두 갈래 — `kubectl apply` push 모델 vs ArgoCD pull (GitOps) 모델
> - 보안 — OIDC, registry credentials, image pull secret, SOPS

---

## 1. 큰 그림 — CI/CD 는 4 단계의 컨베이어 벨트

도구가 무엇이든 (Jenkins, GitHub Actions, GitLab CI, ArgoCD, Tekton, …) 결국 다음 4 단계입니다:

```
[1. Build]  ──>  [2. Test]  ──>  [3. Push]  ──>  [4. Deploy]
 소스 컴파일      유닛/통합        레지스트리      클러스터로
 + 이미지 생성    테스트 통과      이미지 업로드   롤아웃
```

이 4 단계 중 **1~3 을 CI(Continuous Integration)**, **4 를 CD(Continuous Delivery/Deployment)** 라고 부릅니다. 도구를 비교할 때는 항상 "그 도구가 이 4 단계 중 어디까지 책임지나" 를 먼저 물어야 합니다.

- **Jenkins**: 1~4 전부 가능 (전통적으로 `kubectl apply` 까지 직접 했음).
- **GitHub Actions**: 1~3 까지 자연스럽고, 4 는 가능하지만 부자연스러움. CD 는 ArgoCD/Flux 같은 GitOps 컨트롤러에 위임하는 추세.
- **ArgoCD**: 오직 4. CI 가 뱉어낸 이미지/매니페스트를 클러스터로 흘려보내는 일에 특화.

→ 모던 스택은 **GitHub Actions(CI) + ArgoCD(CD)** 조합이 표준이 되어가는 중. 이 글에서도 이 패턴이 중심입니다.

---

## 2. GitHub Actions 실전 — 1 개 파일로 끝나는 CI

제가 운영 중인 `inter-asat` 리포의 실제 워크플로우입니다.

```yaml
# .github/workflows/k3s-images.yml
name: Build K3s images

on:
  push:
    branches: [master, main]
  workflow_dispatch:

env:
  REGISTRY: ghcr.io
  BACKEND_IMAGE: ghcr.io/myoungsoo7/inter-asat-backend
  FRONTEND_IMAGE: ghcr.io/myoungsoo7/inter-asat-frontend

jobs:
  backend:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write           # ghcr.io 푸시 권한
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}   # ← 시크릿 발급 불필요
      - uses: docker/build-push-action@v6
        with:
          context: .
          file: Dockerfile.backend
          push: true
          tags: |
            ${{ env.BACKEND_IMAGE }}:latest
            ${{ env.BACKEND_IMAGE }}:${{ github.sha }}
          cache-from: type=gha,scope=inter-asat-backend
          cache-to: type=gha,mode=max,scope=inter-asat-backend

  frontend:
    runs-on: ubuntu-latest
    # ... 동일 패턴 ...
```

### 2.1 이 한 파일이 하는 일

- `master` 에 push 되는 순간 GitHub 가 ubuntu-latest VM 한 대를 띄움 (무료, 2 코어/7GB).
- buildx 로 Docker 이미지를 multi-platform 빌드.
- `GITHUB_TOKEN` 으로 자동 로그인 (별도 PAT 발급/관리 X).
- `ghcr.io/myoungsoo7/inter-asat-backend:latest` 와 `:<sha>` 두 태그로 push.
- `type=gha` 캐시 — 이전 레이어를 GitHub Actions 자체 캐시에 저장 → 두 번째 빌드부터 절반 이상 빨라짐.

**파일 1 개 = 무료 러너 + 자동 인증 + 빌드 캐시 + 이미지 푸시.** Jenkins 로 같은 일을 하려면 (a) Jenkins 서버, (b) Docker-in-Docker agent, (c) credentials 관리, (d) buildx 설치, (e) 캐시 볼륨까지 직접 세팅해야 합니다. 신규 프로젝트 1 개당 30 분~1 시간이 GitHub Actions 에서는 5 분.

### 2.2 매트릭스 빌드와 병렬화

```yaml
strategy:
  matrix:
    service: [api, worker, scheduler]
jobs:
  build:
    steps:
      - uses: docker/build-push-action@v6
        with:
          file: ${{ matrix.service }}/Dockerfile
          tags: ghcr.io/foo/${{ matrix.service }}:${{ github.sha }}
```

3 개 서비스가 **병렬** 로 빌드됩니다. Jenkins 의 `parallel { }` 블록과 동등한 일이지만, 선언적이라 읽기 쉬워요.

---

## 3. Jenkins 실전 — Declarative Pipeline 으로 같은 파이프라인

같은 일을 Jenkins 로 짜면 이렇습니다.

```groovy
// Jenkinsfile
pipeline {
  agent {
    kubernetes {
      yaml '''
        apiVersion: v1
        kind: Pod
        spec:
          containers:
          - name: buildkit
            image: moby/buildkit:latest
            securityContext: { privileged: true }
          - name: kubectl
            image: bitnami/kubectl:1.30
            command: ['cat']
            tty: true
      '''
    }
  }

  environment {
    REGISTRY      = 'ghcr.io'
    BACKEND_IMAGE = 'ghcr.io/myoungsoo7/inter-asat-backend'
    GIT_SHA       = "${env.GIT_COMMIT.take(7)}"
  }

  stages {
    stage('Checkout') {
      steps { checkout scm }
    }

    stage('Build & Push backend') {
      steps {
        container('buildkit') {
          withCredentials([usernamePassword(
              credentialsId: 'ghcr-creds',
              usernameVariable: 'GHCR_USER',
              passwordVariable: 'GHCR_PASS')]) {
            sh '''
              mkdir -p ~/.docker
              echo "{\\"auths\\":{\\"$REGISTRY\\":{\\"auth\\":\\"$(printf %s "$GHCR_USER:$GHCR_PASS" | base64)\\"}}}" > ~/.docker/config.json
              buildctl build \\
                --frontend dockerfile.v0 \\
                --local context=. \\
                --local dockerfile=. \\
                --opt filename=Dockerfile.backend \\
                --output type=image,name=$BACKEND_IMAGE:$GIT_SHA,push=true \\
                --export-cache type=registry,ref=$BACKEND_IMAGE:cache \\
                --import-cache type=registry,ref=$BACKEND_IMAGE:cache
            '''
          }
        }
      }
    }

    stage('Deploy') {
      steps {
        container('kubectl') {
          withKubeConfig([credentialsId: 'k3s-prod-kubeconfig']) {
            sh '''
              kubectl set image -n asat-prod \\
                deployment/inter-asat-backend \\
                backend=$BACKEND_IMAGE:$GIT_SHA
              kubectl rollout status -n asat-prod deployment/inter-asat-backend --timeout=5m
            '''
          }
        }
      }
    }
  }

  post {
    failure {
      mail to: 'iamipro@naver.com', subject: "FAIL: ${env.JOB_NAME} #${env.BUILD_NUMBER}",
           body: "${env.BUILD_URL}"
    }
  }
}
```

### 3.1 Jenkins 가 더 잘하는 것

- **에이전트 토폴로지의 자유도**: 위 예시처럼 빌드 단계는 buildkit 컨테이너에서, 배포 단계는 kubectl 컨테이너에서 — 한 파이프라인 안에서 다른 환경을 자연스럽게 섞을 수 있음.
- **공유 라이브러리(Shared Library)**: Groovy 로 짠 공통 함수를 모든 파이프라인이 import. 매트릭스 빌드 100 개가 있을 때 GitHub Actions 의 reusable workflow 보다 더 표현력이 높음.
- **장기 빌드/플로팅 빌드**: 12 시간짜리 e2e, 야간 회귀 테스트 같은 거 — Jenkins 가 더 안정적. GitHub Actions 의 job 최대 시간은 6 시간 (self-hosted runner 만 무제한).
- **온프레미스/에어갭 환경**: 외부 인터넷 차단된 사내망에서 CI 가 필요할 때 GitHub Actions 는 self-hosted runner + private GHCR 미러까지 손이 많이 가는 반면, Jenkins 는 그냥 깔면 됨.

### 3.2 Jenkins 가 더 못하는 것

- **러너 관리 부담**: Jenkins controller + agent 노드 자체를 운영해야 함. GitHub-hosted runner 처럼 "그냥 무제한으로 띄움" 이 불가능.
- **선언적 vs 명령형의 어중간함**: Declarative Pipeline 도 결국 Groovy. YAML 만큼 단순하지 않고, 그렇다고 풀 Groovy 만큼 자유롭지도 않은 어중간한 영역.
- **플러그인 카오스**: 1,800 개 플러그인, 호환성 매트릭스가 악몽. Jenkins 업그레이드 한 번에 사용 중인 플러그인 5 개가 깨지는 일이 흔함.
- **시크릿 UX**: Credentials 플러그인 UI 가 2010년대 후반에서 멈춰있음. GitHub Actions 의 `secrets.*` + OIDC 조합이 훨씬 모던.

---

## 4. 8 가지 관점에서 비교

| 관점 | Jenkins | GitHub Actions |
|---|---|---|
| **인프라 부담** | 컨트롤러 + 에이전트 직접 운영 | 0 (GitHub hosted) ~ self-hosted 옵션 |
| **러너 비용** | 직접 서버 비용 | public repo 무료, private repo 분당 과금 (Linux $0.008) |
| **워크플로우 정의** | Groovy (Declarative/Scripted) | YAML |
| **시크릿** | Credentials 플러그인 | `secrets.*` + OIDC (AWS/GCP/Azure 무자격증명) |
| **레지스트리 인증** | 별도 토큰 관리 | `GITHUB_TOKEN` 으로 GHCR 자동 |
| **캐시** | 외부 (S3, registry) 직접 구성 | `type=gha` 내장 + 외부 옵션 |
| **병렬화** | `parallel { }`, matrix 가능 | `strategy.matrix` 매우 자연스러움 |
| **외부 통합** | 1,800 개 플러그인 (양날) | 100,000+ Action (양날) |

→ **신규 프로젝트 / 클라우드 네이티브**: GitHub Actions 가 압도적으로 빠르고 가벼움.<br>
→ **레거시 / 사내 보안망 / 복잡한 빌드 토폴로지**: Jenkins 가 여전히 의미 있음.

---

## 5. Docker 이미지 빌드 모범 사례 (도구 무관)

어느 도구를 쓰든 결국 `docker build` 입니다. 이 단계의 시간이 곧 CI 시간이라 다음 4 가지는 반드시 챙기세요.

### 5.1 Multi-stage build

```dockerfile
# Dockerfile.backend
FROM gradle:8.10-jdk21 AS builder
WORKDIR /app
COPY build.gradle.kts settings.gradle.kts ./
COPY gradle ./gradle
RUN gradle dependencies --no-daemon       # ← 의존성만 먼저 (캐시 효율)
COPY src ./src
RUN gradle bootJar --no-daemon

FROM eclipse-temurin:21-jre-alpine
WORKDIR /app
COPY --from=builder /app/build/libs/*.jar app.jar
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "/app/app.jar"]
```

- builder 단계: JDK + Gradle 포함, 800MB+.
- 최종 단계: JRE alpine 만, 180MB.
- 부수효과: 빌드 도구가 런타임 이미지에 남지 않아 공격 표면 축소.

### 5.2 의존성 → 소스 순서로 COPY

위 예시처럼 `build.gradle.kts` → `gradle dependencies` → `src` 순서. 소스만 바뀌어도 의존성 레이어는 그대로 캐시 히트.

### 5.3 BuildKit 캐시 마운트 (게임 체인저)

```dockerfile
# syntax=docker/dockerfile:1.7
RUN --mount=type=cache,target=/root/.gradle \
    gradle bootJar --no-daemon
```

`--mount=type=cache` 는 빌드 사이에 Gradle 캐시(`~/.gradle`) 를 유지. CI 환경에서 의존성 다시 다운로드하지 않게 됨. 빌드 시간이 5 분 → 1 분으로 줄어드는 일이 흔합니다.

### 5.4 Immutable 태그 — `:latest` 만 쓰지 마세요

```bash
docker build -t myimg:latest -t myimg:$(git rev-parse --short HEAD) .
```

- `:latest` 만 쓰면 "어제 잘 됐는데 오늘 안 돼" 라는 가장 흔한 사고가 발생. Pod 이 재기동될 때 다른 이미지를 받아옴.
- 항상 **commit SHA** 같은 immutable 태그를 함께 push.
- Kubernetes manifest 에는 `:latest` 가 아닌 `:<sha>` 또는 `:<semver>` 만 참조 → Pod 재기동 시 같은 이미지가 보장됨.

---

## 6. CD — 두 갈래 길

이제 이미지가 레지스트리에 올라왔습니다. **이걸 어떻게 클러스터로 흘려보낼 것인가** 가 CD 의 핵심.

### 6.1 Push 모델 — CI 가 `kubectl apply`

전통적인 Jenkins 패턴입니다.

```groovy
stage('Deploy') {
  steps {
    sh '''
      kubectl set image -n asat-prod \
        deployment/backend backend=$IMAGE:$GIT_SHA
      kubectl rollout status -n asat-prod deployment/backend --timeout=5m
    '''
  }
}
```

**장점**:
- 직관적. `git push` → CI 종료 시점에 이미 배포 완료.
- 외부 도구 없이 끝남.

**단점**:
- CI 가 클러스터 자격증명(kubeconfig) 을 가져야 함 → 보안 표면.
- CI 환경이 클러스터에 IP/방화벽으로 도달 가능해야 함.
- 클러스터 실제 상태와 Git 의 desired 상태가 일치한다는 보장이 없음 (누가 `kubectl edit` 하면 끝).

### 6.2 Pull 모델 — GitOps (ArgoCD/Flux)

```
[GitHub Actions]  →  [GHCR]
       │
       ↓ (이미지 빌드 후 manifest repo 의 image tag 만 갱신)
[helm-deploy repo]  ←─  watch  ─→  [ArgoCD in cluster]
                                          │
                                          ↓ sync
                                    [Kubernetes 클러스터]
```

CI 는 이미지를 push 하고 끝. 클러스터로 가는 push 가 없습니다. 대신:

- 클러스터 안의 ArgoCD 가 helm-deploy 리포를 watch.
- 매니페스트의 image tag 가 바뀌면 자동 sync (또는 PR 머지 시).
- 클러스터 상태 = git 상태 (selfHeal).

**장점**:
- CI 에 클러스터 자격증명 0개. CI 가 털려도 클러스터에 직접 영향 없음.
- desired state 가 git 에 명시적으로 박혀있음 → 누가 손으로 바꿔도 ArgoCD 가 되돌림.
- 멀티 클러스터 / 멀티 환경 확장이 자연스러움 (각 클러스터의 ArgoCD 가 같은 repo 의 다른 path 를 봄).

**단점**:
- 배포가 즉시 아님. 짧게는 30 초, 길게는 ArgoCD polling 주기(3 분) 후 적용.
- 초기 학습 곡선. Application CR, App-of-Apps, sync wave, hooks…
- "왜 안 됐지" 디버깅 시 CI 로그 + ArgoCD 로그 + 클러스터 이벤트 3 군데 봐야 함.

### 6.3 어느 쪽을 골라야 하나

| 상황 | 권장 |
|---|---|
| 1~3 개 서비스, 1 개 클러스터 | Push 모델로 충분 |
| 10+ 서비스 또는 멀티 클러스터 | GitOps (Pull) 로 가야 함 |
| 빠른 핫픽스가 필수인 환경 | Push (CD 5 초 vs 30+ 초) |
| 감사 추적/규제 산업 | Pull (git = audit log) |
| CI 에 클러스터 자격증명 주기 싫음 | Pull |

저는 30 개 서비스 운영 시점부터 Pull(ArgoCD) 로 갈아탔고, 더는 push 모델로 돌아갈 일이 없을 것 같습니다.

---

## 7. 실전: GitHub Actions + GHCR + ArgoCD 풀스택 흐름

제 홈랩에서 실제로 흘러가는 파이프라인 전체:

```
개발자 git push
   │
   ↓
inter-asat 리포 (GitHub)
   │
   ↓ workflow trigger
GitHub Actions (ubuntu-latest)
   ├── docker buildx build
   ├── ghcr.io 로그인 (GITHUB_TOKEN)
   └── push ghcr.io/.../backend:<sha>
   │
   ↓ (선택) Image Updater 또는 PR 봇이
helm-deploy 리포의 charts/asat/values.yaml 의 tag 갱신
   │
   ↓ ArgoCD root-app 가 watch
ArgoCD (K3s in cluster)
   ├── helm-deploy/charts/asat 새 manifest 적용
   ├── selfHeal: true
   └── sync: kubectl apply 동등
   │
   ↓
asat-prod ns 의 Deployment 가 새 이미지로 롤링 업데이트
   │
   ↓ Pod imagePullSecret(ghcr-pull) 사용
GHCR 에서 :<sha> 이미지 pull
   │
   ↓
새 Pod Ready, 옛 Pod 종료 (maxSurge/maxUnavailable 따라)
```

이 흐름에서 가장 중요한 두 가지 보안 포인트:

### 7.1 OIDC 로 클라우드 자격증명 제거

```yaml
permissions:
  id-token: write        # OIDC 발급용
  contents: read
  packages: write

steps:
  - uses: aws-actions/configure-aws-credentials@v4
    with:
      role-to-assume: arn:aws:iam::123:role/github-actions
      aws-region: ap-northeast-2
```

GitHub Actions 의 OIDC 토큰으로 AWS IAM 역할을 가정. **AWS access key 를 GitHub secrets 에 넣지 마세요**. OIDC 가 표준입니다.

### 7.2 ImagePullSecret

private GHCR 이미지를 pull 하려면 클러스터에 인증이 필요합니다.

```bash
kubectl -n asat-prod create secret docker-registry ghcr-pull \
  --docker-server=ghcr.io \
  --docker-username=myoungsoo7 \
  --docker-password=<PAT_with_read:packages> \
  --docker-email=iamipro@naver.com
```

그리고 Deployment 에서:

```yaml
spec:
  template:
    spec:
      imagePullSecrets:
        - name: ghcr-pull
      containers:
        - name: backend
          image: ghcr.io/myoungsoo7/inter-asat-backend:abc1234
```

이 secret 자체도 SOPS 로 암호화해서 helm-deploy 리포에 commit 하면 GitOps 일관성 유지. (제 [SOPS 글](/2026/05/14/) 참고.)

---

## 8. 자주 만나는 함정 6 가지

### 8.1 `:latest` 만으로 배포
앞에서 강조했지만 가장 흔합니다. K8s 의 `imagePullPolicy: IfNotPresent` 때문에 같은 태그면 노드 캐시에서 옛 이미지를 그대로 씀. 새 이미지가 push 됐어도 Pod 가 재기동돼야만 적용되고, 재기동돼도 노드별로 다른 이미지가 뜨는 일이 생김.

→ **항상 immutable 태그**.

### 8.2 CI 가 통과했는데 prod 에서만 실패
- CI 의 Docker 베이스 이미지와 prod 베이스 이미지가 다르거나 (예: alpine vs debian)
- CI 의 환경변수와 prod 의 ConfigMap/Secret 이 다름
- CI 가 root, prod 가 non-root (read-only filesystem 등)

→ **CI 에서도 prod 와 동일한 이미지로 smoke test** 실행. 가능하면 K3s/kind 띄워서 진짜 K8s 위에서 한 번 띄워봄.

### 8.3 빌드 캐시가 안 먹힘
- `COPY . .` 한 줄을 너무 위에 둠. 소스 한 줄만 바뀌어도 모든 후속 레이어가 무효화.
- `RUN apt-get update && apt-get install` 한 줄을 분리. `update` 만 캐시 되면 stale 패키지 인덱스로 깨짐.

→ 의존성 → 소스 순서, install/update 는 항상 한 RUN 안에서.

### 8.4 GitHub Actions 시크릿이 fork PR 에서 새는 줄 알았는데
fork 에서 온 `pull_request` 이벤트는 secrets 가 자동으로 마스킹/제거됩니다. 그러나 `pull_request_target` 트리거는 base 브랜치 권한으로 돌기 때문에 fork 의 악성 코드가 secrets 에 닿을 수 있음.

→ `pull_request_target` 은 매우 신중하게. checkout 할 때 SHA 를 명시적으로 고정.

### 8.5 Jenkins agent 가 Docker socket 마운트
빌드를 위해 호스트의 `/var/run/docker.sock` 을 마운트하는 경우, 그 agent 가 털리면 호스트 자체를 장악당함.

→ rootless docker, 또는 Kaniko/BuildKit 같은 daemonless 빌더 사용.

### 8.6 Rollout 실패 시 CI 가 success 로 끝남
`kubectl set image` 만 하고 `rollout status` 를 안 부르면, 새 ReplicaSet 이 CrashLoopBackOff 인 채로 CI 는 초록색.

→ 반드시 `kubectl rollout status --timeout=5m`. 실패하면 자동 rollback 까지 (`kubectl rollout undo`).

---

## 9. 결론 — 어디서부터 시작할까

지금 막 시작하는 분께 권하는 순서:

1. **GitHub Actions 한 파일** 로 빌드 + GHCR push 까지 (이 글 §2).
2. K8s 매니페스트는 `kubectl apply` 로 손으로 한 번 만들어보기. CI 에 넣지 말고.
3. 매니페스트가 익숙해지면 **Helm 차트** 로 변환. values.yaml 에 image tag 분리.
4. 5 개 이상 서비스가 되면 **ArgoCD** 도입. `kubectl apply` 한 번으로 root-app 부트스트랩.
5. 이미지 tag 자동 갱신이 필요해지면 **ArgoCD Image Updater** 또는 GitHub Actions 에서 helm-deploy 리포에 PR 자동 발행.

Jenkins 는 굳이 안 만나는 게 좋지만, 회사에서 만나게 되면:
- Declarative Pipeline 만 씁니다 (Scripted 는 유지보수 지옥).
- 가능하면 **Kubernetes plugin** 으로 agent 를 Pod 으로 띄움 (위 §3 예시).
- 시크릿은 **HashiCorp Vault 연동** 또는 외부 SecretManager 로 빼고, Credentials 플러그인은 부트스트랩 자격증명만 두기.

CI/CD 의 본질은 도구가 아니라 **"내 한 줄 commit 이 5 분 뒤 prod 에 안전하게 도달하는 컨베이어 벨트가 있는가"** 입니다. Jenkins 든 GitHub Actions 든, 그 컨베이어 벨트의 한 부품일 뿐이에요. 도구를 고를 때는 "내가 운영할 수 있는 가장 단순한 조합" 부터 시작하시고, 한계가 명확해질 때만 다른 도구를 더하세요.

---

### 더 읽어볼만한 글

- [Docker Compose vs Kubernetes + ArgoCD GitOps — 30 개 서비스 운영 비교](/2026/05/14/docker-compose-vs-k8s-argocd-gitops-comparison/)
- [ArgoCD 자체를 GitOps 로 셀프 관리 — App-of-Apps 패턴 실전](/2026/05/14/argocd-self-management-app-of-apps/)
- [K8s Secret 의 3rd party 생태계 (SOPS, Sealed Secrets, External Secrets)](/2026/05/14/k8s-secret-3rd-party-ecosystem/)
