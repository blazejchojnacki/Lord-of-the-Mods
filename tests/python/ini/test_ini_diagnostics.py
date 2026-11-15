"""
@file tests/python/ini/test_ini_diagnostics.py
@brief Unit tests for lotm.ini.diagnostics (scan_ini, inspect_ini, and IniInspectionReport).

Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
Part of the Lord of the Mods (lotm) project.
SPDX-License-Identifier: GPL-3.0-or-later
"""

from __future__ import annotations

from pathlib import Path
import pytest

import lotm.ini as ini


def test_scan_ini_across_files_and_directories(
    tmp_path: Path,
    sample_ini_file: Path,
    malformed_ini_file: Path,
    ini_mod_directory: Path,
) -> None:
    """Verify scan_ini across missing paths, single files, and directory trees."""
    # scan_ini on missing path
    with pytest.raises(ini.IniParseError, match="Target path does not exist"):
        ini.scan_ini(tmp_path / "nonexistent_dir")

    # scan_ini on single file (non-strict and strict)
    single_scan = ini.scan_ini(sample_ini_file, strict=True)
    assert single_scan == {sample_ini_file: []}

    broken_scan = ini.scan_ini(malformed_ini_file, strict=False)
    assert len(broken_scan[malformed_ini_file]) == 2

    with pytest.raises(ini.IniParseError):
        ini.scan_ini(malformed_ini_file, strict=True)

    # scan_ini on directory
    dir_scan = ini.scan_ini(ini_mod_directory, strict=True)
    assert len(dir_scan) == 3
    assert all(errs == [] for errs in dir_scan.values())


def test_inspect_ini_across_ini_str_and_buffers(
    sample_ini_file: Path,
    sample_str_file: Path,
) -> None:
    """Verify inspect_ini report fields across .ini, .str, and binary Buffer inputs."""
    # inspect_ini on .ini (contains CommentNode, IncludeNode, ScriptNode, ConstructLevel)
    ini_report = ini.inspect_ini(sample_ini_file, strict=True)
    assert ini_report.file_type == ".ini"
    assert ini_report.start_level == 0
    assert ini_report.define_count == 1
    assert ini_report.include_count == 2
    assert ini_report.block_counts == {"BeginScript": 1, "Object": 1}
    assert ini_report.errors == []

    # inspect_ini on binary Buffer
    buf_report = ini.inspect_ini(
        "weapon.ini",
        strict=True,
        file_content=b"Weapon GondorSword\n    Damage = 40\nEnd\n",
    )
    assert buf_report.block_counts == {"Weapon": 1}

    # inspect_ini on .str (contains CommentNode and StrEntry)
    str_report = ini.inspect_ini(sample_str_file, strict=True)
    assert str_report.file_type == ".str"
    assert str_report.block_counts == {"OBJECT": 1, "GUI": 1}

    # inspect_ini on file with standalone statement
    no_block_report = ini.inspect_ini(
        "extensionless.ini",
        file_content="StandaloneStmt = 1\n",
    )
    assert no_block_report.block_counts == {}
    assert no_block_report.total_top_level_items == 1
