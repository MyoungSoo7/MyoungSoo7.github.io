---
layout: post
title: "[CS300 #246] 전자서명과 인증서 — 누가 만들었는지를 수학으로 증명한다"
date: 2026-10-10 22:06:00 +0900
categories: [cs]
tags: [cs300, security, digital-signature, x509, ed25519]
---

컴퓨터공학 300 주제 시리즈의 246번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

전자서명은 개인키로만 만들고 공개키로 누구나 검증할 수 있는 값이며, 인증서는 "이 공개키는 이 이름의 것" 이라는 주장에 제3자가 서명한 문서다.

## 왜 필요한가

앞 글에서 MAC 은 키를 공유하므로 제3자에게 "누가 만들었다" 를 증명하지 못한다고 했다. 소프트웨어 업데이트를 내려받는 수백만 대의 기기와 개발사가 모두 같은 비밀 키를 나눠 가질 수는 없다. 필요한 건 **만드는 능력은 한 명만, 확인하는 능력은 모두에게** 주는 장치다. 그게 전자서명이다.

그런데 서명을 검증하려면 공개키가 필요하고, 그 공개키가 진짜 그 회사의 것인지 또 알아야 한다. 웹사이트가 내미는 공개키를 그대로 믿으면 중간자가 자기 공개키를 내밀어도 모른다. 이 "공개키의 주인 확인" 문제를 푸는 게 인증서다.

## 핵심 개념

### 서명의 세 가지 연산

```
KeyGen() -> (개인키 sk, 공개키 pk)
Sign(sk, m) -> σ
Verify(pk, m, σ) -> 참/거짓
```

보안 목표는 **존재적 위조 불가(EUF-CMA)** 다. 공격자가 원하는 메시지들의 서명을 얼마든지 받아 봐도, 새 메시지에 대한 유효 서명은 만들 수 없어야 한다.

서명이 주는 것: 무결성, 진정성, **부인 방지**. 개인키를 가진 사람만 만들 수 있으므로 서명자는 나중에 부인하기 어렵다(물론 개인키가 유출되지 않았다는 전제다).

### 해시 후 서명

서명 알고리즘은 긴 메시지를 직접 다루지 않는다. 메시지를 해시한 뒤 그 다이제스트에 서명한다. 따라서 **서명의 안전성은 해시의 충돌 저항성에 기댄다**. 충돌 쌍 (m1, m2) 를 만들 수 있으면 무해한 m1 에 서명받고 m2 에 붙여 쓸 수 있다. MD5·SHA-1 서명 인증서가 퇴출된 이유다.

### 표준 서명 알고리즘

FIPS 186-5 는 세 계열을 승인한다.

| 알고리즘 | 기반 | 특징 |
|---|---|---|
| RSA (PKCS#1 v1.5, PSS) | 소인수분해 | 검증이 빠르고 호환성이 넓다. 키·서명이 크다 |
| ECDSA | 타원곡선 | 키가 작다. **서명마다 쓰는 난수 k 가 새면 개인키가 복원된다** |
| EdDSA (Ed25519, Ed448) | 에드워즈 곡선 | 결정적 서명이라 난수 실수 위험이 없다. RFC 8032 |

ECDSA 의 난수 문제는 유명하다. 두 서명에 같은 k 를 쓰면 간단한 연립식으로 개인키가 나온다. 실제 제품에서 이 실수로 서명 키가 유출된 사례도 있다. 그래서 RFC 6979 의 결정적 k 생성이나 EdDSA 를 쓴다.

### X.509 인증서의 구조

RFC 5280 이 정의하는 인증서는 세 부분이다.

```
Certificate
├─ tbsCertificate        ← 서명 대상 본문
│   ├─ version, serialNumber
│   ├─ signature (알고리즘)
│   ├─ issuer            ← 누가 서명했나
│   ├─ validity          ← notBefore ~ notAfter
│   ├─ subject           ← 누구의 키인가
│   ├─ subjectPublicKeyInfo  ← 공개키 자체
│   └─ extensions
│       ├─ subjectAltName      (도메인 이름들)
│       ├─ basicConstraints    (CA 인가?)
│       ├─ keyUsage / extKeyUsage (용도 제한)
│       └─ ...
├─ signatureAlgorithm
└─ signatureValue        ← 발급자 개인키로 tbsCertificate 에 서명한 값
```

요점: 인증서는 **공개키 + 신원 + 기간 + 용도** 를 묶어 **발급자가 서명**한 것이다. 서명 덕분에 한 바이트라도 바꾸면 검증이 실패한다.

### 이름 확인은 SAN 으로

TLS 에서 "이 인증서가 접속한 도메인의 것인가" 는 subjectAltName 의 DNS 이름으로 판단한다. RFC 9525 는 서비스 식별에 Common Name(CN)을 쓰면 안 된다고 명시한다. 오래된 튜토리얼처럼 CN 에만 도메인을 넣은 인증서는 현대 클라이언트에서 거부된다.

### 서명 검증이 끝이 아니다

인증서 서명이 맞아도 다음을 모두 확인해야 한다.

1. 발급자를 내가 신뢰하는가(체인이 신뢰 루트까지 닿는가)
2. 현재 시각이 유효 기간 안인가
3. 폐기되지 않았는가
4. 이름(SAN)이 일치하는가
5. 용도(keyUsage, extKeyUsage, basicConstraints)가 맞는가

1번과 3번이 다음 글의 PKI 주제다.

## 직접 해 보기

`cryptography` 패키지로 Ed25519 서명을 만들고, 타원곡선 키로 자체 서명 인증서를 만든 뒤 필드를 읽어 본다.

```python
import datetime
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, ed25519
from cryptography.exceptions import InvalidSignature

# 1) Ed25519 서명과 검증
sk = ed25519.Ed25519PrivateKey.generate()
pk = sk.public_key()
doc = b"release v1.2.3 sha256=..."
sig = sk.sign(doc)
print("서명 길이:", len(sig), "바이트")
pk.verify(sig, doc); print("원본 검증: OK")
try:
    pk.verify(sig, doc.replace(b"1.2.3", b"1.2.4"))
except InvalidSignature:
    print("변조 검증: InvalidSignature")

# 2) 자체 서명 인증서
key = ec.generate_private_key(ec.SECP256R1())
name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "demo.example")])
now = datetime.datetime.now(datetime.timezone.utc)
cert = (x509.CertificateBuilder()
        .subject_name(name).issuer_name(name)       # 자체 서명: 주체 = 발급자
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now).not_valid_after(now + datetime.timedelta(days=30))
        .add_extension(x509.SubjectAlternativeName([x509.DNSName("demo.example")]), critical=False)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .sign(key, hashes.SHA256()))
print("주체:", cert.subject.rfc4514_string())
print("SAN:", cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value.get_values_for_type(x509.DNSName))
print("서명 해시:", cert.signature_hash_algorithm.name)
cert.verify_directly_issued_by(cert); print("자기 서명 검증: OK")
```

실행 결과(Python 3.12, cryptography 41):

```
서명 길이: 64 바이트
원본 검증: OK
변조 검증: InvalidSignature
주체: CN=demo.example
SAN: ['demo.example']
서명 해시: sha256
자기 서명 검증: OK
```

자체 서명 인증서는 **서명이 수학적으로 맞을 뿐** 아무도 보증하지 않는다. 브라우저가 경고를 띄우는 이유다. "서명이 유효하다" 와 "믿을 수 있다" 는 다르다.

## 현업에서는

- **인증서 만료 장애**: 서명·체인은 멀쩡한데 notAfter 가 지나 서비스가 멈추는 사고가 가장 흔하다. 만료 30일·7일 전 알림을 모니터링에 넣는다. 쿠버네티스에서는 cert-manager 가 ACME 로 자동 갱신하는 구성이 일반적이다.
- **쿠버네티스 내부 인증서**: API 서버, kubelet, etcd 는 서로 클라이언트 인증서로 신원을 확인한다. k3s 같은 배포판은 내부 인증서를 자동 발급하고 기간이 다가오면 재시작 때 갱신한다. 오래 켜 둔 클러스터에서 "갑자기 kubectl 이 인증 실패" 는 대개 여기서 시작한다.
- **코드·아티팩트 서명**: 릴리스 바이너리와 컨테이너 이미지에 서명하고, 배포 단계에서 서명을 검증해야만 실행되게 한다. 서명만 하고 검증을 강제하지 않으면 의미가 없다.
- **`openssl x509 -text -noout -in cert.pem`**: 인증서 문제를 볼 때 가장 먼저 치는 명령이다. Subject, Issuer, Validity, SAN, Key Usage 를 위 구조도대로 확인한다.

## 확인 문제

1. MAC 대신 전자서명을 써야 하는 상황을 하나 들라.
2. 서명이 해시의 충돌 저항성에 의존하는 이유는?
3. ECDSA 에서 두 서명에 같은 난수 k 를 쓰면 어떻게 되는가? EdDSA 는 왜 이 위험이 없는가?
4. 인증서 서명 검증이 성공했는데도 연결을 거부해야 하는 경우 세 가지를 들라.

### 풀이

1. 다수의 불특정 검증자가 있고 서명자는 하나인 경우. 예: 소프트웨어 업데이트 배포, 계약서 서명처럼 부인 방지가 필요한 경우.
2. 서명은 메시지가 아니라 해시값에 하므로, 같은 해시를 갖는 다른 메시지를 만들 수 있으면 서명을 옮겨 붙일 수 있다.
3. 개인키가 계산으로 복원된다. EdDSA 는 개인키와 메시지에서 k 에 해당하는 값을 결정적으로 유도하므로 난수 생성기 실수가 개입하지 않는다.
4. 만료됨, 폐기됨, SAN 불일치, 신뢰 루트에 닿지 않는 체인, 용도(keyUsage/EKU) 불일치 중 셋.

## 더 읽을거리 (References)

- NIST, [FIPS 186-5: Digital Signature Standard (DSS)](https://csrc.nist.gov/pubs/fips/186-5/final)
- IETF, [RFC 8032: Edwards-Curve Digital Signature Algorithm (EdDSA)](https://www.rfc-editor.org/rfc/rfc8032)
- IETF, [RFC 5280: Internet X.509 PKI Certificate and CRL Profile](https://www.rfc-editor.org/rfc/rfc5280)
- IETF, [RFC 9525: Service Identity in TLS](https://www.rfc-editor.org/rfc/rfc9525)
