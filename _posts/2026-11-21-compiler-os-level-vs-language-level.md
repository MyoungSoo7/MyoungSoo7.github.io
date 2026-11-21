---
layout: post
title: "컴파일러를 두 층에서 보기 — 언어 레벨과 OS 레벨, 그리고 둘이 부딪히는 곳"
date: 2026-11-21 17:23:02 +0900
categories: [cs, compiler]
tags: [compiler, abi, elf, linker, syscall, undefined-behavior, memory-model, llvm, go]
---

컴파일러를 "소스 코드를 기계어로 바꾸는 프로그램"이라고만 설명하면 절반을 빼먹게 된다. 컴파일러는 **두 개의 계약 사이에 끼인 번역기**다.

- **위쪽 계약 — 언어 명세.** 이 프로그램이 *무슨 뜻인지*를 정한다. 컴파일러는 이 뜻을 보존하는 한 무엇이든 해도 된다.
- **아래쪽 계약 — OS·하드웨어의 ABI.** 만들어진 바이너리가 *어떻게 실행 환경과 맞물리는지*를 정한다. 레지스터를 어떻게 쓰는지, 파일 형식은 무엇인지, 커널은 어떻게 부르는지가 여기에 들어간다.

이 글은 두 층을 차례로 본 다음, 실제 사고가 났던 **두 층의 경계**를 사례 세 개로 짚는다.

---

## 1. 언어 레벨 — "뜻만 보존하면 된다"

### 1.1 파이프라인

교과서적인 구성은 프론트엔드(어휘·구문 분석, 타입 검사), 중간 표현(IR), 최적화, 코드 생성이다 ([Aho et al., *Compilers: Principles, Techniques, and Tools*, 2판](#ref-dragon)). 현대 컴파일러에서 핵심은 IR이다. LLVM은 언어와 무관한 SSA(Static Single Assignment) 형태의 저수준 IR을 정의하고, 같은 IR 위에서 컴파일·링크·실행 시점의 분석과 변환을 모두 돌리도록 설계됐다 ([Lattner & Adve, CGO 2004](#ref-llvm)). 그래서 C·Rust·Swift가 서로 다른 프론트엔드를 쓰면서도 최적화기와 백엔드는 공유할 수 있다.

### 1.2 최적화의 근거는 "as-if" 와 미정의 동작

C 표준은 구현이 **관찰 가능한 동작**(volatile 접근, 파일 입출력 등)만 추상 기계와 같으면 실제 계산은 생략하거나 바꿔도 된다고 허용한다 ([ISO/IEC 9899:2011 §5.1.2.3, N1570 초안](#ref-c11)). 이른바 as-if 규칙이다.

여기에 **미정의 동작(UB)** 이 더해진다. 표준이 "UB가 일어나면 아무 일이나 일어나도 된다"고 하므로, 컴파일러는 *UB가 일어나지 않는다*고 가정하고 최적화할 수 있다. Wang 등은 이 가정 때문에 소스에는 있는데 바이너리에서는 사라지는 코드를 *optimization-unstable code* 라고 부르고, 이를 찾는 정적 검사기 STACK을 만들었다. STACK을 리눅스 커널과 Postgres 등에 돌려 개발자가 확인하고 고친 새 버그 160건을 찾았고, C/C++ 코드가 있는 Debian Wheezy 패키지 8,575개 중 3,471개에서 이런 코드가 최소 한 건 검출됐다 ([Wang et al., SOSP 2013](#ref-stack)).

언어 레벨의 컴파일러는 이렇게 생각한다. **"명세가 보장하지 않는 것은 존재하지 않는다."**

---

## 2. OS 레벨 — "바이너리는 혼자 돌지 않는다"

컴파일러가 뱉은 기계어는 그 자체로는 실행되지 않는다. 함수를 부르는 방식, 파일에 담기는 형식, 메모리에 올라가는 방식, 커널에 부탁하는 방식이 모두 OS 쪽 계약에 묶여 있다.

### 2.1 호출 규약(ABI)

x86-64 리눅스는 System V AMD64 psABI를 따른다. 정수 인자는 `rdi, rsi, rdx, rcx, r8, r9` 순으로 넘기고, 스택 정렬과 caller/callee-saved 레지스터 구분까지 이 문서가 정한다 ([x86-64 psABI](#ref-psabi)). 서로 다른 컴파일러로 만든 오브젝트 파일을 링크할 수 있는 건 둘 다 이 규약을 지키기 때문이다.

### 2.2 오브젝트 파일·링커·로더

컴파일러 출력은 ELF 오브젝트다. 섹션(`.text`, `.data` …)과 심볼 테이블, 재배치 항목을 담는다 ([System V gABI — ELF](#ref-elf)). 정적 링커가 이것들을 묶어 실행 파일을 만들고, 실행 시점에는 동적 로더 `ld.so` 가 공유 라이브러리를 찾아 매핑하고 심볼을 해석한다 ([ld.so(8)](#ref-ldso)). `-fPIC` 나 PIE 같은 컴파일 옵션이 존재하는 이유가 여기 있다. 코드가 *어느 주소에 올라갈지 모른다*는 OS 쪽 사정을 컴파일러가 코드 생성 단계에서 반영해야 하기 때문이다.

### 2.3 시스템 콜 — 함수 호출과 닮았지만 다르다

커널을 부르는 규약은 함수 호출 규약과 비슷하지만 **같지 않다.** `syscall(2)` 매뉴얼의 표를 보면 x86-64에서 시스템 콜 번호는 `rax`, 인자는 `rdi, rsi, rdx, r10, r8, r9` 다 ([syscall(2)](#ref-syscall)). 함수 호출의 네 번째 인자 `rcx` 자리에 `r10` 이 들어가 있다. psABI 부록에 따르면 `syscall` 명령이 `rcx` 와 `r11` 을 덮어쓰기 때문이다 ([x86-64 psABI, Linux kernel conventions](#ref-psabi)). 아키텍처마다 이 표가 다르고, 32비트 ARM EABI처럼 64비트 인자를 짝수 레지스터 쌍에 정렬해야 하는 곳도 있다. 매뉴얼은 이를 "역사적 짐(historical baggage)"이라고 적는다.

### 2.4 "안정된 경계"가 어디냐는 OS마다 다르다

리눅스는 **커널↔유저 공간 시스템 콜 인터페이스를 깨지 않는다**고 약속한다. 커널 내부 드라이버 API는 계속 바뀌어도 시스템 콜 인터페이스는 안정적이라는 것이 Greg Kroah-Hartman의 커널 문서 설명이다 ([stable-api-nonsense](#ref-kapi)).

다른 OS는 그렇지 않다. 그래서 언어 툴체인이 OS에 맞춰 설계를 바꾼 기록이 남아 있다.

- **Go 1.12 (macOS/iOS):** 시스템 콜을 직접 하지 않고 `libSystem` 을 거치도록 바꿨다. 이유는 "향후 macOS·iOS 버전과의 전방 호환성 보장"이다 ([Go 1.12 Release Notes](#ref-go112)).
- **Go 1.16 (OpenBSD amd64/arm64):** 마찬가지로 `SYSCALL`/`SVC` 명령 대신 `libc` 를 거치게 바꿨다. OpenBSD 6.9부터는 non-static Go 바이너리가 libc를 통해서만 시스템 콜을 하도록 요구되기 때문이다 ([Go 1.16 Release Notes](#ref-go116)).

같은 언어, 같은 컴파일러라도 **"안정된 계약이 커널에 있느냐 libc에 있느냐"** 라는 OS 쪽 사실이 코드 생성과 런타임 구조를 바꾼다.

---

## 3. 두 층이 부딪히는 곳 — 사례 셋

### 3.1 UB 최적화 vs 커널: 사라진 NULL 검사 (2009)

리눅스 2.6.30의 TUN 드라이버에 이런 코드가 들어갔다 ([LWN, "Fun with NULL pointers, part 1"](#ref-lwn)).

```c
struct tun_struct *tun = __tun_get(tfile);
struct sock *sk = tun->sk;   /* 먼저 역참조 */
...
if (!tun)                    /* 그다음 검사 */
    return POLLERR;
```

언어 레벨에서 보면 GCC의 판단은 옳다. `tun->sk` 에서 이미 역참조했으니 `tun` 이 NULL이면 UB이고, 따라서 `tun` 은 NULL이 아니라고 가정해도 된다. 그래서 GCC는 `if (!tun)` 을 지워 버렸다.

OS 레벨에서 보면 결과는 재앙이다. 커널 공간에서는 0번지가 매핑돼 있을 수 있어서 NULL 역참조가 곧바로 죽지 않는다. 결국 이 조합이 로컬 권한 상승 익스플로잇이 됐다.

오늘날 리눅스 최상위 `Makefile` 에는 언어 레벨 최적화 일부를 끄는 플래그가 박혀 있다 ([torvalds/linux Makefile](#ref-kmake)).

```make
KBUILD_CFLAGS += -fno-strict-aliasing
KBUILD_CFLAGS += -fno-delete-null-pointer-checks
KBUILD_CFLAGS += -fno-strict-overflow
```

OS를 만드는 쪽은 "C 표준이 허용하는 최적화"를 다 받아들일 수 없다. 커널은 C 표준보다 **더 구체적인 기계를 전제로 하는 C 방언**을 쓰는 셈이다. Wang 등이 정의한 C⋆(평평한 주소 공간, 0번지 NULL, 정수 랩어라운드를 가정한 C)가 정확히 이 간극을 형식화한 것이다 ([Wang et al., SOSP 2013](#ref-stack)).

### 3.2 스레드는 라이브러리로 만들 수 없다 (2005)

pthread는 *라이브러리*다. 언어(C99까지)는 스레드를 몰랐다. Boehm은 이 접근이 "거의" 동작하지만 근본적으로는 정확성을 보장할 수 없음을 보였다. 단일 스레드에서는 완벽히 합법인 최적화, 예를 들어 락 바깥으로 변수를 레지스터에 올렸다가 되써 넣는 *speculative register promotion* 이 다른 스레드가 보기에는 없던 쓰기를 만들어 낸다. Boehm에 따르면 이 변환을 한때 수행한 최적화 컴파일러가 최소 네 개(그중 셋은 프로덕션)였다 ([Boehm, PLDI 2005](#ref-boehm)).

결론은 **"컴파일러가 스레드의 존재를 알아야 하고, 언어 명세가 스레드 의미론을 다뤄야 한다"** 였다. 이 논의가 C11·C++11 메모리 모델로 이어졌다. OS가 제공하는 기능(스레드)을 언어 밖 라이브러리로만 두면 언어 레벨 컴파일러가 그 기능을 깨뜨릴 수 있다는 교훈이다.

### 3.3 언어 런타임이 OS 보안 정책과 부딪히다 (2026)

마지막은 이번 달 필자의 홈랩에서 실제로 겪은 일이다. 공개 버그로 정리돼 있다 ([Launchpad #2172422](#ref-lp)).

- **언어 레벨 사정.** 리눅스에서 `setuid` 는 원래 *스레드 단위*로 적용된다. 그런데 POSIX는 프로세스 전체에 적용되기를 요구한다. 그래서 Go 런타임은 `setuid`/`setgid` 를 부르면 모든 스레드에 신호(`SIGRTMIN+1`)를 보내 각 스레드가 같은 시스템 콜을 하게 만든다. 런타임 내부 경로는 `doAllThreadsSyscall` 이다.
- **OS 레벨 사정.** Ubuntu 커널 7.0.0-42/-43에 들어간 AppArmor 보안 패치(CVE-2026-90231) 이후 컨테이너 안 스레드의 라벨이 `docker-default//&unconfined` 같은 *스택 라벨*로 바뀌었다. 그러자 "같은 프로필끼리는 신호 허용" 규칙이 더 이상 매치되지 않았다.
- **결과.** 스레드들은 신호를 못 받고, 메인 스레드는 `sched_yield()` 를 무한 반복한다. Go 1.24로 빌드된 `gosu` 로 권한을 내리는 공식 postgres·mariadb·mongo 이미지가 entrypoint에서 영원히 멈춘다. 버그 리포트에 따르면 같은 커널에서도 Go 1.16.5로 빌드된 옛 gosu는 멀쩡히 동작했다.

컴파일러도, 커널도, 각자의 계약 안에서는 틀린 게 없다. 하지만 **"런타임이 OS에 무엇을 기대하는가"** 는 두 명세 어디에도 온전히 적혀 있지 않았고, 그 틈에서 사고가 났다. 커널 로그에 `apparmor="DENIED" ... comm="gosu" ... signal=rtmin+1` 한 줄이 찍히는 게 거의 유일한 단서였다.

이 사례에서 필자가 쓴 우회책은 양쪽 레벨을 다 건드리지 않는 것이었다. 컨테이너를 처음부터 비root uid로 띄우면 entrypoint가 gosu를 건너뛰므로, `setuid` 경로 자체를 타지 않는다.

---

## 4. 그럼 컴파일러는 믿을 수 있나 — 증명의 경계

CompCert는 C 부분집합(Clight)에서 어셈블리까지의 컴파일러를 Coq로 작성하고, **의미 보존을 기계적으로 증명**했다 ([Leroy, CACM 2009](#ref-compcert)). 언어 레벨에서 가장 강한 보증이다.

그래도 증명의 범위를 정확히 읽어야 한다. 증명은 "소스 의미론 → 어셈블리 의미론"의 보존이다. 어셈블러·링커·로더·커널이 그 어셈블리를 의도대로 실행해 준다는 것은 *가정*이다. 3장의 사고 세 건이 모두 이 가정 쪽에서 났다는 점이 시사적이다.

---

## 5. 정리

| 질문 | 언어 레벨 | OS 레벨 |
|---|---|---|
| 계약 문서 | 언어 표준 (C11 등) | psABI, ELF gABI, 시스템 콜 규약 |
| 컴파일러의 자유 | as-if + "UB는 없다" 가정 | 거의 없음 — 규약을 그대로 따라야 함 |
| 깨지면 | 소스가 바이너리에서 사라짐 (unstable code) | 링크 실패, 로드 실패, 런타임 행·크래시 |
| 대표 사고 | 2009 TUN NULL 검사 삭제 | 2026 AppArmor × Go setuid 행 |
| 방어 수단 | `-fno-delete-null-pointer-checks` 등, STACK | 안정된 경계(libc/syscall) 선택, 런타임 설계 변경 |

한 줄로 줄이면 이렇다. **언어 레벨 컴파일러는 "명세에 없는 것은 없다"고 믿고, OS 레벨은 "명세에 없는 것도 일어난다"고 말한다.** 실무의 버그는 대개 이 두 믿음이 겹치는 얇은 띠에서 나온다.

> **근거의 한계.** 3.3의 원인 분석은 Launchpad 버그 리포트(보고자의 재현·대조 실험)와 필자의 같은 증상 재현에 근거한다. 2026-11-21 현재 버그 상태는 *Confirmed* 이며, Canonical의 공식 수정 공지는 아직 없다.

---

## References

1. <a id="ref-dragon"></a>A. V. Aho, M. S. Lam, R. Sethi, J. D. Ullman. *Compilers: Principles, Techniques, and Tools*, 2nd ed. Addison-Wesley, 2006.
2. <a id="ref-llvm"></a>C. Lattner, V. Adve. "LLVM: A Compilation Framework for Lifelong Program Analysis & Transformation." CGO 2004. <https://llvm.org/pubs/2004-01-30-CGO-LLVM.html>
3. <a id="ref-c11"></a>ISO/IEC 9899:2011 (C11), §5.1.2.3 Program execution. 공개 초안 N1570: <https://www.open-std.org/jtc1/sc22/wg14/www/docs/n1570.pdf>
4. <a id="ref-stack"></a>X. Wang, N. Zeldovich, M. F. Kaashoek, A. Solar-Lezama. "Towards Optimization-Safe Systems: Analyzing the Impact of Undefined Behavior." SOSP 2013. <https://sigops.org/s/conferences/sosp/2013/papers/p260-wang.pdf> · DOI <https://doi.org/10.1145/2517349.2522728>
5. <a id="ref-psabi"></a>System V Application Binary Interface — AMD64 Architecture Processor Supplement (x86-64 psABI). <https://gitlab.com/x86-psABIs/x86-64-ABI>
6. <a id="ref-elf"></a>System V ABI, Generic ABI — ELF. <https://refspecs.linuxfoundation.org/elf/gabi4+/contents.html>
7. <a id="ref-ldso"></a>Linux man-pages, ld.so(8). <https://man7.org/linux/man-pages/man8/ld.so.8.html>
8. <a id="ref-syscall"></a>Linux man-pages, syscall(2). <https://man7.org/linux/man-pages/man2/syscall.2.html>
9. <a id="ref-kapi"></a>G. Kroah-Hartman. "The Linux Kernel Driver Interface (stable-api-nonsense)." Linux kernel documentation. <https://www.kernel.org/doc/html/latest/process/stable-api-nonsense.html>
10. <a id="ref-go112"></a>Go 1.12 Release Notes — Darwin. <https://go.dev/doc/go1.12>
11. <a id="ref-go116"></a>Go 1.16 Release Notes — OpenBSD. <https://go.dev/doc/go1.16>
12. <a id="ref-lwn"></a>J. Corbet. "Fun with NULL pointers, part 1." LWN.net, 2009-07-20. <https://lwn.net/Articles/342330/>
13. <a id="ref-kmake"></a>Linux kernel top-level Makefile (`KBUILD_CFLAGS`). <https://github.com/torvalds/linux/blob/master/Makefile>
14. <a id="ref-boehm"></a>H.-J. Boehm. "Threads Cannot Be Implemented As a Library." PLDI 2005. DOI <https://doi.org/10.1145/1065010.1065042>
15. <a id="ref-lp"></a>Launchpad Bug #2172422, "Regression 7.0.0-42/-43: Go 1.24 programs livelock in setuid (gosu); official DB Docker images hang on start." <https://bugs.launchpad.net/bugs/2172422>
16. <a id="ref-compcert"></a>X. Leroy. "Formal verification of a realistic compiler." *Communications of the ACM* 52(7), 2009. <https://xavierleroy.org/publi/compcert-CACM.pdf>
