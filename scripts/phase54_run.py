"""Phase 5.4: ORB source audit - measurements, candidate-variant signal impact, 13 disputed-date case studies (NO controller, NO fills, NO P&L, NO backtest).

  python scripts/phase54_run.py            run everything
  python scripts/phase54_run.py --list     list the (disabled-by-default) ORB variants

Writes under reports/phase5/phase54_orb_audit/: orb_source_rule_registry.csv, orb_predicate_matrix.csv, orb_13_disputed_dates.csv, orb_level_families_13.csv, orb_level_family_population.csv, orb_variant_impact.csv,
orb_variant_by_date.csv, orb_strength_review.csv, orb_strength_population.csv, orb_ema_trendline_review.csv, orb_journal_cross_check.csv, summary.json, daily/<date>.md, charts/<date>.svg.
The manual journal is read ONLY as descriptive evidence (which dates the trader took an ORB); no rule is chosen or tuned to it.
"""

from __future__ import annotations

import argparse
import json
import sys
import warnings
from collections import Counter
from datetime import date
from pathlib import Path

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import openpyxl  # noqa: E402
import phase54_charts as CH  # noqa: E402
from phase52_run import ORB_DATES, hm, rd  # noqa: E402

from nifty_trading.data.sessions import (  # noqa: E402
    build_session_contexts,
    load_daily_official,
    load_one_minute,
    load_warmup_one_minute,
)
from nifty_trading.research import phase3 as P  # noqa: E402
from nifty_trading.research import phase54 as V  # noqa: E402
from nifty_trading.research import phase54_orb as O  # noqa: E402
from nifty_trading.research.phase35 import write_csv  # noqa: E402
from nifty_trading.strategies import rule_data as RD  # noqa: E402
from nifty_trading.strategies.definitions import (  # noqa: E402
    confirmed_swing_highs,
    confirmed_swing_lows,
    pivot_highs,
    pivot_lows,
    prev_candles,
    prev_high_low,
    to_candles,
)
from nifty_trading.strategies.orb_candidates import inner_levels, trendline_supportive  # noqa: E402

OUT = ROOT / "reports" / "phase5" / "phase54_orb_audit"
P36 = ROOT / "reports" / "phase3" / "phase36_body_based_pdr"
P51 = ROOT / "reports" / "phase5" / "phase51_author_corrections"
JOURNAL = ROOT / "docs" / "trading journal" / "Trading_Journal_Sep2025_Aug2026 REPORT.xlsx"
CORR = {"2025-09-11": "AC04", "2025-09-16": "AC06", "2025-10-08": "AC12", "2025-10-16": "AC14", "2025-10-17": "AC15", "2025-10-27": "AC16", "2025-11-21": "AC24", "2025-11-28": "AC28", "2025-12-05": "AC31",
        "2025-12-12": "AC33", "2025-12-24": "AC37", "2025-12-30": "AC39", "2025-12-31": "AC40"}
METHODS = ("Method 1", "Method 2", "Gap/200DMA")
# what an unresolved / assumed predicate means for the audit: (kind, what is missing)
PRED_KIND = {"level_broken": ("SOURCE_RULE", "the first candle did not break and close beyond the previous-day high/low (Method 1 is source-explicit): the author must have used another level"),
             "inner_level_broken": ("ENGINE_ASSUMPTION", "Method 2's inner level has no construction in the rulebook; the engine's latest-fractal choice was not broken"),
             "trendline": ("ENGINE_ASSUMPTION", "the Method 2 trendline has no construction in the rulebook; the engine's last-two-fractals line was not supportive"),
             "trend": ("OWNER_VARIANT", "the active trend reading (previous close against its EMA) differs from the rulebook's literal 'price above the 200 EMA' at 09:20"),
             "candle_quality": ("NUMERIC_APPROXIMATION", "'strong body, limited wick' is qualitative in the rulebook; the numeric profile (MODERATE) rejected the candle"),
             "candle_shape": ("NUMERIC_APPROXIMATION", "'strong body or suitable pin bar' is qualitative; the numeric profile / pin test rejected the candle"),
             "near_ema_close": ("NUMERIC_APPROXIMATION", "'near the EMA' (15 points) and 'convincing close' (5 points) are not defined in the rulebook"),
             "gap_in_direction": ("SOURCE_RULE", "no opening gap in this direction: the Gap / 200-average setup does not apply"),
             "gap_crosses_200_average": ("READING_OF_SOURCE", "the gap did not carry the OPEN through the 200 average (frozen reading: previous close on the wrong side AND open on the right side)"),
             "first_candle_closes_beyond_average": ("SOURCE_RULE", "the first candle did not close beyond the 200 average")}


def f2(x, n=2):
    return "" if x is None else (round(x, n) if isinstance(x, float) else x)


def load_journal() -> list[dict]:
    ws = openpyxl.load_workbook(JOURNAL, data_only=True).worksheets[0]
    rows = []
    for r in ws.iter_rows(min_row=3, values_only=True):
        if r[0] is None or r[1] is None:
            continue
        t = r[2].strftime("%H:%M") if hasattr(r[2], "strftime") else str(r[2])
        rows.append({"sl": r[0], "date": r[1].strftime("%Y-%m-%d"), "weekday": r[1].strftime("%a"), "entry_time": t, "strategy": r[3]})
    return rows


FIG = {"p1": "p.1-2 overview tables (no chart)", "p3": "p.3 figure 'Method 1 - previous-day resistance breakout' (staircase to a horizontal previous-day resistance; the 09:15-09:20 candle opens below and closes above it; 200 EMA below)",
       "p4": "p.4 figure 'Method 1 - previous-day support breakdown' (mirror; 200 EMA above)", "p4t": "p.4 table 'major level (outside) vs inner level (inside)'",
       "p5": "p.5 figure 'Method 2 - trendline + inner resistance' (rising trendline through swing lows; inner resistance inside the previous day's range; major resistance above, not yet broken)",
       "p7": "p.7 annotated real chart ('inner level drawn approximately') and condition table", "p8": "p.8 figure 'Gap-up above the 200 DMA' (the candle opens BELOW the line, crosses it and closes above; the drawn gap box lies wholly below the line)",
       "p9": "p.9 figure 'Gap-down below the 200 DMA' (the candle opens ABOVE the line, crosses it and closes below)", "p10": "p.10 figure 'Candle-quality filter' (strong bullish / bullish pin bar / upper-wick rejection)",
       "p11": "p.11 parameter table (no chart)", "p12": "p.12 matrix and the two real charts under '10.REF IMAGES' (a long above a rising trendline band with a purple zone; a real gap-up long through the EMA after a decline)",
       "p13": "p.13 three real charts (two short breakdowns of a purple band; one long)"}
DIAG = (("ORB-GLOBAL-00", "p1"), ("ORB-UNIT", "p11"), ("ORB-TREND-00", "p3; p4"), ("ORB-MA-001", "p3; p4; p5; p7; p8; p9"), ("ORB-M1-LONG", "p3"), ("ORB-M1-SHORT", "p4"), ("ORB-M2-LONG", "p5; p7"), ("ORB-M2-SHORT", "p7"),
        ("ORB-GAP-LONG", "p8; p12"), ("ORB-GAP-SHORT", "p9"), ("ORB-CANDLE", "p10"))
# rules whose STATEMENT is quoted from the rulebook but whose construction / measure is not defined: the statement is an explicit (qualitative) document rule, the construction stays UNRESOLVED
QUAL_OVERRIDE = {"ORB-M2-LONG-001": "inner level + rising trendline through swing lows are named (p.5 steps 2 and 4; p.7 table) but no construction exists",
                 "ORB-M2-SHORT-001": "inner support + falling trendline through swing highs are named (p.6-7) but no construction exists",
                 "ORB-GAP-LONG-005": "'excessively extended' opening moves are rejected (p.9 box) but the measure is undefined", "ORB-GAP-SHORT-004": "'excessively extended' opening moves are rejected (p.9 box) but the measure is undefined"}


def registry_rows() -> list[dict]:
    out = []
    for r in RD.RULES:
        if r["strategy"] != "ORB":
            continue
        cls, impl, auth, rid = r["classification"], r["implementation_status"], r["authority"], r["rule_id"]
        if rid in QUAL_OVERRIDE:
            status = f"EXPLICIT_DOCUMENT_RULE (qualitative statement; construction UNRESOLVED / CURRENT_ENGINE_ASSUMPTION: {QUAL_OVERRIDE[rid]})"
        elif rid == "ORB-GLOBAL-004":
            status = "EXPLICIT_DOCUMENT_RULE"
        elif auth == "USER_APPROVED":
            status = "OWNER_APPROVED"
        elif cls == RD.VE:
            status = "EXPLICIT_DOCUMENT_RULE"
        elif cls == RD.VQ:
            status = "EXPLICIT_DOCUMENT_RULE (qualitative; its numeric form is a RESEARCH_PROPOSAL)" if r["proposal_parameter"] else "EXPLICIT_DOCUMENT_RULE (qualitative)"
        elif impl == RD.IMPL_R:
            status = "CURRENT_ENGINE_ASSUMPTION (RESEARCH_PROPOSAL; not in the source)"
        elif cls == RD.CF:
            status = "UNRESOLVED (conflicting wording in the source)"
        else:
            status = "UNRESOLVED"
        keys = next((v for k, v in DIAG if rid.startswith(k)), "")
        out.append({"rule_id": rid, "exact_source_statement": r["description"], "page": str(r["source_page"]), "diagram": "; ".join(FIG[k.strip()] for k in keys.split(";") if k.strip() in FIG), "method": r["method"],
                    "existing_code": "src/nifty_trading/strategies/orb.py" + (f" (proposal parameter: {r['proposal_parameter']})" if r["proposal_parameter"] else ""), "status": status, "registry_classification": cls, "implementation_status": impl,
                    "authority": auth, "unresolved_dependencies": "; ".join(r["unresolved_dependencies"])})
    extra = [
        ("ORB-M1-LEVEL-DEF", "p.4 table: the MAJOR level used in Method 1 is 'the top of the previous day's range (resistance) / bottom (support)'; it is 'broken by the 9:20 candle'. This is the explicit definition of the Method 1 level (the previous day's high / low).", "4", "p4t; p3; p4", "Method 1", "EXPLICIT_DOCUMENT_RULE", "orb.py::_method1 (prev_high_low)"),
        ("ORB-P12-WICK", "p.12 matrix, 'Wick rule': avoid a rejection wick against the trade - for Method 1, Method 2 and the Gap / 200 DMA setup alike.", "12", "p12", "ALL", "EXPLICIT_DOCUMENT_RULE (qualitative; numeric form RESEARCH_PROPOSAL)", "orb.py::_quality; the rejection-wick FLAG (33%) is applied only in the Gap setup"),
        ("ORB-P12-GAPREQ", "p.12 matrix, 'Gap': not mandatory for Method 1 and Method 2; REQUIRED for the Gap / 200 DMA setup. 'Established trend': required for Methods 1 and 2; 'not mandatory if conditions qualify' for the Gap setup.", "12", "p12", "ALL", "EXPLICIT_DOCUMENT_RULE", "orb.py (the Gap setup has no trend gate)"),
        ("ORB-VIS-P5", "Method 2 long schematic: inner resistance = the high of a recent candle near the END of the previous session's range, above a rising trendline through swing lows; the major previous-day resistance is above and unbroken; the first candle closes above the inner level.", "5", "p5", "Method 2", "EXPLICIT_DOCUMENT_RULE (schematic; no algorithm)", "ORB-M2-LONG-001"),
        ("ORB-VIS-P7", "Annotated real chart (p.7): 'MAJOR resistance - NOT yet broken at 9:20'; 'Small inner resistance (near trendline) broken'; 'Rising trendline = support'; the caption states the inner level is 'drawn approximately' and tells the reader to 'verify the exact levels and first-candle close on your original chart'.", "6,7", "p7", "Method 2", "EXPLICIT_DOCUMENT_RULE (illustration; the author concedes the level is approximate)", "ORB-M2-LONG-001/002"),
        ("ORB-VIS-P8P9", "Gap figures: in BOTH schematics the first candle opens on the OLD side of the 200 DMA (below it for the gap-up, above it for the gap-down), its body crosses the line and it closes beyond it; the drawn 'GAP UP / GAP DOWN' box lies wholly on the old side of the line and never reaches it. Text: 'the gap must bring price above [the average]' and 'a candle that only crosses the line but closes below it does not qualify'.", "8,9", "p8; p9", "Gap/200DMA", "EXPLICIT_DOCUMENT_RULE (figures) - they depict the CANDLE crossing; the frozen engine requires the OPEN to be beyond", "orb.py::_gap_setup (frozen: open beyond the average); variant orb-var-gap-candle-crossing"),
        ("ORB-VIS-P10", "Candle-quality figure: strong bullish (big body, close near the high, small upper wick) = preferred; bullish pin bar = conditional (needs breakout + close to confirm; drawn green); large upper-wick rejection = reject. Short setups mirror it. No percentages are given and no colour is stated for the pin bar in the text.", "10", "p10", "ALL", "EXPLICIT_DOCUMENT_RULE (qualitative; numbers are RESEARCH_PROPOSAL)", "ORB-CANDLE-001"),
        ("ORB-VIS-P12", "Two real charts under '10.REF IMAGES' on p.12: (1) a long above a rising trendline band with a thin purple zone that starts at earlier highs and runs a little past the entry candle (a tall gap-up candle follows); (2) a real gap-up long after a long decline - a tall green candle starts far below the EMA(200) and closes at / through it; the entry sits there.", "12", "p12", "Method 2 / Gap", "EXPLICIT_DOCUMENT_RULE (illustrations; unlabelled by method; chart (2) is the Gap setup drawn with the CANDLE crossing the average)", "ORB-GAP-LONG-002/003"),
        ("ORB-VIS-P13", "Three real charts on p.13: (1) and (2) are short breakdowns - a purple horizontal band drawn from a base at the left and extended to the entry candle (the number of sessions between is only inferred from unlabelled dashed verticals), a large red candle closes below it, EMA(200) above price; (3) a long: a purple resistance band that starts inside the previous session and runs past the entry candle, a rising blue trendline far below price, EMA(200) crossing the band, a green candle breaks above. No chart carries a price or date axis or a method label.", "13", "p13", "ALL (unlabelled)", "EXPLICIT_DOCUMENT_RULE (illustrations; levels are bands, not lines)", "(none: the registry has no rule for bands or multi-session levels)"),
        ("ORB-AC-27", "Author (handwritten, 2025-11-27): 'ORB is activated on a red candle for long side, which is wrong. ORB for long should be in green closing.' (the frozen engine's red-candle long passes as a bullish pin bar: the rulebook states no colour for the pin bar in the text; p.10 draws it green)", "hand p.5", "-", "ALL (long)", "AUTHOR_CLARIFICATION (long side only; the short mirror is an interpretation)", "ORB-GLOBAL-002 / orb_colour.py (opt-in)"),
        ("ORB-AC-13DATES", "Author (handwritten, 13 dates): 'ORB should have activated instead of IRF' / 'This should be an ORB trade' / 'Should be ORB, but IRF is activated'. No level, candle, direction or method is drawn or named; AC04 adds 'Ep 30 pts SL' (entry point, 30-point stop = the rulebook's ORB stop).", "hand p.1-6", "-", "ALL", "AUTHOR_CLARIFICATION (intent only; no objective condition)", "(none)"),
        ("ORB-ENG-TREND", "Frozen trend test: the previous session's last close is on the trend side of its EMA(200) ('EMA_PREV_SESSION_CLOSE', Research VARIANT A, owner-approved so that the opening gap cannot establish the trend). The rulebook says: 'Price above the 200 EMA is a basic confirmation, supported by bullish price structure.'", "3,4", "p3; p4", "Method 1/2", "OWNER_APPROVED (a variant of an explicit but under-specified rule)", "definitions.ema_prev_session_trend"),
        ("ORB-ENG-M2LEVEL", "Frozen Method 2 inner level: the LATEST 5-candle (k = 2, NON-STRICT: >= / <=, so flat tops and bottoms count) fractal of the previous session inside its range; trendline: the last two fractal lows (highs).", "4,5,6,7", "p5; p7", "Method 2", "CURRENT_ENGINE_ASSUMPTION (RESEARCH_PROPOSAL; not in the source)", "orb.py::_method2"),
        ("ORB-ENG-STRONG", "Frozen strong candle: MODERATE profile (body >= 60% of the range, wick against the trade <= 20%) or the owner-style pin bar (wick >= 2x body and close within 30% of the range); rejection-wick flag 33% (Gap setup only).", "3,4,9,10", "p10", "ALL", "CURRENT_ENGINE_ASSUMPTION (RESEARCH_PROPOSAL)", "params.py STRONG_CANDLE / PIN_BAR / REJECTION_WICK"),
    ]
    for rid, stmt, page, fig, method, status, code in extra:
        out.append({"rule_id": rid, "exact_source_statement": stmt, "page": page, "diagram": "; ".join(FIG[k.strip()] for k in fig.split(";") if k.strip() in FIG), "method": method, "existing_code": code, "status": status, "registry_classification": "", "implementation_status": "", "authority": "", "unresolved_dependencies": ""})
    return out


def main() -> int:  # noqa: C901
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__.split("\n\n", 1)[1])
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    if a.list:
        for v in V.VARIANTS.values():
            print(f"{v.key:36} {v.authority:34} {v.title}")
        return 0
    (OUT / "daily").mkdir(parents=True, exist_ok=True)
    (OUT / "charts").mkdir(exist_ok=True)
    m1 = load_one_minute()
    ctxs, _ = build_session_contexts(m1, daily_df=load_daily_official(), warmup_1m=load_warmup_one_minute())
    sc = P.combined_scenario("BODY_BASED_PHASE36")
    p = sc.proposals
    ds = sorted(ctxs)
    idx = {d: i for i, d in enumerate(ds)}
    trades = rd(P36 / "all_trades_detailed.csv")
    corr = {r["correction_id"]: r for r in rd(P51 / "all_author_corrections.csv")}
    journal = load_journal()
    jorb = {r["date"]: r for r in journal if r["strategy"] == "ORB"}
    summary: dict = {"journal_rows": len(journal), "journal_by_strategy": dict(Counter(r["strategy"] for r in journal)), "journal_saturday_rows": [r["date"] for r in journal if r["weekday"] in ("Sat", "Sun")]}

    def prior_sessions(d: date, k: int = 5) -> list[list]:
        i = idx[d]
        return [to_candles(ctxs[ds[i - j]].candles) for j in range(1, k + 1) if i - j >= 0]

    def first_colour(d: date) -> str:
        f = ctxs[d].candles.iloc[0]
        return "GREEN" if f.close > f.open else ("RED" if f.close < f.open else "DOJI")

    def colour_long(d: date) -> bool:
        return first_colour(d) != "RED"

    # ---------------------------------------------------------------------------------------- frozen ORB over every session + equality with the Phase 3.6 table
    sigs = {k: V.orb_signals_for(ctxs, sc, k) for k in V.VARIANTS}
    base = sigs[V.FROZEN_KEY]
    conf = lambda recs: [r for r in recs if r.signal_status == "CONFIRMED"]  # noqa: E731
    frozen_conf = sorted((str(d), r.method, r.direction, hm(r.signal_timestamp)) for d in base for r in conf(base[d]))
    p36 = sorted((r["date"], r["method"], r["direction"], r["time"]) for r in rd(P36 / "all_strategy_signals.csv") if r["strategy"] == "ORB")
    summary["frozen_orb_confirmed"] = len(frozen_conf)
    summary["frozen_orb_equals_phase36_table"] = frozen_conf == p36
    frozen_dates = {x[0] for x in frozen_conf}

    # ---------------------------------------------------------------------------------------- registry
    reg = registry_rows()
    write_csv(OUT / "orb_source_rule_registry.csv", reg)
    summary["registry"] = dict(Counter(r["status"].split(" (")[0] for r in reg))

    # ---------------------------------------------------------------------------------------- the 13 dates: predicate matrix (both directions), level families, strength, trend / trendline
    pm_rows, d13_rows, lf13, st_rows, et_rows = [], [], [], [], []
    for dstr in ORB_DATES:
        d = date.fromisoformat(dstr)
        c = ctxs[d]
        cs = to_candles(c.candles)
        f = cs[0]
        long_c = colour_long(d)
        gm = O.geometry(f)
        per: dict[str, dict] = {}
        for long in (True, False):
            pm = O.predicate_matrix(c, p, long)
            per[long] = pm
            for m, rows in pm.items():
                for k, r in enumerate(rows, 1):
                    pm_rows.append({"date": dstr, "direction": "LONG" if long else "SHORT", "first_candle_colour_matches": long == long_c, "method": m, "order": k, "predicate": r["name"], "pass": r["pass"], "observed": r["observed"], "rule": r["rule"],
                                    "rule_id": r["rule_id"], "signed_margin": f2(r["margin"], 3)})
        mm = per[long_c]
        summary_m = {m: {"first_failing": O.first_failing(rows), "n_failing": sum(1 for r in rows if r["pass"] is False)} for m, rows in mm.items()}
        recs = base[d]
        eng_status = "; ".join(f"{r.method} {r.direction}: {r.signal_status}" + (f" ({r.invalidation_reason})" if r.invalidation_reason else "") for r in recs) or "NO RECORD (no level broken / no gap crossing in either direction)"
        irf = [t for t in trades if t["date"] == dstr and t["strategy"] == "IRF"] + [t for t in trades if t["date"] == dstr and t["strategy"] != "IRF"]
        irf_txt = "; ".join(f"{t['strategy']} {t['method']} {t['signal_confirmed_at'][-5:]} {t['direction']} @ {t['entry_price']}" for t in irf) or "none"
        jr = jorb.get(dstr) or next((r for r in journal if r["date"] == dstr), None)
        ac = CORR[dstr]
        cr = corr[ac]
        fails = {m: summary_m[m]["first_failing"] for m in METHODS}
        near = [m for m, v in summary_m.items() if v["n_failing"] <= 1]
        kinds = {PRED_KIND[fails[m]][0] for m in near if fails[m] in PRED_KIND}
        m_entry = m1[(m1["timestamp"].dt.date == d) & (m1["timestamp"].dt.strftime("%H:%M") == "09:20")]
        fill = float(m_entry["open"].iloc[0]) if len(m_entry) else None
        d13_rows.append({
            "date": dstr, "correction_id": ac, "handwritten_pdf_page": cr["pdf_page"], "author_original_comment": cr["author_text_verbatim"], "expected_orb_direction": f"NOT STATED. ASSUMPTION (not author evidence): {'LONG' if long_c else 'SHORT'}, inferred from the first-candle colour ({gm['colour']})",
            "expected_orb_method": "NOT IDENTIFIABLE (no level, drawing or method written); closest by predicates: " + ", ".join(f"{m} (fails {summary_m[m]['first_failing']})" for m in near) if near else "NOT IDENTIFIABLE (every method fails two or more predicates)",
            "expected_entry_candle": "09:15-09:20 candle, entry at the 09:20 open of the next minute bar (rulebook decision time; no ORB drawing exists)", "actual_orb_signal_status": eng_status, "actual_irf_signal_and_other_trades": irf_txt,
            "manual_journal_row": f"{jr['strategy']} {jr['entry_time']}" if jr else "no journal row", "first_candle_ohlc": f"{f.o}/{f.h}/{f.l}/{f.c}", "first_candle_colour": gm["colour"], "body_pct": f2(gm["body_pct"], 1), "upper_wick_pct": f2(gm["upper_wick_pct"], 1),
            "lower_wick_pct": f2(gm["lower_wick_pct"], 1), "previous_day_high_low_close": f"{prev_high_low(c.previous, p)[0]}/{prev_high_low(c.previous, p)[1]}/{c.previous.close_official}", "open_gap_points": f2(c.open_price - c.previous.close_official),
            "ema200_at_first_candle": f2(float(c.candles['ema200_5m'].iloc[0])), "missing_condition_Method_1": fails["Method 1"], "missing_condition_Method_2": fails["Method 2"], "missing_condition_Gap_200DMA": fails["Gap/200DMA"],
            "kinds_of_missing_condition": ", ".join(sorted(kinds)), "relevant_source_rules": "; ".join(sorted({r["rule_id"] for r in mm['Method 1'] + mm['Method 2'] + mm['Gap/200DMA'] if r["pass"] is False})),
            "first_candle_start_end": f"{cs[0].start:%H:%M}-{cs[0].end:%H:%M}", "earliest_causal_entry": f"signal at the 09:20 candle close; fill = open of the 09:20 one-minute bar = {fill}" if fill is not None else "09:20 bar missing",
            "conflicts_with_existing_code": ("UNDETERMINED: every method fails two or more predicates, so the author's setup cannot be identified; the engine violates no explicit source rule that is shown" if not near else
                                             ("YES: the closest method (" + ", ".join(near) + ") is rejected by a condition the engine decides with a research assumption / numeric approximation / owner variant (" + ", ".join(sorted(kinds - {'SOURCE_RULE'})) + "); the source is silent or qualitative there"
                                              if kinds - {"SOURCE_RULE"} else "NO conflict with an explicit source rule: the closest method fails an explicit source condition (level / gap not reached); the author's level is unknown")),
            "required_correction_or_unresolved_definition": " | ".join(f"{m}: {PRED_KIND[v][1]}" for m, v in fails.items() if v in PRED_KIND)})
        # level families for the colour direction
        for r in O.level_families(c, p, prior_sessions(d), long_c):
            lf13.append({"date": dstr, "direction": "LONG" if long_c else "SHORT", **{k: f2(v, 2) if isinstance(v, float) else v for k, v in r.items()}})
        # strength
        stt = O.strength_table(f, long_c, p)
        st_rows.append({"date": dstr, "direction": "LONG" if long_c else "SHORT", "ohlc": f"{f.o}/{f.h}/{f.l}/{f.c}", **{k: f2(v, 2) if isinstance(v, float) else v for k, v in stt.items()},
                        "range": f2(gm["range"]), "body": f2(gm["body"]), "upper_wick": f2(gm["upper_wick"]), "lower_wick": f2(gm["lower_wick"]),
                        "distance_close_to_previous_day_level": f2((f.c - prev_high_low(c.previous, p)[0]) if long_c else (prev_high_low(c.previous, p)[1] - f.c)),
                        "level_broken_Method_1": next(r["pass"] for r in mm["Method 1"] if r["name"] == "level_broken")})
        # EMA / trendline
        tv = O.trend_variants(c, long_c, p)
        pcs = to_candles(prev_candles(c.previous, p))
        tl_idx = pivot_lows(pcs, 0, len(pcs), 2) if long_c else pivot_highs(pcs, 0, len(pcs), 2)
        ok_a, why_a, line_a = trendline_supportive(pcs, tl_idx, f, long_c, "LAST_TWO_FRACTALS_K2")
        ok_b, why_b, _ = trendline_supportive(pcs, tl_idx, f, long_c, "ANY_RISING_PAIR_OF_LAST_THREE_K2")
        last2 = [(f"{pcs[j].start:%H:%M}", pcs[j].l if long_c else pcs[j].h) for j in tl_idx[-3:]]
        sh_idx, sl_idx = confirmed_swing_highs(pcs, len(pcs) - 1, p.swing_k), confirmed_swing_lows(pcs, len(pcs) - 1, p.swing_k)
        t_long, t_short = O.trend_check(c, 0, "LONG", p.trend_mode, p), O.trend_check(c, 0, "SHORT", p.trend_mode, p)
        et_rows.append({"date": dstr, "direction": "LONG" if long_c else "SHORT", "prev_session_last_close": tv["prev_session_last_close"], "prev_session_last_ema": f2(tv["prev_session_last_ema"]), "prev_close_minus_ema": f2(tv["prev_close_minus_ema"]),
                        "ema_at_first_candle": f2(tv["ema_at_first_candle"]), "first_candle_close": tv["first_candle_close"], "first_close_minus_ema": f2(tv["first_close_minus_ema"]), "open_minus_ema": f2(tv["open_minus_ema_at_first_candle"]),
                        "ema_change_last_hour_prev_session": f2(tv.get("ema_change_over_last_hour_of_previous_session")), "trend_active_prev_close_vs_ema": f"{tv['active']['ok']} ({tv['active']['reason']})",
                        "trend_structure_variant": f"{tv['structure_ema_swing2']['ok']} ({tv['structure_ema_swing2']['reason']})", "trend_literal_first_close_vs_ema": f"{tv['first_candle_close_vs_ema_basic']['ok']} ({tv['first_candle_close_vs_ema_basic']['reason']})",
                        "previous_session_confirmed_swing_highs (n, last two)": f"{len(sh_idx)}: " + str([(f"{pcs[j].start:%H:%M}", pcs[j].h) for j in sh_idx[-2:]]), "previous_session_confirmed_swing_lows (n, last two)": f"{len(sl_idx)}: " + str([(f"{pcs[j].start:%H:%M}", pcs[j].l) for j in sl_idx[-2:]]),
                        "long_eligible_active_trend": f"{t_long.ok} ({t_long.reason})", "short_eligible_active_trend": f"{t_short.ok} ({t_short.reason})", "trendline_fractals_last3 (time, price)": str(last2), "trendline_frozen_supportive": ok_a, "trendline_frozen_reason": why_a, "trendline_value_at_open": f2(line_a), "trendline_any_pair_of_last_three_supportive": ok_b, "trendline_any_pair_reason": why_b})
    write_csv(OUT / "orb_predicate_matrix.csv", pm_rows)
    write_csv(OUT / "orb_13_disputed_dates.csv", d13_rows)
    write_csv(OUT / "orb_level_families_13.csv", lf13)
    write_csv(OUT / "orb_strength_review.csv", st_rows)
    write_csv(OUT / "orb_ema_trendline_review.csv", et_rows)
    summary["thirteen"] = {"first_candle_colours": dict(Counter(r["first_candle_colour"] for r in d13_rows)), "missing_Method_1": dict(Counter(r["missing_condition_Method_1"] for r in d13_rows)), "missing_Method_2": dict(Counter(r["missing_condition_Method_2"] for r in d13_rows)),
                           "missing_Gap": dict(Counter(r["missing_condition_Gap_200DMA"] for r in d13_rows)), "frozen_orb_records_on_the_13": sum(len(base[date.fromisoformat(x)]) for x in ORB_DATES),
                           "frozen_orb_confirmed_on_the_13": sum(len(conf(base[date.fromisoformat(x)])) for x in ORB_DATES)}

    # ---------------------------------------------------------------------------------------- population: level families, strength distribution, journal cross-check
    fam_pop: dict[str, Counter] = {}
    st_pop = Counter()
    jc_rows = []
    for d in ds:
        dstr = str(d)
        c = ctxs[d]
        long_c = colour_long(d)
        fams = O.level_families(c, p, prior_sessions(d), long_c)
        f = to_candles(c.candles)[0]
        stt = O.strength_table(f, long_c, p)
        trend_ok = O.trend_check(c, 0, "LONG" if long_c else "SHORT", p.trend_mode, p).ok
        for r in fams:
            cn = fam_pop.setdefault(r["family"], Counter())
            cn["sessions"] += 1
            if r["level"] is not None:
                cn["level_exists"] += 1
            if r["broken"]:
                cn["broken"] += 1
                cn["broken_and_strong_MODERATE"] += int(bool(stt["strong_MODERATE"] or stt["pin_bar_active_definition"]))
                cn["broken_and_strong_LOOSE"] += int(bool(stt["strong_LOOSE"] or stt["pin_bar_active_definition"]))
                cn["broken_and_trend_active"] += int(bool(trend_ok))
                cn["broken_strong_trend"] += int(bool(trend_ok) and bool(stt["strong_MODERATE"] or stt["pin_bar_active_definition"]))
                if dstr in ORB_DATES:
                    cn["broken_on_the_13"] += 1
                if dstr in jorb:
                    cn["broken_on_journal_orb_dates"] += 1
                else:
                    cn["broken_on_dates_without_a_journal_orb"] += 1
        if any(r["family"] == "M1_PREVIOUS_DAY_EXTREME" and r["broken"] for r in fams):
            st_pop["m1_level_broken_sessions"] += 1
            for prof in O.PROFILES:
                st_pop[f"m1_broken_strong_{prof}"] += int(bool(stt[f"strong_{prof}"]))
            st_pop["m1_broken_pin"] += int(bool(stt["pin_bar_active_definition"]))
        # journal cross-check rows are built below for journal ORB dates
    gap_pop = Counter()
    for d in ds:
        for long in (True, False):
            gr = O.gap_crossing_readings(ctxs[d], p, long)
            if gr["gap_in_direction"]:
                gap_pop["gap_in_direction_cases"] += 1
                gap_pop["frozen_reading_cases"] += int(gr["frozen_crossing"])
                gap_pop["candle_crossing_reading_cases"] += int(gr["alt_candle_crossing"])
                if gr["differs"]:
                    gap_pop["cases_where_the_readings_differ"] += 1
                    gap_pop["differ_dates"] = gap_pop.get("differ_dates", 0)
                    summary.setdefault("gap_reading_differ_cases", []).append({"date": str(d), "direction": "LONG" if long else "SHORT", "open_minus_average": f2(gr["open_minus_ma"], 3)})
    summary["gap_reading_population"] = {k: v for k, v in gap_pop.items() if k != "differ_dates"}
    fam_rows = []
    for fam, cn in fam_pop.items():
        n = cn["sessions"]
        fam_rows.append({"family": fam, "sessions": n, "level_exists": cn["level_exists"], "first_candle_breaks_and_closes_beyond": cn["broken"], "pct_of_sessions_broken": round(100 * cn["broken"] / n, 1), "broken_and_strong_MODERATE_or_pin": cn["broken_and_strong_MODERATE"],
                         "broken_and_strong_LOOSE_or_pin": cn["broken_and_strong_LOOSE"], "broken_and_trend_active": cn["broken_and_trend_active"], "broken_strong_and_trend (all gates but the trendline)": cn["broken_strong_trend"],
                         "broken_on_the_13_disputed_dates": cn["broken_on_the_13"], "broken_on_dates_with_a_journal_orb_row (descriptive)": cn["broken_on_journal_orb_dates"], "broken_on_dates_with_no_journal_orb_row (descriptive)": cn["broken_on_dates_without_a_journal_orb"]})
    write_csv(OUT / "orb_level_family_population.csv", fam_rows)
    summary["level_family_population"] = {r["family"]: {k: v for k, v in r.items() if k != "family"} for r in fam_rows}
    write_csv(OUT / "orb_strength_population.csv", [{"measure": k, "sessions": v} for k, v in sorted(st_pop.items())])
    summary["strength_population"] = dict(st_pop)

    # journal cross-check (descriptive)
    for r in sorted((x for x in journal if x["strategy"] == "ORB"), key=lambda x: x["date"]):
        dstr = r["date"]
        row = {"journal_date": dstr, "weekday": r["weekday"], "journal_entry_time": r["entry_time"], "session_in_dataset": date.fromisoformat(dstr) in idx}
        if date.fromisoformat(dstr) not in idx:
            row.update({"engine_orb_signal": "NO SESSION IN THE DATASET (irregular journal date)", "first_candle_colour": "", "Method_1_first_failing": "", "Method_2_first_failing": "", "Gap_first_failing": "", "best_method": "", "binding_predicate": "", "in_the_13": False})
            jc_rows.append(row)
            continue
        d = date.fromisoformat(dstr)
        c = ctxs[d]
        long_c = colour_long(d)
        pm = O.predicate_matrix(c, p, long_c)
        sm = {m: (O.first_failing(rows), sum(1 for x in rows if x["pass"] is False)) for m, rows in pm.items()}
        best = min(sm.items(), key=lambda kv: (kv[1][1], METHODS.index(kv[0])))
        eng = [f"{x.method} {x.direction}" for x in conf(base[d])]
        row.update({"engine_orb_signal": "; ".join(eng) if eng else "none", "first_candle_colour": first_colour(d), "Method_1_first_failing": sm["Method 1"][0], "Method_2_first_failing": sm["Method 2"][0], "Gap_first_failing": sm["Gap/200DMA"][0],
                    "best_method": best[0] if not eng else "(engine signal)", "binding_predicate": (best[1][0] if best[1][1] == 1 else f"{best[1][1]} predicates fail") if not eng else "", "in_the_13": dstr in ORB_DATES})
        jc_rows.append(row)
    write_csv(OUT / "orb_journal_cross_check.csv", jc_rows)
    miss = [r for r in jc_rows if r["session_in_dataset"] and r["engine_orb_signal"] == "none"]
    summary["journal_orb"] = {"rows": len(jc_rows), "engine_orb_signal_on_journal_orb_date": sum(1 for r in jc_rows if r["session_in_dataset"] and r["engine_orb_signal"] not in ("none",)), "journal_orb_dates_without_engine_orb": len(miss),
                              "of_which_in_the_13": sum(1 for r in miss if r["in_the_13"]), "irregular_dates_without_session": sum(1 for r in jc_rows if not r["session_in_dataset"]),
                              "first_candle_colour_of_missed": dict(Counter(r["first_candle_colour"] for r in miss)), "binding_predicate_of_missed": dict(Counter(r["binding_predicate"] for r in miss)),
                              "journal_orb_dates_engine_signal_on_other_dates_total": len(frozen_dates), "engine_orb_signal_dates_without_journal_orb": len(frozen_dates - set(jorb)),
                              "journal_orb_on_the_13": sum(1 for x in ORB_DATES if x in jorb)}
    # ---------------------------------------------------------------------------------------- candidate variants: signal-only impact (ORB engine only)
    imp_rows, by_date = [], []
    base_pairs = {(str(d), r.method, r.direction) for d in base for r in conf(base[d])}
    for k, v in V.VARIANTS.items():
        cf = [(str(d), r.method, r.direction, hm(r.signal_timestamp)) for d in sigs[k] for r in conf(sigs[k][d])]
        pairs = {(x[0], x[1], x[2]) for x in cf}
        dates_k = {x[0] for x in cf}
        added, removed = pairs - base_pairs, base_pairs - pairs
        on13 = sorted(x for x in ORB_DATES if x in dates_k)
        imp_rows.append({"variant": k, "authority": v.authority, "title": v.title, "confirmed_orb_signals": len(cf), "sessions_with_a_signal": len(dates_k), "by_method": str(dict(Counter(x[1] for x in cf))), "by_direction": str(dict(Counter(x[2] for x in cf))),
                         "added_vs_frozen": len(added), "removed_vs_frozen": len(removed), "disputed_dates_with_a_signal (of 13)": len(on13), "disputed_dates_list": ",".join(on13),
                         "date_overlap_with_journal_orb_rows (of 89, descriptive)": len(dates_k & set(jorb)), "signal_dates_with_no_journal_orb_row (descriptive)": len(dates_k - set(jorb)), "added_signal_dates_with_no_journal_orb_row (descriptive)": len({x[0] for x in added} - set(jorb)),
                         "ac27_2025-11-27_signal": "; ".join(f"{x[1]} {x[2]} {x[3]}" for x in cf if x[0] == "2025-11-27") or "none"})
    write_csv(OUT / "orb_variant_impact.csv", imp_rows)
    for dstr in ORB_DATES + ["2025-11-27"]:
        row = {"date": dstr}
        for k in V.VARIANTS:
            row[k] = "; ".join(f"{r.method} {r.direction} {hm(r.signal_timestamp)}" for r in conf(sigs[k][date.fromisoformat(dstr)])) or ""
        by_date.append(row)
    write_csv(OUT / "orb_variant_by_date.csv", by_date)
    summary["variants"] = {r["variant"]: {k: v for k, v in r.items() if k not in ("variant", "title")} for r in imp_rows}

    # ---------------------------------------------------------------------------------------- charts and daily case studies
    for dstr in ORB_DATES:
        d = date.fromisoformat(dstr)
        c = ctxs[d]
        long_c = colour_long(d)
        cs = to_candles(c.candles)
        pcs_all = to_candles(prev_candles(c.previous, p))
        n_prev = 36
        prev_rows = [{"start": x.start, "open": x.o, "high": x.h, "low": x.l, "close": x.c, "ema": x.ema} for x in pcs_all[-n_prev:]]
        today_rows = [{"start": x.start, "open": x.o, "high": x.h, "low": x.l, "close": x.c, "ema": x.ema} for x in cs[:36]]
        ph, pl = prev_high_low(c.previous, p)
        levels = [{"price": ph, "label": "SOURCE prev-day high", "kind": "SOURCE"}, {"price": pl, "label": "SOURCE prev-day low", "kind": "SOURCE"}]
        inner = inner_levels(pcs_all, ph, pl, long_c)
        if inner:
            levels.append({"price": inner[-1], "label": "frozen M2 inner level (latest fractal)", "kind": "CURRENT"})
            hi_lv = max(inner) if long_c else min(inner)
            if abs(hi_lv - inner[-1]) > 1e-9:
                levels.append({"price": hi_lv, "label": "PROV highest inner swing", "kind": "PROVISIONAL"})
        for fam in O.level_families(c, p, prior_sessions(d), long_c):
            if fam["family"] in ("MS_EXTREME_3_SESSIONS", "MS_SWING_NEAREST_FROM_OPEN_3_SESSIONS") and fam["level"] is not None:
                levels.append({"price": fam["level"], "label": "PROV " + fam["family"].replace("_SESSIONS", "").replace("MS_", "multi-session "), "kind": "PROVISIONAL"})
        tl_idx = pivot_lows(pcs_all, 0, len(pcs_all), 2) if long_c else pivot_highs(pcs_all, 0, len(pcs_all), 2)
        trend = None
        if len(tl_idx) >= 2:
            j1, j2 = tl_idx[-2], tl_idx[-1]
            off = len(pcs_all) - n_prev
            def y(j, pcs_all=pcs_all, long_c=long_c):
                return pcs_all[j].l if long_c else pcs_all[j].h
            if j1 - off >= 0:
                trend = {"x1_idx": j1 - off, "y1": y(j1), "x2_idx": j2 - off, "y2": y(j2), "label": "PROV frozen trendline (last two fractals)"}
        marks = [{"idx": n_prev, "price": cs[0].c, "label": "author-expected ORB entry (INFERRED: 09:20; no drawing)", "colour": "#2e7d32"}]
        for t in [t for t in trades if t["date"] == dstr][:2]:
            tt = t["signal_confirmed_at"][-5:]
            k = next((i for i, x in enumerate(cs[:36]) if hm(x.end) == tt), None)
            if k is not None:
                marks.append({"idx": n_prev + k, "price": float(t["entry_price"]), "label": f"Phase 3.6 {t['strategy']} {t['method'][-2:].strip()} {t['direction']}", "colour": "#d81b60"})
        (OUT / "charts" / f"{dstr}.svg").write_text(CH.render(f"{dstr} ORB case study ({CORR[dstr]}): first candle {O.geometry(cs[0])['colour']}", prev_rows, today_rows, levels, trend, marks, note="previous session (last 3 hours) | session from 09:15; levels in gold are source-defined, orange is the frozen research assumption, purple is provisional"))
    # day reports
    row_by = {r["date"]: r for r in d13_rows}
    fam_by: dict[str, list] = {}
    for r in lf13:
        fam_by.setdefault(r["date"], []).append(r)
    st_by = {r["date"]: r for r in st_rows}
    et_by = {r["date"]: r for r in et_rows}
    for dstr in ORB_DATES:
        r = row_by[dstr]
        d = date.fromisoformat(dstr)
        mins = m1[(m1["timestamp"].dt.date == d)].head(5)
        md = [f"# {dstr} - ORB case study ({r['correction_id']}, handwritten page {r['handwritten_pdf_page']})", "", "> Audit evidence only: no controller, no fills, no P&L. Provisional levels are research constructions, not source rules.", "",
              f"**Author:** {r['author_original_comment']}", "", f"* Expected direction: {r['expected_orb_direction']}", f"* Expected method: {r['expected_orb_method']}", f"* Expected entry candle: {r['expected_entry_candle']}", f"* Engine ORB status: {r['actual_orb_signal_status']}",
              f"* Phase 3.6 trade taken instead: {r['actual_irf_signal_and_other_trades']}", f"* Manual journal row: {r['manual_journal_row']}", "",
              "## Original one-minute data (first five bars)", "", "| time | open | high | low | close |", "|---|---|---|---|---|"] + [f"| {x.timestamp:%H:%M} | {x.open} | {x.high} | {x.low} | {x.close} |" for x in mins.itertuples()] + [
              "", f"## First candle {r['first_candle_ohlc']} ({r['first_candle_colour']}; body {r['body_pct']}%, upper wick {r['upper_wick_pct']}%, lower wick {r['lower_wick_pct']}%); previous day high/low/close {r['previous_day_high_low_close']}; gap {r['open_gap_points']}; EMA(200) {r['ema200_at_first_candle']}", "",
              "## Engine eligibility checks (colour-matching direction, engine order)", "", "| method | predicate | pass | observed | margin |", "|---|---|---|---|---|"]
        for x in pm_rows:
            if x["date"] == dstr and x["first_candle_colour_matches"]:
                md.append(f"| {x['method']} | {x['predicate']} | {x['pass']} | {str(x['observed'])[:110]} | {x['signed_margin']} |")
        md += ["", "## Candidate levels (what the first candle did against each construction)", "", "| family | status | level | broken | open already beyond | close - level |", "|---|---|---|---|---|---|"] + [
            f"| {x['family']} | {x['source_status'][:60]} | {x['level']} | {x['broken']} | {x['open_beyond_level']} | {x['close_minus_level']} |" for x in fam_by[dstr]]
        e = et_by[dstr]
        md += ["", "## Trend and trendline", "", f"* previous close {e['prev_session_last_close']} vs its EMA {e['prev_session_last_ema']} (margin {e['prev_close_minus_ema']}); first-candle close {e['first_candle_close']} vs EMA {e['ema_at_first_candle']} (margin {e['first_close_minus_ema']}); EMA change over the last previous hour {e['ema_change_last_hour_prev_session']}",
               f"* active trend: {e['trend_active_prev_close_vs_ema']}; structure variant: {e['trend_structure_variant']}; literal first-close test: {e['trend_literal_first_close_vs_ema']}", f"* frozen trendline: {e['trendline_frozen_reason']} (line at the open {e['trendline_value_at_open']}); any-pair-of-last-three: {e['trendline_any_pair_reason']}", "",
               "## Candle strength", "", f"* body {st_by[dstr]['body_pct']}%, opposite wick {st_by[dstr]['opposite_wick_pct']}%, close location {st_by[dstr]['close_location_pct']}%; STRICT {st_by[dstr]['strong_STRICT']}, MODERATE {st_by[dstr]['strong_MODERATE']}, LOOSE {st_by[dstr]['strong_LOOSE']}; owner pin test {st_by[dstr]['pin_bar_active_definition']} (wick/body {st_by[dstr]['pin_wick_to_body']}, close {st_by[dstr]['pin_close_distance_from_favourable_extreme_pct']}% from the favourable extreme; needs <= 30%)", "",
               "## Missing condition and required definition", "", f"* {r['conflicts_with_existing_code']}", f"* {r['required_correction_or_unresolved_definition']}", "", "## Variants (signal-only; disabled by default)", ""]
        bd = next(x for x in by_date if x["date"] == dstr)
        md += [f"* {k}: {bd[k] or 'no ORB signal'}" for k in V.VARIANTS]
        md += ["", f"![{dstr}](../charts/{dstr}.svg)", ""]
        (OUT / "daily" / f"{dstr}.md").write_text("\n".join(md) + "\n")
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1, default=str))
    print(json.dumps({k: summary[k] for k in ("frozen_orb_confirmed", "frozen_orb_equals_phase36_table", "journal_orb", "thirteen")}, indent=1, default=str)[:3500])
    for r in imp_rows:
        print(r["variant"], r["confirmed_orb_signals"], "disputed", r["disputed_dates_with_a_signal (of 13)"], "journal overlap", r["date_overlap_with_journal_orb_rows (of 89, descriptive)"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
