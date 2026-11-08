"""
@file src/lotm/big/differ.py
@brief Compare .BIG archives and generate delta patches (Library API)

Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
Part of the Lord of the Mods (lotm) project.
SPDX-License-Identifier: GPL-3.0-or-later
"""

from collections.abc import Callable
import logging
import os
from pathlib import Path
from lotm._core import big

logger = logging.getLogger("lotm.big.differ")


def diff(
    base_archive: str | os.PathLike[str],
    target_archive: str | os.PathLike[str],
    filter_pattern: str | None = None,
) -> big.BigDiffResult:
    """
    Compares two EA BIG4 archives and categorizes entries into added, removed, modified, and unchanged.

    Args:
        base_archive: Path to the baseline .big archive file.
        target_archive: Path to the target/modified .big archive file.
        filter_pattern: Optional glob pattern (e.g., 'data/ini/*.ini') to restrict comparison scope.

    Returns:
        A BigDiffResult object containing added, removed, modified, and unchanged BigEntry lists.

    Raises:
        FileNotFoundError: If either the base or target archive file does not exist.
        RuntimeError: If archive headers are malformed or stream reads fail.
    """
    base_path = Path(base_archive)
    target_path = Path(target_archive)
    pattern = filter_pattern or ""

    if not base_path.is_file():
        raise FileNotFoundError(f"Base archive not found: {base_path}")
    if not target_path.is_file():
        raise FileNotFoundError(f"Target archive not found: {target_path}")

    result = big.BigDiff.compare(base_path, target_path, filter_pattern=pattern)
    logger.info(
        "Diff complete (%s vs %s): +%d added, -%d removed, ~%d modified, =%d unchanged",
        base_path.name,
        target_path.name,
        len(result.added),
        len(result.removed),
        len(result.modified),
        len(result.unchanged),
    )
    return result


def create_patch(
    base_archive: str | os.PathLike[str],
    target_archive: str | os.PathLike[str],
    output_file: str | os.PathLike[str],
    filter_pattern: str | None = None,
    progress_callback: Callable[[big.ProgressReport], bool | None] | None = None,
) -> None:
    """
    Compares two EA BIG4 archives and packs only the added and modified entries into a standalone patch archive.

    Args:
        base_archive: Path to the baseline .big archive file.
        target_archive: Path to the target/modified .big archive file.
        output_file: Destination path for the generated delta patch .big archive.
        filter_pattern: Optional glob pattern to restrict which entries are evaluated and packed.
        progress_callback: Optional callback invoked with ProgressReport; returning False cancels patch creation.

    Raises:
        FileNotFoundError: If either the base or target archive file or target output directory does not exist.
        RuntimeError/ValueError: Native C++ exceptions if validation, serialization, or cancellation occurs.
    """
    base_path = Path(base_archive)
    target_path = Path(target_archive)
    output_path = Path(output_file)
    pattern = filter_pattern or ""

    if not base_path.is_file():
        raise FileNotFoundError(f"Base archive not found: {base_path}")
    if not target_path.is_file():
        raise FileNotFoundError(f"Target archive not found: {target_path}")
    if not output_path.parent.is_dir():
        raise FileNotFoundError(f"Target output directory '{output_path.parent}' does not exist.")

    def on_progress(report: big.ProgressReport) -> bool:
        if report.bytes_transferred == report.file_size:
            logger.debug("Packed patch entry: %s", report.entry_name)
        if progress_callback is not None:
            res = progress_callback(report)
            if res is False:
                return False
        return True

    big.BigDiff.create_patch(
        base_path, target_path, output_path, filter_pattern=pattern, progress_callback=on_progress
    )
    logger.info("Finished generating delta patch archive: %s", output_path.resolve())


def create_patch_to_memory(
    base_archive: str | os.PathLike[str],
    target_archive: str | os.PathLike[str],
    filter_pattern: str | None = None,
    progress_callback: Callable[[big.ProgressReport], bool | None] | None = None,
) -> bytes:
    """
    Compares two EA BIG4 archives and packs only the added and modified entries into an in-memory BIG4 buffer.

    Args:
        base_archive: Path to the baseline .big archive file.
        target_archive: Path to the target/modified .big archive file.
        filter_pattern: Optional glob pattern to restrict which entries are evaluated and packed.
        progress_callback: Optional callback invoked with ProgressReport; returning False cancels patch creation.

    Returns:
        A bytes object containing the serialized delta patch BIG4 archive.

    Raises:
        FileNotFoundError: If either the base or target archive file does not exist.
        RuntimeError/ValueError: Native C++ exceptions if validation, serialization, or cancellation occurs.
    """
    base_path = Path(base_archive)
    target_path = Path(target_archive)
    pattern = filter_pattern or ""

    if not base_path.is_file():
        raise FileNotFoundError(f"Base archive not found: {base_path}")
    if not target_path.is_file():
        raise FileNotFoundError(f"Target archive not found: {target_path}")

    def on_progress(report: big.ProgressReport) -> bool:
        if report.bytes_transferred == report.file_size:
            logger.debug("Packed patch entry to memory: %s", report.entry_name)
        if progress_callback is not None:
            res = progress_callback(report)
            if res is False:
                return False
        return True

    data = big.BigDiff.create_patch_to_memory(
        base_path, target_path, filter_pattern=pattern, progress_callback=on_progress
    )
    logger.info("Finished generating delta patch in memory (%d bytes)", len(data))
    return data
