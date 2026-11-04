"""Phase 2.1 INTEGRATION tests against the real dataset and the strategy guides' dated worked examples.

These are historical cases, not synthetic fixtures. They record what the guides' own examples show; none was used to tune a threshold.
"""

import json
from datetime import date
from pathlib import Path

import pytest

from nifty_trading.strategies import PDRStrategy, ProposalConfig

ROOT = Path(__file__).resolve().parents[1]
needs_data = pytest.mark.skipif(not (ROOT / "data" / "processed" / "nifty50_daily").exists(), reason="Phase 2.1 data artefacts not present")


@pytest.fixture(scope="module")
def real():
    from nifty_trading.data.sessions import (
        build_session_contexts,
        load_daily_official,
        load_one_minute,
        load_warmup_one_minute,
    )
    return build_session_contexts(load_one_minute(), daily_df=load_daily_official(), warmup_1m=load_warmup_one_minute())


@needs_data
@pytest.mark.rules("RF-001", "ORB-MA-001")
def test_the_200_line_on_the_guides_5_minute_charts_is_an_ema_of_5_minute_closes_to_within_0_01_point(real):
    """PDR p.3 Example 1 legend 'EMA 200 close 24,582.02' (2025-09-01 12:50 bar) and p.4 Example 3 legend 24,925.18 (2025-10-07 09:40 bar)."""
    ctxs, _ = real
    c1 = ctxs[date(2025, 9, 1)].candles
    r1 = c1[c1.bar_start.dt.strftime("%H:%M") == "12:50"].iloc[0]
    assert (r1.high, r1.low) == (24571.35, 24557.25)  # the legend's printed H and L
    assert r1.ema200_5m == pytest.approx(24582.02, abs=0.01)
    c3 = ctxs[date(2025, 10, 7)].candles
    r3 = c3[c3.bar_start.dt.strftime("%H:%M") == "09:40"].iloc[0]
    assert r3.ema200_5m == pytest.approx(24925.18, abs=0.01)
    # a 200-DAY average is nowhere near these legend values: the daily reading is excluded by the charts themselves
    assert abs(ctxs[date(2025, 9, 1)].daily_sma200_prev - 24582.02) > 400


@needs_data
@pytest.mark.rules("PDR-004", "PDR-006", "PDR-007", "PDR-011")
def test_pdr_dated_worked_examples_1_and_2_reproduce_under_the_text_default(real):
    """PDR guide pp.3-4 Examples 1-2 (2025-09-02, 2025-10-06). Expected candle labels (09:25, 09:30) come from the journal: a CONSISTENCY check, not independent evidence."""
    ctxs, _ = real
    eng = PDRStrategy()  # default pdr_open_vs_zone = ABOVE_ZONE (the text)
    for d, hhmm in {date(2025, 9, 2): "09:25", date(2025, 10, 6): "09:30"}.items():
        rec = [r for r in eng.evaluate_session(ctxs[d]) if r.signal_status == "CONFIRMED"]
        assert rec and rec[0].signal_candle_start.strftime("%H:%M") == hhmm, d


@needs_data
@pytest.mark.rules("PDR-002", "PDR-011")
def test_pdr_example_3_does_not_discriminate_because_the_engine_zone_is_not_the_authors_drawn_zone(real):
    """2025-10-07: the engine's zone comes from the 14:50 spike candle: [25,077.25, 25,095.70] (18.5 points) with the Phase 2.2 wick-only default, 38.6 points with the full-body candidate. The zone the author DREW on the
    chart is only ~4-5 points tall (about 25,080.5-25,084.5; the open 25,087.55 lies above it). So 'the open is inside the zone' is an artefact of the engine's zone, not evidence against the text."""
    ctxs, _ = real
    c = ctxs[date(2025, 10, 7)]
    text = PDRStrategy().evaluate_session(c)[0]
    assert text.signal_status == "INVALIDATED" and text.invalidation_reason == "GAP_UP_OPEN_NOT_ABOVE_ZONE"
    lv = text.reference_levels
    assert lv["zone_low"] == pytest.approx(25077.25) and lv["zone_high"] == pytest.approx(25095.70)  # Phase 2.2 default ZONE_WICK: [body top, wick tip]
    assert lv["zone_high"] - lv["zone_low"] > 15  # still far taller than the drawn zone (~4-5 points)
    full = PDRStrategy(proposals=ProposalConfig(zone_lower_boundary="ZONE_FULL")).evaluate_session(c)[0].reference_levels
    assert full["zone_low"] == pytest.approx(25057.10) and full["zone_high"] - full["zone_low"] > 30  # the Phase 2.1 candidate: 38.6 points
    for mode in ("NOT_BELOW_ZONE", "ANY"):  # the example is reproduced only under the weaker readings, with the engine's (different) zone
        rec = [r for r in PDRStrategy(proposals=ProposalConfig(pdr_open_vs_zone=mode)).evaluate_session(c) if r.signal_status == "CONFIRMED"]
        assert rec and rec[0].signal_candle_start.strftime("%H:%M") == "09:20"
    entry = float(c.candles.close.iloc[1])  # the example's outcome: +69.90 reached, the 40.60 stop never touched
    assert c.candles.high.iloc[2:40].max() >= entry + 69.90 and c.candles.low.iloc[2:40].min() > entry - 40.60


@needs_data
@pytest.mark.rules("PDR-011")
def test_pdr_any_mode_emits_signals_with_the_open_below_the_zone_which_is_why_it_is_not_the_default(real):
    ctxs, _ = real
    below = total = 0
    for c in ctxs.values():
        for r in PDRStrategy(proposals=ProposalConfig(pdr_open_vs_zone="ANY", pdr_zone_method="A_HIGHEST_HIGH")).evaluate_session(c):  # the diagnostic zone of the original measurement
            if r.signal_status == "CONFIRMED":
                total += 1
                below += c.open_price < r.reference_levels["zone_low"]
    # the reviewer measured 66 of 119 with the 5-point proximity; with strict zone intersection the share is still large
    assert total > 0 and below / total > 0.4  # a 'support' zone that is above the open is resistance


@needs_data
@pytest.mark.rules("DATA-QUAL-001")
def test_the_committed_session_quality_manifest_matches_a_fresh_recomputation():
    import importlib.util
    spec = importlib.util.spec_from_file_location("phase21_build_manifests", ROOT / "scripts" / "phase21_build_manifests.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    fresh = mod.build()
    committed = json.loads((ROOT / "data" / "metadata" / "session_quality_manifest.json").read_text())
    key = lambda m: [(s["date"], s["status"], s["evaluable_by_strategies"], s["reasons"], s["official_close"]) for s in m["sessions"]]  # noqa: E731
    assert key(fresh) == key(committed)
    assert fresh["counts"] == committed["counts"] and committed["counts"]["by_status"] == {"VALID": 246, "VALID_SPECIAL_SESSION": 2}
    assert [n["date"] for n in fresh["non_trading_days"]] == [n["date"] for n in committed["non_trading_days"]]


@needs_data
@pytest.mark.rules("DATA-QUAL-001")
def test_runner_covers_every_session_exactly_once_for_non_evaluable_days_and_evaluates_the_rest(real):
    from nifty_trading.strategies import IRFStrategy
    from nifty_trading.strategies.runner import evaluate_dataset
    ctxs, infos = real
    eng = IRFStrategy()
    recs = evaluate_dataset(eng, ctxs, infos)
    not_evaluable = {d for d in infos if d not in ctxs}
    assert not_evaluable == {date(2025, 10, 21)}
    ne = [r for r in recs if r.method == "ALL" and r.signal_status == "NOT_EVALUATED"]
    assert [r.signal_date for r in ne] == [date(2025, 10, 21)]  # exactly one record for the one non-evaluable day
    assert "VALID_SPECIAL_SESSION" in ne[0].invalidation_reason
    direct = [r for d in sorted(ctxs) for r in eng.evaluate_session(ctxs[d])]
    assert len(recs) == len(direct) + 1 and sum(r.signal_status == "CONFIRMED" for r in recs) == sum(r.signal_status == "CONFIRMED" for r in direct) > 300
    assert {r.signal_date for r in recs} <= set(infos) and max(r.signal_date for r in recs) >= date(2026, 8, 28)  # the last sessions are not dropped
