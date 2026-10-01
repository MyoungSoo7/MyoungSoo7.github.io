---
layout: post
title: "도커로 DB 생성·삭제 UI와 서버 로그 UI를 직접 만들어 보기 — 표준 라이브러리 200줄과 함정 6개"
date: 2026-10-01 20:58:00 +0900
categories: [devops, docker]
tags: [docker, docker-engine-api, postgres, server-sent-events, security, python]
---

"DB 하나 띄워 줘"라는 요청이 올 때마다 `docker run -e POSTGRES_PASSWORD=...`를 치는 대신 **버튼 하나로 DB 컨테이너를 만들고 지우고, 그 DB의 서버 로그를 브라우저에서 실시간으로 보는 화면**을 직접 만들어 봤다. 결론부터 말하면 기능은 200줄로 끝난다. 하지만 이 UI는 **사실상 root 권한을 웹 버튼으로 노출하는 물건**이다. 그래서 코드보다 함정 쪽이 더 길어졌다.

글의 숫자와 동작은 전부 로컬 Docker Engine 29.6.2(API 1.55)에서 실제로 돌려서 확인했다. 전체 코드는 맨 아래 부록에 있다.

## 1. 핵심 아이디어 — UI는 Docker Engine API의 또 다른 클라이언트일 뿐

`docker` CLI도 결국 Docker 데몬의 **REST API**를 부르는 클라이언트다. 이 API는 로컬에서는 유닉스 소켓(`/var/run/docker.sock`)으로 열려 있다([Docker Engine API](https://docs.docker.com/reference/api/engine/)). 그러니 웹 UI도 CLI를 셸로 호출할 필요 없이 같은 API를 직접 부르면 된다.

```
브라우저 ──HTTP(JSON)──▶ dbui.py (127.0.0.1:8765) ──HTTP over unix socket──▶ dockerd
   ▲                                                                            │
   └──────── text/event-stream (SSE) ◀── 로그 스트림 역다중화 ◀── /containers/{id}/logs?follow=1
```

| UI 동작 | Engine API 호출 |
| --- | --- |
| 목록 | `GET /containers/json?all=1&filters={"label":["dbui.managed=true"]}` |
| 생성 | `POST /containers/create?name=…` → `POST /containers/{id}/start` → `GET /containers/{id}/json`(할당된 포트 확인) |
| 삭제 | `DELETE /containers/{id}?force=1&v=1` → (선택) `DELETE /volumes/{name}` |
| 로그 | `GET /containers/{id}/logs?follow=1&stdout=1&stderr=1&timestamps=1&tail=200` |

Python 표준 라이브러리만 썼다. `http.client.HTTPConnection`의 `connect()`만 유닉스 소켓으로 바꾸면 된다.

```python
class UnixHTTPConnection(http.client.HTTPConnection):
    def __init__(self, path, timeout=None):
        super().__init__("localhost", timeout=timeout)
        self.path = path

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(self.path)
```

## 2. DB 생성 — 브라우저가 고르는 건 "엔진 이름"뿐

가장 중요한 설계 결정은 이것이다. **브라우저가 보낸 값을 Docker API 요청 본문에 그대로 넣지 않는다.** 이미지, 환경변수, 마운트를 클라이언트가 정할 수 있으면 누군가 `"Binds": ["/:/host"]`를 넣는 순간 호스트 전체가 넘어간다(3장 참고). 그래서 UI는 `{"name": "shop-dev", "engine": "postgres"}`만 받는다. 나머지는 서버의 허용 목록이 정한다.

```python
ENGINES = {
    "postgres": {"image": "postgres:16-alpine", "port": "5432/tcp",
                 "data": "/var/lib/postgresql/data",
                 "env": lambda pw: [f"POSTGRES_PASSWORD={pw}"], "cmd": None},
    "mysql":    {...}, "redis": {...},
}

body = {
    "Image": spec["image"],
    "Env": spec["env"](pw),                      # pw = secrets.token_urlsafe(18)
    "Labels": {LABEL: "true", "dbui.engine": engine},
    "ExposedPorts": {spec["port"]: {}},
    "HostConfig": {
        "PortBindings": {spec["port"]: [{"HostIp": "127.0.0.1", "HostPort": ""}]},
        "Mounts": [{"Type": "volume", "Source": f"dbui-{name}-data", "Target": spec["data"]}],
        "Memory": 512 * 1024 * 1024,
        "RestartPolicy": {"Name": "unless-stopped"},
    },
}
```

설계 포인트는 다음과 같다.

- **`HostPort: ""`** — 빈 값이면 Docker가 비어 있는 포트를 고른다. 실측에서는 64681, 64683이 할당됐다. 고정 포트를 쓰면 DB가 두 개만 돼도 충돌한다.
- **`HostIp: "127.0.0.1"`** — 지정하지 않으면 모든 인터페이스에 바인딩된다. 개발용 DB를 LAN에 열어 둘 이유가 없다.
- **라벨 `dbui.managed=true`** — 목록 조회, 로그 조회, 삭제는 모두 이 라벨이 있는 컨테이너에만 동작한다. 같은 호스트의 다른 컨테이너는 이름을 알아도 건드릴 수 없다.
- **비밀번호는 서버가 생성**하고 생성 응답에서 한 번만 보여 준다. 단, 이것이 "안전하게 숨겨졌다"는 뜻은 아니다(함정 ④).

## 3. 서버 로그 UI — 8바이트 헤더 역다중화 + SSE

로그는 두 단계를 거친다.

**① Docker가 주는 스트림을 푼다.** TTY 없이 띄운 컨테이너의 로그는 stdout과 stderr가 한 스트림에 섞여서 온다. 각 조각 앞에는 8바이트 헤더가 붙는다. `[스트림 종류(1=stdout, 2=stderr), 0, 0, 0, 크기(4바이트 big-endian)]` 뒤에 그 크기만큼의 본문이 오는 구조다([moby 클라이언트 소스 주석](https://github.com/moby/moby/blob/v28.5.2/client/container_attach.go)). 이 헤더를 안 풀고 그대로 화면에 찍으면 줄마다 깨진 바이너리 문자가 섞여 나온다.

```python
def demux(resp):
    while True:
        hdr = resp.read(8)
        if len(hdr) < 8:
            return
        stype, size = hdr[0], struct.unpack(">I", hdr[4:])[0]
        payload = resp.read(size)
        yield ("stderr" if stype == 2 else "stdout"), payload.decode("utf-8", "replace")
```

**② 브라우저로는 Server-Sent Events(SSE)로 흘린다.** 로그는 서버에서 브라우저로 한 방향으로만 흐르므로 WebSocket까지 갈 필요가 없다. `Content-Type: text/event-stream`으로 응답하고 `data: …\n\n` 블록을 계속 쓰면 된다. 브라우저 쪽은 `EventSource` 하나로 받는다([MDN: Using server-sent events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events), [MDN: EventSource](https://developer.mozilla.org/en-US/docs/Web/API/EventSource)).

```javascript
es = new EventSource(`/api/dbs/${name}/logs`);
es.onmessage = (e) => {
  const {stream, line} = JSON.parse(e.data);
  const div = document.createElement("div");
  div.className = stream; div.textContent = line;   // innerHTML 금지
  $("log").append(div);
};
```

**실측 결과**: 로그 창을 열어 둔 상태에서 일부러 틀린 비밀번호로 접속했다. 그러자 `FATAL:  password authentication failed for user "postgres"` 줄이 **`stderr`로 분류된 채 바로** 화면에 도착했다. PostgreSQL은 서버 로그를 stderr로 내보내므로, stdout과 stderr를 구분하지 않으면 정작 중요한 줄이 일반 출력과 섞인다.

## 4. 직접 돌려 보고 확인한 함정 6개

### ① Docker 소켓에 닿는 것 = 호스트 root

Docker 공식 보안 문서는 이렇게 말한다. "only trusted users should be allowed to control your Docker daemon." 컨테이너에 호스트의 `/`를 제한 없이 마운트할 수 있기 때문이다([Docker Engine security — daemon attack surface](https://docs.docker.com/engine/security/#docker-daemon-attack-surface)). CIS Docker Benchmark 1.4도 같은 이유로 docker 그룹 사용자를 사실상 root로 취급한다.

이 UI를 만든다는 것은 **그 권한을 HTTP 엔드포인트로 다시 감싸는 일**이다. 그래서 이 데모는 다음처럼 막아 두었다.

- `127.0.0.1`에만 바인딩한다.
- 허용 목록에 있는 엔진만 받는다.
- 라벨이 없는 컨테이너는 거절한다. 실측: 라벨 없는 `notmine-x` 삭제 요청 → `403`, 컨테이너는 그대로 남음.

여러 사람이 쓰는 서버에 올릴 거라면 인증이 반드시 필요하다. 그리고 웹 서버 자체에는 소켓을 직접 주지 말고, 허용 목록이 있는 별도 프로세스를 사이에 두는 것이 맞다. 데몬 자체를 root 없이 띄우는 [Rootless mode](https://docs.docker.com/engine/security/rootless/)도 피해 범위를 줄이는 선택지다.

### ② `docker rm -v`는 이름 붙은 볼륨을 안 지운다

삭제 API에 `v=1`을 붙이면 볼륨도 지워질 것 같지만, 공식 문서 기준으로 지워지는 것은 **익명 볼륨뿐이다**. "if a volume was specified with a name, it will not be removed."([docker container rm](https://docs.docker.com/reference/cli/docker/container/rm/))

실측: `-v dbui-vtest-data:/data`로 만든 컨테이너를 `docker rm -v`로 지웠다. 컨테이너는 사라졌지만 `dbui-vtest-data` 볼륨은 그대로 남았다. UI에서 "삭제"를 눌렀는데 디스크가 계속 차는 원인이 이것이다. 그래서 이 데모는 삭제 시 "데이터 볼륨도 지울까?"를 따로 묻고 `DELETE /volumes/{name}`을 **명시적으로** 호출한다. 반대로 "실수로 지웠는데 데이터는 살리고 싶다"는 경우에는 이 동작이 안전장치가 된다.

### ③ postgres 이미지는 컨테이너 안 localhost 접속을 비밀번호 없이 받는다

비밀번호 인증이 되는지 확인하려고 `docker exec`로 컨테이너 안에서 `psql -h 127.0.0.1`에 **틀린 비밀번호**를 넣었다. 접속이 성공했다. 버그가 아니라 의도된 설정이다. 이미지가 만든 `pg_hba.conf`를 보면 다음과 같다.

```
host    all             all             127.0.0.1/32            trust
host all all all scram-sha-256
```

공식 이미지 문서도 "sets up `trust` authentication locally … a password will be required if connecting from a different host/container"라고 적어 두었다([postgres Official Image](https://hub.docker.com/_/postgres)). 컨테이너 IP로 다시 접속하자 그제야 `password authentication failed`가 났다. **비밀번호가 동작하는지 테스트하려면 컨테이너 밖에서, 또는 컨테이너 IP로 해야 한다.** 안에서 테스트하면 항상 "된다"는 결과가 나온다.

### ④ 비밀번호를 한 번만 보여 줘도 `docker inspect`에는 남는다

UI는 비밀번호를 한 번만 보여 주지만, 그것은 화면 얘기일 뿐이다. 환경변수로 넣은 값은 컨테이너 설정에 평문으로 저장된다. 실측: `docker inspect`의 `Config.Env`에서 `POSTGRES_PASSWORD`가 그대로 보였다. 소켓 접근 권한이 있는 사람은 누구나 읽을 수 있다. postgres 이미지는 대안으로 `POSTGRES_PASSWORD_FILE`처럼 `_FILE`을 붙인 변수로 **파일에서 읽는 방식**을 지원한다([postgres Official Image — Docker Secrets](https://hub.docker.com/_/postgres)).

### ⑤ 127.0.0.1에 띄워도 다른 웹사이트가 호출할 수 있다

로컬 전용 서버는 안전하다고 생각하기 쉽다. 하지만 사용자가 연 아무 웹페이지나 `http://127.0.0.1:8765/api/dbs`로 요청을 보낼 수 있다. 막는 방법은 두 가지다.

- **CSRF**: `Content-Type: application/json`만 받는다. JSON 요청은 CORS의 "단순 요청"이 아니라서 다른 출처에서는 preflight 단계에서 막힌다. 실측: `text/plain` POST → `415`.
- **DNS rebinding**: 공격자 도메인이 `127.0.0.1`로 다시 resolve되면 같은 출처처럼 보이게 된다. 그래서 `Host` 헤더가 `127.0.0.1:8765` 또는 `localhost:8765`가 아니면 거절한다. 실측: `Host: evil.example:8765` → `403`.

### ⑥ 로그는 신뢰할 수 없는 입력이다

DB 로그에는 사용자가 보낸 쿼리, 사용자 이름, 에러 메시지가 그대로 찍힌다. 접속 시도에 `<img src=x onerror=…>`를 사용자 이름으로 넣으면 그 문자열이 로그로 들어온다. 그래서 로그 줄은 반드시 `textContent`로 넣는다. `innerHTML`로 넣으면 로그 뷰어가 XSS 통로가 된다. 데모는 화면에 2,000줄까지만 남기고 앞쪽을 지운다. 오래 띄워 둔 탭이 메모리를 계속 먹는 것을 막기 위해서다.

## 5. 아직 안 한 것

- **인증과 감사 로그가 없다.** 지금은 1인용 로컬 도구다. 여러 사람이 쓰려면 누가 언제 무엇을 만들고 지웠는지 남겨야 한다.
- **원격 Docker 호스트에 붙지 않는다.** 원격은 TLS 클라이언트 인증서나 SSH로 연결한다. 공식 문서도 그 인증서를 "root 비밀번호처럼" 다루라고 경고한다([Protect the Docker daemon socket](https://docs.docker.com/engine/security/protect-access/)).
- **로그 보존은 Docker 로깅 드라이버에 달려 있다.** 이 UI는 `docker logs`가 돌려주는 만큼만 보여 준다. 컨테이너를 지우면 로그도 같이 사라진다. 장기 보관은 별도 수집기(예: Fluent Bit → Elasticsearch)가 할 일이다.
- **쿠버네티스라면 이 구조를 그대로 옮기면 안 된다.** 같은 일을 하려면 Docker 소켓이 아니라 RBAC로 범위를 좁힌 ServiceAccount로 API 서버를 불러야 한다.

## References

1. Docker Docs — [Docker Engine API reference](https://docs.docker.com/reference/api/engine/) (본문 호출은 [v1.43](https://docs.docker.com/reference/api/engine/version/v1.43/) 기준 경로)
2. moby/moby — [client/container_attach.go, 다중화 스트림 형식 주석](https://github.com/moby/moby/blob/v28.5.2/client/container_attach.go)
3. Docker Docs — [Docker Engine security: Docker daemon attack surface](https://docs.docker.com/engine/security/#docker-daemon-attack-surface)
4. Docker Docs — [Rootless mode](https://docs.docker.com/engine/security/rootless/)
5. Docker Docs — [Protect the Docker daemon socket](https://docs.docker.com/engine/security/protect-access/)
6. Docker Docs — [docker container rm (`--volumes`)](https://docs.docker.com/reference/cli/docker/container/rm/)
7. Docker Hub — [postgres Official Image](https://hub.docker.com/_/postgres) / [README 원문(docker-library/docs)](https://github.com/docker-library/docs/blob/master/postgres/README.md)
8. MDN — [Using server-sent events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events), [EventSource](https://developer.mozilla.org/en-US/docs/Web/API/EventSource)
9. CIS Docker Benchmark 1.4 "Ensure only trusted users are allowed to control Docker daemon" ([Tenable 감사 항목 요약](https://www.tenable.com/audits/items/CIS_Docker_Community_Edition_L1_Linux_Host_OS_v1.1.0.audit:4e3617a32a4d2e545fb6bd50d3fbaba6))

## 부록 — 전체 코드

실행: `python3 dbui.py` 후 `http://127.0.0.1:8765`. 의존성은 없다. Docker Desktop(macOS)에서는 `/var/run/docker.sock`이 `~/.docker/run/docker.sock`의 심볼릭 링크다. 링크가 없으면 `DOCKER_SOCK` 환경변수로 경로를 지정한다.

### dbui.py

```python
#!/usr/bin/env python3
"""Docker 로 DB 컨테이너를 만들고/지우고, 로그를 브라우저로 스트리밍하는 최소 UI.

표준 라이브러리만 쓴다. Docker Engine API 를 유닉스 소켓으로 직접 부른다.
"""
import http.client, json, os, re, secrets, socket, struct, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import quote

SOCK = os.environ.get("DOCKER_SOCK", "/var/run/docker.sock")
API = "/v1.43"            # 이 버전 이상을 지원하는 엔진이면 동작
LISTEN = ("127.0.0.1", int(os.environ.get("PORT", "8765")))
LABEL = "dbui.managed"    # 이 라벨이 붙은 컨테이너만 보고, 지운다
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,30}$")

# 허용 목록: UI 가 받는 건 '엔진 이름'뿐이다. 이미지·환경변수·마운트는 서버가 정한다.
ENGINES = {
    "postgres": {"image": "postgres:16-alpine", "port": "5432/tcp",
                 "data": "/var/lib/postgresql/data",
                 "env": lambda pw: [f"POSTGRES_PASSWORD={pw}"], "cmd": None},
    "mysql":    {"image": "mysql:8.0", "port": "3306/tcp", "data": "/var/lib/mysql",
                 "env": lambda pw: [f"MYSQL_ROOT_PASSWORD={pw}"], "cmd": None},
    "redis":    {"image": "redis:7-alpine", "port": "6379/tcp", "data": "/data",
                 "env": lambda pw: [], "cmd": lambda pw: ["redis-server", "--requirepass", pw]},
}


class UnixHTTPConnection(http.client.HTTPConnection):
    def __init__(self, path, timeout=None):
        super().__init__("localhost", timeout=timeout)
        self.path = path

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(self.path)


def docker(method, path, body=None, stream=False):
    conn = UnixHTTPConnection(SOCK, timeout=None if stream else 30)
    data = json.dumps(body).encode() if body is not None else None
    conn.request(method, API + path, body=data,
                 headers={"Content-Type": "application/json"} if data else {})
    resp = conn.getresponse()
    if stream:
        return resp
    raw = resp.read()
    conn.close()
    if resp.status >= 400:
        raise RuntimeError(f"docker {method} {path} -> {resp.status} {raw[:200]!r}")
    return json.loads(raw) if raw else None


def managed(name):
    """이름이 같아도 우리 라벨이 없으면 남의 컨테이너다 — 손대지 않는다."""
    info = docker("GET", f"/containers/{quote(name)}/json")
    if info["Config"]["Labels"].get(LABEL) != "true":
        raise PermissionError(f"{name} 은(는) 이 UI 가 만든 컨테이너가 아니다")
    return info


def list_dbs():
    flt = quote(json.dumps({"label": [f"{LABEL}=true"]}))
    out = []
    for c in docker("GET", f"/containers/json?all=1&filters={flt}"):
        ports = [f"{p['IP']}:{p['PublicPort']}" for p in c.get("Ports", []) if p.get("PublicPort")]
        out.append({"name": c["Names"][0].lstrip("/"), "engine": c["Labels"].get("dbui.engine"),
                    "state": c["State"], "status": c["Status"], "ports": ports})
    return out


def create_db(name, engine):
    if not NAME_RE.match(name or ""):
        raise ValueError("이름은 소문자·숫자·하이픈 2~31자")
    spec = ENGINES.get(engine)
    if not spec:
        raise ValueError(f"지원 엔진: {', '.join(ENGINES)}")
    pw = secrets.token_urlsafe(18)
    body = {
        "Image": spec["image"],
        "Env": spec["env"](pw),
        "Labels": {LABEL: "true", "dbui.engine": engine},
        "ExposedPorts": {spec["port"]: {}},
        "HostConfig": {
            # 호스트 루프백에만, 빈 포트를 Docker 가 고르게 한다
            "PortBindings": {spec["port"]: [{"HostIp": "127.0.0.1", "HostPort": ""}]},
            "Mounts": [{"Type": "volume", "Source": f"dbui-{name}-data", "Target": spec["data"]}],
            "Memory": 512 * 1024 * 1024,
            "RestartPolicy": {"Name": "unless-stopped"},
        },
    }
    if spec["cmd"]:
        body["Cmd"] = spec["cmd"](pw)
    docker("POST", f"/containers/create?name={quote(name)}", body)
    docker("POST", f"/containers/{quote(name)}/start")
    info = docker("GET", f"/containers/{quote(name)}/json")
    hp = info["NetworkSettings"]["Ports"][spec["port"]][0]["HostPort"]
    # 비밀번호는 이 응답에서 한 번만 보여준다 (Env 에는 남는다 — 본문 참고)
    return {"name": name, "engine": engine, "host": "127.0.0.1", "port": int(hp), "password": pw}


def delete_db(name, keep_data):
    managed(name)
    # v=1 은 '익명' 볼륨만 지운다. 이름 붙은 볼륨은 따로 지워야 한다.
    docker("DELETE", f"/containers/{quote(name)}?force=1&v=1")
    if not keep_data:
        docker("DELETE", f"/volumes/{quote('dbui-' + name + '-data')}")
    return {"deleted": name, "volume_kept": keep_data}


def demux(resp):
    """TTY 없는 컨테이너의 로그 스트림: [type,0,0,0,size(4B BE)] + payload 반복."""
    while True:
        hdr = resp.read(8)
        if len(hdr) < 8:
            return
        stype, size = hdr[0], struct.unpack(">I", hdr[4:])[0]
        payload = resp.read(size)
        yield ("stderr" if stype == 2 else "stdout"), payload.decode("utf-8", "replace")


PAGE = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html"), "rb").read()


class Handler(BaseHTTPRequestHandler):
    def _json(self, code, obj):
        b = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _guard(self):
        # DNS rebinding 방어: Host 헤더가 우리 주소가 아니면 거절
        if self.headers.get("Host") not in (f"127.0.0.1:{LISTEN[1]}", f"localhost:{LISTEN[1]}"):
            self._json(403, {"error": "bad host"}); return False
        return True

    def do_GET(self):
        if not self._guard():
            return
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers(); self.wfile.write(PAGE); return
        if self.path == "/api/dbs":
            return self._json(200, list_dbs())
        m = re.fullmatch(r"/api/dbs/([a-z0-9-]+)/logs", self.path)
        if m:
            return self._logs(m.group(1))
        self._json(404, {"error": "not found"})

    def do_POST(self):
        if not self._guard():
            return
        # CSRF 방어: application/json 은 '단순 요청'이 아니라 다른 출처에선 preflight 에 막힌다
        if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
            return self._json(415, {"error": "application/json only"})
        n = int(self.headers.get("Content-Length", 0))
        req = json.loads(self.rfile.read(n) or b"{}")
        try:
            if self.path == "/api/dbs":
                return self._json(201, create_db(req.get("name"), req.get("engine")))
            m = re.fullmatch(r"/api/dbs/([a-z0-9-]+)/delete", self.path)
            if m:
                return self._json(200, delete_db(m.group(1), bool(req.get("keep_data"))))
            self._json(404, {"error": "not found"})
        except PermissionError as e:
            self._json(403, {"error": str(e)})
        except (ValueError, RuntimeError) as e:
            self._json(400, {"error": str(e)})

    def _logs(self, name):
        try:
            managed(name)
        except Exception as e:
            return self._json(403, {"error": str(e)})
        resp = docker("GET", f"/containers/{quote(name)}/logs"
                      "?follow=1&stdout=1&stderr=1&timestamps=1&tail=200", stream=True)
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        try:
            for stream, text in demux(resp):
                for line in text.splitlines():
                    msg = json.dumps({"stream": stream, "line": line}, ensure_ascii=False)
                    self.wfile.write(f"data: {msg}\n\n".encode())
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass  # 브라우저 탭을 닫으면 여기로 온다
        finally:
            resp.close()

    def log_message(self, fmt, *args):
        sys.stderr.write("[dbui] " + fmt % args + "\n")


if __name__ == "__main__":
    print(f"http://{LISTEN[0]}:{LISTEN[1]}  (docker sock: {SOCK})")
    ThreadingHTTPServer(LISTEN, Handler).serve_forever()
```

### index.html

```html
<!doctype html>
<meta charset="utf-8">
<title>dbui</title>
<style>
  body { font: 14px system-ui, sans-serif; margin: 2rem; max-width: 960px; }
  table { border-collapse: collapse; width: 100%; }
  td, th { border-bottom: 1px solid #ddd; padding: .4rem; text-align: left; }
  #log { background: #111; color: #ddd; height: 320px; overflow: auto;
         font: 12px ui-monospace, monospace; padding: .5rem; white-space: pre-wrap; }
  .stderr { color: #f88; }
</style>
<h1>DB 컨테이너</h1>
<form id="f">
  <input id="name" placeholder="이름 (예: shop-dev)" required>
  <select id="engine"><option>postgres</option><option>mysql</option><option>redis</option></select>
  <button>생성</button>
</form>
<pre id="out"></pre>
<table><thead><tr><th>이름</th><th>엔진</th><th>상태</th><th>포트</th><th></th></tr></thead>
<tbody id="rows"></tbody></table>
<h2>로그 <small id="who"></small></h2>
<div id="log"></div>
<script>
const $ = (id) => document.getElementById(id);
const post = (url, body) => fetch(url, {
  method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body),
}).then(async (r) => ({ok: r.ok, body: await r.json()}));

async function refresh() {
  const dbs = await (await fetch("/api/dbs")).json();
  $("rows").replaceChildren(...dbs.map((d) => {
    const tr = document.createElement("tr");
    for (const v of [d.name, d.engine, d.status, d.ports.join(", ")]) {
      const td = document.createElement("td"); td.textContent = v; tr.append(td);
    }
    const td = document.createElement("td");
    const logs = document.createElement("button"); logs.textContent = "로그";
    logs.onclick = () => tail(d.name);
    const del = document.createElement("button"); del.textContent = "삭제";
    del.onclick = async () => {
      if (prompt(`지우려면 이름을 입력: ${d.name}`) !== d.name) return;
      const keep = confirm("데이터 볼륨은 남길까요? (확인=남김, 취소=같이 삭제)");
      const r = await post(`/api/dbs/${d.name}/delete`, {keep_data: keep});
      $("out").textContent = JSON.stringify(r.body, null, 2); refresh();
    };
    td.append(logs, " ", del); tr.append(td); return tr;
  }));
}

let es;
function tail(name) {
  if (es) es.close();                      // 탭당 연결 하나만 유지
  $("log").replaceChildren(); $("who").textContent = name;
  es = new EventSource(`/api/dbs/${name}/logs`);
  es.onmessage = (e) => {
    const {stream, line} = JSON.parse(e.data);
    const div = document.createElement("div");
    div.className = stream; div.textContent = line;   // innerHTML 금지: 로그는 신뢰할 수 없는 입력
    $("log").append(div);
    while ($("log").childElementCount > 2000) $("log").firstChild.remove();
    $("log").scrollTop = $("log").scrollHeight;
  };
}

$("f").onsubmit = async (e) => {
  e.preventDefault();
  const r = await post("/api/dbs", {name: $("name").value, engine: $("engine").value});
  $("out").textContent = JSON.stringify(r.body, null, 2)
    + (r.ok ? "\n\n※ 비밀번호는 지금 한 번만 표시됩니다." : "");
  refresh();
};
refresh(); setInterval(refresh, 5000);
</script>
```
