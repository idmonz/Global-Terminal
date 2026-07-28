from __future__ import annotations

import html
import re
from typing import Any

_FORMULA_PREFIXES = ("=", "+", "-", "@")
_PATH_RE = re.compile(r"(?:[A-Za-z]:\\|/(?:home|mnt|Users|tmp|private|secret|data/private)/|(?<!https:)(?<!http:)(?<!file:)/(?:[A-Za-z0-9._-]+/)+[A-Za-z0-9._-]+)[^\s)\]]*")


def escape_report_identifier(value: Any, *, max_length: int = 200) -> str:
    text = "" if value is None else str(value)
    text = _PATH_RE.sub("[local-path-redacted]", text)
    text = text.replace("\x00", "")[:max_length]
    return html.escape(text, quote=True)


def escape_csv_formula_text(value: Any) -> str:
    text = "" if value is None else str(value)
    stripped = text.lstrip()
    if stripped.startswith(_FORMULA_PREFIXES):
        text = "'" + text
    return escape_report_identifier(text, max_length=500)


def sanitize_user_supplied_markdown_field(value: Any) -> str:
    return escape_csv_formula_text(value)


def sanitize_report_table_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []
    for row in rows:
        cleaned.append({str(k): escape_csv_formula_text(v) if isinstance(v, str) else v for k, v in dict(row).items()})
    return cleaned
