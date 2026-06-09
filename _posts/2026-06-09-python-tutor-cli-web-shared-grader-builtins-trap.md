---
layout: post
title: "*한국어 대화형 *파이썬 학습 프로그램* 을 *CLI + Web 동시* 로 만들고 *9 챕터 27 문제* 로 확장한 기록 — *exec 채점기의 *3 가지 함정* 과 *코드 한 벌로 양쪽* 굴리는 *모노레포 패턴*"
date: 2026-06-09 18:00:00 +0900
categories: [project, python, education, fullstack]
tags: [python, education, fastapi, cli, exec, sandbox, grader, monorepo, judge-engine, oop, decorator, web-audio]
---

이 글은 *한국어 *대화형 파이썬 학습 프로그램* (https://github.com/MyoungSoo7/python-tutor) 을 *어제 저녁에 시작* 해서 *오늘 오후 9 챕터 27 문제 + CLI / Web 두 버전* 으로 *확장* 한 기록이다.

이력서용 토이 프로젝트가 아니라 — *내가 *실제로 *Python 채점 시스템을 *직접 만들면서 *부딪힌 *exec 의 미묘한 함정 3 가지* 를 *학습 자산으로 *영구 압축* 한다.

읽고 가셔도 좋은 분:
1. *직접 만들면서 *Python 의 *namespace / exec / __builtins__* 의 *진짜 동작* 을 *이해하고 싶은 사람*
2. *CLI + Web 한 코드베이스로 *두 UX 동시 굴리는 *패턴* 의 *얇은 시도* 가 궁금한 사람
3. *judge-engine 같은 *교육용 채점 시스템* 을 *직접 만들 계획* 인 사람

---

## TL;DR

> *CLI* (`python3 tutor.py`) 와 *Web* (FastAPI + vanilla SPA) 가 *grader.py + chapters.py 의 *동일 파일* 을 공유*. *9 챕터 27 문제 / 70+ 테스트 케이스*. *exec 기반 채점기* 의 *3 가지 함정* (`__builtins__` 의 *컨텍스트 의존*, *함수 정의 시점의 globals*, *import 한 모듈의 *함수 외부 손실*) 을 *진짜 코드로 풀어둠*.

**한 그림으로**:

```
              ┌── chapters.py ──┐   ┌── grader.py ──┐
              │ 9 챕터 27 문제   │   │ exec 채점 엔진 │
              └──────┬──────────┘   └────┬───────────┘
                     │ 공유             │
        ┌────────────┴────────┐   ┌─────┴────────────────┐
        │  CLI (tutor.py)      │   │  Web (FastAPI)        │
        │  + ui.py (color/box) │   │  + frontend/index.html│
        │  + progress.py       │   │  + 쿠키 세션          │
        └──────────────────────┘   └───────────────────────┘
```

---

## 0. *왜 *직접 만들었나*

> *기존 *codeup / boj / programmers / Codecademy / Coursera* 가 *훨씬 풍부함* 을 *알면서도 *직접 만든 이유* — *내가 *exec 가 *어떻게 *namespace 를 다루는지* 를 *진짜로* 이해하려면 *직접 채점기를 *써봐야 *한다*.

*lemuel-quant-core 의 judge-engine* 이 *C++ + seccomp + cgroup* 으로 *완전 격리 채점* 을 하는데, *그 위에 *Python 같은 *동적 언어* 의 *교육용 lite 버전* 을 *직접 짜보면서 *판단 기준* 을 *구체화* 하고 싶었다.

결과: *3 가지 함정* 을 *직접 부딪힌 *후* *어떻게 해야 *진짜 안전* 하고 *기대대로 동작* 하는지 *체화*. *이것 만으로도 *이력서 한 줄 가치* 있다.

---

## 1. *9 챕터의 *학습 흐름* — *왜 이 순서*

```
01. 변수와 자료형          ─ 합계 / 정수 나누기 / f-string
02. 조건문                ─ 최댓값 / FizzBuzz / 성적 등급
03. 반복문                ─ 1~n 합 / 짝수 / 자릿수 합
04. 함수                  ─ 절댓값 / 팩토리얼 / 소수 판별
05. 자료구조 (list/dict)  ─ 최댓값 / 단어 빈도 / 평탄화
06. 클래스와 객체          ─ Point 거리 / Counter / Rectangle
07. 예외 처리              ─ safe_divide / int 변환 / 안전 접근
08. 데코레이터              ─ double_result / count_calls / memoize
09. 파일 IO (개념)         ─ 줄 분리 / CSV 파싱 / JSON 파싱
```

*입문 (변수 ~ 자료구조)* → *중급 (OOP / 예외)* → *상급 (데코레이터)* → *실무 (파일 IO)* 의 *난이도 곡선*.

**각 챕터의 *최소 문제 수 3 개* 인 이유**:
- 1 개 — *한 번 풀고 *그 챕터는 *모르겠다 도 잊혀짐*
- 5+ — *지루함 + 다음 챕터 욕구 *깎임*
- 3 — *기본 / 변형 / 함정* 의 *3 종 패턴* 으로 *기억 강화*

예: *01 자료형* 의 3 문제:
- `result = a + b` (기본 + 연산)
- `q, r = n // 10, n % 10` (변형 — 한 문제로 *여러 변수 검증*)
- `f"{first} {last}"` (f-string — *함정 — 첫 시도 시 보통 + 로 푼다*)

---

## 2. *exec 채점기의 *3 가지 함정***

> 단순한 코드 채점기지만, *Python 의 namespace / scoping rule* 의 *섬세한 부분* 을 *제대로 짚지 않으면 *조용히 깨진다*. 직접 부딪힌 *3 가지 함정* 을 *진단 + 수정* 으로 기록.

### Trap 1 — `__builtins__` 가 *모듈* 일 때 vs *dict* 일 때

내 첫 시도:

```python
def _make_safe_globals(extra_globals, allow_import=False):
    safe_builtins = {}
    for name in dir(__builtins__):
        if name in denied: continue
        safe_builtins[name] = getattr(__builtins__, name)
    return {"__builtins__": safe_builtins, **extra_globals}
```

*동작* 처럼 보였다. 그런데 *함수 모드 채점* 에서:

```
fact(0) = 1  ← 통과
fact(1) FAIL: NameError: name 'range' is not defined  ← ???
fact(5) FAIL: NameError: name 'range' is not defined
```

*range 가 없다* 는데, *dir(__builtins__) 에 *range 가 있을 텐데*. 디버깅:

```python
sb = grader._make_safe_globals({})
print(list(sb["__builtins__"].keys())[:10])
# ['__class__', '__contains__', '__delattr__', '__delitem__', '__dir__', '__doc__', ...]
```

*어? *dunder attribute 만* 있다*. *range / len / print 가 *모두 없음*.

**원인**: `__builtins__` 는 *컨텍스트 에 따라 다른 객체* 다:
- *메인 모듈 (`__main__`)* 에서는 *`builtins` 모듈* (range, len, ... 다 있음)
- *import 된 모듈* (grader.py 같은 데) 에서는 *dict* — 그 dict 는 *해당 모듈의 `__builtins__`* 이라는 *내부 메타* 만 담음

*같은 코드 `dir(__builtins__)` 가 *위치에 따라 *완전 다른 결과*.

**고친 버전** — `builtins` 모듈을 *명시 import*:

```python
import builtins

def _make_safe_globals(extra_globals, allow_import=False):
    safe_builtins = {}
    for name in dir(builtins):
        if name in denied: continue
        safe_builtins[name] = getattr(builtins, name)
    return {"__builtins__": safe_builtins, **extra_globals}
```

→ `range / len / print / sum / ...` *전부 정상* 노출. *함수 안의 range 호출도 작동*.

**교훈**: *`__builtins__` 라는 *마법 같은 변수* 를 *직접 안 만지고 *명시 `import builtins`* 가 *코드 위치 무관 정상* 동작.

### Trap 2 — *함수 정의 시점의 *globals 가 *호출 시 lookup 의 *기준***

함수 모드 채점은 *exec 로 함수를 정의* 한 뒤 *외부에서 *반복 호출*. 그런데 다음 코드가 *깨졌다*:

```python
import json
def parse_users(s):
    return {u['name']: u['age'] for u in json.loads(s)}
```

채점 결과:
```
parse_users('[{"name":"a","age":1}]')  FAIL: NameError: name 'json' is not defined
```

이상하다 — *exec 안에서 import json 했고, 함수가 *그 직후에 정의됐는데*.

**원인**: 다음 exec 패턴:

```python
exec(code, g, l)
```

- *globals 는 `g`*, *locals 는 `l`* 로 *분리*.
- *import json* 의 *json 모듈 객체* 는 *`l` (locals) 에 들어간다*.
- *def parse_users(...)* 도 *`l` 에 들어간다*.
- 함수의 *`__globals__`* 는 *`g`* (exec 의 globals).
- 함수 외부 호출 시 *json* lookup → *함수의 `__globals__` = `g`* 에서 찾음 → *없음* → NameError.

> *exec 의 *2 인자 형식 `exec(code, g)`* 는 *globals 와 locals 가 *동일* 한 dict*. *3 인자 `exec(code, g, l)` 은 *분리* → 함수 정의가 *l 에 들어가 *외부에서 *손실*.

**고친 버전** — 함수 모드 채점은 *2 인자 exec*:

```python
def grade_function(code, func_name, tests, allow_import=False):
    g = _make_safe_globals({}, allow_import=allow_import)
    exec(code, g)              # ← 2 인자 — globals = locals
    fn = g.get(func_name)
    # ... 외부에서 fn(*args) 호출 정상
```

→ `import json` 이 *g 에 들어가 *함수의 *globals 에서 찾을 수 있게* 됨.

**교훈**: *함수 정의를 *exec 외부에서 호출* 할 때 — *반드시 *2 인자 exec*. *locals/globals 분리는 *함수가 자기 globals 를 *기억* 한다는 *Python 의 *first-class function* 특성에 *어긋남*.

### Trap 3 — *함수 모드 vs 변수 모드의 *동일성 가정 함정**

처음에 *변수 모드 (value)* 와 *함수 모드 (function)* 를 *비슷한 방식으로 채점* 했는데, *값 모드는 *locals 가 *분리되어야 *시드 값 (setup) 가 *코드에 *주입* 가능*. 즉:

```python
# value 모드 — setup 값을 locals 에 주입
exec(code, g, l_with_setup)   # ← 3 인자 — l_with_setup = {"a": 3, "b": 4, ...}
result = l_with_setup["result"]
```

**결론**:
- *value 모드* — `exec(code, g, l_seeded)` *3 인자, locals 에 setup*
- *function 모드* — `exec(code, g)` *2 인자, 단일 dict*

**교훈**: *Python 의 `exec` 가 *작은 차이 (2 vs 3 인자)* 로 *완전히 다른 namespace 동작* 을 보인다. *교육용 채점기 만들 때 *반드시 *모드별 분리 검증*.

---

## 3. *CLI + Web 한 코드베이스로 *두 UX 굴리기**

### 3.1 *공유의 *경계*

```
[공유 부분]                  [CLI 만]                 [Web 만]
─────────────                ───────                  ────────
chapters.py  ─────┐          tutor.py                 backend/app.py
grader.py    ─────┤          ui.py                    frontend/index.html
                  │          progress.py              (frontend/CSS/JS)
                  │
                  └─→ 변경 시 *양쪽 동시 갱신*
```

`chapters.py + grader.py` 가 *공유*. *콘텐츠 / 채점 로직* 의 *진실은 *한 곳*.

CLI / Web 의 *각자 layer*:
- *CLI* — 터미널 UI (`ui.py`) + 파일 진행도 저장 (`progress.py`) + 메뉴 루프 (`tutor.py`)
- *Web* — REST API (`app.py`) + 쿠키 세션 + 단일 HTML SPA (`frontend/index.html`)

### 3.2 *왜 *FastAPI + vanilla HTML* 인가*

선택지:
- **Next.js + React** — 모던. 빌드 필요. 컨테이너 이미지 ~ 300 MB.
- **Vue + Vite** — 동급. 빌드 필요.
- **vanilla HTML + JS** — *빌드 0*. *컨테이너 이미지 ~ 80 MB*. *단일 파일 558 lines*.

*이 프로젝트는 *학습용 + 가벼움 *우선* → **vanilla HTML 가 *맞는 답***. SPA 의 *복잡한 상태 / 라우팅 / SEO* 가 *불필요*.

**핵심 UX 디테일**:
- `<textarea>` 에 *Tab 키 = 4-space 들여쓰기* 직접 구현
- `Cmd/Ctrl + Enter` = *즉시 제출*
- *사이드바 진행도 바* 가 *채점 후 자동 갱신*
- *다크 테마* + *모바일 768px 이하 sidebar 숨김*

### 3.3 *세션 / 진행도*

```python
# 메모리 dict 저장 — 재시작 시 휘발
SESSIONS: dict[str, dict[str, set[str]]] = {}

@app.get("/api/chapters")
def list_chapters(response, session_id = Cookie(...)):
    sid, prog = get_or_create_session(session_id)
    response.set_cookie("tutor_session", sid,
                        max_age=60*60*24*90, httponly=True, samesite="lax")
    ...
```

*운영 배포 시 *대체*: Redis (단순) 또는 *PostgreSQL* (영구). *인터페이스 1 개만 바꾸면 OK* — 이게 *Bounded Context 의 작은 *경험적 가치*.

---

## 4. *확장 — *6 → 9 챕터 의 *18 → 27 문제**

이번 확장에서 *3 챕터 추가*:

### 06. *클래스와 객체*
- *Point* — *유클리드 거리* (다른 객체 간 메서드 호출)
- *Counter* — *캡슐화* (private 변수 + 메서드만 인터페이스)
- *Rectangle* — *복수 메서드* + 튜플 반환

### 07. *예외 처리*
- *safe_divide* — `try / except ZeroDivisionError`
- *to_int_or_default* — `except (ValueError, TypeError)` *복수 예외*
- *safe_get* — `except IndexError` (리스트 안전 접근)

### 08. *데코레이터*
- *double_result* — 가장 단순한 *wrapper*
- *count_calls* — *함수 속성 (wrapper.calls)* 으로 *외부 노출*
- *memoize* — *dict 기반 캐시*, *재귀 호출 시 *깊이 폭발 방지*

각 문제마다 *gold answer* 를 *작성 → 채점 통과 확인* 의 *self-test 루프*. *Web 서비스 시작 시 *gold answer 자동 검증* 도 *나중에 *CI 단에서 추가 가능*.

---

## 5. *보안 — *어디까지 안전한가*

**현재 수준**:
- 차단: `open / exec / eval / __import__ / input`
- 허용: 그 외 *builtins 전부*

**남은 위험**:
- *무한 루프* — `while True: pass` 가 *서버 한 코어 100%* + *프로세스 응답 없음*. *signal.alarm 으로 *10 초 cap* 추가 필요.
- *메모리 폭발* — `x = [0] * 10**10` 이 *Python 프로세스 메모리 *수십 GB*. *resource.setrlimit* 으로 *cgroup-like 격리* 필요.
- *서브 프로세스 호출* — 일부 builtins 우회 (`__class__` chain) 로 *getattr 조합 공격* 가능.

**진짜 격리 방법**:
1. **Docker 컨테이너 격리** — *Pod 당 *CPU / 메모리 / PID 제한* + `securityContext`
2. **seccomp profile** — *lemuel-quant-core / judge-engine* 의 *룰을 *이식*
3. **gVisor / Kata Containers** — *user-space kernel* 로 *syscall 차단*
4. **별도 채점 워커** — *gRPC 분리* + *시간 / 메모리 제한* + *crash 무영향*

> *교육용 *내 PC* 에서는 *현재 수준* 으로 *충분*. *외부 공개 / 다중 사용자* 환경 에선 *반드시 *컨테이너 격리* + *시간 제한*.

---

## 6. *코드 / 배포 / 확장*

레포: **https://github.com/MyoungSoo7/python-tutor**

```
python-tutor/
├── cli/                CLI 버전 (의존성 0, 표준 라이브러리만)
│   ├── tutor.py        메인 — 메뉴 / 실습 루프
│   ├── ui.py           컬러 / 박스 / 입력 헬퍼
│   ├── grader.py       채점 엔진
│   ├── chapters.py     9 챕터 27 문제
│   ├── progress.py     진행도 저장 (~/.python_tutor_progress.json)
│   └── README.md
├── web/                웹 버전 (FastAPI + vanilla SPA)
│   ├── backend/
│   │   ├── app.py             REST API + 정적파일 서빙
│   │   ├── grader.py          ← CLI 와 *동일 코드*
│   │   ├── chapters.py        ← CLI 와 *동일 코드*
│   │   └── requirements.txt
│   ├── frontend/
│   │   └── index.html         단일 SPA (558 lines)
│   ├── Dockerfile
│   └── docker-compose.yml
├── .gitignore
└── README.md
```

### *3 가지 실행 방법*:

```bash
# 1. CLI — 가장 빠름
git clone https://github.com/MyoungSoo7/python-tutor
cd python-tutor/cli
python3 tutor.py

# 2. Web 로컬
cd python-tutor/web
python3 -m venv backend/.venv
source backend/.venv/bin/activate
pip install -r backend/requirements.txt
uvicorn --app-dir backend app:app --port 8000
# → http://localhost:8000

# 3. Docker
cd python-tutor/web
docker compose up --build
```

### *K3s 클러스터 배포* (홈랩):

내 *helm-deploy* 레포에 *charts/python-tutor* 추가하고 *Cloudflare Tunnel 로 *외부 도메인* 노출* 가능. 다음 챕터의 일.

### *확장* — 새 챕터 추가:

`backend/chapters.py` (또는 `cli/chapters.py` — *같은 파일*) 의 `CHAPTERS` 리스트에 *dict 하나 추가* — *CLI / Web 메뉴 자동 갱신*.

---

## 7. *마무리 — *직접 만들면서 *얻은 것**

### 7.1 *Python namespace 의 *섬세한 동작*** 을 *3 가지 함정* 으로 *체화*

- `__builtins__` 의 *위치 의존성*
- `exec` 의 *2 / 3 인자 namespace 분리*
- *함수의 `__globals__` 가 *정의 시점 globals* 라는 *first-class function 특성*

### 7.2 *코드 공유 모노레포 패턴*

- *공유 부분 (chapters.py / grader.py)* 과 *UX 별 부분 (CLI / Web)* 의 *경계 분명*
- *변경 시 *양쪽 동시 갱신* 의 *자연스러운 *DRY*
- *Bounded Context 와는 다른 *얇은 *공유 layer 패턴*

### 7.3 *교육용 채점 시스템* 의 *현실적 보안 한계*

- *exec + safe_builtins 만으로는 *실수 보호용*. *진짜 격리* 는 *컨테이너 / seccomp / 별도 워커*
- *lemuel-quant-core 의 judge-engine* 이 *이 영역 의 진짜 답* 임을 *직접 만들면서 *체감*

### 7.4 *작은 게 큰 것 보다 *대답력 있는* 경우*

> *이력서 한 줄에 *"Python 학습 시스템 만들었습니다"* 보다 *"exec 의 `__builtins__` 함정 3 개를 *직접 부딪히고 *3 가지 모두 *수정 + 학습 압축* 했습니다"* 가 *훨씬 강력한 *대답력*. *작게 만들었지만 *깊이 부딪힌* 경험이 *큰 시스템 단지 운영* 보다 *면접에서 더 큰 무게*.

---

*다음 글:* *judge-engine 의 *진짜 격리 룰 (seccomp + cgroup) 의 *whitelisted syscall* 을 *strace -f 의 발자취 분석* 으로 *어떻게 *최소화하는가* — *내 lemuel-quant-core 의 *진짜 채점 엔진* 의 *교과서적 *최소 허용 룰*.
