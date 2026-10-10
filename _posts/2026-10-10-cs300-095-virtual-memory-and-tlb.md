---
layout: post
title: "[CS300 #095] 가상 메모리와 TLB — 모든 프로세스가 자기만의 주소 공간을 갖는 방법"
date: 2026-10-10 19:35:00 +0900
categories: [cs]
tags: [cs300, computer-architecture, virtual-memory, tlb, page-table]
---

컴퓨터공학 300 주제 시리즈의 095번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

가상 메모리는 프로그램이 쓰는 주소(가상 주소)와 실제 RAM 주소(물리 주소)를 페이지 단위로 분리하고, 그 대응표(페이지 테이블)를 하드웨어(MMU)가 매 접근마다 참조하게 하는 구조다. TLB 는 이 변환 결과를 담아 두는 작은 캐시로, 변환 비용을 거의 0 으로 만든다.

## 왜 필요한가

프로세스 두 개가 똑같이 `0x400000` 번지를 쓰는데 서로 덮어쓰지 않는다. 노트북 RAM 보다 큰 파일을 `mmap` 해도 잘 열린다. `malloc` 으로 1GB 를 받아도 실제 메모리 사용량은 거의 그대로다. 컨테이너의 메모리 한도를 넘으면 OOM 으로 죽는다. 모두 가상 메모리 때문에 일어나는 일이다.

운영체제 쪽 이야기(페이지 교체, 스와핑)는 6부에서 자세히 다룬다. 이 글은 하드웨어 쪽, 곧 **주소 하나가 매번 어떻게 변환되는가** 와 그 비용을 줄이는 TLB 에 집중한다.

## 핵심 개념

### 가상 메모리가 주는 세 가지

1. **격리**: 프로세스마다 자기 페이지 테이블을 갖는다. 다른 프로세스의 메모리를 가리킬 방법 자체가 없다.
2. **보호**: 페이지마다 읽기·쓰기·실행·사용자 접근 권한 비트를 둔다. 권한을 어기면 하드웨어가 예외를 일으킨다(#086 의 NX 비트가 여기 있다).
3. **추상화**: 물리 메모리가 흩어져 있어도 프로세스에게는 연속된 큰 주소 공간으로 보인다. 아직 쓰지 않은 페이지는 실제 메모리를 차지하지 않는다.

### 페이지와 주소 변환

메모리를 고정 크기 페이지(x86-64 와 대부분의 ARM 리눅스에서 기본 4KB)로 나눈다. 4KB = 2^12 이므로 가상 주소의 하위 12비트는 페이지 안 오프셋이고 나머지가 가상 페이지 번호(VPN)다.

```
가상 주소   [   가상 페이지 번호(VPN)   | 오프셋 12비트 ]
                     │ 페이지 테이블 조회             │ 그대로
                     ▼                               ▼
물리 주소   [   물리 프레임 번호(PFN)   | 오프셋 12비트 ]
```

페이지 테이블 항목(PTE)에는 프레임 번호와 함께 존재(present), 쓰기 가능, 사용자 접근, 실행 금지, 접근됨(accessed), 수정됨(dirty) 같은 비트가 들어 있다.

### 다단계 페이지 테이블

64비트 주소 공간 전체를 한 장의 표로 만들면 너무 크다. 그래서 트리로 만든다. x86-64 의 일반적인 구성은 48비트 가상 주소를 4단계로 나눈다(지원하는 CPU 와 커널에서는 5단계, 57비트도 가능).

```
48비트 가상 주소
[ L4 9비트 | L3 9비트 | L2 9비트 | L1 9비트 | 오프셋 12비트 ]
     │          │          │          │
  CR3 →표 ──► 표 ──────► 표 ──────► 표 ──► 물리 프레임
```

쓰지 않는 구간의 하위 표는 아예 만들지 않으므로 메모리가 절약된다. 대신 **변환 한 번에 메모리 접근이 최대 4번** 더 필요하다. 하드웨어가 이 표를 따라 내려가는 것을 페이지 테이블 워크라고 한다.

### TLB: 변환 결과의 캐시

모든 메모리 접근마다 페이지 테이블을 4번 읽는다면, 캐시를 무시할 때 메모리 접근 횟수가 최대 5배가 된다. 그래서 MMU 안에 최근 변환 결과(VPN → PFN + 권한)를 담는 작은 캐시, **TLB(Translation Lookaside Buffer)** 를 둔다.

```
가상 주소 ─► TLB 조회 ─ 적중 ──────────────────────► 물리 주소 (거의 공짜)
                  └─ 미스 ─► 페이지 테이블 워크 ─► TLB 채움 ─► 물리 주소
                                 └─ PTE 없음 ─► 페이지 폴트 → OS 처리
```

TLB 는 항목 수가 수십~수천 개로 작다. 4KB 페이지 기준으로 TLB 가 덮을 수 있는 메모리 범위(TLB reach)는 "항목 수 × 4KB" 라 수 MB 정도에 그친다. 작업 집합이 이보다 크고 접근이 흩어져 있으면 TLB 미스가 잦아진다. 정확한 TLB 크기와 단계 수는 CPU 마다 다르다.

### 페이지 폴트

PTE 가 없거나 권한이 맞지 않으면 CPU 는 페이지 폴트 예외를 일으키고 OS 에게 넘긴다.

| 종류 | 상황 | OS 의 처리 |
|---|---|---|
| 마이너 폴트 | 처음 쓰는 익명 페이지, 이미 페이지 캐시에 있는 파일 페이지 | 프레임을 할당·연결만 하면 됨. 빠름 |
| 메이저 폴트 | 디스크(스왑, 파일)에서 읽어와야 함 | I/O 대기. 느림 |
| 잘못된 접근 | 매핑 없는 주소, 권한 위반 | 프로세스에 SIGSEGV |

리눅스는 메모리를 요청받아도 실제로 쓰기 전까지 물리 프레임을 주지 않는다(지연 할당, demand paging). 아래 실험에서 확인한다.

### 큰 페이지 (Huge Page)

페이지를 2MB 나 1GB 로 키우면 TLB 항목 하나가 덮는 범위가 512배, 262,144배가 된다. TLB 미스가 줄고 페이지 테이블 워크도 짧아진다. 리눅스는 미리 예약하는 HugeTLB 와, 커널이 자동으로 묶어 주는 투명 큰 페이지(THP) 두 방식을 제공한다. 대신 메모리 낭비(내부 단편화)와 할당 지연이 생길 수 있어 워크로드에 따라 득실이 갈린다.

### 문맥 교환과 TLB

프로세스가 바뀌면 페이지 테이블이 바뀌므로 TLB 의 항목이 쓸모없어진다. 모두 비우면(flush) 새 프로세스가 미스부터 시작한다. 현대 CPU 는 TLB 항목에 주소 공간 식별자(x86 의 PCID, ARM 의 ASID)를 붙여 비우지 않고도 구분한다.

## 직접 해 보기

### 1. 지연 할당 눈으로 보기

1GB 를 매핑하고, 그중 200MB 에만 페이지마다 1바이트씩 쓴다. 리눅스에서 python3 로 확인했다.

```python
import mmap

def rss_mb():
    with open("/proc/self/status") as f:
        for line in f:
            if line.startswith("VmRSS"):
                return int(line.split()[1]) // 1024

print("page size:", mmap.PAGESIZE)
print("start      RSS", rss_mb(), "MB")
m = mmap.mmap(-1, 1 << 30)                 # 가상 주소 1GB 예약 (익명 매핑)
print("mmap 1GB   RSS", rss_mb(), "MB")
for off in range(0, 200 << 20, mmap.PAGESIZE):
    m[off] = 1                             # 200MB 구간의 페이지마다 1바이트씩 쓰기
print("touch 200MB RSS", rss_mb(), "MB")
m.close()
print("close      RSS", rss_mb(), "MB")
```

출력:

```
page size: 4096
start      RSS 10 MB
mmap 1GB   RSS 10 MB
touch 200MB RSS 210 MB
close      RSS 10 MB
```

1GB 를 받았을 때 RSS(실제 상주 메모리)는 그대로다. 가상 주소 범위만 예약됐기 때문이다. 페이지마다 1바이트씩 쓰자 그 페이지들에 마이너 폴트가 나며 물리 프레임이 붙어 정확히 200MB 가 늘었다. 1바이트를 써도 4KB 가 통째로 할당된다.

### 2. 주소 변환과 TLB 흉내

```python
from collections import OrderedDict
PAGE = 4096

class MMU:
    def __init__(self, page_table, tlb_size=4):
        self.pt = page_table                  # 가상 페이지 번호 -> 물리 프레임 번호
        self.tlb = OrderedDict()
        self.tlb_size = tlb_size
        self.hit = self.miss = self.fault = 0

    def translate(self, vaddr):
        vpn, off = divmod(vaddr, PAGE)        # 상위 비트 = 페이지 번호, 하위 12비트 = 오프셋
        if vpn in self.tlb:
            self.hit += 1; self.tlb.move_to_end(vpn)
        else:
            self.miss += 1
            if vpn not in self.pt:            # 페이지 테이블에도 없다 -> 페이지 폴트
                self.fault += 1
                self.pt[vpn] = 100 + len(self.pt)   # OS 가 프레임을 할당했다고 가정
            self.tlb[vpn] = self.pt[vpn]
            if len(self.tlb) > self.tlb_size:
                self.tlb.popitem(last=False)
        return self.tlb[vpn] * PAGE + off

mmu = MMU({0: 7, 1: 3})
print(hex(mmu.translate(0x0123)), hex(mmu.translate(0x1abc)), hex(mmu.translate(0x5000)))

seq = MMU({}); [seq.translate(i * 8) for i in range(4096)]
jmp = MMU({}); [jmp.translate((i % 64) * PAGE) for i in range(4096)]
print("sequential: hit", seq.hit, "miss", seq.miss, "fault", seq.fault)
print("page-jump : hit", jmp.hit, "miss", jmp.miss, "fault", jmp.fault)
```

출력:

```
0x7123 0x3abc 0x66000
sequential: hit 4088 miss 8 fault 8
page-jump : hit 0 miss 4096 fault 64
```

오프셋 `0x123`, `0xabc` 는 변환 후에도 그대로이고 페이지 번호만 바뀐다. 8바이트씩 순차로 읽으면 한 페이지에서 512번 적중하므로 TLB 미스는 페이지 수(8)만큼만 난다. 매번 다른 페이지로 건너뛰는 접근은 TLB 4칸으로 64개 페이지를 감당하지 못해 전부 미스다. 앞 글(#092)의 포인터 추적 실험에서 큰 크기일수록 느려진 이유 중 하나가 이것이다.

## 현업에서는

- **RSS 와 VSZ**: `ps`, `top` 의 VSZ(가상 크기)는 크게 잡혀도 문제가 아니다. 실제 메모리 압박은 RSS 와 그중 익명 메모리 비중으로 본다. 자바·Go 런타임은 큰 가상 영역을 미리 잡아 두는 경우가 많아 VSZ 만 보고 놀라는 일이 흔하다.
- **컨테이너 메모리 한도**: 쿠버네티스 메모리 limit 은 cgroup 이 이 물리 페이지 사용량을 세서 강제한다. 가상 할당은 성공했는데 실제로 써 내려가다 한도를 넘는 순간 OOM 킬이 난다. "할당은 됐는데 왜 죽지?" 의 답이다.
- **큰 페이지 설정**: 대용량 메모리를 쓰는 DB·JVM 은 큰 페이지로 TLB 미스를 줄이기도 한다. 반대로 일부 DB 문서는 THP 의 지연 스파이크를 이유로 끄기를 권하기도 한다. 쿠버네티스는 `hugepages-2Mi` 같은 리소스 이름으로 미리 예약된 큰 페이지를 파드에 할당할 수 있다.

## 확인 문제

1. 4KB 페이지에서 가상 주소 `0x12345` 의 VPN 과 오프셋은.
2. TLB 가 없다면 4단계 페이지 테이블에서 메모리 읽기 한 번에 실제로 몇 번의 메모리 접근이 필요한가(캐시 무시).
3. 마이너 페이지 폴트와 메이저 페이지 폴트의 차이는.
4. 큰 페이지가 TLB 미스를 줄이는 이유는.

### 풀이

1. VPN = `0x12`, 오프셋 = `0x345`.
2. 페이지 테이블 4단계 각 1번 + 실제 데이터 1번 = 5번.
3. 마이너는 디스크 I/O 없이 프레임을 연결만 하면 되는 폴트이고, 메이저는 스왑이나 파일에서 데이터를 읽어 와야 하는 폴트다.
4. TLB 항목 하나가 덮는 메모리 범위가 커져 같은 항목 수로 더 넓은 작업 집합을 감당하기 때문이다.

## 더 읽을거리 (References)

- Linux Kernel Documentation, [Transparent Hugepage Support](https://docs.kernel.org/admin-guide/mm/transhuge.html)
- Linux Kernel Documentation, [HugeTLB Pages](https://docs.kernel.org/admin-guide/mm/hugetlbpage.html)
- Python 공식 문서, [mmap — Memory-mapped file support](https://docs.python.org/3/library/mmap.html)
- Kubernetes Documentation, [Manage HugePages](https://kubernetes.io/docs/tasks/manage-hugepages/scheduling-hugepages/)
