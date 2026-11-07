"""Phase 5.1: match every handwritten correction to the engine and to the historical candles and write the reconciliation outputs.

Inputs (read-only): all_author_corrections.csv + evidence/<date>.json (scripts/phase51_transcription.py, phase51_evidence.py), the Phase 3.6 tables, the rule registry, the manual journal comparison.
The measurements (candle geometry, EMA space, readings of the author's wording) are computed by scripts/phase51_diagnostics.py; the CONCLUSIONS below are my analysis of those measurements and are written out in full
so that each can be challenged. Nothing here changes a strategy; no profit is computed.

Outputs under reports/phase5/phase51_author_corrections/: date_by_date_reconciliation.csv, correction_classifications.csv, strategy_selection_conflicts.csv, manual_journal_comparison.csv, daily/<date>.md,
charts/<date>.svg, Author_Corrections_Verification.xlsx.
"""

from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import phase51_diagnostics as D  # noqa: E402

OUT = ROOT / "reports" / "phase5" / "phase51_author_corrections"
P36 = ROOT / "reports" / "phase3" / "phase36_body_based_pdr"
VALID_CLASSES = {"CONFIRMED_SOFTWARE_BUG", "MISSING_AUTHOR_RULE", "WRONG_STRATEGY_SELECTION", "CANDLE_CONFIRMATION_MISMATCH", "SUPPORT_RESISTANCE_MISMATCH", "EMA_FILTER_MISMATCH", "ENTRY_TIMING_MISMATCH",
                 "AUTHOR_DISCRETION_UNRESOLVED", "DATA_DIFFERENCE", "JOURNAL_INCONSISTENCY", "NO_DISCREPANCY_FOUND"}

# id: (classes, category, author_correct_under_existing_rules, engine_correct_under_existing_rules, missing requirement / root cause, new rule needed, objectively implementable now, owner approval, rule refs)
# category: A = implementation defect, B = explicit new author rule, C = date-specific / discretionary, N = nothing to change
C = {
    "AC01": (["MISSING_AUTHOR_RULE", "CANDLE_CONFIRMATION_MISMATCH", "ENTRY_TIMING_MISMATCH"], "C", "No: the IRF guide has no entry-candle strength test and does not say which red candle supplies the resistance",
             "Yes: the engine confirmed Method 2B on a red candle whose body is 8.2% of its range (85.8% upper wick); IRF-M2B-003 asks only for a red candle closing back below the resistance (resistance = first-push top, a proposal)",
             "the author's clarification that the entry candle must have a 60+ body and that the support / resistance is that of the first red candle outside the range", "yes: 'first red candle S/R + entry-side body >= 60'", "not yet: the wording has several readings (see the readings table)", "YES", "IRF-M2B-001/002/003, IRF-GLOBAL-005"),
    "AC02": (["CANDLE_CONFIRMATION_MISMATCH", "ENTRY_TIMING_MISMATCH"], "C", "Partly: the source rule PDR-007 says 'wait for a green candle after the test'; the drawing shows the green candle that itself tests the zone as the entry",
             "Yes under PDR-A07 (a proposal): the confirmation may not be the interaction candle", "whether the green candle that tests the zone may itself be the confirmation (engine switch pdr_green_may_be_interaction_candle = False)", "no new rule: an existing proposal switch", "yes (switch), but it is an owner decision", "YES", "PDR-007, PDR-A07, PDR-A04"),
    "AC03": (["MISSING_AUTHOR_RULE", "SUPPORT_RESISTANCE_MISMATCH"], "C", "Cannot be decided: 'first red candle outside the 5-minute range' is not defined (fully above vs only the close above)", "Yes under the existing proposals (swing / first-push levels)",
             "which red candle supplies S/R in Method 2", "yes: 'S/R of the first red candle outside the range'", "no: two readings give 11:15 / 11:20 (and the engine 10:40)", "YES", "IRF-M2A-001, IRF-M2B-001"),
    "AC04": (["AUTHOR_DISCRETION_UNRESOLVED", "SUPPORT_RESISTANCE_MISMATCH"], "C", "Cannot be decided: the ORB inner level / trendline have no objective construction (ORB-M2-LONG-001 UNRESOLVED)", "Not decidable either way: the ORB Method 2 inner level and trendline are not defined in the source (orb.py says so); the engine's PROPOSED trendline test invalidated it. No ORB signal existed, so the controller chose nothing wrongly",
             "an objective inner level and trendline for ORB Method 2", "yes: an objective ORB-M2 inner level / trendline", "no", "YES", "ORB-M2-LONG-001/005"),
    "AC05": (["JOURNAL_INCONSISTENCY", "AUTHOR_DISCRETION_UNRESOLVED"], "C", "No: RF-004 (explicit source rule) rejects a gap-up open above yesterday's high; the open is 41.6 points above it", "Yes: the RF engine applied RF-004",
             "either the author reads 'yesterday's range' differently or RF-004 is not meant to apply", "only if the owner/author withdraws or redefines RF-004", "no", "YES", "RF-004, RF-008, RF-013"),
    "AC06": (["AUTHOR_DISCRETION_UNRESOLVED"], "C", "Cannot be decided: no previous-day level was broken by the first candle and no ORB record was produced", "Not decidable: no ORB setup was produced, but Method 2's inner level / trendline is not source-defined, so the engine's silence follows from an undefined rule and does not show the author wrong", "the level or condition the author used to see an ORB", "unknown", "no", "YES", "ORB-M1-LONG-002, ORB-M2-LONG-001"),
    "AC07": (["ENTRY_TIMING_MISMATCH", "CANDLE_CONFIRMATION_MISMATCH", "MISSING_AUTHOR_RULE"], "C", "Consistent with the author's clarification: the engine's failure candle has a 46.9% body (she writes 40%), and under the first-red-candle reading the entry is the 09:45 candle (signal 09:50), i.e. later",
             "Yes under the guide (IRF-M1-004: no body test)", "the entry-candle body threshold (60+ here, '<50' in AC32, 40% quoted here)", "yes: entry-candle body threshold", "no: the threshold is stated three different ways", "YES", "IRF-M1-002/004, IRF-GLOBAL-005"),
    "AC08": (["ENTRY_TIMING_MISMATCH", "SUPPORT_RESISTANCE_MISMATCH", "MISSING_AUTHOR_RULE"], "C", "Consistent with the author's wording: the first-red-candle reading enters at 10:15, earlier than the engine's 11:10", "Yes under the existing proposals", "S/R of the first red candle", "yes: the first-red-candle rule", "no (ambiguous)", "YES", "IRF-M2A-001/002"),
    "AC09": (["ENTRY_TIMING_MISMATCH", "SUPPORT_RESISTANCE_MISMATCH", "MISSING_AUTHOR_RULE"], "C", "Consistent with the author's wording: the first-red-candle reading enters at 10:05 / 10:10, earlier than the engine's 10:40", "Yes under the existing proposals", "S/R of the first red candle", "yes: the first-red-candle rule", "no (ambiguous)", "YES", "IRF-M2B-001/002/003"),
    "AC10": (["CANDLE_CONFIRMATION_MISMATCH", "ENTRY_TIMING_MISMATCH"], "C", "Consistent with the legacy PDR-007 wording ('wait for a green candle', replaced by PDR-A04 in Phase 3.4) and with the author's 'first green candle': the 09:30 candle is the first green candle that closes above the zone ceiling", "Yes under the PDR-A04 thresholds (proposed): the 09:30 candle is no 'good green body' (31.9%) and no 2x hammer (1.8x)",
             "the numeric thresholds of 'good green body / hammer' (proposals, not given by the author)", "yes: replace / loosen the pattern thresholds", "no", "YES", "PDR-007, PDR-A04, PDR-A04a/b/c"),
    "AC11": (["CANDLE_CONFIRMATION_MISMATCH", "ENTRY_TIMING_MISMATCH"], "C", "Consistent: the 09:20 candle is green, body 63.1%, closes 26.45 points above the ceiling", "Yes under the proposed thresholds: its upper wick is 21.7% (limit 20%)",
             "the upper-wick limit of 'good green body' (proposal)", "yes: loosen the thresholds", "no", "YES", "PDR-A04a"),
    "AC12": (["AUTHOR_DISCRETION_UNRESOLVED"], "C", "Cannot be decided: no previous-day level was broken and no ORB record exists", "Not decidable: no ORB setup was produced, but Method 2's inner level / trendline is not source-defined (the first candle is green with a 98.7% body)", "the level or trend condition the author used", "unknown", "no", "YES", "ORB-M2-LONG-001"),
    "AC13": (["EMA_FILTER_MISMATCH", "MISSING_AUTHOR_RULE", "ENTRY_TIMING_MISMATCH"], "B", "Yes, measurably: the engine's entry (09:45) is 2.93 points above the 5-minute EMA(200), which lies between the entry and target 1", "Yes under the written rules: no EMA-distance rule exists for IRF",
             "an IRF short whose EMA(200) lies less than 27 points below the entry must wait for a close below the EMA", "yes: 'EMA space < 27 -> wait for the EMA break'", "partly: 'skip' vs 'defer until the EMA break' are different rules", "YES", "(none: new author rule)"),
    "AC14": (["CANDLE_CONFIRMATION_MISMATCH"], "C", "Cannot be decided: the ORB candle-strength thresholds are proposals (body 26.7%, upper wick 29.9%)", "Yes under the proposed 60% / 20% thresholds", "the ORB strength thresholds", "yes: ORB strength thresholds", "no", "YES", "ORB-M1-LONG-003, ORB-CANDLE-001"),
    "AC15": (["EMA_FILTER_MISMATCH", "CANDLE_CONFIRMATION_MISMATCH"], "C", "Cannot be decided: the 'established trend' is a proposal; the first candle's body is 22.9%", "Yes under the approved trend variant (TREND-EMA-001: previous close vs EMA)", "the trend filter and the strength threshold", "yes", "no", "YES", "ORB-TREND-001/002, TREND-EMA-001"),
    "AC16": (["EMA_FILTER_MISMATCH", "CANDLE_CONFIRMATION_MISMATCH", "AUTHOR_DISCRETION_UNRESOLVED"], "C", "Cannot be decided (ORB); the remark 'IRF activation is also wrong' names no reason", "Yes under the written rules", "trend filter / candle strength for ORB; the reason the IRF is wrong is not stated", "unknown", "no", "YES", "ORB-TREND-001, ORB-GAP-LONG-004"),
    "AC17": (["NO_DISCREPANCY_FOUND"], "N", "Yes - and the engine did exactly this", "Yes: 20251107-1 is an IRF Method 1 trade (stopped out), 20251107-2 a PDS Method 2 second trade", "none found; the red-star sentence beneath it is incomplete on the scan", "none", "n/a", "NO (but see G01)", "DAY-SL-001"),
    "AC18": (["EMA_FILTER_MISMATCH", "MISSING_AUTHOR_RULE", "ENTRY_TIMING_MISMATCH"], "B", "Yes, measurably: the EMA is 25.27 points below the engine's entry, i.e. between entry and target 1", "Yes under the written rules", "the same EMA-space rule as AC13 (written twice, consistently)", "yes: the AC13 / AC18 rule", "partly (skip vs defer)", "YES", "(none: new author rule)"),
    "AC19": (["MISSING_AUTHOR_RULE", "AUTHOR_DISCRETION_UNRESOLVED"], "C", "Partly: the 09:25 candle closes below the initial-range low (and the session low), a boundary the guide leaves undefined (IRF-M1-003)", "Yes only under the proposal default m1_close_below_irl_counts_as_inside = False (IRF-M1-003 is unresolved in the source)",
             "(a) whether a failure candle closing BELOW the initial range counts as the Method 1 activation, and (b) whether an IRF activation at the day's low ends the day's trading", "yes", "no: scope of 'completely stopped' is not stated", "YES", "IRF-M1-002, IRF-M1-003"),
    "AC20": (["MISSING_AUTHOR_RULE", "SUPPORT_RESISTANCE_MISMATCH"], "C", "Cannot be decided: under the first-red-candle readings no entry exists before the cutoff", "Yes under the existing proposals", "S/R of the first red candle", "yes", "no (ambiguous)", "YES", "IRF-M2A-001/002"),
    "AC21": (["SUPPORT_RESISTANCE_MISMATCH", "AUTHOR_DISCRETION_UNRESOLVED"], "C", "Cannot be decided: the engine's zone is [25,809.00, 25,846.45], 37.45 points tall (zone method A_LOWEST_LOW with ZONE_FULL, both proposals); the author says the criteria are not met", "Yes under the proposed zone",
             "the PDS zone construction (author's candle selection, PDS-ZONE-002 UNRESOLVED)", "yes: the PDS zone", "no", "YES", "PDS-ZONE-002, PDS-002, PDS-005"),
    "AC22": (["JOURNAL_INCONSISTENCY", "AUTHOR_DISCRETION_UNRESOLVED"], "C", "No: a second trade after an initial full stop, restricted to PDR/PDS, is the owner-approved rule", "Yes: the second PDS trade is allowed by DAY-SL-001 (not a glitch)",
             "the author's belief that no second trade should occur on that day conflicts with the approved portfolio rule", "unknown", "no", "YES", "DAY-SL-001, DAY-MAX-001"),
    "AC23": ([], "n/a", "crossed out: not an active instruction", "n/a", "none", "none", "n/a", "NO", "-"),
    "AC24": (["EMA_FILTER_MISMATCH"], "C", "Cannot be decided: ORB Method 2 failed the approved trend variant (previous close on the wrong side of its EMA); the first candle's body is 49.7%", "Yes under TREND-EMA-001", "the trend definition", "yes", "no", "YES", "TREND-EMA-001, ORB-TREND-001"),
    "AC25": (["EMA_FILTER_MISMATCH"], "C", "Cannot be decided: RF is rejected by the approved trend variant (previous session close vs EMA); RF-001 'established uptrend' is undefined", "Yes under TREND-EMA-001", "the RF trend definition", "yes", "no", "YES", "RF-001, RF-008, TREND-EMA-001"),
    "AC26": (["MISSING_AUTHOR_RULE", "SUPPORT_RESISTANCE_MISMATCH"], "C", "Cannot be decided: under the first-red-candle readings no entry exists before the cutoff", "Yes under the existing proposals", "S/R of the first red candle", "yes", "no (ambiguous)", "YES", "IRF-M2A-001/002"),
    "AC27": (["MISSING_AUTHOR_RULE", "CANDLE_CONFIRMATION_MISMATCH"], "B", "Yes: a long should close green; the engine's own explanation records that the candle was bearish and admitted by the pin-bar route", "Yes under its proposals (conditional pin bar, no colour test). The source phrase 'a suitable bullish pin-bar-type candle' is in the Gap setup (ORB-GAP-LONG-004); for Method 1 the pin bar enters through 'candle quality across all three setups' (ORB-CANDLE-001, pp. 9-10) and the proposal flag orb_pin_bar_in_methods_1_2, and the same page says a pin bar's close must support the breakout - the engine assumed the level break guarantees that, which is arguably what the author contests",
             "the colour of an ORB long's first candle", "yes: ORB long needs a green close (short, by ORB-GLOBAL-002, a red close)", "YES - implemented as an opt-in variant (strategies/orb_colour.py); NOT the active baseline", "YES before it becomes the baseline", "ORB-GLOBAL-002, ORB-GAP-LONG-004, ORB-M1-LONG-003"),
    "AC28": (["AUTHOR_DISCRETION_UNRESOLVED", "SUPPORT_RESISTANCE_MISMATCH"], "C", "Cannot be decided: Method 2 failed the proposed trendline test; the first candle is a green doji-like hammer (body 6.4%)", "Yes under the encoded rules", "objective ORB inner level / trendline", "yes", "no", "YES", "ORB-M2-LONG-001"),
    "AC29": (["CANDLE_CONFIRMATION_MISMATCH", "ENTRY_TIMING_MISMATCH"], "C", "Consistent with the legacy PDR-007 wording (replaced by PDR-A04 in Phase 3.4): the 09:20 candle is the first green candle closing above the ceiling", "Yes under the proposed thresholds: that candle's body is 36.2% (neither a good body nor a hammer)",
             "the numeric thresholds of the patterns", "yes", "no", "YES", "PDR-007, PDR-A04"),
    "AC30": (["AUTHOR_DISCRETION_UNRESOLVED", "JOURNAL_INCONSISTENCY"], "C", "Partly: if the first entry is moved to the first green candle the day's sequence changes; the second entry itself is allowed by DAY-SL-001", "Yes: the second PDR trade follows the approved rule",
             "a consequence of AC29 rather than a separate rule", "no separate rule", "no", "YES", "DAY-SL-001"),
    "AC31": (["EMA_FILTER_MISMATCH", "AUTHOR_DISCRETION_UNRESOLVED"], "C", "Cannot be decided: the Gap/200DMA setup requires the first candle to close beyond the 200 average (in this engine the 5-minute EMA(200), ma_mode EMA200_5M, not a daily average); it closed 24.77 points on the other side", "Yes under ORB-GAP-*-003", "which ORB setup and direction the author means", "unknown", "no", "YES", "ORB-GAP-LONG-003"),
    "AC32": (["MISSING_AUTHOR_RULE", "CANDLE_CONFIRMATION_MISMATCH", "JOURNAL_INCONSISTENCY"], "B", "Consistent with the author's clarification: the engine's entry candle has a 45.2% body, and the next candle closes below the session low so far", "Yes under the guide (no body or day's-low test)",
             "(a) entry-candle body threshold (stated as 60+, 50 and 40 in different places), (b) 'not at the day's low'", "yes", "partly: the body threshold is inconsistent; 'day's low' needs a measurement definition", "YES", "IRF-M1-004"),
    "AC33": (["CANDLE_CONFIRMATION_MISMATCH", "SUPPORT_RESISTANCE_MISMATCH"], "C", "Cannot be decided: the first candle's body is 52.2% (proposed threshold 60%) and Method 2's trendline test failed", "Yes under the proposed MODERATE profile (body >= 60%); the LOOSE profile (body >= 50%) would admit the 52.2% body, and Method 2's trendline test failed separately", "ORB strength profile and trendline", "yes", "no", "YES", "ORB-M1-LONG-003, ORB-M2-LONG-001"),
    "AC34": (["MISSING_AUTHOR_RULE", "ENTRY_TIMING_MISMATCH"], "C", "Cannot be decided: with the body condition the first-red-candle reading enters LATER (12:45); without it the same candle as the engine", "Yes under the existing proposals", "S/R of the first red candle and the body condition", "yes", "no (ambiguous)", "YES", "IRF-M2B-001/003"),
    "AC35": (["AUTHOR_DISCRETION_UNRESOLVED", "SUPPORT_RESISTANCE_MISMATCH"], "C", "Cannot be decided: the remark is not mechanical ('take resistance in the zone; zone breakout i.e. trap is not considered') and its label is uncertain (PDS / PPS)", "Yes under the encoded rules", "a definition of 'trap' and of taking resistance inside the zone", "unknown", "no", "YES", "PDS-002, PDS-005"),
    "AC36": (["JOURNAL_INCONSISTENCY", "AUTHOR_DISCRETION_UNRESOLVED"], "C", "No for RF: RF-004 rejects the open above yesterday's high; for PDR: five-minute candles had closed below the zone floor (09:20-09:50) before the 10:45 confirmation - the failed-zone policy is an open owner decision, preserved unchanged",
             "Yes under the existing rules and the preserved failed-zone policy", "RF-004 versus the author's reading; the PDR failed-zone policy", "yes (policy)", "no", "YES", "RF-004, PDR failed-zone policy (Phase 3.4 unresolved)"),
    "AC37": (["AUTHOR_DISCRETION_UNRESOLVED"], "C", "Cannot be decided: no ORB record exists (the first candle broke no previous-day level)", "Not decidable: Method 2's inner level / trendline is not source-defined", "the level or condition the author used", "unknown", "no", "YES", "ORB-M2-LONG-001"),
    "AC38": (["CANDLE_CONFIRMATION_MISMATCH", "ENTRY_TIMING_MISMATCH", "JOURNAL_INCONSISTENCY"], "C", "In conflict with PDS-M-001: 'a weak red candle is not taken'; the first red candle at the zone (09:25) has a 10.4% body", "Yes under PDS-M-001 (Method 3 waits for a small-support break)",
             "whether the first red candle at the zone is taken regardless of strength", "yes", "no", "YES", "PDS-M-001, PDS-M3-001"),
    "AC39": (["CANDLE_CONFIRMATION_MISMATCH"], "C", "Cannot be decided: the first candle (red, body 76.2%) failed the proposed lower-wick limit (23.8% > 20%)", "Yes under the proposed MODERATE strength profile (lower-wick limit 20%); the LOOSE profile in params.py (body >= 50%, wick <= 25%) would admit this candle", "the ORB strength profile (a proposal; the author gives no numbers)", "yes", "no", "YES", "ORB-M1-SHORT-003"),
    "AC40": (["EMA_FILTER_MISMATCH", "CANDLE_CONFIRMATION_MISMATCH", "ENTRY_TIMING_MISMATCH"], "C", "Partly: PDR - the first green candle (09:45) is earlier than the engine's 10:10; ORB - rejected by the approved trend variant", "Yes under the proposed thresholds and the approved trend variant",
             "PDR confirmation thresholds; the ORB trend definition", "yes", "no", "YES", "PDR-007, PDR-A04, TREND-EMA-001"),
    "G01": (["AUTHOR_DISCRETION_UNRESOLVED"], "C", "Cannot be decided: the sentence is incomplete", "n/a", "the rest of the sentence", "unknown", "no", "YES (ask the author for the full sentence)", "-"),
    "G02": (["MISSING_AUTHOR_RULE"], "B", "Explicit but under-specified", "Yes under the written rules (no day's-low test exists)", "a definition of 'at the day's low' (wick or close; before or including the signal candle; which IRF methods; whether the day then ends)",
            "yes", "no: scope not clear; as measured, 0 of 109 executed Phase 3.6 IRF trades close below the session low so far", "YES", "(none: new author rule)"),
}
SELECTION = {"AC04": "ORB", "AC05": "RF", "AC06": "ORB", "AC12": "ORB", "AC14": "ORB", "AC15": "ORB", "AC16": "ORB", "AC21": "IRF", "AC22": "IRF", "AC24": "ORB", "AC25": "RF", "AC28": "ORB", "AC31": "ORB", "AC33": "ORB", "AC36": "RF", "AC37": "ORB",
             "AC39": "ORB", "AC40": "ORB", "AC17": "IRF"}


def rd(p: Path) -> list[dict]:
    with open(p, newline="") as f:
        return list(csv.DictReader(f))


def candle_svg(ev: dict, marks: list[dict], zone: tuple[float, float] | None, title: str) -> str:
    cs = [c for c in ev["candles"] if c["start"] <= "13:30"]
    W, H, L, Rg, T, B = 1100, 520, 70, 20, 50, 40
    lo = min(c["l"] for c in cs)
    hi = max(c["h"] for c in cs)
    s = ev["session"]
    extra = [x for x in (s["prev_high"], s["prev_low"], s["first_candle"]["high"], s["first_candle"]["low"]) if x is not None]
    lo, hi = min([lo] + extra + ([zone[0]] if zone else [])), max([hi] + extra + ([zone[1]] if zone else []))
    pad = (hi - lo) * 0.04
    lo, hi = lo - pad, hi + pad
    sy = lambda v: T + (hi - v) / (hi - lo) * (H - T - B)  # noqa: E731
    step = (W - L - Rg) / len(cs)
    sx = lambda i: L + step * (i + 0.5)  # noqa: E731
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" font-family="Helvetica,Arial,sans-serif" font-size="11">', f'<rect width="{W}" height="{H}" fill="white"/>', f'<text x="{L}" y="20" font-size="14" font-weight="bold">{title}</text>',
           f'<text x="{L}" y="38" fill="#555">5-minute candles (labelled by start), IRH/IRL = initial range, dashed = previous-day high/low, orange = EMA(200) of 5-minute closes; markers are placed at the END of the confirming candle</text>']
    for k in range(6):
        v = lo + (hi - lo) * k / 5
        out.append(f'<line x1="{L}" y1="{sy(v):.1f}" x2="{W - Rg}" y2="{sy(v):.1f}" stroke="#eee"/><text x="{L - 5}" y="{sy(v) + 4:.1f}" text-anchor="end">{v:,.0f}</text>')
    if zone:
        out.append(f'<rect x="{L}" y="{sy(zone[1]):.1f}" width="{W - L - Rg}" height="{max(sy(zone[0]) - sy(zone[1]), 2):.1f}" fill="#ffe0b2" opacity="0.6"/><text x="{L + 4}" y="{sy(zone[1]) - 3:.1f}" fill="#e65100">zone {zone[0]:,.2f} - {zone[1]:,.2f}</text>')
    for v, col, lab, dash in ((s["first_candle"]["high"], "#1565c0", "IRH", ""), (s["first_candle"]["low"], "#1565c0", "IRL", ""), (s["prev_high"], "#b71c1c", "prev high", "4 3"), (s["prev_low"], "#1b5e20", "prev low", "4 3")):
        if v is not None:
            out.append(f'<line x1="{L}" y1="{sy(v):.1f}" x2="{W - Rg}" y2="{sy(v):.1f}" stroke="{col}" stroke-dasharray="{dash}"/><text x="{W - Rg - 2}" y="{sy(v) - 2:.1f}" text-anchor="end" fill="{col}">{lab} {v:,.2f}</text>')
    pts = [(sx(i), sy(c["ema200"])) for i, c in enumerate(cs) if c["ema200"] is not None]
    if len(pts) > 1:
        out.append('<polyline fill="none" stroke="#fb8c00" stroke-width="2" points="' + " ".join(f"{x:.1f},{y:.1f}" for x, y in pts) + '"/>')
    for i, c in enumerate(cs):
        col = "#2e7d32" if c["colour"] == "G" else ("#c62828" if c["colour"] == "R" else "#555")
        x = sx(i)
        out.append(f'<line x1="{x:.1f}" y1="{sy(c["h"]):.1f}" x2="{x:.1f}" y2="{sy(c["l"]):.1f}" stroke="{col}"/>')
        top, bot = sy(max(c["o"], c["c"])), sy(min(c["o"], c["c"]))
        out.append(f'<rect x="{x - step * 0.3:.1f}" y="{top:.1f}" width="{step * 0.6:.1f}" height="{max(bot - top, 1):.1f}" fill="{col}"/>')
        if i % 6 == 0:
            out.append(f'<text x="{x:.1f}" y="{H - 22}" text-anchor="middle" fill="#555">{c["start"]}</text>')
    ends = {c["end"]: i for i, c in enumerate(cs)}
    for k, m in enumerate(marks):
        i = ends.get(m["time"])
        if i is None:
            continue
        x, y = sx(i), sy(m["price"])
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6" fill="none" stroke="{m["colour"]}" stroke-width="2.5"/><text x="{x + 8:.1f}" y="{y - 8 - 12 * (k % 3):.1f}" fill="{m["colour"]}" font-weight="bold">{m["label"]}</text>')
    out.append("</svg>")
    return "\n".join(out)


def main() -> int:  # noqa: C901
    recs = rd(OUT / "all_author_corrections.csv")
    from nifty_trading.strategies import rule_data as RD  # the rule registry (no side effects)
    rules = {r["rule_id"]: r for r in RD.RULES}
    manual = defaultdict(list)
    for r in rd(P36 / "manual_journal_comparison.csv"):
        manual[r["date"]].append(r)
    p36_trades = defaultdict(list)
    for r in rd(P36 / "all_trades_detailed.csv"):
        p36_trades[r["date"]].append(r)
    (OUT / "daily").mkdir(exist_ok=True)
    (OUT / "charts").mkdir(exist_ok=True)
    rec_rows, cls_rows, sel_rows, man_rows = [], [], [], []
    by_date: dict[str, list[dict]] = defaultdict(list)
    for r in recs:
        if r["date"]:
            by_date[r["date"]].append(r)
    for d, items in sorted(by_date.items()):
        ev = json.loads((OUT / "evidence" / f"{d}.json").read_text())
        cands = ev.get("candles", [])
        marks, zone = [], None
        zone_sig = next((s for s in ev.get("signals", []) if s["strategy"] in ("PDR", "PDS") and s["controller_event"] == "EXECUTED"), None)
        if zone_sig:
            lv = json.loads(zone_sig["reference_levels"])
            if lv.get("zone_low"):
                zone = (lv["zone_low"], lv["zone_high"])
        md = [f"# {d} - author's correction(s) against the engine", "",
              "> Phase 5.1 date report. Evidence only; no rule was changed to produce a different outcome. Source image(s) are referenced under each correction.", ""]
        for r in items:
            cid = r["correction_id"]
            cl = C[cid]
            tid_n = r["trade_no"]
            tr = next((t for t in ev.get("trades", []) if t["trade_id"].split("-")[1] == tid_n), None) if tid_n else None
            if tr is None and ev.get("trades"):
                tr = ev["trades"][0]
            irf_m = None
            readings = {}
            if tr and tr["strategy"] == "IRF" and cands:
                irf_m = D.irf_trade_measures(cands, tr["signal_confirmed_at"][-5:])
                readings = D.readings(cands)
                if tr:
                    marks.append({"time": tr["signal_confirmed_at"][-5:], "price": float(tr["entry_price"]) if tr["entry_price"] else 0.0, "colour": "#d81b60", "label": f"engine {tr['strategy']} {tr['method'][-2:].strip()}"})
                a = readings.get("FULLY_ABOVE|body>=60", {})
                if a and a.get("entry"):
                    marks.append({"time": a["entry"]["signal_time"], "price": a["entry"]["close"], "colour": "#6a1b9a", "label": f"author reading (first red, body>=60) {a['entry']['trigger']}"})
            elif tr and cands:
                marks.append({"time": tr["signal_confirmed_at"][-5:], "price": float(tr["entry_price"]), "colour": "#d81b60", "label": f"engine {tr['strategy']} {tr['method'][-2:].strip()}"})
            green = None
            if tr and tr["strategy"] == "PDR" and zone:
                green = D.first_green_after_zone(cands, zone[0], zone[1])
                g = (green or {}).get("first_green_close_above_ceiling")
                if g:
                    marks.append({"time": g["signal_time"], "price": g["close"], "colour": "#6a1b9a", "label": "author: first green candle"})
            orb_rej = [x for x in ev.get("rejected", []) if x["strategy"] == "ORB"]
            exp = SELECTION.get(cid)
            exp_sigs = [s for s in ev.get("signals", []) if exp and s["strategy"] == exp]
            exp_rej = [x for x in ev.get("rejected", []) if exp and x["strategy"] == exp]
            auto = f"{tr['trade_id']} {tr['strategy']} {tr['method']} {tr['direction']} signal {tr['signal_confirmed_at'][-5:]} entry {tr['entry_price']} -> {tr['outcome']}" if tr else "(no automated trade)"
            first_dis = {
                "ORB": "the engine records no ORB confirmation: " + ("; ".join(f"{x['method']}: {x['failure_reason'][:70]}" for x in orb_rej) or "no ORB setup record (no previous-day level was broken by the first candle)"),
            }.get(exp or "", "")
            rec_rows.append({"correction_id": cid, "date": d, "pdf_page": r["pdf_page"], "trade_id_as_written": r["trade_id_as_written"], "automated_trade": auto, "author_strategy_label": r["strategy_label_as_written"], "author_expected": r["suggested_strategy"],
                             "author_timing": r["earlier_later_or_not_at_all"], "first_point_of_disagreement": first_dis or cl[4], "engine_status": cl[3], "author_status": cl[2], "evidence_file": f"daily/{d}.md", "chart": f"charts/{d}.svg"})
            cls_rows.append({"correction_id": cid, "date": d, "classifications": ";".join(cl[0]), "category": cl[1], "implemented": "OPT_IN_VARIANT" if cid == "AC27" else "NO", "missing_requirement_or_root_cause": cl[4], "new_rule_required": cl[5],
                             "objectively_implementable": cl[6], "owner_approval_required": cl[7], "rule_references": cl[8], "author_correct_under_existing_rules": cl[2], "engine_correct_under_existing_rules": cl[3]})
            if exp:
                ctrl = [f"{s['time']} {s['strategy']} {s['method']}: {s['controller_event']} {s['controller_reason'][:50]}" for s in ev.get("signals", [])[:4]]
                first_exec = min((s["time"] for s in ev.get("signals", []) if s["controller_event"] == "EXECUTED"), default=None)
                first_exp = min((s["time"] for s in exp_sigs), default=None)
                if first_exp is None:
                    verdict = "CONTROLLER_CORRECT: the expected strategy never produced a confirmed signal, so nothing was skipped; the disagreement lies in that engine's own conditions"
                elif first_exec is not None and first_exp >= first_exec:
                    verdict = f"CONTROLLER_CORRECT: the expected strategy's first confirmed signal ({first_exp}) is not earlier than the executed one ({first_exec}); first-valid-signal selection was respected"
                else:
                    verdict = f"REVIEW: the expected strategy confirmed a signal at {first_exp}, earlier than the first executed signal ({first_exec})"
                sel_rows.append({"correction_id": cid, "date": d, "engine_first_trade": auto, "author_expected_strategy": exp, "expected_strategy_confirmed_signals": ";".join(f"{s['time']} {s['method']}" for s in exp_sigs) or "none",
                                 "expected_strategy_rejections": ";".join(f"{x['method']}: {x['failure_reason'][:60]}" for x in exp_rej) or "none recorded (no setup started)", "controller_events_first_signals": " | ".join(ctrl),
                                 "same_minute_conflict": "yes" if any(s["competing_signals_same_minute"] for s in ev.get("signals", [])[:2]) else "no",
                                 "verdict": verdict,
                                 "classification": ";".join(cl[0])})
            for m in manual.get(d, []):
                man_rows.append({"correction_id": cid, "date": d, "journal_row": m["journal_row"], "journal_strategy": m["journal_strategy"], "manual_entry_time_label": m["manual_entry_time_label"], "manual_direction": m["manual_direction"], "manual_outcome": m["manual_outcome"],
                                 "match_classification": m["match_classification"], "auto_trade": m["trade_id"], "auto_strategy": m["auto_strategy"], "auto_entry_time": m["auto_entry_time"], "author_expected": r["suggested_strategy"],
                                 "note": "supporting evidence only: the manual journal is not ground truth (brief, section 12)"})
            md += [f"## {cid} (PDF page {r['pdf_page']}, as written `{r['trade_id_as_written']}`, label `{r['strategy_label_as_written']}`, {r['status']})", "", "### Author's observation", "", f"> {r['author_text_verbatim']}", "",
                   f"Suggested: **{r['suggested_strategy']}**; timing: {r['earlier_later_or_not_at_all']}; requirement stated: {r['requirement_stated']}. Drawing (my reading): {r['drawing_interpretation']}. Uncertain: {r['uncertain_phrases'] or 'none'}. Image: `{r['source_image']}`.", "",
                   "### Original automated trade", "", auto, ""]
            if tr:
                md += [f"Stop {tr['initial_stop']}, T1 {tr['target_1']}, T2 {tr['target_2']}; exits {tr['leg1_exit_time']} / {tr['leg2_exit_time']}. Engine explanation: {tr['setup_explanation'][:900]}", ""]
            md += ["### Independent historical evidence", "", f"Session: open {ev['session']['open']}, previous high/low/close {ev['session']['prev_high']} / {ev['session']['prev_low']} / {ev['session']['prev_close_official']} (gap {ev['session']['gap_points']}); first candle {ev['session']['first_candle']}.", ""]
            if irf_m:
                md += ["Signal-candle measurements: " + ", ".join(f"{k}={v}" for k, v in irf_m.items()), ""]
            if readings:
                md += ["Readings of the author's 'first red candle' wording (my formalisations, side by side):", "", "| reading | first red candle | support | resistance | entry (signal time, close, trigger, body %) |", "|---|---|---|---|---|"]
                for k, v in readings.items():
                    en = (v or {}).get("entry")
                    md.append(f"| {k} | {(v or {}).get('first_red_candle', '-')} | {(v or {}).get('support', '-')} | {(v or {}).get('resistance', '-')} | {('%s, %s, %s, %s' % (en['signal_time'], en['close'], en['trigger'], en['body_pct'])) if en else 'none before 13:00'} |")
                md.append("")
            if green:
                md += [f"First green candle after the zone interaction ('enter in 1st green candle'): {json.dumps(green)}", ""]
            if orb_rej:
                md += ["ORB records: " + "; ".join(f"{x['method']} {x['category']}: {x['failure_reason']}" for x in orb_rej), ""]
            md += ["Chronological signal timeline (engine):", "", "| time | strategy | method | dir | event | reason |", "|---|---|---|---|---|---|"]
            md += [f"| {s['time']} | {s['strategy']} | {s['method']} | {s['direction']} | {s['controller_event']} | {s['controller_reason'][:80]} |" for s in ev.get("signals", [])[:14]]
            md += ["", "Rejected / invalidated setups: " + ("; ".join(f"{x['time']} {x['strategy']} {x['method']}: {x['failure_reason'][:70]}" for x in ev.get("rejected", [])[:10]) or "none"), ""]
            refs = [x.strip() for x in cl[8].split(",") if x.strip() in rules]
            if refs:
                md += ["Applicable source rules:", ""] + [f"* `{x}` ({rules[x]['classification']}): {rules[x]['description'][:260]}" for x in refs] + [""]
            md += ["### Conclusion", "", f"* **Classification:** {', '.join(cl[0]) or 'not active (crossed out)'}   **Category:** {cl[1]}",
                   f"* **Is the author correct under the existing rules?** {cl[2]}", f"* **Is the engine correct under the existing rules?** {cl[3]}", f"* **Missing requirement / root cause:** {cl[4]}",
                   f"* **New rule required?** {cl[5]}   **Implementable objectively now?** {cl[6]}   **Owner approval needed?** {cl[7]}", ""]
        if cands:
            title = f"{d}: " + " / ".join(i["correction_id"] for i in items)
            (OUT / "charts" / f"{d}.svg").write_text(candle_svg(ev, marks, zone, title))
            md += [f"![{d}](../charts/{d}.svg)", "", "Candles 09:15-13:00 (start, O, H, L, C, colour, body %, upper wick %, lower wick %, EMA200, close - EMA):", "", "| start | O | H | L | C | col | body% | uw% | lw% | EMA | c-EMA |", "|---|---|---|---|---|---|---|---|---|---|---|"]
            md += [f"| {c['start']} | {c['o']} | {c['h']} | {c['l']} | {c['c']} | {c['colour']} | {c['body_pct']} | {c['upper_wick_pct']} | {c['lower_wick_pct']} | {c['ema200']} | {c['close_minus_ema']} |" for c in cands if c["start"] <= "13:00"]
        (OUT / "daily" / f"{d}.md").write_text("\n".join(md) + "\n")
    for r in recs:  # the two general remarks
        if not r["date"]:
            cl = C[r["correction_id"]]
            cls_rows.append({"correction_id": r["correction_id"], "date": "", "classifications": ";".join(cl[0]), "category": cl[1], "implemented": "NO", "missing_requirement_or_root_cause": cl[4], "new_rule_required": cl[5], "objectively_implementable": cl[6],
                             "owner_approval_required": cl[7], "rule_references": cl[8], "author_correct_under_existing_rules": cl[2], "engine_correct_under_existing_rules": cl[3]})
            rec_rows.append({"correction_id": r["correction_id"], "date": "", "pdf_page": r["pdf_page"], "trade_id_as_written": r["trade_id_as_written"], "automated_trade": "(general remark)", "author_strategy_label": r["strategy_label_as_written"],
                             "author_expected": r["suggested_strategy"], "author_timing": r["earlier_later_or_not_at_all"], "first_point_of_disagreement": cl[4], "engine_status": cl[3], "author_status": cl[2], "evidence_file": "", "chart": ""})
    for rows, name in ((rec_rows, "date_by_date_reconciliation.csv"), (cls_rows, "correction_classifications.csv"), (sel_rows, "strategy_selection_conflicts.csv"), (man_rows, "manual_journal_comparison.csv")):
        with open(OUT / name, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
    print(f"{len(rec_rows)} reconciliation rows, {len(cls_rows)} classification rows, {len(sel_rows)} selection rows, {len(man_rows)} manual rows, {len(list((OUT / 'daily').glob('*.md')))} day reports, {len(list((OUT / 'charts').glob('*.svg')))} charts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
