# BE-L05 acceptance

Sources: [scope](../../specs/lobby-v2/BE-L05.md), [implementation and common rules](../../../docs/specs/lobby-v2/implementation.md), [L05 and inherited L04 criteria](../../../docs/specs/lobby-v2/acceptance.md), [room v2 contract](../../../docs/contracts/lobby-v2.md).

Use five participants with mixed EVENT fixtures on 2090-02-01 unless otherwise specified.

- AC-01 / L05-01. On start the first pool contains cards 01–10 in catalog order.
- AC-02 / L05-02. Give each a card three likes and skip every b card unanimously. The second pool contains a before previously unshown c, with b deferred behind both. Preserve catalog order within equal weights and exclude prior cards.
- AC-03 / L05-03. Vote in round two so cumulative weighting and last-round-only weighting yield distinct category orders. The third pool follows the cumulative sum of likes minus skips across all completed rounds.
- AC-04 / L05-04. With one category selected, both pools preserve catalog order and contain no repeats.
- AC-05 / L05-05. Complete the round concurrently as the final two participants without a match. Exactly one next round is persisted and all participants observe the identical pool and order before and after restarting swipes.
- AC-06 / L05-06. Publish a matching event from another account between rounds and observe it in the next pool at its weighted and catalog position. Re-run L04-01 through L04-04 and their inherited criteria.
- AC-07 / Implementation steps 1–5. Developer demonstrates stored completed-round card references, category, likes and skips, filtering before stable weighting and a ten-card cap. Unit tests cover both pure functions and the developer-guide example. Architecture and common-rule checks are Developer evidence.
- AC-08 / Implementation step 6. Discovery v1, backend BE-04 and swipes documentation describe the new behavior and relevant contracts. PM reviews the updated documents and service ownership and endpoint coverage.
