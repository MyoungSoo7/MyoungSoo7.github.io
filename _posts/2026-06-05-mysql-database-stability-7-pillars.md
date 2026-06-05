---
layout: post
title: "MySQL DB 안정성 *7대 기둥* — 백업·HA·성능·스키마·모니터링·변경관리·보안"
date: 2026-06-05 17:15:00 +0900
categories: [reflection, database, devops]
tags: [mysql, database, stability, ha, replication, backup, innodb, performance, sre, schema-migration]
---

*"우리 DB 는 *안정적* 이에요"* 라는 문장은 *기준이 모호* 하다. 어느 누군가에겐 *"99.9% uptime"* 이고, 또 다른 사람에겐 *"매일 슬로우 쿼리 알람 안 옴"*. 진짜 *DB 안정성* 은 *7 가지 차원의 합* 인데, 한두 개만 잘하고 *다른 데 구멍* 이 있으면 *그 구멍으로 다 무너진다*.

본 글은 *MySQL 의 운영 안정성을 높이는* *7대 기둥* 을 정리한다. *어느 한 기둥* 만으론 충분하지 않다는 게 *본 글의 핵심*.

> 본 글은 *고찰* 이다. 구체 명령어/설정값은 *MySQL 8.0+ / InnoDB* 기준의 *권장 시작점*.

---

## TL;DR

| 기둥 | 핵심 | 부재 시 사고 |
|---|---|---|
| **1. 백업·복구** | *주기적 + 검증된* 백업, *PITR 가능* | 디스크 죽음 → 데이터 영구 소실 |
| **2. HA·Replication** | *Replica 1개 이상* + 자동 failover | Master 다운 → 서비스 중단 |
| **3. 성능·자원** | `innodb_buffer_pool`, connection pool, slow query | 트래픽 증가 → connection 고갈 |
| **4. 스키마·쿼리** | *online DDL*, gh-ost / pt-osc, 인덱스 설계 | ALTER 대기 → 30분 lock → 장애 |
| **5. 모니터링** | slow log, performance_schema, Prometheus exporter | 지표 없음 → *사고 후* 원인 못 찾음 |
| **6. 변경 관리** | 마이그레이션 자동화 + 리뷰 + 롤백 계획 | 마이그레이션 실수 → 데이터 손상 |
| **7. 보안** | TLS, 최소 권한, encryption at rest, audit log | 침해 → *데이터 유출* |

---

## 0. 안정성의 *5 가지 위협* 분류

DB 가 *불안정한 이유* 는 거의 *5가지 카테고리* 안:

1. **물리적 / 인프라 장애** — 디스크 고장, 노드 다운, 네트워크 단절
2. **자원 고갈** — connection / 메모리 / 디스크 / CPU
3. **잘못된 변경** — 마이그레이션 실수, 잘못된 인덱스, 권한 변경
4. **외부 공격 / 침해** — SQL injection, 권한 탈취
5. **사람 실수** — `DELETE WHERE` 빼먹기, `DROP TABLE` 실수

7 기둥은 *이 5 위협 각각* 에 대한 방어. *defense in depth* 패턴.

---

## 1. 백업·복구 — *복구 못 하면 백업이 아니다*

### 핵심 원칙
*백업은 *복구해본 적이 있을 때만* 백업이다.* 디스크에 백업 파일 *수십 GB* 가 있어도, *실제로 복원* 못 하면 그건 *고가의 디스크 낭비*.

### 1.1 백업 종류

| 방식 | 설명 | 적합 |
|---|---|---|
| **mysqldump** | 논리 백업 (SQL 텍스트) | 소규모 DB, 스키마 이동 |
| **mysqlpump** | mysqldump 의 병렬 버전 | 중규모 |
| **Percona XtraBackup** | 물리 백업 (innodb 파일) | 대규모, 빠른 복구 |
| **MySQL Enterprise Backup** | 상용 물리 백업 | 라이선스 있으면 |
| **Snapshot (LVM/EBS)** | 파일시스템 레벨 스냅샷 | 클라우드, 빠른 백업 |

소규모 (~10GB) → mysqldump 면 충분.
중대규모 (>100GB) → XtraBackup 필수 (논리 백업은 *복구 시간 너무 김*).

### 1.2 PITR (Point-in-Time Recovery)

binary log 가 *반드시* 켜져있어야 함:
```
[mysqld]
log_bin = mysql-bin
binlog_format = ROW
binlog_expire_logs_seconds = 604800   # 7일 보관
sync_binlog = 1                        # 매 commit 마다 fsync (안전)
```

복구 흐름:
```
[ 가장 가까운 풀백업 복원 ]
        ↓
[ 그 시점부터 사고 발생 직전까지 binlog 재생 ]
        ↓
[ DB 가 사고 *1초 전* 상태로 복원 ]
```

### 1.3 *반드시 정기적* DR 훈련

월 1회 또는 분기 1회:
1. 운영 백업 → 테스트 환경에 복원
2. 데이터 *행 수 / 키 합* 검증
3. *복원 소요 시간 측정* — SLA 안에 들어가는지

이걸 안 하면 *백업 파일은 있는데 복구가 안 됨* 의 *현장 실화* 가 발생.

---

## 2. HA · Replication — *Master 하나로 운영하지 마라*

### 핵심 원칙
*Single instance MySQL = 운영 시스템 아님.* *최소 1개 replica*, 가능하면 *자동 failover*.

### 2.1 Replication 종류

| 종류 | 동기 / 비동기 | 적합 |
|---|---|---|
| **Async Replication** | 비동기 | 일반 |
| **Semi-Sync Replication** | 1개 replica 가 ack 후 commit | 약간 강화 |
| **MySQL Group Replication** | 다중 replica 합의 (Paxos 변형) | HA 강화, 운영 복잡 |
| **InnoDB Cluster** | Group Replication + MySQL Shell + Router | 자동화된 cluster |
| **Galera Cluster** (Percona/MariaDB) | 동기, multi-master | 별도 변형 |

대부분의 경우 **Semi-Sync + MySQL Router** 조합이 *현실적 최적*.

### 2.2 자동 Failover

도구:
- **Orchestrator** (GitHub 개발) — *Topology aware*, 가장 인기
- **MHA (Master High Availability)** — 오래되어 *deprecated 경향*
- **MySQL Router + Group Replication** — 공식 솔루션
- **ProxySQL** — failover 라기보단 *routing + connection multiplexing*

자동 failover 의 *함정*:
- *Split-brain* 위험 — 2 노드가 *서로 master* 라고 주장
- *Phantom failover* — replica 가 잠깐 lag 으로 *master 죽었다 오판*
- *Failover 후 *옛 master 가 살아남* → 다시 와서 *충돌*

대응: *fencing* (옛 master 의 접근 차단), *세심한 timeout 튜닝*.

### 2.3 Read replica 활용
- *쓰기 = master*, *읽기 = replica*
- 읽기 부하 분산 + master 보호
- 단 *replication lag* 주의 — *just-written read* 는 master 에서

### 2.4 *Backup 도 replica 에서*
- Backup 작업이 *master IO 잡아먹음*
- *backup-only replica* 에서 수행 → master 부하 0

---

## 3. 성능·자원 — *connection 이 *조용히* 죽인다*

### 3.1 *innodb_buffer_pool_size* — 최우선 튜닝

```
[mysqld]
innodb_buffer_pool_size = 60% of RAM
```
- 4GB RAM → 2.5GB
- 32GB RAM → 19GB
- 데이터 핫셋이 *모두 메모리에* 들어가야 *IO 0*

확인:
```sql
SHOW STATUS LIKE 'Innodb_buffer_pool_reads';        -- 디스크 읽기
SHOW STATUS LIKE 'Innodb_buffer_pool_read_requests'; -- 전체 읽기
-- hit ratio = (read_requests - reads) / read_requests
-- 99% 이상이 목표
```

### 3.2 *Connection 관리*

**연결 누수 = DB 안정성의 *조용한 살인자*.**

MySQL 측:
```
max_connections = 500     # 단순히 늘리지 말 것 (메모리 폭발 위험)
max_user_connections = 100  # 사용자별 한도
wait_timeout = 60         # 유휴 연결 정리 (초)
interactive_timeout = 60
```

애플리케이션 측 (HikariCP):
```yaml
spring.datasource.hikari:
  maximum-pool-size: 20         # *서버 수 × 20 = 총 DB 연결*
  minimum-idle: 5
  connection-timeout: 5000      # 5초
  max-lifetime: 1800000         # 30분 (MySQL wait_timeout 보다 작게)
  leak-detection-threshold: 60000  # 60초 안 돌아오면 알람
```

서비스 인스턴스 30개 × pool 20 = *총 600 connection*. `max_connections = 500` 이면 *못 들어옴 → 장애*. 반드시 *애플리케이션 총 합산* 으로 계산.

### 3.3 *Slow Query Log*
```
slow_query_log = 1
slow_query_log_file = /var/log/mysql/slow.log
long_query_time = 1.0                 # 1초 이상
log_queries_not_using_indexes = 1     # 인덱스 안 타는 쿼리도
```

매주 `pt-query-digest` 로 분석:
```bash
pt-query-digest /var/log/mysql/slow.log > weekly-slow-report.txt
```

### 3.4 *CPU / 디스크 / 네트워크*
- CPU 일관성 > 피크 — *steady high CPU* 가 *occasional spike* 보다 위험
- 디스크 IOPS = *DB 의 진짜 한계*. SSD 권장
- 네트워크 — replica lag 의 60% 가 *네트워크* 문제

---

## 4. 스키마·쿼리 안전성 — *ALTER 가 *제일 위험한 명령**

### 4.1 Online DDL 의 한계
MySQL 5.6+ 에서 *대부분의 ALTER* 가 `ALGORITHM=INPLACE`. 하지만:
- *NULL → NOT NULL* 변경 → *전체 rebuild*
- *VARCHAR(N) 길이 축소* → *rebuild*
- *주키 변경* → *불가*

대응:
- 변경 전 *반드시* `EXPLAIN ALTER ...` 또는 *dry-run 환경* 테스트
- 대형 테이블 (>100GB) → **gh-ost** 또는 **pt-online-schema-change**

### 4.2 gh-ost (GitHub Online Schema Transformer)
- *Triggerless* — 기존 pt-osc 의 trigger 부하 제거
- binary log 기반 sync
- *throttle* 옵션 — replica lag 보고 자동 일시 정지

```bash
gh-ost \
  --user=migrator \
  --password=*** \
  --host=master \
  --database=mydb \
  --table=large_table \
  --alter="ADD COLUMN new_col INT DEFAULT 0" \
  --execute
```

운영 중인 50GB 테이블에 컬럼 추가 — *서비스 중단 없이* 1~3시간.

### 4.3 인덱스 설계 안전 원칙
- *Compound index* 의 column 순서 = *cardinality 높은 것부터*
- *Covering index* 활용 — `SELECT col WHERE other_col = X` 에서 *둘 다 인덱스에* 있으면 *테이블 안 봄*
- *Unused index* 정리 — `sys.schema_unused_indexes` 로 확인
- *Cardinality 100% 보장 안 됨* — `ANALYZE TABLE` 주기적으로

### 4.4 위험한 SQL 패턴
```sql
-- ❌ 잠금 폭발
UPDATE orders SET status='X';   -- WHERE 빠짐 → 전체 row lock

-- ❌ deadlock 위험
START TRANSACTION;
UPDATE a SET ... WHERE id=1;
UPDATE b SET ... WHERE id=2;
-- 다른 세션이 b → a 순으로 → 데드락

-- ❌ explain 안 보고 production 배포
SELECT * FROM logs WHERE created_at > ...;  -- created_at 인덱스 없으면 full scan
```

대응:
- 운영 쿼리 *모두* `EXPLAIN ANALYZE` 결과 첨부
- *DELETE / UPDATE 의 WHERE 없으면 거부* 하는 코드 리뷰 룰

---

## 5. 모니터링·관측 — *지표 없으면 사후약방문*

### 5.1 *반드시* 활성화

```sql
-- Performance Schema 켜기
SET GLOBAL performance_schema=ON;

-- sys schema (MySQL 5.7+ 기본 포함)
USE sys;
SELECT * FROM sys.schema_table_lock_waits;
SELECT * FROM sys.statement_analysis ORDER BY total_latency DESC LIMIT 10;
SELECT * FROM sys.schema_unused_indexes;
```

### 5.2 Prometheus exporter

```yaml
# mysqld-exporter sidecar
- name: mysqld-exporter
  image: prom/mysqld-exporter:v0.15.1
  env:
    - name: DATA_SOURCE_NAME
      value: "exporter:***@(localhost:3306)/"
  ports:
    - containerPort: 9104
```

Grafana 대시보드:
- MySQL Overview (사전 만들어진 dashboard ID 7362)
- *반드시 만들* 4 패널:
  1. QPS (queries per second)
  2. Connection 사용률 (`max_connections` 대비)
  3. innodb_buffer_pool hit ratio
  4. Replication lag (replica)

### 5.3 *반드시 만들* Alert Rule 7개

```yaml
- alert: MySQLDown
  expr: mysql_up == 0
  for: 1m

- alert: MySQLTooManyConnections
  expr: mysql_global_status_threads_connected / mysql_global_variables_max_connections > 0.8
  for: 3m

- alert: MySQLReplicationLagging
  expr: mysql_slave_lag_seconds > 30
  for: 2m

- alert: MySQLInnoDBLogWaits
  expr: rate(mysql_global_status_innodb_log_waits[5m]) > 10

- alert: MySQLSlowQueries
  expr: rate(mysql_global_status_slow_queries[5m]) > 5

- alert: MySQLDiskSpaceLow
  expr: node_filesystem_free_bytes{mountpoint="/var/lib/mysql"} / node_filesystem_size_bytes < 0.15

- alert: MySQLBackupOld
  expr: time() - last_backup_timestamp > 86400  # 24시간 이상 오래된 백업
```

---

## 6. 변경 관리 — *사람의 실수가 가장 큰 위협*

### 6.1 마이그레이션 자동화
- **Flyway** / **Liquibase** — 버전 관리된 마이그레이션
- *코드처럼* git 에 commit, PR 리뷰
- *환경별 순차 적용* — staging → production
- *롤백 스크립트도 함께* (DOWN migration)

### 6.2 production 변경 *3 step rule*

```
1. Staging 에서 실행 → 결과 검증
2. Production 의 *replica 만* 먼저 적용 → 검증
3. Master 적용
```

각 단계 사이 *최소 24 시간* 관찰 권장 (작은 변경은 1시간).

### 6.3 *위험한 명령* 의 *물리적 방어*

```
# .bashrc / .zshrc 에 추가
alias mysql='echo "production DB - use bastion + audit log"; false'

# bastion 에서만 가능
# 모든 명령 audit log 에 기록
# DROP / DELETE 는 *추가 confirmation* 필요
```

### 6.4 *Read-only 권한 분리*
- 분석가 / 개발자 → SELECT 만
- 운영자 → DML
- DBA 만 → DDL
- *RBAC 강제* — 권한 *없는* 게 안전

### 6.5 *복구 가능한 변경* 원칙
- *컬럼 DROP* 직접 X → *deprecated 표시 후 N개월 관찰* 후 DROP
- *테이블 DROP* 직접 X → *rename 후 N개월* 관찰 후 DROP
- *데이터 DELETE* → *soft-delete (`deleted_at` 컬럼)* + 별도 *purge job*

### 6.6 Audit log
```
[mysqld]
plugin-load = audit_log.so
audit_log_format = JSON
audit_log_policy = LOGINS  # 또는 ALL
```
*"이거 누가 했어?"* 의 *유일한 답*.

---

## 7. 보안 — *데이터 유출 = 회사 사망*

### 7.1 인증 / 권한
```sql
-- 강한 password validation
INSTALL COMPONENT 'file://component_validate_password';
SET GLOBAL validate_password.policy = STRONG;

-- 사용자별 *최소 권한*
GRANT SELECT, INSERT, UPDATE ON mydb.* TO 'app'@'10.%';
-- 절대로 GRANT ALL ON *.* 금지

-- localhost 외 root 접근 차단
DELETE FROM mysql.user WHERE User='root' AND Host NOT IN ('localhost', '127.0.0.1');
```

### 7.2 TLS
```
[mysqld]
ssl-ca = /etc/mysql/certs/ca.pem
ssl-cert = /etc/mysql/certs/server-cert.pem
ssl-key = /etc/mysql/certs/server-key.pem
require_secure_transport = ON
```

### 7.3 Encryption at Rest
- InnoDB tablespace 암호화
- TDE (Transparent Data Encryption) — Enterprise edition
- 또는 *디스크 레벨 LUKS* (오픈소스)

### 7.4 Audit + Anomaly Detection
- Audit log → SIEM (Splunk / ELK)
- *비정상 패턴* 자동 감지:
  - SELECT 결과 *수만 row* — 데이터 덤프 의심
  - *오프타임* (새벽) 접근
  - *외부 IP* 에서 접근

### 7.5 *SQL Injection 방어*
- *PreparedStatement* / *named parameter* 강제
- ORM (JPA, MyBatis) 가 *자동 처리* — 단 *raw SQL 사용 시* 직접 escape
- *WAF (ModSecurity)* 추가 layer

---

## 8. 실전 *체크리스트* — *36 항목*

### 백업·복구 (5)
- [ ] 일 1회 자동 백업
- [ ] binary log 활성화 (`log_bin = ON`)
- [ ] 월 1회 *복구 훈련* (실제 복원 시도)
- [ ] 백업 *오프사이트* 보관 (S3 등)
- [ ] 백업 파일 *암호화*

### HA·Replication (5)
- [ ] Replica *최소 1개*
- [ ] Semi-Sync 활성화 또는 Group Replication
- [ ] *자동 failover* 도구 (Orchestrator 등)
- [ ] Replication lag *모니터링 + 알람*
- [ ] *Failover 훈련* 분기 1회

### 성능·자원 (6)
- [ ] `innodb_buffer_pool_size` = 메모리 60%
- [ ] `max_connections` 적절 (앱 pool × 인스턴스 수 + 여유)
- [ ] HikariCP `max-lifetime` < MySQL `wait_timeout`
- [ ] Slow query log + `long_query_time = 1`
- [ ] `pt-query-digest` 주간 리포트
- [ ] 디스크 사용률 *85% 이하* 유지

### 스키마·쿼리 (5)
- [ ] *모든 ALTER* 사전 `EXPLAIN` + staging 테스트
- [ ] 대형 테이블 ALTER → gh-ost / pt-osc
- [ ] `sys.schema_unused_indexes` 정기 점검
- [ ] *WHERE 없는 DELETE/UPDATE* 코드 리뷰 거부
- [ ] N+1 쿼리 → `pt-query-digest` 또는 APM 으로 감지

### 모니터링 (5)
- [ ] mysqld-exporter + Prometheus
- [ ] Grafana 대시보드 4 핵심 패널
- [ ] *7 핵심 alert rule*
- [ ] Performance Schema ON
- [ ] *알람 *수신처 명확* (oncall 로테이션)

### 변경 관리 (5)
- [ ] Flyway / Liquibase 마이그레이션
- [ ] *마이그레이션 PR 리뷰* 강제
- [ ] Production 변경 *3 step rule* (staging → replica → master)
- [ ] *Audit log* 활성화
- [ ] *RBAC* — 최소 권한 + DDL 분리

### 보안 (5)
- [ ] TLS 강제 (`require_secure_transport = ON`)
- [ ] root 외부 접근 차단
- [ ] *Strong password* 정책
- [ ] Encryption at Rest (TDE or LUKS)
- [ ] WAF + Prepared Statement 강제

---

## 9. *흔한 함정* 5가지

### 9.1 *백업 있다고 안심 → 복구 못 함*
- 백업 *파일 자체* 가 깨져있음 (corrupt)
- 복구 명령 *모름*
- 복구 시간 *SLA 초과* (mysqldump 100GB → 4시간)
- **해법**: 분기 1회 *진짜* 복구 훈련

### 9.2 *Replica 가 *너무 lag* → master 죽을 때 못 씀*
- 평소 lag 30초 — failover 하면 *30초 데이터 손실*
- **해법**: lag 알람 + Semi-Sync (적어도 1개 replica 는 lag 0 보장)

### 9.3 *Connection pool 합산 안 함*
- 앱 1개 기준 pool 20 으로 설정
- *오토스케일링으로 100 개로 늘면* → 총 2000 connection → MySQL 폭발
- **해법**: HikariCP `max-pool-size = (max_connections / max_instances) * 0.7`

### 9.4 *마이그레이션 *down* 스크립트 없음*
- ALTER 실패 → 롤백 못 함 → 데이터 손상
- **해법**: 모든 마이그레이션에 *DOWN* 스크립트 + staging 에서 *up + down* 둘 다 테스트

### 9.5 *Alert 만들고 *수신처 없음**
- 알람 발생 → Slack 채널에 *아무도 안 봄*
- **해법**: PagerDuty / Telegram 직접 호출 + 24/7 oncall 로테이션

---

## 10. 결론 — *DB 안정성 = 7 기둥의 합*

### 한 기둥만 잘 하면?
- 백업만 잘 → 장애 발생 시 *복구 후* 모니터링 부재로 *재발*
- 모니터링만 잘 → 사고 *감지는 빠른데* 백업 없어 *복구 불가*
- HA 만 잘 → replica 자체가 master 의 *잘못된 변경* 을 따라 *함께 죽음*

### *진짜 안정성* 의 정의
> *모든 가능한 위협에 *최소 한 가지 방어* 가 있는 상태.*

7 기둥 중 *6 개 강함 + 1 개 약함* = *그 1 개로 다 무너짐*. *모든 기둥의 평균이 곧 안정성*.

### 작은 팀의 *현실적 우선순위*
인력 1~2 명 운영 환경:
1. **백업 + 복구 훈련** (5)
2. **HA + Semi-Sync** (5)
3. **Slow query + Alert** (5)
4. **gh-ost / Flyway** (5)
5. **TLS + 최소 권한** (5)
6. **Audit log** (5)
7. *나머지는 시간 나면*

### *마지막* — *DB 안정성 = 사람의 신중함*
도구는 *증폭기* 일 뿐. *DROP TABLE 을 *3번 confirm* 한 다음 치는 사람* 이 *Orchestrator + Prometheus + 백업 자동화* 다 갖춘 사람보다 *더 안전한 운영자*.

도구 → 자동화 → 신중함 — *순서가 거꾸로 가면* 도구가 *사고의 가속기* 가 된다.

다음 글에선 *gh-ost 의 *실전 운영 함정 5종* — chunk-size, throttle, 그리고 *cut-over phase 의 0.5초 lock* 의 진실* 을 정리할 예정.
