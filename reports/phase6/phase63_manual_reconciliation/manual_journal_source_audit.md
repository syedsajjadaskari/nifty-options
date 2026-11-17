# Manual journal source audit

* File: `docs/trading journal/Trading_Journal_Sep2025_Aug2026 REPORT.xlsx`, SHA-256 `97a9ad4dfb5520619bb979770115d7b6f4e3e37e649af255c543f5fce9694781` (read-only; every value kept as written).
* Data rows: **190**; the Summary sheet states 189 trades (the Summary figure is not the data-row count; the discrepancy of 1 is unresolved and not corrected).
* By strategy: {'IRF': 73, 'PDR': 8, 'ORB': 89, 'RF': 17, 'PDS': 3}.
* Weekend-dated rows (not exchange sessions, can never match, kept as written): 5 - 2025-10-11 ORB, 2026-02-14 IRF, 2026-08-15 ORB, 2026-08-22 ORB, 2026-08-29 ORB.
* Rows on dates outside the evaluated sessions (other than weekends): 0.
* Columns available: serial number, date, entry-time label, strategy, outcome (Target / SL / BE). **No direction, entry price, support/resistance level, stop, target or exit time is recorded.**
* Consequence: a 'verified exact trade match' (same direction, entry price within a tolerance, compatible exit details) cannot be established for any row. No missing field was manufactured; the matching below uses only date, strategy, time label and the outcome label.

Summary sheet: {"Total trades": 189, "Final cumulative P&L (\u20b9)": 769860, "Target outcomes": 80, "Break-even outcomes": 44, "Stop-loss outcomes": 65, "Winning P&L entries (\u20b9)": 1600560, "Losing P&L entries (\u20b9)": -830700}