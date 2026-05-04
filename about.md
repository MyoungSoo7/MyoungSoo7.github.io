---
layout: page
title: About
permalink: /about/
---

## 푸른영혼의 별 | Java Backend Engineer

공공·이커머스 환경에서 운영 중인 시스템의 안정성과 변경 비용을 기준으로 구조를 설계해온 백엔드 엔지니어입니다.

### 기술 스택
- **Backend**: Java 25, Spring Boot 4, JPA/Hibernate, Kafka, Elasticsearch
- **Architecture**: Hexagonal, MSA, Event-Driven, DDD
- **Infra**: Docker, K3s, Cloudflare Tunnel, GitHub Actions
- **Frontend**: Next.js, React, TypeScript
- **DB**: PostgreSQL, Redis, MySQL
- **AI**: Spring AI, Gemini, RAG, Function Calling
- **Monitoring**: Prometheus, Grafana, Micrometer

---

### 운영 중인 서비스 (20개)

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

---

### 인프라

2대 홈서버 + K3s 클러스터로 운영 중

| 서버 | 사양 | 역할 |
|------|------|------|
| 르무엘 | i7-6500U / 32GB / 400GB | K3s 마스터, ASAT, 약국추천, 최저가쇼핑, RealGrid, Report |
| 루이스 | i7-8565U / 16GB / 98GB | K3s 워커, Settlement, 굿즈, 패션, 라이브, SNS, AI검색, AI비서, 코딩테스트, DB학습, Serverless |

- **네트워크**: Cloudflare Tunnel 2개 → 외부 포트 0개로 HTTPS 제공
- **컨테이너**: Docker 35+ 컨테이너
- **K3s**: ASAT 이중화 (backend 2 + frontend 2)
- **모니터링**: Uptime Kuma + 텔레그램 알림 + Playwright 자동 점검
- **백업**: 매일 04:00 DB 자동 백업 (7일 보관)

---

### 링크
- **GitHub**: [MyoungSoo7](https://github.com/MyoungSoo7)
- **블로그**: [iamipro.tistory.com](https://iamipro.tistory.com)
- **Ghost 블로그**: [blog.lemuel.co.kr](https://blog.lemuel.co.kr)
- **포트폴리오**: [Notion](https://www.notion.so/a43ac75e1d964a01a6e8c679fbd70677)
