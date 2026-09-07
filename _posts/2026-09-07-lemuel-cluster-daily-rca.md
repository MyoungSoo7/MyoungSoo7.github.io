---
layout: post
title: "[Daily RCA] 르무엘 클러스터 관리 레이어와 로그 파이프라인 점검"
date: 2026-09-07 16:35:40 +0900
categories: [Kubernetes, SRE]
tags: [Kubernetes, K3s, RCA, ECK, Elasticsearch, Logstash, Gemini, Observability]
---

# 르무엘 클러스터 일일 RCA

> 본 문서는 2026-09-07 전달된 `르무엘 클러스터 매일 RCA` Cron 응답과 그 안에 포함된 실제 Trace를 정리한 운영 기록이다. 원인과 영향은 제공된 Trace 범위 안에서만 판단했으며, 별도 재검증하지 못한 항목은 미확인으로 남긴다.

## 요약

클러스터의 핵심 파드는 Running 상태를 유지하고 있어 로그 수집·조회 서비스의 현재 가용성은 유지된 것으로 보고되었다. 그러나 관리 레이어의 누적 재시작, Logstash 매핑 충돌, 사용 중인 Gemini 모델의 404, DNS 설정 경고가 동시에 관측되었다.

따라서 이번 상태는 **서비스 가용성 유지와 운영 위험 누적이 공존하는 상태**로 분류한다. 현재 서비스가 응답한다는 사실만으로 관리 레이어와 데이터 처리 파이프라인이 건강하다고 판단해서는 안 된다.

## 1. ECK Operator 재시작과 리더 선출 실패

`elastic-system/elastic-operator-0` 파드는 총 92회 재시작된 것으로 보고되었다. 이전 로그에는 다음 Trace가 포함되어 있다.

```text
2026-09-06T09:29:09Z
context deadline exceeded
leader election lost
```

제공된 분석에 따르면 Kubernetes API와의 통신 지연으로 Lease 갱신이 실패했고, 그 결과 leader election을 잃은 뒤 프로세스가 종료되었다.

### 판정

- 분류: 만성 위험
- 영향도: 높음
- 현재 영향: 제공된 현재 상태에서는 핵심 로그 스택 파드가 Running
- 미확인: 재시작 92회의 전체 원인별 분포와 현재 시점의 재발 여부

ECK Operator 재시작이 곧바로 Elasticsearch 데이터 손실을 의미하는 것은 아니다. 다만 reconciliation과 관리 작업이 반복적으로 중단되면 Elasticsearch·Kibana·Logstash 구성 변경이나 복구 작업이 지연될 수 있다.

## 2. Logstash 매핑 충돌

`logging/logs-ls-0`에서 Elasticsearch 인덱싱 HTTP 400 오류가 다수 발생한 것으로 보고되었다.

확인된 예시는 다음과 같다.

```text
mapper [data.result.value] cannot be changed from type [float] to [text]

failed to parse field [error]
Expected text but found START_OBJECT
```

첫 번째 오류는 동일 필드에 숫자와 문자열이 서로 다른 타입으로 유입된 상황을 가리킨다. 두 번째 오류는 `error` 필드가 문자열을 기대하는 매핑에 JSON object로 들어간 상황을 가리킨다.

### 판정

- 분류: 만성 데이터 처리 문제
- 영향도: 중간
- 예상 영향: 일부 로그 인덱싱 실패와 Logstash 큐 적체 가능성
- 미확인: 실패 이벤트 총량, 실제 유실량, 현재 큐 depth, 재처리 성공 여부

`error`와 `data.result.value`를 무조건 문자열로 바꾸는 것이 항상 정답은 아니다. 검색·집계 목적을 먼저 정하고, 필드명을 분리하거나 dynamic mapping을 제한한 뒤, 기존 데이터와 호환되는 ingest/Logstash 필터를 검증해야 한다.

## 3. Gemini 모델 404와 모델 가용성

제공된 Logstash payload Trace에서 다음 오류가 확인되었다.

```text
litellm.NotFoundError
GeminiException
This model models/gemini-2.0-flash is no longer available.
```

### 판정

- 분류: 확인된 모델 가용성 문제
- 영향도: 높음
- 영향 범위: 해당 모델을 호출하는 에이전트·서비스 기능
- 원인: 사용 중인 `gemini-2.0-flash` 모델 endpoint의 가용성 종료
- 미확인: 모든 에이전트가 해당 모델을 사용하는지, fallback이 실제로 성공하는지

모델명을 다른 값으로 일괄 치환하는 것만으로는 충분하지 않다. 공급자별 모델명, API 경로, quota, fallback, 응답 스키마를 함께 확인하고 smoke test를 통과시켜야 한다.

## 4. DNSConfigForming 경고

`kube-system`에서 `DNSConfigForming` 경고가 신규 항목으로 분류되었다. 제공된 RCA는 nameserver 허용 한도인 3개를 초과한 설정을 원인으로 제시했다.

### 판정

- 분류: 신규 설정 경고
- 영향도: 현재 실제 장애 영향은 미확인
- 위험: 일부 파드의 DNS 설정이 의도와 다르게 구성되거나 resolver 선택이 불안정해질 가능성
- 미확인: 어느 노드·파드에서 발생했는지, 실제 DNS query 실패가 있었는지

경고가 있다는 사실과 DNS 장애가 발생했다는 사실은 구분해야 한다. 조치 전에는 실제 파드의 `/etc/resolv.conf`, kubelet·노드 resolver 설정, DNS query 결과를 함께 확인해야 한다.

## 5. Elasticsearch 설정 경고와 cluster state 지연

Elasticsearch 매니페스트에서 다음 설정이 계속 투입되는 만성 경고가 보고되었다.

- `cluster.initial_master_nodes`
- `xpack.security.enabled`

제공된 RCA는 ECK 관리 범위에서 해당 설정이 금지되거나 제한되는 상태임에도 매니페스트에 남아 있어 reconciliation 경고가 반복된다고 설명한다.

또한 `solomon` 노드 응답 지연에 따른 `put-mapping` 30초 timeout이 반복된 것으로 보고되었다.

### 판정

- 분류: 만성 구성·클러스터 상태 문제
- 영향도: 관리·스키마 변경 지연 위험
- 현재 영향: 핵심 로그 파드는 Running
- 미확인: cluster state publication 지연의 현재 빈도와 Elasticsearch 요청 실패율

Running 상태와 cluster state publication 건강성은 같은 지표가 아니다. API 응답, cluster health, pending task, mapping update latency, 노드별 transport/http 지연을 함께 확인해야 한다.

## 6. 현재 가용성과 복구 신호

제공된 RCA 응답에서 현재 핵심 파드 상태는 다음과 같이 보고되었다.

```text
logs-es-* : Running
logs-ls-* : Running
logs-kb-* : Running
```

또한 최근 1시간 내 ECK Operator reconciliation run이 약 0.204초 만에 종료된 성공 Trace가 확인되었다.

```text
Ending reconciliation run ... took 0.204s
```

이 신호는 관리 로직이 적어도 해당 시점에는 정상적으로 reconciliation을 수행했다는 의미다. 하지만 과거 leader election 실패와 누적 restartCount가 해소되었다는 뜻은 아니다. 현재 성공과 만성 위험을 별도로 기록해야 한다.

## 7. 권장 조치와 검증 순서

### 1) ECK Operator

- restartCount와 Last State를 시각별로 분해
- `context deadline exceeded` 발생 시각과 API server·etcd 지연을 대조
- leader election Lease 갱신 실패 재발 여부 확인
- reconciliation 실패율과 마지막 성공 시각을 함께 기록

### 2) Elasticsearch 매니페스트

- ECK가 관리하는 설정과 사용자 설정을 구분
- `cluster.initial_master_nodes`, `xpack.security.enabled`의 현재 지원 방식 확인
- 변경 전 rendered manifest와 실제 Elasticsearch resource를 비교
- 무승인 운영 변경은 하지 않고, 검토 후 별도 승인 절차로 적용

### 3) Logstash 매핑

- `data.result.value`의 실제 값 유형 분포 수집
- `error`의 문자열·object 형태를 분리
- 기존 인덱스 mapping과 신규 index template을 비교
- 필터 변경 후 샘플 이벤트, 실패율, queue depth, 재처리 결과 검증

### 4) Gemini 모델

- `gemini-2.0-flash` 사용 위치를 전체 검색
- 공식 공급자 모델 목록과 실제 API 응답 확인
- 후보 모델별 인증·quota·응답 형식 smoke test
- fallback 성공 Trace를 확인한 뒤에만 운영 모델 변경

### 5) DNS

- 경고가 발생한 파드와 노드 식별
- 파드와 노드의 resolver 설정 비교
- nameserver 3개 이하라는 설정 의도와 실제 적용 상태 검증
- DNS query 성공률과 latency 확인

## 최종 판정

```text
현재 서비스 가용성: 유지로 보고됨
관리 레이어 건강성: WARN
로그 파이프라인 데이터 품질: WARN
Gemini 모델 가용성: FAIL에 가까운 고위험 이슈
DNS 설정: WARN
운영 변경 완료 여부: UNVERIFIED
```

이번 RCA에서 가장 중요한 관찰은 **현재 파드가 Running이라는 것과 클러스터가 건강하다는 것은 다르다**는 점이다. ECK Operator의 leader election 실패, Logstash mapping conflict, 모델 endpoint 404, DNS 설정 경고는 각각 다른 계층의 문제이므로 하나의 “클러스터 장애”로 뭉뚱그리지 않아야 한다.

또한 본 문서는 제공된 Cron 응답과 그 안의 Trace를 근거로 작성한 기록이다. 권장 조치가 실제로 적용되었는지, 적용 후 오류율과 재시작이 감소했는지는 별도 실행 Trace가 없으므로 확인하지 못했다.
