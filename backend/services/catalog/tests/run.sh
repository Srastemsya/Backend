#!/bin/sh
set -eu
cd "$(dirname "$0")"
stamp="$(date -u +%Y%m%dT%H%M%SZ)-$$"
mkdir -p reports
output="$(mktemp)"
trap 'rm -f "$output"' EXIT
status=0
python3 be_d02_blackbox.py >"$output" 2>&1 || status=$?
report="reports/$stamp.md"
{
  printf '# BE-D02 black-box run\n\nCommand: `python3 be_d02_blackbox.py`\nExit code: %s\n\n' "$status"
  cat "$output"
} >"$report"
cat "$report"
printf '\nReport: %s\n' "$report"
exit "$status"
