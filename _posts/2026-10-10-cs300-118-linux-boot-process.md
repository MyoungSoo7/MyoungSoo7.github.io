---
layout: post
title: "[CS300 #118] 리눅스 부팅 과정 — 전원 버튼에서 로그인 프롬프트까지"
date: 2026-10-10 19:58:00 +0900
categories: [cs]
tags: [cs300, operating-systems, boot, uefi, systemd]
---

컴퓨터공학 300 주제 시리즈의 118번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

리눅스 부팅은 펌웨어(UEFI/BIOS) → 부트로더 → 커널 → initramfs → 실제 루트 파일 시스템의 init(PID 1, 보통 systemd) → 서비스들의 순서로 제어권을 넘겨주는 릴레이이며, 각 구간에서 실패하는 모습이 다르기 때문에 단계를 알면 "어디서 멈췄는지"를 바로 짚을 수 있다.

## 왜 필요한가

서버가 재부팅 후 올라오지 않을 때, 원인이 어디인지에 따라 대응이 완전히 다르다.

- 화면에 아무것도 안 나온다 → 펌웨어나 하드웨어.
- 부트로더 프롬프트에서 멈춘다 → 부트로더 설정이나 디스크 순서.
- `Kernel panic - not syncing: VFS: Unable to mount root fs` → 커널이 루트 파일 시스템을 못 찾음(initramfs 드라이버, `root=` 인자).
- 응급 모드(emergency shell)로 떨어진다 → `/etc/fstab` 의 잘못된 마운트, 파일 시스템 오류.
- 로그인은 되는데 서비스가 안 뜬다 → systemd 유닛 의존성.

홈랩 노드나 베어메탈 서버를 직접 운영하면 커널 업그레이드 후 부팅 실패를 한 번쯤 겪는다. 단계별 구조를 알면 원격 콘솔 화면 한 장으로도 범위를 좁힐 수 있다.

## 핵심 개념

### 전체 흐름

```
[전원]
   |
   v
(1) 펌웨어: UEFI 또는 BIOS
    하드웨어 초기화·자가 진단, 부팅 장치 선택
   |
   v
(2) 부트로더: GRUB, systemd-boot 등 (또는 커널의 EFI stub 직접 실행)
    커널 이미지 + initramfs 를 메모리에 올리고 커널 인자 전달
   |
   v
(3) 커널
    압축 해제, CPU·메모리·인터럽트 초기화, 드라이버 초기화
    initramfs 를 임시 루트(rootfs)로 풀고 그 안의 /init 실행
   |
   v
(4) initramfs 의 /init
    실제 루트 장치에 필요한 드라이버 적재(디스크, RAID, LVM, 암호화)
    실제 루트를 마운트하고 switch_root
   |
   v
(5) init = PID 1 (대부분 systemd)
    유닛 의존성에 따라 마운트, 네트워크, 서비스를 병렬 기동
   |
   v
(6) default.target 도달 -> 로그인 프롬프트 / 서비스 준비 완료
```

### (1) 펌웨어: BIOS 와 UEFI

| | 레거시 BIOS | UEFI |
|---|---|---|
| 부트 코드 위치 | 디스크 첫 섹터(MBR, 512바이트)의 작은 코드 | EFI 시스템 파티션(ESP, FAT 파일 시스템)의 `.efi` 실행 파일 |
| 파티션 테이블 | 주로 MBR | 주로 GPT |
| 부팅 항목 관리 | 장치 순서 | 펌웨어 NVRAM 의 부팅 항목 |
| 보안 부팅 | 없음 | Secure Boot(서명 검증) |

UEFI 는 파일 시스템을 읽을 수 있어서 부트로더를 "파일"로 실행한다. 리눅스 커널 자체를 EFI 실행 파일로 만들어 부트로더 없이 펌웨어가 바로 실행하게 하는 **EFI stub** 기능도 있다(커널 문서 참고).

### (2) 부트로더

GRUB 은 설정 파일을 읽어 메뉴를 보여 주고, 선택된 커널 이미지(`vmlinuz-...`)와 initramfs(`initrd.img-...`)를 메모리에 올린 뒤 **커널 명령줄**과 함께 커널로 점프한다. 커널 명령줄의 대표 항목은 다음과 같다.

| 인자 | 뜻 |
|---|---|
| `root=` | 실제 루트 파일 시스템 장치(UUID 로 지정하는 경우가 많다) |
| `ro` | 루트를 먼저 읽기 전용으로 마운트(이후 fsck 후 rw 로 재마운트) |
| `quiet`, `loglevel=` | 커널 메시지 양 |
| `init=` | PID 1 로 실행할 프로그램 지정 |
| `systemd.unit=` | 기본 대신 부팅할 target(예: `rescue.target`) |

전체 목록은 커널 문서의 kernel-parameters 에 있다.

### (3)~(4) 커널과 initramfs

커널은 루트 파일 시스템을 마운트해야 `/sbin/init` 을 실행할 수 있다. 그런데 루트가 NVMe 위의 LVM 위의 LUKS 암호화 볼륨이라면, 그것을 열 드라이버와 도구가 필요하다. 이것들을 모두 커널에 넣을 수는 없으니, **initramfs** 라는 작은 cpio 아카이브에 담아 함께 올린다.

커널 문서에 따르면 커널은 initramfs 를 메모리 기반 파일 시스템(rootfs)에 풀고 그 안의 `/init` 을 PID 1 로 실행한다. `/init` 은 필요한 모듈을 적재하고 실제 루트를 마운트한 뒤, `switch_root` 로 루트를 바꾸고 실제 init 을 `exec` 한다. PID 는 1 그대로다.

커널은 이 과정에서 커널 스레드를 관리하는 `kthreadd` 를 PID 2 로 만든다. 이후의 모든 커널 스레드는 이 프로세스의 자식이다.

### (5) PID 1: systemd

PID 1 은 특별하다. 고아 프로세스를 입양해 거두고, 죽으면 커널이 패닉에 빠진다. systemd 는 **유닛**(service, mount, socket, target...)과 그 사이의 의존성(`Requires=`, `Wants=`, `After=`)을 그래프로 보고 가능한 한 병렬로 기동한다. `bootup(7)` 매뉴얼에 `sysinit.target` → `basic.target` → `multi-user.target` 으로 이어지는 표준 순서가 그림으로 나와 있다. 서버는 보통 `multi-user.target`, 데스크톱은 `graphical.target` 을 기본으로 한다.

## 직접 해 보기

부팅의 흔적은 실행 중인 시스템의 `/proc` 과 `/sys` 에 남아 있다. 리눅스에서 일반 사용자 권한으로 돌린다.

```python
import os, time

print("펌웨어 방식      :", "UEFI" if os.path.isdir("/sys/firmware/efi") else "BIOS(레거시) 또는 판별 불가")
u = os.uname()
print("커널             :", u.sysname, u.release, u.machine)

with open("/proc/stat") as f:
    btime = int(next(l for l in f if l.startswith("btime")).split()[1])
with open("/proc/uptime") as f:
    up = float(f.read().split()[0])
print("부팅 시각        :", time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(btime)))
print("가동 시간        :", f"{up / 3600:.1f} 시간")

with open("/proc/1/comm") as f:
    print("PID 1            :", f.read().strip())
with open("/proc/cmdline") as f:            # 부트로더가 커널에 넘긴 인자 (키 이름만 출력)
    keys = [a.split("=")[0] for a in f.read().split()]
print("커널 인자 키     :", keys)
with open("/proc/2/comm") as f:
    print("PID 2            :", f.read().strip())
```

우분투 계열 x86-64 장비에서의 출력이다.

```
펌웨어 방식      : UEFI
커널             : Linux 6.8.0-139-generic x86_64
부팅 시각        : 2026-09-20 12:44:19
가동 시간        : 492.1 시간
PID 1            : systemd
커널 인자 키     : ['BOOT_IMAGE', 'root', 'ro']
PID 2            : kthreadd
```

`/sys/firmware/efi` 디렉터리가 있으면 UEFI 로 부팅한 것이다. `/proc/cmdline` 에는 GRUB 이 넘긴 커널 이미지 경로(`BOOT_IMAGE`), 루트 장치(`root=`), 읽기 전용 마운트(`ro`)가 보인다. 값에는 디스크 UUID 같은 장비 고유 정보가 들어 있어 여기서는 키만 출력했다. PID 1 이 systemd, PID 2 가 kthreadd 라는 것도 확인된다. 단계별 소요 시간이 궁금하면 `systemd-analyze` (펌웨어·부트로더·커널·사용자 공간 시간)와 `systemd-analyze blame`(유닛별 시간)을 쓴다.

## 현업에서는

- **커널 업그레이드 후 부팅 실패**: 새 커널의 initramfs 가 제대로 만들어지지 않으면 "Unable to mount root fs" 로 멈춘다. GRUB 메뉴에서 이전 커널로 부팅해 살린 뒤 initramfs 를 다시 생성한다. 원격 장비라면 부팅 메뉴 노출 시간과 이전 커널 보존 개수를 미리 확인해 둔다.
- **fstab 한 줄이 부팅을 막는다**: 존재하지 않는 디스크를 `/etc/fstab` 에 넣으면 systemd 가 그 마운트를 기다리다 응급 모드로 떨어진다. 필수가 아닌 디스크에는 `nofail` 옵션을 붙이는 것이 관례다.
- **이전 부팅의 로그**: `journalctl -b -1` 은 직전 부팅의 로그를 보여 준다(저널이 영구 저장으로 설정된 경우). 갑자기 재부팅된 노드의 원인을 찾을 때 첫 번째로 본다.
- **k3s 노드의 기동 순서**: k3s 는 systemd 서비스로 뜨고 네트워크가 준비된 뒤 시작되도록 유닛에 의존성이 걸린다. 노드가 재부팅 후 `NotReady` 로 오래 남으면 노드의 서비스 상태와 `journalctl -u` 로 k3s 유닛 로그를 먼저 본다.

## 확인 문제

1. UEFI 와 레거시 BIOS 가 부트로더를 찾는 방식의 차이는?
2. initramfs 가 필요한 이유는 무엇인가?
3. `switch_root` 이후에도 init 의 PID 가 1 인 이유는?
4. 부팅 중 "VFS: Unable to mount root fs" 패닉이 났다. 어느 단계의 문제이고, 의심할 것 두 가지는?
5. 리눅스 시스템이 UEFI 로 부팅되었는지 실행 중에 확인하는 방법은?

### 풀이

1. BIOS 는 디스크 첫 섹터(MBR)의 부트 코드를 실행하고, UEFI 는 EFI 시스템 파티션의 FAT 파일 시스템에서 `.efi` 실행 파일을 찾아 실행한다.
2. 실제 루트 파일 시스템을 마운트하는 데 필요한 드라이버와 도구(스토리지 드라이버, LVM, RAID, 암호화 해제)를 커널에 모두 넣지 않고 부팅 초기에 제공하기 위해서다.
3. `switch_root` 는 새 프로세스를 만드는 것이 아니라 같은 프로세스가 루트를 바꾼 뒤 `exec` 로 실제 init 프로그램으로 갈아타는 것이기 때문이다. `exec` 는 PID 를 유지한다.
4. 커널이 initramfs 이후 실제 루트를 마운트하는 단계다. initramfs 에 스토리지 드라이버가 빠졌거나, 커널 명령줄의 `root=` 가 잘못된 장치를 가리키는 경우를 의심한다.
5. `/sys/firmware/efi` 디렉터리가 존재하는지 확인한다.

## 더 읽을거리 (References)

- Linux man-pages, [boot(7)](https://manpages.debian.org/bookworm/manpages/boot.7.en.html), systemd [bootup(7)](https://manpages.debian.org/bookworm/systemd/bootup.7.en.html)
- Linux kernel documentation, [Ramfs, rootfs and initramfs](https://docs.kernel.org/filesystems/ramfs-rootfs-initramfs.html)
- Linux kernel documentation, [The EFI Boot Stub](https://docs.kernel.org/admin-guide/efi-stub.html), [The kernel's command-line parameters](https://docs.kernel.org/admin-guide/kernel-parameters.html)
- systemd, [systemd-analyze(1)](https://manpages.debian.org/bookworm/systemd/systemd-analyze.1.en.html)
