---
layout: post
title: "[CS300 #208] REST API 설계 — 자원, 메서드, 상태 코드의 약속"
date: 2026-10-10 21:28:00 +0900
categories: [cs]
tags: [cs300, web, rest, http, api-design]
---

컴퓨터공학 300 주제 시리즈의 208번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

REST 는 Roy Fielding 이 정리한 아키텍처 스타일이고, 실무의 REST API 설계란 자원을 URI 로 이름 붙이고 HTTP 메서드·상태 코드·헤더의 표준 의미를 그대로 지켜서, 클라이언트와 중간 장치(캐시·프록시)가 별도 설명 없이도 동작을 예측하게 만드는 일이다.

## 왜 필요한가

API 는 한번 공개하면 바꾸기 어렵다. 모바일 앱처럼 사용자가 업데이트를 미루는 클라이언트가 붙어 있으면, 실수한 설계를 몇 년씩 들고 가야 한다.

설계가 HTTP 의미를 어기면 비용이 숨어서 나타난다.

- `GET /deleteUser?id=3` 처럼 GET 으로 상태를 바꾸면, 링크 미리보기 봇이나 프리페치가 그 주소를 "읽기만" 하려다 데이터를 지운다.
- 모든 오류를 `200 OK` 에 `{"success": false}` 로 보내면, 모니터링·재시도·캐시가 실패를 성공으로 취급한다.
- 같은 주문 요청이 네트워크 재시도로 두 번 들어와 결제가 두 번 된다.

HTTP 는 이런 문제의 해법을 이미 표준으로 갖고 있다. REST API 설계는 그 표준을 존중하는 일에 가깝다.

## 핵심 개념

### REST 의 제약 조건

Fielding 은 2000년 박사 논문 5장에서 REST 를 여러 제약 조건의 조합으로 정의했다.

| 제약 | 뜻 | 얻는 것 |
|---|---|---|
| 클라이언트-서버 | 관심사 분리 | 양쪽이 독립적으로 진화 |
| 무상태(stateless) | 요청마다 필요한 정보를 다 담는다 | 서버 수평 확장이 쉬움 |
| 캐시 | 응답이 캐시 가능한지 표시 | 지연·부하 감소 |
| 균일한 인터페이스 | 자원 식별, 표현을 통한 조작, 자기 서술 메시지, 하이퍼미디어 | 범용 클라이언트·중간 장치 |
| 계층화 시스템 | 중간에 프록시·게이트웨이가 끼어도 됨 | 로드 밸런서, CDN |
| 주문형 코드(선택) | 서버가 실행 코드를 보낼 수 있음 | 클라이언트 기능 확장 |

현업에서 "RESTful" 이라 부르는 API 대부분은 하이퍼미디어 제약까지 지키지는 않는다. 그래도 무상태, 캐시, 균일한 인터페이스만 제대로 지켜도 이득이 크다.

### 자원과 URI

URI 는 동사가 아니라 명사, 즉 자원을 가리킨다. 동작은 메서드가 말한다.

```
GET    /orders              주문 목록
POST   /orders              주문 생성
GET    /orders/42           주문 42 조회
PATCH  /orders/42           주문 42 일부 수정
DELETE /orders/42           주문 42 삭제
GET    /orders/42/items     주문 42 의 항목 (하위 자원)
GET    /orders?status=paid&page=2   필터·페이지는 쿼리로
```

"결제 취소"처럼 CRUD 로 표현하기 어색한 동작은 상태 변경으로 보거나(`PATCH /orders/42 {"status": "cancelled"}`), 동작 자체를 자원으로 만든다(`POST /orders/42/cancellations`). 어느 쪽이든 팀 안에서 규칙을 하나로 정하는 것이 중요하다.

### 메서드의 의미: 안전성과 멱등성

RFC 9110 은 메서드의 성질을 정의한다.

| 메서드 | 안전(safe) | 멱등(idempotent) | 쓰임 |
|---|---|---|---|
| GET, HEAD | 예 | 예 | 조회 |
| PUT | 아니오 | 예 | 전체 교체 (없으면 생성 가능) |
| DELETE | 아니오 | 예 | 삭제 |
| POST | 아니오 | 아니오 | 생성, 처리 요청 |
| PATCH | 아니오 | 보장 안 함 | 일부 수정 (RFC 5789) |

**안전**은 서버 상태를 바꾸지 않는다는 뜻이다. 그래서 크롤러와 프리페치가 마음 놓고 GET 을 부른다. **멱등**은 같은 요청을 여러 번 보내도 한 번 보낸 것과 결과가 같다는 뜻이다. 그래서 네트워크 오류 시 PUT 과 DELETE 는 그냥 재시도해도 된다. POST 를 안전하게 재시도하려면 클라이언트가 요청마다 고유 키(흔히 `Idempotency-Key` 헤더)를 보내고 서버가 중복을 걸러 내는 방식을 쓴다.

### 상태 코드

| 코드 | 언제 |
|---|---|
| 200 OK | 성공, 본문 있음 |
| 201 Created | 생성 성공. `Location` 헤더에 새 자원 주소 |
| 204 No Content | 성공, 본문 없음 (삭제 등) |
| 304 Not Modified | 조건부 GET, 캐시본 그대로 써도 됨 |
| 400 Bad Request | 요청 형식 오류 |
| 401 Unauthorized | 인증 필요·실패 |
| 403 Forbidden | 인증은 됐지만 권한 없음 |
| 404 Not Found | 자원 없음 |
| 409 Conflict | 현재 상태와 충돌 |
| 412 Precondition Failed | `If-Match` 등 조건 불일치 |
| 422 Unprocessable Content | 형식은 맞지만 의미상 처리 불가 |
| 429 Too Many Requests | 속도 제한 |
| 5xx | 서버 쪽 오류. 클라이언트 잘못이 아님 |

오류 본문 형식은 직접 만들지 말고 RFC 9457 의 Problem Details(`application/problem+json`)를 쓰면 클라이언트 라이브러리가 일관되게 처리할 수 있다.

### 동시 수정과 조건부 요청

두 사람이 같은 문서를 열고 각자 저장하면 나중 사람이 앞사람의 수정을 덮어쓴다(lost update). HTTP 는 `ETag` 와 `If-Match` 로 이를 막는다. 서버는 자원 버전에 해당하는 `ETag` 를 주고, 클라이언트는 수정할 때 `If-Match: <받은 ETag>` 를 보낸다. 그 사이에 누가 바꿨다면 서버는 `412` 로 거절한다. 낙관적 잠금이다.

### 버전 관리와 페이지

- 깨지는 변경이 필요할 때를 대비해 버전 전략을 정해 둔다(`/v1/` 경로, 헤더 등). 필드 추가처럼 깨지지 않는 변경은 버전 없이 한다. 클라이언트는 모르는 필드를 무시하도록 만든다.
- 큰 목록은 항상 페이지로 나눈다. 데이터가 계속 쌓이는 목록은 `offset` 보다 "마지막으로 본 ID 이후"를 넘기는 커서 방식이 중복·누락에 강하고 깊은 페이지에서도 느려지지 않는다.

## 직접 해 보기

파이썬 표준 라이브러리만으로 할 일(todo) API 를 띄우고 같은 프로세스에서 호출한다. 201 과 `Location`, `ETag`/`If-Match` 낙관적 잠금, 204, Problem Details 형식의 404 를 확인한다.

```python
import json, hashlib, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.request import Request, urlopen
from urllib.error import HTTPError

todos, next_id = {}, 1

def etag(obj):
    return '"' + hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()[:12] + '"'

class Api(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def send(self, code, body=None, headers=None, ctype="application/json"):
        data = json.dumps(body, ensure_ascii=False).encode() if body is not None else b""
        self.send_response(code)
        for k, v in (headers or {}).items(): self.send_header(k, v)
        if data: self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers(); self.wfile.write(data)
    def problem(self, code, title):
        self.send(code, {"type": "about:blank", "title": title, "status": code},
                  ctype="application/problem+json")
    def body(self):
        n = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(n) or b"{}")
    def item(self):
        parts = self.path.strip("/").split("/")
        if len(parts) == 2 and parts[0] == "todos" and parts[1].isdigit():
            return int(parts[1])
        return None

    def do_GET(self):
        if self.path == "/todos":
            return self.send(200, list(todos.values()))
        i = self.item()
        if i not in todos: return self.problem(404, "Not Found")
        self.send(200, todos[i], {"ETag": etag(todos[i])})
    def do_POST(self):
        global next_id
        if self.path != "/todos": return self.problem(405, "Method Not Allowed")
        t = {"id": next_id, "title": self.body()["title"], "done": False}
        todos[next_id] = t; next_id += 1
        self.send(201, t, {"Location": f"/todos/{t['id']}"})
    def do_PUT(self):
        i = self.item()
        if i not in todos: return self.problem(404, "Not Found")
        if self.headers.get("If-Match") != etag(todos[i]):
            return self.problem(412, "Precondition Failed")
        todos[i] = {"id": i, **self.body()}
        self.send(200, todos[i], {"ETag": etag(todos[i])})
    def do_DELETE(self):
        i = self.item()
        if i not in todos: return self.problem(404, "Not Found")
        del todos[i]; self.send(204)

srv = ThreadingHTTPServer(("127.0.0.1", 0), Api)
threading.Thread(target=srv.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{srv.server_port}"

def call(method, path, body=None, headers=None):
    data = json.dumps(body).encode() if body is not None else None
    req = Request(base + path, data=data, method=method, headers=headers or {})
    try:
        with urlopen(req) as r:
            text = r.read().decode()
            loc = r.headers.get("Location")
            print(f"{method:6} {path:9} -> {r.status}  " + (f"[Location: {loc}] " if loc else "") + text)
            return r
    except HTTPError as e:
        print(f"{method:6} {path:9} -> {e.code}  {e.read().decode()}")
        return e

call("POST", "/todos", {"title": "우유 사기"})
r = call("GET", "/todos/1")
tag = r.headers["ETag"]
call("PUT", "/todos/1", {"title": "우유 사기", "done": True}, {"If-Match": '"stale"'})
call("PUT", "/todos/1", {"title": "우유 사기", "done": True}, {"If-Match": tag})
call("DELETE", "/todos/1")
call("GET", "/todos/1")
srv.shutdown()
```

실행 결과(`python3 rest.py`):

```
POST   /todos    -> 201  [Location: /todos/1] {"id": 1, "title": "우유 사기", "done": false}
GET    /todos/1  -> 200  {"id": 1, "title": "우유 사기", "done": false}
PUT    /todos/1  -> 412  {"type": "about:blank", "title": "Precondition Failed", "status": 412}
PUT    /todos/1  -> 200  {"id": 1, "title": "우유 사기", "done": true}
DELETE /todos/1  -> 204  
GET    /todos/1  -> 404  {"type": "about:blank", "title": "Not Found", "status": 404}
```

낡은 `ETag` 로 보낸 첫 PUT 은 412 로 거절되고, 방금 받은 `ETag` 로 보낸 두 번째 PUT 만 성공한다. 같은 DELETE 를 한 번 더 보내면 404 가 오지만 서버 상태(자원이 없음)는 그대로이므로 멱등성은 지켜진다. 멱등성은 응답 코드가 아니라 서버 상태에 대한 성질이다.

## 현업에서는

- **API 리뷰 체크리스트**: GET 이 상태를 바꾸지 않는가, 생성은 201 과 `Location` 을 주는가, 오류가 4xx/5xx 로 구분되는가, 목록에 페이지가 있는가, 동시 수정이 가능한 자원에 버전 검사가 있는가.
- **결제·주문 API**: POST 재시도로 인한 중복 처리를 막으려고 멱등 키를 받는 설계가 흔하다. 클라이언트 타임아웃은 "실패"가 아니라 "모름"이기 때문이다.
- **인그레스와 상태 코드**: 홈랩 k3s 에서도 인그레스 컨트롤러 뒤의 서비스가 오류를 200 으로 내보내면, 인그레스 메트릭의 5xx 비율 알림이 아무것도 잡지 못한다. 상태 코드를 정확히 쓰는 것은 관측성의 출발점이다.
- **문서화**: OpenAPI 명세로 API 를 기술해 두면 문서, 클라이언트 코드 생성, 계약 테스트를 한 원본에서 만든다.

## 확인 문제

1. 안전한 메서드와 멱등 메서드의 차이를 예를 들어 설명하라.
2. POST 요청을 안전하게 재시도하려면 어떻게 설계하는가.
3. 401 과 403 은 각각 언제 쓰는가.
4. `ETag` 와 `If-Match` 로 막는 문제는 무엇이며, 조건이 맞지 않으면 어떤 상태 코드를 주는가.
5. 계속 데이터가 쌓이는 목록에서 offset 페이지보다 커서 페이지가 나은 이유는?

### 풀이

1. 안전은 서버 상태를 바꾸지 않음(GET), 멱등은 여러 번 보내도 결과 상태가 한 번과 같음(PUT, DELETE). 안전한 메서드는 모두 멱등이지만 그 역은 아니다.
2. 클라이언트가 요청마다 고유 멱등 키를 보내고, 서버가 키별 처리 결과를 저장해 중복 요청에는 저장된 결과를 돌려준다.
3. 401 은 인증 정보가 없거나 잘못됐을 때, 403 은 인증은 됐지만 그 자원에 대한 권한이 없을 때.
4. 동시 수정 시 나중 저장이 앞선 수정을 덮어쓰는 lost update. 조건 불일치 시 412 Precondition Failed.
5. 페이지를 넘기는 사이 앞쪽에 데이터가 추가·삭제되면 offset 은 항목이 중복되거나 빠지고, 깊은 offset 은 DB 가 앞부분을 건너뛰느라 느려진다. 커서는 기준 위치 이후를 바로 조회한다.

## 더 읽을거리 (References)

- R. T. Fielding, *Architectural Styles and the Design of Network-based Software Architectures*, Ch.5 REST, UC Irvine, 2000: <https://ics.uci.edu/~fielding/pubs/dissertation/rest_arch_style.htm>
- RFC 9110, *HTTP Semantics*: <https://www.rfc-editor.org/rfc/rfc9110>
- RFC 9457, *Problem Details for HTTP APIs*: <https://www.rfc-editor.org/rfc/rfc9457>
- RFC 5789, *PATCH Method for HTTP*: <https://www.rfc-editor.org/rfc/rfc5789>
