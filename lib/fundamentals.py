from __future__ import annotations

from typing import Any

from .data_status import DataResult, combine_results, failure, success

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None

try:
    import yfinance as yf
except Exception:  # pragma: no cover
    yf = None


INCOME_ALIASES = {
    "total_revenue": ["Total Revenue", "Operating Revenue"],
    "revenue": ["Total Revenue", "Operating Revenue"],
    "cost_of_revenue": ["Cost Of Revenue", "Cost of Revenue"],
    "gross_profit": ["Gross Profit"],
    "operating_expense": ["Operating Expense", "Total Operating Expenses"],
    "operating_income": ["Operating Income", "EBIT"],
    "pretax_income": ["Pretax Income", "Income Before Tax"],
    "tax_provision": ["Tax Provision", "Income Tax Expense"],
    "net_income": ["Net Income", "Net Income Common Stockholders"],
    "ebitda": ["EBITDA", "Normalized EBITDA"],
    "diluted_eps": ["Diluted EPS"],
    "eps": ["Diluted EPS", "Basic EPS"],
}

CASHFLOW_ALIASES = {
    "operating_cash_flow": ["Operating Cash Flow", "Total Cash From Operating Activities"],
    "capital_expenditure": ["Capital Expenditure", "Capital Expenditures"],
    "capex": ["Capital Expenditure", "Capital Expenditures"],
    "free_cash_flow": ["Free Cash Flow"],
    "financing_cash_flow": ["Financing Cash Flow", "Total Cash From Financing Activities"],
    "investing_cash_flow": ["Investing Cash Flow", "Total Cash From Investing Activities"],
    "dividends_paid": ["Cash Dividends Paid", "Common Stock Dividend Paid"],
    "stock_repurchase": ["Repurchase Of Capital Stock", "Repurchase of Capital Stock"],
}

BALANCE_ALIASES = {
    "cash_and_equivalents": ["Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments"],
    "total_debt": ["Total Debt", "Net Debt"],
    "net_debt": ["Net Debt"],
    "total_assets": ["Total Assets"],
    "total_liabilities": ["Total Liabilities Net Minority Interest", "Total Liab"],
    "shareholders_equity": ["Stockholders Equity", "Total Stockholder Equity"],
    "working_capital": ["Working Capital"],
    "current_assets": ["Current Assets", "Total Current Assets"],
    "current_liabilities": ["Current Liabilities", "Total Current Liabilities"],
}


def _empty_status(source: str, error: str) -> tuple[object, DataResult]:
    if pd is None:
        return [], failure(source=source, provider="fundamentals", error="pandas is not installed")
    return pd.DataFrame(), failure(source=source, provider="fundamentals", error=error, coverage="missing")


def _ticker(ticker: str):
    if yf is None:
        return None
    try:
        return yf.Ticker(ticker)
    except Exception:
        return None


def normalize_financial_statement(statement, aliases: dict[str, list[str]] | None = None):
    if pd is None:
        return []
    if statement is None or getattr(statement, "empty", True):
        return pd.DataFrame()
    frame = statement.copy()
    if not isinstance(frame.index, pd.Index):
        return pd.DataFrame()
    frame = frame.T
    frame.index = pd.to_datetime(frame.index, errors="coerce")
    frame = frame.sort_index()
    frame.columns = [str(column) for column in frame.columns]
    if aliases:
        output = pd.DataFrame(index=frame.index)
        for canonical, candidates in aliases.items():
            matched = next((candidate for candidate in candidates if candidate in frame.columns), None)
            output[canonical] = frame[matched] if matched else None
        return output
    return frame


def _statement_attr(obj: Any, annual_attr: str, quarterly_attr: str, period: str):
    if str(period).lower().startswith("q"):
        return getattr(obj, quarterly_attr, None)
    return getattr(obj, annual_attr, None)


def get_income_statement(ticker: str, period: str = "annual"):
    if pd is None or yf is None:
        return _empty_status(f"{ticker} income statement", "yfinance or pandas is not installed")
    obj = _ticker(ticker)
    if obj is None:
        return _empty_status(f"{ticker} income statement", "Ticker object unavailable")
    try:
        frame = normalize_financial_statement(_statement_attr(obj, "income_stmt", "quarterly_income_stmt", period), INCOME_ALIASES)
        status = success(frame, source=f"{ticker} yfinance {period} income statement", provider="yfinance", coverage=f"{len(frame)} periods")
        return frame, status
    except Exception as exc:
        return _empty_status(f"{ticker} income statement", str(exc))


def get_balance_sheet(ticker: str, period: str = "annual"):
    if pd is None or yf is None:
        return _empty_status(f"{ticker} balance sheet", "yfinance or pandas is not installed")
    obj = _ticker(ticker)
    if obj is None:
        return _empty_status(f"{ticker} balance sheet", "Ticker object unavailable")
    try:
        frame = normalize_financial_statement(_statement_attr(obj, "balance_sheet", "quarterly_balance_sheet", period), BALANCE_ALIASES)
        if not frame.empty and "net_debt" in frame.columns and frame["net_debt"].isna().all():
            if {"total_debt", "cash_and_equivalents"}.issubset(frame.columns):
                frame["net_debt"] = frame["total_debt"].fillna(0) - frame["cash_and_equivalents"].fillna(0)
        if not frame.empty and "working_capital" in frame.columns and frame["working_capital"].isna().all():
            if {"current_assets", "current_liabilities"}.issubset(frame.columns):
                frame["working_capital"] = frame["current_assets"].fillna(0) - frame["current_liabilities"].fillna(0)
        status = success(frame, source=f"{ticker} yfinance {period} balance sheet", provider="yfinance", coverage=f"{len(frame)} periods")
        return frame, status
    except Exception as exc:
        return _empty_status(f"{ticker} balance sheet", str(exc))


def get_cash_flow(ticker: str, period: str = "annual"):
    if pd is None or yf is None:
        return _empty_status(f"{ticker} cash flow", "yfinance or pandas is not installed")
    obj = _ticker(ticker)
    if obj is None:
        return _empty_status(f"{ticker} cash flow", "Ticker object unavailable")
    try:
        frame = normalize_financial_statement(_statement_attr(obj, "cashflow", "quarterly_cashflow", period), CASHFLOW_ALIASES)
        if "free_cash_flow" in frame.columns and frame["free_cash_flow"].isna().all():
            if {"operating_cash_flow", "capex"}.issubset(frame.columns):
                frame["free_cash_flow"] = frame["operating_cash_flow"].fillna(0) + frame["capex"].fillna(0)
        status = success(frame, source=f"{ticker} yfinance {period} cash flow", provider="yfinance", coverage=f"{len(frame)} periods")
        return frame, status
    except Exception as exc:
        return _empty_status(f"{ticker} cash flow", str(exc))


def get_financial_statements(ticker: str, period: str = "annual") -> tuple[dict[str, object], DataResult]:
    income, income_status = get_income_statement(ticker, period=period)
    balance, balance_status = get_balance_sheet(ticker, period=period)
    cashflow, cashflow_status = get_cash_flow(ticker, period=period)
    status = combine_results([income_status, balance_status, cashflow_status], provider="fundamentals", source=f"{ticker} {period} financial statements")
    return {"income": income, "balance": balance, "cashflow": cashflow, "period": period}, status


def compute_growth_rates(frame, columns: list[str] | None = None):
    if pd is None or frame is None or getattr(frame, "empty", True):
        return [] if pd is None else pd.DataFrame()
    columns = columns or list(frame.columns)
    output = frame[columns].copy()
    return output.pct_change() * 100


def compute_margin_series(income):
    if pd is None or income is None or getattr(income, "empty", True) or "revenue" not in income.columns:
        return [] if pd is None else pd.DataFrame()
    revenue = income["revenue"].replace(0, pd.NA)
    output = pd.DataFrame(index=income.index)
    for source, target in [
        ("gross_profit", "gross_margin"),
        ("operating_income", "operating_margin"),
        ("net_income", "net_margin"),
        ("ebitda", "ebitda_margin"),
    ]:
        output[target] = income[source] / revenue * 100 if source in income.columns else None
    return output


def compute_valuation_series(info: dict[str, Any] | None):
    info = info or {}
    keys = {
        "trailing_pe": "trailingPE",
        "forward_pe": "forwardPE",
        "price_to_sales": "priceToSalesTrailing12Months",
        "price_to_book": "priceToBook",
        "ev_to_ebitda": "enterpriseToEbitda",
        "debt_to_equity": "debtToEquity",
        "roe": "returnOnEquity",
        "roa": "returnOnAssets",
        "current_ratio": "currentRatio",
        "market_cap": "marketCap",
    }
    return {label: info.get(source) for label, source in keys.items()}


def compute_statement_ratios(income=None, balance=None, cashflow=None, info: dict[str, Any] | None = None) -> dict[str, Any]:
    info = info or {}
    ratios = compute_valuation_series(info)
    latest_income = income.dropna(how="all").iloc[-1] if pd is not None and income is not None and not getattr(income, "empty", True) and not income.dropna(how="all").empty else {}
    latest_balance = balance.dropna(how="all").iloc[-1] if pd is not None and balance is not None and not getattr(balance, "empty", True) and not balance.dropna(how="all").empty else {}
    latest_cashflow = cashflow.dropna(how="all").iloc[-1] if pd is not None and cashflow is not None and not getattr(cashflow, "empty", True) and not cashflow.dropna(how="all").empty else {}

    revenue = latest_income.get("revenue") or latest_income.get("total_revenue")
    gross_profit = latest_income.get("gross_profit")
    operating_income = latest_income.get("operating_income")
    net_income = latest_income.get("net_income")
    free_cash_flow = latest_cashflow.get("free_cash_flow")
    assets = latest_balance.get("total_assets")
    equity = latest_balance.get("shareholders_equity")
    debt = latest_balance.get("total_debt")
    current_assets = latest_balance.get("current_assets")
    current_liabilities = latest_balance.get("current_liabilities")
    cash = latest_balance.get("cash_and_equivalents")

    def safe_div(numerator, denominator):
        try:
            if denominator in (None, 0) or pd.isna(denominator):
                return None
            if numerator is None or pd.isna(numerator):
                return None
            return float(numerator) / float(denominator)
        except Exception:
            return None

    ratios.update(
        {
            "debt_to_equity": ratios.get("debt_to_equity") or safe_div(debt, equity),
            "current_ratio": ratios.get("current_ratio") or safe_div(current_assets, current_liabilities),
            "quick_ratio": safe_div((cash or 0), current_liabilities),
            "roe": ratios.get("roe") or safe_div(net_income, equity),
            "roa": ratios.get("roa") or safe_div(net_income, assets),
            "roic": safe_div(operating_income, (debt or 0) + (equity or 0)),
            "gross_margin": safe_div(gross_profit, revenue),
            "operating_margin": safe_div(operating_income, revenue),
            "net_margin": safe_div(net_income, revenue),
            "fcf_margin": safe_div(free_cash_flow, revenue),
        }
    )
    return ratios


def compute_ttm_frame(frame, window: int = 4):
    if pd is None or frame is None or getattr(frame, "empty", True):
        return [] if pd is None else pd.DataFrame()
    numeric = frame.apply(pd.to_numeric, errors="coerce")
    if len(numeric) < window:
        return pd.DataFrame()
    return numeric.rolling(window=window).sum().dropna(how="all")


def compute_balance_sheet_quality(balance):
    if pd is None or balance is None or getattr(balance, "empty", True):
        return {"net_debt": None, "debt_to_assets": None, "equity_ratio": None, "data_gap": "balance sheet unavailable"}
    latest = balance.dropna(how="all").iloc[-1] if not balance.dropna(how="all").empty else {}
    cash = latest.get("cash_and_equivalents")
    debt = latest.get("total_debt")
    assets = latest.get("total_assets")
    equity = latest.get("shareholders_equity")
    return {
        "net_debt": (debt or 0) - (cash or 0) if debt is not None or cash is not None else None,
        "debt_to_assets": float(debt / assets) if debt is not None and assets else None,
        "equity_ratio": float(equity / assets) if equity is not None and assets else None,
        "data_gap": None,
    }


def get_key_ratios(ticker: str):
    if yf is None:
        return {}, failure(source=f"{ticker} key ratios", provider="yfinance", error="yfinance is not installed")
    obj = _ticker(ticker)
    if obj is None:
        return {}, failure(source=f"{ticker} key ratios", provider="yfinance", error="Ticker object unavailable")
    try:
        info = getattr(obj, "info", {}) or {}
        ratios = compute_valuation_series(info)
        return ratios, success(ratios, source=f"{ticker} yfinance info", provider="yfinance", coverage="available info fields")
    except Exception as exc:
        return {}, failure(source=f"{ticker} key ratios", provider="yfinance", error=str(exc), coverage="missing")


def build_financial_overview(ticker: str, period: str = "annual") -> tuple[dict[str, Any], DataResult]:
    statements, statement_status = get_financial_statements(ticker, period=period)
    ratios, ratio_status = get_key_ratios(ticker)
    income = statements.get("income")
    balance = statements.get("balance")
    cashflow = statements.get("cashflow")
    overview = {
        "ticker": ticker.upper(),
        "income": income,
        "balance": balance,
        "cashflow": cashflow,
        "period": period,
        "growth": compute_growth_rates(income, [col for col in ["revenue", "gross_profit", "operating_income", "net_income", "eps", "diluted_eps"] if income is not None and col in getattr(income, "columns", [])]) if income is not None else pd.DataFrame(),
        "margins": compute_margin_series(income),
        "balance_quality": compute_balance_sheet_quality(balance),
        "ratios": compute_statement_ratios(income, balance, cashflow, ratios),
        "ttm": {
            "income": compute_ttm_frame(income) if period.lower().startswith("q") else pd.DataFrame(),
            "cashflow": compute_ttm_frame(cashflow) if period.lower().startswith("q") else pd.DataFrame(),
        },
        "availability": {
            "income": not getattr(income, "empty", True),
            "balance": not getattr(balance, "empty", True),
            "cashflow": not getattr(cashflow, "empty", True),
            "ratios": bool(ratios),
        },
        "data_gaps": [],
    }
    overview["data_gaps"] = [name for name, available in overview["availability"].items() if not available]
    status = combine_results([statement_status, ratio_status], provider="fundamentals", source=f"{ticker} financial overview")
    return overview, status


def build_financial_visual_panels(overview: dict[str, Any]) -> dict[str, Any]:
    availability = overview.get("availability", {}) if isinstance(overview, dict) else {}
    ratios = overview.get("ratios", {}) if isinstance(overview, dict) else {}
    quality = overview.get("balance_quality", {}) if isinstance(overview, dict) else {}
    cards = [
        {"label": "Trailing PE", "value": ratios.get("trailing_pe"), "status": "source-derived" if ratios.get("trailing_pe") is not None else "data gap"},
        {"label": "Forward PE", "value": ratios.get("forward_pe"), "status": "source-derived" if ratios.get("forward_pe") is not None else "data gap"},
        {"label": "Debt To Assets", "value": quality.get("debt_to_assets"), "status": "source-derived" if quality.get("debt_to_assets") is not None else "data gap"},
        {"label": "Equity Ratio", "value": quality.get("equity_ratio"), "status": "source-derived" if quality.get("equity_ratio") is not None else "data gap"},
    ]
    availability_rows = [{"dataset": key, "available": bool(value)} for key, value in availability.items()]
    return {
        "ticker": overview.get("ticker") if isinstance(overview, dict) else None,
        "metric_cards": cards,
        "availability_matrix": pd.DataFrame(availability_rows) if pd is not None else availability_rows,
        "data_gaps": overview.get("data_gaps", []) if isinstance(overview, dict) else ["overview unavailable"],
        "method": "financial visual payload builder",
    }
