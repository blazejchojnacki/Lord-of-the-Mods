"""
@file src/lotm/big/unpacker.py
@brief Unpack files from .BIG archives (Library API)

Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
Part of the Lord of the Mods (lotm) project.
SPDX-License-Identifier: GPL-3.0-or-later
"""

import logging
from pathlib import Path
from lotm._core import big

logger = logging.getLogger("lotm.big.unpacker")


def unpack(big_path: Path, output_dir: Path) -> list[big.BigEntry]:
    """
    Unpacks an EA BIG4 archive into a target directory.

    Args:
        big_path: Path to the .big archive file.
        output_dir: Destination directory where files will be extracted.

    Returns:
        List of BigEntry objects describing the extracted files.

    Raises:
        FileNotFoundError: If the archive file does not exist.
        ValueError: If the file header does not match the BIG4 specification.
        RuntimeError: If archive bounds checking or stream reads fail.
    """
    if not big_path.is_file():
        raise FileNotFoundError(f"Archive not found: {big_path}")

    archive = big.BigArchive(big_path)

    # Inspect parsed entries via bindings
    entries = archive.get_entries()
    logger.info("Loaded %d entries from %s", len(entries), big_path.name)

    def on_progress(name: str) -> None:
        logger.debug("Extracted: %s", name)

    # Extract all indexed files to the destination folder
    archive.extract_all(output_dir, progress_callback=on_progress)
    logger.info("Finished extracting into: %s", output_dir.resolve())

    return entries


# Backward-compatible alias
extract = unpack
