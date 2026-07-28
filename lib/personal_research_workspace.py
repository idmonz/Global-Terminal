from __future__ import annotations

from pathlib import Path
from typing import Any

from .research_workspace_db import initialize_workspace_db
from .workspace_summary_engine import build_workspace_summary, build_workspace_summary_cards
from .workspace_visuals import build_workspace_metric_cards, build_workspace_quick_action_cards, build_research_only_notice


def build_personal_research_workspace_payload(db_path: str | Path | None = None) -> dict[str, Any]:
    initialize_workspace_db(db_path)
    summary = build_workspace_summary(db_path)
    return {
        "title": "Personal Research Operating System",
        "notice": build_research_only_notice(),
        "summary": summary,
        "summary_cards": build_workspace_summary_cards(db_path),
        "metric_cards": build_workspace_metric_cards(summary),
        "quick_actions": build_workspace_quick_action_cards(),
        "manual_only": True,
        "no_background_daemon": True,
    }

