---
layout: post
title: "유선과 무선의 속도 차이는 어디서 오는가 — 802.3·802.11 모델 비교와 제품 숫자 검증"
date: 2026-09-14 09:42:29 +0900
categories: [infra]
tags: [networking, ethernet, wifi, 802-11, 802-3, throughput, latency, benchmark]
---

"무선이 유선보다 느리다" 는 말은 너무 자주 반복돼서 오히려 설명이 생략된다. 그런데
2026년 현재 카탈로그만 보면 이 말은 틀린 것처럼 보인다. Wi-Fi 7 클라이언트 모듈의
공식 스펙이 5.8 Gbps 인데, 대부분의 메인보드에 달린 유선 포트는 1 Gbps 다. 숫자만
비교하면 무선이 5.8배 빠르다.

그런데도 같은 방에서 파일을 옮겨보면 유선이 이긴다. 이 글은 그 간극이 **어느 계층에서,
어떤 구조적 이유로 생기는지** 를 IEEE 표준 문안으로 확인하고, 그 다음 실제 제품 숫자와
제3자 실측으로 맞춰본다. 마지막에는 내가 운영하는 홈 클러스터에서 직접 잰 값도 붙인다.

---

## 1. 두 표준은 어디까지 같고 어디서 갈라지는가

802.3(이더넷)과 802.11(무선랜)은 서로 다른 네트워크가 아니다. 둘 다 IEEE 802 계열이고,
상위 계층(LLC 이상)에서 보면 같은 MAC 주소 체계와 같은 프레임 개념을 쓴다. IP 는 둘을
구분하지 않는다.

갈라지는 지점은 딱 두 개, **MAC 과 PHY** 다. 그리고 속도 차이는 거의 전부 이 두 층에서
발생한다. PHY 는 "1초에 몇 비트를 변조해서 실어보낼 수 있는가"(= 카탈로그의 그 숫자)를
정하고, MAC 은 "그 중 실제로 내 데이터가 차지하는 비율은 얼마인가"를 정한다.

카탈로그는 PHY 만 적는다. 사용자가 체감하는 건 MAC 이후다. 이 글의 논지는 전부 여기서
나온다.

---

## 2. 모델 차이 ① — 전이중인가 반이중인가

IEEE 802.3 표준[^ieee8023]의 MAC 은 두 가지 모드를 정의한다. 표준 본문의 표현을 그대로 옮기면:

> This standard provides for two modes of operation of the MAC sublayer:
> a) In half duplex mode, stations contend for the use of the physical medium, using the
> CSMA/CD algorithms specified. …
> b) The full duplex mode of operation can be used when all of the following are true:
> 1) The physical medium is capable of supporting simultaneous transmission and reception
> without interference (e.g., 10BASE-T, …). 2) There are exactly two stations on the LAN.
> … Since there is no contention for use of a shared medium, the multiple access (i.e.,
> CSMA/CD) algorithms are unnecessary. 3) Both stations … have been configured to use full
> duplex operation.
>
> — IEEE 802.3, Clause 4 / Annex 4A (IEEE 802.3 EFM 태스크포스 공개 초안 문서)[^ieee8023annex4a]

여기서 결정적인 문장은 **"There are exactly two stations on the LAN"** 이다. 스위치를
쓰는 순간 모든 포트가 "정확히 두 대짜리 LAN"(스위치 포트 ↔ 단말)이 되고, 그래서 경쟁이
사라지고, 그래서 CSMA/CD 가 불필요해진다. 표준은 전이중 모드에서 이렇게까지 못을 박는다:

> In full duplex mode, there is never contention for a shared physical medium. … Full duplex
> stations do not defer to received traffic, nor abort transmission, jam, backoff, and
> reschedule transmissions as part of Transmit Media Access Management. Transmissions may be
> initiated whenever the station has a frame queued, subject only to the interframe spacing …

즉 **오늘날의 스위치드 이더넷에는 충돌이 구조적으로 존재하지 않는다.** 교과서에서 배운
CSMA/CD 는 허브 시대의 유산이고, 지금 쓰는 유선 링크에서는 꺼져 있다. 보낼 게 있으면
프레임 간격만 지키고 그냥 보낸다.

802.11 은 이 선택지가 없다. 라디오는 자기가 송신하는 동안 같은 채널에서 남의 신호를
들을 수 없다(자기 송신 신호가 압도적으로 크다). 그래서 충돌 **탐지**(CD)가 불가능하고,
충돌 **회피**(CA)로 갈 수밖에 없다.[^hpbn] 회피는 탐지보다 비싸다. 탐지는 사고가 났을
때만 비용을 내지만, 회피는 사고가 나든 안 나든 **매 프레임마다** 비용을 낸다.

---

## 3. 모델 차이 ② — 매체가 전용인가 공유인가

스위치 8포트짜리에 8대를 물리면 각 단말은 1 Gbps 를 **각자** 갖는다. 8대가 동시에 풀로
써도 서로의 속도를 깎지 않는다(업링크가 병목이 되기 전까지는).

무선은 반대다. 하나의 AP·하나의 채널에 붙은 모든 단말이 **같은 airtime 을 나눠 쓴다.**
그런데 여기서 중요한 건 "나눠 쓴다"가 아니다. 단말이 늘면 **총합이 줄어든다.**

Duda 의 802.11 성능 분석 논문은 이걸 수치로 보여준다. 802.11b 에서 항상 보낼 데이터가
있는 단말들을 늘려가며 잰 총 처리량은 N=2 에서 7.56 Mb/s, N=10 에서 **7.0 Mb/s** 로
**감소**한다. 충돌률이 올라가기 때문이다.[^duda]

같은 논문이 지적하는 또 하나가 실무에서 더 아프다. DCF 는 모든 스테이션에 채널 접근
기회를 균등하게 준다. 그런데 인프라 모드에서 AP 는 **모든 다운로드 트래픽을 혼자
대표해서** 경쟁한다. 단말이 10대면 AP 는 1/11 의 기회밖에 못 얻는다. 그래서 업로드 하나가
다운로드 넷보다 훨씬 좋은 처리량을 가져가는 비대칭이 생긴다.[^duda] 이건 버그가 아니라
모델의 귀결이다.

---

## 4. 모델 차이 ③ — 오버헤드가 고정인가 가변인가

여기가 가장 실용적인 차이다.

### 유선: 계산으로 끝난다

이더넷의 프레임당 오버헤드는 상수다. 프리앰블+SFD 8바이트, MAC 헤더 14바이트,
FCS 4바이트, 프레임 간격(IFG) 12바이트 = 페이로드 밖으로 **38바이트**. MTU 1500 안에는
IP 20 + TCP 20 이 들어가므로 TCP 페이로드는 1460바이트다.

```
효율 = 1460 / (1500 + 38) = 1460 / 1538 = 0.9493
```

TCP 타임스탬프 옵션(12바이트)이 켜져 있으면 1448/1538 = 0.9415. 이걸 링크 속도에 곱하면:

| 링크 | PHY 속도 | TCP 상한(계산) |
| --- | --- | --- |
| 1000BASE-T | 1,000 Mbit/s | 941–949 Mbit/s |
| 2.5GBASE-T | 2,500 Mbit/s | 2,354–2,373 Mbit/s |
| 10GBASE-T | 10,000 Mbit/s | 9,415–9,493 Mbit/s |

iperf3 로 기가비트 링크를 재면 늘 940 Mbps 언저리가 나오는 이유가 이거다. 실측이 아니라
**산수**다. 그리고 이 값은 거리·벽·이웃·시간대와 무관하게 같다.

> 위 표는 프레이밍 오버헤드만 반영한 계산값이다. 실제 측정치는 NIC·드라이버·CPU·오프로딩
> 에 따라 조금 더 낮게 나올 수 있다.

### 무선: 계산이 안 끝난다

802.11 은 프레임 하나를 보내려면 DIFS 대기 → 랜덤 백오프 → 데이터 전송 → SIFS →
수신측 ACK 를 거친다. 이 중 데이터 전송만 PHY 속도로 빨라지고, **DIFS·SIFS·슬롯 타임은
마이크로초 단위 상수로 고정**돼 있다. PHY 가 빨라질수록 전체 시간에서 오버헤드가 차지하는
비율이 **커진다.**

IEEE 802.11 워킹그룹이 1999년에 낸 프로토콜 효율 분석 문서가 이 역설을 직접 다룬다.
같은 MAC 위에 빠른 PHY 를 얹을수록 효율이 떨어진다는 것이다. 문서의 결론 수치는:

- 작은 패킷 + DATA-ACK: 54 Mbps 에서 효율 **0.08**
- 큰 패킷 + DATA-ACK: 54 Mbps 에서 효율 **0.69**

> "There is quantitative efficiency degradation in all scenarios analyzed. … The degradation
> appears obviously as a result of greater (overhead time / data transfer time) ratio"
> — IEEE 802.11-99/256[^ieee80211eff]

Duda 의 논문은 백오프까지 넣어 이렇게 정리한다.

> "Fact 1: The constant overhead lowers the throughput of the 802.11 DCF to about 20% or 30%
> of the bit rate depending on the variant."

구체적으로 802.11g 54 Mb/s 링크에서 단말 하나가 얻을 수 있는 상한은 백오프 제외 시
37.26 Mb/s(U=0.69), 백오프 포함 시 **30.68 Mb/s(U=0.57)** 다.[^duda]

802.11n 이후의 프레임 집성(A-MPDU)은 이 상수 오버헤드를 여러 프레임이 나눠 내게 해서
효율을 크게 끌어올렸다.[^hpbn] 그래서 현대 Wi-Fi 의 효율은 위 숫자보다 훨씬 낫다. 하지만
**0 으로 만들 수는 없다.** ACK 는 여전히 프레임마다 필요하고, 채널 접근 경쟁도 그대로다.

---

## 5. 제품 숫자로 맞춰보기

이제 모델을 실제 제품에 대입한다. 비교할 때 반드시 구분해야 할 세 가지 숫자가 있다.

1. **PHY 최대치** — 벤더 카탈로그의 그 숫자. 변조·채널폭·스트림 수의 곱.
2. **벤더가 밝히는 추정 처리량** — 벤더가 효율 가정을 넣어 계산한 값. 근거를 명시하는
   벤더도 있다.
3. **제3자 실측** — 방법이 공개된 측정치.

### 클라이언트 모듈: Intel Wi-Fi 7 BE200

인텔 공식 제품 사양은 **5.8 Gbps (320MHz, 4096QAM)** 로 적고 있다.[^intelark] 그런데
같은 회사의 제품 브리프 각주는 그 숫자의 성격을 스스로 밝힌다.

> "'5 Gbps Wi-Fi 7 2x2 client speed' - is based on the current draft of the 802.11be
> specification, which specifies the theoretical maximum data rate for a 2x2 device that
> supports 320 MHz channels in the 6GHz band, with a 4096 QAM modulation is 5.76 Gbps. Based
> on an industry-standard efficiency assumption, the resulting estimated maximum over-the-air
> 2x2 client UDP throughput speed would be 5 Gbps"
> — Intel Wi-Fi 7 BE200 Product Brief, 각주 3[^intelbrief]

즉 **5.76 Gbps 는 이론치, 5 Gbps 는 효율 가정을 넣은 추정치**라고 벤더 스스로 라벨을
붙였다. 이건 정직한 표기다(모든 벤더가 이렇게 쓰지는 않는다). 다만 그 "industry-standard
efficiency assumption" 이 정확히 무엇인지는 문서에 없고, UDP 기준이라 TCP 는 더 낮다.

### AP: 제3자 실측

Level1Techs 가 RF 차폐실에서 동일 클라이언트(BE200, 3 m, 가시선)로 Wi-Fi 7 AP 3종을
iperf3 로 측정한 결과다.[^l1t]

| 항목 | NETGEAR RS700S | EnGenius ECW536 (MLO) | ASUS BE-18000 |
| --- | --- | --- | --- |
| TCP 2스트림 forward | 2,892 Mbps | 3,161 Mbps | 2,195 Mbps |
| TCP 2스트림 reverse | 3,512 Mbps | 3,026 Mbps | 389 Mbps |
| idle p50 지연 | 4.5 ms | 2.7 ms | 3.5 ms |
| idle p99 지연 | 12.6 ms | 6.7 ms | 7.0 ms |

최고치인 3,512 Mbps 를 같은 클라이언트의 이론 PHY 5,760 Mbps 로 나누면 **약 61%** 다.
차폐실·3 m·가시선이라는, 가정에서 재현되지 않는 조건에서 그렇다.

같은 리뷰의 유선 기준선은 이렇게 적혀 있다.

> "On a wired Ethernet connection, you're used seeing ping times of 1 ms or less to your
> router. … there's no contention for the medium, and there's no error recovery overhead.
> … The Wi-Fi MAC layer adds about 1–2 ms of fixed overhead per round trip just for this
> channel access and acknowledgment dance, even for UDP type traffic."

### 소비자 환경: 대역별 비교

MyBroadband 가 Wi-Fi 7 라우터 한 대로 규격·대역만 바꿔가며 NAS 파일 전송을 측정한
결과다. NAS 가 기가비트 포트라 상한이 904 Mbps 로 묶여 있다는 점을 감안해야 한다.[^mybb]

| 연결 | 전송 속도 | 유선 대비 |
| --- | --- | --- |
| 이더넷 (기가비트) | 904 Mbps | 100% |
| Wi-Fi 7 MLO (3대역) | 904 Mbps | 100% |
| 6 GHz | 824 Mbps | 91% |
| 5 GHz | 584 Mbps | 65% |
| 2.4 GHz | 136 Mbps | 15% |

이 표가 말하는 건 **"Wi-Fi 7 이 빠르다"가 아니라 "대역이 전부다"** 에 가깝다. 같은 최신
규격이라도 2.4 GHz 로 내려가면 기가비트 유선의 15% 다. 규격 세대보다 대역 선택이 훨씬
크게 작용한다는 건 이 측정의 저자도 같은 결론으로 적고 있다.

### 종합

| 구분 | 카탈로그(PHY) | 실제로 기대할 값 | 조건 의존성 |
| --- | --- | --- | --- |
| 1GbE 유선 | 1,000 Mbit/s | 941–949 Mbit/s (계산) | 없음 |
| 2.5GbE 유선 | 2,500 Mbit/s | 2,354–2,373 Mbit/s (계산) | 없음 |
| Wi-Fi 7 2×2 (6 GHz, 320 MHz) | 5,760 Mbit/s | 차폐실 3 m 에서 ~3,500 Mbps (실측) | 거리·벽·간섭·단말 수 |
| Wi-Fi 7, 5 GHz | — | 기가비트 유선의 약 65% (실측) | 상동 |
| Wi-Fi 7, 2.4 GHz | — | 기가비트 유선의 약 15% (실측) | 상동 |

**유선 칸의 값은 계산이고 무선 칸의 값은 측정이다.** 이 비대칭 자체가 답이다. 유선은
계산으로 답이 나오기 때문에 측정할 필요가 별로 없고, 무선은 측정해도 조건이 바뀌면 그
값이 더 이상 유효하지 않다.

---

## 6. 처리량보다 지연, 지연보다 지연의 분산

실무에서 유선/무선의 차이가 가장 아프게 드러나는 건 평균 속도가 아니다.

위 실측에서 무선 AP 3종의 idle p50 지연은 2.7~4.5 ms, p99 는 6.7~12.6 ms 였다. 유선
기준선은 p50 약 0.5 ms, p99 약 1 ms 로 적혀 있다.[^l1t] 절대값 차이는 2~4 ms 로, 게임
핑 기준으로는 무시할 만하다.

문제는 **부하를 걸었을 때 꼬리가 벌어지는 정도**다. 같은 측정에서 UDP 부하를 올려가며 잰
RS700S 의 p99 는 100 Mbps 에서 11.0 ms, 1,000 Mbps 에서 19.1 ms, 2,468 Mbps 에서
**127.0 ms** 로 튀었다. 처리량은 계속 올라가는데 지연이 먼저 무너진다.

이게 왜 인프라에서 중요한가. TCP 재전송 타이머, 헬스체크 타임아웃, 분산 시스템의
리더 선출·리스 갱신 같은 것들은 전부 **평균이 아니라 꼬리 지연**에 반응한다. 평균 4 ms
짜리 링크에서 가끔 127 ms 가 나오면, 평균만 보고 잡은 타임아웃은 그 순간에 터진다.

---

## 7. 실제 운영 중인 클러스터에서 잰 값

이 글의 앞 내용은 전부 남의 측정이다. 내가 직접 잰 것도 붙인다. 가정에 있는 소규모
쿠버네티스 클러스터로, 노드가 전부 무선으로 붙어 있다(설계상 그렇게 했다). 같은 AP,
같은 시각, 45~60초 델타 측정이다.

| 노드 | 무선 칩셋 세대 | 협상 비트레이트 | 신호 | 재전송률 | 실패율 |
| --- | --- | --- | --- | --- | --- |
| A | 802.11g (레거시) | 36 Mbit/s | -15 dBm | **97.0%** | 8.02% |
| B | 802.11n (iwlwifi) | 144.4 Mbit/s (MCS15 SGI) | -59 dBm | 2.8% | — |
| C, D | 802.11ax | 86.0 / 103.2 Mbit/s (HE-MCS7/8) | -64 / -67 dBm | 미보고* | — |

\* 해당 드라이버가 재전송 카운터를 채우지 않는다. 0 으로 보이는 건 완벽한 링크라는 뜻이
아니다.

여기서 세 가지가 보인다.

**첫째, 신호 세기는 링크 품질의 순위를 매기지 못한다.** 가장 신호가 센 노드 A(-15 dBm)가
재전송률 97.0% 로 최악이고, 훨씬 약한 노드 B(-59 dBm)가 2.8% 로 최선이다. 다만 노드 A 는
교란 요인이 셋 겹쳐 있다 — AP 와 가장 가깝고(수신 과포화 가능성), 유일하게 레거시
802.11g 카드이며, 부하가 가장 높다. 그래서 **"신호가 세서 느리다"고 단정할 수는 없다.**
말할 수 있는 건 dBm 만으로 순위를 매기면 틀린다는 것뿐이다.

**둘째, 재전송률 97% 는 유선에 대응물이 없는 숫자다.** 이더넷 전이중 링크에는 MAC 계층
재전송이라는 개념 자체가 없다. 프레임이 깨지면 FCS 에서 버려지고 상위 계층이 처리한다.
무선은 이 97% 를 PHY/MAC 이 흡수해서 상위 계층에는 "좀 느린 링크"로만 보이게 한다. 즉
**무선의 손실은 패킷 손실이 아니라 지연과 지터로 번역돼서 올라온다.**[^hpbn] 이게 3장에서
본 "회피 비용을 매 프레임마다 낸다"의 실물이다.

**셋째, 같은 네트워크 안에서 세대 차이가 3~4배다.** 노드 A 와 B 는 같은 AP·같은 방에
있는데 협상 비트레이트가 36 vs 144.4 Mbit/s 다. 무선에서 "우리 집 속도"라는 단일 숫자는
존재하지 않는다. 단말별로 다르고, 시간별로 다르다.

> 이 측정 과정에서 내가 저지른 오류와 그 교정은 따로 정리해 두었다.
> [신호가 가장 센 노드가 가장 느렸다]({% post_url 2026-09-13-wifi-strongest-signal-worst-link-retry-measurement %}) ·
> [dBm 은 링크 품질이 아니다]({% post_url 2026-09-13-wifi-dbm-is-not-link-quality-beacon-loss %})

---

## 8. 그래서 무엇을 기준으로 고르나

모델 차이에서 바로 따라 나오는 판단 기준이다.

**유선을 써야 하는 곳** — 값이 **예측 가능해야** 하는 자리.
- 클러스터 노드 간 통신, 스토리지 트래픽, 백업
- 헬스체크·리스 갱신처럼 꼬리 지연에 타임아웃이 걸린 것
- 항상 켜져 있고 움직이지 않는 장비

**무선으로 충분한 곳** — 값이 **평균적으로만** 좋으면 되는 자리.
- 휴대 단말, 스트리밍, 웹, 일반 업무
- 6 GHz 대역을 쓸 수 있고 AP 와 같은 공간이면 기가비트 유선에 근접한다(실측 91%)

**무선으로 하면 안 되는 걸 무선으로 했을 때 생기는 일** — 내 클러스터가 그 사례다.
노드가 전부 무선이라 링크가 흔들릴 때마다 컨테이너가 죽고, 재시작 백오프가 최대 5분까지
올라가서 **실제 장애 3초가 체감 장애 5분**이 됐다. 처리량이 문제가 아니었다. 연구용으로
일부러 그렇게 둔 구성이라 유지하고 있지만, 운영이었다면 선을 깔았어야 할 자리다.

한 줄로 줄이면 이렇다. **무선의 약점은 느린 게 아니라 예측이 안 되는 것이다.** 카탈로그
숫자만 보면 무선이 이미 유선을 앞질렀고, 좋은 조건에서는 실제로 그렇다. 하지만 "좋은
조건"을 보장하는 비용이 랜선 한 가닥보다 비싸다.

---

## 9. 근거의 한계

정직하게 밝혀 둘 것들이다.

- **중립 헤드투헤드가 부족하다.** 표준 문서(1차)와 벤더 스펙(벤더 1차)은 확실하지만,
  "동일 조건에서 유선과 무선을 나란히 측정한 동료심사 벤치마크"는 찾지 못했다. 위 제3자
  측정 두 건은 방법이 공개돼 있으나 각각 포럼 리뷰와 매체 테스트이고, 동료심사가 아니다.
- **제3자 측정은 서로 조건이 다르다.** Level1Techs 는 RF 차폐실 3 m, MyBroadband 는
  기가비트 NAS 가 상한. 두 표의 숫자를 직접 비교하면 안 된다.
- **효율 분석 논문은 802.11b/g 시대 것이다.** 20~30% 라는 Duda 의 수치는 프레임 집성
  이전이라 현대 Wi-Fi 에 그대로 적용되지 않는다. 그래서 이 글에서는 "구조가 그렇다"는
  논지에만 썼고, 현대 수치는 제3자 실측으로 대체했다.
- **내 클러스터 측정은 노드 4대·단일 AP·가정 환경**이라 일반화할 수 없다. 특히 노드 A 의
  97% 재전송률은 교란 요인 3개가 겹쳐 있어 원인을 특정하지 못했다.
- **유선 표의 값은 계산이지 측정이 아니다.** 프레이밍 오버헤드만 반영했다.

---

## References

[^ieee8023annex4a]: IEEE 802.3, Clause 4 / Annex 4A "Simplified full duplex media access control" (IEEE 802.3 EFM 태스크포스 공개 문서). <https://www.ieee802.org/3/efm/public/jan04/THIN_MAC/4Ad3_1CMP.pdf>
[^ieee8023]: IEEE Std 802.3-2022, *IEEE Standard for Ethernet* (표준 개요 및 초록). IEEE Standards Association. <https://standards.ieee.org/ieee/802.3/10422/>
[^ieee80211eff]: IEEE 802.11-99/256, "Evaluation of Protocol Efficiency" (IEEE 802.11 워킹그룹 문서, 1999-11). <https://www.ieee802.org/11/Documents/DocumentArchives/1999_docs/92568S-Evaluation-of-Protocol-Efficiency_doc.PDF>
[^duda]: A. Duda, "Understanding the Performance of 802.11 Networks," *IEEE PIMRC 2008*. <https://drakkar.imag.fr/IMG/pdf/duda.pimrc08.pdf>
[^hpbn]: I. Grigorik, *High Performance Browser Networking*, O'Reilly — "Performance of Wireless Networks: WiFi". <https://hpbn.co/wifi/>
[^intelark]: Intel® Wi-Fi 7 BE200 제품 사양 (Intel 공식). <https://www.intel.com/content/www/us/en/products/sku/230078/intel-wifi-7-be200/specifications.html>
[^intelbrief]: Intel® Wi-Fi 7 BE200 (Gale Peak 2) Product Brief (Intel 공식 문서). <https://www.intel.com/content/www/us/en/content-details/761674/intel-wi-fi-7-be200-gale-peak-2-product-brief.html>
[^l1t]: "NETGEAR Nighthawk RS700S Wi‑Fi 7 — Real-World Performance Review," Level1Techs Forums, 2026-06-11 (RF 차폐실, Intel BE200 클라이언트, iperf3). 제3자 측정이며 동료심사는 아님. <https://forum.level1techs.com/t/netgear-nighthawk-rs700s-wi-fi-7-real-world-performance-review/251315>
[^mybb]: W. Steyn, "We tested Wi-Fi 7 and achieved super fast speeds," MyBroadband, 2025-11-04. 제3자 매체 측정이며 NAS 가 기가비트 포트로 상한. <https://mybroadband.co.za/news/wireless/616317-we-tested-wi-fi-7-and-achieved-super-fast-speeds.html>
