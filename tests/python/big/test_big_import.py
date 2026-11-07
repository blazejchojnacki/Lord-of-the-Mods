"""
@file tests/python/big/test_big_import.py
@brief Sanity checks for package imports and public symbol exports.

Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
Part of the Lord of the Mods (lotm) project.
SPDX-License-Identifier: GPL-3.0-or-later
"""

import importlib


def test_native_core_import():
    """Verify that the private native C++ extension core loads cleanly."""
    core = importlib.import_module("lotm._core")
    assert hasattr(core, "big"), "Native extension missing 'big' submodule"


def test_big_subpackage_exports():
    """Verify that lotm.big exposes the unified C++ and Python public interface."""
    import lotm.big as big

    # Native classes
    assert hasattr(big, "BigArchive")
    assert hasattr(big, "BigPacker")
    assert hasattr(big, "BigEntry")
    assert hasattr(big, "BigDiff")
    assert hasattr(big, "BigDiffResult")
    assert hasattr(big, "BigOverlay")
    assert hasattr(big, "BigOverlayEntry")

    # Native exception hierarchy
    assert hasattr(big, "BigArchiveError")
    assert hasattr(big, "BigFormatError")
    assert hasattr(big, "BigSecurityError")
    assert issubclass(big.BigFormatError, big.BigArchiveError)
    assert issubclass(big.BigSecurityError, big.BigArchiveError)

    # Pure Python API helpers
    assert hasattr(big, "create_patch")
    assert hasattr(big, "create_patch_to_memory")
    assert hasattr(big, "diff")
    assert hasattr(big, "load_overlay")
    assert hasattr(big, "pack")
    assert hasattr(big, "pack_to_memory")
    assert hasattr(big, "unpack")
    assert callable(big.create_patch)
    assert callable(big.create_patch_to_memory)
    assert callable(big.diff)
    assert callable(big.load_overlay)
    assert callable(big.pack)
    assert callable(big.pack_to_memory)
    assert callable(big.unpack)


def test_cli_modules_import():
    """Verify that CLI entry point handlers are discoverable."""
    import lotm.big.cli as cli

    assert hasattr(cli, "build_parser")
    assert hasattr(cli, "main")
    assert hasattr(cli, "cli_entry")
    assert callable(cli.build_parser)
    assert callable(cli.main)
    assert callable(cli.cli_entry)
