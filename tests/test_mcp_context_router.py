from __future__ import annotations

import pandas as pd

from lib.mcp_context_router import build_mcp_ready_endpoint_manifest, build_screener_context_packet, compress_context_for_llm, route_context_to_ai_provider


def test_mcp_context_compresses_dataframes():
    packet = build_screener_context_packet({"rows": pd.DataFrame({"ticker": ["AAPL"], "price": [100]}), "data_gaps": [], "source_confidence": 80})
    compacted = compress_context_for_llm(packet)

    assert compacted["truncated"] is False
    assert "sample_rows" in str(compacted["packet"])


def test_mcp_manifest_describes_endpoint_schemas():
    manifest = build_mcp_ready_endpoint_manifest()

    assert any(item["endpoint_id"] == "price.history" for item in manifest)
    assert "input_schema" in manifest[0]


def test_context_router_does_not_call_llm_by_default():
    routed = route_context_to_ai_provider({"context_type": "test"})

    assert routed["execute"] is False
    assert "No automatic LLM call" in routed["policy"]
