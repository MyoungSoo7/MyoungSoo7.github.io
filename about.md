---
layout: page
title: About
permalink: /about/
---

## 푸른영혼의 별 | AX Engineer · Agent Architect · Java Backend Engineer

공공·이커머스·금융 도메인의 시스템을 설계하고 운영하며, **안정성·정합성·변경 비용·검증 가능성**을 중심으로 문제를 해결합니다. Java/Spring 기반 백엔드와 K3s·GitOps 운영을 바탕으로, AI Agent·RAG·MCP·Ouroboros를 연결하는 재사용 가능한 Agent platform을 만들고 있습니다.

개별 기능을 빠르게 만드는 것보다 다음 질문을 중요하게 봅니다.

```text
무엇이 변하는가?
누가 소유하는가?
실패하면 어떻게 재처리하는가?
완료를 어떤 Trace로 증명하는가?
```

## 핵심 역량

### Backend & Architecture

- **Java/Kotlin**: Java 25, Kotlin 2.0, Spring Boot 4, Spring MVC, Spring AI, JPA/Hibernate
- **Architecture**: Hexagonal Architecture, DDD, MSA, Event-Driven Architecture, Outbox/Idempotency
- **Messaging & Data**: Apache Kafka, Redis, PostgreSQL, MySQL, Elasticsearch, Apache Parquet, gRPC
- **Frontend**: React 19, Next.js 16, Vue, TypeScript, Tailwind CSS
- **Legacy modernization**: JSP/Spring MVC 시스템과 React/Vue 기반 AX UI의 점진적 전환

### Agent & AI Engineering

- Hermes Agent orchestration·cron·memory·skill 운영
- Claude Code Telegram bots 1~4의 역할 분리·worktree·MCP 운영
- Codex 전문 reviewer·hook·Ouroboros worker 연계
- **Ouroboros v0.51.0**: run/evaluate/evolve/checkpoint/receipt/convergence
- MCP·RAG·Function Calling·Agent tool contract·evaluation harness
- Hidden Checklist·Evaluator 분리·TraceGuard 기반 완료 판정
- Script·Tool·Skill provenance registry 및 artifact lifecycle 관리

### Infrastructure & Operations

- **K3s 1.35**: 3-master HA, embedded etcd, 6-node homelab
- ArgoCD App-of-Apps, GitOps, Velero, Cloudflare Tunnel/R2
- SOPS+age, GitHub Actions, Prometheus, Grafana, Micrometer, Loki
- 최근 24시간 lookback 기반 RCA, 현재/과거/정리 후보 분리
- 업무 데이터의 source count·upsert count·last non-zero success 검증

## 운영 중인 시스템

### 포트폴리오·도메인 서비스

| 서비스             | URL                                                        | 설명                           | 기술                                               |
| ------------------ | ---------------------------------------------------------- | ------------------------------ | -------------------------------------------------- |
| **Settlement MSA** | [jen.lemuel.co.kr](https://jen.lemuel.co.kr)               | 이커머스 주문·결제·정산 플랫폼 | Spring Boot 4 + Kafka + Elasticsearch              |
| **ASAT**           | [eln.lemuel.co.kr](https://eln.lemuel.co.kr)               | 청각 재활 훈련 시스템          | Spring Boot + Next.js + PostgreSQL + Redis + MinIO |
| **Lemuel-XR**      | [xr.lemuel.co.kr](https://xr.lemuel.co.kr)                 | XR·묵상 가이드 서비스          | Spring Boot + Next.js + PostgreSQL + pgvector      |
| **SNS**            | [sns.lemuel.co.kr](https://sns.lemuel.co.kr)               | Kafka·SSE 기반 실시간 피드     | Spring Boot 4 + Kafka                              |
| **Coding Test**    | [codingtest.lemuel.co.kr](https://codingtest.lemuel.co.kr) | 코딩테스트 학습 앱             | Spring Boot 4 + H2                                 |
| **SQL Learning**   | [database.lemuel.co.kr](https://database.lemuel.co.kr)     | SQL 코딩테스트 연습            | Spring Boot 4 + MySQL                              |
| **Media Search**   | [media.lemuel.co.kr](https://media.lemuel.co.kr)           | 이미지·동영상 검색             | Spring Boot + Pexels API                           |
| **Auto Trading**   | [stock.lemuel.co.kr](https://stock.lemuel.co.kr)           | KIS API 기반 자동매매 실험     | Spring Boot + PostgreSQL                           |
| **Crypto Trading** | [crypto.lemuel.co.kr](https://crypto.lemuel.co.kr)         | 암호화폐 자동매매 실험         | Spring Boot + Bithumb API                          |
| **DART Analysis**  | [dart.lemuel.co.kr](https://dart.lemuel.co.kr)             | 공시 수집·NER·감성분석         | C++ crawler + PostgreSQL + KR-FinBERT              |

### Self-hosted·생산성

| 서비스          | URL                                                | 설명                           |
| --------------- | -------------------------------------------------- | ------------------------------ |
| **Vaultwarden** | [vault.lemuel.co.kr](https://vault.lemuel.co.kr)   | Bitwarden 호환 비밀번호 관리자 |
| **Memos**       | [memo.lemuel.co.kr](https://memo.lemuel.co.kr)     | 개인 마이크로블로그            |
| **Linkding**    | [links.lemuel.co.kr](https://links.lemuel.co.kr)   | 북마크 관리자                  |
| **SearXNG**     | [search.lemuel.co.kr](https://search.lemuel.co.kr) | 프라이버시 메타 검색           |
| **Immich**      | [photos.lemuel.co.kr](https://photos.lemuel.co.kr) | 사진 관리·자동 백업            |
| **n8n**         | [n8n.lemuel.co.kr](https://n8n.lemuel.co.kr)       | 워크플로 자동화                |
| **Uptime Kuma** | 내부                                               | 외부 가용성 모니터링           |

### 인프라·운영

| 서비스                   | URL                                                  | 설명                        |
| ------------------------ | ---------------------------------------------------- | --------------------------- |
| **Kubernetes Dashboard** | [k8s.lemuel.co.kr](https://k8s.lemuel.co.kr)         | K3s 클러스터 관리           |
| **Homelab Dashboard**    | [k3s.lemuel.co.kr](https://k3s.lemuel.co.kr)         | 자체 제작 K3s 운영 대시보드 |
| **Grafana**              | [grafana.lemuel.co.kr](https://grafana.lemuel.co.kr) | Prometheus 기반 모니터링    |
| **LiteLLM Gateway**      | intelligence.lemuel.co.kr (인증 필요)                | LLM 라우팅·비용 게이트웨이  |
| **Landing**              | [lemuel.co.kr](https://lemuel.co.kr)                 | 포트폴리오 랜딩             |

모든 서비스는 6-node K3s 클러스터와 Cloudflare Tunnel을 기반으로 운영하며, ArgoCD·SOPS+age·Velero·Prometheus/Grafana/Loki를 사용합니다.

## 주요 설계 주제

- [Apache Kafka 핵심 개념과 운영 체크리스트](https://myoungsoo7.github.io/2026/08/10/apache-kafka-core-concepts-and-production-checklist/)
- [Kafka 기반 MSA와 은행 EAI 비교](https://myoungsoo7.github.io/2026/08/10/kafka-vs-bank-eai-msa-integration/)
- [React·Vue·JSP와 AX 시대의 프론트엔드 선택](https://myoungsoo7.github.io/2026/08/09/react-vue-jsp-ax-comparison/)
- [Java/Spring 확장성과 추상화](https://myoungsoo7.github.io/2026/08/09/scalability-abstraction-interview/)
- [주문·결제·정산 흐름](https://myoungsoo7.github.io/2026/08/09/settlement-order-payment-flow/)
- [계정계 확장: 예금·적금·연금 설계](https://myoungsoo7.github.io/2026/08/09/settlement-account-service-banking-expansion/)

## 정량 인프라·데이터 파이프라인

lemuel-quant-core는 C++·Rust·Go·Julia·R·Python을 활용해 시장 데이터·공시·뉴스·분석·백테스트를 연결하는 실험용 데이터 코어입니다.

```text
C++:
  market-feed·stock-feed·dart-crawler·news-pipeline·data-warehouse

Rust:
  orderbook-matcher

Go:
  lqc-gateway·metrics·SSE bridge

Julia/R/Python:
  최적화·시계열 분석·백테스트·전략 실험
```

실제 구현·실행·운영 상태와 설계 제안은 구분해 기록합니다. 측정되지 않은 성능·비용·트래픽·업타임은 주장하지 않습니다.

## 링크

- **GitHub**: [MyoungSoo7](https://github.com/MyoungSoo7)
- **기술 블로그**: [MyoungSoo7.github.io](https://myoungsoo7.github.io/)
- **Ghost Blog**: [blog.lemuel.co.kr](https://blog.lemuel.co.kr)
- **Portfolio**: [Notion](https://www.notion.so/a43ac75e1d964a01a6e8c679fbd70677)

_이 페이지는 2026-08-12 기준으로 갱신했습니다. 목록의 모든 도메인은 이 날짜에 HTTP 응답과 클러스터 워크로드를 함께 확인해 살아 있는 것만 남겼고, 반대로 클러스터에서 돌고 있으나 누락돼 있던 항목도 같은 기준으로 채웠습니다. 서비스·기술 버전·운영 상태는 변경될 수 있으며, 실제 구현·운영·설계 상태를 구분해 설명합니다._

_공개 페이지에는 credential, token, private IP, 내부 endpoint를 포함하지 않습니다._
