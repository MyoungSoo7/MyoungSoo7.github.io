---
layout: post
title: "Kubernetes 클러스터에 GitHub Actions Runner 설치하기: ARC 운영과 보안 설계"
date: 2026-09-12 13:55:16 +0900
categories: [DevOps, Kubernetes]
tags: [GitHub Actions, Self-hosted Runner, ARC, Kubernetes, CI/CD, Security]
---

# Kubernetes 클러스터에 GitHub Actions Runner 설치하기

GitHub Actions의 기본 runner 대신 자체 Kubernetes 클러스터에서 runner를 운영하면 내부 네트워크 접근, 사설 registry, 특수한 빌드 환경, GPU·대형 메모리 작업 같은 요구사항을 처리할 수 있다. 하지만 self-hosted runner는 단순히 파드 하나를 띄우는 문제가 아니다.

- 어떤 저장소의 작업을 실행할 것인가?
- runner가 접근할 수 있는 내부 시스템은 무엇인가?
- 작업이 끝난 뒤 환경을 깨끗하게 폐기하는가?
- 동시에 여러 workflow가 실행될 때 어떻게 격리하는가?
- GitHub와 Kubernetes의 권한·secret·로그를 어떻게 관리하는가?

GitHub는 Kubernetes 기반 self-hosted runner autoscaling의 권장 구현으로 Actions Runner Controller(ARC)를 안내한다.[1] ARC는 Kubernetes operator로 runner를 조정하고, workflow 수요에 따라 runner scale set을 확장·축소한다.[2]

## 1. 왜 Kubernetes에 GitHub Runner를 두는가

### GitHub-hosted runner로 충분한 경우

- 외부 공개 서비스만 호출한다.
- 특별한 도구나 사설 네트워크가 필요 없다.
- 관리 부담보다 빠른 도입이 중요하다.
- workflow마다 깨끗한 표준 환경이면 충분하다.

### Self-hosted runner가 필요한 경우

- 사설 Kubernetes API·registry·database에 접근해야 한다.
- 내부망에서만 동작하는 테스트가 있다.
- 특정 CPU·메모리·GPU·OS가 필요하다.
- 대형 Docker image cache를 활용하고 싶다.
- 사내 보안·감사·네트워크 정책으로 실행 위치를 제한해야 한다.

GitHub는 self-hosted runner가 GitHub Actions와 통신할 수 있고 workflow 유형에 맞는 hardware resource를 가져야 한다고 설명한다.[1]

## 2. 전체 구조

```text
GitHub Actions
     │
     │ job available / runner registration
     ▼
ARC Controller
     │
     ▼
Runner Scale Set Listener
     │
     │ desired replicas 조정
     ▼
Ephemeral Runner Pod
     │
     ├─ checkout
     ├─ test / build / scan
     ├─ artifact upload
     └─ job 종료 후 삭제
```

ARC의 흐름은 대략 다음과 같다.

1. ARC controller와 runner scale set을 설치한다.
2. listener가 GitHub Actions 서비스와 HTTPS long-poll 연결을 맺는다.
3. workflow의 `runs-on`이 scale set 이름과 일치하면 job 수요를 감지한다.
4. Kubernetes API를 통해 ephemeral runner replica를 늘린다.
5. runner pod가 GitHub에 등록되어 job을 받는다.
6. job이 끝나면 runner를 삭제한다.

GitHub 문서는 ARC가 controller, listener, ephemeral runner를 이용해 이 lifecycle을 관리한다고 설명한다.[2]

## 3. 설치 전 설계

### namespace 분리

권장 구조는 controller와 runner를 같은 namespace에 두지 않는 것이다.

```text
arc-systems
  └─ ARC controller

arc-runners
  └─ runner scale set
  └─ ephemeral runner pods
```

GitHub는 runner pod를 operator pod와 다른 namespace에 배치하는 것을 보안 모범 사례로 안내한다.[3]

### repository·organization 범위

runner를 어디에 등록할지 먼저 결정한다.

- 특정 repository
- organization
- enterprise

범위가 넓을수록 편리하지만 runner가 처리할 수 있는 workflow와 secret의 범위도 넓어진다. 처음에는 특정 repository 또는 제한된 runner group에서 시작하고, 필요할 때만 범위를 확대하는 편이 안전하다.

### runner label과 `runs-on`

scale set 이름은 workflow의 `runs-on`과 연결된다.

```yaml
jobs:
  test:
    runs-on: lemuel-k8s-runner
    steps:
      - uses: actions/checkout@v4
      - run: ./gradlew test
```

팀·환경·하드웨어별로 scale set을 분리할 수 있다.

```yaml
runs-on: [self-hosted, linux, lemuel-k8s-runner]
```

단, label이 너무 세분화되면 job이 장시간 queue에 남을 수 있다. GitHub는 일치하는 online·idle runner가 없으면 job이 대기하고, 일정 시간 안에 runner가 없으면 실패할 수 있다고 설명한다.[1]

## 4. ARC Helm 설치 개념

ARC는 공식 Helm chart를 사용하는 방식이 일반적이다. GitHub 문서의 기본 흐름은 controller chart를 설치하고, 별도의 runner scale set chart를 구성하는 것이다.[3]

개념적인 설치 순서는 다음과 같다.

```bash
helm install arc-controller \
  --namespace arc-systems \
  --create-namespace \
  <arc-controller-chart>

helm install lemuel-runner \
  --namespace arc-runners \
  --create-namespace \
  <runner-scale-set-chart>
```

실제 설치 시에는 현재 chart version, `githubConfigUrl`, 인증 방식, runner image, container mode, resource, node selector를 명시해야 한다. 토큰을 shell command에 평문으로 직접 넣는 방식은 피하고 Kubernetes Secret 또는 GitHub App 인증을 사용한다. GitHub도 secret을 평문으로 CLI에 전달하지 말고 secret reference를 사용하라고 안내한다.[3]

설치 후 확인:

```bash
helm list -A
kubectl get pods -n arc-systems
kubectl get pods -n arc-runners
kubectl get autoscalingrunnerset -n arc-runners
```

설치 성공은 controller pod가 Running인 것만으로 확정하지 않는다. listener의 GitHub 연결, scale set 등록, workflow job 할당, ephemeral runner 생성·삭제까지 확인해야 한다.

## 5. 인증과 Secret

### GitHub App 우선 고려

repository·organization runner는 GitHub App 인증을 검토하는 편이 좋다. enterprise-level runner에는 정책에 따라 PAT가 필요할 수 있으므로 등록 범위와 GitHub 문서의 인증 제약을 확인해야 한다.[3]

### Secret 원칙

- PAT나 private key를 values 파일에 평문으로 commit하지 않는다.
- Helm 명령줄에 secret 값을 직접 넣지 않는다.
- Kubernetes Secret은 올바른 namespace에 만든다.
- secret을 workflow log에 출력하지 않는다.
- 만료·rotation·폐기 절차를 문서화한다.
- runner가 정말 필요한 API만 호출하도록 권한을 줄인다.

GitHub는 workflow secret에 대해 least privilege, masking, 노출 시 즉시 삭제·rotation, 변환된 secret의 별도 등록을 권고한다.[4]

## 6. Runner Pod 실행 모드

### Docker-in-Docker

runner 안에서 Docker build를 수행하기 위해 Docker daemon을 함께 실행하는 방식이다.

장점:

- 기존 Docker workflow를 비교적 쉽게 이식한다.
- `docker build`, `docker compose` 사용이 직관적이다.

위험:

- privileged 권한이 필요할 수 있다.
- Docker socket과 daemon이 공격면이 된다.
- job 간 cache·filesystem 격리가 복잡해진다.
- self-hosted runner의 권한이 커진다.

### Kubernetes mode

ARC가 job의 container·service 작업을 Kubernetes pod로 생성하는 방식이다. GitHub 문서에 따르면 Kubernetes mode에서는 runner container hook이 같은 namespace에 job 관련 pod를 만들 수 있다.[3]

장점:

- Kubernetes resource와 lifecycle로 job을 격리한다.
- CPU·memory request/limit를 job에 적용하기 쉽다.
- Docker daemon 권한을 줄일 수 있다.

주의:

- ServiceAccount와 Role을 최소 권한으로 구성한다.
- job pod가 접근할 수 있는 Secret·ConfigMap을 제한한다.
- image pull·registry·network policy를 검증한다.
- runner와 job pod의 로그와 상태를 함께 추적한다.

## 7. 보안이 가장 중요하다

GitHub Actions workflow는 repository에서 코드를 가져와 shell command, package manager, Docker build 등을 실행한다. 따라서 self-hosted runner는 일반 애플리케이션 pod보다 높은 위험을 가진 실행 환경이다.

GitHub는 production workload와 self-hosted runner를 같은 Kubernetes cluster에서 공유할 때 보안 위험을 고려하라고 권고한다. runner에 실행되는 workflow가 임의 코드를 실행할 수 있기 때문이다.[3]

### 최소한의 격리

```text
production namespace
  ├─ runner 접근 금지 또는 제한
  ├─ production Secret mount 금지
  ├─ NetworkPolicy 제한
  ├─ 별도 node pool 또는 taint
  └─ 별도 runner group
```

권장 원칙:

- ephemeral runner를 사용한다.
- untrusted fork PR에서 self-hosted runner를 직접 사용하지 않는다.
- production credential을 runner에 상시 mount하지 않는다.
- runner group으로 repository 접근을 제한한다.
- job 종료 후 workspace와 runner를 폐기한다.
- container image를 digest로 고정한다.
- runner pod를 non-root로 실행한다.
- privileged와 hostPath를 최소화한다.
- NetworkPolicy로 outbound·inbound를 제한한다.
- controller·listener·runner 로그를 외부 저장소에 보관한다.

GitHub는 autoscaling에서 ephemeral runner를 권장한다. ephemeral runner는 하나의 job만 받고 삭제되므로 이전 job의 파일·credential·process가 다음 job으로 남는 위험을 줄일 수 있다.[1]

## 8. 리소스와 스케줄링

Runner pod에 resource를 명시하지 않으면 CI가 클러스터의 다른 workload를 압박할 수 있다.

```yaml
template:
  spec:
    containers:
      - name: runner
        resources:
          requests:
            cpu: "500m"
            memory: "1Gi"
          limits:
            cpu: "2"
            memory: "4Gi"
```

추가 고려사항:

- `nodeSelector`와 taint/toleration
- job 종류별 runner scale set
- 최대 동시 runner 수
- image cache와 registry rate limit
- Docker layer cache의 보안·용량
- job timeout과 stuck runner 정리
- cluster autoscaler와 runner autoscaling 상호작용

runner 수를 늘리는 것만으로 pipeline이 빨라지지 않는다. node capacity, registry, GitHub API, DB test dependency가 병목일 수 있다.

## 9. workflow 설계

```yaml
name: CI

on:
  pull_request:
  push:
    branches: [main]

permissions:
  contents: read

jobs:
  test:
    runs-on: lemuel-k8s-runner
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v4
      - name: Run tests
        run: ./gradlew test
```

보안 기준:

- `permissions`를 job별로 최소화한다.
- `timeout-minutes`를 설정한다.
- pull request에서 untrusted code와 secret을 분리한다.
- shell 변수는 환경변수로 받아 quoting한다.
- 외부 action은 version 또는 commit으로 고정한다.
- artifact와 cache에 secret이 포함되지 않게 한다.
- job 결과와 runner pod를 trace ID로 연결한다.

## 10. 관측과 장애 대응

ARC 운영에서 확인할 대상:

```text
ARC controller
  ├─ reconciliation error
  ├─ GitHub API authentication
  └─ Kubernetes API access

Runner scale set listener
  ├─ GitHub long-poll
  ├─ job available
  └─ scale decision

Ephemeral runner
  ├─ registration
  ├─ job pickup
  ├─ workflow log
  └─ cleanup
```

대표 장애:

### Job이 계속 queued

- `runs-on` 이름 불일치
- runner group 권한 문제
- scale set listener가 GitHub에 연결되지 않음
- controller가 runner replica를 만들지 못함
- node resource 부족
- GitHub API 인증 실패

### Runner는 생겼지만 job을 받지 못함

- runner registration 실패
- JIT token 오류
- label·group routing 불일치
- outbound HTTPS 차단
- system time·TLS 문제

### Job 후 runner가 남음

- cleanup controller 오류
- pod finalizer 문제
- node 장애
- runner process가 종료되지 않음

### workflow가 실행되지만 내부 서비스에 접근 못함

- NetworkPolicy
- DNS
- route·firewall
- service account 권한
- 내부 CA·TLS
- production endpoint 접근 제한

## 11. 클러스터에 설치하기 전 체크리스트

### 설계

- [ ] repository/organization/enterprise 범위 결정
- [ ] runner group과 label 설계
- [ ] controller·runner namespace 분리
- [ ] production workload와 격리
- [ ] ephemeral lifecycle 선택

### 인증

- [ ] GitHub App 또는 최소 권한 인증
- [ ] Kubernetes Secret reference 사용
- [ ] PAT·private key rotation
- [ ] workflow `GITHUB_TOKEN` 최소 권한

### Kubernetes

- [ ] ServiceAccount 최소 권한
- [ ] Role/RoleBinding 검토
- [ ] NetworkPolicy
- [ ] resource request/limit
- [ ] nodeSelector·taint/toleration
- [ ] image digest·non-root

### 운영

- [ ] controller/listener/runner 로그 보관
- [ ] runner queue와 scale metric
- [ ] stuck job·cleanup alert
- [ ] GitHub API·registry·artifact endpoint 접근성
- [ ] 실제 workflow smoke test
- [ ] rollback·uninstall 절차

## 결론

Kubernetes에 GitHub Actions Runner를 설치하는 것은 단순히 CI 작업을 클러스터에서 실행하는 기능을 추가하는 일이 아니다. GitHub의 workflow 실행 권한과 클러스터의 네트워크·secret·resource 권한을 연결하는 보안·운영 시스템이다.

- ARC는 Kubernetes 기반 runner autoscaling의 권장 구현이다.
- controller와 runner namespace를 분리한다.
- ephemeral runner로 job 간 오염을 줄인다.
- production workload와 runner를 격리한다.
- GitHub App·Kubernetes Secret·최소 권한을 사용한다.
- `runs-on`, runner group, label을 명확히 설계한다.
- pod Running이 아니라 job 수신·실행·삭제까지 검증한다.
- 로그·metric·cleanup을 운영한다.

특히 self-hosted runner에 실행되는 workflow는 임의 코드를 실행할 수 있다는 점을 잊으면 안 된다. 편리한 CI 인프라가 production cluster의 새로운 공격 경로가 되지 않도록, **ephemeral·격리·최소 권한·관측·폐기**를 기본값으로 설계해야 한다.

## 참고 자료

[1] GitHub Actions Self-hosted Runners Reference — 요구사항, ARC 권장, ephemeral runner, 네트워크  
[2] GitHub Actions Runner Controller — ARC 구성요소와 autoscaling 흐름  
[3] GitHub Deploying Runner Scale Sets — Helm 설치, namespace 분리, Secret·보안 권고  
[4] GitHub Actions Secure Use — secret·권한·workflow 보안 원칙

## 출처

- Self-hosted Runners Reference: https://docs.github.com/en/actions/reference/runners/self-hosted-runners
- Actions Runner Controller: https://docs.github.com/en/actions/concepts/runners/actions-runner-controller
- Deploying Runner Scale Sets: https://docs.github.com/en/actions/how-tos/manage-runners/use-actions-runner-controller/deploy-runner-scale-sets
- Secure Use Reference: https://docs.github.com/en/actions/reference/security/secure-use

## Sources

[1] https://docs.github.com/en/actions/reference/runners/self-hosted-runners — GitHub Self-hosted Runners Reference
[2] https://docs.github.com/en/actions/concepts/runners/actions-runner-controller — GitHub Actions Runner Controller
[3] https://docs.github.com/en/actions/how-tos/manage-runners/use-actions-runner-controller/deploy-runner-scale-sets — Deploying Runner Scale Sets
[4] https://docs.github.com/en/actions/reference/security/secure-use — GitHub Actions Secure Use
