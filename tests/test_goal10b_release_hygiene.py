from __future__ import annotations

from scripts.build_release_zip import iter_release_files


def test_goal10b_release_hygiene_excludes_external_cache_secrets():
    names = {path.as_posix() for path in iter_release_files()}
    assert any(name.endswith(".gitignore") for name in names)
    assert any(name.endswith(".env.example") for name in names)
    forbidden = ["external/", "data/cache/", "data/private/", ".streamlit/secrets.toml"]
    joined = "\n".join(names)
    for token in forbidden:
        assert token not in joined
    assert not any(name.endswith("/.env") or name.endswith("\\.env") for name in names)
    assert not any(".env." in name and not name.endswith(".env.example") for name in names)
