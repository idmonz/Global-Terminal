from __future__ import annotations

from lib.compliance import contains_forbidden_language, sanitize_text
from lib.config import DISCLOSURE


def test_compliance_sanitizes_restricted_language():
    cleaned = sanitize_text("This is a buy recommendation.")
    assert not contains_forbidden_language(cleaned)


def test_disclosure_is_allowed():
    assert not contains_forbidden_language(DISCLOSURE)

