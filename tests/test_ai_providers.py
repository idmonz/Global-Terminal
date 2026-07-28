from __future__ import annotations

import lib.ai_providers as providers


def test_no_key_selects_rule_based_fallback(monkeypatch):
    for key in ["ANTHROPIC_API_KEY", "GEMINI_API_KEY", "GROQ_API_KEY", "OPENROUTER_API_KEY", "OLLAMA_BASE_URL", "AI_PROVIDER"]:
        monkeypatch.delenv(key, raising=False)
    selected = providers.select_ai_provider("auto")
    assert selected.provider == "rule_based"
    response = providers.call_ai_model("system", "user", preferred="auto", context={"data_gaps": "none"})
    assert response.ok
    assert response.provider == "rule_based"
    assert response.is_free_mode


def test_ollama_provider_available_when_base_url_exists(monkeypatch):
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    selected = providers.select_ai_provider("ollama")
    assert selected.provider == "ollama"
    assert selected.available
    assert selected.is_local


def test_auto_prefers_free_gemini_when_paid_key_also_exists(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-paid")
    monkeypatch.setenv("GEMINI_API_KEY", "AIza_free")
    monkeypatch.delenv("AI_PROVIDER", raising=False)

    selected = providers.select_ai_provider("auto")

    assert selected.provider == "gemini"
    assert selected.is_free_mode


def test_missing_key_returns_friendly_failure(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    response = providers.call_anthropic("system", "user")
    assert not response.ok
    assert "ANTHROPIC_API_KEY" in response.error
    assert "not configured" in response.warning


def test_provider_call_returns_airesponse_with_mocked_http(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test_secret")

    def fake_post(url, payload, headers, timeout=30):
        return {"choices": [{"message": {"content": "Evidence: neutral context."}}], "usage": {"total_tokens": 12}}, None, 3.4

    monkeypatch.setattr(providers, "_post_json", fake_post)
    response = providers.call_groq("system", "user")
    assert response.ok
    assert response.provider == "groq"
    assert response.usage["total_tokens"] == 12
    assert "Evidence" in response.text


def test_gemini_uses_free_flash_lite_and_header_key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "AIza_test_secret")
    monkeypatch.delenv("AI_MODEL", raising=False)
    captured = {}

    def fake_post(url, payload, headers, timeout=30):
        captured["url"] = url
        captured["payload"] = payload
        captured["headers"] = headers
        return {
            "candidates": [{"content": {"parts": [{"text": "Evidence: neutral Gemini summary."}]}}],
            "usageMetadata": {"totalTokenCount": 9},
        }, None, 4.2

    monkeypatch.setattr(providers, "_post_json", fake_post)
    response = providers.call_gemini("system", "user")

    assert response.ok
    assert response.provider == "gemini"
    assert response.model == "gemini-3.1-flash-lite"
    assert "AIza" not in captured["url"]
    assert captured["headers"]["x-goog-api-key"] == "AIza_test_secret"
    assert captured["payload"]["generationConfig"]["thinkingConfig"]["thinkingLevel"] == "minimal"
    assert "tools" not in captured["payload"]


def test_gemini_search_grounding_is_explicit_opt_in(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "AIza_test_secret")
    monkeypatch.setenv("GEMINI_ENABLE_GOOGLE_SEARCH", "true")
    captured = {}

    def fake_post(url, payload, headers, timeout=30):
        captured["payload"] = payload
        return {
            "candidates": [{"content": {"parts": [{"text": "Evidence: grounded summary."}]}}],
            "usageMetadata": {},
        }, None, 1.0

    monkeypatch.setattr(providers, "_post_json", fake_post)
    response = providers.call_gemini("system", "user")

    assert response.ok
    assert captured["payload"]["tools"] == [{"google_search": {}}]
