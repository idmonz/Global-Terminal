# AI Provider Guide

## Supported Providers

- `ANTHROPIC_API_KEY`: Anthropic Claude API.
- `GEMINI_API_KEY`: Google Gemini API. `GOOGLE_API_KEY` is also accepted as a fallback, but configure only one locally.
- `GROQ_API_KEY`: Groq OpenAI-compatible API.
- `OPENROUTER_API_KEY`: OpenRouter OpenAI-compatible API.
- `OLLAMA_BASE_URL`: local Ollama OpenAI-compatible API, usually `http://localhost:11434/v1`.
- Rule-based fallback: always available and requires no API key.

## Optional Settings

- `AI_PROVIDER=auto`
- `AI_MODEL=gemini-3.1-flash-lite`
- `AI_MAX_TOKENS=`
- `AI_TEMPERATURE=0.2`
- `GEMINI_THINKING_LEVEL=minimal`
- `GEMINI_ENABLE_GOOGLE_SEARCH=false`
- `OLLAMA_MODEL=`

## Behavior

- `auto` chooses the first configured provider in this free-first order: Gemini, Groq, Ollama, OpenRouter, Anthropic, rule-based fallback.
- Gemini defaults to `gemini-3.1-flash-lite` for low-cost/free-tier-first usage.
- Gemini Google Search grounding is disabled by default because search grounding can create billable tool usage. Set `GEMINI_ENABLE_GOOGLE_SEARCH=true` only when the user explicitly wants live web grounding.
- Missing keys never crash the app.
- Provider calls use compact prompt context.
- Prompt context shown in the UI is redacted.
- AI output is cleaned, validated, and disclosed before display.
- AI calls are button-triggered to control cost and rate limits.
