---
layout: post
title: "쿠버네티스 × ELK — 둘이 같이 굴러야 하는 이유, 실제 운영 시나리오, 기대 효과"
date: 2026-05-15 16:00:00 +0900
categories: [infra, kubernetes, observability, elasticsearch]
tags: [k8s, k3s, elk, elasticsearch, kibana, fluent-bit, observability, sre, incident-response]
---

쿠버네티스에 ELK 를 붙이는 건 단순히 "로그 좀 보기 좋게" 가 아닙니다. **컨테이너 워크로드의 운영 구조 자체** 가 로그 집계 시스템을 필수 부품으로 요구합니다. 어제 5-노드 K3s 홈랩에 ECK 기반 ELK 스택을 깐 후 일주일도 안 됐는데, 이미 운영 패턴이 달라진 게 체감됩니다. 둘의 상관관계, 실 운영 시나리오, 그리고 기대 효과를 정리합니다.

> 이 글에서 다루는 것
> - 쿠버네티스의 구조적 특성과 ELK 가 자연스럽게 맞물리는 5 가지 지점
> - 실 운영 시나리오 6 가지 (장애 대응, 캐파 계획, 보안 감사, 컴플라이언스 등)
> - 정량 지표로 본 도입 전/후 차이 (MTTR, 사건 인지 시간 등)
> - 어떤 함정을 피해야 ELK 가 "또 하나의 운영 부담" 으로 전락하지 않는가

---

## 1. 왜 쿠버네티스와 ELK 는 짝이 되는가

### 1-1. 파드는 사라진다, 로그도 같이 사라진다

쿠버네티스의 핵심 설계 가정 하나 — **파드는 일회용** 입니다. Deployment 가 새 ReplicaSet 으로 롤아웃하면 기존 파드는 termination grace period 30 초 뒤 사라집니다. CrashLoopBackOff 가 발생한 파드는 자동 재기동되고, OOM-Killed 파드는 흔적 없이 교체됩니다.

문제는 — **그 파드 안에서 일어난 일** 은 `kubectl logs <pod>` 로만 볼 수 있고, 파드가 사라지면 그 명령어도 함께 사라집니다. `kubectl logs --previous` 가 한 번의 재시작까지는 보존하지만 그 이상은 못 본다는 게 함정.

이건 docker-compose 시절의 "컨테이너가 호스트에 있으니까 `docker logs foo`" 와 본질이 다릅니다. K8s 에서는 **로그가 휘발성** 이고, 휘발성 데이터를 영속화하는 게 ELK 의 첫 번째 역할.

### 1-2. 워크로드 수가 폭발한다 — `kubectl logs` 의 한계

홈랩 5-노드에 24 개 네임스페이스 50 개 파드만 돌아도 — `kubectl logs deploy/foo -n bar` 를 50 번 치기 시작하면 끝납니다. 운영 환경에서는 500 개, 5000 개 파드도 흔합니다. 사람이 단일 명령어로 접근할 수 있는 한계는 보통 한 자릿수 파드.

ELK 가 들어가면 **단 하나의 쿼리** 로 24 ns × N 파드 × M 시간 범위를 한 번에 검색합니다.

```text
# kubectl 시절
$ for ns in $(kubectl get ns -o name); do
    for d in $(kubectl get deploy -n ${ns#namespace/} -o name); do
      kubectl logs $d -n ${ns#namespace/} --tail=100 | grep -i exception
    done
  done
# 50 번의 round-trip, 30+ 초 소요, 메모리 안에서만 grep
```

```text
# ELK 시절 (KQL on Kibana Discover)
level: ERROR or message: "Exception" or message: "Traceback"
# 1 회 쿼리, 100ms 내 응답, 전체 24 ns × 90 일 인덱스 어그리게이션
```

선형 vs 상수 시간 복잡도. 운영자가 50 명의 파드를 일일이 째지 않게 만들어주는 게 두 번째 역할.

### 1-3. 마이크로서비스 호출은 분산 추적이 필수

24 개 네임스페이스 = 사실상 24 개 서비스. 사용자 요청 하나가 ingress → gateway → auth → business-logic → db 까지 5 ~ 10 홉을 거치는 게 보통.

각 홉이 어디서 깨졌는지, 어디서 latency 가 튀었는지 보려면 — **여러 파드의 로그를 시간순으로 한 줄로 엮어서** 봐야 합니다. ELK 의 `@timestamp` 정렬 + `kubernetes.namespace_name` / `kubernetes.pod_name` 필터 조합이 정확히 그 일을 합니다.

OpenTelemetry trace 까지 더하면 더 깔끔하지만, 단순 stdout 로그 집계만으로도 80% 의 디버깅이 해결됩니다.

### 1-4. K8s 자체가 구조화된 메타데이터를 풍부하게 흘려준다

`kubectl describe pod` 에 들어가는 정보들 — namespace, pod_name, container_name, container_image, node_name, labels — 이 메타데이터가 Fluent Bit 의 `kubernetes` 필터를 통해 자동으로 모든 로그 라인에 attach 됩니다.

ELK 가 이 메타데이터를 **인덱싱된 필드** 로 받기 때문에 — `kubernetes.namespace_name: asat-prod AND level: ERROR` 같은 쿼리가 풀 텍스트 grep 이 아닌 inverted index lookup 으로 처리됩니다. 1 억 건이 있어도 ms 단위.

이게 비-K8s 환경에서는 못 하는 일입니다. 사용자가 직접 `app=foo env=prod` 를 매 로그 라인에 박아야 가능한 것을, K8s 가 자연스럽게 제공.

### 1-5. ECK Operator 가 K8s 의 컨트롤 루프 위에 ES 를 얹는다

ECK (Elastic Cloud on Kubernetes) Operator 는 ES 클러스터를 K8s 네이티브 CRD 로 다룹니다.

```yaml
apiVersion: elasticsearch.k8s.elastic.co/v1
kind: Elasticsearch
spec:
  version: 8.16.1
  nodeSets:
    - name: hot
      count: 1
      config: { node.roles: [master, data_hot, ingest] }
```

이 한 줄이면 — pod, service, configmap, secret(TLS cert, elastic 유저 비번), pvc 가 자동 생성. 노드 수 늘리려면 `count: 3`. ES 버전 업그레이드는 `version: 8.17.0` 한 글자. 모두 K8s 의 declarative model 위에 얹혀 있어서 **kubectl apply 한 줄로 운영**.

ES 가 굳이 K8s 안에 있어야 할 이유 중 하나가 이거. 외부에서 별도 클러스터로 띄우면 ECK 의 자동화 혜택을 못 받습니다.

---

## 2. 실 운영 시나리오 6 가지

### 시나리오 1 — 배포 직후 5xx 폭증 알람

**상황** — ArgoCD 가 새 이미지로 자동 롤아웃, 5분 후 settlement-prod 의 ERROR 카운트가 평소 5분 평균 3 건에서 149 건으로 점프.

**ELK 가 한 일**:

```text
5분 윈도 ERROR aggregation by namespace
  → settlement-prod : 149건 (임계치 20 초과)
  → Telegram 봇으로 자동 알람 발송
```

**대응 흐름**:
1. 텔레그램 알람을 받은 운영자가 Kibana Discover 진입
2. `kubernetes.namespace_name: settlement-prod AND level: ERROR` 필터
3. 시간 히스토그램에서 정확한 spike 시점 확인 → ArgoCD 배포 시각과 일치
4. 최근 100 건 ERROR 메시지 한 화면에서 패턴 확인 → "Optimistic lock failure on entity X" 가 다수
5. ArgoCD UI 에서 1 클릭 롤백 → 5분 안에 정상화
6. 인덱스에 남은 ERROR 로그로 디버그 → 다음 PR 로 수정 후 재배포

**핵심** — 사람이 이상을 인지하는 데 걸린 시간이 0 분에 가깝습니다. 봇이 알려주니까.

### 시나리오 2 — OOM-Killed 파드의 마지막 유언 보존

**상황** — asat-app 이 메모리 한도 초과로 OOMKilled, ReplicaSet 이 즉시 새 파드로 교체.

**기존(`kubectl logs`)** — 새 파드는 텅 빈 로그. `--previous` 로 한 번만 볼 수 있고, 다음 OOM 이 또 나면 그 직전 것은 영영 잃음.

**ELK** — 죽기 직전 5초 간의 GC pause 로그, heap dump 알림, 마지막 트랜잭션 ID 까지 인덱싱되어 있음. 90 일 retention 동안 보존.

```text
KQL: kubernetes.pod_name: asat-app-* AND @timestamp: [2026-05-14T15:23:00 TO 2026-05-14T15:23:30]
→ 30 초 윈도의 마지막 ERROR/WARN 라인 전체 확인 가능
```

OOM 의 원인이 트래픽 spike 인지, 특정 쿼리의 N+1 인지, 메모리 누수인지를 사후에 정확히 짚어낼 수 있습니다.

### 시나리오 3 — 보안 감사 — 누가 언제 무엇을 했는가

**요구사항** — 한림대 산학협력단 감사관이 "지난 30 일 동안 admin@asat.com 계정으로 한 모든 API 호출 내역" 을 요청.

**비-ELK 시절** — 사실상 답변 불가. kubectl logs 는 24 시간 전이 한계, 그것도 불연속.

**ELK** — Spring Boot 가 stdout 으로 찍는 access log 가 30 일 분량 hot tier 에 그대로. 60 일이 지나면 warm 으로 이관되어 검색 가능, 그 이후 cold tier 에서 90 일까지.

```text
KQL: app: "asat-app" AND user_email: "admin@asat.com" AND request_method: *
→ CSV export → 감사관에게 제출
```

연구용 시스템이라 IRB / 개인정보보호 감사가 빈번한데, 이걸 사람이 손으로 처리하던 시간이 0 에 가까워집니다.

### 시나리오 4 — 캐파 계획 — 어느 네임스페이스가 진짜로 바빠지는가

**상황** — 다음 분기 클러스터 리소스 증설 결정 직전. 어느 워크로드가 가장 많이 늘었는지를 객관적으로 봐야 함.

**ELK 가 한 일** — Kibana Lens 로 namespace 별 일일 로그 볼륨 추이.

```text
시각화: line chart, x=timestamp(daily), y=count(), split=kubernetes.namespace_name
→ 지난 30 일간 academy-prod 의 로그 볼륨이 3배 증가
→ asat-prod 는 평탄, settlement-prod 는 주말마다 spike
```

로그 볼륨 = 트래픽 + 에러 + GC + 디버그 라인의 합. 정확히 트래픽 그래프는 아니지만 **상대적 변화** 는 정확합니다. 메트릭(Prometheus) 의 request_count 와 교차 검증하면 의사결정 근거가 됩니다.

### 시나리오 5 — 코드 변경 없는 운영 가시성 추가

**기존** — 새 메트릭을 보고 싶으면 코드에 `meterRegistry.counter("foo").increment()` 추가 → PR → review → 배포. 1 ~ 3 일 소요.

**ELK** — 코드는 이미 `log.info("user signed up email={}", email)` 같은 라인을 흘리고 있음. Kibana 에서 KQL 한 줄 + Lens 차트 한 개로 일간 가입 수 대시보드 생성. 코드 무변경, 5 분.

```text
KQL: message: "user signed up"
시각화: 시간별 카운트
저장: 대시보드 "ASAT — 일간 가입 추이"
```

로그가 사실상 무한대의 **암묵적 메트릭** 입니다. 메트릭으로 명시화할지 vs 로그로 검색할지의 결정을 비용 대비 가치로 판단할 수 있게 해줍니다.

### 시나리오 6 — 컴플라이언스 — "이거 했어요" 증빙

**상황** — V35 invitation 토큰의 SHA-256 hash 저장 + 1 회용 + 48h TTL 정책이 실제로 작동하는지 외부 감사관이 확인하고 싶음.

**ELK** — `InvitationService.consume()` 의 모든 호출 로그가 인덱싱되어 있음. 토큰 hash, 사용자, 시각, 결과(SUCCESS/INVALID/EXPIRED) 까지.

```text
KQL: app: "asat-app" AND logger: "InvitationService" AND message: ("consumed" OR "expired")
→ 30 일 분 데이터 → KPI 계산: invitation 사용률, 만료율, 재발급률
```

코드와 별도로 **운영 증거(evidence)** 가 시계열로 쌓입니다. 컴플라이언스 대응의 가장 큰 부담인 "그게 정말 그랬다는 걸 어떻게 증명?" 에 답이 됩니다.

---

## 3. 정량 지표로 본 기대 효과

홈랩 규모지만 의미 있는 변화는 다음과 같습니다.

| 지표 | ELK 도입 전 | ELK 도입 후 |
|------|-------------|-------------|
| **MTTI (Mean Time To Identify)** — 사람이 이상을 인지하는 데 걸린 시간 | 사용자 신고 또는 우연 발견 (수시간~수일) | Telegram 알람 5 분 윈도 → 최악 5 분 |
| **MTTR (Mean Time To Recover)** — 장애 시작부터 복구까지 | 30 분 ~ 2 시간 (로그 수집부터 함) | 5 ~ 15 분 (Discover 검색 → 1 클릭 롤백) |
| **로그 보관 기간** | 파드 lifetime (수 시간 ~ 며칠, 재시작 시 휘발) | 90 일 (hot 7d + warm 23d + cold 60d) |
| **로그 검색 응답 시간** | `kubectl logs ... | grep` 30 초 ~ 분 | KQL 100ms ~ 1 초 |
| **검색 범위** | 단일 파드 / 단일 시간대 | 전체 클러스터 / 90 일 / 어그리게이션 |
| **코드 변경 없는 새 메트릭 추가** | 불가 (PR 필요, 1~3 일) | 가능 (Kibana Lens, 5 분) |
| **감사 응답 시간** | 사실상 불가 | CSV export, 5 분 |
| **운영자 인지 부담** | 24/7 사람이 봐야 함 | 봇이 임계치 초과만 알림 |

가장 큰 변화는 마지막 줄. "이상 신호" 를 사람이 늘 살피는 게 아니라 **시스템이 비정상을 분류해서 사람에게 푸시** 하는 모델로 운영 책임의 방향이 바뀝니다.

---

## 4. 함정 — ELK 가 또 하나의 운영 부담이 되는 5 가지 패턴

성공 사례가 많은 만큼 실패 사례도 많은 게 ELK 입니다. 도입 전에 피해야 하는 함정들.

### 4-1. 데이터 양 통제 실패 — 디스크 폭발

ILM 없이 들어가면 매일 GB 단위로 인덱스가 쌓여 한 달 안에 디스크가 가득. **반드시** hot/warm/cold 티어 + delete phase 까지 정책 박고 시작해야 합니다.

해법 — index template + ILM policy 를 helm chart 의 post-install hook 으로 묶기. 새 인덱스는 자동으로 policy 적용.

### 4-2. ES 자체 백업 누락

K8s Velero 가 PVC 를 백업해줘도 ES 인덱스는 그 안에서 항상 변하는 상태이므로 정합성이 깨질 수 있습니다.

해법 — ES 의 자체 snapshot API 를 R2/S3 로 SLM 자동화. Velero 와 별도 트랙으로 운영. 어제 글에서 19.4 초 만에 첫 스냅샷 SUCCESS 한 게 이 패턴.

### 4-3. 민감 필드 마스킹 부재

password / Authorization header / JWT 토큰 / 개인정보 가 그대로 ES 에 박히면 — 그 자체로 보안 사고. 한국 PIPL / 의료 IRB 환경에서는 즉시 침해 사건.

해법 — Fluent Bit Lua 필터로 sender-side redact. 또는 Spring Boot 의 logback 에서 MDC 필터 적용 후 stdout 으로만 흘리기. 둘 다 권장.

### 4-4. RBAC 없이 모두에게 read 권한

Kibana 에 root 권한으로 접근 가능한 사람이 많아지면 — 위의 4-3 과 결합해서 사고 가능성 증폭. Cloudflare Access SSO + Kibana Spaces / Role mapping 으로 namespace 단위 권한 분리 필수.

### 4-5. 알람 피로 (alert fatigue)

처음에 임계치를 낮게 잡으면 매 5 분마다 알람 → 운영자가 텔레그램을 무음. 그러면 정작 진짜 사고 알람도 무시.

해법 — **임계치를 조금 보수적으로** + **시간대별 조정** + **연쇄 알람 그루핑**. ASAT 의 경우 ERROR 20 건/5분 이 baseline 이고, settlement 처럼 평소 ERROR 가 많은 ns 는 별도 임계치.

---

## 5. 운영 사이클의 새 모습

ELK 가 들어간 후 운영자의 일과는 이렇게 압축됩니다.

```text
[09:00] 출근 — Telegram 보면 밤 사이 알람 없음 확인
[09:05] Kibana 대시보드 한번 훑기 — 지난 12 시간 ERROR 추이, 상위 N 개 ns
[09:10] 다른 일 (코드 작업, PR review)
...
[14:32] 텔레그램 봇 알람 — academy-prod ERROR 47건/5분
[14:33] Kibana Discover 한 번에 들어가서 패턴 확인 (kubernetes.namespace_name: academy-prod AND level: ERROR)
[14:35] DB 커넥션 타임아웃 패턴 발견 → 14:30 ArgoCD 가 deploy 한 새 이미지 의심
[14:36] ArgoCD UI 에서 이전 SHA 로 1 클릭 롤백
[14:38] 알람 카운트 0 으로 떨어지는 거 확인
[14:40] 새 PR — DB pool 설정 수정, push
[15:00] 자동 재배포 + Kibana 로 정상 동작 확인
```

운영자가 능동적으로 모니터링하는 시간은 09:05 의 5 분이 거의 전부. 나머지는 **봇이 운영자를 부를 때만** 끼어듭니다.

---

## 6. 다음 단계 — APM / Trace 통합

ELK 만으로 80% 의 디버깅이 해결되지만, 분산 트랜잭션 추적은 여전히 빈자리. 다음에 채울 것:

1. **OpenTelemetry Java agent** 를 Spring Boot 컨테이너에 sidecar 또는 javaagent 로 attach
2. **OTel Collector** 가 trace / metric / log 를 한 파이프라인으로 받아 ES (또는 Jaeger / Tempo) 로 라우팅
3. Kibana APM UI 가 trace 와 stdout 로그를 **trace_id** 로 자동 join
4. p99 latency 임계치 알람을 Telegram 으로 통합

이 단계가 되면 — "5xx 가 났다" → "어느 호출 chain 의 몇 번째 홉이 timeout 났다" 까지 한 화면에서 확인 가능. 진정한 의미의 distributed observability.

---

## 7. 정리

쿠버네티스에서 ELK 는 **선택이 아니라 구조적 필요** 입니다.

- 파드는 휘발성 → 로그도 휘발성 → ELK 가 영속화
- 워크로드 수가 폭발 → kubectl logs 의 선형 비용 → ELK 의 상수 시간
- 마이크로서비스 호출 분산 → 시간순 결합 → ELK 의 timestamp 정렬
- K8s 자체가 메타데이터를 풍부하게 제공 → ELK 의 인덱싱 효율 극대화
- ECK Operator 가 K8s 네이티브로 ES 를 관리 → 운영 자동화 완성

그리고 ELK 가 가져다주는 변화는 단순한 "로그 잘 보기" 가 아닙니다.

- 사람이 모니터링하던 시간이 봇이 알람 보내는 시간으로 압축
- 사후 디버그가 사전 감지로 전환
- 메트릭으로 명시화하지 않아도 로그가 암묵적 메트릭 역할
- 컴플라이언스 / 감사 대응이 사실상 자동화

도입 비용 — 5-노드 홈랩 기준 RAM 18 GB + CPU 6 core + 디스크 1 TB. 4 시간 작업.
도입 효과 — 운영 시간이 시간 단위에서 분 단위로 압축. 사고 인지 지연이 시간 단위에서 5 분으로.

ROI 계산은 굳이 안 해도 됩니다.

> **TL;DR** — K8s 의 휘발성 + 분산 + 메타데이터 풍부함은 ELK 의 영속성 + 인덱싱 + 어그리게이션과 정확히 짝을 이룬다. 6 가지 실 운영 시나리오에서 MTTI 가 수시간에서 5 분, MTTR 가 시간에서 분으로 압축된다. 5-노드 홈랩에 4 시간이면 가동.
