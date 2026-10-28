"""
@file src/lotm/big/cli.py
@brief Command-line interface for BIG archive tools

Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
Part of the Lord of the Mods (lotm) project.
SPDX-License-Identifier: GPL-3.0-or-later
"""

import argparse
import logging
import sys
from pathlib import Path

from lotm.big.packer import pack
from lotm.big.unpacker import unpack

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("lotm.big")


def main_pack() -> None:
    parser = argparse.ArgumentParser(description="Pack a directory into an EA BIG4 archive using lotm.")
    parser.add_argument("source_dir", type=Path, help="Path to the directory containing files to pack")
    parser.add_argument("-o", "--output", type=Path, default=Path("packed_archive.big"), help="Destination .big file path")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output logging individual files")
    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    try:
        pack(args.source_dir, args.output)
    except Exception as exc:
        print(f"Packing failed: {exc}", file=sys.stderr)
        sys.exit(1)


def main_unpack() -> None:
    parser = argparse.ArgumentParser(description="Extract EA BIG4 archives using lotm.")
    parser.add_argument("archive", type=Path, help="Path to the .big file")
    parser.add_argument("-o", "--output", type=Path, default=Path("extracted_files"), help="Destination directory")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output logging individual files")
    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    try:
        unpack(args.archive, args.output)
    except Exception as exc:
        print(f"Extraction failed: {exc}", file=sys.stderr)
        sys.exit(1)
