---
layout: post
title: "Claude Code 를 Opik 으로 실측하다 — 익스포터는 로컬 머신 밖으로 나가지 않았다"
date: 2026-09-04 07:40:00 +0900
categories: [AI, Observability]
tags: [Opik, ClaudeCode, OpenTelemetry, OTLP, LLMObservability, HomeLab, K3s, SelfHosting]
---

# 에이전트의 비용을 "추정" 말고 "수신" 하기

홈랩에 [Opik 을 올린 게 7월](/2026/07/25/ai-repo-radar-and-opik/)이었다. 올려는 놨는데 정작
**내가 제일 많이 굴리는 LLM 워크로드 — Claude Code 자신 — 은 거기에 한 줄도 안 들어가 있었다.**
[에이전트도 워크로드다](/2026/07/22/homelab-monitoring-claude-telemetry/)라고 써놓고, 그 워크로드의
트레이스만 비어 있던 셈이다.

이 글은 그 구멍을 메운 기록이다. 그리고 메우는 과정에서 **공식 문서 어디에도 안 적힌 동작 하나**를
통제 실험으로 잡아낸 이야기이기도 하다. 결론부터 적으면 이렇다.

> Claude Code 의 OTLP 익스포터는 **로컬 머신 주소로만** 내보낸다.
> 다른 호스트의 주소를 주면 — 그 주소가 `curl` 로 멀쩡히 200 이 나는 주소여도 —
> **요청이 아예 나가지 않는다. 에러도 없이.**

---

## 1. 먼저 안 해도 되는 것: OTEL Collector

Opik 앞에 OpenTelemetry Collector 를 세우려던 시도가 하나 있었다. 4317(gRPC) 포트를 붙잡으려다
다른 프로세스와 충돌했고, 그 충돌을 푸는 데 시간이 갔다.

그런데 **그 작업 자체가 필요 없는 것이었다.** Opik 백엔드에는 OTLP 수신구가 내장돼 있고,
공식 문서는 전송 방식을 이렇게 못박는다.

> "OpenTelemetry integration in Opik currently supports HTTP transport."
> — [Opik OpenTelemetry Integration](https://www.comet.com/docs/opik/tracing/opentelemetry/overview)

HTTP 전용이면 **gRPC 포트 4317 은 애초에 등장할 이유가 없다.** 충돌을 푼 게 아니라,
만들지 말았어야 할 문제를 푼 것이었다. 관측 배선에서 Collector 는 기본값이 아니라 *선택지*다 —
백엔드가 OTLP 를 직접 받으면 한 겹 덜어내는 게 맞다.

주소와 헤더도 같은 문서에 있다. 베이스 엔드포인트는 `/api/v1/private/otel`, 헤더는
`projectName` 과 `Comet-Workspace`. 셀프호스팅에서 내가 실측한 것 두 가지를 덧붙인다.

- **API 는 프론트 nginx(5173) 경유로만 열린다.** 백엔드 컨테이너 포트로 직결하면 404 다.
  즉 트레이스 엔드포인트는 `http://<opik>:5173/api/v1/private/otel/v1/traces`.
- **`projectName` 에 없는 이름을 주면 프로젝트가 자동 생성된다.** 미리 만들 필요가 없다.

---

## 2. 트레이스는 기본으로 안 켜진다

Claude Code 의 텔레메트리는 메트릭·로그(이벤트)·트레이스 세 갈래인데, **트레이스는 베타라
플래그를 따로 켜야 한다.** 공식 문서의 환경변수를 그대로 쓴다.

```bash
CLAUDE_CODE_ENABLE_TELEMETRY=1
CLAUDE_CODE_ENHANCED_TELEMETRY_BETA=1     # 트레이스는 이게 있어야 켜진다
OTEL_TRACES_EXPORTER=otlp
OTEL_EXPORTER_OTLP_TRACES_PROTOCOL=http/protobuf
OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=...
OTEL_EXPORTER_OTLP_TRACES_HEADERS=Comet-Workspace=default,projectName=claude-code
```

여기서 중요한 건 **시그널별(per-signal) 변수를 쓴다**는 점이다. 우리 홈랩은 메트릭·로그를 이미
다른 수집기로 보내고 있었다. `OTEL_EXPORTER_OTLP_ENDPOINT`(전 시그널 공통)를 Opik 으로
돌려버리면 멀쩡히 돌던 메트릭 파이프라인이 통째로 딸려간다. `_TRACES_` 접두 변수는
공통 설정을 *덮어쓰는* 용도로 OTLP 사양에 정의돼 있다 —
[OTLP Exporter Configuration](https://opentelemetry.io/docs/specs/otel/protocol/exporter/).
그래서 트레이스만 갈라 보냈다.

---

## 3. 그리고 아무 일도 일어나지 않았다

설정을 넣고 돌렸다. 에러 없음. 종료 코드 0. Opik 에는 아무것도 없음.

이럴 때 제일 먼저 의심하게 되는 건 수신 쪽이다. "Opik 이 protobuf 를 거부하나?"
"헤더가 틀렸나?" "인증인가?" 전부 아니었다. 수신 쪽은 **세 가지 독립적인 방법으로** 멀쩡했다.

1. Opik 호스트 안에서 `curl` 로 OTLP 페이로드 → 200, 스팬 저장됨
2. **맥에서 LAN 너머로** 같은 `curl` → 200, 스팬 저장됨
3. Claude 가 실제로 뱉은 protobuf 바이트를 파이썬으로 중계 → 200, 스팬 저장됨

3번이 결정적이다. **같은 바이트가, 같은 주소로, 파이썬을 한 번 거치면 들어간다.**
그러면 문제는 수신이 아니라 송신이다.

증거를 확실히 하려고 nginx access log 를 봤다. Claude 를 직접 돌렸을 때
`OTel-OTLP-Exporter-JavaScript` User-Agent 의 요청이 **한 건도 안 찍혀 있었다.**
거부당한 게 아니라 *도착한 적이 없다.*

---

## 4. 통제 실험 — 변수는 주소 하나만

여기서 한 번 틀렸다. 처음엔 "loopback 으로만 나간다" 고 결론 냈는데, 그 근거였던 원격 캐처 실험이
사실은 **캐처가 아예 안 떠 있던 실험**이었다. 원격에서 `pkill -f catcher_all.py` 를 돌렸는데
그 패턴이 *자기 자신의 명령줄* 과 매치돼서 셸이 스스로를 죽였다. 그래서 "0 건 수신" 이 나온 것이지,
익스포터가 안 보낸 게 아니었다. 도달성 확인을 안 한 실험은 실험이 아니다.

다시 짰다. **캐처 프로세스는 하나, 포트도 하나(`0.0.0.0:4999`), 바꾸는 건 주소뿐.**
설정은 `claude --settings '{"env":{...}}'` 로 주입해 셸 환경변수 우선순위 문제를 배제했고,
원격 캐처는 **먼저 `curl` 로 200 을 받아 도달 가능함을 증명한 뒤에** 측정했다.

| 엔드포인트 주소 | 무엇인가 | `curl` 도달성 | 익스포터 수신 |
|---|---|---|---|
| `127.0.0.1:4999` | loopback | — | **1 건** |
| `192.168.219.100:4999` | 맥 *자기* LAN IP | — | **1 건** |
| `192.168.219.111:4999` | louise (다른 호스트) | **200** | **0 건** |
| `192.168.219.101:5173` | Opik 본체 | **200** | **0 건** |

두 번째 줄이 핵심이다. **자기 LAN IP 는 통한다.** 그러니 "loopback 전용" 이 아니다.
자기 LAN IP 로 가는 패킷은 OS 가 루프백으로 돌리므로, 실제 경계는 이쪽이다 —
**로컬 머신을 벗어나면 안 나간다.**

공정하게 덧붙이면, 나는 이 동작의 *원인* 코드를 못 봤다. 프록시 환경변수(`HTTP_PROXY` 등)는
설정돼 있지 않은 것을 확인했고, 같은 머신의 `curl` 은 나가므로 방화벽·라우팅 문제도 아니다.
공식 모니터링 문서에도 이런 제한은 **적혀 있지 않다** — 예시가 전부 `localhost` 일 뿐이다.
그래서 이건 문서화된 사양이 아니라 **2026-09-04 내 환경에서의 재현된 실측**으로만 주장한다.

실무적으로 중요한 건 원인보다 성질이다. 이 실패는 **조용하다.** 로그도, 종료 코드도,
경고도 없다. 수신 쪽 로그를 직접 안 보면 "Opik 설정이 틀렸나" 를 며칠 뒤질 수 있다.
관측 배선을 깔 때 *"보낸 쪽이 실제로 보냈는지"* 를 먼저 확인해야 하는 이유다.

---

## 5. 터널, 그런데 왜 옆 노드를 경유하나

로컬 머신 주소로만 나간다면 답은 하나다 — 로컬에 포트를 하나 만들어 준다.
메트릭·로그가 이미 그렇게 돌고 있었으니 같은 방식이면 된다.

그런데 Opik 이 떠 있는 노드로는 `ssh -L` 이 안 됐다. 붙자마자 connection reset.
원인은 그 노드의 sshd 하드닝이었다.

```
# /etc/ssh/sshd_config.d/hardening.conf
AllowTcpForwarding no
```

`AllowTcpForwarding no` 는 **그 서버를 경유하는 TCP 포워딩 자체를 금지**한다
([sshd_config(5)](https://man.openbsd.org/sshd_config#AllowTcpForwarding)).
보안 설정으로는 맞는 값이라 풀고 싶지 않았다. 그래서 **포워딩이 열려 있는 옆 노드를 경유**해
목적지만 Opik 노드로 잡았다.

```
127.0.0.1:4319  ──ssh──▶  louise  ──LAN──▶  opik-node:5173
```

터널의 목적지는 SSH 서버가 아니어도 된다. 포워딩을 허용하는 아무 노드나 *중계*로 쓰면 된다.
launchd 로 상주시키고(`KeepAlive`), Claude 쪽 엔드포인트는 `http://127.0.0.1:4319/...` 로 고정했다.

---

## 6. 그래서 뭐가 보이나

배선 후 새 세션의 스팬이 들어온다. 계층은 이렇다.

```
claude_code.interaction              ← 사용자 턴 하나
├── claude_code.llm_request          ← 모델 호출
├── claude_code.tool                 ← 도구 실행
│   ├── claude_code.tool.blocked_on_user
│   └── claude_code.tool.execution
└── claude_code.hook
```

`llm_request` 스팬에 모델명과 토큰이 실려 온다. 내가 실측한 요청 한 건의 값은 이랬다 —
`claude-opus-5`, `prompt_tokens` 2, `completion_tokens` 3, 그리고
`cache_creation_input_tokens` **37,505** / `cache_read_input_tokens` **18,713**.

이 숫자가 이 배선의 값어치를 그대로 보여준다. **"질문 두 토큰, 답 세 토큰" 짜리 요청의 실제 비용은
캐시 쪽에 있다.** 프롬프트 캐시 생성·조회 토큰을 안 보면 비용 모델이 통째로 틀린다.
Opik 은 이 값들로 비용을 자체 계산해 붙여준다.

한 가지 분명히 해둘 것: 이건 **트레이스**다. `claude_code.cost.usage` 같은 *메트릭 시계열*은
Opik 으로 가지 않는다 — 그건 계속 기존 수집기 몫이다. 둘은 대체재가 아니라 **다른 면**이다.
트레이스는 "이 턴에서 무슨 일이 있었나", 메트릭은 "시간에 따라 얼마나 쓰나" 를 답한다.

또 하나, 이 설정은 **새로 뜨는 세션부터 적용된다.** 이미 떠 있는 세션은 기동 시점의 환경을
들고 있어서, 재시작 전까지는 트레이스를 안 보낸다.

---

## 마무리 — 조용한 실패를 잡는 법

이 작업에서 배선 자체는 어렵지 않았다. 시간을 다 먹은 건 **아무 에러도 없이 아무 일도 안 일어나는
구간**이었고, 그걸 가른 건 딱 두 가지였다.

1. **수신 쪽 로그를 진실의 기준으로 삼는다.** "보냈다" 는 송신 쪽 침묵으로 증명되지 않는다.
   nginx access log 에 요청이 없다는 사실 하나가 문제의 절반을 잘라냈다.
2. **실험은 도달성부터 증명한다.** 내 첫 결론이 틀렸던 이유는 캐처가 안 떠 있었기 때문이다.
   `curl` 로 200 을 먼저 받아두지 않았다면, 두 번째 결론도 똑같이 틀렸을 것이다.

관측 도구를 붙이는 일은 원래 이런 종류의 일이다 — 도구가 뭘 보여주느냐 이전에,
**데이터가 실제로 거기까지 갔는가**를 매번 실측해야 한다.

---

## References

- [Claude Code — Monitoring usage (공식 문서)](https://docs.claude.com/en/docs/claude-code/monitoring-usage) — 텔레메트리 환경변수, 베타 플래그, 스팬 계층
- [Opik — OpenTelemetry Integration (공식 문서)](https://www.comet.com/docs/opik/tracing/opentelemetry/overview) — HTTP 전송 전용, `/api/v1/private/otel` 엔드포인트, `projectName`·`Comet-Workspace` 헤더
- [OpenTelemetry — OTLP Exporter Configuration (사양)](https://opentelemetry.io/docs/specs/otel/protocol/exporter/) — 시그널별 엔드포인트 변수의 우선순위
- [OpenBSD `sshd_config(5)` — AllowTcpForwarding](https://man.openbsd.org/sshd_config#AllowTcpForwarding) — 포워딩 금지 옵션의 정의

> 본문의 측정값(표·토큰 수치·404/200 응답)은 2026-09-04 내 홈랩 환경에서 직접 실측한 것이다.
> 익스포터의 "로컬 머신 전용" 동작은 **공식 문서에 명시된 사양이 아니라 관측된 동작**이며,
> 버전·플랫폼에 따라 다를 수 있다.
