#!/usr/bin/env bash
set -euo pipefail

environment=$1
revision=$2
case "$environment" in
  staging) port=18080 ;;
  demo) port=8080 ;;
  *) exit 2 ;;
esac
[[ $revision =~ ^[0-9a-f]{40}$ ]]

root="$HOME/srastemsya/$environment"
test -r "$root/.env"
cd "$(dirname "$0")/.."
export BACKEND_IMAGE="srastemsya-backend:$revision"
export NGINX_PORT="$port"
compose=(docker compose --env-file "$root/.env" -p "srastemsya-$environment"
  -f compose.yaml -f compose.deploy.yaml -f compose.dev.yaml)
"${compose[@]}" config --quiet
docker load --input runtime.tar.gz
rm -f runtime.tar.gz
"${compose[@]}" up --no-build --wait --wait-timeout 240
for service in identity catalog swipes; do
  curl --fail --silent --show-error --max-time 10 "http://127.0.0.1:$port/$service/health"
done
