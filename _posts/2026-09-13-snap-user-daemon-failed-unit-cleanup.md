---
layout: post
title: "systemctl --failed 가 못 보는 failed 유닛 — snap 유저 데몬 정리기"
date: 2026-09-13 04:14:57 +0900
categories: [infra, linux]
tags: [systemd, snap, user-daemon, apparmor, dbus, ubuntu, homelab]
---

홈랩 K3s 노드들의 저널을 훑다가 이상한 것을 봤다. 저널에는 `snap.firmware-updater.firmware-notifier.service` 가 매일 새벽 3시에 5번 죽고 포기하는 기록이 또렷한데, 정작 `systemctl --failed` 는 **0 loaded units** 로 깨끗했고 `journalctl -u snap.firmware-updater.firmware-notifier.service` 도 빈 결과를 돌려줬다. 유닛이 실패하고 있는데 표준 점검 명령 두 개가 모두 "그런 유닛 없다"고 답하는 상황 — 이 글은 그 사각지대의 정체와, 두 노드에서 각각 다른 원인으로 죽고 있던 이 서비스를 정리한 기록이다.

## 사각지대의 정체: 시스템 인스턴스와 유저 인스턴스

systemd 는 PID 1 의 **시스템 인스턴스** 하나만 도는 게 아니다. 로그인한 사용자마다 별도의 **유저 인스턴스**(`systemd --user`)가 뜨고, 유저 유닛은 그 안에서 관리된다([systemctl(1)](https://man7.org/linux/man-pages/man1/systemctl.1.html) 의 `--user` 옵션). `systemctl --failed` 와 `journalctl -u` 는 기본이 시스템 인스턴스 대상이라, 유저 유닛의 실패는 **구조적으로 안 보인다.** 실제 저널을 보면 구분이 드러난다:

```
Sep 13 03:00:02 solomon systemd[5645]: snap.firmware-updater.firmware-notifier.service: Failed with result 'exit-code'.
```

`systemd[1]` 이 아니라 `systemd[5645]` — 유저 매니저 프로세스다. 이 유닛의 상태를 보려면 `systemctl --user --failed` 처럼 `--user` 를 붙여야 하고, 그마저도 **그 사용자 세션 안에서** 실행해야 한다. 원격 점검 스크립트가 root 로 `systemctl --failed` 만 돌린다면 이런 실패는 영원히 집계되지 않는다. 내가 이 유닛을 찾은 경로도 결국 유닛 이름 기반 조회가 아니라 저널 전문 grep 이었다.

이 유닛이 유저 인스턴스에 있는 이유는 snap 의 **user daemon** 기능이다. snap 앱에 `daemon-scope: user` 를 주면 PID 1 이 아니라 각 사용자 세션의 systemd 에 등록된다([snapcraft.yaml 레퍼런스](https://documentation.ubuntu.com/snapcraft/latest/reference/snapcraft-yaml/), 도입 배경은 [snapd 포럼의 기능 제안](https://forum.snapcraft.io/t/enabling-user-daemons-and-d-bus-activation/22318)). `snap services` 출력의 `user,timer-activated` 표기가 그 표시다:

```
Service                                Startup  Current   Notes
firmware-updater.firmware-notifier     enabled  inactive  user,timer-activated
firmware-updater.firmware-updater-app  enabled  inactive  user,dbus-activated
```

문제의 주인공은 [firmware-updater](https://github.com/canonical/firmware-updater) — Canonical 이 Flutter/Dart 로 만든 우분투용 펌웨어 업데이트 GUI 앱이다. 본체는 D-Bus 활성화로 필요할 때만 뜨고, 곁딸린 notifier 가 유저 타이머로 **매일 새벽 3시에** 깨어나 펌웨어 업데이트가 있으면 데스크톱 알림을 띄운다. 데스크톱에서는 합리적인 설계다. 하지만 이 노드들은 데스크톱 이미지로 설치만 됐을 뿐 아무도 화면 앞에 앉지 않는 K3s 워커다 — 알림을 받을 사람이 없는 곳에서 알림 데몬이 매일 죽고 있었다.

## 노드별 부검: 같은 유닛, 다른 사인(死因)

흥미로운 건 두 노드의 죽는 이유가 서로 달랐다는 점이다.

**solomon — 로그인 세션의 주인이 gdm 그리터였다.** 아무도 로그인하지 않은 데스크톱에서 유일한 "사용자 세션"은 로그인 화면(gdm 그리터)의 것이고, 그 계정의 홈은 `/home` 이 아니라 `/run/gdm3` 아래다. snap 의 AppArmor 샌드박스는 기본적으로 `/home` 밖의 홈 디렉터리 접근을 허용하지 않아서, notifier 는 뜨자마자 이렇게 죽었다:

```
firmware-updater.firmware-notifier[2939209]: Sorry, home directories outside of /home needs configuration.
systemd[5645]: snap.firmware-updater.firmware-notifier.service: Main process exited, code=exited, status=1/FAILURE
```

에러 메시지가 안내하는 [home-outside-home 문서](https://snapcraft.io/docs/home-outside-home)는 `/home` 밖 홈을 쓰려면 시스템 설정(`snap set system homedirs=...`)이 필요하다는 내용이다. 즉 이건 버그라기보다 "그리터 세션에서까지 유저 데몬을 돌리려던" 조합이 샌드박스 정책과 충돌한 경우다.

**ilwon — 알림을 받아줄 데몬이 없었다.** 여기는 홈 문제를 통과하고도 한 발 더 가서 죽었다. notifier 가 D-Bus 로 데스크톱 알림을 쏘는 순간(`NotificationsClient.notify`), 받아줄 알림 서비스가 세션에 없으니 Dart 예외가 그대로 터졌다:

```
firmware-updater.firmware-notifier[3688288]: Unhandled exception:
firmware-updater.firmware-notifier[3688288]: #2  NotificationsClient.notify (package:desktop_notifications/src/notifications_client.dart:274)
firmware-updater.firmware-notifier[3688288]: #4  main (file:///build/firmware-updater/parts/firmware-notifier/build/apps/firmware_notifier/bin/firmware_notifier.dart:8)
systemd[1801]: snap.firmware-updater.firmware-notifier.service: Main process exited, code=exited, status=255/EXCEPTION
```

둘 다 결말은 같다. systemd 의 시작 제한 — [systemd.unit(5)](https://man7.org/linux/man-pages/man5/systemd.unit.5.html) 기준 기본값은 10초 안에 5회(`StartLimitIntervalSec=10s`, `StartLimitBurst=5`) — 에 걸려 카운터가 5에 도달하면 재시도를 포기한다:

```
systemd[5645]: snap.firmware-updater.firmware-notifier.service: Scheduled restart job, restart counter is at 5.
systemd[5645]: snap.firmware-updater.firmware-notifier.service: Start request repeated too quickly.
```

그리고 다음 날 새벽 3시, 타이머가 다시 깨우고, 다시 5번 죽는다. 매일 반복되는 조용한 실패 루프다. 참고로 세 번째 노드(louise)에는 이 snap 자체가 없었다 — 같은 용도의 노드인데 설치 이력만 다른 것이다.

## 정리: 지우지 않고 끈다

선택지는 셋이었다. ① 근본 수리(solomon 은 `homedirs` 설정, ilwon 은 알림 데몬 설치), ② `snap remove firmware-updater`, ③ notifier 서비스만 비활성화. ①은 "아무도 안 보는 데스크톱 알림"을 살리자고 시스템 설정을 늘리는 일이라 배보다 배꼽이 크고, ②는 나중에 화면 앞에서 펌웨어를 올릴 가능성까지 닫는다. 답은 ③이다:

```bash
sudo snap stop --disable firmware-updater.firmware-notifier
systemctl --user reset-failed snap.firmware-updater.firmware-notifier.service
```

`snap stop --disable` 은 snapd 가 공식 제공하는 서비스 비활성화 경로다([서비스 관리 문서](https://snapcraft.io/docs/service-management)). systemd 유닛을 직접 mask 하는 것보다 이쪽이 나은 이유는, snap 은 refresh 때 유닛 파일을 다시 만들 수 있어서 snapd 계층에 기록된 비활성화라야 갱신 후에도 의도가 유지되기 때문이다. `reset-failed` 는 남아 있던 failed 상태와 재시작 카운터를 지운다 — 이걸 안 하면 서비스는 껐는데 상태 표시만 계속 빨간 채로 남는다.

두 노드 모두 적용 후 실측: `snap services` 에서 notifier 가 `disabled`, `systemctl --user --failed` 는 0 유닛. 본체 앱(`firmware-updater-app`)은 `enabled` 그대로라, 언젠가 데스크톱으로 쓸 일이 생기면 알림만 다시 켜면 된다.

## 남는 교훈

- **`systemctl --failed` 는 절반만 본다.** 유저 인스턴스의 실패는 시스템 인스턴스 조회에 안 잡힌다. 노드 점검 스크립트에 `journalctl` 전문 grep(예: `Failed with result`)이나 로그인 세션별 `systemctl --user --failed` 를 넣어야 전체가 보인다.
- **`Notes` 열을 읽자.** `snap services` 의 `user,timer-activated` 넉 자가 "이 유닛은 어느 systemd 에 있고 언제 뜨는가"를 다 말해준다.
- **데스크톱 이미지로 깐 서버에는 데스크톱의 유령이 산다.** 그리터 세션, 알림 데몬 부재, `/run/gdm3` 홈 — 전부 데스크톱 전제의 소프트웨어가 서버 현실과 부딪히며 낸 소리다. 죽어도 아무 기능도 잃지 않는 실패라면, 근본 수리보다 "그 전제를 끄는 것"이 맞는 수리일 때가 있다.

## References

- man7.org, [systemctl(1)](https://man7.org/linux/man-pages/man1/systemctl.1.html) — `--user`, `--failed`, `reset-failed`
- man7.org, [systemd.unit(5)](https://man7.org/linux/man-pages/man5/systemd.unit.5.html) — `StartLimitIntervalSec=`/`StartLimitBurst=` 기본값
- Snapcraft 공식 문서, [snapcraft.yaml 레퍼런스 — daemon-scope](https://documentation.ubuntu.com/snapcraft/latest/reference/snapcraft-yaml/)
- Snapcraft 공식 문서, [Service management](https://snapcraft.io/docs/service-management)
- Snapcraft 공식 문서, [Home directories outside of /home](https://snapcraft.io/docs/home-outside-home)
- snapd 포럼(공식), [Enabling user daemons and D-Bus activation](https://forum.snapcraft.io/t/enabling-user-daemons-and-d-bus-activation/22318)
- Canonical, [firmware-updater 소스 저장소](https://github.com/canonical/firmware-updater)

*본문의 로그·서비스 상태는 필자의 우분투 K3s 노드 2대에서 2026-09-13 에 직접 채취·실측한 것이다.*
