"""
@file tests/python/ini/conftest.py
@brief Shared Pytest fixtures for SAGE INI, INC, and STR test suites.

Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
Part of the Lord of the Mods (lotm) project.
SPDX-License-Identifier: GPL-3.0-or-later
"""

from __future__ import annotations

from pathlib import Path
import pytest


@pytest.fixture
def sample_ini_content() -> str:
    """Return a comprehensive SAGE .ini configuration payload covering special constructs."""
    return (
        "#define HERO_HEALTH 3000 ; macro comment\n"
        '#include "..\\common\\macros.inc" ; root include\n'
        "; Leading file comment\n"
        "\n"
        "BeginScript TopScript\n"
        "    if a == 1 then return end\n"
        "EndScript ; end top script\n"
        "\n"
        "; Object comment\n"
        "Object GondorAragorn ; header comment\n"
        '    #include "includes\\armor.inc"\n'
        "    Side = Men\n"
        "    Draw = W3DScriptedModelDraw ModuleTag_Draw\n"
        "        DefaultModelConditionState\n"
        "            Model = GUAragorn_SKN\n"
        "        End\n"
        "        AnimationState = MOVING\n"
        "            BeginScript\n"
        '                CurDrawableShowSubObject("SWORD")\n'
        "            EndScript\n"
        "        End\n"
        "    End\n"
        "    ReplaceModule ModuleTag_DefaultBody\n"
        "        Body = RespawnBody ModuleTag_HeroBody\n"
        "            MaxHealth = HERO_HEALTH\n"
        "        End\n"
        "    End\n"
        "    Alpha = FCurve\n"
        "        ControlPoint = 0.0 1.0\n"
        "    End\n"
        "End ; end object\n"
    )


@pytest.fixture
def sample_ini_file(tmp_path: Path, sample_ini_content: str) -> Path:
    """Create a temporary valid .ini file on disk."""
    ini_path = tmp_path / "aragorn.ini"
    ini_path.write_text(sample_ini_content, encoding="utf-8")
    return ini_path


@pytest.fixture
def sample_inc_file(tmp_path: Path) -> Path:
    """Create a temporary valid .inc file starting at an inner schema depth."""
    inc_path = tmp_path / "lod_options.inc"
    inc_path.write_text(
        "; INC header\n"
        "LodOptions\n"
        "    AllowMultipleModels = YES\n"
        "End\n",
        encoding="utf-8",
    )
    return inc_path


@pytest.fixture
def sample_str_file(tmp_path: Path) -> Path:
    """Create a temporary valid .str localization file on disk."""
    str_path = tmp_path / "lotr.str"
    str_path.write_text(
        "; Localization file comment\n"
        "\n"
        "; Hero tooltip\n"
        "OBJECT:GondorAragorn ; inline hdr\n"
        '    "Aragorn, Son of Arathorn" ; text cmt\n'
        "End ; end cmt\n"
        "\n"
        "GUI:StartButton\n"
        '    "Start Game"\n'
        "END\n",
        encoding="utf-8",
    )
    return str_path


@pytest.fixture
def malformed_ini_file(tmp_path: Path) -> Path:
    """Create a temporary .ini file containing negative-level and unclosed-block errors."""
    bad_path = tmp_path / "malformed.ini"
    bad_path.write_text(
        "Armor ValidArmor\n"
        "    Armor = DEFAULT 50%\n"
        "End\n"
        "End ; negative level\n"
        "Object UnclosedObject\n"
        "    Side = Mordor\n",
        encoding="utf-8",
    )
    return bad_path


@pytest.fixture
def ini_mod_directory(tmp_path: Path, sample_ini_content: str) -> Path:
    """Create a structured mod directory containing .ini, .inc, .str, and .txt files."""
    mod_root = tmp_path / "mod_workspace"
    ini_root = mod_root / "data" / "ini"
    obj_dir = ini_root / "object"
    inc_dir = ini_root / "includes"
    lang_dir = mod_root / "lang"

    obj_dir.mkdir(parents=True)
    inc_dir.mkdir(parents=True)
    lang_dir.mkdir(parents=True)

    (obj_dir / "hero.ini").write_text(sample_ini_content, encoding="utf-8")
    (inc_dir / "armor.inc").write_text(
        "ArmorSet\n    Conditions = NONE\nEnd\n",
        encoding="utf-8",
    )
    (lang_dir / "lotr.str").write_text(
        'OBJECT:Hero\n    "Hero"\nEnd\n',
        encoding="utf-8",
    )
    (mod_root / "notes.txt").write_text("Plain text documentation", encoding="utf-8")

    return mod_root
