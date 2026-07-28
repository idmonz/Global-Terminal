from __future__ import annotations

from lib.gdelt_provider import build_gdelt_doc_url


def test_gdelt_url_builder_encodes_query():
    url = build_gdelt_doc_url("oil chokepoint")
    assert "query=oil+chokepoint" in url
    assert "format=json" in url
