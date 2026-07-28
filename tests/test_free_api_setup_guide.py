from __future__ import annotations

from lib.free_api_setup_guide import build_environment_setup_notes, build_free_api_key_checklist


def test_free_api_setup_guide_has_required_columns():
    rows = build_free_api_key_checklist()
    assert {"provider", "purpose", "env_var", "key_required", "no_key_fallback", "pages", "caveat"}.issubset(rows[0])
    assert any("python-dotenv" in note for note in build_environment_setup_notes())
