"""
@file src/lotm/big/packer.py
@brief Pack files into .BIG archives (Library API)

Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
Part of the Lord of the Mods (lotm) project.
SPDX-License-Identifier: GPL-3.0-or-later
"""

from collections.abc import Iterable, Mapping
import logging
import os
from pathlib import Path
from lotm._core import big

logger = logging.getLogger("lotm.big.packer")


def pack(source_dir: str | os.PathLike[str], output_file: str | os.PathLike[str]) -> None:
    """
    Packs a directory into an EA BIG4 archive.

    Args:
        source_dir: Path to the directory containing files to pack.
        output_file: Destination .big file path.

    Raises:
        NotADirectoryError: If the source directory is missing or invalid.
        RuntimeError/ValueError: Native C++ exceptions if packing fails.
    """
    source_path = Path(source_dir)
    output_path = Path(output_file)

    if not source_path.is_dir():
        raise NotADirectoryError(f"Source directory '{source_path}' does not exist or is not a directory.")

    def on_progress(name: str) -> None:
        logger.debug("Packed: %s", name)

    big.BigPacker.pack_from_directory(source_path, output_path, progress_callback=on_progress)
    logger.info("Finished packing into: %s", output_path.resolve())


def pack_to_memory(
    source: str | os.PathLike[str] | Mapping[str, bytes] | Iterable[tuple[str, bytes]]
) -> bytes:
    """
    Packs a directory or an in-memory collection of (path, bytes) records into an EA BIG4 archive buffer.

    Args:
        source: Directory path, mapping of {archive_path: payload_bytes}, or iterable of (archive_path, payload_bytes).

    Returns:
        A bytes object containing the serialized BIG4 archive.

    Raises:
        NotADirectoryError: If a path is provided and the source directory is missing or invalid.
        RuntimeError/ValueError: Native C++ exceptions if validation or packing fails.
    """
    def on_progress(name: str) -> None:
        logger.debug("Packed to memory: %s", name)

    if isinstance(source, (str, os.PathLike)):
        source_path = Path(source)
        if not source_path.is_dir():
            raise NotADirectoryError(f"Source directory '{source_path}' does not exist or is not a directory.")

        data = big.BigPacker.pack_to_memory(source_path, progress_callback=on_progress)
        logger.info("Finished packing directory into memory (%d bytes)", len(data))
        return data

    records = list(source.items()) if isinstance(source, Mapping) else list(source)
    data = big.BigPacker.pack_to_memory(records, progress_callback=on_progress)
    logger.info("Finished packing %d records into memory (%d bytes)", len(records), len(data))
    return data
