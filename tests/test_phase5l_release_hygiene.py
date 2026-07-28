from __future__ import annotations

from scripts import build_release_zip


REQUIRED_PHASE5L_FILES = {
    "lib/research_memory.py",
    "apps/web/src/components/ResearchMemoryWorkstation.tsx",
    "apps/web/scripts/capture-phase5l.mjs",
    "static/api-fixtures/research-memory.json",
    "docs/PHASE_5L_FINAL_REPORT.md",
    "docs/PHASE_5L_PRODUCT_AND_PRIVACY_CONTRACT.md",
    "docs/NEXT_ROADMAP_EXECUTION_PROMPT.md",
}


def test_phase5l_release_selection_includes_product_and_excludes_private_memory():
    names = {path.relative_to(build_release_zip.ROOT).as_posix() for path in build_release_zip.iter_release_files()}
    assert REQUIRED_PHASE5L_FILES <= names
    assert not any(name.startswith("data/private/") for name in names)
    assert not any(name.endswith((".db", ".sqlite", ".sqlite3")) for name in names)
    assert not any("phase5l_visual" in name for name in names)
    assert ".env" not in names

