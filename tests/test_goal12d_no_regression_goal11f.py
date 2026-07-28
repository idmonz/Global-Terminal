from lib.top_command_bar import build_top_command_bar_state
from lib.report_inbox import create_report
from lib.strategy_decision_log import create_strategy_commit


def test_goal12d_goal11f_core_workflows_still_available(tmp_path):
    db = tmp_path / 'workspace.sqlite'
    state = build_top_command_bar_state('order flow BTC')
    assert state['validation']['ok'] is True
    report = create_report(report_type='manual', title='Goal 12D Report', summary='ok', db_path=db)
    assert report['report_id']
    commit = create_strategy_commit(strategy_id='s1', message='Research commit only', db_path=db)
    assert commit['commit_id']
