# Goal 11E Security Audit

## Trust boundaries

- Command Palette input
- Terminal Router input
- Direct workflow action payloads
- Report Markdown/HTML bodies
- Streamlit session state
- Local SQLite workflow mutations

## Controls

- Shared command safety boundary across palette, router, and direct workflow actions.
- Context-aware allowlist for descriptive research phrases.
- Direct mutation actions return blocked cards without DB writes when boundary is crossed.
- Alert action does not fabricate triggers when context is missing.
- Markdown renderers escape raw HTML/script tags while preserving Markdown readability.
- External skills and external source trees are not runtime dependencies and are excluded from release.

## Remaining limitations

- Streamlit UI remains local/manual and should still be reviewed in-browser before broad user rollout.
- Alert evaluation depends on supplied local context or stored alert rules; no background daemon is introduced.
