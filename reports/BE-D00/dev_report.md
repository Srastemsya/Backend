# BE-D00 · Developer

Candidate based on be714aa. Developer runtime image config ID `0b865aa7c0f9f9ce10c5d23c7077a29612a110896dc5071bd9591664018d747c` (isolated Compose project).

- Delivered FastAPI identity and profile state, PostgreSQL bootstrap and fixtures, Redis OTP verifier and shared session/profile checks, separate role credentials and ACL, RS256 tokens, atomic database locking around challenge/replay and refresh rotation, encrypted retry payloads, and Nginx access gates for BE-D01/BE-D03.
- Source/config review checked separate PostgreSQL service names, users, volumes and health probes, separate private/public mounts, Redis TTL and role ACLs, private OTP/refresh verification values, idempotency encryption, startup/readiness sanitization, recovery script and Nginx proxy directives. Catalog and swipes currently implement only protected package-boundary responses. Kafka starts in Compose and is reserved for later catalog work.
- Passed Python compileall, shell syntax, Compose config validation and git diff --check. Docker Compose built and reported three API services, three DBs, Redis, Kafka and Nginx healthy, with the key bootstrap completing. The default port was occupied by an unrelated Compose container, so smoke used the documented override on 18080.
- HTTP smoke returned health 200 for all three services, challenge 201, verify 200, incomplete home 403, registration 200, home and rooms 200 with the same access token, logout 204 and rooms 401. The independent Tester owns acceptance evidence.
- [Public runbook](../../backend/README.md) · [mobile contract](../../docs/contracts/mobile-api.md) · [Discovery contract](../../docs/contracts/discovery-v1.md)

## Source-level compliance evidence

- Seed repeat and migration check via PostgreSQL returned `5|5` for row/distinct contact counts and `1` migration version, both before and after restarting identity and running Compose wait again. The separate synthetic phone and new email are accepted by the development contact allowlist and create accounts on successful verification.
- Both catalog and swipes runtime credentials successfully read the authorization namespace and received Redis NOPERM when attempting a write there. Both containers lacked the private key. Identity alone mounts the private volume; signing uses RS256 while API verification only loads the public PEM.
- Source inspection found OTP verifiers keyed by challenge, HMAC-protected, with 300-second Redis expiry and attempt/resend state serialized in PostgreSQL. Refresh verifiers use HMAC over opaque tokens, and PostgreSQL retry results use authenticated encryption. Session validity keys are written with a 30-day Redis expiry and removed on reuse or logout. Redis connection errors map to 503 and deny protected reads.
- Migration uses repeat-safe DDL and version insertion within the service startup transaction. Source and shell syntax checks verified all three runtime-heal entries, own-database DNS probes, bounded retries via cooldown, no volume deletion and recreation scoped to the affected app.
- Live verification observed an identity-written short-lived authorization key expire in Redis, and stopping/restarting identity's own database changed Nginx readiness from HTTP 503 with the generic database reason back to 200.
- Browser request validation supports an existing session cookie and checks the CSRF token for mutations. This mobile slice issues tokens in the contracted JSON response. Browser cookie issuance requires a separate browser login contract.

## Fix round 1

Rebuilt candidate image config ID `3e1ee132027df35f84be173c8c0bcc00412104f66acd7994b8d0b94fab8c42eb`. Nginx smoke observed `401 UNAUTHENTICATED` without credentials on home, rooms, profile and identity admin. Expired or revoked sessions use `SESSION_EXPIRED`; missing or invalid authentication uses `UNAUTHENTICATED`.

On the round 1 build, captured service, Nginx, database and Redis logs across startup, identity database outage and recovery. The in-memory scan found the expected hostname-only startup record and no DSN, local credential, bearer header or fixture contact markers. HTTP readiness repeated the 503 → 200 transition through Nginx. The command output retained only the scan result.
