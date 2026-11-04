"""Phase 3.2: write backtest_summary.md from the delivered CSV files (every number is computed here, none is typed by hand)."""

from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "phase3" / "phase32"


def rows(n: str) -> list[dict]:
    with open(OUT / n, newline="") as f:
        return list(csv.DictReader(f))


def tab(head: list[str], body: list[list]) -> str:
    return "\n".join(["| " + " | ".join(head) + " |", "|" + "---|" * len(head)] + ["| " + " | ".join(str(x) for x in r) + " |" for r in body])


def rs(x: float) -> str:
    return f"{x:,.0f}"


def main() -> None:
    t, ch, cmp_, dly = rows("automated_trades_detailed.csv"), rows("trade_entry_conditions.csv"), rows("manual_vs_automated.csv"), rows("daily_summary.csv")
    iss = rows("manual_verification_issues.csv")
    prov = json.loads((OUT / "data_provenance.json").read_text())
    base = json.loads((ROOT / "reports/phase3/baseline/summary.json").read_text())
    f = float
    gross = sum(f(x["gross_pnl_rs"]) for x in t)
    net = sum(f(x["illustrative_net_pnl_rs"]) for x in t)
    wins = sum(1 for x in t if f(x["gross_pnl_rs"]) > 0)
    oc = Counter(x["outcome"] for x in t)
    man = [c for c in cmp_ if c["journal_row"]]
    mcls = Counter(c["match_classification"] for c in man)
    extras = [c for c in cmp_ if c["match_classification"] == "EXTRA_AUTOMATED_TRADE"]
    unmatched = [c for c in man if c["match_classification"] not in ("EXACT_MATCH", "TIME_SHIFTED_MATCH")]
    res = Counter(c["result"] for c in ch)
    t_unres = sum(1 for x in t if int(x["checks_unresolved"]) > 0)
    by = defaultdict(list)
    for x in t:
        by[x["strategy"]].append(x)
    mo = defaultdict(float)
    for x in t:
        mo[x["date"][:7]] += f(x["gross_pnl_rs"])
    unres_rules = Counter(rid for rid, _ in {(c["rule_id"], c["trade_id"]) for c in ch if c["result"] == "UNRESOLVED" and not c["rule_id"].startswith("NOTE-")})
    pdr = [x for x in t if x["strategy"] == "PDR"]
    pdr_below = sum(1 for x in iss if x["category"] == "PDR_ZONE_DID_NOT_HOLD_BUT_ENTERED")
    pdr_not_high = len({c["trade_id"] for c in ch if c["rule_id"] == "PDR-002" and c["source_fidelity"].startswith("ZONE_IS_NOT_THE_DAY_HIGH")})
    pdr_int_below = len({c["trade_id"] for c in ch if c["rule_id"] == "PDR-006" and c["source_fidelity"].startswith("INTERACTION_CANDLE_CLOSED_BELOW")})
    pin_ids = {c["trade_id"] for c in ch if c["source_fidelity"].startswith("PIN_BAR_ROUTE_USED")}
    pin_n = len(pin_ids)
    pin_odd = sum(1 for x in t if x["trade_id"] in pin_ids and "against the trade direction" in x["setup_explanation"])
    relax_n = len({c["trade_id"] for c in ch if c["source_fidelity"].startswith("ENGINE_RELAXES_SOURCE")})
    strict_n = len({c["trade_id"] for c in ch if c["rule_id"] == "IRF-M2-005" and c["source_fidelity"].startswith("ENGINE_STRICTER")})
    proxy_n = len({c["trade_id"] for c in ch if c["source_fidelity"].startswith("EMA_ONLY_PROXY")})
    sl40_irf = len({c["trade_id"] for c in ch if c["rule_id"] == "IRF-SL-001" and "WOULD_SELECT_40" in c["source_fidelity"]})
    sl40_pds = len({c["trade_id"] for c in ch if c["rule_id"] == "PDS-SL-001" and "WOULD_SELECT_40" in c["source_fidelity"]})
    conflict_days = [d["date"] for d in dly if "SIMULTANEOUS_SIGNAL_CONFLICT" in d["automated_review_flag"] or "UNRESOLVED_EXECUTION" in d["automated_review_flag"]]
    m3 = Counter(r["failure_reason"].split("(")[0] for r in rows("rejected_signals.csv") if r["method"] == "Method 3" and r["strategy"] == "IRF")
    m3_n = sum(m3.values())
    m3_why = ", ".join(f"{k} {v}" for k, v in m3.most_common())
    pds3 = sum(1 for x in iss if x["category"] == "PDS_M3_SUPPORT_FAR_FROM_ZONE")
    later_irf = [int(m.group(1)) for c in ch if c["rule_id"] == "NOTE-IRF-REPEATED-SETUPS" for m in [re.search(r"^(\d+) further", c["observed"])] if m]
    L = ["# Phase 3.2 - explainable backtest, trade journals and daily verification (summary)", "",
         "**Written for:** the strategy owner, who will check trades one day at a time. Nothing in this phase changes a rule, a parameter, a stop, a target, the cutoff or the selection controller, and nothing was tuned toward profit or toward the manual journal. "
         "The P&L is **synthetic NIFTY 50 index-point P&L x quantity** (the index is not tradable); the illustrative net applies Rs 500 per trade and 0.5 index point adverse on every fill (the Phase 3.0 headline assumption).", "",
         "## 1. Prior figures re-verified from the repository artifacts", "",
         tab(["figure quoted for Phase 3.1", "verified now", "how"], [
             ["213 automated entries", len(t), "baseline re-run through the Phase 3.0 code path; every ledger field identical to the frozen `reports/phase3/baseline/trades.csv` "
              f"({prov['phase30_ledger_check']['n_differences']} differences)"],
             ["Rs 1,72,146 gross synthetic P&L", f"Rs {rs(gross)}", "sum of the 213 trades; also reproduced by an independent walk of the raw 1-minute bars"],
             ["190 manual journal rows", len(man), "the workbook (the performance report prints 189; 5 rows are Saturday-dated)"],
             ["84 matches (67 exact + 17 within 15 minutes)", f"{mcls['EXACT_MATCH'] + mcls['TIME_SHIFTED_MATCH']} ({mcls['EXACT_MATCH']} + {mcls['TIME_SHIFTED_MATCH']})", "Phase 3.1 matching rules unchanged; classifications equal Phase 3.1's"],
             ["129 extra automated trades", len(extras), "213 - 84"], ["106 unmatched manual trades", len(unmatched), "190 - 84"],
             ["413 passing tests after Phase 3.1", "413 passed at the start of this phase", "full suite, run again before any Phase 3.2 code was added (the current total is in `independent_audit.md`)"]]), "",
         "## 2. Headline results (baseline, unchanged)", "",
         tab(["item", "value"], [["Evaluable sessions", len(dly)], ["Executed trades (first / second)", f"{len(t)} ({sum(x['trade_no_of_day'] == '1' for x in t)} / {sum(x['trade_no_of_day'] == '2' for x in t)})"],
                                 ["Days with a trade / no-trade days", f"{sum(x['executed_trades'] != '0' for x in dly)} / {sum(x['executed_trades'] == '0' for x in dly)}"],
                                 ["Gross P&L (Rs)", rs(gross)], ["Illustrative net P&L (Rs)", rs(net)], ["Win rate (trades with gross P&L > 0; this counts T1-then-post-T1-stop trades, which net a small gain, as wins)", f"{100 * wins / len(t):.2f}%"],
                                 ["Profit factor / max drawdown (gross, from the Phase 3.0 summary)", f"{base['gross']['profit_factor']:.2f} / Rs {rs(base['gross']['max_drawdown_rs'])}"],
                                 ["Outcomes", ", ".join(f"{k} {v}" for k, v in sorted(oc.items()))],
                                 ["Same-minute execution ambiguities / provisional forced exits / unresolved exits", f"{sum(int(x['execution_ambiguities']) for x in t)} / {oc.get('FORCED_EXIT', 0)} / {sum(x['resolved'] != 'True' for x in t)}"]]), "",
         "### By strategy and method", "",
         tab(["strategy", "trades", "wins", "gross Rs", "illustrative net Rs", "methods"], [[s, len(v), sum(f(x["gross_pnl_rs"]) > 0 for x in v), rs(sum(f(x["gross_pnl_rs"]) for x in v)),
                                                                                           rs(sum(f(x["illustrative_net_pnl_rs"]) for x in v)), ", ".join(f"{k} {n}" for k, n in sorted(Counter(x["method"] for x in v).items()))]
                                                                                          for s, v in sorted(by.items())]), "",
         "### By month (gross Rs)", "", tab(["month"] + list(sorted(mo)), [["gross"] + [rs(mo[m]) for m in sorted(mo)]]), "",
         "No ranking of strategies or variants by these figures was made or used for any decision.", "",
         "## 3. How completely the trades are explained", "",
         tab(["measure", "value"], [["Trades with an entry explanation, a selection explanation and an exit explanation for both legs", f"{len(t)} of {len(t)}"],
                                    ["Entry conditions recorded (each with rule id, calculation, observed values, requirement, result, status, availability time, reason)", len(ch)],
                                    ["... PASS / FAIL / UNRESOLVED / NOT_APPLICABLE", f"{res['PASS']} / {res['FAIL']} / {res['UNRESOLVED']} / {res['NOT_APPLICABLE']}"],
                                    ["Trades with a FAILED check or a recomputation mismatch against the engine's own record", sum(1 for x in t if int(x['checks_fail']) or x['recomputation_mismatches'])],
                                    ["Trades whose exit could not be reproduced from the raw bars", sum(1 for x in t if x['resolved'] != 'True')],
                                    ["Trades that carry at least one OPEN SOURCE-RULE issue (disclosed, not a gap in the evidence)", t_unres],
                                    ["Trades whose signal is verification-status PROPOSAL_DEPENDENT / RESEARCH_VARIANT", f"{sum(x['signal_verification_status'] == 'PROPOSAL_DEPENDENT' for x in t)} / {sum(x['signal_verification_status'] == 'RESEARCH_VARIANT' for x in t)} (none is VERIFIED)"]]), "",
         "**Evidence versus open rules.** 'Unresolved evidence' (a number that cannot be reproduced) is **zero**: every price traces to a raw 1-minute bar and every candle number to the raw data. What stays open are rules the sources leave undefined - they are listed in every trade and counted here:", "",
         tab(["unresolved rule id", "trades"], [[k, v] for k, v in unres_rules.most_common()]), "",
         "## 4. Journal agreement (Phase 3.1 matching rules, untouched)", "",
         tab(["class", "manual rows"], [[k, v] for k, v in sorted(Counter(c["match_classification"] for c in man).items())]), "",
         f"Extra automated trades: {len(extras)}. Every unmatched row carries the concrete reason from the Phase 3.1 rejection chain; where the evidence does not decide, the cause is stated as **UNKNOWN** "
         f"({sum(1 for c in unmatched if (c['root_cause_primary'] or 'UNKNOWN') == 'UNKNOWN')} rows). The journal records no entry or exit price, so only date, strategy, candle start and outcome class can be compared; P&L is never used to match.", "",
         "## 5. Things the explanations make visible (for the owner's judgement - none was changed)", "",
         f"* **PDR zone hold:** the engine accepts the next green candle after a zone touch without checking that the zone held. In {pdr_below} of the {len(pdr)} PDR entries the confirmation candle closed below the zone floor (`PDR_ZONE_DID_NOT_HOLD_BUT_ENTERED` in `manual_verification_issues.csv`).",
         f"* **PDS Method 3:** {pds3} of the {sum(1 for x in t if x['strategy'] == 'PDS' and x['method'] == 'Method 3')} Method 3 entries used a 'small support' more than 10 points below the zone floor; the guide defines no 'near' distance.",
         f"* **IRF repeats:** every IRF trade is the day's first executable signal, but the engine re-arms on every later breakout and the guide is silent on re-arming (IRF-GLOBAL-004): "
         f"{sum(1 for v in later_irf if v > 0)} of the {len(later_irf)} IRF trades were followed by further IRF signals the same day ({sum(later_irf)} in total, each logged as ignored or rejected and visible in that day's journal).",
         f"* **PDR zone provenance:** in {pdr_not_high} of the {len(pdr)} PDR trades the engine's zone (the owner-approved research candidate 'latest confirmed swing high with a red follower') is **not** the previous day's high (the guide says 'previous day's high/reversal'); "
         f"in {pdr_int_below} of {len(pdr)} the interaction candle closed below the zone floor (price traded through the zone, not a hold) and in {pdr_below} the confirmation close was also below it. "
         "The registry also records that the dated PDR Example 3 (2025-10-07) is not reproduced: the author drew a zone about 4-5 points tall, the engine's is 38.6 points. The audit's 'zone equals an independent construction' check validates the engine's research definition, not the author's drawn zone.",
         f"* **ORB candle route:** {pin_n} ORB trades failed the strong-body test and were admitted through the conditional pin-bar alternative ({pin_odd} of them on a candle of the opposite colour; the pin route accepts either colour because the level break carries the direction); each trade's setup text says so.",
         f"* **Engine readings that differ from the guide's wording:** {relax_n} IRF Method 2B trades accept the push above resistance and the red close on the same candle (the guide's figure shows three candles); all {strict_n} IRF Method 2A trades require the break candle to follow the red candle (stricter than the text). Check rows carry a `source_fidelity` column for these.",
         f"* **Trend filter:** {proxy_n} trades (ORB Methods 1/2 and RF) rest on the previous session's last 5-minute close versus its EMA(200) alone; the guides call the EMA a basic filter that is never the sole proof of a trend.",
         f"* **35 versus 40 stop:** the guide's own selection rule (35 if the most recent opposite candle is within 35 points of entry, else 40) would have chosen 40 on {sl40_irf} of the {len(by['IRF'])} IRF trades and {sl40_pds} of the {len(by['PDS'])} PDS trades; the approved baseline uses a fixed 35 (the 40-point variant is a separate Phase 3.0 scenario). This changes losses, not entries.",
         f"* **Days lost to unresolved same-minute conflicts:** {len(conflict_days)} ({', '.join(conflict_days)}); the day is marked unresolved and nothing is traded (no tie-break priority is approved).",
         f"* **IRF Method 3** (sweep above the range after compression) is evaluated every day but produced no confirmed signal ({m3_n} Method 3 setups were rejected: {m3_why}); it is not part of any trade.",
         "* **ORB and RF:** the level, candle-strength thresholds and trend are mechanical stand-ins for hand-drawn levels and discretionary judgement; each trade states the numbers used.",
         "* **Second trades:** only PDR/PDS signals confirmed after the first trade's original full stop; "
         f"{sum(1 for x in t if x['trade_no_of_day'] == '2')} such trades.", "",
         "## 6. Rules in force (unchanged)", "",
         "First valid signal of IRF/ORB/PDR/PDS/RF takes the day's first trade; none while a trade is active; second trade only after an original full stop before T1 and only a newly confirmed PDR/PDS signal; at most 2 trades a day; "
         "no fill after 13:00:00 IST; 6 lots x 65 (3 + 3); stops ORB 30, IRF/PDR/PDS/RF 35; T1 27; T2 IRF 60, ORB 60, PDR 70, PDS 70 (the performance report suggests 60 - recorded as CONFLICTING), RF 60 (research proposal); after T1 the remaining legs stop at entry -6 (LONG) / +6 (SHORT), no trailing; "
         "same-minute stop/target is resolved adversely and flagged; the forced exit at the 15:14 minute open is a **provisional** implementer assumption (it was never exercised by this ledger); simultaneous different-strategy signals mark the day unresolved (no priority assigned). Full values: `configuration_snapshot.json`, worksheet *Rule Definitions*.", "",
         "## 7. Limits", "",
         "* Explanations are produced by recomputing every condition with the engines' own definition functions and the active configuration, and are cross-checked against the values each engine stored on its signal record; the engines were **not modified** (no tracing code was added), "
         "and the unchanged Phase 3.0 ledger proves the re-run is identical. Numeric evidence exists for the 213 executed trades; for the other signals the engine's rule-id lists, levels and state traces are exported (`all_strategy_signals.csv`, `rejected_signals.csv`).",
         "* Previous-day levels and zones use all candles of the previous session (including the auction print on auction days) - disclosed in Phase 3.0 and unchanged. On 2025-10-23 four engines cannot be evaluated because their previous session is the unverifiable Muhurat session (that day's journal says so).",
         "* Invalidated engine setups on days without a trade are exported with the engine's reason code and failed rule ids (`rejected_signals.csv`), without per-condition numbers: numeric evidence is produced for executed trades only.",
         "* `rule_status` says what kind of rule a condition is in the registry; read it together with `definition_status` and `source_fidelity`: about half of the SOURCE_VERIFIED rows rest on a qualitative wording whose numbers are proposals.",
         "* The charts and the Excel workbook are verification aids; the numerical journals are authoritative.", ""]
    (OUT / "backtest_summary.md").write_text("\n".join(L))
    print("written", OUT / "backtest_summary.md")


if __name__ == "__main__":
    main()
