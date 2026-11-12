---
layout: post
title: "서버가 된 삼성 노트북의 센서 허브 — 모션 센서 6종을 리눅스 IIO 로 읽어 쓰기"
date: 2026-11-12 13:45:00 +0900
categories: [Linux, IoT, Homelab]
tags: [Intel ISH, HID Sensor, IIO, 가속도계, 센서 허브, k3s, 반도체, SPC]
---

> **한 줄 요약**: 화면 자동 회전에 쓰던 노트북 센서 허브를 리눅스 IIO 인터페이스로 그대로 읽을 수 있다. 서버가 된 노트북에서는 설치 환경 감시 장치로 쓸 수 있다. 다만 "자세가 바뀐 것" 과 "충격" 을 같은 식으로 계산하면 오경보가 끝없이 반복된다. 실제로 그렇게 됐다.
>
> **라벨**: **[실측]** 이 노트북에서 직접 읽은 값 / **[사실]** 1차·공식 문서로 확인 / **[추론]** 필자 해석.

## 1. 대상 기계

홈랩 k3s 클러스터의 워커 노드 중 하나는 2018년 무렵 산 삼성 노트북이다. 지금은 뚜껑을 연 채 24시간 서버로 돈다.

| 항목 | 값 | 라벨 |
|---|---|---|
| 제품명(DMI) | `950SBE/951SBE`, 제품군 `Notebook 9 Series`, 보드 `NT950SBE-X716` | [실측] `/sys/class/dmi/id/` |
| CPU | Intel Core i7-8565U | [실측] `lscpu` |
| 센서 허브 | `Intel Corporation Cannon Point-LP Integrated Sensor Hub` (PCI 00:13.0) | [실측] `lspci` |
| 커널 | 6.8 (Ubuntu) | [실측] `uname -r` |

이 노트북은 펜 입력을 지원하고 화면이 돌아가는 형태다. 그래서 일반 클램셸 노트북보다 센서가 많이 들어 있다. [추론]

## 2. 기술 구조 — 센서 허브 → HID → IIO

### 2-1. Intel ISH: 센서 전용 저전력 코프로세서

Intel ISH(Integrated Sensor Hub)는 SoC 안에 들어간 작은 코프로세서다. 센서 폴링과 센서 퓨전 알고리즘을 메인 CPU 대신 처리해 메인 코어가 저전력 상태에 더 오래 머물게 한다. 리눅스 커널 문서는 Intel 이 Cherry Trail 세대부터 ISH 를 SoC 에 넣었다고 설명한다. [사실] ([커널 문서: Intel ISH](https://docs.kernel.org/hid/intel-ish-hid.html))

리눅스에서는 다음 드라이버 체인으로 올라온다. [실측] `lsmod`

```
intel_ish_ipc  →  intel_ishtp  →  intel_ishtp_hid   (ISH 전송 계층)
                                      ↓
                               hid_sensor_hub      (HID 센서 코어)
                                      ↓
 hid_sensor_accel_3d / gyro_3d / magn_3d / incl_3d / rotation / custom_intel_hinge
                                      ↓
                               industrialio (IIO) → /sys/bus/iio/devices/
```

### 2-2. HID 센서 사용법(Usage) 표준

ISH 는 센서를 **HID 장치**로 내보낸다. 키보드·마우스와 같은 HID 프로토콜에 센서용 "Sensors Page(0x20)" 를 정의해 둔 것이다. 덕분에 OS 는 제조사 전용 드라이버 없이 범용 드라이버로 센서를 읽는다. [사실] ([USB-IF HID Usage Tables 1.5, Sensors Page 0x20](https://usb.org/sites/default/files/hut1_5.pdf), [Microsoft: HID Sensors Usages](https://learn.microsoft.com/en-us/windows-hardware/design/whitepapers/hid-sensors-usages))

커널의 `hid-sensor-hub` 는 각 센서를 `HID-SENSOR-xxxx` 라는 플랫폼 장치로 등록한다. `xxxx` 는 사양의 usage ID 다. 예를 들어 `HID-SENSOR-200073` 은 Accelerometer 3D 다. [사실] ([커널 문서: HID Sensors Framework](https://docs.kernel.org/hid/hid-sensor.html))

이 노트북의 센서와 HID usage ID 를 맞춰 보면 이렇다.

| IIO 이름 | 장치명 [실측] | HID Sensors Page usage [사실, HUT 1.5] | 측정 |
|---|---|---|---|
| `accel_3d` | `HID-SENSOR-200073` | 0x73 Motion: Accelerometer 3D | 3축 가속도(중력 포함) |
| `gyro_3d` | `HID-SENSOR-200076` | 0x76 Motion: Gyrometer 3D | 3축 각속도 |
| `magn_3d` | `HID-SENSOR-200083` | 0x83 Orientation: Compass 3D | 지자기, 자북 기준 방위 |
| `incli_3d` | `HID-SENSOR-200086` | 0x86 Orientation: Inclinometer 3D | 기울기 각 |
| `dev_rotation` | `HID-SENSOR-20008a` | 0x8A Orientation: Device Orientation | 자세 쿼터니언 |
| `hinge` | `HID-SENSOR-INT-020b` | 표준 밖, Intel 사용자 정의 센서 | 힌지·화면·키보드 각도 |

힌지 센서만 표준 usage 가 아니다. 커널에는 Intel 사용자 정의 힌지 센서용 드라이버 `hid-sensor-custom-intel-hinge` 가 따로 있다. 이 드라이버는 `hinge`, `screen`, `keyboard` 세 채널을 노출한다. [사실] ([커널 소스](https://github.com/torvalds/linux/blob/master/drivers/iio/position/hid-sensor-custom-intel-hinge.c))

### 2-3. IIO 로 읽기

IIO(Industrial I/O)는 ADC·가속도계·자이로 같은 센서를 위한 커널 서브시스템이다. 값은 sysfs 파일로 읽는다. [사실] ([커널 문서: IIO Introduction](https://docs.kernel.org/driver-api/iio/intro.html))

물리값은 `raw × scale` 이다. 이 노트북을 책상에 놓고 실제로 읽은 값이다. [실측]

```bash
D=/sys/bus/iio/devices/iio:device5      # accel_3d
cat $D/in_accel_scale                   # 0.000009806
cat $D/in_accel_{x,y,z}_raw             # 23668  -307379  947391
```

```
x =  23668 × 0.000009806 ≈  0.23 m/s²
y = -307379 × 0.000009806 ≈ -3.01 m/s²
z =  947391 × 0.000009806 ≈  9.29 m/s²
|a| ≈ 9.77 m/s²   ← 가만히 놓여 있으니 중력 가속도와 거의 같다
```

모든 센서의 샘플링 주파수는 10 Hz 로 잡혀 있었다(`*_sampling_frequency=10.000000`). [실측]

반면 힌지 센서는 세 채널 모두 `0` 을 돌려줬다. 장치는 등록되지만 이 기종·펌웨어에서 실제 각도가 나오는지는 확인하지 못했다. [실측] 그래서 힌지 값은 감시 로직에 쓰지 않는다.

## 3. 사용 사례 — 노트북 서버를 "설치 환경 감시 장비" 로

### 3-1. 무엇을 만들었나

이 노드에는 반도체 공정 제어 기법을 실제 센서로 연습하는 작은 시뮬레이터(이하 fabcell)가 돈다. 노트북 센서를 팹 장비의 **설치 환경 센서**로 보고 다음을 감시한다.

| 감시 항목 | 센서 | 판정 |
|---|---|---|
| 충격 | 가속도계 | 기준 중력 벡터와의 차이가 0.4 m/s² 초과 |
| 수평 이탈 | 가속도계(1분 평균) | 기준 자세 대비 2° 초과 |
| 자유낙하 | 가속도계 | `|a|` 가 거의 0 |
| 정전 | 배터리·어댑터(`/sys/class/power_supply`) | 어댑터 연결 끊김 |
| 공정 변수 | CPU 패키지·칩셋 온도(`/sys/class/thermal`) | SPC 관리도(Western Electric, CUSUM) |

이상이 생기면 실제 팹 장비처럼 SECS/GEM 형식의 알람·이벤트를 내고, 가상 공정을 **HOLD** 한다. 시스템 상태는 systemd user 서비스로 띄우고 텔레그램으로 알린다.

센서 허브의 장점이 그대로 살아난다. 별도 IoT 보드나 USB 센서를 붙이지 않고, 이미 있는 노트북 하나로 진동·자세·전원·온도를 모두 잰다. [추론]

### 3-2. 실제로 난 오경보 — 31.5° 와 5.33 m/s²

어느 날 텔레그램에 이 알림이 2분마다 찍히기 시작했다.

```
🏭 fabcell 설치 환경 이벤트 SHOCK — 충격 5.33 m/s² (기준 대비) → 공정 HOLD
```

로그를 보면 첫 SHOCK 과 함께 이런 줄이 있었다. [실측]

```
[환경] LEVEL_OUT: 기준 자세 대비 31.5°
[환경] SHOCK: 충격 5.33 m/s² (기준 대비)
```

노트북이 옮겨졌거나 화면 각도가 바뀌어 **놓인 자세가 31.5° 달라진 것**이다. 실제로 부딪힌 게 아니다. 그런데 왜 매번 "충격 5.33" 일까?

충격 판정식은 지금 가속도 벡터와 처음 저장한 기준 중력 벡터의 차이(벡터 거리)였다. 가만히 있는 물체의 가속도는 중력 하나뿐이고 크기 *g* 는 그대로다. 그러니 방향만 θ 만큼 돌면 두 벡터의 거리는 다음과 같다.

```
|a − g_ref| = 2 · g · sin(θ / 2)
            = 2 × 9.81 × sin(15.75°)
            ≈ 5.33 m/s²
```

로그 값과 정확히 맞는다. 문턱(0.4 m/s²)은 약 2.3° 기울기만으로 넘는다. 그래서 **자세가 바뀌면 그 뒤로는 영원히 충격 상태**가 된다. 2분 재발 억제 간격마다 같은 값이 다시 찍힌 이유다.

### 3-3. 교훈 — 정적 성분과 동적 성분을 나눠야 한다

[추론] 가속도계 한 개로 충격과 자세를 함께 보려면 신호를 둘로 나눠야 한다.

- **자세(정적)**: 느린 저역 통과 평균. 기준 대비 각도로 판정한다(이번 LEVEL_OUT 처럼).
- **충격(동적)**: *최근 평균*과의 차이(고역 통과)로 판정한다. 고정된 설치 기준과 비교하지 않는다.

또는 자세가 바뀐 것이 확인되면 기준 중력 벡터를 새 자세로 다시 잡고, 그 사실을 이벤트로 한 번만 남긴다. 실제 팹에서도 장비 재설치 후 레벨링을 다시 하고 기준을 다시 잡는 것과 같은 이치다.

## 4. 정리

- 이 노트북(8세대 Core i7)에는 Intel ISH 와 가속도계·자이로·지자기·기울기·자세 센서가 들어 있다. 이 센서들은 표준 HID Sensors usage 로 노출된다. 리눅스는 범용 드라이버(`hid-sensor-hub` + IIO)로 이 센서들을 바로 sysfs 에 올린다.
- 서버로 전환한 노트북에서는 이 센서들로 별도 하드웨어 없이 진동·자세·낙하를 감시할 수 있다.
- 단, 가속도계 값에는 항상 중력이 섞여 있다. 고정 기준과의 차이만 보면 "기울어짐" 이 "충격" 으로 둔갑한다.

## References

1. Linux kernel documentation — *Intel Integrated Sensor Hub (ISH)*. <https://docs.kernel.org/hid/intel-ish-hid.html>
2. Linux kernel documentation — *HID Sensors Framework*. <https://docs.kernel.org/hid/hid-sensor.html>
3. Linux kernel documentation — *Industrial I/O: Introduction*. <https://docs.kernel.org/driver-api/iio/intro.html>
4. USB Implementers Forum — *HID Usage Tables 1.5*, Sensors Page (0x20). <https://usb.org/sites/default/files/hut1_5.pdf>
5. Microsoft — *HID Sensors Usages*. <https://learn.microsoft.com/en-us/windows-hardware/design/whitepapers/hid-sensors-usages>
6. Linux kernel source — `drivers/iio/position/hid-sensor-custom-intel-hinge.c`. <https://github.com/torvalds/linux/blob/master/drivers/iio/position/hid-sensor-custom-intel-hinge.c>
