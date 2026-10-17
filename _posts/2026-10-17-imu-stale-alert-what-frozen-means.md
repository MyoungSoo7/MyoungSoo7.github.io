---
layout: post
title: "5일 동안 울린 '센서 멈춤' 경보 — 센서는 살아 있었다, 틀린 건 '멈춤'의 정의였다"
date: 2026-10-17 15:30:08 +0900
categories: [observability]
tags: [prometheus, alerting, iio, hid-sensor, sre, false-positive, homelab]
---

홈랩 노트북 노드 하나에서 `SentinelImuStale`(가속도계 멈춤 의심) 경보가 **5일 12시간** 동안 꺼지지 않았다. AI 분석 에이전트는 같은 경보를 72시간 안에 여섯 번 조사했고, 판정은 「의심 → 장애 → 의심 → 장애 → 장애 → 의심」으로 오락가락했다. 결론부터 말하면 **센서는 처음부터 끝까지 살아 있었다.** 틀린 건 경보가 「멈춤」을 정의한 방식이었다.

이 글은 그 경보를 어떻게 진단했고 무엇을 바꿨는지, 그리고 **아직 무엇을 모르는지**를 적는다. 이 수집기를 하루 만에 만든 이야기는 [SENTINEL 하루 빌드]({{ site.baseurl }}/2026/09/28/sentinel-one-day-build/)에 있다.

## 1. 경보가 본 것

수집기는 노트북 내장 가속도계를 리눅스 IIO sysfs 로 0.2초마다 읽는다. 1분 창(약 300샘플)마다 **세 축 값이 연속으로 똑같았던 최대 샘플 수**를 `sentinel_imu_stale_samples_max` 로 내보낸다. 경보 규칙은 이랬다.

```yaml
- alert: SentinelImuStale
  expr: sentinel_imu_stale_samples_max >= 25 or sentinel_imu_window_samples == 0
  for: 5m
```

25샘플 × 0.2초 = **5초 동안 값이 안 바뀌면 멈춤**이라는 정의다. Prometheus 의 `for` 는 그 조건이 평가 때마다 계속 참인지 5분간 지켜본 뒤 firing 으로 올린다. 조건이 한 번이라도 거짓이 되면 다시 꺼진다([Prometheus 공식 문서 — Alerting rules](https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/)). 5일 내내 꺼지지 않았다는 건 1분 창 거의 전부에서 5초 이상 같은 값이 나왔다는 뜻이다.

## 2. 센서가 죽었는지부터 확인했다

경보 이름이 「멈춤」이니까 먼저 진짜 멈췄는지를 쟀다. 노드에 들어가 sysfs 를 0.2초 간격으로 200번 직접 읽었다.

| 측정 | 값 |
| --- | --- |
| 200회 읽기 중 값이 바뀐 횟수 | 7 |
| 같은 값이 가장 길게 이어진 횟수 | 66 (약 13초) |
| 누적 샘플 카운터 | 계속 증가 |
| sysfs 읽기 오류 | 0 |
| 진동 RMS·자이로 RMS | 0 아님 |

값은 **느리게라도 바뀐다.** 죽은 센서는 영원히 같은 값을 내거나 읽기 자체가 실패한다. 이건 둘 다 아니다.

## 3. "기준이 빡빡했다"는 첫 진단은 반만 맞았다

여기서 첫 결론을 냈다. "노트북이 가만히 있으면 5초쯤 같은 값은 당연하다. 기준이 빡빡했다." 그런데 과거 데이터를 보니 이 설명이 틀렸다.

| 기간 | 하루 중 `stale_samples_max >= 25` 비율 | 1시간 평균 stale_max |
| --- | --- | --- |
| 10-04 ~ 10-11 | **0%** | 약 1.6 |
| 10-12 00:26 이후 | **100%** | 약 80 |

10월 12일 00:26 전까지는 **0.2초마다 값이 바뀌었다.** 그 순간부터 센서가 값을 갱신하는 주기가 계단처럼 느려졌다. 기준이 원래 빡빡했다면 그 전에도 울렸어야 한다. 정상이던 동작이 어느 시점부터 달라진 것이다.

그 시각 전후를 확인한 결과는 이렇다.

- 하루 전(10-11 00:47)에 덮개를 열고 닫은 기록이 있다. 그때 기울기가 0.03° 에서 3° 로 바뀌었다. 다만 갱신 주기 변화와는 **23시간 반**이 떨어져 있어서 직접 원인으로 묶을 수 없다.
- 10-12 00:26 전후의 커널·시스템 로그에는 센서 관련 메시지가 없다.
- IIO 버퍼가 켜져 있는 걸(`buffer/enable = 1`) 보고 의심했다. 그래서 **버퍼를 껐다 켜서 대조**했다. 결과는 버퍼 on 7/60, off 4/60, 다시 on 4/60 으로 같은 양상이었다. 버퍼는 원인이 아니어서 원래대로 켜 두었다.

이 노트북의 가속도계는 CPU 가 직접 읽는 칩이 아니다. **HID 센서 허브**(인텔 ISH) 뒤에 있다. 리눅스 커널 문서에 따르면 센서 허브는 HID 1.12 센서 사용 테이블을 따르는 HID 장치다. 값은 허브가 보내는 HID 리포트로 들어온다([Linux kernel — HID Sensors Framework](https://docs.kernel.org/hid/hid-sensor.html)). 커널 드라이버는 허브의 보고 간격(reporting interval)과 변화 민감도(sensitivity) 같은 피처를 읽고 쓴다([drivers/iio/common/hid-sensors/hid-sensor-attributes.c](https://github.com/torvalds/linux/blob/master/drivers/iio/common/hid-sensors/hid-sensor-attributes.c)). 즉 **언제 새 값을 줄지 정하는 주체는 허브 펌웨어**다. 허브의 내부 상태가 바뀌면 OS 쪽 설정이 그대로여도 갱신이 느려질 수 있다. sysfs 의 `sampling_frequency` 는 여전히 10 Hz 로 읽혔다.

> ⚠️ 위 문단은 **가능성**이다. 10-12 00:26 에 허브 안에서 무엇이 바뀌었는지는 확인하지 못했다. 허브 펌웨어 상태를 직접 읽을 수단이 없고, 시각이 맞는 로그도 없다.

## 4. 그래서 무엇을 "멈춤"이라 부를 것인가

경보의 이름과 주석은 「센서 멈춤 — 설비 이상과 센서 이상을 가르는 핵심 분류」였다. 그런데 실제 조건 `>= 25` 는 **멈춤이 아니라 느림**을 쟀다. 이름과 측정이 어긋나 있었고, 그래서 사람도 AI 도 같은 데이터를 보고 장애와 의심 사이를 오갔다.

Google SRE 책의 모니터링 장(Rob Ewaschuk 집필)은 알림 규칙에 이렇게 물으라고 한다. "**이 알림을, 무해하다는 걸 알면서 무시할 수 있는 때가 오는가?**" 그리고 "모든 페이지는 행동할 수 있어야 한다(Every page should be actionable)"([Google SRE Book, Ch.6 Monitoring Distributed Systems](https://sre.google/sre-book/monitoring-distributed-systems/)). 5일째 울리는 이 경보는 첫째 질문에 "예"였다. 할 수 있는 행동도 없었다. 센서를 재시작할 대상도, 고칠 설정도 없었다.

바꾼 규칙은 이렇다.

```yaml
# 멈춤 = 1분 창 전체에서 값이 한 번도 안 바뀜, 또는 샘플 0개
- alert: SentinelImuStale
  expr: (sentinel_imu_window_samples > 0 and sentinel_imu_stale_samples_max >= sentinel_imu_window_samples - 1) or sentinel_imu_window_samples == 0
  for: 5m
  labels: {severity: warning}

# 느림 = 멈춤은 아니지만 5초 넘게 같은 값 — 알림 없이 기록만
- alert: SentinelImuSlowUpdate
  expr: sentinel_imu_stale_samples_max >= 25 and sentinel_imu_window_samples > 0
  for: 1h
  labels: {severity: info}
```

포인트는 세 가지다.

1. **멈춤의 정의를 측정 단위에 맞췄다.** 창 하나가 N샘플이면 전부 같을 때 연속 동일 횟수는 N−1 이다. 수집기는 창마다 카운터를 0으로 되돌리므로 이 비교는 창 안에서만 성립한다. 고정 숫자 25 대신 그 창의 실제 샘플 수와 비교하므로 샘플링 주기가 바뀌어도 의미가 유지된다.
2. **느림은 지우지 않고 등급을 내렸다.** 이 클러스터에서 `info` 는 알림 경로로 나가지 않는다. 그래도 Prometheus 에 상태가 남아 나중에 "언제부터 느렸나"를 다시 물을 수 있다. 측정을 지워 초록을 만들면 센서가 진짜로 나빠질 때 볼 데이터가 없다.
3. **배포 전에 과거로 재봤다.** 새 조건을 14일 이력에 대입했다. 창 대비 연속 동일 비율은 최대 0.86 이었고, 5분 연속 최솟값은 0.33 이었다. 새 조건(약 0.997 이상)은 그동안 **한 번도 참이 된 적이 없다.** 레이블 매칭이 의도대로 되는지는 조건을 일부러 느슨하게 바꾼 질의로 확인했다. 결과에 해당 노드가 잡혔다. 규칙 문법은 Prometheus Operator 의 서버 측 dry-run 으로 검증했다.

배포 후 Prometheus 에서 `SentinelImuStale` 이 firing 에서 inactive 로 바뀌었다. 대신 `SentinelImuSlowUpdate` 가 pending 으로 올라왔다. 지금 센서 상태를 정직하게 보여주는 그림이다.

## 5. 아직 안 풀린 것

- **왜 10-12 00:26 에 갱신이 느려졌는가.** 모른다. 다음에 해볼 대조군은 허브 드라이버 재바인드나 재부팅 뒤 갱신 주기가 원래대로(stale_max ≈ 1.6) 돌아오는지 보는 것이다. 돌아오면 허브 상태 문제, 안 돌아오면 다른 쪽이다.
- **"진짜 멈춤"을 실제로 잡는지는 아직 증명되지 않았다.** 14일 동안 진짜 멈춤 사례가 없었기 때문에, 확인된 건 "정상에서 안 울린다"까지다. 양성 사례로 검증하려면 수집기에 고정값을 주입하는 시험이 따로 필요하다.
- **새 기준이 놓치는 경우.** 센서가 30초마다 한 번만 값을 바꾸는 심각한 열화라면, 1분 창 안에 변화가 있으니 멈춤 경보는 울리지 않는다. 이 영역은 info 경보가 기록으로만 덮는다. 그 정도를 장애로 볼지는 이 센서를 무엇에 쓰느냐에 달린 운영 판단이고, 아직 정하지 않았다.

## 6. 정리

경보가 5일 동안 울릴 때 먼저 의심할 것은 센서가 아니라 **경보가 무엇을 재고 있는지**다. 이번에는 이름(멈춤)과 측정(5초 무변화)이 달랐고, 그 틈이 판정을 흔들었다. 고치는 방법은 기준 숫자를 키우는 게 아니었다. **정의를 측정 단위에 맞추고, 덜 심각한 상태는 지우지 않고 등급을 내리는 것**이었다.

## References

1. Prometheus Authors, "Alerting rules", Prometheus Documentation. <https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/>
2. Rob Ewaschuk, "Monitoring Distributed Systems", in *Site Reliability Engineering* (Beyer et al., eds.), O'Reilly / Google, 2016, Ch.6. <https://sre.google/sre-book/monitoring-distributed-systems/>
3. The Linux Kernel documentation, "HID Sensors Framework". <https://docs.kernel.org/hid/hid-sensor.html>
4. Linux kernel source, `drivers/iio/common/hid-sensors/hid-sensor-attributes.c` (reporting interval · sensitivity feature 처리). <https://github.com/torvalds/linux/blob/master/drivers/iio/common/hid-sensors/hid-sensor-attributes.c>
5. 본문의 수치(200회 직접 읽기, 버퍼 on/off 대조, 14일 이력 대입)는 필자 홈랩에서 2026-10-17 에 직접 측정한 1차 데이터다. 단일 장비 한 대의 관측이므로 일반화하지 않는다.
