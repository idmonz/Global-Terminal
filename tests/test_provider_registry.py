from __future__ import annotations

from lib.provider_registry import (
    PROVIDER_SCHEMA,
    build_provider_registry,
    list_providers_by_domain,
    provider_capability_matrix,
    provider_env_status,
    provider_requires_key,
)


def test_provider_registry_schema_and_domains(monkeypatch):
    monkeypatch.delenv("COINGLASS_API_KEY", raising=False)
    registry = build_provider_registry()
    assert registry
    assert set(PROVIDER_SCHEMA).issubset(registry[0])
    assert list_providers_by_domain("Crypto")
    assert provider_capability_matrix().shape[0] == len(registry)
    assert provider_requires_key("coinglass")
    assert provider_env_status("coinglass")["status"] == "missing optional key"
