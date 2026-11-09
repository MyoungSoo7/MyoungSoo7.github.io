---
layout: post
title: "KiviDB 해부 — 모든 코어에서 도는 Rust 판 Redis, 벤치마크 너머에서 확인할 것들"
date: 2026-11-10 02:44:08 +0900
categories: [database]
tags: [kividb, redis, valkey, dragonfly, rust, in-memory, io_uring, vector-search]
---

[kividbio/kividb](https://github.com/kividbio/kividb)는 공개한 지 한 달도 안 돼 GitHub 스타 1,019개, 포크 105개를 모았다(2026-11-10 `gh api` 기준). 소개 문구는 *"Redis®·Valkey 를 대체하는 빠른 멀티스레드 DB, Rust 로 작성, 그대로 끼워 쓸 수 있고 전문·벡터 검색 내장"*이다. README 첫머리에는 "32코어에서 파이프라인 GET 초당 2,100만 건, Redis 8 의 약 9배, Dragonfly 의 2.3배"라는 숫자가 크게 붙어 있다.

이 글은 그 숫자를 되풀이하지 않는다. 대신 **소스와 문서에서 무엇을 확인할 수 있고, 무엇은 아직 벤더 주장일 뿐인지**를 가른다.

> **검증 범위.** 리포를 HEAD `bda2ccf3`(2026-11-09, PR #540 머지)로 클론해 README·`docs/`·`benchmarks/1.2.0/REPORT.md`·`src/store/mod.rs` 를 직접 읽었다. **빌드·실행·벤치마크는 하지 않았다.** 아래 성능 수치는 전부 KiviDB 측이 측정해 공개한 것이고, 2026-11-10 현재 중립 제3자가 재현한 헤드투헤드 벤치마크는 찾지 못했다.

## 1. 무엇인가 — 한 장 요약

| 항목 | 내용 | 출처 |
|---|---|---|
| 언어·빌드 | Rust 2024 에디션, 최소 1.89 | README |
| 프로토콜 | RESP2, RESP3. `redis-cli` 와 기존 클라이언트가 그대로 붙음 | README, COMPATIBILITY |
| 기본 포트 | **6380** (Redis 의 6379 와 나란히 띄우려는 의도) | README |
| 내장 기능 | JSON, `FT.*`(전문·태그·숫자·벡터 FLAT/HNSW), `TS.*`, 벡터 셋. 모듈 로드 없이 바이너리에 포함 | COMPATIBILITY |
| 빌드 변형 | default / `lua` / `tls` / `full`. **기본 빌드엔 Lua 가 없다** | README |
| I/O | 리눅스는 io_uring, 막히면 Tokio 로 폴백 (`--io-model auto`) | README |
| 라이선스 | AGPL-3.0-only + CLA + 별도 상용 라이선스 | README |
| 저작권자 | KIVIDB PRIVATE LIMITED | README |
| 릴리스 | v1.1.0(10-16) → v1.1.1·v1.1.2(10-23) → v1.1.3(10-31) → v1.2.0(11-03) | GitHub Releases |

마지막 두 줄이 이 프로젝트를 읽는 맥락이다. **한 회사가 저작권을 쥔 AGPL + CLA 듀얼 라이선스**이고, 공개 후 3주 사이에 마이너 릴리스가 다섯 번 나왔다.

## 2. "모든 코어에서 돈다"의 실제 모양

README 의 비교표는 Dragonfly 를 *shared-nothing*, KiviDB 를 *sharded* 로 적는다. 소스를 보면 이 차이가 구체적으로 보인다.

`src/store/mod.rs` 의 핵심 타입은 다음과 같다.

```rust
pub struct ShardLock {
    map: RwLock<ShardMap>,
    ...
}
pub type Shard = Arc<ShardLock>;
pub type Db = Arc<Vec<Shard>>;
```

키는 64비트 FNV-1a 해시의 하위 비트로 샤드에 배정된다. 샤드 수는 *코어당 8개를 2의 거듭제곱으로 올림*한 값이다(주석 기준: 8코어 → 64, 16코어 → 128, 64코어 → 512). 즉 **모든 워커 스레드가 키스페이스 전체를 보고, 샤드마다 붙은 `RwLock` 으로 충돌을 피하는 공유-메모리(shared-everything) 설계**다.

Dragonfly 는 반대로 샤드를 스레드 하나가 소유하고, 다른 스레드의 키가 필요하면 메시지를 넘긴다. 이 대비는 Show HN 스레드에서 직접 논쟁이 됐다. Dragonfly 의 멀티스레드 구조를 2022년에 평가했다고 밝힌 사용자 `romange` 는 이렇게 썼다([HN 댓글](https://news.ycombinator.com/item?id=50155630)).

> KeyDB, Garnet, and KiviDB share the same foundation: employing fine-grained locks. … With lock-based approaches, features like MULTI/EXEC, Lua scripts, and multi-key operations introduce severe contention that becomes hard to manage.

단일 키 GET/SET 처럼 락이 거의 겹치지 않는 부하에서는 이 설계가 유리하다. 그런데 **여러 키를 원자적으로 다뤄야 하는 순간** 비용이 어디로 가는지가 다음 절의 주제다.

## 3. MULTI/EXEC 는 어떻게 원자적인가 — 서버 전역 게이트

[`docs/EXEC_ATOMICITY.md`](https://github.com/kividbio/kividb/blob/master/docs/EXEC_ATOMICITY.md)는 이 문제를 숨기지 않고 설명한다.

- 모든 명령은 실행되는 동안 `src/command_gate.rs` 의 게이트를 **공유 모드**로 잡는다.
- `EXEC`, 함수(`FCALL`), 임의 키를 건드릴 수 있는 스크립트는 게이트를 **배타 모드**로 잡는다. 실행 중인 명령이 다 끝나길 기다리고, 끝날 때까지 새 명령을 막는다. 문서 표현으로는 *"Redis 가 스레드 하나로 주는 보장"*을 이렇게 재현한다.
- 예외: `lua-parallel-scripts yes`(기본값)이면 `KEYS` 가 전부 같은 해시 태그 하나에 속하고 빠르다고 확인된 스크립트는 공유 게이트 + 태그 락으로 돈다. BullMQ 처럼 큐 하나에 태그를 묶는 패턴을 겨냥한 장치다.

정리하면 **트랜잭션·임의 스크립트가 많은 부하에서는 그 순간 서버 전체가 직렬화된다.** 멀티스레드의 이점은 그 구간에서 사라진다. 이건 결함이 아니라 설계상 선택이지만, "Redis 보다 9배"라는 숫자가 이런 부하에도 적용된다고 읽으면 안 된다.

이 문서에서 더 눈여겨볼 건 *"The defect this replaced"* 절이다. **1.0.5 이전에는 트랜잭션 명령이 다른 클라이언트 명령과 섞여 실행될 수 있었다.** 이체 테스트에서 감사(auditor) 연결이 `[(0, 900)]`, 즉 한쪽 계좌에서 빠졌지만 다른 쪽에 아직 안 들어간 돈을 관측했다. `WATCH` 에도 같은 틈이 있어 재고 5개에 구매자 10명 테스트가 열두 번에 한 번꼴로 6개째를 팔았다. 지금은 고쳐졌고 테스트로 고정돼 있다. 다만 **락 기반 멀티스레드에서 원자성을 맞추는 게 얼마나 쉽게 어긋나는지**를 보여 주는 1차 기록이다. 위 HN 반론이 짚은 지점과 정확히 겹친다.

## 4. 벤치마크 — 숫자가 두 벌이다

README 를 처음 보면 헷갈리는 부분이다. 성능 수치가 **서로 다른 환경에서 잰 두 벌**로 나온다.

| | 1.1 베어메탈 (2026-10) | 1.2.0 클라우드 VM (2026-11-01~03) |
|---|---|---|
| 서버 | AWS `c7gn.metal`, 32코어로 제한 | Azure `Standard_D32ps_v5` (Ampere Altra 32 vCPU) |
| GET, 파이프라인 16 | KiviDB 21.2M / Dragonfly 9.1M / Redis 2.4M | KiviDB 10.45M / **Garnet 10.69M** / Redis 1.41M |
| SET, 파이프라인 16 | KiviDB 19.2M / Dragonfly 8.5M / Redis 2.0M | KiviDB 7.94M / **Garnet 9.83M** / Redis 1.25M |
| 파이프라인 없음 GET | **Dragonfly 3.35M** / KiviDB 3.07M | — |
| 키당 메모리 | **Dragonfly 134 B** / KiviDB 177 B / Redis 178 B | **KiviDB 140.7 B** / Dragonfly 141.5 B / Redis 174.4 B |

**벤더 주장, 재현 스크립트 공개.** 하네스는 [kivi-benchmark](https://github.com/kividbio/kivi-benchmark)에, 원자료와 표는 [`benchmarks/1.2.0/REPORT.md`](https://github.com/kividbio/kividb/blob/master/benchmarks/1.2.0/REPORT.md)에 있다. 직접 재현할 수 있는 구조지만 이 글에서는 재현하지 않았다.

이 두 벌에서 읽어 낼 것은 세 가지다.

1. **README 맨 위의 "2,100만·9배·2.3배"는 1.1 베어메탈 수치다.** 같은 README 아래쪽, 최신 1.2.0 클라우드 측정에서는 Garnet(마이크로소프트의 C# 구현)이 GET·SET·MSET 에서 앞선다. 헤드라인과 최신 측정이 서로 다른 경쟁자를 기준으로 하고 있다.
2. **이득은 파이프라인 16 에 집중돼 있다.** 파이프라인이 없으면 베어메탈에서도 Dragonfly 가 약간 빠르다. README 는 Azure 램프 테스트에서 비파이프라인 시 Dragonfly 대비 약 20% 낮았다고 스스로 적는다. 일반적인 웹 요청-응답 패턴은 파이프라인 깊이가 얕은 경우가 많다.
3. **조건이 좁다.** 벤치마크 페이지([kividb.io/benchmarks](https://kividb.io/benchmarks))는 베어메탈 결과에 대해 *"영속성은 모든 엔진에서 껐음, 값 크기 100바이트 하나, 32코어 머신 하나, 복제·TLS 없는 단일 노드"*라고 명시한다.

리포트가 **스스로 진 항목을 따로 절로 적어 둔 점**(*Where KiviDB loses*, *What is not covered*)은 평가할 만하다. Garnet 은 core 스위트에서만 돌았고, Valkey 는 벡터·캐시 테스트에서 빠졌으며, kvrocks 는 데이터 타입 스위트에서만 돌았다는 공백도 같이 적혀 있다.

## 5. 호환성 — "드롭인"의 단서 조항

[`docs/COMPATIBILITY.md`](https://github.com/kividbio/kividb/blob/master/docs/COMPATIBILITY.md)는 Redis 8.10 동작을 목표로 한다고 하고, 차이점을 꽤 길게 나열한다. 운영 관점에서 걸리는 것만 추리면 이렇다.

| 차이 | 왜 중요한가 |
|---|---|
| **Sentinel 미구현** | Sentinel 기반 HA 를 쓰는 곳은 구조를 바꿔야 한다 (클러스터 프로토콜은 구현돼 있음) |
| **기본 빌드에 Lua 없음** | BullMQ·Sidekiq·레이트리미터처럼 스크립트를 쓰는 앱은 `lua`/`full` 이미지를 골라야 한다 |
| `save <points>` 무시 | 주기 스냅샷이 없다. AOF 나 `BGSAVE` 로 대체 |
| 설정 파일 엄격 파싱 | 모르는 지시어가 하나라도 있으면 기동 실패. Redis 설정을 그대로 가져오면 걸린다 |
| **Redis·Valkey 로 되돌아가기 어려움** | KiviDB 의 `DUMP` 페이로드를 Redis 가 못 읽고, Redis 가 KiviDB 의 레플리카가 될 수 없다([#450](https://github.com/kividbio/kividb/issues/450)). 이탈하려면 키 단위 복사 |
| HyperLogLog 기본 포맷이 자체 형식 | 이전 후 `hll-write-format redis` 를 켜야 섞이고 되돌릴 수 있다 |
| `MODULE LOAD` 불가 | 서드파티 모듈은 못 쓴다 |
| `HELLO`·`INFO` 가 `redis_version: 8.10.0` 으로 응답 | 클라이언트 기능 협상용. 모니터링이 버전으로 엔진을 판별한다면 KiviDB 를 Redis 로 오인한다 |

"되돌아가기 어려움"은 들어가는 길보다 나오는 길이 좁다는 뜻이다. 도입 전에 이탈 경로까지 같이 리허설해 두는 게 맞다.

자체 측정한 호환성 지표도 있다. [`docs/REDIS_TEST_SUITE.md`](https://github.com/kividbio/kividb/blob/master/docs/REDIS_TEST_SUITE.md)에 따르면 Redis 8.0.0 의 공식 테스트 스위트를 단위별로 따로 돌렸을 때 **1,892 통과, 31 실패, 조기 종료 1**이었다. 이 문서도 흥미로운 고백으로 시작한다. 예전 CI 는 `--timeout 30` 을 *테스트 하나의 제한 시간*으로 착각했다. 그래서 HyperLogLog 퍼즈 테스트에서 러너가 통째로 멈췄고, 90개 파일 중 **11개 유닛만 돌린 결과(약 445건)를 호환성 수치로 보고**하고 있었다. 지금은 고쳐졌지만, 공개 초기의 숫자를 읽을 때 염두에 둘 이력이다.

## 6. 영속성 — fork 없는 체크포인트

Redis 의 `BGSAVE` 는 `fork()` 후 copy-on-write 로 스냅샷을 쓴다. 쓰기가 많으면 메모리가 크게 부푼다(1.2.0 리포트 측정에서 Redis +89%, 역시 벤더 측정). [`docs/PERSISTENCE.md`](https://github.com/kividbio/kividb/blob/master/docs/PERSISTENCE.md)가 설명하는 KiviDB 방식은 다르다.

- 체크포인트 순간에는 **쓰기를 잠깐 멈추고** 데이터셋을 캡처한 뒤 AOF 를 새로 시작한다. 문서 기준 *"키 약 900만 개에서 100 ms 미만"*.
- 실제 파일 쓰기는 그 뒤에 쓰기를 재개한 채 진행한다. 잘라 낸 순간에 쓰기가 멈춰 있었으므로 모든 쓰기는 스냅샷과 새 AOF 중 정확히 한쪽에만 들어간다.
- AOF 를 켜면 레코드가 파일에 들어간 뒤에 응답한다(1.2 부터). 단, 디스크가 5초 넘게 밀리면 응답이 먼저 나가고 `aof_acks_before_write` 카운터가 올라간다. Redis 는 쓰기가 끝날 때까지 기다린다는 점이 다르다.

트레이드오프는 분명하다. fork 메모리 스파이크를 피하는 대신 **키 수에 비례하는 쓰기 정지**를 받아들인다. FounderMag 기사도 HN 토론에서 *"키 수가 늘수록 스냅샷 동안 쓰기가 더 오래 멈춘다"*는 지적이 나왔다고 전한다([FounderMag](https://foundermag.co/launches/kividb/)). 수억 키 규모에서 이 정지가 얼마인지는 공개 자료에서 찾지 못했다.

## 7. 운영 시 놓치기 쉬운 것 두 가지

**기동 시 업데이트 확인.** 릴리스 빌드는 기동할 때 `https://github.com/kividbio/kividb/releases/latest` 로 HTTPS 요청을 한 번 보낸다. README 는 *"요청 자체 외엔 아무것도 보내지 않는다"*고 설명하고, 최대 1.5초를 기다린다. 폐쇄망이나 이그레스 감사가 있는 환경이라면 `--update-check no`, 설정 `update-check no`, 환경변수 `KIVIDB_NO_UPDATE_CHECK=1` 중 하나로 끈다.

**컨테이너에서는 io_uring 이 기본으로 꺼진다.** README 에 따르면 최근 Docker 의 기본 seccomp 프로필이 io_uring 을 막아 Tokio 로 폴백한다. 켜려면 `--security-opt seccomp=unconfined` 가 필요하다고 안내하는데, 이건 컨테이너 격리를 꽤 넓게 푸는 옵션이다. **벤치마크의 io_uring 수치와 쿠버네티스 위 실제 동작이 다를 수 있다**는 뜻이기도 하다. 또 Docker 이미지 기본 명령이 `--protected-mode no` 이고, 인자를 직접 넘기면 그 기본값이 사라져 보호 모드가 다시 켜진다는 함정도 README 에 적혀 있다.

## 8. 누가 만들고 있나

- 기여 통계상 커밋 946건이 `murtazayusuf` 한 계정에 몰려 있고, 2위가 33건이다(GitHub contributors API).
- Show HN 원글에서 작성자는 *"2026년 2월에 Rust 를 익히려고 시작했다"*, *"AI 를 많이 썼지만 설계 결정은 내가 했다"*고 밝혔다([HN](https://news.ycombinator.com/item?id=50152541)).
- 같은 회사가 KiviDB Cloud(AWS·GCP·Azure 매니지드)와 상용 라이선스를 판다. 비교 페이지([kividb.io/compare/redis](https://kividb.io/compare/redis))에는 매니지드 가격 비교가 있는데, 이건 마케팅 자료이므로 이 글에서는 인용하지 않는다.

이건 품질 판정이 아니라 **버스 팩터와 거버넌스에 대한 사실**이다. CLA 로 저작권이 회사에 모이는 구조이므로 라이선스 변경 리스크도 같이 본다. README 는 *"AGPLv3 로 낸 버전은 계속 AGPLv3 로 남는다"*고 약속한다. 이미 공개된 버전에 대해서는 원래 그렇다. 앞으로 나올 버전에 대한 약속은 아니다.

## 9. 그래서 어디에 쓸 만한가

중립 제3자 평가는 아직 얇다. [Console](https://console.dev/tools/kividb)(2026-10-22, David Mytton)의 짧은 리뷰는 장점으로 Redis 프로토콜·검색·Lua 지원과 멀티코어 실행을, 트레이드오프로 AGPL 을 꼽았다. 독립 성능 측정은 없다. FounderMag 은 *"캐시와 벡터 조회엔 유망하지만 아직 주 데이터 저장소는 아니다"*라고 정리했다.

내 판단도 크게 다르지 않다. 근거는 이 글에서 직접 읽은 문서들이다.

- **맞는 곳**: 단일 키 위주 + 파이프라인이 깊은 캐시, Redis Stack 의 `FT.*` 벡터 검색을 별도 모듈 없이 쓰고 싶은 RAG 캐시. 1.2.0 리포트의 필터링 벡터 검색 수치(100 클라이언트 4,478 q/s, Dragonfly 811)가 유일하게 큰 격차인 영역인데, 이것도 벤더 측정이다.
- **신중할 곳**: `MULTI/EXEC`·임의 키 스크립트가 많은 부하(전역 게이트로 직렬화), Sentinel 기반 HA, 되돌아갈 경로가 필요한 주 저장소, io_uring 을 못 쓰는 컨테이너 환경.
- **공통**: 위 벤치마크를 믿지 말고 **자기 워크로드로 잰다.** README 도 같은 말을 한다. *"Treat published figures as one controlled capture, not a guarantee."*

## References

**1차 — 프로젝트 소스·문서** (HEAD `bda2ccf3`, 2026-11-09)

- kividbio/kividb, README — <https://github.com/kividbio/kividb>
- `docs/COMPATIBILITY.md` — <https://github.com/kividbio/kividb/blob/master/docs/COMPATIBILITY.md>
- `docs/EXEC_ATOMICITY.md` — <https://github.com/kividbio/kividb/blob/master/docs/EXEC_ATOMICITY.md>
- `docs/PERSISTENCE.md` — <https://github.com/kividbio/kividb/blob/master/docs/PERSISTENCE.md>
- `docs/REDIS_TEST_SUITE.md` — <https://github.com/kividbio/kividb/blob/master/docs/REDIS_TEST_SUITE.md>
- `src/store/mod.rs` (`ShardLock`, `shard_index`, `num_shards`) — <https://github.com/kividbio/kividb/blob/master/src/store/mod.rs>
- Issue #450 (Redis·Valkey 가 KiviDB 의 DUMP 를 못 읽음) — <https://github.com/kividbio/kividb/issues/450>

**벤더 1차 벤치마크** (재현 스크립트 공개, 이 글에서는 재현하지 않음)

- `benchmarks/1.2.0/REPORT.md` — <https://github.com/kividbio/kividb/blob/master/benchmarks/1.2.0/REPORT.md>
- kividb.io/benchmarks — <https://kividb.io/benchmarks>
- kivi-benchmark 하네스 — <https://github.com/kividbio/kivi-benchmark>

**커뮤니티·제3자**

- Show HN: KiviDB (작성자 `murtazayusuf`, 2026-10-19) — <https://news.ycombinator.com/item?id=50152541>
- `romange` 의 아키텍처 반론 댓글 — <https://news.ycombinator.com/item?id=50155630>
- Console, *KiviDB: review and tradeoffs* (2026-10-22) — <https://console.dev/tools/kividb>
- FounderMag, *KiviDB Is a Multi-Threaded Redis and Valkey Drop-In…* (2026-10-19) — <https://foundermag.co/launches/kividb/>

중립 제3자의 성능 헤드투헤드는 2026-11-10 현재 **부재**하다.
