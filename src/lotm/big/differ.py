"""
@file src/lotm/big/differ.py
@brief Compare .BIG archives and generate delta patches (Library API)

Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
Part of the Lord of the Mods (lotm) project.
SPDX-License-Identifier: GPL-3.0-or-later
"""

import logging
import os
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TypeAlias

from lotm._core import big

from .packer import _make_progress_callback

logger = logging.getLogger("lotm.big.differ")

ArchiveSource: TypeAlias = str | os.PathLike[str] | big.BigArchive


@contextmanager
def _open_archive(archive: ArchiveSource, role: str) -> Iterator[big.BigArchive]:
    """Yield an open BigArchive, opening from disk when given a filesystem path."""
    if isinstance(archive, big.BigArchive):
        yield archive
    else:
        path = Path(archive)
        if not path.is_file():
            raise FileNotFoundError(f"{role} archive not found: {path}")
        with big.BigArchive(path) as opened:
            yield opened


def diff(
    base_archive: ArchiveSource,
    target_archive: ArchiveSource,
    filter_pattern: str | None = None,
) -> big.BigDiffResult:
    """
    Compare two EA BIG4 archives and categorize entries into added, removed, modified, and unchanged.

    Parameters
    ----------
    base_archive : str | os.PathLike[str] | big.BigArchive
        Path to the baseline `.big` archive file or an open `BigArchive` instance.
    target_archive : str | os.PathLike[str] | big.BigArchive
        Path to the target or modified `.big` archive file or an open `BigArchive` instance.
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
        If stream reads fail during byte-level comparison or an archive is closed.

    Examples
    --------
    >>> result = diff("vanilla.big", "modded.big", filter_pattern="*.ini")  # doctest: +SKIP
    """
    pattern = filter_pattern or ""

    with (
        _open_archive(base_archive, "Base") as base_arc,
        _open_archive(target_archive, "Target") as target_arc,
    ):
        result = big.BigDiff.compare(base_arc, target_arc, filter_pattern=pattern)
        logger.info(
            "Diff complete (%s vs %s): +%d added, -%d removed, ~%d modified, =%d unchanged",
            base_arc.file_path.name,
            target_arc.file_path.name,
            len(result.added),
            len(result.removed),
            len(result.modified),
            len(result.unchanged),
        )
        return result


def create_patch(
    base_archive: ArchiveSource,
    target_archive: ArchiveSource,
    output_file: str | os.PathLike[str],
    filter_pattern: str | None = None,
    progress_callback: Callable[[big.ProgressReport], bool | None] | None = None,
) -> None:
    """
    Compare two EA BIG4 archives and pack only added and modified entries into a standalone patch archive.

    Parameters
    ----------
    base_archive : str | os.PathLike[str] | big.BigArchive
        Path to the baseline `.big` archive file or an open `BigArchive` instance.
    target_archive : str | os.PathLike[str] | big.BigArchive
        Path to the target or modified `.big` archive file or an open `BigArchive` instance.
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
    output_path = Path(output_file)
    pattern = filter_pattern or ""

    with (
        _open_archive(base_archive, "Base") as base_arc,
        _open_archive(target_archive, "Target") as target_arc,
    ):
        if not output_path.parent.is_dir():
            raise FileNotFoundError(
                f"Target output directory '{output_path.parent}' does not exist."
            )

        on_progress = _make_progress_callback(
            logger, "Packed patch entry", progress_callback
        )
        big.BigDiff.create_patch(
            base_arc,
            target_arc,
            output_path,
            filter_pattern=pattern,
            progress_callback=on_progress,
        )
        logger.info(
            "Finished generating delta patch archive: %s", output_path.resolve()
        )


def create_patch_to_memory(
    base_archive: ArchiveSource,
    target_archive: ArchiveSource,
    filter_pattern: str | None = None,
    progress_callback: Callable[[big.ProgressReport], bool | None] | None = None,
) -> bytes:
    """
    Compare two EA BIG4 archives and pack only added and modified entries into an in-memory BIG4 buffer.

    Parameters
    ----------
    base_archive : str | os.PathLike[str] | big.BigArchive
        Path to the baseline `.big` archive file or an open `BigArchive` instance.
    target_archive : str | os.PathLike[str] | big.BigArchive
        Path to the target or modified `.big` archive file or an open `BigArchive` instance.
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
    pattern = filter_pattern or ""

    with (
        _open_archive(base_archive, "Base") as base_arc,
        _open_archive(target_archive, "Target") as target_arc,
    ):
        on_progress = _make_progress_callback(
            logger, "Packed patch entry to memory", progress_callback
        )
        data = big.BigDiff.create_patch_to_memory(
            base_arc, target_arc, filter_pattern=pattern, progress_callback=on_progress
        )
        logger.info("Finished generating delta patch in memory (%d bytes)", len(data))
        return data
