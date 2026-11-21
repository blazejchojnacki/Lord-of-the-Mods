"""
@file src/lotm/big/overlay.py
@brief Emulate SAGE engine .BIG load order and virtual file overlay (Library API)

Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
Part of the Lord of the Mods (lotm) project.
SPDX-License-Identifier: GPL-3.0-or-later
"""

import logging
import os
from collections.abc import Iterable
from pathlib import Path

from lotm._core import big

logger = logging.getLogger("lotm.big.overlay")


def load_overlay(
    source: str | os.PathLike[str] | Iterable[str | os.PathLike[str]],
) -> big.BigOverlay:
    """
    Construct a SAGE load-order overlay from a directory or an explicit sequence of `.big` archives.

    Parameters
    ----------
    source : str | os.PathLike[str] | Iterable[str | os.PathLike[str]]
        Path to a directory containing `.big` files (mounted in alphabetical order),
        or an iterable of `.big` archive file paths mounted in the given sequence.

    Returns
    -------
    big.BigOverlay
        Populated overlay instance representing the effective virtual file tree.

    Raises
    ------
    NotADirectoryError
        If a single path is provided and it is not an existing directory.
    FileNotFoundError
        If an archive path in `source` does not exist.
    lotm.big.BigFormatError
        If any mounted archive header or index table is corrupted.
    lotm.big.BigArchiveError
        If any archive cannot be opened or read from disk.

    Examples
    --------
    >>> overlay = load_overlay(["01_base.big", "02_patch.big"])  # doctest: +SKIP
    """
    if isinstance(source, (str, os.PathLike)):
        dir_path = Path(source)
        if not dir_path.is_dir():
            raise NotADirectoryError(
                f"Overlay directory '{dir_path}' does not exist or is not a directory."
            )

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
    logger.info(
        "Mounted %d archives in explicit load order", len(overlay.mounted_archives)
    )
    return overlay
