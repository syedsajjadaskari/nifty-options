"""Phase 6.0: clean-room NIFTY 9:20 ORB research engine built from the latest rulebook (Nifty_920_ORB_Rulebook).

Independent of the legacy ORB engines (strategies/orb.py, orb_candidates.py, research/phase54_orb.py, phase53*): nothing here imports them.
It reuses only verified infrastructure: parquet loaders, the NSE calendar, session classification (usable / official close) and the
bar-executability classifier. Research only: synthetic NIFTY index-point P&L; no orders; not integrated into the five-strategy portfolio.
"""
