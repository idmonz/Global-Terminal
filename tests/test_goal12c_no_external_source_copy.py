from pathlib import Path


def test_goal12c_no_external_source_trees_copied():
    forbidden=['external/','agent-skills-main','Kronos-master','tensortrade-master','QuantDinger-main','optlib-master']
    for path in list(Path('lib').glob('options_*')) + list(Path('lib').glob('quant_diagnostics_*')):
        text=path.read_text(encoding='utf-8')
        assert not any(token in text for token in forbidden), path
