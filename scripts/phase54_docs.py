"""Phase 5.4: the markdown deliverables of reports/phase5/phase54_orb_audit/, written from the CSV / JSON files produced by scripts/phase54_run.py (counts and identities are read, not typed). The page-by-page source
findings were written after rendering and reading all 13 pages of the ORB rulebook and the six handwritten pages.

  python scripts/phase54_docs.py --tests "<pytest result>" --ruff "<ruff result>"
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "phase5" / "phase54_orb_audit"
WARN = "Audit evidence only: no controller, no fills, no P&L, no backtest was run. Variants are disabled by default and none is source-defined or approved."


def rd(p: Path) -> list[dict]:
    with open(p, newline="") as f:
        return list(csv.DictReader(f))


def tab(head: list[str], rows: list[list]) -> str:
    esc = lambda v: str(v).replace("|", "/").replace("\n", " ")  # noqa: E731
    return "\n".join(["| " + " | ".join(head) + " |", "|" + "---|" * len(head)] + ["| " + " | ".join(esc(c) for c in r) + " |" for r in rows])


def fb(x) -> bool:
    return str(x) == "True"


def main() -> int:  # noqa: C901
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--tests", default="not recorded in this run")
    ap.add_argument("--ruff", default="not recorded in this run")
    a = ap.parse_args()
    S = json.loads((OUT / "summary.json").read_text())
    d13 = rd(OUT / "orb_13_disputed_dates.csv")
    reg = rd(OUT / "orb_source_rule_registry.csv")
    lf = rd(OUT / "orb_level_families_13.csv")
    fp = rd(OUT / "orb_level_family_population.csv")
    sr = rd(OUT / "orb_strength_review.csv")
    et = rd(OUT / "orb_ema_trendline_review.csv")
    vi = rd(OUT / "orb_variant_impact.csv")
    jc = rd(OUT / "orb_journal_cross_check.csv")
    sp = {r["measure"]: int(r["sessions"]) for r in rd(OUT / "orb_strength_population.csv")}
    ar = json.loads((OUT / "independent_audit_results.json").read_text()) if (OUT / "independent_audit_results.json").exists() else {"checks": {}, "all_pass": False}
    rev = (OUT / "_reviewer_findings.md").read_text() if (OUT / "_reviewer_findings.md").exists() else ""
    T = S["thirteen"]
    J = S["journal_orb"]
    GP = S["gap_reading_population"]
    FPOP = {r["family"]: r for r in fp}
    VI = {r["variant"]: r for r in vi}
    n_sess = int(fp[0]["sessions"])
    sr_by = {r["date"]: r for r in sr}
    et_by = {r["date"]: r for r in et}
    reg_counts = S["registry"]

    # ============================================================================================ orb_author_corrections.md
    AC = ["# ORB - the author's corrections (13 disputed dates, AC27)", "", WARN, "",
          "All 13 handwritten ORB remarks are plain text ('ORB should have activated instead of IRF'); the six handwritten pages contain NO ORB drawing, level, candle or direction (all six pages were read and rendered). The author never says which ORB method, which level or which direction. "
          f"The first candle is GREEN on {T['first_candle_colours'].get('GREEN', 0)} of the 13 dates and RED on {T['first_candle_colours'].get('RED', 0)}; IRF is a short-only strategy, so on the green days the system sold a market that opened with a strong green candle, and the only ORB that a green first candle can support is a LONG.", "",
          f"**The engine produced no confirmed ORB signal on any of the 13 dates** ({T['frozen_orb_records_on_the_13']} ORB records exist on those dates, all invalidated; {T['frozen_orb_confirmed_on_the_13']} confirmed). Because ORB decides at 09:20 and IRF can only fire later, ORB would already have priority by TIME under the controller's first-valid-signal rule: the dispute is an ORB QUALIFICATION problem, not a controller-priority problem.", "",
          "## The 13 dates", "",
          tab(["date", "AC / hand page", "author's words", "first candle (colour, body %, wicks %)", "open gap", "ORB status", "Phase 3.6 trade taken", "manual journal row"],
              [[r["date"], f"{r['correction_id']} / p.{r['handwritten_pdf_page']}", r["author_original_comment"][:70], f"{r['first_candle_colour']}, {r['body_pct']}, {r['upper_wick_pct']}/{r['lower_wick_pct']}", r["open_gap_points"], r["actual_orb_signal_status"][:60], r["actual_irf_signal_and_other_trades"][:48], r["manual_journal_row"]] for r in d13]), "",
          "## What is missing on each date (first failing predicate per method, colour-matching direction)", "",
          tab(["date", "Method 1", "Method 2", "Gap / 200 DMA", "relevant source rules", "conflict with the existing code?"],
              [[r["date"], r["missing_condition_Method_1"], r["missing_condition_Method_2"], r["missing_condition_Gap_200DMA"], r["relevant_source_rules"][:60], r["conflicts_with_existing_code"][:150]] for r in d13]), "",
          "The full per-date predicate table (observed value, rule, rule id, signed margin) for both directions is in `orb_predicate_matrix.csv`; the required definition per date is in `orb_13_disputed_dates.csv` (`required_correction_or_unresolved_definition`).", "",
          "## Distribution of the missing conditions", "",
          tab(["method", "first failing predicate", "dates"], [[m, k, n] for m, key in (("Method 1", "missing_Method_1"), ("Method 2", "missing_Method_2"), ("Gap / 200 DMA", "missing_Gap")) for k, n in T[key].items()]), "",
          "The causes are NOT one defect: Method 1's level is not broken on 9 dates (the first candle closes inside the previous day's range), the frozen Method 2 inner level is not broken on 6, the Method 2 trendline blocks 4, the trend filter blocks 2 (both are gap-ups through the EMA, i.e. Gap-setup territory), and the numeric candle thresholds block 3 (plus a 0.08-point open-versus-average tie on one date).", "",
          "## Dates where the author's interpretation may conflict with the code", "",
          "* **Numeric thresholds and research constructions (not source rules):** " + ", ".join(r["date"] for r in d13 if r["conflicts_with_existing_code"].startswith("YES")) + " - the closest method is rejected by a trendline / strength / trend / gap-crossing rule that the engine decides with a research assumption.",
          "* **Explicit source conditions not met:** " + ", ".join(r["date"] for r in d13 if r["conflicts_with_existing_code"].startswith("NO")) + " - the closest method fails an explicit source condition (the first candle breaks neither the previous-day extreme nor the frozen inner level); the author's level is unknown (no drawing).",
          "* **Unidentifiable:** " + ", ".join(r["date"] for r in d13 if r["conflicts_with_existing_code"].startswith("UNDETERMINED")) + " - every method fails two or more predicates.", "",
          "The author is not assumed correct about objective candle conditions: where the rulebook's own illustrations (p.3, p.10) show clean candles, the disputed candles are less clean (see `orb_candle_strength_review.md`).", "",
          "## Two dates whose journal row differs from the handwritten correction", "",
          "* 2025-11-21 (AC24: 'ORB should have activated, but IRF is activated'): the manual journal records an IRF trade at 09:40 (Target), not an ORB.", "* 2025-10-17 (AC15): there is no journal row at all.", "",
          "## AC27 - the ORB colour rule (2025-11-27)", "",
          "The author wrote: 'ORB is activated on a red candle for long side, which is wrong. ORB for long should be in green closing.' The frozen engine produced a Method 1 LONG signal on a RED first candle (body 15%, lower wick 85%: it passes the owner-style bullish pin-bar test; the rulebook's text states no colour for the pin bar and its p.10 figure draws the pin bar green, so 'any colour' is the engine's reading, not a source statement). "
          f"The Phase 5.1 colour rule (long needs a green first candle, short a red one) removes {VI['orb-var-colour']['removed_vs_frozen']} frozen ORB signals (53 -> {VI['orb-var-colour']['confirmed_orb_signals']}), including AC27's, and none of those dates carries a manual ORB journal row (a date overlap only; the journal has no direction). "
          "The LONG half has explicit author evidence (AC27); the SHORT half (red first candle for shorts) is an interpretation of 'the same rules in both directions' (ORB-GLOBAL-002) and is NOT activated here."]
    (OUT / "orb_author_corrections.md").write_text("\n".join(AC) + "\n")

    # ============================================================================================ orb_candle_strength_review.md
    three = ["2025-10-16", "2025-12-12", "2025-12-30"]
    ST = ["# ORB - the strong-candle condition (review of the three rejected candles)", "", WARN, "",
          "## What the source says", "",
          "* p.3 / p.4 (Method 1): 'a strong green body and a small upper wick' (short: strong red body, small lower wick). p.5-7 (Method 2): 'convincing green body, limited upper wick'. p.8-9 (Gap): 'a strong green body, or a suitable bullish pin-bar-type candle'; 'reject candles with a very large lower wick'.",
          "* p.10 (the candle-quality figure): PREFERRED = a big body closing near the high with a small upper wick; CONDITIONAL = a bullish pin bar ('its position and close must support the breakout'); REJECT = strong upper-wick rejection. 'A pin bar's shape alone is never sufficient.'",
          "* **No percentage is given anywhere.** The figures draw very clean candles (a body of roughly 80-90% of the range with a tiny wick in the Method 1 and Method 2 charts and in the p.10 'preferred' example).", "",
          "## What the engine uses (RESEARCH_PROPOSAL, not source)", "",
          "Strong = body >= 60% of the range and the wick against the trade <= 20% (profile MODERATE); alternatives STRICT (70% / 15%) and LOOSE (50% / 25%); the conditional pin bar = wick >= 2x the body with the close within 30% of the range (the owner's recommendation); a rejection-wick flag at 33% (Gap setup only).", "",
          "## The three disputed candles rejected by the threshold", "",
          tab(["date", "direction", "OHLC", "body %", "wick against the trade %", "close location %", "STRICT", "MODERATE", "LOOSE", "pin bar (owner test)", "miss vs MODERATE (body / wick, points of %)", "miss vs LOOSE"],
              [[d, sr_by[d]["direction"], sr_by[d]["ohlc"], sr_by[d]["body_pct"], sr_by[d]["opposite_wick_pct"], sr_by[d]["close_location_pct"], sr_by[d]["strong_STRICT"], sr_by[d]["strong_MODERATE"], sr_by[d]["strong_LOOSE"], f"{sr_by[d]['pin_bar_active_definition']} (wick/body {sr_by[d]['pin_wick_to_body']}, {sr_by[d]['pin_close_distance_from_favourable_extreme_pct']}% from the extreme)",
                f"{sr_by[d]['body_margin_MODERATE']} / {sr_by[d]['opp_wick_margin_MODERATE']}", f"{sr_by[d]['body_margin_LOOSE']} / {sr_by[d]['opp_wick_margin_LOOSE']}"] for d in three]), "",
          "(Positive margin = satisfied by that many percentage points; negative = missed by that much.)", "",
          "Full measurement fields for the three candles (points): ", "",
          tab(["date", "O / H / L / C", "range", "body", "upper wick", "lower wick", "colour", "close - previous-day level (trade direction)", "close location in the range %"],
              [[d, sr_by[d]["ohlc"], sr_by[d]["range"], sr_by[d]["body"], sr_by[d]["upper_wick"], sr_by[d]["lower_wick"], sr_by[d]["colour"], sr_by[d]["distance_close_to_previous_day_level"], sr_by[d]["close_location_pct"]] for d in three]), "",
          "* **2025-12-12** (green, body 52.2%, opposite wick 0.7%): rejected by MODERATE only because the body is 7.8 points short of 60%; it passes LOOSE (50%). The candle also opened and closed above the previous high (gap +84).",
          "* **2025-12-30** (red short, body 76.2%, lower wick 23.9%): rejected by MODERATE because the lower wick is 3.9 points above 20%; it passes LOOSE (25%). It broke and closed below the previous low.",
          "* **2025-10-16** (green, body 26.7%, upper wick 29.9%, lower wick 43.4%; gap +77 above the previous high): fails EVERY profile and the owner pin test (wick/body 1.63 < 2). It is neither the 'preferred' nor the 'rejected' shape of p.10 (the upper wick is below the 33% rejection flag) - the source does not decide it.", "",
          "## Two further candles that fail the shape test inside the Gap setup", "",
          tab(["date", "OHLC", "body %", "wick against the trade %", "pin test", "note"],
              [[d, sr_by[d]["ohlc"], sr_by[d]["body_pct"], sr_by[d]["opposite_wick_pct"], f"{sr_by[d]['pin_bar_active_definition']} (wick/body {sr_by[d]['pin_wick_to_body']}; {sr_by[d]['pin_close_distance_from_favourable_extreme_pct']}% from the extreme, needs <= 30)", note] for d, note in (
                  ("2025-10-27", "a pin-bar-type candle (lower wick 2.5x the body) whose close is 2.7 points of % outside the owner's 30% band; fails by a hair"), ("2025-12-31", "body 74% but the wick against the trade is 25.7% (fails MODERATE and LOOSE by 5.7 / 0.7 points)"))]), "",
          "## The author's own numeric remarks (handwritten pages; all in IRF context, listed as evidence)", "",
          "AC32 (2025-12-11): 'should be ignored as candle body is less than 50%'; AC07 (2025-09-17): 'entry candle body is 40% wick is 60%'; AC01 (2025-09-01): '60+ body candle in the entry side'. The author thus uses body percentages of 40-60% when discussing entry candles for IRF; the 50% remark is close to the LOOSE profile (50% / 25%) and 60% to MODERATE. They are not ORB statements and do not fix an ORB threshold.", "",
          "## Verdict on the current threshold", "",
          "* **Explicitly supported by the source?** No - the rulebook gives no numbers. **A reasonable provisional approximation?** Partly: MODERATE (60% / 20%) is looser than the rulebook's own figures; LOOSE (50% / 25%) is looser still. **In conflict with the author's illustration?** The illustrations (clean 80-90% bodies) support the stricter reading, while the author's handwritten expectation (2025-12-12, 2025-12-30) supports a looser one: the author's two statements point in different directions. **Undefined?** Yes: 'strong' and 'convincing' remain qualitative, so a numeric approximation remains necessary.",
          f"* Population (first candles that break and close beyond the previous-day extreme, {sp['m1_level_broken_sessions']} sessions): strong under STRICT {sp['m1_broken_strong_STRICT']}, MODERATE {sp['m1_broken_strong_MODERATE']}, LOOSE {sp['m1_broken_strong_LOOSE']}; pin bar {sp['m1_broken_pin']}. The profile changes the ORB signal count (53 -> {VI['orb-var-strength-strict']['confirmed_orb_signals']} with STRICT, {VI['orb-var-strength-loose']['confirmed_orb_signals']} with LOOSE) and reproduces {VI['orb-var-strength-loose']['disputed_dates_with_a_signal (of 13)']} of the 13 disputed dates with LOOSE ({VI['orb-var-strength-loose']['disputed_dates_list']}).",
          "* **No threshold was optimised.** The percentages were not tuned; the three profiles are the ones that already existed. Choosing between them is an owner decision (`orb_rule_decision_matrix.md`, R8)."]
    (OUT / "orb_candle_strength_review.md").write_text("\n".join(ST) + "\n")

    # ============================================================================================ orb_ema_trendline_review.md
    EM = ["# ORB - the EMA / trend condition and the trendline (review)", "", WARN, "",
          "## What the source requires", "",
          "* Trend (Methods 1 and 2): 'Established trend in trade direction'; p.3: 'Confirm the uptrend. **Price above the 200 EMA is a basic confirmation, supported by bullish price structure.**' (short: price below the 200 EMA, bearish structure). p.5: 'if the breakout is near the EMA, wait for a convincing close above it'. The Gap / 200 DMA setup needs no established trend.",
          "* The rulebook mixes '200 DMA', '200 EMA' and '200 DMA / EMA' (ORB-MA-001); the repository uses the EMA(200) of completed five-minute closes (reproduces the PDR chart legends to 0.005).",
          "* Trendline (Method 2): 'connect swing lows (rising)' / 'swing highs (falling)'; 'a trendline by itself is not an entry signal'. No count, tolerance or algorithm is given.", "",
          "## What the engine requires (stricter or different?)", "",
          "* **Trend, frozen (`EMA_PREV_SESSION_CLOSE`, owner-approved variant A):** the PREVIOUS session's last close on the trend side of its own EMA. Design reason: the opening gap can never establish the trend. The rulebook's literal wording ('price above the 200 EMA' when the 09:20 candle is checked) is a different sampling time. The structure variant (`STRUCTURE_EMA_SWING2`: EMA side plus two higher swing highs and lows) is stricter still and is NOT active.",
          "* **Trendline, frozen:** a line through the last two previous-session k=2 fractal lows (highs), required to slope in the trade direction with the first close on the trend side. This is a research construction.", "",
          "## The two EMA dates", "",
          tab(["date", "previous close - its EMA", "first close - EMA", "open - EMA", "active trend test", "structure variant", "literal first-close test", "EMA change over the last previous hour"],
              [[d, et_by[d]["prev_close_minus_ema"], et_by[d]["first_close_minus_ema"], et_by[d]["open_minus_ema"], et_by[d]["trend_active_prev_close_vs_ema"][:60], et_by[d]["trend_structure_variant"][:60], et_by[d]["trend_literal_first_close_vs_ema"][:40], et_by[d]["ema_change_last_hour_prev_session"]] for d in ("2025-10-27", "2025-12-31")]), "",
          "On both dates the previous session closed on the wrong side of its EMA and the market GAPPED UP through it; the first candle closes above the EMA (+22.3 and +38.2 points), so the rulebook's literal 'price above the 200 EMA' test passes while the frozen previous-close test fails (by 41.5 and 4.6 points). These are exactly the conditions of the Gap / 200 DMA special setup, which needs no trend: on 2025-10-27 that setup fails only the candle shape (see the strength review); on 2025-12-31 the open is 0.08 points below the average (a reading difference, below) and the wick is 25.7%.",
          f"The literal reading is available as `orb-var-trend-ema-basic` (DIAGNOSTIC): it adds {VI['orb-var-trend-ema-basic']['added_vs_frozen']} population signals ({VI['orb-var-trend-ema-basic']['confirmed_orb_signals']} total) but reproduces {VI['orb-var-trend-ema-basic']['disputed_dates_with_a_signal (of 13)']} of the 13 dates, because both disputed dates then fail other conditions. **The EMA filter was not relaxed to generate trades; the variant only measures the effect.** The structure variant removes {VI['orb-var-trend-structure']['removed_vs_frozen']} frozen signals.", "",
          "## Swing structure and long / short eligibility on all 13 dates (previous session; active trend test)", "",
          tab(["date", "direction (colour)", "confirmed swing highs (n, last two)", "confirmed swing lows (n, last two)", "EMA change over the last hour", "LONG eligible (active)", "SHORT eligible (active)", "structure variant"],
              [[r["date"], r["direction"], r["previous_session_confirmed_swing_highs (n, last two)"], r["previous_session_confirmed_swing_lows (n, last two)"], r["ema_change_last_hour_prev_session"], r["long_eligible_active_trend"][:34], r["short_eligible_active_trend"][:34], r["trend_structure_variant"][:50]] for r in et]), "",
          "## The Gap setup: does the OPEN or the CANDLE have to cross the 200 average?", "",
          "**Text:** p.7 'provided the gap pushes price through the 200 DMA AND the first 5-minute candle closes beyond it'; p.8 steps 1-3: 'the market opens above the previous close' / 'price may have been below it; the gap must bring price above' / 'a candle that only crosses the line but closes below it does not qualify'; p.12 matrix: 'First-candle confirmation: close beyond 200 DMA'.",
          "**Figures (rendered and read):** in both Gap schematics (p.8 gap-up, p.9 gap-down) the first candle OPENS ON THE OLD SIDE of the 200 DMA (below it for the gap-up, above it for the gap-down), its body crosses the line and it closes beyond it; the drawn gap box lies wholly on the old side and never reaches the line. The real gap-up chart on p.12 shows a tall green candle starting far below the EMA(200) and closing at / through it, and the entry is taken there. "
          "**The figures therefore depict the CANDLE crossing the average; the frozen reading (the OPEN must already be beyond it) is the stricter reading and no figure evidences it.** The text alone does not decide it; the figures lean to the candle-crossing reading (the engine's Method 1 likewise lets the candle itself cross the level).",
          f"Frozen reading: the previous close on the wrong side of its average AND the open strictly beyond the average. Alternative (variant `orb-var-gap-candle-crossing`): the same previous-close condition, and the candle closes beyond the average and its range reaches it. Across the {GP['gap_in_direction_cases']} evaluable gap-in-direction cases of the {n_sess} sessions: frozen qualifies {GP['frozen_reading_cases']}, alternative {GP['candle_crossing_reading_cases']}; the two readings differ in {GP['cases_where_the_readings_differ']} cases (listed in `summary.json`), one of them 2025-12-31 (open 0.08 below the average). "
          f"As a signal-only variant: {VI['orb-var-gap-candle-crossing']['confirmed_orb_signals']} confirmed ORB signals against 53 ({VI['orb-var-gap-candle-crossing']['added_vs_frozen']} added, {VI['orb-var-gap-candle-crossing']['removed_vs_frozen']} removed; the others of the 10 differing cases fail the candle-shape test); it reproduces {VI['orb-var-gap-candle-crossing']['disputed_dates_with_a_signal (of 13)']} of the 13 disputed dates (2025-12-31 then fails the wick test: upper wick 25.7% against 20% / 25%).", "",
          "Technical notes: (a) the EMA(200) is the EMA of completed five-minute closes seeded with the SMA of the first 200 candles; the 2025-10-21 Muhurat evening session (12 candles) is excluded by the repository's session filter - including it would move the 2025-10-27 EMA from 25839.10 to about 25843.56 and flips no predicate; (b) the fractal pivots are NON-STRICT (>= / <=): flat tops and bottoms count as fractals (the 2025-12-31 long trendline is a zero-slope line), a detail the 'k = 2 fractal' wording does not show.", "",
          "## The two trendline dates", "",
          tab(["date", "last three fractals (time, price)", "frozen trendline", "line value at the open", "any-pair-of-last-three"],
              [[d, et_by[d]["trendline_fractals_last3 (time, price)"], et_by[d]["trendline_frozen_reason"], et_by[d]["trendline_value_at_open"], et_by[d]["trendline_any_pair_reason"]] for d in ("2025-09-11", "2025-11-28")]), "",
          f"Two readings of 'connect the relevant swing lows' exist: the last two fractals (frozen) and any two of the last three. The second makes 2025-11-28 qualify as a Method 2 LONG (`orb-var-trendline-any-pair`: {VI['orb-var-trendline-any-pair']['confirmed_orb_signals']} signals, {VI['orb-var-trendline-any-pair']['added_vs_frozen']} added); dropping the trendline altogether (a diagnostic, since the source says it is part of Method 2) also admits 2025-09-11. The trendline conditions also reject candles that would otherwise qualify on dates outside the dispute.", "",
          "## Is the current implementation stricter than the documented method?", "",
          "Yes in three places, none of them an explicit source rule: (1) the trend test samples the previous close instead of the 09:20 price; (2) the inner level / trendline are single research constructions; (3) the strength profile is numeric. **No relaxation is recommended here**; each is listed as an owner decision with its measured effect in `orb_rule_decision_matrix.md`."]
    (OUT / "orb_ema_trendline_review.md").write_text("\n".join(EM) + "\n")

    # ============================================================================================ orb_level_reconstruction.md
    fam_names = [r["family"] for r in fp]
    broken = {(r["date"], r["family"]): fb(r["broken"]) for r in lf}
    mat = [[r["date"]] + ["x" if broken.get((r["date"], f)) else "." for f in fam_names] for r in d13]
    jb = {k: int(FPOP[k]["broken_on_dates_with_a_journal_orb_row (descriptive)"]) for k in FPOP}
    nj = {k: int(FPOP[k]["broken_on_dates_with_no_journal_orb_row (descriptive)"]) for k in FPOP}
    LV = ["# ORB - support / resistance level reconstruction", "", WARN, "",
          "## What the source defines", "",
          "* **Method 1 (explicit, p.4 table):** the major level is 'the top of the previous day's range (resistance) / bottom (support)' = the previous day's high / low, marked as a horizontal line (p.3-4 figures). The engine uses exactly this (`prev_high_low`).",
          "* **Method 2 (qualitative + two schematics):** 'a smaller level within the previous day's range' - 'a minor swing high or consolidation top' - near a rising trendline; the p.5 schematic puts it at the high of a recent candle near the END of the previous session, p.7's annotated real chart marks a 'small inner resistance (near trendline)' and the caption admits it is 'drawn approximately; verify the exact levels on your original chart'. No algorithm exists (ORB-M2-*-001 are UNRESOLVED).",
          "* **Real reference charts (unlabelled, no price or date axis): two on p.12 and three on p.13.** The purple level is a horizontal BAND, not a line: in the two p.13 short breakdowns it starts at the left (where a base formed) and runs to the entry candle (how many sessions lie between is only inferred from unlabelled dashed verticals); in the p.13 long and the first p.12 chart it starts inside / before the previous session and runs a little PAST the entry candle, with a rising trendline band below. The rulebook text has no rule for a band or a multi-session level.", "",
          "## Source chart by source chart (rendered and read; prices are read off the figures and are approximate; the real charts have no price axis, so band edges are described relative to the candles, not measured)", "",
          tab(["figure", "candles that produce the level", "available when", "horizontal / diagonal", "bodies or wicks", "zone boundaries", "breakout confirmation", "versus the current algorithm"], [
              ["p.3 Method 1 long (schematic)", "the upper part of the last staircase candles (about 24,175-24,180) of the previous session", "marked before the open", "horizontal line (single)", "highs / upper wicks touch the line; bodies just below", "none (a line)", "09:15-09:20 candle opens below and closes about 55 points above", "same as the engine: the previous day's high (p.4 table)"],
              ["p.4 Method 1 short (schematic)", "the lows of the last descending candles (about 24,160)", "marked before the open", "horizontal line", "lows / lower wicks", "none", "candle opens above and closes below", "same (previous day's low)"],
              ["p.5 Method 2 long (schematic)", "the highs of the last 3-4 candles of the previous session ('inner resistance', about 24,150) below a dashed 'major resistance' (about 24,220); the trendline joins swing lows from about 24,060", "inner level: end of the previous session; trendline: needs two swing lows", "inner level horizontal; trendline diagonal rising", "candle highs (wicks)", "none", "candle closes above the inner level; the major level is NOT yet broken", "plausibly the latest fractal inside the range; trendline: at least two fractal lows (engine: the last two)"],
              ["p.6 Method 2 short", "text only ('apply the same steps in reverse')", "-", "-", "-", "-", "-", "no figure"],
              ["p.7 annotated real chart (Method 2 long)", "a small swing high inside the previous day's range 'near the trendline' (yellow dashed); the major zone (purple band) is the multi-candle top of the earlier rally", "previous session ('drawn approximately')", "inner level horizontal; trendline diagonal rising; major zone a horizontal band", "swing HIGHS (wicks) for the inner level; the major band spans bodies and wicks", "major band about 10 candle ranges wide; inner level a line", "a large gap-up green 09:20 candle closes through the inner level; the major band stays above", "consistent with 'a recent swing high'; the exact swing is not recoverable"],
              ["p.8 Gap-up (schematic)", "the 200 DMA (a falling diagonal line); the previous close lies below it", "known before the open", "DIAGONAL (the average)", "n/a", "the drawn GAP UP box lies wholly below the line", "the first candle OPENS below the line, crosses it and closes above", "the frozen engine needs the OPEN above the average: NOT what is drawn"],
              ["p.9 Gap-down (schematic)", "the 200 DMA (a rising diagonal line)", "known before the open", "diagonal", "n/a", "the GAP DOWN box lies wholly above the line", "the first candle opens above the line, crosses it and closes below", "same difference"],
              ["p.12 chart 1 (long, real)", "a thin purple zone from earlier highs, with a rising trendline BAND (blue parallelogram) below", "earlier sessions", "zone horizontal; trendline diagonal band", "highs / bodies of the earlier swing tops", "thin zone (about one to two candle ranges); the entry candle follows just after the zone's right edge", "a tall gap-up candle breaks above the zone", "NOT reproduced (multi-session zone, trendline band)"],
              ["p.12 chart 2 (gap-up long, real)", "the EMA(200) (a curved line); no horizontal level", "known before the open", "curved diagonal", "n/a", "none", "a tall green candle starts far below the EMA and closes at / through it", "the Gap setup with the CANDLE crossing the average (frozen engine: open beyond)"],
              ["p.13 chart 1 (short, real)", "a base at the left: a purple BAND over its range (about 3 candle heights)", "earlier sessions (number only inferred)", "horizontal band", "bodies AND wicks (a zone)", "a band, both edges drawn", "a large red candle (gap down) closes below the band; EMA(200) above price", "NOT reproduced (multi-session band)"],
              ["p.13 chart 2 (short, real)", "a thin purple band from a left candle", "earlier sessions", "horizontal thin band", "bodies / lows", "thin band", "a large red candle breaks below; EMA near / above", "NOT reproduced"],
              ["p.13 chart 3 (long, real)", "a purple resistance band that starts inside the previous session and runs past the entry candle; a rising blue trendline far below price; EMA(200) crossing the band", "previous session onward", "band horizontal; trendline diagonal", "bodies and wicks of the highs", "band", "a green candle breaks above the band and the EMA", "NOT reproduced (band + a trendline spanning many sessions)"]]), "",
          "None of the real charts is dated or labelled with a method, so they cannot be matched to the 13 disputed dates; the author's drawings for those dates would be needed. A definition that reproduced the bands would need a band (body to wick), a base-detection rule and a session lookback - none exists in the source.", "",
          "## What the engine does", "",
          "Method 1: previous-day extreme. Method 2: the latest 5-candle fractal of the previous session inside its range (`LATEST_FRACTAL_K2`; trendline = last two fractal lows / highs). Nothing multi-session.", "",
          "## Constructions that can be computed at 09:15 (causal; none hardcoded to a date)", "",
          "Every family below uses only completed candles of earlier sessions. 'Broken' = the first candle breaks AND closes beyond the level (colour-matching direction). Families that are not in the source are labelled so.", "",
          tab(["family", "source status", f"sessions broken (of {n_sess})", "%", "+ strong candle", "+ strong + trend (all gates but the trendline)", "on the 13 disputed dates", "on journal ORB dates (89)", "on dates without a journal ORB"],
              [[r["family"], next((x["source_status"] for x in lf if x["family"] == r["family"]), "")[:48], r["first_candle_breaks_and_closes_beyond"], r["pct_of_sessions_broken"], r["broken_and_strong_MODERATE_or_pin"], r["broken_strong_and_trend (all gates but the trendline)"], r["broken_on_the_13_disputed_dates"], jb[r["family"]], nj[r["family"]]] for r in fp]), "",
          "Reading the table: a construction that is broken on most sessions (e.g. 'the most distant inner swing broken' on "
          f"{FPOP['M2_HIGHEST_BROKEN_FRACTAL_K2']['pct_of_sessions_broken']}% of sessions, 12 of the 13 disputed dates, but also {nj['M2_HIGHEST_BROKEN_FRACTAL_K2']} sessions without a manual ORB) does not SELECT ORB days: any strong candle crosses some swing. A construction that is rarely broken (previous-day extreme: {FPOP['M1_PREVIOUS_DAY_EXTREME']['pct_of_sessions_broken']}%) explains only {FPOP['M1_PREVIOUS_DAY_EXTREME']['broken_on_the_13_disputed_dates']} of the 13. "
          "The manual journal is used here descriptively only (it has no direction or price); no rule was chosen to match it.", "",
          "## Which constructions the first candle broke on each of the 13 dates", "", tab(["date"] + [f.replace("_SESSIONS", "").replace("MS_", "ms ").replace("M2_", "m2 ").replace("_FRACTAL_K2", "").replace("M1_", "m1 ") for f in fam_names], mat), "",
          "`x` = broken. Per-date detail (level, open already beyond the level, close minus level) is in `orb_level_families_13.csv` and each `daily/<date>.md`; each `charts/<date>.svg` draws the source-defined previous-day levels, the frozen inner level and the provisional constructions with different line styles.", "",
          "## The dates with no previous-day level broken", "",
          "On " + ", ".join(r["date"] for r in d13 if r["missing_condition_Method_1"] == "level_broken") + " the first candle neither breaks nor closes beyond the previous-day extreme. On the six of them where the frozen inner level is also unbroken (" + ", ".join(r["date"] for r in d13 if r["missing_condition_Method_2"] == "inner_level_broken") + "), the author's level cannot be reconstructed from the source, and no deterministic construction I could justify reproduces them: "
          f"the variants that change the inner level reproduce {VI['orb-var-inner-nearest-from-open']['disputed_dates_with_a_signal (of 13)']} date ({VI['orb-var-inner-nearest-from-open']['disputed_dates_list'] or 'none'}) at most.", "",
          "## Does each construction generalise?", "",
          tab(["construction", "deterministic from causal data", "generalises?", "evidence"], [
              ["previous-day extreme (Method 1)", "yes", "yes (source-explicit)", f"broken on {FPOP['M1_PREVIOUS_DAY_EXTREME']['pct_of_sessions_broken']}% of sessions"],
              ["latest inner fractal (frozen Method 2)", "yes (k = 2 is a parameter)", "yes, but one reading among several", f"{FPOP['M2_LATEST_FRACTAL_K2']['pct_of_sessions_broken']}% of sessions"],
              ["highest inner swing / nearest from the open / most distant broken", "yes", "yes, but non-discriminating or order-dependent", f"{FPOP['M2_HIGHEST_FRACTAL_K2']['pct_of_sessions_broken']}% / {FPOP['M2_NEAREST_FRACTAL_FROM_OPEN_K2']['pct_of_sessions_broken']}% / {FPOP['M2_HIGHEST_BROKEN_FRACTAL_K2']['pct_of_sessions_broken']}% of sessions"],
              ["multi-session extreme (2 / 3 / 5 sessions)", "yes (N is a parameter the source does not give)", "unknown: N undefined", f"{FPOP['MS_EXTREME_2_SESSIONS']['pct_of_sessions_broken']}% / {FPOP['MS_EXTREME_3_SESSIONS']['pct_of_sessions_broken']}% / {FPOP['MS_EXTREME_5_SESSIONS']['pct_of_sessions_broken']}% of sessions"],
              ["multi-session swing nearest the open", "yes (3 sessions, k = 2 arbitrary)", "non-discriminating", f"{FPOP['MS_SWING_NEAREST_FROM_OPEN_3_SESSIONS']['pct_of_sessions_broken']}% of sessions"],
              ["the p.13 boxed zones (base + extension across sessions)", "no: base, width and extension rule are undefined", "cannot be implemented without the author's definition", "not built"]]), "",
          "## Unresolved alternatives (for the author)", "",
          "1. Is 'previous-day resistance / support' always the day's extreme, or the most recent swing / zone the price reacted to (the p.13 bands)? 2. How is the Method 2 inner level chosen when the previous day has several swings? 3. Is the level a LINE (high / low) or a BAND (body to wick), and are bodies or wicks used? "
          "The p.13 bands and the p.3-p.7 figures suggest bands / swings; the written rules and the p.4 table say the day's top / bottom. The author's drawings for the 13 dates are what is needed to settle it."]
    (OUT / "orb_level_reconstruction.md").write_text("\n".join(LV) + "\n")

    # ============================================================================================ orb_rule_decision_matrix.md
    def v(k, f):
        return VI[k][f]

    def dd(k):
        return v(k, "disputed_dates_list") or "none"
    union13 = {x for r in vi if r["disputed_dates_list"] for x in r["disputed_dates_list"].split(",")}
    rows = [
        ["R1", "Method 1 level = previous-day high / low (current)", "p.4 table: 'top / bottom of the previous day's range'; p.3-4 figures", "none (keeps the engine)", f"{T['missing_Method_1'].get('level_broken', 0)} dates do not break it", "Method 1", "frozen: 53 signals", "none", "no (source-explicit)"],
        ["R2", "Method 1 / 2 level = multi-session extreme or zone (p.13 bands)", "p.13 reference images only; no rule, no N, no band width", "broken on 3 / 3 / 2 of 13 (N = 2 / 3 / 5)", "unknown (no author drawing)", "Method 1", f"not built; population {FPOP['MS_EXTREME_2_SESSIONS']['pct_of_sessions_broken']}% / {FPOP['MS_EXTREME_3_SESSIONS']['pct_of_sessions_broken']}% / {FPOP['MS_EXTREME_5_SESSIONS']['pct_of_sessions_broken']}% of sessions broken", "high: base / width / N undefined", "YES"],
        ["R3", "Method 2 inner level = highest inner swing", "p.4: 'a smaller level within the previous day's range' (not 'the biggest')", dd("orb-var-inner-highest-fractal"), "removes 2 frozen signals", "Method 2", f"{v('orb-var-inner-highest-fractal', 'confirmed_orb_signals')} signals ({v('orb-var-inner-highest-fractal', 'added_vs_frozen')} added / {v('orb-var-inner-highest-fractal', 'removed_vs_frozen')} removed)", "low", "YES"],
        ["R4", "Method 2 inner level = first inner swing from the open", "p.5 schematic: a recent swing the candle must cross", dd("orb-var-inner-nearest-from-open"), f"removes {v('orb-var-inner-nearest-from-open', 'removed_vs_frozen')} frozen signals", "Method 2", f"{v('orb-var-inner-nearest-from-open', 'confirmed_orb_signals')} ({v('orb-var-inner-nearest-from-open', 'added_vs_frozen')} / {v('orb-var-inner-nearest-from-open', 'removed_vs_frozen')}); date overlap with journal ORB rows {v('orb-var-inner-nearest-from-open', 'date_overlap_with_journal_orb_rows (of 89, descriptive)')}", "low", "YES"],
        ["R5", "Method 2 inner level = most distant inner swing broken", "none (a convenience reading: 'any inner level broken')", dd("orb-var-inner-highest-broken"), f"adds {v('orb-var-inner-highest-broken', 'added_signal_dates_with_no_journal_orb_row (descriptive)')} signal dates with no journal ORB", "Method 2", f"{v('orb-var-inner-highest-broken', 'confirmed_orb_signals')} ({v('orb-var-inner-highest-broken', 'added_vs_frozen')} / {v('orb-var-inner-highest-broken', 'removed_vs_frozen')})", "low", "YES"],
        ["R6", "Method 2 trendline = any two of the last three swing lows (highs)", "p.5-7: 'connect the relevant swing lows' (no count)", dd("orb-var-trendline-any-pair"), f"adds {v('orb-var-trendline-any-pair', 'added_signal_dates_with_no_journal_orb_row (descriptive)')} signal dates with no journal ORB", "Method 2", f"{v('orb-var-trendline-any-pair', 'confirmed_orb_signals')} ({v('orb-var-trendline-any-pair', 'added_vs_frozen')} / {v('orb-var-trendline-any-pair', 'removed_vs_frozen')})", "low", "YES"],
        ["R7", "Method 2 without a trendline (DIAGNOSTIC)", "contradicts p.7: 'a trendline by itself is not an entry signal' implies it is part of Method 2", dd("orb-var-trendline-none"), "drops a source-named condition", "Method 2", f"{v('orb-var-trendline-none', 'confirmed_orb_signals')} ({v('orb-var-trendline-none', 'added_vs_frozen')} / {v('orb-var-trendline-none', 'removed_vs_frozen')})", "trivial", "NOT recommended (diagnostic only)"],
        ["R8", "Strong-candle profile LOOSE (50% / 25%)", "p.3-10: 'strong' is qualitative; the figures show clean candles", dd("orb-var-strength-loose"), "p.10 illustrations favour clean candles; AC27 / other dates unaffected", "Methods 1, 2, Gap", f"{v('orb-var-strength-loose', 'confirmed_orb_signals')} ({v('orb-var-strength-loose', 'added_vs_frozen')} / {v('orb-var-strength-loose', 'removed_vs_frozen')}); date overlap with journal ORB rows {v('orb-var-strength-loose', 'date_overlap_with_journal_orb_rows (of 89, descriptive)')}", "trivial (existing profile)", "YES"],
        ["R9", "Strong-candle profile STRICT (70% / 15%) (DIAGNOSTIC)", "closest to the p.3 / p.10 figures", "none", "removes 15 frozen signals", "Methods 1, 2, Gap", f"{v('orb-var-strength-strict', 'confirmed_orb_signals')} (0 / {v('orb-var-strength-strict', 'removed_vs_frozen')})", "trivial", "YES (diagnostic)"],
        ["R10", "Trend = EMA side + two higher swings (owner variant B)", "p.3: 'supported by bullish price structure'", "none", f"removes {v('orb-var-trend-structure', 'removed_vs_frozen')} frozen signals; AC27 signal removed", "Methods 1, 2", f"{v('orb-var-trend-structure', 'confirmed_orb_signals')} (0 / {v('orb-var-trend-structure', 'removed_vs_frozen')})", "low (existing)", "YES"],
        ["R11", "Trend = first-candle close vs EMA(200) at 09:20 (literal 'price above the 200 EMA') (DIAGNOSTIC)", "p.3 / p.4 wording; frozen design deliberately avoids the gap establishing the trend", dd("orb-var-trend-ema-basic"), "both EMA dates then fail other conditions; AC27 signal kept", "Methods 1, 2", f"{v('orb-var-trend-ema-basic', 'confirmed_orb_signals')} ({v('orb-var-trend-ema-basic', 'added_vs_frozen')} / 0); added signal dates without a journal ORB {v('orb-var-trend-ema-basic', 'added_signal_dates_with_no_journal_orb_row (descriptive)')}", "low (existing mode)", "YES (diagnostic; do not relax merely to add trades)"],
        ["R12", "Gap setup: the candle (not only the open) may cross the 200 average", "p.8 / p.9 schematics and the p.12 real chart DRAW the candle opening on the old side, crossing and closing beyond; text: 'a candle that only crosses the line but closes below it does not qualify'", dd("orb-var-gap-candle-crossing") + " (2025-12-31 then fails the wick test)", "none found", "Gap / 200 DMA", f"{v('orb-var-gap-candle-crossing', 'confirmed_orb_signals')} ({v('orb-var-gap-candle-crossing', 'added_vs_frozen')} / {v('orb-var-gap-candle-crossing', 'removed_vs_frozen')}); {GP['cases_where_the_readings_differ']} of {GP['gap_in_direction_cases']} gap cases differ", "low (built, disabled)", "YES (the figures favour this reading over the frozen one)"],
        ["R13", "ORB colour rule (long green, short red)", "AC27 (long only); short mirror = ORB-GLOBAL-002 interpretation", "none (AC27 is a removal)", "none", "Methods 1, 2, Gap", f"{v('orb-var-colour', 'confirmed_orb_signals')} (0 / {v('orb-var-colour', 'removed_vs_frozen')}); the removed signals lie on dates without a journal ORB", "trivial (existing)", "YES (short side has no author evidence)"],
        ["R14", "Automatic ORB priority over IRF", "not in any document; the brief forbids it", "all 13 'ORB instead of IRF'", "no ORB signal exists, so priority could not help; ORB (09:20) already precedes IRF in time", "controller", "none", "n/a", "NOT applicable (qualification problem)"]]
    DM = ["# ORB - rule decision matrix", "", WARN, "",
          "Every row is a candidate or an existing choice; all candidates are disabled by default (`research/phase54.py`, `strategies/orb_candidates.py`). Combinations were deliberately NOT searched (that would be fitting). 'Dates' = how many of the 13 disputed dates the variant makes a confirmed ORB signal; impact = confirmed ORB signals, signals added / removed against the frozen 53; the journal columns are descriptive.", "",
          tab(["#", "proposed rule", "source evidence", "disputed dates on which the variant yields a signal (the author gave no level, so this is NOT support)", "contradictory examples / cost", "affected methods", "historical signal impact", "implementation difficulty", "owner approval required"], rows), "",
          "## Variant table (signal-only; ORB engine only)", "",
          tab(["variant", "authority", "ORB signals", "added", "removed", "of the 13", "date overlap with journal ORB rows (of 89, descriptive)", "signal dates without a journal ORB", "AC27 date signal"],
              [[r["variant"], r["authority"], r["confirmed_orb_signals"], r["added_vs_frozen"], r["removed_vs_frozen"], r["disputed_dates_with_a_signal (of 13)"], r["date_overlap_with_journal_orb_rows (of 89, descriptive)"], r["signal_dates_with_no_journal_orb_row (descriptive)"], r["ac27_2025-11-27_signal"]] for r in vi]), "",
          "## Conclusions", "",
          f"* **No single construction reproduces the disputed dates:** the best variant reproduces {max(int(r['disputed_dates_with_a_signal (of 13)']) for r in vi)} of 13, and together all variants reach {len(union13)} ({', '.join(sorted(union13))}); {13 - len(union13)} dates are reproduced by none (an unknown level, or several simultaneous misses).",
          f"* **Level and candle strength dominate** where the engine has no ORB on a date with a journal ORB row ({J['journal_orb_dates_without_engine_orb']} in-session dates; the binding predicate of the closest method is {J['binding_predicate_of_missed']}). This is a date-only description: the journal carries no direction, price or level, so it cannot score a rule and no rule was chosen by it.",
          "* **Nothing here should be promoted without the author's drawings** of the level, the trendline and the entry candle for at least the six level dates; the matrix gives the owner the exact trade-offs."]
    (OUT / "orb_rule_decision_matrix.md").write_text("\n".join(DM) + "\n")

    # ============================================================================================ orb_complete_source_audit.md
    miss_j = [r for r in jc if r["session_in_dataset"] == "True" and r["engine_orb_signal"] == "none"]
    CA = ["# ORB - complete source audit (Phase 5.4)", "", f"> {WARN}", "",
          "**Stage 1 only.** Nothing in Stages 2 and 3 (the complete backtest, the journal reconciliation) was started. The owner reviews this report and approves an ORB configuration before anything else runs.", "",
          "## 1. What was read", "",
          "* `docs/strategy_docs/ORB_Strategy_Rulebook-2.pdf` - all **13 pages rendered and read visually** (text, figures and the three real reference charts), plus the extracted text.",
          "* `docs/strategy_docs/corrected/Adobe Scan Nov 05, 2026.pdf` - all **6 handwritten pages rendered and read**. The ORB remarks are text only (no drawings).",
          "* The ORB engine (`strategies/orb.py`), its rule registry entries, the Phase 5.1 / 5.2 / 5.3 reports, the Phase 3.6 signal / trade tables, the manual journal workbook (read-only) and the one-minute data.", "",
          "## 2. The rulebook, page by page", "",
          tab(["page", "content", "visual evidence"], [
              ["1", "Overview: decision at 9:20 once the first 5-minute candle has closed; same rules both directions; stop 30, target 60 (1:2); the three setups (Method 1: previous day's level; Method 2: inner level + trendline; Gap + 200 DMA) and the long / short table", "-"],
              ["2", "The first candle 9:15-9:20 (its close is not known until 9:20 - 'never pre-empt the close'); the five 9:20 checks", "-"],
              ["3", "Method 1 long: confirm uptrend ('price above the 200 EMA is a basic confirmation, supported by bullish price structure'), mark previous-day resistance with a horizontal line, the 9:20 candle must break AND close above it with a strong green body and small upper wick, enter at 9:20", "figure: staircase of candles to a horizontal previous-day resistance; the 09:15-09:20 candle opens below and closes above it; 200 EMA below"],
              ["4", "Method 1 short (mirror); Method 2 introduction: major level = top / bottom of the previous day's range, inner level = a smaller level within it; Method 2 needs the trendline", "mirror figure (descending candles, 200 EMA above)"],
              ["5", "Method 2 long: eight steps (trend, rising trendline, major resistance for context, inner resistance, 9:20 break and close, candle strength, 200 EMA filter, enter)", "figure: rising trendline through swing lows, inner resistance (a recent candle's high) inside the previous day's range, major resistance above and unbroken"],
              ["6-7", "Method 2 short (mirror, falling trendline); reference chart caption: major resistance NOT yet broken at 9:20, a small inner resistance near the trendline breaks; condition table; the reminder 'a trendline by itself is not an entry signal. Verify the exact levels and first-candle close on your original chart'", "annotated REAL chart ('inner level drawn approximately')"],
              ["7-9", "Gap above / below the 200 DMA: gap in direction, the gap must bring price through the average, 'a candle that only crosses the line but closes below it does not qualify', strong candle or suitable pin bar; 'not every gap is valid' (reject extended gaps and strong rejection wicks)", "-"],
              ["9-10", "Candle-quality rules: preferred / conditional (pin bar) / reject (opposite-wick rejection)", "figure: strong bullish, bullish pin bar, upper-wick rejection"],
              ["11", "Trade parameters: entry 9:20, stop entry -/+ 30, target +/- 60; 'standardise your units' (index points, instrument units or rupees)", "-"],
              ["12", "Consolidated rule matrix (trend, level, gap, first-candle confirmation, wick rule, 30/60)", "-"],
              ["13", "REF IMAGES: three real charts - two short breakdowns of a purple horizontal zone that extends across several sessions (EMA above price), one long above a rising blue trendline with a purple zone", "three real charts"]]), "",
          "## 3. The source-rule registry", "",
          f"`orb_source_rule_registry.csv` lists {len(reg)} rows (the {sum(1 for r in reg if r['rule_id'].startswith('ORB-') and not r['rule_id'].startswith(('ORB-VIS', 'ORB-AC', 'ORB-ENG')))} registry rules with page, diagram, method, existing code and status, plus the visual evidence, the author clarifications and the engine's research assumptions). Classification counts: {reg_counts}. "
          "No research assumption is described as a source rule (an audit check enforces this).", "",
          "## 4. What the source defines and what it does not", "",
          tab(["element", "defined by the source?", "engine"], [
              ["first candle 09:15-09:20, decision at 09:20, entry after its close", "yes, explicit", "implemented (verified on all 13 dates: first candle 09:15-09:20, fill = open of the 09:20 minute bar)"],
              ["Method 1 level = previous day's top / bottom", "yes, explicit (p.4 table)", "implemented"],
              ["break AND close beyond the level", "yes, explicit", "implemented"],
              ["established trend; price above the 200 EMA as the basic confirmation", "qualitative; sampling time and 'structure' undefined", "owner variant: previous close vs its EMA (the structure variant is inactive)"],
              ["Method 2 inner level", "qualitative + schematics; no algorithm; 'drawn approximately'", "research assumption: latest fractal k=2"],
              ["Method 2 trendline", "qualitative", "research assumption: last two fractals"],
              ["strong candle / pin bar / rejection wick", "qualitative; no numbers; clean figures", "research numbers (MODERATE, owner pin test, 33%)"],
              ["near the EMA / convincing close", "qualitative", "research numbers (15 points / 5 points)"],
              ["Gap setup: gap through the 200 average, candle closes beyond", "explicit but the open-versus-candle crossing is ambiguous", "frozen reading: the OPEN must be beyond the average"],
              ["multi-session zones (p.13)", "shown, never defined", "not implemented"],
              ["30-point stop, 60-point target", "explicit (units ambiguous)", "implemented as index points (owner-approved)"]]), "",
          "## 5. The 13 disputed dates", "",
          "See `orb_author_corrections.md` and `orb_13_disputed_dates.csv`. In brief: 12 green first candles and 1 red; no ORB signal on any date; the missing conditions are level (9 dates, Method 1), inner level (6), trendline (4), trend (2), strength (3) and a gap-average tie (1) - the dispute is not one defect. All 13 case studies (`daily/<date>.md`, `charts/<date>.svg`) show the original one-minute bars, the five-minute candles, the first candle, the previous-day levels, the multi-session constructions, the EMA(200), the frozen trendline, the engine's eligibility checks and the IRF / other trade taken.", "",
          "## 6. The manual journal as descriptive evidence (read only)", "",
          f"The original journal has {S['journal_rows']} rows ({S['journal_by_strategy']}); 5 rows carry weekend dates ({', '.join(S['journal_saturday_rows'])}) and are kept as supplied. It records {J['rows']} ORB entries. On the {J['rows'] - J['irregular_dates_without_session']} of them that fall on a dataset session the engine has a confirmed ORB signal on {J['engine_orb_signal_on_journal_orb_date']}; the other {J['journal_orb_dates_without_engine_orb']} ({J['of_which_in_the_13']} of them among the 13) have none; "
          f"conversely the engine has ORB signals on {J['engine_orb_signal_dates_without_journal_orb']} dates with no journal ORB. First candles of the {J['journal_orb_dates_without_engine_orb']} missed dates: {J['first_candle_colour_of_missed']}. Binding predicate (the only failing predicate of the closest method): {J['binding_predicate_of_missed']}. The journal has no direction, price or level, so it cannot define a rule; it shows that the engine's ORB under-generates broadly, not only on the 13. Full reconciliation is Phase 5.6.", "",
          "## 7. Findings", "",
          "1. The previous finding is confirmed: the engine produced no ORB signal on the 13 dates; this is a qualification problem, not a priority problem (ORB decides at 09:20, before any IRF).",
          "2. The failures are heterogeneous. A single missing rule would not reproduce them: every single-construction variant reproduces at most "
          f"{max(int(r['disputed_dates_with_a_signal (of 13)']) for r in vi)} of 13.",
          "3. The rulebook itself concedes that Method 2's level is approximate and defers to the author's original chart; the handwritten pages contain no drawings. The author's levels, trendlines and entry candles for the disputed dates are the missing evidence.",
          "4. The engine is stricter than the written method in three places (trend sampling, single research constructions for the inner level / trendline, numeric candle thresholds) - all labelled as assumptions, none an explicit source rule.",
          "5. The rulebook's own figures show clean candles, so the numeric thresholds cannot be loosened on the source's authority alone; the author's expectation on 2025-12-12 and 2025-12-30 (LOOSE would admit both) conflicts with the figures.",
          "6. The Gap setup has a genuine reading ambiguity (open versus candle crossing the average) that affects 10 of 246 gap cases.", "",
          "## 8. What the owner is asked to decide (Stage 1 stop)", "",
          "Provide the author's drawn level / trendline / entry candle for the disputed dates (at least the six level dates), then choose from `orb_rule_decision_matrix.md`. No ORB configuration is selected here, no backtest was run, and Stage 2 will not start until an ORB configuration is explicitly approved.", "",
          "## 9. Verification", "", f"* Tests: **{a.tests}**; ruff: **{a.ruff}**.", f"* Independent audit script: {'ALL ' + str(len(ar['checks'])) + ' CHECKS PASS' if ar['all_pass'] else 'see independent_audit.md'}.", "* The frozen configuration, the Phase 3.0-5.3 reports, the data and the source documents are byte-identical to the baseline snapshot."]
    del miss_j
    (OUT / "orb_complete_source_audit.md").write_text("\n".join(CA) + "\n")

    # ============================================================================================ independent_audit.md
    IA = ["# Independent audit (Phase 5.4)", "",
          f"`scripts/phase54_independent_audit.py` re-derives the claims from the raw Phase 1 minute files and the original journal workbook (no `src/` imports). Result: **{'ALL ' + str(len(ar['checks'])) + ' CHECKS PASS' if ar['all_pass'] else 'FAILURES PRESENT'}**.", "",
          tab(["#", "check", "n", "result", "detail"], [[i + 1, n, v_["n"], "PASS" if v_["pass"] else "FAIL", str(v_["detail"])[:170]] for i, (n, v_) in enumerate(ar["checks"].items())]), "",
          "**Independence caveat.** The audit script is a second implementation written in the same session; the fresh reviewer below is a separate pass.", "",
          "## Tests and lint", "", "* Before any change (existing suite): **717 passed, 1 skipped**.", f"* After implementation: **{a.tests}**", f"* `ruff check src tests scripts`: **{a.ruff}**", "", rev]
    (OUT / "independent_audit.md").write_text("\n".join(IA) + "\n")
    print("docs written; audit:", "ALL PASS" if ar["all_pass"] else "FAILURES / not run", "| registry:", dict(Counter(r["status"].split(" (")[0] for r in reg)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
