---
layout: post
title: "[CS300 #230] GitOps 와 ArgoCD — Git 이 원하는 상태의 유일한 원본"
date: 2026-10-10 21:50:00 +0900
categories: [cs]
tags: [cs300, devops, gitops, argocd, continuous-delivery]
---

컴퓨터공학 300 주제 시리즈의 230번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

GitOps 는 시스템의 원하는 상태를 Git 에 선언해 두고, 클러스터 안의 에이전트가 그것을 끌어와(pull) 실제 상태와 계속 맞추는 운영 방식이다. ArgoCD 는 쿠버네티스용 대표 구현체다.

## 왜 필요한가

전통적인 배포 파이프라인은 CI 서버가 클러스터에 접속해 `kubectl apply` 나 `helm upgrade` 를 실행한다(push 방식). 이 방식에는 몇 가지 약점이 있다.

- CI 서버가 클러스터 관리자 권한을 가져야 한다. CI 가 털리면 클러스터도 털린다.
- 누군가 손으로 `kubectl edit` 을 하면 Git 과 클러스터가 달라진다. 아무도 모르게.
- "지금 운영에 무엇이 떠 있나"라는 질문에 답하려면 클러스터를 직접 뒤져야 한다.
- 클러스터를 새로 만들면 그동안의 배포를 다시 재생할 방법이 마땅치 않다.

GitOps 는 Git 을 원본으로 삼고 클러스터가 스스로 따라가게 해서 이 문제를 뒤집는다.

## 핵심 개념

### OpenGitOps 의 네 가지 원칙

CNCF 산하 OpenGitOps 프로젝트는 GitOps 를 네 원칙으로 정리했다.

| 원칙 | 뜻 |
|---|---|
| Declarative | 시스템의 원하는 상태를 선언적으로 표현한다 |
| Versioned and Immutable | 원하는 상태는 불변하고 버전이 매겨지며 전체 이력이 남는 방식으로 저장한다 |
| Pulled Automatically | 소프트웨어 에이전트가 원본에서 원하는 상태를 자동으로 끌어온다 |
| Continuously Reconciled | 에이전트가 실제 상태를 계속 관찰하고 원하는 상태에 맞추려 시도한다 |

원칙 어디에도 "Git" 이라는 단어가 필수는 아니다. 하지만 버전 관리·불변 이력·리뷰(PR) 를 모두 갖춘 도구로 Git 이 가장 흔하게 쓰인다. 네 번째 원칙은 226번에서 본 쿠버네티스 조정 루프를 클러스터 바깥 원본까지 넓힌 것이다.

### push 와 pull

```
push 방식                           pull 방식(GitOps)
개발자 -> Git -> CI --kubectl--> 클러스터     개발자 -> Git <--watch-- 에이전트(클러스터 안)
          (CI 가 클러스터 자격증명 보유)                          |
                                                              v
                                                           클러스터
```

pull 방식에서는 클러스터 자격증명이 클러스터 밖으로 나가지 않는다. 에이전트는 Git 읽기 권한만 있으면 된다. CI 는 이미지를 빌드해 레지스트리에 올리고, 매니페스트 저장소의 이미지 태그를 바꾸는 커밋(또는 PR)을 만드는 데서 멈춘다.

### ArgoCD 의 구성

ArgoCD 는 쿠버네티스 컨트롤러로 구현되어 있다. 주요 개념은 다음과 같다.

- **Application**: "이 Git 저장소의 이 경로를, 이 클러스터의 이 네임스페이스에" 라는 연결을 정의하는 커스텀 리소스.
- **Target state**: Git 에 있는 원하는 상태.
- **Live state**: 클러스터에 실제로 있는 상태.
- **Sync status**: 둘이 같은가(`Synced`) 다른가(`OutOfSync`).
- **Health status**: 리소스가 정상 동작하는가(`Healthy`, `Progressing`, `Degraded` 등).
- **Sync**: live 를 target 으로 맞추는 작업.

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: web
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://git.example.com/team/deploy.git
    targetRevision: main
    path: apps/web/overlays/prod
  destination:
    server: https://kubernetes.default.svc
    namespace: web
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
```

`source` 는 일반 YAML 디렉터리, Kustomize, 헬름 차트 모두 될 수 있다.

### 자동 동기화의 세 스위치

| 설정 | 동작 |
|---|---|
| `automated` | Git 이 바뀌면 자동으로 sync 한다 |
| `prune: true` | Git 에서 사라진 리소스를 클러스터에서도 지운다. 기본은 꺼짐(안전을 위해) |
| `selfHeal: true` | 누군가 클러스터를 직접 고쳐 live 가 달라지면 Git 상태로 되돌린다 |

`selfHeal` 을 켜면 `kubectl edit` 으로 한 긴급 수정도 곧 되돌려진다. 이것은 버그가 아니라 의도다. 긴급 수정도 Git 커밋으로 해야 한다는 규율을 시스템이 강제하는 것이다.

### 변경 감지

ArgoCD 는 주기적으로 저장소를 폴링해 변경을 감지한다(문서 기준 기본 3분). 더 빨리 반응하려면 Git 서버의 웹훅을 ArgoCD 에 연결한다.

### 저장소 구조

애플리케이션 코드 저장소와 배포 매니페스트 저장소를 분리하는 것이 일반적이다. 코드 커밋마다 배포 이력이 섞이지 않고, 배포 저장소의 권한을 따로 관리할 수 있다. 환경별 차이는 Kustomize 오버레이나 헬름 values 파일로 표현한다.

```
deploy/
  apps/web/base/            # 공통 매니페스트
  apps/web/overlays/dev/    # dev 차이
  apps/web/overlays/prod/   # prod 차이
```

## 직접 해 보기

ArgoCD 의 diff, prune, selfHeal 을 단순화해 시뮬레이션해 보자. 리소스를 `(kind, name) -> spec` 딕셔너리로 표현한다.

```python
def diff(target, live):
    out = []
    for key in sorted(set(target) | set(live)):
        if key not in live:
            out.append(("create", key))
        elif key not in target:
            out.append(("orphan", key))
        elif target[key] != live[key]:
            out.append(("modify", key))
    return out

def sync(target, live, prune, self_heal, manual_drift_keys):
    for action, key in diff(target, live):
        if action == "create":
            live[key] = dict(target[key])
        elif action == "orphan":
            if prune:
                del live[key]
            else:
                print(f"    keep orphan {key} (prune=false)")
        elif action == "modify":
            if key in manual_drift_keys and not self_heal:
                print(f"    leave drift {key} (selfHeal=false)")
                continue
            live[key] = dict(target[key])
    return live

git = {("Deployment", "web"): {"image": "web:1.4", "replicas": 3},
       ("Service", "web"): {"port": 80}}
live = {("Deployment", "web"): {"image": "web:1.3", "replicas": 3},
        ("Service", "web"): {"port": 80},
        ("ConfigMap", "old-flags"): {"x": "1"}}

print("status:", "Synced" if not diff(git, live) else "OutOfSync", diff(git, live))
live = sync(git, live, prune=True, self_heal=True, manual_drift_keys=set())
print("after sync:", "Synced" if not diff(git, live) else "OutOfSync")

# 누군가 kubectl 로 replicas 를 10 으로 바꿨다
live[("Deployment", "web")]["replicas"] = 10
print("manual edit ->", diff(git, live))
for heal in (False, True):
    l = {k: dict(v) for k, v in live.items()}
    print(f"  selfHeal={heal}:")
    l = sync(git, l, prune=True, self_heal=heal,
             manual_drift_keys={("Deployment", "web")})
    print("    replicas =", l[("Deployment", "web")]["replicas"])
```

결과는 다음과 같다.

```
status: OutOfSync [('orphan', ('ConfigMap', 'old-flags')), ('modify', ('Deployment', 'web'))]
after sync: Synced
manual edit -> [('modify', ('Deployment', 'web'))]
  selfHeal=False:
    leave drift ('Deployment', 'web') (selfHeal=false)
    replicas = 10
  selfHeal=True:
    replicas = 3
```

`selfHeal` 이 꺼져 있으면 drift 는 `OutOfSync` 로 표시만 되고 남는다. 켜져 있으면 Git 의 3으로 돌아간다. 오토스케일러(HPA)가 레플리카 수를 바꾸는 경우라면 이것이 문제가 된다. 그래서 HPA 를 쓰는 디플로이먼트는 매니페스트에서 `replicas` 를 빼거나, ArgoCD 의 `ignoreDifferences` 로 그 필드를 비교에서 제외한다.

## 현업에서는

- **롤백은 `git revert`.** 배포 이력이 곧 Git 이력이므로, 문제가 생기면 해당 커밋을 되돌리는 커밋을 올린다. 누가 언제 왜 바꿨는지가 PR 에 남는다.
- **"앱 오브 앱스".** Application 자체를 Git 에 선언하고, 그것들을 관리하는 상위 Application 하나를 둔다. 클러스터를 새로 만들어도 ArgoCD 와 루트 Application 하나만 설치하면 나머지가 따라 올라온다.
- **시크릿은 Git 에 평문으로 두지 않는다.** Sealed Secrets, SOPS, External Secrets Operator 처럼 암호화하거나 외부 저장소를 참조하는 방식을 쓴다.
- **잦은 OutOfSync 의 원인.** 컨트롤러나 웹훅이 리소스에 기본값·어노테이션을 덧붙이면 Git 과 영원히 달라 보인다. 해당 필드를 `ignoreDifferences` 에 넣거나 매니페스트에 그 값을 명시한다.
- **홈랩에도 잘 맞는다.** 노드 몇 대짜리 클러스터라도 ArgoCD 를 두면 "무엇이 떠 있나"를 Git 저장소 하나로 답할 수 있다. 노드를 다시 설치해도 매니페스트 저장소에서 원래 상태를 재현한다.

## 확인 문제

1. OpenGitOps 의 네 원칙을 쓰라.
2. pull 방식이 push 방식보다 보안상 유리한 이유는?
3. `prune` 이 기본적으로 꺼져 있는 이유를 추측해 보라.
4. `selfHeal: true` 인 앱에서 운영자가 `kubectl scale` 로 레플리카를 늘렸다. 어떻게 되는가?
5. HPA 와 ArgoCD 를 함께 쓸 때 생길 수 있는 충돌과 해결책은?

### 풀이

1. Declarative, Versioned and Immutable, Pulled Automatically, Continuously Reconciled.
2. 클러스터 자격증명이 클러스터 밖(CI 서버)에 있을 필요가 없다. 에이전트는 Git 읽기 권한만 갖는다.
3. Git 에서 파일을 실수로 지우거나 경로를 잘못 바꾸면 운영 리소스가 대량으로 삭제될 수 있기 때문이다.
4. ArgoCD 가 drift 를 감지해 Git 의 값으로 되돌린다.
5. HPA 가 바꾼 레플리카 수를 ArgoCD 가 Git 값으로 되돌리며 서로 싸운다. 매니페스트에서 `replicas` 를 빼거나 `ignoreDifferences` 로 제외한다.

## 더 읽을거리 (References)

- OpenGitOps, [GitOps Principles](https://opengitops.dev/)
- Argo CD Docs, [Overview](https://argo-cd.readthedocs.io/en/stable/)
- Argo CD Docs, [Core Concepts](https://argo-cd.readthedocs.io/en/stable/core_concepts/)
- Argo CD Docs, [Automated Sync Policy](https://argo-cd.readthedocs.io/en/stable/user-guide/auto_sync/)
