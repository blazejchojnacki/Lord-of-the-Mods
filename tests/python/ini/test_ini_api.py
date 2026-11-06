"""
@file tests/python/ini/test_ini_api.py
@brief Tests for lotm.ini Python library API functions and parser behavior.

Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
Part of the Lord of the Mods (lotm) project.
SPDX-License-Identifier: GPL-3.0-or-later
"""

from __future__ import annotations

from pathlib import Path

import pytest

from lotm.ini import (
    CommentNode,
    ConstructLevel,
    IncludeNode,
    IniParseError,
    StrEntry,
    iter_unwrapped_items,
    load_file,
    parse_ini_file,
    parse_str_file,
    recognize_structure,
    scan_directory_for_errors,
    scan_file_for_errors,
)


def test_parse_ini_file_structure_and_unwrapping(sample_ini_file: Path) -> None:
    cf = parse_ini_file(sample_ini_file, strict=True)
    assert cf.strict is True
    assert cf.start_level == 0
    assert cf.errors == []
    assert cf.defines == ["#define GONDOR_SOLDIER_HEALTH 200"]

    top_nodes = list(iter_unwrapped_items(cf))
    assert any(isinstance(n, CommentNode) for n in top_nodes)
    assert any(isinstance(n, IncludeNode) for n in top_nodes)

    blocks = [n for n in top_nodes if isinstance(n, ConstructLevel)]
    assert len(blocks) == 1
    obj_block = blocks[0]
    assert obj_block._class == "Object"
    assert obj_block.name == "MordorFighter"
    assert obj_block.comment == "; Mordor Fighter Object"

    inner_nodes = list(iter_unwrapped_items(obj_block))
    nested_blocks = [n for n in inner_nodes if isinstance(n, ConstructLevel)]
    assert len(nested_blocks) == 1
    assert nested_blocks[0]._class == "Body"
    assert nested_blocks[0].name == "ActiveBody"
    assert nested_blocks[0].identifier == "ModuleTag_01"

    printed = cf.print()
    assert "#define GONDOR_SOLDIER_HEALTH 200\n" in printed
    assert "Object MordorFighter\n" in printed


def test_parse_inc_and_str_via_construct_file(
    sample_inc_file: Path, sample_str_file: Path
) -> None:
    inc_cf = parse_ini_file(sample_inc_file, strict=True)
    assert inc_cf.start_level == 1
    assert inc_cf.errors == []
    assert "Body = ActiveBody ModuleTag_Inc" in inc_cf.print()

    str_cf = parse_ini_file(sample_str_file, strict=True)
    assert str_cf.start_level == 0
    assert str_cf.errors == []
    unwrapped = list(iter_unwrapped_items(str_cf))
    assert any(isinstance(n, StrEntry) for n in unwrapped)
    assert "CONTROLBAR:ToolTipGondorArcher" in str_cf.print()


def test_replace_module_and_schema_switching(tmp_path: Path) -> None:
    content = (
        "ChildObject MordorTroll MordorTrollBase\n"
        "  ReplaceModule ModuleTag_OldBody\n"
        "    Body = ActiveBody ModuleTag_NewBody\n"
        "      MaxHealth = 1500\n"
        "    End\n"
        "  End\n"
        "End\n"
        "\n"
        "Armor TrollArmor\n"
        "  Armor = DEFAULT 50%\n"
        "End\n"
    )
    ini_path = tmp_path / "switch_and_replace.ini"
    ini_path.write_text(content, encoding="utf-8")

    cf = parse_ini_file(ini_path, strict=True)
    assert cf.errors == []
    top_blocks = [n for n in iter_unwrapped_items(cf) if isinstance(n, ConstructLevel)]
    assert len(top_blocks) == 2
    assert top_blocks[0]._class == "ChildObject"
    assert top_blocks[1]._class == "Armor"


def test_cp1252_encoding_and_crlf_normalization(tmp_path: Path) -> None:
    # 0x93 and 0x94 are smart quotes in Windows-1252 (invalid UTF-8 standalone bytes)
    raw_bytes = (
        b"; Smart quotes: \x93Ringwraith\x94\r\n"
        b"Object Nazgul\r"
        b"  Side = Mordor\r\n"
        b"End\r\n"
    )
    cp1252_file = tmp_path / "cp1252.ini"
    cp1252_file.write_bytes(raw_bytes)

    cf = parse_ini_file(cp1252_file, strict=True)
    assert cf.errors == []
    printed = cf.print()
    assert "\u201cRingwraith\u201d" in printed
    assert "\r" not in printed


def test_strict_vs_non_strict_error_handling_ini(broken_ini_file: Path) -> None:
    cf = parse_ini_file(broken_ini_file, strict=False)
    assert len(cf.errors) == 1
    assert "Delimiter mismatch: negative level reached" in cf.errors[0]

    with pytest.raises(IniParseError, match="Delimiter mismatch"):
        parse_ini_file(broken_ini_file, strict=True)


def test_strict_vs_non_strict_error_handling_str(
    broken_str_file: Path, tmp_path: Path
) -> None:
    doc = parse_str_file(broken_str_file, strict=False)
    assert len(doc.errors) == 1
    assert "Delimiter mismatch" in doc.errors[0]

    with pytest.raises(IniParseError, match="Delimiter mismatch"):
        parse_str_file(broken_str_file, strict=True)

    unclosed_str = tmp_path / "unclosed.str"
    unclosed_str.write_text('OBJECT:Unclosed\n  "Hello"\n', encoding="utf-8")
    unclosed_doc = parse_str_file(unclosed_str, strict=False)
    assert len(unclosed_doc.entries) == 1

    bad_ext = tmp_path / "not_a_str.ini"
    bad_ext.write_text("Object X\nEnd\n", encoding="utf-8")
    with pytest.raises(IniParseError, match="invalid"):
        parse_str_file(bad_ext)


def test_load_file_and_recognize_structure(
    sample_ini_file: Path, sample_str_file: Path, tmp_path: Path
) -> None:
    content, delims = load_file(sample_ini_file)
    assert "Object MordorFighter" in content
    assert len(delims) > 0

    str_delims, str_start = recognize_structure(sample_str_file)
    assert str_start == 0
    assert "CONTROLBAR" in str_delims[0]

    txt_file = tmp_path / "readme.txt"
    txt_file.write_text("Plain text content", encoding="utf-8")
    txt_content, txt_delims = load_file(txt_file)
    assert txt_content == "Plain text content"
    assert txt_delims == []

    empty_ini = tmp_path / "empty.ini"
    empty_ini.write_text("", encoding="utf-8")
    empty_content, empty_delims = load_file(empty_ini)
    assert empty_content == ""
    assert empty_delims == []

    unknown_delims, unknown_level = recognize_structure(txt_file)
    assert unknown_delims == []
    assert unknown_level == 0

    with pytest.raises(IniParseError, match="empty path"):
        load_file(Path(""))

    with pytest.raises(IniParseError, match="wrong path"):
        load_file(tmp_path / "nonexistent.ini")

    bad_file = tmp_path / "archive.big"
    bad_file.write_text("binary", encoding="utf-8")
    with pytest.raises(IniParseError, match="unsupported file type"):
        load_file(bad_file)


def test_scan_file_and_directory_for_errors(
    sample_ini_file: Path, broken_ini_file: Path, tmp_path: Path
) -> None:
    assert scan_file_for_errors(sample_ini_file) == []

    broken_errs = scan_file_for_errors(broken_ini_file)
    assert len(broken_errs) == 1

    missing_errs = scan_file_for_errors(tmp_path / "missing.ini")
    assert len(missing_errs) == 1
    assert "Fatal error while processing" in missing_errs[0]

    results = scan_directory_for_errors(tmp_path)
    assert sample_ini_file in results
    assert broken_ini_file in results
    assert results[sample_ini_file] == []
    assert len(results[broken_ini_file]) == 1

    with pytest.raises(FileNotFoundError):
        scan_directory_for_errors(tmp_path / "no_such_dir")

    with pytest.raises(NotADirectoryError):
        scan_directory_for_errors(sample_ini_file)
