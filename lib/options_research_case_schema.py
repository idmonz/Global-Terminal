from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

OPTIONS_CASE_NOTICE = "Options, option-chain, volatility-surface, option-book, and model outputs are research calculations only. They are not investment advice, trading recommendations, trade approvals, hedging instructions, or execution instructions."


@dataclass(frozen=True)
class OptionsResearchCaseManifest:
    case_id: str
    title: str
    created_at: str
    updated_at: str
    status: str = "active"
    source: str = "local_private_options_case_store"
    artifacts: dict[str, str] = field(default_factory=dict)
    timeline: list[dict[str, Any]] = field(default_factory=list)
    caveats: list[str] = field(default_factory=lambda: ["local_private_only", "excluded_from_release", "supplied_data_only"])
    notice: str = OPTIONS_CASE_NOTICE
    research_only: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
