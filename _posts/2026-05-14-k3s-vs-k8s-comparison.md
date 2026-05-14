---
layout: post
title: "K3s vs K8s — 같은 것, 다른 것, 그리고 5노드 온프레미스에서 K3s 를 고른 이유"
date: 2026-05-14 17:30:00 +0900
categories: [infra, kubernetes, k3s]
tags: [kubernetes, k3s, comparison, devops, onprem, lightweight]
---

> "K3s 가 K8s 의 경량 버전이라던데 실제로 뭐가 다른가?" 라는 질문은 K8s 를 처음 도입할 때 꼭 한 번 마주칩니다. 결론부터 말하면 **K3s 는 K8s 의 fork 가 아니라 K8s 100% 호환 distribution** 입니다. 같은 API, 같은 manifest, 같은 kubectl. 다른 건 패키징 / 의존성 / 기본 컴포넌트 선택. 본인이 5노드 온프레미스 클러스터에 K3s 를 고른 이유는 그 차이가 정확히 본인 시나리오에 맞아떨어졌기 때문입니다.

## 1. K3s 가 뭔가 — Rancher Labs 의 light distribution

- **만든 곳**: Rancher Labs (현재 SUSE)
- **출시**: 2019년 2월
- **CNCF 인증**: 2020년 8월 CNCF Sandbox 진입, 2022년 Incubation
- **이름 유래**: "Kubernetes" 가 K8s (10글자 → K + 8 + s), 그 절반의 무게라는 의미로 K3s

핵심 문구는 **"Lightweight Kubernetes, Production-grade"** 입니다.

## 2. 같은 것 — 100% 호환

K3s 는 K8s 와 호환되는 distribution 이라 다음은 전부 같습니다.

- ✅ Kubernetes API (apps/v1, core/v1, networking.k8s.io/v1, ...)
- ✅ kubectl 명령어 (`kubectl get pods`, `kubectl apply -f`, ...)
- ✅ Manifest YAML (Deployment, Service, Ingress, PVC, ...)
- ✅ Helm chart (chart 변경 없이 그대로 install)
- ✅ ArgoCD / Flux / Velero / Prometheus Operator 등 K8s 생태계 도구 전부
- ✅ CSI / CNI / CRI 인터페이스
- ✅ RBAC / NetworkPolicy / PodSecurity / EncryptionConfig

즉 K8s 에서 돌던 워크로드를 K3s 로 옮기는 데 코드 변경 0. **CNCF 가 K3s 를 "certified Kubernetes" 로 인증한 이유** 가 이것입니다.

## 3. 다른 것 — 패키징과 기본 선택

K3s 와 K8s 의 진짜 차이는 "어떻게 패키징됐는가" 와 "기본값이 무엇인가" 입니다.

### (1) 바이너리 구조

| 항목 | K8s (kubeadm) | K3s |
|------|--------------|-----|
| control-plane 컴포넌트 | kube-apiserver, controller-manager, scheduler 가 각각 별도 프로세스 (Pod) | **단일 바이너리 1개** (`k3s server`) 가 다 포함 |
| worker 컴포넌트 | kubelet + kube-proxy + container runtime 별도 설치 | **단일 바이너리** (`k3s agent`) 가 다 포함 |
| 바이너리 크기 | 합쳐서 1GB+ | **~50-100MB 단일 바이너리** |
| 설치 명령 | kubeadm init / join (multi-step) | **`curl -sfL https://get.k3s.io \| sh -`** (single shot) |

K3s 는 모든 컴포넌트를 하나의 바이너리에 정적 컴파일해서 묶은 형태. 그래서 ARM 라즈베리파이나 메모리 1GB 시스템에서도 돌릴 수 있을 정도로 가볍습니다.

### (2) 기본 데이터스토어

| | K8s | K3s |
|--|-----|-----|
| 기본 | etcd (분산) | **SQLite 파일** (단일 노드) |
| 옵션 | etcd 외엔 사실상 없음 | SQLite / embedded etcd / 외부 etcd / 외부 PostgreSQL / 외부 MySQL |

**K3s 가 SQLite 를 기본으로 쓰는 이유**: 단일 노드 / 엣지 / 개발 환경에서 etcd 클러스터 설정 (TLS, 3-member quorum) 의 복잡도를 제거. 데이터 손실 위험은 있지만 백업으로 대응.

**프로덕션 HA 가 필요하면**: K3s 도 embedded etcd 모드 지원. 3-master 노드에서 K3s 가 자체 etcd 클러스터 구성. (본인 환경이 이 패턴.)

### (3) 기본 포함 컴포넌트

K3s 는 "보통 K8s 클러스터에 추가로 설치하는 것들" 을 처음부터 묶어서 옵니다.

| 영역 | K8s (kubeadm) | K3s |
|------|--------------|-----|
| CNI | 별도 설치 (Calico/Flannel/Cilium 등) | **Flannel 내장** (VXLAN) |
| Service LB | 별도 설치 (MetalLB 등) | **ServiceLB (Klipper-LB) 내장** |
| Ingress | 별도 설치 (Nginx Ingress 등) | **Traefik 내장** |
| Storage | 별도 설치 (rook-ceph, openebs 등) | **local-path-provisioner 내장** |
| DNS | CoreDNS 별도 설치 | CoreDNS 내장 |
| Metrics | metrics-server 별도 설치 | metrics-server 내장 |

내장 컴포넌트가 마음에 안 들면 `--disable=traefik,servicelb,local-storage` 같은 flag 로 끄고 본인이 원하는 걸 깔면 됩니다.

### (4) 제거된 것들 — Legacy / Cloud Provider

K3s 는 K8s 의 in-tree cloud provider 코드를 전부 제거했습니다.

❌ K3s 에서 빠진 것
- AWS / GCP / Azure / OpenStack 의 in-tree cloud provider (이건 어차피 K8s 도 1.27 부터 out-of-tree 이동 중)
- 일부 legacy storage provisioner (in-tree GCE PD, AWS EBS 등 — CSI 로 대체)
- 일부 admission controller (DenyEscalatingExec 등)
- alpha 단계의 일부 feature

이걸 빼서 바이너리 사이즈도 줄고 보안 표면적도 줄였습니다.

### (5) 런타임

| | K8s | K3s |
|--|-----|-----|
| 기본 CRI | containerd 또는 CRI-O 별도 설치 | **containerd 내장** (k3s 바이너리 안에) |
| Docker 지원 | Docker 1.24 이후 제거됨 | `--docker` flag 로 가능 |

K3s 는 containerd 를 바이너리 안에 내장해서 별도 설치할 필요가 없습니다. 본인 환경에서는 일부 노드에 `--docker` flag 로 Docker 도 함께 굴리고 있는데, K3s 가 이걸 지원하는 게 트러블슈팅에 도움됐습니다 (예: 르무엘 노드는 Docker, 일원/솔로몬은 containerd).

## 4. 메모리 / CPU 비교

같은 기본 클러스터 (1 노드, 부하 없음) 기준 idle 리소스 사용량:

| | K8s (kubeadm) | K3s |
|--|--------------|-----|
| 메모리 | ~700MB-1GB | **~200-400MB** |
| CPU idle | 5-10% | **<1%** |
| 디스크 (바이너리) | ~1GB+ | **~50-100MB** |

라즈베리파이 4 (4GB RAM) 같은 작은 머신에 K8s 를 띄우면 OS + kube 만으로 메모리가 절반 이상 차는데, K3s 는 여유 있게 워크로드까지 돌릴 수 있습니다.

## 5. 언제 K8s, 언제 K3s

### K3s 가 적합

- 1~10 노드의 작은 클러스터
- 온프레미스 / 엣지 / 라즈베리파이
- 단일 운영자 또는 작은 팀
- 빠른 셋업 (`curl ... | sh` 한 줄)
- 메모리/디스크 자원 제약
- 학습용 / 개발 환경

### K8s (kubeadm 또는 매니지드) 가 적합

- 50+ 노드 대규모 클러스터
- 엔터프라이즈 환경 (HA 요구사항 매우 엄격)
- AWS EKS / GCP GKE / Azure AKS 같은 매니지드 사용 시 (이미 K8s)
- 특정 CNI/CSI/Ingress 조합이 강제될 때
- 회사 정책으로 "K3s 는 unsupported" 라고 못 박을 때

> 단, **"K3s 는 프로덕션에 부적합" 은 오해**. Rancher 의 매니지드 K3s (Rancher Hosted) 와 자체 클러스터로 운영하는 사례가 다수 있습니다. CNCF 인증 받은 이상 K8s 와 같은 등급.

## 6. 본인 환경 — 왜 K3s 를 골랐나

본인의 르무엘 인프라는 다음과 같습니다.

- 5 노드 온프레미스 (르무엘 4C/32GB, 루이스 i7/16GB, 데이비드 6C/16GB, 일원 12C/14GB + 4TB HDD, 솔로몬 Mac Mini 2014)
- 1인 운영
- 워크로드 30+ 개 (이커머스, AI, 정산, 모니터링, 백업, 퀀트 등)
- AWS/GCP 매니지드 안 씀 (비용 0 목표)

K3s 가 정확히 맞아떨어진 지점:

| 본인 요구 | K3s 적합도 |
|----------|----------|
| 5노드라서 etcd 클러스터 구성이 부담 | embedded etcd 옵션 (3-master HA), SQLite 가 기본이라 1노드 모드도 쉬움 |
| 운영 인력 1인 | `curl ... \| sh` 셋업이 빨라서 시간 절약 |
| Mac Mini 2014 (4GB RAM) 같은 약한 노드 | K3s 메모리 풋프린트가 작아서 control-plane 으로 충분 |
| 자원 최대 활용 | K8s 자체가 차지하는 메모리/CPU 적음 → 워크로드 용량 확보 |
| Helm/ArgoCD/Velero 다 쓰고 싶음 | 호환성 100%, 그대로 사용 |
| AWS in-tree provider 안 씀 | 어차피 빠져있어도 무관 |

만약 노드가 50개였거나, AWS EKS 매니지드 환경이었거나, 회사 정책상 K3s 가 금지였다면 다른 선택을 했을 거예요.

## 7. 실제 운영 후 느낀 차이

### 좋았던 점

- **셋업 속도** — `curl -sfL https://get.k3s.io | K3S_TOKEN=... sh -s - server` 한 줄로 control-plane 가동. kubeadm 의 init/join 다단계 절차 없음.
- **메모리 여유** — Mac Mini 2014 (4GB) 가 control-plane 역할까지 무리없이 소화.
- **Traefik 즉시 사용** — 별도 설치 없이 Ingress 작동. 단순한 케이스에 편리.
- **SQLite → embedded etcd 인플레이스 마이그레이션** — 클러스터 보존하면서 HA 전환 가능 (18분 다운타임으로 30+ ArgoCD 앱 모두 보존, [관련 글](/2026/05/12/k3s-3master-ha-sqlite-etcd-migration/)).

### 의외였던 함정

- **flannel UFW 8472** — 호스트 방화벽이 flannel VXLAN port 를 막으면 cross-node 통신 실패 ([관련 글](/2026/05/11/k3s-flannel-ufw-8472-cross-node-함정/))
- **NodePort 충돌** — Traefik 이 80/443 점유해서 NodePort 30000-32767 외에는 안 됨
- **local-path-provisioner 의 노드 강결합** — PV 가 특정 노드 디스크에 묶여서 Pod 가 그 노드를 떠날 수 없음 (production 에서는 외부 storage 추천)
- **K3s ConfigMap 자동 복원** — local-path-provisioner 설정을 ConfigMap 으로 바꿔도 K3s 가 매니지드 애드온 매번 복원 ([관련 글](/2026/05/12/k3s-local-path-storage-hdd-bind-mount/))

## 8. 정리

**K3s 와 K8s 는 같은 K8s API 를 구현한 두 distribution**. 패키징과 기본 선택이 다를 뿐 본질은 같습니다.

비유하자면:
- K8s (kubeadm) = **자체 조립 데스크탑** — 원하는 컴포넌트 자유롭게 선택 가능, 대신 셋업 시간/지식 필요
- K3s = **노트북** — 그냥 켜면 다 동작. 일부 컴포넌트 교체는 가능하지만 통합된 게 기본.
- 매니지드 (EKS/GKE/AKS) = **클라우드 인스턴스** — 켜는 것조차 클라우드가 해줌. 가장 비싸지만 가장 적게 신경 씀.

본인이 K3s 를 고른 건 "노트북" 이 맞아서. 더 큰 규모면 "자체 조립" 으로 가야 할 거고, 회사라면 "클라우드 인스턴스" 가 효율적일 수도 있습니다.

면접에서 "K3s 와 K8s 의 차이는?" 이라고 물으면:
> "K3s 는 K8s 100% 호환 distribution 으로 CNCF 인증을 받았습니다. 단일 바이너리에 control-plane + worker + containerd + Flannel + Traefik 등을 묶어 메모리 풋프린트가 200-400MB 정도. AWS in-tree provider 등 legacy 코드를 제거하고 SQLite 를 기본 데이터스토어로 써서 소규모/엣지/온프레미스에 최적화됐습니다. 50노드+ 대규모면 kubeadm 이나 매니지드를 권하고, 5노드 온프레면 K3s 가 셋업 속도 / 메모리 효율에서 압도적입니다."

이 정도 답하면 됩니다.

---

**관련 글**
- [K3s 3-Master HA 마이그레이션 — SQLite → embedded etcd](/2026/05/12/k3s-3master-ha-sqlite-etcd-migration/)
- [K3s flannel cross-node 가 안 될 때 — ufw 8472/UDP 함정](/2026/05/11/k3s-flannel-ufw-8472-cross-node-함정/)
- [K3s local-path-provisioner 에 4TB HDD 통합](/2026/05/12/k3s-local-path-storage-hdd-bind-mount/)
- [K3s 실전 — 5노드 4티어 설계](/2026/05/11/k3s-실전-5노드-4티어-설계/)
