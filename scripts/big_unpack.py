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
