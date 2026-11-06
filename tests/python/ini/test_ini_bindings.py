"""
@file tests/python/ini/test_ini_bindings.py
@brief Tests for native C++ AST nodes, unwrapping, and nanobind bindings.

Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
Part of the Lord of the Mods (lotm) project.
SPDX-License-Identifier: GPL-3.0-or-later
"""

from __future__ import annotations

from lotm.ini import (
    AstNode,
    CommentNode,
    ConstructLevel,
    IncludeNode,
    StatementNode,
    StrDocument,
    StrEntry,
    parse_buffer,
    unwrap_node,
)


def test_basic_ast_nodes_and_variant_unwrapping() -> None:
    stmt = StatementNode("MaxHealth = 100")
    assert stmt.text == "MaxHealth = 100"
    stmt.text = "MaxHealth = 250"
    assert stmt.text == "MaxHealth = 250"

    comment = CommentNode("; balance tweak")
    assert comment.text == "; balance tweak"

    inc = IncludeNode('#include "macros.inc"')
    assert inc.text == '#include "macros.inc"'

    wrapped_stmt = AstNode(stmt)
    unwrapped = unwrap_node(wrapped_stmt)
    assert isinstance(unwrapped, StatementNode)
    assert unwrapped.text == "MaxHealth = 250"

    # Calling unwrap_node on an already unwrapped node is idempotent
    assert unwrap_node(stmt) is stmt


def test_construct_level_manual_building_and_printing() -> None:
    block = ConstructLevel("Object", "GondorArcher", "ModTag", "; Heroic unit")
    assert block._class == "Object"
    assert block.name == "GondorArcher"
    assert block.identifier == "ModTag"
    assert block.comment == "; Heroic unit"

    block.append(AstNode(CommentNode("; Health line\n; Second comment line")))
    block.append(AstNode(StatementNode("Side = Men")))
    block.end_token = "End"

    printed_ini = block.print(0, ".ini")
    assert "; Heroic unit\n" in printed_ini
    assert "Object GondorArcher ModTag\n" in printed_ini
    assert "\tSide = Men\n" in printed_ini
    assert printed_ini.endswith("End\n")

    # Colon-separated header when file_type is not .ini/.inc
    printed_other = block.print(0, ".str")
    assert "Object:GondorArcher:ModTag\n" in printed_other


def test_str_entry_and_document_manual_manipulation() -> None:
    entry = StrEntry()
    entry.category = "OBJECT"
    entry.identifier = "GondorSoldier"
    entry.comment = "// Infantry unit"
    entry.end_token = "End"
    entry.items = [StatementNode('"Gondor Soldier"'), CommentNode("// local note")]

    entry_text = entry.print()
    assert "// Infantry unit\nOBJECT:GondorSoldier\n" in entry_text
    assert '\t"Gondor Soldier"\n' in entry_text
    assert entry_text.endswith("End\n")

    # Category without identifier
    entry_no_id = StrEntry()
    entry_no_id.category = " standalone_category "
    entry_no_id.end_token = "End"
    assert " standalone_category \n" in entry_no_id.print()

    doc = StrDocument()
    doc.name = "custom.str"
    doc.entries = [CommentNode("// Header"), entry]
    doc_text = doc.print()
    assert "// Header\n" in doc_text
    assert "OBJECT:GondorSoldier\n" in doc_text


def test_parse_buffer_zero_copy_shim() -> None:
    payload = b"Object MordorFighter\n  Side = Mordor\nEnd\n"
    size = parse_buffer(payload, strict=False)
    assert size == len(payload)
