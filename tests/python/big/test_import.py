"""
@file tests/python/big/test_import.py
@brief Integration tests validating C++ module resolution and bound API surface.

Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
Part of the Lord of the Mods (lotm) project.
SPDX-License-Identifier: GPL-3.0-or-later
"""

import pytest
import sys


def test_module_resolution_and_metadata():
    """Verify that the compiled C++ extension loads without dynamic linker errors."""
    import lotm
    import lotm.big

    # assert lotm.__doc__ is not None
    assert lotm.big.__doc__ is not None


def test_big_submodule_api_surface():
    """Verify that the Big archive registry correctly binds all required classes."""
    import lotm.big as big

    assert hasattr(big, "BigArchive")
    assert hasattr(big, "BigPacker")
    assert hasattr(big, "BigEntry")


def test_unsupported_attribute_access_handling():
    """Verify that accessing unregistered bindings raises standard AttributeErrors."""
    import lotm.big as big

    with pytest.raises(AttributeError):
        _ = big.NonExistentArchiveType
