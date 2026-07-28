from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .data_status import DataResult, combine_results, error_result, ok_result
from .fundamentals import (
    build_financial_overview as build_fundamental_overview,
    compute_balance_sheet_quality,
    compute_growth_rates,
    compute_margin_series,
    get_balance_sheet,
    get_cash_flow,
    get_financial_statements,
    get_income_statement,
    get_key_ratios,
)
from .openbb_bridge import OPENBB_CAVEAT, is_openbb_installed, openbb_available_result
from .openbb_provider_adapter import (
    get_openbb_balance_sheet,
    get_openbb_cash_flow,
    get_openbb_company_profile,
    get_openbb_estimates,
    get_openbb_filings,
    get_openbb_income_statement,
    get_openbb_metrics,
    get_openbb_ownership,
    get_openbb_peers,
    get_openbb_price_history,
    get_openbb_ratios,
    get_openbb_revenue_geography,
    get_openbb_revenue_segments,
)

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None

try:
    import yfinance as yf
except Exception:  # pragma: no cover
    yf = None


def _empty_frame():
    return pd.DataFrame() if pd is not None else []


def _ticker(ticker: str):
    if yf is None:
        return None
    try:
        return yf.Ticker(ticker)
    except Exception:
        return None


def _caveat(*items: str) -> list[str]:
    return [item for item in items if item]


def _payload(data: Any, status: DataResult, caveats: list[str]) -> tuple[Any, DataResult, list[str]]:
    return data, status, caveats


SOURCE_MODES = ["Auto", "Native only", "OpenBB preferred", "OpenBB only"]


def normalize_financial_source_mode(source_mode: str | None = None) -> str:
    lookup = {mode.lower(): mode for mode in SOURCE_MODES}
    return lookup.get(str(source_mode or "Auto").strip().lower(), "Auto")


def _result_frame(result: DataResult):
    data = getattr(result, "data", None)
    if pd is None:
        return data or []
    return data.copy() if hasattr(data, "copy") and hasattr(data, "columns") else pd.DataFrame()


def _latest_record(frame) -> dict[str, Any]:
    if pd is None or frame is None or getattr(frame, "empty", True):
        return {}
    clean = frame.dropna(how="all")
    if clean.empty:
        return {}
    return clean.iloc[-1].to_dict()


def _availability_rows(results: dict[str, DataResult], *, ticker: str):
    rows = []
    for field, result in results.items():
        frame = _result_frame(result)
        rows.append(
            {
                "provider": result.provider,
                "field": field,
                "available": bool(result.ok and not getattr(frame, "empty", True)),
                "status": result.refreshed_status(),
                "source": result.source,
                "last_updated": result.fetched_at.isoformat(),
                "caveat": getattr(result, "caveat", OPENBB_CAVEAT),
                "ticker": ticker.upper(),
            }
        )
    return pd.DataFrame(rows) if pd is not None else rows


def _coerce_revenue_breakdown(result: DataResult, *, label: str):
    frame = _result_frame(result)
    if pd is None or frame is None or getattr(frame, "empty", True):
        return _empty_frame()
    output = frame.copy()
    output.columns = [str(col).strip().lower().replace(" ", "_") for col in output.columns]
    if label not in output.columns:
        text_cols = [col for col in output.columns if output[col].dtype == "object"]
        if text_cols:
            output = output.rename(columns={text_cols[0]: label})
    if "revenue" not in output.columns:
        numeric = [col for col in output.select_dtypes("number").columns if col != label]
        if numeric:
            output = output.rename(columns={numeric[0]: "revenue"})
    return output if {label, "revenue"}.issubset(output.columns) else _empty_frame()


def _call_periodic(builder, ticker: str, period: str):
    """Call financial builders across older/newer signatures.

    Some local sessions can keep an older `fundamentals.build_financial_overview`
    loaded that does not accept `period`. The page should still render with an
    explicit caveat instead of crashing.
    """
    try:
        return builder(ticker, period=period)
    except TypeError as exc:
        if "period" not in str(exc):
            raise
        data, status = builder(ticker)
        if isinstance(data, dict):
            data = {**data, "period": data.get("period") or "annual", "period_request_data_gap": f"Requested {period}, provider function used annual fallback."}
        if getattr(status, "warning", None):
            status.warning = f"{status.warning}; Requested {period}, used annual fallback because the loaded fundamentals builder lacks period support."
        else:
            status.warning = f"Requested {period}, used annual fallback because the loaded fundamentals builder lacks period support."
        return data, status


def _latest(frame, field: str):
    if pd is None or frame is None or getattr(frame, "empty", True) or field not in frame.columns:
        return None
    series = frame[field].dropna()
    return None if series.empty else series.iloc[-1]


def _safe_info(ticker: str) -> tuple[dict[str, Any], DataResult]:
    if yf is None:
        return {}, error_result(source=f"{ticker} yfinance info", provider="yfinance", error="yfinance is not installed", coverage="missing")
    obj = _ticker(ticker)
    if obj is None:
        return {}, error_result(source=f"{ticker} yfinance info", provider="yfinance", error="Ticker object unavailable", coverage="missing")
    try:
        info = getattr(obj, "info", {}) or {}
        return info, ok_result(info, source=f"{ticker} yfinance info", provider="yfinance", coverage=f"{len(info)} fields")
    except Exception as exc:
        return {}, error_result(source=f"{ticker} yfinance info", provider="yfinance", error=str(exc), coverage="missing")


def build_company_header(ticker: str):
    info, status = _safe_info(ticker)
    fast_price = None
    obj = _ticker(ticker)
    if obj is not None:
        try:
            fast = getattr(obj, "fast_info", {}) or {}
            fast_price = fast.get("last_price") if hasattr(fast, "get") else None
        except Exception:
            fast_price = None
    data = {
        "ticker": ticker.upper(),
        "company_name": info.get("longName") or info.get("shortName") or ticker.upper(),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "market_cap": info.get("marketCap"),
        "current_price": info.get("currentPrice") or info.get("regularMarketPrice") or fast_price,
        "currency": info.get("currency"),
        "exchange": info.get("exchange") or info.get("fullExchangeName"),
        "source_status": status.to_dict(),
    }
    caveats = _caveat("Company fields depend on yfinance availability.", None if status.ok else status.error)
    return _payload(data, status, caveats)


def build_financial_overview(ticker: str, period: str = "annual"):
    overview, status = _call_periodic(build_fundamental_overview, ticker, period)
    caveats = _caveat(
        "Financial statements use yfinance reported fields where available.",
        "Ratios are source-derived or derived from reported statements; missing fields remain missing.",
        None if status.ok else status.error,
    )
    return _payload(overview, status, caveats)


def build_statement_tables(ticker: str, period: str = "annual"):
    statements, status = get_financial_statements(ticker, period=period)
    caveats = _caveat("Annual/quarterly tables are provider-dependent.", None if status.ok else status.error)
    return _payload(statements, status, caveats)


def build_statistics_panel(ticker: str, period: str = "annual"):
    overview, status = _call_periodic(build_fundamental_overview, ticker, period)
    ratios = overview.get("ratios", {})
    rows = []
    categories = {
        "valuation": ["trailing_pe", "forward_pe", "price_to_sales", "price_to_book", "ev_to_ebitda"],
        "profitability": ["roe", "roa", "roic", "gross_margin", "operating_margin", "net_margin", "fcf_margin"],
        "liquidity": ["current_ratio", "quick_ratio"],
        "leverage": ["debt_to_equity"],
    }
    for category, keys in categories.items():
        for key in keys:
            rows.append({"category": category, "metric": key, "value": ratios.get(key), "available": ratios.get(key) is not None})
    frame = pd.DataFrame(rows) if pd is not None else rows
    caveats = _caveat("Statistics are source-derived or derivable from reported fields.", "Unavailable values are left blank.")
    return _payload(frame, status, caveats)


def build_valuation_panel(ticker: str, period: str = "annual"):
    overview, overview_status = _call_periodic(build_fundamental_overview, ticker, period)
    header, header_status, _ = build_company_header(ticker)
    ratios = overview.get("ratios", {})
    income = overview.get("income")
    data = {
        "ratios": ratios,
        "market_cap": header.get("market_cap"),
        "current_price": header.get("current_price"),
        "revenue": _latest(income, "revenue") or _latest(income, "total_revenue"),
        "net_income": _latest(income, "net_income"),
        "caveat": "Valuation panel does not estimate fair value or generate directives.",
    }
    status = combine_results([overview_status, header_status], provider="financial_terminal", source=f"{ticker} valuation panel")
    return _payload(data, status, [data["caveat"]])


def _earnings_dates(ticker: str):
    if pd is None:
        return []
    obj = _ticker(ticker)
    if obj is None:
        return pd.DataFrame(), error_result(source=f"{ticker} earnings dates", provider="yfinance", error="Ticker object unavailable", coverage="missing")
    try:
        getter = getattr(obj, "get_earnings_dates", None)
        frame = getter(limit=16) if callable(getter) else getattr(obj, "earnings_dates", None)
        if frame is None or getattr(frame, "empty", True):
            return pd.DataFrame(), error_result(source=f"{ticker} earnings dates", provider="yfinance", error="Earnings dates unavailable", coverage="missing")
        out = frame.copy().reset_index()
        out.columns = [str(col).strip().lower().replace(" ", "_") for col in out.columns]
        rename = {
            "earnings_date": "period",
            "eps_estimate": "eps_estimate",
            "reported_eps": "eps_actual",
            "surprise(%)": "eps_surprise_pct",
        }
        out = out.rename(columns=rename)
        return out, ok_result(out, source=f"{ticker} yfinance earnings dates", provider="yfinance", coverage=f"{len(out)} rows")
    except Exception as exc:
        return pd.DataFrame(), error_result(source=f"{ticker} earnings dates", provider="yfinance", error=str(exc), coverage="missing")


def build_earnings_panel(ticker: str):
    frame, status = _earnings_dates(ticker)
    next_report = None
    if pd is not None and not getattr(frame, "empty", True) and "period" in frame.columns:
        dated = frame.copy()
        dated["period_dt"] = pd.to_datetime(dated["period"], utc=True, errors="coerce")
        future = dated[dated["period_dt"] >= pd.Timestamp.now(tz="UTC")].sort_values("period_dt")
        if not future.empty:
            next_report = str(future.iloc[0]["period"])
    data = {"earnings_history": frame, "next_report_date": next_report, "has_estimates": bool(pd is not None and not getattr(frame, "empty", True) and any(col in frame.columns for col in ["eps_estimate", "revenue_estimate"]))}
    caveats = _caveat("Earnings estimates are displayed only when yfinance supplies them.", None if status.ok else "Earnings estimate/history data gap.")
    return _payload(data, status, caveats)


def build_revenue_panel(ticker: str, period: str = "annual"):
    overview, status = _call_periodic(build_fundamental_overview, ticker, period)
    income = overview.get("income")
    growth = overview.get("growth")
    data = {
        "total_revenue": income[[col for col in ["revenue", "total_revenue"] if col in getattr(income, "columns", [])]] if income is not None and not getattr(income, "empty", True) else _empty_frame(),
        "revenue_growth": growth[[col for col in ["revenue", "total_revenue"] if col in getattr(growth, "columns", [])]] if growth is not None and not getattr(growth, "empty", True) else _empty_frame(),
        "segment_revenue": _empty_frame(),
        "geographic_revenue": _empty_frame(),
        "data_gap": "Segment/geographic revenue is not fabricated; optional provider data is required when yfinance does not supply it.",
    }
    caveats = _caveat(data["data_gap"])
    return _payload(data, status, caveats)


def build_cashflow_panel(ticker: str, period: str = "annual"):
    cashflow, status = get_cash_flow(ticker, period=period)
    income, income_status = get_income_statement(ticker, period=period)
    fcf_margin = _empty_frame()
    if pd is not None and not getattr(cashflow, "empty", True) and not getattr(income, "empty", True):
        revenue = income["revenue"].replace(0, pd.NA) if "revenue" in income.columns else None
        if revenue is not None and "free_cash_flow" in cashflow.columns:
            fcf_margin = pd.DataFrame({"fcf_margin": cashflow["free_cash_flow"] / revenue})
    combined = combine_results([status, income_status], provider="financial_terminal", source=f"{ticker} cashflow panel")
    data = {"cashflow": cashflow, "fcf_margin": fcf_margin}
    return _payload(data, combined, ["Free cash flow margin is derived only when reported cash flow and revenue exist."])


def build_balance_sheet_panel(ticker: str, period: str = "annual"):
    balance, status = get_balance_sheet(ticker, period=period)
    data = {
        "balance": balance,
        "liquidity_fields": balance[[col for col in ["cash_and_equivalents", "current_assets", "current_liabilities", "working_capital"] if col in getattr(balance, "columns", [])]] if balance is not None and not getattr(balance, "empty", True) else _empty_frame(),
        "leverage_fields": balance[[col for col in ["total_debt", "net_debt", "total_assets", "shareholders_equity"] if col in getattr(balance, "columns", [])]] if balance is not None and not getattr(balance, "empty", True) else _empty_frame(),
    }
    return _payload(data, status, ["Balance sheet fields are reported or provider-derived; missing rows remain data gaps."])


def build_data_availability_matrix(ticker: str, period: str = "annual"):
    statements, statement_status = get_financial_statements(ticker, period=period)
    ratios, ratio_status = get_key_ratios(ticker)
    earnings, earnings_status, _ = build_earnings_panel(ticker)
    rows = []
    for statement_name, frame in statements.items():
        if statement_name == "period":
            continue
        fields = list(getattr(frame, "columns", []))
        if fields:
            for field in fields:
                rows.append(
                    {
                        "provider": "yfinance",
                        "field": f"{statement_name}.{field}",
                        "available": bool(frame[field].notna().any()) if hasattr(frame, "__getitem__") else False,
                        "status": statement_status.refreshed_status(),
                        "source": statement_status.source,
                        "last_updated": statement_status.fetched_at.isoformat(),
                        "caveat": "Reported financial statement field.",
                    }
                )
        else:
            rows.append(
                {
                    "provider": "yfinance",
                    "field": statement_name,
                    "available": False,
                    "status": "missing",
                    "source": statement_status.source,
                    "last_updated": statement_status.fetched_at.isoformat(),
                    "caveat": "Statement unavailable.",
                }
            )
    for field, value in ratios.items():
        rows.append(
            {
                "provider": "yfinance",
                "field": f"ratio.{field}",
                "available": value is not None,
                "status": ratio_status.refreshed_status(),
                "source": ratio_status.source,
                "last_updated": ratio_status.fetched_at.isoformat(),
                "caveat": "Source-derived or statement-derived ratio.",
            }
        )
    rows.append(
        {
            "provider": "yfinance",
            "field": "earnings.history_or_estimates",
            "available": bool(earnings.get("has_estimates")),
            "status": earnings_status.refreshed_status(),
            "source": earnings_status.source,
            "last_updated": earnings_status.fetched_at.isoformat(),
            "caveat": "Forecast/estimate fields are shown only when supplied by the provider.",
        }
    )
    frame = pd.DataFrame(rows) if pd is not None else rows
    status = combine_results([statement_status, ratio_status, earnings_status], provider="financial_terminal", source=f"{ticker} data availability")
    return _payload(frame, status, ["Availability matrix distinguishes available, missing, and provider-limited fields."])


def _build_native_financial_terminal_state(ticker: str, period: str = "annual") -> dict[str, Any]:
    header, header_status, header_caveats = build_company_header(ticker)
    overview, overview_status, overview_caveats = build_financial_overview(ticker, period=period)
    statements, statement_status, statement_caveats = build_statement_tables(ticker, period=period)
    statistics, statistics_status, statistics_caveats = build_statistics_panel(ticker, period=period)
    valuation, valuation_status, valuation_caveats = build_valuation_panel(ticker, period=period)
    earnings, earnings_status, earnings_caveats = build_earnings_panel(ticker)
    revenue, revenue_status, revenue_caveats = build_revenue_panel(ticker, period=period)
    cashflow, cashflow_status, cashflow_caveats = build_cashflow_panel(ticker, period=period)
    balance, balance_status, balance_caveats = build_balance_sheet_panel(ticker, period=period)
    availability, availability_status, availability_caveats = build_data_availability_matrix(ticker, period=period)
    statuses = [header_status, overview_status, statement_status, statistics_status, valuation_status, earnings_status, revenue_status, cashflow_status, balance_status, availability_status]
    return {
        "ticker": ticker.upper(),
        "period": period,
        "built_at": datetime.now(timezone.utc).isoformat(),
        "header": header,
        "overview": overview,
        "statements": statements,
        "statistics": statistics,
        "valuation": valuation,
        "earnings": earnings,
        "revenue": revenue,
        "cashflow": cashflow,
        "balance_sheet": balance,
        "availability": availability,
        "statuses": statuses,
        "status": combine_results(statuses, provider="financial_terminal", source=f"{ticker} financial terminal state"),
        "caveats": header_caveats
        + overview_caveats
        + statement_caveats
        + statistics_caveats
        + valuation_caveats
        + earnings_caveats
        + revenue_caveats
        + cashflow_caveats
        + balance_caveats
        + availability_caveats,
    }


def _build_openbb_financial_terminal_state(ticker: str, period: str = "annual", *, source_mode: str = "OpenBB only") -> dict[str, Any]:
    results = {
        "profile": get_openbb_company_profile(ticker),
        "price_history": get_openbb_price_history(ticker),
        "income": get_openbb_income_statement(ticker, period=period),
        "balance": get_openbb_balance_sheet(ticker, period=period),
        "cashflow": get_openbb_cash_flow(ticker, period=period),
        "ratios": get_openbb_ratios(ticker, period=period),
        "metrics": get_openbb_metrics(ticker, period=period),
        "estimates": get_openbb_estimates(ticker),
        "revenue_segments": get_openbb_revenue_segments(ticker),
        "revenue_geography": get_openbb_revenue_geography(ticker),
        "filings": get_openbb_filings(ticker),
        "peers": get_openbb_peers(ticker),
        "ownership": get_openbb_ownership(ticker),
    }
    profile = _latest_record(_result_frame(results["profile"]))
    income = _result_frame(results["income"])
    balance = _result_frame(results["balance"])
    cashflow = _result_frame(results["cashflow"])
    ratios = _latest_record(_result_frame(results["ratios"]))
    metrics = _latest_record(_result_frame(results["metrics"]))
    ratio_payload = {**ratios, **{key: value for key, value in metrics.items() if key not in ratios}}
    estimates = _result_frame(results["estimates"])
    segments = _coerce_revenue_breakdown(results["revenue_segments"], label="segment")
    geography = _coerce_revenue_breakdown(results["revenue_geography"], label="geography")
    availability = _availability_rows(results, ticker=ticker)
    statuses = list(results.values())
    source_status = combine_results(statuses, provider="financial_terminal", source=f"{ticker} OpenBB financial terminal state")
    header = {
        "ticker": ticker.upper(),
        "company_name": profile.get("company_name") or profile.get("name") or ticker.upper(),
        "sector": profile.get("sector"),
        "industry": profile.get("industry"),
        "market_cap": profile.get("market_cap"),
        "current_price": None,
        "currency": profile.get("currency"),
        "exchange": profile.get("exchange"),
        "source_status": results["profile"].to_dict(),
    }
    overview = {
        "ticker": ticker.upper(),
        "income": income,
        "balance": balance,
        "cashflow": cashflow,
        "period": period,
        "growth": compute_growth_rates(income, [col for col in ["revenue", "total_revenue", "gross_profit", "operating_income", "net_income", "eps", "diluted_eps"] if col in getattr(income, "columns", [])]) if pd is not None else [],
        "margins": compute_margin_series(income),
        "balance_quality": compute_balance_sheet_quality(balance),
        "ratios": ratio_payload,
        "ttm": {"income": _empty_frame(), "cashflow": _empty_frame()},
        "availability": {
            "income": not getattr(income, "empty", True),
            "balance": not getattr(balance, "empty", True),
            "cashflow": not getattr(cashflow, "empty", True),
            "ratios": bool(ratio_payload),
            "estimates": not getattr(estimates, "empty", True),
            "segments": not getattr(segments, "empty", True),
            "geography": not getattr(geography, "empty", True),
        },
        "data_gaps": [],
    }
    overview["data_gaps"] = [name for name, available in overview["availability"].items() if not available]
    caveats = [
        OPENBB_CAVEAT,
        "OpenBB financial datasets are optional and provider-dependent.",
        "Estimates, segment revenue, and geographic revenue are displayed only when provider-supplied.",
    ] + [result.warning for result in statuses if result.warning]
    return {
        "ticker": ticker.upper(),
        "period": period,
        "built_at": datetime.now(timezone.utc).isoformat(),
        "source_mode": source_mode,
        "source_provider": "openbb",
        "openbb_installed": is_openbb_installed(),
        "fallback_used": False,
        "header": header,
        "overview": overview,
        "statements": {"income": income, "balance": balance, "cashflow": cashflow, "period": period},
        "statistics": pd.DataFrame([{"category": "openbb", "metric": key, "value": value, "available": value is not None} for key, value in ratio_payload.items()]) if pd is not None else [],
        "valuation": {"ratios": ratio_payload, "market_cap": header.get("market_cap"), "current_price": header.get("current_price"), "revenue": _latest(income, "revenue") or _latest(income, "total_revenue"), "net_income": _latest(income, "net_income"), "caveat": "Valuation panel does not estimate fair value or generate directives."},
        "earnings": {"earnings_history": estimates, "next_report_date": None, "has_estimates": bool(pd is not None and not getattr(estimates, "empty", True))},
        "revenue": {"total_revenue": income[[col for col in ["revenue", "total_revenue"] if col in getattr(income, "columns", [])]] if pd is not None and not getattr(income, "empty", True) else _empty_frame(), "revenue_growth": overview["growth"], "segment_revenue": segments, "geographic_revenue": geography, "data_gap": "Segment/geographic revenue is not fabricated; optional OpenBB provider data is required."},
        "cashflow": {"cashflow": cashflow, "fcf_margin": _empty_frame()},
        "balance_sheet": {"balance": balance, "liquidity_fields": balance[[col for col in ["cash_and_equivalents", "current_assets", "current_liabilities", "working_capital"] if col in getattr(balance, "columns", [])]] if pd is not None and not getattr(balance, "empty", True) else _empty_frame(), "leverage_fields": balance[[col for col in ["total_debt", "net_debt", "total_assets", "shareholders_equity"] if col in getattr(balance, "columns", [])]] if pd is not None and not getattr(balance, "empty", True) else _empty_frame()},
        "availability": availability,
        "filings": _result_frame(results["filings"]),
        "peers": _result_frame(results["peers"]),
        "ownership": _result_frame(results["ownership"]),
        "price_history": _result_frame(results["price_history"]),
        "statuses": statuses,
        "status": source_status,
        "caveats": [item for item in caveats if item],
    }


def _merge_openbb_over_native(native: dict[str, Any], openbb_state: dict[str, Any], *, source_mode: str) -> dict[str, Any]:
    openbb_success = any(getattr(status, "ok", False) for status in openbb_state.get("statuses", []))
    if not openbb_success:
        native["source_mode"] = source_mode
        native["source_provider"] = "native"
        native["openbb_installed"] = is_openbb_installed()
        native["fallback_used"] = True
        native["openbb_status"] = openbb_state.get("status")
        native["statuses"] = native.get("statuses", []) + openbb_state.get("statuses", [])
        native["status"] = combine_results(native["statuses"], provider="financial_terminal", source=f"{native['ticker']} financial terminal state")
        native["caveats"] = native.get("caveats", []) + ["OpenBB preferred mode used native fallback because OpenBB returned no usable financial rows."]
        return native
    merged = native.copy()
    merged["source_mode"] = source_mode
    merged["source_provider"] = "openbb+native"
    merged["openbb_installed"] = True
    merged["fallback_used"] = False
    for key in ["header", "overview", "statements", "statistics", "valuation", "earnings", "revenue", "cashflow", "balance_sheet", "availability", "filings", "peers", "ownership", "price_history"]:
        if key in openbb_state:
            merged[key] = openbb_state[key]
    merged["statuses"] = openbb_state.get("statuses", []) + native.get("statuses", [])
    merged["status"] = combine_results(merged["statuses"], provider="financial_terminal", source=f"{merged['ticker']} financial terminal state")
    merged["caveats"] = openbb_state.get("caveats", []) + ["Native yfinance path remains available as fallback."]
    return merged


def build_financial_terminal_state(ticker: str, period: str = "annual", source_mode: str = "Auto") -> dict[str, Any]:
    mode = normalize_financial_source_mode(source_mode)
    if mode == "Native only":
        state = _build_native_financial_terminal_state(ticker, period=period)
        state.update({"source_mode": mode, "source_provider": "native", "openbb_installed": is_openbb_installed(), "fallback_used": False})
        return state
    if mode == "OpenBB only":
        return _build_openbb_financial_terminal_state(ticker, period=period, source_mode=mode)
    native = _build_native_financial_terminal_state(ticker, period=period)
    native.update({"source_mode": mode, "source_provider": "native", "openbb_installed": is_openbb_installed(), "fallback_used": False})
    if not is_openbb_installed():
        availability = openbb_available_result()
        native["openbb_status"] = availability
        native["statuses"] = native.get("statuses", []) + [availability]
        native["status"] = combine_results(native["statuses"], provider="financial_terminal", source=f"{ticker} financial terminal state")
        native["fallback_used"] = mode == "OpenBB preferred"
        native["caveats"] = native.get("caveats", []) + ["OpenBB is not installed; native provider path is active."]
        return native
    openbb_state = _build_openbb_financial_terminal_state(ticker, period=period, source_mode=mode)
    return _merge_openbb_over_native(native, openbb_state, source_mode=mode)


def build_unified_financial_endpoint_payload(ticker: str, period: str = "annual", source_mode: str = "auto") -> dict[str, Any]:
    from .data_router import request_financials, request_price_history

    mode = str(source_mode or "auto").lower().replace(" ", "_")
    results = {
        "price_history": request_price_history(ticker, period="1y", source_mode=mode),
        "income": request_financials(ticker, statement="income", period=period, source_mode=mode),
        "balance": request_financials(ticker, statement="balance", period=period, source_mode=mode),
        "cashflow": request_financials(ticker, statement="cashflow", period=period, source_mode=mode),
        "ratios": request_financials(ticker, statement="ratios", period=period, source_mode=mode, allow_proxy=True, allow_estimates=True),
        "metrics": request_financials(ticker, statement="metrics", period=period, source_mode=mode, allow_proxy=True, allow_estimates=True),
    }
    rows = []
    for label, result in results.items():
        rows.append(
            {
                "section": label,
                "ok": result.ok,
                "provider": result.provider,
                "source": result.source,
                "freshness": result.freshness,
                "native_used": result.native_used,
                "openbb_used": result.openbb_used,
                "fallback_used": result.fallback_used,
                "source_confidence": result.metadata.get("source_confidence", 0),
                "data_gaps": len(result.data_gaps),
                "caveat": "; ".join(result.caveats),
            }
        )
    return {
        "ticker": ticker.upper(),
        "period": period,
        "source_mode": mode,
        "results": results,
        "status_table": pd.DataFrame(rows) if pd is not None else rows,
        "data_gaps": [gap for result in results.values() for gap in result.data_gaps],
        "caveat": "Unified Financial Terminal payload does not fabricate unavailable estimates, segment revenue, geography revenue, or transcripts.",
    }
