from __future__ import annotations

from typing import Any

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None

from .no_key_provider_catalog import list_no_key_providers


def build_free_api_key_checklist() -> list[dict[str, Any]]:
    rows = []
    for provider in list_no_key_providers():
        rows.append(
            {
                "provider": provider["name"],
                "purpose": provider["purpose"],
                "env_var": provider.get("env_var", ""),
                "setup_steps": "Create or edit .env, add the blank placeholder only, then insert your local key if you have one.",
                "key_required": provider["key_required"],
                "no_key_fallback": provider["no_key_fallback"],
                "pages": ", ".join(provider["pages"]),
                "caveat": provider["caveat"],
            }
        )
    return rows


def build_free_api_setup_table():
    rows = build_free_api_key_checklist()
    return pd.DataFrame(rows) if pd is not None else rows


def build_environment_setup_notes() -> list[str]:
    return [
        "The app loads .env through python-dotenv at runtime.",
        "VS Code terminal env injection is optional; enable python.terminal.useEnvFile if you want terminals to inherit .env.",
        ".env and .streamlit/secrets.toml must stay local and are excluded from release archives.",
        "Provider Center displays configured or missing_key status without full secret values.",
    ]
