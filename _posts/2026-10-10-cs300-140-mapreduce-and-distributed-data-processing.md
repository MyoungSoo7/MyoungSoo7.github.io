---
layout: post
title: "[CS300 #140] MapReduce 와 분산 데이터 처리 — 계산을 데이터 쪽으로 보낸다"
date: 2026-10-10 20:20:00 +0900
categories: [cs]
tags: [cs300, distributed-systems, mapreduce, spark, hadoop, batch-processing]
---

컴퓨터공학 300 주제 시리즈의 140번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

MapReduce 는 대용량 데이터 처리를 map(각 레코드를 키-값으로 변환)과 reduce(같은 키끼리 모아 합치기) 두 함수로 표현하게 하고, 분할·스케줄링·셔플·장애 복구는 프레임워크가 맡는 프로그래밍 모델이다. 사용자는 순수 함수 두 개만 짜고, 수천 대 기계에서의 병렬 실행과 재시도는 시스템이 처리한다.

## 왜 필요한가

Part 7 의 첫 글은 `cat log | grep | sort | uniq -c` 였다. 한 기계에서 파이프로 이은 작은 프로그램들이 단계별로 데이터를 흘려보냈다. 데이터가 수십 TB 가 되면 이 한 줄이 한 기계에서 끝나지 않는다.

여러 기계로 나누려면 지금까지 본 문제가 한꺼번에 몰려온다. 데이터를 어떻게 나눌지(샤딩), 일을 어떻게 나눠 줄지(작업 큐), 기계가 죽으면 어떻게 할지(장애 감지, 재시도), 같은 일을 두 번 하면 괜찮은지(멱등성). 이걸 분석 작업마다 매번 새로 짤 수는 없다.

구글의 제프리 딘(Jeffrey Dean)과 산제이 게마왓(Sanjay Ghemawat)은 2004년 OSDI 논문에서, 많은 대규모 계산이 "레코드마다 무언가를 뽑고, 같은 키끼리 모아 합친다" 는 같은 모양이라는 점에 주목했다. 이 모양을 프레임워크로 고정하면 분산의 어려움을 프레임워크 한 곳에 몰아넣을 수 있다. 하둡(Hadoop)이 이 설계를 오픈소스로 구현해 빅데이터 시대를 열었다.

## 핵심 개념

### 두 함수

```
map    (k1, v1)        → list(k2, v2)
reduce (k2, list(v2))  → list(v2)
```

단어 세기라면 map 은 문서를 받아 `(단어, 1)` 을 내놓고, reduce 는 `(단어, [1,1,1,...])` 을 받아 합을 낸다. 함수는 부작용이 없어야 한다. 그래야 같은 입력으로 몇 번을 다시 실행해도 같은 결과가 나와 재실행이 안전하다(멱등성).

### 실행 흐름

```
 입력 분할          Map 태스크           셔플(파티션·정렬)        Reduce 태스크        출력
[split 0] ──►  map ─┬─ part 0 ─────┐
[split 1] ──►  map ─┼─ part 1 ───┐ ├──────────────►  reduce 0  ──► out-0
[split 2] ──►  map ─┴─ part 2 ─┐ │ └──────────────►  reduce 1  ──► out-1
                               └─┴────────────────►  reduce 2  ──► out-2
```

1. **분할**: 입력을 큰 조각(split)으로 나눈다. 분산 파일 시스템의 블록 단위가 보통이다.
2. **Map**: 마스터가 워커에 맵 태스크를 배정한다. 결과는 R 개 파티션으로 나눠 **워커의 로컬 디스크**에 쓴다. 파티션은 기본적으로 `hash(key) mod R` 이다(앞 글의 해시 파티셔닝).
3. **셔플**: 리듀서는 모든 맵 워커에서 자기 파티션 조각을 가져와 키로 정렬·그룹화한다. 네트워크를 가장 많이 쓰는 단계다.
4. **Reduce**: 키별로 reduce 함수를 실행해 결과를 분산 파일 시스템에 쓴다.

### 장애 처리: 다시 하면 된다

- **워커 장애**: 마스터가 주기적으로 워커에 ping 한다. 응답이 없으면 그 워커의 태스크를 다른 워커에 다시 배정한다. 완료된 맵 태스크도 다시 한다. 결과가 죽은 기계의 로컬 디스크에 있었기 때문이다. 완료된 리듀스 태스크는 결과가 분산 파일 시스템에 있으므로 다시 하지 않는다.
- **결정론과 원자적 커밋**: 출력은 임시 파일에 쓰고 완료 시 이름을 바꿔(rename) 원자적으로 확정한다. 같은 태스크가 두 번 실행되어도 최종 출력은 하나다.
- **낙오자(straggler)**: 디스크가 나쁜 기계 하나가 전체 작업을 늦춘다. 작업 막바지에 아직 도는 태스크의 **백업 사본**을 다른 기계에서 함께 돌리고, 먼저 끝난 쪽을 쓴다. 논문은 이 기법으로 큰 작업의 완료 시간이 크게 줄었다고 보고한다.

장애를 "막는" 대신 "다시 하면 되게" 만든 설계다. 순수 함수와 원자적 출력 덕분에 가능하다.

### 데이터 지역성

네트워크가 가장 귀한 자원이다. 마스터는 맵 태스크를 그 입력 블록의 복제본이 있는 기계(또는 같은 랙)에 우선 배정한다. **데이터를 계산으로 가져오지 말고, 계산을 데이터로 보낸다.** 이 원칙은 지금의 분산 처리 시스템에도 그대로 남아 있다.

### 컴바이너

단어 세기에서 맵이 `("the", 1)` 을 수만 번 내보내면 셔플이 무거워진다. 맵 쪽에서 미리 지역 합산(`("the", 3021)`)을 하면 네트워크 전송이 크게 준다. 이것이 컴바이너다. reduce 함수가 결합·교환 법칙을 만족할 때(합, 최댓값) 쓸 수 있다.

### MapReduce 이후

MapReduce 는 단계마다 결과를 디스크에 쓴다. 여러 단계를 잇는 작업이나, 같은 데이터를 반복해서 읽는 머신러닝·그래프 알고리즘에는 느렸다.

- **Spark**: 중간 결과를 메모리에 둘 수 있는 RDD(Resilient Distributed Datasets, NSDI 2012)를 도입했다. 장애 시에는 데이터를 복제해 두는 대신 **계보(lineage)**, 즉 그 데이터를 만든 변환 기록으로 잃어버린 파티션만 다시 계산한다. MapReduce 의 "다시 하면 된다" 를 일반화한 것이다.
- **SQL 엔진**: Hive, Spark SQL, Presto/Trino 처럼 SQL 을 분산 실행 계획으로 바꾸는 시스템이 주류가 되었다. 내부에는 여전히 map·셔플·reduce 와 같은 단계가 있다.
- **스트림 처리**: Flink, Kafka Streams 는 끝이 없는 데이터에 같은 아이디어(키로 파티션, 상태, 체크포인트로 장애 복구)를 적용한다.

## 직접 해 보기

맵 태스크 4개, 리듀서 3개짜리 단어 세기를 프로세스 풀로 돌린다. map, 컴바이너, 해시 파티션, 셔플, reduce 를 각각 함수로 드러냈다.

```python
import re, zlib
from collections import defaultdict
from multiprocessing import Pool

DOCS = [
    "the quick brown fox jumps over the lazy dog",
    "the dog barks and the fox runs",
    "a lazy afternoon for a lazy dog",
    "quick thinking saves the day",
] * 1000                                           # 입력 분할(split) 4000개
R = 3                                              # 리듀서 수

def map_fn(doc):                                   # map: (k1,v1) -> list(k2,v2)
    return [(w, 1) for w in re.findall(r"[a-z]+", doc)]

def combine(pairs):                                # 맵 쪽 지역 합산(combiner)
    acc = defaultdict(int)
    for k, v in pairs: acc[k] += v
    return list(acc.items())

def partition(key):                                # 같은 키는 항상 같은 리듀서로
    return zlib.crc32(key.encode()) % R

def map_task(chunk):
    out = [[] for _ in range(R)]
    for doc in chunk:
        for k, v in combine(map_fn(doc)):
            out[partition(k)].append((k, v))
    return out

def reduce_task(pairs):                            # reduce: (k2, list(v2)) -> v
    groups = defaultdict(list)
    for k, v in pairs: groups[k].append(v)         # 셔플 후 키별로 모으기(정렬·그룹)
    return {k: sum(vs) for k, vs in sorted(groups.items())}

if __name__ == "__main__":
    chunks = [DOCS[i::4] for i in range(4)]        # 맵 태스크 4개
    with Pool(4) as pool:
        map_out = pool.map(map_task, chunks)
        shuffled = [sum((m[r] for m in map_out), []) for r in range(R)]   # 셔플
        results = pool.map(reduce_task, shuffled)
    for r, res in enumerate(results):
        print(f"reducer{r}: {dict(list(res.items())[:4])} ...")
    total = {k: v for res in results for k, v in res.items()}
    print("상위 3:", sorted(total.items(), key=lambda kv: -kv[1])[:3])
```

```
reducer0: {'a': 2000, 'and': 1000, 'brown': 1000, 'jumps': 1000} ...
reducer1: {'barks': 1000, 'day': 1000, 'dog': 3000, 'for': 1000} ...
reducer2: {'afternoon': 1000, 'fox': 2000, 'saves': 1000} ...
상위 3: [('the', 5000), ('lazy', 3000), ('dog', 3000)]
```

같은 단어는 언제나 같은 리듀서로 간다. `partition` 이 결정론적이기 때문이다. 각 리듀서는 서로를 몰라도 자기 몫의 키에 대해 완전한 답을 낸다. `map_task` 하나를 일부러 두 번 실행해도 결과는 같다. 함수에 부작용이 없기 때문이다. 이 성질이 기계 수천 대에서의 재실행을 안전하게 만든다. 파이썬 내장 `hash()` 대신 `zlib.crc32` 를 쓴 이유도 있다. 문자열의 `hash()` 는 프로세스마다 무작위 시드가 달라서 워커마다 다른 파티션을 고를 수 있다.

## 현업에서는

- **Spark 작업 튜닝.** 실무 Spark 작업이 느린 원인은 대개 셔플이다. 불필요한 `groupByKey` 대신 맵 쪽 합산을 하는 `reduceByKey` 를 쓰고, 한 키에 데이터가 몰리는 데이터 쏠림(skew)을 키 분산으로 푼다. MapReduce 논문의 컴바이너와 파티션 문제가 이름만 바뀐 것이다.
- **쿠버네티스 위의 배치.** 인덱스가 붙은 쿠버네티스 Job 은 "입력 조각 i 를 처리하는 태스크 i" 를 표현할 수 있어, 작은 규모의 map 단계를 클러스터에서 돌리기 좋다. Spark 도 쿠버네티스를 스케줄러로 쓸 수 있다. 작은 홈랩 클러스터에서도 로그 집계 같은 일을 여러 노드에 나눠 돌려 볼 수 있다. 다만 노드가 적고 네트워크가 느리면 셔플 비용 때문에 한 기계 처리보다 느릴 수도 있다.
- **한 기계로 충분한가부터.** 수십 GB 정도는 좋은 한 대의 기계와 DuckDB·pandas·`sort | uniq` 로 더 빨리 끝나는 경우가 많다. 분산은 데이터가 한 기계를 넘을 때 쓰는 도구다. Part 7 의 결론과 같다. 한 대에서 여러 대로 넘어가면 문제의 종류가 바뀌므로, 넘어갈 이유가 있을 때만 넘어간다.

## 확인 문제

1. map 과 reduce 함수가 부작용이 없어야 하는 이유는?
2. 워커가 죽었을 때 완료된 맵 태스크는 다시 실행하고 완료된 리듀스 태스크는 다시 하지 않는 이유는?
3. 컴바이너를 쓸 수 있는 조건과 효과는?
4. 낙오자 문제를 MapReduce 는 어떻게 완화하는가?
5. Spark 의 RDD 가 장애 시 데이터를 복구하는 방식은?

### 풀이

1. 장애나 낙오자 때문에 같은 태스크가 여러 번 실행될 수 있으므로, 몇 번 실행해도 같은 결과(멱등성)가 나와야 재실행이 안전하다.
2. 맵 출력은 그 워커의 로컬 디스크에 있어 함께 사라지지만, 리듀스 출력은 복제된 분산 파일 시스템에 있어 남아 있기 때문이다.
3. reduce 연산이 결합·교환 법칙을 만족할 때 쓸 수 있고, 맵 쪽에서 미리 합쳐 셔플 데이터량을 줄인다.
4. 작업 막바지에 아직 실행 중인 태스크의 백업 사본을 다른 기계에서 돌리고 먼저 끝난 결과를 쓴다.
5. 데이터를 만든 변환 기록(계보, lineage)을 따라 잃어버린 파티션만 다시 계산한다.

## 더 읽을거리 (References)

- [Jeffrey Dean, Sanjay Ghemawat, "MapReduce: Simplified Data Processing on Large Clusters", OSDI 2004 (PDF)](https://static.googleusercontent.com/media/research.google.com/en//archive/mapreduce-osdi04.pdf)
- [Apache Hadoop — MapReduce Tutorial](https://hadoop.apache.org/docs/stable/hadoop-mapreduce-client/hadoop-mapreduce-client-core/MapReduceTutorial.html)
- [Zaharia et al., "Resilient Distributed Datasets", NSDI 2012 (USENIX)](https://www.usenix.org/conference/nsdi12/technical-sessions/presentation/zaharia)
- [Apache Spark — RDD Programming Guide](https://spark.apache.org/docs/latest/rdd-programming-guide.html)
