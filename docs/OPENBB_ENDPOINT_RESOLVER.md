# OpenBB Endpoint Resolver

`lib/openbb_endpoint_resolver.py` resolves internal endpoint ids to runtime OpenBB paths through version-tolerant aliases.

It supports:

- mock objects in tests
- nested attribute traversal
- runtime path listing
- cached resolution for installed OpenBB sessions
- unavailable reasons when OpenBB is missing or paths differ

The resolver does not import OpenBB unless called.
