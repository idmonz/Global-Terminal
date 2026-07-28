# Phase 6N Provider And Live Evidence

Updated: 2026-07-13

## Controlled Source-Backed Run

Evidence: `review_workspace/phase6n_live/summary.json`.

- one explicit AAPL run completed for one requested symbol;
- three actual operations were contacted: yfinance history, Alpha Vantage
  overview, and Finnhub company news;
- Finnhub earnings was cache-backed/skipped and was not counted as contacted;
- the resulting snapshot used provider `yfinance`, source status `live/fresh`,
  observed market candle `2026-07-13T00:00:00Z`, retrieval
  `2026-07-13T14:06:38Z`, and last price `321.3599853515625`;
- attempt, retrieval, and completion clocks remained distinct;
- the same-day replay reused the stable run and added zero quota calls.

This is a daily observation retrieved during the session, not an exchange
real-time tick claim. A later independent finance check at 14:40:54 UTC showed
AAPL at 318.86 with a 315.25-323.40 intraday range, making the earlier value
plausible but not proving general provider reliability.

## Cache, Offline, And LKG Matrix

- cache-only run: completed, zero actual calls, all providers `contacted=false`;
- controlled provider-offline run: partial, zero actual calls, one valid LKG
  row retained as `stale`;
- the LKG row kept the original market observation clock while retrieval time
  advanced;
- malformed or missing capability output is recorded in the missing-capability
  ledger instead of promoted to live;
- Attention first read, second read, and compose each recorded zero provider
  calls.

## Quota And Session Policy

- the product hard cap is five symbols and 16 operations per explicit run;
- Alpha Vantage is budgeted against the documented free allowance of 25 calls
  per day;
- Finnhub uses a conservative local planning window and does not infer a
  subscription quota; its official documentation separately describes HTTP
  429 behavior and a 30 calls/second global ceiling;
- due-work decisions use explicit capability/session metadata and never invent
  an exchange-open state;
- cache, stale, quota-blocked, missing-key, forbidden, partial, and unavailable
  states are visible and do not consume hidden retries.

## Evidence Limits

One successful run proves the bounded path works in this environment. It does
not prove continuous uptime, broad symbol coverage, licensed real-time status,
or production SLA. Alpha Vantage and Finnhub keys are present but never written
to evidence, fixtures, logs, screenshots, or release artifacts.

