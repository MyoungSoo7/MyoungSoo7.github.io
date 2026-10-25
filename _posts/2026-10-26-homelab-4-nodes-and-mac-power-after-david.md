---
layout: post
title: "david 까지 내린 뒤 — 남은 4노드와 맥, 같은 10분에 동시에 잰 전기"
date: 2026-10-26 02:17:16 +0900
categories: [infra, homelab]
tags: [homelab, k3s, power, rapl, electricity, kepco, macbook, energy]
---

> 홈랩 K3s 클러스터가 **4노드**로 줄었다. 랙 서버 isagal 에 이어 데스크톱 david 도 전기 문제로 퇴역시켰다. 남은 건 lemuel·ilwon·louise·solomon 네 대와 이 봇들이 도는 맥북 한 대다.
> 이번에는 다섯 대를 **같은 10분 동안 동시에** 쟀다(2026-10-26 02:05~02:15 KST, 10초 간격 61샘플). 이전 글들은 노드마다 다른 날·다른 시간에 쟀다.
> 지난 글들과 같은 원칙을 따른다. **잰 것과 추정한 것을 섞지 않는다.** 숫자마다 어느 층위의 값인지 적어 둔다.

## 1. 무엇이 줄었나

[10월 3일 글](/2026/10/03/homelab-7-machines-electricity-bill/)의 7대 표를 기준으로 보면 이렇다.

| 노드 | 10/3 벽 전력 추정 | 지금 |
| --- | --- | --- |
| isagal (Dell R730xd) | 108W (iDRAC 실측) | **퇴역** (10/15, [이전기](/2026/10/15/isagal-retirement-cluster-6-to-5-power-savings/)) |
| david (i5-8500 + GTX 1060) | ~60W (50~80) | **퇴역** |
| ilwon · louise · lemuel · solomon | 35 · 27 · 15 · 15W | 그대로 |
| 맥 (MacBook Pro 13" 2020) | ~20W (센서 없음, 추정) | **이번에 처음 실측** |

두 대를 뺀 몫은 추정 기준으로 **약 168W(108 + 60)** 다. 한 달(730시간)이면 약 **122.6kWh** 다. david 의 60W 는 실측이 아니라 RAPL·GPU 값으로 짐작한 벽 전력이다. 그래서 이 168W 중 확실한 건 isagal 의 108W 뿐이다.

## 2. 어떻게 쟀나 — 층위가 두 가지다

**리눅스 노드 4대 — Intel RAPL.** 커널의 [powercap 프레임워크](https://docs.kernel.org/power/powercap/powercap.html)가 `/sys/class/powercap/intel-rapl:*/energy_uj` 로 누적 에너지 카운터(µJ)를 보여 준다. 10초 간격으로 읽고 차이를 시간으로 나누면 평균 W 가 나온다. 카운터는 `max_energy_range_uj` 에서 0 으로 돌아가므로, 차이가 음수면 그 값을 더해 보정했다. `energy_uj` 는 root 만 읽을 수 있다.

```bash
for z in /sys/class/powercap/intel-rapl:*; do
  echo "$(date +%s.%N) $(basename $z) $(cat $z/name) $(cat $z/energy_uj) $(cat $z/max_energy_range_uj)"
done
```

RAPL 이 재는 건 **CPU 패키지(+일부 칩에서 DRAM)** 다. 보드·디스크·팬·파워 손실은 빠진다. Khan 등은 [RAPL in Action](https://doi.org/10.1145/3177754)(ACM TOMPECS, 2018)에서 RAPL 이 OS 카운터보다 시스템 전력 추정에 낫다고 보고했다. 하지만 그건 **회귀 모델로 벽 전력을 예측할 때의 오차** 이야기다. RAPL 값 자체가 벽 전력이라는 뜻은 아니다. 같은 논문은 하스웰 이전 세대에선 DRAM 도메인이 서버급 칩에만 있었다고 정리한다. solomon(샌디브리지 i5-2415M)에 DRAM 값이 아예 없는 것도 그래서다.

**맥 — 어댑터 입력 전력.** `ioreg -rn AppleSmartBattery` 의 `PowerTelemetryData` 안에 있는 `SystemPowerIn`(mW)을 10초마다 읽었다. 측정하는 동안 배터리는 **완충 상태로 충전하지 않았고(`IsCharging = No`)**, 어댑터는 연결돼 있었다. 덮개는 **닫혀 있었다(`AppleClamshellState = Yes`)**. 그래서 이 값은 충전분이 섞이지 않은 시스템 입력에 가깝다. ⚠️ 이 키는 **Apple 이 문서로 공개한 인터페이스가 아니다.** 공식 정확도 사양이 없으니 "OS 가 보고하는 값" 으로만 읽어야 한다. 어댑터(61W USB-C) 자체 손실은 들어가지 않는다.

## 3. 결과 — 10분 동시 측정

### 리눅스 노드 (RAPL, W)

| 노드 | 기종 | package | └ core | dram | psys | 10분 load avg |
| --- | --- | --- | --- | --- | --- | --- |
| lemuel | HP ProBook 450 G3 (i7-6500U) | **5.50** (4.58~9.68) | 3.11 | 1.11 | 0.07 ⚠️ | 5.40 |
| ilwon | 데스크톱 (i7-8700) | **3.79** (2.46~5.77) | 2.86 | 1.25 | — | 0.67 |
| louise | 삼성 950SBE (i7-8565U) | **10.45** (8.73~17.83) | 7.99 | 0.47 | **25.89** (23.56~35.45) | 1.58 |
| solomon | Mac mini 2011 (i5-2415M) | **5.69** (5.09~7.51) | 2.40 | — | — | 1.58 |

괄호는 10초 구간들 중 최솟값~최댓값이다. uncore 는 네 대 모두 0.00~0.11W 라 표에서 뺐다.

읽을 때 주의할 점이 세 가지 있다.

1. **louise 의 psys 25.9W 가 이 표에서 가장 벽 전력에 가까운 숫자다.** psys 는 플랫폼 도메인이라 CPU 패키지 바깥까지 들어간다. 같은 기계의 package(10.45W)보다 **약 2.5배** 크다. 다만 psys 가 정확히 어디까지를 포함하는지는 플랫폼마다 다르다. 그래서 벽 전력과 같다고는 하지 않는다. 10/3 글의 "플랫폼 센서 24W" 와 비슷한 수준이다.
2. **lemuel 의 psys 0.07W 는 버린다.** 10분 내내 0.07W 로 고정돼 있었다. 노트북 한 대가 0.07W 로 돌 수는 없다. 이 기종에서는 의미 있는 값이 나오지 않는 것으로 본다.
3. **lemuel 은 load avg 5.4 인데 CPU 는 5.5W 다.** 4스레드 기계에 load 5.4 면 꽉 찬 것처럼 보인다. 그런데 패키지 전력은 TDP 15W 의 3분의 1 남짓이다. 리눅스 load average 는 실행 대기 중인 작업만 세지 않고, I/O 를 기다리며 멈춘 작업도 센다. 그래서 load 를 "CPU 가 얼마나 일하나" 의 지표로 읽으면 틀린다. 이 10분 동안 lemuel 의 부하는 CPU 보다 대기 쪽이었다.

[10월 17일 측정](/2026/10/17/ilwon-no-gpu-server-power-measured/)과 비교하면 ilwon 4.13→3.79W, louise 11.21→10.45W 다. 둘 다 같은 범위 안이다. 날이 달라도 평상시 CPU 전력은 거의 그대로였다.

### 맥 (SystemPowerIn)

| 항목 | 값 |
| --- | --- |
| 평균 | **12.35W** |
| 중앙값 | 9.18W |
| 최소 ~ 최대 | 6.99W ~ 25.51W |
| 11W 미만이었던 구간 | 61개 중 37개 |

덮개를 닫고 화면이 꺼져 있으면 맥은 대체로 **7~11W** 에서 놀았다. 평균이 중앙값보다 높은 건 중간중간 25W 까지 튄 구간 때문이다. 이 시간에도 맥에서는 텔레그램 봇 Claude 세션들이 돌고 있었고, 이 측정을 돌린 세션도 그중 하나였다. 그러니까 **12.35W 는 "봇 서버로 쓰일 때의 맥" 값**이다. 10/3 글에서 넣은 추정치 20W 는 실제보다 높았다.

## 4. 남은 다섯 대의 전기를 다시 더하면

벽 전력은 여전히 맥 하나만 직접 쟀다. 리눅스 노드 네 대는 콘센트 전력계가 없다. 그래서 10/3 글의 추정 범위를 그대로 쓴다. 이번 RAPL 값이 그 추정을 뒤집을 만큼 달라지지는 않았다(louise psys 25.9W ≈ 추정 27W).

| 기계 | 벽 전력 | 근거 |
| --- | --- | --- |
| ilwon | ~35W (30~50) | 추정 — CPU 3.8W + 상시 회전 HDD 등 ([10/17 글](/2026/10/17/ilwon-no-gpu-server-power-measured/)) |
| louise | ~27W (20~30) | 추정 — psys 25.9W 실측과 부합 |
| lemuel | ~15W (12~25) | 추정 — CPU+DRAM 6.6W |
| solomon | ~15W (12~25) | 추정 — CPU 5.7W, Apple 공식 유휴 11W(기본 구성·macOS 기준, [Apple](https://support.apple.com/en-us/103253)) |
| 맥 | **12.35W** | **실측** (어댑터 손실 제외) |
| **합계** | **~104W (86~142)** | |

한 달 730시간이면 **약 76kWh (63~104)** 다. 10/3 의 7대 합계는 ~280W·~204kWh 였다. 숫자로는 **월 약 128kWh 가 줄었다.** 이 중 isagal·david 몫이 122.6kWh 이고, 나머지 약 6kWh 는 맥 추정치를 실측으로 바꾸면서 생긴 차이다. 실제로 전기를 덜 쓴 게 아니라 장부를 고친 것이다. 이 둘을 구분해 둔다.

## 5. 요금으로 바꾸면 — 누진 몇 구간이냐가 전부다

주택용 저압 요금은 누진제다. [법제처 찾기쉬운 생활법령](https://www.easylaw.go.kr/CSP/IssueQaRetrieve.laf?issueqaSeq=407&targetRow=&topMenu=openUl7)이 정리한 한전 「기본공급약관」 별표1 기준(2026-05-10 기준 정리)은 이렇다. 하계(7~8월)가 아닐 때의 구간이다.

| 월 사용량 | 기본요금(원/호) | 전력량요금(원/kWh) |
| --- | --- | --- |
| 200kWh 이하 | 910 | 처음 200kWh: 120.0 |
| 201~400kWh | 1,600 | 다음 200kWh: 214.6 |
| 400kWh 초과 | 7,300 | 400kWh 초과: 307.3 |

여기에 kWh 마다 연료비조정단가 +5.0원([한전 공지](https://www.kepco.co.kr/home/media/newsroom/notice/boardView.do?boardMngNo=14&boardNo=2759), 2026년 4분기)과 기후환경요금 9.0원이 붙는다. 기후환경요금 9.0원은 [보도](https://www.newspim.com/news/view/20251029001176) 기준값이다. 한전 1차 페이지 텍스트로는 확인하지 못했다. 서버 전기는 집 사용량의 **맨 위에 얹히므로** 한계 단가로 계산한다. 1구간은 134.0원, 2구간은 228.6원, 3구간은 321.3원이다(부가세·전력산업기반기금 전).

| 집 전체가 | 남은 5대 (월 76.2kWh) | 퇴역 2대 몫 (월 122.6kWh) |
| --- | --- | --- |
| 1구간 | 약 10,200원 | 약 16,400원 |
| 2구간 | 약 17,400원 | 약 28,000원 |
| **3구간** | **약 24,500원** | **약 39,400원** |

10/15 글에서 "다섯 대·맥·생활 전기가 한 계량기라 3구간일 가능성이 높다" 고 적었다. 그렇다면 isagal·david 를 내려서 **한 달에 약 4만 원(부가세 전)** 을 아끼는 셈이다. 남은 다섯 대는 한 달 약 2만 5천 원어치를 쓴다. 다만 이 계산은 고지서가 아니라 추정이다. 게다가 두 대를 빼면서 사용량이 400kWh 아래로 내려갔다면, 기본요금도 7,300원에서 1,600원으로 떨어진다. 그러면 위 표보다 더 아낀다. 반대로 그만큼 내려갔다면 맨 위 kWh 들이 3구간이 아니었다는 뜻이기도 하다.

## 6. 한계 — 무엇을 재지 못했나

- **리눅스 노드 4대의 벽 전력은 여전히 추정이다.** RAPL 은 CPU(와 DRAM)만 잰다. 데스크톱 ilwon 은 HDD·보드·파워 손실 몫이 CPU 보다 훨씬 크다는 게 10/17 글의 결론이었다. 이 몫은 콘센트형 전력계 없이는 확정할 수 없다.
- **옮겨 간 부하는 따로 재지 않았다.** david 가 하던 일이 남은 네 대로 갔다. 이번 측정에 그 몫이 섞여 있는지, 늘었다면 얼마인지는 퇴역 직전과 직후를 비교하지 않아서 모른다.
- **맥 센서는 비공개 키다.** `SystemPowerIn` 의 정확도·샘플링 방식은 공개 문서가 없다.
- **10분 한 번이다.** 새벽 2시의 평상시 부하다. 빌드·백업·CI 가 도는 시간대는 더 높을 것이다. 하루 평균으로 쓰려면 같은 스크립트를 24시간 돌려야 한다.
- **꺼진 두 대의 대기전력.** 전원 코드가 꽂혀 있으면 isagal 의 iDRAC 같은 관리 회로가 대기 전력을 먹는다. 측정하지 않았다.

## 정리

- 클러스터는 4노드(lemuel·ilwon·louise·solomon)가 됐다. isagal(108W 실측)과 david(~60W 추정)를 빼서 **월 약 123kWh** 를 덜 쓴다. 3구간이면 **월 약 4만 원(부가세 전)** 이다.
- 같은 10분 동시 측정 결과, 리눅스 노드의 **CPU 패키지 전력은 3.8~10.5W** 였다. 플랫폼 값이 나오는 louise 만 25.9W 로, 벽 전력 추정(27W)과 맞았다.
- 맥은 처음으로 실측했다. 덮개를 닫은 봇 서버 상태에서 **평균 12.35W(중앙 9.18W)** 로, 추정했던 20W 보다 낮았다.
- 남은 다섯 대의 합은 **~104W, 월 ~76kWh** 다. 이 중 실측은 맥 하나뿐이다. 다음 숙제는 여전히 콘센트 전력계다.

## References

1. The Linux Kernel documentation, [Power Capping Framework](https://docs.kernel.org/power/powercap/powercap.html) — `intel-rapl` 제어 타입, `energy_uj` · `max_energy_range_uj` 속성.
2. K. N. Khan, M. Hirki, T. Niemi, J. K. Nurminen, Z. Ou, "RAPL in Action: Experiences in Using RAPL for Power Measurements," *ACM TOMPECS* 3(2), 2018. [doi:10.1145/3177754](https://doi.org/10.1145/3177754)
3. S. Desrochers, C. Paradis, V. M. Weaver, "A Validation of DRAM RAPL Power Measurements," *MEMSYS '16*, 2016. [doi:10.1145/2989081.2989088](https://doi.org/10.1145/2989081.2989088)
4. 법제처 찾기쉬운 생활법령정보, [전기요금 Q&A](https://www.easylaw.go.kr/CSP/IssueQaRetrieve.laf?issueqaSeq=407&targetRow=&topMenu=openUl7) — 한전 「기본공급약관」 제67조·별표1 주택용(저압) 요율 (2026-05-10 기준).
5. 한국전력공사, [2026년 4분기 연료비조정단가 공지](https://www.kepco.co.kr/home/media/newsroom/notice/boardView.do?boardMngNo=14&boardNo=2759).
6. 뉴스핌, [전기요금에 포함된 기후환경요금 4년새 70% 인상](https://www.newspim.com/news/view/20251029001176) (2025-10-29) — 기후환경요금 9.0원/kWh, **보도 기준값**.
7. Apple Support, [Mac mini power consumption and thermal output (BTU) information](https://support.apple.com/en-us/103253).
8. 이 블로그의 이전 측정: [홈랩 7대의 전기요금](/2026/10/03/homelab-7-machines-electricity-bill/) · [isagal 퇴역](/2026/10/15/isagal-retirement-cluster-6-to-5-power-savings/) · [louise·solomon·lemuel 비교](/2026/10/17/homelab-power-louise-solomon-lemuel/) · [ilwon 실측](/2026/10/17/ilwon-no-gpu-server-power-measured/).

맥의 `SystemPowerIn` 은 Apple 공식 문서가 없는 IORegistry 키다. 이 글에서는 OS 가 보고한 값으로만 인용했다.
