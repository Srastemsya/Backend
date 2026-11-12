#!/bin/sh
set -eu
cd "$(dirname "$0")"
: "${D02_PROJECT:?Set D02_PROJECT to the isolated development project}"
case "$D02_PROJECT" in
  srastemsya-be-d02*) ;;
  *) printf '%s\n' 'Use an isolated BE-D02 Compose project' >&2; exit 2 ;;
esac
exec ./run.sh sh -c '
    docker compose -p "$D02_PROJECT" -f ../compose.yaml -f ../compose.dev.yaml \
        exec -T catalog python - < be_d02_architecture.py
'
