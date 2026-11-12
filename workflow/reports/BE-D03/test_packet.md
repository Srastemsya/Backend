# BE-D03 · Test packet

Candidate commit: `7875b58` in the assigned worktree. Build the runtime locally from that revision.

From `backend`, use a fresh Compose project and verify the checked-out revision before starting:

```sh
git rev-parse --short HEAD
NGINX_PORT=18088 docker compose -p srastemsya_d03test -f compose.yaml -f compose.dev.yaml up --build -d --wait
curl -i http://127.0.0.1:18088/swipes/health
```

Use `http://127.0.0.1:18088/v1` for public HTTP. Repeat the same startup command for the repeat-start exercise. Keep all commands on the isolated project. Process and database controls from `backend`:

```sh
docker compose -p srastemsya_d03test -f compose.yaml -f compose.dev.yaml restart swipes
docker compose -p srastemsya_d03test -f compose.yaml -f compose.dev.yaml stop swipes-db
curl -i http://127.0.0.1:18088/swipes/health
docker compose -p srastemsya_d03test -f compose.yaml -f compose.dev.yaml start swipes-db
curl -i http://127.0.0.1:18088/swipes/health
```

Dev contacts `person1@example.test` through `person5@example.test` have complete profiles. `new@example.test` (EMAIL) and `+15550100100` (SMS) begin registration on a fresh project. The mock accepts these exact contacts. For a repeat incomplete-profile check, use the other contact if it has not been completed, or start a fresh Compose project. Use the synthetic OTP and profile setup documented in the backend README and Discovery contract.

Fixture categories `dev-swipe-places` and `dev-swipe-events` each contain 22 cards. IDs are `dev-swipe-place-01` through `dev-swipe-place-22` and `dev-swipe-event-01` through `dev-swipe-event-22`. Cards 01–20 cost 1000 RUB minor units per person, 21 costs 500, and 22 has unknown price. Event timestamps are 2 January 2090 at 00:01–00:22 UTC. A zero room budget provides an empty starting pool in these categories.

Use `X-Dev-Swipes-Now: 2089-01-01T00:00:00Z` on the first candidate request or room start, and `X-Dev-Swipes-Now: 2089-01-01T00:30:00Z` on the cursor or room expiry request. Use the same clock header on the initial invite and on later join to exercise the invitation expiry. Session time uses the identity clock.

[Backend startup and dev fixtures](../../../backend/README.md) · [Discovery v1 HTTP](../../../docs/contracts/discovery-v1.md) · [Mobile HTTP DTOs](../../../docs/contracts/mobile-api.md).
