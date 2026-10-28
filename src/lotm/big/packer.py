"""
@file src/lotm/big/packer.py
@brief Pack files into .BIG archives (Library API)

Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
Part of the Lord of the Mods (lotm) project.
SPDX-License-Identifier: GPL-3.0-or-later
"""

import logging
from pathlib import Path
from lotm._core import big

logger = logging.getLogger("lotm.big.packer")


def pack(source_dir: Path, output_file: Path) -> None:
    """
    Packs a directory into an EA BIG4 archive.

    Args:
        source_dir: Path to the directory containing files to pack.
        output_file: Destination .big file path.

    Raises:
        NotADirectoryError: If the source directory is missing or invalid.
        RuntimeError/ValueError: Native C++ exceptions if packing fails.
    """
    if not source_dir.is_dir():
        raise NotADirectoryError(f"Source directory '{source_dir}' does not exist or is not a directory.")

    def on_progress(name: str) -> None:
        logger.debug("Packed: %s", name)

    big.BigPacker.pack_from_directory(source_dir, output_file, progress_callback=on_progress)
    logger.info("Finished packing into: %s", output_file.resolve())
