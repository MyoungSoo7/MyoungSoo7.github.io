---
layout: post
title: "프로메테우스·그라파나 관리자가 알아야 할 A to Z — 공식 문서로 검증한 12가지"
date: 2026-08-12 03:10:00 +0900
categories: [모니터링, 인프라]
tags:
  [
    Prometheus,
    Grafana,
    PromQL,
    Alertmanager,
    옵저버빌리티,
    SRE,
    카디널리티,
    히스토그램,
    RED,
    USE,
  ]
---

모니터링 시스템을 운영하는 사람의 일은 그래프를 예쁘게 만드는 게 아니다.

> **새벽 3시에 깨어난 사람이 5분 안에 원인을 좁힐 수 있게 만드는 것.**
> 그리고 **깰 필요가 없을 때는 깨우지 않는 것.**

두 번째가 첫 번째보다 어렵다. 알림 피로는 모니터링 시스템이 죽는 가장 흔한 방식이다.

이 글은 계측 → 수집 → 저장 → 질의 → 시각화 → 경보 순서로 간다. **모든 규칙과 수치는
Prometheus 공식 문서와 Grafana 공식 문서로 대조했고, 확인하지 못한 것은 그렇다고 표시했다.**
인용문은 원문 표현을 옮긴 것이다. 벤더 벤치마크 주장은 인용하지 않았다.

---

## 0. 30초 요약

| #   | 주제                      | 모르면 벌어지는 일                                        |
| --- | ------------------------- | --------------------------------------------------------- |
| 1   | 프로메테우스가 안 맞는 곳 | 과금 데이터를 프로메테우스로 뽑아 정산이 틀림             |
| 2   | 메트릭 4종                | gauge에 `rate()`를 씌워 무의미한 그래프                   |
| 3   | 네이밍                    | ms와 s가 한 메트릭에 섞여 알림 임계치가 1000배 틀림       |
| 4   | **카디널리티**            | **user_id를 라벨에 넣고 프로메테우스가 OOM**              |
| 5   | 히스토그램 vs 서머리      | **퍼센타일을 평균 내서 통계적으로 무의미한 SLO 대시보드** |
| 6   | 저장                      | NFS에 TSDB를 올려 복구 불가능한 손상                      |
| 7   | 레코딩 룰                 | 비율의 평균을 내서 숫자가 조용히 틀림                     |
| 8   | 경보 철학                 | 원인마다 경보를 걸어 장애 한 번에 200개 알림              |
| 9   | Alertmanager              | 그룹핑 없이 페이지 폭탄, HA 앞에 LB를 둠                  |
| 10  | 대시보드 전략             | 대시보드 300개, 쓰는 건 4개                               |
| 11  | 프로비저닝                | 비밀번호의 `$`가 잘려 데이터소스 인증 실패                |
| 12  | 메타모니터링              | **모니터링이 죽은 걸 아무도 모름**                        |

---

## 1. 먼저, 프로메테우스가 맞지 않는 곳

도구를 배울 때는 "안 맞는 곳"부터 아는 게 안전하다. 공식 문서에 명시적인 절이 있다.

> "Prometheus values reliability. You can always view what statistics are available about your
> system, even under failure conditions. **If you need 100% accuracy, such as for per-request
> billing, Prometheus is not a good choice**, as the collected data will likely not be detailed
> and complete enough."
> — Prometheus Documentation, Overview ("When does it not fit?")

프로메테우스는 **정확성보다 가용성을 택한 설계**다. 스크레이프를 한 번 놓치면 그 구간 데이터는
그냥 없다. 대신 다른 게 다 죽어도 프로메테우스는 살아 있도록 만들어졌다.

> "Prometheus is designed for reliability, to be the system you go to during an outage (…) Each
> Prometheus server is standalone, not depending on network storage or other remote services."

**정산·과금·감사처럼 한 건도 놓치면 안 되는 데이터는 다른 시스템으로 모아야 한다.** 이걸 모르고
프로메테우스 카운터로 매출을 집계하는 조직이 실제로 있다.

## 2. 메트릭 4종 — 고르는 법은 규칙 두 줄이다

| 타입          | 성질                                    | 예                                 |
| ------------- | --------------------------------------- | ---------------------------------- |
| **Counter**   | 증가만 (프로세스 재시작 시 리셋)        | 총 요청 수, 총 전송 바이트         |
| **Gauge**     | 오르내림                                | 진행 중 요청 수, 여유 메모리, 온도 |
| **Histogram** | 관측값을 버킷에 카운트                  | 요청 지연 분포                     |
| **Summary**   | 계측 대상 프로세스가 분위수를 직접 계산 | (§5 참고 — 대개 피하는 게 낫다)    |

공식 문서의 판별 규칙은 한 줄이다.

> "To pick between counter and gauge, there is a simple rule of thumb: **if the value can go down,
> it is a gauge.**"
> — Prometheus Documentation, Instrumentation

그리고 두 가지 금지 사항.

> "Raw counters are rarely useful. Use the `rate()` function to get the per-second rate at which
> they are increasing."
>
> "Gauges can be set, go up, and go down. (…) **You should never take a `rate()` of a gauge.**"

### "시간 경과"가 아니라 "타임스탬프"를 내보내라

실무에서 자주 틀리는 지점이라 따로 적는다.

> "If you want to track the amount of time since something happened, **export the Unix timestamp
> at which it happened - not the time since it happened.** With the timestamp exported, you can
> use the expression `time() - my_timestamp_metric` (…) protecting you against the update logic
> getting stuck."

"마지막 성공 이후 경과 시간"을 직접 계산해서 내보내면, **그 갱신 로직이 멈췄을 때 값이 멈춘 채
정상으로 보인다.** 타임스탬프를 내보내면 PromQL 쪽에서 계산하므로 이 함정이 없다.

### 없는 시계열보다 0인 시계열이 낫다

> "Time series that are not present until something happens are difficult to deal with (…) To
> avoid this, export a default value such as `0` for any time series you know may exist in
> advance."

에러 카운터가 **에러가 한 번도 안 났을 때 존재하지 않으면**, `rate(errors_total[5m]) > 0` 같은
알림은 잘 동작하지만 `errors / total` 같은 식은 결과가 사라진다. 미리 0을 노출해야 한다.

## 3. 네이밍 — 나중에 못 고치는 결정

메트릭 이름은 한번 대시보드와 알림 YAML에 박히면 사실상 못 바꾼다. 공식 규칙을 요약한다.

- **애플리케이션 접두사(namespace)를 붙인다.** `prometheus_notifications_total`,
  `process_cpu_seconds_total`
- **하나의 단위, 하나의 양만 가리킨다.** "MUST refer to a single unit (e.g. do not mix seconds
  with milliseconds) and to a single quantity"
- **기본 단위를 쓴다.** 시간은 **초**, 크기는 **바이트**, 온도는 **섭씨**, 비율은 **0–1의
  ratio**(0–100 아님). 비트도 바이트로 통일한다("always use bytes, even where bits appear more
  common").
- **단위를 접미사로.** `http_request_duration_seconds`, `node_memory_usage_bytes`
- **누적 카운터는 `_total`.** `http_requests_total`, `process_cpu_seconds_total`
- **라벨 이름을 메트릭 이름에 넣지 않는다.** `http_responses_500_total`이 아니라
  `http_responses_total{code="500"}`.

그리고 이름이 잘 지어졌는지 검사하는 아주 좋은 경험칙이 문서에 있다.

> "As a rule of thumb, **either the `sum()` or the `avg()` over all dimensions of a given metric
> should be meaningful** (though not necessarily useful). If it is not meaningful, split the data
> up into multiple metrics."

큐의 **용량**과 큐의 **현재 원소 수**를 한 메트릭에 라벨로 섞으면 `sum()`이 무의미해진다.
그러면 잘못 설계한 것이다.

<small>참고: OpenTelemetry 계열 규약은 이름에 단위·타입을 넣지 않기를 권한다. Prometheus 문서는
그 차이를 인지한 채로 **YAML 설정만 보고도 타입과 단위를 알 수 있어야 한다**는 실용적 이유로
접미사를 강하게 권장한다고 명시한다. 두 규약이 충돌하는 지점이므로, 조직 안에서 하나를 정해야
한다.</small>

## 4. 카디널리티 — 프로메테우스가 죽는 가장 흔한 방식

**이 절이 이 글에서 가장 중요하다.** 다른 걸 다 잘해도 여기서 한 번에 무너진다.

공식 문서의 경고문을 그대로 옮긴다.

> **CAUTION**: "Remember that every unique combination of key-value label pairs represents a new
> time series, which can dramatically increase the amount of data stored. **Do not use labels to
> store dimensions with high cardinality (many different label values), such as user IDs, email
> addresses, or other unbounded sets of values.**"
> — Prometheus Documentation, Metric and label naming

핵심은 **곱셈**이다. 라벨 조합 하나하나가 별개의 시계열이고, 라벨이 늘면 시계열 수는 더해지는
게 아니라 곱해진다.

구체적인 지침도 문서에 있다.

> "As a general guideline, **try to keep the cardinality of your metrics below 10**, and for
> metrics that exceed that, aim to limit them to a handful across your whole system. The vast
> majority of your metrics should have no labels.
>
> **If you have a metric that has a cardinality over 100 or the potential to grow that large,
> investigate alternate solutions** such as reducing the number of dimensions or moving the
> analysis away from monitoring and to a general-purpose processing system."

문서가 든 숫자 예시가 감을 잡기에 좋다.

> "node_exporter exposes metrics for every mounted filesystem. Every node will have in the tens of
> timeseries for, say, `node_filesystem_avail`. **If you have 10,000 nodes, you will end up with
> roughly 100,000 timeseries** (…) which is fine for Prometheus to handle.
>
> If you were to now add quota per user, **you would quickly reach a double digit number of
> millions with 10,000 users on 10,000 nodes. This is too much** for the current implementation of
> Prometheus."

노드 1만 대의 파일시스템 지표 10만 개는 괜찮다. 거기에 **사용자 축 하나를 더하면 수천만이 되고
감당하지 못한다.** 라벨 하나의 비용이 이렇게 비대칭적이다.

**절대 라벨에 넣지 말아야 할 것:** 사용자 ID, 이메일, 세션 ID, 요청 ID, 주문 번호, 전체 URL
경로(`/user/12345/order/67890`), 에러 메시지 문자열, IP 주소.

**URL 경로는 반드시 라우트 패턴으로 정규화한다.** `/user/{id}/order/{id}` 형태여야 한다.
프레임워크의 자동 계측이 raw path를 쓰고 있지 않은지 반드시 확인할 것 — 이게 실무에서 가장 흔한
카디널리티 폭발 경로다.

그리고 문서의 마지막 조언이 가장 실용적이다.

> "If you are unsure, **start with no labels and add more labels over time as concrete use cases
> arise.**"

## 5. 히스토그램 vs 서머리 — 퍼센타일은 평균 낼 수 없다

여기가 "모두가 틀리는" 지점이다. 공식 문서에 코드 주석까지 달아 놓은 예제가 있다.

```promql
avg(http_request_duration_seconds{quantile="0.95"}) // BAD!
```

> "aggregating the precomputed quantiles from a summary rarely makes sense. In this particular
> case, **averaging the quantiles yields statistically nonsensical values.**"
> — Prometheus Documentation, Histograms and summaries

**서버 10대의 p95를 평균 낸 값은 전체 p95가 아니다.** 그건 어떤 통계량도 아니다. 그런데 이렇게
만들어진 SLO 대시보드가 세상에 아주 많다.

### 구조적 차이

|                      | 히스토그램                                     | 서머리                                 |
| -------------------- | ---------------------------------------------- | -------------------------------------- |
| 분위수 계산 위치     | **프로메테우스 서버** (`histogram_quantile()`) | 계측 대상 프로세스 안                  |
| 계측 비용            | 카운터 증가만 → 쌈                             | 스트리밍 분위수 계산 → 상대적으로 비쌈 |
| **집계**             | **PromQL로 가능**                              | **불가능**                             |
| 나중에 φ·시간창 변경 | 쿼리만 고치면 됨                               | **불가능** (계측 시점에 고정)          |
| 오차의 축            | 관측값 축 (버킷 폭)                            | φ 축 (설정 가능, 매우 낮음)            |

<small>출처: Prometheus Documentation, Histograms and summaries — Quantiles 절의 비교표</small>

올바른 형태는 이렇다.

```promql
-- 클래식 히스토그램
histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket[5m])))  // GOOD.

-- 네이티브 히스토그램
histogram_quantile(0.95, sum(rate(http_request_duration_seconds[5m])))                  // GOOD.
```

### 문서가 말하는 결론은 명확하다

> "The most important lesson to learn from this document is simple: **If you can, use native
> histograms and prefer them over both classic histograms and summaries.**"

클래식 히스토그램은 버킷마다 시계열이 하나씩 생기고("no matter if the bucket is populated or
not"), 버킷 경계를 미리 잘 골라야 하며, 나중에 바꾸면 큰 혼란을 만든다. 네이티브 히스토그램은
버킷 경계 대신 **해상도**만 고르고, 하나의 시계열로 저장된다.

<small>단, 문서는 네이티브 히스토그램 지원이 아직 제한적이라고 명시한다("native histogram support
is still rare"). 클래식 히스토그램을 서버 쪽에서 NHCB(Native Histograms with Custom Bucket
boundaries)로 수집하는 중간 경로도 제공된다.</small>

### 클래식 히스토그램의 조용한 함정

버킷 경계를 지정해 비율을 구하는 쿼리에 대해 문서가 경고한다.

> "Note that this expression **strictly requires a bucket boundary configured at 0.3.** If the
> histograms involved do not have a bucket with that boundary, no interpolation is applied.
> Instead of an estimation, **no result is returned at all.** If only some of the involved
> histograms have such a bucket, **an incomplete result is returned, but without any warning**,
> which is a pretty bad situation to be in."

**경고 없이 불완전한 결과.** 일부 인스턴스만 그 버킷을 갖고 있으면 그 인스턴스들만 집계된 값이
아무 표시 없이 나온다. SLO 대시보드가 조용히 거짓말을 하는 경로다.

### 분위수 추정 오차는 생각보다 크다

문서의 사고실험이 아주 좋다. 실제 요청 시간이 거의 전부 **220ms**에 몰려 있고,
클래식 히스토그램 버킷이 `{le="0.2"}`, `{le="0.3"}`으로 잡혀 있다고 하자.

- 모든 관측이 200–300ms 버킷에 들어가고, 보간으로 추정된 p95는 **295ms**가 된다.
- 참값은 220ms인데, SLO가 300ms라면 **"아슬아슬하게 지키는 중"으로 보인다.**

같은 상황에서 해상도 1.1의 네이티브 히스토그램이면 추정치는 **228ms**로, 참값에 훨씬 가깝다.

> "The bottom line is: **If you use a summary, you control the error in the dimension of φ. If you
> use a histogram, you control the error in the dimension of the observed value.**"

**퍼센타일 그래프의 숫자는 측정값이 아니라 추정값이다.** 이 사실을 모르고 "p95가 295ms니까 아직
괜찮다"고 판단하면 안 된다.

## 6. 저장 — TSDB를 어디에 두느냐가 생존을 가른다

### 구조

- 수집된 샘플은 **2시간 블록**으로 묶인다. 각 블록은 `chunks`, `index`, `meta.json`으로 구성.
- 현재 블록은 메모리에 있고, **WAL(write-ahead log)** 로 크래시에 대비한다. WAL은 `wal`
  디렉터리에 **128MB 세그먼트**로 저장된다.
- 2시간 블록은 백그라운드에서 더 큰 블록으로 컴팩션된다. 최대 크기는 **리텐션의 10% 또는
  31일 중 작은 쪽**.

### 용량 산정

> "Prometheus stores an average of only 1-2 bytes per sample."

```
needed_disk_space = retention_time_seconds × ingested_samples_per_second × bytes_per_sample
```

기본 리텐션은 **15일**(`--storage.tsdb.retention.time`, 크기 제한도 안 걸면 이 값). 크기 제한
`--storage.tsdb.retention.size`는 기본 비활성이고, 둘 다 설정하면 **먼저 걸리는 쪽이 적용**된다.

그리고 크기 제한을 쓸 때의 공식 권장.

> "At present, we recommend setting the retention size to, **at most, 80-85% of your allocated
> Prometheus disk space.**"

수집량을 줄여야 한다면 문서의 우선순위는 명확하다.

> "To lower the rate of ingested samples, you can either reduce the number of time series you
> scrape (…) or you can increase the scrape interval. However, **reducing the number of series is
> likely more effective**, due to compression of samples within a series."

**스크레이프 주기를 늘리는 것보다 시계열 수를 줄이는 게 효과가 크다.** 같은 시계열 안의 샘플은
압축이 잘 되기 때문이다. §4로 돌아간다.

### 절대 하면 안 되는 것

> **CAUTION**: "Non-POSIX compliant filesystems are not supported for Prometheus' local storage as
> **unrecoverable corruptions may happen. NFS filesystems (including AWS's EFS) are not
> supported.** (…) It is strongly recommended to use a local filesystem for reliability."

쿠버네티스에서 PVC를 아무 스토리지클래스로나 잡으면 밟는 함정이다. **NFS 기반 PV에 프로메테우스
TSDB를 올리면 안 된다.**

또한 로컬 스토리지는 **클러스터링도 복제도 안 된다**("not clustered or replicated"). 단일 노드
DB처럼 다뤄야 하고, 장기 보관과 고가용성이 필요하면 remote write로 외부 저장소를 붙여야 한다.
다만 문서는 원격 저장소들이 "vary greatly in durability, performance, and efficiency"라고
경고하므로, 선택 시 신중한 평가가 필요하다.

### 백업

> "**Snapshots are recommended for backups.** Backups made without snapshots run the risk of
> losing data that was recorded since the last TSDB block was created."

WAL 디렉터리(`chunks_head/`, `wal/`, `wbl/`)를 백업에서 제외하면 정합성 있는 백업이 되지만,
그 시간 범위는 잃는다.

## 7. 레코딩 룰 — 비율을 다루는 법

무거운 쿼리를 미리 계산해 두는 게 레코딩 룰이다. 공식 네이밍 규약은
**`level:metric:operations`** 형태다.

- `level` — 집계 수준과 출력 라벨 (`job`, `instance_path` 등)
- `metric` — 원 메트릭 이름 (`rate()`를 쓸 때 `_total`만 떼고 그대로)
- `operations` — 적용한 연산 목록, **최신 연산이 앞**

```yaml
- record: instance_path:requests:rate5m
  expr: rate(requests_total{job="myjob"}[5m])

- record: path:requests:rate5m
  expr: sum without (instance)(instance_path:requests:rate5m{job="myjob"})
```

그리고 **이 글에서 두 번째로 중요한 규칙**이 여기 있다.

> "When aggregating up ratios, **aggregate up the numerator and denominator separately and then
> divide. Do not take the average of a ratio or average of an average, as that is not
> statistically valid.**"
> — Prometheus Documentation, Recording rules

즉 인스턴스별 에러율을 구한 다음 그걸 평균 내면 **틀린다.** 요청 10개 중 1개 실패한 인스턴스와
10,000개 중 100개 실패한 인스턴스를 동등하게 취급하기 때문이다. 올바른 형태:

```yaml
# 분자와 분모를 각각 집계한 뒤 나눈다
- record: path:request_failures_per_requests:ratio_rate5m
  expr: |2
      sum without (instance)(instance_path:request_failures:rate5m{job="myjob"})
    /
      sum without (instance)(instance_path:requests:rate5m{job="myjob"})
```

마지막으로 집계 시 문법 권고.

> "**Always specify a `without` clause** with the labels you are aggregating away. This is to
> preserve all the other labels such as `job`, which will avoid conflicts and give you more useful
> metrics and alerts."

`by`로 남길 걸 나열하는 대신 `without`으로 버릴 걸 나열하라는 뜻이다. **새 라벨이 추가돼도 자동으로
보존되기 때문**이다.

## 8. 경보 철학 — 원인이 아니라 증상에

공식 문서는 Rob Ewaschuk의 글을 권하며 한 문단으로 요약한다.

> "To summarize: **keep alerting simple, alert on symptoms, have good consoles to allow pinpointing
> causes, and avoid having pages where there is nothing to do.**"
> — Prometheus Documentation, Alerting

풀어 쓰면 이렇다.

> "**Aim to have as few alerts as possible**, by alerting on symptoms that are associated with
> end-user pain rather than trying to catch every possible way that pain could be caused. Alerts
> should link to relevant consoles and make it easy to figure out which component is at fault."

### 시스템 유형별 지침

**온라인 서빙 시스템** — 지연과 에러율을, 스택에서 가능한 한 위쪽에서 본다.

> "**Only page on latency at one point in a stack.** If a lower-level component is slower than it
> should be, but the overall user latency is fine, then there is no need to page."
>
> "For error rates, page on user-visible errors. If there are errors further down the stack that
> will cause such a failure, there is no need to page on them separately."

**오프라인 처리** — 데이터가 시스템을 통과하는 데 걸리는 시간이 핵심 지표.

**배치 잡** — 핵심 지표는 **"마지막으로 성공한 시각"** 이다. 그리고 임계치 설정 지침이 구체적이다.

> "This should generally be **at least enough time for 2 full runs of the batch job.** For a job
> that runs every 4 hours and takes an hour, **10 hours would be a reasonable threshold.** If you
> cannot withstand a single run failing, run the job more frequently, as a single failure should
> not require human intervention."

**한 번의 실패가 사람을 부르게 만들면 안 된다**는 원칙이 잡 실행 주기 설계까지 거슬러 올라간다.

**용량** — 즉각적인 사용자 영향은 없지만, 임박한 장애를 막으려면 사람이 개입해야 하므로 경보 대상.

### 작은 튐은 허용하라

> "**Allow for slack in alerting to accommodate small blips.**"

프로메테우스 알림 규칙의 `for` 절이 이걸 위한 장치다. 30초짜리 스파이크로 사람을 깨우지 않는다.

### 알림 이름

> "the community has rallied around using **Camel Case** for their alert names."

`HighErrorRate`, `KubePodCrashLooping` 같은 형태다.

## 9. Alertmanager — 알림 폭탄을 막는 세 가지 장치

프로메테우스는 알림을 **발생**시키고, Alertmanager는 그걸 **묶고, 억제하고, 라우팅**한다.
역할이 나뉘어 있다는 걸 모르면 설정할 곳을 못 찾는다.

### Grouping — 하나의 사건을 하나의 알림으로

> "Example: Dozens or hundreds of instances of a service are running in your cluster when a network
> partition occurs. Half of your service instances can no longer reach the database. (…) **As a
> result hundreds of alerts are sent to Alertmanager.** As a user, one only wants to get a single
> page while still being able to see exactly which service instances were affected."
> — Alertmanager Documentation

`cluster`와 `alertname`으로 그룹핑하면 수백 개가 **하나의 압축된 알림**이 된다.

### Inhibition — 큰 게 터졌으면 작은 건 조용히

> "Inhibition is a concept of suppressing notifications for certain alerts if certain other alerts
> are already firing. Example: An alert is firing that informs that an entire cluster is not
> reachable. Alertmanager can be configured to **mute all other alerts concerning this cluster**."

클러스터 전체가 죽었는데 그 안의 개별 서비스 알림 300개를 같이 받는 건 무의미하다.

### Silences — 계획된 정비 중 음소거

매처 기반으로 일정 시간 음소거한다. Alertmanager 웹 UI에서 설정한다.

### HA 운영에서 자주 틀리는 것

> "It's important **not to load balance traffic between Prometheus and its Alertmanagers**, but
> instead, point Prometheus to a list of all Alertmanagers."

**Alertmanager 앞에 로드밸런서를 두면 안 된다.** 프로메테우스가 모든 Alertmanager에 알림을 보내고,
Alertmanager 클러스터가 자기들끼리 중복 제거를 한다. LB를 두면 이 구조가 깨진다.

## 10. 대시보드 — 무엇을 그릴지부터 정한다

Grafana 공식 문서는 세 가지 관측 전략을 제시한다.

| 전략                    | 구성                                 | 대상                        | 성격                          |
| ----------------------- | ------------------------------------ | --------------------------- | ----------------------------- |
| **USE**                 | Utilization, Saturation, Errors      | 하드웨어·인프라 자원        | **원인**을 보고               |
| **RED**                 | Rate, Errors, Duration               | 서비스(특히 마이크로서비스) | **사용자 경험 = 증상**을 보고 |
| **Four Golden Signals** | Latency, Traffic, Errors, Saturation | 사용자 대면 시스템          | RED + Saturation              |

그리고 두 방법의 관계를 한 문장으로 정리한 게 아주 좋다.

> "**The USE method tells you how happy your machines are, the RED method tells you how happy your
> users are.** USE reports on causes of issues. RED reports on user experience and is more likely
> to report symptoms of problems. The best practice of alerting is to alert on symptoms rather than
> causes, so **alerting should be done on RED dashboards.**"
> — Grafana Documentation, Dashboard best practices

§8의 프로메테우스 경보 철학과 정확히 맞물린다. **경보는 RED에서, 원인 추적은 USE에서.**

### 대시보드를 만들기 전에 물어야 할 것

> "**A dashboard should tell a story or answer a question.** (…) What is the goal for this
> dashboard? (Hint: **If the dashboard doesn't have a goal, then ask yourself if you really need
> the dashboard.**)"
>
> "**Dashboards should reduce cognitive load, not add to it.** (…) Make your dashboard easy to
> interpret. Other users and future you (when you're trying to figure out what broke at 2 AM) will
> appreciate it."

### 실무 규칙

- 패널마다 **설명(description)을 단다.** 대시보드 자체 설명은 Text 패널로.
- 단위나 범위가 다른 시계열은 **좌/우 Y축을 나눠 쓴다.**
- 데이터가 1시간마다 바뀌는데 **30초 새로고침을 걸지 않는다.** 네트워크와 백엔드에 부담만 준다.
- **스택 그래프는 대부분 끄는 게 낫다.** "The visualizations can be misleading, and hide
  important data."
- CPU 같은 지표는 **정규화**한다. 코어 수가 다른 머신을 절대값으로 비교하면 안 된다.
- 실험용 대시보드는 이름에 `TEST:` / `TMP:`를 붙이고, 끝나면 지운다.

## 11. 대시보드 스프롤 — 성숙도 모델로 자가진단

Grafana 문서의 **대시보드 관리 성숙도 모델**은 자기 조직을 진단하기에 유용하다.

**낮음 (기본 상태 — "거의 모두가 여기서 시작한다")**

- 누구나 대시보드를 수정할 수 있다
- 복사된 대시보드가 잔뜩, 재사용은 거의 없음
- 일회용 대시보드가 영원히 남아 있음
- 버전 관리 없음
- **원하는 대시보드를 찾느라 시간을 낭비한다**
- 알림이 올바른 대시보드로 안내해주지 않는다

**중간 (체계적 대시보드)**

- **템플릿 변수로 스프롤을 방지한다.** 노드마다 대시보드를 만들지 않고 쿼리 변수를 쓴다.
  데이터소스 자체도 변수로 만들면 클러스터가 달라도 같은 대시보드를 쓸 수 있다.
- 서비스 계층을 반영한 계층적 대시보드, 드릴다운
- 대시보드 JSON을 버전 관리

**높음 (최적화된 운영)**

- 스프롤을 **능동적으로** 줄인다 — 정기 리뷰, 승인된 대시보드만 마스터 목록에
- **스크립팅 라이브러리로 대시보드를 생성**해 패턴과 스타일의 일관성을 강제 (grafonnet, grafanalib)
- **브라우저에서 편집하지 않는다.** 보는 사람은 변수로 뷰를 바꾼다.
- 대시보드를 "찾아 헤매는" 것이 예외적인 일
- 실험은 **운영 인스턴스가 아닌 별도 인스턴스**에서

그리고 복사에 대한 경고가 날카롭다.

> "Copying dashboards with no significant changes is not a good idea. **You miss out on updates to
> the original dashboard**, such as documentation changes, bug fixes, or additions to metrics. In
> many cases copies are being made to simply customize the view by setting template parameters.
> **This should instead be done by maintaining a link to the master dashboard and customizing the
> view with URL parameters.**"

## 12. 프로비저닝 — 대시보드를 코드로

> "Grafana has an active provisioning system that uses configuration files. **You can define data
> sources and dashboards using files that can be version controlled, making GitOps more natural.**"
> — Grafana Documentation, Provision Grafana

`provisioning/datasources/*.yaml`에 데이터소스를, `provisioning/dashboards/`에 대시보드를 둔다.
파일에서 제거된 데이터소스를 자동으로 지우려면 루트에 `prune: true`.

### 여러 인스턴스를 돌린다면 `version`을 붙여라

> "If you run multiple instances of Grafana, **add a version number to each data source** in the
> configuration and increase it when you update the configuration. Grafana only updates data
> sources with the same or lower version number (…) **This prevents old configurations from
> overwriting newer ones.**"

### 그리고 아주 잘 밟는 지뢰 — `$` 문자

환경 변수 치환 규칙 때문에, 비밀번호에 `$`가 들어가면 **조용히 잘린다.**

```yaml
# PASSWORD=Pa$sw0rd 일 때
password1: $PASSWORD # → Pa$sw0rd  (정상)
password2: ${PASSWORD} # → Pa        # $sw0rd가 또 다른 변수로 해석됨!
password3: "Pa$$sw0rd" # → Pa$sw0rd  (리터럴은 $$로 이스케이프)
password4: "Pa$sw0rd" # → Pa
```

> "Grafana's provisioning system considers **any set of characters after an `$` a variable name.**"

`${VAR}` 문법이 더 안전해 보여서 그렇게 썼는데 인증이 실패한다면, 십중팔구 이것이다. 원인이
전혀 드러나지 않는 종류의 버그다.

### 환경 변수 사용 범위

> "Only use environment variables **for configuration values.** Do not use it for keys or bigger
> parts of the configuration file structure."
>
> "Use environment variables in dashboard provisioning **configuration**, but **not in the
> dashboard definition files themselves.**"

## 13. 마지막 — 모니터링을 모니터링하라

가장 자주 빠지는 항목이다. **모니터링 시스템이 죽으면 아무 알림도 오지 않는다.** 조용하다는 게
평화롭다는 뜻이 아니다.

> "**It is important to have confidence that monitoring is working.** Accordingly, have alerts to
> ensure that Prometheus servers, Alertmanagers, PushGateways, and other monitoring infrastructure
> are available and running correctly.
>
> As always, if it is possible to alert on symptoms rather than causes, this helps to reduce noise.
> For example, **a blackbox test that alerts are getting from PushGateway to Prometheus to
> Alertmanager to email is better than individual alerts on each.**
>
> **Supplementing the whitebox monitoring of Prometheus with external blackbox monitoring** can
> catch problems that are otherwise invisible, and also serves as a fallback in case internal
> systems completely fail."
> — Prometheus Documentation, Alerting

두 가지 실천이 나온다.

1. **엔드투엔드 합성 알림.** 개별 컴포넌트를 각각 감시하는 것보다, **주기적으로 더미 알림을
   흘려보내고 그게 실제로 도착하는지** 확인하는 게 낫다.
2. **외부에서 보는 블랙박스 모니터링.** 프로메테우스와 같은 클러스터 안에 있는 감시자는 그
   클러스터가 통째로 죽으면 같이 죽는다. **감시자는 감시 대상 밖에 있어야 한다.**

---

## 한 줄씩 다시

1. 프로메테우스는 정확성보다 가용성 — **과금 데이터는 다른 걸 쓴다**
2. 값이 내려갈 수 있으면 gauge, gauge에 `rate()`는 금지
3. 초·바이트·0–1 ratio, 카운터엔 `_total` — `sum()`이나 `avg()`가 의미 있어야 한다
4. **user_id를 라벨에 넣지 마라** — 라벨은 더해지는 게 아니라 곱해진다
5. **퍼센타일은 평균 낼 수 없다** — 서머리는 집계 불가, 히스토그램을 써라
6. **NFS/EFS에 TSDB를 두지 마라** — 시계열 줄이기가 주기 늘리기보다 효과적
7. 비율은 **분자·분모를 따로 집계한 뒤 나눈다** — 비율의 평균은 틀린 값
8. **증상에 경보하고, 스택 한 지점에서만 페이지한다** — 할 일 없는 페이지는 만들지 않는다
9. Grouping·Inhibition·Silence — Alertmanager 앞에 LB 금지
10. **경보는 RED에서, 원인 추적은 USE에서**
11. 복사하지 말고 템플릿 변수를 써라 — JSON은 버전 관리
12. 프로비저닝 비밀번호의 `$`는 `$$`로 이스케이프
13. **감시자는 감시 대상 밖에 있어야 한다**

---

## 이 글의 한계

1. **Prometheus 공식 문서(현행판)와 Grafana 공식 문서(latest) 기준이다.** 버전에 따라 기본값과
   기능이 다를 수 있다.
2. **Thanos·Mimir·VictoriaMetrics 등 장기 저장·수평 확장 계층은 다루지 않았다.** 확인하지 않은
   것에 대해 쓰지 않았다.
3. **성능 비교나 벤치마크 수치는 일절 인용하지 않았다.** 이 영역은 중립적 제3자 벤치마크가
   빈약하고, 벤더 자체 수치를 사실처럼 옮기는 것은 이 글의 원칙에 어긋난다.
4. **§4의 "라벨에 넣지 말아야 할 목록", §10~11의 실무 규칙 일부, §13의 두 가지 실천은 공식 문서의
   원칙에서 끌어낸 내 판단이다.** 인용문이 붙지 않은 문장은 그렇게 읽어야 한다.
5. **직접 부하 테스트를 돌린 결과가 아니다.** 카디널리티 수치는 공식 문서가 제시한 예시다.

---

## References

**① 1차·공식 (Prometheus Documentation)**

- Overview — "When does it fit? / When does it not fit?", 아키텍처와 구성 요소
  <https://prometheus.io/docs/introduction/overview/>
- Instrumentation — counter/gauge 판별, 라벨 과용 경고와 node_exporter 카디널리티 예시,
  타임스탬프 vs 경과시간, 기본값 0 노출
  <https://prometheus.io/docs/practices/instrumentation/>
- Metric and label naming — 접두사·단일 단위·기본 단위·`_total` 규약, 고카디널리티 CAUTION,
  기본 단위 표
  <https://prometheus.io/docs/practices/naming/>
- Histograms and summaries — `avg(...{quantile="0.95"}) // BAD!`, 히스토그램/서머리 비교표,
  분위수 추정 오차, 클래식 히스토그램의 무경고 불완전 결과, 네이티브 히스토그램 권장
  <https://prometheus.io/docs/practices/histograms/>
- Recording rules — `level:metric:operations` 규약, 비율 집계 규칙, `without` 절 권고
  <https://prometheus.io/docs/practices/rules/>
- Alerting — 증상 기반 경보, 시스템 유형별 지침, 배치 잡 2회 실행분 임계치, 메타모니터링
  <https://prometheus.io/docs/practices/alerting/>
- Storage — TSDB 온디스크 구조, 샘플당 1–2바이트, 용량 공식, 기본 리텐션 15d,
  리텐션 크기 80–85% 권장, NFS/EFS 미지원 CAUTION, 스냅샷 백업, remote read/write
  <https://prometheus.io/docs/prometheus/latest/storage/>
- Alertmanager — Grouping / Inhibition / Silences, HA에서 LB 금지
  <https://prometheus.io/docs/alerting/latest/alertmanager/>

**② 1차·공식 (Grafana Documentation)**

- Dashboard best practices — USE / RED / Four Golden Signals, 대시보드 관리 성숙도 모델,
  대시보드 작성·관리 실무 규칙
  <https://grafana.com/docs/grafana/latest/dashboards/build-dashboards/best-practices/>
- Introduction to Grafana Alerting — 알림 규칙·인스턴스·컨택트 포인트·알림 정책·Silence
  <https://grafana.com/docs/grafana/latest/alerting/fundamentals/>
- Provision Grafana — 데이터소스/대시보드 프로비저닝, `version` 필드, `$` 이스케이프 규칙
  <https://grafana.com/docs/grafana/latest/administration/provisioning/>

**③ 공식 문서가 2차로 참조한 자료 (원문 확인 권장)**

- Rob Ewaschuk, "My Philosophy on Alerting" — Prometheus 알림 문서가 권하는 원전
- Google SRE Book — Four Golden Signals의 출처
- Tom Wilkie, "The RED Method" — Grafana 문서가 인용한 원전

<small>③은 이 글에서 원문을 직접 읽고 인용한 것이 아니라, ①·② 공식 문서가 참조 대상으로 지목한
자료다. 해당 방법론을 깊이 다루려면 원문을 직접 확인해야 한다.</small>
