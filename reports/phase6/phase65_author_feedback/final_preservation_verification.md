# Final preservation verification (Phase 6.5 continuation)

Git HEAD at start / now: `9d7f5af8` / `9d7f5af8`. Baseline: `continuation_before_snapshot.json` (taken before any continuation file was written; the Phase 7.0 files already present were recorded as EXTERNAL).

| category | result |
|---|---|
| 1. tracked files modified by this work | [] |
| 2. tracked files modified by another process / unattributed | [] |
| 3. new Phase 6.5 files (continuation) | 488 (+ 2 Phase 6.5 files edited after the snapshot) |
| 4. externally owned Phase 7.0 files | {'present': 2913, 'new_since_snapshot': 1498, 'changed_since_snapshot': 1, 'removed_since_snapshot': 0, 'note': "owned by another process; Phase 6.5 never writes there, so any change/addition is that process's own activity (attribution is by ownership, not by observation)"} |
| 4b. a further externally owned Phase 7.1 effort that appeared during this run | {'present': 23, 'new_since_snapshot': 23, 'changed_since_snapshot': 0, 'removed_since_snapshot': 0, 'note': "a further externally owned effort (Phase 7.1: data/phase71/, scripts/phase71_*, research/phase71/, tests/test_phase71_*) that appeared during this run. Attributed by naming and by exclusion from Phase 6.5's own created files, not observed directly; never read, written or run by Phase 6.5"} |
| 5. untracked source documents | ['docs/strategy_docs/IRF_Inverse_Retest_Failure_Rulebook.pdf', 'docs/strategy_docs/IRF_Method2_First_Red_Candle_Rulebook.pdf'] |
| 6. genuinely deleted original files | [] |
| frozen files changed / removed | 0 / 0 |
| other new files outside known owners | [] |
| **frozen baseline intact** | **True** |

**Limitation:** externally owned Phase 7.0 files changed during this run (1 changed, 1498 new); Phase 6.5 only read their metadata, parsed source text and published outputs; a further externally owned Phase 7.1 effort appeared during this run (23 files); Phase 6.5 never read, wrote or ran them. Those files are excluded from the frozen-baseline verdict, so no hash comparison of them against the start snapshot is possible.

Phase 6.5 never wrote to `irf_v3/`, `reports/phase7/`, `scripts/phase70_*`, `tests/test_phase70_*` or any Phase 7.1 path (`data/phase71/`, `data/raw/phase71_*`, `scripts/phase71_*`, `research/phase71/`, `tests/test_phase71_*`, which it never read; its only access to Phase 7.0 was a read-only inventory: file metadata, a parse of the Phase 7.0 source text - parsed, never executed or imported - and its published Markdown / CSV / JSON outputs). The paper-trading module `core/paper.py` and every configuration module are unchanged (they are FROZEN-class paths in the hash comparison). Nothing was committed, staged or pushed.