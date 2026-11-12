"""Write Phase 5.8 forensic interpretation after the independent measurements."""

from __future__ import annotations

import ast
import csv
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/phase5/phase58_codex_orb_forensic_audit"


def rd(name):
    with open(OUT / name, newline="") as f:
        return list(csv.DictReader(f))


def wr(name, rows):
    with open(OUT / name, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def table(rows, fields):
    def cell(v):
        return str(v).replace("|", ";").replace("\n", " ")
    return "\n".join(["| " + " | ".join(fields) + " |", "|" + "---|" * len(fields)] + ["| " + " | ".join(cell(r.get(k, "")) for k in fields) + " |" for r in rows])


# Each tuple has exact locator, source meaning, actual implementation and authority.
RULES = [
    ("S01", "1 overview; 2 timing figure; 3 Important; 11 Entry row", "Evaluate completed 09:15-09:20 candle; enter 09:20", "orb.py", "_scan", 62, "SOURCE_EXPLICIT", "Exactly first candle only; no later rescan"),
    ("S02", "1 overview and long/short table; 6 mirror", "Same long/short structure", "orb.py", "_scan", 60, "SOURCE_EXPLICIT", "Both directions evaluated independently"),
    ("S03", "3 Method 1 step 2; 4 Major/Inner table", "Method 1 previous-day top/bottom", "definitions.py", "prev_high_low", 399, "SOURCE_EXPLICIT", "Max wick high/min wick low of previous complete candles"),
    ("S04", "3 Method 1 step 3; 4 short step 3", "Break AND close strictly beyond relevant level", "orb.py", "_method1", 110, "SOURCE_EXPLICIT", "High/low and close beyond; high/low test redundant for valid OHLC"),
    ("S05", "3 long step 1; 4 short step 1", "Established trend with current price above/below 200 EMA and supporting structure", "definitions.py", "ema_prev_session_trend", 316, "QUALITATIVE_SOURCE_RESEARCH_VARIANT", "Active reference uses prior-session last close vs its EMA only; no current-price or structure requirement"),
    ("S06", "3 long step 3; 4 short step 3; 10 Preferred", "Strong green/red body with limited opposite wick", "definitions.py", "strong_bullish/strong_bearish", 85, "QUALITATIVE_SOURCE_NUMERIC_PROPOSAL", "60% minimum body, 20% maximum opposite wick, EPS=1e-9"),
    ("S07", "9 Candle-Quality opening; 10 Conditional", "Suitable rejection pin is conditional across methods", "definitions.py", "_pin", 98, "QUALITATIVE_SOURCE_OWNER_RECOMMENDED_PROPOSAL", "Owner-style wick >=2x body; close within favourable 30%; no intrinsic colour check"),
    ("S08", "4 Method 2 introduction and At entry row; 7 annotations", "Inner breakout may qualify before major extreme breaks", "orb.py", "_method2", 154, "SOURCE_EXPLICIT", "Correctly separate from Method 1; no PDH/PDL-break prerequisite"),
    ("S09", "4 inner minor swing/consolidation; 5 step 4; 6 mirror", "Smaller inner level inside previous-day range", "orb.py", "_method2", 145, "UNDEFINED_MECHANICAL_CONSTRUCTION", "Latest previous-session non-strict k2 fractal, excluding major extreme; single price not zone"),
    ("S10", "5 step 2; 6 falling line; 7 Trendline row", "Relevant rising lows/falling highs support the trend", "orb.py", "_method2", 168, "QUALITATIVE_SOURCE_ASSUMED_CONSTRUCTION", "At least 2 k2 pivots; last two only; direction and close side required"),
    ("S11", "5 schematic; 7 chart", "Supportive line through relevant anchors", "orb.py", "_method2", 174, "ENGINEERING_ASSUMPTION", "Slope per 5m candle index; project to index n, ignoring overnight elapsed clock time; no touch/proximity/no-intervening-crossing test"),
    ("S12", "5 step 5; 6 mirror; 7 9:20 row", "Opening candle closes beyond inner level", "orb.py", "_method2", 154, "SOURCE_EXPLICIT_ASSUMED_LEVEL", "Strict high/close or low/close beyond selected inner price"),
    ("S13", "5 step 7; 7 EMA filter row", "Near EMA requires convincing close beyond", "orb.py", "_method2", 188, "QUALITATIVE_SOURCE_NUMERIC_PROPOSAL", "Within inclusive 15-point band; directional close margin >=5; outside band bypasses"),
    ("S14", "7 Special Setup; 12 Established trend row", "Gap method may follow opposite prior trend", "orb.py", "_gap_setup", 202, "SOURCE_EXPLICIT", "No trend gate for gap method"),
    ("S15", "8 step 1; 9 mirror", "Directional gap relative to previous close", "definitions.py", "gap_info", 256, "SOURCE_EXPLICIT_ENGINEERING_CLOSE_CONVENTION", "Open minus official daily close; strict sign; minimum default 0"),
    ("S16", "8 step 2 and figure; 9 figure; 12 lower screenshot", "Gap/first candle pushes price through 200 average", "orb.py", "_gap_setup", 223, "CONFLICTING_TEXT_VERSUS_FIGURES", "Frozen requires previous official close old side and opening price already beyond current MA; figures permit body crossing"),
    ("S17", "8 step 3; 9 mirror", "Completed first candle must close beyond MA", "orb.py", "_gap_setup", 224, "SOURCE_EXPLICIT", "Strict close beyond current average"),
    ("S18", "8 step 4; 9 mirror; 10 figure", "Strong directional body OR suitable pin", "orb.py", "_gap_setup", 234, "QUALITATIVE_SOURCE_NUMERIC_PROPOSAL", "Strong/pin parameters as S06/S07; rejection threshold separately applied"),
    ("S19", "9 Reject lower wick; 10 Reject; 12 Wick row", "Reject adverse rejection wick across all methods", "definitions.py", "upper_rejection/lower_rejection", 145, "QUALITATIVE_SOURCE_NUMERIC_PROPOSAL", "33% flag in gap only; Methods 1/2 quality inherently caps opposite wick to 20% strong / at most30% owner-pin, so no default33% rejection can pass"),
    ("S20", "9 Not every gap is valid", "Reject excessively extended opening move", "orb.py", "_gap_setup", 245, "SOURCE_UNDEFINED_NOT_ENFORCED_BY_DEFAULT", "gap_max_points=None; optional cap measures overnight gap, not complete opening move"),
    ("S21", "2 DMA/EMA wording; 3/5/7 EMA; 8/9 DMA", "Identify the intended 200 average and timeframe", "definitions.py", "ma_value", 366, "SOURCE_CONFLICT_UNRESOLVED", "Reference EMA200 completed 5m closes; daily SMA/EMA are separate optional modes"),
    ("S22", "2 completed-candle rule; 11 Entry row", "No pre-emptive intrabar trade", "sessions.py", "_day_5m", 145, "SOURCE_TIMING_CAUSAL_AGGREGATION", "09:15..09:19 inclusive; n_unique minutes=5; bar_end09:20; excludes09:20 row"),
    ("S23", "200 average; no seed method in source", "Indicators must be available causally", "sessions.py", "causal_ema", 294, "ENGINEERING_CAUSAL_REQUIREMENT", "SMA seed at 200th completed5m close; alpha2/201; warm-up history supplied; no forward fill"),
    ("S24", "DMA alternative; source does not define daily series", "Daily average must exclude current day's close", "sessions.py", "build_session_contexts", 435, "ENGINEERING_CAUSAL_REQUIREMENT", "200 prior official daily bars only; current daily file includes warm-up from2024-09-02, so all evaluated sessions have enough daily history"),
    ("S25", "3/4 fixed parameters; 11 SL/Target table", "ORB SL30; target60 from entry", "params.py", "SourceConstants/TradeConfig", 253, "SOURCE_EXPLICIT_UNITS_OWNER_CONVENTION", "Index-point research convention; no strategy-specific direction/price inferred for manual rows"),
    ("S26", "No ORB source T1 split or fill-price definition", "Execution policy separate from signal confirmation", "selection.py", "fill_from_next_bar", 102, "OWNER_PORTFOLIO_POLICY_PROPOSED_FILL", "09:20 next1m open; portfolio T1=27; existing ledger used, no new exit calculation"),
    ("S27", "Handwritten p.5 20251127-1", "ORB long should have green closing", "orb_colour.py", "_scan", 34, "AUTHOR_CLARIFIED_LONG_SHORT_MIRROR", "Available opt-in wrapper; absent from A/B/C; short red inferred from original symmetry"),
    ("S28", "Handwritten pp.1-6 thirteen ORB expectations", "Author expected ORB instead of IRF/PDR", "orb.py", "all", 58, "INTENT_ONLY_UNRESOLVED", "No direction, level, method or exact entry provided; cannot infer a qualifying setup"),
    ("S29", "Handwritten p.4 20251112-1; p.5 20251211", "IRF should not activate at day's low", "irf.py", "_scan", 57, "AUTHOR_INTENT_UNDEFINED_MEASURE", "Restriction absent in baseline and Phase53; final-day low would leak future; running-low level still needs definition"),
    ("S30", "12 upper; 13 top/middle/bottom reference images", "Zones and earlier-session context occur in charts", "orb.py", "_method2", 141, "VISUAL_EVIDENCE_NO_ALGORITHM", "One-session pivot line omits zone/discretion; no supported multiday construction can be coded from axes-free drawing"),
    ("S31", "No PDF data-hygiene parameters", "Require usable current and verified previous sessions", "base.py", "_precheck", 186, "ENGINEERING_DATA_INTEGRITY", "Whole-session quality and previous-calendar gap checked before scanning; not entry-price action"),
    ("S32", "No ORB PDF optional signal cutoff", "Optional configured signal window", "base.py", "evaluate_session", 171, "ENGINEERING_OPTION_DISABLED", "signal_window_end=None; portfolio13:00 cannot suppress09:20"),
    ("S33", "No ORB PDF dedup/reset instruction", "Methods can co-confirm", "base.py", "_mark_concurrent", 253, "ENGINEERING_ANNOTATION_ONLY", "Annotates; does not delete. ORB ignores max_signals_per_session; six once-per-session paths, no persistent attempt state"),
]


def build():
    summary = json.loads((OUT / "audit_summary.json").read_text())
    observations = rd("orb_predicate_observations.csv")
    predicates = []
    by_pred = defaultdict(list)
    for o in observations:
        by_pred[(o["method"], o["predicate"])].append(o)
    line_by = {("Method 1", "previous_level_close"): ("orb.py", 110), ("Method 1", "trend"): ("orb.py", 119), ("Method 1", "quality"): ("orb.py", 123),
               ("Method 2", "inner_defined"): ("orb.py", 145), ("Method 2", "inner_close"): ("orb.py", 154), ("Method 2", "trend"): ("orb.py", 163), ("Method 2", "trendline"): ("orb.py", 168), ("Method 2", "quality"): ("orb.py", 183), ("Method 2", "near_ma"): ("orb.py", 188),
               ("Gap/200DMA", "gap_direction"): ("orb.py", 206), ("Gap/200DMA", "ma_available"): ("orb.py", 217), ("Gap/200DMA", "gap_crossing"): ("orb.py", 223), ("Gap/200DMA", "ma_close"): ("orb.py", 224), ("Gap/200DMA", "quality"): ("orb.py", 234), ("Gap/200DMA", "gap_cap"): ("orb.py", 245)}
    for (method, pred), rows in by_pred.items():
        file, line = line_by[method, pred]
        failed = [r for r in rows if r["passed"] != "True"]
        hand = sorted({r["date"] for r in failed if r["handwritten_dispute"] == "True"})
        removal = sorted({r["date"] + " " + r["direction"] for r in failed if r["single_gate_removal_qualifies"] == "True"})
        authority = rows[0]["authority"]
        predicates.append({"method": method, "predicate": pred, "path": "src/nifty_trading/strategies/" + file, "line": line,
                           "source": rows[0]["source"], "explicit_in_pdf": "YES" if authority == "SOURCE_EXPLICIT" else "QUALITATIVE_OR_UNRESOLVED_SEE_AUTHORITY",
                           "author_clarified": "No numeric/construction clarification recovered", "owner_approved": "Research variant recorded in repo" if "OWNER_RESEARCH" in authority else "Not evidenced as exact author rule",
                           "authority": authority, "engineering_assumption": authority != "SOURCE_EXPLICIT",
                           "disputed_dates_failing_either_direction": "; ".join(hand),
                           "single_gate_removal_would_qualify_date_direction": "; ".join(removal),
                           "effect": "All other gates retained; sole-gate removal diagnoses sensitivity only. Both directions shown separately in observations."})
    # Additional wrapper/data gates, not reached just through the method matrix.
    extra = [
        ("GLOBAL", "usable_session", "base.py", 187, "No source threshold; data integrity", "May exclude whole day when data corrupt/missing; no disputed day suppressed this way"),
        ("GLOBAL", "verified_previous_session", "base.py", 194, "No source threshold; data integrity", "Changing could use a nonadjacent prior session; not justified"),
        ("GLOBAL", "complete_candles_exist", "base.py", 166, "PDF p.2 completion", "Missing opening candle cannot be repaired or shifted"),
        ("GLOBAL", "only_first_candle", "orb.py", 62, "PDF pp.1-3/11", "Later rescanning would create a different strategy and delayed entries"),
        ("GLOBAL", "signal_window_end", "base.py", 171, "Engineering option None", "No effect in audited configuration; ORB always09:20"),
        ("GLOBAL", "directional_colour", "orb_colour.py", 34, "Handwritten p.5, original p.1 mirror", "Removes red long/green short pin confirmations; does not add missing signals"),
        ("PORTFOLIO", "confirmed_valid_execution_status", "selection.py", 48, "Separate owner portfolio policy", "Invalid signals never reach selection"),
        ("PORTFOLIO", "exact_next1m_fill_bar", "selection.py", 102, "Proposed causal fill", "Missing exact bar blocks entry; no later fill invented"),
        ("PORTFOLIO", "cutoff13_and_state_and_collision", "trading_day.py", 180, "Owner policy; no artificial priority", "First executable chronologically; simultaneous cross-strategy unresolved; second only PDR/PDS after initial full stop"),
    ]
    for method, pred, file, line, source, effect in extra:
        predicates.append({"method": method, "predicate": pred, "path": "src/nifty_trading/strategies/" + file, "line": line, "source": source,
                           "explicit_in_pdf": "SEE_SOURCE", "author_clarified": "Colour only", "owner_approved": "See source traceability",
                           "authority": "DATA_OR_PORTFOLIO_OR_AUTHOR_WRAPPER", "engineering_assumption": True,
                           "disputed_dates_failing_either_direction": "See per-date evidence; not inferred from absent records",
                           "single_gate_removal_would_qualify_date_direction": "No blanket removal tested", "effect": effect})
    wr("orb_all_entry_predicates.csv", predicates)
    mapped = [{"id": ident, "pdf_page_and_exact_locator": locator, "source_rule": source,
               "code_path": ("src/nifty_trading/data/" if file == "sessions.py" else "src/nifty_trading/strategies/") + file,
               "function": function, "line": line, "authority": authority, "source_to_code_assessment": assessment}
              for ident, locator, source, file, function, line, authority, assessment in RULES]
    wr("orb_source_to_code_mapping.csv", mapped)
    branch_rows = []
    for file in ("orb.py", "orb_colour.py", "orb_candidates.py", "base.py"):
        path = ROOT / "src/nifty_trading/strategies" / file
        text = path.read_text()
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.Return)):
                expression = ast.get_source_segment(text, node.test if isinstance(node, ast.If) else node)
                branch_rows.append({"path": str(path.relative_to(ROOT)), "line": node.lineno,
                                    "kind": type(node).__name__, "expression": expression.replace("\n", " ")})
    wr("code_branches_and_returns.csv", sorted(branch_rows, key=lambda r: (r["path"], r["line"])))
    implementation = """# ORB implementation: complete path review

The executable reference is Phase 3.6 / Phase 5.5 A and B, not ProposalConfig's standalone default. `research/phase3.py:47` explicitly selects `EMA_PREV_SESSION_CLOSE`, lifts cap to99 and uses MODERATE/OWNER_2X_CLOSE30. C changes gap crossing only. Standalone default is STRUCTURE_EMA_SWING2; confusing these would misattribute exclusions. Approval claims below mean repository-recorded owner research approval, not independent evidence of the author's exact discretionary rule.

Every line of orb.py and its helpers was read. [Numbered complete source appendix](source_code_numbered.md) preserves all lines; [every branch and return](code_branches_and_returns.csv) includes all core, wrapper and candidate returns. [Function index](code_function_index.csv) provides exact start lines. [Predicate inventory](orb_all_entry_predicates.csv) answers authority and isolated-removal effects; [observations](orb_predicate_observations.csv) provides every boolean/measurement for both directions, including gates hidden by early returns.

```mermaid
flowchart TD
 raw["data/processed/nifty50 1m start-labelled candles"] --> quality["sessions.classify_session:185 - integrity/calendar/complete09:15"]
 quality --> agg["sessions._day_5m:145 - 09:15..09:19, end09:20"]
 agg --> ema["sessions.causal_ema:294 - completed closes, SMA seed200"]
 daily["prior official daily closes and warm-up 1m"] --> context["sessions.build_session_contexts:371 - prior session and daily MA"]
 ema --> context
 context --> check["base.evaluate_session:159 / _precheck:180"]
 check --> scan["orb._scan:58 - only cs0, LONG and SHORT"]
 scan --> m1["_method1:105 - PD extreme close > trend > quality"]
 scan --> m2["_method2:134 - inner > trend > line > quality > nearMA"]
 scan --> gap["_gap_setup:202 - gap > MA available > crossing > close > shape > cap"]
 m1 --> rec["base._rec:227 - timestamp candle END09:20"]
 m2 --> rec
 gap --> rec
 rec --> conc["base._mark_concurrent:251 - annotations only"]
 conc --> port["trading_day.run_trading_day:123 - chronological first fillable signal"]
 irf["irf._scan:57 - opening range then intraday failure"] --> port
 port --> fill["selection.fill_from_next_bar:102 - exact next1m open"]
```

## orb.py line groups

| Lines | Review |
|---|---|
| 1-45 | Imports and source claims. Header says09:20; implementation really uses cs0. No later breakout loop. |
| 48-65 | Class constants, previous-session requirement; both directions and all3 methods once. No signal-ranking or dedup here. `gap_before` is unused by ORB. |
| 68-72 | Copies first high/low/close and previous extrema/official close; reference close is not a fill. |
| 74-79 | Strong OR conditional pin. Pin route has no colour check. Source p.10 allows pin but later author explicitly disallows red longs. |
| 81-86 | Near-MA check uses opening candle EMA under prior-session trend modes; correctly avoids using yesterday's value for this test. |
| 88-100 | Trend dispatch; unknown -> NOT_EVALUATED, false -> INVALIDATED; immediate return before quality. Baseline only last previous5m close vs its EMA. |
| 105-129 | PDH/PDL strict break-and-close; no break -> None (not an invalidated record). New local FSM; trend return first, quality return next, otherwise confirm. |
| 134-166 | Select previous-session latest non-strict5bar pivot inside range. No level or no break -> None. Trend failure masks line/shape/near-MA failures in normal record; audit evaluates all. |
| 168-182 | Two confirmed pivots needed. Last2 low/high anchors; slope per bar; opening projection n-j2; rising/falling and close-side tests. No zone, line-contact distance, or penetration check. |
| 183-197 | Quality then near-MA branch (15 band,5 margin). Far-away wrong-side current price is not explicitly excluded; prior trend is only a proxy. Emits confirmed research result with unresolved inner/MA identifiers. |
| 202-221 | Directional gap; invalid direction -> None. MA warm-up -> NOT_EVALUATED. No established-trend gate (correct exception). |
| 222-232 | Previous official close vs prior EMA plus open vs current EMA. Open not beyond -> None even if body crosses (diagram mismatch). Close must independently be beyond. |
| 233-243 | Strong OR pin and no adverse rejection; separate33% only here. At baseline, M1/M2 already cap adverse wick below33%, so separate omission there does not permit a baseline33%-wick false positive. |
| 244-254 | Optional abs(gap) cap. None leaves extension exclusion unapplied and unresolved. Confirmation has no later re-arm or reset. |

## Numerical definitions and tolerances

`definitions.py:24` EPS=1e-9 applies to shape thresholds, not level/MA breakout strictness. Body/range >=0.60; opposite wick/range <=0.20 (`params.py:26`). STRICT70%/15%, LOOSE50%/25% are alternatives, not PDF numbers. Owner pin: rejection wick>EPS and >=2*body-EPS; favourable-close distance <=0.30*range+EPS (`definitions.py:98`). This can admit opposite-colour/doji candles. A zero-range candle never confirms. Rejection wick >=0.33-EPS. Unused alternative pin profiles are STRICT70% wick/25% body/10% opposite, MODERATE60/33/15, LOOSE55/40/20. k=2 is hardcoded in ORB Method2 (not p.swing_k); fractals allow equal extremes, unlike strict structure-trend swings. Slopes must be >0/<0 exactly; price must be strictly on trend side. No price tick buffer or minimum breakout distance. Near-MA <=15 points and directional margin>=5 with no EPS. Gap minimum0, maximumNone. EMA period200, alpha2/201, SMA seed; daily MA period200. First5m needs5 unique one-minute rows, not4. Optional signal cutoffNone; controller cutoff13:00 inclusive. Owner execution stop30/target60 for ORB and portfolio T1=27 are separate from qualification. No parameter was selected through a grid or outcomes.

## State, returns, resets and suppression

Local variables `out`, `d`, `fn`, `c`, `levels`, `props`, `sat`, `unresolved` and local `SetupFSM` have invocation/method scope. Method2 adds `pcs`, `n`, `piv`, `lvl`, `tl_idx`, `j1/j2`, `slope`, `line_now`, `ok_dir`, `on_side`, `ema`, `beyond`; Gap adds `g`, `mode`, `ma`, `ma_prev`, `crossed`, `closed_beyond`, `shape_ok`, `rejected`. There is no persistent ORB attempt state, per-day fired flag, retry queue, deactivation flag or saved position in ORB. Each evaluate call recomputes deterministically. Terminal local FSM records confirmation/invalidation only. New day means a new context; no state reset bug was found.

Core silent None returns: Method1 no level break; Method2 no inner or no inner break; Gap wrong gap or no MA crossing. All later failures return structured records. `_trend_gate` unknown/false returns stop; caller returns it. Concurrent methods are labelled by base but not removed. `max_signals_per_session` is not consumed by ORB; engine output therefore cannot be reduced by that cap. `signal_window_end` can drop confirmations only if explicitly configured; None here. Colour wrapper invalidates confirmed records post hoc; it leaves stale execution metadata (defect D03). Candidates reuse base methods and replace one family; not selected by default.

## Controller and IRF

The combined controller is `trading_day.py`, not per-strategy `selection.apply_policy`. It groups confirmed signals chronologically, rejects ineligible fills/cutoff, respects one active position and allowed second PDR/PDS after first full stop. Opposite or cross-strategy same-time signals leave an unresolved collision without an approved tie-break. Same-direction same-strategy methods describe one entry. There is no automatic IRF/ORB priority.

IRF baseline builds IRH/IRL from opening candle; later candles above IRH establish the failure attempts. Method1 immediate next close back inside; Method2 extension/pullback and support-break2A or red resistance-failure2B; Method3 compressed sweep plus support break. Baseline Method2B is its own resistance path and does not universally require Method2A's extension/red bookkeeping. B/C change2A support to first-red low and apply provisional28-point EMA clearance. The complete first-IRF levels and state traces are in the selection timeline, not inferred from the journal. Handwritten day's-low restriction is absent in all; no unprovided running-low or final-day-low filter is added.

`base.on_candle:259` is a separate integration adapter: discards timestamp rows beyond now and evaluates only after minute19/24/etc. It rebuilds contexts without explicitly passing official daily or external warm-up frames. That adapter's data contract needs integration validation before a live-use claim. This audit verifies the historical context/engine path used by A/B/C, not broker latency or realtime wiring. Whole-session offline quality classification can exclude a day based on later corruption; this is an offline data-selection policy, not evidence that a09:20 strategy can foresee later data quality. No full-session-quality exclusion explains the13 disputed days.
"""
    (OUT / "orb_implementation_line_by_line.md").write_text(implementation)
    counts = [{"config": k, **v} for k, v in summary["configurations"].items()]
    compact_fields = ["config", "orb_signal_dates", "no_orb_signal_evaluable_dates", "orb_executed_dates", "orb_signal_no_orb_execution", "irf_executed_dates", "another_strategy_executed_dates", "no_automated_trade_dates"]
    (OUT / "orb_level_construction_comparison.md").write_text("""# Level and trendline construction

Method1 previous-day max wick high/min wick low is supported by p.4 top/bottom table. Replacing this with an arbitrary multiday resistance would conflate methods. Method2 already breaks an inner level without needing PDH/PDL; the code does not omit all inner breakouts.

The discrepancy is the construction. The PDF names a minor swing or consolidation top, and relevant trendline anchors; code selects the latest confirmed non-strict k2 pivot of the previous session, then uses the last two opposite pivots. Its line extrapolates in candle-index space. These are engineering choices. Equality pivots can create multiple plateau anchors and zero slope (rejected); latest-pair rejection does not imply no discretionary supportive line exists. All anchors used are confirmed before today's open, so the construction itself has no future-pivot leak. The line's current-close side test is causal at09:20.

Real screenshots pp.12-13 use horizontal bands and multi-session context. They do not specify boundaries, number of touches, body versus wick priority, zone merging, lookback, session inclusion or anchor ranking. P.7 inner line is explicitly approximate. A band is not safely interchangeable with one latest fractal. The audit preserves the prior five actual sessions for each date so the missing choices can be drawn by the author. It does not fabricate a multiday-zone signal candidate.

Three isolated level/line sensitivities are measured: most extreme previous-session inner fractal instead of latest; nearest confirmed inner level ahead of the opening price (chosen without seeing the first close); any supportive pair among last three confirmed pivots instead of last two. Each retains trend, quality and timing. None is an author-confirmed replacement. Numerical raw levels, anchors, slope, projection, signed breakout distances and all gates are in `orb_method_paths.csv`, `orb_predicate_observations.csv` and daily files. Do not rank an author's likely method by the fewest failed predicates: that is not evidence of the intended setup.

No future swing is fitted. Prior five sessions are supplied for human review only, not used to select additional trades. Body/wick reference comparison remains an unresolved level-definition question, not proof that an unbroken PDH should have been broken under Method1.
""")
    impact = summary["candidate_impact"]
    (OUT / "orb_moving_average_investigation.md").write_text("""# Moving-average investigation

PDF pp.2,3,5,7 use EMA or DMA/EMA; pp.8-9 use DMA. In ordinary literal daily terminology SMA200 daily would use200 daily closes, a different horizon from200 five-minute closes. The ORB source does not define a daily formula or say that DMA must literally be daily. Axes-free real screenshots do not identify exact indicator settings. Handwritten p.3 explicitly labels IRF's chart average200 EMA,5min TF; this supports the author's intraday chart convention but does not independently settle ORB.

Reference: EMA200 of concatenated completed5m closes, including the opening close at09:20; alpha2/201, SMA-seeded at candle200. Trend gate uses previous session's last completed5m close against that candle's EMA. Gap prior-close gate uses **official daily close** against the prior last5m EMA, not the prior last5m close used by trend. These two can differ without an arithmetic defect. Current opening average is known only at09:20; no09:15 precomputed-open trade is claimed. Excluding overnight elapsed minutes is standard bar-count computation here, a defined research convention.

Daily SMA200/EMA200 are separately computed from strictly prior official daily closes. Insufficient daily bars produce NaN, never zero or a partly warmed indicator. Their omission from a chart is explicitly labelled unavailable or off scale. No evidence supports replacing the EMA with daily SMA as a confirmed correction. The `gap_daily_sma` sensitivity changes the gap indicator only; Method1/2 trend remains the reference, deliberately isolating the family.

Gap mismatch: frozen open-beyond gate cannot reproduce pp.8-9 schematic geometry where first body spans the line. Isolated gap-candle alternative allows prior-old-side plus directional gap plus (open already beyond OR first range reaches average), with completed close beyond and original quality. It is additive relative to baseline for a fixed indicator. The directional gap and previous-old-side conditions are retained; this is not every first-candle EMA cross.

Fresh independent OHLC aggregation and EMA recurrence results are recorded below. Causal prefix and future-mutation tests supplement arithmetic equality. A fully formed day's classification still uses offline day-quality checks; live adapter parity has not been claimed.

""" + json.dumps(summary["data_verification"], indent=2) + "\n\n" + table([r for r in impact if r["variant"] in ("gap_candle", "gap_daily_sma", "trend_current")], ["variant", "added_method_direction_signals", "removed_method_direction_signals", "changed_handwritten_dates", "authority"]))
    freq = rd("predicate_frequency.csv")
    missing_a = {r["date"] for r in rd("orb_all_manual_journal_dates.csv")
                 if r["config"] == "A" and r["orb_signal"] == "False" and r["session_status"].startswith("USABLE")}
    missing_freq = []
    for row in freq:
        subset = [r for r in observations if r["date"] in missing_a and r["method"] == row["method"]
                  and r["direction"] == row["direction"] and r["predicate"] == row["predicate"]]
        missing_freq.append({"method": row["method"], "direction": row["direction"], "predicate": row["predicate"],
                             "failed_dates": sum(r["passed"] != "True" for r in subset), "missing_evaluable_dates": len(missing_a),
                             "reached_and_failed_dates": sum(r["reached_in_code"] == "True" and r["passed"] != "True" for r in subset),
                             "interpretation": "No frozen ORB signal in either direction; unknown author direction. Counts overlap."})
    wr("predicate_frequency_missing_only.csv", missing_freq)
    (OUT / "orb_candle_strength_investigation.md").write_text("""# Candle confirmation investigation

Original pp.3-7 require convincing directional body and limited adverse wick; pp.9-10 allow a suitably positioned pin. The figures illustrate shape qualitatively. No source gives60%,20%,33%,2x or30%. Pixel measurement of an illustrative PDF candle cannot establish a historical OHLC ratio or a numerical trading threshold.

Reference strong-body threshold is MODERATE: body/range>=60%, opposite wick/range<=20% with1e-9 ratio tolerance. Pin: favourable wick>=2x body and close in favourable30%, also tolerance1e-9 in price geometry. Gap separately rejects adverse wick>=33%. Methods1/2 do not run that33% flag, but their baseline strong/pin routes already cap it below33%; that omission has no extra baseline acceptance effect. Original pin predicate can admit a red long, explicitly rejected by handwritten p.5. Colour candidate removes such signals; it cannot repair missing trades.

Every examined opening candle has O,H,L,C, absolute body/range, body percentage, upper/lower wick and close location in `orb_all_manual_journal_dates.csv`, `orb_13_handwritten_disputes.csv` and daily files. Every method/direction also has signed distance beyond its actual level in `orb_method_paths.csv`; negative means close stayed short of level. Both directions remain visible: a green candle does not prove the author wanted a long. The handwritten source supplies no author candle/level, so exact source-example ratio matching is unavailable.

LOOSE50%/25% replaces one numerical profile only. It is a sensitivity analysis of an unspecified numeric family, not evidence that50%/25% is correct. Removing quality altogether would contradict an explicit qualitative source filter and is not proposed. Thin/doji first candles and large rejection do not become proven valid simply because a cutoff has no printed percentage.

Failure counts below are directional paths on evaluable journal-ORB dates, including gates not reached because a prior gate failed. They overlap. Opposite-direction failures are not proof the author's unknown-direction trade was invalid. `sole_failed_gate_dates` identifies where a numerical gate alone prevents that path; it still does not validate the counterfactual trade.

""" + table([r for r in freq if r["predicate"] == "quality"], ["method", "direction", "failed_dates", "evaluated_dates", "reached_and_failed_dates", "sole_failed_gate_dates"]) + "\n\n" + table([r for r in impact if r["variant"] in ("strength_loose", "colour")], ["variant", "added_method_direction_signals", "removed_method_direction_signals", "changed_handwritten_dates", "authority"]))
    (OUT / "orb_implementation_defects.md").write_text("""# Defects, fidelity gaps and correction status

| ID | Finding | Evidence | Classification | Corrective action |
|---|---|---|---|---|
| D01 | Frozen pin route admits red-candle LONG | Handwritten p.5 20251127-1 explicitly says green closing; `orb.py:78`, `definitions.py:98`; diagnostic source test | Confirmed mismatch with later author clarification; already isolated by opt-in colour variant. Not a cause of missing ORB. | Apply colour wrapper in a separately approved future configuration; long requirement directly supported, short mirror p.1. Keep this audit's active behaviour unchanged. |
| D02 | Frozen gap requires OPEN beyond average | PDF pp.8-9 figures open on old side; p.12 lower real chart; `orb.py:223`; two-direction source-geometry test | Source/implementation mismatch against figures, with conflicting wording; alternative supported, unique intended rule unresolved | Retain diagnostic first-candle-cross candidate; confirm which crossing author means and indicator before default activation. |
| D03 | Opt-in colour invalidation leaves stale confirmation metadata and stamps transition09:15 | `orb_colour.py:35-39` mutates status/reason but not `execution_config`; inherited metadata still says confirmed; uses candle start instead of end in trace. Strict expected-failure regression added | Confirmed software metadata defect in optional wrapper; `is_valid` checks status first, so it does not execute the rejected trade and does not explain missing signals | Safe future metadata-only patch: rebuild execution_config as NOT_A_CONFIRMED_SIGNAL and timestamp09:20, rederive concurrent-method annotations. Not patched under audit-only instruction. |
| D04 | Method2 near-EMA and latest pivot/last-two trendline are not source-defined algorithms | pp.4-7; `orb.py:145-190`; full gate observations | Engineering assumptions, sometimes restrictive; not proven programming errors | Require drawn levels/anchors and numeric conventions; do not substitute a parameter set to match journal. |
| D05 | Excessive opening extension filter not enforced when capNone | PDF p.9 rejection box; `orb.py:245-252` | Missing mechanical source definition; potentially over-permissive rather than missing-signal cause | Obtain definition of opening move, reference point, range/gap measure and cap; do not invent one. |
| D06 | Trend proxy has no explicit current EMA-side or structural confirmation | PDF pp.3-7 price/structure; `definitions.py:316`; `phase3.py:47` | Recorded owner research variant, not author-complete implementation; may exclude a new trend or admit current wrong-side price | Preserve as labelled reference, seek author operational trend definition. Current-close-only alternative tests timing but still omits structure. |
| D07 | IRF day's-low exclusion absent | Handwritten pp.4-5; both IRF modules | Unimplemented author intention with undefined reference/tolerance; cannot prove a specific IRF should be rejected from final-day hindsight | Clarify running-known low vs initial range vs prior candle; no new IRF rule in this audit. |

No objectively reconstructible missed author trade has been proved solely by an execution/controller bug. That statement does **not** prove the ORB engine faithfully captures the author's discretionary ORB. Tests that only compare candidate-default to frozen records or snapshot counts validate internal consistency, not strategy fidelity.

No active strategy, configuration, previous ledger or Phase5.7 file was changed. New diagnostic module/tests and Phase5.8 reports only. No orders, no commit/push, no new P&L/exit simulation.
""")
    (OUT / "orb_required_author_clarifications.md").write_text("""# Required author clarifications and precise action plan

1. For each of the13 handwritten disputes and unmatched journal ORB dates, annotate the supplied actual chart: direction, Method1/2/gap, exact horizontal price or zone bounds, establishing candles, first-candle close and intended09:20 entry. If using other vendor candles, supply that chart's symbol/feed and OHLC. The label ORB alone is not an entry specification.
2. Is Method1 strictly previous-day range top/bottom (p.4), while an inner/multiday structure belongs to Method2? If a multiday zone independently qualifies, define that fourth/generalized setup explicitly rather than silently rewriting Method1.
3. Inner level: latest swing or most relevant consolidation, eligible lookback sessions, body/wick boundaries, number of touches, stale-level invalidation, tolerance and selection when several exist. Are flat-top pivots permitted? Can a level be chosen after seeing the opening close?
4. Trendline: identify anchors known by09:15, pivot-confirmation delay, whether older-session anchors allowed, index-space versus elapsed-time slope, intervening-candle penetration, required proximity and price-side test. Do not require anchors confirmed by future candles.
5. Trend: previous-session state versus09:20 current price, whether both price and structure are necessary, and what structure means. Does the opening move itself establish an uptrend? Repository-recorded owner research approval is not proof of exact author intention.
6. Average: exact indicator name, period200, close input, chart timeframe, seed/warm-up, session inclusion. Confirm whether DMA is informal EMA terminology or literal daily SMA; these remain distinct.
7. Gap crossing: must the OPEN already be beyond average, or may opening body cross as pp.8-9 draw? Must prior official close be on old side, or only prior chart candle close? Require positive gap for a long? Should crossing be judged against current09:20 or prior-session average?
8. Candle strength: operational large body/small wick, whether any fixed percentages intended, permissible conditional pins, whether green long applies to every pin and whether red short symmetry is accepted. The exact long colour correction is source-supported now; it removes false confirmations.
9. Excessive extension: overnight gap size, first5m range/body, distance from MA or another measure? Define units and cap. Sourcequalitative exclusion presently stays unresolved.
10. Entry labels: journal09:15 could label opening candle, but without a direction/price/order timestamp it is not proof of a09:15 executable entry. Confirm label convention separately; preserve causal09:20 decision.
11. IRF at day's low: known-running low versus first5m low versus prior candle or final-day low; wick/body/close/fill; exact comparison tolerance. Final-day low cannot be an entry-time filter.

Safe next implementation work, after this audit: fix optional-wrapper status metadata; maintain explicit authority/source labels; add author-approved source fixtures. Long green rule is directly clarified but enabling it changes signal behaviour, so leave reference configuration intact until a separately scoped activation. Gap-candle candidate is supported by drawings but source wording/MA must be resolved before claiming it is the unique rule. Do not relax strength, add multiday zones, alter IRF, widen timing or give ORB priority to improve agreement. Keep first-valid chronological selection, completed-candle timing, previous-day Method1 distinction, causal indicators, gap-direction requirement and adverse-wick exclusions.
""")
    irf_rows = [r for r in rd("orb_vs_irf_selection_timeline.csv") if r["manual_orb_date"] == "True" and r["irf_executed"] == "True"]
    (OUT / "orb_vs_irf_findings.md").write_text("# ORB versus IRF: explicit per-date chronology\n\nEvery row below is a literal manual ORB date on which the existing portfolio ledger executed IRF. `orb_vs_irf_selection_timeline.csv` gives all methods/directions and full first-IRF levels/state traces; each daily page expands the failed ORB gates and every5m event. No author direction is inferred. No valid author trade is proved by merely removing one gate.\n\n" + table(irf_rows, ["config", "date", "orb_actual_signal_time", "irf_first_signal_time", "irf_first_signal_method", "ledger_trades", "gap_candidate_signal"]) + "\n\nFor each no-ORB row, the exact preventing predicates are in `why` in the CSV and the both-direction method tables in daily/. IRF occurs after09:20; sourceORB only offers that opening decision. If confirmedORB is absent, the controller cannot select it. A signal-only candidate at09:20 would precede a laterIRF causally if no simultaneous other-strategy conflict exists; that is a candidate counterfactual, not a verified author correction or simulated trade.\n")
    source_readme = """# Phase 5.8 - independent ORB forensic audit

Completed original-source examination and candle/signal reconstruction; no active strategy changes or profitability backtest. The original13-page PDF and all6 handwritten pages were visually inspected. Existing reports were cross-checks, not the source of rule conclusions.

The previous controller conclusion holds in its **narrow software sense**: no earlier confirmed frozenORB was silently bypassed forIRF on a journal-ORB day. It does **not** establish source fidelity. The engine's latest-fractal inner level, last-two-fractal trendline, numerical shape filters and prior-sessionEMA trend are mechanical interpretations. Gap-open requirement contradicts both source gap figures. The green-long clarification is absent from the frozen engine and A/B/C. Many author-expected entries remain unresolved because no direction, method or level is recorded.

## A. What is implemented

Method1: previous-day extreme broken and closed beyond at09:20, prior-sessionEMA trend, strong body or pin. Method2: latest inner non-strict5bar fractal in previous session; same trend; last-two-pivot trendline supportive; strong/pin and nearEMA15-point band /5-point close margin. Gap: directional gap, prior close old side and OPEN beyondEMA, first close beyond, strong/pin, rejection-wick filter; extension capNone. Both directions, completed first candle only. Baseline trend is prior-sessionEMA location, not standalone ProposalConfig structure default. See [source rules](orb_original_source_rules.md), [traceability](orb_source_to_code_mapping.csv), [line-by-line audit](orb_implementation_line_by_line.md), [predicates](orb_all_entry_predicates.csv).

Missing/unfinished source components: mechanically defined inner/consolidation zones, relevant trendline choice, exact structural trend, excessive opening extension and indicator ambiguity; author green-long not enabled by default. Some current rules are narrower (open beyondMA, fixed thresholds, latest-pair construction), while the prior-only trend and disabled extension can be more permissive. There is no universal claim all implementation differences reject valid trades.

## B. Independently verified journal coverage

"""
    source_readme += f"Original workbook: **{summary['journal_total_rows']} data rows**, **{summary['orb_journal_rows']} ORB rows**, **{summary['orb_unique_dates']} unique ORB dates**, **{summary['orb_evaluable_unique_dates']} evaluable ORB dates**. Row-level records are preserved in `orb_manual_journal_rows.csv`; unique-date/config records in `orb_all_manual_journal_dates.csv`. Five Saturday entries are retained as journal inconsistencies, not silently shifted. The workbook Summary sheet's189 total is not the data-row count.\n\n"
    source_readme += table(counts, compact_fields)
    source_readme += "\n\nCounts are unique dates per configuration. `no_orb_signal_evaluable_dates` excludes no-session journal dates. The signal/no-execution column isolates portfolio effects. IRF and other-strategy date counts can overlap when a second trade occurs; they are not a mutually exclusive partition. `first_executed_strategy_counts` in audit_summary.json is a partition. A is frozen Phase3.6; B is Phase5.3; C changes B's gap crossing only. All executed entries/exits shown are existing ledger records verified against freshly generated signals and raw entry bars, not new trades.\n\n"
    source_readme += """## C. Root causes

All failures are preserved per method and direction in `orb_predicate_observations.csv` and daily/. `predicate_frequency.csv` gives reached failures, latent failures and sole-gate sensitivities without treating unknown author direction as known. `predicate_frequency_missing_only.csv` restricts those counts to the50 evaluable no-signal dates. Previous-day unbroken is a source-supported Method1 exclusion; it does not disprove a possible Method2 setup. Inner selection and trendline failures reject the current construction; they do not prove no author-valid level exists. Strength percentages and nearMA distances are proposals. Gap crossing is a source conflict, not an unambiguous author exclusion. No root cause is forced from the method with fewest failed gates.

## D. ORB versus IRF

The count of dates withIRF is in the table above; every date is enumerated with first signals and exact failed gates in [selection timeline](orb_vs_irf_selection_timeline.csv), [readable chronology](orb_vs_irf_findings.md) and daily/. First selection was independently checked against freshly generated fillable signals and raw1m bars, without running the controller's exit model. No automatic strategy priority is added. The author's day's-lowIRF exclusion is absent and undefined; final-day hindsight is not used.

## E. Corrections and unresolved decisions

[Defects](orb_implementation_defects.md) separates confirmed optional-wrapper metadata defect, author-colour mismatch, source-conflicting gap interpretation, and undefined constructions. Green longs are explicitly clarified; activating that rule removes signals. Gap-candle is supported by figures but indicator/text still need author resolution. Level/trendline/strength changes require exact definitions. The corrective plan is in [author clarifications](orb_required_author_clarifications.md). No active correction was enabled under the audit-only instruction.

## F. Independent verification

Fresh raw aggregation, independent EMA recurrence, independent six-path predicate reconstruction, frozen/candidate signal parity and prefix invariance were checked. A/B/C confirmed signals were regenerated and compared to stored signals; all ledger fills were checked against raw1m opens. Whole-dataset first-entry chronological choice was checked without recalculating outcomes. [Independent review](independent_review.md) records results and limitations. No independent second person/agent is implied by that filename.

"""
    source_readme += f"Examined **{summary['handwritten_unique_disputes']} handwritten disputes** and all journalORB dates; **{summary['charts']} annotated actual-candle charts**, with daily1m/5m files and prior-five-session evidence. The13 handwritten source setups remain unproved where no exact level/direction exists; hypothetical candidate eligibility is distinguished from author validity.\n\n"
    source_readme += "Frequent failed gates on the50 evaluable frozen no-signal dates (both possible directions, overlapping counts; not author-direction attribution):\n\n"
    source_readme += table([r for r in missing_freq if (r["method"], r["predicate"]) in (("Method 1", "previous_level_close"), ("Method 2", "trendline"), ("Gap/200DMA", "gap_crossing"))], ["method", "direction", "predicate", "failed_dates", "missing_evaluable_dates", "reached_and_failed_dates"]) + "\n\n"
    source_readme += table(impact, ["variant", "added_method_direction_signals", "removed_method_direction_signals", "changed_unique_dates", "changed_handwritten_dates", "authority"])
    source_readme += """\n\nSignal differences count method/direction records, not unique dates or new trades. Every alternative changes one family; all are disabled. No candidate is chosen by journal agreement or profitability. False positives relative to an unrecorded discretionary author decision are unknowable; candidate rows disclose this rather than claiming higher agreement proves fidelity.

## Evidence and reproduction

`ORB_Forensic_Verification.xlsx` contains formula-linked counts and detailed source, journal, disputes, chronology, path observations and candidates. `charts/` covers all evaluableORB journal dates (including matched representatives), all13 handwritten dates and every journalORB/IRF-selected date; missing Saturday sessions have explicit no-data daily pages. Existing ledger exits are marked only for real simulated ledger trades. No manual price is fabricated.

Run only the new forensic scripts:

```sh
.venv/bin/python scripts/phase58_run.py
.venv/bin/python scripts/phase58_candidate_evidence.py
.venv/bin/python scripts/phase58_irf_context.py
.venv/bin/python scripts/phase58_docs.py
.venv/bin/python scripts/phase58_supplement.py
.venv/bin/python scripts/phase58_package.py
node reports/phase5/phase58_codex_orb_forensic_audit/build_workbook.mjs
.venv/bin/pytest -q
.venv/bin/ruff check src tests scripts
```

Do not rerun Phase5.5/5.7 to reproduce this audit. Phase5.8 reads existing ledgers and never calls exit/portfolio simulation. No commit/push or orders.
"""
    (OUT / "README.md").write_text(source_readme)
    print("Phase 5.8 interpretation documents written")


if __name__ == "__main__":
    build()
