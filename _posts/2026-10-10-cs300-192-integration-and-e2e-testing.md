---
layout: post
title: "[CS300 #192] 통합 테스트와 E2E 테스트 — 조각이 맞물리는 곳을 확인하기"
date: 2026-10-10 21:12:00 +0900
categories: [cs]
tags: [cs300, software-engineering, integration-testing, e2e-testing, test-pyramid]
---

컴퓨터공학 300 주제 시리즈의 192번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

통합 테스트는 내 코드가 데이터베이스·메시지 큐·외부 API 같은 **실제 협력자와 맞물려** 동작하는지 확인하고, E2E(End-to-End) 테스트는 사용자가 쓰는 방식 그대로 **시스템 전체를 바깥에서** 확인한다. 위로 갈수록 확신은 커지지만 느리고 불안정해지므로, 아래층을 두껍게 위층을 얇게 쌓는다.

## 왜 필요한가

단위 테스트가 전부 통과해도 시스템은 망가질 수 있다. 테스트 더블은 "DB 가 이렇게 동작할 것" 이라는 **나의 가정**을 흉내 낼 뿐이다. 가정이 틀리면 테스트 더블도 같이 틀린다.

- 스텁은 중복 제목을 받아 줬는데, 실제 DB 에는 UNIQUE 제약이 있었다.
- 목은 `find(code)` 를 기대했는데, 실제 SQL 의 컬럼 이름이 바뀌었다.
- 각 서비스는 멀쩡한데, 직렬화 형식(날짜 문자열 포맷)이 서로 달랐다.

이런 결함은 경계에서 생긴다. 경계를 실제로 넘어 보는 테스트가 필요하다.

## 핵심 개념

### 테스트의 층

| 층 | 범위 | 속도 | 실패 원인 찾기 | 예 |
|---|---|---|---|---|
| 단위 | 함수·클래스 하나 | 밀리초 | 쉽다 | 할인 계산 |
| 통합 | 내 코드 + 실제 협력자 하나 | 수십 ms ~ 초 | 중간 | 저장소 + 실제 DB |
| 계약(contract) | 서비스 간 API 약속 | 빠름 | 중간 | 소비자가 기대하는 응답 스키마 |
| E2E | 사용자 입장에서 전체 시스템 | 초 ~ 분 | 어렵다 | 브라우저로 로그인→주문→결제 |

### 테스트 피라미드

```
          /\        E2E: 적게. 핵심 사용자 여정만
         /  \
        /────\      통합: 경계마다
       /      \
      /────────\    단위: 많이. 대부분의 로직
```

Mike Cohn 이 *Succeeding with Agile* 에서 제시한 그림이다. Ham Vocke 가 martinfowler.com 에 쓴 [The Practical Test Pyramid](https://martinfowler.com/articles/practical-test-pyramid.html)는 이 그림의 핵심을 두 가지로 정리한다. 서로 다른 세분성의 테스트를 쓰고, **위로 갈수록 테스트 수를 줄이라**는 것이다.

이유는 비용이다. E2E 테스트는 브라우저·서버·DB·네트워크를 모두 띄워야 해서 느리고, 그중 하나만 흔들려도 실패한다. 실패해도 "어디가" 깨졌는지 알려 주지 않는다. 같은 검증을 아래층에서 할 수 있으면 아래층에서 한다.

피라미드가 뒤집혀 E2E 가 가장 많은 모양을 흔히 "아이스크림 콘" 이라고 부른다. 테스트 스위트가 한 시간씩 걸리고, 매번 몇 개씩 이유 없이 실패하는 팀의 전형이다.

### 통합 테스트를 잘 쓰는 법

- **진짜를 쓴다, 하지만 격리한다.** 운영과 같은 종류의 DB 를 쓰되, 테스트마다 새 스키마나 트랜잭션 롤백으로 서로 오염되지 않게 한다.
- **컨테이너로 의존성을 띄운다.** [Testcontainers](https://testcontainers.com/) 같은 라이브러리는 테스트 코드에서 PostgreSQL, Kafka 같은 의존성을 일회용 컨테이너로 띄우고 끝나면 지운다. "내 PC 에 설치된 DB 버전" 에 의존하지 않게 된다.
- **경계 하나씩.** 저장소 통합 테스트는 DB 와의 경계만, HTTP 클라이언트 통합 테스트는 외부 API 와의 경계만 본다. 한 테스트에서 여러 경계를 동시에 넘으면 사실상 E2E 다.
- **외부 유료·불안정 API 는 계약 테스트로.** 결제사 API 를 매번 진짜로 부를 수 없다면, 그 API 가 약속한 요청·응답 형식을 계약으로 고정하고 양쪽이 각자 계약을 지키는지 검증한다.

### E2E 테스트를 잘 쓰는 법

- **핵심 사용자 여정만.** 회원가입, 로그인, 결제처럼 깨지면 사업이 멈추는 흐름 몇 개만 고른다.
- **사용자가 보는 것으로 요소를 찾는다.** CSS 클래스 이름 대신 역할·레이블·텍스트로 찾으면 화면 구현이 바뀌어도 덜 깨진다. [Playwright](https://playwright.dev/docs/intro) 같은 도구가 이런 방식을 기본으로 권한다.
- **고정 대기(sleep) 대신 조건 대기.** "2초 기다린 뒤 확인" 은 느린 환경에서 실패하고 빠른 환경에서 시간을 낭비한다. "버튼이 보일 때까지" 처럼 조건을 기다린다.
- **테스트 데이터를 테스트가 만든다.** 공유 스테이징 DB 에 있는 "테스트용 계정" 에 기대면, 누군가 그 계정을 지우는 날 모든 E2E 가 깨진다.

## 직접 해 보기

표준 라이브러리만으로 두 층을 시연한다. 통합 테스트는 저장소와 **실제 SQL 엔진**([`sqlite3`](https://docs.python.org/3/library/sqlite3.html), 메모리 DB)을 함께 돌리고, E2E 스타일 테스트는 **실제 HTTP 서버**를 띄운 뒤 바깥에서 요청을 보낸다.

```python
import json, sqlite3, sys, threading, unittest, urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

# ----- 애플리케이션: 저장소(DB) + HTTP 핸들러 -----
class TodoRepo:
    def __init__(self, conn):
        self.conn = conn
        conn.execute("CREATE TABLE IF NOT EXISTS todo (id INTEGER PRIMARY KEY, title TEXT NOT NULL UNIQUE)")
    def add(self, title):
        cur = self.conn.execute("INSERT INTO todo(title) VALUES (?)", (title,))
        self.conn.commit()
        return cur.lastrowid
    def all(self):
        return [{"id": r[0], "title": r[1]} for r in self.conn.execute("SELECT id, title FROM todo ORDER BY id")]

def make_handler(repo):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, code, body):
            data = json.dumps(body, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        def do_GET(self):
            self._send(200, repo.all())
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            try:
                self._send(201, {"id": repo.add(body["title"])})
            except sqlite3.IntegrityError:
                self._send(409, {"error": "duplicate title"})
        def log_message(self, *args):
            pass                                   # 테스트 출력 조용히
    return Handler

# ----- 통합 테스트: 저장소 + 진짜 SQL 엔진 -----
class RepoIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.repo = TodoRepo(sqlite3.connect(":memory:"))   # 테스트마다 새 DB
    def test_unique_constraint_is_enforced_by_db(self):
        self.repo.add("우유 사기")
        with self.assertRaises(sqlite3.IntegrityError):
            self.repo.add("우유 사기")

# ----- E2E 스타일 테스트: 실제 HTTP 서버를 띄우고 바깥에서 호출 -----
class HttpEndToEndTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        conn = sqlite3.connect(":memory:", check_same_thread=False)
        cls.server = HTTPServer(("127.0.0.1", 0), make_handler(TodoRepo(conn)))  # 0 = 빈 포트
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def call(self, method, data=None):
        req = urllib.request.Request(self.base + "/todos", method=method,
                                     data=json.dumps(data).encode() if data else None,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_create_list_and_duplicate(self):
        self.assertEqual(self.call("POST", {"title": "글쓰기"}), (201, {"id": 1}))
        self.assertEqual(self.call("GET"), (200, [{"id": 1, "title": "글쓰기"}]))
        self.assertEqual(self.call("POST", {"title": "글쓰기"})[0], 409)

if __name__ == "__main__":
    suite = unittest.TestSuite()
    for case in (RepoIntegrationTest, HttpEndToEndTest):
        suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(case))
    unittest.TextTestRunner(stream=sys.stdout, verbosity=2).run(suite)
```

실행 결과(시간 값은 환경마다 다르다):

```
test_unique_constraint_is_enforced_by_db (__main__.RepoIntegrationTest.test_unique_constraint_is_enforced_by_db) ... ok
test_create_list_and_duplicate (__main__.HttpEndToEndTest.test_create_list_and_duplicate) ... ok

----------------------------------------------------------------------
Ran 2 tests in 0.662s

OK
```

통합 테스트가 확인한 것은 "중복 제목을 막는 것은 **DB 의 UNIQUE 제약**이다" 라는 사실이다. 저장소를 `Mock` 으로 바꾼 단위 테스트에서는 이 제약이 존재하지 않는다. E2E 테스트는 그 제약 위반이 HTTP 층까지 올라와 **409 응답**으로 바뀌는지, 즉 층 사이의 번역까지 확인했다.

두 가지를 더 짚는다. 서버를 포트 `0` 으로 띄워 운영체제가 빈 포트를 고르게 했다. 고정 포트를 쓰면 병렬로 도는 다른 테스트와 충돌한다. 그리고 단위 테스트 수백 개가 수십 밀리초에 끝나는 것과 비교하면, 테스트 두 개에 0.6초가 넘게 걸렸다. 대부분은 서버 종료를 기다리는 시간이다. 위층 테스트가 비싼 이유가 이런 데서 쌓인다.

## 현업에서는

- **CI 단계를 층별로 나눈다.** 단위 테스트는 모든 커밋에서, 통합 테스트는 PR 마다, E2E 는 병합 후나 배포 전 스테이징에서 돈다. 빠른 실패를 앞에 둔다.
- **스테이징 환경도 코드로.** 홈랩 k3s 클러스터에 네임스페이스 하나를 E2E 전용으로 두고, 테스트 시작 시 매니페스트로 앱과 DB 를 띄우고 끝나면 네임스페이스째 지우는 방식이 깔끔하다. 테스트가 남긴 쓰레기가 다음 실행에 섞이지 않는다.
- **불안정한 E2E 는 격리한다.** 이유 없이 가끔 실패하는 테스트는 "재시도로 덮기" 보다 별도 목록으로 빼 원인을 찾는 편이 낫다. 재시도는 실제 경쟁 조건 버그까지 덮는다.
- **운영에서도 E2E 가 돈다.** 합성 모니터링(synthetic monitoring)은 운영 환경에 주기적으로 로그인·검색 같은 요청을 보내 핵심 여정이 살아 있는지 확인한다. 배포 직후 스모크 테스트도 같은 발상이다.

## 확인 문제

1. 단위 테스트가 모두 통과해도 통합 테스트가 필요한 이유를 "테스트 더블의 가정" 이라는 말로 설명하라.
2. 테스트 피라미드에서 위층으로 갈수록 테스트 수를 줄이는 이유 두 가지는?
3. E2E 테스트에서 고정 시간 `sleep` 대신 조건 대기를 써야 하는 이유는?
4. 위 예제에서 HTTP 서버를 포트 0 으로 띄운 이유는?
5. 위 예제의 통합 테스트는 단위 테스트로는 확인할 수 없는 무엇을 확인했는가?

### 풀이

1. 테스트 더블은 협력자가 어떻게 동작할지에 대한 작성자의 가정을 흉내 낼 뿐이라, 가정이 틀리면 테스트도 같이 틀린다. 실제 협력자와 맞물려 봐야 가정을 검증할 수 있다.
2. 느리고 비싸며, 여러 구성 요소 중 하나만 흔들려도 실패하고, 실패 원인을 좁히기 어렵다(이 중 둘).
3. 고정 대기는 느린 환경에서는 부족해 실패하고 빠른 환경에서는 시간을 낭비한다. 조건 대기는 준비되는 즉시 진행한다.
4. 운영체제가 사용 가능한 포트를 고르게 해, 다른 프로세스나 병렬 테스트와 포트가 충돌하지 않게 하려고.
5. 중복 제목을 막는 UNIQUE 제약이 실제 DB 스키마에 존재하고, 위반 시 `IntegrityError` 가 발생한다는 사실.

## 더 읽을거리 (References)

- Ham Vocke, [The Practical Test Pyramid](https://martinfowler.com/articles/practical-test-pyramid.html), martinfowler.com
- [Testcontainers](https://testcontainers.com/) 공식 사이트
- Playwright 문서, [Installation / Getting started](https://playwright.dev/docs/intro)
- Python 문서, [sqlite3 — DB-API 2.0 interface for SQLite databases](https://docs.python.org/3/library/sqlite3.html)
- Mike Cohn, *Succeeding with Agile: Software Development Using Scrum*, Addison-Wesley, 2009 (서지 정보)
