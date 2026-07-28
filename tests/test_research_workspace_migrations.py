from lib.research_workspace_migrations import get_workspace_schema_version, run_workspace_migrations
from lib.research_workspace_schema import SCHEMA_VERSION


def test_workspace_migration_sets_version(tmp_path):
    db = tmp_path / "mig.db"
    run_workspace_migrations(db)
    assert get_workspace_schema_version(db) == SCHEMA_VERSION

