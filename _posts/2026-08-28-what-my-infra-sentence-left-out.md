---
layout: post
title: "내 인프라를 한 문단으로 소개하고, 그 문단을 전부 재봤다"
date: 2026-08-28 19:14:27 +0900
categories: [infrastructure]
tags: [kubernetes, observability, kafka, tempo, sops, cloudflare-tunnel, verification]
---

홈랩 클러스터를 남에게 소개할 때 쓰는 문단이 있다.

> 관측은 Prometheus · Grafana · Tempo, 로그는 fluent-bit → Elasticsearch. 메시징은 Strimzi Kafka 4.2.0(KRaft dual-role)에 업무 토픽 47개와 DLT 17개. 시크릿은 SOPS + age 로 암호화해서 커밋하니 리포에 평문이 없고, 밖으로 나가는 트래픽은 포트포워딩 없이 Cloudflare Tunnel 만 지납니다.

오늘 이 문단의 모든 명사를 클러스터에 대고 하나씩 재봤다. **거짓은 없었다.** 그런데 절반은 문장이 들리는 것보다 **짧은 거리에 대해서만** 참이었다.

## 정확했던 것

먼저 맞은 것부터. 숫자가 정확히 맞는다.

| 주장 | 실측 |
|---|---|
| Strimzi Kafka 4.2.0 | `.spec.kafka.version: 4.2.0`, 오퍼레이터 0.51.0 |
| KRaft dual-role | KafkaNodePool `roles: [controller, broker]` |
| 업무 토픽 47개 | 브로커 총 65 − 내부 1 − DLT 17 = **47** |
| DLT 17개 | `.DLT` 접미사 토픽 **17개** |
| 리포에 평문 시크릿 없음 | 전 트리 스캔 결과 **없음** (아래 단서 있음) |

47과 17이 우연히 맞는 숫자가 아니라 정말 그 숫자였다. 이건 기분이 좋았다.

Kafka 노드풀은 `replicas: 1` 이다. dual-role 이 한 대라는 뜻이고, 65개 토픽 전부 replication factor 1 이다. 이건 결함이 아니라 이 클러스터가 무엇인지를 말해주는 숫자다 — 포트폴리오용 홈랩이고, 브로커 한 대가 죽으면 그냥 다 죽는 걸 받아들인 구성이다. 다만 소개 문단이 "KRaft dual-role" 이라고만 하면 듣는 쪽은 보통 3대를 떠올린다.

## ① "fluent-bit → Elasticsearch" 에는 홉이 하나 빠져 있다

fluent-bit 의 출력 설정을 열어봤다.

```
[OUTPUT]
    Name              http
    Host              logs-ls-api.logging.svc.cluster.local
    Port              8080
    Format            json_lines
    Retry_Limit       5
```

Elasticsearch 가 아니다. **Logstash** 다. 실제 경로는 fluent-bit(6노드 데몬셋) → Logstash → Elasticsearch(hot/warm/cold 3티어) → Kibana 다. 소개 문단이 중간 한 홉을 지운 것이다.

이게 왜 사소하지 않은가. fluent-bit 자신의 지표를 6개 노드 전부에서 긁어봤다.

```
proc_records 합계   11,306,615
dropped_records     0
retries_failed      0
```

숫자만 보면 "로그를 하나도 안 잃었다" 로 읽힌다. 그런데 이 카운터는 **Logstash 에 넘긴 것까지만** 센다. 그 뒤에서 Logstash 가 필터로 떨구든 Elasticsearch 가 매핑 충돌로 거절하든, fluent-bit 의 `dropped_records` 는 0 을 유지한다.

Elasticsearch 쪽도 재봤다. 일별 인덱스가 실제로 쌓이고 있다.

```
logstash-k8s-2026.08.28   81,921 docs   (당일, 오후 기준)
logstash-k8s-2026.08.27  191,113
logstash-k8s-2026.08.26  162,315
```

양 끝은 확인했다. **가운데는 확인하지 못했다.** Logstash 의 `_node/stats/events`(9600)를 API 서버 프록시로 두 번 시도했는데 응답을 받지 못했다. 그래서 "입력 1,130만 건, 인덱스 19만 건/일" 두 숫자를 나란히 놓을 수는 있어도 뺄셈을 할 수는 없다 — fluent-bit 카운터는 파드 기동 이후 누적이고 6개 노드의 가동 시간이 다르며, Logstash 가 의도적으로 떨구는 양도 모른다. **양 끝만 초록불이고 중간이 안 보이는 상태**라는 게 오늘 잰 결과의 전부다.

여기서 배운 건 로그 파이프라인 얘기가 아니다. **"0 dropped" 라는 지표가 증명하는 거리가 문장이 주장하는 거리보다 짧았다.**

## ② Tempo 는 켜져 있고, 아무것도 안 받고 있었다

관측 세 기둥 중 Prometheus 와 Grafana 는 확실히 일한다. Prometheus 스크레이프 타깃이 28개 job 이고 전부 `up=1`, 알람 규칙이 37개 PrometheusRule 안에 **174개**다. 이건 죽은 설정이 아니다.

Tempo 를 열어봤다.

```
StatefulSet tempo-0        Running (66d)
receivers                  jaeger(4종) + otlp(grpc/http)  ← 전부 설정됨
block_retention            24h

/api/echo                  → "echo"        (살아 있음)
/api/search/tags           → {"tagNames":[], "metrics":{}}
```

**태그가 비어 있다.** 트레이스가 하나도 인덱싱돼 있지 않다는 뜻이다. 왜인지 찾는 데는 오래 걸리지 않았다.

- 전 네임스페이스 파드 중 `OTEL_EXPORTER_OTLP_ENDPOINT` 를 가진 파드: **0개**
- Grafana 설정에서 Tempo 를 데이터소스로 가리키는 곳: **0곳**
- Prometheus 가 수집한 메트릭 이름 중 `tempo` 로 시작하는 것: **0개**

보내는 쪽이 없고, 보는 쪽이 없고, 안 받고 있다는 걸 알려줄 감시도 없다. 세 번째가 제일 나쁘다. Tempo 는 `Running 1/1` 이고 파드 목록에서도 초록색이라, **무엇도 이상하다고 말하지 않는다.**

공정하게 덧붙이면 retention 이 24시간이라, 24시간보다 전에 트레이스가 있었을 가능성은 이 관측만으로 배제할 수 없다. 하지만 그걸 확인할 방법도 없다 — Tempo 를 스크레이프하지 않으니 과거 수신량의 기록이 아예 없다.

나는 이 블로그에서 [어제](/2026/08/27/grill-me-vs-ouroboros-enforcement/) 인터페이스만 있고 구현이 없어 운영에서 아무것도 안 거르던 게이트 얘기를 썼고, [오늘 낮](/2026/08/28/guard-exemptions-that-expire/)에는 내 정산 리포의 3층 방어 중 한 층이 꺼져 있던 걸 적었다. 같은 걸 세 번째로 찾았는데, 이번엔 남의 코드가 아니라 **내가 남에게 소개하던 문장** 안에 있었다.

## ③ 토픽 65개 중 git 에 선언된 건 1개

Kafka 쪽에서 가장 놀란 숫자다.

```
브로커 실제 토픽                65개
KafkaTopic CR (선언된 토픽)      1개   (notification-topic)
auto.create.topics.enable      true  (브로커 기본값, 미변경)
num.partitions                 1     (브로커 기본값)
```

64개 토픽이 **어디에도 선언돼 있지 않다.** 애플리케이션이 처음 보내는 순간 브로커가 기본값으로 만들어 준 것들이다. 실제로 파티션 분포를 보면 그 흔적이 남아 있다 — 40개가 1파티션(= 자동 생성 기본값), 24개가 3파티션(= 누군가 명시적으로 만든 것), 1개가 50(내부 오프셋 토픽).

`auto.create.topics.enable=true` 의 진짜 위험은 파티션 수가 아니다. **토픽 이름에 오타를 내도 에러가 안 난다는 것**이다. 프로듀서는 성공하고, 새 토픽이 조용히 하나 생기고, 컨슈머는 영원히 아무것도 못 받는다. 예외도 로그도 없다.

DLT 짝을 맞춰 파티션 수를 비교하니 17쌍 중 **4쌍이 어긋나** 있었다(본토픽 1파티션 → DLT 3파티션). 방향상 당장 사고가 나는 조합은 아니지만, 본토픽과 DLT 가 서로 다른 경로로 만들어졌다는 증거다. 한쪽은 선언됐고 한쪽은 자동 생성됐다.

한편 브로커 자체는 Prometheus 가 안 본다. Kafka CR 에 `metricsConfig` 가 없고 `kafka` 네임스페이스의 ServiceMonitor/PodMonitor 가 0개다. 즉 컨슈머 랙도, DLT 적재량도 브로커 쪽에서는 안 보인다.

**그런데 DLQ 알람은 있었다.** 174개 알람 중 정확히 하나가 여기에 닿는다.

```yaml
alert: SettlementDlqGrowing
expr: sum(increase(outbox_dlq_published_total[15m])) > 0
for: 5m
```

브로커가 아니라 **애플리케이션 쪽 Micrometer 카운터**를 본다. 정산 서비스는 스크레이프되고 있으니 이건 실제로 작동하는 통제다. 브로커를 못 보는 상태에서 관측 가능한 지점을 골라 붙인 거라, 설계로는 오히려 영리하다. 다만 이름이 말하듯 아웃박스 발행 경로를 세는 것이고, 17개 DLT 전반을 덮지는 않는다.

## ④ "포트포워딩 없이 터널만" — WAN 에 대해서만 참이다

이게 오늘 나온 가장 값진 발견이다.

문장은 사실이다. 공유기에 포트포워딩이 없고, `cloudflared` 가 바깥으로 나가는 연결을 열어 그 위로만 인터넷 트래픽이 들어온다. **인터넷에서 오는 경로는 정말 터널 하나뿐이다.**

그런데 클러스터 서비스를 세어봤다.

```
NodePort 서비스        39개
LoadBalancer            0개
Ingress                 2개
NetworkPolicy          12개 (47개 네임스페이스 중 3개에만)
```

NodePort 39개는 **모든 노드의 IP 에서 열려 있다.** 그 안에 Postgres 인스턴스 3개, 비밀번호 볼트, Kubernetes 대시보드, ArgoCD 서버, Kibana 가 들어 있다.

추정으로 남기기 싫어서 노드 방화벽을 확인했다.

```
$ ufw status
Status: inactive

$ iptables -S INPUT
-P INPUT ACCEPT
```

그리고 같은 랜에 있는 노트북에서 노드 IP 로 직접 요청을 보내봤다. **HTTP 200.** 터널을 거치지 않고, 인증도 없이, 그냥 닿는다.

정리하면 이렇다. **터널은 인터넷 경계를 설명하는 문장인데, 듣는 사람은(그리고 나 자신도) 그걸 "닫혀 있다" 로 일반화한다.** 실제 경계는 이렇게 갈린다.

| 출발지 | 도달 가능 | 통제 |
|---|---|---|
| 인터넷 | 터널 뒤의 서비스만 | Cloudflare Tunnel |
| 같은 랜 | NodePort 39개 전부 | **없음** |
| 클러스터 내부 파드 | 44/47 네임스페이스에 제한 없음 | NetworkPolicy 3개 ns 만 |

같은 WiFi 에 붙은 아무 기기나 — 예를 들어 펌웨어가 5년 묵은 IoT 하나가 — 데이터베이스 세 대와 볼트에 직접 닿는다. 이건 홈랩이라 감수한 트레이드오프일 수 있다. 문제는 **감수한 적이 없다는 것**이다. 나는 저 문장을 쓰면서 스스로 닫혀 있다고 생각하고 있었다.

## ⑤ SOPS 는 값을 암호화하지, 리포를 암호화하지 않는다

`.sops.yaml` 의 규칙은 이렇다.

```yaml
- path_regex: \.sops\.ya?ml$
  encrypted_regex: '^(data|stringData)$'
  age: age1…
```

`data` 와 `stringData` 만 암호화한다. 나머지는 전부 평문이다. 즉 리포에 커밋된 24개 시크릿 파일에서 **값은 안 보이지만 이건 다 보인다** — 시크릿 이름, 네임스페이스, 키 이름, 시크릿 타입, 그리고 주석에 적어둔 갱신 절차와 스코프.

이건 버그가 아니라 의도된 설계다. 그래야 `git diff` 가 읽히고, 뭐가 바뀌었는지 리뷰할 수 있다. SOPS 의 존재 이유가 그거다. 다만 "리포에 평문이 없다" 는 문장은 **값에 대해 참이고 구조에 대해 거짓**이다. 어떤 서비스가 어떤 종류의 자격증명을 몇 개 들고 있는지는 리포만 보면 다 나온다.

그리고 더 중요한 쪽. 평문 시크릿이 정말 없는지 전 트리를 스캔했다. `kind: Secret` 에 `data`/`stringData` 를 가진 파일이 2개 걸렸다.

- 하나는 Helm 값으로 채우는 템플릿 — 리터럴 값 없음.
- 하나는 하드코딩된 `POSTGRES_PASSWORD` 가 있었다. 값은 `"CHANGEME-via-sops"` 라는 자리표시자였고, 상위 `values.yaml` 이 `postgres.enabled: false` 라 **렌더링되지 않는다.** 클러스터에 해당 시크릿이 존재하지 않는 것도 확인했다.

그래서 "평문 없음" 은 지금 사실이다. 문제는 그게 **강제된 불변식이 아니라는 것**이다.

```
core.hooksPath                        미설정
.gitignore 의 시크릿 관련 규칙        없음
gitleaks / detect-secrets            없음
chart-guard.py (489줄) 의 규칙       프로브·필수 env·SPA fallback·업스트림
                                     → 평문 시크릿 검사 없음
CI (chart-ci)                        최근 실행 전부 failure (비공개 리포 분 과금 차단)
```

저 잠들어 있는 템플릿에 진짜 비밀번호를 적어 넣고 커밋해도, **아무것도 막지 않는다.** 오늘 평문이 없는 이유는 통제가 아니라 습관이다.

재밌는 대칭이 하나 있다. `chart-guard.py` 80행에 이런 주석이 달려 있다 — 계약 파일이 지워지면 검사가 조용히 0건으로 통과하니 앵커를 코드에 박아 뒀다는 것. **공회전하는 검사를 경계하는 규율은 이미 있는데, 정작 평문 시크릿이라는 검사 자체가 없다.**

## 다섯 개를 관통하는 것

되짚어 보면 다섯 발견이 전부 같은 모양이다.

| 문장 | 실제로 참인 범위 |
|---|---|
| fluent-bit → Elasticsearch, 0 dropped | fluent-bit → **Logstash** 까지 |
| 관측은 Prometheus·Grafana·**Tempo** | Tempo 는 켜져 있음. 받고 있지는 않음 |
| 업무 토픽 47 + DLT 17 | 정확. 단 65개 중 **1개만** git 에 선언됨 |
| 포트포워딩 없이 터널만 | **인터넷** 경계에 대해서만. 랜에는 39개 열림 |
| 리포에 평문 없음 | **값**에 대해서만. 그리고 강제되지 않음 |

어느 것도 거짓말이 아니다. 전부 **더 짧은 거리에 대해 참인 문장을 더 긴 거리에 대해 쓴 것**이다. 그리고 그 차이는 대부분 나 자신을 속인다 — 남에게 소개하려고 만든 문장이 시간이 지나면 내가 그 시스템을 기억하는 방식이 되기 때문이다.

인프라를 문단으로 요약하는 습관 자체를 버릴 필요는 없다. 대신 요약할 때마다 이렇게 물으면 된다.

1. 이 화살표(`→`)에 홉이 몇 개 숨어 있나?
2. 이 컴포넌트가 **일하고 있다**는 증거가 있나, 아니면 **떠 있다**는 증거만 있나?
3. 이 경계 문장은 어느 출발지에 대해 참인가? 인터넷? 랜? 파드?
4. 이 상태는 통제가 만든 것인가, 습관이 만든 것인가?

2번이 제일 자주 걸린다. 오늘도 그랬다.

---

**검증 범위.** 2026-08-28 기준 K3s 6노드(v1.35.4+k3s1) 실클러스터에서 잰 값이다. 토픽·파티션·브로커 설정은 `kafka-topics.sh --describe` 와 `kafka-configs.sh --describe --all`, 알람 규칙은 PrometheusRule 전수 파싱, 스크레이프 상태는 Prometheus `up` 쿼리, Tempo 는 `/api/search/tags` 와 `/api/echo`, fluent-bit 은 6개 파드의 `:2020/api/v1/metrics`, Elasticsearch 인덱스는 `_cat/indices` 결과다. NodePort 도달성은 같은 랜의 노트북에서 비민감 서비스 한 개에 요청해 HTTP 200 을 받은 것이며, 나머지 38개는 각각 시도하지 않았다(방화벽 비활성 + `-P INPUT ACCEPT` 로부터의 추론이다). Logstash 단계의 이벤트 수는 **측정하지 못했다** — 본문에 그대로 적었다. 노드 IP·포트 번호·age 공개키는 의도적으로 생략했다. 이 글은 홈랩 구성을 프로덕션 기준으로 평가한 것이 아니라, 소개 문단과 실측의 차이만 다룬다.

## References

- Apache Kafka Documentation — Broker Configs (`auto.create.topics.enable`, `num.partitions`) — <https://kafka.apache.org/documentation/#brokerconfigs>
- Strimzi Documentation — Kafka node pools and KRaft roles — <https://strimzi.io/docs/operators/latest/deploying#assembly-node-pools-str>
- Grafana Tempo Documentation — Configuration (distributor receivers, `block_retention`) — <https://grafana.com/docs/tempo/latest/configuration/>
- Fluent Bit Documentation — HTTP output plugin / Monitoring API — <https://docs.fluentbit.io/manual/pipeline/outputs/http>
- Mozilla SOPS — `encrypted_regex` and creation rules — <https://github.com/getsops/sops>
- Cloudflare Docs — Cloudflare Tunnel (outbound-only connections) — <https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/>
- Kubernetes Documentation — Service type NodePort / Network Policies — <https://kubernetes.io/docs/concepts/services-networking/service/#type-nodeport>
- 이 블로그, [무기한 예외를 문법적으로 불가능하게 만들기](/2026/08/28/guard-exemptions-that-expire/) (2026-08-28)
- 이 블로그, [319단어 대 28만 줄 — grill-me 와 우로보로스](/2026/08/27/grill-me-vs-ouroboros-enforcement/) (2026-08-27)
