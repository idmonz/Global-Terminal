from lib.options_lab_page_layout import build_options_lab_page_payload


def test_goal12c_demo_mode_is_explicit_and_not_default_for_book_or_quant():
    payload=build_options_lab_page_payload()
    assert payload['demo_mode'] is False
    assert payload['option_book_stress'] is None
    assert payload['quant_diagnostics'] is None
    demo=build_options_lab_page_payload(demo_mode=True)
    assert demo['demo_mode'] is True
    assert 'Demo data' in demo['demo_mode_label']
