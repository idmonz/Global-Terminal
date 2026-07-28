# Phase 5Q TradingAgents Adoption Research

Updated: 2026-06-23

## Archive

- Archive: `external (2)/external/TradingAgents-main.zip`
- Entries: 175
- Text-like files: 138
- Approximate uncompressed bytes: 4,716,128
- License in archive: Apache License 2.0

## What It Contains

TradingAgents presents a multi-agent financial research/trading framework:

- analyst team: fundamentals, sentiment, news, technical;
- researcher team: bull and bear researchers;
- trader agent;
- risk management debaters;
- portfolio manager;
- graph orchestration, checkpoint resume and signal processing;
- append-only decision memory;
- provider registry across multiple LLM vendors;
- market data integrations including yfinance, Alpha Vantage, FRED, Reddit, StockTwits and Polymarket;
- structured-output schemas and tests.

## License And Safety Position

Apache-2.0 is permissive, but Phase 5Q does not copy source into the product. The archive is used as a clean-room product/process reference because the current product already has native provider, contract, memory, AI-safety and web boundaries. Direct adaptation should be considered only after exact file-path notice review.

## Adoptable Behaviors

| TradingAgents behavior | Clean-room Global Terminal adaptation |
|---|---|
| Analyst role decomposition | Add `research_perspectives.v1`: fundamentals, technical, news, sentiment, macro and risk perspectives with source-bound claims |
| Bull/bear researcher debate | Add non-advisory "supporting evidence vs risk evidence" panels; no buy/sell/hold or target-price output |
| Structured-output schemas | Use native Pydantic/JSON-safe validators for perspective rows, citations, unsupported claims and advice-language rejection |
| Decision memory | Reuse Research Memory and daily brief captures as append-only research artifacts, not trading decisions |
| Checkpoint/resume | Add local research-run checkpoints only if they contain sanitized public evidence and local-private metadata stays private |
| Provider registry | Extend provider capability ledger for Alpha Vantage/FRED/SEC/Binance/CoinGecko/Korean providers with live/cache/stale/gap states |
| Tool/data validation | Add provider-tool readiness tests that prevent configured credentials from becoming live without successful rows |
| CLI progress UI | Translate into web progress/status rail for long research composition rather than copying terminal UI/assets |

## Rejected Or Out Of Scope

- trading actions;
- order proposals;
- portfolio-manager approval language;
- entry, stop-loss, target price or sizing guidance;
- simulated exchange execution;
- broker routing;
- autonomous agents acting on private user data;
- direct use of TradingAgents assets or screenshots;
- vendoring LangGraph-heavy runtime into the base app.

## Phase 5R Implications

Phase 5R should keep the Daily Brief deterministic and source-bound, but can introduce a native "research perspectives" layer:

1. create role-specific evidence blocks for macro/rates, technicals, fundamentals, news/sentiment and global risk;
2. label each role as deterministic first-party analysis or optional public-sanitized AI draft;
3. show a compact debate matrix: evidence supporting the claim, evidence weakening it, missing data, and human review status;
4. attach source-bound charts/tables to top claims;
5. keep all recommendation/trading-agent semantics disabled.

## Free API Setup Notes

- Alpha Vantage provides official documentation and a free API key path, but free quotas are limited and endpoint entitlements can change. Add `ALPHA_VANTAGE_API_KEY=` as an empty placeholder only.
- FRED requires each application/user to request its own API key. The project already has `FRED_API_KEY=`.
- Gemini remains optional/free-first for public-sanitized drafts only.

Relevant official sources checked during closeout:

- Alpha Vantage official docs/free key page: https://www.alphavantage.co/documentation/
- FRED API key docs: https://fred.stlouisfed.org/docs/api/api_key.html
- OpenBB Workspace widgets: https://docs.openbb.co/workspace/analysts/widgets/overview
- Koyfin features: https://www.koyfin.com/features/
- TradingView watchlists: https://www.tradingview.com/support/solutions/43000745825-mastering-the-tradingview-watchlists/

Outputs remain research calculations and information displays only. They are not investment advice, recommendations, trade approvals, broker actions, autonomous monitoring or execution instructions.
