from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_goal10b_runtime_does_not_import_external_source_trees():
    for path in list((ROOT / "lib").glob("*.py")) + list((ROOT / "pages").glob("*.py")) + [ROOT / "app.py"]:
        text = path.read_text(encoding="utf-8")
        assert "external.worldmonitor" not in text
        assert "external.openbb" not in text.lower()
        assert "finvizfinance" not in text.lower()
