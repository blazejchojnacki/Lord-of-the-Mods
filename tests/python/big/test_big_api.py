"""
@file tests/test_big_api.py
@brief Integration tests for the programmatic Python API of the BIG archive module.

Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
Part of the Lord of the Mods (lotm) project.
SPDX-License-Identifier: GPL-3.0-or-later
"""

import pytest
from pathlib import Path

# Assuming the project root is in PYTHONPATH or pytest is run from the root
import scripts.big_pack as big_pack
import scripts.big_unpack as big_unpack


def test_programmatic_packing_and_unpacking_roundtrip(standard_mod_directory: Path, tmp_path: Path):
    """Verify that packing and unpacking a directory maintains structural and byte fidelity."""
    archive_path = tmp_path / "mod_test.big"
    extract_dir = tmp_path / "output_dir"

    # Pack the standard fixture directory
    big_pack.pack(standard_mod_directory, archive_path)
    assert archive_path.is_file()
    assert archive_path.stat().st_size > 0

    # Unpack the generated archive
    entries = big_unpack.unpack(archive_path, extract_dir)

    # Verify returned entries list
    assert len(entries) == 3
    names = [e.name for e in entries]
    assert "art\\texture.dds" in names
    assert "data\\weapon.ini" in names
    assert "readme.txt" in names

    # Verify extracted file fidelity
    extracted_ini = extract_dir / "data" / "weapon.ini"
    assert extracted_ini.exists()
    assert extracted_ini.read_text(encoding="utf-8") == "Damage=50"


def test_pack_invalid_source_directory_raises_error(tmp_path: Path):
    """Verify that pack() raises NotADirectoryError when given a non-existent path."""
    missing_dir = tmp_path / "does_not_exist"
    out_file = tmp_path / "out.big"

    with pytest.raises(NotADirectoryError, match="does not exist"):
        big_pack.pack(missing_dir, out_file)


def test_unpack_missing_archive_raises_error(tmp_path: Path):
    """Verify that unpack() raises FileNotFoundError when target archive is missing."""
    missing_file = tmp_path / "ghost.big"
    out_dir = tmp_path / "out"

    with pytest.raises(FileNotFoundError, match="Archive not found"):
        big_unpack.unpack(missing_file, out_dir)
