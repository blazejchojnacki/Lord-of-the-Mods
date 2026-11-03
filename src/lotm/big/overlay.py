"""
@file src/lotm/big/overlay.py
@brief Emulate SAGE engine .BIG load order and virtual file overlay (Library API)

Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
Part of the Lord of the Mods (lotm) project.
SPDX-License-Identifier: GPL-3.0-or-later
"""

from collections.abc import Iterable
import logging
import os
from pathlib import Path
from lotm._core import big

logger = logging.getLogger("lotm.big.overlay")


def load_overlay(
    source: str | os.PathLike[str] | Iterable[str | os.PathLike[str]],
) -> big.BigOverlay:
    """
    Constructs a SAGE load-order overlay from a directory or an explicit sequence of .big archives.

    Args:
        source: Path to a directory containing .big files (mounted in alphabetical order),
                or an iterable of .big archive file paths mounted in the given sequence.

    Returns:
        A populated BigOverlay instance representing the effective virtual file tree.

    Raises:
        NotADirectoryError: If a single path is provided and it is not an existing directory.
        FileNotFoundError: If an archive path in an iterable does not exist.
        RuntimeError: If any mounted archive is corrupted or unreadable.
    """
    if isinstance(source, (str, os.PathLike)):
        dir_path = Path(source)
        if not dir_path.is_dir():
            raise NotADirectoryError(f"Overlay directory '{dir_path}' does not exist or is not a directory.")

        overlay = big.BigOverlay.from_directory(dir_path)
        logger.info(
            "Mounted %d archives from directory: %s",
            len(overlay.mounted_archives),
            dir_path.resolve(),
        )
        return overlay

    archive_paths: list[str | os.PathLike[str]] = []
    for item in source:
        p = Path(item)
        if not p.is_file():
            raise FileNotFoundError(f"Archive not found: {p}")
        archive_paths.append(p)

    overlay = big.BigOverlay.from_archives(archive_paths)
    logger.info("Mounted %d archives in explicit load order", len(overlay.mounted_archives))
    return overlay
