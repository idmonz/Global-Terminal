from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "build_progress_showcase.py"
OUTPUT_PATH = ROOT / "docs" / "GLOBAL_TERMINAL_PROGRESS_KO.html"
LINKED_OUTPUT_PATH = ROOT / "docs" / "GLOBAL_TERMINAL_PROGRESS_KO_LINKED.html"


def _load_builder():
    spec = importlib.util.spec_from_file_location("build_progress_showcase", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _manifest(document: str) -> list[dict[str, object]]:
    match = re.search(
        r'<script id="screenshot-manifest" type="application/json">(.*?)</script>',
        document,
        flags=re.DOTALL,
    )
    assert match, "Screenshot manifest is missing"
    return json.loads(match.group(1).replace("<\\/", "</"))


def test_progress_showcase_contains_every_first_party_phase_capture() -> None:
    builder = _load_builder()
    output, screenshot_count, bundle_count = builder.build_html()
    assert output == OUTPUT_PATH
    assert screenshot_count >= 600
    assert bundle_count >= 90

    portable_document = OUTPUT_PATH.read_text(encoding="utf-8")
    linked_document = LINKED_OUTPUT_PATH.read_text(encoding="utf-8")
    manifest = _manifest(linked_document)
    expected = builder.collect_screenshots()

    assert len(manifest) == len(expected) == screenshot_count
    assert {row["relative"] for row in manifest} == {row["relative"] for row in expected}
    assert len({row["relative"] for row in manifest}) == screenshot_count
    assert linked_document.count('data-evidence-count="') == 1
    assert "Phase 6Q" in portable_document
    assert "hosted_scheduler_verified=false" in portable_document
    assert "HTML 파일 하나만 옮겨도 그대로 열립니다" in portable_document
    assert len(re.findall(r'data:image/[^;]+;base64,', portable_document)) == screenshot_count


def test_progress_showcase_references_existing_images_and_excludes_external_evidence() -> None:
    if not OUTPUT_PATH.exists():
        _load_builder().build_html()
    document = OUTPUT_PATH.read_text(encoding="utf-8")
    linked_document = LINKED_OUTPUT_PATH.read_text(encoding="utf-8")
    manifest = _manifest(linked_document)

    for row in manifest:
        relative = str(row["relative"])
        assert (ROOT / relative).is_file(), relative
        assert relative.startswith("review_workspace/phase")
        assert "benchmark" not in relative.lower()
        assert "external2_analysis" not in relative.lower()
        assert "old_goal10b" not in relative.lower()

    text_only = re.sub(r'data:image/[^;]+;base64,[A-Za-z0-9+/=]+', 'data:image/redacted;base64,', document)
    forbidden = ["SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_ANON_KEY", "ALPHAVANTAGE_API_KEY", "FINNHUB_API_KEY", "AIza"]
    assert not any(secret in text_only for secret in forbidden)
    assert re.search(r"\bsk-[A-Za-z0-9_-]{20,}", text_only) is None
    assert "C:\\Users\\" not in text_only
    assert ".env" not in text_only
    assert "../review_workspace/" not in text_only
    assert 'href="ROADMAP.md"' not in text_only
    assert text_only.count('href="data:text/markdown;charset=utf-8;base64,') == 6


def test_progress_showcase_has_accessible_interactive_structure() -> None:
    if not OUTPUT_PATH.exists():
        _load_builder().build_html()
    document = OUTPUT_PATH.read_text(encoding="utf-8")

    required_fragments = [
        'lang="ko"',
        'href="#main"',
        'aria-label="문서 탐색"',
        'id="shot-search"',
        'id="phase-filter"',
        'id="lightbox"',
        'aria-live="polite"',
        '@media (max-width: 460px)',
    ]
    for fragment in required_fragments:
        assert fragment in document

    assert len(re.findall(r'<article class="feature-shot">', document)) >= 10
    assert len(re.findall(r'<tr>', document)) >= 40
