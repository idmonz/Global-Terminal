# Goal 11F Task Plan

| Slice | Implementation target | Validation |
|---|---|---|
| Setup artifact | `.env.example`, release builder | `test_goal11f_env_example_release_setup.py` |
| Command safety | `lib/research_command_safety.py` | `test_goal11f_command_safety_advisory_language.py` |
| Export security | `lib/report_export.py`, `lib/report_html_templates.py` | `test_goal11f_report_html_export_security.py` |
| Energy routing | command palette suggestion/action modules | `test_goal11f_command_palette_energy_brief_routing.py` |
| Release count | `scripts/build_release_zip.py` | `test_goal11f_release_count_consistency.py` |
| Regression | full suite | `python -m pytest -q` |

- Scope: Goal 11F hotfix only; Goal 12 was not implemented.
- Boundary: research-only local workspace, no broker path, no autonomous execution path, no external runtime dependency.
- Verification gates: compileall, smoke tests, full pytest, cleanup dry-run, cleanup execute, and release build.
