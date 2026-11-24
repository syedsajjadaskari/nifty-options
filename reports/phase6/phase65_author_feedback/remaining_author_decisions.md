# Remaining author / owner decisions (Phase 6.5)

| # | decision | why it matters |
|---|---|---|
| 1 | Keep or relax the close-above-ceiling requirement for PDR (B1/B2 bypass it) | the largest source of PDR entry delay; owner-approved today |
| 2 | May the retest candle itself confirm PDR (B2/C)? | unresolved sequencing; affects many cycles |
| 3 | Define PDR / PDS second-confirmation (if wanted at all) | the variants D / SECOND are mechanical conventions |
| 4 | Is a candle-body threshold wanted, for which methods, and at what level? | no source defines one; in the strength gates every removed trade is a direct effect and every added trade a portfolio effect (see the report) |
| 5 | ORB V2 provisional rules: pattern definitions, inner levels, wick rule vs the rulebook examples, feed | 27 disputed dates fail ORB, 12 only on provisional gates |
| 6 | Reconcile Phase 6.5 and Phase 7.0 IRF implementations of the two new methods; decide integration | both exist; signals were compared, not declared equal |
| 7 | Provide direction / price / level for journal rows if exact matching is wanted | no exact trade match is possible today |
| 9 | PDS second confirmation: may a weak red candle between the first and the second eligible candle be skipped? | changes the number of second signals (see `pds_second_weak_red_interplay.json`) |
| 10 | PDR green-only variants: keep or drop the lower-price-rejection confirmation route | B1 / B2 / C currently drop it, which confounds their comparison with the baseline |
| 8 | Tie-break policy for same-minute collisions and the forced-exit convention | still unapproved |

None of the variants has been, or should be, adopted on historical performance.