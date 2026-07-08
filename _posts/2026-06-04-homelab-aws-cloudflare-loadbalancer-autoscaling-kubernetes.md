---
layout: post
title: "*홈랩 K3s · AWS · Cloudflare* — *로드밸런서와 *오토스케일링의 *가능성을 *3 인프라에서 *비교 *고찰*"
date: 2026-06-04 05:00:00 +0900
categories: [infrastructure, kubernetes, cloud, homelab]
tags: [k3s, kubernetes, aws, cloudflare, load-balancer, autoscaling, hpa, metallb, traefik, cloudflare-workers, eks, asg]
---

> *''*우리 *홈랩 *5 노드 *클러스터도 *AWS 처럼 *알아서 *스케일링 *되나요?""*. *''*Cloudflare Tunnel 만 *물려 있는데 *로드밸런서가 *진짜 *필요 한가요?""*. *작은 *K3s 클러스터를 *운영 *시작한 *모든 *개발자가 *반드시 *마주치는 *질문이다.
>
> *답은 *''*AWS / Cloudflare / 홈랩 *3 인프라가 *근본적으로 *다른 *물리적 *제약 *위에 *서 있다""* 는 *사실에서 *시작한다*. *AWS 는 *''*돈을 *쓰면 *알아서""* 가 *전제*, *Cloudflare 는 *''*Edge 가 *대신 *해준다""* 가 *전제*, *홈랩은 *''*내가 *내 *서버를 *직접 *제어 한다""* 가 *전제다*. 같은 *''*로드밸런서""* 와 *''*오토스케일링""* 이 *3 곳에서 *완전히 *다른 *것을 *의미한다.

이 글은 *K3s 5 노드 *홈랩 *위에 *Cloudflare Tunnel 을 *얹어 *운영 *중인 *환경을 *기준으로, *AWS 의 *공식 *답안과 *Cloudflare 의 *Edge *전략과 *우리 홈랩의 *''*진짜 *가능한 *것""* 을 *3 축 비교한다. 마지막은 *''*홈랩 + Cloudflare + (필요 시) AWS""* 의 *하이브리드 *패턴으로 *마무리한다.

대상은 *''*K3s 운영자""*, *''*AWS 만 *써본 *백엔드 *시니어""*, 그리고 *''*Cloudflare 의 *역할이 *실제로 *얼마나 *큰가""* 가 *궁금한 *모든 *개발자*.

---

## 1. *3 인프라의 *근본 *전제*

```
[AWS]                  [Cloudflare]            [홈랩 K3s]
 ───────                ───────────              ──────────
 ●  돈을 쓰면           ●  Edge 가 대신          ●  내가 직접
 ●  무한 확장 가능      ●  지구 분산           ●  WiFi + 5 노드
 ●  managed service     ●  serverless edge      ●  control 완전
 ●  분 단위 과금        ●  요청 단위 과금       ●  전기·인터넷 고정
 ●  SLA 99.99%          ●  SLA 100%             ●  SLA 자체 책임
```

이 *근본 *전제가 *''*같은 *기능을 *3 인프라가 *3 가지 *방식으로 *구현 한다""* 의 *원인이다*. *그 *3 가지 *방식의 *비용·복잡도·결과가 *다르다*.

---

## 2. *로드밸런서 *비교*

### 2.1 *AWS — *''*L4 / L7 / 글로벌 모두 *완성형""*

```
[AWS 의 로드밸런서 4 종]

ELB (Classic) — 레거시, 신규 사용 X
ALB — L7, HTTP/HTTPS/gRPC, host/path 기반 라우팅 (대부분 답)
NLB — L4, TCP/UDP, 극단적 처리량 (수백만 RPS)
GLB — Global Accelerator, 전 세계 endpoint 통합
```

**ALB 의 *전형적 *구성**:
```
인터넷
   ↓
Route 53 (DNS)
   ↓
ALB (Multi-AZ, auto-scaling 자체)
   ↓
Target Group (EC2 / ECS / EKS Pods)
   ↓
실제 워크로드
```

**EKS 통합** — AWS Load Balancer Controller 가 *Ingress 를 *읽어 *자동으로 *ALB 프로비저닝.

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
spec:
  rules: [...]
```

→ ALB 가 *자동 *생성됨. *비용: *시간당 *~$0.025 + *처리 *바이트당.

**장점**:
- Multi-AZ 자동 *분산
- WAF / Shield 통합 (DDoS 방어)
- ACM 으로 *TLS 자동 *관리
- *SLA 99.99% *보장

**단점**:
- *대당 *월 ~$20 ~ $100+ (트래픽 *따라)
- *복잡한 *설정 (Target Group, Listener Rule, SG)
- *Lock-in (AWS API 강결합)

### 2.2 *Cloudflare — *''*Edge 에서 *모든 게 *시작""*

```
[Cloudflare 의 로드밸런싱 *3 층]

Tier 1: Anycast DNS — 전 세계 *수백 *데이터센터로 *자동 *라우팅
Tier 2: Cloudflare Load Balancer — Origin Pool 관리 + 헬스 체크
Tier 3: Workers / Pages — Edge 에서 *직접 *처리 (Origin 없음)
```

**Cloudflare Tunnel + Load Balancer**:
```
인터넷
   ↓
Cloudflare Edge (300+ DC)
   ↓
Anycast → 가장 가까운 DC
   ↓
Cloudflare Load Balancer
   ├─ Origin Pool A (primary, 홈랩)
   ├─ Origin Pool B (failover, AWS)
   └─ Origin Pool C (DR, 다른 리전)
   ↓
Cloudflare Tunnel (outbound long-poll)
   ↓
홈랩 K3s
```

**장점**:
- *전 세계 *지연 시간 *극단적으로 *낮음 (Anycast)
- *DDoS 방어 *기본 (무료 *플랜도)
- *Cloudflare Workers 와 *결합 시 *''*Origin 호출 없이 *Edge 에서 *완료""*
- 가격: Free / Pro $25/월 / Business $200/월 / Enterprise 협상

**단점**:
- *Origin 의 *성능은 *결국 *Origin 책임 (홈랩 *느리면 *그대로 *느림)
- *세션 *유지 (sticky session) 가 *까다로움
- *WebSocket *지연 *Edge 거치는 *비용

### 2.3 *홈랩 K3s — *''*Traefik / MetalLB / kube-vip*''*

```
[홈랩 K3s 의 LB 옵션 3 종]

Traefik   — K3s 기본 *Ingress Controller (L7, HTTP/HTTPS)
MetalLB   — BGP 또는 *L2 (ARP) 로 *외부 *VIP 제공
kube-vip  — Master 노드의 *HA + Service VIP
```

**현실의 *홈랩**:
- *AWS 의 *ALB 와 *같은 *''*외부 LB""* 가 *없음*
- *Cloudflare Tunnel 이 *''*외부 LB""* 역할
- *내부에선 *Traefik 이 *Ingress 처리

**전형적 *구성**:
```
인터넷
   ↓
Cloudflare Edge (DDoS, WAF, 캐시)
   ↓
Cloudflare Tunnel (cloudflared Pod × 2 in K3s)
   ↓
Traefik (NodePort or LoadBalancer Service)
   ↓
Pod 들
```

**MetalLB 가 *왜 *필요한가**:
- 홈랩에선 *AWS / GCP 같은 *''*Cloud Provider LB""* 가 *없음
- `kubernetes.io/load-balancer-class` 가 *비어 있으면 *Service type=LoadBalancer 가 *Pending 영원
- MetalLB 가 *''*내부 IP 풀에서 *외부 *VIP 할당""* 으로 *그 *공백 *채움

**MetalLB *L2 모드** (홈랩 *일반적 *선택):
```yaml
apiVersion: metallb.io/v1beta1
kind: IPAddressPool
metadata: { name: home-pool, namespace: metallb-system }
spec:
  addresses:
    - 10.0.0.200-10.0.0.220
---
apiVersion: metallb.io/v1beta1
kind: L2Advertisement
metadata: { name: l2adv, namespace: metallb-system }
```

→ Service type=LoadBalancer 가 *10.0.0.200 같은 *VIP 받음.

> **현실 *권장**: *''*Cloudflare Tunnel 만 *써도 *외부 *진입은 *충분""*. *MetalLB 는 *내부 *VIP 가 *진짜 *필요 *할 때만*. *''*K8s 표준""* 을 *맞추려고 *MetalLB 도입하면 *오버엔지니어링.

### 2.4 *3 인프라의 *LB 비교 *표*

| | AWS ALB | Cloudflare LB | 홈랩 (Cloudflare Tunnel + Traefik) |
|---|---|---|---|
| L7 라우팅 | ✓ | ✓ | ✓ (Traefik) |
| Multi-region | ✓ (ALB + Route53) | ✓ (Anycast) | ✗ |
| DDoS 방어 | + WAF / Shield | ✓ 기본 | ✓ (Cloudflare 통해) |
| TLS 관리 | ACM 자동 | 자동 | Cloudflare 가 종료 |
| SLA | 99.99% | 100% (선언) | 자체 책임 |
| 비용 (월) | $20 ~ $200+ | Free ~ $200 | $0 (인프라 비용만) |
| 학습 곡선 | 중 (AWS 전반) | 낮음 | 중 (Traefik) |
| 락인 | 매우 높음 | 중간 (DNS 의존) | 없음 |
| 운영 부담 | 거의 0 | 0 | 본인 |

---

## 3. *오토스케일링 *비교*

### 3.1 *AWS — *''*ASG + HPA + Cluster Autoscaler 의 *3 축""*

```
[AWS 오토스케일링 4 종]

ASG (Auto Scaling Group)        — EC2 인스턴스 수 자동 조정
EKS Cluster Autoscaler          — K8s 노드 자동 추가/제거
HPA (Horizontal Pod Autoscaler) — Pod replicas 자동 조정
KEDA                             — 이벤트 기반 (Queue depth 등)
```

**전형적 *AWS EKS 오토스케일링 *체인**:
```
트래픽 ↑
   ↓
HPA 가 CPU 80% 감지
   ↓
Pod replicas 3 → 6 확장
   ↓
하지만 노드 자원 부족 (Pending)
   ↓
Cluster Autoscaler 가 ASG 에 신호
   ↓
ASG 가 EC2 추가 (1 → 2 node)
   ↓
새 노드에 Pod 스케줄
   ↓
2 분 내 완료
```

**비용**:
- EC2 ASG: *분 단위 *과금
- Spot Instance 활용으로 *60 ~ 80% *절감 가능
- 단점: *예측 *못 함 → *예산 *변동성

**KEDA — *이벤트 기반 *스케일링**:
```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
spec:
  scaleTargetRef: { name: worker-deployment }
  triggers:
    - type: aws-sqs-queue
      metadata: { queueURL: ..., queueLength: "100" }
```

→ SQS 메시지 *100 개 *쌓이면 *Pod 자동 *확장.

### 3.2 *Cloudflare — *''*Serverless = *무한 *스케일링""*

Cloudflare 의 *오토스케일링 *철학:
> *''*Workers 는 *''*스케일링""* 개념이 *없다. *요청이 *오면 *즉시 *실행, *끝나면 *증발.""*

```
[Cloudflare Workers]

요청 1 ─→ V8 Isolate 인스턴스 → 응답
요청 2 ─→ V8 Isolate 인스턴스 → 응답
요청 1000 ─→ 1000 개의 V8 Isolate 동시 실행

→ 콜드 스타트 < 5ms
→ 동시성 무제한 (사실상)
→ 과금: 요청 100 만 건 = $0.50
```

**Workers + KV / Durable Objects + R2** 의 *3 축으로:
- *상태 *없는 *처리: Workers
- *Key-Value: KV
- *세션 / 동시성: Durable Objects
- *오브젝트 *스토리지: R2 (S3 호환)

**한계**:
- *각 *요청 *50 ms CPU 시간 *제한 (paid 는 *높음)
- *npm 패키지 *호환성 *제약 (Node API 일부만)
- *상태 유지 워크로드 *부적합

### 3.3 *홈랩 K3s — *''*HPA 까지는 *가능, *그 위는 *어려움""*

```
[홈랩 K3s 의 오토스케일링 현실]

✓ HPA (Pod 단위)              — 가능
✗ Cluster Autoscaler (노드)    — 어려움 (물리 노드 자동 추가 X)
△ VPA (Vertical Pod Autoscaler) — 가능, 권장 안 함 (Pod 재시작)
✓ KEDA                          — 가능 (이벤트 소스 외부 의존)
```

**HPA 가 *홈랩에서 *동작 *하는 *전제**:
- *Metrics Server 설치 필수* — `kubectl top` 이 *동작 하는지 확인
- *Pod resource requests 설정*
- *충분한 *노드 *여유* — 모자라면 *Pending

**HPA 예시**:
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
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
        target: { type: Utilization, averageUtilization: 70 }
```

**Cluster Autoscaler 가 *왜 *어려운가**:
- *물리 *노드를 *''*자동 *부팅""* 시킬 *방법 *없음
- Wake-on-LAN + 사전 *프로비저닝 된 *노드가 *있어야 *흉내 가능
- 현실: *상시 *충분한 *노드 *유지가 *유일한 답

> **홈랩 *오토스케일링의 *진짜 한계**: *''*Pod 는 *스케일 *되지만 *노드는 *고정""*. *AWS 의 *''*무한 *확장""* 환상이 *홈랩에선 *''*max 가 *정해진 *확장""* 으로 *현실화.

### 3.4 *3 인프라의 *오토스케일링 비교 *표*

| | AWS | Cloudflare | 홈랩 K3s |
|---|---|---|---|
| Pod / 함수 단위 | HPA / KEDA | 자동 (Workers) | HPA / KEDA |
| 노드 단위 | Cluster Autoscaler + ASG | N/A (서버리스) | ✗ 사실상 *불가* |
| 스케일 *속도 | 분 단위 | 밀리초 | Pod 분 단위 |
| 최대 확장 | 사실상 무한 (예산 한계) | 사실상 무한 | 노드 자원 한계 |
| 비용 *모델 | 사용량 비례 | 요청당 | 고정 (전기) |
| 콜드 *시작 | 분 (EC2) ~ 초 (Lambda) | 5ms (Workers) | 0 (Pod 항상 떠 있음) |
| 운영 *복잡도 | 높음 | 매우 낮음 | 중간 |

---

## 4. *우리 *홈랩 K3s 에서 *진짜 *가능한 것*

### 4.1 *5 노드 *클러스터의 *capacity 현실*

```
[가정: 일반적 홈랩 5 노드]
- CPU 총 합: 50 vCore
- RAM 총 합: 100 GB
- 디스크: 노드당 500GB ~ 2TB

[K3s 오버헤드 차감]
- 시스템 Pod: ~3 GB RAM
- Cloudflared / Traefik / ArgoCD / Prometheus: ~10 GB RAM

[실 가용]
- 워크로드: ~85 GB RAM, ~45 vCore
```

이 *capacity 안에서 *모든 *오토스케일링이 *''*가능""*. 그 *바깥은 *''*불가능""*.

### 4.2 *가능한 *3 가지*

#### **가능 1 — *Pod 단위 *HPA**
*노드 자원이 *남는 *한도* 내에서 *Pod 확장. 트래픽 *피크 *대응에 *유효.

```yaml
HPA: ghost
  minReplicas: 2
  maxReplicas: 5    # ← 노드 수에 *맞춰 *현실적으로
  cpu target: 70%
```

> **주의**: maxReplicas 를 *너무 *높게 *잡으면 *''*Pod Pending 폭증 → 다른 *서비스가 *Pending""* 의 *연쇄 *장애*.

#### **가능 2 — *이벤트 *기반 *KEDA**
```yaml
KEDA ScaledObject:
  source: PostgreSQL (queue depth)
  scaleTargetRef: worker-deployment
  minReplicas: 0
  maxReplicas: 5
  pollingInterval: 30s
```

*''*Idle 시 *0 Pod, *작업 *들어오면 *확장""* 으로 *자원 *효율 ↑.

#### **가능 3 — *수동 *''*Pre-warming""*
*트래픽 *예상되는 *시간 *전 *수동 *scale up:
```bash
# 한국 *오후 *피크 *시간 *직전
kubectl scale deploy/api --replicas=4
```

크론으로 *자동화도 *가능 — *AWS 의 *Scheduled Scaling 흉내.

### 4.3 *불가능한 *3 가지*

#### **불가능 1 — *진짜 *Cluster Autoscaler**
*물리 노드를 *Pod *부담에 *맞춰 *자동 *증가 *불가능. *사전 *프로비저닝된 *노드만 *사용.

#### **불가능 2 — *Multi-region HA**
*홈랩은 *''*1 위치""*. *집 인터넷 *끊기면 *서비스 *중단. *Cloudflare LB 의 *Failover 로 *AWS 백업 *가능 (하이브리드).

#### **불가능 3 — *예측 *불가능한 *대형 *피크 대응*
*예상 *트래픽의 *5 배 *오면 *클러스터 *전체 *마비. *Cloudflare 의 *캐싱 + Rate Limiting 으로 *''*Origin 까지 *오지 *못하게""* 막는 게 *유일한 답.

---

## 5. *하이브리드 *패턴 — *''*홈랩 + Cloudflare + (선택) AWS""*

### 5.1 *Pattern 1 — *''*Cloudflare 가 *모든 *외벽""*

```
[가장 *작은 *비용으로 *최대 *효과]

인터넷
  ↓
Cloudflare Edge
  ├─ DDoS 방어
  ├─ WAF
  ├─ 캐싱 (Static + HTML Cache Everything)
  ├─ Rate Limiting (Pro $20/월)
  └─ Workers (간단한 API → Edge 에서 처리)
  ↓
Cloudflare Tunnel
  ↓
홈랩 K3s (실제 비즈니스 로직)
  ├─ HPA (Pod 수준)
  └─ Pre-warming (시간대별)
```

**비용**: Cloudflare Pro $20/월 + 홈랩 전기 ~$30/월 = **월 $50**.

**효과**:
- *대부분의 *트래픽이 *Origin 까지 *안 옴 (캐싱)
- *DDoS 의 *90% *Cloudflare 에서 *차단
- *예상 트래픽의 *5 배까지 *흡수 가능

### 5.2 *Pattern 2 — *''*홈랩 + AWS Failover""*

```
인터넷
  ↓
Cloudflare Load Balancer (Business $200/월)
  ├─ Primary Pool: 홈랩 (낮은 비용)
  └─ Failover Pool: AWS Lambda / ECS (고가용)
  ↓
홈랩 정상 → 100% 홈랩
홈랩 다운 → 즉시 AWS 로 전환 (5 ~ 30 초)
```

**비용**: Cloudflare Business $200 + AWS *대기 *비용 (Lambda 라면 *거의 *0).

**효과**:
- *홈랩 *장애 시 *자동 *복구
- *''*99.5% → 99.99%""* SLA *상승

### 5.3 *Pattern 3 — *''*Workers 가 *진짜 *서버""*

```
인터넷
  ↓
Cloudflare Edge
  ↓
Cloudflare Workers (실제 비즈니스 로직)
  ↓ (필요 시)
Origin (홈랩 DB 또는 외부 API)
```

*''*트래픽의 *80% 가 *Edge 에서 *완결""*. Origin 부담 *극단적 ↓.

**적합**:
- 단순 API
- *Auth, *결제, *세션 관리 같은 *상태 *없는 작업

**부적합**:
- 복잡한 *비즈니스 로직 (Spring Boot 등)
- *큰 *데이터 *처리

---

## 6. *결정 *흐름도*

```
Q1. 외부 *노출 *서비스 *있는가?
  └ No  → Cloudflare 불필요, 내부 LB (Traefik) 만으로 *충분
  └ Yes → Q2

Q2. 예상 *피크 *트래픽이 *분당 *1000 req 이하?
  └ Yes → Cloudflare Free + 홈랩 으로 *충분
  └ No  → Q3

Q3. 트래픽이 *수만 ~ 수십만 *req/min 일 *경우?
  └ Cloudflare Pro/Business 도입 + 홈랩의 *HPA + 노드 추가

Q4. 99.99% *이상 *SLA 가 *비즈니스적으로 *필요?
  └ Yes → 하이브리드 (Pattern 2: 홈랩 + AWS Failover)
  └ No  → 홈랩만으로 *충분 (Pattern 1)

Q5. 예측 *불가능한 *대형 *피크 *가능성?
  └ Yes → Cloudflare 캐싱 + Rate Limiting 적극, AWS Lambda backup
  └ No  → 홈랩 + Cloudflare 만
```

---

## 7. *권장 *조합* — *5 노드 *홈랩 *기준*

### **Stage 0 — *지금*
```
Cloudflare Tunnel (Free)
  ↓
Traefik (K3s 기본)
  ↓
Pod (HPA replicas 1 ~ 3)
```
*비용: *전기 *~$30/월. *적합: *개인 *프로젝트, *POC.

### **Stage 1 — *트래픽 *증가 시 ($20 ~ $50/월)*
```
Cloudflare Pro
  - Rate Limiting *룰 *10 개
  - WAF
  - 이미지 *최적화
  ↓
Traefik (replicas 2 ~ 3, Anti-affinity)
  ↓
HPA + Cluster *capacity *상시 *충분 *유지
```
*적합: *외부 *사용자 *있는 *서비스, *데모.

### **Stage 2 — *비즈니스 *서비스 시 ($200 ~ $500/월)*
```
Cloudflare Business + Load Balancer
  ├─ Primary: 홈랩
  └─ Failover: AWS Lambda / ECS Fargate
  ↓
홈랩 + AWS 하이브리드
```
*적합: *매출 *의존 *서비스, *수만 *MAU.

### **Stage 3 — *대규모 ($1000+/월)*
```
Cloudflare Enterprise + Workers
  ↓
AWS EKS (multi-AZ + Cluster Autoscaler)
  + 홈랩 (Cold backup)
```
*적합: *수십만 *MAU, *24/7 *비즈니스.

---

## 8. *정리 — *3 인프라의 *3 가지 *진실*

> 1. ***''*AWS = 돈으로 *모든 것을 *산다*. *오토스케일링 *무한, *비용도 *예측 불가.*''*
> 2. ***''*Cloudflare = 전 세계 *Edge 가 *대신 *해준다*. *Origin 부담 *극단적 *감소, *상태 워크로드 *제약.*''*
> 3. ***''*홈랩 = *내가 *직접 *제어 한다*. *비용 *예측 가능, *확장의 *물리적 *상한 존재.*''*

**우리 5 노드 K3s 홈랩의 *현실적 *위치**:
- *Pod 단위 *HPA *가능* — 노드 자원 안에서
- *Cluster Autoscaler *불가능* — 물리 노드 *고정
- *Cloudflare 의 *Edge 가 *''*가상 *오토스케일링""* 역할 — 캐싱 + DDoS + Rate Limiting

**진짜 *교훈**:
> *''*홈랩의 *경쟁력은 *''*AWS 와 *같은 *기능""* 이 *아니라 *''*Cloudflare 와 *결합해 *AWS 의 *80% *효과를 *5% *비용으로""* 달성하는 *조합 *전략이다.""*

*5 노드 *홈랩 단독으로는 *AWS 와 *경쟁할 *수 없다. *그러나 *Cloudflare 가 *''*세계 분산""* 과 *''*DDoS 방어""* 와 *''*캐싱""* 을 *대신 해주면, *우리 *홈랩은 *''*비즈니스 로직 *실행""* 에만 *집중 *하면 된다. *그 *조합이 *''*월 *수십 달러로 *수만 *MAU 서비스""* 를 *가능 하게 한다.

> **마지막 *한 *문장**:
>
> *''*로드밸런서와 *오토스케일링은 *기술적 *주제처럼 *보이지만 *실은 *''*어디까지 *내가 *직접 *제어 하고 *어디부터 *외부에 *맡길 것인가""* 의 *경계 *결정이다. *그 경계가 *비용·복잡도·확장성을 *결정하고, *그 *결정이 *우리 *홈랩의 *진짜 *가치를 *만든다.""*

---

## 더 읽으면 *좋은 *자료

- *AWS Well-Architected Framework — Reliability Pillar*
- *Cloudflare Learning Center — Load Balancing*
- *Kubernetes 공식 *문서 — Horizontal Pod Autoscaler*
- *MetalLB 공식 *문서*
- *Traefik 공식 *Ingress 가이드*
- *Brendan Burns, **Designing Distributed Systems*** (2018) — 분산 *원리
- *Liz Rice, **Container Security*** (2020) — 컨테이너 *경계*
- *본 블로그의 *별도 *글*: [K3s 5 노드 홈랩 — *트래픽 폭주 *시나리오와 *예방 *대책](/2026/05/30/k3s-homelab-traffic-surge-scenarios-prevention/)
- *본 블로그의 *별도 *글*: [MSA · Kubernetes · ELK — *오버엔지니어링의 *손익분기점과 *대안](/2026/05/29/msa-kubernetes-elk-overengineering-breakeven-alternatives/)
- *Cloudflare Workers 공식 *튜토리얼*
