"""
@file tests/python/big/conftest.py
@brief Global pytest configuration and shared fixtures for lotm integration tests.

Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
Part of the Lord of the Mods (lotm) project.
SPDX-License-Identifier: GPL-3.0-or-later
"""

import pytest
import pathlib


@pytest.fixture
def standard_mod_directory(tmp_path: pathlib.Path) -> pathlib.Path:
    """
    Provisions an isolated, standardized directory structure simulating a mod workspace.
    """
    src_dir = tmp_path / "mod_source"
    src_dir.mkdir()

    # Create nested directories and files
    (src_dir / "data").mkdir()
    (src_dir / "data" / "weapon.ini").write_text("Damage=50", encoding="utf-8")
    (src_dir / "art").mkdir()
    (src_dir / "art" / "texture.dds").write_bytes(b"DDS_HEADER_DATA")
    (src_dir / "readme.txt").write_text("Lord of the Mods", encoding="utf-8")

    return src_dir
