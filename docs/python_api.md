# Lord-of-the-Mods
# lotm Python API

The `lotm` project provides programmatic access to its core operations, allowing integration into custom UI applications, modding tools, and automation scripts.

## Installation

Install the pre-compiled library via pip:

```cmd
pip install lord-of-the-mods
```

## `lotm.big.pack`

### `pack(source_dir: Path, output_file: Path) -> None`
Packs a directory structure into an EA BIG4 standard archive. Missing parent directories for the output file are created automatically. Exposed from `lotm.big.packer`.

* **source_dir**: `pathlib.Path` pointing to the directory to compress.
* **output_file**: `pathlib.Path` indicating the target `.big` destination.
* **Exceptions**:
  * `NotADirectoryError`: Raised if the source directory is invalid or missing.
  * `ValueError`: Raised if the output file path resides inside the source directory (self-inclusion).
  * `lotm.big.BigFormatError` (Native): Raised if a single file or the total archive size exceeds the 4GB (32-bit) format limit.
  * `lotm.big.BigArchiveError` (Native): Raised if an I/O failure occurs during packing.

## `lotm.big.unpack`

### `unpack(big_path: Path, output_dir: Path) -> list[big.BigEntry]`
Extracts the contents of a BIG4 archive into a designated folder. Exposed from `lotm.big.unpacker`.

* **big_path**: `pathlib.Path` pointing to the source `.big` file.
* **output_dir**: `pathlib.Path` indicating the extraction destination.
* **Returns**: A list of `BigEntry` objects containing `name`, `size`, and `offset` metadata for the extracted files.
* **Exceptions**:
  * `FileNotFoundError`: Raised if the source archive does not exist.
  * `lotm.big.BigFormatError` (Native): Raised if the BIG4 magic header is missing, corrupted, or if physical file limits are breached.
  * `lotm.big.BigSecurityError` (Native): Raised if the archive contains malicious Zip-Slip path traversals, Windows DOS device names, Alternate Data Streams, or Zip-Bomb amplification structures.
  * `lotm.big.BigArchiveError` (Native): Raised if standard OS I/O read/write operations fail.
