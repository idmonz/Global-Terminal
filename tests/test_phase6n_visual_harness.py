from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_SCREENSHOTS = (
    "observation-run-progress-desktop.png",
    "observation-run-completed-desktop.png",
    "observation-run-mobile-critical-first.png",
    "observation-run-mobile-critical-first-tall.png",
    "observation-run-runtime-offline.png",
    "attention-account-a-reviewed.png",
    "attention-account-b-isolated.png",
    "attention-version-conflict.png",
    "attention-account-offline-local-retained.png",
    "observation-run-drilldown-news.png",
    "observation-run-drilldown-brief.png",
    "observation-run-drilldown-map.png",
    "observation-run-drilldown-analyst.png",
)


def test_phase6n_visual_command_and_capture_harness_cover_run_truth_and_failures():
    package = (ROOT / "apps/web/package.json").read_text(encoding="utf-8")
    capture = (ROOT / "apps/web/scripts/capture-phase6n.mjs").read_text(encoding="utf-8")
    search = (ROOT / "apps/web/src/components/SymbolSearch.tsx").read_text(encoding="utf-8")
    css = (ROOT / "apps/web/src/app/globals.css").read_text(encoding="utf-8")

    assert '"visual:phase6n": "node scripts/capture-phase6n.mjs"' in package
    for marker in (
        "phase6n_visual",
        "observation-run-completed-desktop",
        "observation-run-mobile-critical-first",
        "observation-run-no-due-work",
        "observation-run-quota-blocked",
        "observation-run-partial-lkg",
        "observation-run-cancelled",
        "observation-run-provider-offline",
        "productNavWidth",
        "providerRequestCount",
        "horizontalOverflow",
        "captureAccountIsolationConflictAndOffline",
        "attention-account-a-reviewed",
        "attention-account-b-isolated",
        "attention-version-conflict",
        "attention-account-offline-local-retained",
        'for (const destination of ["News", "Brief", "Map", "Analyst"])',
        "focusVisible",
        "liveRegionCount",
        "assertCleanTelemetry",
        "assertControlledOfflineTelemetry",
        "assertControlledConflictTelemetry",
        "assertProductStyles",
        "route.fallback()",
        "httpFailures",
        "requestFailures",
        "cancelledRequests",
        "isExpectedNavigationCancellation",
        'url.searchParams.has("_rsc")',
        'url.hostname === "tile.openstreetmap.org"',
        "response.url()",
        "response.request().resourceType()",
        "maxTabStops",
        "report.passed = true",
    ):
        assert marker in capture
    assert "visual-harness-route-not-found" not in capture
    assert "serviceUnavailableResponse" in capture
    assert 'event.key === "Escape"' in search
    assert "event.currentTarget.contains(next)" in search
    assert '"identity title summary"' in css
    assert ".attention-row-clocks" in css and "grid-area: clocks" in css
    assert ".attention-since-strip > span { min-width: 3.85rem; }" in css


def test_phase6n_visual_handoff_is_exact_and_machine_verifiable():
    package = (ROOT / "apps/web/package.json").read_text(encoding="utf-8")
    verifier = (ROOT / "apps/web/scripts/verify-phase6n-visual-summary.mjs").read_text(encoding="utf-8")
    handoff = (ROOT / "scripts/run_phase6n_visual_handoff.ps1").read_text(encoding="utf-8")

    assert '"visual:verify:phase6n": "node scripts/verify-phase6n-visual-summary.mjs"' in package
    for marker in (
        "phase6n.visual.v1",
        "observation-run-mobile-critical-first",
        "observation-run-runtime-offline",
        "attention-account-b-isolated",
        "attention-version-conflict",
        "providerRequestCount",
        "firstRow",
        "focusVisible",
        "liveRegionCount",
    ):
        assert marker in verifier
    assert "npm --prefix apps/web run visual:phase6n" in handoff
    assert "npm --prefix apps/web run visual:verify:phase6n" in handoff
    assert "scripts/start_local_product.py --production" in handoff
    assert "Find-AvailablePort -Start 3167" in handoff
    assert "Find-AvailablePort -Start 8167" in handoff
    assert 'Where-Object { $_.status -eq "started"' in handoff
    assert "Stop-ProcessTree" in handoff
    assert '$env:GLOBAL_TERMINAL_LOCAL_AUTH_ENABLED = "true"' in handoff
    assert '$env:GLOBAL_TERMINAL_ACCOUNT_DB_PATH = $phase6nAccountDb' in handoff
    assert '$env:GLOBAL_TERMINAL_COOKIE_SECURE = "false"' in handoff
    assert "phase6n-account-$([guid]::NewGuid().ToString('N')).db" in handoff
    assert "Restore-ProcessEnvironmentVariable" in handoff


def test_phase6n_visual_summary_verifier_executes_and_rejects_provider_requests(tmp_path: Path):
    screenshots = []
    for name in REQUIRED_SCREENSHOTS:
        screenshot = tmp_path / name
        screenshot.write_bytes(b"phase6n-visual-proof" * 700)
        screenshots.append({"file": str(screenshot), "bytes": screenshot.stat().st_size})

    state_names = (
        "observation-run-no-due-work",
        "observation-run-quota-blocked",
        "observation-run-partial-lkg",
        "observation-run-cancelled",
        "observation-run-provider-offline",
        "observation-run-no-list",
    )
    report = {
        "evidence_version": "phase6n.visual.v1",
        "passed": True,
        "captures": {
            "journey": {"providerRequestCount": 0, "productNavWidth": 168, "focusVisible": True, "liveRegionCount": 1, "errors": []},
            "mobile": {"providerRequestCount": 0, "horizontalOverflow": False, "firstRow": {"top": 700}, "errors": []},
            "states": {name: {"providerRequestCount": 0, "errors": []} for name in state_names},
            "offline": {"providerRequestCount": 0, "errors": [], "expectedErrors": ["controlled 503"]},
            "drilldown": {"routes": ["News", "Brief", "Map", "Analyst"], "returned": True, "errors": []},
            "account": {"available": True, "isolated": True, "providerRequestCount": 0, "errors": [], "expectedErrors": ["controlled 409", "controlled 503"]},
            "regressions": {"screenshots": screenshots, "providerRequestCount": 0, "errors": []},
        },
    }
    summary = tmp_path / "summary.json"
    summary.write_text(json.dumps(report), encoding="utf-8")
    command = ["node", "apps/web/scripts/verify-phase6n-visual-summary.mjs", str(summary)]

    accepted = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    assert accepted.returncode == 0, accepted.stderr
    assert '"ok": true' in accepted.stdout

    report["captures"]["journey"]["providerRequestCount"] = 1
    summary.write_text(json.dumps(report), encoding="utf-8")
    rejected = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    assert rejected.returncode != 0
    assert "journey made a provider request" in rejected.stderr


def test_phase6n_isolated_web_origin_can_read_symbol_runtime_contracts():
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from backend.api.app import create_app

    client = TestClient(create_app())
    origin = "http://127.0.0.1:3167"
    paths = (
        "/api/symbol-workstation/AAPL/summary?asset_class=equity&runtime_mode=fixture",
        "/api/symbol-workstation/AAPL/panels/chart?asset_class=equity&runtime_mode=fixture",
    )
    for path in paths:
        response = client.get(path, headers={"Origin": origin})
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == origin
