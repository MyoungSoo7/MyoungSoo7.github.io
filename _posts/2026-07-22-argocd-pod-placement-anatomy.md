---
layout: post
title: "ArgoCD 파드 배치 해부 — 홈랩 K3s에서 스케줄러가 GitOps 두뇌를 어디에 앉혔나"
date: 2026-07-22 06:30:00 +0900
categories: [DevOps, Kubernetes]
tags: [ArgoCD, K3s, GitOps, Scheduling, HomeLab, HA, ControlPlane]
---

# 관제탑은 어디에 앉아 있는가

6노드 K3s 홈랩에서 79개 애플리케이션을 ArgoCD로 굴리고 있다. 어느 날 서버 점검 봇이 ArgoCD 파드들의 배치 현황을 이렇게 보고했다.

| 컴포넌트 | 노드 | 노드 성격 |
|---|---|---|
| argocd-server | ilwon | Server (control-plane, etcd) |
| argocd-repo-server | ilwon | Server (control-plane, etcd) |
| argocd-applicationset-controller | ilwon | Server (control-plane, etcd) |
| argocd-dex-server | ilwon | Server (control-plane, etcd) |
| argocd-application-controller-0 | louise | Agent (Worker) |
| argocd-image-updater | louise | Agent (Worker) |
| argocd-notifications-controller | david | Agent (Worker) |
| argocd-redis | david | Agent (Worker) |

한눈에 보면 묘하게 **의도적인 설계처럼** 보인다. API를 상대하는 컴포넌트 4개는 전부 마스터 노드에, 무거운 조정 루프와 캐시는 워커에. 그런데 고백하자면 — **이 배치에 나는 아무 정책도 넣지 않았다.** nodeSelector도, affinity도, taint도 없다. 순수하게 kube-scheduler가 알아서 앉힌 결과다. 이 글은 그 "우연"이 왜 꽤 합리적인 모양이 되었는지, 그리고 어디까지 우연에 기대도 되는지에 대한 해부다.

## 각 컴포넌트는 무슨 일을 하나

배치를 평가하려면 먼저 각자의 직무를 알아야 한다.

- **argocd-server** — UI/API 게이트웨이. 사람과 CLI가 접속하는 얼굴. 실제 동기화는 하지 않는다.
- **argocd-repo-server** — Git 클론 + `helm template`/kustomize 렌더링 담당. **CPU 스파이크의 진원지**. 매니페스트 생성이 몰리면 여기가 먼저 뜨겁다.
- **argocd-application-controller** — 진짜 두뇌. 79개 앱의 desired(Git) vs live(클러스터) 를 끊임없이 비교하고 sync/selfHeal을 실행하는 조정 루프. **K8s API를 가장 많이 두드리는 컴포넌트**이자 메모리 최대 소비자.
- **argocd-redis** — repo-server 렌더 결과와 컨트롤러 상태의 캐시. 상태는 휘발성 — 죽어도 재계산하면 된다.
- **applicationset / dex / notifications / image-updater** — 앱 템플릿 생성, SSO, 알림, 이미지 자동 갱신. 전부 가볍다.

실측(kubectl top)을 보면 직무 설명이 그대로 숫자로 나온다:

```
argocd-application-controller-0   4m   498Mi   ← 메모리 챔피언 (requests 512Mi 딱 맞게 씀)
argocd-repo-server                1m   110Mi   ← 평시엔 조용, 렌더링 때 스파이크
argocd-server                     2m    36Mi
argocd-redis                      4m    10Mi
나머지                            ~1m   30-60Mi
```

## 스케줄러는 왜 이렇게 앉혔나

K3s의 중요한 특성: **마스터 노드에 기본 taint가 없다.** kubeadm 클러스터라면 control-plane taint 때문에 일반 워크로드가 마스터에 못 올라가지만, K3s는 마스터도 그냥 큰 워커다. 그래서 스케줄러 입장에서 6노드는 성격이 아니라 **잔여 용량**으로만 구분된다.

우리 노드 스펙이 힌트를 준다:

| 노드 | CPU | RAM | 역할 |
|---|---|---|---|
| ilwon | 12c | 32G | control-plane + NVMe 1TB |
| isagal | 40c | 16G | worker (최다 코어) |
| lemuel | 4c | 32G | control-plane (상시 과부하로 종종 cordon) |
| louise | 8c | 16G | worker |
| david | 6c | 16G | worker |
| solomon | 4c | 16G | control-plane (백업 전용 성향) |

ilwon은 **클러스터에서 가장 균형 잡힌 큰 노드**다. 스케줄러의 기본 스코어링(LeastAllocated + 분산)이 잔여 용량 큰 ilwon에 스테이트리스 4총사를 몰아주고, 나머지를 louise/david에 뿌린 건 자연스러운 결과다. 의도가 아니라 **용량의 중력**이다.

## 우연치고는 좋은 배치인 이유

그런데 결과물을 뜯어보면 교과서적 설계와 상당히 겹친다.

**1. application-controller가 API 서버와 "가깝다"** — 는 착각을 먼저 깨야 한다. controller는 louise(워커)에 있다. 하지만 K3s HA에서 각 노드의 kubelet/클라이언트는 로컬 로드밸런서를 통해 아무 마스터 API에나 붙는다. LAN 홈랩에서 노드 간 RTT는 밀리초 미만 — **API 근접성은 이 규모에선 배치 기준이 될 수 없다.** 오히려 중요한 건 다음 항목이다.

**2. 두뇌(controller)와 얼굴(server)이 다른 노드에 있다.** ilwon이 통째로 죽어도 UI/API만 죽지, 조정 루프는 louise에서 계속 돈다. 반대로 louise가 죽으면 sync는 멈추지만 UI로 상태는 볼 수 있다. 단일 장애가 "관측 불능 + 조정 불능"을 동시에 만들지 않는 분산 — 이건 우연히 얻은 복원력이다.

**3. GitOps의 본질적 안전망.** 여기서 가장 중요한 사실: **ArgoCD가 전멸해도 워크로드는 멀쩡하다.** ArgoCD는 배포 파이프라인이지 런타임 의존성이 아니다. 실제로 며칠 전 solomon(마스터 1대)이 10분간 NotReady로 플랩해 settlement 계열이 연쇄 재기동되는 사고가 있었는데, ArgoCD는 ilwon/louise/david에 앉아 있던 덕에 무사했고, 복구 조정을 계속 수행했다. 만약 ArgoCD 전체가 solomon에 몰려 있었다면? 워크로드는 여전히 돌았겠지만 selfHeal이 멈춘 채로 사고를 맞았을 것이다.

## 어디까지 우연에 기대면 안 되는가

이 배치의 약점도 명확하다. 전부 "다음 리스케줄 때 무너질 수 있는 우연"이라는 점이다.

**1. 전 컴포넌트 단일 replica.** 홈랩에선 합리적 선택이지만, ilwon 재부팅 한 번이면 UI·렌더링·SSO가 동시에 몇 분 사라진다. 다행히 controller는 다른 노드라 sync 루프는 산다 — 그러나 이것도 보장이 아니라 현재 상태일 뿐이다.

**2. 재스케줄 복권.** 노드 드레인 한 번, 재부팅 한 번이면 스케줄러는 그때의 잔여 용량으로 다시 주사위를 굴린다. server+controller가 같은 노드에 앉는 날이 올 수 있고, 그날부터 그 노드는 GitOps 단일 장애점이 된다.

**3. lemuel/solomon 함정.** 우리 클러스터에서 lemuel은 CPU 과부하로 종종 cordon되고, solomon은 방금도 플랩 전력이 있다. 스케줄러는 그 이력을 모른다. 다음 리스케줄에서 controller가 solomon에 앉는 걸 막는 장치가 현재 없다.

## 최소 비용의 개입 — 정책은 세 줄이면 된다

홈랩에서 ArgoCD를 3-replica HA로 만드는 건 오버엔지니어링이다(공식 HA 매니페스트는 redis-sentinel 3개 + 컨트롤러 샤딩까지 끌고 온다). 대신 **"우연을 계약으로"** 바꾸는 최소 개입 두 가지면 충분하다.

```yaml
# 1) 두뇌와 얼굴은 같은 노드에 앉히지 않는다 (server 쪽에 안티어피니티)
affinity:
  podAntiAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 100
        podAffinityTerm:
          labelSelector:
            matchLabels:
              app.kubernetes.io/name: argocd-application-controller
          topologyKey: kubernetes.io/hostname

# 2) 불안정 이력 노드 기피 (controller 쪽)
affinity:
  nodeAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 100
        preference:
          matchExpressions:
            - key: kubernetes.io/hostname
              operator: NotIn
              values: [solomon, lemuel]
```

`preferred`(soft)로 두는 게 핵심이다. 홈랩에선 노드가 자주 드나들기 때문에 `required`(hard)로 걸면 어느 날 파드가 Pending에 갇힌다. 정책은 "가능하면 이렇게"까지만 말하고, 최후엔 스케줄러에게 양보해야 한다.

여기에 하나 더 얹는다면 `priorityClassName`. 노드 메모리 압박 시 ArgoCD가 일반 앱보다 먼저 쫓겨나지 않게 하는 것 — 사고 복구 도구는 사고 중에 살아 있어야 가치가 있다.

## 고찰 — 배치도는 시스템의 자화상이다

이번 분석에서 얻은 교훈은 세 문장으로 줄일 수 있다.

1. **K3s에서 "마스터/워커"는 스케줄러에게 존재하지 않는 구분이다.** taint를 안 쓰는 순간 배치는 순전히 용량 게임이 되고, 그 결과가 그럴듯해 보여도 그것은 설계가 아니라 기상 현상이다.
2. **GitOps 컨트롤러의 HA는 워크로드 HA와 다른 문제다.** ArgoCD가 죽어도 서비스는 산다. 그래서 풀 HA 대신 "두뇌와 얼굴의 분리 + 불안정 노드 기피"라는 훨씬 싼 보험이 홈랩의 정답이 된다.
3. **좋은 우연을 발견하면 계약으로 승격시켜라.** 지금 배치가 마음에 든다면, 그게 다음 재부팅에도 유지되도록 soft affinity 세 줄을 넣는 것 — 그것이 우연과 설계의 차이다.

관제탑이 어디 앉아 있는지 오늘 처음 확인했다면, 그 배치는 아직 당신의 설계가 아니다. 내일도 같은 자리에 앉아 있게 만들었을 때 비로소 설계가 된다.

---

*6노드 K3s 홈랩(lemuel 클러스터), ArgoCD 79 apps, 2026-07-22 실측 기준. 수치는 `kubectl top` / `kubectl get pods -o wide` 스냅샷.*
