---
layout: post
title: "Discord 가 *Go 로 만든 Read States 서비스를 *Rust 로 다시 쓴* 이유와 *실측 효과* — *GC pause 의 조용한 살인자*, *p99 의 *수 ms → < 1 ms*, *메모리 *5 배 감소* 의 *정공적 분해*"
date: 2026-06-10 17:30:00 +0900
categories: [performance, rust, go, case-study]
tags: [discord, rust, golang, gc, garbage-collection, latency, p99, ownership, borrow-checker, tokio, async, memory, rewrite, case-study, performance, system-language]
---

*Discord 가 *2020 년* 자기들의 *Read States* 서비스 — *초당 수십만 메시지 의 *읽음 상태 추적* — 를 Go 에서 Rust 로 *재작성* 한 사례*. *한 서비스 의 *언어 교체* 가 *수년 후* *Rust 의 시스템 프로그래밍 지위 를 *대중 화* 시킨 *상징적 사건* 이 됐다. 표면 상의 이유 는 *"Go GC pause 가 p99 를 망친다"* 였지만 — *진짜 이유는 *deterministic *메모리 모델 의 차이*. 그 차이 가 *실측 으로 *얼마나 큰지* 가 *압도적 으로 인상적*.

이 글은 *그 *공식 블로그* 의 핵심 + *그 안 의 *진짜 기술 적 이유* 를 정리 한다. **(1) Read States 가 무엇이고 왜 까다로운가**, **(2) Go 의 한계 — GC 의 *조용한 살인자***, **(3) 왜 Rust 인가 — *ownership = GC 없는 안전**, **(4) Discord 의 *실측 효과 비교***, **(5) 일반화 — Rust vs Go 의 *어디서 차이가 나는가***, **(6) *Rust 가 정답이 아닐 때***, **(7) 학습 로드맵**. 어제 [캐시 적중률](https://myoungsoo7.github.io) / [서버 성능 기초](https://myoungsoo7.github.io) 글 의 *심화 시리즈*.

> **출처**: Discord 의 2020 년 2 월 공식 블로그 [*"Why Discord is switching from Go to Rust"*](https://discord.com/blog/why-discord-is-switching-from-go-to-rust). 본 글의 *수치 와 분석* 은 모두 *그 블로그 + 후속 컨퍼런스 발표* 에 기반.

---

## TL;DR

| 지표 | Go (이전) | Rust (이후) | 변화 |
|---|---|---|---|
| **평균 응답 시간** | 약 *20 ms* | 약 *5 ms* | *~4 배 빠름* |
| **p99 latency 의 *튐 (spike)*** | *수 백 ms ~ 수 초* | *< 1 ms* | *수 백 배 안정* |
| **CPU 사용량 (동일 부하)** | baseline | *~10% 수준* | *~10 배 적음* |
| **메모리 footprint** | baseline | *~5 배 감소* | 5 배 적음 |
| **GC pause** | *2 분마다 2 초* (관측됨) | *0 (GC 없음)* | 사라짐 |
| **개발 시간** | 빠른 prototype | *느린 학습* + *튼튼한 구현* | trade-off |

**핵심 메시지**:

- *Go 의 GC pause 는 *모든 코드 최적화 의 효과 를 *집어삼킨다*. 아무리 좋은 알고리즘 도 *2 초 멈춤* 앞에선 무의미.
- *Rust 의 *ownership system* 은 *GC 없이 메모리 안전* 을 *컴파일 타임* 에 보장. *런타임 의 *어떤 pause 도 없다*.
- *Discord 의 *수치 는 *예외적 으로 인상적* — 일반적인 서비스 에서는 *2 ~ 3 배 의 개선 이 더 흔함*. 그러나 *p99 의 안정성* 은 *어디든 *극적*.
- *Rust 가 정답이 아닌 자리* 도 명확 — *학습 비용*, *컴파일 시간*, *프로토타입 속도*. 모든 서비스 가 Read States 처럼 *극한* 요구 가 아니다.

**실무 함의**: *지금 시스템의 *p99 가 *튄다* 면 — *원인을 *GC* 또는 *외부 API* 둘 중 하나 로 좁힐 수 있다. Rust 가 답이 되는 경우는 *전자* (GC 가 진짜 원인일 때). *그 외 에는 *Go / Java / Kotlin 의 더 가벼운 도구* 가 정공.

---

## 0. *Read States 서비스* — *수십만 RPS 의 *읽음 상태**

Discord 의 *모든 메시지 / 모든 채널* 에 대해 *각 사용자 의 *마지막으로 읽은 위치* 를 추적. 사용자가 *수억 채널 × 수십억 메시지* 를 *읽음 표시* 하는 동안 — *그 상태 가 *모든 디바이스 에 *실시간 동기화* 되어야 한다.

특징:
- *읽기·쓰기 비율 이 *압도적 으로 쓰기 편향*. 초당 수십만 RPS.
- *작은 객체 가 *수억 개*. *Read State 1 개 = 채널 ID + 마지막 메시지 ID + 마지막 mention + 카운트* — *수십 바이트*.
- *지연 이 *사용자 체감 의 *적색*. 늦으면 *"읽음 표시 가 안 사라진다"* 의 *느린 앱* 인식.

*이 워크로드 에서 Go 의 GC 가 *질병 으로 드러남*.

---

## 1. *Go 의 한계* — *GC 의 조용한 살인자*

### 1-1. *Go GC 는 *세계 최고 수준* — 그런데도 문제*

Go 의 *concurrent mark-and-sweep* GC 는 *2015 년 이후 GC pause 가 *수 ms 이하로 *압축됨*. *Java 의 G1 / ZGC 와 *대등한 수준*. *대부분의 서비스 에는 *충분 함*.

그런데 Read States 는 *수억 개 의 작은 객체* 를 *상시 유지*. *GC 의 *mark 단계 가 *모든 객체 의 *살아 있음* 을 검사*. *객체 수 가 많을수록 *그 비용 이 폭증*.

### 1-2. *Discord 가 관측한 *2 분 주기 의 *2 초 pause**

> "the lazy collector causes a 2-second pause every 2 minutes" — Discord 의 공식 블로그

*2 분에 한 번 — *어김 없이 *2 초* GC pause*. 그 동안 *모든 요청 이 *대기*. *p99 latency 가 *수 백 ms 의 *spike*. 그 *spike 가 *모니터링 그래프 의 *치명적 모양*.

*Go GC 의 *튜닝* 으로 *시도 했지만* — *근본적 해결 불가능*. *GC 가 있는 한 *pause 는 *어딘가에서 *반드시 발생*. 빈도 / 길이 / 순간 의 trade-off 만 있다.

### 1-3. *왜 *Discord 만 이 문제 를 겪었나*

대부분의 Go 서비스 는 *수천~수만 RPS* + *적당한 객체 수*. *GC pause 가 *수십 ms* 라 *p99 에 *눈에 띄지 않음*.

Discord 의 Read States 는 *수십만 RPS* + *수억 객체* 의 *극단 의 워크로드*. *GC 의 비용 이 *비선형 적으로 *치솟음*. *대부분의 서비스 에선 Go 의 GC 가 안 보이지만 — *Discord 의 극한 에서는 *주범*.

---

## 2. *왜 Rust 인가* — *Ownership = GC 없는 안전*

### 2-1. *Rust 의 *3 가지 약속**

1. *메모리 안전* — *컴파일 타임 에 use-after-free, double-free, leak 의 *대부분 차단*
2. *데이터 경쟁 없음* — *컴파일 타임 에 race condition *대부분 차단*
3. *Zero-cost abstraction* — *추상화 비용 0*. *고수준 코드 = 저수준 C 와 *같은 성능*

이 셋 을 *런타임 비용 (GC, runtime) *0 으로 달성*. *어제 [컴퓨터과학 7 분야](https://myoungsoo7.github.io) 글 의 *Rust 의 ownership 예제* 의 *진짜 효과*.

### 2-2. *Ownership 의 *예제 1 줄**

```rust
let s1 = String::from("hello");
let s2 = s1;                    // 소유권 이동
println!("{}", s1);             // 컴파일 에러! s1 은 더 이상 유효 X
```

*C 였다면 *런타임 의 *use-after-free* 사고. *Java 였다면 *GC 가 알아서* — 하지만 *GC 의 cost*. *Rust 는 *컴파일러 가 *못 컴파일 시킴*.

### 2-3. *Drop = *deterministic 해제**

```rust
fn process() {
    let data = load();           // 큰 데이터 로드
    use_data(&data);
}                                // ← 정확히 여기서 *data 의 메모리 즉시 해제*
```

*scope 종료 = *해제 시점이 *컴파일 타임 결정*. *GC 의 *나중에 한꺼번에* 와 정반대. *latency 의 *예측 가능성* 이 *압도적*.

---

## 3. *Discord 의 *실측 효과**

### 3-1. *Latency 그래프 가 *완전히 다른 모양*

원본 블로그 의 *대표 그래프*:

```
Go 시절 의 p99:
   ms
1000 |        █ █                    █
 800 |    █   █ █     █              █
 600 |    █   █ █     █     █        █
 400 |    █   █ █     █     █  █     █
 200 |  █ █   █ █  █  █  █  █  █ █   █
   0 |__█_█___█_█__█__█__█__█__█_█___█__
        ^^ GC pause 마다 *수 백 ms spike*

Rust 이후 의 p99:
   ms
   5 |
   4 |
   3 |
   2 |
   1 | ████████████████████████████████  ← 평탄
   0 |__________________________________
```

*Spike 자체 가 *사라짐*. *p99 가 *5 ms 미만 으로 *안정*. *모든 사용자 가 *같은 좋은 경험*.

### 3-2. *CPU 사용량 ~ 10 배 감소*

같은 트래픽 처리에 *CPU 가 *Go 대비 *~10% 수준*. *Go 도 *빠른 언어* 인데 — *Rust 가 *비교 우위 가 큰 이유*:

- *GC 없음* — *GC 코드 실행 자체 가 *CPU 비용*
- *Cache 친화 적 메모리 배치* — Rust 는 *stack 우선*, Go 는 *heap 의 GC 친화 적 배치*
- *Inlining + 인라인 최적화* — LLVM 최적화 가 *훨씬 깊이 들어감*

*"같은 일 을 *10 배 적은 CPU 로*"* — *클라우드 비용 도 비례 절감*.

### 3-3. *메모리 5 배 감소*

Rust 의 *minimal runtime overhead* + *stack 우선* + *deterministic drop* 의 결과:

- Go 의 *struct 는 *GC heap 에 가는 경향* (escape analysis 한계)
- Rust 의 *struct 는 *stack 또는 *small heap*. *GC bookkeeping 없음*

*수억 개 의 작은 객체 가 *수십 GB → 수 GB* 로 감소*. *물리 서버 수 도 감소*. *비용 = 메모리 = 서버 수* 의 *직선 적 효과*.

### 3-4. *서버 대수 감소 → 운영 비용 직접 감소*

공식 수치는 명시 안 됐지만 — *CPU 10 배 + 메모리 5 배 + spike 없음* 의 조합 으로 *서버 대수 가 *수 분의 1*. *클라우드 비용 절감 의 *직접 효과* + *운영 의 단순화*.

---

## 4. *Rust vs Go* — *어디서 차이가 나는가*

| 차원 | Go | Rust | 누가 우위 |
|---|---|---|---|
| *메모리 모델* | GC | Ownership | Rust (예측 가능성) |
| *런타임 pause* | GC pause 수 ms | 0 | Rust |
| *추상화 비용* | 작음 | *0* | Rust |
| *컴파일 시간* | *매우 빠름* | 느림 | Go |
| *학습 곡선* | *완만* | *가파름* | Go |
| *언어 단순함* | *극단 적* | 복잡 | Go |
| *동시성 모델* | goroutine + channel | async/await + tokio | Go (단순), Rust (제어) |
| *생태계 (백엔드 서비스)* | 성숙 | 빠르게 성장 중 | Go (현재), Rust (미래) |
| *프로토타이핑 속도* | *최고급* | 느림 | Go |
| *튼튼함 (production)* | *높음* | *최고급* | Rust |
| *p99 안정성* | GC 따라 다름 | *극도로 안정* | Rust |
| *고수준 코드 성능* | *빠름* | *C 와 동급* | Rust |

*이 표 가 *언어 선택 의 *체크리스트*. *극한 의 *p99 안정성 + 메모리 footprint* 가 필요 하면 Rust. *빠른 개발 + 적당한 성능* 으로 충분 하면 Go.

### 4-1. *Go 가 여전히 정공 인 자리*

- *프로토타입 / MVP* — *빠른 작성 + 빠른 배포*
- *대부분 의 API 서버* — *수천 RPS 의 일반 워크로드*
- *DevOps 도구* — *kubectl, terraform, helm 의 *Go 가 표준*. *단일 바이너리 의 *배포 편의성*
- *팀 의 *Go 숙련도 가 높을 때* — *학습 곡선 비용 회피*

### 4-2. *Rust 가 정공 인 자리*

- *시스템 프로그래밍* — 운영체제, 임베디드, 브라우저 엔진
- *극한 의 latency 요구* — *p99 < 1 ms* 같은 SLO
- *수백만 RPS 의 *작은 객체 워크로드* — Discord 의 Read States
- *메모리 제약 환경* — IoT, edge computing
- *Safety critical* — *use-after-free 가 *법적 책임* 으로 갈 수 있는 자리

---

## 5. *Rust 가 정답이 *아닐 때*

### 5-1. *학습 곡선 의 *현실 적 비용**

Rust 는 *2 년 차 개발자 가 *3 개월 학습 후 *production 코드* 를 짤 수 있다* 정도. Go 는 *2 주*. *팀 의 *모든 멤버 가 *Rust 를 익히는 *총 비용* 이 *연간 수 천 만 원 ~ 억 단위*.

Discord 는 *그 비용 을 정당화 할 수 있는 *극한 의 워크로드* 가 있었다. 일반 적인 *수백 RPS 의 *비즈니스 서비스* 에서는 *그 비용 의 회수 가 *불가능*.

### 5-2. *컴파일 시간 의 압박*

Rust 의 *리컴파일 시간* 은 *Go 의 *수 배*. *5 분 컴파일* 이 *흔함*. *iterative 개발 의 사이클 이 느려짐*. *프로토타입 단계* 에서 *치명적*.

### 5-3. *생태계 의 *그래도 아직 *불완전**

Spring Boot 같은 *모든 게 포함된 *frameworks* 가 *Rust 에는 *아직 미성숙*. *DB driver, ORM, HTTP client* 등 *기본 라이브러리 의 *성숙도* 가 *Go / Java 보다 *떨어짐*. *2025 년 의 현실*.

### 5-4. *틀린 의사 결정 의 신호*

*"멋있어서 Rust"* — *기술 채택 의 가장 위험한 동기*. *극한 의 latency / 메모리 / safety 요구* 가 *명시적* 이지 않으면 — *Go / Kotlin / Java 가 정공*.

---

## 6. *후속 영향* — *Rust 의 *2020 → 2025 의 부상**

Discord 의 사례 가 *Rust 의 *시스템 영역 *기업 채택* 의 *시동탄*. 후속:

- *AWS Firecracker* (Lambda / Fargate 의 기반 VMM) — *Rust*
- *Cloudflare Workers* — *Rust*
- *Dropbox 의 *Magic Pocket* 일부 — *Rust*
- *Microsoft 의 *Azure 일부 + Windows 커널 부분* — *Rust*
- *Linux 커널 의 *Rust 모듈 정식 채택* (2023)

*"시스템 영역 의 Go" 의 자리 가 *5 년 만 에 *Rust 로 옮겨갔다**. *Discord 가 그 출발점 의 *상징*.

---

## 7. *한국 에서 의 *Rust 채택 사례*

대형 한국 기업 의 *백엔드 Rust 채택 사례 는 *2025 년 기준 *아직 적다*. 주된 영역:

- *블록체인 / 암호화폐* — *극한 성능* 요구. *클레이튼, 카이아* 등 의 *부분 모듈*
- *Edge / CDN* — *Cloudflare 한국 지사 등*
- *Game 백엔드 의 *극한 부분* — 일부 게임사 의 *실시간 매칭 서버*
- *AI 인프라* — *벡터 DB, model serving* 의 *고성능 부분*

*대부분의 비즈니스 백엔드 는 *여전히 *Java / Kotlin / Go 의 영토*. *Rust 가 *주류 가 되려면 *학습 비용 의 *기업 적 투자* 가 필요*.

---

## 8. *학습 로드맵* — *Rust 시작 하기*

| 단계 | 집중 | 자료 |
|---|---|---|
| 1 | *Ownership / Borrow Checker* | *The Rust Book* (무료 공식, 한국어 번역 있음) |
| 2 | *Result / Option / 에러 처리* | *Rust by Example* (무료 공식) |
| 3 | *Trait + Generic* | 위 동일 |
| 4 | *async / tokio* | Tokio 공식 docs |
| 5 | *백엔드 framework — axum / actix-web* | axum 의 examples |
| 6 | *Database (sqlx / sea-orm)* | 라이브러리 docs |
| 7 | *실전 프로젝트 — *작은 마이크로서비스 1 개* 만들어 보기 | (개인 선택) |

### 8-1. *최소 어휘* 한 줄 정리

- *Ownership / Borrow* — Rust 의 *영혼*. 메모리 안전 의 *컴파일 타임 보장*
- *Lifetime* — *참조 의 *유효 기간 의 *컴파일러 추적*
- *Trait* — *Java 의 interface + Haskell 의 type class 의 *교집합*
- *Result<T, E>* — *예외 대신 *값 으로 *에러 처리*
- *async / .await* — *Tokio runtime 위 의 비동기*
- *Cargo* — *빌드 + 패키지 관리 의 *단일 도구*. *Maven, npm 같은*
- *No GC* — *Rust 의 *최대 차별점*

---

## 9. *마무리* — *언어 선택 = trade-off 의 명시화*

*"Discord 가 Rust 로 갈아탔다 = 우리 도 가야 한다"* — *기술 결정 의 가장 위험한 추론*. Discord 의 *극한 의 워크로드* 는 *대부분의 한국 백엔드 서비스 와 *완전히 다른 동물*. *그들이 풀 수 없던 문제 가 *우리 의 문제 가 *아닐 수 있다*.

*언어 선택 의 *세 가지 기준*:

1. *극한 의 latency / 메모리 / safety 요구* — *명시적 으로 정량 화*. SLO 가 *p99 < 1 ms* 이면 Rust 검토. *p99 < 100 ms* 이면 Go / Java 도 충분.
2. *팀 의 *기존 숙련도* — *학습 곡선 의 *총 비용 vs 성능 의 이익* 의 *수년 적 비교*. 1 명 이 Rust 를 안다 ≠ 팀 이 Rust 를 안다.
3. *서비스 의 *수명*. *향후 5 년 운영* 할 시스템 이면 *학습 투자 의 회수 기간이 길다*. *6 개월 의 PoC* 면 *그 투자 의 회수 불가능*.

*"Discord 의 *수치 는 *극단 적이고 *그래서 *인상적*. 우리 시스템 의 *수치는 *그 정도가 *아닐 가능성 이 크다*. 그러나 *p99 의 *spike 가 *진짜 문제 인 자리* — *결제, 매칭, 인증 같은 critical path* — 에서는 *Rust 의 결정* 이 *수년 의 *운영 효과* 로 돌아온다*. *case-by-case 의 분석 이 정공*.

*"Rust 를 *모든 자리에 *쓸 필요 없다*. 그러나 *언제 Rust 를 써야 하는지* 는 *알아야 한다*. Discord 의 사례 가 *그 *경계 선* 을 *우리 모두 에게 *가시화* 시킨 *공헌*."* — 이 한 줄 이 *글 의 결론*.
