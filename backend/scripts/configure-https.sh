#!/usr/bin/env bash
set -euo pipefail

environment=$1
domain=$2
case "$environment" in
  staging) port=18080 ;;
  demo) port=8080 ;;
  *) exit 2 ;;
esac
label='[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?'
if [[ ${#domain} -gt 253 || ! $domain =~ ^($label\.)+$label$ ]]; then
  echo 'API_DOMAIN must be a lowercase DNS hostname' >&2
  exit 2
fi

# Both environments share the system Nginx and Certbot configuration.
exec 9>/run/lock/srastemsya-https.lock
flock 9
config="/etc/nginx/conf.d/srastemsya-$environment.conf"
other=staging
if [[ $environment == staging ]]; then other=demo; fi
other_config="/etc/nginx/conf.d/srastemsya-$other.conf"
if [[ -f $other_config ]] && grep -Fq "server_name $domain;" "$other_config"; then
  echo 'Use a different API_DOMAIN for each environment' >&2
  exit 2
fi

if [[ -f $config ]]; then
  if ! grep -Fq "server_name $domain;" "$config"; then
    echo 'Existing Nginx vhost uses a different domain. Update it on the server first.' >&2
    exit 2
  fi
else
  cat > "$config" <<NGINX
server {
    listen 80;
    server_name $domain;

    location / {
        proxy_pass http://127.0.0.1:$port;
        proxy_set_header Host \$host;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    }
}
NGINX
  if ! nginx -t; then
    rm -f "$config"
    exit 1
  fi
  nginx -s reload
fi

# Never log request targets (which may contain invitation tokens) on either
# the HTTP or HTTPS vhost. Apply also to vhosts created by earlier releases.
if ! grep -Fq 'access_log off; # invitation privacy' "$config"; then
  sed -i '/server_name .*;/a\    access_log off; # invitation privacy' "$config"
  nginx -t
  nginx -s reload
fi

certbot --nginx --non-interactive --agree-tos --register-unsafely-without-email --redirect \
  --keep-until-expiring --cert-name "$domain" -d "$domain"
