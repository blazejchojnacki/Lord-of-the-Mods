# Extracting an Archive:

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

# Repacking a directory:

``` Python
import lotm.big as big
from pathlib import Path

# Packs all files inside 'extracted_ini' into a compliant BIG4 archive
big.BigPacker.pack_from_directory(
    source_dir=Path("extracted_ini"),
    output_file=Path("repacked_ini.big")
)
```