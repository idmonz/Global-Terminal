from __future__ import annotations

import hashlib
import json
import os
from copy import deepcopy
from typing import Any, Protocol, runtime_checkable

from .identity_tenancy import _require_authenticated, public_account_payload


TENANT_RESEARCH_SYNC_VERSION = "tenant_research_sync.v1"
MAX_SYNC_RESOURCES = 25
MAX_SYNC_BYTES = 30_000
_PUBLIC_EXCLUSION_CATEGORIES = ["credentials", "identity", "local-paths", "private-notes"]

_PRIVATE_SYNC_FIELDS = {
    "access_token",
    "authorization",
    "cookie",
    "csrf_token",
    "db_path",
    "metadata_json",
    "owner_user_id",
    "password",
    "private_body",
    "private_note",
    "private_path",
    "refresh_token",
    "review_notes",
    "service_role_key",
    "supabase_anon_key",
    "supabase_publishable_key",
    "supabase_secret_key",
    "session_token",
    "tenant_id",
    "user_id",
    "watch_reason",
}


class HostedPersistenceUnavailable(RuntimeError):
    pass


def _is_private_key(key: Any) -> bool:
    normalized = str(key or "").strip().lower()
    return (
        normalized in _PRIVATE_SYNC_FIELDS
        or normalized.startswith("private_")
        or normalized.endswith("_secret")
        or normalized.endswith("_token")
        or normalized.endswith("_path")
    )


def sanitize_sync_value(value: Any, *, depth: int = 0) -> Any:
    if depth > 8:
        return "[depth-limited]"
    if isinstance(value, dict):
        return {
            str(key): sanitize_sync_value(item, depth=depth + 1)
            for key, item in value.items()
            if not _is_private_key(key)
        }
    if isinstance(value, (list, tuple)):
        return [sanitize_sync_value(item, depth=depth + 1) for item in list(value)[:MAX_SYNC_RESOURCES]]
    if isinstance(value, str):
        return value[:2_000]
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return str(value)[:2_000]


def _fingerprint(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _resource(
    resource_type: str,
    resource_id: Any,
    version: Any,
    payload: dict[str, Any],
    *,
    deleted: bool = False,
) -> dict[str, Any] | None:
    normalized_id = str(resource_id or "").strip()
    if not normalized_id:
        return None
    sanitized = sanitize_sync_value(payload)
    row = {
        "resource_type": str(resource_type or "record")[:40],
        "resource_id": normalized_id[:80],
        "version": max(1, int(version or 1)),
        "deleted": bool(deleted),
        "payload": sanitized,
    }
    row["fingerprint"] = _fingerprint({key: value for key, value in row.items() if key != "fingerprint"})
    return row


def _snapshot_from_resources(resources: list[dict[str, Any]], *, excluded_count: int = 0) -> dict[str, Any]:
    accepted: list[dict[str, Any]] = []
    for row in sorted(resources, key=lambda item: (str(item.get("resource_type")), str(item.get("resource_id")))):
        if len(accepted) >= MAX_SYNC_RESOURCES:
            excluded_count += 1
            continue
        candidate = {
            "snapshot_version": TENANT_RESEARCH_SYNC_VERSION,
            "resources": [*accepted, row],
            "resource_count": len(accepted) + 1,
            "excluded_resource_count": excluded_count,
            "provider_call_count": 0,
            "excluded_fields": _PUBLIC_EXCLUSION_CATEGORIES,
            "bounded": True,
        }
        candidate_bytes = len(json.dumps(candidate, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8"))
        if candidate_bytes > MAX_SYNC_BYTES:
            excluded_count += 1
            continue
        accepted.append(row)
    output = {
        "snapshot_version": TENANT_RESEARCH_SYNC_VERSION,
        "resources": accepted,
        "resource_count": len(accepted),
        "excluded_resource_count": excluded_count,
        "provider_call_count": 0,
        "excluded_fields": _PUBLIC_EXCLUSION_CATEGORIES,
        "bounded": True,
    }
    output["snapshot_fingerprint"] = _fingerprint(output["resources"])
    output["payload_bytes"] = len(json.dumps(output, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    while output["payload_bytes"] > MAX_SYNC_BYTES and output["resources"]:
        output["resources"].pop()
        output["resource_count"] = len(output["resources"])
        output["excluded_resource_count"] += 1
        output["snapshot_fingerprint"] = _fingerprint(output["resources"])
        output["payload_bytes"] = len(json.dumps(output, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    return output


def build_sync_snapshot(account_export: dict[str, Any]) -> dict[str, Any]:
    sanitized_export = sanitize_sync_value(account_export)
    resources: list[dict[str, Any]] = []
    for watchlist in sanitized_export.get("watchlists") or []:
        if not isinstance(watchlist, dict):
            continue
        parent = _resource(
            "watchlist",
            watchlist.get("resource_id"),
            watchlist.get("version"),
            {key: value for key, value in watchlist.items() if key != "items"},
        )
        if parent:
            resources.append(parent)
        for item in watchlist.get("items") or []:
            if not isinstance(item, dict):
                continue
            child = _resource(
                "watchlist-item",
                item.get("resource_id"),
                item.get("version"),
                {**item, "watchlist_resource_id": watchlist.get("resource_id")},
            )
            if child:
                resources.append(child)
    for rule in sanitized_export.get("rules") or []:
        if isinstance(rule, dict):
            row = _resource("rule", rule.get("resource_id"), rule.get("version"), rule)
            if row:
                resources.append(row)
    for inbox in sanitized_export.get("inbox") or []:
        if isinstance(inbox, dict):
            row = _resource("inbox", inbox.get("resource_id"), inbox.get("version"), inbox)
            if row:
                resources.append(row)
    for receipt in sanitized_export.get("consent_receipts") or []:
        if isinstance(receipt, dict):
            row = _resource("consent-receipt", receipt.get("receipt_id"), 1, receipt)
            if row:
                resources.append(row)
    return _snapshot_from_resources(resources)


def normalize_sync_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for raw in (snapshot or {}).get("resources") or []:
        if not isinstance(raw, dict):
            continue
        row = _resource(
            str(raw.get("resource_type") or "record"),
            raw.get("resource_id"),
            raw.get("version"),
            raw.get("payload") if isinstance(raw.get("payload"), dict) else {},
            deleted=bool(raw.get("deleted")),
        )
        if row:
            rows.append(row)
    return _snapshot_from_resources(rows, excluded_count=max(0, int((snapshot or {}).get("excluded_resource_count") or 0)))


@runtime_checkable
class TenantResearchPersistence(Protocol):
    def health(self) -> dict[str, Any]: ...

    def snapshot(self, context: dict[str, Any]) -> dict[str, Any]: ...

    def apply_snapshot(
        self,
        context: dict[str, Any],
        snapshot: dict[str, Any],
        *,
        idempotency_key: str,
    ) -> dict[str, Any]: ...


@runtime_checkable
class TenantResearchRepository(Protocol):
    """Phase 6K account contract boundary, independent of storage provider."""

    def summary(self, context: dict[str, Any]) -> dict[str, Any]: ...

    def preview_import(self, context: dict[str, Any], *, source_list_id: str = "primary", limit: int = 25) -> dict[str, Any]: ...

    def confirm_import(self, context: dict[str, Any], body: Any) -> dict[str, Any]: ...

    def cancel_import(self, context: dict[str, Any], *, preview_id: str) -> dict[str, Any]: ...

    def get_watchlist(self, context: dict[str, Any], resource_id: str) -> dict[str, Any] | None: ...

    def list_watchlists(self, context: dict[str, Any]) -> list[dict[str, Any]]: ...

    def delete_watchlist(self, context: dict[str, Any], resource_id: str, *, expected_version: int) -> bool: ...

    def configure_rule(self, context: dict[str, Any], watchlist_id: str, **kwargs: Any) -> dict[str, Any]: ...

    def scan_inbox(self, context: dict[str, Any], watchlist_id: str, **kwargs: Any) -> dict[str, Any]: ...

    def list_inbox(self, context: dict[str, Any], **kwargs: Any) -> list[dict[str, Any]]: ...

    def get_inbox_item(self, context: dict[str, Any], resource_id: str) -> dict[str, Any] | None: ...

    def update_inbox_state(self, context: dict[str, Any], resource_id: str, **kwargs: Any) -> dict[str, Any]: ...

    def export(self, context: dict[str, Any]) -> dict[str, Any]: ...

    def build_contract(self, context: dict[str, Any]) -> dict[str, Any]: ...


class SQLiteTenantResearchPersistence:
    def __init__(self, store: Any):
        self.store = store

    def health(self) -> dict[str, Any]:
        return {
            "adapter": "sqlite-tenant-research",
            "available": True,
            "hosted": False,
            "hosted_verified": False,
            "source_status": "local-private",
            "provider_call_count": 0,
        }

    def snapshot(self, context: dict[str, Any]) -> dict[str, Any]:
        _require_authenticated(context)
        return build_sync_snapshot(self.store.export(context))

    def apply_snapshot(
        self,
        context: dict[str, Any],
        snapshot: dict[str, Any],
        *,
        idempotency_key: str,
    ) -> dict[str, Any]:
        del snapshot, idempotency_key
        _require_authenticated(context)
        raise HostedPersistenceUnavailable("SQLite account research remains the local source of truth in Phase 6L.")


class DeterministicFakeTenantResearchPersistence:
    """Contract fake for conformance, outage, retry, and conflict tests only."""

    def __init__(self, *, available: bool = True):
        self.available = bool(available)
        self._snapshots: dict[str, dict[str, Any]] = {}
        self._receipts: dict[tuple[str, str], dict[str, Any]] = {}

    def _tenant(self, context: dict[str, Any]) -> str:
        tenant_id, _ = _require_authenticated(context)
        return tenant_id

    def health(self) -> dict[str, Any]:
        return {
            "adapter": "deterministic-fake",
            "available": self.available,
            "hosted": True,
            "hosted_verified": self.available,
            "source_status": "test-ready" if self.available else "unavailable",
            "provider_call_count": 0,
        }

    def seed(self, context: dict[str, Any], snapshot: dict[str, Any]) -> None:
        self._snapshots[self._tenant(context)] = normalize_sync_snapshot(snapshot)

    def snapshot(self, context: dict[str, Any]) -> dict[str, Any]:
        tenant_id = self._tenant(context)
        if not self.available:
            raise HostedPersistenceUnavailable("Deterministic hosted transport is offline.")
        return deepcopy(self._snapshots.get(tenant_id) or _snapshot_from_resources([]))

    def apply_snapshot(
        self,
        context: dict[str, Any],
        snapshot: dict[str, Any],
        *,
        idempotency_key: str,
    ) -> dict[str, Any]:
        tenant_id = self._tenant(context)
        if not self.available:
            raise HostedPersistenceUnavailable("Deterministic hosted transport is offline.")
        receipt_key = (tenant_id, str(idempotency_key))
        if receipt_key in self._receipts:
            return {**deepcopy(self._receipts[receipt_key]), "status": "deduped"}
        from .tenant_research_sync import build_reconciliation_plan

        local = normalize_sync_snapshot(snapshot)
        remote = self._snapshots.get(tenant_id) or _snapshot_from_resources([])
        plan = build_reconciliation_plan(local, remote)
        if plan["counts"].get("conflict") or plan["counts"].get("remote-newer") or plan["counts"].get("deletion"):
            result = {
                "status": "conflict",
                "plan": plan,
                "remote_revision": remote.get("snapshot_fingerprint"),
                "provider_call_count": 0,
            }
            self._receipts[receipt_key] = deepcopy(result)
            return result
        self._snapshots[tenant_id] = local
        result = {
            "status": "applied",
            "remote_revision": local.get("snapshot_fingerprint"),
            "resource_count": local.get("resource_count"),
            "provider_call_count": 0,
        }
        self._receipts[receipt_key] = deepcopy(result)
        return result


class SupabaseTenantResearchPersistence:
    """Optional hosted boundary; unavailable until live auth/RLS conformance passes."""

    def health(self) -> dict[str, Any]:
        configured = bool(
            os.getenv("SUPABASE_URL", "").strip()
            and (
                os.getenv("SUPABASE_PUBLISHABLE_KEY", "").strip()
                or os.getenv("SUPABASE_ANON_KEY", "").strip()
            )
        )
        return {
            "adapter": "supabase-tenant-research",
            "available": False,
            "configured": configured,
            "contacted": False,
            "hosted": True,
            "hosted_verified": False,
            "source_status": "configured-unverified" if configured else "missing-key",
            "hosted_persistence": "unavailable",
            "provider_call_count": 0,
            "caveat": "Configuration presence is not auth, RLS, recovery, or tenant-isolation proof.",
        }

    def snapshot(self, context: dict[str, Any]) -> dict[str, Any]:
        _require_authenticated(context)
        raise HostedPersistenceUnavailable("Supabase tenant research has not passed live conformance.")

    def apply_snapshot(
        self,
        context: dict[str, Any],
        snapshot: dict[str, Any],
        *,
        idempotency_key: str,
    ) -> dict[str, Any]:
        del snapshot, idempotency_key
        _require_authenticated(context)
        raise HostedPersistenceUnavailable("Supabase tenant research has not passed live conformance.")
