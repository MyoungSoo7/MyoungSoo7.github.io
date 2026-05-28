---
layout: post
title: "홈랩 K3s 5노드의 CPU 가 모자랄 때 — 데이터센터의 Capacity Planning 흉내내기"
date: 2026-05-29 00:30:00 +0900
categories: [infra, homelab]
tags: [k3s, kubernetes, capacity-planning, sre, homelab, scheduling, taints, affinity, over-commit, tco]
---

홈랩 K3s 5노드 클러스터를 *프로덕션처럼* 굴리다 보면, 어느 날 *"왜 자꾸 CPU 가 모자라지?"* 가 시작된다. 빌드는 늦어지고, 배치 잡은 밀리고, 가끔 응답이 느려진다. 노드 한 대 더 살까? 어떤 사양으로? *얼마짜리까지* 사야 하나?

이건 사실 *데이터센터에서 SRE/플랫폼팀이 매 분기마다 하는 일* — **Capacity Planning** 이다. 큰 회사에선 Prometheus·Grafana·Cloud Cost API 가 다 자동화돼있지만, *그 결정의 뼈대* 는 홈랩에서도 똑같이 적용된다.

이 글은 *내 K3s 클러스터에 CPU 가 모자라기 시작한 어제 밤*, 노드 한 대 추가 결정을 내리기까지의 *진단·분석·의사결정 프로세스* 를 데이터센터 표준 절차와 매핑해 정리한다.

> 본 글의 IP 주소·노드 이름·매물 가격은 *실제 내 환경* 기준입니다. 너의 환경엔 그대로 적용하지 말고 *프로세스* 만 차용해서 본인 데이터로 다시 계산하세요.

---

## TL;DR

| 단계 | 데이터센터 표준 절차 | 내 홈랩에서 한 일 |
|---|---|---|
| 1 | Utilization / Saturation / Errors (USE) 측정 | `kubectl top` + `kubectl describe nodes` |
| 2 | Over-commit ratio 분석 | requests/limits 합계 vs node capacity 비교 |
| 3 | 자원 *비대칭* 식별 | CPU vs 메모리 vs 스토리지 노드별 매트릭스 |
| 4 | Scale-out vs Scale-up 결정 | 노트북 한 대 추가 vs 큰 서버 한 대 추가 |
| 5 | TCO 모델 (하드웨어 + 전력 + 운영) | 35만 매물 + 알리 메모리 + 전력 +3만/월 |
| 6 | Bin Packing — 워크로드 배치 설계 | Node label / taint / NodeAffinity |
| 7 | SLO 기반 *언제 다시 평가할지* 결정 | "louise 메모리 80% 넘으면 알람" |

---

## 0. 문제: 체감은 있는데 데이터가 없다

먼저 *체감 증상* 부터:

- `mvn clean install` 이 갑자기 5분에서 12분으로 늘어남
- academy 의 ffmpeg HLS 인코딩 잡이 *대기열에 쌓임*
- lemuel-xr 의 embedding 배치가 야간에 안 끝남
- 가끔 Grafana 대시보드가 *살짝* 느려짐

이걸 *"CPU 가 모자란 것 같다"* 라고 결론내리는 건 위험하다. 진짜 원인은 메모리 swap 일 수도, 디스크 I/O 일 수도, 네트워크 latency 일 수도, *그저 노드 한 대의 일시적 부하* 일 수도 있다.

데이터센터 운영의 첫째 원칙: **체감 ≠ 진단**. 측정해서 *어디가 어떻게 모자란지* 데이터로 확인해야 다음 단계로 간다.

---

## 1. USE 방법론 — 무엇을 어떻게 측정할 것인가

Brendan Gregg (Netflix 출신 시스템 성능 분석가) 가 정리한 **USE** 프레임워크가 출발점:

- **U**tilization: 자원이 *얼마나 일하는 중* 인가 (예: CPU 80% 점유)
- **S**aturation: 그 자원이 *얼마나 밀려있는* 가 (예: 대기 큐 길이)
- **E**rrors: *에러 카운트* (예: OOM kill, throttle 횟수)

K8s 에선 이걸 다음과 같이 본다:

```bash
# Utilization
$ kubectl top nodes

# Saturation (CPU throttle, memory pressure)
$ kubectl describe node <node>   # Conditions 섹션
$ kubectl get events -A | grep -iE "throttl|oom|evict"

# Errors
$ kubectl get pods -A --field-selector=status.phase=Failed
$ journalctl -u k3s | grep -iE "oom|killed"
```

내 클러스터 실측값 (5노드 K3s v1.35.4):

```
$ kubectl describe nodes | awk '...'   # requests vs capacity

david   | CPU cap=6   req=4345m (72%) | MEM cap=15.8GB req=10.5GB (66%)
ilwon   | CPU cap=12  req=5905m (49%) | MEM cap=32.2GB req=23.6GB (73%)
lemuel  | CPU cap=4   req=105m  (3%)  | MEM cap=32.8GB req=0.2GB  (0.5%) [cordoned]
louise  | CPU cap=8   req=4475m (56%) | MEM cap=16.2GB req=14.5GB (90%) ⚠️
solomon | CPU cap=4   req=705m  (18%) | MEM cap=15.8GB req=3.5GB  (22%)
```

평균만 보면 *CPU 45%, 메모리 46% 점유* 라 "여유 있어 보임". **이게 함정.**

---

## 2. Over-commit Ratio — 평균이 거짓말한다

Kubernetes 의 *Requests* 는 *최소 보장량*, *Limits* 는 *최대 사용량*. Limits 합계는 capacity 를 초과할 수 있다 (over-commit). 평소엔 문제 없지만, *피크* 가 동시에 오면 throttle 또는 OOM.

```
david   | CPU limit 합 23 / capacity 6   = 383% over-commit
ilwon   | CPU limit 합 29.7 / capacity 12 = 248% over-commit
louise  | CPU limit 합 26 / capacity 8   = 325% over-commit
```

세 워커 모두 *300~400%* over-commit. 일반적으로 *200% 이하* 가 안전선이라 본다. 즉:

- 평균 부하 시: CPU 45% 점유 (정상)
- 피크 부하 동시 발생 시: limit 합계 78 코어 vs capacity 30 코어 → **CPU 가 절대 부족**
- 결과: 워크로드들이 *서로* 의 CPU 시간 뺏기 → throttle → 응답 늦어짐

**진단 결론**: 평균 부하는 문제 없음. *피크 부하 분산* 이 안 됨. 즉 *Saturation* 이 진짜 병목.

---

## 3. 자원 비대칭 — CPU 만 모자란 게 아니다

USE 분석 다음 단계는 *어떤 차원이 비대칭* 인지 찾기.

| 노드 | CPU 코어 | RAM | CPU/RAM 비율 |
|---|---|---|---|
| david | 6 | 16GB | 2.7 GB/core |
| ilwon | 12 | 32GB | 2.7 GB/core |
| lemuel | 4 | 32GB | **8.0 GB/core** (cordon) |
| louise | 8 | 16GB | 2.0 GB/core |
| solomon | 4 | 16GB | 4.0 GB/core |
| **평균** | | | **3.9 GB/core** |

평균 *3.9 GB/core* 인데, *lemuel 만 8 GB/core* 로 튀어나옴. 이게 *RAM 헤비, CPU 라이트* 워크로드를 받기 좋은 비대칭 노드.

반면 *louise* 는 *2.0 GB/core* 로 *CPU 헤비, RAM 가난* — 메모리 90% 점유에서 보이듯 RAM 이 먼저 터질 형국.

**해석**:
- *모든 노드의 RAM/CPU 비율을 평준화* 하면 안 됨. 어떤 워크로드는 RAM 헤비, 어떤 건 CPU 헤비.
- 노드 비대칭을 *taint/affinity* 로 *활용* 하는 게 데이터센터의 표준 패턴 (Google Borg, AWS EC2 인스턴스 패밀리 c5/m5/r5 가 정확히 이런 분류)
- 새 노드를 추가할 때도 *어떤 비율의 노드가 더 필요한지* 부터 결정

---

## 4. Scale-out vs Scale-up — 어느 쪽으로 늘릴 것인가

자원 부족 진단이 끝나면 *어떻게 늘릴지* 결정:

| 전략 | 정의 | 장점 | 단점 |
|---|---|---|---|
| **Scale-up (세로)** | 기존 노드의 CPU/RAM 업그레이드 | 운영 노드 수 안 늘어 단순 | 단일 노드 한계, 다운타임 |
| **Scale-out (가로)** | 노드 개수 추가 | HA 강화, 무중단 추가 | 운영 복잡, 네트워크 오버헤드 |

내 환경 분석:
- lemuel/louise (노트북) → 메모리 증설 불가 (이미 max). *Scale-up 불가능*
- solomon (2014 Mac Mini) → 메모리 증설 불가. *Scale-up 불가능*
- ilwon (데스크탑) → 메모리 증설 가능. 하지만 한계 32~64GB
- → **Scale-out 만 가능**. 새 노드 한 대 추가가 답

새 노드의 *사양* 은 *비대칭 분석* 결과를 기반으로:
- 현재 부족한 차원: *CPU 헤비 워크로드 수용 capacity*
- 부족하지 않은 차원: *전체 메모리* (lemuel 의 32GB 가 묶여있어서 그렇지, 총량은 충분)
- → **CPU 많고 메모리 적정인 노드** 가 정답

마침 *Dell PowerEdge R730xd 중고 매물* 이 한국 시장에서 30~50만원대로 풀려있다. CPU 20코어 / 16GB RAM 인 사양이 *내가 원하는 비대칭* 과 정확히 일치한다.

---

## 5. TCO — 진짜 비용은 가격표가 아니다

데이터센터에서 노드 한 대의 비용 = *Total Cost of Ownership*. 3년 또는 5년 horizon 으로 계산:

```
TCO = 하드웨어 매입 비용
    + 전력비 (idle + load 가중 평균) × 24h × 365일 × N년
    + 운영 인건비 (모니터링/패치/장애 대응 시간)
    + 공간 비용 (랙 임대, 냉방 부하)
    + 기회 비용 (유지보수에 쓴 시간 동안 못 한 일)
```

내 옵션 두 가지:

### 옵션 A: 미니멀 35만원 매물

```
하드웨어: R730xd 본체 (CPU 20코어 + 16GB + iDRAC Ent + 듀얼 PSU)  35만원
추가: 알리 메모리 32GB × 2 (DDR4 RDIMM 2400)                    15만원
추가: 쿠팡 SATA SSD 500GB (OS 부팅용)                            7만원
추가: 변환 어댑터 + 케이블 잡비                                  2만원
─────────────────────────────────────────────────────────────────
하드웨어 매입 합계                                              59만원

전력비: idle ~200W × 24h × 30일 = 144kWh/월
       144 × 200원/kWh = 약 3만원/월
       3년 = 108만원

3년 TCO 합계                                                   ~167만원
```

### 옵션 B: 풀세팅 168만 매물

```
하드웨어: R730xd 풀세팅 (CPU 32코어 + 128GB + SSD 3.2TB + HDD)  168만원
추가: 없음                                                       0원
─────────────────────────────────────────────────────────────────
하드웨어 매입 합계                                             168만원

전력비: idle ~250W × 24h × 30일 = 180kWh/월
       180 × 200원/kWh = 약 3.6만원/월
       3년 = 130만원

3년 TCO 합계                                                   ~298만원
```

**TCO 차이: 131만원**. 하지만 옵션 B 는 *3.2배 메모리, 32배 스토리지, 더 큰 CPU*. 비례하지 않게 더 강력.

**의사결정 기준**: *워크로드가 그 자원을 다 쓸 수 있느냐* 가 핵심.

내 경우:
- 현재 클러스터의 *CPU 부족* 만 해소하면 충분 (백엔드 공부에 집중하는 게 우선)
- 메모리 128GB 는 지금 워크로드론 다 못 씀
- → **옵션 A 가 답**. 131만원 절약 + *학습할 시간 확보*

데이터센터에서도 같은 결정 흐름이다. "더 좋은 거 사면 더 좋다" 가 아니라, *지금 부족한 차원만 정확히 메우는* 게 가성비 최강.

---

## 6. Bin Packing — 새 노드에 무엇을 보낼 것인가

새 노드가 도착하면 *모든 워크로드가 자동으로* 거기로 옮겨가지 않는다. 명시적으로 *스케줄링 의도* 를 표현해야 한다.

### 노드 라벨링 (capability 광고)

```yaml
# 새 노드 (issachar) — CPU 헤비 워커
apiVersion: v1
kind: Node
metadata:
  name: issachar
  labels:
    kubernetes.io/role: worker
    workload-class: cpu-heavy
    hardware-generation: dell-13g
    storage-class: hdd  # SSD 적음
```

### Taint 로 *원치 않는* 워크로드 차단

```bash
# CPU 헤비 워크로드만 받게
kubectl taint nodes issachar dedicated=cpu-heavy:PreferNoSchedule
```

`PreferNoSchedule` 은 *soft constraint* — scheduler 가 *최대한* 피하지만 다른 노드가 다 차면 와도 OK. *NoSchedule* 은 *hard constraint* — 명시적 toleration 없으면 *절대* 안 옴.

### Workload 쪽에서 *toleration + affinity*

```yaml
# academy ffmpeg HLS 인코딩 Job — CPU 헤비, RAM 라이트
spec:
  template:
    spec:
      affinity:
        nodeAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            preference:
              matchExpressions:
              - key: workload-class
                operator: In
                values: [cpu-heavy]
      tolerations:
      - key: dedicated
        operator: Equal
        value: cpu-heavy
        effect: PreferNoSchedule
      containers:
      - name: ffmpeg
        resources:
          requests:
            cpu: "4"
            memory: 2Gi
          limits:
            cpu: "8"
            memory: 4Gi
```

이렇게 *워크로드별로 라벨링* 해두면, 새 노드 추가 시 *자동으로* 적합한 워크로드만 모인다.

데이터센터에서 이건 *수십~수백 개 워크로드 × 수십 개 노드 패밀리* 매트릭스가 된다. Borg / Mesos / K8s scheduler 의 핵심 일감이 이 *Bin Packing 최적화*.

---

## 7. SLO 기반 *다음 평가* 자동화

Capacity planning 은 *한 번 하고 끝* 이 아니다. 워크로드는 자라고, 노드는 늙고, 사용자 트래픽은 변한다.

**데이터센터 표준**: SLO (Service Level Objective) 기반 *알람* 으로 *다음 capacity 재평가 시점* 을 자동으로 알린다.

```yaml
# Prometheus Alert 예시
- alert: NodeMemoryHighUtilization
  expr: |
    (1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) > 0.80
  for: 30m
  labels:
    severity: warning
  annotations:
    summary: "{{ $labels.instance }} memory > 80% for 30min"
    description: "Capacity planning 재평가 필요"

- alert: ClusterCPUOverCommitted
  expr: |
    sum(kube_pod_container_resource_limits{resource="cpu"}) /
    sum(kube_node_status_capacity{resource="cpu"}) > 2.5
  for: 1h
  labels:
    severity: warning
```

내 환경엔 아직 Prometheus alert 룰을 *느슨하게* 둔 상태. 이번 노드 추가 작업 이후 *louise 메모리 80%* / *클러스터 over-commit 2.5x* 두 alert 부터 깔 예정.

---

## 8. 홈랩 vs 진짜 데이터센터 — 무엇이 같고 무엇이 다른가

### 같은 것

| 항목 | 홈랩 | 데이터센터 |
|---|---|---|
| USE 측정 | `kubectl top` | Prometheus + Grafana |
| Over-commit 관리 | 수동 계산 | VerticalPodAutoscaler / quota |
| 비대칭 인지 | 표 그리기 | Node 패밀리 (m5/c5/r5/x1) |
| Taint/affinity | 수동 라벨링 | 스케줄러 정책 + GitOps |
| TCO 모델 | 엑셀 | Cloud Cost API + FinOps tooling |

### 다른 것

| 항목 | 홈랩 | 데이터센터 |
|---|---|---|
| 노드 추가 시간 | 매물 알아보기 1주 + 도착 1주 + 셋업 1일 | terraform apply 5분 |
| 단일 노드 죽으면 | 직접 가서 케이블 흔들기 | 자동 교체 (cluster-autoscaler) |
| 전력 | 직접 콘센트 부담 | 임대료에 포함 (보통) |
| 냉방 | 거실 에어컨 | HVAC 자동 |
| 보안 | 공유기 + ufw | VPC + IAM + zero-trust mesh |
| 비용 단위 | 만원 | 만 달러 |
| 의사결정자 | 본인 | SRE + Finance + Engineering Manager 3자 회의 |

홈랩의 *진짜 가치* 는 **결정 흐름을 직접 다 해보는 것**. 데이터센터의 자동화된 답이 *어떤 결정의 결과* 인지 *직접* 겪어보는 것.

cluster-autoscaler 가 자동으로 노드 늘려주는 그 한 줄의 yaml 뒤에는, *내가 위에서 한 USE 분석 + 비대칭 식별 + TCO 비교 + Bin Packing 설계* 가 *코드로 박혀있는* 거다. 자동화의 *작동 원리* 를 모르면 자동화가 잘못된 결정을 내릴 때 디버깅 못 한다.

---

## 9. 내가 내린 결정 (요약)

진단:
- ✅ USE 측정: requests 평균 45%, **limits 평균 300%+ over-commit**
- ✅ 비대칭 식별: louise 메모리 90%, lemuel cordon, david/louise CPU 헤비
- ✅ Saturation 원인: 피크 부하 시 limits 합계 vs capacity 비례

결정:
- ✅ Scale-out 만 가능 (노트북 노드들 Scale-up 불가)
- ✅ CPU 헤비 / 메모리 적정 노드 추가
- ✅ R730xd 35만 매물 + 알리 메모리 64GB + 쿠팡 SSD = **59만원**
- ✅ 풀세팅 168만 옵션 *기각* (TCO 131만원 절약, 학습 시간 확보)

다음 단계:
- ⏳ Ubuntu Server 설치 → `issachar` hostname → ufw disable → K3s agent 합류
- ⏳ Node label `workload-class=cpu-heavy` + taint
- ⏳ academy ffmpeg, lemuel-xr embedding 배치 점진 이관
- ⏳ Prometheus alert 룰 추가: louise mem > 80%, cluster over-commit > 2.5x

---

## 10. 마무리 — Capacity Planning 은 *직관* 이 아니라 *데이터* 다

체감만으로 결정하면:
- "느린 것 같으니 큰 거 사자" → 168만 풀세팅
- 실제 부족한 자원만큼 *과투자* → 메모리 128GB 가 놀고, 전력비만 매월 +3만원

데이터로 결정하면:
- 진짜 부족한 차원 (CPU 헤비 capacity) 만 정확히 메움
- 131만원 절약 + 다음 부족 시점 (메모리) 까지 *학습 시간* 확보
- 그 사이 SLO alert 자동화로 *다음 평가 시점* 도 예약

데이터센터의 capacity planning 은 *위 7단계의 자동화* 일 뿐이다. 홈랩에서 손으로 한 번 해보면 클라우드 콘솔의 *그 인스턴스 추천 화면* 이 왜 그렇게 생겼는지 보이기 시작한다.

---

## 참고

- Brendan Gregg, [The USE Method](https://www.brendangregg.com/usemethod.html)
- Google SRE Book, Chapter 5 — *Eliminating Toil* / Chapter 18 — *Software Engineering in SRE*
- AWS Well-Architected Framework — Cost Optimization Pillar
- Kubernetes 공식 문서 — [Assigning Pods to Nodes](https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/)
- 본 글의 R730xd 매입·셋업 이야기: [Dell R730XD iDRAC 첫 셋업 — 함정 5종]({% post_url 2026-05-28-dell-r730xd-idrac-first-setup-traps %})
