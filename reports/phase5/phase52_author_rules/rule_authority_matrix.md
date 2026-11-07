# Rule authority matrix

Authority levels: SOURCE_VERIFIED (a guide states it), AUTHOR_APPROVED (the author's own sentence, Phase 3.4), USER_APPROVED (owner), AUTHOR_CALL (Phase 5.2 telephone statement), HANDWRITTEN (Phase 5.1), PROPOSED (a research parameter nobody approved).

| rule | authority | current engine | Phase 5.2 status | evidence |
|---|---|---|---|---|
| PDR / PDS entry on the first eligible confirmation candle | USER_APPROVED (owner clarification) + AUTHOR_CALL | already implemented (PDR: first qualifying candle after the retest; PDS: first red candle at the zone, Method 3 on the earliest support break) | ACTIVE - verified, unchanged | pdr_first_eligible_audit.md, pds_first_eligible_audit.md |
| PDR zone = previous-day body-based resistance, open strictly above, retest, pattern, close strictly above the ceiling | AUTHOR_APPROVED (PDR-A01..A05) / OWNER_INTERPRETATION | implemented (Phase 3.6) | ACTIVE - preserved | unchanged |
| PDR pattern numbers (body 60%, upper wick 20%, 2x wick, 30% close, hammer 10% / 60%) | PROPOSED | implemented as research parameters | ACTIVE - preserved (the brief forbids changing them) | the handwritten 'first green candle' candles fail them (see the PDR audit) |
| the PDR confirmation may not be the retest candle | PROPOSED (PDR-A07) | implemented | ACTIVE - preserved and LABELLED; owner decision O7 | 8 armed setups have a retest candle that would itself qualify |
| PDS: first red candle at the zone; weak first candle not taken; Method 3 break of a small support | SOURCE_VERIFIED_QUALITATIVE (PDS-M-001, PDS-M3-001) | implemented | ACTIVE - preserved | pds_first_eligible_audit.md |
| PDS co-confirmed methods recorded, one actionable signal | USER_APPROVED (brief 5.2) | recorded by `PDSCoConfirmStrategy` (annotation only) | ACTIVE in `phase52-approved` | occurs in 0 sessions (a strong body and a higher-price-rejection pin bar are mutually exclusive with the current thresholds) |
| IRF Method 2A support = first red candle (level?) | AUTHOR_CALL | support = swing-low fractal (proposal SWING_K1) | CANDIDATE only (low / body low); UNRESOLVED | irf_first_red_candle_audit.md |
| IRF EMA gap of 28 points | AUTHOR_CALL (handwritten pages: 27) | no EMA condition | UNRESOLVED - diagnostics only | irf_ema_28_point_audit.md |
| IRF not at the day's low | AUTHOR_CALL ('already in the documents': not located) | no condition | UNRESOLVED - diagnostics only | irf_day_low_audit.md |
| ORB long needs a green first candle (short: red) | HANDWRITTEN for long (AC27); short = source interpretation (ORB-GLOBAL-002) | pin-bar route admits either colour | CANDIDATE (Phase 5.1, opt-in), kept selectable | phase52-cand-orb-colour |
| ORB inner level, trendline, strength thresholds, trend filter | PROPOSED research variants (not in the source) | implemented as proposals | ACTIVE - preserved; causes of the missing signals reported | orb_missing_signal_audit.md |
| first valid signal first; max two trades; second trade only PDR/PDS after a full stop; 13:00 cutoff; 6 lots 3+3; stops 35 (ORB 30); T1 27; T2 60/70; post-T1 stop entry -/+ 6; no trailing; forced exit; same-minute conflicts unresolved | USER_APPROVED | implemented | ACTIVE - unchanged (no controller code touched) | frozen hashes verified |
| RF | SOURCE_VERIFIED / USER_APPROVED | implemented | ACTIVE - unchanged | RF signals identical under every configuration |
