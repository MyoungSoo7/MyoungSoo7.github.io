---
layout: post
title: "쿠버네티스 3일차 — ConfigMap / Secret / Volume / PVC"
date: 2026-05-11 09:00:00 +0900
categories: [infra, kubernetes]
tags: [kubernetes, configmap, secret, volume, pvc, persistent-volume, storage]
---

[2일차]({% post_url 2026-05-10-kubernetes-day2-pod-deployment-service %}) 까지 우리는 **Pod 를 띄우고 Service 로 노출** 하는 법을 배웠습니다. 그런데 진짜 운영에서는 두 가지가 더 필요합니다.

> "DB 비밀번호는 어디 두지?"
> "Pod 가 죽었다가 살아나면 데이터는?"

3일차는 이 두 가지 — **앱 설정** 과 **데이터 영속성** — 을 다루는 4종 세트를 손으로 만들어 봅니다.

> 이 글에서 다루는 것
> - **ConfigMap**: 환경변수 / 설정파일을 클러스터 차원에서 관리
> - **Secret**: 비밀번호 / API 키를 base64 + RBAC 로 보호
> - **Volume**: Pod 라이프사이클을 넘어선 데이터 저장
> - **PV / PVC**: 동적으로 디스크를 할당받는 표준 인터페이스

---

## 1. ConfigMap — 설정값을 코드 밖으로

### 안티패턴: 도커 이미지에 설정 박기

```dockerfile
ENV DATABASE_URL=postgres://prod-db:5432/...
ENV JWT_SECRET=hardcoded-please-no
```

이렇게 하면 **개발/스테이징/프로덕션마다 이미지를 새로 빌드** 해야 합니다. 환경별로 이미지 N개라니, 컨테이너의 의미가 사라집니다.

### 패턴: ConfigMap 으로 빼기

```yaml
# configmap-app.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  LOG_LEVEL: "INFO"
  FEATURE_NEW_UI: "true"
  application.yml: |
    spring:
      datasource:
        url: jdbc:postgresql://db:5432/lemuel
        hikari:
          maximum-pool-size: 20
```

### Pod 에서 쓰는 두 가지 방법

```yaml
# 방법 A: 환경변수로
spec:
  containers:
    - name: web
      image: my-app:1.0
      envFrom:
        - configMapRef: { name: app-config }   # 모든 키를 env 로

# 방법 B: 파일로 마운트
      volumeMounts:
        - name: cfg
          mountPath: /etc/app
  volumes:
    - name: cfg
      configMap: { name: app-config }
# → /etc/app/application.yml 파일이 자동 생성
```

> ⚠️ ConfigMap 변경은 환경변수로 주입한 경우 **Pod 재시작이 필요** 합니다. 파일 마운트면 ~1분 후 자동 갱신.

---

## 2. Secret — 비밀번호 / API 키 / 인증서

ConfigMap 과 거의 똑같은데, 다음이 다릅니다.

| | ConfigMap | Secret |
|---|---|---|
| 용도 | 일반 설정 | 비밀번호, 토큰, 인증서 |
| 저장 형식 | 평문 | **base64 인코딩** (암호화 X) |
| RBAC 권한 | 비교적 느슨하게 줘도 됨 | **엄격하게** 제한 (안 그러면 Secret 의미 X) |
| 메모리 | tmpfs | tmpfs (디스크 안 닿음) |

```bash
# Secret 만들기 (키-값)
kubectl create secret generic db-cred \
  --from-literal=username=lemuel \
  --from-literal=password='S3cret!@#'

# yaml 로 만들 때는 base64 인코딩
echo -n 'S3cret!@#' | base64
# UzNjcmV0IUAj
```

```yaml
apiVersion: v1
kind: Secret
metadata: { name: db-cred }
type: Opaque
data:
  username: bGVtdWVs        # base64("lemuel")
  password: UzNjcmV0IUAj    # base64("S3cret!@#")
```

### ⚠️ Secret 의 가장 큰 함정

**base64 는 암호화가 아닙니다.** 누구든 디코딩하면 평문입니다. 그래서 다음 둘 중 하나는 반드시 해야 합니다.

1. **etcd 암호화 켜기** (kube-apiserver `--encryption-provider-config`)
2. **Sealed Secrets / SOPS / External Secrets** 같은 도구로 git 에 암호화된 형태로 저장

저는 르무엘 프로젝트에서 **SOPS + age** 조합을 씁니다. git 에 들어가도 안전한 형태로요.

```bash
# 평문 secret.yaml → 암호화된 secret.enc.yaml
sops --age age1abc... -e secret.yaml > secret.enc.yaml
git add secret.enc.yaml  # 마음 편하게 커밋
```

---

## 3. Volume — Pod 라이프사이클을 넘어선 저장

### 컨테이너 안 디스크는 일회용

도커 컨테이너의 파일시스템은 **컨테이너가 죽으면 함께 사라집니다.** Pod 도 마찬가지입니다.

> "그럼 DB 데이터는? 업로드된 사진은?"

쿠버네티스에서는 **Volume** 을 Pod 에 붙여서 해결합니다.

### Volume 종류 — 자주 만나는 4가지

| 종류 | 수명 | 용도 |
|---|---|---|
| `emptyDir` | Pod 와 같이 죽음 | 컨테이너 간 임시 공유 (sidecar 캐시) |
| `hostPath` | 노드와 같이 죽음 | 노드 로컬 파일 (테스트, 비추) |
| `configMap` / `secret` | 별도 | 앞에서 본 설정 마운트 |
| **`persistentVolumeClaim`** | **클러스터 단위** | 운영용 디스크 (DB, 업로드 등) |

운영에서 거의 다 PVC 입니다.

```yaml
# emptyDir 예시 (sidecar 로그 수집)
spec:
  volumes:
    - name: logs
      emptyDir: {}
  containers:
    - name: app
      volumeMounts:
        - { name: logs, mountPath: /var/log/app }
    - name: log-shipper
      volumeMounts:
        - { name: logs, mountPath: /logs, readOnly: true }
```

---

## 4. PV / PVC — 표준 디스크 인터페이스

Volume 종류가 너무 많고 클라우드마다 다릅니다 (EBS, GCE PD, Azure Disk, Ceph, NFS, …). 그래서 쿠버네티스가 한 겹 추상화를 깔아줍니다.

### 두 명의 등장인물

- **PersistentVolume (PV)**: "여기 디스크 100GB 있어요" — **공급** 측. 보통 클러스터 관리자나 StorageClass 가 자동 생성.
- **PersistentVolumeClaim (PVC)**: "디스크 50GB 필요해요" — **요구** 측. 개발자가 yaml 에 작성.

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata: { name: db-data }
spec:
  accessModes: [ "ReadWriteOnce" ]   # 단일 노드 read-write (대부분 DB)
  resources:
    requests:
      storage: 20Gi
  storageClassName: standard          # 클라우드별 기본값
```

```yaml
# Pod 에서 사용
spec:
  containers:
    - name: postgres
      image: postgres:17
      volumeMounts:
        - { name: data, mountPath: /var/lib/postgresql/data }
  volumes:
    - name: data
      persistentVolumeClaim: { claimName: db-data }
```

### Dynamic Provisioning — 가장 많이 쓰는 흐름

옛날에는 관리자가 PV 를 미리 N 개 만들어 놓고 PVC 가 거기서 골랐습니다. 지금은 **PVC 를 만들면 StorageClass 가 PV 를 즉시 자동 생성** 합니다.

```
[개발자]                        [클러스터]
   │                                │
   │  PVC apply (20Gi 필요)         │
   ├───────────────────────────────►│
   │                                │── StorageClass 발동
   │                                │── 클라우드에 EBS 20GB 생성
   │                                │── PV 객체 자동 생성
   │                                │── PVC 와 자동 바인딩
   │  Pod 가 PVC 마운트              │
   │  → 디스크 사용                  │
```

### AccessMode 3가지

| 모드 | 의미 | 언제 |
|---|---|---|
| `ReadWriteOnce` (RWO) | 한 노드만 read-write | DB, 단일 인스턴스 |
| `ReadOnlyMany` (ROX) | 여러 노드 read-only | 정적 자원 공유 |
| `ReadWriteMany` (RWX) | 여러 노드 read-write | 공유 파일시스템 (NFS, EFS) |

대부분 **RWO** 면 충분합니다. RWX 는 NFS 같은 공유 스토리지를 깐 경우만.

---

## 5. 실습 — Postgres + ConfigMap + Secret + PVC 한 통

```yaml
# postgres-stack.yaml
---
apiVersion: v1
kind: ConfigMap
metadata: { name: postgres-config }
data:
  POSTGRES_DB: lemuel
---
apiVersion: v1
kind: Secret
metadata: { name: postgres-secret }
type: Opaque
data:
  POSTGRES_USER: bGVtdWVs              # lemuel
  POSTGRES_PASSWORD: UzNjcmV0IUAj      # S3cret!@#
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata: { name: postgres-data }
spec:
  accessModes: [ "ReadWriteOnce" ]
  resources: { requests: { storage: 5Gi } }
---
apiVersion: apps/v1
kind: Deployment
metadata: { name: postgres }
spec:
  replicas: 1
  selector: { matchLabels: { app: postgres } }
  template:
    metadata: { labels: { app: postgres } }
    spec:
      containers:
        - name: postgres
          image: postgres:17
          envFrom:
            - configMapRef: { name: postgres-config }
            - secretRef: { name: postgres-secret }
          ports: [ { containerPort: 5432 } ]
          volumeMounts:
            - { name: data, mountPath: /var/lib/postgresql/data }
      volumes:
        - name: data
          persistentVolumeClaim: { claimName: postgres-data }
```

```bash
kubectl apply -f postgres-stack.yaml
kubectl get pvc,deploy,pods
# pvc 가 Bound 되고 pod 가 Running 되면 성공
```

이제 Pod 를 죽여도 **데이터는 살아있습니다.**

```bash
kubectl delete pod -l app=postgres
# 새 Pod 가 뜨면서 같은 PVC 를 다시 마운트
```

---

## 핵심 한 줄 정리

- **ConfigMap**: 환경별 설정 분리. envFrom 또는 파일 마운트
- **Secret**: 비밀번호. base64 ≠ 암호화. SOPS / Sealed Secrets 권장
- **Volume**: Pod 가 죽어도 살아남는 저장소. emptyDir / configMap / **PVC**
- **PV / PVC**: 표준 디스크 인터페이스. Dynamic Provisioning 으로 자동 생성
- **운영 90% 는 PVC + ReadWriteOnce + StorageClass**

4일차에서는 드디어 **무중단 배포** — RollingUpdate / Canary / Blue-Green / Rollback — 을 손으로 굴려봅니다.

---

> 이 글은 르무엘 사내 K8s 7일 입문 코스의 3일차 자료입니다. [1일차]({% post_url 2026-05-09-kubernetes-day1-architecture %}) → [2일차]({% post_url 2026-05-10-kubernetes-day2-pod-deployment-service %}) 와 함께 읽으면 흐름이 매끄럽습니다.
