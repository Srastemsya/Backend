#!/bin/sh
set -u
cd "$(dirname "$0")"
mkdir -p ../reports
stamp="$(date -u +%Y%m%dT%H%M%SZ)-be-l05-$$"
report="../reports/$stamp.md"
log="$(mktemp)"
trap 'rm -f "$log"' EXIT
python3 -B -m unittest -v acceptance_http >"$log" 2>&1
status=$?
passed=$(awk '/ \.\.\. ok$/ {n++} END {print n+0}' "$log")
failed=$(awk '/ \.\.\. (FAIL|ERROR)$/ {n++} END {print n+0}' "$log")
skipped=$(awk '/ \.\.\. skipped/ {n++} END {print n+0}' "$log")
{
    printf '# BE-L05 HTTP %s\n\n' "$stamp"
    printf -- '- Command `python3 -B -m unittest -v acceptance_http`\n- Exit code %s\n- Passed %s, failed %s, skipped %s\n\n' "$status" "$passed" "$failed" "$skipped"
    cat "$log"
} >"$report"
printf '%s\n' "$report"
exit "$status"
