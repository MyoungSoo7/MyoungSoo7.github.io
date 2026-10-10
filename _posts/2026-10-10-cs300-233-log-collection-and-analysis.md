---
layout: post
title: "[CS300 #233] 로그 수집과 분석 — 구조화 로그, 수집 파이프라인, 질의"
date: 2026-10-10 21:53:00 +0900
categories: [cs]
tags: [cs300, devops, logging, observability, loki]
---

컴퓨터공학 300 주제 시리즈의 233번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

로그는 개별 사건의 기록이다. 쓸모 있는 로그는 기계가 읽을 수 있게 구조화하고, 각 노드에서 수집기가 모아 중앙 저장소로 보내고, 레이블과 필드로 질의할 수 있어야 한다.

## 왜 필요한가

메트릭은 "에러율이 3% 로 올랐다"고 알려 준다. 하지만 어떤 요청이, 어떤 입력으로, 어떤 예외를 던졌는지는 로그에 있다. 서버가 한 대일 때는 SSH 로 들어가 `tail -f` 하면 됐다. 파드가 수십 개로 늘고 수시로 사라지면 그 방법은 끝난다. 파드가 지워지면 그 파드의 로그도 노드에서 곧 사라지기 때문이다. 로그를 파드 밖으로, 중앙으로 옮겨야 한다.

## 핵심 개념

### 심각도 수준

로그 수준의 뿌리는 syslog 다. RFC 5424 는 심각도를 0부터 7까지 여덟 단계로 정의한다.

| 값 | 이름 | 뜻 |
|---|---|---|
| 0 | Emergency | 시스템 사용 불가 |
| 1 | Alert | 즉시 조치 필요 |
| 2 | Critical | 치명적 상태 |
| 3 | Error | 에러 |
| 4 | Warning | 경고 |
| 5 | Notice | 정상이지만 주목할 상태 |
| 6 | Informational | 정보 |
| 7 | Debug | 디버그 |

애플리케이션 로깅 라이브러리는 보통 이를 줄여 ERROR, WARN, INFO, DEBUG 정도로 쓴다. 운영 환경 기본 수준은 INFO 로 두고, 문제를 추적할 때만 DEBUG 를 잠깐 켠다.

### 구조화 로그

```
# 비구조화
2026-10-10 12:00:01 ERROR payment failed for order 1234 user 42 after 3 retries

# 구조화(JSON)
{"ts":"2026-10-10T12:00:01Z","level":"error","msg":"payment failed",
 "order_id":1234,"user_id":42,"retries":3,"trace_id":"4bf92f35..."}
```

비구조화 로그는 사람이 읽기 편하지만, "retries 가 2 이상인 결제 실패"를 찾으려면 정규식을 짜야 하고 문구가 바뀌면 깨진다. 구조화 로그는 필드로 질의한다. 특히 `trace_id` 를 넣어 두면 분산 추적(234번)과 로그를 연결할 수 있다.

### 컨테이너 로그의 흐름

쿠버네티스에서 권장하는 방식은 단순하다. 애플리케이션은 **표준 출력과 표준 에러**로 로그를 쓴다. 나머지는 플랫폼이 맡는다.

```
앱(stdout/stderr)
   -> 컨테이너 런타임이 노드의 로그 파일에 기록(/var/log/pods/...)
   -> kubelet 이 크기 기준으로 회전
   -> 노드마다 하나씩 뜬 수집 에이전트(DaemonSet)가 파일을 읽음
   -> 파싱·레이블 부착(네임스페이스, 파드, 컨테이너)
   -> 중앙 저장소(Loki, Elasticsearch, 클라우드 로깅 등)
   -> 질의·대시보드·경보
```

`kubectl logs` 는 노드에 남아 있는 파일을 읽을 뿐이다. 파드가 삭제되거나 노드가 사라지면 함께 사라진다. 쿠버네티스 자체는 로그 저장 솔루션을 제공하지 않는다. 그래서 클러스터 수준 로깅을 따로 구성한다.

수집 패턴은 세 가지가 있다.

| 패턴 | 설명 |
|---|---|
| 노드 에이전트 | 노드마다 하나의 수집기. 가장 흔하고 효율적 |
| 사이드카 | 파드마다 수집 컨테이너. 파일로만 로그를 쓰는 레거시 앱용 |
| 앱이 직접 전송 | 앱이 로그 백엔드에 직접 보냄. 앱과 백엔드가 결합된다 |

### 저장 방식: 전문 색인 vs 레이블 색인

| 방식 | 대표 | 특징 |
|---|---|---|
| 전문(full-text) 색인 | Elasticsearch/OpenSearch | 모든 단어를 색인. 검색이 빠르고 유연하지만 저장·메모리 비용이 크다 |
| 레이블 색인 | Grafana Loki | 레이블(namespace, app 등)만 색인하고 본문은 압축 저장. 질의 시 해당 스트림을 훑는다. 저렴하지만 레이블 설계가 중요하다 |

Loki 의 질의 언어 LogQL 은 PromQL 과 닮았다.

```logql
{namespace="shop", app="payment"} |= "failed"
{namespace="shop", app="payment"} | json | retries >= 2
sum by (app) (rate({namespace="shop"} | json | level="error" [5m]))
```

첫 줄은 레이블로 스트림을 고르고 본문을 문자열로 거른다. 둘째 줄은 JSON 을 파싱해 필드로 거른다. 셋째 줄은 로그에서 메트릭(초당 에러 로그 수)을 만든다.

Loki 에서도 레이블 카디널리티 규칙이 그대로 적용된다. `user_id` 를 레이블로 올리면 스트림이 폭발한다. 그런 값은 본문 필드에 두고 질의 시 파싱한다.

### OpenTelemetry 와 로그

OpenTelemetry 는 메트릭·추적·로그를 같은 데이터 모델과 같은 수집기(Collector)로 다루려는 표준이다. 로그 레코드에 trace ID 와 span ID 를 담는 필드가 정의되어 있어, 한 요청의 로그와 추적을 서로 오가며 볼 수 있다.

### 보존과 비용

로그는 양이 가장 많은 관측 데이터다. 보존 기간을 계층화한다. 최근 며칠은 빠른 저장소에, 그 이후는 저렴한 객체 저장소에, 감사 로그처럼 규정이 요구하는 것은 별도로 더 길게. DEBUG 로그를 운영에서 상시 켜 두면 비용이 수십 배로 늘 수 있다.

### 로그에 쓰면 안 되는 것

비밀번호, 토큰, 세션 쿠키, 카드 번호, 주민등록번호 같은 개인정보. 로그는 많은 사람이 보고 오래 남는다. 요청 본문을 통째로 로깅하는 습관이 가장 흔한 유출 경로다. 수집 단계에서 마스킹 규칙을 두는 것도 방어선이 된다.

## 직접 해 보기

구조화 로그를 파싱해 질의하고, 로그에서 메트릭을 뽑아 보자.

```python
import json
from collections import Counter

raw = """\
{"ts":"12:00:01","level":"info","app":"payment","msg":"charged","order_id":1,"ms":120}
{"ts":"12:00:02","level":"error","app":"payment","msg":"payment failed","order_id":2,"retries":3}
{"ts":"12:00:02","level":"info","app":"cart","msg":"added","order_id":3,"ms":15}
not-json garbage line from a legacy library
{"ts":"12:00:03","level":"error","app":"payment","msg":"payment failed","order_id":4,"retries":1}
{"ts":"12:00:04","level":"warn","app":"cart","msg":"slow","order_id":5,"ms":950}
{"ts":"12:00:05","level":"error","app":"cart","msg":"db timeout","order_id":6}"""

records, unparsed = [], 0
for line in raw.splitlines():
    try:
        records.append(json.loads(line))
    except json.JSONDecodeError:
        unparsed += 1

# LogQL: {app="payment"} | json | retries >= 2
hits = [r for r in records if r["app"] == "payment" and r.get("retries", 0) >= 2]
print("payment failures with retries>=2:", [r["order_id"] for r in hits])

# LogQL: sum by (app) (count_over_time({...} | json | level="error"))
print("errors by app:", dict(Counter(r["app"] for r in records if r["level"] == "error")))

# 지연 필드에서 메트릭 추출
lat = sorted(r["ms"] for r in records if "ms" in r)
print("latency samples(ms):", lat, "max:", lat[-1])
print("unparsed lines:", unparsed)
```

결과는 다음과 같다.

```
payment failures with retries>=2: [2]
errors by app: {'payment': 2, 'cart': 1}
latency samples(ms): [15, 120, 950] max: 950
unparsed lines: 1
```

파싱에 실패한 한 줄을 버리지 않고 센 점에 주목한다. 실제 수집기도 파싱 실패율을 지표로 내보내야 한다. 형식이 바뀐 로그가 조용히 사라지는 것을 막기 위해서다.

## 현업에서는

- **"로그가 안 보여요".** 앱이 stdout 이 아니라 컨테이너 안의 파일에 쓰고 있는 경우가 많다. 노드 에이전트는 그 파일을 볼 수 없다. 앱 설정을 stdout 으로 바꾸거나 사이드카를 붙인다.
- **멀티라인 스택 트레이스.** 자바 예외처럼 여러 줄짜리 로그는 줄마다 별도 레코드로 쪼개져 들어온다. 구조화 로그로 한 레코드 안에 넣거나, 수집기에 멀티라인 결합 규칙을 둔다.
- **시각.** 노드 시계가 어긋나면 서로 다른 노드의 로그 순서가 뒤집혀 보인다. NTP 동기화와 UTC 기록을 기본으로 한다.
- **로그 경보는 신중하게.** "ERROR 가 한 줄이라도 나오면 경보"는 금방 소음이 된다. 로그에서 만든 비율 메트릭에 경보를 걸거나, 메트릭 쪽 경보를 주로 쓰고 로그는 원인 조사에 쓴다.
- **홈랩 규모.** 노드 몇 대짜리 클러스터라면 Loki + 노드 에이전트(Promtail 의 후속인 Grafana Alloy 등) + Grafana 조합이 가볍다. 이미 Prometheus·Grafana 를 쓰고 있다면 같은 대시보드에서 메트릭과 로그를 나란히 볼 수 있다.

## 확인 문제

1. RFC 5424 에서 심각도 값이 작을수록 더 심각한가, 덜 심각한가? Error 는 몇인가?
2. 쿠버네티스에서 애플리케이션 로그를 stdout 으로 쓰라고 권장하는 이유는?
3. 파드가 삭제된 뒤 `kubectl logs` 로 그 파드의 로그를 볼 수 있는가?
4. Loki 에서 사용자 ID 를 레이블로 쓰면 안 되는 이유와 대안은?
5. 구조화 로그에 trace ID 를 넣으면 얻는 이점은?

### 풀이

1. 작을수록 심각하다(0 이 Emergency). Error 는 3.
2. 런타임이 표준 위치에 파일로 기록하고 kubelet 이 회전하므로, 노드 에이전트 하나가 모든 컨테이너 로그를 같은 방식으로 수집할 수 있다.
3. 볼 수 없다(노드에서 함께 정리된다). 중앙 수집이 필요한 이유다.
4. 레이블 값마다 스트림이 생겨 카디널리티가 폭발한다. 본문 필드로 두고 질의 시 `| json` 으로 파싱해 거른다.
5. 한 요청의 로그를 모든 서비스에 걸쳐 찾고, 분산 추적 화면과 로그를 서로 연결할 수 있다.

## 더 읽을거리 (References)

- R. Gerhards, [RFC 5424: The Syslog Protocol](https://www.rfc-editor.org/rfc/rfc5424), IETF, 2009.
- Kubernetes Docs, [Logging Architecture](https://kubernetes.io/docs/concepts/cluster-administration/logging/)
- OpenTelemetry, [Logs](https://opentelemetry.io/docs/concepts/signals/logs/)
- Grafana Labs, [Grafana Loki documentation](https://grafana.com/docs/loki/latest/)
