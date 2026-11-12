"""Phase 6.0 stage 3: reconstruct the three rulebook examples (16, 17, 24 Sep 2025) from actual candles on BOTH data feeds and write the verification matrix, the Markdown report and the workbook."""

from __future__ import annotations

import functools
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pandas as pd  # noqa: E402
from phase60_common import OUT, get_window  # noqa: E402

from nifty_trading.research.orb_v2 import config as C  # noqa: E402
from nifty_trading.research.orb_v2 import data_access as DA  # noqa: E402
from nifty_trading.research.orb_v2 import execution as EX  # noqa: E402
from nifty_trading.research.orb_v2 import levels as L  # noqa: E402
from nifty_trading.research.orb_v2 import signal_engine as SE  # noqa: E402
from nifty_trading.research.orb_v2.reporting import md_table, write_workbook  # noqa: E402

CFG = C.A
EX_DOC = {  # what the rulebook says (section references are the document's own headings)
    "2025-09-16": {"n": 1, "section": "5. Filter 2 / Example 1 (image1)", "intent": "BUY valid: inner resistance broken, major resistance (author's upper purple zone) still above", "ema_doc": "about 25,050", "upper_pct_doc": 11, "lower_pct_doc": None, "body_pct_doc": None,
                   "entry_doc": 25107.0, "stop_doc": 25077.0, "target_doc": 25168.0, "screenshot_ema": (25047.63, "15 Sep 11:45", "2025-09-15", "11:45"),
                   "screenshot_tags": "entry 25,107.45 / SL 25,076.60 / TP 25,168.00 (position tool; stop is -30.85 and target +60.55 from the tag, i.e. hand-drawn)"},
    "2025-09-17": {"n": 2, "section": "6. Filter 3 / Example 2 (image3)", "intent": "BUY chart shown as an example; the rulebook itself says 'by the 20% rule written here this candle fails. TO CONFIRM'", "ema_doc": "about 25,207", "upper_pct_doc": 47, "lower_pct_doc": 3,
                   "body_pct_doc": None, "entry_doc": 25297.0, "stop_doc": 25265.0, "target_doc": None, "screenshot_ema": (25206.80, "17 Sep 13:25", "2025-09-17", "13:25"), "screenshot_tags": "entry 25,296.80 / SL 25,265.25 / TP 25,351.25 (+54.45: hand-drawn)"},
    "2025-09-24": {"n": 3, "section": "6. Filter 3 / Example 3 (image4)", "intent": "SELL; the author described it as a trade that must NOT be taken because of its wick, yet the written rule treats a long UPPER wick on a SELL as good", "ema_doc": "about 25,234", "upper_pct_doc": 66,
                   "lower_pct_doc": 7, "body_pct_doc": 27, "entry_doc": None, "stop_doc": None, "target_doc": None, "screenshot_ema": (25233.85, "23 Sep 14:50", "2025-09-23", "14:50"), "screenshot_tags": "entry 25,090.50 / SL 25,120.50 / TP 25,031.15"}}
VIS = {"2025-09-16": [("lower purple zone", 25092.2, 25095.8), ("upper purple zone", 25111.8, 25114.8)], "2025-09-24": [("top purple zone", 25177.4, 25182.6), ("middle purple zone", 25135.7, 25140.4), ("lower purple zone", 25084.0, 25087.0)]}


def add_cond(matrix, ds, doc, vendor, failed, name, code, observed, requirement, authority):
    matrix.append({"example_date": ds, "example": doc["n"], "feed": vendor, "condition": name, "observed": observed, "requirement": requirement, "authority": authority, "verdict": "PASS" if code not in failed else "FAIL"})


def main() -> int:  # noqa: C901
    wins = {"5P": get_window("A", "5P"), "TV": get_window("A", "TV")}
    matrix, summary, doc_vs, zone_rows = [], [], [], []
    for ds, doc in EX_DOC.items():
        d = pd.Timestamp(ds).date()
        for vendor, inp in wins.items():
            sd, why = DA.session_data(inp, d)
            dec = SE.evaluate_session(sd, CFG)
            x = dec.detail
            failed = set(dec.failed)
            ex = EX.simulate(sd, dec.signal, CFG, inp.cal) if dec.signal else None
            cond = functools.partial(add_cond, matrix, ds, doc, vendor, failed)
            cond("Gap filter", "GAP_TOO_LARGE", f"gap {x['gap_points']:+.2f} (open {x['open_1m']:.2f} vs official prev close {x['prev_close']:.2f})", "|gap| <= 250 (or 300)", "TO_CONFIRM (250 or 300)")
            cond("200 EMA direction", "EMA_EQUAL", f"close {x['candle_close']:.2f} vs EMA {x['ema_now']:.2f} -> {x['direction_by_ema']} ({x['ema_scenario']})", "BUY above / SELL below the 5-min EMA(200)", "EXPLICIT_LATEST_RULEBOOK (same-candle EMA value: TO_CONFIRM)")
            cond("Previous-day level break", "LEVEL_NOT_BROKEN", f"{x['levels_broken_n']}/{x['levels_total']} broken ({x['qualifying_category']}); nearest: {x['primary_level']}", "close beyond any previous-day level, major or inner", "EXPLICIT (break = close beyond; zone edge TO_CONFIRM); inner-level construction PROVISIONAL")
            cond("Candle colour", "COLOUR_MISMATCH", x["colour"], "green for BUY, red for SELL", "EXPLICIT_LATEST_RULEBOOK")
            cond("Accepted pattern", "NO_PATTERN", f"{x['patterns_matched'] or 'none'} (full-body {x['full_body']}, pin {x['pin_bar']}, engulfing {x['engulfing']})", "hammer/shooting star, engulfing or full-body", "full-body EXPLICIT; pin proportions and engulfing reference PROVISIONAL")
            cond("Wrong-side wick", "WRONG_SIDE_WICK", f"{100 * x['wrong_side_wick_pct']:.1f}% of range", "<= 20% of the whole range", "EXPLICIT_LATEST_RULEBOOK (20% adjustable)")
            cond("Zero-range candle", "ZERO_RANGE_CANDLE", f"range {x['range_points']:.2f}", "high != low", "EXPLICIT_LATEST_RULEBOOK")
            e_ref = float(inp.chain[pd.Timestamp(doc["screenshot_ema"][2]).date()].query("start == @pd.Timestamp(@doc['screenshot_ema'][2] + ' ' + @doc['screenshot_ema'][3])")["ema"].iloc[0])
            summary.append({"example_date": ds, "example": doc["n"], "feed": vendor, "O": x["candle_open"], "H": x["candle_high"], "L": x["candle_low"], "C": x["candle_close"], "colour": x["colour"], "body_pct": round(100 * x["body_pct"], 1),
                            "upper_wick_pct": round(100 * x["upper_wick_pct"], 1), "lower_wick_pct": round(100 * x["lower_wick_pct"], 1), "total_wick_pct": round(100 * (x["upper_wick_pct"] + x["lower_wick_pct"]), 1), "ema_at_0920": round(x["ema_now"], 2),
                            "ema_at_screenshot_hover": round(e_ref, 2), "screenshot_ema_label": doc["screenshot_ema"][0], "ema_diff_vs_screenshot": round(e_ref - doc["screenshot_ema"][0], 2), "prev_day_high": x["prev_high"], "prev_day_low": x["prev_low"],
                            "prev_close_official": x["prev_close"], "gap_points": round(x["gap_points"], 2), "open_beyond_prev_range": x["gap_beyond_prev_range"], "levels_broken": f"{x['levels_broken_n']}/{x['levels_total']}", "level_category": x["qualifying_category"],
                            "patterns": x["patterns_matched"], "written_rule_verdict(V2-A)": ("SIGNAL " + dec.signal) if dec.signal else "NO SIGNAL: " + ", ".join(dec.failed), "entry_if_traded": ex["entry_price"] if ex and ex.get("traded") else "",
                            "exit_if_traded": f"{ex['exit_reason']} {ex['gross_points']:+.1f}" if ex and ex.get("traded") and ex.get("gross_points") is not None else ""})
            if doc["upper_pct_doc"] is not None:
                doc_vs.append({"example_date": ds, "feed": vendor, "measure": "upper wick %", "rulebook": doc["upper_pct_doc"], "actual": round(100 * x["upper_wick_pct"], 1), "difference": round(100 * x["upper_wick_pct"] - doc["upper_pct_doc"], 1)})
            if doc["lower_pct_doc"] is not None:
                doc_vs.append({"example_date": ds, "feed": vendor, "measure": "lower wick %", "rulebook": doc["lower_pct_doc"], "actual": round(100 * x["lower_wick_pct"], 1), "difference": round(100 * x["lower_wick_pct"] - doc["lower_pct_doc"], 1)})
            if doc["body_pct_doc"] is not None:
                doc_vs.append({"example_date": ds, "feed": vendor, "measure": "body %", "rulebook": doc["body_pct_doc"], "actual": round(100 * x["body_pct"], 1), "difference": round(100 * x["body_pct"] - doc["body_pct_doc"], 1)})
            if ds in VIS:
                lv = [l for l in L.all_levels(sd.prev_candles, CFG)]
                for nm, fl, ce in VIS[ds]:
                    best = min(lv, key=lambda l, fl=fl, ce=ce: abs((l.floor + l.ceiling) / 2 - (fl + ce) / 2))
                    zone_rows.append({"example_date": ds, "feed": vendor, "author_zone": nm, "author_floor_px": fl, "author_ceiling_px": ce, "nearest_engine_zone": f"{best.kind} {best.side} {best.floor:.2f}-{best.ceiling:.2f}", "engine_evidence": best.evidence,
                                      "mid_distance_pts": round(abs((best.floor + best.ceiling) / 2 - (fl + ce) / 2), 2)})
    # ---------------------------------------------------------------- classification of each example (rule-based statements, numbers come from `summary`)
    S = {(r["example_date"], r["feed"]): r for r in summary}
    verdicts = [
        {"example": 1, "date": "2025-09-16", "classification": "REPRODUCED ON THE SECONDARY FEED; FAILS THE PATTERN RULE ON 5paisa", "detail":
            f"On the secondary feed (the screenshot's feed) the candle is O {S[('2025-09-16', 'TV')]['O']} H {S[('2025-09-16', 'TV')]['H']} L {S[('2025-09-16', 'TV')]['L']} C {S[('2025-09-16', 'TV')]['C']}: upper wick {S[('2025-09-16', 'TV')]['upper_wick_pct']}% (rulebook ~11%), total wick {S[('2025-09-16', 'TV')]['total_wick_pct']}% -> full-body (<=20%) passes -> {S[('2025-09-16', 'TV')]['written_rule_verdict(V2-A)']}. "
            f"On 5paisa the first minute opens at {S[('2025-09-16', '5P')]['O']} (secondary {S[('2025-09-16', 'TV')]['O']}), lower wick {S[('2025-09-16', '5P')]['lower_wick_pct']}%, total wick {S[('2025-09-16', '5P')]['total_wick_pct']}% -> no pattern -> {S[('2025-09-16', '5P')]['written_rule_verdict(V2-A)']}. Author's zones match engine swing-zones within ~2 points (see zone table)."},
        {"example": 2, "date": "2025-09-17", "classification": "VIOLATES THE WRITTEN WICK RULE ON BOTH FEEDS (genuine contradiction; not a measurement error)", "detail":
            f"Secondary feed upper wick {S[('2025-09-17', 'TV')]['upper_wick_pct']}% / lower {S[('2025-09-17', 'TV')]['lower_wick_pct']}% reproduces the rulebook's 47% / 3% exactly; 5paisa gives {S[('2025-09-17', '5P')]['upper_wick_pct']}% / {S[('2025-09-17', '5P')]['lower_wick_pct']}%. Both exceed the 20% limit -> {S[('2025-09-17', 'TV')]['written_rule_verdict(V2-A)']}. "
            "The EMA, gap and level conditions pass (the open is above the previous day's high, so the close is beyond the major level; the rulebook says no previous-day level is drawn on this screenshot - a likely but UNCONFIRMED explanation is that nothing lies above the candle). Not a different candle, not an approximate measurement: the rule or the example needs author correction."},
        {"example": 3, "date": "2025-09-24", "classification": "PASSES THE WRITTEN RULES ON THE SECONDARY FEED (via the shooting-star pattern); the author's 'must not be taken' remark contradicts the rulebook table", "detail":
            f"Secondary feed: upper {S[('2025-09-24', 'TV')]['upper_wick_pct']}%, body {S[('2025-09-24', 'TV')]['body_pct']}%, lower {S[('2025-09-24', 'TV')]['lower_wick_pct']}% reproduces the rulebook's 66/27/7 exactly. Colour red, below the EMA, wrong-side (lower) wick {S[('2025-09-24', 'TV')]['lower_wick_pct']}% <= 20%, "
            f"pattern {S[('2025-09-24', 'TV')]['patterns']} (shooting-star proportions are PROVISIONAL) -> {S[('2025-09-24', 'TV')]['written_rule_verdict(V2-A)']}. On 5paisa the candle is a different shape (O {S[('2025-09-24', '5P')]['O']} - an opening print 32 points above the secondary feed's open; upper wick "
            f"{S[('2025-09-24', '5P')]['upper_wick_pct']}%, body {S[('2025-09-24', '5P')]['body_pct']}%) and passes via full-body. The disagreement is therefore about the RULE (is a long upper wick on a SELL bad?), not the candle: requires author clarification; no pass/fail is assumed."}]
    write_workbook(OUT / "ORB_V2_Examples_Verification.xlsx", {"Verdicts": verdicts, "Candle_and_EMA": summary, "Condition_matrix": matrix, "Rulebook_vs_actual": doc_vs, "Zones_author_vs_engine": zone_rows},
                   {"purpose": "Reconstruction of the three rulebook examples from actual one-minute candles on two feeds (5paisa = primary; secondary vendor = the feed the screenshots match).",
                    "rules": "Config ORB-V2-A (written-rule reference). Pattern proportions are PROVISIONAL conventions. Author zones are read from the screenshots by pixel position (+/-1.5 points) and are visual evidence only.",
                    "feeds": "Never mixed: each row states its feed."})
    md = ["# Reconstruction of the rulebook examples (16, 17 and 24 September 2025)", "",
          "Source: `Nifty_920_ORB_Rulebook (2) (1).docx` (identical bytes to `(2).docx`; SHA-256 8504fb6f...). The four embedded images were extracted at native resolution (`charts_examples/doc_images/`). "
          "Prices were never overwritten to match a screenshot. Every number below is recomputed from one-minute candles.", "",
          "## Key finding: the screenshots come from the secondary-vendor feed, not from 5paisa", "",
          "The rulebook's measured wick percentages (Example 2: 47% / 3%; Example 3: 66% / 27% / 7%) and the EMA labels in the screenshots are reproduced **exactly** by the secondary vendor's minute data and **not** by 5paisa. "
          "The first 09:15 one-minute bar differs between feeds (24 Sep: 5paisa opens 25,142.55 - an opening print - while the secondary feed opens 25,108.75). The wrong-side-wick and pattern tests are therefore feed-dependent. "
          "Which feed defines the author's candle is the most important unresolved data decision (see `unresolved_rule_definitions.md`).", "",
          "## Verdicts", "", md_table(verdicts), "", "## Candle, EMA and decision per example and feed", "", md_table(summary, ["example_date", "feed", "O", "H", "L", "C", "colour", "body_pct", "upper_wick_pct", "lower_wick_pct", "total_wick_pct", "ema_at_0920", "gap_points", "levels_broken", "patterns", "written_rule_verdict(V2-A)"]), "",
          "## Rulebook numbers versus actual", "", md_table(doc_vs), "",
          "## EMA check against the screenshot labels", "", md_table(summary, ["example_date", "feed", "ema_at_screenshot_hover", "screenshot_ema_label", "ema_diff_vs_screenshot"]),
          "The independent EMA(200) agrees with the TradingView/FYERS labels to within a quarter of a point on all three hover candles (the rulebook's 'about 25,050 / 25,207 / 25,234' are the same labels read at the hover time, not the 09:20 value).", "",
          "## Author's purple zones versus engine swing zones", "", md_table(zone_rows), "",
          "Zones were read from the screenshots by pixel position against the price axis (+/-1.5 points) and are visual evidence only; the general construction rule remains undefined. Because the engine produces roughly ten zones per side, a small nearest-zone distance is WEAK evidence (several engine zones lie within a few points of any price) and does not validate the swing-zone construction. In Example 1 the author's 'major' upper zone (~25,112-25,115) is **not** the previous-day high (25,137.45, off the left edge of the screenshot): the author's 'major' appears to mean the prominent late-day zone, which the rulebook does not define.", "",
          "## Per-example condition matrix", "", md_table(matrix, ["example_date", "feed", "condition", "observed", "requirement", "verdict", "authority"]), "",
          "## What needs author confirmation", "",
          "1. Which feed is the author's candle (5paisa vs the TradingView/FYERS-type secondary feed)? The first-minute opening print differs and flips Example 1 and the pattern outcome of Example 3.",
          "2. Example 2: the written 20% rule fails the example on every feed. Is the rule direction/threshold wrong, or the example mislabeled?",
          "3. Example 3: is a long upper wick on a SELL good (rulebook table) or bad (the author's remark)?",
          "4. Example 1: what does 'major' mean when it is not the previous-day high?", "",
          "Charts: `charts_examples/example_<date>_<feed>.svg` (screenshot above, reconstructed chart below)."]
    (OUT / "original_examples_reconstruction.md").write_text("\n".join(md))
    (OUT / "phase60_state_examples.json").write_text(json.dumps({"summary": summary, "verdicts": verdicts, "zones": zone_rows}, indent=1, default=str))
    print(md_table(summary, ["example_date", "feed", "upper_wick_pct", "lower_wick_pct", "body_pct", "ema_diff_vs_screenshot", "written_rule_verdict(V2-A)"]))
    print(md_table(zone_rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
