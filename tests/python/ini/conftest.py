"""
@file tests/python/ini/conftest.py
@brief Shared pytest fixtures for SAGE configuration and localization tests.

Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
Part of the Lord of the Mods (lotm) project.
SPDX-License-Identifier: GPL-3.0-or-later
"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture()
def sample_ini_file(tmp_path: Path) -> Path:
    content = (
        "#define GONDOR_SOLDIER_HEALTH 200\n"
        '; Leading file comment\n'
        '#include "..\\..\\common.inc"\n'
        "\n"
        "; Mordor Fighter Object\n"
        "Object MordorFighter\n"
        "  Side = Mordor\n"
        "  Body = ActiveBody ModuleTag_01\n"
        "    MaxHealth = 100\n"
        "  End\n"
        "End\n"
    )
    file_path = tmp_path / "mordor_fighter.ini"
    file_path.write_text(content, encoding="utf-8")
    return file_path


@pytest.fixture()
def sample_inc_file(tmp_path: Path) -> Path:
    content = (
        "; Sub-level include block\n"
        "Body = ActiveBody ModuleTag_Inc\n"
        "  MaxHealth = 500\n"
        "End\n"
    )
    file_path = tmp_path / "shared_body.inc"
    file_path.write_text(content, encoding="utf-8")
    return file_path


@pytest.fixture()
def sample_str_file(tmp_path: Path) -> Path:
    content = (
        "// Standalone header comment\n"
        "\n"
        "// Tooltip for Gondor Archer\n"
        "CONTROLBAR:ToolTipGondorArcher\n"
        '  "Gondor Archer"\n'
        "  // Inner comment before end\n"
        "\n"
        "END\n"
    )
    file_path = tmp_path / "lotr.str"
    file_path.write_text(content, encoding="utf-8")
    return file_path


@pytest.fixture()
def broken_ini_file(tmp_path: Path) -> Path:
    content = (
        "Object GondorArcher\n"
        "  Side = Men\n"
        "End\n"
        "End\n"  # Extra unmatched closing delimiter
    )
    file_path = tmp_path / "broken.ini"
    file_path.write_text(content, encoding="utf-8")
    return file_path


@pytest.fixture()
def broken_str_file(tmp_path: Path) -> Path:
    content = (
        "OBJECT:LoneEntry\n"
        '  "Text"\n'
        "END\n"
        "; Comment before unmatched end\n"
        "END\n"
    )
    file_path = tmp_path / "broken.str"
    file_path.write_text(content, encoding="utf-8")
    return file_path
