from __future__ import annotations

from lib.ai_analysis import analyze_crypto_neutral, analyze_overview_neutral
from lib.ai_providers import AIResponse
from lib.ai_safety import validate_ai_output


def test_analysis_falls_back_without_provider(monkeypatch):
    for key in ["ANTHROPIC_API_KEY", "GEMINI_API_KEY", "GROQ_API_KEY", "OPENROUTER_API_KEY", "OLLAMA_BASE_URL"]:
        monkeypatch.delenv(key, raising=False)
    response = analyze_overview_neutral({"data_gaps": "unit test"})
    assert response.ok
    assert response.provider == "rule_based"
    assert "Data gaps" in response.text


def test_analysis_neutralizes_unsafe_provider_output(monkeypatch):
    def fake_call(system, user, preferred="auto", context=None):
        return AIResponse(ok=True, provider="mock", model="mock", text="Strong Buy. Time to enter.", source_status={})

    monkeypatch.setattr("lib.ai_analysis.call_ai_model", fake_call)
    response = analyze_crypto_neutral({"asset": "BTC"})
    assert response.ok
    assert validate_ai_output(response.text)[0]
    assert "Strong Buy" not in response.text
