"""
@file src/lotm/__init__.py
@brief High-performance SAGE engine archive and configuration manipulation library.

Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
Part of the Lord of the Mods (lotm) project.
SPDX-License-Identifier: GPL-3.0-or-later
"""

import logging
from importlib.metadata import version

# Prevent "No handler found" warnings for users who don't configure logging
logging.getLogger("lotm").addHandler(logging.NullHandler())

__version__ = version("lord-of-the-mods")

from . import big, ini, pipeline

__all__ = ["__version__", "big", "ini", "pipeline"]
