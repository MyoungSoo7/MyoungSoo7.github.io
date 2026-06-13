---
layout: page
title: About
permalink: /about/
---

## 푸른영혼의 별 | Java Backend Engineer

공공·이커머스 환경에서 운영 중인 시스템의 *안정성* 과 *변경 비용* 을 기준으로 구조를 설계해온 백엔드 엔지니어. 7년차.

### 기술 스택
- **Backend**: Java 25, Kotlin 2.0, Spring Boot 4, JPA/Hibernate, Kafka, Elasticsearch, gRPC
- **System / 정량**: C++20 (Boost.Beast, simdjson, Arrow/Parquet, ONNX Runtime), Rust (tokio), Go, Julia (JuMP, HiGHS), R (Shiny, rugarch, forecast), Python (pandas, vectorbt)
- **Architecture**: Hexagonal, MSA, Event-Driven, DDD
- **Infra**: K3s 1.35 (3-master HA, embedded etcd), ArgoCD, Velero, Cloudflare Tunnel, Cloudflare R2, GitHub Actions, SOPS+age
- **Frontend**: Next.js 16, React 19, TypeScript, Tailwind, hls.js
- **DB**: PostgreSQL 17, Redis 7, MySQL 8, Apache Parquet
- **AI**: Spring AI, Gemini, RAG, Function Calling, KR-FinBERT (ONNX)
- **Monitoring**: Prometheus, Grafana, Micrometer, Loki

---

<!-- AUTO-UPDATE-START -->
*Last update: 2026-06-13 (KST)* — **6 노드 K3s 클러스터** · **65 ArgoCD 앱** · **22+ 외부 도메인**
<!-- AUTO-UPDATE-END -->

### 운영 중인 시스템

#### 🛒 도메인 사이트 (22+)

| 서비스 | URL | 설명 | 기술 |
|--------|-----|------|------|
| **Settlement MSA** | [jen.lemuel.co.kr](https://jen.lemuel.co.kr) | 이커머스 정산 플랫폼 (4모듈 MSA, **HA 3 replica**) | Spring Boot 4 + Kafka + ES |
| **ASAT** | [eln.lemuel.co.kr](https://eln.lemuel.co.kr) | 청각 재활 훈련 시스템 (K3s 5컴포넌트) | Spring Boot + Next.js + Postgres + Redis + MinIO |
| **Sparta MSA (AI 검색)** | [chat.lemuel.co.kr](https://chat.lemuel.co.kr) | Spring Cloud Gateway + AI 챗봇 (**HA 3 replica**) | Spring AI + Gemini + pgvector |
| **K-POP 굿즈** | [goods.lemuel.co.kr](https://goods.lemuel.co.kr) | 굿즈 뽑기 (*데모 — 익명 가챠 모드*) | Spring Boot 4 + Next.js 16 |
| **패션 매칭** | [fashion.lemuel.co.kr](https://fashion.lemuel.co.kr) | 디자이너-의뢰인 매칭 + AI 프로필 | Spring Boot 4 + Next.js + AI |
| **라이브커머스** | [live.lemuel.co.kr](https://live.lemuel.co.kr) | 실시간 방송 상품 판매 | Spring Boot 4 + React |
| **SNS** | [sns.lemuel.co.kr](https://sns.lemuel.co.kr) | SNS 피드 (Kafka + SSE 실시간 알림) | Spring Boot 4 + Kafka |
| **약국 추천** | [pharmacy.lemuel.co.kr](https://pharmacy.lemuel.co.kr) | 위치 기반 약국 추천 | Spring Boot 4 + Redis + 카카오 API |
| **최저가 쇼핑** | [lowshopping.lemuel.co.kr](https://lowshopping.lemuel.co.kr) | 네이버 쇼핑 최저가 비교 | Spring Boot 4 + Thymeleaf |
| **코딩테스트** | [codingtest.lemuel.co.kr](https://codingtest.lemuel.co.kr) | 100문제 학습 앱 | Spring Boot 4 + H2 |
| **SQL 학습** | [database.lemuel.co.kr](https://database.lemuel.co.kr) | SQL 코딩 테스트 연습 | Spring Boot 4 + MySQL |
| **RealGrid** | [realgrid.lemuel.co.kr](https://realgrid.lemuel.co.kr) | 엔터프라이즈 데이터 그리드 | Spring Boot 4 + React |
| **AI 비서** | [jabis.lemuel.co.kr](https://jabis.lemuel.co.kr) | 일정/메모/할일 AI 비서 | Spring Boot 4 + OpenAI/Anthropic |
| **Media Search** | [media.lemuel.co.kr](https://media.lemuel.co.kr) | 무료 이미지/동영상 검색 | Spring Boot 4 + Pexels API |
| **Auto Trading** | [stock.lemuel.co.kr](https://stock.lemuel.co.kr) | 자동 주식매매 (KIS API) | Spring Boot 4 + PostgreSQL |
| **Crypto Trading** | [crypto.lemuel.co.kr](https://crypto.lemuel.co.kr) | 빗썸 암호화폐 자동매매 | Spring Boot 4 + Bithumb API |
| **K8s Dashboard** | [k8s.lemuel.co.kr](https://k8s.lemuel.co.kr) | Kubernetes 클러스터 관리 | K3s + Dashboard v2.7 |
| **Homelab Dashboard** | [k3s.lemuel.co.kr](https://k3s.lemuel.co.kr) | 자체 제작 K3s 운영 대시보드 | Spring Boot 3 + Thymeleaf + K8s Java client 24 + JSch |
| **frp Self-Hosted Tunnel** | [frp.lemuel.co.kr](https://frp.lemuel.co.kr) | Cloudflare Tunnel 의 *self-host 카운터파트* (2026-06-08 신규) | Fast Reverse Proxy + Helm + ArgoCD |
| **Ghost CMS Blog** | [blog.lemuel.co.kr](https://blog.lemuel.co.kr) | 일반 글 / 본질 / 회고 (Admin API 자동 게시) | Ghost 5.130 + SQLite |
| **Burger Display Order** | [qr.lemuel.co.kr](https://qr.lemuel.co.kr) | 매장 키오스크 주문 디스플레이 (QR 결제) | React 18 + Vite + TossPayments + nginx |
| **Grafana** | [grafana.lemuel.co.kr](https://grafana.lemuel.co.kr) | 서비스 모니터링 대시보드 | Grafana + Prometheus |

#### 🏛️ 통합 정량 인프라 — [lemuel-quant-core](https://github.com/MyoungSoo7/lemuel-quant-core)

9개 언어 ~5,500 lines. 6개 사이트 (crypto/stock/dart/news/data/codingtest) 의 데이터 수집·분석·시그널을 통합한 백엔드 코어.

| 모듈 | 언어 | 서버 | 역할 |
|------|------|------|------|
| judge-engine | C++20 + gRPC | 르무엘 (systemd) | seccomp+cgroup 샌드박스 코드 채점 |
| market-feed | C++20 + Boost.Beast | 루이스 | Binance WSS → Redis pub/sub |
| stock-feed | C++20 + KIS API | 루이스 | 한투 OpenAPI WS → Redis |
| dart-crawler | C++20 + libpqxx | 루이스 | DART 공시 폴러 → PostgreSQL |
| news-pipeline | C++20 + KR-FinBERT | 르무엘 | RSS + NER + 감성분석 |
| data-warehouse | C++20 + Apache Arrow | 르무엘 | 5분 rollup → R2 Parquet |
| orderbook-matcher | Rust + tokio | 루이스 | L2 호가창 + spread bps |
| lqc-gateway | Go + Prometheus | 루이스 | metrics + SSE bridge + healthz |
| QuantTools.jl | Julia + JuMP | 르무엘 | Black-Scholes + Markowitz |
| R 분석 6 | R + Quarto + Shiny | 르무엘 | GARCH/ARIMA/공적분/일간 리포트/대시보드 |
| backtester / strategy-bot | Python + vectorbt | 르무엘 | 전략 백테스트 + 텔레그램 알림 |

> lemuel-academy(동영상 강의 플랫폼)는 진행 중인 작업이라 [/progress/](/progress/) 의 작업 로그로 이동했습니다.

---

### 🏗️ 인프라 — 온프레미스 K3s 클러스터 (**6 노드**, 100% 자체호스팅)

#### 노드 구성 (2026-06-13 기준)

| 서버 | 사양 | K3s 역할 | tier | 주요 워크로드 |
|------|------|----------|------|---------------|
| **르무엘 (lemuel)** | 4 vCPU / 32GB RAM / Ubuntu 24.04 | control-plane, etcd, leader | management | news-pipeline, judge-engine (systemd), GitHub Actions runner |
| **루이스 (louise)** | i7-8565U 8 vCPU / 16GB RAM / Ubuntu 24.04 | worker | worker | market-feed (C++), orderbook-matcher (Rust), lqc-gateway (Go), dart-crawler, settlement/sparta replica 1 |
| **데이비드 (david)** | 6 vCPU / 16GB RAM / Ubuntu 26.04 | worker (모니터링) | worker | kube-prometheus-stack, Loki, lemuel-explorer, settlement/sparta replica 2 |
| **일원 (ilwon)** | 12 vCPU / 32GB RAM / 457GB NVMe + 4TB HDD + 1TB SSD / Ubuntu 26.04 | control-plane, etcd | storage | postgres / storage 풀, ASAT, lowshopping, pharmacy |
| **솔로몬 (solomon)** | 저전력 소형 노드 / 4 vCPU / 15GB / *Intel DC S3700 SSD (etcd 이전 2026-06-06)* / Ubuntu 26.04 | control-plane, etcd | storage-backup | backup 전용 + etcd quorum |
| **이사갈 (isagal)** ⭐ *2026-06-07 신규* | **40 vCPU / 15GB RAM / 3.6TB SSD** / Ubuntu 26.04 | worker (*CPU 깡패*) | worker | settlement/sparta replica 3 (HA 보강), frp self-host, 추가 워크로드 수용 capacity |

**총합** : **74 vCPU / 126 GB RAM / 9 TB+ 스토리지** (NVMe + HDD + SSD)

> 이사갈 합류 (2026-06-07) 로 클러스터 capacity 가 약 1.6배 확장. HA 3 replica + podAntiAffinity 로 *각 핵심 서비스가 3 노드에 spread* 됨.

#### K3s 운영 방식

**3-master HA + embedded etcd** (2026-05-12 완료)
- SQLite → embedded etcd 인플레이스 마이그레이션 (18 분 다운타임으로 30+ ArgoCD 앱 모두 보존)
- RAFT 합의 (르무엘 / 일원 / 솔로몬 3 voter quorum)
- 솔로몬 etcd 디스크 SSD 이전 (2026-06-06, Intel DC S3700) — etcd p99 latency *극적 개선*
- 이사갈은 *worker only* — etcd 멤버 아님 (2026-06-07 orphan Learner 멤버 제거 정리 완료)

**외부 노출 — Cloudflare Tunnel + frp Self-Host**
- 외부 직접 노출 포트 *없음*. cloudflared 가 클러스터 내부 트래픽 중계
- 22+ 외부 도메인 모두 lemuel.co.kr 산하 서브도메인
- Cloudflare Access (SSO + Zero Trust) 로 관리 페이지 보호
- 2026-06-08 *frp self-host 추가* — Cloudflare Tunnel 의 self-host 카운터파트 (5 PR 의 디버깅 + 학습)

**GitOps — ArgoCD + Image Updater**
- Helm 차트 기반 *65+ ArgoCD 앱* 매니페스트가 GitHub repo 단일 진실
- 컨테이너 이미지 푸시 → ArgoCD Image Updater 가 차트 values 자동 갱신
- 시크릿은 SOPS + age 로 git 안에 암호화 보관 (6 머신 + Mac 모두 등록)

**HA 정책 (2026-06-08 적용)**
- settlement / sparta : *replicas 3 + podAntiAffinity preferred*
- 각 핵심 서비스가 *david / louise / isagal 3 노드에 spread*
- 노드 1개 fail 해도 *2/3 ready 유지* (downtime 0)

**백업 — Velero + Cloudflare R2**
- daily-with-volumes : 03:00 KST, 전체 ns, 30 일 TTL
- hourly-critical : 매시 정각, jen/asat/fashion/settlement/ghost/jabis/argocd, 7 일 TTL
- PV 데이터는 Kopia uploader (PodVolumeBackup), object lock 활성
- node-agent OOM fix (2026-06-07) — DaemonSet mem 512Mi→2Gi + KOPIA_PARALLEL_FILE_READS=2

**모니터링 & 알림**
- **kube-prometheus-stack** — Prometheus + Grafana + Alertmanager + node-exporter
- **Loki** (로그 집중화, 데이비드 노드)
- **Blackbox Exporter** (HTTPS 도메인 외부 가용성)
- **ServerCheck 봇** (Mac 에서 5 분 cycle, SSH + HTTP 헬스체크, Telegram 알림)
- *4 개 병렬 Claude 세션* 이 동일 알림에 독립 반응 (디버깅 자동화)

**네트워크 / 보안**
- 호스트 방화벽 (ufw) 화이트리스트 정책 — K8s control plane / kubelet / flannel / etcd 트래픽은 *내부 LAN 으로만 제한*
- 모든 SSH 접속은 *비표준 포트 + key-only*
- 노드 간 트래픽은 모두 LAN, 외부 노출은 Cloudflare 단일 진입점

#### 최근 운영 / 학습 기록 (2026-06)

**인프라 변경**
- (2026-06-06) 솔로몬 etcd 디스크 SSD 이전 (Intel DC S3700)
- (2026-06-07) **이사갈 노드 신규 합류** — 40 vCPU CPU 깡패, etcd orphan Learner 멤버 제거 정리
- (2026-06-07) Velero node-agent OOM 해소 — mem 2Gi
- (2026-06-08) frp self-host 추가 — Cloudflare Tunnel 의 *self-host 카운터파트*
- (2026-06-08) settlement/sparta HA — replicas=3 + podAntiAffinity preferred
- (2026-06-09) Goods online 데모 리팩토 — 로그인 제거, *익명 가챠 모드* + V3 seed (IDOL/ACTOR/ETC 9 sets)

**시리즈 글 (2026-06 깃헙블로그)**
- *성능 시리즈* — 처리량/응답시간 → 수직/수평 확장 → 로컬/리모트 캐시 → GC/메모리 → CDN 비교 → DB 성능 9 층
- *트랜잭션 시리즈* — 트랜잭션 경계 → 롤백 전략 7가지
- *기본 시리즈* — 구조적 프로그래밍 + 자료구조 → Java vs Python → 자료구조/알고리즘 본질
- *AI 시대 시리즈* — 자바 다시 배운다면 / 바이브 코딩 PM vs 개발자 / 생성형 AI 원리 (GPT/Gemini/Claude)
- *디자인 패턴* — Java vs Python / Spring Boot 안의 패턴
- *역사* — 소프트웨어 위기 60년 (CPU/Memory/HDD/SSD 발전사)
- *철학* — 안정과 고도화 / CS vs CE / 어셈블리 ↔ JVM
- *Ghost 블로그* — 과학·기술·수학·중급수학 *본질* 시리즈

---

### 링크
- **GitHub**: [MyoungSoo7](https://github.com/MyoungSoo7)
- **블로그**: [iamipro.tistory.com](https://iamipro.tistory.com)
- **Ghost 블로그**: [blog.lemuel.co.kr](https://blog.lemuel.co.kr) — 일반 글 / 본질 / 회고
- **포트폴리오**: [Notion](https://www.notion.so/a43ac75e1d964a01a6e8c679fbd70677)
