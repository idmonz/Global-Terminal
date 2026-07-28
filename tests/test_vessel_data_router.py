from __future__ import annotations

from lib.vessel_data_router import build_aisstream_status, build_noaa_accessais_status, build_vessel_data_status, route_vessel_data


def test_vessel_data_router_requires_successful_live_probe():
    assert build_noaa_accessais_status()["status"] == "historical-only"
    assert build_aisstream_status(api_key_present=True, probe_ok=False)["live"] is False
    assert build_aisstream_status(api_key_present=True, probe_ok=True)["live"] is True
    assert route_vessel_data("AISStream", [{"lat": 1}], provider_status={"live": False, "ok": False})["rows"] == []
    assert len(build_vessel_data_status()) == 2
