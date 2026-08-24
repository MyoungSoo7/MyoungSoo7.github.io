#!/usr/bin/env python3
"""_data/popular.json 을 다시 만든다 — 글별 조회수 순위.

왜 빌드 때가 아니라 미리 만들어 두는가:
GoatCounter 의 공개 카운터는 *경로 하나당 요청 하나* 다(`/counter/<path>.json`).
글이 600편이 넘으니 브라우저에서 순위를 매기려면 페이지를 열 때마다 600요청이 나간다.
그래서 하루 한 번 여기서 전부 세어 파일로 떨어뜨리고, 사이트는 그 파일만 읽는다.

전량 집계에 토큰은 필요 없다. `/api/v0/stats/hits` 는 401 이지만, 공개 카운터를
경로마다 부르는 것만으로 같은 숫자가 나온다(2026-08-24 실측: 636편 42초).

함정: 조회가 0 인 경로는 **404 로 온다.** 다만 본문은 `{"count_unique":"0"}` 라
정상 응답이다. 404 를 에러로 처리하면 조회 없는 글 361편이 전부 실패로 잡힌다.
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

SITE = "https://myoungsoo7.github.io"
GC = "https://lemuel.goatcounter.com/counter/"
OUT = Path(__file__).resolve().parent.parent / "_data" / "popular.json"

# 순위에 남길 최대 편수와, 목록에 낄 최소 조회수.
# 1회짜리가 191편이라 그대로 두면 순위가 아니라 목록이 된다.
KEEP = 50
MIN_VIEWS = 2


def counter(path: str) -> int:
    """경로 하나의 순방문자 수. 실패하면 -1(0 과 구분해야 한다)."""
    url = GC + urllib.parse.quote(path, safe="") + ".json"
    try:
        body = urllib.request.urlopen(url, timeout=20).read()
    except urllib.error.HTTPError as e:
        if e.code != 404:
            return -1
        body = e.read()          # 404 지만 본문에 0 이 들어 있다
    except Exception:
        return -1
    try:
        d = json.loads(body)
    except Exception:
        return -1
    raw = d.get("count_unique") or d.get("count") or 0
    try:
        return int(str(raw).replace(",", ""))
    except ValueError:
        return -1


def main() -> int:
    posts = json.load(urllib.request.urlopen(SITE + "/search.json", timeout=30))

    with ThreadPoolExecutor(max_workers=12) as ex:
        views = list(ex.map(lambda p: counter(p["url"]), posts))

    failed = sum(1 for v in views if v < 0)
    if failed > len(posts) * 0.2:
        # 절반이 실패한 순위를 커밋하면 멀쩡하던 인기글이 사라진다. 차라리 안 쓴다.
        print(f"[error] {failed}/{len(posts)} 건 조회 실패 — 파일을 쓰지 않는다", file=sys.stderr)
        return 1

    ranked = sorted(
        (
            {"url": p["url"], "title": p["title"], "date": p["date"], "views": v}
            for p, v in zip(posts, views)
            if v >= MIN_VIEWS
        ),
        key=lambda r: (-r["views"], r["date"]),
    )[:KEEP]

    # 순위가 그대로면 파일을 건드리지 않는다. 타임스탬프만 바꿔 쓰면 아무것도 안 바뀐 날에도
    # 커밋이 하나씩 쌓이고 Pages 가 매일 헛빌드를 한다. `generated` 는 그래서 "마지막으로
    # 순위가 바뀐 시각" 이지 "마지막으로 확인한 시각" 이 아니다.
    if OUT.exists():
        try:
            if json.loads(OUT.read_text(encoding="utf-8")).get("posts") == ranked:
                print(f"[ok] {len(posts)}편 조회 — 순위 변동 없음, 파일 그대로 둔다")
                return 0
        except Exception:
            pass  # 파일이 깨져 있으면 그냥 새로 쓴다

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(
        json.dumps(
            {
                "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "scanned": len(posts),
                "failed": failed,
                "posts": ranked,
            },
            ensure_ascii=False,
            indent=1,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"[ok] {len(posts)}편 조회, {len(ranked)}편 기록 (실패 {failed}) → {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
