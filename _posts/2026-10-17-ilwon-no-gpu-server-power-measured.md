---
layout: post
title: "GPU 없는 홈랩 서버 '일원'의 전기 — CPU 는 4W, 나머지가 진짜 전기를 먹는다"
date: 2026-10-17 18:30:00 +0900
categories: [Infra, homelab]
tags: [homelab, power, rapl, electricity, k3s, kepco, energy, no-gpu]
---

[홈랩 7 대 전기요금 글](/2026/10/03/homelab-7-machines-electricity-bill/)에서 일원(ilwon)은 짧은 샘플 두어 번으로 "벽 전력 약 35W(30~50W)"라고 추정만 하고 넘어갔다. 그 뒤 [랙 서버 isagal 을 퇴역](/2026/10/15/isagal-retirement-cluster-6-to-5-power-savings/)시키면서 일원은 control-plane·etcd 에 로그 저장소·Kafka·Prometheus 까지 짊어진, 클러스터에서 가장 바쁜 상태 저장 노드가 됐다.

그래서 이번에는 일원 하나만 놓고 **33 분 연속 실측**과 **부품별 공식 사양**으로 전기를 다시 봤다. 결론은 제목대로다. **CPU 가 쓰는 전기는 4W 남짓이고, 전기 사용량을 좌우하는 건 CPU 밖의 부품들이다.**

> 측정 시점: 2026-10-17 17:5x~18:3x KST, 평상시 부하. 벽 콘센트 전력계로 잰 값이 **아니다**. 무엇을 쟀고 무엇을 추정했는지 아래에서 구분한다.

---

## 1. 일원은 어떤 기계인가

| 항목 | 사양 |
|---|---|
| CPU | Intel Core i7-8700, 6 코어 12 스레드, 3.2GHz(최대 4.6GHz), **TDP 65W** ([Intel](https://www.intel.com/content/www/us/en/products/sku/126686/intel-core-i78700-processor-12m-cache-up-to-4-60-ghz/specifications.html)) |
| GPU | **없음**(CPU 내장 UHD 630 만) |
| 메모리 | DDR4-2666 8GB × 4 = 32GB |
| 저장장치 | NVMe 500GB(Samsung 970 EVO Plus, OS) · NVMe 1TB(SK hynix Gold P31) · HDD 4TB(WD Red Plus) |
| 역할 | K3s control-plane + etcd + 워커. 로그 Elasticsearch·Logstash, Kafka, Prometheus 등 상주 |

GPU 가 없다는 건 전기 관점에서 큰 장점이다. 같은 블로그의 10/3 측정에서 다른 노드(david)의 GTX 1060 은 그 시점에 11.5W 를 쓰고 있었다. 일원에는 그 몫이 아예 없다.

---

## 2. 실측: Intel RAPL 33 분

리눅스는 Intel CPU 의 RAPL(Running Average Power Limit) 에너지 카운터를 `/sys/class/powercap/intel-rapl:*/energy_uj` 로 노출한다. 커널 문서에 따르면 package 영역은 CPU 패키지 전체이고, 그 아래 core·uncore 하위 영역이 있다. 순간 전력이 아니라 **누적 에너지(마이크로줄)**만 주므로, 10 초 간격 차이를 시간으로 나눠 평균 전력을 구했다([Linux kernel docs](https://docs.kernel.org/power/powercap/powercap.html)).

**200 샘플(10 초 간격, 33.3 분) 결과**

| 영역 | 평균 | 중앙값 | p5 | p95 | 최대 |
|---|---|---|---|---|---|
| package(CPU 전체) | **4.13W** | 4.03W | 2.66W | 5.97W | 7.25W |
| └ core | 3.19W | 3.08W | 1.73W | 5.06W | 6.28W |
| dram | **1.31W** | 1.31W | 1.24W | 1.37W | 1.43W |
| CPU 사용률 | 8.0% | 7.9% | 6.3% | 9.8% | 10.7% |

- 같은 시간 노드 CPU 사용률은 8% 였다. Prometheus 로 지난 2 주의 하루 평균을 보면 **매일 9.6~11.5%**(10/2 하루만 43%)로 꾸준하다. 그래서 이 33 분은 평상시를 잘 대표한다.
- CPU 전력 한도(PL1)는 65W(TDP)로 잡혀 있다. 평상시엔 그 **6% 수준**만 쓰고 있다.
- 전력 관리 설정은 `intel_pstate` 드라이버, governor `powersave`, EPP(에너지·성능 선호) `balance_performance` 다.
- DRAM 1.31W 는 RAPL 의 DRAM 영역 값이다. 데스크톱 칩에서 이 값이 실측인지 모델 추정인지는 확인하지 못했으니 참고치로만 본다.

**CPU + 메모리 = 약 5.4W.** 한 달(730 시간)이면 4kWh 도 안 된다.

---

## 3. 나머지 부품: 제조사 사양으로 더하기

| 부품 | 공식 사양(평균 전력) | 비고 |
|---|---|---|
| HDD 4TB WD Red Plus | 읽기/쓰기 **4.7W**, 대기(idle) **3.1W**, 절전 0.3W | WD 제품 브리프의 현행 4TB 모델(WD40EFPX) 수치. 내 드라이브는 이전 모델 WD40EFZZ 라 근사치다([WD](https://documents.westerndigital.com/content/dam/doc-library/en_us/assets/public/western-digital/product/internal-drives/wd-red-plus-hdd/product-brief-western-digital-wd-red-plus-hdd.pdf)) |
| NVMe Samsung 970 EVO Plus 500GB | 활성 읽기 5W·쓰기 5.8W, idle(ASPM) **30mW** | [Samsung 데이터시트](https://download.semiconductor.samsung.com/resources/data-sheet/Samsung_NVMe_SSD_970_EVO_Plus_Data_Sheet_Rev.3.0.pdf) |
| NVMe SK hynix Gold P31 1TB | **공식 전력 수치 없음** | 제조사 페이지에 활성·idle 전력 표기가 없다 |
| 메인보드·칩셋·팬·NIC·USB Wi-Fi | **측정·공식 수치 없음** | |
| 파워서플라이 손실 | 효율 미상 | 아래 4 절 |

HDD 는 쿠버네티스 로컬 스토리지(로그 ES 등)라 계속 일한다. `hdparm` 으로 봐도 `active/idle` 상태이고 스핀다운하지 않는다. 그래서 **3.1~4.7W 가 24 시간 그대로** 나간다. HDD 하나가 CPU 평균 전력과 비슷한 수준이다.

**측정값 + 공식 사양으로 확인되는 것만 더하면 약 8.5~12.1W**(CPU·DRAM 5.4W + HDD 3.1~4.7W + 970 EVO Plus 0.03~2W 가정)다. 지난 글의 벽 전력 추정 35W(30~50W)와 비교하면, **벽 전력의 대략 2/3 는 우리가 직접 재지도, 공식 수치로 확인하지도 못한 부분**이다. 메인보드·칩셋·VRM·팬·P31·파워 손실이 여기에 들어간다.

---

## 4. 왜 '벽 전력'은 모르는가 — 파워서플라이 저부하 효율

일원 파워의 정격 대비 30~50W 는 아주 낮은 부하다. 그런데 80 PLUS 인증은 **20%·50%·100% 부하** 효율만 정한다. 10% 부하는 Bronze·Gold 등급에서 요구 항목이 아니다([CLEAResult 80 PLUS](https://www.clearesult.com/80plus/80plus-psu-ratings-explained)). 예를 들어 115V 내부형 기준 Bronze 는 82/85/82%, Gold 는 87/90/87% 다.

즉 **일원이 실제로 도는 구간(정격의 한 자릿수 %)의 효율은 인증서에 없다.** 그래서 부품 합에서 벽 전력을 역산할 수 없다. 이 부분을 정확히 하려면 콘센트형 전력계를 꽂는 수밖에 없다. 랙 서버 isagal 은 iDRAC 가 벽 전력을 직접 줬지만(108W), 일반 데스크톱에는 그런 센서가 없다.

---

## 5. 그래서 한 달에 얼마인가 — 누진 단계가 답을 바꾼다

벽 전력을 지난 글의 추정 범위(30~50W, 중심 35W)로 두면 한 달(730 시간) 사용량과 **전력량요금만의 증분**은 이렇다. 단가는 한전 주택용 저압, 2023-11-09 시행 요금표 기준이다([한전 요금표](https://cyber.kepco.co.kr/ckepco/front/jsp/CY/E/E/CYEEHP00101.jsp)).

| 벽 전력 | 월 사용량 | 집 전체가 1 단계(≤200kWh)일 때 120.0원 | 2 단계 214.6원 | 3 단계 307.3원 |
|---|---|---|---|---|
| 30W | 21.9kWh | 약 2,600원 | 약 4,700원 | 약 6,700원 |
| **35W** | **25.6kWh** | **약 3,100원** | **약 5,500원** | **약 7,900원** |
| 50W | 36.5kWh | 약 4,400원 | 약 7,800원 | 약 11,200원 |

- 같은 25kWh 라도 **집의 나머지 전기 사용량이 몇 단계에 있느냐에 따라 2.5 배** 차이가 난다. 서버가 쓰는 전기는 집 사용량의 '맨 위'에 얹히기 때문이다. 경계를 넘기면 기본요금 단계도 바뀐다.
- 위 표는 **전력량요금만** 셌다. 실제 청구에는 기후환경요금·연료비조정요금·부가가치세·전력산업기반기금이 더 붙는다. 이 항목들의 현재 값은 지난 글에 정리했다.
- CPU 만 보면(5.4W → 월 4kWh) 몇백 원 수준이다. **전기요금을 줄이고 싶다면 CPU 튜닝보다 상시 도는 HDD·보드·파워 효율이 레버**다.

---

## 6. 정리

1. **GPU 없는 i7-8700 서버는 평상시 CPU 가 약 4W 다.** 평균 사용률 8%, PL1 65W 의 6% 수준이다. GPU 가 없으니 그래픽카드 몫의 전력(다른 노드에서 측정 당시 11.5W)도 없다.
2. **전기의 대부분은 CPU 밖에서 쓴다.** 상시 회전하는 HDD 4TB 만 3.1~4.7W(공식 사양)로 CPU 평균과 비슷하다. 벽 전력의 약 2/3 는 보드·팬·파워 손실처럼 재기 어려운 부분이다.
3. **RAPL 로는 서버 전기요금을 계산할 수 없다.** 측정이 정확한 건 CPU·메모리뿐이고, 저부하 파워 효율은 인증 규격에도 없다. 다음 단계는 콘센트 전력계로 실측해 이 글의 추정 범위를 하나의 숫자로 바꾸는 것이다.
4. 요금은 서버가 아니라 **집 전체의 누진 단계**가 결정한다. 같은 25kWh 가 월 3 천 원일 수도, 8 천 원일 수도 있다.

---

## References

1. Linux kernel documentation, *Power Capping Framework* (intel-rapl). <https://docs.kernel.org/power/powercap/powercap.html>
2. Intel, *Core i7-8700 Processor specifications*. <https://www.intel.com/content/www/us/en/products/sku/126686/intel-core-i78700-processor-12m-cache-up-to-4-60-ghz/specifications.html>
3. Western Digital, *WD Red Plus HDD product brief* (Power Management). <https://documents.westerndigital.com/content/dam/doc-library/en_us/assets/public/western-digital/product/internal-drives/wd-red-plus-hdd/product-brief-western-digital-wd-red-plus-hdd.pdf>
4. Samsung Semiconductor, *Samsung NVMe SSD 970 EVO Plus Data Sheet* Rev.3.0. <https://download.semiconductor.samsung.com/resources/data-sheet/Samsung_NVMe_SSD_970_EVO_Plus_Data_Sheet_Rev.3.0.pdf>
5. SK hynix, *Gold P31* 제품 페이지(전력 수치 미표기). <https://ssd.skhynix.com/gold_p31/>
6. CLEAResult, *80 PLUS PSU ratings explained*. <https://www.clearesult.com/80plus/80plus-psu-ratings-explained>
7. 한국전력공사, *주택용 전력 요금표*(2023-11-09 시행). <https://cyber.kepco.co.kr/ckepco/front/jsp/CY/E/E/CYEEHP00101.jsp>
