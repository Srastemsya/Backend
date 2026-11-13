#!/usr/bin/env bash
set -uo pipefail
cd "$(dirname "$0")"
stamp="$(date -u +%Y%m%dT%H%M%SZ)-be-l06-$$"
report="../reports/$stamp.md"
output="$(mktemp)"
trap 'rm -f "$output"' EXIT
mkdir -p ../reports
export NGINX_PORT=18197
python3 acceptance_http.py "$@" >"$output" 2>&1
status=$?
passed="$(awk '/^test_.* \.\.\. ok$/{n++} END{print n+0}' "$output")"
failed="$(awk '/^(FAIL|ERROR):/{n++} END{print n+0}' "$output")"
skipped="$(awk '/^test_.* \.\.\. skipped/{n++} END{print n+0}' "$output")"
{
    printf '# BE-L06 HTTP acceptance · %s\n\n' "$stamp"
    printf -- '- Command: `python3 acceptance_http.py%s`\n' "${*:+ $*}"
    printf -- '- Candidate: `%s`\n' "$(git rev-parse HEAD)"
    printf -- '- Exit code: %s\n- Passed: %s\n- Failed: %s\n- Skipped: %s\n\n' "$status" "$passed" "$failed" "$skipped"
    printf '```text\n'
    awk '/^test_|^(FAIL|ERROR):|^Ran |^OK|^FAILED/' "$output"
    printf '```\n'
} > "$report"
cat "$output"
printf 'Report: %s\n' "$report"
exit "$status"
