from pathlib import Path

ALLOWED = "Options, option-chain, volatility-surface, option-book, and model outputs are research calculations only. They are not investment advice, trading recommendations, trade approvals, hedging instructions, or execution instructions."
FORBIDDEN = ["guaranteed return", "profit guarantee", "execute order", "broker route", "live trade", "auto trade", "rebalance now", "hedge this", "trade now", "go long", "go short", "entry signal", "exit signal"]


def test_goal12c_new_runtime_has_no_execution_language():
    offenders=[]
    files=list(Path('lib').glob('options_*')) + list(Path('lib').glob('quant_diagnostics_*')) + [Path('pages/24_Options_Quant_Model_Lab.py')]
    for path in files:
        text=path.read_text(encoding='utf-8').lower().replace(ALLOWED.lower(), '')
        for phrase in FORBIDDEN:
            if phrase in text:
                offenders.append((str(path), phrase))
    assert offenders == []
