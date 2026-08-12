---
layout: post
title: "LLM/RAG 기반 AI 서비스 분석·설계 — 어디서 조용히 깨지고, 무엇부터 고도화할 것인가"
date: 2026-08-12 21:00:00 +0900
categories: [AI, 아키텍처]
tags:
  [
    RAG,
    LLM,
    Retrieval,
    Vector Search,
    Evaluation,
    RAGAS,
    Context Engineering,
    분석설계,
  ]
---

RAG를 붙이는 일 자체는 어렵지 않다. 문서를 자르고, 임베딩하고, top-k를 프롬프트에 넣으면 데모는 그날 돈다. 어려운 건 **그게 틀렸을 때 알아채는 것**이다.

RAG 시스템의 최악의 실패는 "모른다"가 아니라 "근거 없이 답한다"이다. 검색이 엉뚱한 청크를 물어와도 파이프라인은 예외를 던지지 않는다. HTTP 200이 떨어지고, 문장은 매끄럽고, 사용자는 그것을 믿는다. 장애 알람은 울리지 않는다. 이 글은 그 조용한 실패 지점을 단계별로 분해하고, 무엇을 먼저 측정하고 무엇부터 고도화해야 하는지를 설계 관점에서 정리한 것이다.

주장은 가급적 1차 자료(원논문·벤더 공식 문서)에만 기댔고, 벤더 자체 벤치마크는 그렇다고 명시했다.

---

## 1. RAG의 설계상 가치는 "정확도"가 아니다

RAG라는 이름을 붙인 원논문은 Lewis 등의 2020년 NeurIPS 논문이다.[^lewis] 이 논문의 핵심 프레이밍은 **parametric memory**(사전학습된 seq2seq 모델의 가중치)와 **non-parametric memory**(위키피디아의 dense vector index)를 결합한다는 것이다. 검색기는 DPR, 생성기는 BART였다.

논문은 검색된 문서 $$z$$ 를 **잠재변수로 두고 top-$$K$$ 근사로 주변화(marginalize)** 한다. 주변화를 출력 단위로 하느냐 토큰 단위로 하느냐에 따라 두 정식화가 갈린다.[^lewis] 문서 하나가 전체 시퀀스를 책임지는 RAG-Sequence는

$$
p_{\text{RAG-Seq}}(y \mid x) \;\approx\; \sum_{z \in \text{top-}K(p(\cdot \mid x))} p_\eta(z \mid x) \prod_{i}^{N} p_\theta(y_i \mid x, z, y_{1:i-1})
$$

이고, 토큰마다 다른 근거를 쓸 수 있는 RAG-Token은 합과 곱의 순서가 뒤집힌다.

$$
p_{\text{RAG-Token}}(y \mid x) \;\approx\; \prod_{i}^{N} \sum_{z \in \text{top-}K(p(\cdot \mid x))} p_\eta(z \mid x)\, p_\theta(y_i \mid x, z, y_{1:i-1})
$$

여기서 $$p_\eta(z \mid x)$$ 가 검색기(DPR), $$p_\theta(y_i \mid x, z, y_{1:i-1})$$ 가 생성기(BART)다.

실무 설계자가 여기서 가져가야 할 것은 수식 자체가 아니라 **$$z$$ 가 명시적이라는 사실**이다. 논문이 성능 수치와 나란히 강조한 결론이 그 점이다 — 파라미터에 지식을 욱여넣은 모델과 달리, RAG는 (1) 답의 **출처를 제시**할 수 있고, (2) 세상이 바뀌면 **인덱스를 교체(hot-swap)하는 것만으로 지식을 갱신**할 수 있다. 재학습이 필요 없다.[^lewis]

그러니까 RAG를 도입하는 설계 근거는 "LLM이 더 똑똑해진다"가 아니다. **감사 가능성(auditability)과 갱신 가능성(updatability)** 이다. 이 둘이 필요 없는 도메인이라면 RAG는 과설계다. 반대로 이 둘이 필요한데 출처를 화면에 못 띄우고 있다면, 그 시스템은 RAG의 값을 치르면서 값어치를 안 받고 있는 것이다.

---

## 2. 파이프라인을 실패 지점으로 분해하기

전형적인 RAG는 네 단계다. 각 단계는 **독립적으로, 조용히** 실패한다.

| 단계        | 하는 일                     | 조용한 실패 방식                                |
| ----------- | --------------------------- | ----------------------------------------------- |
| ① 청킹/색인 | 문서를 자르고 임베딩        | 청크가 문맥을 잃어 검색 자체가 불가능해짐       |
| ② 검색      | 질의로 top-k 회수           | 정답 청크가 top-k에 없음 (recall 실패)          |
| ③ 배치      | 회수 결과를 프롬프트에 넣음 | 정답이 들어갔는데 모델이 못 씀 (위치·길이 문제) |
| ④ 생성      | 답 생성                     | 근거 없는 문장을 생성 (faithfulness 실패)       |

이걸 확률로 보면 설계 우선순위가 바로 나온다. 종단 정답률은 단계별 성공률의 **곱**이다.

$$
P_{\text{answer}} \;\le\; P_{\text{index}} \cdot P_{\text{retrieve}} \cdot P_{\text{attend}} \cdot P_{\text{ground}}
$$

각 항은 차례로 ① 정답이 청크로 색인돼 있을 확률, ② 그 청크가 top-k에 회수될 확률, ③ 회수된 것을 모델이 실제로 참조할 확률, ④ 참조한 근거대로 서술할 확률이다. 각 단계가 95%씩이어도 $$0.95^4 \approx 0.81$$ 이다. **한 단계만 90%로 내려가도 종단은 77%가 된다.** 그리고 현장에서 사람들이 튜닝하는 건 대개 ④(프롬프트)인데, 실제로 무너져 있는 건 ①·②인 경우가 많다. 측정을 단계별로 쪼개지 않으면 어디를 고쳐야 하는지 원리적으로 알 수 없다.

### ①의 실패: 청크는 자기가 어디서 왔는지 모른다

문서를 400~800토큰으로 자르면, 각 청크는 원문의 맥락을 잃는다. "매출은 전 분기 대비 3% 증가했다"는 청크에는 **어느 회사, 어느 분기**인지가 없다. 임베딩은 그 없는 정보를 만들어내지 못하므로, "ACME의 2023년 2분기 매출"이라는 질의는 이 청크를 못 찾는다. 인덱스에 정답이 들어 있는데도 그렇다.

Anthropic은 이 문제에 대해 **Contextual Retrieval** — 청크를 임베딩하기 전에 그 청크가 원문 어디에 위치하는지를 설명하는 짧은 문맥을 앞에 붙이는 방법 — 을 공개했다.[^ctx] 자사 벤치마크(코드베이스 9종, 248개 질의, 'golden chunk' 기준 Pass@k) 기준 수치는 다음과 같다. **벤더 자체 측정이며 중립 제3자 재현은 확인되지 않는다.**

- Contextual Embeddings 단독: top-20 검색 실패율 5.7% → 3.7% (35% 감소)
- \+ Contextual BM25(하이브리드): 5.7% → 2.9% (49% 감소)
- \+ 리랭킹: 5.7% → 1.9% (67% 감소)

설계자 입장에서 중요한 건 비율보다 **비용 구조**다. 문맥 생성은 질의마다가 아니라 **색인 시 1회** 발생한다. HyDE처럼 매 검색에 지연을 얹는 기법과 성질이 다르다. 같은 문서의 청크를 연달아 처리하면 프롬프트 캐싱이 먹는다. Anthropic이 제시한 예시 비용은 8k토큰 문서를 800토큰 청크로 자르고 청크당 100토큰의 문맥을 생성할 때 **문서 100만 토큰당 $1.02**다.[^cookbook] 함정도 같은 문서에 적혀 있다 — 임베딩 모델의 입력 토큰 한계가 고정된 경우, 문맥을 덧붙인 청크가 잘려나가 오히려 성능이 떨어질 수 있다.

### ②의 실패: dense-only는 고유명사에서 진다

의미 검색은 "환불 절차"와 "반품 프로세스"를 이어주지만, `ERR_TIMEOUT_4471` 같은 정확 일치 토큰에서는 키워드 검색(BM25)이 이긴다. Anthropic의 실험에서 하이브리드가 단독 대비 추가 이득을 낸 것도 이 결이다.[^ctx] 사내 문서·에러코드·법조문·상품코드가 섞인 한국어 코퍼스라면 dense-only로 출발하는 것 자체가 설계 결함에 가깝다.

### ③의 실패: 넣었다고 쓰는 게 아니다

이 단계가 가장 과소평가된다. Liu 등의 TACL 2024 논문 "Lost in the Middle"은 통제 실험으로 다음을 보였다.[^lost]

- 관련 정보가 **입력의 처음이나 끝**에 있을 때 성능이 가장 높고, **중간**에 있을 때 크게 떨어지는 U자 곡선이 나타난다(primacy/recency bias).
- 극단적으로, 정답 문서를 중간에 놓았을 때 GPT-3.5-Turbo의 다중문서 QA 성능은 **문서를 아예 안 준 closed-book 설정(56.1%)보다도 낮았다.**
- "긴 컨텍스트 모델"이라고 해서 이 문제에서 자유롭지 않았다. 확장 컨텍스트 버전이 원본과 사실상 동일한 성능을 보이는 경우가 많았다.
- open-domain QA 케이스 스터디에서, **리더의 성능은 리트리버의 recall보다 훨씬 먼저 포화**했다. 회수 문서를 20개에서 50개로 늘렸을 때 개선은 GPT-3.5-Turbo 약 1.5%, claude-1.3 약 1%에 그쳤다.

설계 함의는 분명하다. **top-k를 키우는 것은 값싼 개선처럼 보이지만 값싼 개선이 아니다.** 토큰 비용과 지연은 $$k$$ 에 선형으로 늘어나는데 정확도는 빠르게 포화한다. 그리고 넣은 만큼 모델이 걸러내야 할 노이즈가 늘어난다. $$k$$ 를 늘리는 대신 **리랭킹으로 상위를 정제하고, 정제된 것을 앞뒤에 배치**하는 쪽이 같은 토큰 예산에서 더 낫다.

"컨텍스트 윈도우가 커지면 RAG는 필요 없어진다"는 주장을 이 논문은 직접 반박하지는 않지만, 근거를 약화시킨다. 위 결과는 **넣을 수 있는 양**과 **쓸 수 있는 양**이 다르다는 것을 보여준다.

### ④의 실패: 매끄러운 문장은 근거의 증거가 아니다

여기서 필요한 건 프롬프트 튜닝이 아니라 **구조적 강제**다. Claude API의 `search_result` 콘텐츠 블록은 회수 결과를 `source`/`title`/`content`로 넘기면 모델 응답의 각 텍스트 블록에 어떤 결과의 어느 범위를 근거로 삼았는지를 `cited_text`와 인덱스로 되돌려준다.[^searchresult] 프롬프트로 "출처를 밝혀라"라고 부탁하는 것과 다른 점이 두 가지 있다.

1. 인용은 **제공한 문서 안의 유효한 포인터임이 보장**된다. 모델이 출처를 지어낼 수 없다.
2. `cited_text`는 **출력 토큰으로 과금되지 않는다.** 프롬프트로 원문을 그대로 다시 쓰게 하던 방식 대비 비용이 준다.[^citations]

인용 품질이 프롬프트 기반보다 낫다는 것은 Anthropic 자체 평가 주장이며, 문서에 정량 수치가 제시되어 있지 않다 — 그대로 인용 가능한 근거는 아니다.[^citations]

설계상 반드시 알아야 할 제약도 있다. **인용 기능과 structured outputs는 동시에 못 쓴다**(400 에러). 인용은 텍스트 블록 사이에 인용 블록을 끼워 넣는 방식이라 엄격한 JSON 스키마와 충돌하기 때문이다.[^citations] "응답을 JSON으로 받으면서 인용도 받는다"를 전제로 API 설계를 해뒀다면 그 시점에 갈아엎어야 한다. 회수 결과의 인용 단위는 `content` 배열의 텍스트 블록이므로, **청크를 어떻게 블록으로 쪼개느냐가 곧 인용의 정밀도**가 된다.[^searchresult] 이건 색인 설계(①)와 UI 설계가 같은 결정에 묶여 있다는 뜻이다.

---

## 3. 측정 설계가 먼저다

위 네 단계를 따로 고칠 수 있으려면 따로 측정해야 한다. 순서는 반대가 아니다 — **평가셋 없이 하는 튜닝은 튜닝이 아니라 도박이다.**

### 검색 단계: Pass@k / recall@k

정답 청크(golden chunk)를 붙인 질의 집합을 만들고, 상위 $$k$$ 안에 그것이 들어왔는지만 본다.[^cookbook] 이 지표는 LLM을 태우지 않으므로 싸고 빠르고 결정적이다. **①·②의 개선은 전부 여기서 판정된다.** 200~300개 규모면 시작할 수 있다.

### 생성 단계: 참조 없는 3축 (RAGAS)

Es 등의 RAGAS는 정답 라벨 없이(reference-free) RAG를 3축으로 평가하는 프레임워크다(EACL 2024 시스템 데모).[^ragas]

- **Faithfulness**: 답변의 주장이 주어진 컨텍스트에서 추론 가능한가. 답변을 statement 집합 $$S$$ 로 분해하고, 컨텍스트가 뒷받침하는 것 $$V$$ 의 비율로 계산한다.

$$
F = \frac{|V|}{|S|}
$$

- **Answer Relevance**: 답변에서 역으로 질문 $$n$$ 개를 생성해 원 질문과의 유사도를 본다. 사실성은 보지 않고, 불완전하거나 군더더기가 있는 답을 벌한다.
- **Context Relevance**: 회수된 컨텍스트 중 답에 실제로 필요한 문장의 비율. 낮으면 노이즈를 잔뜩 넣고 있다는 뜻이다.

이 3축 분리가 실무에서 갖는 값은, **어느 팀이 무엇을 고쳐야 하는지가 지표에서 바로 나온다**는 것이다. Faithfulness는 낮은데 Context Relevance가 높으면 생성 쪽 문제고, 반대면 검색 쪽 문제다.

한계도 저자들이 명시했다. WikiEval에서 사람 평가자 간 일치율은 faithfulness·context relevance 약 95%, answer relevance 약 90%였고, **context relevance가 가장 평가하기 어려운 축**이었다 — 특히 컨텍스트가 길어지면 판정 모델이 "핵심 문장 고르기"에 자주 실패했다.[^ragas] 즉 이 지표는 회귀 감시용으로는 훌륭하지만, 절대값을 SLA로 박기에는 근거가 약하다.

---

## 4. 고도화 로드맵 — 싼 것부터

투입 대비 효과 순서로 정리하면 이렇게 된다. 위에서부터 하지 않고 아래를 먼저 하면 개선인지 아닌지 판정할 방법이 없다.

**0단계 — 평가셋 (선행 조건)**
질의 200~300개 + golden chunk. 여기 없이 아래 어떤 것도 "개선했다"고 말할 수 없다.

**1단계 — 하이브리드 검색**
BM25 + dense. 고유명사·코드·수치가 많은 한국어 코퍼스에서 특히 효과가 크다. 인프라 추가가 가장 적은 축이다.

**2단계 — 문맥 부여 청킹 (Contextual Embeddings)**
색인 시 1회 비용. 캐싱을 쓰면 문서 100만 토큰당 $1.02 수준.[^cookbook] 다만 임베딩 모델의 입력 한계로 잘리지 않는지 반드시 확인해야 한다.

**3단계 — 리랭킹**
질의마다 비용과 지연이 붙는다. Anthropic 벤치마크에서 마지막 구간(49%→67% 실패 감소)을 담당한 것이 이 단계다.[^ctx] 앞 단계를 안 하고 이것부터 붙이면 비싼 값을 치르고 적게 얻는다.

**4단계 — Just-in-time / 에이전틱 검색**
여기서 아키텍처가 바뀐다. Anthropic은 사전 색인 기반 회수에서 **런타임에 필요할 때 끌어오는** 방식으로의 이동을 정리했다.[^ctxeng] 데이터를 미리 전부 전처리해 넣는 대신, 파일 경로·저장된 질의·링크 같은 **가벼운 식별자**만 들고 있다가 도구로 그때그때 로드한다. Claude Code가 `CLAUDE.md`는 앞에 미리 넣고 `glob`/`grep`은 필요할 때 쓰는 하이브리드 방식을 택한 이유로 **"오래된 색인(stale indexing) 문제를 우회한다"**는 점을 든다.

이 지점이 설계상 진짜 분기다. 문서가 자주 바뀌는 도메인에서 벡터 인덱스는 **항상 과거를 가리킨다.** 재색인 지연이 곧 오답 유효기간이 된다. 반대로 코퍼스가 안정적이고 지연 요구가 빡세면 사전 색인이 맞다. 둘 중 하나를 고르는 게 아니라, **어느 데이터를 어느 쪽에 둘지를 나누는 것**이 설계다.

**5단계 — 장기 태스크의 컨텍스트 관리**
한 번의 질의응답을 넘어가면 다른 문제가 시작된다. Anthropic이 정리한 세 가지 축은 compaction(대화를 요약해 새 창으로 이어감), structured note-taking(창 밖 영속 메모), sub-agent(각자 깨끗한 창에서 탐색하고 **1,000~2,000토큰 수준의 압축된 요약만 반환**)이다.[^ctxeng] 관통하는 원칙은 하나다 — **"원하는 결과를 낼 가능성을 최대화하는 최소한의 고신호 토큰 집합을 찾는 것."**

---

## 5. 운영 설계에서 빠지기 쉬운 것들

**인덱스 갱신은 배포다.** 임베딩 모델을 바꾸면 전체 재색인이다. 벡터 차원이 바뀌면 스키마 마이그레이션이다. 무중단으로 하려면 새 인덱스를 병렬로 만들고 트래픽을 옮기는, 사실상 blue-green 배포 설계가 필요하다. "임베딩 모델 업그레이드"를 라이브러리 버전 올리듯 잡아두면 그날 서비스가 선다.

**실패를 성공으로 기록하지 않기.** 회수 결과가 비었을 때 파이프라인이 그냥 빈 컨텍스트로 생성 단계에 넘어가면, 모델은 파라미터 기억으로 답한다. 출처 없는 답이 출처 있는 답과 같은 UI로 나간다. 회수 0건은 **명시적 분기**여야 한다.

**모르는 것을 안다고 말하지 않기.** 나는 최근 실계좌에 붙은 자동매매 코드에서 같은 종류의 버그를 고쳤다. 브로커가 HTTP 200 본문으로 "거부"를 알려주는데 응답을 안 읽어서, 거부된 주문이 체결로 장부에 기록되고 있었다. RAG의 hallucination은 성질이 정확히 같다 — **실패 경로가 성공 경로와 같은 모양으로 출력되는 것**. 고치는 방법도 같다. 성공·실패·불명을 코드에서 다른 타입으로 갈라놓는 것.

**비용은 $$k$$ 에 선형, 정확도는 아니다.** 2장 ③에서 본 대로 리더 성능은 리트리버 recall보다 먼저 포화한다.[^lost] top-k를 20에서 50으로 늘리는 결정은 정확도 결정이 아니라 예산 결정이다.

---

## 6. 한계와 면책

- Contextual Retrieval의 수치(35%/49%/67%)는 **Anthropic 자사 데이터셋(코드베이스 9종·248질의)에서 자사가 측정한 값**이다.[^ctx] 중립 제3자의 재현 결과는 확인하지 못했다. 같은 방법이 한국어 사내 문서에서 같은 폭의 이득을 낸다는 근거는 없다. 자기 코퍼스에서 재측정해야 한다.
- Anthropic 블로그의 실패율 기준 수치와 쿡북의 Pass@k 기준 수치는 **측정 기준이 달라 직접 비교하면 안 된다.**[^ctx][^cookbook] 이 글에서는 섞지 않았다.
- "Lost in the Middle"의 실험 대상 모델은 GPT-3.5-Turbo, claude-1.3, MPT-30B-Instruct, LongChat-13B 등 2023년 시점 모델이다.[^lost] 이후 세대에서 U자 곡선이 얼마나 완화됐는지에 대한 **동일 프로토콜의 최신 공개 측정치는 이 글에서 확인하지 못했다.** 경향의 방향은 설계 원칙으로 삼되, 완화 정도는 자기 모델에서 직접 재봐야 한다.
- RAGAS 지표는 저자들 스스로 context relevance의 판정 신뢰도가 낮다고 보고했다.[^ragas] 회귀 감시용으로 쓰되 절대 임계값을 계약에 박지 말 것.

---

## 정리

1. RAG를 쓰는 이유는 정확도가 아니라 **출처 제시와 지식 갱신**이다. 그걸 안 쓰면 값만 치른다.
2. 종단 정답률은 단계별 성공률의 **곱**이다. 단계를 나눠 측정하지 않으면 어디가 깨졌는지 알 수 없다.
3. **평가셋이 0단계다.** 하이브리드 → 문맥 청킹 → 리랭킹 → 에이전틱 순서로 붙이면 각 단계의 값어치를 판정할 수 있다.
4. 컨텍스트에 **넣을 수 있는 양과 쓸 수 있는 양은 다르다.** top-k 증설은 값싼 개선이 아니다.
5. 인용은 프롬프트로 부탁할 것이 아니라 **API 수준에서 강제**할 것. 단, 구조화 출력과는 함께 못 쓴다.
6. 회수 실패는 **명시적 분기**여야 한다. 실패 경로가 성공 경로와 같은 모양으로 나가면 안 된다.

---

## References

[^lewis]: Patrick Lewis, Ethan Perez, Aleksandra Piktus, Fabio Petroni, Vladimir Karpukhin, Naman Goyal, Heinrich Küttler, Mike Lewis, Wen-tau Yih, Tim Rocktäschel, Sebastian Riedel, Douwe Kiela. "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks." NeurIPS 2020. [arXiv:2005.11401](https://arxiv.org/abs/2005.11401) / [NeurIPS proceedings PDF](https://proceedings.neurips.cc/paper/2020/file/6b493230205f780e1bc26945df7481e5-Paper.pdf)

[^lost]: Nelson F. Liu, Kevin Lin, John Hewitt, Ashwin Paranjape, Michele Bevilacqua, Fabio Petroni, Percy Liang. "Lost in the Middle: How Language Models Use Long Contexts." _Transactions of the Association for Computational Linguistics_, Vol. 12, pp. 157–173, 2024. DOI: 10.1162/tacl_a_00638. [ACL Anthology](https://aclanthology.org/2024.tacl-1.9/) / [arXiv:2307.03172](https://arxiv.org/abs/2307.03172)

[^ragas]: Shahul Es, Jithin James, Luis Espinosa Anke, Steven Schockaert. "RAGAs: Automated Evaluation of Retrieval Augmented Generation." EACL 2024 System Demonstrations, pp. 150–158. [ACL Anthology](https://aclanthology.org/2024.eacl-demo.16/) / [arXiv:2309.15217](https://arxiv.org/abs/2309.15217)

[^ctx]: Anthropic. "Introducing Contextual Retrieval." Anthropic Engineering, 2024-09-19. <https://www.anthropic.com/engineering/contextual-retrieval> — _벤더 1차 자료이자 벤더 자체 벤치마크._

[^cookbook]: Anthropic. "Enhancing RAG with contextual retrieval." Claude Cookbook. <https://platform.claude.com/cookbook/capabilities-contextual-embeddings-guide> — _벤더 공식 문서. 데이터셋(코드베이스 9종·248질의)·비용 예시의 출처._

[^ctxeng]: Anthropic. "Effective context engineering for AI agents." Anthropic Engineering. <https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents>

[^searchresult]: Anthropic. "Search results." Claude Platform Docs. <https://platform.claude.com/docs/en/build-with-claude/search-results>

[^citations]: Anthropic. "Citations." Claude Platform Docs. <https://platform.claude.com/docs/en/build-with-claude/citations>
