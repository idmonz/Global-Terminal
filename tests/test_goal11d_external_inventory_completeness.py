from pathlib import Path

REQUIRED_EXTERNALS = [
    "OpenStock-main.zip",
    "bloomberg-terminal-main.zip",
    "BB-Terminal-main.zip",
    "worldmonitor-main.zip",
    "osiris-master.zip",
    "OpenAlice-master.zip",
    "OpenBB-develop.zip",
    "optlib-master.zip",
    "quant-traderr-lab-main.zip",
    "agent-skills-main.zip",
    "Kronos-master.zip",
    "QuantDinger-main.zip",
    "tensortrade-master.zip",
    "worldview-main.zip",
]


def test_goal11d_external_inventory_completeness_report_lists_all_references():
    text = Path("docs/GOAL_11D_EXTERNAL_COMPLETENESS_AUDIT.md").read_text(encoding="utf-8")
    for name in REQUIRED_EXTERNALS:
        assert name in text
    assert "No external source code was copied" in text
