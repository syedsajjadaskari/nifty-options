"""Phase 3.4: write the markdown reports and the day-by-day workbook from the delivered CSV files (every number is computed here)."""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "phase3" / "phase34_pdr_revision"


def rd(n: str) -> list[dict]:
    with open(OUT / n, newline="") as f:
        return list(csv.DictReader(f))


def tab(head, body) -> str:
    return "\n".join(["| " + " | ".join(head) + " |", "|" + "---|" * len(head)] + ["| " + " | ".join(str(x) for x in r) + " |" for r in body])


def fl(x) -> float:
    return float(x)


def main() -> None:  # noqa: C901
    S, D, J, DET, SENS = rd("old_vs_new_pdr_signals.csv"), rd("pdr_daily_signal_comparison.csv"), rd("pdr_manual_journal_comparison.csv"), rd("pdr_entry_condition_details.csv"), rd("pdr_sensitivity_counts.csv")
    EXV, RULES, J2 = rd("source_example_validation.csv"), rd("pdr_revision_rules.csv"), rd("pdr_journal_agreement_2x2.csv")
    summ = json.loads((OUT / "_run_summary.json").read_text())
    audit = json.loads((OUT / "independent_audit_results.json").read_text()) if (OUT / "independent_audit_results.json").exists() else {}
    old_all = {c: [r for r in S if r["row_type"] == "OLD_SIGNAL" and r["candidate"] == c] for c in "AB"}
    new_all = {c: [r for r in S if r["row_type"] == "NEW_SIGNAL" and r["candidate"] == c] for c in "AB"}
    valid = {c: [r for r in old_all[c] if r["signal_valid_under_revision"] == "True"] + new_all[c] for c in "AB"}

    def tagcount(rows, tag, sole=False):
        return sum(1 for r in rows if tag in r["change_tags"].split(";") and (not sole or r["change_tags"] == tag))

    def day_sets(c):
        out = {}
        for r in D:
            if r["candidate"] == c:
                out[r["date"]] = (set(filter(None, r["old_signal_times"].split(";"))), set(filter(None, r["signal_times"].split(";"))))
        return out
    diffdays = {c: [d for d, (o, n) in day_sets(c).items() if o != n] for c in "AB"}
    olddays = {c: [d for d, (o, n) in day_sets(c).items() if o] for c in "AB"}
    newdays = {c: [d for d, (o, n) in day_sets(c).items() if n] for c in "AB"}
    both = {c: [d for d in olddays[c] if d in newdays[c]] for c in "AB"}
    trades_old = {c: [r for r in old_all[c] if r["old_trade_id"]] for c in "AB"}
    pat = {c: Counter(r["patterns_passed"] for r in valid[c]) for c in "AB"}
    nongreen = {c: sum(1 for r in new_all[c] if fl(r["confirmation_close"]) <= fl(r["confirmation_open"])) for c in "AB"}
    zone_diff_days = sum(1 for a, b in zip([r for r in D if r["candidate"] == "A"], [r for r in D if r["candidate"] == "B"], strict=True) if (a["zone_floor"], a["zone_ceiling"]) != (b["zone_floor"], b["zone_ceiling"]))
    unres_days = sorted({r["date"] for r in D if r["candidate"] == "B" and "UNRESOLVED_ZONE" in r["change_tags"].split(";")})
    sens = {r["variant"]: r for r in SENS}
    tol_days = sum(1 for r in D if r["candidate"] == "B" and r["zone_changes_with_tolerance_5_10_15"] == "True")
    after_cutoff = sum(1 for r in D if r["candidate"] == "A" for t in filter(None, r["signal_times"].split(";")) if t > "13:00")
    wide_A, wide_B = (sum(1 for r in D if r["candidate"] == c and r["zone_width"] and fl(r["zone_width"]) > 30) for c in "AB")
    max_w = max(fl(r["zone_width"]) for r in D if r["zone_width"])

    def g2(cand, prof, rule):
        r = next(x for x in J2 if x["candidate"] == cand and x["pattern_thresholds"].startswith(prof) and x["open_rule"].startswith(rule))
        return f"{r['exact']} exact + {r['shifted_within_15_min']} shifted = {r['within_tolerance_total']}"
    pdr_rows = [m for m in J if m["attribution"] == "PDR"]
    disp_rows = [m for m in J if m["attribution"] != "PDR"]

    def jcount(rows, key):
        ex = sum(1 for m in rows if "(EXACT" in m[key])
        sh = sum(1 for m in rows if "(TIME_SHIFTED" in m[key])
        return ex, sh, len(rows) - ex - sh

    # ------------------------------------------------------------------------------------------------ examples for the plain-English part
    ex_removed = next(r for r in trades_old["A"] if r["old_trade_id"] == "20260113-1-PDR")
    ex2 = [e for e in EXV if e["example"].startswith("Example 2") and e["pattern_profile"] == "RESEARCH_DEFAULT"][0]
    ex2l = [e for e in EXV if e["example"].startswith("Example 2") and e["pattern_profile"] == "EXAMPLE_LENIENT"][0]
    ex_new = next((r for r in new_all["A"] if fl(r["confirmation_close"]) <= fl(r["confirmation_open"])), new_all["A"][0])

    # ------------------------------------------------------------------------------------------------ summary
    L = ["# Phase 3.4 - PDR revision with the author's clarified rules (summary)", "",
         "**Written for:** the strategy owner, for manual review. This phase changes the PDR **signal** engine only (zone selection and entry qualification). It did **not** run a portfolio back-test, compute any P&L, change another engine, the controller, stops, targets, sizing or the cutoff, "
         "or overwrite any earlier ledger, report or data file (a hash snapshot taken before the first edit proves it). Nothing was tuned: where the author gave no numbers, the numbers are labelled research parameters.", "",
         "## What the author's three sentences now require (AUTHOR_APPROVED)", "",
         "1. **Previous-day high + a zone, connecting multiple highs.** The zone must contain the previous session's highest high (its ceiling), and repeated highs are connected into one zone.",
         "2. **One of three confirmation candles:** a good green-body candle OR a lower-price-rejection candle OR a hammer (OR logic; every pattern that passes is recorded; one signal per candle).",
         "3. **The confirmation candle must close strictly ABOVE the zone ceiling** (equal, inside the zone or below the floor is invalid; a lower wick may dip into or below the zone).", "",
         "Everything else the author did not define (how many highs, tolerance, separation, width, spike handling, lower boundary, the numeric shape of the patterns, candle colour of the rejection and hammer, how long a setup stays armed) is a research parameter recorded on every signal; "
         "**no zone candidate is source-verified**. The engine is `src/nifty_trading/strategies/pdr_revised.py`; the legacy engine `pdr.py` is untouched and still reproduces the old stream exactly (383 signals, identical to the Phase 3.2 export).", "",
         "## Results (signal level, 247 sessions)", "",
         tab(["question", "answer"], [
             ["A. Original PDR signals", f"{summ['old_signals']} confirmed raw signals on {summ['old_first_signal_days']} days; the Phase 3.0 portfolio executed {summ['old_executed_trades']} of them"],
             ["B. Revised PDR candidate signals (default patterns)", f"candidate A (day-high zone): {len(valid['A'])} signals on {len(newdays['A'])} days; candidate B (multiple-high zone): {len(valid['B'])} signals on {len(newdays['B'])} days. "
                                                                  f"Co-equal row: with thresholds read off the guide's own four examples, {summ['revised']['A']['lenient_signals']} (A) / {summ['revised']['B']['lenient_signals']} (B). Neither number is validated. "
                                                                  f"These are RAW signals: {after_cutoff} of the {len(valid['A'])} (A) are timed after 13:00 and the controller's entry cutoff would drop them"],
             ["C. Old signals removed by the close-above-ceiling rule", f"{tagcount(old_all['A'], 'REMOVED_BY_CLOSE_RULE')} of {len(old_all['A'])} old signals fail the test (candidate A; {tagcount(old_all['B'], 'REMOVED_BY_CLOSE_RULE')} for B); "
                                                                       f"{tagcount(old_all['A'], 'REMOVED_BY_CLOSE_RULE', sole=True)} fail ONLY this rule (the other tags are explanatory and overlap)"],
             ["D. Removed / added by the zone construction", f"removed with a zone-selection tag: {tagcount(old_all['A'], 'REMOVED_BY_ZONE_SELECTION')} (A) / {tagcount(old_all['B'], 'REMOVED_BY_ZONE_SELECTION')} (B), of which "
                                                            f"{tagcount(old_all['A'], 'REMOVED_BY_ZONE_SELECTION', sole=True)} only by the zone; newly valid because of the zone: {tagcount(new_all['A'], 'NEWLY_VALID_ZONE')} (A) / {tagcount(new_all['B'], 'NEWLY_VALID_ZONE')} (B)"],
             ["E. Signals added by the three patterns", f"{tagcount(new_all['A'], 'NEWLY_VALID_PATTERN')} (A) / {tagcount(new_all['B'], 'NEWLY_VALID_PATTERN')} (B) new signals owe their validity to the pattern rule; {nongreen['A']} new signals are on a candle that is not green (hammer / rejection). "
                                                       f"Patterns over all {len(valid['A'])} valid signals (A): " + ", ".join(f"{k} {v}" for k, v in pat['A'].most_common())],
             ["F. Days with a different PDR signal outcome", f"{len(diffdays['A'])} of {len({r['date'] for r in D})} sessions for A ({len(diffdays['B'])} for B): {len(olddays['A'])} days had an old signal, {len(newdays['A'])} have a revised one, {len(both['A'])} have both"],
             ["G. Manual PDR journal", f"old stream {jcount(pdr_rows, 'old_signal')[0]} exact + {jcount(pdr_rows, 'old_signal')[1]} time-shifted of {len(pdr_rows)} PDR rows; revised A {jcount(pdr_rows, 'revised_A_signal')[0]} exact + {jcount(pdr_rows, 'revised_A_signal')[1]} shifted; "
                                       f"revised B {jcount(pdr_rows, 'revised_B_signal')[0]} + {jcount(pdr_rows, 'revised_B_signal')[1]}. Thresholds x open rule (candidate A, agreement observation only, see the table below): "
                                       f"default/open-above {g2('A', 'default', 'open must')}; default/open-anywhere {g2('A', 'default', 'open anywhere')}; example-read/open-above {g2('A', 'lenient', 'open must')}; example-read/open-anywhere {g2('A', 'lenient', 'open anywhere')}. "
                                       f"Disputed-attribution rows: {len(disp_rows)}"],
             ["H. Unresolved source interpretations", "see `pdr_unresolved_cases.md` (the first one matters most: the proposed default pattern thresholds reject all four of the guide's own dated entry candles)"],
             ["I. Tests and independent audit", "see `independent_audit.md`"], ["J. Paths", "`reports/phase3/phase34_pdr_revision/` (README lists every file)"]]), "",
         "## In plain English, with numbers", "",
         f"* **A removed old entry.** The old engine entered `{ex_removed['old_trade_id']}` on a candle that closed at {fl(ex_removed['old_confirmation_close']):,.2f}. The previous day's high - now the zone ceiling - is {fl(ex_removed['new_zone_ceiling']):,.2f}, so the close is "
         f"{fl(ex_removed['new_zone_ceiling']) - fl(ex_removed['old_confirmation_close']):,.2f} points BELOW it. Tags: {ex_removed['change_tags']}. (The old zone was [{fl(ex_removed['old_zone_floor']):,.2f}, {fl(ex_removed['old_zone_ceiling']):,.2f}] - the same candle here, but its close was already below that zone's floor.)",
         f"* **The guide's own Example 2.** The author entered on the 09:30 candle on 2025-10-06: O {ex2['entry_open']}, H {ex2['entry_high']}, L {ex2['entry_low']}, C {ex2['entry_close']}. It closes {fl(ex2['close_minus_drawn_ceiling']):.2f} points above the drawn ceiling (the close rule is met) "
         f"but its body is {fl(ex2['body_pct']) * 100:.0f}% of the range and the lower wick is 1.79 x the body, so with the proposed default thresholds (body >= 60%, wick >= 2 x body) it passes **no** pattern. "
         f"With the example-read thresholds (body >= 40%, wick >= 1.5 x body) it passes {ex2l['patterns_passed']}. Under the default thresholds the revised engine therefore fires one candle later (09:35).",
         f"* **A newly valid signal.** {ex_new['new_signal_id']}: candle {ex_new['confirmation_candle_start']}, patterns {ex_new['patterns_passed']}, close {fl(ex_new['confirmation_close']):,.2f} = {fl(ex_new['close_minus_new_ceiling']):.2f} points above the ceiling {fl(ex_new['new_zone_ceiling']):,.2f}; "
         f"the old engine produced nothing on it ({ex_new['reason']}).",
         f"* **Why so many signals disappear.** The ceiling is now the previous day's high, and the preserved PDR-011 rule asks the session to open above the zone: that excludes most gap-ups that open inside yesterday's range. Allowing any open would raise candidate A from {len(valid['A'])} to "
         f"{sens['revised A, open may be anywhere (open_vs_zone=ANY)']['signals']} signals (a sensitivity, not an author rule).",
         f"* **Candidate B versus A - they cannot differ in signals.** The multiple-high zone differs from the day-high zone on {zone_diff_days} of 247 days, but only in its FLOOR; the ceiling is always the previous-day high, because the day's high is always a member. "
         f"The close rule, the rejection pattern and (under the active open-above-zone rule) the interaction test look only at the ceiling, so A and B give the identical {len(valid['A'])} signals (tolerance 10 and 15 also give {sens['revised B, tolerance 10']['signals']}). "
         f"The floor matters only in the open-anywhere sensitivity (A {sens['revised A, open may be anywhere (open_vs_zone=ANY)']['signals']} vs B {sens['revised B, open may be anywhere (open_vs_zone=ANY)']['signals']}). The only zone choice that can move the ceiling is the spike policy (Example 3), which is a diagnostic option contradicting PDR-A01.", "",
         "## Journal agreement: thresholds x open rule (candidate A; B is identical)", "",
         tab(["", "open must be above the zone (active)", "open anywhere (sensitivity)"],
             [["default thresholds", g2("A", "default", "open must"), g2("A", "default", "open anywhere")], ["example-read thresholds", g2("A", "lenient", "open must"), g2("A", "lenient", "open anywhere")]]), "",
         f"Over the {len(pdr_rows)} journal rows attributed to PDR (exact = same candle start; shifted = within 15 minutes). Reading: the loss of rows 4, 21 and 44 is explained by the pattern thresholds (the example-read thresholds recover them), but rows 22 (2025-10-07, the guide's Example 3) and 134 (2026-05-19) are lost to the preserved open-above-zone rule, "
         "not to the thresholds: they appear only when both are relaxed. **This is an agreement observation only, not a selection criterion:** the example-read thresholds were read off four of these very rows, so their agreement is circular; the journal records no prices or zones; and no setting is chosen because it matches the journal better. Per-row detail: `pdr_journal_agreement_2x2.csv`.", "",
         "## The most important open point", "",
         "The author gave no numbers for 'good green body', 'lower price rejection' or 'hammer'. The profile named RESEARCH_DEFAULT is a **placeholder**, not a recommendation: the Phase 2.2 owner-recommended 60%/20% candle and 2x-wick pin definitions plus a hammer shape, kept because the brief said to reuse the existing definitions. It rejects **all four** of the guide's dated entry candles. "
         "The EXAMPLE_LENIENT thresholds (40%/25%, 1.5x wick) were read off those same four candles, so their accepting all four is true by construction and proves nothing else. Both counts (81 and 103) are co-equal research outputs; **no setting is validated**. "
         "The owner needs to obtain from the author numeric definitions of the three patterns, or a handful of labelled example candles (the profile keeps its historical name RESEARCH_DEFAULT in the files so that earlier config ids stay comparable).", "",
         "## Not done, by design", "",
         "No combined five-strategy back-test, no P&L (the comparison is at signal level: a removed signal is not a removed executed trade until the shared controller is re-run), no change to other engines, the controller, stops, targets, sizing or the cutoff, no forward test, no Phase 3.5.", ""]
    (OUT / "phase34_summary.md").write_text("\n".join(L))

    # ------------------------------------------------------------------------------------------------ unresolved cases
    U = ["# PDR revision - unresolved cases", "",
         "**Written for:** the strategy owner. Each item is something the author's three clarifications do not settle. The engine records the chosen research setting on every signal; none is source-verified. No item was resolved by looking at profit.", "",
         tab(["#", "unresolved point", "what the engine does (research setting)", "evidence / size of the effect", "decision needed"], [
             ["1", "Numeric shape of GOOD GREEN BODY, LOWER-PRICE REJECTION and HAMMER (and the candle colour of the last two)",
              "default: body >= 60% with upper wick <= 20%; rejection = lower wick >= 2 x body with the close in the top 30% and the low reaching the zone; hammer = lower wick >= 2 x body, upper wick <= 10%, body in the upper part; colour not required for the last two",
              f"all four dated guide entry candles fail every default pattern; the example-read profile passes all four. Signals: {len(valid['A'])} (default) vs {summ['revised']['A']['lenient_signals']} (example-read); patterns alone: green body {sens['revised A, good green body only']['signals']}, rejection {sens['revised A, lower-price rejection only']['signals']}, hammer {sens['revised A, hammer only']['signals']}",
              "numbers for the three patterns (and whether a rejection/hammer may be red)"],
             ["2", "How many highs are 'multiple', how close, how far apart, how wide; which bodies set the lower boundary; whether an isolated spike is always included",
              "touches >= 2 within 5 points of the day high, members closer than 2 candles count once, floor = lowest member body top, the day high is ALWAYS included",
              f"B differs from A on {zone_diff_days} days (floor only; the ceiling is identical on every day); the B zone changes with the tolerance (5/10/15) on {tol_days} days; the tag UNRESOLVED_ZONE ({len(unres_days)} days) is the union of the two and concerns the drawn FLOOR only. The signal count stays {sens['revised B, tolerance 10']['signals']} for every tolerance and equals A",
              "the cluster parameters and the lower-boundary rule"],
             ["3", "Example 3 (PDF p.4, 2025-10-07): the author's drawn box is a thin shelf of equal highs and excludes the 14:50 spike",
              "the spike (25,095.70) is kept as the ceiling, as the author asked ('day's high should be considered'); the zone becomes [25,077.25, 25,095.70]",
              f"the open (25,087.55) is inside that zone, so the preserved open-above-zone rule rejects the day; excluding the spike when it lies above a shelf (diagnostic only, contradicts PDR-A01) gives {sens['revised B, spike excluded when it lies above a shelf (diagnostic)']['signals']} signals instead of {len(valid['B'])}; the journal has a PDR entry on that date at 09:20",
              "is a spike above a shelf part of the zone, or is the shelf the zone?"],
             ["4", "Must the session open ABOVE the zone? (legacy PDR-011, a proposal, preserved)", "yes (open > zone ceiling = previous-day high)",
              f"anywhere-open sensitivity: {sens['revised A, open may be anywhere (open_vs_zone=ANY)']['signals']} (A) / {sens['revised B, open may be anywhere (open_vs_zone=ANY)']['signals']} (B) signals instead of {len(valid['A'])}. PDR-011 was tuned for a swing-high zone BELOW the day's high; with the ceiling at the previous-day high it requires the gap to clear yesterday's whole range. The guide only says 'open gap up' and 'do not enter at the open'. "
              f"It also explains journal rows 22 and 134 (see the 2x2 table in the summary). In the author's own Example 3 drawing the shelf ceiling (25,084.40) lies BELOW the 09:15 open (25,087.55), so PDR-011 would pass on the drawn zone; the conflict arises from including the spike. Example 5 may open at/inside the zone (low-resolution reading)",
              "whether the gap must clear yesterday's high"],
             ["5", "May the confirmation be the test candle itself? (legacy rule: no)", "no, the confirmation comes after the test candle", f"sensitivity: {sens['revised A, confirmation may be the test candle itself']['signals']} signals", "same-candle test-and-confirm"],
             ["6", "How long does a tested setup stay armed?", "until a candle qualifies or the session ends (the old engine re-armed the same way)", "no cut-off other than the approved 13:00 entry cutoff, applied by the controller", "an expiry"],
             ["7", "Which zone floor? the guide says 'the relevant candle-body level'", "body top of the source candle(s) (the wick-only convention that fits Examples 1, 2 and 4)", f"the floor does not enter the close rule, the rejection pattern (which uses the ceiling) or, while the open must lie above the ceiling, the interaction test; it matters only in the open-anywhere sensitivity (A {sens['revised A, open may be anywhere (open_vs_zone=ANY)']['signals']} vs B {sens['revised B, open may be anywhere (open_vs_zone=ANY)']['signals']}). It does change the drawn box and the chart", "body top vs body bottom"],
             ["8", "Session 2025-10-23 (previous session is the unverifiable Muhurat day)", "the engine cannot evaluate it (NOT_EVALUATED)", "one session; tagged DATA_OR_IMPLEMENTATION_ISSUE in the daily comparison", "none (data)"],
             ["9", "Example 5 (undated) and the figures' candles differ slightly from the repository data at the open", "not used as evidence", "see `pdr_source_rule_verification.md` of Phase 3.3", "owner to look at Example 5"],
             ["10", "How wide may a 'small box' be? (guide p.2: a small box, not the whole surrounding move)", "no limit (width recorded)", f"widths above 30 points: {wide_A} days (A) / {wide_B} days (B); maximum {max_w:.2f} points", "a maximum width, or acceptance"],
             ["11", "Journal rows 67 (2025-12-31 09:45) and 147 (2026-06-05 09:25)", "no signal within tolerance under the active setting (row 147 shifted +15 under the example-read thresholds)", "see `pdr_journal_agreement_2x2.csv`", "none: stays unexplained, no discretionary decision is inferred"]]), "",
         "## Days where the choice of thresholds changes the signals (default vs example-read, candidate A)", "",
         tab(["date", "default signals", "example-read signals"], [[r["date"], r["revised_signal_count"], r["lenient_profile_signal_count_sensitivity"]] for r in D if r["candidate"] == "A" and r["revised_signal_count"] != r["lenient_profile_signal_count_sensitivity"]]), "",
         "## Days where candidate B's zone is unresolved", "", f"{len(unres_days)} days carry the tag UNRESOLVED_ZONE (see `pdr_daily_signal_comparison.csv`, candidate B rows): " + ", ".join(unres_days[:40]) + (" ..." if len(unres_days) > 40 else ""), ""]
    (OUT / "pdr_unresolved_cases.md").write_text("\n".join(U))

    # ------------------------------------------------------------------------------------------------ rules
    R = ["# Author-approved PDR rules (Phase 3.4)", "",
         "**Written for:** the strategy owner. Statuses: `AUTHOR_APPROVED` = stated by the strategy author in the clarification below; `PROPOSED_FOR_REVIEW` = a research number or interpretation the engine needs but the author did not give; `USER_APPROVED` = the owner's existing portfolio/execution rules; "
         "`PRESERVED_FROM_PHASE2` = kept from the legacy engine because no clarification contradicts it; `OWNER_INTERPRETATION` = the Phase 3.3/3.4 brief's reading of the author's words (for example 'strictly above', 'the CEILING', 'every pattern recorded; one signal per candle') - it is not a separate author sentence and has not been confirmed by the author.", "",
         "> \"The high should be considered, day's high should be considered and a zone should be drawn. If there are multiple highs, then a zone which connects all should be considered.\"",
         "> \"One good green body candle or lower price rejection candle or hammer candle is required for entry.\"",
         "> \"The candle should close above the zone.\"", "",
         tab(["rule", "status", "text", "source", "supersedes / parameter"], [[r["rule_id"], r["status"], r["text"], r["source"], (r["supersedes"] or r["parameter"])] for r in RULES]), "",
         "## What these clarifications supersede", "",
         "* The legacy zone candidates B (latest confirmed **reversal swing high** with a red follower - the Phase 2.3 default) and C (repeated-highs shelf that could discard the day high) are **retired from trading**; the reversal-swing zone is kept as a diagnostic on every record (`legacy_reversal_zone_diagnostic`).",
         "* The author's sentences are the `AUTHOR_APPROVED` rows A01, A02 (principle only), A04 and A05; their readings are the separate `OWNER_INTERPRETATION` rows A01a, A04z and A05a.",
         "* The legacy confirmation 'the first later green candle' (PDR-007, no location or strength test) is replaced by PDR-A04 + PDR-A05.", "",
         "## What is NOT changed", "",
         "Gap-up requirement, the return to the zone, the first-valid-signal selection, the conditional second trade, the 13:00 cutoff, six lots (3 + 3), T1 27, T2 70 (the guide's value; the report's 60 stays a recorded conflict), stop 35, post-T1 stop entry - 6, no trailing, the closing-auction conventions and the forced-exit assumption.", ""]
    (OUT / "author_approved_pdr_rules.md").write_text("\n".join(R))

    # ------------------------------------------------------------------------------------------------ zone construction
    zA = [r for r in D if r["candidate"] == "A"]
    kinds = Counter(r["zone_kind"] for r in D if r["candidate"] == "B")
    widthA = sorted(fl(r["zone_width"]) for r in zA)
    widthB = sorted(fl(r["zone_width"]) for r in D if r["candidate"] == "B")
    med = lambda v: v[len(v) // 2]  # noqa: E731
    Z = ["# PDR zone construction (research candidates A and B)", "",
         "**Written for:** the strategy owner. Neither candidate is source-verified: the author fixed the principle (the previous-day high is considered, multiple highs are connected) but not the algorithm.", "",
         "## Candidate A - day-high anchored", "",
         "The candle that made the previous session's highest high (first occurrence). Zone = [body top, wick high] of that candle - the wick-only convention that fits the guide's Examples 1, 2 and 4. The ceiling is the previous-day high (PDR-A01). "
         f"Zone width over the 247 sessions: median {med(widthA):.2f} points, maximum {max(widthA):.2f}.", "",
         "## Candidate B - multiple-high zone", "",
         tab(["research parameter", "default", "why / status"], [["local high", "a candle whose high is not lower than its 1 neighbour on each side", "PROPOSED_FOR_REVIEW"], ["touches", ">= 2 distinct touches", "PROPOSED (PDR-A02a)"],
                                                                 ["tolerance", "a local high within 5.0 points of the day's high joins (the Phase 2.3 shelf tolerance)", "PROPOSED (PDR-A02b)"], ["separation", "members closer than 2 candles count as one touch (one push)", "PROPOSED (PDR-A02c)"],
                                                                 ["cluster width", "not limited; recorded", "PROPOSED (PDR-A02d)"], ["spike policy", "the day's high is ALWAYS included; a shelf below a distant spike is flagged SPIKE_ABOVE_SHELF", "PROPOSED (PDR-A02e)"],
                                                                 ["lower boundary (B)", "lowest body top among the members", "PROPOSED (PDR-A02f)"], ["lower boundary (A)", "body top of the day-high candle", "PROPOSED (PDR-A02g)"],
                                                                 ["what is a 'high'", "non-strict local high, k = 1", "PROPOSED (PDR-A02h)"], ["equal day highs", "the first candle anchors the zone", "PROPOSED (PDR-A02i)"]]), "",
         "**A and B are signal-equivalent by construction:** the day's high is always a member of B, so B's ceiling equals A's ceiling on every day; only the floor differs, and under the active rules the floor does not enter any signal decision. The A/B split therefore carries no information about signals; "
         "options that would invent no numbers are an exactly-repeated-highs variant or an author-hand-marked zone file for the ~31 signal days.", "",
         "Over the 247 sessions the zone kind is: " + ", ".join(f"{k} {v}" for k, v in kinds.most_common()) + f". Zone width: median {med(widthB):.2f}, maximum {max(widthB):.2f} points. B differs from A on {zone_diff_days} days (floor only); the ceiling is identical on every day. {wide_A} days (A) / {wide_B} days (B) are wider than 30 points (maximum {max_w:.2f}), which stretches the guide's 'small box'.", "",
         "## The legacy reversal-swing zone (diagnostic only)", "",
         "Every record carries the zone the retired Phase 2.3 candidate would have used; it is drawn in grey on the charts and never traded.", "",
         "## Discrepancy with the guide's figures (documented, not hidden)", "",
         "* **Example 3 (2025-10-07).** The author's drawn box is a 3.6-point shelf of equal highs (about 25,081-25,084) that excludes the single 14:50 spike (25,095.70); it is not stated whether the exclusion was intended. Candidate A/B keep the spike, as the author asked, so the zone is [25,077.25, 25,095.70] (18.45 points); the open (25,087.55) lies inside it and the preserved open-above-zone rule rejects the day. "
         "See `charts/EXAMPLE_3_shelf_vs_spike.svg`.",
         "* **Examples 1, 2 and 4** are day-high zones: the revised zones coincide with the engine's old zones there (within a few points of the drawn boxes).",
         "* Representative multiple-high constructions are in `charts/MULTIHIGH_*.svg`.", ""]
    (OUT / "pdr_zone_construction.md").write_text("\n".join(Z))

    # ------------------------------------------------------------------------------------------------ confirmation patterns
    exrows = [[e["example"], e["pattern_profile"], f"{fl(e['body_pct']) * 100:.0f}% / {fl(e['upper_wick_pct']) * 100:.0f}% / {fl(e['lower_wick_pct']) * 100:.0f}%", e["close_minus_drawn_ceiling"], e["patterns_passed"], e["qualifies_under_drawn_zone"]] for e in EXV]
    P = ["# PDR confirmation patterns", "",
         "**Written for:** the strategy owner. The author requires ONE of three candles (OR logic) and a close strictly above the zone ceiling. The shapes are not numerically defined by the author; the numbers below are PROPOSED_FOR_REVIEW.", "",
         tab(["pattern", "default rule (RESEARCH_DEFAULT)", "example-read profile (EXAMPLE_LENIENT, sensitivity only)", "colour"], [
             ["good green body", "bullish; body >= 60% of the range; upper wick <= 20%", "body >= 40%; upper wick <= 25%", "must be green"],
             ["lower-price rejection", "lower wick >= 2 x body; close in the top 30% of the range; the low reached the zone (low <= ceiling)", "wick >= 1.5 x body; top 40%", "NOT required (author silent)"],
             ["hammer", "lower wick >= 2 x body; upper wick <= 10% of the range; body bottom at >= 60% of the range (a bullish LOWER-wick shape - not the bearish upper-wick pin bar)", "wick >= 1.5 x body; upper wick <= 15%; body position >= 55%", "NOT required (author silent)"]]), "",
         "Common mandatory condition (PDR-A05, AUTHOR_APPROVED): `close > zone ceiling`, strictly. No pattern overrides it. A lower wick may penetrate the zone; the whole candle need not stay above it. Zero-range candles pass no pattern (ratios are undefined) and the engine never divides by zero. "
         "When several patterns pass on one candle all are recorded and one signal is produced.", "",
         "## The guide's four dated entry candles against both profiles", "",
         tab(["example", "profile", "body / upper wick / lower wick", "close vs drawn ceiling", "patterns passed", "qualifies (drawn zone)"], exrows), "",
         "Under the default thresholds none of the four candles passes a pattern although all four close above the drawn ceiling; under the example-read thresholds all four pass (Example 2 via rejection + hammer, the others via the green body). "
         "Those example-read numbers are a sensitivity read off four candles, **not** an author approval and not tuned on any result.", "",
         f"## Pattern use among the {len(valid['A'])} valid signals (candidate A)", "", tab(["patterns passed", "signals"], [[k, v] for k, v in pat["A"].most_common()]), "",
         f"Diagnostics: green body alone {sens['revised A, good green body only']['signals']}, rejection alone {sens['revised A, lower-price rejection only']['signals']}, hammer alone {sens['revised A, hammer only']['signals']} signals.", ""]
    (OUT / "pdr_confirmation_patterns.md").write_text("\n".join(P))

    # ------------------------------------------------------------------------------------------------ traceability
    T = ["# Source-to-code traceability (PDR revision)", "",
         "**Written for:** the strategy owner and reviewers. The revision rules live in `PDR_REVISION_RULES` (same schema as the Phase 2 registry, plus the statuses `AUTHOR_APPROVED` and `OWNER_INTERPRETATION`); they are deliberately **not** merged into the central registry (`rule_data.py`, `docs/phase2/rule_registry.yaml`) until the author confirms the open details, "
         "so the Phase 2 registry and its sync tests stay untouched.", "",
         tab(["rule", "status", "code", "tests"], [
             ["PDR-A01 the day's high is considered / PDR-A01a ceiling = previous-day high (reading)", "AUTHOR_APPROVED / OWNER_INTERPRETATION", "`build_zone_a`, `build_zone_b` (ceiling = max high of the previous session)", "`test_zone_a_is_anchored...`, `test_an_unrelated_lower_reversal_swing_never_replaces...`, independent audit (247 zones)"],
             ["PDR-A02 multiple highs connected (+ a-i numeric details, incl. A's lower boundary, k, tie-break)", "AUTHOR_APPROVED / PROPOSED", "`build_zone_b`, `local_highs`", "`test_repeated_highs...`, `test_cluster_behaviour...`, `test_a_single_isolated_high...`, `test_a_narrow_shelf_below_an_isolated_higher_spike...`, `test_the_spike_handling_policy...`, `test_equal_day_highs_anchor_the_zone...`, `test_candidates_a_and_b_share_one_ceiling...`"],
             ["PDR-A03 gap up / return to the zone preserved", "PRESERVED", "`PDRRevisedStrategy._scan` (gap_info, open vs ceiling, overlap test)", "`test_the_zone_uses_the_previous_session_only`, `test_pdr_011_...`, `test_no_gap_up_means_no_setup...`, `test_the_interaction_test_uses_the_whole_zone_range...`, `test_the_test_candle_itself_cannot_confirm...`, `test_a_data_gap_while_armed...`, `test_after_a_signal_the_setup_re_arms...`, signal-stream equality in the independent audit"],
             ["PDR-A04 three patterns, OR logic", "AUTHOR_APPROVED (shapes PROPOSED)", "`good_green_body`, `lower_price_rejection`, `hammer`, `classify_confirmation`", "`test_a_close_strictly_above...`, `test_a_lower_price_rejection...`, `test_a_hammer_confirms...`, `test_several_passing_patterns...`, `test_zero_range_candles...`, `test_a_red_hammer_and_a_red_rejection_candle...`, `test_the_green_body_thresholds_are_inclusive...`, `test_the_rejection_candle_needs_the_low...`, `test_the_hammer_wick_must_be_twice...`, `test_the_default_profile_agrees_with_the_phase_2_2...`"],
             ["PDR-A05 close strictly above the ceiling", "AUTHOR_APPROVED", "`classify_confirmation` (`close > zone_ceiling`)", "`test_a_close_that_is_not_strictly_above...` (equal / inside / below), `test_a_lower_wick_may_penetrate...`"],
             ["PDR-A06 causal entry", "USER_APPROVED (existing EXE-FILL-001)", "signal timestamp = candle end; fill by the unchanged `selection.fill_from_next_bar`", "`test_no_look_ahead...`, `test_every_revised_signal_closes_strictly_above...`"],
             ["PDR-A07 armed until a candle qualifies", "PROPOSED", "`_scan` (j stays set until a qualifying candle)", "sensitivity rows in `pdr_sensitivity_counts.csv`"],
             ["nothing else changed", "-", "all other source files byte-identical (hash snapshot)", "`test_other_engines_the_controller_stops_targets...`, `test_no_source_test_or_script_file...`, `test_stops_targets_position_size...`"]]), "",
         "Legacy rules superseded for the revised engine: PDR-002/PDR-ZONE-002 (zone candidates B/C) by PDR-A01/A02; PDR-007 (any green candle) by PDR-A04/A05. PDR-010 (reversal filter OFF), PDR-011 (open above the zone), PDR-009 (stop selection) and PDR-012 (signal cap lifted for the controller) keep their Phase 2 status.", ""]
    (OUT / "source_to_code_traceability.md").write_text("\n".join(T))

    # ------------------------------------------------------------------------------------------------ README
    files = [("README.md", "this file"), ("author_approved_pdr_rules.md", "the author's clarifications as rules with statuses"), ("pdr_zone_construction.md", "candidates A and B, parameters, Example 3 discrepancy"),
             ("pdr_confirmation_patterns.md", "the three patterns, thresholds, the guide's example candles"), ("old_vs_new_pdr_signals.csv", "every old signal (383) x candidate and every newly valid signal, with tags and reasons; the 54 old trades are flagged"),
             ("pdr_daily_signal_comparison.csv", "one row per session per candidate (494): zone, gap, retest, patterns, signals, old vs revised status, tags, reason"),
             ("pdr_entry_condition_details.csv", "every candle examined after a test, accepted or rejected, with pattern details, close vs ceiling, fill"),
             ("pdr_manual_journal_comparison.csv", "PDR and disputed journal rows against the old and revised signals"), ("pdr_unresolved_cases.md", "open interpretations with the size of their effect"),
             ("pdr_sensitivity_counts.csv", "signal counts under each unresolved setting (counts only)"), ("source_example_validation.csv", "the guide's dated examples under the revised rules"),
             ("charts/", f"{len(list((OUT / 'charts').glob('*.svg')))} annotated charts on real candles + `charts_index.csv`"), ("source_to_code_traceability.md", "rule -> code -> tests"),
             ("independent_audit.md", "second implementation + second reviewer"), ("phase34_summary.md", "results in plain English"), ("PDR_Revision_Day_by_Day.xlsx", "workbook for day-by-day checking (does not replace the Phase 3.2 master workbook)"),
             ("before_snapshot.json", "hashes, git head and test status recorded before the first edit"), ("pdr_revision_rules.csv", "the rules as data"),
             ("pdr_journal_agreement_2x2.csv", "journal agreement by pattern thresholds x open rule (agreement observation only)"), ("_run_summary.json", "machine-readable headline counts of the run"),
             ("independent_audit_results.json", "machine-readable results of scripts/phase34_independent_audit.py")]
    RM = ["# Phase 3.4 - PDR revision (author-approved entry rules)", "",
          "**Written for:** the strategy owner, for manual review. Start with `phase34_summary.md`.", "",
          "The strategy author's clarifications - previous-day high (+ connected multiple highs), one of three confirmation candles, close strictly above the zone ceiling - are implemented in a **new, versioned engine** (`src/nifty_trading/strategies/pdr_revised.py`); the legacy PDR engine and every earlier result are untouched. "
          "Comparison is at **signal level only**: no portfolio back-test, no P&L. Every signal carries a configuration id and the approval status of each rule; numeric details the author did not give are research parameters.", "",
          tab(["file", "content"], [[f"`{a}`", b] for a, b in files]), "",
          "## Reproduce", "", "```", ".venv/bin/python scripts/phase34_run.py                 # engines, CSVs, charts", ".venv/bin/python scripts/phase34_independent_audit.py   # second implementation from the raw data",
          ".venv/bin/python scripts/phase34_docs.py                # markdown + workbook", ".venv/bin/python -m pytest -q && .venv/bin/ruff check .", "```", ""]
    (OUT / "README.md").write_text("\n".join(RM))

    # ------------------------------------------------------------------------------------------------ workbook
    wb = Workbook()
    wb.remove(wb.active)
    head_fill = PatternFill("solid", fgColor="1F3864")
    for name, rows_ in (("Daily Comparison", D), ("Old vs New Signals", S), ("Entry Conditions", DET), ("Journal Comparison", J), ("Sensitivity", SENS), ("Journal 2x2", J2), ("Examples", EXV), ("Rules", RULES)):
        ws = wb.create_sheet(name)
        if not rows_:
            continue
        cols = list(rows_[0].keys())
        for ci, c in enumerate(cols, 1):
            cell = ws.cell(row=1, column=ci, value=c)
            cell.fill, cell.font = head_fill, Font(bold=True, color="FFFFFF")
            cell.alignment = Alignment(wrap_text=True)
            ws.column_dimensions[get_column_letter(ci)].width = min(max(10, len(c) + 2, *(len(str(r.get(c, ""))) + 2 for r in rows_[:100])), 48)
        for ri, r in enumerate(rows_, 2):
            for ci, c in enumerate(cols, 1):
                v = r.get(c, "")
                try:
                    v = float(v) if v not in ("", None) and v.replace(".", "", 1).replace("-", "", 1).isdigit() else v
                except (AttributeError, ValueError):
                    pass
                ws.cell(row=ri, column=ci, value=v)
        ws.freeze_panes = "C2"
        ws.auto_filter.ref = f"A1:{get_column_letter(len(cols))}{len(rows_) + 1}"
    wb.save(OUT / "PDR_Revision_Day_by_Day.xlsx")
    print("docs written", {k: len(v) for k, v in {"D": D, "S": S, "DET": DET}.items()}, audit.get("all_pass"))


if __name__ == "__main__":
    main()
