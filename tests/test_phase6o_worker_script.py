from pathlib import Path


def test_phase6o_worker_requires_explicit_opt_in_and_never_starts_from_view():
    root = Path(__file__).resolve().parents[1]
    script = (root / "scripts/run_watchlist_alert_worker.py").read_text(encoding="utf-8")
    domain = (root / "lib/watchlist_alert_manager.py").read_text(encoding="utf-8")

    assert "GLOBAL_TERMINAL_ALERT_WORKER_ENABLED" in script
    assert "--loop" in script
    assert "max(60" in script
    assert "run_alert_worker_once" in script
    assert '"view_starts_worker": False' in domain
    assert '"observation_jobs_enabled": False' in domain
    assert "ObservationRunCoordinator" not in script

