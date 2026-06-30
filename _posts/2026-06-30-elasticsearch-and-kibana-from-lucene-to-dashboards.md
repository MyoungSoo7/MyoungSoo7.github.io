---
layout: post
title: "Elasticsearch 와 Kibana — Lucene 의 segment 부터 Kibana 의 dashboard 까지"
date: 2026-06-30 04:30:00 +0900
categories: [observability, elasticsearch, kibana, lucene]
tags: [elasticsearch, kibana, lucene, segment, refresh, flush, kql, lens, alerting, runtime-field]
---

어제 의 *Logstash + Elasticsearch — Fluent Bit 부터 ILM 까지* 의 *자매 편*. 이번 엔 *Logstash 빼고 *Elasticsearch 의 *내부 mechanics* + *Kibana 의 실무 활용* 의 *2 인 무대*. 내 6 노드 K3s + ELK 운영 의 *14 개월 경험* 중 *어제 글 에 안 들어간 *깊은 부분* 의 집중.

---

## 1. Elasticsearch 의 *진짜 정체* — *분산 Lucene*

Elasticsearch 는 *처음 부터 만든 검색 엔진 이 아니다*. *Apache Lucene 의 *분산 wrapper*. Lucene 은 *Doug Cutting 이 1999 부터 개발* 한 *Java 의 *full-text search 라이브러리*. Elasticsearch (2010) 는 *Lucene 의 *index 를 *shard 로 *분산 + REST API + cluster 운영* 의 *layer 추가*.

```
Elasticsearch Cluster
├── Node 1 (master + data hot)
│   ├── Index "logs-2026.06.30"
│   │   ├── Shard 0 (primary)
│   │   │   └── Lucene Index
│   │   │       ├── Segment 0 (immutable)
│   │   │       ├── Segment 1
│   │   │       └── Segment N
│   │   └── Shard 1 (primary)
│   └── Index "products"
│       └── Shard 0 (replica)
├── Node 2 (data warm)
└── Node N
```

핵심 단어:
- **Index** — RDB 의 *DB* 격. *논리 적 묶음*.
- **Shard** — *index 의 *물리 적 분할*. *각 shard 가 *완전 한 Lucene index*.
- **Segment** — *Lucene 의 *최소 저장 단위*. *immutable*.
- **Replica** — *primary shard 의 *복제*. *HA + read 분산*.

---

## 2. Segment — *Lucene 의 *심장*

ES 의 *write 의 *비밀* — *append-only*.

```
Write 흐름:
  1) Doc 도착 → In-Memory Buffer
  2) 1 초 마다 (refresh_interval) → 새 segment 로 *디스크 flush* + *open*
  3) 5 초 마다 (translog fsync) → translog 영구 화
  4) 30 분 / 512MB 마다 (flush) → translog 비움
  5) 백그라운드 → segment 병합 (merge)
```

### Segment 의 *불변성*
한 번 만들어진 segment 는 *수정 불가*. *update 는 *기존 doc *삭제 (tombstone) + 새 doc *추가*. *delete 도 *tombstone 만 추가* — 실 데이터 *남아 있음*.

→ **Force Merge** 또는 *background merge* 가 *tombstone + 작은 segment* 를 *정리*.

```bash
# 수동 force merge
POST /logs-2026.06.01/_forcemerge?max_num_segments=1
```

⚠️ *production 의 *hot index 에 *force merge 금지* — *I/O 폭증 + CPU 소진*. *ILM 의 warm phase 의 *background 작업* 으로 *자동화*.

### Translog — *crash 의 *방어*
*in-memory buffer 의 데이터 가 *segment 가 되기 전* 에 *crash 발생 시 *유실*. 방지 — *모든 write 가 *translog 에 *동시 기록*.

```yaml
index.translog.durability: request   # 매 request 마다 fsync (느림 + 안전)
# 또는
index.translog.durability: async     # 비동기 fsync (빠름 + 위험)
```

*default = request*. *5 초 마다 fsync* — *최악 의 경우 5 초 의 *데이터 유실 가능*.

### Refresh vs Flush vs Commit
헷갈리기 쉬운 *3 가지*:
- **Refresh** — *in-memory buffer → 새 segment 생성 + 검색 가능*. *기본 1 초 마다*.
- **Flush** — *translog 비움 + Lucene commit*. *기본 30 분 / 512MB 마다*.
- **Lucene Commit** — *segment 의 *영구 화 (fsync)*.

→ *refresh = 검색 가능 시점*, *flush = 디스크 영구 화 시점*. *둘 의 *분리* 가 *성능 의 핵심*.

---

## 3. Shard 수 — *영원 한 고민*

새 index 생성 시 *가장 어려운 결정*:

```json
PUT /logs-2026.06.30
{
    "settings": {
        "number_of_shards": 3,
        "number_of_replicas": 1
    }
}
```

### Shard 수 의 *trade-off*
- **너무 적음** (예: 1) — *write 의 *single point 부하*, *큰 segment*, *re-shard 불가능*
- **너무 많음** (예: 50) — *master 의 *heartbeat 폭증*, *각 shard 의 *고정 overhead (수 MB heap)*, *작은 segment 의 *비효율*

### *권장*
- *각 shard 의 *목표 크기 — 10~50 GB*
- *총 shard 수 = ceil(index 의 *예상 최종 크기 / 30GB)*
- *예시*: 1일 100GB log → 3 shard / 일
- *replica 1* (HA + read 분산)
- **node 당 *최대 shard 수 — 500~1000* 이내** (heap 의 *고정 overhead 계산*)

### *Re-sharding 의 *지옥*
*number_of_shards 는 *한 번 정 하면 변경 불가*. 변경 = *새 index + reindex API*:

```bash
POST /_reindex
{
    "source": { "index": "logs-old-shard-1" },
    "dest":   { "index": "logs-new-shard-5" }
}
```

→ *수십 GB 의 *수 시간*. *처음 설계 의 *시간 투자* 가 *수년 의 *부채 회피*.

---

## 4. Replica — *HA + 부하 분산*

```json
"number_of_replicas": 1
```

각 *primary shard 의 *복제*. *primary 가 *node 1*, *replica 가 *node 2* 에 *자동 배치*. *동일 node 에 *primary + replica 배치 불가* (HA 보장).

### Replica 의 *3 가지 역할*
1. **HA** — *primary node 의 *fail 시 *replica 가 *primary 로 승격*
2. **Read 분산** — *search / get 의 *primary + replica 중 *load balancing*
3. **Refresh 부담 공유** — *replica 도 *동일 한 refresh 받음 → 검색 일관성*

### *replica 0 의 위험*
- *node 1 의 *fail 시 → *해당 shard 의 *primary 영구 손실*
- *backup 이 없으면 *복구 불가*
- → *production 의 *모든 hot index 는 *replica >= 1 의무*

→ warm / cold tier 는 *cost 절감 위해 replica 0 가능* (Velero / snapshot 으로 backup).

---

## 5. Index Template — *반복 의 *제거*

새 index 가 *매일 자동 생성* 되는 경우 (log) — *각 index 마다 *수동 mapping* 의 *지옥*. 해결 — **Index Template**.

```json
PUT /_index_template/logs-template
{
    "index_patterns": ["logs-*"],
    "priority": 100,
    "template": {
        "settings": {
            "number_of_shards": 3,
            "number_of_replicas": 1,
            "index.lifecycle.name": "logs-policy",
            "index.lifecycle.rollover_alias": "logs"
        },
        "mappings": {
            "properties": {
                "@timestamp": { "type": "date" },
                "level": { "type": "keyword" },
                "message": {
                    "type": "text",
                    "fields": { "raw": { "type": "keyword" } }
                },
                "kubernetes.namespace": { "type": "keyword" },
                "trace_id": { "type": "keyword" }
            }
        }
    }
}
```

→ *logs-2026.06.30* 새 index 가 *생기면 *자동 으로 *이 template 적용*. *수동 작업 0*.

### Component Template — *재사용*
*공통 부분* 을 *component 로 분리*:

```json
PUT /_component_template/k8s-fields
{
    "template": {
        "mappings": {
            "properties": {
                "kubernetes.namespace": { "type": "keyword" },
                "kubernetes.pod_name": { "type": "keyword" }
            }
        }
    }
}

PUT /_index_template/logs-template
{
    "index_patterns": ["logs-*"],
    "composed_of": ["k8s-fields", "common-timestamp"],
    "template": { ... }
}
```

→ *DRY 원칙* 의 ES 적용.

---

## 6. Runtime Field — *2021 의 *큰 변화*

ES 7.11 (2021) 부터 — *index 에 *없는 field* 를 *query 시 *계산*.

```json
GET /logs-*/_search
{
    "runtime_mappings": {
        "response_time_seconds": {
            "type": "double",
            "script": {
                "source": "emit(doc['response_time_ms'].value / 1000.0)"
            }
        }
    },
    "query": {
        "range": { "response_time_seconds": { "gte": 1.0 } }
    }
}
```

→ *기존 데이터 재 인덱싱 없이 *새 field 의 *추가 + 검색*. *prototype 의 *극도 의 빠름*.

⚠️ **함정** — *runtime field 는 *index 안 됨* → *느림*. *최종 적 으로 *index 화 의 *재 인덱싱 권장*.

### Painless Script — *ES 의 *DSL*
*Java 와 비슷 한 문법* + *script injection 안전*:

```json
"script": {
    "source": """
        if (doc['status'].value >= 500) {
            emit('server-error')
        } else if (doc['status'].value >= 400) {
            emit('client-error')
        } else {
            emit('ok')
        }
    """
}
```

---

## 7. Aggregation — *RDB 의 GROUP BY 의 *극단*

ES 의 *진짜 강점* — *수억 row 의 *그룹화 + 집계 가 *수 ms*.

```json
GET /logs-*/_search
{
    "size": 0,
    "query": { "range": { "@timestamp": { "gte": "now-1h" } } },
    "aggs": {
        "by_namespace": {
            "terms": { "field": "kubernetes.namespace", "size": 10 },
            "aggs": {
                "avg_response": {
                    "avg": { "field": "response_time_ms" }
                },
                "p95_response": {
                    "percentiles": {
                        "field": "response_time_ms",
                        "percents": [95, 99]
                    }
                },
                "errors": {
                    "filter": { "term": { "level": "ERROR" } }
                }
            }
        }
    }
}
```

→ *namespace 별 *평균 / p95 / p99 / error count* 의 *단일 query*.

### Bucket vs Metric
- **Bucket aggregation** — *그룹 만들기* (terms, date_histogram, range)
- **Metric aggregation** — *값 계산* (avg, sum, percentiles, cardinality)

### Cardinality — *근사 distinct count*
*HyperLogLog 기반*. *수억 row 의 *고유 값 카운트* 가 *수 ms + 정밀도 ±0.5%*:

```json
"unique_users": {
    "cardinality": { "field": "user_id", "precision_threshold": 1000 }
}
```

`precision_threshold` — *낮을 수록 *메모리 절감 + 정밀도 하락*.

### Pipeline Aggregation — *집계 의 *집계*
```json
"aggs": {
    "by_hour": {
        "date_histogram": { "field": "@timestamp", "interval": "1h" },
        "aggs": {
            "errors_per_hour": { "filter": { "term": { "level": "ERROR" } } },
            "error_diff": {
                "derivative": { "buckets_path": "errors_per_hour._count" }
            }
        }
    }
}
```

→ *시간 별 error 증감 (1 차 미분)*. *spike detection 의 *기반*.

---

## 8. Kibana — *ES 의 *얼굴*

Kibana 는 *ES 의 *Web UI*. 그러나 *단순 UI 가 아니라 *6 개 의 *큰 영역*:

1. **Discover** — *raw log 탐색*
2. **Visualize / Lens** — *차트 생성*
3. **Dashboard** — *차트 의 *조합*
4. **Maps** — *지리 데이터*
5. **Alerting** — *조건 기반 알림*
6. **Stack Management** — *index / template / ILM 관리*

내 *11 개 운영 대시보드* 의 *기반*.

---

## 9. Kibana — Discover (탐색)

*가장 자주 쓰는 화면*. *log 의 *raw 검색*.

### KQL (Kibana Query Language)
```
kubernetes.namespace : "sparta-prod" 
  and level : "ERROR"
  and response_time_ms > 1000
  and @timestamp >= now-1h
```

→ *직관 적*. *Spring Boot 의 *@Query DSL* 의 *느낌*.

### Lucene Query (옵션)
*고급 query* 가 필요 하면 *KQL toggle off*:
```
message:"NullPointerException" AND _exists_:user_id
```

### Saved Search — *재사용*
*자주 쓰는 query* 의 *저장*. *대시보드 에 *embed 가능*. *모든 *team 멤버* 가 *공유*.

### Field 별 *상위 값 분석*
*왼쪽 사이드 의 *field 클릭* → *해당 field 의 *상위 값 + 분포*. *namespace 별 log 비율* 같은 *즉각 분석*.

---

## 10. Kibana — Lens (시각화)

*Kibana 7.10 부터*. *drag-and-drop 차트 생성*. *과거 의 *Visualize 의 *복잡 함* 제거.

### 기본 흐름
1. *index pattern 선택* (예: `logs-*`)
2. *field 를 *drag → x-axis / y-axis / breakdown*
3. *차트 타입 자동 추천*
4. *suggestions 패널 의 *대안 시각화* 즉시 비교

### 예시 — *namespace 별 *시간 별 *error count*
```
X-axis: @timestamp (1h bucket)
Y-axis: count of records
Breakdown: kubernetes.namespace (top 5)
Filter: level = "ERROR"
```

→ *5 줄 의 *설정* → *line chart 자동 생성*.

### Formula — *계산 컬럼*
```
( count(kql='level:ERROR') / count() ) * 100
```

→ *error rate (%)*. *Lens 의 *runtime field 와 동등*.

---

## 11. Kibana — Dashboard (조합)

여러 *Lens 차트 + Saved Search + Maps* 를 *한 화면 에 조합*.

### 내 *11 개 대시보드*
| 이름 | 차트 수 | 갱신 |
|---|---|---|
| **Cluster Overview** | 12 | 5 분 |
| **Pod CrashLoop** | 8 | 1 분 |
| **Slow Query** | 6 | 5 분 |
| **GC Pressure** | 9 | 5 분 |
| **Disk Usage** | 7 | 30 분 |
| **ArgoCD Sync** | 5 | 1 분 |
| **Velero Backup** | 4 | 60 분 |
| **Cert-Manager** | 3 | 1 일 |
| **Sparta MSA Trace** | 14 | 1 분 |
| **Settlement KPI** | 18 | 5 분 |
| **lemuel-xr Audit** | 10 | 5 분 |

→ *대부분 의 *진단* 이 *대시보드 의 *3~5 차트 의 *조합* 에서 *즉시 보임*.

### Cross-Dashboard 의 *Drilldown*
*pod CrashLoop 대시보드* 에서 *특정 pod 클릭* → *해당 pod 의 *log 탐색 화면* 으로 *자동 이동 + filter 자동 설정*. *디버깅 의 *시간 절감*.

### Time Range — *전역 의 *기본*
*대시보드 우측 상단 의 *time picker*. *모든 차트 에 *자동 적용*. *now-15m*, *now-1h*, *2026-06-20 00:00 ~ 2026-06-30 23:59* 등.

---

## 12. Kibana — Alerting (Rules)

*조건 기반 알림*. *7.x 부터 *built-in*.

```yaml
# 예시 — ERROR 폭증
Rule type: Elasticsearch query
Index pattern: logs-*
Query: { "bool": { "must": [{ "term": { "level": "ERROR" } }] } }
Aggregation type: count
Threshold: > 100 for last 5m
Schedule: every 1m

Actions:
  - Slack #incident
  - Email iamipro@naver.com
  - Webhook to Telegram bot
```

### Multi-condition
```
WHEN count > 100 
  AND avg(response_time_ms) > 1000
  AND group by kubernetes.namespace
```

→ *namespace 별 *동시 조건*. *Prometheus Alertmanager 와 *동등*.

### Snooze / Mute
*alert 의 *일시 정지*. *배포 시간 의 *false positive 방지*.

내 클러스터 의 *Velero 백업 시간 (04:00~04:30)* — *backup 중 의 *disk I/O 폭증* 의 *알림 mute*.

---

## 13. Kibana — Maps (지리)

GeoIP 기반 *지도 시각화*. *Nginx access log 의 *IP → 위치* 의 *세계 지도 분포*.

```json
"geoip": {
    "type": "geo_point"
}
```

Logstash 의 `geoip` filter:
```ruby
geoip { source => "client_ip" }
```

→ *Kibana Maps 에서 *cluster + heatmap + choropleth*.

내 클러스터 의 *vault.lemuel.co.kr* 접속 *지리 분포* — *대부분 한국 + 일부 미국 + 중국 의 *공격 시도 (Cloudflare 가 차단)*.

---

## 14. Saved Objects — *Kibana 의 *모든 자산*

*Discover saved search / Lens 차트 / Dashboard / Alert / Map* 등 — *모두 *Saved Object*.

```bash
# Export
curl -X POST "http://kibana:5601/api/saved_objects/_export" \
  -H 'kbn-xsrf: true' \
  -H 'Content-Type: application/json' \
  -d '{"type": "dashboard"}' > dashboards.ndjson

# Import (다른 환경 에)
curl -X POST "http://kibana:5601/api/saved_objects/_import?overwrite=true" \
  -H 'kbn-xsrf: true' \
  --form file=@dashboards.ndjson
```

→ *git 으로 *대시보드 버전 관리*. *staging / production 의 *동기화*.

### Kibana Spaces — *멀티 테넌트*
*같은 ES 위 의 *여러 Kibana 인스턴스* (논리 적). *팀 별 격리*:
- `default` — *모든 운영*
- `dev` — *개발 환경*
- `audit` — *감사 / 보안 팀*

각 space 가 *별도 의 dashboard + role*. *권한 분리*.

---

## 15. Index Lifecycle Management (ILM) — *Kibana UI*

*어제 의 글 에서 *JSON policy* 를 다뤘지만 — *Kibana UI 가 *훨씬 직관*.

`Stack Management → Index Lifecycle Policies`:
1. *phase 별 *설정 (hot / warm / cold / delete)
2. *조건 (size / age) 시각 적 설정*
3. *각 phase 의 *action (allocate / forcemerge / freeze) 의 *체크박스*
4. *수동 mapping 없이 *완료*

→ *production 의 *현실 적 운영* 의 *핵심 도구*.

---

## 16. 운영 함정 — *내 14 개월*

### (1) Watermark 의 *3 단*
ES 의 *디스크 보호*:
- **low** (85%) — *새 shard 할당 중단*
- **high** (90%) — *기존 shard 다른 노드 로 이동*
- **flood-stage** (95%) — *모든 index *read-only 전환*

2026-06-02 사고 — *Hot 노드 의 *95% 도달* → *모든 새 write 차단*. 회복 — *오래된 index 수동 삭제* + 
```bash
PUT /_settings
{ "index.blocks.read_only_allow_delete": null }
```

### (2) Mapping 폭증
*Spring Boot 의 *예외 객체 의 *모든 field 가 *dynamic mapping* → *수천 개 field* → *디스크 폭증*.

해결 — *strict mapping* + *index.mapping.total_fields.limit: 1000*.

### (3) Heap 의 *31 GB 의 *벽*
*ES 의 heap > 31GB* → *Java 의 *compressed pointer 비활성화* → *오히려 *느려짐*. *최대 31 GB 권장*.

```yaml
# elasticsearch.yml
ES_JAVA_OPTS: "-Xms31g -Xmx31g"
```

### (4) Hot Threads — *진단 의 *비밀 무기*
```bash
GET /_nodes/hot_threads
```

→ *CPU 사용 률 의 *상위 스레드*. *어떤 query 가 *CPU 소진 중* 의 *즉시 진단*.

### (5) Pending Tasks
```bash
GET /_cluster/pending_tasks
```

→ *master 의 *대기 작업*. *큰 mapping update / shard relocation* 의 *적체*.

### (6) Backup — *Snapshot Repository*
```bash
# Cloudflare R2 + S3 compatibility
PUT /_snapshot/r2-backup
{
    "type": "s3",
    "settings": {
        "bucket": "lemuel-es-snapshots",
        "endpoint": "<account>.r2.cloudflarestorage.com",
        "region": "auto"
    }
}

# Daily snapshot
PUT /_snapshot/r2-backup/snap-2026-06-30
{
    "indices": "logs-*,products,users",
    "include_global_state": false
}
```

내 클러스터 의 *R2 자동 백업* 의 *기반*.

---

## 17. 마치며 — *14 개월 의 *작은 결론*

Elasticsearch 의 *진짜 가치* — *Lucene 의 *segment + inverted index 의 *수십 년 의 *최적화* 위에 *분산 + REST + cluster 운영 의 *layer*. *직접 Lucene 을 *touch 하지 않아도 *production 의 *모든 검색 / 집계 요구* 의 *대부분 의 답*.

Kibana 의 *진짜 가치* — *코드 없이 *시각화 / 알림 / 탐색 의 *완전 한 도구*. *데이터 엔지니어 가 *없는 *백엔드 1 인 팀* 도 *production-grade observability 의 *구축 가능*. 내 *11 개 운영 대시보드* 가 *그 증거*.

ES + Kibana 의 *조합 의 *핵심 메시지*:
- **Schema-on-read 의 *유연성*** — *log 의 *구조 변화 에 *robust*
- **Aggregation 의 *압도적 성능*** — *수억 row 의 *그룹화 가 *수 ms*
- **Real-time 의 *진짜 의미*** — *refresh 1 초 후 *검색 가능*
- **운영 도구 의 *성숙*** — *14 년 의 *production 사용* 의 *누적 노하우*

이게 *Cloudflare Logpush / Splunk / Datadog / Loki* 같은 *대안 들 의 *압도* 의 *이유*. *오픈 소스 + 성숙 도 + 생태계* 의 *완성*.

내가 *14 개월 운영* 하면서 *체득* 한 *작은 결론* — *ES 는 *처음 의 *설계 (shard 수 + mapping + template + ILM)* 의 *시간 투자* 가 *수년 의 *부채 회피*. *수동 운영* 의 *시간* 보다 *자동화 의 *시간* 의 *압도적 우위*.

---

## 참고

- *Elasticsearch: The Definitive Guide* (1st ed. — outdated 지만 *원리 의 reference*)
- *Elasticsearch in Action* (Madhusudhan Konda, 2023) — *최신*
- *Lucene in Action* (Erik Hatcher, 2010) — *Lucene 내부 의 *유일 한 완성 본*
- *Elastic 공식 문서* — [www.elastic.co/guide](https://www.elastic.co/guide/)
- *Kibana 공식 reference* — [www.elastic.co/guide/en/kibana](https://www.elastic.co/guide/en/kibana/current/index.html)
- 자매편:
    - [Logstash 와 Elasticsearch — Fluent Bit 파이프라인 부터 ILM 까지](/2026/06/29/logstash-and-elasticsearch-from-fluent-bit-to-ilm.html)
    - [데이터베이스 의 본질 — B+Tree 부터 MVCC, Replication 까지](/2026/06/22/database-internals-from-bplus-tree-to-mvcc-replication.html)
    - [DB 설계 와 쿼리 — 14 개월 운영 경험](/2026/06/29/db-design-and-query-practical-guide.html)
    - [Prometheus 가 어떻게 메트릭 을 수집하고 Grafana 에 시각화하는가](/2026/06/19/prometheus-metrics-collection-and-grafana-visualization.html)
