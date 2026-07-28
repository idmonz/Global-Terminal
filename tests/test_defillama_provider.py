from __future__ import annotations

from lib.defillama_provider import build_defillama_url


def test_defillama_url_builder():
    assert build_defillama_url("/protocols").endswith("/protocols")
