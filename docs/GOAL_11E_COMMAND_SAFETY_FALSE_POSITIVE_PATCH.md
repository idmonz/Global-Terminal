# Goal 11E Command Safety False-Positive Patch

## Fixed

The command safety layer now distinguishes market-action intent from descriptive research phrases.

Allowed descriptive classes include:

- macro duration phrases such as long-term Treasury and short-term rates
- duration research phrases such as long duration and short duration
- market-structure phrases such as order flow, orderflow, order book, order book depth, limit order book
- ratio/positioning descriptors such as taker ratio terms, long/short ratio, short interest

Blocked intent classes remain blocked in both Command Palette and Terminal Router:

- direct market-action requests
- directional action requests
- market-order or route requests
- entry/exit action-intent phrases

## Implementation

- `normalize_command_text()` remains the shared normalizer.
- `detect_forbidden_command_intent()` now uses allowed spans and context-aware token logic.
- `sanitize_research_query()` preserves descriptive allowed phrases and preserves target symbols/topics for blocked phrases.
