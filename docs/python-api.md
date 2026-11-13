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

### `unpack(big_path: str | os.PathLike[str], output_dir: str | os.PathLike[str], filter_pattern: str | None = None, progress_callback: Callable[[ProgressReport], bool | None] | None = None, create_directories: bool = True) -> list[lotm.big.BigEntry]`
Extracts the contents of a BIG4 archive into a designated folder. Exposed directly from `lotm.big` (implemented in `lotm.big.unpacker`).

* **`big_path`**: `str | os.PathLike[str]` pointing to the source `.big` archive to read.
* **`output_dir`**: `str | os.PathLike[str]` indicating the target extraction directory.
* **`filter_pattern`**: Optional glob string (e.g. `"data/ini/*.ini"`) to extract only matching files.
* **`progress_callback`**: Optional callable receiving a `ProgressReport` instance. Returning `False` cancels the operation and triggers cleanup of partial extractions.
* **`create_directories`**: If `True`, automatically creates the output directory tree. If `False`, raises `FileNotFoundError` if `output_dir` does not exist prior to extraction.
* **Returns**: A list of `BigEntry` objects containing `name`, `size`, and `offset` metadata for each extracted entry.
* **Exceptions**:
  * `FileNotFoundError`: Raised if the source `.big` file cannot be found, or if the target output directory cannot be found when `create_directories` is `False`.
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
    print(f"Archive is bound to {arc.file_path}")
    entries = arc.get_entries("*.dds")
    print(f"Archive contains {len(entries)} texture files.")
# arc is now closed, memory is freed, and further calls will raise BigArchiveError.
```

### `read_entry(entry: str | os.PathLike[str] | BigEntry) -> bytes`
Reads a single archive entry directly into memory as a `bytes` object (fully supporting the Python Buffer Protocol) without unpacking the entire archive to disk. The GIL is safely released during physical I/O.

* **`entry`**: A string/Path object (internal path matched case-insensitively using standard SAGE rules) or a `BigEntry` object obtained from `get_entries()`.
* **Returns**: A `bytes` object containing the binary file payload.
* **Exceptions**:
  * `lotm.big.BigArchiveError` (Native): Raised if the archive is closed, the file is unreadable, or the requested entry does not exist.
  * `lotm.big.BigFormatError` (Native): Raised if the physical bounds of the archive are breached during the read.

### `stream_entry(entry: str | os.PathLike[str] | BigEntry, chunk_callback: Callable[[memoryview], bool | None]) -> None`
Streams an entry payload strictly from the source archive through reusable buffers without materializing the entire file in RAM. Recommended for large assets (`.vp6`, `.map`, `.w3d`).

* **`entry`**: A string/Path object or a `BigEntry` object.
* **`chunk_callback`**: Callable invoked sequentially with each memoryview chunk (up to 1MB). Return `False` to abort streaming.

**Usage Example:**
```python
from lotm.big import BigArchive, BigArchiveError

try:
    with BigArchive("downloaded_mod.big") as arc:
        # Zero-copy streaming for large video assets
        def _process_video(chunk: memoryview) -> bool:
            # Send chunk bytes to decoder or disk sink
            return True
            
        arc.stream_entry("data/movies/intro.vp6", _process_video)
            
except BigArchiveError as err:
    print(f"Failed to stream entry: {err}")
```

---

## `lotm.big.diff` & `create_patch`

The `BigDiff` engine compares two archives structurally and byte-by-byte.

### `diff(base: str | Path | BigArchive, target: str | Path | BigArchive, filter_pattern=None) -> BigDiffResult`
Outputs a `BigDiffResult` categorizing files into `added`, `removed`, `modified`, and `unchanged`.

### `create_patch(base, target, output_file, filter_pattern=None, progress_callback=None) -> None`
Automatically packs only the added and modified entries into a minimal, standalone patch archive. An in-memory variant (`create_patch_to_memory`) is also available.

---

## `lotm.big.load_overlay`

Simulates the SAGE engine's load-order to resolve the effective virtual file tree across multiple `.big` files.

### `load_overlay(source: Path | Iterable[Path]) -> BigOverlay`
`BigOverlay` exposes `read_entry(name)` and `stream_entry(name, cb)` matching `BigArchive` semantics. It also supports context managers to release memory deterministically.

```python
from lotm.big import load_overlay

# Pass a directory to load all enclosed archives alphabetically, or pass a specific sequence list.
with load_overlay(["base.big", "patch.big", "mod.big"]) as overlay:
    # Resolve the winning payload after all overrides are calculated
    resolved = overlay.resolve("data/weapon.ini")
    print(f"Weapon stats sourced from: {resolved.source_archive.name}")
    
    weapon_bytes = overlay.read_entry("data/weapon.ini")
```

---

## `lotm.ini` — SAGE Configuration & Localization API

The `lotm.ini` package provides a native C++20 AST parser, iterative serializer, and validator for SAGE `.ini`, `.inc`, and `.str` files.

### `parse_ini(file_path: str | os.PathLike[str], *, strict: bool = False, file_content: str | Buffer | None = None) -> ConstructFile`
Parses a `.ini`, `.inc`, or `.str` file into a root `ConstructFile` AST object. When `file_content` is `None`, the file is memory-mapped directly from disk via Win32 `CreateFileMappingW`. When a `bytes` or `memoryview` buffer is supplied (such as from `BigArchive.read_entry`), it is ingested zero-copy without intermediate Python string decoding.

* **`file_path`**: Path to the configuration file (used for extension recognition and error reporting, or disk reading when `file_content` is `None`).
* **`strict`**: If `True`, raises `IniParseError` immediately on negative nesting levels or unclosed blocks at EOF. If `False`, records diagnostics in `ConstructFile.errors`.
* **`file_content`**: Optional `str` or binary `Buffer` (`bytes`, `bytearray`, `memoryview`).
* **Exceptions**:
  * `lotm.ini.IniParseError`: Raised on invalid file paths/extensions, strict delimiter mismatches, exceeding `MAX_INI_DEPTH` (16), or exceeding legacy 32-bit SAGE buffer limits (256-byte block names / 512-byte identifiers).

**Zero-Copy BIG-to-INI Pipeline Example:**
```python
from lotm.big import BigArchive
from lotm.ini import parse_ini, ConstructLevel

with BigArchive("ini.big") as archive:
    raw_bytes = archive.read_entry("data/ini/weapon.ini")
    doc = parse_ini("data/ini/weapon.ini", strict=True, file_content=raw_bytes)

for item in doc:
    if isinstance(item, ConstructLevel):
        print(f"{item._class} -> {item.name}")
```

### `parse_str(file_path: str | os.PathLike[str], *, strict: bool = False, file_content: str | Buffer | None = None) -> StrDocument`
Parses a SAGE `.str` localization dictionary into a `StrDocument` containing `StrEntry` blocks, standalone comments, and diagnostic errors.

### `format_ini(file_path: str | os.PathLike[str], output_path: str | os.PathLike[str] | None = None, *, strict: bool = False, file_content: str | None = None) -> str`
Parses and iteratively serializes a `.ini`, `.inc`, or `.str` file with consistent 4-space indentation, optionally writing the formatted output to `output_path`.

### `scan_ini(target_path: str | os.PathLike[str], *, strict: bool = False) -> dict[Path, list[str]]`
Scans a single file or recursively scans a directory tree for `.ini`, `.inc`, and `.str` structural errors, returning a dictionary mapping each `Path` to its list of diagnostic messages.

### `inspect_ini(file_path: str | os.PathLike[str], *, strict: bool = False, file_content: str | None = None) -> IniInspectionReport`
Returns an immutable `IniInspectionReport` dataclass summarizing `file_path`, `file_type`, `start_level`, `define_count`, `include_count`, `total_top_level_items`, `block_counts`, and `errors`.

### `validate_include(node: IncludeNode, current_file: str | os.PathLike[str], virtual_root: str | os.PathLike[str]) -> Path`
Resolves a `#include` directive (`IncludeNode`) relative to `current_file.parent` or `virtual_root` and verifies that the canonical target path remains strictly confined inside `virtual_root` (blocking `../` Local File Inclusion escapes).

```python
from pathlib import Path
from lotm.ini import IncludeNode, validate_include, IniParseError

node = IncludeNode('"..\\common\\macros.inc"')
try:
    safe_path = validate_include(
        node,
        current_file=Path("mod/data/ini/object/hero.ini"),
        virtual_root=Path("mod/data/ini"),
    )
except IniParseError as err:
    print(f"Blocked unsafe include: {err}")
```

### AST Node Hierarchy (`lotm.ini`)
* **`ConstructFile`**: Root document container supporting `len(doc)`, indexing (`doc[i]`), iteration, `.append(node)`, `.defines`, `.errors`, and `.print()`.
* **`ConstructLevel`**: Nested block node (`_class`, `name`, `identifier`, `comment`, `header_comment`, `end_token`, `end_comment`, `items`) supporting sequence indexing, iteration, `.append(node)`, and `.print(level=0, file_type=".ini")`.
* **`ScriptNode`**: Opaque `BeginScript ... EndScript` container preserving raw Lua lines (`content`) so inner Lua `end` tokens never collide with INI block closures.
* **`IncludeNode`**: Lossless `#include` node exposing `raw_path`, `comment`, and the normalized `.clean_path` property.
* **`StatementNode` & `CommentNode`**: Leaf AST nodes representing key-value assignments and standalone/inline comments.
* **`StrEntry` & `StrDocument`**: Localization structures for `.str` files.
