from pathlib import Path


def test_goal12d_no_heavy_runtime_dependencies_added():
    req = Path('requirements.txt').read_text(encoding='utf-8').lower()
    for token in ['tensorflow', 'torch', 'transformers', 'huggingface', 'tensortrade', 'kronos']:
        assert token not in req
