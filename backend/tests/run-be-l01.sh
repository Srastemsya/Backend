#!/bin/sh
# BE-L01 acceptance suite. Runs only this unit and writes one factual
# timestamped report per invocation. Never hand-edits reports.
set -u
cd "$(dirname "$0")"
mkdir -p reports
stamp="$(date -u +%Y%m%dT%H%M%SZ)-$$"
report="reports/$stamp-be-l01.md"
log="$(mktemp)"
compose_log="$log.compose"
trap 'rm -f "$log" "$compose_log"' EXIT

base_url="${BE_L01_BASE_URL:-http://127.0.0.1:18090}"
project="${BE_L01_COMPOSE_PROJECT:-}"
port="${BE_L01_NGINX_PORT:-18090}"
SUMMARY=""
compose_status="skipped"

if [ -n "$project" ] && [ "${BE_L01_SKIP_RESTART:-0}" != "1" ]; then
    NGINX_PORT="$port" docker compose -p "$project" \
        -f ../compose.yaml -f ../compose.dev.yaml \
        up --build -d --wait >"$compose_log" 2>&1
    compose_status="$?"
    SUMMARY="repeat Compose ${project} (NGINX_PORT=${port}): exit ${compose_status}"
fi

if [ -z "${BE_L01_PREV_IDS:-}" ]; then
    BE_L01_PREV_IDS="$(ls -1t reports/*-be-l01-prev-ids.json 2>/dev/null | head -1)"
fi
export BE_L01_BASE_URL="$base_url"
export BE_L01_PREV_IDS="${BE_L01_PREV_IDS:-}"
export BE_L01_COMPOSE_PROJECT="$project"
export PYTHONWARNINGS=ignore

if [ "$#" -eq 0 ]; then
    set -- python3 be_l01_acceptance.py
fi
"$@" >"$log" 2>&1
status=$?

passed=$(awk '/ \.\.\. ok$/ {count++} END {print count+0}' "$log")
failed=$(awk '/ \.\.\. (FAIL|ERROR)$/ {count++} END {print count+0}' "$log")
skipped=$(awk '/ \.\.\. skipped/ {count++} END {print count+0}' "$log")
redact='s/(accessToken|refreshToken|token)=[^&" ]+/\1=REDACTED/g; s/eyJ[A-Za-z0-9._-]+/JWT_REDACTED/g'

{
    printf '# BE-L01 acceptance run %s\n\n' "$stamp"
    printf -- '- Command `%s`\n' "$*"
    printf -- '- Base URL `%s`\n' "$base_url"
    printf -- '- Compose project `%s`, %s\n' "${project:-none}" "${SUMMARY:-no restart}"
    printf -- '- Exit code %s\n- Passed %s, failed %s, skipped %s\n\n' \
        "$status" "$passed" "$failed" "$skipped"
    printf '## Checks\n\n```\n'
    awk '/^test_[a-z0-9_]+ .*\.\.\. (ok|FAIL|ERROR|skipped)$/' "$log" \
        | sed -E "$redact"
    printf '```\n\n## Failures\n\n```\n'
    awk '/^AssertionError: /' "$log" | head -20 | sed -E "$redact"
    printf '```\n'
    printf '\n## Summary\n\n```\n'
    awk '/^Ran [0-9]+ test/ || /^OK$/ || /^FAILED \(/ || /^FAILED$/' "$log"
    printf '```\n'
} >"$report"

if [ "$compose_status" != "skipped" ] && [ "$compose_status" -ne 0 ]; then
    printf 'compose failed; see infra log, report: %s\n' "$report" >&2
    exit "$compose_status"
fi
printf '%s\n' "$report"
exit "$status"
