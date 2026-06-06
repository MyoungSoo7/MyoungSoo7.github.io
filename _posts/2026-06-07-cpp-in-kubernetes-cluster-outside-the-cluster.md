---
layout: post
title: "내 K3s 클러스터의 *모든 시세 데이터* 가 C++ 를 거치는데, *왜 C++ Pod 는 하나도 없는가* — 6 모듈 quant-core 와 K8s 의 *contract 분리*"
date: 2026-06-07 00:30:00 +0900
categories: [kubernetes, cpp, architecture]
tags: [cpp, cpp20, kubernetes, k3s, systemd, gRPC, redis, websocket, market-data, judge-engine, sandboxing, seccomp, architecture, bounded-context]
---

내 *K3s 클러스터* 의 ArgoCD 대시보드를 열면 *64 개 Application* 이 떠 있다. *crypto-prod, dart-prod, trading-prod, codingtest-prod, data-prod, sns-prod, lemuel-xr-prod, settlement-prod, sparta-prod, …*. 그 중 *crypto / dart / trading / codingtest / data / news* 6개 사이트는 *전부 *시세 / 공시 / 뉴스 / 채점* 같은 *latency-critical 한 데이터 흐름* 위에서 돌아간다. 그런데 *그 데이터의 *원천* 은 *전부 C++ 로 쓰여 있다*.

그렇다면 *이 C++ 코드가 어디서 도는가*. 답은 *놀랍게도 K3s 클러스터 안이 아니다*. *Pod 한 줄 없다*. C++ 6 모듈은 *클러스터의 *바깥*, 즉 *systemd unit* 으로 *bare metal 위에서 직접 돈다*. 그 결과물만 *gRPC / Redis pub-sub / Parquet on R2* 를 통해 *클러스터 안의 Spring Boot · Next.js · Python 서비스* 로 흘러들어간다.

처음 보면 *비대칭적이고 어색* 해 보인다. *"왜 K8s 시대에 systemd 를?"*. 그러나 *6개월 운영* 해보니 이 *Layer 분리* 가 *유일하게 작동* 하는 형태였다. *그 이유* 를 *3 layer 의 contract* 로 분해해서 기록한다.

이 글은:
1. *quant-core 의 6 모듈* 과 *각각이 왜 C++ 인가*
2. *왜 C++ 가 K8s Pod 가 아닌 systemd 인가* — *4 가지 mismatch*
3. *경계의 contract* — *클러스터 안과 밖이 만나는 *3 개 채널* (gRPC, Redis, Parquet)
4. *그래서 K8s 는 무엇을 책임지는가* — *오케스트레이션의 영역 vs latency 의 영역*

순으로 진행한다.

---

## TL;DR

**한 줄 요약**

> *K3s 클러스터* 는 *애플리케이션 오케스트레이션의 영역*. *C++ quant-core* 는 *나노~밀리초 단위 latency 와 *영구 WebSocket 세션* 의 영역. 두 layer 는 *gRPC / Redis / Parquet* 라는 *contract* 로 *느슨하게 결합* 하고, *각자가 잘하는 일만 하는 것* 이 *cluster 가 64 앱을 *안정적으로 굴리면서도 C++ 가 *마이크로초의 자유* 를 *유지* 할 수 있는 *유일한 방법* 이다.

**3 layer 분리**

| Layer | 도구 | 책임 | 왜 |
|-------|------|------|----|
| **외곽 (bare metal + systemd)** | C++20, Boost.Beast WS, simdjson, libpqxx, Apache Arrow, ONNX | 시세 수집, 공시 크롤, 뉴스 NLP, 채점 샌드박스, 시계열 저장 | *latency*, *WebSocket 영구 연결*, *seccomp/cgroup 직접 제어*, *외부 IP allowlist* |
| **경계 (cross-boundary contracts)** | gRPC, Redis pub/sub, PostgreSQL, Parquet on S3-호환 객체 스토리지 | 외곽과 클러스터 사이의 *데이터 흐름과 의미 약속* | *언어/배포 독립*, *backpressure*, *replay 가능* |
| **클러스터 (K3s)** | Spring Boot, Next.js, Python(FastAPI), Postgres, ELK | 사용자 노출 API, UI, 검색·집계·BI | *오케스트레이션*, *HA*, *GitOps*, *self-heal*, *blue-green* |

---

## 1. quant-core 의 6 모듈 — *각각이 왜 C++ 인가*

`lemuel-quant-core` 는 *C++20 모노레포* 다. CMake 로 *6 개 모듈* 을 *각자 독립 빌드/배포* 하고, *공통 shared 라이브러리* (네트워크, 직렬화, 로깅) 를 *static link* 한다.

```
lemuel-quant-core/
├── shared/               # 공통 유틸 (FeedClient 추상화 등)
├── modules/
│   ├── judge-engine/     # 샌드박스 코드 채점 (seccomp + cgroup)
│   ├── market-feed/      # 암호화폐 거래소 WebSocket 수집
│   ├── stock-feed/       # 한국 주식 시세/호가 수집 (한투 OpenAPI)
│   ├── dart-crawler/     # DART 공시 수집/파싱
│   ├── news-pipeline/    # 뉴스 크롤링 + NER + 감성분석
│   └── data-warehouse/   # 통합 시계열 저장 (Parquet + R2 백업)
```

### 1.1 `judge-engine` — *왜 C++ 인가*

코딩테스트 사이트의 *제출 코드* 를 *받아 실행* 하고 *시간·메모리 한계* 안에서 *정답 비교* 하는 모듈. *외부 코드를 *내 호스트에서 실행* 한다는 게 *위험* 한 작업이라 *Linux 커널 단의 격리* 가 *필수*.

| 요구사항 | 왜 C++ |
|----------|--------|
| `seccomp-bpf` 필터 *직접 작성* — 허용 syscall 명시 | libc 의 `prctl(SECCOMP_SET_MODE_FILTER)` 직접 호출, *Go/Java runtime 의 helper thread* 가 *예측 못한 syscall* 발생시키는 문제 회피 |
| `cgroup v2` 의 *메모리·CPU 한계* 동적 생성 | `/sys/fs/cgroup/...` 에 직접 write, 짧은 라이프사이클의 *fork/exec* 로 *수십 ms 단위 spawn* |
| 채점 시간 *측정 오차 < 1ms* | userspace 의 `clock_gettime(CLOCK_MONOTONIC)` + `rusage` 직접 — JVM warm-up / GC pause 가 없는 환경 |

> 채점은 *0.5 초 안에 끝나는* 짧은 작업이 *동시 수십 개* 들어온다. *JVM cold start* 200ms 가 *유효 채점 시간을 절반* 으로 깎는다. *Go runtime 의 sigaltstack* 이 seccomp 룰과 *충돌* 한다. *C++ + raw syscall* 이 *유일한 안전한 길*.

### 1.2 `market-feed` — *암호화폐 시세*

*Binance / Upbit 등의 WebSocket endpoint* 에 *영구 연결* 해서 *틱 단위 가격·호가창* 을 *받아내고 정규화* 해서 *다운스트림* 으로 흘려보낸다.

| 요구사항 | 왜 C++ |
|----------|--------|
| *지속 연결 100 + 채널*, 메시지 *수 천/초* | `Boost.Beast` 의 *zero-copy 파서* + `simdjson` 의 *SIMD JSON 디코드* (Java Jackson 보다 *5-10×*) |
| GC pause 가 *틱 손실* 로 직결 | C++ 의 *deterministic destruction* — GC pause window 자체가 *존재하지 않음* |
| 호가창 *내부 표현* 이 *L1 cache* 안에 *상주* | *packed struct + std::array* 로 *cache line 정렬*, JVM 의 *object header overhead* 회피 |

### 1.3 `stock-feed` — *한국 주식*

한국투자증권 OpenAPI 의 *실시간 시세* (WebSocket + KIS 자체 프로토콜) 수집. *암호화폐와 달리* *영업시간 정해진 burst 패턴* 이라 *peak throughput* 보다 *peak latency tail* 이 중요.

> *동시호가 직전 9 시* 의 *호가창 폭주* 가 *수 십만 메시지/초*. *Tail latency p99.9* 가 *5ms 안* 으로 들어와야 *호가창 재구성이 *현재 시각과 동기화*.

### 1.4 `dart-crawler` — *DART 공시*

금융감독원의 *DART OpenAPI* 를 *5 분 주기 poll* 해서 *신규 공시* 만 *중복 제거* 해서 저장. *고빈도* 는 아니지만 *XML/HTML 파싱과 동적 schema 처리* 가 무거워 *libxml2 + libpqxx batch insert* 의 *zero-copy 경로* 가 *Python 의 lxml-loop* 대비 *5×* 빠르다.

### 1.5 `news-pipeline` — *뉴스 + NER + 감성*

RSS 수집 → *형태소 분석* → *NER (개체 인식)* → *감성 분석* → *점수보드 push* 의 *4 단계 파이프라인*. 모델 추론은 *ONNX Runtime C++ API* 로 *동일 프로세스 안* 에서 직접 호출 — *서비스 간 IPC 왕복* 없이 *latency 최소화*.

### 1.6 `data-warehouse` — *시계열 저장*

위 5 개 모듈이 흘려보낸 데이터를 *Apache Arrow Parquet* 로 *컬럼 압축* 해서 *S3 호환 객체 스토리지* 로 영구 백업. *수십 GB/일* 의 *write throughput* 이 *libarrow + zstd* 의 *zero-copy 컬럼 빌더* 위에서 *단일 프로세스 단일 노드* 로 처리됨.

---

## 2. *왜 K8s Pod 가 아닌가* — 4 가지 mismatch

이 6 모듈을 *컨테이너 이미지로 만들어 *Pod 로 띄우면 안 되나?* 처음엔 그러려고 했다. *4 번* 실패하고 *systemd 로 회귀* 했다. 그 *4 개의 부적합* 을 *layer 별로* 분해하면:

### 2.1 *영구 WebSocket 세션 ↔ Pod 의 ephemeral 생명주기*

K8s Pod 는 *언제든 evict 가능* 한 *임시 실체* 다. *NodeNotReady, scheduling priority, rolling update, image update, OOM, kubelet restart* — *수십 가지 트리거* 가 *Pod 을 재시작* 시킨다. 매 재시작마다:

- WebSocket *재핸드셰이크* (수 백 ms)
- 거래소 측 *rate limit* (IP 당 *연결 X 개/분*) 위반 위험
- *호가창 메모리 재구성* 을 *snapshot REST 호출* 로 보충 — *snapshot 자체* 가 *분당 N 회 제한*

> *WebSocket 재연결 = 시세 *공백 *수 백 ms*. 그게 *Pod restart 가 흔한 K8s 환경* 에서는 *시도 때도 없이* 발생한다.

*systemd unit* 은 *bare metal 의 *PID 1* 아래 *Restart=on-failure* 로 *프로세스만 재시작*. *호스트* 가 *물리적으로 살아 있는 동안* 은 *프로세스 정체성* 이 *영속*. *재시작 빈도* 가 *K8s Pod 의 *수십 분의 1*.

### 2.2 *seccomp + cgroup ↔ K8s 의 *이미 cgroup* 위*

judge-engine 은 *코드 채점 시점* 에 *동적으로 cgroup* 을 만들어 *메모리·CPU 한계* 를 *fork 하는 자식 프로세스* 에 *덮어씌운다*. K8s Pod 안에서 이 작업을 하면:

- Pod 자체가 이미 *kubelet 이 만든 cgroup* 안에 있음 (cgroup v2 의 *unified hierarchy*)
- 그 *안에서 *자식 cgroup* 을 또 만들면 *권한 정책* (`Delegate=yes` of systemd 와 동등한 K8s pod 의 cgroup namespace 설정) 이 *복잡*
- `seccomp-bpf` 의 *프로파일 합성* 이 *containerd 의 *기본 seccomp profile* 과 *겹쳐서 *예측 어려운 거부* 발생

*컨테이너의 격리* 와 *내가 직접 채점 격리* 의 *이중 격리* 는 *서로 disable* 시키지 않으면 *작동 안 함*. 그리고 *컨테이너 격리만 의존* 하면 *코드 실행 환경* 이 *프로세스 단위 격리가 아니라 *Pod 단위 격리* — 한 Pod 안에서 *수십 개 채점 동시 실행* 이 *서로 격리되지 않는다*.

> *bare metal + systemd + seccomp + cgroup* 의 *단순한 4 층* 이 *K8s Pod + containerd + cgroup + seccomp + 내 seccomp + 내 cgroup* 의 *6 층* 보다 *훨씬 진단 가능* 하고 *훨씬 안전*.

### 2.3 *외부 IP allowlist ↔ Pod 의 *random source IP**

한국투자증권 API 는 *고객 등록 시 IP allowlist* 를 *고정 등록* 해야 한다. *Pod 의 outbound source IP* 는 *기본적으로 노드의 IP* 지만, *K8s 의 SNAT 정책*, *CNI (flannel/cilium) 의 동작*, *cloud LB 의 source NAT* 에 따라 *어느 노드의 어느 IP 로 나가는지* *예측 어렵다*.

*systemd 로 *호스트에서 직접 돌면* — *그 호스트의 *primary IP* 가 *source*. *고정 등록* 가능. *Cloudflare Tunnel* 이라는 *추가 layer* 의 source IP 변환을 *우회*.

### 2.4 *언어 런타임 ↔ 컨테이너 이미지 size*

C++ 모듈은 *전체 의존성을 static link* 하면 *단일 실행파일 ~ 50 MB*. Spring Boot 의 *JRE 포함 이미지* 는 *기본 250 MB*. *6 개 모듈을 K8s 에 띄우려면 *6 개의 컨테이너 이미지 + 6 개 ArgoCD Application + 6 개 Service + 6 개 PVC* — *정작 *binary 자체는 50 MB* 인데 *오케스트레이션 metadata 가 더 크다*.

*systemd unit 한 줄 = 이미 binary 1 개*. *오케스트레이션 표면적이 0*.

---

## 3. 경계의 contract — *3 개 채널*

이게 *진짜 흥미로운 부분*. 외곽과 클러스터가 *어떻게 만나는가*. *3 개의 잘 정의된 contract* 가 그 역할을 한다.

### 3.1 채널 1 — gRPC (*동기 RPC*)

```
[클러스터 안]                    [클러스터 밖]
crypto-trading                  market-feed (systemd)
(Spring Boot Pod)               ┌──────────────────┐
  │                             │ Binance WS x N   │
  │  GetSnapshot(symbol)        │ Upbit WS x M     │
  ├────────── gRPC ──────────►  │                  │
  │  ◄────── OrderBook  ────────┤ in-memory book   │
  │                             │                  │
  └─                            └──────────────────┘
```

gRPC 는 *Cloudflare Tunnel 의 내부망* 위에서 *mTLS* 로 보호. *클러스터 안의 Pod* 는 *Service alias* 를 통해 *외부 호스트의 systemd 프로세스* 에 *gRPC 호출* — *마치 클러스터 안의 다른 Service 인 것처럼* 보임.

*왜 gRPC 인가*:
- *Pod 가 *언제 재시작* 해도 *gRPC client 의 *connection pool* 이 *재연결* 하면 끝
- *systemd 가 *그동안에도 *영속 connection* 을 *Binance 와* 유지
- *Protobuf 스키마* 가 *언어 독립적인 contract* — Spring Boot, Python, Go 의 *모든 클라이언트* 가 *같은 .proto* 로 *binding 생성*

### 3.2 채널 2 — Redis pub/sub (*비동기 fan-out*)

```
[market-feed (systemd)]
       │  publish "ticker.binance.BTCUSDT" {"p":...,"t":...}
       ▼
[Redis (클러스터 안 Pod)]
       │
       ├──► crypto-trading (Spring Boot Pod) — 실시간 차트 push
       ├──► auto-trading (Spring Boot Pod)   — 시그널 계산
       ├──► sns-app (Next.js Pod)            — 시세 위젯 push
       └──► data-warehouse (systemd)         — Parquet 컬럼 append
```

*pub/sub* 의 핵심 가치는 *fan-out 의 cost 가 publisher 에서 분리* 되는 것. *market-feed* 는 *하나의 publish* 만 하면 *N 개의 구독자* 가 *각자의 속도* 로 *소비*. *느린 구독자가 빠른 구독자를 막지 않음*.

*backpressure* 는 *Redis Stream + consumer group* 으로 한 단계 더 견고하게 확장할 수 있는데, *현재 정상 부하* 에서는 *순수 pub/sub* 으로 충분하다.

### 3.3 채널 3 — Parquet on S3-호환 객체 스토리지 (*replay 가능 영속*)

```
[data-warehouse (systemd)]
   │
   │ 5 분 마다 in-memory buffer flush
   ▼
   parquet-{date}-{symbol}-{seq}.zst.parquet
   │
   ▼
[S3 호환 객체 스토리지]
   │
   ▼
[클러스터 안의 Spark / Trino / Pandas Pod 등 BI tool]
```

이 채널은 *동기 통신이 아니라 *상태의 영속* 이다. *5 분 단위로 Parquet 컬럼 압축* 해서 *영구 저장*. *클러스터 안의 BI tool 이 *언제든 *과거 데이터 재처리* 가능.

> *gRPC* 는 *지금 이 순간* 의 *현재 상태 질의*. *Redis* 는 *방금 일어난 이벤트의 fan-out*. *Parquet* 는 *과거 전부의 replay*. *세 시간축의 *contract* 가 *명확히 분리* 되어 있다.

---

## 4. 그래서 K8s 는 무엇을 책임지는가

이 분리 끝에 남는 *K8s 의 본질적 역할* 은 *사실 더 명확* 해진다.

### 4.1 *오케스트레이션의 영역*

| 영역 | 도구 | 왜 |
|------|------|----|
| *6 사이트의 Spring Boot / Next.js / Python 서비스* | K8s Deployment + Service | rolling update, replicas, HA, self-heal |
| *각 서비스의 PostgreSQL* | StatefulSet + PVC | PV 의 node affinity 로 *데이터 locality* |
| *각 서비스의 ingress* | Cloudflare Tunnel + Service ClusterIP | *고정 외부 domain* 을 *동적 Pod* 에 매핑 |
| *전체 환경의 *secret 관리* | sops-secrets-operator | GitOps 안에서 *암호화된 secret* 이 *git 추적* |
| *백업* | Velero + Kopia + R2 | *namespace 단위 backup/restore* 의 *one-click* |
| *모니터링* | kube-prometheus-stack + Grafana + ELK | *cluster-wide 메트릭/로그/추적* |

이것들은 *전형적인 *애플리케이션 오케스트레이션의 가치*. K8s 가 *없어도 동작* 은 할 수 있지만 *없으면 운영 인력이 N 배* 든다.

### 4.2 *latency 의 영역은 *systemd 가 책임*

| 영역 | 도구 | 왜 K8s 가 아닌가 |
|------|------|------------------|
| WebSocket 영구 시세 수집 | systemd | Pod restart 의 *수 백 ms 시세 공백* |
| 채점 샌드박스 spawn | systemd | seccomp/cgroup *이중 격리 *복잡도* |
| 외부 API IP allowlist | systemd | Pod 의 *random source IP* |
| Parquet 컬럼 빌더 의 zero-copy | systemd | *언어 런타임 layer* 추가 비용 |

### 4.3 *결합의 contract* 는 *3 개 채널*

| 시간축 | 채널 | 용도 |
|--------|------|------|
| *지금* | gRPC | 현재 상태 질의 |
| *방금* | Redis pub/sub | 이벤트 fan-out |
| *과거 전부* | Parquet on R2 | replay / BI / 학습 |

---

## 5. *대안 — *오즈 시나리오* 4 가지와 그 거절 이유

이 *layer 분리* 가 *유일한 답* 은 아니다. *고려했던 대안* 들을 *왜 안 갔는지* 같이 기록.

### Alt 1 — *모두 K8s 안* (C++ 도 Pod)

- *판단*: Pod 재시작 빈도, seccomp 이중 격리, 외부 IP allowlist 의 *3 중 부적합* 으로 거절.
- *실험 결과*: 시세 공백이 *분당 평균 2 회* 발생 → *호가창 재구성 비용* 이 *수집보다 큼*.

### Alt 2 — *모두 systemd* (Spring Boot 도 systemd)

- *판단*: *오케스트레이션의 가치* 를 *수동 운영으로 대체* 하면 *인력이 N 배*.
- *세부*: rolling update 마다 *해당 호스트의 systemd unit 을 *수동 swap*, secret 관리는 *기계마다 다른 ENV* 파일, 모니터링은 *node_exporter 만으로는 부족* → 결국 *K8s 가 풀어둔 문제* 를 *수동으로 재구현*.

### Alt 3 — *Kubernetes DaemonSet + hostNetwork*

- *판단*: *Pod 의 random source IP 문제* 는 hostNetwork 로 해소 가능. 하지만 *seccomp 이중 격리* 와 *Pod restart 빈도* 는 여전. *부분 해결*.
- *세부*: hostNetwork 가 *모든 노드의 모든 포트* 를 *공유* 시켜 *port collision* 의 *operational risk* 가 *세 배*.

### Alt 4 — *Kubernetes + Pod priority + 영구 PVC + 별도 nodeSelector*

- *판단*: *bare metal 의 *서버 1 대를 *그저 *K8s node* 로 등록* 한 뒤 *해당 node 만 *quant 워크로드* 만 띄우게 *taint*. *systemd 와 거의 동등* 하지만 *kubelet 의 *예측 못한 reconciliation* 이 *간헐 재시작* 유발.
- *세부*: 결국 *Pod 의 ephemeral 본질* 을 *K8s 가 *완전히 끄게* 만들 수는 없음. *K8s 의 *자동 복원 본능* 을 *override* 하는 것 자체가 *K8s 를 쓰는 의미* 를 *깎는 것*.

---

## 6. 학습 압축 — *언어/도구 선택의 기준*

이 분리에서 *일반화 가능한 결론*:

### 6.1 *컨테이너 = 표준 패키징* 이지만 *모든 워크로드* 에 *맞지 않음*

> Pod 의 *ephemeral* 가정과 *영구 외부 연결* 의 *수십 ms 공백* 이 *허용 안 되는 워크로드* 는 *서로 어울리지 않는다*. *컨테이너 표준* 의 *복음* 이 *workload 의 본질적 요구* 를 *덮을 때* 가 있다.

### 6.2 *언어 선택 = 격리 layer 의 수*

> *seccomp + cgroup 의 *직접 제어* 가 *필수* 인 워크로드는 *runtime 의 *helper thread / GC / signal handler* 가 *예측 못한 syscall 발생* 시키는 *high-level runtime* (JVM, Go, Python, Node) 를 *피해야 한다*. C++ / Rust 의 *deterministic destruction* 과 *minimal runtime* 이 *유일한 안전한 길*.

### 6.3 *contract 는 *3 시간축* 으로 분리하면 *재사용성이 직교*

> *지금 (gRPC)*, *방금 (pub/sub)*, *과거 전부 (Parquet)*. 세 시간축에 *각자의 도구* 를 *각자의 protocol 로 명확히 분리* 하면 *클러스터 안과 밖이 *자유롭게 진화*. *systemd 의 *bare metal 프로세스* 가 *언어와 배포 방식* 을 자유롭게 바꿔도 *클러스터 안은 *contract 만 보고 *변경 없음*.

### 6.4 *K8s 의 미덕 = *분리된 영역* 위에서 *그것만 잘함*

> K8s 가 *모든 워크로드* 의 *통일 platform* 이 *되어야 한다* 는 *교조* 를 *버리면*, *그것이 잘하는 영역* (오케스트레이션, GitOps, self-heal) 에서 *놀라울 정도로 잘한다*. *그것이 잘 못 하는 영역* (latency-critical, 영구 외부 connection, kernel-level 격리) 은 *그것에 맡기지 않는다*.

---

## 7. 끝맺음 — *경계가 가치를 만든다*

내 *K3s 클러스터* 의 *64 개 Application* 은 *전부 *Java / Kotlin / TypeScript / Python* 의 *high-level runtime*. *C++ Pod 는 0 개*. 이 사실은 *C++ 가 K8s 와 *어울리지 않는다* 가 아니라 *C++ 가 *K8s 와 다른 layer* 에서 *각자가 잘하는 일에 집중* 한다는 *분업의 결과*.

> *경계가 분명할 때 *두 layer 가 *각자 더 강해진다*. C++ 의 *마이크로초 자유* 와 K8s 의 *오케스트레이션 자동화* 는 *같은 platform 위에서 만나지 않을 때* 가 *각자 더 빛난다*.

오늘 작업 끝낼 무렵의 *분포*:

```
클러스터 안 (K3s)
  Java/Kotlin/TS/Python   64 apps  /  156 Running Pods
  C++ Pods                0 개

클러스터 밖 (systemd, bare metal x 3)
  C++ binary              6 modules
  영구 WebSocket          100+ 채널
  cgroup 채점             동시 32 격리 슬롯

contract (cross-boundary)
  gRPC                    내부망 mTLS
  Redis pub/sub           클러스터 안 Pod
  Parquet on R2           S3-호환 객체 스토리지
```

*숫자가 적은 게 작은 게 아니다*. *6 개 C++ 모듈* 이 *6 개 사이트의 *모든 시세·공시·뉴스·채점* 의 *원천*. *그 원천이 클러스터 안에 있을 필요는 없다*. *경계를 분명히 그은 결과*.

---

*다음 글:* *gRPC contract 를 *어떻게 *Protobuf 스키마 진화* 와 *backward compatibility* 의 함정 없이 *6 사이트의 7 언어 client* 가 *동시에 안전하게 진화* 할 수 있는가.
