"""Create the print-ready author packet with the bundled ReportLab runtime."""

from __future__ import annotations

import csv
import json
from html import escape
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Table, TableStyle

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/phase5/phase59_orb_author_validation"
NAVY = colors.HexColor("#183149")
GREY = colors.HexColor("#5E6A75")
STYLE = ParagraphStyle("Body", fontName="Helvetica", fontSize=10, leading=14, textColor=NAVY)
SMALL = ParagraphStyle("Small", parent=STYLE, fontSize=9, leading=12)


def main():
    data = json.loads((OUT / "case_data.json").read_text())
    priority = json.loads((OUT / "priority_cases.json").read_text())
    questions = json.loads((OUT / "questions.json").read_text())
    with open(OUT / "all_50_missing_orb_dates.csv", newline="") as f:
        missing = list(csv.DictReader(f))
    path = OUT / "ORB_Author_Review_Package.pdf"
    pdf = canvas.Canvas(str(path), pagesize=A4, pageCompression=1)
    pdf.setTitle("ORB Author Review Package - Phase5.9")
    pdf.setAuthor("Independent ORB research review")
    manifest = []
    page_width, page_height = A4

    def start(title, subtitle="", wide=False, kind="text", date=None):
        nonlocal page_width, page_height
        page_width, page_height = landscape(A4) if wide else A4
        pdf.setPageSize((page_width,page_height))
        pdf.setFillColor(NAVY)
        pdf.setFont("Helvetica-Bold",18 if not wide else 14)
        pdf.drawString(34,page_height-37,title)
        pdf.setFillColor(GREY)
        pdf.setFont("Helvetica",9)
        pdf.drawString(34,page_height-54,subtitle)
        pdf.setStrokeColor(colors.HexColor("#D9E0E7"))
        pdf.line(34,page_height-64,page_width-34,page_height-64)
        manifest.append({"page":len(manifest)+1,"kind":kind,"date":date,"title":title,"width":page_width,"height":page_height})
        return page_height-84

    def end():
        pdf.setFillColor(GREY)
        pdf.setFont("Helvetica",8)
        pdf.drawString(34,18,"Phase 5.9 | Author annotation required | No rule activated | Times IST")
        pdf.drawRightString(page_width-34,18,str(len(manifest)))
        pdf.showPage()

    def paragraph(value,y,width=None,style=STYLE,max_height=None):
        width = page_width-68 if width is None else width
        item=Paragraph(value,style)
        _, height=item.wrap(width,1000)
        if max_height is not None and height>max_height:
            raise ValueError((manifest[-1],"Text exceeds reserved height",height,max_height))
        if y-height<35:
            raise ValueError((manifest[-1],"Text runs below footer",y,height))
        item.drawOn(pdf,34,y-height)
        return y-height-11

    y=start("ORB author review package","Phase5.9 | NIFTY50 | 8 November2026 | Frozen configuration A")
    y=paragraph("<b>Purpose.</b> Please draw the ORB entries and levels you intended, then define the rules behind them. The package shows what the current algorithm recognizes and rejects. It does not establish that every journal label should become a trade.",y)
    y=paragraph("<b>No invented author entry.</b> All expected author prices, directions and exact candles remain unknown. The box labelled <b>AUTHOR ORB ENTRY — TO BE MARKED</b> is outside the price/time plot. Orange/teal reference lines are research-engine constructions, not lines attributed to you.",y)
    metrics=[["Independently recounted evidence","Count"],["Original journal data rows","190"],["ORB-labelled rows / unique dates","89 /89"],["Evaluable ORB journal dates","85"],["Dates generating and executing frozen ORB","35"],["Evaluable dates with no ORB signal","50"],["ORB-journal dates with an IRF execution","34"],["Handwritten ORB disputed observations","13"],["Unique author-review cases (overlap removed)","52"]]
    tab=Table(metrics,colWidths=[page_width-138,70],rowHeights=24)
    tab.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),NAVY),("TEXTCOLOR",(0,0),(-1,0),colors.white),("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTNAME",(0,1),(-1,-1),"Helvetica"),("FONTSIZE",(0,0),(-1,-1),10),("ALIGN",(1,1),(1,-1),"RIGHT"),("VALIGN",(0,0),(-1,-1),"MIDDLE"),("LINEBELOW",(0,0),(-1,0),.7,colors.white),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.HexColor("#F2F5F8"),colors.white])]))
    _,th=tab.wrap(page_width-68,600)
    tab.drawOn(pdf,34,y-th)
    y-=th+20
    y=paragraph("<b>Counts overlap.</b> Eleven handwritten dates belong to the50 missing-signal dates. Two more handwritten observations are outside the ORB journal labels. Among the50 missing dates,34 have IRF,5 another strategy and12 no trade; one day has IRF then PDS. Four literal ORB Saturday dates have no evaluable session and are not silently corrected.",y)
    y=paragraph("<b>How to use this packet.</b> Start with the five priority cases. Each has a five-minute overview, opening one-minute detail, prior-five-session context and a question sheet. Review the remaining eight handwritten charts, the separate gap contrast and the full50-date summary. The workbook has one row per unique case, with author response and approval fields blank.",y)
    paragraph("The existing controller did not bypass an earlier confirmed frozen ORB. That result does not prove strategy fidelity. No new rule or candidate profitability backtest is authorized by this packet.",y)
    end()
    y=start("Six grouped questions","Answer once as a general definition, then mark case-specific exceptions.")
    for q in questions:
        y=paragraph(f"<b>{q['id']}. {escape(q['topic'])}</b><br/>{escape(q['question'])}",y)
        y=paragraph("Source: "+escape(q["source"]),y,style=SMALL)
    paragraph("Trade confirmation, source support for a general rule and engineering implementation approval are separate decisions. Leave unresolved responses blank. An author-marked earlier entry would still need a causal rule check and the original portfolio collision/state rules.",y,style=SMALL)
    end()

    def chart_page(date,kind,section):
        name={"overview":"Five-minute overview","opening_1m":"Opening one-minute detail","history_5m":"Five-session level context"}[kind]
        start(f"{section}: {date} | {name}","Configuration A | Actual candles and existing simulated ledger | Author entry remains unknown",True,kind,date)
        # Exact aspect ratio; at 3400 pixels this exceeds300dpi at the printed width.
        image=OUT/"author_review_charts"/f"{date}_{kind}.png"
        iw=page_width-50
        ih=iw*1250/2000
        pdf.drawImage(str(image),25,30,width=iw,height=ih,preserveAspectRatio=True,mask="auto")
        end()

    def form(date,case,generic=False):
        y=start("Author response - "+date,"Mark the chart and record exact candle/level evidence. All responses are blank.",kind="author_sheet",date=None if generic else date)
        if case.get("author_original_comment"):
            y=paragraph("Original comment: "+escape(case["author_original_comment"]),y,style=SMALL,max_height=42)
        y=paragraph("AUTHOR ORB ENTRY — TO BE MARKED. Do not treat the engine's current lines as your own intended levels.",y,style=SMALL)
        blocks=[
            ("A. Method", "Method 1 / Method 2 / Gap / Other described in PDF; identify the PDF page.",47,1),
            ("B. Entry candle", "Exact candle start/end; BUY or SELL; decision/execution time; entry price if known; why this candle qualifies.",76,2),
            ("C. Support / resistance", "Exact price or zone boundaries; bodies/wicks/both; establishing candle dates/times; current/previous/multiple sessions; level selection.",96,3),
            ("D. Trendline", "Required? Exact anchor candles/prices; break or hold a side; completed close required; any prohibited intervening crossing.",84,2),
            ("E. Candle confirmation", "Required colour; minimum body / maximum wick; close beyond versus wick break; second confirmation; conditional pin rule.",84,2),
            ("F. Moving average", "Indicator name/period/input/timeframe;200-day SMA versus5m average; may open one side and close the other; entry gate or trend filter?",84,2),
            ("G. Rejection / approvals", "What exact condition would make you ignore this ORB trade? Separately record trade confirmation, source support and engineering approval.",92,3),
        ]
        for heading,prompt,height,lines in blocks:
            if y-height<35:
                raise ValueError((date,"Form overflow",heading,y,height))
            pdf.setFont("Helvetica-Bold",10)
            pdf.setFillColor(NAVY)
            pdf.drawString(34,y,heading)
            paragraph(escape(prompt),y-7,style=SMALL,max_height=27)
            pdf.setStrokeColor(colors.HexColor("#C7CDD3"))
            for i in range(lines):
                yy=y-height+10+i*13
                pdf.line(34,yy,page_width-34,yy)
            y-=height
        end()

    for i,p in enumerate(priority,1):
        d=p["date"]
        for kind in ("overview","opening_1m","history_5m"):
            chart_page(d,kind,f"Priority{i}")
        form(d,data[d]["case"])
    rest=[d for d,p in data.items() if p["case"]["handwritten_dispute"] and not p["case"]["priority"]]
    for d in rest:
        chart_page(d,"overview","Remaining handwritten case")
    chart_page("2026-07-15","overview","Separate missing-journal gap contrast (not handwritten)")
    code={"previous_level_close":"PD","inner_defined":"ID","inner_close":"IN","trend":"TR","trendline":"TL","quality":"Q","near_ma":"NEAR","gap_direction":"GDIR","ma_available":"WARM","gap_crossing":"CROSS","ma_close":"CLOSE","gap_cap":"CAP"}
    for part in range(2):
        y=start(f"All50 missing ORB dates - {part+1}/2","First failed gate per LONG/SHORT path; complete additional failures are in CSV/workbook/daily records.")
        matrix=[["Date","Row","M1 L/S","M2 L/S","Gap L/S","Portfolio A","Author entry"]]
        for row in missing[part*25:(part+1)*25]:
            first=json.loads(row["first_failing_conditions"])
            verdict=[]
            for method in ("Method 1","Method 2","Gap/200DMA"):
                verdict.append(" / ".join(code.get(first[f"{direction} {method}"],first[f"{direction} {method}"]) for direction in ("LONG","SHORT")))
            matrix.append([row["date"],",".join(str(x) for x in json.loads(row["orb_journal_sheet_rows"])),*verdict,row["selected_portfolio_strategy"],"UNKNOWN"])
        widths=[72,44,72,72,82,82,103]
        tab=Table(matrix,colWidths=widths,rowHeights=22)
        tab.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),NAVY),("TEXTCOLOR",(0,0),(-1,0),colors.white),("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTNAME",(0,1),(-1,-1),"Helvetica"),("FONTSIZE",(0,0),(-1,-1),8),("VALIGN",(0,0),(-1,-1),"MIDDLE"),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.HexColor("#F2F5F8"),colors.white])]))
        _,height=tab.wrap(page_width-68,700)
        tab.drawOn(pdf,34,y-height)
        y-=height+18
        y=paragraph("PD previous-day close break; IN inner close break; ID no inner level; TR trend; TL trendline; Q shape; GDIR gap direction; CROSS MA crossing; CLOSE close beyond MA; NEAR near-MA close; WARM indicator available; CAP extension cap. L/S paths are diagnostics, not the author's unknown direction.",y,style=SMALL)
        paragraph("Every date has an overview chart in all_missing_orb/. An ORB label is not proof that the strategy should trade. No author's expected entry is known or plotted.",y,style=SMALL)
        end()
    form("________________",{},True)
    pdf.save()
    (OUT/"pdf_pages.json").write_text(json.dumps(manifest,indent=2))
    print(f"Created {path.name}: {len(manifest)} pages")


if __name__ == "__main__":
    main()
