"""Dataset-level evaluation that never skips a day silently.

``build_session_contexts`` only creates contexts for evaluable sessions. This runner pairs it with the quality
information so that EVERY non-evaluable session with data produces exactly one explicit ``NOT_EVALUATED`` record
carrying its quality status and reasons. An evaluable session produces zero or more normal records (zero when no
setup occurred).
"""

from __future__ import annotations

from datetime import date

from nifty_trading.data.sessions import SessionContext, SessionInfo
from nifty_trading.strategies.base import (
    SignalEngine,
    SignalRecord,
    SignalStatus,
    VerificationStatus,
)


def evaluate_dataset(engine: SignalEngine, ctxs: dict[date, SessionContext], infos: dict[date, SessionInfo]) -> list[SignalRecord]:
    out: list[SignalRecord] = []
    for d in sorted(infos):
        if d in ctxs:
            out.extend(engine.evaluate_session(ctxs[d]))
            continue
        info = infos[d]
        out.append(SignalRecord(
            strategy=engine.STRATEGY, method="ALL", direction=engine._default_direction(), signal_date=d, signal_timestamp=None,
            signal_candle_start=None, signal_candle_open=None, signal_candle_high=None, signal_candle_low=None, signal_candle_close=None,
            reference_levels={}, rule_ids_satisfied=[], rule_ids_failed=[], signal_status=SignalStatus.NOT_EVALUATED.value,
            invalidation_reason=f"SESSION_NOT_EVALUABLE:{info.quality.value}:{info.status.value}"
                                + (f"({'; '.join(info.reasons)})" if info.reasons else ""),
            verification_status=VerificationStatus.NOT_READY.value, flags=list(info.flags),
            execution_config=engine.exec_config("ALL", VerificationStatus.NOT_READY.value, "NOT_EVALUATED")))
    return out
