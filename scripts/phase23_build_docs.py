"""Phase 2.3: generate docs/phase2/phase23_user_approved_rules.md from the rule registry YAML (authority, supersession, code, tests)."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "phase2"


def main() -> None:
    reg = yaml.safe_load((DOCS / "rule_registry.yaml").read_text())
    rules = reg["rules"]
    by_id = {r["rule_id"]: r for r in rules}
    approved = [r for r in rules if r.get("effective_phase") == "2.3"]
    md = ["# Phase 2.3 - user-approved rules (generated from the rule registry)\n",
          "Authority vocabulary: **SOURCE_VERIFIED** (stated in a PDF/the report) · **USER_APPROVED** (the strategy owner's instruction; NOT a rule written in the PDFs) · "
          "**PROPOSED_FOR_REVIEW** · **CONFLICTING** · **UNRESOLVED**. Every rule below carries `effective_phase = 2.3`. History is never erased: a replaced rule stays in the "
          "registry, marked `SUPERSEDED_BY_USER_APPROVED_RULE`.\n",
          f"Registry: {len(rules)} rules; {len(approved)} created or re-authorised in Phase 2.3.\n",
          "| rule | authority | approval source | replaces / replaced by | implementing function | verifying tests |", "|---|---|---|---|---|---|"]
    for r in approved:
        rep = []
        if r.get("supersedes"):
            rep.append(f"supersedes **{r['supersedes']}**")
        if r.get("superseded_by"):
            rep.append(f"SUPERSEDED BY **{r['superseded_by']}**")
        impl = "<br>".join(f"`{x}`" for x in r["implemented_by"]) or ("- (superseded; legacy mode `post_t1_stop_mode='ENTRY_BREAKEVEN'`)" if r["implementation_status"].startswith("SUPERSEDED") else "-")
        tests = "<br>".join(f"`{t.split('::')[-1]}`" for t in r["tested_by"][:3]) + (f"<br>(+{len(r['tested_by']) - 3} more)" if len(r["tested_by"]) > 3 else "") or "-"
        md.append(f"| **{r['rule_id']}** | {r['authority']} | {r['approval_source'] or '-'} | {'; '.join(rep) or '-'} | {impl} | {tests} |")
    md += ["\n## What each approved rule says\n"]
    for r in approved:
        md += [f"### {r['rule_id']} - {r['authority']}", r["description"], ""]
    md += ["## The supersession record\n",
           "| old rule | authority of the old rule | new rule | status |", "|---|---|---|---|"]
    for r in approved:
        if r.get("supersedes"):
            old = by_id[r["supersedes"].split()[0]]
            md.append(f"| **{old['rule_id']}** ({old['description'][:110]}...) | {old['authority']} (performance report) | **{r['rule_id']}** | old: `{old['implementation_status']}`; new: APPROVED (USER_APPROVED) |")
    md.append("\nExample: `RULE POST_T1_STOP_006 | AUTHORITY USER_APPROVED | OLD_RULE EXACT_ENTRY_BREAKEVEN (EXE-BE-001) | NEW_RULE ENTRY_MINUS_6_LONG / ENTRY_PLUS_6_SHORT | STATUS APPROVED`.")
    (DOCS / "phase23_user_approved_rules.md").write_text("\n".join(md) + "\n")
    print(len(approved), "rules written")


if __name__ == "__main__":
    main()
