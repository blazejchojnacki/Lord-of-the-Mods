"""
@file tests/python/ini/test_ini_formatter.py
@brief Unit tests for lotm.ini.formatter (format_ini, FormatOptions, normalization toggles, and atomic sibling writes).

Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
Part of the Lord of the Mods (lotm) project.
SPDX-License-Identifier: GPL-3.0-or-later
"""

from __future__ import annotations

import os
from pathlib import Path
import pytest

import lotm.ini as ini


def test_format_ini_in_memory_string_and_buffer() -> None:
    """Verify format_ini without output_path across string and binary Buffer inputs."""
    # format_ini without output_path (both str and Buffer)
    formatted_str = ini.format_ini(
        "inline.ini",
        file_content="Armor A\nArmor = DEFAULT 10%\nEnd\n",
    )
    assert "    Armor = DEFAULT 10%\n" in formatted_str

    formatted_buf = ini.format_ini(
        "inline.ini",
        file_content=b"Armor A\nArmor = DEFAULT 10%\nEnd\n",
    )
    assert formatted_buf == formatted_str


def test_format_options_object_and_ast_print_overloads() -> None:
    """Verify FormatOptions construction, properties, equality, repr, and direct AST .print(options=...) calls."""
    default_opts = ini.FormatOptions()
    assert default_opts.indent == ini.LEVEL_INDENT
    assert not default_opts.normalize_end_tokens
    assert not default_opts.normalize_header_spacing
    assert not default_opts.normalize_statement_equals
    assert not default_opts.normalize_comments
    assert not default_opts.coalesce_blank_lines
    assert default_opts == ini.FormatOptions()
    assert "FormatOptions" in repr(default_opts)

    custom_opts = ini.FormatOptions(
        indent="  ",
        normalize_end_tokens=True,
        normalize_header_spacing=True,
        normalize_statement_equals=True,
        normalize_comments=True,
        coalesce_blank_lines=True,
    )
    assert custom_opts != default_opts
    assert custom_opts.indent == "  "

    doc = ini.parse_ini(
        "direct.ini",
        strict=True,
        file_content="Object   GondorSoldier // hdr\n  Damage=50 // dmg\n  beginscript Init\n    x = 1\n  endscript\nEND\n",
    )
    rendered = doc.print(custom_opts)
    assert "Object GondorSoldier ; hdr\n" in rendered
    assert "  Damage = 50 ; dmg\n" in rendered
    assert "  BeginScript Init\n" in rendered
    assert "    x = 1\n" in rendered
    assert "  EndScript\n" in rendered
    assert rendered.endswith("End\n\n")

    block = doc[0]
    assert isinstance(block, ini.ConstructLevel)
    assert "  Damage = 50 ; dmg\n" in block.print(options=custom_opts)

    script = block[1]
    assert isinstance(script, ini.ScriptNode)
    assert "  BeginScript Init\n" in script.print(level=1, options=custom_opts)

    str_doc = ini.parse_str(
        "direct.str",
        strict=True,
        file_content='OBJECT:GondorSoldier // hdr\n  "Soldier" // txt\nend\n',
    )
    str_rendered = str_doc.print(custom_opts)
    assert "OBJECT:GondorSoldier ; hdr\n" in str_rendered
    assert str_rendered.endswith("End\n\n")

    str_entry = str_doc[0]
    assert isinstance(str_entry, ini.StrEntry)
    assert f'{custom_opts.indent}"Soldier" ; txt\n' in str_entry.print(custom_opts)


def test_format_ini_normalization_toggles_and_options_merging() -> None:
    """Verify normalize_end_tokens, normalize_header_spacing, normalize_statement_equals, normalize_comments, coalesce_blank_lines, and FormatOptions merging."""
    messy_ini = (
        "Object   GondorFighter   ModTag_A // header\n"
        "    // comment 1\n"
        "\n"
        "    ; comment 2\n"
        "    Damage=75 // slash inline\n"
        "    beginscript   InitTag\n"
        "        x = 1\n"
        "\n"
        "\n"
        "        y = 2\n"
        "    endscript\n"
        "ENd\n"
    )
    normalized_ini = ini.format_ini(
        "messy.ini",
        file_content=messy_ini,
        strict=True,
        normalize_end_tokens=True,
        normalize_header_spacing=True,
        normalize_statement_equals=True,
        normalize_comments=True,
        coalesce_blank_lines=True,
    )
    assert "Object GondorFighter ModTag_A ; header\n" in normalized_ini
    assert "    ; comment 1\n" in normalized_ini
    assert "    Damage = 75 ; slash inline\n" in normalized_ini
    assert "    BeginScript InitTag\n" in normalized_ini
    assert "    EndScript\n" in normalized_ini
    assert normalized_ini.endswith("End\n\n")
    assert "\n\n\n" not in normalized_ini

    # Verify OR-merging explicit FormatOptions with keyword overrides
    base_opts = ini.FormatOptions(indent="  ", normalize_end_tokens=True)
    merged = ini.format_ini(
        "merge.ini",
        file_content="Weapon Bow\nDamage=30\nEND\n",
        options=base_opts,
        normalize_statement_equals=True,
    )
    assert "  Damage = 30\n" in merged
    assert merged.endswith("End\n\n")

    messy_str = (
        "OBJECT:GondorFighter\n"
        '    "Gondor Fighter"\n'
        "end\n"
    )
    normalized_str = ini.format_ini(
        "messy.str",
        file_content=messy_str,
        strict=True,
        normalize_end_tokens=True,
        normalize_header_spacing=True,
    )
    assert "OBJECT:GondorFighter\n" in normalized_str
    assert normalized_str.endswith("End\n\n")


def test_format_ini_atomic_file_output_and_cleanup_on_failure(
    tmp_path: Path,
    sample_ini_file: Path,
    malformed_ini_file: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify format_ini writes atomically to disk and cleans up .lotm_tmp on failure."""
    # format_ini with output_path creating parent directory
    out_formatted = tmp_path / "formatted_out" / "hero.ini"
    ini.format_ini(sample_ini_file, output_path=out_formatted, strict=True)
    assert out_formatted.is_file()

    # format_ini in strict mode rejects malformed input before creating output file
    strict_fail_dest = tmp_path / "formatted_out" / "strict_fail.ini"
    with pytest.raises(ini.IniParseError):
        ini.format_ini(malformed_ini_file, output_path=strict_fail_dest, strict=True)
    assert not strict_fail_dest.exists()

    # format_ini atomic write cleanup when os.replace fails
    fail_dest = tmp_path / "formatted_out" / "atomic_fail.ini"
    tmp_sibling = fail_dest.with_name(f".{fail_dest.name}.lotm_tmp")

    def _mock_replace_fail(src: os.PathLike[str], dst: os.PathLike[str]) -> None:
        raise OSError("Simulated atomic rename failure")

    with monkeypatch.context() as m:
        m.setattr(os, "replace", _mock_replace_fail)
        with pytest.raises(OSError, match="Simulated atomic rename failure"):
            ini.format_ini(sample_ini_file, output_path=fail_dest, strict=True)

    assert not tmp_sibling.exists()
    assert not fail_dest.exists()
