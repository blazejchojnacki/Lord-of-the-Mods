# Lord-of-the-Mods
# lotm Python API

The `lotm` project provides programmatic access to its core operations, allowing integration into custom UI applications, modding tools, and automation scripts.

## Installation

Install the pre-compiled library via pip:

```cmd
pip install lord-of-the-mods
```

## `lotm.big.pack`

### `pack(source_dir: str | os.PathLike[str], output_file: str | os.PathLike[str], progress_callback: Callable[[ProgressReport], bool | None] | None = None) -> None`
Packs a directory structure into an EA BIG4 standard archive atomically via a temporary sibling file. Raises FileNotFoundError if the target output directory does not exist.

* **`source_dir`**: `str | os.PathLike[str]` pointing to the directory to compress.
* **`output_file`**: `str | os.PathLike[str]` indicating the target `.big` destination file.
* **`progress_callback`**: Optional callable receiving a `ProgressReport` instance. Returning `False` cancels the operation and triggers cleanup.
* **Exceptions**:
  * `NotADirectoryError`: Raised if the source directory does not exist or is not a directory.
  * `ValueError`: Raised if the output file path resolves inside the source directory (self-inclusion).
  * `lotm.big.BigFormatError` (Native): Raised if an individual file or cumulative archive size exceeds the 4GB (32-bit) format boundary.
  * `lotm.big.BigArchiveError` (Native): Raised if an I/O read/write error occurs during packing.
  * `FileNotFoundError`: Raised if the target output directory does not exist.

**Usage Example:**
```python
from pathlib import Path
from lotm.big import pack, BigFormatError, BigArchiveError

try:
    pack(Path("mod_workspace/data"), Path("build/my_mod.big"))
    print("Archive packed successfully.")
except ValueError as err:
    print(f"Configuration Error: {err}")
except (BigFormatError, BigArchiveError) as err:
    print(f"Native serialization failed: {err}")
```

### `pack_to_memory(source, progress_callback: Callable[[ProgressReport], bool | None] | None = None) -> bytes`
Packs a directory or an in-memory collection of paths and payloads into a contiguous BIG4 byte buffer without touching the disk.

* **`source`**: A directory path `str | os.PathLike`, a `Mapping[str, Buffer]`, or an `Iterable[tuple[str, Buffer]]`.
* **`progress_callback`**: Optional callable receiving a `ProgressReport` instance. Returning `False` cancels the operation.
* **Returns**: A `bytes` object representing the fully compliant archive.

```python
from lotm.big import pack_to_memory

virtual_mod = {
    "data/weapon.ini": b"Damage=50",
    "readme.txt": b"Mod v1.0",
}
archive_bytes = pack_to_memory(virtual_mod)
```

---

## `lotm.big.unpack`

### `unpack(big_path: str | os.PathLike[str], output_dir: str | os.PathLike[str], filter_pattern: str | None = None, progress_callback: Callable[[ProgressReport], bool | None] | None = None) -> list[lotm.big.BigEntry]`
Extracts the contents of a BIG4 archive into a designated folder. Raises FileNotFoundError if the target extraction directory does not exist. Exposed directly from `lotm.big` (implemented in `lotm.big.unpacker`).

* **`big_path`**: `str | os.PathLike[str]` pointing to the source `.big` archive to read.
* **`output_dir`**: `str | os.PathLike[str]` indicating the target extraction directory.
* **`filter_pattern`**: Optional glob string (e.g. `"data/ini/*.ini"`) to extract only matching files.
* **`progress_callback`**: Optional callable receiving a `ProgressReport` instance. Returning `False` cancels the operation and triggers cleanup of partial extractions.
* **Returns**: A list of `BigEntry` objects containing `name`, `size`, and `offset` metadata for each extracted entry.
* **Exceptions**:
  * `FileNotFoundError`: Raised if the source `.big` file or target output directory cannot be found.
  * `lotm.big.BigFormatError` (Native): Raised if the BIG4 magic header is missing, corrupted, or if physical archive bounds are breached.
  * `lotm.big.BigSecurityError` (Native): Raised if the archive contains directory traversals (Zip-Slip), Windows DOS device names, Alternate Data Streams (`:`), directory symlinks, or amplification (Zip-Bomb) structures.
  * `lotm.big.BigArchiveError` (Native): Raised if standard OS file stream operations fail or the operation is cancelled.

**Usage Example:**
```python
from pathlib import Path
from lotm.big import unpack, BigSecurityError, BigFormatError

try:
    entries = unpack(Path("downloaded_mod.big"), Path("extracted/"), filter_pattern="*.ini")
    print(f"Extracted {len(entries)} ini files successfully.")
except BigSecurityError as err:
    print(f"Security violation aborted extraction: {err}")
except BigFormatError as err:
    print(f"Corrupted or invalid BIG4 archive: {err}")
```

---

## `lotm.big.BigArchive`

For advanced use cases, the native `BigArchive` class provides object-oriented access to the archive, including in-memory single-file extraction and context management.

### Context Manager & Lifecycle
`BigArchive` implements the Python context manager protocol, ensuring that memory structures and the parsed index are deterministically released when the block exits.

```python
from lotm.big import BigArchive

with BigArchive("my_mod.big") as arc:
    entries = arc.get_entries("*.dds")
    print(f"Archive contains {len(entries)} texture files.")
# arc is now closed, memory is freed, and further calls will raise BigArchiveError.
```

### `read_entry(entry: str | BigEntry) -> bytes`
Reads a single archive entry directly into memory as a `bytes` object (fully supporting the Python Buffer Protocol) without unpacking the entire archive to disk. The GIL is safely released during physical I/O.

* **`entry`**: A `str` (the internal path inside the archive, matched case-insensitively using standard SAGE rules) or a `BigEntry` object obtained from `get_entries()`.
* **Returns**: A `bytes` object containing the binary file payload.
* **Exceptions**:
  * `lotm.big.BigArchiveError` (Native): Raised if the archive is closed, the file is unreadable, or the requested entry does not exist.
  * `lotm.big.BigFormatError` (Native): Raised if the physical bounds of the archive are breached during the read.

**Usage Example:**
```python
from lotm.big import BigArchive, BigArchiveError

try:
    with BigArchive("downloaded_mod.big") as arc:
        # Read via case-insensitive path string
        ini_data = arc.read_entry("data/weapon.ini")
        
        # Zero-copy memoryview parsing
        with memoryview(ini_data) as mv:
            header = mv[:10].tobytes()
            print(f"Header: {header}")
            
except BigArchiveError as err:
    print(f"Failed to read entry: {err}")
```

---

## `lotm.big.diff` & `create_patch`

The `BigDiff` engine compares two archives structurally and byte-by-byte.

### `diff(base_archive, target_archive, filter_pattern=None) -> BigDiffResult`
Outputs a `BigDiffResult` categorizing files into `added`, `removed`, `modified`, and `unchanged`.
```python
from lotm.big import diff

result = diff("vanilla.big", "modded.big")
if result.has_differences:
    print(f"Modified {len(result.modified)} files.")
```

### `create_patch(base_archive, target_archive, output_file, filter_pattern=None, progress_callback=None) -> None`
Automatically packs only the added and modified entries into a minimal, standalone patch archive. An in-memory variant (`create_patch_to_memory`) is also available.

---

## `lotm.big.load_overlay`

Simulates the SAGE engine's load-order to resolve the effective virtual file tree across multiple `.big` files.

### `load_overlay(source: Path | Iterable[Path]) -> BigOverlay`
```python
from lotm.big import load_overlay

# Pass a directory to load all enclosed archives alphabetically, or pass a specific sequence list.
overlay = load_overlay(["base.big", "patch.big", "mod.big"])

# Resolve the winning payload after all overrides are calculated
resolved = overlay.resolve("data/weapon.ini")
print(f"Weapon stats sourced from: {resolved.source_archive.name}")
```
