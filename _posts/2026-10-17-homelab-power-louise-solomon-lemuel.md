---
layout: post
title: "홈랩 전력 비교 — louise·solomon·lemuel: 실측한 것과 못 잰 것을 나눠서"
date: 2026-10-17 18:22:20 +0900
categories: [infra, homelab]
tags: [power, rapl, energy, homelab, k3s, mac-mini, laptop-server]
---

홈랩 k3s 클러스터의 세 노드 — **louise**(2018년 삼성 노트북), **solomon**(2011년 Mac mini), **lemuel**(2017년 HP 노트북) — 의 전력 사용량을 비교했다. 결론부터 말하면, **세 대를 같은 잣대로 잰 숫자는 아직 없다.** 노드마다 확인할 수 있는 층위가 달랐기 때문이다. 이 글은 그 층위를 섞지 않고 정리한다.

| 노드 | 하드웨어 | 이 글에서 확인한 전력 정보 | 층위 |
|---|---|---|---|
| louise | 삼성 950SBE, Intel Core i7-8565U | **CPU 패키지 실측 평균 11.2W** (RAPL, 11분) | 실측 · CPU 패키지만 |
| solomon | Apple Mac mini (Mid 2011), Macmini5,1 | 공식 **유휴 11W / CPU 최대 85W** | 제조사 공식 · 기본 구성 기준 |
| lemuel | HP ProBook 450 G3 | 공식 어댑터 **45W 또는 65W**, CPU 공칭 TDP 15W(모델 추정) | 상한·공칭값 · 실측 없음 |

## 측정 조건

- 일시: 2026-10-17 18:13 ~ 18:24 KST, 약 11분(659초)
- 세 노드 모두 평소 워크로드(k3s 파드, 상시 봇 세션 등) 그대로. 일부러 부하를 걸거나 줄이지 않았다.
- CPU 사용률은 각 노드의 node-exporter `node_cpu_seconds_total` 에서 같은 구간의 idle 비율로 계산했다.

| 노드 | 같은 11분의 CPU 사용률 | 논리 CPU 수 |
|---|---|---|
| louise | 65.3% | 8 |
| lemuel | 60.4% | 4 |
| solomon | 21.4% | 4 |

세 대가 하는 일의 양이 다르다는 점이 중요하다. 전력만 놓고 비교하면 "일을 덜 하는 노드가 효율적" 이라는 잘못된 결론이 나온다.

## louise — RAPL 로 CPU 패키지 전력을 실측

Intel CPU 는 RAPL(Running Average Power Limit) 에너지 카운터를 제공하고, 리눅스는 이를 powercap 프레임워크로 `/sys/class/powercap/intel-rapl:*` 아래에 노출한다([Linux kernel — Power Capping Framework](https://www.kernel.org/doc/html/latest/power/powercap/powercap.html)). `energy_uj` 는 누적 마이크로줄이라 두 시점의 차이를 시간으로 나누면 평균 전력이 된다.

```bash
# 10초 간격 두 번 읽어 평균 전력(W) 계산 — energy_uj 는 root 만 읽을 수 있다
a=$(sudo cat /sys/class/powercap/intel-rapl:0/energy_uj); sleep 10
b=$(sudo cat /sys/class/powercap/intel-rapl:0/energy_uj)
echo "scale=2; ($b - $a) / 10 / 1000000" | bc
```

11분 동안 10초 간격으로 61번 읽은 결과다.

| RAPL 도메인 | 평균 전력 |
|---|---|
| package-0 (CPU 패키지 전체) | **11.21 W** |
| ├ core | 8.14 W |
| └ uncore (내장 GPU 등) | 0.00 W |
| dram | 1.41 W |

10초 구간별 패키지 전력은 **최소 6.73W, 중앙값 8.55W, 최대 21.12W** 였다. i7-8565U 의 공칭 TDP 는 15W, 설정 가능한 TDP-up 은 25W 다([Intel 제품 사양](https://www.intel.com/content/www/us/en/products/sku/149091/intel-core-i78565u-processor-8m-cache-up-to-4-60-ghz/specifications.html)). 10초 구간 기준으로 15W 를 넘는 순간도 있었지만, 11분 평균은 TDP 안쪽이다.

**이 숫자가 아닌 것**: RAPL 은 CPU 패키지와 DRAM 만 잰다. 화면, SSD, Wi-Fi, 메인보드, 어댑터의 변환 손실은 빠져 있다. 따라서 **콘센트에서 louise 가 끌어가는 전력은 이보다 크다.** 얼마나 큰지는 이 측정으로는 알 수 없다. 측정 내내 배터리는 97%, "Not charging" 상태라 충전 전력은 섞이지 않았다.

## solomon — Apple 공식 수치

Apple 은 Mac mini 모델별 소비전력을 공개한다([Mac mini power consumption and thermal output](https://support.apple.com/en-us/103253)). Mac mini (Mid 2011) 의 2.3GHz 듀얼코어 Core i5 기본 구성(2GB 메모리, 500GB 5400rpm HDD)은 다음과 같다.

| 상태 | 소비전력 | 발열 |
|---|---|---|
| 유휴 (Finder 만 열린 상태, 기본 전원 관리) | **11 W** | 38 BTU/h |
| CPU Max (프로세서를 최대로 쓰는 계산 테스트) | **85 W** | 290 BTU/h |

같은 모델의 기술 사양 문서는 최대 연속 전력을 85W 로 적는다([Mac mini (Mid 2011) Technical Specifications](https://support.apple.com/en-us/112007)). solomon 의 node-exporter 는 보드 버전을 `Macmini5,1`, CPU 최대 주파수를 2.9GHz 로 보고한다. 이는 2.3GHz Core i5 구성과 맞는다.

주의할 점이 둘 있다.

1. Apple 수치는 **macOS 에서, 기본 구성으로** 잰 값이다. solomon 은 Ubuntu 를 쓰고 메모리를 15GB 로 늘렸다. 전원 관리 방식과 부품이 달라 유휴 전력이 11W 와 같다고 볼 수 없다.
2. 이번 11분 동안 solomon 의 CPU 사용률은 21.4% 였다. 유휴(11W)보다는 크고 CPU Max(85W)보다는 작을 것이다. 그러나 **사용률에서 전력을 선형으로 환산하는 것은 근거가 없어** 이 글에서는 하지 않는다.

이 Mac mini 는 전원부가 본체에 들어 있어서, 위 수치는 **콘센트 기준 시스템 전체** 전력이다. louise 의 RAPL 값(CPU 패키지만)과는 층위가 다르다. 두 숫자를 나란히 놓고 "solomon 이 louise 와 비슷하다" 고 말하면 틀린다.

## lemuel — 공식 문서로 상한만 확인

HP 는 ProBook 450 G3 의 시스템 소비전력을 데이터시트에 적지 않았다. 확인할 수 있는 것은 어댑터 옵션이다([HP ProBook 450 G3 Datasheet](https://www.hp.com/sbso/hpinfo/newsroom/HPSMB2015/HPProBook%20450G3NotebookPCDatasheet.pdf)).

- 전원 어댑터: **45W 또는 65W Smart AC adapter**

이는 상한일 뿐이다. 어댑터는 최대 부하와 배터리 충전을 함께 감당하도록 정해진다. 평소 소비전력과는 다르다.

CPU 모델명은 클러스터의 node-exporter 가 수집하지 않아 직접 확인하지 못했다. 대신 lemuel 의 CPU 최대 주파수 3.1GHz, 논리 CPU 4개를 이 기종의 CPU 옵션과 대조하면 **Core i7-6500U(2코어, 최대 3.1GHz)로 추정**된다. 데이터시트의 다른 옵션 i5-6200U 는 최대 2.8GHz 이고, i3-6100U 는 터보가 없다. i7-6500U 의 공칭 TDP 는 15W 다([Intel 제품 사양](https://www.intel.com/content/www/us/en/products/sku/88194/intel-core-i76500u-processor-4m-cache-up-to-3-10-ghz/specifications.html)). 어디까지나 **추정**이고, TDP 는 실제 소비전력이 아니라 열 설계 기준값이다.

lemuel 은 CPU 4개에 사용률 60.4%, 1분 load 가 5 안팎으로 셋 중 가장 빠듯하게 돌고 있다.

## 연간 전력량으로 환산하면

평균 전력 W 를 1년(8,760시간) 내내 쓰면 `W × 8.76 = kWh/년` 이다.

| 노드 | 근거 | 연간 환산 |
|---|---|---|
| louise | CPU 패키지 실측 11.2W | 약 98 kWh (**CPU 패키지만** — 실제 시스템은 더 많다) |
| solomon | 공식 유휴 11W ~ CPU Max 85W | 약 96 ~ 745 kWh 사이 (범위가 넓다) |
| lemuel | 실측 없음 | 산출하지 않음 |

이 표가 보여 주는 것은 **"아직 비교할 수 없다"** 는 사실이다. louise 는 하한만 있고 solomon 은 범위만 있으며, lemuel 은 숫자가 없다.

## 제대로 비교하려면

1. **같은 층위로 잰다.** 가장 확실한 방법은 세 대 모두 콘센트에 **전력 측정 플러그(전력량계)** 를 끼우고 같은 시간대에 재는 것이다. 어댑터 손실과 화면·디스크까지 포함한 실제 전기요금 기준이 된다.
2. **solomon·lemuel 에서도 RAPL 을 읽어 본다.** 같은 명령으로 CPU 패키지 전력을 재면, 최소한 louise 와 같은 층위의 비교는 된다. 다만 세대가 다른 CPU 라 노출되는 도메인과 정확도가 다를 수 있으니, 실제로 `/sys/class/powercap` 에 무엇이 있는지부터 확인한다.
3. **일의 양으로 나눈다.** 전력만이 아니라 "같은 작업을 끝내는 데 드는 에너지(J)" 를 비교해야 효율을 말할 수 있다. 예를 들어 같은 빌드나 벤치마크를 돌리고 걸린 시간 × 평균 전력을 비교한다.
4. **노트북 서버는 화면과 충전 상태를 고정한다.** 화면 밝기, 덮개 상태, 배터리 충전 여부가 바뀌면 콘센트 전력이 크게 달라진다.

## 정리

- **louise**: CPU 패키지 평균 11.2W 를 실측했다(중앙값 8.6W, 최대 21.1W). 시스템 전체는 이보다 크다.
- **solomon**: 실측은 없다. Apple 공식값은 기본 구성 기준 유휴 11W, CPU 최대 85W 이고, 콘센트 기준 시스템 전체 값이다. 지금 구성(Ubuntu, 메모리 증설)에서 얼마인지는 재 봐야 안다.
- **lemuel**: 실측도 공식 소비전력도 없다. 어댑터 45/65W 라는 상한과, CPU 모델이 맞다면 TDP 15W 라는 공칭값만 있다.
- 세 대의 우열을 말하려면 **콘센트 전력량계로 같은 시간대에** 재는 것이 다음 단계다.

## References

- Linux kernel documentation, [Power Capping Framework](https://www.kernel.org/doc/html/latest/power/powercap/powercap.html)
- Apple Support, [Mac mini power consumption and thermal output (BTU) information](https://support.apple.com/en-us/103253)
- Apple Support, [Mac mini (Mid 2011) - Technical Specifications](https://support.apple.com/en-us/112007)
- HP, [HP ProBook 450 G3 Notebook PC Datasheet (PDF)](https://www.hp.com/sbso/hpinfo/newsroom/HPSMB2015/HPProBook%20450G3NotebookPCDatasheet.pdf)
- Intel, [Intel Core i7-8565U Processor — Product Specifications](https://www.intel.com/content/www/us/en/products/sku/149091/intel-core-i78565u-processor-8m-cache-up-to-4-60-ghz/specifications.html)
- Intel, [Intel Core i7-6500U Processor — Product Specifications](https://www.intel.com/content/www/us/en/products/sku/88194/intel-core-i76500u-processor-4m-cache-up-to-3-10-ghz/specifications.html)
- 측정 데이터: louise RAPL `energy_uj` 및 세 노드 node-exporter `node_cpu_seconds_total`, 2026-10-17 18:13~18:24 KST (직접 측정)
