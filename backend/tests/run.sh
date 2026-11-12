#!/bin/sh
set -u
cd "$(dirname "$0")"
mkdir -p reports
stamp="$(date -u +%Y%m%dT%H%M%SZ)-$$"
report="reports/$stamp.md"
log="$(mktemp)"
trap 'rm -f "$log"' EXIT
if [ "$#" -eq 0 ]; then
    set -- python3 be_d00_acceptance.py
fi
"$@" >"$log" 2>&1
status=$?
passed=$(awk '/ \.\.\. ok$/ {count++} END {print count+0}' "$log")
failed=$(awk '/ \.\.\. (FAIL|ERROR)$/ {count++} END {print count+0}' "$log")
skipped=$(awk '/ \.\.\. skipped/ {count++} END {print count+0}' "$log")
{
    printf '# Backend run %s\n\n' "$stamp"
    printf -- '- Command `%s`\n- Exit code %s\n- Passed %s, failed %s, skipped %s\n\n' "$*" "$status" "$passed" "$failed" "$skipped"
    awk '/^test_ac/ || /^setUpClass .* \.\.\. ERROR$/ || /^Ran / || /^OK$/ || /^FAILED / || /File ".*be_d(00|01)_(acceptance|runtime|cursor_ttl)\.py", line/ || /^AssertionError: .*D00 sanitized failure/ || /^AssertionError: (.*[0-9] != [0-9]|[0-9]+ not found in \([0-9, ]+\)|False is not true|True is not false)/' "$log"
} >"$report"
printf '%s\n' "$report"
exit "$status"
