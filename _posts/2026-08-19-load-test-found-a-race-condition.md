---
layout: post
title: "부하 테스트를 안 했다고 적었다 — 그래서 돌렸더니 경합 버그가 나왔다"
date: 2026-08-19 00:05:00 +0900
categories: [Backend, Kubernetes]
tags: [Go, SSE, 부하테스트, 동시성, Kubernetes, OOMKilled, settlement]
---

이력서 끝에 "검증 노트"를 붙이는 습관이 있다. 근거가 있는 수치와 없는 수치를 갈라 적는 칸이다. 거기에 이렇게 썼다.

> 부하 테스트는 수행하지 않았습니다. 따라서 처리량·지연시간 수치는 주장하지 않습니다.

정직하게 쓴 문장이었는데, 읽는 쪽에서 당연한 반문이 돌아왔다. **그럼 지금 해보면 되지 않나.**

맞는 말이라 돌렸다. 대상은 운영 중인 `settlement` 의 `market-stream-service` — Go 로 짠 SSE/WebSocket 시세 스트리밍 서버다. 결과로 처리량 수치를 얻었고, 덤으로 **찾을 생각이 없던 동시성 버그를 하나 밟았다.** 이 글은 그 과정이다.

## 무엇을 재지 않으려고 애썼는가

부하 테스트에서 가장 흔한 실패는 "엉뚱한 걸 재고 그게 서버 성능이라고 믿는 것"이다. 이번엔 세 가지를 미리 배제했다.

**첫째, 네트워크 경로.** 내 맥에서 클러스터로는 SSH 터널(`127.0.0.1:16443`)을 타고 들어간다. 여기서 부하를 걸면 재는 건 서버가 아니라 터널이다. 그래서 **부하 생성기를 클러스터 안에 파드로 띄워** ClusterIP 를 직접 때렸다.

**둘째, 상류 증폭.** 스트리밍 서버가 시세를 어디서 가져오는지 먼저 코드로 확인했다. `Hub` 는 종목 코드당 소스 고루틴을 정확히 하나만 돌린다.

```go
cs, ok := h.codes[stockCode]
if !ok {
    // ... 이 종목의 첫 구독자일 때만 루프를 띄운다
    go h.runQuoteLoop(ctx, stockCode)
}
```

즉 같은 종목 구독자를 100 명으로 늘리든 5,000 명으로 늘리든 **상류 호출량은 그대로다.** 게다가 배포된 파드에는 환경변수가 하나도 안 걸려 있어 소스가 기본값인 `simulated` 로 뜬다 — 외부 호출 자체가 없다. DB·Kafka·`market-service` 로 부하가 번질 경로가 없다는 걸 확인하고 시작했다.

**셋째, 쓰기 경로.** 읽기 전용 엔드포인트만 건드렸다. 결제 웹훅(Kafka 발행)이나 주문 생성은 애초에 대상에서 뺐다.

### distroless 이미지에는 셸이 없다

처음엔 게으르게 `kubectl exec` 로 대상 파드 안에서 `wget` 을 때려보려 했다. 두 번 다 이렇게 죽었다.

```
exec: "wget": executable file not found in $PATH
exec: "timeout": executable file not found in $PATH
```

Go 바이너리를 distroless 로 말아서 셸도 유틸리티도 없다. 보안상 옳은 선택이고, 그래서 진단 도구를 대상 안에 넣을 수 없다. 결과적으로는 잘된 일이었다 — 별도 부하 파드를 띄우는 쪽이 측정 위생상으로도 맞다.

부하 생성기는 `python:3.13-slim` 파드에 표준 라이브러리 `asyncio` 만으로 짰다. pip 설치가 필요 없으니 폐쇄망에서도 그대로 돈다. 커넥션마다 raw HTTP GET 을 열고 `text/event-stream`[^sse] 을 읽으며 연결 성공 여부, 첫 이벤트까지 걸린 시간, 수신 이벤트 수를 기록한다.

## 결과

조건은 **replica 1개, 메모리 limit 128Mi, tick 1초**다. 동시 SSE 커넥션을 단계적으로 올렸다.

| 동시 커넥션 | 연결 성공률 |     처리량 |           파드 메모리 | 이벤트 드롭 |
| ----------: | ----------: | ---------: | --------------------: | ----------: |
|         100 |        100% |  87.6 ev/s |                  10Mi |           0 |
|         500 |        100% |   433 ev/s |                  17Mi |           0 |
|       2,000 |        100% | 1,567 ev/s |                  66Mi |           0 |
|       3,000 |           — |          — |                 116Mi |           — |
|       5,000 |       69.4% |          — | 124Mi → **OOMKilled** |           — |

2,000 커넥션 구간의 지연시간은 연결 p50 16.5ms / p95 54.8ms, 첫 이벤트 도착 p95 952ms 였다. 첫 이벤트가 1초 가까이 걸리는 건 지연이 아니라 설계다 — 접속 시점 스냅샷을 쏘지 않고 다음 tick 경계까지 기다리기 때문이다. tick 이 1초니 최대 1초. 이건 성능 문제가 아니라 **접속 직후 화면이 1초간 비어 있다**는 UX 문제로 읽어야 한다.

드롭이 전 구간 0인 것도 의미가 있다. `broadcast` 는 구독자 버퍼(기본 16)가 차면 가장 오래된 tick 을 버리고 최신 것을 넣는다. 실시간 시세에서는 밀린 값보다 최신 값이 낫다는 판단이다. 2,000 커넥션까지 그 폴백이 한 번도 발동하지 않았다.

## 발견 1 — 병목은 CPU 가 아니라 메모리였다

2,000 커넥션에서 CPU 는 **75m** 밖에 안 썼다. 코어 하나의 8% 다. 반면 메모리는 10Mi → 66Mi 로 올랐다.

커넥션당 약 **30KB**. 이 기울기를 그대로 밀면 128Mi limit 에서 베이스라인을 뺀 118Mi ÷ 30KB ≈ 4,000 커넥션이 이론 한계고, 실제 붕괴점은 3,470 커넥션이었다. 이론과 실측이 어긋나지 않는다.

여기서 나온 실무적 결론은 단순하다. **이 서비스의 용량은 CPU 로 산정하면 안 된다.** limit 128Mi 는 어떤 근거로 잡힌 값이 아니라 그냥 기본값처럼 박혀 있었고, 그 숫자가 곧 "동시 접속 2,000 명"이라는 뜻이라는 걸 아무도 계산해 본 적이 없었다. 1만 동시 접속을 받으려면 limit 를 512Mi 로 올리거나 replica 를 늘려야 한다.

한계를 넘겼을 때는 컨테이너가 exit code 137 로 종료되고 `reason: OOMKilled` 이 찍힌다.[^k8soom] 실제 기록은 이랬다.

```json
{
  "terminated": {
    "exitCode": 137,
    "reason": "OOMKilled",
    "finishedAt": "2026-08-18T14:49:57Z"
  }
}
```

참고로 이 서비스는 `GOMEMLIMIT` 을 설정하지 않았다. Go 런타임은 기본적으로 cgroup 메모리 한계를 모르기 때문에, 한계 근처에서 GC 를 더 세게 돌지 않고 그냥 커널에게 죽는다. GOMEMLIMIT 을 컨테이너 limit 보다 약간 낮게 잡으면 GC 가 먼저 개입해 죽는 대신 느려지는 쪽으로 완만하게 저하시킬 수 있다.[^gcguide]

## 발견 2 — 진짜 소득은 여기 있었다

3,000 커넥션 시험 중 메모리 가드가 발동해서 **3,000 개 클라이언트를 한꺼번에 끊었다.** 그러자 서버가 OOM 이 아니라 패닉으로 죽었다.

```
panic: send on closed channel

goroutine 53 [running]:
...market-stream-service/internal/hub.(*Hub).broadcast(...)
        internal/hub/hub.go:179 +0x2d4
...market-stream-service/internal/hub.(*Hub).runQuoteLoop(...)
        internal/hub/hub.go:155 +0x1c7
```

원인은 코드를 보면 바로 보인다. `broadcast` 는 이렇게 생겼다.

```go
func (h *Hub) broadcast(stockCode string, tick quote.Tick) {
	h.mu.Lock()
	cs, ok := h.codes[stockCode]
	// ...
	// Snapshot subscriber channels so we can release the lock before sending.
	chans := make([]chan quote.Tick, 0, len(cs.subs))
	for sub := range cs.subs {
		chans = append(chans, sub.ch)
	}
	h.mu.Unlock()          // ← 175행: 여기서 락을 놓는다

	for _, ch := range chans {
		select {
		case ch <- tick:   // ← 179행: 패닉 지점
		default:
			// ...
		}
	}
}
```

주석이 의도를 정확히 밝히고 있다. "느린 클라이언트가 브로드캐스터나 다른 구독자를 막지 못하게" 하려고 **일부러** 락을 놓고 전송한다. 락을 쥔 채로 보내면 구독자 하나가 안 읽을 때 전체 팬아웃이 멈추니까, 그 자체로는 타당한 판단이다.

문제는 그 사이에 `unsubscribe` 가 끼어들 수 있다는 것이다.

```go
delete(cs.subs, sub)   // 130행
close(sub.ch)          // 131행
```

`broadcast` 가 175행에서 락을 놓은 뒤 179행에서 보내기까지의 창에, `unsubscribe` 가 락을 잡고 채널을 닫아버리면 — 이미 스냅샷에 담긴 그 채널로 전송이 들어간다. Go 명세는 이 경우를 명확히 규정한다.

> Sending to or closing a closed channel causes a run-time panic.[^spec]

구조적으로 말하면 **채널을 닫는 주체가 잘못됐다.** Go 의 채널 관례는 보내는 쪽이 닫는 것이다 — 공식 파이프라인 문서의 예제도 전부 송신 스테이지가 `close(out)` 을 호출한다.[^pipelines] "더 보낼 값이 없다"는 사실은 송신자만 알 수 있기 때문이다.[^spec] 그런데 여기서는 **수신측 경로인 `unsubscribe` 가 채널을 닫는다.** 송신자(`runQuoteLoop`)는 그 사실을 알 방법이 없다. 락 밖으로 나오는 순간 스냅샷은 낡은 정보가 된다.

### 왜 지금까지 안 터졌나

창이 좁기 때문이다. `broadcast` 가 락을 놓고 나서 실제 send 까지는 나노초 단위고, 그 안에 하필 다른 고루틴이 unsubscribe 를 완주해야 한다. 구독자가 몇 명일 때는 사실상 안 걸린다.

증거도 있다. 이 파드는 **2일 22시간 동안 재시작이 0회**였다. 평소 부하에서는 멀쩡히 돈다는 뜻이다. 3,000 개를 동시에 끊으니까 그제서야 나왔다.

그래서 이건 코드 리뷰로 못 잡는 종류의 버그다. 로직이 틀린 게 아니라 **타이밍이 틀렸고**, 타이밍은 부하를 걸어야 드러난다. 터졌을 때의 대가는 작지 않다 — 프로세스가 죽으면 그 순간 붙어 있던 스트리밍 클라이언트가 **전원** 끊긴다. 한 명의 disconnect 가 전체 가용성 사고로 번지는 구조다.

## 이 측정의 한계

수치를 주장했으니 어디까지 믿을 수 있는지도 적어야 한다.

**메모리 샘플링 해상도가 15초다.** 이 클러스터의 metrics-server 는 `--metric-resolution=15s` 로 떠 있다(직접 확인). 그래서 3,000 커넥션 구간에서 판독값이 7Mi → 116Mi 로 한 번에 튀었다. 실제로는 그 사이 어딘가를 연속으로 지나갔을 텐데 나는 그 궤적을 못 봤다. 표의 메모리 값은 **구간 최대치가 아니라 15초 격자에 걸린 샘플**이다.

**부하 생성기가 단일 프로세스다.** 파이썬 `asyncio` 는 단일 스레드라, 커넥션 수가 커지면 클라이언트가 먼저 포화할 수 있다. 5,000 구간에서 처리량이 482 ev/s 로 주저앉은 걸 서버 한계로 읽으면 안 된다 — 그 구간은 서버가 OOMKill 로 죽어서 나온 숫자다. **2,000 까지의 수치만 서버 성능으로 인용할 수 있다고 본다.**

**소스가 simulated 다.** 실제 시세 API 를 폴링하는 모드로는 안 재봤다. 그 모드에서는 상류 지연과 실패가 새 변수로 들어온다.

**단일 종목 팬아웃만 쟀다.** 종목 코드를 여러 개로 늘리면 소스 고루틴이 종목 수만큼 늘어나므로 메모리 기울기가 달라진다.

## 운영에 준 피해

숨길 일이 아니라 적는다. 테스트 도중 `market-stream` 이 **2회 재시작**했다. 1회는 OOMKill, 1회는 위 패닉이다. 각각 2초 안에 자동 복구됐고 다른 파드는 영향이 없었다. 읽기 전용 스트리밍이라 데이터 정합성 영향은 없다.

사전에 "에러가 보이면 즉시 중단" 이라는 원칙을 세우고 들어갔는데, 결과적으로 그 원칙은 절반만 지켜졌다. 메모리 가드는 15초 해상도 때문에 늦게 발동했고, 발동 자체가 대량 disconnect 를 만들어 패닉을 유발했다. **가드가 사고를 막은 게 아니라 다른 사고를 일으켰다.** 다음에 같은 걸 한다면 부하 파드 쪽에서 커넥션을 계단식으로 줄이는 램프다운을 넣어야 한다.

## 안 고쳤다

이 채널에서는 settlement 코드 수정이 금지돼 있어서 버그는 보고만 하고 손대지 않았다. 방향만 적어두면, 고칠 길은 대략 셋이다.

1. **`unsubscribe` 에서 `close` 를 없앤다.** 구독 종료는 구독자 쪽 컨텍스트 취소로 알리고 채널은 GC 에 맡긴다. 관례에 맞고 변경 폭도 작다.
2. **송신 구간까지 락으로 덮는다.** `RWMutex` 로 바꿔 broadcast 를 `RLock` 아래 두고 `close` 는 `Lock` 아래 둔다. 다만 논블로킹 send 라 실제 홀드 타임은 짧지만, 원 주석이 피하려던 결합이 일부 돌아온다.
3. **구독자별 종료 플래그를 send 와 같은 락으로 보호한다.**

어느 쪽이든 검증은 `go test -race` 로 대량 subscribe/unsubscribe 를 돌리는 테스트가 같이 들어가야 한다. 이번처럼 운영 파드를 죽여서 발견하는 건 한 번이면 충분하다.

## 남는 것

이력서에 "부하 테스트 미수행"이라고 적었을 때 나는 그게 성실함의 표시라고 생각했다. 하루 부하를 걸어보니 그건 **성실함이 아니라 공백**이었다. 안 해봤으니 용량을 몰랐고, 안 해봤으니 2일 넘게 조용히 살아 있던 경합 버그도 몰랐다.

이제 검증 노트는 이렇게 바뀐다.

> 동시 2,000 SSE 커넥션에서 1,567 events/s, 단일 파드 66Mi, 이벤트 드롭 0. 붕괴점 약 3,500 커넥션(메모리 한계). 부하 시험 중 `Hub.broadcast` 의 send-on-closed-channel 경합을 발견.

수치보다 마지막 문장이 더 마음에 든다.

## References

[^spec]: The Go Programming Language Specification, "Close" — `close(c)` 의 의미와 닫힌 채널 전송 시 런타임 패닉 규정. <https://go.dev/ref/spec#Close>

[^pipelines]: The Go Blog, "Go Concurrency Patterns: Pipelines and cancellation" — 파이프라인 각 스테이지에서 **송신 측**이 출력 채널을 닫는 패턴. <https://go.dev/blog/pipelines>

[^k8soom]: Kubernetes Documentation, "Assign Memory Resources to Containers and Pods" — 컨테이너가 메모리 limit 을 초과하면 종료되고 `reason: OOMKilled` 로 기록된다. <https://kubernetes.io/docs/tasks/configure-pod-container/assign-memory-resource/>

[^gcguide]: The Go Programming Language, "A Guide to the Go Garbage Collector" — 메모리 한계는 `GOMEMLIMIT` 으로 설정한다. <https://go.dev/doc/gc-guide>

[^sse]: WHATWG HTML Standard, "Server-sent events" — `text/event-stream` 미디어 타입과 이벤트 스트림 형식. <https://html.spec.whatwg.org/multipage/server-sent-events.html>

측정 수치(처리량·지연시간·메모리·재시작 기록)는 모두 본인이 자체 K3s 클러스터에서 직접 실행한 결과이며, 제3자 검증은 받지 않았습니다. metrics-server 해상도 15초는 해당 클러스터 `metrics-server` 배포의 `--metric-resolution` 인자에서 확인했습니다.
