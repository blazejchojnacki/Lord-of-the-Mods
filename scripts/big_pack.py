"""
@file scripts/big_pack.py
@brief Script enabling packing files into .BIG using shell commands

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

    big.BigPacker.pack_from_directory(source_dir, output_file)
    logger.info("Finished packing into: %s", output_file.resolve())


def main() -> None:
    parser = argparse.ArgumentParser(description="Pack a directory into an EA BIG4 archive using lotm.")
    parser.add_argument("source_dir", type=Path, help="Path to the directory containing files to pack")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("packed_archive.big"),
        help="Destination .big file path (default: ./packed_archive.big)",
    )

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    try:
        pack(args.source_dir, args.output)
    except Exception as exc:
        logger.error("Packing failed: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
