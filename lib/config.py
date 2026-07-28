from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .env_loader import get_env_var, load_project_env


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
STATIC_DIR = ROOT_DIR / "static"
CACHE_DIR = DATA_DIR / "cache"
INDEX_CONSTITUENTS_DIR = STATIC_DIR / "index_constituents"

DISCLOSURE = (
    "This dashboard is for educational and informational purposes only. "
    "It is not financial advice, not a recommendation to buy or sell any security, "
    "and is not personalized to your situation. Consult a licensed advisor before making investment decisions."
)

AI_DISCLOSURE = "AI summary; verify with primary data. Not financial advice."


load_project_env(ROOT_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    anthropic_api_key: str | None = None
    fred_api_key: str | None = None
    eia_api_key: str | None = None
    world_monitor_key: str | None = None
    world_monitor_base_url: str | None = None
    coinglass_api_key: str | None = None
    coinmarketcap_api_key: str | None = None
    alphavantage_api_key: str | None = None
    finnhub_api_key: str | None = None
    polygon_api_key: str | None = None
    newsapi_key: str | None = None
    gemini_api_key: str | None = None
    groq_api_key: str | None = None
    openrouter_api_key: str | None = None
    ollama_base_url: str | None = None
    ollama_model: str | None = None
    ai_provider: str = "auto"
    ai_model: str | None = None
    ai_max_tokens: str | None = None
    ai_temperature: str = "0.2"
    gdelt_enabled: bool = True
    binance_base_url: str = "https://fapi.binance.com"


def get_settings() -> Settings:
    return Settings(
        anthropic_api_key=get_env_var("ANTHROPIC_API_KEY"),
        fred_api_key=get_env_var("FRED_API_KEY"),
        eia_api_key=get_env_var("EIA_API_KEY"),
        world_monitor_key=get_env_var("WORLD_MONITOR_KEY"),
        world_monitor_base_url=get_env_var("WORLD_MONITOR_BASE_URL"),
        coinglass_api_key=get_env_var("COINGLASS_API_KEY"),
        coinmarketcap_api_key=get_env_var("COINMARKETCAP_API_KEY"),
        alphavantage_api_key=get_env_var("ALPHAVANTAGE_API_KEY") or get_env_var("ALPHA_VANTAGE_API_KEY"),
        finnhub_api_key=get_env_var("FINNHUB_API_KEY"),
        polygon_api_key=get_env_var("POLYGON_API_KEY"),
        newsapi_key=get_env_var("NEWSAPI_KEY"),
        gemini_api_key=get_env_var("GEMINI_API_KEY"),
        groq_api_key=get_env_var("GROQ_API_KEY"),
        openrouter_api_key=get_env_var("OPENROUTER_API_KEY"),
        ollama_base_url=get_env_var("OLLAMA_BASE_URL"),
        ollama_model=get_env_var("OLLAMA_MODEL"),
        ai_provider=get_env_var("AI_PROVIDER", "auto") or "auto",
        ai_model=get_env_var("AI_MODEL"),
        ai_max_tokens=get_env_var("AI_MAX_TOKENS"),
        ai_temperature=get_env_var("AI_TEMPERATURE", "0.2") or "0.2",
        gdelt_enabled=(get_env_var("GDELT_ENABLED", "true") or "true").lower() == "true",
        binance_base_url=get_env_var("BINANCE_BASE_URL", "https://fapi.binance.com") or "https://fapi.binance.com",
    )


def load_environment() -> None:
    load_project_env(ROOT_DIR / ".env")


def get_config() -> Settings:
    settings = get_settings()
    return Settings(
        anthropic_api_key=settings.anthropic_api_key,
        fred_api_key=settings.fred_api_key,
        eia_api_key=settings.eia_api_key,
        world_monitor_key=settings.world_monitor_key,
        world_monitor_base_url=(settings.world_monitor_base_url or "").rstrip("/") or None,
        coinglass_api_key=settings.coinglass_api_key,
        coinmarketcap_api_key=settings.coinmarketcap_api_key,
        alphavantage_api_key=settings.alphavantage_api_key,
        finnhub_api_key=settings.finnhub_api_key,
        polygon_api_key=settings.polygon_api_key,
        newsapi_key=settings.newsapi_key,
        gemini_api_key=settings.gemini_api_key,
        groq_api_key=settings.groq_api_key,
        openrouter_api_key=settings.openrouter_api_key,
        ollama_base_url=(settings.ollama_base_url or "").rstrip("/") or None,
        ollama_model=settings.ollama_model,
        ai_provider=settings.ai_provider,
        ai_model=settings.ai_model,
        ai_max_tokens=settings.ai_max_tokens,
        ai_temperature=settings.ai_temperature,
        gdelt_enabled=settings.gdelt_enabled,
        binance_base_url=settings.binance_base_url.rstrip("/"),
    )


def ensure_runtime_dirs() -> None:
    for path in (DATA_DIR, STATIC_DIR, CACHE_DIR, INDEX_CONSTITUENTS_DIR):
        path.mkdir(parents=True, exist_ok=True)


def missing_optional_keys() -> dict[str, bool]:
    settings = get_settings()
    return {
        "ANTHROPIC_API_KEY": settings.anthropic_api_key is None,
        "FRED_API_KEY": settings.fred_api_key is None,
        "EIA_API_KEY": settings.eia_api_key is None,
        "WORLD_MONITOR_KEY": settings.world_monitor_key is None,
        "WORLD_MONITOR_BASE_URL": settings.world_monitor_base_url is None,
        "COINGLASS_API_KEY": settings.coinglass_api_key is None,
        "COINMARKETCAP_API_KEY": settings.coinmarketcap_api_key is None,
        "ALPHAVANTAGE_API_KEY": settings.alphavantage_api_key is None,
        "FINNHUB_API_KEY": settings.finnhub_api_key is None,
        "GEMINI_API_KEY": settings.gemini_api_key is None,
        "GROQ_API_KEY": settings.groq_api_key is None,
        "OPENROUTER_API_KEY": settings.openrouter_api_key is None,
        "OLLAMA_BASE_URL": settings.ollama_base_url is None,
    }


ensure_runtime_dirs()
