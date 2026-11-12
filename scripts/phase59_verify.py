"""Read-only final artifact checks, independent of the chart renderer and strategies."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import xml.etree.ElementTree as ET
from pathlib import Path

import openpyxl
import pandas as pd
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/phase5/phase59_orb_author_validation"
NS = {"s": "http://www.w3.org/2000/svg"}
OHLC = ("open", "high", "low", "close")


def read(name):
    return json.loads((OUT / name).read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def near(actual, expected, tolerance=1e-7):
    assert math.isclose(float(actual), float(expected), abs_tol=tolerance, rel_tol=0), (actual, expected)


def main():
    before = read("before_hashes.json")["files"]
    drift = [p for p, digest in before.items() if not (ROOT / p).is_file() or sha(ROOT / p) != digest]
    assert not drift, drift
    input_hashes = read("data_source_hashes.json")
    assert all(sha(ROOT / p) == digest for p, digest in input_hashes.items())

    # Recount literal workbook rows; never repair a date, label or time.
    journal = openpyxl.load_workbook(ROOT / "docs/trading journal/Trading_Journal_Sep2025_Aug2026 REPORT.xlsx", read_only=True, data_only=True)
    original = [(i, r) for i, r in enumerate(journal["Trading Journal"].values, 1) if i >= 3 and r[0] is not None]
    orb_dates = {r[1].date().isoformat() for _, r in original if r[3] == "ORB"}
    assert len(original) == 190 and sum(r[3] == "ORB" for _, r in original) == len(orb_dates) == 89
    recount = pd.read_csv(OUT / "journal_recount_rows.csv", keep_default_na=False)
    for (i, r), (_, target) in zip(original, recount.iterrows(), strict=True):
        assert target.sheet_row == i and target.date == r[1].date().isoformat()
        assert target.time_label == str(r[2]) and target.strategy_as_written == r[3]
    journal.close()

    # Use raw minute data to rebuild five-minute OHLC without project helpers.
    inputs = sorted({p for row in csv.DictReader((OUT / "source_to_chart_traceability.csv").open())
                     for p in json.loads(row["ema_input_partitions"])})
    raw = pd.concat([pd.read_parquet(ROOT / p) for p in inputs]).sort_values("timestamp")
    assert not raw.timestamp.duplicated().any()
    raw_all = raw.set_index("timestamp")
    starts = raw.groupby(raw.timestamp.dt.date).timestamp.min()
    standard_days = set(starts[starts.dt.strftime("%H:%M") == "09:15"].index)
    raw = raw[raw.timestamp.dt.date.isin(standard_days)]
    minute_of_day = raw.timestamp.dt.hour * 60 + raw.timestamp.dt.minute
    raw = raw[(minute_of_day >= 555) & (minute_of_day < 930)]
    raw = raw.set_index("timestamp")
    five = raw.resample("5min", origin="start_day", offset="15min", label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
    counts = raw.close.resample("5min", origin="start_day", offset="15min").size()
    incomplete_buckets = int((counts.loc[five.index] != 5).sum())
    five = five.loc[counts.loc[five.index] == 5]
    alpha = 2 / 201
    ema = {}
    seed = float(five.close.iloc[:200].mean())
    for i, (ts, close) in enumerate(five.close.items()):
        if i < 199:
            continue
        seed = seed if i == 199 else alpha * float(close) + (1-alpha) * seed
        ema[ts] = seed

    cases = read("case_data.json")
    assert len(cases) == 52
    case_candles = ema_checks = 0
    for payload in cases.values():
        assert all(v is None for v in payload["author_entry"].values())
        assert payload["case"]["expected_orb_direction"] == payload["case"]["expected_entry_candle"] == "UNKNOWN"
        assert all(v is None for k, v in payload["case"].items() if k.startswith("author_reviewed_") or k in
                   ("author_explanation", "author_confirms_trade", "source_supports_general_rule", "engineering_implementation_approved"))
        assert not any(path["eligible"] for path in payload["paths"])
        for group in ("one_minute", "five_minute", "previous_five_minute", "history_five_minute"):
            minute = group == "one_minute"
            for row in payload[group]:
                ts = pd.Timestamp(row["timestamp" if minute else "bar_start"])
                source = (raw_all if minute else five).loc[ts]
                for k in OHLC:
                    near(row[k], source[k])
                case_candles += 1
                if not minute:
                    near(row["ema200_5m"], ema[ts])
                    ema_checks += 1

    signals = pd.read_csv(ROOT / "reports/phase5/phase55_combined_backtest/all_confirmed_signals.csv")
    ledger = pd.read_csv(ROOT / "reports/phase5/phase55_combined_backtest/all_executed_trades.csv")
    ledger = ledger[ledger.config == "A"]
    signals = signals[signals.config == "A"]
    active_dates = set(raw.index.date.astype(str))
    evaluable = orb_dates & active_dates
    orb_signal_dates = set(signals.loc[signals.strategy == "ORB", "date"]) & evaluable
    orb_trade_dates = set(ledger.loc[ledger.strategy == "ORB", "date"]) & evaluable
    irf_dates = set(ledger.loc[ledger.strategy == "IRF", "date"]) & evaluable
    missing = evaluable - orb_signal_dates
    assert (len(evaluable), len(orb_signal_dates), len(orb_trade_dates), len(missing), len(irf_dates)) == (85,35,35,50,34)
    assert orb_signal_dates == orb_trade_dates and irf_dates <= missing
    assert set(pd.read_csv(OUT / "all_50_missing_orb_dates.csv").date) == missing
    hand = set(pd.read_csv(OUT / "all_13_handwritten_cases.csv").date)
    assert len(hand) == 13 and len(hand & missing) == 11 and set(cases) == hand | missing
    ledger = ledger.set_index("trade_id")
    ledger_checks = 0
    for payload in cases.values():
        for trade in payload["trades"]:
            source = ledger.loc[trade["trade_id"]]
            assert source.strategy == trade["strategy"] and source.method == trade["method"] and source.direction == trade["direction"]
            assert pd.Timestamp(source.signal_confirmed_at).strftime("%H:%M") == trade["signal_time"]
            assert pd.Timestamp(source.fill_timestamp).strftime("%H:%M") == trade["entry_time"]
            near(raw.loc[pd.Timestamp(source.fill_timestamp).tz_localize("Asia/Kolkata"), "open"], trade["entry"])
            for key, col in (("entry", "entry_price"), ("stop", "initial_stop"), ("t1", "target_1"), ("t2", "target_2")):
                near(trade[key], source[col])
            for leg in trade["exits"]:
                near(leg["price"], source[f'leg{leg["leg"]}_exit_price'])
                assert pd.Timestamp(source[f'leg{leg["leg"]}_exit_time']).strftime("%H:%M") == leg["time"]
            ledger_checks += 1

    chart_rows = []
    trace = list(csv.DictReader((OUT / "source_to_chart_traceability.csv").open()))
    assert len(trace) == 62
    for record in trace:
        svg = ET.parse(OUT / record["chart_svg"]).getroot()
        meta = json.loads(svg.find("s:metadata", NS).text)
        assert all(v is None for v in meta["author_entry"].values()) and meta["orb_confirmed_signals"] == []
        assert not record["author_entry_time"] and not record["author_entry_price"]
        plot, scale, box = meta["plot"], meta["scale"], meta["author_box"]
        assert box["x"] > plot["right"]
        assert meta["author_label"] == "AUTHOR ORB ENTRY — TO BE MARKED"
        assert json.loads(record["all_plotted_raw_partitions"]) == meta["data_provenance"]["plotted_partitions"]
        for partition in meta["data_provenance"]["plotted_partitions"] + meta["data_provenance"]["ema_input_partitions"]:
            assert partition in input_hashes

        def px(i, plot=plot, scale=scale):
            return plot["left"] + i / scale["count"] * (plot["right"] - plot["left"])

        def py(price, plot=plot, scale=scale):
            return plot["top"] + (scale["price_high"]-price) / (scale["price_high"]-scale["price_low"]) * (plot["bottom"]-plot["top"])

        candles = svg.findall("s:g[@class='candle']", NS)
        assert len(candles) == len(meta["candles"]) == int(record["candles_drawn"])
        for i, (node, row) in enumerate(zip(candles, meta["candles"], strict=True)):
            ts = pd.Timestamp(row[meta["time_key"]])
            source = (raw if meta["period_minutes"] == 1 else five).loc[ts]
            for key in OHLC:
                near(node.get(f"data-{key}"), source[key])
            wick, body = node.find("s:line", NS), node.find("s:rect", NS)
            near(wick.get("x1"), px(i+.5), .001)
            near(wick.get("y1"), py(source.high), .001)
            near(wick.get("y2"), py(source.low), .001)
            near(body.get("y"), py(max(source.open, source.close)), .001)
            near(body.get("height"), max(abs(py(source.open)-py(source.close)), 1), .001)
        levels = svg.findall("s:line[@class='reference_level']", NS)
        for node in levels:
            level = next(v for v in meta["levels"] if v["label"] == node.get("data-label"))
            near(node.get("data-price"), level["price"])
            near(node.get("y1"), py(level["price"]), .001)
            near(node.get("x1"), px(level["from_index"]), .001)
        markers = svg.findall("s:g[@class='trade_marker']", NS)
        assert len(markers) == len(meta["markers"])
        for node, marker in zip(markers, meta["markers"], strict=True):
            assert node.get("data-role") == marker["role"] and node.get("data-trade") == marker["trade_id"]
            circle = node.find("s:circle", NS)
            near(circle.get("cx"), px(marker["x_index"]), .001)
            near(circle.get("cy"), py(marker["price"]), .001)
            trade = ledger.loc[marker["trade_id"]]
            col = "entry_price" if marker["role"] == "ENTRY" else f'leg{marker["role"][-1]}_exit_price'
            near(marker["price"], trade[col])
        png = Image.open(OUT / record["chart_png"])
        assert png.size == (3400, 2125)
        near(png.info["dpi"][0], 300, .05)
        chart_rows.append({"date": meta["date"], "kind": meta["kind"], "candles": len(candles),
                           "reference_lines": len(levels), "ledger_markers": len(markers), "raw_ohlc_and_svg_positions_match": True,
                           "unknown_author_outside_plot": True, "high_resolution_png": True})
    for folder in ("priority_five", "remaining_eight", "all_missing_orb"):
        for file in (OUT / folder).glob("*.png"):
            assert sha(file) == sha(OUT / "author_review_charts" / file.name)

    workbook = openpyxl.load_workbook(OUT / "ORB_Author_Review.xlsx", data_only=True)
    blank = [cell for row in workbook["CaseReview"].iter_rows(min_row=5, max_row=56, min_col=4, max_col=12) for cell in row]
    assert len(blank) == 468 and all(c.value is None for c in blank)
    assert all(c.value is None for row in workbook["RuleQuestions"].iter_rows(min_row=5,max_row=10,min_col=7,max_col=9) for c in row)
    assert len({workbook["CaseReview"].cell(i,1).value for i in range(5,57)}) == 52
    expected = [190,89,89,85,35,35,50,34,13,52,5]
    assert [workbook["Overview"].cell(i,2).value for i in range(5,16)] == expected
    assert [workbook["Overview"].cell(i,2).value for i in (18,19,20)] == [0,0,52]
    assert not [(ws.title,c.coordinate,c.value) for ws in workbook for row in ws for c in row if c.data_type == "e"]
    workbook.close()
    structure = openpyxl.load_workbook(OUT / "ORB_Author_Review.xlsx", data_only=False)
    assert "AuthorCases" in structure["CaseReview"].tables
    assert structure["CaseReview"].data_validations.count >= 3
    structure.close()
    pdf = read("pdf_quality_checks.json")
    assert pdf["pages"] == 34 and pdf["embedded_charts_match_latest_pngs"] and not pdf["text_outside_page"]
    assert pdf["sha256"] == sha(OUT / "ORB_Author_Review_Package.pdf")
    assert "784 passed, 1 skipped, 1 xfailed" in (OUT / "pytest_full.log").read_text()
    result = {"original_files_verified_unchanged":len(before), "data_hash_manifest_entries_verified":len(input_hashes),
              "referenced_minute_partitions":len(inputs), "incomplete_buckets_excluded":incomplete_buckets,
              "independent_baseline":[89,85,35,50,34], "case_union":52,
              "case_candle_comparisons":case_candles,"case_ema_comparisons":ema_checks,"ledger_trades_verified":ledger_checks,
              "charts_verified":len(chart_rows),"svg_candles_verified":sum(r["candles"] for r in chart_rows),
              "ledger_markers_verified":sum(r["ledger_markers"] for r in chart_rows), "blank_case_author_cells":len(blank),
              "pdf_pages":pdf["pages"],"all_checks_passed":True}
    with (OUT / "chart_verification.csv").open("w") as f:
        writer = csv.DictWriter(f,fieldnames=chart_rows[0].keys())
        writer.writeheader()
        writer.writerows(chart_rows)
    (OUT / "independent_audit_results.json").write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))


if __name__ == "__main__":
    main()
