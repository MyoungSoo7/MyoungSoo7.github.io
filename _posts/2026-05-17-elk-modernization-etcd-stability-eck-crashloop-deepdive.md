---
layout: post
title: "K3s 홈랩 하루치 운영기 — Logstash 파이프라인, etcd leader 안정화, ECK 크래시 디버깅"
date: 2026-05-17 23:30:00 +0900
categories: [infra, kubernetes]
tags: [kubernetes, k3s, eck, logstash, kibana, elasticsearch, gitops, argocd, etcd, troubleshooting, postmortem]
---

ELK 학습 목표 5가지 — *구축 / 자동 수집 / Logstash 변환 / ES 고급 집계 / Kibana 대시보드* — 를 한 번에 끝내려고 시작한 하루였는데, 중간에 클러스터 부하 spike·etcd leader 변동·ECK operator 크래시 루프까지 줄줄이 만나서 결국 종합적인 운영 회고가 됐다.

이 글은 그 하루(2026-05-17)에 손댄 것들 중 **포트폴리오로 의미 있는 다섯 주제**를 추려서 정리한다. *왜 했나 → 어떻게 했나 → 시행착오 → 배운 점* 순서로.

> ⚠️ 보안 — 이 글에는 클러스터 IP·비밀번호·토큰은 포함되지 않는다. 실제 운영 식별자는 `<redacted>` 또는 generic 명칭으로 대체.

---

## TL;DR — 다섯 주제 한눈에

| # | 주제 | 결과 | 핵심 배움 |
|---|---|---|---|
| 1 | Fluent Bit → **Logstash** → ES 파이프라인 전환 | ✅ ECK Logstash CRD 로 가동 | 시행착오 4번 = `ssl_verification_mode`/`readinessProbe`/`case-sensitive 매핑`/`dest 인덱스명 충돌` |
| 2 | **Kibana 대시보드** 6개 + GitOps 자동 import | ✅ NDJSON 단일 소스, helm Job 으로 import | UI 편집 → export → git push 워크플로우가 진실 소스 |
| 3 | ES **고급 검색·집계** (ILM + 템플릿 + Transform) | ✅ raw 98k events → summary 401 rows | `transform` role 노드 필요. data_stream 충돌 회피 위해 dest 이름 분리 |
| 4 | etcd **raft leader 안정화** (lemuel → ilwon) | ✅ 매일 04:00 cron 으로 자동 재고정 | scheduler 메시지의 "Insufficient memory" 는 거짓말일 수 있음. node 라벨도 거짓말일 수 있음 |
| 5 | ECK operator **crash loop** 디버깅 (못 고침) | 🟡 부분 완화만, 영향 무해 판정 | "고치지 못함" 도 정확한 진단이면 valid한 결론 |

전체 변경: helm-deploy 레포에 commit **9개**, blog/ops 자산 **4개 파일** 신설.

---

## 1. Fluent Bit → Logstash → ES 파이프라인 전환

### 1.1 왜 Logstash 를 추가했나

기존 구성:

```
Fluent Bit (DaemonSet, 5 노드) ──► Elasticsearch (직접 HTTP)
```

Fluent Bit 의 `[OUTPUT] Name es` 가 ES 에 곧장 적재. 빠르고 단순한데 변환·라우팅이 약하다 — grok 패턴 같은 정규화 DSL 이 없고 conditional output 도 빈약.

학습 목표가 *"Logstash 를 활용하여 로그를 수집, 변환, 적재"* 였으니 중간에 Logstash 를 끼워 넣는 게 본 과제.

### 1.2 새 구조

```
Fluent Bit (DaemonSet)
       │ HTTP POST json_lines
       ▼
Logstash (ECK Logstash CRD, 1 replica)
       │ filter: grok / mutate / translate / drop
       │ output: ES bulk
       ▼
Elasticsearch  (별도 인덱스 패턴 logstash-k8s-*)
```

기존 `logs-k8s-*` 는 그대로 보존해 ILM 으로 자연 만료 — 호환 충격 제로.

### 1.3 ECK Logstash CRD 의 깔끔함

ECK 2.10+ 부터 `kind: Logstash` CRD 가 추가됐다. ES, Kibana 와 같은 패턴.

```yaml
apiVersion: logstash.k8s.elastic.co/v1alpha1
kind: Logstash
metadata:
  name: logs
  namespace: logging
spec:
  count: 1
  version: "8.16.1"
  elasticsearchRefs:
    - name: logs           # 같은 ns 의 Elasticsearch CR 이름
      clusterName: logs    # ECK 가 env 주입 시 prefix 로 사용 → ${LOGS_ES_HOSTS}
  pipelines:
    - pipeline.id: main
      config.string: |
        input  { http { port => 8080  codec => json } }
        filter { ... }
        output { elasticsearch { hosts => ["${LOGS_ES_HOSTS}"] ... } }
```

`elasticsearchRefs` 만 선언하면 ECK 가 자동으로 SA·인증서·env vars(`<CLUSTER>_ES_HOSTS`, `_ES_USER`, `_ES_PASSWORD`, `_ES_SSL_CERTIFICATE_AUTHORITY`) 를 주입. 사용자가 인증 정보 손댈 필요 없음.

### 1.4 시행착오 4번 (commit 단위)

GitOps 레포에 다음 4 개 commit 으로 기록됨. 각자 별도의 함정.

#### (a) `ssl_verification_mode => "certificate"` — invalid value

Logstash ES output 의 SSL 검증 모드는 `[full|none]` 둘만 허용. `"certificate"` 는 ES 자체 옵션이라 헷갈렸음.

```
[ERROR] Invalid setting for elasticsearch output plugin:
  Expected one of ["full", "none"], got ["certificate"]
```

→ `"full"` 로 수정. 그러면 hostname + CA 검증 둘 다 활성화.

#### (b) Readiness probe 가 HTTP input 포트를 HTTPS 로 친다

ECK 가 자동 생성하는 readiness probe 가 우리 service 의 첫 port (8080) 에 HTTPS GET 시도. 우리는 plain HTTP input → probe 영원히 실패 → pod Ready=false → service endpoint 등록 안 됨 → Fluent Bit "no upstream connections available".

```yaml
podTemplate:
  spec:
    containers:
      - name: logstash
        readinessProbe:
          tcpSocket:
            port: 9600        # Logstash API 포트 (TCP 만 확인)
```

→ 명시적으로 override.

#### (c) level 매핑 case-sensitive

Logstash `translate` 필터 사전:

```ruby
dictionary => { "INFO" => "30", "ERROR" => "50", ... }
```

근데 Spring Boot 는 `INFO` 대문자 보내고 klog/controller 들은 `info` 소문자 보냄. case-sensitive 매칭이라 소문자는 fallback `0` 으로 떨어짐.

→ `mutate { uppercase => [ "level" ] }` 로 정규화 후 매핑. `WARNING` (klog 가 사용) 도 dictionary 에 추가.

#### (d) 출력 인덱스명이 기존 data_stream 패턴과 충돌

처음엔 `logstash-k8s-YYYY.MM.dd` 로 적재하려 했더니 기존 `logs-k8s` 인덱스 템플릿(data_stream 강제) 패턴 `logs-*-*` 에 매칭돼 *"Could not create destination index"* 오류.

→ destination 이름을 `k8s-events-summary` 로 분리. raw 데이터는 `logstash-k8s-*`, summary 는 `k8s-events-summary` — pattern 충돌 회피.

### 1.5 데이터 평탄화 + 노이즈 drop 필터

```ruby
filter {
  # 1) k8s 메타 평탄화 — Kibana 검색 편하게
  if [kubernetes] {
    mutate {
      add_field => {
        "[k8s_namespace]" => "%{[kubernetes][namespace_name]}"
        "[k8s_pod]"       => "%{[kubernetes][pod_name]}"
        "[k8s_container]" => "%{[kubernetes][container_name]}"
      }
    }
  }

  # 2) level → severity 숫자 (case-insensitive)
  if [level] {
    mutate { uppercase => [ "level" ] }
    translate {
      source => "[level]"
      target => "[level_num]"
      dictionary => {
        "TRACE" => "10"  "DEBUG" => "20"  "INFO" => "30"
        "WARN"  => "40"  "WARNING" => "40"
        "ERROR" => "50"  "FATAL" => "60"
      }
      fallback => "0"
    }
    mutate { convert => { "[level_num]" => "integer" } }
  }

  # 3) Exception class 추출 — 알림·검색 편하게
  if [level] in ["ERROR", "FATAL"] or [message] =~ "Exception|Traceback" {
    grok {
      match => { "message" => "(?<exception_first>%{JAVACLASS:exception_class}(:\s*%{DATA:exception_msg})?)" }
      tag_on_failure => []
    }
  }

  # 4) 시끄러운 헬스체크 drop
  if [message] =~ "/actuator/health" or [message] =~ "/metrics" {
    drop {}
  }
}
```

### 1.6 결과 (적용 30분 후)

- Logstash pipeline `events.in=378, out=376, filtered=376` — 정상 흐름
- ES 인덱스 `logstash-k8s-YYYY.MM.dd` 자동 생성, 301 docs 첫 5분
- 샘플 문서 top-level: `@timestamp, cluster_id, k8s_namespace, k8s_pod, k8s_container, level, level_num, received_at, ...`

Fluent Bit 의 record_modifier 가 박은 `cluster_id` 도 보존됨 — Logstash 가 의미 있는 변환만 추가하고 원본은 깨끗하게 유지.

---

## 2. Kibana 대시보드 6개 + GitOps 자동 import

### 2.1 0개에서 6개로

Logstash 가 적재만 잘 해도 Kibana 에 대시보드가 없으면 "지나가는 로그" 일 뿐. 운영 가시화의 핵심은 시각화.

**구성한 6 패널** (모두 Lens 시각화):

| 패널 | 타입 | 핵심 인사이트 |
|---|---|---|
| Total Events (24h) | Metric | 24시간 누적 적재량 — 트래픽 sanity check |
| Severity distribution | Donut | INFO/WARN/ERROR 비율 — 정상성 |
| Log volume over time | Area | 시간별 볼륨 — 트래픽 패턴 |
| Events per Namespace top 10 | Bar | 가장 시끄러운 ns — 라우팅 후보 |
| ERROR + FATAL over time | Line | severity ≥ 50 추이 — incident 감지 |
| Top error pods 15 | DataTable | 에러 많은 (ns, pod) — 즉시 조치 대상 |

### 2.2 GitOps 자동 import

수동 클릭으로 만들면 일회용. 핵심 패턴 — *Kibana 의 NDJSON export 파일을 git 에 넣고 매 sync 마다 import.*

```
charts/elk-cluster/
├── dashboards/
│   ├── README.md                       ← 업데이트 절차
│   └── k8s-logs-overview.ndjson        ← 진실 소스
└── templates/
    └── dashboards-importer.yaml        ← ConfigMap + Job
```

**중요 디테일**:

- `.Files.Glob "dashboards/*.ndjson"` 로 차트가 모든 NDJSON 자동 발견 — 새 대시보드 추가 시 코드 수정 0
- Job 이 Kibana `_import?overwrite=true` 호출 — `overwrite=true` 가 GitOps 핵심. UI 변경은 다음 sync 때 원복
- `--form file=@$f` 로 multipart 업로드 (Kibana saved-objects API 의 표준)

**워크플로우 (UI 편집 → Git push)**:

1. Kibana UI 에서 자유롭게 편집
2. Stack Management → Saved Objects → 체크 → **Export** (`Include related objects` ON)
3. 받은 NDJSON 으로 `dashboards/k8s-logs-overview.ndjson` 덮어씀
4. `git push` → ArgoCD sync → Job 재실행 → 1분 내 적용

이게 정착되면 "디자이너처럼 UI 에서 만들고 코드처럼 git 에 저장한다" 라는 깔끔한 흐름이 됨.

---

## 3. ES 고급 검색·집계 — ILM + 컴포넌트/인덱스 템플릿 + Transform

### 3.1 dynamic mapping 의 위험

처음엔 `logstash-k8s-YYYY.MM.dd` 가 dynamic mapping 으로 그냥 생성됐다. ES 가 알아서 추론하는 건 편하지만 단점이 3개:

1. **숫자 vs 텍스트 추론 실수** — `level_num` 이 `long` (8 byte) 으로 잡힐 수 있음. `byte` (1 byte) 면 충분.
2. **모든 keyword 가 multi-field (`text + .keyword`)** — 메모리 낭비. 우리는 aggregation 만 필요.
3. **ILM 미적용** — 인덱스가 무한정 쌓이고 hot/warm/cold 라우팅 안 됨.

→ 명시 매핑 + ILM 정책을 한 번에 적용해야 한다.

### 3.2 ILM 정책 — hot 7d → warm 14d → cold 30d → delete 60d

```json
{
  "policy": {
    "phases": {
      "hot":  { "min_age": "0ms",  "actions": {
        "rollover": { "max_age": "7d", "max_primary_shard_size": "30gb" },
        "set_priority": { "priority": 100 }
      }},
      "warm": { "min_age": "7d",   "actions": {
        "set_priority": { "priority": 50 },
        "allocate":    { "include": { "_tier_preference": "data_warm" } },
        "forcemerge":  { "max_num_segments": 1 }
      }},
      "cold": { "min_age": "30d",  "actions": {
        "set_priority": { "priority": 10 },
        "allocate":    { "include": { "_tier_preference": "data_cold" } }
      }},
      "delete": { "min_age": "60d", "actions": { "delete": {} } }
    }
  }
}
```

핵심 효과:
- 7일 이후 `forcemerge` 로 세그먼트 1 개로 합쳐 검색 속도 ↑
- 30일 이후 cold 노드 (큰 HDD) 로 이전 → 비싼 NVMe 공간 회수
- 60일 자동 삭제 — 디스크 무한증가 방지

### 3.3 Transform — continuous aggregation

raw 데이터 (수백만 docs/day) 를 매 분 집계해 요약 인덱스 유지. 대시보드/알림이 raw 안 스캔.

```json
{
  "source": { "index": ["logstash-k8s-*"] },
  "dest":   { "index": "k8s-events-summary" },
  "frequency": "1m",
  "sync": { "time": { "field": "@timestamp", "delay": "60s" } },
  "pivot": {
    "group_by": {
      "hour":          { "date_histogram": { "field": "@timestamp", "calendar_interval": "1h" } },
      "k8s_namespace": { "terms": { "field": "k8s_namespace.keyword" } },
      "level":         { "terms": { "field": "level.keyword", "missing_bucket": true } }
    },
    "aggregations": {
      "events":       { "value_count": { "field": "@timestamp" } },
      "max_severity": { "max":         { "field": "level_num" } }
    }
  }
}
```

**1차 검증**: raw 98,583 events → summary 401 rows. **244배 압축**. "namespace 별 1시간당 ERROR" 쿼리가 사실상 즉답.

### 3.4 시행착오 — Transform 의 함정

#### (a) `transform` role 누락

처음 Transform PUT 시:
```
"Transform requires the transform node role for at least 1 node, found no transform nodes"
```

ES 노드 role 을 명시적으로 선언했더니 (`master, data_hot, data_content, ingest, remote_cluster_client`) `transform` 이 빠져있었음. → hot 노드에 `transform` 추가.

(하지만 ECK 가 클러스터 yellow 상태에선 hot 노드 재시작 안 함 — `if_yellow_only_restart_upgrading_nodes_with_unassigned_replicas` 안전 predicate. 강제 재시작 필요했음.)

#### (b) `k8s_namespace` text 필드에 terms 집계 → fielddata 에러

```
Fielddata is disabled on [k8s_namespace] in [logstash-k8s-2026.05.17].
Text fields are not optimised for operations that require per-document field data...
```

기존 dynamic mapping 으로 만들어진 인덱스는 `k8s_namespace` 가 multi-field `text + keyword`. Transform 쿼리에서 `field: "k8s_namespace"` (text) 가 아니라 `field: "k8s_namespace.keyword"` 명시해야 함. → 수정 + 새 컴포넌트 템플릿도 multi-field 로 통일해 이전·이후 호환.

#### (c) dest 인덱스명이 다른 템플릿에 매칭됨

`logs-k8s-summary` 라는 destination 이름 → 기존 `logs-k8s` 인덱스 템플릿(data_stream 강제) 에 매칭 → Transform 이 일반 인덱스로 생성 못함. → `k8s-events-summary` 로 변경.

### 3.5 운영자가 알아두면 좋은 명령

```bash
GET logstash-k8s-*/_ilm/explain
# 각 인덱스의 phase, 다음 액션, 남은 시간

GET _transform/logs-k8s-daily-summary/_stats
# state, operations_behind, documents_processed/indexed
```

`operations_behind` 가 계속 늘면 transform 이 못 따라가는 중 — search 속도가 ingestion 보다 느린 상태. 알람 걸기 좋은 지표.

---

## 4. etcd raft leader 안정화 — 부하는 가벼운 노드로

### 4.1 발견 — 4코어 노드 load5=3.96

평소엔 잠잠하던 control-plane 노드 하나가 load average 4 수준 (4코어 = 100% 포화) 으로 치솟고 있었음. ELK + settlement migration + ArgoCD sync 가 동시에 돈 게 트리거였지만, 진짜 원인은 더 깊이 있었음.

### 4.2 잘못된 길 — "디스크가 HDD 라서"

처음 진단: "이 노드 라벨에 `storage-tier=hdd` 박혀있네. etcd 가 HDD 위에서 도니까 fsync 가 느려서 그렇겠지" — 그럴듯한 가설이라 사용자도 동의.

근데 노드 들어가서 확인했더니:

```bash
$ cat /sys/block/sda/queue/rotational
0                                   # 0 = SSD, 1 = HDD
$ # node-exporter info
node_disk_info{model="SAMSUNG_MZNLN512", ...}    # Samsung SATA SSD
```

**라벨이 거짓말이었다.** 노드는 SATA SSD. 라벨 `hdd` 는 옛날에 누가 잘못 박은 잔재. fsync 가 진짜 느린 게 아니었음.

> **운영 인사이트**: 노드 라벨은 메타데이터이지 진실이 아니다. 의심되면 OS 레벨에서 확인하자.

### 4.3 진짜 원인 — CPU 4코어 + etcd raft leader + kubeconfig 기본 endpoint

세 가지가 겹친 결과:

1. **CPU 4코어** — 5 노드 중 가장 약함. 다른 control-plane 은 8/12 코어.
2. **etcd raft leader** — 25일째 무중단 가동이라 leader 였음. 모든 write proposal 이 여기로 집중.
3. **kubeconfig 기본 endpoint** — `~/.kube/config` 가 이 노드를 가리킴 → kubectl/helm/ArgoCD 모든 트래픽이 여기로 우선.

### 4.4 해결 단계

#### Step 1 — kubeconfig endpoint 전환

```bash
cp ~/.kube/config ~/.kube/config.bak.$(date +%Y%m%d-%H%M%S)
sed -i.tmp 's|server: https://<weak-node-ip>:6443|server: https://<beefy-node-ip>:6443|' ~/.kube/config
```

cert SAN 에 3개 마스터 IP 모두 포함돼있어 TLS 문제 없음. **load5 3.96 → 1.88 (즉시 절반).**

#### Step 2 — etcd leader 이전

먼저 ilwon 에 `etcd-client` 설치 (alpine 패키지) — k3s 는 etcdctl 번들 안 함. 그 다음:

```bash
# 현재 leader 확인
ETCDCTL_API=3 etcdctl --endpoints=https://127.0.0.1:2379 \
  --cacert=/var/lib/rancher/k3s/server/tls/etcd/server-ca.crt \
  --cert=/var/lib/rancher/k3s/server/tls/etcd/server-client.crt \
  --key=/var/lib/rancher/k3s/server/tls/etcd/server-client.key \
  endpoint status --cluster -w table

# leader 이전 — target 이 이미 leader 면 no-op 으로 성공
etcdctl ... move-leader <target-member-id>
```

`Leadership transferred from X to Y` — RAFT TERM 한 단계 증가. **load5 1.88 → 1.82.**

#### Step 3 — 매일 04:00 KST cron 으로 재고정

leader 는 노드 재부팅·네트워크 단절·CPU spike 시 재선거됨. 한 번 옮겨도 다음 재선거 때 약한 노드로 돌아갈 수 있음. 매일 자동 재고정:

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: etcd-leader-pin
spec:
  schedule: "0 4 * * *"
  timeZone: Asia/Seoul
  jobTemplate:
    spec:
      template:
        spec:
          nodeSelector:
            kubernetes.io/hostname: <beefy-node>     # etcd 인증서가 거기 있음
          securityContext: { runAsUser: 0 }          # hostPath cert read
          containers:
            - name: pinner
              image: alpine:3.20
              command: [/bin/sh, -c]
              args:
                - |
                  apk add --no-cache --quiet curl
                  ETCD_VER=v3.5.16
                  curl -fsSL "https://github.com/etcd-io/etcd/releases/download/${ETCD_VER}/etcd-${ETCD_VER}-linux-amd64.tar.gz" | tar xz
                  install -m 0755 etcd-${ETCD_VER}-linux-amd64/etcdctl /usr/local/bin/etcdctl

                  EP="--endpoints=https://<cp-1>:2379,https://<cp-2>:2379,https://<cp-3>:2379"
                  CERTS="--cacert=/etcd-certs/server-ca.crt ..."

                  TARGET=$(ETCDCTL_API=3 etcdctl $EP $CERTS member list \
                           | grep -E ', <beefy-node>-' | awk -F, '{gsub(/ /,"",$1); print $1}')
                  ETCDCTL_API=3 etcdctl $EP $CERTS move-leader "$TARGET"
              volumeMounts:
                - { name: etcd-certs, mountPath: /etcd-certs, readOnly: true }
          volumes:
            - name: etcd-certs
              hostPath: { path: /var/lib/rancher/k3s/server/tls/etcd, type: Directory }
```

**핵심 트릭**:
- `move-leader` 는 target 이 이미 leader 면 no-op (`Leadership transferred from X to X`) 으로 *성공* 응답 → 매일 무조건 실행해도 안전
- member ID 를 hardcode 안 함 — `member list` 에서 prefix grep 으로 동적 조회 (노드 재설치 시 ID 바뀜)
- 가벼운 alpine 에 런타임 etcdctl 다운로드 — bitnami/etcd 는 archived, quay.io/coreos/etcd 는 distroless 라 sh 없음 (가장 깔끔한 차선)

### 4.5 보너스 — WiFi 위 etcd 의 함정

다음날 확인했더니 leader 가 또 바뀜. 이번엔 *제 3 의 control-plane* 노드가 leader. 그 노드는 VXLAN 이 **WiFi 위**에서 도는 노드:

```bash
ip -d link show flannel.1
# vxlan id 1 local <ip> dev wlp3s0b1 ...  ← WiFi 인터페이스
```

WiFi 위 etcd leader → API write latency 폭증 → ECK operator 같은 lease-renewal 의존 컨트롤러가 줄줄이 crash. *제 4 의 노드 (가벼운 노드) 부하 spike 의 일등 공신.*

> **운영 인사이트**: 홈랩에서도 etcd 멤버는 유선 권장. WiFi VXLAN 은 패킷 손실 → heartbeat 미스 → 재선거 → 도미노.

---

## 5. ECK Operator Crash Loop — 못 고친 이야기

### 5.1 증상

10시간 동안 ECK operator pod 가 **97번 재시작**. 평균 6~9분 주기.

```
elastic-operator-0    0/1   CrashLoopBackOff   97 (6m14s ago)   10h
```

### 5.2 root cause 의심

operator 로그:

```
E0517 12:08:51.343 leaderelection.go:436] error retrieving resource lock 
  elastic-system/elastic-operator-leader: 
  client rate limiter Wait returned an error: context deadline exceeded

{"log.level":"error","message":"Failed to start the controller manager",
 "error":"leader election lost", ...}
Error: leader election lost
```

`client rate limiter` — client-go 의 QPS 제한기에서 막힘. lease 갱신 요청이 줄을 못 뚫음.

### 5.3 시도 3가지 — 다 부분 효과

#### 시도 1: chart values `config:` 에 leader-elect-* 추가

```yaml
config:
  leader-elect-lease-duration: 120s
  leader-elect-renew-deadline: 90s
  leader-elect-retry-period: 30s
```

→ **chart 가 이 key 인식 안 함.** ECK helm chart 2.16.1 의 `config:` 는 camelCase 키만 받고, leader election timing 은 노출 안 함. ConfigMap rendered output 에서 내 키들이 사라짐.

#### 시도 2: StatefulSet args 에 CLI flag 직접 patch

```bash
kubectl patch statefulset elastic-operator --type=json -p='[{
  "op":"replace","path":"/spec/template/spec/containers/0/args",
  "value":["manager","--config=/conf/eck.yaml",
           "--leader-elect-lease-duration=120s",
           "--leader-elect-renew-deadline=90s",
           "--leader-elect-retry-period=30s"]
}]'
```

→ **ECK 가 `Error: unknown flag: --leader-elect-lease-duration`.** `manager --help` 확인해보니 ECK 2.16.1 에 lease-duration 플래그 자체가 없었음. 하드코딩.

#### 시도 3: `--kube-client-qps=200` + `--kube-client-timeout=3m`

이건 ECK 가 받는 플래그. QPS 기본은 client-go 의 5/burst 10 — 너무 작음. 200 으로 올리고 timeout 도 1m → 3m.

→ **부분 효과만.** crash 주기 6~9분 → 5분. 완치 아님.

### 5.4 한계 인정

ECK 2.16.1 의 lease duration 은 **소스 코드에 하드코딩** 되어있어 운영자가 못 바꿈. 진짜 fix 는:

- ECK 2.18+ 업그레이드 (lease duration 노출됐을 수 있음)
- single control-plane 으로 마이그레이션 (etcd 경쟁 사라짐)

둘 다 30분~2시간 작업 + 위험 중-상.

### 5.5 영향 재평가 — 무해 판정

여기서 잠깐 멈추고 **실제 영향**을 측정:

| 컴포넌트 | crash 의 영향 |
|---|---|
| ES 데이터 적재 | ✅ 영향 0 (operator 죽어도 ES pod 들은 계속 동작) |
| Kibana 검색 | ✅ 영향 0 |
| Logstash 파이프라인 | ✅ 영향 0 |
| 새 CR 변경 적용 | 🟡 6~9분 지연 (operator 재시작 동안) |
| 클러스터 부하 | 🟡 leader 노드 가끔 spike |

→ **데이터 영향 0. 운영 영향만 살짝.** lemuel 부하는 etcd leader 이전 + cron 으로 흡수됨.

### 5.6 결정 — 그냥 둠

"고치지 못함" 도 **정확한 진단이면 valid 한 결론**이다. 영향이 무해하고, 진짜 fix 의 비용/위험이 effect 보다 크면 *알면서 두는 것* 이 합리적.

운영 일지에 기록 ✓, 다음 ECK 메이저 업그레이드 시 자연 fix 기대.

> **시니어 엔지니어링 정수**: 모든 문제를 다 고치려 들지 말 것. *어떤 문제를 안 고치기로 결정했는지* 가 더 중요한 시그널.

---

## 마무리 — 다섯 주제의 공통 패턴

이 다섯 주제를 관통하는 패턴이 있다.

1. **"표준 설정의 가정" 의심** — Logstash readiness probe 가 HTTP input 포트 HTTPS, ECK default lease 15s, dynamic ES mapping 의 multi-field. 모두 "보통 케이스" 에 맞춘 디폴트이고, 우리 케이스에선 깨짐.

2. **메타데이터(라벨/이름) ≠ 진실** — 노드 라벨 `storage-tier=hdd` 가 거짓. 인덱스 패턴 `logs-*` 가 다른 템플릿에 충돌. 항상 source-of-truth 까지 내려가서 확인.

3. **"부분 효과" 도 효과** — ECK crash 주기 9분 → 5분이 만족스럽진 않지만 진짜 fix 비용 대비 합리적이면 거기서 멈추는 게 맞음. 완벽주의 vs 실용주의의 균형.

4. **GitOps 가 진실 소스 — 손 패치는 ignoreDifferences 짝꿍 필수** — ECK args 패치를 ArgoCD selfHeal 이 되돌리지 못하게 `ignoreDifferences` 등록. 임시 fix 도 GitOps 원칙을 깨지 않게.

5. **자동화는 멱등(idempotent) 으로** — etcd leader pin cron 은 매일 무조건 실행 (이미 leader 면 no-op). ES advanced setup Job 은 'already exists' 응답을 OK 처리. 재실행 안전한 자동화가 운영 비용을 0 에 수렴시킴.

> **TL;DR** — 하루치 ELK 학습이 5주제 짜리 운영 회고로 진화. 핵심은 *시행착오를 빠르게 commit 단위로 기록* 하고 *못 고친 것도 정확히 진단하는 것*. K3s 홈랩이라도 "왜 안 됐는지" 를 추적하는 근육은 그대로 키울 수 있다.

---

### 부록 — 이 하루의 helm-deploy 변경 (commit 9개)

```text
feat(elk): Logstash 도입 — Fluent Bit → Logstash(HTTP:8080) → ES
fix(elk):  Logstash ssl_verification_mode certificate→full
fix(elk):  Logstash readiness probe TCP:9600
fix(elk):  Logstash level 매핑 case-insensitive
feat(elk): Kibana 'K8s Logs - Operational Overview' 대시보드 GitOps
feat(elk): ES 고급 셋업 — ILM + 인덱스 템플릿 + Transform
fix(elk):  hot 노드에 transform role 추가
fix(elk):  Transform .keyword 사용 + dest 인덱스명 충돌 회피
feat(cluster-ops): etcd leader 매일 ilwon 으로 재고정 CronJob
```

기록을 commit 단위로 남기면 *나중의 나* 가 똑같은 함정 만났을 때 5분 안에 솔루션 찾는다.
