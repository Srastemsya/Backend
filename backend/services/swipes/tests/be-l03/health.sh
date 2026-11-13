#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../../../.."
export NGINX_PORT=18943
compose=(docker compose -p srastemsya_l03 -f compose.yaml -f compose.dev.yaml)
health_url="${L03_BASE:-http://127.0.0.1:18943}/swipes/health"
body="$(mktemp)"
logs="$(mktemp)"
since="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
restore() {
    "${compose[@]}" start swipes-db >/dev/null 2>&1 || true
    rm -f "$body" "$logs"
}
trap restore EXIT

test "$(curl -sS -o "$body" -w '%{http_code}' "$health_url")" = 200
"${compose[@]}" stop swipes-db >/dev/null 2>&1
test "$(curl -sS -o "$body" -w '%{http_code}' "$health_url")" = 503
"${compose[@]}" logs --since "$since" --no-color swipes > "$logs"
python3 - "$body" "$logs" <<'PY'
import json
import re
import sys
from pathlib import Path

response = Path(sys.argv[1]).read_text()
json.loads(response)
for path in sys.argv[1:]:
    text = Path(path).read_text()
    if re.search(r"postgres(?:ql)?://|password\s*[=:]|Bearer\s+\S+|BEGIN .*PRIVATE KEY", text, re.I):
        raise SystemExit("credential pattern found in health response or service logs")
PY
"${compose[@]}" start swipes-db >/dev/null 2>&1
for ((attempt=0; attempt<30; attempt++)); do
    if test "$(curl -sS -o "$body" -w '%{http_code}' "$health_url")" = 200; then
        printf '%s\n' 'INT-02 PASS (200, 503, 200; no credential patterns in outage response or swipes logs)'
        exit 0
    fi
    sleep 1
done
printf '%s\n' 'INT-02 FAIL (health did not recover)' >&2
exit 1
