---
layout: post
title: "ELK 'monitoring 45건' 알람의 정체 — 모니터링이 자기를 알람하는 메타-함정"
date: 2026-05-16 14:30:00 +0900
categories: [infra, kubernetes]
tags: [kubernetes, monitoring, elk, grafana, alerting, sidecar, argocd, postmortem]
---

오후 2시, 텔레그램에 알람이 떴다:

```
ELK ERROR spike (last 5m, threshold 20) - 04:40
monitoring : 45건
Kibana: https://kibana.lemuel.co.kr
```

처음 본 순간의 직감 — *"04:40 새벽에 모니터링 스택 어딘가 죽었구나"*. 그런데 진단을 시작하자마자 두 개의 함정이 동시에 튀어나왔다:

1. **첫 가설(`kube-state-metrics` 재시작 노이즈)이 사실 틀렸음**을 알아채기까지 30분
2. 알람 메시지의 "04:40"이 **컨테이너 UTC 시각**이라는 사실을 놓쳤음

결론적으로 진짜 원인은 **`kps-grafana` 의 k8s-sidecar 컨테이너가 apiserver의 일시적 503에 매번 `level=ERROR`로 로깅**하는 거였다. 한 사이클에 ~48줄. 모니터링 스택이 *자기 자신을 위한 모니터링 알람을 생성*한다.

이 글은 그 디버깅 과정과, 같이 정리한 "쿠버네티스 모니터링 노이즈 잡는 4단계 원칙"을 묶었다.

> 이 글에서 다루는 것
> - 알람 메시지에서 보이는 시각이 *컨테이너 시각(UTC)* 일 수 있다는 함정
> - 모니터링 스택 자체가 알람의 발신자가 되는 메타-문제
> - 알람을 끄기 전에 *그 알람의 쿼리를 직접 재현*해야 하는 이유
> - GitOps 환경에서 알람 룰을 안전하게 패치하는 방법
> - "노이즈 필터"가 "신호 누락"으로 바뀌지 않게 하는 4가지 원칙

---

## TL;DR

| 단계 | 발견 | 시간 |
|---|---|---|
| 1차 가설 | `kube-state-metrics` 재시작 시 reflector reconnect 에러 (klog `E0516` 포맷) | ❌ 틀림 |
| 검증 | 알람 CronJob의 *실제 ES 쿼리*를 재현 → KSM 로그는 `level: ERROR` 필드를 안 씀, 매칭 0 | ✅ 가설 폐기 |
| 2차 발견 | 알람의 "04:40"이 **UTC** (컨테이너 기본 시간대) → KST 13:40 today | ✅ 시간 보정 |
| 진짜 원인 | `kps-grafana` 의 `grafana-sc-datasources` / `grafana-sc-dashboard` (k8s-sidecar Python)가 apiserver 503 받을 때 `ApiException when calling kubernetes` 를 `level=ERROR` 로 기록 → 5분에 48건 | ✅ |
| 근본 원인 | 르무엘(WiFi control-plane)의 apiserver 일시 지연 → sidecar polling이 503 → 에러 다발 | ✅ |
| 핫픽스 | 알람 CronJob의 쿼리에 `must_not: "ApiException when calling kubernetes"` 추가 | 5분 |
| 배포 | helm 차트 git push → ArgoCD sync (`kubectl patch` 안 됨, selfHeal에 되돌아감) | ✅ |

---

## 1. 첫 가설 — KSM 재시작이 만든 reconnect 에러

알람이 *모니터링 네임스페이스* 라고 했으니 그 네임스페이스의 pod부터 봤다.

```bash
$ kubectl get pods -n monitoring
NAME                                     READY   STATUS    RESTARTS        AGE
kps-grafana-69c97c555d-w2mtq             3/3     Running   3 (88m ago)     2d21h
kps-kube-state-metrics-d46bf8787-q7g66   1/1     Running   15 (85m ago)    43h
kps-prometheus-node-exporter-rnk6q       1/1     Running   10 (15h ago)    3d2h
...
```

`kube-state-metrics`의 재시작 횟수가 **15회**. 43시간 가동에 15번 재시작이면 잦다. 로그를 보니:

```
E0516 04:34:49 reflector.go:150 Failed to watch *v1.Pod: failed to list *v1.Pod: apiserver not ready
E0516 04:34:49 reflector.go:150 Failed to watch *v1.CertificateSigningRequest: apiserver not ready
E0516 04:34:49 reflector.go:150 Failed to watch *v1.ValidatingWebhookConfiguration: apiserver not ready
E0516 04:35:00 reflector.go:150 Failed to watch *v1.Namespace: apiserver not ready
E0516 04:35:03 reflector.go:150 Failed to watch *v1.PersistentVolume: apiserver not ready
E0516 04:35:07 reflector.go:150 Failed to watch *v1.Node: apiserver not ready
... (각 resource type별로 retry 반복)
```

타이밍이 04:34-04:35 KST에 딱 맞는다. 7-8개 resource type × retry → "5분에 45건" 정도 나오겠다. 매우 그럴듯한 가설.

그러나 *알람 룰의 실제 쿼리*를 보지 않고 짜낸 가설이었다.

---

## 2. 검증 — 알람 쿼리를 직접 재현하기

이 환경에서 알람을 보내는 건 `logging` 네임스페이스의 `log-error-alerter` CronJob이다 (5분마다 ES에 질의 → Telegram 전송). 차트 코드를 직접 봤다:

```yaml
QUERY='{
  "size": 0,
  "query": {
    "bool": {
      "filter": [
        { "range": { "@timestamp": { "gte": "now-5m" } } },
        { "bool": { "should": [
            { "term": { "level": "ERROR" } },
            { "term": { "level": "FATAL" } },
            { "match_phrase": { "message": "Exception" } },
            { "match_phrase": { "message": "Traceback" } }
        ] } }
      ]
    }
  },
  "aggs": {
    "by_ns": { "terms": { "field": "kubernetes.namespace_name", "size": 50 } }
  }
}'
```

핵심: 매칭 조건은 `level: ERROR/FATAL` 또는 `message`가 "Exception" / "Traceback" 포함.

여기서 *KSM 가설이 깨졌다*. KSM은 klog 포맷(`E0516 04:34:49`)으로 stdout에 찍는데, fluent-bit 파싱 결과 `level` 필드는 안 만들어진다. 또 메시지 본문도 "Exception"이나 "Traceback"이 아니다 — 그냥 "Failed to watch ... apiserver not ready".

쿼리를 그대로 ES에 던져 봤다:

```bash
$ curl ... '{"query":{"bool":{"filter":[
    {"term":{"kubernetes.namespace_name":"monitoring"}},
    {"range":{"@timestamp":{"gte":"2026-05-15T19:35:00Z","lte":"2026-05-15T19:45:00Z"}}},
    {"bool":{"should":[
      {"term":{"level":"ERROR"}},...
    ]}}
  ]}}}'

→ "total": {"value": 0, "relation": "eq"}
```

**0 hits.** KSM 가설은 데이터로 부정됐다.

> 1번째 원칙: **알람을 끄거나 무시하기 전에, 그 알람의 *쿼리를 직접 재현*해보라.** 알람 메시지의 텍스트만으로 가설을 세우면 실제 알람 룰이 *완전히 다른 조건*을 본다는 사실을 놓친다.

---

## 3. 두 번째 발견 — 그 "04:40"은 UTC였다

KSM 가설은 폐기됐는데 데이터가 0인 게 이상했다. 알람은 분명 45건이라고 했다. 시각이 잘못된 게 아닐까?

CronJob의 코드:

```bash
TS=$(date '+%H:%M')
MSG=$(printf '%s\n%s\n%s\n%s' "ELK ERROR spike (last 5m, threshold $THRESHOLD) - $TS" ...)
```

평범한 `date`. **컨테이너의 기본 시간대는 UTC.** 알람의 "04:40"은 UTC였다. KST로 변환하면 13:40 — 같은 날 오후, 알람 도착 20분 전.

UTC 04:35-04:45 (KST 13:35-13:45) 윈도우로 동일 쿼리를 다시 던졌다:

```json
{
  "total": {"value": 51},
  "aggregations": {
    "by_ns": {
      "buckets": [
        {"key": "monitoring", "doc_count": 48},
        {"key": "settlement-staging", "doc_count": 1}
      ]
    }
  }
}
```

**`monitoring: 48` — 매치.** ([±3은 5분 윈도우 경계 차이 / threshold 20 비교 시점 차이로 자연스러움])

> 2번째 원칙: **컨테이너에서 출력된 시각은 별도 설정이 없으면 UTC다.** 알람 메시지의 시각을 사람 눈으로 읽기 전에, 그 시각이 어느 시간대로 찍혔는지 한번 확인하라. 디버깅을 9시간 헛돌게 할 수 있다.

---

## 4. 진짜 원인 — Grafana sidecar의 ApiException

UTC 04:35-04:45 윈도우에서 `monitoring` ns의 ERROR 로그를 직접 까봤다:

```
pod_name:       kps-grafana-69c97c555d-w2mtq
container_name: grafana-sc-datasources
level:          ERROR
msg:            'ApiException when calling kubernetes: (503)
                 Reason: Service Unavailable
                 HTTP response headers: HTTPHeaderDict({'Connection': 'close', ...})
                 HTTP response body: b'{"kind":"Status",...}'
```

`grafana-sc-datasources` 와 `grafana-sc-dashboard` — 둘 다 `kiwigrid/k8s-sidecar` 이미지. Grafana의 *동적 datasource/dashboard 로딩*을 위해 ConfigMap/Secret을 watch하는 Python 사이드카다. 이 친구는:

- kubernetes_asyncio 라이브러리로 apiserver polling
- API 호출 실패 시 **Python logging.error()** 로 기록 (그래서 `level: "ERROR"` 필드가 정확히 박힘)
- HTTP 503 / 403 받으면 위와 같은 다중 줄 메시지 한 번에 출력

5분에 ~48번 호출 실패 = 5분에 ~48 ERROR 줄. 임계치 20 초과 → 알람 발사.

### 4.1 왜 apiserver가 503/403을 줬나

호스트 측 컨텍스트:

- 르무엘 = K3s control-plane, **WiFi**로 클러스터 연결 (홈랩 의도된 선택)
- 새벽 시간대 `top` 캡처로 확인: 르무엘 부하 자주 튐 (대부분 측정 아티팩트, 일부 실제 reconcile loop)
- 르무엘의 kube-apiserver는 etcd 합의 + Flannel VXLAN + 모든 kubectl 요청을 처리
- 일시적 부하 + WiFi 지연 시 apiserver가 503 응답
- 403은 RBAC 정보를 watch하는 도중 캐시 갱신 race
- sidecar는 *짧은 polling 주기* (몇 초 단위)로 끊임없이 호출 → 일시 장애도 다중 ERROR 줄로 증폭

### 4.2 진짜 장애인가, 노이즈인가

- Grafana 본체는 *정상 가동* (Running 2d21h)
- Dashboard/Datasource 자체는 *살아있음* (이미 로드된 것들은 sidecar API 실패와 무관하게 작동)
- KSM의 잦은 재시작도 같은 뿌리 (apiserver liveness probe 일시 실패)
- *근본 인프라 약점*(WiFi+single control-plane)이 *모니터링 스택 메트릭*에 다중으로 새는 패턴

장애가 아니라 "*환경 특성에 비해 알람 룰이 너무 민감하다*". 노이즈 필터링이 맞다.

> 3번째 원칙: **'모니터링 시스템이 모니터링 알람을 일으키는 상황'을 식별하라.** Prometheus가 자기 자신을 scrape하다 실패해서 alertmanager가 발사, Grafana sidecar가 apiserver 못 봐서 ERROR 로깅 → 알람 룰 트리거, KSM이 재시작하다 reflector 에러 다발 → 다른 알람 룰 트리거. 이런 자기-참조 알람은 *진짜 신호의 약 2-5배* 잡음을 만든다.

---

## 5. 핫픽스 — must_not 절 한 줄

`grafana-sc-*` 사이드카의 메시지는 `"ApiException when calling kubernetes"`로 시작한다. 이 phrase로 필터링:

```yaml
QUERY='{
  ...
  "query": {
    "bool": {
      "filter": [ ... ],
      "must_not": [
        { "match_phrase": { "message": "ApiException when calling kubernetes" } }
      ]
    }
  },
  ...
}'
```

`must_not` + `match_phrase` 조합 → 정확한 phrase가 들어간 문서를 *집계에서도 제외*.

### 5.1 GitOps 워크플로

이 환경은 ArgoCD `elk-cluster` Application이 helm 차트를 관리한다. 직전 [블로그 포스트](/2026/05/16/k8s-ops-pitfalls-from-one-night-debugging/)에서 다룬 함정 1번 — *ArgoCD selfHeal이 kubectl patch를 1초 만에 되돌린다*. 그래서 패치는 *git에 commit + push, 그 다음 sync*:

```bash
# 1. 차트 수정
$EDITOR helm-deploy/charts/elk-cluster/templates/error-alert-cronjob.yaml

# 2. commit + push
git add ... && git commit -m "fix(elk): grafana sidecar ApiException 제외" && git push

# 3. ArgoCD sync (자동 sync 안 켜져있으면)
kubectl patch application elk-cluster -n argocd --type=merge \
  -p '{"operation":{"sync":{}}}'

# 4. 검증
kubectl get cronjob -n logging log-error-alerter -o yaml \
  | grep -A2 "must_not\|ApiException"
```

다음 사이클(5분 후)부터 알람 안 옴.

> 4번째 원칙: **알람 룰은 *코드*다. git에 두고, 리뷰하고, GitOps로 배포하라.** Kibana UI에서 알람을 끄거나 임계치를 휙휙 바꾸면 *재현 불가능한 운영 상태*가 된다. CronJob/Watcher/Detection Rule이 git의 manifest로 관리되면 6개월 뒤에도 *왜 이 phrase가 제외돼있는지*를 commit message로 알 수 있다.

---

## 6. 노이즈 필터링의 위험 — 신호를 죽이지 않으려면

알람을 끄는 건 쉽다. 위험한 건 *진짜 신호*까지 같이 죽는 것. 이 변경이 안전한지 점검:

1. **"ApiException when calling kubernetes"** 는 충분히 좁은 phrase인가?
   - 검색: `match_phrase` 라서 정확한 시퀀스만 매칭 → 일반 코드의 `ApiException`은 영향 없음
   - 특히 kubernetes 클라이언트 라이브러리의 특정 메시지 — 다른 곳에서 동일 phrase 쓸 가능성 낮음
2. **이 phrase로 새는 *진짜 장애*가 있을 수 있나?**
   - 예: 누군가가 ConfigMap을 삭제했고 sidecar가 그걸 알리려고 ERROR 찍는 경우 → 같은 phrase로 묻힐 수 있음
   - 완화: 별도 알람으로 "grafana sidecar가 *지속적으로*(예: 30분 이상) ApiException를 찍는다"는 더 약한 조건의 알람을 분리 추가 (TODO)
3. **다른 sidecar/agent가 같은 phrase 안 쓰는가?**
   - 같은 `k8s-sidecar` 이미지 쓰는 곳: ArgoCD image-updater, cert-manager-webhook 등 — 만약 거기서도 동일 메시지가 나오면 동시에 제외됨
   - 본 환경에서는 `monitoring` ns의 grafana sidecar 둘만 사용 → 영향 범위 확정

> 보너스 원칙 — **노이즈 필터는 두 단계로 한다.** *즉시* 노이즈를 죽이는 것 + *나중에* "정말 사라진 신호가 있나" 확인하는 추적 알람. 첫 단계만 하고 끝내면, 6개월 뒤 진짜 장애를 같은 필터가 묻어버릴 수 있다.

---

## 7. 운영 습관 — 4가지 원칙 종합

> **1. 알람을 끄기 전에 알람의 쿼리를 직접 재현하라.**  
> 알람 텍스트로 가설 세우면 30분을 잃기 쉽다. 알람 룰의 코드를 보고 그 쿼리를 ES/Prometheus에 직접 던져, 어떤 데이터가 매치되는지 *눈으로 본 다음* 가설을 세워라.

> **2. 컨테이너 출력 시각은 UTC를 기본으로 의심하라.**  
> 컨테이너의 `date`, 로그 timestamp, 메트릭 timestamp는 별도 설정 없으면 거의 UTC. 알람 메시지 → 데이터 윈도우 매핑할 때 시간대를 한 번 확인. 안 그러면 9시간 헛도는다.

> **3. 모니터링 스택의 자기-참조 알람을 식별하라.**  
> Prometheus가 자기 scrape 실패, Grafana sidecar의 apiserver 폴링 실패, KSM의 reflector reconnect 실패 — 이런 자기-참조 노이즈가 모니터링 알람의 *2-5배 잡음원*이다. 환경의 본질적 약점(WiFi, 단일 control-plane 등)이 이쪽으로 새어 알람을 만든다. 노이즈로 분리해서 알람 룰에서 제외하되, *지속성 조건*을 둔 더 약한 알람을 분리 추가하라.

> **4. 알람 룰은 코드다 — GitOps로 관리하라.**  
> Kibana UI / Grafana UI에서 알람을 끄거나 임계치를 즉석에서 바꾸지 마라. 변경 사항은 helm chart / yaml에 commit하고 ArgoCD sync. 6개월 뒤 누군가 "왜 이 phrase가 제외돼있지?"라고 물을 때 commit message가 답한다.

---

## 마무리

이번 incident의 *진짜 발견*은 알람 필터 한 줄이 아니다. **모니터링 스택이 인프라 약점에 의해 자기 자신을 위한 알람을 만들고 있었다**는 메타-관찰이다. 르무엘이 WiFi+single-host control-plane인 한, apiserver의 일시적 503은 계속 날 거고, 그걸 polling하는 모든 sidecar는 ERROR를 찍는다. KSM은 재시작하고, Grafana sidecar는 polling 실패를 알리고, Prometheus도 5xx 받을 거다.

해결책 두 종류:

1. **인프라 약점을 고친다** — Ethernet으로 가거나 control-plane을 더 안정적인 머신으로. 본 환경은 *포트폴리오 홈랩*이라 의도된 선택, 안 함.
2. **알람 룰을 환경에 맞춘다** — 자기-참조 노이즈는 필터링, 진짜 장애 신호만 통과. 이번에 한 거.

진짜 production이라면 1번을 우선시한다. 홈랩이라면 2번이 합리적이다. 어느 쪽이든 *어느 약점이 어떤 알람 노이즈로 새고 있는지 명확히 파악*해두는 게 중요하다. 그 매핑이 있으면 어느 날 진짜 장애가 발생했을 때 "이건 알람 노이즈인가, 신호인가" 0.5초 만에 판단할 수 있다.

> **TL;DR** — ELK 알람 "monitoring 45건"은 grafana k8s-sidecar의 apiserver polling 실패였다. 시간 조사하다 UTC/KST 헷갈리고, KSM 가설로 30분 헛돌고, 결국 알람의 ES 쿼리를 직접 재현해서야 찾았다. 노이즈 필터 한 줄로 끝났지만 진짜 교훈은 *"모니터링 스택이 모니터링 알람을 만드는 자기-참조 루프"*를 식별한 것. 알람 룰은 코드처럼 git에 두고 GitOps로 관리하라.
