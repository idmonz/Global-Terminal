from pathlib import Path

ALLOWED_DISCLOSURE = "Options and model outputs are research calculations only. They are not investment advice, trading recommendations, trade approvals, or execution instructions."
FORBIDDEN_PHRASES = ["strong buy", "strong sell", "guaranteed return", "guaranteed profit", "profit guarantee", "go long", "go short", "entry signal", "exit signal", "trade now", "market order", "broker route"]
SCAN_PATHS = [Path("lib"), Path("pages")]


def test_goal12a_new_code_has_no_actionable_market_language():
    offenders = []
    for root in SCAN_PATHS:
        for path in root.rglob("*.py"):
            if "goal12a" not in path.name.lower() and not any(part in path.name for part in ["options_", "quant_model_"]) and path.name != "24_Options_Quant_Model_Lab.py":
                continue
            text = path.read_text(encoding="utf-8").lower().replace(ALLOWED_DISCLOSURE.lower(), "")
            for phrase in FORBIDDEN_PHRASES:
                if phrase in text:
                    offenders.append((str(path), phrase))
    assert offenders == []
