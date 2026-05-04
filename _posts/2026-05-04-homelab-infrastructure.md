---
layout: post
title: "홈서버 2대 + K3s로 15개 서비스 운영하기"
date: 2026-05-04 02:00:00 +0900
categories: [infra, devops]
tags: [docker, k3s, cloudflare-tunnel, homelab]
---

## 인프라 구성

2대의 중고 노트북으로 15개 서비스를 운영하고 있습니다.

### 서버 사양

| 서버 | CPU | RAM | 디스크 | 역할 |
|------|-----|-----|--------|------|
| 르무엘 | i7-6500U | 32GB | 400GB | K3s 마스터, ASAT, 약국추천, 쇼핑 |
| 루이스 | i7-8565U | 16GB | 98GB | K3s 워커, Settlement, 굿즈, 패션, AI검색 등 |

### Cloudflare Tunnel

외부 포트를 하나도 개방하지 않고 HTTPS 서비스를 제공합니다.

```
인터넷 → Cloudflare Edge → Tunnel → 홈서버 nginx → Docker 컨테이너
```

- 터널 2개: lemuel-home, louise-home
- 도메인: *.lemuel.co.kr (15개 서브도메인)
- SSL 인증서: Cloudflare 자동 관리

### K3s 클러스터

ASAT 프로젝트를 K3s로 이중화 운영합니다:
- 마스터: 르무엘
- 워커: 루이스
- Backend Pod 2개 + Frontend Pod 2개 (양쪽 노드 분배)

### 자동화

- **DB 백업**: 매일 04:00 크론 (7일 보관)
- **Playwright 사이트 점검**: 매일 아침 15개 도메인 자동 테스트
- **Uptime Kuma**: 서비스 모니터링 + 텔레그램 알림

### 운영 중인 서비스 (15개)

| 서비스 | URL | 기술 |
|--------|-----|------|
| ASAT | eln.lemuel.co.kr | Spring Boot 4 + Web Audio |
| Settlement | jen.lemuel.co.kr | Spring Boot 4 + Kafka + ES |
| AI 검색 | chat.lemuel.co.kr | Spring AI + Gemini |
| 굿즈 뽑기 | goods.lemuel.co.kr | Spring Boot 4 + Toss |
| 패션 매칭 | fashion.lemuel.co.kr | Spring Boot 4 + AI |
| 라이브커머스 | live.lemuel.co.kr | Spring Boot 4 + React |
| SNS | sns.lemuel.co.kr | Spring Boot 4 + Kafka |
| 약국 추천 | pharmacy.lemuel.co.kr | Spring Boot 4 + Redis |
| 최저가 쇼핑 | lowshopping.lemuel.co.kr | Spring Boot 4 |
| 코딩테스트 | codingtest.lemuel.co.kr | Spring Boot 4 + H2 |
| DB 학습 | database.lemuel.co.kr | Spring Boot 4 + MySQL |
| RealGrid | realgrid.lemuel.co.kr | Spring Boot 4 + React |
| AI 비서 | jabis.lemuel.co.kr | Spring Boot 4 + AI |
| Serverless | serveless.lemuel.co.kr | Micronaut 4 |
| ASAT K3s | asat.lemuel.co.kr | K3s 이중화 |

Docker 35+ 컨테이너, Cloudflare Tunnel 2개, K3s 2노드 클러스터로 **외부 포트 0개**로 운영 중입니다.
