# BE-L05 public test packet

Candidate `eb4b34dcad3bceb20eb7b55640f039a91b3744fd` on `be-l05`.

[Room v2](../../../docs/contracts/lobby-v2.md) · [Discovery v1](../../../docs/contracts/discovery-v1.md) · [Mobile HTTP](../../../docs/contracts/mobile-api.md) · [Swipes routes](../../../docs/services/swipes.md) · [Dev fixtures and mock sign-in](../../../backend/README.md#стендовые-данные-комнаты-be-l01)

Run from the candidate's `backend` directory using an unused project and port dedicated to this test.

```sh
export NGINX_PORT=18195
docker compose -p srastemsya_l05_tester -f compose.yaml -f compose.dev.yaml up --build -d --wait
curl -fsS http://127.0.0.1:18195/swipes/health
docker compose -p srastemsya_l05_tester -f compose.yaml -f compose.dev.yaml restart swipes
curl --retry 15 --retry-delay 1 --retry-connrefused -fsS http://127.0.0.1:18195/swipes/health
docker compose -p srastemsya_l05_tester -f compose.yaml -f compose.dev.yaml down
```

For a fresh set of volumes, run the same startup command with a new unused project name after stopping the dedicated stack. Use that project name for restart and shutdown as well.

The public API prefix is `/v1` at `http://127.0.0.1:18195`. Dev accounts are `person1@example.test` through `person10@example.test` with fixture sign-in described in the backend README. Fixtures are selectable with `kind=EVENT&localDate=2090-02-01`, `kind=EVENT&categoryId=dev-lobby-short` and `kind=EVENT&categoryId=dev-lobby-two`. Request-scoped clocks are `X-Dev-Swipes-Now` and `X-Dev-Catalog-Now` with RFC 3339 timestamps.
