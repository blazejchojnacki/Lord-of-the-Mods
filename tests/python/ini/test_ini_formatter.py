"""
@file tests/python/ini/test_ini_formatter.py
@brief Unit tests for lotm.ini.formatter (format_ini and atomic sibling writes).

Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
Part of the Lord of the Mods (lotm) project.
SPDX-License-Identifier: GPL-3.0-or-later
"""

from __future__ import annotations

import os
from pathlib import Path
import pytest

import lotm.ini as ini


def test_format_ini_in_memory_string_and_buffer() -> None:
    """Verify format_ini without output_path across string and binary Buffer inputs."""
    # format_ini without output_path (both str and Buffer)
    formatted_str = ini.format_ini(
        "inline.ini",
        file_content="Armor A\nArmor = DEFAULT 10%\nEnd\n",
    )
    assert "    Armor = DEFAULT 10%\n" in formatted_str

    formatted_buf = ini.format_ini(
        "inline.ini",
        file_content=b"Armor A\nArmor = DEFAULT 10%\nEnd\n",
    )
    assert formatted_buf == formatted_str


def test_format_ini_atomic_file_output_and_cleanup_on_failure(
    tmp_path: Path,
    sample_ini_file: Path,
    malformed_ini_file: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify format_ini writes atomically to disk and cleans up .lotm_tmp on failure."""
    # format_ini with output_path creating parent directory
    out_formatted = tmp_path / "formatted_out" / "hero.ini"
    ini.format_ini(sample_ini_file, output_path=out_formatted, strict=True)
    assert out_formatted.is_file()

    # format_ini in strict mode rejects malformed input before creating output file
    strict_fail_dest = tmp_path / "formatted_out" / "strict_fail.ini"
    with pytest.raises(ini.IniParseError):
        ini.format_ini(malformed_ini_file, output_path=strict_fail_dest, strict=True)
    assert not strict_fail_dest.exists()

    # format_ini atomic write cleanup when os.replace fails
    fail_dest = tmp_path / "formatted_out" / "atomic_fail.ini"
    tmp_sibling = fail_dest.with_name(f".{fail_dest.name}.lotm_tmp")

    def _mock_replace_fail(src: os.PathLike[str], dst: os.PathLike[str]) -> None:
        raise OSError("Simulated atomic rename failure")

    with monkeypatch.context() as m:
        m.setattr(os, "replace", _mock_replace_fail)
        with pytest.raises(OSError, match="Simulated atomic rename failure"):
            ini.format_ini(sample_ini_file, output_path=fail_dest, strict=True)

    assert not tmp_sibling.exists()
    assert not fail_dest.exists()
