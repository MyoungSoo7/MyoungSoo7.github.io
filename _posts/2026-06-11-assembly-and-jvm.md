---
layout: post
title: "어셈블리어와 JVM — *추상의 *두 층 사이* 의 *상관 관계 와 영향도*"
date: 2026-06-11 11:15:00 +0900
categories: [backend, jvm, performance, fundamentals]
tags: [assembly, jvm, jit, bytecode, performance, compiler, java, native]
---

> *어셈블리어* 는 *모든 코드 의 *바닥*. *JVM* 은 *그 바닥 위에 *세워진 *추상의 *층*.
> 둘은 *멀리 떨어져 *보인다*. 그러나 *실 행 순간 * 에는 *서로 *닿는다*.
> 그 *닿는 지점* 을 *알면* — *Java 코드 의 *성능 의 비밀* 이 *보인다*.

---

## TL;DR

| 항목 | 어셈블리어 | JVM |
|------|-----------|------|
| **위치** | *CPU 직 접 명령* | *바이트코드 가상 머신* |
| **추상 단계** | *0 단계 (machine 코드 의 *기호 표현)* | *2~3 단계 위* |
| **이식성** | *CPU 아키텍처 *종속* (x86, ARM) | *플랫폼 독립* |
| **속도** | *원리 상 *최고* | *JIT 후 *어셈블리 와 *근접* 가능 |
| **개발자 의 *접점*** | *직접 작성 *드문* | *바이트코드 가끔, *JIT 결과 보기* |
| **만나는 곳** | *JIT 결과* — *바이트코드 → 어셈블리* | *Hot path 의 *어셈블리 생성* |

*핵심 통찰* :

> *Java 의 *느림 / 빠름* 은 *결국 *JIT 가 *어떤 어셈블리 를 *만들었는가* 의 문제*.

---

## 1. *어셈블리어* — *machine 코드의 *기호 표현*

### 본질

어셈블리어는 *CPU 명령어 (machine code) 와 *1:1 대응*. *수 십 ~ 수 백 개* 의 *명령어 (instruction)* 가 *각 CPU 아키텍처 별로 *다르다*.

대표 :

- **x86-64** (Intel / AMD) — *수 천 개 명령어*, *CISC*, *legacy 가 *많음*
- **ARM64** — *수 백 개*, *RISC*, *모바일 / Apple Silicon / 임베디드 표준*
- **RISC-V** — *오픈 ISA*, *교육 / 신생 *플랫폼*

### 예 — *간단한 *덧셈*

```
; x86-64 어셈블리
mov rax, [a]    ; a 값을 *레지스터 rax 에 *복사*
mov rbx, [b]    ; b 를 rbx 에
add rax, rbx    ; rax = rax + rbx
mov [c], rax    ; 결과를 c 에 *저장*
```

각 줄이 *CPU 사이클 *1~3 개* 안에 *직접 실행*. *최소 단위 의 *명령*.

### *왜 *어셈블리 가 *중요한가*

대부분 개발자 는 *어셈블리를 *직접 안 쓴다*. 그래도 *왜* 알아야 하는가 :

1. ***디버깅 *최후 의 수단*** — *컴파일러 출력 의 어셈블리 를 *읽어야 *해결되는 *버그*. 메모리 정렬 / SIMD / 인라인 실패 등.
2. ***성능 *최적화*** — *왜 *이 코드 가 *예상보다 *느린지* — *어셈블리 차이*.
3. ***JIT 동작 이해*** — *JIT 가 *어떤 어셈블리 를 만드는지* 가 *성능 의 *전부*.
4. ***보안*** — *익스플로잇 / 패치 분석* 은 *어셈블리 가 *기본*.

---

## 2. **JVM** — *바이트코드의 *가상 머신*

### 본질

JVM (Java Virtual Machine) 의 *핵심 발상* :

> *"하드웨어 마다 다른 *machine 코드 가 아니라 *추상 *바이트코드* 로 *컴파일* 하자. 그러면 *어디서든 *돌릴 수 있다*."*

```
Java 소스
   ↓ (javac 컴파일)
바이트코드 (.class) — 가상의 *machine 코드*
   ↓ (JVM 실행)
JVM 이 *해석 (interpret) 또는 *JIT 컴파일*
   ↓ (JIT 후)
실제 CPU 의 어셈블리어 / machine 코드
   ↓
CPU 가 *실행*
```

### *바이트코드의 *형태*

```
// Java
int sum(int a, int b) {
  return a + b;
}

// 바이트코드 (javap -c)
iload_1      // 첫 인자 (a) 를 *operand stack 에 *push
iload_2      // b push
iadd         // 두 정수 더해서 push
ireturn      // stack top 반환
```

*스택 기반 가상 머신* — *레지스터 가 *명시 적 으로 *없고* 모든 연산이 *operand stack 위에서* 일어난다. *추상* 의 *명확함*.

### *JVM 의 *3 가지 *모드*

1. **Interpreter** — 바이트코드 *한 줄씩 *해석 *실행*. *느림*. *초기 실행*.
2. **C1 Compiler (Client)** — *간단한 최적화 + 빠른 JIT 컴파일*. *짧은 실행 시간*.
3. **C2 Compiler (Server)** — *깊은 최적화 + 느린 JIT 컴파일*. *긴 실행 시간 의 *hot path 용*.

→ JVM 은 *Tiered Compilation* — *처음엔 *interpret*, *자주 호출 되면 *C1*, *더 자주 면 *C2*. *점진적 최적화*.

---

## 3. **JIT** — *바이트코드 ↔ 어셈블리* 의 *다리*

### JIT 의 *순간*

JVM 이 *어떤 메서드 가 *수천 번 호출됨* 을 감지 :

```
1. *바이트코드 분석*
2. *최적화 적용* (인라인 / dead code 제거 / loop 변환)
3. *어셈블리어 생성* (target CPU 의 native code)
4. *machine 코드 *캐시 에 저장*
5. *다음 호출 부터 *바이트코드 대신 *machine 코드 직접 실행*
```

→ *JIT 후 의 성능* 이 *Java 의 *진짜 성능*. *대부분 *벤치 마크* 가 *warm-up* 단계를 두는 이유.

### JIT 의 *대표 최적화*

#### **Inlining**

```java
int square(int x) { return x * x; }
int sumOfSquares(int a, int b) {
  return square(a) + square(b);
}
```

JIT 가 *square 메서드 호출 을 *제거* 하고 *그대로 펼침* :

```
return a*a + b*b;  // 호출 비용 0
```

→ *함수 호출 의 비용 *완전 제거*. *최소한의 *최적화*.

#### **Escape Analysis**

```java
List<Integer> tmp = new ArrayList<>();
tmp.add(1);
tmp.add(2);
return tmp.get(0) + tmp.get(1);
```

*tmp 객체 가 *메서드 *밖으로 안 나간다* 를 *증명* 하면 — *힙 할당 *없이 *stack 에 *할당* 또는 *완전 제거*. *GC 부담 *0*.

#### **Loop Unrolling**

```java
for (int i = 0; i < 4; i++) { sum += arr[i]; }
```

JIT 가 *루프 펼침* :

```
sum += arr[0];
sum += arr[1];
sum += arr[2];
sum += arr[3];
```

→ *분기 예측 부담 ↓*. *명령 파이프라인 *최적화*.

#### **SIMD / Vectorization**

JIT 가 *Java 코드 의 *루프 를 *SIMD 명령* 으로 변환 :

```
// 원본
for (int i = 0; i < 8; i++) c[i] = a[i] + b[i];

// JIT 변환 (AVX2 사용 시)
vmovdqu ymm0, [a]
vpaddd  ymm0, ymm0, [b]
vmovdqu [c], ymm0
```

*8 개 정수 *한 번에 *덧셈*. *CPU 의 *벡터 명령 활용*. *최대 8배 빠름*.

→ *Java 가 *어셈블리어 직접 못 쓴다* 는 *옛 말*. *JIT 가 *AVX/NEON 까지 *활용*.

---

## 4. *AOT* (Ahead-of-Time) — *JIT 의 *대안*

### JIT 의 약점

- ***warm-up 시간*** — *처음 호출 은 *interpret 또는 C1*. *느림*. *짧은 작업* 엔 *불리*.
- ***메모리 사용*** — *JIT 컴파일러 자체 가 *메모리 + CPU* 소비.
- ***예측 어려움*** — *언제 *어떤 메서드 가 *컴파일 되는지* *비결정 적*.

### AOT 의 등장

**GraalVM Native Image** :

- *Java 코드 를 *빌드 시점 에 *machine 코드 로 *컴파일*
- *실행 시 *JIT 없음*
- *바이너리 단일 파일*
- *수 ms 안 *시작*

### 비교

| 항목 | JIT (HotSpot) | AOT (GraalVM Native) |
|------|----------------|------------------------|
| 시작 시간 | *수 초* | *수 ms* |
| 최고 성능 | *높음 (warm 후)* | *중간* |
| 메모리 | *큼* | *작음* |
| 빌드 시간 | *짧음* | *길음 (1~10분)* |
| Reflection | *모두 지원* | *런타임 등록 필요* |
| 적합 | *서버 long-running* | *CLI / 람다 / 컨테이너* |

→ *AWS Lambda / 마이크로서비스 / CLI* 는 *AOT (Native)* 강세. *대형 서버 모놀리식* 은 *JIT* 강세.

---

## 5. *둘 의 *상호 영향* — *어셈블리 ← JIT → JVM*

### *어셈블리어가 JVM 에 *준 영향*

- JVM 의 *바이트코드 명령어 가 *어셈블리어 발상 의 *추상화*
- *스택 기반 가상 머신* — *어셈블리어 의 *레지스터 / 스택* 의 *간소화*
- *JIT 컴파일 의 *최적화 패턴* — *전통적 *어셈블리 최적화* 기법 의 *자동화*

### *JVM 이 *어셈블리어 학습에 준 영향*

- ***대중 개발자 의 *어셈블리 학습 *부담 ↓*** — *Java 만 잘 짜면 *충분*. *어셈블리 는 *후순위*.
- ***추상의 양면성*** — *생산성 ↑* 이지만 *깊이 ↓*. *시스템 디버깅 *난도 가 *오히려 ↑* 되는 *부작용*.
- ***시스템 SW 와 *애플리케이션 의 *격차 가 *더 벌어 짐*** — *어셈블리 깊이 가 *희소 한 능력 이 됨*.

---

## 6. *어셈블리를 *알면 *JVM 이 *어떻게 *더 보이는가**

### 예 — *왜 *이 코드 가 *느린가* 의 *디버깅*

```java
public int sum(int[] arr) {
  int s = 0;
  for (int v : arr) {
    s = (s + v) % 1_000_000_007;  // <- *모듈로*
  }
  return s;
}
```

*벤치 마크 가 *예상보다 *2 배 느림*. *왜*?

JIT 결과 의 *어셈블리* 를 본다 (`-XX:+PrintAssembly`) :

```
... 
idiv   rcx        ; *나눗셈 명령 — *수십 사이클 *비용*
...
```

→ *모듈로 (%) 가 *나눗셈 명령* 으로 *직역*. *CPU 의 *가장 느린 명령 중 하나*.

해결책 — *Barrett reduction* 또는 *덧셈 후 한 번만 modulo* :

```java
long s = 0;
for (int v : arr) s += v;
return (int)(s % 1_000_000_007);  // *한 번만*
```

→ *나눗셈 1 번* 으로 *총 비용 *감소*. *2 배 *빨라짐*.

**어셈블리 안 보면 *원인 못 짚는다*. JIT 결과 의 *어셈블리 보기* 가 *진짜 *튜닝의 도구*.

### *유용한 *JVM 옵션*

```
-XX:+UnlockDiagnosticVMOptions
-XX:+PrintAssembly                # JIT 어셈블리 출력 (HSDIS 라이브러리 필요)
-XX:+PrintInlining                # 인라인 결과
-XX:+PrintCompilation             # 어떤 메서드 가 *언제 *컴파일 되었는지*
-Xlog:gc*                         # GC 로그
```

이 옵션 을 *직접 본 경험* 이 *JVM 깊이 의 *큰 도약*.

---

## 7. *어셈블리어를 *얼마나 *깊이* 알아야 하는가*

### *최소* — *7 가지 만 *알아도 *충분*

```
1. mov  — 데이터 이동
2. add / sub / mul / div  — 산술
3. cmp + je / jne / jl / jg  — 조건 분기
4. call / ret  — 함수 호출
5. push / pop  — 스택 조작
6. lea  — 주소 계산
7. xor  — 비트 연산 (clear 용도 도 있음)
```

→ 위 7 개 + *레지스터 (rax, rbx, rcx, rsi, rdi, rbp, rsp)* 의 *역할* 만 알아도 *JIT 출력 *대부분 *읽힘*.

### *중급* — *벡터 (SIMD) 명령*

```
mov  → movdqu / vmovdqu  (벡터 16/32 바이트)
add  → paddd / vpaddd
mul  → pmulld / vpmulld
```

*hot path 의 *벡터화 결과* 를 *확인* 하는 정도.

### *깊이* — *마이크로 아키텍처*

- *Pipeline / Out-of-order execution*
- *Branch prediction / cache hierarchy*
- *Memory ordering / atomic operations*
- *NUMA*

여기까지는 *시스템 SW 전공 *영역*. *백엔드 일반 *개발자엔 *필수 는 아님*.

---

## 8. *시간 투자 *권장*

### *Java 개발자 *3~5 년차*

- *바이트코드 보기* (`javap -c`) — *15 분 만에 *기본 *눈에 익음*
- *JIT 옵션 활용* — *PrintCompilation 한 번 돌려보기*
- *JMH (Java Microbenchmark Harness)* — *벤치 마크 의 표준*

### *7 년차 +*

- *PrintAssembly + HSDIS* 설치 — *JIT 어셈블리 직접 보기*
- *Code Tools / JITWatch* — *시각화 도구*
- *벤치 마크 의 *어셈블리 차이* 로 *최적화 *근거 마련*

### *깊이 가는 사람*

- *Agner Fog 의 *Optimization Manuals* — *CPU 명령 별 latency / throughput*
- *Intel / AMD / ARM 의 *공식 *Reference Manual*
- *flame graph + perf* 와 함께

---

## 9. *현장 *경험* — *어셈블리 한 번 가 *팀의 *답 을 *바꾼 *순간*

본인이 *7 년 일하며 *어셈블리 를 *진짜 본 *순간 *3 가지* :

### 9.1. *DB JDBC driver 의 *느린 직렬화*

원인 — *JSON 직렬화 가 *string concat 사용 → *CharArray 의 *반복 복사*. JIT 가 *이 패턴 못 최적화*. 해결 — *StringBuilder + 사전 크기 설정* → *어셈블리 *간결화* → *3 배 빠름*.

### 9.2. *Spring Boot 컨트롤러 의 *예상 외 *지연*

원인 — *Reflection 호출 이 *인라인 안 됨*. JIT 의 *deoptimization* 가 *반복*. 해결 — *Method Handle + LambdaMetafactory* → *인라인 가능* → *p99 -30%*.

### 9.3. *대용량 *for loop 의 *Auto-vectorization 실패*

원인 — *조건문 (if) 이 *루프 안* 에 *있음 → JIT 가 *SIMD 변환 못 함*. 해결 — *조건 분리 후 *두 개 루프* → *SIMD 활성* → *2 배 빠름*.

이 세 경우 모두 *어셈블리 안 봤으면 *원인 추측만* 했을 것*. *어셈블리 본 후 *명확한 *근거* 로 *해결*.

---

## 10. *어셈블리 ≠ *과거*, JIT ≠ *블랙박스*

### *흔한 *오해*

> *"어셈블리 는 *옛 *지식*. 지금은 *고급 언어 만 쓰면 *됨*."*

→ *완전한 *오해*. *Java / Kotlin / Go / Rust 의 *최고 성능* 은 *결국 *어셈블리 의 *질* 에서 나옴*. *현대 일수록 *깊이 차이 가 *더 *결정적*.

> *"JIT 가 *알아서 *최적화 함*. *몰라도 *됨*."*

→ *JIT 가 *항상 *완벽한 *아님*. *특정 패턴* 은 *최적화 못 한다*. *알아야 *피하거나 *유도 한다*.

### *진짜 *21 세기 의 *조합*

- *Java 의 *생산성 + JIT 의 *자동 최적화*
- *어셈블리 의 *이해 + 마이크로 아키텍처 직관*
- *측정 도구 (JMH + flame graph) 활용*

이 세 가지 의 *조합* 이 *현대 백엔드 의 *고급 *튜닝 능력*.

---

## 11. 마치며

> *어셈블리 와 JVM 은 *멀어 보이지만 *같은 *연속선 위의 *다른 점*. *그 연속을 *몸 에 *익히면* — *Java 의 *성능 의 *비밀* 이 *덮인 *베일* 을 *벗는다***.

3 줄 요약 :

1. **JIT 는 *바이트코드 ↔ 어셈블리* 의 *번역*** — *Java 의 *진짜 성능* 은 *그 번역 결과* 에 달림.
2. **어셈블리 7 개 명령 + 레지스터 만 알아도 *JIT 출력 *대부분 읽음*** — *진입 장벽 *생각보다 *낮음*.
3. **측정 → JIT 결과 분석 → 코드 변경** — *시니어 *튜닝 의 *표준 워크플로*.

학부 시절 *어셈블리 가 *지루* 했던 본인 *7 년 후 회고* :

> *"그때 *어셈블리 가 *지금 *백엔드 튜닝 의 *결정적 *근육* 이 *될 *줄 *몰랐다*."*

다음 글 — *JIT 의 *깊이* — Tiered Compilation / Deoptimization / OSR 의 *내부 동작*. 같은 시리즈 로 이어 집니다.

---

> 본 글은 *7년차 백엔드 *엔지니어 의 *JVM 운영 회고*. *어셈블리 깊이 는 *시스템 SW *전공 *대비* *얕다*. *그러나 *현장 *튜닝* 에 *결정적인 만큼 만* — *그 부분 만 *깊게* 보는 것* 도 *충분*.
