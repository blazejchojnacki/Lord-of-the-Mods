"""
@file src/lotm/big/unpacker.py
@brief Unpack files from .BIG archives (Library API)

Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
Part of the Lord of the Mods (lotm) project.
SPDX-License-Identifier: GPL-3.0-or-later
"""

import logging
import os
from pathlib import Path
from lotm._core import big

logger = logging.getLogger("lotm.big.unpacker")


def unpack(
    big_path: str | os.PathLike[str],
    output_dir: str | os.PathLike[str],
    filter_pattern: str | None = None,
) -> list[big.BigEntry]:
    """
    Unpacks an EA BIG4 archive into a target directory.

    Args:
        big_path: Path to the .big archive file.
        output_dir: Destination directory where files will be extracted.
        filter_pattern: Optional glob pattern (e.g., 'data/ini/*.ini') to selectively extract entries.

    Returns:
        List of BigEntry objects describing the extracted files.

    Raises:
        FileNotFoundError: If the archive file does not exist.
        ValueError: If the file header does not match the BIG4 specification.
        RuntimeError: If archive bounds checking or stream reads fail.
    """
    archive_path = Path(big_path)
    dest_path = Path(output_dir)
    pattern = filter_pattern or ""

    if not archive_path.is_file():
        raise FileNotFoundError(f"Archive not found: {archive_path}")

    archive = big.BigArchive(archive_path)

    # Inspect parsed entries via bindings
    entries = archive.get_entries(pattern)
    logger.info("Loaded %d entries from %s", len(entries), archive_path.name)

    def on_progress(name: str) -> None:
        logger.debug("Extracted: %s", name)

    # Extract all indexed files to the destination folder
    archive.extract_all(dest_path, progress_callback=on_progress, filter_pattern=pattern)
    logger.info("Finished extracting into: %s", dest_path.resolve())

    return entries
