"""Prepare source-linked workbook matrices; author responses remain null."""

import csv
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"reports/phase5/phase59_orb_author_validation"


def rows(path):
    with open(path,newline="") as f:
        return list(csv.DictReader(f))


def main():
    payload=json.loads((OUT/"case_data.json").read_text())
    cases=[x["case"] for x in payload.values()]
    baseline=json.loads((OUT/"baseline_recount.json").read_text())
    questions=json.loads((OUT/"questions.json").read_text())
    prior=rows(ROOT/"reports/phase5/phase58_codex_orb_forensic_audit/orb_all_manual_journal_dates.csv")
    prior={x["date"]:x for x in prior if x["config"]=="A"}
    raw=rows(OUT/"journal_recount_rows.csv")
    evidence=[]
    for r in raw:
        scope=prior.get(r["date"])
        evidence.append([int(r["sheet_row"]),r["date"],r["time_label"],r["strategy_as_written"],
                         int(scope["session_status"].startswith("USABLE")) if scope else None,
                         int(scope["orb_signal"]=="True") if scope else None,
                         int(scope["orb_executed"]=="True") if scope else None,
                         int(scope["irf_executed"]=="True") if scope else None])
    matrix=[]
    for c in cases:
        fail=" | ".join(k+": "+", ".join(v) for k,v in c["all_failed_conditions"].items())
        candidate=" | ".join(f'{x["variant"]}: {x["method"]} {x["direction"]} @09:20; reference {x["level"]:.2f}; DISABLED' for x in c["candidate_alternatives"]) or "No isolated Phase5.8 candidate qualifies; author setup still unknown"
        matrix.append([c["case_id"],c["date"],c["priority_topic"] or ("Other handwritten" if c["handwritten_dispute"] else "Missing journal ORB"),
                       c["author_reviewed_method"],c["author_reviewed_direction"],c["author_reviewed_entry_time"],c["author_reviewed_entry_price"],
                       c["author_reviewed_support_resistance"],c["author_explanation"],c["author_confirms_trade"],c["source_supports_general_rule"],c["engineering_implementation_approved"],
                       ", ".join(str(x) for x in c["journal_sheet_rows"]),c["handwritten_reference"],c["current_orb_result"],c["selected_portfolio_strategy"],
                       fail,c["source_pdf_pages"],"Frozen A: previous extreme; latest k2 inner; last-two pivot line; prior EMA trend; proposed60%/20% or pin;09:20 only",
                       candidate,"UNKNOWN - not recorded","UNKNOWN - not recorded",c["chart"],"; ".join(c["journal_time_labels"]),
                       int(c["missing_journal_orb"]),int(c["handwritten_dispute"]),int(c["priority"])])
    irf=rows(OUT/"orb_vs_irf_34_dates.csv")
    sheets=[
        {"name":"Overview","title":"ORB author review | Phase 5.9","subtitle":"Configuration A | One row per unique case | Blank author cells do not imply approval",
         "headers":["Verified baseline / workflow","Value"],"rows":[["Original journal data rows",190],["ORB journal rows",89],["Unique ORB dates (independently counted)",89],["Evaluable ORB journal dates",85],["ORB signal dates",35],["ORB executed dates",35],["Missing ORB-signal dates",50],["Journal ORB dates executing IRF",34],["Handwritten disputes",13],["Unique review cases",52],["Priority cases",5]],
         "widths":[58,22]},
        {"name":"CaseReview","title":"Case decisions and author responses","subtitle":"Amber columns D:L are deliberately blank for the author. Expected entries are UNKNOWN. No response activates trading logic.",
         "headers":["Case ID","Date","Review focus","Author method","Author direction","Author candle / entry time","Author entry price","Author level / zone","Author explanation","Author confirms trade","Source supports general rule","Engineering implementation approved","Original journal sheet row","Handwritten correction reference","Current ORB result","Actual portfolio strategy","All failed paths","Source PDF pages","Current implementation","Disabled candidate alternative","Expected ORB direction","Expected entry candle","Chart path","Journal time label as written","Missing journal case","Handwritten case","Priority case"],
         "rows":matrix,"widths":[20,16,45,23,20,32,20,65,80,24,28,32,24,55,32,27,135,75,100,110,35,35,65,28,22,22,22],
         "dateColumns":[1],"numericColumns":[24,25,26],"inputRange":"D5:L56"},
        {"name":"OriginalJournal","title":"Original journal source rows","subtitle":"Source: docs/trading journal/Trading_Journal_Sep2025_Aug2026 REPORT.xlsx, Trading Journal. No dates or strategy labels corrected. Flags apply to ORB-journal scope only.",
         "headers":["Original sheet row","Date as written","Time label as written","Strategy as written","ORB-scope evaluable","ORB signal on date","ORB executed on date","IRF executed on date"],
         "rows":evidence,"widths":[23,18,27,26,26,26,27,27],"dateColumns":[1],"numericColumns":[0,4,5,6,7]},
        {"name":"IRFExecutions","title":"All 34 ORB-journal dates executing IRF","subtitle":"Source: existing Phase5.5 A ledger; all entries and exits preserved. These are model fills, not author-expected ORB entries.",
         "headers":["Date","Method","Signal time","Entry time","Entry","Original SL","Target 1","Target 2","Leg1 exit time","Leg1 exit price","Leg2 exit time","Leg2 exit price","ORB result","Disabled candidates"],
         "rows":[[r["date"],r["method"],r["signal_time"],r["entry_time"],*[float(r[k]) for k in ("entry_price","initial_stop","target_1","target_2")],r["leg1_exit_time"],float(r["leg1_exit_price"]),r["leg2_exit_time"],float(r["leg2_exit_price"]),"No confirmed earlier ORB",r["hypothetical_candidates"]] for r in irf],
         "widths":[16,23,28,28,20,20,20,20,23,24,23,24,40,110],"dateColumns":[0]},
        {"name":"RuleQuestions","title":"Six general questions to answer once","subtitle":"General author definitions, source support and engineering approval are separate blank inputs. See author_interview_questions.md for coverage and related dates.",
         "headers":["Question","Rule family","Exact question","Source page / reference","Current implementation","Disabled alternative","Author general definition","Source supported?","Engineering approved?"],
         "rows":[[q["id"],q["topic"],q["question"],q["source"],q["current"],q["candidate"],None,None,None] for q in questions],
         "widths":[15,45,110,80,110,110,110,25,30],"inputRange":"G5:I10"},
    ]
    (OUT/"workbook_data.json").write_text(json.dumps({"sheets":sheets,"baseline":baseline},indent=2))
    print("Prepared5-sheet workbook;52 case rows,190 original rows,34 IRF executions,6 grouped questions")


if __name__=="__main__":
    main()
