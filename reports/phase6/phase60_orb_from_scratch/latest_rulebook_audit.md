# Audit of the latest rulebook

* File: `docs/strategy_docs/Nifty_920_ORB_Rulebook (2) (1).docx` (SHA-256 `8504fb6fca64a7e168928826970e1735b1aab14d6b2c4c6b3cf567282aac75a7`). The prompt names `Nifty_920_ORB_Rulebook (2).docx`; that file is only in `~/Downloads`, and its bytes are identical to the repository copy `(2) (1).docx` (and to a second Downloads copy), so the repository copy was used. It is untracked in git.
* Read: every paragraph, every table (8 tables incl. the rule matrix), the callout boxes and all 4 embedded images, extracted from the DOCX package at native resolution (`charts_examples/doc_images/`). **Limit:** no DOCX page renderer (LibreOffice) is installed here, so page-layout images could not be produced; the text, tables and images were read from the document XML and the image files.
* Structure: section numbers run 1, 3, 4, ... 10 (there is no section 2; no content appears to be missing). Page headers use '9:15 candle' and '9:20 candle' interchangeably for the first candle.

## What it requires (summary)

One decision per day at 09:20 on the NIFTY 50 5-minute chart, only when all of: gap within 250/300 points; 09:20 close on the allowed side of the 200 EMA; at least one previous-day resistance (BUY) / support (SELL), major or inner, broken by the close; green (BUY) / red (SELL) candle with at least one accepted pattern and a wrong-side wick of at most 20% of the range. Stop 30 / target 60 points, no re-entry, no entry after 09:20.

## Every statement the document itself marks as unconfirmed

| where | statement | marker |
|---|---|---|
| 4 EMA | Compare the 9:20 close with the EMA value on that same candle | TO CONFIRM |
| 5 | Break = close beyond the level; a wick poke does not count | TO CONFIRM |
| 5 | Zone break edges (BUY above top, SELL below bottom) | TO CONFIRM |
| 5 | How levels are found (swings or hand-drawn) | not yet defined |
| 6 | Hammer / shooting-star proportions; engulfing reference at the first candle | still to be defined |
| 6 Ex2 | Example 2 fails the 20% rule | TO CONFIRM |
| 6 callout | Examples 2 and 3 do not match the written wick rule | rule as written applies |
| 1; 7 | Maximum gap 250 or 300 | final value to be confirmed |
| 8 | Entry price = close of the 9:15 candle | TO CONFIRM |
| 8 | Same-candle stop/target order (conservative default: stop first) | TO CONFIRM |
| 8 | End-of-session exit time (e.g. 3:15 PM) | to be confirmed |


## Observations on the document's own numbers

* The EMA values quoted in the examples ('about 25,050 / 25,207 / 25,234') are the TradingView labels at the cursor position in each screenshot (15 Sep 11:45, 17 Sep 13:25, 23 Sep 14:50), not the 09:20 value; the independent EMA reproduces all three labels within 0.25 points.
* The position tools in the screenshots are hand-drawn (Example 1: stop 30.85 / target 60.55 from the entry tag; Example 2: stop 31.55 / target 54.45), so the 'about 25,107 / 25,077 / 25,168' figures are approximate.
* The measured candle percentages (Examples 2 and 3) are reproduced exactly by the secondary feed (see `original_examples_reconstruction.md`).

## Rule registry

`rule_authority_registry.csv` (32 rules) classifies every rule; `source_to_code_traceability.csv` links each to code and tests.