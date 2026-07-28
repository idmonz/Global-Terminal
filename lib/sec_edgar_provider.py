from __future__ import annotations

import os
from datetime import datetime, timezone
import math
from typing import Any

import requests


SEC_BASE = "https://data.sec.gov"
SEC_FACT_CONTRACT_VERSION = "sec_company_facts.v1"
SEC_FACT_CONCEPTS: dict[str, tuple[str, str]] = {
    "RevenueFromContractWithCustomerExcludingAssessedTax": ("Revenue", "USD"),
    "Revenues": ("Revenue", "USD"),
    "OperatingIncomeLoss": ("Operating income", "USD"),
    "NetIncomeLoss": ("Net income", "USD"),
    "Assets": ("Assets", "USD"),
    "Liabilities": ("Liabilities", "USD"),
    "StockholdersEquity": ("Stockholders equity", "USD"),
    "CashAndCashEquivalentsAtCarryingValue": ("Cash and cash equivalents", "USD"),
    "NetCashProvidedByUsedInOperatingActivities": ("Operating cash flow", "USD"),
    "PaymentsToAcquirePropertyPlantAndEquipment": ("Capital expenditure", "USD"),
    "EarningsPerShareDiluted": ("Diluted EPS", "USD/shares"),
}
_REVIEWED_FORMS = {"10-K", "10-K/A", "10-Q", "10-Q/A"}


def get_sec_user_agent() -> str | None:
    return os.getenv("SEC_USER_AGENT") or None


def normalize_cik(cik: str | int) -> str:
    return str(cik).strip().lstrip("0").zfill(10)


def build_sec_company_facts_url(cik: str | int) -> str:
    return f"{SEC_BASE}/api/xbrl/companyfacts/CIK{normalize_cik(cik)}.json"


def sec_rate_limit_policy() -> dict[str, Any]:
    return {"provider": "sec_edgar", "requires_user_agent": True, "requests_per_second_ceiling": 10, "status": "guarded"}


def fetch_sec_company_facts(cik: str | int, *, session: Any | None = None, user_agent: str | None = None, timeout: int = 15) -> dict[str, Any]:
    agent = user_agent or get_sec_user_agent()
    url = build_sec_company_facts_url(cik)
    if not agent:
        return {"ok": False, "provider": "sec_edgar", "status": "missing_key", "url": url, "data": None, "error": "SEC_USER_AGENT is required for SEC EDGAR requests.", "caveat": "No secret value is displayed."}
    client = session or requests
    response = client.get(url, headers={"User-Agent": agent, "Accept-Encoding": "gzip, deflate"}, timeout=timeout)
    response.raise_for_status()
    return {
        "ok": True,
        "provider": "sec_edgar",
        "status": "available",
        "url": url,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "data": response.json(),
        "caveat": "SEC data may update after filings are accepted.",
    }


def normalize_sec_company_facts(
    payload: dict[str, Any] | None,
    *,
    per_concept: int = 4,
) -> list[dict[str, Any]]:
    facts = payload.get("facts") if isinstance(payload, dict) and isinstance(payload.get("facts"), dict) else {}
    us_gaap = facts.get("us-gaap") if isinstance(facts.get("us-gaap"), dict) else {}
    output: list[dict[str, Any]] = []
    limit = max(1, min(int(per_concept), 12))
    for concept, (contract_label, expected_unit) in SEC_FACT_CONCEPTS.items():
        definition = us_gaap.get(concept)
        if not isinstance(definition, dict):
            continue
        units = definition.get("units") if isinstance(definition.get("units"), dict) else {}
        observations = units.get(expected_unit)
        if not isinstance(observations, list):
            continue
        normalized = []
        seen: set[tuple[str, str, str, str]] = set()
        for raw in observations:
            if not isinstance(raw, dict) or str(raw.get("form") or "") not in _REVIEWED_FORMS:
                continue
            value = _finite_number(raw.get("val"))
            if value is None:
                continue
            identity = (
                str(raw.get("accn") or ""),
                str(raw.get("end") or ""),
                str(raw.get("filed") or ""),
                expected_unit,
            )
            if identity in seen:
                continue
            seen.add(identity)
            normalized.append(
                {
                    "namespace": "us-gaap",
                    "concept": concept,
                    "label": str(definition.get("label") or contract_label),
                    "contract_label": contract_label,
                    "description": str(definition.get("description") or "")[:600] or None,
                    "unit": expected_unit,
                    "value": value,
                    "start": _date_text(raw.get("start")),
                    "end": _date_text(raw.get("end")),
                    "instant": _date_text(raw.get("end")) if not raw.get("start") else None,
                    "filed": _date_text(raw.get("filed")),
                    "accession": str(raw.get("accn") or "") or None,
                    "form": str(raw.get("form") or "") or None,
                    "fiscal_year": _integer(raw.get("fy")),
                    "fiscal_period": str(raw.get("fp") or "") or None,
                    "frame": str(raw.get("frame") or "") or None,
                    "provider": "sec_edgar",
                    "source_status": "official-filing-fact",
                    "not_financial_advice": True,
                }
            )
        normalized.sort(
            key=lambda row: (
                str(row.get("filed") or ""),
                str(row.get("end") or ""),
                str(row.get("accession") or ""),
            ),
            reverse=True,
        )
        output.extend(normalized[:limit])
    return output


def build_sec_company_facts_context(
    cik: str | int,
    *,
    session: Any | None = None,
    user_agent: str | None = None,
    timeout: int = 15,
) -> dict[str, Any]:
    url = build_sec_company_facts_url(cik)
    try:
        result = fetch_sec_company_facts(
            cik,
            session=session,
            user_agent=user_agent,
            timeout=timeout,
        )
    except Exception as exc:
        return _sec_fact_gap(url, "provider-error", f"SEC company facts request failed: {type(exc).__name__}.")
    if not result.get("ok"):
        return _sec_fact_gap(url, str(result.get("status") or "unavailable"), str(result.get("error") or "SEC company facts unavailable."))
    payload = result.get("data") if isinstance(result.get("data"), dict) else {}
    rows = normalize_sec_company_facts(payload)
    fetched_at = result.get("fetched_at") or datetime.now(timezone.utc).isoformat()
    status = "live/fresh" if rows else "unavailable"
    caveat = "Official SEC XBRL facts retain their reported unit, period, form, filed date, and accession."
    data_gap = None if rows else "No reviewed us-gaap concept/unit observations were returned."
    return {
        "contract_version": SEC_FACT_CONTRACT_VERSION,
        "availability": "available" if rows else "unavailable",
        "provider": "sec_edgar",
        "source_status": status,
        "source_url": url,
        "fetched_at": fetched_at,
        "cik": normalize_cik(cik),
        "entity_name": payload.get("entityName"),
        "facts": rows,
        "fact_count": len(rows),
        "concept_count": len({row["concept"] for row in rows}),
        "source_register": [
            {
                "provider": "sec_edgar",
                "source": "SEC XBRL companyfacts",
                "source_url": url,
                "source_status": status,
                "fetched_at": fetched_at,
                "row_count": len(rows),
                "caveat": caveat,
                "data_gap": data_gap,
                "not_financial_advice": True,
            }
        ],
        "caveat": caveat,
        "data_gap": data_gap,
        "not_financial_advice": True,
    }


def _sec_fact_gap(url: str, status: str, gap: str) -> dict[str, Any]:
    return {
        "contract_version": SEC_FACT_CONTRACT_VERSION,
        "availability": "provider-required" if status == "missing_key" else "unavailable",
        "provider": "sec_edgar",
        "source_status": "missing-key" if status == "missing_key" else status,
        "source_url": url,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "cik": None,
        "entity_name": None,
        "facts": [],
        "fact_count": 0,
        "concept_count": 0,
        "source_register": [
            {
                "provider": "sec_edgar",
                "source": "SEC XBRL companyfacts",
                "source_url": url,
                "source_status": "missing-key" if status == "missing_key" else status,
                "fetched_at": None,
                "row_count": 0,
                "caveat": "SEC fair-access identification is required.",
                "data_gap": gap,
                "not_financial_advice": True,
            }
        ],
        "caveat": "SEC fair-access identification is required.",
        "data_gap": gap,
        "not_financial_advice": True,
    }


def _finite_number(value: Any) -> float | int | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return int(number) if number.is_integer() else number


def _integer(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _date_text(value: Any) -> str | None:
    text = str(value or "").strip()
    if len(text) != 10:
        return None
    try:
        return datetime.fromisoformat(text).date().isoformat()
    except ValueError:
        return None
