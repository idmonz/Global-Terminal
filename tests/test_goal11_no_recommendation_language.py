from pathlib import Path

ACTIONABLE_PHRASES = [
    "should buy", "should sell", "time to enter", "time to exit", "go long", "go short",
    "guaranteed return", "expected profit guarantee",
]


def test_goal11_files_avoid_actionable_trading_phrases():
    targets = (
        list(Path("lib").glob("*research*.py"))
        + list(Path("lib").glob("*watchlist*.py"))
        + list(Path("lib").glob("*alert*.py"))
        + list(Path("lib").glob("*report*.py"))
        + list(Path("lib").glob("*strategy*.py"))
        + list(Path("pages").glob("2[0-2]_*.py"))
        + [Path("pages/19_Research_Workspace.py")]
    )
    text = "\n".join(p.read_text(encoding="utf-8").lower() for p in targets if p.exists())
    for phrase in ACTIONABLE_PHRASES:
        assert phrase not in text
