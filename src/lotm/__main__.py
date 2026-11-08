"""
@file src/lotm/__main__.py
@brief Root module execution entry point for python -m lotm

Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
Part of the Lord of the Mods (lotm) project.
SPDX-License-Identifier: GPL-3.0-or-later
"""

from lotm.cli import cli_entry

if __name__ == "__main__":  # pragma: no cover
    cli_entry()
