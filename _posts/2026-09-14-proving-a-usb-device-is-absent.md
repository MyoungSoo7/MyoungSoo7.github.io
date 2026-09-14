---
layout: post
title: "커널이 아무 말도 안 했다 — 'USB 장치가 없다'를 증명하는 순서"
date: 2026-09-14 22:42:18 +0900
categories: [infra]
tags: [usb, linux, kernel, sysfs, apparmor, dmesg, homelab, measurement]
---

무선으로만 돌아가는 K3s 홈랩에 WiFi 6 USB 동글을 하나 더 달려고 연장선을 꽂았다. 돌아온 질문은 짧았다. **"제대로 되어 있어?"**

답하려면 먼저 *없음* 을 증명해야 했다. 있는 걸 확인하는 건 쉽다 — 링크 속도를 재면 된다. 그런데 "안 보인다" 는 관찰은 그 자체로는 아무것도 결론짓지 못한다. 장치가 정말 없는 건지, 도구가 못 보는 건지, 다른 기계를 보고 있는 건지가 전부 같은 모양으로 나타나기 때문이다.

이 글은 그 세 가지를 하나씩 떼어내는 순서에 대한 기록이다. 결론부터 쓰면, 두 노드의 결과는 정반대였다.

```
solomon: 25시간 동안 USB 관련 커널 이벤트 0건   → 전기적으로 연결조차 안 됨
isagal : 8초 만에 열거 → 펌웨어 로드 → 이름 복구  → 정상
```

> 같은 클러스터에서 나온 앞선 글들 — [dBm 은 링크 품질이 아니다]({% post_url 2026-09-13-wifi-dbm-is-not-link-quality-beacon-loss %}), [신호가 가장 센 노드가 가장 느렸다]({% post_url 2026-09-13-wifi-strongest-signal-worst-link-retry-measurement %}) — 이 *무선 신호의 측정* 을 다뤘다면, 이 글은 그 앞 단계, **장치가 거기 있기는 한가** 를 다룬다.

## 0. 0단계 — 어느 기계를 보고 있는지부터 확정한다

시작은 "solomon에 USB 선을 연결했다" 였다. 그래서 solomon을 팠다. 없었다. 커널 로그도 조용했다. 한참을 파고 나서야 정정이 왔다 — **꽂은 건 isagal이었다.**

웃고 넘길 일이 아니다. 사람이 기억으로 말하는 "어디에 무엇을 꽂았다" 는 진단의 전제인데, 이게 틀리면 그 뒤의 모든 측정이 엉뚱한 대상을 향한다. 그리고 이 경우 증상이 *똑같다*. 장치가 없는 기계를 들여다보면 당연히 아무것도 안 나오고, 그건 "고장났다" 와 구별되지 않는다.

기계는 기억하지 않고 기록한다. isagal의 커널 로그에는 작업 시각이 초 단위로 남아 있었다.

```
19:00:01  usb 1-1.4: USB disconnect, device number 6
19:00:01  wlx…: deauthenticating (Reason: 3=DEAUTH_LEAVING)
19:00:09  usb 2-1.2: new high-speed USB device number 10 using ehci-pci
```

19:00:01 에 뽑혀서 19:00:09 에 다른 포트에 꽂혔다. 8초. 사람의 손이 움직인 시간이 그대로 찍혀 있다. **어느 기계에 작업했는지는 물어볼 게 아니라 로그로 확정할 일이다.**

## 1. 1단계 — 도구를 믿지 말고 ABI 를 본다

solomon에서 `lsusb` 를 돌렸다. 애플 블루투스 허브와 적외선 수신기뿐, 네트워크 장치는 없었다. 그런데 같은 순간 커널 로그에 이런 게 쏟아졌다.

```
apparmor="DENIED" operation="open" profile="lsusb"
  name="/sys/devices/pci0000:00/0000:00:1d.7/uevent" requested_mask="r"
apparmor="DENIED" operation="open" profile="lsusb"
  name="/sys/devices/pci0000:00/uevent" requested_mask="r"
```

`lsusb` 가 **AppArmor 프로파일 안에서** 돌고 있고, sysfs 읽기 일부가 거부되고 있었다. 실제로 이 배포판(Ubuntu 26.04)에는 `/etc/apparmor.d/lsusb` 가 기본으로 들어 있다. 파일 머리에 Canonical 저작권과 2024년이 박혀 있는, 배포판이 넣어준 프로파일이다.

```
profile lsusb /usr/bin/lsusb {
  include <abstractions/base>
  /usr/bin/lsusb mr,
  network netlink raw,
  capability net_admin,
  /etc/udev/hwdb.bin r,
  /dev/bus/usb/@{d}@{d}@{d}/@{d}@{d}@{d} rw,
  ...
```

여기서 나는 **"그럼 목록 자체가 잘렸겠구나"** 라고 의심했다. 보안 정책이 sysfs 를 막고 있으니 장치가 누락됐을 수 있다고. 그래서 정책 레이어를 우회해서 직접 셌다.

```bash
for d in /sys/bus/usb/devices/*/; do
  [ -f "$d/idVendor" ] || continue
  echo "$(basename $d) $(cat $d/idVendor):$(cat $d/idProduct)"
done
```

결과는 **9개. `lsusb` 도 9개.** 의심은 틀렸다. AppArmor 가 막은 건 장치 목록이 아니라 부가 정보를 긁는 경로였고, 목록은 온전했다.

틀린 의심이었지만 절차는 옳았다고 본다. **"없다" 는 결론을 userspace 도구 하나에 의존해서 내리면 안 된다.** 그 도구는 보안 정책·권한·패키지 버전이라는 레이어를 통과한 결과를 보여주고, 그 레이어들은 조용히 실패하도록 설계돼 있다. 교차확인 비용이 명령어 한 줄이라면 항상 치는 게 맞다.

그리고 이때 무엇으로 교차확인할지가 중요하다. `/sys/bus/usb/devices/.../speed` 는 리눅스 커널이 **stable ABI** 로 문서화한 경로다. 커널 문서는 stable ABI 에 대해 "userspace 프로그램이 제약 없이 사용해도 되며 최소 2년간 하위 호환을 보장한다" 고 못박는다. 즉 여기 값이 있으면 있는 것이고 없으면 없는 것이다 — 중간에 정책이 끼지 않는다.

## 2. 2단계 — 로그의 *침묵* 을 읽는다

이제 진짜 질문. solomon에 장치가 안 보이는 게 **꽂히긴 했는데 실패한 것** 인지, **애초에 안 꽂힌 것** 인지다. 둘은 처방이 완전히 다르다.

USB 연결은 실패하는 방식마다 서로 다른 흔적을 남긴다. 이걸 세 갈래로 나눠 놓으면 판정이 기계적으로 끝난다.

| 무엇이 일어났나 | 커널 로그에 남는 것 |
| --- | --- |
| ① 정상 열거 | `new high-speed USB device number N using ehci-pci` → 드라이버·펌웨어 로드 |
| ② 열거를 시도했으나 실패 | `device descriptor read/64, error -71`, `unable to enumerate USB device`, `over-current` |
| ③ 전기적으로 연결 자체가 안 됨 | **아무것도 없음** |

solomon에서 부팅 이후 25시간치를 전부 긁었다. ①도 ②도 ③의 반증도 없었다. 신규 열거 이벤트 **0건**, 열거 실패 **0건**, 과전류 **0건**.

```bash
sudo dmesg -T | grep -iE 'new (full|high|super)-speed USB device|unable to enumerate|over-current|device descriptor read|USB disconnect'
# (출력 없음)
```

**열거 실패조차 없다는 것이 핵심 단서다.** 전원이 들어오고 D+/D- 에 신호가 잡히면 커널은 최소한 시도는 하고, 시도가 깨지면 `error -71` 같은 걸 남긴다. 그 흔적조차 없다는 건 호스트 컨트롤러가 **장치가 붙었다는 사실 자체를 인지하지 못했다** 는 뜻이다. 드라이버 문제도, 설정 문제도 아니다. 그 아래, 전기 층위의 문제다.

반대로 isagal은 ①의 교과서적 전개였다.

```
19:00:09  usb 2-1.2: new high-speed USB device number 10 using ehci-pci
19:00:09  rtw89_8851bu 2-1.2:1.0: loaded firmware rtw89/rtw8851b_fw.bin
19:00:09  rtw89_8851bu 2-1.2:1.0: Firmware version 0.29.41.5, cmd version 0, type 5
19:00:10  rtw89_8851bu 2-1.2:1.0: rfkill hardware state changed to enable
19:00:10  rtw89_8851bu 2-1.2:1.0 wlx…: renamed from wlan0
```

열거 → 펌웨어 → rfkill 해제 → 인터페이스 이름 복구까지 1초 안에 완주했다. **"제대로 됐나" 의 답은 이 다섯 줄이다.** 링크 속도를 재기 전에 이게 먼저다.

## 3. 3단계 — 원인 후보를 하나씩 배제한다

"전기 층위" 는 아직 너무 넓다. 좁혀야 한다.

**드라이버 — 배제.** 잘 되는 isagal의 동글은 `rtw89_8851bu` (Realtek RTL8851BU, `0bda:b831`) 로 붙는다. 안 되는 solomon에 그 모듈이 있는지 봤다.

```
solomon: rtw89_core 있음 / rtw89_usb 있음 / rtw89_8851b 있음 / rtw89_8851bu 있음
isagal : rtw89_core 있음 / rtw89_usb 있음 / rtw89_8851b 있음 / rtw89_8851bu 있음
커널  : 양쪽 다 7.0.0-31-generic (동일)
```

같은 커널, 같은 모듈. 꽂히기만 하면 붙는다. 드라이버는 용의선상에서 빠진다.

> 여담이지만 여기서 한 번 헛발을 짚었다. `modinfo rtw89` 가 "없음" 을 뱉길래 잠깐 드라이버 부재를 의심했는데, `rtw89` 는 모듈 이름이 아니라 드라이버 *계열* 이름이었다. 실제 모듈은 `rtw89_core` 다. **모듈 유무는 계열 이름이 아니라 실제 모듈 이름으로 물어야 한다.**

**포트 규격 — 확인하되 원인은 아님.** 두 노드 모두 PCI 상에 노출된 USB 컨트롤러가 EHCI 뿐이었다. xHCI 가 없다는 건 **USB 3.0 포트가 물리적으로 없다** 는 뜻이다. isagal에서 동글이 실제로 잡힌 포트를 sysfs 로 읽어보면 그대로 나온다.

```
path  = pci0000:00/0000:00:1d.0/usb2/2-1/2-1.2
speed = 480 Mbps        ← High Speed (USB 2.0)
bMaxPower = 500mA
```

커널의 `speed` 속성은 480 이면 High Speed, 5000 이면 Super Speed 를 뜻한다. 즉 이 동글은 USB 3.0 장치지만 2.0 으로 폴백해 돌고 있다. 속도로는 문제가 없다 — 링크가 100 Mbit/s 급이라 480 Mbps 버스는 남아돈다. **다만 전력이 걸린다.**

**남은 것 — 전력과 케이블.** USB-IF 의 USB 2.0 사양은 §7.2.1 에서 unit load 를 100 mA 로 정의하고, 외부 전원을 쓰는 호스트의 고전력 포트는 포트당 5 unit load, 즉 **500 mA** 를 공급하도록 규정한다. 위에서 읽은 `bMaxPower = 500mA` 가 정확히 그 상한이다. 그리고 바로 다음 절 §7.2.2 의 제목이 **"Voltage Drop Budget"** 이다 — 케이블과 커넥터에서 허용되는 전압 강하가 예산으로 잡혀 있다는 뜻이고, 연장선은 그 예산을 먹는다.

정리하면 solomon의 가설은 이렇게 좁혀진다. USB 3.0 포트가 없어 500 mA 가 상한인데, 여기에 연장선이 끼면서 전압이 떨어져 장치가 **링크 트레이닝조차 못 갔다.** 열거 실패 로그가 없는 것과 앞뒤가 맞는다. 확인 순서도 여기서 따라나온다 — ① 연장선 빼고 직결 ② 잡히면 연장선 확정, 급전형으로 교체 ③ 안 잡히면 포트를 바꿔가며 시도.

## 4. 그리고 가장 흔한 착각 — "고쳤다" 를 말할 수 있는가

isagal은 정상이었다. 여기서 보통 "케이블 작업으로 무선이 안정됐다" 로 넘어간다. 그런데 그 말을 하려면 **작업 전 상태를 알아야 한다.**

기준선을 미리 떠 두지 않았으니 소급해서 만들었다. 무선 끊김은 로그에 남으므로, 나흘치 journal 에서 끊김 이벤트를 시간대별로 세면 개입 전 상태가 복원된다.

```bash
sudo journalctl --since "4 days ago" --no-pager \
  | grep -icE 'deauthenticating|USB disconnect|link is not ready' ...
```

```
9/11  18시 1건  20시 5건  23시 1건
9/12  08시 5건  10시 1건  12시 1건  13시 4건  16시 1건  18시 3건  19시 5건 …
9/13  00시 3건  01시 5건  02시 2건  14시 1건  17시 10건  18시 2건
9/14  19시 2건   ← 내가 케이블을 뽑았다 꽂은 그 2건
```

9/13 18시부터 9/14 19시까지 **25시간 동안 0건.** 즉 **케이블을 만지기 전에 링크는 이미 안정돼 있었다.** 그러니 이번 작업의 효과는 "끊김을 고쳤다" 가 아니라 잘해야 "끊김 없이 자리를 옮겼다" 다. 9/13 17시의 10건이 알려진 장애였고, 그건 이미 지나간 일이었다.

같은 날 신호 세기도 이렇게 움직였다.

```
19:11   -62 dBm
19:15   -67 ~ -71 dBm     ← 4분 사이 5~9 dB 이동
21:04   -63 dBm  (2초 간격 6회 평균)
```

한 번 재고 판정했다면 "개선됐다" 도 "악화됐다" 도 얼마든지 쓸 수 있었다. 그래서 판정 자체를 하루 미루고, 측정 방식을 스크립트로 고정했다 — 신호는 2초 간격 6회 평균, 핑은 AP 로 100발, 끊김은 journal 24시간치 카운트. **다음 측정이 같은 잣대로 찍히도록 만드는 것까지가 측정이다.**

그렇게 뜬 기준선은 이랬다.

```
         신호평균   rx/tx Mbit    RTT avg/max      손실   24h 끊김
isagal   -63 dBm   68.8/103.2      4.6 /   54 ms   0%     2건(작업분)
david    -64 dBm   86.0/103.2     82.1 /  569 ms   0%     0건
ilwon    -67 dBm   51.6/ 86.0    572.4 / 2850 ms   0%     0건
```

정작 눈에 걸린 건 작업한 isagal이 아니라 **ilwon**이었다. 신호는 4 dB 차이인데 평균 지연이 124배다. 손실은 0%다. 그리고 ilwon은 control-plane 겸 etcd 멤버다. 손 댄 곳을 보러 갔다가 안 본 곳의 문제를 발견한 셈인데, 이게 "같은 잣대로 여러 대를 동시에 재는" 방식의 실질적인 이득이었다.

## 5. 정리 — 부재를 증명하는 체크리스트

1. **대상부터 확정한다.** "어디에 꽂았다" 는 진술은 전제이지 사실이 아니다. 타임스탬프로 확정한다.
2. **userspace 도구 하나로 "없다" 를 단정하지 않는다.** 정책·권한 레이어가 조용히 낀다. 커널 stable ABI 로 교차확인한다. (이번엔 도구가 멀쩡했지만, 확인 비용이 한 줄이면 항상 친다.)
3. **침묵과 실패를 구별한다.** 열거 실패 로그가 *있는* 것과 *없는* 것은 완전히 다른 진단이다. 없으면 더 아래층이다.
4. **배제로 좁힌다.** 잘 되는 기계와 안 되는 기계에서 같은 항목(커널·모듈·컨트롤러·포트 속도)을 나란히 읽으면 후보가 빠르게 준다.
5. **"고쳤다" 를 말하기 전에 개입 전 상태를 확보한다.** 없으면 로그에서 소급 복원한다. 복원해 보면 애초에 안 망가져 있었던 경우가 꽤 있다.
6. **판정을 서두르지 말고, 다음 측정이 같은 잣대가 되게 만든다.**

무선 이야기처럼 시작했지만 결국 이 글의 주제는 측정 규율이다. "안 보인다" 는 관찰은 공짜로 얻어지는 대신 아무것도 결론짓지 못한다. 결론은 *무엇이 안 보이는지를 구별* 하는 데서 나온다.

## References

- [USB 2.0 Specification — USB Implementers Forum](https://usb.org/document-library/usb-20-specification) — §7.2.1 Classes of Devices(unit load 100 mA, 고전력 포트 5 unit load), §7.2.2 Voltage Drop Budget
- [ABI stable symbols / sysfs-bus-usb — The Linux Kernel documentation](https://www.kernel.org/doc/Documentation/ABI/stable/sysfs-bus-usb) — `/sys/bus/usb/devices/.../speed` 의 stable ABI 정의(1.5 / 12 / 480 / 5000 Mbit/s)
- [Stable ABI 정책 — The Linux Kernel documentation](https://docs.kernel.org/admin-guide/abi-stable.html) — "userspace 프로그램이 제약 없이 사용해도 되며 최소 2년간 하위 호환을 보장한다"
- [`drivers/usb/core/sysfs.c` — torvalds/linux](https://github.com/torvalds/linux/blob/master/drivers/usb/core/sysfs.c) — `speed_show()` / `bMaxPower_show()` 구현

측정값은 모두 자체 홈랩(Ubuntu 26.04, 커널 7.0.0-31-generic, K3s v1.35.4+k3s1)에서 2026-09-14 에 잰 값이며 일반 벤치마크가 아니다. 사설 주소와 하드웨어 주소는 노드 이름·`wlx…` 로 치환했다.
