from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


SOURCE_MODES = {"auto", "native_only", "openbb_preferred", "openbb_only", "provider_specific"}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_source_mode(source_mode: str | None = None) -> str:
    value = str(source_mode or "auto").strip().lower().replace(" ", "_")
    return value if value in SOURCE_MODES else "auto"


@dataclass
class DataRequest:
    request_id: str = field(default_factory=lambda: str(uuid4()))
    app_area: str = ""
    domain: str = ""
    endpoint: str = ""
    symbol: str | None = None
    symbols: list[str] = field(default_factory=list)
    asset_class: str | None = None
    start_date: Any = None
    end_date: Any = None
    interval: str | None = None
    period: str | None = None
    provider_preference: str | None = None
    source_mode: str = "auto"
    required_fields: list[str] = field(default_factory=list)
    optional_fields: list[str] = field(default_factory=list)
    allow_fallback: bool = True
    allow_estimates: bool = False
    allow_proxy: bool = False
    user_params: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.source_mode = normalize_source_mode(self.source_mode)
        if self.symbol and not self.symbols:
            self.symbols = [self.symbol]
        self.symbols = [str(symbol).upper() for symbol in self.symbols if symbol]
        if self.symbol:
            self.symbol = str(self.symbol).upper()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SourceMetadata:
    provider: str
    source: str
    fetched_at: str = field(default_factory=utc_now_iso)
    freshness: str = "unknown"
    source_mode: str = "auto"
    endpoint: str = ""
    caveat: str | None = None
    is_cached: bool = False
    is_optional: bool = False
    requires_key: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DataGap:
    field: str
    reason: str
    severity: str = "medium"
    provider: str | None = None
    endpoint: str | None = None
    is_blocking: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ProviderCapability:
    provider: str
    endpoint: str
    app_area: str = ""
    native: bool = True
    openbb: bool = False
    requires_key: bool = False
    supports_proxy: bool = False
    supports_estimates: bool = False
    priority: int = 100
    caveat: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EndpointCapability:
    endpoint_id: str
    app_area: str
    domain: str
    label: str
    description: str
    required_fields: list[str] = field(default_factory=list)
    optional_fields: list[str] = field(default_factory=list)
    native_providers: list[str] = field(default_factory=list)
    openbb_candidate_paths: list[str] = field(default_factory=list)
    optional_provider_keys: list[str] = field(default_factory=list)
    estimated_allowed: bool = False
    proxy_allowed: bool = False
    caveat: str = ""
    downstream_pages: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DataContract:
    endpoint: str
    required_fields: list[str] = field(default_factory=list)
    optional_fields: list[str] = field(default_factory=list)
    primary_key: list[str] = field(default_factory=list)
    time_field: str | None = "date"
    caveat: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DataRoute:
    provider: str
    endpoint: str
    source: str
    native: bool = True
    openbb: bool = False
    fallback_chain: list[str] = field(default_factory=list)
    missing_keys: list[str] = field(default_factory=list)
    warning: str | None = None
    caveat: str | None = None
    rank: int = 100

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DataPayload:
    data: Any
    metadata: SourceMetadata
    gaps: list[DataGap] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"data": self.data, "metadata": self.metadata.to_dict(), "gaps": [gap.to_dict() for gap in self.gaps]}


@dataclass
class UnifiedDataResult:
    ok: bool
    data: Any = None
    provider: str = ""
    source: str = ""
    endpoint: str = ""
    native_used: bool = False
    openbb_used: bool = False
    fallback_used: bool = False
    is_estimated: bool = False
    is_proxy: bool = False
    freshness: str = "unknown"
    data_gaps: list[DataGap] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    caveats: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["data_gaps"] = [gap.to_dict() if hasattr(gap, "to_dict") else gap for gap in self.data_gaps]
        return payload


def request_from_kwargs(endpoint: str, **kwargs: Any) -> DataRequest:
    return DataRequest(endpoint=endpoint, **kwargs)
