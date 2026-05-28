---
layout: post
title: "CI/CD 의 역사 — *cron 스크립트* 부터 *쿠버네티스 GitOps* 까지: 빌드 파이프라인이 *클러스터의 일부* 가 되기까지"
date: 2026-05-29 00:25:00 +0900
categories: [devops, kubernetes, history]
tags: [ci-cd, jenkins, github-actions, docker, kubernetes, argocd, gitops, helm, continuous-deployment]
---

> *''아침에 출근해서 보니 빌드가 깨져 있었다''* — 1999 년 Martin Fowler 가 *Continuous Integration* 논문에 적은 이 한 줄은, 20 년 뒤에는 *''누가 kubectl 을 만졌어요?''* 로 바뀌게 된다. CI/CD 의 25 년 역사는 곧 *''빌드와 배포를 어떻게 사람 손에서 뺏을까''* 의 역사다. 그리고 그 끝에 **쿠버네티스** 가 서 있다.

이 글은 *CI/CD 의 진화* 를 **Kubernetes 의 등장과 어떻게 얽혔는지** 라는 시선으로 다시 짚는다. *cron 빌드 → CruiseControl → Jenkins → Docker → GitHub Actions → Kubernetes → GitOps* 로 이어진 흐름은 우연이 아니다. *컨테이너* 와 *선언형 인프라* 가 만나는 지점에서 CI/CD 는 *클러스터의 일부* 가 되었다.

---

## 1. 0세대 (~2000) — *사람이 빌드 서버였다*

CI/CD 라는 용어가 없던 시절, 빌드는 *팀의 가장 부지런한 사람* 이 *밤마다* 직접 돌렸다. *nightly build* 라는 단어가 이 시대의 산물이다 — 마이크로소프트가 Windows NT 시절 매일 밤 빌드 담당자를 정해 *''오늘 빌드 깨면 다음 날 본인이 다시 돌림''* 이라는 규칙을 만들었다는 이야기가 유명하다.

자동화의 첫 시도는 *cron + shell script* 였다. *''매일 02:00 에 SVN checkout → make → 결과를 메일로 보내라''* 가 1세대 CI 의 본체였다. 깨지면 누가 깼는지 메일 본문에서 찾아야 했고, *재현 환경* 같은 건 없었다. 한 사람의 로컬에서 잘 되던 게 빌드 서버에서 안 되는 *Works On My Machine* 농담이 이때 태어났다.

## 2. 2001 — *CruiseControl* 과 *Continuous Integration* 의 정의

2001 년 ThoughtWorks 가 **CruiseControl** 을 오픈소스로 공개한다. *최초의 명시적 CI 서버* 였다. 같은 해 Martin Fowler 가 *''Continuous Integration''* 글을 발표하고, *''매일 여러 번 통합한다''* 는 단순한 정의를 박아넣는다.

CruiseControl 이 한 일은 *별 게 없다* — VCS 를 *주기적으로 polling* 하고, 변경이 있으면 *빌드를 trigger* 하고, *결과를 웹 UI 로 보여주는 것*. 하지만 이 *''사람이 안 시켜도 알아서 돈다''* 는 한 가지가 *CI 라는 단어가 가리키는 본질* 이었다.

그러나 CruiseControl 은 *XML 설정 지옥* 으로 악명 높았다. *config.xml* 한 파일에 모든 빌드를 박아넣는 구조였고, 200줄 넘는 XML 을 *손* 으로 작성해야 했다. 이 불편이 다음 세대를 불렀다.

## 3. 2005~2011 — *Hudson, Jenkins, 그리고 플러그인의 시대*

2005 년 Sun 의 Kohsuke Kawaguchi 가 *''XML 안 쓰는 CI 가 필요하다''* 며 **Hudson** 을 만든다. *웹 UI 에서 모든 걸 클릭으로 설정* 하는 혁신적인 접근이었고, *플러그인 아키텍처* 가 핵심이었다 — *''내가 안 만든 기능은 누가 만든다''*.

2011 년 Oracle 이 Sun 을 인수한 뒤 Hudson 상표권을 두고 분쟁이 터졌고, 커뮤니티는 *fork* 해서 **Jenkins** 로 이름을 바꾼다. *이름 분쟁* 이라는 사소한 사건이 *''오픈소스 CI 의 표준''* 을 결정했다.

Jenkins 가 지배한 10 년은 *플러그인 1,800 개* 의 시대였다. 어떤 빌드 시나리오든 *플러그인을 깔면 됨*. 그러나 *대가* 가 있었다:

- **상태 폭발** — Jenkins master 한 대에 모든 job 의 history, workspace, credentials 가 쌓임. 디스크 풀나면 끝
- **재현 불가능한 빌드** — *''Jenkins 노드에 깔린 JDK 버전''* 이 빌드 결과를 좌우. 노드 갈아끼우면 빌드 깨짐
- **플러그인 버전 매트릭스 지옥** — 80 개 플러그인을 *동시에 업데이트* 안 하면 서로 conflict

이 *대가* 가 다음 혁명의 연료가 된다.

## 4. 2013~2014 — *Docker 가 모든 걸 바꿨다*

2013 년 dotCloud 가 내부 도구로 쓰던 *컨테이너 래퍼* 를 **Docker** 라는 이름으로 오픈소스화한다. 발표 직후 6 개월 만에 *데브옵스 컨퍼런스의 절반이 Docker 얘기* 가 되었다.

Docker 가 CI/CD 에 끼친 영향은 *세 가지* 로 정리된다:

1. **빌드 산출물 = 컨테이너 이미지** — 더 이상 *''jar 파일을 어디 서버에 어떻게 deploy 할까''* 가 문제가 아니다. *이미지 한 장* 이 곧 *실행 가능한 단위*
2. **재현 가능한 빌드 환경** — *Dockerfile* 한 줄에 *''JDK 17 + Maven 3.9''* 를 박아넣으면 *어떤 호스트* 에서 빌드해도 같은 결과
3. **레지스트리 = 배포 채널** — *Docker Hub*, 나중에는 *GitHub Container Registry*, *Harbor* 가 *''ftp/scp 로 jar 옮기던''* 시대를 끝냄

이 셋이 만나면서 *''빌드 → 배포''* 라는 두 단어 사이의 거리가 폭발적으로 줄었다. *5 년 안에* CI 와 CD 의 경계가 사라진다.

## 5. 2014~2015 — *Kubernetes 가 도착했다*

2014 년 6 월, Google 이 **Kubernetes** 를 오픈소스로 공개한다. 내부적으로 10 년 넘게 돌리던 *Borg* 의 *재설계 후속작* 이었다. *''컨테이너를 어떻게 운영할까''* 라는 질문에 Google 이 *''여기 답이 있다''* 라며 던진 답안지였다.

Kubernetes 의 두 가지 *철학적 결정* 이 CI/CD 의 미래를 결정했다:

### 5.1. *선언형 (Declarative)*

기존 시스템 관리 방식은 *명령형 (Imperative)* 이었다. *''ssh 들어가서 systemctl restart nginx 해''*. 그러나 K8s 는 *''YAML 에 *원하는 상태* 만 적어라, 거기로 가는 길은 컨트롤러가 알아서 찾는다''* 로 뒤집었다.

이 한 가지가 *''Git 에 적힌 게 곧 운영 상태''* 라는 *GitOps* 의 전제 조건이 된다. 명령형 세계에선 *''누가 언제 무슨 명령을 쳤는지''* 가 진실이지만, 선언형 세계에선 *''Git 에 뭐가 적혀 있는지''* 가 진실이다.

### 5.2. *컨트롤 루프 (Control Loop)*

K8s 의 모든 컨트롤러는 *''현재 상태''* 와 *''원하는 상태''* 를 *계속 비교하고* *''차이가 있으면 조정한다''* 는 단순한 패턴을 따른다. *Reconciliation Loop* 라 부른다.

이 패턴이 *외부 시스템* 으로 확장될 수 있다는 *깨달음* 이 다음 챕터를 연다.

## 6. 2015~2018 — *GitHub Actions, GitLab CI, CircleCI* — CI 가 *VCS 안으로* 들어오다

Jenkins 의 *''별도 서버 운영''* 모델은 *팀 한 명이 항상 Jenkins 트러블슈팅에 묶이는''* 비용을 만들었다. 이 비용을 *클라우드 SaaS* 가 흡수하기 시작한다.

- 2011 **Travis CI** — *GitHub 옆에 붙여서 push 하면 자동 빌드*. *.travis.yml* 한 파일이면 끝
- 2012 **CircleCI** — Travis 와 비슷하지만 *유료 SaaS* 로 차별화
- 2015 **GitLab CI** — *GitLab 자체에 CI 내장*. *.gitlab-ci.yml* 이 standard
- 2019 **GitHub Actions** — *GitHub 가 자체 CI 를 내놓음*. *.github/workflows/\*.yml*

이 흐름의 *공통점* 은 *''설정이 코드 옆에 산다''* 였다. Jenkins 의 *''중앙 서버에 job 정의''* 모델이 *''레포 안의 yml''* 로 분산된 것. **Pipeline as Code**.

그리고 *모든 yml 들* 이 *결국 Docker 이미지를 빌드* 하고 있었다. 2018 년경엔 *''Java 빌드한 결과물을 어딘가 ftp 로 던지는''* 워크플로는 *유물* 이 되어 있었다.

## 7. 2017~ — *ArgoCD, Flux* — GitOps 의 탄생

CI 가 *''이미지를 빌드하고 레지스트리에 push 하는 것''* 까지 진화하자 *남은 질문* 이 있었다:

> *''누가 클러스터에 kubectl apply 하지?''*

전통적인 답은 *''CI 가 kubectl 친다''* 였다. *Jenkins job 의 마지막 단계에 kubectl apply* 를 박는 방식. 그러나 이 모델은 *세 가지 문제* 가 있다:

1. *Jenkins 가 클러스터 credentials 를 가져야 함* — 보안 사고시 폭발 반경 거대
2. *Drift 감지 불가* — Jenkins 가 apply 한 후, 누가 클러스터에서 *손* 으로 바꿨다면 알 길 없음
3. *Rollback 이 힘듦* — *''이전 상태''* 가 어디 적혀 있는지 모름

2017 년 *Argo Project* 가 **ArgoCD** 를, *Weaveworks* 가 **Flux** 를 거의 동시에 발표하며 *답* 을 내놓는다. 핵심은 *반전* 이다:

> *''CI 가 클러스터로 push 하지 마라. **클러스터가 Git 에서 pull 하라**''*

이 한 줄이 **GitOps** 의 정의다. ArgoCD 는 *클러스터 안에 사는 컨트롤러* 로서, *Git 레포지토리를 watch* 하고 *manifest 가 바뀌면 자동으로 sync* 한다. 그리고 *드리프트가 발생하면 다시 Git 상태로 되돌린다*.

이건 *우연이 아니다* — K8s 의 *Reconciliation Loop* 패턴을 *Git → Cluster* 라는 외부 축으로 확장한 것. ArgoCD 는 *''Git 이 desired state, 클러스터가 actual state''* 라는 새로운 컨트롤 루프를 *추가* 한 것일 뿐이다.

## 8. 2020~ — *Image Updater, Renovate* — 마지막 사람 손을 없애기

GitOps 가 등장한 직후에도 *한 군데* 에 *사람 손* 이 남아 있었다:

> *''CI 가 이미지를 빌드하면, manifest 의 image tag 를 누가 업데이트 하지?''*

초기엔 *CI 가 manifest 레포를 직접 commit* 하는 패턴이 흔했다. *''build 한 sha 로 helm values.yaml 의 image.tag 를 sed 해서 git push''*. 이게 또 *credentials 문제* 를 만들었다.

**ArgoCD Image Updater** (2020), **Renovate Bot**, **Flux Image Automation** 이 이 마지막 손도 없앤다. *Image Updater* 는 *클러스터 안에서* 레지스트리를 watch 하다가 *새 이미지 태그* 가 올라오면 *manifest 레포에 PR 또는 commit* 한다. 그러면 ArgoCD 가 *그 commit 을 보고* sync 한다.

이로써 파이프라인은 *완전한 닫힌 루프* 가 된다:

```
개발자 push → CI 이미지 빌드 → 레지스트리 push
                                    ↓
                       Image Updater 가 새 태그 감지
                                    ↓
                       helm values 의 image.tag 자동 갱신
                                    ↓
                       ArgoCD 가 Git 변경 감지 → 클러스터 sync
                                    ↓
                       Kubernetes 가 Pod rolling update
```

*어디에도 사람이 kubectl 을 치지 않는다*. *어디에도 누군가의 노트북에 박힌 credentials 가 없다*. *모든 변화는 Git history 에 남는다*.

## 9. 현재 — *Backstage, Crossplane, Internal Developer Platform*

2022 년 이후의 흐름은 *''CI/CD 자체가 한 단계 추상화''* 되는 것이다. *Spotify Backstage*, *Crossplane*, *Internal Developer Platform (IDP)* 같은 단어들이 등장한다.

핵심 아이디어:
- *애플리케이션 개발자는 yaml 을 안 쓴다* — *''Java 서비스''* 라고만 적으면 Backstage 가 알아서 *cookiecutter + ArgoCD app + helm chart 세트* 를 만들어줌
- *인프라도 K8s 리소스다* — Crossplane 은 *AWS RDS, GCP CloudSQL 같은 외부 자원* 까지 *K8s CRD* 로 다룸. 인프라 변경도 GitOps 의 일부

쿠버네티스는 이제 *''애플리케이션 실행 환경''* 이 아니라 *''플랫폼 자체의 API''* 가 되어 있다. CI/CD 는 *그 API 의 한 사용자* 일 뿐이다.

## 10. 정리 — *CI/CD 가 K8s 를 흡수한 게 아니라, CI/CD 가 K8s 를 향해 진화한 것*

25 년의 흐름을 다시 보면, *각 단계는 이전 단계의 *한계* 에서 자라났다*:

| 시대 | 도구 | 핵심 한계 | 다음 단계가 해결한 것 |
|---|---|---|---|
| 1990s | cron + shell | 사람이 매번 trigger | 자동 trigger |
| 2001 | CruiseControl | XML 설정 지옥 | 웹 UI + 플러그인 |
| 2005~ | Jenkins | 상태 폭발, 재현 불가 | 컨테이너로 환경 격리 |
| 2013 | Docker | 컨테이너 한 대 운영 | 다대다 스케줄링 |
| 2014 | Kubernetes | 명령형 운영 부담 | 선언형 + GitOps |
| 2017 | ArgoCD/Flux | CI 가 클러스터 push | 클러스터가 Git pull |
| 2020 | Image Updater | manifest 수동 갱신 | 완전 자동 sync |

*Kubernetes 가 CI/CD 의 끝* 인 이유는 *K8s 의 컨트롤 루프 패턴* 이 *''사람의 손''* 을 *마지막 한 군데까지 제거할 수 있는 유일한 모델* 이었기 때문이다. Jenkins 가 *''사람이 잡 정의는 한다''* 였다면, GitOps 는 *''사람이 git push 만 한다''*. 그리고 그 사이 *모든 단계* 가 *컨트롤러* 다.

> *''DevOps 의 목표는 사람을 자동화에서 빼내는 것이다''* — 25 년의 진화는 그 한 문장으로 압축된다.

남은 *사람의 책임* 은 *''Git 에 *옳은* 코드를 commit 하는 것''* 뿐이다. 그리고 그게 *진짜 일* 이다.

---

## 더 읽을 거리

- Martin Fowler, *Continuous Integration* (2006, 개정판) — *https://martinfowler.com/articles/continuousIntegration.html*
- Google, *Borg, Omega, and Kubernetes* (ACM 2016)
- Weaveworks, *GitOps: Operations by Pull Request* (2017)
- Kelsey Hightower, *Kubernetes the Hard Way* — 선언형 인프라의 *밑바닥*
- CNCF Landscape — *https://landscape.cncf.io/* — 지금 *생태계의 폭* 을 한눈에

*다음 글 예고: ArgoCD Application Set + Image Updater 실전 운영 패턴 — 18 개 helm 차트를 어떻게 한 사람이 관리하나*
