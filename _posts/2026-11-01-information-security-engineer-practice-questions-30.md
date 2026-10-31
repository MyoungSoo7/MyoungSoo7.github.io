---
title: "정보보안기사 학습 문제 30 — AES·GCM·해시와 암호 선택"
date: 2026-11-01 07:31:41 +0900
categories: [정보보안기사, 암호]
tags: [AES, GCM, SHA-256, CRYPTREC, 암호알고리즘]
---

이번 글의 세 문항은 공개 기출문제의 원문을 재현하지 않은 **창작 문제**다. 정답과 해설은 게시 시점에 확인한 CRYPTREC 공개 암호 목록과 연결된 NIST 표준 문서를 근거로 작성했다.

## 문제 1 — AES의 분류

### 문제
CRYPTREC의 현행 권고 암호 목록에 대한 설명으로 옳은 것은?

### 선택지
1. AES는 128비트 블록 암호로 분류되며 NIST FIPS 197을 참조한다.
2. AES는 일방향 해시 함수이며 복호화 키가 없다.
3. AES는 공개키 전자서명 알고리즘으로만 사용된다.
4. AES는 64비트 블록 암호로만 분류된다.

### 정답
**1번**

### 해설
CRYPTREC의 현행 암호 목록은 대칭키 암호의 128비트 블록 암호 항목에 AES를 두고 NIST FIPS 197을 사양으로 연결한다. AES는 대칭키 암호이므로 해시 함수나 공개키 서명 알고리즘과 분류가 다르다. [1]

### 오답 포인트
암호화와 해시를 혼동하지 않아야 한다. AES의 블록 크기와 키 길이를 같은 개념으로 외우거나, 대칭키 AES를 공개키 알고리즘으로 분류하면 오답이다.

### 출처 또는 검증 근거
[1] CRYPTREC, *Specifications of CRYPTREC Ciphers List*, 현행 권고 암호 목록, https://www.cryptrec.go.jp/en/method.html

## 문제 2 — GCM의 성격

### 문제
암호 운용 모드에 대한 설명으로 가장 적절한 것은?

### 선택지
1. GCM은 인증된 암호화 모드로 분류되며 NIST SP 800-38D와 연결된다.
2. GCM은 비밀번호를 저장하는 일방향 해시 함수다.
3. GCM은 키 교환을 위한 공개키 알고리즘이다.
4. GCM은 암호문 없이 무결성만 제공하는 로그 형식이다.

### 정답
**1번**

### 해설
CRYPTREC 사양 표는 GCM을 authenticated encryption modes, 즉 인증된 암호화 모드로 분류하고 NIST SP 800-38D를 참조한다. 따라서 기밀성뿐 아니라 암호화와 인증을 함께 고려하는 모드라는 점이 핵심이다. [1]

### 오답 포인트
GCM을 해시나 키 교환 알고리즘으로 외우면 안 된다. 실제 운용에서는 nonce 재사용 같은 모드별 조건도 별도로 관리해야 하며, 모드 선택만으로 키 관리가 끝나지 않는다.

### 출처 또는 검증 근거
[1] CRYPTREC, *Specifications of CRYPTREC Ciphers List*, authenticated encryption modes 항목, https://www.cryptrec.go.jp/en/method.html

## 문제 3 — 해시 함수와 용도

### 문제
CRYPTREC 현행 목록의 해시 함수 항목에 관한 설명으로 옳은 것은?

### 선택지
1. SHA-256·SHA-384·SHA-512 등이 해시 함수 항목에 포함되며 NIST FIPS 180-4를 참조한다.
2. SHA-256은 항상 원문을 복원할 수 있는 대칭키 복호화 알고리즘이다.
3. 해시 함수는 공개키 개인키 쌍을 사용해 세션을 협상한다.
4. SHA-1만 현행 권고 목록의 유일한 해시 함수다.

### 정답
**1번**

### 해설
CRYPTREC 페이지는 현행 권고 암호 목록의 해시 함수로 SHA-256, SHA-384, SHA-512, SHA-512/256 등을 열거하고 NIST FIPS 180-4를 사양으로 제시한다. 해시는 일반적으로 고정 길이 다이제스트를 계산하는 함수이며 대칭키 복호화와 같은 개념이 아니다. [1]

### 오답 포인트
“암호화”라는 넓은 표현만 보고 해시를 복호화 가능한 암호문으로 이해하면 안 된다. 또한 목록의 현행 권고 항목과 모니터링 항목을 섞어 암기하지 않도록 분류를 확인해야 한다.

### 출처 또는 검증 근거
[1] CRYPTREC, *Specifications of CRYPTREC Ciphers List*, hash functions 항목, https://www.cryptrec.go.jp/en/method.html
