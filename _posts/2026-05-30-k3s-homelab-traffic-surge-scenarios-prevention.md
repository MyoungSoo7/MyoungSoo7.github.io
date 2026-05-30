---
layout: post
title: "K3s 5 노드 홈랩 — *트래픽이 *몰릴 때 *어디부터 *터지나*, 그리고 *예방 *대책*"
date: 2026-05-30 12:45:00 +0900
categories: [kubernetes, infrastructure, sre, homelab]
tags: [k3s, kubernetes, homelab, traffic-surge, ddos, hpa, rate-limiting, cloudflare, traefik, postgresql, wifi]
---

> *''*홈랩이니까 *부담 없겠지""*. *맞는 말 같지만 *완전히 *틀리기도 한다*. *내 K3s 위에 *Cloudflare Tunnel 을 *달면 *그 순간부터 *''*인터넷 전체''* 가 *내 5 노드 클러스터를 *때릴 수 있는 *외부 표면이 *된다*. *AWS 처럼 *알아서 *오토스케일링 하지 않는 *환경에서 *트래픽 *피크가 *오면 *어디부터 *터지고, *어떻게 *살아남게 *설계할 것인가* 가 *''*홈랩 운영자의 *진짜 *공부""*.
>
> 이 글은 *5 노드 K3s 홈랩* (lemuel / louise / david / ilwon / solomon, *WiFi 운영*) 위에 *Cloudflare Tunnel + Traefik + 다수의 서비스* 가 *얹혀있는 *실제 상황* 에서 *트래픽이 *몰릴 때 *어디부터 깨지는가* 를 *층층이 *해부 하고, *각 층의 *예방 대책 *을 *''*돈 안 들이고 *할 수 있는 것 → 돈 드는 것""* 순서로 본다.

대상은 *''*K3s / Rancher / 자체 *클러스터*'' 를 *집/사무실에서 *돌리는 *모든 *운영자, 그리고 *''*우리 *프로덕션도 *AWS 인데 *비슷한 *고민 한다""* 는 *백엔드 시니어*.

---

## 1. 출발점 — *''*홈랩이 *세상에 *연결될 때*''*

```
[인터넷]
   │
   ▼
[Cloudflare Edge]          ← *전 세계 *수백 *데이터센터, *''*1 차 *방어 *겸 *가속""*
   │ (Cloudflare Tunnel — outbound long-poll)
   ▼
[K3s 5 노드 클러스터]
  - lemuel  (master, 컨트롤 플레인 주력)
  - louise
  - david
  - ilwon   ← *최고 사양 *워커 (CPU 12 / Mem 32G)
  - solomon
   │
   ▼
[Traefik Ingress]          ← *라우팅 *+ TLS 종료*
   │
   ▼
[Pod 들 — Ghost / ArgoCD UI / Grafana / Kibana / *백엔드 서비스]
   │
   ▼
[PostgreSQL / Elasticsearch / Redis]
```

이 *5 노드 클러스터의 *물리적 *제약*:

- *Home WiFi* — *공유 대역폭, 802.11 *RTS/CTS 경합*
- *전기료* — *상시 100W ~ 200W*
- *단일 ISP 라인*
- *백업 *없음 (있더라도 *집 안에)*

이게 *''*우리 클러스터의 *현실""* 이다. *''*AWS 처럼 *알아서 *증설""* 안 된다.

---

## 2. *트래픽 *시나리오 *5 종*

### 2.1 *시나리오 A — *''*친구 / SNS 에 *링크 공유""*

```
크기:     순간 동시접속 *수십 ~ 수백*
지속:     수 분 ~ 1 시간
특성:     정상 사용자, *각자 *비슷한 패턴
위험도:   ★★☆☆☆
```

가장 자주 *오는 *시나리오. *''*개인 블로그가 *해커뉴스에 *올라가는 그날""* 이 *대표 케이스. *Cloudflare 의 *캐시가 *대부분 *흡수*.

### 2.2 *시나리오 B — *''*검색엔진 / 봇 *크롤링""*

```
크기:     초당 *수 ~ 수십 req*, *지속 *수시간 ~ 수일*
특성:     User-Agent: *Googlebot / Bingbot / 이상한 *오픈소스 크롤러
위험도:   ★★★☆☆ (지속적 부담)
```

검색엔진 *크롤러는 *정상적이지만, *''*매 페이지마다 *동적 *렌더링""* 이 일어나면 *DB 부하 *지속적 누적*.

### 2.3 *시나리오 C — *''*취미 *DDoS / 스크립트 키디""*

```
크기:     초당 *수백 ~ 수천 req*
특성:     UDP/TCP SYN flood, HTTP GET 반복, *botnet
위험도:   ★★★★☆
```

*''*아무나 *대상이 될 수 있음""*. Cloudflare 의 *Free 플랜도 *기본 *DDoS 방어* 가 *상당히 *강함. 그래도 *L7 가 *Origin 까지 *오면 *깨질 수 있음*.

### 2.4 *시나리오 D — *''*내부 *cascade (서비스 → DB) 폭주""*

```
크기:     1 개 서비스의 버그가 *DB 쿼리 폭증
특성:     *외부 *트래픽 *없어도 *내부 *cascade*
위험도:   ★★★★★ (가장 잦고 *치명적)
```

*경험상 *가장 *자주 *클러스터 *흔드는 *시나리오. *''*한 서비스가 *PG connection 을 *고갈시키면 *그 PG 를 *공유하는 *모든 서비스가 *순차적으로 *죽음""*.

### 2.5 *시나리오 E — *''*악성 *targeted attack""*

```
크기:     수 *Gbps* 또는 *L7 정교 공격
특성:     봇넷 동원, *Cloudflare 우회 시도, *0-day 노림
위험도:   ★★★★★ (드물지만 *치명적)
```

*홈랩 *수준에선 *''*Cloudflare 가 *못 막으면 *우리도 *못 막는다""* 가 *현실. *대응은 *''*Origin IP 노출 *철저히 방지""* + *''*최악의 경우 *서비스 *중단 *수용""*.

---

## 3. *''*어디부터 *터지는가""* — *7 개 *깨짐 *지점*

### 3.1 *깨짐 #1 — *Cloudflare Tunnel 대역폭*

```
원인:     단일 *Tunnel connection 의 *처리량 한계
증상:     latency 증가 → timeout → 502
초기 신호: cloudflared 의 *''*concurrent connections""* 메트릭
```

*Cloudflare Tunnel 자체는 *수십 ~ 수백 Mbps 까지 *건강하게 *작동, 그 이상이면 *Origin (집 인터넷) 이 *먼저 *상한*. 우리 *환경에서는 *집 ISP *상행 대역폭이 *진짜 *상한선*.

### 3.2 *깨짐 #2 — *Traefik Ingress*

```
원인:     단일 Pod 가 *모든 *요청 *처리, *worker thread *고갈
증상:     *502 / 504 *간헐적
초기 신호: traefik *active connections, request_duration_seconds histogram
```

K3s 기본 Traefik 은 *Deployment *1 replica*. 트래픽이 *몰리면 *그 1 Pod 가 *병목.

### 3.3 *깨짐 #3 — *애플리케이션 Pod 자원 한계*

```
원인:     Pod 의 CPU/memory limit 도달
증상:     OOMKilled, *throttling, *응답 *수 초~분*
초기 신호: container_memory_working_set_bytes / cpu_throttling
```

### 3.4 *깨짐 #4 — *PostgreSQL connection pool 고갈*

```
원인:     pgbouncer/HikariCP *max_connections 도달
증상:     ''*FATAL: connection limit exceeded""*, *쿼리 대기, *전체 서비스 마비
초기 신호: pg_stat_activity, *''*backend_count_per_state""*
```

*''*가장 *흔하고 *치명적""*. *''*1 서비스의 폭주가 *5 서비스를 *동시에 *죽임""*.

### 3.5 *깨짐 #5 — *etcd 리더 선출 *불안*

```
원인:     컨트롤 *플레인 노드 *CPU 과부하 → *etcd lease *만료
증상:     ''*leader election lost""* → *Pod 스케줄링 *중단, *kubectl *느림
초기 신호: etcd_server_leader_changes_seen_total, *apiserver 99 분위*
```

K3s 는 *master 1 노드 (lemuel) 에 *컨트롤 플레인 + etcd 가 *함께 있음*. *그 노드의 *CPU 가 *터지면 *전 클러스터 *불안정.

### 3.6 *깨짐 #6 — *WiFi 대역 + 노드 간 *통신*

```
원인:     Pod ↔ Pod 통신이 *WiFi 를 *경유 (특히 *PG ↔ App, ES ↔ Logstash)
증상:     ''*context deadline exceeded""*, *내부 *latency 폭증
초기 신호: node_network_receive_drop_total, ping 손실*
```

*홈랩 *WiFi 운영의 *유일한 *진짜 약점*. *유선 *전환이 *가장 *비용 대비 효과 큼*.

### 3.7 *깨짐 #7 — *Logging 파이프라인 폭주*

```
원인:     트래픽 ↑ → 로그 ↑ → fluent-bit → Logstash → ES 폭증
증상:     fluent-bit *CrashLoopBackOff, *Logstash *OOM, *ES yellow/red
초기 신호: fluent-bit *buffer_size, *logstash *pipeline.events.duration*
```

*''*트래픽이 *몰리면 *로그도 *몰린다""* — *모니터링 인프라가 *먼저 죽으면 *''*뭐가 *문제인지 *알 수 없는 *상태""* 로 *침몰*.

---

## 4. *예방 대책 *— *돈 없이 *할 수 있는 것* 부터

### 4.1 *대책 1 — *Cloudflare 캐싱 *최대화* ($0)

```
[현재 추정]   Static asset 만 *기본 *캐시
[최적화]      Page Rules / Cache Rules 로 *HTML 도 *조건부 *캐시*

  - Cache Level: Cache Everything (Cookie 없는 경로만)
  - Edge Cache TTL: 30 min
  - Browser Cache TTL: 4 hours
  - Bypass Cache on Cookie: 로그인 사용자만 우회
```

이거 하나만 *해도 *대부분의 *Read-heavy 트래픽이 *Origin 까지 *안 옴*. *''*첫 페이지 *조회는 *Cloudflare 가 *처리, *우리는 *''*변경 시점""* 만 *서빙""*.

### 4.2 *대책 2 — *Cloudflare *Rate Limiting* ($0 ~ $5/월)

```
Free 플랜: 룰 *1 개 *(10 req/s 까지 *제한)
Pro 플랜:   룰 *10 개

권장 룰:
  - /wp-admin, /admin 경로 → 10 req/min per IP
  - /api 경로 → 100 req/min per IP
  - /login 경로 → 5 req/min per IP
```

*''*5 달러로 *대부분의 *script kiddie *방어""*. *L7 공격이 *Origin 에 *오기 전에 *Cloudflare 가 *차단*.

### 4.3 *대책 3 — *Traefik HPA *+ replicas* ($0)

```yaml
# helm-deploy 에서 *Traefik 을 *2 ~ 3 replicas 로
controller:
  replicas: 3
  resources:
    requests: { cpu: 100m, memory: 128Mi }
    limits:   { cpu: 1, memory: 512Mi }
  affinity:
    podAntiAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        - labelSelector: { matchLabels: { app: traefik } }
          topologyKey: kubernetes.io/hostname
```

*Anti-affinity 로 *서로 *다른 노드에 *분산. *한 노드 *죽어도 *2/3 살아남음.

### 4.4 *대책 4 — *애플리케이션 Pod *HPA + PDB* ($0)

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: ghost
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: ghost
  minReplicas: 2
  maxReplicas: 6
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80

---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: ghost-pdb
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: ghost
```

> **주의**: *''*HPA 가 *Pod 늘려도 *노드 자원이 *없으면 *Pending""*. *Cluster Autoscaler 가 *없는 홈랩에선 *''*HPA 의 *max replicas 를 *현실적으로""* 잡아야 함.

### 4.5 *대책 5 — *PostgreSQL pgbouncer + 서비스별 분리* ($0)

```
[현재]   여러 서비스가 *공유 PG 인스턴스의 *공유 user 로 *직접 연결
[개선]   pgbouncer 1 인스턴스 + 서비스별 *별도 user/database
        + max_client_conn 명시 + transaction-level pooling

[Spring Boot]
  spring.datasource.hikari.maximum-pool-size: 10   # ← *서비스 *전체에 *공유 *상한*

[PG]
  max_connections = 200
  서비스 A: pgbouncer pool 20
  서비스 B: pgbouncer pool 20
  서비스 C: pgbouncer pool 20
  ...
  → *''*1 서비스 *폭주가 *다른 서비스 *connection 을 *못 *훔침""*
```

*''*Triple defense""* — 앱 connection pool + pgbouncer + PG 자체 limit. *한 층이 *뚫려도 *다음 층이 *막음.

### 4.6 *대책 6 — *Circuit Breaker / Timeout* ($0, 코드 수정)

```java
// Spring Boot — *Resilience4j*
@Bean
public Resilience4jCircuitBreakerFactory factory() {
    var cfg = CircuitBreakerConfig.custom()
        .failureRateThreshold(50)
        .waitDurationInOpenState(Duration.ofSeconds(30))
        .slidingWindowSize(20)
        .build();
    var timeoutCfg = TimeLimiterConfig.custom()
        .timeoutDuration(Duration.ofSeconds(3))
        .build();
    return new Resilience4jCircuitBreakerFactory(
        CircuitBreakerRegistry.of(cfg),
        TimeLimiterRegistry.of(timeoutCfg));
}

@CircuitBreaker(name = "payment-gateway")
@TimeLimiter(name = "payment-gateway")
public CompletableFuture<PaymentResult> charge(PaymentCommand cmd) {
    return CompletableFuture.supplyAsync(() -> gateway.charge(cmd));
}
```

*''*외부 의존이 *느려져도 *내 서비스가 *같이 *느려지지 *않음""*. *''*Cascade 차단의 *핵심""*.

### 4.7 *대책 7 — *etcd / 마스터 *전용 노드 *분리* ($0 ~ 노드 추가)

```
[현재]   lemuel = master + worker (Pod 실행 같이)
[개선]   lemuel = master 전용 (taint: node-role.kubernetes.io/control-plane=:NoSchedule)
        louise/david/ilwon/solomon = worker 전용
```

*''*마스터 노드가 *애플리케이션 *부하 받지 *않게""* → etcd 안정성 확보.

> **주의**: *''*기억""* 메모리에 *''*일원은 *주력 워커, etcd 전용 분리 권고 금지""* 라고 *기록되어 *있음. *그 결정은 *유지하되, *대신 *lemuel 의 *application Pod 부담을 *최소화 하는 *방향이 *대안*.

### 4.8 *대책 8 — *Logging *backpressure* ($0)

```yaml
# fluent-bit
[FILTER]
    Name          throttle
    Match         *
    Rate          1000    # 초당 1000 라인 *상한*
    Window        300     # 5 분 *윈도우
    Interval      1s

# logstash
queue.type: persisted
queue.max_bytes: 1gb
```

*''*폭주 시 *최신 로그 *일부만 *드롭, 나머지 시스템은 *살아남음""*. *''*로그가 *없으면 *디버깅 *못 함""* 보다 *''*로그가 *부분 *없어도 *서비스 *살아 있음""* 이 *우선*.

### 4.9 *대책 9 — *WiFi → 유선 *전환* ($30 ~ $100)

*가장 *비용 대비 *효과 *큰 *물리적 *개선*:

- *기가비트 *스위치 *1 개*
- *Cat 6 케이블 *5 개*
- *전 노드 *유선 *연결*

*''*WiFi 의 *공유 대역 + RTS/CTS 경합""* 이 *''*전이중 *1 Gbps *유선""* 으로 *전환되면 *Pod ↔ Pod *지연이 *10 분의 1 수준* 으로 *떨어짐*. *''*홈랩 *제일 *값싼 *튜닝""*.

### 4.10 *대책 10 — *Cloudflare *Pro + WAF* ($20/월)

```
+ Image Resizing
+ Polish (이미지 자동 압축)
+ Rate Limiting *룰 *10 개
+ WAF *룰 (OWASP Top 10 기본)
+ Bot Fight Mode
```

*''*월 *20 달러로 *L7 공격의 *90% 차단""*. *Pro 한 단계가 *''*홈랩의 *방어선 *수십 배""*.

### 4.11 *대책 11 — *Cloudflare Workers / Pages* ($0 ~ $5/월)

```
[전략]
  - *Static 페이지 → Cloudflare Pages (집 서버 안 옴)
  - *API 의 *간단한 *변환 → Cloudflare Workers (집 서버 안 옴)
  - *Read-heavy *데이터 → KV Store 캐시
```

*''*요청의 *70% 가 *집까지 *안 옴""* 만들기. *집 서버는 *''*진짜 *비즈니스 로직만""* 처리.

---

## 5. *''*모니터링 *— *터지기 전에 *알아채기""*

### 5.1 *Prometheus *알람 룰 *7 종*

```yaml
groups:
- name: traffic-surge
  rules:
  - alert: HighRequestRate
    expr: sum(rate(traefik_service_requests_total[5m])) > 100
    for: 5m
    labels: { severity: warning }

  - alert: HighErrorRate
    expr: |
      sum(rate(traefik_service_requests_total{code=~"5.."}[5m]))
        / sum(rate(traefik_service_requests_total[5m])) > 0.05
    for: 5m

  - alert: PodCPUThrottling
    expr: |
      sum by (pod) (rate(container_cpu_cfs_throttled_periods_total[5m]))
        / sum by (pod) (rate(container_cpu_cfs_periods_total[5m])) > 0.5

  - alert: HighDBConnections
    expr: pg_stat_activity_count > 150
    for: 2m

  - alert: ETCDLeaderChange
    expr: increase(etcd_server_leader_changes_seen_total[15m]) > 1
    for: 1m
    labels: { severity: critical }

  - alert: NodeNetworkDrops
    expr: rate(node_network_receive_drop_total[5m]) > 100
    for: 5m

  - alert: LogstashLag
    expr: logstash_node_pipeline_events_filtered_total - logstash_node_pipeline_events_in_total > 10000
```

### 5.2 *대시보드 *3 패널*

1. **Traffic Overview** — req/s, 5xx 비율, p95 latency
2. **Resource Pressure** — node CPU/mem, pod throttling, DB conn count
3. **Saturation Signals** — fluent-bit buffer, network drops, etcd leader

이 *3 패널만 *상시 *띄워두면 *''*피크 *오기 전에 *증후 *보임""*.

### 5.3 *알람을 *어디로 보낼 것인가*

```
Telegram (즉시, 휴대폰 푸시)  ← *critical
Slack / Email (일상 trend)     ← *warning
대시보드 (상시 모니터링)        ← *모든 메트릭
```

*홈랩 *환경엔 *Telegram 이 *제일 *현실적. *''*Bot Token + Chat ID 만으로 *즉시 *푸시""*.

---

## 6. *''*실제 *피크가 *오면""* — *Runbook*

### 6.1 *대응 *5 단계*

```
[1] 인지 — Telegram 알람 또는 *대시보드
[2] 진단 — kubectl get events / Grafana / Kibana 빠른 *3 곳 *체크
[3] 임시 *완화 — *''*가장 *빠른 *효과의 *조치""*
[4] 근본 *조사 — *피크 *지나간 *후*
[5] 재발 *방지 — *Runbook / 대시보드 갱신
```

### 6.2 *임시 *완화 *5 카드*

피크 *순간 *''*30 초 안에 *결정""* 해야 하는 카드들:

#### 카드 1 — Cloudflare *''*Under Attack Mode""* 활성화
```
Cloudflare *대시보드 → Security → Settings → Under Attack Mode
효과: *모든 *방문자가 *5 초 *Cloudflare *검증 *통과 *후 진입
```

#### 카드 2 — *문제 *서비스 *replica *임시 증설
```bash
kubectl scale deploy/ghost --replicas=4
```

#### 카드 3 — *비핵심 *서비스 *임시 *중단
```bash
kubectl scale deploy/grafana --replicas=0    # *모니터링 *잠시 정지
kubectl scale deploy/argocd-server --replicas=0  # *배포 *잠시 정지
```

#### 카드 4 — *문제 *경로 *임시 *차단
```yaml
# Traefik middleware 로 *특정 *path *503*
apiVersion: traefik.io/v1alpha1
kind: Middleware
metadata: { name: emergency-block }
spec:
  errors:
    status: ["503"]
    service: { name: noop }
```

#### 카드 5 — *DB read replica 로 *읽기 *분산
```
[전제] read replica 가 *미리 *세팅 되어 있어야*
[조치] 애플리케이션 *config 의 *read DSN 을 *replica 로 *전환
```

### 6.3 *''*절대 *하지 말 것""*

- *''*피크 중에 *kubectl delete pod""* — *cascade 가속*
- *''*피크 중에 *helm upgrade / ArgoCD sync""* — *변경 + 부하 = 재앙*
- *''*피크 중에 *''*디버깅을 *위해 *로그 *전체 *받기""* — *DB 더 죽음*

---

## 7. *비용 *별 *권장 *조합*

### Tier 0 — *돈 *0원* (당장 가능)
- Cloudflare 캐시 최대화
- Traefik replicas ≥ 2
- 애플리케이션 HPA + PDB
- pgbouncer + 서비스별 DB user 분리
- Circuit breaker + Timeout
- Prometheus 알람 룰

### Tier 1 — *월 *수천 ~ 수만 원*
- 유선 네트워크 전환 ($30 ~ $100 일회)
- Cloudflare Pro ($20/월)
- 추가 노드 1 대 (구형 미니 PC $200)
- 외부 백업 (NAS / S3 Glacier)

### Tier 2 — *월 *수십만 원* (홈랩 → 준 프로덕션)
- Cloudflare Business ($200/월) + WAF custom rules
- AWS RDS Multi-AZ 대체 (월 $50 ~)
- ELK SaaS (Elastic Cloud / Loki Grafana)
- Cluster Autoscaler 로 *클라우드 노드 *증설

---

## 8. *''*결정 *흐름도""* — *''*우리 *클러스터의 *어느 *단계인가""*

```
Q1. 외부 노출 *서비스 있는가?
  └ No   → Cloudflare 불필요. 내부 *cascade 만 *대비
  └ Yes  → Q2

Q2. 트래픽 *분당 *100 req 이상 *정기적으로?
  └ No   → Tier 0 으로 *충분
  └ Yes  → Q3

Q3. 외부 *비즈니스 사용자 있는가?
  └ No   → Tier 0 + Tier 1 일부
  └ Yes  → Tier 1 + 모니터링 *상시 + Runbook

Q4. 매출 의존하는 서비스 있는가?
  └ No   → Tier 1 유지
  └ Yes  → Tier 2 + 외부 *전문 *모니터링
```

---

## 9. *정리 — *''*홈랩 운영의 *3 가지 *진실""*

> 1. ***''*Cloudflare 까지가 *내 *외벽이고, *그 안은 *내가 *직접 *지킨다.*''*
> 2. ***''*외부 트래픽 *피크 보다 *내부 *cascade 가 *더 자주 *클러스터를 *흔든다.*''*
> 3. ***''*예방의 *80% 는 *돈 안 *드는 *설정과 *코드 변경.*''*

K3s 5 노드 홈랩의 *진짜 강점* 은 *''*싸다""* 가 *아니다*. *''*모든 *레이어를 *내가 *이해하고 *제어할 수 있다""* 가 *진짜 가치*. *AWS 처럼 *''*마법으로 *알아서 *되는 *것""* 이 *없으니 *''*내가 *모르는 *상태에서 *조용히 *돈만 *나가는 일""* 도 *없다*.

> **마지막 한 문장**:
>
> *''*트래픽 폭주는 *피할 수 *없다*. *''*폭주가 *왔을 때 *어디서 *깨지고 *어떻게 *살아남는가""* 의 *시나리오를 *미리 *그려 두는 것이 *''*홈랩 *운영자의 *진짜 *역량""*. *그 시나리오가 *Cloudflare → Traefik → Pod → DB → 로깅 → WiFi 까지 *전 계층 *덮을 때 *비로소 *우리 클러스터는 *''*견딘다""* 라고 말할 수 있다.*''*

---

## 더 읽으면 좋은 자료

- *Google SRE Book*, *''Embracing Risk''* / *''Service Level Objectives''* 장
- *Google SRE Workbook*, *''Practical Alerting''* / *''Eliminating Toil''*
- *Cloudflare Learning Center* — *''DDoS Mitigation""*, *''Rate Limiting Best Practices""*
- *Kubernetes 공식 문서* — *''Horizontal Pod Autoscaler""*, *''Pod Disruption Budgets""*
- *PostgreSQL Wiki* — *''Number of Database Connections""*
- *Brendan Gregg*, *''Systems Performance""* — *''USE Method""* (Utilization / Saturation / Errors)
- *Mikhail Khludnev*, *''Robust client-server communication""*
- 본 블로그의 [별도 글](/2026/05/29/msa-kubernetes-elk-overengineering-breakeven-alternatives/) — *오버엔지니어링 손익분기점*
- *Cilium 블로그* — *eBPF 기반 *부하 분산 / 보안*
