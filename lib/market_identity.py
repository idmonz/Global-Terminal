from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from .runtime_cache import fetch_json_with_cache
from .sec_edgar_provider import get_sec_user_agent, normalize_cik


MARKET_IDENTITY_VERSION = "market_identity.v1"
SEC_TICKER_EXCHANGE_URL = "https://www.sec.gov/files/company_tickers_exchange.json"
SEC_TICKER_EXCHANGE_TTL_SECONDS = 21_600

_SUPPORTED_MICS = {"XNAS", "XNYS", "XASE", "ARCX", "BATS", "IEXG"}
_SYMBOL_PATTERN = re.compile(r"^[A-Z][A-Z0-9-]{0,14}$")
_UNSUPPORTED_NAME = re.compile(
    r"\b(WARRANTS?|RIGHTS?|UNITS?|PREFERRED|PREFERENCE|PREF\.?|DEPOSITARY SHARES?)\b",
    re.IGNORECASE,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _source_status(result: Any) -> str:
    if not getattr(result, "ok", False):
        return "unavailable"
    if result.refreshed_status() == "stale":
        return "stale"
    if getattr(result, "is_cached", False):
        return "cached"
    return "live/fresh"


def normalize_sec_ticker_exchange_rows(
    payload: dict[str, Any] | None,
    *,
    fetched_at: str,
) -> list[dict[str, Any]]:
    fields = payload.get("fields") if isinstance(payload, dict) else None
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(fields, list) or not isinstance(data, list):
        return []
    field_names = [str(field or "").strip().lower() for field in fields]
    output: dict[str, dict[str, Any]] = {}
    for values in data:
        if not isinstance(values, list):
            continue
        raw = dict(zip(field_names, values))
        symbol = str(raw.get("ticker") or "").strip().upper().replace(".", "-")
        cik = raw.get("cik")
        if not _SYMBOL_PATTERN.fullmatch(symbol) or cik in {None, ""}:
            continue
        output[symbol] = {
            "symbol": symbol,
            "cik": normalize_cik(cik),
            "sec_name": str(raw.get("name") or "").strip() or None,
            "sec_exchange": str(raw.get("exchange") or "").strip() or None,
            "sec_provider": "sec_edgar",
            "sec_source_url": SEC_TICKER_EXCHANGE_URL,
            "sec_source_status": "official/current",
            "sec_fetched_at": fetched_at,
        }
    return [output[symbol] for symbol in sorted(output)]


def fetch_sec_ticker_exchange_directory(
    *,
    session: Any | None = None,
    timeout: int = 15,
) -> dict[str, Any]:
    fetched_at = _now_iso()
    user_agent = get_sec_user_agent()
    if not user_agent:
        return {
            "identity_version": MARKET_IDENTITY_VERSION,
            "rows": [],
            "source": {
                "provider": "sec_edgar",
                "source_url": SEC_TICKER_EXCHANGE_URL,
                "source_status": "missing-key",
                "fetched_at": fetched_at,
                "row_count": 0,
                "caveat": "SEC fair-access identification is required; no credential value is exposed.",
                "data_gap": "SEC_USER_AGENT is not configured.",
            },
        }
    payload, result = fetch_json_with_cache(
        f"{MARKET_IDENTITY_VERSION}:sec-ticker-exchange",
        SEC_TICKER_EXCHANGE_URL,
        provider="sec_edgar",
        source="SEC company ticker and exchange directory",
        headers={"User-Agent": user_agent, "Accept-Encoding": "gzip, deflate"},
        ttl_seconds=SEC_TICKER_EXCHANGE_TTL_SECONDS,
        timeout=timeout,
        session=session,
    )
    status = result.to_dict()
    rows = normalize_sec_ticker_exchange_rows(
        payload if isinstance(payload, dict) else None,
        fetched_at=str(status.get("fetched_at") or fetched_at),
    )
    source_status = _source_status(result)
    return {
        "identity_version": MARKET_IDENTITY_VERSION,
        "rows": rows,
        "source": {
            **status,
            "source_url": SEC_TICKER_EXCHANGE_URL,
            "source_status": source_status,
            "row_count": len(rows),
            "provider_call_count": 0 if status.get("cached") else 1,
            "caveat": "Official SEC ticker/CIK/exchange identity; not listing status, taxonomy, or index membership.",
            "data_gap": status.get("error") or status.get("warning"),
            "not_financial_advice": True,
        },
    }


def _exclusion_reason(row: dict[str, Any]) -> str | None:
    symbol = str(row.get("symbol") or "").strip().upper()
    name = str(row.get("name") or "")
    if not _SYMBOL_PATTERN.fullmatch(symbol):
        return "invalid-symbol"
    if str(row.get("listing_status") or "") != "active":
        return "inactive-or-flagged"
    if str(row.get("mic") or "") not in _SUPPORTED_MICS:
        return "unsupported-exchange"
    if str(row.get("security_type") or "") not in {"equity", "etf"}:
        return "unsupported-security-type"
    if _UNSUPPORTED_NAME.search(name):
        return "unsupported-security-type"
    return None


def build_market_identity_contract(
    *,
    listing_contract: dict[str, Any],
    sec_rows: list[dict[str, Any]] | None = None,
    sec_source: dict[str, Any] | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    sec_lookup = {
        str(row.get("symbol") or "").upper(): row
        for row in sec_rows or []
        if isinstance(row, dict)
    }
    accepted: dict[str, dict[str, Any]] = {}
    exclusions: list[dict[str, Any]] = []
    for raw in sorted(
        (row for row in listing_contract.get("rows") or [] if isinstance(row, dict)),
        key=lambda row: (str(row.get("symbol") or ""), str(row.get("name") or "")),
    ):
        symbol = str(raw.get("symbol") or "").strip().upper()
        reason = _exclusion_reason(raw)
        if reason:
            exclusions.append(
                {
                    "symbol": symbol or None,
                    "reason": reason,
                    "provider": raw.get("membership_provider") or "nasdaq_trader",
                    "source_status": raw.get("membership_source_status") or "unavailable",
                }
            )
            continue
        sec = sec_lookup.get(symbol) or {}
        accepted[symbol] = {
            "symbol": symbol,
            "normalized_symbol": symbol,
            "name": raw.get("name") or sec.get("sec_name") or symbol,
            "asset_class": raw.get("asset_class") or "equity",
            "security_type": raw.get("security_type") or "equity",
            "exchange": raw.get("exchange"),
            "mic": raw.get("mic"),
            "cik": sec.get("cik"),
            "listing_status": raw.get("listing_status"),
            "listing_provider": raw.get("membership_provider") or "nasdaq_trader",
            "listing_source_url": raw.get("membership_source_url"),
            "listing_source_status": raw.get("membership_source_status"),
            "listing_as_of": raw.get("membership_as_of"),
            "sec_provider": sec.get("sec_provider"),
            "sec_source_url": sec.get("sec_source_url"),
            "sec_source_status": sec.get("sec_source_status") or "unavailable",
            "sec_exchange": sec.get("sec_exchange"),
            "identity_conflict": bool(
                sec.get("sec_exchange")
                and raw.get("exchange")
                and str(sec.get("sec_exchange")).lower() not in str(raw.get("exchange")).lower()
                and str(raw.get("exchange")).lower() not in str(sec.get("sec_exchange")).lower()
            ),
            "authoritative_listing_identity": True,
            "authoritative_index_membership": False,
            "caveat": "Nasdaq Trader listing identity and SEC ticker/CIK identity are independent official sources; no index membership is claimed.",
            "not_financial_advice": True,
        }
    listing_summary = listing_contract.get("summary") or {}
    rows = [accepted[symbol] for symbol in sorted(accepted)]
    return {
        "identity_version": MARKET_IDENTITY_VERSION,
        "generated_at": generated_at or _now_iso(),
        "rows": rows,
        "exclusions": exclusions,
        "sources": [
            *(listing_contract.get("sources") or []),
            *([sec_source] if sec_source else []),
        ],
        "summary": {
            "candidate_count": len(listing_contract.get("rows") or []),
            "supported_count": len(rows),
            "excluded_count": len(exclusions),
            "sec_cik_coverage_count": sum(bool(row.get("cik")) for row in rows),
            "identity_conflict_count": sum(bool(row.get("identity_conflict")) for row in rows),
            "listing_source_status": listing_summary.get("source_status") or "unavailable",
            "listing_as_of": listing_summary.get("directory_as_of"),
            "authoritative_listing_identity": bool(listing_summary.get("authoritative_listing_identity")),
            "authoritative_index_membership": False,
        },
        "caveat": "Identity reconciliation excludes unsupported security types and never infers index membership.",
        "not_financial_advice": True,
    }
