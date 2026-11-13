# BE-L05 independent acceptance

**PASS** on candidate `eb4b34dcad3bceb20eb7b55640f039a91b3744fd`. Nginx on port 18195, Compose project `srastemsya_l05_tester_final` with fresh volumes. The suite used documented dev sign-in and request-scoped clocks. The final runner passed 12 methods, with 0 failed and 0 skipped.

| Criteria | Observed |
| --- | --- |
| AC-01 / L05-01 | First pool contains exactly 01–10 in catalog order. |
| AC-02 / L05-02 | Second pool contains the nine remaining A cards in catalog order and then C13. B cards and prior cards are excluded. |
| AC-03 / L05-03 | Round-three pool starts with C then B, matching cumulative weights C=-5, B=-25, A=-40. Round-two-only weights would put B first. |
| AC-04 / L05-04 | The one-category fixture yielded ordered 01–10 and then 11–14. |
| AC-05 / L05-05 | Parallel final completions yielded one next round. All five snapshots agreed on the round and pool, and snapshots were unchanged after restart. |
| AC-06 / L05-06 | An event published by account 6 after round one started occupied its weighted position between A11 and A14 in round two. Round one stayed unchanged. |
| L04-01–04 | Expiry T+30 and T+50, continued voting at T+30, closure at T+50, post-closure writes rejected and no state changes. Swipes restart preserved all five snapshots including finished and unfinished personal votes. |
| L03-01–05 | Verified thresholds for 2, 3, 5 and 10 participants, exact result fields, pre-match null, tie order and higher-like winner after parallel completions, and L02 regressions. |
| L02-01–04 | Four participants agreed on 10/10/2 in order, then exhaustion. Feed page retained 20 items and cursor. |
| D03-03/04/08/09/10 | Private rooms and fixed membership, incomplete completion rejection, vote replacement and reconnection, long poll join and vote notifications with own-vote privacy, old-version response, empty 204 timeout, outsider 404 and revoked-session 401. |
| INT-01/02 | Missing session and incomplete profile blocked with 401 and 403. Isolated swipes database interruption yielded 503 and recovery yielded 200. The suite checked responses and swipes logs for credential-shaped text. |

AC-07 is Developer evidence. AC-08 is PM evidence.

The first run observed the contracted 401 on revocation and failed because the test also required an unspecified error code. The final run asserted the contracted status on fresh volumes. [First run](../../../backend/services/swipes/tests/reports/20261113T061447Z-be-l05-24604.md) · [First review](../../../backend/services/swipes/tests/reviews/20261113T061447Z-be-l05-24604.md)

[Final runner output](../../../backend/services/swipes/tests/reports/20261113T061615Z-be-l05-24678.md) · [Final review](../../../backend/services/swipes/tests/reviews/20261113T061615Z-be-l05-24678.md)
