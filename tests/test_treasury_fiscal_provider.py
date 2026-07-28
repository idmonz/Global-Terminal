from __future__ import annotations

from lib.treasury_fiscal_provider import build_treasury_fiscal_url


def test_treasury_fiscal_url_builder():
    url = build_treasury_fiscal_url(params={"page[size]": 1})
    assert "fiscaldata.treasury.gov" in url
    assert "page%5Bsize%5D=1" in url
