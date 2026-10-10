---
layout: post
title: "[CS300 #222] 리눅스 서버 운영 기초 — 서버가 아플 때 먼저 보는 곳"
date: 2026-10-10 21:42:00 +0900
categories: [cs]
tags: [cs300, devops, linux, sysadmin, procfs]
---

컴퓨터공학 300 주제 시리즈의 222번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

리눅스 서버 운영은 "디렉터리 구조, 프로세스, 자원(CPU·메모리·디스크), 로그, 원격 접속" 다섯 가지를 읽을 줄 아는 데서 시작한다. 대부분의 답은 `/proc` 과 로그에 이미 있다.

## 왜 필요한가

컨테이너와 쿠버네티스가 아무리 추상화를 쌓아도 그 아래는 리눅스 프로세스다. 파드가 OOMKilled 로 죽으면 그것은 커널의 메모리 회수 결정이고, "디스크가 찼다"는 경보는 결국 어느 파일시스템의 어느 디렉터리 문제다. 위 계층의 오류 메시지를 아래 계층의 사실로 번역하는 능력이 운영의 기본기다.

## 핵심 개념

### 디렉터리 구조 (FHS)

리눅스 배포판은 대체로 Filesystem Hierarchy Standard(FHS) 를 따른다. 운영자가 자주 보는 곳은 다음과 같다.

| 경로 | 용도 |
|---|---|
| `/etc` | 호스트별 설정 파일 |
| `/var/log` | 로그 |
| `/var/lib` | 프로그램의 상태 데이터(DB 파일, 컨테이너 이미지 등) |
| `/home` | 사용자 홈 |
| `/tmp` | 임시 파일 |
| `/usr` | 배포판이 설치한 프로그램(읽기 전용 취급) |
| `/opt` | 별도 패키지 |
| `/proc`, `/sys` | 커널이 보여 주는 가상 파일시스템 |

"디스크가 찼다"는 경보가 오면 대개 `/var/log` 나 `/var/lib` 가 범인이다. 로그가 회전(rotate)되지 않거나, 컨테이너 이미지가 쌓였거나, DB 가 커졌다.

### 프로세스와 신호

프로그램이 실행되면 PID 를 가진 프로세스가 된다. 운영자는 `ps`, `top` 으로 프로세스를 보고 `kill` 로 **신호**를 보낸다.

| 신호 | 번호 | 기본 동작 | 쓰임 |
|---|---|---|---|
| SIGTERM | 15 | 종료 | 정상 종료 요청. 프로그램이 정리 후 끝낼 수 있다 |
| SIGKILL | 9 | 종료 | 강제 종료. 잡거나 무시할 수 없다 |
| SIGHUP | 1 | 종료 | 많은 데몬이 "설정 다시 읽기"로 처리한다 |
| SIGINT | 2 | 종료 | 터미널의 Ctrl+C |

순서가 중요하다. 먼저 SIGTERM 을 보내고 기다린 다음에야 SIGKILL 을 쓴다. 쿠버네티스도 파드를 지울 때 같은 순서를 따른다. SIGTERM 을 보내고 유예 시간(기본 30초)이 지나면 SIGKILL 을 보낸다.

### /proc: 커널이 열어 둔 창

`/proc` 은 디스크에 있는 파일이 아니다. 읽을 때마다 커널이 현재 상태를 만들어 준다. `top`, `free`, `ps` 같은 도구도 결국 여기를 읽는다.

- `/proc/loadavg`: 1·5·15분 평균 부하
- `/proc/meminfo`: 메모리 상세(MemTotal, MemAvailable 등)
- `/proc/<pid>/status`: 프로세스 상태, 메모리 사용량(VmRSS)
- `/proc/<pid>/fd/`: 프로세스가 연 파일 디스크립터

### 자원 읽는 법

**CPU 와 load average.** load average 는 실행 중이거나 실행을 기다리는 태스크 수에, 리눅스에서는 중단 불가능한 대기(D 상태, 주로 디스크 I/O 대기) 태스크까지 더한 값의 지수 이동 평균이다. 그래서 CPU 가 한가해도 디스크가 느리면 load 가 오른다. 판단은 코어 수와 비교해서 한다. 4코어에서 load 4 는 꽉 찬 상태, 8 은 대기열이 쌓이는 상태로 읽는다.

**메모리.** `free` 의 `free` 칸은 작아도 걱정할 필요가 없다. 리눅스는 남는 메모리를 페이지 캐시로 쓰고 필요하면 돌려준다. 봐야 할 값은 `available`(MemAvailable)이다. 이것이 바닥나면 커널의 OOM killer 가 프로세스를 골라 죽인다.

**디스크.** 두 가지를 본다. 용량(`df -h`)과 inode(`df -i`). 작은 파일이 수백만 개 쌓이면 용량은 남아도 inode 가 바닥나 파일을 만들 수 없다. 또 하나의 함정은 "지웠는데 공간이 안 돌아오는" 경우다. 프로세스가 열어 둔 파일은 삭제해도 닫힐 때까지 공간이 반환되지 않는다.

### 로그

systemd 를 쓰는 배포판은 journald 가 로그를 모은다.

```bash
journalctl -u nginx.service --since "1 hour ago"   # 특정 유닛, 최근 1시간
journalctl -p err -b                              # 이번 부팅 이후 에러 이상
journalctl -k                                     # 커널 메시지(OOM 등)
```

전통적인 텍스트 로그는 `/var/log` 아래에 남는다. 커널의 OOM 기록, 디스크 오류는 커널 로그에서 찾는다.

### 원격 접속과 최소 권한

서버 접속은 SSH 로 한다. 기본 원칙은 세 가지다.

1. 비밀번호 대신 공개키 인증을 쓴다(`PasswordAuthentication no`).
2. root 직접 로그인을 막는다(`PermitRootLogin no`). 일반 계정으로 들어와 `sudo` 로 올린다.
3. 필요한 사람에게만, 필요한 권한만 준다.

## 직접 해 보기

`/proc` 을 직접 읽어 `uptime`·`free` 의 핵심 값을 재현해 보자. 리눅스에서 실행한다.

```python
import os

def loadavg():
    with open("/proc/loadavg") as f:
        one, five, fifteen = f.read().split()[:3]
    return float(one), float(five), float(fifteen)

def meminfo():
    info = {}
    with open("/proc/meminfo") as f:
        for line in f:
            key, rest = line.split(":", 1)
            info[key] = int(rest.split()[0])  # kB
    return info

cores = os.cpu_count()
l1, l5, l15 = loadavg()
print(f"cores={cores} load(1m)={l1:.2f} per-core={l1 / cores:.2f}")

m = meminfo()
total, avail = m["MemTotal"], m["MemAvailable"]
print(f"mem total={total // 1024} MiB available={avail // 1024} MiB "
      f"({avail / total:.0%} available)")

st = os.statvfs("/")
used = 1 - st.f_bavail / st.f_blocks
iused = 1 - st.f_favail / st.f_files if st.f_files else 0
print(f"/ disk used={used:.0%} inode used={iused:.0%}")

with open(f"/proc/{os.getpid()}/status") as f:
    rss = [l for l in f if l.startswith("VmRSS")][0].split()[1]
print(f"this python process RSS={int(rss) // 1024} MiB")
```

출력은 머신마다 다르다. 형태는 이렇다.

```
cores=4 load(1m)=0.85 per-core=0.21
mem total=15843 MiB available=9120 MiB (58% available)
/ disk used=41% inode used=7%
this python process RSS=9 MiB
```

여기서 `per-core` 가 1 을 오래 넘거나, `available` 비율이 한 자릿수로 떨어지거나, 디스크·inode 사용률이 90% 를 넘으면 들여다볼 때다. 모니터링 시스템의 기본 경보 규칙도 대개 이 값들로 만든다.

## 현업에서는

- **장애 첫 1분 루틴.** 접속하면 `uptime`(부하), `free -h`(메모리), `df -h`(디스크), `journalctl -p err -b`(에러) 순으로 본다. 이것만으로 원인 영역이 대부분 좁혀진다.
- **"지웠는데 디스크가 안 줄어요".** 로그 파일을 `rm` 했는데 데몬이 그 파일을 계속 열고 있는 경우다. `/proc/<pid>/fd` 에서 `(deleted)` 표시가 붙은 링크로 찾는다. 해결은 데몬 재시작이나 로그 재오픈 신호다. 처음부터 logrotate 의 설정을 맞춰 두는 것이 낫다.
- **쿠버네티스 노드에서도 똑같다.** 파드가 이유 없이 재시작되면 노드의 커널 로그에서 OOM 기록을 찾는다. 이미지가 쌓여 노드 디스크가 차면 kubelet 이 디스크 압박(DiskPressure) 상태를 보고하고 파드를 축출한다. 상위 이벤트의 원인이 노드의 `/var/lib` 에 있는 경우가 흔하다.
- **설정은 손으로 고치지 않는다.** 한 대를 손으로 고치면 나머지와 달라진다. 설정 파일은 버전 관리하고 자동화 도구로 배포한다. 이 원칙이 231번 IaC 로 이어진다.

## 확인 문제

1. 4코어 서버의 load average 가 1분 6.0, 15분 1.0 이다. 무엇을 뜻하는가?
2. `free` 의 free 값이 매우 작은데 available 은 크다. 문제인가?
3. 디스크 용량은 50% 남았는데 "No space left on device" 가 난다. 무엇을 확인해야 하는가?
4. SIGTERM 대신 바로 SIGKILL 을 보내면 어떤 위험이 있는가?
5. 큰 로그 파일을 삭제했는데 디스크 사용량이 줄지 않는다. 원인과 확인 방법은?

### 풀이

1. 최근 1분 사이 부하가 코어 수를 넘어 급증했다. 실행 대기 또는 I/O 대기 태스크가 늘었다는 뜻이다. 15분 값이 낮으니 막 시작된 현상이다.
2. 아니다. 남는 메모리를 페이지 캐시로 쓰는 정상 동작이다. available 을 기준으로 판단한다.
3. inode 고갈(`df -i`). 작은 파일이 대량으로 쌓였을 가능성이 크다.
4. 프로그램이 정리 작업(버퍼 플러시, 연결 종료, 임시 파일 삭제)을 못 하고 죽는다. 데이터 손상이나 불완전한 상태가 남을 수 있다.
5. 프로세스가 그 파일을 아직 열고 있다. `/proc/<pid>/fd` 에서 `(deleted)` 링크를 찾거나 `lsof` 로 확인하고, 프로세스가 파일을 닫게 한다.

## 더 읽을거리 (References)

- Linux Foundation, [Filesystem Hierarchy Standard 3.0](https://refspecs.linuxfoundation.org/FHS_3.0/fhs/index.html)
- The Linux Kernel documentation, [The /proc Filesystem](https://docs.kernel.org/filesystems/proc.html)
- OpenBSD manual, [sshd_config(5)](https://man.openbsd.org/sshd_config)
- Linux man-pages (Debian), [signal(7)](https://manpages.debian.org/bookworm/manpages/signal.7.en.html)
