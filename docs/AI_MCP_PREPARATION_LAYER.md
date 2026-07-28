# AI / MCP Preparation Layer

Modules:

- `lib/mcp_context_router.py`
- `lib/openbb_ai_context_router.py`

The layer builds compact packets for financial, portfolio, screener, macro/energy, and War Room contexts. It also creates an MCP-ready endpoint manifest with input schema, output schema, source/fallback, and caveats.

No automatic LLM call is made. `route_context_to_ai_provider(..., execute=False)` returns a prepared packet by default.
