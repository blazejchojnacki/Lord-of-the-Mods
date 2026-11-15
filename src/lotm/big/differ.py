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
    Compare two EA BIG4 archives and categorize entries into added, removed, modified, and unchanged.

    Parameters
    ----------
    base_archive : str | os.PathLike[str]
        Path to the baseline `.big` archive file.
    target_archive : str | os.PathLike[str]
        Path to the target or modified `.big` archive file.
    filter_pattern : str | None, default=None
        Optional glob pattern (e.g., `'data/ini/*.ini'`) to restrict comparison scope.

    Returns
    -------
    big.BigDiffResult
        Comparison result containing `added`, `removed`, `modified`, and `unchanged` entry lists.

    Raises
    ------
    FileNotFoundError
        If either the base or target archive file does not exist.
    lotm.big.BigFormatError
        If archive headers are malformed or entry bounds exceed physical file size.
    lotm.big.BigSecurityError
        If either archive exceeds the Zip-Bomb amplification ratio quota.
    lotm.big.BigArchiveError
        If stream reads fail during byte-level comparison.

    Examples
    --------
    >>> result = diff("vanilla.big", "modded.big", filter_pattern="*.ini")  # doctest: +SKIP
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
    Compare two EA BIG4 archives and pack only added and modified entries into a standalone patch archive.

    Parameters
    ----------
    base_archive : str | os.PathLike[str]
        Path to the baseline `.big` archive file.
    target_archive : str | os.PathLike[str]
        Path to the target or modified `.big` archive file.
    output_file : str | os.PathLike[str]
        Destination path for the generated delta patch `.big` archive.
    filter_pattern : str | None, default=None
        Optional glob pattern to restrict which entries are evaluated and packed.
    progress_callback : Callable[[big.ProgressReport], bool | None] | None, default=None
        Optional callback invoked with `ProgressReport`; returning `False` cancels patch creation.

    Raises
    ------
    FileNotFoundError
        If either the base or target archive file or target output directory does not exist.
    ValueError
        If `output_file` aliases an input archive or resolves to an existing directory.
    lotm.big.BigFormatError
        If archive headers are malformed or the patch exceeds the 4 GiB (32-bit) format limit.
    lotm.big.BigSecurityError
        If either input archive exceeds the Zip-Bomb amplification ratio quota.
    lotm.big.BigArchiveError
        If stream I/O fails or patch generation is cancelled by `progress_callback`.

    Examples
    --------
    >>> create_patch("vanilla.big", "modded.big", "delta_patch.big")  # doctest: +SKIP
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
    Compare two EA BIG4 archives and pack only added and modified entries into an in-memory BIG4 buffer.

    Parameters
    ----------
    base_archive : str | os.PathLike[str]
        Path to the baseline `.big` archive file.
    target_archive : str | os.PathLike[str]
        Path to the target or modified `.big` archive file.
    filter_pattern : str | None, default=None
        Optional glob pattern to restrict which entries are evaluated and packed.
    progress_callback : Callable[[big.ProgressReport], bool | None] | None, default=None
        Optional callback invoked with `ProgressReport`; returning `False` cancels patch creation.

    Returns
    -------
    bytes
        Serialized delta patch BIG4 archive buffer.

    Raises
    ------
    FileNotFoundError
        If either the base or target archive file does not exist.
    lotm.big.BigFormatError
        If archive headers are malformed or the patch exceeds the 4 GiB (32-bit) format limit.
    lotm.big.BigSecurityError
        If either input archive exceeds the Zip-Bomb amplification ratio quota.
    lotm.big.BigArchiveError
        If stream I/O fails or patch generation is cancelled by `progress_callback`.

    Examples
    --------
    >>> patch_bytes = create_patch_to_memory("vanilla.big", "modded.big")  # doctest: +SKIP
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
