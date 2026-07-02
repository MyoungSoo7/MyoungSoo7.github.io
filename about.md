---
layout: page
title: About
permalink: /about/
---

## 푸른영혼의 별 | Java Backend Engineer

공공·이커머스 환경에서 운영 중인 시스템의 *안정성* 과 *변경 비용* 을 기준으로 구조를 설계해온 백엔드 엔지니어. 9년차.

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

### 운영 중인 시스템

#### 🛒 포트폴리오 / 도메인 사이트

| 서비스 | URL | 설명 | 기술 |
|--------|-----|------|------|
| **Settlement MSA** | [jen.lemuel.co.kr](https://jen.lemuel.co.kr) | 이커머스 정산 플랫폼 (4모듈 MSA, **HA 3 replica**) | Spring Boot 4 + Kafka + ES |
| **ASAT** | [eln.lemuel.co.kr](https://eln.lemuel.co.kr) | 청각 재활 훈련 시스템 (K3s 5컴포넌트) | Spring Boot + Next.js + Postgres + Redis + MinIO |
| **Sparta MSA (AI 검색)** | [chat.lemuel.co.kr](https://chat.lemuel.co.kr) | Spring Cloud Gateway + AI 챗봇 (**HA 3 replica**) | Spring AI + Gemini + pgvector |
| **lemuel-xr** | [xr.lemuel.co.kr](https://xr.lemuel.co.kr) | XR / 묵상 가이드 (트랙 B 인물 미션) | Spring Boot + Next.js + PostgreSQL + pgvector |
| **K-POP 굿즈** | [goods.lemuel.co.kr](https://goods.lemuel.co.kr) | 굿즈 뽑기 (*데모 — 익명 가챠 모드*) | Spring Boot 4 + Next.js 16 |
| **SNS** | [sns.lemuel.co.kr](https://sns.lemuel.co.kr) | SNS 피드 (Kafka + SSE 실시간 알림) | Spring Boot 4 + Kafka |
| **약국 추천** | [pharmacy.lemuel.co.kr](https://pharmacy.lemuel.co.kr) | 위치 기반 약국 추천 | Spring Boot 4 + Redis + 카카오 API |
| **최저가 쇼핑** | [lowshopping.lemuel.co.kr](https://lowshopping.lemuel.co.kr) | 네이버 쇼핑 최저가 비교 | Spring Boot 4 + Thymeleaf |
| **코딩테스트** | [codingtest.lemuel.co.kr](https://codingtest.lemuel.co.kr) | 100문제 학습 앱 | Spring Boot 4 + H2 |
| **SQL 학습** | [database.lemuel.co.kr](https://database.lemuel.co.kr) | SQL 코딩 테스트 연습 | Spring Boot 4 + MySQL |
| **Media Search** | [media.lemuel.co.kr](https://media.lemuel.co.kr) | 무료 이미지/동영상 검색 | Spring Boot 4 + Pexels API |
| **Auto Trading** | [stock.lemuel.co.kr](https://stock.lemuel.co.kr) | 자동 주식매매 (KIS API) | Spring Boot 4 + PostgreSQL |
| **Crypto Trading** | [crypto.lemuel.co.kr](https://crypto.lemuel.co.kr) | 빗썸 암호화폐 자동매매 | Spring Boot 4 + Bithumb API |
| **DART 공시** | [dart.lemuel.co.kr](https://dart.lemuel.co.kr) | 공시 공시 추적 + NER 감성분석 | Spring Boot + C++ crawler + KR-FinBERT |
| **Burger Display Order** | [qr.lemuel.co.kr](https://qr.lemuel.co.kr) | 매장 키오스크 주문 디스플레이 (QR 결제) | React 18 + Vite + TossPayments + nginx |
| **Ghost CMS Blog** | [blog.lemuel.co.kr](https://blog.lemuel.co.kr) | 일반 글 / 본질 / 회고 (Admin API 자동 게시) | Ghost 5.130 + SQLite |

#### 🚚 물류 / 미들오피스

| 서비스 | URL | 설명 | 기술 |
|--------|-----|------|------|
| **LMS (물류 관리)** | [lms.lemuel.co.kr](https://lms.lemuel.co.kr) | 물류 운영 / 배송 관리 시스템 | Spring Boot Kotlin + PostgreSQL |
| **OMS (주문 관리)** | [oms.lemuel.co.kr](https://oms.lemuel.co.kr) | 통합 주문 관리 | Spring Boot Kotlin + Kafka |
| **WMS (창고 관리)** | [wms.lemuel.co.kr](https://wms.lemuel.co.kr) | 창고 / 재고 / 입출고 관리 | Spring Boot Kotlin + PostgreSQL |
| **Logistic Admin / Robot** | (내부) | 물류 어드민 + 로봇 콘솔 (event/route/task/monitoring) | Spring Boot + MQTT + Kafka |
| **Logistics 통합 대시보드** | (내부) | 7 마이크로서비스 통합 모니터링 | Spring Boot + Grafana |

#### 🛠 셀프호스팅 / 개인 productivity (2026-06-21 추가)

| 서비스 | URL | 설명 | 비고 |
|--------|-----|------|------|
| **Vaultwarden** | [vault.lemuel.co.kr](https://vault.lemuel.co.kr) | Bitwarden 호환 비밀번호 매니저 | 자체 차트, SOPS+age, ADMIN_TOKEN 보호 |
| **Memos** | [memo.lemuel.co.kr](https://memo.lemuel.co.kr) | Twitter-like 개인 마이크로블로그 | 시니어 의 생각 흐름 일지 |
| **Linkding** | [links.lemuel.co.kr](https://links.lemuel.co.kr) | 셀프호스팅 북마크 매니저 | Ghost 와 짝 — 블로그 자료 모음 |
| **SearXNG** | [search.lemuel.co.kr](https://search.lemuel.co.kr) | 프라이버시 메타 검색 엔진 | Valkey sidecar, secret_key SOPS |
| **Immich** | [photos.lemuel.co.kr](https://photos.lemuel.co.kr) | Google Photos 대체 (AI 얼굴 인식 + 자동 백업) | postgres+pgvector + Redis + ML (4 component 자체 차트) |
| **Uptime Kuma** | (내부) | 외부 가용성 모니터 | Self-host status page |

#### 🔧 인프라 / 운영

| 서비스 | URL | 설명 | 기술 |
|--------|-----|------|------|
| **K8s Dashboard** | [k8s.lemuel.co.kr](https://k8s.lemuel.co.kr) | Kubernetes 클러스터 관리 | K3s + Dashboard v2.7 |
| **Homelab Dashboard** | [k3s.lemuel.co.kr](https://k3s.lemuel.co.kr) | 자체 제작 K3s 운영 대시보드 | Spring Boot 3 + Thymeleaf + K8s Java client 24 + JSch |
| **frp Self-Hosted Tunnel** | [frp.lemuel.co.kr](https://frp.lemuel.co.kr) | Cloudflare Tunnel 의 *self-host 카운터파트* | Fast Reverse Proxy + Helm + ArgoCD |
| **Grafana** | [grafana.lemuel.co.kr](https://grafana.lemuel.co.kr) | 서비스 모니터링 대시보드 | Grafana + Prometheus |
| **Landing** | [lemuel.co.kr](https://lemuel.co.kr) | 도메인 메인 / 포트폴리오 랜딩 | static + Cloudflare |

**총 33+ 도메인** — 모두 6 노드 K3s 클러스터 + Cloudflare Tunnel 의 *단일 외부 진입점* 으로 운영. ArgoCD App-of-Apps + SOPS+age (시크릿) + Velero (백업, daily/hourly + R2) + Prometheus/Grafana/Loki (관측).

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

---

### 링크
- **GitHub**: [MyoungSoo7](https://github.com/MyoungSoo7)
- **블로그**: [iamipro.tistory.com](https://iamipro.tistory.com)
- **Ghost 블로그**: [blog.lemuel.co.kr](https://blog.lemuel.co.kr)  
- **포트폴리오**: [Notion](https://www.notion.so/a43ac75e1d964a01a6e8c679fbd70677)
