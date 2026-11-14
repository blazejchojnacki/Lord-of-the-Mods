"""
@file src/lotm/ini/cli.py
@brief Command-line interface subcommands for the lotm.ini domain package.

Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
Part of the Lord of the Mods (lotm) project.
SPDX-License-Identifier: GPL-3.0-or-later
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from lotm.ini.diagnostics import inspect_ini, scan_ini
from lotm.ini.formatter import format_ini
from lotm.ini.parser import IniParseError

EXIT_SUCCESS = 0
EXIT_ERROR = 1


def _handle_scan(args: argparse.Namespace) -> int:
    """Execute `lotm ini scan` across a target file or directory."""
    target = Path(args.target)
    results = scan_ini(target, strict=False)

    total_files = len(results)
    files_with_errors = {path: errs for path, errs in results.items() if errs}
    clean_files = total_files - len(files_with_errors)

    lines: list[str] = [
        f"Scanned {total_files} file(s): {clean_files} clean, {len(files_with_errors)} with errors."
    ]
    for file_path, errs in files_with_errors.items():
        lines.append(f"\n[{file_path}] ({len(errs)} error(s)):")
        for err in errs:
            lines.append(f"  - {err}")

    report_text = "\n".join(lines) + "\n"

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(report_text, encoding="utf-8")
        print(f"Scan report written to '{out_path}'.")
    else:
        stream = sys.stderr if files_with_errors else sys.stdout
        print(report_text, end="", file=stream)

    if args.strict and files_with_errors:
        raise IniParseError(
            f"Strict scan failed: {len(files_with_errors)} file(s) contain structural errors."
        )

    return EXIT_SUCCESS


def _handle_format(args: argparse.Namespace) -> int:
    """Execute `lotm ini format` on a single configuration file."""
    source_path = Path(args.file)
    dest_path = Path(args.output) if args.output else source_path

    format_ini(source_path, output_path=dest_path, strict=args.strict)

    if args.output:
        print(f"Formatted '{source_path}' -> '{dest_path}'.")
    else:
        print(f"Formatted '{source_path}' in-place.")
    return EXIT_SUCCESS


def _handle_inspect(args: argparse.Namespace) -> int:
    """Execute `lotm ini inspect` and print a structural summary."""
    report = inspect_ini(args.file, strict=args.strict)

    print(f"File:            {report.file_path}")
    print(f"Type:            {report.file_type}")
    print(f"Start Level:     {report.start_level}")
    print(f"Defines:         {report.define_count}")
    print(f"Includes:        {report.include_count}")
    print(f"Top-Level Items: {report.total_top_level_items}")

    if report.block_counts:
        print("Block Breakdown:")
        for block_cls, count in sorted(report.block_counts.items()):
            print(f"  {block_cls}: {count}")

    if report.errors:
        print(f"Errors ({len(report.errors)}):", file=sys.stderr)
        for err in report.errors:
            print(f"  - {err}", file=sys.stderr)

    return EXIT_SUCCESS


def register_subparser(parent_subparsers: Any) -> None:
    """
    Register the `ini` domain subtree (`scan`, `format`, `inspect`) on the umbrella CLI parser.

    Parameters
    ----------
    parent_subparsers : argparse._SubParsersAction
        Top-level subparsers action from `lotm.cli`.
    """
    ini_parser = parent_subparsers.add_parser(
        "ini",
        help="Parse, validate, format, and inspect SAGE .ini, .inc, and .str files.",
        description="SAGE engine configuration (.ini, .inc, .str) utilities.",
    )
    subparsers = ini_parser.add_subparsers(dest="command", required=True)

    scan_parser = subparsers.add_parser(
        "scan",
        help="Scan a file or directory for delimiter and block nesting errors.",
    )
    scan_parser.add_argument(
        "target",
        help="Path to a .ini/.inc/.str file or directory to scan recursively.",
    )
    scan_parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="Optional output file path to write the diagnostic report.",
    )
    scan_parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with a non-zero error code if any structural errors are found.",
    )
    scan_parser.set_defaults(handler=_handle_scan)

    format_parser = subparsers.add_parser(
        "format",
        help="Format a .ini, .inc, or .str file with normalized indentation.",
    )
    format_parser.add_argument(
        "file",
        help="Path to the configuration file to format.",
    )
    format_parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="Destination file path (defaults to overwriting the input file in-place).",
    )
    format_parser.add_argument(
        "--strict",
        action="store_true",
        help="Abort formatting if any delimiter or level mismatch errors exist.",
    )
    format_parser.set_defaults(handler=_handle_format)

    inspect_parser = subparsers.add_parser(
        "inspect",
        help="Inspect a configuration file and display AST statistics.",
    )
    inspect_parser.add_argument(
        "file",
        help="Path to the .ini, .inc, or .str file to inspect.",
    )
    inspect_parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail with an error if the inspected file contains structural issues.",
    )
    inspect_parser.set_defaults(handler=_handle_inspect)
