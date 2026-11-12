#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
stamp="$(date -u +%Y%m%dT%H%M%SZ)-release-e2e-$$"
report="tests/reports/$stamp.md"
mkdir -p tests/reports
startup='NGINX_PORT=18089 docker compose -p srastemsya_release_e2e -f compose.yaml -f compose.dev.yaml up --build -d --wait'
passed=0
failed=0
skipped=1
set -o noclobber
printf '# AC-16 release E2E\n\n- Invocation: `tests/release-e2e/run.sh %s`\n- Startup from backend: `%s`\n' "${1:-}" "$startup" > "$report"
set +o noclobber
finish() {
  rc=$?
  printf '\nExit code: %d. Passed: %d. Failed: %d. Skipped: %d.\n' "$rc" "$passed" "$failed" "$skipped" >> "$report"
  printf 'Report: %s\n' "$report"
}
trap finish EXIT
revision="$(git rev-parse HEAD)"
printf -- '- Build revision: `%s`\n\n' "$revision" >> "$report"
if [[ "$revision" != "${1:-}" ]]; then
  printf 'Candidate mismatch.\n' >> "$report"
  exit 1
fi
project_filter='label=com.docker.compose.project=srastemsya_release_e2e'
containers="$(docker ps -aq --filter "$project_filter")"
volumes="$(docker volume ls -q --filter "$project_filter")"
if [[ -n "$containers" || -n "$volumes" ]]; then
  printf 'The isolated project already has containers or volumes.\n' >> "$report"
  exit 1
fi
if ! NGINX_PORT=18089 docker compose -p srastemsya_release_e2e -f compose.yaml -f compose.dev.yaml up --build -d --wait >/dev/null 2>&1; then
  printf 'Compose startup failed.\n' >> "$report"
  exit 1
fi
skipped=0
if python3 -u tests/release-e2e/scenario.py >> "$report" 2>&1; then
  passed=1
else
  failed=1
  exit 1
fi
