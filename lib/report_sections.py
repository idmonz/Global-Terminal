from __future__ import annotations
from typing import Any


def section(title: str, lines: list[str] | None = None) -> str:
    body = lines or ["No supplied context for this section."]
    return "\n".join([f"## {title}", "", *body, ""])


def bullet_rows(rows: list[dict[str, Any]], fields: list[str], *, empty: str) -> list[str]:
    if not rows:
        return [f"- {empty}"]
    out = []
    for row in rows:
        parts = [f"{field}: {row.get(field, 'n/a')}" for field in fields]
        out.append("- " + " | ".join(parts))
    return out


def inspect_next(commands: list[str]) -> str:
    return section("What To Inspect Next", [f"- `{cmd}`" for cmd in commands] or ["- No next command supplied."])
