from __future__ import annotations

import os
from dataclasses import dataclass, field
from time import perf_counter
from typing import Any, Callable

from .ai_safety import ai_output_to_safe_markdown, redact_secrets

try:
    import requests
except Exception:  # pragma: no cover
    requests = None


DEFAULT_MODELS = {
    "anthropic": "claude-3-5-haiku-latest",
    "gemini": "gemini-3.1-flash-lite",
    "groq": "llama-3.1-8b-instant",
    "openrouter": "openrouter/auto",
    "ollama": "llama3.1",
    "rule_based": "deterministic-neutral-fallback",
}


@dataclass(frozen=True)
class AIProviderConfig:
    provider: str
    model: str
    available: bool
    env_var: str | None = None
    base_url: str | None = None
    warning: str | None = None
    is_local: bool = False
    is_free_mode: bool = False


@dataclass
class AIResponse:
    ok: bool
    provider: str
    model: str
    text: str
    usage: dict[str, Any] = field(default_factory=dict)
    latency_ms: float = 0.0
    error: str | None = None
    warning: str | None = None
    is_local: bool = False
    is_free_mode: bool = False
    source_status: dict[str, Any] = field(default_factory=dict)


def _env(name: str) -> str | None:
    value = os.getenv(name)
    return value if value else None


def _env_bool(name: str, default: bool = False) -> bool:
    value = _env(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _gemini_key() -> tuple[str | None, str]:
    key = _env("GEMINI_API_KEY")
    if key:
        return key, "GEMINI_API_KEY"
    key = _env("GOOGLE_API_KEY")
    if key:
        return key, "GOOGLE_API_KEY"
    return None, "GEMINI_API_KEY"


def _model(provider: str) -> str:
    explicit = _env("AI_MODEL")
    if explicit:
        return explicit
    if provider == "ollama":
        return _env("OLLAMA_MODEL") or DEFAULT_MODELS[provider]
    return DEFAULT_MODELS[provider]


def _max_tokens() -> int:
    try:
        return int(_env("AI_MAX_TOKENS") or "700")
    except ValueError:
        return 700


def _temperature() -> float:
    try:
        return float(_env("AI_TEMPERATURE") or "0.2")
    except ValueError:
        return 0.2


def list_available_ai_providers() -> list[AIProviderConfig]:
    ollama_base = _env("OLLAMA_BASE_URL")
    gemini_key, gemini_env = _gemini_key()
    providers = [
        AIProviderConfig(
            provider="anthropic",
            model=_model("anthropic"),
            available=bool(_env("ANTHROPIC_API_KEY")),
            env_var="ANTHROPIC_API_KEY",
            warning=None if _env("ANTHROPIC_API_KEY") else "Missing optional ANTHROPIC_API_KEY.",
        ),
        AIProviderConfig(
            provider="gemini",
            model=_model("gemini"),
            available=bool(gemini_key),
            env_var=gemini_env,
            warning=None if gemini_key else "Missing optional GEMINI_API_KEY or GOOGLE_API_KEY.",
            is_free_mode=True,
        ),
        AIProviderConfig(
            provider="groq",
            model=_model("groq"),
            available=bool(_env("GROQ_API_KEY")),
            env_var="GROQ_API_KEY",
            warning=None if _env("GROQ_API_KEY") else "Missing optional GROQ_API_KEY.",
            is_free_mode=True,
        ),
        AIProviderConfig(
            provider="openrouter",
            model=_model("openrouter"),
            available=bool(_env("OPENROUTER_API_KEY")),
            env_var="OPENROUTER_API_KEY",
            warning=None if _env("OPENROUTER_API_KEY") else "Missing optional OPENROUTER_API_KEY.",
            is_free_mode=True,
        ),
        AIProviderConfig(
            provider="ollama",
            model=_model("ollama"),
            available=bool(ollama_base),
            env_var="OLLAMA_BASE_URL",
            base_url=(ollama_base or "").rstrip("/") or None,
            warning=None if ollama_base else "Missing optional OLLAMA_BASE_URL.",
            is_local=True,
            is_free_mode=True,
        ),
        AIProviderConfig(
            provider="rule_based",
            model=DEFAULT_MODELS["rule_based"],
            available=True,
            warning="Offline deterministic fallback.",
            is_free_mode=True,
        ),
    ]
    return providers


def select_ai_provider(preferred: str = "auto") -> AIProviderConfig:
    preferred = (preferred or _env("AI_PROVIDER") or "auto").lower()
    providers = list_available_ai_providers()
    by_name = {provider.provider: provider for provider in providers}
    if preferred != "auto":
        selected = by_name.get(preferred)
        if selected is not None:
            return selected
        return by_name["rule_based"]
    for name in ["gemini", "groq", "ollama", "openrouter", "anthropic"]:
        candidate = by_name[name]
        if candidate.available:
            return candidate
    return by_name["rule_based"]


def _response(
    *,
    ok: bool,
    provider: str,
    model: str,
    text: str = "",
    usage: dict[str, Any] | None = None,
    latency_ms: float = 0.0,
    error: str | None = None,
    warning: str | None = None,
    is_local: bool = False,
    is_free_mode: bool = False,
) -> AIResponse:
    return AIResponse(
        ok=ok,
        provider=provider,
        model=model,
        text=ai_output_to_safe_markdown(text) if text else "",
        usage=usage or {},
        latency_ms=round(latency_ms, 2),
        error=redact_secrets(error),
        warning=redact_secrets(warning),
        is_local=is_local,
        is_free_mode=is_free_mode,
        source_status={
            "provider": provider,
            "model": model,
            "ok": ok,
            "local": is_local,
            "free_mode": is_free_mode,
            "warning": redact_secrets(warning),
            "error": redact_secrets(error),
        },
    )


def _missing(provider: str, env_var: str, *, is_local: bool = False, is_free_mode: bool = False) -> AIResponse:
    return _response(
        ok=False,
        provider=provider,
        model=_model(provider),
        error=f"Missing optional environment variable: {env_var}",
        warning=f"{provider} is unavailable because {env_var} is not configured.",
        is_local=is_local,
        is_free_mode=is_free_mode,
    )


def _post_json(url: str, payload: dict[str, Any], headers: dict[str, str] | None, *, timeout: int = 30) -> tuple[dict[str, Any] | None, str | None, float]:
    start = perf_counter()
    if requests is None:
        return None, "requests is not installed", 0.0
    try:
        response = requests.post(url, json=payload, headers=headers or {}, timeout=timeout)
        if response.status_code in {401, 403}:
            return None, f"{response.status_code} authentication or subscription required", (perf_counter() - start) * 1000
        if response.status_code == 429:
            return None, "429 rate limited", (perf_counter() - start) * 1000
        response.raise_for_status()
        return response.json(), None, (perf_counter() - start) * 1000
    except Exception as exc:
        return None, str(exc), (perf_counter() - start) * 1000


def _messages(system_prompt: str, user_prompt: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def call_anthropic(system_prompt: str, user_prompt: str, *, model: str | None = None) -> AIResponse:
    key = _env("ANTHROPIC_API_KEY")
    provider = "anthropic"
    model = model or _model(provider)
    if not key:
        return _missing(provider, "ANTHROPIC_API_KEY")
    payload = {
        "model": model,
        "max_tokens": _max_tokens(),
        "temperature": _temperature(),
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_prompt}],
    }
    headers = {"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
    data, error, latency = _post_json("https://api.anthropic.com/v1/messages", payload, headers)
    if error:
        return _response(ok=False, provider=provider, model=model, error=error, latency_ms=latency)
    content = data.get("content", []) if isinstance(data, dict) else []
    text = "\n".join(part.get("text", "") for part in content if isinstance(part, dict))
    return _response(ok=True, provider=provider, model=model, text=text, usage=data.get("usage", {}), latency_ms=latency)


def call_gemini(system_prompt: str, user_prompt: str, *, model: str | None = None) -> AIResponse:
    key, env_var = _gemini_key()
    provider = "gemini"
    model = model or _model(provider)
    if not key:
        return _missing(provider, env_var, is_free_mode=True)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    payload = {
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
        "generationConfig": {"temperature": _temperature(), "maxOutputTokens": _max_tokens()},
    }
    if str(model).startswith("gemini-3"):
        payload["generationConfig"]["thinkingConfig"] = {
            "thinkingLevel": (_env("GEMINI_THINKING_LEVEL") or "minimal").lower()
        }
    if _env_bool("GEMINI_ENABLE_GOOGLE_SEARCH", False):
        payload["tools"] = [{"google_search": {}}]
    data, error, latency = _post_json(url, payload, {"x-goog-api-key": key, "Content-Type": "application/json"})
    if error:
        return _response(ok=False, provider=provider, model=model, error=error, latency_ms=latency, is_free_mode=True)
    candidates = data.get("candidates", []) if isinstance(data, dict) else []
    text = ""
    if candidates:
        parts = candidates[0].get("content", {}).get("parts", [])
        text = "\n".join(part.get("text", "") for part in parts if isinstance(part, dict))
    return _response(ok=True, provider=provider, model=model, text=text, usage=data.get("usageMetadata", {}), latency_ms=latency, is_free_mode=True)


def _call_openai_compatible(
    provider: str,
    url: str,
    key: str | None,
    system_prompt: str,
    user_prompt: str,
    *,
    model: str | None = None,
    is_local: bool = False,
    is_free_mode: bool = False,
    headers: dict[str, str] | None = None,
) -> AIResponse:
    model = model or _model(provider)
    if not key and not is_local:
        env_var = {"groq": "GROQ_API_KEY", "openrouter": "OPENROUTER_API_KEY"}.get(provider, "API_KEY")
        return _missing(provider, env_var, is_local=is_local, is_free_mode=is_free_mode)
    request_headers = headers or {}
    if key:
        request_headers["Authorization"] = f"Bearer {key}"
    request_headers["Content-Type"] = "application/json"
    payload = {
        "model": model,
        "messages": _messages(system_prompt, user_prompt),
        "temperature": _temperature(),
        "max_tokens": _max_tokens(),
    }
    data, error, latency = _post_json(url, payload, request_headers)
    if error:
        return _response(ok=False, provider=provider, model=model, error=error, latency_ms=latency, is_local=is_local, is_free_mode=is_free_mode)
    choices = data.get("choices", []) if isinstance(data, dict) else []
    text = choices[0].get("message", {}).get("content", "") if choices else ""
    return _response(ok=True, provider=provider, model=model, text=text, usage=data.get("usage", {}), latency_ms=latency, is_local=is_local, is_free_mode=is_free_mode)


def call_groq(system_prompt: str, user_prompt: str, *, model: str | None = None) -> AIResponse:
    return _call_openai_compatible(
        "groq",
        "https://api.groq.com/openai/v1/chat/completions",
        _env("GROQ_API_KEY"),
        system_prompt,
        user_prompt,
        model=model,
        is_free_mode=True,
    )


def call_openrouter(system_prompt: str, user_prompt: str, *, model: str | None = None) -> AIResponse:
    return _call_openai_compatible(
        "openrouter",
        "https://openrouter.ai/api/v1/chat/completions",
        _env("OPENROUTER_API_KEY"),
        system_prompt,
        user_prompt,
        model=model,
        is_free_mode=True,
        headers={"HTTP-Referer": "https://localhost", "X-Title": "Global Market Analyst Terminal"},
    )


def call_ollama(system_prompt: str, user_prompt: str, *, model: str | None = None) -> AIResponse:
    base_url = (_env("OLLAMA_BASE_URL") or "").rstrip("/")
    provider = "ollama"
    if not base_url:
        return _missing(provider, "OLLAMA_BASE_URL", is_local=True, is_free_mode=True)
    return _call_openai_compatible(
        provider,
        f"{base_url}/chat/completions",
        None,
        system_prompt,
        user_prompt,
        model=model or _model(provider),
        is_local=True,
        is_free_mode=True,
    )


def call_rule_based_fallback(system_prompt: str = "", user_prompt: str = "", *, context: Any = None, model: str | None = None) -> AIResponse:
    provider = "rule_based"
    pieces = []
    if isinstance(context, dict):
        gaps = context.get("data_gaps") or context.get("source_status") or "Data gaps are listed where providers are unavailable."
        pieces = [
            "Evidence: Structured dashboard metrics are available for review.",
            "Risks: Elevated volatility, missing providers, or stale source status can reduce confidence.",
            f"Uncertainty: {gaps}",
            "Watch-points: Monitor source freshness, volatility regime, breadth, leverage, and event severity.",
            "Data gaps: Optional paid or local providers may be unavailable in free mode.",
        ]
    else:
        source = str(context or user_prompt or "No context supplied.")[:900]
        pieces = [
            "Evidence: Offline neutral fallback used because no configured LLM provider was selected.",
            "Risks: Summary depth is limited to the compact structured context.",
            "Uncertainty: Provider availability and source freshness should be checked.",
            f"Watch-points: {source}",
            "Data gaps: No external AI provider response was used.",
        ]
    return _response(
        ok=True,
        provider=provider,
        model=model or DEFAULT_MODELS[provider],
        text="\n".join(f"- {piece}" for piece in pieces),
        warning="Rule-based fallback used; no paid API required.",
        is_free_mode=True,
    )


PROVIDER_CALLS: dict[str, Callable[[str, str], AIResponse]] = {
    "anthropic": call_anthropic,
    "gemini": call_gemini,
    "groq": call_groq,
    "openrouter": call_openrouter,
    "ollama": call_ollama,
}


def call_ai_model(system_prompt: str, user_prompt: str, *, preferred: str = "auto", context: Any = None) -> AIResponse:
    config = select_ai_provider(preferred)
    if config.provider == "rule_based":
        return call_rule_based_fallback(system_prompt, user_prompt, context=context, model=config.model)
    caller = PROVIDER_CALLS.get(config.provider)
    if caller is None:
        return call_rule_based_fallback(system_prompt, user_prompt, context=context)
    if not config.available:
        return _response(
            ok=False,
            provider=config.provider,
            model=config.model,
            error=config.warning or "Provider unavailable.",
            warning=config.warning,
            is_local=config.is_local,
            is_free_mode=config.is_free_mode,
        )
    return caller(system_prompt, user_prompt)
