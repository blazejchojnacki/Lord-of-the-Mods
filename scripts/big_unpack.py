"""
@file scripts/big_unpack.py
@brief Script enabling unpacking files from .BIG using shell commands

Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
Part of the Lord of the Mods (lotm) project.
SPDX-License-Identifier: GPL-3.0-or-later
"""

import argparse
import logging
from pathlib import Path
import sys

try:
    import lotm.big as big
except ModuleNotFoundError:
    print(
        "Error: 'lotm' module not found. "
        "Ensure PYTHONPATH includes the build directory (e.g., build\\src\\cppy_bridge).",
        file=sys.stderr,
    )
    sys.exit(1)

logger = logging.getLogger("lotm")


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

    # Extract all indexed files to the destination folder
    archive.extract_all(output_dir)
    logger.info("Finished extracting into: %s", output_dir.resolve())

    return entries


# Backward-compatible alias
extract = unpack


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract EA BIG4 archives using lotm.")
    parser.add_argument("archive", type=Path, help="Path to the .big file")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("extracted_files"),
        help="Destination directory (default: ./extracted_files)",
    )

    args = parser.parse_args()

    try:
        unpack(args.archive, args.output)
    except Exception as exc:
        print(f"Extraction failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
