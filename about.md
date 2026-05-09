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
- **Infra**: Docker, K3s, Cloudflare Tunnel, Cloudflare R2, GitHub Actions, AWS Lightsail
- **Frontend**: Next.js 15, React 19, TypeScript, Tailwind, hls.js
- **DB**: PostgreSQL 17, Redis 7, MySQL 8, Apache Parquet
- **AI**: Spring AI, Gemini, RAG, Function Calling, KR-FinBERT (ONNX)
- **Monitoring**: Prometheus, Grafana, Micrometer

---

<!-- AUTO-UPDATE-START -->
*Last auto-update: 2026-05-09 (KST)* — public repos: **176**

#### 🔥 최근 푸시한 레포 5

| 레포 | 언어 | 마지막 푸시 | 설명 |
|------|------|-------------|------|
| [lemuel-quant-core](https://github.com/MyoungSoo7/lemuel-quant-core) | C++ | 2026-05-08 | 고성능 C++ 시장 데이터 파이프라인 + 채점 엔진. crypto/stock/dart/news/data/codingtest 사이트와 통합되는 lemuel 인프라 코어. |
| [lemuel-academy](https://github.com/MyoungSoo7/lemuel-academy) | Kotlin | 2026-05-08 | 동영상 강의 플랫폼 — 크리에이터/학생/관리자 MSA. ffmpeg HLS 트랜스코딩 + R2 저장 + Spring Boot Kotlin + Next.js. Class101/탈잉 스타일. |
| [settlement](https://github.com/MyoungSoo7/settlement) | Java | 2026-05-08 | 주문·결제·정산·승인 시스템(헥사고날아키텍처, 자바, 스프링부트, k8s, prometheus, elasticsearch,  postgresql) |
| [MyoungSoo7.github.io](https://github.com/MyoungSoo7/MyoungSoo7.github.io) | HTML | 2026-05-08 |  |
| [MyoungSoo7](https://github.com/MyoungSoo7/MyoungSoo7) |  | 2026-05-07 |  |

<!-- AUTO-UPDATE-END -->

### 운영 중인 시스템

#### 🛒 도메인 사이트 (20+)

| 서비스 | URL | 설명 | 기술 |
|--------|-----|------|------|
| **Settlement MSA** | [jen.lemuel.co.kr](https://jen.lemuel.co.kr) | 이커머스 정산 플랫폼 (4모듈 MSA) | Spring Boot 4 + Kafka + ES |
| **ASAT** | [eln.lemuel.co.kr](https://eln.lemuel.co.kr) | 청각 재활 훈련 시스템 | Spring Boot 4 + Web Audio API |
| **ASAT K3s** | [asat.lemuel.co.kr](https://asat.lemuel.co.kr) | ASAT K3s 이중화 배포 | K3s 2노드 클러스터 |
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
| **Serverless** | [serveless.lemuel.co.kr](https://serveless.lemuel.co.kr) | 환율/주가 API | Micronaut 4 + GraalVM |
| **Media Search** | [media.lemuel.co.kr](https://media.lemuel.co.kr) | 무료 이미지/동영상 검색 | Spring Boot 4 + Pexels API |
| **Auto Trading** | [stock.lemuel.co.kr](https://stock.lemuel.co.kr) | 자동 주식매매 (KIS API) | Spring Boot 4 + PostgreSQL |
| **Crypto Trading** | [crypto.lemuel.co.kr](https://crypto.lemuel.co.kr) | 빗썸 암호화폐 자동매매 | Spring Boot 4 + Bithumb API |
| **K8s Dashboard** | [k8s.lemuel.co.kr](https://k8s.lemuel.co.kr) | Kubernetes 클러스터 관리 | K3s + Dashboard v2.7 |
| **Grafana** | [grafana.lemuel.co.kr](https://grafana.lemuel.co.kr) | 서비스 모니터링 대시보드 | Grafana + Prometheus |

#### 🏛️ 통합 정량 인프라 — [lemuel-quant-core](https://github.com/MyoungSoo7/lemuel-quant-core)

9개 언어 ~5,500 lines. 6개 사이트(crypto/stock/dart/news/data/codingtest)의 데이터 수집·분석·시그널을 통합한 백엔드 코어.

| 모듈 | 언어 | 서버 | 역할 |
|------|------|------|------|
| judge-engine | C++20 + gRPC | 르무엘클라우드 | seccomp+cgroup 샌드박스 코드 채점 |
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

#### 🎬 동영상 강의 플랫폼 — [lemuel-academy](https://github.com/MyoungSoo7/lemuel-academy)

Class101/탈잉 스타일 MSA. Spring Boot 4 Kotlin × 4 + Next.js 15 × 3 + ffmpeg HLS 트랜스코딩.

| 서비스 | 역할 |
|--------|------|
| user-service | JWT 인증 + 진도 + 즐겨찾기 |
| catalog-service | 강의/챕터/레슨/리뷰 + 검수 워크플로 |
| media-service + ffmpeg-worker | R2 업로드 → HLS 1080p/720p/480p |
| api-gateway | Spring Cloud Gateway + JwtFilter |
| learner / creator-studio / admin | Next.js 3개 (Tailwind + hls.js) |

---

### 인프라

3대 서버 (홈 2 + AWS Lightsail) + K3s 클러스터.

| 서버 | 사양 | 역할 |
|------|------|------|
| 르무엘 | i7-6500U / 32GB / 400GB | K3s 마스터, ASAT, 약국, 쇼핑, RealGrid, news-pipeline, data-warehouse, Shiny |
| 루이스 | i7-8565U / 16GB / 98GB | K3s 워커, Settlement, 굿즈, 패션, 라이브, SNS, market-feed, dart-crawler, Rust orderbook-matcher, Go gateway |
| 르무엘클라우드 | AWS Lightsail 2C/4G | codingtest, media, database, judge-engine gRPC |

- **네트워크**: Cloudflare Tunnel 3개 → 외부 포트 0개로 HTTPS 제공
- **컨테이너**: Docker 40+ 컨테이너
- **K3s**: ASAT 이중화 (backend 2 + frontend 2)
- **모니터링**: Uptime Kuma + Grafana + Prometheus + 텔레그램 알림
- **백업**: 매일 04:00 DB 자동 백업 → Cloudflare R2 (7일 보관)
- **시세 백업**: 5분 주기 Parquet rollup → R2 lemuel-backup/snapshots/

---

### 링크
- **GitHub**: [MyoungSoo7](https://github.com/MyoungSoo7)
- **블로그**: [iamipro.tistory.com](https://iamipro.tistory.com)
- **Ghost 블로그**: [blog.lemuel.co.kr](https://blog.lemuel.co.kr)
- **포트폴리오**: [Notion](https://www.notion.so/a43ac75e1d964a01a6e8c679fbd70677)
