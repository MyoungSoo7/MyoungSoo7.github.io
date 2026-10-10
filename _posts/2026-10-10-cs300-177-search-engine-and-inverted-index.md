---
layout: post
title: "[CS300 #177] 검색 엔진과 역색인 — 단어에서 문서로 거꾸로 가기"
date: 2026-10-10 20:57:00 +0900
categories: [cs]
tags: [cs300, database, inverted-index, full-text-search, bm25]
---

컴퓨터공학 300 주제 시리즈의 177번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

역색인은 "문서 → 단어"가 아니라 "단어 → 그 단어가 나오는 문서 목록"을 저장하는 자료구조이고, 검색 엔진은 이 목록들을 교차·합집합한 뒤 BM25 같은 점수 함수로 관련도 순으로 정렬해 돌려준다.

## 왜 필요한가

게시판 검색을 `WHERE body LIKE '%역색인%'` 으로 구현하면 두 가지 문제가 생긴다. 첫째, 앞이 와일드카드인 `LIKE` 는 B+트리 인덱스를 쓸 수 없어 모든 행을 읽는다. 둘째, 결과에 순서가 없다. "역색인"이 제목에 있는 글과 각주에 한 번 나오는 글이 똑같이 취급된다. 사용자는 "가장 관련 있는 것"을 위에서 보고 싶어 한다.

검색 엔진은 이 두 문제를 역색인과 점수 함수로 푼다. Elasticsearch, OpenSearch, Solr 는 모두 Apache Lucene 이라는 역색인 라이브러리 위에 서 있고, PostgreSQL 과 SQLite 도 전문 검색(full-text search) 기능을 내장하고 있다.

## 핵심 개념

### 정색인과 역색인

```
정색인 (문서 → 단어)                역색인 (단어 → 포스팅 목록)
 doc1: [postgresql, b-tree, gin]     "역색인" → [doc2, doc3]
 doc2: [검색, 엔진, 역색인, 문서]    "문서"   → [doc2(1회), doc3(2회)]
 doc3: [역색인, 단어, 문서, 문서]    "단어"   → [doc2, doc3]
```

책 뒤의 찾아보기가 바로 역색인이다. 단어 하나에 붙은 문서 목록을 **포스팅 목록(postings list)** 이라 하고, 각 항목을 포스팅이라 한다. 포스팅에는 문서 ID 뿐 아니라 단어 빈도(tf), 단어가 나온 위치(position)를 함께 저장하기도 한다. 위치가 있어야 `"inverted index"` 같은 구문 검색이나 근접 검색을 할 수 있다.

포스팅 목록은 문서 ID 순으로 정렬해 두므로, `A AND B` 는 두 정렬 목록의 교집합을 병합하듯 선형 시간에 구할 수 있다. 문서 ID 차이값을 가변 길이 정수로 압축하는 등 저장을 줄이는 기법이 많이 쓰인다.

### 분석기: 문자열을 단어로

색인과 검색 모두 같은 **분석기(analyzer)** 를 거친다. Elasticsearch 문서는 분석기를 세 단계로 설명한다.

1. **문자 필터**: HTML 태그 제거 같은 원문 전처리
2. **토크나이저**: 문자열을 토큰으로 자르기
3. **토큰 필터**: 소문자화, 불용어 제거, 어간 추출(running → run), 동의어 추가

분석이 검색 품질의 절반이다. 색인 때 `Running` 을 `run` 으로 저장했다면 검색어 `runs` 도 `run` 으로 바뀌어야 맞는다. 한국어는 조사가 단어에 붙기 때문에 공백 분리만으로는 "인덱스를", "인덱스와", "인덱스" 가 다 다른 단어가 된다. 그래서 형태소 분석기(예: Elasticsearch 의 nori 플러그인)가 필요하다.

### 점수: TF-IDF 에서 BM25 로

관련도 점수의 직관은 두 가지다.

- **TF(단어 빈도)**: 문서 안에 검색어가 많이 나올수록 관련 있다. 다만 10번과 20번의 차이는 1번과 2번만큼 크지 않다(포화).
- **IDF(역문서 빈도)**: 모든 문서에 나오는 흔한 단어("the", "이다")는 변별력이 없다. 드문 단어일수록 가중치가 크다.

여기에 **문서 길이 정규화**가 붙는다. 긴 문서는 우연히 단어를 많이 포함하므로 감점한다. 이를 정리한 것이 Robertson 등이 제안한 **BM25** 다.

```
score(D, Q) = Σ  IDF(q) · tf(q,D)·(k1+1) / ( tf(q,D) + k1·(1 − b + b·|D|/avgdl) )
             q∈Q
```

`k1` 은 TF 포화 속도, `b` 는 길이 정규화 강도다. 흔히 `k1` 은 1.2 근처, `b` 는 0.75 를 쓴다. Lucene 의 `BM25Similarity` 도 이 값을 기본으로 둔다.

### 색인 갱신: 세그먼트

역색인은 정렬·압축된 구조라 중간에 끼워 넣기가 비싸다. Lucene 은 새 문서를 작은 불변 **세그먼트**로 따로 만들고, 검색 시 모든 세그먼트를 함께 조회하며, 백그라운드에서 세그먼트를 병합한다. 삭제는 "삭제 표시"만 하고 병합 때 실제로 지운다. 그래서 Elasticsearch 에는 문서를 넣고 검색에 보이기까지 짧은 지연(refresh 주기)이 있다. 검색 엔진이 "준실시간(near real-time)"이라고 불리는 이유다.

### DB 내장 전문 검색

| 시스템 | 기능 |
|---|---|
| PostgreSQL | `tsvector`/`tsquery` 타입, `to_tsvector()` 로 분석, GIN 인덱스, `ts_rank` |
| SQLite | FTS5 가상 테이블, `MATCH` 질의, 내장 `bm25()` 순위 함수 |
| MySQL | `FULLTEXT` 인덱스, `MATCH ... AGAINST` |

데이터가 수백만 건 이하이고 한 DB 안에서 끝내고 싶다면 내장 기능으로 충분한 경우가 많다. 별도 검색 엔진은 복잡한 분석기, 패싯, 대규모 분산이 필요할 때 고려한다.

## 직접 해 보기

역색인과 BM25 를 직접 구현해 본다. 분석기는 일부러 단순하게 만들었다.

```python
import math, re
from collections import defaultdict, Counter

docs = {
    1: "PostgreSQL 은 B-tree 인덱스와 GIN 인덱스를 지원한다",
    2: "검색 엔진은 역색인으로 단어에서 문서를 찾는다",
    3: "역색인은 단어마다 문서 목록을 저장한다. 문서 목록을 포스팅이라 한다",
    4: "Redis 는 인메모리 키 값 저장소다",
}

def tokenize(text):                         # 분석기: 소문자화 + 단어 분리 + 조사 '은/는/으로' 정도만 떼기
    toks = re.findall(r"[0-9a-zA-Z가-힣-]+", text.lower())
    return [re.sub(r"(은|는|으로|을|를|이라|마다)$", "", t) for t in toks]

index = defaultdict(dict)                   # 단어 → {문서ID: 단어 빈도}
doc_len = {}
for doc_id, text in docs.items():
    toks = tokenize(text)
    doc_len[doc_id] = len(toks)
    for term, tf in Counter(toks).items():
        index[term][doc_id] = tf

print("포스팅 '역색인':", index["역색인"])
print("포스팅 '문서'  :", index["문서"])

N, avgdl = len(docs), sum(doc_len.values()) / len(docs)
def bm25(query, k1=1.2, b=0.75):
    scores = defaultdict(float)
    for term in tokenize(query):
        postings = index.get(term, {})
        df = len(postings)
        if not df:
            continue
        idf = math.log(1 + (N - df + 0.5) / (df + 0.5))
        for d, tf in postings.items():
            norm = tf * (k1 + 1) / (tf + k1 * (1 - b + b * doc_len[d] / avgdl))
            scores[d] += idf * norm
    return sorted(scores.items(), key=lambda x: -x[1])

for q in ["역색인 문서", "인덱스"]:
    print(q, "→", [(d, round(s, 3)) for d, s in bm25(q)])
```

결과:

```
포스팅 '역색인': {2: 1, 3: 1}
포스팅 '문서'  : {2: 1, 3: 2}
역색인 문서 → [(3, 1.503), (2, 1.472)]
인덱스 → [(1, 1.204)]
```

문서 3 은 "문서"가 두 번 나와 더 높은 점수를 받았지만, 더 길어서 길이 정규화로 감점을 받아 차이가 크지 않다. 더 흥미로운 것은 "인덱스" 결과다. 문서 1 에는 "인덱스"가 두 번 있지만 tf 는 1 이다. "인덱스와"의 "와"를 이 분석기가 떼지 못해 다른 단어가 되었기 때문이다. 한국어 검색에 형태소 분석기가 필요한 이유가 여기서 바로 보인다.

SQLite 의 FTS5 는 같은 일을 내장으로 해 준다. `bm25()` 는 값이 작을수록(더 음수일수록) 관련도가 높다.

```python
import sqlite3
con = sqlite3.connect(":memory:")
con.execute("CREATE VIRTUAL TABLE doc USING fts5(body)")
con.executemany("INSERT INTO doc(body) VALUES (?)", [(s,) for s in [
    "an inverted index maps each term to a list of documents",
    "a b-tree keeps keys sorted on disk pages",
    "search engines build an inverted index and the index stores postings",
    "redis is an in-memory key value store",
    "write-ahead logging makes recovery possible",
    "replication ships the log to a replica",
]])
for row in con.execute("""SELECT rowid, round(bm25(doc), 3), highlight(doc, 0, '[', ']')
                          FROM doc WHERE doc MATCH 'inverted index' ORDER BY bm25(doc)"""):
    print(row)
```

```
(3, -1.281, 'search engines build an [inverted] [index] and the [index] stores postings')
(1, -1.059, 'an [inverted] [index] maps each term to a list of documents')
```

## 현업에서는

- **원본은 DB, 검색은 사본**: 검색 엔진 색인은 DB 를 반정규화한 사본으로 다룬다. 변경 데이터 캡처나 이벤트로 색인을 갱신하고, 어긋나면 전체 재색인으로 복구할 수 있게 만든다. 매핑(스키마)을 바꿀 때도 새 색인을 만들어 채운 뒤 별칭(alias)을 바꿔 무중단으로 전환한다.
- **분석기 변경은 재색인**: 색인 시점의 분석 결과가 저장되어 있으므로, 분석기나 사전을 바꾸면 기존 문서를 다시 색인해야 효과가 난다.
- **검색 품질은 측정한다**: 검색어별 클릭률, 결과 없음 비율, 상위 결과 클릭 위치를 지표로 둔다. 동의어 사전 하나가 "결과 없음"을 크게 줄이기도 한다.
- **로그 검색**: Elasticsearch/OpenSearch 는 로그 수집 스택에서도 흔하다. 홈랩 k3s 클러스터에서 파드 로그를 모아 검색하는 경우에도 원리는 같다. 다만 로그는 쓰기량이 커서 색인 수명 주기(오래된 색인 삭제)를 꼭 설정해야 디스크가 버틴다.

## 확인 문제

1. `LIKE '%키워드%'` 가 B+트리 인덱스를 쓸 수 없는 이유는?
2. 포스팅에 위치 정보를 저장하면 어떤 검색이 가능해지는가?
3. IDF 가 흔한 단어의 점수를 낮추는 이유는?
4. BM25 에서 `b = 0` 이면 무엇이 달라지는가?
5. 위 예제에서 "인덱스" 검색의 tf 가 1 로 나온 이유와 해결 방법은?

### 풀이

1. B+트리는 값의 앞부분부터 정렬되어 있어 접두사가 정해져야 탐색할 수 있다. 앞이 `%` 면 시작점을 정할 수 없다.
2. 구문 검색(`"inverted index"` 처럼 단어가 연속으로 나오는지)과 근접 검색.
3. 거의 모든 문서에 나오는 단어는 문서를 구별하는 정보가 적기 때문이다. df 가 클수록 IDF 가 작아진다.
4. 문서 길이 정규화가 꺼진다. 긴 문서와 짧은 문서를 같은 기준으로 tf 만 보고 점수를 매긴다.
5. "인덱스와"의 조사 "와"가 분리되지 않아 다른 토큰이 되었다. 형태소 분석기를 쓰거나 조사 처리 규칙을 보강한다.

## 더 읽을거리 (References)

- Christopher D. Manning, Prabhakar Raghavan, Hinrich Schütze, *Introduction to Information Retrieval*, Cambridge University Press, 2008. [온라인판](https://nlp.stanford.edu/IR-book/), [역색인 절](https://nlp.stanford.edu/IR-book/html/htmledition/a-first-take-at-building-an-inverted-index-1.html)
- Apache Lucene, [BM25Similarity API 문서](https://lucene.apache.org/core/9_0_0/core/org/apache/lucene/search/similarities/BM25Similarity.html)
- Elasticsearch 공식 문서, [Text analysis](https://www.elastic.co/guide/en/elasticsearch/reference/current/analysis.html), [Korean (nori) analysis plugin](https://www.elastic.co/guide/en/elasticsearch/plugins/current/analysis-nori.html)
- PostgreSQL 공식 문서, [Full Text Search — Introduction](https://www.postgresql.org/docs/current/textsearch-intro.html); SQLite 공식 문서, [FTS5](https://www.sqlite.org/fts5.html)
