---
layout: post
title: "AWS Lightsail로 서비스 이전 — 3대 서버 인프라 확장"
date: 2026-05-06 10:00:00 +0900
categories: [infra, devops]
tags: [aws, lightsail, docker, cloudflare-tunnel, migration]
---

## 왜 확장?

루이스 서버(16GB)에 51개 컨테이너가 돌면서 메모리 66% 사용. 서비스 추가 시 한계.

## AWS Lightsail 선택

- **$24/월** (서울 리전, 2코어/4GB/80GB)
- EC2 대비 고정 요금 + 전송량 포함
- 5분 만에 생성, SSH 바로 접속

## 이전 대상

루이스에서 경량 서비스 3개를 AWS로 이전:
- **codingtest** — H2 DB, 가벼움
- **media-search** — Pexels API, 상태 없음
- **database** — SQL 학습용

## 인프라 현황 (3대 서버)

| 서버 | 위치 | 스펙 | 역할 |
|------|------|------|------|
| 르무엘 | 집 | i7/32GB | K3s 마스터, ASAT, DART 등 |
| 루이스 | 집 | i7/16GB | K3s 워커, Settlement, 트레이딩 등 |
| AWS | 서울 | 2c/4GB | codingtest, media, database |

모두 Cloudflare Tunnel로 외부 포트 0개 운영.

**GitHub Pages**: [MyoungSoo7.github.io](https://MyoungSoo7.github.io)
