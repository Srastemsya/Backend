#!/bin/sh
set -u
cd "$(dirname "$0")"
mkdir -p reports
stamp="$(date -u +%Y%m%dT%H%M%SZ)-$$"
report="reports/$stamp.md"
log="$(mktemp)"
trap 'rm -f "$log"' EXIT
set -- python3 -m unittest -v test_room_rules
"$@" >"$log" 2>&1
status=$?
passed=$(awk '/ \.\.\. ok$/ {count++} END {print count+0}' "$log")
failed=$(awk '/ \.\.\. (FAIL|ERROR)$/ {count++} END {print count+0}' "$log")
skipped=$(awk '/ \.\.\. skipped/ {count++} END {print count+0}' "$log")
{
    printf '# Swipes unit tests %s\n\n' "$stamp"
    printf -- '- Command `%s`\n- Exit code %s\n- Passed %s, failed %s, skipped %s\n\n' "$*" "$status" "$passed" "$failed" "$skipped"
    cat "$log"
} >"$report"
printf '%s\n' "$report"
exit "$status"
