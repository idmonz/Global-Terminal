# Command Palette UX

The command palette resolves user text into research objects: asset, crypto, provider, region/chokepoint, strategy, or topic. It then produces action cards for opening the correct workspace, adding a watch item, creating alert conditions, or generating a manual research brief.

Execution-style commands are blocked by boundary checks.


## Goal 11D command safety and quick-add loop

The command palette now uses shared research boundary detection with the terminal router. Safe command results can call workflow actions such as watchlist quick-add or manual report creation. Blocked commands return boundary cards and safe alternatives without mutating state.

## Goal 11E Update

Goal 11E update: command safety now distinguishes descriptive research phrases from market-action intent and preserves the target topic for blocked-command alternatives.

## Goal 11F routing and safety update

Energy Brief labels now route to the Energy Brief workflow action. Advisory and guarantee phrasing returns a research-boundary card, while descriptive research terms continue to resolve normally.
