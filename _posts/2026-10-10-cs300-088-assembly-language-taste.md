---
layout: post
title: "[CS300 #088] 어셈블리 언어 맛보기 — 컴파일러가 만든 코드를 읽는 법"
date: 2026-10-10 19:28:00 +0900
categories: [cs]
tags: [cs300, computer-architecture, assembly, x86-64, compiler-output]
---

컴퓨터공학 300 주제 시리즈의 088번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

어셈블리 언어는 기계어 명령어를 사람이 읽을 수 있는 기호로 한 줄씩 옮긴 언어다. 직접 작성할 일은 드물지만, 컴파일러가 만든 어셈블리를 읽을 수 있으면 성능 문제와 이상한 버그의 정체가 보인다.

## 왜 필요한가

고급 언어의 한 줄이 실제로 몇 개의 명령어가 되는지, 반복문이 어떻게 분기로 바뀌는지, 함수 인자가 어디로 넘어가는지는 어셈블리를 봐야 알 수 있다. 실무에서 어셈블리를 마주치는 장면은 대개 다음과 같다.

- 프로파일러(`perf annotate`)가 핫스팟을 명령어 단위로 보여 줄 때
- 코어 덤프나 크래시 로그에 찍힌 명령어 주소를 해석할 때
- 컴파일러가 반복문을 벡터화했는지 확인할 때
- 보안 분석에서 바이너리의 동작을 추적할 때

목표는 어셈블리로 프로그램을 짜는 것이 아니라 **읽는 것**이다.

## 핵심 개념

### 기계어와 어셈블리, 어셈블러

```
C 소스 ──(컴파일러)──► 어셈블리 ──(어셈블러)──► 목적 파일 ──(링커)──► 실행 파일
                       addq %rsi,%rax              48 01 f0
```

어셈블리 한 줄은 대개 기계어 명령어 하나에 대응한다. 어셈블러는 기호를 비트로 바꾸고, 레이블을 주소로 계산해 넣는다.

### x86-64 의 두 가지 문법

같은 명령어를 두 가지로 적는다. 리눅스 도구(gcc, objdump, GNU as)의 기본은 AT&T 문법이다.

| | AT&T | Intel |
|---|---|---|
| 피연산자 순서 | `원본, 목적지` | `목적지, 원본` |
| 레지스터 | `%rax` | `rax` |
| 즉시값 | `$10` | `10` |
| 메모리 | `8(%rdi)` | `[rdi+8]` |
| 크기 | 접미사 `q`(8B) `l`(4B) `w` `b` | `QWORD PTR` 등 |

`addq %rsi, %rax` 는 AT&T 로 "rax = rax + rsi" 다. `objdump -M intel` 이나 `gcc -masm=intel` 로 Intel 문법을 볼 수 있다.

### 레지스터

x86-64 에는 64비트 범용 레지스터가 16개 있다. 이름은 역사의 흔적이다.

| 64비트 | 하위 32비트 | System V 호출 규약에서의 쓰임 |
|---|---|---|
| %rax | %eax | 반환값 |
| %rdi, %rsi, %rdx, %rcx, %r8, %r9 | %edi ... | 정수 인자 1~6번째 |
| %rsp | %esp | 스택 포인터 |
| %rbx, %rbp, %r12~%r15 | | 호출된 함수가 보존해야 하는 레지스터 |
| %rip | | 명령어 포인터(PC) |

32비트 레지스터(`%eax`)에 쓰면 상위 32비트가 0 으로 지워진다. 그래서 컴파일러는 `movq $0, %rax` 대신 더 짧은 `movl $0, %eax` 나 `xorl %eax, %eax` 를 즐겨 쓴다.

### 명령어 다섯 부류만 알면 읽힌다

| 부류 | 예 | 뜻 |
|---|---|---|
| 데이터 이동 | `movq 8(%rdi), %rax` | rax = *(rdi + 8) |
| 산술·논리 | `addq`, `subq`, `imulq`, `andq`, `xorl` | 결과를 목적지에 쓰고 플래그를 갱신 |
| 비교 | `cmpq $10, %rcx`, `testq %rdi, %rdi` | 뺄셈·AND 를 하되 결과는 버리고 플래그만 설정 |
| 분기 | `jmp`, `je`, `jne`, `jle`, `jg` | 플래그를 보고 PC 를 바꿈 |
| 호출 | `call`, `ret`, `push`, `pop` | 스택에 복귀 주소를 넣고 빼며 함수 이동 |

`leaq` 는 이름과 달리 메모리를 읽지 않는다. 주소 계산 회로를 빌려 `a + b*k + c` 꼴의 산술을 한 명령에 하는 용도로 자주 쓰인다.

### 반복문은 비교와 조건 분기다

고급 언어의 `for`, `while` 은 어셈블리에서 "비교 → 조건 분기 → 뒤로 점프" 로 바뀐다.

```
for (i = 1; i <= n; i++) s += i;

        i = 1
loop:   s += i
        i++
        if (i <= n) goto loop
```

## 직접 해 보기

### 1. 손으로 쓴 어셈블리 실행하기

x86-64 리눅스에서 GNU as 와 ld 로 확인했다. 1 부터 10 까지 더한 값을 프로세스 종료 코드로 돌려준다.

```
# sum.s — 1 부터 10 까지 더해 종료 코드로 돌려준다 (x86-64 리눅스, AT&T 문법)
        .globl _start
        .text
_start:
        movq    $0, %rax          # rax = 합계 = 0
        movq    $1, %rcx          # rcx = i = 1
.Lloop:
        addq    %rcx, %rax        # 합계 += i
        incq    %rcx              # i++
        cmpq    $10, %rcx         # i 와 10 비교
        jle     .Lloop            # i <= 10 이면 반복
        movq    %rax, %rdi        # 종료 코드 = 합계
        movq    $60, %rax         # 시스템 콜 번호 60 = exit
        syscall
```

```bash
as sum.s -o sum.o && ld sum.o -o sum && ./sum; echo "exit=$?"
```

```
exit=55
```

C 라이브러리 없이 커널에 직접 `exit` 시스템 콜을 했다. 종료 코드는 하위 8비트만 전달되므로 255 를 넘는 합은 이 방법으로 볼 수 없다.

### 2. 컴파일러의 출력 읽기

```c
long sum_to(long n) {
    long s = 0;
    for (long i = 1; i <= n; i++)
        s += i;
    return s;
}
```

```bash
gcc -O1 -fcf-protection=none -S sumc.c -o -
```

gcc 13.3 의 출력에서 지시어를 걸러 낸 결과다. 주석은 덧붙였다.

```
sum_to:
	testq	%rdi, %rdi      # n 과 n 을 AND → n <= 0 인지 플래그로 확인
	jle	.L4             # n <= 0 이면 0 반환하러
	addq	$1, %rdi        # rdi = n + 1  (반복 종료값)
	movl	$1, %eax        # i = 1
	movl	$0, %edx        # s = 0
.L3:
	addq	%rax, %rdx      # s += i
	addq	$1, %rax        # i++
	cmpq	%rdi, %rax      # i 와 n+1 비교
	jne	.L3             # 다르면 반복
.L1:
	movq	%rdx, %rax      # 반환값 = s
	ret
.L4:
	movl	$0, %edx
	jmp	.L1
```

인자 n 은 `%rdi` 로 들어오고 반환값은 `%rax` 로 나간다. 호출 규약 표 그대로다. `i <= n` 을 `i != n+1` 로 바꾼 것도 보인다. `-O2` 로 올리면 gcc 는 한 번에 두 항씩 더하도록 반복문을 펼치고 `leaq` 로 덧셈을 합친다. 같은 C 코드라도 최적화 단계마다 기계어가 달라진다.

### 3. 비교: 파이썬 바이트코드

파이썬도 내부에 자신만의 "어셈블리" 를 갖고 있다. `dis` 모듈로 볼 수 있다(python3.12).

```python
import dis
def sum_to(n):
    s = 0
    for i in range(1, n + 1):
        s += i
    return s
dis.dis(sum_to)
```

출력 일부:

```
        >>   36 FOR_ITER                 7 (to 54)
             40 STORE_FAST               2 (i)
             42 LOAD_FAST                1 (s)
             44 LOAD_FAST                2 (i)
             46 BINARY_OP               13 (+=)
             50 STORE_FAST               1 (s)
             52 JUMP_BACKWARD            9 (to 36)
```

구조는 같다. 반복 시작, 값 적재, 덧셈, 저장, 뒤로 점프. 차이는 이 명령어를 CPU 가 아니라 파이썬 인터프리터 루프가 하나씩 해석한다는 점이다. 바이트코드 한 개를 처리하는 데 기계어 명령 여러 개가 필요하므로 같은 반복문이 C 보다 훨씬 느리다. 바이트코드 형식은 파이썬 버전마다 바뀔 수 있다.

## 현업에서는

- **크래시 분석**: 세그멘테이션 폴트 로그의 `ip` 주소를 `objdump -d` 출력에서 찾으면 어떤 명령어가 어떤 레지스터 값으로 메모리를 읽다 죽었는지 알 수 있다.
- **성능 튜닝**: `perf annotate` 는 핫스팟 함수의 어셈블리에 명령어별 샘플 비율을 붙여 준다. 반복문 안에 예상하지 못한 함수 호출이나 메모리 적재가 있는지 보는 데 쓴다.
- **컴파일러 확인**: 브라우저에서 여러 컴파일러의 출력을 나란히 보여 주는 Compiler Explorer 같은 도구로 "이 코드가 벡터화됐나", "이 분기가 사라졌나" 를 빠르게 확인한다.
- **ABI 문제**: C 확장 모듈이나 FFI 바인딩에서 인자가 엉뚱하게 넘어가면 호출 규약(레지스터 순서, 구조체 전달 방식) 불일치를 의심한다. x86-64 psABI 문서가 기준이다.

## 확인 문제

1. AT&T 문법 `movq 16(%rbx), %rax` 를 C 식으로 써라.
2. System V x86-64 호출 규약에서 첫 번째 정수 인자와 반환값은 어떤 레지스터에 있는가.
3. `cmpq` 와 `subq` 의 차이는.
4. `xorl %eax, %eax` 가 하는 일은 무엇이고 왜 자주 보이는가.

### 풀이

1. `rax = *(long *)(rbx + 16);`
2. 첫 인자 `%rdi`, 반환값 `%rax`.
3. 둘 다 뺄셈을 해 플래그를 세우지만 `cmpq` 는 결과를 레지스터에 쓰지 않는다.
4. rax 를 0 으로 만든다. 같은 값끼리 XOR 하면 0 이고, 32비트 쓰기가 상위 비트도 지우며, 즉시값이 없어 명령어가 짧기 때문이다.

## 더 읽을거리 (References)

- GNU Binutils, [Using as — the GNU Assembler](https://sourceware.org/binutils/docs/as/)
- [System V Application Binary Interface — x86-64 psABI](https://gitlab.com/x86-psABIs/x86-64-ABI)
- GCC 공식 문서, [Options That Control Optimization](https://gcc.gnu.org/onlinedocs/gcc/Optimize-Options.html)
- Python 공식 문서, [dis — Disassembler for Python bytecode](https://docs.python.org/3/library/dis.html)
