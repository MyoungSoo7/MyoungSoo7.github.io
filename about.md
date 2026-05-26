---
layout: page
title: About
permalink: /about/
---

## 푸른영혼의 별 | Java Backend Engineer

공공·이커머스 환경에서 운영 중인 시스템의 안정성과 변경 비용을 기준으로 구조를 설계해온 백엔드 엔지니어입니다.

### 기술 스택
- **Backend**: Java 25, Kotlin 2.0, Spring Boot 4, JPA/Hibernate, Kafka, Elasticsearch, gRPC
- **System / 정량**: C++20 (Boost.Beast, simdjson, Arrow/Parquet, ONNX Runtime), Rust (tokio), Go, Julia (JuMP, HiGHS), R (Shiny, rugarch, forecast), Python (pandas, vectorbt)
- **Architecture**: Hexagonal, MSA, Event-Driven, DDD
- **Infra**: K3s 1.35 (3-master HA, embedded etcd), ArgoCD, Velero, Cloudflare Tunnel, Cloudflare R2, GitHub Actions, SOPS+age
- **Frontend**: Next.js 15, React 19, TypeScript, Tailwind, hls.js
- **DB**: PostgreSQL 17, Redis 7, MySQL 8, Apache Parquet
- **AI**: Spring AI, Gemini, RAG, Function Calling, KR-FinBERT (ONNX)
- **Monitoring**: Prometheus, Grafana, Micrometer

---

<!-- AUTO-UPDATE-START -->
*Last auto-update: 2026-05-27 (KST)* — public repos: **174**
<!-- AUTO-UPDATE-END -->

### 운영 중인 시스템

#### 🛒 도메인 사이트 (20+)

| 서비스 | URL | 설명 | 기술 |
|--------|-----|------|------|
| **Settlement MSA** | [jen.lemuel.co.kr](https://jen.lemuel.co.kr) | 이커머스 정산 플랫폼 (4모듈 MSA) | Spring Boot 4 + Kafka + ES |
| **ASAT** | [eln.lemuel.co.kr](https://eln.lemuel.co.kr) | 청각 재활 훈련 시스템 (K3s 5컴포넌트) | Spring Boot + Next.js + Postgres + Redis + MinIO |
| **AI 검색** | [chat.lemuel.co.kr](https://chat.lemuel.co.kr) | AI 상품 검색 (RAG + Agent) | Spring AI + Gemini + pgvector |
| **K-POP 굿즈** | [goods.lemuel.co.kr](https://goods.lemuel.co.kr) | 굿즈 뽑기 (해시 체인 투명성) | Spring Boot 4 + Toss Payments |
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
| **Grafana** | [grafana.lemuel.co.kr](https://grafana.lemuel.co.kr) | 서비스 모니터링 대시보드 | Grafana + Prometheus |

#### 🏛️ 통합 정량 인프라 — [lemuel-quant-core](https://github.com/MyoungSoo7/lemuel-quant-core)

9개 언어 ~5,500 lines. 6개 사이트(crypto/stock/dart/news/data/codingtest)의 데이터 수집·분석·시그널을 통합한 백엔드 코어.

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

📜 [구축기 블로그 포스트](/2026/05/07/lemuel-quant-core-build/)

> lemuel-academy(동영상 강의 플랫폼)는 진행 중인 작업이라 [/progress/](/progress/) 의 작업 로그로 이동했습니다.

---

### 인프라 — 온프레미스 K3s 클러스터 (5 노드, 100% 자체호스팅)

#### 노드 구성

| 서버 | 사양 | K3s 역할 | 주요 워크로드 |
|------|------|----------|--------------|
| **르무엘** | 4C / 32GB | control-plane, etcd | settlement, fashion, goods, ghost, news-pipeline, judge-engine (systemd) |
| **루이스** | i7-8565U / 16GB | worker | market-feed, orderbook-matcher (Rust), lqc-gateway (Go), dart-crawler |
| **데이비드** | 6C / 16GB / 218GB SSD | worker (모니터링) | kube-prometheus-stack, Loki, lemuel-explorer |
| **일원** | 12C / 14GB / 457GB NVMe + **4TB HDD** + **1TB SSD** | control-plane, etcd | postgres / storage 풀, ASAT, lowshopping, pharmacy |
| **솔로몬** | 저전력 소형 노드, **floating VIP** | control-plane, etcd | backup 전용 + etcd quorum |

총 ~40 vCPU / ~80GB RAM / 5.4TB+ 스토리지 (NVMe + HDD + SSD)

#### K3s 운영 방식

**3-master HA + embedded etcd** (2026-05-12 완료)
- SQLite → embedded etcd 인플레이스 마이그레이션 (18 분 다운타임으로 30+ ArgoCD 앱 모두 보존)
- RAFT 합의 (르무엘 / 일원 / 솔로몬 3 멤버 quorum), 1 노드 다운에도 control-plane 유지

**솔로몬 floating VIP** — 소형 노드 WiFi 안정성
- 3 WiFi NIC (내장 WiFi + USB 동글 2개), 30 줄 bash watchdog 가 활성 NIC 자동 결정
- keepalived 대신 단순 bash + systemd (단일 호스트 다중 NIC 시나리오엔 VRRP 부적합)
- 페일오버 시 gratuitous ARP 로 스위치 ARP table 즉시 갱신, K3s 통신 무중단

**외부 노출 — Cloudflare Tunnel**
- 외부에 직접 노출되는 포트 없음. cloudflared 가 클러스터 내부로만 트래픽 중계
- 15+ 외부 도메인 모두 lemuel.co.kr 산하 서브도메인
- Cloudflare Access (SSO + Zero Trust) 로 관리 페이지 보호

**GitOps — ArgoCD + Image Updater**
- Helm 차트 기반 30+ 앱 매니페스트가 GitHub repo 단일 진실
- 컨테이너 이미지 푸시 → ArgoCD Image Updater 가 차트 values 자동 갱신
- 시크릿은 SOPS + age 로 git 안에 암호화 보관 (5 머신 + Mac 모두 등록)

**백업 — Velero + Cloudflare R2**
- daily-with-volumes: 03:00 KST, 전체 ns, 30 일 TTL
- hourly-critical: 매시 정각, jen/asat/fashion/settlement/ghost/jabis/argocd, 7 일 TTL
- PV 데이터는 Kopia uploader (PodVolumeBackup), object lock 활성

**모니터링**
- **kube-prometheus-stack** (Prometheus + Grafana + Alertmanager + node-exporter, monitoring ns)
- **Loki** (로그 집중화, 데이비드 노드)
- **Blackbox Exporter** (HTTPS 도메인 외부 가용성)
- **ServerCheck 봇** (Mac 에서 5 분 cycle, SSH + HTTP 헬스체크, Telegram 알림)

**네트워크 / 보안**
- 호스트 방화벽 (ufw) 화이트리스트 정책 — K8s control plane / kubelet / flannel / etcd 트래픽은 내부 LAN 으로만 제한
- 모든 SSH 접속은 비표준 포트 + key-only
- 노드 간 트래픽은 모두 LAN, 외부 노출은 Cloudflare 단일 진입점 (Tunnel + Access)

#### 최근 운영 기록 (2026-05-12 일괄)

K3s 마이그레이션 / HA 전환 / WiFi 안정화 / 스토리지 통합 / SB4 의존성 디버깅 — 네 편 postmortem:

- [K3s 3-Master HA 마이그레이션 — SQLite → embedded etcd](/2026/05/12/k3s-3master-ha-sqlite-etcd-migration/)
- [K3s local-path-provisioner 에 4TB HDD 통합 — configmap 자동 복원 우회하기](/2026/05/12/k3s-local-path-storage-hdd-bind-mount/)
- [Spring Boot 4 의존성 지옥 디버깅 후기 — Spring AI / SpringDoc / classpath leakage](/2026/05/12/spring-boot-4-dependency-hell-debugging/)

---

### 링크
- **GitHub**: [MyoungSoo7](https://github.com/MyoungSoo7)
- **블로그**: [iamipro.tistory.com](https://iamipro.tistory.com)
- **Ghost 블로그**: [blog.lemuel.co.kr](https://blog.lemuel.co.kr)
- **포트폴리오**: [Notion](https://www.notion.so/a43ac75e1d964a01a6e8c679fbd70677)
