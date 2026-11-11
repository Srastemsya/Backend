#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
compose() {
    if [ "${SR_ALWAYS_DEV:-0}" = 1 ]; then
        docker compose -f compose.yaml -f compose.dev.yaml "$@"
    else
        docker compose -f compose.yaml "$@"
    fi
}
state_dir="${TMPDIR:-/tmp}/srastemsya-heal-${COMPOSE_PROJECT_NAME:-srastemsya}"
mkdir -p "$state_dir"
now=$(date +%s)
for service in identity catalog swipes; do
    db="$service-db"
    if compose exec -T "$service" python -c "import socket,urllib.request; socket.getaddrinfo('$db',5432); urllib.request.urlopen('http://localhost:8000/health',timeout=5)" >/dev/null 2>&1 &&
        ! compose logs --no-color --since 1m "$service" 2>/dev/null | grep -q 'gaierror'; then
        continue
    fi
    last=$(cat "$state_dir/$service" 2>/dev/null || echo 0)
    [ "$((now - last))" -ge 120 ] || continue
    printf '%s\n' "$now" > "$state_dir/$service"
    compose up -d --force-recreate --no-deps "$service" >/dev/null 2>&1 || printf 'Recovery failed for %s\n' "$service" >&2
done
