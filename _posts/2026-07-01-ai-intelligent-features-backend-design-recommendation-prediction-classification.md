---
layout: post
title: "*AI 기반 *추천 / 예측 / 분류* 의 *백엔드 설계* — *모델 학습* 은 *알아서* 한다고 *치고*, *서빙 / 피처 / 지연 예산 / 피드백 루프* 가 *진짜 *백엔드 의 *일* 이다"
date: 2026-07-01 07:30:00 +0900
categories: [backend, ai, ml-engineering, spring-boot]
tags: [recommendation, prediction, classification, ml-serving, mlops, feature-store, spring-ai, onnx, triton, bentoml, ab-test, latency-budget, cold-start, feedback-loop]
---

> *"AI 기능 = 모델 학습"* 이라고 *말하는 사람과 *"AI 기능 = *모델 은 *데이터 사이언티스트 가 만들고*, *내가 할 일 은 *피처 / 서빙 / 지연 예산 / 피드백 루프 / A/B 테스트* 다"* 라고 *말하는 사람은 *PR 의 *변경 면적* 이 *완전히 다르다*.
>
> *추천 / 예측 / 분류* 는 *서로 다른 *문제* 지만 *백엔드 입장* 에서는 *동일한 5 가지 *공통 결정* 이 *재 등장* 한다. *어디서 *추론* 하는가 (인라인 / 비동기 / 사전계산 / 모델 서버)*, *피처를 *어디서 *읽는가 (DB / Redis / Feature Store)*, *지연 예산 은 *얼마인가 (50ms vs 500ms)*, *모델 실패 시 *무엇 으로 *떨어지는가 (fallback)*, *결과 가 *맞았는지를 *어떻게 *기록 하는가 (feedback)*. *모델 자체 의 *정확도* 는 *그 후* 의 *질문*.
>
> 이 글은 *Spring Boot 백엔드* 입장 에서 *AI 기능 을 *집어 넣을 때 *반드시 *결정 해야 하는 *것* 들을 *체계화* 한다. *모델 학습 의 *디테일* 은 *생략* — *백엔드 개발자 가 *프로덕션 에 *AI 기능 을 *얹기 위해 *알아야 하는 것* 만 *남긴다*.

---

## TL;DR

> *AI 기능 의 *백엔드 일* 은 *모델 코드 보다 *5 배 *많다*.
>
> 1. **3 가지 *지능형 기능* 의 *본질 차이***:
>    - **추천 (Recommendation)** — *"이 사용자에게 *무엇 을 *보여 줄까"* — *대량 후보 → 소수 정렬 의 *2 단 (candidate generation → ranking)*
>    - **예측 (Prediction)** — *"이 값 이 *얼마 가 될까"* — *회귀 (regression)*. 매출 / 이탈 확률 / ETA / 가격
>    - **분류 (Classification)** — *"이 입력 이 *어떤 카테고리 인가"* — *이진 / 다중 *클래스*. 스팸 / 사기 / 카테고리 자동 태깅 / 감성 분석
>
> 2. **4 가지 *서빙 아키텍처***:
>    - **인라인 (Inline)** — *API 핸들러 안에서 *직접 추론*. p95 < 50ms 필요.
>    - **비동기 (Async via Queue)** — *Kafka / SQS 로 *요청 분리*. ETA 분석 / 이미지 태깅.
>    - **사전 계산 (Precompute + Serve)** — *야간 배치 로 *답을 *DB / Redis 에 굳혀 두고 *조회 만*. 추천 의 *디폴트*.
>    - **모델 서버 (Triton / TF Serving / BentoML / vLLM)** — *Python 모델 을 *별도 *gRPC 서버* 로 *분리*. *Spring 은 *클라이언트*.
>
> 3. **Spring Boot 의 *실현 옵션***: Spring AI (1.0 GA, 2025), 직접 ONNX Runtime, Python 사이드카 (FastAPI / BentoML), gRPC Triton.
>
> 4. **Feature Store** — *학습 시 의 *피처 와 *추론 시 의 *피처 가 *일치 해야 한다* (training-serving skew 방지). Feast / Tecton / Hopsworks.
>
> 5. **Latency 예산** — *전체 200ms 의 *p95* 중 *모델 50ms 가 *현실 적*. *나머지 150ms 는 *피처 로딩 / 직렬화 / 네트워크*.
>
> 6. **Cold Start + Fallback** — *모델 결과 가 *없을 때 *무엇을 보여 줄지* 가 *기능 성공 의 *반*. *인기 순 / 룰 기반 / 카테고리 기본값*.
>
> 7. **피드백 루프** — *클릭 / 구매 / 평점 을 *학습 데이터 로 *환원 하지 않으면 *모델 이 *점점 *낡는다*. *Kafka → S3 → Airflow → 재 학습 → 모델 레지스트리 → 카나리 배포*.

---

## 0. *백엔드 개발자 가 *AI 기능 에서 *진짜 *책임지는 *것*

### 0.1 *흔한 *오해* — *"모델 학습 = AI 기능"*

JD / 블로그 에서 *"AI 기능 개발"* 이라는 단어 가 *나오면 *흔히 *떠올리는* 그림:

```
1. 데이터 수집
2. 모델 학습 (Jupyter Notebook 에서 sklearn / PyTorch)
3. 정확도 95% 달성
4. 끝
```

이건 *데이터 사이언티스트 의 *그림*. *백엔드 의 *그림* 은 *그 옆에서 *완전히 다르게 *진행* 된다:

```
1. 모델 의 *입력 (피처) 을 *프로덕션 에서 *어떻게 *모으는가
2. 추론 을 *언제 *어디서 *실행 하는가 (인라인 / 비동기 / 사전계산)
3. 모델 *서버 와 *Spring Boot 가 *어떻게 *통신 하는가 (HTTP / gRPC / FFI)
4. 지연 예산 안에 *맞추기 위해 *피처 / 결과 *캐싱* 을 *어떻게 *설계 하는가
5. 모델 *실패 시 *fallback* 은 무엇인가
6. A/B 테스트 의 *트래픽 라우팅 + 결과 측정* 은 *어떻게 하는가
7. 사용자 의 *클릭 / 행동* 을 *학습 데이터 로 *어떻게 *모으는가
8. 새 모델 버전 의 *카나리 배포* 와 *롤백* 은 *어떻게 하는가
```

> *"모델 정확도 95%"* 와 *"프로덕션 트래픽 의 *p99 가 *200ms 이하"* 는 *다른 *세계*. *백엔드 개발자 가 *책임 지는 것* 은 *후자*. *전자 가 *아무리 *높아도 *p99 가 *5 초* 면 *서비스 *불가능*.

### 0.2 *AI 기능 *백엔드 의 *5 결정*

```
┌──────────────────────────────────────────────────┐
│  사용자 요청                                       │
└──────────────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────────────┐
│  결정 ①  *어디서 *추론 하나*                       │
│         (인라인 / 비동기 / 사전계산 / 모델 서버)    │
└──────────────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────────────┐
│  결정 ②  *피처 를 *어디서 *읽나*                   │
│         (DB / Redis / Feature Store)              │
└──────────────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────────────┐
│  결정 ③  *지연 예산 은 *얼마*                       │
│         (50ms vs 500ms vs 5s)                     │
└──────────────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────────────┐
│  결정 ④  *모델 실패 시 *fallback*                   │
│         (인기 순 / 룰 / 캐시 / 빈 결과)             │
└──────────────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────────────┐
│  결정 ⑤  *피드백 을 *어떻게 *기록 하나*             │
│         (Kafka / S3 / DB / Click Tracker)         │
└──────────────────────────────────────────────────┘
```

*이 5 개 결정* 이 *추천 / 예측 / 분류* *3 가지 *기능 의 *공통 *축*. *모델 의 *알고리즘 (랜덤 포레스트 / XGBoost / Transformer)* 와는 *독립*.

---

## 1. *3 가지 *지능형 기능* 의 *본질 차이*

### 1.1 *추천 (Recommendation) — *대량 후보 → 소수 정렬*

> *"이 사용자 에게 *수천 ~ 수백만 개 의 *후보 중* *최적 의 *10 개* 를 *보여 줘"*

**구조 (Two-stage)**:

```
[Candidate Generation]  ← 1억 → 1000  (recall 중심, 빠른 ANN)
        ↓
[Ranking]               ← 1000 → 10   (precision 중심, 무거운 모델)
        ↓
[Re-ranking + 비즈니스 룰]  ← 10 → 10  (다양성, 광고, 신상품 강제 노출)
```

**대표 모델**:
- Candidate: *Two-Tower 임베딩 + ANN (FAISS / Milvus / pgvector)*
- Ranking: *DeepFM, Wide & Deep, DLRM, Transformer*
- 룰: 비즈니스 규칙 (광고 슬롯 N 개 강제, 다양성 보장)

**대표 사례**: Netflix / YouTube / Spotify / 쿠팡 / 아마존

**백엔드 의 *진짜 *난점***:
- 1 억 카탈로그 의 *임베딩 인덱스* 의 *주기적 *재 빌드*
- *콜드 스타트* — 신규 사용자 / 신규 상품 에 *대한 추천 부재*
- *피드백 루프* — 클릭 / 구매 / 좋아요 / 체류 시간 의 *수집 → 학습 데이터*
- *Position bias* — 1 위 에 노출 된 게 *실력* 인지 *위치 운* 인지 분리

### 1.2 *예측 (Prediction) — *연속 값 의 *추정 (회귀)*

> *"이 사용자 / 주문 / 상품 의 *수치* 가 *얼마 가 될까"*

**대표 사례**:
- **이탈 예측 (Churn)** — *향후 30 일 안에 *해지 할 확률* 0~1
- **CLV (Customer Lifetime Value)** — *향후 N 년 의 *누적 수익*
- **수요 예측 (Demand Forecasting)** — *내일 의 *주문 수*
- **ETA (Estimated Time of Arrival)** — 배송 / 차량 의 *도착 까지 분 단위*
- **가격 예측** — 부동산 / 중고차 가격
- **광고 CTR 예측** — *이 광고 가 *클릭 될 확률*

**대표 모델**: *XGBoost / LightGBM / CatBoost (95% 의 *실무 *기본값)*, *시계열 은 Prophet / DeepAR / Temporal Fusion Transformer*

**백엔드 의 *진짜 *난점***:
- *예측 시점* 과 *피처 시점* 의 *시간 일관성* (data leakage 방지)
- *결과 의 *불확실성* 표현 (예측 ± 신뢰 구간)
- *예측 가 *틀렸을 때* 의 *비즈니스 영향* (ETA 5 분 → 30 분 늦으면 환불)

### 1.3 *분류 (Classification) — *카테고리 의 *지정*

> *"이 입력 이 *N 개 카테고리 중 *어느 것 인가"*

**대표 사례**:
- **스팸 / 사기 탐지 (Fraud Detection)** — 이진 (스팸 / 정상)
- **이미지 / 텍스트 카테고리** — 다중 (옷, 가전, 음식, ...)
- **감성 분석 (Sentiment)** — 긍정 / 중립 / 부정
- **콘텐츠 모더레이션** — 욕설 / 폭력 / 음란
- **언어 감지** — 한 / 영 / 일 / 중
- **고객 문의 자동 분류** — *결제 / 배송 / 환불 / 기술*

**대표 모델**: *로지스틱 회귀 (간단 한 베이스라인), XGBoost, 그리고 *현대 의 *Transformer (BERT / DistilBERT / KoBERT) + 파인튜닝* 또는 *LLM zero-shot*

**백엔드 의 *진짜 *난점***:
- *threshold 튜닝* (사기 탐지 의 *False Positive 비용* 이 *얼마인가*)
- *클래스 불균형* — 사기 거래 가 *전체 의 *0.1%* 인 경우 의 *학습 / 평가*
- *연속 학습* — 새 사기 패턴 의 *빠른 적응*

### 1.4 *공통 점 — *3 가지 모두 *결국* *"모델(피처) → 점수"*

| 기능 | 출력 |
|---|---|
| 추천 | (아이템, 점수) × 1000 → 정렬 → 상위 10 |
| 예측 | 단일 수치 (확률 또는 회귀값) |
| 분류 | 카테고리 (또는 카테고리별 확률) |

> *모든 ML 모델 은 *결국 *입력 피처 → 점수 / 확률 / 수치 의 *함수*. *3 가지 기능 의 *차이* 는 *그 점수* 를 *어떻게 *해석 하느냐* (정렬 / 임계값 / 그대로) 의 *차이* 일 뿐. 그래서 *백엔드 의 *서빙 아키텍처* 는 *3 가지 가 *대부분 *공통*.

---

## 2. *4 가지 *서빙 아키텍처* — *어디서 *추론* 할 것인가*

### 2.1 *아키텍처 ① — *인라인 (Inline)*

```
[Request] → [Spring Controller] → [Service]
                                     ↓
                              [추론 직접 실행]
                                     ↓
                                  [Response]
```

**언제 쓰나**: *p95 < 50ms 의 *실시간 응답* 이 *필요* 한 *간단 한 모델*.

**구현 옵션**:
- *Spring AI 의 *EmbeddingClient* (LLM API 호출)
- *ONNX Runtime Java* — Python 학습 모델 을 *ONNX* 로 export → JVM 안 에서 직접 실행 (외부 호출 없음)
- *XGBoost4J* — XGBoost 모델 의 *Java 바인딩*
- *DJL (Deep Java Library)* — PyTorch / TensorFlow 모델 의 *Java 실행*

**예제 — ONNX Runtime 인라인 (사기 탐지)**:

```java
@Service
public class FraudDetector {

    private final OrtEnvironment env = OrtEnvironment.getEnvironment();
    private final OrtSession session;

    public FraudDetector(@Value("${ml.fraud.model-path}") String path) throws Exception {
        this.session = env.createSession(path);
    }

    public double scoreFraud(TransactionFeatures features) throws Exception {
        float[] inputArr = features.toArray();
        try (OnnxTensor tensor = OnnxTensor.createTensor(env, new float[][]{inputArr})) {
            try (OrtSession.Result result = session.run(Map.of("input", tensor))) {
                float[][] output = (float[][]) result.get(0).getValue();
                return output[0][1];  // 사기 클래스 확률
            }
        }
    }
}
```

**강점**: 추가 인프라 없음, 가장 낮은 latency, Spring 의 thread pool 활용 그대로

**약점**:
- 모델 이 *JVM 안 *에 있어 *모델 메모리 = Heap / Native* — 큰 모델 (BERT, GPT) 은 OOM
- *GPU 가속* 어려움 (ONNX Runtime CUDA 가능 하지만 복잡)
- *모델 업데이트* 마다 *애플리케이션 재배포*

### 2.2 *아키텍처 ② — *비동기 (Async via Queue)*

```
[Request] → [Spring Controller] → [Kafka Producer]
                                     ↓
                                [응답 즉시 반환 (202 Accepted)]

[Kafka Consumer] → [모델 추론] → [결과 DB / Webhook / WebSocket]
```

**언제 쓰나**:
- *즉시 응답* 이 *불필요* (이메일 / 푸시 알림 / 비동기 분석)
- *모델 추론 시간 이 *수 초 ~ 수 분* (예: 동영상 분석, 큰 LLM 답변)
- *백프레셔* 가 필요 (트래픽 폭주 시 큐 가 흡수)

**예제 — Kafka 기반 이미지 자동 태깅**:

```java
@Service
public class ImageTagController {

    private final KafkaTemplate<String, ImageTaggingTask> kafka;

    @PostMapping("/images/{id}/tag")
    public ResponseEntity<Void> requestTagging(@PathVariable UUID id) {
        kafka.send("image-tagging", new ImageTaggingTask(id, Instant.now()));
        return ResponseEntity.accepted().build();  // 202 — "받았다, 나중에 알려줄게"
    }
}

@KafkaListener(topics = "image-tagging", groupId = "image-tagger")
class ImageTagger {
    public void consume(ImageTaggingTask task) {
        List<String> tags = mlClient.tagImage(task.imageId());  // 수 초 걸려도 OK
        imageRepository.updateTags(task.imageId(), tags);
        webSocketPublisher.notify(task.userId(), "tags-ready");
    }
}
```

**강점**: 백프레셔, 재시도 / DLQ, 모델 서버 의 *자유 로운 *스케일링*

**약점**: 사용자 경험 의 *비동기 처리 (로딩 → 알림) 필요*

### 2.3 *아키텍처 ③ — *사전 계산 + 서빙 (Precompute + Serve)*

```
[야간 배치 작업]
   ↓
[모든 사용자 × 후보 의 *추천 / 예측 계산*]
   ↓
[결과 를 *Redis / DynamoDB / Postgres 에 *굳혀 둠*]

---

[Request] → [Spring Controller] → [Redis 조회] → [Response]
```

**언제 쓰나**:
- *추천 의 *디폴트* (사용자 마다 *오늘의 추천 10 개* 를 *밤새 계산*)
- *예측 의 *디폴트* (모든 고객 의 *이탈 확률* 을 *주 1 회 계산*)
- *p99 가 *수 밀리초* 여야 하는 *핫 패스*

**예제 — 야간 배치 추천 + Redis 서빙**:

```java
// 1. 배치 (Spring Batch + Python via REST)
@Scheduled(cron = "0 0 3 * * *")  // 매일 새벽 3 시
public void precomputeRecommendations() {
    List<User> users = userRepo.findAllActive();
    for (User u : users) {
        List<RecommendedItem> recs = mlClient.recommend(u.id(), 50);
        redis.opsForList().rightPushAll(
            "rec:user:" + u.id(),
            recs.stream().map(RecommendedItem::toJson).toList()
        );
        redis.expire("rec:user:" + u.id(), Duration.ofDays(2));
    }
}

// 2. 서빙 (단순 조회)
@GetMapping("/users/{id}/recommendations")
public List<RecommendedItem> recommend(@PathVariable UUID id) {
    List<String> json = redis.opsForList().range("rec:user:" + id, 0, 9);
    return json.stream().map(RecommendedItem::fromJson).toList();
}
```

**강점**:
- *p99 < 5ms* 의 *극한 *지연* (Redis 단순 조회)
- *모델 서버 가 *프로덕션 *부하* 와 *무관* (배치 시간 에 만 부하)
- *비싼 모델 (수 초 추론) 도 *사용 가능*

**약점**:
- *실시간 행동 반영 불가* (방금 본 상품 이 *추천 에 *반영 되려면 *내일*)
- *Hybrid* 가 *현실 *해법*: 사전계산 + *실시간 *재 랭킹*

### 2.4 *아키텍처 ④ — *모델 서버 (gRPC / HTTP)*

```
[Spring Boot]  ──(gRPC / HTTP)──→  [Python 모델 서버]
                                       - Triton (NVIDIA)
                                       - TF Serving (Google)
                                       - TorchServe (Meta)
                                       - BentoML
                                       - vLLM (LLM 전용)
                                       - Ray Serve
```

**언제 쓰나**:
- *큰 모델* (Transformer, LLM) — Java 안 에 *직접* 못 들고
- *GPU 활용* 이 *필수*
- *모델 의 *독립 배포* (Spring 재배포 없이 모델만 갱신)
- *Python 생태계* 의 *라이브러리 (transformers, sklearn) 그대로 활용*

**예제 — Spring Boot + Triton (gRPC)**:

```java
@Service
public class SentimentClassifier {

    private final InferenceServiceGrpc.InferenceServiceBlockingStub stub;

    public SentimentClassifier(@Value("${triton.host}") String host) {
        ManagedChannel channel = ManagedChannelBuilder
            .forAddress(host, 8001).usePlaintext().build();
        this.stub = InferenceServiceGrpc.newBlockingStub(channel);
    }

    public Sentiment classify(String text) {
        ModelInferRequest request = ModelInferRequest.newBuilder()
            .setModelName("sentiment-kobert")
            .addInputs(InferInputTensor.newBuilder()
                .setName("input_ids")
                .setDatatype("INT64")
                .addShape(1).addShape(128)
                .setContents(buildInputIds(text))
                .build())
            .build();
        ModelInferResponse response = stub.modelInfer(request);
        float[] logits = parseLogits(response);
        return Sentiment.values()[argmax(logits)];
    }
}
```

**강점**:
- 모델 / Spring 의 *완전 *분리* (각자 *독립 *배포 / 스케일링)
- *GPU 활용 최적*
- *모델 메모리* 가 *Spring Heap 과 *무관*

**약점**:
- 추가 인프라 (Triton 클러스터 + 모니터링)
- 네트워크 RTT (gRPC 5~20ms 추가)
- *protobuf 정의* 관리

### 2.5 *4 가지 *비교 *매트릭스*

| 측면 | 인라인 | 비동기 | 사전계산 | 모델 서버 |
|---|---|---|---|---|
| p95 latency | < 50ms | 비동기 (수 초~분) | < 10ms | 50~200ms |
| 모델 크기 한도 | 작음 (~100MB) | 무제한 | 무제한 (배치 시간) | 무제한 (GPU) |
| 인프라 비용 | 낮음 | 중간 (Kafka) | 중간 (Redis + Batch) | 높음 (모델 서버) |
| 실시간 행동 반영 | ✅ | △ | ❌ | ✅ |
| 모델 *독립 배포* | ❌ | △ | ✅ | ✅ |
| GPU 사용 | △ (복잡) | ✅ | ✅ (배치) | ✅ |
| 운영 복잡도 | 낮음 | 중간 | 중간 | 높음 |

> *현실 의 *대규모 추천 시스템* 은 *대체로 *③ + ④ + ①* 의 *Hybrid*: ③ 야간 배치 로 *후보 *생성* → ① 사용자 요청 시 *Redis 조회* + *실시간 피처 결합* → ④ 무거운 reranking 은 *Triton gRPC*.

---

## 3. *Spring Boot 의 *실현 옵션*

### 3.1 *Spring AI (1.0 GA, 2025)*

Spring 진영의 *공식* AI 추상화 레이어 (2025 1.0). *OpenAI / Anthropic / Bedrock / Vertex AI / Ollama / Azure OpenAI / Mistral* 등 *수십 개 *프로바이더 를 *공통 인터페이스 로 *추상화*.

```java
@Service
public class ProductDescriptionGenerator {
    private final ChatClient chat;

    public ProductDescriptionGenerator(ChatClient.Builder builder) {
        this.chat = builder.build();
    }

    public String generate(Product p) {
        return chat.prompt()
            .user(u -> u.text("상품 설명 50 자: {name}").param("name", p.name()))
            .call()
            .content();
    }
}
```

**제공 기능**:
- ChatClient (LLM 호출)
- EmbeddingClient (임베딩 생성)
- VectorStore (pgvector / Pinecone / Chroma / Milvus / Qdrant)
- RAG (Retrieval-Augmented Generation) 추상화
- Tool calling (LLM 이 *자바 메서드 호출* 가능)
- Advisors (메모리 / 모더레이션 / 토큰 카운팅)

**언제 쓰나**: *LLM 기반 기능* (텍스트 생성, 임베딩 검색, 챗봇). *고전적 ML (XGBoost, 분류기) 에는 *부적합*.

### 3.2 *ONNX Runtime + DJL*

전통적 ML 모델 (XGBoost, LightGBM, RandomForest, BERT) 의 *Java 인라인 실행*.

```xml
<!-- pom.xml -->
<dependency>
    <groupId>com.microsoft.onnxruntime</groupId>
    <artifactId>onnxruntime</artifactId>
    <version>1.18.0</version>
</dependency>
```

**워크플로**:
1. 데이터 사이언티스트 가 Python sklearn/PyTorch 로 모델 학습
2. ONNX 로 export (`skl2onnx`, `torch.onnx.export`)
3. Java 백엔드 가 `.onnx` 파일을 로드 후 직접 실행

**장점**: 외부 인프라 없음. 단일 jar 로 *AI 기능* 포함.
**단점**: 큰 모델 어려움, GPU 가속 복잡.

### 3.3 *Python 사이드카 (FastAPI / BentoML)*

```
[Spring Boot]  ──(HTTP)──→  [FastAPI / BentoML 사이드카]
                                - Python 환경
                                - PyTorch / sklearn / Transformers
                                - Docker 별도 컨테이너
```

**언제 쓰나**: *팀에 Python ML 엔지니어 있음*. *Spring 안 에 ONNX 박는 게 *고통* 인 경우.

**구조** (ASAT 의 *분석 사이드카* 와 *유사 한 패턴*):

```yaml
# docker-compose.yml
services:
  backend:
    image: my-spring-app
    environment:
      ML_SIDECAR_URL: http://ml-sidecar:8000
  ml-sidecar:
    image: my-ml-sidecar
    build: ./ml-sidecar
    ports: ["8000:8000"]
    deploy:
      resources:
        reservations:
          devices:
          - capabilities: [gpu]
```

```python
# ml-sidecar/main.py
from fastapi import FastAPI
from pydantic import BaseModel
import torch

app = FastAPI()
model = torch.load("model.pt", map_location="cuda")

class ChurnRequest(BaseModel):
    user_id: str
    features: list[float]

@app.post("/predict/churn")
def predict_churn(req: ChurnRequest):
    with torch.no_grad():
        score = model(torch.tensor(req.features).cuda()).item()
    return {"user_id": req.user_id, "churn_probability": score}
```

```java
// Spring Boot 클라이언트
@Service
public class ChurnPredictionClient {

    private final WebClient webClient;

    public ChurnPredictionClient(@Value("${ml.sidecar.url}") String url) {
        this.webClient = WebClient.create(url);
    }

    public double predictChurn(UUID userId, double[] features) {
        return webClient.post()
            .uri("/predict/churn")
            .bodyValue(Map.of("user_id", userId, "features", features))
            .retrieve()
            .bodyToMono(ChurnResponse.class)
            .map(ChurnResponse::churnProbability)
            .timeout(Duration.ofMillis(500))
            .onErrorReturn(0.0)  // ← Fallback: 모델 실패 시 0
            .block();
    }
}
```

### 3.4 *gRPC + Triton / TorchServe*

Python 사이드카 와 유사하지만 *Triton / TorchServe* 의 *전용 모델 서버 *프로토콜 (KServe v2, 또는 gRPC)*. *멀티 모델 / 동적 로딩 / 배치 처리* 의 *고성능 기능* 제공.

**장점**: 모델 *수십 개* 를 *한 서버* 에서 *서빙*, *동적 배치* (예: 50ms 안에 들어오는 요청 묶어 처리), *GPU 활용 최적화*.

**단점**: protobuf 관리, 운영 복잡.

### 3.5 *옵션 *결정 매트릭스*

| 상황 | 추천 옵션 |
|---|---|
| LLM 기능 (생성 / 임베딩) | Spring AI |
| XGBoost / sklearn 모델, p95 < 50ms | ONNX Runtime 인라인 |
| Python 라이브러리 *그대로* 사용, 팀에 Python 있음 | FastAPI / BentoML 사이드카 |
| GPU 추론, 다중 모델, 고 동시성 | Triton + gRPC |
| 추론 시간 > 1 초, 즉시 응답 불필요 | Kafka + 모델 서버 (③ + ④) |

---

## 4. *피처 (Feature) 의 *조달*

### 4.1 *피처 가 *어디서 *오는가*

추천 / 예측 / 분류 *모두 *입력 피처* 가 *필요*. *피처 의 *종류*:

| 피처 종류 | 예시 | 어디서 |
|---|---|---|
| **사용자 정적 피처** | 나이, 성별, 가입일, 등급 | RDB (user 테이블) |
| **사용자 동적 피처** | 최근 7 일 클릭 수, 평균 객단가 | DW / Redis (배치 갱신) |
| **실시간 행동 피처** | 방금 본 상품, 검색어 | Redis / 세션 |
| **컨텍스트 피처** | 시간 (요일/시각), 기기, 지역 | Request 헤더 |
| **아이템 피처** | 가격, 카테고리, 평점, 재고 | RDB (product 테이블) |
| **임베딩 피처** | user_embedding, item_embedding | pgvector / Milvus / Pinecone |

### 4.2 *Training-Serving Skew — *학습 / 서빙 의 *피처 일치 의 *함정*

> *프로덕션 의 *최대 *실수* — *학습 시 의 *피처 계산식* 과 *서빙 시 의 *계산식* 이 *다르다*.

흔한 실수:
- *학습*: Python pandas `df.groupby("user_id")["amount"].mean()` — 전체 기간 평균
- *서빙*: Java `WHERE user_id = ? AND created_at > NOW() - INTERVAL '30 days'` — 30 일 평균

*같은 이름 (avg_amount)* 인데 *다른 정의*. 모델 의 *정확도 가 *프로덕션 에서 *추락* 한다 (오프라인 95% → 온라인 60%). *Training-Serving Skew* 라고 부른다.

### 4.3 *Feature Store — *학습 과 *서빙 의 *공통 정의*

Feast / Tecton / Hopsworks / SageMaker Feature Store — *피처 정의 를 *한 곳 에 *코드 로 *고정* 하고, *오프라인 (학습용 batch)* 과 *온라인 (서빙용 low-latency lookup)* 양쪽에 *동일 계산 식* 을 *제공*.

```python
# features/user.py (Feast 예시)
@feature_view(
    entities=[user],
    ttl=Duration(days=30),
    source=BigQuerySource(table="user_activity"),
)
class UserActivityFeatures:
    avg_amount_30d: Float32 = avg("amount", window="30d")
    click_count_7d: Int64 = count("click", window="7d")
```

- *학습 시*: BigQuery 의 *과거 시점* 기준 *시간 일관성 있게* batch 추출 (*point-in-time correctness*)
- *서빙 시*: Redis / DynamoDB 의 *현재 값* 을 *밀리초 *조회*

> *Feature Store 의 *진짜 가치* 는 *피처 의 *시간 정합성* + *코드 의 *재사용*. 작은 팀 은 *과한 인프라*. *모델 수 > 10 개 또는 *모델 < 학습/서빙 skew 사고 *3 회 이상* 발생 시 *도입 검토*.

### 4.4 *간단 한 시작 — *피처 계산 함수 의 *공유*

Feature Store 가 *과 한* 작은 팀 의 *현실 적 *시작*:

- *Python 학습 코드* 와 *Java 서빙 코드* 가 *같은 SQL 또는 같은 *명세* 를 *읽도록 *피처 *정의 문서* 를 *git* 의 *단일 위치* 에 둠
- *피처 계산 식* 의 *단위 테스트* (Python + Java 모두)
- *학습 데이터 생성 SQL* 을 *Java 가 *Replay 가능 하게 *명시*

---

## 5. *지연 예산 (Latency Budget)*

### 5.1 *예산 분배*

사용자 가 *체감 하는 *p95 = 200ms* 의 *전형 적 분배*:

| 단계 | 예산 (ms) | 비고 |
|---|---|---|
| 클라이언트 → 게이트웨이 | ~20ms | TLS handshake (재사용 시 작음) |
| 인증 / 권한 확인 | ~5ms | JWT 파싱 + RBAC |
| 피처 로딩 (Redis / DB) | ~20ms | 캐시 히트 가정 |
| 모델 추론 | ~50ms | ← *모델 의 *진짜 예산* |
| 비즈니스 룰 / 후처리 | ~10ms | 광고 슬롯 / 다양성 / 필터 |
| 응답 직렬화 | ~5ms | JSON 직렬화 |
| 게이트웨이 → 클라이언트 | ~20ms | 네트워크 RTT |
| **여유 (variance)** | **~70ms** | GC, p95 buffer |
| **합계** | **~200ms** | |

> *모델 추론 50ms 가 *현실 적 예산*. *큰 Transformer (BERT-base CPU)* 는 *100~300ms* — *예산 초과*. *그래서 *Distillation, Quantization, ONNX 최적화* 가 *필수*. *또는 *③ 사전계산* 으로 *우회*.

### 5.2 *Latency 단축 *기법*

- **모델 압축**: Distillation (BERT → DistilBERT, 6 배 빠름), Quantization (FP32 → INT8, 4 배 빠름)
- **하드웨어**: GPU (T4 / A10), TPU, AWS Inferentia
- **배치 추론 (Dynamic Batching)**: Triton 의 *동적 배치* — 50ms 안 의 요청 묶어 한 번에 GPU 호출
- **피처 캐싱**: Redis 의 사용자 피처 캐시, *방금 본 상품* 만 새로 결합
- **결과 캐싱**: 같은 입력에 대한 결과 캐시 (단순 분류 / 임베딩)
- **사전 계산 fallback**: 사용자 요청 시 *야간 배치 결과* 를 *디폴트* 로 빠르게 반환

---

## 6. *Cold Start + Fallback — *모델 결과 가 *없을 때*

### 6.1 *4 가지 *Cold Start*

1. **신규 사용자** — 행동 이력 없음 → 협업 필터링 (CF) 의 *적용 불가*
2. **신규 아이템** — 임베딩 / 학습 데이터 없음 → 후보 풀에 *나타나지 않음*
3. **신규 카테고리** — 학습 데이터 의 *클래스* 에 없는 *새 유형*
4. **모델 서버 장애** — Triton down, gRPC 타임아웃

### 6.2 *현실 적 *Fallback*

| 상황 | Fallback |
|---|---|
| 신규 사용자 추천 | *인기 순* (전체 또는 카테고리별 Top 10) |
| 신규 아이템 추천 | *콘텐츠 기반* (텍스트/이미지 임베딩 의 유사도) |
| 신규 카테고리 분류 | *"기타" 클래스* 또는 *수동 큐* |
| 모델 서버 장애 | *직전 캐시 값*, *룰 기반*, *전 모델 (이전 버전)* |

```java
public List<RecommendedItem> recommend(UUID userId) {
    try {
        return mlClient.recommend(userId).timeout(Duration.ofMillis(100)).block();
    } catch (Exception e) {
        metrics.counter("recommend.fallback").increment();
        return popularItemsCache.getTopN(10);  // Fallback
    }
}
```

> *모델 *없는* 상태 가 *유저 체감 의 *80%* 를 *결정 한다* — 신규 사용자, 장애 시점, 새 상품. *Fallback 의 *품질* 이 *AI 기능 의 *진짜 *품질 의 *바닥*.

---

## 7. *A/B 테스트 + Online Metric*

### 7.1 *왜 *Offline metric 만 으로는 *안 되는가*

- 오프라인: *F1 / AUC / NDCG@10 / MAP* — *과거 데이터 의 *재현*
- 온라인: *CTR / 전환율 / 매출 / 체류 시간* — *실제 사용자 행동*

> 오프라인 metric 이 *95% AUC* 이어도 *온라인 CTR* 이 *떨어질 수 있다*. *Position bias, Novelty effect, Survivorship bias* 등 *오프라인 이 *측정 못 하는 *효과*. *A/B 테스트 가 *최종 *판단*.

### 7.2 *A/B 테스트 인프라*

```
[Request] → [Feature Flag / Split Service] → A or B
                                              ↓
                                     [모델 A or 모델 B]
                                              ↓
                                     [Result + Variant Tag]
                                              ↓
                                     [Tracking Log (Kafka)]
                                              ↓
                                  [BigQuery / Athena 분석]
```

대표 구현:
- *GrowthBook, LaunchDarkly, Optimizely, Statsig* (SaaS)
- *Spring 의 *Feature Flag* 라이브러리 (FF4J)
- *직접 구현* — Redis 의 사용자 → variant 매핑 + Kafka 로 click 로그

### 7.3 *측정 *주의 점*

- **Sample Size**: *통계 적 유의성* 위한 *최소 *사용자 수* 계산 (보통 *수천 ~ 수만*)
- **유저 식별 안정성**: 같은 유저는 *세션 / 일자 가 바뀌어도 *같은 variant*
- **노출 편향 (Exposure Bias)**: 한 variant 만 본 사용자만 측정 — 노출 한 모든 사용자 측정
- **Multiple Hypothesis Testing**: 여러 metric 동시 측정 시 *Bonferroni 보정*
- **단기 / 장기 효과**: *클릭 율* (단기) 과 *재방문 / 구독 율* (장기) 의 *분리*

---

## 8. *피드백 루프 + 재 학습 (MLOps)*

### 8.1 *피드백 의 *수집*

```
[사용자 클릭 / 구매 / 평점]
         ↓
[Frontend tracker → Kafka click-events]
         ↓
[Stream → S3 (Parquet, 일별 파티션)]
         ↓
[Airflow / Prefect daily job]
         ↓
[학습 데이터 셋 갱신 → 모델 재 학습 → 평가]
         ↓
[Model Registry (MLflow / SageMaker)]
         ↓
[카나리 배포 (5% 트래픽 신 모델, 95% 기존)]
         ↓
[A/B 비교 → 통계 적 유의 → 100% 전환]
```

### 8.2 *재 학습 주기*

| 모델 | 재 학습 주기 | 이유 |
|---|---|---|
| 사기 탐지 | 매일 또는 매주 | 사기 패턴 변화 빠름 |
| 추천 (랭킹) | 매일 | 신상품 / 트렌드 |
| 추천 (임베딩) | 주 1 ~ 월 1 | 비싸고 천천히 변함 |
| 분류 (감성, 카테고리) | 분기별 | 변화 느림 |
| 예측 (이탈, ETA) | 월 1 ~ 분기별 | 도메인 안정 적 |

### 8.3 *모델 *드리프트 (Drift) *모니터링*

- **Data Drift**: 입력 피처 의 *분포 변화* (예: 코로나로 *온라인 결제 비율* 폭증)
- **Concept Drift**: 입력 → 정답 의 *관계* 변화 (예: 사기 패턴 변경)
- **Performance Drift**: Online metric 의 *하락* (CTR 5% → 3.5%)

모니터링 도구: *Evidently, Arize AI, Fiddler, WhyLabs, Weights & Biases*

---

## 9. *흔한 *반(反) 패턴*

### 9.1 *"모델 정확도 95% 면 *프로덕션 *합격"*

오프라인 95% 가 *온라인 60%* 로 떨어지는 *흔한 원인*:
- *Training-Serving Skew*
- *Distribution Shift* (학습 시점 ↔ 서빙 시점 의 *시간 차 *3 개월*)
- *Selection Bias* (학습 데이터 가 *기존 시스템 의 *추천 결과* 만 포함)

### 9.2 *"AI 기능 = LLM API 호출 한 번"*

LLM 호출 *그 자체* 는 *AI 기능 의 *5%*. *나머지 95%*:
- 프롬프트 관리 (버저닝, A/B)
- 토큰 비용 모니터링
- 모더레이션 / Guardrails
- Hallucination 대응 / RAG
- 비동기 vs 스트리밍
- 캐싱 (의미 적 유사 입력의 결과 재사용)

### 9.3 *"모델 서버 의 *고가용성 = Spring 의 *고가용성"*

Triton 1 대 가 *내려가면 *전체 추천 다운*. *Spring 은 *최소 2 대 *Triton + Fallback (인기 순) + Circuit Breaker* 가 필요.

### 9.4 *"피드백 수집 = 나중에 하면 됨"*

피드백 로그 가 *없으면 *재 학습 *불가능*. *초기 3 개월 의 *클릭 / 구매 로그 가 *없으면 *모델 의 *첫 *재학습 이 *3 개월 *지연*. *기능 출시 와 *동시 *로그 수집* 이 *필수*.

### 9.5 *"피처 캐시 *없이 *모든 요청 마다 *DB 조회"*

피처 5 개 의 *DB 조회 가 *각각 *20ms = 총 100ms*. *예산 *초과*. *Redis 단일 hash 로 *1 회 조회* 5ms 가 *현실*.

---

## 10. *정리

### 10.1 *3 가지 *기능 의 *공통 결정*

| 결정 | 답의 *축* |
|---|---|
| ① 추론 위치 | 인라인 / 비동기 / 사전계산 / 모델 서버 |
| ② 피처 조달 | DB / Redis / Feature Store |
| ③ 지연 예산 | 50ms / 500ms / 5s |
| ④ Fallback | 인기 / 룰 / 캐시 / 빈 결과 |
| ⑤ 피드백 | Kafka → S3 → 재 학습 → 카나리 |

### 10.2 *Spring Boot 의 *기본 *권장 출발점*

- *LLM 기능* (생성 / 임베딩 / 검색) → **Spring AI**
- *전통적 ML 모델 (XGBoost / 분류기)* → **ONNX Runtime 인라인** (시작 점)
- *Python 라이브러리 필수* → **FastAPI 사이드카** (ASAT 의 *Python 분석 사이드카* 패턴 과 동일)
- *GPU / 다중 모델 / 고 부하* → **Triton + gRPC**
- *대규모 추천* → **사전계산 + Redis + 실시간 재 랭킹**

### 10.3 *시니어 가 *AI 기능 PR 에서 *질문 하는 *5 가지*

1. *Latency 의 *p95 / p99 는 어디? * fallback 은 무엇?
2. *피처 가 *학습 시 와 *동일 한 정의 인가? (training-serving skew)*
3. *모델 서버 가 *down 되면 *어떻게 되나?*
4. *피드백 (클릭/구매) 이 *Kafka 에 *흘러가나? * 학습 데이터 까지 *루프 가 *돌아가나?*
5. *A/B 테스트 인프라 가 *있나? * 카나리 배포 가 *가능 한가?*

### 10.4 *마지막 한 마디

> *AI 기능 의 *진짜 *백엔드 일* 은 *모델 의 *옆* 에서 *벌어진다*. *모델 정확도* 는 *5% 의 *질문*. *피처 / 서빙 위치 / 지연 예산 / Fallback / 피드백 루프* 의 *5 가지 결정* 이 *95% 의 *프로덕션 성공* 을 *결정*.
>
> *AI 가 *마법 처럼 *느껴지지만 *프로덕션 의 *AI 시스템* 의 *80%* 는 *전통적 *분산 시스템 의 *문제*. *캐시, 큐, 백프레셔, fallback, 모니터링, 카나리 배포, 피드백 루프* — *백엔드 개발자 가 *이미 *알고 있는 *언어*. *나머지 20%* 만 *모델 / 피처 / metric 의 *ML 어휘 를 *추가* 로 *배우면 된다*. *모델 학습 부터 *공부 하려고 *덤비면 *프로덕션 에 *못 *닿는다*. *반대 방향 — *백엔드 의 *5 결정 부터* — 이 *현실 적 *진입로*.
