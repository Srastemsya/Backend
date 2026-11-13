#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p ../reports
stamp="$(date -u +%Y%m%dT%H%M%SZ)-l03-$$"
report="../reports/$stamp.md"
http_output="$(mktemp)"
health_output="$(mktemp)"
trap 'rm -f "$http_output" "$health_output"' EXIT

http_status=0
health_status=0
python3 http_acceptance.py > "$http_output" 2>&1 || http_status=$?
bash health.sh > "$health_output" 2>&1 || health_status=$?
passed="$(awk '/^test_.* \.\.\. ok$/ {count++} END {print count+0}' "$http_output")"
skipped="$(awk '/^test_.* \.\.\. skipped/ {count++} END {print count+0}' "$http_output")"
failed=$((8 - passed - skipped))
if ((health_status == 0)); then
    passed=$((passed + 1))
else
    failed=$((failed + 1))
fi
exit_code=0
if ((http_status || health_status || failed || skipped)); then
    exit_code=1
fi
{
    printf '# BE-L03 swipes HTTP acceptance\n\n'
    printf -- '- UTC stamp: %s\n' "$stamp"
    printf -- '- Commands: `python3 http_acceptance.py` and `bash health.sh`\n'
    printf -- '- Exit code: %d (HTTP %d, readiness %d)\n' "$exit_code" "$http_status" "$health_status"
    printf -- '- Passed: %d\n- Failed or aborted: %d\n- Skipped: %d\n\n' "$passed" "$failed" "$skipped"
    printf '~~~text\n'
    awk '/^test_|^FAIL:|^ERROR:|^AssertionError:|^RuntimeError:|^Ran |^FAILED|^OK/' "$http_output"
    awk '/^INT-02/' "$health_output"
    printf '~~~\n'
} > "$report"
cat "$report"
printf '\nReport: %s\n' "$report"
exit "$exit_code"
