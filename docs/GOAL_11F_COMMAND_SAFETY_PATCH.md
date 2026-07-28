# Goal 11F Command Safety Patch

## Changes

- Added advisory and guarantee intent detection to `lib/research_command_safety.py`.
- Added explicit allowances for descriptive research phrases around holding period, exit liquidity, entry barriers, order-flow research, and duration terminology.
- Preserved shared behavior across Command Palette, Terminal Router, and direct workflow action calls.
- Blocked commands still return safe alternatives: review research context, add to watchlist, generate research brief, and create neutral condition alert.

## Validation

- `tests/test_goal11f_command_safety_advisory_language.py`
- Existing Goal 11D/11E command safety tests

## Boundary

The workspace remains research-only and does not route market actions, broker tasks, or autonomous workflows.
