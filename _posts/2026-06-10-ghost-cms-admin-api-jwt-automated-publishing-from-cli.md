---
layout: post
title: "Ghost CMS 에 *CLI 한 줄로 글 올리기* — Admin API + JWT (HS256, hex secret, kid 헤더) + Markdown → HTML 자동화 파이프라인 *50 줄로* 만들기"
date: 2026-06-10 02:00:00 +0900
categories: [automation, cms, api]
tags: [ghost, ghost-cms, admin-api, jwt, hs256, pyjwt, markdown, python, automation, headless-cms, blog, cli, pep-668, venv]
---

GitHub Pages 에 Markdown 으로 글을 *써* 두고, *같은 글* 을 Ghost CMS 에 *손으로 옮겨 붙이는* 의식은 *한 번 까진 참아 줄 만하지만 두 번 부터 죄악*. *CLI 한 줄* 로 *Markdown → Ghost 의 *발행 된 글* 까지 가는 *50 줄 짜리 파이프라인*을 만들어 보면, 본질은 *Ghost Admin API + JWT (HS256) + Markdown 변환* 의 *세 조각 의 *깔끔한 조립**. 다만 그 사이에 *Admin API Key 의 hex 디코딩*, *JWT 의 *kid* 헤더*, *POST 시 `?source=html` 쿼리스트링*, *PUT 시 `updated_at` 충돌 검사* 같은 *문서에 작게 적힌 함정* 들이 있다. 한 번 빠지면 1 시간, 알고 나면 30 분.

이 글은 *그 *최소 코드 + 함정 5 가지* 를 정리한다. Ghost 5.x 기준. Python 3.10+. **(1) Ghost Admin API 의 인증 구조**, **(2) HS256 JWT 직접 생성**, **(3) Markdown → HTML 변환**, **(4) POST 로 글 생성**, **(5) PUT 으로 *draft → published* 전환**, **(6) 함정 5 가지 + 우회**.

---

## TL;DR

**Ghost CMS Admin API** = *JWT (HS256, hex 시크릿, *kid* 헤더 필수)* 로 인증하는 *REST*.

```python
import jwt, time, requests, markdown

ADMIN_KEY = "<key-id>:<secret-hex>"      # Ghost 의 Custom Integration 에서 발급
key_id, secret = ADMIN_KEY.split(':')

iat = int(time.time())
token = jwt.encode(
    {'iat': iat, 'exp': iat + 5 * 60, 'aud': '/admin/'},
    bytes.fromhex(secret),               # ← 함정 1: hex 디코딩 필수
    algorithm='HS256',
    headers={'kid': key_id},             # ← 함정 2: kid 헤더 없으면 거부
)

html = markdown.markdown(open('post.md').read(),
                         extensions=['extra', 'tables', 'fenced_code'])

r = requests.post(
    'https://example.com/ghost/api/admin/posts/?source=html',  # ← 함정 3
    json={'posts': [{'title': '제목', 'html': html, 'status': 'draft'}]},
    headers={'Authorization': f'Ghost {token}'},               # ← 함정 4: 'Bearer' 아님
)
print(r.status_code, r.json()['posts'][0]['url'])
```

*이 한 블록* 이 *글 1 개 업로드 의 *전부*. 50 줄 으로 *frontmatter 파서 + 태그 + 발행 상태 토글* 까지 붙이면 *완성된 CLI 도구*.

---

## 1. Ghost Admin API 의 *인증 구조*

Ghost 5.x 는 *3 가지 API* 를 노출한다:

| API | 인증 | 권한 | 용도 |
|---|---|---|---|
| **Content API** | API key (key 만) | *읽기만* | 공개 사이트 |
| **Admin API** | *JWT* (`HS256` + `kid`) | *읽기 + 쓰기 + 발행* | 자동화 |
| **Members API** | session cookie | 멤버 전용 | 결제 / 댓글 |

자동 글쓰기 = **Admin API**. *그 단 하나의 사실* 만 알면 출발 OK.

### 1-1. Admin API Key 발급

Ghost Admin → **Settings → Integrations → Add custom integration** → 이름 입력. 발급되는 *Admin API Key* 형식:

```
69f882acb274c4000113e422:4b733f5cf2752f1bb3e6060c9609d3cbda0ee57b377429c67fc312bda0d52d89
                       ↑
                      콜론 (id:secret 구분)
```

- 콜론 *앞* = `kid` (Key ID, 24 자 hex)
- 콜론 *뒤* = HMAC `secret` (*64 자 hex* — bytes 32개의 16진수 표현)

> *주의*: *Admin API Key 는 *전체 권한*. 노출 시 *글 작성·삭제·테마 변경* 까지 가능. *git 에 넣지 말 것*. `.env` + `.gitignore` 가 정공.

---

## 2. JWT 직접 생성 — 함정의 7할이 여기

Ghost 의 JWT 는 *비표준 적 요구사항* 두 가지를 가진다:

### 2-1. *kid* 헤더 — 어떤 키로 sign 했는지

JWT 의 표준 헤더에는 `alg`, `typ` 만 있고 *kid (Key ID)* 는 옵션. Ghost 는 *반드시 헤더에 kid* 가 있어야 함. *없으면 *401 Authorization Failed* 묻지도 따지지도 않고 거부*.

```python
token = jwt.encode(
    payload,
    secret_bytes,
    algorithm='HS256',
    headers={'kid': key_id},   # ← 이 줄 빼면 100% 401
)
```

### 2-2. *secret 은 hex 인코딩* — 그대로 sign 하면 안 됨

Admin Key 의 `secret` 부분이 *64 자 hex*. 이걸 *문자열 그대로* sign 하면 Ghost 가 *서명 검증 실패*. *32 바이트 의 *raw HMAC secret* 으로 *디코딩* 후 sign 해야 함.

```python
# ❌ 틀림 — 문자열 그대로
token = jwt.encode(payload, secret, algorithm='HS256', ...)

# ✅ 맞음 — bytes.fromhex 로 디코딩
token = jwt.encode(payload, bytes.fromhex(secret), algorithm='HS256', ...)
```

이 한 줄 차이로 *모든 요청이 401*. 디버깅 시 *서명 자체가 다르게 계산* 되므로 *Ghost log 에 *"invalid signature"** 가 찍힌다.

### 2-3. payload — *iat / exp / aud* 셋만

```python
{
    'iat': int(time.time()),
    'exp': int(time.time()) + 5 * 60,   # 최대 5분, 그 이상이면 거부
    'aud': '/admin/'                     # 정확히 이 문자열 (앞뒤 / 둘 다)
}
```

- `iat` (issued at) — *지금* 의 epoch seconds
- `exp` (expires) — *최대 5 분 후* 까지만 인정
- `aud` (audience) — *정확히 `/admin/`*. *trailing slash 빼면 401*

이 세 가지가 *맞아야 *200 응답*. 하나라도 틀리면 *서명 자체는 옳아도 401*.

---

## 3. *최소 동작 코드* — 50 줄

```python
#!/usr/bin/env python3
"""Upload a Markdown file as a draft post to Ghost CMS via Admin API."""
import sys, time, re, json, argparse
import jwt, requests
import markdown as md_lib


def make_jwt(admin_key: str) -> str:
    key_id, secret = admin_key.split(':')
    iat = int(time.time())
    payload = {'iat': iat, 'exp': iat + 5 * 60, 'aud': '/admin/'}
    return jwt.encode(
        payload,
        bytes.fromhex(secret),
        algorithm='HS256',
        headers={'kid': key_id},
    )


def parse_frontmatter(text: str):
    """Jekyll-style YAML frontmatter (--- ... ---) 한 줄 파서."""
    m = re.match(r'^---\s*\n(.*?)\n---\s*\n', text, re.DOTALL)
    if not m:
        return {}, text
    fm = {}
    for line in m.group(1).split('\n'):
        if ':' in line:
            k, _, v = line.partition(':')
            fm[k.strip()] = v.strip().strip('"')
    return fm, text[m.end():]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--admin-key', required=True)
    ap.add_argument('--host', default='https://example.com')
    ap.add_argument('--md', required=True)
    ap.add_argument('--status', default='draft', choices=['draft', 'published'])
    args = ap.parse_args()

    raw = open(args.md, encoding='utf-8').read()
    fm, body = parse_frontmatter(raw)
    html = md_lib.markdown(
        body, extensions=['extra', 'tables', 'fenced_code', 'codehilite', 'sane_lists']
    )

    token = make_jwt(args.admin_key)
    r = requests.post(
        f"{args.host}/ghost/api/admin/posts/?source=html",
        json={'posts': [{
            'title': fm.get('title', 'Untitled'),
            'html': html,
            'status': args.status,
            'tags': [{'name': t.strip()} for t in fm.get('tags', '').split(',') if t.strip()],
        }]},
        headers={'Authorization': f'Ghost {token}', 'Content-Type': 'application/json'},
        timeout=60,
    )
    print(f"HTTP {r.status_code}")
    if r.ok:
        p = r.json()['posts'][0]
        print(f"OK id={p['id']} url={p['url']}")
    else:
        print(r.text[:500])
    sys.exit(0 if r.ok else 1)


if __name__ == '__main__':
    main()
```

실행:

```bash
python ghost_post.py \
  --admin-key "$GHOST_ADMIN_KEY" \
  --host "https://example.com" \
  --md ./my-post.md \
  --status draft
# HTTP 201
# OK id=... url=https://example.com/p/<uuid>/
```

*50 줄 안에서 *Markdown → 발행 된 글* 까지*. 더 줄일 수는 있지만 *frontmatter 파서 + 태그 + status 토글* 이 운영에서 빠질 수 없다.

---

## 4. Markdown → HTML — Ghost 가 받는 *세 가지 입력 형식*

Ghost 의 POST 본문 의 본문은 *셋 중 하나*:

| 필드 | 형식 | 권장 시점 |
|---|---|---|
| `mobiledoc` | Ghost 의 내부 JSON 표현 | Ghost ↔ Ghost 마이그레이션 |
| `lexical` | Ghost 5.x 의 새 에디터 JSON | 손으로 만들기 어려움 |
| `html` + `?source=html` | 평범한 HTML | **외부 자동화 의 정공** |

`?source=html` 쿼리스트링을 *반드시* 붙여야 *html 필드 가 *해석 된다*. 빼면 Ghost 가 *html 필드를 *무시* 하고 *빈 글* 을 만든다. 빈 글이 보이면 *이 쿼리스트링부터 의심*.

### 4-1. Markdown → HTML — Python `markdown` 라이브러리

```python
import markdown
html = markdown.markdown(
    md_text,
    extensions=['extra', 'tables', 'fenced_code', 'codehilite', 'sane_lists'],
)
```

- `extra` — 기본 set (footnote, abbr, attr_list, def_list 등)
- `tables` — 파이프 표
- `fenced_code` — 백틱 3개 코드 블록
- `codehilite` — *Pygments 와 함께* 쓰면 *syntax highlight*. 단 Ghost 의 *기본 CSS* 가 *pygments class* 를 모르면 *색 안 입혀짐*. 별도 CSS 주입 필요
- `sane_lists` — 리스트 indent 규칙 정규화

대안 — *Markdown 의 *고급 기능* 이 더 필요* 하면 `mistune` 이나 *Pandoc CLI* 호출.

---

## 5. *draft → published* 전환 — *update 의 충돌 검사*

POST 로 글을 *draft* 로 올린 뒤 *published* 로 바꾸려면 PUT. 그런데 *Ghost 는 *concurrent edit* 을 막기 위해 *클라이언트가 *가진 *updated_at* 을 함께 보내라* 요구*. *DB 의 현재 *updated_at* 과 *다르면 409 Conflict*.

```python
# 1) 현재 post 가져와 updated_at 확보
r = requests.get(f"{host}/ghost/api/admin/posts/{post_id}/",
                 headers={'Authorization': f'Ghost {token}'})
current = r.json()['posts'][0]

# 2) PUT 으로 status 만 변경 + updated_at 동봉
requests.put(
    f"{host}/ghost/api/admin/posts/{post_id}/",
    json={'posts': [{
        'status': 'published',
        'updated_at': current['updated_at'],   # ← 이 줄 빼면 409
    }]},
    headers={'Authorization': f'Ghost {token}', 'Content-Type': 'application/json'},
)
```

*409 가 떨어지면* — *누가 *방금* 그 글을 수정* 했거나, *내가 *오래 전 의 updated_at* 을 보냈다는 신호. *GET 다시 → PUT 재시도*.

---

## 6. *함정 5 가지* — 빠지면 1 시간씩 잡아먹는

### 6-1. *PEP 668 — 시스템 Python 에 pip install 실패*

macOS 의 brew Python (3.12+) 또는 최신 Ubuntu 에서:

```
$ python3 -m pip install pyjwt requests markdown
error: externally-managed-environment
× This environment is externally managed
```

*시스템 Python 보호* 정책. *venv* 가 정공:

```bash
python3 -m venv /tmp/ghost-venv
/tmp/ghost-venv/bin/pip install pyjwt requests markdown
/tmp/ghost-venv/bin/python script.py ...
```

또는 *pipx* (CLI 도구 격리) 도 정공. *`--break-system-packages` 는 쓰지 말 것* — 시스템 Python 깨질 위험.

### 6-2. *401 이 떨어질 때 — 4 곳을 순서대로 확인*

| 순서 | 확인 | 일반적 오류 |
|---|---|---|
| 1 | *kid* 헤더 — JWT 헤더에 들어있나? | `headers={'kid': key_id}` 누락 |
| 2 | *secret 의 hex 디코딩* | `bytes.fromhex(secret)` 안 함 |
| 3 | *aud* 값 — `/admin/` 정확히? | trailing slash 누락 |
| 4 | *exp* — 현재로부터 *5 분 이내*? | 시계 동기화 / 너무 긴 만료 |

이 네 가지가 *401 의 *4 대 출처*. 디버깅 시 *순서대로* 점검.

### 6-3. *?source=html* 누락 — *빈 글* 이 올라간다

```python
# ❌ 본문이 비어 보임
url = f"{host}/ghost/api/admin/posts/"

# ✅ 정상
url = f"{host}/ghost/api/admin/posts/?source=html"
```

쿼리스트링을 *URL 에 명시*. requests 의 `params=` 로 넘겨도 됨.

### 6-4. *한국어 slug — 자모 직역 으로 *추하게 변환***

한국어 제목을 그대로 POST 하면 Ghost 가 *slug 를 *자음·모음 직역* 으로 만든다*:

```
제목: "수학의 기초 8 분야"
slug: suhagyi-gico-8-bunyaga  ← 거칠다
```

해결책: POST 시 *명시적 `slug` 필드*:

```python
'posts': [{
    'title': '수학의 기초 8 분야',
    'slug': 'math-foundations-8-domains',  # 명시
    'html': html,
    ...
}]
```

영문 slug 가 *SEO 와 공유 링크 가독성* 측면에서도 정공.

### 6-5. *코드 블록 의 *syntax highlight 가 안 입혀짐*

`codehilite` extension 으로 HTML 안에 `class="codehilite"` 가 들어가지만 — Ghost *기본 테마* 가 그 CSS 를 가지지 않을 수 있음. 두 가지 우회:

- *Ghost 테마 에 *highlight.js* 추가* (수동 / fork)
- *POST 본문 안에 *`<style>...</style>` 인라인** — 글 1 개 당 1 번. 우아하진 않지만 동작.

---

## 7. *함정에 빠지지 않는 *디버깅 명령** 모음

### 7-1. JWT 직접 검증

```bash
# JWT 를 발급해서 jwt.io 같은 곳 (또는 로컬 디코더) 에 붙여 보기
python -c "
import jwt, time
key_id, secret = 'KEY_ID:SECRET'.split(':')
print(jwt.encode(
    {'iat': int(time.time()), 'exp': int(time.time())+300, 'aud': '/admin/'},
    bytes.fromhex(secret),
    algorithm='HS256',
    headers={'kid': key_id},
))
"
```

### 7-2. 직접 curl 로 GET 한 번

```bash
TOKEN=$(python -c "...")  # 위의 JWT 발급
curl -i -H "Authorization: Ghost $TOKEN" \
     https://example.com/ghost/api/admin/site/
```

`200 OK + JSON` 이 떨어지면 *JWT 완벽*. `401` 이면 *위의 4 대 출처* 점검.

### 7-3. Ghost 의 실제 에러 메시지

Ghost 는 `401` 응답 본문에 *친절한 message* 를 담아 준다:

```json
{
  "errors": [{
    "message": "Authorization failed",
    "context": "Token is missing or malformed",
    "type": "UnauthorizedError",
    "details": null,
    "property": null,
    "help": "Please sign in to access the editor.",
    "code": null,
    "id": "..."
  }]
}
```

`context` 가 *진짜 원인*. *"Token is missing"* → kid 헤더 없음. *"Invalid signature"* → hex 디코딩 안 함. *"Token expired"* → exp 가 과거.

---

## 8. *양방향 미러* — GitHub Pages ↔ Ghost CMS

Jekyll 의 `_posts/*.md` 를 *그대로* Ghost 에 *batch upload* 가능. 한 번 더 작은 스크립트:

```python
from pathlib import Path

for p in Path('_posts').glob('*.md'):
    upload(p, status='draft')   # 위 5 단계 의 코드 재사용
    print(f"uploaded: {p.name}")
```

이러면 *GitHub Pages 는 *원본 (코드/markdown 의 git 이력)*, Ghost 는 *발행 채널 (멤버십·뉴스레터·SEO)** 의 *듀얼 publishing*. *지금 이 글 자체* 도 *같은 자동화 로 두 곳 에 동시 등장* 한다.

업그레이드 시 검토할 것:

- *중복 등록 방지* — Ghost 의 *slug 기반 멱등 upsert* (POST 401/409 fallback → PUT)
- *Frontmatter 일관성* — Jekyll 의 `layout`, `categories` 같은 Ghost 무관 필드 *무시*
- *이미지 업로드* — Markdown 의 로컬 `![alt](./img.png)` → Ghost 의 *Images API* `/ghost/api/admin/images/upload/` 로 *미리 업로드 → URL 치환*

---

## 9. *마무리*

*Ghost Admin API* 는 *문서가 깔끔하지만 *함정의 90%는 *작은 글씨 에 있다*. *kid 헤더 필수*, *secret 의 hex 디코딩*, *aud 의 정확한 `/admin/`*, *POST 의 `?source=html`*, *PUT 의 updated_at* — 이 다섯이 *오늘 정리* 의 핵심. 한 번 알면 *50 줄 짜리 자동화 도구* 가 *수십 편 의 글 을 *5 분 안에* 올린다*.

*수동 작업 의 *반복* 은 *코드 의 *부재* 의 신호*. *Markdown 한 줄 → Ghost 의 발행 된 글* 까지 *마우스 0 번* 으로 가야 *자동화 의 본질*. 그리고 *그 마우스 0 번* 의 출발점이 — *위의 50 줄*.
