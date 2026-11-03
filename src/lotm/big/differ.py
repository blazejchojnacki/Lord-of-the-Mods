"""
@file src/lotm/big/differ.py
@brief Compare .BIG archives (Library API)

Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
Part of the Lord of the Mods (lotm) project.
SPDX-License-Identifier: GPL-3.0-or-later
"""

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
