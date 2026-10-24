"""
@file tests/python/big/test_cli.py
@brief Tests for the command-line interface wrappers of the BIG archive tools.

Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
Part of the Lord of the Mods (lotm) project.
SPDX-License-Identifier: GPL-3.0-or-later
"""

import pytest
import sys
from pathlib import Path

import scripts.big_pack as big_pack
import scripts.big_unpack as big_unpack


def test_cli_pack_successful_execution_returns_zero(standard_mod_directory: Path, tmp_path: Path, monkeypatch, capsys):
    """Verify standard packing command exits cleanly and outputs success message."""
    out_big = tmp_path / "cli_test.big"
    monkeypatch.setattr(sys, "argv", ["big_pack", str(standard_mod_directory), "-o", str(out_big)])

    big_pack.main()

    stdout, stderr = capsys.readouterr()
    assert out_big.exists()
    assert "Finished packing" in stdout
    assert stderr == ""

def test_cli_pack_invalid_source_returns_nonzero(tmp_path: Path, monkeypatch, capsys):
    """Verify packing a missing directory exits with code 1 and writes to stderr."""
    missing_dir = tmp_path / "void"
    monkeypatch.setattr(sys, "argv", ["big_pack", str(missing_dir)])

    with pytest.raises(SystemExit) as exc:
        big_pack.main()

    assert exc.value.code == 1
    stdout, stderr = capsys.readouterr()
    assert "Error: Source directory" in stderr


def test_cli_unpack_successful_execution_returns_zero(standard_mod_directory: Path, tmp_path: Path, monkeypatch, capsys):
    """Verify standard unpacking command exits cleanly."""
    archive = tmp_path / "ready.big"
    extract_dir = tmp_path / "extracted"

    # Pre-pack an archive using the API to test the CLI unpacker
    big_pack.pack(standard_mod_directory, archive)

    monkeypatch.setattr(sys, "argv", ["big_unpack", str(archive), "-o", str(extract_dir)])

    big_unpack.main()

    stdout, stderr = capsys.readouterr()
    assert (extract_dir / "data" / "weapon.ini").exists()
    assert "Loaded 2 entries" in stdout
    assert stderr == ""


def test_cli_unpack_missing_archive_returns_nonzero(tmp_path: Path, monkeypatch, capsys):
    """Verify unpacking a missing archive exits with code 1 and writes to stderr."""
    missing_file = tmp_path / "void.big"
    monkeypatch.setattr(sys, "argv", ["big_unpack", str(missing_file)])

    with pytest.raises(SystemExit) as exc:
        big_unpack.main()

    assert exc.value.code == 1
    stdout, stderr = capsys.readouterr()
    assert "Extraction failed" in stderr
    assert "Archive not found" in stderr
