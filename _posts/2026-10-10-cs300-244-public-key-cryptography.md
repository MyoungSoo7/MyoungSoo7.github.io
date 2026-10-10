---
layout: post
title: "[CS300 #244] 공개키 암호 — 만나지 않고도 비밀을 나누는 방법"
date: 2026-10-10 22:04:00 +0900
categories: [cs]
tags: [cs300, security, cryptography, rsa, ecdh]
---

컴퓨터공학 300 주제 시리즈의 244번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

공개키 암호는 공개해도 되는 키와 숨겨야 하는 키를 짝으로 쓰는 방식이며, 실무에서는 데이터를 직접 암호화하기보다 **키 합의(ECDH)와 전자서명**에 쓰고 본문은 대칭키로 처리하는 하이브리드 구조로 쓴다.

## 왜 필요한가

앞 글에서 본 대칭키 암호는 빠르고 튼튼하지만 양쪽이 같은 키를 미리 가져야 한다. 처음 접속하는 웹사이트와 내가 미리 비밀을 나눴을 리 없다. n 명이 서로 통신하려면 키가 n(n-1)/2 개 필요하다는 규모 문제도 있다.

1976년 Diffie 와 Hellman 은 공개 채널만으로 두 사람이 같은 비밀을 갖는 방법을 발표했고, 1978년 Rivest·Shamir·Adleman 은 공개키로 암호화하고 개인키로만 푸는 RSA 를 발표했다. 이 두 아이디어가 HTTPS, SSH, 코드 서명, 메신저의 종단 간 암호화를 가능하게 했다.

## 핵심 개념

### 한쪽으로만 쉬운 함수

공개키 암호는 "계산은 쉽고 역산은 어려운" 수학 문제에 기댄다.

| 체계 | 기반 문제 | 쉬운 방향 | 어려운 방향 |
|---|---|---|---|
| RSA | 소인수분해 | 두 큰 소수 곱하기 | 곱에서 두 소수 찾기 |
| Diffie-Hellman | 이산 로그 | g^a mod p 계산 | 결과에서 a 찾기 |
| 타원곡선(ECDH, ECDSA, EdDSA) | 타원곡선 이산 로그 | 점 a 배 하기 | 결과 점에서 a 찾기 |

RSA 에는 **트랩도어**가 있다. 소인수(p, q)를 아는 사람만 역산이 쉬워진다. 그 소인수에서 유도한 값이 개인키다.

### RSA 의 구조

```
키 생성: n = p·q,  φ = (p-1)(q-1),  e 선택,  d = e⁻¹ mod φ
공개키 (n, e)   개인키 d
암호화 c = m^e mod n      복호화 m = c^d mod n
서명   s = m^d mod n      검증   m == s^e mod n
```

위는 **교과서 RSA** 다. 그대로 쓰면 안 된다. 같은 평문은 같은 암호문이 되고(결정적), 곱셈 성질로 암호문을 조작할 수 있다. 실제로는 RFC 8017(PKCS #1)의 패딩을 반드시 쓴다. 암호화에는 **OAEP**, 서명에는 **PSS** 가 권장된다. 오래된 PKCS#1 v1.5 암호화 패딩은 패딩 오라클 공격의 역사가 길다.

### Diffie-Hellman 키 합의

```
공개: 군과 생성원 g
앨리스: 비밀 a, 공개 A = g^a      밥: 비밀 b, 공개 B = g^b
앨리스 계산: B^a = g^(ab)         밥 계산: A^b = g^(ab)
도청자: A, B 를 봐도 g^(ab) 를 못 구한다(계산적 DH 가정)
```

중요한 한계가 있다. DH 자체는 **상대가 누구인지 확인하지 않는다**. 중간자가 양쪽에 각각 키 교환을 하면 그대로 끼어든다. 그래서 키 교환 값에 서명을 붙이고, 그 서명 키를 인증서로 보증한다. 이것이 다음 두 글(전자서명, PKI)의 주제다.

### 타원곡선을 쓰는 이유

같은 안전성을 훨씬 짧은 키로 얻는다. NIST SP 800-57 Part 1 의 비교표에 따르면 대략 다음과 같다.

| 안전성(비트) | RSA/DH 모듈러스 | 타원곡선 키 |
|---|---|---|
| 112 | 2048 | 224~255 |
| 128 | 3072 | 256~383 |
| 192 | 7680 | 384~511 |
| 256 | 15360 | 512 이상 |

X25519(RFC 7748)는 256비트급 곡선 위의 DH 로, 구현 실수를 줄이도록 설계되어 TLS 1.3 과 SSH 에서 널리 쓰인다.

### 하이브리드 암호

공개키 연산은 대칭키보다 훨씬 느리고, RSA 는 한 번에 키 길이보다 짧은 데이터만 다룬다. 그래서 실제 프로토콜은 이렇게 짠다.

```
1) 공개키로 키 합의(ECDH) 또는 키 캡슐화(KEM)
2) 공유 비밀을 KDF(예: HKDF)로 늘려 대칭 키 생성
3) 본문은 AES-GCM / ChaCha20-Poly1305 로 암호화
```

TLS 1.3 의 핸드셰이크가 정확히 이 구조다. 또 매 세션마다 새 임시 키(ephemeral)를 쓰면 서버 개인키가 나중에 털려도 과거 트래픽을 못 푸는 **전방 비밀성(forward secrecy)** 을 얻는다.

### 양자 컴퓨터와 PQC

충분히 큰 양자 컴퓨터가 생기면 Shor 알고리즘으로 소인수분해와 이산 로그가 풀린다. 그래서 NIST 는 2024년 격자 기반 키 캡슐화 ML-KEM(FIPS 203)과 서명 ML-DSA(FIPS 204)를 표준으로 발표했다. "지금 저장해 두었다가 나중에 해독" 하는 위협 때문에 키 합의부터 기존 방식과 PQC 를 섞는 하이브리드 전환이 진행되고 있다.

## 직접 해 보기

두 부분이다. (1) 작은 수로 교과서 RSA 를 손으로 돌려 수식을 확인한다(실전 금지). (2) `cryptography` 패키지로 X25519 키 합의 → HKDF → AES-GCM 의 하이브리드 뼈대를 만든다.

```python
# (1) 교과서 RSA — 원리 확인용
p, q = 61, 53
n, phi = p * q, (p - 1) * (q - 1)
e = 17
d = pow(e, -1, phi)               # e*d ≡ 1 (mod phi)
m = 65
c = pow(m, e, n)
print(f"n={n}, d={d}, 암호문={c}, 복호={pow(c, d, n)}")

# (2) X25519 + HKDF + AES-GCM
import os
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

alice, bob = X25519PrivateKey.generate(), X25519PrivateKey.generate()
s_a = alice.exchange(bob.public_key())
s_b = bob.exchange(alice.public_key())
print("공유 비밀 일치:", s_a == s_b, len(s_a), "바이트")

def derive(shared):
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=None,
                info=b"cs300 demo v1").derive(shared)

k = derive(s_a)
nonce = os.urandom(12)
ct = AESGCM(k).encrypt(nonce, b"hello bob", None)
print("밥이 복호:", AESGCM(derive(s_b)).decrypt(nonce, ct, None))
```

실행 결과(Python 3.12, cryptography 41):

```
n=3233, d=2753, 암호문=2790, 복호=65
공유 비밀 일치: True 32 바이트
밥이 복호: b'hello bob'
```

(`pow(e, -1, phi)` 로 모듈러 역원을 구하는 기능은 Python 3.8 부터 있다.) 공유 비밀을 그대로 AES 키로 쓰지 않고 HKDF 를 거치는 데 주목하자. DH 출력은 균일한 난수가 아니므로 KDF 로 정제하고, `info` 로 용도를 묶는다.

## 현업에서는

- **SSH 키**: `ssh-keygen -t ed25519` 가 흔한 기본값이 된 이유가 타원곡선의 짧은 키와 빠른 연산이다. 서버에 올라가는 건 공개키뿐이고 개인키는 내 노트북을 떠나지 않는다. 홈랩 노드 간 SSH 신뢰를 맺을 때도 같은 원리다.
- **TLS 설정 점검**: 서버가 임시 키 교환(ECDHE)만 허용하는지, RSA 키 전송 방식이 꺼져 있는지 본다. TLS 1.3 은 RSA 키 전송을 아예 없앴다.
- **RSA 를 직접 부르는 코드**: `RSA/ECB/PKCS1Padding` 같은 문자열이 보이면 리뷰 대상이다. 데이터 암호화가 목적이라면 대개 하이브리드 라이브러리(예: HPKE 구현)나 KMS 의 envelope 암호화로 바꾸는 게 맞다.
- **암호 민첩성**: PQC 전환을 앞두고 알고리즘 이름이 코드 곳곳에 박혀 있으면 교체가 어렵다. 알고리즘 선택을 설정·라이브러리 한 곳으로 모아 두는 설계가 중요해졌다.

## 확인 문제

1. 공개키 암호가 대칭키 암호의 어떤 문제를 해결하는가?
2. 교과서 RSA 를 그대로 쓰면 안 되는 이유 두 가지는?
3. Diffie-Hellman 만으로는 중간자 공격을 막을 수 없는 이유는?
4. 128비트 안전성을 원할 때 RSA 와 타원곡선 키 길이는 대략 얼마인가?
5. 전방 비밀성이란 무엇이며 어떻게 얻는가?

### 풀이

1. 사전에 비밀을 공유하지 않은 상대와 공개 채널만으로 키를 맞추는 키 배송 문제와, 키 개수가 사용자 수의 제곱으로 느는 규모 문제.
2. 결정적이라 같은 평문이 같은 암호문이 되고, 곱셈 성질로 암호문을 조작할 수 있다. OAEP·PSS 패딩을 써야 한다.
3. DH 는 상대의 신원을 확인하지 않는다. 중간자가 양쪽과 따로 키를 맞추면 구별할 수 없다. 서명과 인증서로 인증해야 한다.
4. RSA 3072비트, 타원곡선 256비트급(SP 800-57 기준).
5. 장기 개인키가 나중에 유출돼도 과거 세션을 해독할 수 없는 성질. 세션마다 임시 키로 키 합의(ECDHE)를 하고 사용 후 버린다.

## 더 읽을거리 (References)

- IETF, [RFC 8017: PKCS #1: RSA Cryptography Specifications Version 2.2](https://www.rfc-editor.org/rfc/rfc8017)
- IETF, [RFC 7748: Elliptic Curves for Security (X25519, X448)](https://www.rfc-editor.org/rfc/rfc7748)
- NIST, [SP 800-57 Part 1 Rev. 5: Recommendation for Key Management](https://csrc.nist.gov/pubs/sp/800/57/pt1/r5/final)
- NIST, [FIPS 203: Module-Lattice-Based Key-Encapsulation Mechanism Standard](https://csrc.nist.gov/pubs/fips/203/final)
- 논문: W. Diffie, M. Hellman, "New Directions in Cryptography", *IEEE Trans. Information Theory*, 1976. / R. Rivest, A. Shamir, L. Adleman, "A Method for Obtaining Digital Signatures and Public-Key Cryptosystems", *CACM*, 1978.
