"""Read back every packet page, compare embedded charts and render all pages."""

import hashlib
import json
from pathlib import Path

import pdfplumber
import pypdfium2 as pdfium
from PIL import Image, ImageChops
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"reports/phase5/phase59_orb_author_validation"


def main():
    path=OUT/"ORB_Author_Review_Package.pdf"
    manifest=json.loads((OUT/"pdf_pages.json").read_text())
    reader=PdfReader(path)
    comparisons=[]
    for meta,page in zip(manifest,reader.pages,strict=True):
        if meta["kind"] in ("overview","opening_1m","history_5m"):
            source=OUT/"author_review_charts"/f'{meta["date"]}_{meta["kind"]}.png'
            expected=Image.open(source).convert("RGB")
            actual=page.images[0].image.convert("RGB")
            equal=actual.size==expected.size and ImageChops.difference(actual,expected).getbbox() is None
            comparisons.append({"page":meta["page"],"date":meta["date"],"kind":meta["kind"],"pixels_match_current_png":equal,"width_pixels":actual.width,"height_pixels":actual.height})
    if any(not r["pixels_match_current_png"] for r in comparisons):
        raise AssertionError({"embedded_png_drift":[r for r in comparisons if not r["pixels_match_current_png"]]})
    out=OUT/"pdf_review"
    out.mkdir(exist_ok=True)
    pdf=pdfium.PdfDocument(str(path))
    thumbs=[]
    for i in range(len(pdf)):
        page=pdf[i]
        img=page.render(scale=1.4).to_pil().convert("RGB")
        img.save(out/f"page_{i+1:02}.png")
        thumb=img.copy()
        thumb.thumbnail((300,420))
        thumbs.append(thumb)
        page.close()
    pdf.close()
    sheet=Image.new("RGB",(1200,((len(thumbs)+3)//4)*440),"#E4E8EC")
    for i,img in enumerate(thumbs):
        sheet.paste(img,((i%4)*300, (i//4)*440))
    sheet.save(out/"contact_all_pages.png")
    outside=[]
    with pdfplumber.open(path) as document:
        for i,page in enumerate(document.pages,1):
            for ch in page.chars:
                if ch["x0"] < 0 or ch["x1"] > page.width+.2 or ch["top"] < 0 or ch["bottom"] > page.height+.2:
                    outside.append({"page":i,"text":ch["text"],"x0":ch["x0"],"x1":ch["x1"]})
    result={"pages":len(reader.pages),"manifest_pages":len(manifest),"embedded_chart_pages":len(comparisons),"embedded_charts_match_latest_pngs":all(r["pixels_match_current_png"] for r in comparisons),"comparisons":comparisons,"text_outside_page":outside,"sha256":hashlib.sha256(path.read_bytes()).hexdigest()}
    (OUT/"pdf_quality_checks.json").write_text(json.dumps(result,indent=2))
    if len(reader.pages)!=34 or outside:
        raise AssertionError(result)
    print(f"PDF QA passed: {len(reader.pages)} pages, {len(comparisons)} exact embedded chart matches, no text outside page")


if __name__=="__main__":
    main()
