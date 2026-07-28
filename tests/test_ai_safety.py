from __future__ import annotations

from lib.ai_safety import (
    ai_output_to_safe_markdown,
    allowed_market_context_terms,
    append_ai_disclosure,
    clean_ai_output,
    forbidden_recommendation_terms,
    redact_secrets,
    validate_ai_output,
)


def test_forbidden_terms_are_cleaned_and_detected():
    assert "Buy" in forbidden_recommendation_terms()
    ok, terms = validate_ai_output("This is a Strong Buy and trade now.")
    assert not ok
    assert "Strong Buy" in terms
    cleaned = clean_ai_output("Strong Buy. You should sell now.")
    assert validate_ai_output(cleaned)[0]
    assert "Strong Buy" not in cleaned


def test_allowed_market_context_terms_are_not_blocked():
    assert "long/short ratio" in allowed_market_context_terms()
    text = "The long/short ratio and gamma exposure proxy are elevated."
    ok, terms = validate_ai_output(text)
    assert ok
    assert terms == []


def test_disclosure_appended_and_secrets_redacted():
    redacted = redact_secrets("ANTHROPIC_API_KEY=sk-ant-secret and GROQ_API_KEY=gsk_secret and GOOGLE_API_KEY=AIza_secret")
    assert "sk-ant-secret" not in redacted
    assert "gsk_secret" not in redacted
    assert "AIza_secret" not in redacted
    disclosed = append_ai_disclosure("Neutral evidence summary.")
    assert "AI summary" in disclosed
    safe = ai_output_to_safe_markdown("Should buy because of momentum.")
    assert validate_ai_output(safe)[0]
