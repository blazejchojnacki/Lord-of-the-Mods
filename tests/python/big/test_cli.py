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

import lotm.big.cli as cli
import lotm.big as big


def test_cli_pack_successful_execution(standard_mod_directory: Path, tmp_path: Path, monkeypatch):
    """Verify standard packing CLI command executes successfully and creates the archive."""
    out_big = tmp_path / "cli_test.big"
    monkeypatch.setattr(sys, "argv", ["lotm-big-pack", str(standard_mod_directory), "-o", str(out_big)])

    cli.main_pack()
    assert out_big.exists()
    assert out_big.stat().st_size > 0


def test_cli_pack_invalid_source_exits_with_error(tmp_path: Path, monkeypatch, capsys):
    """Verify packing an invalid directory exits non-zero and writes diagnostic output."""
    missing_dir = tmp_path / "void"
    monkeypatch.setattr(sys, "argv", ["lotm-big-pack", str(missing_dir)])

    with pytest.raises(SystemExit) as exc:
        cli.main_pack()

    assert exc.value.code != 0
    _, stderr = capsys.readouterr()
    assert len(stderr.strip()) > 0


def test_cli_unpack_successful_execution(standard_mod_directory: Path, tmp_path: Path, monkeypatch):
    """Verify standard unpacking CLI command executes successfully and extracts files."""
    archive = tmp_path / "ready.big"
    extract_dir = tmp_path / "extracted"

    # Pre-pack an archive using the API to test the CLI unpacker
    big.pack(standard_mod_directory, archive)
    monkeypatch.setattr(sys, "argv", ["lotm-big-unpack", str(archive), "-o", str(extract_dir)])

    cli.main_unpack()
    assert (extract_dir / "data" / "weapon.ini").exists()


def test_cli_unpack_missing_archive_exits_with_error(tmp_path: Path, monkeypatch, capsys):
    """Verify unpacking a missing archive exits non-zero and writes diagnostic output."""
    missing_file = tmp_path / "void.big"
    monkeypatch.setattr(sys, "argv", ["lotm-big-unpack", str(missing_file)])

    with pytest.raises(SystemExit) as exc:
        cli.main_unpack()

    assert exc.value.code != 0
    _, stderr = capsys.readouterr()
    assert len(stderr.strip()) > 0
