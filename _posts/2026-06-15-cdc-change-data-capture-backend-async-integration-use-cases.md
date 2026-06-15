---
layout: post
title: "*백엔드 비동기 연동의 *CDC (Change Data Capture)* 완전 가이드 — *WAL / binlog 작동 원리 / Debezium 구현 / 자주 쓰는 사례 7 가지 + 실전 postmortem 4 건***"
date: 2026-06-15 16:00:00 +0900
categories: [backend, distributed-system, msa, cdc, kafka]
tags: [cdc, change-data-capture, debezium, kafka-connect, wal, binlog, replication, elasticsearch, redis-cache-invalidation, data-warehouse, event-sourcing, msa]
---

이 글은 *백엔드 / MSA / 데이터 파이프라인* 에서 *데이터베이스 변경을 *실시간으로 *다른 시스템 으로 *전파* 하는 *CDC (Change Data Capture)* 의 *원리 + 자주 쓰는 사례 7 가지 + 실전 postmortem* 을 *깊이* 정리한다. *WAL / binlog / oplog 의 *내부 작동* / *Debezium 구현* / *Outbox + CDC 조합* 까지.

전 글 ([트랜잭션 + Outbox 패턴 + 비동기 연동](/2026/06/15/transaction-outbox-pattern-async-integration-deep-dive/)) 의 *후속 deep-dive*. *CDC 는 *비동기 연동의 *대규모 진입로* — *왜 *대기업 *데이터 파이프라인 / MSA 가 *전부 CDC 로 가는지* 의 *진짜 이유*.

읽고 가셔도 좋은 분:
1. *Outbox + Poller 구조 가 *DB 부하* 로 *한계* 에 부딪힌 백엔드
2. *MSA 데이터 동기화 / 캐시 무효화 / ES 인덱싱* 을 *수동 API 호출 로 *처리 중인 팀
3. *Data Warehouse / Lake* 로 *데이터를 매시간 ETL* 하다가 *실시간 needs* 가 생긴 분석팀
4. *이벤트 소싱 / CQRS* 의 *현실적 구현 방법* 이 *애매한* 사람

---

## TL;DR

> *CDC 는 *애플리케이션 코드 변경 없이 *DB 의 *WAL / binlog* 을 *읽어서 *변경 이벤트로 *Kafka 등에 발행* 하는 패턴. *Debezium 이 *2026 년 표준*. *Outbox poller 의 *DB 부하 부담 없음* + *수 ms latency* + *애플리케이션 무관* 의 *3 가지 강력한 이점*. *MSA 데이터 동기화 / Redis 캐시 무효화 / ES 색인 / Data Warehouse / 감사 로그 / 이벤트 소싱 / Search 트리거* 의 *7 대 사례* 가 *전부 CDC 로 수렴 중*.

**한 그림으로**:

```
[PostgreSQL]
    │
    ├── Application INSERT/UPDATE/DELETE
    │      ↓
    └── WAL (Write-Ahead Log)
           ↓ logical replication slot
           ↓
[Debezium Connector]
           ↓ Kafka Connect
           ↓
[Kafka Topic: db_changes.public.orders]
           │
   ┌───────┼────────┬─────────┬──────────┐
   ▼       ▼        ▼         ▼          ▼
[ES Index] [Redis] [DataWH] [감사 로그] [MSA 알림]
```

---

## 0. *CDC 가 *왜 *나왔는가***

### 0.1 *기존 방식 — *Polling / Trigger / Dual Write***

| 방식 | 문제점 |
|------|--------|
| **Polling** | DB 부하 (반복 SELECT) + latency (poll 간격) |
| **DB Trigger** | DB 의존 + 디버깅 지옥 + 트랜잭션 분산 |
| **Dual Write** | *원자성 깨짐* (전 글 [Outbox 가이드](/2026/06/15/transaction-outbox-pattern-async-integration-deep-dive/) 참고) |
| **API 호출** | 결합도 폭증 + 서비스 다운 시 영향 전파 |
| **Outbox + Poller** | DB 부하 (poll 의 *주기 SELECT*) + latency (2-5 초 권장) |

### 0.2 *CDC 의 *접근***

> *DB 자체가 *이미 *모든 변경* 을 *WAL / binlog 에 *기록 중*. *그 로그를 *그냥 읽으면 된다*. 애플리케이션 코드 변경 X. DB 추가 부하 거의 0 (replication 이미 *돌고 있는 기능 재활용*).

---

## 1. *CDC 의 *원리 — *WAL / binlog / oplog***

### 1.1 *PostgreSQL — *WAL (Write-Ahead Log)***

```
[Transaction]
    INSERT INTO orders (...) VALUES (...);
       ↓
[WAL Buffer]
    LSN 0/1234567: INSERT public.orders ...
       ↓ commit
[WAL Segment File]
    pg_wal/000000010000000000000001
       ↓ (logical replication slot 통해 외부 노출)
[Debezium PostgreSQL Connector]
    pgoutput / wal2json plugin 으로 디코딩
       ↓
[Kafka Topic]
```

*PostgreSQL 설정*:
```ini
# postgresql.conf
wal_level = logical                    # ★ logical replication 활성화
max_wal_senders = 10
max_replication_slots = 10
```

```sql
-- Debezium 이 자동 생성하는 replication slot
SELECT * FROM pg_create_logical_replication_slot('debezium', 'pgoutput');

-- Publication 정의 (어느 테이블 추적할지)
CREATE PUBLICATION dbz_publication FOR TABLE orders, payments, settlements;
```

### 1.2 *MySQL — *binlog***

```
[Transaction]
    UPDATE payments SET status = 'CAPTURED' WHERE id = 123;
       ↓
[binlog]
    Event: UPDATE_ROWS_EVENT
    Table: payments
    Before: { id: 123, status: 'AUTHORIZED' }
    After:  { id: 123, status: 'CAPTURED' }
       ↓
[Debezium MySQL Connector]
    binlog 디코딩 (ROW 포맷)
       ↓
[Kafka Topic]
```

*MySQL 설정*:
```ini
# my.cnf
server-id = 1
log_bin = mysql-bin
binlog_format = ROW                    # ★ ROW (필수, STATEMENT 안 됨)
binlog_row_image = FULL                # ★ before + after 모두
expire_logs_days = 7
```

### 1.3 *MongoDB — *oplog***

```javascript
// MongoDB replica set 의 oplog 컬렉션
db.oplog.rs.find({}).sort({ts: -1}).limit(5)
// {
//   "ts": Timestamp(...), 
//   "op": "u",                          // u=update, i=insert, d=delete
//   "ns": "shop.orders",
//   "o": { "$set": { "status": "PAID" }},
//   "o2": { "_id": ObjectId("...") }
// }
```

*Debezium MongoDB Connector* 는 *change stream* 을 사용 (oplog 직접 읽음).

### 1.4 *작동의 *핵심 통찰***

> *CDC 는 *새로운 기술 아님*. *DB 가 *수십 년 전부터 *복제 (replication) 를 위해 *이미 만들어 둔 로그* 를 *재활용*. 그래서 *DB 추가 부하 거의 0*, *latency 수 ms*.

---

## 2. *Debezium — *CDC 의 *de facto 표준***

### 2.1 *아키텍처*

```
┌──────────────────────────────────────────────┐
│         Kafka Connect Cluster (분산)          │
│  ┌────────────────────────────────────────┐  │
│  │  Debezium Source Connector              │  │
│  │  (PostgreSQL / MySQL / MongoDB / ...)   │  │
│  └────────────────────────────────────────┘  │
└──────────────────────────────────────────────┘
              ↓ ↑                ↓
        [DB WAL]          [Kafka Brokers]
                          ↓
                   ┌──────┼──────┐
                   ▼      ▼      ▼
                 Topic  Topic  Topic
                 (테이블별 1 토픽)
```

### 2.2 *지원 DB*

| DB | Status |
|----|--------|
| PostgreSQL | ★ Production |
| MySQL | ★ Production |
| MongoDB | ★ Production |
| SQL Server | ★ Production |
| Oracle | Production (LogMiner) |
| Db2 | Production |
| Cassandra | Incubating |

### 2.3 *Debezium PostgreSQL Connector 설정*

```json
{
  "name": "lemuel-postgres-connector",
  "config": {
    "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
    "database.hostname": "postgres.lemuel.svc",
    "database.port": "5432",
    "database.user": "debezium",
    "database.password": "${secret:debezium-pw}",
    "database.dbname": "lemuel",
    "database.server.name": "lemuel-prod",
    "plugin.name": "pgoutput",
    "publication.name": "dbz_publication",
    "slot.name": "debezium_slot",
    
    "table.include.list": "public.orders,public.payments,public.settlements",
    
    "topic.prefix": "lemuel.cdc",
    
    "key.converter": "org.apache.kafka.connect.json.JsonConverter",
    "value.converter": "org.apache.kafka.connect.json.JsonConverter",
    
    "snapshot.mode": "initial",
    "tombstones.on.delete": "true",
    
    "transforms": "unwrap",
    "transforms.unwrap.type": "io.debezium.transforms.ExtractNewRecordState",
    "transforms.unwrap.drop.tombstones": "false"
  }
}
```

### 2.4 *발행되는 메시지 예시*

```json
{
  "before": {
    "id": 12345,
    "status": "AUTHORIZED",
    "amount": 50000
  },
  "after": {
    "id": 12345,
    "status": "CAPTURED",
    "amount": 50000
  },
  "source": {
    "version": "2.7.0",
    "connector": "postgresql",
    "name": "lemuel-prod",
    "ts_ms": 1717238400000,
    "db": "lemuel",
    "schema": "public",
    "table": "payments",
    "txId": 98765,
    "lsn": 1234567890
  },
  "op": "u",
  "ts_ms": 1717238400123
}
```

---

## 3. *자주 쓰는 사례 7 가지*

### 3.1 *Case A — *MSA 데이터 동기화***

> *서비스 A 의 *DB 변경을 *서비스 B 가 *알아야 할 때*. API 호출 대신 CDC.

```
[Order Service DB]
    UPDATE orders SET status = 'PAID' WHERE id = 123;
        ↓ WAL
[Debezium]
        ↓
[Kafka: lemuel.cdc.public.orders]
        ↓
[Settlement Service]   [Inventory Service]   [Notification Service]
   ↓                       ↓                      ↓
정산 생성              재고 감소               알림 발송
```

**왜 좋은가**:
- Order Service 가 *다른 서비스의 존재 모름* (디커플링)
- *새 consumer 추가 시 *Order Service 코드 변경 X*
- 서비스 다운 시 *Kafka 가 버퍼* — *데이터 누락 X*

### 3.2 *Case B — *Redis 캐시 무효화***

> *DB 변경 즉시 *Redis 캐시* 갱신/삭제.

```
[Product DB]
    UPDATE products SET price = 12000 WHERE id = 5;
        ↓ WAL
[Debezium]
        ↓
[Kafka: lemuel.cdc.public.products]
        ↓
[Cache Invalidator Consumer]
        ↓
    Redis DEL product:5
    또는
    Redis SET product:5 {new data}
```

**기존 방식의 문제**:
```java
// ❌ — 캐시 무효화 누락 사고
@Transactional
public void updatePrice(Long id, int price) {
    productRepo.updatePrice(id, price);   // DB 갱신
    // Redis 무효화 빠뜨림 → *오래된 가격이 *영원히 캐시*
}
```

**CDC 의 *장점***:
- *모든 INSERT/UPDATE/DELETE 가 *자동 캐치*
- 개발자가 *캐시 무효화 잊어도 안전*

### 3.3 *Case C — *Elasticsearch 색인***

> *상품 / 게시글 / 검색 데이터를 *DB 변경 즉시 *ES 에 색인*.

```
[Products DB]
    INSERT INTO products (...) VALUES (...);
        ↓
[Debezium]
        ↓
[Kafka: lemuel.cdc.public.products]
        ↓
[ES Indexer Consumer]
        ↓
    PUT /products/_doc/{id}
    { "name": "...", "price": ..., "tags": [...] }
```

**대안 (Elastic 의 Logstash JDBC input plugin)** 대비 *장점*:
- *Logstash JDBC = *Polling 기반* (DB 부하)
- *CDC = *Push 기반* (DB 부하 거의 0)

### 3.4 *Case D — *Data Warehouse / Lake 실시간 ETL***

> *OLTP DB → OLAP (Snowflake / BigQuery / S3) 로 *데이터 이동*.

```
[OLTP PostgreSQL]
        ↓ CDC
[Debezium]
        ↓
[Kafka]
        ↓
[Kafka Connect Sink Connector]
        ↓
[Snowflake / BigQuery / S3 Iceberg]
        ↓
[Analytics / BI Dashboard]
```

**기존 방식 (매일 새벽 ETL Batch)** 대비:
- 실시간 분석 가능 (latency 분 단위)
- 배치 윈도우 *DB 부하 폭증 없음* (CDC 는 *지속적 스트림*)

### 3.5 *Case E — *감사 로그 (Audit Log)***

> *모든 DB 변경을 *불변 로그로 기록*. *컴플라이언스 / 보안*.

```
[모든 변경]
        ↓
[CDC Stream]
        ↓
[Kafka: cdc.audit]
        ↓
[S3 Audit Bucket (immutable)]
        ↓
   분석 / 감사 / 컴플라이언스
```

**기존 방식 (Application 측 로깅)** 대비:
- *코드 변경 / 누락 위험 X*
- *우회 불가능* (직접 DB INSERT 도 캐치)
- 금융 / 의료 *컴플라이언스 강제* 가능

### 3.6 *Case F — *이벤트 소싱 / CQRS***

> *Read Model 을 *Write Model 의 *변경으로 자동 갱신*.

```
[Write Model — 트랜잭션 DB]
    Order INSERT / UPDATE
        ↓ CDC
[Kafka]
        ↓
[Read Model Builder]
        ↓
[Read DB — 비정규화된 빠른 조회용]
    Materialized View / Denormalized Table
```

### 3.7 *Case G — *Search / Recommendation 트리거***

> *상품 등록 / 사용자 행동* 변경 시 *추천 엔진 재계산*.

```
[User Activity DB]
        ↓ CDC
[Kafka]
        ↓
[ML Pipeline]
        ↓
    Feature Store 업데이트
    추천 모델 retrain trigger
```

---

## 4. *Outbox + CDC 조합 (★ 최강)*

### 4.1 *왜 *Outbox + CDC 가 *완벽한가***

```
[Producer 서비스]
  @Transactional
    DB 변경
    outbox_events INSERT       ← 비즈니스 의미 명확한 이벤트
       ↓ commit
[PostgreSQL WAL]
       ↓
[Debezium]                     ← Poller 대신 WAL 직접 읽음
       ↓
[Kafka Topic]                  ← outbox 테이블의 각 row 가 1 메시지
       ↓
[Consumer]
```

### 4.2 *순수 CDC (테이블 직접 추적) 와의 차이*

| 항목 | 순수 CDC | Outbox + CDC |
|------|---------|--------------|
| 발행 이벤트 의미 | DB 변경 (INSERT/UPDATE/DELETE) | 비즈니스 이벤트 (OrderCreated, PaymentCaptured) |
| 스키마 변경 영향 | Consumer 깨짐 | Outbox payload 안정 |
| 여러 row 합친 이벤트 | 불가능 (테이블 1개당) | 가능 (1 outbox row 에 표현) |
| 1 이벤트 = N 토픽 | 어려움 | event_type 따라 분배 |
| 마이그레이션 | 어려움 (스키마 = 계약) | 쉬움 (outbox 형식 유지) |

> *대규모 MSA 의 *2026 년 표준 = *Outbox + Debezium CDC 조합*.

### 4.3 *Debezium 의 *Outbox Event Router 변환기***

```json
{
  "transforms": "outbox",
  "transforms.outbox.type": "io.debezium.transforms.outbox.EventRouter",
  "transforms.outbox.route.by.field": "aggregate_type",
  "transforms.outbox.route.topic.replacement": "lemuel.${routedByValue}",
  "transforms.outbox.table.field.event.id": "event_id",
  "transforms.outbox.table.field.event.key": "aggregate_id",
  "transforms.outbox.table.field.event.payload": "payload"
}
```

→ outbox_events 의 *각 row 가 *aggregate_type 따라 *다른 Kafka 토픽으로 라우팅*.

```sql
INSERT INTO outbox_events 
  (event_id, aggregate_type, aggregate_id, event_type, payload)
VALUES 
  ('uuid-1', 'Payment', '12345', 'PaymentCaptured', '{"orderId":12345,"amount":50000}');
```

→ Kafka topic: `lemuel.Payment` 으로 자동 라우팅. payload 가 메시지 본문.

---

## 5. *실전 Postmortem 4 건*

### Case 1 — *Polling 부하 사고 → CDC 전환*

**증상**: Outbox poller 가 *2 초 주기 SELECT* 로 DB CPU *지속 30%* 점유. *피크 시 *Latency 증가*.

**원인**: poll 간격 줄이면 부하 폭증 / 늘리면 latency 증가 — *근본 딜레마*.

**해결**: Debezium CDC 전환. 
- DB CPU 30% → *2%*
- Latency 2초 → *50ms*
- 단점: Kafka Connect cluster 운영 부담 *증가*

### Case 2 — *WAL 디스크 폭주***

**증상**: Debezium consumer lag 누적 → WAL 디스크 *200GB 폭주*.

**원인**: 
- replication slot 이 *consumer 가 처리한 위치까지 WAL 보관*
- consumer 다운 / 느림 → WAL 무한 적체
- PostgreSQL 디스크 풀 → *DB 자체 멈춤*

**해결**:
```sql
-- 모니터링
SELECT slot_name, active, 
       pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn)) AS lag
FROM pg_replication_slots;

-- 알람
WHEN lag > 10GB THEN PAGE oncall
```
+ 비활성 slot 자동 삭제 cron + WAL retention 명시.

### Case 3 — *스키마 변경 시 *Consumer 폭발***

**증상**: `ALTER TABLE orders ADD COLUMN coupon_id ...` 후 *모든 consumer 가 *NullPointerException*.

**원인**: 순수 CDC 사용 중 → *DB 스키마 = Kafka 메시지 스키마*. 컬럼 추가 시 모든 consumer 영향.

**해결**: 
1. Outbox 패턴 전환 (스키마 격리)
2. Schema Registry (Avro / Protobuf) 도입 — backward compatible 변경 강제

### Case 4 — *Snapshot 폭주 — *초기 동기화 사고***

**증상**: Debezium 첫 실행 시 *기존 1억 row 를 *snapshot* — DB locked 6시간.

**원인**: 기본 `snapshot.mode=initial` → *전체 테이블 *SELECT*.

**해결**:
```json
{
  "snapshot.mode": "no_data",                  // 스키마만 snapshot, 데이터는 X
  "snapshot.fetch.size": "10000",              // 청크 크기
  "snapshot.lock.timeout.ms": "1000"           // lock 타임아웃
}
```

운영 DB 는 *snapshot 없이 *현재 시점 부터 CDC* 시작.

---

## 6. *CDC 의 *함정 7 가지*

### 6.1 *Replication slot 누수*

> 비활성 slot 이 *WAL 보관 유발*. *반드시 모니터링*.

### 6.2 *DELETE 의 *tombstone 처리***

> Kafka log compaction 시 *DELETE 이벤트 = *null payload* 메시지. Consumer 가 *null 처리 안 하면 *NullPointerException*.

```java
@KafkaListener(...)
public void onChange(ConsumerRecord<String, String> record) {
    if (record.value() == null) {
        // ★ tombstone — DELETE 이벤트
        cache.evict(record.key());
        return;
    }
    // ... 정상 처리
}
```

### 6.3 *Kafka Connect Cluster 운영 복잡도*

> Debezium = *Kafka Connect 위에 *실행*. Connect cluster *별도 운영 필요*. *작은 팀에는 부담*.

### 6.4 *대용량 트랜잭션 — *메모리 폭주***

> 1 트랜잭션이 *수십만 row 변경* 시 Debezium *전체를 메모리에 buffer*. *큰 트랜잭션 *지양*.

### 6.5 *시간 순서 보장 — *Topic Partition***

```
Topic: lemuel.cdc.public.orders
  Partition 0: orders 의 id 1, 4, 7
  Partition 1: orders 의 id 2, 5, 8
  Partition 2: orders 의 id 3, 6, 9
```

> *같은 row 의 변경은 *항상 같은 partition* (key 로 보장). *다른 row 간 순서 X* — 비즈니스 로직 이를 *전제 X*.

### 6.6 *Consumer 가 *재처리 시 *시계열 비교 위험***

```java
// ❌ — 시간 비교 만으로 latest 판단
if (event.getTimestamp() > lastSeen.get(orderId)) {
    update(orderId, event);
}
// Kafka replay / consumer rebalance 시 *오래된 이벤트 *다시 적용* 가능
```

> *LSN / version 필드* 같은 *순서 보장 키* 사용.

### 6.7 *DB 마이그레이션 — *컬럼 명 변경***

> `RENAME COLUMN status TO order_status` 시 모든 consumer 깨짐. *Outbox 패턴이 *방어선*.

---

## 7. *2026 년 *CDC 의 *상태***

| 도구 | 위치 |
|------|------|
| **Debezium** | ★ 표준, 가장 성숙 |
| **AWS DMS** | AWS 전용, 매니지드 |
| **Maxwell** | MySQL 전용, 가벼움 |
| **Striim** | 상용, 복잡한 변환 지원 |
| **Estuary Flow** | 모던 SaaS, 빠른 셋업 |
| **Materialize** | streaming SQL, CDC 입력 |
| **RisingWave** | streaming DB, CDC 입력 |

> *오픈소스 = Debezium*. *클라우드 매니지드 = AWS DMS / Estuary*. *분석 결합 = Materialize / RisingWave*.

---

## 8. *선택 가이드 — *언제 CDC, 언제 Outbox, 언제 둘 다***

| 상황 | 권장 |
|------|------|
| 모놀리스, 단순 시스템 | Outbox + Poller (Debezium 운영 부담 큼) |
| MSA 5+ 서비스, 데이터 흐름 많음 | **Outbox + Debezium CDC** ★ |
| 데이터 파이프라인 (OLAP / Analytics) | **순수 CDC** (Debezium 직접) |
| Redis 캐시 무효화만 필요 | **순수 CDC** (간단) |
| 비즈니스 이벤트 + 분석 둘 다 | **Outbox + CDC + 분석용 CDC 별도** |
| 운영 인력 적음 | Outbox + Poller |
| 운영 인력 충분 (DevOps 전담) | **Debezium CDC** |

---

## 9. *최소 구축 가이드 — *Docker Compose***

```yaml
version: '3.8'
services:
  postgres:
    image: debezium/postgres:16
    environment:
      POSTGRES_DB: lemuel
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports: ["5432:5432"]
  
  kafka:
    image: redpandadata/redpanda:latest
    command:
      - redpanda start --smp 1 --memory 1G --overprovisioned
    ports: ["9092:9092"]
  
  connect:
    image: debezium/connect:2.7
    depends_on: [kafka, postgres]
    environment:
      BOOTSTRAP_SERVERS: kafka:9092
      GROUP_ID: connect-cluster
      CONFIG_STORAGE_TOPIC: connect_configs
      OFFSET_STORAGE_TOPIC: connect_offsets
      STATUS_STORAGE_TOPIC: connect_statuses
    ports: ["8083:8083"]
```

```bash
# 1. PostgreSQL WAL 설정
docker exec -it postgres psql -U postgres -c "ALTER SYSTEM SET wal_level = logical;"
docker restart postgres

# 2. Debezium connector 등록
curl -X POST http://localhost:8083/connectors -H "Content-Type: application/json" -d '{
  "name": "lemuel-postgres",
  "config": {
    "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
    "database.hostname": "postgres",
    "database.port": "5432",
    "database.user": "postgres",
    "database.password": "postgres",
    "database.dbname": "lemuel",
    "topic.prefix": "lemuel.cdc",
    "plugin.name": "pgoutput",
    "table.include.list": "public.orders,public.payments"
  }
}'

# 3. 데이터 변경 후 Kafka 토픽 확인
docker exec -it kafka rpk topic consume lemuel.cdc.public.orders
```

---

## 10. *마무리 — *CDC 의 *진짜 의미***

### 10.1 *CDC 는 *MSA 데이터 흐름의 *기본기*

> *대규모 MSA 의 *데이터 흐름 = CDC*. *Outbox 가 *비즈니스 이벤트 계약* 을, *CDC 가 *실시간 운반* 을 담당. *둘이 짝꿍*.

### 10.2 *2026 년 데이터 엔지니어의 *기본 도구***

> 데이터 엔지니어 / 백엔드 개발자가 *CDC 모르면 *대규모 MSA / 데이터 파이프라인 못 짠다*. Snowflake / BigQuery / Iceberg / Materialize *전부 *CDC 가 입력*.

### 10.3 *애플리케이션 코드 변경 0 의 *위력***

> *기존 시스템에 *CDC 만 붙이면 *데이터 흐름 *전부 활성화* — *애플리케이션 수정 0*. 레거시 모놀리스에서도 *CDC 만 깔면 *분석 / 캐시 / 검색 시스템 *바로 연결 가능*. *마이그레이션의 *가장 강력한 지렛대*.

### 10.4 *이력서 변환 hook*

> *"CDC / Debezium / 데이터 동기화 경험"* 한 줄에:
> - WAL / binlog / oplog 작동 원리
> - Debezium 셋업 + PostgreSQL replication slot
> - 자주 쓰는 사례 7 가지 (MSA 동기화 / 캐시 / ES / DW / 감사 / Event Sourcing / ML)
> - Outbox + CDC 조합의 *장점 (스키마 격리)*
> - 함정 7 가지 (slot 누수 / tombstone / snapshot / 순서)
> - 실전 postmortem 4 건
> 
> *5 단 깊이 면접 답변* 모두 준비.

---

## 부록 — *Cache Invalidation Consumer 예제 (Kotlin)*

```kotlin
@Component
class ProductCacheInvalidator(
    private val redisTemplate: StringRedisTemplate,
) {
    
    @KafkaListener(
        topics = ["lemuel.cdc.public.products"],
        groupId = "product-cache-invalidator"
    )
    fun onProductChange(record: ConsumerRecord<String, String>) {
        val key = record.key()
        val value = record.value()
        
        // tombstone — DELETE
        if (value == null) {
            redisTemplate.delete("product:$key")
            return
        }
        
        val change = parseCdcEvent(value)
        when (change.op) {
            "c", "u" -> redisTemplate.delete("product:$key")    // INSERT / UPDATE
            "d"      -> redisTemplate.delete("product:$key")    // DELETE
            "r"      -> { /* snapshot read — 무시 또는 prewarm */ }
        }
    }
}

data class CdcEvent(
    val before: Map<String, Any?>?,
    val after: Map<String, Any?>?,
    val op: String,
    val ts_ms: Long,
)
```

---

*다음 글:* *Saga 패턴의 *실전 구현 — *Choreography vs Orchestration* 비교 + *보상 트랜잭션* 의 *실제 코드*.
