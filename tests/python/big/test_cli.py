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


def test_cli_pack_successful_execution(standard_mod_directory: Path, tmp_path: Path, monkeypatch):
    """Verify standard packing CLI command executes successfully and creates the archive."""
    out_big = tmp_path / "cli_test.big"
    monkeypatch.setattr(sys, "argv", ["big_pack", str(standard_mod_directory), "-o", str(out_big)])

    big_pack.main()
    assert out_big.exists()
    assert out_big.stat().st_size > 0


def test_cli_pack_invalid_source_exits_with_error(tmp_path: Path, monkeypatch, capsys):
    """Verify packing an invalid directory exits non-zero and writes diagnostic output."""
    missing_dir = tmp_path / "void"
    monkeypatch.setattr(sys, "argv", ["big_pack", str(missing_dir)])

    with pytest.raises(SystemExit) as exc:
        big_pack.main()

    assert exc.value.code != 0
    _, stderr = capsys.readouterr()
    assert len(stderr.strip()) > 0


def test_cli_unpack_successful_execution(standard_mod_directory: Path, tmp_path: Path, monkeypatch):
    """Verify standard unpacking CLI command executes successfully and extracts files."""
    archive = tmp_path / "ready.big"
    extract_dir = tmp_path / "extracted"

    # Pre-pack an archive using the API to test the CLI unpacker
    big_pack.pack(standard_mod_directory, archive)
    monkeypatch.setattr(sys, "argv", ["big_unpack", str(archive), "-o", str(extract_dir)])

    big_unpack.main()
    assert (extract_dir / "data" / "weapon.ini").exists()


def test_cli_unpack_missing_archive_exits_with_error(tmp_path: Path, monkeypatch, capsys):
    """Verify unpacking a missing archive exits non-zero and writes diagnostic output."""
    missing_file = tmp_path / "void.big"
    monkeypatch.setattr(sys, "argv", ["big_unpack", str(missing_file)])

    with pytest.raises(SystemExit) as exc:
        big_unpack.main()

    assert exc.value.code != 0
    _, stderr = capsys.readouterr()
    assert len(stderr.strip()) > 0
