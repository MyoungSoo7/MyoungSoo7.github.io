---
layout: post
title: "*쿠버네티스* 의 *유용성* — *온프레미스* 와 *클라우드* 의 *비대칭 비교*"
date: 2026-06-20 16:30:00 +0900
categories: [kubernetes, infrastructure, devops, cloud]
tags: [kubernetes, k3s, eks, gke, aks, on-premise, cloud, hybrid, cost, multi-cluster, self-hosting]
---

> *"쿠버네티스 는 *클라우드 회사 가 *클라우드 회사 를 위해 *만든 *툴 인데*, *왜 *내 *온프레미스 5 대 노드 에 *깔고 있을까?"* — 이 질문 은 *모순 처럼 보이지만 *사실은 *쿠버네티스 의 *진짜 매력* 을 *드러내는 질문* 이다.
>
> *쿠버네티스 는 *2014 년 Google 에서 *Borg 의 오픈소스 자녀* 로 *세상 에 나왔다*. *그래서 *클라우드 의 자식* 처럼 *보이지만*, *그 본질 은 *추상화 그 자체* — *"내 워크로드 가 *어떤 인프라 에서 돌든 *같은 방식* 으로 *기술 / 배포 / 운영 가능* 하다"* 는 *선언*. *그 선언 이 *클라우드 에서 *극대화* 되고 *온프레미스 에서 *다른 종류의 가치* 를 만든다*.
>
> 이 글은 *온프레미스 K8s (k3s, kubeadm, RKE2, OpenShift)* 와 *클라우드 K8s (EKS, GKE, AKS)* 의 *유용성 을 *동일 한 7 가지 축* 에서 *비대칭 비교* 한다. 내 *6 노드 K3s 클러스터 운영 경험* + *클라우드 production 경험* 을 *교차해서* 정리.

내 *6 편 백엔드 / 보안 연작* 의 *후속편* :
- [*CPU 의 *L1 / L2 / L3 캐시*](/2026/06/18/cpu-l1-l2-l3-cache-and-bottleneck-analysis.html)
- [*I/O 병목 어떻게 해결하지?*](/2026/06/18/io-bottleneck-how-to-solve.html)
- [*Virtual Thread* 와 *Carrier Thread* 의 *관계*](/2026/06/19/virtual-thread-and-carrier-thread-relationship.html)
- [*Prometheus* 가 *수집* 하고 *Grafana* 가 *대답* 한다*](/2026/06/19/prometheus-grafana-metrics-visualization.html)
- [*논블로킹 I/O 서버*](/2026/06/19/non-blocking-io-server-deep-dive.html)
- [*보안 의 7 기둥*](/2026/06/20/security-7-pillars-auth-encryption-firewall-audit.html)

성능 / 관측 / 보안 의 *기술적 깊이* 위에 *어디에 그 모든 것 을 *얹을 것인가* — 그게 *인프라 선택*. 그 선택 의 *대표 질문* 이 *온프렘 vs 클라우드*.

---

## TL;DR — *한 줄 결론*

> *클라우드 K8s* 의 *유용성* 은 *"내가 *클러스터 자체* 를 *운영 할 필요 없음"* — control-plane / etcd / 노드 패치 / 백업 / 업그레이드 를 *클라우드 가 대신*. *대신 *비용* 이 *3~10 배*. *온프레미스 K8s* 의 *유용성* 은 *"내 인프라 의 *모든 줄 을 *내가 통제"* — *데이터 주권 / latency / 비용 / 학습 / 커스터마이징*. *대신 *내가 *etcd 의 *split brain 까지 *책임* 진다*. 둘 다 *Kubernetes 의 *공통 API 와 *생태계* 위에서 *작동 한다* — *어디서 돌든 *manifest 는 *같다*. *그게 *진짜 가치*. 선택은 *워크로드 / 팀 / 비용 / 컴플라이언스* 의 *함수* 이지 *"클라우드 가 무조건 옳다"* 가 *아니다*.

---

## 1. *왜 *쿠버네티스 인가* — *공통 의 가치 부터*

### 1.1 *Kubernetes 의 *본질 적 기여*

쿠버네티스 가 *어디서 돌든* 제공하는 *핵심 가치*:

| 영역 | Kubernetes 이전 | Kubernetes 이후 |
|---|---|---|
| 워크로드 기술 | `docker run -p 8080:80 -e ... -v ...` 명령어 *한 줄* | *선언적 YAML* — `Deployment + Service + ConfigMap` |
| 헬스 / 재시작 | systemd, supervisor, *수동 fan-out* | *liveness/readiness probe + RestartPolicy* |
| 스케일링 | nginx upstream *수동 갱신* | *HPA + label selector + Service* |
| 배포 | scp + restart + rollback 매뉴얼 | *RollingUpdate strategy, revisionHistoryLimit* |
| 시크릿 | env file + chmod 600 | *Secret + RBAC + KMS encryption at rest* |
| 멀티 노드 | *각 노드 마다 docker run 반복* | *DaemonSet, scheduler 가 알아서* |

→ *어디서 돌든 *manifest 가 *같음*. 이게 *유일한 universal 가치*.

### 1.2 *Kubernetes 의 *3 가지 약속*

1. **Portability** — 같은 manifest 로 *EKS / GKE / 온프렘 K3s* 어디서든 작동.
2. **Declarative** — *원하는 상태* 만 선언, *현재 → 목표* reconciliation 은 *컨트롤러* 가 함.
3. **Extensibility** — *CRD + Operator* 로 *Kubernetes 자체* 를 *확장* (PostgreSQL Operator, Istio, ArgoCD).

이 *3 가지 약속* 위에 *클라우드 가 더 *얹을지 *내가 *직접 다 깔지* 의 *선택* 이 이 글 의 *주제*.

---

## 2. *클라우드 K8s — *EKS / GKE / AKS 의 *유용성*

### 2.1 *Managed 의 *진짜 의미*

> *"Managed Kubernetes"* 가 *managed 하는 것은 *정확히 무엇 인가*?

| 영역 | EKS | GKE | AKS | 셀프 K8s |
|---|---|---|---|---|
| Control plane (apiserver, scheduler, controller-manager) | ✓ 99.95% SLA | ✓ 99.5%~99.95% | ✓ 99.95% | *직접 관리* |
| etcd | ✓ 클라우드 내부 | ✓ Spanner 위에 (GKE), 자체 etcd 도 | ✓ | *직접* |
| 노드 OS 패치 | △ 부분 (managed node group) | ✓ 자동 (autopilot, surge upgrade) | ✓ 부분 | *직접* |
| 백업 | *직접* (Velero) | *직접* | *직접* | *직접* |
| 모니터링 / 로깅 | CloudWatch 통합 | Cloud Logging 통합 | Azure Monitor | Prometheus+Grafana 직접 |
| LoadBalancer Service | ✓ ELB 자동 | ✓ Cloud LB | ✓ | *MetalLB, Cilium LB* 등 직접 |
| Persistent Volume | ✓ EBS / EFS | ✓ Persistent Disk / Filestore | ✓ Azure Disk | *Longhorn, OpenEBS, Rook-Ceph* 직접 |
| DNS / Service Discovery | ✓ Route53 통합 | ✓ Cloud DNS | ✓ | *external-dns + 직접 설정* |
| ingress / TLS | ✓ ALB Ingress Controller | ✓ GKE Ingress | ✓ | *nginx-ingress + cert-manager* 직접 |

→ *클라우드 가 *책임 지는 영역* 이 *훨씬 넓다*. *내가 할 일 = manifest 쓰는 것* 만 *남는다* (이상적인 경우).

### 2.2 *클라우드 의 *진짜 매력 — *3 가지*

#### **(1) 운영 부담 *대폭* 축소**

- *etcd 디스크 *fsync 성능 튜닝*? 클라우드 책임.
- *controller-manager leader election split brain*? 클라우드 책임.
- *K8s 1.31 → 1.32 업그레이드 의 *deprecated API 마이그레이션*? *문서 따라 한 번 클릭*.
- *노드 OS CVE 패치*? *managed node group 이 surge upgrade*.

> *3 인 팀 이 *서비스 만들 시간을 *서비스에 집중 가능*. *5 인 SRE 팀 이 *없어도 *production 운영 가능*.

#### **(2) 통합 의 *마법*

```yaml
# AWS EKS — Service 가 자동으로 ALB 생성
apiVersion: v1
kind: Service
metadata:
  name: my-app
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-type: nlb
spec:
  type: LoadBalancer
  ports: [{port: 80, targetPort: 8080}]
  selector: {app: my-app}
# → 90초 후 ALB DNS 자동 발급, Route53 자동 등록 (external-dns)
```

```yaml
# GKE — Persistent Volume 이 자동으로 Persistent Disk 생성
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: data-pvc
spec:
  storageClassName: standard-rwo
  accessModes: [ReadWriteOnce]
  resources:
    requests:
      storage: 100Gi
# → 즉시 PD 생성, mount, 백업 가능
```

→ *클라우드 자원* (LB, DB, Storage, DNS) 이 *manifest 한 줄 로 *통합* 됨. *이걸 *온프렘 에서 *흉내 내려면* *시간 / 노력 / 학습* 다 필요.

#### **(3) Scale-out 의 *물리적 자유*

- *트래픽 spike 5x* → *Cluster Autoscaler 가 5분 안에 *노드 5 개 추가*.
- *주말 trough* → *노드 자동 축소* (비용 절약).
- *멀티 AZ HA* → *manifest 변경 없이* `topologyKey: topology.kubernetes.io/zone` 한 줄.

→ *온프렘 에선 *물리 노드 가 *한정 됨*. *spike 가 *내 자원 한계 넘으면* *서비스 거부* 또는 *수동 노드 추가*.

### 2.3 *클라우드 K8s 의 *함정 — *흔히 안 보이는 *비용*

#### **함정 1 — *Egress 비용***

```text
AWS EKS 의 한 사례:
- 컴퓨트 (EC2): $500 / 월
- EKS control plane: $73 / 월 ($0.10/시간)
- LoadBalancer (ALB): $25 / 월
- EBS PV: $50 / 월
- ★ Inter-AZ 트래픽 (replica 통신): $300 / 월
- ★ Egress to internet: $450 / 월
- ★ NAT Gateway 트래픽: $200 / 월

= $1,598 / 월. 컴퓨트 $500 *대비 *3 배의 hidden cost*.
```

> *Egress 가 *제일 비싸다*. *멀티 AZ 의 *데이터 이동* 만으로 *컴퓨트 보다 비쌀 수 있음*.

#### **함정 2 — *Vendor lock-in***

```yaml
# EKS 전용 annotations
service.beta.kubernetes.io/aws-load-balancer-type: nlb
service.beta.kubernetes.io/aws-load-balancer-ssl-cert: arn:aws:acm:...
# → GKE 로 옮기면 *그대로 *작동 안 함*

# GKE 전용
cloud.google.com/load-balancer-type: "Internal"
networking.gke.io/managed-certificates: cert-1
# → EKS 로 옮기면 *그대로 *작동 안 함*
```

→ *"Kubernetes 라서 *어디든 옮길 수 있어"* 는 *부분적 진실*. *클라우드 specific annotation / IAM 통합 / managed DB* 가 *얽혀 들수록 *이동 비용 증가*.

#### **함정 3 — *Control plane 의 *블랙박스***

- *kubectl 응답 이 *느려요* → 클라우드 콘솔 의 *Health* 만 확인 가능. *내부 etcd / apiserver 로그* 직접 접근 불가.
- *알림 한 줄* — "Control plane upgrade scheduled". *내가 결정 못 함*.

#### **함정 4 — *데이터 주권***

- *EU GDPR* / *한국 개인정보보호법* / *금융 망분리* 등 *특정 데이터 의 *국내 / 자체 위치 보관 의무*.
- *클라우드 region 이 *맞아도 *클라우드 사업자 의 *접근 권한* 자체 가 *법적 으로 *문제* 인 경우.

---

## 3. *온프레미스 K8s — *K3s / kubeadm / RKE2 / OpenShift 의 *유용성*

### 3.1 *Onprem 의 *진짜 가치 — *3 가지*

#### **(1) 비용 의 *현실*

```text
[6 노드 클러스터 의 1년 비용 비교]

★ Onprem (실제 우리 클러스터):
- 노트북 2 대 (lemuel, louise) — 이미 보유, $0
- 데스크탑 1 대 (ilwon) — $1,500 (1회 구매)
- Mac mini 1 대 (solomon) — $400 (중고)
- Dell server 1 대 (isagal) — $300 (중고)
- 전기 (월 평균 50W * 6 = 300W): $5/월 × 12 = $60/년
- 인터넷 / 회선 비용: 이미 있음

총 1년: $2,200 (대부분 1회성)
2년차부터: $60/년

★ EKS 동급 클러스터 (74 vCPU + 126 GB RAM):
- EC2 m5.2xlarge × 6 (8vCPU/32GB): $0.384/h × 6 × 24 × 365 = $20,179/년
- EKS control plane: $73/월 × 12 = $876/년
- EBS gp3 9TB: $0.08/GB × 9000 = $720/월 × 12 = $8,640/년
- 데이터 egress (트래픽에 따라): $1,000~5,000/년

총 1년: $30,000+
```

→ **약 10~15 배 차이**. *개인 개발자 / 학습 / 스타트업 의 *MVP* 에선 *비교 불가능한 차이*.

> *주의* : *비용 비교 가 *공정 하려면* *내 인건비 (etcd 운영 시간)* 도 *포함* 해야 함. *시간당 $50* 으로 잡으면 *주 5시간 운영 = $13,000/년* — *클라우드 와 *근접*.
>
> → **시간 / 학습 가치 가 *비용 보다 중요* 한 단계** 에서 *온프렘 의 우위*.

#### **(2) Latency / Throughput 의 *물리적 우위*

- *LAN 내부 통신* RTT ~0.5 ms. *클라우드 inter-AZ* RTT ~2 ms. *4 배 차이*.
- *NVMe Gen4 직접 부착* 의 *random IOPS* 1M+. *EBS gp3* 16K IOPS (기본).
- *NUMA 친화 적 배치* 직접 가능 (CPU manager static, topology-aware scheduling).

→ *고성능 컴퓨팅, low-latency trading, AI inference batch* 에서 *온프렘 이 *압도적*. 우리 클러스터 의 *솔로몬 etcd SSD 이전 (Intel DC S3700)* 후 *etcd p99 latency 극적 개선* 도 이 맥락.

#### **(3) 통제 / 학습 / 커스터마이징 의 *자유*

- *kernel sysctl 직접 변경* (somaxconn, vm.dirty_ratio).
- *kubelet 옵션 자유 설정* (cpu manager policy, topology manager).
- *etcd 자체 튜닝* — *우리 클러스터 의 *3-master HA + embedded etcd* 인플레이스 마이그레이션 (2026-05-12, SQLite → etcd, 18 분 다운타임)* 이 *대표 사례*.
- *CRD / Operator 자유 개발*.
- *모든 layer 의 *내부 동작* 을 *볼 수 있음* — *학습 가치 가 *압도적*.

> *내 K8s 가 *안 도는 이유* 를 *내가 *해결* 할 수 있는 사람* 이 *클라우드 K8s 가 *안 도는 이유* 도 *추정* 할 수 있다. 그 반대 는 *어렵다*. 그래서 *시니어 엔지니어 의 K8s 학습 경로* 로 *온프렘 이 *강력한 도구*.

### 3.2 *Onprem 의 *부담 — *내 가 *모두 책임*

| 영역 | 내 가 책임 | 도구 |
|---|---|---|
| Control plane HA | 3-master etcd quorum, leader election | k3s, kubeadm, RKE2 |
| Storage | local-path, Longhorn, OpenEBS, Rook-Ceph | (선택) |
| LoadBalancer | MetalLB, kube-vip, Cilium LB | (선택) |
| Ingress / TLS | ingress-nginx, traefik, cert-manager | (선택) |
| DNS | external-dns + 내부 DNS 서버 (CoreDNS, BIND) | (선택) |
| 백업 | Velero + 외부 storage (S3, R2) | (필수) |
| 모니터링 | kube-prometheus-stack + Loki | (필수) |
| 노드 OS | 직접 관리 (apt upgrade, kernel patch) | ansible |
| GitOps | ArgoCD, Flux | (선택) |
| 인증서 | k3s 자동 + cert-manager | k3s |
| Secrets | SOPS, Vault, Sealed Secrets | (선택) |
| 외부 노출 | Cloudflare Tunnel, frp, ngrok | (선택) |

→ *기능 매트릭스 가 *전부 *내 책임*. *팀 / 시간 / 의지* 가 *없다면 *과부담*.

### 3.3 *우리 클러스터 의 *실제 운영 (참고 사례)*

내 *6 노드 K3s 클러스터* 가 *온프렘 운영 의 *현실 reference*:

- *3-master HA + embedded etcd* (2026-05-12 마이그레이션)
- *ArgoCD + Image Updater* 로 *65+ 앱 GitOps*
- *Cloudflare Tunnel + frp self-host* 로 *외부 노출 (단일 진입점)*
- *Velero + R2* 로 *daily + hourly 백업*
- *kube-prometheus-stack + Loki* 로 *관측성*
- *SOPS + age* 로 *secrets git 안 암호화*
- *podAntiAffinity preferred* 로 *HA 3 replica 자동 분산*

이 *전체 stack* 이 *EKS 에선 *자동 으로 따라옴*. *온프렘 에선 *직접 깔고 운영*.

운영 의 *현실*:
- *2026-06-06* 솔로몬 etcd 디스크 SSD 이전.
- *2026-06-07* isagal 노드 합류 + orphan etcd Learner 제거.
- *2026-06-19* config.yaml `cluster-dns: 169.254.20.10` 한 줄 의 *6 시간 outage* (Wi-Fi 재부팅 후 k3s 재시작 시점 에 *잘못된 옵션 활성화*).

→ *클라우드 K8s 에선 *겪을 일 없는 *세밀한 문제*. *부담* 이지만 동시에 *학습 의 보고*.

---

## 4. *비대칭 비교 — *7 가지 축*

### 4.1 *축 1 — *초기 진입 비용*

| | 클라우드 | 온프렘 |
|---|---|---|
| 시간 (cluster up) | *10 분* (EKS / GKE 한 줄 명령) | *수 시간 ~ 며칠* (kubeadm) / *30분* (k3s install one-liner) |
| 학습 비용 | *Kubernetes 자체* | *Kubernetes + Linux 운영 + 네트워크 + storage* |
| 초기 자본 | *$0~$500* | *$2,000~$10,000+* (하드웨어) |

→ **MVP / 빠른 prototype 은 *클라우드 압승***.

### 4.2 *축 2 — *지속 비용 (TCO)*

| 시나리오 | 클라우드 | 온프렘 |
|---|---|---|
| 24/7 30%~80% 사용률 | *비쌈* (idle 도 과금) | *저렴* (이미 깔린 인프라) |
| Spike 의존 (peak/avg = 10:1) | *저렴* (autoscale) | *비쌈* (peak 기준 인프라 필요) |
| 데이터 egress 많음 | *매우 비쌈* | *저렴* (LAN 무료) |
| 1년 ~ 3년 운영 | 청구서 누적 | *초기 자본 회수* |

> *지속 사용 의 cost crossover* 는 *대략 *4~12 개월*. 그 이후 *온프렘 이 *비용 우위*.

### 4.3 *축 3 — *Scale 의 *유연성*

| | 클라우드 | 온프렘 |
|---|---|---|
| 수직 (노드 spec 키우기) | *몇 분* (인스턴스 교체) | *수일* (하드웨어 구매) |
| 수평 (노드 수 늘리기) | *5분* (Cluster Autoscaler) | *수일~수주* (구매 + 설정) |
| 자동 축소 (idle) | *지원* | *수동* (전원 끄기) |
| Multi-region | *지원* | *불가능 (LAN 한정)* |

→ *변동 트래픽 / 글로벌 사용자* 라면 *클라우드 압승*.

### 4.4 *축 4 — *Latency / Throughput*

| | 클라우드 | 온프렘 |
|---|---|---|
| Pod-to-Pod LAN | ~1 ms | ~0.5 ms |
| Pod-to-DB | inter-AZ 2 ms 또는 same-AZ 0.5 ms | LAN 0.5 ms |
| Disk IOPS (gp3 vs NVMe Gen4) | 16K IOPS | 1M IOPS (60 배) |
| Disk throughput (per-disk) | 4 Gbps | 28 Gbps (PCIe Gen4 x4) |

→ *고성능 컴퓨팅, low-latency, HFT, large AI inference* → *온프렘 압승*.

### 4.5 *축 5 — *데이터 주권 / 컴플라이언스*

| 워크로드 | 적합 |
|---|---|
| *개인정보 (한국 PIPA, EU GDPR)* | *온프렘 또는 region-locked 클라우드* |
| *결제 (PCI-DSS)* | *둘 다 가능 — 둘 다 *직접 *책임* 영역 있음* |
| *금융 망분리* | *온프렘 필수* (또는 *private cloud*) |
| *의료 / EMR* | *지역 별 규제 강력* — *온프렘 우세 한 한국* |
| *국방 / 정부* | *온프렘 / 폐쇄망 필수* |

### 4.6 *축 6 — *운영 부담 / 신뢰성*

| | 클라우드 | 온프렘 |
|---|---|---|
| Control plane 가용성 | *99.95% SLA* | *내 SLA*, 보통 *99.5%~99.9%* |
| etcd 운영 | 자동 | 직접 (백업, 디스크, quorum) |
| 노드 패치 | *자동 ~ 반자동* | *수동* (apt upgrade, kernel) |
| 모니터링 통합 | 클라우드 기본 | *Prometheus 직접* |
| 장애 시 *fix 책임* | *클라우드 + 내가 분담* | *전부 내가* |
| 24/7 oncall | *클라우드 측 도 oncall* | *내 / 내 팀 만* |

→ *팀 < 5명 + 비즈니스 critical* 이면 *클라우드 우세*. *팀 > 10명 + 운영 노하우* 면 *온프렘 가능*.

### 4.7 *축 7 — *Lock-in 과 *Portability*

| | 클라우드 | 온프렘 |
|---|---|---|
| Pure manifest portability | 높음 | *최고* |
| 클라우드 specific 기능 의존 | 빠르게 증가 | *없음* |
| 다른 클라우드 로 *이동 비용* | *수개월* (재작성 + 데이터 이전) | *없음 (어디든 동일)* |
| Hybrid 운영 | *복잡* | *복잡* |

> *클라우드 의 *lock-in 은 *서서히 깊어진다*. *처음엔 *manifest 만 쓰지만* *3년 후* IAM 통합, managed DB, 클라우드 specific annotation 가 *수백 개*.

---

## 5. *Hybrid / Multi-Cloud — *최선 의 *현실 답*

### 5.1 *왜 *Hybrid 인가*

> *현실 의 *큰 조직* 은 *둘 중 하나* 가 아니라 *둘 다*.

- **Stateful + 민감 데이터** → 온프렘 / private cloud.
- **Stateless + 외부 노출 + spike-prone** → 퍼블릭 클라우드.
- **DR (Disaster Recovery)** → 온프렘 ↔ 클라우드 *backup-restore*.

### 5.2 *대표 패턴*

#### **(1) Edge + Core**
```text
[Edge node (온프렘 매장)]     [Core (클라우드)]
   - 매장 별 데이터              - 중앙 집계
   - 오프라인 가능               - 분석 / ML
   - k3s edge cluster            - EKS / GKE
       └────── replication ─────┘
```

#### **(2) Burst Cloud**
```text
[일상 트래픽: 온프렘]
        ↓ peak 도래
[Spike: 클라우드 cluster 자동 spin-up]
        ↓
[Spike 해소: 클라우드 spin-down]
```
*Kubernetes federation* (KubeFed) 또는 *Argo Rollouts traffic split*.

#### **(3) Multi-Cloud Avoid Lock-in**
- *모든 manifest 가 *어느 클라우드 든 *작동* 하도록 *설계 의무*.
- *Crossplane, Pulumi* 같은 *IaC 다중 클라우드* 도구.
- *조직 의지 + 비용* 양쪽 다 큼.

### 5.3 *Hybrid 의 *함정*

- *Identity 통합* — *어느 IdP 가 master 인가*.
- *데이터 sync* — *어느 쪽 이 source of truth 인가*.
- *Network 통합* — *VPN / Direct Connect / Cloudflare Tunnel*.
- *비용 폭증* — *두 곳 다 부담 + 통신 비용*.

→ *온프렘 또는 클라우드 어느 하나 만 한 *후 *3년 운영* 후 *현실 적인 hybrid 결정*.

---

## 6. *언제 *어떤 선택 인가* — *의사결정 트리*

### 6.1 *클라우드 K8s 가 *압도적* 인 경우*

- **트래픽 변동 큰 B2C 서비스** — autoscale 의 자유.
- **글로벌 사용자** — multi-region.
- **팀 < 5명** — 운영 부담 ↓.
- **MVP / pre-PMF** — 빠른 시작.
- **컴퓨트 의존도 매우 낮음** (월 < $1000) — 비용 차이 무시.
- **컴플라이언스 region-locked OK** — AWS Seoul / GCP Seoul.

### 6.2 *온프렘 K8s 가 *압도적* 인 경우*

- **연속 24/7 워크로드 + 사용률 50%+** — TCO 우세.
- **저지연 요구 (< 5ms)** — LAN 통신 의 물리적 우위.
- **금융 / 의료 / 정부 망분리**.
- **데이터 egress 매우 많음** — 클라우드 egress 비용 폭탄.
- **학습 / 연구 목적**.
- **개인 / 스타트업 의 *비용 최소화***.
- **이미 *서버 / 노트북 / 데스크탑* 보유**.

### 6.3 *Hybrid 가 *맞는 경우*

- **위 두 카테고리 가 *동시 에 진실*** 인 큰 조직.
- **DR 요구** — 한쪽이 죽어도 다른 쪽 으로.
- **점진 적 마이그레이션 중**.

### 6.4 *어느 쪽이든 *둘 다 잘못 가는 경우*

- **K8s 안 써도 되는 워크로드 를 *K8s 에 욱여 넣음*** — VM 1 대로 충분한 monolith 를 *unnecessarily K8s 화*.
- **팀 의지 / 기술 수준 부족** — *어디서 돌든* *운영 못 함*.
- **CI/CD / 관측성 부재** — manifest 만 있고 *그것을 *돌리는 *플로우 없음*.

---

## 7. *Kubernetes 외 *대안 — *진짜 비교*

### 7.1 *Kubernetes 가 *항상 정답 인가*

| 워크로드 | K8s 대안 | 언제 |
|---|---|---|
| 단일 monolith | Docker Compose + systemd | 노드 1~3 대 |
| Stateful 시스템 (DB, Kafka) | *bare metal + Ansible* | 운영 부담 < K8s 의 학습 비용 |
| Serverless 함수 | AWS Lambda, Cloud Run | 트래픽 매우 변동 + stateless |
| Batch | Apache Airflow + bare workers | K8s 의 *과잉 추상화* 회피 |
| HPC | Slurm | GPU job, MPI |
| Edge IoT (수만 device) | K3s / k0s / MicroK8s | K8s 의 *경량 분기* |

→ *Kubernetes 가 *과한* 경우 도 많다. *워크로드 / 팀 / 운영 능력* 의 함수.

### 7.2 *Kubernetes 의 *경량 변종*

| | 특징 | 적합 |
|---|---|---|
| **k3s** | 단일 binary, embedded etcd or SQLite, < 100MB | edge, dev, 소형 cluster |
| **k0s** | Mirantis 의 single binary, modular | edge, telecom |
| **MicroK8s** | snap 기반, Canonical, addon system | Ubuntu 친화, dev |
| **kind** | Docker in Docker | CI 테스트 |
| **minikube** | local VM | dev 환경 |
| **OpenShift** | Red Hat의 *극도로 *enterprise 한 K8s | 보안 / 컴플라이언스 강조 큰 조직 |

→ 우리 클러스터 는 *k3s* — *6 노드 의 *경량 + HA + ArgoCD + 외부 노출* 조합 이 *2026 년 현재 *극도로 실용적*.

---

## 8. *결론 — *유용성 은 *대칭 이 아니다*

> *클라우드 K8s 의 *유용성* 과 *온프레미스 K8s 의 *유용성* 은 *같은 단어 가 *완전히 다른 의미* 다.

- *클라우드 K8s 의 유용성* = *"내가 *클러스터 자체* 를 *운영 할 필요 없음"*. 1인 개발자 가 *production-grade 인프라* 를 *쓸 수 있다*. *비용 의 댓가* 와 *통제 의 손실*.
- *온프레미스 K8s 의 유용성* = *"내 인프라 의 *모든 줄 을 *내가 통제"*. 학습 / latency / 비용 / 컴플라이언스 / 커스터마이징 의 *자유*. *시간 의 댓가* 와 *책임 의 무게*.

> *Kubernetes 가 *진짜로 *주는 *공통 가치* 는 *어디서 돌든 *manifest 가 *같다는 것* — *그 한 가지 가 *2026 년 인프라 의 *공통 어휘 가 되었다는 사실*.

선택 은 *워크로드 / 팀 / 비용 / 컴플라이언스* 의 *함수*. *"클라우드 가 무조건 옳다"* 는 *마케팅 의 거짓말* 이고, *"온프렘 이 정답"* 도 *학습 의 자만*. *둘 의 *상대적 유용성* 을 *내 맥락* 에서 *측정* 하는 것 이 *시니어 엔지니어 의 일*.

*내 개인 클러스터* 는 *온프렘 k3s 6 노드*. *동시 에 *상용 production 워크로드* 는 *EKS / GKE 로 운영해 본 경험*. *둘 다 의 *실전 reference* 를 *몸 으로 갖고 있을 때* *진짜 *교차 결정 이 가능* 하다*.

*Kubernetes 의 *유용성* 은 *클라우드 든 *온프렘 이든* — *어디 에 *내 워크로드 가 *진짜로 *적합* 한가* 의 *답을 *측정 할 수 있게* 해 준다*. *그게 *2026 년 *백엔드 엔지니어 가 *Kubernetes 를 *이해 해야 하는 *진짜 이유*.

---

## *참고*

- *Brendan Burns, Kelsey Hightower, Joe Beda*, *Kubernetes: Up and Running*.
- *Liz Rice*, *Container Security*.
- *AWS EKS Best Practices Guide* — [aws.github.io/aws-eks-best-practices](https://aws.github.io/aws-eks-best-practices).
- *GKE Architecture and Best Practices* — Google Cloud 공식.
- *k3s 공식 문서* — [docs.k3s.io](https://docs.k3s.io).
- *FinOps Foundation* — 클라우드 비용 모범 사례.
- *Cloud Native Computing Foundation* (CNCF) — 매년 *Annual Survey*.
- 자매편 :
  - [*CPU 의 *L1 / L2 / L3 캐시*](/2026/06/18/cpu-l1-l2-l3-cache-and-bottleneck-analysis.html)
  - [*I/O 병목 어떻게 해결하지?*](/2026/06/18/io-bottleneck-how-to-solve.html)
  - [*Virtual Thread* 와 *Carrier Thread* 의 *관계*](/2026/06/19/virtual-thread-and-carrier-thread-relationship.html)
  - [*Prometheus* 가 *수집* 하고 *Grafana* 가 *대답* 한다*](/2026/06/19/prometheus-grafana-metrics-visualization.html)
  - [*논블로킹 I/O 서버*](/2026/06/19/non-blocking-io-server-deep-dive.html)
  - [*보안 의 7 기둥*](/2026/06/20/security-7-pillars-auth-encryption-firewall-audit.html)
