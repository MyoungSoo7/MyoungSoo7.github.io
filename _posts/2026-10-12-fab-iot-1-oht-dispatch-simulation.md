---
layout: post
title: "[팹 IoT 연구 1] OHT 루프 레일 시뮬레이션 — 차량 수·배차 규칙·대기 위치가 FOUP 배송 시간을 어떻게 바꾸나"
date: 2026-10-12 00:10:00 +0900
categories: [iot]
tags: [semiconductor, iot, mqtt, amhs, oht, simulation, dispatching]
---

> 이 글의 수치는 전부 **노트북에서 돌린 이산 사건 시뮬레이션(합성 데이터)** 결과다. 레일 길이, 차량 속도, 호이스트 시간, 요청률은 실험용으로 정한 가정값이며 어느 실제 팹의 값도 아니다. 실제 팹 규모나 업계 통계는 확인할 수 없어 일부러 쓰지 않았다.

## 연구 질문

OHT(Overhead Hoist Transport) 차량은 천장 레일을 따라 웨이퍼 캐리어(FOUP)를 장비 로드포트와 스토커 사이로 나른다. 레일이 일방통행이면 앞 차가 멈출 때 뒤 차도 선다. 그래서 "차를 더 넣으면 빨라지나"는 단순한 질문이 아니다.

이번 실험에서 답하려는 것은 세 가지다.

1. **차량 수**를 늘리면 FOUP 배송 시간(요청 생성부터 목적지 하역 완료까지)의 평균과 p95 는 어떻게 변하나. 언제부터 이득이 사라지나.
2. **배차 규칙** — 가장 오래 기다린 요청/가장 오래 쉰 차량부터(FIFO) vs 가장 가까운 차량/가장 가까운 요청부터(nearest) — 의 차이는 얼마나 되나. nearest 의 고질적 약점인 꼬리 지연(starvation)은 드러나나.
3. **빈 차의 대기 위치** — 레일 위에 그냥 서 있기, 가까운 대피선(siding)으로 빠지기, 대피선을 고르게 나눠 쓰기(재배치) — 가 레일 막힘(blocking)과 배송 시간에 주는 영향은.

마지막으로, 이 시뮬레이터의 상태·사건을 홈랩에서 이미 쓰고 있는 MQTT 기반 가상 물류 로봇 구조에 얹는다면 차량이 무엇을 어떤 토픽으로 발행해야 하는지 설계한다.

## 배경 — 반도체 팹에서 이 문제

팹의 자동 반송 설비(AMHS)는 베이 사이를 잇는 interbay 반송과 베이 안의 intrabay 반송으로 나뉘어 논의되어 왔고, 300 mm 팹의 AMHS 전반은 Agrawal·Heragu 의 서베이(2006)가 정리했다. 반송 시스템과 상위 물류 제어(MCS) 사이의 장비 모델은 SEMI E82(Interbay/Intrabay AMHS SEM, IBSEM)로, 차량과 장비 로드포트 사이에서 캐리어를 주고받는 핸드오프 신호는 SEMI E84(Enhanced Carrier Handoff Parallel I/O Interface)로 표준화되어 있다([SEMI E82](https://store-us.semi.org/products/e08200-semi-e82-specification-for-interbay-intrabay-amhs-sem-ibsem), [SEMI E84](https://store-us.semi.org/products/e08400-semi-e84-specification-for-enhanced-carrier-handoff-parallel-i-o-interface)). 표준 본문은 유료라 이 글에서는 제목 수준 이상의 내용을 인용하지 않는다.

배차(dispatching) 규칙 연구의 고전적 출발점은 AGV 쪽이다. Egbelu·Tanchoco(1984)는 AGV 배차 규칙을 차량 주도(vehicle-initiated)와 작업장 주도(workcenter-initiated)로 나눠 특성을 비교했다. 이 글의 두 규칙도 그 구분을 따라 요청 도착 시점(작업장 주도)과 차량 해제 시점(차량 주도)의 선택을 각각 정의했다. OHT 쪽으로 오면 Kim 외(2009)가 대형 팹에서 헝가리안 알고리즘 기반 할당을, Benzoni 외(2023)가 차량 look-ahead 배차를 다룬다. 이 글은 그 기준선이 되는 가장 단순한 두 규칙과 빈 차 처리 방식만 장난감 레이아웃에서 재 본다.

이 모델에서 차량은 호이스트를 내리는 동안 레일 구간을 점유하고, 뒤 차는 기다린다. 차량이 많으면 빈 차가 픽업 지점 가까이 있을 확률은 높아지지만 정체도 는다. 두 힘이 어디서 만나는지가 관심사다.

## 실험 설계

### 모델

[SimPy](https://simpy.readthedocs.io/en/latest/) 4.1.2 로 이산 사건 시뮬레이션을 만들었다. 레이아웃은 다음과 같다(전부 가정값).

| 항목 | 값 |
|---|---|
| 레일 | 일방통행 루프 300 m, 3 m 구간 100개 |
| 구간 제어 | 한 구간에 차 한 대. 다음 구간을 확보해야 현재 구간을 놓는다 |
| 차량 속도 | 3 m/s 일정(가감속 없음) → 구간당 1 s |
| 호이스트(적재·하역) | 각 15 s, 그동안 해당 구간 점유 |
| 장비 로드포트 | 4개 베이 × 4포트 = 16개 (구간 8·33·58·83 부터 3구간 간격) |
| 스토커 | 2개 (구간 0, 50) |
| 대피선 | 8개 (구간 5부터 12구간 간격). 레일 밖이라 정체를 만들지 않음, 용량 무제한 |
| 요청 | 포아송 도착, 150건/h(중부하)와 250건/h(고부하) |
| 출발·도착 | 50% 는 스토커↔장비, 50% 는 장비↔장비(무작위 쌍) |
| 시간 | 워밍업 30분 → 측정 2시간 → 도착 중지 후 1시간 배수(drain) |
| 반복 | 시드 1~5, 조건별 5회 |

**배차 규칙** 두 가지:

- `fifo`: 새 요청이 오면 가장 오래 쉰 차량에 준다. 일을 마친 차량은 가장 오래된 대기 요청을 가져간다.
- `nearest`: 새 요청이 오면 픽업 지점까지 하류 방향 거리가 가장 짧은 빈 차에 준다. 일을 마친 차량은 자기 위치에서 하류 방향으로 가장 가까운 픽업 지점의 요청을 가져간다.

**빈 차 정책** 세 가지:

- `stay`(레일 위 정지): 일이 끝난 곳에 선다. 뒤 차가 그 구간을 기다리면 한 구간 앞으로 밀려난다.
- `siding`(가까운 대피선): 하류 방향 첫 대피선으로 가서 레일을 비운다.
- `balance`(분산 대피선): 다른 빈 차가 가장 적게 머물거나 향하는 대피선을 고른다(동률이면 가까운 쪽). 재배치(rebalancing)의 가장 거친 형태다.

차량 수는 4, 5, 6, 8, 10, 12, 14, 16, 20대. 2 부하 × 9 차량 수 × 2 규칙 × 3 정책 × 5 시드 = 540회를 돌렸다. 2코어 노트북에서 `systemd-run` 으로 CPU 100%·메모리 1.5 GB 상한을 걸고, 전체 10여 분이 걸렸다.

### 측정 지표

- 배송 시간: 요청 생성 → 목적지 하역 완료. 측정 창(워밍업 이후 2시간)에 생성된 요청만 센다.
- 대기 시간: 요청 생성 → 픽업 지점 도착.
- 막힘 비율: 전 차량의 (다음 구간을 기다린 시간) / (기다린 시간 + 주행 시간).
- 미완료: 배수 1시간이 지나도 끝나지 않은 측정 창 요청 수. 0 이 아니면 그 조건은 불안정(대기열 발산)으로 본다.

### 핵심 코드

레일 막힘은 구간마다 용량 1인 `simpy.Resource` 로 만든다. 다음 구간을 먼저 요청하고, 받은 뒤에야 현재 구간을 놓는다.

```python
def step(self):
    nxt = (self.pos + 1) % N_CELLS
    req = self.sim.cells[nxt].request()
    t0 = self.env.now
    yield req                                  # 앞 구간이 빌 때까지 대기
    self.blocked += self.env.now - t0          # 막힘 시간 누적
    yield self.env.timeout(CELL_T)             # 구간 주행
    self.moving += CELL_T
    self.sim.cells[self.pos].release(self.hold)
    self.hold = req
    self.pos = nxt
```

배차는 하류 방향 거리 `(b - a) % N` 하나로 두 규칙을 가른다.

```python
def assign_new(self, req):                     # 요청 주도
    if not self.idle:
        self.pending.append(req); return
    if self.rule == "fifo":
        v = min(self.idle, key=lambda v: (v.idle_since, v.vid))
    else:
        v = min(self.idle, key=lambda v: (dist(v.pos, req.src), v.vid))
    ...

def next_job_for(self, v):                     # 차량 주도
    if self.rule == "fifo":
        return self.pending.pop(0)
    i = min(range(len(self.pending)),
            key=lambda i: (dist(v.pos, self.pending[i].src), self.pending[i].t_create))
    return self.pending.pop(i)
```

`stay` 정책의 빈 차는 1초마다 자기 구간에 대기열이 생겼는지 보고, 있으면 한 칸 전진한다. 대피선 정책은 목표 구간에 도착하면 구간 자원을 반납하고 레일에서 빠진다. 전체 스크립트는 약 280줄이다.

## 결과

### 평균 배송 시간

![차량 수별 평균 배송 시간](/assets/img/fab-iot/fab-iot-1-delivery-mean.png)

주황은 `fifo`, 파랑은 `nearest`, 선 모양은 빈 차 정책이다. 세로축은 로그다.

### 대표 조건 표 (시드 5개 평균, 단위 초)

**150건/h**

| 차량 | 규칙 | 빈 차 정책 | 평균 | p95 | p99 | 막힘 비율 |
|---|---|---|---:|---:|---:|---:|
| 8 | fifo | 레일 위 정지 | 174.5 | 297.5 | 348.3 | 0.226 |
| 8 | fifo | 대피선(분산) | 154.0 | 249.1 | 284.5 | 0.111 |
| 8 | nearest | 레일 위 정지 | 151.3 | 284.5 | 366.0 | 0.269 |
| 8 | nearest | 대피선(가까운) | 124.2 | 210.3 | 258.7 | 0.105 |
| 8 | nearest | 대피선(분산) | 117.9 | 202.0 | 243.9 | 0.090 |
| 16 | fifo | 레일 위 정지 | 243.6 | 449.5 | 526.4 | 0.496 |
| 16 | fifo | 대피선(분산) | 147.8 | 231.9 | 271.0 | 0.131 |
| 16 | nearest | 레일 위 정지 | 193.7 | 424.2 | 576.5 | 0.550 |
| 16 | nearest | 대피선(가까운) | 105.3 | 171.1 | 212.2 | 0.104 |
| 16 | nearest | 대피선(분산) | 97.0 | 161.3 | 196.7 | 0.095 |

**250건/h**

| 차량 | 규칙 | 빈 차 정책 | 평균 | p95 | p99 | 막힘 비율 | 미완료 |
|---|---|---|---:|---:|---:|---:|---:|
| 6 | fifo | 대피선(분산) | 2753.9 | 4240.1 | 4361.3 | 0.084 | 53.8 |
| 6 | nearest | 대피선(분산) | 770.8 | 2422.4 | 3122.8 | 0.184 | 0 |
| 8 | fifo | 대피선(분산) | 1134.3 | 1729.9 | 1827.0 | 0.119 | 0 |
| 8 | nearest | 대피선(분산) | 214.1 | 477.6 | 747.6 | 0.199 | 0 |
| 12 | fifo | 대피선(분산) | 196.7 | 336.3 | 393.9 | 0.205 | 0 |
| 12 | nearest | 레일 위 정지 | 160.2 | 297.0 | 374.6 | 0.325 | 0 |
| 12 | nearest | 대피선(분산) | 128.4 | 231.3 | 288.1 | 0.178 | 0 |
| 16 | nearest | 레일 위 정지 | 171.0 | 344.2 | 452.5 | 0.442 | 0 |
| 16 | nearest | 대피선(분산) | 108.1 | 188.1 | 241.8 | 0.169 | 0 |

전 조건(108개 셀) 표는 재현 폴더의 `summary.csv` 에, 시드별 원자료는 `results_lam150.csv`, `results_lam250.csv` 에 있다. 시드 간 평균 배송 시간의 표준편차는 포화와 거리가 먼 조건에서 대체로 평균의 1~6% 였고, 포화 근처(150건/h 의 4~6대, 250건/h 의 4~12대)에서는 최대 약 40% 까지 커졌다.

### p95 와 막힘 비율

![차량 수별 p95 배송 시간](/assets/img/fab-iot/fab-iot-1-delivery-p95.png)

![차량 수별 주행 중 막힘 비율](/assets/img/fab-iot/fab-iot-1-blocked-ratio.png)

### 관찰

1. **레일 위에 빈 차를 세워 두면 차량 수에 최적점이 생긴다.** 150건/h 에서 `stay` 의 평균 배송 시간은 8대 근처에서 바닥을 찍고 다시 오른다(`fifo` 174.5 s → 20대 281.5 s, `nearest` 151.3 s → 20대 227.3 s). 같은 구간에서 막힘 비율은 0.23~0.27 에서 0.56~0.63 으로 올라간다. 250건/h 에서도 최적점은 12~14대로 옮겨 갈 뿐 같은 모양이다.
2. **빈 차를 레일 밖으로 빼면 그 최적점이 사라진다.** 대피선 정책에서는 차량을 늘려도 평균이 단조 감소하거나 평평해지고, 8대 이상에서 막힘 비율은 150건/h 에서 0.09~0.13, 250건/h 에서 0.12~0.24 에 머문다. 남은 막힘은 호이스트 작업 중인 차 뒤나 대피선 진출입 때 생길 수 있는데, 원인별로 나눠 재지는 않았다.
3. **`nearest` 는 이 레이아웃의 모든 조건에서 `fifo` 보다 평균과 p95 가 낮았다.** 차이는 포화 근처에서 가장 크다. 250건/h·8대에서 `fifo` 는 평균 1134 s, `nearest` 는 214 s 다. 빈 차 주행을 줄이는 것이 곧 수송 능력을 늘리는 일이어서, 같은 차량 수에서 `fifo` 는 이미 포화(가동률 0.85)인데 `nearest` 는 여유(0.70)가 남는다. 250건/h·6대에서 `fifo` 는 배수 1시간 뒤에도 평균 54건이 남는 불안정 상태였고 `nearest` 는 다 처리했다.
4. **그래도 `nearest` 의 꼬리는 상대적으로 길다.** 250건/h·6대에서 `nearest` 의 p95/평균 비는 약 3.1(770.8 → 2422.4), `fifo` 는 약 1.5 다. 멀리 있는 픽업 요청이 계속 뒤로 밀리는 전형적인 starvation 징후다. 이 실험의 범위에서는 절대값으로도 `nearest` 가 낮았지만, 부하가 더 몰리면 p99 나 최대값 기준 SLA 가 깨질 수 있는 구조다.
5. **분산 재배치는 `nearest` 에서만 의미가 있었다.** `nearest` 에서 `balance` 는 `siding` 대비 평균을 10대 이상에서 약 7~10% 줄였다(150건/h·12대 110.1 → 99.2 s). `fifo` 에서는 차이가 시드 간 편차 안에 있다. `fifo` 는 차량 위치를 보지 않고 가장 오래 쉰 차를 고르므로, 빈 차를 어디에 흩어 놓든 쓰지 않는다.

## 해석

- **차량 수 결정은 빈 차를 어디에 둘 수 있느냐와 묶여 있다.** 레일 위에서만 대기할 수 있다면 "많을수록 좋다"가 성립하지 않는다. 이 모델에서 빈 차는 이동 수단이 아니라 장애물로 바뀌는 지점이 분명히 있었다. 반대로 대기 공간이 레일 밖에 있으면 차량 수는 주로 대기 시간(빈 차가 픽업 지점에 오기까지)을 줄이는 쪽으로만 작용하고, 그 효과는 일정 대수 이후 체감한다(150건/h `nearest`/`balance` 기준 12대 99.2 s, 20대 96.7 s).
- **배차 규칙의 효과는 "공짜 용량"이다.** 150건/h 에서 `fifo` 는 차량을 20대까지 늘려도 `nearest` 8대(대피선 분산 117.9 s)를 따라잡지 못했다. `fifo` 대피선 계열은 8대 이후 약 145~154 s 에서 더 내려가지 않는다. 위치를 보지 않는 규칙은 빈 차의 공차 주행이 평균 반 바퀴 근처에서 줄지 않기 때문이다.
- **공정성 문제는 규칙을 통째로 바꾸기보다 보정으로 다뤄 볼 만하다.** 예를 들어 거리 점수에 대기 시간 가중을 더하거나, 일정 시간 이상 기다린 요청에 우선권을 주는 혼합 규칙이다. 이번 실험에는 그런 규칙을 넣지 않았으므로 효과를 수치로 말할 수는 없다.

### MQTT 텔레메트리로 옮기면

홈랩에는 MQTT 브로커 위에서 가상 물류 로봇이 상태를 발행하고 지휘 서비스가 명령을 내리는 구조가 있다. 위 시뮬레이터의 변수들을 같은 방식으로 내보낸다면 다음과 같이 나눌 수 있다. 실제 팹의 OHT 제어는 SEMI E82/E84 와 장비 고유 프로토콜로 이뤄지므로, 여기서의 MQTT 는 제어 경로가 아니라 **관측·분석용 사이드 채널**이라는 전제다.

| 토픽 | 발행자 | 내용 | QoS / retain |
|---|---|---|---|
| `fab/f1/amhs/oht/<vid>/state` | 차량 | `idle`·`to_pickup`·`hoisting`·`loaded`·`parked` 상태 전이, 현재 구간, 작업 ID | QoS 1, retain |
| `fab/f1/amhs/oht/<vid>/pos` | 차량 | 구간 진입 시 구간 번호와 시각 | QoS 0 |
| `fab/f1/amhs/oht/<vid>/event` | 차량 | `blocked_start`/`blocked_end`(앞 차 ID 포함), `load_done`, `unload_done` | QoS 1 |
| `fab/f1/amhs/oht/<vid>/cmd` | 배차기 | 작업 할당, 대피선 이동 지시 | QoS 1 |
| `fab/f1/amhs/request` | MCS 대역 | 반송 요청(출발·도착·생성 시각) | QoS 1 |
| `fab/f1/amhs/zone/<zid>/occupancy` | 배차기(파생) | 구간 점유 차량 | QoS 0, retain |

설계 근거는 MQTT 5.0 명세에 있다.

- 상태 토픽을 retain(3.3.1.3)으로 두면 나중에 붙은 대시보드나 배차기 재기동 직후에도 차량별 마지막 상태를 곧바로 받는다.
- 차량 연결에 Will 메시지(3.1.2.5 이후)를 걸어 `state` 에 `offline` 을 남기면, 차량이 끊겼을 때 배차기가 그 차를 빈 차 목록에서 빼는 판단을 브로커 이벤트로 받을 수 있다.
- 배차기를 여러 복제본으로 띄운다면 `fab/f1/amhs/request` 를 공유 구독(4.8.2, `$share/dispatch/...`)으로 받아 요청 하나가 한 복제본에만 가게 할 수 있다. 다만 `nearest` 는 전체 빈 차 위치를 알아야 하므로, 복제본마다 `oht/+/state` 를 와일드카드(4.7)로 전부 구독해 상태를 따로 들고 있어야 한다.
- 위치 토픽은 유실돼도 다음 구간 진입이 곧 덮어쓰므로 QoS 0 으로 충분하다. 반면 막힘 시작·끝 이벤트는 짝이 맞아야 막힘 시간을 합산할 수 있어 QoS 1 이 낫다(4.3).

이번 실험의 막힘 비율은 정확히 `blocked_start`/`blocked_end` 쌍을 합산한 값과 같은 정의이므로, 이 토픽 구조만 있으면 실시간으로 같은 지표를 계산할 수 있다. 메시지 양은 모델 가정에서 쉽게 나온다. 구간 3 m·속도 3 m/s 이므로 주행 중인 차량 한 대가 `pos` 를 초당 1건 낸다. 20대가 모두 달린다면 초당 20건 수준이고, 이는 MQTT 브로커 하나로 충분히 감당할 규모다. 산업 쪽에서 토픽·페이로드 규칙을 더 엄격히 정하고 싶다면 Eclipse Sparkplug 같은 명세가 참고가 된다([Sparkplug Specification](https://sparkplug.eclipse.org/specification/)).

홈랩 가상 로봇 시뮬레이터에 이 실험을 붙인다면, 로봇 하나를 OHT 차량 하나로 보고 그래프 위 노드 대신 환형 구간 번호를 위치로 쓰는 것이 가장 작은 변경이다. 이번 글에서는 클러스터 브로커에 접속하지 않았고, 위 토픽 설계는 실측이 아니라 제안이다.

## 한계

- **합성 데이터다.** 레이아웃, 속도, 호이스트 시간, 요청률, 스토커 비율은 실험용 가정값이다. 실제 팹 레이아웃, 차량 성능, 물동량 분포를 반영하지 않는다.
- **단일 루프다.** 실제 OHT 레일은 지름길(short cut), 분기·합류, 베이별 intrabay 루프가 얽혀 있다. 분기·합류 지점의 우선권 제어나 경로 선택(route guidance)은 모델에 없다.
- **차량 동역학이 없다.** 가감속, 차간 거리 제어, 커브 감속이 없고 구간 단위 점유만 있다. 막힘 비율의 절대값은 이 단순화에 크게 좌우된다.
- **대피선 용량 무제한**으로 두었다. 실제 대기 공간은 제한되어 있어, 대피선 정책의 이득은 상한값에 가깝다.
- **배차 규칙이 두 개뿐**이다. 대기 시간 가중 혼합 규칙, 헝가리안 할당, look-ahead 같은 실무·연구 규칙은 비교하지 않았다.
- **포화 조건의 평균은 낮게 편향되어 있다.** 미완료가 남은 조건(250건/h 의 `fifo` 4~6대, `nearest` 4대)은 끝난 요청만으로 평균을 내므로 실제보다 좋게 보인다. 이들 조건은 "불안정"으로만 읽어야 한다.
- 시드 5개라 차이가 작은 비교(예: `fifo` 의 `siding` vs `balance`)는 결론을 내리지 않았다.
- MQTT 설계는 제안이며, 실제 브로커에서 부하나 지연을 재지 않았다.

## 재현 방법

```bash
python3 -m venv venv
./venv/bin/pip install simpy==4.1.2 matplotlib==3.11.2
# 한 부하 수준 스윕 (시드 1~5)
./venv/bin/python ohtsim.py --lam 150 --vehicles 4,5,6,8,10,12,14,16,20 \
    --seeds 1,2,3,4,5 --out results_lam150.csv
./venv/bin/python ohtsim.py --lam 250 --vehicles 4,5,6,8,10,12,14,16,20 \
    --seeds 1,2,3,4,5 --out results_lam250.csv
./venv/bin/python aggregate.py   # summary.csv
./venv/bin/python plot.py        # 그림 3장
```

- `ohtsim.py`: 시뮬레이터(레이아웃 상수는 파일 맨 위). `--rules`, `--idle`, `--horizon`, `--warmup` 으로 조건을 바꾼다.
- `run_all.sh`: 이 글에 쓴 전체 스윕을 자원 상한(`systemd-run --user --scope -p MemoryMax=1500M -p CPUQuota=100%`) 안에서 돌린다.
- 난수는 시뮬레이션마다 `random.Random(seed)` 하나만 쓰므로 같은 시드면 같은 결과가 나온다.
- 2코어 노트북 기준 시뮬레이션 1회는 1~3초, 전체 540회는 10여 분이었다.

## References

- SEMI, *SEMI E82 — Specification for Interbay/Intrabay AMHS SEM (IBSEM)*. <https://store-us.semi.org/products/e08200-semi-e82-specification-for-interbay-intrabay-amhs-sem-ibsem>
- SEMI, *SEMI E84 — Specification for Enhanced Carrier Handoff Parallel I/O Interface*. <https://store-us.semi.org/products/e08400-semi-e84-specification-for-enhanced-carrier-handoff-parallel-i-o-interface>
- G. K. Agrawal, S. S. Heragu, "A Survey of Automated Material Handling Systems in 300-mm Semiconductor Fabs," *IEEE Transactions on Semiconductor Manufacturing*, 19(1), 2006. DOI: 10.1109/TSM.2005.863217
- P. J. Egbelu, J. M. A. Tanchoco, "Characterization of automatic guided vehicle dispatching rules," *International Journal of Production Research*, 22(3), 359–374, 1984. DOI: 10.1080/00207548408942459
- B.-I. Kim, J. Shin, S. Jeong, J. Koo, "Effective overhead hoist transport dispatching based on the Hungarian algorithm for a large semiconductor FAB," *International Journal of Production Research*, 47(10), 2823–2834, 2009. DOI: 10.1080/00207540701491090
- A. Benzoni, C. Yugma, P. Bect, "Vehicle Look-Ahead Dispatching for Overhead Hoist Transport System in Semiconductor Manufacturing," *IEEE Transactions on Semiconductor Manufacturing*, 36(1), 130–138, 2023. DOI: 10.1109/TSM.2023.3236071
- OASIS, *MQTT Version 5.0*, OASIS Standard, 2019. <https://docs.oasis-open.org/mqtt/mqtt/v5.0/mqtt-v5.0.html>
- Eclipse Foundation, *The Sparkplug Specification*. <https://sparkplug.eclipse.org/specification/>
- SimPy documentation. <https://simpy.readthedocs.io/en/latest/>
