"""
@file tests/python/ini/test_cli.py
@brief Command-line interface tests for lotm.ini.ini_cli.

Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
Part of the Lord of the Mods (lotm) project.
SPDX-License-Identifier: GPL-3.0-or-later
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from lotm.ini.ini_cli import (
    EXIT_ERROR,
    EXIT_PARSE_FAILURE,
    EXIT_SUCCESS,
    cli_entry,
    main as cli_main,
)


def test_cli_scan_file_and_directory(
    sample_ini_file: Path,
    broken_ini_file: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Single clean file to stdout
    rc = cli_main(["scan", str(sample_ini_file)])
    assert rc == EXIT_SUCCESS
    out = capsys.readouterr().out
    assert "Files with Errors: 0 / 1" in out

    # Directory scan with --output and --strict on broken file
    report_out = tmp_path / "cli_report.txt"
    rc_strict = cli_main(
        ["scan", str(tmp_path), "-o", str(report_out), "--strict"]
    )
    assert rc_strict == EXIT_PARSE_FAILURE
    assert report_out.is_file()
    report_content = report_out.read_text(encoding="utf-8")
    assert "broken.ini" in report_content

    # Single broken file without --strict returns EXIT_SUCCESS
    rc_single_broken = cli_main(["scan", str(broken_ini_file)])
    assert rc_single_broken == EXIT_SUCCESS

    # Nonexistent target returns EXIT_ERROR
    rc_missing = cli_main(["scan", str(tmp_path / "missing_dir")])
    assert rc_missing == EXIT_ERROR
    assert "I/O error" in capsys.readouterr().err


def test_cli_format_ini_and_str(
    sample_ini_file: Path,
    sample_str_file: Path,
    broken_ini_file: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Format .ini to stdout
    rc = cli_main(["format", str(sample_ini_file)])
    assert rc == EXIT_SUCCESS
    assert "Object MordorFighter" in capsys.readouterr().out

    # Format .str to output file
    formatted_str = tmp_path / "formatted.str"
    rc_str = cli_main(["format", str(sample_str_file), "-o", str(formatted_str)])
    assert rc_str == EXIT_SUCCESS
    assert "CONTROLBAR:ToolTipGondorArcher" in formatted_str.read_text(encoding="utf-8")

    # Format broken .ini with --strict catches IniParseError and returns EXIT_PARSE_FAILURE
    rc_broken = cli_main(["format", str(broken_ini_file), "--strict"])
    assert rc_broken == EXIT_PARSE_FAILURE
    assert "Parse error" in capsys.readouterr().err

    # Format missing file returns EXIT_ERROR
    rc_missing = cli_main(["format", str(tmp_path / "missing.ini")])
    assert rc_missing == EXIT_ERROR


def test_cli_inspect_and_entry_point(
    sample_ini_file: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rc = cli_main(["inspect", str(sample_ini_file)])
    assert rc == EXIT_SUCCESS
    out = capsys.readouterr().out
    assert "Start Level: 0" in out
    assert "Level 0 Delimiters" in out

    # Unrecognized structure file
    empty_file = tmp_path / "empty.ini"
    empty_file.write_text("; only comment\n", encoding="utf-8")
    rc_unrec = cli_main(["inspect", str(empty_file)])
    assert rc_unrec == EXIT_PARSE_FAILURE
    assert "Unrecognized or empty" in capsys.readouterr().out

    # Missing file
    assert cli_main(["inspect", str(tmp_path / "nope.ini")]) == EXIT_ERROR

    # Test cli_entry() SystemExit wrapper
    monkeypatch.setattr(sys, "argv", ["lotm-ini", "inspect", str(sample_ini_file)])
    with pytest.raises(SystemExit) as exc_info:
        cli_entry()
    assert exc_info.value.code == EXIT_SUCCESS
