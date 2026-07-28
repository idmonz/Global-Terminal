# OpenBB Provider Catalog

The local OpenBB catalog lives in `lib/openbb_catalog.py`.

It maps OpenBB target domains to local app areas:

- Equity
- ETF
- Fixed Income / Rates
- Economy / Macro
- Commodity / Energy
- Derivatives / Options
- Regulators
- Technical
- Quantitative

Each row includes app area, endpoint label, use case, provider examples, key requirement, free/paid likelihood, native fallback, and caveat.

The catalog is metadata-only and does not call OpenBB on page load.

## Goal 9 Internal Catalog

`lib/endpoint_catalog.py` now holds the internal OpenBB-compatible endpoint catalog. `lib/openbb_catalog.py` exposes `build_openbb_compatible_endpoint_catalog()` for Data Hub views.

The catalog maps native providers, optional OpenBB candidate paths, optional keys, proxy flags, caveats, and downstream pages.
