"""
@file src/lotm/ini/ini_cli.py
@brief Command-line interface for SAGE .ini, .inc, and .str structural tools.

Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
Part of the Lord of the Mods (lotm) project.
SPDX-License-Identifier: GPL-3.0-or-later
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import NoReturn

from lotm.ini.parser import (
    IniParseError,
    parse_ini_file,
    parse_str_file,
    recognize_structure,
    scan_directory_for_errors,
    scan_file_for_errors,
)

EXIT_SUCCESS = 0
EXIT_ERROR = 1
EXIT_PARSE_FAILURE = 2


def build_parser() -> argparse.ArgumentParser:
    """Construct and return the ArgumentParser for lotm-ini."""
    parser = argparse.ArgumentParser(
        prog="lotm-ini",
        description="SAGE engine .ini, .inc, and .str parsing, formatting, and validation CLI.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcommand: scan
    scan_parser = subparsers.add_parser(
        "scan",
        help="Scan a file or directory for delimiter and syntax errors.",
    )
    scan_parser.add_argument(
        "target",
        type=Path,
        help="Path to a .ini/.inc/.str file or a directory to scan recursively.",
    )
    scan_parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Optional file path to write the diagnostic report.",
    )
    scan_parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with code 2 if any structural errors are detected.",
    )

    # Subcommand: format
    format_parser = subparsers.add_parser(
        "format",
        help="Parse and pretty-print a SAGE .ini, .inc, or .str file.",
    )
    format_parser.add_argument(
        "file_path",
        type=Path,
        help="Path to the input .ini, .inc, or .str file.",
    )
    format_parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Optional destination file path (writes to stdout if omitted).",
    )
    format_parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail with exit code 2 if delimiter mismatches occur.",
    )

    # Subcommand: inspect
    inspect_parser = subparsers.add_parser(
        "inspect",
        help="Inspect the recognized delimiter structure and nesting level of a file.",
    )
    inspect_parser.add_argument(
        "file_path",
        type=Path,
        help="Path to the .ini, .inc, or .str file to inspect.",
    )

    return parser


def _handle_scan(args: argparse.Namespace) -> int:
    target: Path = args.target
    if not target.exists():
        raise FileNotFoundError(f"Target path does not exist: {target}")

    report_lines: list[str] = []
    total_files = 0
    files_with_errors = 0
    total_errors = 0

    if target.is_file():
        total_files = 1
        errors = scan_file_for_errors(target)
        if errors:
            files_with_errors = 1
            total_errors = len(errors)
            report_lines.append(f"--- {target.name} ---")
            for err in errors:
                report_lines.append(f"  * {err}")
    elif target.is_dir():
        scan_results = scan_directory_for_errors(target)
        total_files = len(scan_results)
        for file_path, errors in scan_results.items():
            if errors:
                files_with_errors += 1
                total_errors += len(errors)
                rel_path = file_path.relative_to(target)
                report_lines.append(f"\n--- {rel_path} ---")
                for err in errors:
                    report_lines.append(f"  * {err}")
    else:
        raise OSError(f"Unsupported filesystem entry: {target}")

    header = [
        "=" * 60,
        f"Scan Report for: {target.resolve()}",
        f"Files with Errors: {files_with_errors} / {total_files}",
        f"Total Errors: {total_errors}",
        "=" * 60,
    ]
    full_report = "\n".join(header + report_lines)

    if args.output is not None:
        args.output.write_text(full_report + "\n", encoding="utf-8")
        print(f"Scan complete. Found {total_errors} errors across {files_with_errors} files.")
        print(f"Report saved to: {args.output.resolve()}")
    else:
        print(full_report)

    if args.strict and total_errors > 0:
        return EXIT_PARSE_FAILURE
    return EXIT_SUCCESS


def _handle_format(args: argparse.Namespace) -> int:
    file_path: Path = args.file_path
    if not file_path.is_file():
        raise FileNotFoundError(f"Input file does not exist: {file_path}")

    if file_path.suffix.lower() == ".str":
        doc = parse_str_file(file_path, strict=args.strict)
        formatted = doc.print()
        errors = list(doc.errors)
    else:
        ast = parse_ini_file(file_path, strict=args.strict)
        formatted = ast.print()
        errors = list(ast.errors)

    if args.output is not None:
        args.output.write_text(formatted, encoding="utf-8")
    else:
        sys.stdout.write(formatted)

    if args.strict and errors:
        return EXIT_PARSE_FAILURE
    return EXIT_SUCCESS


def _handle_inspect(args: argparse.Namespace) -> int:
    file_path: Path = args.file_path
    if not file_path.is_file():
        raise FileNotFoundError(f"Input file does not exist: {file_path}")

    delimiters, start_level = recognize_structure(file_path)
    if not delimiters:
        print(f"File: {file_path}")
        print("Structure: Unrecognized or empty")
        return EXIT_PARSE_FAILURE

    print(f"File: {file_path}")
    print(f"Start Level: {start_level}")
    for idx, level_delims in enumerate(delimiters):
        if level_delims:
            joined = ", ".join(level_delims)
            print(f"Level {idx} Delimiters ({len(level_delims)}): {joined}")
    return EXIT_SUCCESS


def main(argv: Sequence[str] | None = None) -> int:
    """
    Execute the lotm-ini CLI with structured exception handling.

    Parameters
    ----------
    argv : Sequence[str] | None, default=None
        Command-line arguments (defaults to sys.argv[1:] when None).

    Returns
    -------
    int
        Process exit code (0 for success, 1 for I/O or runtime error, 2 for parse error).
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "scan":
            return _handle_scan(args)
        if args.command == "format":
            return _handle_format(args)
        if args.command == "inspect":
            return _handle_inspect(args)
    except IniParseError as exc:
        print(f"Parse error: {exc}", file=sys.stderr)
        return EXIT_PARSE_FAILURE
    except (FileNotFoundError, NotADirectoryError, PermissionError, OSError) as exc:
        print(f"I/O error: {exc}", file=sys.stderr)
        return EXIT_ERROR
    except Exception as exc:  # pragma: no cover
        print(f"Unexpected error: {exc}", file=sys.stderr)
        return EXIT_ERROR

    return EXIT_ERROR  # pragma: no cover


def cli_entry() -> NoReturn:
    """Console script entry point for pyproject.toml."""
    sys.exit(main())


if __name__ == "__main__":
    cli_entry()
