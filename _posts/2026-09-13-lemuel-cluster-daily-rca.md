---
layout: post
title: "르무엘 클러스터 일일 RCA 리포트 (2026-09-13)"
date: 2026-09-13 09:00:00 +0900
categories: [DevOps, K3s]
tags: [k3s, rca, cloudflared, kafka, monitoring]
---

## 1. 개요
본 리포트는 `k8s-rca-daily.sh`가 수집한 2026-09-12~13 기간의 Trace를 바탕으로 르무엘 클러스터의 상태를 분석한 결과입니다.

## 2. 주요 장애 및 특이사항 (Critical Incidents)

### 2.1. 네트워크 및 터널 연결 중단 (2026-09-12 07:56 - 08:15 UTC)
*   **현상**: `cloudflared-louise` (Node: david)의 터널 연결이 반복적으로 끊어지고 재시도됨.
*   **근거**:
    *   `ERR failed to accept QUIC stream: timeout: no recent network activity`
    *   `Unable to reach the origin service... connect: connection refused`
*   **영향 범위**: `photos.lemuel.co.kr`, `memo.lemuel.co.kr`, `sns.lemuel.co.kr`, `blog.lemuel.co.kr`, `media.lemuel.co.kr` 등 다수 서비스의 외부 접근 불가.
*   **분석**: 해당 시간대 노드 `david` 또는 클러스터 외부 망의 불안정성으로 인해 Cloudflare Edge와의 QUIC 연결이 타임아웃된 것으로 판단됨.

### 2.2. Kafka 클러스터 통신 지연
*   **현상**: `lemuel-entity-operator`가 Kafka bootstrap 서버에 접속하지 못해 타임아웃 발생.
*   **근거**: `org.apache.kafka.common.errors.TimeoutException: Timed out waiting to send the call. Call: fetchMetadata` (08:11 UTC).
*   **분석**: 2.1항의 네트워크 불안정 시간대와 일치하며, 노드 간 내부 통신(Internal IP)에도 영향을 미쳤을 가능성이 있음.

## 3. 관측 도구 및 에이전트 상태 (Monitoring & Agent Health)

### 3.1. Kubelet 통신 장애 (Log Collection Failure)
*   **현상**: 특정 노드의 로그 수집 시 `TLS handshake timeout` 또는 `EOF` 발생.
*   **대상 노드**: `louise` (192.168.219.111), `isagal` (192.168.219.119)
*   **근거**: RCA 스크립트 실행 중 `elastic-operator`, `immich-server`, `litellm`, `strimzi-cluster-operator` 로그 수집 실패.
*   **분석**: Kubelet(10250) 응답 지연으로, 노드 부하 또는 네트워크 혼잡이 원인일 수 있음.

### 3.2. Memory-QA 서비스 Broken Pipe
*   **현상**: `memory-qa` (Node: solomon) 컨테이너 로그에서 빈번한 `BrokenPipeError` 발생.
*   **근거**: `BrokenPipeError: [Errno 32] Broken pipe` (18:47 - 00:01 UTC 구간 집중).
*   **분석**: 클라이언트 측에서 응답을 기다리지 않고 연결을 끊었음을 의미하며, LLM 응답 지연으로 인한 타임아웃 가능성이 높음.

## 4. 작업 및 파드 상태 요약

| Namespace | Pod / Job Name | Status | Error Detail |
| :--- | :--- | :--- | :--- |
| settlement-prod | settlement-company-reputation | Error | 29820840-stg72, 29820840-tllzz 실패 |
| velero | argocd-default-kopia-maintain | Error | Maintain-job 실패 |
| agent-system | memory-qa | Running | BrokenPipeError 다수 발생 |

## 5. 결론 및 권고 사항
1.  **네트워크 점검**: 08:00 UTC 전후의 `david` 노드 및 외부 회선 로그 확인 필요.
2.  **노드 자원 검토**: `louise`와 `isagal` 노드의 Kubelet 응답 지연 원인 파악 (CPU/IO wait 등).
3.  **작업 재실행**: 실패한 `settlement-prod` 배치 작업의 재실행 및 세부 로그(파드 내부) 확인 권고.

---
*본 리포트는 Hermes Agent에 의해 자동 생성되었습니다.*
