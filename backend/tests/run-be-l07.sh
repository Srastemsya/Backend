#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
export NGINX_PORT=18098
stamp="$(date -u +%Y%m%dT%H%M%SZ)-be-l07-$$"
report="tests/reports/$stamp.md"
out="$(mktemp)"
trap 'rm -f "$out"' EXIT
status=0
python3 tests/be_l07_blackbox.py >"$out" 2>&1 || status=$?
{
  printf '# BE-L07 independent HTTP acceptance\n\n'
  printf 'Revision `%s`\n\n' "$(git rev-parse HEAD)"
  printf 'Command `NGINX_PORT=18098 python3 tests/be_l07_blackbox.py`\n\n'
  printf 'Exit code %s. Passed %s, failed %s, skipped 0 case groups.\n\n' "$status" \
    "$(grep -c '^PASS ' "$out" || :)" "$(grep -c '^FAIL ' "$out" || :)"
  printf '```text\n'
  cat "$out"
  printf '```\n'
} > "$report"
cat "$report"
printf '\nEvidence %s\n' "$report"
exit "$status"
