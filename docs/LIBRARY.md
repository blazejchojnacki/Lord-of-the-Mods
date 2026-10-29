# Lord-of-the-Mods
# Python library guide

`lotm` exposes high-performance C++ archive operations directly to Python scripts.

## Installation

Install the pre-compiled library via pip:

```cmd
pip install lord-of-the-mods
```

No C++ compiler, CMake, or Visual Studio installation is required for pre-compiled wheels.

## Extracting an Archive:

Use `BigArchive` to inspect headers and unpack files. The archive header and index are parsed immediately and immutably upon instantiation.

```python
import lotm.big as big
from pathlib import Path

# Parses the header and validates the index securely upon initialization
archive = big.BigArchive(Path("ini.big"))

# List entries
for entry in archive.get_entries():
    print(f"{entry.name} ({entry.size} bytes at offset {entry.offset})")

# Optional progress callback
def on_extract(file_name: str) -> None:
    print(f"Successfully extracted: {file_name}")

# Extract all contents (thread-safe for multiple concurrent readers)
archive.extract_all(Path("extracted_ini"), progress_callback=on_extract)
```

## Repacking a directory:

Use the high-level `pack` utility to create a binary-search sorted archive compliant with the SAGE engine. Standard logging is used for progress tracking.

```python
import lotm.big as big
from pathlib import Path
import logging

logging.basicConfig(level=logging.DEBUG)

# Packs all files inside 'extracted_ini' into a compliant BIG4 archive
big.pack(
    source_dir=Path("extracted_ini"),
    output_file=Path("repacked_ini.big")
)
```

*(Note: For custom progress callbacks during packing, use the native C++ engine directly via `big.BigPacker.pack_from_directory(..., progress_callback=...)`)*
