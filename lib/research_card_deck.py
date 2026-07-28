from __future__ import annotations

from typing import Any


def build_research_card_deck(cards: list[dict[str, Any]] | None = None, *, title: str = "Research cards", empty_message: str = "No cards available.") -> dict[str, Any]:
    normalized = []
    for idx, card in enumerate(cards or []):
        normalized.append(
            {
                "id": card.get("id") or card.get("key") or f"card_{idx+1}",
                "title": card.get("title", "Research card"),
                "summary": card.get("summary", ""),
                "status": card.get("status") or card.get("severity") or "info",
                "tags": card.get("tags", []),
                "source": card.get("source", ""),
                "next_action": card.get("next_action") or "review",
                "research_only": True,
            }
        )
    return {"title": title, "cards": normalized, "empty": len(normalized) == 0, "empty_message": empty_message, "research_only": True}


def build_next_action_buttons(actions: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    return [
        {
            "label": action.get("label", "Review"),
            "command": action.get("command", "REVIEW"),
            "page": action.get("page", ""),
            "enabled": bool(action.get("enabled", True)),
            "research_only": True,
        }
        for action in actions or []
    ]
