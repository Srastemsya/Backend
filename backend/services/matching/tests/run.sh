#!/bin/sh
set -eu
cd "$(dirname "$0")"
mkdir -p reports
stamp="$(date -u +%Y%m%dT%H%M%SZ)-$$"
output="$(mktemp)"
trap 'rm -f "$output"' EXIT HUP INT TERM
suite=acceptance.py
if [ "${1:-}" = "--be-l02" ]; then
    suite=be_l02_acceptance.py
    shift
fi
code=0
python3 -B "$suite" "$@" > "$output" 2>&1 || code=$?
report="reports/$stamp.md"
{
    printf '# Matching acceptance run %s\n\n' "$stamp"
    printf 'Command: `python3 -B %s' "$suite"
    for criterion in "$@"; do printf ' %s' "$criterion"; done
    printf '`\n\n'
    printf 'Exit code: %s\n\n' "$code"
    printf 'Passed: %s\n\n' "$(awk '/^PASS / {count++} END {print count+0}' "$output")"
    printf 'Failed: %s\n\n' "$(awk '/^FAIL / {count++} END {print count+0}' "$output")"
    printf 'Skipped: %s\n\n' "$(awk '/^SKIP / {count++} END {print count+0}' "$output")"
    printf '```text\n'
    cat "$output"
    printf '```\n'
} > "$report"
cat "$output"
printf 'Report: %s/%s\n' "$PWD" "$report"
exit "$code"
