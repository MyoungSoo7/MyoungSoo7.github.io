---
layout: post
title: "K3s vs K8s — 현실적인 비교, 6노드 14개월 운영 경험"
date: 2026-06-24 21:30:00 +0900
categories: [kubernetes, k3s, infrastructure, fundamentals]
tags: [k3s, kubernetes, k8s, kubeadm, rke2, on-premise, comparison, real-world]
---

K3s 클러스터 운영 14개월 째 다. 6 노드, 65+ ArgoCD apps, 33 도메인. 그 사이 cluster-dns outage 복구 (6시간), etcd orphan member 제거, Velero OOM fix, frp self-host 구축, SOPS+age 도입 등 *작은 사고들 의 *반복*. 그 운영 의 *14개월* 위에서 자주 받는 질문 — "K3s 와 K8s 차이가 뭐냐"  + 그 자매 질문 — "그럼 K8s 로 옮겨야 하나?".

블로그 쓰기 전에 *한 줄 결론* 부터: **manifest API 는 100% 같다. 패키징 과 운영 깊이가 다르다. 6 노드 self-host 에선 K3s 가 거의 항상 정답**. 

이 글 은 그 결론 의 *왜* — 14개월 의 *실제 운영* 위에서 정리한다.

---

## 1. 같은 점 — 둘 다 진짜 Kubernetes

가장 흔한 오해부터. K3s 는 *K8s 의 *서브셋* 도 *경량화 된 다른 것* 도 아니다. **CNCF certified Kubernetes** 다. 인증 마크 가 *진짜*.

```
- API server, scheduler, controller-manager, kubelet, kube-proxy — 모두 있음
- Pod, Deployment, Service, Ingress, ConfigMap, Secret, PV — 모두 동일 API
- kubectl 명령 — 100% 호환
- Helm chart — 100% 호환
- CRD + Operator — 동일하게 작동
- 인증서, RBAC, NetworkPolicy — 동일 표준
```

내 클러스터 의 sparta-prod 의 PostgreSQL StatefulSet 의 manifest 가 *그대로* AWS EKS 또는 GKE 또는 kubeadm K8s 위 에서 *작동*. 코드 변경 0. **이게 K3s 의 *진짜 보호 막* 이다** — 학습 한 K8s 지식 의 *영구 자산*.

## 2. 패키징 — 단일 binary vs 분리 component

여기 가 *진짜 차이* 의 출발점.

**Upstream K8s (kubeadm)**:
```
control-plane node:
  /usr/bin/kube-apiserver          (단독 프로세스, ~300MB RAM)
  /usr/bin/kube-controller-manager  (단독, ~200MB)
  /usr/bin/kube-scheduler           (단독, ~150MB)
  /usr/bin/etcd                     (단독, ~500MB+)

worker node:
  /usr/bin/kubelet                  (단독, ~200MB)
  /usr/bin/kube-proxy               (단독, ~100MB)
  containerd                         (별도 설치)
```

→ control-plane 1 노드 의 *baseline 메모리* ~1.2GB. 추가 로 *kubectl logs / kubectl exec* 시 *별도 분리 된 log* 분석 가능. *각 component 의 flag* 직접 조정 가능. *진짜 정밀 한 운영*.

**K3s**:
```
control-plane node:
  /usr/local/bin/k3s server  (단일 프로세스, ~400MB)
    └ kube-apiserver, controller-manager, scheduler, etcd, containerd 등을
      goroutine 으로 *통합 실행*

worker node:
  /usr/local/bin/k3s agent   (단일 프로세스, ~200MB)
    └ kubelet, kube-proxy, containerd 통합
```

→ control-plane *baseline 메모리* ~400~500MB. *3 배 차이*. 솔로몬 (15GB RAM, 2014 Mac mini) 같은 작은 노드 에서 *진짜 큰 차이*. 우리 클러스터 의 3-master HA 가 *가능 한 이유*.

대가 — log 가 *한 binary 의 통합 stdout*. *어느 component 가 *뭘 한지* 분리 어려움. 우리 의 2026-06-19 cluster-dns outage 디버깅 시 *journalctl -u k3s* 의 *모든 로그 가 섞임* — 익숙해지면 OK 지만 *kubeadm 의 *분리 log* 보다 *추적 시간 더 걸림*.

## 3. 기본 내장 컴포넌트 — opinionated vs unopinionated

**K3s 가 *자동* 으로 깔고 오는 것**:

| 컴포넌트 | K3s 기본 | upstream K8s |
|---|---|---|
| Container runtime | containerd 내장 | 직접 설치 |
| Ingress controller | Traefik | 직접 설치 (nginx-ingress 등) |
| LoadBalancer (Service type) | Klipper-LB (NodePort 의 자동 노출) | MetalLB / cilium 직접 |
| StorageClass (default) | local-path-provisioner | 직접 (Longhorn, OpenEBS, Rook 등) |
| DNS | CoreDNS | CoreDNS (둘 다 표준) |
| Metrics Server | 내장 | 직접 설치 |
| Helm Controller | HelmChart CRD 내장 | helm CLI 직접 |
| Network plugin (CNI) | Flannel | 선택 (Calico, Cilium, Flannel) |

**우리 클러스터 의 *현실*** — K3s 기본 의 *대부분 을 *우리 가 *대체* 함:
- Traefik 끄고 *ingress-nginx* 사용 (cert-manager 호환성 + 익숙함)
- Klipper-LB 끄고 *Cloudflare Tunnel* 사용 (외부 IP 노출 없는 외부 진입)
- local-path-provisioner 유지 + *infra-ssd 의 ssd-local* (StorageClass, no-provisioner) 추가
- Helm Controller 끄고 *ArgoCD* 로 GitOps

→ K3s 의 *기본 의 합리적 default* 가 *시작 의 30분 을 절약*. 그 후 *옵션 으로 교체 가능*. *upstream K8s 는 *모든 결정 직접* — *시작 의 1~3일* 더 걸림.

## 4. 자원 비교 — 실제 숫자

내 6노드 클러스터 의 *실제 메모리* 측정:

```
르무엘 (control-plane, etcd): 5.0GB / 31.2GB 사용 (16%)
일원   (control-plane, etcd): 24.3GB / 30.7GB 사용 (79%) - postgres pool
솔로몬 (control-plane, etcd): 5.2GB / 15.0GB 사용 (35%)
루이스 (worker):           6.0GB / 15.5GB (39%)
데이비드 (worker, 모니터링):    11.0GB / 15.1GB (73%) - Prometheus stack
이사갈 (worker, 큰 노드):    9.2GB / 15.0GB (61%) - Immich + 30 pods
```

이 중 *K3s 자체 의 baseline* (시스템 + K3s daemon):
- control-plane: ~600MB ~ 1GB
- worker: ~300~500MB

같은 노드 가 *upstream K8s (kubeadm)* 면 *baseline 1.5~2GB* 예상. *솔로몬 같은 *15GB RAM* 노드 에선 *워크로드 capacity 가 *10~15% 감소*. *대량 PostgreSQL 또는 Elasticsearch* 처럼 *메모리 hungry* 워크로드 의 *direct 비용*.

→ K3s 의 *경량성* 은 *small/medium cluster* 의 *진짜 가치*. *수십 노드 대규모* 에선 *3 배 차이* 가 *상대적으로 작아짐* — 거기선 *K8s 의 정밀 운영* 이 *경량 보다 가치 큼*.

## 5. 운영 깊이 — log, etcd, 인증서

**Log 분리도**:
- upstream K8s: 각 component (apiserver, scheduler, controller-manager, etcd) 가 *각자 systemd service* 또는 *Pod*. `journalctl -u kube-apiserver` 또는 `kubectl logs -n kube-system kube-apiserver-*` 로 *분리 본다*.
- K3s: 모두 `journalctl -u k3s` 한 곳. *통합 logging*. 추적 시 *어느 component 인지 찾기* 가 *추가 step*.

**etcd 관리**:
- upstream K8s: etcd 가 *별도 process*. `etcdctl` 로 *직접 backup / restore / member list / snapshot*. 완전 한 control.
- K3s: etcd 가 *k3s binary 안 embedded*. `etcdctl` 직접 작동 안 됨 — *우리 가 06-22 진단 시 `/tmp/etcdctl` 별도 설치* 한 이유. K3s 자체 의 `k3s etcd-snapshot list` 명령 으로 *snapshot 관리*. *backup 자동* (configurable).

**인증서 갱신**:
- upstream K8s (kubeadm): `kubeadm certs renew` 명령. *수동 또는 자동화*. 인증서 *세부 종류* (apiserver, etcd-peer, scheduler 등) 가 *수십 개*.
- K3s: 인증서 *자동 갱신* (기본). *우리 가 신경 쓸 일 없음*.

→ *수동 작업 의 *학습 깊이* 는 K8s 가 *압승*. *운영 부담 의 가벼움* 은 K3s 가 *압승*. Trade-off.

## 6. 14개월 K3s 운영 의 *실 사고 들*

내 클러스터 의 *진짜 사고 기록*:

| 시점 | 사고 | K8s 였으면? |
|---|---|---|
| 2026-05-12 | SQLite → embedded etcd 인플레이스 마이그 | upstream K8s 는 *원래 etcd 분리* — 마이그 자체 불필요 |
| 2026-06-06 | 솔로몬 etcd 디스크 SSD 이전 | K8s 도 *동일 작업* — 차이 없음 |
| 2026-06-07 | isagal 노드 합류 + orphan etcd Learner 제거 | K8s 는 *kubeadm join* 명령 다름. 동일 한 sago 가능 |
| 2026-06-19 | cluster-dns: 169.254.20.10 한 줄 의 *6시간 outage* | K8s 도 *동일* — config 의 잘못된 값 이 사고 의 원인. 차이 없음 |
| 2026-06-22 | Cloudflare Tunnel 의 *deleted workflow / Public Hostname 누락* | K8s 와 무관 — Cloudflare 측 사고 |
| 2026-06-23 | settlement V50 Flyway non-idempotent ADD CONSTRAINT | K8s 와 무관 — 애플리케이션 / DB 사고 |
| 2026-06-23 | sparta-product logback FileNotFoundException | K8s 와 무관 — 애플리케이션 사고 |

→ **사고 의 *대부분 이 K3s 특화 가 아님***. *애플리케이션, DB, 외부 인프라 (Cloudflare)* 가 *원인 의 80%+*. K3s 자체 의 *결함* 으로 인한 사고 는 *14개월 동안 *거의 없음*.

→ K8s 로 옮겨도 *위 사고 의 80%+ 는 *동일 발생*. 학습 가치 의 marginal 은 *생각보다 작음*.

## 7. K3s 가 *오히려 *유리* 한 영역

내 운영 위에서 *K3s 의 *진짜 강점*:

**Edge / IoT — *진짜 K3s 의 home***. 라즈베리 파이 4 8GB 1 대 에 *K3s + 5 ~ 10 워크로드*. upstream K8s 는 *RAM 으로 거의 불가능*.

**Self-hosted 6노드 미만 의 작은 lab** — *우리 같은 시나리오*. *install one-liner* (`curl -sfL https://get.k3s.io | sh -`) 가 *진짜 의미*. 5분 안 클러스터 가동.

**Embedded etcd HA** — *3 voter quorum*. upstream K8s 는 *etcd 를 *별도 cluster* 구축. *3 머신 추가* 의 *비용 또는 *stacked 의 *복잡도*. K3s 는 *server 모드 노드 가 *자동 etcd voter*.

**rolling upgrade** — `k3s install` 다시 실행 으로 *버전 업*. kubeadm 의 *수동 단계* 보다 *훨씬 단순*.

## 8. K8s (upstream) 가 *오히려 *유리* 한 영역

공정 한 균형:

**대규모 (50+ 노드)**: K3s 의 *embedded etcd* 가 *대규모 voter quorum* 의 *부담*. upstream K8s 의 *external etcd cluster + dedicated control-plane* 이 *scaling 자유*.

**Audit log, admission webhook, network policy 정밀**: kubeadm 의 *각 component flag* 직접 튜닝. K3s 는 *대부분 가능* 하지만 *추가 옵션 의 *플래그 전달 의 *간접성*.

**Service Mesh + 복잡 한 networking**: Istio, Cilium 의 *고급 기능*. K3s 도 가능 하지만 *기본 Flannel 의 *제약*. upstream K8s 는 *CNI 선택 의 자유 가 *처음 부터*.

**규제 / 컴플라이언스 (FIPS, CIS hardened)**: RKE2 (K3s 의 hardened 형제) 가 *답*. *순수 K3s* 는 *FIPS 미지원*.

**Enterprise managed K8s (EKS, GKE, AKS) 와 의 *호환***: production 클라우드 와 *체감 동일* — *학습 한 운영 경험 의 *직접 전이*.

## 9. 14개월 후 의 *솔직한 평가*

내 K3s 클러스터 가 *production-grade* 였나? — **YES**.
- 33 도메인 의 *진짜 사용자 (개인 + 일부 공유)*
- 65+ ArgoCD apps + GitOps
- Velero + R2 (daily + hourly 백업)
- Prometheus / Grafana / Loki / Alertmanager 완전 stack
- SOPS+age 의 git-tracked secrets
- 3-master HA + embedded etcd
- Cloudflare Tunnel + Access (Zero Trust)
- 6노드 의 podAntiAffinity HA 분산

이 모든 게 *K3s 위*. *upstream K8s 였어도 동일 가능*. K3s 가 *부족 한 적이 *14개월 한 번도 없음*.

→ K3s 의 *마지막 약점* 은 *resume signal* 정도. 채용 시장 의 *kubeadm 운영 경험* 이 *K3s 경험* 보다 *높게 평가* 받는 경향. 그러나 *진짜 깊이 — etcd, networking, observability, security, GitOps — 는 K3s 의 *14개월 운영* 만 으로 *완전 체화* 가능.

## 10. 마치며 — 누구에게 어떤 선택

**K3s 가 답**:
- self-host, 1~20 노드
- solo 또는 작은 팀
- edge / IoT
- 학습 의 *시작 점* — *manifest API 의 *체화*

**RKE2 가 답** (K3s 와 K8s 의 *중간*):
- 보안 / 컴플라이언스 강제 (FIPS, CIS)
- production 의 *진짜 hardened*
- K3s 친숙 + K8s 학습 욕구 둘 다

**upstream K8s (kubeadm) 가 답**:
- 50+ 노드
- *진짜 운영 정밀* 욕구 (audit log, custom admission, network policy 정밀)
- *kubeadm 운영 경험 의 resume signal* 이 *목표*
- *대규모 enterprise / 클라우드 K8s 와 의 *완전 호환*

**클라우드 managed K8s (EKS / GKE / AKS) 가 답**:
- 회사 의 production 시스템
- *cluster 관리 자체 가 *목표 가 아닌 시점*
- *비용 보다 *시간 우선*

내 14개월 의 결론 — *K3s 가 *충분 한 production 운영 자산*. *학습 의 *깊이 는 *클러스터 의 종류 보다 *사고 의 횟수 와 *깊이* 가 결정한다*. 6 시간 outage 한 번 의 회복 이 *책 1권 의 학습* 보다 깊다.

K3s 의 *경량 함정* — *너무 단순 해 보여서 *깊이 가 부족 해 보임*. 그러나 *위 에 *진짜 production 워크로드 33 개* 를 얹고 *14개월 운영* 하면 *깊이 는 자동 으로 따라온다*. *사고 가 깊이를 만든다*. K3s 든 K8s 든.

---

## 참고

- *K3s 공식 문서* — [docs.k3s.io](https://docs.k3s.io)
- *kubeadm 공식 가이드* — [kubernetes.io/docs/setup/production-environment/tools/kubeadm](https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/)
- *RKE2 (K3s 의 hardened 자매)* — [docs.rke2.io](https://docs.rke2.io)
- *CNCF K8s 인증 conformance* — *K3s 도 정식 회원*
- 자매편:
  - [K8s 의 유용성 — 온프레미스 vs 클라우드](/2026/06/20/kubernetes-on-premise-vs-cloud-usefulness.html)
  - [컨테이너 오케스트레이션](/2026/06/20/kubernetes-container-orchestration-what-we-actually-use.html)
  - [K8s 로드밸런서](/2026/06/21/kubernetes-loadbalancer-network-layers-l4-l7.html)
