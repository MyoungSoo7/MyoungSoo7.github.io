---
layout: post
title: "Framework-bench 읽기 — 여섯 웹 프레임워크 벤치마크에서 숫자보다 먼저 봐야 할 것들"
date: 2026-10-24 13:50:11 +0900
categories: [Engineering, Performance]
tags: [Benchmark, k6, Axum, Spring Boot, NestJS, FastAPI, Gin, ASP.NET Core, Load Testing, Little's Law]
---

[lms0806/Framework-bench](https://github.com/lms0806/Framework-bench) 는 **Axum(Rust), Spring Boot(Java), NestJS(Node), FastAPI(Python), Gin(Go), ASP.NET Core(C#)** 여섯 개의 웹 서버 성능을 k6 로 비교하는 리포다. 2026-10-22 에 만들어졌고 이틀 동안 커밋 22개가 쌓였다. 아직 막 시작한 프로젝트다.

README, k6 스크립트, 측정 스크립트, 서버 코드 여섯 개를 모두 읽었다. 이 글은 결과를 요약하고, **그 숫자를 어떻게 읽어야 하는지**를 정리한다. 미리 말하면 이 리포는 꽤 정직하게 만들어졌다. README 스스로 "서버의 최대 처리량으로 단정할 수 없습니다" 라고 적어 두었다. 이 글은 그 문장이 **왜 맞는지**, 그리고 숫자가 실제로 무엇을 재고 있는지를 구체적으로 풀어 본다.

> 아래 측정값은 모두 리포 README 에 실린 값이다. 내가 재현한 값이 아니다.

## 1. 무엇을 어떻게 쟀나

### 서버와 엔드포인트

여섯 서버가 같은 엔드포인트 네 개를 구현한다.

| 경로 | 작업 |
|---|---|
| `GET /plaintext` | `Hello, World!` 문자열 |
| `GET /json` | `{"message":"Hello, World!"}` |
| `GET /json-large` | 항목 1,000개짜리 JSON 배열을 **매 요청마다 생성**해서 직렬화 |
| `POST /aggregate` | 숫자 1,000개 JSON 을 받아 개수·합·최소·최대 계산 |

JSON 라이브러리는 서버마다 "그 생태계에서 빠른 것" 을 골랐다. Axum 은 `sonic-rs`(직렬화)·`simd-json`(역직렬화), Spring 은 Jackson + Blackbird 모듈, NestJS 는 `fast-json-stringify`, FastAPI 는 Pydantic, Gin 은 표준 `encoding/json`, ASP.NET Core 는 소스 생성 방식의 `System.Text.Json`.

### 병렬도를 4로 맞췄다

측정 스크립트(`run-local.ps1`)는 병렬도(기본 4)를 각 런타임의 고유한 손잡이로 전달한다.

- Axum: `TOKIO_WORKER_THREADS=4`
- Spring Boot: `SERVER_TOMCAT_THREADS_MAX=4`, `SERVER_TOMCAT_THREADS_MIN_SPARE=4`
- NestJS: 클러스터 워커 프로세스 4개
- FastAPI: Uvicorn 워커 프로세스 4개
- Gin: `GOMAXPROCS=4`
- ASP.NET Core: `DOTNET_PROCESSOR_COUNT=4`

### k6 시나리오

k6 의 `constant-arrival-rate` 실행기로 목표 요청률(RPS)을 고정하고, 최대 VU 500개, 작업별 워밍업 10초 후 20초씩 3회, 반복별 **중앙값**을 보고한다. 서버와 k6 는 **같은 Windows PC** 에서 돈다.

### 잘한 점

- **응답을 검증한다.** 상태 코드만이 아니라 Content-Type 과 **본문 전체를 바이트 단위로** 기대값과 비교한다. 틀린 응답을 빨리 내는 서버가 이기는 일을 막는다.
- **사전 검증(preflight)** 이 있다. 본 측정 전에 요청 하나를 보내 틀리면 바로 실패시킨다.
- **임계값을 엄격하게 걸었다.** HTTP 실패율 0, 체크 통과율 100%, 누락 반복 0 이 아니면 k6 가 실패로 끝난다.
- **열린 모델(open model)** 이다. 응답이 느려져도 요청 도착률은 그대로 유지된다. 서버가 느려지면 요청을 덜 보내게 되는 닫힌 모델의 착시를 피한다.
- 워밍업, 3회 반복, 중앙값, 버전 고정, 서버별 테스트 코드, 그리고 **한계를 README 에 스스로 적은 것**.

## 2. 결과 요약

### 목표 50,000 RPS (2026-10-23)

README 의 성공 요청/초 중앙값을 엔드포인트별로 다시 늘어놓으면 이렇다.

| 서버 | plaintext | json | json-large | aggregate |
|---|---:|---:|---:|---:|
| Axum | 24,445.8 | 25,153.4 | **11,612.2** | **21,910.0** |
| Spring Boot | 23,091.5 | 23,015.8 | 10,434.6 | 18,625.7 |
| NestJS | 22,336.4 | 21,849.4 | 6,591.3 | 17,852.1 |
| FastAPI | 10,504.4 | 10,499.6 | 1,758.1 | 6,190.0 |
| Gin | **25,615.4** | **25,481.6** | 5,330.4 (실패율 38.5%) | 17,466.7 |
| ASP.NET Core | 25,510.3 | 24,722.1 | 10,974.5 | 20,308.1 |

**모든 작업에서 50,000 RPS 를 달성하지 못했고, 모든 작업에서 반복이 누락됐다**(README).

### 목표 10,000 RPS (2026-10-24)

| 서버 | plaintext | json | json-large | aggregate |
|---|---:|---:|---:|---:|
| Axum | 9,952.8 | 9,803.7 | **7,818.6** | 9,960.8 |
| Spring Boot | 9,916.2 | 9,869.4 | 6,878.8 | 9,987.9 |
| NestJS | 9,781.1 | 9,309.8 | 5,125.1 | 9,984.3 |
| FastAPI | 7,526.3 | 7,492.3 | 1,600.2 | 6,145.9 |
| Gin | 9,939.9 | 9,945.4 | 4,832.8 (실패율 15.8%) | 9,990.0 |
| ASP.NET Core | 9,911.8 | 9,925.8 | 7,349.3 | 9,997.4 |

## 3. 50,000 RPS 결과가 실제로 잰 것 — Little 의 법칙

50k 표에서 이상한 점이 하나 보인다. 언어도 런타임도 다른 서버 넷(Axum·Gin·ASP.NET·Spring)이 plaintext 에서 **2만 3천~2만 5천 근처에 몰려 있다.** 서버 성능이 정말 이렇게 비슷할까?

열쇠는 **최대 VU 500개**다. k6 문서에 따르면 `constant-arrival-rate` 는 정해진 요청률을 맞추려고 VU 수를 늘리는데, "The number of VUs to achieve the desired rate varies depending on how long each iteration takes to execute." 즉 필요한 VU 수는 반복 하나가 걸리는 시간에 달려 있다.[^k6-car] VU 가 바닥나면 시작하지 못한 반복이 **누락(dropped)** 으로 잡힌다.

여기에 큐잉 이론의 **Little 의 법칙** L = λW 를 대 보자.[^little] 시스템 안에 동시에 있는 요청 수(L)는 도착률(λ)에 평균 체류 시간(W)을 곱한 값이다. 이 측정에서 L 의 상한은 VU 500개다. 그러니 처리량의 상한은

```
λ ≤ L / W = 500 / (요청 하나의 평균 왕복 시간)
```

이다. 50,000 RPS 를 내려면 W 가 10ms 이하여야 한다. 그런데 FastAPI 를 뺀 다섯 서버의 plaintext·json p95 는 26~31ms 다. 거꾸로 Axum json 의 25,153 RPS 를 넣어 보면 W ≈ 500 / 25,153 ≈ **약 20ms** 다. 500개 VU 가 쉬지 않고 돌았다는 뜻이다.

정리하면 50k 측정에서 서버 순위는 사실상 **"VU 500개가 동시에 붙었을 때의 왕복 시간" 순위**다. 그 왕복 시간에는 서버 처리 시간뿐 아니라 **같은 PC 에서 CPU 를 나눠 쓰는 k6 자신의 시간**도 들어 있다. 2만 3천~2만 5천에 몰린 건 서버들의 한계가 비슷해서라기보다, **측정 장치(VU 상한 + 같은 기계)의 한계에 함께 걸린 것**으로 읽는 게 맞다.

k6 문서도 부하 생성기에 대해 경고한다. k6 가 CPU 를 100% 쓰면 "the result metrics to have a much larger response time than in reality" 가 될 수 있으니, 부하 생성기에 **최소 20% 의 유휴 CPU** 를 남기라는 것이다.[^k6-large] 서버와 k6 가 한 기계에 있으면 이 조건을 지키기 어렵고, 지켰는지도 확인하기 어렵다.

## 4. 10,000 RPS 결과가 말해 주는 것

목표를 10k 로 낮추자 그림이 달라진다. **plaintext·json·aggregate 는 FastAPI 를 뺀 다섯 개가 모두 목표에 붙었다.** 목표치에 닿은 측정은 순위를 매기지 못한다. "다섯 다 최소 1만은 낸다" 까지만 말해 준다.

그래서 10k 측정에서 실제로 서버를 가르는 신호는 두 가지다.

1. **`json-large` 처리량** — 유일하게 모두가 목표에 못 미친 작업이다. Axum(7,818.6) > ASP.NET(7,349.3) > Spring(6,878.8) > NestJS(5,125.1) > Gin(4,832.8, 실패 포함) > FastAPI(1,600.2). 1,000개 항목을 만들고 직렬화하는 **CPU 작업**이 드러나는 곳이다.
2. **꼬리 지연(p95/p99)** — 처리량이 같아도 지연은 다르다. 예를 들어 `aggregate` 는 다섯 서버 모두 1만 근처지만, p95 는 Axum 2.99ms, Spring·ASP.NET 3.99ms, NestJS 4.99ms, Gin 5.00ms 였다.

FastAPI 는 두 측정 모두에서 크게 뒤처졌다. 특히 `json-large` 는 10k 목표에서 1,600 RPS, p95 634ms 다. 다만 FastAPI 쪽은 응답 모델을 `TypedDict` 로 선언했고 Pydantic 이 응답 검증·직렬화를 맡는다. 순수 프레임워크 오버헤드인지, 응답 검증 비용인지는 이 측정만으로는 갈라 보기 어렵다.

## 5. "같은 조건" 인가 — 네 가지 비대칭

### ① Spring Boot 만 Tomcat 스레드가 기본값의 50분의 1

`SERVER_TOMCAT_THREADS_MAX=4` 는 Spring Boot 의 환경 변수 바인딩 규칙(점은 밑줄, 대시는 제거, 대문자)에 따라 `server.tomcat.threads.max` 로 들어간다.[^sb-env] 이 속성의 기본값은 **200** 이다.[^sb-props]

Spring MVC 는 기본적으로 요청 하나가 워커 스레드 하나를 점유하는 모델이다. 다른 서버들의 "4" 는 **CPU 코어 수**에 가까운 개념(Tokio 워커, GOMAXPROCS, 프로세스 수)이지만, Tomcat 의 "4" 는 **동시에 처리할 수 있는 요청 수**에 가깝다. 같은 숫자를 넣었지만 뜻이 다르다. 이번 엔드포인트들은 I/O 대기가 없는 CPU 작업이라 영향이 작을 수 있지만, 그건 측정해 봐야 아는 일이다. 기본 스레드 풀이나 가상 스레드(`spring.threads.virtual.enabled`, 기본값 `false`)[^sb-props]로 한 번 더 재 보면 확인할 수 있다.

### ② "프레임워크" 비교이자 "JSON 라이브러리" 비교

Axum 은 SIMD 기반 `sonic-rs`/`simd-json`, NestJS 는 스키마 기반 `fast-json-stringify`, ASP.NET 은 소스 생성, Gin 은 리플렉션 기반 표준 `encoding/json` 이다. `json-large` 의 차이에는 프레임워크보다 **JSON 라이브러리 선택**이 더 크게 들어가 있을 수 있다. 각 생태계의 "빠른 선택" 을 고른 건 실무적으로 의미가 있지만, 결과를 "Gin 이 느리다" 가 아니라 **"Gin + encoding/json 조합이 이 조건에서 이렇게 나왔다"** 로 읽어야 한다.

작은 불일치도 하나 있다. README 는 Axum 이 JSON 에 `sonic-rs` 를 쓴다고 적었지만, 코드를 보면 `/json` 은 axum 의 기본 `Json`(serde 기반)이고, `sonic-rs` 는 `/json-large` 와 `/aggregate` 응답에만 쓴다.

### ③ 병렬도 4 vs 기계 전체

서버는 병렬도 4로 묶였지만 k6 는 묶이지 않았다. README 에는 PC 의 코어 수와 측정 중 CPU 사용률이 없다. 남는 코어를 k6 가 얼마나 썼는지 모르면 "서버 4코어 대 부하 생성기 나머지 전부" 의 비율도 알 수 없다.

### ④ Gin 의 `json-large` 실패는 원인 미상

Gin 은 50k 측정의 plaintext·json 에서 1위인데 `json-large` 에서만 연결 거부와 타임아웃으로 실패율 38.5%(50k)·15.8%(10k)를 냈다. README 는 현상만 기록했고, 실행별 상세 결과가 있다는 `benchmark/results/` 디렉터리는 리포에 커밋되어 있지 않다(커밋된 건 차트 SVG 두 장). 원인을 추정할 근거가 공개되어 있지 않으니, 여기서도 원인은 짐작하지 않겠다.

## 6. 다음에 해 볼 만한 것

벤치마크를 더 단단하게 만들 수 있는 방향을 적는다. 리포의 방향성을 존중하는 선에서의 제안이다.

1. **VU 상한을 Little 의 법칙으로 잡는다.** 목표 RPS × 예상 p99 지연으로 필요한 VU 를 계산하고, 누락이 0 이 될 때까지 `maxVUs` 를 올린다. 누락이 생긴 측정은 "목표 미달" 이 아니라 **"측정 무효"** 로 표시하는 편이 해석이 깔끔하다.
2. **부하 생성기를 분리하거나, 최소한 CPU 를 고정한다.** 다른 기계가 어렵다면 서버와 k6 에 서로 다른 코어를 고정하고, 측정 중 k6 의 CPU 사용률을 같이 기록한다. k6 문서의 "유휴 20%" 기준을 확인할 수 있게 된다.[^k6-large]
3. **목표 RPS 를 계단식으로 올린다.** 1만에서 모두 목표에 닿고 5만에서 모두 VU 에 막혔으니, 그 사이 계단(2만, 3만…)에서 각 서버가 **처음 목표를 놓치는 지점**이 진짜 처리량 한계에 가깝다.
4. **Spring 은 기본 스레드 풀 또는 가상 스레드 버전도 같이 잰다.**
5. **JSON 트랙을 둘로 나눈다.** "각 생태계 최적" 트랙과 "표준 라이브러리" 트랙을 같이 두면 프레임워크 차이와 라이브러리 차이를 갈라 볼 수 있다.
6. **원본 결과를 커밋한다.** k6 `--summary-export` JSON 과 서버 로그가 있으면 Gin 실패 같은 이상치를 다른 사람도 들여다볼 수 있다.

## 정리

| 질문 | 답 |
|---|---|
| 측정 설계는 믿을 만한가? | 응답 본문 검증, 사전 검증, 열린 모델, 엄격한 임계값, 반복 중앙값 — 기본기는 탄탄하다. |
| 50k 결과의 순위는 서버 순위인가? | 아니다. VU 500개 + 같은 기계라는 **측정 장치의 한계**에 모두 걸렸다. Little 의 법칙으로 보면 왕복 시간 순위에 가깝다. |
| 10k 결과에서 읽을 수 있는 건? | `json-large` 의 CPU 처리량과 꼬리 지연. 나머지 작업은 대부분 목표에 닿아 순위를 매기지 못한다. |
| 조심할 비대칭은? | Spring 만 Tomcat 스레드 4개(기본 200), JSON 라이브러리가 서버마다 다름, k6 자원 미기록, Gin 실패 원인 미공개. |

README 의 마지막 경고 — "서버와 k6가 자원을 공유하므로 서버의 최대 처리량으로 단정할 수 없습니다" — 가 이 리포에서 가장 중요한 문장이다. 숫자를 인용할 땐 이 문장을 같이 들고 가야 한다.

## References

- 리포: lms0806, _Framework-bench_. <https://github.com/lms0806/Framework-bench> (2026-10-24 커밋 `28592f3` 기준)

[^k6-car]: Grafana k6 docs, "Constant arrival rate". <https://grafana.com/docs/k6/latest/using-k6/scenarios/executors/constant-arrival-rate/>
[^k6-large]: Grafana k6 docs, "Running large tests". <https://grafana.com/docs/k6/latest/testing-guides/running-large-tests/>
[^little]: J. D. C. Little, "A Proof for the Queuing Formula: L = λW", _Operations Research_, 9(3), pp. 383–387, 1961. doi:10.1287/opre.9.3.383. <https://doi.org/10.1287/opre.9.3.383>
[^sb-env]: Spring Boot Reference, "Externalized Configuration" — Binding From Environment Variables. <https://docs.spring.io/spring-boot/reference/features/external-config.html>
[^sb-props]: Spring Boot Reference, "Common Application Properties" (`server.tomcat.threads.max`, `spring.threads.virtual.enabled`). <https://docs.spring.io/spring-boot/appendix/application-properties/index.html>
