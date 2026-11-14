# BE-D03 · Independent black-box acceptance

**AC-01–15 PASS** for candidate `7875b58`, built in fresh Compose project `srastemsya_d03test`. The suite executed 15 criteria with zero failures and zero skips. AC-16 has separate evidence.

From `backend`:

```sh
NGINX_PORT=18088 docker compose -p srastemsya_d03test -f compose.yaml -f compose.dev.yaml up --build -d --wait
curl -i http://127.0.0.1:18088/swipes/health
NGINX_PORT=18088 services/matching/tests/run.sh
```

| Criterion | Observed |
|---|---|
| AC-01 | EVENT and PLACE boundary prices included, unknown prices excluded with a budget and included without it. |
| AC-02 | Nonoverlapping pages through null cursor, exact replay despite a new publication, 409 CURSOR_EXPIRED at 30 minutes. |
| AC-03 | Four identical rosters and card orders, outsider 404, no late admission. |
| AC-04 | Incomplete pass 409 INVALID_STATE, revised choice retained, post-completion edit rejected, personal progress recovered. |
| AC-05 | Two of four likes produced no match, next round excluded prior cards, small pool exhausted, completion replay returned current snapshot and old vote returned 409 STALE_ROUND. |
| AC-06 | Parallel completion yielded one shared MATCHED result. Equal majorities used pool order and unequal majorities used the higher count. |
| AC-07 | Reconnect and restart preserved roster and vote. At 30 minutes room became CLOSED with null round and rejected mutation. |
| AC-08 | Join woke lobby poll with 200 and a higher version. The invitation token was absent. |
| AC-09 | Vote and completion woke polls. Older version returned immediately. Peer decisions remained private. |
| AC-10 | Idle poll held for the 25-second window and returned empty 204. Next poll delivered the join. Outsider got 404 immediately and revoked session got 401 SESSION_EXPIRED. |
| AC-11 | Fresh and repeat Compose startups succeeded. Nginx health returned 200, protected registration, events and rooms worked, categories did not duplicate, and only Nginx had a loopback port published. |
| AC-12 | Protected endpoints returned 401 UNAUTHENTICATED and 403 PROFILE_INCOMPLETE as appropriate. |
| AC-13 | Stopping the matching database yielded 503 and restarting it restored 200. The checked body and matching logs exposed no database connection URI. |
| AC-14 | Process restart preserved all per-viewer snapshots and prior shown cards, and retained the room deadline tested under AC-07. Four start/join races each yielded a serializable roster. |
| AC-15 | Nginx delivered near-subscribe update and recovered after cancellation. Clock fixture checked expiry boundaries and captured logs lacked tested tokens. Developer source checks are a separate part of this criterion. |

[Passing script report](../../../backend/services/matching/tests/reports/20261112T045901Z-80802.md) · [Independent review](../../../backend/services/matching/tests/reviews/20261112T045901Z-80802.md)

The initial harness attempt used a generated email outside the packet's supported dev fixtures. The corrected run used the documented accounts. [Initial script report](../../../backend/services/matching/tests/reports/20261112T045829Z-80531.md) · [Initial review](../../../backend/services/matching/tests/reviews/20261112T045829Z-80531.md)

## AC-16 · Independent full release journey

**PASS** on the same runtime candidate `7875b58`. A separate tester used fresh Compose project `srastemsya_release_e2e` and exercised the documented routes through Nginx on port 18089.

From `backend`:

```sh
NGINX_PORT=18089 docker compose -p srastemsya_release_e2e -f compose.yaml -f compose.dev.yaml up --build -d --wait
```

Email and SMS profile completion returned HTTP 200. Event publication returned 201. A different account saw the same EVENT ref in the list, map and a fresh swipe request, each HTTP 200. The parallel final-seat race returned 201 and 409 EVENT_FULL, with counts 1/1/0. Invitation creation returned 201, join via the invite link returned 200, and the waiting organizer received HTTP 200 for the updated lobby and terminal MATCHED result for the published event.

[Factual run](../../../backend/tests/reports/20261112T050047Z-release-e2e-81112.md) · [Independent review](../../../backend/tests/reviews/20261112T050047Z-release-e2e-81112.md) · [Initial sandbox attempt](../../../backend/tests/reports/20261112T050035Z-release-e2e-81023.md)
