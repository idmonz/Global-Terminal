from __future__ import annotations

from typing import Any

from .options_time_to_expiry import derive_time_to_expiry_years


def _norm(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def _has_explicit_model(row: dict[str, Any]) -> bool:
    supplied = _norm(row.get("model") or row.get("pricing_model"))
    return supplied in {"black_scholes", "bs", "bsm", "black_76", "black76", "b76", "garman_kohlhagen", "gk", "fx"}


def infer_option_pricing_model_for_row(row: dict[str, Any]) -> dict[str, Any]:
    supplied = _norm(row.get("model") or row.get("pricing_model"))
    if supplied in {"black_scholes", "bs", "bsm"}:
        return {"ok": True, "model": "black_scholes", "source": "supplied_model", "caveats": ["user_supplied_model_override"], "research_only": True}
    if supplied in {"black_76", "black76", "b76"}:
        return {"ok": True, "model": "black_76", "source": "supplied_model", "caveats": ["user_supplied_model_override"], "research_only": True}
    if supplied in {"garman_kohlhagen", "gk", "fx"}:
        return {"ok": True, "model": "garman_kohlhagen", "source": "supplied_model", "caveats": ["user_supplied_model_override"], "research_only": True}
    asset_class = _norm(row.get("asset_class") or row.get("instrument_type") or row.get("underlying_type"))
    symbol = _norm(row.get("underlying") or row.get("root") or row.get("symbol"))
    if row.get("domestic_rate") not in (None, "") and row.get("foreign_rate") not in (None, ""):
        return {"ok": True, "model": "garman_kohlhagen", "source": "rate_fields", "caveats": [], "research_only": True}
    if asset_class in {"fx", "forex", "currency", "fx_option"}:
        return {"ok": True, "model": "garman_kohlhagen", "source": "asset_class", "caveats": [], "research_only": True}
    if row.get("futures_price") not in (None, "") or asset_class in {"futures", "commodity", "futures_option"}:
        return {"ok": True, "model": "black_76", "source": "futures_fields", "caveats": [], "research_only": True}
    if asset_class in {"equity", "index", "etf", "stock"}:
        return {"ok": True, "model": "black_scholes", "source": "asset_class", "caveats": [], "research_only": True}
    if asset_class == "crypto" or symbol in {"btc", "eth", "btcusd", "btcusdt", "ethusd", "ethusdt"}:
        return {"ok": True, "model": "black_scholes", "source": "crypto_caveated_default", "caveats": ["crypto_option_uses_black_scholes_style_caveat"], "research_only": True}
    return {"ok": False, "model": "manual_unknown", "source": "unknown_manual_mode", "caveats": ["unknown_model_manual_mode", "pricing_skipped_missing_model"], "research_only": True}


def validate_model_specific_fields(row: dict[str, Any], model: str) -> dict[str, Any]:
    missing: list[str] = []
    if model == "black_76" and row.get("futures_price") in (None, "") and row.get("underlying_price") in (None, ""):
        missing.append("futures_price_or_underlying_price")
    if model == "garman_kohlhagen":
        if row.get("domestic_rate") in (None, "") and row.get("risk_free_rate") in (None, ""):
            missing.append("domestic_rate_or_risk_free_rate")
        if row.get("foreign_rate") in (None, ""):
            missing.append("foreign_rate")
    return {"ok": not missing, "missing_fields": missing, "caveats": [f"missing_{m}" for m in missing], "research_only": True}


def build_row_pricing_input(row: dict[str, Any], *, volatility: float | None = None, premium: float | None = None) -> dict[str, Any]:
    model_payload = infer_option_pricing_model_for_row(row)
    if not model_payload.get("ok"):
        raise ValueError("pricing_skipped_missing_model: unknown_model_manual_mode")
    model = model_payload["model"]
    field_check = validate_model_specific_fields(row, model)
    if not field_check.get("ok"):
        raise ValueError("model_specific_fields_missing: " + ",".join(field_check.get("missing_fields", [])))
    tte_payload = derive_time_to_expiry_years(row, snapshot_timestamp=row.get("snapshot_timestamp"))
    if not tte_payload.get("ok"):
        raise ValueError(f"time_to_expiry_unavailable: {tte_payload.get('caveat')}")
    tte = tte_payload.get("time_to_expiry_years")
    base = {
        "option_type": row.get("option_type", "call"),
        "underlying_price": float(row.get("underlying_price") or row.get("futures_price") or 0.0),
        "strike": float(row.get("strike")),
        "time_to_expiry_years": float(tte),
        "risk_free_rate": float(row.get("risk_free_rate", row.get("domestic_rate", 0.0)) or 0.0),
        "dividend_yield": float(row.get("dividend_yield", row.get("foreign_rate", 0.0)) or 0.0),
        "volatility": float(volatility if volatility is not None else row.get("volatility", row.get("implied_volatility", 0.2)) or 0.2),
        "contract_multiplier": float(row.get("contract_multiplier", 100.0) or 100.0),
        "model": model,
        "model_selection": model_payload,
        "caveats": list(model_payload.get("caveats", [])) + list(field_check.get("caveats", [])),
        "research_only": True,
    }
    if premium is not None:
        base["premium"] = float(premium)
    if model == "black_76":
        base["futures_price"] = float(row.get("futures_price") or row.get("underlying_price"))
        base["underlying_price"] = base["futures_price"]
    if model == "garman_kohlhagen":
        base["domestic_rate"] = float(row.get("domestic_rate", row.get("risk_free_rate", 0.0)) or 0.0)
        base["foreign_rate"] = float(row.get("foreign_rate", row.get("dividend_yield", 0.0)) or 0.0)
        base["risk_free_rate"] = base["domestic_rate"]
        base["dividend_yield"] = base["foreign_rate"]
    return base
