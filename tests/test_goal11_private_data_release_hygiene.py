import zipfile
from scripts.build_release_zip import build_release, iter_release_files


def test_goal11_private_data_and_external_excluded_from_release():
    names = [p.as_posix() for p in iter_release_files()]
    assert not any("data/private" in name or name.endswith(".db") or name.endswith(".sqlite") or name.endswith(".sqlite3") for name in names)
    zip_path, manifest = build_release()
    with zipfile.ZipFile(zip_path) as archive:
        zip_names = archive.namelist()
    forbidden = ["external/", "agent-skills-main", "OpenBB-develop", "worldmonitor-main", "OpenStock", "OpenAlice", "osiris", "optlib", "quant-traderr"]
    assert not any(any(token in name for token in forbidden) for name in zip_names)
    assert ".gitignore" in zip_names

