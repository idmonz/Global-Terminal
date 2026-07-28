from __future__ import annotations

import csv
import hashlib
import math
import os
import re
import threading
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import quote

from .config import STATIC_DIR
from .runtime_cache import (
    RuntimeCacheRecord,
    load_runtime_cache_record,
    save_runtime_cache_record,
)


SYMBOL_DIRECTORY_VERSION = "symbol_directory.v1"
SYMBOL_WORKSTATION_VERSION = "symbol_workstation.v2"
REGISTRY_REVIEWED_AT = "2026-06-22T00:00:00+00:00"
FIXTURE_FETCHED_AT = "2026-06-22T00:00:00+00:00"
MAX_SEARCH_LIMIT = 20
MAX_QUERY_LENGTH = 64
MAX_SYMBOL_LENGTH = 24
HISTORY_STALE_SECONDS = 86_400
_SAFE_SYMBOL = re.compile(r"^[A-Z0-9][A-Z0-9._=/\-]{0,23}$")
_SAFE_QUERY = re.compile(r"^[A-Za-z0-9 ._=/\-]{1,64}$")
_MATERIALIZED_IDENTITY_CACHE: dict[tuple[str, int, int], list[dict[str, Any]]] = {}
_MATERIALIZED_IDENTITY_CACHE_LOCK = threading.Lock()
_STATIC_IDENTITIES_CACHE: list[dict[str, Any]] | None = None
_STATIC_IDENTITY_INDEX_CACHE: tuple[dict[str, dict[str, Any]], dict[str, str]] | None = None
_STATIC_IDENTITY_LOCK = threading.Lock()


@dataclass(frozen=True)
class SymbolIdentity:
    symbol: str
    name: str
    asset_class: str
    exchange: str
    currency: str
    region: str
    provider_symbol: str
    aliases: tuple[str, ...]
    registry_provider: str
    registry_source: str
    sector: str | None = None
    industry: str | None = None
    market_cap: float | None = None
    base_asset: str | None = None
    quote_asset: str | None = None
    source_status: str = "static/proxy"
    reviewed_at: str = REGISTRY_REVIEWED_AT
    caveat: str = ""
    data_gap: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "aliases": list(self.aliases),
            "search_symbol": _alias_key(self.symbol),
            "listing_status": "reviewed-static/not-current",
            "authoritative_security_master": False,
            "not_financial_advice": True,
        }


ETF_IDENTITIES = [
    ("SPY", "SPDR S&P 500 ETF Trust", "NYSE Arca"),
    ("QQQ", "Invesco QQQ Trust", "Nasdaq"),
    ("IWM", "iShares Russell 2000 ETF", "NYSE Arca"),
    ("DIA", "SPDR Dow Jones Industrial Average ETF Trust", "NYSE Arca"),
    ("VTI", "Vanguard Total Stock Market ETF", "NYSE Arca"),
    ("TLT", "iShares 20+ Year Treasury Bond ETF", "Nasdaq"),
    ("GLD", "SPDR Gold Shares", "NYSE Arca"),
    ("SLV", "iShares Silver Trust", "NYSE Arca"),
    ("USO", "United States Oil Fund", "NYSE Arca"),
    ("IBIT", "iShares Bitcoin Trust ETF", "Nasdaq"),
]

CRYPTO_IDENTITIES = [
    ("BTC", "Bitcoin"),
    ("ETH", "Ethereum"),
    ("BNB", "BNB"),
    ("SOL", "Solana"),
    ("XRP", "XRP"),
    ("DOGE", "Dogecoin"),
    ("ADA", "Cardano"),
    ("AVAX", "Avalanche"),
    ("LINK", "Chainlink"),
    ("DOT", "Polkadot"),
    ("TRX", "TRON"),
    ("LTC", "Litecoin"),
    ("BCH", "Bitcoin Cash"),
    ("UNI", "Uniswap"),
    ("ATOM", "Cosmos"),
    ("NEAR", "NEAR Protocol"),
    ("APT", "Aptos"),
    ("ARB", "Arbitrum"),
    ("OP", "Optimism"),
    ("SUI", "Sui"),
]

PROVIDER_CAPABILITIES = [
    {
        "asset_class": "equity",
        "provider": "yfinance",
        "intervals": ["1d", "1h"],
        "ranges_by_interval": {
            "1d": ["5d", "1mo", "3mo", "6mo", "1y", "2y", "5y"],
            "1h": ["5d", "1mo"],
        },
        "ttl_seconds": 900,
        "stale_seconds": HISTORY_STALE_SECONDS,
        "key_required": False,
        "source_status": "free-first/provider-dependent",
        "caveat": "Delayed public adapter; reliability and terms can change.",
    },
    {
        "asset_class": "etf",
        "provider": "yfinance",
        "intervals": ["1d", "1h"],
        "ranges_by_interval": {
            "1d": ["5d", "1mo", "3mo", "6mo", "1y", "2y", "5y"],
            "1h": ["5d", "1mo"],
        },
        "ttl_seconds": 900,
        "stale_seconds": HISTORY_STALE_SECONDS,
        "key_required": False,
        "source_status": "free-first/provider-dependent",
        "caveat": "Delayed public adapter; holdings and authoritative fund metadata are not included.",
    },
    {
        "asset_class": "crypto",
        "provider": "Binance USD-M Futures",
        "intervals": ["15m", "1h", "4h", "1d"],
        "ranges_by_interval": {
            "15m": ["1d", "5d"],
            "1h": ["1d", "5d", "1mo"],
            "4h": ["5d", "1mo", "3mo"],
            "1d": ["1mo", "3mo", "6mo", "1y"],
        },
        "ttl_seconds": 300,
        "stale_seconds": HISTORY_STALE_SECONDS,
        "key_required": False,
        "source_status": "free-first/provider-dependent",
        "caveat": "Public exchange endpoint; pair availability, rate limits, and regional access can change.",
    },
]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _clean_number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _alias_key(value: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(value or "").upper())


def normalize_symbol_input(value: str) -> str:
    normalized = str(value or "").strip().upper()
    if len(normalized) > MAX_SYMBOL_LENGTH or not _SAFE_SYMBOL.fullmatch(normalized):
        return ""
    return normalized


def normalize_search_query(value: str) -> str:
    normalized = " ".join(str(value or "").strip().split())[:MAX_QUERY_LENGTH]
    if not normalized or not _SAFE_QUERY.fullmatch(normalized):
        return ""
    return normalized


def _equity_identities() -> list[SymbolIdentity]:
    source = STATIC_DIR / "index_constituents" / "sp500.csv"
    rows: list[SymbolIdentity] = []
    if not source.exists():
        return rows
    with source.open("r", encoding="utf-8", newline="") as handle:
        for item in csv.DictReader(handle):
            symbol = normalize_symbol_input(item.get("ticker") or "")
            if not symbol:
                continue
            market_cap = _clean_number(item.get("market_cap"))
            aliases = {symbol, symbol.replace("-", "."), symbol.replace(".", "-")}
            rows.append(
                SymbolIdentity(
                    symbol=symbol,
                    name=str(item.get("company") or symbol),
                    asset_class="equity",
                    exchange="US listed",
                    currency="USD",
                    region="United States",
                    provider_symbol=symbol,
                    aliases=tuple(sorted(aliases)),
                    registry_provider="phase5i.local_equity_registry",
                    registry_source="static/index_constituents/sp500.csv",
                    sector=str(item.get("sector") or "Unclassified"),
                    industry=str(item.get("industry") or "Unclassified"),
                    market_cap=market_cap,
                    caveat="Reviewed local taxonomy used for bounded discovery; index membership and market cap are not claimed current.",
                    data_gap="Authoritative current exchange and index membership require a separately licensed security master.",
                )
            )
    return rows


def _etf_identities() -> list[SymbolIdentity]:
    return [
        SymbolIdentity(
            symbol=symbol,
            name=name,
            asset_class="etf",
            exchange=exchange,
            currency="USD",
            region="United States",
            provider_symbol=symbol,
            aliases=(symbol,),
            registry_provider="phase5m.reviewed_etf_registry",
            registry_source="project-native bounded ETF taxonomy",
            sector="ETF / cross-asset proxy",
            industry="Exchange-traded fund",
            caveat="Project-native reviewed ETF identity for discovery; holdings, AUM, and membership are provider-gated.",
            data_gap="Authoritative fund reference data and holdings are unavailable in this slice.",
        )
        for symbol, name, exchange in ETF_IDENTITIES
    ]


def _crypto_identities() -> list[SymbolIdentity]:
    rows = []
    for base, name in CRYPTO_IDENTITIES:
        symbol = f"{base}USDT"
        aliases = (
            symbol,
            base,
            f"{base}/USDT",
            f"{base}-USDT",
            f"{base}USD",
            f"{base}-USD",
            f"{base}/USD",
        )
        rows.append(
            SymbolIdentity(
                symbol=symbol,
                name=name,
                asset_class="crypto",
                exchange="Binance USD-M",
                currency="USDT",
                region="Global",
                provider_symbol=symbol,
                aliases=aliases,
                registry_provider="phase5m.reviewed_binance_pair_registry",
                registry_source="Binance public pair convention",
                base_asset=base,
                quote_asset="USDT",
                caveat="Static reviewed pair convention; a successful public exchange response is required before live listing is claimed.",
                data_gap="Exchange listing status and regional availability can change.",
            )
        )
    return rows


def _static_symbol_identities() -> list[dict[str, Any]]:
    global _STATIC_IDENTITIES_CACHE
    with _STATIC_IDENTITY_LOCK:
        if _STATIC_IDENTITIES_CACHE is None:
            identities = [*_equity_identities(), *_etf_identities(), *_crypto_identities()]
            _STATIC_IDENTITIES_CACHE = [
                item.to_dict()
                for item in sorted(
                    identities,
                    key=lambda row: (row.asset_class, row.symbol),
                )
            ]
        return [dict(row) for row in _STATIC_IDENTITIES_CACHE]


def _materialized_identity_from_row(
    row: dict[str, Any],
    *,
    materialization: dict[str, Any],
) -> dict[str, Any] | None:
    symbol = normalize_symbol_input(str(row.get("symbol") or ""))
    asset_class = _normalize_asset_class(str(row.get("asset_class") or ""))
    membership = row.get("membership") if isinstance(row.get("membership"), dict) else {}
    taxonomy = row.get("taxonomy") if isinstance(row.get("taxonomy"), dict) else {}
    security_type = str(membership.get("security_type") or "").strip().lower()
    listing_status = str(membership.get("listing_status") or "").strip().lower()
    if (
        not symbol
        or asset_class not in {"equity", "etf"}
        or listing_status not in {"active", "listed"}
        or security_type not in {"equity", "etf", "common-stock", "common stock"}
    ):
        return None
    exchange = str(membership.get("exchange") or row.get("exchange") or "US listed")
    mic = str(membership.get("mic") or row.get("mic") or "") or None
    cik = str(membership.get("cik") or "").zfill(10) if membership.get("cik") else None
    provider_sector = taxonomy.get("provider_sector")
    classification_conflict = bool(taxonomy.get("classification_conflict"))
    registry_source_url = str(membership.get("source_url") or "") or None
    taxonomy_source_url = str(taxonomy.get("source_url") or "") or None
    source_status = str(membership.get("source_status") or "official/listing")
    snapshot_status = str(materialization.get("read_status") or "unavailable")
    financial_snapshot = dict(row.get("financial_snapshot") or {})
    if financial_snapshot and not financial_snapshot.get("fetched_at"):
        financial_snapshot["fetched_at"] = (
            row.get("fetched_at")
            or materialization.get("created_at")
        )
    aliases = {symbol, symbol.replace("-", "."), symbol.replace(".", "-")}
    return {
        "symbol": symbol,
        "name": str(row.get("name") or symbol),
        "asset_class": asset_class,
        "exchange": exchange,
        "currency": "USD",
        "region": str(row.get("region") or row.get("country") or "United States"),
        "provider_symbol": symbol,
        "aliases": sorted(aliases),
        "registry_provider": str(membership.get("provider") or "materialized-market-snapshot"),
        "registry_source": "materialized Market Map identity",
        "registry_source_url": registry_source_url,
        "sector": str(taxonomy.get("sector") or row.get("sector") or "Unclassified"),
        "industry": str(taxonomy.get("industry") or row.get("industry") or "Unclassified"),
        "market_cap": _clean_number(row.get("market_cap")),
        "base_asset": None,
        "quote_asset": None,
        "source_status": source_status,
        "reviewed_at": str(
            membership.get("as_of")
            or materialization.get("created_at")
            or row.get("fetched_at")
            or REGISTRY_REVIEWED_AT
        ),
        "caveat": str(
            membership.get("caveat")
            or "Official listing identity is reconciled through the materialized Market Map snapshot."
        ),
        "data_gap": str(row.get("data_gap") or "") or None,
        "search_symbol": _alias_key(symbol),
        "listing_status": listing_status,
        "authoritative_security_master": False,
        "not_financial_advice": True,
        "identity_origin": "materialized-market-snapshot",
        "snapshot_status": snapshot_status,
        "snapshot_created_at": materialization.get("created_at"),
        "mic": mic,
        "cik": cik,
        "security_type": security_type,
        "sec_source_status": membership.get("sec_source_status"),
        "identity_conflict": bool(membership.get("identity_conflict")),
        "taxonomy_provider": taxonomy.get("provider"),
        "taxonomy_source_url": taxonomy_source_url,
        "taxonomy_source_status": taxonomy.get("source_status"),
        "classification_version": taxonomy.get("classification_version"),
        "classification_conflict": classification_conflict,
        "provider_sector": provider_sector,
        "market_map_context": {
            "symbol": symbol,
            "sector": taxonomy.get("sector") or row.get("sector"),
            "industry": taxonomy.get("industry") or row.get("industry"),
            "provider_sector": provider_sector,
            "classification_version": taxonomy.get("classification_version"),
            "classification_source_status": taxonomy.get("source_status"),
            "classification_conflict": classification_conflict,
            "taxonomy_authoritative": bool(taxonomy.get("taxonomy_authoritative")),
            "market_cap": _clean_number(row.get("market_cap")),
            "price": _clean_number(row.get("price")),
            "return_1d_pct": _clean_number(row.get("return_1d_pct")),
            "market_data_as_of": row.get("market_data_as_of"),
            "market_provider": row.get("provider"),
            "market_source_url": row.get("source_url"),
            "market_source_status": row.get("source_status"),
            "market_fetched_at": row.get("fetched_at"),
            "snapshot_status": snapshot_status,
            "snapshot_created_at": materialization.get("created_at"),
            "financial_snapshot": financial_snapshot,
            "factors": dict(row.get("factors") or {}),
            "caveat": row.get("caveat"),
            "data_gap": row.get("data_gap"),
        },
    }


def _merge_materialized_identity(
    materialized: dict[str, Any],
    static: dict[str, Any] | None,
) -> dict[str, Any]:
    if not static:
        return materialized
    merged = dict(materialized)
    merged["aliases"] = sorted(
        {
            *[str(value) for value in materialized.get("aliases") or []],
            *[str(value) for value in static.get("aliases") or []],
        }
    )
    static_industry = str(static.get("industry") or "")
    if static_industry and static_industry != "Unclassified":
        merged["industry"] = static_industry
        merged["market_map_context"] = {
            **dict(merged.get("market_map_context") or {}),
            "local_industry": static_industry,
            "local_taxonomy_provider": static.get("registry_provider"),
        }
    merged["local_registry_evidence"] = {
        "provider": static.get("registry_provider"),
        "source": static.get("registry_source"),
        "source_status": static.get("source_status"),
        "reviewed_at": static.get("reviewed_at"),
        "caveat": static.get("caveat"),
        "data_gap": static.get("data_gap"),
    }
    return merged


def _materialized_symbol_identities(
    *,
    snapshot_base_dir: str | Path | None = None,
) -> list[dict[str, Any]]:
    from .market_snapshot_store import read_market_snapshot

    root = Path(
        snapshot_base_dir
        or os.getenv("MARKET_SNAPSHOT_DIR")
        or Path("data") / "cache" / "market_snapshots"
    ).expanduser().resolve()
    manifest = root / "latest.json"
    try:
        stat = manifest.stat()
        cache_key = (str(root), stat.st_mtime_ns, stat.st_size)
    except OSError:
        cache_key = (str(root), -1, -1)
    with _MATERIALIZED_IDENTITY_CACHE_LOCK:
        cached = _MATERIALIZED_IDENTITY_CACHE.get(cache_key)
    if cached is not None:
        return [dict(row) for row in cached]

    snapshot = read_market_snapshot(base_dir=snapshot_base_dir)
    data = snapshot.get("data") if isinstance(snapshot.get("data"), dict) else {}
    materialization = data.get("materialization") if isinstance(data.get("materialization"), dict) else {}
    rows = data.get("instruments") if isinstance(data.get("instruments"), list) else []
    output = []
    for row in rows:
        identity = _materialized_identity_from_row(
            row,
            materialization=materialization,
        ) if isinstance(row, dict) else None
        if identity:
            output.append(identity)
    with _MATERIALIZED_IDENTITY_CACHE_LOCK:
        _MATERIALIZED_IDENTITY_CACHE.clear()
        _MATERIALIZED_IDENTITY_CACHE[cache_key] = [dict(row) for row in output]
    return output


def _materialized_symbol_identity(
    symbol: str,
    *,
    snapshot_base_dir: str | Path | None = None,
) -> dict[str, Any] | None:
    normalized = normalize_symbol_input(symbol)
    if not normalized:
        return None
    return next(
        (
            dict(row)
            for row in _materialized_symbol_identities(
                snapshot_base_dir=snapshot_base_dir,
            )
            if row.get("symbol") == normalized
        ),
        None,
    )


def symbol_identities(
    *,
    include_materialized: bool = False,
    snapshot_base_dir: str | Path | None = None,
) -> list[dict[str, Any]]:
    static_rows = _static_symbol_identities()
    if not include_materialized:
        return static_rows
    static_by_symbol = {row["symbol"]: row for row in static_rows}
    merged_by_symbol = dict(static_by_symbol)
    for row in _materialized_symbol_identities(snapshot_base_dir=snapshot_base_dir):
        merged_by_symbol[row["symbol"]] = _merge_materialized_identity(
            row,
            static_by_symbol.get(row["symbol"]),
        )
    return sorted(
        merged_by_symbol.values(),
        key=lambda row: (str(row.get("asset_class")), str(row.get("symbol"))),
    )


def _identity_index(
    *,
    include_materialized: bool = False,
    snapshot_base_dir: str | Path | None = None,
) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    global _STATIC_IDENTITY_INDEX_CACHE
    if not include_materialized:
        with _STATIC_IDENTITY_LOCK:
            if _STATIC_IDENTITY_INDEX_CACHE is not None:
                return _STATIC_IDENTITY_INDEX_CACHE
    identities = symbol_identities(
        include_materialized=include_materialized,
        snapshot_base_dir=snapshot_base_dir,
    )
    by_symbol = {row["symbol"]: row for row in identities}
    aliases: dict[str, str] = {}
    for row in identities:
        for alias in [row["symbol"], *row.get("aliases", [])]:
            aliases.setdefault(_alias_key(str(alias)), row["symbol"])
    if not include_materialized:
        with _STATIC_IDENTITY_LOCK:
            _STATIC_IDENTITY_INDEX_CACHE = (by_symbol, aliases)
    return by_symbol, aliases


def resolve_symbol(
    value: str,
    *,
    asset_class: str | None = None,
    include_materialized: bool = True,
    snapshot_base_dir: str | Path | None = None,
) -> dict[str, Any] | None:
    normalized = normalize_symbol_input(value)
    if not normalized:
        return None
    static_by_symbol, static_aliases = _identity_index()
    canonical = static_aliases.get(_alias_key(normalized)) or normalized
    materialized = (
        _materialized_symbol_identity(
            canonical,
            snapshot_base_dir=snapshot_base_dir,
        )
        if include_materialized
        else None
    )
    if materialized:
        identity = _merge_materialized_identity(
            materialized,
            static_by_symbol.get(canonical),
        )
    else:
        identity = static_by_symbol.get(canonical)
    requested_class = _normalize_asset_class(asset_class)
    if identity is None or (requested_class and identity["asset_class"] != requested_class):
        return None
    return dict(identity)


def search_symbols(
    query: str = "",
    *,
    asset_class: str | None = None,
    limit: int = 8,
    include_materialized: bool = False,
    snapshot_base_dir: str | Path | None = None,
) -> list[dict[str, Any]]:
    normalized_class = _normalize_asset_class(asset_class)
    limit = max(1, min(MAX_SEARCH_LIMIT, int(limit or 8)))
    identities = [
        row
        for row in symbol_identities(
            include_materialized=include_materialized,
            snapshot_base_dir=snapshot_base_dir,
        )
        if not normalized_class or row["asset_class"] == normalized_class
    ]
    if not str(query or "").strip():
        return identities[:limit]
    safe_query = normalize_search_query(query)
    if not safe_query:
        return []
    query_key = _alias_key(safe_query)
    query_words = safe_query.lower().split()

    def score(row: dict[str, Any]) -> tuple[int, int, str]:
        symbol = str(row["symbol"])
        symbol_key = _alias_key(symbol)
        aliases = {_alias_key(str(item)) for item in row.get("aliases", [])}
        name = str(row.get("name") or "").lower()
        if query_key == symbol_key:
            rank = 0
        elif query_key in aliases:
            rank = 1
        elif symbol_key.startswith(query_key):
            rank = 2
        elif any(word and name.startswith(word) for word in query_words):
            rank = 3
        elif all(word in f"{symbol.lower()} {name}" for word in query_words):
            rank = 4
        else:
            rank = 99
        class_rank = {"equity": 0, "etf": 1, "crypto": 2}.get(str(row["asset_class"]), 9)
        return rank, class_rank, symbol

    ranked = sorted((row for row in identities if score(row)[0] < 99), key=score)
    return ranked[:limit]


def build_symbol_directory_contract(
    *,
    query: str = "",
    asset_class: str | None = None,
    limit: int = MAX_SEARCH_LIMIT,
    include_materialized: bool = False,
    snapshot_base_dir: str | Path | None = None,
) -> dict[str, Any]:
    all_rows = symbol_identities(
        include_materialized=include_materialized,
        snapshot_base_dir=snapshot_base_dir,
    )
    rows = (
        search_symbols(
            query,
            asset_class=asset_class,
            limit=limit,
            include_materialized=include_materialized,
            snapshot_base_dir=snapshot_base_dir,
        )
        if query or asset_class
        else all_rows
    )
    counts = {
        current: sum(1 for row in all_rows if row["asset_class"] == current)
        for current in ("equity", "etf", "crypto")
    }
    return {
        "symbol_directory_version": SYMBOL_DIRECTORY_VERSION,
        "workspace": "symbol-directory",
        "identities": rows,
        "asset_class_counts": counts,
        "search_contract": {
            "max_query_length": MAX_QUERY_LENGTH,
            "max_result_limit": MAX_SEARCH_LIMIT,
            "default_limit": 8,
            "ranking": ["exact-symbol", "exact-alias", "symbol-prefix", "name-prefix", "name-token"],
            "allowed_characters": "letters, numbers, spaces, dot, hyphen, underscore, slash, equals",
        },
        "provider_capabilities": PROVIDER_CAPABILITIES,
        "readiness": {
            "registry_row_count": len(all_rows),
            "result_count": len(rows),
            "bounded_registry": True,
            "materialized_identity_activation": include_materialized,
            "materialized_identity_count": sum(
                row.get("identity_origin") == "materialized-market-snapshot"
                for row in all_rows
            ),
            "authoritative_security_master_claimed": False,
            "external_rows_copied": False,
            "live_listing_claimed": False,
            "non_advisory": True,
        },
        "summary": {
            "workspace": "symbol-directory",
            "registry_row_count": len(all_rows),
            "result_count": len(rows),
            "query": normalize_search_query(query) if query else "",
            "asset_class": _normalize_asset_class(asset_class) or "all",
            "source_status": "static/proxy",
            "non_advisory": True,
        },
        "source_register": [
            {
                "provider": "phase5i.local_equity_registry",
                "source": "static/index_constituents/sp500.csv",
                "source_url": None,
                "source_status": "static/proxy",
                "fetched_at": REGISTRY_REVIEWED_AT,
                "row_count": counts["equity"],
                "caveat": "Reviewed local taxonomy; membership and market cap are not claimed current.",
                "data_gap": "Authoritative security master unavailable.",
                "not_financial_advice": True,
            },
            {
                "provider": "phase5m.reviewed_asset_registry",
                "source": "project-native ETF and crypto pair identities",
                "source_url": "https://fapi.binance.com/fapi/v1/exchangeInfo",
                "source_status": "static/proxy",
                "fetched_at": REGISTRY_REVIEWED_AT,
                "row_count": counts["etf"] + counts["crypto"],
                "caveat": "Static reviewed identities; successful provider responses are required for live claims.",
                "data_gap": "Current listing status is not continuously synchronized.",
                "not_financial_advice": True,
            },
            *(
                [
                    {
                        "provider": "market_snapshot_store",
                        "source": "materialized Nasdaq/SEC-reconciled identities",
                        "source_url": None,
                        "source_status": "cached/materialized",
                        "fetched_at": max(
                            (
                                str(row.get("snapshot_created_at") or "")
                                for row in all_rows
                                if row.get("identity_origin") == "materialized-market-snapshot"
                            ),
                            default=None,
                        ),
                        "row_count": sum(
                            row.get("identity_origin") == "materialized-market-snapshot"
                            for row in all_rows
                        ),
                        "caveat": "Materialized identities retain official listing and SEC evidence but do not form a complete security master.",
                        "data_gap": "Snapshot age and provider classification remain separate from listing identity.",
                        "not_financial_advice": True,
                    }
                ]
                if include_materialized
                else []
            ),
        ],
    }


def _normalize_asset_class(value: str | None) -> str | None:
    current = str(value or "").strip().lower()
    aliases = {"crypto_pair": "crypto", "equity": "equity", "etf": "etf", "crypto": "crypto"}
    return aliases.get(current)


def _capability_for(asset_class: str) -> dict[str, Any]:
    return next(row for row in PROVIDER_CAPABILITIES if row["asset_class"] == asset_class)


def _capability_error(asset_class: str, interval: str, range_name: str) -> str | None:
    capability = _capability_for(asset_class)
    if interval not in capability["intervals"]:
        return "unsupported-interval"
    if range_name not in capability["ranges_by_interval"].get(interval, []):
        return "unsupported-range"
    return None


def history_cache_key(asset_class: str, symbol: str, interval: str, range_name: str) -> str:
    return f"symbol-workstation:{asset_class}:{symbol}:{interval}:{range_name}"


def build_symbol_capability_plan(
    identity: dict[str, Any],
    *,
    interval: str,
    range_name: str,
    compare: str | None = None,
) -> dict[str, Any]:
    capability = _capability_for(str(identity["asset_class"]))
    is_equity = identity["asset_class"] == "equity"
    capability_error = _capability_error(
        str(identity["asset_class"]),
        interval,
        range_name,
    )
    maximum_provider_calls = (
        0
        if capability_error
        else 12
        if is_equity and compare
        else 11
        if is_equity
        else 3
    )
    return {
        "plan_version": "symbol_capability_plan.v1",
        "symbol": identity["symbol"],
        "asset_class": identity["asset_class"],
        "interval": interval,
        "range": range_name,
        "cache_partition": history_cache_key(
            str(identity["asset_class"]),
            str(identity["symbol"]),
            interval,
            range_name,
        ),
        "history": {
            "provider": capability["provider"],
            "maximum_provider_calls": 1,
            "ttl_seconds": capability["ttl_seconds"],
            "stale_seconds": capability["stale_seconds"],
        },
        "financial_and_sec": {
            "maximum_provider_calls": 7 if is_equity else 1,
            "applicable": identity["asset_class"] in {"equity", "etf"},
        },
        "news": {
            "maximum_provider_calls": 3 if is_equity else 1,
            "exact_title_or_identity_match_required": True,
        },
        "comparison": {
            "symbol": compare,
            "maximum_provider_calls": 1 if compare else 0,
        },
        "request_supported": capability_error is None,
        "capability_error": capability_error,
        "maximum_provider_calls": maximum_provider_calls,
        "selected_symbol_only": True,
        "broad_universe_rebuild": False,
        "per_universe_symbol_fanout": False,
        "same_symbol_lkg_only": True,
        "no_cross_symbol_fallback": True,
        "not_financial_advice": True,
    }


def _load_history_cache(key: str) -> RuntimeCacheRecord | None:
    return load_runtime_cache_record(key)


def _save_history_cache(record: RuntimeCacheRecord) -> None:
    save_runtime_cache_record(record)


def _frame_records(frame: Any, *, crypto: bool = False) -> list[dict[str, Any]]:
    if frame is None:
        return []
    if hasattr(frame, "to_dict"):
        records = frame.to_dict(orient="records")
    elif isinstance(frame, list):
        records = frame
    else:
        return []
    output = []
    for row in records:
        if not isinstance(row, dict):
            continue
        date_value = row.get("open_time") if crypto else row.get("date")
        if hasattr(date_value, "isoformat"):
            date_value = date_value.isoformat()
        output.append(
            {
                "date": str(date_value or ""),
                "open": _clean_number(row.get("open")),
                "high": _clean_number(row.get("high")),
                "low": _clean_number(row.get("low")),
                "close": _clean_number(row.get("close")),
                "volume": _clean_number(row.get("volume")),
            }
        )
    return [row for row in output if row["date"] and row["close"] is not None]


def _fetch_provider_history(
    identity: dict[str, Any],
    interval: str,
    range_name: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if identity["asset_class"] in {"equity", "etf"}:
        from .market_data import fetch_price_history

        frame, status = fetch_price_history(identity["provider_symbol"], period=range_name, interval=interval)
        rows = _frame_records(frame)
        if not rows or not status.ok:
            raise RuntimeError(status.error or "Provider returned no usable equity/ETF history.")
        return rows, {
            "provider": "yfinance",
            "source": identity["provider_symbol"],
            "source_url": f"https://finance.yahoo.com/quote/{quote(identity['provider_symbol'])}",
            "fetched_at": status.fetched_at.isoformat(),
            "cached": bool(status.is_cached),
        }

    from .crypto_derivatives import get_binance_klines

    frame, status = get_binance_klines(
        identity["provider_symbol"],
        interval=interval,
        limit=_crypto_limit(interval, range_name),
    )
    rows = _frame_records(frame, crypto=True)
    if not rows or not status.ok:
        raise RuntimeError(status.error or "Provider returned no usable crypto history.")
    return rows, {
        "provider": "Binance USD-M Futures",
        "source": "Binance public klines",
        "source_url": f"https://fapi.binance.com/fapi/v1/klines?symbol={quote(identity['provider_symbol'])}&interval={quote(interval)}",
        "fetched_at": status.fetched_at.isoformat(),
        "cached": bool(status.is_cached),
    }


def _crypto_limit(interval: str, range_name: str) -> int:
    interval_seconds = {"15m": 900, "1h": 3600, "4h": 14_400, "1d": 86_400}[interval]
    range_seconds = {
        "1d": 86_400,
        "5d": 432_000,
        "1mo": 2_592_000,
        "3mo": 7_776_000,
        "6mo": 15_552_000,
        "1y": 31_536_000,
    }[range_name]
    return max(24, min(1500, int(range_seconds / interval_seconds) + 1))


def _fixture_history(identity: dict[str, Any]) -> list[dict[str, Any]]:
    digest = hashlib.sha256(identity["symbol"].encode("utf-8")).digest()
    if identity["asset_class"] == "crypto":
        base_price = 20 + int.from_bytes(digest[:2], "big") % 90_000
    else:
        base_price = 25 + int.from_bytes(digest[:2], "big") % 550
    end = datetime(2026, 6, 21, tzinfo=timezone.utc)
    rows = []
    price = float(base_price)
    for index in range(48):
        drift = ((digest[index % len(digest)] / 255) - 0.48) * 0.035
        open_price = price
        close = max(0.01, open_price * (1 + drift))
        high = max(open_price, close) * (1.006 + (digest[(index + 5) % len(digest)] / 255) * 0.012)
        low = min(open_price, close) * (0.994 - (digest[(index + 9) % len(digest)] / 255) * 0.008)
        rows.append(
            {
                "date": (end - timedelta(days=47 - index)).date().isoformat(),
                "open": round(open_price, 4),
                "high": round(high, 4),
                "low": round(low, 4),
                "close": round(close, 4),
                "volume": float(100_000 + digest[(index + 13) % len(digest)] * 11_000),
            }
        )
        price = close
    return rows


def _fixture_history_fallback(
    identity: dict[str, Any],
    *,
    status: str,
    data_gap: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows = _fixture_history(identity)
    source_url = f"https://example.test/phase-5t/{quote(identity['symbol'])}"
    return _annotate_history(
        rows,
        identity=identity,
        provider="phase5t.symbol_fixture_fallback",
        source_url=source_url,
        fetched_at=FIXTURE_FETCHED_AT,
        source_status="fixture",
        caveat="Deterministic symbol-seeded fallback keeps the workstation renderable; values are synthetic and not live market observations.",
        data_gap=data_gap,
    ), {
        "provider": "phase5t.symbol_fixture_fallback",
        "source_url": source_url,
        "fetched_at": FIXTURE_FETCHED_AT,
        "source_status": "fixture",
        "status": status,
        "effective_interval": "1d",
        "effective_range": "3mo",
        "data_gap": data_gap,
    }


def _unavailable_history(
    identity: dict[str, Any],
    *,
    status: str,
    data_gap: str,
    interval: str,
    range_name: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    capability = _capability_for(identity["asset_class"])
    return [], {
        "provider": capability["provider"],
        "source_url": None,
        "fetched_at": None,
        "source_status": "unavailable",
        "status": status,
        "effective_interval": interval,
        "effective_range": range_name,
        "data_gap": data_gap,
    }


def _annotate_history(
    rows: list[dict[str, Any]],
    *,
    identity: dict[str, Any],
    provider: str,
    source_url: str | None,
    fetched_at: str,
    source_status: str,
    caveat: str,
    data_gap: str | None,
) -> list[dict[str, Any]]:
    return [
        {
            **row,
            "symbol": identity["symbol"],
            "asset_class": identity["asset_class"],
            "provider": provider,
            "source_url": source_url,
            "fetched_at": fetched_at,
            "freshness": source_status,
            "source_status": source_status,
            "caveat": caveat,
            "data_gap": data_gap,
            "not_financial_advice": True,
        }
        for row in rows
    ]


def _history_for_request(
    identity: dict[str, Any],
    interval: str,
    range_name: str,
    runtime_mode: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if runtime_mode == "fixture":
        rows = _fixture_history(identity)
        return _annotate_history(
            rows,
            identity=identity,
            provider="phase5m.symbol_fixture",
            source_url=f"https://example.test/phase-5m/{quote(identity['symbol'])}",
            fetched_at=FIXTURE_FETCHED_AT,
            source_status="fixture",
            caveat="Deterministic symbol-seeded fixture; values are synthetic and not market observations.",
            data_gap="Fixture effective capability is 1d / 3mo.",
        ), {
            "provider": "phase5m.symbol_fixture",
            "source_url": f"https://example.test/phase-5m/{quote(identity['symbol'])}",
            "fetched_at": FIXTURE_FETCHED_AT,
            "source_status": "fixture",
            "status": "fixture",
            "effective_interval": "1d",
            "effective_range": "3mo",
        }

    capability = _capability_for(identity["asset_class"])
    key = history_cache_key(identity["asset_class"], identity["symbol"], interval, range_name)
    cached = _load_history_cache(key)
    now = _utc_now()
    ttl_seconds = int(capability["ttl_seconds"])
    if cached is not None:
        age = cached.age_seconds(now)
        if age <= ttl_seconds:
            rows = _annotate_history(
                list(cached.data or []),
                identity=identity,
                provider=cached.provider,
                source_url=cached.source_url,
                fetched_at=cached.fetched_at_iso,
                source_status="cached",
                caveat="Fresh public history served from the symbol/interval/range cache.",
                data_gap=None,
            )
            return rows, {
                "provider": cached.provider,
                "source_url": cached.source_url,
                "fetched_at": cached.fetched_at_iso,
                "source_status": "cached",
                "status": "cached",
                "effective_interval": interval,
                "effective_range": range_name,
            }
        if runtime_mode == "cache":
            if age <= HISTORY_STALE_SECONDS:
                rows = _annotate_history(
                    list(cached.data or []),
                    identity=identity,
                    provider=cached.provider,
                    source_url=cached.source_url,
                    fetched_at=cached.fetched_at_iso,
                    source_status="stale",
                    caveat="Cache-only mode retained an older public history snapshot.",
                    data_gap="Live refresh was not attempted in cache mode.",
                )
                return rows, {
                    "provider": cached.provider,
                    "source_url": cached.source_url,
                    "fetched_at": cached.fetched_at_iso,
                    "source_status": "stale",
                    "status": "stale",
                    "effective_interval": interval,
                    "effective_range": range_name,
                }
            cached = None

    if runtime_mode == "cache":
        return _unavailable_history(
            identity,
            status="cache-miss",
            data_gap="No same-symbol/interval/range cache record is available; live refresh was not attempted.",
            interval=interval,
            range_name=range_name,
        )

    try:
        rows, metadata = _fetch_provider_history(identity, interval, range_name)
        fetched_at = _parse_datetime(metadata.get("fetched_at"))
        record = RuntimeCacheRecord(
            key=key,
            data=rows,
            source=str(metadata.get("source") or identity["symbol"]),
            provider=str(metadata.get("provider") or capability["provider"]),
            source_url=str(metadata.get("source_url") or ""),
            fetched_at=fetched_at,
        )
        _save_history_cache(record)
        annotated = _annotate_history(
            rows,
            identity=identity,
            provider=record.provider,
            source_url=record.source_url,
            fetched_at=record.fetched_at_iso,
            source_status="live/fresh",
            caveat="Free-first public history; inspect provider, interval, and fetched time.",
            data_gap=None,
        )
        return annotated, {
            "provider": record.provider,
            "source_url": record.source_url,
            "fetched_at": record.fetched_at_iso,
            "source_status": "live/fresh",
            "status": "ready",
            "effective_interval": interval,
            "effective_range": range_name,
        }
    except Exception as exc:
        if cached is not None and cached.age_seconds(now) <= HISTORY_STALE_SECONDS:
            message = str(exc)
            rows = _annotate_history(
                list(cached.data or []),
                identity=identity,
                provider=cached.provider,
                source_url=cached.source_url,
                fetched_at=cached.fetched_at_iso,
                source_status="stale",
                caveat="Live refresh failed; the prior public history snapshot was retained.",
                data_gap=message,
            )
            return rows, {
                "provider": cached.provider,
                "source_url": cached.source_url,
                "fetched_at": cached.fetched_at_iso,
                "source_status": "stale",
                "status": "stale",
                "effective_interval": interval,
                "effective_range": range_name,
                "data_gap": message,
            }
        return _unavailable_history(
            identity,
            status="provider-error",
            data_gap=f"Live provider refresh failed and no same-symbol last-known-good record is available: {exc}",
            interval=interval,
            range_name=range_name,
        )


def _parse_datetime(value: Any) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except Exception:
        return _utc_now()


def _quote(history: list[dict[str, Any]]) -> dict[str, Any]:
    closes = [float(row["close"]) for row in history if row.get("close") is not None]
    if not closes:
        return {"last_price": None, "change": None, "change_pct": None}
    previous = closes[-2] if len(closes) > 1 else closes[-1]
    change = closes[-1] - previous
    change_pct = change / previous * 100 if previous else None
    return {
        "last_price": closes[-1],
        "change": round(change, 6),
        "change_pct": round(change_pct, 6) if change_pct is not None else None,
    }


def _chart_spec(identity: dict[str, Any], history: list[dict[str, Any]], state: dict[str, Any]) -> dict[str, Any]:
    return {
        "chart_id": f"{identity['symbol']}.universal-price",
        "chart_type": "price-line",
        "title": f"{identity['symbol']} Price History",
        "symbol": identity["symbol"],
        "interval": state["effective_interval"],
        "range": state["effective_range"],
        "timezone": "UTC",
        "units": identity["currency"],
        "series": [
            {
                "name": "close",
                "points": [{"x": row["date"], "y": row["close"]} for row in history if row.get("close") is not None],
            }
        ],
        "provider": state["provider"],
        "source_status": state["source_status"],
        "fetched_at": state.get("fetched_at"),
        "caveat": history[0]["caveat"] if history else "No plottable provider history is available.",
        "data_gap": state.get("data_gap"),
        "not_financial_advice": True,
    }


def _workstation(
    identity: dict[str, Any],
    interval: str,
    range_name: str,
    runtime_mode: str,
) -> dict[str, Any]:
    capability_error = _capability_error(identity["asset_class"], interval, range_name)
    if capability_error:
        state = {
            "provider": _capability_for(identity["asset_class"])["provider"],
            "source_url": None,
            "fetched_at": None,
            "source_status": "unavailable",
            "status": capability_error,
            "effective_interval": None,
            "effective_range": None,
            "data_gap": f"{interval}/{range_name} is outside the declared provider capability matrix.",
        }
        history: list[dict[str, Any]] = []
    else:
        history, state = _history_for_request(identity, interval, range_name, runtime_mode)

    market_context = identity.get("market_map_context") if isinstance(identity.get("market_map_context"), dict) else {}
    history_quote = _quote(history)
    materialized_quote = not history and _clean_number(market_context.get("price")) is not None
    quote_row = {
        **(
            {
                "last_price": _clean_number(market_context.get("price")),
                "change": None,
                "change_pct": _clean_number(market_context.get("return_1d_pct")),
            }
            if materialized_quote
            else history_quote
        ),
        "symbol": identity["symbol"],
        "currency": identity["currency"],
        "provider": market_context.get("market_provider") if materialized_quote else state["provider"],
        "source_url": market_context.get("market_source_url") if materialized_quote else state.get("source_url"),
        "fetched_at": market_context.get("market_fetched_at") if materialized_quote else state.get("fetched_at"),
        "source_status": identity.get("snapshot_status") if materialized_quote else state["source_status"],
        "freshness": identity.get("snapshot_status") if materialized_quote else state["source_status"],
        "caveat": (
            "Same-symbol delayed Market Map observation retained while on-demand history is unavailable."
            if materialized_quote
            else history[0]["caveat"]
            if history
            else "No verified quote could be derived."
        ),
        "data_gap": state.get("data_gap"),
        "not_financial_advice": True,
    }
    source_register = [
        {
            "provider": identity["registry_provider"],
            "source": identity["registry_source"],
            "source_url": identity.get("registry_source_url"),
            "source_status": identity["source_status"],
            "fetched_at": identity["reviewed_at"],
            "row_count": 1,
            "caveat": identity["caveat"],
            "data_gap": identity["data_gap"],
            "not_financial_advice": True,
        },
        *(
            [
                {
                    "provider": identity.get("taxonomy_provider"),
                    "source": "Market Map classification",
                    "source_url": identity.get("taxonomy_source_url"),
                    "source_status": identity.get("taxonomy_source_status"),
                    "fetched_at": identity.get("snapshot_created_at"),
                    "row_count": 1,
                    "caveat": "Provider classification is separate from official listing identity and is not claimed as GICS.",
                    "data_gap": (
                        "Classification conflicts are preserved."
                        if identity.get("classification_conflict")
                        else None
                    ),
                    "not_financial_advice": True,
                }
            ]
            if identity.get("identity_origin") == "materialized-market-snapshot"
            else []
        ),
        *(
            [
                {
                    "provider": market_context.get("market_provider"),
                    "source": f"{identity['symbol']} delayed Market Map observation",
                    "source_url": market_context.get("market_source_url"),
                    "source_status": identity.get("snapshot_status") or market_context.get("market_source_status"),
                    "fetched_at": market_context.get("market_fetched_at"),
                    "row_count": 1,
                    "caveat": "Materialized same-symbol quote context is independent from the on-demand OHLCV history.",
                    "data_gap": market_context.get("data_gap"),
                    "not_financial_advice": True,
                }
            ]
            if market_context.get("market_provider")
            else []
        ),
        {
            "provider": state["provider"],
            "source": f"{identity['symbol']} {interval}/{range_name} history",
            "source_url": state.get("source_url"),
            "source_status": state["source_status"],
            "fetched_at": state.get("fetched_at"),
            "row_count": len(history),
            "caveat": quote_row["caveat"],
            "data_gap": state.get("data_gap"),
            "not_financial_advice": True,
        },
        {
            "provider": "symbol-scoped-news",
            "source": identity["symbol"],
            "source_url": None,
            "source_status": "unavailable",
            "fetched_at": None,
            "row_count": 0,
            "caveat": "No broad headline is relabeled as symbol-specific without an exact symbol/name match.",
            "data_gap": "A verified symbol-scoped news match is unavailable in this slice.",
            "not_financial_advice": True,
        },
    ]
    fundamentals = {
        "availability": "taxonomy-only" if identity["asset_class"] in {"equity", "etf"} else "not_applicable",
        "sector": identity.get("sector"),
        "industry": identity.get("industry"),
        "market_cap_reference": identity.get("market_cap"),
        "provider": identity["registry_provider"],
        "source_status": identity["source_status"],
        "fetched_at": identity["reviewed_at"],
        "caveat": "Static taxonomy context only; current statements, estimates, holdings, and valuation are not inferred.",
        "data_gap": "Provider-backed fundamentals are unavailable." if identity["asset_class"] in {"equity", "etf"} else None,
        "not_financial_advice": True,
    }
    crypto_context = {
        "availability": "pair-context" if identity["asset_class"] == "crypto" else "not_applicable",
        "base_asset": identity.get("base_asset"),
        "quote_asset": identity.get("quote_asset"),
        "derivatives_claimed": bool(identity["asset_class"] == "crypto" and history),
        "provider": state["provider"] if identity["asset_class"] == "crypto" else "not_applicable",
        "source_status": state["source_status"] if identity["asset_class"] == "crypto" else "not_applicable",
        "fetched_at": state.get("fetched_at") if identity["asset_class"] == "crypto" else None,
        "caveat": "Price history does not imply liquidation, positioning, or account-flow coverage.",
        "data_gap": "Funding, open interest, and flow panels require separate verified rows." if identity["asset_class"] == "crypto" else None,
        "not_financial_advice": True,
    }
    unavailable = [row for row in source_register if row["source_status"] == "unavailable"]
    return {
        "identity": identity,
        "market_map_context": dict(identity.get("market_map_context") or {}),
        "capability_plan": build_symbol_capability_plan(
            identity,
            interval=interval,
            range_name=range_name,
        ),
        "request": {
            "symbol": identity["symbol"],
            "asset_class": identity["asset_class"],
            "requested_interval": interval,
            "requested_range": range_name,
            "effective_interval": state.get("effective_interval"),
            "effective_range": state.get("effective_range"),
            "runtime_mode": runtime_mode,
        },
        "quote": quote_row,
        "history": history,
        "chart_specs": [_chart_spec(identity, history, state)],
        "fundamentals": fundamentals,
        "crypto_context": crypto_context,
        "news": [],
        "source_register": source_register,
        "unavailable_sources": unavailable,
        "summary": {
            "symbol": identity["symbol"],
            "name": identity["name"],
            "asset_class": identity["asset_class"],
            "status": state["status"],
            "source_status": state["source_status"],
            "fetched_at": state.get("fetched_at"),
            "history_row_count": len(history),
            "provider": state["provider"],
            "runtime_mode": runtime_mode,
            "non_advisory": True,
            "broker_execution_added": False,
        },
        "caveat": "Universal Symbol Workstation is source-aware read-only research context.",
    }


def build_symbol_workstation_contract(
    symbol: str,
    *,
    asset_class: str | None = None,
    interval: str = "1d",
    range_name: str = "3mo",
    runtime_mode: str = "fixture",
    snapshot_base_dir: str | Path | None = None,
) -> dict[str, Any]:
    requested_symbol = normalize_symbol_input(symbol)
    normalized_class = _normalize_asset_class(asset_class)
    normalized_interval = str(interval or "1d").strip().lower()[:8]
    normalized_range = str(range_name or "3mo").strip().lower()[:8]
    normalized_mode = runtime_mode if runtime_mode in {"fixture", "cache", "live-if-available"} else "fixture"
    identity = (
        resolve_symbol(
            requested_symbol,
            asset_class=normalized_class,
            include_materialized=False,
        )
        if normalized_mode == "fixture"
        else None
    ) or resolve_symbol(
        requested_symbol,
        asset_class=normalized_class,
        snapshot_base_dir=snapshot_base_dir,
    )
    if identity is None:
        by_any_class = (
            resolve_symbol(
                requested_symbol,
                include_materialized=False,
            )
            if normalized_mode == "fixture"
            else None
        ) or resolve_symbol(
            requested_symbol,
            snapshot_base_dir=snapshot_base_dir,
        )
        status = "asset-class-mismatch" if by_any_class is not None and normalized_class else "unknown-symbol"
        return {
            "symbol_workstation_version": SYMBOL_WORKSTATION_VERSION,
            "workspace": "symbol-workstation",
            "workstations": [],
            "capabilities": PROVIDER_CAPABILITIES,
            "readiness": {
                "supported": False,
                "status": status,
                "cross_symbol_fixture_fallback": False,
                "non_advisory": True,
            },
            "summary": {
                "workspace": "symbol-workstation",
                "symbol": requested_symbol or str(symbol or "")[:MAX_SYMBOL_LENGTH],
                "asset_class": normalized_class or "unknown",
                "status": status,
                "source_status": "unavailable",
                "workstation_count": 0,
                "non_advisory": True,
            },
            "source_register": [],
            "unavailable_sources": [
                {
                    "provider": "symbol-directory",
                    "source_status": "unavailable",
                    "availability": "unavailable",
                    "error": status,
                    "recommended_action": "Search the bounded symbol directory and open an exact supported identity.",
                    "not_financial_advice": True,
                }
            ],
        }
    workstation = _workstation(identity, normalized_interval, normalized_range, normalized_mode)
    return {
        "symbol_workstation_version": SYMBOL_WORKSTATION_VERSION,
        "workspace": "symbol-workstation",
        "workstations": [workstation],
        "capabilities": PROVIDER_CAPABILITIES,
        "readiness": {
            "supported": True,
            "status": workstation["summary"]["status"],
            "cross_symbol_fixture_fallback": False,
            "cache_partitioned_by_symbol_interval_range": True,
            "non_advisory": True,
        },
        "summary": {
            "workspace": "symbol-workstation",
            **workstation["summary"],
            "workstation_count": 1,
        },
        "source_register": workstation["source_register"],
        "unavailable_sources": workstation["unavailable_sources"],
    }


def build_symbol_workstation_fixture_catalog() -> dict[str, Any]:
    workstations = [
        _workstation(identity, "1d", "3mo", "fixture")
        for identity in symbol_identities(include_materialized=False)
    ]
    source_register = build_symbol_directory_contract(include_materialized=False)["source_register"]
    return {
        "symbol_workstation_version": SYMBOL_WORKSTATION_VERSION,
        "workspace": "symbol-workstation",
        "workstations": workstations,
        "capabilities": PROVIDER_CAPABILITIES,
        "readiness": {
            "supported": True,
            "status": "fixture-catalog",
            "cross_symbol_fixture_fallback": False,
            "cache_partitioned_by_symbol_interval_range": True,
            "fixture_row_count": len(workstations),
            "non_advisory": True,
        },
        "summary": {
            "workspace": "symbol-workstation",
            "status": "fixture-catalog",
            "source_status": "fixture",
            "workstation_count": len(workstations),
            "non_advisory": True,
            "broker_execution_added": False,
        },
        "source_register": source_register,
        "unavailable_sources": [],
    }
