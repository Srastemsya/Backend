# Runtime heal (Compose DNS / deps)

Incident class: app 500s while Postgres is up — `Temporary failure in name resolution`, fallback host `postgres`, containers on different Compose projects. Git looking “old” does not mean Docker networks are fine.

## Always (new FastAPI service)

- `GET /health` is **readiness**: 200 only if own Postgres answers (`SELECT 1`). Redis/Kafka too if the process cannot serve without them. 503 + `{"status":"error","reason":"db"}` — no DSN/passwords.
- Compose **healthcheck** on the app hits `/health`. `depends_on` other apps: `service_healthy`, not `service_started`.
- `DATABASE_URL` host = Compose service name (`identity-db`). No fallback hostname `postgres`.
- Log startup: service name, DB **hostname only**, ready/not. Then ERROR/WARNING only.
- New service → add a row to `scripts/heal-compose-runtime.sh` in the **same change**.
- Prod: do not publish Postgres `5432` on `0.0.0.0`. One Compose project directory forever.

## Heal script (required)

`scripts/heal-compose-runtime.sh` on a 30–60s timer. Detect: crash-loop, `/health` ≠ 200, `getent hosts` miss, gaierror in logs. Fix: `docker compose up -d --force-recreate --no-deps` (app ± its DB).

```text
# ❌ BAD
docker compose down -v
# ✅ GOOD
docker compose up -d --force-recreate --no-deps identity
```

Cooldown per service. Never recreate volumes. Do not log secrets.

