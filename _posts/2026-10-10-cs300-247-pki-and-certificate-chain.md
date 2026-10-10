---
layout: post
title: "[CS300 #247] PKI 와 인증서 체인 — 믿음을 위임하는 구조"
date: 2026-10-10 22:07:00 +0900
categories: [cs]
tags: [cs300, security, pki, x509, tls]
---

컴퓨터공학 300 주제 시리즈의 247번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

PKI 는 소수의 루트 CA 를 미리 믿어 두고, 그 믿음을 서명된 인증서의 사슬로 중간 CA 와 서버 인증서까지 위임하는 체계이며, 검증은 "서명이 맞나" 뿐 아니라 이름·기간·권한·폐기 여부를 사슬의 모든 고리에서 확인하는 일이다.

## 왜 필요한가

앞 글에서 인증서는 "이 공개키는 이 이름의 것" 이라는 주장에 발급자가 서명한 문서라고 했다. 그러면 발급자의 공개키는 어떻게 믿나? 또 다른 인증서로? 이 질문은 어딘가에서 멈춰야 한다. 멈추는 지점이 운영체제나 브라우저에 미리 들어 있는 **신뢰 저장소(trust store)** 의 루트 인증서다.

인터넷의 모든 HTTPS 사이트가 각자 브라우저에 공개키를 등록할 수는 없다. PKI 는 수십~수백 개의 루트만 배포해 두고 나머지를 사슬로 연결해 규모 문제를 푼다. 대신 루트 하나가 잘못 발급하면 그 피해도 인터넷 전체에 미친다. 이 구조의 강점과 약점을 함께 알아야 한다.

## 핵심 개념

### 사슬의 구성

```
[루트 CA]            자체 서명. 신뢰 저장소에 들어 있음. 보통 오프라인 보관
    │ 서명
[중간(발급) CA]      CA:TRUE. 실제 발급 업무 담당
    │ 서명
[잎(엔드 엔티티)]    CA:FALSE. 서버·클라이언트·코드 서명 등
```

루트 키를 직접 쓰지 않고 중간 CA 를 두는 이유는 피해 범위 때문이다. 중간 CA 키가 유출되면 그 중간 CA 만 폐기하고 새로 발급하면 된다. 루트 키가 유출되면 전 세계 신뢰 저장소를 갱신해야 한다.

서버는 TLS 핸드셰이크에서 **잎 인증서와 중간 인증서**를 함께 보내야 한다. 루트는 클라이언트가 이미 가지고 있으므로 보내지 않아도 된다. 중간 인증서를 빠뜨리는 설정 실수가 흔하다. 일부 브라우저는 캐시나 AIA 로 메워서 동작하지만 curl·자바 클라이언트는 실패하므로 "브라우저에선 되는데 서버 간 호출만 실패" 하는 증상이 나타난다.

### 경로 검증

RFC 5280 6장의 경로 검증 알고리즘을 요약하면 각 고리마다 다음을 확인한다.

| 확인 항목 | 내용 |
|---|---|
| 이름 연결 | 자식의 issuer 가 부모의 subject 와 같다 |
| 서명 | 부모 공개키로 자식 서명이 검증된다 |
| 기간 | 검증 시점이 각 인증서의 notBefore~notAfter 안이다 |
| CA 권한 | 부모의 basicConstraints 가 CA:TRUE 다 |
| 경로 길이 | 부모의 pathLenConstraint 를 넘지 않는다 |
| 키 용도 | 부모 keyUsage 에 keyCertSign 이 있다, 잎의 EKU 가 용도와 맞다 |
| 이름 제약 | nameConstraints 가 있으면 허용된 도메인 안이다 |
| 폐기 | CRL·OCSP 등으로 폐기되지 않았다 |

basicConstraints 확인을 빠뜨린 구현은 실제로 존재했고, 그 결과는 치명적이었다. 아무 도메인의 정상 인증서를 산 사람이 그 키로 다른 도메인 인증서를 "발급" 해도 통과됐기 때문이다. 아래 실습에서 이 경우를 재현한다.

### 폐기(revocation)

키가 유출되면 만료 전에 무효화해야 한다.

- **CRL**: CA 가 폐기된 일련번호 목록을 서명해 주기적으로 공개한다. 목록이 커지고 갱신 주기만큼 늦다.
- **OCSP**(RFC 6960): 인증서 하나의 상태를 실시간으로 묻는다. 클라이언트가 CA 에 접속 기록을 남기는 프라이버시 문제와, 응답이 없을 때 그냥 통과시키는(soft-fail) 문제가 있다.
- **OCSP 스테이플링**: 서버가 OCSP 응답을 미리 받아 핸드셰이크에 붙여 준다.

현실적으로 폐기는 잘 작동하지 않는 편이라, 인증서 **유효 기간을 짧게** 하고 자동 갱신하는 방향으로 업계가 움직였다.

### 인증서 투명성(CT)

CA 가 몰래 잘못 발급하면 어떻게 아나? CT(RFC 6962, 개정판 RFC 9162)는 발급된 인증서를 누구나 볼 수 있는 추가 전용(append-only) 로그에 기록하게 한다. 로그는 머클 트리로 되어 있어 기록이 지워지거나 바뀌면 드러난다. 도메인 소유자는 CT 로그를 감시해 자기 도메인으로 모르는 인증서가 발급됐는지 알 수 있다.

### ACME 와 자동 발급

RFC 8555 의 ACME 는 도메인 소유 증명과 발급을 자동화한다. CA 가 낸 과제를 풀어 도메인 통제권을 증명한다.

| 과제 | 증명 방식 | 쓰임 |
|---|---|---|
| http-01 | `/.well-known/acme-challenge/` 에 토큰 파일 게시 | 80 포트가 열린 일반 웹 서버 |
| dns-01 | `_acme-challenge` TXT 레코드 게시 | 와일드카드, 내부망 서버 |
| tls-alpn-01 | 443 포트 TLS 확장으로 응답 | 80 포트를 못 여는 경우 |

## 직접 해 보기

루트 → 중간 → 잎 3단 사슬을 만들고, 교육용 최소 검증기를 작성한다. 그리고 CA 권한이 없는 잎 인증서 키로 다른 도메인 인증서를 만들어 검증기가 거부하는지 본다.

```python
import datetime
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec

now = datetime.datetime.now(datetime.timezone.utc)
def nm(cn): return x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn)])

def issue(subject_cn, subject_key, issuer_cn, issuer_key, ca, pathlen=None, days=30):
    b = (x509.CertificateBuilder()
         .subject_name(nm(subject_cn)).issuer_name(nm(issuer_cn))
         .public_key(subject_key.public_key())
         .serial_number(x509.random_serial_number())
         .not_valid_before(now).not_valid_after(now + datetime.timedelta(days=days))
         .add_extension(x509.BasicConstraints(ca=ca, path_length=pathlen), critical=True))
    return b.sign(issuer_key, hashes.SHA256())

k_root, k_int, k_leaf, k_evil = (ec.generate_private_key(ec.SECP256R1()) for _ in range(4))
root = issue("Demo Root CA", k_root, "Demo Root CA", k_root, ca=True, pathlen=1, days=3650)
inter = issue("Demo Issuing CA", k_int, "Demo Root CA", k_root, ca=True, pathlen=0)
leaf = issue("www.demo.example", k_leaf, "Demo Issuing CA", k_int, ca=False)
# 잎 인증서 키로 다른 인증서를 서명해 본다 (CA 권한이 없는데!)
evil = issue("bank.example", k_evil, "www.demo.example", k_leaf, ca=False)

TRUST_STORE = [root]

def validate(chain):
    """chain[0]=잎, 마지막은 루트 직전까지. 교육용 최소 검증(기간·폐기·이름 확인 생략)."""
    path = chain + [next(r for r in TRUST_STORE if r.subject == chain[-1].issuer)]
    for i, (child, parent) in enumerate(zip(path, path[1:])):
        if parent.subject != child.issuer:
            return "거부: 이름 연결 실패"
        child.verify_directly_issued_by(parent)           # 서명 검증
        bc = parent.extensions.get_extension_for_class(x509.BasicConstraints).value
        if not bc.ca:
            return f"거부: '{parent.subject.rfc4514_string()}' 는 CA 가 아닌데 서명했다"
        if bc.path_length is not None and i > bc.path_length:
            return "거부: pathLen 제약 위반"
    return "통과: " + " -> ".join(c.subject.rfc4514_string() for c in path)

print(validate([leaf, inter]))
print(validate([evil, leaf, inter]))
```

실행 결과(Python 3.12, cryptography 41):

```
통과: CN=www.demo.example -> CN=Demo Issuing CA -> CN=Demo Root CA
거부: 'CN=www.demo.example' 는 CA 가 아닌데 서명했다
```

두 번째 사슬은 **모든 서명이 수학적으로 유효하다**. 그래도 거부해야 한다. `if not bc.ca` 세 줄을 지우면 `bank.example` 위조 인증서가 통과한다. 경로 검증을 직접 구현하지 말고 검증된 라이브러리(OpenSSL, 플랫폼 검증기)를 써야 하는 이유다. 이 코드는 원리 확인용일 뿐이다.

## 현업에서는

- **사설 CA**: 사내 서비스 간 mTLS, 쿠버네티스 클러스터 내부 통신은 공인 CA 대신 사설 CA 를 쓴다. 쿠버네티스 자체도 클러스터 CA 를 갖고 API 서버·kubelet 인증서를 서명한다. 홈랩 k3s 에서도 `kubeconfig` 안의 `certificate-authority-data` 가 바로 이 루트다. 이 파일이 유출되면 클러스터 관리자 권한이 함께 유출될 수 있으니(클라이언트 인증서와 키가 함께 들어 있는 경우) 비밀로 다룬다.
- **cert-manager**: 인그레스용 공인 인증서는 ACME 로, 내부용은 사설 CA Issuer 로 자동 발급·갱신하는 구성이 흔하다. 갱신 실패 알림을 반드시 걸어 둔다.
- **중간 인증서 누락 점검**: `openssl s_client -connect host:443 -showcerts` 로 서버가 실제로 보내는 사슬을 본다. 잎만 오면 설정 파일에 fullchain 을 지정했는지 확인한다.
- **CT 모니터링**: 자사 도메인에 대한 신규 인증서 발급을 CT 로그로 감시하면 피싱용 유사 도메인이나 잘못된 발급을 일찍 잡는다.

## 확인 문제

1. 루트 CA 키로 직접 서버 인증서를 발급하지 않고 중간 CA 를 두는 이유는?
2. 서버가 중간 인증서를 보내지 않을 때 나타나는 전형적 증상은?
3. 모든 서명이 유효한데도 사슬을 거부해야 하는 경우 두 가지는?
4. OCSP 의 약점 두 가지와 이를 보완하는 방법은?
5. 와일드카드 인증서를 ACME 로 받으려면 어떤 과제를 써야 하는가?

### 풀이

1. 루트 키를 오프라인에 두어 노출을 줄이고, 중간 CA 가 털려도 그것만 폐기·교체하면 되게 피해 범위를 한정하려고.
2. 브라우저에서는 열리는데 curl·서버 간 클라이언트에서 "unable to get local issuer certificate" 류의 오류가 난다.
3. 부모가 CA:TRUE 가 아님, pathLen 위반, 기간 만료, 폐기됨, 이름 제약 위반 중 둘.
4. 클라이언트 접속 정보가 CA 에 새는 프라이버시 문제, 응답 실패 시 통과시키는 soft-fail 문제. OCSP 스테이플링과 짧은 유효 기간·자동 갱신으로 보완한다.
5. dns-01.

## 더 읽을거리 (References)

- IETF, [RFC 5280: Internet X.509 PKI Certificate and CRL Profile](https://www.rfc-editor.org/rfc/rfc5280)
- IETF, [RFC 6960: X.509 Internet PKI Online Certificate Status Protocol - OCSP](https://www.rfc-editor.org/rfc/rfc6960)
- IETF, [RFC 9162: Certificate Transparency Version 2.0](https://www.rfc-editor.org/rfc/rfc9162)
- IETF, [RFC 8555: Automatic Certificate Management Environment (ACME)](https://www.rfc-editor.org/rfc/rfc8555)
