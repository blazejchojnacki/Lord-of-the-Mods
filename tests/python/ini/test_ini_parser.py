"""
@file tests/python/ini/test_ini_parser.py
@brief Unit tests for lotm.ini.parser (parse_ini, parse_str, Buffer protocol, and legacy encodings).

Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
Part of the Lord of the Mods (lotm) project.
SPDX-License-Identifier: GPL-3.0-or-later
"""

from __future__ import annotations

from pathlib import Path
import pytest

import lotm.ini as ini


def test_parse_ini_and_parse_str_from_disk_and_strings(
    sample_ini_file: Path,
    sample_inc_file: Path,
    sample_str_file: Path,
    malformed_ini_file: Path,
) -> None:
    """Verify parse_ini and parse_str on disk files, .inc files, and in-memory strings."""
    ini_doc = ini.parse_ini(sample_ini_file, strict=True)
    reconstructed = ini_doc.print()
    reparsed = ini.parse_ini(sample_ini_file, strict=True, file_content=reconstructed)
    assert reparsed.print() == reconstructed

    inc_doc = ini.parse_ini(sample_inc_file, strict=True)
    assert inc_doc.start_level == 2
    assert len(inc_doc) == 2

    str_doc = ini.parse_str(sample_str_file, strict=True)
    assert len(str_doc.entries) == 3
    assert not str_doc.errors

    inline_str_doc = ini.parse_str(
        "inline.str",
        strict=True,
        file_content='OBJECT:GondorArcher\n    "Gondor Archer"\nEnd\n',
    )
    assert len(inline_str_doc) == 1

    lenient_doc = ini.parse_ini(malformed_ini_file, strict=False)
    assert len(lenient_doc.errors) == 2

    with pytest.raises(ini.IniParseError):
        ini.parse_ini(malformed_ini_file, strict=True)


def test_buffer_protocol_ingestion() -> None:
    """Verify parse_ini and parse_str correctly process zero-copy Buffer objects."""
    ini_content = b"Object GondorFighter\n  Side = Men\nEnd\n"

    # Test bytes, bytearray, memoryview, and empty b"" ingestion for parse_ini (ConstructFile)
    doc_bytes = ini.parse_ini("dummy.ini", file_content=ini_content)
    assert len(doc_bytes) == 1
    assert "Side = Men" in doc_bytes.print()

    doc_ba = ini.parse_ini("dummy.ini", file_content=bytearray(ini_content))
    assert len(doc_ba) == 1

    doc_mv = ini.parse_ini("dummy.ini", file_content=memoryview(ini_content))
    assert len(doc_mv) == 1

    doc_empty_buf = ini.parse_ini("empty_virtual.ini", strict=True, file_content=b"")
    assert len(doc_empty_buf) == 0

    # Test bytes and memoryview ingestion for parse_str (StrParser)
    str_content = b'OBJECT:Unit\n  "Soldier"\nEnd\n'
    str_bytes = ini.parse_str("dummy.str", file_content=str_content)
    assert len(str_bytes.entries) == 1
    assert "OBJECT:Unit" in str_bytes.print()

    str_mv = ini.parse_str("dummy.str", file_content=memoryview(str_content))
    assert len(str_mv.entries) == 1


def test_utf8_bom_and_cp1252_encoding_fallback(tmp_path: Path) -> None:
    """Verify UTF-8 BOM stripping and Windows-1252 fallback across disk and Buffer APIs."""
    # UTF-8 with BOM on disk
    bom_ini_path = tmp_path / "bom_unit.ini"
    bom_ini_path.write_bytes(b"\xef\xbb\xbfObject GondorArcher\n    Side = Men\nEnd\n")
    bom_doc = ini.parse_ini(bom_ini_path, strict=True)
    assert len(bom_doc) == 1
    assert isinstance(bom_doc[0], ini.ConstructLevel)
    assert bom_doc[0]._class == "Object"

    # Windows-1252 encoded .ini and .str payloads (smart quotes 0x93/0x94, Euro 0x80, é 0xE9)
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
