"""Look-ahead bias, registry/traceability integrity and the BaseStrategy adapter (Tasks 10-12)."""

import math
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml
from synthetic import DAY, IST, ctx, minute_rows

import nifty_trading.strategies  # noqa: F401  (registers every @implements)
from nifty_trading.core.strategy import SignalType, StrategyContext
from nifty_trading.strategies import ALL_STRATEGIES, IRFStrategy
from nifty_trading.strategies.rule_data import IMPL_P, IMPL_R, NOT, RULES
from nifty_trading.strategies.rules import IMPLEMENTATIONS

ROOT = Path(__file__).resolve().parents[1]
DOC_PAGES = {"IRF_Strategy_Guide Updated.pdf": 17, "ORB_Strategy_Rulebook-2.pdf": 13, "PDR_Strategy_Guide.pdf": 4,
             "PDS strategy.pdf": 7, "RF strategy.pdf": 9}
CLASSES = {"VERIFIED_EXPLICIT", "VERIFIED_QUALITATIVE", "CONFLICTING", "MISSING", "PROPOSED"}
REQUIRED = {"rule_id", "strategy", "method", "description", "source_document", "source_page", "classification",
            "required_inputs", "mathematical_condition", "evaluation_time", "invalidation_condition",
            "implementation_status", "unresolved_dependencies"}


# ------------------------------------------------------------------ random sessions for property tests
def random_ctx(seed: int):
    rng = np.random.default_rng(seed)

    def walk(start, n=75):
        out, p = [], start
        for _ in range(n):
            o = p
            c = o + rng.normal(0, 12)
            h = max(o, c) + abs(rng.normal(0, 6))
            l = min(o, c) - abs(rng.normal(0, 6))  # noqa: E741
            out.append((o, h, l, c))
            p = c
        return out

    prev = walk(24000)
    prev_close = prev[-1][3] + rng.normal(0, 5)
    first_open = prev_close + rng.normal(0, 60)
    day = walk(first_open)
    ema = [float(np.mean([x[3] for x in day[:k + 1]]) + rng.normal(0, 25)) for k in range(75)]
    return ctx(day, prev={"cands": prev, "close": prev_close, "ema_last": 24000 + rng.normal(0, 30)}, ema=ema,
               prior_above=tuple(bool(x) for x in rng.integers(0, 2, 3)))


def keyed(recs, upto):
    return sorted((r.method, r.direction, r.signal_timestamp, r.signal_candle_close, r.signal_status) for r in recs
                  if r.signal_status in ("CONFIRMED", "INVALIDATED") and r.signal_timestamp is not None and r.signal_timestamp <= upto)


@pytest.mark.rules("DATA-TIME-001", "IRF-GLOBAL-003", "ORB-GLOBAL-001")
@pytest.mark.parametrize("strategy", ALL_STRATEGIES, ids=lambda s: s.STRATEGY)
def test_no_lookahead_truncated_session_equals_prefix_of_full_session(strategy):
    eng = strategy()
    compared = 0
    for seed in range(40):
        c = random_ctx(seed)
        full = eng.evaluate_session(c)
        ends = list(c.candles["bar_end"])
        for k in range(1, 76):
            pre = eng.evaluate_session(c.prefix(k))
            assert keyed(pre, ends[k - 1]) == keyed(full, ends[k - 1]), f"{strategy.STRATEGY} seed={seed} k={k}"
            compared += 1
        for r in full:
            if r.signal_timestamp is not None:  # trigger candle is complete at its end, on the 5-minute grid, never before 09:20
                assert r.signal_timestamp.minute % 5 == 0 and r.signal_timestamp.second == 0
                assert r.signal_timestamp >= pd.Timestamp(DAY.year, DAY.month, DAY.day, 9, 20, tz=IST)
    assert compared == 40 * 75


def _fixtures():
    import test_phase2_irf as irf
    import test_phase2_orb as orb
    import test_phase2_pdr_pds_rf as o
    return [
        (IRFStrategy(), ctx([irf.IR, (98, 104, 97, 103), (103, 103.5, 98, 99)])),
        (IRFStrategy(), ctx(irf.M2A)), (IRFStrategy(), ctx(irf.M2B)), (IRFStrategy(), ctx(irf.M3)),
        (ALL_STRATEGIES[1](), ctx([orb.STRONG_UP, (24055, 24056, 24054, 24055)], prev=orb.PREV, ema=23950.0)),
        (ALL_STRATEGIES[2](), ctx([(24050, 24060, 24040, 24055), (24055, 24058, 24001, 24003), (24003, 24030, 24002, 24025)], prev=o.PDR_PREV)),
        (ALL_STRATEGIES[3](), ctx([(23950, 23960, 23940, 23945), (24010, 24015, 23960, 23965)], prev=o.PDS_PREV)),
        (ALL_STRATEGIES[4](), ctx(o.RF_OK, prev=o.RF_PREV, ema=23950.0)),
    ]


@pytest.mark.rules("DATA-TIME-001")
def test_every_worked_fixture_signal_appears_only_when_its_trigger_candle_closes():
    n_checked = 0
    for eng, c in _fixtures():
        confirmed = [r for r in eng.evaluate_session(c) if r.signal_status == "CONFIRMED"]
        assert confirmed, f"fixture for {eng.STRATEGY} produced no signal (test would be vacuous)"
        for r in confirmed:
            idx = list(c.candles["bar_start"]).index(r.signal_candle_start)
            before = [x for x in eng.evaluate_session(c.prefix(idx)) if x.signal_status == "CONFIRMED" and x.method == r.method
                      and x.signal_timestamp == r.signal_timestamp]
            after = [x for x in eng.evaluate_session(c.prefix(idx + 1)) if x.signal_status == "CONFIRMED" and x.method == r.method
                     and x.signal_timestamp == r.signal_timestamp]
            assert not before and after
            n_checked += 1
    assert n_checked >= 8


# ------------------------------------------------------------------ registry integrity
def test_registry_ids_unique_fields_complete_and_classifications_valid():
    ids = [r["rule_id"] for r in RULES]
    assert len(ids) == len(set(ids))
    for r in RULES:
        assert REQUIRED <= set(r), r["rule_id"]
        assert r["classification"] in CLASSES
        if r["classification"] == "PROPOSED":
            assert r["implementation_status"] in (IMPL_P, NOT)  # a PROPOSED rule is never 'implemented verified'


def test_source_pages_do_not_exceed_the_actual_document_page_counts():
    from pypdf import PdfReader
    for doc, n in DOC_PAGES.items():
        path = ROOT / "docs" / "strategy_docs" / doc
        if path.exists():
            assert len(PdfReader(str(path)).pages) == n, doc
    for r in RULES:
        if r["source_document"] in DOC_PAGES:
            pages = [int(p) for p in str(r["source_page"]).replace(" vs ", ",").replace("-", ",").split(",") if p.strip().isdigit()]
            assert pages and max(pages) <= DOC_PAGES[r["source_document"]], r["rule_id"]


def test_every_implemented_rule_has_code_and_every_code_reference_exists():
    coded = {rid for ids in IMPLEMENTATIONS.values() for rid in ids}
    from nifty_trading.strategies.rule_data import RULE_IDS
    assert coded <= RULE_IDS
    must_have_code = {r["rule_id"] for r in RULES if r["implementation_status"] in ("IMPLEMENTED_VERIFIED", IMPL_P, IMPL_R)
                      and r["strategy"] in ("IRF", "ORB", "PDR", "PDS", "RF", "DATA")}
    assert not (must_have_code - coded), sorted(must_have_code - coded)


def test_every_rule_id_cited_in_emitted_records_exists_in_the_registry():
    from nifty_trading.strategies.rule_data import RULE_IDS
    n = 0
    for eng, c in _fixtures():
        for r in eng.evaluate_session(c):
            for rid in r.rule_ids_satisfied + r.rule_ids_failed + r.rule_ids_unresolved:
                assert rid in RULE_IDS, rid
                n += 1
    assert n > 40


def test_the_yaml_registry_is_in_sync_with_the_python_registry():
    path = ROOT / "docs" / "phase2" / "rule_registry.yaml"
    if not path.exists():
        pytest.skip("run scripts/phase2_build_docs.py first")
    doc = yaml.safe_load(path.read_text())
    assert [r["rule_id"] for r in doc["rules"]] == [r["rule_id"] for r in RULES]
    for y, r in zip(doc["rules"], RULES, strict=True):
        assert {k: y[k] for k in r} == yaml.safe_load(yaml.safe_dump(r)), r["rule_id"]  # YAML adds implemented_by / tested_by only
    assert doc["unresolved_flags"]["RF_TARGET_STATUS"] == "UNRESOLVED"


@pytest.mark.rules("RF-011")
def test_rf_target_is_never_silently_assigned_anywhere():
    from nifty_trading.strategies.params import RF_TARGET_STATUS, SOURCE
    assert RF_TARGET_STATUS == "UNRESOLVED" and SOURCE.rf_target_points is None
    from nifty_trading.core.exit_policy import policy_for
    assert policy_for("RF").t2_points is None


# ------------------------------------------------------------------ BaseStrategy adapter
def _ctx_at(df, label):
    t = datetime(DAY.year, DAY.month, DAY.day, *label, tzinfo=IST)
    row = df[df.timestamp == t].iloc[0]
    return StrategyContext(current_time=t, current_candle=row, historical_candles=df)


@pytest.mark.rules("IRF-M1-004", "DATA-TIME-001")
def test_on_candle_emits_the_signal_only_on_the_last_minute_of_the_trigger_candle():
    # NOTE: the history clip inside on_candle is defence in depth (the engine is causal), so this test cannot detect its removal.
    cands = [(95, 100, 90, 98), (98, 104, 97, 103), (103, 103.5, 98, 99), (99, 150, 40, 41)]  # 4th candle is wild future data
    df = minute_rows(cands)
    eng = IRFStrategy()
    assert eng.on_candle(_ctx_at(df, (9, 28))) == []  # mid-candle: 09:25-09:30 not complete
    [sig] = eng.on_candle(_ctx_at(df, (9, 29)))  # last minute of the 09:25 candle; df still contains the future candle
    assert sig.signal_type is SignalType.SELL and sig.price == 99 and sig.stop_loss is None and sig.target is None
    assert sig.metadata["method"] == "Method 1" and sig.metadata["reference_price_is_fill"] is False
    assert eng.on_candle(_ctx_at(df, (9, 34))) == []  # later candle: nothing new


# ------------------------------------------------------------------ real dataset (Phase 1 parquet)
DATA = ROOT / "data" / "processed" / "nifty50"
needs_data = pytest.mark.skipif(not DATA.exists(), reason="Phase 1 parquet dataset not present")


@pytest.fixture(scope="module")
def real():
    from nifty_trading.data.sessions import build_session_contexts, load_one_minute
    df = load_one_minute()
    ctxs, infos = build_session_contexts(df)
    return df, ctxs, infos


@needs_data
def test_real_dataset_facts(real):
    df, ctxs, infos = real
    assert len(df) == 92_981 and df.timestamp.is_unique and df.timestamp.is_monotonic_increasing
    assert str(df.timestamp.dt.tz) == "Asia/Kolkata" and (df.timestamp.dt.second == 0).all()
    assert len(infos) == 248 and len(ctxs) == 247
    excluded = [d for d, i in infos.items() if not i.usable]
    assert [str(d) for d in excluded] == ["2025-10-21"]  # Muhurat session
    flagged = {str(d): i.flags for d, i in infos.items() if i.flags and i.usable}
    stale = {d for d, f in flagged.items() if any(x.startswith("STALE_FEED_ROWS_EXCLUDED") for x in f)}
    assert len(stale) == 21 and min(stale) == "2026-08-03" and max(stale) == "2026-08-31"  # frozen-feed tail, then excluded
    assert set(flagged) == {"2025-11-25", "2026-02-01", "2026-03-10"} | stale
    for d, c in ctxs.items():
        n_stale = str(d) in stale
        assert len(c.candles) == (72 if n_stale else 75), d  # the 15:15, 15:20 and 15:25 candles are dropped, never repaired


@needs_data
def test_real_dataset_timestamps_are_start_of_minute_labels(real):
    df, _, _ = real
    rng = df.high - df.low
    t = df.timestamp.dt.strftime("%H:%M")
    assert (rng[t == "09:15"] > 0).all() and (rng[t == "15:30"] == 0).mean() > 0.7  # 15:30 is a closing-print stub
    assert rng[t == "09:15"].median() > 10 * max(rng[t == "15:30"].median(), 1e-9) or rng[t == "15:30"].median() == 0


@needs_data
def test_real_first_candle_is_rows_0915_to_0919_and_closes_at_0920(real):
    df, ctxs, _ = real
    d = sorted(ctxs)[10]
    rows = df[(df.timestamp.dt.date == d) & (df.timestamp.dt.strftime("%H:%M") <= "09:19")]
    c = ctxs[d].candles.iloc[0]
    assert (c.open, c.high, c.low, c.close) == (rows.open.iloc[0], rows.high.max(), rows.low.min(), rows.close.iloc[-1])
    assert c.bar_end.strftime("%H:%M") == "09:20"


@needs_data
def test_real_indicator_warmup_facts(real):
    _, ctxs, _ = real
    days = sorted(ctxs)
    assert math.isnan(ctxs[days[0]].candles["ema200_5m"].iloc[0]) and math.isnan(ctxs[days[2]].candles["ema200_5m"].iloc[0])
    assert not math.isnan(ctxs[days[3]].candles["ema200_5m"].iloc[0])  # 3 sessions x 75 >= 200
    n_daily = sum(not math.isnan(c.daily_sma200_prev) for c in ctxs.values())
    assert n_daily == 47  # a 200-DMA candidate is evaluable on only the last 47 sessions with Phase 1 data


@needs_data
@pytest.mark.parametrize("strategy", ALL_STRATEGIES, ids=lambda s: s.STRATEGY)
def test_real_sessions_run_cleanly_with_valid_rule_ids_and_no_early_signals(real, strategy):
    from nifty_trading.strategies.rule_data import RULE_IDS
    _, ctxs, _ = real
    eng = strategy()
    for c in ctxs.values():
        for r in eng.evaluate_session(c):
            for rid in r.rule_ids_satisfied + r.rule_ids_failed + r.rule_ids_unresolved:
                assert rid in RULE_IDS
            if r.signal_status == "CONFIRMED":
                assert r.signal_timestamp.strftime("%H:%M") >= "09:20" and r.signal_timestamp.strftime("%H:%M") <= "15:30"
                assert r.verification_status != "NOT_READY" and r.reference_price_is_fill is False
            if r.signal_status == "NOT_EVALUATED":
                assert r.verification_status == "NOT_READY"


@needs_data
@pytest.mark.parametrize("strategy", ALL_STRATEGIES, ids=lambda s: s.STRATEGY)
def test_real_sessions_prefix_invariance_sample(real, strategy):
    _, ctxs, _ = real
    eng = strategy()
    days = sorted(ctxs)[5::12]
    for d in days:
        c = ctxs[d]
        full = eng.evaluate_session(c)
        ends = list(c.candles["bar_end"])
        for k in range(1, len(ends) + 1, 3):
            assert keyed(eng.evaluate_session(c.prefix(k)), ends[k - 1]) == keyed(full, ends[k - 1]), (strategy.STRATEGY, d, k)


@pytest.mark.rules("IRF-M1-004")
def test_signal_window_end_keeps_signals_up_to_and_including_the_cutoff_minute():
    from nifty_trading.strategies import ProposalConfig
    c = ctx([(95, 100, 90, 98), (98, 104, 97, 103), (103, 103.5, 98, 99)])  # Method 1 fires at 09:30
    keep = IRFStrategy(proposals=ProposalConfig(signal_window_end="09:30")).evaluate_session(c)
    drop = IRFStrategy(proposals=ProposalConfig(signal_window_end="09:25")).evaluate_session(c)
    assert [r.method for r in keep if r.signal_status == "CONFIRMED"] == ["Method 1"]
    assert not [r for r in drop if r.signal_status == "CONFIRMED"]


def test_verification_never_reports_verified_for_a_rule_that_is_not_verified_explicit(monkeypatch):
    from nifty_trading.strategies import base
    assert base.verification_for(["IRF-M1-001", "IRF-M1-002"], []).value == "VERIFIED"  # both VERIFIED_EXPLICIT and implemented verified
    fake = dict(base.RULE_BY_ID["IRF-M1-001"], classification="VERIFIED_QUALITATIVE")
    monkeypatch.setitem(base.RULE_BY_ID, "IRF-M1-001", fake)  # same rule but only 'qualitative'
    assert base.verification_for(["IRF-M1-001"], []).value == "PROPOSAL_DEPENDENT"
    assert base.verification_for(["IRF-M2-002"], []).value == "PROPOSAL_DEPENDENT"
    assert base.verification_for(["ORB-GAP-LONG-004"], ["ORB-GAP-LONG-005"]).value == "RESEARCH_VARIANT"
