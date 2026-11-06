"""
@file scripts/fuzz_ini_parser.py
@brief Batch scanner to test lotm.ini.parser against a directory of SAGE engine files.

Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
Part of the Lord of the Mods (lotm) project.
SPDX-License-Identifier: GPL-3.0-or-later
"""

import argparse
import sys
from pathlib import Path
from lotm.ini import scan_file_for_errors

def main() -> None:
    parser = argparse.ArgumentParser(description="Scan SAGE config files for delimiter mismatches.")
    parser.add_argument("target_dir", type=Path, help="Directory containing extracted game files")
    parser.add_argument("-o", "--output", type=Path, default=Path("fuzz_report.txt"), help="Output report file")
    args = parser.parse_args()

    if not args.target_dir.is_dir():
        print(f"Error: {args.target_dir} is not a valid directory.", file=sys.stderr)
        sys.exit(1)

    target_exts = {".ini", ".inc", ".str"}
    files_to_scan = [p for p in args.target_dir.rglob("*") if p.is_file() and p.suffix.lower() in target_exts]

    print(f"Found {len(files_to_scan)} files to scan. Processing...")

    report_lines = []
    files_with_errors = 0
    total_errors = 0

    for file_path in files_to_scan:
        errors = scan_file_for_errors(str(file_path))
        if errors:
            files_with_errors += 1
            total_errors += len(errors)
            report_lines.append(f"\n--- {file_path.relative_to(args.target_dir)} ---")
            for err in errors:
                report_lines.append(f"  * {err}")

    report_lines.insert(0, "=" * 60)
    report_lines.insert(0, f"Total Errors: {total_errors}")
    report_lines.insert(0, f"Files with Errors: {files_with_errors} / {len(files_to_scan)}")
    report_lines.insert(0, f"Fuzzing Report for: {args.target_dir.resolve()}")
    report_lines.insert(0, "=" * 60)

    report_text = "\n".join(report_lines)
    args.output.write_text(report_text, encoding="utf-8")
    
    print(f"Scan complete. Found {total_errors} errors across {files_with_errors} files.")
    print(f"Report saved to: {args.output.resolve()}")

if __name__ == "__main__":
    main()
