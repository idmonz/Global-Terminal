from __future__ import annotations

import csv
import io
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any

from .data_status import DataResult
from .runtime_cache import fetch_text_with_cache


NASDAQ_DIRECTORY_VERSION = "nasdaq_symbol_directory.v1"
NASDAQ_LISTED_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
OTHER_LISTED_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"
DIRECTORY_TTL_SECONDS = 21_600

_NASDAQ_MARKET_CATEGORY = {
    "Q": ("NASDAQ Global Select", "XNAS"),
    "G": ("NASDAQ Global Market", "XNAS"),
    "S": ("NASDAQ Capital Market", "XNAS"),
}
_OTHER_EXCHANGE = {
    "A": ("NYSE American", "XASE"),
    "N": ("NYSE", "XNYS"),
    "P": ("NYSE Arca", "ARCX"),
    "Z": ("Cboe BZX", "BATS"),
    "V": ("IEX", "IEXG"),
}
_FOOTER_PATTERN = re.compile(r"File Creation Time:\s*(\d{2})(\d{2})(\d{4})(\d{2}):?(\d{2})", re.IGNORECASE)


def _clean_symbol(value: Any) -> str:
    return str(value or "").strip().upper().replace(".", "-")


def _directory_as_of(text: str) -> str | None:
    match = _FOOTER_PATTERN.search(text)
    if not match:
        return None
    month, day, year, hour, minute = (int(value) for value in match.groups())
    try:
        return datetime(year, month, day, hour, minute).isoformat()
    except ValueError:
        return None


def parse_nasdaq_symbol_directory(
    text: str,
    *,
    directory: str,
    source_url: str,
    fetched_at: str,
) -> dict[str, Any]:
    """Normalize official listing identity without claiming index membership or taxonomy."""
    reader = csv.DictReader(io.StringIO(text), delimiter="|")
    rows: list[dict[str, Any]] = []
    directory_as_of = _directory_as_of(text)
    for raw in reader:
        first_value = str(next(iter(raw.values()), "") or "")
        if first_value.lower().startswith("file creation time"):
            continue
        test_issue = str(raw.get("Test Issue") or "").strip().upper()
        if test_issue == "Y":
            continue
        if directory == "nasdaq-listed":
            symbol = _clean_symbol(raw.get("Symbol"))
            exchange, mic = _NASDAQ_MARKET_CATEGORY.get(
                str(raw.get("Market Category") or "").strip().upper(),
                ("NASDAQ", "XNAS"),
            )
            financial_status = str(raw.get("Financial Status") or "N").strip().upper()
            name = str(raw.get("Security Name") or symbol).strip()
        else:
            symbol = _clean_symbol(raw.get("ACT Symbol") or raw.get("NASDAQ Symbol"))
            exchange_code = str(raw.get("Exchange") or "").strip().upper()
            exchange, mic = _OTHER_EXCHANGE.get(exchange_code, ("Other US exchange", "unknown"))
            financial_status = "not_reported"
            name = str(raw.get("Security Name") or symbol).strip()
        if not symbol:
            continue
        is_etf = str(raw.get("ETF") or "").strip().upper() == "Y"
        rows.append(
            {
                "symbol": symbol,
                "name": name,
                "asset_class": "etf" if is_etf else "equity",
                "security_type": "etf" if is_etf else "equity",
                "exchange": exchange,
                "mic": mic,
                "listing_status": "active" if financial_status in {"N", "not_reported", ""} else "flagged",
                "financial_status_code": financial_status,
                "test_issue": False,
                "membership_provider": "nasdaq_trader",
                "membership_source_url": source_url,
                "membership_source_status": "official/current-day",
                "membership_as_of": directory_as_of or fetched_at,
                "membership_timestamp_timezone": "not_specified_by_source_file" if directory_as_of else "UTC",
                "membership_caveat": "Official US listing identity; this is not index membership, sector taxonomy, or a live quote.",
                "not_financial_advice": True,
            }
        )
    return {
        "directory": directory,
        "directory_as_of": directory_as_of,
        "directory_timestamp_timezone": "not_specified_by_source_file" if directory_as_of else None,
        "rows": rows,
    }


def _source_status(result: DataResult) -> str:
    if not result.ok:
        return "unavailable"
    refreshed = result.refreshed_status()
    if refreshed == "stale":
        return "stale"
    if result.is_cached:
        return "cached"
    return "live/fresh"


def _fetch_directory(
    *,
    key: str,
    url: str,
    directory: str,
    session: Any | None,
    timeout: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    text, result = fetch_text_with_cache(
        key,
        url,
        provider="nasdaq_trader",
        source=f"Nasdaq Trader {directory} symbol directory",
        headers={"User-Agent": "Global Terminal research client"},
        ttl_seconds=DIRECTORY_TTL_SECONDS,
        timeout=timeout,
        session=session,
    )
    status = result.to_dict()
    source_status = _source_status(result)
    parsed = (
        parse_nasdaq_symbol_directory(
            text,
            directory=directory,
            source_url=url,
            fetched_at=status["fetched_at"],
        )
        if text
        else {"directory": directory, "directory_as_of": None, "rows": []}
    )
    return parsed, {
        **status,
        "source_url": url,
        "source_status": source_status,
        "freshness": source_status,
        "row_count": len(parsed["rows"]),
        "provider_call_count": 0 if status.get("cached") else 1,
        "directory_as_of": parsed.get("directory_as_of"),
        "caveat": "Official listing identity only; no index membership, quote, sector, or industry claim.",
        "data_gap": status.get("error") or status.get("warning"),
        "not_financial_advice": True,
    }


def fetch_nasdaq_symbol_directory(
    *,
    session: Any | None = None,
    timeout: int = 15,
) -> dict[str, Any]:
    """Fetch both official US symbol directories concurrently and return a bounded JSON-safe contract."""
    requests = (
        {
            "key": f"{NASDAQ_DIRECTORY_VERSION}:nasdaq-listed",
            "url": NASDAQ_LISTED_URL,
            "directory": "nasdaq-listed",
            "session": session,
            "timeout": timeout,
        },
        {
            "key": f"{NASDAQ_DIRECTORY_VERSION}:other-listed",
            "url": OTHER_LISTED_URL,
            "directory": "other-listed",
            "session": session,
            "timeout": timeout,
        },
    )
    with ThreadPoolExecutor(max_workers=2, thread_name_prefix="nasdaq-directory") as executor:
        outputs = list(executor.map(lambda kwargs: _fetch_directory(**kwargs), requests))
    parsed_rows = [row for parsed, _ in outputs for row in parsed["rows"]]
    deduped = {row["symbol"]: row for row in parsed_rows}
    sources = [status for _, status in outputs]
    statuses = {source["source_status"] for source in sources}
    if "live/fresh" in statuses:
        source_status = "live/fresh"
    elif "cached" in statuses:
        source_status = "cached"
    elif "stale" in statuses:
        source_status = "stale"
    else:
        source_status = "unavailable"
    directory_times = [source["directory_as_of"] for source in sources if source.get("directory_as_of")]
    return {
        "nasdaq_directory_version": NASDAQ_DIRECTORY_VERSION,
        "rows": sorted(deduped.values(), key=lambda row: row["symbol"]),
        "sources": sources,
        "summary": {
            "listing_count": len(deduped),
            "equity_count": sum(row["asset_class"] == "equity" for row in deduped.values()),
            "etf_count": sum(row["asset_class"] == "etf" for row in deduped.values()),
            "flagged_count": sum(row["listing_status"] == "flagged" for row in deduped.values()),
            "source_status": source_status,
            "directory_as_of": max(directory_times) if directory_times else None,
            "authoritative_listing_identity": bool(deduped),
            "authoritative_index_membership": False,
            "taxonomy_included": False,
        },
    }
