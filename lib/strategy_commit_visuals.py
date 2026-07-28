from __future__ import annotations
from typing import Any
from .strategy_decision_log import build_strategy_commit_summary


def build_strategy_commit_cards(commits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [build_strategy_commit_summary(c) for c in commits]

