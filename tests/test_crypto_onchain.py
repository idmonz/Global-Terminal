from lib.crypto_onchain import get_defillama_chains, get_stablecoins_by_chain, get_stablecoins_overview
from lib.data_status import failure, success


def test_defillama_chain_schema(monkeypatch):
    payload = [{"name": "Ethereum", "chain": "Ethereum", "tvl": 1000}]

    def fake_get(base, path, **kwargs):
        return payload, success(payload, source="unit", provider="DefiLlama")

    monkeypatch.setattr("lib.crypto_onchain._llama_get", fake_get)
    frame, status = get_defillama_chains()
    assert status.ok
    assert frame["tvl"].iloc[0] == 1000


def test_defillama_malformed_stablecoins(monkeypatch):
    def fake_get(base, path, **kwargs):
        return ["bad"], success(["bad"], source="unit", provider="DefiLlama")

    monkeypatch.setattr("lib.crypto_onchain._llama_get", fake_get)
    frame, status = get_stablecoins_overview()
    assert frame.empty
    assert not status.ok


def test_defillama_missing_provider_failure(monkeypatch):
    def fake_get(base, path, **kwargs):
        return None, failure(source="unit", provider="DefiLlama", error="network unavailable")

    monkeypatch.setattr("lib.crypto_onchain._llama_get", fake_get)
    frame, status = get_defillama_chains()
    assert frame.empty
    assert not status.ok


def test_defillama_stablecoinchains_endpoint_and_schema(monkeypatch):
    seen = {}

    def fake_get(base, path, **kwargs):
        seen["path"] = path
        payload = [{"name": "Ethereum", "totalCirculatingUSD": {"peggedUSD": 1000, "peggedEUR": 25}}]
        return payload, success(payload, source="unit", provider="DefiLlama")

    monkeypatch.setattr("lib.crypto_onchain._llama_get", fake_get)
    frame, status = get_stablecoins_by_chain()
    assert status.ok
    assert seen["path"] == "/stablecoinchains"
    assert frame["chain"].iloc[0] == "Ethereum"
    assert frame["stablecoin_supply_usd"].iloc[0] == 1000
