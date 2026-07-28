from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class AssetClassDefinition:
    asset_class: str
    label: str
    primary_identifier: str
    description: str
    core_fields: list[str]
    search_fields: list[str]
    classification_fields: list[str]
    routing_commands: list[str]
    source_status: str = "reference-schema"
    local_status: str = "schema-ready/no-live-universe"
    live_rows_claimed: bool = False
    license_stance: str = "direct-use-allowed"
    evidence_ref: str = ""
    caveat: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


FINANCEDATABASE_EVIDENCE = {
    "project": "FinanceDatabase",
    "archive": "FinanceDatabase-main.zip",
    "detected_license": "MIT",
    "license_stance": "direct-use-allowed",
    "evidence_refs": [
        "FinanceDatabase-main/pyproject.toml:1-5",
        "FinanceDatabase-main/database/equities/NMS.csv:1-1",
        "FinanceDatabase-main/database/cryptos.csv:1-1",
        "FinanceDatabase-main/database/currencies.csv:1-1",
        "FinanceDatabase-main/database/indices.csv:1-1",
        "FinanceDatabase-main/database/moneymarkets.csv:1-1",
    ],
    "adoption_boundary": "Schema/taxonomy behavior only; no external CSV row data is copied into first-party fixtures.",
}


ASSET_CLASS_DEFINITIONS = [
    AssetClassDefinition(
        asset_class="equity",
        label="Equities",
        primary_identifier="symbol",
        description="Listed company and share-class reference metadata for terminal search, watchlists, and equity commands.",
        core_fields=[
            "symbol",
            "name",
            "summary",
            "currency",
            "sector",
            "industry_group",
            "industry",
            "exchange",
            "mic",
            "market",
            "country",
            "market_cap",
            "isin",
            "cusip",
            "figi",
            "delisted",
        ],
        search_fields=["symbol", "name", "isin", "cusip", "figi", "sector", "industry", "country"],
        classification_fields=["sector", "industry_group", "industry", "country", "market_cap", "exchange", "mic"],
        routing_commands=["DES", "FA", "GP", "HP", "KEY", "NI", "INTEL"],
        evidence_ref="FinanceDatabase-main/database/equities/NMS.csv:1-1",
        caveat="Equity universe schema is ready; live/security-master rows require a configured provider or separately reviewed import.",
    ),
    AssetClassDefinition(
        asset_class="etf",
        label="ETFs",
        primary_identifier="symbol",
        description="Exchange-traded fund metadata for category/family search and portfolio exposure grouping.",
        core_fields=["symbol", "name", "currency", "summary", "category_group", "category", "family", "exchange", "mic", "isin"],
        search_fields=["symbol", "name", "isin", "category_group", "category", "family"],
        classification_fields=["category_group", "category", "family", "exchange", "mic"],
        routing_commands=["DES", "GP", "HP", "WEI", "NI"],
        evidence_ref="FinanceDatabase-main/database/etfs/NYQ.csv:1-1",
        caveat="ETF rows are not bundled; provider-backed holdings and flow data remain future work.",
    ),
    AssetClassDefinition(
        asset_class="fund",
        label="Funds",
        primary_identifier="symbol",
        description="Fund reference metadata for family/category grouping and saved research lists.",
        core_fields=["symbol", "name", "currency", "summary", "category_group", "category", "family", "exchange", "mic"],
        search_fields=["symbol", "name", "category_group", "category", "family"],
        classification_fields=["category_group", "category", "family", "exchange", "mic"],
        routing_commands=["DES", "GP", "HP", "NI"],
        evidence_ref="FinanceDatabase-main/database/funds/NAS.csv:1-1",
        caveat="Fund universe schema is present without live NAV, holdings, or provider claims.",
    ),
    AssetClassDefinition(
        asset_class="index",
        label="Indices",
        primary_identifier="symbol",
        description="Index reference metadata for macro tape, chart commands, and benchmark selection.",
        core_fields=["symbol", "name", "currency", "summary", "category_group", "category", "exchange", "mic"],
        search_fields=["symbol", "name", "category_group", "category"],
        classification_fields=["category_group", "category", "exchange", "mic"],
        routing_commands=["GP", "HP", "MOV", "WEI", "NI"],
        evidence_ref="FinanceDatabase-main/database/indices.csv:1-1",
        caveat="Index schema does not imply live constituent, weight, or price coverage.",
    ),
    AssetClassDefinition(
        asset_class="fx_pair",
        label="FX Pairs",
        primary_identifier="symbol",
        description="Currency pair metadata for FX command routing and macro exposure views.",
        core_fields=["symbol", "name", "base_currency", "quote_currency", "summary", "exchange"],
        search_fields=["symbol", "name", "base_currency", "quote_currency"],
        classification_fields=["base_currency", "quote_currency", "exchange"],
        routing_commands=["FXC", "CURV", "GP", "HP", "NI"],
        evidence_ref="FinanceDatabase-main/database/currencies.csv:1-1",
        caveat="FX schema is available; live FX quotes require existing keyless or configured market providers.",
    ),
    AssetClassDefinition(
        asset_class="crypto_pair",
        label="Crypto Pairs",
        primary_identifier="symbol",
        description="Crypto pair metadata for crypto command routing and cross-asset risk grouping.",
        core_fields=["symbol", "name", "cryptocurrency", "currency", "summary", "exchange"],
        search_fields=["symbol", "name", "cryptocurrency", "currency"],
        classification_fields=["cryptocurrency", "currency", "exchange"],
        routing_commands=["CRYPTO", "GP", "HP", "NI"],
        evidence_ref="FinanceDatabase-main/database/cryptos.csv:1-1",
        caveat="Crypto schema is not a live exchange list; CoinGecko/Binance runtime status remains separate.",
    ),
    AssetClassDefinition(
        asset_class="money_market",
        label="Money Markets",
        primary_identifier="symbol",
        description="Money-market instrument metadata for cash/short-duration watchlists and macro liquidity views.",
        core_fields=["symbol", "name", "currency", "summary", "family", "exchange"],
        search_fields=["symbol", "name", "family", "currency"],
        classification_fields=["family", "currency", "exchange"],
        routing_commands=["DES", "CURV", "NI"],
        evidence_ref="FinanceDatabase-main/database/moneymarkets.csv:1-1",
        caveat="Money-market schema is reference-only in this slice; yields and holdings need provider validation.",
    ),
]


COMMAND_ASSET_MATRIX = [
    {
        "command": "DES",
        "label": "Description",
        "accepted_asset_classes": ["equity", "etf", "fund", "money_market"],
        "implementation_status": "schema-ready/provider-required",
        "caveat": "Can resolve asset type and target fields, but live descriptions depend on configured provider rows.",
    },
    {
        "command": "FA",
        "label": "Fundamental Analysis",
        "accepted_asset_classes": ["equity"],
        "implementation_status": "future-provider-required",
        "caveat": "Requires financial statements provider; no external fundamentals are bundled.",
    },
    {
        "command": "FXC",
        "label": "FX Crosses",
        "accepted_asset_classes": ["fx_pair"],
        "implementation_status": "schema-ready/provider-required",
        "caveat": "FX pair parsing is schema-ready; quotes remain provider-status dependent.",
    },
    {
        "command": "CRYPTO",
        "label": "Crypto Market",
        "accepted_asset_classes": ["crypto_pair"],
        "implementation_status": "schema-ready/provider-required",
        "caveat": "Crypto pair routing can use existing CoinGecko/Binance provider states when available.",
    },
    {
        "command": "WEI",
        "label": "Weights / Exposure",
        "accepted_asset_classes": ["etf", "index"],
        "implementation_status": "future-provider-required",
        "caveat": "Constituent and holdings data must be provider-backed before shown as live.",
    },
    {
        "command": "NI",
        "label": "News Intelligence",
        "accepted_asset_classes": ["equity", "etf", "fund", "index", "fx_pair", "crypto_pair", "money_market"],
        "implementation_status": "schema-ready/source-backed-news-required",
        "caveat": "Asset-to-news matching should expose source freshness and approximate matching caveats.",
    },
]


def build_asset_universe_contract() -> dict[str, Any]:
    asset_classes = [definition.to_dict() for definition in ASSET_CLASS_DEFINITIONS]
    return {
        "asset_classes": asset_classes,
        "command_asset_matrix": COMMAND_ASSET_MATRIX,
        "reference_sources": [FINANCEDATABASE_EVIDENCE],
        "readiness": {
            "schema_ready": True,
            "live_rows_claimed": False,
            "external_rows_copied": False,
            "default_mode": "reference-schema",
            "provider_required_for_live_universe": True,
        },
    }
