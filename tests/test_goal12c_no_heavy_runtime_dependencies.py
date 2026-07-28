from pathlib import Path


def test_goal12c_no_heavy_mandatory_runtime_dependencies():
    req=(Path('requirements.txt').read_text(encoding='utf-8') + '\n' + Path('requirements-openbb.txt').read_text(encoding='utf-8')).lower()
    for token in ['torch', 'tensorflow', 'huggingface', 'transformers', 'tensortrade']:
        assert token not in req
    for path in list(Path('lib').glob('quant_diagnostics_*')) + list(Path('lib').glob('options_*')):
        text=path.read_text(encoding='utf-8').lower()
        assert 'from torch' not in text
        assert 'import torch' not in text
        assert 'tensorflow' not in text
        assert 'transformers' not in text
