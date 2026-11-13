"""
@file tests/python/ini/test_ini_api.py
@brief Comprehensive unit tests for lotm.ini C++ bindings and high-level Python API.

Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
Part of the Lord of the Mods (lotm) project.
SPDX-License-Identifier: GPL-3.0-or-later
"""

from __future__ import annotations

import os
from collections.abc import Buffer
from pathlib import Path
import pytest

import lotm.ini as ini


def test_ast_leaf_nodes_properties_equality_and_repr() -> None:
    """Verify CommentNode, StatementNode, IncludeNode, and ScriptNode bindings."""
    c1 = ini.CommentNode("; comment 1")
    c2 = ini.CommentNode()
    c2.text = "; comment 1"
    assert c1 == c2
    assert "CommentNode" in repr(c1)

    s1 = ini.StatementNode("Damage = 50", "; inline")
    s2 = ini.StatementNode()
    s2.text = "Damage = 50"
    s2.comment = "; inline"
    assert s1 == s2
    assert "StatementNode" in repr(s1)

    inc1 = ini.IncludeNode('  "..\\shared\\macros.inc" ', "; inc cmt")
    inc2 = ini.IncludeNode()
    inc2.raw_path = '  "..\\shared\\macros.inc" '
    inc2.comment = "; inc cmt"
    assert inc1 == inc2
    assert inc1.clean_path == "../shared/macros.inc"
    assert "IncludeNode" in repr(inc1)

    scr = ini.ScriptNode(
        name="BeginScript",
        identifier="OnInit",
        comment="; pre",
        header_comment="; hdr",
        end_token="EndScript",
        end_comment="; end",
        content=['CurDrawableShowSubObject("BOW")', "if x then end"],
    )
    scr.name = "BeginScript"
    scr.identifier = "OnInit"
    scr.comment = "; pre"
    scr.header_comment = "; hdr"
    scr.end_token = "EndScript"
    scr.end_comment = "; end"
    scr.content = ['CurDrawableShowSubObject("BOW")', "if x then end"]

    assert scr == ini.ScriptNode(
        "BeginScript",
        "OnInit",
        "; pre",
        "; hdr",
        "EndScript",
        "; end",
        ['CurDrawableShowSubObject("BOW")', "if x then end"],
    )
    assert "ScriptNode" in repr(scr)
    printed_scr = scr.print(level=1, file_type=".ini")
    assert "    BeginScript OnInit ; hdr\n" in printed_scr
    assert '        CurDrawableShowSubObject("BOW")\n' in printed_scr
    assert "    EndScript ; end\n" in printed_scr


def test_construct_level_container_operations_and_indexing() -> None:
    """Verify ConstructLevel sequence protocol, negative indexing, and bounds checks."""
    block = ini.ConstructLevel(
        _class="Object",
        name="GondorArcher",
        identifier="ModTag_01",
        comment="; lead",
        header_comment="; hdr",
        end_token="End",
        end_comment="; tail",
    )
    assert len(block) == 0
    assert block._class == "Object"
    assert block.name == "GondorArcher"
    assert block.identifier == "ModTag_01"
    assert block.comment == "; lead"
    assert block.header_comment == "; hdr"
    assert block.end_token == "End"
    assert block.end_comment == "; tail"

    block._class = "ChildObject"
    block.name = "GondorRanger"
    block.identifier = "GondorArcher"
    block.comment = "; updated lead"
    block.header_comment = "; updated hdr"
    block.end_token = "END"
    block.end_comment = "; updated tail"

    block.append(ini.CommentNode("; inner cmt"))
    block.append(ini.StatementNode("Health = 200"))
    assert len(block) == 2

    # Positive and negative __getitem__ / __setitem__
    assert isinstance(block[0], ini.CommentNode)
    assert isinstance(block[-1], ini.StatementNode)

    block[-1] = ini.StatementNode("Health = 250", "; buffed")
    assert isinstance(block[1], ini.StatementNode)
    assert block[1].text == "Health = 250"

    with pytest.raises(IndexError):
        _ = block[5]
    with pytest.raises(IndexError):
        _ = block[-5]
    with pytest.raises(IndexError):
        block[5] = ini.CommentNode("; out")

    iterated = list(block)
    assert len(iterated) == 2
    assert "ConstructLevel" in repr(block)
    assert "ChildObject GondorRanger GondorArcher" in block.print()

    block.items = [ini.StatementNode("Side = Men")]
    assert len(block) == 1
    assert block == block


def test_str_entry_and_str_document_bindings(sample_str_file: Path) -> None:
    """Verify StrEntry, StrDocument, and StrParser bindings."""
    entry = ini.StrEntry(
        category="OBJECT",
        identifier="GondorSoldier",
        comment="; lead",
        header_comment="; hdr",
        end_token="End",
        end_comment="; end",
        items=[ini.CommentNode("; c"), ini.StatementNode('"Soldier"')],
    )
    entry.category = "OBJECT"
    entry.identifier = "GondorSoldier"
    entry.comment = "; lead"
    entry.header_comment = "; hdr"
    entry.end_token = "End"
    entry.end_comment = "; end"
    entry.items = [ini.CommentNode("; c"), ini.StatementNode('"Soldier"')]

    assert entry == entry
    assert "StrEntry" in repr(entry)
    assert "OBJECT:GondorSoldier" in entry.print()

    doc = ini.StrDocument("custom.str", [entry], ["warn 1"])
    doc.name = "custom2.str"
    doc.entries = [entry]
    doc.errors = []
    assert "StrDocument" in repr(doc)
    assert "OBJECT:GondorSoldier" in doc.print()

    parsed_doc = ini.parse_str(sample_str_file, strict=True)
    assert len(parsed_doc.entries) == 3
    assert not parsed_doc.errors


def test_construct_file_overloads_and_sequence_protocol(sample_ini_file: Path) -> None:
    """Verify both ConstructFile __init__ overloads, properties, and sequence methods."""
    # 1. Default empty ConstructFile
    empty_cf = ini.ConstructFile()
    assert len(empty_cf) == 0
    assert empty_cf.name == ""

    # 2. 7-argument metadata constructor with empty name (does not auto-construct)
    meta_empty = ini.ConstructFile(
        name="",
        comment="; doc cmt",
        defines=["#define A 1"],
        delimiters=[["Weapon"], []],
        start_level=0,
        strict=False,
        file_content=None,
    )
    assert meta_empty.comment == "; doc cmt"
    assert meta_empty.defines == ["#define A 1"]
    assert len(meta_empty) == 0

    # 3. 7-argument metadata constructor with non-empty name and content (auto-constructs)
    meta_parsed = ini.ConstructFile(
        name="inline.ini",
        comment="; doc",
        defines=[],
        delimiters=[],
        start_level=0,
        strict=True,
        file_content="Weapon GondorBow\n    AttackRange = 300\nEnd\n",
    )
    assert len(meta_parsed) == 1
    assert "ConstructFile" in repr(meta_parsed)

    # Property read/write accessors
    meta_parsed.comment = "; updated"
    meta_parsed.defines = ["#define RANGE 300"]
    meta_parsed.delimiters = [["Weapon"], []]
    meta_parsed.start_level = 0
    meta_parsed.strict = False
    meta_parsed.file_content = "Weapon GondorBow\nEnd\n"
    meta_parsed.current_level = 0
    meta_parsed.last_comment = ""
    meta_parsed.errors = ["custom warning"]
    assert meta_parsed.errors == ["custom warning"]

    meta_parsed.construct()
    assert meta_parsed.errors == []

    # Indexing and iteration on ConstructFile
    meta_parsed.append(ini.CommentNode("; appended"))
    assert len(meta_parsed) == 2
    assert isinstance(meta_parsed[-1], ini.CommentNode)

    meta_parsed[-1] = ini.StatementNode(" standalone = 1 ")
    assert isinstance(meta_parsed[1], ini.StatementNode)

    with pytest.raises(IndexError):
        _ = meta_parsed[10]
    with pytest.raises(IndexError):
        _ = meta_parsed[-10]
    with pytest.raises(IndexError):
        meta_parsed[10] = ini.CommentNode("; oob")

    items_list = list(meta_parsed)
    assert len(items_list) == 2
    meta_parsed.items = items_list

    # 4. Standard disk parsing via parse_ini
    disk_cf = ini.parse_ini(sample_ini_file, strict=True)
    reconstructed = disk_cf.print()
    reparsed = ini.parse_ini(sample_ini_file, strict=True, file_content=reconstructed)
    assert reparsed.print() == reconstructed


def test_module_level_functions_and_security_guards(
    ini_mod_directory: Path,
    sample_ini_file: Path,
    malformed_ini_file: Path,
) -> None:
    """Verify recognize_structure, validate_include, load_file, and scan_file_for_errors."""
    delims, start_lvl = ini.recognize_structure(sample_ini_file)
    assert start_lvl == 0
    assert len(delims) > 0

    # validate_include inside virtual root vs path traversal escape
    vroot = ini_mod_directory / "data" / "ini"
    hero_ini = vroot / "object" / "hero.ini"
    valid_inc = ini.IncludeNode('"includes\\armor.inc"')
    resolved = ini.validate_include(valid_inc, hero_ini, vroot)
    assert resolved.is_file()
    assert resolved.name == "armor.inc"

    escape_inc = ini.IncludeNode('"..\\..\\notes.txt"')
    with pytest.raises(ini.IniParseError, match="Security violation"):
        ini.validate_include(escape_inc, hero_ini, vroot)

    # load_file on .ini and .txt
    ini_text, loaded_delims = ini.load_file(sample_ini_file)
    assert "Object GondorAragorn" in ini_text
    assert len(loaded_delims) > 0

    txt_path = ini_mod_directory / "notes.txt"
    txt_text, txt_delims = ini.load_file(txt_path)
    assert txt_text == "Plain text documentation"
    assert txt_delims == []

    # scan_file_for_errors
    assert ini.scan_file_for_errors(sample_ini_file) == []
    errs = ini.scan_file_for_errors(malformed_ini_file)
    assert len(errs) == 2


def test_high_level_format_scan_and_inspect_api(
    tmp_path: Path,
    sample_ini_file: Path,
    sample_str_file: Path,
    malformed_ini_file: Path,
    ini_mod_directory: Path,
) -> None:
    """Verify format_ini, scan_ini, and inspect_ini across all execution branches."""
    # format_ini without output_path
    formatted_str = ini.format_ini(
        "inline.ini",
        file_content="Armor A\nArmor = DEFAULT 10%\nEnd\n",
    )
    assert "    Armor = DEFAULT 10%\n" in formatted_str

    # format_ini with output_path creating parent directory
    out_formatted = tmp_path / "formatted_out" / "hero.ini"
    ini.format_ini(sample_ini_file, output_path=out_formatted, strict=True)
    assert out_formatted.is_file()

    # scan_ini on missing path
    with pytest.raises(ini.IniParseError, match="Target path does not exist"):
        ini.scan_ini(tmp_path / "nonexistent_dir")

    # scan_ini on single file (non-strict and strict)
    single_scan = ini.scan_ini(sample_ini_file, strict=True)
    assert single_scan == {sample_ini_file: []}

    broken_scan = ini.scan_ini(malformed_ini_file, strict=False)
    assert len(broken_scan[malformed_ini_file]) == 2

    with pytest.raises(ini.IniParseError):
        ini.scan_ini(malformed_ini_file, strict=True)

    # scan_ini on directory
    dir_scan = ini.scan_ini(ini_mod_directory, strict=True)
    assert len(dir_scan) == 3
    assert all( errs == [] for errs in dir_scan.values() )

    # inspect_ini on .ini (contains CommentNode, IncludeNode, ScriptNode, ConstructLevel)
    ini_report = ini.inspect_ini(sample_ini_file, strict=True)
    assert ini_report.file_type == ".ini"
    assert ini_report.start_level == 0
    assert ini_report.define_count == 1
    assert ini_report.include_count == 2
    assert ini_report.block_counts == {"BeginScript": 1, "Object": 1}
    assert ini_report.errors == []

    # inspect_ini on .str (contains CommentNode and StrEntry)
    str_report = ini.inspect_ini(sample_str_file, strict=True)
    assert str_report.file_type == ".str"
    assert str_report.block_counts == {"OBJECT": 1, "GUI": 1}

    # inspect_ini on file with extensionless name fallback
    no_ext_report = ini.inspect_ini(
        "extensionless.ini",
        file_content="StandaloneStmt = 1\n",
    )
    assert no_ext_report.block_counts == {}
    assert no_ext_report.total_top_level_items == 1


def test_buffer_protocol_ingestion() -> None:
    """Verify parse_ini, parse_str, and recognize_structure correctly process zero-copy Buffer objects."""
    import lotm._core as _core

    ini_content = b"Object GondorFighter\n  Side = Men\nEnd\n"

    # Test bytes and memoryview ingestion for parse_ini (ConstructFile)
    doc_bytes = ini.parse_ini("dummy.ini", file_content=ini_content)
    assert len(doc_bytes) == 1
    assert "Side = Men" in doc_bytes.print()

    doc_mv = ini.parse_ini("dummy.ini", file_content=memoryview(ini_content))
    assert len(doc_mv) == 1

    # Test bytes and memoryview ingestion for parse_str (StrParser)
    str_content = b'OBJECT:Unit\n  "Soldier"\nEnd\n'
    str_bytes = ini.parse_str("dummy.str", file_content=str_content)
    assert len(str_bytes.entries) == 1
    assert "OBJECT:Unit" in str_bytes.print()

    str_mv = ini.parse_str("dummy.str", file_content=memoryview(str_content))
    assert len(str_mv.entries) == 1

    # Test native core recognize_structure_buffer
    delims, start_lvl = _core.ini.recognize_structure_buffer("dummy.ini", ini_content)
    assert start_lvl == 0
    assert len(delims) > 0


def test_utf8_bom_and_cp1252_encoding_fallback(tmp_path: Path) -> None:
    """Verify UTF-8 BOM stripping and Windows-1252 fallback across disk and Buffer APIs."""
    # 1. UTF-8 with BOM on disk
    bom_ini_path = tmp_path / "bom_unit.ini"
    bom_ini_path.write_bytes(b"\xef\xbb\xbfObject GondorArcher\n    Side = Men\nEnd\n")
    bom_doc = ini.parse_ini(bom_ini_path, strict=True)
    assert len(bom_doc) == 1
    assert isinstance(bom_doc[0], ini.ConstructLevel)
    assert bom_doc[0]._class == "Object"

    # 2. Windows-1252 encoded .ini and .str payloads (smart quotes 0x93/0x94, Euro 0x80, é 0xE9)
    # Passed correctly as raw byte strings
    cp1252_ini_bytes = (
        b"Object Rohirrim ; \x93\xc9omer's Guard \x80\x94\n"
        b"    Side = Men\n"
        b"End\n"
    )
    cp1252_ini_path = tmp_path / "cp1252_unit.ini"
    cp1252_ini_path.write_bytes(cp1252_ini_bytes)

    disk_ini_doc = ini.parse_ini(cp1252_ini_path, strict=True)
    assert len(disk_ini_doc) == 1
    assert "“Éomer's Guard €”" in disk_ini_doc.print()

    buf_ini_doc = ini.parse_ini("memory_cp1252.ini", strict=True, file_content=cp1252_ini_bytes)
    assert "“Éomer's Guard €”" in buf_ini_doc.print()

    cp1252_str_bytes = b'OBJECT:Rohirrim\n    "Cavalier d\'\xc9lite \x80"\nEnd\n'
    str_doc = ini.parse_str("lotr.str", strict=True, file_content=cp1252_str_bytes)
    assert len(str_doc.entries) == 1
    assert "Cavalier d'Élite €" in str_doc.print()
