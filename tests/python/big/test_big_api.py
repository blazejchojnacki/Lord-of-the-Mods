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

    packed_reports: list[str] = []
    # Pack the standard fixture directory
    big.pack(
        standard_mod_directory,
        archive_path,
        progress_callback=lambda r: (packed_reports.append(r.entry_name), True)[1],
    )
    assert archive_path.is_file()
    assert archive_path.stat().st_size > 0
    assert len(packed_reports) == 3

    unpacked_reports: list[str] = []
    # Unpack the generated archive
    entries = big.unpack(
        archive_path,
        extract_dir,
        progress_callback=lambda r: (unpacked_reports.append(r.entry_name), None)[1],
    )
    assert len(unpacked_reports) == 3

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


def test_pack_invalid_source_directory_raises_error(standard_mod_directory: Path, tmp_path: Path):
    """Verify that pack() raises NotADirectoryError or FileNotFoundError for missing paths."""
    missing_dir = tmp_path / "does_not_exist"
    out_file = tmp_path / "out.big"

    with pytest.raises(NotADirectoryError, match="does not exist"):
        big.pack(missing_dir, out_file)

    missing_parent_out = tmp_path / "missing_parent" / "out.big"
    with pytest.raises(FileNotFoundError, match="does not exist"):
        big.pack(standard_mod_directory, missing_parent_out)


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


def test_unpack_missing_output_dir_strict_mode(standard_mod_directory: Path, tmp_path: Path):
    """Verify that unpack() respects create_directories=False."""
    archive_path = tmp_path / "mod.big"
    big.pack(standard_mod_directory, archive_path)

    missing_out = tmp_path / "missing_strict"
    with pytest.raises(FileNotFoundError, match="does not exist"):
        big.unpack(archive_path, missing_out, create_directories=False)


def test_progress_report_lifetime_retention(standard_mod_directory: Path, tmp_path: Path):
    """Verify ProgressReport objects can be safely retained and accessed after operations."""
    archive_path = tmp_path / "retention.big"

    reports: list[big.ProgressReport] = []
    def pack_cb(report: big.ProgressReport) -> bool:
        reports.append(report)
        return True

    big.pack(standard_mod_directory, archive_path, progress_callback=pack_cb)

    # Accessing entry_name on retained objects must not crash (UAF) and must return correct strings
    assert len(reports) == 3
    entry_names = [r.entry_name for r in reports]
    assert "data\\weapon.ini" in entry_names
    assert "art\\texture.dds" in entry_names
    assert "readme.txt" in entry_names

    # Check string representation uses the safe retained memory
    for r in reports:
        assert "ProgressReport" in repr(r)
        assert str(r.bytes_transferred) in repr(r)


def test_diff_streaming_io_and_bounds_failures(tmp_path: Path):
    """Verify streaming diff propagates native IO and Format errors safely to Python."""
    base_path = tmp_path / "base.big"
    target_path = tmp_path / "target.big"

    base_path.write_bytes(big.pack_to_memory({"data/same_size.ini": b"1234"}))
    target_path.write_bytes(big.pack_to_memory({"data/same_size.ini": b"5678"}))

    # Truncate the target file physically to trigger streaming bounds check failure
    with open(target_path, "ab") as f:
        f.truncate(target_path.stat().st_size - 2)

    with pytest.raises(big.BigFormatError, match="Extraction bounds exceeded"):
        big.diff(base_path, target_path)


def test_cpp_api_raises_big_format_error_on_corrupt_magic(tmp_path: Path):
    """Verify that the C++ bindings propagate BigFormatError for invalid and binary magic headers."""
    bad_archive = tmp_path / "corrupt.big"
    bad_archive.write_bytes(b"BOGUS_DATA")

    with pytest.raises(big.BigFormatError, match="Not a valid BIG4 file"):
        big.BigArchive(bad_archive)

    binary_magic = tmp_path / "binary_magic.big"
    binary_magic.write_bytes(b"\x80\xff\x00\x7f_DATA")

    with pytest.raises(big.BigFormatError, match=r"Found: \?\?\?\?"):
        big.BigArchive(binary_magic)


def test_cpp_api_raises_big_format_error_on_total_size_underflow(tmp_path: Path):
    """Verify that header total_size smaller than header_size raises BigFormatError."""
    bad_archive = tmp_path / "underflow.big"
    with open(bad_archive, "wb") as f:
        f.write(b"BIG4")
        f.write(struct.pack("<I", 12))  # total_size < header_size (24)
        f.write(struct.pack(">I", 0))
        f.write(struct.pack(">I", 24))
        f.write(b"L219\x00\x00\x00\x00")

    with pytest.raises(big.BigFormatError, match="Corrupted BIG4 index"):
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

    with pytest.raises(big.BigSecurityError, match="Directory traversal"):
        archive.extract_all(out_dir)


@pytest.mark.parametrize("malicious_path", [
    b"\\\\?\\C:\\Windows\\System32\\cmd.exe\x00",
    b"\\??\\malicious.exe\x00",
    b"C:../escaped.txt\x00",
    b"folder .\\payload.txt\x00",
    b"data\\file<invalid>.txt\x00",
    b"data\\COM\xC2\xB9.ini\x00",
    b"data\\CLOCK$.txt\x00",
])
def test_cpp_api_raises_big_security_error_on_ntfs_evasion(tmp_path: Path, malicious_path: bytes):
    """Verify that the C++ bindings propagate BigSecurityError for extended NTFS path evasions."""
    bad_archive = tmp_path / "ntfs_evasion.big"

    header_size = 16 + 8 + len(malicious_path)
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
        f.write(malicious_path)
        f.write(b"DATA")

    archive = big.BigArchive(bad_archive)
    out_dir = tmp_path / "out"

    with pytest.raises(big.BigSecurityError, match="prefix|drive-relative|Unsafe"):
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
    """Verify that C++ progress callbacks correctly invoke Python callables with ProgressReport."""
    archive_path = tmp_path / "callback.big"
    out_dir = tmp_path / "out"

    packed: list[str] = []
    def pack_cb(report: big.ProgressReport) -> bool:
        assert report.bytes_transferred == report.file_size
        assert report.total_bytes_transferred <= report.total_archive_size
        assert "ProgressReport" in repr(report)
        packed.append(report.entry_name)
        return True

    big.BigPacker.pack_from_directory(standard_mod_directory, archive_path, progress_callback=pack_cb)

    assert len(packed) == 3
    assert any("weapon.ini" in p for p in packed)

    archive = big.BigArchive(archive_path)
    extracted: list[str] = []
    def extract_cb(report: big.ProgressReport) -> None:
        extracted.append(report.entry_name)

    archive.extract_all(out_dir, progress_callback=extract_cb)

    assert len(extracted) == 3
    assert any("texture.dds" in e for e in extracted)


def test_cooperative_cancellation_across_python_api(standard_mod_directory: Path, tmp_path: Path):
    """Verify returning False from progress_callback cancels operations cleanly."""
    archive_path = tmp_path / "cancel_pack.big"
    with pytest.raises(big.BigArchiveError, match="cancelled"):
        big.pack(standard_mod_directory, archive_path, progress_callback=lambda _: False)
    assert not archive_path.exists()

    with pytest.raises(big.BigArchiveError, match="cancelled"):
        big.pack_to_memory(standard_mod_directory, progress_callback=lambda _: False)

    with pytest.raises(big.BigArchiveError, match="cancelled"):
        big.pack_to_memory({"a.txt": b"1"}, progress_callback=lambda _: False)

    valid_arc = tmp_path / "valid.big"
    big.pack(standard_mod_directory, valid_arc)
    with pytest.raises(big.BigArchiveError, match="cancelled"):
        big.unpack(valid_arc, tmp_path / "cancel_out", progress_callback=lambda _: False)


def test_pack_exception_in_callback_cleans_up_partial_file(standard_mod_directory: Path, tmp_path: Path):
    """Verify that Python exceptions inside the C++ callback clean up temp files and preserve existing targets."""
    archive_path = tmp_path / "failed_pack.big"

    def raising_cb(report: big.ProgressReport) -> bool:
        if "texture.dds" in report.entry_name:
            raise RuntimeError("Simulated user interrupt during packing")
        return True

    with pytest.raises(RuntimeError, match="Simulated user interrupt"):
        big.BigPacker.pack_from_directory(standard_mod_directory, archive_path, progress_callback=raising_cb)

    assert not archive_path.exists(), "The partial .big file was not deleted by the RAII guard"

    # Pre-existing target file must remain intact if an overwrite pack is interrupted
    archive_path.write_bytes(b"ORIGINAL_ARCHIVE_BYTES")
    with pytest.raises(RuntimeError, match="Simulated user interrupt"):
        big.BigPacker.pack_from_directory(standard_mod_directory, archive_path, progress_callback=raising_cb)

    assert archive_path.read_bytes() == b"ORIGINAL_ARCHIVE_BYTES"


def test_unpack_exception_in_callback_aborts_safely(standard_mod_directory: Path, tmp_path: Path):
    """Verify GIL safe exception unwinding during extraction."""
    archive = tmp_path / "valid.big"
    out_dir = tmp_path / "aborted_extract"
    big.pack(standard_mod_directory, archive)

    def raising_cb(report: big.ProgressReport) -> bool:
        raise ValueError("Simulated extraction abort")

    with pytest.raises(ValueError, match="Simulated extraction abort"):
        archive_obj = big.BigArchive(archive)
        archive_obj.extract_all(out_dir, progress_callback=raising_cb)


def test_in_memory_read_entry_and_buffer_protocol(standard_mod_directory: Path, tmp_path: Path):
    """Verify single-file in-memory extraction via path string, BigEntry, and memoryview."""
    archive_path = tmp_path / "in_memory.big"
    big.pack(standard_mod_directory, archive_path)

    with big.BigArchive(archive_path) as arc:
        assert not arc.closed
        assert arc.file_path == archive_path

        # Test value semantics (set deduplication)
        entries_set = set(arc.get_entries())
        assert len(entries_set) == 3
        # Ensure __eq__ overrides pointer identity
        assert arc.get_entries()[0] == arc.get_entries()[0]

        # Read by normalized case-insensitive path string
        raw_ini = arc.read_entry("DATA/weapon.ini")
        assert isinstance(raw_ini, bytes)
        assert raw_ini == b"Damage=50"

        # Verify Python Buffer Protocol compatibility via memoryview
        with memoryview(raw_ini) as mv:
            assert mv[:6].tobytes() == b"Damage"

        # Read by BigEntry metadata record
        entries = arc.get_entries()
        dds_entry = next(e for e in entries if "texture.dds" in e.name)
        raw_dds = arc.read_entry(dds_entry)
        assert raw_dds == b"DDS_HEADER_DATA"

        # Verify streaming entry
        streamed_chunks = []
        def chunk_cb(mv: memoryview) -> bool:
            streamed_chunks.append(mv.tobytes())
            return True
        arc.stream_entry("DATA/weapon.ini", chunk_cb)
        assert b"".join(streamed_chunks) == b"Damage=50"

    assert arc.closed


def test_read_entry_missing_file_raises_big_archive_error(standard_mod_directory: Path, tmp_path: Path):
    """Verify that requesting a non-existent entry raises BigArchiveError."""
    archive_path = tmp_path / "missing_entry.big"
    big.pack(standard_mod_directory, archive_path)

    with big.BigArchive(archive_path) as arc:
        with pytest.raises(big.BigArchiveError, match="Entry not found"):
            arc.read_entry("data/missing_unit.ini")


def test_closed_archive_rejects_operations_and_context_reentry(standard_mod_directory: Path, tmp_path: Path):
    """Verify that closing an archive blocks further operations and context manager re-entry."""
    archive_path = tmp_path / "lifecycle.big"
    big.pack(standard_mod_directory, archive_path)

    arc = big.BigArchive(archive_path)
    first_entry = arc.get_entries()[0]
    arc.close()

    assert arc.closed

    with pytest.raises(big.BigArchiveError, match="closed archive"):
        arc.get_entries()

    with pytest.raises(big.BigArchiveError, match="closed archive"):
        arc.read_entry("readme.txt")

    with pytest.raises(big.BigArchiveError, match="closed archive"):
        arc.read_entry(first_entry)

    with pytest.raises(big.BigArchiveError, match="closed archive"):
        arc.extract_all(tmp_path / "out")

    with pytest.raises(big.BigArchiveError, match="closed archive"):
        with arc:
            pass


def test_pack_to_memory_from_directory_and_records(standard_mod_directory: Path, tmp_path: Path):
    """Verify in-memory archive packing from a directory, a mapping, and buffer-protocol objects."""
    disk_archive = tmp_path / "disk_reference.big"
    big.pack(standard_mod_directory, disk_archive)
    expected_bytes = disk_archive.read_bytes()

    # 1. Pack from directory path
    dir_reports: list[str] = []
    mem_from_dir = big.pack_to_memory(
        standard_mod_directory,
        progress_callback=lambda r: (dir_reports.append(r.entry_name), True)[1],
    )
    assert isinstance(mem_from_dir, bytes)
    assert mem_from_dir == expected_bytes
    assert len(dir_reports) == 3

    # 2. Pack from Mapping[str, bytes]
    mapping_input = {
        "data/weapon.ini": b"Damage=50",
        "art/texture.dds": b"DDS_HEADER_DATA",
        "readme.txt": b"Lord of the Mods",
    }
    dict_reports: list[str] = []
    mem_from_dict = big.pack_to_memory(
        mapping_input,
        progress_callback=lambda r: (dict_reports.append(r.entry_name), None)[1],
    )
    assert mem_from_dict == expected_bytes
    assert len(dict_reports) == 3

    # 3. Pack from sequence of (path, bytes) tuples
    sequence_input = list(mapping_input.items())
    mem_from_seq = big.pack_to_memory(sequence_input)
    assert mem_from_seq == expected_bytes

    # 4. Pack zero-copy from bytearray and memoryview slices
    raw_padded = bytearray(b"__Damage=50__")
    with memoryview(raw_padded)[2:11] as ini_slice:
        buffer_input = [
            ("data/weapon.ini", ini_slice),
            ("art/texture.dds", bytearray(b"DDS_HEADER_DATA")),
            ("readme.txt", memoryview(b"Lord of the Mods")),
        ]
        mem_from_buffers = big.pack_to_memory(buffer_input)
        assert mem_from_buffers == expected_bytes


def test_pack_to_memory_validation_and_callbacks(tmp_path: Path):
    """Verify error propagation and progress callbacks for in-memory packing."""
    missing_dir = tmp_path / "missing_source"
    with pytest.raises(NotADirectoryError, match="does not exist"):
        big.pack_to_memory(missing_dir)

    with pytest.raises(ValueError, match="Duplicate case-insensitive path"):
        big.pack_to_memory([("data/unit.ini", b"1"), ("DATA\\UNIT.INI", b"2")])

    with pytest.raises(ValueError, match="Entry path cannot be empty"):
        big.pack_to_memory([("", b"payload")])

    with pytest.raises(TypeError):
        big.BigPacker.pack_to_memory([("a.txt", 12345)])  # type: ignore[list-item]

    reported: list[str] = []
    raw_bytes = big.BigPacker.pack_to_memory(
        [("b.txt", b"B"), ("a.txt", b"A")],
        progress_callback=lambda r: (reported.append(r.entry_name), True)[1]
    )
    assert len(raw_bytes) > 0
    assert reported == ["a.txt", "b.txt"]


def test_pack_to_memory_path_injection():
    """Verify pack_to_memory blocks embedded nulls and directory traversals."""
    with pytest.raises(ValueError, match="Invalid or unsafe archive entry path"):
        big.pack_to_memory([("data/weapon.ini\x00b.ini", b"payload")])
    with pytest.raises(ValueError, match="Invalid or unsafe archive entry path"):
        big.pack_to_memory([("../escaped.txt", b"payload")])
    with pytest.raises(ValueError, match="Invalid or unsafe archive entry path"):
        big.pack_to_memory([("COM1", b"payload")])


def test_selective_unpack_with_glob_filter(standard_mod_directory: Path, tmp_path: Path):
    """Verify that unpack() with filter_pattern extracts and returns only matching entries."""
    archive_path = tmp_path / "selective.big"
    extract_dir = tmp_path / "selective_out"
    big.pack(standard_mod_directory, archive_path)

    entries = big.unpack(archive_path, extract_dir, filter_pattern="*.ini")

    assert len(entries) == 1
    assert entries[0].name == "data\\weapon.ini"
    assert (extract_dir / "data" / "weapon.ini").exists()
    assert not (extract_dir / "readme.txt").exists()
    assert not (extract_dir / "art" / "texture.dds").exists()


def test_diff_archives_and_error_handling(tmp_path: Path):
    """Verify diff() categorizes archive changes accurately and validates input paths."""
    base_path = tmp_path / "base.big"
    target_path = tmp_path / "target.big"

    base_path.write_bytes(big.pack_to_memory({
        "data/weapon.ini": b"Damage=50",
        "data/armor.ini": b"Armor=100",
        "readme.txt": b"v1.0",
    }))
    target_path.write_bytes(big.pack_to_memory({
        "data/weapon.ini": b"Damage=75",
        "data/armor.ini": b"Armor=100",
        "data/new_unit.ini": b"Cost=200",
    }))

    result = big.diff(base_path, target_path)
    assert result.has_differences
    assert "added=1" in repr(result)
    assert [e.name for e in result.added] == ["data\\new_unit.ini"]
    assert [e.name for e in result.removed] == ["readme.txt"]
    assert [e.name for e in result.modified] == ["data\\weapon.ini"]
    assert [e.name for e in result.unchanged] == ["data\\armor.ini"]

    # Compare open BigArchive instances directly
    with big.BigArchive(base_path) as b_arc, big.BigArchive(target_path) as t_arc:
        filtered_res = big.BigDiff.compare(b_arc, t_arc, filter_pattern="*armor.ini")
        assert not filtered_res.has_differences

    with pytest.raises(FileNotFoundError, match="Base archive not found"):
        big.diff(tmp_path / "missing_base.big", target_path)

    with pytest.raises(FileNotFoundError, match="Target archive not found"):
        big.diff(base_path, tmp_path / "missing_target.big")


def test_diff_amplification_limit(tmp_path: Path):
    """Verify diff and create_patch bounds check amplification ratios."""
    base_archive = tmp_path / "zipbomb_base.big"
    target_archive = tmp_path / "safe_target.big"

    target_archive.write_bytes(big.pack_to_memory({"readme.txt": b"Safe"}))

    file_count = 50
    entry_name = b"A.txt\x00"
    entry_record_size = 4 + 4 + len(entry_name)
    header_size = 16 + (file_count * entry_record_size)
    payload_size = 1024 * 1024
    total_size = header_size + payload_size

    with open(base_archive, "wb") as f:
        f.write(b"BIG4")
        f.write(struct.pack("<I", total_size))
        f.write(struct.pack(">I", file_count))
        f.write(struct.pack(">I", header_size))

        for _ in range(file_count):
            f.write(struct.pack(">I", header_size))
            f.write(struct.pack(">I", payload_size))
            f.write(entry_name)

        f.write(b"X" * payload_size)

    with pytest.raises(big.BigSecurityError, match="amplification"):
        big.diff(base_archive, target_archive)


def test_create_patch_and_create_patch_to_memory(tmp_path: Path):
    """Verify delta patch generation to disk and memory packs only added and modified files."""
    base_path = tmp_path / "base.big"
    target_path = tmp_path / "target.big"
    patch_path = tmp_path / "delta_patch.big"

    base_path.write_bytes(big.pack_to_memory({
        "data/weapon.ini": b"Damage=50",
        "data/armor.ini": b"Armor=100",
    }))
    target_path.write_bytes(big.pack_to_memory({
        "data/weapon.ini": b"Damage=75",
        "data/armor.ini": b"Armor=100",
        "data/new_unit.ini": b"Cost=200",
    }))

    patch_cb_names: list[str] = []
    big.create_patch(
        base_path,
        target_path,
        patch_path,
        progress_callback=lambda r: (patch_cb_names.append(r.entry_name), True)[1],
    )
    assert patch_path.is_file()
    assert patch_cb_names == ["data\\new_unit.ini", "data\\weapon.ini"]

    mem_cb_names: list[str] = []
    mem_patch = big.create_patch_to_memory(
        base_path,
        target_path,
        progress_callback=lambda r: (mem_cb_names.append(r.entry_name), None)[1],
    )
    assert patch_path.read_bytes() == mem_patch
    assert mem_cb_names == patch_cb_names

    # Cooperative cancellation in create_patch and create_patch_to_memory
    with pytest.raises(big.BigArchiveError, match="cancelled"):
        big.create_patch(base_path, target_path, tmp_path / "cancelled_patch.big", progress_callback=lambda _: False)

    with pytest.raises(big.BigArchiveError, match="cancelled"):
        big.create_patch_to_memory(base_path, target_path, progress_callback=lambda _: False)

    with big.BigArchive(patch_path) as patch_arc:
        names = [e.name for e in patch_arc.get_entries()]
        assert names == ["data\\new_unit.ini", "data\\weapon.ini"]
        assert patch_arc.read_entry("data/weapon.ini") == b"Damage=75"

    # Exercise BigArchive overloads and progress callbacks directly
    cb_mem: list[str] = []
    cb_disk: list[str] = []
    direct_patch_path = tmp_path / "direct_patch.big"
    with big.BigArchive(base_path) as b_arc, big.BigArchive(target_path) as t_arc:
        raw = big.BigDiff.create_patch_to_memory(
            b_arc, t_arc, progress_callback=lambda r: (cb_mem.append(r.entry_name), True)[1]
        )
        assert raw == mem_patch
        big.BigDiff.create_patch(
            b_arc, t_arc, direct_patch_path, progress_callback=lambda r: (cb_disk.append(r.entry_name), True)[1]
        )

    assert cb_mem == ["data\\new_unit.ini", "data\\weapon.ini"]
    assert cb_disk == cb_mem

    # Error handling for overwriting input archives, missing parent dir, and missing input archives
    with pytest.raises(ValueError, match="cannot overwrite an input archive"):
        big.create_patch(base_path, target_path, base_path)

    with pytest.raises(FileNotFoundError, match="does not exist"):
        big.create_patch(base_path, target_path, tmp_path / "missing_parent" / "patch.big")

    missing = tmp_path / "missing.big"
    with pytest.raises(FileNotFoundError, match="Base archive not found"):
        big.create_patch(missing, target_path, patch_path)

    with pytest.raises(FileNotFoundError, match="Target archive not found"):
        big.create_patch(base_path, missing, patch_path)

    with pytest.raises(FileNotFoundError, match="Base archive not found"):
        big.create_patch_to_memory(missing, target_path)

    with pytest.raises(FileNotFoundError, match="Target archive not found"):
        big.create_patch_to_memory(base_path, missing)


def test_load_overlay_from_directory_and_archive_sequence(tmp_path: Path):
    """Verify SAGE load-order emulation across directories and explicit archive sequences."""
    arc1 = tmp_path / "01_ini.big"
    arc2 = tmp_path / "02_patch.big"

    arc1.write_bytes(big.pack_to_memory({
        "data/weapon.ini": b"Damage=50",
        "readme.txt": b"v1.0",
    }))
    arc2.write_bytes(big.pack_to_memory({
        "data/weapon.ini": b"Damage=99",
        "art/icon.dds": b"DDS_PAYLOAD",
    }))

    # 1. Load from directory (alphabetical order: 01_ini.big -> 02_patch.big)
    overlay_dir = big.load_overlay(tmp_path)
    assert len(overlay_dir.mounted_archives) == 2

    resolved = overlay_dir.resolve("data/weapon.ini")
    assert resolved.name == "data\\weapon.ini"
    assert resolved.size == 9
    assert resolved.offset > 0
    assert resolved.entry.name == "data\\weapon.ini"
    assert resolved.source_archive == arc2
    assert resolved.override_count == 1
    assert "overrides=1" in repr(resolved)
    assert overlay_dir.read_entry("data/weapon.ini") == b"Damage=99"

# 2. Load from explicit sequence in reverse order (02_patch.big -> 01_ini.big)
    with big.load_overlay([arc2, arc1]) as overlay_seq:
        assert overlay_seq.read_entry("data/weapon.ini") == b"Damage=50"
        assert overlay_seq.resolve("data/weapon.ini").source_archive == arc1

        # Verify value semantics and case-insensitive ordering on overlay
        entries = overlay_seq.get_entries()
        assert entries[0].name == "art\\icon.dds"
        assert entries[1].name == "data\\weapon.ini"

        entries_set = set(entries)
        assert len(entries_set) == 3
        assert entries[0] == entries[0]

    assert overlay_seq.closed

    # 3. Error handling
    with pytest.raises(NotADirectoryError, match="does not exist"):
        big.load_overlay(tmp_path / "missing_dir")

    with pytest.raises(FileNotFoundError, match="Archive not found"):
        big.load_overlay([arc1, tmp_path / "missing_arc.big"])
