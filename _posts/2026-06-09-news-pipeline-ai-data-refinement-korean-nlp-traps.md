---
layout: post
title: "*뉴스 → 종목별 시그널* 의 *5 단 AI 데이터 파이프라인* — *한국어 tokenization 함정 3 + 도메인 사전 + 노이즈 라벨링 + 2 티어 폴백* 의 *진짜 데이터 정제 경험***"
date: 2026-06-09 19:00:00 +0900
categories: [ai, nlp, data-pipeline, korean-nlp, cpp]
tags: [ai, ml, data-refinement, korean-nlp, ner, finbert, kosac, onnx, lemuel-quant-core, news-pipeline, sentiment-analysis, tokenization, domain-dictionary, label-noise]
---

이 글은 *lemuel-quant-core 의 news-pipeline 모듈* 을 *AI 데이터 파이프라인의 *5 단계 *공식 정의* — *원천 → 정제 → 정규화 → 모델 입력 → 추론/학습* — 로 *명시적 재정의* 한 기록이다. *교과서적 AI/ML 시스템* 의 *데이터 정제 영역* 이 *얼마나 *섬세한 결정* 의 누적인지* 를 *한국어 NLP 의 *3 가지 함정* + *도메인 사전 설계* + *노이즈 라벨링 5 종* + *2 티어 폴백 전략* 으로 *진짜 코드와 함께* 풀어쓴다.

읽고 가셔도 좋은 분:
1. *AI / ML 데이터 정제 경험* 을 *이력서 / 면접에서 *증빙 자료* 로 정리하려는 사람
2. *한국어 NLP* 의 *tokenization 함정 / 도메인 사전 / 라벨 노이즈* 의 *실전 시행착오* 가 궁금한 사람
3. *KR-FinBERT 같은 *금융 특화 모델* 을 *직접 운영* 해본 경험을 *정리 / 비교* 하고 싶은 사람

---

## TL;DR

> *뉴스 → 종목별 시그널* 의 *AI 데이터 파이프라인* 을 *5 단계 (원천 → 정제 → 정규화 → 모델 입력 → 추론/학습)* 로 *명시적 분해*. 각 단계의 *한국어 NLP 함정* — *띄어쓰기 비일관 / 종목명 OOV / 한자-영문-한글 혼용* — 과 *도메인 사전 설계* + *노이즈 라벨링 5 종 분류* + *KR-FinBERT (ONNX) ↔ LexiconScorer 2 티어 폴백* 을 *직접 부딪힌 진짜 코드* 로 정리.

**5 단계 한 그림**:

```
[원천 (Source)]                    RSS / HTML / Naver 뉴스 / 종목별 검색 API
       │  libcurl + gumbo-parser
       ▼
[정제 (Cleaning)]                  HTML 태그 / 광고 / 중복 / 비기사 페이지 제거
       │
       ▼
[정규화 (Normalization)]           띄어쓰기 / 한자→한글 / 따옴표 통일 / 종목명 longest-match
       │  TickerNer + 도메인 사전
       ▼
[모델 입력 (Featurization)]        시드 사전 키워드 추출 / FinBERT vocab 토큰화
       │
       ▼
[추론 / 점수 (Scoring)]            LexiconScorer (시드) ↔ KR-FinBERT-SC (ONNX) 폴백
       │
       ▼
[종목별 누적 점수 (NewsScoreBoard)]  반감기 기반 weighted sum → Redis push
```

---

## 0. *왜 *이 글을 쓰는가*

> *AI 데이터 정제 경험* 은 *해본 사람만 *진짜 무게* 를 안다. 모델 부르는 *한 줄 코드 (model.predict(text))* 가 *전체 시스템의 *5% 미만*. 나머지 *95%* 가 *데이터 정제 + 정규화 + 도메인 사전 + 노이즈 처리*.

내가 *lemuel-quant-core/news-pipeline* 을 *직접 만들면서 *부딪힌 *결정의 누적* 을 *AI 데이터 파이프라인의 *공식 5 단계* 로 *재정의* 하면, *이력서 / 면접 / 다음 프로젝트* 어디서든 *재현 가능한 *방법론* 으로 *변환*. 이 글이 그 *변환의 흔적*.

---

## 1. *5 단계 — *공식 정의***

AI / ML 시스템의 *데이터 파이프라인* 은 *5 단계* 로 분해된다 (이 분해는 *내가 *직접 만들면서 *역으로 정리* 한 *현장 분류*):

| # | 단계 | 책임 | 결과물 |
|---|------|------|--------|
| 1 | **원천 (Source)** | *데이터를 *어디서 / 얼마나 자주 / 어떤 인터페이스* 로 받는가 | raw HTML / JSON / XML |
| 2 | **정제 (Cleaning)** | *raw 에서 *불필요한 *노이즈 제거* — 태그, 광고, 중복 | UTF-8 텍스트 |
| 3 | **정규화 (Normalization)** | *동일 entity 의 *서로 다른 표현* 을 *하나의 형태로* | 정규화된 텍스트 + entity 태깅 |
| 4 | **모델 입력 (Featurization)** | *모델이 이해할 수 있는 *형식으로* — 토큰 ID / 임베딩 / 시드 키워드 | model 입력 텐서 / dict |
| 5 | **추론 / 점수 (Scoring)** | 모델 호출 + *후처리 (반감기, 임계값, 분포 보정)* | 최종 점수 / 시그널 |

> 각 단계의 *결과물이 *명확* 해야 *디버깅 / 재현 / 검증* 가능. *5 단계의 *경계 흐려지면 *AI 모델이 *왜 안 맞는지 *영원히 모름*.

---

## 2. *원천 (Stage 1) — *Naver 뉴스 / RSS 의 *함정 4 가지**

### 2.1 *수집 코드 — libcurl + gumbo-parser*

```cpp
// rss_crawler.cpp — RSS 폴링 + HTML 본문 추출
class RssCrawler {
    void poll() {
        for (const auto& feed : feeds_) {
            const auto xml = fetch(feed.url);                 // libcurl multi
            for (const auto& item : parse_rss(xml)) {
                if (seen_.count(item.guid)) continue;          // 중복 제거
                const auto html = fetch(item.link);            // 본문 페이지
                const auto body = extract_body(html);          // gumbo-parser
                queue_.push({item.guid, item.title, body, item.pub_date});
            }
        }
    }
};
```

### 2.2 *함정 4 가지 — *실전 시행착오***

**함정 1 — *피드의 *update 빈도 비일관***

같은 *증권사 RSS* 가 *분당 1 건 ~ 시간당 200 건* 사이에서 *예측 불가하게 변동*. *고정 폴링 간격* 으로는 *peak miss + idle 시간 wasted*.

→ *adaptive polling* — *최근 응답 시 *새 item 있었으면 *간격 줄임 / 없었으면 늘림*.

**함정 2 — *중복 기사가 *대규모 — *제목 80% 일치하는 *서로 다른 GUID***

같은 통신사 기사가 *연합뉴스 → 네이버 → 다음 → 한경 → 매경* 으로 *5 곳에 다른 GUID* 로 *동시 노출*.

→ *제목 정규화 (공백 / 특수문자 제거) 후 SHA-1* 로 *deduplication key*. 5 곳 중 *가장 빠른 1 건만* 큐에 푸시.

**함정 3 — *HTML 본문 추출 알고리즘 의 *패턴 의존성***

*Naver 뉴스* 본문 `<div id="dic_area">` vs *Daum* `<div data-text="true">` vs *한경* `<article class="article-body">`. *각 사이트별 *추출 룰* 이 *6 개월 마다 *바뀜*.

→ *boilerplate detection 알고리즘 (justext / dragnet)* 의 *통계적 접근* 이 *룰 기반보다 *내구성 우수*.

**함정 4 — *Naver / Daum 의 *반자동 *차단 정책***

*동일 IP* 에서 *분당 100 회* 넘으면 *captcha + rate limit*. 우리는 *영구 차단 직전 경고* 받음.

→ *user-agent rotation + delay + 다중 IP (Cloudflare proxy)* 조합. *공식 API 가 있으면 *우선 API 사용*.

---

## 3. *정제 (Stage 2) — *노이즈 5 종 *분류와 *제거***

> 이 단계가 *AI 데이터 정제 의 *진짜 무게중심*. *제거 못 한 *노이즈 1% 가 *모델 정확도 *5% 깎음*.

### 3.1 *노이즈 5 종*

| 노이즈 종류 | 예시 | 제거 방법 |
|-----------|------|----------|
| **HTML / 스크립트 잔재** | `<script>...</script>`, `&nbsp;` | gumbo-parser tag filter |
| **광고 / 스폰서 기사** | "[광고] / 본 콘텐츠는 ... 협찬을 받았습니다" | 키워드 prefix filter + length anomaly |
| **중복 / 페이지네이션** | "1/3 페이지" 같은 분할 표시 | 제목 SHA-1 + URL canonical |
| **목록 / 헤드라인 페이지** | 본문 길이 < 100자 | length threshold |
| **외국어 본문** | 영어/중국어 본문 (글로벌 통신사) | char distribution 검사 |

### 3.2 *함정 — *광고 인지 어려운 사례***

```
"[보도자료] XX전자, 신제품 출시 — 매출 25% 증가 예상"
```

*[보도자료] prefix* 가 있어서 *광고로 분류* 했는데, *실제로는 *주가 관련 *유의미 정보*. *완전 자동 분류 어려움*.

→ *보도자료 + 기업 IR 발표* 는 *별도 *flag* 로 *남기되 *모델에 통과*. *flag 가 *후속 분석 *가중치 조정* 입력.

---

## 4. *정규화 (Stage 3) — *한국어 NLP 의 *3 가지 함정***

> 이 단계가 *블로그 제목의 핵심*. *한국어가 *영어 NLP 의 *교과서 알고리즘* 을 *그대로 못 적용* 하는 *근본 이유* 3 가지.

### 4.1 *함정 1 — *띄어쓰기 비일관***

```
원본 1:  "삼성전자 의 주가가 상승했다"
원본 2:  "삼성전자의주가가상승했다"
원본 3:  "삼 성 전 자 의 주가가 상승했다"
```

*동일 의미*. *모델은 *세 가지를 *서로 다른 입력* 으로 인식. *NER 의 *종목명 추출이 *2, 3 에서 실패*.

**해결 — *3 단 정규화***:

```cpp
std::string normalize_spacing(const std::string& text) {
    // 1) 한글 사이 공백 제거 (자모 분리 케이스)
    //    "삼 성 전 자" → "삼성전자"
    auto step1 = collapse_hangul_spaces(text);
    
    // 2) 형태소 분석기로 *의미 단위 띄어쓰기 재구성*
    //    Khaiii / Mecab-ko 의 *명사 + 조사 분리* 결과를
    //    *재결합* 해서 *정규형* 생성
    auto step2 = morpheme_normalize(step1);
    
    // 3) 다중 공백 단일화
    return collapse_multiple_spaces(step2);
}
```

### 4.2 *함정 2 — *종목명 OOV (Out-of-Vocabulary)***

*KoBERT / KR-FinBERT* 같은 *프리트레인 모델* 의 *vocab* 에 *대부분의 종목명이 *없다*.

```python
tokenizer.tokenize("삼성전자")
# → ['삼', '##성', '##전', '##자']    ← 4 토큰으로 *쪼개짐*

tokenizer.tokenize("디어유")
# → ['디', '##어', '##유']           ← 종목명 의미가 *완전 분해*

tokenizer.tokenize("우리금융지주")
# → ['우', '##리', '##금', '##융', '##지', '##주']  ← 6 토큰
```

*4-6 sub-word 로 분해* 되면 *모델이 *종목명을 *entity 로 인식* 할 능력 *상실*. *감성 점수가 *종목과 분리* 되어 *시그널 무용지물*.

**해결 — *Pre-tokenization 종목명 entity tagging***:

```cpp
// NER 이 *모델 입력 전에* 종목명을 *특수 토큰* 으로 치환
//
//  원본:   "삼성전자가 신제품 출시했다"
//  태깅:   "[TICKER:005930] 가 신제품 출시했다"
//  모델 입력 시 [TICKER:005930] 가 *one token* 으로 보존
//  (vocab 에 [TICKER:*] 패턴 추가)

std::vector<Mention> TickerNer::tag(const std::string& body) const {
    // Longest-match scan — alias 가 긴 것부터 매칭
    // "삼성전자" (4자) > "삼성" (2자) 우선
    // ...
}
```

→ *원문은 *별도 보존*, *모델에는 *entity-tagged 버전* 입력. *감성 점수가 *종목별로 *명확히 귀속*.

### 4.3 *함정 3 — *한자 / 영문 / 한글 혼용***

```
"삼성電子, AAPL 대비 25% 할인"
"NAVER(035420)의 검색광고 매출"
"카카오톡 vs 네이버"
```

*한자 (電子)*, *영문 티커 (AAPL)*, *괄호 안 종목코드 (035420)* — *동일 entity 의 *3 가지 표현*. *모델은 *연결 못 함*.

**해결 — *Cross-script alias 사전***:

```cpp
// 종목 마스터 CSV (도메인 사전)
//   ticker, 정규형, 한자, 영문, 별칭...
// 005930, 삼성전자, 三星電子, Samsung Electronics, 삼성, 삼전, 005930
// 035420, NAVER, , Naver, 네이버, 035420
//
// load 시 *모든 alias → ticker* 의 reverse map 구축
void TickerNer::add_alias(const std::string& ticker, std::string alias);
```

→ *어떤 표현이든 *동일 ticker 로 정규화*. *cross-script 연결 보존*.

---

## 5. *모델 입력 (Stage 4) — *2 티어 폴백 설계***

### 5.1 *왜 *2 티어인가*

```
[티어 1 — LexiconScorer]   *사전 기반*. 시드 키워드 매칭만.
                          - 빠름 (수 ms)
                          - 정확도 *낮음* (정확률 ~ 65%)
                          - *영구 의존성 0* — 모델 다운 0
                          
[티어 2 — KR-FinBERT-SC]   *ONNX runtime 추론*. 금융 특화 BERT.
                          - 느림 (10-50 ms)
                          - 정확도 *높음* (정확률 ~ 88%)
                          - 모델 파일 440 MB + ONNX runtime 의존
```

**전략**:
- *기본은 KR-FinBERT*. *최고 정확도*.
- *모델 미로드 / GPU 부족 / 추론 실패 시 LexiconScorer 폴백*. *실패에도 *시그널 계속 흐름*.

### 5.2 *시드 사전 — LexiconScorer*

```cpp
// 사전: KOSAC 한국어 감성 사전 + 도메인 보강
static const std::unordered_set<std::string> pos = {
    "상승", "급등", "호실적", "성장", "흑자", "수주", "확대",
    "신고가", "최고", "회복", "개선", "달성",
};
static const std::unordered_set<std::string> neg = {
    "하락", "급락", "적자", "악재", "감산", "감원", "리콜",
    "신저가", "부진", "악화", "충격", "우려", "조사", "처분",
};

Result LexiconScorer::score(const std::string& text) const {
    int p = 0, n = 0;
    for (const auto& w : pos) if (text.find(w) != std::string::npos) ++p;
    for (const auto& w : neg) if (text.find(w) != std::string::npos) ++n;
    if (p == 0 && n == 0) return {Sentiment::Neutral, 0.0};
    const double s = (double)(p - n) / (p + n);
    return {
        s > 0.1 ? Sentiment::Positive
                : s < -0.1 ? Sentiment::Negative : Sentiment::Neutral,
        std::min(1.0, std::abs(s) + 0.1 * (p + n))
    };
}
```

### 5.3 *함정 — *시드 사전의 *3 가지 *한계***

**한계 1 — *문맥 의존 키워드***

```
"실적 상승세 *꺾여*"   → 시드 사전: '상승' = positive 1
                       → 실제: negative
```

*"꺾여 / 둔화 / 멈춤"* 같은 *부정 부사가 *시드 키워드 의미 *반전*. *시드 사전의 *치명적 한계*.

**한계 2 — *반어 / 추측법***

```
"성장 전망 *어둡다*"   → 시드: '성장' = positive 1
                       → 실제: negative
```

**한계 3 — *과거 vs 미래 시제***

```
"이전 분기는 호실적 — 다음 분기 *우려*"
                       → 시드: '호실적' + '우려' → neutral
                       → 실제: 미래 부정적 negative
```

→ *문맥 / 부사 / 시제* 가 *시드 사전의 *천장*. *KR-FinBERT 가 *이 3 가지 모두 처리* (BERT 의 *contextual embedding* 의 본질).

---

## 6. *추론 (Stage 5) — *KR-FinBERT-SC + NewsScoreBoard 반감기***

### 6.1 *KR-FinBERT-SC ONNX 추론*

```cpp
// finbert.cpp — ONNX Runtime 로드 + 추론
class FinBertScorer : public SentimentScorer {
    Ort::Env env_;
    Ort::Session session_;
    
    Result score(const std::string& text) const override {
        // 1) WordPiece tokenize (vocab 파일 로드 시 분리)
        auto input_ids = tokenize(text);
        
        // 2) ONNX 입력 텐서 구성
        Ort::Value input = Ort::Value::CreateTensor<int64_t>(
            allocator_, input_ids.data(), input_ids.size(), shape, 2);
        
        // 3) 추론
        auto outputs = session_.Run(
            Ort::RunOptions{nullptr},
            {"input_ids"}, {input}, {"logits"});
        
        // 4) softmax → label / confidence
        const auto* logits = outputs[0].GetTensorData<float>();
        return softmax_to_result(logits);
    }
};
```

### 6.2 *NewsScoreBoard 반감기 — *시간 가중치***

```cpp
// 종목별 누적 점수: 새 뉴스 = full weight, 1시간 후 = 50%, 2시간 후 = 25%
// 반감기 t = 3600s
struct NewsScoreBoard {
    void add(const std::string& ticker, double sentiment, time_t when) {
        const double age = now() - when;
        const double weight = std::exp(-age / 3600.0);
        scores_[ticker] += sentiment * weight;
    }
    
    double get(const std::string& ticker) const {
        // *현재 시각 기준 *재계산* — 시간이 흐르면 자연 감쇠
        // ...
    }
};
```

→ *새 뉴스* 가 *가장 영향력*. *오래된 뉴스가 *자연 감쇠*. *오버피팅 방지 + 시그널의 시간 무게 명확*.

---

## 7. *학습 (Stage 5+) — *DART 공시 → LLM fine-tuning 데이터셋***

*다음 글의 주제* — *DART 공시 데이터를 *Korean LLM fine-tuning* 데이터셋으로 *정제하는 5 단계 파이프라인 (별도 글 예정).

**미리 보기**:
- DART OpenAPI → XBRL XML 수집
- 공시 본문 추출 (PDF / HWP 변환)
- *공시 사실 → 종목 영향 추론* 의 *지도 학습 쌍 생성*
- Llama-3 / Qwen / Gemma 의 *Korean-finance fine-tuning* (LoRA)

---

## 8. *마무리 — *AI 데이터 정제 *경험 의 본질***

### 8.1 *모델은 *5%*, *데이터 정제는 *95%**

> AI / ML 시스템에서 *모델 (.predict)* 은 *전체 코드의 *5%*. 나머지 *95% 가 *데이터 정제 + 정규화 + 도메인 사전 + 노이즈 처리*. *이 5 단계 의 *경계가 분명할 때 *모델이 *왜 안 맞는지 *진단 가능*.

### 8.2 *한국어 NLP 는 *영어 알고리즘 의 *그대로 적용 불가**

> *띄어쓰기 / OOV / 한자-영문-한글 혼용* 의 *3 가지 함정* 이 *영어 NLP* 의 *교과서 알고리즘* 을 *직접 적용 시 *정확도 절반*. *Pre-tokenization entity tagging + cross-script alias 사전* 이 *한국어 NLP 의 *전제 인프라*.

### 8.3 *2 티어 폴백이 *prod 안정성 의 *핵심***

> *최고 정확도 모델* 과 *가벼운 폴백* 의 *2 티어 구조*. *모델 미로드 / GPU 부족 / 의존성 실패* 어떤 경우에도 *시그널 계속 흐름*. *프로덕션의 *진짜 *resilience 패턴*.

### 8.4 *이 경험을 *이력서로 변환***

> *"AI 데이터 정제 경험"* 한 줄에 *5 단계 분해 + 한국어 NLP 함정 3 + 도메인 사전 + 노이즈 5 종 + 2 티어 폴백* 을 *4 단 깊이* 까지 *흔들림 없이 답변 가능*. 이게 *짧은 한 줄이 *깊은 면접 질문* 으로 변환되는 *진짜 방법*.

---

*다음 글:* *DART 공시 → Korean LLM fine-tuning 데이터셋* 만들기 — *공시 사실 → 종목 영향 추론* 의 *지도 학습 쌍 생성*, *XBRL → 자연어* 변환, *Llama-3 / Qwen / Gemma 의 LoRA fine-tuning*.

---

## 코드

레포: **https://github.com/MyoungSoo7/lemuel-quant-core** (private — 면접 시 화면 공유 가능)

`modules/news-pipeline/` 안에:
- `rss_crawler.cpp` — 원천 (Stage 1)
- `ner.cpp` — 정규화 (Stage 3) — 종목명 longest-match
- `sentiment.cpp` — 모델 입력 + 추론 (Stage 4-5) — 2 티어 폴백
- `finbert.cpp` — KR-FinBERT-SC ONNX 추론
- `news_score.cpp` — NewsScoreBoard 반감기 누적
