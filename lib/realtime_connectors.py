from __future__ import annotations

from typing import Any, Callable

from .live_feeds import (
    AIS_UNAVAILABLE_MESSAGE,
    FLIGHT_UNAVAILABLE_MESSAGE,
    fetch_gdelt_feed,
    fetch_rss_feed,
    fetch_usgs_earthquakes,
)
from .provider_registry import provider_env_status


def connect_binance_websocket_optional(symbol: str = "btcusdt", connector: Callable[..., Any] | None = None) -> dict[str, Any]:
    if connector is None:
        return {"provider": "binance_futures", "symbol": symbol, "connected": False, "status": "not_started", "caveat": "Websocket connector is optional and not started on app launch."}
    connection = connector(symbol)
    return {"provider": "binance_futures", "symbol": symbol, "connected": True, "connection": connection, "status": "connected", "caveat": "Public stream subject to provider limits."}


def connect_aisstream_optional(connector: Callable[..., Any] | None = None) -> dict[str, Any]:
    env = provider_env_status("aisstream")
    if not env["configured"]:
        return {"provider": "aisstream", "connected": False, "status": "unavailable", "warning": AIS_UNAVAILABLE_MESSAGE, "caveat": "No live vessel flow is claimed."}
    if connector is None:
        return {"provider": "aisstream", "connected": False, "status": "configured_not_started", "caveat": "AIS stream is optional and must be started explicitly."}
    return {"provider": "aisstream", "connected": True, "connection": connector(), "status": "connected", "caveat": "Live AIS unavailable unless the provider stream remains connected and tested."}


def connect_opensky_optional(connector: Callable[..., Any] | None = None) -> dict[str, Any]:
    env = provider_env_status("opensky")
    if not env["configured"]:
        return {"provider": "opensky", "connected": False, "status": "unavailable", "warning": FLIGHT_UNAVAILABLE_MESSAGE, "caveat": "No live flight tracking is claimed."}
    if connector is None:
        return {"provider": "opensky", "connected": False, "status": "configured_not_started", "caveat": "Flight connector is optional and must be started explicitly."}
    return {"provider": "opensky", "connected": True, "connection": connector(), "status": "connected", "caveat": "Live flight data is provider-dependent."}


def poll_rss_sources(urls: list[str], parser=None):
    return fetch_rss_feed(urls, parser=parser)


def poll_gdelt(query: str = "geopolitical risk", requester=None):
    return fetch_gdelt_feed(query, requester=requester)


def poll_usgs_earthquakes(requester=None):
    return fetch_usgs_earthquakes(requester=requester)


def normalize_realtime_event(event: dict[str, Any]) -> dict[str, Any]:
    return {
        "event_id": event.get("event_id") or event.get("id") or event.get("url") or event.get("title"),
        "title": event.get("title") or event.get("name") or "Realtime event",
        "domain": event.get("domain") or event.get("provider") or "unknown",
        "severity": event.get("severity") or "watch",
        "lat": event.get("lat"),
        "lon": event.get("lon"),
        "source": event.get("source") or event.get("provider") or "optional feed",
        "freshness": event.get("freshness") or "fresh",
        "caveat": event.get("caveat") or "Realtime event normalized from optional provider payload.",
    }


def safe_close_connection(connection: Any) -> bool:
    if connection is None:
        return True
    close = getattr(connection, "close", None)
    if callable(close):
        close()
    return True
