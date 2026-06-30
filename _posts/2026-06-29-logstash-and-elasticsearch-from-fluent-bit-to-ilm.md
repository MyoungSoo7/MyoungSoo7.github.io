---
layout: post
title: "Logstash 와 Elasticsearch — Fluent Bit 파이프라인 부터 ILM 까지"
date: 2026-06-29 09:50:00 +0900
categories: [observability, elk, elasticsearch, logstash]
tags: [elasticsearch, logstash, fluent-bit, ilm, kibana, eck, observability, log-aggregation, inverted-index]
---

내 6 노드 K3s 클러스터 의 *33 개 도메인* 의 로그는 *모두 ELK 로 모인다*. Fluent Bit (각 노드 의 DaemonSet) → Logstash (필터 + 라우팅) → Elasticsearch (hot/warm tier + ILM) → Kibana (시각화) 의 *완전 한 파이프라인*. 이 글은 *14개월 운영 경험* 위에서 *Logstash 와 Elasticsearch 의 *역할 + 설계 결정 + 운영 함정* 의 *현실 가이드*.

---

## 1. ELK 가 *왜 필요한가* — 한 마디로

쿠버네티스 의 *6 노드 + 70 개 pod* 의 *로그 가 *각 노드 의 /var/log/containers/* 에 *흩어져 있다*. 사고 발생 시 *모든 노드 에 SSH + 로그 추적* 은 *불가능*. *중앙 집중* 의 *유일한 합리적 방법* — ELK.

```
Pod stdout → /var/log/containers/{pod}_{ns}_{container}.log
   ↓ Fluent Bit DaemonSet (각 노드)
Logstash (필터·enrich·라우팅)
   ↓
Elasticsearch (저장·인덱싱·검색)
   ↓
Kibana (대시보드·검색 UI)
```

대안: *Loki (Grafana)*, *Splunk (유료)*, *Datadog (SaaS)*. ELK 의 *장점* — *오픈 소스 + 풀텍스트 검색 의 압도적 강점 + Kibana 의 성숙 도*.

---

## 2. Fluent Bit vs Logstash — *왜 둘 다*

흔한 오해 — *"Logstash 만 으로 충분한 거 아닌가?"*. 현실 — *별도 의 역할*.

### Fluent Bit
- **C 로 작성** — *극도 의 경량* (메모리 *10~30 MB*)
- **노드 마다 DaemonSet** — *각 노드 의 /var/log* 에서 *직접 수집*
- **간단 한 파싱 + 라우팅** — *JSON parse, multiline join* 정도
- **로 컬 buffering** — *Logstash 일시 중단 시 *디스크 buffer 로 보존*

### Logstash
- **JVM 으로 작성** — *무거움* (메모리 *2~4 GB* 권장)
- **중앙 집중** — *클러스터 에 *1~2 개 의 인스턴스*
- **복잡 한 변환** — *grok 정규식, geoip enrichment, GC log 파싱, application-specific 라우팅*
- **다중 output** — *ES + Slack + S3 archive* 같은 *동시 라우팅*

### *왜 둘 다*
*노드 마다 Logstash 를 *돌리면 *각 노드 의 *2~4 GB 가 *로그 만 으로 *낭비*. *경량 의 Fluent Bit 가 *수집 + 간단 한 변환* 만 하고 *복잡 한 작업 은 *중앙 의 Logstash 에 *위임* 의 *분업 구조*.

내 클러스터 의 *fluent-bit-config*:
```ini
[INPUT]
    Name             tail
    Path             /var/log/containers/*.log
    Parser           docker
    DB               /var/log/flb_kube.db
    Mem_Buf_Limit    50MB
    Skip_Long_Lines  On
    Refresh_Interval 10

[FILTER]
    Name             kubernetes
    Match            kube.*
    Kube_URL         https://kubernetes.default.svc:443
    Merge_Log        On
    K8S-Logging.Parser   On
    K8S-Logging.Exclude  On

[OUTPUT]
    Name             forward
    Match            *
    Host             logstash.elk.svc.cluster.local
    Port             24224
    Retry_Limit      no_limits
```

→ Fluent Bit *kubernetes filter 가 *pod label / namespace / container name 의 *meta* 를 *자동 추가*. Logstash 가 *그 meta 기반 라우팅* 가능.

---

## 3. Logstash 파이프라인 — *입력 → 필터 → 출력*

Logstash 의 *심장* 은 *config 파일*. 3 stage:

```ruby
# /usr/share/logstash/pipeline/logstash.conf
input {
    forward {
        port => 24224
    }
    beats {
        port => 5044
    }
}

filter {
    # 1) JSON 자동 파싱
    if [log] =~ /^\{/ {
        json {
            source => "log"
            target => "parsed"
        }
    }

    # 2) Spring Boot 로그 grok 파싱
    if [kubernetes][container_name] =~ /sparta-.*-service/ {
        grok {
            match => {
                "log" => "%{TIMESTAMP_ISO8601:timestamp} %{LOGLEVEL:level} \[%{DATA:thread}\] %{DATA:logger} - %{GREEDYDATA:message}"
            }
        }
        date {
            match => ["timestamp", "ISO8601"]
            target => "@timestamp"
        }
    }

    # 3) GC log 별도 인덱스
    if [kubernetes][container_name] =~ /.*-gc-log/ {
        mutate {
            add_field => { "index_target" => "gc-logs" }
        }
    }

    # 4) ERROR 만 별도 alerting 라우팅
    if [level] == "ERROR" {
        clone {
            clones => ["alert"]
        }
    }

    # 5) Velero / ArgoCD 같은 *operator* 로그 의 tag
    if [kubernetes][namespace] in ["velero", "argocd", "kube-system"] {
        mutate {
            add_tag => ["operator-log"]
        }
    }
}

output {
    # 메인 — 모든 로그 ES 에 저장
    elasticsearch {
        hosts => ["http://elasticsearch.elk.svc.cluster.local:9200"]
        index => "%{[index_target]}-%{+YYYY.MM.dd}"
        manage_template => false
        ilm_enabled => false   # ES 측 ILM 사용
    }

    # ERROR 만 Slack
    if "alert" in [tags] {
        http {
            url => "https://slack.webhook.url"
            http_method => "post"
            format => "json"
            mapping => {
                "text" => "ERROR in %{[kubernetes][namespace]}/%{[kubernetes][pod_name]}: %{message}"
            }
        }
    }

    # operator-log 만 S3 백업
    if "operator-log" in [tags] {
        s3 {
            region => "ap-northeast-2"
            bucket => "lemuel-logs-archive"
            prefix => "operators/%{+YYYY/MM/dd}"
        }
    }
}
```

### grok — *Logstash 의 *핵심 무기***
정규식 의 *명명 된 캡처*. *Spring Boot 의 *기본 포맷*, *Nginx access log*, *MySQL slow query* 등 *수십 개 의 미리 정의 된 패턴* 제공.

함정: *grok 의 *비용*. *복잡 한 정규식 + 큰 라인* → *Logstash 의 CPU 폭증*. 가능 하면 *애플리케이션 측 *JSON 로깅* 으로 *grok 회피* 가 *훨씬 효율*.

### Dead Letter Queue
*Logstash 에서 ES 가 *reject 한 이벤트* (예: *mapping 충돌*) 의 *별도 저장*. 잃지 않음.
```ruby
dead_letter_queue.enable: true
dead_letter_queue.max_bytes: 1024mb
```

---

## 4. Elasticsearch — *Inverted Index 의 *마법***

Elasticsearch 의 *진짜 가치* — *풀텍스트 검색* 의 *압도적 성능*. RDB 의 *LIKE '%foo%'* 가 *full scan* 이라면 ES 는 *O(1)~O(log n)*.

### Inverted Index 의 구조
```
원본 문서:
  doc1: "the quick brown fox"
  doc2: "the lazy dog"
  doc3: "the fox jumps"

Inverted Index:
  "the"   → [doc1, doc2, doc3]
  "quick" → [doc1]
  "brown" → [doc1]
  "fox"   → [doc1, doc3]
  "lazy"  → [doc2]
  "dog"   → [doc2]
  "jumps" → [doc3]
```

검색 *"fox"* → *[doc1, doc3] 즉시 반환*. *full scan 없음*. *RDB 의 BTree index + 풀텍스트 의 *최적화 결합*.

### Analyzer — *토큰화 + 정규화*
영문 의 *"Running"* 과 *"runs"* 와 *"ran"* 를 *같은 토큰 으로 매핑* 의 *역할*.

```
"The quick brown foxes were running"
  ↓ Standard Tokenizer (공백 + 구두점)
["The", "quick", "brown", "foxes", "were", "running"]
  ↓ Lowercase Filter
["the", "quick", "brown", "foxes", "were", "running"]
  ↓ Stop Filter (the, were 제거)
["quick", "brown", "foxes", "running"]
  ↓ Stemmer (foxes→fox, running→run)
["quick", "brown", "fox", "run"]
```

→ *"foxes are running"* 과 *"a fox runs"* 가 *같은 토큰 셋* 으로 *매칭*.

### 한국어 — *Nori Analyzer*
한국어 의 *조사 / 어미 변화* 의 처리. *세종 사전 기반*.

```json
PUT /korean-blog
{
    "settings": {
        "analysis": {
            "analyzer": {
                "korean": {
                    "type": "custom",
                    "tokenizer": "nori_tokenizer",
                    "filter": ["lowercase", "nori_part_of_speech"]
                }
            }
        }
    }
}
```

`"먹는다", "먹었다", "먹는"` → `"먹다"` 의 *공통 형태소 추출*.

---

## 5. Index Mapping — *DB 의 *스키마* 격*

```json
PUT /sparta-logs-2026.06.29
{
    "mappings": {
        "properties": {
            "@timestamp": { "type": "date" },
            "level": { "type": "keyword" },          // ← exact match
            "message": { "type": "text" },           // ← 풀텍스트 검색
            "kubernetes.namespace": { "type": "keyword" },
            "kubernetes.pod_name": { "type": "keyword" },
            "trace_id": { "type": "keyword" },
            "user_id": { "type": "long" },
            "response_time_ms": { "type": "integer" },
            "meta": { "type": "object", "enabled": true }
        }
    }
}
```

### keyword vs text — *흔한 함정*
- `keyword` — *exact match 만*. *groupBy / aggregation 가능*. 예: `level = "ERROR"`
- `text` — *analyzer 적용 + 풀텍스트 검색*. *aggregation 불가*. 예: `message LIKE 'NullPointer'`

*둘 다 필요* 면 *multi-field*:
```json
"message": {
    "type": "text",
    "fields": {
        "raw": { "type": "keyword" }
    }
}
```
→ *풀텍스트 는 `message`*, *aggregation 은 `message.raw`*.

### Dynamic Mapping — *프로덕션 함정*
ES 는 *자동 으로 field 추가*. 처음 *string 으로 본 field 가 *나중에 *number 로 오면 → *reject*. 또는 *모든 field 의 *index 생성* → *디스크 폭증*.

해결:
```json
"settings": {
    "index.mapping.total_fields.limit": 1000,    // ← 폭증 방지
    "index.mapping.ignore_malformed": true        // ← 타입 충돌 무시
}
```

또는 *strict mapping* — *알려진 field 만 허용*. 운영 의 *권장*.

---

## 6. Tier 설계 — Hot / Warm / Cold

내 클러스터 의 *7 노드 ES* — *Hot 3, Warm 2, Cold 2*.

| Tier | 노드 | 디스크 | CPU/RAM | 역할 |
|---|---|---|---|---|
| **Hot** | 3 | NVMe SSD | 높음 | *최근 7일* 의 *활발한 read/write* |
| **Warm** | 2 | SATA SSD | 중간 | *7~30일* 의 *읽기 위주* |
| **Cold** | 2 | HDD | 낮음 | *30일~* 의 *드물 게 읽음* |

### Hot — *write 의 *진앙*
- *모든 새 인덱스 가 *여기 에 생성*
- *refresh_interval = 1s* (*1초 마다 검색 가능*) — *높은 write throughput 필요*
- *replica = 1* (*HA 보장*)

### Warm — *read 의 *대부분*
- *refresh_interval = 30s* (*write 거의 없음 → 비용 절감*)
- *replica = 0* (*디스크 절감*)
- *force_merge → 1 segment* (*read 최적화*)

### Cold — *audit / 규정 보관*
- *searchable snapshot* 또는 *frozen tier*
- *디스크 의 *95%+ 절감*
- *검색 시 *느림 허용* (몇 초)

### Node Allocation
```yaml
# warm 노드 의 elasticsearch.yml
node.attr.data: warm

# 또는 cold
node.attr.data: cold
```

→ *index 의 *tier 속성* 에 따라 *자동 라우팅*.

---

## 7. ILM (Index Lifecycle Management) — *자동화 의 *심장***

수동 으로 *오래된 인덱스 의 삭제 / tier 이동* 은 *불가능*. ES 의 *ILM 정책* 으로 *자동화*.

```json
PUT /_ilm/policy/logs-policy
{
    "policy": {
        "phases": {
            "hot": {
                "min_age": "0ms",
                "actions": {
                    "rollover": {
                        "max_size": "50GB",
                        "max_age": "1d"
                    },
                    "set_priority": { "priority": 100 }
                }
            },
            "warm": {
                "min_age": "7d",
                "actions": {
                    "allocate": {
                        "include": { "data": "warm" },
                        "number_of_replicas": 0
                    },
                    "forcemerge": { "max_num_segments": 1 },
                    "set_priority": { "priority": 50 }
                }
            },
            "cold": {
                "min_age": "30d",
                "actions": {
                    "allocate": {
                        "include": { "data": "cold" }
                    },
                    "freeze": {},
                    "set_priority": { "priority": 0 }
                }
            },
            "delete": {
                "min_age": "90d",
                "actions": {
                    "delete": {}
                }
            }
        }
    }
}
```

→ *Hot 7일 → Warm 23일 → Cold 60일 → 삭제*. *완전 자동*.

### Rollover — *index size 의 자동 관리*
`max_size: 50GB` — *해당 크기 도달 시 *새 index 생성*. *큰 index 의 *write contention 분산*.

`logs-2026.06.29-000001` → `logs-2026.06.29-000002` → ... — *alias 가 *항상 *최신 index 로 *write*.

---

## 8. ECK Operator — *K8s 의 *ES 운영*

내 클러스터 는 *ECK (Elastic Cloud on Kubernetes) Operator* 로 *ES + Kibana + Logstash* 운영.

```yaml
apiVersion: elasticsearch.k8s.elastic.co/v1
kind: Elasticsearch
metadata:
  name: lemuel
  namespace: elk
spec:
  version: 8.13.0
  nodeSets:
    - name: hot
      count: 3
      config:
        node.roles: ["master", "data_hot", "data_content"]
        node.attr.data: hot
      podTemplate:
        spec:
          containers:
            - name: elasticsearch
              resources:
                requests: { memory: 8Gi, cpu: 2 }
                limits: { memory: 8Gi, cpu: 4 }
              env:
                - name: ES_JAVA_OPTS
                  value: "-Xms4g -Xmx4g"
      volumeClaimTemplates:
        - metadata: { name: elasticsearch-data }
          spec:
            accessModes: ["ReadWriteOnce"]
            resources: { requests: { storage: 200Gi } }
            storageClassName: local-path
    - name: warm
      count: 2
      config:
        node.roles: ["data_warm"]
        node.attr.data: warm
      # ...
```

ECK 의 *장점*:
- *master / data tier 의 *자동 분리*
- *certificate 자동 관리 (HTTPS)*
- *upgrade 의 *zero-downtime rolling*
- *snapshot 정책 의 *CRD 관리*

---

## 9. 운영 함정 — *내가 *14개월 *겪은 것들*

### (1) Mapping Explosion — *디스크 폭증*
*Spring Boot 의 *예외 객체 의 *모든 field 가 *동적 mapping* → *수천 개 field* → *디스크 의 *수 TB*.

해결 — *namespace 별 *strict mapping*. 알려진 field 만.

### (2) Shard Oversharding — *클러스터 의 *과부하*
*매일 N 개 의 새 인덱스 + 각 5 shard + 1 replica* = *N × 10 shard / 일*. *수개월 후 *수만 shard* → *master 노드 의 *heartbeat 폭증*.

해결 — *큰 인덱스 면 *적은 shard*, *작은 인덱스 면 *shard 1* 또는 *index consolidation*. *권장 shard 크기 — 10~50 GB*.

### (3) Yellow / Red 상태
- **Yellow** — *replica 미할당* (*예: warm 노드 의 *부족*). *데이터 손실 위험 *없지만 *주의*.
- **Red** — *primary 미할당*. *읽기 / 쓰기 모두 *불능*. 즉시 대응.

대부분 의 *Red* 의 원인 — *disk 의 *full* (95% 임계치 의 *flood-stage* 도달 → ES *read-only* 전환).

### (4) Heap Pressure
*ES 의 *기본 heap 50% of RAM*. 그러나 *32 GB 이상 의 heap 은 *비효율* (compressed pointer 의 한계). *최대 31 GB 의 *heap*. 나머지 는 *Lucene 의 *file cache 로*.

### (5) Heavy GC — *Latency 의 적*
*큰 검색 결과 (수십만 row)* → *큰 heap allocation* → *Major GC* → *Latency 폭증*.

해결 — *scroll API* 또는 *search_after* 의 *cursor 기반 분할*.

```json
POST /logs-*/_search?scroll=1m
{
    "size": 1000,
    "query": { "match_all": {} },
    "sort": [{ "_doc": "asc" }]
}
```

### (6) 06-02 의 *ECK Operator 재시작 사고*

내 클러스터 의 *2026-06-02* — *Hot 노드 의 *디스크 90% 도달 → ES 의 *flood-stage* → *모든 인덱스 *read-only*. ECK Operator 가 *상태 회복 못 함*. 

해결: 
```
1) 디스크 정리 — 오래된 인덱스 수동 삭제
2) flood-stage 해제: PUT /_settings { "index.blocks.read_only_allow_delete": null }
3) ECK Operator 재시작: kubectl rollout restart -n elastic-system deploy/elastic-operator
```

→ ILM 의 *delete phase* 가 *제대로 작동 안 한 *원인 — *Hot tier 에 *오래된 인덱스 가 *남아 있음*. *rollover alias 의 *오설정*.

---

## 10. Kibana — *시각화 의 *대표*

ELK 의 *K*. Logstash + ES 만 으로는 *raw query API* 만 가능. *Kibana 가 *UI + 대시보드 + alerting 의 *통합 환경*.

### Discover — *로그 검색*
*KQL (Kibana Query Language)*:
```
kubernetes.namespace: "sparta-prod" AND level: "ERROR" AND @timestamp >= now-1h
```

→ *최근 1시간 의 *sparta-prod 의 *ERROR 만*.

### Lens — *비주얼라이제이션*
*drag-and-drop* 의 *차트 생성*. *namespace 별 ERROR 수 (line) + 평균 response_time (bar) + pod restart count (gauge)*.

### Alerting (8.x+ 의 *Stack Monitoring*)
*alert rule*:
```
WHEN count(errors) > 100 IN 5m FOR sparta-prod
  → Slack #incident
```

내 클러스터 의 *대시보드 11 개* — *Cluster Overview, Pod CrashLoop, Slow Query, GC Pressure, Disk Usage, ArgoCD Sync Health, ...*.

---

## 11. 검색 성능 — *Query DSL 의 *세계***

```json
GET /sparta-logs-*/_search
{
    "query": {
        "bool": {
            "must": [
                { "match": { "message": "NullPointerException" } },
                { "term": { "kubernetes.namespace": "sparta-prod" } }
            ],
            "filter": [
                { "range": { "@timestamp": { "gte": "now-1h" } } }
            ]
        }
    },
    "aggs": {
        "by_pod": {
            "terms": { "field": "kubernetes.pod_name" }
        }
    },
    "size": 0
}
```

핵심 — **filter vs must**:
- `must` — *score 계산 + 캐싱 안 함*
- `filter` — *score 계산 없음 + cache 가능 → 훨씬 빠름*. *정확 match 는 *항상 filter*.

### Aggregation — *RDB 의 GROUP BY 격*
```json
"aggs": {
    "errors_per_namespace": {
        "terms": { "field": "kubernetes.namespace", "size": 10 },
        "aggs": {
            "by_hour": {
                "date_histogram": { "field": "@timestamp", "interval": "1h" }
            }
        }
    }
}
```

→ *namespace 별 *시간 별 *error 분포*. *Kibana 의 *line chart 의 *기반*.

---

## 12. 마치며 — *작은 결론*

ELK 의 *진짜 가치* 는 *사고 추적 의 *latency*. 06-02 의 *flood-stage 사고* 가 *2시간* 만에 *해결 된 이유* — *Kibana 의 *대시보드* 가 *디스크 의 95% 도달 의 *즉각 신호 + ES 의 *raw API 가 *flood-stage 해제 의 *단일 명령* 의 *경로 명확*.

Logstash 의 *진짜 가치* — *애플리케이션 측 의 *변환 책임 의 *흡수*. *Spring Boot 가 *모든 로그 의 *JSON 화 + trace_id 주입 의 *책임 짐* 또는 *Logstash 가 grok 으로 처리*. 후자 의 *유연성* — *애플리케이션 의 *재배포 없이 *로그 의 *변환 만 추가*.

Elasticsearch 의 *진짜 가치* — *풀텍스트 검색* 의 *압도적 성능*. RDB 의 `LIKE '%foo%'` 가 *Full Scan* 이면 ES 는 *Inverted Index 의 *O(1) ~ O(log n)*. *수억 row 의 *수 ms 검색* 의 *마법*. *log 분석* 만 이 아니라 *e-commerce 의 *검색 + 추천 + 자동완성* 의 *대부분 의 핵심*.

내 클러스터 의 *14개월* — *33 개 도메인 의 *모든 로그 가 *ELK 한 곳* + *7 노드 ES tier* + *Fluent Bit 의 *경량 수집* + *Logstash 의 *유연 한 변환* + *Kibana 의 *대시보드* + *ECK Operator 의 *자동 운영* = *production-grade observability 의 *완성*. *모든 사고 의 *근본 원인 추적* 의 *수 분 내 완료*. 이게 *ELK 의 *진짜 보상*.

---

## 참고

- *Elasticsearch: The Definitive Guide* (공식 — outdated 지만 *원리 의 reference*)
- *Elasticsearch in Action* (Madhusudhan Konda) — *최신*
- *Elastic 공식 문서* — [www.elastic.co/guide](https://www.elastic.co/guide/)
- *Logstash 공식 reference* — [www.elastic.co/guide/en/logstash](https://www.elastic.co/guide/en/logstash/current/index.html)
- *ECK Operator 공식* — [www.elastic.co/guide/en/cloud-on-k8s](https://www.elastic.co/guide/en/cloud-on-k8s/current/index.html)
- 자매편:
    - [데이터베이스 의 본질 — B+Tree 부터 MVCC, Replication 까지](/2026/06/22/database-internals-from-bplus-tree-to-mvcc-replication.html)
    - [DB 설계 와 쿼리 — 14개월 운영 경험 으로 정리한 실전 가이드](/2026/06/29/db-design-and-query-practical-guide.html)
    - [Prometheus 가 어떻게 메트릭 을 수집하고 Grafana 에 시각화하는가](/2026/06/19/prometheus-metrics-collection-and-grafana-visualization.html)
    - [I/O 병목 어떻게 해결하지?](/2026/06/18/io-bottleneck-how-to-solve.html)
