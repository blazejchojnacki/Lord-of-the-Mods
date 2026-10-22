# Python library user manual

`lotm` exposes high-performance C++ archive operations directly to Python scripts.

---

## Extracting an Archive:

Use `BigArchive` to inspect headers and unpack files

``` Python
import lotm.big as big
from pathlib import Path

archive = big.BigArchive(Path("ini.big"))
archive.read_header()

# List entries
for entry in archive.get_entries():
    print(f"{entry.name} ({entry.size} bytes at offset {entry.offset})")

# Extract all contents
archive.extract_all(Path("extracted_ini"))
```

## Repacking a directory:

Use `BigPacker` to create a binary-search sorted archive compliant with the SAGE engine

``` Python
import lotm.big as big
from pathlib import Path

# Packs all files inside 'extracted_ini' into a compliant BIG4 archive
big.BigPacker.pack_from_directory(
    source_dir=Path("extracted_ini"),
    output_file=Path("repacked_ini.big")
)
```