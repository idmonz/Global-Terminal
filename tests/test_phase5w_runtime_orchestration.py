from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from backend.api import app as backend_app
from lib.api_contracts import (
    build_api_route_manifest_payload,
    build_api_runtime_health_payload,
    validate_api_payload,
)


ROOT = Path(__file__).resolve().parents[1]


def _assert_valid(payload: dict) -> None:
    valid, issues = validate_api_payload(payload)
    assert valid, issues
    json.dumps(payload)


def test_runtime_health_contract_is_json_safe_and_non_advisory() -> None:
    payload = build_api_runtime_health_payload(fastapi_available=True)

    _assert_valid(payload)
    encoded = json.dumps(payload)
    assert payload["payload_type"] == "runtime_health"
    assert payload["summary"]["fastapi_available"] is True
    assert payload["summary"]["fixture_fallback_required_when_api_unreachable"] is True
    assert payload["summary"]["broker_execution_added"] is False
    assert payload["summary"]["hosted_persistence_added"] is False
    assert "api_key" not in encoded.lower()
    assert "secret" not in encoded.lower() or "secrets_in_output" in encoded
    assert any(row["component"] == "fastapi_runtime" for row in payload["data"]["components"])


def test_manifest_and_backend_expose_runtime_health_route() -> None:
    manifest = build_api_route_manifest_payload(fastapi_available=True)
    backend_payload = backend_app.get_runtime_health_payload()

    _assert_valid(manifest)
    _assert_valid(backend_payload)
    routes = {row["path"] for row in manifest["data"]}
    assert "/api/runtime-health" in routes
    assert backend_payload["payload_type"] == "runtime_health"


def test_local_product_launcher_dry_run_is_safe_and_actionable() -> None:
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "start_local_product.py"), "--dry-run"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)

    assert payload["dry_run"] is True
    assert payload["secrets_printed"] is False
    assert payload["api_url"] == "http://127.0.0.1:8000"
    assert payload["web_url"] == "http://127.0.0.1:3000"
    assert "backend.api.app:app" in payload["api_command"]
    assert "NEXT_PUBLIC_GLOBAL_TERMINAL_API_BASE_URL" in payload["env_overrides"]
    assert "AIza" not in completed.stdout
    assert "sk-" not in completed.stdout


def test_next_shell_surfaces_runtime_health_state() -> None:
    page = (ROOT / "apps" / "web" / "src" / "app" / "page.tsx").read_text(encoding="utf-8")
    fixtures = (ROOT / "apps" / "web" / "src" / "lib" / "fixtures.ts").read_text(encoding="utf-8")
    css = (ROOT / "apps" / "web" / "src" / "app" / "globals.css").read_text(encoding="utf-8")

    assert "loadRuntimeHealth" in fixtures
    assert "RuntimeHealthSnapshot" in fixtures
    assert "RuntimeHealthChip" in page
    assert "data-runtime-health-state" in page
    assert "runtimeHealth={runtimeHealth}" in page
    assert ".runtime-health-chip" in css
