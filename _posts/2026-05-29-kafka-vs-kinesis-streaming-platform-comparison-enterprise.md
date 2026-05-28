---
layout: post
title: "Kafka vs Kinesis — *오픈소스의 왕* 과 *클라우드 네이티브의 답*, 12 개 축에서 *솔직히* 비교"
date: 2026-05-29 01:20:00 +0900
categories: [architecture, streaming, aws, kafka]
tags: [kafka, kinesis, msk, confluent, event-streaming, aws, linkedin, netflix, uber, pinterest, hearst]
---

> 2010 년 LinkedIn 에서 *''N×M connector 카오스''* 를 풀기 위해 **Kafka** 가 태어났다. 3 년 뒤 2013 년, AWS 가 *''Kafka 운영이 *너무 어렵다*''* 는 시장의 비명을 듣고 **Kinesis** 를 발표했다. 그 후 13 년, *둘은 *서로 다른 진영* 의 *서로 다른 답* 으로* 살아남았다.
>
> *''Kafka 와 Kinesis 중 무엇이 더 좋은가''* 는 *틀린 질문* 이다. *''*내 상황에서* 어떤 게 더 맞는가''* 가 *맞는 질문* 이고, 그 답은 *처리량·운영 인력·비용 모델·기존 스택·보존 기간* 의 *5 가지 축* 위에서 갈린다.

이 글은 두 플랫폼을 *12 개 비교 축* 으로 분해하고, *6 개 기업의 실전 사례* 를 통해 *''어느 진영이 *왜* 그 선택을 했는가''* 를 본다. 마지막은 *2026 년의 결정 흐름도* 로 마무리한다.

---

## 1. 출생 배경 — *왜 두 플랫폼이 *동시대* 에 태어났나*

### 1.1 **Kafka** (2010, LinkedIn) — *''N×M connector 지옥''* 의 탈출구

2008 ~ 2010 년 LinkedIn 의 데이터 플로우:

- *N 개 생산자* (회원 활동, 채용 데이터, 활동 로그, ...)
- *M 개 소비자* (검색 인덱스, 추천, 분석, 사기 탐지, ...)
- *연결당 ETL pipeline* — *N × M = 폭발*

기존 메시지 큐 (ActiveMQ, RabbitMQ) 의 한계:
- *처리량* 이 LinkedIn 규모를 못 받침
- *영구 보존* 어려움 — *ack 하면 삭제*
- *복수 소비자* 가 *각자 다른 속도* 로 읽기 어려움

Jay Kreps, Neha Narkhede, Jun Rao 가 *''*Database log 개념을 *분산 시스템* 으로 일반화''* 한 *Kafka* 를 발표. 2011 년 오픈소스화, 2014 년 *Confluent* 창업.

> **핵심 발상**: *''메시지 큐가 아니라 *분산 로그* (distributed commit log)''*. 데이터는 *append-only*, 보존 정책에 따라 *영구* 또는 *시간/크기 기반 삭제*.

### 1.2 **Kinesis** (2013, AWS) — *''Kafka 좋은데 운영이 *지옥*''* 의 답

Kafka 가 *너무 좋다* 보니 *모두 쓰고 싶어 했다*. 하지만:

- *Zookeeper + Broker 클러스터* 의 *운영 복잡도*
- *Disk / 네트워크 / JVM tuning* 의 *전문성 요구*
- *Rebalancing / partition reassignment* 의 *함정*

2013 년 AWS re:Invent 에서 발표된 **Amazon Kinesis Data Streams** 의 *마케팅 한 줄*:

> *''Kafka 의 성능을, *클러스터 관리 없이*. *완전 관리형*.''*

이후 AWS 는 Kinesis 패밀리를 *4 개 서비스* 로 확장:
- **Kinesis Data Streams** — *Kafka 와 1:1 대응* 되는 *코어*
- **Kinesis Data Firehose** — *''스트리밍 → S3/Redshift/Elasticsearch''* 의 *자동 ETL*
- **Kinesis Data Analytics** — *Flink 관리형* (현재는 *''Amazon Managed Service for Apache Flink''* 로 개명)
- **Kinesis Video Streams** — *비디오 스트림 *전용**

이 글은 *주로* **Kinesis Data Streams (KDS)** vs **Kafka** 의 *코어 대결* 을 다룬다.

---

## 2. *12 개 축* 비교 — *솔직하게*

### 2.1 한 눈에 보는 비교표

| # | 축 | **Kafka** | **Kinesis Data Streams** |
|---|---|---|---|
| 1 | 모델 | Topic / **Partition** | Stream / **Shard** |
| 2 | 처리량 단위 | partition 당 *수십 MB/s* | shard 당 *1 MB/s in, 2 MB/s out* |
| 3 | 보존 기간 | *시간/크기 정책*, *영구* 가능 | *24 시간 ~ 365 일* (on-demand: 7 일~) |
| 4 | 순서 보장 | partition 내부 | shard 내부 |
| 5 | 확장 | partition 추가 (수동) | shard 분할/병합 (provisioned) 또는 *자동* (on-demand) |
| 6 | 운영 부담 | *broker / Zookeeper / 모니터링* | **AWS 가 다 함** |
| 7 | 비용 모델 | *인프라 비용 + 인력* | *shard-hour + PUT payload* |
| 8 | 클라이언트 | 다양한 언어 SDK (오픈소스) | AWS SDK (멀티 언어) + KCL |
| 9 | 에코시스템 | Kafka Connect, Streams, ksqlDB, Schema Registry | Firehose, Lambda, Flink (KDA), Glue Schema Registry |
| 10 | 보안 | TLS, SASL, ACL — *직접 설정* | IAM 통합 (*기본*) |
| 11 | 멀티 컨슈머 | 자유 (consumer group) | 기본 2 개 *enhanced fan-out* 까지 *추가 비용* |
| 12 | 락인 | *낮음* (오픈소스) | *높음* (AWS 전용) |

### 2.2 *축별 *깊은 분석**

#### 축 #1, 2 — *Partition vs Shard*

근본적으로 같은 개념이다. *순서 보장의 기본 단위*, *병렬 처리의 기본 단위*. 하지만 *처리량의 상한이 다르다*.

- **Kafka partition** — *디스크 I/O 와 네트워크 한도* 까지 *수십 MB/s* 가능
- **Kinesis shard** — *AWS 가 *명시* — 1 MB/s in, 2 MB/s out, 1,000 records/s in*

이 차이가 *비용 모델 차이* 의 *근본 원인*. Kafka 는 *''partition 을 많이 두면 *처리량 ↑*, 비용은 *인프라*''*. Kinesis 는 *''shard 를 많이 두면 *처리량 ↑*, 비용은 *shard-hour 누적*''*.

#### 축 #3 — *보존 기간*

- **Kafka** — *기본 7 일*, *원하면 *수년 / 영원***. Event Sourcing 에 *적합*.
- **Kinesis** — *기본 24 시간*, *최대 365 일* (추가 비용). Event Sourcing 으로는 *부적합*.

> *''Kafka 는 *재생 가능한 진실의 원천*, Kinesis 는 *흐르는 데이터 파이프''*. 이게 *진영의 *철학적 차이*.

#### 축 #6 — *운영 부담*

여기서 *진짜 차이* 가 갈린다.

**Kafka 셀프 호스팅**:
- Zookeeper (또는 KRaft 모드) 운영
- Broker 5+ 노드 *최소*
- *Rebalancing, ISR 관리, disk full 대응, JVM GC tuning*
- *전담 SRE 1~2 명* 이 *현실*

**Kinesis**:
- *AWS 콘솔에서 stream 생성 *클릭 한 번**
- *''스토리지가 가득''* 같은 경고가 *원천적으로 없음*
- *AWS 가 24/7 운영*

**MSK (Amazon Managed Streaming for Kafka)** — *중간 타협*:
- *Kafka 호환* 인데 *AWS 가 broker 운영*
- *cluster 자체는* 여전히 *고객 책임*
- Kinesis 만큼 *완전 관리형* 은 아니지만 *Kafka 의 *호환성과 에코시스템* 유지*

#### 축 #7 — *비용 모델*

흔히 *''Kinesis 가 비싸다''* 라고 단순화되는데 *틀렸다*.

- **소규모** — Kinesis 가 *훨씬 저렴*. *인력 비용 + 노드 비용* 보면 *Kafka 운영비 100 만원/월 vs Kinesis 사용비 10 만원/월* 가능
- **대규모** — Kafka *셀프 호스팅* 이 *압도적으로 저렴*. Kinesis 의 *shard-hour + PUT 요금* 이 *Netflix 규모* 에서 *수억원/월* 됨
- **MSK** — *중간*. Kafka 의 인프라 비용 + AWS 마진 30% 정도

> **현실 공식**: *팀 규모 < 30 명 → Kinesis (또는 Confluent Cloud)*. *팀 규모 > 50 명 + 전담 데이터 인프라 팀 존재 → Kafka 셀프 호스팅 검토*.

#### 축 #11 — *멀티 컨슈머*

Kafka 의 *킬러 기능* 중 하나. *같은 토픽을 *무한히 많은* consumer group 이 *각자 다른 속도로* 읽을 수 있다*.

Kinesis 는 *기본 2 개* shard 당 consumer 만 허용. *3 개 이상* 은 **Enhanced Fan-Out** 으로 *별도 비용* — 이게 *''데이터 메시 (Data Mesh)''* 같은 *''여러 도메인이 같은 이벤트 소비''* 패턴에 *큰 제약*.

#### 축 #12 — *벤더 락인*

- **Kafka** — *오픈소스*. *AWS / GCP / 자체 IDC / Confluent Cloud* 어디든 *같은 코드*
- **Kinesis** — *AWS 전용*. *멀티 클라우드 / 온프레미스 이전* 시 *재작성 필요*

*기업의 클라우드 전략* 이 *''AWS 올인''* 이면 락인 비용 *낮음*. *''멀티 클라우드 가능성 유지''* 면 *Kafka 가 정답*.

---

## 3. *기업 사례* — 누가 무엇을 선택했나

### 3.1 *Kafka 진영*

#### **LinkedIn** — *Kafka 의 *친정**

- *일일 7 조 메시지* (2022 기준)
- *Kafka 클러스터 100+ 개*
- *''*Brooklin* '' 이라는 자체 *cross-cluster mirroring* 도구도 오픈소스화

#### **Uber** — *Kafka 위의 *실시간 가격 산정**

- *모든 운전자 위치 업데이트 → Kafka*
- *모든 승객 요청 → Kafka*
- *Surge pricing 알고리즘 = Kafka Streams 실시간 집계*
- *Kafka 클러스터 *수십 개*, *피크 시 초당 *수억 메시지*

#### **Pinterest** — *Kafka + Flink + Iceberg 의 *데이터 lakehouse**

- *모든 사용자 인터랙션 (pin, save, click) → Kafka*
- *Flink 로 실시간 추천 feature 계산*
- *Iceberg (Apache) 로 *장기 데이터 lake*

#### **Airbnb** — *Kafka + Spark 의 *예약 데이터 파이프라인**

- *모든 검색·예약 이벤트 → Kafka*
- *''*JitneyKafka*'' 자체 abstraction 으로 *Avro 스키마 강제*
- *데이터 분석가가 *코드 변경 없이* 새 토픽 구독 가능*

> **공통 패턴**: *대규모 + 전담 데이터 인프라 팀 + 멀티 클라우드 또는 hybrid 인프라 + Event Sourcing 또는 *재생 필요* 도메인*.

### 3.2 *Kinesis 진영*

#### **Netflix** — *둘 다 쓴다* (현실적 진실)

Netflix 는 *Kafka 의 *대표적 사용자* 로 알려져 있지만, *Kinesis 도 *깊게* 쓴다*.

- **Keystone** (메인 telemetry) — *Kafka* (셀프 호스팅, 일일 *수조 이벤트*)
- **Kinesis Data Streams** — *''*일시적* 데이터 처리''*, *Lambda 트리거 패턴*
- *''*도메인 별 *목적별 선택*''* — *교조적이지 않음*

#### **Hearst** — *''Magazine + News''* 의 *전사 데이터 통합*

- *Cosmopolitan, Elle, Esquire 등 *수백 개 매체*의 *조회 데이터*
- *Kinesis Data Streams + Firehose → S3 + Redshift*
- *''*AWS 통합* 이 *주요 선택 이유* — *별도 운영 인력 없이* 가동''*

#### **Capital One** — *금융 사기 탐지*

- *모든 카드 트랜잭션 → Kinesis*
- *Lambda 가 *수초 안에* 사기 패턴 검출*
- *''*AWS 의 *컴플라이언스 + IAM* 이 *금융 규제* 와 잘 맞음''*

#### **Roche** (제약) — *임상 시험 데이터 스트리밍*

- *글로벌 *수천 개 임상 사이트* 데이터 → Kinesis Firehose → S3*
- *HIPAA / GxP 컴플라이언스 가 *AWS managed* 라 *감사 부담 ↓*

> **공통 패턴**: *AWS 올인 + 전담 인프라 팀 부족 + 운영 단순화 우선 + 컴플라이언스 요구 강함*.

### 3.3 *진영 이동 사례* — *''갈아탔다''*

#### **Pinterest** — Kinesis → Kafka (2016)

초기에는 Kinesis 로 시작했다가 *규모가 커지면서* Kafka 셀프 호스팅으로 이동. 이유:

- *Kinesis 비용이 *예측 불가능* 하게 증가*
- *Kafka 의 *영구 보존* 이 *분석 사용 사례에 필수*
- *전담 인프라 팀이 *성숙* 함*

#### **Lyft** — Kinesis → Kafka (2018) — *대규모는 결국 Kafka*

#### **반대 방향 사례는 *드물다*** — *Kafka → Kinesis 이전은 *흔치 않음**

> **인사이트**: *''소규모로 시작해서 Kinesis, 커지면 Kafka''* 가 *흔한 진화 경로*. *반대는 드뭄*.

---

## 4. *처리량 / 비용 / 운영* 의 *3 축 시뮬레이션*

### 4.1 *시나리오 A — 스타트업, 1 MB/s 트래픽*

| | Kafka 셀프 호스팅 | MSK | Kinesis |
|---|---|---|---|
| 인프라 비용 | EC2 3 노드 m5.large ≈ $200/월 | $300/월 | $11/월 (1 shard) |
| 운영 인력 | *0.5 ~ 1 명* 필요 | *0.2 명* | *0 명* |
| 총 *진짜* 비용 | ~$2,000/월 | ~$1,000/월 | **~$50/월** |

> *결정*: **Kinesis 압도적**.

### 4.2 *시나리오 B — 중견 기업, 100 MB/s 트래픽*

| | Kafka | MSK | Kinesis |
|---|---|---|---|
| 인프라 비용 | EC2 9 노드 m5.2xlarge ≈ $4,000/월 | $7,000/월 | $1,100/월 (100 shard) + 데이터 처리 |
| 운영 인력 | *2 명* | *1 명* | *0.5 명* |
| 총 *진짜* 비용 | ~$20,000/월 | ~$15,000/월 | ~$10,000/월 |

> *결정*: **상황별**. *전담 팀 있으면 Kafka*, *없으면 Kinesis 또는 MSK*.

### 4.3 *시나리오 C — 대기업, 10 GB/s 트래픽 (Netflix 급)*

| | Kafka | Kinesis |
|---|---|---|
| 인프라 비용 | ~$50,000/월 | ~$700,000/월 |
| 운영 인력 | *5 명 *전담* * | *2 명* |
| 총 *진짜* 비용 | ~$150,000/월 | ~$900,000/월 |

> *결정*: **Kafka 압도적**. *Netflix 가 *Kafka 를 셀프 호스팅* 하는 이유* — *대규모에서는 *클라우드 마진* 이 *인력 비용을 압도*.

---

## 5. *2026 트렌드* — *세 가지 변화*

### 5.1 *Kafka 의 *서버리스화** — Confluent Cloud + MSK Serverless

*''Kafka 의 *낮은 락인* + Kinesis 의 *운영 단순함*''* 을 *둘 다* 가지려는 시도.

- **Confluent Cloud** — *Kafka 만든 회사가 *완전 관리형* 으로 판매*
- **MSK Serverless** (2021) — *AWS 의 *Kafka 서버리스* 답*
- **Aiven, Redpanda Cloud** — *대안 관리형*

> **2026 의 *실용적 디폴트***: *''서버리스 Kafka''*. *오픈소스 호환 + 운영 부담 ↓*.

### 5.2 *Kinesis 의 *On-Demand 모드** — *Kinesis 의 진화*

기존 Kinesis 는 *shard 수를 *수동* 으로 관리* 했는데, *On-Demand 모드* 에서는 *AWS 가 *자동 확장*.

- *Shard provisioning 부담 제거*
- *비용은 *사용량 비례* — 작은 트래픽엔 *훨씬 저렴*
- *peak/valley* 가 큰 워크로드에 *적합*

### 5.3 *''Streaming-first DB''* 의 등장

- **RisingWave** — *PostgreSQL 호환 streaming DB*
- **Materialize** — *''실시간 view''* — *SQL 로 *스트림 처리**
- **ksqlDB** — Kafka 위의 *SQL 추상*

> *''Kafka / Kinesis 를 *직접 *쓰지 않고* SQL 로 *위에서*''* 가 *점차 표준화*.

---

## 6. *결정 흐름도* — *''뭐 쓸까''*

```
1) AWS 올인인가?
   ├─ Yes  → 2 번
   └─ No   → Kafka (셀프 또는 Confluent Cloud)

2) 트래픽이 1 GB/s 이하인가?
   ├─ Yes  → 3 번
   └─ No   → Kafka (MSK 또는 셀프) — *비용이 Kinesis 앞섬*

3) 보존 기간 365 일 초과 필요?
   ├─ Yes  → Kafka 또는 *S3 + Glacier 백업 결합 Kinesis*
   └─ No   → 4 번

4) 멀티 컨슈머 5 개 이상 필요?
   ├─ Yes  → Kafka (Kinesis 는 enhanced fan-out 비용 ↑)
   └─ No   → 5 번

5) 전담 데이터 인프라 팀이 있는가?
   ├─ Yes  → Kafka (MSK 또는 셀프) — *유연성 + 비용 우위*
   └─ No   → **Kinesis** ✅ — *AWS 가 운영*
```

---

## 7. *언제 *둘 다* 쓰는가*

*''*전부 Kafka* 또는 *전부 Kinesis*''* 가 *교조적* 이라는 게 *현장의 합의*. **Netflix 가 둘 다 쓰는 이유** 를 따라가면:

- ***''*핵심 비즈니스 telemetry* + *대량 + 보존 필요*''*** → **Kafka**
  - 회원 활동, 시청 이벤트, 결제 이벤트
- ***''*일시적 + Lambda 트리거 + 부서 별 데이터*''*** → **Kinesis**
  - 부서 별 ad-hoc 데이터 수집, 로그 수집 후 S3 적재

이 *''*도메인 별 *목적별 선택*''* 패턴이 *2026 년의 *현실적 답*.

---

## 8. *간단 코드 비교* — Java / Spring Boot

### 8.1 *Kafka Producer*

```java
@RequiredArgsConstructor
@Service
public class OrderEventPublisher {
    private final KafkaTemplate<String, OrderEvent> kafkaTemplate;

    public void publish(OrderEvent event) {
        kafkaTemplate.send("orders", event.orderId(), event);
    }
}
```

### 8.2 *Kinesis Producer*

```java
@RequiredArgsConstructor
@Service
public class OrderEventPublisher {
    private final KinesisAsyncClient kinesis;

    public void publish(OrderEvent event) {
        kinesis.putRecord(PutRecordRequest.builder()
            .streamName("orders")
            .partitionKey(event.orderId())
            .data(SdkBytes.fromUtf8String(toJson(event)))
            .build());
    }
}
```

### 8.3 *Kafka Consumer*

```java
@KafkaListener(topics = "orders", groupId = "payment-service")
public void on(OrderEvent event) {
    paymentService.process(event);
}
```

### 8.4 *Kinesis Consumer* (KCL 사용)

```java
public class OrderRecordProcessor implements ShardRecordProcessor {
    @Override
    public void processRecords(ProcessRecordsInput input) {
        input.records().forEach(rec -> {
            var event = parse(rec.data());
            paymentService.process(event);
        });
        input.checkpointer().checkpoint();
    }
    // ... initialize / leaseLost / shardEnded
}
```

> **차이**: *Kafka 가 *훨씬 간결*. *Kinesis 는 *checkpoint 직접 관리*. *Spring Cloud Stream Kinesis Binder* 로 *추상화 가능*.

---

## 9. 정리 — *진짜 답*

> ***''Kafka 가 더 좋다''* 도 *''Kinesis 가 더 좋다''* 도 *틀린 명제* 다. *문제는 *내 조직과 도메인이 *어디 있는가*''*.

12 개 축의 *진짜 의미* 를 한 문장씩으로 압축하면:

- **Kafka** = *''*힘 들이지만 *유연하고 강한 진정한 분산 로그*''*. *Event Sourcing*, *멀티 컨슈머*, *멀티 클라우드*, *영구 보존* 의 *왕*.
- **Kinesis** = *''*AWS 가 *전부 해 주는* 실용적 스트리밍''*. *작게 시작*, *컴플라이언스 강함*, *Lambda 통합* 의 *왕*.

> **2026 년 권장 시작점**:
>
> 1. *AWS 올인 + 전담 팀 ≤ 5 명* → **Kinesis** 또는 **MSK Serverless**
> 2. *멀티 클라우드 또는 *온프레 가능성* + 전담 팀 있음* → **Kafka (Confluent Cloud)**
> 3. *대규모 + 비용 민감 + 전담 인력 충분* → **Kafka 셀프 호스팅**
> 4. *결정 못 하겠으면 — *Kinesis 로 시작 → 커지면 Kafka 로 이주** 가 *흔하고 안전한 경로*

기술 선택은 *''*베스트 프랙티스* 가 *내 회사의 베스트 프랙티스''* 라는 *환상* 으로 자주 망한다. *Netflix 의 *Kafka 사랑* 을 *스타트업이 따라하는 것* 만큼 비싼 결정도 없다. *내 처지를 먼저 보고, 도구를 *그 위에* 얹는 게* *언제나 옳다*.

---

## 더 읽으면 좋은 자료

- Jay Kreps, **The Log: What every software engineer should know about real-time data's unifying abstraction** (2013) — *Kafka 의 *철학적 출발*
- Ben Stopford (Confluent), **Designing Event-Driven Systems** — *무료 PDF*
- AWS, **Amazon Kinesis Data Streams Developer Guide** — *공식 문서*
- Pinterest Engineering, **Kafka at Pinterest** — *Kinesis → Kafka 이주의 이유*
- Netflix Tech blog, **Keystone Real-time Stream Processing Platform**
- Capital One Tech, **Real-time Fraud Detection with Kinesis + Lambda**
- Uber Engineering, **Kafka at Uber — multi-region replication**
- Confluent Cloud 공식 문서 — *''Confluent Cloud vs MSK vs Kinesis''*
- *Redpanda* docs — *''Kafka 호환 *고성능 대안*''* 의 *제 3 의 길*
