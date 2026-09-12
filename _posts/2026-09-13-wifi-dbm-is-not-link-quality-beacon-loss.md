---
layout: post
title: "신호는 -56 dBm 로 멀쩡한데 비콘을 90번 놓쳤다 — dBm 만 보면 안 되는 이유"
date: 2026-09-13 03:40:00 +0900
categories: [infra, network]
tags: [WiFi, 802.11, mac80211, beacon-loss, 2.4GHz, 5GHz, Kubernetes]
---

집에서 K3s 6노드를 전부 무선으로 굴리고 있다. 한 노드가 자꾸 `NotReady` 로 떨어져서
무선 링크 통계를 떠봤는데, 숫자가 직관과 정반대였다.

```
# 5GHz 채널 40 에 붙은 노드
signal:         -51 dBm
beacon loss:    0
tx bitrate:     866.7 MBit/s
connected time: 36510 초

# 2.4GHz 채널 11 에 붙은 노드
signal:         -56 dBm
beacon loss:    90
tx bitrate:     129.0 MBit/s
connected time: 36776 초
```

신호 세기 차이는 **5 dB** 밖에 안 된다. 어느 신호 세기 표를 봐도 -56 dBm 은 "좋음"
구간이다. 그런데 한쪽은 비콘을 **한 번도** 안 놓쳤고 다른 쪽은 **90번** 놓쳤다.
같은 시간(약 10시간) 동안, 같은 공유기의 다른 라디오에 붙어서.

dBm 은 링크 품질의 절반만 말해준다. 나머지 절반이 뭔지 정리한다.

## 세 지표는 서로 다른 것을 잰다

`iw dev <iface> station dump` 가 뱉는 값들은 층위가 다르다. 섞어 읽으면 오진한다.

| 지표 | 재는 것 | 층위 |
| --- | --- | --- |
| 대역·채널 | 어느 주파수를 쓰는가 | 물리 매질 선택 |
| signal (dBm) | 내 안테나에 도달한 **수신 전력** | PHY |
| beacon loss | AP 의 정기 방송을 **놓친 횟수** | MAC (연결 유지) |

signal 은 "얼마나 크게 들리는가" 고, beacon loss 는 "그래서 알아들었는가" 다.
시끄러운 방에서 큰 소리로 말해도 못 알아듣는 것과 같다. 소리 크기와 명료도는 다른 축이다.

## dBm: 로그 스케일이라 5 dB 는 생각보다 크다

dBm 은 1 mW 기준 로그 스케일이다. 10 dB 차이가 전력 10배다. 그래서 -51 과 -56 의
5 dB 차이는 실제로는 전력 약 **3.16배**(10^0.5) 차이다. 작지 않다.

그래도 이건 여전히 **절대 수신 전력**일 뿐이다. 내 신호가 얼마나 센지만 말하고,
**그 주변이 얼마나 시끄러운지는 한 마디도 안 한다.** 복조에 실제로 필요한 건 신호 대
잡음·간섭 비(SNR/SINR) 인데, `signal` 필드 하나로는 그 분모를 알 수 없다.

## beacon loss: 커널이 정확히 무엇을 센 것인가

이건 추측할 필요가 없다. 리눅스 커널 소스에 그대로 적혀 있다.

먼저 카운터의 정의. `include/uapi/linux/nl80211.h`:

```c
 * @NL80211_STA_INFO_BEACON_LOSS: count of times beacon loss was detected (u32)
```

"비콘 손실이 **검출된 횟수**" 다. 놓친 비콘 **개수**가 아니다. 그럼 무엇이 "검출"인가.
`net/mac80211/mlme.c`:

```c
/*
 * Beacon loss timeout is calculated as N frames times the
 * advertised beacon interval.  This may need to be somewhat
 * higher than what hardware might detect to account for
 * delays in the host processing frames. But since we also
 * probe on beacon miss before declaring the connection lost
 * default to what we want.
 */
static int beacon_loss_count = 7;
module_param(beacon_loss_count, int, 0644);
MODULE_PARM_DESC(beacon_loss_count,
		 "Number of beacon intervals before we decide beacon was lost.");
```

타임아웃 계산은 같은 파일에서:

```c
	sdata->u.mgd.beacon_timeout =
		usecs_to_jiffies(ieee80211_tu_to_usec(beacon_loss_count *
						      bss_conf->beacon_int));
```

그리고 TU(Time Unit)는 `include/linux/ieee80211.h` 에서:

```c
#define TU_TO_JIFFIES(x)	(usecs_to_jiffies((x) * 1024))
```

즉 1 TU = 1024 µs 다. 내 환경에서 실제로 스캔해 보니 잡히는 AP 12개 중 41개 비콘
프레임이 `beacon interval: 100 TUs`, 하나만 101 TUs 였다. 100 TU 를 넣고 계산하면:

```
7 × 100 TU × 1024 µs = 716,800 µs ≈ 716.8 ms
```

**약 0.72초 동안 비콘이 한 장도 안 들어오면 카운터가 1 올라간다.** 타이머가 터지면
커널은 바로 끊지 않고 probe 를 한 번 쏜다:

```c
	if (beacon) {
		mlme_dbg_ratelimited(sdata,
				     "detected beacon loss from AP (missed %d beacons) - probing\n",
				     beacon_loss_count);
```

```c
		if (ifmgd->associated)
			sdata->deflink.u.mgd.beacon_loss_count++;
		ieee80211_mgd_probe_ap(sdata, true);
```

probe 응답을 기다리는 시간도 정해져 있다:

```c
static int probe_wait_ms = 500;
module_param(probe_wait_ms, int, 0644);
MODULE_PARM_DESC(probe_wait_ms,
		 "Maximum time(ms) to wait for probe response"
		 " before disconnecting (reason 4).");
```

정리하면 **beacon loss 90 = 0.72초짜리 무응답 구간을 90번 겪고, 90번 probe 로 살려냈다**는
뜻이다. 연결은 10시간 유지됐으니 probe 는 매번 성공했다. 링크가 "끊기지 않았다"는 건
사실이지만, 90번 **끊길 뻔했다**는 것도 같이 사실이다. 그리고 그 0.72초는 위쪽 레이어에서
그대로 지연으로 나타난다 — kubelet 하트비트, TCP 재전송, 헬스체크가 다 그 구간을 밟는다.

5GHz 쪽 `beacon loss: 0` 은 10시간 동안 그런 구간이 **한 번도 없었다**는 뜻이다.

## 그럼 왜 신호가 더 센데도 못 받나

전력은 충분한데 비콘을 못 받는다면 원인은 분모 쪽, 즉 매질에 있다. 두 가지를 실측했다.

### 1. 채널이 미어터진다

같은 자리에서 4번 스캔해 유니크 BSSID 로 집계했다.

| 대역 | 채널(MHz) | AP 수 |
| --- | --- | --- |
| 2.4GHz | 2417 | 1 |
| 2.4GHz | 2427 | 1 |
| 2.4GHz | 2437 | 2 |
| 2.4GHz | **2462 (ch11)** | **6** |
| 5GHz | 5200 (ch40) | 2 |

우리 2.4GHz 노드들이 붙어 있는 ch11 한 채널에만 AP 가 6개다. 2.4GHz 전체로는 10개,
5GHz 는 2개. 게다가 2.4GHz 는 20MHz 채널을 겹치지 않게 놓으면 사실상 1·6·11 세 개뿐이라
피할 공간 자체가 없다.

802.11 은 CSMA/CA 라 **하나의 채널을 모두가 시분할로 나눠 쓴다.** AP 가 6개면 내 AP 가
비콘을 쏘려는 순간에 남의 프레임이 매질을 잡고 있을 확률이 그만큼 올라간다. 비콘은 재전송이
없는 브로드캐스트라, 그 순간 밀리면 그냥 사라진다. 신호가 세든 말든 상관이 없다.

이게 신호 -56 dBm 과 beacon loss 90 이 동시에 성립하는 이유다.

### 2. USB 3.0 이 2.4GHz 대역에 노이즈를 뿌린다

우리 노드는 전부 USB 무선 동글을 쓴다. 이게 하필 2.4GHz 에 불리하다.

인텔이 USB-IF 를 통해 공개한 백서가 이 현상을 측정해 놓았다. USB 3.0 은 5 Gbit/s
시그널링이고 그 데이터 스펙트럼이 DC~5GHz 로 매우 광대역이라, **2.4–2.5 GHz 구간에
브로드밴드 노이즈가 실린다.** 백서의 측정값:

- 외장 USB 3.0 HDD 를 연결하면 2.4GHz 대역 노이즈 플로어가 **약 20 dB** 상승
- 노트북의 USB 3.0 리셉터클 커넥터 자체가 노이즈 플로어를 **약 25 dB** 상승
- 주변기기를 완전히 차폐하면 약 12 dB 저감
- **무선 동글을 USB 연장선으로 USB 3.0 포트/기기에서 멀리 떼어놓는 것**이 유효한 완화책

백서의 결론 문장이 핵심이다. 이 노이즈는 무선 장치의 동작 대역(2.4–2.5 GHz) **안에**
떨어지기 때문에 **필터로 걸러낼 수 없고**, SNR 을 깎아 수신 감도를 떨어뜨린다.

주의할 점은 이게 `signal` 값을 나쁘게 만들지 않는다는 것이다. 내 신호의 절대 전력은
그대로다. 올라가는 건 **바닥(noise floor)** 이다. 그래서 dBm 만 보면 멀쩡해 보인다.
5GHz 는 이 노이즈 대역 밖이라 애초에 해당이 없다.

## 실무 체크리스트

무선 링크가 불안한데 dBm 이 괜찮게 나온다면:

1. **beacon loss 를 먼저 본다.** `iw dev <iface> station dump | grep -E 'signal|beacon loss|connected time'`.
   connected time 으로 나눠서 "시간당 몇 번"으로 환산해야 의미가 있다. 누적값은 오래 붙어
   있을수록 커진다.
2. **같은 채널에 누가 있는지 센다.** `iw dev <iface> scan` 을 여러 번 돌려 BSSID 유니크로
   집계한다. 한 번만 돌리면 놓치는 AP 가 있다 — 위 실측도 1회 스캔에선 6개, 4회 합치니 12개였다.
3. **2.4GHz 에서 USB 3.0 과 동글이 붙어 있는지 본다.** 케이스에 직결돼 있으면 연장선으로
   빼보는 것만으로 달라질 수 있다.
4. **tx bitrate 를 같이 본다.** 레이트 적응 알고리즘이 내려간 결과라 링크 품질의 간접
   지표가 된다. 위 사례에서 129 vs 866.7 Mbit/s 였다.
5. **dBm 단독으로 판단하지 않는다.** 신호가 세면서 동시에 링크가 나쁜 상태는 흔하다.

## 우리가 내린 결정과, 아직 확인 못 한 것

문제의 노드에 동글을 하나 더 꽂을까 고민했는데, 데이터를 보고 접었다. 그 노드의 동글은
멀쩡한 노드 두 대와 **완전히 같은 모델**(Realtek `0bda:b831`, `rtw89_8851bu` 드라이버)이고,
그 두 대는 10시간 무중단이다. 같은 모델이 옆에서 잘 돌면 모델 탓이 아니다. 그리고 같은
동글을 하나 더 꽂아봐야 **같은 채널, 같은 노이즈**에 붙는다. 본딩·페일오버는 *장치가 죽는*
고장에는 듣지만 *매질이 나쁜* 고장에는 안 듣는다.

`iw phy` 로 확인해보니 그 동글은 이미 5GHz(Band 2, ch36~165)를 지원한다. 그래서 1순위는
하드웨어 추가가 아니라 **대역 이동**으로 정했다. 비용 0원이고, 같은 클러스터에서 5GHz 노드가
이미 beacon loss 0 을 실증하고 있다.

다만 정직하게 남겨둘 것이 있다. **문제의 노드 위치에서 5GHz 신호를 아직 못 쟀다.** 그 노드가
지금 네트워크에서 떨어져 있어서다. 위 스캔의 5GHz 값(-75/-76 dBm)은 *멀쩡한 다른 노드 자리*
기준이지 문제 노드 자리 기준이 아니다. 5GHz 는 같은 거리에서 2.4GHz 보다 자유공간 손실이
크고 벽 투과도 불리하다(자유공간 손실은 주파수의 제곱에 비례한다, ITU-R P.525). 그래서
"5GHz 로 옮기면 해결" 이라고 지금 단정할 수는 없다. 그 자리에서 양쪽 대역을 재본 뒤에야
결론이 난다.

이 글에서 확실하게 말할 수 있는 건 여기까지다 — **-56 dBm 이라는 숫자 하나로 "무선은
문제없다"고 판단하면 안 된다.** 그 옆에 beacon loss 90 이 같이 찍혀 있었고, 원인은 신호가
아니라 채널이었다.

## References

1. Linux kernel, `include/uapi/linux/nl80211.h` — `NL80211_STA_INFO_BEACON_LOSS` 정의.
   <https://github.com/torvalds/linux/blob/master/include/uapi/linux/nl80211.h>
2. Linux kernel, `net/mac80211/mlme.c` — `beacon_loss_count`, `beacon_timeout` 계산,
   `probe_wait_ms`, 비콘 손실 시 probe 경로.
   <https://github.com/torvalds/linux/blob/master/net/mac80211/mlme.c>
3. Linux kernel, `include/linux/ieee80211.h` — `TU_TO_JIFFIES` (1 TU = 1024 µs).
   <https://github.com/torvalds/linux/blob/master/include/linux/ieee80211.h>
4. Intel Corporation, *USB 3.0 Radio Frequency Interference Impact on 2.4 GHz Wireless
   Devices — White Paper*, April 2012. USB-IF 문서 라이브러리 게재본.
   <https://www.usb.org/sites/default/files/327216.pdf>
5. USB Implementers Forum, 문서 라이브러리 등재 항목(2012-04-01).
   <https://www.usb.org/document-library/usb-30-radio-frequency-interference-impact-24-ghz-wireless-devices>
6. IEEE Std 802.11-2020, *Wireless LAN Medium Access Control (MAC) and Physical Layer (PHY)
   Specifications* — 비콘 프레임·TU·CSMA/CA 의 규범적 출처. IEEE GET 프로그램으로 무료 열람 가능.
   <https://standards.ieee.org/ieee/802.11/7028/>
7. ITU-R Recommendation P.525, *Calculation of free-space attenuation* — 자유공간 손실의
   주파수 의존성. <https://www.itu.int/rec/R-REC-P.525/en>

본문의 측정값은 모두 필자의 홈 클러스터에서 `iw` 로 직접 수집한 것이다. 특정 제품의 우열을
주장하지 않으며, 중립 제3자의 기기 간 비교 시험을 인용한 것이 아니다. 다른 전파 환경에서는
다른 값이 나온다.
