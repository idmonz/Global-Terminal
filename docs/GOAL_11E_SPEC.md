# Goal 11E Spec

Goal 11E is a micro-hardening gate for the Research OS before Goal 12. It preserves all Goal 10B/11/11B/11C/11D functionality and only hardens command safety, direct workflow actions, alert evaluation, report/tool coverage, state persistence, and rendering safety.

## Non-goals

- No Goal 12 Options Pricing & Quant Model Lab.
- No live trading, broker routing, autonomous agents, background daemons, or external runtime dependencies.
- No external source code copy.

## Acceptance focus

- Valid research phrases remain usable.
- Market-action intent remains blocked consistently.
- Safe manual actions mutate SQLite only after explicit action.
- Alert evaluation is real when supplied context exists and caveated when missing.
- Tool Center actions are mapped or explicitly disabled.
- Selected report/commit state persists across review updates.
- Markdown remains readable and unsafe HTML remains escaped.
