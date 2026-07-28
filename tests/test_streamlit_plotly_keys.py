from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _plotly_chart_calls(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "plotly_chart":
            yield node


def test_goal6_streamlit_plotly_calls_have_keys():
    for rel in ["pages/6_News.py", "pages/14_War_Room.py", "pages/15_Financial_Terminal.py"]:
        path = ROOT / rel
        calls = list(_plotly_chart_calls(path))
        assert calls, rel
        for call in calls:
            assert any(keyword.arg == "key" for keyword in call.keywords), rel
