# Internal Unified Data Layer

Goal 9 adds a native data path:

`DataRequest -> provider_router -> endpoint_catalog -> native/OpenBB adapter -> schema_normalizer -> UnifiedDataResult`.

Key modules:

- `lib/data_contracts.py`: request, route, provider, endpoint, gap, and result dataclasses.
- `lib/endpoint_catalog.py`: OpenBB-compatible internal endpoint catalog.
- `lib/provider_router.py`: native/OpenBB/proxy/data-gap routing.
- `lib/schema_normalizer.py`: tolerant normalizers that return DataFrames plus `DataGap` records.
- `lib/data_router.py`: central request dispatcher.
- `lib/unified_data_layer.py`: stable facade for pages and future AI/API use.
- `lib/data_freshness_engine.py` and `lib/data_gap_engine.py`: diagnostics.

The layer prefers native providers unless source mode asks for OpenBB, and OpenBB remains lazy and optional.
# Goal 10 Update

`lib.unified_data_layer.request_data` is restored as a compatibility export over `lib.data_router.request_data`. Goal 10 executive summaries consume unified result metadata such as source confidence, freshness, provider health, proxy labels, and data gaps rather than bypassing the unified layer.
