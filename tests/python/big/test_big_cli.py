"""
@file tests/python/big/test_big_cli.py
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


def test_cli_unpack_with_filter_pattern(standard_mod_directory: Path, tmp_path: Path, monkeypatch):
    """Verify unpacking CLI command with -f/--filter extracts only matching files."""
    archive = tmp_path / "filtered.big"
    extract_dir = tmp_path / "extracted_filtered"

    big.pack(standard_mod_directory, archive)
    monkeypatch.setattr(
        sys, "argv", ["lotm-big-unpack", str(archive), "-o", str(extract_dir), "-f", "art/*.dds"]
    )

    cli.main_unpack()
    assert (extract_dir / "art" / "texture.dds").exists()
    assert not (extract_dir / "data" / "weapon.ini").exists()
    assert not (extract_dir / "readme.txt").exists()


def test_cli_diff_successful_and_verbose_execution(tmp_path: Path, monkeypatch):
    """Verify lotm-big-diff CLI command executes cleanly with verbose output and patch output."""
    base_arc = tmp_path / "base.big"
    target_arc = tmp_path / "target.big"
    patch_arc = tmp_path / "patch.big"

    base_arc.write_bytes(big.pack_to_memory({"a.txt": b"1", "b.txt": b"2"}))
    target_arc.write_bytes(big.pack_to_memory({"b.txt": b"3", "c.txt": b"4"}))

    monkeypatch.setattr(
        sys, "argv", ["lotm-big-diff", str(base_arc), str(target_arc), "-o", str(patch_arc), "-v"]
    )
    cli.main_diff()
    assert patch_arc.is_file()


def test_cli_diff_missing_archive_exits_with_error(tmp_path: Path, monkeypatch, capsys):
    """Verify comparing a missing archive exits non-zero and writes diagnostic output."""
    missing_file = tmp_path / "void.big"
    monkeypatch.setattr(
        sys, "argv", ["lotm-big-diff", str(missing_file), str(missing_file)]
    )

    with pytest.raises(SystemExit) as exc:
        cli.main_diff()

    assert exc.value.code != 0
    _, stderr = capsys.readouterr()
    assert len(stderr.strip()) > 0


def test_cli_overlay_successful_and_verbose_execution(tmp_path: Path, monkeypatch):
    """Verify lotm-big-overlay CLI command executes cleanly for directory and file inputs."""
    arc1 = tmp_path / "01_base.big"
    arc2 = tmp_path / "02_patch.big"

    arc1.write_bytes(big.pack_to_memory({"a.ini": b"1"}))
    arc2.write_bytes(big.pack_to_memory({"a.ini": b"2", "b.ini": b"3"}))

    monkeypatch.setattr(
        sys, "argv", ["lotm-big-overlay", str(tmp_path), "-f", "*.ini", "-v"]
    )
    cli.main_overlay()


def test_cli_overlay_missing_source_exits_with_error(tmp_path: Path, monkeypatch, capsys):
    """Verify lotm-big-overlay exits non-zero when given a non-existent archive path."""
    missing_file = tmp_path / "void.big"
    monkeypatch.setattr(
        sys, "argv", ["lotm-big-overlay", str(missing_file)]
    )

    with pytest.raises(SystemExit) as exc:
        cli.main_overlay()

    assert exc.value.code != 0
    _, stderr = capsys.readouterr()
    assert len(stderr.strip()) > 0
