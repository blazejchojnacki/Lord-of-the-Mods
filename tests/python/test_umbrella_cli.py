"""
@file tests/python/test_umbrella_cli.py
@brief Integration tests for the lotm umbrella CLI runner.

Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
Part of the Lord of the Mods (lotm) project.
SPDX-License-Identifier: GPL-3.0-or-later
"""

import sys
import pytest
from pathlib import Path

import lotm.cli as cli


def test_umbrella_cli_version_flag(capsys):
    """Verify that the umbrella CLI reports its version correctly."""
    with pytest.raises(SystemExit) as exc_info:
        cli.main(["--version"])
        
    assert exc_info.value.code == 0
    stdout, _ = capsys.readouterr()
    assert "lotm" in stdout


def test_umbrella_cli_big_pack_execution(standard_mod_directory: Path, tmp_path: Path, capsys):
    """Verify that lotm routes 'big pack' commands correctly through the umbrella parser."""
    out_big = tmp_path / "umbrella_test.big"
    argv = ["big", "pack", str(standard_mod_directory), "-o", str(out_big)]

    assert cli.main(argv) == cli.EXIT_SUCCESS
    assert out_big.exists()
    assert out_big.stat().st_size > 0
    stdout, _ = capsys.readouterr()
    assert "Packed archive:" in stdout


def test_umbrella_cli_missing_domain_exits_with_error(capsys):
    """Verify that lotm fails cleanly when an invalid top-level domain is provided."""
    argv = ["unknown_domain", "pack"]

    with pytest.raises(SystemExit) as exc_info:
        cli.main(argv)
        
    assert exc_info.value.code != 0
    _, stderr = capsys.readouterr()
    assert "invalid choice: 'unknown_domain'" in stderr


def test_umbrella_cli_exception_handling(tmp_path: Path, capsys):
    """Verify that lotm traps runtime errors gracefully and logs the failed domain/command."""
    missing_dir = tmp_path / "void"
    argv = ["big", "pack", str(missing_dir)]

    assert cli.main(argv) == cli.EXIT_ERROR
    _, stderr = capsys.readouterr()
    assert "Command 'big pack' failed:" in stderr
    

def test_umbrella_cli_entry_invokes_sys_exit(standard_mod_directory: Path, tmp_path: Path, monkeypatch):
    """Verify cli_entry() parses sys.argv directly via python -m lotm execution."""
    out_big = tmp_path / "entry.big"
    monkeypatch.setattr(sys, "argv", ["lotm", "big", "pack", str(standard_mod_directory), "-o", str(out_big)])

    with pytest.raises(SystemExit) as exc_info:
        cli.cli_entry()

    assert exc_info.value.code == cli.EXIT_SUCCESS
    assert out_big.is_file()
