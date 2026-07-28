from lib.layer_catalog_time_controls import build_layer_catalog, filter_layers_by_preset


def test_goal11d_layer_metadata_has_worldview_style_fields():
    catalog = build_layer_catalog(["osint", "provider"])
    assert catalog["layers"]
    required = {"layer_id", "display_name", "source", "source_type", "freshness", "temporal_coverage", "spatial_coverage", "update_frequency", "caveat", "enabled", "requires_key", "historical_only", "provider_status"}
    for row in catalog["layers"]:
        assert required <= set(row)
    filtered = filter_layers_by_preset(catalog, ["osint"])
    enabled_types = {row["source_type"] for row in filtered["layers"] if row["enabled"]}
    assert enabled_types == {"osint"}
