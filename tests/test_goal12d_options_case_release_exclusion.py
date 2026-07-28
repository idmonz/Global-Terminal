from scripts.build_release_zip import _is_excluded, ROOT


def test_goal12d_options_case_files_are_release_excluded():
    assert _is_excluded(ROOT / "data" / "private" / "options_cases" / "case_a" / "case_manifest.json") is True
    assert _is_excluded(ROOT / "data" / "private" / "options_cases" / "case_a" / "chain_snapshot.json") is True
    assert _is_excluded(ROOT / "data" / "cache" / "uploaded_option_chain.csv") is True
