---
layout: post
title: "신호가 가장 센 노드가 가장 느렸다 — 무선 재전송률을 잘못 재서 결론을 뒤집은 기록"
date: 2026-09-13 18:22:35 +0900
categories: [infra]
tags: [wifi, 802.11, linux, networking, measurement, homelab]
---

집에 있는 소형 쿠버네티스 클러스터가 전부 무선으로 붙어 있다. 그중 한 대를
공유기 바로 옆(1 m 이내)으로 옮겼더니 **오히려 느려졌다.** 그래서 다시 50~70 cm
떨어뜨렸더니 **신호는 약해졌는데 전송 속도가 두 배가 됐다.**

이 글은 그 현상을 쫓다가 내가 **먼저 내린 결론이 측정 방법 때문에 틀렸다는 걸
발견한 기록**이다. 숫자보다 "그 숫자를 어떻게 재야 하는가"가 본론이다.

> 이 글은 [같은 날 쓴 "dBm 은 링크 품질이 아니다"]({% post_url 2026-09-13-wifi-dbm-is-not-link-quality-beacon-loss %})의
> 후속이다. 그 글은 *신호가 좋은데 느린* 경우를 다뤘고, 이 글은 *신호가 너무 좋아서
> 의심스러운* 경우와 그걸 재는 방법을 다룬다.

---

## 1. 표준은 최소 감도만 규정하지 않는다 — 최대 입력 레벨도 규정한다

무선을 다루다 보면 "감도(sensitivity)"는 익숙하다. 이만큼 약한 신호까지는 받아야
한다는 하한선이다. 그런데 IEEE 802.11 에는 **상한선**도 있다. 절 제목 자체가 그렇다 —
802.11g-2003 의 **19.5.3 "Receive maximum input level capability"**([IEEE 802.11g-2003
목차][ieee11g-toc]).

값은 대역과 PHY 마다 다르다. IEEE 802.11 워킹그룹에 제출된 문서가 클로즈별 동적
범위를 이렇게 정리해 두었다([Kwak, IEEE 802.11 기고문][rcpi]).

| Clause | PHY | 동적 범위 (최소 감도 ~ 최대 입력) |
| --- | --- | --- |
| 17 | 802.11a OFDM (5 GHz) | −82 ~ **−30 dBm** |
| 18 | 802.11b DSSS (2.4 GHz) | −76 ~ **−10 dBm** |
| 19 | 802.11g OFDM/DSSS (2.4 GHz) | −82 ~ **−20 dBm** |

같은 값이 벤더 시험 보고서에서도 확인된다. 퀄컴 QCC74x 설계검증시험 보고서 Table 1-10
은 802.11g / 802.11n 2.4 GHz / 802.11ax 2.4 GHz 모두 **−20 dBm** 으로 적고, 근거 조항을
IEEE Std 802.11-2012 §18.3.10.5, §20.3.21.4, IEEE P802.11ax/D1.0 §28.3.17.5 로
명시한다([Qualcomm 80-WL740-71][qcc74x]). 5 GHz 쪽 −30 dBm 은 동료심사 논문에서도
설계 전제로 인용된다 — "The 802.11ax receiver must operate properly at a maximum input
level of −30 dBm"([Kaczmarczyk et al., PAN journals][lna]).

여기서 중요한 건 값보다 **의미**다. 이 조항은 "이 값까지는 PER 10% 이하를 보장하라"는
뜻이다. 뒤집으면 **그 위는 표준이 아무것도 요구하지 않는다.** 수신기가 어떻게 동작하든
규격 위반이 아니다. 위 논문이 같은 맥락에서 AGC 이득 범위(약 82 dB → 30 dB)와 P1dB,
IIP3 를 논하는 이유가 이것이다 — 강한 입력에서 선형성을 유지하는 건 공짜가 아니다.

내가 옮기기 전 그 노드의 측정값은 **−10 dBm** 이었다. 2.4 GHz OFDM 상한선보다 10 dB 위다.

---

## 2. 실측: 신호를 **약하게** 만들었더니 속도가 두 배가 됐다

노드를 공유기에서 50~70 cm 떼어놓은 것 말고는 아무것도 바꾸지 않았다.

| | 이동 전 | 이동 후 |
| --- | --- | --- |
| signal | −10 dBm | −15 dBm |
| tx bitrate | 18.0 Mbit/s | **36.0 Mbit/s** |
| rx bitrate | — | 54.0 Mbit/s |

신호가 5 dB **나빠졌는데** 협상된 전송 속도는 정확히 두 배가 됐다. "세면 빠르다"는
직관과 반대 방향이다. 이 두 값은 순간값이라 비교가 성립한다 — 뒤에 설명할 누적
카운터와 다르다.

여기까지가 관찰이다. 원인은 아직 확정하지 못했다(4장).

---

## 3. 재전송률은 이렇게 재야 한다 — 누적값으로 before/after 를 비교하면 안 된다

처음에 나는 이렇게 재고 "재전송률이 76.4% → 67.9% 로 좋아졌다"고 적었다.

```bash
iw dev <iface> station dump | grep -E 'tx packets|tx retries|tx failed'
```

**이건 틀린 측정이다.** `tx packets` / `tx retries` / `tx failed` 는 전부 **association
이후 누적값**이다. 노드를 물리적으로 옮기면 재접속이 일어나 카운터가 0 부터 다시
쌓인다. 즉 "이동 전" 값은 수 시간치 평균이고 "이동 후" 값은 몇 분치 평균이다.
**분모가 다른 두 숫자를 빼서 개선이라고 부른 것**이다.

제대로 재려면 두 번 읽어서 차분을 낸다.

```bash
read_st(){ iw dev "$IF" station dump \
  | awk '/tx packets/{p=$3} /tx retries/{r=$3} /tx failed/{f=$3} END{print p+0, r+0, f+0}'; }
A=$(read_st); sleep 60; B=$(read_st)
echo "$A $B" | awk '{dp=$4-$1; dr=$5-$2; df=$6-$3;
  printf "tx=%d retries=%d(%.1f%%) failed=%d(%.2f%%)\n", dp, dr, 100*dr/dp, df, 100*df/dp}'
```

같은 노드를 이 방법으로 60초 재니 **재전송률 97.0%, 실패율 8.02%** 가 나왔다.
누적값이 말하던 67.9% 와 전혀 다르다. **내가 먼저 발표한 "재전송률이 개선됐다"는
주장은 철회한다.** 이동 전의 델타 측정치가 없으므로, 재전송률이 좋아졌는지 나빠졌는지는
**모른다**가 정답이다. 속도가 두 배가 된 것만 사실이다.

---

## 4. 같은 창으로 잰 4개 노드 — 신호 세기로는 순위가 안 나온다

위 델타 방식으로 노드 4대를 45~60초씩 동시에 쟀다.

| 노드 | 드라이버 | signal | tx bitrate | 재전송률 | 실패율 |
| --- | --- | --- | --- | --- | --- |
| A (공유기 1 m 이내) | `b43` (802.11g 레거시) | **−15 dBm** | 36.0 Mbit/s | **97.0%** | 8.02% |
| B | `iwlwifi` | −59 dBm | 144.4 Mbit/s (MCS15 SGI) | **2.8%** | 0.00% |
| C | `rtw89_8851bu` | −64 dBm | 86.0 Mbit/s (HE-MCS7) | 0.0% ⚠️ | 0.00% ⚠️ |
| D | `rtw89_8851bu` | −67 dBm | 103.2 Mbit/s (HE-MCS8) | 0.0% ⚠️ | 0.00% ⚠️ |

신호가 **44 dB 더 약한** B 가 재전송률은 A 의 **35분의 1** 이다. 신호 세기로 링크
품질의 순위를 매기는 건 이 표에서 완전히 실패한다.

**다만 A 가 왜 나쁜지는 이 데이터로 확정할 수 없다.** A 는 이 클러스터에서
동시에 세 가지 유일자다.

1. 공유기에 1 m 이내로 가장 가깝다 (과근접 수신부 포화 후보)
2. 유일한 `b43` = 802.11g 레거시 전용이다. MCS 인덱스 없이 36/54 Mbit/s 순수 OFDM
   레이트로 붙는다 — HT/VHT/HE 가 없다
3. 측정 시점에 이 노드의 load average 가 25~50 으로 매우 높았다

세 요인을 분리하려면 같은 위치에 다른 카드를 꽂아 보거나, 같은 카드를 멀리 옮겨
봐야 한다. **그 대조 실험을 하기 전까지 "과근접 포화 때문"은 가설일 뿐이다.**
이동 전 −10 dBm 이 표준 상한(−20 dBm)을 넘었다는 사실과, 떼어놓자 속도가 두 배가
됐다는 사실이 가설을 **지지**하지만 증명하지는 않는다.

---

## 5. 측정 함정 세 가지

### 5-1. `rtw89` 는 재전송 카운터를 채우지 않는다

위 표에서 ⚠️ 표시한 두 줄이다. C 는 45초 동안 **17,982 패킷**, D 는 **19,053 패킷**을
보내면서 재전송이 **정확히 0** 이다. −64 / −67 dBm 짜리 무선 링크에서 2만 패킷 무재전송은
물리적으로 있을 수 없다. 이건 완벽한 링크가 아니라 **드라이버가 그 필드를 안 채우는
것**이다. `iw` 는 필드를 출력하므로 값이 없다는 신호조차 없다 — 그냥 0 으로 보인다.

판별법은 간단하다. **패킷 수 대비 정확히 0 이면 의심하고, 다른 드라이버를 같은 창으로
재서 대조한다.** 재전송률 비교는 **같은 드라이버끼리만** 유효하다.

### 5-2. `/proc/net/dev` 의 10번째 필드는 tx_packets 이 아니다

`iw` 가 못 미더워서 `/proc/net/dev` 로 교차검증하려다 여기서 한 번 더 틀렸다.
커널이 직접 찍는 헤더를 보면 답이 나온다.

```
Inter-|   Receive                                                |  Transmit
 face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets ...
```

Receive 쪽이 **8개**다. 인터페이스 이름을 `$1` 로 잡으면 `$2`~`$9` 가 수신,
**`$10` 이 tx_bytes, `$11` 이 tx_packets** 이다. `$10` 을 패킷 수로 쓰면 분모가 바이트
단위라 재전송률이 0에 수렴한다 — 실제로 내가 처음에 "재전송률 0%"라고 적은 이유다.

### 5-3. `connected time` 은 완전 단절 중에도 올라간다

또 다른 노드가 핑도 안 되고 클러스터에서 NotReady 인 동안에도 `iw` 의
`connected time` 은 멀쩡히 증가하고 있었다. **association 이 살아 있는 것과
도달 가능한 것은 다른 얘기다.** 링크 생존을 이 값으로 판단하면 안 된다.

반대로 이 값은 다른 용도로는 정확하다 — **물리적으로 옮겼는지 검증**하는 데 쓴다.
옮겼다면 재접속이 일어나 `connected time` 과(전원을 뺐다면) `uptime` 이 리셋된다.
둘 다 끊김이 없으면 그 장비는 옮겨지지 않은 것이다. 이 클러스터에서 "옮겼다"고
알고 있던 노드 하나가 실제로는 안 옮겨진 걸 이 방법으로 잡았다.

---

## 6. 정리

- IEEE 802.11 은 수신 **최대 입력 레벨**을 규정한다. 2.4 GHz OFDM 은 −20 dBm 이고,
  **그 위는 표준이 아무 보장도 하지 않는다.** "공유기에 붙일수록 좋다"는 무조건 참이 아니다.
- 신호를 5 dB 약하게 만들었더니 협상 속도가 두 배가 됐다. 관찰은 재현했지만
  **원인(과근접 포화 / 레거시 PHY / 채널 혼잡)은 분리하지 못했다.**
- 재전송률은 **누적값이 아니라 델타로** 잰다. 누적값 before/after 비교는 분모가 달라서
  성립하지 않는다 — 이 글의 초안이 그래서 틀렸다.
- 드라이버가 카운터를 안 채울 수 있다. **2만 패킷에 재전송 0 은 완벽이 아니라 미보고다.**
- `/proc/net/dev` 는 필드 순서를 커널 헤더로 확인하고 쓴다.

다음 대조 실험은 같은 위치에 최신 카드를 꽂아 보는 것이다. 그래야 위치 탓인지
카드 탓인지 갈린다. 그 전까지는 "가설"이라고 쓰는 게 맞다.

---

## References

**1차 · 표준**

- IEEE Std 802.11g-2003, Clause **19.5.3 "Receive maximum input level capability"** —
  조항 존재 및 명칭은 표준 목차에서 확인. [IEEE 802.11g-2003 Table of Contents][ieee11g-toc]
- J. Kwak (InterDigital), *RCPI: Improved RSSI Measurement*, IEEE 802.11 기고 발표자료 —
  클로즈별 PHY 동적 범위(Clause 17: −82 ~ −30 dBm, Clause 18: −76 ~ −10 dBm,
  Clause 19: −82 ~ −20 dBm). [자료][rcpi]
- 리눅스 커널이 출력하는 `/proc/net/dev` 헤더 — 필드 순서는 본문처럼 실행 노드에서 직접 확인.

**벤더 1차 (시험 보고서 — 재현 조건이 문서에 명시되어 있으나 제3자 검증은 아님)**

- Qualcomm, *QCC74x Design Verification Test Report*, 80-WL740-71 Rev. AC, Table 1-10
  "IEEE receiver maximum input specification" — 802.11g / 11n 2.4 GHz / 11ax 2.4 GHz
  = −20 dBm, 근거 조항 IEEE Std 802.11-2012 §18.3.10.5 · §20.3.21.4,
  IEEE P802.11ax/D1.0 §28.3.17.5. [PDF][qcc74x]

**동료심사 논문**

- P. Kaczmarczyk et al., *A 5-dBm IIP3 3.5-mW LNA for 802.11ax Receiver in 40nm CMOS*,
  Polish Academy of Sciences journals — 802.11ax 수신기 최대 입력 −30 dBm 전제,
  AGC 이득 범위 및 P1dB·IIP3 설계 논의. [PDF][lna]

**본문 측정치**

이 글의 dBm · bitrate · 재전송률 수치는 전부 2026-09-13 에 필자의 홈랩 노드에서
`iw`(델타 방식)로 직접 측정한 값이다. 노드 4대 · 드라이버 3종 · 단일 위치 변경이라
표본이 작고, 4장에 적은 교란 요인이 남아 있다. **일반화하지 말고 같은 방법으로
직접 재 보길 권한다.**

[ieee11g-toc]: https://inus04aapb1h3nprod.dxcloud.episerver.net/en-au/standards/ieee-802-11g-2003-571324_saig_ieee_ieee_1307553/
[rcpi]: https://www.slideserve.com/thane-beck/rcpi-improved-rssi-measurement-a-quantized-power-measurement-to-support-network-management
[qcc74x]: https://docs.qualcomm.com/doc/80-WL740-71/80-WL740-71_REV_AC_QCC74x_Design_Verification_Test_Report.pdf
[lna]: https://journals.pan.pl/Content/138491/23_5290_Kaczmarczyk_L_sk.pdf?handler=pdf
