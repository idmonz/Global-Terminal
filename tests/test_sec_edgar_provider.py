from __future__ import annotations

from lib.sec_edgar_provider import build_sec_company_facts_url, fetch_sec_company_facts, sec_rate_limit_policy


def test_sec_edgar_requires_user_agent(monkeypatch):
    monkeypatch.delenv("SEC_USER_AGENT", raising=False)
    result = fetch_sec_company_facts("320193")
    assert result["status"] == "missing_key"
    assert "CIK0000320193" in build_sec_company_facts_url("320193")
    assert sec_rate_limit_policy()["requires_user_agent"] is True
