from __future__ import annotations
from .watchlist_alias_registry import ALIASES, aliases_for, normalize_token

OSINT_ALIASES = ALIASES


def aliases_for_entity(value):
    return aliases_for(value)
