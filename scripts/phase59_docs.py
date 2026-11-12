"""Author-facing instructions, per-case annotation sheets and rule decisions."""

from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/phase5/phase59_orb_author_validation"

QUESTIONS = [
    {"id": "Q1", "topic": "Inner level and multi-session zone", "question": "Which exact resistance/support price or zone should the opening candle break? Mark its boundaries and establishing candles, say bodies/wicks/both, and define the current/previous/multi-session lookback and selection when several levels exist.", "source": "ORB PDF pp.4-7; reference bands pp.12-13", "current": "Latest non-strict k=2 previous-session inner pivot; a single price. Method 1 separately uses the previous day's wick extreme.", "candidate": "Existing nearest-inner/extreme-inner diagnostics only. No multi-session zone algorithm is attributed to the author."},
    {"id": "Q2", "topic": "Candle strength and colour", "question": "What makes an opening candle sufficiently strong? State whether a minimum body or maximum adverse wick is required, how a conditional pin qualifies, and confirm directional colour. Please mark an acceptable and unacceptable example rather than choosing a percentage to match the journal.", "source": "ORB PDF pp.3-7,9-10; handwritten p.5 green-long clarification", "current": "Body >=60% and opposite wick <=20%, or owner-style pin (wick >=2x body, favourable close30%). Gap rejection flag33%. Numbers are proposals.", "candidate": "Existing LOOSE50%/25% sensitivity and colour wrapper, both disabled. They do not establish the intended author rule."},
    {"id": "Q3", "topic": "Trendline anchors and qualification", "question": "When is a trendline required? Identify two or more exact candle anchors that were known before entry. Define pivot confirmation, permitted sessions, intervening price crossings, and whether price must break or remain on a side with a completed close.", "source": "ORB PDF pp.5-7", "current": "Last two confirmed previous-session k=2 lows/highs; projected in candle-index space. Rising/falling slope and opening-close side are mandatory.", "candidate": "Existing any-pair-of-last-three diagnostic only; relevant anchors must be supplied by the author."},
    {"id": "Q4", "topic": "Moving average and gap crossing", "question": "What exact average, timeframe and input do you use? Does 200 DMA mean a 200-day SMA or the average on a five-minute chart? Can the first candle open on one side and close on the other? Is a directional overnight gap/prior-close-side test mandatory, and is the average an entry condition or only a trend filter?",
     "source": "ORB PDF pp.2-3,5,7-9,12; gap figures differ from some wording", "current": "EMA200 of completed five-minute closes. Gap setup requires directional gap, prior official close on the old side, open already beyond current EMA and first close beyond.", "candidate": "Existing first-candle-crossing interpretation only. A generic EMA cross without the specified directional gap is not silently accepted."},
    {"id": "Q5", "topic": "Established trend", "question": "What evidence establishes trend before a Method 1/2 trade? Must it pre-exist in the previous session, can the opening move establish it, and what bullish/bearish structure is required in addition to the EMA location?", "source": "ORB PDF pp.1,3-7,12", "current": "Frozen research reference uses previous-session last5m close versus its EMA; no additional current-close/structure condition.", "candidate": "Existing current-close EMA diagnostic remains a basic proxy, not a complete source-defined trend."},
    {"id": "Q6", "topic": "Method, timestamp and rejection", "question": "For each marked trade, identify Method 1, Method 2, gap, or another method with its PDF page. Mark candle start/end, BUY/SELL, decision and intended execution time; confirm wick versus close and any second confirmation. What exact condition would make you ignore this ORB trade?", "source": "ORB PDF pp.1-3,11; handwritten ORB comments have no exact entry", "current": "Opening09:15-09:20 candle only; decision at09:20. Journal09:15 is a label, not proof of an executable09:15 fill.", "candidate": "No later-candle variant or guessed author entry is introduced."},
]


def read(name):
    with open(OUT / name, newline="") as f:
        return list(csv.DictReader(f))


def table(rows, keys):
    def cell(v):
        return str(v).replace("|", ";").replace("\n", " ")
    return "\n".join(["| " + " | ".join(keys) + " |", "|"+"---|"*len(keys)] + ["| "+" | ".join(cell(r.get(k,"")) for k in keys)+" |" for r in rows])


def annotation(case, priority=False):
    d = case["date"]
    return f"""# Author annotation sheet - {d}

Case {case['case_id']} | {'Priority' if priority else 'Supplementary handwritten'} review | Configuration A

AUTHOR ORB ENTRY — TO BE MARKED

The expected entry, direction and level are not recorded. Please mark the supplied chart; all response and approval fields below are deliberately blank. Existing orange/teal lines belong to the research engine, not to you.

Original comment: {case['author_original_comment'] or 'ORB label in manual journal; no exact entry is recorded.'}

## A. ORB method

[ ] Method 1   [ ] Method 2   [ ] Gap setup   [ ] Other method described in PDF

PDF page / other-method description: __________________________________________

## B. Entry candle

Exact candle start / end: ____________________   Direction BUY / SELL: __________

Decision / intended execution time: __________   Entry price, if known: __________

Why this candle qualifies: ___________________________________________________

____________________________________________________________________________

## C. Support or resistance

Exact level / zone lower and upper bounds: ___________________________________

Bodies, wicks or both: _______________________________________________________

Establishing candle dates and start times: ____________________________________

Current day / previous day / multiple sessions; lookback: _____________________

How to choose if several levels exist: _______________________________________

## D. Trendline

Required? __________   Exact anchor dates/times and prices: ____________________

____________________________________________________________________________

Break the line, or remain above/below it? _____________________________________

Must a completed candle close confirm? _______________________________________

## E. Candle confirmation

Required green/red colour: __________   Minimum body / maximum wick: __________

Close beyond the level required? __________   Wick break sufficient? __________

Second confirmation candle required? __________   Pin-bar rule: _______________

## F. Moving average

Name, period, input, timeframe: ______________________________________________

200-day SMA or average on five-minute chart? __________________________________

Can a candle open one side and close the other? _______________________________

Entry condition or trend filter? __________   Directional gap required? _______

## G. Trade rejection and approval

What exact condition would make you ignore this ORB trade?

____________________________________________________________________________

____________________________________________________________________________

Confirm this trade? __________   Evidence supports a general rule? ____________

Engineering implementation approved? __________   Reviewer / date: ____________

Approval of one drawing is not automatic approval of a mechanical rule for all dates.
"""


def main():
    baseline = json.loads((OUT / "baseline_recount.json").read_text())
    priorities = json.loads((OUT / "priority_cases.json").read_text())
    payload = json.loads((OUT / "case_data.json").read_text())
    all_cases = [v["case"] for v in payload.values()]
    coverage = read("question_coverage.csv")
    (OUT / "questions.json").write_text(json.dumps(QUESTIONS, indent=2))
    priority_rows = [{"date": x["date"], "topic": x["topic"], "selection reason": x["why"], "source pages": x["source_pages"]} for x in priorities]
    (OUT / "five_priority_cases.md").write_text("# Five priority disputed dates\n\nSelection was made by distinct qualification mechanisms and source-definition uncertainty, before reading any hypothetical outcome. Existing ledger profit/outcome fields are not used to select cases.\n\n" + table(priority_rows,["date","topic","selection reason","source pages"]) + "\n\nNo handwritten dispute is newly qualified by the isolated gap-candle interpretation. The gap representative is an explicit negative control, 2025-12-05. The already-required missing-journal date2026-07-15 supplies a separate candle-crossing contrast; it is not labelled a handwritten dispute or a sixth priority case.\n\nEach priority date has a full-session5m chart, first-hour1m detail, five-session context and a complete author-response sheet in priority_five/. All six method/direction paths and additional failures are preserved in daily/ and gate_evidence.csv.\n")
    guide = ["# Six grouped author questions", "", "Start with the five priority cases, then apply the same answers to related dates. Do not ask fifty copies of the same question. The author must still mark each claimed entry where direction/level is missing.", "",
             "Coverage below counts dates with a reached engine rejection in that family, plus dates where it is the sole failed gate on at least one diagnostic path. These sets overlap, and author method/direction are unknown; they are not a promise that an answer will validate that many trades. Q1 is foundational despite only two sole-inner-gate cases. Q2 and Q3 have22 and8 sole-gate cases respectively. Q6 records missing evidence for all cases. No profit or journal-agreement optimization was used.", ""]
    for q in QUESTIONS:
        c = next(c for c in coverage if c["question"] == q["id"])
        guide += [f"## {q['id']}. {q['topic']}", "", q["question"], "", f"Source: {q['source']}", "", f"Current code: {q['current']}", "", f"Diagnostic coverage: {c['reached_gate_date_coverage']} reached-rejection dates among the50 missing dates; {len(json.loads(c['sole_failed_gate_dates']))} sole-gate dates. Q6 means missing method/time evidence, not a time-filter failure.", "", "Related dates: "+", ".join(json.loads(c["sole_failed_gate_dates"])) if json.loads(c["sole_failed_gate_dates"]) else "No unique sole-gate attribution; retain the full per-date evidence.", ""]
    guide += ["## Interview order", "", "1. Have the author draw the intended entry, level and method on each priority chart, without showing candidate outcome claims.", "2. Ask Q1 and Q6 first to identify what setup is being discussed; then Q2/Q3 for mechanical definitions and Q4/Q5 for indicator/trend interpretation.", "3. Record exceptions and rejection conditions; apply a proposed general definition to all affected charts for review, not automatic activation.", "4. Obtain separate source-evidence and engineering approval. Leave disputed answers unresolved rather than choosing the rule that matches more journal dates."]
    (OUT / "author_interview_questions.md").write_text("\n".join(guide)+"\n")
    decision = [{"question": q["id"], "rule family": q["topic"], "source": q["source"], "current implementation": q["current"], "candidate alternative": q["candidate"], "decision": "PENDING AUTHOR RESPONSE; NO ACTIVE CHANGE"} for q in QUESTIONS]
    (OUT / "rule_decision_matrix.md").write_text("# Rule decisions remain open\n\n"+table(decision,["question","rule family","source","current implementation","candidate alternative","decision"])+"\n\nA date label is not proof of a valid entry. No proposed rule is selected by outcome or agreement count. Source support, author trade confirmation and engineering approval are separate fields in the workbook, all left blank.\n")
    template_case = {"date":"________________", "case_id":"________________", "author_original_comment":""}
    (OUT / "author_response_template.md").write_text(annotation(template_case))
    for d, p in payload.items():
        case = p["case"]
        if case["handwritten_dispute"]:
            folder = "priority_five" if case["priority"] else "remaining_eight"
            (OUT / folder / f"{d}_author_sheet.md").write_text(annotation(case, case["priority"]))
        daily = [f"# {d} - author validation", "", f"Case {case['case_id']}. Frozen configuration A. Author entry, direction and level UNKNOWN.", "",
                 f"[Overview chart](../author_review_charts/{d}_overview.png) | [SVG](../author_review_charts/{d}_overview.svg)",
                 f"Original journal rows: {case['journal_sheet_rows']}; labels as written: {case['journal_time_labels']}; strategies: {case['journal_strategy_as_written']}",
                 f"Handwritten reference: {case['handwritten_reference'] or 'None'}", f"Original comment: {case['author_original_comment'] or 'None'}", "",
                 "## All method/direction predicates", ""]
        for path in p["paths"]:
            daily += [f"### {path['direction']} {path['method']}", "", f"Reference level {path['level']}; first failure {path['first_failure']}. Signed close distance {path['signed_breakout_distance']}.", "",
                      table(path["gates"],["predicate","passed","reached_in_code","observed","source","authority"]), ""]
        daily += ["## Existing portfolio ledger", "", table(p["trades"],["trade_id","strategy","method","direction","signal_time","entry_time","entry","stop","t1","t2","exits"]), "",
                  "## Disabled diagnostic candidates", "", json.dumps(case["candidate_alternatives"], indent=2), "",
                  "## Author evidence needed", "", ", ".join(case["author_clarifications_required"])+". Exact author entry remains blank; no rule is approved."]
        (OUT / "daily" / f"{d}.md").write_text("\n".join(daily)+"\n")
    wrapper = json.loads((OUT / "optional_wrapper_probe.json").read_text())
    (OUT / "optional_wrapper_defect_review.md").write_text("""# Optional colour-wrapper metadata defect

The defect is reproducible: `orb_colour.py:35-39` changes a red-long pin record from CONFIRMED to INVALIDATED, but leaves execution-config confirmation labels and verification metadata unchanged. Its appended trace also uses candle-start09:15 instead of confirmation09:20. The probe in optional_wrapper_probe.json preserves the actual fields.

| Concern | Finding |
|---|---|
| Strategy identity | `strategy` remains ORB. The defect does not relabel ORB as IRF. |
| Candidate/config selection | A/B use ORBStrategy; C uses ORBCandidateStrategy. None uses ORBColourStrategy. Factory selection is explicit, not inferred from stale metadata. |
| Signal selection | `selection.is_valid` rejects INVALIDATED before reading executable metadata. No false trade results from the stale label in the tested path. |
| Signal tracing | The optional wrapper contains stale inherited confirmation information and a wrong start-time label; a consumer relying on metadata alone could mislabel a rejected record. This is a real maintenance defect. |
| Phase5.9 chart/report labels | Derived from canonical `signal_status`, actual A ledger and fresh frozen-engine outputs. No optional-wrapper record is displayed as confirmed. |
| Manual comparison | Phase5.6/5.8 signal counts use signal_status; A/B/C execution ledgers do not use the colour wrapper. The35/50/34 baseline is unaffected. |

No active or wrapper source was fixed: the defect is isolated from this package's charts and counts. A future metadata-only maintenance patch should rebuild status metadata, stamp the confirmation end and rederive concurrency labels. Phase5.8's strict expected-failure test remains present and is explicitly reported, not hidden. Author-rule activation remains out of scope.

Actual engine classes and rejected-record values:

```json
"""+json.dumps(wrapper,indent=2)+"\n```\n")
    # Human-friendly indices without invented marker coordinates.
    for folder, cases in (("priority_five",[c for c in all_cases if c["priority"]]),("remaining_eight",[c for c in all_cases if c["handwritten_dispute"] and not c["priority"]]),("all_missing_orb",[c for c in all_cases if c["missing_journal_orb"]])):
        (OUT / folder / "README.md").write_text(f"# {folder.replace('_',' ').title()}\n\n"+"\n".join(f"- [{c['date']}]({c['date']}_overview.png) - {c['selected_portfolio_strategy']}; author entry unknown" for c in cases)+"\n")
    (OUT / "README.md").write_text(f"""# Phase 5.9 - ORB author chart validation

This is an annotation package, not a new strategy or profitability study. Frozen configuration A is used consistently because the requested35/50/34 baseline belongs to that configuration. Current engine reference lines are labelled provisional; author entries and approvals remain blank.

## Reproduced baseline

Original workbook: **{baseline['journal_rows']} data rows**, **{baseline['orb_journal_rows']} ORB rows on {baseline['orb_unique_dates']} unique dates**. Of these, **85 dates are evaluable:35 generated/executed ORB and50 generated no ORB**. IRF executed on34 ORB-labelled dates; none had a confirmed earlier ORB.

The13 handwritten dates overlap the50 missing-signal dates on11 dates. The union is **52 unique cases**, all charted. 2025-10-17 has no journal row; 2025-11-21 has an IRF journal label, so both remain handwritten-only ORB observations. Four literal ORB Saturday dates are retained in the recount and excluded from the50 evaluable missing dates.

Within the50 dates,34 have IRF,5 have another strategy and12 have no trade. These counts overlap:2025-11-07 contains IRF followed by PDS. They are not a partition. No original journal date, time label or classification was changed.

## Five priority cases

{table(priority_rows,['date','topic','selection reason'])}

The gap case is deliberately a negative control: none of the13 handwritten disputes gains a signal from candle-crossing alone. The separate existing missing-journal case2026-07-15 demonstrates that source conflict without inventing a handwritten dispute.

## Author workflow and outputs

1. Open `ORB_Author_Review_Package.pdf`: it contains the five priority overviews, one-minute details, prior-session context and a question sheet for each; all eight remaining handwritten charts; a gap contrast and all50 missing-date records in summary.
2. Draw the intended level/zone, entry candle and direction. Use the blank area marked **AUTHOR ORB ENTRY — TO BE MARKED**. No label is placed at a guessed price or timestamp.
3. Enter general definitions and case-specific responses in `ORB_Author_Review.xlsx`, which has one row per unique case and blank author response/approval columns. `author_response_template.md` provides a printable alternative.
4. Use the six grouped questions in `author_interview_questions.md`. A marked trade, source support and engineering approval are separate decisions. No rule activates automatically.

The package includes **52 overview charts plus10 priority detail/context charts**, as SVG and3400-pixel PNG files at300 DPI. `priority_five/`, `remaining_eight/` and `all_missing_orb/` contain explicit subsets. The50 missing dates and34 IRF dates have dedicated CSVs. Every path failure, including hidden later failures, is preserved in `gate_evidence.csv` and `daily/`. `source_to_chart_traceability.csv` maps all62 charts to original data, source pages and actual ledger IDs.

Chart prices and markers are read from actual one-minute data and existing Phase5.5 ledger A. Original SL, T1/T2 and exits are shown only for existing simulated trades. Target-gap fills may be conservative model levels outside that minute's range; they are not represented as observed brokerage fills. No hypothetical ORB price, stop, target or exit is drawn.

## Findings and limits

The engine's unbroken previous-day extreme is a source-supported Method1 exclusion, not proof that Method2 is impossible. Its latest-fractal inner level, last-two-pivot line, numerical body/wick thresholds and prior-session trend are mechanical assumptions. The source's gap drawings and some wording conflict. The author must define exact levels, anchors, colour/strength, average/timeframe, crossing, trend and entry timing before a general correction can be implemented.

The optional colour-wrapper metadata defect is reproduced and documented separately. It does not affect A/B/C strategy identity, actual ledger selection, this package's labels or the verified manual counts. No fix to active behaviour was necessary.

## Verification and scope

Fresh recount, independent1m-to5m aggregation, currentORB/predicate parity and IRF signal/raw-fill checks were performed before accepting Phase5.8 as an input. `independent_audit.md` records chart-to-candle, ledger, original-file, PDF and workbook checks, test results and the required fresh read-only reviewer findings. Author confirmation remains necessary even after technical review.

No five-strategy implementation, stop, target, controller, data or previous report was modified. Phase5.7 was read as a visual reference and never written. No candidate profitability backtest, parameter search, live/paper order, commit or push was made. The full pytest suite includes existing baseline historical-regression tests as explicitly requested.

## Reproduction

```sh
.venv/bin/python scripts/phase59_snapshot.py  # once only; refuses to replace the original snapshot
.venv/bin/python scripts/phase59_run.py
.venv/bin/python scripts/phase59_charts.py
node reports/phase5/phase59_orb_author_validation/render_charts.mjs
.venv/bin/python scripts/phase59_docs.py
```

Author responses are not available. Stop here until the author returns the annotated charts; do not implement or backtest a new rule from this package.
""")
    print("Author questions, decisions,52 daily explanations and13 response sheets written")


if __name__ == "__main__":
    main()
