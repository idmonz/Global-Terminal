from pathlib import Path


def test_goal12d_no_external_source_trees_copied_into_runtime():
    root = Path('.')
    forbidden_dirs = ['external', 'agent-skills-main', 'optlib-master', 'Kronos-master', 'tensortrade-master', 'QuantDinger-main', 'OpenAlice-master', 'OpenStock-main']
    for name in forbidden_dirs:
        assert not (root / name).exists()
    for py in Path('lib').glob('*.py'):
        text = py.read_text(encoding='utf-8')
        assert 'from optlib' not in text
        assert 'import optlib' not in text
        assert 'tensortrade' not in text.lower() or 'concept' in text.lower() or 'placeholder' in text.lower()
