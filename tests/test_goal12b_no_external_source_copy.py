from pathlib import Path

SIGNATURES = ["TDA_API_KEY", "scipy.stats.mvn", "mvndst", "tensortrade.env", "QuantDinger-main", "shiyu-coder/Kronos"]


def test_goal12b_no_external_source_signatures_in_runtime():
    offenders=[]
    files=list(Path("lib").glob("options_*")) + list(Path("lib").glob("quant_diagnostics_*")) + [Path("pages/24_Options_Quant_Model_Lab.py")]
    for path in files:
        text=path.read_text(encoding="utf-8")
        for sig in SIGNATURES:
            if sig in text:
                offenders.append((str(path), sig))
    assert offenders == []


def test_goal12b_no_external_runtime_dependencies_added():
    req=Path("requirements.txt").read_text(encoding="utf-8").lower()
    for dep in ["optlib", "kronos", "tensortrade", "quantdinger"]:
        assert dep not in req
