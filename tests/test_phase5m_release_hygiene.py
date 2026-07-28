from __future__ import annotations

from scripts import build_release_zip


def test_phase5m_release_includes_symbol_product_and_excludes_external_private_state():
    names = {path.relative_to(build_release_zip.ROOT).as_posix() for path in build_release_zip.iter_release_files()}

    for required in [
        "lib/symbol_workstation.py",
        "apps/web/src/components/SymbolSearch.tsx",
        "apps/web/src/components/SymbolWorkstation.tsx",
        "static/api-fixtures/symbol-directory.json",
        "static/api-fixtures/symbol-workstation.json",
        "docs/PHASE_5M_FINAL_REPORT.md",
    ]:
        assert required in names

    assert not any(name.startswith("external (2)/") for name in names)
    assert not any(name.startswith("data/private/") for name in names)
    assert ".env" not in names
    assert not any(name.endswith((".sqlite", ".sqlite3", ".db")) for name in names)

