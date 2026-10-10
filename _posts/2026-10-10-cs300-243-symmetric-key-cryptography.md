---
layout: post
title: "[CS300 #243] 대칭키 암호 — 같은 키로 잠그고 여는 일의 세부 사항"
date: 2026-10-10 22:03:00 +0900
categories: [cs]
tags: [cs300, security, cryptography, aes, aead]
---

컴퓨터공학 300 주제 시리즈의 243번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

대칭키 암호는 같은 비밀 키로 암호화와 복호화를 하는 방식이고, 현대 실무에서 쓸 형태는 사실상 하나다 — **AES-GCM 이나 ChaCha20-Poly1305 같은 인증 암호(AEAD)를, 논스를 절대 재사용하지 않고** 쓰는 것.

## 왜 필요한가

디스크 암호화, TLS 로 오가는 웹 트래픽, 데이터베이스 컬럼 암호화, 백업 파일 보호. 대량의 데이터를 실제로 감싸는 건 거의 언제나 대칭키 암호다. 공개키 암호는 느려서 키를 주고받는 데만 쓰고, 본문은 대칭키로 처리한다.

문제는 알고리즘이 아니라 **사용법**에서 터진다. AES 자체는 안전한데 ECB 모드로 쓰거나, 논스를 재사용하거나, 암호화만 하고 무결성 검사를 빼서 깨지는 사고가 반복된다. 그래서 "AES 를 쓴다" 는 말은 안전을 보장하지 않는다. 어떤 모드로, 어떤 논스 정책으로, 키를 어디에 두는지까지 말해야 한다.

## 핵심 개념

### 블록 암호와 스트림 암호

- **블록 암호**: 고정 길이 블록을 키에 따라 다른 블록으로 바꾸는 순열이다. AES(FIPS 197)는 블록 128비트, 키 128·192·256비트를 쓴다.
- **스트림 암호**: 키와 논스로 의사난수 키스트림을 만들고 평문과 XOR 한다. ChaCha20 이 대표다.

블록 암호 하나로는 16바이트밖에 못 다룬다. 긴 데이터를 처리하는 방법이 **운용 모드**다.

### 운용 모드

| 모드 | 동작 | 문제점 | 판단 |
|---|---|---|---|
| ECB | 블록마다 독립 암호화 | 같은 평문 블록 → 같은 암호문 블록. 패턴이 그대로 샌다 | 쓰지 않는다 |
| CBC | 앞 암호문 블록을 다음 평문에 XOR, 시작은 IV | IV 예측 가능하면 위험, 패딩 오라클 공격, 무결성 없음 | 레거시 |
| CTR | 카운터를 암호화해 키스트림 생성 | 무결성 없음, 논스 재사용 시 붕괴 | 단독 사용 비권장 |
| GCM | CTR + GHASH 인증 태그 | 논스 재사용 시 기밀성과 무결성 모두 붕괴 | 표준 선택 |

### 왜 "암호화만" 은 부족한가

CTR 처럼 XOR 로 동작하는 방식은 공격자가 암호문의 비트를 뒤집으면 평문의 같은 위치 비트가 뒤집힌다. 내용을 몰라도 `amount=100` 을 `amount=900` 으로 바꿀 수 있다는 뜻이다. 기밀성만 지키고 무결성은 안 지킨다.

그래서 현대 암호는 **AEAD(Authenticated Encryption with Associated Data)** 를 쓴다. 암호화와 동시에 인증 태그를 만들고, 복호화 때 태그가 맞지 않으면 평문을 아예 내주지 않는다. "연관 데이터(AD)" 는 암호화하지 않지만 함께 인증하는 값이다. 헤더나 레코드 ID 를 여기 넣으면 암호문을 다른 레코드에 옮겨 붙이는 공격을 막는다.

TLS 1.3(RFC 8446)은 아예 AEAD 암호 스위트만 허용한다.

### 대표 AEAD 두 가지

| 항목 | AES-GCM | ChaCha20-Poly1305 |
|---|---|---|
| 규격 | NIST SP 800-38D | RFC 8439 |
| 키 | 128 또는 256비트 | 256비트 |
| 논스 | 96비트 권장 | 96비트 |
| 태그 | 최대 128비트(보통 128) | 128비트 |
| 장점 | AES 하드웨어 명령이 있는 CPU 에서 빠름 | 하드웨어 가속 없는 환경에서도 빠르고 상수 시간 구현이 쉬움 |

### 논스(nonce)는 "한 번만"

논스는 비밀일 필요가 없지만 **같은 키로 두 번 쓰면 안 된다**. GCM 에서 논스를 재사용하면 두 암호문의 XOR 이 두 평문의 XOR 이 되고, 인증 키까지 유도될 수 있어 위조가 가능해진다. 논스를 무작위로 뽑는 경우 SP 800-38D 는 한 키로 암호화하는 횟수에 상한을 둔다. 메시지 수가 많으면 키를 주기적으로 교체하거나 카운터 기반 논스를 쓴다.

### 키 관리가 진짜 문제다

대칭키 암호의 근본 약점은 **키 배송**이다. 양쪽이 같은 비밀을 미리 가져야 한다. n 명이 서로 비밀 통신하려면 n(n-1)/2 개의 키가 필요하다. 이 문제를 푸는 게 다음 글의 공개키 암호다. 실무에서는 키를 코드나 환경 변수에 박지 않고 KMS·HSM·시크릿 관리 도구에 두며, 데이터 키를 마스터 키로 다시 감싸는 **봉투 암호화(envelope encryption)** 를 흔히 쓴다.

## 직접 해 보기

파이썬 `cryptography` 패키지로 세 가지를 확인한다. (1) ECB 의 패턴 누출 (2) GCM 의 변조 감지 (3) 논스 재사용의 결과. 3번은 **하면 안 되는 예**를 보여 주기 위한 것이다.

```python
import os
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag

key = os.urandom(32)                      # AES-256 키
block = b"ATTACK AT DAWN!!"               # 정확히 16바이트 = AES 블록 1개
pt = block * 4

# 1) ECB: 같은 평문 블록 -> 같은 암호문 블록
enc = Cipher(algorithms.AES(key), modes.ECB()).encryptor()
ct = enc.update(pt) + enc.finalize()
blocks = [ct[i:i+16] for i in range(0, len(ct), 16)]
print("ECB 서로 다른 암호문 블록 수:", len(set(blocks)), "/", len(blocks))

# 2) GCM: 블록이 모두 다르고, 변조를 감지한다
aes = AESGCM(key)
nonce = os.urandom(12)                    # 96비트 논스
ct = aes.encrypt(nonce, pt, b"header-v1") # 마지막 16바이트가 인증 태그
blocks = [ct[i:i+16] for i in range(0, len(pt), 16)]
print("GCM 서로 다른 암호문 블록 수:", len(set(blocks)), "/", len(blocks))
print("복호화:", aes.decrypt(nonce, ct, b"header-v1")[:16])
bad = bytearray(ct); bad[0] ^= 1
try:
    aes.decrypt(nonce, bytes(bad), b"header-v1")
except InvalidTag:
    print("1비트 변조 -> InvalidTag")

# 3) 논스 재사용(금지): 두 암호문 XOR = 두 평문 XOR
p1, p2 = b"salary=3000000KRW", b"salary=9000000KRW"
c1 = aes.encrypt(nonce, p1, None)
c2 = aes.encrypt(nonce, p2, None)
x = bytes(a ^ b for a, b in zip(c1, c2))
print("c1^c2 == p1^p2 :", x[:len(p1)] == bytes(a ^ b for a, b in zip(p1, p2)))
```

실행 결과(cryptography 41, Python 3.12):

```
ECB 서로 다른 암호문 블록 수: 1 / 4
GCM 서로 다른 암호문 블록 수: 4 / 4
복호화: b'ATTACK AT DAWN!!'
1비트 변조 -> InvalidTag
c1^c2 == p1^p2 : True
```

마지막 줄의 의미가 크다. 공격자가 p1 을 안다면(예: 알려진 양식) p2 를 바로 계산한다. 논스 관리 실수 하나로 AES-256 의 강도가 의미를 잃는다.

## 현업에서는

- **"직접 조립하지 않는다"**: CBC 와 HMAC 을 손으로 엮거나 IV 를 직접 관리하는 코드는 리뷰에서 가장 먼저 의심받는다. 언어별 고수준 API(`AESGCM`, libsodium 의 secretbox, Go 의 `crypto/cipher.AEAD`)를 쓴다.
- **쿠버네티스 시크릿 암호화**: API 서버의 [저장 시 암호화 설정](https://kubernetes.io/docs/tasks/administer-cluster/encrypt-data/)은 `aescbc`, `aesgcm`, `secretbox`, `kms` 같은 제공자를 고르게 되어 있다. 공식 문서의 표는 `aescbc` 를 패딩 오라클 취약성 때문에 비권장으로, 무작위 논스를 쓰는 `aesgcm` 을 "20만 번 쓰기마다 키 교체 필요" 로 적고 있다. 논스 상한 문제가 실제 운영 문서에 드러나는 예다.
- **키는 코드 밖에**: 깃 저장소에 키를 커밋하는 사고는 지금도 흔하다. 시크릿 스캐너를 CI 에 걸고, 유출된 키는 "지웠다" 가 아니라 "교체했다" 로 처리한다.
- **성능**: 최신 서버 CPU 는 AES 전용 명령을 가지고 있어 암호화 비용이 대개 병목이 아니다. "느려서 암호화 안 한다" 는 근거는 측정 후에만 쓴다.

## 확인 문제

1. ECB 모드가 안전하지 않은 이유를 한 문장으로 설명하라.
2. AES-CTR 로 암호화한 데이터에 무결성 문제가 있는 이유는?
3. AEAD 의 "연관 데이터(AD)" 는 암호화되는가? 왜 쓰는가?
4. GCM 에서 같은 키·같은 논스로 두 메시지를 암호화하면 어떤 일이 생기는가?

### 풀이

1. 같은 평문 블록이 항상 같은 암호문 블록이 되어 데이터의 반복 패턴이 그대로 드러난다.
2. 암호문 비트를 뒤집으면 평문 같은 위치가 그대로 뒤집히는데, 이를 감지할 장치가 없다.
3. 암호화되지 않는다. 다만 인증 태그 계산에 포함되므로 바뀌면 복호화가 실패한다. 헤더·레코드 ID 를 묶어 암호문을 다른 맥락으로 옮기는 공격을 막는다.
4. 두 암호문 XOR 이 두 평문 XOR 이 되어 기밀성이 깨지고, 인증 키 유도로 위조까지 가능해질 수 있다.

## 더 읽을거리 (References)

- NIST, [FIPS 197: Advanced Encryption Standard (AES)](https://csrc.nist.gov/pubs/fips/197/final)
- NIST, [SP 800-38D: Recommendation for Block Cipher Modes of Operation: GCM and GMAC](https://csrc.nist.gov/pubs/sp/800/38/d/final)
- IETF, [RFC 8439: ChaCha20 and Poly1305 for IETF Protocols](https://www.rfc-editor.org/rfc/rfc8439)
- pyca, [cryptography 공식 문서](https://cryptography.io/en/latest/)
