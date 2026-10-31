# Lord-of-the-Mods
# lotm Python API

The `lotm` project provides programmatic access to its core operations, allowing integration into custom UI applications, modding tools, and automation scripts.

## Installation

Install the pre-compiled library via pip:

```cmd
pip install lord-of-the-mods
```

## `lotm.big.pack`

### `pack(source_dir: str | os.PathLike[str], output_file: str | os.PathLike[str]) -> None`
Packs a directory structure into an EA BIG4 standard archive. Missing parent directories for the output destination are created automatically. Exposed directly from `lotm.big` (implemented in `lotm.big.packer`).

* **`source_dir`**: `str | os.PathLike[str]` pointing to the directory to compress.
* **`output_file`**: `str | os.PathLike[str]` indicating the target `.big` destination file.
* **Exceptions**:
  * `NotADirectoryError`: Raised if the source directory does not exist or is not a directory.
  * `ValueError`: Raised if the output file path resolves inside the source directory (self-inclusion).
  * `lotm.big.BigFormatError` (Native): Raised if an individual file or cumulative archive size exceeds the 4GB (32-bit) format boundary.
  * `lotm.big.BigArchiveError` (Native): Raised if an I/O read/write error occurs during packing.

---

## `lotm.big.unpack`

### `unpack(big_path: str | os.PathLike[str], output_dir: str | os.PathLike[str]) -> list[lotm.big.BigEntry]`
Extracts the contents of a BIG4 archive into a designated folder. Missing parent directories are created automatically. Exposed directly from `lotm.big` (implemented in `lotm.big.unpacker`).

* **`big_path`**: `str | os.PathLike[str]` pointing to the source `.big` archive to read.
* **`output_dir`**: `str | os.PathLike[str]` indicating the target extraction directory.
* **Returns**: A list of `BigEntry` objects containing `name`, `size`, and `offset` metadata for each extracted entry.
* **Exceptions**:
  * `FileNotFoundError`: Raised if the source `.big` file cannot be found.
  * `lotm.big.BigFormatError` (Native): Raised if the BIG4 magic header is missing, corrupted, or if physical archive bounds are breached.
  * `lotm.big.BigSecurityError` (Native): Raised if the archive contains directory traversals (Zip-Slip), Windows DOS device names, Alternate Data Streams (`:`), directory symlinks, or amplification (Zip-Bomb) structures.
  * `lotm.big.BigArchiveError` (Native): Raised if standard OS file stream operations fail.
