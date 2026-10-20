'''
@file scripts/big_unpack.py
@brief Script enabling unpacking files from .BIG using shell commands

Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
Part of the Lord of the Mods (lotm) project.

This program is free software: you can redistribute it and/or modify
	it under the terms of the GNU General Public License as published by
	the Free Software Foundation, either version 3 of the License, or
	(at your option) any later version.

	This program is distributed in the hope that it will be useful,
	but WITHOUT ANY WARRANTY; without even the implied warranty of
	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
	GNU General Public License for more details.

	You should have received a copy of the GNU General Public License
	along with this program.  If not, see <https://www.gnu.org/licenses/>.

SPDX-License-Identifier: GPL-3.0-or-later
'''

import argparse
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


def extract(big_path: Path, output_dir: Path) -> None:
    if not big_path.is_file():
        raise FileNotFoundError(f"Archive not found: {big_path}")

    archive = big.BigArchive(big_path)

    # Parse header and index
    archive.read_header()

    # Inspect parsed entries via bindings
    entries = archive.get_entries()
    print(f"Loaded {len(entries)} entries from {big_path.name}")

    # Extract all indexed files to the destination folder
    archive.extract_all(output_dir)
    print(f"Finished extracting into: {output_dir.resolve()}")


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
        extract(args.archive, args.output)
    except Exception as exc:
        print(f"Extraction failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
