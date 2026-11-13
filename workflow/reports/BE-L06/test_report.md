# BE-L06 · Independent black-box acceptance

**PASS** on candidate `691b00643525f01c528592e8c68f18a36e294103`. Fresh Docker Compose build, public routes via Nginx on port 18197. 14 passed, 0 failed, 0 skipped.

[Harness](../../../backend/services/swipes/tests/be-l06/run.sh) · [Generated report](../../../backend/services/swipes/tests/reports/20261113T062722Z-be-l06-27038.md) · [Coverage review](../../../backend/services/swipes/tests/reviews/20261113T062722Z-be-l06-27038.md)

| Criterion | Test and result |
|---|---|
| AC-01 | `test_ac01`: leader from the first of two rounds won with three likes from five members, `TOP_SCORE`, and a null round. |
| AC-02 | `test_ac02`: ties selected the earlier round and then the earlier candidate in the same round. |
| AC-03 | `test_ac03`: all four short-fixture cards were passed by all three members, yielding `EXHAUSTED` with null round and result. |
| AC-04 | `test_ac04`: a threshold match returned `THRESHOLD`; a zero-budget room started as `EXHAUSTED` with null round and result. |
| AC-05 | `test_ac05`: concurrent completions produced a single final snapshot delivered through long polling; repeats returned the same snapshot; stale votes returned `409 STALE_ROUND`. Vote projections were private. |
| AC-06 | `test_l05_01_02_03_05`, `test_l05_04`, `test_l05_06_l04`: catalog and weighted order, cumulative weights, single-category order, concurrent completion and restart, new publication, and both expiry boundaries passed. Transitive L03, L02, D03-03/04/08–10 and INT-01/02 checks passed in the same run. |

The [initial run](../../../backend/services/swipes/tests/reports/20261113T062552Z-be-l06-26876.md) hit fixture sign-in cooldown while setting up the revoked-session check. The [initial review](../../../backend/services/swipes/tests/reviews/20261113T062552Z-be-l06-26876.md) records the correction. The final run reused its existing session and completed the revocation check.

Reproduction on a fresh project from the backend directory. Set `NGINX_PORT=18197`, start Compose per the [test packet](test_packet.md), then run `BE_L06_PROJECT=<project> services/swipes/tests/be-l06/run.sh`.
