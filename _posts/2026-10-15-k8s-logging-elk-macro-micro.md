---
layout: post
title: "쿠버네티스 로깅, 거시와 미시 — 왜 모으는가부터 우리 ELK 의 17GB 까지"
date: 2026-10-15 13:48:19 +0900
categories: [kubernetes, observability]
tags: [logging, elk, elasticsearch, logstash, fluent-bit, kibana, loki, ilm, k3s, observability]
---

> 홈랩 K3s 클러스터(노드 6대)에서 서비스를 몇 개 내리고 나서 남은 걸 메모리 순으로 세어 봤다. 맨 위가 **로깅(ELK) 약 17GB**였다.
> 이걸 그대로 둘지, 줄일지, 뺄지 정하기 전에 로깅을 두 높이에서 정리해 둔다.
> **거시**: 왜 로그를 한곳에 모으고, 어떤 설계들이 있는가. **미시**: 우리 클러스터 ELK 를 2026-10-13~15 에 실측한 값.
> 미시 파트의 수치는 전부 이 클러스터에서 직접 잰 값이라 일반화하면 안 된다.

## TL;DR

- 쿠버네티스는 로그를 **저장하지 않는다**. 노드·파드가 죽으면 로그도 같이 사라지니 클러스터 레벨 로깅이 필요하다. 이 말은 쿠버네티스 공식 문서에 있다.
- 백엔드 설계는 크게 두 가지다. **본문 전문을 색인하는 방식**(Elasticsearch)과 **라벨만 색인하는 방식**(Loki). 앞쪽은 검색이 강한 대신 RAM 과 디스크를 쓴다. 뒤쪽은 싸지만 검색이 grep 에 가깝다.
- 우리 ELK 실측 결과:
  - 로그 데이터 **약 15GB를 붙잡는 데 RAM 약 17GB**를 쓴다. 그 대부분이 노드 한 대(ilwon)에 몰려 있다.
  - 9/25 까지 컨테이너 로그의 **약 83%가 에러 없이 버려지고 있었다**. 원인은 설정 한 줄이었다.
  - 저장 용량의 **62.6%가 원문 사본 필드(`event.original`)**였다.
  - 지금 들어오는 로그의 **절반가량은 ArgoCD 의 "처리 시작/완료" 소음**이다.

---

# Part 1. 거시 — 로그를 왜, 어떻게 모으는가

## 1.1 로그는 "파일"이 아니라 "이벤트 스트림"이다

Twelve-Factor App 은 로그를 *시간순으로 흐르는 이벤트 스트림*으로 정의한다. 앱은 로그를 어디로 보낼지 신경 쓰지 말고 **stdout 에 버퍼 없이 쓰기만** 하라고 한다. 모으고, 보내고, 보관하는 일은 실행 환경의 몫이다 ([12factor.net — Logs](https://12factor.net/logs)).

쿠버네티스는 이 철학을 그대로 따른다. 컨테이너의 stdout/stderr 를 노드의 파일로 받아 두고, `kubectl logs` 로 보여 준다. 다만 공식 문서는 한계를 분명히 적는다.

> "In a cluster, logs should have a separate storage and lifecycle independent of nodes, pods, or containers. This concept is called cluster-level logging."
> "Kubernetes does not provide a native storage solution for log data."
> — [Kubernetes Docs, Logging Architecture](https://kubernetes.io/docs/concepts/cluster-administration/logging/)

크래시한 컨테이너, 축출된 파드, 죽은 노드의 로그는 `kubectl logs` 로는 못 본다. 그때 필요한 게 **클러스터 레벨 로깅**이다. 노드와 별개의 저장소와 수명을 가진 백엔드다.

## 1.2 표준 파이프라인: 수집 → 가공 → 저장·색인 → 조회

같은 문서가 권하는 가장 흔한 패턴은 **노드마다 로깅 에이전트를 DaemonSet 으로 띄우는 것**이다. 단계는 넷이다.

| 단계 | 하는 일 | 대표 구현 |
| --- | --- | --- |
| 수집 | 노드의 `/var/log/containers/*.log` 를 tail 하고 파드 메타데이터를 붙인다 | Fluent Bit, Fluentd, Vector, Grafana Alloy |
| 가공 | 파싱·필터·필드 정리·드롭 | Logstash, (에이전트 자체 필터) |
| 저장·색인 | 검색 가능한 형태로 보관 | Elasticsearch, Loki, ClickHouse |
| 조회 | 검색·대시보드·알림 | Kibana, Grafana |

ELK 는 Elasticsearch·Logstash·Kibana 의 머리글자다. 수집기를 Fluent Bit 로 쓰면 흔히 EFK 라고도 부른다.

## 1.3 핵심 갈림길: "본문을 색인하나, 라벨만 색인하나"

설계 철학이 실제로 갈리는 곳은 저장·색인 단계다.

**Elasticsearch: 전문 색인.** 문서의 필드를 역색인(inverted index)으로 만든다. 그래서 임의 문자열 검색, 필드 집계, 정렬이 빠르다. 대가는 색인 크기와 메모리다. JVM 힙이 필요하고, Elastic 은 **힙을 가용 메모리의 50% 이하로** 두라고 권한다. 나머지는 OS 파일시스템 캐시와 off-heap 버퍼가 쓰기 때문이다 ([Elastic Docs — JVM settings](https://www.elastic.co/docs/reference/elasticsearch/jvm-settings)). 노드 메모리가 힙의 대략 두 배가 되는 구조다.

**Loki: 라벨만 색인.** Grafana Loki 공식 문서는 이렇게 설명한다.

> "Loki does not index the contents of the logs, but only indexes metadata about your logs as a set of labels for each log stream."
> — [Grafana Loki Docs, Overview](https://grafana.com/docs/loki/latest/get-started/overview/)

본문은 압축 청크로 오브젝트 스토리지(S3·GCS 등)에 넣는다. 색인은 라벨 집합만큼 작다. 문서는 이 구조가 Loki 를 "less expensive to operate" 하게 만든다고 쓴다. 단, 이것은 **벤더 자기 서술**이다. 같은 워크로드로 ES 와 Loki 를 맞붙인 중립 제3자 벤치마크는 이 글을 쓰며 찾지 못했다. 그래서 "몇 배 싸다" 같은 수치는 쓰지 않는다.

트레이드오프를 정리하면 이렇다.

| | Elasticsearch (ELK/EFK) | Loki |
| --- | --- | --- |
| 색인 대상 | 본문·필드 전부 | 라벨(스트림 메타데이터)만 |
| 강점 | 임의 검색·집계·필드 분석 | 저장 비용·운영 단순성 (벤더 서술) |
| 약점 | 힙+파일캐시 메모리, 색인 디스크 | 본문 검색은 청크 스캔. 라벨 설계를 잘못하면 느려진다 |
| 저장 | 로컬 디스크(+스냅샷) | 오브젝트 스토리지 |

## 1.4 시간이 지난 로그는 "식혀서" 버린다 — 데이터 티어와 ILM

로그는 시계열이다. 어제 로그는 자주 보고 3주 전 로그는 거의 안 본다. Elasticsearch 는 이를 **데이터 티어**로 표현한다 ([Elastic Docs — Data tiers](https://www.elastic.co/docs/manage-data/lifecycle/data-tiers)).

- **hot**: 색인과 최신 데이터 조회
- **warm**: 덜 자주 조회, 거의 갱신 없음
- **cold**: 드물게 조회
- **frozen**: 아주 드물게 조회 (searchable snapshot 전용)

**ILM(Index Lifecycle Management)**은 인덱스 나이에 따라 이 티어를 자동으로 옮기고 마지막에 지운다. 단계마다 `min_age` 를 두고, 이 값은 단계를 따라 증가해야 한다 ([Elastic Docs — ILM phases](https://www.elastic.co/docs/manage-data/lifecycle/index-lifecycle-management/index-lifecycle)).

여기서 주의할 점이 있다. 티어는 *같은 하드웨어를 나눠 쓰라는 설계가 아니다.* Elastic 문서는 같은 티어 노드끼리 하드웨어 프로필을 맞추라고 권하고, 차가운 티어일수록 싼 저장소를 전제한다. 홈랩에서 hot/warm 을 같은 노드에 두면 "식혀서 아낀다"는 이점은 거의 없고 JVM 프로세스 수만 늘어난다. 이 점은 Part 2 에서 실제로 드러난다.

---

# Part 2. 미시 — 우리 클러스터의 ELK, 실측

> 측정일: 2026-10-13 ~ 10-15. 출처: `_cat/*` API, ILM API, 인덱스 집계, `kubectl top`, helm-deploy 리포 git 이력.

## 2.1 구성

```
[각 노드] Fluent Bit (DaemonSet, tail /var/log/containers/*.log + kubernetes 필터)
     │  http output, Format json
     ▼
 Logstash (http input, codec json) ── ruby/mutate/grok 필터 131줄
     ▼
 Elasticsearch 8.16.1 (ECK 오퍼레이터)  hot ─7d→ warm ─14d→ cold ─30d→ delete
     ▼
 Kibana
```

| 컴포넌트 | 노드 | 메모리 limit / 힙 | 실사용 | PVC |
| --- | --- | --- | --- | --- |
| ES hot (master·ingest 겸) | ilwon | 6Gi / 4g | 5,778Mi | 200Gi |
| ES warm | ilwon | 5Gi / 3g | 4,248Mi | 300Gi |
| ES cold | solomon | 4Gi / 2g | 2,940Mi | 500Gi |
| Logstash | ilwon | 4Gi / 2g | 3,594Mi | — |
| Kibana | louise | — | 608Mi | — |
| Fluent Bit | 노드마다 | — | 약 15~22Mi | — |

- 클러스터 상태: green, 데이터 노드 3, 샤드 113, **레플리카 0**. 노드 하나를 잃으면 그 노드의 인덱스도 잃는다.
- 디스크 위의 인덱스: hot 5.1GB, warm 4.2GB, cold 5.3GB, **합계 약 14.6GB**.
- 보존 정책 `logstash-k8s-policy`: 0d hot → 7d warm (forcemerge 1세그먼트) → 14d cold → 30d delete. 일별 인덱스 `logstash-k8s-YYYY.MM.dd`, 현재 31개.

한 줄로 줄이면 이렇다.

$$
\frac{\text{RAM}}{\text{보관 중인 로그}} \approx \frac{17\ \text{GB}}{14.6\ \text{GB}} \approx 1.2
$$

로그 1GB 를 붙잡는 데 RAM 이 1GB 넘게 든다. 게다가 hot·warm·Logstash 셋이 같은 노드(ilwon)에 있어서 그 노드 하나가 ELK 에만 **약 13.6GB**를 쓰고 메모리 사용률 85%다. 1.4절에서 말한 "같은 하드웨어 위의 티어"가 바로 이 모습이다. warm 티어는 비용을 아끼지 못하고 JVM 하나를 더 띄울 뿐이다.

## 2.2 발견 ① — 9/25 까지 컨테이너 로그 83%가 조용히 사라지고 있었다

Fluent Bit http output 의 `format` 은 `json`, `json_lines`, `json_stream`, `msgpack`, `gelf` 중에서 고른다 ([Fluent Bit Docs — HTTP output](https://docs.fluentbit.io/manual/data-pipeline/outputs/http)). 우리는 `json_lines`(줄바꿈으로 구분된 NDJSON)로 보내고 있었다. 받는 쪽은 Logstash http input 의 json codec 이다 ([Logstash Docs — Http input](https://www.elastic.co/guide/en/logstash/current/plugins-inputs-http.html)).

결과적으로 **본문의 첫 줄만 이벤트가 되고 나머지 줄은 에러 없이 버려졌다.** 노드 하나에서 잰 값은 이랬다.

$$
\text{색인률} = \frac{19}{115} \approx 16.5\% \quad\Rightarrow\quad \text{유실률} \approx 83.5\%
$$

`format json`(JSON 배열)으로 바꾸자 배열 원소마다 이벤트로 쪼개져 3/3 이 들어왔다. 고친 커밋은 2026-09-25 의 `fluent-bit kube.*: Format json` 이다.

일별 인덱스에 그 흔적이 그대로 남아 있다.

| 기간 | 하루 문서 수 | 하루 용량 |
| --- | --- | --- |
| 9/25 이전 | 약 22만~26만 | 131~158MB |
| 9/25 이후 | 약 120만~186만 | 487~734MB |

**새 소음이 생긴 게 아니다. 원래 있던 로그가 비로소 보이기 시작한 것이다.** 같은 날 ArgoCD 로그만 따로 보면 3시간당 3,981건에서 약 9만 건으로 뛰었다.

이 유실이 무서운 이유는 아무 신호도 없었기 때문이다. Fluent Bit 은 HTTP 200 을 받았으니 성공으로 셌다. Logstash 도 에러를 남기지 않았다. Kibana 에는 로그가 "있었다". 문서 수가 줄어든 것이 아니라 *처음부터 적게 들어왔으니*, 비교할 기준선이 없으면 알아챌 방법이 없다. 이번에 잡은 방법은 **보낸 건수와 색인된 건수를 직접 맞대 본 것**이다.

## 2.3 발견 ② — 저장 용량의 62.6%가 "원문 사본"이었다

Logstash 의 json codec 은 ECS 호환 모드에 따라 원문을 `event.original` 에 복사해 둘 수 있다. 7월 말에 인덱스 하나를 열어 보니 이랬다.

- `event.original`: **3,923MB** (전체의 62.6%)
- 실제 로그 텍스트: 5.4MB

같은 내용을 파싱된 필드로 한 번, 원문 문자열로 또 한 번 저장하고 색인까지 하고 있었다. 2026-07-29 에 파이프라인 0.4단계에서 이 필드를 지웠다. 지금 http input 은 `ecs_compatibility => disabled` 다.

같은 계열의 비용이 하나 더 있다. 매핑에 dynamic template 이 없어서 **문자열 필드 167개가 전부 `text` + `keyword` 로 이중 매핑**된다. 집계하지 않을 필드까지 keyword 를, 검색하지 않을 필드까지 text 를 갖고 있다.

## 2.4 발견 ③ — 로그의 절반은 "잘 돌고 있음"이라는 말이다

10/13 하루치를 네임스페이스별로 집계했다.

| 네임스페이스 | 문서 수 | 주된 내용 |
| --- | --- | --- |
| argocd | 744,398 | notifications-controller "Start processing / Processing completed" 309,144, application-controller "Update successful" 291,782 |
| velero | 184,888 | 백업 진행 로그 |
| monitoring | 158,372 | otel-collector 152,859 (prometheusexporter 스택트레이스) |
| fab-lab | 84,078 | detector |
| kube-system(coredns) | 71,588 | DNS 질의 |
| settlement | 25,764 | 실제 업무 서비스 |

실제 업무 서비스인 settlement 는 하루 2.6만 건이다. **ArgoCD 가 그 29배**인데 내용은 "처리 시작", "처리 끝", "업데이트 성공"이다. 이 클러스터에서 "로그 저장 비용"은 거의 **소음 저장 비용**이라는 뜻이다.

드롭 규칙이 없는 건 아니다. Logstash 4단계는 `/actuator/health` 와 `/metrics` 를 버린다. 그런데 이 규칙은 `[message]` 필드만 본다. Fluent Bit 이 보내는 본문은 `log` 필드에 있어서 `/healthz` 류 헬스체크 로그는 그대로 통과했다. 이번에 내린 서비스 둘이 하루 약 6.8만 건을 이런 healthz 로그로 쓰고 있었다.

## 2.5 그래서 보존 30일은 얼마인가

현재 유입량으로 30일을 채우면 대략 이렇게 된다.

$$
30\ \text{일} \times (0.49 \sim 0.73)\ \text{GB/일} \approx 15 \sim 22\ \text{GB}
$$

지금 14.6GB 인 이유는 9/25 이후 데이터가 아직 30일치가 안 쌓였기 때문이다. 디스크는 hot 에만 수백 GB 여유가 있어서 문제가 아니다. **문제는 RAM**이다. 그리고 2.4절을 보면 그 RAM 의 절반은 소음을 담는 데 쓰인다.

## 2.6 ELK 에 기대고 있는 것

뺄 때 같이 죽는 것을 확인했다.

- `log-error-alerter` CronJob (5분마다): ES 를 질의해 에러 로그를 알린다. **ES 가 없으면 이 알림이 사라진다.**
- 같은 ES 에 사는 다른 인덱스들: filebeat, metricbeat, Claude Code OTel 로그, k8s 이벤트 요약.
- 메트릭(Prometheus)과 트레이스는 ES 와 독립이라 영향이 없다.

---

# Part 3. 선택지

이 클러스터는 연구용이다. 그래서 기준은 "무엇을 잃고 무엇을 얻나" 하나다.

| 선택 | RAM 회수 | 잃는 것 | 비고 |
| --- | --- | --- | --- |
| A. 그대로 + 소음 제거 | 0 (증가 둔화) | 없음 | argocd·velero·otel 드롭, healthz 규칙을 `log` 까지 확장, dynamic template |
| B. hot 단일 노드로 축소 | 약 7GB | 7일 넘은 로그, 티어 구조 | warm/cold 제거, 보존 7일. 알림 유지 |
| C. ELK 전체 제거 | 약 17GB | 중앙 로그 검색, 에러 알림 | `kubectl logs` 로 회귀. 죽은 파드 로그는 못 봄 (1.1절) |
| D. Loki 로 교체 | 측정 안 함 | 본문 전문 검색·집계 | 라벨 색인이라 가벼울 것으로 *기대*. 실측 전엔 숫자로 약속하지 않음 |

개인적인 정리는 이렇다. **어느 쪽을 고르든 A(소음 제거)는 먼저 하는 게 맞다.** 소음을 걷어 내야 B 나 D 를 가늠할 기준선이 정직해진다. 그리고 2.2절이 남긴 교훈은 선택과 상관없이 유효하다. 로그 파이프라인은 **보낸 건수와 받은 건수를 주기적으로 맞대 보지 않으면, 반이 사라져도 아무도 모른다.**

---

## References

1. The Twelve-Factor App — *XI. Logs* (Adam Wiggins). <https://12factor.net/logs>
2. Kubernetes Documentation — *Logging Architecture*. <https://kubernetes.io/docs/concepts/cluster-administration/logging/>
3. Elastic Documentation — *Elasticsearch data tiers*. <https://www.elastic.co/docs/manage-data/lifecycle/data-tiers>
4. Elastic Documentation — *Index lifecycle management phases and actions*. <https://www.elastic.co/docs/manage-data/lifecycle/index-lifecycle-management/index-lifecycle>
5. Elastic Documentation — *JVM settings* (heap sizing). <https://www.elastic.co/docs/reference/elasticsearch/jvm-settings>
6. Elastic — *Logstash Http input plugin*. <https://www.elastic.co/guide/en/logstash/current/plugins-inputs-http.html>
7. Fluent Bit Documentation — *HTTP output*. <https://docs.fluentbit.io/manual/data-pipeline/outputs/http>
8. Grafana Labs — *Loki overview* (벤더 1차 문서, 비용 관련 서술은 벤더 주장). <https://grafana.com/docs/loki/latest/get-started/overview/>

> 수치 출처: Part 2 의 모든 수치는 필자의 홈랩 K3s 클러스터에서 2026-10-13~15 에 직접 측정했다 (`_cat` API·ILM API·인덱스 집계·`kubectl top`·git 이력). ES 와 Loki 를 맞붙인 중립 제3자 벤치마크는 찾지 못해 성능·비용 비교 수치는 싣지 않았다.
