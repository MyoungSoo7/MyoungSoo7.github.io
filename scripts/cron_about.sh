#!/usr/bin/env bash
# Daily about.md auto-update + commit + push.
# Cron 등록 예 (르무엘):
#   0 9 * * * /opt/lqc/MyoungSoo7.github.io/scripts/cron_about.sh >> /var/log/lqc/about_update.log 2>&1
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$ROOT"
echo "[$(date '+%F %T')] sync"
git -c safe.directory="$ROOT" pull --rebase --autostash || true

if /usr/bin/python3 "$SCRIPT_DIR/auto_update_about.py"; then
    if [[ -n "$(git status --porcelain about.md)" ]]; then
        git -c user.email="auto@lemuel.co.kr" \
            -c user.name="auto-update" \
            add about.md
        git commit -m "auto: refresh about.md $(date +%F)"
        git push origin master
        echo "[$(date '+%F %T')] pushed"
    else
        echo "[$(date '+%F %T')] no changes"
    fi
else
    echo "[$(date '+%F %T')] update script failed" >&2
    exit 1
fi
