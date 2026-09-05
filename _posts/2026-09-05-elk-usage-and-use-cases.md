---
layout: post
title: "ELK 스택 사용법과 실전 사용사례: 로그를 검색 가능한 운영 데이터로 바꾸기"
date: 2026-09-05 12:54:49 +0900
categories: [Observability]
tags: [ELK, Elasticsearch, Logstash, Kibana, Filebeat, 로그분석, 보안관제]
---

# ELK의 사용법과 사용사례

서비스가 장애를 일으켰을 때 가장 먼저 필요한 것은 “무슨 일이 일어났는가”를 시간순으로 재구성할 수 있는 관측 데이터다. ELK는 로그를 한곳에 모으는 도구를 넘어, 수집·정제·검색·시각화·알림을 하나의 운영 흐름으로 연결하는 대표적인 로그 분석 플랫폼이다.

엄밀히 말하면 오늘날 Elastic Stack은 Elasticsearch와 Kibana를 중심으로 Elastic Agent, Logstash, Beats 등을 조합한다. Elastic 공식 문서는 Elasticsearch를 분산 검색·분석 엔진이자 데이터 저장소·벡터 데이터베이스로 설명하고, Kibana는 검색·시각화·대시보드·운영 관리 UI로 설명한다.[1][3]

이 글에서는 전통적인 **ELK(Elasticsearch–Logstash–Kibana)**를 기준으로 설명하되, 실제 운영에서는 Filebeat 또는 Elastic Agent를 앞단에 추가하는 구성을 함께 다룬다.

## 1. ELK의 전체 구조

```text
애플리케이션 / 서버 / 컨테이너
          │
          ▼
 Filebeat 또는 Elastic Agent
          │
          ▼
       Logstash
  수집 → 파싱 → 보강 → 라우팅
          │
          ▼
    Elasticsearch
  인덱싱 → 검색 → 집계
          │
          ▼
        Kibana
 Discover / Dashboard / Alert / Case
```

### Elasticsearch: 저장과 검색의 중심

Elasticsearch는 데이터를 인덱스와 샤드 구조로 저장하고, near real-time 검색과 집계를 제공한다. 인덱스는 여러 샤드로 나뉘어 노드에 분산될 수 있으므로 데이터량과 검색량이 커지는 환경에 적합하다.[1][3]

주요 역할은 다음과 같다.

- 로그 문서 저장
- 전문 검색과 필드 필터링
- 시간 범위 검색
- 상태 코드·응답시간·서비스별 집계
- 지리 정보와 시계열 데이터 분석
- 알림과 머신러닝 기능의 데이터 기반 제공

### Logstash: 수집·변환·라우팅

Logstash는 실시간 데이터 수집 엔진이다. 다양한 input, filter, output 플러그인을 사용해 서로 다른 원천의 이벤트를 통합하고, 파싱·정규화·보강 후 목적지로 전송한다.[2]

예를 들어 다음과 같은 작업을 담당한다.

- Apache/Nginx 로그에서 IP, 경로, 상태 코드 추출
- 애플리케이션 JSON 로그의 필드 정규화
- 문자열 시간값을 `@timestamp`로 변환
- 환경·서비스·버전 필드 추가
- 민감한 필드 제거 또는 마스킹
- 서비스별 인덱스나 데이터 스트림으로 라우팅

### Filebeat 또는 Elastic Agent: 가벼운 수집기

Filebeat는 서버의 로그 파일을 감시하고 새 로그를 수집해 Elasticsearch 또는 Logstash로 전달하는 경량 shipper다. 로그 파일별 harvester가 새 내용을 읽고, 수집 이벤트를 출력 대상으로 보낸다.[4]

운영에서는 다음과 같이 선택할 수 있다.

- 단순한 파일 수집: Filebeat → Elasticsearch
- 복잡한 파싱과 라우팅: Filebeat → Logstash → Elasticsearch
- 로그·메트릭·보안 통합 수집: Elastic Agent와 Fleet

## 2. 기본 설치와 운영 순서

### 2.1 버전은 맞춰서 설치한다

Elastic Stack 구성요소는 같은 버전 계열로 맞추는 것이 기본이다. Elasticsearch, Kibana, Logstash, Beats 또는 Agent의 버전 불일치는 호환성 문제를 만들 수 있으므로, 설치 전에 버전 매트릭스와 업그레이드 경로를 확인해야 한다.[3]

### 2.2 먼저 로그 스키마를 정한다

도구를 설치하기 전에 로그의 최소 필드를 정하는 것이 좋다.

```json
{
  "@timestamp": "2026-09-05T03:54:49.000Z",
  "service.name": "order-service",
  "service.version": "2026.09.05",
  "log.level": "ERROR",
  "message": "payment request failed",
  "http.request.method": "POST",
  "url.path": "/api/orders",
  "http.response.status_code": 502,
  "event.duration": 2400000000,
  "trace.id": "...",
  "user.id": "[REDACTED]"
}
```

핵심은 자유로운 문자열만 남기지 않는 것이다. `status_code`, `duration`, `service.name`, `trace.id`가 구조화되어 있어야 Kibana의 필터와 집계가 안정적으로 작동한다.

### 2.3 Filebeat → Logstash 파이프라인 예시

Filebeat 입력 예시는 다음과 같다.

```yaml
filebeat.inputs:
  - type: filestream
    id: shop-api
    paths:
      - /var/log/shop/*.json
    parsers:
      - ndjson:
          target: ""
          add_error_key: true

output.logstash:
  hosts: ["logstash:5044"]
```

Logstash는 JSON을 읽고 필요한 필드를 보강한 뒤 Elasticsearch로 보낼 수 있다.

```conf
input {
  beats {
    port => 5044
  }
}

filter {
  if [message] {
    json {
      source => "message"
      skip_on_invalid_json => true
    }
  }

  mutate {
    add_field => { "event.dataset" => "shop.api" }
    remove_field => ["authorization", "cookie", "password"]
  }
}

output {
  elasticsearch {
    hosts => ["https://elasticsearch:9200"]
    index => "logs-shop-api-%{+YYYY.MM.dd}"
  }
}
```

실제 운영에서는 자격증명을 설정 파일에 평문으로 넣지 말고, Secret·API key·TLS 인증서를 별도의 보안 경로로 관리해야 한다.

## 3. Kibana에서 로그를 보는 방법

### 3.1 Data View를 만든다

Kibana에서 `logs-*`와 같은 인덱스 패턴을 Data View로 등록하고 시간 필드로 `@timestamp`를 지정한다. 그러면 시간 범위 기반의 로그 탐색이 가능해진다.

### 3.2 Discover에서 원인을 좁힌다

장애 조사 순서는 보통 다음과 같다.

1. 장애가 시작된 시간 범위를 선택한다.
2. `service.name`으로 문제 서비스를 제한한다.
3. `log.level: ERROR` 또는 `http.response.status_code >= 500`을 필터링한다.
4. `trace.id`, 요청 경로, 사용자 요청 ID로 관련 이벤트를 연결한다.
5. 원인 후보가 나타난 시점과 배포 버전을 비교한다.
6. 동일 오류의 발생량과 최초·마지막 발생 시각을 집계한다.

Kibana의 Discover는 원시 데이터를 검색·필터링하는 진입점이고, Lens와 Dashboard는 검색 결과를 차트와 운영 화면으로 재사용하는 계층이다.[3]

예시 KQL:

```text
service.name: "order-service" and
log.level: "ERROR" and
http.response.status_code >= 500
```

```text
trace.id: "특정-trace-id"
```

### 3.3 대시보드를 만든다

운영 대시보드에는 다음 패널을 우선 배치한다.

- 서비스별 로그량
- 오류율과 5xx 응답 수
- p50/p95/p99 응답시간
- 엔드포인트별 요청량
- 배포 버전별 오류 비교
- 예외 클래스 상위 목록
- 노드·파드·가용영역별 오류 분포

대시보드는 보기 좋은 화면보다 의사결정에 필요한 질문에 답해야 한다. 예를 들어 “지금 오류가 늘었는가?”와 “어느 서비스·버전·경로에서 늘었는가?”가 한 화면에서 이어져야 한다.

## 4. 대표 사용사례

### 사례 1: 장애 원인 분석

API 오류가 갑자기 증가하면 Kibana에서 오류율, 배포 버전, 요청 경로, trace ID를 함께 본다. 애플리케이션 로그와 프록시 로그를 동일한 `@timestamp`, `trace.id`, `request.id`로 연결하면 “외부 요청 실패인지, 내부 예외인지, downstream timeout인지”를 빠르게 분리할 수 있다.

단, 로그 검색 결과만으로 장애 원인을 확정해서는 안 된다. 배포 이벤트, 메트릭, 트레이스, 실제 응답 코드와 함께 대조해야 한다.

### 사례 2: Kubernetes 운영 관측

컨테이너 표준출력을 수집해 `kubernetes.namespace`, `kubernetes.pod.name`, `kubernetes.container.name`, `kubernetes.node.name`을 구조화하면 파드 재시작과 오류 로그를 함께 분석할 수 있다.

활용 예시는 다음과 같다.

- 특정 namespace의 CrashLoopBackOff 관련 로그 검색
- 노드별 오류 집중 여부 확인
- 특정 이미지 태그 배포 후 오류율 비교
- readiness/liveness 실패와 애플리케이션 예외의 시간 상관관계 확인

ELK는 Kubernetes 상태 자체를 대체하지 않는다. `kubectl`, 이벤트, 메트릭, 로그를 함께 사용해야 실제 상태와 로그 누락을 구분할 수 있다.

### 사례 3: 보안 관제

웹 접근 로그, 인증 실패, 권한 변경, API key 사용, 방화벽·프록시 로그를 중앙화하면 비정상 패턴을 탐지할 수 있다. Elastic Security는 SIEM과 보안 분석 흐름을 제공하며, 탐지 규칙과 알림을 이용해 조사 대상 이벤트를 만들 수 있다.[6]

예시는 다음과 같다.

- 짧은 시간에 반복되는 로그인 실패
- 평소와 다른 국가·IP·시간대의 접근
- 관리자 권한 변경 직후 대량 API 호출
- 동일 계정의 동시다발적 세션
- 웹 서버의 비정상적인 경로 스캔

보안 로그에는 개인정보와 인증정보가 포함될 수 있으므로 수집 전에 마스킹, 접근권한, 보존기간을 정해야 한다.

### 사례 4: 비즈니스 분석

ELK는 기술 로그뿐 아니라 주문·결제·배송 이벤트를 검색 가능한 이벤트 데이터로 만들 수 있다. 예를 들어 주문 완료율, 결제 실패 사유, 시간대별 구매량, 특정 상품의 오류율을 집계할 수 있다.

다만 로그를 정산 원장이나 거래 데이터베이스의 대체재로 사용하면 안 된다. 비즈니스 수치의 기준 데이터와 로그 기반 분석 수치를 분리하고, 둘 사이의 차이를 reconciliation으로 확인해야 한다.

### 사례 5: 검색과 고객지원

제품 문서, FAQ, 티켓, 장애 이력 등을 Elasticsearch에 색인하면 전문 검색과 필터를 제공할 수 있다. 최신 Elasticsearch는 벡터 검색과 AI 관련 기능도 제공하지만, 검색 품질은 임베딩 모델보다 문서 분할, 메타데이터, 권한 필터, 평가셋 설계에 크게 좌우된다.[1]

## 5. 운영에서 자주 실패하는 지점

### 로그를 모두 수집하면 된다는 착각

무작정 모든 로그를 저장하면 비용과 노이즈만 증가한다. 운영에 필요한 필드, 보존기간, 샘플링 정책, debug 로그의 조건을 정해야 한다.

### JSON처럼 보이지만 실제로는 문자열인 로그

문자열 하나에 모든 정보가 들어 있으면 Kibana 집계가 어렵다. 애플리케이션에서 구조화 로그를 생성하고, 불가피한 경우 Logstash 또는 ingest pipeline에서 파싱한다.

### 시간대와 시간 필드 불일치

`@timestamp`를 UTC로 저장하더라도 Kibana 표시 시간대, 애플리케이션 로컬 시간, DB 시간대가 섞이면 장애 순서가 뒤집힐 수 있다. 시스템 전체의 시간 동기화와 timestamp 규칙을 먼저 정해야 한다.

### 인덱스를 날짜별로 무한 생성

인덱스와 샤드 수가 과도하면 클러스터 운영 부담이 커진다. 데이터 스트림, lifecycle 정책, hot-warm-cold 보존 전략을 검토하고, 작은 데이터에 지나치게 많은 샤드를 만들지 않는다.

### 로그에 비밀정보를 기록

비밀번호, 토큰, 쿠키, 결제정보, 개인정보를 로그에 남기지 않는다. 이미 유출된 로그는 단순 삭제보다 자격증명 회전, 접근권한 점검, 보존본·스냅샷 확인까지 필요하다.

## 6. ELK를 도입하는 현실적인 단계

1. 한 서비스의 구조화 JSON 로그부터 시작한다.
2. `@timestamp`, `service.name`, `log.level`, `trace.id`, `duration`, `status_code`를 표준화한다.
3. Filebeat 또는 Agent로 수집하고, 복잡한 변환이 필요할 때만 Logstash를 둔다.
4. Discover에서 장애 조사 절차를 재현한다.
5. 오류율·지연시간·로그량 대시보드를 만든다.
6. 보존기간과 비용을 측정한다.
7. 알림은 실제 대응 가능한 수준으로 제한한다.
8. 보안 로그와 비즈니스 이벤트를 별도 데이터 스트림과 권한으로 분리한다.

## 결론

ELK의 핵심은 제품 세 개를 설치하는 것이 아니라, 운영 이벤트를 일관된 구조로 수집하고 검색 가능한 증거로 만드는 것이다.

- Filebeat 또는 Agent는 데이터를 운반한다.
- Logstash는 복잡한 수집·변환·라우팅을 담당한다.
- Elasticsearch는 저장·검색·집계를 담당한다.
- Kibana는 탐색·시각화·대시보드·알림의 인터페이스가 된다.

작게 시작한다면 한 서비스의 장애 대응 시간을 줄이는 것부터 검증하는 것이 좋다. “모든 로그를 모으기”보다 “장애가 발생했을 때 어떤 필드로 원인을 좁힐 것인가”를 먼저 설계해야 ELK가 실제 운영 가치를 만든다.

## 참고 자료

[1] Elasticsearch Reference — 검색·분석 엔진, 데이터 저장소, 쿼리와 집계  
[2] Logstash Reference — 수집·변환·라우팅 파이프라인  
[3] The Elastic Stack — Elasticsearch, Kibana, Agent, Logstash 구성과 역할  
[4] Filebeat Overview — 로그 파일 수집과 전달 구조  
[5] Elastic Observability — 로그·메트릭·트레이스 기반 관측  
[6] Elastic Security — 보안 분석과 탐지 흐름

## 출처

- Elasticsearch: https://www.elastic.co/guide/en/elasticsearch/reference/current/index.html
- Logstash: https://www.elastic.co/guide/en/logstash/current/introduction.html
- Elastic Stack / Kibana: https://www.elastic.co/guide/en/kibana/current/introduction.html
- Filebeat: https://www.elastic.co/guide/en/beats/filebeat/current/filebeat-overview.html
- Observability: https://www.elastic.co/docs/solutions/observability
- Security: https://www.elastic.co/docs/solutions/security

## Sources

[1] https://www.elastic.co/guide/en/elasticsearch/reference/current/index.html — Elasticsearch Reference
[2] https://www.elastic.co/guide/en/logstash/current/introduction.html — Logstash Reference
[3] https://www.elastic.co/guide/en/kibana/current/introduction.html — The Elastic Stack
[4] https://www.elastic.co/guide/en/beats/filebeat/current/filebeat-overview.html — Filebeat Overview
[5] https://www.elastic.co/docs/solutions/observability — Elastic Observability
[6] https://www.elastic.co/docs/solutions/security — Elastic Security
