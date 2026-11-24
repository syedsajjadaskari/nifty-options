"""Phase 6.5 continuation tests: PDR variant behaviours (B1 / B2 / C / D) and the PDS second-confirmation variant on synthetic sessions, the unchanged baselines, the Phase 7.0 read-only discipline of the Phase 6.5 scripts,
and invariants of the delivered result files (skipped when the files are absent)."""

from __future__ import annotations

import dataclasses
import json
import re
from pathlib import Path

import pandas as pd
import pytest
from synthetic import ctx

from nifty_trading.research import phase3 as P
from nifty_trading.strategies.first_eligible_phase53 import (
    PDRFirstEligibleStrategy,
    PDSFirstEligibleStrategy,
)
from nifty_trading.strategies.pdr_variants import APPROVAL, PDRVariantStrategy
from nifty_trading.strategies.pds_variants import PDSSecondConfirmationStrategy

ROOT = Path(__file__).resolve().parents[1]
R65 = ROOT / "reports" / "phase6" / "phase65_author_feedback"
SC = P.combined_scenario("BODY_BASED_PHASE36")
PREV_PDR = {"cands": [(100, 105, 99, 104), (104, 110, 103, 108), (108, 109, 100, 101)], "close": 101.0}      # zone [104, 108]
PREV_PDS = {"cands": [(100, 102, 96, 101), (101, 101.5, 95, 100), (100, 100.5, 96, 99.5)], "close": 99.0}      # zone [95, 101]


def confirmed(recs, strategy):
    return sorted((r for r in recs if r.signal_status == "CONFIRMED" and r.strategy == strategy), key=lambda r: r.signal_timestamp)


def hm(r) -> str:
    return f"{r.signal_timestamp:%H:%M}"


def pdr(today, mode=None, open_price=112.0):
    c = ctx(today, prev=PREV_PDR, open_price=open_price)
    if mode is None:
        eng = PDRFirstEligibleStrategy(proposals=SC.proposals, trade=SC.trade, revision=SC.pdr_revision)
    else:
        eng = PDRVariantStrategy(mode, proposals=SC.proposals, trade=SC.trade, revision=SC.pdr_revision)
    return [hm(r) for r in confirmed(eng.evaluate_session(c), "PDR")]


def drop_candle(c, i):
    return dataclasses.replace(c, candles=c.candles.drop(index=i).reset_index(drop=True))


def pds(today, cls):
    c = ctx(today, prev=PREV_PDS, open_price=90.0)
    return confirmed(cls(proposals=SC.proposals, trade=SC.trade).evaluate_session(c), "PDS")


# ---------------------------------------------------------------------------------------------------------------- PDR variants
GREEN_INSIDE_ZONE_FIRST = [(112, 113, 110, 111),            # 09:15 above the zone, no retest
                           (111, 111.5, 107, 108.5),        # 09:20 retest candle (red)
                           (107.0, 107.9, 106.8, 107.8),    # 09:25 GREEN, closes inside the zone (<= ceiling 108): baseline / C reject, B1 / B2 accept
                           (107.8, 109.5, 107.7, 109.0)]    # 09:30 green above the ceiling: the baseline's first eligible candle


def test_b1_and_b2_accept_a_green_close_inside_the_zone_the_baseline_and_c_do_not():
    assert pdr(GREEN_INSIDE_ZONE_FIRST) == ["09:35"]                      # baseline: the approved close-above-ceiling rule delays the entry
    assert pdr(GREEN_INSIDE_ZONE_FIRST, "B1") == ["09:30"]
    assert pdr(GREEN_INSIDE_ZONE_FIRST, "B2")[0] == "09:30"                # B2 also opens a new cycle on the next retesting green candle (the controller takes the first signal)
    assert pdr(GREEN_INSIDE_ZONE_FIRST, "C") == ["09:35"]                 # C keeps the ceiling requirement


RETEST_IS_GREEN_ABOVE = [(112, 113, 110, 111),
                         (107.5, 109.5, 107.2, 109.0),      # 09:20 the retest candle is itself green and closes above the ceiling
                         (109.0, 110.0, 108.6, 109.8),      # 09:25 the next eligible candle
                         (109.8, 111.0, 109.5, 110.5)]      # 09:30 a later independently eligible candle


def test_retest_candle_may_confirm_only_in_b2_and_c_and_d_waits_for_a_later_second_candle():
    assert pdr(RETEST_IS_GREEN_ABOVE) == ["09:30"]                        # baseline: the retest candle may not confirm
    assert pdr(RETEST_IS_GREEN_ABOVE, "B1") == ["09:30"]
    assert pdr(RETEST_IS_GREEN_ABOVE, "B2") == ["09:25"]
    assert pdr(RETEST_IS_GREEN_ABOVE, "C") == ["09:25"]
    assert pdr(RETEST_IS_GREEN_ABOVE, "D") == ["09:35"]                   # first eligible 09:25 registered; the later independent candle (ends 09:35) triggers


def test_d_needs_two_independently_eligible_candles_and_never_uses_a_single_one():
    one_only = RETEST_IS_GREEN_ABOVE[:3]
    assert pdr(one_only) == ["09:30"] and pdr(one_only, "D") == []


def test_every_variant_keeps_the_gap_and_open_conditions():
    for mode in (None, "B1", "B2", "C", "D"):
        assert pdr(RETEST_IS_GREEN_ABOVE, mode, open_price=108.0) == []   # open == ceiling is not strictly above the zone


def test_variants_are_labelled_and_the_baseline_class_is_untouched():
    assert APPROVAL["B1"].startswith("AUTHOR_CONFIRMATION_REQUIRED") and APPROVAL["B2"].startswith("AUTHOR_CONFIRMATION_REQUIRED") and APPROVAL["C"].startswith("AUTHOR_CONFIRMATION_REQUIRED")
    assert APPROVAL["D"].startswith("MECHANICAL_RESEARCH_CONVENTION")
    with pytest.raises(ValueError):
        PDRVariantStrategy("Z", proposals=SC.proposals, trade=SC.trade, revision=SC.pdr_revision)
    c = ctx(RETEST_IS_GREEN_ABOVE, prev=PREV_PDR, open_price=112.0)
    recs = confirmed(PDRVariantStrategy("C", proposals=SC.proposals, trade=SC.trade, revision=SC.pdr_revision).evaluate_session(c), "PDR")
    assert recs[0].reference_levels["pdr_variant"] == "C" and recs[0].reference_levels["green_candle_is_retest_candle"] is True


def test_variant_signals_use_closed_candles_only():
    c = ctx(RETEST_IS_GREEN_ABOVE, prev=PREV_PDR, open_price=112.0)
    for mode in ("B1", "B2", "C", "D"):
        eng = PDRVariantStrategy(mode, proposals=SC.proposals, trade=SC.trade, revision=SC.pdr_revision)
        full = [hm(r) for r in confirmed(eng.evaluate_session(c), "PDR")]
        eng2 = PDRVariantStrategy(mode, proposals=SC.proposals, trade=SC.trade, revision=SC.pdr_revision)
        for cut in range(1, len(RETEST_IS_GREEN_ABOVE) + 1):
            pre = [hm(r) for r in confirmed(eng2.evaluate_session(c.prefix(cut)), "PDR")]
            assert pre == [t for t in full if t <= f"09:{15 + 5 * cut:02d}"]            # a prefix reproduces exactly the signals that were already decided


# ---------------------------------------------------------------------------------------------------------------- PDS second confirmation
TWO_GOOD_RED = [(90, 92, 89, 91), (91, 96, 90.5, 95.5),
                (95.5, 97.0, 91.9, 93.0),       # 09:25 first good red candle at the zone (Method 1)
                (96.0, 97.5, 92.4, 93.5)]       # 09:30 a later, independently good red candle at the zone


def test_pds_second_confirmation_waits_for_a_later_independent_candle():
    first = pds(TWO_GOOD_RED, PDSFirstEligibleStrategy)
    second = pds(TWO_GOOD_RED, PDSSecondConfirmationStrategy)
    assert hm(first[0]) == "09:30" and first[0].method == "Method 1"
    assert [hm(r) for r in second] == ["09:35"] and second[0].method == "Method 1"
    assert not pds(TWO_GOOD_RED[:3], PDSSecondConfirmationStrategy)                 # a single eligible candle never triggers the second-confirmation variant


WEAK_THEN_BREAK = [(90, 92, 89, 91), (91, 96, 90.5, 95.5), (97, 98, 95.2, 96.5), (96.5, 96.8, 94.5, 95.0), (95.0, 96.0, 94.8, 95.8), (95.8, 96.0, 93.0, 93.5), (93.5, 94.0, 92.0, 92.5)]


def test_method_3_support_break_is_unchanged_and_still_mandatory():
    a, b = pds(WEAK_THEN_BREAK, PDSFirstEligibleStrategy), pds(WEAK_THEN_BREAK, PDSSecondConfirmationStrategy)
    assert [(r.method, hm(r)) for r in a] == [(r.method, hm(r)) for r in b] == [("Method 3", "09:45")]
    assert not pds(WEAK_THEN_BREAK[:5], PDSSecondConfirmationStrategy)              # without the break there is no entry


def test_a_missing_candle_resets_the_pdr_second_confirmation_cycle():
    day = RETEST_IS_GREEN_ABOVE + [(110.5, 112.0, 110.2, 111.5)]                      # 09:15 .. 09:30: retest 09:20, first eligible 09:25, independent second 09:30, filler 09:35
    c = ctx(day, prev=PREV_PDR, open_price=112.0)
    eng = PDRVariantStrategy("D", proposals=SC.proposals, trade=SC.trade, revision=SC.pdr_revision)
    assert [hm(r) for r in confirmed(eng.evaluate_session(c), "PDR")] == ["09:35"]
    eng2 = PDRVariantStrategy("D", proposals=SC.proposals, trade=SC.trade, revision=SC.pdr_revision)
    assert [hm(r) for r in confirmed(eng2.evaluate_session(drop_candle(c, 3)), "PDR")] == []   # the 09:30 candle is missing: the registered first candle is not carried across the hole


GOOD_RED_THEN_CLOSE_ABOVE_ZONE = TWO_GOOD_RED[:3] + [(93.0, 103.0, 92.5, 102.0)] + [(96.0, 97.5, 92.4, 93.5)]      # 09:30 closes above the zone high (101): the cycle is abandoned


def test_pds_second_confirmation_is_abandoned_when_price_closes_above_the_zone():
    assert [hm(r) for r in pds(GOOD_RED_THEN_CLOSE_ABOVE_ZONE, PDSFirstEligibleStrategy)][:1] == ["09:30"]     # the baseline takes the first eligible candle
    assert not pds(GOOD_RED_THEN_CLOSE_ABOVE_ZONE, PDSSecondConfirmationStrategy)                            # the variant lost the zone before a second candle: the later good red only starts a NEW cycle


def test_second_confirmation_may_be_a_different_method_from_the_first():
    pin = (95.0, 99.0, 93.9, 94.0)                                                     # red pin bar: upper wick 4.0 > body 1.0 and > lower wick 0.1, high reached the zone (Method 2)
    got = pds(TWO_GOOD_RED[:3] + [pin], PDSSecondConfirmationStrategy)
    assert [(r.method, hm(r)) for r in got] == [("Method 2", "09:35")]


def test_documented_convention_a_weak_red_between_the_two_candles_ends_the_methods_1_2_path():
    weak = (97.0, 98.0, 95.2, 96.5)                                                    # red, body 0.5 smaller than both wicks: neither Method 1 nor 2
    day = TWO_GOOD_RED[:3] + [weak, (96.0, 97.5, 92.4, 93.5)]
    assert not [r for r in pds(day, PDSSecondConfirmationStrategy) if r.method in ("Method 1", "Method 2")]    # open decision #9: skipping the weak candle would give a signal here
    assert not [r for r in pds(day[:3] + day[4:], PDSSecondConfirmationStrategy) if r.method not in ("Method 1", "Method 2")] and pds(day[:3] + day[4:], PDSSecondConfirmationStrategy)


# ---------------------------------------------------------------------------------------------------------------- Phase 7.0 read-only discipline
def test_phase65_scripts_never_write_to_phase70_paths():
    pat = re.compile(r"(irf_v3|reports/phase7|phase70_|test_phase70|phase71|test_phase71)")
    writes = re.compile(r"(write_text|write_bytes|write_csv|to_csv|\.unlink|shutil|rmtree|os\.remove|open\([^)]*['\"][wa]b?['\"])")
    for f in sorted((ROOT / "scripts").glob("phase65b_*.py")) + sorted((ROOT / "src" / "nifty_trading" / "strategies").glob("p*_variants.py")):
        for n, line in enumerate(f.read_text().splitlines(), 1):
            stripped = line.split("#")[0]
            assert not (pat.search(stripped) and writes.search(stripped)), f"{f.name}:{n} writes near a Phase 7.0 path"


# ---------------------------------------------------------------------------------------------------------------- result-file invariants
def need(name):
    p = R65 / name
    if not p.exists():
        pytest.skip(f"{name} not generated")
    return p


def test_win_rate_definition_and_counts_are_consistent():
    full = pd.read_csv(need("full_backtest_comparison.csv"))
    wr = pd.read_csv(need("strategy_win_rates.csv"))
    assert (full.winners_gross + full.losers_gross + full.breakeven_gross == full.trades).all()
    assert ((full.gross_win_rate_pct - (100 * full.winners_gross / full.trades)).abs() < 0.06).all()                # winner = positive total completed-trade P&L
    g = wr.groupby(["window", "config"])[["executed_trades", "winners"]].sum().reset_index().merge(full[["window", "config", "trades", "winners_gross"]])
    assert (g.executed_trades == g.trades).all() and (g.winners == g.winners_gross).all()                      # strategy rows add up to the portfolio row


def test_ten_configurations_and_both_windows_are_present():
    full = pd.read_csv(need("full_backtest_comparison.csv"))
    assert set(full.config) == {"BASE", "S60", "S70", "SD", "PDR_B1", "PDR_B2", "PDR_C", "PDR_D", "PDS_FROZEN", "PDS_SECOND"} and set(full.window) == {"A", "B"}


def test_strength_configurations_reproduce_the_saved_checkpoint_ledgers():
    v = json.loads(need("continuation_state.json").read_text())["validation"]
    assert v and all(x["identical"] for x in v.values())


def test_trade_set_attribution_reconciles_with_the_ledgers():
    t = pd.read_csv(need("configuration_trade_comparison.csv"))
    t = t[t.config != "BASE"]
    assert ((t.removed_direct_effect + t.removed_portfolio_effect) == t.baseline_trades_removed).all()
    assert ((t.added_direct_effect + t.added_portfolio_effect) == t.new_trades_added).all()
    full = pd.read_csv(need("full_backtest_comparison.csv")).set_index(["window", "config"])
    for r in t.itertuples():
        assert full.loc[(r.window, "BASE"), "trades"] - r.baseline_trades_removed + r.new_trades_added == full.loc[(r.window, r.config), "trades"]


def test_journal_summary_never_counts_date_only_agreement_as_a_match():
    j = pd.read_csv(need("strict_match_comparison.csv"))
    assert (j.journal_rows == 190).all()
    assert (j.strict + j.time_tolerant + j.date_strategy_only + j.manual_only == j.journal_rows).all()            # date-only rows sit in their own class, never inside the matched ones
    assert (j.strict_tolerant_total == j.strict + j.time_tolerant).all()
    pairs = pd.read_csv(need("manual_journal_reconciliation.csv"), dtype=str, keep_default_na=False)
    if "verified_exact_trade_match" in pairs:
        assert (pairs.verified_exact_trade_match.str.lower() != "true").all()                                    # no exact trade match is claimed anywhere
        assert not pairs[pairs.stage == "DATE_STRATEGY_ONLY"].verified_exact_trade_match.str.lower().eq("true").any()


def test_net_columns_are_net_of_rs_70_per_trade_and_gross_columns_are_gross():
    full = pd.read_csv(need("full_backtest_comparison.csv"))
    assert ((full.gross_rs - full.net_rs - 70 * full.trades).abs() < 1).all()
    wr = pd.read_csv(need("strategy_win_rates.csv"))
    assert ((wr.gross_rs - wr.net_rs_70_per_trade - 70 * wr.executed_trades).abs() < 1).all()
    cost = pd.read_csv(need("cost_slippage_sensitivity.csv"))
    c70 = cost[cost.scenario == "C70_TRADE"].set_index(["window", "config"]).net_rs
    assert ((full.set_index(["window", "config"]).net_rs - c70).abs() < 1).all()


def test_delay_category_is_blank_for_cycles_that_were_not_delayed_and_second_signals_exclude_method_3():
    cyc = pd.read_csv(need("pdr_first_eligible_audit.csv"), dtype=str, keep_default_na=False)
    assert (cyc[cyc.delayed_earlier_green == "False"].delay_category == "").all()
    assert set(cyc[cyc.delayed_earlier_green == "True"].delay_category.str[0]) <= set("ABCDEFG")
    pds = pd.read_csv(need("pds_confirmation_variants.csv"), dtype=str, keep_default_na=False)
    m3 = pds[pds.pds_method == "Method 3"]
    assert (m3.date == "ALL").all()                                                                              # Method 3 appears only as a displacement summary, never as a second confirmation


def test_delivered_file_set_is_complete_when_the_final_report_exists():
    if not (R65 / "PHASE65_FINAL_REPORT.md").exists():
        pytest.skip("final report not generated")
    for f in ("pdr_rule_authority_matrix.md", "pdr_215_delayed_cycles.csv", "pdr_variant_B_signals.csv", "pdr_variant_C_signals.csv", "pdr_variant_D_signals.csv", "pds_confirmation_variants.csv", "complete_configuration_manifest.json", "strategy_win_rates.csv",
              "trade_set_attribution.csv", "mismatch_root_causes.md", "final_independent_audit.md", "final_preservation_verification.md", "Phase65_Author_Feedback_Complete.xlsx", "phase7_irf_overlap_inventory.md", "remaining_author_decisions.md"):
        assert (R65 / f).exists(), f
