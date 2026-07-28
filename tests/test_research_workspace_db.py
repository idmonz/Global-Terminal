from lib.research_workspace_db import initialize_workspace_db, execute_query, backup_workspace_db, reset_demo_workspace_data


def test_workspace_db_initializes_idempotently(tmp_path):
    db = tmp_path / "rw.db"
    first = initialize_workspace_db(db)
    second = initialize_workspace_db(db)
    assert first == second and db.exists()
    row = execute_query("SELECT COUNT(*) AS count FROM watchlist_items", fetch=True, one=True, db_path=db)
    assert row["count"] == 0
    backup = backup_workspace_db(tmp_path / "backup.db", db)
    assert backup.exists()
    assert reset_demo_workspace_data(db)["demo"] is True

