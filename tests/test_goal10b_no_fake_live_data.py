from __future__ import annotations

from lib.osint_map_layers import get_osint_layer
from lib.vessel_data_router import build_aisstream_status, build_noaa_accessais_status


def test_goal10b_no_fake_live_data_for_ais_flights_or_firms():
    assert build_noaa_accessais_status()["live"] is False
    assert build_aisstream_status(api_key_present=True, probe_ok=False)["live"] is False
    assert get_osint_layer("opensky")["live"] is False
    assert get_osint_layer("nasa_firms")["freshness"] == "missing-key"
