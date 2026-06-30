---
layout: post
title: "백엔드 개발자가 봐야 할 처리량과 응답시간 — 네트워크 · 디스크 · 메모리 · 디바이스 · CPU 다시 보기"
date: 2026-06-10 17:00:00 +0900
categories: [backend, performance, architecture]
tags: [throughput, latency, network, disk, memory, cpu, hardware, performance-engineering]
---

> *백엔드 시스템* 이 *느리다* 는 말을 자주 듣는다. *어디가 느린지* 는 *덜 자주* 보인다.
> 사용자가 보는 *3초의 지연* 은 *5 개의 다른 *층* 에서* 1 초씩 모인 것일 수 있다.
> 각 층의 *속도 수준* 을 *몸에 익혀* 두면 — *처음 보는 시스템도 *대략 어디가 병목인지* 짚을 수 있다.

---

## TL;DR

| 자원 | *전형적* 속도 | 백엔드의 *주된 영향* |
|------|---------------|----------------------|
| **L1 cache** | ~1 ns | CPU bound 의 *최내부* |
| **L2 / L3 cache** | ~10~50 ns | hot path 의 *분기 / 배열 접근* |
| **RAM** | ~100 ns | 데이터 구조 *접근 시간* |
| **NVMe SSD** | ~100 µs | DB 의 *random read* / log write |
| **SATA SSD** | ~500 µs | 위와 *5 배 느림* |
| **HDD random** | ~10 ms | *현대 백엔드에서 *피해야 할* 디스크* |
| **로컬 *동일 노드* 네트워크** | ~50 µs | *Pod-to-Pod* on same node |
| **LAN (1Gbps)** | ~0.5 ms + 전송시간 | *동일 데이터센터* 호출 |
| **인터넷 (10ms~)** | 10~300 ms | *클라이언트 ↔ 서버* / *원격 API* |

이 표 1 장을 *몸에 익히면* — *대부분의 *처음 보는 시스템* 의 *병목 후보* 가 *직감* 된다.

---

## 1. *처리량 (Throughput)* 과 *응답시간 (Latency)* — 둘은 다른 지표

이 둘을 *혼동하면* 잘못된 최적화로 간다. 정의 :

- **처리량** : *단위 시간당 처리 가능한 *요청 수*. *시스템 *전체* 의 능력.
- **응답시간** : *한 요청* 이 *시작에서 끝까지* 걸리는 시간. *개별 *경험*.

비유 — *고속도로* :

- *처리량* = *시간당 통과 차량 수* (TPS / RPS).
- *응답시간* = *한 차가 도착할 때까지의 시간*.

이 둘은 *서로 다른 방향* 으로 최적화된다 :

| 목표 | 처리량 ↑ | 응답시간 ↓ |
|------|----------|------------|
| 배칭 | *좋음* (한 번에 많이) | *나쁨* (대기 발생) |
| 캐싱 | *좋음* | *좋음* |
| 동시성 ↑ | *좋음 (TPS↑)* | 컨텍스트 스위치로 *나쁨 가능* |
| 큐 도입 | *좋음 (스무딩)* | *나쁨 (큐 대기시간)* |

> *처리량과 응답시간은 *동시에 최적화 안 되는 경우* 가 있다*. 어느 게 *우선인지* 가 *비즈니스 결정*.

---

## 2. 네트워크 속도 — *Latency + Bandwidth* 의 곱

흔히 "100Mbps 인데 왜 느려?" 묻는다. 답 : *Bandwidth (대역폭) 와 Latency (지연시간) 가 다르다*.

- **Bandwidth** : *시간당 옮길 수 있는 *바이트 수*. (1 Gbps, 100 Mbps)
- **Latency** : *첫 바이트 가 *상대 도착하는 데* 걸리는 시간*. (ping 시간 = RTT)

작은 응답 (~ 1KB) — *대부분 Latency 가 지배*. 큰 응답 (10MB) — *Bandwidth 가 지배*.

### 전형적 RTT (왕복) 수치 :

```
같은 host 의 두 process → 0.05ms
같은 노드 의 두 pod      → 0.1ms
같은 LAN 노드 사이      → 0.5~1ms
같은 데이터센터         → 0.5~2ms
같은 도시 의 다른 DC    → 5~10ms
서울 ↔ 일본 도쿄         → 30ms
서울 ↔ 미국 동부         → 200ms
모바일 4G                → 50~80ms
모바일 5G                → 20~40ms
```

### 백엔드의 흔한 함정

1. ***내부 호출이 *과도하게 많은 경우*** — MSA 에서 *한 요청* 이 *서비스 5 개 직렬 호출* 이면 *5 × 1ms = 5ms* 만으로 끝. 단 *그게 *10 개* 면 *10ms* 가 *상수*. *최소 latency floor* 가 *서비스 분리 수* 에 비례.
2. ***DB 호출이 직렬 N+1*** — *연관 조회 매 row 마다 *DB 1 회 round-trip*. *10 row 면 *10ms*, *100 row 면 *100ms*. *Join 또는 batch fetch* 로 해결.
3. ***외부 API 동기 호출*** — *3rd party API 가 *50ms* 라면 *그 50ms 가 *그대로* 사용자에게 더해진다*. *비동기 / 캐싱 / fallback* 검토.

---

## 3. 디스크 속도 — *SSD vs HDD vs NVMe* + *Random vs Sequential*

디스크 성능의 *두 차원* :

1. **매체 종류** : HDD / SATA SSD / NVMe SSD
2. **접근 패턴** : 순차 (sequential) / 랜덤 (random)

### 전형적 수치 (random 4KB IOPS) :

```
HDD                   → 100~200 IOPS    (응답 5~10ms)
SATA SSD              → 50,000~90,000 IOPS  (응답 100~500µs)
NVMe SSD (consumer)   → 100,000~500,000 IOPS  (응답 50~100µs)
NVMe SSD (enterprise) → 1,000,000+ IOPS       (응답 10~50µs)
```

### Random 과 Sequential 의 차이

- 같은 SSD 라도 *sequential* 은 *random 보다 5~10 배 빠르다*. *바이트 전송 위주* 일 때는 *sequential* 이 좋고, *DB 의 random read* 는 *최악 케이스*.
- HDD 는 *random* 이 *치명적*. *Head 가 *물리적으로 움직여야* 한다*. 100 IOPS — *초당 100 개 random 4KB* 만 가능.

### 백엔드 의사결정

- *DB 가 random read 가 많다면* — **무조건 NVMe SSD**. HDD 는 *백업 / 콜드 스토리지* 외엔 *현대 운영 부적합*.
- *append-only 로그 / WAL* — *sequential* 이라 HDD 도 가능. 비용 절감 시.
- *Elasticsearch / Kafka / ClickHouse* 등 *sequential heavy* 시스템 — *SSD 가 *성능 차이 *덜*. 그러나 *복구 / replication 시* 는 *random* 도 섞여 *SSD 가 필요*.

> 본인 cluster 운영에서 — *NVMe SSD vs HDD 의 차이* 가 *DB latency 10 배 vs 1 배* 차이로 *직접 체감*. *옛 HDD 에 ES* 깐 적 있고 *심각하게 느렸다*. NVMe 로 옮기자 *문제 사라짐*.

---

## 4. 메모리 크기 — *작아도 *많아도* 문제*

RAM 의 역할 :

1. *프로그램 자체* + *데이터 구조* 저장
2. *디스크 데이터의 *캐시*
3. *DB / 검색엔진 / Kafka* 등 *모든 high-perf 시스템* 의 *first-tier 저장소*

### *너무 작을 때*

- **Swap** 발생 → *디스크에 메모리 데이터 spill* → *RAM 100ns 였던 게 *SSD 100µs* — *1000 배 느림*
- **OOM Kill** → 프로세스 *강제 종료*
- **Cache miss 증가** → *DB 가 모든 query 마다 *디스크* 까지 가야 함

### *너무 클 때 (의외의 문제)*

- *JVM heap 30GB+* → *GC pause 가 *수초로 늘어남* (G1 보다 *큰 heap* 에 약함)
- *너무 큰 cache* → *cache 일관성 / invalidation* 이 어려워짐
- *비용 증가*

### 전형적 권장

| 서비스 | RAM 권장 |
|--------|----------|
| Spring Boot API (한 인스턴스) | 512MB ~ 2GB |
| PostgreSQL (중급) | 8 ~ 32GB |
| Elasticsearch (한 노드) | 16 ~ 64GB |
| Redis | *내가 *저장할 데이터 + 30%* |
| Kafka broker | 4 ~ 16GB |

> RAM 은 *내 데이터 크기 * 2~3 배* 가 안전 시작점. *너무 빠듯하게* 잡으면 *swap / OOM*. *너무 풍부하게* 잡으면 *비용 / GC*.

---

## 5. *디바이스* — *사용자 측* 도 *백엔드 의 성능*

사용자 측 디바이스 (휴대폰 / 노트북 / IoT) 가 *느리면* — *백엔드 가 빨라도 *체감 느림*.

대표 영향 :

1. **모바일** — *CPU 약함 + 네트워크 4G/5G + 배터리* — 큰 JSON / 이미지 / JS 처리 *느림*
2. **저사양 PC** — *오래된 Windows / 적은 RAM* — *복잡한 SPA* 가 *느림*
3. **IoT** — *수십 KB 메모리 만* — *통신 프로토콜* 자체가 *간결해야*

### 백엔드의 역할

- ***응답 크기 *최소화*** — *불필요한 필드 제거 + Gzip + Brotli*
- **이미지 *해상도 적응*** — *모바일엔 *작은 이미지*
- ***pagination / streaming*** — *큰 데이터를 *한 번에 안 보내*
- ***GraphQL / sparse fieldset*** — *클라이언트가 *필요한 것만* 받게*
- ***Edge / CDN*** — *지리적 거리 단축*

> 백엔드를 *서버만의 일* 로 보지 말라. *디바이스 + 네트워크 + 서버 = 사용자 경험*. *전 stack 의 성능 의식*.

---

## 6. CPU 속도 — *Clock × IPC × Cores × 컨텍스트*

CPU 성능을 *Clock (GHz) 하나로* 비교하던 시절은 *끝났다*. 4 가지 차원 :

1. **Clock speed** (GHz) — 한 cycle 의 빠르기
2. **IPC** (Instructions Per Cycle) — *cycle 당 *처리하는 명령 수* — 최근 CPU 의 *진짜 진보 영역*
3. **Core 수** — 동시 처리 가능한 *논리 thread 수*
4. **Cache + 메모리 대역폭** — *데이터를 얼마나 빨리 가져오나*

### 백엔드의 흔한 CPU bound

- ***JSON 직렬화 / 역직렬화*** — *큰 응답* 처리 시 *CPU 가 가장 큰 비용*
- ***암호화 / 해시*** — bcrypt / TLS / HMAC — *CPU intensive*
- ***이미지 / 영상 처리*** — *수십 ms 단위*. 별도 worker 권장
- ***대형 객체의 deep copy / GC*** — JVM / Node.js 등에서 흔함

### Context switch 의 비용

*많은 thread* 가 *동시에 active* 면 — *OS 가 *thread 간 전환* 마다 *수 µs* 소비. *1000 개 thread* 면 *분단위 누적 비용*.

해결 :
- *thread pool* 로 *동시 active 수 제한*
- *event loop / async I/O* — 한 thread 가 *여러 요청 동시 처리*
- *코루틴 (Kotlin / Go goroutine / Python asyncio)* — *경량 동시성*

---

## 7. *9 개의 절대 속도* — Latency Numbers Every Programmer Should Know

Jeff Dean (Google) 의 *유명한 표* 의 *오늘 버전* 으로 변환 :

```
L1 cache reference            ~ 1   ns
L2 cache reference            ~ 4   ns
Branch mispredict             ~ 5   ns
L3 cache reference            ~ 30  ns
Main memory reference         ~ 100 ns
Compress 1KB w/ Zippy         ~ 2   µs
Send 1KB over 1 Gbps          ~ 8   µs
SSD random read               ~ 16  µs   (~100µs 일반적)
Read 1MB sequential from RAM  ~ 5   µs
Read 1MB sequential from SSD  ~ 200 µs
Round trip same datacenter    ~ 500 µs
HDD seek                      ~ 10  ms
TCP packet roundtrip CA → NL  ~ 150 ms
```

### *이 표의 활용*

본인이 *어떤 시스템* 을 보고 *왜 느린지* 의심할 때 :

1. *전체 시간* 을 *전형적 수치* 와 비교
2. *내 시간* 이 *몇 배* 차이인지 봄
3. *수십 배 이상 느리다* 면 *그 층에 *비정상 적 비용*
4. *수 배 차이* 면 *최적화 여지가 있음*

예시 :
- *5ms 가 *예상되는 *동일 데이터센터 API 호출* 이 *50ms* — *10 배 비정상*. *네트워크 / DB / GC* 의심.
- *DB 의 *간단한 query* 가 *200ms* — *예상 ~10ms* 대비 *20 배*. *index 누락 또는 *연결 풀 문제*.

---

## 8. *백엔드 개발자의 *멘탈 모델**

위 모든 수치를 *외울 필요* 는 없다. 그러나 *대략적 비율* 은 *몸에 익혀야* 한다 :

> **L1 < RAM < SSD < LAN < 인터넷**
> **~ 100 배 격차 가 *각 단계 마다 *대략***

즉 :
- L1 의 *100 배* 가 RAM
- RAM 의 *1000 배* 가 SSD
- SSD 의 *5~10 배* 가 LAN
- LAN 의 *10~100 배* 가 인터넷

이 *지수적 격차* 가 *시스템 디자인의 *제약* 이다*. *cache 히트* 가 *왜 *비대칭적으로 *효과적인지* 가 *여기서 나옴*. *RAM 보다 *100 배 느린 *SSD 를 *건드리지 않는 것* 만으로* — *시스템 전체가 *수십 배 빨라진다*.

---

## 9. *실제 측정의 *습관*

직감을 키우려면 — *직접 측정* 이 *가장 빠른 길*.

권장 도구 :

| 측정 대상 | 도구 |
|----------|------|
| CPU bound | `perf`, `flame graph`, JFR / JProfiler |
| 메모리 | `jmap`, VisualVM, `htop` |
| 디스크 | `iostat`, `iotop`, `fio` |
| 네트워크 | `tcpdump`, `iftop`, `mtr`, `traceroute` |
| 응답시간 | Grafana + Prometheus, OpenTelemetry, Jaeger |
| 로드 테스트 | k6, Gatling, Locust, wrk |

*한 번 측정* 으로 *수치를 *몸에 *기록* 한다*. 다음 번 *비슷한 시스템* 을 보면 *예상치* 와 *현재 측정* 을 비교 — *어디가 *비정상* 인지 *바로* 짚어진다.

---

## 10. *5 개 자원 간의 *trade-off**

좋은 백엔드 디자인은 *5 자원의 *적절한 분배*. *모든 게 *동시에 빠를 수* 없다*.

흔한 trade-off :

- **RAM ↑ → CPU ↓** : 캐싱이 *CPU 부담 줄임*
- **CPU ↑ → 네트워크 ↓** : 압축이 *네트워크 비용 줄임* (CPU 대신)
- **디스크 ↑ → RAM ↓** : 큰 데이터 *디스크 활용* (cache miss 증가)
- **네트워크 ↑ → 디스크 ↓** : *원격 캐시* 활용 (S3, Redis Cluster)

엔지니어의 일 — *지금 시스템 의 병목 자원* 을 식별하고 *그 자원에 *집중* 시켜 *다른 자원 비용* 으로 *분산*.

---

## 11. 마치며

> *백엔드 개발자가 *느리다* 를 *듣고도 어디가 *느린지* 못 짚는다면* — *5 자원의 *속도 수준* 을 *몸에 익히지 않은* 것.

위 표를 *외우려고 하지 말고* — *매주 *한두 번* *내가 짠 서비스의 *지연시간* 을 측정* 하라. 한 달이면 *직감* 이 *생긴다*. *어느 층이 *원인일지* — *처음 보는 시스템* 도 *80% 정도* 짚게 된다.

*처리량 vs 응답시간* 의 차이를 *결정에 반영* 하라. *비즈니스가 *피크 트래픽 수용* 을 원하면 처리량*. *사용자가 *체감 빠른 응답* 을 원하면 응답시간*. *둘 다* 는 *비싸지만 가능* 하다 — 단 *어느 게 *지금 우선* 인지* 의 *결정* 이 *처음 출발*.

*하드웨어는 *가만히 있지 않는다*. *NVMe / DDR5 / 100Gbps 네트워크* 가 *흔해진다*. *작년의 *낭만적 최적화* 가 *올해의 *불필요한 복잡도* 가 될 수 있다*. *주기적으로 *전제* 를 갱신* 하라.

마지막으로 — *5 자원의 *수치* 를 *기억하지 못해도* — *내가 지금 *짜고 있는 시스템* 의 *예상 응답시간* 을 *최소 5 가지 자원으로 *분해* 해 *추정* 할 수 있는 *습관** — *이 습관이 *시니어 백엔드 개발자의 *근육**.

→ 다음 시스템 설계 회의 — *예상 응답시간 분해* 부터 그려 보라. *그 그림* 이 *팀의 공통 언어* 가 된다.

---

> 본 글은 *9년차 백엔드 개발자의 *실 경험* 기반. *수치는 *2026 년 상반기 기준*. *변할 수 있는 부분* 은 *원리 + 비율* 에 무게중심을. *절대 수치* 는 *측정 도구* 를 *직접 돌리는* 게 *언제나 가장 정확*.
