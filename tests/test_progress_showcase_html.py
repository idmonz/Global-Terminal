from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "build_progress_showcase.py"
OUTPUT_PATH = ROOT / "docs" / "GLOBAL_TERMINAL_PROGRESS_KO.html"
LINKED_OUTPUT_PATH = ROOT / "docs" / "GLOBAL_TERMINAL_PROGRESS_KO_LINKED.html"
REVIEW_ROOT = ROOT / "review_workspace"


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


def _capture_sources_available() -> bool:
    return REVIEW_ROOT.is_dir() and any(
        path.is_dir() and path.name.lower().startswith("phase")
        for path in REVIEW_ROOT.iterdir()
    )


def test_progress_showcase_contains_every_first_party_phase_capture() -> None:
    builder = _load_builder()
    assert OUTPUT_PATH.is_file()
    assert LINKED_OUTPUT_PATH.is_file()
    portable_document = OUTPUT_PATH.read_text(encoding="utf-8")
    linked_document = LINKED_OUTPUT_PATH.read_text(encoding="utf-8")
    portable_manifest = _manifest(portable_document)
    manifest = _manifest(linked_document)
    screenshot_count = len(portable_manifest)
    bundle_count = len({str(row["bundle"]) for row in portable_manifest})

    if _capture_sources_available():
        expected = builder.collect_screenshots()
        assert len(manifest) == len(expected)
        assert {row["relative"] for row in manifest} == {row["relative"] for row in expected}

    assert screenshot_count >= 600
    assert bundle_count >= 90

    assert len(manifest) == len(portable_manifest)
    assert {row["relative"] for row in manifest} == {
        row["relative"] for row in portable_manifest
    }
    assert len(manifest) == screenshot_count
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

    raw_evidence_available = _capture_sources_available()
    for row in manifest:
        relative = str(row["relative"])
        if raw_evidence_available:
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
    assert len(re.findall(r'data:image/[^;]+;base64,', document)) == len(manifest)


def test_progress_showcase_collector_fails_closed_when_raw_evidence_is_absent(tmp_path: Path) -> None:
    builder = _load_builder()
    builder.REVIEW_ROOT = tmp_path / "missing-review-workspace"

    assert builder.collect_screenshots() == []


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
