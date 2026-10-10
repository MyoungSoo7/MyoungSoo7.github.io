---
layout: post
title: "[CS300 #250] OWASP Top 10 개관 — 웹 애플리케이션 위험의 공용어"
date: 2026-10-10 22:10:00 +0900
categories: [cs]
tags: [cs300, security, owasp, web-security, appsec]
---

컴퓨터공학 300 주제 시리즈의 250번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

OWASP Top 10 은 웹 애플리케이션에서 가장 흔하고 치명적인 위험 범주 열 개를 정리한 **인식 제고용 문서**이며, 체크리스트나 표준이 아니라 "어디부터 볼 것인가" 를 정하는 출발점이다.

## 왜 필요한가

개발자, 보안 담당자, 감사인, 경영진이 같은 말을 쓰려면 공용어가 필요하다. "A01 위반" 이라고 하면 접근 통제 문제라는 걸 모두 안다. 보안 교육 과정, 스캐너 보고서, 침투 테스트 보고서, 계약서의 보안 요구 사항이 Top 10 범주로 쓰이는 이유다.

또 Top 10 은 데이터에 근거한 우선순위다. OWASP 는 여러 기관이 제출한 실제 테스트 데이터와 커뮤니티 설문을 합쳐 순위를 정한다. 막연한 "해킹 방어" 대신 실제로 많이 터지는 것부터 막자는 취지다.

주의할 점이 있다. OWASP 스스로 Top 10 을 코딩·테스트 표준으로 쓴다면 그것은 [**최소한이자 출발점일 뿐**](https://owasp.org/Top10/2021/A00_2021_How_to_use_the_OWASP_Top_10_as_a_standard/)이라고 적어 두었다. 열 개를 다 막았다고 안전한 게 아니다. 체계적인 검증 기준이 필요하면 OWASP ASVS(Application Security Verification Standard)를 쓴다.

## 핵심 개념

### 2021년판과 2025년판

OWASP 는 몇 년마다 목록을 갱신한다. 현재 공식 사이트에는 2025년판이 올라와 있다.

| 순위 | 2021 | 2025 |
|---|---|---|
| A01 | Broken Access Control | Broken Access Control |
| A02 | Cryptographic Failures | Security Misconfiguration |
| A03 | Injection | **Software Supply Chain Failures** |
| A04 | Insecure Design | Cryptographic Failures |
| A05 | Security Misconfiguration | Injection |
| A06 | Vulnerable and Outdated Components | Insecure Design |
| A07 | Identification and Authentication Failures | Authentication Failures |
| A08 | Software and Data Integrity Failures | Software or Data Integrity Failures |
| A09 | Security Logging and Monitoring Failures | Security Logging and Alerting Failures |
| A10 | Server-Side Request Forgery (SSRF) | **Mishandling of Exceptional Conditions** |

읽을 거리:

- **접근 통제 실패는 두 판 연속 1위**다. 2025년판에서는 SSRF(CWE-918)와 CSRF(CWE-352)가 이 범주 안에 들어갔다.
- **공급망 실패**가 새 범주로 3위에 올랐다. 2021년의 "취약하고 오래된 구성 요소" 를 넓혀, 의존성뿐 아니라 빌드 시스템·배포 인프라 전체를 본다. 데이터상 비중은 작지만 커뮤니티 설문에서 압도적으로 우려 대상으로 꼽혔다고 OWASP 는 설명한다.
- **예외 상황 처리 실패**가 새로 들어왔다. 오류를 삼키거나, 실패 시 열린 상태로 동작(fail-open)하거나, 오류 메시지로 내부 정보를 흘리는 문제다.
- 인젝션은 순위가 내려갔지만 여전히 CVE 수가 매우 많은 범주다. 2025년판 설명은 XSS 와 SQL 인젝션을 이 범주에 함께 넣는다.

### 범주는 CWE 의 묶음이다

각 범주는 여러 CWE(Common Weakness Enumeration) 항목의 묶음이다. 예를 들어 접근 통제 실패에는 경로 조작, 권한 확인 누락, 사용자 제어 키로 인한 인가 우회(CWE-639, IDOR) 등이 들어 있다. 스캐너 보고서의 CWE 번호를 보면 Top 10 어느 범주인지 거꾸로 찾을 수 있다.

### 범주별 핵심 대책 요약

| 범주 | 한 줄 대책 |
|---|---|
| 접근 통제 실패 | 서버에서 기본 거부, 객체 수준 소유권 확인 |
| 보안 설정 오류 | 하드닝 기준, 기본 계정·샘플 제거, 설정을 코드로 관리 |
| 공급망 실패 | 의존성 목록(SBOM)·버전 고정·서명 검증·빌드 무결성 |
| 암호화 실패 | 전송·저장 암호화, 검증된 라이브러리, 키 관리 |
| 인젝션 | 파라미터화 쿼리, 문맥별 출력 인코딩 |
| 안전하지 않은 설계 | 위협 모델링, 보안 요구 사항, 안전한 기본값 |
| 인증 실패 | MFA, 안전한 세션 관리, 무차별 대입 방지 |
| 무결성 실패 | 서명·검증, 신뢰할 수 없는 역직렬화 금지 |
| 로깅·경보 실패 | 보안 이벤트 기록과 경보, 탐지 가능성 |
| 예외 처리 실패 | 실패 시 닫힘(fail-closed), 일반 오류 메시지, 자원 정리 |

이후 글에서 SQL 인젝션, XSS·CSRF, 접근 통제·IDOR, 시큐어 코딩, 공급망, 로깅을 각각 깊게 다룬다.

## 직접 해 보기

작은 WSGI 앱 두 개(취약/개선)를 만들고 같은 점검표로 검사한다. 네트워크를 쓰지 않고 함수 호출만으로 돌린다.

```python
import traceback
from wsgiref.util import setup_testing_defaults

def vulnerable_app(environ, start_response):
    try:
        if environ["PATH_INFO"] == "/admin":
            body = b"admin panel"                         # 인가 확인 없음 (A01)
        else:
            1 / 0                                         # 예외 발생
        start_response("200 OK", [("Content-Type", "text/html")])
    except Exception:
        body = traceback.format_exc().encode()            # 스택 트레이스 노출 (A02, A10)
        start_response("500 Internal Server Error", [("Content-Type", "text/plain"),
                                                     ("Server", "DemoFramework/0.9.1")])
    return [body]

SEC_HEADERS = [("Content-Type", "text/plain; charset=utf-8"),
               ("Content-Security-Policy", "default-src 'self'"),
               ("X-Content-Type-Options", "nosniff"),
               ("Strict-Transport-Security", "max-age=31536000")]

SESSIONS = {"s-9b1c": {"user": "kim", "role": "admin"}}   # 서버 쪽 세션 저장소(데모)

def current_user(environ):
    cookie = environ.get("HTTP_COOKIE", "")
    sid = cookie.split("sid=", 1)[1].split(";")[0] if "sid=" in cookie else None
    return SESSIONS.get(sid)

def fixed_app(environ, start_response):
    try:
        if environ["PATH_INFO"] == "/admin":
            user = current_user(environ)
            if not user or user["role"] != "admin":         # 서버에서 역할 확인
                start_response("403 Forbidden", SEC_HEADERS)
                return [b"forbidden"]
            body = b"admin panel"
        else:
            1 / 0
        start_response("200 OK", SEC_HEADERS)
    except Exception:
        # 내부 로그에는 자세히, 사용자에게는 일반 메시지
        start_response("500 Internal Server Error", SEC_HEADERS)
        body = b"internal error, ref=7f3a"
    return [body]

def call(app, path):
    env = {}; setup_testing_defaults(env); env["PATH_INFO"] = path
    out = {}
    def sr(status, headers): out["status"], out["headers"] = status, dict(headers)
    out["body"] = b"".join(app(env, sr))
    return out

def audit(app):
    findings = []
    r = call(app, "/admin")
    if r["status"].startswith("200"): findings.append("A01 익명 사용자가 /admin 에 접근")
    r = call(app, "/boom")
    if b"Traceback" in r["body"]: findings.append("A02/A10 오류 응답에 스택 트레이스 노출")
    if "Server" in r["headers"]: findings.append("A02 Server 헤더로 버전 노출")
    for h in ("Content-Security-Policy", "X-Content-Type-Options"):
        if h not in r["headers"]: findings.append(f"A02 보안 헤더 누락: {h}")
    return findings or ["점검표 항목 통과"]

for name, app in [("취약", vulnerable_app), ("개선", fixed_app)]:
    print(f"[{name}]"); [print("  -", f) for f in audit(app)]
```

실행 결과(Python 3.12):

```
[취약]
  - A01 익명 사용자가 /admin 에 접근
  - A02/A10 오류 응답에 스택 트레이스 노출
  - A02 Server 헤더로 버전 노출
  - A02 보안 헤더 누락: Content-Security-Policy
  - A02 보안 헤더 누락: X-Content-Type-Options
[개선]
  - 점검표 항목 통과
```

"점검표 통과" 는 **이 다섯 항목**을 통과했다는 뜻일 뿐이다. 자동 점검은 설정 오류처럼 겉으로 드러나는 문제는 잘 잡지만, 접근 통제나 설계 결함은 업무 맥락을 알아야 판단할 수 있어 대부분 놓친다. Top 10 1위가 자동화로 잘 안 잡히는 범주라는 사실이 시사하는 바가 크다.

## 현업에서는

- **보안 요구 사항의 틀**: 외주 개발 계약이나 내부 보안 기준에 "OWASP Top 10 대응" 이 들어가는 경우가 많다. 이때 반드시 버전(2021 또는 2025)을 명시한다. 범주 번호가 판마다 다르다.
- **도구 결과 분류**: SAST·DAST·의존성 스캐너는 결과를 CWE 와 Top 10 범주로 태깅한다. 대시보드에서 범주별 추세를 보면 팀의 약한 영역이 드러난다.
- **쿠버네티스 환경의 "설정 오류"**: 애플리케이션 밖의 설정도 A02 다. 대시보드나 관리 UI 를 인증 없이 인그레스로 노출하거나, 디버그 모드로 배포하거나, 기본 비밀번호의 DB 를 서비스 타입 NodePort 로 열어 두는 것이 전형적이다. 홈랩에서도 "테스트용으로 잠깐" 연 포트가 그대로 남는 일이 흔하다.
- **교육 순서**: 신입 교육은 A01(인가)과 A05(인젝션)부터 시작하는 게 효과적이다. 코드 리뷰에서 가장 자주 지적되고, 원리를 알면 바로 고칠 수 있다.

## 확인 문제

1. OWASP Top 10 을 "보안 표준" 으로 쓰면 안 되는 이유는? 대신 쓸 수 있는 OWASP 문서는?
2. 2025년판에서 새로 들어온 범주 두 가지는?
3. 2021년판의 A10 SSRF 는 2025년판에서 어디로 갔는가?
4. 자동 스캐너가 A01(접근 통제 실패)을 잘 찾지 못하는 이유는?

### 풀이

1. 인식 제고용 최소 목록이라 범위가 좁고 검증 가능한 요구 사항 형태가 아니다. 검증 기준으로는 OWASP ASVS 를 쓴다.
2. Software Supply Chain Failures(A03), Mishandling of Exceptional Conditions(A10).
3. A01 Broken Access Control 범주에 포함됐다.
4. "이 사용자가 이 객체에 접근해도 되는가" 는 업무 규칙에 달려 있어, 응답만 보고 정상인지 판단할 근거가 스캐너에 없다.

## 더 읽을거리 (References)

- OWASP, [OWASP Top 10:2025](https://owasp.org/Top10/2025/)
- OWASP, [OWASP Top 10:2021](https://owasp.org/Top10/2021/)
- OWASP, [OWASP Top Ten 프로젝트 페이지](https://owasp.org/www-project-top-ten/)
- MITRE, [CWE Top 25 Most Dangerous Software Weaknesses](https://cwe.mitre.org/top25/)
