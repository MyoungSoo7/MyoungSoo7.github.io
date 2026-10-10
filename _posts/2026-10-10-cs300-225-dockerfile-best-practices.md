---
layout: post
title: "[CS300 #225] Dockerfile 작성법 — 캐시 순서, 멀티스테이지, 작은 이미지"
date: 2026-10-10 21:45:00 +0900
categories: [cs]
tags: [cs300, devops, docker, dockerfile, build-cache]
---

컴퓨터공학 300 주제 시리즈의 225번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

좋은 Dockerfile 은 "자주 안 바뀌는 것을 위에, 자주 바뀌는 것을 아래에" 두어 빌드 캐시를 살리고, 멀티스테이지로 빌드 도구를 최종 이미지에서 빼고, root 가 아닌 사용자로 실행한다.

## 왜 필요한가

Dockerfile 은 몇 줄만 써도 돌아간다. 그래서 대충 쓰기 쉽다. 대충 쓴 Dockerfile 은 이런 결과를 낳는다.

- 코드 한 줄 고쳤는데 의존성 설치를 처음부터 다시 해서 빌드가 몇 분씩 걸린다.
- 컴파일러와 소스, 캐시 파일이 그대로 남아 이미지가 수백 MB 더 크다.
- root 로 실행되어 컨테이너 탈출 시 피해가 커진다.
- 비밀값이 레이어에 남아 이미지를 받은 누구나 꺼낼 수 있다.

전부 작성 순서와 몇 가지 습관으로 막을 수 있다.

## 핵심 개념

### 주요 명령어

| 명령 | 역할 | 레이어 생성 |
|---|---|---|
| `FROM` | 베이스 이미지 지정, 스테이지 시작 | - |
| `RUN` | 빌드 시 명령 실행 | 예 |
| `COPY` / `ADD` | 빌드 컨텍스트의 파일을 이미지로 복사 | 예 |
| `WORKDIR` | 작업 디렉터리 | (설정) |
| `ENV` / `ARG` | 런타임 환경 변수 / 빌드 시 인자 | (설정) |
| `USER` | 이후 명령과 실행 사용자 | (설정) |
| `EXPOSE` | 문서용 포트 표시. 실제로 포트를 열지 않는다 | (설정) |
| `ENTRYPOINT` / `CMD` | 컨테이너 시작 명령 / 기본 인자 | (설정) |

`COPY` 와 `ADD` 중에서는 `COPY` 를 기본으로 쓴다. `ADD` 는 원격 URL·로컬 tar 자동 해제 같은 부가 동작이 있어 의도가 흐려진다.

### 빌드 캐시의 규칙

빌더는 명령을 위에서부터 차례로 실행하며, 각 단계마다 "이전과 같은가"를 판단해 같으면 캐시를 재사용한다.

- `RUN` 은 명령 문자열이 같으면 캐시 적중으로 본다. 명령이 외부에서 받는 내용이 바뀌었는지는 보지 않는다.
- `COPY`/`ADD` 는 복사 대상 파일의 내용(체크섬)까지 비교한다.
- **한 단계가 캐시를 놓치면, 그 아래 모든 단계가 다시 실행된다.**

마지막 규칙 때문에 순서가 모든 것이다.

### 나쁜 예와 좋은 예

```dockerfile
# 나쁜 예
FROM python:3.12
COPY . /app                     # 코드 한 줄만 바뀌어도 여기서 캐시 무효
WORKDIR /app
RUN pip install -r requirements.txt   # 매번 재설치
CMD python main.py
```

```dockerfile
# 좋은 예
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt   # requirements 가 같으면 캐시
COPY . .
RUN useradd --create-home --uid 10001 app
USER app
CMD ["python", "main.py"]
```

차이는 세 가지다.

1. 의존성 목록만 먼저 복사해 설치하고, 소스는 나중에 복사한다. 코드를 고쳐도 의존성 설치 단계는 캐시를 탄다.
2. `-slim` 베이스와 `--no-cache-dir` 로 불필요한 파일을 줄였다.
3. `CMD` 를 JSON 배열(exec form)로 썼다. 문자열(shell form)로 쓰면 `/bin/sh -c` 가 PID 1 이 되어, `docker stop` 이 보내는 SIGTERM 이 애플리케이션에 전달되지 않을 수 있다. 그러면 유예 시간이 끝날 때까지 기다렸다가 SIGKILL 로 죽는다.

### .dockerignore

`COPY . .` 는 빌드 컨텍스트 전체를 대상으로 한다. `.git`, `node_modules`, 로컬 가상환경, `.env` 같은 파일이 들어가면 이미지가 커지고 캐시가 쓸데없이 깨지며 비밀이 새어 나간다. `.dockerignore` 로 제외한다.

```
.git
__pycache__
.venv
.env
*.log
```

### 멀티스테이지 빌드

컴파일 언어는 빌드에 필요한 도구(컴파일러, 헤더, 빌드 캐시)와 실행에 필요한 것(바이너리 하나)이 크게 다르다. 멀티스테이지는 한 Dockerfile 안에 여러 `FROM` 을 두고, 앞 스테이지의 결과물만 뒤로 복사한다.

```dockerfile
FROM golang:1.23 AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -o /out/server ./cmd/server

FROM gcr.io/distroless/static-debian12
COPY --from=build /out/server /server
USER nonroot
ENTRYPOINT ["/server"]
```

최종 이미지에는 Go 컴파일러도 소스도 없다. 셸조차 없으므로 공격 표면이 작다. 대신 컨테이너 안에 들어가 디버깅하기는 어려워진다. 이 트레이드오프를 알고 고른다.

### 레이어를 줄이는 RUN

```dockerfile
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*
```

`apt-get update` 와 `install` 을 한 `RUN` 에 묶는 이유는 두 가지다. 따로 두면 `update` 단계가 캐시되어 오래된 패키지 목록으로 설치하게 될 수 있다. 그리고 목록 파일 삭제를 같은 `RUN` 안에서 해야 레이어에서 실제로 빠진다. 다른 `RUN` 에서 지우면 앞 레이어에 바이트가 남는다.

### 비밀값

`ENV TOKEN=...` 이나 `COPY .env` 로 넣은 비밀은 이미지 레이어·설정에 남는다. `ARG` 도 이미지 이력에 드러날 수 있다. BuildKit 의 비밀 마운트(`RUN --mount=type=secret,...`)를 쓰면 해당 `RUN` 동안만 파일로 보이고 레이어에는 남지 않는다. 런타임 비밀은 이미지가 아니라 실행 환경(쿠버네티스 Secret 등)에서 주입한다.

## 직접 해 보기

빌드 캐시 규칙을 시뮬레이션해서 순서의 효과를 숫자로 보자. 각 단계의 캐시 키는 "이전 단계 키 + 명령 + (COPY 라면 파일 내용)"의 해시로 만든다.

```python
import hashlib

def build(steps, files, cache):
    parent, rebuilt = "", 0
    for kind, arg, cost in steps:
        content = ""
        if kind == "COPY":
            names = sorted(files) if arg == "." else [arg]
            content = "".join(n + files[n] for n in names)
        key = hashlib.sha256((parent + kind + arg + content).encode()).hexdigest()
        if key in cache:
            status = "CACHED"
        else:
            status, rebuilt = "RUN   ", rebuilt + cost
            cache.add(key)
        parent = key
        print(f"  {status} {kind} {arg}")
    print(f"  -> rebuild cost: {rebuilt}s")

bad = [("COPY", ".", 1), ("RUN", "pip install -r requirements.txt", 60)]
good = [("COPY", "requirements.txt", 1), ("RUN", "pip install -r requirements.txt", 60),
        ("COPY", ".", 1)]

v1 = {"requirements.txt": "flask==3.0", "main.py": "v1"}
v2 = {"requirements.txt": "flask==3.0", "main.py": "v2"}  # 코드만 수정

for name, steps in [("bad", bad), ("good", good)]:
    cache = set()
    print(f"[{name}] first build")
    build(steps, v1, cache)
    print(f"[{name}] after editing main.py")
    build(steps, v2, cache)
```

결과는 다음과 같다.

```
[bad] first build
  RUN    COPY .
  RUN    RUN pip install -r requirements.txt
  -> rebuild cost: 61s
[bad] after editing main.py
  RUN    COPY .
  RUN    RUN pip install -r requirements.txt
  -> rebuild cost: 61s
[good] first build
  RUN    COPY requirements.txt
  RUN    RUN pip install -r requirements.txt
  RUN    COPY .
  -> rebuild cost: 62s
[good] after editing main.py
  CACHED COPY requirements.txt
  CACHED RUN pip install -r requirements.txt
  RUN    COPY .
  -> rebuild cost: 1s
```

같은 수정에 61초와 1초. 실제 빌드에서도 차이는 이 구조에서 나온다.

## 현업에서는

- **CI 빌드 시간.** CI 러너는 매번 깨끗한 환경에서 시작하는 경우가 많아 로컬 캐시가 없다. 레지스트리에 캐시를 내보내고 가져오는 설정(BuildKit 의 cache export/import)을 함께 쓴다.
- **이미지 스캔.** 베이스 이미지가 클수록 취약점 스캐너가 보고하는 패키지도 많다. slim·distroless 베이스로 바꾸는 것만으로 보고 건수가 크게 줄어드는 경우가 흔하다.
- **non-root 와 쿠버네티스.** 파드의 `securityContext.runAsNonRoot: true` 를 켜면 root 로 실행하려는 이미지는 시작이 거부된다. Dockerfile 에서 숫자 UID 로 `USER` 를 지정해 두면 이 검사를 통과한다.
- **헬스체크는 오케스트레이터에.** Dockerfile 의 `HEALTHCHECK` 는 쿠버네티스가 쓰지 않는다. 쿠버네티스에서는 liveness·readiness 프로브로 정의한다.

## 확인 문제

1. 빌드 캐시에서 한 단계가 캐시를 놓치면 그 뒤 단계는 어떻게 되는가?
2. `COPY requirements.txt` 와 `RUN pip install` 을 `COPY . .` 보다 먼저 두는 이유는?
3. `CMD python app.py` 와 `CMD ["python", "app.py"]` 의 차이가 종료 동작에 미치는 영향은?
4. 멀티스테이지 빌드의 장점과 단점을 하나씩 들라.
5. `apt-get update` 와 `apt-get install` 을 별도 `RUN` 으로 나누면 생길 수 있는 문제는?

### 풀이

1. 그 뒤의 모든 단계가 다시 실행된다.
2. 소스 코드가 바뀌어도 의존성 목록이 같으면 설치 단계가 캐시를 타기 때문이다.
3. shell form 은 `/bin/sh -c` 가 PID 1 이 되어 SIGTERM 이 앱에 전달되지 않을 수 있다. 정상 종료가 안 되고 유예 후 강제 종료된다. exec form 은 앱이 PID 1 이 되어 신호를 직접 받는다.
4. 장점: 빌드 도구가 최종 이미지에서 빠져 작고 안전하다. 단점: 셸·도구가 없어 컨테이너 안 디버깅이 어렵다.
5. `update` 단계가 캐시되어 오래된 패키지 목록으로 `install` 하게 된다. 또 목록 파일을 지워도 앞 레이어에 남는다.

## 더 읽을거리 (References)

- Docker Docs, [Dockerfile reference](https://docs.docker.com/reference/dockerfile/)
- Docker Docs, [Building best practices](https://docs.docker.com/build/building/best-practices/)
- Docker Docs, [Multi-stage builds](https://docs.docker.com/build/building/multi-stage/)
- Docker Docs, [Docker build cache](https://docs.docker.com/build/cache/)
