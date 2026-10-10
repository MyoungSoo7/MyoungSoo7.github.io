---
layout: post
title: "[CS300 #248] 비밀번호 저장 — 빠른 해시는 공격자를 돕는다"
date: 2026-10-10 22:08:00 +0900
categories: [cs]
tags: [cs300, security, password-hashing, argon2, scrypt]
---

컴퓨터공학 300 주제 시리즈의 248번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

비밀번호는 암호화하지도, SHA-256 으로 해시하지도 않는다. 사용자마다 다른 **솔트**를 붙여 **일부러 느리고 메모리를 많이 먹는 함수(Argon2id, scrypt, bcrypt, PBKDF2)** 로 해시해 저장한다.

## 왜 필요한가

DB 는 언젠가 유출된다고 가정해야 한다. SQL 인젝션, 백업 파일 노출, 내부자. 그때 비밀번호 컬럼이 어떤 형태인지가 피해 규모를 정한다.

- **평문**: 즉시 전부 노출. 사용자들이 다른 사이트에 같은 비밀번호를 쓰므로 피해가 우리 서비스 밖으로 번진다.
- **암호화**: 키가 같은 서버에 있으므로 키도 함께 털리기 쉽다. 그리고 비밀번호를 복호화할 이유가 애초에 없다.
- **빠른 해시(MD5, SHA-256)**: 역산은 못 해도 추측은 빠르다. 공격자는 흔한 비밀번호 목록을 해시해 대조한다. 해시가 빠를수록 추측도 빠르다.

비밀번호 저장의 목표는 "유출돼도 하나하나 깨는 데 드는 비용을 최대한 크게" 만드는 것이다.

## 핵심 개념

### 솔트

솔트는 사용자마다 다른 무작위 값으로, 해시 입력에 붙여 함께 저장한다. 비밀이 아니다.

```
솔트 없음:  hash("123456")            → 모든 사용자 동일 값
솔트 있음:  hash(salt_A + "123456")   ≠ hash(salt_B + "123456")
```

솔트가 막는 것:
- **미리 계산한 표(레인보우 테이블)**: 솔트마다 표를 다시 만들어야 하므로 사전 계산이 무의미해진다.
- **한 번에 여러 계정 공격**: 같은 비밀번호를 쓰는 사용자를 해시값만 보고 묶을 수 없다. 추측 하나를 사용자 수만큼 따로 계산해야 한다.

솔트가 막지 못하는 것: 계정 하나를 집중해 추측하는 공격. 그건 느린 함수가 막는다.

### 느린 함수, 메모리 하드 함수

| 함수 | 비용 조절 | OWASP 최소 권장(치트시트 기준) | 비고 |
|---|---|---|---|
| Argon2id | 메모리 m, 반복 t, 병렬 p | m=19 MiB, t=2, p=1 | RFC 9106. 1순위 |
| scrypt | N, r, p | N=2^17, r=8, p=1 (약 128 MiB) | Argon2id 를 못 쓸 때 |
| bcrypt | work factor | 10 이상 | 레거시. 입력 72바이트 제한 |
| PBKDF2-HMAC-SHA256 | 반복 횟수 | 600,000 이상 | FIPS-140 준수가 필요할 때 |

반복만 늘리는 PBKDF2 는 GPU·전용 하드웨어로 병렬화하기 쉽다. Argon2·scrypt 는 계산마다 큰 메모리를 요구해 병렬 공격 비용을 올린다. 이것이 "메모리 하드" 의 의미다.

bcrypt 의 72바이트 제한은 실무 함정이다. 그보다 긴 입력은 잘려서 뒷부분이 무시된다. 긴 패스프레이즈를 쓰는 사용자에게 문제가 될 수 있다.

### 페퍼

모든 비밀번호에 공통으로 섞는 비밀 값을 페퍼라 한다. DB 와 다른 곳(HSM, 시크릿 관리 도구)에 둔다. DB 만 유출되면 공격자는 페퍼를 몰라 추측을 시작할 수 없다. OWASP 는 이를 **추가 심층 방어**로만 권한다. 페퍼 자체가 안전성의 기반이 되면 안 된다.

### 저장 형식과 재해시

알고리즘·파라미터·솔트·해시를 한 문자열에 담는 형식이 관례다.

```
$argon2id$v=19$m=19456,t=2,p=1$<솔트 base64>$<해시 base64>
```

파라미터가 함께 저장되므로 나중에 비용을 올릴 수 있다. 로그인 성공 시점에는 평문 비밀번호를 잠깐 손에 쥐고 있으므로, 저장된 파라미터가 현재 기준보다 약하면 그 자리에서 새 파라미터로 다시 해시해 저장한다.

### 비밀번호 정책: NIST SP 800-63B

2025년 7월 공개된 최종판(Rev. 4)의 요지는 다음과 같다.

- 단일 인증 수단으로 쓰는 비밀번호는 **최소 15자**, 다중 인증의 일부라면 최소 8자.
- 최대 길이는 **64자 이상** 허용을 권장. 공백·유니코드 허용.
- 대소문자·특수문자 섞기 같은 **조합 규칙을 강제하지 않는다**.
- **주기적 변경을 강제하지 않는다**. 유출 증거가 있을 때만 바꾸게 한다.
- 흔하거나 유출된 비밀번호 **차단 목록**과 대조한다.

조합 규칙과 주기적 변경은 `Password1!` → `Password2!` 같은 예측 가능한 패턴을 낳을 뿐이라는 판단이다.

## 직접 해 보기

표준 라이브러리만으로 (1) 솔트 없는 해시의 문제 (2) 함수별 속도 (3) scrypt 기반 저장·검증을 확인한다. `hashlib.scrypt` 는 OpenSSL 이 지원할 때 쓸 수 있다.

```python
import hashlib, hmac, os, time, base64

pw = b"correct horse battery staple"

# 1) 솔트 없는 빠른 해시 (하면 안 되는 예)
print("sha256 A:", hashlib.sha256(pw).hexdigest()[:16])
print("sha256 B:", hashlib.sha256(pw).hexdigest()[:16])

# 2) 속도 비교 — 이 숫자가 곧 공격자의 추측 속도다
def bench(label, fn, n):
    t = time.perf_counter()
    for _ in range(n): fn()
    dt = (time.perf_counter() - t) / n
    print(f"{label:<28} 1회 {dt*1000:9.3f} ms  (초당 약 {1/dt:,.0f}회)")

salt = os.urandom(16)
bench("sha256", lambda: hashlib.sha256(salt + pw).digest(), 100000)
bench("pbkdf2-sha256 600,000회", lambda: hashlib.pbkdf2_hmac("sha256", pw, salt, 600_000), 3)
bench("scrypt N=2^17 r=8 p=1", lambda: hashlib.scrypt(pw, salt=salt, n=2**17, r=8, p=1,
                                                     maxmem=2**28, dklen=32), 3)

# 3) 저장 형식: 알고리즘·파라미터·솔트·해시를 한 문자열에
def hash_pw(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.scrypt(password.encode(), salt=salt, n=2**17, r=8, p=1, maxmem=2**28, dklen=32)
    b64 = lambda b: base64.b64encode(b).decode()
    return f"scrypt$17$8$1${b64(salt)}${b64(dk)}"

def verify_pw(password: str, stored: str) -> bool:
    algo, logn, r, p, s, h = stored.split("$")
    dk = hashlib.scrypt(password.encode(), salt=base64.b64decode(s), n=2**int(logn),
                        r=int(r), p=int(p), maxmem=2**28, dklen=32)
    return hmac.compare_digest(dk, base64.b64decode(h))

rec1, rec2 = hash_pw("hunter2-but-longer"), hash_pw("hunter2-but-longer")
print("같은 비밀번호, 저장값 같은가?", rec1 == rec2)
print("맞는 비밀번호:", verify_pw("hunter2-but-longer", rec1))
print("틀린 비밀번호:", verify_pw("hunter3-but-longer", rec1))
```

2코어 노트북 서버에서의 실행 결과(Python 3.12). 시간은 기계마다 다르다.

```
sha256 A: c4bbcb1fbec99d65
sha256 B: c4bbcb1fbec99d65
sha256                       1회     0.002 ms  (초당 약 624,996회)
pbkdf2-sha256 600,000회       1회   771.347 ms  (초당 약 1회)
scrypt N=2^17 r=8 p=1        1회   984.886 ms  (초당 약 1회)
같은 비밀번호, 저장값 같은가? False
맞는 비밀번호: True
틀린 비밀번호: False
```

CPU 한 코어 기준으로도 추측 속도가 수십만 배 차이 난다. 공격자는 GPU 를 쓰므로 실제 격차는 함수 종류에 따라 더 벌어지거나 줄어든다. 메모리 하드 함수가 GPU 에 불리한 이유가 여기 있다. 반대로 로그인 한 번에 1초 가까이 걸리는 건 서버에도 부담이므로, 실제 서비스는 처리량을 재고 파라미터를 정한다. 운영에서는 `maxmem` 같은 세부를 직접 다루기보다 argon2-cffi 같은 검증된 라이브러리를 쓰는 편이 낫다.

## 현업에서는

- **프레임워크 기본값 확인**: Django, Spring Security, ASP.NET Identity 등은 비밀번호 해셔를 내장하고 있다. 직접 만들지 말고 기본 해셔가 무엇이고 비용이 얼마인지 확인한다. 오래된 프로젝트는 약한 파라미터가 그대로인 경우가 많다.
- **레거시 마이그레이션**: MD5 로 저장된 레거시 테이블은 `argon2(md5(pw))` 처럼 기존 해시를 한 번 더 감싸 즉시 전체를 보호하고, 로그인 시 정식 형식으로 교체하는 방식이 흔하다.
- **로그인 엔드포인트 보호**: 느린 해시는 서버 CPU 를 쓰므로 로그인 API 가 서비스 거부의 표적이 된다. 속도 제한과 동시 해시 계산 수 상한을 함께 둔다. 쿠버네티스라면 인증 서비스 파드의 CPU·메모리 limit 을 해시 파라미터에 맞춰 잡아야 한다. Argon2 메모리 파라미터 × 동시 로그인 수가 limit 을 넘으면 OOMKilled 가 난다.
- **차단 목록**: 신규 가입·변경 시 유출 비밀번호 목록과 대조한다. k-익명성 방식의 조회 API 를 쓰면 비밀번호 전체를 외부로 보내지 않고 확인할 수 있다.

## 확인 문제

1. 비밀번호를 AES 로 암호화해 저장하면 안 되는 이유 두 가지는?
2. 솔트가 막는 공격과 막지 못하는 공격을 하나씩 들라.
3. PBKDF2 보다 Argon2id·scrypt 가 권장되는 이유는?
4. NIST SP 800-63B 가 금지하는 비밀번호 정책 두 가지는?
5. bcrypt 를 쓸 때 주의할 입력 길이 문제는?

### 풀이

1. 키가 같은 시스템에 있어 함께 유출되기 쉽다. 그리고 검증에 복호화가 필요 없으므로 되돌릴 수 있는 형태로 둘 이유가 없다.
2. 막는 것: 레인보우 테이블, 여러 계정 동시 대조. 막지 못하는 것: 한 계정에 대한 집중 추측(사전 공격).
3. 메모리를 많이 요구해 GPU·전용 하드웨어로 대량 병렬 추측하는 비용을 크게 올린다.
4. 문자 조합 규칙 강제, 주기적 변경 강제.
5. 72바이트를 넘는 부분은 무시된다. 긴 패스프레이즈의 뒷부분이 반영되지 않는다.

## 더 읽을거리 (References)

- OWASP, [Password Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)
- NIST, [SP 800-63B-4: Digital Identity Guidelines — Authentication and Authenticator Management](https://pages.nist.gov/800-63-4/sp800-63b.html)
- IETF, [RFC 9106: Argon2 Memory-Hard Function for Password Hashing and Proof-of-Work Applications](https://www.rfc-editor.org/rfc/rfc9106)
- Python, [hashlib — Key derivation (pbkdf2_hmac, scrypt)](https://docs.python.org/3/library/hashlib.html)
