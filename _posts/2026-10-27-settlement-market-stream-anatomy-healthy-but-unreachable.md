---
layout: post
title: "market-stream-service 해부 — 건강한데 아무도 못 닿는 Go 서비스 하나"
date: 2026-10-27 23:13:30 +0900
categories: [settlement, architecture]
tags: [go, sse, websocket, fan-out, goroutine, nginx, kubernetes, settlement]
---

정산 시스템(비공개 레포 `settlement`)에는 자바가 아닌 서비스가 두 개 남아 있다. 하나는 파이썬 receipt-ocr 이고, 다른 하나가 오늘 뜯어볼 **Go 로 쓴 `market-stream-service`** 다. 하는 일은 단순하다. 종목 코드 하나에 대해 1초마다 시세 틱을 만들고, 그 종목을 보는 브라우저 전부에게 SSE 로 흘려보낸다.

코드는 작다. 테스트를 빼면 Go 파일 7개, 의존성은 `nhooyr.io/websocket` 하나다. 그런데 오늘 밤 이 서비스를 처음부터 끝까지 따라가 보니 결론이 두 갈래로 갈렸다.

- **안쪽은 잘 만들어졌다.** 동시성 모델이 명확하고, 실제로 운영 파드를 죽였던 경합을 고치면서 남긴 주석이 교과서 수준이다.
- **바깥에서는 닿지 않는다.** 운영 클러스터에서 공개 경로로 부르면 이 서비스가 아니라 모놀리스가 `401` 을 돌려준다. 파드는 `Running`, 재시작 0회다. 그런데 듣는 사람이 없다.

이 글은 구조를 위에서 아래로 내려간 뒤, 그 구조가 운영에서 어디서 끊기는지를 실측으로 보여준다.

## 1. 한 장 요약

```
브라우저 (CeoInvestPage → LiveQuoteTicker)
   │  EventSource('/api/market-stream/stream/005930')
   ▼
frontend nginx ──(compose: gateway-service)──► gateway  RewritePath /api/market-stream/x → /x
   │                                                   │
   ▼                                                   ▼
market-stream-service :8110   (Go, distroless, non-root)
   ├─ cmd/server        설정 로드 · 소스 선택 · HTTP 서버 · graceful stop
   ├─ internal/httpapi  GET /healthz · GET /stream/{code} (SSE) · GET /ws/{code}
   ├─ internal/hub      종목당 고루틴 1개 → 구독자 N 명 팬아웃
   └─ internal/quote    QuoteSource: Simulated(랜덤워크) | Polling(기준가만 외부에서)
```

| 레이어 | 파일 | 책임 |
| --- | --- | --- |
| 진입점 | `cmd/server/main.go` | 환경변수 7개 → `config`, 소스 선택, `http.Server` + SIGTERM 처리 |
| HTTP | `internal/httpapi/server.go`, `ws.go` | Go 1.22 ServeMux 경로 패턴(`GET /stream/{stockCode}`), SSE·WS 프레이밍 |
| 팬아웃 | `internal/hub/hub.go` | 종목별 시세 루프 생명주기, 구독·해제, 논블로킹 브로드캐스트 |
| 시세 원천 | `internal/quote/*.go` | `Tick` 계약, `QuoteSource` 인터페이스, 두 구현 |

테스트 함수는 52개다(`func Test` 기준). 패키지 3개에 고루 퍼져 있다.

## 2. 동시성 모델 — 종목당 고루틴 하나

`Hub` 의 상태는 뮤텍스 하나 뒤의 맵 하나다.

```go
type Hub struct {
    mu    sync.Mutex
    codes map[string]*codeState   // 종목 → {구독자 집합, 루프 취소 함수}
    ...
}
```

규칙은 세 줄로 정리된다.

1. 어떤 종목의 **첫 구독자**가 들어오면 `context.WithCancel` 로 시세 루프 고루틴을 하나 띄운다.
2. 구독자 하나는 버퍼 채널 하나다(기본 16칸). HTTP 요청 하나가 구독 하나다.
3. **마지막 구독자**가 나가면 루프를 `cancel()` 하고 맵에서 지운다.

그래서 종목이 $K$ 개 활성이고 접속이 $N$ 개면 고루틴 수는 대략 $K + N$ 이다. 사용자가 몇 명이든 종목당 시세 계산은 1초에 한 번이다. README 는 "접속·해제를 아무리 반복해도 고루틴이 새지 않는다"고 하고, `TestHub_NoGoroutineLeak` 가 그걸 지킨다.

### 느린 클라이언트: drop-oldest

```go
select {
case sub.ch <- tick:
default:                       // 버퍼가 가득 찼다
    select { case <-sub.ch: default: }   // 가장 오래된 틱을 버리고
    select { case sub.ch <- tick: default: } // 최신 틱을 넣는다
}
```

시세는 최신값만 의미가 있다. 느린 클라이언트를 기다리는 대신 **가장 오래된 틱을 버린다.** 브로드캐스터는 어떤 경우에도 막히지 않는다. 같은 판단이 SSE 계약에도 이어진다. 이 스트림은 `id:` 필드를 보내지 않는다. 그래서 재접속해도 놓친 틱을 다시 받지 않는다(레포 `docs/sse.md`). HTML 표준에서 `Last-Event-ID` 재개는 서버가 `id` 를 실어 보낼 때만 성립한다([WHATWG HTML §9.2](https://html.spec.whatwg.org/multipage/server-sent-events.html)). 따라서 `id` 를 안 보내는 것은 "재생 없음"을 명시적으로 선언하는 셈이다.

## 3. 이 서비스를 실제로 죽였던 경합 (8/19)

지금의 `broadcast` 는 **채널에 보내는 동안에도 락을 잡고 있다.** 처음부터 그랬던 건 아니다. 수정 커밋 `32ffbb05`(2026-08-19) 메시지가 경위를 그대로 남겨 두었다.

> 운영 파드가 실제로 이 경합으로 죽었다. `panic: send on closed channel` — `hub.broadcast`

예전 코드는 "느린 클라이언트가 팬아웃을 막지 못하게 하려고" 구독자 채널 목록을 스냅샷한 다음 락을 풀고 보냈다. 그 사이에 `unsubscribe` 가 락을 잡고 `close(sub.ch)` 를 하면, 브로드캐스터가 이미 닫힌 채널로 보내게 된다. Go 명세에서 이건 에러가 아니라 **런타임 패닉**이다("A send on a closed channel proceeds by causing a run-time panic" — [Go spec, Send statements](https://go.dev/ref/spec#Send_statements)). 프로세스가 죽으니 접속해 있던 다른 클라이언트도 전부 끊긴다. **한 명이 나간 일이 전원 장애가 된다.**

수정의 핵심은 커밋 메시지의 한 문장이다. *락을 풀어서 얻는 게 없었다.* 느린 클라이언트로부터의 보호는 이미 논블로킹 send(`select` + `default`)가 하고 있었다. 락 해제는 거기에 보탠 것 없이 정합성만 깼다. 그래서 전송 구간까지 같은 뮤텍스로 덮었고, `close` 도 그 뮤텍스 안에서만 일어나므로 경합 창이 아예 사라졌다.

비용도 커밋에 측정돼 있다(레포 내부 측정, 재현은 `go test -race` 의 회귀 테스트로 가능하다). 구독자 2,000명일 때 broadcast 1회가 126µs 다. 틱이 1초에 한 번이니 락 점유율은 이렇다.

$$
\frac{126\,\mu s}{1\,s} \approx 0.013\%
$$

회귀 테스트는 한 종목에 구독자 200명, 1ms 틱, 라운드마다 전원 동시 해제를 40번 반복한다. 수정 전 코드에서는 `-race` 가 `chansend` 와 `closechan` 줄을 정확히 짚었다고 한다. 이 버그를 찾은 것도 단위 테스트가 아니라 **동시 SSE 3,000 커넥션을 한꺼번에 끊는 부하 시험**이었다는 점을 기억해 둘 만하다.

## 4. `Tick` 계약 — 값이 진짜인지를 매 틱에 싣는다 (8/20)

```json
{"stockCode":"005930","price":70124.29,"ts":"2026-10-27T14:12:03.977Z","source":"SAMPLE"}
```

이 틱은 오늘 밤 운영 파드에서 직접 받은 것이다. `source` 필드는 다음 날 커밋 `2e292026` 에서 들어왔다. 이유는 이렇다. 틱은 랜덤워크로 만든 **합성값**인데, 프론트에 뜨던 `LIVE` 배지는 *SSE 연결 상태*만 뜻했다. 시세 화면에서는 그게 "실시세"로 읽혔다.

설계 판단이 세 개 있다.

- **스트림을 열 때 한 번 알리지 않고 매 틱에 싣는다.** 중간에 합류하거나 재연결한 소비자도 알 수 있어야 하기 때문이다.
- **어휘를 시세 REST API 의 `ValueSource`(SAMPLE/EXCHANGE)와 똑같이 맞췄다.** 같은 구분을 두 서비스가 다른 말로 하면 소비자는 추측하게 된다.
- **Polling 소스도 SAMPLE 이다.** 기준가만 외부에서 가져오고 그 위의 움직임은 여전히 랜덤워크다. EXCHANGE 를 달면 지어낸 숫자를 실시세라고 말하는 셈이 된다.

프론트(`LiveQuoteTicker.tsx`)는 SAMPLE 이면 '근사 샘플' 배지와 "투자 판단·계산에 쓰지 마세요" 문구를 띄운다. `source` 가 없는 옛 프레임도 SAMPLE 로 취급한다. 표기가 빠졌을 때 실시세처럼 보이는 쪽으로 기울면 안 되기 때문이다.

## 5. `QuoteSource` — 확장점은 깔끔하고, 구멍은 두 군데

```go
type QuoteSource interface {
    BasePrice(stockCode string, fallback float64) float64
    Name() string        // "어떤 구현인가" — 로그용
    ValueSource() string // "진짜인가" — 페이로드용
}
```

`Name()` 과 `ValueSource()` 를 나눈 것은 좋은 결정이다. 구현 이름은 서비스 밖으로 나갈 이유가 없고, 진위는 반드시 나가야 한다. 실시세 피드(KIS/KRX 웹소켓 등)를 붙일 때도 이 인터페이스 하나만 구현하면 되고, Hub·핸들러·클라이언트 계약은 그대로 둘 수 있다고 README 는 적고 있다.

**SimulatedSource** 는 `(seed XOR fnv64(종목코드))` 로 종목마다 난수기를 따로 둔다. 그래서 같은 시드면 같은 수열이 나와 테스트가 결정적이다. 한 틱의 움직임은 기준가 $b$ 의 ±1% 이고, 전체는 ±5% 밴드에 묶인다.

$$
p_{t+1} = \operatorname{clamp}\big(p_t + u\cdot 0.01\,b,\; 0.95\,b,\; 1.05\,b\big),\qquad u \sim \mathcal{U}(-1, 1)
$$

코드를 읽으며 확인한 구멍이 두 개 있다. 둘 다 지금 당장 사고는 아니고, 구조적으로 그렇다는 뜻이다.

1. **Polling 의 "60초마다 갱신"은 실제로는 루프가 새로 뜰 때만 일어난다.** `runQuoteLoop` 는 `BasePrice()` 를 루프 시작 시 **딱 한 번** 부른다. 그래서 `MARKET_STREAM_POLL_INTERVAL` 은 "구독자가 0이 됐다가 다시 생긴 경우"에만 의미가 있다. 누군가 화면을 계속 띄워 두면 기준가는 루프가 처음 뜬 시점 값으로 고정된다.
2. **Hub 는 종목을 지우지만 SimulatedSource 는 지우지 않는다.** `rngs`·`price`·`base` 맵에는 `delete` 가 한 군데도 없다. 고루틴은 새지 않는다. 다만 **한 번이라도 요청된 종목 코드마다 상태가 영원히 남는다.** 경로 파라미터 검증도 공백 제거 후 빈 문자열인지만 본다. 공개 스트림이 되는 순간, 임의 문자열을 바꿔 가며 부르면 맵이 계속 자란다.

## 6. graceful stop 이 언제나 10초를 꽉 채운다 — 로컬 재현

`main.go` 의 종료 순서는 다음과 같다.

```go
srv.Shutdown(ctx10s)   // 1) HTTP 서버를 닫고 연결이 유휴가 되길 기다린다
h.Shutdown()           // 2) 그 다음 Hub 를 닫아 구독 채널을 close 한다
```

`net/http` 문서는 `Shutdown` 이 "리스너를 닫고, 유휴 연결을 닫은 뒤, 연결이 유휴로 돌아오기를 **무기한 기다린다**"고 하고, 장기 연결은 호출자가 따로 알려야 한다며 `RegisterOnShutdown` 을 가리킨다([net/http Server.Shutdown](https://pkg.go.dev/net/http#Server.Shutdown)). SSE 핸들러는 Hub 채널이 닫히거나 요청 컨텍스트가 취소돼야 빠져나간다. 그런데 Hub 는 2)에서야 닫힌다. 그래서 **SSE 클라이언트가 하나라도 붙어 있으면 1)은 반드시 타임아웃이 난다.**

`origin/main` 을 `git archive` 로 뽑아 go1.26.2 로 빌드했다. 클라이언트 하나를 붙인 채 SIGTERM 을 보냈다.

```text
23:13:01.058  shutdown signal received
23:13:11.058  ERROR graceful shutdown failed  err="context deadline exceeded"
23:13:11.058  hub: shutdown complete
              → 종료까지 10.07s, 그동안 클라이언트는 틱을 계속 받았다
```

쿠버네티스 기본 `terminationGracePeriodSeconds` 는 30초라서 운영에서 강제 종료까지 가지는 않는다. 다만 롤아웃 때마다 파드가 10초씩 쓸데없이 버티고, 매번 ERROR 로그를 하나씩 남긴다. 고치는 방법은 한 줄이다. `srv.RegisterOnShutdown(h.Shutdown)` 로 Hub 닫기를 HTTP 종료 *시작* 시점에 걸면, 핸들러가 채널 close 를 보고 바로 빠져나간다.

같은 맥락에서 `/ws` 핸들러는 `InsecureSkipVerify: true` 로 Origin 검사를 끄고 TODO 를 달아 두었다. 게이트웨이가 `/ws/**` 를 노출하지 않으므로 지금은 클러스터 안에서만 닿는다. 또 의존성 `nhooyr.io/websocket` 은 pkg.go.dev 에서 deprecated 로 표시돼 있고 후속은 `github.com/coder/websocket` 이다([pkg.go.dev](https://pkg.go.dev/nhooyr.io/websocket)).

## 7. 운영에서 끊기는 곳 — 401 을 돌려주는 건 이 서비스가 아니다

여기까지는 코드 이야기였다. 이제 실제 클러스터(settlement-prod)를 본다. 2026-10-27 23:11 KST 실측이다.

| 확인 | 결과 |
| --- | --- |
| 파드 | `market-stream` 1/1 Running, 재시작 0, lemuel 노드(solomon 을 내린 뒤 옮겨 옴) |
| 사용량 | CPU 1m, 메모리 3Mi (요청 25m / 64Mi) |
| 이미지 | `main-95c29ab` — `origin/main` 과 이 디렉터리 diff 0. 위에서 읽은 코드가 곧 운영본이다 |
| 소스 | 로그 `"source":"simulated"`. 차트가 `MARKET_STREAM_SOURCE` 를 주지 않는다 |
| 클러스터 안에서 직접 | `curl http://market-stream:8110/stream/005930` → **1초 간격 틱 정상** |
| 공개 경로 | `https://settlement.lemuel.co.kr/api/market-stream/stream/005930` → **401 JSON** |

401 본문을 보면 Spring 의 에러 포맷이다. Go 서비스는 401 을 돌려주는 코드가 아예 없다. 경로를 따라가면 이유가 나온다.

- 레포의 `frontend/nginx.conf` 는 `/api/market-stream/` 를 **gateway-service** 로 보낸다. 레포 문서는 gateway 가 `RewritePath` 로 프리픽스를 벗겨 넘긴다고 설명한다.
- 하지만 **운영 클러스터에는 gateway 가 없다.** 그리고 운영 nginx 는 이미지에 구운 파일이 아니라 helm 차트의 ConfigMap 이 같은 경로를 `subPath` 로 덮어쓴 *두 번째 사본*이다.
- 그 사본에는 market-stream 전용 location 이 없다. 그래서 요청은 `^/(auth|api|...)(/|$)` catch-all 에 걸려 모놀리스 `settlement-app:8080` 으로 간다. 모놀리스는 그 경로를 인증이 필요한 미지 경로로 보고 401 을 낸다. 비슷하게 생긴 `^/api/market(/|$)` 규칙도 있지만 `market` 뒤가 `-` 라서 매칭되지 않는다.

**한 번은 길이 있었다.** helm-deploy 이력을 보면 9/24 05:30 `6e04a6e` 가 운영 nginx 를 "gateway 라우팅 표의 사본"으로 다시 쓰면서 `location ^~ /api/market-stream/ { proxy_pass http://market-stream:8110/; }` 를 넣었다. 그런데 같은 PR 에 finance-service 추가가 묶여 있었다. finance·query 가 prod 어댑터 빈이 없어 기동에 실패하자 08:30 에 **PR 통째로** 리버트됐다. 그날 16:37 finance 라우팅은 좁게 다시 들어왔지만(`b7e39c0`) 시세 스트림 한 줄은 돌아오지 않았다. git 이력상 운영 nginx 에 이 경로가 있었던 건 그 세 시간뿐이다.

로그도 같은 이야기를 한다. Hub 는 종목 루프를 띄울 때마다 INFO 로그 `hub: started quote loop` 를 남긴다. 그런데 오늘 13:35 UTC 기동 이후 로그는 기동 두 줄이 전부다. **구독자가 한 명도 없었다.**

### 왜 아무도 몰랐나

이 서비스는 이런 "조용한 고장"을 드러낼 수단을 스스로 갖고 있지 않다.

- `healthz` 는 프로세스가 살아 있는지만 본다. 경로가 끊겨도 초록불이다.
- `Hub.ActiveCodes()` · `SubscriberCount()` 주석에는 "테스트와 **메트릭**용"이라고 적혀 있다. 하지만 `/metrics` 엔드포인트는 없고, 차트에도 `metricsPath` 가 없다. "활성 종목 수 = 0"이 한 달 동안 이어져도 그걸 볼 그래프가 없었다.
- 레포 안의 게이트(`sse-nginx-gate.test.mjs`, `spa-fallback-gate.test.mjs`)는 **레포 안의 nginx 두 벌만** 검사한다. 운영 ConfigMap 사본에는 helm-deploy 주석이 직접 경고해 둔 것처럼 같은 검사가 닿지 않는다.

[오늘 앞서 쓴 18→6 통합 글]({% post_url 2026-10-27-settlement-18-to-6-the-consumers-nobody-listed %})의 결론과 같은 모양이다. 거기서는 *목록에 없던 소비자*가 조용히 멈춰 있었다. 여기서는 **목록에 있는 생산자가 소비자에게 닿지 못한 채** 조용히 돌고 있다. 둘 다 "각자 초록불"이었다.

## 8. 정리 — 고칠 것 다섯 개, 크기 순

| # | 내용 | 크기 |
| --- | --- | --- |
| 1 | 운영 nginx ConfigMap 에 `location ^~ /api/market-stream/` 한 블록(`proxy_pass http://market-stream:8110/;` + `proxy_buffering off` + `read_timeout 3600s`). 화면이 처음으로 살아난다 | 소 — helm-deploy 한 곳 |
| 2 | `srv.RegisterOnShutdown(h.Shutdown)` — 종료 10초 대기와 ERROR 로그 제거 | 한 줄 |
| 3 | 구독자·활성 종목 게이지를 `/metrics` 로 노출하고 차트에 `metricsPath` 를 단다. "0명이 30일"을 경보로 만든다 | 소 |
| 4 | 종목 코드 형식 검증(6자리 숫자 등)과 SimulatedSource 상태를 Hub 해제 시 함께 정리 | 소 |
| 5 | Polling 기준가 갱신을 루프 안으로(틱 N 회마다 `BasePrice` 재호출). `nhooyr` → `coder/websocket` | 중 |

1번은 공개 표면을 여는 변경이라 내 판단으로 넣지 않았다. 이 글은 구조 분석까지다. 그리고 1번을 넣는 순간 4번이 공개 표면이 된다. 순서를 지키는 게 좋다. 4번 → 1번이다.

마지막으로 숫자 하나가 눈에 걸린다. 같은 시각 같은 종목(005930)을 보면, 시세 REST 의 최신 종가는 10/23 기준 **215,500원 (EXCHANGE)** 이다. 스트림은 **약 70,000원 (SAMPLE)** 이다. 시뮬레이션 기준가가 모든 종목에 `defaultBasePrice = 70000` 으로 고정이기 때문이다. SAMPLE 표기가 있으니 거짓말은 아니다. 하지만 1번으로 길이 열리면 사용자가 처음 보는 숫자가 이것이다. 그러면 Polling 으로 바꿀지(차트에 `MARKET_BASE_URL` 은 이미 대비돼 있다) 함께 정해야 한다.

## References

- WHATWG, *HTML Living Standard — §9.2 Server-sent events* (event stream 형식, `Last-Event-ID`). <https://html.spec.whatwg.org/multipage/server-sent-events.html>
- The Go Authors, *The Go Programming Language Specification — Send statements / Close* ("A send on a closed channel proceeds by causing a run-time panic"). <https://go.dev/ref/spec#Send_statements>
- The Go Authors, *net/http — Server.Shutdown, Server.RegisterOnShutdown* (go1.26.2 `src/net/http/server.go` 주석으로 대조). <https://pkg.go.dev/net/http#Server.Shutdown>
- *nhooyr.io/websocket v1.8.17* — deprecated, `github.com/coder/websocket` 로 이전. <https://pkg.go.dev/nhooyr.io/websocket>
- Kubernetes Docs, *Pod Lifecycle — Termination of Pods* (`terminationGracePeriodSeconds` 기본 30s). <https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/#pod-termination>
- 비공개 레포 `settlement` — `market-stream-service/` (origin/main 448d9860), 커밋 `32ffbb05`(broadcast 경합 수정, 8/19)·`2e292026`(Tick source, 8/20), `docs/sse.md`, `gateway-service/src/main/resources/application.yml`, `frontend/src/components/LiveQuoteTicker.tsx`
- helm-deploy — `charts/polyglot-services/values.yaml`, 커밋 `6e04a6e`(9/24 05:30, 시세 경로 추가)·`75a2459`(08:30, PR 통째 리버트)·`b7e39c0`(16:37, finance 만 재도입)
- 실측: settlement-prod 파드·로그·클러스터 내부 curl, 공개 경로 curl (2026-10-27 23:11 KST), 로컬 graceful stop 재현 (go1.26.2, 10.07s)
