---
layout: post
title: "*ELK + Beats* — *Filebeat / Logstash / Elasticsearch / Kibana* 의 *4 단계* 와 *production 로깅 의 *진짜 그림*"
date: 2026-06-21 00:30:00 +0900
categories: [observability, logging, infrastructure, devops]
tags: [elk, elasticsearch, logstash, kibana, beats, filebeat, metricbeat, loki, logging, log-aggregation, ilm]
---

> *"로그 가 *서버 마다 *각자 흩어져 있다"* — 노드 5 개 까지 는 *`ssh + tail -f`* 로 버틸 수 있다. *50 개 부터* 그 방법 은 *물리적으로 불가능* 해진다.
>
> *2010 년대 초* *Elasticsearch 와 *Logstash 와 *Kibana* 가 *각자 다른 회사 / 다른 시점 에 출현* 한 후 *Elastic NV 가 *세 개를 묶어 *ELK Stack* 으로 통합* 했다. *그 후 *Beats* 가 *경량 수집기 로 추가* 되어 *오늘 의 *production 표준* 이 *되었다*. *Filebeat → Logstash → Elasticsearch → Kibana* — 이 *4 단계 가 *각자 책임 을 *나눠서 *대규모 로깅 의 *공통 어휘 가 되었다*.
>
> 이 글은 *4 단계 의 *각자 책임* 과 *역사 적 의도*, *Elasticsearch 의 *shard / replica / hot-warm-cold* 구조, *Kibana 의 KQL 과 lens*, *Logstash vs 직접 전송 의 architectural 트레이드 오프*, *우리 클러스터 의 Loki 와의 *비교* 까지 *production 관점* 에서 *분해* 한다.

내 *8 편 인프라 / 관측 연작* 의 *후속편* :
- [*CPU 의 *L1 / L2 / L3 캐시*](/2026/06/18/cpu-l1-l2-l3-cache-and-bottleneck-analysis.html)
- [*I/O 병목 어떻게 해결하지?*](/2026/06/18/io-bottleneck-how-to-solve.html)
- [*Virtual Thread* 와 *Carrier Thread* 의 *관계*](/2026/06/19/virtual-thread-and-carrier-thread-relationship.html)
- [*Prometheus* 가 *수집* 하고 *Grafana* 가 *대답* 한다*](/2026/06/19/prometheus-grafana-metrics-visualization.html)
- [*논블로킹 I/O 서버*](/2026/06/19/non-blocking-io-server-deep-dive.html)
- [*보안 의 7 기둥*](/2026/06/20/security-7-pillars-auth-encryption-firewall-audit.html)
- [*K8s 의 유용성 — 온프레미스 vs 클라우드*](/2026/06/20/kubernetes-on-premise-vs-cloud-usefulness.html)
- [*컨테이너 오케스트레이션 — DEIS / Rancher / Mesos / Nomad / Swarm 전쟁사*](/2026/06/20/kubernetes-container-orchestration-what-we-actually-use.html)

*Prometheus + Grafana* 가 *메트릭 의 *오늘 의 표준* 이었다면, *ELK + Beats* 는 *로그 의 *오늘 의 표준*. *둘 이 *observability 의 *3 기둥 중 *2 개 (metric, log)* 를 *각자 점유* 한 게 *현재 의 관측성 풍경*.

---

## TL;DR — *한 줄 결론*

> *ELK Stack* 은 *4 단계 의 *각자 책임 분리* : *Filebeat (경량 수집, 노드 마다)* → *Logstash (파싱 / 변환, 중앙)* → *Elasticsearch (저장 / 색인 / 검색)* → *Kibana (시각화)*. *Beats 가 *Logstash 보다 *수십 배 *경량* 이라서 *모든 노드 에 깔아도 부담 없음*. *Logstash 는 *복잡 한 파싱* 만 담당. *Elasticsearch 는 *역색인 (inverted index)* 기반 *전문 검색 엔진* 이라 *수십 TB 의 로그 에서 *KQL 한 줄 로 ms 단위 검색*. *Kibana 의 *KQL + lens + ILM* 이 *그것 을 *눈 으로 볼 수 있게* 만든다*. *대신 *비싸다* — Elasticsearch 가 *메모리 / 디스크 의 *블랙홀*. *그 비용 을 *못 감당 한 작은 팀* 은 *Loki + Grafana* 같은 *경량 대안* 으로 *피난*. *어느 쪽 을 *선택 할지* 는 *로그 양 / 검색 요구 / 비용* 의 *함수*.

---

## 1. *왜 *중앙 로깅 인가*

### 1.1 *분산 로그 의 *3 가지 고통*

> *서비스 5 개 + 노드 6 대 = 30 곳 의 *별개 로그 파일*. *문제 발생 시 *어디 부터 봐야 하나*.

| 고통 | 결과 |
|---|---|
| *어디 에 로그 가 있는지 모름* | `ssh A; tail -f; ssh B; tail -f; ssh C; ...` 무한 반복 |
| *시간 동기화 안 됨* | A 노드 12:00 의 *원인 이 *B 노드 11:59 의 *결과* — 순서 추론 불가 |
| *로그 회전 / 삭제* | 어제 의 *진짜 사고 로그* 가 *오늘 사라짐* |
| *검색 불가* | 1 GB 로그 파일 에서 *특정 user_id* 찾으려면 `grep` 분당 100MB 처리 |
| *Aggregation 불가* | "지난 1 시간 의 5xx 응답 *수*" 같은 *집계* 가 *불가능* |

### 1.2 *중앙 로깅 의 *3 가지 약속*

1. **모든 노드 의 로그 가 *한 곳 으로 모임***.
2. **시간 동기화 + 구조화* 되어 있어 *순서 / 인과 추론 가능***.
3. **검색 / 집계 / 시각화 가 *한 UI 에서 가능***.

→ 이게 *Elasticsearch + Kibana + 어떤 수집기* 가 *함께 풀고자 한 문제*.

---

## 2. *역사 — *3 회사 가 *합쳐진 길*

### 2.1 *각자 의 출발*

- **Elasticsearch (2010)** — Shay Banon 이 *Lucene 위에 *RESTful 분산 검색 엔진* 으로 출시. *내 부인 의 *레시피 검색* 을 위해 만든 첫 *Compass* 의 *진화*.
- **Logstash (2009)** — Jordan Sissel 이 *로그 의 *파싱 / 변환* 을 위해 *오픈소스 로 시작*. 처음엔 *Elasticsearch 와 무관*.
- **Kibana (2013)** — Rashid Khan 이 *Elasticsearch 의 *시각화 UI* 로 만든 첫 *Logstash 의 시각화*.

### 2.2 *Elastic NV 의 *통합 — *2014 년*

- Logstash 의 *Jordan Sissel*, Kibana 의 *Rashid Khan*, Elasticsearch 의 *Shay Banon* 이 *Elastic NV (전 Elasticsearch BV) 에 합류*.
- *ELK Stack* 이라는 *브랜드* 가 *공식 화*.

### 2.3 *Beats 의 *추가 — *2015 년*

> *Logstash 가 *각 노드 에 깔리기엔 *너무 무거웠다* (JVM, 100+ MB RAM 기본).

- *Packetbeat (네트워크)* 가 처음.
- *Filebeat (파일 tail), Metricbeat (메트릭), Heartbeat (uptime), Auditbeat (auditd), Winlogbeat (Windows)* 등 *family 로 확장*.
- **각자 *Go 로 작성*, *10 ~ 30 MB RAM***. *모든 노드 에 *DaemonSet* 으로 깔아도 부담 없음.

→ *ELK → Elastic Stack* 으로 *명칭 변경* — Beats 도 포함 의미.

---

## 3. *4 단계 의 *각자 책임*

```text
[App] → [Filebeat] → [Logstash] → [Elasticsearch] → [Kibana]
  ↑          ↑           ↑              ↑              ↑
log 출력  경량 수집    파싱/변환     저장/색인      시각화
표준출력   tail+ship   grok/mutate   shard/replica  KQL/dashboard
JSON      buffering   필터           역색인         ILM
```

### 3.1 *Filebeat — *경량 수집*

**책임** :
- *파일 시스템 의 *로그 파일 tail*.
- *변경 감지 + ship (전송)*.
- *backpressure 안전* — Logstash / ES 느릴 때 *로컬 disk 큐*.
- *at-least-once 보장* — registry 파일 로 *위치 기억*.

**경량성** :
- *Go binary 단일*, *RAM 10~30 MB*.
- *CPU 사용 ~0.1 vCPU* idle 시.

**설정 예** :
```yaml
filebeat.inputs:
  - type: filestream
    id: app-logs
    paths:
      - /var/log/myapp/*.log
    parsers:
      - ndjson:                   # 한 줄 = 한 JSON
          target: ""
          overwrite_keys: true

processors:
  - add_host_metadata:            # hostname, OS 자동 추가
      when.not.contains.tags: forwarded
  - add_kubernetes_metadata:      # K8s 환경 — pod, container, label 자동
      host: ${NODE_NAME}
      matchers:
        - logs_path:
            logs_path: "/var/log/containers/"

output.logstash:
  hosts: ["logstash.observability.svc:5044"]
  # 또는 ES 직접 전송 (Logstash 안 거침)
  # output.elasticsearch:
  #   hosts: ["https://es.observability.svc:9200"]
```

**Filebeat 의 *핵심 advantage*** :
- *각 노드 에 *DaemonSet* — 노드 추가 시 *자동 배포*.
- *K8s metadata 자동* — pod / container / label / namespace 가 *자동 enrichment*.
- *registry 로 *재시작 안전*.

### 3.2 *Logstash — *파싱 / 변환 / 라우팅*

**책임** :
- *비정형 로그 → 구조화 (Grok)*.
- *필드 변환 (mutate)*.
- *enrichment (lookup, geoip)*.
- *조건 별 라우팅 (특정 인덱스, alert 발사)*.

**왜 *경량 이 아닌가* — JVM 기반, *RAM 1 GB+ 기본*. *Beats 의 *50 배*.

**예 — Nginx access log 파싱** :
```ruby
input {
  beats { port => 5044 }
}

filter {
  # 비정형 log line → 필드
  grok {
    match => {
      "message" => '%{IPORHOST:client_ip} - %{DATA:user} \[%{HTTPDATE:timestamp}\] "%{WORD:method} %{DATA:request} HTTP/%{NUMBER:http_version}" %{NUMBER:status:int} %{NUMBER:bytes:int}'
    }
  }
  date {
    match => ["timestamp", "dd/MMM/yyyy:HH:mm:ss Z"]
    target => "@timestamp"
  }
  geoip {
    source => "client_ip"      # IP → city, country
  }
  if [status] >= 500 {
    mutate { add_tag => ["server_error"] }
  }
}

output {
  if "server_error" in [tags] {
    elasticsearch {
      hosts => ["https://es:9200"]
      index => "logs-errors-%{+YYYY.MM.dd}"
    }
  } else {
    elasticsearch {
      hosts => ["https://es:9200"]
      index => "logs-access-%{+YYYY.MM.dd}"
    }
  }
}
```

**Logstash 가 *없는 경우*** :
- 앱 이 *이미 JSON 으로 로그 출력* (Spring Boot logback-json) → *Logstash 불필요*.
- Filebeat 가 *Elasticsearch 로 직접 ship*.
- *Beats 의 *processor* 로 *간단한 변환 가능*.

### 3.3 *Elasticsearch — *저장 / 색인 / 검색 의 *심장*

**책임** :
- *문서 (document)* 저장 — JSON.
- *역색인 (inverted index)* 생성 — *어느 단어 가 *어느 문서 에 있는지* 의 역방향 매핑.
- *분산 검색* — shard 단위로 *병렬 처리*.
- *aggregation* — count, avg, percentile, histogram 등.

#### **(1) 역색인 의 *위력***

```text
[Forward index — 일반 DB]
doc1 = "the quick brown fox"
doc2 = "the lazy dog"

[Inverted index — Elasticsearch]
the    → doc1, doc2
quick  → doc1
brown  → doc1
fox    → doc1
lazy   → doc2
dog    → doc2
```

→ *"fox" 검색* — *역색인 lookup 으로 *즉시* doc1. *grep* 처럼 *전체 스캔* 안 함.

#### **(2) Shard 와 *Replica***

```text
Index "logs-2026.06.21" (10 GB)
   │
   ├ Primary shard 0 (2 GB) — node A
   ├ Primary shard 1 (2 GB) — node B
   ├ Primary shard 2 (2 GB) — node C
   ├ Primary shard 3 (2 GB) — node A
   └ Primary shard 4 (2 GB) — node B
   │
   ├ Replica of shard 0 — node B   ← node A 죽어도 OK
   ├ Replica of shard 1 — node C
   ├ ...
```

- *Shard* = *데이터 의 수평 분할*. *index 생성 시 결정* (이후 변경 어려움).
- *Replica* = *동기 복제*. *읽기 성능 + HA*.
- *검색 시 모든 shard 가 *병렬 처리* → 결과 *merge*.

→ *수십 TB 의 로그 에서 *ms 단위 검색* 의 *물리적 근거*.

#### **(3) ILM — *Index Lifecycle Management***

> *최근 로그 는 *빠른 디스크* 에, *옛 로그 는 *싼 디스크* 에, *3개월 후 *삭제*.

```text
[Hot phase]     0~3일   SSD, primary+replica   (검색 빈도 높음)
   ↓ rollover
[Warm phase]    3~30일  HDD, replica 줄임       (검색 가끔)
   ↓
[Cold phase]    30~90일 cold node, replica 0   (분기별 audit)
   ↓
[Frozen phase]  90~365일 S3 / snapshot         (1년 보존)
   ↓
[Delete]        365일+
```

→ *ILM policy* 가 *자동 으로 데이터 를 *적절한 디스크 로 이동*. *비용 / 성능 의 균형*.

#### **(4) Mapping — *스키마*

```json
PUT /logs-app
{
  "mappings": {
    "properties": {
      "@timestamp":   { "type": "date" },
      "level":        { "type": "keyword" },    # exact match
      "message":      { "type": "text" },        # full-text search
      "user_id":      { "type": "long" },
      "status":       { "type": "integer" },
      "client_ip":    { "type": "ip" },
      "geoip.location": { "type": "geo_point" }  # geo 검색
    }
  }
}
```

> **`text` vs `keyword`** :
> - `text` : *분석 (tokenize, lowercase, stemming)* — *full-text search*.
> - `keyword` : *그대로 저장* — *exact match, aggregation*.
> - *user_id, status 같은 *카테고리 / 식별자* 는 *반드시 `keyword`*. *`text` 로 저장 하면 aggregation 깨짐*.

### 3.4 *Kibana — *눈 으로 볼 수 있게*

**책임** :
- *Discover* : raw log 탐색 (KQL 또는 Lucene 쿼리).
- *Visualize / Lens* : chart, table, map, gauge.
- *Dashboard* : visualization 의 *집합*.
- *Alerts* : 조건 만족 시 *Slack / email / webhook*.
- *Index Management* : ILM, snapshot.

#### **KQL (Kibana Query Language)** :
```text
status >= 500 and host.name : "lemuel*"
level : "ERROR" and not message : "expected"
client_ip : "192.168.0.0/16"          # IP range
@timestamp > now-1h                    # 시간 범위
"user_id":42                           # JSON 필드 매치
```

#### **Lens — *드래그 앤 드롭 시각화*** :
- *필드 를 *축 / metric 으로 드래그*.
- *bar / line / pie / heatmap / area* 자동 선택.
- *Prometheus + Grafana 와 *비슷한 사용 경험*, *하지만 *로그 데이터* 에 *최적화*.

---

## 4. *Architectural 선택 — *Logstash 의 *생사*

### 4.1 *Logstash 가 *필요한 경우*

- *비정형 텍스트 로그* (Apache, Nginx, 옛 syslog).
- *복잡한 enrichment* (외부 DB lookup, geoip).
- *조건 별 라우팅* (특정 인덱스 / DLQ).
- *변환 후 *여러 destination* 분산.

### 4.2 *Logstash 가 *필요 없는 경우*

- *앱 이 *JSON structured logging* (Spring Boot logback-json, Pino, Bunyan).
- *간단한 enrichment* — Beats processor 로 충분.
- *비용 / 운영 부담 절감*.

→ *2026 년 추세* : *앱 이 JSON 으로 로그 출력 → Filebeat 가 ES 직접 ship*. *Logstash 생략 이 *흔함*.

### 4.3 *3 가지 흔한 architecture*

#### **(1) Full ELK + Beats — *대규모 운영*

```text
[App] → [Filebeat] → [Logstash] → [Elasticsearch] → [Kibana]
                          ↑
                     비정형 로그 파싱
```

#### **(2) Beats 직접 — *단순 운영*

```text
[App (JSON log)] → [Filebeat] → [Elasticsearch] → [Kibana]
```

#### **(3) Beats + Kafka + Logstash — *대규모 + 신뢰성**

```text
[App] → [Filebeat] → [Kafka] → [Logstash] → [Elasticsearch] → [Kibana]
                       ↑
                  buffer / replay
                  여러 consumer
                  ES 다운 시에도 데이터 손실 0
```

→ *수억 events/일* 의 *대규모 워크로드 의 *권장 패턴*. Kafka 가 *buffer + replay + multi-consumer*.

---

## 5. *Elasticsearch 의 *운영 의 *현실*

### 5.1 *세 종류 의 노드*

| 역할 | 책임 | 권장 사양 |
|---|---|---|
| **master** | cluster state 관리, shard 분배 | *전용 노드 권장* (작은 리소스 OK, RAM 2GB) |
| **data** | shard 저장 + 검색 | *큰 RAM (32GB+), 빠른 SSD* |
| **coordinator** | client 요청 분배 + merge | *medium spec* |
| **ingest** | pipeline 처리 (Logstash 대체 가능) | |
| **ML** | anomaly detection (X-Pack) | *전용 GPU 또는 큰 RAM* |

→ *production* 은 *최소 *3 master + 2 data + 2 coordinator* 권장.

### 5.2 *메모리 의 *진실*

> *Elasticsearch 는 *RAM 의 50% 를 *JVM heap 으로*, *나머지 50% 를 *page cache (Lucene)* 로 사용*.

```yaml
# JVM heap = 노드 RAM 의 50%, *최대 32 GB* (compressed oops 한계)
ES_JAVA_OPTS: "-Xms16g -Xmx16g"

# 노드 RAM 32GB → JVM 16GB + OS page cache 16GB
```

→ *대용량 검색 워크로드* 는 *32GB+ RAM* 이 *권장 최소*. *솔로몬 (15GB) 같은 노드 *에선 *부담*.

### 5.3 *Shard 의 *적정 크기*

- *너무 작음* : 수많은 shard → cluster state 폭증 → master 부담.
- *너무 큼* : 검색 / 복구 시간 증가.
- *권장* : *10 ~ 50 GB / shard*. *50 GB 초과 시 *rollover*.

### 5.4 *흔한 함정 — *7 가지*

| 함정 | 결과 |
|---|---|
| *Mapping explosion* (필드 수 무제한) | cluster state 폭증 → master CPU 100% |
| *Dynamic mapping 으로 *모든 필드 *자동 색인** | 디스크 / 메모리 폭증 |
| *Replica 0 + master 1* | 노드 1 죽으면 *복구 불가능* |
| *Heap 32GB 초과* | compressed oops 깨짐 → 메모리 효율 급락 |
| *Swap 활성화* | GC pause 폭발 → cluster yellow / red |
| *Snapshot 없이 운영* | 디스크 손상 시 *완전 손실* |
| *ILM 미설정* | 디스크 가득 → cluster read-only |

---

## 6. *Loki — *경량 대안*

### 6.1 *왜 *Loki 인가*

> *Grafana Labs* 가 *2018 년* 출시. *"Prometheus 의 *철학 을 *로그 에"*.

**핵심 차이 (Loki vs ES)** :
- *Loki 는 *log content* 를 *index 안 함* — *label 만 index*.
- *검색 시 *label 로 *후보 stream* 좁힘 → *그 stream 의 raw text 를 grep 처럼 *brute force*.

```text
[ES]    : 모든 단어 색인 → 빠른 풀텍스트 검색 가능, 디스크 5~10x 증가
[Loki]  : label 만 색인 → 디스크 효율 10x ↑, brute force 검색은 시간 ↑
```

→ *디스크 비용 압도적 절감*. *대신 *복잡한 풀텍스트 검색* 은 *느림*.

### 6.2 *Loki 의 *적합 워크로드*

- *Kubernetes pod log* (label 이 풍부 — namespace, pod, container, app).
- *간단한 grep 패턴* 검색.
- *비용 민감* 한 작은 ~ 중간 규모.
- *Grafana 와 *통합 UI* — 이미 Grafana 쓰는 경우.

### 6.3 *우리 클러스터 — Loki 의 *현실*

> 우리 6 노드 K3s 클러스터 는 *데이비드 노드* 에 *Loki* 운영.

**이유** :
- *6 노드 규모* — ES 의 *고가용성 운영 부담* 보다 *Loki 의 단순함 이 매력*.
- *Grafana + Prometheus + Loki* 가 *단일 UI* 로 통합.
- *디스크 비용* — 매일 *수 GB 로그* 를 *디스크 부담 없이* 보관.
- *복잡한 풀텍스트 검색 요구* 가 *현재 없음*.

→ *production 의 *작은 ~ 중간 규모* 에서 *Loki + Grafana 가 *ELK 대비 *더 합리적* 인 *흔한 사례*.

### 6.4 *Loki 의 *부족함*

- *수억 events/day 의 *대규모 워크로드* 에선 *brute force 검색 의 한계*.
- *복잡한 aggregation / pivot / anomaly detection* — ES 가 압승.
- *대규모 enterprise audit / 보안 분석* — ES 가 표준.

→ *Loki 는 *Operational logging*, *ELK 는 *Analytics-grade logging*.

---

## 7. *ELK 의 *2026 년 *경쟁자들*

| 도구 | 특징 | 적합 |
|---|---|---|
| **Elasticsearch** (Elastic) | *full-text + aggregation* 의 표준 | 대규모, 풀텍스트 중심 |
| **OpenSearch** (AWS fork) | ES 7.10 fork + 자체 진화 | AWS 환경 + 라이선스 자유 |
| **Loki** (Grafana) | label-only index, *경량* | Operational, K8s, Grafana 통합 |
| **Splunk** | enterprise 표준, 매우 비쌈 | 대기업 / 컴플라이언스 |
| **Datadog** | SaaS, 통합 관측성 | 클라우드 우선, 비용 무관 |
| **Sumo Logic** | SaaS, 보안 강조 | 작은 ~ 중간, 컴플라이언스 |
| **ClickHouse + Vector** | OLAP-style 로그 분석, *고성능 / 저비용* | 신생 — *2024 년 부터 채택 증가* |

### 7.1 *Elasticsearch 의 *라이선스 변화*

- *2021* — Elastic 이 *SSPL 라이선스* 도입. *AWS 우려* 로 *fork 가 OpenSearch* 로 분리.
- *2024* — Elastic 이 *AGPL + SSPL dual license* 로 *부분 완화*. 그러나 *OpenSearch 가 *이미 *대규모 채택*.

→ *2026 년 *오픈소스 ES 의 *주류 는 *OpenSearch*. *우리 클러스터 도 *Loki 를 선택* 한 이유 의 *부분적 동기*.

---

## 8. *언제 *ELK 를 *써야 하나*

### 8.1 *ELK 가 *압도적*인 경우*

- *대규모 (수억 events/일)*.
- *복잡한 풀텍스트 검색* — error message, stack trace.
- *비정형 로그 가 많음* (legacy apache, syslog).
- *컴플라이언스* (PCI, HIPAA) 가 *전체 로그 *보존 + 검색* 요구.
- *팀 이 *ELK 의 운영 노하우* 보유.

### 8.2 *ELK 가 *과한 경우*

- *작은 ~ 중간 규모* (< 1억 events/일).
- *K8s 환경* — label 풍부 한 pod log.
- *팀 < 5명*.
- *Grafana 이미 사용*.
- → **Loki 가 *더 합리적*.

### 8.3 *Hybrid — *작은 팀 의 현실*

```text
[App 일반 로그]   →  Loki   (대다수)
[Security audit] →  ELK    (작은 부분, 컴플라이언스)
[Application metrics] → Prometheus
[Traces] → Tempo / Jaeger
```

→ *각 로그 의 *성격 에 맞게 *다른 도구* — *비용 / 운영 부담 / 검색 요구* 의 *최적화*.

---

## 9. *결론 — *4 단계 의 *분업 의 *가치***

> *ELK + Beats* 의 *진짜 가치* 는 *각 단계 가 *각자 책임만 *제대로 함* 으로써 *전체 가 *확장 가능* 해 진다는 *분업 의 원칙*.

- *Filebeat* 가 *수집 만* 하기 때문에 *모든 노드 에 *부담 없이* 깔 수 있다.
- *Logstash* 가 *파싱 만* 하기 때문에 *중앙 에서 *복잡한 변환* 을 *집약*.
- *Elasticsearch* 가 *저장 / 검색 만* 하기 때문에 *역색인 의 *극한 성능* 을 *달성*.
- *Kibana* 가 *시각화 만* 하기 때문에 *KQL + Lens + ILM* 의 *깊이* 를 *제공*.

> *Prometheus + Grafana 가 *메트릭 의 *오늘 의 표준* 이라면, *Elastic Stack* 또는 *Loki + Grafana* 가 *로그 의 *오늘 의 표준*. *어느 쪽 을 선택할지* 는 *규모 / 검색 요구 / 비용 / 팀 노하우* 의 *함수*.

*우리 6 노드 K3s 클러스터* 는 *Loki 를 *선택* — *비용 / 단순성 의 *최적*. *수억 events/일* 의 *enterprise 워크로드* 라면 *ELK 가 *유일한 답*. *둘 의 *상대적 가치* 를 *내 맥락 에서 측정* 하는 것 이 *시니어 엔지니어 의 일*.

*"로그 가 *서버 마다 *각자 흩어져 있다"* 는 *2010 년 의 고통* 은 *2026 년 *ELK 또는 Loki 의 *어느 쪽 으로든 *해결 가능*. *그 4 단계 (수집 → 변환 → 색인 → 시각화) 의 *분업 의 원칙* 이 *현대 로깅 의 *불변 의 어휘*.

---

## *참고*

- *Elastic 공식 문서* — [elastic.co/guide](https://www.elastic.co/guide).
- *Grafana Loki 공식* — [grafana.com/oss/loki](https://grafana.com/oss/loki).
- *Logging Best Practices* — CNCF 의 *Observability Whitepaper*.
- *Clinton Gormley, Zachary Tong*, *Elasticsearch: The Definitive Guide* (2015).
- *Madhusudhan Konda*, *Elasticsearch in Action*, 2nd ed.
- *Brendan Gregg* — *Linux Performance* 에서 *로깅 관측성* 의 *시스템 적 관점*.
- 자매편 :
  - [*Prometheus + Grafana* — 메트릭 표준](/2026/06/19/prometheus-grafana-metrics-visualization.html)
  - [*K8s 의 유용성 — 온프레미스 vs 클라우드*](/2026/06/20/kubernetes-on-premise-vs-cloud-usefulness.html)
  - [*컨테이너 오케스트레이션 전쟁사*](/2026/06/20/kubernetes-container-orchestration-what-we-actually-use.html)
  - [*보안 의 7 기둥*](/2026/06/20/security-7-pillars-auth-encryption-firewall-audit.html)
