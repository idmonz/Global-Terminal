import zipfile
from pathlib import Path
from scripts.build_release_zip import build_release


def test_goal12d_release_hygiene_excludes_private_external_and_cases():
    zip_path, manifest = build_release()
    names = manifest['files']
    assert '.env.example' in names
    assert 'lib/options_research_case_store.py' in names
    assert 'lib/options_surface_price_checks.py' in names
    assert all(not name.startswith('data/private/') for name in names)
    assert all('options_cases' not in name for name in names)
    assert all(not name.startswith('external/') for name in names)
    with zipfile.ZipFile(zip_path) as z:
        z_names = z.namelist()
    assert 'release_manifest.json' in z_names
    assert all('options_cases' not in name for name in z_names)
    assert all('external/' not in name for name in z_names)
