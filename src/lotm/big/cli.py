"""
@file src/lotm/big/cli.py
@brief Command-line interface for BIG archive tools

Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
Part of the Lord of the Mods (lotm) project.
SPDX-License-Identifier: GPL-3.0-or-later
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import NoReturn

from lotm.big.differ import create_patch, diff
from lotm.big.overlay import load_overlay
from lotm.big.packer import pack
from lotm.big.unpacker import unpack

EXIT_SUCCESS = 0
EXIT_ERROR = 1

logger = logging.getLogger("lotm.big")


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    pkg_logger = logging.getLogger("lotm")
    pkg_logger.setLevel(level)
    if not any(isinstance(h, logging.StreamHandler) for h in pkg_logger.handlers):
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(message)s"))
        pkg_logger.addHandler(handler)


def build_parser() -> argparse.ArgumentParser:
    """Construct and return the ArgumentParser for lotm-big."""
    parser = argparse.ArgumentParser(
        prog="lotm-big",
        description="Command-line interface for EA BIG4 archive manipulation.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcommand: pack
    pack_parser = subparsers.add_parser(
        "pack",
        help="Pack a directory into an EA BIG4 archive using lotm.",
    )
    pack_parser.add_argument("source_dir", type=Path, help="Path to the directory containing files to pack")
    pack_parser.add_argument("-o", "--output", type=Path, default=Path("packed_archive.big"), help="Destination .big file path")
    pack_parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output logging individual files")

    # Subcommand: unpack
    unpack_parser = subparsers.add_parser(
        "unpack",
        help="Extract EA BIG4 archives using lotm.",
    )
    unpack_parser.add_argument("archive", type=Path, help="Path to the .big file")
    unpack_parser.add_argument("-o", "--output", type=Path, default=Path("extracted_files"), help="Destination directory")
    unpack_parser.add_argument("-f", "--filter", type=str, default=None, help="Optional glob pattern to filter extracted files")
    unpack_parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output logging individual files")

    # Subcommand: diff
    diff_parser = subparsers.add_parser(
        "diff",
        help="Compare two EA BIG4 archives or generate a delta patch using lotm.",
    )
    diff_parser.add_argument("base_archive", type=Path, help="Path to the base .big file")
    diff_parser.add_argument("target_archive", type=Path, help="Path to the target .big file")
    diff_parser.add_argument("-o", "--output", type=Path, default=None, help="Optional destination .big file path to write a delta patch archive")
    diff_parser.add_argument("-f", "--filter", type=str, default=None, help="Optional glob pattern to filter compared files")
    diff_parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output logging individual changes")

    # Subcommand: overlay
    overlay_parser = subparsers.add_parser(
        "overlay",
        help="Inspect SAGE load-order resolution across .big archives using lotm.",
    )
    overlay_parser.add_argument("sources", type=Path, nargs="+", help="Directory containing .big files, or explicit .big archive paths in load order")
    overlay_parser.add_argument("-f", "--filter", type=str, default=None, help="Optional glob pattern to filter resolved entries")
    overlay_parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output logging winning archives and override counts")

    return parser


def _handle_pack(args: argparse.Namespace) -> int:
    _setup_logging(args.verbose)
    pack(args.source_dir, args.output)
    return EXIT_SUCCESS


def _handle_unpack(args: argparse.Namespace) -> int:
    _setup_logging(args.verbose)
    unpack(args.archive, args.output, filter_pattern=args.filter)
    return EXIT_SUCCESS


def _handle_diff(args: argparse.Namespace) -> int:
    _setup_logging(args.verbose)
    result = diff(args.base_archive, args.target_archive, filter_pattern=args.filter)
    for entry in result.added:
        logger.debug("+ %s (%d B)", entry.name, entry.size)
    for entry in result.removed:
        logger.debug("- %s (%d B)", entry.name, entry.size)
    for entry in result.modified:
        logger.debug("~ %s (%d B)", entry.name, entry.size)

    if args.output is not None:
        create_patch(args.base_archive, args.target_archive, args.output, filter_pattern=args.filter)
    return EXIT_SUCCESS


def _handle_overlay(args: argparse.Namespace) -> int:
    _setup_logging(args.verbose)
    target_source = args.sources[0] if len(args.sources) == 1 and args.sources[0].is_dir() else args.sources
    overlay = load_overlay(target_source)
    entries = overlay.get_entries(args.filter or "")
    logger.info("Resolved %d effective entries across %d archives", len(entries), len(overlay.mounted_archives))
    for item in entries:
        logger.debug("%s -> %s (overrides=%d)", item.name, item.source_archive.name, item.override_count)
    return EXIT_SUCCESS


def main(argv: Sequence[str] | None = None) -> int:
    """
    Execute the lotm-big CLI with structured exception handling.

    Parameters
    ----------
    argv : Sequence[str] | None, default=None
        Command-line arguments (defaults to sys.argv[1:] when None).

    Returns
    -------
    int
        Process exit code (0 for success, 1 for runtime error).
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "pack":
            return _handle_pack(args)
        if args.command == "unpack":
            return _handle_unpack(args)
        if args.command == "diff":
            return _handle_diff(args)
        if args.command == "overlay":
            return _handle_overlay(args)
    except Exception as exc:
        print(f"Command '{args.command}' failed: {exc}", file=sys.stderr)
        return EXIT_ERROR

    return EXIT_ERROR  # pragma: no cover


def cli_entry() -> NoReturn:
    """Console script entry point for pyproject.toml."""
    sys.exit(main())


if __name__ == "__main__":  # pragma: no cover
    cli_entry()
