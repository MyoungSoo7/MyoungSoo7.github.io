---
layout: post
title: "[CS300 #119] cgroup 과 네임스페이스 — 컨테이너를 이루는 두 개의 커널 기능"
date: 2026-10-10 19:59:00 +0900
categories: [cs]
tags: [cs300, operating-systems, cgroups, namespaces, containers]
---

컴퓨터공학 300 주제 시리즈의 119번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

네임스페이스는 프로세스가 **무엇을 볼 수 있는지**(PID, 네트워크, 마운트, 호스트 이름 등)를 나누고, cgroup 은 프로세스 묶음이 **얼마나 쓸 수 있는지**(CPU, 메모리, I/O, 프로세스 수)를 제한·계량하며, 컨테이너는 이 두 기능으로 격리하고 제한한 평범한 리눅스 프로세스다.

## 왜 필요한가

한 서버에서 여러 서비스를 돌리면 두 가지 문제가 생긴다.

- **간섭**: 한 서비스의 메모리 누수가 서버 전체를 OOM 으로 몰고, 배치 작업 하나가 CPU 를 독차지한다.
- **충돌**: 두 서비스가 같은 포트를 쓰려 하고, 서로 다른 버전의 라이브러리가 필요하고, 한 서비스가 다른 서비스의 프로세스를 `kill` 할 수 있다.

가상 머신으로 나누면 해결되지만 무겁다. 리눅스는 커널 하나를 공유하면서 프로세스 단위로 **보이는 세계**와 **쓸 수 있는 양**을 나누는 기능을 제공한다. 이것이 네임스페이스와 cgroup 이고, Docker, containerd, 쿠버네티스가 모두 이 위에서 동작한다.

쿠버네티스 파드의 `resources.limits.memory` 가 실제로 무엇을 하는지, 컨테이너 안의 `ps` 에 프로세스가 몇 개 안 보이는 이유, `OOMKilled` 와 CPU 스로틀링이 어디서 오는지가 모두 이 글의 내용이다.

## 핵심 개념

### 네임스페이스: 보이는 것을 나눈다

`namespaces(7)` 매뉴얼이 정리한 리눅스 네임스페이스 종류다.

| 네임스페이스 | 격리하는 것 | 컨테이너에서 보이는 효과 |
|---|---|---|
| Mount | 마운트 지점 목록 | 자기만의 루트 파일 시스템 |
| UTS | 호스트 이름, 도메인 이름 | 컨테이너마다 다른 hostname |
| IPC | System V IPC, POSIX 메시지 큐 | 공유 메모리 분리 |
| PID | 프로세스 ID 번호 공간 | 컨테이너 안의 첫 프로세스가 PID 1 |
| Network | 네트워크 장치, IP, 라우팅, 포트 | 컨테이너마다 독립된 `eth0` 과 포트 |
| User | UID/GID 매핑, 권한(capability) | 안에서는 root, 밖에서는 일반 사용자 |
| Cgroup | cgroup 계층의 루트 위치 | 자기 cgroup 이 루트처럼 보임 |
| Time | 부팅 시각·monotonic 시계 오프셋 | 체크포인트/복원 용도 |

관련 시스템 콜은 세 개다. `clone()` 은 새 프로세스를 새 네임스페이스에서 시작하고, `unshare()` 는 현재 프로세스를 새 네임스페이스로 옮기고, `setns()` 는 기존 네임스페이스에 들어간다. `kubectl exec` 나 `nsenter` 가 컨테이너 "안으로 들어가는" 것은 `setns()` 다.

각 프로세스의 소속은 `/proc/PID/ns/` 아래의 링크로 보인다. 링크가 가리키는 번호가 같으면 같은 네임스페이스다.

### cgroup: 쓸 수 있는 양을 나눈다

cgroup(control group)은 프로세스들을 계층 구조의 그룹으로 묶고, 그룹마다 자원 컨트롤러를 붙인다. 현재 주류는 단일 계층의 **cgroup v2** 이고, `/sys/fs/cgroup` 아래 디렉터리 트리로 드러난다. 디렉터리를 만들면 그룹이 생기고, 파일에 값을 쓰면 설정이 바뀐다.

| 컨트롤러 | 대표 파일 | 의미 |
|---|---|---|
| memory | `memory.max` | 넘으면 회수 후 OOM kill |
| | `memory.high` | 넘으면 강하게 회수·스로틀(하드 리밋 이전의 완충) |
| | `memory.current` | 현재 사용량(페이지 캐시 포함) |
| cpu | `cpu.max` | `$MAX $PERIOD` 형식. 기간마다 쓸 수 있는 CPU 시간. 기본 `max 100000` |
| | `cpu.weight` | 경합 시 상대 비율(기본 100) |
| io | `io.max`, `io.weight` | 장치별 대역폭·IOPS 상한과 비율 |
| pids | `pids.max` | 만들 수 있는 프로세스·스레드 수(포크 폭탄 방지) |

cgroup 은 제한만 하는 것이 아니라 **계량**도 한다. `memory.stat`, `cpu.stat` 의 수치가 컨테이너 모니터링 지표의 원천이다. `cpu.stat` 의 `nr_throttled`, `throttled_usec` 는 CPU 쿼터에 걸린 횟수와 시간이다.

### 컨테이너 = 프로세스 + 네임스페이스 + cgroup + α

```
컨테이너 런타임(runc 등)이 하는 일, 아주 단순화하면

clone(CLONE_NEWPID | CLONE_NEWNS | CLONE_NEWNET | CLONE_NEWUTS | CLONE_NEWIPC ...)
   -> 자식 프로세스를 /sys/fs/cgroup/.../<컨테이너> 에 넣는다 (memory.max, cpu.max 설정)
   -> 이미지 층을 overlayfs 로 겹쳐 마운트하고 pivot_root 로 루트를 바꾼다
   -> capability 를 줄이고 seccomp 필터를 건다
   -> execve("/app/server")
```

네임스페이스와 cgroup 외에 capability 축소, seccomp, AppArmor/SELinux 같은 보안 장치가 함께 쓰인다. 그래도 커널은 **공유**한다는 사실이 컨테이너 격리의 한계다.

## 직접 해 보기

현재 프로세스가 속한 cgroup 과 네임스페이스를 읽고, 특권 없이 user 네임스페이스를 만들어 본다.

```python
import os

# 1) 내가 속한 cgroup 과 그 한도 (cgroup v2: /proc/self/cgroup 이 "0::<경로>" 한 줄)
rel = open("/proc/self/cgroup").read().strip().split("::", 1)[1]
print("cgroup 경로:", rel)
base = "/sys/fs/cgroup"
print("루트에서 켜진 컨트롤러:", open(f"{base}/cgroup.controllers").read().split())
for f in ("memory.max", "memory.current", "pids.max", "cpu.max"):
    p = os.path.join(base + rel, f)
    print(f"  {f:15s}", open(p).read().strip() if os.path.exists(p) else "(이 단계에서는 컨트롤러 미활성)")

# 2) 내가 속한 네임스페이스: 링크 안의 번호가 같으면 같은 네임스페이스다
for ns in ("pid", "net", "mnt", "uts", "user", "cgroup"):
    print(f"  ns/{ns:7s}", os.readlink(f"/proc/self/ns/{ns}"))

# 3) 특권 없이 user 네임스페이스를 만들어 그 안에서 root(uid 0) 되어 보기
import sys; sys.stdout.flush()
uid, gid = os.getuid(), os.getgid()
pid = os.fork()
if pid == 0:
    try:
        os.unshare(os.CLONE_NEWUSER)                       # Python 3.12+
        open("/proc/self/setgroups", "w").write("deny")
        open("/proc/self/uid_map", "w").write(f"0 {uid} 1")   # 안의 0 = 밖의 내 uid
        open("/proc/self/gid_map", "w").write(f"0 {gid} 1")
        print("[자식] 새 user ns:", os.readlink("/proc/self/ns/user"), " uid:", os.getuid(), flush=True)
    except OSError as e:
        print("[자식] 실패:", e, "(배포판 보안 정책이 비특권 user 네임스페이스를 막았을 수 있다)", flush=True)
    os._exit(0)
os.waitpid(pid, 0)
print("[부모] uid:", os.getuid())
```

우분투 계열 노트북의 tmux 세션에서 돌린 결과다(세션 ID 는 가렸다).

```
cgroup 경로: /user.slice/user-1000.slice/user@1000.service/app.slice/session-XXXX.scope
루트에서 켜진 컨트롤러: ['cpuset', 'cpu', 'io', 'memory', 'hugetlb', 'pids', 'rdma', 'misc']
  memory.max      max
  memory.current  1080987648
  pids.max        38199
  cpu.max         (이 단계에서는 컨트롤러 미활성)
  ns/pid     pid:[4026531836]
  ns/net     net:[4026531840]
  ns/mnt     mnt:[4026531841]
  ns/uts     uts:[4026531838]
  ns/user    user:[4026531837]
  ns/cgroup  cgroup:[4026531835]
[자식] 실패: [Errno 13] Permission denied: '/proc/self/setgroups' (배포판 보안 정책이 비특권 user 네임스페이스를 막았을 수 있다)
[부모] uid: 1000
```

읽을거리가 많다.

- cgroup 경로에서 systemd 가 프로세스를 `user.slice` → 사용자 → 서비스 → scope 로 계층화해 둔 것이 보인다. 이 그룹은 메모리 상한이 없고(`max`), `cpu` 컨트롤러는 이 단계까지 내려 보내지 않아 `cpu.max` 파일이 없다. cgroup v2 에서는 부모가 `cgroup.subtree_control` 로 켠 컨트롤러만 자식에서 쓸 수 있다.
- 네임스페이스 번호는 호스트의 기본값들이다. 컨테이너 안에서 같은 코드를 돌리면 pid, net, mnt, uts 번호가 달라진다.
- 마지막 실험은 이 장비에서 실패했다. 이 장비의 `kernel.apparmor_restrict_unprivileged_userns` 값이 1 이어서, AppArmor 가 비특권 프로세스의 user 네임스페이스 권한을 제한한다. 이런 제한이 없는 시스템에서는 `user_namespaces(7)` 에 설명된 대로 매핑이 성공하고 자식 안의 `getuid()` 가 0 을 돌려준다. 밖에서 보면 여전히 uid 1000 인 일반 프로세스다. rootless 컨테이너가 이 원리로 동작하며, 그래서 보안 정책이 이 기능을 따로 통제한다.

## 현업에서는

- **파드 limit 이 곧 cgroup 파일이다**: 쿠버네티스 문서에 따르면 cgroup v2 지원은 v1.25 에서 안정화되었다. 컨테이너의 `limits.memory` 는 `memory.max` 로, `limits.cpu` 는 `cpu.max` 의 쿼터로, `requests.cpu` 는 `cpu.weight` 로 변환된다. `OOMKilled` 는 `memory.max` 를 넘어 cgroup 안에서 OOM kill 이 난 것이다.
- **CPU 스로틀링 확인**: 응답 지연이 주기적으로 튀는데 CPU 사용률은 limit 아래라면, 짧은 순간에 쿼터를 다 써서 남은 기간을 기다리는 것일 수 있다. 컨테이너 cgroup 의 `cpu.stat` 에서 `nr_throttled` 가 늘고 있는지 본다. 지연에 민감한 서비스는 CPU limit 을 넉넉히 하거나 두지 않는 선택도 한다.
- **`memory.current` 에는 페이지 캐시가 들어 있다**: 로그를 많이 쓰는 컨테이너의 메모리 사용량이 계속 오르는 것처럼 보이는 이유다. 회수 가능한 캐시를 뺀 워킹 셋 지표를 함께 본다.
- **노드 디버깅**: 노드에서 특정 컨테이너의 네트워크를 보려면 그 프로세스의 네트워크 네임스페이스에 들어가 `ip addr`, `ss` 를 실행한다(`nsenter -t PID -n`). 컨테이너 이미지에 도구가 없어도 호스트의 도구로 들여다볼 수 있다.

## 확인 문제

1. 네임스페이스와 cgroup 의 역할 차이를 한 문장으로 설명하라.
2. 컨테이너 안의 애플리케이션이 PID 1 로 보이는데 호스트에서는 PID 가 다른 이유는?
3. cgroup v2 의 `cpu.max` 값이 `50000 100000` 이면 무엇을 뜻하는가?
4. 컨테이너가 `OOMKilled` 로 재시작되었다. 커널 수준에서 무슨 일이 일어났는가?
5. 컨테이너가 가상 머신보다 격리가 약하다고 말하는 근본 이유는?

### 풀이

1. 네임스페이스는 프로세스가 볼 수 있는 시스템 자원의 범위를 나누고, cgroup 은 프로세스 그룹이 쓸 수 있는 자원의 양을 제한·계량한다.
2. 컨테이너가 새 PID 네임스페이스에서 시작해 그 안의 번호 공간에서는 첫 프로세스가 1 이지만, 호스트(부모) PID 네임스페이스에서는 별도의 번호를 가지기 때문이다.
3. 100,000µs(100ms) 기간마다 50,000µs 까지 CPU 를 쓸 수 있다. 즉 평균 0.5 코어로 제한된다.
4. 컨테이너 cgroup 의 메모리 사용량이 `memory.max` 에 도달했고, 회수로도 공간을 만들지 못하자 커널이 그 cgroup 안의 프로세스를 OOM killer 로 종료했다.
5. 모든 컨테이너가 호스트 커널 하나를 공유하므로, 커널 취약점이나 잘못된 커널 설정이 모든 컨테이너에 영향을 줄 수 있기 때문이다.

## 더 읽을거리 (References)

- Linux man-pages, [namespaces(7)](https://manpages.debian.org/bookworm/manpages/namespaces.7.en.html), [user_namespaces(7)](https://manpages.debian.org/bookworm/manpages/user_namespaces.7.en.html)
- Linux kernel documentation, [Control Group v2](https://docs.kernel.org/admin-guide/cgroup-v2.html)
- Kubernetes 문서, [About cgroup v2](https://kubernetes.io/docs/concepts/architecture/cgroups/)
- Kubernetes 문서, [Resource Management for Pods and Containers](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/)
