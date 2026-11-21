"""
@file src/lotm/big/unpacker.py
@brief Unpack files from .BIG archives (Library API)

Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
Part of the Lord of the Mods (lotm) project.
SPDX-License-Identifier: GPL-3.0-or-later
"""

from collections.abc import Callable
import logging
import os
from pathlib import Path
from lotm._core import big
from .packer import _make_progress_callback

logger = logging.getLogger("lotm.big.unpacker")


def unpack(
    big_path: str | os.PathLike[str],
    output_dir: str | os.PathLike[str],
    filter_pattern: str | None = None,
    progress_callback: Callable[[big.ProgressReport], bool | None] | None = None,
    create_directories: bool = True,
) -> list[big.BigEntry]:
    """
    Unpack an EA BIG4 archive into a target directory.

    Parameters
    ----------
    big_path : str | os.PathLike[str]
        Path to the source `.big` archive file.
    output_dir : str | os.PathLike[str]
        Destination directory where files will be extracted.
    filter_pattern : str | None, default=None
        Optional glob pattern (e.g., `'data/ini/*.ini'`) to selectively extract matching entries.
    progress_callback : Callable[[big.ProgressReport], bool | None] | None, default=None
        Optional callback invoked with `ProgressReport`; returning `False` cancels extraction.
    create_directories : bool, default=True
        If `True`, automatically creates `output_dir` if it does not exist. If `False`,
        raises `FileNotFoundError` when `output_dir` is missing.

    Returns
    -------
    list[big.BigEntry]
        Metadata records describing the extracted files.

    Raises
    ------
    FileNotFoundError
        If the archive file does not exist, or if `create_directories` is `False` and
        `output_dir` does not exist.
    lotm.big.BigFormatError
        If the archive header is malformed or entry offsets exceed physical file bounds.
    lotm.big.BigSecurityError
        If Zip-Slip path traversal, reserved Windows device names, Alternate Data Streams,
        symlinks, or Zip-Bomb amplification limits are triggered.
    lotm.big.BigArchiveError
        If stream I/O fails or extraction is cancelled by `progress_callback`.

    Examples
    --------
    >>> entries = unpack("my_mod.big", "extracted_files", filter_pattern="*.ini")  # doctest: +SKIP
    """
    archive_path = Path(big_path)
    dest_path = Path(output_dir)
    pattern = filter_pattern or ""

    if not archive_path.is_file():
        raise FileNotFoundError(f"Archive not found: {archive_path}")
    if not create_directories and not dest_path.is_dir():
        raise FileNotFoundError(f"Target output directory '{dest_path}' does not exist.")

    archive = big.BigArchive(archive_path)

    # Inspect parsed entries via bindings
    entries = archive.get_entries(pattern)
    logger.info("Loaded %d entries from %s", len(entries), archive_path.name)

    on_progress = _make_progress_callback(logger, "Extracted", progress_callback)

    # Extract all indexed files to the destination folder
    archive.extract_all(dest_path, progress_callback=on_progress, filter_pattern=pattern, create_directories=create_directories)
    logger.info("Finished extracting into: %s", dest_path.resolve())

    return entries
