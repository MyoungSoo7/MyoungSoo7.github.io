---
layout: post
title: "오프셋 과 어셈블리어 의 관계 — 어셈블리어 는 결국 오프셋 의 산술 언어 였다는 깨달음"
date: 2026-06-21 19:30:00 +0900
categories: [systems, low-level, assembly, compiler, computer-architecture]
tags: [assembly, x86-64, offset, addressing-mode, rip-relative, pic, aslr, struct-layout, calling-convention, gcc, gdb]
---

> *gdb* 에서 *disas main* 을 친다. 화면 가득 *수십 줄 의 어셈블리*. 무엇이 보이는가 :
>
> ```
> mov    -0x10(%rbp), %rax       ; rbp 에서 -16 만큼 떨어진 곳
> call   0x4011a0 <printf@plt>    ; 현재 위치 에서 *상대* 점프
> mov    0x20(%rdi), %rcx         ; rdi 가 가리키는 곳 에서 +32
> lea    0x2e9b(%rip), %rsi       ; 현재 명령어 의 *다음 주소* 에서 *상대*
> jne    0x401234                 ; 조건 분기 — *상대* 오프셋
> ```
>
> *전부 *오프셋*. *예외 없이*. *어셈블리어 의 *모든 메모리 접근*, *모든 호출*, *모든 분기*, *모든 변수* 가 *결국 *기준점 + 거리* 의 *산술***.

이 글은 *어셈블리어와 오프셋 사이 의 *깊은 관계* * 를 추적한다. *오프셋 이 *왜 *어셈블리 의 *본질 의 언어* * 인지, *왜 *절대 주소* 가 *환상* 이고 *상대 주소 만 *실재* 인지*, *그리고 이게 *모던 시스템 — PIC / ASLR / JIT / eBPF — 의 *기반* 으로 어떻게 이어지는지*.

*[내 어제 의 *프로세스 추상화* 글](/2026/06/18/process-abstraction.html)* 의 *한 단계 더 아래*. *[CPU 캐시 와 병목 분석](/2026/06/18/cpu-l1-l2-l3-cache-and-bottleneck-analysis.html)* 이 *물리* 라면 *오프셋 의 언어* 는 *그 위 의 *명령어 의 문법*.

---

## TL;DR — *한 줄 결론*

> *어셈블리어 의 *거의 모든 명령* 은 *오프셋 의 산술*. *메모리 접근 (base + index*scale + disp)*, *함수 호출 (call rel32)*, *분기 (jcc rel32)*, *전역 변수 접근 (RIP-relative)*, *구조체 필드 (compile-time offset)*, *스택 로컬 변수 (rbp offset)* — *예외 없이*. *"절대 주소" 는 *어셈블리 에는 거의 없다*. *오프셋 만 *실재*. *그래서 *바이너리 가 *어느 주소 에 로드 돼도 동작* 하고*, *그래서 *ASLR 이 가능* 하며*, *그래서 *JIT 이 *런타임에 *오프셋 산술* 만 *기계어 로 토해 내면* 된다*. *어셈블리어 = *오프셋 의 산술 언어*.

---

## 1. *오프셋 의 정의 *— *"기준점 + 거리" 의 *추상화***

*offset (오프셋)* 의 사전적 의미 — *"기준점 으로 부터 떨어진 양"*.

```
[기준점 base]                    [목표 target]
        │                              │
        └──────  offset = 거리  ───────┘
```

*컴퓨터 의 모든 위치 표현* 이 *이 관계* :
- *메모리* — 어떤 주소 에 *기준점* + *떨어진 바이트 수*
- *코드* — 현재 명령어 에서 *떨어진 명령어 수*
- *구조체* — 시작 주소 에서 *떨어진 필드 위치*
- *파일* — 시작 바이트 에서 *떨어진 위치 (fseek 의 offset)*

*절대 주소 = *기준점 0 + 오프셋*. *결국 *상대* 의 *특수한 경우*. *상대 가 더 일반* 이다.

---

## 2. *어셈블리 의 *어디에 오프셋 이 있나* — *6 가지 자리***

| # | 자리 | 형태 | 예시 |
|---|---|---|---|
| 1 | *메모리 주소 지정* | `[base + index*scale + disp]` | `mov rax, [rbp-0x10]` |
| 2 | *함수 호출* | `call rel32` (PC-relative) | `call printf` |
| 3 | *분기* | `jmp rel32`, `jcc rel32` | `je 0x4012a0` |
| 4 | *전역 변수* (x86-64) | `[rip + disp]` | `mov rax, [rip+0x2e9b]` |
| 5 | *구조체 필드* | `[base + struct_offset]` | `mov rax, [rdi+0x20]` |
| 6 | *PLT / GOT* | 모두 RIP-relative | `call printf@PLT` |

*하나도 *절대 주소* 가 아니다*. *전부 *오프셋*.

*절대 주소 명령* 이 *없는 건 아니다* — `mov rax, 0x401234` 같은 *immediate move* 가능. 그러나 *현대 컴파일된 코드* 에서 *거의 안 나옴*. *PIC (Position Independent Code)* 의 *표준* 이 됐기 때문.

---

## 3. *메모리 주소 지정 *— *x86-64 의 *황금 공식***

### 3.1 *[base + index*scale + disp]*

x86-64 의 *메모리 오퍼랜드* 의 일반 형태 :

```
주소 = base + index × scale + displacement
       (레지스터)  (레지스터)  (1/2/4/8)  (32bit 상수)
```

*displacement* = *오프셋*. *scale* = *원소 크기*. *index* = *몇 번째 원소*. *base* = *기준점*.

*하나의 명령 안* 에 *4 개의 구성요소*. *대부분 의 메모리 접근 이 *이 식 의 *특수형* *.

### 3.2 *7 가지 실용 케이스 — *컴파일러 가 *생성 하는 패턴***

```asm
; 1. 단순 절대 (immediate disp 만)
mov rax, [0x601020]              ; base=0, index=0, disp=0x601020

; 2. 스택 로컬 변수 — rbp 기반
mov rax, [rbp - 0x10]            ; base=rbp, disp=-16
                                 ; "함수 시작 시 16 바이트 떨어진 곳"

; 3. 함수 인자 — 일부는 rbp+offset (x86-64 는 대부분 레지스터지만 6 개 초과 시)
mov rax, [rbp + 0x18]            ; 7 번째 인자

; 4. 구조체 필드 — 객체 포인터 + 컴파일 타임 offset
mov rcx, [rdi + 0x20]            ; rdi 가 가리키는 객체 의 *0x20 번 필드*
                                 ; 예) struct { int a; long b; long c; } 의 .c

; 5. 배열 — base + index × scale
mov rax, [rdi + rcx*8]           ; rdi 가 배열, rcx 가 인덱스, 8 = sizeof(long)
mov al,  [rdi + rcx]             ; char 배열 (scale=1)

; 6. 다차원 배열 / 구조체 안 의 배열
mov rax, [rdi + rcx*8 + 0x10]    ; struct 의 0x10 위치 부터 *배열 시작*

; 7. RIP-relative (전역 변수 / 상수 / 문자열)
lea rsi, [rip + 0x2e9b]          ; "여기서 *3 KB* 뒤 의 *.rodata* 문자열"
```

*"이 모든 게 *기준점 + 오프셋* "* 이 *어셈블리 의 *세계관*.

---

## 4. *PC-Relative *— *함수 호출 과 분기 의 *오프셋***

### 4.1 *call 명령 의 진실*

C 코드 :
```c
printf("hello\n");
```

어셈블리 :
```asm
call 0x4011a0 <printf@plt>
```

*그러나 *기계어* 를 보면* :
```
e8 a0 fa ff ff
```

- `e8` — *call rel32* opcode
- `a0 fa ff ff` — *little-endian 32 bit signed* = *-0x560*

즉 *기계어 자체* 는 *"현재 명령 의 다음 주소 에서 -0x560 만큼 이동"*. *printf 의 *절대 주소* 가 *기계어 어디에도 없다*.

*어셈블러 가 *0x4011a0 으로 표시* 하는 건 *현재 PC + (-0x560) = 0x4011a0* 의 *계산 결과* 일 뿐. *실제 기계어 는 *오프셋*.

### 4.2 *jmp / jcc 의 *동일 원리***

```asm
4012a0: cmp rax, 0
4012a4: je 4012b8        ; 기계어 = 74 12  (jz rel8, +0x12)
                          ; "여기 +18 바이트"
```

*"4012b8 로 점프"* 가 아니라 *"여기 에서 +18 바이트"*. *컴파일러 가 *위치 가 바뀌어도 *명령어 사이 의 거리* 만 유지하면 *정상 동작*.

### 4.3 *RIP-relative *— *x86-64 의 발명***

*32-bit x86* 에선 *전역 변수 접근* 이 *절대 주소* :
```asm
mov eax, [0x804a000]         ; 32-bit 절대 주소
```

*64-bit x86-64* 가 *대규모 변경* — *RIP-relative 주소 지정* 추가 :
```asm
mov rax, [rip + 0x2e9b]      ; PC 기반 상대 주소
```

*왜* — *Position Independent Code (PIC)* 의 *기본 단위*. *바이너리 가 *어느 주소 에 매핑돼도* *오프셋 그대로 동작*. *ASLR 의 *기반*.

---

## 5. *구조체 의 *컴파일 타임 오프셋***

### 5.1 *struct 의 *물리 적 *레이아웃***

```c
struct User {
    int  id;        // offset 0  (4 byte)
    char _pad[4];   // offset 4  (padding for alignment)
    long created;   // offset 8  (8 byte)
    long updated;   // offset 16 (8 byte)
};
```

*컴파일 시점* 에 *각 필드 의 오프셋* 이 *상수* 로 결정. *런타임 에 변경 불가*.

C 코드 :
```c
user->updated = 100;
```

어셈블리 :
```asm
mov qword [rdi + 0x10], 100
```

*"rdi 가 가리키는 User 객체 의 *16 번 째 바이트 부터* 100"*. *컴파일러 가 *struct User 의 *.updated 가 offset 0x10 임* 을 *컴파일 시점* 에 *알고 박아 넣는다*.

### 5.2 *offsetof() 매크로 의 *시각화***

C 의 `offsetof(struct User, updated)` 는 *컴파일 시점* 에 *상수 16* 으로 치환. *런타임 계산 0*.

JVM 의 *Unsafe.objectFieldOffset()* 도 *동일 의미* — *런타임 에 *오프셋 한 번 계산* 해 두고 *그 다음 모든 접근 은 *오프셋 산술* 한 방*.

### 5.3 *왜 *구조체 필드 가 빠른가***

```asm
; 1 명령 — *상수 오프셋 더하기 + 로드*
mov rax, [rdi + 0x10]
```

*CPU 의 *주소 계산 유닛 (AGU)* 가 *base + disp 를 1 사이클* 안 에 계산. *L1 캐시 히트* 면 *4 사이클 안 에 완료*. *오프셋 의 *컴파일 타임 결정* 이 *극한 성능 의 기반*.

*동적 객체 (Python 의 dict, JS 의 object)* 가 *느린 이유* — *필드 위치 가 *런타임 에 *해시 lookup*. *오프셋 산술 1 명령 vs 해시 lookup 수십 명령* 의 차이.

---

## 6. *스택 프레임 *— *함수 의 *오프셋 공간***

### 6.1 *프롤로그 가 *오프셋 할당하는 의식***

C :
```c
int func(int a, int b) {
    int local1 = a + b;
    int local2 = a * b;
    char buf[64];
    return local1 + local2;
}
```

어셈블리 :
```asm
func:
    push rbp                ; 이전 rbp 저장
    mov rbp, rsp            ; 현재 스택 정점 을 *기준점* 으로
    sub rsp, 0x60           ; *96 바이트 의 *오프셋 공간* 확보

    ; 로컬 변수 들 의 *위치 가 *오프셋 으로 결정*
    mov [rbp-0x04], edi     ; a 저장 (offset -4)
    mov [rbp-0x08], esi     ; b 저장 (offset -8)
    mov eax, [rbp-0x04]
    add eax, [rbp-0x08]
    mov [rbp-0x0c], eax     ; local1 = a + b (offset -12)
    mov eax, [rbp-0x04]
    imul eax, [rbp-0x08]
    mov [rbp-0x10], eax     ; local2 = a * b (offset -16)
    ; buf 는 [rbp-0x60] ~ [rbp-0x20] 의 64 바이트
    
    mov eax, [rbp-0x0c]
    add eax, [rbp-0x10]
    
    leave                   ; rbp 복원 + rsp 복원
    ret
```

*함수 의 *지역 변수* 들 이 *전부 *rbp 기준 의 오프셋*. *컴파일러 가 *지역 변수 별 *오프셋* 을 *컴파일 시점에 *할당*. *런타임 에는 *그저 산술*.

### 6.2 *Calling Convention *— *오프셋 의 약속***

System V AMD64 ABI :
- 첫 6 개 정수 인자 : rdi, rsi, rdx, rcx, r8, r9
- 7 번째 부터 : *스택 의 *rbp + 0x10*, *rbp + 0x18*, ...
- 반환값 : rax
- Caller-saved : rax, rcx, rdx, ...
- Callee-saved : rbx, rbp, r12~r15

*"7 번째 인자 = rbp + 0x10"* 같은 *모든 약속 이 *오프셋*. *Calling Convention = *오프셋 의 합의*.

---

## 7. *왜 *절대 주소 가 환상* 인가 *— *PIC · ASLR · 가상 주소***

### 7.1 *Position Independent Code (PIC)*

*PIC* = *코드 가 *어느 주소 에 로드되든 *동일하게 동작*. *가능 한 이유* — *모든 주소 참조* 가 *PC-relative offset*.

```asm
; PIC 이전 (32-bit)
mov eax, [0x80100000]      ; 절대 주소. 이 주소가 정확해야 동작

; PIC 이후 (x86-64)
mov eax, [rip + 0xabc]     ; 현재 위치 기준 상대. *어디 로드돼도 동작*
```

*PIE (Position Independent Executable)* 는 *PIC 의 확장* — *실행 파일* 도 *어느 주소 든 로드 가능*.

### 7.2 *ASLR (Address Space Layout Randomization)*

*보안 기능* — *프로세스 의 *코드 / 스택 / heap / 라이브러리 주소* 를 *부팅 마다 *랜덤화*. *공격자 가 *gadget 주소 를 *못 예측*.

*ASLR 이 가능 한 이유* — *PIC 의 *오프셋 기반 코드* 가 *어느 주소 에서 든 동작*. *절대 주소 코드* 였다면 *재배치 (relocation)* 가 *매번 필요* 해서 *비현실적*.

### 7.3 *가상 메모리 의 *오프셋 본질***

*가상 주소 0x4011a0* — *이게 *물리 주소* 가 아니다*. *프로세스 의 *CR3 (페이지 테이블 베이스)* 에 *상대 적인 *4 단계 (PGD/P4D/PUD/PMD/PT)* 변환* 후 *물리 주소*.

```
가상 주소 = CR3 + 페이지 테이블 트래버설
물리 주소 = 페이지 테이블 의 *최종 PT entry* 가 가리키는 *물리 페이지* + page 내 *오프셋*
```

*"가상 주소 = 물리 주소 의 *환상* "*. *모든 게 *기준 + 변환 + 오프셋*.

CPU 의 *MMU + TLB* 가 *이 변환을 *나노초 단위* 로* 처리. *어셈블리 의 *오프셋 산술* 이 *MMU 의 *주소 변환* 위 에서 동작*. *2 단 의 *오프셋 의 산술*.

---

## 8. *모던 시스템 의 *오프셋 의 진화***

### 8.1 *JIT — *런타임에 *오프셋 산술 코드 생성***

*HotSpot JVM* 의 *C2 컴파일러* 가 *Java 메서드 를 기계어로 변환* 할 때 :

```java
// Java
class User {
    int id;
    String name;
}

user.id = 42;
```

```asm
; JIT 가 *런타임에 *생성* — *컴파일 타임 의 *struct offset* 과 동일 원리*
mov dword [r10 + 12], 42       ; r10=user, *12 는 *Java 객체 헤더 (mark word + klass) 다음*
```

*JIT 가 *런타임 에 *Class 의 layout* 을 *계산* — *그 결과 가 *상수 오프셋*. *그 후 의 모든 필드 접근 은 *C 의 구조체 만큼 빠름*. *Java 가 *느리지 않은 이유*.

### 8.2 *eBPF — *오프셋 검증 의 verifier***

*Linux 의 eBPF* — *커널 안 에서 *유저 코드 실행*. *안전성 보장* 의 *핵심* 이 *verifier*.

*verifier 가 검사하는 것* :
- *모든 메모리 접근 이 *허용된 오프셋 범위* 안 인가
- *포인터 + 오프셋* 의 결과 가 *해당 객체 의 *크기 안* 인가
- *루프 의 *오프셋 변화* 가 *수렴 하는가*

*"안전 한 코드 = *오프셋 의 *정적 분석 통과 한 코드*"*. *eBPF 의 *안전성 보장* 이 *오프셋 의 *수학적 검증*.

### 8.3 *CHERI — *capability 기반 의 *오프셋의 의미 변환***

*ARM Morello*, *RISC-V CHERI* 의 *capability* — *포인터 가 *그냥 64-bit 주소* 가 아니라 *base + bounds + permissions* 의 *128-bit 캡슐*.

```
[ 전통 포인터 ]
   주소 64 bit
   → 무한 산술 가능 (off-by-one 가능)

[ Capability ]
   주소 + (시작 ~ 끝) + 권한 128 bit
   → *오프셋 더하기* 가 *bounds 안 일 때만 유효*
   → off-by-one / buffer overflow *하드웨어 단계* 에서 차단
```

*오프셋 산술 의 *자유 가 *제약 됨*. *그 대신 *메모리 안전성 의 *새 차원*.

---

## 9. *체감 *— *gdb 에서 *오프셋 으로 보는 시야***

### 9.1 *디스어셈블 의 *오프셋 읽기***

```
(gdb) disas main
   0x4011a0 <+0>:     push   %rbp
   0x4011a1 <+1>:     mov    %rsp,%rbp
   0x4011a4 <+4>:     sub    $0x20,%rsp                  ; *오프셋 공간 32 byte 확보*
   0x4011a8 <+8>:     movl   $0x0,-0x4(%rbp)             ; *rbp 에서 -4 (= 첫 로컬 변수)*
   0x4011af <+15>:    movq   $0x402004,-0x10(%rbp)       ; *rbp 에서 -16 의 *문자열 주소*
   0x4011b7 <+23>:    mov    -0x10(%rbp),%rax
   0x4011bb <+27>:    mov    %rax,%rdi
   0x4011be <+30>:    call   0x401080 <puts@plt>         ; *상대 호출*
   0x4011c3 <+35>:    leave
   0x4011c4 <+36>:    ret
```

*모든 명령 의 *왼쪽 의 주소* 도 *섹션 베이스 + 오프셋*. *각 명령 안 의 *피연산자* 도 *오프셋*. *오프셋 의 산술 만 보이면 *어셈블리 가 *읽힌다*.

### 9.2 *디버깅 의 *오프셋 매핑***

내가 *gdb 의 backtrace* 에서 *함수명 + 오프셋* 을 보는 이유 — *디버그 정보 가 없어도 *어셈블리 의 *어느 지점* 인지 *알 수 있게* :

```
#0  0x00007ffff7e3a4a0 in __memcmp_avx2_movbe () from /lib64/libc.so.6
#1  0x0000000000401234 in compare_users+0x42 () at user.c:128
                                          ^^^^
                                          *함수 시작 에서 *66 바이트 떨어진 명령*
```

*Stack trace 의 *모든 frame* 이 *함수 + 오프셋*. *심볼 만 있으면 *오프셋 으로 *정확 한 명령 위치* 까지 *역추적* 가능*.

### 9.3 *Core dump 분석 의 *오프셋 활용***

내 [*Settlement 시스템 의 *디버깅 경험*](/2026/06/18/eight-checklist-self-audit-of-my-settlement-system.html)* 에서 — *프로덕션 의 *segfault* 가 발생 시 *코어 덤프* 를 *gdb 에 띄우면* *함수명 + 오프셋* 으로 *정확한 줄* 까지 *복원*. *디버그 심볼 패키지 + 오프셋* 의 조합 이 *프로덕션 디버깅 의 *생명선*.

---

## 10. *오프셋 의 산술 *— *어셈블리어 의 *문법***

여기까지 의 *큰 그림* :

| 추상화 레이어 | 오프셋 의 형태 |
|---|---|
| *C 의 구조체 필드 접근* | `offsetof()` 의 *컴파일 타임 상수* |
| *어셈블리 의 메모리 접근* | `[base + index*scale + disp]` |
| *함수 호출* | `call rel32` |
| *분기* | `jcc rel32` |
| *전역 변수* | `[rip + disp]` |
| *PIC / PIE* | *모든 참조 가 PC-relative* |
| *ASLR* | *부팅 마다 *base 만 *랜덤*. *오프셋 은 동일* |
| *가상 메모리* | *CR3 기준 *페이지 테이블 트래버설 + 페이지 내 오프셋* |
| *JIT 생성 코드* | *런타임 에 *클래스 layout 계산 후 *오프셋 상수* |
| *eBPF verifier* | *오프셋 의 *정적 안전성 분석* |
| *CHERI capability* | *오프셋 산술 의 *bounds 강제* |

*"어셈블리어 는 *오프셋 의 *산술 언어*"*. *이 한 줄 이 *모든 것 의 요약*.

---

## 11. *맺음 *— *오프셋 의 *시야 를 가지면***

내가 *시스템 을 디버깅 할 때* — *gdb 의 disas*, *perf 의 hot function*, *objdump 의 출력*, *coredump 의 backtrace* — *모든 것* 이 *오프셋 의 산술* 로 표현된다.

*오프셋 의 시야* 를 가지면 :

1. **C 의 *구조체 레이아웃* 이 *물리적 으로 보인다*** — *padding / alignment 가 *오프셋 의 *낭비* 임이 보임. *false sharing 의 *원인* 도 *오프셋 의 *경합*.

2. **JIT 컴파일러 의 *성능 비밀* 이 보인다*** — *Polymorphic Inline Cache 의 *클래스 별 오프셋 캐싱* 의 *진짜 의미*.

3. **보안 취약점 의 *원리* 가 보인다*** — *buffer overflow 의 *오프셋 의 *부정 변경*. *ROP 의 *gadget 주소* 의 *오프셋 의 *예측 가능성**.

4. **분산 시스템 의 *직렬화* 가 보인다*** — *Protocol Buffer / Avro 의 *field number = 오프셋*. *바이너리 포맷 의 *오프셋 의 *불변 약속*.

내 [*Settlement 의 Outbox*](/2026/06/15/transaction-outbox-pattern-async-integration-deep-dive.html) 의 *Kafka 메시지 의 offset* 까지 — *Kafka 의 *consumer offset* 도 *partition 시작 부터 의 *바이트 오프셋*. *분산 시스템 의 *replay / catch up* 의 *기반*.

*어셈블리 의 오프셋* 부터 *Kafka 의 오프셋* 까지 — *같은 추상화*. *기준 + 거리*. *상대 적 위치 의 산술*.

*내일 *gdb 에서 disas* 를 칠 때* — *명령어 의 *피연산자* 를 보면서 *"이건 오프셋"* 이라고 *읽을 수 있다면* — *어셈블리 가 *읽힌다*. *어셈블리 가 *읽히면 *시스템 의 *진짜 모습* 이 보인다*.

오프셋 의 시야 가 *시스템 엔지니어 의 *X-ray 시야*.

---

## 부록 — *오늘 *3 분 안 에 해볼 수 있는 *3 가지***

```sh
# 1. C 코드 한 줄을 어셈블리로 — *오프셋 의 노출*
echo 'struct U { int a; long b; }; int main() { struct U u; u.b = 42; return 0; }' | \
  gcc -O0 -S -masm=intel -x c - -o /dev/stdout | head -30

# 2. 내 바이너리 의 *call 의 오프셋 보기*
objdump -d -M intel /usr/bin/ls | grep -E 'call|jmp' | head -10

# 3. gdb 의 *오프셋 시야*
gdb -batch -ex 'file /usr/bin/ls' -ex 'disas main' 2>/dev/null | head -20
```

*첫 번째* 의 결과 에서 *.b 의 오프셋 이 *8* 임을 확인* (padding 포함). *두 번째* 에서 *모든 call / jmp 가 *상대 주소* 임 확인*. *세 번째* 에서 *내 시스템 의 *어떤 바이너리 든 *오프셋 의 언어* 로 *읽을 수 있음* 을 확인*.

이 *3 분 의 경험* 이 *어셈블리어 가 *오프셋 의 산술 언어* 라는 *직관* 을 *몸에 새긴다*.

---

*관련 글*

- [*CPU 의 *L1/L2/L3 캐시* — 메모리 벽 과 병목 구간 분석*](/2026/06/18/cpu-l1-l2-l3-cache-and-bottleneck-analysis.html) — *오프셋 의 *물리* 인 *캐시 라인 정렬*
- [*프로세스 라는 추상화* — CPU·메모리·스레드·코어 가 만나는 중심](/2026/06/18/process-abstraction.html) — *가상 메모리 의 *오프셋의 환상*
- [*IntelliJ 가 켜질 때 도대체 무엇이 실행되는가*](/2026/06/18/intellij-startup-processes-ssd-memory-cpu-deep-dive.html) — *JIT 의 *런타임 오프셋 산술 코드 생성*
- [*Transactional Outbox 패턴 과 비동기 통합 *깊이 들여다 보기*](/2026/06/15/transaction-outbox-pattern-async-integration-deep-dive.html) — *Kafka offset 까지 의 *오프셋의 추상화 의 *연속체*
