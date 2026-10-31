"""
@file tests/python/big/test_big_api.py
@brief Integration tests for the programmatic Python API of the BIG archive module.

Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
Part of the Lord of the Mods (lotm) project.
SPDX-License-Identifier: GPL-3.0-or-later
"""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import pytest
import struct

import lotm.big as big


def test_programmatic_packing_and_unpacking_roundtrip(standard_mod_directory: Path, tmp_path: Path):
    """Verify that packing and unpacking a directory maintains structural and byte fidelity."""
    archive_path = tmp_path / "mod_test.big"
    extract_dir = tmp_path / "output_dir"

    # Pack the standard fixture directory
    big.pack(standard_mod_directory, archive_path)
    assert archive_path.is_file()
    assert archive_path.stat().st_size > 0

    # Unpack the generated archive
    entries = big.unpack(archive_path, extract_dir)

    # Verify returned entries list
    assert len(entries) == 3
    names = [e.name for e in entries]
    assert "art\\texture.dds" in names
    assert "data\\weapon.ini" in names
    assert "readme.txt" in names

    # Verify extracted file fidelity
    extracted_ini = extract_dir / "data" / "weapon.ini"
    assert extracted_ini.exists()
    assert extracted_ini.read_text(encoding="utf-8") == "Damage=50"


def test_pack_invalid_source_directory_raises_error(tmp_path: Path):
    """Verify that pack() raises NotADirectoryError when given a non-existent path."""
    missing_dir = tmp_path / "does_not_exist"
    out_file = tmp_path / "out.big"

    with pytest.raises(NotADirectoryError, match="does not exist"):
        big.pack(missing_dir, out_file)


def test_pack_output_inside_source_directory_raises_error(standard_mod_directory: Path):
    """Verify that packing an archive directly inside the source directory raises ValueError."""
    self_included_out = standard_mod_directory / "nested.big"

    with pytest.raises(ValueError, match="cannot reside inside the source directory"):
        big.pack(standard_mod_directory, self_included_out)


def test_unpack_missing_archive_raises_error(tmp_path: Path):
    """Verify that unpack() raises FileNotFoundError when target archive is missing."""
    missing_file = tmp_path / "ghost.big"
    out_dir = tmp_path / "out"

    with pytest.raises(FileNotFoundError, match="Archive not found"):
        big.unpack(missing_file, out_dir)


def test_cpp_api_raises_big_format_error_on_corrupt_magic(tmp_path: Path):
    """Verify that the C++ bindings propagate BigFormatError for invalid magic headers."""
    bad_archive = tmp_path / "corrupt.big"
    bad_archive.write_bytes(b"BOGUS_DATA")

    with pytest.raises(big.BigFormatError, match="Not a valid BIG4 file"):
        big.BigArchive(bad_archive)


def test_cpp_api_raises_big_security_error_on_zip_slip(tmp_path: Path):
    """Verify that the C++ bindings propagate BigSecurityError for path traversal attempts."""
    bad_archive = tmp_path / "zipslip.big"
    
    name = b"../escaped.txt\x00"
    header_size = 16 + 8 + len(name)
    payload_size = 4
    offset = header_size
    total_size = header_size + payload_size
    
    with open(bad_archive, "wb") as f:
        f.write(b"BIG4")
        f.write(struct.pack("<I", total_size))
        f.write(struct.pack(">I", 1))
        f.write(struct.pack(">I", header_size))
        f.write(struct.pack(">I", offset))
        f.write(struct.pack(">I", payload_size))
        f.write(name)
        f.write(b"DATA")
        
    archive = big.BigArchive(bad_archive)
    out_dir = tmp_path / "out"
    
    with pytest.raises(big.BigSecurityError, match="Path traversal attempt"):
        archive.extract_all(out_dir)


def test_concurrent_pack_and_unpack_releases_gil(standard_mod_directory: Path, tmp_path: Path):
    """Verify multi-threaded packing and extraction execute concurrently without GIL deadlocks."""
    def worker(worker_id: int) -> int:
        archive_path = tmp_path / f"concurrent_{worker_id}.big"
        extract_dir = tmp_path / f"extract_{worker_id}"
        big.pack(standard_mod_directory, archive_path)
        entries = big.unpack(archive_path, extract_dir)
        return len(entries)

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(worker, range(4)))

    assert results == [3, 3, 3, 3]


def test_cpp_api_progress_callbacks_propagate(standard_mod_directory: Path, tmp_path: Path):
    """Verify that C++ progress callbacks correctly invoke Python callables."""
    archive_path = tmp_path / "callback.big"
    out_dir = tmp_path / "out"
    
    packed = []
    def pack_cb(name: str) -> None:
        packed.append(name)
        
    big.BigPacker.pack_from_directory(standard_mod_directory, archive_path, progress_callback=pack_cb)
    
    assert len(packed) == 3
    assert any("weapon.ini" in p for p in packed)
    
    archive = big.BigArchive(archive_path)
    extracted = []
    def extract_cb(name: str) -> None:
        extracted.append(name)
        
    archive.extract_all(out_dir, progress_callback=extract_cb)
    
    assert len(extracted) == 3
    assert any("texture.dds" in e for e in extracted)

    def test_pack_exception_in_callback_cleans_up_partial_file(standard_mod_directory: Path, tmp_path: Path):
    """Verify that Python exceptions inside the C++ callback trigger RAII cleanup of the output file."""
    archive_path = tmp_path / "failed_pack.big"
    
    def raising_cb(name: str) -> None:
        if "texture.dds" in name:
            raise RuntimeError("Simulated user interrupt during packing")
            
    with pytest.raises(RuntimeError, match="Simulated user interrupt"):
        big.BigPacker.pack_from_directory(standard_mod_directory, archive_path, progress_callback=raising_cb)
        
    assert not archive_path.exists(), "The partial .big file was not deleted by the RAII guard"


def test_unpack_exception_in_callback_aborts_safely(standard_mod_directory: Path, tmp_path: Path):
    """Verify GIL safe exception unwinding during extraction."""
    archive = tmp_path / "valid.big"
    out_dir = tmp_path / "aborted_extract"
    big.pack(standard_mod_directory, archive)
    
    def raising_cb(name: str) -> None:
        raise ValueError("Simulated extraction abort")
        
    with pytest.raises(ValueError, match="Simulated extraction abort"):
        archive_obj = big.BigArchive(archive)
        archive_obj.extract_all(out_dir, progress_callback=raising_cb)


def test_pack_case_insensitive_collision_raises_error(tmp_path: Path):
    """Verify that packing directories with case-insensitive collisions raises an error."""
    src_dir = tmp_path / "colliding_mod"
    src_dir.mkdir()
    (src_dir / "data").mkdir()
    (src_dir / "data" / "unit.ini").write_text("Damage=10", encoding="utf-8")
    (src_dir / "data" / "UNIT.INI").write_text("Damage=99", encoding="utf-8")
    
    out_file = tmp_path / "collision.big"
    
    with pytest.raises(ValueError, match="Duplicate case-insensitive path"):
        big.pack(src_dir, out_file)
