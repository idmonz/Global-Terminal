from __future__ import annotations

from html import escape
from math import isfinite
from typing import Any, Iterable


SEVERITY_COLORS = {
    "critical": "#ef4444",
    "high": "#f97316",
    "medium": "#f59e0b",
    "watch": "#38bdf8",
    "low": "#22c55e",
    "info": "#94a3b8",
    "data gap": "#64748b",
}

FRESHNESS_COLORS = {
    "fresh": "#22c55e",
    "estimated": "#38bdf8",
    "stale": "#f59e0b",
    "missing": "#94a3b8",
    "error": "#ef4444",
    "unknown": "#64748b",
}


def _clean(value: Any) -> str:
    if value is None:
        return "N/A"
    return escape(str(value))


def _fmt(value: Any, digits: int = 2, suffix: str = "") -> str:
    if value is None:
        return "N/A"
    try:
        number = float(value)
        if not isfinite(number):
            return "N/A"
        return f"{number:,.{digits}f}{suffix}"
    except Exception:
        return str(value)


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    if isinstance(value, Iterable) and not isinstance(value, (dict, bytes)):
        return list(value)
    return [value]


def terminal_css() -> str:
    return """
<style>
:root {
  --terminal-bg: #070b12;
  --terminal-panel: #0d1420;
  --terminal-panel-2: #111827;
  --terminal-border: rgba(148, 163, 184, 0.22);
  --terminal-text: #e5e7eb;
  --terminal-muted: #94a3b8;
  --terminal-cyan: #38bdf8;
}
.terminal-shell {
  background: linear-gradient(180deg, rgba(15, 23, 42, 0.98), rgba(7, 11, 18, 0.98));
  border: 1px solid var(--terminal-border);
  border-radius: 8px;
  padding: 14px 16px;
  margin-bottom: 12px;
}
.terminal-title {
  color: var(--terminal-text);
  font-size: 1.65rem;
  font-weight: 700;
  letter-spacing: 0;
  line-height: 1.15;
}
.terminal-subtitle {
  color: var(--terminal-muted);
  font-size: 0.86rem;
  margin-top: 5px;
}
.terminal-meta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
  margin-top: 10px;
}
.terminal-section {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  border-bottom: 1px solid var(--terminal-border);
  padding-bottom: 7px;
  margin: 14px 0 9px;
}
.terminal-section-title {
  color: var(--terminal-text);
  font-size: 0.96rem;
  font-weight: 700;
}
.terminal-section-caption {
  color: var(--terminal-muted);
  font-size: 0.78rem;
}
.terminal-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-left-width: 3px;
  border-radius: 999px;
  color: var(--terminal-text);
  background: rgba(15, 23, 42, 0.82);
  padding: 3px 8px;
  font-size: 0.72rem;
  font-weight: 650;
  white-space: nowrap;
}
.terminal-card {
  background: rgba(13, 20, 32, 0.92);
  border: 1px solid var(--terminal-border);
  border-radius: 8px;
  padding: 11px 12px;
  min-height: 100%;
}
.terminal-card-title {
  color: var(--terminal-text);
  font-size: 0.92rem;
  font-weight: 700;
  line-height: 1.25;
}
.terminal-card-summary {
  color: #cbd5e1;
  font-size: 0.79rem;
  line-height: 1.38;
  margin-top: 7px;
}
.terminal-card-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  margin-top: 9px;
}
.terminal-action-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
  gap: 8px;
  margin-top: 10px;
}
.terminal-action-item {
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 8px;
  padding: 9px 10px;
  background: rgba(15, 23, 42, 0.48);
}
.terminal-metric {
  background: rgba(13, 20, 32, 0.92);
  border: 1px solid var(--terminal-border);
  border-radius: 8px;
  padding: 9px 10px;
  min-height: 84px;
}
.terminal-metric-label {
  color: var(--terminal-muted);
  font-size: 0.72rem;
  text-transform: uppercase;
}
.terminal-metric-value {
  color: var(--terminal-text);
  font-size: 1.05rem;
  font-weight: 750;
  margin-top: 3px;
}
.terminal-metric-delta {
  color: var(--terminal-muted);
  font-size: 0.72rem;
  margin-top: 3px;
}
.terminal-mini-bar {
  height: 8px;
  background: rgba(30, 41, 59, 0.9);
  border-radius: 999px;
  overflow: hidden;
  border: 1px solid rgba(148, 163, 184, 0.16);
}
.terminal-mini-bar-fill {
  height: 100%;
  border-radius: 999px;
}
.terminal-sparkline {
  display: block;
  width: 100%;
  max-width: 150px;
  height: 28px;
  margin-top: 5px;
}
</style>
"""


def _render_html(st_module: Any, html: str) -> None:
    if st_module is not None and hasattr(st_module, "markdown"):
        st_module.markdown(html, unsafe_allow_html=True)


def status_badge(label: str, status: str | None = None, *, tone: str | None = None) -> str:
    normalized = (tone or status or label or "info").lower()
    color = FRESHNESS_COLORS.get(normalized) or SEVERITY_COLORS.get(normalized, "#94a3b8")
    text = label if status is None else f"{label}: {status}"
    return f'<span class="terminal-badge" style="border-left-color:{color}">{_clean(text)}</span>'


def severity_badge(severity: str | None) -> str:
    label = (severity or "watch").lower()
    color = SEVERITY_COLORS.get(label, SEVERITY_COLORS["watch"])
    return f'<span class="terminal-badge" style="border-left-color:{color}">Severity: {_clean(label.title())}</span>'


def freshness_badge(freshness: str | None) -> str:
    label = (freshness or "unknown").lower()
    color = FRESHNESS_COLORS.get(label, FRESHNESS_COLORS["unknown"])
    return f'<span class="terminal-badge" style="border-left-color:{color}">Source: {_clean(label.title())}</span>'


def data_gap_badge(label: str = "Data gap") -> str:
    return status_badge(label, tone="data gap")


def terminal_page_header(
    st_module: Any = None,
    title: str = "Global Market Analyst Terminal",
    subtitle: str = "",
    meta: Iterable[str | dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if isinstance(st_module, str):
        title, st_module = st_module, None
    meta_items: list[str] = []
    for item in _as_list(meta):
        if isinstance(item, dict):
            meta_items.append(status_badge(str(item.get("label", "status")), str(item.get("value", "")), tone=str(item.get("tone", "info"))))
        else:
            meta_items.append(status_badge(str(item), tone="info"))
    html = (
        terminal_css()
        + '<div class="terminal-shell">'
        + f'<div class="terminal-title">{_clean(title)}</div>'
        + (f'<div class="terminal-subtitle">{_clean(subtitle)}</div>' if subtitle else "")
        + (f'<div class="terminal-meta-row">{"".join(meta_items)}</div>' if meta_items else "")
        + "</div>"
    )
    _render_html(st_module, html)
    return {"title": title, "subtitle": subtitle, "meta": list(meta or []), "html": html}


def terminal_section_header(
    st_module: Any = None,
    title: str = "",
    caption: str = "",
    badges: Iterable[str] | None = None,
) -> dict[str, Any]:
    if isinstance(st_module, str):
        title, st_module = st_module, None
    badge_html = "".join(badges or [])
    html = (
        '<div class="terminal-section">'
        + "<div>"
        + f'<div class="terminal-section-title">{_clean(title)}</div>'
        + (f'<div class="terminal-section-caption">{_clean(caption)}</div>' if caption else "")
        + "</div>"
        + (f'<div class="terminal-meta-row">{badge_html}</div>' if badge_html else "")
        + "</div>"
    )
    _render_html(st_module, html)
    return {"title": title, "caption": caption, "badges": list(badges or []), "html": html}


def mini_bar(value: Any, *, label: str = "", max_value: float = 100.0, color: str = "#38bdf8") -> str:
    try:
        number = max(0.0, min(float(value), max_value))
        pct = 0.0 if max_value <= 0 else number / max_value * 100.0
    except Exception:
        number, pct = 0.0, 0.0
    caption = f'<div class="terminal-metric-delta">{_clean(label)} {_fmt(number, 1)}</div>' if label else ""
    return f'{caption}<div class="terminal-mini-bar"><div class="terminal-mini-bar-fill" style="width:{pct:.1f}%;background:{color}"></div></div>'


def mini_sparkline(values: Iterable[Any] | None, *, color: str = "#38bdf8") -> str:
    cleaned: list[float] = []
    for value in _as_list(values):
        try:
            number = float(value)
            if isfinite(number):
                cleaned.append(number)
        except Exception:
            continue
    if len(cleaned) < 2:
        return ""
    width, height, pad = 148, 28, 2
    low, high = min(cleaned), max(cleaned)
    span = high - low or 1.0
    points = []
    for idx, value in enumerate(cleaned):
        x = pad + idx * (width - pad * 2) / max(1, len(cleaned) - 1)
        y = height - pad - (value - low) / span * (height - pad * 2)
        points.append(f"{x:.1f},{y:.1f}")
    return (
        f'<svg class="terminal-sparkline" viewBox="0 0 {width} {height}" role="img">'
        f'<polyline fill="none" stroke="{color}" stroke-width="2" points="{" ".join(points)}" />'
        "</svg>"
    )


def _card_html(payload: dict[str, Any]) -> str:
    badges = [severity_badge(payload.get("severity")), freshness_badge(payload.get("freshness"))]
    badges.extend(status_badge(str(tag), tone="info") for tag in payload.get("tags", [])[:6])
    if payload.get("source"):
        badges.append(status_badge("Source", str(payload["source"]), tone="info"))
    bullets = payload.get("bullets", [])
    bullet_html = ""
    if bullets:
        bullet_html = "<ul>" + "".join(f"<li>{_clean(item)}</li>" for item in bullets[:4]) + "</ul>"
    return (
        '<div class="terminal-card">'
        f'<div class="terminal-card-title">{_clean(payload.get("title", "Untitled"))}</div>'
        f'<div class="terminal-card-summary">{_clean(payload.get("summary", ""))}</div>'
        + bullet_html
        + f'<div class="terminal-card-meta">{"".join(badges)}</div>'
        + "</div>"
    )


def intelligence_card(
    st_module: Any = None,
    *,
    title: str,
    summary: str = "",
    severity: str = "watch",
    tags: Iterable[str] | None = None,
    bullets: Iterable[str] | None = None,
    source: str | None = None,
    freshness: str | None = None,
) -> dict[str, Any]:
    payload = {
        "title": title,
        "summary": summary,
        "severity": severity,
        "tags": [str(item) for item in _as_list(tags)],
        "bullets": [str(item) for item in _as_list(bullets)],
        "source": source,
        "freshness": freshness or "unknown",
    }
    payload["html"] = _card_html(payload)
    _render_html(st_module, payload["html"])
    return payload


def compact_event_card(st_module: Any = None, event: dict[str, Any] | None = None) -> dict[str, Any]:
    event = event or {}
    return intelligence_card(
        st_module,
        title=str(event.get("title") or event.get("name") or "Event watch-point"),
        summary=str(event.get("summary") or event.get("classification") or event.get("region") or "Heuristic event context."),
        severity=str(event.get("severity") or event.get("risk_proxy") or "watch"),
        tags=_as_list(event.get("asset_tags")) + _as_list(event.get("region_tags") or event.get("region")),
        source=str(event.get("source") or event.get("provider") or "public/proxy") if event.get("source") or event.get("provider") else None,
        freshness=str(event.get("freshness") or event.get("source_status") or "unknown"),
    )


def compact_news_card(st_module: Any = None, item: dict[str, Any] | None = None) -> dict[str, Any]:
    item = item or {}
    return intelligence_card(
        st_module,
        title=str(item.get("title") or "News watch-point"),
        summary=str(item.get("summary") or item.get("description") or "No summary supplied.")[:260],
        severity=str(item.get("severity") or "watch"),
        tags=_as_list(item.get("impact_channels")) + _as_list(item.get("asset_tags")) + _as_list(item.get("region_tags") or item.get("region")),
        source=str(item.get("source") or "public feed"),
        freshness=str(item.get("freshness") or "unknown"),
    )


def watchpoint_card(st_module: Any = None, title: str = "Watch-point", points: Iterable[str] | None = None, severity: str = "watch") -> dict[str, Any]:
    return intelligence_card(
        st_module,
        title=title,
        summary="Monitor as neutral evidence, not as a directive.",
        severity=severity,
        tags=["watch-point", "heuristic"],
        bullets=points,
        freshness="estimated",
    )


def metric_strip(st_module: Any = None, metrics: Iterable[dict[str, Any]] | None = None, *, columns: int = 4) -> list[dict[str, Any]]:
    rows = []
    for metric in metrics or []:
        payload = {
            "label": str(metric.get("label", "")),
            "value": metric.get("value"),
            "delta": metric.get("delta"),
            "freshness": metric.get("freshness", "unknown"),
            "sparkline": metric.get("sparkline"),
            "source": metric.get("source"),
        }
        spark = mini_sparkline(payload["sparkline"]) if payload.get("sparkline") is not None else ""
        badge = freshness_badge(str(payload["freshness"]))
        html = (
            '<div class="terminal-metric">'
            f'<div class="terminal-metric-label">{_clean(payload["label"])}</div>'
            f'<div class="terminal-metric-value">{_clean(_fmt(payload["value"]))}</div>'
            f'<div class="terminal-metric-delta">{_clean(_fmt(payload["delta"], suffix="%") if isinstance(payload["delta"], (int, float)) else payload["delta"])}</div>'
            + spark
            + f'<div class="terminal-card-meta">{badge}</div>'
            + "</div>"
        )
        payload["html"] = html
        rows.append(payload)
    if st_module is not None and hasattr(st_module, "columns") and rows:
        cols = st_module.columns(max(1, min(columns, len(rows))))
        for idx, payload in enumerate(rows):
            with cols[idx % len(cols)]:
                _render_html(st_module, payload["html"])
    return rows


def workspace_presets() -> list[dict[str, str]]:
    return [
        {"name": "Global Command Center", "page": "app.py", "focus": "Cross-asset overview, provider freshness, and command routing."},
        {"name": "Equity Desk", "page": "pages/2_Stock_Analyzer.py", "focus": "Equity fundamentals, options proxy, breadth, and screeners."},
        {"name": "Crypto Derivatives Desk", "page": "pages/8_Crypto_Intelligence.py", "focus": "Funding, OI, taker flow, estimated liquidation pressure, and crypto scenarios."},
        {"name": "Energy / Geopolitics Desk", "page": "pages/9_Energy_Geopolitics.py", "focus": "Oil fundamentals, chokepoints, route proxies, and geopolitical events."},
        {"name": "Portfolio Quant Lab", "page": "pages/16_Portfolio_Quant_Lab.py", "focus": "Editable portfolios, backtests, strategy candidates, optimizers, and attribution."},
        {"name": "Risk Manager", "page": "pages/11_Risk_Lab.py", "focus": "VaR, CVaR, stress tests, and scenario estimates."},
        {"name": "Financial Terminal", "page": "pages/15_Financial_Terminal.py", "focus": "Financial statement terminal and valuation/fundamental panels."},
        {"name": "News / OSINT War Room", "page": "pages/14_War_Room.py", "focus": "Map-first events, source status, right rail, and data gaps."},
    ]


def terminal_ticker_tape(items: Iterable[dict[str, Any]] | None = None) -> dict[str, Any]:
    rows = []
    for item in items or []:
        rows.append(
            {
                "label": str(item.get("label") or item.get("ticker") or "Asset"),
                "value": _fmt(item.get("value") or item.get("price")),
                "delta": _fmt(item.get("delta") or item.get("change_pct"), suffix="%" if isinstance(item.get("delta") or item.get("change_pct"), (int, float)) else ""),
                "freshness": str(item.get("freshness") or item.get("data_status") or "unknown"),
            }
        )
    html = '<div class="terminal-meta-row">' + "".join(status_badge(f"{row['label']} {row['value']} ({row['delta']})", tone=row["freshness"]) for row in rows[:16]) + "</div>"
    return {"items": rows, "html": html}


def provider_health_strip(st_module: Any = None) -> dict[str, Any]:
    from .provider_diagnostics import provider_health_summary

    summary = provider_health_summary()
    badges = [
        status_badge("Providers", str(summary["total_providers"]), tone="info"),
        status_badge("Available", str(summary["available"]), tone="fresh"),
        status_badge("Configured", str(summary["configured"]), tone="fresh" if summary["configured"] else "estimated"),
        status_badge("Optional gaps", str(summary["optional_missing"]), tone="missing" if summary["optional_missing"] else "fresh"),
    ]
    html = '<div class="terminal-meta-row">' + "".join(badges) + "</div>"
    _render_html(st_module, html)
    return {"summary": summary, "html": html, "badges": badges}


def keyword_chips_html(keywords: Iterable[Any] | None = None) -> str:
    chips = []
    for item in _as_list(keywords):
        payload = item if isinstance(item, dict) else {"label": str(item), "category": "keyword", "importance": "low"}
        label = payload.get("label") or payload.get("keyword") or "Keyword"
        category = payload.get("category", "keyword")
        importance = str(payload.get("importance", "low")).lower()
        tone = "critical" if importance == "high" else "watch" if importance == "medium" else "info"
        chips.append(status_badge(f"{label} - {category}", tone=tone))
    return '<div class="terminal-meta-row">' + "".join(chips[:10]) + "</div>"


def action_cards_html(actions: Iterable[dict[str, Any]] | None = None) -> str:
    rows = []
    for action in _as_list(actions):
        title = action.get("label", "Open panel")
        summary = action.get("description", action.get("tooltip", "Inspect related context."))
        command = action.get("command")
        page = action.get("page")
        meta = []
        if command:
            meta.append(status_badge("Command", command, tone="info"))
        if page:
            meta.append(status_badge("Page", page, tone="fresh"))
        rows.append(
            '<div class="terminal-action-item">'
            f'<div class="terminal-card-title">{_clean(title)}</div>'
            f'<div class="terminal-card-summary">{_clean(summary)}</div>'
            f'<div class="terminal-card-meta">{"".join(meta)}</div>'
            "</div>"
        )
    return '<div class="terminal-action-grid">' + "".join(rows[:8]) + "</div>"


def modern_summary_band(
    st_module: Any = None,
    *,
    title: str,
    bullets: Iterable[str] | None = None,
    keywords: Iterable[Any] | None = None,
    actions: Iterable[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    bullet_html = "<ul>" + "".join(f"<li>{_clean(item)}</li>" for item in _as_list(bullets)[:6]) + "</ul>" if bullets else ""
    html = (
        '<div class="terminal-card">'
        f'<div class="terminal-card-title">{_clean(title)}</div>'
        + bullet_html
        + keyword_chips_html(keywords)
        + action_cards_html(actions)
        + "</div>"
    )
    _render_html(st_module, html)
    return {"title": title, "bullets": list(bullets or []), "keywords": list(keywords or []), "actions": list(actions or []), "html": html}


def source_freshness_dot(indicator: dict[str, Any]) -> str:
    color = indicator.get("color", "#94a3b8")
    label = indicator.get("freshness", "unknown")
    source = indicator.get("source", "source")
    return f'<span title="{_clean(indicator.get("tooltip", ""))}" style="display:inline-flex;align-items:center;gap:6px;color:#cbd5e1;font-size:0.75rem;"><span style="width:8px;height:8px;border-radius:999px;background:{color};display:inline-block;"></span>{_clean(source)} {_clean(label)}</span>'


def goal10_summary_strip(
    st_module: Any = None,
    *,
    workspace: str,
    risk_state: str = "watch",
    data_confidence: str | float = "source-labeled",
    provider_status: str = "optional providers visible",
    caveat: str = "Research-only view; proxy, stale, missing-key, and historical-only outputs stay labeled.",
) -> dict[str, Any]:
    badges = [
        status_badge("Workspace", workspace, tone="info"),
        status_badge("Risk State", risk_state, tone=risk_state),
        status_badge("Data Confidence", str(data_confidence), tone="estimated"),
        status_badge("Provider Status", provider_status, tone="fresh" if "ready" in provider_status.lower() else "estimated"),
    ]
    html = (
        '<div class="terminal-card">'
        f'<div class="terminal-card-title">{_clean(workspace)} Executive Summary</div>'
        f'<div class="terminal-card-summary">{_clean(caveat)}</div>'
        f'<div class="terminal-card-meta">{"".join(badges)}</div>'
        "</div>"
    )
    _render_html(st_module, html)
    return {"workspace": workspace, "risk_state": risk_state, "data_confidence": data_confidence, "provider_status": provider_status, "html": html}


def terminal_status_console(entries: Iterable[dict[str, Any]] | None = None) -> dict[str, Any]:
    rows = []
    for entry in entries or []:
        rows.append(
            {
                "timestamp": str(entry.get("timestamp") or ""),
                "source": str(entry.get("source") or "terminal"),
                "status": str(entry.get("status") or "info"),
                "message": str(entry.get("message") or entry.get("warning") or entry.get("error") or ""),
            }
        )
    html = '<div class="terminal-card">' + "".join(f'<div class="terminal-card-summary">{_clean(row["timestamp"])} [{_clean(row["status"])}] {_clean(row["source"])}: {_clean(row["message"])}</div>' for row in rows[:12]) + "</div>"
    return {"entries": rows, "html": html}


def war_room_right_rail_panels(context: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    context = context or {}
    panel_names = [
        "Live Intelligence Feed",
        "AI Brief",
        "Strategic Posture Proxy",
        "Forecast / Scenario Watch",
        "Country Instability",
        "Chokepoint Risk",
        "Market Impact",
        "Crypto Stress",
        "Source Freshness",
        "Provider Health",
    ]
    rows = []
    for name in panel_names:
        rows.append(
            {
                "title": name,
                "severity": context.get("severity", "watch"),
                "freshness": context.get("freshness", "estimated"),
                "source_status": context.get("source_status", "public/proxy"),
                "data_gap_warning": context.get("data_gap_warning", "Optional feeds may be unavailable."),
                "caveat": "Panel uses available data and clearly marked proxies.",
            }
        )
    return rows


def layer_control_payload(*, search: str = "", domain: str | None = None, time_range: str = "24h", region: str = "Global") -> dict[str, Any]:
    from .layer_registry import build_layer_registry

    query = str(search or "").lower()
    layers = build_layer_registry()
    if domain and domain != "All":
        layers = [layer for layer in layers if layer["domain"].lower() == domain.lower()]
    if query:
        layers = [layer for layer in layers if query in layer["label"].lower() or query in layer["layer_id"].lower() or query in layer["domain"].lower()]
    grouped: dict[str, list[dict[str, Any]]] = {}
    for layer in layers:
        grouped.setdefault(layer["domain"], []).append(layer)
    return {
        "layers": layers,
        "grouped_layers": grouped,
        "available_layers": [layer for layer in layers if layer["is_available"]],
        "unavailable_layers": [layer for layer in layers if not layer["is_available"]],
        "time_range": time_range,
        "region": region,
        "time_options": ["1h", "6h", "24h", "7d", "30d", "all"],
        "region_options": ["Global", "Americas", "Europe", "MENA", "Asia", "Korea", "Energy chokepoints", "Custom"],
        "caveat": "Unavailable layers remain visible and clearly marked unavailable.",
    }


def screener_terminal_payload(frame: Any) -> dict[str, Any]:
    records = _as_list(frame.to_dict(orient="records") if hasattr(frame, "to_dict") else frame)
    return {
        "row_count": len(records),
        "factor_badges": ["momentum", "volatility", "risk", "news impact", "data gap"],
        "export_enabled": True,
        "selected_row_detail": records[0] if records else {},
        "caveat": "Ranks are heuristic research context, not advice.",
    }


def crypto_terminal_payload(snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
    snapshot = snapshot or {}
    return {
        "derivatives_radar": True,
        "oi_price_quadrant": "available when OI and price history are supplied",
        "funding_percentile": snapshot.get("funding_percentile"),
        "taker_imbalance": snapshot.get("taker_buy_sell_ratio"),
        "liquidation_pressure_label": "estimated/proxy",
        "caveat": "No official liquidation heatmap is claimed without an official provider.",
    }


def energy_terminal_payload() -> dict[str, Any]:
    return {
        "chokepoint_risk_board": True,
        "oil_risk_premium_proxy": True,
        "eia_freshness_cards": True,
        "shipping_status": "Live AIS unavailable unless optional provider is configured.",
        "war_room_link": "pages/14_War_Room.py",
        "caveat": "Energy/geopolitics impacts are scenario estimates and proxy context.",
    }
