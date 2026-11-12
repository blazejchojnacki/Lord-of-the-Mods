"""
@file tests/python/ini/test_ini_cli.py
@brief Tests for the command-line interface subcommands of lotm.ini.

Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
Part of the Lord of the Mods (lotm) project.
SPDX-License-Identifier: GPL-3.0-or-later
"""

from __future__ import annotations

from pathlib import Path
import pytest

import lotm.cli as umbrella_cli


def test_ini_cli_scan_clean_directory(
    ini_mod_directory: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify `lotm ini scan` succeeds on a clean directory and prints summary to stdout."""
    rc = umbrella_cli.main(["ini", "scan", str(ini_mod_directory), "--strict"])
    assert rc == umbrella_cli.EXIT_SUCCESS

    stdout, stderr = capsys.readouterr()
    assert "Scanned 3 file(s): 3 clean, 0 with errors." in stdout
    assert stderr == ""


def test_ini_cli_scan_with_errors_non_strict_and_strict(
    malformed_ini_file: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify `lotm ini scan` reports errors to stderr in non-strict mode and fails in --strict mode."""
    # Non-strict scan outputs diagnostics to stderr and returns EXIT_SUCCESS
    rc_lenient = umbrella_cli.main(["ini", "scan", str(malformed_ini_file)])
    assert rc_lenient == umbrella_cli.EXIT_SUCCESS
    stdout, stderr = capsys.readouterr()
    assert stdout == ""
    assert "1 with errors" in stderr
    assert "negative level reached" in stderr

    # Non-strict scan with -o / --output writes report to disk
    report_file = tmp_path / "reports" / "scan_report.txt"
    rc_out = umbrella_cli.main(["ini", "scan", str(malformed_ini_file), "-o", str(report_file)])
    assert rc_out == umbrella_cli.EXIT_SUCCESS
    assert report_file.is_file()
    assert "negative level reached" in report_file.read_text(encoding="utf-8")
    stdout_out, _ = capsys.readouterr()
    assert "Scan report written to" in stdout_out

    # Strict scan exits with EXIT_ERROR when errors are detected
    rc_strict = umbrella_cli.main(["ini", "scan", str(malformed_ini_file), "--strict"])
    assert rc_strict == umbrella_cli.EXIT_ERROR
    _, stderr_strict = capsys.readouterr()
    assert "Command 'ini scan' failed: Strict scan failed:" in stderr_strict


def test_ini_cli_format_to_output_and_in_place(
    tmp_path: Path,
    malformed_ini_file: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify `lotm ini format` both with -o destination and in-place overwriting."""
    unformatted = tmp_path / "unformatted.ini"
    unformatted.write_text("Weapon GondorSword\nDamage = 25\nEnd\n", encoding="utf-8")
    formatted_dest = tmp_path / "out" / "formatted.ini"

    # Format to separate output file
    rc_out = umbrella_cli.main(
        ["ini", "format", str(unformatted), "-o", str(formatted_dest), "--strict"]
    )
    assert rc_out == umbrella_cli.EXIT_SUCCESS
    assert formatted_dest.is_file()
    assert "    Damage = 25\n" in formatted_dest.read_text(encoding="utf-8")
    stdout_out, _ = capsys.readouterr()
    assert "->" in stdout_out

    # Format in-place
    rc_inplace = umbrella_cli.main(["ini", "format", str(unformatted)])
    assert rc_inplace == umbrella_cli.EXIT_SUCCESS
    assert "    Damage = 25\n" in unformatted.read_text(encoding="utf-8")
    stdout_inplace, _ = capsys.readouterr()
    assert "in-place" in stdout_inplace

    # Strict format on malformed file fails cleanly
    rc_fail = umbrella_cli.main(["ini", "format", str(malformed_ini_file), "--strict"])
    assert rc_fail == umbrella_cli.EXIT_ERROR
    _, stderr_fail = capsys.readouterr()
    assert "Command 'ini format' failed:" in stderr_fail


def test_ini_cli_inspect_clean_empty_and_malformed_files(
    sample_ini_file: Path,
    malformed_ini_file: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify `lotm ini inspect` output across clean, blockless, and malformed files."""
    # Clean file with blocks
    rc_clean = umbrella_cli.main(["ini", "inspect", str(sample_ini_file), "--strict"])
    assert rc_clean == umbrella_cli.EXIT_SUCCESS
    stdout_clean, stderr_clean = capsys.readouterr()
    assert "Defines:         1" in stdout_clean
    assert "Includes:        2" in stdout_clean
    assert "Block Breakdown:" in stdout_clean
    assert "Object: 1" in stdout_clean
    assert stderr_clean == ""

    # File without blocks (only defines/comments)
    only_defines = tmp_path / "macros.inc"
    only_defines.write_text("#define MACRO_A 10\n; just a comment\n", encoding="utf-8")
    rc_noblocks = umbrella_cli.main(["ini", "inspect", str(only_defines)])
    assert rc_noblocks == umbrella_cli.EXIT_SUCCESS
    stdout_noblocks, _ = capsys.readouterr()
    assert "Defines:         1" in stdout_noblocks
    assert "Block Breakdown:" not in stdout_noblocks

    # Malformed file in non-strict mode prints errors to stderr
    rc_malformed = umbrella_cli.main(["ini", "inspect", str(malformed_ini_file)])
    assert rc_malformed == umbrella_cli.EXIT_SUCCESS
    _, stderr_malformed = capsys.readouterr()
    assert "Errors (2):" in stderr_malformed

    # Malformed file in strict mode returns EXIT_ERROR
    rc_strict_err = umbrella_cli.main(["ini", "inspect", str(malformed_ini_file), "--strict"])
    assert rc_strict_err == umbrella_cli.EXIT_ERROR
    _, stderr_strict = capsys.readouterr()
    assert "Command 'ini inspect' failed:" in stderr_strict
