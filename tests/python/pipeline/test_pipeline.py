"""
@file tests/python/pipeline/test_pipeline.py
@brief Integration and unit tests for the modular lotm.pipeline archive-to-AST bridge.

Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
Part of the Lord of the Mods (lotm) project.
SPDX-License-Identifier: GPL-3.0-or-later
"""

from __future__ import annotations

from collections.abc import Buffer
import os
from pathlib import Path
import pytest

import lotm
import lotm.big as big
import lotm.ini as ini
import lotm.pipeline as pipeline


def _build_sample_archive(path: Path) -> Path:
    """Create a sample BIG4 archive containing .ini, .inc, .str, and binary .dds entries."""
    payloads = {
        "data/ini/weapon.ini": (
            b"Weapon   GondorSword // header\n"
            b"    Damage=50 // slash\n"
            b"END\n"
        ),
        "data/ini/includes/armor.inc": (
            b"ArmorSet\n"
            b"    Conditions = NONE\n"
            b"    Armor = DEFAULT 25%\n"
            b"End\n"
        ),
        "lang/lotr.str": (
            b'OBJECT:GondorSword // hdr\n'
            b'    "Gondor Sword"\n'
            b"end\n"
        ),
        "art/textures/sword.dds": b"DDS_RAW_BINARY_PAYLOAD",
    }
    path.write_bytes(big.pack_to_memory(payloads))
    return path


def test_pipeline_public_exports() -> None:
    """Verify top-level lotm.pipeline import and __all__ symbol exports."""
    assert hasattr(lotm, "pipeline")
    assert "pipeline" in lotm.__all__

    expected = {
        "ArchiveEditor",
        "ArchiveHandle",
        "ArchiveInput",
        "EntryStage",
        "FormatConfigStage",
        "IniAstStage",
        "StrAstStage",
        "TransformResult",
        "transform_archive",
    }
    assert set(pipeline.__all__) == expected
    for name in expected:
        assert hasattr(pipeline, name), f"Missing pipeline export: {name}"


def test_entry_stages_matching_and_application() -> None:
    """Verify IniAstStage, StrAstStage, FormatConfigStage, and custom EntryStage protocol compliance."""
    def bump_damage(doc: ini.ConstructFile) -> None:
        wpn = doc.find_block("Weapon", "GondorSword")
        assert wpn is not None
        wpn.set_value("Damage", "99")

    ini_stage = pipeline.IniAstStage(
        mutator=bump_damage,
        format_options=ini.FormatOptions(normalize_end_tokens=True),
    )
    assert isinstance(ini_stage, pipeline.EntryStage)
    assert ini_stage.matches("DATA\\INI\\WEAPON.INI")
    assert ini_stage.matches("data/ini/macros.inc")
    assert not ini_stage.matches("lang/lotr.str")

    out_ini = ini_stage.apply("data/ini/weapon.ini", b"Weapon GondorSword\n    Damage = 50\nEND\n", strict=True)
    assert b"Damage = 99" in out_ini
    assert out_ini.endswith(b"End\n\n")

    def update_str_entry(doc: ini.StrDocument) -> None:
        first = doc[0]
        assert isinstance(first, ini.StrEntry)
        first[0] = ini.StatementNode('"Forged Gondor Sword"')

    str_stage = pipeline.StrAstStage(
        mutator=update_str_entry,
        format_options=ini.FormatOptions(normalize_end_tokens=True),
    )
    assert isinstance(str_stage, pipeline.EntryStage)
    assert str_stage.matches("LANG\\LOTR.STR")
    assert not str_stage.matches("data/ini/weapon.ini")

    out_str = str_stage.apply("lang/lotr.str", b'OBJECT:GondorSword\n    "Old"\nend\n', strict=True)
    assert b'"Forged Gondor Sword"' in out_str
    assert out_str.endswith(b"End\n\n")

    fmt_stage = pipeline.FormatConfigStage(
        options=ini.FormatOptions(
            normalize_end_tokens=True,
            normalize_header_spacing=True,
            normalize_statement_equals=True,
            normalize_comments=True,
        )
    )
    assert isinstance(fmt_stage, pipeline.EntryStage)
    assert fmt_stage.matches("weapon.ini")
    assert fmt_stage.matches("macros.inc")
    assert fmt_stage.matches("lotr.str")
    assert not fmt_stage.matches("hero.dds")

    formatted_ini = fmt_stage.apply("weapon.ini", b"Weapon   Sword // hdr\n  Damage=10 // cmt\nEND\n", strict=True)
    assert b"Weapon Sword ; hdr\n" in formatted_ini
    assert b"    Damage = 10 ; cmt\n" in formatted_ini
    assert formatted_ini.endswith(b"End\n\n")

    formatted_str = fmt_stage.apply("lotr.str", b'OBJECT:Sword // hdr\n  "Sword"\nend\n', strict=True)
    assert b"OBJECT:Sword ; hdr\n" in formatted_str
    assert formatted_str.endswith(b"End\n\n")


def test_archive_editor_ast_caching_deduplication_and_full_repack(tmp_path: Path) -> None:
    """Verify ArchiveEditor caches ASTs case-insensitively and repacks full archives cleanly."""
    src_big = _build_sample_archive(tmp_path / "base.big")
    out_big = tmp_path / "repacked.big"

    with pipeline.ArchiveEditor(src_big) as editor:
        assert not editor.closed

        # Opening the same entry with different casing/slashes returns the same cached AST instance
        doc1 = editor.open_ini("data/ini/weapon.ini", strict=True)
        doc2 = editor.open_ini("DATA\\INI\\WEAPON.INI", strict=True)
        assert doc1 is doc2

        # Two sequential edits compose on the same cached AST
        editor.edit_ini(
            "data/ini/weapon.ini",
            lambda d: d.find_block("Weapon", "GondorSword").set_value("Damage", "120"),  # type: ignore[union-attr]
        )
        editor.edit_ini(
            "DATA\\INI\\WEAPON.INI",
            lambda d: d.find_block("Weapon", "GondorSword").set_value("AttackRange", "25"),  # type: ignore[union-attr]
            format_options=ini.FormatOptions(normalize_end_tokens=True),
        )

        # Edit .str localization AST
        str_doc1 = editor.open_str("lang/lotr.str", strict=True)
        str_doc2 = editor.open_str("LANG\\LOTR.STR", strict=True)
        assert str_doc1 is str_doc2
        editor.edit_str(
            "lang/lotr.str",
            lambda d: d.append(ini.StrEntry("GUI", "NewButton", items=[ini.StatementNode('"Click"')])),
            format_options=ini.FormatOptions(normalize_end_tokens=True),
        )

        # Add new raw file and delete existing .inc file
        editor.put_bytes("data/ini/new_spell.ini", b"SpecialPower SpellTest\nEnd\n")
        assert editor.remove("data/ini/includes/armor.inc") is True
        assert editor.remove("data/ini/includes/armor.inc") is False
        assert editor.remove("nonexistent/file.ini") is False

        result = editor.save(out_big)
        assert result.output_path == out_big
        assert result.output_bytes is None
        assert result.modified_entries == ["data\\ini\\weapon.ini", "lang\\lotr.str"]
        assert result.added_entries == ["data\\ini\\new_spell.ini"]
        assert result.removed_entries == ["data\\ini\\includes\\armor.inc"]

    assert editor.closed

    with big.BigArchive(out_big) as repacked:
        names = [e.name for e in repacked.get_entries()]
        assert "art\\textures\\sword.dds" in names
        assert "data\\ini\\weapon.ini" in names
        assert "data\\ini\\new_spell.ini" in names
        assert "lang\\lotr.str" in names
        assert "data\\ini\\includes\\armor.inc" not in names

        weapon_text = repacked.read_entry("data/ini/weapon.ini").decode("utf-8")
        assert "Damage=120" in weapon_text
        assert "AttackRange = 25" in weapon_text
        assert weapon_text.endswith("End\n\n")

        str_text = repacked.read_entry("lang/lotr.str").decode("utf-8")
        assert "GUI:NewButton" in str_text


def test_archive_editor_delta_patch_and_raw_override_precedence(tmp_path: Path) -> None:
    """Verify save_patch / to_patch_memory emit only modified/added entries and handle put_bytes -> open_ini."""
    src_big = _build_sample_archive(tmp_path / "base.big")
    patch_big = tmp_path / "delta_patch.big"

    with big.BigArchive(src_big) as open_arc:
        with pipeline.ArchiveEditor(open_arc) as editor:
            # Stage raw bytes first, then parse via open_ini to verify staged raw override pickup
            editor.put_bytes("data/ini/staged_unit.ini", b"Object StagedHero\n    Side = Men\nEnd\n")
            staged_doc = editor.open_ini("data/ini/staged_unit.ini", strict=True)
            hero = staged_doc.find_block("Object", "StagedHero")
            assert hero is not None
            hero.set_value("Side", "Dunedain")

            # Also stage raw override for .str and open_str
            editor.put_bytes("lang/extra.str", b'OBJECT:Extra\n    "Extra"\nEnd\n')
            extra_str = editor.open_str("lang/extra.str", strict=True)
            assert len(extra_str.entries) == 1

            # Modify one existing file and replace an existing binary file with raw bytes
            editor.edit_ini(
                "data/ini/weapon.ini",
                lambda d: d.find_block("Weapon", "GondorSword").set_value("Damage", "85"),  # type: ignore[union-attr]
            )
            editor.put_bytes("art/textures/sword.dds", b"UPDATED_DDS_BYTES")

            patch_res = editor.save_patch(patch_big)
            assert patch_res.modified_entries == ["art\\textures\\sword.dds", "data\\ini\\weapon.ini"]
            assert patch_res.added_entries == ["data\\ini\\staged_unit.ini", "lang\\extra.str"]

        # Borrowed BigArchive must remain open after ArchiveEditor exits
        assert not open_arc.closed

    with big.BigArchive(patch_big) as patch_arc:
        patch_names = [e.name for e in patch_arc.get_entries()]
        # Unmodified armor.inc and lotr.str must NOT be in the delta patch
        assert patch_names == [
            "art\\textures\\sword.dds",
            "data\\ini\\staged_unit.ini",
            "data\\ini\\weapon.ini",
            "lang\\extra.str",
        ]
        assert patch_arc.read_entry("art/textures/sword.dds") == b"UPDATED_DDS_BYTES"
        assert b"Side = Dunedain" in patch_arc.read_entry("data/ini/staged_unit.ini")
        assert b"Damage=85" in patch_arc.read_entry("data/ini/weapon.ini")


def test_archive_editor_format_entries_and_overlay_source(tmp_path: Path) -> None:
    """Verify ArchiveEditor with BigOverlay source, glob filtering, removed skips, and batch format_entries()."""
    arc1 = tmp_path / "01_base.big"
    arc2 = tmp_path / "02_mod.big"

    arc1.write_bytes(big.pack_to_memory({
        "data/ini/weapon.ini": b"Weapon Sword\n    Damage=10\nEND\n",
        "data/ini/armor.ini": b"Armor Plate\n    Armor = DEFAULT 20%\nEND\n",
    }))
    arc2.write_bytes(big.pack_to_memory({
        "data/ini/weapon.ini": b"Weapon Sword\n    Damage=50\nEND\n",
        "lang/mod.str": b'OBJECT:Sword\n    "Mod Sword"\nend\n',
    }))

    fmt_opts = ini.FormatOptions(
        normalize_end_tokens=True,
        normalize_statement_equals=True,
    )

    with big.load_overlay([arc1, arc2]) as overlay:
        with pipeline.ArchiveEditor(overlay) as editor:
            # Remove one entry and filter to *.ini so non-matching and removed entries are skipped
            assert editor.remove("data/ini/armor.ini") is True
            formatted = editor.format_entries("*.ini", options=fmt_opts)
            assert formatted == ["data\\ini\\weapon.ini"]

            # Applying a stage also skips removed entries
            applied = editor.apply_stage(
                pipeline.FormatConfigStage(options=fmt_opts),
                filter_pattern="*",
            )
            assert "data\\ini\\armor.ini" not in applied
            assert "data\\ini\\weapon.ini" in applied
            merged_bytes = editor.to_memory()

        assert not overlay.closed

    with tempfile_archive(tmp_path / "overlay_out.big", merged_bytes) as out_arc:
        weapon_txt = out_arc.read_entry("data/ini/weapon.ini").decode("utf-8")
        assert "Damage = 50" in weapon_txt
        assert weapon_txt.endswith("End\n\n")
        assert not any(e.name.endswith("armor.ini") for e in out_arc.get_entries())


def tempfile_archive(path: Path, data: bytes) -> big.BigArchive:
    """Write `data` to `path` and return an open BigArchive context manager."""
    path.write_bytes(data)
    return big.BigArchive(path)


def test_transform_archive_one_shot_and_custom_stage(tmp_path: Path) -> None:
    """Verify transform_archive() with transforms, custom EntryStage, filter/format options, and save()."""
    src_big = _build_sample_archive(tmp_path / "base.big")
    out_patch = tmp_path / "one_shot_patch.big"
    out_full = tmp_path / "full_transformed.big"
    out_filtered = tmp_path / "filtered_formatted.big"

    class BinaryMarkerStage:
        """Custom EntryStage appending a version marker to .dds payloads."""

        def matches(self, entry_name: str) -> bool:
            return entry_name.lower().endswith(".dds")

        def apply(self, entry_name: str, payload: Buffer, *, strict: bool = False) -> bytes:
            return bytes(payload) + b"_V2"

    # In-memory transform with INI mutator + FormatOptions
    mem_res = pipeline.transform_archive(
        src_big,
        transforms={
            "data/ini/weapon.ini": lambda doc: doc.find_block("Weapon", "GondorSword").set_value("Damage", "200"),  # type: ignore[union-attr]
        },
        format_options=ini.FormatOptions(normalize_end_tokens=True, normalize_statement_equals=True),
        strict=True,
        patch_only=True,
    )
    assert mem_res.output_bytes is not None
    assert mem_res.output_path is None
    assert mem_res.modified_entries == ["data\\ini\\weapon.ini"]

    # Disk patch with pluggable custom EntryStage + FormatConfigStage
    disk_res = pipeline.transform_archive(
        src_big,
        output_file=out_patch,
        stages=[
            BinaryMarkerStage(),
            pipeline.FormatConfigStage(options=ini.FormatOptions(normalize_end_tokens=True)),
        ],
        filter_pattern="*",
        patch_only=True,
    )
    assert disk_res.output_path == out_patch
    assert disk_res.output_bytes is None
    assert "art\\textures\\sword.dds" in disk_res.modified_entries

    with big.BigArchive(out_patch) as patch_arc:
        assert patch_arc.read_entry("art/textures/sword.dds") == b"DDS_RAW_BINARY_PAYLOAD_V2"
        assert patch_arc.read_entry("lang/lotr.str").decode("utf-8").endswith("End\n\n")

    # Full archive save (patch_only=False) with format_options across all config entries
    full_res = pipeline.transform_archive(
        src_big,
        output_file=out_full,
        format_options=ini.FormatOptions(normalize_end_tokens=True),
    )
    assert full_res.output_path == out_full
    assert full_res.output_bytes is None
    assert full_res.modified_entries == [
        "data\\ini\\includes\\armor.inc",
        "data\\ini\\weapon.ini",
        "lang\\lotr.str",
    ]
    with big.BigArchive(out_full) as full_arc:
        assert len(full_arc.get_entries()) == 4
        assert full_arc.read_entry("data/ini/weapon.ini").decode("utf-8").endswith("End\n\n")

    # filter_pattern alone formats matching entries
    filtered_res = pipeline.transform_archive(
        src_big,
        output_file=out_filtered,
        filter_pattern="*.ini",
        format_options=ini.FormatOptions(normalize_end_tokens=True),
        patch_only=True,
    )
    assert filtered_res.modified_entries == ["data\\ini\\weapon.ini"]


def test_pipeline_error_handling_and_atomic_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify error handling for missing/closed archives, invalid paths, cancellation, and failed os.replace."""
    with pytest.raises(FileNotFoundError, match="Archive not found"):
        pipeline.ArchiveEditor(tmp_path / "does_not_exist.big")

    src_big = _build_sample_archive(tmp_path / "base.big")

    closed_arc = big.BigArchive(src_big)
    closed_arc.close()
    with pytest.raises(big.BigArchiveError, match="closed archive"):
        pipeline.ArchiveEditor(closed_arc)

    editor = pipeline.ArchiveEditor(src_big)
    with pytest.raises(ValueError, match="Entry path cannot be empty"):
        editor.put_bytes("", b"data")

    # Cooperative cancellation during packing
    editor.put_bytes("added.txt", b"hello")
    with pytest.raises(big.BigArchiveError, match="cancelled"):
        editor.to_patch_memory(progress_callback=lambda _: False)

    # Invalid save destinations (existing directory, missing parent dir)
    existing_dir = tmp_path / "dir_target"
    existing_dir.mkdir()
    with pytest.raises(ValueError, match="cannot be a directory"):
        editor.save_patch(existing_dir)

    with pytest.raises(FileNotFoundError, match="does not exist"):
        editor.save(tmp_path / "missing_parent" / "out.big")

    # Atomic replace failure cleans up .lotm_tmp sibling file
    atomic_target = tmp_path / "atomic_target.big"

    def _fail_replace(src: os.PathLike[str], dst: os.PathLike[str]) -> None:
        raise OSError("Simulated atomic rename error")

    with monkeypatch.context() as m:
        m.setattr(os, "replace", _fail_replace)
        with pytest.raises(OSError, match="Simulated atomic rename error"):
            editor.save_patch(atomic_target)

    assert not atomic_target.exists()
    assert list(tmp_path.glob("*.lotm_tmp")) == []

    # Closed editor rejects context re-entry and operations
    editor.close()
    assert editor.closed
    with pytest.raises(big.BigArchiveError, match="closed ArchiveEditor"):
        with editor:
            pass
    with pytest.raises(big.BigArchiveError, match="closed ArchiveEditor"):
        editor.open_ini("data/ini/weapon.ini")

    # Underlying archive closed mid-session raises BigArchiveError
    live_arc = big.BigArchive(src_big)
    with pipeline.ArchiveEditor(live_arc) as borrowed_editor:
        live_arc.close()
        with pytest.raises(big.BigArchiveError, match="Underlying archive or overlay has been closed"):
            borrowed_editor.open_ini("data/ini/weapon.ini")
