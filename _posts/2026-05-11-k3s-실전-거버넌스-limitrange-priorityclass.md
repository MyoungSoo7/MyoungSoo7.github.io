---
layout: post
title: "K3s 실전 3편 — LimitRange / ResourceQuota / PriorityClass 로 OOM 방어"
date: 2026-05-11 22:00:00 +0900
categories: [infra, kubernetes, k3s]
tags: [k3s, kubernetes, limitrange, resourcequota, priorityclass, oom, governance, helm]
---

[2편]({% post_url 2026-05-11-k3s-실전-솔로몬-스토리지-티어 %}) 에서 솔로몬에 DB 8 개를 박았습니다. 이제 진짜 무서운 건 **OOM 으로 DB 가 죽는 일** 입니다. 메모리 burst 한 앱이 솔로몬을 압박하면 PostgreSQL 이 evict 당해버려요. 이걸 막기 위해 K3s 클러스터 전체에 **3가지 거버넌스** 를 깔았습니다.

> 이 글에서 다루는 것
> - **LimitRange** — 컨테이너 리소스 default / max / **maxLimitRequestRatio**
> - **ResourceQuota** — namespace 단위 자원 천장
> - **PriorityClass** — OOM 시 누가 살아남을지 5 단 등급
> - **memory limits == requests** 강제 패턴 (DB OOM 보호의 핵심)
> - Helm 표준 템플릿(`_limitrange.tpl`) 으로 모든 차트가 자동 적용

---

## 1. LimitRange — 컨테이너 리소스 안전망

### 왜 필요한가

개발자가 `resources:` 없이 Deployment yaml 을 쓰면 K3s 는 그 컨테이너에 무한 메모리를 허용합니다. 한 노드의 RAM 이 다 빨려도 막을 수가 없어요. LimitRange 는 **namespace 안의 모든 컨테이너에 자동으로 default request/limit 를 주입** 합니다.

### 표준 템플릿 (`charts/academy/templates/_limitrange.tpl`)

```yaml
{{- define "lemuel.limitrange" -}}
apiVersion: v1
kind: LimitRange
metadata:
  name: {{ .Release.Name }}-limits
spec:
  limits:
    - type: Container
      default:                  # limits 미지정 시 자동 주입
        cpu: 500m
        memory: 512Mi
      defaultRequest:           # requests 미지정 시
        cpu: 100m
        memory: 128Mi
      max:                      # 절대 상한
        cpu: 4000m
        memory: 4Gi
      min:
        cpu: 50m
        memory: 64Mi
      maxLimitRequestRatio:     # ★★★ 핵심
        cpu: 8
        memory: {{ .Values.limitRange.burstRatio.memory | default 2 }}
{{- end -}}
```

각 차트의 `templates/limitrange.yaml` 한 줄로 적용:

```yaml
{{- include "lemuel.limitrange" . }}
```

### `maxLimitRequestRatio.memory` 가 핵심

이게 OOM 방어의 본체입니다.

| 컨테이너 종류 | memory ratio | 의미 |
|---|---|---|
| 일반 앱 | `2` | limits 가 requests 의 2 배까지만 (적당한 burst 허용) |
| **DB** | **`1`** ★ | **limits == requests 강제** → burst 절대 금지 → OOM 보호 |
| CPU bound 워커 | `1` | 메모리는 burst 안 하고, CPU 는 burst 8 |

DB 차트 `values.yaml`:

```yaml
limitRange:
  burstRatio:
    memory: 1   # ★ DB 는 무조건 1
```

이렇게 두면 PostgreSQL Pod 가 만들어질 때 K3s API server 가 **memory limits != requests 면 거절** 합니다. DB 가 burst 로 메모리를 더 받아서 다른 Pod 를 evict 시키는 시나리오 자체가 막힙니다.

---

## 2. ResourceQuota — namespace 천장

LimitRange 가 컨테이너 단위라면 ResourceQuota 는 **namespace 단위 총합 제한** 입니다.

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: lemuel-quota
  namespace: jen-prod
spec:
  hard:
    requests.cpu: "10"
    requests.memory: 16Gi
    limits.cpu: "30"
    limits.memory: 32Gi
    pods: "30"
    persistentvolumeclaims: "10"
    services: "20"
```

이걸 모든 운영 namespace 에 일괄 깔아두면, 누가 실수로 `replicas: 1000` 을 쳐도 namespace 천장에 막혀서 클러스터 전체가 박살나는 사고는 안 납니다.

### 일괄 적용 — 하나의 helm chart 로

8 개 namespace 에 각각 LimitRange + Quota 를 박는 대신, "lemuel-governance" 라는 별도 차트 하나에 다 몰아넣었습니다:

```yaml
# charts/lemuel-governance/templates/policy.yaml
{{- $namespaces := list "argocd" "velero" "academy-staging" "academy-prod" \
                       "jen-prod" "settlement-prod" "asat" -}}
{{- range $ns := $namespaces }}
---
apiVersion: v1
kind: LimitRange
metadata:
  name: lemuel-default
  namespace: {{ $ns }}
spec:
  # ... 위 표준 템플릿 그대로
---
apiVersion: v1
kind: ResourceQuota
metadata:
  name: lemuel-quota
  namespace: {{ $ns }}
spec:
  # ... 위 quota 그대로
{{- end }}
```

ArgoCD 가 이걸 자동 sync → 새 namespace 추가하면 governance 만 다시 sync 하면 끝.

---

## 3. PriorityClass — OOM 살벌한 순간의 우선순위

LimitRange + Quota 로도 못 막는 시나리오가 있습니다: **노드 전체 RAM 이 진짜 부족할 때**. 이때 K3s 의 kubelet 이 누구를 evict 할지 결정합니다. PriorityClass 가 없으면 무작위(QoS class 만 보고). 5 단 우선순위를 깔아서 **DB 가 가장 마지막에 죽도록** 보장합니다.

```yaml
# 1) 시스템 코어 (절대 죽으면 안 되는 것)
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata: { name: lemuel-system-critical }
value: 2000000000   # 거의 시스템 critical 급
description: "kube-system, argocd, velero, monitoring agents"
---
# 2) DB / 스토리지
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata: { name: lemuel-critical }
value: 1000000000
description: "PostgreSQL, Redis, MinIO 등 stateful 워크로드"
---
# 3) 운영 앱
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata: { name: lemuel-production }
value: 100000
description: "운영 앱 — settlement, jen, academy 본체"
---
# 4) 일반
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata: { name: lemuel-normal }
value: 1000
description: "기본값 (staging 앱 등)"
---
# 5) 배치 / 테스트
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata: { name: lemuel-batch-low }
value: 10
description: "야간 배치, 임시 테스트 — OOM 시 가장 먼저 evict"
```

### 적용 방법

각 워크로드 차트에서 `priorityClassName` 한 줄:

```yaml
# DB
spec:
  template:
    spec:
      priorityClassName: lemuel-critical

# 운영 앱
spec:
  template:
    spec:
      priorityClassName: lemuel-production

# 야간 배치
spec:
  template:
    spec:
      priorityClassName: lemuel-batch-low
```

### 시나리오 검증

솔로몬 RAM 이 16GB 인데 합산 limits 가 18GB 가 되어서 압박이 생겼다고 치면:

1. 야간 배치 Job (`lemuel-batch-low`) 가 가장 먼저 evict
2. 그래도 부족하면 staging 앱 (`lemuel-normal`) evict
3. 그래도 부족하면 운영 앱 (`lemuel-production`) evict
4. 마지막까지 PostgreSQL (`lemuel-critical`) 은 살아남음
5. kube-system 은 `lemuel-system-critical` 로 절대 보호

→ **DB 데이터 무결성 우선** 이라는 운영 원칙이 K3s 단에서 강제됨.

---

## 4. 실측 — 적용 전 / 후

### 적용 전 (랜덤 OOM)

```
$ kubectl get events --sort-by='.lastTimestamp' | grep Evicted
2026-05-08 03:12  jen-postgres-0      Evicted: The node was low on resource: memory
2026-05-08 03:12  argocd-server-xxx    Evicted: The node was low on resource: memory
2026-05-08 03:13  academy-staging-xxx Evicted: ...
```

DB / 컨트롤플레인 / staging 이 같이 죽음. 데이터 손실 발생.

### 적용 후 (배치만 죽음)

```
$ kubectl get events --sort-by='.lastTimestamp' | grep Evicted
2026-05-11 04:30  nightly-report-job  Evicted: The node was low on resource: memory
2026-05-11 04:30  staging-test-pod    Evicted: ...
```

배치 + staging 만 evict, DB / 운영 / argocd 살아남음 ✅

---

## 5. argocd 가 ratio 4 로 LimitRange 위반 — 예외 처리

`argocd-application-controller` 가 자체적으로 limits=2Gi requests=512Mi 를 박아서 **ratio 4** 가 됩니다. 표준 ratio 2 를 어겨서 새 Pod 가 안 뜨는 사고가 있었습니다.

해결: argocd namespace 만 LimitRange ratio 8 로 풀어줌.

```yaml
# charts/lemuel-governance/values.yaml
namespaces:
  argocd:
    burstRatio:
      memory: 8   # ArgoCD 만 예외
  velero:
    burstRatio:
      memory: 4
  default:
    burstRatio:
      memory: 2
```

원칙은 어기더라도 명시적으로 어기는 게 낫습니다 (값 변경 이력이 git 에 남음).

---

## 6. 정리

| 거버넌스 | 단위 | 막는 시나리오 |
|---|---|---|
| LimitRange | 컨테이너 | "메모리 무한 요청" |
| LimitRange `ratio.memory: 1` | DB 컨테이너 | "DB burst 로 다른 Pod evict" |
| ResourceQuota | namespace | "한 팀이 클러스터 다 잡음" |
| PriorityClass (5 단) | Pod | "OOM 시 DB 가 죽음" |

이 4 개 다 거는 데 한 시간이면 됩니다. **그런데 한 번 안 걸어두면 사고는 새벽 3시에 옵니다.** 미리 깔아두는 게 압도적으로 싸요.

---

## 다음 글

- **K3s 실전 4편 — flannel cross-node DNS 함정과 NodeLocal DNSCache**
- 거버넌스 다 깔았더니 다음 사고는 DNS 였습니다…
