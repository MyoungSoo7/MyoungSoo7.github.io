---
layout: post
title: "K3s Dashboard + Grafana 모니터링 — 실제 클러스터 운영 현황 시각화"
date: 2026-05-03 21:00:00 +0900
categories: [infra, monitoring]
tags: [kubernetes, k3s, grafana, prometheus, dashboard]
---

## K3s Kubernetes Dashboard

실제 운영 중인 K3s 클러스터에 Kubernetes Dashboard를 설치하여 Pod, Deployment, Service 상태를 웹에서 관리합니다.

**Live**: [k8s.lemuel.co.kr](https://k8s.lemuel.co.kr)

### 구성

- K3s 2노드 클러스터 (르무엘 마스터 + 루이스 워커)
- Kubernetes Dashboard v2.7 (NodePort → nginx 프록시)
- admin-user ServiceAccount + ClusterRoleBinding
- Token 기반 인증

## Grafana + Prometheus 모니터링

**Live**: [grafana.lemuel.co.kr](https://grafana.lemuel.co.kr)

### 구성

- Prometheus: 메트릭 수집 (Spring Boot Actuator `/actuator/prometheus`)
- Grafana: 시각화 대시보드 (CPU, 메모리, 요청 수, 응답 시간)
- 30초 주기 스크래핑

### 모니터링 대상

- Settlement MSA (order-service, settlement-service)
- 코딩테스트 앱
- Prometheus 자체 메트릭

## 기술 스택

Kubernetes Dashboard v2.7 / Grafana / Prometheus / Docker / K3s
