# Backend architecture (standing rule)

```text
Browser / apps
    ▲  JWT (HttpOnly cookie) + CSRF
FastAPI service  ← own Postgres  · Redis cache  · admin JWT UI
    ▲
Kafka (default) · HTTP only when rare sync needed
```

**Stack:** FastAPI · Docker Compose · Kafka · Postgres · Redis.

The browser cookie and CSRF requirements apply to browser sessions. Follow the [mobile HTTP contract](../../../docs/contracts/mobile-api.md) for Android and iOS authentication.

## Always

- **One service = one Postgres DB.** No shared schemas / cross-service SQL.
- **Inter-service:** Kafka events by default; HTTP only for rare sync/read paths — document why.
- **Cache** public/read responses in Redis (TTL + invalidate on writes/events).
- **Auth:** user JWT; browser sessions via **HttpOnly** cookies + **CSRF** for cookie-auth mutating requests.
- **Admin:** each service exposes an **admin UI** gated by **admin JWT** (separate from user JWT).
- Startup: log **service status** (name, version/env, DB/Kafka/Redis readiness). Then only **ERROR** and **WARNING** in normal operation.
- **Runtime heal:** `/health` must probe own DB; Compose healthcheck + `scripts/heal-compose-runtime.sh` (rule: `workflow/rules/matchwear/runtime-heal.md`).

## Secrets hygiene

- Never log or echo passwords, JWTs, refresh tokens, CSRF secrets, Authorization headers, cookie values.
- Redact secrets in exception/request dumps; no debug middleware that prints full bodies with credentials.

## Don't

- One Postgres for multiple services
- Sync service-to-service SQL or shared ORM models across apps
- Chatty HTTP between services when an event fits
- INFO/DEBUG request spam in production logs
- Admin routes without admin JWT

**Docs:** new/changed HTTP or Kafka surfaces → update the relevant contract in the same change (rule: `workflow/rules/matchwear/docs-with-code.md`).
