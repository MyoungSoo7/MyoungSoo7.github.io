---
layout: post
title: "[CS300 #116] 디스크 스케줄링과 SSD — 헤드를 덜 움직이던 시대에서 큐를 깊게 쓰는 시대로"
date: 2026-10-10 19:56:00 +0900
categories: [cs]
tags: [cs300, operating-systems, disk-scheduling, ssd, io-scheduler]
---

컴퓨터공학 300 주제 시리즈의 116번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

HDD 시절의 디스크 스케줄링은 기계 헤드의 이동 거리를 줄이려고 요청 순서를 바꾸는 기술(SSTF, SCAN, C-SCAN)이었고, 탐색 시간이 없는 SSD 시대에는 플래시의 "덮어쓸 수 없음"을 숨기는 FTL 과 여러 큐를 병렬로 채우는 다중 큐 블록 계층이 그 자리를 차지했다.

## 왜 필요한가

저장장치는 컴퓨터에서 가장 느린 부품이다. 같은 양의 데이터를 읽어도 순서와 방식에 따라 처리 시간이 몇 배, 몇십 배 차이 난다.

- HDD 는 원판이 돌고 팔이 움직인다. 멀리 떨어진 블록을 번갈아 읽으면 대부분의 시간이 팔을 옮기는 데 쓰인다.
- SSD 는 움직이는 부품이 없지만, 이미 쓴 자리를 바로 덮어쓰지 못한다. 쓰기 패턴이 나쁘면 내부에서 몇 배의 쓰기가 일어나 성능과 수명이 함께 떨어진다.

"DB 가 갑자기 느려졌다", "디스크 사용률 100% 인데 처리량은 낮다", "SSD 가 오래 쓰니 느려졌다" 같은 문제를 이해하려면 두 장치의 물리적 성질과 운영체제가 그것을 다루는 방식을 알아야 한다.

## 핵심 개념

### HDD 의 접근 시간

```
접근 시간 = 탐색 시간(seek)  +  회전 지연(rotational latency)  +  전송 시간(transfer)
           팔을 트랙으로 이동     원하는 섹터가 헤드 밑에 올 때까지   실제 읽기
```

임의 접근에서는 앞의 두 항목이 지배적이고, 둘 다 밀리초 단위다. 순차 접근에서는 탐색과 회전 지연이 거의 없어 전송 속도만 남는다. 그래서 HDD 에서 임의 I/O 와 순차 I/O 의 처리량 차이는 매우 크다.

### 고전 디스크 스케줄링 알고리즘

| 알고리즘 | 방법 | 특징 |
|---|---|---|
| FCFS | 도착 순서대로 | 공정하지만 헤드가 마구 오간다 |
| SSTF | 현재 위치에서 가장 가까운 요청부터 | 이동이 짧지만 먼 요청이 굶을 수 있다 |
| SCAN (엘리베이터) | 한 방향 끝까지 가며 처리, 반대로 돌아오며 처리 | 기아가 없다. 양 끝 요청이 손해 |
| C-SCAN | 한 방향으로만 처리하고 끝에서 처음으로 점프 | 대기 시간이 더 균일하다 |
| LOOK / C-LOOK | SCAN/C-SCAN 과 같되 마지막 요청 위치에서 돌아선다 | 쓸데없는 끝까지 이동을 없앤다 |

### SSD 의 내부 구조

NAND 플래시에는 HDD 에 없는 세 가지 제약이 있다.

1. **읽기·쓰기 단위는 페이지(보통 수 KB), 지우기 단위는 블록(페이지 수백 개 묶음)** 이다.
2. **이미 쓴 페이지에 덮어쓸 수 없다.** 블록 전체를 지운 뒤에야 다시 쓸 수 있다.
3. 블록마다 **지우기 횟수에 수명 한계**가 있다.

SSD 컨트롤러 안의 **FTL(Flash Translation Layer)** 이 이를 숨긴다.

```
운영체제가 보는 것:  논리 블록 주소(LBA) 7 번에 덮어쓰기
FTL 이 하는 일:      빈 물리 페이지 P 에 새 내용을 쓰고
                     매핑 표를 LBA 7 -> P 로 바꾸고
                     옛 페이지는 '무효'로 표시
나중에(GC):          무효 페이지가 많은 블록에서 유효 페이지만 다른 곳으로 옮기고
                     블록 전체를 지워 재사용
```

- **가비지 컬렉션(GC)**: 유효 페이지를 옮기는 내부 쓰기가 생긴다.
- **쓰기 증폭(write amplification)**: 호스트가 쓴 양보다 플래시에 실제로 쓴 양이 많아지는 비율이다. 빈 공간이 적을수록 GC 가 옮겨야 할 유효 페이지가 많아져 커진다.
- **웨어 레벨링**: 특정 블록만 닳지 않게 쓰기를 고르게 분산한다.
- **TRIM(discard)**: 운영체제가 "이 LBA 들은 이제 안 쓴다"고 알려 주는 명령이다. FTL 은 그 페이지를 옮길 필요가 없어지므로 GC 비용과 쓰기 증폭이 줄어든다.

### 리눅스 블록 계층과 I/O 스케줄러

SSD 는 탐색이 없으므로 "헤드 이동 최소화"는 의미가 없다. 대신 NVMe 같은 장치는 **여러 개의 하드웨어 큐**를 가지고 많은 요청을 동시에 처리한다. 리눅스는 이를 위해 **blk-mq(다중 큐 블록 계층)** 를 도입했다. CPU 별 소프트웨어 큐와 하드웨어 디스패치 큐를 두어 락 경합 없이 요청을 밀어 넣는다.

블록 장치별 I/O 스케줄러는 `/sys/block/<장치>/queue/scheduler` 에서 보고 바꿀 수 있고, 커널 문서에 따르면 선택지는 다음과 같다.

| 스케줄러 | 성격 |
|---|---|
| `none` | 재정렬 없이 그대로 보낸다. 빠른 NVMe 에 흔하다 |
| `mq-deadline` | 요청마다 마감 시각을 두어 기아를 막고, 읽기를 우선한다 |
| `bfq` | 프로세스별 공정한 대역폭 배분, 대화형 응답성 중시 |
| `kyber` | 목표 지연 시간을 기준으로 큐 깊이를 조절 |

## 직접 해 보기

교과서의 전형적 예제(실린더 0~199, 헤드 53, 요청 큐 98, 183, 37, 122, 14, 124, 65, 67)로 알고리즘별 헤드 이동 거리를 계산한다.

```python
REQ, HEAD, MAX = [98, 183, 37, 122, 14, 124, 65, 67], 53, 199

def total(path):
    return sum(abs(b - a) for a, b in zip(path, path[1:]))

def fcfs(h, req):
    return [h] + req

def sstf(h, req):
    path, left = [h], list(req)
    while left:
        nxt = min(left, key=lambda r: abs(r - path[-1]))   # 가장 가까운 요청
        path.append(nxt); left.remove(nxt)
    return path

def scan(h, req):            # 엘리베이터: 먼저 0 쪽으로 끝까지 갔다가 되돌아온다
    down = sorted([r for r in req if r <= h], reverse=True)
    up = sorted([r for r in req if r > h])
    return [h] + down + [0] + up

def look(h, req):            # SCAN 과 같되 끝까지 가지 않고 마지막 요청에서 돌아선다
    down = sorted([r for r in req if r <= h], reverse=True)
    up = sorted([r for r in req if r > h])
    return [h] + down + up

def cscan(h, req):           # 한 방향(위)으로만 처리, 끝에 닿으면 처음으로 점프
    up = sorted([r for r in req if r >= h])
    low = sorted([r for r in req if r < h])
    return [h] + up + [MAX, 0] + low

for name, fn in [("FCFS", fcfs), ("SSTF", sstf), ("SCAN", scan), ("LOOK", look), ("C-SCAN", cscan)]:
    p = fn(HEAD, REQ)
    print(f"{name:7s} 이동 {total(p):4d} 실린더  순서 {p}")
```

```
FCFS    이동  640 실린더  순서 [53, 98, 183, 37, 122, 14, 124, 65, 67]
SSTF    이동  236 실린더  순서 [53, 65, 67, 37, 14, 98, 122, 124, 183]
SCAN    이동  236 실린더  순서 [53, 37, 14, 0, 65, 67, 98, 122, 124, 183]
LOOK    이동  208 실린더  순서 [53, 37, 14, 65, 67, 98, 122, 124, 183]
C-SCAN  이동  382 실린더  순서 [53, 65, 67, 98, 122, 124, 183, 199, 0, 14, 37]
```

FCFS 대비 SSTF·SCAN 은 이동 거리를 3분의 1 남짓으로 줄인다. C-SCAN 의 382 에는 199 에서 0 으로 돌아가는 이동(199)이 포함되어 있다. 교재에 따라 이 복귀 이동을 빼고 세기도 한다. C-SCAN 은 총 이동은 길지만 어느 위치의 요청이든 기다리는 시간이 고르다.

리눅스 장비라면 각 장치가 회전형인지와 현재 스케줄러를 sysfs 에서 읽을 수 있다.

```python
import glob, os
def rd(q, f):
    try: return open(os.path.join(q, f)).read().strip()
    except OSError: return "-"
for q in sorted(glob.glob("/sys/block/*/queue")):
    dev = q.split("/")[3]
    if dev.startswith(("loop", "ram", "zram")): continue
    print(f"{dev:10s} rotational={rd(q,'rotational')}  scheduler={rd(q,'scheduler')}")
```

SSD 를 단 노트북에서는 `sda  rotational=0  scheduler=none [mq-deadline]` 같은 줄이 나온다. 대괄호가 현재 선택이다. 장치 매퍼(dm-) 같은 가상 장치는 스케줄러 파일이 없을 수 있다.

## 현업에서는

- **`iostat -x` 읽기**: `r_await`/`w_await`(평균 대기 포함 지연), `aqu-sz`(평균 큐 길이), `%util` 을 본다. 병렬 처리 능력이 큰 SSD·NVMe 에서는 `%util` 100% 가 곧 포화를 뜻하지 않는다는 점이 `iostat` 매뉴얼에도 적혀 있다. 지연 시간과 큐 길이를 함께 봐야 한다.
- **정기 TRIM**: 많은 배포판이 주간 `fstrim.timer` 를 제공한다. 마운트 옵션 `discard` 로 매 삭제마다 TRIM 을 보내는 방식과 주기적 `fstrim` 중 무엇이 나은지는 장치와 워크로드에 따라 다르다.
- **빈 공간이 성능이다**: SSD 를 거의 가득 채워 쓰면 GC 가 옮길 유효 페이지가 많아져 쓰기 지연이 튄다. DB 볼륨은 여유를 두고, 지속 쓰기 성능은 장치 사양의 "정상 상태(steady state)" 수치를 기준으로 본다.
- **클러스터 스토리지**: k3s 의 기본 local-path 프로비저너는 노드 로컬 디스크 디렉터리를 쓰므로, etcd(또는 내장 DB)와 DB 파드가 같은 디스크를 쓰면 서로의 fsync 지연에 영향을 준다. 중요한 상태 저장소는 디스크를 분리하는 것이 안전하다.

## 확인 문제

1. HDD 접근 시간의 세 구성 요소는?
2. SSTF 의 장점과 단점은?
3. SSD 가 같은 위치에 "덮어쓰기"를 요청받았을 때 내부에서 실제로 일어나는 일은?
4. 쓰기 증폭이 무엇이고, TRIM 이 그것을 줄이는 원리는?
5. 빠른 NVMe SSD 에서 I/O 스케줄러로 `none` 을 흔히 쓰는 이유는?

### 풀이

1. 탐색 시간, 회전 지연, 전송 시간.
2. 헤드 이동 거리가 짧아 처리량이 좋지만, 현재 위치에서 먼 요청이 계속 밀려 기아에 빠질 수 있다.
3. FTL 이 빈 물리 페이지에 새 내용을 쓰고, 논리→물리 매핑을 갱신하며, 옛 페이지를 무효로 표시한다. 무효 페이지는 나중에 가비지 컬렉션으로 블록 단위로 지워진다.
4. 호스트가 쓴 양 대비 플래시에 실제로 쓴 양의 비율이 1 보다 커지는 현상이다. TRIM 으로 더는 쓰지 않는 페이지를 알려 주면 GC 가 그 페이지를 옮기지 않아도 되므로 내부 쓰기가 줄어든다.
5. 탐색 시간이 없어 재정렬 이득이 거의 없고, 장치가 여러 큐로 많은 요청을 병렬 처리하므로 소프트웨어 스케줄링이 오히려 CPU 비용과 지연만 더할 수 있기 때문이다.

## 더 읽을거리 (References)

- OSTEP, [Hard Disk Drives (PDF)](https://pages.cs.wisc.edu/~remzi/OSTEP/file-disks.pdf), [Flash-based SSDs (PDF)](https://pages.cs.wisc.edu/~remzi/OSTEP/file-ssd.pdf)
- Linux kernel documentation, [Multi-Queue Block IO Queueing Mechanism (blk-mq)](https://docs.kernel.org/block/blk-mq.html)
- Linux kernel documentation, [Switching Scheduler](https://docs.kernel.org/block/switching-sched.html)
- Linux man-pages, [fstrim(8)](https://manpages.debian.org/bookworm/util-linux/fstrim.8.en.html), [iostat(1)](https://manpages.debian.org/bookworm/sysstat/iostat.1.en.html)
