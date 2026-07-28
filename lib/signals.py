from __future__ import annotations

from .technical_analysis import compute_technical_score_neutral


def summarize_signal_state(data) -> dict:
    return compute_technical_score_neutral(data)

