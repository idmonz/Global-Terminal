from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


NOW = datetime(2026, 7, 11, 0, 0, tzinfo=timezone.utc)


def _inputs() -> dict:
    shared_news = {
        "title": "Port disruption changes Red Sea shipping schedule",
        "summary": "A named port authority reported a temporary schedule change.",
        "provider": "public-rss",
        "source_url": "https://example.test/news/red-sea-schedule",
        "source_status": "live/fresh",
        "published_at": "2026-07-10T22:00:00+00:00",
        "fetched_at": "2026-07-10T22:02:00+00:00",
        "confidence": 0.72,
        "region": "Red Sea",
        "severity": "high",
        "related_assets": ["BRENT"],
        "caveat": "One public report; independent confirmation remains useful.",
        "data_gap": "No live vessel-flow telemetry.",
    }
    return {
        "watchlist_changes": [
            {
                "change_id": "chg-aapl-price",
                "change_type": "price",
                "symbol": "AAPL",
                "title": "AAPL saved price changed",
                "summary": "Saved close changed +4.2% between completed snapshots.",
                "severity": "material",
                "source_status": "cached",
                "provider": "alpha-vantage",
                "source_url": "https://www.alphavantage.co/",
                "observed_at": "2026-07-10T20:00:00+00:00",
                "retrieved_at": "2026-07-10T20:05:00+00:00",
                "confidence": 0.8,
                "caveat": "Saved observation comparison, not a live tick.",
                "data_gap": "Intraday sequence is not represented.",
            }
        ],
        "catalysts": [
            {
                "event_id": "earnings-aapl-q3",
                "symbol": "AAPL",
                "title": "AAPL earnings date recorded",
                "summary": "The cached company calendar records a reporting date.",
                "event_type": "earnings",
                "severity": "material",
                "provider": "finnhub",
                "source_url": "https://finnhub.io/",
                "source_status": "cached",
                "observed_at": "2026-07-10T18:00:00+00:00",
                "retrieved_at": "2026-07-10T18:05:00+00:00",
                "confidence": 0.75,
                "caveat": "Calendar dates can change.",
                "data_gap": "No issuer filing attached.",
            }
        ],
        "news_rows": [shared_news],
        "daily_brief": {
            "comparison": {
                "changed": [
                    {
                        "claim_id": "brief-global-risk",
                        "changed_fields": ["severity", "statement"],
                        "after": {
                            "claim_id": "brief-global-risk",
                            "claim_kind": "global_risk_observation",
                            "statement": "Red Sea logistics evidence moved from watch to elevated.",
                            "severity": "high",
                            "provider": "public-rss",
                            "source_url": "https://example.test/news/red-sea-schedule",
                            "source_status": "live/fresh",
                            "observed_at": "2026-07-10T22:00:00+00:00",
                            "fetched_at": "2026-07-10T22:02:00+00:00",
                            "confidence": 0.72,
                            "linked_regions": ["Red Sea"],
                            "linked_symbols": ["BRENT"],
                            "caveat": "Claim preserves the source report wording.",
                            "data_gap": "No causal market impact is asserted.",
                        },
                    }
                ],
                "refreshed": [
                    {
                        "claim_id": "brief-fetch-only",
                        "before_fetched_at": "2026-07-10T21:00:00+00:00",
                        "after_fetched_at": "2026-07-10T21:10:00+00:00",
                    }
                ],
                "added": [],
                "removed": [],
            }
        },
        "provider_health": [
            {
                "provider": "finnhub",
                "source": "company-news",
                "status": "rate-limited",
                "source_status": "rate-limited",
                "fetched_at": "2026-07-10T22:05:00+00:00",
                "source_url": "https://finnhub.io/",
                "warning": "Free quota was reached; cached evidence retained.",
                "confidence": 1.0,
                "caveat": "This is provider health, not a market event.",
                "data_gap": "No new company-news rows until the quota resets.",
            }
        ],
        "war_map_events": [
            {
                "marker_id": "marker-red-sea",
                "title": "Red Sea schedule disruption",
                "region": "Red Sea",
                "severity": "high",
                "provider": "public-rss",
                "source_url": "https://example.test/news/red-sea-schedule",
                "source_status": "live/fresh",
                "observed_at": "2026-07-10T22:00:00+00:00",
                "fetched_at": "2026-07-10T22:02:00+00:00",
                "confidence": 0.72,
                "related_assets": ["BRENT"],
                "summary": "The map links the report to a named region and transmission channel.",
                "caveat": "Map co-location is context, not causality.",
                "data_gap": "No live AIS layer.",
                "related_news": [shared_news],
            }
        ],
    }


def test_phase6m_normalizes_every_source_kind_with_stable_fingerprints():
    from lib.attention_desk import build_attention_desk_contract

    first = build_attention_desk_contract(**_inputs(), now=NOW)
    second_inputs = _inputs()
    second_inputs["news_rows"][0]["fetched_at"] = "2026-07-10T22:09:00+00:00"
    second = build_attention_desk_contract(**second_inputs, now=NOW)

    assert first["attention_desk_version"] == "attention_desk.v1"
    assert {origin for row in first["items"] for origin in row["origins"]} >= {
        "watchlist-change",
        "catalyst",
        "news",
        "daily-brief",
        "provider-health",
    }
    assert [row["fingerprint"] for row in first["items"]] == [
        row["fingerprint"] for row in second["items"]
    ]
    assert all(len(row["fingerprint"]) == 64 for row in first["items"])
    assert all(row["provider_call_count"] == 0 for row in first["items"])


def test_phase6m_fetch_clock_only_refresh_is_not_material():
    from lib.attention_desk import build_attention_desk_contract

    desk = build_attention_desk_contract(**_inputs(), now=NOW)
    refresh = next(row for row in desk["all_items"] if row["change_kind"] == "fetch-refresh")

    assert refresh["material"] is False
    assert refresh["severity"] == "info"
    assert refresh["fingerprint"] not in {row["fingerprint"] for row in desk["items"]}
    assert desk["summary"]["fetch_refresh_count"] == 1


def test_phase6m_cross_surface_dedupe_preserves_sources_and_exact_origins():
    from lib.attention_desk import build_attention_desk_contract

    desk = build_attention_desk_contract(**_inputs(), now=NOW)
    red_sea = [row for row in desk["items"] if row["subject"]["region"] == "Red Sea"]

    assert len(red_sea) == 1
    assert set(red_sea[0]["origins"]) >= {"news", "daily-brief", "war-map"}
    assert {row["provider"] for row in red_sea[0]["source_register"]} == {"public-rss"}
    assert red_sea[0]["drilldowns"]["news"].startswith("/?view=news&")
    assert red_sea[0]["drilldowns"]["brief"].startswith("/?view=daily-brief&")
    assert red_sea[0]["drilldowns"]["map"].startswith("/?view=war-room-map&")


def test_phase6m_ranking_is_explained_and_non_advisory():
    from lib.attention_desk import build_attention_desk_contract, find_forbidden_attention_language

    desk = build_attention_desk_contract(**_inputs(), now=NOW)
    scores = [row["rank"]["score"] for row in desk["items"]]

    assert scores == sorted(scores, reverse=True)
    assert all(row["rank"]["factors"] for row in desk["items"])
    assert desk["items"][0]["review_state"] == "new"
    assert find_forbidden_attention_language(desk) == []
    encoded = json.dumps(desk, ensure_ascii=False).lower()
    assert "buy now" not in encoded
    assert "target price" not in encoded
    assert "place order" not in encoded


def test_phase6m_checkpoint_counts_do_not_change_provider_clocks():
    from lib.attention_desk import build_attention_desk_contract

    checkpoint = {"reviewed_through_at": "2026-07-10T21:00:00+00:00", "version": 2}
    desk = build_attention_desk_contract(**_inputs(), checkpoint=checkpoint, now=NOW)
    source_row = next(row for row in desk["items"] if row["origin_kind"] == "watchlist-change")

    assert desk["since_last_review"]["material"] >= 1
    assert desk["checkpoint"]["reviewed_through_at"] == checkpoint["reviewed_through_at"]
    assert source_row["observed_at"] == "2026-07-10T20:00:00+00:00"
    assert source_row["retrieved_at"] == "2026-07-10T20:05:00+00:00"


def test_phase6m_policy_filters_are_validated_without_erasing_source_truth():
    from lib.attention_desk import build_attention_desk_contract, validate_attention_policy

    policy = validate_attention_policy(
        {
            "minimum_severity": "high",
            "included_change_kinds": ["new-evidence", "source-degradation"],
            "source_health_handling": "include",
            "version": 3,
        }
    )
    desk = build_attention_desk_contract(**_inputs(), policy=policy, now=NOW)

    assert all(row["severity"] in {"high", "critical"} for row in desk["items"])
    assert all(row["change_kind"] in set(policy["included_change_kinds"]) for row in desk["items"])
    assert desk["summary"]["unfiltered_material_count"] > desk["summary"]["visible_count"]
    with pytest.raises(ValueError):
        validate_attention_policy({"tenant_id": "client-controlled", "minimum_severity": "high"})


def test_phase6m_review_store_is_versioned_forward_safe_and_tenant_isolated(tmp_path: Path):
    from lib.attention_desk import AttentionConflict, AttentionReviewStore
    from lib.identity_tenancy import local_test_context

    store = AttentionReviewStore(tmp_path / "account.db")
    account_a = local_test_context("analyst-a")
    account_b = local_test_context("analyst-b")
    fingerprint = "a" * 64

    reviewed = store.update_state(account_a, fingerprint, action="review", expected_version=0, now=NOW)
    assert reviewed["review_state"] == "reviewed"
    with pytest.raises(AttentionConflict):
        store.update_state(account_a, fingerprint, action="acknowledge", expected_version=0, now=NOW)
    acknowledged = store.update_state(account_a, fingerprint, action="acknowledge", expected_version=1, now=NOW)
    assert acknowledged["review_state"] == "acknowledged"
    with pytest.raises(ValueError):
        store.update_state(account_a, fingerprint, action="review", expected_version=2, now=NOW)
    assert store.list_states(account_b, [fingerprint]) == {}


def test_phase6m_snooze_has_bounded_expiry_and_safe_undo(tmp_path: Path):
    from lib.attention_desk import AttentionReviewStore
    from lib.identity_tenancy import local_test_context

    store = AttentionReviewStore(tmp_path / "account.db")
    context = local_test_context("analyst-a")
    fingerprint = "b" * 64
    until = NOW + timedelta(hours=4)

    snoozed = store.update_state(
        context,
        fingerprint,
        action="snooze",
        expected_version=0,
        snoozed_until=until,
        now=NOW,
    )
    assert snoozed["review_state"] == "snoozed"
    restored = store.update_state(context, fingerprint, action="undo-snooze", expected_version=1, now=NOW)
    assert restored["review_state"] == "new"
    again = store.update_state(
        context,
        fingerprint,
        action="snooze",
        expected_version=2,
        snoozed_until=until,
        now=NOW,
    )
    expired = store.list_states(context, [fingerprint], now=until + timedelta(seconds=1))[fingerprint]
    assert again["snoozed_until"] == until.isoformat()
    assert expired["review_state"] == "new"
    assert expired["snooze_expired"] is True
    with pytest.raises(ValueError):
        store.update_state(
            context,
            "c" * 64,
            action="snooze",
            expected_version=0,
            snoozed_until=NOW + timedelta(days=31),
            now=NOW,
        )


def test_phase6m_policy_checkpoint_and_audit_are_private_bounded_and_conflicted(tmp_path: Path):
    from lib.attention_desk import AttentionConflict, AttentionReviewStore
    from lib.identity_tenancy import local_test_context

    store = AttentionReviewStore(tmp_path / "account.db")
    account_a = local_test_context("analyst-a")
    account_b = local_test_context("analyst-b")

    policy = store.save_policy(
        account_a,
        {
            "minimum_severity": "material",
            "included_change_kinds": ["market-change", "new-evidence", "source-degradation"],
            "source_health_handling": "include",
        },
        expected_version=0,
        now=NOW,
    )
    checkpoint = store.mark_checkpoint(account_a, expected_version=0, now=NOW)
    with pytest.raises(AttentionConflict):
        store.save_policy(account_a, policy, expected_version=0, now=NOW)

    assert policy["version"] == 1
    assert checkpoint["version"] == 1
    assert store.get_policy(account_b)["version"] == 0
    assert store.get_checkpoint(account_b)["version"] == 0
    audit = store.list_audit(account_a, limit=500)
    assert len(audit) <= 100
    encoded = json.dumps(audit).lower()
    assert "tenant_id" not in encoded
    assert "user_id" not in encoded


def test_phase6m_supabase_migration_qualifies_rls_and_adds_attention_tables():
    root = Path(__file__).resolve().parents[1]
    migration = (root / "supabase/migrations/20260711234452_phase6m_attention_and_rls_hardening.sql").read_text(encoding="utf-8")
    lowered = migration.lower()

    assert "m.tenant_id = tenant_id" not in lowered
    assert "global_terminal_workspace_preferences.tenant_id" in lowered
    assert "security definer" in lowered
    assert "set search_path = ''" in lowered
    assert "auth.uid()" in lowered
    for table in (
        "global_terminal_attention_states",
        "global_terminal_attention_policies",
        "global_terminal_attention_checkpoints",
        "global_terminal_attention_audit",
    ):
        assert f"create table if not exists public.{table}" in lowered
        assert f"alter table public.{table} enable row level security" in lowered


def test_phase6m_analyst_return_state_preserves_bounded_attention_filters():
    from lib.analyst_workspace import sanitize_workspace_return_state

    safe = sanitize_workspace_return_state(
        {"origin": "attention-desk", "originState": "mode=fixture&review=needs-review"}
    )

    assert safe == {
        "origin": "attention-desk",
        "originState": "mode=fixture&review=needs-review",
    }
    assert "originState" not in sanitize_workspace_return_state(
        {"origin": "attention-desk", "originState": "mode=fixture&review=needs-review\\..\\secret"}
    )
