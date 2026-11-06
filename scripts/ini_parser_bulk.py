"""
@file scripts/ini_parser_bulk.py
@brief Batch scanner to test lotm.ini.parser against a directory of SAGE engine files.

Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
Part of the Lord of the Mods (lotm) project.
SPDX-License-Identifier: GPL-3.0-or-later
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from lotm.ini import (
    SUPPORTED_EXTENSIONS,
    IniParseError,
    scan_directory_for_errors,
)


def build_arg_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the batch fuzzing scanner."""
    parser = argparse.ArgumentParser(
        description="Scan SAGE config files for delimiter mismatches."
    )
    parser.add_argument(
        "target_dir",
        type=Path,
        help="Directory containing extracted game files",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("fuzz_report.txt"),
        help="Output report file",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return non-zero exit code if any file contains errors",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the batch scanner across all supported SAGE files in target_dir."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        scan_results = scan_directory_for_errors(
            args.target_dir, extensions=SUPPORTED_EXTENSIONS
        )
    except (FileNotFoundError, NotADirectoryError) as exc:
        print(f"Error: {args.target_dir} is not a valid directory ({exc}).", file=sys.stderr)
        return 1
    except (IniParseError, OSError) as exc:
        print(f"Error while scanning directory: {exc}", file=sys.stderr)
        return 1

    print(f"Found {len(scan_results)} files to scan. Processing...")

    report_lines: list[str] = []
    files_with_errors = 0
    total_errors = 0

    for file_path, errors in scan_results.items():
        if errors:
            files_with_errors += 1
            total_errors += len(errors)
            report_lines.append(f"\n--- {file_path.relative_to(args.target_dir)} ---")
            for err in errors:
                report_lines.append(f"  * {err}")

    report_lines.insert(0, "=" * 60)
    report_lines.insert(0, f"Total Errors: {total_errors}")
    report_lines.insert(0, f"Files with Errors: {files_with_errors} / {len(scan_results)}")
    report_lines.insert(0, f"Fuzzing Report for: {args.target_dir.resolve()}")
    report_lines.insert(0, "=" * 60)

    report_text = "\n".join(report_lines)
    try:
        args.output.write_text(report_text, encoding="utf-8")
    except OSError as exc:
        print(f"Error writing report to {args.output}: {exc}", file=sys.stderr)
        return 1

    print(f"Scan complete. Found {total_errors} errors across {files_with_errors} files.")
    print(f"Report saved to: {args.output.resolve()}")

    if args.strict and total_errors > 0:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
