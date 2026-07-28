# Phase 8 AI Visual Terminal Plan

## Scope

Phase 8 adds a provider-agnostic AI analysis layer and a WorldMonitor-style situational awareness terminal without rewriting the recovered Phase4, goal1, or goal3 modules.

## AI Layer

- Add optional providers for Anthropic, Gemini, Groq, OpenRouter, Ollama, and rule-based fallback.
- Keep all LLM calls button-triggered.
- Send compact structured context rather than raw large dataframes.
- Redact secrets from prompt debugging views.
- Validate and neutralize output before display.

## Visual Terminal

- Upgrade `app.py` into an Overview Terminal.
- Add cross-asset cards, chart modes, heatmap strip, crypto/equity/energy/risk mini-panels, event map, and source status.
- Add financial statement visualization, option-chain/gamma proxy, screeners, and map panels.

## Guardrails

- No fake live data.
- No recommendation language.
- Estimated or proxy data must be labeled.
- WorldMonitor remains optional and is not a runtime dependency.
