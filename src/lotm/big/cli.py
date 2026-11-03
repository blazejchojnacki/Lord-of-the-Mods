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

from lotm.big.differ import create_patch, diff
from lotm.big.packer import pack
from lotm.big.unpacker import unpack

logger = logging.getLogger("lotm.big")


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(message)s")


def main_pack() -> None:
    parser = argparse.ArgumentParser(description="Pack a directory into an EA BIG4 archive using lotm.")
    parser.add_argument("source_dir", type=Path, help="Path to the directory containing files to pack")
    parser.add_argument("-o", "--output", type=Path, default=Path("packed_archive.big"), help="Destination .big file path")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output logging individual files")
    args = parser.parse_args()

    _setup_logging(args.verbose)

    try:
        pack(args.source_dir, args.output)
    except Exception as exc:
        print(f"Packing failed: {exc}", file=sys.stderr)
        sys.exit(1)


def main_unpack() -> None:
    parser = argparse.ArgumentParser(description="Extract EA BIG4 archives using lotm.")
    parser.add_argument("archive", type=Path, help="Path to the .big file")
    parser.add_argument("-o", "--output", type=Path, default=Path("extracted_files"), help="Destination directory")
    parser.add_argument("-f", "--filter", type=str, default=None, help="Optional glob pattern to filter extracted files")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output logging individual files")
    args = parser.parse_args()

    _setup_logging(args.verbose)

    try:
        unpack(args.archive, args.output, filter_pattern=args.filter)
    except Exception as exc:
        print(f"Extraction failed: {exc}", file=sys.stderr)
        sys.exit(1)


def main_diff() -> None:
    parser = argparse.ArgumentParser(description="Compare two EA BIG4 archives or generate a delta patch using lotm.")
    parser.add_argument("base_archive", type=Path, help="Path to the base .big file")
    parser.add_argument("target_archive", type=Path, help="Path to the target .big file")
    parser.add_argument("-o", "--output", type=Path, default=None, help="Optional destination .big file path to write a delta patch archive")
    parser.add_argument("-f", "--filter", type=str, default=None, help="Optional glob pattern to filter compared files")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output logging individual changes")
    args = parser.parse_args()

    _setup_logging(args.verbose)

    try:
        result = diff(args.base_archive, args.target_archive, filter_pattern=args.filter)
        for entry in result.added:
            logger.debug("+ %s (%d B)", entry.name, entry.size)
        for entry in result.removed:
            logger.debug("- %s (%d B)", entry.name, entry.size)
        for entry in result.modified:
            logger.debug("~ %s (%d B)", entry.name, entry.size)

        if args.output is not None:
            create_patch(args.base_archive, args.target_archive, args.output, filter_pattern=args.filter)
    except Exception as exc:
        print(f"Comparison failed: {exc}", file=sys.stderr)
        sys.exit(1)
