from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest


OPEN_NOW = datetime(2026, 7, 13, 15, 0, tzinfo=timezone.utc)
CLOSED_NOW = datetime(2026, 7, 11, 15, 0, tzinfo=timezone.utc)


def _watchlist(symbols: tuple[str, ...] = ("AAPL", "BTCUSDT")) -> dict:
    return {
        "resource_id": "twl_phase6n_daily",
        "name": "Phase 6N Daily",
        "items": [
            {
                "resource_id": f"twi_{symbol.lower()}",
                "symbol": symbol,
                "display_name": symbol,
                "asset_class": "crypto" if symbol.endswith("USDT") else "equity",
                "exchange": "Binance" if symbol.endswith("USDT") else "NASDAQ",
                "position": index,
            }
            for index, symbol in enumerate(symbols)
        ],
    }


def _request(key: str = "phase6n-observation-001") -> dict:
    return {
        "idempotency_key": key,
        "interval": "1d",
        "range": "3mo",
        "max_symbols": 5,
        "session_policy": "market-aware",
    }


def _row(
    symbol: str,
    price: float,
    *,
    observed_at: str = "2026-07-13T20:00:00+00:00",
    retrieved_at: str = "2026-07-13T20:05:00+00:00",
    source_status: str = "live/fresh",
) -> dict:
    return {
        "symbol": symbol,
        "identity": {
            "symbol": symbol,
            "asset_class": "equity",
            "exchange": "NASDAQ",
            "identity_status": "exact",
        },
        "status": "fresh" if source_status == "live/fresh" else "stale",
        "source_status": source_status,
        "observed_at": observed_at,
        "retrieved_at": retrieved_at,
        "fetched_at": retrieved_at,
        "quote": {
            "last_price": price,
            "change_pct": 2.0,
            "market_data_as_of": observed_at,
            "retrieved_at": retrieved_at,
            "provider": "yfinance",
            "source_url": f"https://finance.yahoo.com/quote/{symbol}",
            "source_status": source_status,
        },
        "performance": {"return_1w_pct": 2.0},
        "risk": {"realized_volatility_1m_pct": 18.0},
        "technicals": {"rsi_14": 54.0},
        "financials": {"availability": "available", "pe_ratio": 24.0},
        "catalysts": {"earnings": [], "news": []},
        "source_register": [
            {
                "provider": "yfinance",
                "source_url": f"https://finance.yahoo.com/quote/{symbol}",
                "source_status": source_status,
                "observed_at": observed_at,
                "retrieved_at": retrieved_at,
            }
        ],
        "confidence": 0.8,
        "caveat": "Delayed public observation.",
        "data_gap": "No licensed realtime tick stream.",
        "not_financial_advice": True,
    }


def _result(rows: list[dict], *, calls: int = 1, missing: list[dict] | None = None) -> dict:
    return {
        "rows": rows,
        "provider_budget": {
            "maximum_calls": 16,
            "actual_calls": calls,
            "actual_calls_by_operation": {"yfinance:multi-history": calls},
            "cache_hits": 0,
            "stale_hits": 0,
            "failed_calls": len(missing or []),
            "blocked_calls": 0,
            "skipped_calls": 0,
        },
        "missing_capabilities": missing or [],
        "provider_states": [
            {
                "provider": "yfinance",
                "operation": "multi-history",
                "configured": True,
                "contacted": bool(calls),
                "source_status": rows[0]["source_status"] if rows else "unavailable",
            }
        ],
    }


def test_phase6n_plan_is_stable_bounded_and_session_honest():
    from lib.watchlist_observation_runs import (
        MAX_OBSERVATION_PROVIDER_CALLS,
        MAX_OBSERVATION_SYMBOLS,
        build_observation_run_plan,
        validate_observation_request,
    )
    from lib.identity_tenancy import local_test_context

    context = local_test_context("analyst-a")
    validated = validate_observation_request(_request())
    first = build_observation_run_plan(context, _watchlist(), validated, now=CLOSED_NOW)
    second = build_observation_run_plan(context, _watchlist(), validated, now=CLOSED_NOW)

    assert first == second
    assert first["run_id"] == second["run_id"]
    assert first["bounds"]["maximum_symbols"] == MAX_OBSERVATION_SYMBOLS == 5
    assert first["provider_budget"]["maximum_calls"] <= MAX_OBSERVATION_PROVIDER_CALLS == 16
    assert first["bounds"]["maximum_concurrency"] <= 2
    assert first["bounds"]["timeout_seconds"] <= 75
    assert first["bounds"]["maximum_payload_bytes"] <= 250_000
    assert first["session"]["market_open_claimed"] is False
    assert first["session"]["calendar_status"] == "proxy-unverified"
    decisions = {row["symbol"]: row for row in first["symbol_plan"]}
    assert decisions["AAPL"]["due_mode"] == "cache-only"
    assert decisions["BTCUSDT"]["due_mode"] == "provider-refresh"
    assert first["provider_budget"]["planned_calls_by_operation"]["alpha-vantage:overview"] == 0


def test_phase6n_plan_respects_quota_and_rejects_client_identity(monkeypatch):
    monkeypatch.setenv("ALPHAVANTAGE_API_KEY", "test-alpha-vantage-key")
    monkeypatch.setenv("FINNHUB_API_KEY", "test-finnhub-key")

    from lib.watchlist_observation_runs import build_observation_run_plan, validate_observation_request
    from lib.identity_tenancy import local_test_context

    with pytest.raises(ValueError, match="server-derived"):
        validate_observation_request({**_request(), "tenant_id": "client-tenant"})
    with pytest.raises(ValueError, match="maximum"):
        validate_observation_request({**_request(), "max_symbols": 6})

    plan = build_observation_run_plan(
        local_test_context("analyst-a"),
        _watchlist(("AAPL", "MSFT")),
        validate_observation_request(_request()),
        quota_usage={"alpha_vantage_daily": 25, "finnhub_window": 29},
        now=OPEN_NOW,
    )

    calls = plan["provider_budget"]["planned_calls_by_operation"]
    assert calls["alpha-vantage:overview"] == 0
    assert calls["finnhub:earnings-calendar"] + calls["finnhub:company-news"] <= 1
    assert any(row["reason"] == "daily-quota-exhausted" for row in plan["skipped_capabilities"])
    assert plan["provider_budget"]["next_safe_refresh_at"]
    assert plan["retry_policy"] == {"automatic_retries": 0, "backoff_on_429": True}


def test_phase6n_store_is_idempotent_single_flight_cancellable_and_tenant_isolated(tmp_path: Path):
    from lib.identity_tenancy import local_test_context
    from lib.watchlist_observation_runs import (
        ObservationRunBusy,
        ObservationRunConflict,
        ObservationRunStore,
        build_observation_run_plan,
        validate_observation_request,
    )

    store = ObservationRunStore(tmp_path / "account.db")
    account_a = local_test_context("analyst-a")
    account_b = local_test_context("analyst-b")
    request = validate_observation_request(_request())
    plan = build_observation_run_plan(account_a, _watchlist(), request, now=OPEN_NOW)

    queued = store.create_run(account_a, _watchlist(), request, plan, now=OPEN_NOW)
    replay = store.create_run(account_a, _watchlist(), request, plan, now=OPEN_NOW)
    assert queued["status"] == "queued"
    assert replay["run_id"] == queued["run_id"]
    assert replay["idempotent_replay"] is True
    with pytest.raises(ObservationRunConflict):
        store.create_run(
            account_a,
            _watchlist(),
            {**request, "range": "1y"},
            plan,
            now=OPEN_NOW,
        )
    other_request = validate_observation_request(_request("phase6n-observation-002"))
    other_plan = build_observation_run_plan(account_a, _watchlist(), other_request, now=OPEN_NOW)
    with pytest.raises(ObservationRunBusy):
        store.create_run(account_a, _watchlist(), other_request, other_plan, now=OPEN_NOW)

    cancelled = store.cancel_run(account_a, queued["run_id"], now=OPEN_NOW)
    assert cancelled["status"] == "cancelled"
    assert cancelled["completed_at"]
    assert store.get_run(account_b, queued["run_id"]) is None
    assert store.list_runs(account_b) == []
    with pytest.raises(KeyError):
        store.cancel_run(account_b, queued["run_id"], now=OPEN_NOW)


def test_phase6n_atomic_snapshots_preserve_lkg_and_separate_clocks(tmp_path: Path):
    from lib.identity_tenancy import local_test_context
    from lib.watchlist_observation_runs import (
        ObservationRunStore,
        build_observation_run_plan,
        validate_observation_request,
    )

    store = ObservationRunStore(tmp_path / "account.db")
    context = local_test_context("analyst-a")
    watchlist = _watchlist(("AAPL",))

    first_request = validate_observation_request(_request("phase6n-snapshot-001"))
    first_plan = build_observation_run_plan(context, watchlist, first_request, now=OPEN_NOW)
    first = store.create_run(context, watchlist, first_request, first_plan, now=OPEN_NOW)
    store.start_run(context, first["run_id"], now=OPEN_NOW)
    completed = store.commit_run(
        context,
        first["run_id"],
        _result([_row("AAPL", 100.0)]),
        now=OPEN_NOW,
    )
    first_snapshot = store.list_snapshots(context, first["run_id"])[0]

    assert completed["status"] == "completed"
    assert completed["attempted_at"] == OPEN_NOW.isoformat()
    assert completed["completed_at"] == OPEN_NOW.isoformat()
    assert first_snapshot["observed_at"] == "2026-07-13T20:00:00+00:00"
    assert first_snapshot["retrieved_at"] == "2026-07-13T20:05:00+00:00"

    second_request = validate_observation_request(_request("phase6n-snapshot-002"))
    second_plan = build_observation_run_plan(context, watchlist, second_request, now=OPEN_NOW)
    second = store.create_run(context, watchlist, second_request, second_plan, now=OPEN_NOW)
    store.start_run(context, second["run_id"], now=OPEN_NOW)
    partial = store.commit_run(
        context,
        second["run_id"],
        _result(
            [],
            calls=1,
            missing=[
                {
                    "symbol": "AAPL",
                    "provider": "yfinance",
                    "capability": "history",
                    "source_status": "provider-error",
                    "reason": "controlled-offline",
                }
            ],
        ),
        now=OPEN_NOW,
    )
    retained = store.list_snapshots(context, second["run_id"])[0]

    assert partial["status"] == "partial"
    assert partial["lkg_reused_count"] == 1
    assert retained["source_status"] == "stale"
    assert retained["lkg_source_snapshot_id"] == first_snapshot["snapshot_id"]
    assert retained["payload"]["quote"]["last_price"] == 100.0
    assert retained["observed_at"] == first_snapshot["observed_at"]
    assert retained["retrieved_at"] == OPEN_NOW.isoformat()


def test_phase6n_malformed_result_rolls_back_without_replacing_lkg(tmp_path: Path):
    from lib.identity_tenancy import local_test_context
    from lib.watchlist_observation_runs import (
        ObservationRunStore,
        build_observation_run_plan,
        validate_observation_request,
    )

    store = ObservationRunStore(tmp_path / "account.db")
    context = local_test_context("analyst-a")
    watchlist = _watchlist(("AAPL",))
    good_request = validate_observation_request(_request("phase6n-good-atomic"))
    good_plan = build_observation_run_plan(context, watchlist, good_request, now=OPEN_NOW)
    good = store.create_run(context, watchlist, good_request, good_plan, now=OPEN_NOW)
    store.start_run(context, good["run_id"], now=OPEN_NOW)
    store.commit_run(context, good["run_id"], _result([_row("AAPL", 101.0)]), now=OPEN_NOW)

    bad_request = validate_observation_request(_request("phase6n-bad-atomic"))
    bad_plan = build_observation_run_plan(context, watchlist, bad_request, now=OPEN_NOW)
    bad = store.create_run(context, watchlist, bad_request, bad_plan, now=OPEN_NOW)
    store.start_run(context, bad["run_id"], now=OPEN_NOW)
    malformed = _row("MSFT", 200.0)
    malformed["private_note"] = "x" * 260_000

    with pytest.raises(ValueError):
        store.commit_run(context, bad["run_id"], _result([malformed]), now=OPEN_NOW)
    assert store.list_snapshots(context, bad["run_id"]) == []
    latest = store.latest_last_known_good(context, watchlist["resource_id"], "AAPL")
    assert latest["payload"]["quote"]["last_price"] == 101.0
    failed = store.fail_run(context, bad["run_id"], error_code="provider-output-invalid", now=OPEN_NOW)
    assert failed["status"] == "failed"
    assert "private_note" not in json.dumps(failed)


def test_phase6n_comparable_runs_feed_attention_with_zero_provider_calls(tmp_path: Path):
    from lib.attention_desk import build_attention_desk_contract
    from lib.identity_tenancy import local_test_context
    from lib.watchlist_observation_runs import (
        ObservationRunStore,
        build_observation_run_plan,
        validate_observation_request,
    )

    store = ObservationRunStore(tmp_path / "account.db")
    context = local_test_context("analyst-a")
    watchlist = _watchlist(("AAPL",))
    for index, price in enumerate((100.0, 103.0), start=1):
        request = validate_observation_request(_request(f"phase6n-diff-00{index}"))
        plan = build_observation_run_plan(context, watchlist, request, now=OPEN_NOW)
        run = store.create_run(context, watchlist, request, plan, now=OPEN_NOW)
        store.start_run(context, run["run_id"], now=OPEN_NOW)
        store.commit_run(context, run["run_id"], _result([_row("AAPL", price)]), now=OPEN_NOW)

    attention = store.build_attention_context(context, now=OPEN_NOW)
    desk = build_attention_desk_contract(
        watchlist_changes=attention["changes"],
        observation_run=attention,
        now=OPEN_NOW,
        mode="cache",
    )

    assert attention["provider_call_count"] == 0
    assert attention["latest_run"]["status"] == "completed"
    assert attention["material_change_count"] >= 1
    assert any(row["subject"]["symbol"] == "AAPL" for row in desk["items"])
    assert desk["summary"]["provider_call_count"] == 0
    assert desk["observation_run"]["provider_call_count"] == 0


def test_phase6n_schema_and_supabase_migration_are_tenant_qualified():
    from lib.research_workspace_schema import SCHEMA_VERSION, TABLE_NAMES

    root = Path(__file__).resolve().parents[1]
    migration = (root / "supabase/migrations/20260714230000_phase6n_observation_and_hosted_hardening.sql").read_text(encoding="utf-8").lower()

    assert SCHEMA_VERSION >= 14
    for table in (
        "tenant_observation_runs",
        "tenant_observation_snapshots",
        "tenant_provider_quota_ledger",
        "tenant_observation_run_audit",
    ):
        assert table in TABLE_NAMES
    for table in (
        "global_terminal_observation_runs",
        "global_terminal_observation_snapshots",
        "global_terminal_provider_quota_ledger",
        "global_terminal_observation_run_audit",
    ):
        assert f"create table public.{table}" in migration
        assert f"alter table public.{table} enable row level security" in migration
    assert "auth.uid()" in migration
    assert "tenant_id = tenant_id" not in migration
    assert "revoke all" in migration
    assert "references public.global_terminal_tenants(id)" in migration
    assert "foreign key (tenant_id, owner_user_id, run_id)" in migration
    assert "global_terminal_tenant_memberships" in migration
    assert "global_terminal_record_observation_run_audit" in migration


def test_phase6n_cache_only_adapter_never_counts_or_contacts_provider(monkeypatch):
    from types import SimpleNamespace

    from lib.identity_tenancy import local_test_context
    from lib.watchlist_observation_runs import (
        SourceBackedObservationAdapter,
        build_observation_run_plan,
        validate_observation_request,
    )
    import lib.watchlist_desk as watchlist_desk
    import lib.watchlist_observation_runs as observation_runs

    calls = {"history": 0, "alpha": 0, "earnings": 0, "news": 0}

    def unexpected(name):
        def fail(*_args, **_kwargs):
            calls[name] += 1
            raise AssertionError(f"cache-only contacted {name}")

        return fail

    history = [
        {
            "date": "2026-07-10",
            "open": 100.0,
            "high": 102.0,
            "low": 99.0,
            "close": 101.0,
            "volume": 1_000_000,
        }
    ]
    monkeypatch.setattr(watchlist_desk, "_prime_history_batch", unexpected("history"))
    monkeypatch.setattr(observation_runs, "fetch_alpha_vantage_overview", unexpected("alpha"))
    monkeypatch.setattr(observation_runs, "fetch_finnhub_earnings_calendar", unexpected("earnings"))
    monkeypatch.setattr(observation_runs, "fetch_finnhub_company_news", unexpected("news"))
    monkeypatch.setattr(
        observation_runs,
        "load_runtime_cache_record",
        lambda _key: SimpleNamespace(data=history),
    )

    request = validate_observation_request({**_request("phase6n-cache-only"), "session_policy": "cache-only"})
    watchlist = _watchlist(("AAPL",))
    plan = build_observation_run_plan(local_test_context("analyst-a"), watchlist, request, now=OPEN_NOW)
    result = SourceBackedObservationAdapter().observe(
        watchlist,
        plan,
        previous_rows={},
        cancellation_requested=lambda: False,
    )

    assert calls == {"history": 0, "alpha": 0, "earnings": 0, "news": 0}
    assert result["provider_budget"]["actual_calls"] == 0
    assert all(value == 0 for value in result["provider_budget"]["actual_calls_by_operation"].values())
    assert all(row["contacted"] is False for row in result["provider_states"])
