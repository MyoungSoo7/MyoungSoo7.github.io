---
layout: post
title: "[CS300 #253] 접근 통제 실패와 IDOR — 로그인했다고 남의 것을 열면 안 된다"
date: 2026-10-10 22:13:00 +0900
categories: [cs]
tags: [cs300, security, access-control, idor, bola]
---

컴퓨터공학 300 주제 시리즈의 253번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

접근 통제 실패는 사용자가 허락된 범위를 벗어나 행동할 수 있는 모든 결함이고, 그 대표가 IDOR(안전하지 않은 직접 객체 참조) — URL 이나 요청의 ID 만 바꿔 남의 데이터에 접근하는 문제다. 해법은 **모든 요청에서, 서버가, 객체 단위로** 소유권과 권한을 확인하는 것이다.

## 왜 필요한가

OWASP Top 10 은 2021년판과 2025년판 모두 접근 통제 실패를 1위에 두었다. 2025년판 설명에 따르면 이 범주에 묶인 CWE 가 40개로 가장 많다. OWASP API Security Top 10(2023)도 1위가 BOLA(Broken Object Level Authorization)인데, 이는 IDOR 의 API 판 이름이다.

이 결함이 흔한 이유는 **자동으로 잡기 어렵기** 때문이다. `/invoices/1002` 응답이 200 이라는 사실만으로는 정상인지 사고인지 알 수 없다. 1002번 청구서가 요청자의 것인지는 업무 규칙만 안다. 스캐너도, 컴파일러도, 프레임워크 기본값도 이걸 대신 판단해 주지 못한다. 그래서 개발자가 설계와 코드에서 직접 챙겨야 한다.

## 핵심 개념

### 접근 통제 실패의 모양들

| 유형 | 예 |
|---|---|
| 객체 수준(IDOR/BOLA) | `GET /api/orders/1002` 의 숫자만 바꿔 남의 주문 조회 |
| 기능 수준 | 일반 사용자가 `/admin/users` API 를 직접 호출. UI 에서 메뉴만 숨김 |
| 속성 수준(대량 할당) | 프로필 수정 요청에 `"role":"admin"` 을 끼워 넣으면 반영됨 |
| 경로 조작 | `?file=../../etc/passwd` 로 허용 디렉터리 밖 파일 접근 |
| 메타데이터 조작 | JWT·쿠키·숨은 필드의 권한 값을 클라이언트가 바꿈 |
| 교차 출처 | CSRF, 과도하게 열린 CORS |
| 서버 측 요청 위조(SSRF) | 서버가 사용자 지정 URL 을 대신 요청해 내부망에 닿음 |

2025년판은 SSRF 와 CSRF 도 이 범주에 넣었다. 공통점은 "허락받지 않은 주체가 허락받지 않은 대상에 닿는다" 다.

### IDOR 의 구조

```
GET /api/invoices/1002
Cookie: session=alice

서버(취약):  SELECT * FROM invoices WHERE id = 1002
             → 로그인은 확인했다. 그런데 1002 가 alice 것인지는 안 봤다.
```

인증은 됐다. 기능 접근 권한도 있다("청구서 조회" 는 일반 사용자 기능이다). 빠진 건 **이 객체**에 대한 권한이다.

### 왜 "추측하기 어려운 ID" 는 해결책이 아닌가

순차 정수 대신 UUID 를 쓰면 무작위 대입이 어려워진다. 하지만 ID 는 URL, 로그, 공유 링크, 다른 API 응답, 브라우저 기록을 통해 새어 나간다. OWASP IDOR 치트시트도 무작위 ID 는 심층 방어일 뿐이며 접근 통제 검사를 대신하지 못한다고 말한다. **숨기는 것은 통제가 아니다.**

### 올바른 패턴

1. **조회 범위를 사용자로 한정**한다. `WHERE id = ? AND owner_id = ?` 처럼 소유 조건을 쿼리에 넣거나, `current_user.invoices.find(id)` 처럼 사용자에서 출발하는 관계로 조회한다.
2. **인가를 한 곳에 모은다**. 정책 함수나 미들웨어로 중앙화하고, 엔드포인트마다 손으로 쓰지 않는다. 새 엔드포인트가 기본으로 거부되게 한다.
3. **입력 필드 허용 목록**으로 대량 할당을 막는다. 요청 DTO 에 수정 가능한 필드만 둔다.
4. **403 과 404 선택**: 남의 객체에 403 을 돌려주면 "그 ID 는 존재한다" 는 정보가 샌다. 민감한 자원이면 404 로 통일한다.
5. **테스트로 고정**한다. "사용자 A 의 토큰으로 사용자 B 의 객체를 요청하면 거부" 를 엔드포인트마다 자동 테스트로 둔다.

## 직접 해 보기

메모리 SQLite 로 청구서 조회(IDOR)와 프로필 수정(대량 할당)을 취약/개선 버전으로 나란히 돌린다.

```python
import sqlite3
db = sqlite3.connect(":memory:")
db.executescript("""
CREATE TABLE invoices(id INTEGER PRIMARY KEY, owner_id INTEGER, amount INTEGER, memo TEXT);
INSERT INTO invoices VALUES (1001, 1, 50000, 'alice 의 청구서'),
                            (1002, 2, 990000, 'bob 의 청구서');
CREATE TABLE users(id INTEGER PRIMARY KEY, name TEXT, role TEXT);
INSERT INTO users VALUES (1, 'alice', 'user'), (2, 'bob', 'user');
""")

# 취약: 로그인만 확인하고 id 로 바로 조회 (IDOR)
def get_invoice_vulnerable(current_user_id, invoice_id):
    row = db.execute("SELECT id, amount, memo FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
    return (200, row) if row else (404, None)

# 개선: 소유권을 쿼리 조건에 넣는다 (객체 수준 인가)
def get_invoice_safe(current_user_id, invoice_id):
    row = db.execute("SELECT id, amount, memo FROM invoices WHERE id = ? AND owner_id = ?",
                     (invoice_id, current_user_id)).fetchone()
    return (200, row) if row else (404, None)   # 존재 여부도 숨기려면 403 대신 404

alice = 1
for f in (get_invoice_vulnerable, get_invoice_safe):
    print(f.__name__, "alice -> 1002:", f(alice, 1002))

# 대량 할당(mass assignment): 요청 본문을 그대로 업데이트하면 role 까지 바뀐다
def update_profile_vulnerable(user_id, body: dict):
    for k, v in body.items():                 # 키를 검증 없이 컬럼명으로 사용(SQL 인젝션 위험도 겸함)
        db.execute(f"UPDATE users SET {k} = ? WHERE id = ?", (v, user_id))
ALLOWED_FIELDS = {"name"}
def update_profile_safe(user_id, body: dict):
    bad = set(body) - ALLOWED_FIELDS          # 먼저 전체를 검사하고, 하나라도 있으면 아무것도 안 바꾼다
    if bad:
        raise PermissionError(f"수정 불가 필드: {sorted(bad)}")
    for k, v in body.items():                 # k 는 허용 목록을 통과한 식별자만
        db.execute(f"UPDATE users SET {k} = ? WHERE id = ?", (v, user_id))

update_profile_vulnerable(alice, {"name": "Alice", "role": "admin"})
print("취약 업데이트 후:", db.execute("SELECT * FROM users WHERE id=1").fetchone())
db.execute("UPDATE users SET role='user' WHERE id=1")
try:
    update_profile_safe(alice, {"name": "Alice", "role": "admin"})
except PermissionError as e:
    print("개선 업데이트:", e)
```

실행 결과(Python 3.12):

```
get_invoice_vulnerable alice -> 1002: (200, (1002, 990000, 'bob 의 청구서'))
get_invoice_safe alice -> 1002: (404, None)
취약 업데이트 후: (1, 'Alice', 'admin')
개선 업데이트: 수정 불가 필드: ['role']
```

개선 버전에서 바뀐 건 쿼리 조건 하나(`AND owner_id = ?`)와 허용 목록 하나다. 코드 양은 거의 같다. 접근 통제 결함은 대개 어려워서가 아니라 **빠뜨려서** 생긴다. 개선된 수정 함수가 검사를 **먼저 전부** 하고 나서야 쓰기를 시작한다는 점도 보자. 필드별로 검사하며 쓰면 허용된 필드만 반쯤 반영된 상태로 오류가 나는데, 이것도 예외 처리 실패의 한 모양이다.

## 현업에서는

- **테스트 매트릭스**: 사용자 두 명(A, B)과 역할 두 개(일반, 관리자)로 "A 가 B 의 자원에 읽기/수정/삭제" 를 전 엔드포인트에 자동으로 돌리는 테스트가 효과적이다. 침투 테스트에서도 계정 두 개로 요청을 바꿔 보내는 것이 가장 기본적인 점검이다.
- **GraphQL·배치 API**: 한 요청에 여러 ID 를 받는 API 는 목록의 **모든 항목**을 검사해야 한다. 첫 항목만 확인하는 버그가 흔하다.
- **파일 다운로드**: 객체 스토리지의 사전 서명 URL(presigned URL)을 발급하기 전에 소유권을 확인하고, 유효 기간을 짧게 둔다. URL 이 곧 권한이 되기 때문이다.
- **쿠버네티스 RBAC 도 같은 문제**: `get secrets` 권한을 네임스페이스 전체에 주면 그 네임스페이스의 모든 시크릿을 읽는다. `resourceNames` 로 특정 객체만 허용할 수 있다. 홈랩에서 편의상 `cluster-admin` 을 바인딩해 둔 서비스 어카운트가 있다면 그 파드가 털리는 순간 클러스터 전체가 열린다.

## 확인 문제

1. 인증, 기능 수준 인가, 객체 수준 인가의 차이를 `GET /api/invoices/1002` 로 설명하라.
2. ID 를 UUID 로 바꾸는 것이 IDOR 의 해결책이 아닌 이유는?
3. 대량 할당 취약점은 무엇이고 어떻게 막는가?
4. 남의 객체 요청에 403 대신 404 를 돌려주는 이유는?

### 풀이

1. 인증: 요청자가 alice 인지 확인. 기능 수준: alice 가 청구서 조회 기능을 쓸 수 있는지. 객체 수준: 1002번 청구서가 alice 가 볼 수 있는 것인지.
2. ID 는 여러 경로로 노출되며, 숨기는 것은 접근 통제가 아니다. 서버의 소유권 검사가 여전히 필요하다.
3. 요청 본문의 필드를 모델에 그대로 반영해 사용자가 바꾸면 안 되는 필드(역할, 잔액 등)까지 바뀌는 취약점. 수정 가능한 필드 허용 목록이나 전용 DTO 로 막는다.
4. 403 은 객체가 존재한다는 사실을 알려 준다. 404 로 통일하면 존재 여부도 숨길 수 있다.

## 더 읽을거리 (References)

- OWASP, [A01:2025 Broken Access Control](https://owasp.org/Top10/2025/A01_2025-Broken_Access_Control/)
- OWASP, [Insecure Direct Object Reference Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Insecure_Direct_Object_Reference_Prevention_Cheat_Sheet.html)
- OWASP, [API1:2023 Broken Object Level Authorization](https://owasp.org/API-Security/editions/2023/en/0xa1-broken-object-level-authorization/)
- MITRE, [CWE-639: Authorization Bypass Through User-Controlled Key](https://cwe.mitre.org/data/definitions/639.html)
