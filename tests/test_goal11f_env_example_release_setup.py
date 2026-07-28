from __future__ import annotations

import re
import zipfile
from pathlib import Path

from scripts.build_release_zip import ROOT, build_release, iter_release_files

EXPECTED_PROVIDER_NAMES = {
    "FRED_API_KEY",
    "EIA_API_KEY",
    "BLS_API_KEY",
    "NASA_FIRMS_MAP_KEY",
    "AISSTREAM_API_KEY",
    "OPENSKY_CLIENT_ID",
    "OPENSKY_CLIENT_SECRET",
    "COINGECKO_API_KEY",
    "ALPHAVANTAGE_API_KEY",
    "ALPHA_VANTAGE_API_KEY",
    "FINNHUB_API_KEY",
    "BOK_ECOS_API_KEY",
    "OPENDART_API_KEY",
    "KOSIS_API_KEY",
    "KRX_API_KEY",
    "SEC_USER_AGENT",
    "NWS_USER_AGENT",
    "GEMINI_API_KEY",
    "AI_PROVIDER",
    "AI_MODEL",
    "GEMINI_THINKING_LEVEL",
    "GEMINI_ENABLE_GOOGLE_SEARCH",
    "WATCHLIST_BACKGROUND_REFRESH_ENABLED",
    "WATCHLIST_REFRESH_KILL_SWITCH",
    "WATCHLIST_REFRESH_INTERVAL_SECONDS",
    "WATCHLIST_CHANGE_ALERT_KILL_SWITCH",
    "GLOBAL_TERMINAL_AUTH_PROVIDER",
    "GLOBAL_TERMINAL_LOCAL_AUTH_ENABLED",
    "GLOBAL_TERMINAL_SESSION_TTL_SECONDS",
    "GLOBAL_TERMINAL_COOKIE_SECURE",
    "GLOBAL_TERMINAL_ACCOUNT_DB_PATH",
    "SUPABASE_URL",
    "SUPABASE_PUBLISHABLE_KEY",
    "SUPABASE_SECRET_KEY",
    "SUPABASE_ANON_KEY",
    "SUPABASE_SERVICE_ROLE_KEY",
}

EXPECTED_SAFE_CONFIG_DEFAULTS = {
    "GLOBAL_TERMINAL_ALERT_WORKER_ENABLED": "false",
    "GLOBAL_TERMINAL_ALERT_WORKER_OBSERVE_ENABLED": "false",
    "GLOBAL_TERMINAL_ALERT_WORKER_INTERVAL_SECONDS": "300",
    "GLOBAL_TERMINAL_HOSTED_AUTH_ENABLED": "false",
    "GLOBAL_TERMINAL_HOSTED_SESSION_TTL_SECONDS": "86400",
    "GLOBAL_TERMINAL_ACCOUNT_CONTINUITY_ENABLED": "false",
    "GLOBAL_TERMINAL_SUPABASE_TIMEOUT_SECONDS": "8",
    "GLOBAL_TERMINAL_HOSTED_SCHEDULER_ENABLED": "false",
    "GLOBAL_TERMINAL_HOSTED_SCHEDULER_KILL_SWITCH": "true",
    "GLOBAL_TERMINAL_HOSTED_SCHEDULER_VERIFIED": "false",
    "GLOBAL_TERMINAL_HOSTED_SCHEDULER_EVIDENCE_PATH": "",
    "GLOBAL_TERMINAL_HOSTED_SCHEDULER_EVIDENCE_MAX_AGE_HOURS": "168",
    "GLOBAL_TERMINAL_HOSTED_SCHEDULER_LEASE_SECONDS": "120",
}


def test_goal11f_env_example_exists_and_is_placeholder_only():
    path = ROOT / ".env.example"
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    for name in EXPECTED_PROVIDER_NAMES:
        assert f"{name}=" in text
    for name, value in EXPECTED_SAFE_CONFIG_DEFAULTS.items():
        assert f"{name}={value}" in text
    for line in text.splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        assert key in EXPECTED_PROVIDER_NAMES | EXPECTED_SAFE_CONFIG_DEFAULTS.keys()
        expected = EXPECTED_SAFE_CONFIG_DEFAULTS.get(key, "")
        assert value.strip() == expected
    assert not re.search(r"sk-[A-Za-z0-9]", text)
    assert "@" not in "\n".join(line for line in text.splitlines() if not line.startswith("#"))


def test_goal11f_env_example_included_but_real_env_files_excluded():
    names = {path.relative_to(ROOT).as_posix() for path in iter_release_files()}
    assert ".env.example" in names
    assert ".env" not in names
    assert ".env.local" not in names
    assert ".env.production" not in names
    zip_path, manifest = build_release()
    with zipfile.ZipFile(zip_path) as archive:
        archive_names = set(archive.namelist())
    assert ".env.example" in archive_names
    assert ".env" not in archive_names
    assert ".env.local" not in archive_names
    assert ".env.production" not in archive_names
    assert ".env.example" in manifest["files"]
