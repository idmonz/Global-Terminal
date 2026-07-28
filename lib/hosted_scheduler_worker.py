from __future__ import annotations

import hashlib
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .account_continuity import AccountBundleStore
from .supabase_account_runtime import SupabaseRepositoryConflict
from .supabase_hosted_scheduler import SupabaseHostedSchedulerServiceClient
from .tenant_research_desk import TenantResearchDeskStore
from .watchlist_alert_manager import WatchlistAlertManagerStore
from .watchlist_observation_runs import ObservationRunCoordinator, ObservationRunStore


HOSTED_SCHEDULER_WORKER_VERSION = "hosted_scheduler_worker.v1"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _correlation(value: Any) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()[:16]


def _record(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def execute_claim_with_existing_engines(
    claim: dict[str, Any],
    account_document: dict[str, Any],
    *,
    observation_adapter: Any | None = None,
) -> dict[str, Any]:
    """Restore one account bundle and reuse Phase 6N/6O engines once."""
    bundle = account_document.get("payload")
    if not isinstance(bundle, dict):
        raise ValueError("Hosted account bundle is unavailable.")
    context = {
        "authenticated": True,
        "identity_provider": "hosted-scheduler-service",
        "tenant_id": str(claim.get("tenant_id") or ""),
        "user_id": str(claim.get("owner_user_id") or ""),
        "role": "owner",
        "plan": "free",
    }
    bounds = _record(claim.get("bounds"))
    max_symbols = max(1, min(int(bounds.get("max_symbols") or 1), 5))
    provider_budget = max(0, min(int(bounds.get("max_provider_calls") or 0), 16))
    with tempfile.TemporaryDirectory(prefix="global-terminal-phase6q-") as temporary:
        db_path = Path(temporary) / "account.db"
        bundle_store = AccountBundleStore(db_path)
        bundle_store.restore(context, bundle, prefer_remote=True)
        research_store = TenantResearchDeskStore(account_db_path=db_path, local_db_path=db_path)
        observation_store = ObservationRunStore(db_path)
        coordinator = ObservationRunCoordinator(
            observation_store,
            lambda current_context, resource_id: research_store.get_watchlist(current_context, resource_id),
            adapter=observation_adapter,
            execute_inline=True,
        )
        idempotency = f"phase6q-observation-{_correlation(claim.get('scheduler_run_id'))}"
        observation = coordinator.submit(
            context,
            {
                "watchlist_id": str(claim.get("watchlist_id") or ""),
                "idempotency_key": idempotency,
                "interval": "1d",
                "range": "3mo",
                "max_symbols": max_symbols,
                "session_policy": "cache-only" if provider_budget < 4 else "market-aware",
            },
        )
        observation_run_id = str(observation.get("run_id") or "")
        snapshots = observation_store.list_snapshots(context, observation_run_id) if observation_run_id else []
        alert_store = WatchlistAlertManagerStore(db_path)
        evaluation = alert_store.evaluate_due(
            context,
            {
                "idempotency_key": f"phase6q-evaluation-{_correlation(claim.get('scheduler_run_id'))}",
                "mode": "worker",
            },
        )
        provider_calls = max(0, int(observation.get("provider_call_count") or 0))
        if provider_calls > provider_budget:
            raise ValueError("Hosted observation exceeded its claimed provider budget.")
        source = _record(snapshots[0]) if snapshots else {}
        observation_status = str(observation.get("status") or "failed")
        source_status = str(source.get("source_status") or "unavailable")
        if observation_status == "quota-blocked":
            final_status = "quota-blocked"
        elif observation_status in {"failed", "cancelled"}:
            final_status = observation_status
        elif not snapshots or source_status in {"unavailable", "provider-error", "malformed"}:
            final_status = "provider-unavailable"
        elif observation_status == "partial" or source_status in {"cached", "aging", "stale", "rate-limited"}:
            final_status = "partial"
        else:
            final_status = "completed"
        trigger_count = max(0, int(evaluation.get("triggered_count") or 0))
        clocks = _record(evaluation.get("source_clock"))
        completed_bundle = bundle_store.capture(context)
        return {
            "bundle": completed_bundle,
            "document_version": int(account_document.get("version") or 0),
            "result": {
                "status": final_status,
                "observation_run_id": observation_run_id,
                "evaluation_run_id": str(evaluation.get("run_id") or ""),
                "trigger_count": trigger_count,
                "provider_call_count": provider_calls,
                "provider": str(source.get("provider") or ""),
                "source_url": str(source.get("source_url") or ""),
                "source_status": source_status,
                "observed_at": source.get("observed_at") or clocks.get("observed_at"),
                "retrieved_at": source.get("retrieved_at") or clocks.get("retrieved_at"),
                "evaluated_at": evaluation.get("completed_at"),
                "triggered_at": evaluation.get("completed_at") if trigger_count else None,
                "caveat": str(source.get("caveat") or "Public/free-first data may be delayed and scheduled workflows may start late."),
                "data_gap": str(source.get("data_gap") or ("No validated source-backed snapshot was persisted." if not snapshots else "")),
                "duplicate_suppressed": bool(evaluation.get("deduped_count")),
            },
        }


def run_hosted_scheduler_once(
    service: SupabaseHostedSchedulerServiceClient | Any | None = None,
    *,
    worker_id: str = "github-actions-phase6q",
    executor: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]] = execute_claim_with_existing_engines,
    lease_seconds: int = 120,
) -> dict[str, Any]:
    client = service or SupabaseHostedSchedulerServiceClient()
    started = time.perf_counter()
    claim = client.claim(worker_id, lease_seconds=lease_seconds)
    if claim.get("claimed") is not True:
        return {
            "evidence_version": HOSTED_SCHEDULER_WORKER_VERSION,
            "status": str(claim.get("status") or "no-due"),
            "reason": str(claim.get("reason") or "no-work-claimed"),
            "claimed": False,
            "provider_call_count": 0,
            "duration_ms": round((time.perf_counter() - started) * 1_000),
            "completed_at": _utc(),
            "secrets_printed": False,
        }
    correlation_id = _correlation(claim.get("scheduler_run_id"))
    try:
        client.heartbeat(claim, lease_seconds=lease_seconds)
        account_document = client.load_account_document(claim)
        execution = executor(claim, account_document)
        result = _record(execution.get("result"))
        result["duration_ms"] = round((time.perf_counter() - started) * 1_000)
        persisted = client.persist_account_document(
            claim,
            _record(execution.get("bundle")),
            expected_version=int(execution.get("document_version") or 0),
        )
        if str(persisted.get("status") or "") not in {"applied", "deduped"}:
            raise SupabaseRepositoryConflict(int(persisted.get("current_version") or 0))
        finished = client.finish(claim, result)
        return {
            "evidence_version": HOSTED_SCHEDULER_WORKER_VERSION,
            "status": str(finished.get("status") or result.get("status") or "failed"),
            "claimed": True,
            "correlation_id": correlation_id,
            "provider_call_count": int(result.get("provider_call_count") or 0),
            "trigger_count": int(result.get("trigger_count") or 0),
            "source_status": str(result.get("source_status") or "unavailable"),
            "document_status": str(persisted.get("status") or "unavailable"),
            "idempotent_replay": bool(finished.get("idempotent_replay")),
            "duration_ms": int(result.get("duration_ms") or 0),
            "completed_at": _utc(),
            "secrets_printed": False,
        }
    except Exception as exc:
        error_code = "account-document-conflict" if isinstance(exc, SupabaseRepositoryConflict) else "scheduler-runtime-failed"
        failure = {
            "status": "failed",
            "provider_call_count": 0,
            "trigger_count": 0,
            "source_status": "unavailable",
            "error_code": error_code,
            "duration_ms": round((time.perf_counter() - started) * 1_000),
            "caveat": "The hosted run failed safely; no success or live-data claim was emitted.",
            "data_gap": "Last-known-good evidence remains available when previously persisted.",
        }
        finish_confirmed = False
        try:
            client.finish(claim, failure)
            finish_confirmed = True
        except Exception:
            finish_confirmed = False
        return {
            "evidence_version": HOSTED_SCHEDULER_WORKER_VERSION,
            "status": "failed",
            "claimed": True,
            "correlation_id": correlation_id,
            "error_code": error_code,
            "finish_confirmed": finish_confirmed,
            "provider_call_count": 0,
            "trigger_count": 0,
            "source_status": "unavailable",
            "duration_ms": failure["duration_ms"],
            "completed_at": _utc(),
            "secrets_printed": False,
        }
