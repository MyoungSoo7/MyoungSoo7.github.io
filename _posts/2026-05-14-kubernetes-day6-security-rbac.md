---
layout: post
title: "쿠버네티스 6일차 — 보안 + RBAC + NetworkPolicy"
date: 2026-05-14 09:00:00 +0900
categories: [infra, kubernetes]
tags: [kubernetes, rbac, networkpolicy, security, serviceaccount]
---

운영하다 보면 만나는 가장 무서운 문장:

> "그 클러스터 전권 토큰이 git 에 있었습니다."

6일차는 **누가 무엇을 할 수 있는지** 를 명시적으로 정하는 날입니다. 안 하면 전부 다 됨 = 모두가 root.

> 이 글에서 다루는 것
> - **RBAC**: 사람/앱이 무슨 API 를 호출할 수 있나
> - **ServiceAccount**: 앱이 클러스터에 접근하는 신원
> - **NetworkPolicy**: Pod 간 트래픽 제한
> - **Secret 보안**: SOPS / Sealed Secrets / etcd 암호화
> - **Pod Security Admission**: 컨테이너 자체의 권한 제한

---

## 1. RBAC — Role-Based Access Control

### 4 종류의 객체

```
[Role / ClusterRole]      ← 권한의 묶음 (read pods, edit secrets, …)
        ↑ bound to
[RoleBinding / ClusterRoleBinding]
        ↑
[Subject: User / Group / ServiceAccount]
```

- **Role** = 네임스페이스 한정 / **ClusterRole** = 클러스터 전역
- **RoleBinding** 으로 Subject 와 Role 을 연결

### 예 — 개발자에게 prod 네임스페이스 read-only

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata: { namespace: prod, name: pod-reader }
rules:
  - apiGroups: [""]
    resources: ["pods", "pods/log"]
    verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata: { namespace: prod, name: dev-can-read }
subjects:
  - kind: User
    name: dev-1@lemuel.co.kr
    apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: pod-reader
  apiGroup: rbac.authorization.k8s.io
```

### 황금률 — Least Privilege

> "필요한 만큼만, 더는 안 준다."

- ❌ `cluster-admin` 을 모두에게
- ✅ Role 분리: `viewer`, `editor`, `admin` (네임스페이스별)

---

## 2. ServiceAccount — 앱의 신원

Pod 도 클러스터 API 를 호출할 수 있습니다 (자기 자신 정보 읽기, ConfigMap 가져오기, …). 이때 신원이 **ServiceAccount** 입니다.

### 기본 ServiceAccount 의 함정

각 네임스페이스에 `default` ServiceAccount 가 자동 생성. **모든 Pod 가 명시 안 하면 default 를 씀.** RBAC 미설정이면 기본권한이 의외로 넓을 수 있습니다.

### 패턴 — Pod 마다 전용 SA + 최소 권한

```yaml
apiVersion: v1
kind: ServiceAccount
metadata: { name: cert-minter, namespace: academy }
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata: { namespace: academy, name: cert-minter }
rules:
  - apiGroups: [""]
    resources: ["secrets"]
    verbs: ["get"]
    resourceNames: ["minter-key"]    # 특정 Secret 만
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata: { namespace: academy, name: cert-minter }
subjects: [ { kind: ServiceAccount, name: cert-minter } ]
roleRef:
  kind: Role
  name: cert-minter
  apiGroup: rbac.authorization.k8s.io
---
# Deployment 에 명시
spec:
  template:
    spec:
      serviceAccountName: cert-minter
```

---

## 3. NetworkPolicy — Pod 간 방화벽

기본값은 **모든 Pod 가 모든 Pod 와 통신 가능**. 운영 클러스터에서는 위험합니다. NetworkPolicy 로 화이트리스트만 허용하게 좁힙니다.

### 예 — frontend 만 backend 호출 가능

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: { name: backend-from-frontend, namespace: prod }
spec:
  podSelector: { matchLabels: { app: backend } }
  policyTypes: ["Ingress"]
  ingress:
    - from:
        - podSelector: { matchLabels: { app: frontend } }
      ports:
        - protocol: TCP
          port: 8080
```

### 함정 — CNI 가 지원해야 동작

NetworkPolicy 는 **선언만 한 것** 이고, 실제 강제는 CNI 가 합니다.

| CNI | NetworkPolicy 지원 |
|---|---|
| Flannel (기본) | ❌ 무시됨 |
| Calico | ✅ |
| Cilium | ✅✅ (eBPF, 가장 강력) |

지원 CNI 가 아니면 yaml 만 들어가고 트래픽은 다 통합니다. 반드시 확인.

---

## 4. Secret 보안 강화

3일차에서 봤듯 **Secret 의 base64 는 암호화가 아닙니다.** 추가로 다음 셋 중 하나는 거의 필수.

### A) etcd 암호화

```yaml
# kube-apiserver --encryption-provider-config=enc.yaml
kind: EncryptionConfiguration
apiVersion: apiserver.config.k8s.io/v1
resources:
  - resources: ["secrets"]
    providers:
      - aescbc:
          keys:
            - name: key1
              secret: <base64 key>
      - identity: {}
```

저장소 (etcd 데이터) 차원에서 암호화.

### B) SOPS + age — git 친화적

```bash
# 평문 secret.yaml → 암호화된 .enc.yaml
sops --age age1abc... -e secret.yaml > secret.enc.yaml
git add secret.enc.yaml   # 안전하게 커밋

# 배포 시 복호화
sops -d secret.enc.yaml | kubectl apply -f -
```

저는 lemuel-secrets 를 SOPS+age 로 굴립니다. age 키만 안전하게 보관하면 git 에 들어가도 OK.

### C) Sealed Secrets — kubeseal

```bash
# 평문 secret.yaml → SealedSecret (클러스터만 복호화 가능)
kubeseal -f secret.yaml -w sealed-secret.yaml
git add sealed-secret.yaml
kubectl apply -f sealed-secret.yaml
```

---

## 5. Pod Security — 컨테이너 자체 권한

Pod Security Admission (Standards):

| 등급 | 의미 |
|---|---|
| `privileged` | 모든 권한 (위험) |
| `baseline` | 흔한 위험만 차단 |
| `restricted` | 강력하게 제한 (권장) |

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: prod
  labels:
    pod-security.kubernetes.io/enforce: restricted
```

### 컨테이너 수준 보안 컨텍스트

```yaml
spec:
  containers:
    - name: app
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        readOnlyRootFilesystem: true
        allowPrivilegeEscalation: false
        capabilities:
          drop: ["ALL"]
```

이걸 안 박으면 컨테이너 안에서 root 로 돌아갑니다 — 컨테이너 탈출(escape) 시 노드 root.

---

## 6. 보안 체크리스트 (운영 시작 전)

- [ ] 모든 사람의 `kubectl` kubeconfig 가 다 다른 user 로 분리
- [ ] `cluster-admin` Binding 은 최소 (1~2명)
- [ ] 각 앱이 전용 ServiceAccount + 최소 권한 Role
- [ ] CNI 가 NetworkPolicy 지원하고, default-deny 가 적용됨
- [ ] Secret 은 SOPS / Sealed Secrets / etcd 암호화 중 최소 1
- [ ] Namespace 에 `pod-security.kubernetes.io/enforce: baseline` 이상
- [ ] 컨테이너에 `runAsNonRoot: true` + `drop: ["ALL"]`

---

## 핵심 한 줄 정리

- **RBAC**: Role + RoleBinding + Subject. Least Privilege 고집
- **ServiceAccount**: Pod 의 신원. 기본 SA 의존하지 말고 전용 SA + 최소 권한
- **NetworkPolicy**: Pod 간 방화벽. **CNI 가 지원해야 동작** (Calico/Cilium)
- **Secret**: SOPS / Sealed Secrets / etcd 암호화 중 하나 필수
- **Pod Security**: restricted 등급 + runAsNonRoot + capabilities drop

마지막 7일차에서는 지금까지 배운 모든 것을 모아서 **종합 프로젝트** — 작은 SaaS 클러스터 운영 — 을 만들어 봅니다.

---

> 시리즈 [1일차]({% post_url 2026-05-09-kubernetes-day1-architecture %}) 부터 보시면 좋습니다.
