'''
@file scripts/big_pack.py
@brief Script enabling packing files into .BIG using shell commands

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

    if not args.source_dir.is_dir():
        print(f"Error: Source directory '{args.source_dir}' does not exist.", file=sys.stderr)
        sys.exit(1)

    try:
        big.BigPacker.pack_from_directory(args.source_dir, args.output)
    except Exception as exc:
        print(f"Packing failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
