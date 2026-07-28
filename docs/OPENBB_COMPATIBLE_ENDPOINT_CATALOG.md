# OpenBB-Compatible Endpoint Catalog

`lib/endpoint_catalog.py` defines endpoint metadata for market, equity, ETF, options, macro/rates, commodity/energy, shipping, crypto, technical, quant, news, and OSINT workflows.

Each endpoint records:

- endpoint id, app area, domain, label
- required and optional fields
- native providers
- OpenBB candidate paths
- optional provider keys
- proxy/estimated flags
- caveats and downstream pages

`lib/openbb_catalog.py` exposes `build_openbb_compatible_endpoint_catalog()` for the OpenBB Data Hub.
# Goal 10 Update

OpenBB remains optional. Goal 10 adds Data Provider Center/OpenBB Data Hub runtime probe panels and a compatibility wrapper for `resolve_openbb_endpoint_path`. Provider rights, licensing, and API key requirements remain user-verified before production use.
