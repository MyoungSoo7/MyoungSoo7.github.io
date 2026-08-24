#!/usr/bin/env bash
# _data/popular.json 을 다시 세어 커밋·푸시한다. 하루 한 번.
# 맥 등록: LaunchAgent com.lms.blog-popular (매일 09:40 KST)
#   로그: ~/Library/Logs/blog-popular.log
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT"

echo "[$(date '+%F %T')] sync"
# --autostash: 다른 세션이 워킹트리를 쓰고 있어도 rebase 가 죽지 않게.
git pull --rebase --autostash origin master || true

/usr/bin/python3 "$SCRIPT_DIR/update_popular.py"

if [[ -z "$(git status --porcelain _data/popular.json)" ]]; then
    echo "[$(date '+%F %T')] 순위 변동 없음"
    exit 0
fi

# *이 파일만* 커밋한다. 같은 리포를 여러 세션이 쓰고 있어서 -a 는 남의 작업을 끌어간다.
git add _data/popular.json
git -c user.email="auto@lemuel.co.kr" -c user.name="auto-update" \
    commit -m "auto: 인기글 순위 갱신 $(date +%F)" -- _data/popular.json

# push 는 거절을 전제로 재시도한다. 동시에 올리면 하나만 성공하고 나머지는 non-fast-forward
# 로 *거절* 된다 — 덮어쓰기는 구조적으로 없다. --force 는 절대 쓰지 않는다.
for i in 1 2 3; do
    if git push origin master; then
        echo "[$(date '+%F %T')] pushed (시도 $i)"
        exit 0
    fi
    echo "[$(date '+%F %T')] push 거절됨 — rebase 후 재시도 ($i)"
    git pull --rebase --autostash origin master || true
done

echo "[$(date '+%F %T')] push 3회 실패" >&2
exit 1
