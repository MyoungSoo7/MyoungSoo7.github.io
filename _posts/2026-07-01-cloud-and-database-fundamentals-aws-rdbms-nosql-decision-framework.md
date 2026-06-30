---
layout: post
title: "*클라우드 (AWS) + 데이터베이스 (RDBMS / NoSQL)* — *2026 백엔드 의 *2 가지 기반* 의 *기본 의 정리* 와 *선택 의 판단 틀**"
date: 2026-07-01 07:30:00 +0900
categories: [backend, cloud, aws, database, fundamentals]
tags: [aws, ec2, s3, rds, dynamodb, lambda, vpc, rdbms, nosql, postgresql, mongodb, redis, cassandra, decision-framework, fundamentals]
---

> *백엔드 개발자 의 *입사 1 일차* — *팀 의 *온콜 슬랙* 에서 *EC2 의 *t3.medium 이 *AZ ap-northeast-2c 에서 *재기동 됐고 RDS 의 *Multi-AZ failover 가 *15 초 의 *connection drop 을 *유발* 했다는 *얘기* 가 *오간다*. *옆 의 *시니어 가 *"DynamoDB 의 *partition key 의 *hot partition 도 *같이 봐"* 라고 *덧 붙인다*.
>
> *처음 의 *주니어 — *각 단어 가 *외계어*. *6 개월 뒤 — *대충 의미 가 *잡힘*. *3 년 뒤 — *왜 그 결정 들 이 그렇게 되었는지* 의 *원리 가 *보인다*. *9 년 뒤 — *내 가 *그 결정 의 *주인*. *그 사이 의 *학습 의 *대부분 이 *2 가지 영역 의 *기본 의 *밑바닥*. *클라우드 + 데이터베이스*.
>
> 이 글은 *그 *2 가지 의 *기본* 을 *9 년차 시각 으로 *외우는 것 이 아니라 *선택 의 판단 틀* 로 *정리* 한 *주니어 → 미들 의 *지도*.

이 글은 *각 서비스 의 *상세 매뉴얼 이 아니다*. *각 영역 의 *추상화 의 *얇은 골격 + 그 위 의 *선택 의 *기준 들* 의 *정리*. *상세 한 깊이 는 *자매편 의 *수십 개 글 로 *분기*. 그 *지도 의 *입구 의 글*.

함께 보면 좋은 *자매편* :
- *[Lightsail → K3s 온프렘 이주](/2026/05/12/lightsail-to-k3s-onprem-repatriation.html)* — *Cloud 의 *대 안 의 시점*
- *[Cloud Exit + FinOps](/2026/05/30/infrastructure-cost-reduction-cloud-exit-finops.html)*
- *[K3s 온프렘 vs Cloud — 유용성](/2026/06/20/kubernetes-on-premise-vs-cloud-usefulness.html)*
- *[DBMS 의 *3 층 구조* — *클라이언트 / 인스턴스 / 데이터베이스*](/2026/06/26/dbms-architecture-client-instance-database-three-layer-deep-dive.html)*
- *[풀 스캔 이 *인덱스 보다 *빠른 경우*](/2026/06/29/when-full-table-scan-beats-the-index.html)*
- *[MySQL 의 *7 가지 안정성 기둥*](/2026/06/05/mysql-database-stability-7-pillars.html)*
- *[Backend 의 *Fundamentals*](/2026/06/15/backend-fundamentals.html)*

---

## TL;DR — *한 줄 결론*

> *클라우드 = *3 가지 추상화 (IaaS/PaaS/SaaS) × 4 가지 자원 (Compute/Storage/Network/Managed) 의 *조합*. *데이터베이스 = *2 가지 패러다임 (RDBMS / NoSQL) × 5 가지 NoSQL 종 의 *선택*. *둘 의 *교집합 — *Managed DB 의 *서비스 화 + 클라우드 의 *DB 비용 의 *주요 항목 화*. *2026 의 *백엔드 의 *진짜 기량 의 *80 % 가 *이 *2 가지 영역 의 *기본 의 *내면 화*. *그 위 에 *세분화 / 도구 / 패턴 이 *얹힌다*.

---

## 1. *왜 *이 *2 가지 가 *2026 의 *기반 인가**

### 1.1 *2 가지 의 *공통 점*

- *백엔드 의 *모든 시스템 의 *밑* 에 *반드시* 있다*.
- *각자 *수십 년 의 *축적 의 *결정 의 *기록 의 *집적*.
- *학습 의 *난이도* 보다 *그 부재 의 *비용* 이 *훨씬 큼*.
- *최신 트렌드 (LLM, K8s, MSA) 의 *영원한 *밑바닥*.

### 1.2 *2 가지 의 *서로 의 *그림자*

- *클라우드 의 *주된 결정 이 *DB 의 *비용 / 가용성 / 확장 의 *결정 적 영향*.
- *DB 의 *선택 이 *클라우드 의 *서비스 의 *어느 것 을 *쓰는지* 의 *결정*.
- *둘 을 *분리 해서 학습 하는 *것* 의 *함정*.

> *9 년 의 *경험 — *주니어 의 *대부분 의 *디버깅 의 어려움* 의 *주된 원인* 이 *둘 의 *경계* 에 대한 *시야 의 *부재*. *RDS 가 *왜 *느린지 — *DB 의 SQL 의 문제 인지 *AWS 의 *네트워크 / IOPS 의 문제 인지 *구분 못 함*.

---

## 2. *클라우드 의 *기본 — *AWS 를 *기준 으로*

*AWS* 가 *시장 의 *대표적 *기준*. *GCP / Azure / Naver Cloud* 도 *동일 한 추상화 의 *변주*. *AWS 를 *깊이 알면 *다른 것 으로 의 *전환 의 *학습 곡선 ↓*.

### 2.1 *3 가지 *추상화 의 *레벨**

| 레벨 | 의미 | 예 시 (AWS) | 책임 의 *분배* |
|---|---|---|---|
| **IaaS (Infrastructure as a Service)** | *가상 머신, 네트워크, 디스크 의 *제공* | *EC2, EBS, VPC* | *내가 *OS / DB / 앱 의 *전부 관리* |
| **PaaS (Platform as a Service)** | *플랫폼 의 *제공*. *내가 *앱 만* 올림* | *RDS, ECS, Elastic Beanstalk, Lambda* | *AWS 가 *OS / DB engine 관리. *내가 *앱 / 스키마 관리* |
| **SaaS (Software as a Service)** | *완성 된 서비스 의 *제공* | *Cognito (인증), SES (메일), Pinpoint (캠페인)* | *AWS 가 *대부분 관리*. *내가 *설정 만* |

*결정 의 *축* — *제어 vs 편 의* 의 *trade-off*.

- *IaaS = *최대 제어, 최대 책임*.
- *SaaS = *최소 제어, 최소 책임*.
- *PaaS = *둘 의 중간*.

### 2.2 *4 가지 *자원 의 *축**

#### Compute — *연산*

| 서비스 | 모델 | 적합 |
|---|---|---|
| *EC2* | *가상 머신* | *전통 적 인 *서비스 / DB 자체 운영* |
| *ECS / EKS* | *컨테이너* | *MSA / 12-factor 앱* |
| *Lambda* | *함수* | *이벤트 기반 / 간헐 적 워크로드* |
| *Fargate* | *서버리스 컨테이너* | *EC2 관리 회피 + 컨테이너 의 자유* |

#### Storage — *저장*

| 서비스 | 모델 | 적합 |
|---|---|---|
| *S3* | *Object Storage* | *정적 파일 / 백업 / 데이터 호수* |
| *EBS* | *Block Storage (EC2 에 마운트)* | *DB 데이터 파일 / 파일 시스템* |
| *EFS* | *NFS* | *다수 인스턴스 의 *공유 디렉토리* |
| *Glacier* | *Cold Storage* | *장기 보관, 드물게 접근* |

#### Network — *연결*

| 서비스 | 역할 |
|---|---|
| *VPC* | *논리 적 사설 네트워크* |
| *Subnet (Public / Private)* | *VPC 의 *분할*, *공개 / 사설 의 구분* |
| *Security Group / NACL* | *Firewall (인스턴스 / 서브넷 단위)* |
| *ALB / NLB* | *L7 / L4 로드 밸런서* |
| *Route 53* | *DNS* |
| *CloudFront* | *CDN (Edge 캐시)* |
| *NAT Gateway* | *Private subnet 의 *외부 송신* |

#### Managed Services — *완성 도구*

| 서비스 | 역할 |
|---|---|
| *RDS* | *관리 형 RDBMS (MySQL/PostgreSQL/Oracle/SQL Server)* |
| *Aurora* | *AWS 의 *클라우드 네이티브 RDBMS* |
| *DynamoDB* | *Managed Key-Value / Document NoSQL* |
| *ElastiCache* | *Managed Redis / Memcached* |
| *MSK / Kinesis* | *Managed Kafka / Streaming* |
| *SQS / SNS* | *Managed Queue / Pub-Sub* |
| *Secrets Manager / KMS* | *비밀 관리 / 암호화 키* |

### 2.3 *책임 의 *경계 — *AWS 의 *Shared Responsibility Model**

| 책임 | AWS | 사용자 |
|---|---|---|
| 데이터 센터 의 *물리 적 보안* | ✅ | — |
| 하드웨어 의 *유지 보수* | ✅ | — |
| Hypervisor / Network 의 *물리 적 운용* | ✅ | — |
| Managed 서비스 의 *OS / DB engine 패치* | ✅ | — |
| OS (EC2 위) 의 *패치* | — | ✅ |
| 애플리케이션 의 *코드 / 설정* | — | ✅ |
| 데이터 의 *암호화 / 백업 정책* | — | ✅ |
| IAM / Security Group / VPC 의 *설계* | — | ✅ |
| 비밀번호 / 키 의 *관리* | — | ✅ |

*"AWS 가 *알아서 해주는 것 / 내가 해야 하는 것" 의 *경계 의 *명확 한 이해 가 *AWS 학습 의 *시작 점*.

### 2.4 *4 가지 *기본 의 *결정 의 *판단 틀**

1. **워크로드 의 *모양** — *상시 / 간헐 적 / 이벤트 기반*. → *EC2 / Fargate / Lambda* 의 *선택*.
2. **데이터 의 *형태** — *구조 화 / 비구조 화 / 시계열 / 그래프*. → *RDS / DynamoDB / Timestream / Neptune* 의 *선택*.
3. **접근 의 *패턴** — *공개 / 사설 / 하이브리드*. → *ALB / VPN / Direct Connect / Cloudflare Tunnel* 의 *선택*.
4. **비용 의 *예측 가능성** — *상시 / 변동*. → *Reserved / Savings Plan / On-Demand / Spot* 의 *선택*.

> *이 *4 가지 가 *AWS 의 *수백 개 서비스 의 *대부분 의 *선택 의 *결정 의 *축*. *각 결정 의 *깊이 는 *후속 학습*. *우선 *4 가지 의 *축 자체 가 *시야 의 *바탕*.

---

## 3. *데이터베이스 의 *기본 — *2 가지 패러다임**

### 3.1 *RDBMS — *관계 형 데이터베이스**

#### *핵심 특징*

- *Schema-on-write* — *쓰기 전 에 *스키마 정의 강제*.
- *ACID 보장* — *원자성 / 일관성 / 격리 / 내구성*.
- *SQL 의 *선언 형 질의*.
- *JOIN — *여러 테이블 의 *관계 적 결합*.
- *Foreign Key 의 *참조 무결성*.
- *Transactions — *여러 작업 의 *원자 적 단위*.

#### *대표 적 *제품*

| 제품 | 특징 |
|---|---|
| *PostgreSQL* | *오픈소스, *기능 풍부, *확장 성 강함, *JSON 지원 ↑* |
| *MySQL* | *대중 적, *간단, *MariaDB 분기* |
| *Oracle* | *엔터프라이즈, *기능 의 *완전한 집합, *비싼 라이선스* |
| *SQL Server* | *Microsoft 생태계* |
| *SQLite* | *임베디드, *파일 기반* |

#### *적합 한 상황*

- *금융 / 결제 / 회계 — *정합성 의 *절대 적 요구*.
- *관계 형 데이터* (사용자-주문-상품 같은 *분명 한 관계*).
- *복잡 한 질의* — JOIN, 집계, 분석.
- *Schema 가 *상대 적으로 안정*.

### 3.2 *NoSQL — *비 관계 형 데이터베이스**

*"Not Only SQL"*. *RDBMS 의 *제약 의 *완화* 의 *5 가지 종*.

#### *5 가지 NoSQL 종*

| 종 | 모델 | 대표 |
|---|---|---|
| **Key-Value** | *key → value* 의 *단순 맵* | *Redis, DynamoDB, Memcached* |
| **Document** | *JSON / BSON 문서* | *MongoDB, CouchDB, DynamoDB* |
| **Wide-Column** | *행 별 *유연한 컬럼* | *Cassandra, HBase, ScyllaDB* |
| **Graph** | *노드 + 엣지* | *Neo4j, Neptune, ArangoDB* |
| **Time-Series** | *시간 인덱스 의 *최적화* | *InfluxDB, TimescaleDB, Timestream* |

#### *공통 *특징 들*

- *Schema-on-read* (대부분) — *쓰기 시 *유연*, *읽기 시 *해석*.
- *BASE* — *Basically Available, Soft state, Eventually consistent*.
- *수평 확장 (Horizontal scaling) 의 *친화 적 설계*.
- *높은 쓰기 처리량 / 큰 데이터 양 의 *최적화*.
- *분산 / 복제 의 *내장 적 *지원*.

#### *각 종 의 *적합 한 상황*

| 종 | 적합 |
|---|---|
| *Key-Value* | *세션 / 캐시 / 카운터 / 큐 / 분산 락* |
| *Document* | *유연한 스키마 / *프로토 타입 / *콘텐츠 관리* |
| *Wide-Column* | *대용량 시계열 / 로그 / IoT* |
| *Graph* | *소셜 / 추천 / 사기 탐지 / 지식 그래프* |
| *Time-Series* | *메트릭 / 센서 / 모니터링* |

### 3.3 *RDBMS vs NoSQL — *선택 의 *결정 표*

| 질문 | RDBMS 우세 | NoSQL 우세 |
|---|---|---|
| 데이터 모델 이 *관계 형 인가? | ✅ | |
| Schema 가 *자주 바뀌나? | | ✅ (Document) |
| 트랜잭션 / ACID 가 *필수 인가? | ✅ | |
| 처리량 이 *극단 적 으로 높나? | | ✅ |
| 데이터 가 *수십 TB / PB 인가? | | ✅ |
| 복잡 한 *JOIN 이 *필요 한가? | ✅ | |
| 쿼리 가 *주로 *단순 lookup 인가? | | ✅ (Key-Value) |
| 그래프 traversal 이 *주된 패턴 인가? | | ✅ (Graph) |
| 시계열 인가? | | ✅ (Time-Series) |
| 팀 의 *경험 / 도구 / 학습 이 *충분 한가? | RDBMS = 99 % | NoSQL = 학습 곡선 |

> *9 년 의 *결론* — *대부분 의 *시작 은 *PostgreSQL*. *NoSQL 은 *명확 한 적합 한 상황 에서 만 *추가*. *둘 의 *공존 (Polyglot Persistence) 이 *큰 시스템 의 *흔한 답*.

### 3.4 *Polyglot Persistence — *현실 의 *답**

*하나 의 시스템* 에서 *각 영역 의 *최적 DB 의 *공존*:

- *주 거래 데이터* — *PostgreSQL* (트랜잭션 / 정합성)
- *세션 / 캐시* — *Redis* (속도)
- *검색* — *Elasticsearch / OpenSearch* (전문 검색)
- *시계열 메트릭* — *Prometheus / TimescaleDB / InfluxDB*
- *분석 / 데이터 호수* — *S3 + Athena / BigQuery* (스토리지 의 분리)
- *그래프 관계 (있다면)* — *Neo4j / Neptune*

*복잡 함 의 대가 가 *각자 의 *최적 의 *수익*. *9 년차 의 *현실 적 *시스템 의 *대부분 이 *이 패턴*.

---

## 4. *클라우드 + DB 의 *교집합 — *2026 의 *흔한 패턴**

### 4.1 *Managed DB 의 *5 가지 *수익**

| 수익 | 내용 |
|---|---|
| *백업 의 *자동 화* | *Snapshot, PITR* |
| *Replication 의 *내장* | *Read Replica, Multi-AZ* |
| *Patching 의 *자동 화* | *유지 관리 윈도우* |
| *모니터링 의 *내장* | *CloudWatch, Performance Insights* |
| *고가용성 의 *기본* | *Multi-AZ failover* |

### 4.2 *Managed DB 의 *5 가지 *비용*

| 비용 | 내용 |
|---|---|
| *가격 의 *2 ~ 4 배* | *원본 EC2 + DB 자체 운영 대비* |
| *세부 제어 의 *제한* | *OS / 일부 설정 의 *불가* |
| *Lock-in 의 *위험* | *Aurora, DynamoDB 등 의 *클라우드 종속* |
| *대용량 의 *비용 폭증* | *IOPS / Storage 의 *수익 가 의 *유료* |
| *Egress 비용* | *외부 송신 의 *비용 가 의 *함정* |

### 4.3 *흔한 *조합 패턴**

#### *패턴 1 — *RDS PostgreSQL + ElastiCache Redis*

- *주 트랜잭션 = RDS PostgreSQL*.
- *세션 / 캐시 = ElastiCache Redis*.
- *작은 ~ 중간 규모 의 *전형 적 백엔드*.

#### *패턴 2 — *Aurora + DynamoDB*

- *복잡 한 관계 = Aurora*.
- *높은 처리량 / 단순 lookup = DynamoDB*.
- *큰 규모 + AWS 의 *클라우드 네이티브 채택*.

#### *패턴 3 — *RDS + Elasticsearch + S3 (데이터 호수)*

- *운영 데이터 = RDS*.
- *검색 = Elasticsearch*.
- *분석 / 장기 보관 = S3 + Athena*.

---

## 5. *주니어 → 시니어 의 *학습 의 *7 단계**

### 5.1 *단계 1 — *기본 어휘 의 *친밀**

- *EC2, S3, RDS, VPC* 의 *각자 한 줄 정의* 가 *자동 적 으로 떠 오름*.
- *psql, mysql 의 *기본 명령*.
- *EXPLAIN 의 *읽기 가능*.

### 5.2 *단계 2 — *Console 의 *습숙**

- *AWS Console 의 *주요 메뉴 의 *위치 파악*.
- *DB GUI (DBeaver / DataGrip)* 의 *능숙*.

### 5.3 *단계 3 — *CLI / IaC 의 *전환**

- *aws CLI* 의 *주요 명령*.
- *Terraform / CDK / CloudFormation 의 *읽기 / 작성*.
- *Console 의존 의 *해체*.

### 5.4 *단계 4 — *디버깅 의 *3 층 시야**

- *RDS 의 *느림 의 *원인 — *DB 자체 vs *네트워크 vs *IAM vs *Storage IOPS* 의 *분리 진단*.
- *CloudWatch Metrics + Performance Insights + EXPLAIN ANALYZE 의 *동시 사용*.

### 5.5 *단계 5 — *비용 의 *내면화**

- *각 결정 의 *월 청구서 의 *영향 의 *직관*.
- *내 [트래픽 의 비용 화 글](/2026/06/26/traffic-as-cost-the-causal-chain-from-request-to-cloud-bill.html)* 의 *시각*.
- *Reserved / Savings / Spot 의 *조합*.

### 5.6 *단계 6 — *설계 의 *주체*

- *VPC 의 *서브넷 의 *분할 의 *근거 를 *내 가 *제시*.
- *DB 의 *읽기 복제본 / Sharding 의 *결정*.
- *온콜 의 *수정 시 의 *판단*.

### 5.7 *단계 7 — *경계 의 *조 정*

- *Cloud 의 *과도 한 의존 의 *재 평가*.
- *온프렘 / 하이브리드 의 *적합 한 도입* (내 [Lightsail → K3s 이주](/2026/05/12/lightsail-to-k3s-onprem-repatriation.html)).
- *Polyglot Persistence 의 *경계 의 *결정*.
- *비용 의 *조직 적 *책임 의 *제도화*.

---

## 6. *주니어 가 *흔히 *오해 하는 *5 가지**

### 6.1 *"NoSQL = *항상 *빠름"*

*틀림*. *NoSQL 의 *빠름 의 *조건* — *액세스 패턴 이 *DB 모델 에 *맞는 경우*. *맞지 않으면 *RDBMS 보다 *극단 적 으로 느림*.

### 6.2 *"AWS = 비싸다"*

*조건 적 *. *작은 트래픽 에선 *비싸 보임*. *큰 트래픽 에선 *유지 보수 비용 까지 합치면 *경쟁 력 있음*. *내 경우 *작은 사이드 = *온프렘*, *기업 = *상황 별*.

### 6.3 *"RDBMS 는 *수평 확장 안 된다"*

*완전 한 거짓 은 *아니지만 *과장*. *Read Replica, Partitioning, Sharding, *Aurora 의 *분산 스토리지 등 *많은 옵션*. *NoSQL 만큼 *자연 스러움 은 *부족*. *그러나 *대부분 의 *현실 적 규모 에서 *충분*.

### 6.4 *"Managed = *나는 *책임 없다"*

*틀림*. *Shared Responsibility Model 의 *내 영역 (스키마, 쿼리, IAM, 백업 정책) 의 *책임 은 *여전 히 *나*. *Managed 가 *덮어 주는 영역 의 *오해 가 *흔한 사고 의 *원인*.

### 6.5 *"Cloud = 우월"*

*9 년 의 *반복 적 검증* — *상황 별 *최적 의 답 이 다름*. *K3s 홈랩 / 온프렘 의 *수익 의 *영역 이 *분명* 함. *맹목 적 *클라우드 신앙 의 *경계 가 *시니어 의 *판단력*.

---

## 7. *추천 학습 자원**

### 7.1 *AWS*

- *AWS Skill Builder* — *공식 무료 학습 플랫폼*.
- *AWS Well-Architected Framework* — *설계 의 *6 가지 원칙*.
- *AWS Solutions Architect Associate 자격증* — *체계 적 학습 의 *효과 적 강제*.
- *"AWS in Action"* (Wittig, Manning) — *책 의 *기본*.

### 7.2 *RDBMS*

- *"Designing Data-Intensive Applications"* (Kleppmann) — *분산 데이터 의 *교과서 의 *현대 적 명작*.
- *"PostgreSQL Up & Running"* (Obe & Hsu) — *PostgreSQL 의 *실 무 적 입문*.
- *"High Performance MySQL"* (Schwartz et al.) — *MySQL 의 *경전*.
- *Use The Index, Luke!* — *인덱스 의 *온라인 무료 교과서*.

### 7.3 *NoSQL*

- *"NoSQL Distilled"* (Sadalage & Fowler) — *짧고 *완전 한 *개요*.
- *MongoDB / DynamoDB / Cassandra 의 *공식 문서* — *각자 의 *데이터 모델 의 *깊이*.
- *"Database Internals"* (Petrov) — *분산 의 *밑바닥*.

### 7.4 *자매편 의 *통합 읽기*

- *위 의 *자매편 7 개 의 *순서 적 읽기*.

---

## 8. *결론 — *2 가지 기반 의 *조용한 의미**

*"클라우드 와 *데이터베이스 의 *기본 을 *학습 한다"* — *이 *한 문장 의 *9 년 의 *내면화 의 *형태* :

- *주니어 — *어휘 의 친밀*.
- *미들 — *결정 의 판단 틀*.
- *시니어 — *결정 의 *책임 의 *주체*.
- *9 년차 — *결정 의 *경계 의 *조 정*.

*각 단계 의 *학습 의 *질 적 차이*. *외우는 것 이 아니라 *판단 의 *축 의 *내면화*.

> *"클라우드 + DB 의 *기본 의 *학습 의 *진짜 정점* 은 *그 *2 가지 의 *경계 의 *언제 *유 지 / 어떻게 *교차 시키는지* 의 *판단 력 의 *체화*. *그 위 에 *모든 *현대 적 시스템 의 *결정 의 *80 % 가 *얹힌다*. *그 *80 % 의 *주인 이 되는 것* 이 *백엔드 의 *9 년차 의 *진짜 자리*.

---

## 다음 으로 *권 하는 읽기**

- *위 의 *자매편 7 개 의 *순서 적 통독* — *이 글 의 *각 부분 의 *깊이*.
- *각 영역 의 *공식 문서* 의 *습관 적 *재 방문*.
- *내 *13 개 레포 의 *코드* — *이 *기본 의 *실 무 적 적용* 의 *살아있는 사례*.

*다음 글* — *클라우드 의 *4 가지 자원 의 *각 깊이 + DB 의 *5 가지 NoSQL 종 의 *각 적합 사례 + Polyglot Persistence 의 *실제 적용 의 *5 부 시리즈* — *곧*.
