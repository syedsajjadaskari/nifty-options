# Optional colour-wrapper metadata defect

The defect is reproducible: `orb_colour.py:35-39` changes a red-long pin record from CONFIRMED to INVALIDATED, but leaves execution-config confirmation labels and verification metadata unchanged. Its appended trace also uses candle-start09:15 instead of confirmation09:20. The probe in optional_wrapper_probe.json preserves the actual fields.

| Concern | Finding |
|---|---|
| Strategy identity | `strategy` remains ORB. The defect does not relabel ORB as IRF. |
| Candidate/config selection | A/B use ORBStrategy; C uses ORBCandidateStrategy. None uses ORBColourStrategy. Factory selection is explicit, not inferred from stale metadata. |
| Signal selection | `selection.is_valid` rejects INVALIDATED before reading executable metadata. No false trade results from the stale label in the tested path. |
| Signal tracing | The optional wrapper contains stale inherited confirmation information and a wrong start-time label; a consumer relying on metadata alone could mislabel a rejected record. This is a real maintenance defect. |
| Phase 5.9 chart/report labels | Derived from canonical `signal_status`, actual A ledger and fresh frozen-engine outputs. No optional-wrapper record is displayed as confirmed. |
| Manual comparison | Phase 5.6/5.8 signal counts use signal_status; A/B/C execution ledgers do not use the colour wrapper. The 35/50/34 baseline is unaffected. |

No active or wrapper source was fixed: the defect is isolated from this package's charts and counts. A future metadata-only maintenance patch should rebuild status metadata, stamp the confirmation end and rederive concurrency labels. Phase 5.8's strict expected-failure test remains present and is explicitly reported, not hidden. Author-rule activation remains out of scope.

Actual engine classes and rejected-record values:

```json
{
  "records": [
    {
      "strategy": "ORB",
      "method": "Method 1",
      "signal_status": "INVALIDATED",
      "execution_entry_status": "PROPOSAL_DEPENDENT",
      "selection_is_valid": false,
      "trace": [
        "09:20 WAITING_FOR_SETUP->SETUP_DETECTED: 09:15 candle broke and closed beyond 115.0",
        "09:20 SETUP_DETECTED->SIGNAL_CONFIRMED: level broken, trend ok, candle strong",
        "09:15 SIGNAL_CONFIRMED->SETUP_INVALIDATED: AUTHOR_CLARIFICATION_PHASE51_AC27: ORB long needs a green close; short (mirror, ORB-GLOBAL-002) a red close"
      ]
    }
  ],
  "orb_engine_classes": {
    "A": [
      "ORBStrategy"
    ],
    "B": [
      "ORBStrategy"
    ],
    "C": [
      "ORBCandidateStrategy"
    ]
  },
  "phase59_uses_signal_status_not_execution_entry_label": true,
  "active_change": false
}
```
