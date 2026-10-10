---
layout: post
title: "[CS300 #240] 비용 관리 (FinOps) — 클라우드 청구서를 엔지니어링 문제로 다루기"
date: 2026-10-10 22:00:00 +0900
categories: [cs]
tags: [cs300, devops, finops, cloud-cost, kubernetes]
---

컴퓨터공학 300 주제 시리즈의 240번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

FinOps 는 엔지니어링·재무·사업 조직이 함께 클라우드와 기술 비용을 실시간에 가깝게 보고(Inform), 줄일 곳을 찾고(Optimize), 그것을 일상 운영에 녹이는(Operate) 실천 체계다. 핵심은 "비용을 쓰는 사람이 비용을 본다"는 것이다.

## 왜 필요한가

온프레미스 시절에는 서버를 사는 일이 구매 절차를 거쳤다. 클라우드에서는 엔지니어가 명령 한 줄로 월 수백만 원짜리 자원을 만든다. 오토스케일러는 스스로 노드를 늘리고, 잊힌 테스트 환경은 몇 달씩 돌고, 로그는 조용히 쌓인다. 청구서는 한 달 뒤에 재무팀에 도착하는데, 재무팀은 어떤 서비스의 어떤 결정이 비용을 만들었는지 모른다.

비용을 만드는 결정은 엔지니어가 하고, 비용을 보는 사람은 재무팀이다. 이 간극을 메우는 것이 FinOps 다. 비용은 성능·가용성과 마찬가지로 설계 시 고려해야 할 비기능 요구사항이 된다.

## 핵심 개념

### FinOps Foundation 의 정의와 원칙

FinOps Foundation 은 FinOps 를 "기술의 비즈니스 가치를 최대화하고, 시의적절한 데이터 기반 의사결정을 가능하게 하며, 엔지니어링·재무·사업 팀 간 협업으로 재무적 책임을 만드는 운영 프레임워크이자 문화적 실천"으로 정의한다. 원칙은 다음과 같다.

| 원칙 | 요지 |
|---|---|
| Teams need to collaborate | 재무·기술·제품·리더가 함께 지출과 가치를 관리한다 |
| Business value drives technology decisions | 비용·품질·속도 사이의 의식적 트레이드오프 |
| Everyone takes ownership for their technology usage | 쓰는 팀이 자기 비용을 책임진다 |
| FinOps data should be accessible, timely, and accurate | 비용 데이터는 빨리, 정확히, 누구나 볼 수 있게 |
| FinOps should be enabled centrally | 약정 구매·도구·표준은 중앙 팀이 지원 |
| Take advantage of the variable cost model | 쓰는 만큼 내는 모델을 적극 활용 |

### 세 단계: Inform → Optimize → Operate

FinOps 는 한 번 하고 끝나는 프로젝트가 아니라 반복하는 주기다.

1. **Inform**: 비용을 보이게 한다. 태그·레이블로 비용을 팀·서비스·환경에 배분(allocation)하고, 대시보드와 예산·이상 경보를 만든다.
2. **Optimize**: 줄일 곳을 찾는다. 과대 할당 축소(rightsizing), 쓰지 않는 자원 삭제, 약정 할인, 스팟 인스턴스, 저장 계층 이동.
3. **Operate**: 이를 습관으로 만든다. 정책·자동화·정기 리뷰, 단위 비용 지표 추적.

### 배분(allocation)과 태깅

배분이 안 되면 아무도 책임지지 않는다. 클라우드 자원에는 `team`, `service`, `env` 같은 태그를 강제하고, 태그 없는 자원은 생성 단계에서 막거나 경보를 건다.

쿠버네티스는 여기서 한 단계 더 어렵다. 노드 하나의 비용을 여러 네임스페이스의 파드가 나눠 쓰기 때문이다. OpenCost 같은 도구는 노드 비용을 파드의 자원 requests 와 실제 사용량 중 큰 쪽을 기준으로 나눠 네임스페이스·레이블별 비용을 계산한다. 어느 파드에도 배분되지 않은 노드 용량은 **유휴(idle) 비용**으로 따로 표시된다.

### 최적화 수단

| 수단 | 내용 | 주의 |
|---|---|---|
| Rightsizing | 실제 사용량에 맞게 인스턴스·requests 축소 | 피크와 여유를 고려. 메모리는 줄이면 OOM |
| 유휴 자원 정리 | 붙지 않은 디스크, 오래된 스냅샷, 꺼지지 않은 개발 환경 | 삭제 전 소유자 확인 |
| 스케줄 기반 끄기 | 개발·스테이징을 야간·주말에 0으로 | 업무 시간 정의 |
| 약정 할인 | 1~3년 사용 약정으로 단가 인하(예약 인스턴스, savings plan 등) | 실제 사용률이 낮으면 손해 |
| 스팟/선점형 | 회수될 수 있는 대신 크게 싼 용량 | 중단을 견디는 워크로드만 |
| 저장 계층화 | 오래된 데이터를 저렴한 계층으로 | 꺼낼 때 비용·지연 |
| 데이터 전송 | 영역·리전 간 트래픽, 인터넷 송출 | 아키텍처 단계에서 고려 |

### 단위 경제(unit economics)

총비용이 늘었다는 것만으로는 좋고 나쁨을 알 수 없다. 사용자가 두 배가 됐다면 비용이 1.5배 늘어난 것은 좋은 소식이다. 그래서 "주문 1건당 인프라 비용", "활성 사용자 1명당 월 비용"처럼 사업 지표로 나눈 단위 비용을 추적한다. 이것이 "Business value drives technology decisions" 원칙의 구체적 형태다.

## 직접 해 보기

쿠버네티스 노드 비용을 네임스페이스별로 배분하고, rightsizing 효과와 약정 할인의 손익분기 사용률을 계산해 보자. 단가는 계산을 위한 **가상의 값**이다.

```python
NODE_COST_PER_H = 0.40          # 가상의 노드 시간당 비용
NODE_CPU, NODE_MEM = 8.0, 32.0  # 코어, GiB
NODES = 3
# 시간당 단가를 CPU:메모리 = 1:1 로 나눠 자원 단가를 정한다(단순화)
CPU_PRICE = NODE_COST_PER_H * 0.5 / NODE_CPU
MEM_PRICE = NODE_COST_PER_H * 0.5 / NODE_MEM

workloads = {  # ns: (cpu_request, cpu_used, mem_request, mem_used)
    "shop":      (6.0, 4.5, 20.0, 14.0),
    "search":    (8.0, 1.2, 24.0, 10.0),
    "batch":     (2.0, 2.6,  8.0,  9.0),
    "observ":    (3.0, 2.0, 12.0, 10.0),
}
total = NODE_COST_PER_H * NODES
allocated = 0
print("ns       cost/h   cpu(req/used)  efficiency")
for ns, (cr, cu, mr, mu) in workloads.items():
    cost = max(cr, cu) * CPU_PRICE + max(mr, mu) * MEM_PRICE
    allocated += cost
    eff = (cu * CPU_PRICE + mu * MEM_PRICE) / cost
    print(f"{ns:8} ${cost:6.3f}   {cr:4.1f}/{cu:4.1f}      {eff:5.0%}")
print(f"cluster ${total:.3f}/h, allocated ${allocated:.3f}, idle ${total - allocated:.3f}")

# search 를 실제 사용량 + 30% 여유로 rightsizing
cr, cu, mr, mu = workloads["search"]
new_cr, new_mr = round(cu * 1.3, 1), round(mu * 1.3, 1)
saved = ((cr - new_cr) * CPU_PRICE + (mr - new_mr) * MEM_PRICE) * 24 * 30
print(f"\nrightsize search: cpu {cr}->{new_cr}, mem {mr}->{new_mr}, "
      f"save ~${saved:.2f}/month of requested capacity")

# 약정 할인: 할인율 d 이면 사용률이 (1-d) 이상이어야 이득
for d in (0.2, 0.4):
    print(f"commitment discount {d:.0%}: break-even utilization = {1 - d:.0%}")
```

결과는 다음과 같다.

```
ns       cost/h   cpu(req/used)  efficiency
shop     $ 0.275    6.0/ 4.5        73%
search   $ 0.350    8.0/ 1.2        26%
batch    $ 0.121    2.0/ 2.6       100%
observ   $ 0.150    3.0/ 2.0        75%
cluster $1.200/h, allocated $0.896, idle $0.304

rightsize search: cpu 8.0->1.6, mem 24.0->13.0, save ~$164.70/month of requested capacity
commitment discount 20%: break-even utilization = 80%
commitment discount 40%: break-even utilization = 60%
```

읽는 법은 이렇다.

- `search` 는 CPU 8코어를 요청하고 1.2코어만 쓴다. 요청한 만큼 노드 자리를 차지하므로 비용은 요청 기준으로 붙는다. 효율이 26% 로 가장 낮고 rightsizing 1순위다. 절약액은 "요청 용량 기준"이다. 실제 청구서가 줄어들려면 비게 된 자리만큼 노드를 줄이거나 다른 워크로드를 올려야 한다.
- `batch` 는 요청보다 더 쓴다. 비용은 사용량 기준으로 붙는다. 비용보다 안정성(스로틀링·축출 위험)을 먼저 봐야 할 신호다.
- 배분되지 않은 나머지는 유휴 비용이다. 노드 수가 수요보다 많다는 뜻이다.
- 약정 할인율이 40% 면, 약정한 용량의 60% 이상을 실제로 써야 이득이다. 확실히 계속 쓸 기저 부하에만 약정한다.

## 현업에서는

- **보이게 하는 것이 절반이다.** 팀별 월간 비용 리포트를 슬랙·메일로 자동 발송하기만 해도 비용이 줄어드는 경우가 많다. 아무도 보지 않던 자원이 보이기 시작하기 때문이다.
- **이상 탐지 경보.** 일일 비용이 평소의 1.5배를 넘으면 경보를 건다. 오토스케일 폭주, 무한 재시도 루프, 로그 폭증, 유출된 자격증명으로 만든 채굴 인스턴스가 대개 여기서 잡힌다.
- **requests 위생.** 쿠버네티스 비용의 상당 부분은 "요청만 하고 안 쓰는" 용량에서 나온다. VPA 의 권장값(추천 모드)이나 Prometheus 의 실사용 분위수를 보고 분기마다 조정한다(238번).
- **아키텍처 결정에 비용을 넣는다.** 영역 간 트래픽이 과금되는 환경에서 서비스 메시·복제를 영역을 가로질러 구성하면 전송 비용이 커진다. 설계 리뷰 체크리스트에 비용 항목을 둔다.
- **온프레미스·홈랩에도 같은 사고방식.** 장비를 이미 샀더라도 전력, 교체 주기, 그리고 무엇보다 "자원이 모자라 새 장비를 사야 하는 시점"이 비용이다. 노드별 requests 대비 실사용을 보면 같은 장비로 더 많은 서비스를 올릴 수 있는지, 정말 증설이 필요한지 판단할 수 있다.

## 확인 문제

1. FinOps 의 세 단계를 순서대로 쓰고 각 단계의 대표 활동을 하나씩 들라.
2. 쿠버네티스에서 네임스페이스별 비용을 requests 기준으로 배분하는 이유는?
3. 총 클라우드 비용이 지난달보다 30% 늘었다. 이것만으로 나쁘다고 할 수 없는 이유와, 함께 봐야 할 지표는?
4. 약정 할인율이 30% 일 때 약정이 이득이 되는 최소 사용률은?
5. 스팟 인스턴스에 올리기 적합한 워크로드와 부적합한 워크로드를 하나씩 들라.

### 풀이

1. Inform(태깅·배분·대시보드), Optimize(rightsizing·약정 할인·유휴 자원 정리), Operate(정책·자동화·정기 리뷰).
2. 요청한 만큼 스케줄러가 노드 자원을 예약해 다른 파드가 쓸 수 없기 때문이다. 실제로 그보다 더 쓰면 사용량 기준을 쓴다.
3. 사용량·매출이 함께 늘었을 수 있다. 주문당·사용자당 비용 같은 단위 비용을 봐야 한다.
4. 70%.
5. 적합: 중단돼도 재시도할 수 있는 배치·CI 작업, 상태 없는 수평 확장 워커. 부적합: 단일 인스턴스 DB, 중단되면 안 되는 상태 저장 서비스.

## 더 읽을거리 (References)

- FinOps Foundation, [What is FinOps?](https://www.finops.org/introduction/what-is-finops/)
- FinOps Foundation, [FinOps Principles](https://www.finops.org/framework/principles/)
- AWS Well-Architected Framework, [Cost Optimization Pillar](https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html)
- OpenCost, [OpenCost Specification](https://opencost.io/docs/specification)
