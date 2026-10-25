---
layout: post
title: "홈랩 k3s 클러스터에 지금 무엇이 돌고 있나 — 2026-10-26 실측 인벤토리"
date: 2026-10-26 02:30:00 +0900
categories: [Kubernetes]
tags: [k3s, homelab, argocd, kafka, strimzi, prometheus, falco, velero, gitops]
---

"클러스터에 뭐가 돌고 있어?" 라는 질문에 기억으로 답하면 틀린다. 이 글의 모든 숫자는
2026-10-26 새벽 `kubectl` 로 직접 뽑은 값이다. 네트워크 구성(주소·장비 정보)은 의도적으로 뺐다.

## 1. 하드웨어 — 4노드, x86 미니PC 급

| 노드 | 역할 | vCPU | 메모리 | 사용률(CPU / MEM) |
|---|---|---|---|---|
| ilwon | control-plane, etcd | 12 | 32 GiB | 7% / 73% |
| lemuel | control-plane, etcd | 4 | 32 GiB | 59% / 52% |
| solomon | etcd | 4 | 16 GiB | 13% / 32% |
| louise | worker | 8 | 16 GiB | 8% / 64% |

- 쿠버네티스 배포판은 [k3s](https://docs.k3s.io/) `v1.35.4+k3s1`, 전부 amd64, OS 는 Ubuntu 24.04 / 26.04 혼재.
- etcd 멤버가 3개라 하나가 죽어도 쿼럼이 유지된다. k3s 의 내장 etcd HA 구성은
  [공식 문서 — High Availability Embedded etcd](https://docs.k3s.io/datastore/ha-embedded) 그대로다.
- 한때 6노드였지만 전력 절감으로 줄였다(→ [이전 글](/2026/10/15/isagal-retirement-cluster-6-to-5-power-savings/)).
  지금은 4노드다.

메모리가 CPU 보다 먼저 찬다. 홈랩에서 흔한 패턴이고, ilwon 은 그래서 kubelet 예약·퇴거 임계값을 따로 잡아 뒀다.

## 2. 규모 한눈에

- 네임스페이스 **49개**
- 파드 **129 Running** + 13 Completed (CronJob 잔여)
- CRD **61종**, PVC **45개**
- Argo CD Application **69개 — 전부 `Synced / Healthy`**

## 3. 플랫폼 계층 — 앱을 떠받치는 것들

### GitOps: Argo CD
클러스터 상태의 기준은 Git 이다. [Argo CD](https://argo-cd.readthedocs.io/en/stable/) 가 69개 앱을
동기화하고, `argocd-image-updater` 가 새 이미지 태그를 감지해 매니페스트를 갱신한다.
ApplicationSet 컨트롤러도 떠 있다.

### CI: Actions Runner Controller + BuildKit
`arc-system` / `arc-runners` 에 [Actions Runner Controller](https://docs.github.com/en/actions/hosting-your-own-runners/managing-self-hosted-runners-with-actions-runner-controller/about-actions-runner-controller)
가 있어 GitHub Actions 잡이 클러스터 안 러너 파드에서 돈다. 이미지 빌드는 `buildkitd`,
pull 은 `registry-mirror` 로 캐시한다.

### 관측성
- **메트릭:** kube-prometheus-stack — [Prometheus Operator](https://prometheus-operator.dev/),
  Prometheus, Alertmanager, Grafana, node-exporter(DaemonSet 4개), kube-state-metrics.
- **트레이스:** [Grafana Tempo](https://grafana.com/docs/tempo/latest/).
- **로그:** [Fluent Bit](https://docs.fluentbit.io/) DaemonSet → Logstash → Elasticsearch(hot 티어).
  Elasticsearch 는 [ECK 오퍼레이터](https://www.elastic.co/guide/en/cloud-on-k8s/current/index.html) 로 관리.
- **외형 감시:** Uptime Kuma.
- Claude Code 텔레메트리 전용 OpenTelemetry 컬렉터도 `monitoring` 에 있다.

### 보안
- [Falco](https://falco.org/docs/) — 런타임 시스템콜 감시, 전 노드 DaemonSet + falcosidekick.
- `sops-operator` — Git 에 암호화해 넣은 시크릿([SOPS](https://github.com/getsops/sops))을 클러스터 안에서 복호화.
- 외부 노출은 `cloudflared` 터널로만 한다. 공유기에 포트를 열지 않는다.

### 백업·스토리지
- [Velero](https://velero.io/docs/) + node-agent(DaemonSet) — 리소스·볼륨 백업.
- StorageClass 5종: k3s 기본 `local-path`, 노드 지정 local-path, SSD/ES 전용 정적 PV, 그리고
  클러스터 안 `nfs-server` 가 제공하는 공유 볼륨.

### 메시징
- [Strimzi](https://strimzi.io/docs/operators/latest/overview) 로 운영하는 **Kafka 4.2.0** 클러스터 `lemuel`.
  노드풀 하나가 controller + broker 를 겸하는 단일 노드 구성 — 즉 ZooKeeper 없는 KRaft 모드다
  (Kafka 4.0 부터 ZooKeeper 모드는 제거됐다: [Apache Kafka 4.0 릴리스 노트](https://kafka.apache.org/40/documentation.html#upgrade_4_0_0)).
  복제는 없으니 학습·개발용 용도다.

### 노드 자가 관리
`kube-system` 에 직접 만든 `node-self-healer`(노드 이상 시 자가복구 스크립트) 같은 자체 DaemonSet 이 있고, CoreDNS 앞단 캐시로 `node-local-dns` 를 깔았다
([NodeLocal DNSCache](https://kubernetes.io/docs/tasks/administer-cluster/nodelocaldns/)).

## 4. 애플리케이션 계층

### 상시 가동 중

| 영역 | 네임스페이스 | 구성 |
|---|---|---|
| 정산 시스템 | `settlement-prod` | 앱·조회·재무·운영·외부데이터·서킷브레이커·프론트 등 **9개 서비스 Deployment** + Elasticsearch + Redis. 영수증 OCR, 시세 스트림 포함 |
| 프로젝트 관리 | `plane-prod` | [Plane](https://docs.plane.so/) 셀프호스팅 — web/api/worker/live + Postgres, RabbitMQ, MinIO, Redis |
| 사진 | `immich-prod` | [Immich](https://immich.app/docs/overview/introduction) 서버 + ML + Postgres + Redis |
| 블로그 | `ghost-prod` | Ghost (비 IT 글 전용 블로그) |
| 워크플로 자동화 | `n8n` | n8n |
| 메모 | `memos-prod` | Memos |
| 검색 | `searxng-prod`, `blogsearch-prod`, `media-search-prod` | 메타 검색엔진 SearXNG, 블로그·미디어 검색 |
| 로컬 LLM | `openviking` | Ollama + 애플리케이션 |
| 에이전트 실험 | `agent-system` | NeMo Guardrails, Nemotron Nano, 감시·카나리 에이전트, Dragonfly(인메모리 스토어) |
| IoT / 제조 | `iot`, `fab-lab` | MQTT 브로커, 로봇 시뮬레이터, 반도체 공정 데이터(SECOM) 리플레이어 + 이상 탐지기 |
| 기타 | `codingtest-prod`, `landing-prod`, `ghstats`, `database-prod`, `jen-prod`, `analytics-prod` | 코딩테스트, 랜딩, GitHub 통계, MySQL/Postgres |

### 꺼둔 것 (replicas 0)
`lemuel-xr-prod`, `trading-prod`, `crypto-prod`, `sns-prod`, `asat-prod`, `data-prod` 는
매니페스트와 Argo CD 앱은 살아 있지만 **replicas 0** 이다. 메모리가 빠듯한 4노드에서
당장 쓰지 않는 서비스는 내려 두고, 필요할 때 Git 에서 숫자만 올린다. GitOps 의 장점이
가장 체감되는 지점이다 — 끄는 것도 커밋이고, 다시 켜는 것도 커밋이다.

## 5. 정리

- 4노드·총 28 vCPU·약 92 GiB에 **앱 20여 종 + 풀스택 플랫폼**(GitOps, CI, 메트릭·로그·트레이스, 런타임 보안, 백업, Kafka)을 올려 두었다.
- 병목은 CPU 가 아니라 **메모리**다. 그래서 "안 쓰면 0 으로" 가 운영 원칙이 됐다.
- 69개 Argo CD 앱이 전부 Synced/Healthy — 상태를 기억이 아니라 Git 과 `kubectl` 이 말해준다.

## References

- k3s Documentation — <https://docs.k3s.io/>
- k3s High Availability Embedded etcd — <https://docs.k3s.io/datastore/ha-embedded>
- Argo CD Documentation — <https://argo-cd.readthedocs.io/en/stable/>
- GitHub Docs, About Actions Runner Controller — <https://docs.github.com/en/actions/hosting-your-own-runners/managing-self-hosted-runners-with-actions-runner-controller/about-actions-runner-controller>
- Prometheus Operator — <https://prometheus-operator.dev/>
- Grafana Tempo Documentation — <https://grafana.com/docs/tempo/latest/>
- Fluent Bit Documentation — <https://docs.fluentbit.io/>
- Elastic Cloud on Kubernetes — <https://www.elastic.co/guide/en/cloud-on-k8s/current/index.html>
- Falco Documentation — <https://falco.org/docs/>
- SOPS — <https://github.com/getsops/sops>
- Velero Documentation — <https://velero.io/docs/>
- Strimzi Overview — <https://strimzi.io/docs/operators/latest/overview>
- Apache Kafka 4.0 Upgrade Notes — <https://kafka.apache.org/40/documentation.html#upgrade_4_0_0>
- Kubernetes, Using NodeLocal DNSCache — <https://kubernetes.io/docs/tasks/administer-cluster/nodelocaldns/>
- Plane Docs — <https://docs.plane.so/>
- Immich Docs — <https://immich.app/docs/overview/introduction>
