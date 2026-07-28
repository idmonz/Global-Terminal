from __future__ import annotations

from pathlib import Path

from scripts.audit_git_publish import audit_git_candidates


def test_git_publish_audit_accepts_source_and_reviewed_test_placeholders(tmp_path: Path):
    (tmp_path / "lib").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "lib/app.py").write_text("print('safe')\n", encoding="utf-8")
    (tmp_path / "tests/test_key.py").write_text(
        "KEY = 'sb_secret_phase6q_server_only_value'\n",
        encoding="utf-8",
    )
    env = tmp_path / ".env"
    env.write_text("REAL_KEY=real-private-value-12345\n", encoding="utf-8")

    result = audit_git_candidates(
        tmp_path,
        [Path("lib/app.py"), Path("tests/test_key.py")],
        env_path=env,
    )

    assert result["passed"] is True
    assert result["reviewed_test_placeholder_count"] == 1
    assert result["exact_value_hit_count"] == 0


def test_git_publish_audit_rejects_private_paths_exact_values_and_tokens(tmp_path: Path):
    (tmp_path / "lib").mkdir()
    (tmp_path / "review_workspace").mkdir()
    (tmp_path / "lib/leak.py").write_text(
        "TOKEN = 'ghp_test12345678901234567890123456'\nREAL = 'real-private-value-12345'\n",
        encoding="utf-8",
    )
    (tmp_path / "review_workspace/state.json").write_text("{}\n", encoding="utf-8")
    env = tmp_path / ".env"
    env.write_text("REAL_KEY=real-private-value-12345\n", encoding="utf-8")

    result = audit_git_candidates(
        tmp_path,
        [Path("lib/leak.py"), Path("review_workspace/state.json")],
        env_path=env,
    )

    assert result["passed"] is False
    assert result["exact_value_hit_paths"] == ["lib/leak.py"]
    assert result["token_pattern_hit_paths"] == ["lib/leak.py"]
    assert result["forbidden_paths"] == ["review_workspace/state.json"]
