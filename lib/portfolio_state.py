from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PORTFOLIO_PATH = ROOT / "data" / "private" / "portfolio.json"
SUPPORTED_ASSET_CLASSES = {"stock", "ETF", "crypto", "bond_proxy", "commodity", "cash", "custom"}
PORTFOLIO_COLUMNS = [
    "ticker",
    "name",
    "asset_class",
    "region",
    "currency",
    "quantity",
    "weight",
    "target_weight",
    "price",
    "market_value",
    "include",
    "notes",
]


def default_portfolio_rows() -> list[dict[str, Any]]:
    return [
        {"ticker": "SPY", "name": "S&P 500 ETF", "asset_class": "ETF", "region": "US", "currency": "USD", "quantity": 1.0, "weight": 0.35, "target_weight": 0.35, "price": 0.0, "market_value": 0.0, "include": True, "notes": "Core equity proxy"},
        {"ticker": "TLT", "name": "Long Treasury ETF", "asset_class": "bond_proxy", "region": "US", "currency": "USD", "quantity": 1.0, "weight": 0.25, "target_weight": 0.25, "price": 0.0, "market_value": 0.0, "include": True, "notes": "Duration proxy"},
        {"ticker": "GLD", "name": "Gold ETF", "asset_class": "commodity", "region": "Global", "currency": "USD", "quantity": 1.0, "weight": 0.15, "target_weight": 0.15, "price": 0.0, "market_value": 0.0, "include": True, "notes": "Gold proxy"},
        {"ticker": "BTC-USD", "name": "Bitcoin", "asset_class": "crypto", "region": "Global", "currency": "USD", "quantity": 1.0, "weight": 0.15, "target_weight": 0.15, "price": 0.0, "market_value": 0.0, "include": True, "notes": "Crypto proxy"},
        {"ticker": "CASH", "name": "Cash", "asset_class": "cash", "region": "Global", "currency": "USD", "quantity": 1.0, "weight": 0.10, "target_weight": 0.10, "price": 1.0, "market_value": 0.0, "include": True, "notes": "Residual cash sleeve"},
    ]


def sanitize_portfolio_name(name: str | None) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9 _.-]+", "", str(name or "Research Portfolio")).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned[:64] or "Research Portfolio"


def _coerce_rows(rows: Any) -> pd.DataFrame:
    if rows is None:
        return pd.DataFrame(default_portfolio_rows())
    if isinstance(rows, pd.DataFrame):
        return rows.copy()
    if isinstance(rows, dict):
        return pd.DataFrame([rows])
    return pd.DataFrame(list(rows))


def normalize_portfolio_rows(rows: Any = None) -> pd.DataFrame:
    frame = _coerce_rows(rows)
    for column in PORTFOLIO_COLUMNS:
        if column not in frame.columns:
            if column == "include":
                frame[column] = True
            elif column in {"quantity", "weight", "target_weight", "price", "market_value"}:
                frame[column] = 0.0
            elif column == "asset_class":
                frame[column] = "custom"
            elif column == "currency":
                frame[column] = "USD"
            else:
                frame[column] = ""
    frame = frame[PORTFOLIO_COLUMNS].copy()
    frame["ticker"] = frame["ticker"].astype(str).str.strip().str.upper()
    frame["name"] = frame["name"].fillna("").astype(str)
    frame["asset_class"] = frame["asset_class"].where(frame["asset_class"].isin(SUPPORTED_ASSET_CLASSES), "custom")
    frame["region"] = frame["region"].replace("", "Global").fillna("Global").astype(str)
    frame["currency"] = frame["currency"].replace("", "USD").fillna("USD").astype(str).str.upper()
    frame["include"] = frame["include"].fillna(True).astype(bool)
    for column in ["quantity", "weight", "target_weight", "price", "market_value"]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce").fillna(0.0)
    computed_value = frame["quantity"] * frame["price"]
    frame["market_value"] = np.where(frame["market_value"].abs() > 0, frame["market_value"], computed_value)
    included = frame["include"] & frame["ticker"].ne("")
    market_total = float(frame.loc[included, "market_value"].clip(lower=0).sum())
    if market_total > 0:
        frame.loc[included, "weight"] = frame.loc[included, "market_value"].clip(lower=0) / market_total
    else:
        total_weight = float(frame.loc[included, "weight"].clip(lower=0).sum())
        if total_weight > 0:
            frame.loc[included, "weight"] = frame.loc[included, "weight"].clip(lower=0) / total_weight
    target_total = float(frame.loc[included, "target_weight"].clip(lower=0).sum())
    if target_total > 0:
        frame.loc[included, "target_weight"] = frame.loc[included, "target_weight"].clip(lower=0) / target_total
    else:
        frame.loc[included, "target_weight"] = frame.loc[included, "weight"]
    frame.loc[~included, ["weight", "target_weight"]] = 0.0
    return frame


def validate_portfolio_rows(rows: Any) -> tuple[bool, list[str]]:
    frame = normalize_portfolio_rows(rows)
    issues: list[str] = []
    if frame["ticker"].eq("").any():
        issues.append("Rows with blank tickers are ignored.")
    if frame.loc[frame["include"], "ticker"].duplicated().any():
        issues.append("Duplicate included tickers detected.")
    if (frame[["weight", "target_weight"]] < 0).any().any():
        issues.append("Weights cannot be negative in the default research mode.")
    included_weight = float(frame.loc[frame["include"], "weight"].sum())
    if included_weight <= 0:
        issues.append("Included rows must have positive weights or market values.")
    unsupported = sorted(set(frame["asset_class"]) - SUPPORTED_ASSET_CLASSES)
    if unsupported:
        issues.append(f"Unsupported asset classes: {', '.join(unsupported)}")
    return not any("must" in issue.lower() or "cannot" in issue.lower() or "duplicate" in issue.lower() for issue in issues), issues


def portfolio_rows_to_weights(rows: Any, *, use_target: bool = False, include_cash: bool = True) -> dict[str, float]:
    frame = normalize_portfolio_rows(rows)
    column = "target_weight" if use_target else "weight"
    selected = frame[frame["include"] & frame["ticker"].ne("")]
    if not include_cash:
        selected = selected[selected["asset_class"] != "cash"]
    weights = selected.set_index("ticker")[column].astype(float).to_dict()
    total = sum(max(0.0, value) for value in weights.values())
    if total > 0:
        weights = {ticker: max(0.0, value) / total for ticker, value in weights.items()}
    return weights


def cash_weight(rows: Any) -> float:
    frame = normalize_portfolio_rows(rows)
    return float(frame.loc[frame["include"] & (frame["asset_class"] == "cash"), "weight"].sum())


def rebalance_weights(
    rows: Any,
    *,
    method: str = "normalize",
    volatility: dict[str, float] | pd.Series | None = None,
    cash_weight_value: float | None = None,
) -> pd.DataFrame:
    frame = normalize_portfolio_rows(rows)
    selected = frame["include"] & frame["ticker"].ne("")
    non_cash = selected & (frame["asset_class"] != "cash")
    cash = max(0.0, min(1.0, float(cash_weight_value if cash_weight_value is not None else cash_weight(frame))))
    investable = max(0.0, 1.0 - cash)
    if method == "equal":
        count = int(non_cash.sum())
        if count:
            frame.loc[non_cash, "target_weight"] = investable / count
    elif method == "inverse_volatility" and volatility is not None:
        vol_map = dict(volatility)
        inv = frame.loc[non_cash, "ticker"].map(lambda ticker: 1.0 / max(float(vol_map.get(ticker, np.nan)), 1e-9) if pd.notna(vol_map.get(ticker, np.nan)) else np.nan)
        if inv.notna().sum() > 0 and float(inv.sum()) > 0:
            frame.loc[non_cash, "target_weight"] = inv.fillna(0).to_numpy() / float(inv.sum()) * investable
    else:
        total = float(frame.loc[non_cash, "target_weight"].clip(lower=0).sum())
        if total > 0:
            frame.loc[non_cash, "target_weight"] = frame.loc[non_cash, "target_weight"].clip(lower=0) / total * investable
    if selected.any():
        frame.loc[selected & (frame["asset_class"] == "cash"), "target_weight"] = 0.0
        cash_rows = frame.index[selected & (frame["asset_class"] == "cash")]
        if len(cash_rows):
            frame.loc[cash_rows[0], "target_weight"] = cash
    return normalize_portfolio_rows(frame)


def portfolio_summary(rows: Any) -> dict[str, Any]:
    frame = normalize_portfolio_rows(rows)
    included = frame[frame["include"] & frame["ticker"].ne("")]
    weights = included["weight"].astype(float)
    return {
        "asset_count": int(len(included)),
        "total_market_value": float(included["market_value"].sum()),
        "weight_sum": float(weights.sum()),
        "cash_weight": cash_weight(frame),
        "largest_weight": float(weights.max()) if not weights.empty else 0.0,
        "asset_classes": sorted(included["asset_class"].dropna().unique().tolist()),
        "regions": sorted(included["region"].dropna().unique().tolist()),
        "data_gaps": [] if not included.empty else ["No included portfolio rows."],
        "caveat": "Portfolio rows are user-defined research inputs and are not personalized financial advice.",
    }


def _read_store(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"portfolios": {}}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"portfolios": {}}


def save_portfolio_to_json(name: str, rows: Any, path: str | Path | None = None) -> Path:
    target = Path(path) if path is not None else DEFAULT_PORTFOLIO_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    store = _read_store(target)
    key = sanitize_portfolio_name(name)
    store.setdefault("portfolios", {})[key] = {
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        "rows": normalize_portfolio_rows(rows).to_dict(orient="records"),
    }
    target.write_text(json.dumps(store, indent=2, ensure_ascii=False), encoding="utf-8")
    return target


def load_portfolio_from_json(name: str | None = None, path: str | Path | None = None) -> pd.DataFrame:
    target = Path(path) if path is not None else DEFAULT_PORTFOLIO_PATH
    store = _read_store(target)
    portfolios = store.get("portfolios", {})
    if not portfolios:
        return normalize_portfolio_rows(default_portfolio_rows())
    key = sanitize_portfolio_name(name) if name else sorted(portfolios.keys())[-1]
    return normalize_portfolio_rows(portfolios.get(key, {}).get("rows", default_portfolio_rows()))


def list_saved_portfolios(path: str | Path | None = None) -> list[str]:
    target = Path(path) if path is not None else DEFAULT_PORTFOLIO_PATH
    return sorted(_read_store(target).get("portfolios", {}).keys())


def delete_saved_portfolio(name: str, path: str | Path | None = None) -> bool:
    target = Path(path) if path is not None else DEFAULT_PORTFOLIO_PATH
    store = _read_store(target)
    key = sanitize_portfolio_name(name)
    if key not in store.get("portfolios", {}):
        return False
    del store["portfolios"][key]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(store, indent=2, ensure_ascii=False), encoding="utf-8")
    return True
