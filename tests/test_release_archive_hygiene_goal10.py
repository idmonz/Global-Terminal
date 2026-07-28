from __future__ import annotations

from scripts.build_release_zip import iter_release_files


def test_goal10_release_archive_excludes_secrets_and_external_sources():
    paths = [path.relative_to(path.parents[1]).as_posix() if path.is_absolute() else path.as_posix() for path in iter_release_files()]
    joined = "\n".join(paths)
    assert ".gitignore" in joined
    assert ".env.example" in joined
    assert "requirements-openbb.txt" in joined
    assert "external/" not in joined
    assert ".env\n" not in joined
    assert "provider_probe_results.json" not in joined
