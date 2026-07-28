# Modern Visual System

Goal 10B adds a project-native visual system for a modern Global Intelligence Terminal. It is clean, summary-first, dark-mode friendly, and intentionally not a Bloomberg-style orange/black terminal clone.

## Modules

- `lib/visual_tokens.py`: spacing, radius, borders, neutral/accent/risk/data-quality palettes, typography, table, metric, and chart card tokens.
- `lib/modern_visual_system.py`: summary panels, page headers, metric cards, confidence badges, freshness badges, and modern cards.
- `lib/summary_keyword_engine.py`: extracts 3-8 keyword chips for risk drivers, assets, regions, provider issues, freshness, macro, crypto, energy, watchlists, and strategy research.
- `lib/click_path_engine.py`: builds next-action cards and drilldown maps using neutral research verbs.
- `lib/ui_action_cards.py`: compact action card payloads with no trading directives.

## Design Rules

- Summary first, detail second.
- Data confidence, source freshness, proxy/missing/historical-only labels stay visible.
- Click paths use inspect, review, open, drill down, compare, verify data, and check source.
- Commands and cards do not use buy/sell/hold/trade/enter/exit language.
