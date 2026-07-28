from __future__ import annotations

import zipfile

from scripts.build_release_zip import ROOT, build_release


def test_release_archive_includes_gitignore_and_excludes_generated_artifacts():
    zip_path, manifest = build_release()
    with zipfile.ZipFile(zip_path) as archive:
        names = set(archive.namelist())

    required = {
        ".gitignore",
        "app.py",
        "requirements.txt",
        "requirements-openbb.txt",
        "pytest.ini",
        "lib/market_data.py",
        "lib/data_contracts.py",
        "lib/endpoint_catalog.py",
        "lib/provider_router.py",
        "lib/schema_normalizer.py",
        "lib/data_router.py",
        "lib/unified_data_layer.py",
        "lib/openbb_bridge.py",
        "lib/openbb_endpoint_resolver.py",
        "lib/openbb_real_probe.py",
        "lib/openbb_capability_runtime.py",
        "lib/openbb_factor_backend.py",
        "lib/portfolio_factor_router.py",
        "lib/mcp_context_router.py",
        "pages/16_Portfolio_Quant_Lab.py",
        "pages/18_OpenBB_Data_Hub.py",
        "pages/17_Data_Provider_Center.py",
        "scripts/run_smoke_tests.py",
        "docs/GOAL_9_PRE_FLIGHT_REPORT.md",
        "docs/GOAL_9_FINAL_REPORT.md",
        "docs/INTERNAL_UNIFIED_DATA_LAYER.md",
        "docs/OPENBB_ENDPOINT_RESOLVER.md",
        "docs/PORTFOLIO_FACTOR_BACKEND.md",
    }
    assert required.issubset(names)
    assert not any(name.startswith("external/") for name in names)
    forbidden_tokens = ["OpenBB-develop", "worldmonitor-main", "OpenStock", "OpenAlice", "FinceptTerminal", "finvizfinance", "bloomberg-terminal", "BB-Terminal", "quant-traderr"]
    assert not any(any(token in name for token in forbidden_tokens) for name in names)
    assert not any(name.startswith("data/cache/") or name.startswith("data/private/") for name in names)
    assert not any("__pycache__" in name or name.endswith(".pyc") or name.endswith(".pyo") or name.endswith(".log") for name in names)
    assert ".env" not in names
    assert ".streamlit/secrets.toml" not in names
    assert (ROOT / ".gitignore").exists()
    assert ".gitignore" in manifest["files"]
