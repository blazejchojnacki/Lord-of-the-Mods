# Lord-of-the-Mods
# lotm Python API

The `lotm` project provides programmatic access to its core operations, allowing integration into custom UI applications, modding tools, and automation scripts.

## `scripts.big_pack`

### `pack(source_dir: Path, output_file: Path) -> None`
Packs a directory structure into an EA BIG4 standard archive. Missing parent directories for the output file are created automatically.

* **source_dir**: `pathlib.Path` pointing to the directory to compress.
* **output_file**: `pathlib.Path` indicating the target `.big` destination.
* **Exceptions**:
  * `NotADirectoryError`: Raised if the source directory is invalid or missing.
  * `std::length_error` (Native): Raised if a single file or the total archive size exceeds the 4GB (32-bit) format limit.

## `scripts.big_unpack`

### `unpack(big_path: Path, output_dir: Path) -> list[big.BigEntry]`
Extracts the contents of a BIG4 archive into a designated folder. Aliased as `extract()`.

* **big_path**: `pathlib.Path` pointing to the source `.big` file.
* **output_dir**: `pathlib.Path` indicating the extraction destination.
* **Returns**: A list of `BigEntry` objects containing `name`, `size`, and `offset` metadata for the extracted files.
* **Exceptions**:
  * `FileNotFoundError`: Raised if the source archive does not exist.
  * `ValueError` (Native): Raised if the BIG4 magic header is missing or corrupt.
