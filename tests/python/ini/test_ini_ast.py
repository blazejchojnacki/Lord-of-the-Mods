"""
@file tests/python/ini/test_ini_ast.py
@brief Unit tests for lotm.ini C++ AST node bindings, reference semantics, and module-level helpers.

Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
Part of the Lord of the Mods (lotm) project.
SPDX-License-Identifier: GPL-3.0-or-later
"""

from __future__ import annotations

from pathlib import Path
import pytest

import lotm._core as _core
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

    with pytest.raises(ini.IniParseError):
        scr.name = "A" * 257
    with pytest.raises(ini.IniParseError):
        scr.identifier = "B" * 513

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

    with pytest.raises(ini.IniParseError):
        block._class = "C" * 257
    with pytest.raises(ini.IniParseError):
        block.name = "N" * 257
    with pytest.raises(ini.IniParseError):
        block.identifier = "I" * 513

    block.append(ini.CommentNode("; inner cmt"))
    block.append(ini.StatementNode("Health = 200"))
    assert len(block) == 2

    # Positive and negative __getitem__ / __setitem__ and reference semantics
    assert isinstance(block[0], ini.CommentNode)
    block[0].text = "; mutated inner cmt"
    assert isinstance(block[0], ini.CommentNode)
    assert block[0].text == "; mutated inner cmt"

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

    with pytest.raises(ini.IniParseError):
        entry.category = "C" * 257
    with pytest.raises(ini.IniParseError):
        entry.identifier = "I" * 513

    entry.append(ini.CommentNode("; appended child"))
    assert len(entry) == 3
    assert isinstance(entry[-1], ini.CommentNode)
    entry[-1] = ini.CommentNode("; replaced child")
    assert list(entry)[-1] == ini.CommentNode("; replaced child")

    with pytest.raises(IndexError):
        _ = entry[10]

    assert entry == entry
    assert "StrEntry" in repr(entry)
    assert "OBJECT:GondorSoldier" in entry.print()

    doc = ini.StrDocument("custom.str", [entry], ["warn 1"])
    doc.name = "custom2.str"
    doc.entries = [entry]
    doc.errors = []
    doc.append(ini.CommentNode("; doc tail"))
    assert len(doc) == 2
    assert isinstance(doc[0], ini.StrEntry)
    doc[0].identifier = "GondorElite"
    assert isinstance(doc[0], ini.StrEntry)
    assert doc[0].identifier == "GondorElite"
    doc[-1] = ini.CommentNode("; doc tail 2")
    assert len(list(doc)) == 2
    assert doc == doc

    with pytest.raises(IndexError):
        _ = doc[10]

    assert "StrDocument" in repr(doc)
    assert "OBJECT:GondorElite" in doc.print()

    parsed_doc = ini.StrParser.parse_file(sample_str_file, strict=True)
    assert len(parsed_doc.entries) == 3
    assert not parsed_doc.errors


def test_construct_file_overloads_and_sequence_protocol(sample_ini_file: Path) -> None:
    """Verify ConstructFile __init__ overloads, properties, and sequence methods."""
    # Default empty ConstructFile
    empty_cf = ini.ConstructFile()
    assert len(empty_cf) == 0
    assert empty_cf.name == ""

    # 7-argument metadata constructor with empty name (does not auto-construct)
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

    # 7-argument metadata constructor with non-empty name and content (auto-constructs)
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

    # Verify in-place reference semantics on ConstructFile indexing and iteration
    assert isinstance(meta_parsed[0], ini.ConstructLevel)
    meta_parsed[0].name = "MirkwoodBow"
    assert "Weapon MirkwoodBow" in meta_parsed.print()

    for root_node in meta_parsed:
        if isinstance(root_node, ini.ConstructLevel):
            root_node.name = "LorienBow"
    assert "Weapon LorienBow" in meta_parsed.print()

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
    assert meta_parsed == meta_parsed

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

    # Standard disk parsing via ConstructFile
    disk_cf = ini.ConstructFile(sample_ini_file, strict=True)
    reconstructed = disk_cf.print()
    reparsed = ini.ConstructFile(sample_ini_file, strict=True, file_content=reconstructed)
    assert reparsed.print() == reconstructed


def test_module_level_functions_and_security_guards(
    ini_mod_directory: Path,
    sample_ini_file: Path,
    malformed_ini_file: Path,
) -> None:
    """Verify recognize_structure, recognize_structure_buffer, validate_include, load_file, and scan_file_for_errors."""
    delims, start_lvl = ini.recognize_structure(sample_ini_file)
    assert start_lvl == 0
    assert len(delims) > 0

    buf_delims, buf_start = _core.ini.recognize_structure_buffer(
        "dummy.ini",
        b"Object GondorFighter\n  Side = Men\nEnd\n",
    )
    assert buf_start == 0
    assert len(buf_delims) > 0

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
