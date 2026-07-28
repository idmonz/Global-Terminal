# Modern Command UX System

Goal 10B adds command and shortcut payload helpers that preserve useful terminal concepts without copying Bloomberg's visual style.

## Modules

- `lib/top_command_bar.py`: command bar state, suggestions, placeholder, validation, and research-only guard.
- `lib/shortcut_registry.py`: shortcut-to-command/page registry.
- `lib/shortcut_help.py`: searchable help rows and help panel.
- `lib/refresh_state.py`: fresh/aging/stale/unknown refresh state.
- `lib/source_freshness_indicator.py`: source freshness dots and truth labels.

## Guarantees

- Commands route to research pages and diagnostics.
- Trade execution language is blocked by `validate_command_bar_action`.
- Help payloads state that commands do not execute trades.
- Source freshness and truth labels are first-class payload fields.
