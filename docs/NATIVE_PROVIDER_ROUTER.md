# Native Provider Router

`lib/provider_router.py` ranks provider candidates by source mode:

- `auto`: native first, OpenBB optional, proxy/static, then data gap
- `native_only`: native/static/proxy only
- `openbb_preferred`: OpenBB first if available, native fallback allowed
- `openbb_only`: OpenBB route or explicit data gap
- `provider_specific`: selected provider only where cataloged

Missing optional keys become `DataGap` records. Secret values are never displayed.
