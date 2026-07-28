from __future__ import annotations

from scripts import build_release_zip


def test_phase5n_release_includes_product_depth_and_excludes_runtime_or_external_state():
    names = {path.relative_to(build_release_zip.ROOT).as_posix() for path in build_release_zip.iter_release_files()}

    for required in [
        "lib/symbol_intelligence.py",
        "tests/test_phase5n_symbol_intelligence.py",
        "apps/web/scripts/capture-phase5n.mjs",
        "docs/PHASE_5N_PRODUCT_AND_QUANT_CONTRACT.md",
        "docs/PHASE_5N_API_PROVIDER_CONTRACT.md",
    ]:
        assert required in names

    assert ".env" not in names
    assert not any(name.startswith("external (2)/") for name in names)
    assert not any(name.startswith("data/cache/") for name in names)
    assert not any(name.startswith("review_workspace/") for name in names)
    assert not any(name.startswith("apps/web/.next/") for name in names)
    assert not any(name.startswith("apps/web/node_modules/") for name in names)
