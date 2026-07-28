from __future__ import annotations

import zipfile
from pathlib import Path

import pytest


def tmpdb(tmp_path):
    return tmp_path / "research_workspace.db"

