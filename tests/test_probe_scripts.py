from __future__ import annotations

import subprocess
import sys


def test_probe_script_supports_dry_run():
    result = subprocess.run([sys.executable, "scripts/run_provider_probes.py", "--dry-run", "coingecko_public"], capture_output=True, text=True, check=True)
    assert "coingecko_public" in result.stdout
