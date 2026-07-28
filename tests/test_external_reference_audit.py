from __future__ import annotations

import json
import zipfile
from pathlib import Path

from scripts.audit_external_references import build_external_audit
from scripts.audit_phase5f_external import build_inventory


def _write_zip(path: Path, files: dict[str, str | bytes]) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            zf.writestr(name, content)


def test_external_audit_outputs_inventory_license_and_line_artifacts(tmp_path):
    external_dir = tmp_path / "external"
    output_dir = tmp_path / "phase2e"
    external_dir.mkdir()
    _write_zip(
        external_dir / "sample-main.zip",
        {
            "sample-main/LICENSE": "MIT License\n\nCopyright test\n",
            "sample-main/README.md": "# Sample\n\nLicense: MIT\n",
            "sample-main/src/model.py": "def hello():\n    return 'world'\n",
            "sample-main/assets/logo.png": b"\x89PNG\r\n",
        },
    )

    payloads = build_external_audit(external_dir, output_dir=output_dir, generated_at="2026-06-16T00:00:00+00:00")

    assert set(payloads) == {
        "external_zip_inventory.json",
        "external_license_matrix.json",
        "external_feature_candidates.json",
        "external_line_inventory.json",
    }
    assert {path.name for path in output_dir.glob("*.json")} == set(payloads)

    inventory = payloads["external_zip_inventory.json"]
    license_matrix = payloads["external_license_matrix.json"]
    line_inventory = payloads["external_line_inventory.json"]
    encoded = json.dumps(payloads, sort_keys=True)

    assert inventory["archive_count"] == 1
    assert inventory["archives"][0]["archive"] == "sample-main.zip"
    assert any(row["path"] == "sample-main/src/model.py" for row in inventory["archives"][0]["files"])
    assert license_matrix["archives"][0]["detected_license"] == "MIT"
    assert license_matrix["archives"][0]["license_stance"] == "direct-use-allowed"
    assert line_inventory["archives"][0]["total_indexed_lines"] >= 3
    assert str(tmp_path) not in encoded


def test_financedatabase_named_archive_gets_asset_universe_candidate(tmp_path):
    external_dir = tmp_path / "external"
    external_dir.mkdir()
    _write_zip(
        external_dir / "FinanceDatabase-main.zip",
        {
            "FinanceDatabase-main/LICENSE": "MIT License\n\nCopyright test\n",
            "FinanceDatabase-main/pyproject.toml": (
                "[project]\n"
                'name = "financedatabase"\n'
                'description = "This is a database of 300.000+ symbols containing Equities, ETFs, Funds, Indices, Currencies, Cryptocurrencies and Money Markets."\n'
                'license = {text = "MIT"}\n'
            ),
            "FinanceDatabase-main/database/equities/NMS.csv": (
                "symbol,name,summary,currency,sector,industry_group,industry,exchange,mic,market,country\n"
                "AAA,Example Inc,,USD,Technology,Software,Software,NMS,XNAS,NASDAQ,United States\n"
            ),
            "FinanceDatabase-main/database/cryptos.csv": "symbol,name,cryptocurrency,currency,summary,exchange\nBTC-USD,Bitcoin USD,BTC,USD,,CCC\n",
            "FinanceDatabase-main/database/currencies.csv": "symbol,name,base_currency,quote_currency,summary,exchange\nEURUSD=X,EUR/USD,EUR,USD,,CCY\n",
            "FinanceDatabase-main/database/indices.csv": "symbol,name,currency,summary,category_group,category,exchange,mic\nSPYIDX,Example Index,USD,,Equities,Equities,NYQ,XNYS\n",
            "FinanceDatabase-main/database/moneymarkets.csv": "symbol,name,currency,summary,family,exchange\nAAAAX,Example MMF,USD,,Example,NAS\n",
        },
    )

    payloads = build_external_audit(external_dir, generated_at="2026-06-16T00:00:00+00:00")
    candidates = payloads["external_feature_candidates.json"]["candidates"]
    license_row = payloads["external_license_matrix.json"]["archives"][0]

    assert license_row["detected_license"] == "MIT"
    assert any(candidate["external_project"] == "FinanceDatabase" for candidate in candidates)
    assert any(
        candidate["local_implementation_target"].startswith("lib/asset_universe.py")
        and candidate["license_stance"] == "direct-use-allowed"
        for candidate in candidates
    )


def test_full_inventory_normalizes_external_directory_before_summary(tmp_path):
    external_dir = tmp_path / "external"
    external_dir.mkdir()
    _write_zip(
        external_dir / "sample-main.zip",
        {
            "sample-main/LICENSE": "MIT License\n",
            "sample-main/src/example.py": "value = 1\n",
        },
    )

    rows, summary = build_inventory(external_dir)

    assert summary["archive_count"] == 1
    assert summary["external_dir"] == "external"
    assert summary["totals"]["errors"] == 0
    assert any(row["path"] == "sample-main/src/example.py" for row in rows)
    assert str(tmp_path) not in json.dumps(summary, sort_keys=True)
