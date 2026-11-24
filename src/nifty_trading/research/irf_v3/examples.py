"""Recreation of every worked example in the two rulebooks.

Authority of the figures: only the numbers printed in the PDFs are source facts; prices read off screenshots are approximate (the PDFs say so). Two examples per method are drawn
illustrations (synthetic candles built to carry the labelled numbers); the others are TradingView screenshots. A screenshot with no date is NEVER assigned a date here.
"""

from __future__ import annotations

from datetime import date

from nifty_trading.research.irf_v3 import data_access as DA
from nifty_trading.research.irf_v3.config import PDF1, PDF2, IrfV3Config
from nifty_trading.research.irf_v3.models import M1, M2
from nifty_trading.research.irf_v3.signal_engine import evaluate_session

DATA_END_TV = date(2026, 11, 4)

# id, method, pdf, page, image, kind, stated_date, A (level / Level A), B, entry, stop, target, stated outcome, stated gaps (entry-vs-level, stop dist, target dist)
EXAMPLES = [
    dict(id="M1-ILL", method="M1", pdf=PDF1, page=4, img="m1_p4_img1.png", kind="ILLUSTRATIVE_FIGURE", date=None, A=25035.0, B=None, entry=25030.0, stop=25070.0, target=24970.0, outcome="(illustration)",
         stated_stop_dist=40.0, stated_tp_dist=60.0, note="Page 3 table candle O25000 H25035 L24996 C25020 (green); level 25,035; entry 25,030 is 'an illustration'."),
    dict(id="M1-E1", method="M1", pdf=PDF1, page=6, img="m1_p6_img1.png", kind="SCREENSHOT", date=None, A=24391.80, B=None, entry=24373.25, stop=24408.50, target=24314.00, outcome="Stop-loss hit",
         stated_gap=18.55, stated_stop_dist=35.25, stated_tp_dist=59.25, note="Table row 'Session marked 5' - NO DATE in the rulebook."),
    dict(id="M1-E2", method="M1", pdf=PDF1, page=7, img="m1_p7_img1.png", kind="SCREENSHOT", date=date(2026, 11, 11), A=25377.5, B=None, entry=25363.90, stop=25404.65, target=25303.40, outcome="Target hit +60.50",
         stated_stop_dist=40.75, stated_tp_dist=60.50, note="Marked level 'about 25,377.5' (approximate); failure candle 'around 9:55 AM'."),
    dict(id="M1-E3", method="M1", pdf=PDF1, page=7, img="m1_p7_img2.png", kind="SCREENSHOT", date=date(2026, 11, 16), A=25301.55, B=None, entry=25299.75, stop=25340.45, target=25239.10, outcome="Target hit",
         stated_gap=1.80, stated_stop_dist=40.70, stated_tp_dist=60.65, note="Failure candle 'around 10:00 AM'. The screenshot axis shows '13 Nov 26' at its left edge."),
    dict(id="M2-ILL", method="M2", pdf=PDF2, page=4, img="m2_p4_img1.png", kind="ILLUSTRATIVE_FIGURE", date=None, A=25085.0, B=25094.0, entry=25090.0, stop=25130.0, target=25030.0, outcome="(illustration)",
         stated_stop_dist=40.0, stated_tp_dist=60.0, note="Page 3 table: first candle O25050 H25085 L25045 C25070; first red candle O25094 C25092; entry 25,090; stop 25,125-25,130."),
    dict(id="M2-E1", method="M2", pdf=PDF2, page=5, img="m2_p5_img1.png", kind="SCREENSHOT", date=None, A=25358.35, B=25379.95, entry=25376.25, stop=25412.10, target=None, outcome="Stop-loss hit (about 35 pts)",
         stated_gap=3.70, note="NO DATE in the rulebook; target not stated; second candle red BEFORE the breakout and ignored."),
    dict(id="M2-E2", method="M2", pdf=PDF2, page=6, img="m2_p6_img1.png", kind="SCREENSHOT", date=date(2026, 11, 12), A=25302.15, B=25350.30, entry=25337.95, stop=25373.15, target=25276.80, outcome="Target hit",
         stated_gap=12.35, stated_stop_dist=35.20, stated_tp_dist=61.15, note="Second candle red before the breakout: ignored."),
    dict(id="M2-E3", method="M2", pdf=PDF2, page=6, img="m2_p6_img2.png", kind="SCREENSHOT", date=date(2026, 11, 6), A=24540.05, B=24660.45, entry=24647.25, stop=24687.70, target=24586.15, outcome="Target hit",
         stated_gap=13.20, stated_stop_dist=40.45, stated_tp_dist=61.10, note="Continues on page 7."),
    dict(id="M2-E4", method="M2", pdf=PDF2, page=7, img="m2_p7_img1.png", kind="SCREENSHOT", date=date(2026, 11, 3), A=23611.15, B=23621.90, entry=23612.80, stop=23648.30, target=23552.55, outcome="Stop-loss hit (-35.50)",
         stated_gap=9.10, stated_stop_dist=35.50, stated_tp_dist=60.25, note="First candle red with a very long lower wick and a thin upper wick reaching Level A."),
]


def arithmetic_check(ex: dict) -> dict:
    """Do the numbers printed for the example agree with each other? (entry-vs-level gap, stop distance, target distance)."""
    ref = ex["B"] if ex["B"] is not None else ex["A"]
    out = {"entry_below_level": round(ref - ex["entry"], 2), "stop_distance": round(ex["stop"] - ex["entry"], 2), "target_distance": round(ex["entry"] - ex["target"], 2) if ex["target"] is not None else None}
    flags = []
    for key, stated in (("entry_below_level", ex.get("stated_gap")), ("stop_distance", ex.get("stated_stop_dist")), ("target_distance", ex.get("stated_tp_dist"))):
        if stated is not None and out[key] is not None and abs(out[key] - stated) > 0.011:
            flags.append(f"{key}: computed {out[key]} vs stated {stated}")
    out["internal_consistency"] = "CONSISTENT" if not flags else "; ".join(flags)
    return out


def _c(ts_i: int, o, h, lo, c):
    return (o, h, lo, c)


def synthetic_m1_figure() -> DA.Session:
    """Figure on page 4 (Method 1): first candle O25000 H25035 L24996 C25020; two green candles closing above 25,035; a red failure candle closing at 25,030; three red follow-through candles."""
    seq = [(25000, 25035, 24996, 25020), (25022, 25045, 25015, 25040), (25040, 25052, 25038, 25048), (25048, 25052, 25028, 25030), (25030, 25032, 25000, 25004), (25004, 25006, 24975, 24980),
           (24980, 24982, 24960, 24965)]
    return DA.synthetic_session(date(2000, 1, 3), seq)


def synthetic_m2_figure() -> DA.Session:
    """Figure on page 4 (Method 2): first candle O25050 H25085 L25045 C25070; green candle closing above Level A; two small green candles; the FIRST red candle O25094 C25092; a green candle closing above
    Level B; a green candle; a large red candle closing at 25,090 (< Level B = failure); follow-through reds."""
    seq = [(25050, 25085, 25045, 25070), (25072, 25090, 25068, 25088), (25088, 25092, 25086, 25091), (25091, 25095, 25090, 25093), (25094, 25096, 25091, 25092), (25092, 25102, 25091, 25100),
           (25100, 25104, 25098, 25102), (25102, 25104, 25088, 25090), (25090, 25092, 25070, 25072), (25072, 25074, 25050, 25055), (25055, 25056, 25025, 25028)]
    return DA.synthetic_session(date(2000, 1, 3), seq)


def candidate_search(tolerance: float = 1.0) -> dict:
    """For the UNDATED screenshots only: which sessions of the stores have a first-candle high within ``tolerance`` points of the stated level? Reported as information; NO date is ever adopted."""
    from nifty_trading.data import sessions as S
    from nifty_trading.research import phase4_data as D4

    frames = {"TV (2017-2026-11-04)": D4.load_processed_minutes(D4.SRC_TV_MIN), "5P window B": D4.load_processed_minutes(D4.SRC_5P_MIN), "5P window A": S.load_one_minute()}
    firsts = {}
    for name, m in frames.items():
        ts = m["timestamp"].dt.tz_localize(None) if m["timestamp"].dt.tz is not None else m["timestamp"]
        mm = ts.dt.hour * 60 + ts.dt.minute
        f = m.assign(_d=ts.dt.date)[(mm >= 555) & (mm < 560)]
        firsts[name] = f.groupby("_d")["high"].max()
    res = {}
    for ex in EXAMPLES:
        if ex["date"] is not None or ex["kind"] != "SCREENSHOT":
            continue
        hits = {}
        for name, s in firsts.items():
            h = s[(s - ex["A"]).abs() <= tolerance]
            hits[name] = [(str(d), round(float(v), 2)) for d, v in h.items()]
        verdicts = []
        tv_days = [date.fromisoformat(d) for d, _ in hits.get("TV (2017-2026-11-04)", [])]
        sess = DA.load_vendor_days(tv_days) if tv_days else {}
        for d, sx in sess.items():
            from nifty_trading.research.irf_v3.config import SCENARIOS

            ev = evaluate_session(sx, SCENARIOS["SL40_T60"], None)
            tr = ev.traces[M1 if ex["method"] == "M1" else M2]
            if tr.status != "SIGNAL":
                verdicts.append((str(d), f"NOT_SUPPORTED: the {ex['method']} engine finds no signal that day ({tr.no_signal_reason})"))
                continue
            lvl_ok = ex["B"] is None or abs(tr.reference_level - ex["B"]) <= 2.0
            ent_ok = abs(tr.confirmation_candle.close - ex["entry"]) <= 2.0
            verdicts.append((str(d), "SUPPORTED_BUT_NOT_ADOPTED" if (lvl_ok and ent_ok) else f"NOT_SUPPORTED: level {tr.reference_level:.2f}, failure close {tr.confirmation_candle.close:.2f} vs stated entry {ex['entry']}"))
        res[ex["id"]] = {"level": ex["A"], "tolerance": tolerance, "candidates": hits, "verdicts": verdicts}
    return res


def replay(ex: dict, cfg_sl35: IrfV3Config, cfg_sl40: IrfV3Config, tv_sessions: dict) -> dict:
    """Run the matching method on the example. Returns a record with status and the engine's facts."""
    rec = {"example": ex["id"], "pdf": ex["pdf"], "page": ex["page"], "kind": ex["kind"], "date_stated": str(ex["date"]) if ex["date"] else "NONE (undated; not assigned)", "method": ex["method"]}
    rec.update({f"arith_{k}": v for k, v in arithmetic_check(ex).items()})
    sess, vendor, status = None, "", ""
    if ex["kind"] == "ILLUSTRATIVE_FIGURE":
        sess = synthetic_m1_figure() if ex["method"] == "M1" else synthetic_m2_figure()
        vendor = "SYNTHETIC (figure-read candles carrying the printed numbers)"
    elif ex["date"] is None:
        status = "NOT_REPRODUCIBLE_UNDATED"
    elif ex["date"] > DATA_END_TV:
        status = f"DATA_UNAVAILABLE (secondary-vendor store ends {DATA_END_TV}; the primary 5paisa store ends 2026-08-31)"
    else:
        sess = tv_sessions.get(ex["date"])
        vendor = "TV (secondary vendor, the feed the screenshots come from)"
        if sess is None or not sess.evaluable:
            status = "DATA_UNAVAILABLE"
    if sess is None:
        rec.update({"status": status, "vendor": "", "replay_signal": "", "notes": ex["note"]})
        return rec
    m = M1 if ex["method"] == "M1" else M2
    res = {}
    for tag, cfg in (("SL35", cfg_sl35), ("SL40", cfg_sl40)):
        ev = evaluate_session(sess, cfg, None)
        res[tag] = ev
    ev = res["SL40"]
    tr = ev.traces[m]
    first = sess.candles[0]
    rec.update({"vendor": vendor, "replay_first_candle_ohlc": f"{first.open:.2f}/{first.high:.2f}/{first.low:.2f}/{first.close:.2f}", "replay_level_A": first.high,
                "level_A_diff_vs_source": round(first.high - ex["A"], 2), "replay_signal": tr.status})
    if tr.status == "SIGNAL":
        t40, t35 = res["SL40"].trades[m], res["SL35"].trades[m]
        rec.update({"replay_level_B": tr.reference_level if m == M2 else "", "level_B_diff_vs_source": round(tr.reference_level - ex["B"], 2) if (m == M2 and ex["B"]) else "",
                    "failure_candle": f"{tr.confirmation_candle.start:%H:%M}-{tr.confirmation_candle.end:%H:%M}", "failure_close": tr.confirmation_candle.close,
                    "replay_entry_next_open": t40.get("entry_price"), "entry_diff_vs_source_close_convention": round(tr.confirmation_candle.close - ex["entry"], 2),
                    "replay_SL35_exit": f'{t35.get("exit_reason")} {t35.get("gross_points")}' if t35 and t35.get("traded") else "", "replay_SL40_exit": f'{t40.get("exit_reason")} {t40.get("gross_points")}' if t40 and t40.get("traded") else "",
                    "replay_signal_time": f"{tr.signal_time:%H:%M}"})
    if ex["kind"] == "SCREENSHOT":
        near = min(sess.candles, key=lambda c: abs(c.close - ex["entry"]))
        rec["diag_candle_closing_nearest_source_entry"] = f"{near.start:%H:%M}-{near.end:%H:%M} close {near.close:.2f} (diff {near.close - ex['entry']:+.2f} vs source entry {ex['entry']})"
    rec["_ev"] = ev
    rec["_sess"] = sess
    return rec
