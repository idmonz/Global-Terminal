from __future__ import annotations

import pandas as pd

from lib.alpha_strategy_workbench import build_alpha_strategy_workbench
from lib.compliance import contains_forbidden_language
from lib.data_status import ok_result
from lib.executive_terminal import build_executive_terminal_brief
from lib.provider_quality import build_openbb_probe_quality_table, build_provider_quality_scorecard, build_provider_quality_summary


def test_executive_terminal_brief_schema_and_safe_copy():
    payload = {
        "cards": pd.DataFrame(
            [
                {"label": "S&P 500", "ticker": "^GSPC", "change_pct": 0.8, "return_1m_pct": 2.1, "data_status": "real/delayed yfinance"},
                {"label": "WTI", "ticker": "CL=F", "change_pct": -1.6, "return_1m_pct": 4.4, "data_status": "real/delayed yfinance"},
            ]
        ),
        "market_radar": {"composite": {"score": 57.5, "label": "Mixed evidence", "components": 4}},
        "source_statuses": [
            ok_result(source="unit source", provider="unit", coverage="test"),
            ok_result(source="proxy source", provider="unit", coverage="test", is_estimated=True),
        ],
        "data_gaps": ["AIS unavailable without an optional provider."],
    }

    brief = build_executive_terminal_brief(payload, route="Overview Terminal", region_focus="Global")

    assert {"metrics", "cards", "movers", "route_map", "freshness_counts"}.issubset(brief)
    assert brief["freshness_counts"]["fresh"] >= 1
    assert "Provider Center" in brief["route_map"]["desk"].tolist()
    assert not brief["movers"].empty
    assert not contains_forbidden_language(" ".join(card["summary"] for card in brief["cards"]), allow_disclosure=False)


def test_provider_quality_scorecard_and_openbb_probe_normalization():
    diagnostics = pd.DataFrame(
        [
            {"provider": "yfinance", "status": "ok", "configured": True, "available": True, "latency_ms": 12.0},
            {"provider": "aisstream", "status": "missing_key", "requires_key": True, "configured": False, "warning": "Missing optional key."},
            {"provider": "openbb", "status": "skipped", "skipped": True, "warning": "Optional backend not installed."},
        ]
    )

    scorecard = build_provider_quality_scorecard(diagnostics)
    summary = build_provider_quality_summary(scorecard)
    openbb_quality = build_openbb_probe_quality_table(
        pd.DataFrame(
            [
                {"probe": "installation", "ok": False, "skipped": True, "warning": "Optional backend not installed."},
                {"endpoint": "equity.profile", "ok": True, "skipped": False, "checked_at": "2026-06-11T00:00:00Z"},
            ]
        )
    )

    assert scorecard.loc[scorecard["provider"] == "yfinance", "quality_label"].iloc[0] == "ready"
    assert summary["provider_count"] == 3
    assert summary["gap_count"] >= 1
    assert "installation" in openbb_quality["provider"].tolist()
    assert "equity.profile" in openbb_quality["provider"].tolist()


def test_alpha_strategy_workbench_payload():
    strategy_returns = pd.DataFrame(
        {
            "Momentum": [0.01, -0.004, 0.006, 0.003],
            "Low Vol": [0.002, 0.001, -0.001, 0.002],
        },
        index=pd.date_range("2025-01-01", periods=4),
    )
    research = {
        "leaderboard": pd.DataFrame(
            [
                {"candidate": "Momentum", "category": "price", "risk_adjusted_score": 72.0, "sharpe": 1.1, "factor_coverage_pct": 80.0, "source_confidence": 0.8, "data_quality_penalty": 20.0},
                {"candidate": "Low Vol", "category": "risk", "risk_adjusted_score": 61.0, "sharpe": 0.8, "factor_coverage_pct": 70.0, "source_confidence": 0.7, "data_quality_penalty": 30.0},
            ]
        ),
        "combinations": pd.DataFrame([{"name": "Momentum + Low Volatility", "composite_score": 68.0}]),
        "strategy_returns": strategy_returns,
        "oos": {"decay_pct": 12.0, "overfit": False},
        "walk_forward": {"windows": pd.DataFrame([{"window": 1}, {"window": 2}])},
    }

    workbench = build_alpha_strategy_workbench(research, {"factor_coverage_pct": 75.0, "source_confidence": 0.85})

    assert not workbench["leaderboard"].empty
    assert round(workbench["ensemble_weights"]["weight"].sum(), 6) == 1.0
    assert len(workbench["validation"]) == 4
    assert workbench["metrics"][0]["value"] == 2
    assert not contains_forbidden_language(" ".join(card["summary"] for card in workbench["cards"]), allow_disclosure=False)
