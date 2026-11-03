"""
Lord of the Mods (lotm)
High-performance SAGE engine archive manipulation library.

Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
Part of the Lord of the Mods (lotm) project.
SPDX-License-Identifier: GPL-3.0-or-later
"""

import logging

# Prevent "No handler found" warnings for users who don't configure logging
logging.getLogger("lotm").addHandler(logging.NullHandler())

__version__ = "0.3.0"

__all__ = ["__version__"]
