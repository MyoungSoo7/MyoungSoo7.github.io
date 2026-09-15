---
layout: post
title: "AWS·GCP·네이버클라우드에서 Redis 가 기여할 수 있는 자리"
date: 2026-09-15 23:20:00 +0900
categories: [backend, infra]
tags: [Redis, Valkey, AWS, GCP, 네이버클라우드, ElastiCache, Memorystore, 캐시]
---

"Redis 를 쓰면 뭐가 좋아지는가" 는 클라우드가 정하지 않는다 — 워크로드가 정한다. 그러나 **어떤 관리형으로, 어떤 엔진 이름으로, 어떤 운영 모델로 쓰게 되는가**는 클라우드마다 꽤 다르고, 2024년 라이선스 사변 이후로는 더 달라졌다. 이 글은 ① Redis 가 기여하는 자리 자체를 먼저 고정하고, ② 세 클라우드(AWS·GCP·네이버클라우드)의 관리형 지형을 공식 문서 기준으로 얹은 뒤, ③ 선택 기준을 정리한다.

## 1. Redis 가 기여하는 자리 — 클라우드 불문 다섯 곳

Redis 는 인메모리 자료구조 저장소다. 문자열만이 아니라 해시·리스트·셋·정렬 셋(sorted set)·스트림 같은 자료구조를 서버 쪽에서 원자적으로 다룬다는 것이 관계형 DB 나 단순 캐시와의 본질적 차이다[^redis-types]. 그래서 기여 지점도 자료구조를 따라간다:

1. **읽기 캐시 (cache-aside).** RDB 앞단에서 반복 조회를 흡수해 DB 부하와 지연을 동시에 줄인다. 가장 흔하고, 투자 대비 효과가 가장 확실한 자리.
2. **세션 스토어.** 앱 서버를 스케일아웃할 때 세션을 서버 밖으로 꺼내는 표준 해법. sticky session 을 제거해 배포·장애 대응이 단순해진다.
3. **순위표·집계.** sorted set 은 "점수로 정렬된 상위 N" 을 O(log N) 으로 준다 — RDB 로 하면 매번 ORDER BY 풀스캔이 되는 작업이다.
4. **레이트리밋·분산 락.** 원자적 INCR/EXPIRE, SET NX 가 재료다. 다중 인스턴스 환경에서 "전역으로 하나만" 을 보장하는 가장 싼 도구.
5. **pub/sub·경량 큐.** 실시간 알림, 프로세스 간 신호 전달. (내구성이 필요한 이벤트 버스는 Kafka 류의 자리이고, Redis 스트림은 그 중간이다.)

이 다섯이 "기여할 수 있는 부분" 의 본체다. 아래 클라우드별 이야기는 **같은 다섯 자리를 어떤 관리형 그릇에 담느냐**의 문제다.

## 2. 전제 지식 — 2024 라이선스 사변과 Valkey

2024년 3월 Redis Inc. 가 Redis 를 오픈소스 라이선스에서 소스 가용(RSALv2/SSPLv1) 이중 라이선스로 전환하자, 커뮤니티는 즉시 Linux Foundation 산하에 BSD-3 라이선스의 포크 **Valkey** 를 세웠다[^valkey]. AWS·Google 등이 창립 멤버로 참여했고, 이후 세 클라우드의 관리형 서비스는 모두 Valkey 를 전면에 배치했다. 한편 Redis 쪽도 2025년 5월 Redis 8 부터 AGPLv3 를 라이선스 선택지로 되돌렸다[^redis-agpl].

실무자에게 중요한 건 하나다: **Valkey 는 Redis OSS 7.2 호환 드롭인**이라 기존 클라이언트(Jedis, redis-py, Lettuce 등)가 그대로 붙는다[^gcp-valkey-blog]. 즉 아래에서 "Valkey" 가 보여도 앱 코드 관점에선 같은 Redis 프로토콜 이야기다.

## 3. AWS — ElastiCache 와 MemoryDB, 캐시와 주 DB 의 분업

AWS 는 자리를 둘로 나눠 놨다.

- **ElastiCache** — 캐시·세션·순위표 등 위 다섯 자리의 기본 그릇. 2024년 10월부터 Valkey 엔진을 지원하며, AWS 공지 기준 Valkey 엔진은 서버리스가 다른 엔진 대비 33%, 노드 기반이 20% 저렴하고, Redis OSS 엔진에서 무중단 업그레이드로 넘어갈 수 있다[^aws-ec-valkey]. 서버리스 옵션은 용량 산정 없이 시작할 수 있어 "일단 캐시부터" 단계에 맞다.
- **MemoryDB** — 같은 Redis 프로토콜이지만 **다중 AZ 에 트랜잭션 로그로 내구성을 확보한 인메모리 주 데이터베이스**다. 캐시가 아니라 마이크로초 읽기가 필요한 원본 저장소(세션의 단일 원본, 게임 상태, 스트리밍 메타데이터)가 기여 지점이고, 역시 Valkey 엔진(30% 저가)과 벡터 검색을 지원한다[^aws-mdb-valkey].

요약하면 AWS 에서 Redis 의 기여는 "RDS/DynamoDB 앞의 캐시(ElastiCache)" 와 "잃으면 안 되는 인메모리 원본(MemoryDB)" 으로 갈라 설계하는 데 있다.

## 4. GCP — Memorystore 포트폴리오, 엔진 선택제

GCP 는 **Memorystore** 하나의 상품군 아래 Valkey·Redis Cluster·Redis·Memcached 네 엔진을 두고 고르게 한다[^gcp-memorystore]. 2025년 4월 Valkey 가 GA 되면서 99.99% SLA, 무중단 스케일(최대 250노드), Private Service Connect, 영속화(RDB/AOF), 리전 간 복제까지 갖췄다[^gcp-valkey-ga]. Google 은 라이선스 변경 직후 Valkey 창립에 참여한 쪽이라, 포트폴리오의 무게중심도 Valkey 로 옮겨 가 있다 — 기존 Memorystore for Redis 사용자에겐 마이그레이션 경로와 약정 할인(CUD) 승계를 안내한다[^gcp-valkey-ga].

GCP 에서의 기여 지점은 AWS 와 같은 다섯 자리이되, 그릇 선택이 "서비스를 고르는" 문제가 아니라 "엔진을 고르는" 문제라는 점이 다르다. 단순 조회 캐시면 Memcached 도 후보가 되고, 자료구조·영속성이 필요한 순간부터 Valkey/Redis 쪽이 된다.

## 5. 네이버클라우드 — Cloud DB for Cache, 국내 리전과 관리형의 결합

네이버클라우드의 관리형은 **Cloud DB for Cache** 다 — 2025년 6월 19일 기존 'Cloud DB for Redis' 에서 개명했고, API v2 부터 Redis 와 Valkey 를 함께 지원한다[^ncp-api]. 제품 페이지 기준 2026년 1월 22일 Valkey 7.2.11 이 출시됐고, 복제 기반 읽기 분산·자동 Fail-over·클러스터 구성을 제공하며, "네이버 서비스에서 검증된 최적화 설정" 을 기본값으로 내세운다[^ncp-product]. 백업(일 1회 자동 + 수동)과 백업으로부터의 신규 서버 생성, FlushAll 같은 위험 명령의 API 대체 제공도 문서화돼 있다[^ncp-api].

NCP 에서 Redis 의 기여 지점은 기술적으로는 동일한 다섯 자리지만, 선택 이유가 다른 축에서 나온다 — **국내 리전·국내 지원 조직·공공 클라우드(CSAP) 요건**이 걸린 시스템에서 하이퍼스케일러를 못 쓰거나 안 쓰는 경우의 관리형 Redis 라는 자리다. 반대로 서버리스형 과금이나 벡터 검색 같은 확장 기능은 하이퍼스케일러 대비 얇으므로, 그런 요건이 핵심이라면 기여 폭이 좁아진다.

## 6. 정리 — 한 장 비교와 선택 기준

| | AWS | GCP | 네이버클라우드 |
| --- | --- | --- | --- |
| 관리형 상품 | ElastiCache / MemoryDB | Memorystore (엔진 4종) | Cloud DB for Cache |
| Valkey | 두 서비스 모두 지원, 엔진별 저가 책정 (AWS 공지 기준) | GA, 99.99% SLA | 지원 (7.2.11, 2026-01) |
| 내구성 있는 주 DB 용도 | MemoryDB (다중 AZ 로그) | 영속화 옵션 (RDB/AOF) | 백업·복원 중심 |
| 서버리스 | ElastiCache Serverless | 없음 (노드 기반) | 없음 (서버 스펙 선택) |
| 특기 사항 | 벡터 검색 (MemoryDB) | 엔진 선택제, PSC | 국내 리전·공공 대응 |

선택 기준은 세 줄로 줄일 수 있다. **첫째, 기여 지점은 클라우드가 아니라 워크로드가 정한다** — 캐시·세션·순위표·락·pub/sub 중 무엇이 필요한지가 먼저다. 둘째, 같은 Redis 프로토콜이라 앱 코드는 세 클라우드 모두에서 사실상 이식적이다 — 락인은 코드가 아니라 운영 모델(서버리스 과금, SLA, 네트워크 연결 방식)에서 생긴다. 셋째, 2026년 현재 관리형의 무게중심은 세 곳 모두 Valkey 로 이동했다 — 신규 도입이라면 Valkey 엔진으로 시작하는 것이 라이선스·가격 양면에서 무난한 기본값이다.

---

## 근거의 한계

- "33%/20%/30% 저렴" 은 AWS 자체 공지의 자사 엔진 간 비교이고, "99.99% SLA" 등도 각 벤더의 자기 서비스 서술이다 — 중립 제3자의 성능·가격 헤드투헤드는 확인하지 못했다.
- 세 클라우드 관리형 Redis 의 점유율·사용 통계는 신뢰할 만한 중립 출처를 찾지 못해 인용하지 않았다.
- 네이버클라우드 사용 가이드(guide.ncloud-docs.com)는 자동화 접근이 차단(403)돼 본문을 실측하지 못했고, 그 문서에만 있는 세부(접속 범위 제한 등)는 이 글에서 뺐다. NCP 관련 서술은 실측 가능한 제품 페이지와 API 문서만 근거로 했다.

## References

[^redis-types]: Redis 공식 문서 — [Data types](https://redis.io/docs/latest/develop/data-types/)
[^valkey]: Valkey 공식 사이트 — [valkey.io](https://valkey.io/) (Linux Foundation 산하, BSD-3)
[^redis-agpl]: Redis 공식 블로그 — [Redis is open source again (AGPLv3)](https://redis.io/blog/agplv3/)
[^aws-ec-valkey]: AWS 공식 공지 — [Announcing Amazon ElastiCache for Valkey](https://aws.amazon.com/about-aws/whats-new/2024/10/amazon-elasticache-valkey/) 및 [AWS Database Blog — ElastiCache/MemoryDB Valkey 지원](https://aws.amazon.com/blogs/database/amazon-elasticache-and-amazon-memorydb-announce-support-for-valkey/)
[^aws-mdb-valkey]: AWS 공식 공지 — [Announcing Amazon MemoryDB for Valkey](https://aws.amazon.com/about-aws/whats-new/2024/10/amazon-memorydb-valkey/)
[^gcp-memorystore]: Google Cloud 공식 — [Memorystore 제품 페이지](https://cloud.google.com/memorystore)
[^gcp-valkey-ga]: Google Cloud 공식 블로그 — [Memorystore for Valkey GA](https://cloud.google.com/blog/products/databases/announcing-general-availability-of-memorystore-for-valkey)
[^gcp-valkey-blog]: Google Cloud 공식 블로그 — [Announcing Memorystore for Valkey](https://cloud.google.com/blog/products/databases/announcing-memorystore-for-valkey) (Redis 7.2 호환·클라이언트 호환)
[^ncp-product]: 네이버클라우드 공식 — [Cloud DB for Cache 제품 페이지](https://www.ncloud.com/product/database/cloudDbCache)
[^ncp-api]: 네이버클라우드 공식 API 문서 — [Cloud DB for Cache (VPC) API](https://api.ncloud-docs.com/docs/en/database-vcache) (2025-06-19 개명 고지, API v2 의 Redis·Valkey 지원)
