# OpenBB Real Probe

`lib/openbb_real_probe.py` adds optional probes:

- installation probe
- endpoint path probe
- sample query probe
- financial, macro, options, and screener probe bundles

Probes are safe when OpenBB is missing and are intended for button-triggered diagnostics in `pages/18_OpenBB_Data_Hub.py`.

No heavy OpenBB query runs on import or page load.
# Goal 10 Update

`run_openbb_installation_probe()` is exposed from `lib.openbb_bridge` as a compatibility probe. Goal 10 also adds `lib.provider_probe_runner` for non-OpenBB provider diagnostics. Both paths are optional and safe without OpenBB installed.
