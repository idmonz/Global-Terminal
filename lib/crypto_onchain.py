from __future__ import annotations

from typing import Any

from .cache import fetch_json
from .data_status import combine_results, failure

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None


DEFILLAMA_PROVIDER = "DefiLlama"
LLAMA_BASE = "https://api.llama.fi"
STABLES_BASE = "https://stablecoins.llama.fi"


def _llama_get(base: str, path: str, *, params: dict[str, Any] | None = None, ttl_seconds: int = 1800, source: str | None = None):
    return fetch_json(f"{base}{path}", params=params, provider=DEFILLAMA_PROVIDER, source=source or path, ttl_seconds=ttl_seconds, timeout=15)


def _frame(payload: Any):
    if pd is None:
        return payload
    if isinstance(payload, dict):
        if "protocols" in payload and isinstance(payload["protocols"], list):
            return pd.DataFrame(payload["protocols"])
        if "chains" in payload and isinstance(payload["chains"], list):
            return pd.DataFrame(payload["chains"])
        if "data" in payload and isinstance(payload["data"], list):
            return pd.DataFrame(payload["data"])
        return pd.DataFrame([payload])
    return pd.DataFrame(payload if isinstance(payload, list) else [])


def _stablecoin_chain_frame(payload: Any):
    if pd is None:
        return payload
    rows = []
    for item in payload if isinstance(payload, list) else []:
        if not isinstance(item, dict):
            continue
        circulating = item.get("totalCirculatingUSD") or {}
        row = {
            "name": item.get("name"),
            "chain": item.get("name"),
            "stablecoin_supply_usd": circulating.get("peggedUSD"),
        }
        for peg, value in circulating.items():
            row[f"supply_{peg}"] = value
        rows.append(row)
    frame = pd.DataFrame(rows)
    if not frame.empty:
        for col in [col for col in frame.columns if col.startswith("supply_") or col == "stablecoin_supply_usd"]:
            frame[col] = pd.to_numeric(frame[col], errors="coerce")
        frame = frame.sort_values("stablecoin_supply_usd", ascending=False, na_position="last")
    return frame


def get_defillama_chains():
    payload, status = _llama_get(LLAMA_BASE, "/v2/chains", ttl_seconds=1800, source="DefiLlama chain TVL")
    if payload is None:
        return _frame([]), status
    if not isinstance(payload, list):
        return _frame([]), failure(source="DefiLlama chain TVL", provider=DEFILLAMA_PROVIDER, error="Chain TVL response was not a list.", coverage="malformed response")
    frame = _frame(payload)
    if pd is not None and not frame.empty and "tvl" in frame.columns:
        frame["tvl"] = pd.to_numeric(frame["tvl"], errors="coerce")
    return frame, status


def get_defillama_protocols():
    payload, status = _llama_get(LLAMA_BASE, "/protocols", ttl_seconds=1800, source="DefiLlama protocol TVL")
    if payload is None:
        return _frame([]), status
    if not isinstance(payload, list):
        return _frame([]), failure(source="DefiLlama protocol TVL", provider=DEFILLAMA_PROVIDER, error="Protocol response was not a list.", coverage="malformed response")
    frame = _frame(payload)
    if pd is not None and not frame.empty and "tvl" in frame.columns:
        frame["tvl"] = pd.to_numeric(frame["tvl"], errors="coerce")
    return frame, status


def get_stablecoins_overview():
    payload, status = _llama_get(STABLES_BASE, "/stablecoins", params={"includePrices": "true"}, ttl_seconds=1800, source="DefiLlama stablecoins")
    if payload is None:
        return _frame([]), status
    if not isinstance(payload, dict):
        return _frame([]), failure(source="DefiLlama stablecoins", provider=DEFILLAMA_PROVIDER, error="Stablecoin response was not a JSON object.", coverage="malformed response")
    frame = _frame(payload.get("peggedAssets", []))
    return frame, status


def get_stablecoins_by_chain():
    payload, status = _llama_get(STABLES_BASE, "/stablecoinchains", ttl_seconds=1800, source="DefiLlama stablecoins by chain")
    if payload is None:
        return _frame([]), status
    if not isinstance(payload, list):
        return _frame([]), failure(source="DefiLlama stablecoins by chain", provider=DEFILLAMA_PROVIDER, error="Stablecoin chain response was not a list.", coverage="malformed response")
    return _stablecoin_chain_frame(payload), status


def get_dex_volume_overview():
    payload, status = _llama_get(LLAMA_BASE, "/overview/dexs", params={"excludeTotalDataChart": "true", "excludeTotalDataChartBreakdown": "true", "dataType": "dailyVolume"}, ttl_seconds=1800, source="DefiLlama DEX volume")
    if payload is None:
        return _frame([]), status
    return _frame(payload), status


def get_fees_overview():
    payload, status = _llama_get(LLAMA_BASE, "/overview/fees", params={"excludeTotalDataChart": "true", "excludeTotalDataChartBreakdown": "true", "dataType": "dailyFees"}, ttl_seconds=1800, source="DefiLlama fees")
    if payload is None:
        return _frame([]), status
    return _frame(payload), status


def build_onchain_dashboard():
    chains, chains_status = get_defillama_chains()
    protocols, protocols_status = get_defillama_protocols()
    stablecoins, stable_status = get_stablecoins_overview()
    stable_by_chain, stable_chain_status = get_stablecoins_by_chain()
    dex, dex_status = get_dex_volume_overview()
    fees, fees_status = get_fees_overview()
    data = {
        "chains": chains,
        "protocols": protocols,
        "stablecoins": stablecoins,
        "stablecoins_by_chain": stable_by_chain,
        "dex_volume": dex,
        "fees": fees,
    }
    status = combine_results([chains_status, protocols_status, stable_status, stable_chain_status, dex_status, fees_status], provider=DEFILLAMA_PROVIDER, source="DefiLlama on-chain dashboard")
    return data, status
