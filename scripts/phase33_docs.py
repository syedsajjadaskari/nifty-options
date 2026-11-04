"""Phase 3.3: write README.md, pdr_source_rule_verification.md, trade_by_trade_audit.md and owner_decisions_required.md from the delivered CSV files (every number is computed here)."""

from __future__ import annotations

import csv
import json
import statistics
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "phase3" / "phase33_pdr_audit"


def rd(n: str) -> list[dict]:
    with open(OUT / n, newline="") as f:
        return list(csv.DictReader(f))


def tab(head: list[str], body: list[list]) -> str:
    return "\n".join(["| " + " | ".join(head) + " |", "|" + "---|" * len(head)] + ["| " + " | ".join(str(x) for x in r) + " |" for r in body])


def f(x) -> float:
    return float(x)


def main() -> None:  # noqa: C901
    calc = rd("pdr_confirmation_calculations.csv")
    aff = [r for r in calc if r["close_below_floor"] == "True"]
    cls = {r["trade_id"]: r for r in rd("pdr_trade_classifications.csv")}
    cf = rd("zone_rule_counterfactual_counts.csv")
    ex = rd("source_example_checks.csv")
    man = {r["trade_id"]: r for r in rd("manual_journal_comparison.csv")}
    n, na = len(calc), len(aff)
    pos = Counter(r["confirmation_close_position"] for r in calc)
    cc = Counter(r["classification"] for r in aff)
    dist = sorted(-f(r["confirmation_close_minus_floor"]) for r in aff)
    pen = sorted(f(r["zone_penetration_depth_below_floor_5m"]) for r in aff)
    bins = [("<= 5 points", 0, 5), ("5-10", 5, 10), ("10-25", 10, 25), ("25-50", 25, 50), ("> 50", 50, 1e9)]
    dbin = [[b[0], sum(1 for x in dist if b[1] < x <= b[2] or (b[1] == 0 and x <= b[2] and x > 0))] for b in bins]
    not_day_high = sum(1 for r in calc if r["zone_is_previous_day_high_candle"] != "True")
    not_day_high_aff = sum(1 for r in aff if r["zone_is_previous_day_high_candle"] != "True")
    int_below_aff = sum(1 for r in aff if r["interaction_close_below_floor"] == "True")
    second_aff = sum(1 for r in aff if r["trade_no_of_day"] == "2")
    matched_all = [r for r in calc if r["journal_match"] in ("EXACT_MATCH", "TIME_SHIFTED_MATCH")]
    drawn = [r for r in ex if r["zone_reading"] == "drawn zone"]
    p32 = list(csv.DictReader(open(ROOT / "reports" / "phase3" / "phase32" / "manual_vs_automated.csv", newline="")))
    jr_unmatched = [f"{r['date']} {r['manual_entry_time_label']} {r['manual_outcome']}" for r in p32 if r["journal_strategy"] == "PDR" and r["match_classification"] not in ("EXACT_MATCH", "TIME_SHIFTED_MATCH")]
    prov = json.loads((OUT / "independent_audit_results.json").read_text()) if (OUT / "independent_audit_results.json").exists() else {}

    # ---------------------------------------------------------------------------------------------- source rule verification
    L = ["# PDR - what the original guide actually requires (source-rule verification)", "",
         "**Written for:** the strategy owner. Source: `docs/strategy_docs/PDR_Strategy_Guide.pdf` (4 pages). I read the text layer of every page and rendered all four pages to images; **pages 1-2 contain text and tables only (no figures)**, "
         "pages 3-4 contain the checklist and the five chart examples. Earlier AI summaries (Phase 2.2 research, registry rows PDR-001..012) were consulted only after reading the PDF. "
         "Every statement below is tagged **EXPLICIT** (the words are on the page), **FIGURE** (read off a chart; calibrated reading, +/- 1 point) or **UNRESOLVED** (the guide does not say).", "",
         "## 1. The text, page by page", "",
         tab(["page / section", "what it says (quotation)", "kind"], [
             ["p.1 table 'Strategy at a Glance'", "'Concept: Yesterday's resistance zone is expected to act as support after a gap-up open.' 'Zone: Small box from candle body to upper wick at the previous day's high/reversal.' "
              "'Next-day condition: Market must open gap up.' 'Trigger: Price returns to the zone, then a green candle forms.' 'Target 70 points (fixed).' 'Stop-loss 35 or 40 points, depending on the situation.'", "EXPLICIT"],
             ["p.1 s2 Overview", "'When the market opens gap up and then pulls back into the marked zone, the zone is watched to see whether it now works as support. If a green candle forms after the zone is tested, the trade is taken.' "
              "'Sequence: Previous day's high and reversal -> Mark zone -> Gap-up open -> Price returns to zone -> Support test -> Green candle -> Entry.'", "EXPLICIT (purpose + sequence)"],
             ["p.1 s3.1", "'Find the high where price reached a peak and then reversed. Locate the candle associated with that high. Note the candle's body and upper wick.'", "EXPLICIT"],
             ["p.2 s3.2", "'Upper boundary: the highest point of the upper wick. Lower boundary: the relevant candle-body level. Draw a small rectangle ... Extend the rectangle to the right so it stays visible on the next trading day.' "
              "'The zone is an area, not a single exact price. Mark only the actual resistance shown by price action, not the whole surrounding move.'", "EXPLICIT (which body edge: UNRESOLVED)"],
             ["p.2 s4.1", "'The market must open gap up. Do not enter at the open. Wait for price to come back toward the marked zone. If price keeps rising without returning to the zone, there is no setup.'", "EXPLICIT (gap size, reference close: UNRESOLVED)"],
             ["p.2 s4.2", "Interaction table: 'Wick touches zone / Body touches zone / Price enters zone (Price moves inside the rectangle) / Very close approach (Price comes close enough to count as a test of the zone)'. "
              "'Price does not need to hit one exact level. A move that stays far from the zone does not qualify.'", "EXPLICIT ('very close': UNRESOLVED)"],
             ["p.2 s4.3", "'After the zone has been tested, wait for a green candle and take the long entry on that confirmation.'", "EXPLICIT - no wording about where the green candle closes"],
             ["p.3 s6 checklist", "'Previous day: clear high and reversal identified' / 'Zone drawn from candle body to upper wick and extended forward' / 'Next day opens gap up' / 'Price returned to the zone (wick, body, inside, or very close)' / "
              "'Green candle formed after the interaction' / 'Entry taken; target 70 points; stop-loss 35 or 40 points'", "EXPLICIT"]]), "",
         "## 2. The four questions of the audit", "",
         "### A. How is the resistance zone built?", "",
         "* **EXPLICIT:** the zone belongs to 'the high where price reached a peak and then reversed' of the previous day; it is a small rectangle from the candle's body level up to the highest point of its upper wick (p.1 s3.1, p.2 s3.2).",
         "* **UNRESOLVED:** the text never says 'the absolute highest candle of the day'; it never says 'repeated shelf' or 'several candles'; it does not say which body edge ('the relevant candle-body level'); it gives no definition of 'clear high and reversal'.",
         "* **FIGURE (calibrated in Phase 2.2 and re-checked against the data in `source_example_checks.csv`):** Example 1 (2025-09-02), Example 2 (2025-10-06) and Example 4 (2025-11-20) draw the zone on the candle that made the previous session's high, from its body top to its wick tip "
         "(Example 4 within 0.4 point). Example 3 (2025-10-07) draws a thin box on a late-session **shelf of equal highs** (about 25,081-25,084) and skips the single 14:50 spike candle (25,095.70): the only figure that uses several candles. "
         "A PDR-style picture on page 9 of the RF guide (not part of the PDR guide) shows a long entry far below its zone; it is **not used as evidence**. So the figures support 'the candle at a clear high' (and, once, a shelf), not one mechanical rule.",
         f"* **Engine reading (owner-approved research candidate B):** the latest confirmed swing high (2 candles each side) that has a red candle among the peak and the next two; [body top, wick high]. "
         f"It is the previous day's high candle in only {n - not_day_high} of the {n} PDR trades ({not_day_high} differ); among the {na} affected trades {not_day_high_aff} differ. Whether that is 'the high where price reached a peak and then reversed' is exactly what the guide leaves open.", "",
         "### B. Opening conditions", "",
         "* **EXPLICIT:** the market must open gap up (p.1 table, p.2 s4.1); do not enter at the open; wait for a return toward the zone; no setup if price keeps rising.",
         "* **UNRESOLVED:** gap size (any gap qualifies in the code), the reference price of the gap (the code uses the official previous close), whether the **open must lie above the zone** (the overview says the market 'pulls back into the marked zone', which implies it; it is stated nowhere as a rule), and any requirement on the first candle (none is stated).", "",
         "### C. Retest conditions", "",
         "* **EXPLICIT:** a wick touch, a body touch, price inside the rectangle, or a 'very close approach' all count as the zone being tested; the price does not have to hit one exact level; a move that stays far from the zone does not qualify (p.2 s4.2, p.3 checklist).",
         "* **Not addressed at all:** price crossing **below the zone floor**; price returning to the zone **from below**; how far a candle may trade through the zone; whether a candle that closes through the zone still counts as a test. "
         "The checklist item 'Price returned to the zone (wick, body, inside, or very close)' is satisfied by any candle whose range overlaps the rectangle, which every one of the audited trades has.",
         "* **FIGURE:** price does trade below the drawn floor in the author's examples, but mostly in the **confirmation candle's own lower wick**: Example 2's green candle wicks 20.0 points below the drawn floor and Example 3's 3.7 (Example 1: 0.35, inside the calibration error); "
         "the candles BEFORE the confirmation candle (the retest proper) have their lowest low " + ", ".join(f"{r['example'].split(' (')[0]} {f(r['retest_low_before_confirmation_candle_minus_floor']):+.2f}" for r in drawn)
         + " points from the drawn floor (negative = below). Example 2's last test candle also closes 0.05 below the drawn floor (inside the +/-1 reading error). So the figures show wick penetration of the floor on the confirmation candle, "
         "and a retest that holds above the floor in three of four examples (Example 2 breaks it by 3.25 points on a 3.7-point box).", "",
         "### D. The confirmation candle", "",
         "* **EXPLICIT:** 'a green candle' formed 'after the zone has been tested' / 'after the interaction' (p.1 overview, p.2 s4.3, p.3 checklist). No candle-strength threshold, no body or wick size.",
         "* **UNRESOLVED:** any requirement that the green candle close above the floor, or above the ceiling, or that the zone 'held'. The only wording in this direction is the **purpose** statement - the zone is watched 'to see whether it now works as support' (p.1 s2) and the sequence has a 'Support test' step - which describes why the setup exists but does not define a numerical or positional test.",
         "* **FIGURE:** in all four dated examples the green confirmation candle closes **above the drawn ceiling** "
         + ", ".join(f"{r['example'].split(' (')[0]} by {f(r['confirmation_close_minus_ceiling']):.1f}" for r in drawn) + " points (and well above the floor); Example 5 (undated) is drawn the same way. No figure shows a confirmation close below the floor.", "",
         "## 3. Source evidence on whether a zone-hold confirmation is required", "",
         tab(["points towards requiring a hold (close at/above the zone)", "points towards NOT requiring one"], [
             ["p.1: 'expected to act as support'; 'watched to see whether it now works as support'; the sequence has a 'Support test' before the green candle", "p.2 s4.3 and the p.3 checklist state only 'a green candle after the interaction' - nothing about where it closes"],
             ["All four dated examples (and Example 5's drawing) end with a confirmation close above the ceiling", "'Price enters zone' is a valid interaction; 'Price does not need to hit one exact level'"],
             ["p.2: 'A move that stays far from the zone does not qualify' - the zone is meant to be where the action is", "In Examples 2 and 3 the confirmation candle's own wick trades below the drawn floor (20.0 and 3.7 points) before it closes above the ceiling; Example 2's last test candle closes at the floor"],
             ["p.2 s4.1: do not enter at the open; wait for price to come back TOWARD the zone (a pullback from above)", "The guide never says what a close through the zone means, nor gives a threshold; any rule here would be invented"]]), "",
         "**Conclusion (unchanged by any profit consideration):** the guide neither **requires** nor **forbids** a zone-hold confirmation. It is **UNRESOLVED in the source**. A hold condition is consistent with the *purpose* and with every dated figure, but it is not written, so adding it would be a new rule that only the owner can approve.", "",
         "## 4. The 27 affected trades against these questions", "",
         f"Independent count from the raw data: **{na} of {n}** PDR trades (long, bullish confirmation candle) closed below the selected zone floor (derived, not hard-coded; `independent_audit.md` repeats the derivation by a second route). "
         f"Confirmation close position over all {n} trades: above the ceiling {pos['ABOVE_CEILING']}, inside the zone {pos['INSIDE_ZONE']}, below the floor {pos['BELOW_FLOOR']}.", "",
         tab(["written condition (page)", "holds for the 27?"], [["gap-up open (p.1, p.2 s4.1)", f"{sum(1 for r in aff if r['explicit_conditions_all_hold'] == 'True')} of {na} satisfy all four written conditions below"],
                                                              ["not entered at the open (p.2 s4.1)", "all (the earliest possible fill is 09:25)"], ["zone interaction before the confirmation (p.2 s4.2, p.3)", "all (the test candle's range overlaps the rectangle)"],
                                                              ["green candle after the interaction (p.2 s4.3, p.3)", "all"], ["close at/above the floor or ceiling", "**not written anywhere**"]]), "",
         f"Distance of the confirmation close below the floor (points): min {min(dist):.2f}, median {statistics.median(dist):.2f}, max {max(dist):.2f}. Distribution: " + ", ".join(f"{a} {b}" for a, b in dbin) + ". "
         f"The test candle itself closed below the floor in {int_below_aff} of the {na}; the lowest price of the retest was {min(pen):.2f}-{max(pen):.2f} points (median {statistics.median(pen):.2f}) below the floor, "
         "against 0.35 / 20.0 / 3.7 / none in the author's Examples 1-4.", "",
         "## 5. Classification (decision rule)", "",
         "Applied in this order, to each affected trade, **without reading any outcome or P&L**: (1) DATA_OR_IMPLEMENTATION_ISSUE if an engine export differs from the raw reconstruction or the zone's source candle lies in the closing-auction window; "
         "(2) SOURCE_CONTRADICTED if an explicit written condition is violated; (3) ZONE_SELECTION_DISPUTED if another source-plausible zone (the previous-day-high candle A, or the repeated-highs shelf C) would fire on the SAME confirmation candle with its close at/above that zone's floor - "
         "the entry would then be acceptable under another reading of 'which resistance'; (4) INSUFFICIENT_EVIDENCE if the sequence cannot be reconstructed; (5) otherwise SOURCE_AMBIGUOUS. "
         "SOURCE_SUPPORTED is reserved for a sequence the guide clearly allows **and** that matches what its figures show; every written checklist item is satisfied by all 27, but no text or figure addresses a close through the zone, so none qualifies.", "",
         tab(["classification", "trades"], [[k, v] for k, v in sorted(cc.items())] + [["SOURCE_SUPPORTED", 0], ["SOURCE_CONTRADICTED", 0], ["DATA_OR_IMPLEMENTATION_ISSUE", 0], ["INSUFFICIENT_EVIDENCE", 0]]), "",
         f"A secondary flag marks the {not_day_high_aff} affected trades whose zone is not the previous-day-high candle (the zone-selection question is open for them too, even where it does not change the result). "
         "**Reading the zero counts:** SOURCE_SUPPORTED and SOURCE_CONTRADICTED are zero by the nature of the rule and the evidence - the four written conditions are guaranteed by how a PDR signal is generated, and no figure shows a close through the zone - they are not a measured finding. "
         "The ZONE_SELECTION_DISPUTED test assumes reading B (close at/above the floor) for the alternative zone; the one trade it flags (20260506-1-PDR) closes inside zone C, 7.5 points below that zone's ceiling, and would not pass reading C. "
         "Because 26 trades share one label, an informational severity column separates them (it is not used by the classification):", "",
         tab(["severity of the close below the floor", "trades"], [[k, v] for k, v in sorted(Counter(r["close_below_floor_severity_band"] for r in aff).items())]), "",
         "## 6. Counterfactual diagnostic (counts only; no re-run, no P&L, no recommendation)", "",
         tab(["reading", "definition", f"of {n} trades satisfying", f"of the {na} affected satisfying", "source evidence"], [[c["reading"], c["definition"], c["trades_satisfying"], c["affected_trades_satisfying"], c["source_evidence_status"]] for c in cf]), "",
         "By construction none of the 27 affected trades can satisfy B, C or D (their close is below the floor), so the counts also show how many of the other trades each reading would keep. "
         "A is the written text; B and C are not written but fit all four dated figures (C is the strictest reading that still fits them; yet one of the five journal-matched trades, 20260605-1, closes inside the zone and would fail C). "
         "D includes the confirmation candle's own wick, which trades below the drawn floor in Examples 2 and 3, so D would not have accepted those two examples; the sensitivity D2 (retest low before the confirmation candle) holds for Examples 1, 3 and 4 and fails Example 2 by 3.25 points, so the figures cannot separate D2 from a tolerant D2. "
         "None of these is recommended, and none was chosen by its win rate or profit.", "",
         "## 7. Source figures versus the data", "",
         tab(["example", "date", "zone reading", "zone [floor, ceiling]", "retest low vs floor", "confirmation close vs floor", "vs ceiling", "position"],
             [[e["example"], e["date"], e["zone_reading"] + (" (no sequence)" if "none" in e.get("interaction_candle", "") else ("" if e.get("is_the_examples_own_entry_candle") == "True" else " (not the example's own entry)")), f"[{f(e['zone_floor']):.2f}, {f(e['zone_ceiling']):.2f}]",
               f"{e.get('retest_low_minus_floor', '')} (before the confirmation candle: {e.get('retest_low_before_confirmation_candle_minus_floor', '')})", e.get("confirmation_close_minus_floor", ""), e.get("confirmation_close_minus_ceiling", ""),
               e.get("confirmation_position", e.get("interaction_candle", ""))] for e in ex]), "",
         "Rows whose confirmation candle is not the example's own entry candle (`is_the_examples_own_entry_candle` = False, typically the shelf zone C on another part of the day) are unrelated sequences and say nothing about the example. "
         "The drawn zones are the Phase 2.2 readings of the chart price tags (about +/- 1 point), but the drawn edges also deviate from the candle edges: Example 1's drawn ceiling (24,640) is 5.0 above the previous day's wick tip (24,635.0) and Example 2's drawn floor is 2.1 above the candle's body top. "
         "The figures' own candles also differ from the repo data at the open (Example 1's first candle is green in the figure and red in the data, Example 4's first candle shows a small upper wick the data does not have); the sequences are unaffected. "
         "Example 3's engine zone is [25,077.25, 25,095.70] (18.45 points, built from the 14:50 spike candle), against the drawn 3.6-point shelf; the engine rejects that day because the open (25,087.55) is inside its zone (an earlier registry note quoting a 38.6-point box is not reproduced). "
         "**Example 5** (undated, no axis) could not be matched to the data. Read at 5x zoom: its zone starts at a peak candle about one session earlier, and the entry session appears to open roughly flat inside/at the zone with no visible gap-up above it, "
         "which would bear on the gap-up rule and on PDR-011 (open above the zone). This is a low-resolution reading and **the owner should look at it**. "
         "The three examples the engine reproduces (1, 2, 4) all match a journal PDR trade exactly (`manual_journal_comparison.csv`); the journal also has a PDR row on 2025-10-07 09:20, the Example 3 date and its confirmation candle, which the engine does not trade.", ""]
    (OUT / "pdr_source_rule_verification.md").write_text("\n".join(L))

    # ---------------------------------------------------------------------------------------------- trade-by-trade
    T = ["# PDR trade-by-trade audit - the 27 entries whose confirmation candle closed below the zone floor", "",
         "**Written for:** the strategy owner, who will look at each trade's chart (`charts/<trade_id>.svg`). Prices are index points from the raw one-minute data (5-minute candles rebuilt causally; a candle labelled 09:15 covers 09:15-09:19 and is usable at 09:20). "
         "Everything after the entry is labelled POST_ENTRY and is context only. No outcome or P&L is used for any classification.", ""]
    for r in aff:
        c = cls[r["trade_id"]]
        m = man[r["trade_id"]]
        T += [f"## {r['trade_id']} - {r['date']} ({r['weekday']}), {'second' if r['trade_no_of_day'] == '2' else 'first'} trade of the day", "",
              f"**Classification: {c['classification']}** ({c['confidence']} confidence). Basis: {c['basis']}. Owner clarification: {c['owner_clarification']}. Chart: ![{r['trade_id']}](charts/{r['trade_id']}.svg)", "",
              tab(["item", "value"], [
                  ["Previous-day candle used for the zone", f"{r['zone_source_candle_start']} O {f(r['zone_source_open']):,.2f} H {f(r['zone_source_high']):,.2f} L {f(r['zone_source_low']):,.2f} C {f(r['zone_source_close']):,.2f}"],
                  ["Zone (method B_SWING_HIGH_REVERSAL, body top .. wick high)", f"floor {f(r['zone_floor']):,.2f} / ceiling {f(r['zone_ceiling']):,.2f} (height {f(r['zone_height']):.2f})"],
                  ["Previous-day high", f"{f(r['previous_day_high']):,.2f} at {r['previous_day_high_candle_start']} - the zone {'IS' if r['zone_is_previous_day_high_candle'] == 'True' else 'is NOT'} that candle"
                   + ("" if r['zone_is_previous_day_high_candle'] == 'True' else f" (zone ceiling {f(r['zone_ceiling_below_previous_day_high']):.2f} points lower)")],
                  ["Open / official previous close / gap", f"{f(r['session_open']):,.2f} / {f(r['official_previous_close']):,.2f} / {f(r['gap_points']):+.2f}; open {f(r['open_above_zone_ceiling_points']):.2f} points above the zone ceiling"],
                  ["Interaction (test) candle", f"{r['interaction_candle_start']} O {f(r['interaction_open']):,.2f} H {f(r['interaction_high']):,.2f} L {f(r['interaction_low']):,.2f} C {f(r['interaction_close']):,.2f} - "
                   f"closed {'BELOW' if r['interaction_close_below_floor'] == 'True' else 'at/above'} the floor"],
                  ["Lowest price of the retest (5-min lows, test..confirmation)", f"{f(r['retest_low_5m']):,.2f} = {f(r['zone_penetration_depth_below_floor_5m']):.2f} points below the floor (1-minute low {f(r['retest_low_1m']):,.2f})"],
                  ["Green confirmation candle", f"{r['confirmation_candle_start']} O {f(r['confirmation_open']):,.2f} H {f(r['confirmation_high']):,.2f} L {f(r['confirmation_low']):,.2f} C {f(r['confirmation_close']):,.2f}; "
                   f"body {f(r['confirmation_body_pct']):.1f}%, upper wick {f(r['confirmation_upper_wick']):.2f} ({f(r['confirmation_upper_wick_pct']):.1f}%), lower wick {f(r['confirmation_lower_wick']):.2f} ({f(r['confirmation_lower_wick_pct']):.1f}%)"],
                  ["Close relative to the zone", f"{-f(r['confirmation_close_minus_floor']):.2f} points BELOW the floor ({f(r['confirmation_close_minus_ceiling']):+.2f} vs the ceiling)"],
                  ["Signal confirmed / earliest fill / entry price", f"{r['signal_confirmed_at']} / {r['earliest_fill_timestamp']} (open of the next 1-minute bar) / {f(r['entry_price']):,.2f}"],
                  ["POST_ENTRY context", f"next candle {r['POST_ENTRY_next_candle_start']} low {r['POST_ENTRY_next_candle_low']} close {r['POST_ENTRY_next_candle_close']}; it {'did' if r['POST_ENTRY_next_candle_intersects_zone'] == 'True' else 'did not'} move back into the zone"],
                  ["Alternative zones, same sequence rule", f"A previous-day-high candle {r['alt_A_previous_day_high_zone']} (fires on this candle: {r['alt_A_previous_day_high_fires_on_same_candle']}); C repeated shelf {r['alt_C_repeated_shelf_zone']} (fires: {r['alt_C_repeated_shelf_fires_on_same_candle']})"],
                  ["Nearest figure in the guide", c.get("nearest_source_figure", "")],
                  ["Manual journal", f"{m['journal_match_class']}: {m['reason_or_note']}"],
                  ["Source-rule status", "green candle after the interaction: SOURCE_VERIFIED (qualitative, PDR-007); close-location / zone-hold: not a source rule and not tested by the engine (UNRESOLVED)"]]), ""]
    (OUT / "trade_by_trade_audit.md").write_text("\n".join(T))

    # ---------------------------------------------------------------------------------------------- owner decisions
    O = ["# Phase 3.3 - owner decisions required (PDR)", "",
         "Only the decisions the documents and the data cannot settle. Nothing was changed in this phase; none of the options below was chosen by its win rate or profit.", "",
         tab(["#", "decision", "why it is open (evidence)", "options (diagnostic counts, not recommendations)"], [
             ["1", "**Is a zone-hold confirmation required?** (must the green confirmation candle close at/above the zone floor, or above the ceiling?)",
              f"Not written in the guide; the purpose statement and all four dated figures point to a hold, the text and the checklist do not require it. {na} of {n} entries close below the floor.",
              f"keep the written text (A: {n}); close >= floor (B: {cf[1]['trades_satisfying']}); close > ceiling (C: {cf[2]['trades_satisfying']}); the written rule stays if the owner says the guide means only 'a green candle'"],
             ["2", "**May the retest low trade below the floor?** (reading D / D2)", "In the author's Examples 2 and 3 the confirmation candle's own wick trades 20.0 and 3.7 points below the drawn floor before closing above the ceiling; the candles before it hold above the floor in Examples 1, 3, 4 and break it by 3.25 points (on a 3.7-point box) in Example 2. The figures cannot separate D2 from a tolerant D2.", f"D satisfied by {cf[3]['trades_satisfying']} of {n}, D2 by {cf[4]['trades_satisfying']}; a tolerance (points) would have to come from the owner"],
             ["3", "**Which previous-day candle marks the zone?** (day-high candle, latest reversal swing, or repeated-highs shelf)",
              f"The guide says 'the high where price reached a peak and then reversed'; its examples use the session-high candle (1, 2, 4) and a shelf (3). The engine's zone is the day-high candle in only {n - not_day_high} of {n} trades; "
              f"it changes the entry for {cc.get('ZONE_SELECTION_DISPUTED', 0)} of the 27 and is an open question for {not_day_high_aff} of them.", "A / B / C (PDR-ZONE-002); the registry already lists B and C as owner-approved research candidates"],
             ["4", "**Must the open lie above the zone?** (PDR-011)", "'Pulls back into the marked zone' implies it; it is not a stated rule; the engine rejects days when the open is inside the zone.", "keep / drop / allow open inside the zone"],
             ["5", "**What counts as a 'very close approach'?**", "No number in the guide (p.2 s4.2); the engine uses strict range overlap (proximity 0).", "a number of points, or strict overlap"],
             ["6", "**Second trades:** may a second PDR entry follow an original full stop on the same day when price has traded through the zone?", f"{second_aff} of the 27 affected entries are second trades; the controller rule is approved, the zone-hold question is separate.", "follows decision 1"],
             ["7", "**Journal:** are the unmatched PDR entries meant to be taken?", f"None of the {na} affected trades matches a journal PDR row. Of the {len(matched_all)} automated PDR trades that match (4 exact, 1 within tolerance - the latter a row labelled ORB and attributed to PDR by the Phase 2.1 hypothesis), four close above the ceiling and one (20260605-1) inside the zone. "
              f"The journal has {len(jr_unmatched)} PDR rows with no automated trade ({'; '.join(jr_unmatched)}); one of them is the Example 3 date. The journal records no zone or price, so no discretionary decision can be inferred.", "owner to say how the journal PDR entries were chosen"]]), "",
         "## Source figures that need the owner's eye", "",
         "* Example 5 (PDR p.4) has no date and cannot be matched to the data; at high zoom the entry session seems to open at/inside the zone with no visible gap-up (a low-resolution reading) - please look; it matters for the gap-up rule and decision 4.",
         "* Example 3 (PDR p.4, 2025-10-07) is not reproduced by the engine zone ([25,077.25, 25,095.70], 18.45 points, from the 14:50 spike; the open 25,087.55 is inside it so the engine rejects the day); the drawn zone is a 3.6-point shelf, and the journal has a PDR entry on that day at 09:20.", ""]
    (OUT / "owner_decisions_required.md").write_text("\n".join(O))
    print("docs written", len(L), len(T), len(O), prov.get("all_pass"))


if __name__ == "__main__":
    main()
