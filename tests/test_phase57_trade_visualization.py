"""Phase 5.7: unit tests of the enhanced trade-chart renderer on a hand-built specification (labels, the post-T1 stop only after T1, price-to-pixel geometry, label placement without overlaps, badge) and file-level tests on the delivered
bundle (one chart per executed trade, subset folders, exact-match counts equal to the verified Phase 5.6 numbers, labels equal to the ledger). Presentation only: nothing here runs a backtest."""

from __future__ import annotations

import csv
import json
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from nifty_trading.research import phase57 as V

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "phase5" / "phase57_trade_visualization"
P55 = ROOT / "reports" / "phase5" / "phase55_combined_backtest"
P56 = ROOT / "reports" / "phase5" / "phase56_manual_reconciliation"
NS = "{http://www.w3.org/2000/svg}"
needs_bundle = pytest.mark.skipif(not (OUT / "phase57_state.json").exists(), reason="Phase 5.7 bundle not generated")


def candles(n=24, start=datetime(2026, 1, 5, 9, 15), base=100.0):
    out = []
    for i in range(n):
        o = base + (i % 5) * 0.8
        out.append({"start": start + timedelta(minutes=5 * i), "o": o, "h": o + 2, "l": o - 2, "c": o + (1 if i % 2 else -1), "ema": base - 3})
    return out


def spec(post=105.0, t1_hit=True, status="EXACT_MATCH", direction="LONG"):
    e0 = datetime(2026, 1, 5, 9, 35)
    t1ts = datetime(2026, 1, 5, 9, 50)
    t2ts = datetime(2026, 1, 5, 10, 20)
    exits = [{"leg": "1", "label": "LEG1 EXIT — T1 hit, 09:50 @ 127.00", "ts": t1ts, "price": 127.0, "reason": "TARGET_1"}, {"leg": "2", "label": "LEG2 EXIT — T2 hit, 10:20 @ 160.00", "ts": t2ts, "price": 160.0, "reason": "TARGET_2"}]
    return {"header": {"l1": "TRADE X", "l2": "line two", "l3": "line three", "l4": "journal row #1"}, "badge": (status, status), "candles": candles(), "hlines": [("prev-day high", 110.0, "#1b5e20"), ("far away level", 5000.0, "#000")], "zones": [], "marks": [],
            "manual": [{"label": "09:30", "row": "1", "matched": True, "text": "JOURNAL #1 ORB 09:30 Target"}],
            "trade": {"direction": direction, "entry_ts": e0, "entry": 100.0, "stop": 65.0, "t1": 127.0, "t2": 160.0, "post_t1": post if t1_hit else None, "t1_hit_ts": t1ts if t1_hit else None, "exits": exits},
            "blocks": [("ENTRY", [("a line", "")]), ("LEVELS", [("x", "b")]), ("P&L", [("y", "g")]), ("JOURNAL", [("z", "ok")])], "meta": {"kind": "TRADE", "trade_id": "X"}, "note": "note"}


def texts(svg):
    root = ET.fromstring(svg)
    out = {}
    for el in root.iter(f"{NS}text"):
        out.setdefault(el.get("data-kind", "_"), []).append("".join(el.itertext()))
    return root, out


def test_labels_levels_and_exits_are_named_and_priced():
    _root, t = texts(V.render(spec()))
    assert t["ENTRY_LABEL"] == ["ENTRY 09:35 @ 100.00"]
    assert t["LABEL_SL"] == ["SL @ 65.00"] and t["LABEL_T1"] == ["T1 @ 127.00"] and t["LABEL_T2"] == ["T2 @ 160.00"] and t["LABEL_POST_T1_STOP"] == ["POST-T1 STOP @ 105.00"]
    assert t["EXIT_LABEL_1"] == ["LEG1 EXIT — T1 hit, 09:50 @ 127.00"] and t["EXIT_LABEL_2"] == ["LEG2 EXIT — T2 hit, 10:20 @ 160.00"]


def test_post_t1_stop_is_never_drawn_when_t1_was_not_hit():
    s = spec(t1_hit=False)
    s["trade"]["exits"] = [{"leg": "FULL", "label": "FULL EXIT — Initial SL, 09:55 @ 65.00", "ts": datetime(2026, 1, 5, 9, 55), "price": 65.0, "reason": "ORIGINAL_STOP_BEFORE_T1"}]
    root, t = texts(V.render(s))
    assert "LABEL_POST_T1_STOP" not in t and not any(el.get("data-kind") == "POST_T1_STOP" for el in root.iter())
    assert t["EXIT_LABEL_FULL"] == ["FULL EXIT — Initial SL, 09:55 @ 65.00"]


def test_every_price_line_sits_at_its_price_on_the_charts_own_scale():
    svg = V.render(spec())
    root = ET.fromstring(svg)
    meta = json.loads(root.find(f"{NS}metadata").text)
    sc = meta["scale"]
    n = 0
    for el in root.iter(f"{NS}line"):
        if el.get("data-price") is None:
            continue
        y = float(el.get("y1"))
        price = sc["price_high"] - (y - sc["plot_top"]) / (sc["plot_bottom"] - sc["plot_top"]) * (sc["price_high"] - sc["price_low"])
        assert abs(price - float(el.get("data-price"))) < (sc["price_high"] - sc["price_low"]) / (sc["plot_bottom"] - sc["plot_top"]) * 0.1 + 1e-6
        n += 1
    assert n == 5  # entry, SL, T1, T2, post-T1 stop


def test_far_away_reference_levels_are_listed_not_drawn():
    svg = V.render(spec())
    assert "off the price scale" in svg and "far away level 5,000.00" in svg
    assert "prev-day high 110.00" in svg  # the near level is drawn and named in the right margin


def test_badge_colour_follows_the_match_status():
    for status, col in V.BADGE.items():
        if status != "NO_TRADE_JOURNAL_DAY":
            assert col in V.render(spec(status=status))


def test_right_margin_labels_never_overlap():
    items = [{"y": 100.0 + 2 * i} for i in range(10)] + [{"y": 480.0}, {"y": 481.0}]
    V.spread(items, 13.0, 120.0, 500.0)
    ys = sorted(it["ly"] for it in items)
    assert all(b - a >= 13.0 - 1e-9 for a, b in zip(ys, ys[1:], strict=False)) and ys[0] >= 120.0 and ys[-1] <= 500.0 + 1e-9


def test_labels_next_to_markers_do_not_overlap():
    labels = [{"x": 300.0, "y": 200.0, "text": "ENTRY 09:35 @ 100.00"}, {"x": 305.0, "y": 202.0, "text": "LEG1 EXIT - T1 hit, 09:50 @ 127.00"}, {"x": 1100.0, "y": 210.0, "text": "LEG2 EXIT - T2 hit, 10:20 @ 160.00"}]
    V.place_near(labels, 1200.0, 130.0, 590.0)
    boxes = [(lb["lx"] if lb["anchor"] == "start" else lb["lx"] - V.CH_W * len(lb["text"]), lb["ly"]) for lb in labels]
    for i, a in enumerate(labels):
        for j, b in enumerate(labels):
            if i < j:
                wa, wb = V.CH_W * len(a["text"]), V.CH_W * len(b["text"])
                overlap_x = boxes[i][0] < boxes[j][0] + wb and boxes[j][0] < boxes[i][0] + wa
                assert not (overlap_x and abs(a["ly"] - b["ly"]) < 11)
    assert labels[2]["anchor"] == "end"  # a label that does not fit on the right of its marker goes to the left


def test_money_format():
    assert V.money(24985.4) == "24,985.40" and V.money(5.0, 0) == "5"


@needs_bundle
def test_bundle_has_one_chart_per_trade_and_the_verified_exact_counts():
    trades = list(csv.DictReader(open(P55 / "all_executed_trades.csv", newline="")))
    st56 = json.loads((P56 / "phase56_state.json").read_text())
    files = {p.name for p in (OUT / "charts_all").glob("*.svg")}
    assert files == {f"{t['config']}_{t['trade_id']}.svg" for t in trades} and len(files) == 574
    summ = {r["config"]: r for r in csv.DictReader(open(OUT / "exact_match_summary.csv", newline=""))}
    for k in "ABC":
        m = st56["matching"][k]
        assert (int(summ[k]["strict"]), int(summ[k]["time_tolerant"]), int(summ[k]["date_strategy_only"])) == (m["strict"], m["time_tolerant"], m["date_strategy_only"])
        assert int(summ[k]["counted_matches"]) == m["strict"] + m["time_tolerant"] and int(summ[k]["automated_trades"]) == m["automated_trades"]
    assert len(list((OUT / "charts_exact_matches").glob("*.svg"))) == sum(st56["matching"][k]["strict"] for k in "ABC")
    assert len(list((OUT / "charts_time_tolerant").glob("*.svg"))) == sum(st56["matching"][k]["time_tolerant"] for k in "ABC")


@needs_bundle
def test_chart_labels_equal_the_ledger_for_every_trade():
    trades = list(csv.DictReader(open(P55 / "all_executed_trades.csv", newline="")))
    legs = {}
    for g in csv.DictReader(open(P55 / "all_trade_legs.csv", newline="")):
        legs.setdefault((g["config"], g["trade_id"]), {})[g["leg"]] = g
    bad = []
    for t in trades:
        _r, tx = texts((OUT / "charts_all" / f"{t['config']}_{t['trade_id']}.svg").read_text())
        t1_hit = legs[(t["config"], t["trade_id"])]["1"]["exit_reason"] == "TARGET_1"
        want = [f"ENTRY {t['fill_timestamp'][-5:]} @ {float(t['entry_price']):,.2f}"]
        if tx.get("ENTRY_LABEL") != want or tx.get("LABEL_SL") != [f"SL @ {float(t['initial_stop']):,.2f}"] or tx.get("LABEL_T1") != [f"T1 @ {float(t['target_1']):,.2f}"] or tx.get("LABEL_T2") != [f"T2 @ {float(t['target_2']):,.2f}"]:
            bad.append((t["config"], t["trade_id"]))
        if ("LABEL_POST_T1_STOP" in tx) != t1_hit:
            bad.append((t["config"], t["trade_id"], "post-T1"))
    assert not bad


@needs_bundle
def test_status_counts_on_the_index_are_consistent():
    idx = list(csv.DictReader(open(OUT / "all_executed_trades_visual_index.csv", newline="")))
    c = Counter((i["config"], i["match_status"]) for i in idx)
    assert sum(c.values()) == 574 and all(i["journal_row"] for i in idx if i["match_status"] != "AUTOMATED_ONLY") and not any(i["journal_row"] for i in idx if i["match_status"] == "AUTOMATED_ONLY")
