from __future__ import annotations

import pytest

from lib.sdmx_provider import build_sdmx_url


def test_sdmx_provider_builds_safe_request_urls():
    url = build_sdmx_url("https://stats.example.org/api", "EXR", "A.USD", {"startPeriod": "2025"})
    assert url.startswith("https://")
    assert "startPeriod=2025" in url
    with pytest.raises(ValueError):
        build_sdmx_url("ftp://bad", "EXR")
