---
layout: post
title: "Opik 을 띄우면 Redis 와 ClickHouse 가 따라온다 — 세 도구의 사용법과 사용 사례"
date: 2026-10-03 17:09:38 +0900
categories: [AI, Database]
tags: [Opik, Redis, ClickHouse, LLM관측, 셀프호스팅, OLAP, 캐시]
---

LLM 관측 도구 **Opik** 을 셀프호스팅으로 띄우면 컨테이너가 열 개 가까이 올라온다. 그중 눈에 띄는 것이 **Redis** 와 **ClickHouse** 다. "LLM 호출 기록 하나 보자고 왜 DB 가 이렇게 많이 뜨지?" 라는 질문에서 이 글은 시작한다.

답을 먼저 말하면 이렇다. **Opik 은 데이터의 성격에 따라 저장소를 나눠 쓴다.** 그 분업을 이해하면 Redis 와 ClickHouse 가 각각 무엇을 잘하는지, 내 서비스에서는 언제 써야 하는지도 같이 보인다.

Opik 자체의 소개와 LiteLLM 연동은 이전 글([Opik LLM 관측](/2026/09/05/opik-llm-observability/), [LiteLLM 게이트웨이와 Opik](/2026/09/05/litellm-gateway-opik-observability/))에서 다뤘다. 이 글은 **세 도구의 역할 분담과 사용법**에 집중한다.

## 1. Opik — LLM 앱의 블랙박스 기록계

[Opik](https://github.com/comet-ml/opik) 은 Comet 이 만든 오픈소스(Apache-2.0) 도구다. README 는 스스로를 *"the open-source LLM observability and evaluation platform for AI agent tracing, LLM evaluation, prompt management, and production monitoring"* 이라고 소개한다.

### 사용법 — 셀프호스팅과 SDK

[로컬 배포 문서](https://www.comet.com/docs/opik/self-host/local_deployment) 기준으로는 세 줄이면 뜬다.

```bash
git clone https://github.com/comet-ml/opik.git
cd opik
./opik.sh          # → http://localhost:5173
```

같은 문서는 이 방식이 *"not meant for production deployments"* 라고 분명히 적는다. 운영 환경에는 Helm/Kubernetes 배포를 권한다.

애플리케이션 쪽은 파이썬 SDK 를 설치하고 로컬 서버를 바라보게 설정한 뒤, 추적할 함수에 데코레이터를 붙이면 된다.

```python
# pip install opik
import opik
from opik import track

opik.configure(use_local=True)   # 셀프호스팅 서버 사용

@track
def answer(question: str) -> str:
    ...   # LLM 호출, 검색, 후처리 — 이 함수의 입력·출력·시간이 trace 로 남는다
```

OpenAI, Anthropic, LangChain, LangGraph, LiteLLM 등 주요 라이브러리와의 연동이 README 에 정리돼 있다.

### 사용 사례

| 사례 | 하는 일 |
|---|---|
| **트레이싱** | 에이전트가 어떤 순서로 무슨 도구를 불렀는지, 각 단계의 입력·출력·지연·비용을 본다 |
| **평가(Evaluation)** | 데이터셋을 만들고 `evaluate()` 로 프롬프트·모델 변경 전후를 비교한다. [평가 문서](https://www.comet.com/docs/opik/evaluation/overview)에 따르면 *"30+ pre-built metrics for hallucination, relevance, coherence"* 가 있다 |
| **LLM-as-a-judge** | 환각(Hallucination) 같은 지표는 다른 LLM 이 채점한다. 점수는 0 또는 1 이다 |
| **운영 모니터링** | 실서비스 트레이스에 피드백 점수를 붙여 품질 추세를 본다 |

## 2. 왜 저장소가 여러 개인가 — Opik 의 데이터 분업

[Opik 아키텍처 문서](https://www.comet.com/docs/opik/self-host/architecture)는 각 저장소의 역할을 명확히 나눈다.

| 저장소 | 맡는 데이터 | 데이터의 성격 |
|---|---|---|
| **MySQL** | 프로젝트, 데이터셋, 프롬프트, 워크스페이스 (*"transactional data"*) | 적고, 자주 바뀌고, 정확해야 함 |
| **ClickHouse** | 트레이스, 스팬, 실험, 피드백 점수 (*"large-scale analytical data"*) | 엄청 많고, 한 번 쓰면 거의 안 바뀌고, 집계해서 봄 |
| **Redis** | 캐시, 속도 제한, 분산 락, 스트림(온라인 평가, 실험 집계, 작업 큐) | 빠르고, 일시적이고, 메모리에 있어야 함 |
| **MinIO** | 첨부파일, 아티팩트 (S3 호환) | 큰 바이너리 |
| **Zookeeper** | ClickHouse 클러스터 조율 | 메타 조율 |

이 표가 이 글의 핵심이다. **"LLM 호출 기록" 은 하나처럼 보이지만, 사실 성격이 다른 데이터 네 종류다.** 하나의 DB 에 다 넣으면 어느 하나는 반드시 손해를 본다. 그래서 Opik 은 데이터마다 맞는 엔진을 골랐다. 이제 그중 두 개를 따로 보자.

## 3. Redis — 메모리 위의 자료구조 서버

### 무엇인가

[Redis 문서](https://redis.io/docs/latest/get-started/)의 정의는 이렇다. *"an in-memory data store used by millions of developers as a cache, vector database, document database, streaming engine, and message broker."* [자료형 문서](https://redis.io/docs/latest/develop/data-types/)는 더 짧게 말한다. *"Redis is a data structure server."*

핵심은 **데이터가 메모리에 있고, 그 데이터가 단순한 값이 아니라 자료구조**라는 점이다. 문자열, 해시, 리스트, 셋, 정렬된 셋(Sorted Set), 스트림, JSON 등이 있다.

### 사용법 — 자료구조별 한 줄씩

```bash
SET session:abc '{"user":42}' EX 1800    # 30분 뒤 자동 삭제되는 세션 (EX = 초 단위 만료)
INCR rate:user:42                        # 원자적 카운터 — 요청 수 세기
EXPIRE rate:user:42 60                   # 60초 창(window)
ZADD leaderboard 980 "alice"             # 정렬된 셋 — 점수 순위
ZREVRANGE leaderboard 0 9 WITHSCORES     # 상위 10명
XADD jobs * type eval trace_id t-123     # 스트림 — 작업 큐에 이벤트 추가
```

`SET … EX` 의 만료는 [SET 명령 문서](https://redis.io/docs/latest/commands/set/)에 *"Set the specified expire time, in seconds"* 로 정의돼 있다.

### 사용 사례

| 사례 | 쓰는 자료구조 | Opik 에서는 |
|---|---|---|
| 캐시 | String + 만료 | 반복 조회 결과 캐싱 |
| 속도 제한 | `INCR` + 만료, 토큰 버킷 | 아키텍처 문서의 *"Token-bucket rate limiting"* |
| 분산 락 | `SET NX` + 만료 | 여러 백엔드 인스턴스가 같은 작업을 겹쳐 하지 않게 |
| 작업 큐·이벤트 | Streams, 리스트 | 온라인 평가, 실험 집계, 작업 큐 |
| 순위·랭킹 | Sorted Set | (일반 사례) 게임 순위, 인기 글 |

분산 락은 이 블로그의 [Redis 분산 락 글](/2026/05/04/redis-distributed-lock/)에서 따로 다뤘다.

**언제 쓰나:** 데이터가 **작고, 빨라야 하고, 잃어도 다시 만들 수 있을 때.** 원본 데이터의 유일한 저장소로 쓰는 건 피하는 게 기본이다.

## 4. ClickHouse — 대량 로그를 위한 열 지향 분석 DB

### 무엇인가

[ClickHouse 문서](https://clickhouse.com/docs/intro): *"a high-performance, column-oriented SQL database management system (DBMS) for online analytical processing (OLAP)."*

**열 지향(column-oriented)** 이 핵심이다. 일반 DB(MySQL 등)는 한 행을 통째로 저장한다. ClickHouse 는 **같은 열의 값들을 모아서** 저장한다. "지난 7일간 모델별 평균 지연시간" 같은 쿼리는 수억 행 중 `model`, `latency`, `time` 세 열만 읽으면 된다. 열 단위로 저장하면 필요한 열만 읽고, 같은 종류의 값끼리 모여 있어 압축도 잘 된다.

### 사용법 — MergeTree 테이블 하나

```sql
CREATE TABLE llm_spans
(
    ts          DateTime,
    project     String,
    model       String,
    latency_ms  UInt32,
    tokens      UInt32,
    cost_usd    Float64
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(ts)
ORDER BY (project, model, ts);

-- 프로젝트·모델별 일간 지연 p95 와 비용
SELECT project, model, toDate(ts) AS day,
       quantile(0.95)(latency_ms) AS p95_ms,
       sum(cost_usd)               AS cost
FROM llm_spans
WHERE ts >= now() - INTERVAL 7 DAY
GROUP BY project, model, day
ORDER BY day;
```

[MergeTree 문서](https://clickhouse.com/docs/engines/table-engines/mergetree-family/mergetree)에서 알아 둘 두 가지:

- **`ORDER BY` 가 성능을 좌우한다.** *"The table's primary key determines the sort order within each table part."* 정렬된 데이터 위에 **희소 인덱스(sparse index)** 를 만든다(8192행 단위 granule). 그래서 *"in most cases, such indexes fit in the computer's RAM."* 자주 거르는 열(위 예에서는 project, model)을 앞에 둔다.
- **파티션은 속도를 위한 게 아니다.** *"Partitioning does not speed up queries (in contrast to the ORDER BY expression)."* 파티션은 오래된 데이터를 월 단위로 지우는 것 같은 **관리** 용도다. 조회 속도는 `ORDER BY` 설계가 결정한다.

### 사용 사례

[ClickHouse 사용 사례 페이지](https://clickhouse.com/docs/use-cases)는 시계열, **관측(Observability)**, 데이터 레이크, 머신러닝·GenAI 를 든다. Opik 이 트레이스와 스팬을 ClickHouse 에 넣는 것이 정확히 관측 사례다.

| 사례 | 예 |
|---|---|
| 로그·트레이스 분석 | LLM 스팬, API 접근 로그, 에러 로그 |
| 실시간 대시보드 | 서비스 지표, 사용자 행동 집계 |
| 시계열 | 센서·메트릭 |
| 제품 분석 | 이벤트 퍼널, 리텐션 |

**언제 쓰나:** 데이터가 **많고, 추가만 되고(append-only), 행 단위 수정보다 집계 조회가 중요할 때.** 반대로 주문 상태처럼 한 행을 자주 고치는 트랜잭션 데이터에는 맞지 않는다. Opik 이 그런 데이터를 MySQL 에 두는 이유다.

## 5. 셀프호스팅할 때 꼭 챙길 것 — 문을 닫아 두기

이 세 도구를 직접 띄울 때 가장 흔한 실수는 **포트를 모든 네트워크에 열어 두는 것**이다. 도커로 띄우면 기본값이 그렇다.

- **Redis**: [보안 문서](https://redis.io/docs/latest/operate/oss_and_stack/management/security/)의 첫 문장이 이렇다. *"Redis is designed to be accessed by trusted clients inside trusted environments."* 외부에 노출되면 *"a single FLUSHALL command can be used by an external attacker to delete the whole data set."* 최소한 `bind 127.0.0.1`(또는 내부망)과 인증(`requirepass` 나 Redis 6+ 의 ACL)을 건다.
- **ClickHouse**: 기본 포트는 HTTP 8123, 네이티브 9000 이다([포트 문서](https://clickhouse.com/docs/guides/sre/network-ports)). 사용자 비밀번호를 설정하고, 외부에서 직접 붙을 일이 없으면 열지 않는다.
- **도커로 띄웠다면 방화벽만 믿으면 안 된다.** [Docker 문서](https://docs.docker.com/engine/network/packet-filtering-firewalls/)에 따르면 도커로 공개한 포트는 ufw 규칙보다 먼저 처리되어 *"effectively ignoring your firewall configuration."* 확실한 방법은 [포트를 공개할 때](https://docs.docker.com/engine/network/port-publishing/) `127.0.0.1:6379:6379` 처럼 **주소를 붙여 묶는 것**이다.

Opik 의 Redis·ClickHouse·MySQL 은 Opik 백엔드만 접근하면 된다. 그러니 외부로 열어 둘 이유가 없다. **화면(5173)만 필요한 곳에 열고, 저장소는 전부 안쪽에 둔다.**

## 정리

| | Opik | Redis | ClickHouse |
|---|---|---|---|
| 한 줄 | LLM 앱 관측·평가 | 메모리 자료구조 서버 | 열 지향 OLAP DB |
| 잘하는 것 | 트레이스, 평가, 프롬프트 관리 | 캐시, 속도 제한, 락, 큐 | 대량 로그·이벤트 집계 |
| 못하는 것 | — | 대용량 영구 원본 저장 | 잦은 행 단위 수정 |
| Opik 안에서 | 본체 | 캐시·락·스트림 | 트레이스·스팬·점수 |

Opik 의 구성은 그 자체로 좋은 설계 교과서다. **데이터를 성격대로 나누고, 성격에 맞는 엔진에 맡긴다.**

- 정확해야 하는 것은 MySQL 에
- 빨라야 하는 것은 Redis 에
- 많고 집계해야 하는 것은 ClickHouse 에

내 서비스에서도 같은 질문으로 저장소를 고르면 된다. *이 데이터는 많은가, 빨라야 하는가, 자주 바뀌는가?*

## References

- Opik — [GitHub (comet-ml/opik)](https://github.com/comet-ml/opik) · [Self-host architecture](https://www.comet.com/docs/opik/self-host/architecture) · [Local deployment](https://www.comet.com/docs/opik/self-host/local_deployment) · [Evaluation overview](https://www.comet.com/docs/opik/evaluation/overview)
- Redis — [Get started](https://redis.io/docs/latest/get-started/) · [Data types](https://redis.io/docs/latest/develop/data-types/) · [SET](https://redis.io/docs/latest/commands/set/) · [Security](https://redis.io/docs/latest/operate/oss_and_stack/management/security/)
- ClickHouse — [Introduction](https://clickhouse.com/docs/intro) · [MergeTree](https://clickhouse.com/docs/engines/table-engines/mergetree-family/mergetree) · [Use cases](https://clickhouse.com/docs/use-cases) · [Network ports](https://clickhouse.com/docs/guides/sre/network-ports)
- Docker — [Packet filtering and firewalls](https://docs.docker.com/engine/network/packet-filtering-firewalls/) · [Port publishing](https://docs.docker.com/engine/network/port-publishing/)
