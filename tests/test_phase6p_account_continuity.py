from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest


USER_A = "11111111-1111-4111-8111-111111111111"
TENANT_A = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"


class FakeResponse:
    def __init__(self, status_code: int, payload: Any):
        self.status_code = status_code
        self._payload = payload
        self.headers: dict[str, str] = {}

    def json(self) -> Any:
        return self._payload


class FakeTransport:
    def __init__(self, responses: list[FakeResponse]):
        self.responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    def request(self, method: str, url: str, **kwargs: Any) -> FakeResponse:
        observed = {"method": method, "url": url, **kwargs}
        if isinstance(observed.get("json"), dict) and "password" in observed["json"]:
            observed = {**observed, "json": {**observed["json"], "password": "[redacted]"}}
        self.calls.append(observed)
        if not self.responses:
            raise AssertionError(f"Unexpected transport call: {method} {url}")
        return self.responses.pop(0)


def hosted_context() -> dict[str, Any]:
    return {
        "state": "authenticated-hosted",
        "authenticated": True,
        "identity_provider": "supabase",
        "user_id": USER_A,
        "tenant_id": TENANT_A,
        "display_name": "Account A",
        "role": "owner",
        "plan": "free",
        "session_expires_at": "2026-07-15T12:00:00+00:00",
        "_supabase_access_token": "access-secret",
    }


def test_phase6p_supabase_config_and_health_never_expose_credentials(monkeypatch: pytest.MonkeyPatch):
    from lib.supabase_account_runtime import SupabaseAccountConfig, SupabaseRepositoryHealth

    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "publishable-secret-value")
    config = SupabaseAccountConfig.from_env()
    health = SupabaseRepositoryHealth(config).public_snapshot()

    assert config.configured is True
    assert "publishable-secret-value" not in repr(config)
    assert "publishable-secret-value" not in json.dumps(health, sort_keys=True)
    assert health["configured"] is True
    assert health["contacted"] is False
    assert health["authenticated"] is False
    assert health["hosted_verified"] is False


def test_phase6p_auth_failure_stage_is_bounded_and_public_message_stays_generic():
    from lib.supabase_account_runtime import SupabaseAuthenticationError

    error = SupabaseAuthenticationError(
        "Hosted sign-in could not be verified.",
        stage="Membership Provider: Rejected / private detail",
    )
    assert str(error) == "Hosted sign-in could not be verified."
    assert error.stage == "membership-provider-rejected-private-detail"
    assert len(error.stage) <= 64


def test_phase6p_hosted_session_derives_identity_and_tenant_from_supabase():
    from lib.identity_tenancy import public_account_payload
    from lib.supabase_account_runtime import (
        SupabaseAccountConfig,
        SupabaseAuthClient,
        SupabaseHostedSessionManager,
    )

    transport = FakeTransport(
        [
            FakeResponse(
                200,
                {
                    "access_token": "access-secret",
                    "refresh_token": "refresh-secret",
                    "expires_in": 3600,
                    "user": {"id": USER_A, "email": "accounta@example.com"},
                },
            ),
            FakeResponse(200, [{"tenant_id": TENANT_A, "role": "owner"}]),
        ]
    )
    config = SupabaseAccountConfig("https://example.supabase.co", "publishable-secret-value")
    manager = SupabaseHostedSessionManager(SupabaseAuthClient(config, transport=transport))

    credentials = manager.create("accounta@example.com", "password-not-logged")
    context = manager.resolve(credentials.session_token)

    assert context["authenticated"] is True
    assert context["identity_provider"] == "supabase"
    assert context["user_id"] == USER_A
    assert context["tenant_id"] == TENANT_A
    assert context["role"] == "owner"
    assert context["_supabase_access_token"] == "access-secret"
    assert manager.validate_csrf(
        credentials.session_token,
        credentials.csrf_token,
        credentials.csrf_token,
    ) is True
    public = public_account_payload(context)
    encoded = json.dumps(public, sort_keys=True)
    assert "access-secret" not in encoded
    assert "refresh-secret" not in encoded
    assert "password-not-logged" not in json.dumps(transport.calls, sort_keys=True)
    assert transport.calls[1]["params"]["user_id"] == f"eq.{USER_A}"
    assert "tenant_id" not in transport.calls[0].get("json", {})


def test_phase6p_sign_in_defers_existing_password_policy_to_supabase():
    from lib.supabase_account_runtime import SupabaseAccountConfig, SupabaseAuthClient

    transport = FakeTransport(
        [
            FakeResponse(
                200,
                {
                    "access_token": "access-secret",
                    "refresh_token": "refresh-secret",
                    "expires_in": 3600,
                    "user": {"id": USER_A, "email": "accounta@example.com"},
                },
            )
        ]
    )
    client = SupabaseAuthClient(
        SupabaseAccountConfig("https://example.supabase.co", "publishable-secret-value"),
        transport=transport,
    )

    result = client.sign_in("accounta@example.com", "six777")

    assert result["user_id"] == USER_A
    assert transport.calls[0]["json"]["password"] == "[redacted]"


def test_phase6p_sign_in_rejects_only_empty_or_unbounded_password_shapes():
    from lib.supabase_account_runtime import (
        SupabaseAccountConfig,
        SupabaseAuthClient,
        SupabaseAuthenticationError,
    )

    transport = FakeTransport([])
    client = SupabaseAuthClient(
        SupabaseAccountConfig("https://example.supabase.co", "publishable-secret-value"),
        transport=transport,
    )

    with pytest.raises(SupabaseAuthenticationError) as empty:
        client.sign_in("accounta@example.com", "")
    with pytest.raises(SupabaseAuthenticationError) as oversized:
        client.sign_in("accounta@example.com", "x" * 1025)

    assert empty.value.stage == "credential-shape-invalid"
    assert oversized.value.stage == "credential-shape-invalid"
    assert transport.calls == []


def test_phase6p_account_bundle_is_bounded_identity_free_and_restorable(tmp_path: Path):
    from lib.account_continuity import AccountBundleStore
    from lib.research_workspace_db import execute_query, json_dumps

    source = tmp_path / "source.db"
    target = tmp_path / "target.db"
    context = hosted_context()
    now = "2026-07-15T08:00:00+00:00"
    execute_query(
        """
        INSERT INTO tenant_watchlists (
          resource_id, tenant_id, owner_user_id, name, source_key,
          source_fingerprint, version, active, created_at, updated_at
        ) VALUES (?, ?, ?, 'Daily Radar', 'phase6p:primary', 'fingerprint', 1, 1, ?, ?)
        """,
        ("twl_phase6p", TENANT_A, USER_A, now, now),
        db_path=source,
    )
    execute_query(
        """
        INSERT INTO tenant_watchlist_items (
          resource_id, tenant_id, watchlist_resource_id, symbol, asset_class,
          display_name, provider, source_status, evidence_json, version,
          active, created_at, updated_at
        ) VALUES (?, ?, ?, 'AAPL', 'equity', 'Apple Inc.', 'saved-observation',
                  'cached', ?, 1, 1, ?, ?)
        """,
        (
            "twi_phase6p",
            TENANT_A,
            "twl_phase6p",
            json_dumps({"source_status": "cached", "private_note": "must-not-leave-local"}),
            now,
            now,
        ),
        db_path=source,
    )
    execute_query(
        """
        INSERT INTO tenant_attention_states (
          resource_id, tenant_id, owner_user_id, fingerprint, review_state,
          prior_state, version, created_at, updated_at
        ) VALUES ('att_phase6p', ?, ?, ?, 'reviewed', 'new', 1, ?, ?)
        """,
        (TENANT_A, USER_A, "a" * 64, now, now),
        db_path=source,
    )

    bundle = AccountBundleStore(source).capture(context)
    encoded = json.dumps(bundle, sort_keys=True).lower()
    assert bundle["account_continuity_version"] == "account_continuity.v1"
    assert bundle["payload_bytes"] <= 512_000
    assert bundle["row_count"] == 3
    assert "tenant_id" not in encoded
    assert "owner_user_id" not in encoded
    assert "private_note" not in encoded
    assert TENANT_A.lower() not in encoded
    assert USER_A.lower() not in encoded

    restored = AccountBundleStore(target).restore(context, bundle)
    assert restored["status"] == "restored"
    assert restored["inserted_count"] == 3
    watchlist = execute_query(
        "SELECT tenant_id, owner_user_id, name FROM tenant_watchlists WHERE resource_id=?",
        ("twl_phase6p",),
        fetch=True,
        one=True,
        db_path=target,
    )
    assert watchlist == {"tenant_id": TENANT_A, "owner_user_id": USER_A, "name": "Daily Radar"}


def test_phase6p_bundle_rejects_client_identity_and_cross_parent_rows(tmp_path: Path):
    from lib.account_continuity import AccountBundleStore, AccountContinuityValidationError

    bundle = {
        "account_continuity_version": "account_continuity.v1",
        "tables": {
            "tenant_watchlist_items": [
                {
                    "resource_id": "twi_invalid",
                    "tenant_id": "forged",
                    "watchlist_resource_id": "missing-parent",
                    "symbol": "AAPL",
                }
            ]
        },
    }
    with pytest.raises(AccountContinuityValidationError):
        AccountBundleStore(tmp_path / "target.db").restore(hosted_context(), bundle)


def test_phase6p_supabase_document_repository_uses_user_jwt_and_optimistic_rpc():
    from lib.supabase_account_runtime import (
        SupabaseAccountConfig,
        SupabaseAccountDocumentRepository,
    )

    transport = FakeTransport(
        [
            FakeResponse(200, []),
            FakeResponse(200, {"status": "applied", "version": 1, "document_fingerprint": "f" * 64}),
        ]
    )
    repository = SupabaseAccountDocumentRepository(
        SupabaseAccountConfig("https://example.supabase.co", "publishable-secret-value"),
        transport=transport,
    )
    context = hosted_context()
    assert repository.load(context) is None
    result = repository.save(
        context,
        {
            "account_continuity_version": "account_continuity.v1",
            "tables": {},
            "fingerprint": "f" * 64,
            "payload_bytes": 100,
            "row_count": 0,
        },
        expected_version=0,
        idempotency_key="phase6p-repository-0001",
    )
    assert result["status"] == "applied"
    assert transport.calls[0]["headers"]["Authorization"] == "Bearer access-secret"
    assert transport.calls[1]["url"].endswith("/rest/v1/rpc/global_terminal_apply_account_document")
    assert transport.calls[1]["json"]["p_expected_version"] == 0
    public_health = repository.health()
    serialized = json.dumps(public_health, sort_keys=True)
    assert "access-secret" not in serialized
    assert "publishable-secret-value" not in serialized
    assert public_health["contacted"] is True
    assert public_health["read_successful"] is True
    assert public_health["write_successful"] is True


def test_phase6p_document_delete_maps_rpc_conflict_and_validates_idempotency():
    from lib.supabase_account_runtime import (
        SupabaseAccountConfig,
        SupabaseAccountDocumentRepository,
        SupabaseRepositoryConflict,
    )

    transport = FakeTransport(
        [
            FakeResponse(
                200,
                [{"status": "document-version-conflict", "version": 9, "document_fingerprint": "f" * 64}],
            )
        ]
    )
    repository = SupabaseAccountDocumentRepository(
        SupabaseAccountConfig("https://example.supabase.co", "publishable-secret-value"),
        transport=transport,
    )
    with pytest.raises(SupabaseRepositoryConflict) as conflict:
        repository.delete(
            hosted_context(),
            expected_version=3,
            idempotency_key="phase6p-delete-conflict",
        )
    assert conflict.value.current_version == 9
    with pytest.raises(ValueError, match="idempotency"):
        repository.delete(hosted_context(), expected_version=9, idempotency_key="short")


def test_phase6p_migration_is_rls_first_atomic_and_audit_immutable():
    root = Path(__file__).resolve().parents[1]
    migration = root / "supabase/migrations/20260715180000_phase6p_account_continuity.sql"
    sql = migration.read_text(encoding="utf-8").lower()

    assert "global_terminal_account_documents" in sql
    assert "global_terminal_account_document_receipts" in sql
    assert "global_terminal_account_document_audit" in sql
    assert sql.count("enable row level security") >= 3
    assert "auth.uid()" in sql
    assert "security definer" in sql
    assert "set search_path = ''" in sql
    assert "p_expected_version" in sql
    assert "p_idempotency_key" in sql
    assert "document-version-conflict" in sql
    assert "grant execute" in sql
    assert "grant insert" not in sql
    assert "service_role" not in sql


def test_phase6p_env_example_keeps_hosted_auth_server_derived():
    root = Path(__file__).resolve().parents[1]
    template = (root / ".env.example").read_text(encoding="utf-8")

    assert "SUPABASE_URL=" in template
    assert "SUPABASE_PUBLISHABLE_KEY=" in template
    assert "NEXT_PUBLIC_SUPABASE" not in template
    assert "GLOBAL_TERMINAL_HOSTED_AUTH_ENABLED=" in template
    assert "GLOBAL_TERMINAL_ACCOUNT_CONTINUITY_ENABLED=" in template


def test_phase6p_hosted_rls_harness_is_secure_redacted_and_product_key_safe():
    root = Path(__file__).resolve().parents[1]
    script = (root / "scripts/test-phase6p-account-continuity-rls.ps1").read_text(encoding="utf-8")
    lowered = script.lower()

    assert "read-host \"$label password\" -assecurestring" in lowered
    assert "phase6p_hosted_rls_summary.json" in lowered
    assert "phase6p-conformance-$suffix" in lowered
    assert 'documentkey = "research-continuity"' not in lowered
    assert "[security.securestring]$accountapassword" in lowered
    assert "[security.securestring]$accountbpassword" in lowered
    assert "$latencysamplecount" in lowered
    assert "hosted_latency" in lowered
    assert "idempotent_rpc_p95_ms" in lowered
    assert "service_role" not in lowered
    assert USER_A.lower() not in lowered
    assert TENANT_A.lower() not in lowered


def test_phase6p_product_recovery_harness_is_private_and_uses_distinct_repositories():
    root = Path(__file__).resolve().parents[1]
    script = (root / "scripts/test-phase6p-product-recovery.ps1").read_text(encoding="utf-8")
    lowered = script.lower()

    assert 'read-host "account a password" -assecurestring' in lowered
    assert 'read-host "account b password" -assecurestring' in lowered
    assert "phase6p_product_recovery_summary.json" in lowered
    assert "[security.securestring]$accountapassword" in lowered
    assert "[security.securestring]$accountbpassword" in lowered
    assert '"session-one.db"' in lowered
    assert '"session-two.db"' in lowered
    assert "get-availabletcpport" in lowered
    assert "8467" not in lowered
    assert "8567" not in lowered
    assert "phase6p_product_recovery\\$runid" in lowered
    assert "market_provider_calls = 0" in lowered
    assert "runtime_env_injected = $true" in lowered
    assert "$env:supabase_url = $script:supabaseurl" in lowered
    assert "$env:supabase_publishable_key = $script:publishablekey" in lowered
    assert '$env:global_terminal_cookie_secure = "false"' in lowered
    assert "[switch]$runtimepreflightonly" in lowered
    assert "/api/account/session" in lowered
    assert '"configured-unverified"' in lowered
    assert "phase6p_product_recovery_runtime_preflight_summary.json" in lowered
    assert "remote_contacted = $false" in lowered
    assert "preflight remains anonymous and credential-free" in lowered
    assert "test-directsupabaseidentity" in lowered
    assert "credential probe failed" in lowered
    assert "tenant membership query failed" in lowered
    assert "hosted_sign_in_retry_count" in lowered
    assert "account_diagnostic_call_count" in lowered
    assert "scope=local" in lowered
    assert "global_terminal_qa_auth_diagnostics" in lowered
    assert "x-global-terminal-qa-auth-stage" in lowered
    assert "get-safeauthstage" in lowered
    assert "global_terminal_account_db_path" in lowered
    assert "-windowstyle hidden" in lowered
    assert "service_role" not in lowered
    assert USER_A.lower() not in lowered
    assert TENANT_A.lower() not in lowered


def test_phase6p_visual_handoff_uses_isolated_runtime_and_cleans_up():
    root = Path(__file__).resolve().parents[1]
    script = (root / "scripts/run_phase6p_visual_handoff.ps1").read_text(encoding="utf-8")
    lowered = script.lower()

    assert "phase6p-account-" in lowered
    assert "find-availableport" in lowered
    assert "visual:phase6p" in lowered
    assert "visual:verify:phase6p" in lowered
    assert "stop-processtree" in lowered
    assert "remove-item -literalpath $accountartifact" in lowered
    assert "service_role" not in lowered


def test_phase6p_hosted_handoff_prompts_once_and_keeps_credentials_in_process():
    root = Path(__file__).resolve().parents[1]
    script = (root / "scripts/run_phase6p_hosted_handoff.ps1").read_text(encoding="utf-8")
    lowered = script.lower()
    phase6o = (root / "scripts/test-phase6o-alert-rls.ps1").read_text(encoding="utf-8").lower()

    assert lowered.count('read-host "account a password" -assecurestring') == 1
    assert lowered.count('read-host "account b password" -assecurestring') == 1
    assert "test-phase6o-alert-rls.ps1" in lowered
    assert "test-phase6p-account-continuity-rls.ps1" in lowered
    assert "test-phase6p-product-recovery.ps1" in lowered
    assert "phase6p_hosted_handoff_summary.json" in lowered
    assert "phase6p_hosted_handoff_preflight_summary.json" in lowered
    assert "$preflightonly" in lowered
    assert "$resumerecovery" in lowered
    assert "-runtimepreflightonly" in lowered
    assert "phase6p_product_recovery_runtime_preflight_summary.json" in lowered
    assert '"phase6p.product.recovery.runtime-preflight.v1"' in lowered
    assert "isolated_runtime_preflight_passed" in lowered
    assert "hosted_sign_in_available" in lowered
    assert lowered.index("-runtimepreflightonly") < lowered.index('read-host "account a password" -assecurestring')
    assert "addhours(-24)" in lowered
    assert "resumed_from_verified_rls" in lowered
    assert "expectedevidenceversion" in lowered
    assert "notbeforeutc" in lowered
    assert "evidence_freshness_verified" in lowered
    assert '"phase6o.hosted.rls.v1"' in lowered
    assert '"phase6p.hosted.rls.v1"' in lowered
    assert '"phase6p.product.recovery.v1"' in lowered
    assert "-accountapassword $accountapassword" in lowered
    assert "-accountbpassword $accountbpassword" in lowered
    assert "start-process" not in lowered
    assert "convertfrom-securepassword" not in lowered
    assert "service_role" not in lowered
    assert "[security.securestring]$accountapassword" in phase6o
    assert "[security.securestring]$accountbpassword" in phase6o
    product_recovery = (root / "scripts/test-phase6p-product-recovery.ps1").read_text(encoding="utf-8").lower()
    assert product_recovery.index("if ($runtimepreflightonly)") < product_recovery.index(
        'read-host "account a password" -assecurestring'
    )
    assert USER_A.lower() not in lowered
    assert TENANT_A.lower() not in lowered


def test_phase6p_same_origin_proxy_allowlists_only_explicit_account_continuity_routes():
    root = Path(__file__).resolve().parents[1]
    proxy = (root / "apps/web/src/app/api/account/[...path]/route.ts").read_text(encoding="utf-8")

    for marker in (
        '"hosted-session"',
        '"continuity"',
        '"continuity/replay"',
        '"continuity/resolve"',
        '"continuity/export"',
        '"continuity/import"',
        "sameOrigin(request)",
        "MAX_BODY_BYTES",
        "MAX_BACKUP_BODY_BYTES",
    ):
        assert marker in proxy
    assert "GLOBAL_TERMINAL_API_BASE_URL" in proxy


class FakeDocumentRepository:
    def __init__(self):
        self.documents: dict[str, dict[str, Any]] = {}
        self.receipts: dict[tuple[str, str], dict[str, Any]] = {}
        self.available = True
        self.save_calls = 0

    def load(self, context: dict[str, Any]) -> dict[str, Any] | None:
        from lib.supabase_account_runtime import SupabaseRepositoryUnavailable

        if not self.available:
            raise SupabaseRepositoryUnavailable("offline")
        value = self.documents.get(str(context["tenant_id"]))
        return json.loads(json.dumps(value)) if value else None

    def save(
        self,
        context: dict[str, Any],
        bundle: dict[str, Any],
        *,
        expected_version: int,
        idempotency_key: str,
    ) -> dict[str, Any]:
        from lib.supabase_account_runtime import SupabaseRepositoryConflict, SupabaseRepositoryUnavailable

        if not self.available:
            raise SupabaseRepositoryUnavailable("offline")
        tenant_id = str(context["tenant_id"])
        receipt_key = (tenant_id, idempotency_key)
        if receipt_key in self.receipts:
            return {**self.receipts[receipt_key], "status": "deduped"}
        current = self.documents.get(tenant_id)
        current_version = int((current or {}).get("version") or 0)
        if current_version != expected_version:
            raise SupabaseRepositoryConflict(current_version)
        self.save_calls += 1
        version = current_version + 1
        self.documents[tenant_id] = {
            "payload": json.loads(json.dumps(bundle)),
            "fingerprint": bundle["fingerprint"],
            "version": version,
        }
        result = {"status": "applied", "version": version, "fingerprint": bundle["fingerprint"]}
        self.receipts[receipt_key] = dict(result)
        return result

    def delete(self, context: dict[str, Any], *, expected_version: int, idempotency_key: str) -> dict[str, Any]:
        del idempotency_key
        tenant_id = str(context["tenant_id"])
        current = self.documents.get(tenant_id)
        if int((current or {}).get("version") or 0) != expected_version:
            from lib.supabase_account_runtime import SupabaseRepositoryConflict

            raise SupabaseRepositoryConflict(int((current or {}).get("version") or 0))
        self.documents.pop(tenant_id, None)
        return {"status": "deleted", "version": expected_version + 1}

    def health(self) -> dict[str, Any]:
        return {
            "configured": True,
            "contacted": True,
            "authenticated": True,
            "hosted_verified": self.available,
            "source_status": "hosted-ready" if self.available else "unavailable",
            "provider_call_count": 0,
        }


def _seed_phase6p_watchlist(db_path: Path, *, version: int = 1, name: str = "Daily Radar") -> None:
    from lib.research_workspace_db import execute_query

    now = "2026-07-15T08:00:00+00:00"
    execute_query(
        """
        INSERT INTO tenant_watchlists (
          resource_id, tenant_id, owner_user_id, name, source_key,
          source_fingerprint, version, active, created_at, updated_at
        ) VALUES (?, ?, ?, ?, 'phase6p:primary', 'fingerprint', ?, 1, ?, ?)
        """,
        ("twl_phase6p", TENANT_A, USER_A, name, version, now, now),
        db_path=db_path,
    )


def test_phase6p_continuity_new_session_restore_outage_replay_and_conflict(tmp_path: Path):
    from lib.account_continuity import AccountContinuityCoordinator
    from lib.research_workspace_db import execute_query

    repository = FakeDocumentRepository()
    first_db = tmp_path / "first.db"
    _seed_phase6p_watchlist(first_db)
    first = AccountContinuityCoordinator(first_db, repository=repository, enabled=True)

    assert first.restore(hosted_context())["status"] == "hosted-ready"
    saved = first.sync(hosted_context(), idempotency_key="phase6p-first-save")
    assert saved["status"] == "applied"
    assert saved["remote_version"] == 1
    assert repository.save_calls == 1

    second_db = tmp_path / "second.db"
    second = AccountContinuityCoordinator(second_db, repository=repository, enabled=True)
    restored = second.restore(hosted_context())
    assert restored["status"] == "hosted-ready"
    row = execute_query(
        "SELECT name, tenant_id, owner_user_id FROM tenant_watchlists WHERE resource_id='twl_phase6p'",
        fetch=True,
        one=True,
        db_path=second_db,
    )
    assert row == {"name": "Daily Radar", "tenant_id": TENANT_A, "owner_user_id": USER_A}

    execute_query(
        "UPDATE tenant_watchlists SET name='Offline Radar', version=2 WHERE tenant_id=? AND resource_id='twl_phase6p'",
        (TENANT_A,),
        db_path=second_db,
    )
    repository.available = False
    queued = second.sync(hosted_context(), idempotency_key="phase6p-offline-save")
    assert queued["status"] == "pending"
    assert second.status(hosted_context())["state"] == "offline-read-only"
    assert second.status(hosted_context())["pending_count"] == 1

    repository.available = True
    replayed = second.replay(hosted_context())
    assert replayed["status"] == "recovered"
    assert replayed["applied_count"] == 1
    assert replayed["pending_count"] == 0
    assert repository.save_calls == 2
    repeated = second.replay(hosted_context())
    assert repeated["status"] == "no-due-work"
    assert repository.save_calls == 2

    remote = repository.documents[TENANT_A]
    remote["version"] += 1
    execute_query(
        "UPDATE tenant_watchlists SET name='Local divergence', version=3 WHERE tenant_id=? AND resource_id='twl_phase6p'",
        (TENANT_A,),
        db_path=second_db,
    )
    conflict = second.sync(hosted_context(), idempotency_key="phase6p-conflict-save")
    assert conflict["status"] == "conflict"
    assert second.status(hosted_context())["conflict_count"] == 1
    assert repository.documents[TENANT_A]["payload"]["tables"]["tenant_watchlists"][0]["name"] == "Offline Radar"

    audit_count = execute_query(
        "SELECT COUNT(*) AS count FROM tenant_account_continuity_audit WHERE tenant_id=?",
        (TENANT_A,),
        fetch=True,
        one=True,
        db_path=second_db,
    )
    assert int(audit_count["count"]) >= 3


def test_phase6p_replay_advances_remote_version_across_multiple_offline_mutations(tmp_path: Path):
    from lib.account_continuity import AccountContinuityCoordinator
    from lib.research_workspace_db import execute_query

    repository = FakeDocumentRepository()
    db_path = tmp_path / "multi-replay.db"
    _seed_phase6p_watchlist(db_path)
    coordinator = AccountContinuityCoordinator(db_path, repository=repository, enabled=True)
    assert coordinator.restore(hosted_context())["status"] == "hosted-ready"
    assert coordinator.sync(hosted_context(), idempotency_key="phase6p-seed-remote")["remote_version"] == 1

    repository.available = False
    execute_query(
        "UPDATE tenant_watchlists SET name='Offline first', version=2 WHERE tenant_id=?",
        (TENANT_A,),
        db_path=db_path,
    )
    assert coordinator.sync(hosted_context(), idempotency_key="phase6p-offline-first")["status"] == "pending"
    execute_query(
        "UPDATE tenant_watchlists SET name='Offline latest', version=3 WHERE tenant_id=?",
        (TENANT_A,),
        db_path=db_path,
    )
    assert coordinator.sync(hosted_context(), idempotency_key="phase6p-offline-latest")["status"] == "pending"

    repository.available = True
    replayed = coordinator.replay(hosted_context())
    assert replayed["status"] == "recovered"
    assert replayed["applied_count"] == 2
    assert replayed["pending_count"] == 0
    assert replayed["conflict_count"] == 0
    assert repository.documents[TENANT_A]["version"] == 3
    assert repository.documents[TENANT_A]["payload"]["tables"]["tenant_watchlists"][0]["name"] == "Offline latest"


def test_phase6p_backup_export_import_restores_only_current_server_tenant(tmp_path: Path):
    from lib.account_continuity import AccountBundleStore, AccountContinuityCoordinator
    from lib.research_workspace_db import execute_query

    source_db = tmp_path / "backup-source.db"
    _seed_phase6p_watchlist(source_db, name="Backup Radar")
    exported = AccountBundleStore(source_db).capture(hosted_context())

    target_db = tmp_path / "backup-target.db"
    repository = FakeDocumentRepository()
    coordinator = AccountContinuityCoordinator(target_db, repository=repository, enabled=True)
    restored = coordinator.import_backup(
        hosted_context(),
        exported,
        strategy="replace",
        idempotency_key="phase6p-backup-import-001",
    )
    assert restored["status"] == "applied"
    row = execute_query(
        "SELECT tenant_id, owner_user_id, name FROM tenant_watchlists WHERE resource_id='twl_phase6p'",
        fetch=True,
        one=True,
        db_path=target_db,
    )
    assert row == {"tenant_id": TENANT_A, "owner_user_id": USER_A, "name": "Backup Radar"}
    assert repository.documents[TENANT_A]["payload"]["tables"]["tenant_watchlists"][0]["name"] == "Backup Radar"
