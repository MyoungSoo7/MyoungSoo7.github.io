---
layout: post
title: "*컨테이너 오케스트레이션* — *DEIS / Rancher / Mesos / Nomad / Swarm* 의 *전쟁사* 와 *우리 가 실제로 *쓰고 있는 *Kubernetes 의 *기능 들*"
date: 2026-06-20 23:30:00 +0900
categories: [kubernetes, infrastructure, container-orchestration, devops]
tags: [kubernetes, container-orchestration, k3s, docker-swarm, mesos, marathon, nomad, rancher, deis, scheduling, hpa, podantiaffinity]
---

![컨테이너 오케스트레이션 후보 — DEIS / Rancher / Mesos+Marathon / Nomad / Docker Swarm](/assets/images/container-orchestration-landscape.jpg)
*컨테이너 오케스트레이션 전쟁 (2014~2018) 의 5 후보 — 그리고 살아남은 K8s. 이 글은 그 *전쟁사* 와 *우리가 실제로 쓰는 K8s 의 기능* 을 다룬다.*

> *"쿠버네티스 가 *컨테이너 오케스트레이션* 의 *표준 이다"* — 이 한 줄 은 *2018 년 부터 *반복 되어 진실 처럼 들리지만*, *그 표준화 이전 에 *5 ~ 6 개 의 *다른 후보* 가 *각자 *진지 한 시도* 를 했다는 사실 은 *기억 에서 지워진다*.
>
> *DEIS, Rancher, Mesos + Marathon, HashiCorp Nomad, Docker Swarm* — *2014 ~ 2018 사이* 의 *오케스트레이션 전쟁* 의 *주요 참전자* 다. *각자 *고유한 철학* 과 *기술적 강점* 을 가지고 있었다. *왜 *Kubernetes 가 살아남았나*, *그들이 *틀린 길* 이었나, *살아남은 K8s 의 *어떤 기능* 이 *우리 가 *실제로 *쓰고 있는 것* 인가 — *이 글 은 그 *세 질문* 에 *답한다*.
>
> 우리 *6 노드 K3s 클러스터* 에서 *K8s 의 *어떤 오케스트레이션 기능* 이 *실제로 *작동 중* 이고, *어떤 것은 *깔려는 있지만 *잠자고* 있고, *어떤 것은 *아예 안 쓰는지* — 그 *사용 / 미사용 의 *비대칭* 까지 *고찰* 한다.

내 *7 편 인프라 연작* 의 *후속편* :
- [*CPU 의 *L1 / L2 / L3 캐시*](/2026/06/18/cpu-l1-l2-l3-cache-and-bottleneck-analysis.html)
- [*I/O 병목 어떻게 해결하지?*](/2026/06/18/io-bottleneck-how-to-solve.html)
- [*Virtual Thread* 와 *Carrier Thread* 의 *관계*](/2026/06/19/virtual-thread-and-carrier-thread-relationship.html)
- [*Prometheus* 가 *수집* 하고 *Grafana* 가 *대답* 한다*](/2026/06/19/prometheus-grafana-metrics-visualization.html)
- [*논블로킹 I/O 서버*](/2026/06/19/non-blocking-io-server-deep-dive.html)
- [*보안 의 7 기둥*](/2026/06/20/security-7-pillars-auth-encryption-firewall-audit.html)
- [*K8s 의 유용성 — 온프레미스 vs 클라우드*](/2026/06/20/kubernetes-on-premise-vs-cloud-usefulness.html)

이전 글이 *"K8s 의 *유용성* 이 *어디서 *어떻게 다른가"* 였다면, 이 글은 *"K8s 가 *해 주는 일* 의 *진짜 목록* 과 *나는 *그 중 무엇 을 *실제로 *쓰고 있나"*. *내 클러스터 가 *내 마음 속 의 *추상화 와 *얼마나 일치 하는지* 의 *자가 진단*.

---

## TL;DR — *한 줄 결론*

> *컨테이너 오케스트레이션* 의 *5 후보* 는 *각자 *진지한 강점* 이 있었다 — *Mesos 의 *2단계 스케줄러*, *Nomad 의 *단일 binary 의 *simplicity*, *Swarm 의 *Docker 와의 *연속성*, *Rancher 의 *멀티 클러스터 UI*, *DEIS 의 *PaaS-style 단순함*. *K8s 가 *살아남은 이유* 는 *"가장 우수 해서"* 가 *아니라* *"가장 *확장 가능* 했고 *생태계 가 *복리 로 성장* 해서"*. *우리 6 노드 K3s 클러스터 에서 *실제로 *작동 중* 인 K8s 의 오케스트레이션 기능 은 *15 가지 정도* — *Pod scheduling, Deployment rolling, podAntiAffinity, ConfigMap/Secret, PV, Ingress, HPA-light, NetworkPolicy 등*. *반대 로 *잠자고 있는 기능* 도 많다 — *VerticalPodAutoscaler, PodDisruptionBudget, Network Plugin 의 일부 정책, mTLS, PodSecurity Standards 의 일부*. 사용/미사용 의 *비대칭 을 알아야* *진짜 운영* 이 된다.

---

## 1. *컨테이너 오케스트레이션* 의 *전쟁 사 (2014 ~ 2018)*

### 1.1 *왜 *오케스트레이션 이 필요했나*

*2013 년 Docker 등장 후* :
- *컨테이너 1 개* — `docker run` 으로 끝.
- *컨테이너 10 개* — `docker-compose up` 으로 가능.
- *컨테이너 100 개 (5 노드)* — *불가능*. 어디에 띄울 지, 죽으면 어떻게 살릴 지, network / storage / secrets 어떻게 공유 할 지.

→ *분산 컨테이너 의 *생사 / 배치 / 통신 / 상태* 를 *자동화* 하는 *오케스트레이터* 가 *필수 가 된 순간*.

### 1.2 *5 후보 의 *각자 의 *철학*

#### **(1) DEIS — *Heroku-style PaaS***

Engine Yard 에서 *2013 년* 출시. *"git push 만 하면 *배포 끝"* 의 *Heroku 경험* 을 *오픈소스로*.

```bash
# DEIS v1 의 사용 경험
deis create my-app
git push deis master
# → 빌드 + 배포 + 라우팅 자동
```

- **강점** : *극도로 단순*. 개발자 가 *Dockerfile 조차 안 만들어도* (buildpack) *배포 가능*.
- **약점** : *복잡한 워크로드 에 *부족함*. *StatefulSet, DaemonSet 같은 *세밀한 제어* 없음.
- **운명** : *DEIS v2 부터 *K8s 위에 *얹는 방향* 으로 전환. *2017 년 Microsoft 인수 후* *2020 년 종료*.

#### **(2) Rancher — *멀티 클러스터 의 UI*

*2014 년* 미국 Rancher Labs 에서 출시.

- **강점** : *멀티 클러스터 *통합 UI*. *cattle 자체 오케스트레이터* 도 가졌지만 *K8s 가 사실상 표준 되자* *Rancher 가 K8s 의 *최고 UI* 로 *피봇*.
- **운명** : *2020 년 SUSE 인수*. 지금 도 *RKE2, K3s* 의 *부모* 로 *살아있다* — *K3s 가 우리 클러스터 의 base*. *전환 의 성공 사례*.

#### **(3) Apache Mesos + Marathon — *데이터센터 OS***

*Berkeley AMPLab 에서 *2009 년 출발*. *Twitter, Airbnb, Apple* 의 *초기 채택*.

- **철학** : *"한 데이터센터 전체 가 *하나의 컴퓨터"*. *컨테이너 만이 아니라* *Spark, Hadoop, Cassandra* 같은 *non-container 워크로드* 도 *함께 스케줄*.
- **2단계 스케줄링** — *Mesos 가 *resource offer* 를 *framework (Marathon, Chronos, Spark)* 에 *제공*, framework 가 *수락 / 거부 결정*. *K8s 의 *중앙 집중 scheduler 와 *근본적 차이*.
- **약점** : *복잡도*. *Marathon (Mesos 위의 컨테이너 scheduler)* + *Mesos* + *Zookeeper* — *3 component stack*.
- **운명** : *Twitter 도 K8s 로 migrate (2020). *Apache Mesos 프로젝트 archived (2021)*. *진지한 기술 적 우위 가 *생태계 부족 으로 패배*.

#### **(4) HashiCorp Nomad — *단일 binary 의 *minimalism***

*2015 년 HashiCorp* 가 *Consul, Vault, Terraform* 의 *형제* 로 출시.

- **강점** :
  - *단일 binary*. *Server + Client* 모두 *같은 nomad 명령*. *K8s 의 *수십 component* 와 대조적.
  - *비-컨테이너 워크로드 도 지원* (raw exec, Java, Docker, QEMU).
  - *학습 곡선 압도적으로 낮음*.
- **현황** : *2026 년 현재 도 *살아있다*. *작은 팀 / 단순 워크로드* 에서 *진지한 대안*. *Cloudflare, Roblox, Trivago* 등 *대규모 채택 사례 있음*.
- **약점** : *생태계 의 깊이* — Operator, CRD, service mesh, GitOps 도구 모두 *K8s 가 압도적 으로 많다*.

#### **(5) Docker Swarm — *Docker 의 *연속성***

*2014 년 출시*. Docker 의 *자체 오케스트레이터*.

- **강점** : *Docker CLI 와 *완전한 연속성*. `docker service create` 한 줄.
- **약점** :
  - *기능 적으로 *K8s 에 점차 밀림* (StatefulSet 부재, NetworkPolicy 미약).
  - *Docker Inc 의 *상업 적 혼란* (2017 ~ 2019).
- **운명** : *Mirantis 가 Docker Enterprise 인수 (2019)*. *유지 보수 모드*. *2026 년 현재 *작은 ecosystem*.

### 1.3 *왜 *Kubernetes 가 *살아남았나*

> *기술 적 우월성 보다 *생태계 의 *복리 효과*.

| 요인 | 영향 |
|---|---|
| *Google 의 *Borg 의 *17 년 경험* | *production 에서 *증명* 된 패턴 (controller, declarative, label) |
| *CNCF (Cloud Native Computing Foundation)* | *벤더 중립 거버넌스* — AWS, Azure, GCP 모두 *기여 / 지원* |
| *오픈소스 의 *기여자 폭증* | *2020 년 contributors 6,000+. *Linux 다음 가는 *프로젝트 크기* |
| *CRD + Operator 패턴* | *Kubernetes 자체* 가 *확장 가능* — Postgres, Cassandra, Kafka 모두 *operator* 화 |
| *벤더 lock-in 회피 압력* | *AWS, Azure, GCP 가 *각자 다른 오케스트레이터* 라면 *고객 이 *못 옮김*. *K8s 가 *공통 분모* 가 됨 |
| *Helm + 차트 시장* | *재사용 가능 한 *애플리케이션 패키지* — 다른 곳 엔 없는 풍부함 |

> *Mesos 가 *기술적으로 *더 성숙 했지만* *생태계 가 *복리 로 자라지 못함*. *Swarm 이 *더 단순 했지만* *세밀한 워크로드 지원 부족*. *Nomad 는 *지금도 살아있지만* *생태계 의 *수십 배 차이* 가 *결정 적*.

> *2026 년 K8s = *컨테이너 오케스트레이션 의 *공통 어휘*. *학습 / 채용 / 도구 / 클라우드 *통합* 모든 면에서 *복리 효과*.

---

## 2. *Kubernetes 의 *오케스트레이션 기능* — *전체 지도*

### 2.1 *14 가지 핵심 기능*

K8s 가 *오케스트레이터 로서* 해 주는 일 :

```text
┌─────────────────────────────────────────────────────────┐
│  [Workload 추상화]                                       │
│   1. Pod scheduling      (어디에 띄울지)                  │
│   2. ReplicaSet          (몇 개 유지)                     │
│   3. Deployment          (rolling update / rollback)     │
│   4. StatefulSet         (순서 / 고유 ID 보장)            │
│   5. DaemonSet           (모든 노드 에 1 개)              │
│   6. Job / CronJob       (배치 / 스케줄)                  │
├─────────────────────────────────────────────────────────┤
│  [상태 / 생명주기]                                        │
│   7. Liveness / Readiness Probe                          │
│   8. Resource Limits / Requests                          │
│   9. HPA (Horizontal Pod Autoscaler)                    │
│  10. VPA (Vertical Pod Autoscaler) / Cluster Autoscaler │
│  11. PodDisruptionBudget                                 │
├─────────────────────────────────────────────────────────┤
│  [네트워크 / 접근]                                        │
│  12. Service (ClusterIP / NodePort / LoadBalancer)       │
│  13. Ingress + TLS                                       │
│  14. NetworkPolicy                                       │
├─────────────────────────────────────────────────────────┤
│  [스토리지 / 설정]                                        │
│  15. ConfigMap / Secret                                  │
│  16. PersistentVolume / PVC                              │
│  17. StorageClass                                        │
├─────────────────────────────────────────────────────────┤
│  [보안 / 격리]                                            │
│  18. RBAC (Role-Based Access Control)                    │
│  19. ServiceAccount                                      │
│  20. PodSecurity Standards                               │
│  21. NetworkPolicy (재게재 — 보안 관점)                   │
├─────────────────────────────────────────────────────────┤
│  [확장 / 운영]                                            │
│  22. CRD + Operator                                      │
│  23. Admission Webhooks (Validating / Mutating)          │
│  24. Init Container / Sidecar                            │
│  25. Affinity / Anti-affinity / Topology Spread          │
└─────────────────────────────────────────────────────────┘
```

→ *25 가지 + α*. *대부분 클러스터 가 *이 중 *절반 만 *적극 사용*. *나머지 는 *깔려는 있지만 *잠자고 있음*.

---

## 3. *우리 6 노드 K3s 클러스터 — *실제로 *쓰고 있는 기능*

> *"내 클러스터 가 *내 마음 의 추상화 와 *얼마나 일치 하는가"* 의 자가 진단.

### 3.1 *적극 사용 — *15 가지*

#### *(a) 워크로드 / 라이프사이클*

| 기능 | 우리 클러스터 의 사용 |
|---|---|
| **Pod scheduling** | *6 노드 (lemuel/louise/david/ilwon/solomon/isagal) 에 워크로드 분산*. tier label (management/worker/storage/storage-backup) 로 *역할 구분* |
| **Deployment** | 65+ 앱 의 *기본 워크로드 단위*. ArgoCD 가 Helm chart → Deployment 로 변환 |
| **StatefulSet** | PostgreSQL, ASAT, MinIO 등 *stateful 서비스* |
| **DaemonSet** | node-exporter, fluent-bit, Velero node-agent, cAdvisor |
| **CronJob** | etcd-leader-pin, Velero backup, lemuel-explorer batch |
| **Liveness / Readiness Probe** | 모든 Spring Boot 앱 의 `/actuator/health/liveness` 와 `/readiness` |
| **Resource Limits / Requests** | 모든 워크로드 — Velero node-agent OOM fix (06-07) 도 *resources.limits.memory: 2Gi* 패치 의 사례 |

#### *(b) 네트워크 / 접근*

| 기능 | 사용 |
|---|---|
| **Service (ClusterIP)** | *모든 내부 통신* (앱 ↔ 앱, 앱 ↔ DB) |
| **Ingress + TLS** | ingress-nginx + cert-manager + Cloudflare Tunnel. *22+ 도메인* 모두 이 경로 |
| **Cloudflare Tunnel** | 클러스터 외부 진입점 *유일* — 외부 직접 노출 포트 *없음* |

#### *(c) 스토리지 / 설정*

| 기능 | 사용 |
|---|---|
| **ConfigMap** | 모든 앱 의 *환경 별 설정* (logback, application.yml override) |
| **Secret + SOPS+age** | DB 비밀번호, API 키 — *git 안에 *암호화 저장*, *6 머신 의 age 키 로만 복호화* |
| **PersistentVolume / PVC** | postgres data, MinIO bucket, ASAT recordings |
| **StorageClass** | local-path (default), longhorn (HA storage), nfs (백업) |

#### *(d) 보안 / 분산*

| 기능 | 사용 |
|---|---|
| **podAntiAffinity (preferred)** | *settlement / sparta replicas=3 가 *david / louise / isagal 3 노드 에 자동 분산* (06-08 적용) |
| **ServiceAccount + RBAC** | 각 ArgoCD app 별 ServiceAccount, namespace 단위 권한 |
| **NetworkPolicy (부분)** | namespace 간 traffic 제한 (일부 — 전체 적용 안 됨) |

#### *(e) 확장 / 운영*

| 기능 | 사용 |
|---|---|
| **CRD + Operator** | ArgoCD (Application CRD), cert-manager (Certificate CRD), Velero (Backup CRD) |
| **Init Container** | DB migration (Flyway), 의존성 check |
| **Sidecar** | 일부 — Istio 안 씀, 명시적 sidecar 일부 |

### 3.2 *깔려는 있는데 *잠자는 기능 — *7 가지*

> *"있긴 한데 *적극 활용 안 함"*. 향후 *개선 여지*.

| 기능 | 현재 상태 | 활용 시 효과 |
|---|---|---|
| **HPA (Horizontal Pod Autoscaler)** | *대부분 앱 *replicas 고정 (3)*. HPA 거의 없음 | *트래픽 spike 자동 대응* |
| **VPA (Vertical Pod Autoscaler)** | 깔려는 있지만 *active mode 없음* (recommend only) | *resources.requests/limits 자동 추천* |
| **PodDisruptionBudget (PDB)** | *0 개 적용*. 노드 drain 시 *동시 다수 evict 위험* | *HA 보장 명시적* |
| **PodSecurity Standards** | *baseline / restricted policy 없음* | runAsNonRoot, capabilities 강제 |
| **NetworkPolicy (완전)** | *namespace 단위 일부 만* | *전체 zero-trust* |
| **Topology Spread Constraints** | *podAntiAffinity 사용 — TSC 가 더 세밀* | zone / rack 단위 분산 |
| **Mutating Admission Webhooks** | *없음* | sidecar 자동 주입, label/annotation 강제 |

### 3.3 *아예 안 쓰는 기능 — *5 가지*

> *workload 가 *그 요구를 *안 함*. *불필요한 기능* — *지금 은*.

| 기능 | 안 쓰는 이유 |
|---|---|
| **Cluster Autoscaler** | *온프렘 — 노드 가 *고정* 됨. 자동 추가 불가능 |
| **Multi-tenancy 의 *namespace 격리***  | *개인 클러스터 — *내가 *모든 namespace 오너* |
| **GPU / Device Plugin** | *AI inference 워크로드 아직 없음* |
| **JobSet (batch)** | *Spark / Ray 워크로드 없음* — 정량 분석은 *systemd + R/Julia/Python 직접*. K8s 외부 |
| **Service Mesh (Istio / Linkerd)** | *서비스 간 mTLS + 정교한 traffic 정책 까지 필요한 규모 아님*. Cloudflare Tunnel + LAN 통신 으로 충분 |

---

## 4. *고찰 — *우리 사용 패턴 의 *3 가지 관찰*

### 4.1 *관찰 1 — *Kubernetes 가 *대체 한 기존 도구*

> 우리 클러스터 가 *2024 년 systemd 단독 운영* 에서 *2026 년 K3s 6 노드* 로 *전환* 한 후 *대체 된 도구* 들 :

| 이전 (systemd 시대) | K3s 도입 후 |
|---|---|
| systemd unit per app | Deployment manifest |
| nginx + manual upstream 설정 | Ingress + Service |
| `/etc/cron.d` 또는 anacron | CronJob |
| ansible-playbook 수동 실행 | ArgoCD 가 git push 시 자동 적용 |
| `rsync` + 수동 백업 | Velero + R2 (daily / hourly) |
| Prometheus 직접 설치 + scrape config 수동 | kube-prometheus-stack (ServiceMonitor CRD) |
| `journalctl -f` SSH 로 분산 | Loki + Grafana |
| 환경 변수 .env file | ConfigMap + Secret |
| 비밀번호 chmod 600 | Secret + SOPS + age |
| HAProxy / nginx 직접 | (없음 — Cloudflare + Service) |

→ **8 가지 도구 + 매뉴얼 작업** 이 **Kubernetes manifest + ArgoCD 의 *git push*** 로 *통합*.

### 4.2 *관찰 2 — *K8s 의 *추상화 가 *과한 부분 도 있다*

> *모든 워크로드 가 *K8s 에 맞는 것은 *아니다*.

우리 클러스터 의 *예외 적 운영* :

- **judge-engine, news-pipeline** — *르무엘 의 systemd 직접 실행*. K8s pod 가 아님. *이유* : *kernel-level isolation (seccomp + cgroup)* 직접 구성 + *짧은 lifecycle (코드 실행 N초)* 에 *K8s overhead (pod 시작 ~100ms)* 회피.
- **R Shiny dashboard** — *louise 의 systemd*. R 의 *Shiny Server* 가 *프로세스 모델 단순* — K8s 화 의 *가치 < 운영 비용*.
- **lqc-gateway (Go)** — *K8s pod 로 *운영 시도 했지만* *systemd + healthcheck* 가 *더 가볍고 디버깅 쉬워서* *되돌림*.

→ **모든 것을 *K8s 화* 하는 것 이 *반드시 옳지 않다*. *워크로드 의 특성 (lifecycle, isolation 요구, latency 민감도)* 에 따라 *systemd / Docker Compose / bare metal* 의 *교차 운영* 이 *현실 적*.

### 4.3 *관찰 3 — *오케스트레이션 의 *진짜 가치* 는 *manifest 의 *통일성***

> *K8s 의 *진짜 마법* 은 *기능 의 풍부함* 이 아니라 *모든 워크로드 가 *같은 manifest 어휘 로 *기술 된다는 것*.

- *Spring Boot 앱* — `Deployment + Service + Ingress + ConfigMap + Secret`.
- *PostgreSQL* — `StatefulSet + PVC + Service`.
- *cron 작업* — `CronJob`.
- *daemon* — `DaemonSet`.

→ *9개 서비스 65+ 앱* 의 *manifest 가 *같은 어휘*. *새 팀원 이 *한 manifest 읽으면 *모든 서비스 의 *대략적 구조 이해 가능*. *이게 *Kubernetes 가 *우리 클러스터 에 *준 *가장 큰 *현실 적 가치*.

> *비교* : *2014 년 systemd + nginx + cron + ansible* 시대 에는 *각 서비스 의 *운영 패턴* 이 *제 각각*. *새 팀원 의 *온보딩 비용* 이 *서비스 마다 *재설정*.

---

## 5. *오케스트레이션 의 *남은 후보 들 의 *현재 가치*

### 5.1 *Nomad — *작은 팀 / 단순 워크로드*

> *2026 년 현재 도 *진지한 대안*.

- *K8s 의 *25 가지 기능 중 *14 가지* 만 필요* 한 경우 — *Nomad 는 *그 14 가지 를 *훨씬 단순하게* 제공.
- *Cloudflare 의 *전체 edge* 가 Nomad 위.
- *Roblox 의 게임 백엔드 *수만 컨테이너* 가 Nomad.
- *학습 곡선 1/10*, *운영 부담 1/5*, *생태계 1/100*.

→ *MVP / 단순 워크로드 / 작은 팀* 에서 *Nomad 가 *진지한 K8s 대안*. 우리 클러스터 *처음 부터 다시 짠다면 *K8s 인지 Nomad 인지* 진지 하게 *비교 했어야*.

### 5.2 *Mesos — *역사적 교훈*

- *기술 적 으로 *2단계 스케줄러 가 *우수*.
- *Spark, Hadoop, Cassandra 같은 *non-container 워크로드 통합* — *그 시대 의 *유일한 답*.
- *현재 도 일부 *큰 회사* (예: 이전의 Apple) 에서 *유산 으로 운영*.
- *교훈* : *기술 적 우월성 만으로는 *생태계 전쟁 에서 *못 이긴다*.

### 5.3 *Docker Swarm — *작은 / 단순 학습 용*

- *2026 년 *적극 운영 사례 거의 없음*.
- *개인 학습 / 1 ~ 3 노드 의 *간단 setup* 에서는 *여전히 *최단 거리*.
- *`docker stack deploy` 한 줄* 의 *간편함*.

### 5.4 *Rancher — *살아남은 사례*

- *자체 cattle 오케스트레이터 를 포기 → K8s 의 *최고 UI / 멀티 클러스터 매니저* 로 *피봇 성공*.
- *RKE2, K3s* — *Rancher 가 만든 *Kubernetes 배포판 들*. *우리 클러스터 의 K3s 도 *그 결과물*.

→ *전쟁 에서 진 회사 도 *피봇 으로 *다른 위치* 에서 *살아남을 수 있다는 *사례*.

---

## 6. *컨테이너 오케스트레이션* 의 *2026 년 *지형*

```text
                ┌─────────────────────┐
                │   Kubernetes (~92%)  │
                │   - EKS, GKE, AKS    │
                │   - K3s, RKE2        │
                │   - kubeadm, kind    │
                │   - OpenShift        │
                └─────────────────────┘
                          ▲
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
  HashiCorp Nomad   Docker Compose    Serverless
  (~5%)             (~2%)              (Lambda, etc)
  - 단순 / 단일       - 1~3 노드       - 함수 단위
                                       - 컨테이너 우회
```

> *2014 년 의 *5 후보 의 *전쟁* 은 *끝났다*. *2026 년 의 *경쟁 은 *K8s vs *서버리스*. *컨테이너 의 *추상화 자체* 를 *건너뛰는 방향* 으로 *다음 변화* 가 *오는 중*.

---

## 7. *결론 — *기능 보다 *공통 어휘***

> *Kubernetes 의 *컨테이너 오케스트레이션 으로서 의 *진짜 가치* 는 *기능 의 풍부함* 이 아니라 *모든 워크로드 가 *같은 manifest 어휘 를 *공유한다는 것*.

오늘 정리한 것들 :

1. *오케스트레이션 전쟁 (2014 ~ 2018)* 의 *5 후보 (DEIS / Rancher / Mesos / Nomad / Swarm)* 는 *각자 진지한 강점* 이 있었지만 *생태계 의 *복리 효과* 가 *K8s 의 *승리* 의 *진짜 이유*.
2. *K8s 의 *25 가지 오케스트레이션 기능* 중 *우리 클러스터 가 *실제로 *적극 사용* 하는 것 은 *15 가지*. *7 가지 는 *깔려는 있지만 *잠자고 있고*, *5 가지 는 *아예 안 쓴다*. *그 비대칭 을 인식 하는 것* 이 *진짜 운영*.
3. *모든 워크로드 를 *K8s 에 *욱여 넣을 필요 없다*. *judge-engine, R Shiny, lqc-gateway* 처럼 *systemd 가 *더 맞는 워크로드* 도 있다. *교차 운영 의 현실 적 가치*.
4. *Nomad, Swarm, Mesos* 는 *2026 년 현재 도 *맥락 에 따라 합리적 선택*. *"K8s 가 표준"* 이 *"K8s 가 항상 정답"* 을 의미 하지 않는다.

> *우리 6 노드 K3s 클러스터* 가 *오케스트레이션 의 *15 % 를 *적극 활용* 하고 *85 % 는 *깔려는 있지만 *잠자고 있다*. 그 *잠자는 부분 의 *어느 것을 깨워야 할지* 는 *워크로드 성장* 의 *함수*. *PDB, HPA, NetworkPolicy 완전 적용, PodSecurity Standards, Topology Spread Constraints* 가 *다음 단계 의 *유력 후보*.

*Kubernetes 가 *해 주는 일* 의 *전체 지도* 를 *알고 있어야* *내 클러스터 가 *어디서 *부족 한지* *알 수 있다*. *그게 *컨테이너 오케스트레이션* 을 *내 머리 위에 *지도 로 *그리는 *시니어 엔지니어 의 일*.

---

## *참고*

- *Brendan Burns, Joe Beda, Kelsey Hightower*, *Kubernetes: Up and Running*.
- *Mesosphere 의 Marathon 공식 문서* (현재 archived).
- *HashiCorp Nomad 공식 문서* — [nomadproject.io/docs](https://www.nomadproject.io/docs).
- *Apache Mesos 의 *역사* — *Twitter Engineering Blog 시리즈* (2014 ~ 2019).
- *CNCF Annual Survey 2024* — 컨테이너 오케스트레이션 채택 통계.
- *Adrian Cockcroft* (Netflix) — *microservices 시대 의 *오케스트레이션 선택 lecture*.
- 자매편 :
  - [*K8s 의 유용성 — 온프레미스 vs 클라우드*](/2026/06/20/kubernetes-on-premise-vs-cloud-usefulness.html) — *어디서 *돌릴지*
  - [*보안 의 7 기둥*](/2026/06/20/security-7-pillars-auth-encryption-firewall-audit.html) — *어떻게 *지킬지*
  - [*Prometheus + Grafana*](/2026/06/19/prometheus-grafana-metrics-visualization.html) — *어떻게 *관찰할지*
  - [*논블로킹 I/O 서버*](/2026/06/19/non-blocking-io-server-deep-dive.html), [*Virtual Thread*](/2026/06/19/virtual-thread-and-carrier-thread-relationship.html), [*I/O 병목*](/2026/06/18/io-bottleneck-how-to-solve.html), [*CPU 캐시*](/2026/06/18/cpu-l1-l2-l3-cache-and-bottleneck-analysis.html) — *그 위에서 *돌릴 코드 의 기본기*
