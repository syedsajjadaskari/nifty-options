# ORB versus IRF: the disputed days

A date is disputed when the journal labels ORB and the frozen (A) or Phase 5.3 (B) IRF executed, or configuration C's first trade is IRF. No automatic ORB priority exists or was added: a VALID ORB confirmed at 09:20 always wins under the first-valid-signal controller; an invalid ORB never replaces IRF because its hypothetical trade would have reached a target.

* Disputed dates: **39**. ORB V2 has a valid signal on **12** of them, and on all of those ORB is the selected first trade (software-defect count: **0**).
* ORB V2 rejected on the other 27 (a date can fail several conditions): **12** fail ONLY provisional gates (the pattern convention - 11 of them on that gate alone - or the level construction), so they depend on author rules that are not yet defined; **14** fail the EXPLICIT wrong-side-wick rule (> 20% of the range; the rulebook's Examples 2/3 already conflict with this rule, see Phase 6.0) - usually together with the pattern gate; 1 fails the gap limit. On 2 of them ORB V2 WOULD signal on the secondary data feed (data difference).
* The author's pattern 'ORB would have hit its target but IRF hit its stop' occurs in the hypothetical paths of **8** dates (ORB counterfactual TARGET versus IRF INITIAL_FULL_STOP); counterfactual ORB paths on rejected days: {'TARGET': 12, 'T1_THEN_BUFFER_STOP': 6, 'INITIAL_FULL_STOP': 9}; IRF outcomes where IRF was executed in C: {'TARGET': 5, 'INITIAL_FULL_STOP': 12, 'T1_THEN_BUFFER_STOP': 6}.
* Counterfactual ORB paths use an ASSUMED direction (the EMA side; the journal records no direction) and the same portfolio exit rules; they are hypotheticals and are labelled so in every chart.

| date | C_first_trade | orb_v2_signal | orb_v2_failed_conditions | orb_cause_class | orb_data_feed_difference | orb_outcome | irf_outcome | author_pattern_orb_target_irf_stop |
|---|---|---|---|---|---|---|---|---|
| 2025-09-11 | ORB@09:20 INITIAL_FULL_STOP | BUY |  | ORB V2 VALID (signal at 09:20) | False | INITIAL_FULL_STOP | T1_THEN_BUFFER_STOP | False |
| 2025-09-16 | no trade | none | NO_PATTERN | PROVISIONAL_PATTERN_CONVENTION | True | TARGET |  | False |
| 2025-10-01 | ORB@09:20 INITIAL_FULL_STOP | SELL |  | ORB V2 VALID (signal at 09:20) | False | INITIAL_FULL_STOP | INITIAL_FULL_STOP | False |
| 2025-10-08 | IRF@09:50 TARGET | none | LEVEL_NOT_BROKEN | PROVISIONAL_LEVEL_CONSTRUCTION | False | T1_THEN_BUFFER_STOP | TARGET | False |
| 2025-10-15 | IRF@09:40 INITIAL_FULL_STOP | none | NO_PATTERN | PROVISIONAL_PATTERN_CONVENTION | False | INITIAL_FULL_STOP | INITIAL_FULL_STOP | False |
| 2025-10-16 | IRF@09:40 INITIAL_FULL_STOP | none | NO_PATTERN;WRONG_SIDE_WICK | PROVISIONAL_PATTERN_CONVENTION; SOURCE_SUPPORTED_RULE (wrong-side wick <= 20%) | False | TARGET | INITIAL_FULL_STOP | True |
| 2025-10-27 | IRF@10:00 INITIAL_FULL_STOP | none | NO_PATTERN;WRONG_SIDE_WICK | PROVISIONAL_PATTERN_CONVENTION; SOURCE_SUPPORTED_RULE (wrong-side wick <= 20%) | False | TARGET | INITIAL_FULL_STOP | True |
| 2025-11-07 | IRF@11:45 INITIAL_FULL_STOP | none | NO_PATTERN;WRONG_SIDE_WICK | PROVISIONAL_PATTERN_CONVENTION; SOURCE_SUPPORTED_RULE (wrong-side wick <= 20%) | False | T1_THEN_BUFFER_STOP | INITIAL_FULL_STOP | False |
| 2025-11-28 | ORB@09:20 INITIAL_FULL_STOP | BUY |  | ORB V2 VALID (signal at 09:20) | False | INITIAL_FULL_STOP | INITIAL_FULL_STOP | False |
| 2025-12-04 | IRF@12:55 T1_THEN_BUFFER_STOP | none | LEVEL_NOT_BROKEN;NO_PATTERN;WRONG_SIDE_WICK | PROVISIONAL_LEVEL_CONSTRUCTION; PROVISIONAL_PATTERN_CONVENTION; SOURCE_SUPPORTED_RULE (wrong-side wick <= 20%) | False | INITIAL_FULL_STOP | T1_THEN_BUFFER_STOP | False |
| 2025-12-05 | ORB@09:20 INITIAL_FULL_STOP | BUY |  | ORB V2 VALID (signal at 09:20) | False | INITIAL_FULL_STOP | TARGET | False |
| 2025-12-12 | IRF@09:50 TARGET | none | NO_PATTERN | PROVISIONAL_PATTERN_CONVENTION | False | T1_THEN_BUFFER_STOP | TARGET | False |
| 2025-12-22 | IRF@09:40 INITIAL_FULL_STOP | none | NO_PATTERN | PROVISIONAL_PATTERN_CONVENTION | False | TARGET | INITIAL_FULL_STOP | True |
| 2025-12-24 | ORB@09:20 T1_THEN_BUFFER_STOP | BUY |  | ORB V2 VALID (signal at 09:20) | False | T1_THEN_BUFFER_STOP | TARGET | False |
| 2025-12-30 | IRF@10:40 TARGET | none | WRONG_SIDE_WICK | SOURCE_SUPPORTED_RULE (wrong-side wick <= 20%) | False | T1_THEN_BUFFER_STOP | TARGET | False |
| 2026-01-02 | no trade | none | NO_PATTERN | PROVISIONAL_PATTERN_CONVENTION | False | TARGET |  | False |
| 2026-01-16 | IRF@10:45 TARGET | none | NO_PATTERN;WRONG_SIDE_WICK | PROVISIONAL_PATTERN_CONVENTION; SOURCE_SUPPORTED_RULE (wrong-side wick <= 20%) | False | INITIAL_FULL_STOP | TARGET | False |
| 2026-01-27 | ORB@09:20 TARGET | SELL |  | ORB V2 VALID (signal at 09:20) | False | TARGET | INITIAL_FULL_STOP | False |
| 2026-02-17 | IRF@10:40 T1_THEN_BUFFER_STOP | none | LEVEL_NOT_BROKEN;NO_PATTERN;WRONG_SIDE_WICK | PROVISIONAL_LEVEL_CONSTRUCTION; PROVISIONAL_PATTERN_CONVENTION; SOURCE_SUPPORTED_RULE (wrong-side wick <= 20%) | False | T1_THEN_BUFFER_STOP | T1_THEN_BUFFER_STOP | False |
| 2026-02-25 | IRF@10:45 TARGET | none | NO_PATTERN;WRONG_SIDE_WICK | PROVISIONAL_PATTERN_CONVENTION; SOURCE_SUPPORTED_RULE (wrong-side wick <= 20%) | False | TARGET | TARGET | False |
| 2026-04-10 | ORB@09:20 INITIAL_FULL_STOP | BUY |  | ORB V2 VALID (signal at 09:20) | False | INITIAL_FULL_STOP | T1_THEN_BUFFER_STOP | False |
| 2026-04-13 | IRF@10:45 INITIAL_FULL_STOP | none | GAP_TOO_LARGE;NO_PATTERN | PROVISIONAL_PATTERN_CONVENTION; SOURCE_RULE_WITH_UNCONFIRMED_LIMIT (250 or 300) | False | INITIAL_FULL_STOP | INITIAL_FULL_STOP | False |
| 2026-04-17 | ORB@09:20 INITIAL_FULL_STOP | BUY |  | ORB V2 VALID (signal at 09:20) | False | INITIAL_FULL_STOP | T1_THEN_BUFFER_STOP | False |
| 2026-04-21 | ORB@09:20 TARGET | BUY |  | ORB V2 VALID (signal at 09:20) | False | TARGET | INITIAL_FULL_STOP | False |
| 2026-05-18 | IRF@12:00 INITIAL_FULL_STOP | none | NO_PATTERN;WRONG_SIDE_WICK | PROVISIONAL_PATTERN_CONVENTION; SOURCE_SUPPORTED_RULE (wrong-side wick <= 20%) | False | TARGET | INITIAL_FULL_STOP | True |
| 2026-05-22 | IRF@09:50 INITIAL_FULL_STOP | none | NO_PATTERN;WRONG_SIDE_WICK | PROVISIONAL_PATTERN_CONVENTION; SOURCE_SUPPORTED_RULE (wrong-side wick <= 20%) | False | TARGET | INITIAL_FULL_STOP | True |
| 2026-05-25 | IRF@11:00 T1_THEN_BUFFER_STOP | none | NO_PATTERN;WRONG_SIDE_WICK | PROVISIONAL_PATTERN_CONVENTION; SOURCE_SUPPORTED_RULE (wrong-side wick <= 20%) | False | INITIAL_FULL_STOP | T1_THEN_BUFFER_STOP | False |
| 2026-06-16 | IRF@09:40 T1_THEN_BUFFER_STOP | none | NO_PATTERN | PROVISIONAL_PATTERN_CONVENTION | False | INITIAL_FULL_STOP | T1_THEN_BUFFER_STOP | False |
| 2026-06-22 | IRF@10:05 T1_THEN_BUFFER_STOP | none | NO_PATTERN;WRONG_SIDE_WICK | PROVISIONAL_PATTERN_CONVENTION; SOURCE_SUPPORTED_RULE (wrong-side wick <= 20%) | False | T1_THEN_BUFFER_STOP | T1_THEN_BUFFER_STOP | False |
| 2026-07-02 | ORB@09:20 TARGET | BUY |  | ORB V2 VALID (signal at 09:20) | False | TARGET | TARGET | False |
| 2026-07-06 | IRF@10:15 INITIAL_FULL_STOP | none | NO_PATTERN | PROVISIONAL_PATTERN_CONVENTION | False | TARGET | INITIAL_FULL_STOP | True |
| 2026-07-10 | IRF@10:05 T1_THEN_BUFFER_STOP | none | NO_PATTERN;WRONG_SIDE_WICK | PROVISIONAL_PATTERN_CONVENTION; SOURCE_SUPPORTED_RULE (wrong-side wick <= 20%) | False | TARGET | T1_THEN_BUFFER_STOP | False |
| 2026-07-15 | ORB@09:20 TARGET | BUY |  | ORB V2 VALID (signal at 09:20) | False | TARGET | TARGET | False |
| 2026-07-16 | no trade | none | NO_PATTERN;WRONG_SIDE_WICK | PROVISIONAL_PATTERN_CONVENTION; SOURCE_SUPPORTED_RULE (wrong-side wick <= 20%) | False | INITIAL_FULL_STOP |  | False |
| 2026-07-17 | IRF@10:05 INITIAL_FULL_STOP | none | NO_PATTERN | PROVISIONAL_PATTERN_CONVENTION | False | TARGET | INITIAL_FULL_STOP | True |
| 2026-07-29 | IRF@10:00 INITIAL_FULL_STOP | none | NO_PATTERN | PROVISIONAL_PATTERN_CONVENTION | False | TARGET | INITIAL_FULL_STOP | True |
| 2026-07-30 | ORB@09:20 INITIAL_FULL_STOP | BUY |  | ORB V2 VALID (signal at 09:20) | False | INITIAL_FULL_STOP | T1_THEN_BUFFER_STOP | False |
| 2026-08-10 | no trade | none | NO_PATTERN | PROVISIONAL_PATTERN_CONVENTION | False | INITIAL_FULL_STOP |  | False |
| 2026-08-28 | IRF@09:35 INITIAL_FULL_STOP | none | NO_PATTERN | PROVISIONAL_PATTERN_CONVENTION | True | INITIAL_FULL_STOP | INITIAL_FULL_STOP | False |


Files: `orb_vs_irf_disputed_days.csv`, `charts_orb_vs_irf/` (per date one chart per candidate: `_executed` or `_counterfactual`).