from __future__ import annotations

from lib.openbb_ai_context_router import build_mcp_ready_openbb_endpoint_manifest, build_openbb_ai_context_bundle


def test_openbb_ai_context_bundle_includes_caveats_and_manifest():
    bundle = build_openbb_ai_context_bundle(screener={"rows": [], "data_gaps": [], "source_confidence": 50})

    assert bundle["mcp_manifest"]
    assert "OpenBB" in bundle["caveat"]
    assert "screener" in bundle["packets"]


def test_openbb_mcp_manifest_has_openbb_candidates():
    manifest = build_mcp_ready_openbb_endpoint_manifest()
    price = next(item for item in manifest if item["endpoint_id"] == "price.history")

    assert "openbb_candidates" in price["source_fallback"]
