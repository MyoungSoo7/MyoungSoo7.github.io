---
layout: post
title: "*Linux Kernel 의 *본질* — *Process*, *Scheduler*, *Namespaces*, *Cgroups*, *BPF*"
date: 2026-06-22 19:00:00 +0900
categories: [linux, kernel, fundamentals, infrastructure]
tags: [linux, kernel, process, scheduler, cfs, eevdf, namespaces, cgroups, ebpf, container, docker, kubernetes, fundamentals]
---

> *"컨테이너 는 *가상 머신 의 *경량 버전 이 *아니다"* — Docker / K8s 시대 의 *가장 흔한 오해*. *컨테이너 는 *Linux 의 *기본 기능* 인 *Namespaces + Cgroups* 의 *조합* 이다. *별도 OS 없음, hypervisor 없음, 격리 도 *kernel level*.
>
> 그런데 *그 *Namespaces 는 *어떻게 격리* 하고, *Cgroups 는 *어떻게 자원 제한* 하고, *Scheduler 는 *수천 process 사이 *CPU 시간 을 어떻게 분배* 할까? *그 모든 것 의 *밑* 에 *Linux Kernel 의 *내부* 가 *작동* 한다.
>
> 이 글은 *기본기 시리즈 의 *Linux 편* — *Process / Thread 의 진실*, *CFS → EEVDF Scheduler*, *Namespaces 7 종*, *Cgroups v1 / v2*, *eBPF 의 *현대 적 위력* — 을 *infrastructure 엔지니어 의 *깊이* 로 정리한다.

내 *기본기 시리즈* :
- [*분산 시스템*](/2026/06/22/distributed-systems-cap-base-saga-2pc-cdc-consistency.html)
- [*JVM 본질*](/2026/06/22/jvm-internals-jit-gc-memory-model-escape-analysis.html)
- [*DB 본질*](/2026/06/22/database-internals-from-bplus-tree-to-mvcc-replication.html)
- [*오브젝트 서평*](/2026/06/22/object-book-review-cho-younghoo-object-oriented-design.html)

---

## TL;DR — *한 줄 결론*

> Linux Kernel 의 *컨테이너 시대 본질* 은 *6 가지* : (1) **Process** — task_struct 의 *PID + memory + fd + signal 의 묶음*, (2) **Thread = LWP** — *task_struct 가 *VM/fd 공유* 하는 *light-weight process*, (3) **CFS → EEVDF Scheduler** — *RBTree 기반 fair 분배 → JDK 6.6 부터 *EEVDF* 의 *latency 우선*, (4) **Namespaces 7 종** — PID/Mount/Network/IPC/UTS/User/Cgroup 의 *격리*, (5) **Cgroups v2** — *통합 hierarchy 의 *CPU/memory/io/pids* 제한, (6) **eBPF** — *kernel 안 의 *프로그래밍 가능 한 sandboxed VM* — *trace / network / security 의 *modern 표준*. *Docker / containerd / Kubernetes 의 *모든 추상화 가 *이 6 가지 의 위에서 *돈다*. *2026 년 의 *cilium, falco, pixie, parca* — 모두 *eBPF 위에서 *새로 태어남*.

---

## 1. *Process 의 *진실***

### 1.1 *task_struct — *모든 것이 이 한 구조체***

```c
// Linux kernel 의 task_struct (단순화)
struct task_struct {
    pid_t                   pid;            // Process ID
    pid_t                   tgid;           // Thread group ID (POSIX PID)
    struct mm_struct       *mm;             // 메모리 (가상 주소 공간)
    struct files_struct    *files;          // file descriptors
    struct fs_struct       *fs;             // current working directory, root
    struct signal_struct   *signal;         // signal handlers
    struct nsproxy         *nsproxy;        // ★ namespaces
    struct cgroup_subsys_state *cgroups;    // ★ cgroups
    struct sched_entity     se;             // scheduler entity
    int                     prio, nice;     // priority
    // ...
};
```

→ *Process 는 *task_struct 하나*. *PID 는 *그 안 의 한 필드*. *mm / files / signal* 같은 *모든 자원* 이 *task_struct 의 *포인터* 로 *연결*.

### 1.2 *Thread = task_struct 의 *공유*

> *Linux 에서 *thread 는 *별도 개념 아님*. *task_struct 가 *VM + files + signal* 을 *다른 task 와 공유* 하면 *그게 thread*.

```c
// fork() — *모든 것 복사* — 완전한 새 process
pid_t pid = fork();

// pthread_create() 또는 clone(...) — *공유 비트 선택*
pid_t lwp = clone(child_func, stack, CLONE_VM | CLONE_FILES | CLONE_SIGHAND, arg);
//                                    ↑ memory 공유  ↑ fd 공유   ↑ signal 공유
```

→ *Java Thread* 도 *내부적 으론 *clone() syscall*. *VM + files 공유* 의 *task*.

### 1.3 *Process Tree*

```bash
$ pstree -p
systemd(1)
  ├─sshd(1234)
  │   └─sshd(1567)──bash(1568)──vim(1789)
  └─docker(2000)
      └─containerd-shim(2010)
          └─java(2050)
              ├─{java}(2051)
              ├─{java}(2052)
              └─{java}(2053)
```

`{java}` 가 *thread 들* (LWP).

### 1.4 *Process 의 *상태*

```
TASK_RUNNING        — 실행 중 또는 *run queue 에 대기*
TASK_INTERRUPTIBLE  — 자원 대기 (signal 도 깨움)
TASK_UNINTERRUPTIBLE — 자원 대기 (signal 안 깨움, 디스크 I/O 등)
__TASK_STOPPED      — SIGSTOP
__TASK_TRACED       — debugger 추적
EXIT_ZOMBIE         — 종료 했지만 parent 가 아직 wait() 안 함
EXIT_DEAD           — 완전 종료
```

`uninterruptible` (D state) 의 *프로세스* 가 *오래 머무르면* — *디스크 hang* 의 *전형적 증상*. `top` 에서 *load average 폭증* 의 *원인 도 이것*.

---

## 2. *Scheduler — *CFS → EEVDF***

### 2.1 *왜 *Scheduler 인가*

> *CPU 1 개* 에 *프로세스 100 개*. *누가 *언제 *얼마나 실행*?

전통 Unix : *priority-based round-robin*. *PID 순서, time slice 고정*.
Linux *O(1) scheduler* (2.6, 2003) — *priority 별 *queue*.
**CFS (Completely Fair Scheduler)** (2.6.23, 2007) — *Ingo Molnar*. *RBTree 기반 fair 분배*.
**EEVDF (Earliest Eligible Virtual Deadline First)** (6.6, 2023) — *latency-aware*.

### 2.2 *CFS 의 *철학***

> *"이상적 multitasking CPU"* — N 개 프로세스 가 *각각 1/N 의 *CPU 시간* 받음.

핵심 자료구조 : **Red-Black Tree** — *각 task 의 *vruntime (virtual runtime)* 으로 *정렬*.

```
vruntime = 실제 실행 시간 / nice weight

다음 실행 = vruntime 가장 적은 task
```

→ *수행 적게 한 task 가 *먼저 실행*. *fairness 자동 보장*.

### 2.3 *Nice — *우선순위***

```
nice -20 : 가장 높은 우선순위 (root 만)
nice   0 : 기본
nice +19 : 가장 낮음

vruntime weight: nice 가 *낮을 수록* weight *높음* — *같은 시간 실행 해도 *vruntime 적게 증가* — *더 자주 실행*
```

### 2.4 *EEVDF (6.6+) — *latency 친화***

CFS 의 *문제* : *fairness 는 보장* 하지만 *latency 보장 약함*. *interactive task 가 *batch task 옆 에서 *답답해질 수 있음*.

EEVDF :
- 각 task 가 *deadline* 가짐 (요청한 *latency-nice* 기반).
- *"deadline 가장 가까운 *eligible task 가 *다음 실행*"*.
- *fairness + latency 둘 다 보장*.

→ *interactive workload (UI, low-latency server)* 가 *batch workload 영향 없이 *빠른 응답*.

### 2.5 *Scheduling Class*

```
SCHED_DEADLINE  ← Real-time, deadline 명시 (최우선)
SCHED_FIFO      ← Real-time, FIFO
SCHED_RR        ← Real-time, round-robin
SCHED_NORMAL    ← CFS/EEVDF (기본)
SCHED_BATCH     ← 큰 batch (낮은 우선순위)
SCHED_IDLE      ← idle 시 만 실행
```

→ *대부분 의 process 는 *NORMAL*. *Real-time 은 *audio / robotics / 산업 제어*.

### 2.6 *cfs_period_us / cfs_quota_us — *컨테이너 CPU limit***

Kubernetes `resources.limits.cpu: 500m` 의 *물리적 의미* :

```bash
# 100ms 마다 50ms 만 CPU 사용 — 즉 0.5 core
cfs_period_us: 100000
cfs_quota_us:   50000
```

→ *spike workload* 가 *50ms 다 소진* 하면 *throttle* — `nr_throttled` 메트릭 증가.

```bash
# CFS throttle 통계
cat /sys/fs/cgroup/cpu/<container>/cpu.stat
nr_periods 1234
nr_throttled 567        ← 56% 가 throttle!
throttled_time 89000000  ← ns 단위
```

→ *Kubernetes 의 *CPU throttling* 의 *진짜 원인* 식별 의 *evidence*.

---

## 3. *Namespaces — *컨테이너 의 *격리***

### 3.1 *7 종 namespace*

| Namespace | 격리 대상 | 도입 |
|---|---|---|
| **mnt** | mount point | 2.4.19 |
| **uts** | hostname, domainname | 2.6.19 |
| **ipc** | System V IPC, POSIX message queue | 2.6.19 |
| **pid** | process ID | 2.6.24 |
| **net** | network interface, route, port | 2.6.29 |
| **user** | UID/GID | 3.8 |
| **cgroup** | cgroup root | 4.6 |
| (**time**) | system clock (CLOCK_BOOTTIME) | 5.6 |

### 3.2 *PID namespace — *컨테이너 안 의 PID 1*

```bash
# Host
$ ps aux | grep java
1234  java -jar app.jar

# 같은 process — 컨테이너 안 에서
$ docker exec mycontainer ps aux
PID 1  java -jar app.jar       ← *컨테이너 안 에선 PID 1*
```

→ *PID 1 은 *컨테이너 안 의 의미*. *Host 의 *PID 1234 와 *별개*.

### 3.3 *Network namespace*

```bash
# 새 net namespace 생성
ip netns add mynet

# 그 안 에서 명령 실행
ip netns exec mynet ip addr   # lo 만 보임
ip netns exec mynet curl https://google.com   # 네트워크 없음

# veth pair 로 bridge 연결
ip link add veth0 type veth peer name veth1
ip link set veth1 netns mynet
```

→ *Docker bridge network* 의 *진짜 작동* — *각 container 가 *자기 net namespace* + *veth pair* 로 *bridge 와 연결*.

### 3.4 *Mount namespace — *각자 의 file system view*

```bash
# Host 의 /tmp
ls /tmp
# → host 의 /tmp 내용

# 컨테이너 안 의 /tmp
docker exec mycontainer ls /tmp
# → 컨테이너 의 /tmp (별개)
```

→ *각 컨테이너 가 *자기 의 *root filesystem (overlay)*. *Host 의 *파일 시스템* 을 *볼 수 없음*.

### 3.5 *User namespace — *rootless 컨테이너***

```bash
# 컨테이너 안 의 uid 0 (root)
# = host 의 uid 100000

unshare -U -r bash
$ id
uid=0(root) gid=0(root) ...

# 다른 터미널 (host)
$ ps aux | grep bash
100000  bash    ← *host 에선 일반 user*
```

→ *Podman, rootless Docker* 의 *기반*. *컨테이너 내 root 가 *host 의 root 아님*.

### 3.6 *unshare 명령 — *namespace 직접 조작*

```bash
# 자기 만 의 PID + UTS + Mount + Network namespace 생성
unshare --pid --uts --mount --net --fork bash
$ hostname newhost
$ ps aux   # *자기 만 보임*
```

→ Docker 가 *결국 unshare + chroot + cgroup 의 *조합* 일 뿐.

---

## 4. *Cgroups (Control Groups) — *자원 제한***

### 4.1 *v1 vs v2*

**v1** (2.6.24, 2008) — *각 controller 가 *별도 hierarchy*. 복잡.
**v2** (4.5, 2016 / RHEL 9 / Ubuntu 22.04+ 기본) — *통합 hierarchy*. 단순.

### 4.2 *v2 의 *controller*

| Controller | 제어 |
|---|---|
| **cpu** | CPU 시간 (weight, max) |
| **memory** | 메모리 (max, swap, oom_kill) |
| **io** | block I/O (weight, max bps/iops) |
| **pids** | process 수 |
| **rdma** | RDMA 자원 |
| **misc** | 기타 |

### 4.3 *Memory cgroup*

```bash
# Pod 의 cgroup 디렉토리
ls /sys/fs/cgroup/kubepods.slice/.../pod_id/

# Memory limit
cat memory.max
# 2147483648    ← 2GB

# 현재 사용
cat memory.current
# 1024000000    ← ~1GB

# OOM 통계
cat memory.events
# low 0
# high 0
# max 0
# oom 0
# oom_kill 1    ← OOM Kill 1 회
```

→ K8s 의 `resources.limits.memory: 2Gi` 가 *결국 *cgroup memory.max 설정*. *limit 초과 시 *kernel OOM killer* 가 *프로세스 죽임*.

### 4.4 *CPU cgroup*

```bash
# 절대 limit
cat cpu.max
# 100000 200000   ← 200ms / 200ms = 1 CPU 의 50% (즉 0.5 core)

# Weight (다른 cgroup 과 의 *상대 적 share*)
cat cpu.weight
# 100   ← default. 다른 cgroup 도 100 이면 *동등 분배*
```

→ K8s 의 `requests.cpu: 500m` = *cpu.weight 의 *상대 적 값*. `limits.cpu: 500m` = *cpu.max 의 *quota*.

### 4.5 *I/O cgroup*

```bash
# 특정 device 의 *최대 IOPS*
echo "8:0 rbps=10485760 wbps=5242880" > io.max
#       ↑ 8:0 = /dev/sda
#                  ↑ read 10MB/s    ↑ write 5MB/s
```

→ *noisy neighbor 의 *디스크 점유* 방지.

---

## 5. *eBPF — *kernel 안 의 *프로그래밍 가능 한 VM***

### 5.1 *eBPF 의 *혁신***

> *Extended Berkeley Packet Filter*. *kernel 안 에서 *안전 한 user code 실행*. *kernel 모듈 없이 *trace / 측정 / 정책 결정*.

**왜 *안전한가*** : *verifier* 가 *모든 eBPF 프로그램 의 *loop / memory access / 시스템 호출 합법성 검증 후 실행*. *crash 안 시킴*.

### 5.2 *eBPF 의 *6 가지 활용***

1. **Tracing** — *bcc, bpftrace, tracee* — *kernel / userspace event 추적*
2. **Networking** — *Cilium* (k8s CNI), *XDP* (high-speed packet processing)
3. **Security** — *Falco* (runtime threat detection), *Tetragon*
4. **Observability** — *Pixie* (auto-instrumentation), *Parca* (continuous profiling)
5. **LSM (Linux Security Module)** — kernel 보안 정책
6. **Storage** — *file system tracing, latency analysis*

### 5.3 *bpftrace — *간단 한 trace*

```bash
# 모든 process 의 open() syscall 추적
bpftrace -e 'tracepoint:syscalls:sys_enter_openat { printf("%s %s\n", comm, str(args->filename)); }'

# read latency histogram
bpftrace -e 'kprobe:vfs_read { @start[tid] = nsecs; }
             kretprobe:vfs_read /@start[tid]/ { @us = hist((nsecs - @start[tid]) / 1000); delete(@start[tid]); }'
```

→ *5 줄 코드 로 *kernel level 측정*. *수십 종 의 tool* 이 *bpftrace one-liner* 로 가능.

### 5.4 *Cilium — *eBPF 기반 CNI*

> *iptables 대신 *eBPF 로 *모든 K8s 네트워크 처리*.

장점:
- *iptables 의 *O(N) 룰 평가 대신 *O(1) hash map*
- *NetworkPolicy L7 (HTTP, gRPC) 지원*
- *Service Load Balancing* — kube-proxy 대체
- *Hubble* — *eBPF 기반 *실시간 흐름 가시화*

→ 내 [*K8s 로드밸런서 글*](/2026/06/21/kubernetes-loadbalancer-network-layers-l4-l7.html) 참조.

### 5.5 *eBPF 의 *2026 년*

- *kernel 5.x+ 가 *production 표준*
- *대부분 의 modern observability tool* 이 *eBPF based*
- *기존 *kernel module / strace / sysdig* 의 *진화*

---

## 6. *Process 의 *I/O — *5 가지 모델***

### 6.1 *Blocking I/O*

```c
read(fd, buf, size);   // 데이터 올 때까지 *thread block*
```

### 6.2 *Non-blocking I/O*

```c
fcntl(fd, F_SETFL, O_NONBLOCK);
n = read(fd, buf, size);
if (n == -1 && errno == EAGAIN) { /* 다음에 다시 */ }
```

### 6.3 *I/O Multiplexing — *select / poll / epoll*

내 [*논블로킹 I/O 서버 글*](/2026/06/19/non-blocking-io-server-deep-dive.html) 참조.

### 6.4 *Async I/O (AIO)*

```c
struct aiocb cb = { .aio_fildes = fd, .aio_buf = buf, ... };
aio_read(&cb);   // *비동기 시작* — kernel 이 *완료 시 signal* 또는 *callback*
```

POSIX AIO 는 *Linux 에서 *제한 적 (libaio)*. 그래서 *io_uring* 등장.

### 6.5 *io_uring — *진정한 async***

```c
struct io_uring ring;
io_uring_queue_init(32, &ring, 0);

struct io_uring_sqe *sqe = io_uring_get_sqe(&ring);
io_uring_prep_read(sqe, fd, buf, size, offset);
io_uring_submit(&ring);

// 나중에 결과 수확
struct io_uring_cqe *cqe;
io_uring_wait_cqe(&ring, &cqe);
```

→ *epoll 보다 *system call 횟수 ↓*. *fixed file / fixed buffer 로 *zero-copy 친화*. *대부분 의 syscall 비동기 가능*.

---

## 7. *Memory Management — *page, vmalloc, slab*

### 7.1 *Virtual Memory*

```
[Process A 의 가상 주소]   [Page Table]    [Physical RAM]
   0x00400000      ─────→   PTE          ─────→  0x1234_5000
   0x00800000      ─────→   PTE          ─────→  0x5678_9000
```

- *각 process 가 *자기 의 가상 주소 공간* (보통 *48-bit*)
- *Page Table* 이 *가상 → 물리 매핑*
- *MMU (CPU 하드웨어)* 가 *런타임 변환*

### 7.2 *Page — *기본 단위*

- *4 KB* 기본
- *Huge Page* — *2 MB* 또는 *1 GB* — *TLB miss 감소*

```bash
# Huge page 활성화 (Linux)
echo always > /sys/kernel/mm/transparent_hugepage/enabled
```

→ *JVM, PostgreSQL* 같은 *대용량 heap* 워크로드 에 효과.

### 7.3 *Memory 할당 의 *3 종*

| 메모리 | 용도 |
|---|---|
| **kmalloc** | kernel 일반 (작은 contiguous) |
| **vmalloc** | kernel large (가상 contiguous, 물리 흩어짐) |
| **slab/slob/slub** | kernel object cache (자주 할당/해제 객체) |

### 7.4 *Page Cache*

```bash
# 전체 page cache + buffer
free -h
#               total        used        free      shared  buff/cache   available
# Mem:           31Gi        12Gi        2.0Gi       1.0Gi        17Gi        18Gi
#                                                              ↑
#                                                          page cache + dirty buffers
```

→ *read syscall* 의 *95% 이상* 이 *page cache 에서 응답*. *디스크 IO 가 *조용히 *page cache 거치는* 이유.

### 7.5 *OOM Killer*

```
[메모리 부족 발생]
   ↓
[OOM Killer 발동]
   ↓
[oom_score 계산 — 각 process 의 *희생 가치*]
   ↓
[score 가장 높은 process *SIGKILL*]
```

`/proc/<pid>/oom_score` 또는 `oom_score_adj` 로 *우선순위 조정 가능*.

→ K8s 에서 *Pod 가 *OOMKilled* 되는 *진짜 메커니즘*. cgroup memory.max 초과 시 *cgroup OOM* — *프로세스 만 죽이고 *노드 는 *안 죽음*.

---

## 8. *디버깅 / 측정 도구*

### 8.1 *strace — *syscall trace***

```bash
strace -p <pid> -f -e trace=open,read,write
# fd 열고 / 읽고 / 쓰는 syscall 추적
```

### 8.2 *ltrace — *library call trace***

```bash
ltrace -p <pid>
# libc 의 *함수 호출 추적*
```

### 8.3 *perf — *kernel 의 *내장 profiler***

```bash
# CPU profile
perf record -g -p <pid> sleep 30
perf report

# cache miss / IPC
perf stat -e cycles,instructions,cache-misses ./mybinary
```

### 8.4 *bpftrace — *eBPF 기반 동적 trace***

위 5 장 참조.

### 8.5 */proc — *kernel 의 *file system 인터페이스***

```bash
/proc/<pid>/status      # 프로세스 메모리 / 상태
/proc/<pid>/stat        # scheduler / CPU 통계
/proc/<pid>/maps        # 메모리 매핑
/proc/<pid>/fd/         # 열린 fd
/proc/<pid>/ns/         # namespace
/proc/<pid>/cgroup      # cgroup 멤버십
/proc/loadavg           # 시스템 부하
/proc/meminfo           # 메모리 통계
/proc/interrupts        # 인터럽트 통계
```

→ *모든 시스템 도구* (top, ps, htop, free) 가 *내부적 으로 /proc 읽음*.

---

## 9. *체크리스트 — *Linux 본질 의 *실전***

내가 *production Linux 호스트* 운영 시 *확인* 하는 *12 가지*:

**관찰**:
1. `top` 의 *%wa (iowait)* 30%+ 시 *디스크 병목 의심*
2. `uptime` 의 *load average* > CPU 수 시 *과부하*
3. `vmstat 1` 의 *si / so* (swap in/out) > 0 시 *메모리 부족*
4. `iostat -x 1` 의 *%util* 95%+ 시 *디스크 포화*

**컨테이너**:
5. *Pod 가 *OOMKilled 시 *cgroup memory.max 초과* 인지 확인
6. *CPU throttling* (`nr_throttled` / `nr_periods` > 10%) 시 *limit 부족*
7. *컨테이너 안 의 *PID 1* 이 *zombie reap* 정상 처리 하는가 (`docker run --init`)

**자원 limit**:
8. `ulimit -n` (open files) 적절 한가 (java 앱 — 65535+)
9. `vm.max_map_count` 적절 한가 (Elasticsearch — 262144+)
10. `net.core.somaxconn` 적절 한가 (high-traffic — 65535)
11. *Transparent Huge Pages* — JVM/PG 에 권장, MongoDB/Redis 에는 비권장

**디버깅**:
12. *strace / perf / bpftrace 가 *production 에 설치* 되어 있는가

---

## 10. *결론 — *컨테이너 의 *kernel-level 진실***

> *Docker / Kubernetes 의 *모든 추상화 가 *Linux Kernel 의 *기본 기능 의 *조합*. *Namespaces 가 *격리*, *Cgroups 가 *제한*, *eBPF 가 *측정*, *Scheduler 가 *분배*.

오늘 정리한 *6 본질* :
1. **Process** — task_struct 의 *모든 자원 의 묶음*
2. **Thread = LWP** — VM/files/signal 공유 의 *clone()*
3. **Scheduler** — CFS → EEVDF 의 *fair + latency*
4. **Namespaces** — 7 종 의 *kernel level 격리*
5. **Cgroups v2** — *CPU / memory / I/O / pids* 제한
6. **eBPF** — *kernel 안 의 *프로그래밍 가능 한 VM*

> *컨테이너 가 *어떻게 격리 되고*, *Pod 가 *어떻게 자원 제한 되고*, *Cilium 이 *어떻게 iptables 대체 하는지* — *모든 것 의 *밑* 에 *이 6 가지 가 *돈다*.

*Kubernetes 의 *높은 추상화* 가 *작동 하는 동안* 은 *모름 도 OK*. *그러나 *Pod 가 *throttle 되거나, OOMKilled 되거나, *네트워크 가 *이상* 할 때 — *이 6 가지 의 *어느 것 이 *깨졌는지* *식별 의 능력 이 *시니어 의 *깊이*.

*2026 년 의 Linux 는 *7 년 전 의 Linux 가 아니다*. *eBPF, io_uring, EEVDF, cgroup v2, user namespace* — *모두 *production 표준*. *그 변화 의 *흐름* 이 *cloud native 의 *진짜 토대*.

---

## *참고*

- *Linux Kernel Development* (Robert Love, 3rd ed.).
- *Systems Performance: Enterprise and the Cloud* (Brendan Gregg).
- *Linux Performance Tools* — [brendangregg.com/linuxperf.html](https://www.brendangregg.com/linuxperf.html).
- *BPF Performance Tools* (Brendan Gregg).
- *Container Security* (Liz Rice).
- 자매편:
  - [*K8s 로드밸런서*](/2026/06/21/kubernetes-loadbalancer-network-layers-l4-l7.html)
  - [*K8s 컨테이너 오케스트레이션*](/2026/06/20/kubernetes-container-orchestration-what-we-actually-use.html)
  - [*Virtual Thread*](/2026/06/19/virtual-thread-and-carrier-thread-relationship.html)
