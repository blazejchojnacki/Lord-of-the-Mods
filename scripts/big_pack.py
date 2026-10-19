# Gemini Pro 3.1

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
