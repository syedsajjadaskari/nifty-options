"""Phase 5: the option-execution feasibility block appended to every daily journal.

It states, per index-signal trade, which long option the signal WOULD map to (bullish -> buy CE, bearish -> buy PE) and why NO option fill exists. Nothing here estimates a premium. The conclusion is the finding of
``scripts/phase5_options_probe.py`` and ``reports/phase5/options_feasibility/option_data_availability.md``: the broker's instrument master lists only LIVE contracts, so the codes of the contracts that existed on a
historical date cannot be obtained; no premium series for them can be requested; and no contract-selection policy has been approved by the owner.
"""

from __future__ import annotations

from nifty_trading.research import phase5_data as D5

LEG = {"LONG": "BUY CALL (CE)", "SHORT": "BUY PUT (PE)"}


def option_block(trades: list[dict], ix: D5.IndexSpec, spec) -> str:
    lines = ["## Option-execution feasibility (information only; no option trade is simulated)", ""]
    if not trades:
        lines += ["No index-signal trade this session, so no option instrument is implied.", ""]
        return "\n".join(lines)
    lines += [f"The index result above is an INDEX-POINT result on {ix.name}. It is not an option result: a move of N index points is not a move of N premium points (delta, gamma, theta, vega, spread and liquidity decide the premium).", "",
              "| trade | strategy | index direction | long option it maps to | historical contract identified? | premium data available? | premium fill supportable? |", "|---|---|---|---|---|---|---|"]
    for t in trades:
        lines.append(f"| {t['trade_id']} | {t['strategy']} | {t['direction']} | {LEG.get(t['direction'], '?')} | no | no | no |")
    lines += ["", "Why: (1) the broker's instrument master lists only contracts that are live today, so the scrip code of a contract that existed on this date is not available; (2) historical candles can only be requested by scrip code; "
              "(3) the strike and expiry selection policy is an owner decision that has not been made (`options_feasibility/option_contract_selection_decisions.md`). No option entry, exit, premium or option P&L is shown, and none may be inferred from the index points.", ""]
    return "\n".join(lines)
