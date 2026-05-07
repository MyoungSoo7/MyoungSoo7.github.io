#!/usr/bin/env python3
"""Daily auto-updater for about.md.

Replaces the block between <!-- AUTO-UPDATE-START --> and <!-- AUTO-UPDATE-END -->
with fresh metrics derived from the GitHub account.

Cron 사용 (르무엘):
    0 9 * * * cd /opt/lqc/MyoungSoo7.github.io && \
        /usr/bin/python3 scripts/auto_update_about.py && \
        git -c user.email=auto@lemuel.co.kr -c user.name="auto-update" \
            commit -am "auto: refresh about.md $(date +%F)" && \
        git push
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

GITHUB_USER = os.environ.get("GH_USER", "MyoungSoo7")
ABOUT_PATH = Path(__file__).resolve().parent.parent / "about.md"
START_MARK = "<!-- AUTO-UPDATE-START -->"
END_MARK = "<!-- AUTO-UPDATE-END -->"


def gh_json(args: list[str]) -> dict:
    """Run gh CLI with --json fields and return parsed JSON. Empty dict on error."""
    try:
        out = subprocess.check_output(["gh"] + args, text=True)
        import json
        return json.loads(out)
    except Exception as e:
        print(f"[warn] gh failed: {e}", file=sys.stderr)
        return {}


def repo_count() -> int:
    raw = gh_json(["api", f"users/{GITHUB_USER}", "--jq",
                    "{public_repos: .public_repos}"])
    return int(raw.get("public_repos", 0))


def latest_pushes(limit: int = 5) -> list[dict]:
    raw = gh_json([
        "api", f"users/{GITHUB_USER}/repos?sort=pushed&per_page={limit}",
    ])
    if not isinstance(raw, list):
        return []
    out = []
    for r in raw[:limit]:
        out.append({
            "name": r.get("name"),
            "url": r.get("html_url"),
            "desc": (r.get("description") or "").strip()[:120],
            "pushed": r.get("pushed_at", "")[:10],
            "lang": r.get("language") or "",
            "stars": r.get("stargazers_count", 0),
        })
    return out


def render_block() -> str:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    repos = repo_count()
    pushes = latest_pushes(5)

    lines = [
        START_MARK,
        f"*Last auto-update: {today} (KST)* — public repos: **{repos}**",
        "",
        "#### 🔥 최근 푸시한 레포 5",
        "",
        "| 레포 | 언어 | 마지막 푸시 | 설명 |",
        "|------|------|-------------|------|",
    ]
    for p in pushes:
        desc = p["desc"].replace("|", "\\|")
        lines.append(
            f"| [{p['name']}]({p['url']}) | {p['lang']} | "
            f"{p['pushed']} | {desc} |"
        )
    lines.append("")
    lines.append(END_MARK)
    return "\n".join(lines)


def main() -> int:
    if not ABOUT_PATH.exists():
        print(f"about.md not found at {ABOUT_PATH}", file=sys.stderr)
        return 1
    src = ABOUT_PATH.read_text(encoding="utf-8")
    if START_MARK not in src or END_MARK not in src:
        print("auto-update markers missing in about.md", file=sys.stderr)
        return 2

    new_block = render_block()
    pattern = re.compile(
        re.escape(START_MARK) + r".*?" + re.escape(END_MARK),
        re.DOTALL,
    )
    updated = pattern.sub(new_block, src)

    if updated == src:
        print("about.md unchanged; skipping write")
        return 0

    ABOUT_PATH.write_text(updated, encoding="utf-8")
    print(f"about.md updated ({len(updated.splitlines())} lines)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
