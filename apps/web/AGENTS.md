<!-- BEGIN:nextjs-agent-rules -->
# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code. Heed deprecation notices.
<!-- END:nextjs-agent-rules -->

# Global Terminal Web Rules

- Treat this app as the commercial product, not a fixture inspector.
- Put market, symbol, chart, map, news, or report content before diagnostics.
- Preserve symbol, asset class, timeframe, and runtime mode in the URL.
- Use stable chart/map dimensions and verify renderer-ready nonblank output.
- Make loading, empty, cached, stale, fixture, provider-required, unavailable, and error states visible.
- Keep provenance compact and inspectable; do not let it dominate the first viewport.
- Maintain keyboard navigation, visible focus, WCAG AA contrast, and readable 390px layouts.
- Do not add Streamlit assumptions, execution controls, recommendation language, secrets, private paths, or unreviewed external assets.
- Run `npm.cmd --prefix apps/web test`, `run lint`, and `run build` after changes.
