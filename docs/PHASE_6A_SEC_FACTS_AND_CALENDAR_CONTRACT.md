# Phase 6A SEC Facts And Calendar Contract

Updated: 2026-07-01

## SEC Company Facts

`lib/sec_edgar_provider.py` now normalizes an allow-list of reviewed `us-gaap`
concepts from SEC company facts.

Every fact preserves:

- CIK and ticker identity;
- namespace, concept, source label, and contract label;
- unit and value without zero imputation;
- start/end or instant;
- fiscal year and fiscal period;
- form, filed date, accession, and frame;
- provider, source URL, fetch time, status, caveat, and data gap.

Forms are bounded to 10-K/10-Q and amendments. Units are checked per reviewed
concept. The configured SEC user agent is used for fair access but is never
returned in payloads.

## Earnings Calendar

`lib/equity_provider_breadth.py` now normalizes:

- Alpha Vantage reported earnings;
- Finnhub scheduled earnings calendar rows.

Reported and scheduled states remain separate. Dates, timezone uncertainty,
reported EPS, estimated EPS, fiscal quarter, provider, source status, and gaps are
preserved. Missing values remain null. No target, recommendation, position, or
trade action is added.

## Observed AAPL State

- SEC status: `live/fresh`;
- facts: 44 rows across 11 reviewed concepts;
- earnings status: `cached`;
- displayed earnings rows: 8 in final visual evidence;
- scheduled rows can have unavailable reported EPS;
- the UI shows period, unit, filing form, and filed date.

