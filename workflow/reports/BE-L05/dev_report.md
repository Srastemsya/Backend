# BE-L05 developer report

Candidate `eb4b34dcad3bceb20eb7b55640f039a91b3744fd` on `be-l05`, based on `origin/dev` at `03bab0a`. Developer Compose project `srastemsya_l05` on port 18095.

## Implementation and architecture

- The final completion aggregates the round's cards in pool order with reference, category, likes and passes. The same counts drive the threshold check. The completed-round summary is appended before the next pool is built, and the summary and next pool are persisted together in swipes' own PostgreSQL snapshot.
- The round transition uses the existing row lock and completion replay check. The existing transaction updates the version once, and Redis publishes the version after the database commit. Public snapshots continue to expose only the requesting member's votes. Reading older snapshots without a history field starts accumulation with the next completion.
- The next round reads the current candidate list via the existing internal catalog HTTP contract, a synchronous read at round creation. Swipes filters out previously shown cards, applies stable descending category weights and caps the pool at ten. Single-user pagination, authentication, admin and readiness routes, Redis notification and recovery configuration, errors and the exhaustion state are unchanged.
- The two sorting and weighting functions use only their inputs and import no service dependencies. Public routes, schema, cache behavior, inter-service contracts and service ownership remain unchanged.

## Evidence

- `sh backend/services/swipes/tests/run.sh` passed 5/5, covering both pure functions, zero-weight categories and the cumulative fixture example. [Suite output](../../../backend/services/swipes/tests/reports/20261113T061020Z-23923.md)
- `git diff --check` passed.
- `NGINX_PORT=18095 docker compose -p srastemsya_l05 -f compose.yaml -f compose.dev.yaml up --build -d --wait` succeeded from `backend`. `GET /swipes/health` through Nginx returned 200.
- Public HTTP smoke with five dev participants exercised the two completed mixed rounds and verified all three exact pools through Nginx.
- Repeating the same Compose startup succeeded and readiness again returned 200. Fixture counts after the repeat were not measured separately. The isolated stack was stopped with `NGINX_PORT=18095 docker compose -p srastemsya_l05 -f compose.yaml -f compose.dev.yaml down`, preserving volumes.
- Source checks: `git diff --check origin/dev` passed. `rg -n 'room_candidates|FOR UPDATE|notify|save|PAGE_SIZE|ROOM_POOL_SIZE' backend/runtime/swipes.py` and inspection of the surrounding transaction confirmed that the lock, version update, post-commit notification and distinct feed/room limits remain in place. `rg -n 'swipes:|swipes-db:|healthcheck|service_healthy' backend/compose.yaml` and `rg -n 'swipes' backend/scripts/heal-compose-runtime.sh` confirmed the existing swipes DB, readiness dependency and recovery coverage. `git diff --name-only origin/dev` confirmed no changes to the runtime configuration, schemas, other services or acceptance suites.
- Concurrency, restart persistence, publication and inherited L04 acceptance are covered by independent Tester validation.

## Updated public documentation

[Discovery v1](../../../docs/contracts/discovery-v1.md#свайпы-в-комнате) · [Backend specification, BE-04](../../../docs/specs/backend.md#be-04--подборки-и-комнаты) · [Swipes service](../../../docs/services/swipes.md)
