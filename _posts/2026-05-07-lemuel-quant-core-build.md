---
layout: post
title: "lemuel-quant-core: 9개 언어로 만든 통합 퀀트 인프라 (Day 1~2)"
date: 2026-05-07 23:30:00 +0900
categories: [infra, quant]
tags: [cpp, python, r, rust, go, julia, kubernetes, redis, postgresql, cloudflare-tunnel, binance, dart, kr-finbert]
---

이틀 만에 0에서 시작해 9개 언어로 5,500줄을 짜고 3대 서버에 풀 배포까지 끝낸 정량 시스템 구축기.

## 왜 만들었나

운영 중인 6개 사이트(crypto, stock, dart, news, data, codingtest) 가 각각 따로 데이터를 긁고 있었다. 같은 시세를 4번 받고, 같은 공시를 3번 파싱하고, 채점은 사이트마다 위험하게 직접 돌리고 있었다. 이걸 하나의 코어로 통합하기로 했다.

목표:
- **수집**: 시세/공시/뉴스를 한 곳에서 받아서 Redis 로 fan-out
- **저장**: 5분마다 Cloudflare R2 에 Parquet 백업
- **분석**: GARCH/ARIMA/공적분/백테스트 한 자리에서
- **결과**: Shiny 대시보드, 일간 PDF, Telegram 시그널 알림

## 한 줄 요약

> "Binance/한투/DART/RSS → 분석 → 사이트/Telegram" 자동 파이프라인. 9개 언어, 14개 서비스, 3대 서버, ~5,500줄.

## 모듈 14개

### 🏛️ C++ 코어 6개

이건 실시간성과 메모리 효율이 중요해서 C++20 + CMake.

- **judge-engine** — codingtest 채점기. seccomp-bpf 시스템콜 화이트리스트 + cgroup v2 메모리/CPU 제한 + setrlimit + chroot. fork+execv 로 자식 띄우고 1초 타임리미트. AC/WA/CE/TLE/MLE/RE 6 verdict. gRPC 서버 모드 별도 빌드.
- **market-feed** — Binance combined-stream WSS 클라이언트. Boost.Beast TLS handshake + simdjson ondemand 파싱 + hiredis publish. trade.binance.* / book.binance.* 채널.
- **stock-feed** — 한투 OpenAPI WebSocket. OAuth2 (token + approval_key) → ws://ops.koreainvestment.com:21000 → H0STCNT0(체결)/H0STASP0(호가) tr_id 별 dispatch. KRX 장 시간(9:00~15:30) + 동시호가 + 시간외 자동 인지.
- **dart-crawler** — DART OpenAPI 60초 폴링. simdjson 으로 list 배열 추출 → libpqxx PostgreSQL upsert(ON CONFLICT DO NOTHING). 첫 가동에 100건 들어옴. seen set 10k LRU 로 메모리 DoS 방지.
- **news-pipeline** — 4단계: RSS 크롤링(libcurl + 자체 XML parser) → 사전 기반 종목 NER(longest-match) → KR-FinBERT ONNX 추론 → 반감기 2시간 exponential decay 점수보드.
- **data-warehouse** — Redis 구독 워커 + 5분 주기 rollup. Apache Arrow Schema 빌더 → Parquet 직접 출력 → AWS SDK PutObject(R2 endpointOverride).

공유 추상화는 `shared/include/lqc/` 에 두고 `lqc::feed::FeedClient` 인터페이스로 crypto/equities 양쪽이 같은 코드 모양.

### 🐍 Python 2개

- **backtester** — R2 Parquet 다운로드 → pandas/vectorbt → SMA/RSI/Bollinger 전략 → Sharpe/CAGR/MDD 메트릭 + 차트 PNG. CLI: `python -m backtester.run --symbol btcusdt --strategy sma --fast 20 --slow 60`.
- **strategy-bot** — Redis 트레이드 스트림 구독. 종목별 deque 윈도우 유지 + MA crossover + Price jump detector. 시그널 발생시 Telegram 알림. (symbol, kind) 별 60초 cooldown 으로 스팸 방지.

### 📊 R 6개

R 의 통계적 엄밀성이 필요한 부분.

- **r/common** — paws.storage(R2 클라이언트) + redux(Redis) + RPostgres(DART) 헬퍼.
- **quant_research/backtest.R** — PerformanceAnalytics + TTR + xts 로 SMA/RSI/Bollinger 백테스트.
- **stat_models/garch_volatility.R** — rugarch GARCH(1,1) student-t. 매 15분 cron 으로 sigma_next + persistence + half-life publish.
- **stat_models/arima_forecast.R** — forecast::auto.arima 다음 60봉 점/구간 예측. 매 시간 cron.
- **stat_models/cointegration.R** — Engle-Granger ADF + Johansen trace 두 검정으로 페어트레이딩 후보 발굴 + 헤지비.
- **daily_report/report.qmd** — Quarto 일간 리포트. 변동성 표 + 가격 차트(ggplot2) + DART 공시 30건. 매일 09:00 KST 렌더 + Telegram sendDocument.
- **shiny_dashboard** — Shiny + bslib darkly. 3개 탭: Live trades(plotly) / Backtest / DART. systemd unit으로 :3838 항시 가동.
- **risk_engine** — Historical/Parametric Gaussian/Monte Carlo 3종 VaR + CVaR + 연환산 Sharpe.

### 🦀 Rust 1개

- **orderbook-matcher** — tokio + tokio-tungstenite. Binance @depth20@100ms 풀 호가창을 BTreeMap<Px, f64> 로 유지(Px 는 i64 ×1e8 fixed-point). top-of-book + spread bps 계산해 `book.binance.<sym>.top` 채널 publish. 검증: BTC mid $81,038 / spread 0.001 bps.

### 🐹 Go 1개

- **lqc-gateway** — 한 바이너리 3가지: ① Prometheus exporter(채널별 메시지 카운터 + last-seen age) ② SSE bridge `/stream/<channel>` (브라우저 EventSource) ③ /healthz(Redis ping + 핵심 채널 fresh).

### 🔵 Julia 1개

- **QuantTools.jl** — Black-Scholes(call/put + 5 Greek + Newton-Raphson IV) + JuMP/HiGHS Markowitz mean-variance + efficient frontier + SMA crossover 백테스터(R 대비 50~100배 빠름) + Parquet2 직접 로더. 검증: BS call $10.4506 (textbook 값).

## 서버 배치

| 서버 | 모듈 | 이유 |
|------|------|------|
| 르무엘클라우드 (AWS Lightsail) | judge-engine | codingtest 사이트와 동일 호스트, 외부 코드 격리는 클라우드가 안전 |
| 루이스 (홈서버) | market-feed, stock-feed, dart-crawler, lqc-gateway, orderbook-matcher | crypto/stock/dart 사이트가 같은 호스트 — localhost Redis push |
| 르무엘 (홈서버) | news-pipeline, data-warehouse, shiny-dashboard | KR-FinBERT 메모리 + 디스크 I/O — 32GB RAM 필요 |

## 데이터 흐름

```
Binance/한투/DART/RSS
     ↓ (실시간)
[C++ 코어 6개] → Redis pubsub
     ↓ (5분 rollup)
data-warehouse → R2 Parquet 백업
     ↓ (cron)
[R/Julia 분석] → 시그널 publish
     ↓
[strategy-bot/Shiny/사이트] → 사용자
```

## 고생한 9가지

순서대로 부딪히고 해결한 것들.

### 1. Boost 1.90 (Homebrew) `find_package COMPONENTS system` 안 됨

Beast/Asio 가 header-only 라 `find_package(Boost CONFIG)` + `Boost::headers` 로 우회.

### 2. Linux gcc 가 `<algorithm>` 명시 include 요구

`std::max({a, b, c})` 의 initializer-list 오버로드. macOS clang 은 transitive include 로 통과했지만 GCC 13 에서 fail. 헤더 추가.

### 3. seccomp 화이트리스트 부족 → hello world 도 SIGSYS

glibc 2.35+ (Ubuntu 22.04+) 가 startup 에 `clone3`, `rseq`, `prctl`, `execve` 사용. 최소 화이트리스트로는 컴파일된 hello world 도 죽었다. 30+ syscall 추가 + clone 은 `CLONE_THREAD` 마스크 일치만 허용해서 namespace escape 차단.

### 4. AWS SDK for C++ 2.0 `S3Client(creds, ccfg)` deprecated

`SimpleAWSCredentialsProvider` + `(provider, endpointProvider, ccfg)` 형태로 변경. `Aws::FStream` 도 typedef 충돌 → `Aws::StringStream` 으로 우회.

### 5. simdjson `find_field` 가 가끔 작동 안 함

DART API 응답에서 `doc.find_field("list")` 가 SUCCESS 인데 array 가 비어보임. 객체 순회 패턴(`for (auto field : obj)`) 으로 우회. `simdjson_result<string_view>` 비교는 `.get(sv)` 후 비교.

### 6. libcurl 이 default User-Agent 로 DART API fail

UA 가 비어있으면 DART 가 빈 응답 리턴. `CURLOPT_USERAGENT="lemuel-quant-core/0.1"` + `CURLOPT_FOLLOWLOCATION=1` 추가.

### 7. KR-FinBERT IR 버전 mismatch

`torch.onnx.export` 가 IR 10 으로 만들었는데 ONNX Runtime 1.17.1 이 IR 9 까지만 지원. 두 단계 해결: ONNX Runtime 1.20.1 업그레이드 + `optimum.onnxruntime.ORTModelForSequenceClassification` 으로 재export(IR 8 / opset 18 / 387MB 단일 파일). C++ FinBertOnnx 에 `token_type_ids` 입력 추가(BERT 는 3-input).

### 8. R `install.packages(..., dependencies=TRUE)` 가 DuckDB 컴파일에서 stuck

40분 후 죽이고 `dependencies=c("Depends","Imports","LinkingTo")` 로 재시도. Suggests 가 거대한 의존성 트리를 끌어왔던 게 원인. redux/RPostgres 는 libhiredis-dev/libpq-dev 추가 후 별도 install.

### 9. Quarto + R + lqc(nologin shell) 권한 충돌

`quarto::quarto_render()` 가 processx 통해 spawn 하다 EACCES. `system2()` 직접 호출로 우회. 추가로 quarto 가 work_dir 외부에 출력 시도 → cd 후 상대경로 호출로 해결.

## 보안 — 1라운드 감사 + fix

작동 확인 후 4개 시스템(cloud/lemuel/louise/macOS) + 코드 보안 감사 돌렸다. 발견 + 조치:

🔴 Critical
- 루이스 product-redis :6379 무인증 + LAN 노출 → 외부 redis-cli 응답 확인 → docker-compose 127.0.0.1 바인딩 + iptables DOCKER-USER drop
- 르무엘 goods-redis :6385 동일 처리
- judge-engine gRPC 0.0.0.0:50051 무인증 → 127.0.0.1 바인드 (AWS SG 가 외부는 막고 있었지만 코드 레벨에서도)

🟡 High
- macOS sandbox `popen` 셸 문자열 인젝션 잠재 → fork+execv 로 변경
- seccomp execve 무제한 → 허용 필수, clone 은 `CLONE_THREAD` 마스크 일치만 허용
- install_deps.sh 외부 tarball 다운로드 → ONNX Runtime sha256 핀, AWS SDK commit hash 옵션 추가
- DART URL `crtfc_key=` raw concat → `curl_easy_escape()` 적용
- Binance/KIS WS frame size 무제한 → `read_message_max(256KB)`

🟡 Medium
- runner.cpp 동시 제출 race(workdir 공유) → per-submission UUID 디렉토리 + RAII 정리
- runner.cpp 컴파일 명령 popen → fork+execvp("c++", argv)

이걸로 보안 자세 MEDIUM-HIGH → MEDIUM-LOW.

## 코드 통계

```
C++       1,800 lines  (6 모듈 + gRPC)
R         1,058 lines  (6 프로젝트 + Shiny + Quarto)
Python      600 lines  (backtester + strategy-bot + common)
Rust        380 lines  (orderbook-matcher)
Julia       350 lines  (QuantTools)
Go          280 lines  (lqc-gateway)
─────────────────────
합계      4,468 lines  (외 docs/scripts/systemd/cron 포함시 ~5,500)
```

빌드/배포 인프라(systemd unit 9종, GitHub Actions, install_deps.sh, build_and_install.sh, server_assignments.md, CLAUDE.md, site-integration.md) 도 별도 ~600 lines.

## 무엇이 살아있나

> Day 2 끝 기준, 8 서비스 active 상태로 자동 운영 중

- judge-engine (르무엘클라우드, gRPC 대기)
- market-feed (루이스, BTC/ETH 실시간 — 검증된 마지막 트레이드 $81,038)
- dart-crawler (루이스, 공시 101건 저장)
- lqc-gateway (루이스, Prometheus + SSE)
- orderbook-matcher (루이스, top-of-book 0.001 bps spread)
- news-pipeline (르무엘, FinBERT 추론 중)
- data-warehouse (르무엘, 5분 rollup → R2)
- shiny-dashboard (르무엘 :3838)

cron 스케줄:
- 매일 09:00 KST: daily report 렌더 + Telegram
- 매 15분: GARCH 변동성 publish
- 매 시간: ARIMA 60봉 예측

## 회고

**잘한 거**
- 처음부터 모듈 경계와 인터페이스를 lqc::feed 로 추상화 — crypto/equities 가 같은 코드 모양
- 외부 의존성을 `LQC_HAS_<X>` define 으로 가드해서 일부 lib 없는 환경에서도 폴백으로 빌드
- systemd unit 안에 NoNewPrivileges, ProtectSystem 등 hardening 옵션 미리

**아쉬운 거**
- R `dependencies=TRUE` 로 시작했다가 DuckDB 에서 40분 날렸다. 처음부터 minimal deps 로 갈 걸
- macOS dev 빌드와 Linux production 빌드 사이에 syscall/header 차이 미리 정리해두지 않아서 배포 단계에서 발견
- ONNX Runtime 버전 + 모델 IR 호환성 매트릭스 미리 확인 안 함

**다음 할 거**
- Cloudflare Tunnel 로 Shiny 외부 노출 (shiny.lemuel.co.kr)
- KIS API 키 받아 stock-feed 활성화
- 4번째 홈서버 데이비드 추가 (k3s 클러스터 확장)
- 사이트 레포에 connector 코드 직접 통합

레포: [github.com/MyoungSoo7/lemuel-quant-core](https://github.com/MyoungSoo7/lemuel-quant-core)
