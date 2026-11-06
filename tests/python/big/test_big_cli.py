"""
@file tests/python/big/test_cli.py
@brief Tests for the command-line interface wrappers of the BIG archive tools.

Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
Part of the Lord of the Mods (lotm) project.
SPDX-License-Identifier: GPL-3.0-or-later
"""

import pytest
from pathlib import Path

import lotm.big.cli as cli
import lotm.big as big


def test_cli_pack_successful_execution(standard_mod_directory: Path, tmp_path: Path):
    """Verify standard packing CLI command executes successfully and creates the archive."""
    out_big = tmp_path / "cli_test.big"
    argv = ["pack", str(standard_mod_directory), "-o", str(out_big)]

    assert cli.main(argv) == cli.EXIT_SUCCESS
    assert out_big.exists()
    assert out_big.stat().st_size > 0


def test_cli_pack_invalid_source_exits_with_error(tmp_path: Path, capsys):
    """Verify packing an invalid directory exits non-zero and writes diagnostic output."""
    missing_dir = tmp_path / "void"
    argv = ["pack", str(missing_dir)]

    assert cli.main(argv) == cli.EXIT_ERROR
    _, stderr = capsys.readouterr()
    assert len(stderr.strip()) > 0
    assert "failed:" in stderr


def test_cli_unpack_successful_execution(standard_mod_directory: Path, tmp_path: Path):
    """Verify standard unpacking CLI command executes successfully and extracts files."""
    archive = tmp_path / "ready.big"
    extract_dir = tmp_path / "extracted"

    # Pre-pack an archive using the API to test the CLI unpacker
    big.pack(standard_mod_directory, archive)
    argv = ["unpack", str(archive), "-o", str(extract_dir)]

    assert cli.main(argv) == cli.EXIT_SUCCESS
    assert (extract_dir / "data" / "weapon.ini").exists()


def test_cli_unpack_missing_archive_exits_with_error(tmp_path: Path, capsys):
    """Verify unpacking a missing archive exits non-zero and writes diagnostic output."""
    missing_file = tmp_path / "void.big"
    argv = ["unpack", str(missing_file)]

    assert cli.main(argv) == cli.EXIT_ERROR
    _, stderr = capsys.readouterr()
    assert len(stderr.strip()) > 0
    assert "failed:" in stderr


def test_cli_unpack_with_filter_pattern(standard_mod_directory: Path, tmp_path: Path):
    """Verify unpacking CLI command with -f/--filter extracts only matching files."""
    archive = tmp_path / "filtered.big"
    extract_dir = tmp_path / "extracted_filtered"

    big.pack(standard_mod_directory, archive)
    argv = ["unpack", str(archive), "-o", str(extract_dir), "-f", "art/*.dds"]

    assert cli.main(argv) == cli.EXIT_SUCCESS
    assert (extract_dir / "art" / "texture.dds").exists()
    assert not (extract_dir / "data" / "weapon.ini").exists()
    assert not (extract_dir / "readme.txt").exists()


def test_cli_diff_successful_and_verbose_execution(tmp_path: Path):
    """Verify lotm-big diff CLI command executes cleanly with verbose output and patch output."""
    base_arc = tmp_path / "base.big"
    target_arc = tmp_path / "target.big"
    patch_arc = tmp_path / "patch.big"

    base_arc.write_bytes(big.pack_to_memory({"a.txt": b"1", "b.txt": b"2"}))
    target_arc.write_bytes(big.pack_to_memory({"b.txt": b"3", "c.txt": b"4"}))

    argv = ["diff", str(base_arc), str(target_arc), "-o", str(patch_arc), "-v"]
    
    assert cli.main(argv) == cli.EXIT_SUCCESS
    assert patch_arc.is_file()


def test_cli_diff_missing_archive_exits_with_error(tmp_path: Path, capsys):
    """Verify comparing a missing archive exits non-zero and writes diagnostic output."""
    missing_file = tmp_path / "void.big"
    argv = ["diff", str(missing_file), str(missing_file)]

    assert cli.main(argv) == cli.EXIT_ERROR
    _, stderr = capsys.readouterr()
    assert len(stderr.strip()) > 0
    assert "failed:" in stderr


def test_cli_overlay_successful_and_verbose_execution(tmp_path: Path):
    """Verify lotm-big overlay CLI command executes cleanly for directory and file inputs."""
    arc1 = tmp_path / "01_base.big"
    arc2 = tmp_path / "02_patch.big"

    arc1.write_bytes(big.pack_to_memory({"a.ini": b"1"}))
    arc2.write_bytes(big.pack_to_memory({"a.ini": b"2", "b.ini": b"3"}))

    argv = ["overlay", str(tmp_path), "-f", "*.ini", "-v"]
    
    assert cli.main(argv) == cli.EXIT_SUCCESS


def test_cli_overlay_missing_source_exits_with_error(tmp_path: Path, capsys):
    """Verify lotm-big overlay exits non-zero when given a non-existent archive path."""
    missing_file = tmp_path / "void.big"
    argv = ["overlay", str(missing_file)]

    assert cli.main(argv) == cli.EXIT_ERROR
    _, stderr = capsys.readouterr()
    assert len(stderr.strip()) > 0
    assert "failed:" in stderr
