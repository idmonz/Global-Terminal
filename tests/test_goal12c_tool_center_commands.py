from lib.research_tool_actions import get_research_tool_definition, search_research_tools
from lib.terminal_command_router import route_terminal_command
from lib.research_workflow_actions import validate_research_workflow_action


def test_goal12c_tool_center_exposes_safe_new_tools():
    names=[tool['tool_name'] for tool in search_research_tools('Surface QA')]
    assert 'Build Surface QA' in names
    tool=get_research_tool_definition('Build Option Book Stress')
    assert tool and tool['workflow_action'] == 'BUILD_OPTION_BOOK_STRESS'


def test_goal12c_command_router_exposes_new_commands():
    assert route_terminal_command('SURFACE QA')['ok'] is True
    assert route_terminal_command('OPTION BOOK STRESS')['ok'] is True
    assert route_terminal_command('HRP RMT')['ok'] is True


def test_goal12c_workflow_action_validation_accepts_new_safe_actions():
    assert validate_research_workflow_action('BUILD_SURFACE_QA', {})['ok'] is True
    assert validate_research_workflow_action('GENERATE_OPTION_BOOK_STRESS_REPORT', {})['ok'] is True
