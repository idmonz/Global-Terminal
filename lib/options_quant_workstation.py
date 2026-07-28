from __future__ import annotations

import math
import threading
import time
from copy import deepcopy
from datetime import date, datetime, timezone
from typing import Any
from urllib.parse import quote

from .options_flow import get_options_chain, get_options_expirations
from .options_greeks import build_greek_units_table, calculate_greeks, scale_greeks_by_contract
from .options_pricing_models import black_scholes_price
from .options_scenarios import option_scenario_grid


OPTIONS_QUANT_WORKSTATION_VERSION = "options_quant.v2"
_CACHE_TTL_SECONDS = 300
_CACHE_STALE_SECONDS = 1800
_CACHE_LOCK = threading.Lock()
_RUNTIME_CACHE: dict[str, dict[str, Any]] = {}
_MODEL_RATE_ASSUMPTION = 0.04
_MODEL_DIVIDEND_ASSUMPTION = 0.0
_CONTRACT_MULTIPLIER_ASSUMPTION = 100.0
_DISCLOSURE = (
    "Options and model outputs are research calculations only. They are not investment advice, "
    "trading recommendations, trade approvals, hedging instructions, broker actions, or execution instructions."
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean_number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _records(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if hasattr(value, "to_dict"):
        try:
            return [dict(row) for row in value.to_dict(orient="records")]
        except TypeError:
            pass
    if isinstance(value, list):
        return [dict(row) for row in value if isinstance(row, dict)]
    return []


def _iso(value: Any) -> str | None:
    if value in (None, ""):
        return None
    if hasattr(value, "to_pydatetime"):
        value = value.to_pydatetime()
    if isinstance(value, datetime):
        parsed = value
    else:
        text = str(value).strip().replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return str(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat()


def _parse_datetime(value: Any) -> datetime | None:
    text = _iso(value)
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _expiry_date(value: Any) -> date | None:
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def _status_dict(value: Any) -> dict[str, Any]:
    if hasattr(value, "to_dict"):
        return dict(value.to_dict())
    return dict(value or {}) if isinstance(value, dict) else {}


def _moneyness(option_type: str, strike: float, spot: float) -> str:
    ratio = strike / spot
    if abs(ratio - 1.0) <= 0.025:
        return "atm"
    if option_type == "call":
        return "itm" if strike < spot else "otm"
    return "itm" if strike > spot else "otm"


def _days_to_expiry(expiry: str, fetched_at: str) -> int:
    expiry_value = _expiry_date(expiry)
    fetched = _parse_datetime(fetched_at)
    if expiry_value is None or fetched is None:
        return 0
    return max(0, (expiry_value - fetched.date()).days)


def normalize_provider_option_rows(
    *,
    symbol: str,
    expiry: str,
    calls: Any,
    puts: Any,
    underlying_price: Any,
    fetched_at: str,
    source_status: str,
    provider: str = "yfinance options",
    source_url: str | None = None,
) -> dict[str, Any]:
    symbol = str(symbol or "").strip().upper()
    spot = _clean_number(underlying_price)
    fetched = _parse_datetime(fetched_at)
    expiry_value = _expiry_date(expiry)
    rows: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    seen: set[tuple[str, str, float, str]] = set()
    source_url = source_url or f"https://finance.yahoo.com/quote/{quote(symbol)}/options"

    for option_type, frame in (("call", calls), ("put", puts)):
        for raw in _records(frame):
            contract_symbol = str(raw.get("contractSymbol") or raw.get("symbol") or "").strip()
            strike = _clean_number(raw.get("strike"))
            bid = _clean_number(raw.get("bid"))
            ask = _clean_number(raw.get("ask"))
            last = _clean_number(raw.get("lastPrice") if raw.get("lastPrice") is not None else raw.get("last"))
            volume = _clean_number(raw.get("volume"))
            open_interest = _clean_number(raw.get("openInterest") if raw.get("openInterest") is not None else raw.get("open_interest"))
            provider_iv = _clean_number(raw.get("impliedVolatility") if raw.get("impliedVolatility") is not None else raw.get("implied_volatility"))
            reasons: list[str] = []

            if not symbol:
                reasons.append("missing_underlying_symbol")
            if not contract_symbol:
                reasons.append("missing_contract_symbol")
            if spot is None or spot <= 0:
                reasons.append("non_positive_underlying_price")
            if strike is None or strike <= 0:
                reasons.append("non_positive_strike")
            if expiry_value is None:
                reasons.append("invalid_expiry")
            elif fetched and expiry_value < fetched.date():
                reasons.append("expired_contract")
            if bid is None:
                reasons.append("missing_bid")
            elif bid < 0:
                reasons.append("negative_bid")
            if ask is None:
                reasons.append("missing_ask")
            elif ask < 0:
                reasons.append("negative_ask")
            if bid is not None and ask is not None and bid > ask:
                reasons.append("bid_greater_than_ask")
            for field, number in (("last", last), ("volume", volume), ("open_interest", open_interest), ("implied_volatility", provider_iv)):
                if number is not None and number < 0:
                    reasons.append(f"negative_{field}")
            if provider_iv is not None and provider_iv > 5.0:
                reasons.append("implied_volatility_out_of_range")

            identity = (provider, symbol, float(strike or 0.0), f"{expiry}:{option_type}")
            if identity in seen:
                reasons.append("duplicate_contract_identity")
            if reasons:
                rejected.append({"contract_symbol": contract_symbol, "option_type": option_type, "expiry": expiry, "strike": strike, "reasons": sorted(dict.fromkeys(reasons))})
                continue
            seen.add(identity)

            quality_flags: list[str] = []
            if bid == 0 and ask == 0:
                quality_flags.append("zero_bid_ask")
            mid = None if bid is None or ask is None else (bid + ask) / 2.0
            spread_pct = None if mid in (None, 0) else (ask - bid) / mid
            if spread_pct is not None and spread_pct > 0.25:
                quality_flags.append("wide_spread")
            if volume is None:
                quality_flags.append("missing_volume")
            if open_interest is None:
                quality_flags.append("missing_open_interest")
            if provider_iv in (None, 0):
                quality_flags.append("missing_or_zero_provider_iv")

            last_trade_at = _iso(raw.get("lastTradeDate") if raw.get("lastTradeDate") is not None else raw.get("last_trade_at"))
            last_trade = _parse_datetime(last_trade_at)
            quote_age_hours = None
            if fetched and last_trade:
                quote_age_hours = max(0.0, (fetched - last_trade).total_seconds() / 3600.0)
                if quote_age_hours > 72:
                    quality_flags.append("stale_last_trade")

            days = _days_to_expiry(expiry, fetched_at)
            tte = max(days, 1) / 365.25
            greeks: dict[str, Any] = {}
            contract_greeks: dict[str, Any] = {}
            model_status = "unavailable"
            if spot and strike and provider_iv and 0 < provider_iv <= 5.0 and days >= 0:
                try:
                    calculated = calculate_greeks({
                        "option_type": option_type,
                        "underlying_price": spot,
                        "strike": strike,
                        "time_to_expiry_years": tte,
                        "risk_free_rate": _MODEL_RATE_ASSUMPTION,
                        "dividend_yield": _MODEL_DIVIDEND_ASSUMPTION,
                        "volatility": provider_iv,
                        "contract_multiplier": _CONTRACT_MULTIPLIER_ASSUMPTION,
                        "premium": mid if mid and mid > 0 else last,
                        "model": "black_scholes",
                    })
                    greeks = dict(calculated.get("greeks") or {})
                    contract_greeks = scale_greeks_by_contract(
                        greeks,
                        contract_multiplier=_CONTRACT_MULTIPLIER_ASSUMPTION,
                        quantity=1.0,
                        underlying_price=spot,
                    )
                    model_status = "calculated"
                except (TypeError, ValueError, ZeroDivisionError, OverflowError) as exc:
                    quality_flags.append(f"greeks_unavailable:{type(exc).__name__}")

            rows.append({
                "underlying_symbol": symbol,
                "underlying_price": spot,
                "contract_symbol": contract_symbol,
                "option_type": option_type,
                "expiry": expiry,
                "days_to_expiry": days,
                "time_to_expiry_years": tte,
                "strike": strike,
                "moneyness": _moneyness(option_type, float(strike), float(spot)),
                "bid": bid,
                "ask": ask,
                "mid": mid,
                "last": last,
                "volume": volume,
                "open_interest": open_interest,
                "provider_iv": provider_iv,
                "in_the_money": bool(raw.get("inTheMoney")) if raw.get("inTheMoney") is not None else None,
                "contract_multiplier": _CONTRACT_MULTIPLIER_ASSUMPTION,
                "contract_multiplier_status": "assumed_us_equity_standard",
                "exercise_style": "american_assumed_us_equity",
                "currency": raw.get("currency") or "USD",
                "last_trade_at": last_trade_at,
                "quote_timestamp": None,
                "quote_age_hours": quote_age_hours,
                "spread_pct": spread_pct,
                "greeks": greeks,
                "contract_greeks": contract_greeks,
                "delta": greeks.get("delta"),
                "gamma": greeks.get("gamma"),
                "vega": greeks.get("vega"),
                "theta_per_day": greeks.get("theta_per_day"),
                "rho": greeks.get("rho"),
                "model": "black_scholes",
                "model_status": model_status,
                "risk_free_rate": _MODEL_RATE_ASSUMPTION,
                "dividend_yield": _MODEL_DIVIDEND_ASSUMPTION,
                "provider": provider,
                "source_url": source_url,
                "fetched_at": fetched_at,
                "freshness": "fixture" if source_status == "fixture" else "delayed" if source_status == "live/fresh" else source_status,
                "source_status": source_status,
                "confidence": 0.82 if model_status == "calculated" and not quality_flags else 0.62,
                "quality_flags": sorted(quality_flags),
                "caveat": "Delayed public data. Provider last-trade time is not a guaranteed bid/ask quote timestamp.",
                "data_gap": "Multiplier, exercise style, risk free rate, and dividend yield are explicit model assumptions.",
                "not_financial_advice": True,
            })

    return {"rows": rows, "rejected_rows": rejected}


def _fixture_rows() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str], str]:
    fetched_at = "2026-06-20T16:00:00+00:00"
    expiries = ["2030-01-18", "2030-02-15", "2030-03-15"]
    spot = 200.0
    strikes = [160.0, 180.0, 190.0, 200.0, 210.0, 220.0, 240.0]
    all_rows: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for expiry_index, expiry in enumerate(expiries):
        days = _days_to_expiry(expiry, fetched_at)
        calls: list[dict[str, Any]] = []
        puts: list[dict[str, Any]] = []
        for strike_index, strike in enumerate(strikes):
            volatility = 0.21 + abs(strike / spot - 1.0) * 0.24 + expiry_index * 0.012
            for option_type, target in (("call", calls), ("put", puts)):
                premium = black_scholes_price(option_type, spot, strike, max(days, 1) / 365.25, _MODEL_RATE_ASSUMPTION, volatility, _MODEL_DIVIDEND_ASSUMPTION)
                target.append({
                    "contractSymbol": f"AAPL{expiry.replace('-', '')}{option_type[0].upper()}{int(strike * 1000):08d}",
                    "lastTradeDate": fetched_at,
                    "strike": strike,
                    "lastPrice": round(premium, 4),
                    "bid": round(max(0.01, premium * 0.98), 4),
                    "ask": round(max(0.02, premium * 1.02), 4),
                    "volume": 50 + strike_index * 17 + expiry_index * 11,
                    "openInterest": 400 + (len(strikes) - abs(strike_index - 3)) * 140 + expiry_index * 40,
                    "impliedVolatility": volatility,
                    "inTheMoney": strike < spot if option_type == "call" else strike > spot,
                    "contractSize": "REGULAR",
                    "currency": "USD",
                })
        normalized = normalize_provider_option_rows(
            symbol="AAPL",
            expiry=expiry,
            calls=calls,
            puts=puts,
            underlying_price=spot,
            fetched_at=fetched_at,
            source_status="fixture",
            provider="phase5j.fixture",
            source_url="https://example.test/phase-5j/options/AAPL",
        )
        all_rows.extend(normalized["rows"])
        rejected.extend(normalized["rejected_rows"])
    return all_rows, rejected, expiries, expiries[0]


def _runtime_rows(symbol: str, requested_expiry: str | None) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str], str | None, dict[str, Any], list[str]]:
    key = f"{symbol}:{requested_expiry or 'nearest'}"
    now = time.monotonic()
    with _CACHE_LOCK:
        cached = _RUNTIME_CACHE.get(key)
        if cached and now - cached["stored_at"] <= _CACHE_TTL_SECONDS:
            rows = deepcopy(cached["rows"])
            for row in rows:
                row["source_status"] = "cached"
                row["freshness"] = "cached"
            return rows, deepcopy(cached["rejected_rows"]), list(cached["expiries"]), cached["selected_expiry"], {**cached["status"], "status": "cached", "cached": True}, []

        try:
            expiries, expiry_status = get_options_expirations(symbol)
            expiry_status_dict = _status_dict(expiry_status)
            if not expiries:
                raise RuntimeError(expiry_status_dict.get("error") or "No option expiries returned by provider.")
            selected = requested_expiry if requested_expiry in expiries else expiries[0]
            selected_index = expiries.index(selected)
            analysis_expiries = expiries[selected_index:selected_index + 3]
            if selected not in analysis_expiries:
                analysis_expiries.insert(0, selected)
            fetched_at = _now_iso()
            rows: list[dict[str, Any]] = []
            rejected: list[dict[str, Any]] = []
            failures: list[str] = []
            for expiry in analysis_expiries:
                chain, chain_status = get_options_chain(symbol, expiry)
                chain_status_dict = _status_dict(chain_status)
                if not chain_status_dict.get("status") in {"fresh", "live", "ok", "available"} and not getattr(chain_status, "ok", False):
                    failures.append(str(chain_status_dict.get("error") or f"{expiry}: unavailable"))
                    continue
                normalized = normalize_provider_option_rows(
                    symbol=symbol,
                    expiry=expiry,
                    calls=chain.get("calls"),
                    puts=chain.get("puts"),
                    underlying_price=chain.get("underlying_price"),
                    fetched_at=fetched_at,
                    source_status="live/fresh",
                )
                rows.extend(normalized["rows"])
                rejected.extend(normalized["rejected_rows"])
            if not rows:
                raise RuntimeError("; ".join(failures) or "Provider returned no valid option rows.")
            status = {
                "provider": expiry_status_dict.get("provider") or "yfinance options",
                "source": f"{symbol} option expiries and chains",
                "source_url": f"https://finance.yahoo.com/quote/{quote(symbol)}/options",
                "status": "fresh",
                "fetched_at": fetched_at,
                "cached": False,
                "error": None,
            }
            _RUNTIME_CACHE[key] = {
                "stored_at": now,
                "rows": deepcopy(rows),
                "rejected_rows": deepcopy(rejected),
                "expiries": list(expiries),
                "selected_expiry": selected,
                "status": deepcopy(status),
            }
            gaps = failures
            if requested_expiry and requested_expiry not in expiries:
                gaps.append(f"Requested expiry {requested_expiry} was unavailable; nearest provider expiry selected.")
            return rows, rejected, list(expiries), selected, status, gaps
        except Exception as exc:
            if cached and now - cached["stored_at"] <= _CACHE_STALE_SECONDS:
                rows = deepcopy(cached["rows"])
                for row in rows:
                    row["source_status"] = "stale"
                    row["freshness"] = "stale"
                    row["data_gap"] = f"{row['data_gap']} Live refresh failed: {exc}"
                return rows, deepcopy(cached["rejected_rows"]), list(cached["expiries"]), cached["selected_expiry"], {**cached["status"], "status": "stale", "cached": True, "warning": str(exc)}, [str(exc)]
            return [], [], [], requested_expiry, {
                "provider": "yfinance options",
                "source": f"{symbol} option expiries and chains",
                "source_url": f"https://finance.yahoo.com/quote/{quote(symbol)}/options",
                "status": "unavailable",
                "fetched_at": _now_iso(),
                "cached": False,
                "error": str(exc),
            }, [str(exc)]


def reset_options_quant_cache() -> None:
    with _CACHE_LOCK:
        _RUNTIME_CACHE.clear()


def _iv_payloads(rows: list[dict[str, Any]], selected_expiry: str | None) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], bool]:
    valid = [row for row in rows if row.get("provider_iv") is not None and float(row["provider_iv"]) > 0]
    smile = [
        {
            "contract_symbol": row["contract_symbol"],
            "expiry": row["expiry"],
            "strike": row["strike"],
            "option_type": row["option_type"],
            "moneyness": row["moneyness"],
            "implied_volatility": row["provider_iv"],
            "source_status": row["source_status"],
            "not_financial_advice": True,
        }
        for row in valid
        if row.get("expiry") == selected_expiry
    ]
    term: list[dict[str, Any]] = []
    for expiry in sorted({str(row["expiry"]) for row in valid}):
        members = [row for row in valid if row["expiry"] == expiry]
        if not members:
            continue
        nearest = sorted(members, key=lambda row: (abs(float(row["strike"]) / float(row["underlying_price"]) - 1.0), row["option_type"]))[:2]
        term.append({
            "expiry": expiry,
            "days_to_expiry": nearest[0]["days_to_expiry"],
            "atm_implied_volatility": sum(float(row["provider_iv"]) for row in nearest) / len(nearest),
            "sample_count": len(nearest),
            "source_status": nearest[0]["source_status"],
            "not_financial_advice": True,
        })
    counts = {expiry: len({float(row["strike"]) for row in valid if row["expiry"] == expiry}) for expiry in {row["expiry"] for row in valid}}
    eligible_expiries = {expiry for expiry, count in counts.items() if count >= 3}
    surface_ready = len(eligible_expiries) >= 2
    surface = [
        {
            "expiry": row["expiry"],
            "days_to_expiry": row["days_to_expiry"],
            "strike": row["strike"],
            "option_type": row["option_type"],
            "moneyness_ratio": float(row["strike"]) / float(row["underlying_price"]),
            "implied_volatility": row["provider_iv"],
            "source_status": row["source_status"],
            "not_financial_advice": True,
        }
        for row in valid
        if row["expiry"] in eligible_expiries
    ] if surface_ready else []
    return smile, term, surface, surface_ready


def _gamma_exposure(rows: list[dict[str, Any]], selected_expiry: str | None) -> tuple[list[dict[str, Any]], bool]:
    aggregates: dict[float, dict[str, float]] = {}
    eligible = [
        row for row in rows
        if row.get("expiry") == selected_expiry
        and row.get("gamma") is not None
        and row.get("open_interest") is not None
        and row.get("contract_multiplier") is not None
        and row.get("underlying_price") is not None
    ]
    for row in eligible:
        strike = float(row["strike"])
        sign = 1.0 if row["option_type"] == "call" else -1.0
        exposure = (
            float(row["gamma"])
            * float(row["open_interest"])
            * float(row["contract_multiplier"])
            * float(row["underlying_price"]) ** 2
            * 0.01
            * sign
        )
        target = aggregates.setdefault(strike, {"call": 0.0, "put": 0.0, "net": 0.0})
        target[row["option_type"]] += exposure
        target["net"] += exposure
    output = [
        {
            "strike": strike,
            "call_gamma_exposure": values["call"],
            "put_gamma_exposure": values["put"],
            "net_gamma_exposure": values["net"],
            "unit": "currency exposure proxy per 1 percentage-point spot move",
            "dealer_sign_convention": "calls positive, puts negative",
            "observed_dealer_positioning": False,
            "not_financial_advice": True,
        }
        for strike, values in sorted(aggregates.items())
    ]
    return output, bool(output)


def _scenario_rows(rows: list[dict[str, Any]], selected_expiry: str | None, selected_contract: str | None = None) -> tuple[list[dict[str, Any]], str | None]:
    candidates = [row for row in rows if row.get("expiry") == selected_expiry and row.get("provider_iv") and row.get("model_status") == "calculated"]
    if not candidates:
        return [], None
    selected = next((row for row in candidates if row.get("contract_symbol") == selected_contract), None)
    selected = selected or min(candidates, key=lambda row: (abs(float(row["strike"]) / float(row["underlying_price"]) - 1.0), row["option_type"] != "call"))
    spot = float(selected["underlying_price"])
    volatility = float(selected["provider_iv"])
    premium = selected.get("mid") if selected.get("mid") not in (None, 0) else selected.get("last")
    try:
        scenario = option_scenario_grid(
            {
                "option_type": selected["option_type"],
                "underlying_price": spot,
                "strike": selected["strike"],
                "time_to_expiry_years": selected["time_to_expiry_years"],
                "risk_free_rate": selected["risk_free_rate"],
                "dividend_yield": selected["dividend_yield"],
                "volatility": volatility,
                "contract_multiplier": selected["contract_multiplier"],
                "premium": premium,
                "model": selected["model"],
            },
            price_grid=[spot * value for value in (0.90, 0.95, 1.0, 1.05, 1.10)],
            volatility_grid=[max(0.01, volatility + value) for value in (-0.05, 0.0, 0.05)],
            time_grid=[selected["time_to_expiry_years"]],
            rate_grid=[selected["risk_free_rate"]],
        )
    except (TypeError, ValueError, ZeroDivisionError, OverflowError):
        return [], selected["contract_symbol"]
    output = []
    for row in scenario.get("rows", []):
        output.append({
            **row,
            "spot_change_pct": (float(row["underlying_price"]) / spot - 1.0) * 100.0,
            "volatility_change_points": (float(row["volatility"]) - volatility) * 100.0,
            "contract_symbol": selected["contract_symbol"],
            "model": selected["model"],
            "not_financial_advice": True,
        })
    return output, selected["contract_symbol"]


def _quality(rows: list[dict[str, Any]], rejected: list[dict[str, Any]]) -> dict[str, Any]:
    flag_counts: dict[str, int] = {}
    for row in rows:
        for flag in row.get("quality_flags") or []:
            flag_counts[str(flag)] = flag_counts.get(str(flag), 0) + 1
    total = len(rows) + len(rejected)
    score = 0.0 if total == 0 else max(0.0, 100.0 - len(rejected) / total * 50.0 - sum(flag_counts.values()) / max(len(rows), 1) * 4.0)
    return {
        "total_rows": total,
        "accepted_rows": len(rows),
        "rejected_rows": len(rejected),
        "quality_score": round(score, 2),
        "flag_counts": flag_counts,
        "missing_open_interest_rows": flag_counts.get("missing_open_interest", 0),
        "missing_iv_rows": flag_counts.get("missing_or_zero_provider_iv", 0),
        "wide_spread_rows": flag_counts.get("wide_spread", 0),
        "zero_market_rows": flag_counts.get("zero_bid_ask", 0),
        "research_only": True,
    }


def build_options_quant_workstation_contract(
    symbol: str = "AAPL",
    *,
    expiry: str | None = None,
    include_runtime: bool = False,
    selected_contract: str | None = None,
) -> dict[str, Any]:
    symbol = str(symbol or "AAPL").strip().upper()
    data_gaps: list[str] = []
    if include_runtime:
        rows, rejected, expiries, selected_expiry, status, runtime_gaps = _runtime_rows(symbol, expiry)
        data_gaps.extend(runtime_gaps)
    else:
        rows, rejected, expiries, default_expiry = _fixture_rows()
        selected_expiry = expiry if expiry in expiries else default_expiry
        status = {
            "provider": "phase5j.fixture",
            "source": "deterministic option chain fixture",
            "source_url": "https://example.test/phase-5j/options/AAPL",
            "status": "fixture",
            "fetched_at": "2026-06-20T16:00:00+00:00",
            "cached": False,
            "error": None,
        }

    source_status = str(status.get("status") or "unavailable")
    if source_status == "fresh":
        source_status = "live/fresh"
    smile, term, surface, surface_ready = _iv_payloads(rows, selected_expiry)
    exposure, gex_ready = _gamma_exposure(rows, selected_expiry)
    scenarios, selected_contract = _scenario_rows(rows, selected_expiry, selected_contract)
    quality = _quality(rows, rejected)
    selected_rows = [row for row in rows if row.get("expiry") == selected_expiry]
    spot = next((row.get("underlying_price") for row in selected_rows if row.get("underlying_price") is not None), None)
    greeks_rows = [
        {
            "contract_symbol": row["contract_symbol"],
            "expiry": row["expiry"],
            "strike": row["strike"],
            "option_type": row["option_type"],
            "delta": row.get("delta"),
            "gamma": row.get("gamma"),
            "vega": row.get("vega"),
            "theta_per_day": row.get("theta_per_day"),
            "contract_delta": (row.get("contract_greeks") or {}).get("contract_delta"),
            "contract_gamma": (row.get("contract_greeks") or {}).get("contract_gamma"),
            "contract_vega_1pct": (row.get("contract_greeks") or {}).get("contract_vega_1pct"),
            "contract_theta_1day": (row.get("contract_greeks") or {}).get("contract_theta_1day"),
            "model": row.get("model"),
            "model_status": row.get("model_status"),
            "source_status": row.get("source_status"),
            "research_only": True,
            "not_financial_advice": True,
        }
        for row in selected_rows
        if row.get("model_status") == "calculated"
    ]
    unavailable: list[dict[str, Any]] = []
    if not rows:
        unavailable.append({
            "provider": status.get("provider") or "yfinance options",
            "capability": "option chain",
            "source_status": "unavailable",
            "availability": "unavailable",
            "data_gap": status.get("error") or "No valid option-chain rows are available.",
            "recommended_action": "Retry later or use deterministic fixture mode.",
            "not_financial_advice": True,
        })
    if not surface_ready:
        unavailable.append({
            "provider": status.get("provider") or "yfinance options",
            "capability": "volatility surface",
            "source_status": "unavailable",
            "availability": "unavailable",
            "data_gap": "Surface requires at least two expiries with three valid strikes each.",
            "recommended_action": "Select a broader chain snapshot or inspect the IV smile instead.",
            "not_financial_advice": True,
        })
    if not gex_ready:
        unavailable.append({
            "provider": status.get("provider") or "yfinance options",
            "capability": "gamma exposure research proxy",
            "source_status": "unavailable",
            "availability": "unavailable",
            "data_gap": "Gamma exposure requires gamma, open interest, multiplier, and spot.",
            "recommended_action": "Inspect missing OI/IV quality flags.",
            "not_financial_advice": True,
        })
    if not include_runtime:
        unavailable.append({
            "provider": "yfinance options",
            "capability": "live option chain",
            "source_status": "provider-required",
            "availability": "unavailable",
            "data_gap": "Fixture mode does not claim a live option chain.",
            "recommended_action": "Use live-if-available mode with the optional local API.",
            "not_financial_advice": True,
        })
    if status.get("error"):
        data_gaps.append(str(status["error"]))

    provider_capabilities = [
        {
            "provider": status.get("provider") or "yfinance options",
            "capability": "equity option chain",
            "source_status": source_status,
            "freshness": source_status,
            "installed": True,
            "key_required": False,
            "used_for_calculation": bool(rows),
            "caveat": "Unofficial delayed public data; terms and reliability may change.",
            "data_gap": status.get("error") or "",
            "research_only": True,
            "not_financial_advice": True,
        },
        {
            "provider": "manual/supplied data",
            "capability": "local calculator and CSV research workflow",
            "source_status": "supplied",
            "freshness": "user-supplied",
            "installed": True,
            "key_required": False,
            "used_for_calculation": False,
            "caveat": "Separate internal-lab workflow; not substituted for provider rows.",
            "data_gap": "",
            "research_only": True,
            "not_financial_advice": True,
        },
    ]
    source_register = [
        {
            **status,
            "source_status": source_status,
            "row_count": len(rows),
            "freshness": "fixture" if source_status == "fixture" else "delayed" if source_status == "live/fresh" else source_status,
            "confidence": 0.82 if rows and source_status in {"live/fresh", "cached"} else 0.45 if rows else 0.0,
            "caveat": "Provider retrieval time and last-trade time are separate; bid/ask quote time is unavailable.",
            "data_gap": status.get("error") or "",
            "not_financial_advice": True,
        },
        {
            "provider": "options_quant_model",
            "source": "project-native Black-Scholes and scenario engines",
            "source_url": "",
            "status": "assumption-bound",
            "source_status": "assumption-bound",
            "freshness": "not_applicable",
            "fetched_at": None,
            "row_count": len(greeks_rows),
            "confidence": 0.7 if greeks_rows else 0.0,
            "caveat": "European-model approximation applied to US equity options; early exercise is not modeled.",
            "data_gap": "Risk free rate, dividend yield, multiplier, and exercise style are assumptions unless provider-supplied.",
            "not_financial_advice": True,
        },
    ]
    if not include_runtime:
        source_register.append({
            "provider": "yfinance options",
            "source": f"{symbol} option expiries and chains",
            "source_url": f"https://finance.yahoo.com/quote/{quote(symbol)}/options",
            "status": "provider-required",
            "source_status": "provider-required",
            "freshness": "unavailable",
            "fetched_at": None,
            "row_count": 0,
            "confidence": 0.0,
            "caveat": "Fixture mode is deterministic and does not claim provider rows.",
            "data_gap": "Use live-if-available mode with the optional local API.",
            "not_financial_advice": True,
        })
    legacy_greeks = []
    selected_greek_row = next((row for row in greeks_rows if row["contract_symbol"] == selected_contract), greeks_rows[0] if greeks_rows else None)
    if selected_greek_row:
        for greek, unit in (("delta", "per underlying unit"), ("gamma", "delta change per underlying unit"), ("vega", "per 1.00 volatility point"), ("theta_per_day", "per calendar day")):
            legacy_greeks.append({"greek": greek, "value": selected_greek_row.get(greek), "unit": unit, "research_only": True, "not_financial_advice": True})

    return {
        "options_quant_version": OPTIONS_QUANT_WORKSTATION_VERSION,
        "workspace": "options-quant",
        "symbol": symbol,
        "underlying_price": spot,
        "expiries": expiries,
        "selected_expiry": selected_expiry,
        "selected_contract": selected_contract,
        "chain_rows": rows,
        "rejected_rows": rejected,
        "iv_smile": smile,
        "iv_term_structure": term,
        "surface_points": surface,
        "greeks_rows": greeks_rows,
        "greek_units": build_greek_units_table(_CONTRACT_MULTIPLIER_ASSUMPTION),
        "gamma_exposure_by_strike": exposure,
        "scenario_rows": scenarios,
        "quality": quality,
        "assumptions": {
            "pricing_model": "Black-Scholes equity-option research approximation",
            "risk_free_rate": {"value": _MODEL_RATE_ASSUMPTION, "source_status": "explicit-assumption", "unit": "decimal annual rate"},
            "dividend_yield": {"value": _MODEL_DIVIDEND_ASSUMPTION, "source_status": "explicit-assumption", "unit": "decimal annual yield"},
            "contract_multiplier": {"value": _CONTRACT_MULTIPLIER_ASSUMPTION, "source_status": "assumed_us_equity_standard"},
            "exercise_style": {"value": "American", "source_status": "assumed_us_equity_standard", "model_gap": "Early exercise is not modeled."},
            "dealer_sign_convention": {
                "value": "calls positive, puts negative",
                "source_status": "explicit-assumption",
                "observed_dealer_positioning": False,
            },
            "timestamp_alignment": "retrieval time and provider last-trade time preserved separately; quote time unavailable",
        },
        "provider_capabilities": provider_capabilities,
        "source_register": source_register,
        "unavailable_sources": unavailable,
        "data_gaps": sorted(dict.fromkeys(str(gap) for gap in data_gaps if gap)),
        "readiness": {
            "live_option_chain_claimed": bool(include_runtime and rows and source_status in {"live/fresh", "cached", "stale"}),
            "surface_ready": surface_ready,
            "gex_ready": gex_ready,
            "gex_claimed": False,
            "dealer_positioning_claimed": False,
            "manual_calculator_available": True,
            "provider_required": not bool(rows),
            "broker_execution_added": False,
            "account_action_added": False,
            "non_advisory": True,
        },
        "summary": {
            "workspace": "options-quant",
            "symbol": symbol,
            "selected_expiry": selected_expiry,
            "expiry_count": len(expiries),
            "chain_row_count": len(rows),
            "rejected_row_count": len(rejected),
            "iv_point_count": len(smile),
            "greeks_row_count": len(greeks_rows),
            "scenario_row_count": len(scenarios),
            "source_status": source_status if rows else "unavailable",
            "quality_score": quality["quality_score"],
            "runtime_requested": bool(include_runtime),
            "broker_execution_added": False,
            "non_advisory": True,
        },
        # Backward-compatible fields used by the prior diagnostics fixture.
        "options_gamma_proxy": {
            "source_status": source_status if rows else "unavailable",
            "provider": status.get("provider") or "yfinance options",
            "freshness": source_status,
            "estimated_gamma_concentration_proxy": max(exposure, key=lambda row: abs(row["net_gamma_exposure"]))["strike"] if exposure else None,
            "caveat": "Assumption-dependent research exposure; not observed dealer positioning.",
            "data_gap": "" if exposure else "Required OI/gamma inputs are unavailable.",
            "not_financial_advice": True,
        },
        "pricing_preview": {"contract_symbol": selected_contract, "model": "black_scholes", "research_only": True},
        "greeks_table": legacy_greeks,
        "scenario_table": scenarios[:15],
        "strategy_templates": [],
        "scenario_matrix": [],
        "command_routes": [
            {"raw": f"{symbol} OMON", "target_view": "options-quant", "source_status": source_status, "not_financial_advice": True},
            {"raw": "SOLVE IV", "target_view": "options-quant", "source_status": "supplied", "not_financial_advice": True},
        ],
        "caveat": _DISCLOSURE,
        "not_financial_advice": True,
    }
