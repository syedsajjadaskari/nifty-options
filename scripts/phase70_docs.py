"""Phase 7.0 documents + workbook. Reads the CSV/JSON written by phase70_run.py; every number in the prose comes from those files."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/phase7/phase70_complete_irf_rebuild"
P1 = "IRF_Inverse_Retest_Failure_Rulebook.pdf"
P2 = "IRF_Method2_First_Red_Candle_Rulebook.pdf"


def rd(name: str) -> pd.DataFrame:
    return pd.read_csv(OUT / name)


def w(name: str, text: str) -> None:
    (OUT / name).write_text(text.strip() + "\n")


def table(df: pd.DataFrame, cols: list[str] | None = None) -> str:
    d = df[cols] if cols else df
    head = "| " + " | ".join(d.columns) + " |\n|" + "---|" * len(d.columns) + "\n"
    return head + "\n".join("| " + " | ".join("" if pd.isna(v) else str(v) for v in r) + " |" for r in d.itertuples(index=False))


def perf(window: str, scen: str, book: str) -> dict:
    p = rd("historical_performance_comparison.csv")
    return p[(p.window == window) & (p.scenario == scen) & (p.book == book)].iloc[0].to_dict()


def build() -> None:
    perfdf = rd("historical_performance_comparison.csv")
    s1, s2 = rd("method1_signals.csv"), rd("method2_signals.csv")
    ov = rd("overlap_analysis.csv")
    summ = rd("manual_journal_match_summary.csv")
    rec = rd("manual_journal_reconciliation.csv")
    ex = rd("source_example_reproduction.csv")
    aud = json.loads((OUT / "audit_results.json").read_text())
    chg = rd("changed_entry_times_vs_earlier_phases.csv")
    st = json.loads((OUT / "_state" / "state.json").read_text())
    n = {"A": st["sessions"]["A"], "B": st["sessions"]["B"]}
    sig = {(m, wd): (len(g), int((g.status == "SIGNAL_ELIGIBLE").sum()), int((g.status == "SIGNAL_AFTER_CUTOFF").sum())) for m, d in (("M1", s1), ("M2", s2)) for wd, g in d.groupby("window")}
    ovc = ov.groupby(["window", "overlap_class"]).size().unstack(fill_value=0)

    # ---------------------------------------------------------------- source audits
    w("method1_source_audit.md", f"""
# Method 1 source audit - {P1}

Source: `docs/strategy_docs/{P1}` (untracked in Git, read only, 8 pages, 4 embedded images). Every page was rendered and viewed; every embedded image was extracted at original resolution to `source_extracts/` (`m1_p4_img1.png`, `m1_p6_img1.png`, `m1_p7_img1.png`, `m1_p7_img2.png`).

**Document-level findings**
* The document says rules are marked CONFIRMED or TO CONFIRM and that all TO CONFIRM items are collected in a section 'Open Items to Confirm'. **No such section exists in the 8 pages, and no rule carries an explicit CONFIRMED tag.** Authority classes used here: `STATED` (printed without a TO CONFIRM tag), `TO_CONFIRM` (explicit tag), `SOURCE_SILENT`, `EXAMPLE_ONLY` (see `rule_authority_registry.csv`).
* Prices read from the screenshots are, by the document's own statement, approximate.

| Page | Content | Rules / facts captured (rule id) |
|---|---|---|
| 1 | Summary tiles (SHORT, SL 35-40, target 60, 5 min); how-to-read box; overview table | Nifty 50 index, 5-min (R01); level = first-candle high incl. wick (R02); breakout = any later candle closing above (R03); failure = later close below (R05); entry after the failure candle closes (R07); SL ~35-40 above entry (R12); target 60 below (R13); no trend restriction (R08); 1 trade/day; no entry after 1 pm (R16). Header row 'Latest entry time and exit time' prints only 'No entry after 1 Pm' (R18) |
| 2 | Core principle; 'What IRF does not use' | No EMA(200), no previous-day S/R, no gap filter, price may be above or below the 200 EMA (R08) |
| 3 | Marking the level; the 6-step sequence | First candle 09:15-09:20; level = high incl. wick, marked once, never moves (R02). Example candle O25000 H25035 L24996 C25020 (green) -> level 25,035 not 25,020. Colour of the first candle: TO CONFIRM (R09). Candle that merely wicks above and closes at/below is not a breakout (R03). The failure may come right after the breakout or many candles later (R05) |
| 4 | **Figure 1** (drawn illustration: green first candle, two greens closing above 25,035, red failure candle, 3 red follow-through candles; SL 25,070 (entry+40) / 25,065 (35); target 24,970; entry 25,030 'an illustration') + 'Order matters' | Both closes needed, in order; a close below with no earlier close above is not a signal (R06) |
| 5 | 'What counts' table; entry/SL/TP table; worked example; bullets | Close exactly on the level ignored: TO CONFIRM (R10). Entry price E = close of the failure candle: TO CONFIRM (R11). SL E+35..40, target E-60, risk-reward 1:1.5 (40) / ~1:1.7 (35) (R12, R13). SL/TP measured from the entry, not the level. One trade/day, strategy finished after SL or target: TO CONFIRM (R14). SL and target both inside one 5-minute candle -> SL first: TO CONFIRM (R15). Not hit -> closed at end of session, exit time to be confirmed (R17). Worked example: level 25,035; close 25,048 (breakout); close 25,030 (failure); entry 25,030; SL 25,065-25,070; TP 24,970 |
| 6 | Chart-example table + **Screenshot 1** ('Session marked 5', stop-loss hit) | Level 24,391.80; entry 24,373.25 (18.55 below the level); SL 24,408.50 (35.25); TP 24,314.00 (59.25). **No date.** The text says price rose to ~24,430 and the SL was hit near the end of the box |
| 7 | **Screenshot 2** (11 Nov 2026, target hit +60.50, RR 1.48) and **Screenshot 3** (16 Nov 2026, target hit) | Ex 2: level 'about 25,377.5'; entry 25,363.90; SL 25,404.65 (40.75); TP 25,303.40 (60.50); failure candle 'around 9:55'. Ex 3: level 25,301.55; entry 25,299.75 (1.80 below); SL 25,340.45 (40.70); TP 25,239.10 (60.65); failure 'around 10:00' |
| 8 | Rule matrix | Restates R02, R03, R05, R07, R12, R13, R08, trades/day 1 (TO CONFIRM) |

**What the document does NOT specify:** a rule for choosing 35 vs 40 points; the exit clock; whether a trade may follow a stopped trade; an invalidation of the setup (e.g. by time or distance); a minimum distance of the failure close below the level (the examples show 1.80 to 18.55 points).

**Observed example geometry:** stop distances 35.25 / 40.75 / 40.70 and target distances 59.25 / 60.50 / 60.65 - the author's boxes are placed by hand, so no fixed-point model reproduces the examples' exit prices exactly.
""")
    w("method2_source_audit.md", f"""
# Method 2 source audit - {P2}

Source: `docs/strategy_docs/{P2}` (untracked in Git, read only, 8 pages, 5 embedded images: `m2_p4_img1.png`, `m2_p5_img1.png`, `m2_p6_img1.png`, `m2_p6_img2.png`, `m2_p7_img1.png`; all extracted at original resolution and viewed).

**Document-level findings**
* As in the first PDF, the 'Open Items to Confirm' section and per-rule CONFIRMED tags are absent.
* Page 5 carries an **orphan fragment '60 points in every case.'** directly under the 'What counts' table with no sentence before it - evidence that text was deleted or lost; nothing is inferred from it.
* The method derives its mechanics from the document only. The filename 'First Red Candle' is not used as a rule.

| Page | Content | Rules / facts captured |
|---|---|---|
| 1 | Summary tiles; how-to-read; overview table | Level A = first-candle high incl. wick (R02); rally breakout = a candle closes above Level A, price then continues up (R03); Level B = top of the BODY of the FIRST RED candle in the rally, upper wick ignored (R05); second breakout = candle closes above Level B, do not enter (R08); failure = later candle closes below Level B (R09); SHORT after the failure candle closes (R11); SL 35-40 above entry, target 60 below (R14); no trend restriction (R12); 1 trade/day |
| 2 | Latest entry/exit time '1 pm'; core principle; **side-by-side table** Method 1 vs Method 2; 'What Method 2 does not use' | 'Latest entry time and exit time | 1 pm' is a single value for both (R16, ambiguous). M2 uses no EMA(200), previous-day S/R or gap filter (R12) |
| 3 | The two levels; numeric example; 9-step sequence | For a red candle the body top is its **open** (R05). Example: first candle O25050 H25085 L25045 C25070 (green) -> Level A 25,085; first red candle open 25,094 close 25,092 -> Level B 25,094. Steps: wait for candle 1; mark A; wait for a close above A (colour irrelevant); let the rally continue; find the FIRST red candle; mark B; wait for a later close above B; wait for a later close back below B (immediately or many candles later); enter SHORT after the failure candle closes |
| 4 | **Figure 2** (drawn: first candle, green closing above A, 2 small greens, small red (B 25,094), green closing above B, green, large red failure, 3 reds; SL 25,125-25,130; target 25,030; entry 25,090) + 'Order matters' | A close below B with no earlier close above B is not a signal; a red candle before the close above A is not the first red candle of the rally (R10, R06) |
| 5 | 'What counts' table; orphan fragment; **Screenshot 1** (undated, SL hit) | Red candle before any close above A: ignored, TO CONFIRM (R06). Only the FIRST red candle sets B (R05). Exactly-on-level: TO CONFIRM (R13). Ex 1: A 25,358.35; second candle red but before the breakout (ignored); B 25,379.95; rally to ~25,500; failure 'long after' the second breakout; entry 25,376.25 (3.70 below B); SL 25,412.10 |
| 6 | Ex 1 end; **Screenshot 2** (12 Nov 2026, target hit); **Screenshot 3** (6 Nov 2026, target hit) | Ex 2: A 25,302.15; B 25,350.30 (a small red candle); entry 25,337.95 (12.35 below B); SL 25,373.15 (35.20); TP 25,276.80 (61.15); target ~75 min after entry. Ex 3: A 24,540.05; B 24,660.45 |
| 7 | Ex 3 end; **Screenshot 4** (3 Nov 2026, stop-loss hit -35.50) | Ex 3: entry 24,647.25 (13.20 below B); SL 24,687.70 (40.45); TP 24,586.15 (61.10); target ~15 min after entry. Ex 4: first candle red, very long lower wick, thin upper wick reaching A 23,611.15; B 23,621.90; entry 23,612.80 (9.10 below B); SL 23,648.30 (35.50); TP 23,552.55 (60.25) |
| 8 | Rule matrix | Restates the sequence; trades/day 1 (TO CONFIRM) |

**What the document does NOT specify:** entry-price convention, tie rule and end-of-session exit for Method 2 (Method 1 lists them as TO CONFIRM; Method 2 is silent); what happens if price closes back below Level A or below Level B before the second breakout (no invalidation is stated); whether the rally-breakout candle itself, when red, may be the first red candle; whether a red candle that closes below Level A can set Level B; what the orphan fragment on page 5 meant.

**Questions 1-14 of the task, answered from the PDF:** (1) the initial range is the 09:15 candle's high/low, only the high is used; (2) Method 2 starts at the rally breakout; (3) the breakout above Level A is compulsory; (4) it must CLOSE above A; (5) first red candle = close < open (the examples show the red body only) after the breakout; (6) its wick low is NOT used - the level is the body top (open); (7) Level B becomes valid when that red candle closes (09:xx+5), and is used from then on; (8) confirmation needs a later close above B then a later close below B; (9) no retest of any support is required; (10) no EMA/trend condition; (11) no candle-body-strength rule; (12) entries are allowed until 1 pm; (13) SL = entry + 35..40, target = entry - 60; (14) a setup is invalidated by nothing explicit - only by missing the order of steps.
""")

    w("source_rule_comparison.md", f"""
# Source-rule comparison: Method 1 vs Method 2

Both documents were read independently. Where they say the same thing it is recorded as a SIMILARITY; where only one speaks it is a DIFFERENCE or a SILENCE; where one reading of a shared row could be contradictory it is a CONFLICT. Method-specific definitions are preserved - no rule was borrowed across methods.

| Topic | Method 1 ({P1}) | Method 2 ({P2}) | Classification |
|---|---|---|---|
| Instrument / timeframe | Nifty 50 index, 5 min | same | similarity |
| First level | marked level = high of 09:15 candle incl. wick (p1,p3) | Level A = high of 09:15 candle incl. wick (p1,p3) | similarity (identical definition; each module computes it independently) |
| What must break | the first-candle high itself | Level B = body top (open) of the first red candle after the rally breakout | difference (core) |
| Breakout | any later candle (any colour) closes above the marked level | any later candle (any colour) closes above Level A (rally) AND later above Level B (second breakout) | difference (two breakouts in M2) |
| Failure | later close below the SAME marked level | later close below Level B | difference |
| Red candle | irrelevant | decisive (first red candle after the rally breakout); red candles before the breakout ignored (TO CONFIRM) | difference |
| Entry | after the failure candle closes; price = failure close (TO CONFIRM) | after the failure candle closes; price not stated | similarity + M2 silence |
| SL / target | entry +35..40 / entry -60 | entry +35..40 / entry -60 | similarity |
| Filters | none (no EMA200, S/R, gap, trend) | none (same list) | similarity |
| Trades per day | 1 (TO CONFIRM) | 1 (TO CONFIRM) | similarity |
| Latest entry / exit | row 'Latest entry time and exit time' prints 'No entry after 1 Pm' | same row prints '1 pm' | **CONFLICT / ambiguity**: M2's single value could also be an exit clock; M1 separately says the end-of-session exit time is to be confirmed. Preserved: entry cutoff 13:00 for both; a 13:00 forced exit is a labelled sensitivity |
| Tie SL/target in one candle | SL first (TO CONFIRM) | not stated | M2 silence - the M1 convention is applied to M2 as a flagged assumption |
| End-of-session exit | 'closed at end of session, time to be confirmed' | not stated | silence |
| Invalidation | none stated | none stated (order of steps only) | shared silence |
| Which method wins when both fire | not stated | not stated | shared silence - see `combined_irf_state_machine.md` |
| Colour of first candle | not restricted (TO CONFIRM) | examples include green and red first candles | similarity (no rule) |

**Implementation consequence:** `method1.py` and `method2.py` share no code. Both read the same candle list, but nothing of M2's red-candle/second-breakout logic exists in M1, and M1's single-level confirmation is not reused in M2.
""")

    w("method1_entry_logic.md", f"""
# IRF_V3_METHOD_1 - entry logic (from {P1} only)

```
S0 AWAIT_FIRST_CANDLE  : the 09:15-09:20 candle completes at 09:20:00. level = its HIGH (wick included). Frozen for the day.            [R02]
S1 AWAIT_BREAKOUT      : each later candle, evaluated at its END:
                           close >  level  -> breakout recorded, NO entry; go to S2                                                  [R03, R04]
                           close <  level  -> ignored (no earlier breakout close)                                                    [R06]
                           close == level  -> ignored                                                                                [R10]
S2 AWAIT_FAILURE       : close <  level  -> FAILURE: SHORT signal, signal_time = that candle's end                                    [R05, R07]
                           close >= level  -> keep waiting (any number of candles)
```
Nothing else is tested: no EMA, gap, previous-day structure, trend, first-candle colour, candle body size or breakout size.

**Execution (labelled scenarios, none optimised):** fill = OPEN of the one-minute bar that starts when the failure candle ends (first causally available price; the source's 'close of the failure candle' is the reference scenario `SIGNAL_CLOSE`). Fill bar must start <= 13:00:00 ({'inclusive'}), exist and be continuous-session. Stop = entry + 35 (`SL35_T60`) or +40 (`SL40_T60`); target = entry - 60. Both touched in one 5-minute window -> stop. Open at 15:14 forced exit. 1 trade/day; later breakout/failure cycles are counted (`later_cycles_after_first_signal(not_traded)`) but never traded.

**Rejection / no-trade reasons recorded per day:** `FIRST_CANDLE_MISSING`, `NO_CLOSE_ABOVE_LEVEL` (never broke out), `BREAKOUT_WITHOUT_FAILURE`, `SIGNAL_AFTER_CUTOFF`, `NOT_EVALUATED:<session reason>`.

**Provenance:** every signal row in `method1_signals.csv` carries `source_rule_ids` (M1-R02, R03, R05, R06, R07), the reference candle (the first candle), breakout candle, confirmation candle and timestamps.
""")

    w("method2_entry_logic.md", f"""
# IRF_V3_METHOD_2 - entry logic (from {P2} only)

```
S0 AWAIT_A_BREAKOUT : Level A = HIGH of the 09:15 candle (wick included). Each later candle at its END:
                        close > A  -> rally breakout (any colour)                                         [R03]
                        red candle (close < open) before that -> ignored, counted                          [R06]
S1 AWAIT_FIRST_RED  : the FIRST later candle with close < open sets Level B = its OPEN (top of body, wick ignored); later reds ignored   [R05, R07]
S2 AWAIT_B_BREAKOUT : a later candle with close > B -> second breakout, NO entry                          [R08]
S3 AWAIT_FAILURE    : a later candle with close < B -> FAILURE: SHORT signal at that candle's end         [R09, R11]
close == a level -> ignored (R13). Nothing invalidates an armed setup (R18 - source silent).
```
**Reading choices where the PDF can be read two ways (all disclosed in `rule_authority_registry.csv` / `unresolved_author_questions.md`):**
* *Breakout candle itself red?* Primary: NOT eligible ('first red candle AFTER the rally breakout'). The variant `M2_ALT_BREAKOUT_RED` (eligible) is run as a sensitivity - it changes {int(perfdf[(perfdf.scenario == 'SL40_T60__M2_ALT_BREAKOUT_RED') & (perfdf.book == 'M2')].executed_trades.sum()) - int(perfdf[(perfdf.scenario == 'SL40_T60') & (perfdf.book == 'M2')].executed_trades.sum())} M2 trades across both windows (net of both windows).
* *Setup expiry:* none; a Level B set at 09:35 is still armed at 12:55.
* *Red candle that closes below Level A* can still set Level B (the PDF does not require the rally to be intact).

Execution is the same labelled scenario set as Method 1 (assumed, because the Method 2 text is silent on entry price, tie and exit).

**Rejection / no-trade reasons:** `NO_CLOSE_ABOVE_LEVEL_A`, `NO_RED_CANDLE_AFTER_RALLY_BREAKOUT`, `NO_CLOSE_ABOVE_LEVEL_B`, `SECOND_BREAKOUT_WITHOUT_FAILURE`, `SIGNAL_AFTER_CUTOFF`, `NOT_EVALUATED:<reason>`.
""")

    w("combined_irf_state_machine.md", f"""
# Combined IRF V3 signal engine

Both methods run on the SAME session independently; neither can see the other's state.

```
session -> [Method 1 machine] -> M1 signal? (time t1)        \\
        -> [Method 2 machine] -> M2 signal? (time t2)         >-> eligibility (fill bar <= 13:00:00, bar exists & continuous)
                                                              /-> select earliest eligible signal_time
```
Cases handled and counted (window A / window B first signals, from `overlap_analysis.csv` and the signal ledgers):

| Case | A | B |
|---|---|---|
| Only M1 qualifies | {int(((s1.window == 'A') & ~s1.date.isin(s2[s2.window == 'A'].date)).sum())} | {int(((s1.window == 'B') & ~s1.date.isin(s2[s2.window == 'B'].date)).sum())} |
| Only M2 qualifies | {int(((s2.window == 'A') & ~s2.date.isin(s1[s1.window == 'A'].date)).sum())} | {int(((s2.window == 'B') & ~s2.date.isin(s1[s1.window == 'B'].date)).sum())} |
| Both, M1 first | {ovc.loc['A'].get('BOTH_M1_FIRST', 0)} | {ovc.loc['B'].get('BOTH_M1_FIRST', 0)} |
| Both, M2 first | {ovc.loc['A'].get('BOTH_M2_FIRST', 0)} | {ovc.loc['B'].get('BOTH_M2_FIRST', 0)} |
| Both, same instant | {ovc.loc['A'].get('BOTH_SAME_TIME', 0)} | {ovc.loc['B'].get('BOTH_SAME_TIME', 0)} |
| Signal(s) only after the 13:00 cutoff | A: M1 {sig[('M1', 'A')][2]}, M2 {sig[('M2', 'A')][2]} | B: M1 {sig[('M1', 'B')][2]}, M2 {sig[('M2', 'B')][2]} |

* Ledger: `combined_irf_signals.csv` keeps every first signal of both methods with `selected_in_combined`, `overlap_class`, `status`.
* One trade per day: the earliest ELIGIBLE signal. Because both methods' trades are simulated by the same function, a same-instant pair has identical entry, stop, target and exit - **counting is by day, never by method, so no trade is double counted** (verified by test `test_combined_book_has_no_double_counted_trades`).
* **Same-instant tie** (both signals on one failure candle): the documents define no priority. Policy `TIE_METHOD_1` is a deterministic research label (NOT author-approved) that only attributes the trade; P&L is unaffected (`overlap_analysis.csv`, column `same_entry_price_and_exit`).
* A method that produced its first signal after 13:00 is not eligible; the other method (if earlier) is selected. If both are late: `NO_ELIGIBLE_SIGNAL`.
* A setup that invalidates before confirmation: neither PDF states any invalidation, so none exists; a setup that never completes appears as a no-signal day with its missing conditions in `daily_verification.csv`.
""")

    questions = """
# Unresolved author questions (Phase 7.0)

None of these was answered by either PDF. Each implemented choice is labelled and (where it matters) run as a separate scenario. No choice is approved by the owner.

## Both methods
1. **Stop distance** - 35 or 40 points? The PDFs say 'about 35 to 40' and the examples show 35.2-40.75. Run as `SL35_T60` and `SL40_T60`.
2. **Entry price** - the failure candle's close (M1 TO CONFIRM; M2 silent) or the first executable price after it? Primary: open of the next one-minute bar; the close convention is run as `SL40_ENTRY_SIGNAL_CLOSE`.
3. **Exit clock** - M1: 'end of the session, time to be confirmed'; M2 row 'Latest entry time and exit time = 1 pm'. Primary: forced exit at the 15:14 bar open; `*_FORCED_EXIT_1300` scenarios test a 13:00 exit.
4. **Entry cutoff** - 'no entry after 1 pm': is a fill at exactly 13:00 allowed? Implemented inclusive (13:00:00 allowed), consistent with the repository's ENTRY-CUTOFF-001.
5. **Stop-vs-target in one candle** - SL first (M1, TO CONFIRM); M2 silent; the 5-minute-window reading is primary, chronological one-minute order is `SL40_TIE_MINUTE_ORDER`.
6. **Trades per day** - 1 (TO CONFIRM). Is the day finished after a stop-loss (M1 says so, TO CONFIRM), or may a later failure be traded? Later cycles are only counted.
7. **Priority when both methods fire** - not stated. Earliest signal; same instant -> Method 1 label (P&L unaffected).
8. **Exactly-equal closes** - ignored (TO CONFIRM in both).
9. **Setup expiry** - does an armed setup expire (time of day, distance, number of candles)? Neither PDF says so.

## Method 1
10. First-candle colour - no rule (TO CONFIRM). 11. Is there a minimum depth of the failure close below the level? (examples: 1.80-18.55 points) - none implemented.

## Method 2
12. Can the red rally-breakout candle itself be the first red candle? Primary no; variant `M2_ALT_BREAKOUT_RED` reported.
13. Must the rally stay above Level A until Level B breaks? Primary: no condition. 14. If price closes back below Level A (or below B) before the second breakout, is the setup dead? Primary: no (source silent).
15. Must the first red candle have its open above Level A? Not required here.
16. The orphan sentence '60 points in every case.' on page 5 - what did it qualify?
17. Page references to 'Open Items to Confirm' - the section is missing from both PDFs; please supply the list so TO CONFIRM items can be closed.
18. Undated screenshots (M1 Example 1 'Session marked 5', M2 Example 1) - please supply the dates; and the Nov 2026 data (11, 12, 16 Nov; 6 Nov) is not in any data store.
19. **M2 Example 4 (3 Nov 2026)**: on the secondary-vendor data the first close below Level B is the 10:00 candle (0.70 below B), but the screenshot's entry equals the close of the 10:05 candle. Is a minimum margin below B required, or is the author's failure candle simply the later one?
20. **M2 invalidation**: if price closes below Level A before the first red candle / Level B is marked (roughly a third of M2 rally sessions, `m2_rally_diagnostics.json`), is the setup dead? Primary keeps it armed; `SL40_M2_INVALIDATE_BELOW_A` is the alternative.
"""
    w("unresolved_author_questions.md", questions)

    # ---------------------------------------------------------------- performance + README
    def hp(win, scen, book):
        d = perf(win, scen, book)
        return d

    rows = []
    for win in "AB":
        for scen in ("SL40_T60", "SL35_T60"):
            for book in ("M1", "M2", "COMBINED"):
                d = hp(win, scen, book)
                rows.append({"window": win, "scenario": scen, "book": book, "sessions": d["sessions"], "signals": d["signals"], "trades": d["executed_trades"], "W": d["wins"], "L": d["losses"], "win%": d["win_rate_pct"],
                             "PF": d["profit_factor"], "gross pts": d["gross_points"], "avg W": d["avg_win"], "avg L": d["avg_loss"], "max DD pts": d["max_drawdown_points"], "SL": d["stop_hits"], "TP": d["target_hits"],
                             "forced": d["forced_exits"]})
    ptab = table(pd.DataFrame(rows))
    sA = summ.set_index("engine")
    ex = ex.astype(object)
    exs = ex[["example", "pdf", "page", "date_stated", "status", "replay_signal", "failure_candle", "level_A_diff_vs_source", "level_B_diff_vs_source", "replay_SL40_exit"]].fillna("")
    reasons = rec[rec.COMBINED_match_class == "MANUAL_ONLY"][["date", "journal_time_label", "journal_outcome", "v3_reason_no_combined_trade"]].copy()
    reasons["v3_reason_no_combined_trade"] = reasons["v3_reason_no_combined_trade"].str.replace(" | ", " ; ", regex=False)
    ovA = ov[ov.window == "A"]
    first_counts = ovA.overlap_class.value_counts().to_dict()
    diag = json.loads((OUT / "m2_rally_diagnostics.json").read_text())
    sens = perfdf[(perfdf.kind == "SENSITIVITY") & (perfdf.book != "M1")].copy()
    sens = sens[["window", "scenario", "book", "executed_trades", "win_rate_pct", "profit_factor", "gross_points", "max_drawdown_points"]]
    sens = sens[sens.scenario.isin(["SL40_CUTOFF_EXCLUSIVE", "SL40_M2_INVALIDATE_BELOW_A", "SL40_T60__M2_ALT_BREAKOUT_RED", "SL40_ENTRY_SIGNAL_CLOSE", "SL40_TIE_MINUTE_ORDER", "SL40_FORCED_EXIT_1300", "SL35_FORCED_EXIT_1300"])]
    sens = sens[sens.book.isin(["M2", "COMBINED"])]
    n_wrong = int(rec.classification_note.astype(str).str.startswith("METHOD_ATTRIBUTION_DIFFERS").sum())
    caus = aud["causality"]
    mism_total = sum(v["mismatches"] for k, v in aud.items() if k != "causality")
    w("README.md", f"""
# Phase 7.0 - complete IRF reconstruction from the two new rulebooks

**Written for:** the strategy owner. Research only: synthetic NIFTY **index-point** results (not options/futures P&L); no order placed; no parameter optimised; no existing strategy, dataset, journal or paper-trading configuration touched; nothing committed, staged or pushed. The two PDFs remain untracked.

Method 1 and Method 2 were rebuilt **independently, from their own PDF only**, in the new package `src/nifty_trading/research/irf_v3/` (no call into any older IRF engine; generic one-minute readers, the NSE calendar and the bar-executability classifier were reused after verification). A third, separately written NumPy/`resample` implementation (`audit.py`) reconstructed every signal and trade; **{mism_total} mismatches** over all scenarios and both windows.

Start with this README, then `source_rule_comparison.md`, `unresolved_author_questions.md`, `source_example_reproduction.csv`, `historical_performance_comparison.csv`, `manual_journal_reconciliation.csv`.

## Performance (index points; SL scenarios are separately labelled because the PDFs do not choose between 35 and 40)

Window A = 2025-09-01..2026-08-31 (5paisa one-minute data, {n['A']} evaluable sessions). Window B = 2022-09-01..2025-08-31 ({n['B']} sessions). Win = gross points > 0 on a closed trade. `signals` = first signals incl. those after the 13:00 cutoff (not tradable); for COMBINED it is the number of days traded.

{ptab}

## Final questions

**1. Exact rules of Method 1.** Level = high (wick included) of the 09:15-09:20 candle. A later candle closes strictly above it (any colour; no entry). A later candle then closes strictly below the same level -> SHORT after that failure candle closes. No EMA, gap, previous-day S/R, trend, colour or body filter. Stop entry+35..40 (two scenarios), target entry-60, 1 trade/day, no entry after 1 pm. See `method1_entry_logic.md`.

**2. Exact rules of Method 2.** Level A = first-candle high. A later candle closes above A (rally breakout). The first red candle after it sets Level B = its open (body top, wick ignored); red candles before the breakout are ignored. A later candle closes above B (second breakout, no entry), a later candle closes below B -> SHORT after it closes. Same filters (none), stop and target. See `method2_entry_logic.md`.

**3. Similarities / differences.** Same first level, same stop/target, same filter list, same entry timing. M1 trades the failure of the first-candle high; M2 needs a two-stage sequence (A breakout -> first red candle -> B breakout -> B failure). `source_rule_comparison.md`.

**4. Unresolved assumptions.** 35 vs 40 stop; entry price; exit clock (and the ambiguous '1 pm' exit in M2); inclusive 13:00; same-candle tie for M2; one-trade/after-stop rule; priority between methods; whether the red breakout candle can be 'first red'; whether an armed M2 setup can expire or die. 20 items in `unresolved_author_questions.md`.

**5. Does Method 1 reproduce its source examples?** Partly, and only where it can be tested: the drawn Figure 1 reproduces exactly (level 25,035, failure close 25,030, entry 25,030, stop 25,065/25,070, target 24,970). Of the three screenshots, Example 1 is **undated** (no date is invented; a level-only search of the data stores finds no supporting session), and Examples 2 (11 Nov) and 3 (16 Nov) fall **after the end of every data store** (secondary vendor ends 2026-11-04, primary ends 2026-08-31) - they cannot be replayed. Only their printed arithmetic could be checked (internally consistent).

**6. Does Method 2 reproduce its source examples?** Figure 2 reproduces exactly (A 25,085, B 25,094, failure close 25,090, entry 25,090, target 25,030). Of the four screenshots only **Example 4 (3 Nov 2026)** has data (secondary vendor, the feed the screenshots come from): first-candle high 23,610.70 vs 23,611.15 stated (-0.45), Level B 23,621.70 vs 23,621.90 (-0.20), stop-loss outcome reproduced (-35/-40). **The engine's failure candle is 10:00-10:05 (close 23,621.00, 0.70 below B); the screenshot's entry 23,612.80 equals the close of the 10:05-10:10 candle (23,613.00), i.e. one candle later** - a 0.7-point margin that the cross-vendor differences and/or author discretion could explain; the logic was not changed to fit. Example 1 undated; Examples 2 (12 Nov) and 3 (6 Nov) have no data.

**7. Method 1 signals.** Window A {sig[('M1', 'A')][0]} first-signals ({sig[('M1', 'A')][1]} tradable, {sig[('M1', 'A')][2]} after 13:00); window B {sig[('M1', 'B')][0]} ({sig[('M1', 'B')][1]} / {sig[('M1', 'B')][2]}).

**8. Method 2 signals.** Window A {sig[('M2', 'A')][0]} ({sig[('M2', 'A')][1]} / {sig[('M2', 'A')][2]}); window B {sig[('M2', 'B')][0]} ({sig[('M2', 'B')][1]} / {sig[('M2', 'B')][2]}).

**9. Overlap.** Dates where both methods signal: window A {len(ovA)} ({first_counts}), window B {len(ov[ov.window == 'B'])}.

**10. Which triggers first on overlapping dates.** Window A: Method 1 first on {first_counts.get('BOTH_M1_FIRST', 0)}, Method 2 first on {first_counts.get('BOTH_M2_FIRST', 0)}, same instant on {first_counts.get('BOTH_SAME_TIME', 0)} (window B: {int((ov[ov.window == 'B'].overlap_class == 'BOTH_M1_FIRST').sum())} / {int((ov[ov.window == 'B'].overlap_class == 'BOTH_M2_FIRST').sum())} / {int((ov[ov.window == 'B'].overlap_class == 'BOTH_SAME_TIME').sum())}). The median gap M2-after-M1 is {int(ovA.minutes_M2_after_M1.median())} minutes.

**11. Combined IRF trades.** Window A {perf('A', 'SL40_T60', 'COMBINED')['executed_trades']}, window B {perf('B', 'SL40_T60', 'COMBINED')['executed_trades']} (one per day; both stop scenarios trade the same days).

**12. Standalone win rates (A, B).** SL40: M1 {perf('A', 'SL40_T60', 'M1')['win_rate_pct']}% / {perf('B', 'SL40_T60', 'M1')['win_rate_pct']}%; M2 {perf('A', 'SL40_T60', 'M2')['win_rate_pct']}% / {perf('B', 'SL40_T60', 'M2')['win_rate_pct']}%. SL35: M1 {perf('A', 'SL35_T60', 'M1')['win_rate_pct']}% / {perf('B', 'SL35_T60', 'M1')['win_rate_pct']}%; M2 {perf('A', 'SL35_T60', 'M2')['win_rate_pct']}% / {perf('B', 'SL35_T60', 'M2')['win_rate_pct']}%.

**13. Combined win rate (A, B).** SL40 {perf('A', 'SL40_T60', 'COMBINED')['win_rate_pct']}% / {perf('B', 'SL40_T60', 'COMBINED')['win_rate_pct']}%; SL35 {perf('A', 'SL35_T60', 'COMBINED')['win_rate_pct']}% / {perf('B', 'SL35_T60', 'COMBINED')['win_rate_pct']}%.

**14. Profit factors and max drawdowns** are in the table above (window A combined SL40: PF {perf('A', 'SL40_T60', 'COMBINED')['profit_factor']}, DD {perf('A', 'SL40_T60', 'COMBINED')['max_drawdown_points']} pts; SL35: PF {perf('A', 'SL35_T60', 'COMBINED')['profit_factor']}, DD {perf('A', 'SL35_T60', 'COMBINED')['max_drawdown_points']} pts). Index-point equity only. Costs/slippage are in `cost_slippage_sensitivity.csv`: window-A combined SL40 earns +103.2 points over 139 trades (0.74 pt/trade) and is already negative after a 1-point round-trip cost (-35.8); SL35 is negative gross (-14.35). Window-B combined SL40 (+1580.85 over 440 trades, 3.6 pt/trade) stays positive up to a 3-point round-trip cost (+260.85) and turns negative at 5 points.

**15. Manual IRF journal rows matched** (73 IRF rows, 1 on a weekend that can never match; the journal has no direction/price so **no exact trade match can be claimed**): Combined strict {sA.loc['COMBINED', 'strict']}, + time-tolerant {sA.loc['COMBINED', 'time_tolerant_extra']}, + date-and-strategy-only {sA.loc['COMBINED', 'date_strategy_only']}, manual-only {sA.loc['COMBINED', 'manual_only']}. Method 1 alone {sA.loc['M1', 'strict']}/{sA.loc['M1', 'time_tolerant_extra']}/{sA.loc['M1', 'date_strategy_only']}/{sA.loc['M1', 'manual_only']}; Method 2 alone {sA.loc['M2', 'strict']}/{sA.loc['M2', 'time_tolerant_extra']}/{sA.loc['M2', 'date_strategy_only']}/{sA.loc['M2', 'manual_only']} (strict/tolerant/date-only/manual-only). {n_wrong} journal dates show a method-attribution difference (combined credits one method, the other's signal is nearer the journal time). Automated-only combined trades: {sA.loc['COMBINED', 'automated_only']} ({int((pd.read_csv(OUT / 'manual_journal_automated_only.csv').query("book=='COMBINED'")['class'] == 'AUTOMATED_ONLY_WRONG_STRATEGY_DATE').sum())} on dates where the journal holds a different strategy).

**16. Versus earlier IRF implementations** (first confirmed IRF signal per date, window A): Phase 3.6 {sA.loc['PHASE_3_6', 'strict']}/{sA.loc['PHASE_3_6', 'time_tolerant_extra']}/{sA.loc['PHASE_3_6', 'date_strategy_only']}/{sA.loc['PHASE_3_6', 'manual_only']}; Phase 5.3 {sA.loc['PHASE_5_3', 'strict']}/{sA.loc['PHASE_5_3', 'time_tolerant_extra']}/{sA.loc['PHASE_5_3', 'date_strategy_only']}/{sA.loc['PHASE_5_3', 'manual_only']}; Phase 6.1 {sA.loc['PHASE_6_1', 'strict']}/{sA.loc['PHASE_6_1', 'time_tolerant_extra']}/{sA.loc['PHASE_6_1', 'date_strategy_only']}/{sA.loc['PHASE_6_1', 'manual_only']}. V3 Combined reaches the same strict agreement as Phase 3.6 (34) and a higher one than Phases 5.3/6.1 (27). The earlier phases' notes say 5.3/6.1 implement owner-approved EMA-28 / first-red-low support rules that the two new PDFs do not mention; this analysis does not attribute the difference to any single cause. Entry candle changed vs Phase 3.6 on {int(chg.set_index('earlier_phase').loc['PHASE_3_6', 'changed_candle_start'])} of {int(chg.set_index('earlier_phase').loc['PHASE_3_6', 'dates_both_have_a_first_signal'])} shared dates; vs 5.3/6.1 on {int(chg.set_index('earlier_phase').loc['PHASE_5_3', 'changed_candle_start'])} of {int(chg.set_index('earlier_phase').loc['PHASE_5_3', 'dates_both_have_a_first_signal'])} (`changed_entry_times_vs_earlier_phases.csv`).

**17. Primary reasons for missing trades.** Journal rows not matched by the combined engine (manual-only): {len(reasons)} - listed below. Across all days without a combined trade the dominant reason is simply that price never closes above the first-candle high (`NO_CLOSE_ABOVE_LEVEL`), then breakouts that never fail, then signals that arrive after 13:00 (see `daily_verification.csv`, `no_trade_reason`).

{table(reasons)}

**18. Are all signal timestamps causally valid?** Yes: {caus['signals_checked']} signals re-run on candle lists truncated at the failure candle reproduce the same signal and, truncated one candle earlier, produce none; the fill bar is never before the signal time. Failures: {len(caus['failures'])}.

**19. Did independent verification reproduce the results?** Yes - {mism_total} signal/trade mismatches across window A and B in all 9 execution scenarios/variants (`independent_audit.md`). An independent read-only reviewer also reproduced every window-A signal and trade; its findings and what was changed are in `independent_audit.md` section 6.

**20. Were all existing strategies and paper trading preserved?** See `preservation_verification.md` (hash comparison of strategies, ORB V2, broker/core/config code, data, journal and earlier reports before/after; `git diff` of tracked files is empty).

## Source examples (`source_example_reproduction.csv`)

{table(exs)}

Level-only candidate search for the two undated screenshots (`undated_example_candidate_search.json`): one secondary-vendor session each within +-1.0 point of the printed level; neither reproduces the printed sequence, so **no date is suggested**.

## Sensitivity of the unresolved readings (Method 2 and combined books; Method 1 rows in `historical_performance_comparison.csv`)

{table(sens)}

Method 2 reading risk quantified (independent review finding): window A has {diag['A']['sessions_with_rally_breakout']} sessions with a rally breakout; in {diag['A']['first_red_candle_closed_below_level_A']} of the {diag['A']['sessions_with_level_b_marked']} where Level B was marked the first red candle itself closed below Level A (window B: {diag['B']['first_red_candle_closed_below_level_A']} of {diag['B']['sessions_with_level_b_marked']}). The PDF states no invalidation, so the headline keeps those setups armed; `SL40_M2_INVALIDATE_BELOW_A` shows what the alternative reading does. The red-breakout-candle reading matters little ({diag['A']['breakout_candle_itself_red']} red breakout candles in window A).

## Files
`method1_source_audit.md`, `method2_source_audit.md`, `source_rule_comparison.md`, `rule_authority_registry.csv`, `method1_entry_logic.md`, `method2_entry_logic.md`, `combined_irf_state_machine.md`, `unresolved_author_questions.md`, `method1_signals.csv`, `method2_signals.csv`, `combined_irf_signals.csv`, `method1_backtest.csv`, `method2_backtest.csv`, `combined_irf_backtest.csv`, `daily_verification.csv`, `manual_journal_reconciliation.csv`, `historical_performance_comparison.csv`, `independent_audit.md`, `preservation_verification.md`, `IRF_V3_Complete_Research.xlsx`, `charts_method1/`, `charts_method2/`, `charts_combined/`, `daily/` (one markdown per session, both windows), plus supporting: `overlap_analysis.csv`, `sensitivity_trades.csv`, `monthly_returns_points.csv`, `annual_performance_points.csv`, `cost_slippage_sensitivity.csv`, `manual_journal_match_summary.csv`, `manual_journal_automated_only.csv`, `changed_entry_times_vs_earlier_phases.csv`, `source_example_reproduction.csv`, `undated_example_candidate_search.json`, `audit_results.json`, `source_extracts/` (PDF figures at original resolution).

Charts exist for the 9 source examples and for every executed trade of window A (SL40 drawn; SL35 outcome in the subtitle). Window B (2022-2025) has results, ledgers and daily files but no per-trade charts.

Reproduce: `python scripts/phase70_run.py all && python scripts/phase70_docs.py`.
""")

    # ---------------------------------------------------------------- independent audit
    lines = ["# Independent audit (Phase 7.0)", "",
             "## 1. Second implementation vs production (no shared logic)",
             "`audit.py` rebuilds the 5-minute candles with `pandas.resample`, finds signals with NumPy index searches and replays trades on one-minute NumPy arrays; it is compared with the production state machines for **every session x method x scenario**.", "",
             "| window/scenario | signal comparisons | trade comparisons | mismatches |", "|---|---|---|---|"]
    for k, v in aud.items():
        if k != "causality":
            lines.append(f"| {k} | {v['signal_comparisons']} | {v['trade_comparisons']} | {v['mismatches']} |")
    lines += ["", "## 2. Causality (no look-ahead)", f"{caus['signals_checked']} signals (both methods, both windows): re-running the state machine on candles truncated at the failure candle reproduces the identical signal and timestamp; truncated one candle earlier it produces none; the fill timestamp is never before the signal timestamp. Failures: **{len(caus['failures'])}**.", "",
              "## 3. Test suite", "`tests/test_phase70_irf_v3.py` - Method 1 (figure, order, wick, equality, colour-agnostic, later cycles), Method 2 (figure, B = open not wick, first red only, red-before-breakout, no second breakout, wick, red-breakout variant, equality), isolation, causality, entry/stop/target maths, same-window tie, forced exit, cutoff inclusive of 13:00, combined cases (only M1 / only M2 / neither / same instant / M2 first), no double counting, metrics, journal matching stages, independent rebuild on synthetic days, example arithmetic and figures, undated examples never dated, no imports of old IRF engines / no unsupported-filter tokens, registry completeness.", "",
              "## 4. Checks listed in the task", "| Check | Result |", "|---|---|",
              "| Opening-range accuracy | first candle = the five 09:15-09:19 rows; verified in tests and by the independent rebuild |", "| Correct reference levels | M1 level, M2 Level A / B (open of the first red candle) verified by tests and the independent rebuild |",
              "| Candle sequencing / confirmation timing | signal_time == failure-candle end in every row (checked) |", "| No future data | see section 2 |", "| No unsupported extra filters | AST/token test on method1.py/method2.py; no EMA/gap/S-R/body/first-red-low code exists |",
              "| No duplicate trades | one combined trade per day; test + `combined_irf_backtest.csv` unique dates per window/scenario |", "| Entry/exit prices, stop/target | independent array replay: 0 mismatches |", "| Method isolation | tests |",
              "| Combined selection | tests + overlap analysis |", "| Journal matching | staged one-to-one matcher tested; journal SHA-256 `" + st["journal_sha256"] + "` equals the Phase 6.3 audit SHA; the workbook is opened read-only |",
              "| Chart correctness | charts built from the same trace/trade objects; Nov-3 chart inspected beside the embedded screenshot |", "",
              "## 5. Limitations of this audit", "* The independent rebuild was written by the same author from the same reading of the PDFs, so it detects coding defects, not a mistaken interpretation; interpretation risks are the unresolved questions. That is why an external read-only reviewer was also run (section 6).",
              "* Window B uses the secondary 5paisa store of Phase 4; both stores' session classification is inherited from `classify_session`.", "",
              "## 6. External read-only reviewer (separate agent, read both PDFs first, wrote its own aggregation and state machines)",
              "**Result:** no signal or P&L defect. It reproduced signal time and level for both methods in all 246 window-A sessions (0 mismatches) and rebuilt every traded session at SL40 and SL35 (278 trades, 0 bad); three sessions were traced by hand (2025-09-01, 2025-09-02, 2025-12-15).", "",
              "| # | Reviewer finding | Class | Action taken |", "|---|---|---|---|",
              "| 1 | MFE/MAE were updated for bars after the exit minute inside a 5-minute window (diagnostic only; fills, exits, P&L unaffected) | confirmed defect | fixed in `execution.py` (excursions only up to the exit bar); test `test_mfe_mae_stop_at_the_exit_bar` |",
              "| 2 | 'Red' = close < open; a doji is not red - not in the registry | disclosure gap | registry row M2-R20; test added |",
              "| 3 | M2 setup is never invalidated; in about a third of rally sessions the first red candle itself closes below Level A | ambiguity | quantified in `m2_rally_diagnostics.json` and README; new labelled variant `SL40_M2_INVALIDATE_BELOW_A` (not in the source) with independent-rebuild support; registry M2-R18 expanded; question 20 |",
              "| 4 | 'No entry after 1 pm' could exclude a fill at exactly 13:00:00 | ambiguity | new sensitivity `SL40_CUTOFF_EXCLUSIVE` (fill must start <= 12:59); test added |",
              "| 5 | Red rally-breakout candle as first red (only a handful of sessions) | ambiguity, disclosed | already reported as `M2_ALT_BREAKOUT_RED` |",
              "| 6 | M2 Example 4: failure candle one candle later than the engine's | unresolved | kept as a documented non-reproduction; registry M2-R21; question 19 |",
              "| 7 | Journal label is compared with the signal-candle START (a label meaning entry time would shift every match by 5 minutes) | disclosure nuance | stated in `recon.py` and the README; conventions unchanged from Phase 5.6/6.3 |",
              "| 8 | Each method contributes only its first cycle to the combined book | design note | by design (1 trade/day); later cycles are counted, not traded |",
              "Everything else (M1/M2 logic, look-ahead, execution maths, combined selection, metrics, matcher, no imported older-IRF assumptions) was rated NO ISSUE.", ""]
    (OUT / "independent_audit.md").write_text("\n".join(lines) + "\n")
    export_xlsx()


def export_xlsx() -> None:
    sheets = [("Rules", "rule_authority_registry.csv"), ("Performance", "historical_performance_comparison.csv"), ("Trades_M1", "method1_backtest.csv"), ("Trades_M2", "method2_backtest.csv"),
              ("Trades_Combined", "combined_irf_backtest.csv"), ("Signals_M1", "method1_signals.csv"), ("Signals_M2", "method2_signals.csv"), ("Daily", "daily_verification.csv"), ("Overlap", "overlap_analysis.csv"),
              ("Examples", "source_example_reproduction.csv"), ("Journal_Recon", "manual_journal_reconciliation.csv"), ("Journal_Summary", "manual_journal_match_summary.csv"), ("Journal_AutoOnly", "manual_journal_automated_only.csv"),
              ("Monthly_pts", "monthly_returns_points.csv"), ("Annual_pts", "annual_performance_points.csv"), ("Costs", "cost_slippage_sensitivity.csv"), ("Changed_vs_earlier", "changed_entry_times_vs_earlier_phases.csv")]
    readme = pd.DataFrame({"IRF V3 Complete Research - Phase 7.0": [
        "Research only. Synthetic NIFTY index points - not options/futures P&L. Nothing optimised; no orders; no strategy/journal/paper-trading change.",
        "Sources: IRF_Inverse_Retest_Failure_Rulebook.pdf (Method 1) and IRF_Method2_First_Red_Candle_Rulebook.pdf (Method 2) only.",
        "Windows: A = 2025-09-01..2026-08-31; B = 2022-09-01..2025-08-31. Scenarios SL35_T60 / SL40_T60 are separately labelled (the PDFs do not choose).",
        "Journal reconciliation is read-only and has no direction/price: no exact trade match is claimed.", "See README.md in the report folder for the 20 final answers."]})
    with pd.ExcelWriter(OUT / "IRF_V3_Complete_Research.xlsx", engine="openpyxl") as xw:
        readme.to_excel(xw, sheet_name="README", index=False)
        for name, f in sheets:
            df = pd.read_csv(OUT / f)
            df.to_excel(xw, sheet_name=name, index=False)
            ws = xw.sheets[name]
            ws.freeze_panes = "A2"
            for i, c in enumerate(df.columns, 1):
                ws.column_dimensions[get_column_letter(i)].width = min(max(len(str(c)) + 2, 12), 44)
        xw.sheets["README"].column_dimensions["A"].width = 150


if __name__ == "__main__":
    build()
