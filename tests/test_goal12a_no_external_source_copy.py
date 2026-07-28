from pathlib import Path

NEW_FILES = list(Path("lib").glob("options_*.py")) + list(Path("lib").glob("quant_model_*.py")) + [Path("pages/24_Options_Quant_Model_Lab.py")]
EXTERNAL_SIGNATURES = ["TDA_API_KEY", "scipy.stats.mvn", "mvndst", "Davis Edwards", "BartolomeD", "shiyu-coder/Kronos", "tensortrade.env", "QuantDinger-main"]


def test_no_external_source_signatures_copied_into_goal12a_runtime():
    offenders = []
    for path in NEW_FILES:
        text = path.read_text(encoding="utf-8")
        for signature in EXTERNAL_SIGNATURES:
            if signature in text:
                offenders.append((str(path), signature))
    assert offenders == []


def test_no_external_runtime_dependency_added():
    req = Path("requirements.txt").read_text(encoding="utf-8") if Path("requirements.txt").exists() else ""
    forbidden = ["optlib", "tensortrade", "kronos", "quantdinger", "tda"]
    assert not any(item in req.lower() for item in forbidden)
