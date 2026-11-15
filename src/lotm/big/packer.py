"""
@file src/lotm/big/packer.py
@brief Pack files into .BIG archives (Library API)

Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
Part of the Lord of the Mods (lotm) project.
SPDX-License-Identifier: GPL-3.0-or-later
"""

from collections.abc import Buffer, Callable, Iterable, Mapping
import logging
import os
from pathlib import Path
from lotm._core import big

logger = logging.getLogger("lotm.big.packer")


def pack(
    source_dir: str | os.PathLike[str],
    output_file: str | os.PathLike[str],
    progress_callback: Callable[[big.ProgressReport], bool | None] | None = None,
) -> None:
    """
    Pack a directory into an EA BIG4 archive.

    Parameters
    ----------
    source_dir : str | os.PathLike[str]
        Path to the directory containing files to pack.
    output_file : str | os.PathLike[str]
        Destination .big file path.
    progress_callback : Callable[[big.ProgressReport], bool | None] | None, default=None
        Optional callback invoked with `ProgressReport`; returning `False` cancels packing.

    Raises
    ------
    NotADirectoryError
        If the source directory is missing or invalid.
    FileNotFoundError
        If the target output directory does not exist.
    ValueError
        If the output archive path resides inside the source directory or contains
        duplicate case-insensitive entry paths.
    lotm.big.BigFormatError
        If an individual file or total archive size exceeds the 4 GiB (32-bit) format limit.
    lotm.big.BigArchiveError
        If an I/O error occurs or the operation is cancelled by `progress_callback`.

    Examples
    --------
    >>> pack("mod_workspace/data", "build/my_mod.big")  # doctest: +SKIP
    """
    source_path = Path(source_dir)
    output_path = Path(output_file)

    if not source_path.is_dir():
        raise NotADirectoryError(f"Source directory '{source_path}' does not exist or is not a directory.")
    if not output_path.parent.is_dir():
        raise FileNotFoundError(f"Target output directory '{output_path.parent}' does not exist.")

    def on_progress(report: big.ProgressReport) -> bool:
        if report.bytes_transferred == report.file_size:
            logger.debug("Packed: %s", report.entry_name)
        if progress_callback is not None:
            res = progress_callback(report)
            if res is False:
                return False
        return True

    big.BigPacker.pack_from_directory(source_path, output_path, progress_callback=on_progress)
    logger.info("Finished packing into: %s", output_path.resolve())


def pack_to_memory(
    source: str | os.PathLike[str] | Mapping[str, Buffer] | Iterable[tuple[str, Buffer]],
    progress_callback: Callable[[big.ProgressReport], bool | None] | None = None,
) -> bytes:
    """
    Pack a directory or an in-memory collection of `(path, buffer)` records into an EA BIG4 byte buffer.

    Parameters
    ----------
    source : str | os.PathLike[str] | Mapping[str, Buffer] | Iterable[tuple[str, Buffer]]
        Directory path, mapping of `{archive_path: payload_buffer}`, or iterable of
        `(archive_path, payload_buffer)` pairs.
    progress_callback : Callable[[big.ProgressReport], bool | None] | None, default=None
        Optional callback invoked with `ProgressReport`; returning `False` cancels packing.

    Returns
    -------
    bytes
        Serialized BIG4 archive payload.

    Raises
    ------
    NotADirectoryError
        If a filesystem path is provided and the source directory is missing or invalid.
    ValueError
        If an entry path is empty, unsafe, or duplicates another entry case-insensitively.
    lotm.big.BigFormatError
        If an individual file or total archive size exceeds the 4 GiB (32-bit) format limit.
    lotm.big.BigArchiveError
        If an I/O error occurs or the operation is cancelled by `progress_callback`.

    Examples
    --------
    >>> data = pack_to_memory({"data/weapon.ini": b"Damage=50"})
    >>> data[:4]
    b'BIG4'
    """
    def on_progress(report: big.ProgressReport) -> bool:
        if report.bytes_transferred == report.file_size:
            logger.debug("Packed to memory: %s", report.entry_name)
        if progress_callback is not None:
            res = progress_callback(report)
            if res is False:
                return False
        return True

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
