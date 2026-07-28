from lib.workspace_summary_engine import build_workspace_summary, build_workspace_summary_cards


def test_workspace_summary_cards(tmp_path):
    db=tmp_path/"sum.db"
    summary = build_workspace_summary(db)
    cards = build_workspace_summary_cards(db)
    assert summary["notice"].startswith("This workspace")
    assert len(cards) == 4

