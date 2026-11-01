"""Source-to-code traceability: ``@implements`` ties a function to registry rule IDs."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from nifty_trading.strategies.rule_data import RULE_IDS, RULES

F = TypeVar("F", bound=Callable)
IMPLEMENTATIONS: dict[str, tuple[str, ...]] = {}
RULE_BY_ID: dict[str, dict] = {r["rule_id"]: r for r in RULES}


def implements(*rule_ids: str) -> Callable[[F], F]:
    """Register ``fn`` as an implementation of the given rules. Unknown IDs fail at import time."""
    unknown = [r for r in rule_ids if r not in RULE_IDS]
    if unknown:
        raise KeyError(f"unknown rule id(s) {unknown}")

    def deco(fn: F) -> F:
        IMPLEMENTATIONS[f"{fn.__module__}.{fn.__qualname__}"] = tuple(rule_ids)
        fn.__rule_ids__ = tuple(rule_ids)  # type: ignore[attr-defined]
        return fn

    return deco


def classification(rule_id: str) -> str:
    return RULE_BY_ID[rule_id]["classification"]
